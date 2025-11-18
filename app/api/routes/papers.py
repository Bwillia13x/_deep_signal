from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from app.db.models.paper import Paper
from app.db.schemas.paper import PaperOut
from app.db.session import get_db
from app.services.embeddings import EmbeddingService

router = APIRouter(prefix="/papers", tags=["papers"])
_get_db_dependency = Depends(get_db)


@router.get("", response_model=list[PaperOut])
def list_papers(
    q: str | None = Query(None, description="Full-text search query"),
    domain: str | None = Query(None, description="Filter by domain"),
    min_composite_score: float | None = Query(None, ge=0.0, le=1.0, description="Minimum composite score"),
    min_moat_score: float | None = Query(None, ge=0.0, le=1.0, description="Minimum moat score"),
    min_scalability_score: float | None = Query(None, ge=0.0, le=1.0, description="Minimum scalability score"),
    sort_by: str = Query("id", description="Sort by: id, composite_score, published_at"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = _get_db_dependency,
):
    """
    List papers with advanced filtering and sorting.
    
    - **q**: Full-text search on title and abstract
    - **domain**: Filter by specific domain
    - **min_composite_score**: Minimum composite score threshold
    - **min_moat_score**: Minimum moat score threshold
    - **min_scalability_score**: Minimum scalability score threshold
    - **sort_by**: Sort field (id, composite_score, published_at)
    - **limit**: Results per page (1-100)
    - **offset**: Pagination offset
    """
    query = db.query(Paper)
    
    # Apply filters
    filters = []
    if q:
        filters.append(text("tsv @@ plainto_tsquery('english', :q)"))
    if domain:
        filters.append(Paper.domain == domain)
    if min_composite_score is not None:
        filters.append(Paper.composite_score >= min_composite_score)
    if min_moat_score is not None:
        filters.append(Paper.moat_score >= min_moat_score)
    if min_scalability_score is not None:
        filters.append(Paper.scalability_score >= min_scalability_score)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Apply text search params if needed
    if q:
        query = query.params(q=q)
    
    # Apply sorting
    if sort_by == "composite_score":
        query = query.order_by(Paper.composite_score.desc().nullslast())
    elif sort_by == "published_at":
        query = query.order_by(Paper.published_at.desc().nullslast())
    else:
        query = query.order_by(Paper.id.desc())
    
    return query.limit(limit).offset(offset).all()


@router.get("/near")
def similar_papers(
    text_query: str | None = Query(None, description="Raw text to embed"),
    paper_id: int | None = Query(None, description="Use embedding from paper_id"),
    k: int = Query(10, ge=1, le=50, description="Number of similar papers to return"),
    db: Session = _get_db_dependency,
):
    """
    Find similar papers using vector similarity search.
    
    Provide either text_query or paper_id:
    - **text_query**: Raw text to embed and search
    - **paper_id**: Use embedding from existing paper
    - **k**: Number of results (1-50)
    """
    if not text_query and not paper_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_parameter",
                "message": "Provide either text_query or paper_id",
                "fields": ["text_query", "paper_id"]
            }
        )
    
    if text_query:
        vec = EmbeddingService.get().embed(text_query)
    else:
        row = db.query(Paper.embedding).filter(Paper.id == paper_id).first()
        if not row or not row[0]:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"Paper with id {paper_id} not found or has no embedding",
                    "paper_id": paper_id
                }
            )
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
