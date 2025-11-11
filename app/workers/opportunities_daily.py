import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Opportunity, Paper, PaperRepoLink
from app.db.session import SessionLocal
from app.utils.vector import centroid, cosine_similarity, momentum_score

logger = logging.getLogger(__name__)
TOP_K_PER_DOMAIN = 5


def _selection_score(novelty: float, momentum: float) -> float:
    raw = 0.55 * novelty + 0.45 * momentum
    return max(0.0, min(1.0, raw))


def _related_repositories(session: Session, paper_id: int) -> Sequence[int]:
    rows = session.query(PaperRepoLink.repo_id).filter_by(paper_id=paper_id).all()
    return [row.repo_id for row in rows]


def main() -> None:
    session = SessionLocal()
    today = datetime.utcnow().date()
    week_of = today - timedelta(days=today.weekday())
    try:
        papers = (
            session.query(Paper)
            .filter(Paper.embedding.is_not(None), Paper.domain.is_not(None))
            .all()
        )
        domain_groups: dict[str, list[Paper]] = {}
        for paper in papers:
            domain = paper.domain or "other"
            domain_groups.setdefault(domain, []).append(paper)
        for domain, group in domain_groups.items():
            vectors = [paper.embedding for paper in group if paper.embedding]
            domain_centroid = centroid(vectors)
            enriched: list[tuple[float, float, float, Paper]] = []
            for paper in group:
                novelty = 0.0
                if paper.embedding and domain_centroid:
                    similarity = cosine_similarity(paper.embedding, domain_centroid)
                    novelty = max(0.0, min(1.0, 1 - similarity))
                momentum = momentum_score(paper.published_at)
                score = _selection_score(novelty, momentum)
                enriched.append((score, novelty, momentum, paper))
            enriched.sort(key=lambda item: item[0], reverse=True)
            session.query(Opportunity).filter_by(
                domain=domain, week_of=week_of
            ).delete()
            for rank, (score, novelty, momentum, paper) in enumerate(
                enriched[:TOP_K_PER_DOMAIN], start=1
            ):
                slug = (
                    f"{domain.lower().replace('.', '-')}-{week_of.isoformat()}-{rank}"
                )
                opportunity = Opportunity(
                    slug=slug,
                    domain=domain,
                    score=score,
                    component_scores={"novelty": novelty, "momentum": momentum},
                    key_papers=[paper.id],
                    related_repos=list(_related_repositories(session, paper.id)),
                    executive_summary=f"{paper.title} shows rising novelty in {domain}.",
                    investment_thesis="Track complementary partners and runway.",
                    week_of=week_of,
                )
                session.add(opportunity)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        logger.info("Opportunity run complete for week %s", week_of.isoformat())
