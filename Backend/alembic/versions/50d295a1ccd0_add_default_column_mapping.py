"""add default_column_mapping column to fornecedores

Revision ID: 50d295a1ccd0
Revises: d5a5e8bdfbd1
Create Date: 2025-07-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '50d295a1ccd0'
down_revision: Union[str, None] = 'd5a5e8bdfbd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fornecedores',
        sa.Column(
            'default_column_mapping',
            sa.JSON().with_variant(sa.JSON(), 'postgresql'),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column('fornecedores', 'default_column_mapping')
