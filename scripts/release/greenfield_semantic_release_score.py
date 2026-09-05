"""Structural Greenfield release scoring over sealed model-authored custody."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    atomic_fact_ledger_hash,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    require_atomic_fact_ledger,
)

from greenfield_matrix_statistics import RELEASE_SLICE_DIMENSIONS
from greenfield_matrix_statistics import release_slice_contract
from greenfield_matrix_statistics import release_slice_coverage_issues
from greenfield_matrix_statistics import release_slice_evidence
from greenfield_matrix_statistics import release_slice_minimum_sample_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract_issues
from greenfield_matrix_statistics import release_statistical_confidence_contract_issues
from greenfield_matrix_statistics import threshold_check
from greenfield_matrix_statistics import wilson_interval
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_relation_fidelity import RELATION_FAMILIES
from greenfield_relation_fidelity import annotation_relation_evidence
from greenfield_relation_fidelity import snapshot_relation_evidence


SEMANTIC_RELEASE_SCORE_VERSION = "odylith.greenfield.semantic-release-score.v6"
NORMALIZED_SEMANTIC_DIGEST_VERSION = "odylith.greenfield.normalized-semantics.v1"
_SCORED_ROLE = "scored"
_REFERENCE_ROLE = "reference_only"


def evaluate_semantic_release(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
    release_required_slices: Mapping[str, Sequence[str]] | None = None,
    _include_model_profiles: bool = True,
    _allow_not_applicable_metrics: bool = False,
) -> dict[str, Any]:
    """Compare frozen expectations with exact atomic custody and typed outcomes."""

    case_ids = [_case_id(case) for case in cases]
    result_ids = [_result_case_id(result) for result in results]
    duplicate_case_ids = _duplicates(case_ids)
    duplicate_result_ids = _duplicates(result_ids)
    results_by_id = {
        case_id: result
        for case_id, result in zip(result_ids, results, strict=False)
        if case_id
    }
    metric_counts: dict[str, list[int]] = {
        "atomic_semantic_fidelity": [0, 0],
        "relation_fidelity": [0, 0],
        "clarification_identity": [0, 0],
        "unnecessary_question_rate": [0, 0],
    }
    case_outcomes: list[dict[str, Any]] = []
    p0_findings: list[dict[str, str]] = []
    p1_findings: list[dict[str, str]] = []
    missing_case_ids: list[str] = []
    for case in cases:
        case_id = _case_id(case)
        annotation = annotations.get(case_id)
        result = results_by_id.get(case_id)
        if annotation is None or result is None:
            missing_case_ids.append(case_id)
            continue
        outcome = _score_case(
            case=case,
            case_id=case_id,
            annotation=annotation,
            result=result,
            metric_counts=metric_counts,
        )
        case_outcomes.append(outcome)
        p0_findings.extend(outcome["p0_findings"])
        p1_findings.extend(outcome["p1_findings"])

    metrics = {name: _metric(name, *counts) for name, counts in metric_counts.items()}
    relation_metric = metrics["relation_fidelity"]
    relation_metric["sample_count"] = relation_metric["denominator"]
    relation_metric["correct_count"] = relation_metric["numerator"]
    relation_metric["incorrect_count"] = relation_metric["denominator"] - relation_metric["numerator"]
    relation_metric["point_estimate"] = relation_metric["rate"]
    if not relation_metric["denominator"]:
        relation_metric["evidence"] = "no commit relation samples were selected"
    passed_count = sum(1 for outcome in case_outcomes if outcome["passed"])
    sample_count = len(case_outcomes)
    overall = _metric("overall_case_success", passed_count, sample_count)
    slices = _slice_rows(cases=cases, outcomes=case_outcomes)
    worst_slice = min(
        slices,
        key=lambda row: (
            float(row["point_estimate"]),
            float(row["confidence_interval_95"]["lower"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    least_confident_slice = min(
        slices,
        key=lambda row: (
            float(row["confidence_interval_95"]["lower"]),
            float(row["point_estimate"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    relation_slices = _relation_slice_rows(cases=cases, outcomes=case_outcomes)
    worst_relation_slice = min(
        relation_slices,
        key=lambda row: (
            float(row["point_estimate"]),
            float(row["confidence_interval_95"]["lower"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    least_confident_relation_slice = min(
        relation_slices,
        key=lambda row: (
            float(row["confidence_interval_95"]["lower"]),
            float(row["point_estimate"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    relation_family_metrics = _relation_family_metrics(case_outcomes)
    acceptance_checks = _acceptance_checks(
        floors=floors,
        metrics=metrics,
        overall=overall,
        worst_slice=worst_slice,
        worst_relation_slice=worst_relation_slice,
        p0_findings=p0_findings,
        p1_findings=p1_findings,
        allow_not_applicable_metrics=_allow_not_applicable_metrics,
    )
    confidence_contract = _mapping(floors.get("statistical_confidence"))
    confidence_contract_issues = release_statistical_confidence_contract_issues(
        confidence_contract,
        minimum_samples=_mapping(floors.get("release_slice_minimum_samples")),
    )
    confidence_checks = _confidence_checks(
        confidence=confidence_contract,
        metrics=metrics,
        relation_family_metrics=relation_family_metrics,
        overall=overall,
        least_confident_slice=least_confident_slice,
        least_confident_relation_slice=least_confident_relation_slice,
        allow_not_applicable_metrics=_allow_not_applicable_metrics,
    )
    issues = [
        str(check["issue"])
        for check in (*acceptance_checks, *confidence_checks)
        if check["status"] in {"failed", "unproven"}
        and str(check.get("issue") or "").strip()
    ]
    issues.extend(confidence_contract_issues)
    if missing_case_ids:
        issues.append("semantic release results are incomplete")
    if set(annotations) != set(case_ids):
        issues.append("semantic release annotations do not exactly match selected cases")
    if duplicate_case_ids:
        issues.append("semantic release cases contain duplicate IDs")
    if duplicate_result_ids:
        issues.append("semantic release results contain duplicate IDs")
    release_evidence_issues = [
        f"case `{outcome['case_id']}` {issue}"
        for outcome in case_outcomes
        for issue in outcome["release_evidence_issues"]
    ]
    issues.extend(release_evidence_issues)
    relation_evidence_issues = [
        f"case `{outcome['case_id']}` {issue}"
        for outcome in case_outcomes
        for issue in outcome["relation_evidence_issues"]
    ]
    issues.extend(relation_evidence_issues)
    required_slices = _required_release_slices(release_required_slices)
    release_minimum_samples = release_slice_minimum_sample_contract()
    if release_required_slices is not None and (
        set(release_required_slices) != set(RELEASE_SLICE_DIMENSIONS)
        or required_slices != release_slice_contract()
    ):
        issues.append("semantic release slice contract does not match the published operating envelope")
    minimum_sample_contract_issues = (
        release_slice_minimum_sample_contract_issues(
            floors.get("release_slice_minimum_samples")
        )
        if release_required_slices is not None
        else []
    )
    issues.extend(minimum_sample_contract_issues)
    coverage_issues = (
        release_slice_coverage_issues(
            slices=slices,
            required=required_slices,
            minimum_samples=release_minimum_samples,
        )
        if release_required_slices is not None
        else []
    )
    issues.extend(coverage_issues)
    model_profiles = (
        _model_profile_reports(
            cases=cases,
            annotations=annotations,
            results=results,
            floors=floors,
            case_outcomes=case_outcomes,
        )
        if _include_model_profiles
        else []
    )
    for profile in model_profiles:
        if profile["status"] != "passed":
            issues.append(f"model profile `{profile['profile']}` failed the semantic release floors")
    normalized_semantic_digests = {
        str(row["case_id"]): str(row["normalized_semantic_digest"])
        for row in case_outcomes if str(row.get("normalized_semantic_digest") or "")
    }
    return {
        "version": SEMANTIC_RELEASE_SCORE_VERSION,
        "status": "passed" if not issues else "failed",
        "passed": not issues,
        "sample_count": sample_count,
        "selected_case_count": len(cases),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_result_ids": duplicate_result_ids,
        "metrics": metrics,
        "relation_sample_count": int(relation_metric["sample_count"]),
        "relation_fidelity_by_family": relation_family_metrics,
        "relation_slices": relation_slices,
        "worst_relation_slice": worst_relation_slice,
        "least_confident_relation_slice": least_confident_relation_slice,
        "overall_case_success": overall,
        "worst_slice": worst_slice,
        "least_confident_slice": least_confident_slice,
        "slices": slices,
        "p0_count": len(p0_findings),
        "p0_findings": p0_findings,
        "p1_count": len(p1_findings),
        "p1_findings": p1_findings,
        "acceptance_checks": acceptance_checks,
        "confidence_contract": confidence_contract,
        "confidence_contract_issues": confidence_contract_issues,
        "confidence_checks": confidence_checks,
        "issues": list(dict.fromkeys(issues)),
        "release_required_slices": required_slices,
        "release_minimum_samples": (
            release_minimum_samples if release_required_slices is not None else {}
        ),
        "release_minimum_sample_contract_issues": minimum_sample_contract_issues,
        "release_evidence_issues": release_evidence_issues,
        "relation_evidence_issues": relation_evidence_issues,
        "normalized_semantic_digests": normalized_semantic_digests,
        "release_coverage_issues": coverage_issues,
        "model_profiles": model_profiles,
        "case_outcomes": [
            {
                "case_id": row["case_id"],
                "passed": row["passed"],
                "expected_outcome": row["expected_outcome"],
                "observed_outcome": row["observed_outcome"],
                "failed_dimensions": row["failed_dimensions"],
                "release_slices": row["release_slices"],
                "relation_counts": row["relation_counts"],
                "normalized_semantic_digest": row["normalized_semantic_digest"],
            }
            for row in case_outcomes
        ],
    }


def _score_case(
    *,
    case: Any,
    case_id: str,
    annotation: Mapping[str, Any],
    result: GreenfieldMatrixResult,
    metric_counts: Mapping[str, list[int]],
) -> dict[str, Any]:
    expected = str(annotation.get("expected_outcome") or "")
    evidence = _mapping(result.evidence)
    clarification = _mapping(evidence.get("clarification"))
    receipt = _mapping(evidence.get("preconfirm_dry_run"))
    snapshot = _mapping(receipt.get("semantic_snapshot"))
    if clarification.get("mode") == "clarification_required":
        observed = "clarify"
    else:
        observed = "commit" if snapshot else "failed"
    failed_dimensions: list[str] = []
    p0: list[dict[str, str]] = []
    p1: list[dict[str, str]] = []
    relation_counts = _empty_relation_counts()
    relation_evidence_issues: list[str] = []
    normalized_semantic_digest = ""
    if expected != observed or result.status != "passed" or not result.quality.passed:
        failed_dimensions.append("outcome")
    if expected == "clarify" and observed == "commit":
        p0.append(_finding(case_id, "material_ambiguity_ignored"))

    if expected == "commit":
        metric_counts["unnecessary_question_rate"][1] += 1
        if observed == "clarify":
            metric_counts["unnecessary_question_rate"][0] += 1
        if snapshot:
            relation_counts, relation_evidence_issues, normalized_semantic_digest = _score_commit(
                case=case,
                case_id=case_id,
                annotation=annotation,
                snapshot=snapshot,
                metric_counts=metric_counts,
                failed_dimensions=failed_dimensions,
                p0=p0,
                p1=p1,
            )
    elif expected == "clarify":
        metric_counts["clarification_identity"][1] += 1
        expected_clarification = _mapping(annotation.get("expected_clarification"))
        observed_fields = clarification.get("required_fields")
        exact_identity = (
            observed == "clarify"
            and isinstance(observed_fields, Sequence)
            and not isinstance(observed_fields, (str, bytes, bytearray))
            and list(observed_fields) == [expected_clarification.get("field")]
            and clarification.get("question") == expected_clarification.get("question")
        )
        if exact_identity:
            metric_counts["clarification_identity"][0] += 1
        else:
            failed_dimensions.append("clarification_identity")

    release_slices, release_evidence_issues = release_slice_evidence(
        case=case,
        result=result,
        annotated_complexity=_mapping(annotation.get("complexity")),
        allow_unsealed_clarification=expected == "clarify" and observed == "clarify",
    )
    if release_evidence_issues:
        failed_dimensions.append("release_evidence")

    return {
        "case_id": case_id,
        "expected_outcome": expected,
        "observed_outcome": observed,
        "passed": not failed_dimensions and not p0,
        "failed_dimensions": list(dict.fromkeys(failed_dimensions)),
        "p0_findings": p0,
        "p1_findings": p1,
        "relation_counts": relation_counts,
        "relation_evidence_issues": relation_evidence_issues,
        "normalized_semantic_digest": normalized_semantic_digest,
        "release_slices": release_slices,
        "release_evidence_issues": list(release_evidence_issues),
    }


def _score_commit(
    *,
    case: Any,
    case_id: str,
    annotation: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    metric_counts: Mapping[str, list[int]],
    failed_dimensions: list[str],
    p0: list[dict[str, str]],
    p1: list[dict[str, str]],
) -> tuple[dict[str, Any], list[str], str]:
    expected_relations = annotation_relation_evidence(
        case=case,
        value=annotation.get("relation_fidelity"),
        atom_rows=annotation.get("atoms"),
    )
    actual_relations = snapshot_relation_evidence(case=case, snapshot=snapshot)
    relation_counts = _empty_relation_counts()
    relation_issues = [
        *(f"relation annotation {issue}" for issue in expected_relations.issues),
        *(f"relation custody {issue}" for issue in actual_relations.issues),
    ]
    if expected_relations.issues:
        p1.append(_finding(case_id, "relation_annotation_invalid"))
    if actual_relations.issues:
        p1.append(_finding(case_id, "relation_custody_invalid"))
    for family in RELATION_FAMILIES:
        expected_family = Counter(expected_relations.keys.get(family, ()))
        actual_family = Counter(actual_relations.keys.get(family, ()))
        matched = (
            sum((expected_family & actual_family).values())
            if not relation_issues
            else 0
        )
        sample_count = max(
            sum((expected_family | actual_family).values()),
            int(expected_relations.minimum_samples.get(family, 0)),
            int(actual_relations.minimum_samples.get(family, 0)),
        )
        relation_counts["matched"] += matched
        relation_counts["sample_count"] += sample_count
        relation_counts["families"][family] = {
            "matched": matched,
            "sample_count": sample_count,
        }
        if expected_family != actual_family:
            p1.append(_finding(case_id, f"{family}_mismatch"))
    metric_counts["relation_fidelity"][0] += int(relation_counts["matched"])
    metric_counts["relation_fidelity"][1] += int(relation_counts["sample_count"])
    if relation_issues or relation_counts["matched"] != relation_counts["sample_count"]:
        failed_dimensions.append("relation_fidelity")

    actual_rows = _validated_atomic_facts(snapshot)
    if actual_rows is None:
        failed_dimensions.append("atomic_custody_invalid")
        p0.append(_finding(case_id, "atomic_custody_invalid"))
        return relation_counts, relation_issues, ""
    expected_rows = _annotation_atoms(annotation, role=_SCORED_ROLE)
    reference_rows = _annotation_atoms(annotation, role=_REFERENCE_ROLE)
    expected = Counter(_expected_atom_key(row) for row in expected_rows)
    reference = {_expected_atom_key(row) for row in reference_rows}
    actual = Counter(
        key
        for row in actual_rows
        if (key := _actual_atom_key(row)) not in reference
    )
    union_count = sum((expected | actual).values())
    matched_count = sum((expected & actual).values())
    metric_counts["atomic_semantic_fidelity"][0] += matched_count
    metric_counts["atomic_semantic_fidelity"][1] += union_count
    if expected != actual:
        failed_dimensions.append("atomic_semantic_fidelity")
        if expected - actual:
            p0.append(_finding(case_id, "expected_atomic_fact_missing"))
        if actual - expected:
            p0.append(_finding(case_id, "unexpected_atomic_fact"))
    digest = ""
    if (
        expected == actual
        and not relation_issues
        and relation_counts["matched"] == relation_counts["sample_count"]
    ):
        digest = _normalized_semantic_digest(annotation)
        if not digest:
            failed_dimensions.append("normalized_semantic_identity")
            p1.append(_finding(case_id, "normalized_semantic_identity_invalid"))
    return relation_counts, relation_issues, digest


def _normalized_semantic_digest(annotation: Mapping[str, Any]) -> str:
    """Bind canonical atom IDs to the exact relation graph without source wording."""

    path_ids: dict[tuple[str, str, int], str] = {}
    role_ids: dict[tuple[int, str], str] = {}
    seen_ids: set[str] = set()
    scored_atoms: list[tuple[str, str, str, str, str, str]] = []
    try:
        for atom in _items(annotation.get("atoms")):
            atom_id = str(atom.get("id") or "").strip()
            source_hash = str(_mapping(atom.get("source")).get("quote_sha256") or "")
            if not atom_id or atom_id in seen_ids or len(source_hash) != 64:
                return ""
            seen_ids.add(atom_id)
            if atom.get("evaluation_role") == _SCORED_ROLE:
                scored_atoms.append((
                    atom_id, str(atom.get("category") or ""), _SCORED_ROLE,
                    str(atom.get("materiality") or ""), str(atom.get("expected_custody") or ""),
                    str(atom.get("expected_polarity") or ""),
                ))
            for link in _items(atom.get("projection_links")):
                order = int(link["relation_order"])
                path = str(link["path"])
                role = str(link["relation_role"])
                if order < 0 or not path or not _index_identity(path_ids, (path, source_hash, order), atom_id):
                    return ""
                if order and role and not _index_identity(role_ids, (order, role), atom_id):
                    return ""
        relation = _mapping(annotation.get("relation_fidelity"))
        events: list[tuple[Any, ...]] = []
        for row in _items(relation.get("first_path_events")):
            order = int(row["order"])
            actor_id = _path_identity(path_ids, row, "actor_fact", order)
            owner_id = _path_identity(path_ids, row, "product_owner", order) if row.get("product_owner_path") else ""
            action_id = role_ids.get((order, "action_verb_quote"), "")
            target_id = role_ids.get((order, "target_quote"), "")
            visible_id = role_ids.get((order, "visible_result_quote"), "")
            if (
                order <= 0
                or actor_id != role_ids.get((order, "actor_fact_quote"), "")
                or not action_id
                or bool(row.get("target_sha256")) != bool(target_id)
                or bool(row.get("visible_result_sha256")) != bool(visible_id)
                or bool(row.get("product_owner_path")) != bool(owner_id)
            ):
                return ""
            events.append((
                order, str(row.get("actor_kind") or ""), actor_id, owner_id,
                action_id, target_id, visible_id,
            ))
        contexts = [
            (
                str(row["context_kind"]), _path_identity(
                    path_ids, row, "fact", int(row["first_path_event_order"])
                ), int(row["first_path_event_order"]),
            )
            for row in _items(relation.get("context_relations"))
        ]
        components = [
            (
                _path_identity(path_ids, row, "responsibility", int(row["first_path_event_order"])),
                _path_identity(path_ids, row, "product_owner", int(row["first_path_event_order"])),
                int(row["first_path_event_order"]), str(row["responsibility_source"]),
            )
            for row in _items(relation.get("component_responsibility_relations"))
        ]
    except (KeyError, TypeError, ValueError):
        return ""
    if not scored_atoms or not events or not components:
        return ""
    if any(not row[1] for row in contexts) or any(not row[0] or not row[1] for row in components):
        return ""
    payload = {
        "version": NORMALIZED_SEMANTIC_DIGEST_VERSION,
        "expected_outcome": "commit",
        "atoms": sorted(scored_atoms),
        "relations": {"first_path_events": sorted(events), "context_relations": sorted(contexts),
                      "component_responsibility_relations": sorted(components)},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _index_identity(index: dict[Any, str], key: Any, atom_id: str) -> bool:
    existing = index.setdefault(key, atom_id)
    return existing == atom_id


def _path_identity(index: Mapping[tuple[str, str, int], str], row: Mapping[str, Any], prefix: str, order: int) -> str:
    key = (str(row.get(f"{prefix}_path") or ""), str(row.get(f"{prefix}_sha256") or ""), order)
    return str(index.get(key) or index.get((key[0], key[1], 0)) or "")


def _validated_atomic_facts(
    snapshot: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...] | None:
    value = snapshot.get("atomic_facts")
    try:
        require_atomic_fact_ledger(value, facts=_mapping(snapshot.get("facts")))
    except ValueError:
        return None
    rows = _items(value)
    if str(snapshot.get("atomic_custody_sha256") or "") != atomic_fact_ledger_hash(rows):
        return None
    return rows


def _annotation_atoms(
    annotation: Mapping[str, Any],
    *,
    role: str,
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        row
        for row in _items(annotation.get("atoms"))
        if row.get("evaluation_role") == role
    )


def _expected_atom_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    source = _mapping(row.get("source"))
    return (
        str(row.get("category") or ""),
        str(row.get("expected_polarity") or ""),
        str(row.get("expected_custody") or ""),
        int(source.get("start_byte", -1)),
        int(source.get("end_byte", -1)),
        str(source.get("quote_sha256") or ""),
        _links_key(row.get("projection_links")),
    )


def _actual_atom_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    categories = _strings(row.get("categories"))
    refs = _items(row.get("source_span_refs"))
    ref = refs[0] if len(refs) == 1 else {}
    return (
        categories[0] if len(categories) == 1 else "",
        str(row.get("polarity") or ""),
        str(row.get("custody_state") or ""),
        int(ref.get("source_start_byte", -1)),
        int(ref.get("source_end_byte", -1)),
        str(ref.get("text_sha256") or ""),
        _links_key(row.get("projection_links")),
    )


def _links_key(value: Any) -> str:
    rows = list(value) if _is_sequence(value) else []
    return json.dumps(rows, sort_keys=True, separators=(",", ":"))


def _acceptance_checks(
    *,
    floors: Mapping[str, Any],
    metrics: Mapping[str, Mapping[str, Any]],
    overall: Mapping[str, Any],
    worst_slice: Mapping[str, Any],
    worst_relation_slice: Mapping[str, Any],
    p0_findings: Sequence[Mapping[str, str]],
    p1_findings: Sequence[Mapping[str, str]],
    allow_not_applicable_metrics: bool,
) -> list[dict[str, Any]]:
    checks = [
        _check("no_observed_p0_contradiction", not p0_findings, "observed P0 semantic contradiction"),
        _check(
            "no_observed_p1_relation_defect",
            not p1_findings,
            "observed P1 typed-relation defect",
        ),
    ]
    for name in ("atomic_semantic_fidelity", "relation_fidelity", "clarification_identity"):
        checks.append(
            _acceptance_metric_floor_check(
                name,
                metrics[name],
                floors.get(name),
                allow_not_applicable=(
                    allow_not_applicable_metrics and name != "relation_fidelity"
                ),
            )
        )
    checks.append(
        _acceptance_metric_ceiling_check(
            "unnecessary_question_rate",
            metrics["unnecessary_question_rate"],
            floors.get("unnecessary_question_rate_ceiling"),
            allow_not_applicable=allow_not_applicable_metrics,
        )
    )
    checks.append(
        _acceptance_metric_floor_check(
            "overall_case_success",
            overall,
            floors.get("overall_case_success"),
        )
    )
    checks.append(
        threshold_check(
            "worst_slice_success",
            observed=(
                worst_slice.get("point_estimate")
                if worst_slice
                else None
            ),
            expected=floors.get("worst_slice_success"),
            direction="floor",
        )
    )
    checks.append(
        threshold_check(
            "worst_relation_slice_fidelity",
            observed=(
                worst_relation_slice.get("point_estimate")
                if worst_relation_slice
                else None
            ),
            expected=floors.get("relation_fidelity"),
            direction="floor",
        )
    )
    return checks


def _confidence_checks(
    *,
    confidence: Mapping[str, Any],
    metrics: Mapping[str, Mapping[str, Any]],
    relation_family_metrics: Mapping[str, Mapping[str, Any]],
    overall: Mapping[str, Any],
    least_confident_slice: Mapping[str, Any],
    least_confident_relation_slice: Mapping[str, Any],
    allow_not_applicable_metrics: bool,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name in ("atomic_semantic_fidelity", "relation_fidelity", "clarification_identity"):
        checks.append(
            _confidence_metric_floor_check(
                name,
                metrics[name],
                confidence.get(name),
                allow_not_applicable=(
                    allow_not_applicable_metrics and name != "relation_fidelity"
                ),
            )
        )
    checks.append(
        _confidence_metric_ceiling_check(
            "unnecessary_question_rate",
            metrics["unnecessary_question_rate"],
            confidence.get("unnecessary_question_rate_ceiling"),
            allow_not_applicable=allow_not_applicable_metrics,
        )
    )
    checks.append(
        _confidence_metric_floor_check(
            "overall_case_success",
            overall,
            confidence.get("overall_case_success"),
        )
    )
    checks.append(
        threshold_check(
            "worst_slice_success",
            observed=(
                _mapping(least_confident_slice.get("confidence_interval_95")).get("lower")
                if least_confident_slice
                else None
            ),
            expected=confidence.get("worst_slice_success"),
            direction="floor",
        )
    )
    checks.append(
        threshold_check(
            "worst_relation_slice_fidelity",
            observed=(
                _mapping(least_confident_relation_slice.get("confidence_interval_95")).get("lower")
                if least_confident_relation_slice
                else None
            ),
            expected=confidence.get("relation_fidelity"),
            direction="floor",
        )
    )
    for family, metric in sorted(relation_family_metrics.items()):
        checks.append(
            _confidence_metric_floor_check(
                f"relation_fidelity:{family}",
                metric,
                confidence.get("relation_fidelity"),
                allow_not_applicable=True,
            )
        )
    return checks


def _model_profile_reports(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
    case_outcomes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    profile_by_case = {
        str(outcome.get("case_id") or ""): str(
            _mapping(outcome.get("release_slices")).get("model_profile") or ""
        )
        for outcome in case_outcomes
    }
    grouped: dict[str, list[Any]] = defaultdict(list)
    for case in cases:
        profile = profile_by_case.get(_case_id(case), "")
        if profile:
            grouped[profile].append(case)
    results_by_id = {_result_case_id(result): result for result in results}
    reports: list[dict[str, Any]] = []
    for profile, profile_cases in sorted(grouped.items()):
        case_ids = {_case_id(case) for case in profile_cases}
        report = evaluate_semantic_release(
            cases=profile_cases,
            annotations={case_id: annotations[case_id] for case_id in case_ids if case_id in annotations},
            results=[results_by_id[case_id] for case_id in case_ids if case_id in results_by_id],
            floors=floors,
            release_required_slices=None,
            _include_model_profiles=False,
            _allow_not_applicable_metrics=True,
        )
        reports.append(
            {
                "profile": profile,
                "status": report["status"],
                "passed": report["passed"],
                "sample_count": report["sample_count"],
                "metrics": report["metrics"],
                "overall_case_success": report["overall_case_success"],
                "worst_slice": report["worst_slice"],
                "least_confident_slice": report["least_confident_slice"],
                "worst_relation_slice": report["worst_relation_slice"],
                "least_confident_relation_slice": report[
                    "least_confident_relation_slice"
                ],
                "relation_slices": report["relation_slices"],
                "p0_count": report["p0_count"],
                "p1_count": report["p1_count"],
                "acceptance_checks": report["acceptance_checks"],
                "confidence_contract": report["confidence_contract"],
                "confidence_contract_issues": report[
                    "confidence_contract_issues"
                ],
                "confidence_checks": report["confidence_checks"],
                "issues": report["issues"],
            }
        )
    return reports


def _acceptance_metric_floor_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return threshold_check(name, observed=observed, expected=expected, direction="floor")


def _acceptance_metric_ceiling_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return threshold_check(name, observed=observed, expected=expected, direction="ceiling")


def _confidence_metric_floor_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = (
        _mapping(metric.get("confidence_interval_95")).get("lower")
        if metric.get("status") == "measured"
        else None
    )
    return threshold_check(name, observed=observed, expected=expected, direction="floor")


def _confidence_metric_ceiling_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = (
        _mapping(metric.get("confidence_interval_95")).get("upper")
        if metric.get("status") == "measured"
        else None
    )
    return threshold_check(name, observed=observed, expected=expected, direction="ceiling")


def _not_applicable_check(name: str, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "not_applicable",
        "observed": None,
        "expected": expected,
        "issue": "",
    }


def _check(name: str, passed: bool, issue: str) -> dict[str, Any]:
    return {"name": name, "status": "passed" if passed else "failed", "issue": "" if passed else issue}


def _metric(name: str, numerator: int, denominator: int) -> dict[str, Any]:
    metric = {
        "name": name,
        "status": "measured" if denominator else "not_applicable",
        "numerator": int(numerator),
        "denominator": int(denominator),
        "rate": round(numerator / denominator, 6) if denominator else None,
    }
    if denominator:
        lower, upper = wilson_interval(numerator, denominator)
        metric["confidence_interval_95"] = _interval_payload(lower, upper)
    else:
        metric["confidence_interval_95"] = None
    return metric


def _slice_rows(*, cases: Sequence[Any], outcomes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    outcome_by_id = {str(row["case_id"]): bool(row["passed"]) for row in outcomes}
    release_slices_by_id = {
        str(row.get("case_id") or ""): _mapping(row.get("release_slices"))
        for row in outcomes
    }
    grouped: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for case in cases:
        case_id = _case_id(case)
        if case_id not in outcome_by_id:
            continue
        release_slices = release_slices_by_id.get(case_id, {})
        for dimension, value in (
            *_case_slices(case),
            *((dimension, str(release_slices.get(dimension) or "")) for dimension in RELEASE_SLICE_DIMENSIONS),
        ):
            if not value:
                continue
            grouped[(dimension, value)].append(outcome_by_id[case_id])
    rows: list[dict[str, Any]] = []
    for (dimension, value), values in sorted(grouped.items()):
        passed = sum(values)
        total = len(values)
        lower, upper = wilson_interval(passed, total)
        rows.append(
            {
                "dimension": dimension,
                "value": value,
                "sample_count": total,
                "passed_count": passed,
                "failed_count": total - passed,
                "point_estimate": round(passed / total, 6),
                "confidence_interval_95": _interval_payload(lower, upper),
            }
        )
    return rows


def _relation_slice_rows(
    *,
    cases: Sequence[Any],
    outcomes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    counts_by_id = {
        str(row.get("case_id") or ""): _mapping(row.get("relation_counts"))
        for row in outcomes
    }
    release_slices_by_id = {
        str(row.get("case_id") or ""): _mapping(row.get("release_slices"))
        for row in outcomes
    }
    grouped: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for case in cases:
        case_id = _case_id(case)
        counts = counts_by_id.get(case_id, {})
        sample_count = int(counts.get("sample_count", 0) or 0)
        if sample_count <= 0:
            continue
        matched = int(counts.get("matched", 0) or 0)
        release_slices = release_slices_by_id.get(case_id, {})
        for dimension, value in (
            *_case_slices(case),
            *((dimension, str(release_slices.get(dimension) or "")) for dimension in RELEASE_SLICE_DIMENSIONS),
        ):
            if not value:
                continue
            grouped[(dimension, value)][0] += matched
            grouped[(dimension, value)][1] += sample_count
    rows: list[dict[str, Any]] = []
    for (dimension, value), (matched, sample_count) in sorted(grouped.items()):
        lower, upper = wilson_interval(matched, sample_count)
        rows.append(
            {
                "dimension": dimension,
                "value": value,
                "sample_count": sample_count,
                "correct_count": matched,
                "incorrect_count": sample_count - matched,
                "point_estimate": round(matched / sample_count, 6),
                "confidence_interval_95": _interval_payload(lower, upper),
            }
        )
    return rows


def _relation_family_metrics(
    outcomes: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    totals = {family: [0, 0] for family in RELATION_FAMILIES}
    for outcome in outcomes:
        families = _mapping(_mapping(outcome.get("relation_counts")).get("families"))
        for family in RELATION_FAMILIES:
            counts = _mapping(families.get(family))
            totals[family][0] += int(counts.get("matched", 0) or 0)
            totals[family][1] += int(counts.get("sample_count", 0) or 0)
    metrics: dict[str, dict[str, Any]] = {}
    for family, (matched, sample_count) in totals.items():
        metric = _metric(family, matched, sample_count)
        metric["sample_count"] = sample_count
        metric["correct_count"] = matched
        metric["incorrect_count"] = sample_count - matched
        metric["point_estimate"] = metric["rate"]
        if not sample_count:
            metric["evidence"] = "no relation samples for this family"
        metrics[family] = metric
    return metrics


def _empty_relation_counts() -> dict[str, Any]:
    return {
        "matched": 0,
        "sample_count": 0,
        "families": {
            family: {"matched": 0, "sample_count": 0}
            for family in RELATION_FAMILIES
        },
    }


def _case_slices(case: Any) -> tuple[tuple[str, str], ...]:
    provenance = getattr(case, "provenance", None)
    rows = [
        ("input_style", str(getattr(case, "input_style", "") or "unspecified")),
        ("expectation", str(getattr(case, "expectation", "") or "transaction_committed")),
        ("source_family", str(getattr(provenance, "source_family", "") or "unspecified")),
    ]
    return tuple(dict.fromkeys(rows))


def _required_release_slices(
    value: Mapping[str, Sequence[str]] | None,
) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}
    normalized: dict[str, tuple[str, ...]] = {}
    for dimension in RELEASE_SLICE_DIMENSIONS:
        rows = value.get(dimension)
        if not _is_sequence(rows):
            normalized[dimension] = ()
            continue
        normalized[dimension] = tuple(
            dict.fromkeys(str(item or "").strip() for item in rows if str(item or "").strip())
        )
    return normalized


def _items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not _is_sequence(value):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _strings(value: Any) -> tuple[str, ...]:
    if not _is_sequence(value):
        return ()
    return tuple(str(item) for item in value)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _duplicates(values: Sequence[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _interval_payload(lower: float, upper: float) -> dict[str, Any]:
    return {
        "method": "wilson",
        "lower": lower,
        "upper": upper,
        "inference_scope": "descriptive fixed-corpus score interval; not a population user-utility claim",
    }


def _finding(case_id: str, category: str) -> dict[str, str]:
    return {"case_id": case_id, "category": category}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or getattr(case, "slug", "")).strip()


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    case = _mapping(_mapping(result.evidence).get("case"))
    return str(case.get("id") or "").strip()

__all__ = ["NORMALIZED_SEMANTIC_DIGEST_VERSION", "SEMANTIC_RELEASE_SCORE_VERSION", "evaluate_semantic_release"]
