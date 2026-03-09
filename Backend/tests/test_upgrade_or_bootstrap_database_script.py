from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "upgrade_or_bootstrap_database.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("upgrade_or_bootstrap_database", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runtime_bootstraps_empty_database(monkeypatch):
    module = _load_script_module()
    calls: list[tuple[str, object | None]] = []

    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "build_alembic_config",
        staticmethod(lambda config_path: calls.append(("config", config_path)) or "cfg"),
    )
    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "is_database_empty",
        lambda self: True,
    )
    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "create_schema",
        staticmethod(lambda: calls.append(("create_schema", None))),
    )
    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "seed_defaults",
        staticmethod(lambda: calls.append(("seed_defaults", None))),
    )
    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "stamp_head",
        staticmethod(lambda config: calls.append(("stamp_head", config))),
    )
    monkeypatch.setattr(module.asyncio, "run", lambda coro: coro)

    result = module.DatabaseUpgradeOrBootstrapRuntime().run(config_path=Path("alembic.ini"))

    assert result == "bootstrapped"
    assert calls == [
        ("config", Path("alembic.ini")),
        ("create_schema", None),
        ("seed_defaults", None),
        ("stamp_head", "cfg"),
    ]


def test_runtime_upgrades_existing_database(monkeypatch):
    module = _load_script_module()
    calls: list[tuple[str, object | None]] = []

    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "build_alembic_config",
        staticmethod(lambda config_path: calls.append(("config", config_path)) or "cfg"),
    )
    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "is_database_empty",
        lambda self: False,
    )
    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "upgrade_head",
        staticmethod(lambda config: calls.append(("upgrade_head", config))),
    )

    result = module.DatabaseUpgradeOrBootstrapRuntime().run(config_path=Path("alembic.ini"))

    assert result == "upgraded"
    assert calls == [
        ("config", Path("alembic.ini")),
        ("upgrade_head", "cfg"),
    ]


def test_main_prints_bootstrap_message(monkeypatch, capsys):
    module = _load_script_module()
    parser = module.build_arg_parser()
    args = parser.parse_args(["--config", "Backend/alembic.ini"])

    monkeypatch.setattr(module, "build_arg_parser", lambda: parser)
    monkeypatch.setattr(parser, "parse_args", lambda argv=None: args)
    monkeypatch.setattr(
        module.DatabaseUpgradeOrBootstrapRuntime,
        "run",
        lambda self, config_path: "bootstrapped",
    )

    exit_code = module.main([])

    assert exit_code == 0
    assert "Bootstrapped current schema" in capsys.readouterr().out
