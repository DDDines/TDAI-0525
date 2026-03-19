"""add_soft_delete_to_produtos

Revision ID: 6c4d0c90a1bf
Revises: 20773b153872
Create Date: 2026-03-18 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c4d0c90a1bf'
down_revision: Union[str, None] = '20773b153872'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class _MigrationEntries:
    @staticmethod
    def upgrade() -> None:
        """Add soft-delete fields to produtos."""
        op.add_column(
            'produtos',
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.add_column(
            'produtos',
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f('ix_produtos_is_deleted'), 'produtos', ['is_deleted'], unique=False)

    @staticmethod
    def downgrade() -> None:
        """Remove soft-delete fields from produtos."""
        op.drop_index(op.f('ix_produtos_is_deleted'), table_name='produtos')
        op.drop_column('produtos', 'deleted_at')
        op.drop_column('produtos', 'is_deleted')


upgrade = _MigrationEntries.upgrade
downgrade = _MigrationEntries.downgrade
