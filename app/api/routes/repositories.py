from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models.repository import Repository
from app.db.schemas.repository import RepositoryOut
from app.db.session import get_db

router = APIRouter(prefix="/repositories", tags=["repositories"])
_get_db_dependency = Depends(get_db)


@router.get("", response_model=list[RepositoryOut])
def list_repositories(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = _get_db_dependency,
):
    return (
        db.query(Repository)
        .order_by(Repository.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
