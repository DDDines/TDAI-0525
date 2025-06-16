"""unir tudo

Revision ID: dd1ac7978ae9
Revises: bcf0924f1fd6, ffb1c4d4e37a
Create Date: 2025-06-16 16:08:05.057391

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd1ac7978ae9'
down_revision: Union[str, None] = ('bcf0924f1fd6', 'ffb1c4d4e37a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

