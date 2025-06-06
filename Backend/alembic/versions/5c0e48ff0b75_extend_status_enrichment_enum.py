"""extend StatusEnriquecimentoEnum with additional values

Revision ID: 5c0e48ff0b75
Revises: 7b4809b4d9af
Create Date: 2025-06-08 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5c0e48ff0b75'
down_revision: Union[str, None] = '7b4809b4d9af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum_name = 'statusenriquecimentoenum'
    new_values = [
        'CONCLUIDO_SUCESSO',
        'CONCLUIDO_COM_DADOS_PARCIAIS',
        'FALHOU',
        'FALHA_API_EXTERNA',
        'FALHA_CONFIGURACAO_API_EXTERNA',
        'NENHUMA_FONTE_ENCONTRADA'
    ]
    conn = op.get_bind()
    for value in new_values:
        conn.execute(sa.text(f"ALTER TYPE {status_enum_name} ADD VALUE IF NOT EXISTS '{value}'"))


def downgrade() -> None:
    # Enum value removal is not supported in a simple way.
    pass
