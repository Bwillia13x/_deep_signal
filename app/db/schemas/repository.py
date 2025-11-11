from pydantic import BaseModel


class RepositoryOut(BaseModel):
    id: int
    full_name: str
    description: str | None = None
    language: str | None = None
    topics: list[str] | None = None
    stars: int
    forks: int
    open_issues: int
    deeptech_complexity_score: float | None = None
    velocity_score: float | None = None

    class Config:
        from_attributes = True
