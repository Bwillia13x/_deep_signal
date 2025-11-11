from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
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
