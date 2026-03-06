"""Add user company and avatar profile fields.

Revision ID: 6d0f5e9d2a21
Revises: 71136158c1ff
Create Date: 2026-03-05 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6d0f5e9d2a21"
down_revision: Union[str, None] = "71136158c1ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class _MigrationEntries:
    @staticmethod
    def upgrade() -> None:
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.add_column(sa.Column("nome_empresa", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("avatar_url", sa.String(), nullable=True))

    @staticmethod
    def downgrade() -> None:
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.drop_column("avatar_url")
            batch_op.drop_column("nome_empresa")


upgrade = _MigrationEntries.upgrade
downgrade = _MigrationEntries.downgrade
