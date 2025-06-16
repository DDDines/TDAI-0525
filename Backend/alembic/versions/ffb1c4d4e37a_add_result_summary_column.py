"""add result_summary column to catalog_import_files

Revision ID: ffb1c4d4e37a
Revises: e82d95b0cae0
Create Date: 2025-07-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'ffb1c4d4e37a'
down_revision: Union[str, None] = 'e82d95b0cae0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('catalog_import_files', sa.Column('result_summary', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('catalog_import_files', 'result_summary')
