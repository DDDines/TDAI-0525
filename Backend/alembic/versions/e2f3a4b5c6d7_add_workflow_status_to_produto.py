"""add_workflow_status_to_produto

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-03-19 00:02:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE produtoworkflowstatusenum AS ENUM (
                'rascunho', 'em_revisao', 'aprovado', 'pronto_para_exportar', 'exportado'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS workflow_status produtoworkflowstatusenum
        NOT NULL DEFAULT 'rascunho'
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_produtos_workflow_status
        ON produtos (workflow_status)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_produtos_workflow_status")
    op.execute("ALTER TABLE produtos DROP COLUMN IF EXISTS workflow_status")
    op.execute("DROP TYPE IF EXISTS produtoworkflowstatusenum")
