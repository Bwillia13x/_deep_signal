from sqlalchemy import BigInteger, Date, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[float] = mapped_column(Float)
    component_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    key_papers: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    related_repos: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    investment_thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    week_of: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
