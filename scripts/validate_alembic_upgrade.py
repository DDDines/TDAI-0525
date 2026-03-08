"""Validate that the current Alembic head revision upgrades cleanly from its down_revision schema."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable, List

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.database import Base, engine
import Backend.models  # noqa: F401


@dataclass(frozen=True)
class HeadOperation:
    """Describe one additive operation performed by the Alembic head revision."""

    kind: str
    table_name: str
    name: str


class HeadRevisionIntrospection:
    """Parse the head Alembic revision and identify additive operations to rewind."""

    def __init__(self, revision_path: Path) -> None:
        self._revision_path = Path(revision_path)

    def _iter_upgrade_nodes(self, tree: ast.AST) -> Iterable[ast.AST]:
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "upgrade":
                        yield item
            elif isinstance(node, ast.FunctionDef) and node.name == "upgrade":
                yield node

    @staticmethod
    def _constant_string(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    @staticmethod
    def _column_name_from_args(args: List[ast.AST]) -> str | None:
        if not args:
            return None
        first_arg = args[0]
        if isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Attribute):
            if first_arg.func.attr == "Column" and first_arg.args:
                return HeadRevisionIntrospection._constant_string(first_arg.args[0])
        return None

    def run(self) -> List[HeadOperation]:
        tree = ast.parse(self._revision_path.read_text(encoding="utf-8"), filename=str(self._revision_path))
        operations: List[HeadOperation] = []
        for upgrade in self._iter_upgrade_nodes(tree):
            batch_tables: dict[str, str] = {}
            for node in ast.walk(upgrade):
                if isinstance(node, ast.With):
                    for item in node.items:
                        context_expr = item.context_expr
                        if not isinstance(context_expr, ast.Call) or not isinstance(context_expr.func, ast.Attribute):
                            continue
                        if context_expr.func.attr != "batch_alter_table" or not context_expr.args:
                            continue
                        alias = item.optional_vars.id if isinstance(item.optional_vars, ast.Name) else None
                        table_name = self._constant_string(context_expr.args[0])
                        if alias and table_name:
                            batch_tables[alias] = table_name
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                attr_name = node.func.attr
                owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
                if attr_name == "create_table" and node.args:
                    table_name = self._constant_string(node.args[0])
                    if table_name:
                        operations.append(HeadOperation("table", table_name, table_name))
                elif attr_name == "create_index" and len(node.args) >= 2:
                    index_name = self._constant_string(node.args[0])
                    table_name = self._constant_string(node.args[1])
                    if table_name and index_name:
                        operations.append(HeadOperation("index", table_name, index_name))
                elif attr_name == "add_column":
                    if owner in batch_tables:
                        column_name = self._column_name_from_args(node.args)
                        if column_name:
                            operations.append(HeadOperation("column", batch_tables[owner], column_name))
                    elif len(node.args) >= 2:
                        table_name = self._constant_string(node.args[0])
                        column_name = self._column_name_from_args(node.args[1:])
                        if table_name and column_name:
                            operations.append(HeadOperation("column", table_name, column_name))
        return operations


class AlembicUpgradeValidator:
    """Prepare the pre-head schema and validate the latest Alembic upgrade path."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = Path(config_path).resolve()
        self._backend_dir = self._config_path.parent
        self._config = Config(str(self._config_path))
        self._config.set_main_option("script_location", str(self._backend_dir / "alembic"))
        self._script = ScriptDirectory.from_config(self._config)

    def _head_revision(self):
        head = self._script.get_current_head()
        return self._script.get_revision(head)

    def _rewind_head_additions(self, operations: List[HeadOperation]) -> None:
        with engine.begin() as connection:
            for operation in operations:
                inspector = inspect(connection)
                if operation.kind == "index":
                    indexes = {item["name"] for item in inspector.get_indexes(operation.table_name)}
                    if operation.name in indexes:
                        connection.execute(text(f'DROP INDEX "{operation.name}"'))
                elif operation.kind == "column":
                    columns = {item["name"] for item in inspector.get_columns(operation.table_name)}
                    if operation.name in columns:
                        connection.execute(
                            text(f'ALTER TABLE "{operation.table_name}" DROP COLUMN "{operation.name}"')
                        )
                elif operation.kind == "table":
                    if inspector.has_table(operation.table_name):
                        connection.execute(text(f'DROP TABLE "{operation.table_name}"'))

    def run(self) -> str:
        head_revision = self._head_revision()
        previous_revision = head_revision.down_revision or "base"
        operations = HeadRevisionIntrospection(Path(head_revision.path)).run()

        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self._rewind_head_additions(operations)

        command.stamp(self._config, previous_revision)
        command.upgrade(self._config, "head")
        return str(head_revision.revision)


class AlembicUpgradeCli:
    """CLI wrapper for head-upgrade validation."""

    @staticmethod
    def build_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Validate Alembic head upgrade against a prepared pre-head schema.")
        parser.add_argument(
            "--config",
            default=str(Path(__file__).resolve().parent.parent / "Backend" / "alembic.ini"),
            help="Path to alembic.ini",
        )
        return parser

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = cls.build_arg_parser().parse_args(argv)
        revision = AlembicUpgradeValidator(Path(args.config)).run()
        print(f"Alembic head upgrade validated for revision {revision}.")
        return 0


if __name__ == "__main__":
    raise SystemExit(AlembicUpgradeCli.main())
