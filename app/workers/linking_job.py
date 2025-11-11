import logging
import re

from sqlalchemy.orm import Session

from app.db.models.paper import Paper
from app.db.models.paper_repo_link import PaperRepoLink
from app.db.models.repository import Repository
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
MAX_MATCHES = 3
MIN_CONFIDENCE = 0.4
TOKEN_PATTERN = re.compile(r"\w{3,}")


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _upsert_link(
    session: Session, paper_id: int, repo_id: int, confidence: float, evidence: dict
) -> None:
    link = (
        session.query(PaperRepoLink)
        .filter_by(paper_id=paper_id, repo_id=repo_id)
        .one_or_none()
    )
    if link:
        if confidence > link.confidence:
            link.confidence = confidence
            link.evidence = evidence
        return
    session.add(
        PaperRepoLink(
            paper_id=paper_id, repo_id=repo_id, confidence=confidence, evidence=evidence
        )
    )


def main() -> None:
    session = SessionLocal()
    created = 0
    updated = 0
    try:
        papers = session.query(Paper).all()
        repositories = session.query(Repository).all()
        repo_tokens_map = {
            repo.id: _tokens(repo.full_name) | _tokens(repo.description)
            for repo in repositories
        }
        for paper in papers:
            if not (paper.keywords or paper.title):
                continue
            paper_tokens = _tokens(paper.title) | {
                kw.lower() for kw in (paper.keywords or [])
            }
            matches: list[tuple[float, int, dict]] = []
            for repo in repositories:
                repo_topics = {topic.lower() for topic in (repo.topics or [])}
                overlap = paper_tokens & repo_topics
                title_overlap = bool(paper_tokens & repo_tokens_map.get(repo.id, set()))
                confidence = 0.0
                if overlap:
                    confidence = min(0.9, 0.45 + 0.1 * len(overlap))
                if title_overlap:
                    confidence = max(confidence, 0.4)
                if confidence < MIN_CONFIDENCE:
                    continue
                evidence = {
                    "matching_topics": sorted(overlap),
                    "title_overlap": title_overlap,
                    "repo_topics": sorted(repo_topics),
                }
                matches.append((confidence, repo.id, evidence))
            matches.sort(key=lambda row: row[0], reverse=True)
            for confidence, repo_id, evidence in matches[:MAX_MATCHES]:
                before = (
                    session.query(PaperRepoLink)
                    .filter_by(paper_id=paper.id, repo_id=repo_id)
                    .one_or_none()
                )
                _upsert_link(session, paper.id, repo_id, confidence, evidence)
                if before:
                    updated += 1
                else:
                    created += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        logger.info("Linking done (created=%d, updated=%d)", created, updated)
