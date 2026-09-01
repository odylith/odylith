from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.install import test_greenfield_semantic_release_score as support


from greenfield_relation_fidelity import annotation_relation_evidence
from greenfield_relation_fidelity import snapshot_relation_evidence


score_module = support.score_module
FLOORS = support.FLOORS
_rich_relation_bundle = support._rich_relation_bundle
_refresh_relation_hash = support._refresh_relation_hash
_case = support._case
_commit_result = support._commit_result
_commit_annotation = support._commit_annotation
_clarification_annotation = support._clarification_annotation
_clarification_result = support._clarification_result
_repeated_relation_evidence = support._repeated_relation_evidence
_RELATION_REGRESSION_FIXTURE = json.loads(
    (Path(__file__).parents[2] / "fixtures/greenfield-release-corpus/relation-fidelity-regressions.v1.json")
    .read_text(encoding="utf-8")
)
_RELATION_FAILURE_CASES = tuple(
    (row["mutation"], set(row["expected_categories"]))
    for row in _RELATION_REGRESSION_FIXTURE["cases"]
    if row["expected_outcome"] == "reject"
)


@pytest.fixture(autouse=True)
def _isolate_structural_scoring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(score_module, "require_atomic_fact_ledger", lambda *_args, **_kwargs: None)


def test_relation_fidelity_reports_exact_family_and_worst_slice_evidence() -> None:
    case, annotation, result = _rich_relation_bundle("relations-pass")

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: annotation},
        results=(result,),
        floors=FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    relation = report["metrics"]["relation_fidelity"]
    assert report["passed"] is True
    assert report["relation_sample_count"] == 8
    assert relation["correct_count"] == 8
    assert (relation["rate"], relation["point_estimate"]) == (1.0, 1.0)
    assert relation["confidence_interval_95"]["method"] == "wilson"
    assert {
        family: metric["sample_count"]
        for family, metric in report["relation_fidelity_by_family"].items()
    } == {
        "first_path_events": 3,
        "context_relations": 4,
        "component_responsibility_relations": 1,
    }
    assert report["worst_relation_slice"]["point_estimate"] == 1.0
    assert "valid-independent-context" in {
        row["id"] for row in _RELATION_REGRESSION_FIXTURE["cases"]
    }


@pytest.mark.parametrize(
    ("damage", "expected_categories"),
    _RELATION_FAILURE_CASES,
)
def test_relation_fidelity_rejects_structurally_valid_wrong_relations(
    damage: str,
    expected_categories: set[str],
) -> None:
    case, annotation, result = _rich_relation_bundle(f"relations-{damage}")
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    semantics = snapshot["authored_semantics"]
    if damage == "wrong_product_owner":
        event = semantics["first_path_relations"][2]
        event.update(
            {
                "actor_quote": "Backup Engine",
                "actor_fact_path": "/internal_systems/1",
                "actor_fact_quote": "Backup Engine",
                "owner_system_path": "/internal_systems/1",
                "owner_system_quote": "Backup Engine",
            }
        )
        semantics["component_responsibility_relations"][0].update(
            {
                "owner_system_path": "/internal_systems/1",
                "owner_system_quote": "Backup Engine",
            }
        )
    elif damage == "wrong_external_actor":
        semantics["first_path_relations"][1].update(
            {
                "actor_quote": "Archive API",
                "actor_fact_path": "/external_systems/1",
                "actor_fact_quote": "Archive API",
            }
        )
    elif damage == "wrong_actor_fact":
        semantics["first_path_relations"][1].update(
            {
                "actor_fact_path": "/external_systems/1",
                "actor_fact_quote": "Archive API",
            }
        )
    elif damage == "wrong_existing_context_event":
        semantics["first_path_context_relations"][0]["first_path_event_order"] = 3
    elif damage == "false_independence":
        semantics["first_path_context_relations"][1]["first_path_event_order"] = 0
    elif damage == "wrong_action":
        semantics["first_path_relations"][2]["action_verb_quote"] = "show"
    elif damage == "wrong_target":
        semantics["first_path_relations"][2]["target_quote"] = "accepted receipt"
    elif damage == "wrong_recovery_path":
        semantics["first_path_relations"][2]["recovery_path"] = True
    elif damage == "mutual_context_omission":
        semantics["first_path_context_relations"] = []
        annotation["relation_fidelity"]["context_relations"] = []
    elif damage == "mutual_component_omission":
        semantics["component_responsibility_relations"] = []
        annotation["relation_fidelity"]["component_responsibility_relations"] = []
    else:
        semantics["component_responsibility_relations"][0].update(
            {
                "responsibility_path": "/first_path",
                "responsibility_quote": "accepted receipt",
                "responsibility_source": "terminal_visible_result",
            }
        )
    _refresh_relation_hash(result)

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: annotation},
        results=(result,),
        floors=FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    categories = {row["category"] for row in report["p1_findings"]}
    relation = report["metrics"]["relation_fidelity"]
    relation_floor = next(
        row for row in report["floor_checks"] if row["name"] == "relation_fidelity"
    )
    assert report["passed"] is False
    assert report["metrics"]["atomic_semantic_fidelity"]["rate"] == 1.0
    assert (
        relation["sample_count"] > relation["correct_count"]
        or report["relation_evidence_issues"]
    )
    assert relation["confidence_interval_95"] is not None
    assert expected_categories <= categories
    assert relation_floor["observed"] == relation["confidence_interval_95"]["lower"]
    assert next(
        row for row in report["floor_checks"]
        if row["name"] == "no_observed_p1_relation_defect"
    )["status"] == "failed"
    assert report["worst_relation_slice"]["point_estimate"] < 1.0
    if damage == "mutual_context_omission":
        context_metric = report["relation_fidelity_by_family"]["context_relations"]
        assert (context_metric["sample_count"], context_metric["correct_count"]) == (4, 0)
    if damage == "mutual_component_omission":
        component_metric = report["relation_fidelity_by_family"][
            "component_responsibility_relations"
        ]
        assert relation["correct_count"] == 0
        assert (component_metric["sample_count"], component_metric["correct_count"]) == (1, 0)


@pytest.mark.parametrize("damage", ("missing", "digest", "order"))
def test_relation_fidelity_rejects_missing_or_digest_mismatched_sealed_authority(
    damage: str,
) -> None:
    case = _case(f"relation-custody-{damage}", expectation="transaction_committed")
    result = _commit_result(case)
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    if damage == "missing":
        snapshot.pop("authored_semantics")
        snapshot.pop("authored_relation_set_sha256")
    elif damage == "digest":
        snapshot["authored_relation_set_sha256"] = "f" * 64
    else:
        snapshot["authored_semantics"]["first_path_relations"][0]["order"] = "one"
        _refresh_relation_hash(result)

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(result,),
        floors=FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    assert report["passed"] is False
    assert report["metrics"]["atomic_semantic_fidelity"]["rate"] == 1.0
    assert report["metrics"]["relation_fidelity"]["rate"] < 1.0
    assert "relation_custody_invalid" in {
        row["category"] for row in report["p1_findings"]
    }
    assert report["relation_evidence_issues"]


@pytest.mark.parametrize("allow_not_applicable", (False, True))
def test_zero_of_zero_relation_evidence_is_never_reported_as_a_pass(
    allow_not_applicable: bool,
) -> None:
    case = _case("relation-zero", expectation="clarification_required")

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _clarification_annotation()},
        results=(_clarification_result(case),),
        floors=FLOORS,
        _allow_not_applicable_metrics=allow_not_applicable,
    )

    relation = report["metrics"]["relation_fidelity"]
    relation_floor = next(
        row for row in report["floor_checks"] if row["name"] == "relation_fidelity"
    )
    worst_floor = next(
        row
        for row in report["floor_checks"]
        if row["name"] == "worst_relation_slice_fidelity"
    )
    assert relation["status"] == "not_applicable"
    assert relation["sample_count"] == 0
    assert relation["confidence_interval_95"] is None
    assert relation["evidence"]
    assert relation_floor["status"] == "unproven"
    assert worst_floor["status"] == "unproven"
    assert relation_floor["status"] != "passed"
    assert worst_floor["status"] != "passed"
    assert report["passed"] is False
    assert report["model_profiles"][0]["passed"] is False
    profile_relation_floor = next(
        row
        for row in report["model_profiles"][0]["floor_checks"]
        if row["name"] == "relation_fidelity"
    )
    assert profile_relation_floor["status"] == "unproven"


def test_repeated_identical_events_keep_distinct_source_and_projection_identity() -> None:
    case, annotation, snapshot = _repeated_relation_evidence()

    expected = annotation_relation_evidence(
        case=case,
        value=annotation["relation_fidelity"],
        atom_rows=annotation["atoms"],
    )
    actual = snapshot_relation_evidence(case=case, snapshot=snapshot)

    assert expected.issues == ()
    assert actual.issues == ()
    assert expected.keys == actual.keys
    assert len(actual.keys["first_path_events"]) == 2
    assert actual.keys["first_path_events"][0] != actual.keys["first_path_events"][1]
    assert "repeated-identical-source-distinct-events" in {
        row["id"] for row in _RELATION_REGRESSION_FIXTURE["cases"]
    }
