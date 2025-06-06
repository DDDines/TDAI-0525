"""extend StatusEnriquecimentoEnum with additional values

Revision ID: f25a0939520a
Revises: 7b4809b4d9af
Create Date: 2025-06-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f25a0939520a'
down_revision: Union[str, None] = '7b4809b4d9af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE statusenriquecimentoenum ADD VALUE IF NOT EXISTS 'FALHOU'")
    op.execute("ALTER TYPE statusenriquecimentoenum ADD VALUE IF NOT EXISTS 'FALHA_API_EXTERNA'")
    op.execute("ALTER TYPE statusenriquecimentoenum ADD VALUE IF NOT EXISTS 'FALHA_CONFIGURACAO_API_EXTERNA'")
    op.execute("ALTER TYPE statusenriquecimentoenum ADD VALUE IF NOT EXISTS 'CONCLUIDO_SUCESSO'")
    op.execute("ALTER TYPE statusenriquecimentoenum ADD VALUE IF NOT EXISTS 'CONCLUIDO_COM_DADOS_PARCIAIS'")
    op.execute("ALTER TYPE statusenriquecimentoenum ADD VALUE IF NOT EXISTS 'NENHUMA_FONTE_ENCONTRADA'")


def downgrade() -> None:
    pass
