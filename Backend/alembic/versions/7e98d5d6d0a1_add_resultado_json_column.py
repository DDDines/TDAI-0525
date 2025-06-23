"""add resultado_json column to catalog_import_files

Revision ID: 7e98d5d6d0a1
Revises: 999999999999
Create Date: 2025-07-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7e98d5d6d0a1'
down_revision: Union[str, None] = '999999999999'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('catalog_import_files', sa.Column('resultado_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('catalog_import_files', 'resultado_json')
