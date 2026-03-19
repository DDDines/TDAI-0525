"""add_basic_generation_template_configs

Revision ID: 9a3d1f6b2c44
Revises: 6c4d0c90a1bf
Create Date: 2026-03-19 06:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a3d1f6b2c44"
down_revision: Union[str, None] = "6c4d0c90a1bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class _MigrationEntries:
    @staticmethod
    def upgrade() -> None:
        """Add persisted basic-generation template configs (idempotent)."""
        # Enum: create only if it doesn't exist
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE externalcredentialscopeenum AS ENUM ('COMPANY', 'USER');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
            """
        )
        # Table: create only if it doesn't exist
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS basic_generation_template_configs (
                id SERIAL PRIMARY KEY,
                scope_type externalcredentialscopeenum NOT NULL,
                company_identifier VARCHAR,
                user_id INTEGER REFERENCES users(id),
                title_template TEXT,
                description_template TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                CONSTRAINT uq_basic_generation_template_scope_subject
                    UNIQUE (scope_type, company_identifier, user_id)
            )
            """
        )
        # Indices: create only if they don't exist
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_basic_generation_template_configs_id "
            "ON basic_generation_template_configs (id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_basic_generation_template_configs_company_identifier "
            "ON basic_generation_template_configs (company_identifier)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_basic_generation_template_configs_user_id "
            "ON basic_generation_template_configs (user_id)"
        )

    @staticmethod
    def downgrade() -> None:
        """Remove persisted basic-generation template configs."""
        op.execute("DROP INDEX IF EXISTS ix_basic_generation_template_configs_user_id")
        op.execute("DROP INDEX IF EXISTS ix_basic_generation_template_configs_company_identifier")
        op.execute("DROP INDEX IF EXISTS ix_basic_generation_template_configs_id")
        op.drop_table("basic_generation_template_configs")


upgrade = _MigrationEntries.upgrade
downgrade = _MigrationEntries.downgrade
