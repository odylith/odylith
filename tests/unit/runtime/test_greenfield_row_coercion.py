from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
GREENFIELD_ROWS_PATH = DOMAIN_INTELLIGENCE / "greenfield_rows.py"


def test_greenfield_mapping_row_coercion_stays_in_shared_owner() -> None:
    rows_source = GREENFIELD_ROWS_PATH.read_text(encoding="utf-8")
    assert "def mapping_rows" in rows_source
    assert "def dict_rows" in rows_source
    assert "def row_count" in rows_source
    assert "def mapping_count" in rows_source
    assert not (DOMAIN_INTELLIGENCE / "greenfield_preconfirm_rows.py").exists()

    for path in (
        DOMAIN_INTELLIGENCE / "greenfield_apply_prewrite.py",
        DOMAIN_INTELLIGENCE / "greenfield_prewrite_stale_cleanup.py",
        DOMAIN_INTELLIGENCE / "greenfield_semantic_component_package.py",
        DOMAIN_INTELLIGENCE / "greenfield_semantic_delivery.py",
        DOMAIN_INTELLIGENCE / "greenfield_semantic_memory.py",
        DOMAIN_INTELLIGENCE / "greenfield_semantic_package_validation.py",
        DOMAIN_INTELLIGENCE / "greenfield_semantic_traceability.py",
        DOMAIN_INTELLIGENCE / "greenfield_release_commit.py",
        DOMAIN_INTELLIGENCE / "greenfield_traceability_commit.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "def _mapping_rows" not in source
        assert "from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows" in source
