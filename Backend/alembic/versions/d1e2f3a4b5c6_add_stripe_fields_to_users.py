"""add_stripe_fields_to_users

Revision ID: d1e2f3a4b5c6
Revises: c7e8f9a0b1d2
Create Date: 2026-03-19 00:01:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c7e8f9a0b1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR UNIQUE,
        ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR UNIQUE
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id
        ON users (stripe_customer_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_stripe_subscription_id
        ON users (stripe_subscription_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_stripe_subscription_id")
    op.execute("DROP INDEX IF EXISTS ix_users_stripe_customer_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS stripe_subscription_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS stripe_customer_id")
