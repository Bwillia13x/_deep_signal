"""Add scoring fields to papers table

Revision ID: 002_add_scoring_fields
Revises: 001_initial_schema
Create Date: 2025-11-18 04:10:58

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_add_scoring_fields"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scoring fields to papers table
    op.add_column("papers", sa.Column("moat_score", sa.Float, nullable=True))
    op.add_column("papers", sa.Column("moat_evidence", sa.JSON, nullable=True))
    op.add_column("papers", sa.Column("scalability_score", sa.Float, nullable=True))
    op.add_column("papers", sa.Column("scalability_evidence", sa.JSON, nullable=True))
    op.add_column("papers", sa.Column("attention_gap_score", sa.Float, nullable=True))
    op.add_column("papers", sa.Column("attention_gap_evidence", sa.JSON, nullable=True))
    op.add_column("papers", sa.Column("network_score", sa.Float, nullable=True))
    op.add_column("papers", sa.Column("network_evidence", sa.JSON, nullable=True))
    op.add_column("papers", sa.Column("composite_score", sa.Float, nullable=True))
    op.add_column("papers", sa.Column("scoring_metadata", sa.JSON, nullable=True))
    
    # Add indexes for scoring queries
    op.create_index("ix_papers_composite_score", "papers", ["composite_score"])
    op.create_index("ix_papers_moat_score", "papers", ["moat_score"])
    op.create_index("ix_papers_scalability_score", "papers", ["scalability_score"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_papers_scalability_score", "papers")
    op.drop_index("ix_papers_moat_score", "papers")
    op.drop_index("ix_papers_composite_score", "papers")
    
    # Drop columns
    op.drop_column("papers", "scoring_metadata")
    op.drop_column("papers", "composite_score")
    op.drop_column("papers", "network_evidence")
    op.drop_column("papers", "network_score")
    op.drop_column("papers", "attention_gap_evidence")
    op.drop_column("papers", "attention_gap_score")
    op.drop_column("papers", "scalability_evidence")
    op.drop_column("papers", "scalability_score")
    op.drop_column("papers", "moat_evidence")
    op.drop_column("papers", "moat_score")
