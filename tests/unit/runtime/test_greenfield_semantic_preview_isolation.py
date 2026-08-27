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
            "presentation": {
                "title": "Automated Watcher",
                "status": "working_assumption",
                "source_refs": [],
            },
            "product_story": "The product checks certificates.",
            "state_objects": [],
            "visible_outputs": ["Certificate expiry scan report"],
            "first_path": "The product checks inventory and emits a report.",
            "policy_boundaries": [],
            "product_boundaries": ["Runs inside the consumer repository."],
            "human_actors": [],
            "external_systems": ["Read-only certificate inventory"],
            "owned_capabilities": [
                "Expiry scan: Check certificates and emit the expiry report."
            ],
            "assumptions": [],
            "ambiguities": [],
            "proof_boundary": "A report is emitted.",
        }
    )

    assert "## State objects\n- None." in rendered
    assert "## Visible outputs\n- Certificate expiry scan report" in rendered
    assert "## Human actors\n- None." in rendered
    assert "> Presentation: Working title assumption; editable before confirmation." in rendered
    assert "## Product boundaries\n- Runs inside the consumer repository." in rendered
    assert "## Owned capabilities\n- Expiry scan: Check certificates" in rendered
    assert "Internal product systems" not in rendered
    assert "Primary user" not in rendered
    assert "Core workspace" not in rendered


def test_graph_preview_renders_current_typed_policy_boundary_without_reinterpretation() -> None:
    rendered = render_candidate_intent_markdown(
        {
            "title": "Handoff board",
            "presentation": {
                "title": "Handoff board",
                "status": "working_assumption",
                "source_refs": [],
            },
            "product_story": "A shift coordinator claims one intake card.",
            "state_objects": ["intake card"],
            "visible_outputs": ["claim receipt"],
            "first_path": "Select one ready intake card and mark it claimed.",
            "policy_boundaries": [
                {
                    "label": "Never reassign a card automatically.",
                    "modalities": ["prohibited"],
                    "statement": "Never reassign a card automatically.",
                }
            ],
            "product_boundaries": ["The handoff board is repo-local."],
            "human_actors": [
                {
                    "actor_fact_id": "actor.0",
                    "label": "shift coordinator",
                    "owned_step_fact_ids": ["step.0"],
                    "owned_actions": ["Select one ready intake card."],
                }
            ],
            "external_systems": ["local duty roster"],
            "owned_capabilities": [
                "Handoff board First Path: Deliver the sealed first-path workflow."
            ],
            "assumptions": [],
            "ambiguities": [],
            "proof_boundary": "The claim receipt is visible.",
        }
    )

    assert "- prohibited: Never reassign a card automatically" in rendered
    assert "- The handoff board is repo-local." in rendered
    assert "- shift coordinator — Select one ready intake card" in rendered
    assert "- None." not in rendered.split("## Policy boundaries", 1)[1].split("##", 1)[0]
    assert "Internal product systems" not in rendered


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
