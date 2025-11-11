from datetime import date

from pydantic import BaseModel


class OpportunityOut(BaseModel):
    id: int
    slug: str
    domain: str | None = None
    score: float
    component_scores: dict[str, float] | None = None
    key_papers: list[int] | None = None
    related_repos: list[int] | None = None
    executive_summary: str | None = None
    investment_thesis: str | None = None
    week_of: date

    class Config:
        from_attributes = True
