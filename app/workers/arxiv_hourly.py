import logging
import random
import time
from collections.abc import Sequence
from datetime import datetime, timedelta

import feedparser

from app.config import settings
from app.db.models.paper import Paper
from app.db.session import SessionLocal
from app.lib.http import HttpClient
from app.metrics import ARXIV_ERRORS, ARXIV_PAPERS_PROCESSED, ARXIV_REQUESTS_TOTAL
from app.services.embeddings import EmbeddingService
from app.services.keyword_domain import classify_domain

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
PAGE_LIMIT = 3
FETCH_DELAY = 3.0


def _parse_published(entry) -> datetime | None:
    published_parsed = entry.get("published_parsed")
    if not published_parsed:
        return None
    return datetime(*published_parsed[:6])


def _extract_keywords(entry: dict) -> Sequence[str]:
    tags = [tag.get("term") for tag in entry.get("tags", []) if tag.get("term")]
    primary = entry.get("arxiv_primary_category", {}).get("term")
    if primary and primary not in tags:
        tags.insert(0, primary)
    return tags if tags else []


def _enforce_domain(title: str, keywords: Sequence[str]) -> str:
    base_text = title or ""
    # fallback to classify by keywords if text is sparse
    return classify_domain(base_text, keywords or settings.arxiv_categories)


def _build_embedding_text(entry: dict) -> str:
    pieces = [entry.get("title"), entry.get("summary")]
    return "\n".join(p.strip() for p in pieces if p)


def _fetch_entries(
    client: HttpClient, category: str, start: int, max_results: int
) -> list[dict]:
    params = {
        "search_query": f"cat:{category}",
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    try:
        resp = client.get(
            ARXIV_API_URL, params=params, extra_headers={"Accept": "application/atom+xml"}
        )
        ARXIV_REQUESTS_TOTAL.labels(category=category, status=resp.status_code).inc()
        
        if resp.status_code != 200:
            logger.warning(
                "arXiv request failed (%s): %s", resp.status_code, resp.text[:200]
            )
            ARXIV_ERRORS.labels(category=category, error_type="http_error").inc()
            return []
        return list(feedparser.parse(resp.text).entries)
    except Exception as e:
        logger.error("arXiv request exception for category %s: %s", category, str(e))
        ARXIV_REQUESTS_TOTAL.labels(category=category, status="error").inc()
        ARXIV_ERRORS.labels(category=category, error_type="request_exception").inc()
        return []


def _persist_entry(
    session, embedder: EmbeddingService, entry: dict, published_at: datetime | None, category: str
):
    external_id = entry.get("id")
    if not external_id:
        ARXIV_ERRORS.labels(category=category, error_type="missing_id").inc()
        return None
    if "/" in external_id:
        external_id = external_id.rsplit("/", 1)[-1]
    
    try:
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or "").strip()
        keywords = list(_extract_keywords(entry))
        doi = entry.get("arxiv_doi")
        domain = _enforce_domain(title, keywords)
        text_to_embed = _build_embedding_text(entry) or external_id
        embedding = embedder.embed(text_to_embed)
        if len(embedding) != settings.embedding_dim:
            logger.debug(
                "Embedding dim mismatch (%d expected, %d got)",
                settings.embedding_dim,
                len(embedding),
            )
        paper = session.query(Paper).filter_by(external_id=external_id).one_or_none()
        values = {
            "title": title,
            "abstract": summary,
            "domain": domain,
            "keywords": keywords,
            "doi": doi,
            "published_at": published_at,
            "embedding": embedding,
        }
        if not paper:
            paper = Paper(external_id=external_id, **values)
            session.add(paper)
            ARXIV_PAPERS_PROCESSED.labels(category=category, status="inserted").inc()
            return "insert"
        updated = False
        for field, value in values.items():
            if getattr(paper, field) != value:
                setattr(paper, field, value)
                updated = True
        if updated:
            ARXIV_PAPERS_PROCESSED.labels(category=category, status="updated").inc()
        else:
            ARXIV_PAPERS_PROCESSED.labels(category=category, status="unchanged").inc()
        return "update" if updated else None
    except Exception as e:
        logger.error("Error persisting arXiv entry %s: %s", external_id, str(e))
        ARXIV_ERRORS.labels(category=category, error_type="persist_error").inc()
        raise


def main() -> None:
    client = HttpClient()
    embedder = EmbeddingService.get()
    cutoff = datetime.utcnow() - timedelta(days=settings.arxiv_lookback_days)
    inserted = 0
    updated = 0
    session = SessionLocal()
    try:
        for category in settings.arxiv_categories:
            start = 0
            page = 0
            stop = False
            while page < PAGE_LIMIT and not stop:
                entries = _fetch_entries(
                    client, category, start, settings.arxiv_max_results
                )
                if not entries:
                    break
                for entry in entries:
                    published_at = _parse_published(entry)
                    if published_at and published_at < cutoff:
                        stop = True
                        break
                    status = _persist_entry(session, embedder, entry, published_at, category)
                    if status == "insert":
                        inserted += 1
                    elif status == "update":
                        updated += 1
                session.commit()
                page += 1
                start += settings.arxiv_max_results
                if stop:
                    break
                time.sleep(FETCH_DELAY + random.random())
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        logger.info("arXiv ingestion done (inserted=%d, updated=%d)", inserted, updated)
