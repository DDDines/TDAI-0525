"""add progress fields to CatalogImportFile

Revision ID: af1a26b2e401
Revises: f25a0939520a
Create Date: 2025-06-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'af1a26b2e401'
down_revision: Union[str, None] = 'f25a0939520a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('catalog_import_files', sa.Column('total_pages', sa.Integer(), nullable=True))
    op.add_column('catalog_import_files', sa.Column('pages_processed', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('catalog_import_files', 'pages_processed')
    op.drop_column('catalog_import_files', 'total_pages')
