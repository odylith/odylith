from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_artifact_graph_reads_canonical_intent_without_legacy_workstream_payload() -> None:
    source = (DOMAIN_INTELLIGENCE / "artifact_graph.py").read_text(encoding="utf-8")

    assert "def canonical_graph_from_workstream" in source
    assert 'get("domain_intelligence")' not in source
    assert "def graph_layer(" not in source


def test_project_intelligence_binding_uses_shared_mapping_coercion_owner() -> None:
    source = (DOMAIN_INTELLIGENCE / "project_intelligence_binding.py").read_text(encoding="utf-8")

    assert "def _mapping(" not in source
    assert "from odylith.runtime.common.value_coercion import mapping_copy" in source
