"""add_last_exported_at_to_produto

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-19 22:20:00.000000

"""
from alembic import op

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS last_exported_at TIMESTAMPTZ NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE produtos DROP COLUMN IF EXISTS last_exported_at")
