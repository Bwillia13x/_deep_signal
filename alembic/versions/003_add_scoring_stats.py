"""Add moat and scalability stats to domain_metrics

Revision ID: 003_add_scoring_stats
Revises: 002_add_scoring_fields
Create Date: 2025-11-18 04:15:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_scoring_stats"
down_revision = "002_add_scoring_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scoring statistics to domain_metrics table
    op.add_column("domain_metrics", sa.Column("moat_mu", sa.Float, nullable=True))
    op.add_column("domain_metrics", sa.Column("moat_sigma", sa.Float, nullable=True))
    op.add_column("domain_metrics", sa.Column("scalability_mu", sa.Float, nullable=True))
    op.add_column("domain_metrics", sa.Column("scalability_sigma", sa.Float, nullable=True))
    op.add_column("domain_metrics", sa.Column("attention_mu", sa.Float, nullable=True))
    op.add_column("domain_metrics", sa.Column("attention_sigma", sa.Float, nullable=True))
    op.add_column("domain_metrics", sa.Column("network_mu", sa.Float, nullable=True))
    op.add_column("domain_metrics", sa.Column("network_sigma", sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column("domain_metrics", "network_sigma")
    op.drop_column("domain_metrics", "network_mu")
    op.drop_column("domain_metrics", "attention_sigma")
    op.drop_column("domain_metrics", "attention_mu")
    op.drop_column("domain_metrics", "scalability_sigma")
    op.drop_column("domain_metrics", "scalability_mu")
    op.drop_column("domain_metrics", "moat_sigma")
    op.drop_column("domain_metrics", "moat_mu")
