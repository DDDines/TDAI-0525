"""add_import_validation_rules

Revision ID: 20773b153872
Revises: a028b2cbb145
Create Date: 2026-03-17 22:42:03.600412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20773b153872'
down_revision: Union[str, None] = 'a028b2cbb145'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class _MigrationEntries:
    @staticmethod
    def upgrade() -> None:
        """Create import_validation_rules table."""
        op.create_table('import_validation_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('fornecedor_id', sa.Integer(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('min_quality_score', sa.Float(), nullable=True),
        sa.Column('times_applied', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['fornecedor_id'], ['fornecedores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_import_validation_rules_id'), 'import_validation_rules', ['id'], unique=False)

    @staticmethod
    def downgrade() -> None:
        """Drop import_validation_rules table."""
        op.drop_index(op.f('ix_import_validation_rules_id'), table_name='import_validation_rules')
        op.drop_table('import_validation_rules')


upgrade = _MigrationEntries.upgrade
downgrade = _MigrationEntries.downgrade
