"""Add recommendation tier to opportunities

Revision ID: 004_add_recommendation_tier
Revises: 003_add_scoring_stats
Create Date: 2025-11-18 04:25:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_recommendation_tier"
down_revision = "003_add_scoring_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add recommendation tier to opportunities table
    op.add_column("opportunities", sa.Column("recommendation", sa.String(20), nullable=True))
    op.create_index("ix_opportunities_recommendation", "opportunities", ["recommendation"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_recommendation", "opportunities")
    op.drop_column("opportunities", "recommendation")
