from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
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
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import first_path_flowchart_mermaid
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_tribunal_substance import check_confirmed_artifact_substance
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


_RETIRED_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1ba7-v3-final-holdout-regressions.v1.json"
)
_RETIRED = json.loads(_RETIRED_PATH.read_text(encoding="utf-8"))
_CASES = {str(case["case_id"]): case for case in _RETIRED["cases"]}


@pytest.fixture(autouse=True)
def _preconfirm_surface_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)


def _proposal_for_case(tmp_path: Path, case_id: str) -> dict[str, object]:
    case = _CASES[case_id]
    prompt = str(case["prompt"])
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path / case_id,
        fallback_title=str(case["name"]),
    )
    return build_greenfield_proposal(
        repo_root=tmp_path / case_id,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )


def _prewrite_quality_issues(
    *,
    root: Path,
    proposal: dict[str, object],
) -> list[str]:
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")

    assert tribunal.passed, tribunal.issues
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=root,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    return greenfield_rendered_package_quality_issues(prewrite.package)


@pytest.mark.parametrize("case_id", ("gfhi-001", "gfhi-002"))
def test_handoff_pair_preserves_declared_visible_result_and_atomic_custody(
    tmp_path: Path,
    case_id: str,
) -> None:
    case = _CASES[case_id]
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path / case_id,
        fallback_title=str(case["name"]),
    )

    assert "The product shows a claim receipt." in str(intent["proof_boundary"])
    assert any(
        atom.get("custody_state") == "accepted_fact"
        and str(atom.get("normalized_value")).casefold() == "a claim receipt"
        for atom in intent["product_intent_authority"]["atomic_facts"]
    )


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
    assert all(term in first_path.casefold() for term in ("review analyst", "observation markers", "decision ribbon"))
    assert re.search(r"\bgroups?\b", first_path, flags=re.IGNORECASE)
    components = [
        {
            "component_id": "review-set",
            "label": "Review Set Workflow Support",
            "release_scope": "first_path_required",
        }
    ]
    semantic_model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title=str(intent["title"]),
            state_object=str(intent["state_object"]),
            first_path=first_path,
            proof_boundary=str(intent["proof_boundary"]),
            visible_result="a decision ribbon",
            human_actors=intent["human_actors"],
            components=components,
        )
    )
    flowchart = first_path_flowchart_mermaid(
        label=str(intent["title"]),
        actors=[str(actor) for actor in intent["human_actors"]],
        components=components,
        first_path=first_path,
        semantic_model=semantic_model,
    )

    step_labels = [
        match.group("label").replace("<br/>", " ").casefold()
        for match in re.finditer(r'^\s*S\d+\["(?P<label>[^"]+)"\]$', flowchart, flags=re.MULTILINE)
    ]

    assert len(step_labels) >= 3
    assert len(step_labels) == len(set(step_labels))
    assert sum("decision ribbon" in label for label in step_labels) == 1
    if case_id == "gfhi-004":
        assert any(label.startswith("confirm ") for label in step_labels)
    assert "decision ribbon" in flowchart.replace("<br/>", " ")
    substance_issues: list[str] = []
    check_confirmed_artifact_substance(
        proposal={
            "intent": {
                "reasoning_mode": "odylith_confirmed_governed_proposal",
                "first_path": first_path,
            },
            "semantic_model": semantic_model,
        },
        backlog=[],
        components=[],
        diagrams=[
            {
                "title": "First Path Sequence",
                "summary": str(intent["product_story"]),
                "read_guide": str(intent["proof_boundary"]),
                "mermaid_source": flowchart,
            }
        ],
        issues=substance_issues,
    )
    assert not [issue for issue in substance_issues if "omits the tail" in issue]


@pytest.mark.parametrize("case_id", ("gfhi-003", "gfhi-004", "gfhi-021"))
def test_disclosed_atlas_state_labels_are_nominal_and_complete(tmp_path: Path, case_id: str) -> None:
    proposal = _proposal_for_case(tmp_path, case_id)
    diagrams = {
        str(row["title"]): str(row["mermaid_source"])
        for row in proposal["diagrams"]
        if str(row["title"]) in {"State and Evidence View", "Release Proof Review"}
    }

    assert set(diagrams) == {"State and Evidence View", "Release Proof Review"}
    for title, source in diagrams.items():
        assert generated_public_copy_issues(f"{case_id} {title}", source) == ()
    assert not _prewrite_quality_issues(root=tmp_path / case_id, proposal=proposal)


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


@pytest.mark.parametrize("case_id", ("gfhi-016", "gfhi-017", "gfhi-019"))
def test_retired_component_package_residuals_compile_cleanly(
    tmp_path: Path,
    case_id: str,
) -> None:
    proposal = _proposal_for_case(tmp_path, case_id)

    assert not component_spec_preflight_issues(proposal)
    assert not _prewrite_quality_issues(root=tmp_path / case_id, proposal=proposal)

    rendered_brief = json.dumps(proposal["project_brief"], ensure_ascii=False)
    components = proposal["components"]
    if case_id == "gfhi-016":
        assert "While Itinerary Stays Staged Delivery Service" in rendered_brief
    elif case_id == "gfhi-017":
        assert all(
            not str(row["component_contract"]["produced_outputs"]).casefold().rstrip(" .").endswith(" the")
            for row in components
        )
    else:
        assert all(
            "draft state" not in str(row["component_contract"]["owned_state"]).casefold()
            for row in components
        )
