"""add_extraction_mode_to_catalog_import_file

Revision ID: c7e8f9a0b1d2
Revises: 9a3d1f6b2c44, b1c2d3e4f5a6
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e8f9a0b1d2'
down_revision: Union[str, tuple, None] = ('9a3d1f6b2c44', 'b1c2d3e4f5a6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class _MigrationEntries:
    @staticmethod
    def upgrade() -> None:
        """Add extraction_mode column to catalog_import_files."""
        op.add_column(
            'catalog_import_files',
            sa.Column('extraction_mode', sa.String(), nullable=True),
        )

    @staticmethod
    def downgrade() -> None:
        """Remove extraction_mode column from catalog_import_files."""
        op.drop_column('catalog_import_files', 'extraction_mode')


upgrade = _MigrationEntries.upgrade
downgrade = _MigrationEntries.downgrade
