"""add LeadContact table

Revision ID: a3f2e1d4b5c6
Revises: 149adcd94073
Create Date: 2026-02-26

Adds DB-02b: LeadContact — typed contact details for a Lead.
contact_type is stored as String (SQLite has no native enum); valid values
are enforced by the ContactType enum in models.py:
  professional: email, linkedin, phone, calendly
  developer:    github, stackoverflow
  social:       twitter, medium, substack, youtube
  startup:      angellist, crunchbase, producthunt
  web:          website, portfolio
"""
from alembic import op
import sqlalchemy as sa

revision = "a3f2e1d4b5c6"
down_revision = "149adcd94073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leadcontact",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("contact_type", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["lead.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leadcontact_lead_id", "leadcontact", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_leadcontact_lead_id", table_name="leadcontact")
    op.drop_table("leadcontact")
