from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import best_component_node_for_text
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps


def _diagram_slugs() -> dict[str, str]:
    return {
        "context": "context",
        "sequence": "sequence",
        "state_evidence": "state-evidence",
        "component_boundaries": "component-boundaries",
        "ownership": "ownership",
        "proof_review": "proof-review",
    }


def test_atlas_component_cards_explain_specific_boundary_without_path_boilerplate() -> None:
    rows = confirmed_diagrams(
        label="Operations Platform",
        diagram_slugs=_diagram_slugs(),
        components=[
            {
                "component_id": "source-import",
                "label": "Source Import Adapter",
                "kind": "adapter",
                "responsibility": "External source import",
            },
            {
                "component_id": "decision-scoring",
                "label": "Decision Scoring Engine",
                "kind": "service",
                "responsibility": "Scores candidate decisions with confidence, inputs, and rule version.",
            },
            {
                "component_id": "state-ledger",
                "label": "State Ledger Service",
                "kind": "service",
                "responsibility": "Records versioned state changes, actor, timestamp, and source evidence.",
            },
            {
                "component_id": "exception-review",
                "label": "Exception Review Workflow",
                "kind": "service",
                "responsibility": "Coordinates exception review, handoff, blocked-state recovery, and final outcome.",
            },
            {
                "component_id": "user-review",
                "label": "User Review Surface",
                "kind": "client",
                "responsibility": "Review screen for user approval and correction.",
            },
            {
                "component_id": "assignment-planner",
                "label": "Assignment Planner",
                "kind": "service",
                "responsibility": "Assigns jobs to available resources while respecting priority, capacity, and constraints.",
            },
        ],
    )

    components = {row["name"]: row["description"] for row in rows[0]["components"]}
    encoded = json.dumps(rows)

    assert components["Source Import Adapter"] == (
        "Translates external source import inputs into product-owned records and preserves source provenance. "
        "Reviewers need to see which source supplied the input and what normalized result entered the product."
    )
    assert components["Decision Scoring Engine"] == (
        "Scores candidate decisions with confidence, inputs, and rule version. Reviewers need to see the inputs, "
        "rule version, result, and downstream decision that depended on it."
    )
    assert components["State Ledger Service"] == (
        "Records versioned state changes, actor, timestamp, and source evidence. Reviewers need to see the "
        "versioned state, source evidence, and decisions that depended on this record."
    )
    assert components["Exception Review Workflow"] == (
        "Coordinates exception review, handoff, blocked-state recovery, and final outcome. Reviewers need to see "
        "each responsibility transfer, failure state, recovery action, and final outcome."
    )
    assert components["User Review Surface"] == (
        "Presents review screen for user approval and correction to users and captures the action or decision the "
        "product needs next. Reviewers need to see what the user saw, submitted, corrected, or approved and which "
        "product state changed after that action."
    )
    assert components["Assignment Planner"] == (
        "Owns product responsibility to assign jobs to available resources while respecting priority, capacity, "
        "and constraints. Reviewers need to see what this boundary receives, produces, records, and makes available next."
    )
    assert "accepted first release path" not in encoded
    assert "for the accepted first" not in encoded
    assert "Owns the responsibility to" not in encoded
    assert "Owns the product responsibility" not in encoded
    assert "hands off" not in encoded
    assert "part of the path" not in encoded
    assert "Design pressure" not in encoded
    assert "Domain evidence" not in encoded
    assert "**" not in encoded
    assert "`" not in encoded


def test_confirmed_diagram_text_model_stays_in_dedicated_owner() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    diagram_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagrams.py"
    text_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagram_text.py"
    diagram_source = diagram_owner.read_text(encoding="utf-8")
    text_source = text_owner.read_text(encoding="utf-8")

    assert len(diagram_source.splitlines()) < 800
    assert "greenfield_confirmed_diagram_text as diagram_text" in diagram_source
    assert "def _component_description" not in diagram_source
    assert "def _brief_proof_boundary" not in diagram_source
    assert "def _short_label" not in diagram_source
    assert "def component_description" in text_source
    assert "def brief_proof_boundary" in text_source
    assert "def short_label" in text_source


def test_sequence_event_steps_stay_in_dedicated_owner() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    diagram_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py"
    steps_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_sequence_steps.py"
    diagram_source = diagram_owner.read_text(encoding="utf-8")
    steps_source = steps_owner.read_text(encoding="utf-8")

    assert len(diagram_source.splitlines()) < 800
    assert "from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps" in diagram_source
    assert "sequence_event_steps(first_path, semantic_model=semantic_model)" in diagram_source
    assert "sequence_event_steps(first_path, semantic_model=semantic_model, dedupe=True)" in diagram_source
    for moved in (
        "def _semantic_event_steps",
        "def _drop_launcher_only_steps",
        "def _launcher_only_step",
        "def _normalize_event_step",
        "def _first_path_steps",
        "def _expand_compound_steps",
        "def _dedupe_steps",
    ):
        assert moved not in diagram_source
        assert moved in steps_source
    assert "def sequence_event_steps" in steps_source


def test_sequence_diagram_term_routing_uses_shared_index() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    diagram_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py"
    index_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py"
    diagram_source = diagram_owner.read_text(encoding="utf-8")
    index_source = index_owner.read_text(encoding="utf-8")

    assert "def ordered_terms" in index_source
    assert "stem_ing" in index_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms"
        in diagram_source
    )
    assert "def _domain_terms" not in diagram_source
    assert "normalize_domain_token" not in diagram_source
    assert "stem_ing=True" in diagram_source

    assert ordered_terms("Race readings and reviewing status.", stopwords={"and"}, stem_ing=True) == [
        "race",
        "read",
        "review",
        "status",
    ]
    assert (
        best_component_node_for_text(
            "reviewing race readings",
            components=[
                {"label": "Generic queue", "responsibility": "stores status"},
                {"label": "Race read review", "responsibility": "reviews telemetry reading"},
            ],
        )
        == "component2"
    )


def test_sequence_event_steps_preserve_action_later_decision_tail() -> None:
    steps = sequence_event_steps(
        "A user adds a person to follow, chooses approved public data sources, sees recent activity signals with source links, "
        "reviews risk and context summaries, adds selected items to a watchlist, and records whether they plan to research, "
        "ignore, or act later.",
        dedupe=True,
    )

    assert steps[-1] == "A user records whether they plan to research, ignore, or act later"
