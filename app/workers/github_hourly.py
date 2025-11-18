import logging
import math
import random
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models.http_cache import HttpCache
from app.db.models.repository import Repository
from app.db.session import SessionLocal
from app.lib.http import HttpClient
from app.metrics import (
    GITHUB_ERRORS,
    GITHUB_RATE_LIMIT_HITS,
    GITHUB_REPOS_PROCESSED,
    GITHUB_REQUESTS_TOTAL,
)

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
PAGE_LIMIT = 2
PER_PAGE = 30
RATE_LIMIT_SECONDS = 2.0


def _cache_key(url: str, params: dict[str, str]) -> str:
    if not params:
        return url
    return f"{url}?{urlencode(sorted(params.items()))}"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _github_headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json,application/vnd.github.mercy-preview+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return headers


def _compute_velocity(
    stars: int, pushed_at: datetime | None
) -> tuple[float, dict[str, float]]:
    now = datetime.utcnow()
    recency_days = (now - pushed_at).days if pushed_at else 365
    recency_score = max(0.0, min(1.0, 1 - recency_days / 180))
    star_score = min(1.0, math.log1p(stars) / math.log1p(2000))
    velocity = 0.6 * recency_score + 0.4 * star_score
    return velocity, {
        "recency_days": recency_days,
        "recency_score": recency_score,
        "star_score": star_score,
    }


def _compute_complexity(star_score: float, open_issues: int) -> float:
    issue_penalty = min(0.25, open_issues / 400)
    complexity = 0.35 + 0.5 * star_score - issue_penalty
    return max(0.0, min(1.0, complexity))


def _persist_cache(
    session: Session, key: str, response, params: dict[str, str]
) -> None:
    cache = session.query(HttpCache).filter_by(url=key).one_or_none()
    if not cache:
        cache = HttpCache(url=key)
        session.add(cache)
    cache.etag = response.headers.get("ETag")
    cache.last_modified = response.headers.get("Last-Modified")
    cache.status_code = response.status_code
    cache.meta = {"params": params}
    session.flush()


def _upsert_repository(session: Session, data: dict, query: str) -> str:
    full_name = data.get("full_name")
    if not full_name:
        GITHUB_ERRORS.labels(error_type="missing_full_name").inc()
        return "skipped"
    
    try:
        repo = session.query(Repository).filter_by(full_name=full_name).one_or_none()
        created_at = _parse_datetime(data.get("created_at"))
        pushed_at = _parse_datetime(data.get("pushed_at"))
        stars = data.get("stargazers_count", 0) or 0
        forks = data.get("forks_count", 0) or 0
        open_issues = data.get("open_issues_count", 0) or 0
        velocity, velocity_evidence = _compute_velocity(stars, pushed_at)
        star_score = min(1.0, math.log1p(stars) / math.log1p(2000))
        complexity = _compute_complexity(star_score, open_issues)
        values = {
            "description": data.get("description"),
            "language": data.get("language"),
            "topics": data.get("topics") or [],
            "stars": stars,
            "forks": forks,
            "open_issues": open_issues,
            "created_at": created_at,
            "pushed_at": pushed_at,
            "deeptech_complexity_score": complexity,
            "velocity_score": velocity,
            "velocity_evidence": velocity_evidence,
        }
        if not repo:
            repo = Repository(full_name=full_name, **values)
            session.add(repo)
            GITHUB_REPOS_PROCESSED.labels(query=query, status="inserted").inc()
            return "insert"
        
        updated = False
        for field, value in values.items():
            if getattr(repo, field) != value:
                setattr(repo, field, value)
                updated = True
        
        if updated:
            GITHUB_REPOS_PROCESSED.labels(query=query, status="updated").inc()
            return "update"
        else:
            GITHUB_REPOS_PROCESSED.labels(query=query, status="unchanged").inc()
            return "unchanged"
    except Exception as e:
        logger.error("Error upserting repository %s: %s", full_name, str(e))
        GITHUB_ERRORS.labels(error_type="upsert_error").inc()
        raise


def main() -> None:
    if not settings.github_token:
        logger.warning("Skipping GitHub ingestion: GITHUB_TOKEN not configured")
        return
    client = HttpClient()
    since = (
        (datetime.utcnow() - timedelta(days=settings.github_search_days))
        .date()
        .isoformat()
    )
    headers = _github_headers()
    session = SessionLocal()
    inserted = 0
    updated = 0
    
    try:
        for category in settings.arxiv_categories:
            for page in range(1, PAGE_LIMIT + 1):
                params = {
                    "q": f"{category} in:name,description pushed:>={since}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": str(PER_PAGE),
                    "page": str(page),
                }
                cache_key = _cache_key(GITHUB_SEARCH_URL, params)
                cache = session.query(HttpCache).filter_by(url=cache_key).one_or_none()
                
                try:
                    resp = client.get(
                        GITHUB_SEARCH_URL,
                        params=params,
                        etag=cache.etag if cache else None,
                        last_modified=cache.last_modified if cache else None,
                        extra_headers=headers,
                    )
                    GITHUB_REQUESTS_TOTAL.labels(
                        endpoint="search/repositories", status=resp.status_code
                    ).inc()
                    
                    if resp.status_code == 304:
                        _persist_cache(session, cache_key, resp, params)
                        continue
                    
                    if resp.status_code == 403:
                        # Rate limit hit
                        GITHUB_RATE_LIMIT_HITS.inc()
                        logger.warning("GitHub rate limit hit, stopping for this category")
                        break
                    
                    if resp.status_code != 200:
                        logger.warning(
                            "GitHub search error %d: %s", resp.status_code, resp.text[:200]
                        )
                        GITHUB_ERRORS.labels(error_type="http_error").inc()
                        break
                    
                    payload = resp.json()
                    items = payload.get("items", [])
                    if not items:
                        break
                    
                    for item in items:
                        status = _upsert_repository(session, item, category)
                        if status == "insert":
                            inserted += 1
                        elif status == "update":
                            updated += 1
                    
                    _persist_cache(session, cache_key, resp, params)
                    session.commit()
                    time.sleep(RATE_LIMIT_SECONDS + random.random())
                    
                except Exception as e:
                    logger.error("GitHub request exception for category %s: %s", category, str(e))
                    GITHUB_REQUESTS_TOTAL.labels(endpoint="search/repositories", status="error").inc()
                    GITHUB_ERRORS.labels(error_type="request_exception").inc()
                    break
                    
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        logger.info("GitHub ingestion completed (inserted=%d, updated=%d)", inserted, updated)
