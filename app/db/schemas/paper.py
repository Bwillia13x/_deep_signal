from pydantic import BaseModel


class PaperOut(BaseModel):
    id: int
    external_id: str
    title: str
    abstract: str | None = None
    domain: str | None = None
    keywords: list[str] | None = None

    class Config:
        from_attributes = True
