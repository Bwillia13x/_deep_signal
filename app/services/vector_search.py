from sqlalchemy import text
from sqlalchemy.orm import Session


def search_by_vector(db: Session, vec: list[float], k: int = 10):
    sql = text(
        """
        SELECT id, 1 - (embedding <=> :vec) AS similarity
        FROM papers
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vec
        LIMIT :k
    """
    )
    return db.execute(sql, {"vec": vec, "k": k}).mappings().all()
