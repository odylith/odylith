from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
from tests.greenfield_matrix_campaign_test_support import write_semantic_release_fixture


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_evaluation_contract import EVALUATION_SPLIT_VERSION
from greenfield_evaluation_contract import FINAL_HOLDOUT_VERSION
from greenfield_evaluation_contract import STRUCTURAL_FLOORS_VERSION
from greenfield_evaluation_contract import assign_tracked_splits
from greenfield_evaluation_contract import cross_split_membership_issues
from greenfield_evaluation_contract import evaluate_frozen_evaluation_contract
from greenfield_evaluation_contract import profile_confidence_sample_issues
from greenfield_evaluation_contract import validate_atomic_annotations
from greenfield_model_profiles import MODEL_PROFILES
from greenfield_model_profiles import MODEL_PROFILE_ASSIGNMENT_SEED
from greenfield_model_profiles import MODEL_PROFILE_ASSIGNMENT_VERSION
from greenfield_matrix_statistics import release_slice_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract
from greenfield_matrix_statistics import release_statistical_confidence_contract
from greenfield_relation_fidelity import RELATION_FIDELITY_ANNOTATION_VERSION
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


SEED = "a" * 64


def _case(
    case_id: str,
    prompt: str,
    *,
    group: str = "",
    edit_evidence: str = "",
) -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        case_id=case_id,
        name=case_id,
        prompt=prompt,
        confirmed_intent_markdown=edit_evidence,
        required_terms=("fixture",),
        leakage_terms=("fixture",),
        metamorphic_group=group,
        metamorphic_transform="variant" if group else "",
    )


def _link(
    value: str,
    *,
    field: str = "human_actors",
    path: str = "/human_actors/0",
    projection_value: str | None = None,
    relation_order: int = 0,
    relation_role: str = "",
) -> dict[str, object]:
    projection = projection_value if projection_value is not None else value
    encoded = value.encode("utf-8")
    projection_start = projection.encode("utf-8").index(encoded)
    return {
        "field": field,
        "path": path,
        "value_sha256": hashlib.sha256(projection.encode("utf-8")).hexdigest(),
        "projection_start_byte": projection_start,
        "projection_end_byte": projection_start + len(encoded),
        "relation_order": relation_order,
        "relation_role": relation_role,
    }


def _atom(
    prompt: str,
    value: str,
    *,
    edit_evidence: str = "",
    role: str = "scored",
    identifier: str = "actor-1",
    field: str = "human_actors",
    path: str = "/human_actors/0",
    projection_value: str | None = None,
    relation_order: int = 1,
    relation_role: str = "actor_fact_quote",
    category: str = "actors",
) -> dict[str, object]:
    encoded_prompt = combined_prompt_evidence_source(
        prompt=prompt,
        edit_evidence=edit_evidence,
    ).encode("utf-8")
    encoded_value = value.encode("utf-8")
    start = encoded_prompt.index(encoded_value)
    return {
        "id": identifier,
        "category": category,
        "evaluation_role": role,
        "materiality": "material",
        "expected_custody": "accepted_fact",
        "expected_polarity": "affirmed",
        "source": {
            "source_id": "operator_evidence",
            "start_byte": start,
            "end_byte": start + len(encoded_value),
            "quote_sha256": hashlib.sha256(encoded_value).hexdigest(),
        },
        "projection_links": [
            _link(
                value,
                field=field,
                path=path,
                projection_value=projection_value,
                relation_order=relation_order,
                relation_role=relation_role,
            )
        ],
    }


def _complexity(case: GreenfieldMatrixCase) -> dict[str, int]:
    evidence = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=case.confirmed_intent_markdown,
    )
    return {
        "evidence_bytes": len(evidence.encode("utf-8")),
        "documents": 2 if case.confirmed_intent_markdown else 1,
        "actors": 1,
        "state_objects": 1,
        "paths": 1,
        "external_systems": 0,
        "internal_systems": 0,
        "contradictions": 0,
        "ambiguities": 0,
        "safety_boundaries": 0,
        "success_metrics": 0,
        "evidence_requirements": 0,
        "component_responsibilities": 0,
        "assumptions": 0,
        "non_goals": 0,
    }


def _annotation(case: GreenfieldMatrixCase) -> dict[str, object]:
    title, first_path = _product_case_parts(case.prompt)
    event_start = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=case.confirmed_intent_markdown,
    ).encode("utf-8").index(first_path.encode("utf-8"))
    actor_sha = hashlib.sha256(b"Operator").hexdigest()
    action = first_path.split()[1]
    action_sha = hashlib.sha256(action.encode("utf-8")).hexdigest()
    title_sha = hashlib.sha256(title.encode("utf-8")).hexdigest()
    event_sha = hashlib.sha256(first_path.encode("utf-8")).hexdigest()
    return {
        "case_id": case.case_id,
        "split": "final_holdout",
        "prompt_sha256": hashlib.sha256(case.prompt.encode("utf-8")).hexdigest(),
        "expected_outcome": "commit",
        "expected_clarification": None,
        "complexity": _complexity(case),
        "atoms": [
            _atom(
                case.prompt,
                "Operator",
                edit_evidence=case.confirmed_intent_markdown,
            ),
            _atom(
                case.prompt,
                title,
                edit_evidence=case.confirmed_intent_markdown,
                role="reference_only",
                identifier="title-1",
                field="title",
                path="/title",
                relation_order=0,
                relation_role="",
                category="dependencies",
            ),
            _atom(
                case.prompt,
                action,
                edit_evidence=case.confirmed_intent_markdown,
                role="reference_only",
                identifier="action-1",
                field="first_path",
                path="/first_path",
                projection_value=first_path,
                relation_order=1,
                relation_role="action_verb_quote",
                category="actions",
            ),
            _atom(
                case.prompt,
                first_path,
                edit_evidence=case.confirmed_intent_markdown,
                role="reference_only",
                identifier="visible-result-1",
                field="first_path",
                path="/first_path",
                projection_value=first_path,
                relation_order=1,
                relation_role="visible_result_quote",
                category="outputs",
            ),
        ],
        "relation_fidelity": {
            "version": RELATION_FIDELITY_ANNOTATION_VERSION,
            "first_path_events": [
                {
                    "order": 1,
                    "source_start_byte": event_start,
                    "source_end_byte": event_start + len(first_path.encode("utf-8")),
                    "event_start_byte": 0,
                    "event_end_byte": len(first_path.encode("utf-8")),
                    "event_sha256": event_sha,
                    "actor_kind": "human",
                    "actor_fact_path": "/human_actors/0",
                    "actor_fact_sha256": actor_sha,
                    "product_owner_path": "",
                    "product_owner_sha256": "",
                    "action_verb_sha256": action_sha,
                    "target_sha256": "",
                    "visible_result_sha256": event_sha,
                }
            ],
            "context_relations": [],
            "component_responsibility_relations": [
                {
                    "responsibility_path": "/first_path",
                    "responsibility_sha256": event_sha,
                    "product_owner_path": "/title",
                    "product_owner_sha256": title_sha,
                    "first_path_event_order": 1,
                    "responsibility_source": "terminal_visible_result",
                }
            ],
        },
    }


def _product_case_parts(prompt: str) -> tuple[str, str]:
    title, separator, first_path = prompt.partition(" supports this path: ")
    assert separator and title and first_path.endswith(".")
    return title, first_path[:-1]


def _clarification_annotation(case: GreenfieldMatrixCase) -> dict[str, object]:
    annotation = _annotation(case)
    annotation["expected_outcome"] = "clarify"
    annotation["expected_clarification"] = {
        "field": "first_path",
        "question": "What is the first complete task and visible result?",
    }
    annotation["atoms"] = []
    annotation["relation_fidelity"] = None
    return annotation


def _floors() -> dict[str, object]:
    return {
        "version": STRUCTURAL_FLOORS_VERSION,
        "atomic_semantic_fidelity": 1.0,
        "relation_fidelity": 1.0,
        "clarification_identity": 1.0,
        "unnecessary_question_rate_ceiling": 0.0,
        "overall_case_success": 1.0,
        "worst_slice_success": 1.0,
        "release_slice_minimum_samples": release_slice_minimum_sample_contract(),
        "statistical_confidence": release_statistical_confidence_contract(),
    }


def _lineage(
    *case_ids: str,
    semantic_family: str = "semantic-family",
    template_family: str = "template-family",
) -> dict[str, dict[str, str]]:
    return {
        case_id: {
            "semantic_family": semantic_family,
            "template_family": template_family,
        }
        for case_id in case_ids
    }


def test_atomic_annotations_require_exact_source_byte_spans_and_hashes() -> None:
    case = _case(
        "case-1",
        "Café Desk supports this path: Operator records one decision.",
    )
    annotation = _annotation(case)

    annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert not issues
    assert set(annotations) == {"case-1"}
    annotation["atoms"][0]["source"]["start_byte"] = 1
    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])
    assert any("quote_sha256" in issue or "UTF-8" in issue for issue in issues)


def test_atomic_annotations_reject_retired_actor_surface_role() -> None:
    case = _case(
        "case-1",
        "Review Desk supports this path: Operator records one decision.",
    )
    annotation = _annotation(case)
    annotation["atoms"][0]["projection_links"][0]["relation_role"] = "actor_quote"

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert any("invalid structural fields" in issue for issue in issues)


def test_atomic_annotations_reject_spoofed_source_byte_complexity() -> None:
    case = _case(
        "case-1",
        "Café Desk supports this path: Operator records one decision.",
    )
    annotation = _annotation(case)
    annotation["complexity"]["evidence_bytes"] += 1

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert "annotation `case-1` complexity `evidence_bytes` does not match frozen source evidence" in issues


def test_atomic_annotations_require_one_typed_clarification_identity() -> None:
    case = replace(
        _case(
            "case-1",
            "Permit Desk supports this path: Operator needs a permit workflow.",
        ),
        expectation="clarification_required",
    )
    annotation = _clarification_annotation(case)

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert not issues
    annotation["expected_clarification"]["field"] = "totally_unbounded_field"
    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])
    assert "annotation `case-1` unsupported material question field `totally_unbounded_field`" in issues


def test_reference_only_atoms_are_admitted_without_becoming_scored_truth() -> None:
    case = _case(
        "case-1",
        "Review Desk supports this path: Operator records one decision for an Auditor.",
    )
    annotation = _annotation(case)
    reference = _atom(
        case.prompt,
        "Auditor",
        role="reference_only",
        relation_order=0,
        relation_role="",
    )
    reference["id"] = "actor-reference"
    annotation["atoms"].append(reference)

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert not issues


def test_atomic_annotations_reject_an_owner_identity_without_frozen_atom_custody() -> None:
    case = _case(
        "case-1",
        "Review Desk supports this path: Operator records one decision.",
    )
    annotation = _annotation(case)
    relation = annotation["relation_fidelity"]
    relation["component_responsibility_relations"][0]["product_owner_sha256"] = "f" * 64

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert any("product owner identity is not atom-grounded" in issue for issue in issues)


def test_atomic_annotations_reject_zero_of_zero_commit_relations() -> None:
    case = _case(
        "case-1",
        "Review Desk supports this path: Operator records one decision.",
    )
    annotation = _annotation(case)
    relation = annotation["relation_fidelity"]
    relation["first_path_events"] = []
    relation["component_responsibility_relations"] = []

    _annotations, issues = validate_atomic_annotations(cases=(case,), rows=[annotation])

    assert any("requires at least one first_path event" in issue for issue in issues)
    assert "annotation `case-1` commit outcome has no scored relations" in issues


def test_split_assignment_keeps_connected_declared_lineage_in_one_split() -> None:
    first = _case("case-1", "Alpha Operator records one result.")
    second = _case("case-2", "Beta Operator records the same result.")
    third = _case("case-3", "Gamma Operator preserves a receipt.")

    assignments, issues = assign_tracked_splits(
        (first, second, third),
        assignment={
            "algorithm": "declared-lineage-component-sha256-bucket-v2",
            "seed": SEED,
            "buckets": {
                "development": [0, 5999],
                "regression": [6000, 8499],
                "private_validation": [8500, 9999],
            },
        },
        lineage={
            "case-1": {"semantic_family": "semantic-a", "template_family": "template-a"},
            "case-2": {"semantic_family": "semantic-a", "template_family": "template-b"},
            "case-3": {"semantic_family": "semantic-c", "template_family": "template-b"},
        },
    )

    assert not issues
    assert len(set(assignments.values())) == 1


def test_split_assignment_rejects_missing_or_partial_declared_lineage() -> None:
    case = _case("case-1", "Alpha Operator records one result.")

    _assignments, issues = assign_tracked_splits(
        (case,),
        assignment={
            "algorithm": "declared-lineage-component-sha256-bucket-v2",
            "seed": SEED,
            "buckets": {
                "development": [0, 5999],
                "regression": [6000, 8499],
                "private_validation": [8500, 9999],
            },
        },
        lineage={"case-1": {"semantic_family": "semantic-a"}},
    )

    assert issues == (
        "tracked corpus lineage `case-1` must declare only semantic_family and template_family",
    )


def test_cross_split_membership_uses_declared_identity_not_word_similarity() -> None:
    tracked = _case("tracked", "Operator opens a review case.")
    holdout = _case("holdout", "A person begins an assessment.")

    issues = cross_split_membership_issues(
        tracked_cases=(tracked,),
        tracked_assignments={"tracked": "development"},
        final_holdout_cases=(holdout,),
        tracked_lineage=_lineage(
            "tracked",
            semantic_family="equivalent-semantic",
            template_family="tracked-template",
        ),
        final_holdout_lineage=_lineage(
            "holdout",
            semantic_family="equivalent-semantic",
            template_family="holdout-template",
        ),
    )

    assert issues == (
        "one declared lineage or exact source identity crosses development and final_holdout: tracked, holdout",
    )


def test_reworded_cases_without_shared_identity_do_not_trigger_a_lexical_oracle() -> None:
    tracked = _case("tracked", "Operator opens a review case and records a decision receipt.")
    holdout = _case("holdout", "An operator opens the review case and records the decision receipt.")

    assert cross_split_membership_issues(
        tracked_cases=(tracked,),
        tracked_assignments={"tracked": "development"},
        final_holdout_cases=(holdout,),
        tracked_lineage=_lineage(
            "tracked",
            semantic_family="tracked-semantic",
            template_family="tracked-template",
        ),
        final_holdout_lineage=_lineage(
            "holdout",
            semantic_family="holdout-semantic",
            template_family="holdout-template",
        ),
    ) == ()


def test_exact_prompt_identity_crossing_is_rejected_without_a_similarity_threshold() -> None:
    tracked = _case("tracked", "Operator records one exact receipt.")
    holdout = _case("holdout", "Operator records one exact receipt.")

    issues = cross_split_membership_issues(
        tracked_cases=(tracked,),
        tracked_assignments={"tracked": "regression"},
        final_holdout_cases=(holdout,),
        tracked_lineage=_lineage(
            "tracked",
            semantic_family="tracked-semantic",
            template_family="tracked-template",
        ),
        final_holdout_lineage=_lineage(
            "holdout",
            semantic_family="holdout-semantic",
            template_family="holdout-template",
        ),
    )

    assert issues == (
        "one declared lineage or exact source identity crosses regression and final_holdout: tracked, holdout",
    )


def test_frozen_contract_verifies_v5_acceptance_confidence_and_samples(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    corpus_path = repo_root / "tests/fixtures/corpus.json"
    corpus_path.parent.mkdir(parents=True)
    corpus = {
        "cases": [
            {
                "case_id": "tracked-1",
                "name": "tracked one",
                "prompt": "Alpha Operator records one review receipt.",
                "required_terms": ["Alpha"],
                "leakage_terms": ["receipt"],
            }
        ]
    }
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
    holdout_cases = tuple(
        replace(
            _case(
                f"holdout-{index}",
                f"Desk {index} supports this path: Operator records governed result {index}.",
                edit_evidence=(
                    f"Keep governed result {index} reviewable."
                    if index % 2 == 0
                    else ""
                ),
            ),
            tags=(f"model-profile:{MODEL_PROFILES[(index - 1) // 12]}",),
        )
        for index in range(1, 37)
    )
    annotations = [_annotation(case) for case in holdout_cases]
    for index, annotation in enumerate(annotations):
        profile_index = index % 12
        if 4 <= profile_index < 8:
            annotation["complexity"].update({"actors": 5, "safety_boundaries": 3})
        elif profile_index >= 8:
            annotation["complexity"].update(
                {
                    "actors": 17,
                    "internal_systems": 17,
                    "ambiguities": 9,
                    "safety_boundaries": 9,
                }
            )
    holdout_path = tmp_path / "holdout.json"
    holdout = {
        "version": FINAL_HOLDOUT_VERSION,
        "claim_class": "blinded-independent-synthetic-holdout",
        "cases": [
            {
                "case_id": case.case_id,
                "name": case.name,
                "prompt": case.prompt,
                "required_terms": [case.prompt.split()[0]],
                "leakage_terms": [case.prompt.split()[-1].rstrip(".")],
                "tags": list(case.tags),
                **(
                    {"confirmed_intent_markdown": case.confirmed_intent_markdown}
                    if case.confirmed_intent_markdown
                    else {}
                ),
            }
            for case in holdout_cases
        ],
        "annotations": annotations,
    }
    holdout_path.write_text(json.dumps(holdout), encoding="utf-8")
    manifest_path = repo_root / "manifest.json"
    manifest = {
        "version": EVALUATION_SPLIT_VERSION,
        "tracked_corpus": {
            "path": "tests/fixtures/corpus.json",
            "sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
            "case_count": 1,
            "lineage": _lineage(
                "tracked-1",
                semantic_family="tracked-semantic",
                template_family="tracked-template",
            ),
            "assignment": {
                "algorithm": "declared-lineage-component-sha256-bucket-v2",
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
            "case_count": 36,
            "annotation_count": 36,
            "claim_class": "blinded-independent-synthetic-holdout",
            "lineage": {
                case.case_id: {
                    "semantic_family": f"holdout-semantic-{case.case_id}",
                    "template_family": f"holdout-template-{index % 3}",
                }
                for index, case in enumerate(holdout_cases)
            },
        },
        "frozen_floors": _floors(),
        "profiles": {
            "complexity_bands": list(release_slice_contract()["complexity_band"]),
            "evidence_formats": list(release_slice_contract()["evidence_format"]),
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
    assert report["final_holdout"]["annotation_count"] == 36
    assert report["final_holdout"]["confidence_sample_issues"] == []
    assert report["acceptance_thresholds"]["overall_case_success"] == 1.0
    assert report["statistical_confidence"]["overall_case_success"] == 0.5

    manifest["version"] = "odylith.greenfield.evaluation-splits.v4"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    retired_v4 = evaluate_frozen_evaluation_contract(
        repo_root=repo_root,
        manifest_path=manifest_path,
        final_holdout_path=holdout_path,
    )
    assert retired_v4["passed"] is False
    assert EVALUATION_SPLIT_VERSION in " ".join(retired_v4["issues"])

    manifest["version"] = EVALUATION_SPLIT_VERSION
    manifest["frozen_floors"]["overall_case_success"] = 0.99
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    softened = evaluate_frozen_evaluation_contract(
        repo_root=repo_root,
        manifest_path=manifest_path,
        final_holdout_path=holdout_path,
    )
    assert softened["passed"] is False
    assert "exact 1.0 acceptance threshold" in " ".join(softened["issues"])


def test_profile_confidence_preflight_rejects_sparse_metric_denominators() -> None:
    commit_cases = tuple(
        replace(
            _case(
                f"sparse-commit-{index}",
                f"Desk {index} supports this path: Operator records result {index}.",
            ),
            tags=(f"model-profile:{profile}",),
        )
        for index, profile in enumerate(MODEL_PROFILES, start=1)
    )
    clarify_cases = tuple(
        replace(
            _case(
                f"sparse-clarify-{index}",
                f"Desk {index} supports this path: Operator records result {index}.",
            ),
            expectation="clarification_required",
            tags=(f"model-profile:{profile}",),
        )
        for index, profile in enumerate(MODEL_PROFILES, start=1)
    )
    cases = (*commit_cases, *clarify_cases)
    annotations = {
        **{case.case_id: _annotation(case) for case in commit_cases},
        **{
            case.case_id: _clarification_annotation(case)
            for case in clarify_cases
        },
    }

    issues = profile_confidence_sample_issues(
        cases=cases,
        annotations=annotations,
        minimum=4,
    )

    assert any(
        "1 `commit` observation(s)" in issue
        for issue in issues
    )
    assert any(
        "1 `clarify` observation(s)" in issue
        for issue in issues
    )
    assert any(
        "1 `component_responsibility_relations` relation sample(s)" in issue
        for issue in issues
    )
    assert not any("`context_relations` relation sample" in issue for issue in issues)


def test_frozen_contract_rejects_v1_and_non_structural_floors(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    corpus_path = repo_root / "corpus.json"
    corpus_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "tracked",
                        "name": "tracked",
                        "prompt": "Tracked Operator records evidence.",
                        "required_terms": ["Tracked"],
                        "leakage_terms": ["evidence"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    case = _case(
        "holdout",
        "Holdout Desk supports this path: Operator records evidence.",
    )
    holdout_path = tmp_path / "holdout.json"
    holdout_path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.final-holdout.v1",
                "claim_class": "blinded",
                "cases": [
                    {
                        "case_id": case.case_id,
                        "name": case.name,
                        "prompt": case.prompt,
                        "required_terms": ["Holdout"],
                        "leakage_terms": ["evidence"],
                    }
                ],
                "annotations": [_annotation(case)],
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
                    "path": "corpus.json",
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
                    "case_count": 1,
                    "annotation_count": 1,
                    "claim_class": "blinded",
                },
                "frozen_floors": {"version": "old"},
                "profiles": {
                    "complexity_bands": list(release_slice_contract()["complexity_band"]),
                    "evidence_formats": list(release_slice_contract()["evidence_format"]),
                    "models": list(MODEL_PROFILES),
                    "model_assignment": {
                        "version": MODEL_PROFILE_ASSIGNMENT_VERSION,
                        "seed": MODEL_PROFILE_ASSIGNMENT_SEED,
                    },
                },
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
    assert EVALUATION_SPLIT_VERSION in " ".join(report["issues"])
    assert FINAL_HOLDOUT_VERSION in " ".join(report["issues"])
    assert "acceptance and confidence fields" in " ".join(report["issues"])


@pytest.mark.parametrize(
    ("profile_key", "expected_issue"),
    (
        ("complexity_bands", "published complexity-band contract"),
        ("evidence_formats", "published evidence-format contract"),
        ("models", "supported model-profile contract"),
    ),
)
def test_frozen_contract_rejects_partial_published_release_slice_declarations(
    tmp_path: Path,
    profile_key: str,
    expected_issue: str,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    holdout_path, manifest_path = write_semantic_release_fixture(
        repo_root=repo_root,
        temp_root=tmp_path,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profiles"][profile_key] = manifest["profiles"][profile_key][:-1]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = evaluate_frozen_evaluation_contract(
        repo_root=repo_root,
        manifest_path=manifest_path,
        final_holdout_path=holdout_path,
    )

    assert report["passed"] is False
    assert expected_issue in " ".join(report["issues"])
