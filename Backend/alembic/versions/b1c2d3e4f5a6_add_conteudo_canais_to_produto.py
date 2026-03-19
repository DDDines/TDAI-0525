"""add_conteudo_canais_to_produto

Revision ID: b1c2d3e4f5a6
Revises: a028b2cbb145
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a028b2cbb145'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class _MigrationEntries:
    @staticmethod
    def upgrade() -> None:
        """Add conteudo_canais JSON column to produtos (idempotent)."""
        op.execute("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS conteudo_canais JSON")

    @staticmethod
    def downgrade() -> None:
        """Remove conteudo_canais from produtos."""
        op.drop_column('produtos', 'conteudo_canais')


upgrade = _MigrationEntries.upgrade
downgrade = _MigrationEntries.downgrade
