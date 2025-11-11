Below is a production-ready repo scaffold with structure, core files, and minimal code to run API + Postgres (pgvector) locally and in CI. It includes FastAPI app, Alembic migrations, Prometheus metrics, workers skeleton, Docker, Compose, GitHub Actions, pre-commit, and Kubernetes manifests.

Repository tree (overview)

- .env.example
- .gitignore
- .editorconfig
- .pre-commit-config.yaml
- ruff.toml
- mypy.ini
- README.md
- Makefile
- docker-compose.yml
- Dockerfile.api
- Dockerfile.worker
- requirements/
  - base.txt
  - api.txt
  - worker.txt
  - dev.txt
- app/
  - __init__.py
  - version.py
  - main.py
  - config.py
  - logging_config.py
  - metrics.py
  - middleware/
    - __init__.py
    - request_id.py
  - api/
    - __init__.py
    - deps.py
    - routes/
      - __init__.py
      - health.py
      - papers.py
      - repositories.py
      - opportunities.py
  - db/
    - __init__.py
    - base.py
    - session.py
    - models/
      - __init__.py
      - paper.py
      - repository.py
      - paper_repo_link.py
      - domain_metric.py
      - opportunity.py
      - http_cache.py
    - schemas/
      - __init__.py
      - paper.py
      - repository.py
      - opportunity.py
    - crud/
      - __init__.py
      - papers.py
      - repositories.py
      - opportunities.py
  - services/
    - __init__.py
    - embeddings.py
    - vector_search.py
    - keyword_domain.py
  - workers/
    - __init__.py
    - arxiv_hourly.py
    - github_hourly.py
    - scoring_daily.py
    - linking_job.py
    - opportunities_daily.py
  - lib/
    - __init__.py
    - http.py
- alembic.ini
- alembic/
  - env.py
  - script.py.mako
  - versions/
    - 001_initial_schema.py
- tests/
  - conftest.py
  - test_api_health.py
  - test_db_migrations.py
- .github/
  - workflows/
    - ci.yml
- deploy/
  - k8s/
    - api-deployment.yaml
    - api-service.yaml
    - api-ingress.yaml
    - worker-cron-arxiv.yaml
    - worker-cron-github.yaml
    - worker-cron-scoring.yaml
    - worker-cron-opportunities.yaml
  - monitoring/
    - prometheus.yml
    - grafana/
      - provisioning/
        - datasources/
          - prometheus.yaml
        - dashboards/
          - deeptech-radar-overview.json
- scripts/
  - wait-for-db.sh
  - seed_dev_data.py

Key files (contents)

.env.example
APP_ENV=dev
LOG_LEVEL=INFO
PORT=8000
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/deeptech
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIM=384
CORS_ORIGINS=<http://localhost:3000>
GITHUB_TOKEN=REPLACE_ME
ARXIV_CATEGORIES=cs.AI,cs.LG
PROMETHEUS_MULTIPROC_DIR=/tmp/metrics

.gitignore
__pycache__/
*.pyc
*.pyo
.env
.venv/
.pytest_cache/
.coverage
dist/
build/
*.egg-info/
.DS_Store
logs/
.prom/
grafana-data/
.idea/
.vscode/

.editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

.pre-commit-config.yaml
repos:

- repo: <https://github.com/astral-sh/ruff-pre-commit>
  rev: v0.6.9
  hooks:
  - id: ruff
      args: [--fix]
- repo: <https://github.com/psf/black>
  rev: 24.10.0
  hooks:
  - id: black
- repo: <https://github.com/pycqa/isort>
  rev: 5.13.2
  hooks:
  - id: isort
      args: [--profile=black]
- repo: <https://github.com/pre-commit/pre-commit-hooks>
  rev: v4.6.0
  hooks:
  - id: trailing-whitespace
  - id: end-of-file-fixer
- repo: <https://github.com/PyCQA/bandit>
  rev: 1.7.10
  hooks:
  - id: bandit
      args: ["-lll","-q","-x","tests"]

ruff.toml
line-length = 100
target-version = "py311"
select = ["E","F","I","B","UP","N","SIM","C4","RUF"]
ignore = ["E501"]

mypy.ini
[mypy]
python_version = 3.11
strict = False
ignore_missing_imports = True
warn_unused_ignores = True
warn_redundant_casts = True
warn_unused_configs = True
exclude = (alembic/|tests/)

Makefile
PY=python3
PIP=pip

export PYTHONPATH := $(shell pwd)

.DEFAULT_GOAL := help

help:
 @echo "make setup       - install dev deps"
 @echo "make up          - start dev stack (api, db, prometheus, grafana)"
 @echo "make down        - stop dev stack"
 @echo "make migrate     - alembic upgrade head"
 @echo "make revision    - alembic revision -m 'msg'"
 @echo "make fmt         - format code"
 @echo "make lint        - ruff lint"
 @echo "make typecheck   - mypy"
 @echo "make test        - pytest"
 @echo "make api         - run api locally"
 @echo "make seed        - seed sample data"

setup:
 $(PIP) install -r requirements/dev.txt
 pre-commit install

up:
 docker-compose up -d --build
 @scripts/wait-for-db.sh db 5432
 docker-compose exec api alembic upgrade head

down:
 docker-compose down -v

migrate:
 alembic upgrade head

revision:
 alembic revision -m "$(m)"

fmt:
 black .
 isort .
 ruff check --fix .

lint:
 ruff check .

typecheck:
 mypy .

test:
 pytest -q

api:
 uvicorn app.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

seed:
 $(PY) scripts/seed_dev_data.py

docker-compose.yml
version: "3.9"
services:
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: deeptech
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d deeptech"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - pgdata:/var/lib/postgresql/data

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    env_file: .env
    environment:
      DATABASE_URL: ${DATABASE_URL}
      PROMETHEUS_MULTIPROC_DIR: /tmp/metrics
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  prometheus:
    image: prom/prometheus:v2.55.1
    volumes:
      - ./deploy/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:11.2.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./deploy/monitoring/grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"

volumes:
  pgdata:
  grafana-data:

Dockerfile.api
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements/base.txt requirements/api.txt ./
RUN pip install -r api.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]

Dockerfile.worker
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements/base.txt requirements/worker.txt ./
RUN pip install -r worker.txt
COPY . .
CMD ["python","-m","app.workers.arxiv_hourly"]

requirements/base.txt
fastapi==0.115.2
uvicorn[standard]==0.32.0
pydantic==2.9.2
sqlalchemy==2.0.36
psycopg[binary]==3.2.3
pgvector==0.3.4
alembic==1.13.3
prometheus-client==0.21.0
httpx==0.27.2
python-dotenv==1.0.1
orjson==3.10.7

requirements/api.txt
-r base.txt

requirements/worker.txt
-r base.txt
sentence-transformers==3.2.1
torch==2.4.1
pypdf==5.0.1
rapidfuzz==3.9.7

requirements/dev.txt
-r api.txt
pytest==8.3.3
pytest-cov==5.0.0
pre-commit==4.0.1
requests-mock==1.12.1
mypy==1.13.0
ruff==0.6.9
black==24.10.0
isort==5.13.2

alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = ${DATABASE_URL}

[post_write_hooks]
hooks = lint

[lint]
type = console_scripts
entrypoint = ruff
options = "check --fix"

alembic/env.py
from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.base import Base  # noqa: F401  (import models via Base.metadata)
from app.db.models import paper, repository, paper_repo_link, domain_metric, opportunity, http_cache  # noqa

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
DATABASE_URL = os.getenv("DATABASE_URL")

def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "papers",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(128), nullable=False, unique=True),
        sa.Column("doi", sa.String(255), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("domain", sa.String(64), nullable=True, index=True),
        sa.Column("keywords", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("tsv", sa.dialects.postgresql.TSVECTOR, nullable=True),
    )
    op.create_index("ix_papers_embedding_hnsw", "papers", ["embedding"], postgresql_using="hnsw")
    op.create_index("ix_papers_tsv", "papers", ["tsv"], postgresql_using="gin")
    op.execute("""
        CREATE TRIGGER papers_tsv_update BEFORE INSERT OR UPDATE
        ON papers FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(tsv, 'pg_catalog.english', title, abstract)
    """)

    op.create_table(
        "repositories",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("full_name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("language", sa.String(64), nullable=True, index=True),
        sa.Column("topics", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("stars", sa.Integer, nullable=False, server_default="0"),
        sa.Column("forks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("open_issues", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deeptech_complexity_score", sa.Float, nullable=True),
        sa.Column("velocity_score", sa.Float, nullable=True),
        sa.Column("velocity_evidence", sa.JSON, nullable=True),
    )

    op.create_table(
        "paper_repo_links",
        sa.Column("paper_id", sa.BigInteger, sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("repo_id", sa.BigInteger, sa.ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "domain_metrics",
        sa.Column("domain", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("window_end", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("paper_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("repo_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("novelty_mu", sa.Float),
        sa.Column("novelty_sigma", sa.Float),
        sa.Column("momentum_mu", sa.Float),
        sa.Column("momentum_sigma", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "opportunities",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("domain", sa.String(64), nullable=True, index=True),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("component_scores", sa.JSON, nullable=True),
        sa.Column("key_papers", sa.ARRAY(sa.BigInteger), nullable=True),
        sa.Column("related_repos", sa.ARRAY(sa.BigInteger), nullable=True),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("investment_thesis", sa.Text, nullable=True),
        sa.Column("week_of", sa.Date, nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "http_cache",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("url", sa.Text, nullable=False, unique=True),
        sa.Column("etag", sa.String(255)),
        sa.Column("last_modified", sa.String(255)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status_code", sa.Integer),
        sa.Column("meta", sa.JSON),
    )

def downgrade() -> None:
    op.drop_table("http_cache")
    op.drop_table("opportunities")
    op.drop_table("domain_metrics")
    op.drop_table("paper_repo_links")
    op.drop_table("repositories")
    op.execute("DROP TRIGGER IF EXISTS papers_tsv_update ON papers")
    op.drop_index("ix_papers_tsv")
    op.drop_index("ix_papers_embedding_hnsw")
    op.drop_table("papers")

app/version.py
__all__ = ["__version__"]
__version__ = "0.1.0"

app/config.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    port: int = Field(default=8000, alias="PORT")
    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/deeptech", alias="DATABASE_URL")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=384, alias="EMBEDDING_DIM")
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_nested_delimiter = "__"

settings = Settings()  # type: ignore

app/logging_config.py
import logging
import sys
import json
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data)

def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

app/metrics.py
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("api_requests_total", "API requests", ["path","method","status"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "API latency", ["path","method"])

app/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id", str(uuid.uuid4()))
        response: Response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response

app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app/db/models/paper.py
from sqlalchemy import BigInteger, DateTime, Text, String, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import TSVECTOR, ARRAY
from pgvector.sqlalchemy import Vector
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
    ingested_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    tsv: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

app/db/models/repository.py
from sqlalchemy import BigInteger, DateTime, Text, String, Integer, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY
from app.db.base import Base

class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(64))
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(String()))
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[DateTime | None]
    pushed_at: Mapped[DateTime | None]
    ingested_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deeptech_complexity_score: Mapped[float | None]
    velocity_score: Mapped[float | None]
    velocity_evidence: Mapped[dict | None]

app/db/models/paper_repo_link.py
from sqlalchemy import BigInteger, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class PaperRepoLink(Base):
    __tablename__ = "paper_repo_links"
    paper_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[dict | None]
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

app/db/models/domain_metric.py
from sqlalchemy import String, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class DomainMetric(Base):
    __tablename__ = "domain_metrics"
    domain: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[DateTime] = mapped_column(DateTime(timezone=True), primary_key=True)
    window_end: Mapped[DateTime] = mapped_column(DateTime(timezone=True), primary_key=True)
    paper_count: Mapped[int]
    repo_count: Mapped[int]
    novelty_mu: Mapped[float | None]
    novelty_sigma: Mapped[float | None]
    momentum_mu: Mapped[float | None]
    momentum_sigma: Mapped[float | None]

app/db/models/opportunity.py
from sqlalchemy import BigInteger, Date, DateTime, Float, Text, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    domain: Mapped[str | None] = mapped_column(String(64))
    score: Mapped[float]
    component_scores: Mapped[dict | None] = mapped_column(JSONB)
    key_papers: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    related_repos: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    executive_summary: Mapped[str | None] = mapped_column(Text)
    investment_thesis: Mapped[str | None] = mapped_column(Text)
    week_of: Mapped[Date]
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

app/db/models/http_cache.py
from sqlalchemy import BigInteger, Text, String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class HttpCache(Base):
    __tablename__ = "http_cache"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True)
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    fetched_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status_code: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict | None]

app/db/schemas/paper.py
from pydantic import BaseModel
from typing import Optional, List

class PaperOut(BaseModel):
    id: int
    external_id: str
    title: str
    abstract: Optional[str] = None
    domain: Optional[str] = None
    keywords: Optional[List[str]] = None
    class Config:
        from_attributes = True

app/api/routes/health.py
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter(tags=["system"])

@router.get("/healthz")
def healthz():
    return {"status": "ok"}

@router.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}

app/api/routes/papers.py
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.db.models.paper import Paper
from app.db.schemas.paper import PaperOut
from app.services.embeddings import EmbeddingService

router = APIRouter(prefix="/papers", tags=["papers"])

@router.get("", response_model=list[PaperOut])
def list_papers(
    q: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Paper).order_by(Paper.id.desc())
    if q:
        query = query.filter(text("tsv @@ plainto_tsquery('english', :q)")).params(q=q)
    return query.limit(limit).offset(offset).all()

@router.get("/near")
def similar_papers(
    text_query: Optional[str] = Query(None, description="Raw text to embed"),
    paper_id: Optional[int] = Query(None, description="Use embedding from paper_id"),
    k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if not text_query and not paper_id:
        raise HTTPException(400, "Provide text_query or paper_id")
    if text_query:
        vec = EmbeddingService.get().embed(text_query)
    else:
        row = db.query(Paper.embedding).filter(Paper.id == paper_id).first()
        if not row or not row[0]:
            raise HTTPException(404, "paper_id not found or no embedding")
        vec = row[0]

    sql = text("""
        SELECT id, title, 1 - (embedding <=> :vec) AS similarity
        FROM papers
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vec
        LIMIT :k
    """)
    res = db.execute(sql, {"vec": vec, "k": k}).mappings().all()
    return [{"id": r["id"], "title": r["title"], "similarity": float(r["similarity"])} for r in res]

app/api/routes/repositories.py
from fastapi import APIRouter
router = APIRouter(prefix="/repositories", tags=["repositories"])
@router.get("")
def list_repositories():
    return []

app/api/routes/opportunities.py
from fastapi import APIRouter
router = APIRouter(prefix="/opportunities", tags=["opportunities"])
@router.get("")
def list_opportunities():
    return []

app/api/deps.py
from fastapi import Header

def get_request_id(x_request_id: str | None = Header(default=None)):
    return x_request_id

app/lib/http.py
import httpx
import time
from typing import Optional

class HttpClient:
    def __init__(self, timeout=15.0):
        self.client = httpx.Client(timeout=timeout, headers={"user-agent": "deeptech-radar/0.1"})
    def get(self, url: str, etag: Optional[str] = None, last_modified: Optional[str] = None):
        headers = {}
        if etag: headers["If-None-Match"] = etag
        if last_modified: headers["If-Modified-Since"] = last_modified
        backoff = 1.0
        for attempt in range(5):
            resp = self.client.get(url, headers=headers)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff)
                backoff *= 2
                continue
            return resp
        return resp

app/services/embeddings.py
from __future__ import annotations
import threading
from typing import List
import math
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None  # type: ignore

from app.config import settings

class EmbeddingService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.dim = settings.embedding_dim
        self._model = SentenceTransformer(settings.embedding_model) if SentenceTransformer else None

    @classmethod
    def get(cls) -> "EmbeddingService":
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = EmbeddingService()
        return cls._instance

    def embed(self, text: str) -> List[float]:
        if not self._model:
            # Dev fallback: zero vector
            return [0.0] * self.dim
        vec = self._model.encode(text, normalize_embeddings=True)
        # Ensure list[float]
        return [float(x) for x in vec.tolist()] if hasattr(vec, "tolist") else list(vec)

app/services/vector_search.py
from sqlalchemy import text
from sqlalchemy.orm import Session

def search_by_vector(db: Session, vec: list[float], k: int = 10):
    sql = text("""
        SELECT id, 1 - (embedding <=> :vec) AS similarity
        FROM papers
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vec
        LIMIT :k
    """)
    return db.execute(sql, {"vec": vec, "k": k}).mappings().all()

app/main.py
import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from app.config import settings
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.papers import router as papers_router
from app.api.routes.repositories import router as repos_router
from app.api.routes.opportunities import router as opp_router

app = FastAPI(title="DeepTech Radar", version="0.1.0")

configure_logging(settings.log_level)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(papers_router)
app.include_router(repos_router)
app.include_router(opp_router)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

scripts/wait-for-db.sh
# !/usr/bin/env sh
set -e
host="$1"
port="$2"
until nc -z "$host" "$port"; do
  echo "Waiting for $host:$port..."
  sleep 1
done
echo "DB is up"

tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

tests/test_api_health.py
def test_health(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

tests/test_db_migrations.py
import os
from alembic.config import Config
from alembic import command

def test_alembic_upgrade_downgrade(tmp_path):
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

.github/workflows/ci.yml
name: ci
on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  build-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: deeptech
        ports: ["5432:5432"]
        options: >-
          --health-cmd="pg_isready -U postgres -d deeptech"
          --health-interval=5s
          --health-timeout=5s
          --health-retries=10
    env:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/deeptech
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Install deps
      run: |
        pip install -r requirements/dev.txt
    - name: Lint
      run: |
        ruff check .
        black --check .
        isort --check-only .
    - name: Type check
      run: mypy .
    - name: Tests
      run: pytest -q

deploy/monitoring/prometheus.yml
global:
  scrape_interval: 15s
scrape_configs:

- job_name: "api"
    static_configs:
  - targets: ["api:8000"]

deploy/monitoring/grafana/provisioning/datasources/prometheus.yaml
apiVersion: 1
datasources:

- name: Prometheus
  type: prometheus
  access: proxy
  url: <http://prometheus:9090>
  isDefault: true

deploy/k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deeptech-api
spec:
  replicas: 2
  selector:
    matchLabels: { app: deeptech-api }
  template:
    metadata:
      labels: { app: deeptech-api }
    spec:
      containers:
      - name: api
        image: ghcr.io/yourorg/deeptech-api:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef: { name: deeptech-secrets, key: DATABASE_URL }
        - name: PROMETHEUS_MULTIPROC_DIR
          value: /tmp/metrics
        ports: [{ containerPort: 8000 }]
        readinessProbe:
          httpGet: { path: /readyz, port: 8000 }
        livenessProbe:
          httpGet: { path: /healthz, port: 8000 }
        resources:
          requests: { cpu: "100m", memory: "256Mi" }
          limits: { cpu: "500m", memory: "512Mi" }

deploy/k8s/api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: deeptech-api
spec:
  selector: { app: deeptech-api }
  ports:
    - name: http
      port: 80
      targetPort: 8000

deploy/k8s/api-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: deeptech-api
spec:
  rules:
    - host: deeptech.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: deeptech-api
                port:
                  number: 80

deploy/k8s/worker-cron-arxiv.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: arxiv-hourly
spec:
  schedule: "15 ** **"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: arxiv-worker
            image: ghcr.io/yourorg/deeptech-worker:latest
            args: ["python","-m","app.workers.arxiv_hourly"]
            envFrom:
            - secretRef: { name: deeptech-secrets }

README.md
DeepTech Radar — Repo

- Quickstart
  - Copy .env.example to .env and adjust
  - make setup
  - make up
  - Open <http://localhost:8000/healthz>
  - Prometheus <http://localhost:9090>
  - Grafana <http://localhost:3000> (admin/admin)

- Common commands
  - make migrate, make revision m="msg", make test, make fmt

- API
  - GET /healthz, /readyz, /metrics
  - GET /papers?q=quantum&limit=20
  - GET /papers/near?text_query=graph%20neural%20nets&k=10

- Notes
  - Local Postgres uses pgvector extension via pgvector/pgvector:pg15 image
  - Embeddings default to zero vector if model not installed (worker image includes model)

Next steps you can ask me for

- Fill workers/arxiv_hourly.py and github_hourly.py with real ingestion + ETag caching.
- Add scoring_daily.py, linking_job.py, opportunities_daily.py logic.
- Provide Grafana dashboard with panels wired to Prometheus metrics.
- Create a ZIP/tarball or a repo PR with these files.
