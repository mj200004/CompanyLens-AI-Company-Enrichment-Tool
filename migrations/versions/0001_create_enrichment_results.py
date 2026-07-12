"""create enrichment results

Revision ID: 0001_create_enrichment_results
Revises:
Create Date: 2026-07-11 01:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_create_enrichment_results"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrichment_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_domain", sa.String(length=255), nullable=False),
        sa.Column("website_name", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("primary_phone", sa.String(length=128), nullable=True),
        sa.Column("emails", sa.JSON(), nullable=False),
        sa.Column("phones", sa.JSON(), nullable=False),
        sa.Column("services_summary", sa.Text(), nullable=True),
        sa.Column("target_customers", sa.Text(), nullable=True),
        sa.Column("pain_points", sa.Text(), nullable=True),
        sa.Column("value_proposition", sa.Text(), nullable=True),
        sa.Column("outreach_opener", sa.Text(), nullable=True),
        sa.Column("source_pages", sa.JSON(), nullable=False),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_enrichment_results_created_at"), "enrichment_results", ["created_at"], unique=False)
    op.create_index(op.f("ix_enrichment_results_normalized_domain"), "enrichment_results", ["normalized_domain"], unique=False)
    op.create_index(op.f("ix_enrichment_results_source_url"), "enrichment_results", ["source_url"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_enrichment_results_source_url"), table_name="enrichment_results")
    op.drop_index(op.f("ix_enrichment_results_normalized_domain"), table_name="enrichment_results")
    op.drop_index(op.f("ix_enrichment_results_created_at"), table_name="enrichment_results")
    op.drop_table("enrichment_results")
