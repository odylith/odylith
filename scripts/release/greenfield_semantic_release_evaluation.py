"""Release evaluation for source-grounded Greenfield semantic graphs.

The evaluator never decides semantic equivalence from prose. Independent reviewers
link source annotation IDs to candidate graph IDs; a separate adjudicator resolves
their disagreements. This module verifies those custody records and computes the
frozen release metrics.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import hashlib
import json
from math import sqrt
from pathlib import Path
from typing import Any

from greenfield_semantic_release_support import canonical_sha256
from greenfield_semantic_release_evidence import CANDIDATE_BUNDLE_VERSION
from greenfield_semantic_release_evidence import EVALUATION_CONTRACT_VERSION
from greenfield_semantic_release_evidence import FLOOR_NAMES
from greenfield_semantic_release_evidence import REPORT_VERSION
from greenfield_semantic_release_evidence import require_auxiliary_reports
from greenfield_semantic_release_evidence import require_candidate_bundle
from greenfield_semantic_release_evidence import require_evaluation_contract
from greenfield_semantic_release_evidence import resource_ceiling_checks

REVIEW_VERSION = "odylith.greenfield.semantic-release-review.v1"
ADJUDICATION_VERSION = "odylith.greenfield.semantic-release-adjudication.v1"

ANNOTATION_CATEGORIES = (
    "actors", "actions", "states", "outputs", "constraints", "dependencies",
    "assumptions", "ambiguities", "non_goals", "material_questions",
)
DECISION_FIELDS = (
    "outcome_correct",
    "matched_annotation_ids",
    "unsupported_fact_ids",
    "unsupported_relation_ids",
    "matched_explicit_system_indexes",
    "first_path_comprehensible",
    "package_concise",
    "package_reviewable",
    "surfaces_differentiated",
    "question_necessary",
    "question_fields",
    "equivalent_source_consistent",
    "p0_findings",
    "p1_findings",
)
_Z_95 = 1.959963984540054


def evaluate_semantic_release(
    *,
    corpus: Mapping[str, Any],
    corpus_sha256: str,
    contract: Mapping[str, Any],
    active_evidence_plan: Mapping[str, Any],
    deterministic_law_report: Mapping[str, Any],
    candidates: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    adjudication: Mapping[str, Any],
    auxiliary_reports: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify independent semantic evidence and return one release decision."""

    case_index, annotation_index, annotation_rows = _corpus_indexes(corpus)
    frozen = _contract(contract)
    candidate_index, candidate_meta, bundle_hash, per_case_resources, evidence_bindings = (
        require_candidate_bundle(
            candidates,
            corpus=corpus,
            corpus_sha256=corpus_sha256,
            case_index=case_index,
            contract=frozen,
            active_evidence_plan=active_evidence_plan,
            deterministic_law_report=deterministic_law_report,
        )
    )
    auxiliary_bindings = require_auxiliary_reports(auxiliary_reports, contract=frozen)
    review_rows, review_hashes, reviewer_ids = _reviews(
        reviews,
        candidates=candidate_index,
        candidate_meta=candidate_meta,
        annotations=annotation_index,
        bundle_hash=bundle_hash,
        minimum_count=frozen["minimum_independent_reviews"],
    )
    decisions = _adjudication(
        adjudication,
        candidates=candidate_index,
        candidate_meta=candidate_meta,
        annotations=annotation_index,
        bundle_hash=bundle_hash,
        reviews=review_rows,
        review_hashes=review_hashes,
        reviewer_ids=reviewer_ids,
    )
    metrics = _metrics(
        cases=case_index,
        annotations=annotation_index,
        annotation_rows=annotation_rows,
        candidates=candidate_index,
        decisions=decisions,
    )
    checks = _floor_checks(metrics, frozen["floors"])
    resource_metrics, resource_checks = resource_ceiling_checks(
        per_case_resources,
        ceilings=frozen["resource_ceilings"],
    )
    passed = all(row["passed"] for row in (*checks, *resource_checks))
    return {
        "version": REPORT_VERSION,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "implementation_revision": candidates["implementation_revision"],
        "corpus_sha256": corpus_sha256,
        "evaluation_contract_sha256": canonical_sha256(contract),
        "candidate_bundle_sha256": bundle_hash,
        "evidence_bindings": evidence_bindings,
        "auxiliary_report_bindings": auxiliary_bindings,
        "review_sha256s": review_hashes,
        "adjudication_sha256": canonical_sha256(adjudication),
        "case_count": len(case_index),
        "reviewer_count": len(reviewer_ids),
        "metrics": metrics,
        "resource_metrics": resource_metrics,
        "resource_ceiling_checks": resource_checks,
        "frozen_floors": frozen["floors"],
        "frozen_resource_ceilings": frozen["resource_ceilings"],
        "floor_checks": checks,
    }


def wilson_interval(successes: int, sample_count: int) -> dict[str, Any]:
    if sample_count <= 0:
        lower, upper = 0.0, 1.0
    else:
        count = max(0, min(int(successes), int(sample_count)))
        total = float(sample_count)
        estimate = count / total
        z2 = _Z_95 * _Z_95
        denominator = 1.0 + z2 / total
        center = (estimate + z2 / (2.0 * total)) / denominator
        margin = (_Z_95 / denominator) * sqrt(
            (estimate * (1.0 - estimate) / total) + (z2 / (4.0 * total * total))
        )
        lower, upper = max(0.0, center - margin), min(1.0, center + margin)
    return {
        "method": "wilson",
        "lower": round(lower, 6),
        "upper": round(upper, 6),
        "scope": "descriptive fixed-corpus interval; not a population utility claim",
    }


def _corpus_indexes(
    corpus: Mapping[str, Any],
) -> tuple[
    dict[str, Mapping[str, Any]],
    dict[str, dict[str, Mapping[str, Any]]],
    dict[str, Mapping[str, Any]],
]:
    cases = _mapped_rows(corpus.get("cases"), "corpus.cases")
    annotations = _mapped_rows(corpus.get("annotations"), "corpus.annotations")
    case_index = _unique_index(cases, "case_id", "corpus cases")
    annotation_rows = _unique_index(annotations, "case_id", "corpus annotations")
    if set(case_index) != set(annotation_rows):
        raise ValueError("corpus cases and annotations do not have identical case IDs")
    indexed: dict[str, dict[str, Mapping[str, Any]]] = {}
    for case_id, case in case_index.items():
        prompt = _text(case.get("prompt"), f"{case_id}.prompt")
        prompt_bytes = prompt.encode("utf-8")
        annotation = annotation_rows[case_id]
        expected_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if annotation.get("prompt_sha256") != expected_hash:
            raise ValueError(f"{case_id} annotation prompt hash does not match source evidence")
        by_id: dict[str, Mapping[str, Any]] = {}
        for category in ANNOTATION_CATEGORIES:
            for row in _mapped_rows(annotation.get(category, []), f"{case_id}.{category}"):
                item_id = _text(row.get("id"), f"{case_id}.{category}.id")
                if item_id in by_id or row.get("category") != category:
                    raise ValueError(f"{case_id} annotation IDs or categories are malformed")
                start, end = row.get("source_start"), row.get("source_end")
                if (
                    not isinstance(start, int)
                    or not isinstance(end, int)
                    or not 0 <= start < end <= len(prompt_bytes)
                ):
                    raise ValueError(f"{case_id}.{item_id} source span is invalid")
                if prompt_bytes[start:end] != str(row.get("source_quote") or "").encode("utf-8"):
                    raise ValueError(f"{case_id}.{item_id} source quote does not match its exact span")
                by_id[item_id] = row
        indexed[case_id] = by_id
    return case_index, indexed, annotation_rows


def _contract(value: Mapping[str, Any]) -> dict[str, Any]:
    return require_evaluation_contract(value)


def _reviews(
    values: Sequence[Mapping[str, Any]],
    *,
    candidates: Mapping[str, Mapping[str, Any]],
    candidate_meta: Mapping[str, Mapping[str, Any]],
    annotations: Mapping[str, Mapping[str, Mapping[str, Any]]],
    bundle_hash: str,
    minimum_count: int,
) -> tuple[list[dict[str, dict[str, Any]]], list[str], list[str]]:
    if len(values) < minimum_count:
        raise ValueError("semantic release evidence lacks the required independent reviews")
    indexed_reviews: list[dict[str, dict[str, Any]]] = []
    hashes: list[str] = []
    reviewer_ids: list[str] = []
    authoring_run_ids = {
        str(meta[field])
        for meta in candidate_meta.values()
        for field in ("critic_run_id", "author_run_id")
    }
    for index, raw in enumerate(values):
        review = _mapping(raw, f"review[{index}]")
        _exact_keys(
            review,
            {"version", "reviewer_id", "independent", "candidate_bundle_sha256", "cases"},
            f"review[{index}]",
        )
        if review.get("version") != REVIEW_VERSION or review.get("independent") is not True:
            raise ValueError("semantic release reviews must be versioned and independently authored")
        reviewer_id = _text(review.get("reviewer_id"), f"review[{index}].reviewer_id")
        if reviewer_id in reviewer_ids:
            raise ValueError("semantic release reviewer identities must be distinct")
        if reviewer_id in authoring_run_ids:
            raise ValueError("semantic release reviewers must be independent from authoring runs")
        if review.get("candidate_bundle_sha256") != bundle_hash:
            raise ValueError("semantic release review does not bind the candidate bundle")
        rows = _decision_index(
            review.get("cases"),
            label=f"review[{index}]",
            candidates=candidates,
            candidate_meta=candidate_meta,
            annotations=annotations,
        )
        indexed_reviews.append(rows)
        hashes.append(canonical_sha256(review))
        reviewer_ids.append(reviewer_id)
    return indexed_reviews, sorted(hashes), reviewer_ids


def _adjudication(
    value: Mapping[str, Any],
    *,
    candidates: Mapping[str, Mapping[str, Any]],
    candidate_meta: Mapping[str, Mapping[str, Any]],
    annotations: Mapping[str, Mapping[str, Mapping[str, Any]]],
    bundle_hash: str,
    reviews: Sequence[Mapping[str, Mapping[str, Any]]],
    review_hashes: Sequence[str],
    reviewer_ids: Sequence[str],
) -> dict[str, dict[str, Any]]:
    row = _mapping(value, "adjudication")
    _exact_keys(
        row,
        {
            "version", "adjudicator_id", "independent", "candidate_bundle_sha256",
            "review_sha256s", "cases", "resolved_disagreements",
        },
        "adjudication",
    )
    if row.get("version") != ADJUDICATION_VERSION or row.get("independent") is not True:
        raise ValueError("semantic release adjudication must be versioned and independent")
    adjudicator = _text(row.get("adjudicator_id"), "adjudicator_id")
    if adjudicator in reviewer_ids:
        raise ValueError("semantic release adjudicator must be distinct from reviewers")
    authoring_run_ids = {
        str(meta[field])
        for meta in candidate_meta.values()
        for field in ("critic_run_id", "author_run_id")
    }
    if adjudicator in authoring_run_ids:
        raise ValueError("semantic release adjudicator must be independent from authoring runs")
    if row.get("candidate_bundle_sha256") != bundle_hash:
        raise ValueError("semantic release adjudication does not bind the candidate bundle")
    if sorted(_strings(row.get("review_sha256s"), "review_sha256s")) != list(review_hashes):
        raise ValueError("semantic release adjudication does not bind every review")
    decisions = _decision_index(
        row.get("cases"),
        label="adjudication",
        candidates=candidates,
        candidate_meta=candidate_meta,
        annotations=annotations,
    )
    disagreements = _mapped_rows(row.get("resolved_disagreements"), "resolved_disagreements")
    resolutions: dict[tuple[str, str], Mapping[str, Any]] = {}
    for resolution in disagreements:
        _exact_keys(resolution, {"case_id", "field", "selected_value_sha256", "rationale"}, "resolved disagreement")
        key = (
            _text(resolution.get("case_id"), "resolution case_id"),
            _text(resolution.get("field"), "resolution field"),
        )
        if key in resolutions or key[0] not in decisions or key[1] not in DECISION_FIELDS:
            raise ValueError("semantic release disagreement resolution is duplicated or unknown")
        _text(resolution.get("rationale"), "resolution rationale")
        if resolution.get("selected_value_sha256") != canonical_sha256(decisions[key[0]][key[1]]):
            raise ValueError("semantic release disagreement resolution does not bind the selected value")
        resolutions[key] = resolution
    actual_disagreements: set[tuple[str, str]] = set()
    for case_id, decision in decisions.items():
        for field in DECISION_FIELDS:
            values = [canonical_sha256(review[case_id][field]) for review in reviews]
            if len(set(values)) == 1:
                if canonical_sha256(decision[field]) != values[0]:
                    raise ValueError("adjudication changed a unanimous independent review decision")
            else:
                actual_disagreements.add((case_id, field))
    if set(resolutions) != actual_disagreements:
        raise ValueError("adjudication must resolve every and only actual reviewer disagreement")
    return decisions


def _decision_index(
    value: Any,
    *,
    label: str,
    candidates: Mapping[str, Mapping[str, Any]],
    candidate_meta: Mapping[str, Mapping[str, Any]],
    annotations: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, dict[str, Any]]:
    rows = _mapped_rows(value, f"{label}.cases")
    indexed = _unique_index(rows, "case_id", f"{label}.cases")
    if set(indexed) != set(candidates):
        raise ValueError(f"{label} must decide every candidate exactly once")
    normalized: dict[str, dict[str, Any]] = {}
    for case_id, raw in indexed.items():
        _exact_keys(raw, {"case_id", "candidate_sha256", *DECISION_FIELDS}, f"{label}.{case_id}")
        meta = candidate_meta[case_id]
        if raw.get("candidate_sha256") != meta["candidate_sha256"]:
            raise ValueError(f"{label}.{case_id} does not bind the candidate")
        decision = {"case_id": case_id, "candidate_sha256": meta["candidate_sha256"]}
        for field in (
            "outcome_correct", "first_path_comprehensible", "package_concise",
            "package_reviewable", "surfaces_differentiated", "question_necessary",
            "equivalent_source_consistent",
        ):
            if not isinstance(raw.get(field), bool):
                raise ValueError(f"{label}.{case_id}.{field} must be boolean")
            decision[field] = raw[field]
        decision["matched_annotation_ids"] = _unique_strings(
            raw.get("matched_annotation_ids"),
            f"{label}.{case_id}.matched_annotation_ids",
        )
        if not set(decision["matched_annotation_ids"]) <= set(annotations[case_id]):
            raise ValueError(f"{label}.{case_id} cites unknown source annotations")
        for field, valid_ids in (
            ("unsupported_fact_ids", meta["fact_ids"]),
            ("unsupported_relation_ids", meta["relation_ids"]),
        ):
            decision[field] = _unique_strings(raw.get(field), f"{label}.{case_id}.{field}")
            if not set(decision[field]) <= set(valid_ids):
                raise ValueError(f"{label}.{case_id}.{field} cites unknown graph IDs")
        indexes = raw.get("matched_explicit_system_indexes")
        if not isinstance(indexes, list) or any(not isinstance(item, int) or item < 0 for item in indexes):
            raise ValueError(f"{label}.{case_id} explicit system indexes are malformed")
        if len(indexes) != len(set(indexes)):
            raise ValueError(f"{label}.{case_id} explicit system indexes are duplicated")
        decision["matched_explicit_system_indexes"] = sorted(indexes)
        decision["question_fields"] = _unique_strings(raw.get("question_fields"), f"{label}.{case_id}.question_fields")
        decision["p0_findings"] = _unique_strings(raw.get("p0_findings"), f"{label}.{case_id}.p0_findings")
        decision["p1_findings"] = _unique_strings(raw.get("p1_findings"), f"{label}.{case_id}.p1_findings")
        normalized[case_id] = decision
    return normalized


def _metrics(
    *,
    cases: Mapping[str, Mapping[str, Any]],
    annotations: Mapping[str, Mapping[str, Mapping[str, Any]]],
    annotation_rows: Mapping[str, Mapping[str, Any]],
    candidates: Mapping[str, Mapping[str, Any]],
    decisions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    totals = Counter()
    case_outcomes: dict[str, bool] = {}
    slices: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for case_id, case in cases.items():
        source_rows = annotations[case_id]
        annotation_row = annotation_rows[case_id]
        decision = decisions[case_id]
        candidate = candidates[case_id]
        expected_outcome = str(annotation_row.get("expected_outcome") or "")
        material_ids = {
            item_id for item_id, item in source_rows.items() if item.get("materiality") == "material"
        }
        accepted_ids = {
            item_id for item_id, item in source_rows.items()
            if item.get("materiality") == "material" and item.get("expected_custody") == "accepted_fact"
        }
        constraint_ids = {
            item_id for item_id, item in source_rows.items() if item.get("category") == "constraints"
        }
        matched = set(decision["matched_annotation_ids"])
        totals["material_expected"] += len(material_ids)
        totals["material_matched"] += len(material_ids & matched)
        totals["accepted_expected"] += len(accepted_ids)
        totals["accepted_matched"] += len(accepted_ids & matched)
        totals["constraint_expected"] += len(constraint_ids)
        totals["constraint_matched"] += len(constraint_ids & matched)
        totals["matched_claims"] += len(matched)
        totals["unsupported_facts"] += len(decision["unsupported_fact_ids"])
        totals["unsupported_relations"] += len(decision["unsupported_relation_ids"])
        explicit_systems = list(annotation_row.get("explicit_systems") or [])
        if any(index >= len(explicit_systems) for index in decision["matched_explicit_system_indexes"]):
            raise ValueError(f"{case_id} adjudication cites an unknown explicit system")
        totals["systems_expected"] += len(explicit_systems)
        totals["systems_matched"] += len(decision["matched_explicit_system_indexes"])
        totals["p0"] += len(decision["p0_findings"])
        totals["p1"] += len(decision["p1_findings"])
        totals["deterministic_failures"] += len(
            candidates[case_id]["transaction_proof"]["deterministic_law_failures"]
        )
        is_commit = expected_outcome == "commit"
        is_clarify = expected_outcome == "clarify"
        question_fields = set(decision["question_fields"])
        expected_fields = set(annotation_row.get("expected_question_fields") or [])
        question_success = is_clarify and decision["question_necessary"] and expected_fields <= question_fields
        if is_clarify:
            totals["question_expected"] += 1
            totals["question_matched"] += int(question_success)
        if is_commit:
            totals["unnecessary_question_denominator"] += 1
            totals["unnecessary_questions"] += int(
                candidate.get("outcome") == "clarify" or decision["question_necessary"]
            )
            totals["first_path_expected"] += 1
            totals["first_path_matched"] += int(decision["first_path_comprehensible"])
            utility = (
                decision["package_concise"]
                and decision["package_reviewable"]
                and decision["surfaces_differentiated"]
            )
            totals["package_expected"] += 1
            totals["package_matched"] += int(utility)
        else:
            utility = True
        case_passed = all(
            (
                decision["outcome_correct"],
                expected_outcome == candidate.get("outcome"),
                material_ids <= matched,
                not decision["unsupported_fact_ids"],
                not decision["unsupported_relation_ids"],
                not decision["p0_findings"],
                not decision["p1_findings"],
                len(decision["matched_explicit_system_indexes"]) == len(explicit_systems),
                decision["first_path_comprehensible"] if is_commit else question_success,
                utility,
                not candidate["transaction_proof"]["deterministic_law_failures"],
            )
        )
        case_outcomes[case_id] = case_passed
        for dimension, value in _case_slices(case, annotation_row, candidate):
            slices[(dimension, value)].append(case_passed)
    groups: dict[str, list[str]] = defaultdict(list)
    for case_id, case in cases.items():
        group = str(case.get("metamorphic_group") or "").strip()
        if group:
            groups[group].append(case_id)
    equivalent_groups = [members for members in groups.values() if len(members) >= 2]
    equivalent_passed = sum(
        all(decisions[case_id]["equivalent_source_consistent"] for case_id in members)
        for members in equivalent_groups
    )
    slice_rows = [_slice_row(key, values) for key, values in sorted(slices.items())]
    worst = min(
        slice_rows,
        key=lambda row: (row["point_estimate"], row["confidence_interval_95"]["lower"]),
        default={},
    )
    passed_count = sum(case_outcomes.values())
    case_count = len(case_outcomes)
    observed_claims = totals["matched_claims"] + totals["unsupported_facts"]
    denominators = {
        "fact_precision": observed_claims,
        "material_semantic_recall": totals["material_expected"],
        "accepted_fact_custody": totals["accepted_expected"],
        "constraint_recall": totals["constraint_expected"],
        "explicit_system_recall": totals["systems_expected"],
        "material_question_recall": totals["question_expected"],
        "unnecessary_question_rate": totals["unnecessary_question_denominator"],
        "first_path_comprehension": totals["first_path_expected"],
        "package_utility": totals["package_expected"],
        "equivalent_source_convergence": len(equivalent_groups),
        "overall_success": case_count,
    }
    return {
        "p0_findings": totals["p0"],
        "p1_findings": totals["p1"],
        "fact_precision": _rate(totals["matched_claims"], observed_claims),
        "material_semantic_recall": _rate(totals["material_matched"], totals["material_expected"]),
        "accepted_fact_custody": _rate(totals["accepted_matched"], totals["accepted_expected"]),
        "constraint_recall": _rate(totals["constraint_matched"], totals["constraint_expected"]),
        "explicit_system_recall": _rate(totals["systems_matched"], totals["systems_expected"]),
        "material_question_recall": _rate(totals["question_matched"], totals["question_expected"]),
        "unnecessary_question_rate": _rate(
            totals["unnecessary_questions"],
            totals["unnecessary_question_denominator"],
        ),
        "first_path_comprehension": _rate(totals["first_path_matched"], totals["first_path_expected"]),
        "package_utility": _rate(totals["package_matched"], totals["package_expected"]),
        "equivalent_source_convergence": _rate(equivalent_passed, len(equivalent_groups)),
        "unsupported_relation_count": totals["unsupported_relations"],
        "deterministic_law_failures": totals["deterministic_failures"],
        "overall_success": _rate(passed_count, case_count),
        "overall_confidence_interval_95": wilson_interval(passed_count, case_count),
        "passed_case_count": passed_count,
        "failed_case_count": case_count - passed_count,
        "metric_denominators": denominators,
        "worst_slice": worst,
        "slices": slice_rows,
    }


def _case_slices(
    case: Mapping[str, Any],
    annotation: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> tuple[tuple[str, str], ...]:
    complexity = _mapping(annotation.get("complexity", {}), "annotation complexity")
    score = sum(int(complexity.get(name) or 0) for name in (
        "actors", "state_objects", "paths", "external_systems", "contradictions", "ambiguities", "safety_boundaries",
    ))
    band = "simple" if score <= 3 else "moderate" if score <= 6 else "complex"
    values = [
        ("input_style", str(case.get("input_style") or "unspecified")),
        ("expected_outcome", str(annotation.get("expected_outcome") or "unspecified")),
        ("complexity", band),
        ("model_profile", str(candidate.get("model_profile") or "unspecified")),
        ("host_profile", str(candidate.get("host_profile") or "unspecified")),
    ]
    values.extend(("tag", str(tag)) for tag in case.get("tags", []) if str(tag).strip())
    return tuple(dict.fromkeys(values))


def _slice_row(key: tuple[str, str], values: Sequence[bool]) -> dict[str, Any]:
    passed = sum(values)
    total = len(values)
    return {
        "dimension": key[0],
        "value": key[1],
        "sample_count": total,
        "passed_count": passed,
        "failed_count": total - passed,
        "point_estimate": _rate(passed, total),
        "confidence_interval_95": wilson_interval(passed, total),
    }


def _floor_checks(metrics: Mapping[str, Any], floors: Mapping[str, float]) -> list[dict[str, Any]]:
    bindings = {
        "maximum_p0_findings": ("p0_findings", "<="),
        "maximum_p1_findings": ("p1_findings", "<="),
        "minimum_fact_precision": ("fact_precision", ">="),
        "minimum_accepted_fact_custody": ("accepted_fact_custody", ">="),
        "minimum_constraint_recall": ("constraint_recall", ">="),
        "minimum_explicit_system_recall": ("explicit_system_recall", ">="),
        "minimum_material_question_recall": ("material_question_recall", ">="),
        "maximum_unnecessary_question_rate": ("unnecessary_question_rate", "<="),
        "minimum_first_path_comprehension": ("first_path_comprehension", ">="),
        "minimum_package_utility": ("package_utility", ">="),
        "minimum_equivalent_source_convergence": ("equivalent_source_convergence", ">="),
        "minimum_overall_success": ("overall_success", ">="),
        "minimum_worst_slice_success": ("worst_slice.point_estimate", ">="),
        "maximum_deterministic_law_failures": ("deterministic_law_failures", "<="),
    }
    rows: list[dict[str, Any]] = []
    for floor_name in FLOOR_NAMES:
        metric_name, operator = bindings[floor_name]
        if metric_name == "worst_slice.point_estimate":
            observed_value = _mapping(metrics.get("worst_slice", {}), "worst_slice").get(
                "point_estimate"
            )
        else:
            observed_value = metrics[metric_name]
        threshold = float(floors[floor_name])
        proven = isinstance(observed_value, (int, float)) and not isinstance(
            observed_value, bool
        )
        observed = float(observed_value) if proven else None
        passed = bool(
            proven
            and (
                observed <= threshold
                if operator == "<="
                else observed >= threshold
            )
        )
        rows.append({
            "floor": floor_name,
            "metric": metric_name,
            "operator": operator,
            "observed": observed,
            "threshold": threshold,
            "evidence_status": "proven" if proven else "unproven",
            "passed": passed,
        })
    return rows


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _mapped_rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def _unique_index(rows: Sequence[Mapping[str, Any]], key: str, label: str) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _text(row.get(key), f"{label}.{key}")
        if value in indexed:
            raise ValueError(f"{label} contains duplicate {key}: {value}")
        indexed[value] = row
    return indexed


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} fields do not match the versioned contract")


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be non-empty text")
    return text


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a string array")
    rows = [_text(item, label) for item in value]
    if not rows:
        raise ValueError(f"{label} must not be empty")
    if len(rows) != len(set(rows)):
        raise ValueError(f"{label} contains duplicates")
    return rows


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a string array")
    rows = [_text(item, label) for item in value]
    if len(rows) != len(set(rows)):
        raise ValueError(f"{label} contains duplicates")
    return sorted(rows)


def _rate(successes: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(successes / total, 6)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return _mapping(value, str(path))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--active-evidence-plan", type=Path, required=True)
    parser.add_argument("--deterministic-law-report", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--review", type=Path, action="append", required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--host-parity-report", type=Path, required=True)
    parser.add_argument("--lower-capability-safety-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    corpus_bytes = args.corpus.read_bytes()
    corpus = _mapping(json.loads(corpus_bytes), str(args.corpus))
    report = evaluate_semantic_release(
        corpus=corpus,
        corpus_sha256=hashlib.sha256(corpus_bytes).hexdigest(),
        contract=_load(args.contract),
        active_evidence_plan=_load(args.active_evidence_plan),
        deterministic_law_report=_load(args.deterministic_law_report),
        candidates=_load(args.candidates),
        reviews=[_load(path) for path in args.review],
        adjudication=_load(args.adjudication),
        auxiliary_reports={
            "host_parity": _load(args.host_parity_report),
            "lower_capability_safety": _load(args.lower_capability_safety_report),
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ADJUDICATION_VERSION",
    "CANDIDATE_BUNDLE_VERSION",
    "EVALUATION_CONTRACT_VERSION",
    "REPORT_VERSION",
    "REVIEW_VERSION",
    "canonical_sha256",
    "evaluate_semantic_release",
    "wilson_interval",
]
