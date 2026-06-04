from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_semantic_context import context_object_phrases
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues


ROOT = Path(__file__).resolve().parents[3]
SEMANTIC_CONTRACT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_semantic_contract.py"
SEMANTIC_CONTEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_semantic_context.py"


def test_component_semantic_context_stays_in_dedicated_owner() -> None:
    contract_source = SEMANTIC_CONTRACT_PATH.read_text(encoding="utf-8")
    context_source = SEMANTIC_CONTEXT_PATH.read_text(encoding="utf-8")

    assert len(contract_source.splitlines()) < 800
    assert "greenfield_component_semantic_context as semantic_context" in contract_source
    assert "def _context_object_phrases" not in contract_source
    assert "def _context_required_phrases" not in contract_source
    assert "def _needs_context_backfill" not in contract_source
    assert "def _looks_actor_term" not in context_source
    assert "greenfield_actor_terms import looks_actor_term as _looks_actor_term" in context_source
    assert "def context_object_phrases" in context_source
    assert "def context_required_phrases" in context_source
    assert "def needs_context_backfill" in context_source
    assert context_object_phrases(
        "Inspector reviews permit note, missing documents, and timeline evidence.",
        label_terms=["permit", "note"],
        description_terms=["review", "document"],
    ) == ("permit note", "missing document")


def test_component_contract_removes_actor_and_handoff_verbs_from_artifact_nouns() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Visit Capture Service",
            "source_system_description": (
                "captures the service visit, equipment identity, observed condition, "
                "technician note, and correction history"
            ),
        },
        proposal={
            "intent": {
                "title": "Field Service Notebook",
                "first_path": (
                    "A technician opens a new service visit, selects the equipment, records the observed "
                    "condition and note, saves the visit, sees it on the equipment timeline, edits the note "
                    "when a mistake is found, and hands off one service visit with equipment identity, "
                    "condition, note, timestamp, timeline visibility, and follow-up evidence."
                ),
            }
        },
        sibling={"label": "Equipment Timeline Service"},
        previous_label="Equipment Directory",
        next_label="Equipment Timeline Service",
        state_label="Service Visit Record",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "hand visit" not in rendered
    assert "technician open" not in rendered
    assert "service visit" in rendered
    assert not generated_semantic_slop_issues(contract)
