"""empty message

Revision ID: f2814cfd496c
Revises: 5360b07baba0, 7e98d5d6d0a1
Create Date: 2025-06-23 18:22:19.826961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2814cfd496c'
down_revision: Union[str, None] = ('5360b07baba0', '7e98d5d6d0a1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

