import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Opportunity, Paper, PaperRepoLink
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
TOP_K_PER_DOMAIN = 5
MIN_COMPOSITE_SCORE = 0.65
DEDUP_WEEKS = 4


def _get_recommendation_tier(score: float) -> str:
    """Determine recommendation tier based on composite score."""
    if score >= 0.8:
        return "STRONG_BUY"
    elif score >= 0.7:
        return "BUY"
    elif score >= 0.6:
        return "WATCH"
    else:
        return "MONITOR"


def _generate_executive_summary(paper: Paper) -> str:
    """Generate data-driven executive summary from paper evidence."""
    parts = [f"{paper.title}"]
    
    # Add novelty insight
    if paper.composite_score and paper.composite_score > 0.7:
        parts.append(f"shows exceptional potential (score: {paper.composite_score:.2f})")
    elif paper.composite_score and paper.composite_score > 0.65:
        parts.append(f"presents strong opportunity (score: {paper.composite_score:.2f})")
    
    # Add domain context
    if paper.domain:
        parts.append(f"in {paper.domain}")
    
    # Add moat insight
    if paper.moat_evidence and paper.moat_score and paper.moat_score > 0.5:
        barriers = paper.moat_evidence.get("total_barriers", 0)
        if barriers > 0:
            parts.append(f"with {barriers} identified barriers to replication")
    
    # Add scalability insight
    if paper.scalability_evidence and paper.scalability_score and paper.scalability_score > 0.5:
        signals = paper.scalability_evidence.get("positive_signals", 0)
        if signals > 0:
            parts.append(f"and {signals} manufacturing scalability indicators")
    
    return ". ".join(parts) + "."


def _generate_investment_thesis(paper: Paper) -> str:
    """Generate investment thesis from scoring evidence."""
    thesis_parts = []
    
    # Strengths
    strengths = []
    if paper.moat_score and paper.moat_score > 0.6:
        strengths.append("Strong barriers to entry")
    if paper.scalability_score and paper.scalability_score > 0.6:
        strengths.append("High manufacturing scalability")
    if paper.attention_gap_score and paper.attention_gap_score > 0.6:
        strengths.append("Undervalued opportunity (high quality, low attention)")
    
    if strengths:
        thesis_parts.append("Strengths: " + ", ".join(strengths))
    
    # Risks
    risks = []
    if paper.moat_score and paper.moat_score < 0.3:
        risks.append("Low barriers to competition")
    if paper.scalability_score and paper.scalability_score < 0.3:
        risks.append("Manufacturing challenges")
    if paper.network_score and paper.network_score < 0.3:
        risks.append("Limited research network")
    
    if risks:
        thesis_parts.append("Risks: " + ", ".join(risks))
    
    # Next steps
    thesis_parts.append("Next steps: Monitor complementary partners, assess technical feasibility, track commercial traction.")
    
    return " | ".join(thesis_parts)


def _related_repositories(session: Session, paper_id: int) -> Sequence[int]:
    rows = session.query(PaperRepoLink.repo_id).filter_by(paper_id=paper_id).all()
    return [row.repo_id for row in rows]


def _get_recently_selected_papers(session: Session, domain: str, week_of: datetime.date) -> set[int]:
    """Get paper IDs selected in the last DEDUP_WEEKS weeks."""
    cutoff_date = week_of - timedelta(weeks=DEDUP_WEEKS)
    recent_opps = session.query(Opportunity).filter(
        and_(
            Opportunity.domain == domain,
            Opportunity.week_of >= cutoff_date,
            Opportunity.week_of < week_of
        )
    ).all()
    
    paper_ids = set()
    for opp in recent_opps:
        if opp.key_papers:
            paper_ids.update(opp.key_papers)
    
    return paper_ids


def main() -> None:
    session = SessionLocal()
    today = datetime.utcnow().date()
    # Weekly freeze: Monday 00:00 UTC
    week_of = today - timedelta(days=today.weekday())
    
    try:
        papers = (
            session.query(Paper)
            .filter(
                Paper.embedding.is_not(None),
                Paper.domain.is_not(None),
                Paper.composite_score.is_not(None),
                Paper.composite_score >= MIN_COMPOSITE_SCORE
            )
            .all()
        )
        
        domain_groups: dict[str, list[Paper]] = {}
        for paper in papers:
            domain = paper.domain or "other"
            domain_groups.setdefault(domain, []).append(paper)
        
        for domain, group in domain_groups.items():
            # Get recently selected papers for deduplication
            recently_selected = _get_recently_selected_papers(session, domain, week_of)
            
            # Filter out recently selected papers
            candidates = [p for p in group if p.id not in recently_selected]
            
            # Sort by composite score
            candidates.sort(key=lambda p: p.composite_score or 0.0, reverse=True)
            
            # Clear existing opportunities for this week/domain
            session.query(Opportunity).filter_by(
                domain=domain, week_of=week_of
            ).delete()
            
            # Create top K opportunities
            for rank, paper in enumerate(candidates[:TOP_K_PER_DOMAIN], start=1):
                slug = (
                    f"{domain.lower().replace('.', '-')}-{week_of.isoformat()}-{rank}"
                )
                
                composite_score = paper.composite_score or 0.0
                recommendation = _get_recommendation_tier(composite_score)
                
                component_scores = {
                    "composite": composite_score,
                    "moat": paper.moat_score,
                    "scalability": paper.scalability_score,
                    "attention_gap": paper.attention_gap_score,
                    "network": paper.network_score,
                }
                
                opportunity = Opportunity(
                    slug=slug,
                    domain=domain,
                    score=composite_score,
                    component_scores=component_scores,
                    recommendation=recommendation,
                    key_papers=[paper.id],
                    related_repos=list(_related_repositories(session, paper.id)),
                    executive_summary=_generate_executive_summary(paper),
                    investment_thesis=_generate_investment_thesis(paper),
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
