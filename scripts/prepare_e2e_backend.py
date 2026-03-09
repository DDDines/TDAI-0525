"""Prepare a clean backend database for Playwright end-to-end runs."""

from __future__ import annotations

import sys

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.core.config import settings
from scripts.upgrade_or_bootstrap_database import DatabaseUpgradeOrBootstrapRuntime


class E2EBackendPreparation:
    """Prepare schema and seed defaults before browser-driven smoke tests."""

    @classmethod
    def run(cls) -> None:
        print(f"Preparing e2e backend database: {settings.DATABASE_URL}")
        runtime = DatabaseUpgradeOrBootstrapRuntime()
        if runtime.is_database_empty():
            runtime.create_schema()
            import asyncio

            asyncio.run(runtime.seed_defaults())
        print("E2E backend database prepared.")


if __name__ == "__main__":
    E2EBackendPreparation.run()
