from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_workstream_intelligence_list_coercion_stays_in_shared_text_owner() -> None:
    source = (DOMAIN_INTELLIGENCE / "greenfield_workstream_intelligence.py").read_text(encoding="utf-8")

    assert "def _list_values(" not in source
    assert "from odylith.runtime.domain_intelligence.greenfield_text import text_values" in source


def test_project_intelligence_binding_uses_shared_mapping_coercion_owner() -> None:
    source = (DOMAIN_INTELLIGENCE / "project_intelligence_binding.py").read_text(encoding="utf-8")

    assert "def _mapping(" not in source
    assert "from odylith.runtime.common.value_coercion import mapping_copy" in source
