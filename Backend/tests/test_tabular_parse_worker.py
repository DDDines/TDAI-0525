"""Tests for the isolated tabular parsing subprocess worker."""

from __future__ import annotations

import builtins
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from Backend.testing.runtime_apis import tabular_parse_worker


def _build_excel_bytes() -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {"sku": "A1", "nome": "Produto A"},
                {"sku": None, "nome": None},
            ]
        ).to_excel(writer, sheet_name="Plan1", index=False)
        pd.DataFrame([{"sku": "B2", "nome": "Produto B"}]).to_excel(
            writer,
            sheet_name="Plan2",
            index=False,
        )
    return buffer.getvalue()


def test_tabular_parse_worker_basic_helpers_cover_json_and_csv_fallbacks(monkeypatch):
    class _Scalar:
        def item(self):
            return 7

    class _BrokenScalar:
        def item(self):
            raise RuntimeError("broken item")

    runtime = tabular_parse_worker.TabularParseWorkerRuntime
    assert runtime._coerce_json_safe(pd.NA) is None
    assert runtime._coerce_json_safe(_Scalar()) == 7
    broken = _BrokenScalar()
    assert runtime._coerce_json_safe(broken) is broken

    records = runtime._records_from_dataframe(
        pd.DataFrame([{"a": 1}, {"a": None}])
    )
    assert records == [{"a": 1}]

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "chardet":
            raise ImportError("sem chardet")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert runtime._decode_csv_bytes("produto".encode("utf-8")) == "produto"
    monkeypatch.setattr(builtins, "__import__", original_import)
    monkeypatch.setitem(
        __import__("sys").modules,
        "chardet",
        SimpleNamespace(detect=lambda content: {"encoding": "latin-1"}),
    )
    assert runtime._decode_csv_bytes(b"\xffproduto") == "ÿproduto"
    __import__("sys").modules.pop("chardet", None)

    assert runtime._detect_csv_delimiter("a;b\n1;2") == ";"

    monkeypatch.setattr(
        tabular_parse_worker.csv.Sniffer,
        "sniff",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad sniff")),
    )
    assert runtime._detect_csv_delimiter("a;b") == ";"
    assert runtime._detect_csv_delimiter("a\tb") == "\t"
    assert runtime._detect_csv_delimiter("a,b") == ","


def test_tabular_parse_worker_reads_real_excel_and_csv_payloads(tmp_path):
    excel_path = tmp_path / "catalog.xlsx"
    excel_path.write_bytes(_build_excel_bytes())

    runtime = tabular_parse_worker.TabularParseWorkerRuntime
    all_records = runtime._read_excel_records(str(excel_path), None)
    assert all_records == [
        {"sku": "A1", "nome": "Produto A"},
        {"sku": "B2", "nome": "Produto B"},
    ]
    plan2_records = runtime._read_excel_records(str(excel_path), "Plan2")
    assert plan2_records == [{"sku": "B2", "nome": "Produto B"}]

    csv_path = tmp_path / "catalog.csv"
    csv_path.write_bytes("sku;nome\nA1;Produto A\n".encode("utf-8-sig"))
    csv_records = runtime._read_csv_records(str(csv_path))
    assert csv_records == [{"sku": "A1", "nome": "Produto A"}]

    excel_preview = runtime._build_excel_preview(str(excel_path), 1)
    assert excel_preview == {
        "headers": ["sku", "nome"],
        "sample_rows": [{"sku": "A1", "nome": "Produto A"}],
    }

    csv_preview = runtime._build_csv_preview(str(csv_path), 1)
    assert csv_preview == {
        "headers": ["sku", "nome"],
        "sample_rows": [{"sku": "A1", "nome": "Produto A"}],
    }
    csv_path.write_bytes("sku;nome\nA1;Produto A\nB2;Produto B\n".encode("utf-8-sig"))
    assert runtime._build_csv_preview(str(csv_path), 1)["sample_rows"] == [
        {"sku": "A1", "nome": "Produto A"}
    ]


def test_tabular_parse_worker_memory_limit_and_error_payload_paths(monkeypatch):
    runtime = tabular_parse_worker.TabularParseWorkerRuntime
    monkeypatch.setenv("FILE_PARSE_MAX_MEMORY_MB", "128")
    monkeypatch.setattr(tabular_parse_worker.os, "name", "posix", raising=False)
    fake_resource = SimpleNamespace(
        RLIMIT_AS=1,
        setrlimit=lambda resource_name, limits: limits == (134217728, 134217728),
    )
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "resource":
            return fake_resource
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    runtime._apply_memory_limit_from_env()
    monkeypatch.setattr(builtins, "__import__", original_import)

    monkeypatch.setenv("FILE_PARSE_MAX_MEMORY_MB", "64")

    def broken_import(name, *args, **kwargs):
        if name == "resource":
            raise ImportError("resource unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)
    runtime._apply_memory_limit_from_env()
    monkeypatch.setattr(builtins, "__import__", original_import)

    monkeypatch.setattr(tabular_parse_worker.os, "name", "nt", raising=False)
    runtime._apply_memory_limit_from_env()

    assert runtime.build_error_payload(MemoryError()) == {
        "ok": False,
        "error_code": "FILE_PARSE_OOM",
        "error": "Leitura do arquivo excedeu o limite de memoria do parser isolado.",
    }
    assert runtime.build_error_payload(RuntimeError("bad parse")) == {
        "ok": False,
        "error_code": "FILE_PARSE_UNSAFE",
        "error": "bad parse",
    }


def test_tabular_parse_worker_execute_job_and_cli_paths(tmp_path, monkeypatch):
    input_path = tmp_path / "input.xlsx"
    output_path = tmp_path / "output.json"
    input_path.write_bytes(b"dummy")

    runtime = tabular_parse_worker.TabularParseWorkerRuntime
    cli = tabular_parse_worker.TabularParseWorkerCli
    monkeypatch.setattr(
        runtime,
        "_read_excel_records",
        lambda input_path, sheet_name=None: [{"sku": "A1", "sheet": sheet_name}],
    )
    monkeypatch.setattr(
        runtime,
        "_read_csv_records",
        lambda input_path: [{"sku": "B2"}],
    )
    monkeypatch.setattr(
        runtime,
        "_build_excel_preview",
        lambda input_path, max_rows: {"headers": ["a"], "sample_rows": [{"a": max_rows}]},
    )
    monkeypatch.setattr(
        runtime,
        "_build_csv_preview",
        lambda input_path, max_rows: {"headers": ["b"], "sample_rows": [{"b": max_rows}]},
    )

    assert runtime.execute_job(
        mode="excel_ingest",
        input_path=str(input_path),
        output_path=str(output_path),
        sheet_name="Plan1",
    ) == {"ok": True, "records": [{"sku": "A1", "sheet": "Plan1"}]}
    assert json.loads(output_path.read_text(encoding="utf-8"))["ok"] is True

    assert runtime.execute_job(
        mode="csv_ingest",
        input_path=str(input_path),
        output_path=str(output_path),
    ) == {"ok": True, "records": [{"sku": "B2"}]}
    assert runtime.execute_job(
        mode="excel_preview",
        input_path=str(input_path),
        output_path=str(output_path),
        max_rows=3,
    ) == {"ok": True, "headers": ["a"], "sample_rows": [{"a": 3}]}
    assert runtime.execute_job(
        mode="csv_preview",
        input_path=str(input_path),
        output_path=str(output_path),
        max_rows=4,
    ) == {"ok": True, "headers": ["b"], "sample_rows": [{"b": 4}]}

    with pytest.raises(ValueError, match="nao suportado"):
        runtime.execute_job(
            mode="unknown",
            input_path=str(input_path),
            output_path=str(output_path),
        )

    parser = cli.build_arg_parser()
    parsed = parser.parse_args(
        ["--mode", "csv_preview", "--input", "in.csv", "--output", "out.json", "--max-rows", "7"]
    )
    assert parsed.max_rows == 7

    monkeypatch.setattr(runtime, "execute_job", lambda **kwargs: {"ok": True})
    assert (
        cli.main(
            ["--mode", "csv_preview", "--input", "in.csv", "--output", str(output_path)]
        )
        == 0
    )

    monkeypatch.setattr(
        runtime,
        "execute_job",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("cli fail")),
    )
    assert (
        cli.main(
            ["--mode", "csv_preview", "--input", "in.csv", "--output", str(output_path)]
        )
        == 1
    )
    assert json.loads(output_path.read_text(encoding="utf-8"))["error"] == "cli fail"
