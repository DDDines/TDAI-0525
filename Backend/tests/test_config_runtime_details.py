"""Additional tests for config runtime branches."""

from __future__ import annotations

import builtins
from pathlib import Path
from types import SimpleNamespace

from Backend.core import config as config_module
from Backend.core.config import ConfigRuntime


def test_load_settings_base_uses_installed_provider():
    """Use the native pydantic-settings provider when available."""
    base_settings, settings_config_dict = config_module._SettingsBaseLoader.load()

    assert base_settings is not None
    assert settings_config_dict is not None


def test_load_settings_base_falls_back_when_pydantic_settings_is_missing(monkeypatch):
    """Fall back to pydantic.BaseSettings when pydantic-settings is unavailable."""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pydantic_settings":
            raise ModuleNotFoundError("forced for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    base_settings, settings_config_dict = config_module._SettingsBaseLoader.load()

    assert base_settings.__module__.startswith("pydantic.v1")
    assert settings_config_dict is dict


def test_load_dotenv_calls_loader_when_file_exists(monkeypatch, tmp_path):
    """Load dotenv files only when the path exists."""
    runtime = ConfigRuntime()
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("X=1", encoding="utf-8")
    captured = {}

    monkeypatch.setattr(
        config_module,
        "load_dotenv",
        lambda *, dotenv_path: captured.setdefault("dotenv_path", dotenv_path),
    )

    runtime.load_dotenv(dotenv_path)

    assert captured["dotenv_path"] == dotenv_path


def test_load_dotenv_logs_warning_when_file_is_missing(monkeypatch, tmp_path):
    """Log a warning instead of loading a missing dotenv file."""
    runtime = ConfigRuntime()
    messages = []

    monkeypatch.setattr(
        config_module.logger,
        "warning",
        lambda message, path: messages.append((message, path)),
    )

    runtime.load_dotenv(tmp_path / "missing.env")

    assert messages
    assert "Arquivo .env nao encontrado" in messages[0][0]


def test_build_default_cors_origins_skips_invalid_entries(monkeypatch):
    """Ignore invalid default origins and keep only validated URLs."""
    runtime = ConfigRuntime()

    class _FakeAdapter:
        def validate_python(self, value):
            if value == "http://localhost":
                raise config_module.ValidationError.from_exception_data("AnyHttpUrl", [])
            return f"ok:{value}"

    monkeypatch.setattr(config_module, "http_url_adapter", _FakeAdapter())

    result = runtime.build_default_cors_origins()

    assert result == ["ok:http://localhost:5173", "ok:http://127.0.0.1:5173"]


def test_parse_cors_origins_skips_invalid_values_and_logs_warning(monkeypatch):
    """Keep valid CORS origins and warn for invalid ones."""
    runtime = ConfigRuntime()
    warnings = []

    class _FakeAdapter:
        def validate_python(self, value):
            if value == "invalid-origin":
                raise config_module.ValidationError.from_exception_data("AnyHttpUrl", [])
            return f"ok:{value}"

    monkeypatch.setattr(config_module, "http_url_adapter", _FakeAdapter())
    monkeypatch.setattr(
        config_module.logger,
        "warning",
        lambda message, origin: warnings.append((message, origin)),
    )

    result = runtime.parse_cors_origins("http://localhost:5173, invalid-origin, http://127.0.0.1:5173")

    assert result == ["ok:http://localhost:5173", "ok:http://127.0.0.1:5173"]
    assert warnings == [("Origem CORS invalida '%s' em BACKEND_CORS_ORIGINS. Sera ignorada.", "invalid-origin")]


def test_configure_database_url_keeps_existing_database_url(monkeypatch):
    """Preserve the configured database URL when one is already set."""
    runtime = ConfigRuntime()
    info_messages = []
    settings_obj = SimpleNamespace(DATABASE_URL="postgresql://db", SQLITE_DB_FILE="ignored.db")

    monkeypatch.setattr(config_module.logger, "info", lambda message, value: info_messages.append((message, value)))

    runtime.configure_database_url(settings_obj)

    assert settings_obj.DATABASE_URL == "postgresql://db"
    assert info_messages == [("DATABASE_URL carregada do .env: %s", "postgresql://db")]


def test_configure_database_url_builds_sqlite_fallback(monkeypatch):
    """Build a SQLite fallback when DATABASE_URL is not configured."""
    runtime = ConfigRuntime()
    info_messages = []
    settings_obj = SimpleNamespace(DATABASE_URL=None, SQLITE_DB_FILE="catalog.db")

    monkeypatch.setattr(config_module.logger, "info", lambda message, value: info_messages.append((message, value)))

    runtime.configure_database_url(settings_obj)

    assert settings_obj.DATABASE_URL.startswith("sqlite:///")
    assert settings_obj.DATABASE_URL.replace("\\", "/").endswith("Backend/catalog.db")
    assert "Usando SQLite" in info_messages[0][0]


def test_configure_cors_origins_uses_parse_results(monkeypatch):
    """Use parsed CORS origins when explicit config exists."""
    runtime = ConfigRuntime()
    settings_obj = SimpleNamespace(cors_origins_str="http://localhost:5173", BACKEND_CORS_ORIGINS=[])

    monkeypatch.setattr(runtime, "parse_cors_origins", lambda raw: [f"parsed:{raw}"])

    runtime.configure_cors_origins(settings_obj)

    assert settings_obj.BACKEND_CORS_ORIGINS == ["parsed:http://localhost:5173"]


def test_configure_cors_origins_falls_back_to_empty_list_on_parse_error(monkeypatch):
    """Use an empty list when explicit CORS parsing explodes."""
    runtime = ConfigRuntime()
    settings_obj = SimpleNamespace(cors_origins_str="bad", BACKEND_CORS_ORIGINS=[])
    errors = []

    monkeypatch.setattr(runtime, "parse_cors_origins", lambda raw: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(
        config_module.logger,
        "error",
        lambda message, exc: errors.append((message, str(exc))),
    )

    runtime.configure_cors_origins(settings_obj)

    assert settings_obj.BACKEND_CORS_ORIGINS == []
    assert errors == [("Erro ao processar BACKEND_CORS_ORIGINS do .env: %s. Usando fallback.", "boom")]


def test_configure_cors_origins_uses_defaults_when_missing(monkeypatch):
    """Use default CORS origins when no explicit env value exists."""
    runtime = ConfigRuntime()
    settings_obj = SimpleNamespace(cors_origins_str=None, BACKEND_CORS_ORIGINS=[])
    info_messages = []

    monkeypatch.setattr(runtime, "build_default_cors_origins", lambda: ["default:a", "default:b"])
    monkeypatch.setattr(config_module.logger, "info", lambda message, value: info_messages.append((message, value)))

    runtime.configure_cors_origins(settings_obj)

    assert settings_obj.BACKEND_CORS_ORIGINS == ["default:a", "default:b"]
    assert info_messages == [("Usando CORS origins padrao: %s", ["default:a", "default:b"])]


def test_build_settings_runs_runtime_pipeline(monkeypatch, tmp_path):
    """Run the full settings build pipeline in order."""
    runtime = ConfigRuntime()
    calls = []
    dotenv_path = tmp_path / ".env"

    monkeypatch.setattr(runtime, "resolve_dotenv_path", lambda: dotenv_path)
    monkeypatch.setattr(runtime, "load_dotenv", lambda path: calls.append(("load_dotenv", path)))
    monkeypatch.setattr(runtime, "configure_database_url", lambda settings_obj: calls.append(("configure_database_url", settings_obj)))
    monkeypatch.setattr(runtime, "configure_cors_origins", lambda settings_obj: calls.append(("configure_cors_origins", settings_obj)))
    monkeypatch.setattr(config_module.logger, "info", lambda *args: calls.append(("log", args[0])))

    settings_obj = runtime.build_settings()

    assert settings_obj is not None
    assert calls[0] == ("load_dotenv", dotenv_path)
    assert calls[1][0] == "configure_database_url"
    assert calls[2][0] == "configure_cors_origins"


def test_settings_include_async_and_celery_defaults():
    """Expose defaults for async dispatch and Celery-backed execution."""
    settings_obj = config_module.Settings(_env_file=None)

    assert settings_obj.ASYNC_DISPATCH_PROVIDER == "background_tasks"
    assert settings_obj.REDIS_URL == "redis://localhost:6379/0"
    assert settings_obj.CELERY_BROKER_URL == "redis://localhost:6379/0"
    assert settings_obj.CELERY_RESULT_BACKEND == "redis://localhost:6379/1"
    assert settings_obj.CELERY_TASK_ALWAYS_EAGER is False
