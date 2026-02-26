from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from Backend.core.logging_config import get_logger

logger = get_logger(__name__)


class ShadowResultComparator:
    """Persiste e compara saidas legacy/oop para analise de regressao."""

    def __init__(self, base_dir: Path | None = None) -> None:
        backend_root = Path(__file__).resolve().parents[2]
        self._base_dir = base_dir or (backend_root / "logs" / "shadow_compare")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def record_result(
        self,
        *,
        context: str,
        entity_id: int | str,
        variant: str,
        payload: Dict[str, Any],
    ) -> None:
        safe_context = context.replace("/", "_").replace(" ", "_")
        target_path = self._base_dir / f"{safe_context}_{entity_id}.json"
        current = self._load_file(target_path)
        normalized_payload = self._normalize_for_compare(payload)
        current[str(variant)] = normalized_payload
        self._save_file(target_path, current)

        legacy_payload = current.get("legacy")
        oop_payload = current.get("oop")
        if legacy_payload is None or oop_payload is None:
            logger.info(
                "SHADOW result compare pendente (%s id=%s): aguardando variante complementar",
                context,
                entity_id,
            )
            return

        if legacy_payload == oop_payload:
            logger.info("SHADOW result compare OK (%s id=%s)", context, entity_id)
            return

        logger.warning(
            "SHADOW result compare DIFF (%s id=%s)\nlegacy=%s\noop=%s",
            context,
            entity_id,
            json.dumps(legacy_payload, ensure_ascii=False, sort_keys=True),
            json.dumps(oop_payload, ensure_ascii=False, sort_keys=True),
        )

    def _load_file(self, path: Path) -> Dict[str, Any]:
        try:
            if not path.exists():
                return {}
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_file(self, path: Path, payload: Dict[str, Any]) -> None:
        try:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Falha ao salvar comparacao shadow em %s: %s", path, exc)

    def _normalize_for_compare(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {
                str(k): self._normalize_for_compare(v)
                for k, v in sorted(value.items(), key=lambda i: str(i[0]))
            }
        if isinstance(value, (list, tuple, set)):
            return [self._normalize_for_compare(item) for item in value]
        return repr(value)
