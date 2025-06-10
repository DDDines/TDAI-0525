"""replace lambda with clause in product type index

Revision ID: ab0264b3dd00
Revises: e82d95b0cae0
Create Date: 2025-06-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ab0264b3dd00'
down_revision: Union[str, None] = 'e82d95b0cae0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_product_types_global_key_name_unique', table_name='product_types')
    op.create_index(
        'ix_product_types_global_key_name_unique',
        'product_types',
        ['key_name'],
        unique=True,
        postgresql_where=sa.text('user_id IS NULL')
    )


def downgrade() -> None:
    op.drop_index('ix_product_types_global_key_name_unique', table_name='product_types')
    op.create_index(
        'ix_product_types_global_key_name_unique',
        'product_types',
        ['key_name'],
        unique=True,
        postgresql_where=sa.text('user_id IS NULL')
    )
