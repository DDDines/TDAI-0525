"""Isolated tabular file parsing worker used by subprocess-based hardening."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class TabularParseWorkerRuntime:
    """Class-based worker surface used by the subprocess parser entrypoint."""

    @staticmethod
    def _coerce_json_safe(value: Any) -> Any:
        """Convert pandas/numpy-ish values into JSON-safe primitives."""
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass
        return value

    @classmethod
    def _records_from_dataframe(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Normalize a dataframe into JSON-safe row dictionaries."""
        normalized_df = df.copy()
        normalized_df.dropna(how="all", inplace=True)
        records: List[Dict[str, Any]] = []
        for row in normalized_df.to_dict(orient="records"):
            records.append({str(key): cls._coerce_json_safe(value) for key, value in row.items()})
        return records

    @staticmethod
    def _decode_csv_bytes(content: bytes) -> str:
        """Decode CSV bytes using a conservative fallback chain."""
        try:
            import chardet  # type: ignore

            detection = chardet.detect(content)
            encoding = (detection.get("encoding") or "utf-8").lower()
        except Exception:
            encoding = "utf-8"
        if encoding.startswith("utf-8"):
            return content.decode("utf-8-sig", errors="replace")
        return content.decode(encoding, errors="replace")

    @staticmethod
    def _detect_csv_delimiter(content: str) -> str:
        """Infer CSV delimiter using sniffing with stable fallback rules."""
        sample = "\n".join(content.splitlines()[:5]) if content else ""
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
            return dialect.delimiter
        except Exception:
            first_line = content.splitlines()[0] if content.splitlines() else ""
            if ";" in first_line:
                return ";"
            if "\t" in first_line:
                return "\t"
            return ","

    @classmethod
    def _read_excel_records(cls, input_path: str, sheet_name: Optional[str]) -> List[Dict[str, Any]]:
        """Read Excel sheets and emit JSON-safe row dictionaries."""
        workbook = pd.ExcelFile(input_path)
        sheets = [sheet_name] if sheet_name else workbook.sheet_names
        records: List[Dict[str, Any]] = []
        for sheet in sheets:
            df = pd.read_excel(workbook, sheet_name=sheet)
            records.extend(cls._records_from_dataframe(df))
        return records

    @classmethod
    def _read_csv_records(cls, input_path: str) -> List[Dict[str, Any]]:
        """Read CSV payload and emit JSON-safe row dictionaries."""
        content = Path(input_path).read_bytes()
        decoded = cls._decode_csv_bytes(content)
        delimiter = cls._detect_csv_delimiter(decoded)
        return [dict(row) for row in csv.DictReader(io.StringIO(decoded), delimiter=delimiter)]

    @classmethod
    def _build_excel_preview(cls, input_path: str, max_rows: int) -> Dict[str, Any]:
        """Build a preview payload from the first Excel sheet."""
        df = pd.read_excel(input_path, sheet_name=0)
        headers = [str(col) for col in df.columns]
        sample_rows = [
            {str(key): cls._coerce_json_safe(value) for key, value in row.items()}
            for row in df.head(max_rows).fillna("").to_dict(orient="records")
        ]
        return {"headers": headers, "sample_rows": sample_rows}

    @classmethod
    def _build_csv_preview(cls, input_path: str, max_rows: int) -> Dict[str, Any]:
        """Build a preview payload from CSV content."""
        content = Path(input_path).read_bytes()
        decoded = cls._decode_csv_bytes(content)
        delimiter = cls._detect_csv_delimiter(decoded)
        reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)
        sample_rows: List[Dict[str, Any]] = []
        for idx, row in enumerate(reader):
            if idx >= max_rows:
                break
            sample_rows.append(dict(row))
        return {"headers": reader.fieldnames or [], "sample_rows": sample_rows}

    @staticmethod
    def _apply_memory_limit_from_env() -> None:
        """Apply a soft address-space cap on POSIX when configured."""
        max_memory_mb = int(os.getenv("FILE_PARSE_MAX_MEMORY_MB", "0") or "0")
        if max_memory_mb <= 0 or os.name == "nt":
            return
        try:
            import resource

            limit_bytes = max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
        except Exception:
            return

    @classmethod
    def execute_job(
        cls,
        *,
        mode: str,
        input_path: str,
        output_path: str,
        sheet_name: Optional[str]=None,
        max_rows: int=5,
    ) -> Dict[str, Any]:
        """Execute the requested parse job and persist a structured JSON result."""
        cls._apply_memory_limit_from_env()
        if mode == "excel_ingest":
            payload: Dict[str, Any] = {"ok": True, "records": cls._read_excel_records(input_path, sheet_name)}
        elif mode == "csv_ingest":
            payload = {"ok": True, "records": cls._read_csv_records(input_path)}
        elif mode == "excel_preview":
            payload = {"ok": True, **cls._build_excel_preview(input_path, max_rows)}
        elif mode == "csv_preview":
            payload = {"ok": True, **cls._build_csv_preview(input_path, max_rows)}
        else:
            raise ValueError(f"Modo de parsing nao suportado: {mode}")
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    @staticmethod
    def build_error_payload(exc: Exception) -> Dict[str, Any]:
        """Map worker exceptions to stable structured error codes."""
        if isinstance(exc, MemoryError):
            return {
                "ok": False,
                "error_code": "FILE_PARSE_OOM",
                "error": "Leitura do arquivo excedeu o limite de memoria do parser isolado.",
            }
        return {
            "ok": False,
            "error_code": "FILE_PARSE_UNSAFE",
            "error": str(exc) or exc.__class__.__name__,
        }


class TabularParseWorkerCli:
    """CLI surface that keeps subprocess parsing entrypoints class-based."""

    @staticmethod
    def build_arg_parser() -> argparse.ArgumentParser:
        """Build the CLI parser for the worker entrypoint."""
        parser = argparse.ArgumentParser(description="Parse tabular files in an isolated subprocess.")
        parser.add_argument("--mode", required=True)
        parser.add_argument("--input", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--sheet-name")
        parser.add_argument("--max-rows", type=int, default=5)
        return parser

    @classmethod
    def main(cls, argv: Optional[List[str]]=None) -> int:
        """CLI entrypoint used by the parent runtime."""
        parser = cls.build_arg_parser()
        args = parser.parse_args(argv)
        try:
            TabularParseWorkerRuntime.execute_job(
                mode=args.mode,
                input_path=args.input,
                output_path=args.output,
                sheet_name=args.sheet_name,
                max_rows=args.max_rows,
            )
            return 0
        except Exception as exc:
            payload = TabularParseWorkerRuntime.build_error_payload(exc)
            Path(args.output).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return 1


if __name__ == "__main__":
    raise SystemExit(TabularParseWorkerCli.main())
