"""add_company_model

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-03-19 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id SERIAL PRIMARY KEY,
            nome VARCHAR NOT NULL,
            cnpj VARCHAR UNIQUE,
            criado_por_user_id INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_companies_id ON companies (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_companies_cnpj ON companies (cnpj)")
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id)
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_company_id ON users (company_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_company_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS company_id")
    op.execute("DROP TABLE IF EXISTS companies")
