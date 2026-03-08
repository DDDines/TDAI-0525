"""Sync bundled prompt defaults into the database as new versioned templates."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.database import SessionLocal  # noqa: E402
from Backend.infrastructure.repositories.prompt_template_repository import (  # noqa: E402
    PromptTemplateRepository,
)


def main() -> int:
    """Persist new versions for changed bundled prompt defaults."""
    session = SessionLocal()
    try:
        created_versions = PromptTemplateRepository(session).sync_default_templates()
    finally:
        session.close()

    if not created_versions:
        print("No prompt updates were required.")
        return 0

    print("Prompt templates updated:")
    for nome, versao in sorted(created_versions.items()):
        print(f"- {nome}: v{versao}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
