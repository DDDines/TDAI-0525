"""rename TipoAcaoIAEnum to TipoAcaoEnum

Revision ID: 440d06ca18c5
Revises: ('de2f5f4cc0f6', 'ab0264b3dd00')
Create Date: 2025-06-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '440d06ca18c5'
down_revision: Union[str, Sequence[str], None] = ('de2f5f4cc0f6', 'ab0264b3dd00')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE tipoacaoiaenum RENAME TO tipoacaoenum")


def downgrade() -> None:
    op.execute("ALTER TYPE tipoacaoenum RENAME TO tipoacaoiaenum")
