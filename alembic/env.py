from __future__ import annotations

import contextlib
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.db.base import Base
from app.db.models import (  # noqa
    domain_metric,
    http_cache,
    opportunity,
    paper,
    paper_repo_link,
    repository,
)

config = context.config
if config.config_file_name is not None:
    with contextlib.suppress(KeyError):
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
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
