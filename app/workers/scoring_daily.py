import logging
from datetime import datetime, timedelta
from statistics import mean, pstdev

from app.db.models import DomainMetric, Paper, PaperRepoLink
from app.db.session import SessionLocal
from app.utils.vector import centroid, cosine_similarity, momentum_score

logger = logging.getLogger(__name__)
WINDOW_DAYS = 7


def main() -> None:
    session = SessionLocal()
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(days=WINDOW_DAYS)
    try:
        papers = (
            session.query(Paper)
            .filter(Paper.embedding.is_not(None), Paper.domain.is_not(None))
            .all()
        )
        domain_groups: dict[str, list[Paper]] = {}
        for paper in papers:
            domain = paper.domain or "unknown"
            domain_groups.setdefault(domain, []).append(paper)
        for domain, group in domain_groups.items():
            vectors = [paper.embedding for paper in group if paper.embedding]
            domain_centroid = centroid(vectors)
            novelty_scores: list[float] = []
            momentum_scores: list[float] = []
            for paper in group:
                novelty = 0.0
                if paper.embedding and domain_centroid:
                    similarity = cosine_similarity(paper.embedding, domain_centroid)
                    novelty = max(0.0, min(1.0, 1 - similarity))
                momentum = momentum_score(paper.published_at)
                novelty_scores.append(novelty)
                momentum_scores.append(momentum)
            repo_ids = {
                row.repo_id
                for row in (
                    session.query(PaperRepoLink)
                    .join(Paper, PaperRepoLink.paper_id == Paper.id)
                    .filter(Paper.domain == domain)
                )
            }
            metric = (
                session.query(DomainMetric)
                .filter_by(
                    domain=domain, window_start=window_start, window_end=window_end
                )
                .one_or_none()
            )
            if not metric:
                metric = DomainMetric(
                    domain=domain, window_start=window_start, window_end=window_end
                )
                session.add(metric)
            metric.paper_count = len(group)
            metric.repo_count = len(repo_ids)
            metric.novelty_mu = mean(novelty_scores) if novelty_scores else 0.0
            metric.novelty_sigma = (
                pstdev(novelty_scores) if len(novelty_scores) > 1 else 0.0
            )
            metric.momentum_mu = mean(momentum_scores) if momentum_scores else 0.0
            metric.momentum_sigma = (
                pstdev(momentum_scores) if len(momentum_scores) > 1 else 0.0
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        logger.info(
            "Scoring run complete for window %s - %s",
            window_start.isoformat(),
            window_end.isoformat(),
        )
