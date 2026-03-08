"""Prepare a clean backend database for Playwright end-to-end runs."""

from __future__ import annotations

import asyncio
import sys

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend import models
from Backend.core.config import settings
from Backend.database import engine
from Backend.main import MainBootstrapWorkflow


class E2EBackendPreparation:
    """Prepare schema and seed defaults before browser-driven smoke tests."""

    @classmethod
    def ensure_schema(cls) -> None:
        models.Base.metadata.create_all(bind=engine)

    @staticmethod
    async def seed_defaults() -> None:
        await MainBootstrapWorkflow().startup_event_create_defaults()

    @classmethod
    def run(cls) -> None:
        print(f"Preparing e2e backend database: {settings.DATABASE_URL}")
        cls.ensure_schema()
        asyncio.run(cls.seed_defaults())
        print("E2E backend database prepared.")


if __name__ == "__main__":
    E2EBackendPreparation.run()
