import logging
from datetime import datetime, timedelta
from statistics import mean, pstdev

from sqlalchemy import func

from app.db.models import DomainMetric, Paper, PaperRepoLink, Repository
from app.db.session import SessionLocal
from app.services.scoring import (
    calculate_attention_gap_score,
    calculate_composite_score,
    calculate_moat_score,
    calculate_network_score,
    calculate_scalability_score,
)
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
        
        # First pass: compute raw scores and collect domain statistics
        for domain, group in domain_groups.items():
            vectors = [paper.embedding for paper in group if paper.embedding]
            domain_centroid = centroid(vectors)
            novelty_scores: list[float] = []
            momentum_scores: list[float] = []
            moat_scores: list[float] = []
            scalability_scores: list[float] = []
            attention_raw_scores: list[float] = []
            network_scores: list[float] = []
            
            for paper in group:
                # Novelty score
                novelty = 0.0
                if paper.embedding and domain_centroid:
                    similarity = cosine_similarity(paper.embedding, domain_centroid)
                    novelty = max(0.0, min(1.0, 1 - similarity))
                novelty_scores.append(novelty)
                
                # Momentum score
                momentum = momentum_score(paper.published_at)
                momentum_scores.append(momentum)
                
                # Moat score
                moat, moat_evidence = calculate_moat_score(
                    paper.title,
                    paper.abstract,
                    paper.keywords
                )
                paper.moat_score = moat
                paper.moat_evidence = moat_evidence
                moat_scores.append(moat)
                
                # Scalability score
                scalability, scalability_evidence = calculate_scalability_score(
                    paper.title,
                    paper.abstract,
                    paper.keywords
                )
                paper.scalability_score = scalability
                paper.scalability_evidence = scalability_evidence
                scalability_scores.append(scalability)
                
                # Get repo stars for attention calculation
                repo_links = session.query(PaperRepoLink).filter_by(paper_id=paper.id).all()
                link_count = len(repo_links)
                repo_stars = 0
                if link_count > 0:
                    repo_ids = [link.repo_id for link in repo_links]
                    star_sum = session.query(func.sum(Repository.stars)).filter(
                        Repository.id.in_(repo_ids)
                    ).scalar()
                    repo_stars = int(star_sum) if star_sum else 0
                
                attention_raw_scores.append(repo_stars + link_count * 10)
                
                # Network score (simplified - just count authors for now)
                # In a real implementation, we'd parse authors from the paper
                # For now, use a placeholder
                network, network_evidence = calculate_network_score(authors=None)
                paper.network_score = network
                paper.network_evidence = network_evidence
                network_scores.append(network)
            
            # Calculate domain statistics for attention
            attention_mu = mean(attention_raw_scores) if attention_raw_scores else 0.0
            attention_sigma = pstdev(attention_raw_scores) if len(attention_raw_scores) > 1 else 0.0
            
            # Second pass: compute attention gap and composite scores
            for paper in group:
                # Get paper's attention data
                repo_links = session.query(PaperRepoLink).filter_by(paper_id=paper.id).all()
                link_count = len(repo_links)
                repo_stars = 0
                if link_count > 0:
                    repo_ids = [link.repo_id for link in repo_links]
                    star_sum = session.query(func.sum(Repository.stars)).filter(
                        Repository.id.in_(repo_ids)
                    ).scalar()
                    repo_stars = int(star_sum) if star_sum else 0
                
                # Attention gap score
                attention_gap, attention_evidence = calculate_attention_gap_score(
                    moat_score=paper.moat_score or 0.0,
                    scalability_score=paper.scalability_score or 0.0,
                    repo_stars=repo_stars,
                    link_count=link_count,
                    domain_mean_stars=attention_mu,
                    domain_std_stars=attention_sigma,
                )
                paper.attention_gap_score = attention_gap
                paper.attention_gap_evidence = attention_evidence
                
                # Composite score
                composite, metadata = calculate_composite_score(
                    novelty=novelty_scores[group.index(paper)],
                    momentum=momentum_scores[group.index(paper)],
                    attention_gap=attention_gap,
                    moat=paper.moat_score or 0.0,
                    scalability=paper.scalability_score or 0.0,
                    network=paper.network_score or 0.0,
                )
                paper.composite_score = composite
                paper.scoring_metadata = metadata
            
            # Store domain metrics
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
            metric.novelty_sigma = pstdev(novelty_scores) if len(novelty_scores) > 1 else 0.0
            metric.momentum_mu = mean(momentum_scores) if momentum_scores else 0.0
            metric.momentum_sigma = pstdev(momentum_scores) if len(momentum_scores) > 1 else 0.0
            metric.moat_mu = mean(moat_scores) if moat_scores else 0.0
            metric.moat_sigma = pstdev(moat_scores) if len(moat_scores) > 1 else 0.0
            metric.scalability_mu = mean(scalability_scores) if scalability_scores else 0.0
            metric.scalability_sigma = pstdev(scalability_scores) if len(scalability_scores) > 1 else 0.0
            metric.attention_mu = attention_mu
            metric.attention_sigma = attention_sigma
            metric.network_mu = mean(network_scores) if network_scores else 0.0
            metric.network_sigma = pstdev(network_scores) if len(network_scores) > 1 else 0.0
        
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
