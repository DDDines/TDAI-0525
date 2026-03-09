"""Upgrade an existing database or bootstrap an empty one for first deploy."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend import models  # noqa: E402
from Backend.database import engine  # noqa: E402
from Backend.main import MainBootstrapWorkflow  # noqa: E402


class DatabaseUpgradeOrBootstrapRuntime:
    """Handle empty-database bootstrap separately from normal Alembic upgrades."""

    @staticmethod
    def build_alembic_config(config_path: Path) -> Config:
        config = Config(str(config_path))
        config.set_main_option("script_location", str(config_path.parent / "alembic"))
        return config

    @staticmethod
    def list_table_names() -> list[str]:
        return list(inspect(engine).get_table_names())

    def is_database_empty(self) -> bool:
        user_tables = [name for name in self.list_table_names() if name != "alembic_version"]
        return not user_tables

    @staticmethod
    def create_schema() -> None:
        models.Base.metadata.create_all(bind=engine)

    @staticmethod
    async def seed_defaults() -> None:
        await MainBootstrapWorkflow().startup_event_create_defaults()

    @staticmethod
    def stamp_head(config: Config) -> None:
        command.stamp(config, "head")

    @staticmethod
    def upgrade_head(config: Config) -> None:
        command.upgrade(config, "head")

    def run(self, *, config_path: Path) -> str:
        config = self.build_alembic_config(config_path)
        if self.is_database_empty():
            self.create_schema()
            asyncio.run(self.seed_defaults())
            self.stamp_head(config)
            return "bootstrapped"
        self.upgrade_head(config)
        return "upgraded"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upgrade an existing CatalogAI database or bootstrap an empty one."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "Backend" / "alembic.ini"),
        help="Path to alembic.ini",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    mode = DatabaseUpgradeOrBootstrapRuntime().run(config_path=Path(args.config).resolve())
    if mode == "bootstrapped":
        print("Database was empty. Bootstrapped current schema and stamped Alembic head.")
    else:
        print("Database upgraded to Alembic head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
