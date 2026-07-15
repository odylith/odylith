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
        DOMAIN_INTELLIGENCE / "greenfield_preconfirm_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_preconfirm_semantic_drift.py",
        DOMAIN_INTELLIGENCE / "greenfield_preconfirm_semantic_alignment.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_prewrite_gate.py",
        DOMAIN_INTELLIGENCE / "proposal_tribunal.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_title_repair.py",
        DOMAIN_INTELLIGENCE / "greenfield_apply_prewrite.py",
        DOMAIN_INTELLIGENCE / "greenfield_backlog_impact.py",
        DOMAIN_INTELLIGENCE / "greenfield_experience.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "def _mapping_rows" not in source
        assert "from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows" in source

    for path in (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_prewrite_gate.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_component_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_component_contract_differentiation.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "def _dict_rows" not in source
        assert "from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows" in source

    for path in (
        DOMAIN_INTELLIGENCE / "greenfield_backlog_impact.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_component_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_component_contract_differentiation.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "def _component_rows" not in source

    experience_source = (DOMAIN_INTELLIGENCE / "greenfield_experience.py").read_text(encoding="utf-8")
    assert "def _created_rows" not in experience_source

    post_confirm_source = (DOMAIN_INTELLIGENCE / "greenfield_preconfirm_completion.py").read_text(encoding="utf-8")
    assert "def _row_count" not in post_confirm_source
    assert "def _mapping_count" not in post_confirm_source
    assert "from odylith.runtime.domain_intelligence.greenfield_rows import row_count" in post_confirm_source
    assert "from odylith.runtime.domain_intelligence.greenfield_rows import mapping_count" in post_confirm_source
