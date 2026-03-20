"""add_workspace_invites

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS workspace_invites (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            email VARCHAR NOT NULL,
            token VARCHAR NOT NULL UNIQUE,
            created_by_user_id INTEGER NOT NULL REFERENCES users(id),
            accepted_at TIMESTAMPTZ NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_workspace_invites_company_id ON workspace_invites (company_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workspace_invites_email ON workspace_invites (email)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_workspace_invites_token ON workspace_invites (token)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace_invites")
