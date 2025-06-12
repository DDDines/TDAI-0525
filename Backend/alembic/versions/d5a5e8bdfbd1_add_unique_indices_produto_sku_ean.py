"""add unique indices for sku and ean per user

Revision ID: d5a5e8bdfbd1
Revises: c1f4cd5f7a6a
Create Date: 2025-06-30 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd5a5e8bdfbd1'
down_revision: Union[str, None] = 'c1f4cd5f7a6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_produtos_user_sku', 'produtos', ['user_id', 'sku'])
    op.create_unique_constraint('uq_produtos_user_ean', 'produtos', ['user_id', 'ean'])


def downgrade() -> None:
    op.drop_constraint('uq_produtos_user_ean', 'produtos', type_='unique')
    op.drop_constraint('uq_produtos_user_sku', 'produtos', type_='unique')
