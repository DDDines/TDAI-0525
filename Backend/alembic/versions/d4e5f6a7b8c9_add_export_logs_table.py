"""add_export_logs_table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'export_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('format', sa.String(), nullable=False, server_default='xlsx'),
        sa.Column('filtros_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_export_logs_id', 'export_logs', ['id'])
    op.create_index('ix_export_logs_user_id', 'export_logs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_export_logs_user_id', table_name='export_logs')
    op.drop_index('ix_export_logs_id', table_name='export_logs')
    op.drop_table('export_logs')
