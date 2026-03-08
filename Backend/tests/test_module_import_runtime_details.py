from __future__ import annotations

import builtins
import importlib
import importlib.util
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module_with_import_failure(*, module_name: str, relative_path: str, failing_prefix: str):
    module_path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(failing_prefix):
            raise ImportError(f"forced import error for {name}")
        return original_import(name, globals, locals, fromlist, level)

    builtins.__import__ = fake_import
    try:
        spec.loader.exec_module(module)
    finally:
        builtins.__import__ = original_import

    return module


def test_runtime_modules_cover_import_fallbacks_for_optional_dependencies():
    web_module = _load_module_with_import_failure(
        module_name="temp_web_data_extractor_module",
        relative_path="Backend/infrastructure/runtime_modules/web_data_extractor_module.py",
        failing_prefix="googleapiclient",
    )
    assert web_module.GOOGLE_API_CLIENT_INSTALLED is False

    file_module = _load_module_with_import_failure(
        module_name="temp_file_processing_module",
        relative_path="Backend/infrastructure/runtime_modules/file_processing_module.py",
        failing_prefix="pdfminer.pdfdocument",
    )
    assert file_module.PDFPasswordIncorrect is None


def test_database_module_reload_covers_sqlite_branches(monkeypatch):
    import sqlalchemy

    calls = []

    def fake_create_engine(url, **kwargs):
        calls.append((url, kwargs))
        return f"engine:{url}"

    monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)
    original_config_module = sys.modules.get("Backend.core.config")

    def load_database_module(database_url: str):
        fake_config_module = ModuleType("Backend.core.config")
        fake_config_module.settings = SimpleNamespace(DATABASE_URL=database_url)
        monkeypatch.setitem(sys.modules, "Backend.core.config", fake_config_module)

        spec = importlib.util.spec_from_file_location(
            f"temp_database_module_{database_url.replace(':', '_').replace('/', '_')}",
            PROJECT_ROOT / "Backend" / "database.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        return module

    try:
        reloaded = load_database_module("sqlite:///:memory:")
        assert calls[-1][0] == "sqlite:///:memory:"
        assert calls[-1][1]["connect_args"] == {"check_same_thread": False}
        assert calls[-1][1]["poolclass"] is reloaded.StaticPool

        load_database_module("sqlite:///catalog.db")
        assert calls[-1][0] == "sqlite:///catalog.db"
        assert calls[-1][1]["connect_args"] == {"check_same_thread": False}
        assert "poolclass" not in calls[-1][1]

        load_database_module("postgresql://catalog:pwd@localhost/catalog")
        assert calls[-1][0] == "postgresql://catalog:pwd@localhost/catalog"
        assert calls[-1][1] == {}
    finally:
        if original_config_module is not None:
            monkeypatch.setitem(sys.modules, "Backend.core.config", original_config_module)
        else:
            sys.modules.pop("Backend.core.config", None)


def test_create_tables_script_covers_import_error_and_main_execution(monkeypatch, capsys):
    create_tables_path = PROJECT_ROOT / "Backend" / "create_tables.py"
    project_root = str(PROJECT_ROOT)

    original_import = builtins.__import__

    def failing_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("Backend.core.config"):
            raise ImportError("config missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", failing_import)
    with pytest.raises(SystemExit):
        runpy.run_path(str(create_tables_path), run_name="__main__")
    output = capsys.readouterr().out
    assert "Iniciando script de criacao de tabelas" in output
    assert "ERRO ao importar modulos" in output

    monkeypatch.setattr(builtins, "__import__", original_import)

    import Backend.core.config as config_module
    import Backend.database as database_module
    import sqlalchemy

    created = []
    original_settings = config_module.settings

    class _FakeMetadata:
        def create_all(self, engine):
            created.append(engine)

    monkeypatch.setattr(sqlalchemy, "create_engine", lambda url: f"engine:{url}")
    monkeypatch.setattr(config_module, "settings", SimpleNamespace(DATABASE_URL="sqlite:///catalog.db"), raising=False)
    monkeypatch.setattr(database_module, "Base", SimpleNamespace(metadata=_FakeMetadata()), raising=False)

    try:
        original_sys_path = list(sys.path)
        while project_root in sys.path:
            sys.path.remove(project_root)
        runpy.run_path(str(create_tables_path), run_name="__main__")
        output = capsys.readouterr().out
        assert created == ["engine:sqlite:///catalog.db"]
        assert "SUCESSO" in output
        assert f"Raiz do projeto ({project_root}) adicionada ao path." in output
    finally:
        sys.path[:] = original_sys_path
        monkeypatch.setattr(config_module, "settings", original_settings, raising=False)
