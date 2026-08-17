from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import (
    render_candidate_intent_markdown,
)


def test_graph_preview_preserves_empty_plural_axes_without_inventing_defaults() -> None:
    rendered = render_candidate_intent_markdown(
        {
            "title": "Automated Watcher",
            "product_story": "The product checks certificates.",
            "state_objects": [],
            "visible_outputs": ["Certificate expiry scan report"],
            "first_path": "The product checks inventory and emits a report.",
            "operational_constraints": [],
            "human_actors": [],
            "external_systems": ["Read-only certificate inventory"],
            "internal_systems": ["Expiry scan service"],
            "assumptions": [],
            "ambiguities": [],
            "proof_boundary": "A report is emitted.",
        }
    )

    assert "## State objects\n- None." in rendered
    assert "## Visible outputs\n- Certificate expiry scan report" in rendered
    assert "## Human actors\n- None." in rendered
    assert "Primary user" not in rendered
    assert "Core workspace" not in rendered


def test_graph_preview_cold_import_does_not_load_legacy_semantic_authorities() -> None:
    root = Path(__file__).resolve().parents[3]
    script = """
import json
import sys
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import render_candidate_intent_markdown
blocked = ('greenfield_confirmed_', 'greenfield_first_path_', 'greenfield_product_intent_envelope')
print(json.dumps(sorted(name for name in sys.modules if any(token in name for token in blocked))))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env={"PYTHONPATH": str(root / "src")},
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "[]"
