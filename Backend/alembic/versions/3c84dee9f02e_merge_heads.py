"""merge heads

Revision ID: 3c84dee9f02e
Revises: 440d06ca18c5, 62a7a657e0f0
Create Date: 2025-06-10 15:59:57.669439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c84dee9f02e'
down_revision: Union[str, None] = ('440d06ca18c5', '62a7a657e0f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

