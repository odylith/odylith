from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
GREENFIELD_ROWS_PATH = DOMAIN_INTELLIGENCE / "greenfield_rows.py"


def test_greenfield_mapping_row_coercion_stays_in_shared_owner() -> None:
    rows_source = GREENFIELD_ROWS_PATH.read_text(encoding="utf-8")
    assert "def mapping_rows" in rows_source
    assert not (DOMAIN_INTELLIGENCE / "greenfield_post_confirm_rows.py").exists()

    for path in (
        DOMAIN_INTELLIGENCE / "greenfield_post_confirm_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_post_confirm_semantic_drift.py",
        DOMAIN_INTELLIGENCE / "greenfield_post_confirm_semantic_alignment.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_prewrite_gate.py",
        DOMAIN_INTELLIGENCE / "proposal_tribunal.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_title_repair.py",
        DOMAIN_INTELLIGENCE / "greenfield_apply_prewrite.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "def _mapping_rows" not in source
        assert "from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows" in source
