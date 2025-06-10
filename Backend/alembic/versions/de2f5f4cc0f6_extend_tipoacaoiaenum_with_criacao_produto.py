"""extend TipoAcaoIAEnum with CRIACAO_PRODUTO value

Revision ID: de2f5f4cc0f6
Revises: e82d95b0cae0
Create Date: 2025-06-10 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'de2f5f4cc0f6'
down_revision: Union[str, None] = 'e82d95b0cae0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE tipoacaoiaenum ADD VALUE IF NOT EXISTS 'CRIACAO_PRODUTO'")


def downgrade() -> None:
    # Enum value removal not supported
    pass
