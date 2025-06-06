"""add log_enriquecimento_web column to Produto

Revision ID: 7b4809b4d9af
Revises: 522dce3cd6aa
Create Date: 2025-06-07 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7b4809b4d9af'
down_revision: Union[str, None] = '522dce3cd6aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('produtos', sa.Column('log_enriquecimento_web', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('produtos', 'log_enriquecimento_web')
