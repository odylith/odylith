from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_findings
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.greenfield_project_judgment import project_story_semantic_issues
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import (
    intent_hypothesis_from_operator_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    GreenfieldClarificationRequired,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import (
    explicit_product_title_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


_RETIRED_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-ba25-final-holdout-regressions.v1.json"
)
_RETIRED_HOLDOUT = json.loads(_RETIRED_HOLDOUT_PATH.read_text(encoding="utf-8"))
_RETIRED_HOLDOUT_CASES = tuple(_RETIRED_HOLDOUT["cases"])
_AA51_RETIRED_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-aa51-final-holdout-regressions.v1.json"
)
_AA51_RETIRED_HOLDOUT = json.loads(_AA51_RETIRED_HOLDOUT_PATH.read_text(encoding="utf-8"))
_AA51_AUTHORITY_CASES = tuple(
    case for case in _AA51_RETIRED_HOLDOUT["cases"] if case["expectation"] == "clarification_required"
)
_87E277_RETIRED_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-87e277-final-holdout-regressions.v1.json"
)
_87E277_RETIRED_HOLDOUT = json.loads(_87E277_RETIRED_HOLDOUT_PATH.read_text(encoding="utf-8"))
_87E277_ANNOTATIONS = {
    str(annotation["case_id"]): annotation for annotation in _87E277_RETIRED_HOLDOUT["annotations"]
}
_87E277_CLARIFICATION_CASES = tuple(
    case for case in _87E277_RETIRED_HOLDOUT["cases"] if case["expectation"] == "clarification_required"
)
_87E277_EXTERNAL_SYSTEM_CASES = tuple(
    case
    for case in _87E277_RETIRED_HOLDOUT["cases"]
    if case["expectation"] == "transaction_committed"
    and _87E277_ANNOTATIONS[str(case["case_id"])]["explicit_systems"]
)
_87E277_SEALED_SYSTEM_CASES = tuple(
    case
    for case in _87E277_EXTERNAL_SYSTEM_CASES
    if case["case_id"] in {
        "gfh-20260808-v2-01",
        "gfh-20260808-v2-02",
        "gfh-20260808-v2-14",
        "gfh-20260808-v2-20",
    }
)
_CF410_RETIRED_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-cf410-final-holdout-regressions.v1.json"
)
_CF410_RETIRED_HOLDOUT = json.loads(_CF410_RETIRED_HOLDOUT_PATH.read_text(encoding="utf-8"))
_CF410_ANNOTATIONS = {
    str(annotation["case_id"]): annotation for annotation in _CF410_RETIRED_HOLDOUT["annotations"]
}
_CF410_CLARIFICATION_CASES = tuple(
    case for case in _CF410_RETIRED_HOLDOUT["cases"] if case["expectation"] == "clarification_required"
)
_CF410_FALSE_CLARIFICATION_CASE_IDS = frozenset(
    {
        "gfh-20260808-v3-03",
        "gfh-20260808-v3-05",
        "gfh-20260808-v3-06",
        "gfh-20260808-v3-15",
        "gfh-20260808-v3-19",
    }
)
_CF410_FALSE_CLARIFICATION_CASES = tuple(
    case
    for case in _CF410_RETIRED_HOLDOUT["cases"]
    if case["case_id"] in _CF410_FALSE_CLARIFICATION_CASE_IDS
)
_CF410_MISSING_SYSTEM_CASE_IDS = frozenset(
    {
        "gfh-20260808-v3-01",
        "gfh-20260808-v3-08",
        "gfh-20260808-v3-09",
        "gfh-20260808-v3-17",
    }
)
_CF410_MISSING_SYSTEM_CASES = tuple(
    case
    for case in _CF410_RETIRED_HOLDOUT["cases"]
    if case["case_id"] in _CF410_MISSING_SYSTEM_CASE_IDS
)
_CF410_COLD_CHAIN_ACTOR_CASES = tuple(
    case
    for case in _CF410_RETIRED_HOLDOUT["cases"]
    if case["case_id"] in {
        "gfh-20260808-v3-04",
        "gfh-20260808-v3-06",
    }
)
_CF410_COLD_CHAIN_BRIEF = next(
    case for case in _CF410_RETIRED_HOLDOUT["cases"] if case["case_id"] == "gfh-20260808-v3-05"
)
_1C54_RETIRED_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1c54-final-holdout-regressions.v1.json"
)
_1C54_RETIRED_HOLDOUT = json.loads(_1C54_RETIRED_HOLDOUT_PATH.read_text(encoding="utf-8"))
_1C54_ANNOTATIONS = {
    str(annotation["case_id"]): annotation for annotation in _1C54_RETIRED_HOLDOUT["annotations"]
}
_1C54_CLARIFICATION_CASES = tuple(
    case for case in _1C54_RETIRED_HOLDOUT["cases"] if case["expectation"] == "clarification_required"
)
_1C54_FALSE_CLARIFICATION_CASES = tuple(
    case
    for case in _1C54_RETIRED_HOLDOUT["cases"]
    if case["case_id"] in {"gfh-20260809-03", "gfh-20260809-10", "gfh-20260809-20"}
)
_1C54_CUSTODY_CASE_IDS = frozenset(
    {
        "gfh-20260809-05",
        "gfh-20260809-08",
        "gfh-20260809-12",
        "gfh-20260809-13",
        "gfh-20260809-15",
        "gfh-20260809-16",
        "gfh-20260809-17",
        "gfh-20260809-19",
        "gfh-20260809-22",
        "gfh-20260809-23",
    }
)
_1C54_CUSTODY_CASES = tuple(
    case for case in _1C54_RETIRED_HOLDOUT["cases"] if case["case_id"] in _1C54_CUSTODY_CASE_IDS
)


def _material_field_key(value: object) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def _contains_normalized(values: object, expected: object) -> bool:
    rows = values if isinstance(values, (list, tuple)) else (values,)
    haystack = " ".join(" ".join(str(row).casefold().split()) for row in rows)
    needle = " ".join(str(expected).casefold().split())
    return bool(needle and needle in haystack)


@pytest.fixture(autouse=True)
def _preconfirm_surface_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)


def test_failed_final_holdout_is_marked_disclosed_and_retired() -> None:
    assert _RETIRED_HOLDOUT["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert _RETIRED_HOLDOUT["disclosed"] is True
    assert len(_RETIRED_HOLDOUT_CASES) == 24


def test_87e277_failed_holdout_is_marked_disclosed_and_retired() -> None:
    assert _87E277_RETIRED_HOLDOUT["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert _87E277_RETIRED_HOLDOUT["disclosed"] is True
    assert len(_87E277_RETIRED_HOLDOUT["cases"]) == 24
    assert len(_87E277_RETIRED_HOLDOUT["annotations"]) == 24


def test_cf410_failed_holdout_is_marked_disclosed_and_retired() -> None:
    assert _CF410_RETIRED_HOLDOUT["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert _CF410_RETIRED_HOLDOUT["disclosed"] is True
    assert _CF410_RETIRED_HOLDOUT["retired_from"]["holdout_sha256"] == (
        "2713e5b4cbd0abe0c7cc1e517c063c29ca3cdd029c2db5de764ecc8c03c9cfb5"
    )
    assert len(_CF410_RETIRED_HOLDOUT["cases"]) == 24
    assert len(_CF410_RETIRED_HOLDOUT["annotations"]) == 24


def test_1c54_failed_holdout_is_marked_disclosed_and_retired() -> None:
    assert _1C54_RETIRED_HOLDOUT["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert _1C54_RETIRED_HOLDOUT["disclosed"] is True
    assert _1C54_RETIRED_HOLDOUT["retired_from"] == {
        "product_revision": "1c54cb3403d482bdb72559aae5f9a52185cc242e",
        "holdout_sha256": "d48f7180bfd129a02609ac17289b1cf3233eeeba1f313a7aac16564e2a1a5a7e",
        "evaluation_manifest_sha256": "c1efaaf96b12e14c5c81387bd189797fafb1616f40e08680c5d82481d99df09c",
        "result_sha256": "8c6286bb28ccfa7c490d259861499ed8979863b20da4e9ccb6ded41156a6da90",
        "evaluated_on": "2026-08-09",
    }
    assert len(_1C54_RETIRED_HOLDOUT["cases"]) == 24
    assert len(_1C54_RETIRED_HOLDOUT["annotations"]) == 24


@pytest.mark.parametrize(
    "case",
    _1C54_CLARIFICATION_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_1c54_material_decisions_ask_one_focused_question_before_staging(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    annotation = _1C54_ANNOTATIONS[str(case["case_id"])]

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=str(case["prompt"]),
            repo_root=tmp_path,
            fallback_title=str(case["name"]),
        )

    assert error.value.required_fields == tuple(annotation["expected_question_fields"])
    assert error.value.question.count("?") == 1
    assert len(error.value.question) <= 280
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize(
    "case",
    _1C54_FALSE_CLARIFICATION_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_1c54_complete_distributed_paths_reach_candidate_materialization(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )

    assert intent["product_intent_authority"]["materiality_status"] == "passed"
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.json").is_file()


@pytest.mark.parametrize(
    "case",
    _1C54_CUSTODY_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_1c54_explicit_systems_and_critical_constraints_reach_sealed_fact_custody(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    annotation = _1C54_ANNOTATIONS[str(case["case_id"])]
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    accepted_facts = [
        atom["normalized_value"]
        for atom in intent["product_intent_authority"]["atomic_facts"]
        if atom["custody_state"] == "accepted_fact"
    ]
    constraint_truth = [*intent["operational_constraints"], *intent["non_goals"]]

    assert all(
        _contains_normalized(intent["external_systems"], system)
        for system in annotation["explicit_systems"]
    )
    assert all(
        _contains_normalized(constraint_truth, constraint)
        for constraint in annotation["critical_constraints"]
    )
    assert all(
        _contains_normalized(accepted_facts, fact)
        for fact in [*annotation["explicit_systems"], *annotation["critical_constraints"]]
    )


def test_1c54_compact_negative_field_does_not_absorb_the_evidence_envelope(tmp_path: Path) -> None:
    case = next(case for case in _1C54_CUSTODY_CASES if case["case_id"] == "gfh-20260809-08")
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )

    assert [row.rstrip(".") for row in intent["non_goals"]] == [
        "never turn a missing trace into a normal reading"
    ]
    assert all("Brief // Product:" not in row for row in intent["non_goals"])


@pytest.mark.parametrize(
    "case",
    _CF410_CLARIFICATION_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_cf410_material_questions_preserve_source_labels_and_write_nothing(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    annotation = _CF410_ANNOTATIONS[str(case["case_id"])]
    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=str(case["prompt"]),
            repo_root=tmp_path,
            fallback_title=str(case["name"]),
        )

    expected_fields = tuple(_material_field_key(field) for field in annotation["expected_question_fields"])
    assert error.value.required_fields == expected_fields
    question = error.value.question.casefold()
    assert all(str(field).casefold() in question for field in annotation["expected_question_fields"])
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize(
    "case",
    _CF410_FALSE_CLARIFICATION_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_cf410_structured_evidence_reaches_candidate_materialization(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )

    assert intent["product_intent_authority"]["materiality_status"] == "passed"
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.json").is_file()


@pytest.mark.parametrize(
    "case",
    _CF410_MISSING_SYSTEM_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_cf410_named_external_systems_retain_custody_without_entering_the_user_path(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    annotation = _CF410_ANNOTATIONS[str(case["case_id"])]
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )

    expected_systems = tuple(str(system) for system in annotation["explicit_systems"])
    assert tuple(intent["external_systems"]) == expected_systems
    first_path = str(intent["first_path"]).casefold()
    actor_text = " ".join(str(actor) for actor in intent["human_actors"]).casefold()
    assert all(system.casefold() not in first_path for system in expected_systems)
    assert all(system.casefold() not in actor_text for system in expected_systems)
    assert "pasted clinic brief" not in first_path
    assert "research packet" not in first_path
    assert str(case["required_terms"][0]).casefold() in str(intent["title"]).casefold()
    accepted_dependencies = {
        " ".join(str(atom["normalized_value"]).casefold().split())
        for atom in intent["product_intent_authority"]["atomic_facts"]
        if "dependencies" in atom["categories"] and atom["custody_state"] == "accepted_fact"
    }
    assert accepted_dependencies == {" ".join(system.casefold().split()) for system in expected_systems}


@pytest.mark.parametrize(
    "case",
    _CF410_COLD_CHAIN_ACTOR_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_cf410_semicolon_actor_steps_preserve_phrasal_delivery_action(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    actor_labels = {str(row).split(":", 1)[0].casefold() for row in intent["human_actors"]}
    steps = tuple(step.casefold() for step in first_path_model(str(intent["first_path"])).steps)

    assert {"intake clerks", "nutrition leads", "dispatch drivers"} <= actor_labels
    assert any(step.startswith("dispatch drivers hand out parcels") for step in steps)

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=str(case["prompt"]),
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )
    component_labels = {str(row["label"]).casefold() for row in proposal["components"]}

    assert "parcels delivery service" in component_labels
    assert all("hand out" not in label for label in component_labels)
    assert run_greenfield_tribunal(proposal, release_selector="0.0.1").passed


def test_cf410_pasted_cold_chain_brief_does_not_false_block_phrasal_action(tmp_path: Path) -> None:
    case = _CF410_COLD_CHAIN_BRIEF
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=str(case["prompt"]),
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )

    actor_labels = {str(row).split(":", 1)[0].casefold() for row in intent["human_actors"]}
    first_path = str(intent["first_path"]).casefold()

    assert "cold-chain pantry ledger" in str(intent["title"]).casefold()
    assert actor_labels == {"intake clerks", "nutrition leads", "dispatch drivers"}
    assert "refrigeration telemetry api" not in first_path
    assert "a proposal with" not in first_path
    assert "donated lot" in str(intent["state_object"]).casefold()
    assert "dispatch drivers" not in str(intent["state_object"]).casefold()
    assert tuple(intent["external_systems"]) == ("refrigeration telemetry API",)
    component_labels = {str(row["label"]).casefold() for row in proposal["components"]}
    assert "temperature checks validation service" in component_labels
    assert all(not label.startswith("are ") for label in component_labels)
    gate_component = next(
        row for row in proposal["components"] if str(row["label"]).casefold() == "temperature checks validation service"
    )
    assert str(gate_component["responsibility"]).casefold().startswith(
        "enforces temperature checks as the release gate"
    )
    gate_contract = json.dumps(gate_component["component_contract"], sort_keys=True).casefold()
    assert "checks are the release gate" not in gate_contract
    assert "retain temperature" not in gate_contract
    assert "failure reason ledger" not in gate_contract
    assert "known-limit checkpoint" not in gate_contract
    assert "recovery-condition ledger" not in gate_contract
    assert run_greenfield_tribunal(proposal, release_selector="0.0.1").passed


@pytest.mark.parametrize(
    "case",
    _87E277_CLARIFICATION_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_87e277_material_unknowns_are_specific_and_write_free(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    annotation = _87E277_ANNOTATIONS[str(case["case_id"])]
    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=str(case["prompt"]),
            repo_root=tmp_path,
            fallback_title=str(case["name"]),
        )

    expected_fields = {str(field).replace(" ", "_") for field in annotation["expected_question_fields"]}
    assert set(error.value.required_fields) == expected_fields
    assert str(error.value).endswith("?")
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize(
    "case",
    _87E277_EXTERNAL_SYSTEM_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_87e277_explicit_dependencies_enter_typed_intent_hypothesis(
    case: dict[str, object],
) -> None:
    intent = intent_hypothesis_from_operator_evidence(
        str(case["prompt"]),
        prefer_product_title=True,
    )

    external_systems = sorted(" ".join(str(row).casefold().split()) for row in intent["external_systems"])
    expected = sorted(
        " ".join(str(system).casefold().split())
        for system in _87E277_ANNOTATIONS[str(case["case_id"])]["explicit_systems"]
    )
    assert external_systems == expected


@pytest.mark.parametrize(
    "case",
    _87E277_SEALED_SYSTEM_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_87e277_explicit_dependencies_are_sealed_as_accepted_facts(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    expected = {
        " ".join(str(system).casefold().split())
        for system in _87E277_ANNOTATIONS[str(case["case_id"])]["explicit_systems"]
    }
    accepted_dependencies = {
        " ".join(str(atom["normalized_value"]).casefold().split())
        for atom in intent["product_intent_authority"]["atomic_facts"]
        if "dependencies" in atom["categories"] and atom["custody_state"] == "accepted_fact"
    }

    assert accepted_dependencies == expected


def test_typed_materiality_gate_blocks_before_candidate_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = greenfield_product_intent_envelope.build_product_intent_envelope

    def blocked_envelope(*args: object, **kwargs: object) -> dict[str, object]:
        envelope = original(*args, **kwargs)
        envelope["materiality_gate"] = {
            "status": "clarification_required",
            "blocked_fields": ["proof_boundary"],
            "clarification_policy": "block_only_material_unknowns",
        }
        return envelope

    monkeypatch.setattr(
        greenfield_product_intent_envelope,
        "build_product_intent_envelope",
        blocked_envelope,
    )

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=(
                "Mara reviews one returned crate, records its orchard lot, marks it inspected, "
                "and sees the daily return tally."
            ),
            repo_root=tmp_path,
            fallback_title="Orchard Returns",
        )

    assert error.value.required_fields == ("proof_boundary",)
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize(
    "case",
    _RETIRED_HOLDOUT_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_retired_holdout_preserves_outcome_and_no_write_contract(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    expectation = str(case["expectation"])
    if expectation == "clarification_required":
        with pytest.raises(GreenfieldClarificationRequired) as error:
            materialize_prompt_intent_hypothesis(
                prompt=str(case["prompt"]),
                repo_root=tmp_path,
                fallback_title=str(case["name"]),
            )
        assert error.value.required_fields == tuple(case["expected_question_fields"])
        assert not (tmp_path / ".odylith/runtime/greenfield").exists()
        return

    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    first_path = str(intent["first_path"])
    assert first_path.endswith(".")
    assert "can the first" not in first_path.casefold()
    findings = generated_public_copy_findings(
        "retired holdout intent",
        {key: value for key, value in intent.items() if key not in {"prompt", "_product_intent_authority"}},
    )
    categories = {finding.category for finding in findings}
    assert "adjacent_duplicate_word" not in categories
    assert "clipped_public_copy" not in categories


@pytest.mark.parametrize(
    ("name", "prompt", "required_path_terms", "excluded_path_terms", "expected_external_terms"),
    (
        (
            "reordered orchard evidence",
            (
                "A note about old orchard fence paint is out of scope. The Grove Roster supplies lot names and "
                "must not be changed. At the packing shed, inspection notes are visible only to that shed. Mara is "
                "the packing-shed clerk using the Orchard Bin Ledger: she records a returned crate, chooses its "
                "orchard lot, marks it inspected, then sees the daily return tally. Success means that one record "
                "produces that tally."
            ),
            ("records a returned crate", "daily return tally"),
            ("fence paint", "grove roster supplies"),
            ("grove roster",),
        ),
        (
            "quiet room evidence",
            (
                "Niko, a library host, reserves a quiet-room slot in the Lantern Desk. Niko chooses a room and "
                "marks the slot held; the visitor-facing board then shows the room and time. Room availability is "
                "read from the Hall Calendar. Do not promise a reservation until the calendar returns availability."
            ),
            ("marks the slot held", "shows the room and time"),
            ("room availability is read",),
            ("hall calendar",),
        ),
        (
            "tool loan JSON",
            (
                '{"operator":"Sana","role":"workshop steward","product":"Bench Borrower",'
                '"path":["scan tool tag","set loan state to checked out","show return due date"],'
                '"source":"Tool Shelf Index","constraint":"never mark unavailable tools checked out"}'
            ),
            ("scan tool tag", "show return due date"),
            ('{"operator"',),
            ("tool shelf index",),
        ),
        (
            "marina evidence",
            (
                "Harbor Slate is for dock attendant Ivo. Ivo starts by entering a vessel tag. On a match, the "
                "product records the berth as occupied and the berth map displays the placement. Tide Ledger "
                "supplies assignments; Harbor Slate cannot edit it."
            ),
            ("entering a vessel tag", "berth map displays"),
            ("tide ledger supplies",),
            ("tide ledger",),
        ),
        (
            "museum evidence",
            (
                "Uma, an exhibit preparer, drafts a label request in Gallery Slip. Uma selects an object code, sets "
                "the request to awaiting review, and sees a curator queue number. Object codes come from Collection "
                "Shelf. Gallery Slip must not authenticate provenance, appraise value, or publish a label."
            ),
            ("awaiting review", "curator queue number"),
            ("collection shelf",),
            ("collection shelf",),
        ),
        (
            "unseen acoustic workflow vocabulary",
            (
                "Ari, an acoustic technician, uses Fathom Console to calibrate a sensor, compare a reference trace, "
                "and receive a variance report. Reference traces come from the Anechoic Archive. Fathom Console "
                "cannot certify that a device is safe."
            ),
            ("calibrate a sensor", "variance report"),
            ("anechoic archive", "certify"),
            ("anechoic archive",),
        ),
    ),
)
def test_ranked_evidence_compiles_the_complete_path_without_false_clarification(
    tmp_path: Path,
    name: str,
    prompt: str,
    required_path_terms: tuple[str, ...],
    excluded_path_terms: tuple[str, ...],
    expected_external_terms: tuple[str, ...],
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=name,
    )

    first_path = str(intent["first_path"]).casefold()
    external_systems = " ".join(str(row) for row in intent["external_systems"]).casefold()
    assert all(term in first_path for term in required_path_terms)
    assert all(term not in first_path for term in excluded_path_terms)
    assert all(term in external_systems for term in expected_external_terms)
    if name == "unseen acoustic workflow vocabulary":
        assert intent["title"] == "Fathom Console"


@pytest.mark.parametrize(
    ("prompt", "expected_fields"),
    (
        (
            "Dara uses Stall Signal to record a stall arrival. One note says the display is for vendors only; "
            "another says the same display must be public. The display audience is unresolved.",
            ("display_audience",),
        ),
        (
            "Noel records a sample card. One sentence says it is an observation record only; another says it must "
            "declare the water safe to drink. Those proof boundaries conflict.",
            ("proof_boundary",),
        ),
        (
            "Build Quay Token for ferry kiosk helper Pia to log paper tokens.",
            ("visible_result", "dependency_source"),
        ),
        (
            "Create Kite List for youth-club coordinator Lea to note member arrivals.",
            ("visible_result", "state_transition", "proof_boundary"),
        ),
    ),
)
def test_material_clarification_is_field_specific_and_write_free(
    tmp_path: Path,
    prompt: str,
    expected_fields: tuple[str, ...],
) -> None:
    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Focused Product",
        )

    assert error.value.required_fields == expected_fields
    assert str(error.value).endswith("?")
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_unresolved_domain_state_does_not_invent_a_material_contradiction(tmp_path: Path) -> None:
    prompt = (
        "Create a dashboard for unresolved service tickets where an operator reviews source logs, assigns an owner, "
        "and sees a resolution queue."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Service Ticket Dashboard",
    )

    assert "resolution queue" in str(intent["first_path"]).casefold()


def test_domain_conflict_outcome_does_not_invent_a_material_contradiction(tmp_path: Path) -> None:
    prompt = (
        "Build a Quantum Networking Lab Management App where lab operators reserve a calibrated entanglement "
        "link for an experiment, confirm device and calibration availability, record either a conflict or an "
        "accepted reservation, and see an auditable ready-to-run reservation."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Quantum Networking Lab Management App",
    )

    first_path = str(intent["first_path"]).casefold()
    assert "record either a conflict or an accepted reservation" in first_path
    assert "auditable ready-to-run reservation" in first_path


def test_inline_labeled_evidence_compiles_one_complete_path(tmp_path: Path) -> None:
    prompt = (
        "Domain label: lantern archive intake. Brief // domain: archival conservation // "
        "actor: collection registrars // system: CatalogBridge // objective: record conservation work. "
        "Acceptance: keep condition changes linked to bench notes; output: an intervention register; "
        "state model: condition states; dependency: require curator approval before public history changes. "
        "Safety boundary: must not erase superseded notes. First path: the first path begins with "
        "condition-note intake. The first path is fixed."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Archive Intake",
    )

    first_path = str(intent["first_path"]).casefold()
    assert str(intent["title"]).startswith("Lantern Archive Intake")
    assert "collection registrars" in first_path
    assert "condition-note intake" in first_path
    assert "record conservation work" in first_path
    assert "intervention register" in first_path
    assert intent["internal_systems"]


def test_product_for_actor_request_uses_action_start_and_visible_result(tmp_path: Path) -> None:
    prompt = (
        "Domain label: meadow acoustics catalog. Build a greenfield product for field recording teams to "
        "catalog acoustic transects in EchoGrid. It must retain microphone settings and habitat conditions, "
        "produce a transect evidence bundle, and track recording-quality states. Lead review is required before "
        "classification, and the product must not classify a segment when habitat metadata is absent. "
        "The first path is fixed: it begins with microphone-setting verification."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Acoustics Catalog",
    )

    first_path = str(intent["first_path"]).casefold()
    assert str(intent["title"]).startswith("Meadow Acoustics Catalog")
    assert "field recording teams" in first_path
    assert "catalog acoustic transects" in first_path
    assert "microphone-setting verification" in first_path
    assert "transect evidence bundle" in first_path


def test_explicit_unfamiliar_actor_role_does_not_trigger_clarification(tmp_path: Path) -> None:
    prompt = (
        "Domain label: oral archive accession. Create a product for oral-history custodians who need to accession "
        "recordings in EchoVault. The product must preserve custody labels and generate an accession manifest. "
        "The first path is fixed: it begins with custody intake."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Archive Accession",
    )

    assert "oral-history custodians" in str(intent["first_path"]).casefold()


def test_explicit_system_actor_still_requires_a_human_owner(tmp_path: Path) -> None:
    prompt = (
        "Create a product for the routing service to route intake records and return a delivery receipt in RouteGrid."
    )

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Routing Intake",
        )

    assert error.value.required_fields == ("human_actors", "first_path")
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_nominal_path_result_is_rendered_as_an_action_not_raw_meta_prose(tmp_path: Path) -> None:
    prompt = (
        "Domain label: textile calibration. Create a product for calibration technicians who need to calibrate "
        "woven batches in GaugeDesk. The product must generate a signed spool ledger. "
        "The first path is fixed: the first calibration path is the signed batch receipt."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Textile Calibration",
    )

    first_path = str(intent["first_path"]).casefold()
    assert "can the first" not in first_path
    assert "calibrate woven batches" in first_path
    assert "signed batch receipt" in first_path
    assert "signed spool ledger" in first_path


def test_implementation_request_outranks_research_evidence_prose(tmp_path: Path) -> None:
    prompt = (
        "Domain label: woven panel census. Evidence B says the registrar owns a census decision and uses "
        "record-confidence states. Evidence A says source notes use ThreadIndex for historical panel records. "
        "Implementation request: create the product so museum registrars can curate textile census records; "
        "output: a reviewed panel record; proof boundary: do not expose restricted donor correspondence. "
        "The first path is fixed: it begins with weave-structure review."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Panel Census",
    )

    first_path = str(intent["first_path"]).casefold()
    assert "museum registrars" in first_path
    assert "curate textile census records" in first_path
    assert "weave-structure review" in first_path
    assert "panel record" in first_path
    assert "evidence b says" not in first_path


def test_research_evidence_can_supply_the_visible_result_without_leaking_its_wrapper(tmp_path: Path) -> None:
    prompt = (
        "Domain label: ceramic trial comparison. Evidence B says the firing specialist owns a trial comparison "
        "sheet and the state vocabulary is kiln-run states. Evidence A describes historical trial records. "
        "Implementation request: create the product so ceramic firing specialists can compare kiln trial results; "
        "proof boundary: do not claim a result from an incomplete log. The first path is fixed: it begins with "
        "atmosphere-log review."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Trial Comparison",
    )

    first_path = str(intent["first_path"]).casefold()
    assert "trial comparison sheet" in first_path
    assert "evidence b says" not in first_path


def test_first_approval_ownership_ambiguity_is_focused_and_write_free(tmp_path: Path) -> None:
    prompt = (
        "Build a collection intake product for archive stewards to record accession decisions and receive a "
        "custody card. Either archive stewards or the lead curator may own the first approval, and the choice "
        "changes the initial path and proof record."
    )

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Collection Intake",
        )

    assert error.value.required_fields == ("first_approval_actor", "first_path", "proof_record_owner")
    assert "first approval" in str(error.value).casefold()
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize("case", _AA51_AUTHORITY_CASES, ids=lambda case: str(case["case_id"]))
def test_explicit_missing_decision_authority_is_focused_and_write_free(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=str(case["prompt"]),
            repo_root=tmp_path,
            fallback_title=str(case["name"]),
        )

    assert error.value.required_fields == ("decision_authority", "governing_decision_rule")
    assert "authority" in str(error.value).casefold()
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_optional_owner_filter_omission_does_not_force_clarification(tmp_path: Path) -> None:
    prompt = (
        "Create a workspace where support coordinators review a customer request, assign a case owner, and see "
        "a resolution summary. The first release omits optional owner filters."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Support Resolution",
    )

    assert "resolution summary" in str(intent["first_path"]).casefold()


@pytest.mark.parametrize(
    "edit_evidence",
    (
        "Only change the actor name.",
        "Preserve the existing flow and add a calendar sync.",
    ),
)
def test_vague_edit_directives_require_a_concrete_correction(
    tmp_path: Path,
    edit_evidence: str,
) -> None:
    prompt = (
        "Rae, a service coordinator, reviews one support case, assigns an owner, and sees a resolution summary."
    )

    with pytest.raises(ValueError, match="What should change about the first complete path"):
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Service Resolution",
            edit_evidence=edit_evidence,
        )

    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize(
    "negative_boundary",
    (
        "It must not generate a public certificate before supervisor approval.",
        "It is forbidden to generate a public certificate before supervisor approval.",
    ),
)
def test_negated_output_is_not_promoted_into_the_first_path(
    tmp_path: Path,
    negative_boundary: str,
) -> None:
    prompt = (
        "Create a product for permit clerks to review filings and see an approval queue in Civic Desk. "
        f"{negative_boundary}"
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Permit Review",
    )

    first_path = str(intent["first_path"]).casefold()
    assert "approval queue" in first_path
    assert "public certificate" not in first_path


@pytest.mark.parametrize("actor", ("EchoGrid sensors", "dock cameras", "warehouse robots"))
def test_explicit_non_human_actor_requires_a_write_free_clarification(
    tmp_path: Path,
    actor: str,
) -> None:
    prompt = (
        f"Create a product for {actor} to monitor samples, verify seal states, and generate a packet "
        "in AtlasBay."
    )

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Sample Monitoring",
        )

    assert error.value.required_fields == ("human_actors", "first_path")
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_explicit_who_grammar_preserves_an_unfamiliar_human_role(tmp_path: Path) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=(
            "Create a product for harbor tallykeepers who need to record one berth count and see a signed tally "
            "in Quay Desk."
        ),
        repo_root=tmp_path,
        fallback_title="Harbor Tally",
    )

    assert "harbor tallykeepers" in str(intent["first_path"]).casefold()


@pytest.mark.parametrize("subject", ("These", "Those", "Records", "Outputs", "Evidence"))
def test_capitalized_sentence_subject_is_not_product_title(subject: str) -> None:
    assert explicit_product_title_evidence(f"{subject} must remain reviewable.") == ""


@pytest.mark.parametrize("subject", ("These", "Those", "Records", "Outputs", "Evidence"))
def test_actor_led_prompt_uses_the_supplied_title_instead_of_a_path_fragment(
    tmp_path: Path,
    subject: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=(
            "Archivists record one accession and see a custody receipt. "
            f"{subject} must remain reviewable."
        ),
        repo_root=tmp_path,
        fallback_title="Archive Demo",
    )

    assert str(intent["title"]).casefold().startswith("archive demo")
    assert subject.casefold() not in str(intent["title"]).casefold()


def test_explicit_single_word_product_name_is_preserved(tmp_path: Path) -> None:
    prompt = (
        "Niko, a booking coordinator, uses Lumen to reserve one room and sees a reservation receipt."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Fallback Product",
    )

    assert explicit_product_title_evidence(prompt) == "Lumen"
    assert str(intent["title"]).startswith("Lumen")


def test_generic_using_clause_is_not_promoted_to_a_product_name() -> None:
    assert explicit_product_title_evidence("Using Evidence from interviews, map the approval path.") == ""


def test_visible_output_already_in_the_action_chain_is_not_repeated(tmp_path: Path) -> None:
    prompt = (
        "Create a product for dispatch coordinators to monitor samples, verify seal states, and generate a "
        "packet in AtlasBay."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Sample Dispatch",
    )

    first_path = str(intent["first_path"]).casefold()
    assert first_path.count("packet") == 1
    assert "generate a packet and receive a packet" not in first_path


@pytest.mark.parametrize(
    ("prompt", "edit_evidence", "path_term", "boundary_term"),
    (
        (
            (
                "Rae, a seed-library volunteer, prepares a pickup packet in Sprout Counter. Rae searches a member "
                "code, reserves one seed packet, and sees a pickup label."
            ),
            (
                "## Confirmed edit\nKeep the Circle Register and Packet Shelf availability checks. Make the "
                "existing boundary explicit: Sprout Counter prepares the pickup label but does not send messages."
            ),
            "pickup label",
            "does not send messages",
        ),
        (
            (
                "Oren, the prop-room keeper, uses Cue Crate to receive a returned prop. The keeper scans the prop "
                "label, selects sound or repair-needed, and gets a shelf-return card."
            ),
            (
                "## Confirmed edit\nKeep the sound and repair-needed choices. Preserve the boundary that "
                "repair-needed props stay off the ready shelf."
            ),
            "shelf-return card",
            "stay off the ready shelf",
        ),
    ),
)
def test_additive_edit_rebuild_preserves_path_and_boundary(
    tmp_path: Path,
    prompt: str,
    edit_evidence: str,
    path_term: str,
    boundary_term: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Edited Product",
        edit_evidence=edit_evidence,
    )

    assert path_term in str(intent["first_path"])
    assert boundary_term in " ".join(intent["operational_constraints"]).casefold()


@pytest.mark.parametrize(
    ("prompt", "external_source", "expected_title"),
    (
        (
            (
                "Mara, a packing-shed clerk, records each returned crate in the Orchard Bin Ledger. She selects the "
                "orchard lot, marks the crate inspected, and sees a daily return tally. The ledger imports lot names "
                "from the Grove Roster. Keep inspection notes visible only to the packing shed."
            ),
            "grove roster",
            "Orchard Bin Ledger",
        ),
        (
            (
                "Tomas, an aviary volunteer, logs a feeder refill in Perch Note. Tomas selects an enclosure, records the "
                "feeder refilled state, and receives a shift summary. Enclosure names come from Roost Index. Perch Note "
                "must never diagnose an animal, prescribe feed, or state that an enclosure is healthy."
            ),
            "roost index",
            "Perch Note",
        ),
    ),
)
def test_project_and_radar_copy_is_complete_and_nonrepetitive(
    tmp_path: Path,
    prompt: str,
    external_source: str,
    expected_title: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Complete Copy Product",
    )
    assert str(intent["title"]).startswith(expected_title)
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    package = prewrite.package
    package_issues = greenfield_rendered_package_quality_issues(package)
    rendered = "\n".join(
        [
            *package.backlog_result["idea_files"].values(),
            *package.rendered_component_specs.values(),
            *package.rendered_atlas_sources.values(),
            package.project_brief_record_text,
        ]
    ).casefold()
    copy_debt = ("adjacent duplicate", "clipped", "repeats noncanonical", "semantically repetitive")

    assert not [issue for issue in package_issues if any(term in issue for term in copy_debt)]
    assert external_source in rendered
    for scope, value in (
        ("project dashboard preview", package.project_dashboard_preview),
        ("prewrite Radar package", package.backlog_result),
    ):
        categories = {finding.category for finding in generated_public_copy_findings(scope, value)}
        assert "adjacent_duplicate_word" not in categories
        assert "clipped_public_copy" not in categories

    story = package.project_dashboard_preview["product_story"]["release_contract"]
    assert project_story_semantic_issues(story) == []
    bodies = [str(row["body"]).strip() for row in story]
    assert len(bodies) == len(set(body.casefold() for body in bodies))
    assert all(body.endswith((".", "?", "!")) for body in bodies)
    assert all(not body.casefold().endswith(("such as.", "plus.")) for body in bodies)


def test_source_obligation_is_not_miscompiled_as_the_last_user_path_event(tmp_path: Path) -> None:
    prompt = (
        "Create a market stall desk. A vendor coordinator checks applications, consults the weather feed, "
        "assigns an allocation receipt, and publishes an opening roster. Retain waitlist order. "
        "Do not rank vendors by neighborhood or income."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Market Stall Desk",
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )
    first_path = str(intent["first_path"]).casefold()
    constraints = [str(value).casefold() for value in intent["operational_constraints"]]
    accepted_constraints = {
        str(atom["normalized_value"]).casefold()
        for atom in intent["product_intent_authority"]["atomic_facts"]
        if "constraints" in atom["categories"] and atom["custody_state"] == "accepted_fact"
    }
    sequence = next(row for row in proposal["diagrams"] if row["title"] == "First Path Sequence")

    assert "publishes an opening roster" in first_path
    assert "retain waitlist order" not in first_path
    assert "retain waitlist order" in constraints
    assert "retain waitlist order" in accepted_constraints
    assert "opening roster" in str(sequence["mermaid_source"]).casefold()
    assert run_greenfield_tribunal(proposal, release_selector="0.0.1").passed


def test_canopy_restatement_preserves_complete_source_meaning(tmp_path: Path) -> None:
    case = next(
        row for row in _87E277_RETIRED_HOLDOUT["cases"] if row["case_id"] == "gfh-20260808-v2-02"
    )
    prompt = str(case["prompt"])

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert intent["title"] == "Tree-canopy Ledger"
    assert "mapping gateway" not in str(intent["first_path"]).casefold()
    assert "retain geotagged photos for seven years" in {
        str(value).casefold() for value in intent["operational_constraints"]
    }
    assert "do not score neighborhoods in the first release" in {
        str(value).casefold().rstrip(" .") for value in intent["non_goals"]
    }
    assert all(str(term).casefold() in rendered for term in case["required_terms"])
    assert run_greenfield_tribunal(proposal, release_selector="0.0.1").passed


def test_compact_canopy_confirmation_preserves_custody_without_envelope_leakage(tmp_path: Path) -> None:
    case = next(
        row for row in _87E277_RETIRED_HOLDOUT["cases"] if row["case_id"] == "gfh-20260808-v2-06"
    )
    prompt = str(case["prompt"])

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )
    accepted = {
        str(atom["normalized_value"]).casefold()
        for atom in intent["product_intent_authority"]["atomic_facts"]
        if atom["custody_state"] == "accepted_fact"
    }

    assert intent["title"] == "Tree-canopy Ledger"
    assert "mapping gateway" not in str(intent["first_path"]).casefold()
    assert "neighborhood stewards may correct site text" in str(intent["first_path"]).casefold()
    assert {str(row).split(":", 1)[0].casefold() for row in intent["human_actors"]} == {
        "arborists",
        "neighborhood stewards",
    }
    assert intent["external_systems"] == ["mapping gateway"]
    assert intent["operational_constraints"] == ["Retain geotagged photos for seven years"]
    assert {"arborists", "neighborhood stewards", "mapping gateway"} <= accepted
    assert run_greenfield_tribunal(proposal, release_selector="0.0.1").passed
