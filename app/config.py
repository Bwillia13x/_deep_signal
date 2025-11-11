from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    port: int = Field(default=8000, alias="PORT")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/deeptech",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )
    embedding_dim: int = Field(default=384, alias="EMBEDDING_DIM")
    cors_origins: list[str] = Field(default=["*"], alias="CORS_ORIGINS")
    arxiv_categories: list[str] = Field(
        default_factory=lambda: ["cs.AI", "cs.LG"], alias="ARXIV_CATEGORIES"
    )
    arxiv_max_results: int = Field(default=25, alias="ARXIV_MAX_RESULTS")
    arxiv_lookback_days: int = Field(default=30, alias="ARXIV_LOOKBACK_DAYS")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_search_days: int = Field(default=30, alias="GITHUB_SEARCH_DAYS")
    prometheus_multiproc_dir: str = Field(
        default="/tmp/metrics", alias="PROMETHEUS_MULTIPROC_DIR"
    )

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_nested_delimiter = "__"


settings = Settings()  # type: ignore
