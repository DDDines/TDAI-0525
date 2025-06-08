"""merge heads

Revision ID: e82d95b0cae0
Revises: 6910abc2a315, f25a0939520a
Create Date: 2025-06-09 01:26:03.607435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e82d95b0cae0'
down_revision: Union[str, None] = ('6910abc2a315', 'f25a0939520a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

