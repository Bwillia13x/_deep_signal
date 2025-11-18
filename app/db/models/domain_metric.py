from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DomainMetric(Base):
    __tablename__ = "domain_metrics"
    domain: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    window_end: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    repo_count: Mapped[int] = mapped_column(Integer, default=0)
    novelty_mu: Mapped[float | None] = mapped_column(Float, nullable=True)
    novelty_sigma: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum_mu: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum_sigma: Mapped[float | None] = mapped_column(Float, nullable=True)
    moat_mu: Mapped[float | None] = mapped_column(Float, nullable=True)
    moat_sigma: Mapped[float | None] = mapped_column(Float, nullable=True)
    scalability_mu: Mapped[float | None] = mapped_column(Float, nullable=True)
    scalability_sigma: Mapped[float | None] = mapped_column(Float, nullable=True)
