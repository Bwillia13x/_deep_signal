from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models.paper import Paper
from app.db.schemas.paper import PaperOut
from app.db.session import get_db
from app.services.embeddings import EmbeddingService

router = APIRouter(prefix="/papers", tags=["papers"])
_get_db_dependency = Depends(get_db)


@router.get("", response_model=list[PaperOut])
def list_papers(
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = _get_db_dependency,
):
    query = db.query(Paper).order_by(Paper.id.desc())
    if q:
        query = query.filter(text("tsv @@ plainto_tsquery('english', :q)")).params(q=q)
    return query.limit(limit).offset(offset).all()


@router.get("/near")
def similar_papers(
    text_query: str | None = Query(None, description="Raw text to embed"),
    paper_id: int | None = Query(None, description="Use embedding from paper_id"),
    k: int = Query(10, ge=1, le=50),
    db: Session = _get_db_dependency,
):
    if not text_query and not paper_id:
        raise HTTPException(400, "Provide text_query or paper_id")
    if text_query:
        vec = EmbeddingService.get().embed(text_query)
    else:
        row = db.query(Paper.embedding).filter(Paper.id == paper_id).first()
        if not row or not row[0]:
            raise HTTPException(404, "paper_id not found or no embedding")
        vec = row[0]

    sql = text(
        """
        SELECT id, title, 1 - (embedding <=> :vec) AS similarity
        FROM papers
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vec
        LIMIT :k
    """
    )
    res = db.execute(sql, {"vec": vec, "k": k}).mappings().all()
    return [
        {"id": r["id"], "title": r["title"], "similarity": float(r["similarity"])}
        for r in res
    ]
