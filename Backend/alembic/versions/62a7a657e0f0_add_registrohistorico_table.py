"""add RegistroHistorico table

Revision ID: 62a7a657e0f0
Revises: de2f5f4cc0f6
Create Date: 2025-06-11 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '62a7a657e0f0'
down_revision: Union[str, None] = 'de2f5f4cc0f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'registros_historico',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('entidade', sa.String(), nullable=False),
        sa.Column('acao', sa.Enum('CRIACAO', 'ATUALIZACAO', 'DELECAO', name='tipoacaosistemaenum'), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('detalhes_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_registros_historico_id'), 'registros_historico', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_registros_historico_id'), table_name='registros_historico')
    op.drop_table('registros_historico')
    op.execute("DROP TYPE IF EXISTS tipoacaosistemaenum")
