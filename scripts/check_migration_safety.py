"""Check Alembic migrations for destructive upgrade operations."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


FORBIDDEN_SQL_PATTERNS = (
    re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
    re.compile(r"\bRENAME\s+COLUMN\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class MigrationIssue:
    """Represent one destructive migration finding."""

    path: str
    lineno: int
    detail: str


class MigrationSafetyChecker:
    """AST-driven checker for destructive upgrade operations in Alembic revisions."""

    def __init__(self, versions_dir: Path) -> None:
        self._versions_dir = Path(versions_dir)

    def iter_migration_files(self) -> Iterable[Path]:
        """Iterate concrete migration python files under the configured versions directory."""
        if not self._versions_dir.exists():
            return []
        return sorted(
            path
            for path in self._versions_dir.glob("*.py")
            if path.is_file() and path.name != "__init__.py"
        )

    def _extract_string_literals(self, node: ast.AST) -> List[str]:
        """Extract string payloads from constants or nested text-wrapping calls."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.Call) and node.args:
            literals: List[str] = []
            for arg in node.args:
                literals.extend(self._extract_string_literals(arg))
            return literals
        return []

    def _find_upgrade_nodes(self, tree: ast.AST) -> List[ast.AST]:
        """Collect class/staticmethod-based or direct upgrade functions."""
        nodes: List[ast.AST] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "upgrade":
                        nodes.append(item)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "upgrade":
                nodes.append(node)
        return nodes

    def check_file(self, path: Path) -> List[MigrationIssue]:
        """Inspect one Alembic revision file for destructive upgrade operations."""
        issues: List[MigrationIssue] = []
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for upgrade_node in self._find_upgrade_nodes(tree):
            for node in ast.walk(upgrade_node):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                attr_name = node.func.attr
                if attr_name == "drop_column":
                    issues.append(
                        MigrationIssue(
                            path=str(path),
                            lineno=node.lineno,
                            detail="drop_column detected in upgrade path",
                        )
                    )
                    continue
                if attr_name == "alter_column":
                    for keyword in node.keywords:
                        if keyword.arg == "new_column_name":
                            issues.append(
                                MigrationIssue(
                                    path=str(path),
                                    lineno=node.lineno,
                                    detail="column rename detected via alter_column(new_column_name=...)",
                                )
                            )
                            break
                    continue
                if attr_name != "execute":
                    continue
                raw_sql = " ".join(
                    literal for arg in node.args for literal in self._extract_string_literals(arg)
                )
                for pattern in FORBIDDEN_SQL_PATTERNS:
                    if pattern.search(raw_sql):
                        issues.append(
                            MigrationIssue(
                                path=str(path),
                                lineno=node.lineno,
                                detail=f"destructive SQL detected: {pattern.pattern}",
                            )
                        )
                        break
        return issues

    def run(self) -> List[MigrationIssue]:
        """Run the destructive migration scan across all revision files."""
        issues: List[MigrationIssue] = []
        for path in self.iter_migration_files():
            issues.extend(self.check_file(path))
        return issues


class MigrationSafetyCli:
    """CLI wrapper for migration safety checks."""

    @staticmethod
    def build_arg_parser() -> argparse.ArgumentParser:
        """Build the CLI parser."""
        parser = argparse.ArgumentParser(description="Validate Alembic revisions for zero-downtime-safe upgrades.")
        parser.add_argument(
            "--versions-dir",
            default=str(Path(__file__).resolve().parent.parent / "Backend" / "alembic" / "versions"),
            help="Path to the Alembic versions directory.",
        )
        return parser

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        """Run the migration safety CLI and emit findings to stdout."""
        args = cls.build_arg_parser().parse_args(argv)
        checker = MigrationSafetyChecker(Path(args.versions_dir))
        issues = checker.run()
        if not issues:
            print("Migration safety check passed.")
            return 0
        print("Migration safety violations found:")
        for issue in issues:
            print(f"- {issue.path}:{issue.lineno} -> {issue.detail}")
        return 1


if __name__ == "__main__":
    raise SystemExit(MigrationSafetyCli.main())
