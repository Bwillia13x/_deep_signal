from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["system"])
_get_db_dependency = Depends(get_db)


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/readyz")
def readyz(db: Session = _get_db_dependency):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
