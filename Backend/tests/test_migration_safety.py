"""Safety tests for Alembic revisions and the migration safety checker."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = PROJECT_ROOT / "scripts" / "check_migration_safety.py"


def _load_checker_module():
    spec = importlib.util.spec_from_file_location("check_migration_safety", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_alembic_revisions_are_zero_downtime_safe():
    module = _load_checker_module()
    checker = module.MigrationSafetyChecker(PROJECT_ROOT / "Backend" / "alembic" / "versions")

    assert checker.run() == []


def test_migration_safety_checker_flags_drop_and_rename_patterns(tmp_path):
    module = _load_checker_module()
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    safe_file = versions_dir / "1111_safe.py"
    safe_file.write_text(
        """
class _MigrationEntries:
    @staticmethod
    def upgrade():
        batch_op.add_column("nova_coluna")
""".strip(),
        encoding="utf-8",
    )
    unsafe_file = versions_dir / "2222_unsafe.py"
    unsafe_file.write_text(
        """
from alembic import op

class _MigrationEntries:
    @staticmethod
    def upgrade():
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("avatar_url")
        op.execute("ALTER TABLE users RENAME COLUMN a TO b")
        batch_op.alter_column("old", new_column_name="new")
""".strip(),
        encoding="utf-8",
    )

    issues = module.MigrationSafetyChecker(versions_dir).run()

    assert len(issues) == 3
    assert any("drop_column" in issue.detail for issue in issues)
    assert any("destructive SQL" in issue.detail for issue in issues)
    assert any("new_column_name" in issue.detail for issue in issues)


def test_migration_safety_cli_returns_expected_exit_code(tmp_path, capsys):
    module = _load_checker_module()
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    assert module.MigrationSafetyCli.main(["--versions-dir", str(versions_dir)]) == 0
    assert "passed" in capsys.readouterr().out

    unsafe_file = versions_dir / "3333_unsafe.py"
    unsafe_file.write_text(
        """
class _MigrationEntries:
    @staticmethod
    def upgrade():
        batch_op.drop_column("legacy")
""".strip(),
        encoding="utf-8",
    )

    assert module.MigrationSafetyCli.main(["--versions-dir", str(versions_dir)]) == 1
    assert "violations" in capsys.readouterr().out
