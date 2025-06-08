"""merge heads

Revision ID: 6910abc2a315
Revises: 5c0e48ff0b75, bdaeb62ae8de
Create Date: 2025-06-09 01:25:01.379226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6910abc2a315'
down_revision: Union[str, None] = ('5c0e48ff0b75', 'bdaeb62ae8de')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

