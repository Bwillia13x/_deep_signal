from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Paper(Base):
    __tablename__ = "papers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String(64))
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String()), nullable=True)
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    tsv: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    
    # Scoring fields
    moat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    moat_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scalability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    scalability_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attention_gap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    attention_gap_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    network_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    scoring_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
