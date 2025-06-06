"""update product type index condition

Revision ID: bdaeb62ae8de
Revises: 7b4809b4d9af
Create Date: 2025-06-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdaeb62ae8de'
down_revision: Union[str, None] = '7b4809b4d9af'
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

