from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models.opportunity import Opportunity
from app.db.schemas.opportunity import OpportunityOut
from app.db.session import get_db

router = APIRouter(prefix="/opportunities", tags=["opportunities"])
_get_db_dependency = Depends(get_db)


@router.get("", response_model=list[OpportunityOut])
def list_opportunities(
    domain: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = _get_db_dependency,
):
    query = db.query(Opportunity).order_by(
        Opportunity.week_of.desc(), Opportunity.score.desc()
    )
    if domain:
        query = query.filter(Opportunity.domain == domain)
    return query.limit(limit).all()
