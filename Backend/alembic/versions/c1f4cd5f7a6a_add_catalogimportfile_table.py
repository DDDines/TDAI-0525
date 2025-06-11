"""add CatalogImportFile table

Revision ID: c1f4cd5f7a6a
Revises: 3c84dee9f02e
Create Date: 2025-06-20 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c1f4cd5f7a6a'
down_revision: Union[str, None] = '3c84dee9f02e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'catalog_import_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('fornecedor_id', sa.Integer(), nullable=True),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('stored_filename', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='UPLOADED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['fornecedor_id'], ['fornecedores.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_catalog_import_files_id'), 'catalog_import_files', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_catalog_import_files_id'), table_name='catalog_import_files')
    op.drop_table('catalog_import_files')
