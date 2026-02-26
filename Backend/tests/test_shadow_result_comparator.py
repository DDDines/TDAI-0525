from pathlib import Path

from Backend.application.services.shadow_result_comparator import (
    ShadowResultComparator,
)


def test_shadow_result_comparator_persists_variants(tmp_path: Path):
    comparator = ShadowResultComparator(base_dir=tmp_path)
    comparator.record_result(
        context="catalog_import.finalize",
        entity_id=1,
        variant="legacy",
        payload={"status": "IMPORTED", "created": 10},
    )
    comparator.record_result(
        context="catalog_import.finalize",
        entity_id=1,
        variant="oop",
        payload={"status": "IMPORTED", "created": 10},
    )

    stored = (tmp_path / "catalog_import.finalize_1.json").read_text(encoding="utf-8")
    assert "\"legacy\"" in stored
    assert "\"oop\"" in stored
