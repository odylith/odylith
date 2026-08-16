from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_evaluation_contract import assign_tracked_splits
from greenfield_evaluation_contract import cross_split_leakage_issues
from greenfield_evaluation_contract import evaluate_frozen_evaluation_contract
from greenfield_evaluation_contract import final_holdout_term_contract_issues
from greenfield_evaluation_contract import prepare_frozen_evaluation_cases
from greenfield_evaluation_contract import validate_atomic_annotations
from greenfield_matrix_case_file import load_case_file
from greenfield_model_profiles import MODEL_PROFILES
from greenfield_model_profiles import MODEL_PROFILE_ASSIGNMENT_SEED
from greenfield_model_profiles import MODEL_PROFILE_ASSIGNMENT_VERSION
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


SEED = "a" * 64


def _case(case_id: str, prompt: str, *, group: str = "") -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        case_id=case_id,
        name=case_id,
        prompt=prompt,
        required_terms=(prompt.split()[0],),
        leakage_terms=(prompt.split()[-1].rstrip("."),),
        metamorphic_group=group,
        metamorphic_transform="variant" if group else "",
    )


def _item(prompt: str, value: str) -> dict[str, object]:
    start = prompt.encode("utf-8").index(value.encode("utf-8"))
    return {
        "id": "actor-1",
        "value": value,
        "source_quote": value,
        "source_start": start,
        "source_end": start + len(value.encode("utf-8")),
        "materiality": "material",
        "expected_custody": "accepted_fact",
    }


def _annotation(case: GreenfieldMatrixCase) -> dict[str, object]:
    row: dict[str, object] = {
        "case_id": case.case_id,
        "prompt_sha256": hashlib.sha256(case.prompt.encode("utf-8")).hexdigest(),
        "expected_outcome": "commit",
        "expected_question_fields": [],
        "explicit_systems": [],
        "critical_constraints": [],
        "complexity": {
            "evidence_bytes": len(case.prompt.encode("utf-8")),
            "documents": 1,
            "actors": 1,
            "state_objects": 1,
            "paths": 1,
            "external_systems": 0,
            "contradictions": 0,
            "ambiguities": 0,
            "safety_boundaries": 0,
        },
    }
    for category in (
        "actors",
        "actions",
        "states",
        "outputs",
        "constraints",
        "dependencies",
        "assumptions",
        "ambiguities",
        "non_goals",
        "material_questions",
    ):
        row[category] = []
    row["actors"] = [_item(case.prompt, "Operator")]
    return row


def test_atomic_annotations_require_exact_source_byte_spans() -> None:
    case = _case("case-1", "Café Operator records one decision.")
    annotation = _annotation(case)

    annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert not issues
    assert set(annotations) == {"case-1"}
    annotation["actors"][0]["source_start"] = 1
    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])
    assert any("source_quote does not match" in issue or "UTF-8" in issue for issue in issues)


def test_atomic_annotations_require_material_fields_for_clarification() -> None:
    case = _case("case-1", "Operator needs a permit workflow.")
    case = replace(case, expectation="clarification_required")
    annotation = _annotation(case)
    annotation["expected_outcome"] = "clarify"

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert "annotation `case-1` clarify outcome has no expected_question_fields" in issues

    annotation["expected_question_fields"] = ["first_path"]
    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert not issues

    annotation["expected_question_fields"] = ["totally_unbounded_field"]
    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert "annotation `case-1` unsupported material question field `totally_unbounded_field`" in issues


def test_atomic_annotations_reject_a_value_not_entailed_by_its_source_span() -> None:
    case = _case("case-1", "Operator records one decision.")
    annotation = _annotation(case)
    annotation["actors"][0]["value"] = "Regulator"

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert any("not directly entailed" in issue for issue in issues)


def test_atomic_annotations_reject_dropped_prohibition_polarity() -> None:
    case = _case("case-1", "Operator reviews a record but must not publish exports.")
    annotation = _annotation(case)
    item = _item(case.prompt, "exports")
    item["id"] = "non-goal-1"
    item["expected_polarity"] = "prohibited"
    annotation["non_goals"] = [item]

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert any("drops governing prohibition polarity" in issue for issue in issues)


def test_atomic_annotations_allow_reviewed_affirmative_constraint_near_negative_prose() -> None:
    case = _case("case-1", "Operator must retain the source record without publishing exports.")
    annotation = _annotation(case)
    item = _item(case.prompt, "retain the source record")
    item["id"] = "constraint-1"
    item["expected_polarity"] = "affirmative"
    annotation["constraints"] = [item]

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert not issues


def test_atomic_annotations_require_declared_polarity_for_governed_boundaries() -> None:
    case = _case("case-1", "Operator must not publish exports.")
    annotation = _annotation(case)
    item = _item(case.prompt, "publish exports")
    item["id"] = "constraint-1"
    annotation["constraints"] = [item]

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert any("invalid expected_polarity" in issue for issue in issues)


def test_split_assignment_keeps_metamorphic_group_in_one_split() -> None:
    first = _case("case-1", "Alpha Operator records one result.", group="same")
    second = _case("case-2", "Beta Operator records the same result.", group="same")

    assignments, issues = assign_tracked_splits(
        (first, second),
        assignment={
            "algorithm": "metamorphic-or-source-group-sha256-bucket-v1",
            "seed": SEED,
            "buckets": {
                "development": [0, 5999],
                "regression": [6000, 8499],
                "private_validation": [8500, 9999],
            },
        },
    )

    assert not issues
    assert assignments["case-1"] == assignments["case-2"]


def test_cross_split_leakage_rejects_renamed_near_duplicate() -> None:
    tracked = _case("tracked", "Operator opens a review case and records an accepted decision receipt.")
    holdout = _case("holdout", "An operator opens the review case and records the accepted decision receipt.")

    issues = cross_split_leakage_issues(
        tracked_cases=(tracked,),
        tracked_assignments={"tracked": "development"},
        final_holdout_cases=(holdout,),
        threshold=0.75,
    )

    assert issues
    assert "near-duplicate prompt leakage" in issues[0]


def test_final_holdout_rejects_terms_that_are_both_required_and_forbidden() -> None:
    case = GreenfieldMatrixCase(
        case_id="holdout-1",
        name="holdout one",
        prompt="Archive Operator records one review receipt from SourceCipher.",
        required_terms=("Archive", "review receipt"),
        leakage_terms=("archive", "SourceCipher"),
    )

    issues = final_holdout_term_contract_issues((case,))

    assert issues == (
        "final holdout case `holdout-1` both requires and forbids `archive`; "
        "required_terms and leakage_terms must be disjoint",
    )


def test_final_holdout_rejects_required_and_forbidden_term_containment() -> None:
    case = GreenfieldMatrixCase(
        case_id="holdout-1",
        name="holdout one",
        prompt="Archive Operator records one review receipt.",
        required_terms=("archive ledger",),
        leakage_terms=("archive",),
    )

    issues = final_holdout_term_contract_issues((case,))

    assert issues == (
        "final holdout case `holdout-1` both requires and forbids overlapping terms "
        "`archive ledger` and `archive`; required_terms and leakage_terms must be disjoint",
    )


def test_frozen_contract_verifies_hashes_counts_annotations_and_no_leakage(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    corpus_path = repo_root / "tests/fixtures/corpus.json"
    corpus_path.parent.mkdir(parents=True)
    tracked_prompt = "Alpha Operator records one review receipt."
    corpus = {
        "cases": [
            {
                "case_id": "tracked-1",
                "name": "tracked one",
                "prompt": tracked_prompt,
                "required_terms": ["Alpha"],
                "leakage_terms": ["Alpha"],
            }
        ]
    }
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
    holdout_path = tmp_path / "holdout.json"
    holdout_cases = (
        _case("holdout-1", "Omega Operator records one proof token."),
        _case("holdout-2", "Sigma Operator accepts one permit decision."),
        _case("holdout-3", "Delta Operator publishes one readiness result."),
    )
    holdout = {
        "version": "odylith.greenfield.final-holdout.v1",
        "claim_class": "blinded-independent-synthetic-holdout",
        "authoring_method": "independently-authored test holdout",
        "cases": [
            {
                "case_id": case.case_id,
                "name": case.name,
                "prompt": case.prompt,
                "required_terms": [case.prompt.split()[0]],
                "leakage_terms": [case.prompt.split()[-1].rstrip(".")],
            }
            for case in holdout_cases
        ],
        "annotations": [_annotation(case) for case in holdout_cases],
    }
    holdout_path.write_text(json.dumps(holdout), encoding="utf-8")
    manifest_path = repo_root / "manifest.json"
    manifest = {
        "version": "odylith.greenfield.evaluation-splits.v1",
        "tracked_corpus": {
            "path": "tests/fixtures/corpus.json",
            "sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
            "case_count": 1,
            "assignment": {
                "algorithm": "metamorphic-or-source-group-sha256-bucket-v1",
                "seed": SEED,
                "buckets": {
                    "development": [0, 5999],
                    "regression": [6000, 8499],
                    "private_validation": [8500, 9999],
                },
            },
        },
        "final_holdout": {
            "sha256": hashlib.sha256(holdout_path.read_bytes()).hexdigest(),
            "byte_size": holdout_path.stat().st_size,
            "case_count": 3,
            "annotation_count": 3,
            "claim_class": "blinded-independent-synthetic-holdout",
        },
        "frozen_floors": {"version": "floors-v1"},
        "profiles": {
            "models": list(MODEL_PROFILES),
            "model_assignment": {
                "version": MODEL_PROFILE_ASSIGNMENT_VERSION,
                "seed": MODEL_PROFILE_ASSIGNMENT_SEED,
            },
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = evaluate_frozen_evaluation_contract(
        repo_root=repo_root,
        manifest_path=manifest_path,
        final_holdout_path=holdout_path,
    )

    assert report["passed"] is True
    assert report["tracked"]["case_count"] == 1
    assert report["final_holdout"]["annotation_count"] == 3
    assert report["final_holdout"]["model_profile_counts"] == {
        profile: 1 for profile in MODEL_PROFILES
    }
    bound_cases, prepared_contract = prepare_frozen_evaluation_cases(
        cases=load_case_file(holdout_path),
        repo_root=repo_root,
        manifest_path=manifest_path,
        final_holdout_path=holdout_path,
    )
    assert prepared_contract == report
    assert {case.provenance.corpus_tier for case in bound_cases} == {
        "independent_synthetic_release_holdout"
    }
    assert {case.provenance.derivation_method for case in bound_cases} == {
        "independently-authored test holdout"
    }
    assert all(
        case.provenance.derived_prompt_sha256 == hashlib.sha256(case.prompt.encode("utf-8")).hexdigest()
        for case in bound_cases
    )


def test_frozen_contract_rejects_byte_size_or_declared_style_without_cases(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    corpus_path = repo_root / "tests/fixtures/corpus.json"
    corpus_path.parent.mkdir(parents=True)
    corpus_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "tracked-1",
                        "name": "tracked one",
                        "prompt": "Alpha Operator records one review receipt.",
                        "required_terms": ["Alpha"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    holdout_path = tmp_path / "holdout.json"
    holdout_case = _case("holdout-1", "Omega Operator records one proof token.")
    holdout_path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.final-holdout.v1",
                "claim_class": "blinded-independent-synthetic-holdout",
                "cases": [
                    {
                        "case_id": holdout_case.case_id,
                        "name": holdout_case.name,
                        "prompt": holdout_case.prompt,
                        "required_terms": ["Omega"],
                    }
                ],
                "annotations": [_annotation(holdout_case)],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = repo_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.evaluation-splits.v1",
                "tracked_corpus": {
                    "path": "tests/fixtures/corpus.json",
                    "sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
                    "case_count": 1,
                    "assignment": {
                        "algorithm": "metamorphic-or-source-group-sha256-bucket-v1",
                        "seed": SEED,
                        "buckets": {
                            "development": [0, 5999],
                            "regression": [6000, 8499],
                            "private_validation": [8500, 9999],
                        },
                    },
                },
                "final_holdout": {
                    "sha256": hashlib.sha256(holdout_path.read_bytes()).hexdigest(),
                    "byte_size": holdout_path.stat().st_size + 1,
                    "case_count": 1,
                    "annotation_count": 1,
                    "claim_class": "blinded-independent-synthetic-holdout",
                },
                "profiles": {"evidence_styles": ["direct_request", "research_evidence"]},
                "frozen_floors": {},
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_frozen_evaluation_contract(
        repo_root=repo_root,
        manifest_path=manifest_path,
        final_holdout_path=holdout_path,
    )

    assert report["passed"] is False
    assert "final holdout byte_size does not match" in " ".join(report["issues"])
    assert "research_evidence" in " ".join(report["issues"])
