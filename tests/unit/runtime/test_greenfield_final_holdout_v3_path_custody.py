from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import (
    prompt_intent_source,
)
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import (
    is_external_dependency_clause,
)
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import (
    source_boundary_rows_from_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import (
    authoritative_prompt_evidence_text,
    is_discarded_evidence_clause,
    rankable_prompt_evidence_text,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)


_RETIRED_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1ba7-v3-final-holdout-regressions.v1.json"
)
_RETIRED_HOLDOUT = json.loads(_RETIRED_HOLDOUT_PATH.read_text(encoding="utf-8"))
_CASES = {str(case["case_id"]): case for case in _RETIRED_HOLDOUT["cases"]}
_ANNOTATIONS = {
    str(annotation["case_id"]): annotation for annotation in _RETIRED_HOLDOUT["annotations"]
}


def _normalized(value: object) -> str:
    return " ".join(str(value).casefold().split())


@pytest.mark.parametrize(
    ("case_id", "actor", "path_terms"),
    (
        ("gfhi-001", "shift coordinator", ("ready intake card", "claim receipt")),
        ("gfhi-004", "review analyst", ("observation markers", "decision ribbon")),
        ("gfhi-007", "release clerk", ("prepared packet", "shelf receipt")),
        ("gfhi-008", "release clerk", ("prepared packet", "shelf receipt")),
        ("gfhi-009", "digest editor", ("queue entries", "review seal")),
        ("gfhi-012", "curator", ("résumé note", "review badge")),
        (
            "gfhi-015",
            "planner",
            ("staged itinerary", "simulated sequence", "dry-run preview"),
        ),
        (
            "gfhi-016",
            "planner",
            ("staged itinerary", "simulated sequence", "dry-run preview"),
        ),
        ("gfhi-017", "mapper", ("verified fragment", "reviewable", "map seal")),
        ("gfhi-018", "index steward", ("candidate heading", "acceptance glyph")),
        ("gfhi-021", "board keeper", ("pending panel", "acceptance token")),
    ),
)
def test_v3_actor_and_first_path_prefer_positive_authoritative_evidence(
    case_id: str,
    actor: str,
    path_terms: tuple[str, ...],
) -> None:
    case = _CASES[case_id]
    source = prompt_intent_source(str(case["prompt"]))
    actor_text = _normalized(source.actor)
    path_text = _normalized(source.first_path)

    assert _normalized(actor) in actor_text
    assert _normalized(actor) in path_text
    assert all(_normalized(term) in path_text for term in path_terms)
    assert all(
        _normalized(term) not in f"{actor_text} {path_text}"
        for term in case["leakage_terms"]
    )


@pytest.mark.parametrize("verb_phrase", ("claim a ready card", "can claim a ready card"))
def test_qualified_actor_replaces_pronoun_without_modal_or_inflection_drift(
    verb_phrase: str,
) -> None:
    source = prompt_intent_source(
        "Build a queue board for a shift coordinator. "
        f"They {verb_phrase} and see a claim receipt."
    )

    assert source.actor == "shift coordinator"
    assert source.first_path == (
        "The shift coordinator can claim a ready card and see a claim receipt"
    )


@pytest.mark.parametrize(
    "case_id",
    (
        "gfhi-001",
        "gfhi-004",
        "gfhi-007",
        "gfhi-008",
        "gfhi-009",
        "gfhi-012",
        "gfhi-015",
        "gfhi-016",
        "gfhi-017",
        "gfhi-018",
        "gfhi-021",
    ),
)
def test_v3_explicit_dependency_declarations_recall_full_bounded_labels(case_id: str) -> None:
    case = _CASES[case_id]
    annotation = _ANNOTATIONS[case_id]
    expected = [str(row["value"]) for row in annotation["explicit_systems"]]

    assert source_boundary_rows_from_evidence(str(case["prompt"])) == expected


@pytest.mark.parametrize(
    "prompt",
    (
        "A planner reads a report and approves it.",
        "Create a product that uses a report.",
        "Use the product to review a report.",
        "The planning team is read-only.",
        "The product is read-only.",
        "Read the report.",
    ),
)
def test_explicit_dependency_grammar_rejects_people_products_and_generic_reports(
    prompt: str,
) -> None:
    assert source_boundary_rows_from_evidence(prompt) == []


def test_title_only_final_edit_preserves_earlier_boundary_custody() -> None:
    prompt = (
        "Build an intake board. A clerk reviews one packet. Use SignalFlow. "
        "Final edit: rename the product Intake Board."
    )

    assert source_boundary_rows_from_evidence(prompt) == ["SignalFlow"]


def test_use_system_to_complete_workflow_keeps_boundary_and_path_separate() -> None:
    prompt = "Use SignalFlow to load one intake packet and show a review queue."
    source = prompt_intent_source(prompt)

    assert source_boundary_rows_from_evidence(prompt) == ["SignalFlow"]
    assert not is_external_dependency_clause(prompt)
    assert "load one intake packet" in source.first_path
    assert "show a review queue" in source.first_path


@pytest.mark.parametrize(
    ("prompt", "expected_path"),
    (
        (
            "Read from SignalFlow to prepare one review packet and show the result.",
            "Read from SignalFlow to prepare one review packet and show the result",
        ),
        (
            "Read from SignalFlow. Prepare one review packet. Show the result.",
            "Prepare one review packet. Show the result",
        ),
    ),
)
def test_read_dependency_preserves_attached_or_following_workflow(
    prompt: str,
    expected_path: str,
) -> None:
    source = prompt_intent_source(prompt)

    assert source_boundary_rows_from_evidence(prompt) == ["SignalFlow"]
    assert source.first_path == expected_path


def test_final_request_phrase_inside_workflow_is_not_a_revision_boundary() -> None:
    prompt = (
        "ReviewHub helps a clerk review one intake packet, then issue the final request: "
        "approval notice, and see the signed result."
    )

    assert authoritative_prompt_evidence_text(prompt) == prompt
    assert prompt_intent_source(prompt).first_path == prompt.rstrip(".")


def test_final_request_field_is_ordinary_product_evidence() -> None:
    prompt = "Final request: ReviewHub helps a clerk review one intake packet and see the signed result."

    assert authoritative_prompt_evidence_text(prompt) == prompt
    assert rankable_prompt_evidence_text(prompt) == prompt
    assert prompt_intent_source(prompt).first_path == (
        "ReviewHub helps a clerk review one intake packet and see the signed result"
    )


def test_sentence_boundary_final_request_composes_command_audience_path(tmp_path: Path) -> None:
    prompt = (
        "Build a review hub for a clerk to approve one request. "
        "Final request: record the approval reason and see the signed result."
    )
    expected_path = (
        "Clerk can approve one request. record the approval reason and see the signed result"
    )

    assert authoritative_prompt_evidence_text(prompt) == prompt
    source = prompt_intent_source(prompt)
    assert source.actor == "clerk"
    assert source.first_path == expected_path

    staged = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Review Hub",
    )
    assert staged["human_actors"] == [
        "Clerk: needs the product to approve one request and keep the result visible and reviewable"
    ]
    assert staged["first_path"] == f"{expected_path}."


@pytest.mark.parametrize(
    ("prompt", "expected_source_path", "expected_staged_path", "expected_actor_row"),
    (
        (
            "LabelClean helps a reviewer remove placeholder tokens from a public report and see the cleaned report.",
            "LabelClean helps a reviewer remove placeholder tokens from a public report and see the cleaned report",
            "LabelClean helps a reviewer remove placeholder tokens from a public report and see the cleaned report.",
            "Labelclean reviewer: needs the product to remove placeholder tokens from a public report and see the cleaned report and keep the result visible and reviewable",
        ),
        (
            "LabelClean helps a reviewer exclude obsolete labels from a public report and see the cleaned report.",
            "Reviewer can exclude obsolete labels from a public report and see the cleaned report. The product shows the cleaned report",
            "Reviewer can exclude obsolete labels from a public report and see the cleaned report. The product shows the cleaned report.",
            "Labelclean reviewer: needs the product to exclude obsolete labels from a public report and see the cleaned report and keep the result visible and reviewable",
        ),
        (
            "LabelClean helps a reviewer retire a scratch title before publishing the approved title and see the public page.",
            "LabelClean helps a reviewer retire a scratch title before publishing the approved title and see the public page",
            "LabelClean helps a reviewer retire a scratch title before publishing the approved title and see the public page.",
            "Labelclean reviewer: needs the product to retire a scratch title before publishing the approved title and see the public page and keep the result visible and reviewable",
        ),
    ),
)
def test_placeholder_like_artifacts_remain_rankable_workflow_objects(
    tmp_path: Path,
    prompt: str,
    expected_source_path: str,
    expected_staged_path: str,
    expected_actor_row: str,
) -> None:
    assert not is_discarded_evidence_clause(prompt)
    assert rankable_prompt_evidence_text(prompt) == prompt
    source = prompt_intent_source(prompt)
    assert source.actor == "reviewer"
    assert source.first_path == expected_source_path

    staged = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Fallback",
    )
    assert staged["human_actors"] == [expected_actor_row]
    assert staged["first_path"] == expected_staged_path


def test_actor_owned_placeholder_action_keeps_split_archive_outcome() -> None:
    prompt = (
        "A reviewer removes placeholder tokens from a public report. "
        "The reviewer archives the cleaned report."
    )

    assert rankable_prompt_evidence_text(prompt) == prompt
    assert prompt_intent_source(prompt).first_path == prompt.rstrip(".")


@pytest.mark.parametrize(
    "clause",
    (
        "The obsolete scratch label Juniper Comet must not enter the governed package.",
        "Discard the superseded note-name Quartz Ferry.",
        "A discarded experiment called Nickel Orchard is not part of the intent.",
        "The placeholder Copper Parasol is superseded.",
        "The trial label Mossy Compass is excluded.",
        "Research note: the superseded token Silver Oar is not part of the product.",
    ),
)
def test_retired_negative_custody_clauses_remain_unrankable(clause: str) -> None:
    assert is_discarded_evidence_clause(clause)
    assert rankable_prompt_evidence_text(clause) == ""


@pytest.mark.parametrize("case_id", ("gfhi-008", "gfhi-009", "gfhi-015", "gfhi-018"))
def test_v3_path_ranking_does_not_drop_negative_constraint_custody(
    tmp_path: Path,
    case_id: str,
) -> None:
    case = _CASES[case_id]
    annotation = _ANNOTATIONS[case_id]
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    constraints = " ".join([*intent["operational_constraints"], *intent["non_goals"]])

    assert all(
        _normalized(row["value"]) in _normalized(constraints)
        for row in annotation["critical_constraints"]
    )
