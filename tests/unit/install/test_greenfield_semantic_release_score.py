from __future__ import annotations

from dataclasses import replace
import hashlib
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_semantic_release_score import evaluate_semantic_release
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_evidence
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import atomic_fact_ledger_hash
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope


FLOORS = {
    "accepted_fact_custody": 1.0,
    "critical_constraint_recall": 1.0,
    "explicit_system_recall": 1.0,
    "material_question_recall": 0.95,
    "unnecessary_question_rate_ceiling": 0.05,
    "first_path_comprehension": 0.9,
    "overall_case_success": 0.95,
    "worst_slice_success": 0.8,
}
PROMPT = "Operator submits one signed permit to the Registry API and reviews the accepted permit receipt."


def test_semantic_release_passes_grounded_commit_and_material_clarification() -> None:
    commit = _case("commit", expectation="transaction_committed", input_style="direct_request")
    clarify = _case("clarify", expectation="clarification_required", input_style="thin_request")
    report = evaluate_semantic_release(
        cases=(commit, clarify),
        annotations={
            "commit": _commit_annotation(),
            "clarify": _clarification_annotation(),
        },
        results=(_commit_result(commit), _clarification_result(clarify)),
        floors={**FLOORS, "worst_slice_success": 1.0},
    )

    assert report["passed"] is True
    assert report["p0_count"] == 0
    assert report["metrics"]["accepted_fact_custody"]["rate"] == 1.0
    assert report["metrics"]["material_question_recall"]["rate"] == 1.0
    assert report["overall_case_success"]["confidence_interval_95"]["method"] == "wilson"


def test_semantic_release_makes_missing_explicit_system_a_p0() -> None:
    case = _case("missing-system", expectation="transaction_committed", input_style="pasted_brief")
    result = _commit_result(case, external_systems=[])

    report = evaluate_semantic_release(
        cases=(case,),
        annotations={"missing-system": _commit_annotation()},
        results=(result,),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["p0_findings"] == [
        {"case_id": "missing-system", "category": "explicit_system_missing"}
    ]


def test_semantic_release_does_not_pass_required_zero_of_zero_metric() -> None:
    case = _case("commit", expectation="transaction_committed", input_style="direct_request")
    annotation = _commit_annotation()
    annotation["critical_constraints"] = []

    report = evaluate_semantic_release(
        cases=(case,),
        annotations={"commit": annotation},
        results=(_commit_result(case),),
        floors=FLOORS,
    )

    check = next(row for row in report["floor_checks"] if row["name"] == "critical_constraint_recall")
    assert check["status"] == "unproven"
    assert "0 of 0" in check["issue"]
    assert report["passed"] is False


def test_semantic_release_rejects_right_words_in_the_wrong_field() -> None:
    case = _case("wrong-field", expectation="transaction_committed", input_style="direct_request")
    result = _commit_result(case, external_systems=[], registry_as_assumption=True)
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    snapshot["material_custody"]["assumptions"] = {
        "custody_state": "accepted_fact",
        "entailment_relationship": "direct_product_claim",
    }

    report = evaluate_semantic_release(
        cases=(case,),
        annotations={"wrong-field": _commit_annotation()},
        results=(result,),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["p0_findings"] == [
        {"case_id": "wrong-field", "category": "explicit_system_missing"}
    ]
    assert report["metrics"]["accepted_fact_custody"]["numerator"] == 4
    assert report["metrics"]["accepted_fact_custody"]["denominator"] == 5


def test_semantic_release_does_not_treat_field_custody_as_atomic_proof() -> None:
    case = _case("field-only", expectation="transaction_committed", input_style="direct_request")
    result = _commit_result(case)
    result.evidence["preconfirm_dry_run"]["semantic_snapshot"]["atomic_facts"] = []

    report = evaluate_semantic_release(
        cases=(case,),
        annotations={"field-only": _commit_annotation()},
        results=(result,),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["metrics"]["accepted_fact_custody"]["rate"] == 0.0
    assert report["p0_findings"] == [
        {"case_id": "field-only", "category": "atomic_custody_invalid"}
    ]


@pytest.mark.parametrize("damage", ("projection", "source_ref"))
def test_semantic_release_rejects_hash_matched_forged_atomic_custody(damage: str) -> None:
    case = _case("forged-atomic", expectation="transaction_committed", input_style="direct_request")
    result = _commit_result(case)
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    atoms = snapshot["atomic_facts"]
    index = next(index for index, atom in enumerate(atoms) if "dependencies" in atom["categories"])
    atom = atoms[index]
    if damage == "projection":
        atoms[index] = {
            **atom,
            "projection_links": [
                {
                    **atom["projection_links"][0],
                    "path": "/external_systems/999",
                    "value_sha256": "0" * 64,
                }
            ],
        }
    else:
        atoms[index] = {
            **atom,
            "source_span_refs": [{**atom["source_span_refs"][0], "text_sha256": "0" * 64}],
        }
    snapshot["atomic_custody_sha256"] = atomic_fact_ledger_hash(atoms)

    report = evaluate_semantic_release(
        cases=(case,),
        annotations={"forged-atomic": _commit_annotation()},
        results=(result,),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["p0_findings"] == [
        {"case_id": "forged-atomic", "category": "atomic_custody_invalid"}
    ]


@pytest.mark.parametrize(
    "supporting_evidence",
    (
        "## Research Notes\nArchive API supports long-term storage.",
        "Source evidence: Archive API supports long-term storage.",
    ),
)
def test_semantic_release_rejects_forged_custody_from_supporting_evidence(
    supporting_evidence: str,
) -> None:
    prompt = f"{PROMPT}\n\n{supporting_evidence}"
    case = replace(
        _case("supporting-forgery", expectation="transaction_committed", input_style="direct_request"),
        prompt=prompt,
    )
    result = _commit_result(case, external_systems=["Archive API - optional research integration."])
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    atoms = snapshot["atomic_facts"]
    index = next(index for index, atom in enumerate(atoms) if atom["normalized_value"] == "Archive API")
    atom = atoms[index]
    supporting_text = "Archive API supports long-term storage"
    atoms[index] = {
        **atom,
        "custody_state": "accepted_fact",
        "entailment_relationship": "ordered_source_entailment",
        "source_span_ids": ["forged:supporting"],
        "source_span_refs": [
            {
                "span_id": "forged:supporting",
                "classification": "supporting_evidence",
                "text_sha256": hashlib.sha256(supporting_text.encode("utf-8")).hexdigest(),
            }
        ],
    }
    snapshot["atomic_custody_sha256"] = atomic_fact_ledger_hash(atoms)

    report = evaluate_semantic_release(
        cases=(case,),
        annotations={
            "supporting-forgery": {
                **_commit_annotation(),
                "dependencies": [
                    {
                        "value": "Archive API",
                        "expected_custody": "accepted_fact",
                    }
                ],
                "explicit_systems": ["Archive API"],
            }
        },
        results=(result,),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["p0_findings"] == [
        {"case_id": "supporting-forgery", "category": "atomic_custody_invalid"}
    ]


def test_semantic_release_rejects_duplicate_result_ids() -> None:
    case = _case("duplicate", expectation="transaction_committed", input_style="direct_request")
    result = _commit_result(case)

    report = evaluate_semantic_release(
        cases=(case,),
        annotations={"duplicate": _commit_annotation()},
        results=(result, result),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["duplicate_result_ids"] == ["duplicate"]


def test_semantic_release_does_not_let_aggregate_success_hide_one_weak_model_profile() -> None:
    profiles = (
        "provider-free-standard-v1",
        "bounded-reasoning-standard-v1",
        "lower-capability-safe-v1",
    )
    profile_sizes = (7, 7, 6)
    cases: list[GreenfieldMatrixCase] = []
    results: list[GreenfieldMatrixResult] = []
    annotations: dict[str, dict[str, object]] = {}
    for profile, size in zip(profiles, profile_sizes, strict=True):
        for index in range(size):
            case_id = f"{profile}-{index}"
            case = replace(
                _case(case_id, expectation="transaction_committed", input_style="direct_request"),
                tags=("complexity:bounded", f"model-profile:{profile}"),
            )
            result = _commit_result(case)
            if profile == "lower-capability-safe-v1" and index == 0:
                result = replace(result, status="failed")
            cases.append(case)
            results.append(result)
            annotations[case_id] = _commit_annotation()

    report = evaluate_semantic_release(
        cases=cases,
        annotations=annotations,
        results=results,
        floors=FLOORS,
    )
    by_profile = {row["profile"]: row for row in report["model_profiles"]}

    assert report["overall_case_success"]["rate"] == 0.95
    assert report["worst_slice"]["point_estimate"] >= FLOORS["worst_slice_success"]
    assert by_profile["provider-free-standard-v1"]["passed"] is True
    assert by_profile["bounded-reasoning-standard-v1"]["passed"] is True
    assert by_profile["lower-capability-safe-v1"]["passed"] is False
    assert "model profile `lower-capability-safe-v1` failed" in " ".join(report["issues"])


def _case(case_id: str, *, expectation: str, input_style: str) -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        case_id=case_id,
        name=case_id,
        prompt=PROMPT,
        required_terms=("permit",),
        expectation=expectation,
        input_style=input_style,
        input_style_declared=True,
        tags=("complexity:bounded", "model-profile:provider-free-standard-v1"),
    )


def _item(identifier: str, value: str, category: str) -> dict[str, str]:
    return {
        "id": identifier,
        "value": value,
        "materiality": "material",
        "expected_custody": "accepted_fact",
        "category": category,
    }


def _commit_annotation() -> dict[str, object]:
    return {
        "expected_outcome": "commit",
        "expected_question_fields": [],
        "actors": [_item("actor", "Operator", "actors")],
        "actions": [_item("action", "submits signed permit", "actions")],
        "states": [_item("state", "accepted permit", "states")],
        "outputs": [_item("output", "permit receipt", "outputs")],
        "constraints": [],
        "dependencies": [_item("dependency", "Registry API", "dependencies")],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": [],
        "critical_constraints": ["signed permit"],
        "explicit_systems": ["Registry API"],
    }


def _clarification_annotation() -> dict[str, object]:
    return {
        "expected_outcome": "clarify",
        "expected_question_fields": ["first_path"],
        "actors": [],
        "actions": [],
        "states": [],
        "outputs": [],
        "constraints": [],
        "dependencies": [],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": [],
        "critical_constraints": [],
        "explicit_systems": [],
    }


def _commit_result(
    case: GreenfieldMatrixCase,
    *,
    external_systems: list[str] | None = None,
    registry_as_assumption: bool = False,
) -> GreenfieldMatrixResult:
    facts = {
        "product_story": "Permit Review helps an operator review one accepted permit.",
        "state_object": "The primary state object is an accepted permit.",
        "first_path": PROMPT,
        "proof_boundary": "The first release proves one signed accepted permit.",
        "human_actors": ["Operator: submits and reviews the permit."],
        "external_systems": ["Registry API: accepts the signed permit."] if external_systems is None else external_systems,
    }
    if registry_as_assumption:
        facts["assumptions"] = ["Registry API"]
    custody = {
        key: {"custody_state": "accepted_fact", "entailment_relationship": "direct_product_claim"}
        for key in (
            "product_story",
            "state_object",
            "first_path",
            "proof_boundary",
            "human_actors",
            "external_systems",
        )
    }
    envelope = build_product_intent_envelope(
        facts,
        source_text=f"# Operator prompt evidence\n\n{case.prompt}",
        source_path="operator-prompt.txt",
        source_format="operator_prompt",
    )
    atomic_facts = envelope["custody_ledger"]["atomic_facts"]
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        evidence={
            "case": case_evidence(case),
            "preconfirm_dry_run": {
                "semantic_snapshot": {
                    "facts": facts,
                    "material_custody": custody,
                    "atomic_facts": atomic_facts,
                    "atomic_custody_sha256": atomic_fact_ledger_hash(atomic_facts),
                },
            },
        },
    )


def _clarification_result(case: GreenfieldMatrixCase) -> GreenfieldMatrixResult:
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=0.1,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        evidence={
            "case": case_evidence(case),
            "clarification": {
                "mode": "clarification_required",
                "required_fields": ["first_path"],
            },
        },
    )
