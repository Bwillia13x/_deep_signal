import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

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
        sa.Column(
            "published_at", sa.DateTime(timezone=True), nullable=True, index=True
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("tsv", sa.dialects.postgresql.TSVECTOR, nullable=True),
    )
    op.create_index(
        "ix_papers_embedding_hnsw", "papers", ["embedding"], postgresql_using="hnsw"
    )
    op.create_index("ix_papers_tsv", "papers", ["tsv"], postgresql_using="gin")
    op.execute(
        """
        CREATE TRIGGER papers_tsv_update BEFORE INSERT OR UPDATE
        ON papers FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(tsv, 'pg_catalog.english', title, abstract)
    """
    )

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
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("deeptech_complexity_score", sa.Float, nullable=True),
        sa.Column("velocity_score", sa.Float, nullable=True),
        sa.Column("velocity_evidence", sa.JSON, nullable=True),
    )

    op.create_table(
        "paper_repo_links",
        sa.Column(
            "paper_id",
            sa.BigInteger,
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "repo_id",
            sa.BigInteger,
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "http_cache",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("url", sa.Text, nullable=False, unique=True),
        sa.Column("etag", sa.String(255)),
        sa.Column("last_modified", sa.String(255)),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
