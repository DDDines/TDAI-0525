"""add_lm_studio_to_credential_provider_enum

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-03-19 22:00:00.000000

"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE externalcredentialproviderenum ADD VALUE IF NOT EXISTS 'lm_studio'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; skip downgrade
    pass
