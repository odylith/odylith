from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    component_spec_preflight_issues,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_modal_grammar_repair import (
    repair_generated_modal_grammar,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)


_RETIRED_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1ba7-v3-final-holdout-regressions.v1.json"
)
_RETIRED = json.loads(_RETIRED_PATH.read_text(encoding="utf-8"))
_CASES = {str(case["case_id"]): case for case in _RETIRED["cases"]}


@pytest.mark.parametrize("case_id", ("gfhi-003", "gfhi-004"))
def test_retired_marker_pair_repairs_modal_grammar_before_sealing(tmp_path: Path, case_id: str) -> None:
    case = _CASES[case_id]

    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path / case_id,
        fallback_title=str(case["name"]),
    )
    first_path = str(intent["first_path"])

    assert not re.search(r"\b(?:can|should)\s+(?:a|an|the)\s+", first_path, flags=re.IGNORECASE)
    assert not re.search(r"\bcan\s+[^.!?]{0,80}\bshould\b", first_path, flags=re.IGNORECASE)
    assert all(term in first_path.casefold() for term in ("review analyst", "observation markers", "decision ribbon", "grouped"))


def test_semantic_path_keys_are_repaired_while_repository_paths_remain_identity() -> None:
    payload = {
        "first_path": "A curator can attaches a note and sees a badge.",
        "raw_path": "A curator can attaches a note and sees a badge.",
        "intended_path": "src/can attaches/to reviews",
        "source_path": "fixtures/can attaches/to reviews.json",
    }

    assert repair_generated_modal_grammar(payload)
    assert payload["first_path"] == "A curator can attach a note and see a badge."
    assert payload["raw_path"] == payload["first_path"]
    assert payload["intended_path"] == "src/can attaches/to reviews"
    assert payload["source_path"] == "fixtures/can attaches/to reviews.json"


@pytest.mark.parametrize(
    ("case_id", "retired_component"),
    (("gfhi-011", "Obsolete Codename Brisk Lantern"), ("gfhi-012", "Retired Phrase Marble Kite")),
)
def test_retired_unicode_pair_projects_typed_transition_support_axis(
    case_id: str,
    retired_component: str,
) -> None:
    first_path = (
        "The curator attaches one résumé note to a café entry and marks the entry reviewed. "
        "The entry moves from unreviewed to reviewed. A blue review badge confirms success."
    )
    systems = [
        "Résumé Note Intake — owns résumé note intake records; First-path action is the curator attaches one résumé note",
        "Entry Reviewed Workflow Support — owns entry reviewed workflow status; First-path action is the curator marks the entry reviewed",
        "From Unreviewed Workflow Support — owns from unreviewed workflow status; First-path action is the entry moves from unreviewed to reviewed",
        "Badge Confirms Success Review Record — owns badge confirms success review records; First-path action is the blue review badge confirms success",
        f"{retired_component} Workflow Support — owns retired phrase workflow status; First-path action is discard {retired_component}",
    ]
    components = confirmed_components(
        label="Café Résumé Board",
        label_slug="cafe-resume-board",
        internal_systems=systems,
        first_path=first_path,
        state_object="The primary state object is a résumé note.",
        proof_boundary="A curator reviews one café entry and sees a blue review badge.",
        external_systems=["local naïve-text index"],
        non_goals=["Never translate the text.", "Never export the text."],
    )
    proposal = {
        "title": "Café Résumé Board",
        "intent": {
            "first_path": first_path,
            "state_object": "The primary state object is a résumé note.",
            "external_systems": ["local naïve-text index"],
        },
        "components": components,
    }

    assert not component_spec_preflight_issues(proposal), case_id
    transition = next(row for row in components if str(row["label"]).startswith("From Unreviewed"))
    assert "moves from unreviewed to reviewed" in str(transition["responsibility"])
    assert "local naïve-text index" in str(transition["responsibility"])
