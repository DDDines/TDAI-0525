"""unir tudo

Revision ID: bcf0924f1fd6
Revises: 50d295a1ccd0, af1a26b2e401
Create Date: 2025-06-16 16:07:28.893739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcf0924f1fd6'
down_revision: Union[str, None] = ('50d295a1ccd0', 'af1a26b2e401')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

