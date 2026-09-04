"""Frozen split, holdout, atomic, and relation contracts for Greenfield release proof."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any

from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_matrix_release_artifacts import sha256_file
from greenfield_matrix_input_axes import RELEASE_INPUT_STYLES
from greenfield_matrix_clarification import material_question_field_issues
from greenfield_matrix_statistics import expected_case_evidence_format
from greenfield_matrix_statistics import expected_case_source_complexity
from greenfield_matrix_statistics import release_slice_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract_issues
from greenfield_matrix_statistics import release_statistical_confidence_contract
from greenfield_matrix_statistics import release_statistical_confidence_contract_issues
from greenfield_matrix_statistics import release_statistical_confidence_sample_minimum
from greenfield_model_profiles import MODEL_PROFILES
from greenfield_model_profiles import MODEL_PROFILE_ASSIGNMENT_SEED
from greenfield_model_profiles import MODEL_PROFILE_ASSIGNMENT_VERSION
from greenfield_model_profiles import assign_model_profiles
from greenfield_model_profiles import case_model_profile
from greenfield_model_profiles import profile_coverage
from greenfield_model_profiles import profile_counts
from greenfield_relation_fidelity import RELATION_FAMILIES
from greenfield_relation_fidelity import annotation_relation_evidence
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    SUPPORTED_COMPLEXITY_DIMENSIONS,
    greenfield_complexity_band,
)
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


EVALUATION_SPLIT_VERSION = "odylith.greenfield.evaluation-splits.v5"
FINAL_HOLDOUT_VERSION = "odylith.greenfield.final-holdout.v5"
STRUCTURAL_FLOORS_VERSION = "odylith.greenfield.structural-floors.v4"
ATOMIC_CATEGORIES = (
    "actors",
    "actions",
    "states",
    "outputs",
    "constraints",
    "dependencies",
    "assumptions",
    "ambiguities",
    "non_goals",
)
MATERIALITY_VALUES = frozenset({"material", "non_material"})
CUSTODY_VALUES = frozenset({"accepted_fact", "bounded_interpretation", "assumption", "ambiguity"})
POLARITY_VALUES = frozenset({"affirmed", "required", "prohibited"})
EVALUATION_ROLES = frozenset({"scored", "reference_only"})
EXPECTED_OUTCOMES = frozenset({"commit", "clarify"})
COMPLEXITY_DIMENSIONS = SUPPORTED_COMPLEXITY_DIMENSIONS
_FROZEN_METRIC_FLOOR_KEYS = frozenset(
    {
        "atomic_semantic_fidelity",
        "relation_fidelity",
        "clarification_identity",
        "unnecessary_question_rate_ceiling",
        "overall_case_success",
        "worst_slice_success",
    }
)
_FROZEN_FLOOR_KEYS = _FROZEN_METRIC_FLOOR_KEYS | {
    "release_slice_minimum_samples",
    "statistical_confidence",
}
_FROZEN_ACCEPTANCE_THRESHOLDS = {
    "atomic_semantic_fidelity": 1.0,
    "relation_fidelity": 1.0,
    "clarification_identity": 1.0,
    "unnecessary_question_rate_ceiling": 0.0,
    "overall_case_success": 1.0,
    "worst_slice_success": 1.0,
}
_LINEAGE_KEYS = frozenset({"semantic_family", "template_family"})
_RELATION_ROLES = frozenset(
    {
        "actor_quote",
        "action_verb_quote",
        "target_quote",
        "visible_result_quote",
    }
)


def evaluate_frozen_evaluation_contract(
    *,
    repo_root: Path,
    manifest_path: Path,
    final_holdout_path: Path,
) -> dict[str, Any]:
    """Validate frozen inputs without exposing holdout prompt text."""

    root = Path(repo_root).expanduser().resolve()
    manifest = _json_object(Path(manifest_path).expanduser().resolve(), label="evaluation split manifest")
    issues: list[str] = []
    if manifest.get("version") != EVALUATION_SPLIT_VERSION:
        issues.append(f"evaluation split manifest must declare {EVALUATION_SPLIT_VERSION}")
    tracked = _mapping(manifest.get("tracked_corpus"))
    tracked_path = _repo_path(root, tracked.get("path"), issues=issues, label="tracked corpus")
    tracked_cases: tuple[GreenfieldMatrixCase, ...] = ()
    if tracked_path is not None:
        _require_file_hash(
            tracked_path,
            expected=tracked.get("sha256"),
            issues=issues,
            label="tracked corpus",
        )
        try:
            tracked_cases = load_case_file(tracked_path)
        except RuntimeError as error:
            issues.append(f"tracked corpus cannot be loaded: {error}")
    expected_tracked_count = _positive_int(tracked.get("case_count"))
    if expected_tracked_count != len(tracked_cases):
        issues.append(
            f"tracked corpus case_count mismatch: expected {expected_tracked_count}, loaded {len(tracked_cases)}"
        )
    assignments, assignment_issues = assign_tracked_splits(
        tracked_cases,
        assignment=_mapping(tracked.get("assignment")),
        lineage=tracked.get("lineage"),
    )
    issues.extend(assignment_issues)

    final_ref = _mapping(manifest.get("final_holdout"))
    holdout_path = Path(final_holdout_path).expanduser().resolve()
    _require_file_hash(
        holdout_path,
        expected=final_ref.get("sha256"),
        issues=issues,
        label="final holdout",
    )
    expected_holdout_bytes = _positive_int(final_ref.get("byte_size"))
    if not holdout_path.is_file() or holdout_path.stat().st_size != expected_holdout_bytes:
        issues.append("final holdout byte_size does not match the frozen manifest")
    holdout_payload: dict[str, Any] = {}
    holdout_cases: tuple[GreenfieldMatrixCase, ...] = ()
    annotations: dict[str, Mapping[str, Any]] = {}
    try:
        holdout_payload = _json_object(holdout_path, label="final holdout")
        holdout_cases = load_case_file(holdout_path)
    except RuntimeError as error:
        issues.append(str(error))
    if holdout_payload:
        if holdout_payload.get("version") != FINAL_HOLDOUT_VERSION:
            issues.append(f"final holdout must declare {FINAL_HOLDOUT_VERSION}")
        if holdout_payload.get("claim_class") != final_ref.get("claim_class"):
            issues.append("final holdout claim_class does not match the frozen manifest")
        annotations, annotation_issues = validate_atomic_annotations(
            cases=holdout_cases,
            rows=holdout_payload.get("annotations"),
        )
        issues.extend(annotation_issues)
    if len(holdout_cases) != _positive_int(final_ref.get("case_count")):
        issues.append("final holdout case_count does not match the frozen manifest")
    if len(annotations) != _positive_int(final_ref.get("annotation_count")):
        issues.append("final holdout annotation_count does not match the frozen manifest")
    profiles = _mapping(manifest.get("profiles"))
    required_release_slices = release_slice_contract()
    declared_styles = _string_sequence(profiles.get("evidence_styles"))
    unknown_styles = sorted(set(declared_styles) - set(RELEASE_INPUT_STYLES))
    if unknown_styles:
        issues.append("evaluation profiles declare unsupported evidence styles: " + ", ".join(unknown_styles))
    input_style_counts = Counter(str(case.input_style) for case in holdout_cases)
    missing_styles = [style for style in declared_styles if input_style_counts.get(style, 0) == 0]
    if missing_styles:
        issues.append("final holdout has no cases for declared evidence styles: " + ", ".join(missing_styles))
    declared_bands = _string_sequence(profiles.get("complexity_bands"))
    if declared_bands != required_release_slices["complexity_band"]:
        issues.append("evaluation profiles do not match the published complexity-band contract")
    declared_formats = _string_sequence(profiles.get("evidence_formats"))
    if declared_formats != required_release_slices["evidence_format"]:
        issues.append("evaluation profiles do not match the published evidence-format contract")
    declared_models = _string_sequence(profiles.get("models"))
    if declared_models != required_release_slices["model_profile"]:
        issues.append("evaluation profiles do not match the supported model-profile contract")
    model_assignment = _mapping(profiles.get("model_assignment"))
    if model_assignment.get("version") != MODEL_PROFILE_ASSIGNMENT_VERSION:
        issues.append("evaluation model-profile assignment version is unsupported")
    if model_assignment.get("seed") != MODEL_PROFILE_ASSIGNMENT_SEED:
        issues.append("evaluation model-profile assignment seed does not match the frozen contract")
    assigned_holdout_cases = assign_model_profiles(holdout_cases)
    model_counts = profile_counts(assigned_holdout_cases) if assigned_holdout_cases else {}
    missing_models = [profile for profile in MODEL_PROFILES if int(model_counts.get(profile, 0)) == 0]
    if missing_models:
        issues.append("final holdout has no assigned cases for model profiles: " + ", ".join(missing_models))
    model_coverage = profile_coverage(assigned_holdout_cases) if assigned_holdout_cases else {}
    for dimension, values in model_coverage.items():
        for value, counts in values.items():
            if sum(counts.values()) < len(MODEL_PROFILES):
                continue
            missing = [profile for profile in MODEL_PROFILES if int(counts.get(profile, 0)) == 0]
            if missing:
                issues.append(
                    f"final holdout model profiles do not cover {dimension} `{value}`: "
                    + ", ".join(missing)
                )
    complexity_band_counts = Counter(
        greenfield_complexity_band(_mapping(annotation.get("complexity")))
        for annotation in annotations.values()
    )
    evidence_format_counts = Counter(expected_case_evidence_format(case) for case in holdout_cases)
    for dimension, counts in (
        ("complexity_band", complexity_band_counts),
        ("evidence_format", evidence_format_counts),
        ("model_profile", Counter(model_counts)),
    ):
        missing = [
            value
            for value in required_release_slices[dimension]
            if int(counts.get(value, 0)) == 0
        ]
        unknown = sorted(set(counts) - set(required_release_slices[dimension]))
        if missing:
            issues.append(f"final holdout lacks {dimension} coverage: " + ", ".join(missing))
        if unknown:
            issues.append(f"final holdout has unknown {dimension} coverage: " + ", ".join(unknown))
        minimums = release_slice_minimum_sample_contract()[dimension]
        for value in required_release_slices[dimension]:
            observed = int(counts.get(value, 0))
            minimum = int(minimums[value])
            if observed and observed < minimum:
                issues.append(
                    f"final holdout has {observed} sample(s) for {dimension} `{value}`; "
                    f"requires at least {minimum}"
                )
    profile_confidence_sample_minimum = release_statistical_confidence_sample_minimum()
    profile_confidence_issues = profile_confidence_sample_issues(
        cases=assigned_holdout_cases,
        annotations=annotations,
        minimum=profile_confidence_sample_minimum,
    )
    issues.extend(profile_confidence_issues)
    frozen_floors = _mapping(manifest.get("frozen_floors"))
    issues.extend(_frozen_floor_issues(frozen_floors))
    issues.extend(
        cross_split_membership_issues(
            tracked_cases=tracked_cases,
            tracked_assignments=assignments,
            final_holdout_cases=holdout_cases,
            tracked_lineage=tracked.get("lineage"),
            final_holdout_lineage=final_ref.get("lineage"),
        )
    )
    return {
        "version": EVALUATION_SPLIT_VERSION,
        "status": "passed" if not issues else "failed",
        "passed": not issues,
        "issues": list(dict.fromkeys(issues)),
        "tracked": {
            "case_count": len(tracked_cases),
            "split_counts": dict(sorted(Counter(assignments.values()).items())),
            "sha256": str(tracked.get("sha256") or ""),
        },
        "final_holdout": {
            "case_count": len(holdout_cases),
            "annotation_count": len(annotations),
            "sha256": str(final_ref.get("sha256") or ""),
            "claim_class": str(final_ref.get("claim_class") or ""),
            "outcome_counts": _outcome_counts(holdout_cases),
            "input_style_counts": dict(sorted(input_style_counts.items())),
            "model_profile_counts": model_counts,
            "model_profile_coverage": model_coverage,
            "complexity_band_counts": dict(sorted(complexity_band_counts.items())),
            "evidence_format_counts": dict(sorted(evidence_format_counts.items())),
            "metamorphic_group_count": len(
                {
                    str(case.metamorphic_group or "").strip()
                    for case in holdout_cases
                    if str(case.metamorphic_group or "").strip()
                }
            ),
            "confidence_sample_minimum": profile_confidence_sample_minimum,
            "confidence_sample_issues": profile_confidence_issues,
        },
        "frozen_floors": dict(frozen_floors),
        "acceptance_thresholds": {
            name: frozen_floors.get(name)
            for name in sorted(_FROZEN_METRIC_FLOOR_KEYS)
        },
        "statistical_confidence": _mapping(
            frozen_floors.get("statistical_confidence")
        ),
        "profiles": dict(profiles),
        "required_release_slices": {
            dimension: list(values)
            for dimension, values in required_release_slices.items()
        },
    }


def assign_tracked_splits(
    cases: Sequence[GreenfieldMatrixCase],
    *,
    assignment: Mapping[str, Any],
    lineage: Any,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Assign connected declared-lineage groups to exactly one frozen split."""

    issues: list[str] = []
    if assignment.get("algorithm") != "declared-lineage-component-sha256-bucket-v2":
        issues.append("tracked split assignment algorithm is unsupported")
    seed = str(assignment.get("seed") or "").strip()
    if not is_sha256(seed):
        issues.append("tracked split assignment seed must be a SHA-256 value")
    bucket_rows = _mapping(assignment.get("buckets"))
    buckets, bucket_issues = _validated_buckets(bucket_rows)
    issues.extend(bucket_issues)
    declared_lineage, lineage_issues = _validated_case_lineage(
        cases=cases,
        value=lineage,
        label="tracked corpus",
    )
    issues.extend(lineage_issues)
    component_identities = _lineage_component_identities(
        cases=cases,
        lineage=declared_lineage,
    )
    assignments: dict[str, str] = {}
    seen_ids: set[str] = set()
    for case in cases:
        case_id = _case_id(case)
        if not case_id or case_id in seen_ids:
            issues.append(f"tracked corpus has duplicate or missing case ID `{case_id}`")
            continue
        seen_ids.add(case_id)
        component_identity = component_identities.get(case_id, "")
        if not component_identity:
            continue
        digest = hashlib.sha256(f"{seed}:{component_identity}".encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 10000
        split = next((name for name, lower, upper in buckets if lower <= bucket <= upper), "")
        if not split:
            issues.append(f"tracked split bucket {bucket} has no owner")
            continue
        assignments[case_id] = split
    return assignments, tuple(issues)


def validate_atomic_annotations(
    *,
    cases: Sequence[GreenfieldMatrixCase],
    rows: Any,
) -> tuple[dict[str, Mapping[str, Any]], tuple[str, ...]]:
    """Validate blinded truth as exact atomic and typed-relation expectations."""

    issues: list[str] = []
    if not _is_sequence(rows):
        return {}, ("final holdout annotations must be an array",)
    cases_by_id = {_case_id(case): case for case in cases}
    annotations: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, Mapping):
            issues.append(f"annotation {index} must be an object")
            continue
        case_id = str(raw.get("case_id") or "").strip()
        if not case_id or case_id in annotations:
            issues.append(f"annotation {index} has duplicate or missing case_id `{case_id}`")
            continue
        case = cases_by_id.get(case_id)
        if case is None:
            issues.append(f"annotation references unknown case_id `{case_id}`")
            continue
        annotations[case_id] = dict(raw)
        expected_keys = {
            "case_id",
            "split",
            "prompt_sha256",
            "expected_outcome",
            "expected_clarification",
            "complexity",
            "atoms",
            "relation_fidelity",
        }
        if set(raw) != expected_keys:
            issues.append(f"annotation `{case_id}` must use only the frozen structural fields")
        if raw.get("split") != "final_holdout":
            issues.append(f"annotation `{case_id}` must declare split `final_holdout`")
        expected_hash = hashlib.sha256(case.prompt.encode("utf-8")).hexdigest()
        if str(raw.get("prompt_sha256") or "") != expected_hash:
            issues.append(f"annotation `{case_id}` prompt_sha256 does not match its case")
        expected_outcome = str(raw.get("expected_outcome") or "").strip()
        if expected_outcome not in EXPECTED_OUTCOMES:
            issues.append(f"annotation `{case_id}` has invalid expected_outcome")
        case_outcome = "clarify" if str(case.expectation) == "clarification_required" else "commit"
        if expected_outcome != case_outcome:
            issues.append(f"annotation `{case_id}` expected_outcome does not match case expectation")
        _validate_expected_clarification(
            case_id=case_id,
            expected_outcome=expected_outcome,
            value=raw.get("expected_clarification"),
            issues=issues,
        )
        _validate_complexity(case=case, case_id=case_id, value=raw.get("complexity"), issues=issues)
        item_ids: set[str] = set()
        items = raw.get("atoms")
        if not _is_sequence(items):
            issues.append(f"annotation `{case_id}` atoms must be an array")
            continue
        atom_identities: set[str] = set()
        scored_count = 0
        for item_index, item in enumerate(items, start=1):
            _validate_atomic_item(
                case=case,
                case_id=case_id,
                index=item_index,
                item=item,
                item_ids=item_ids,
                issues=issues,
            )
            if not isinstance(item, Mapping):
                continue
            if item.get("evaluation_role") == "scored":
                scored_count += 1
            identity = _annotation_atom_identity(item)
            if identity in atom_identities:
                issues.append(f"annotation `{case_id}` has duplicate structural atom custody")
            atom_identities.add(identity)
        if expected_outcome == "commit" and scored_count == 0:
            issues.append(f"annotation `{case_id}` commit outcome has no scored atoms")
        if expected_outcome == "commit":
            relation_evidence = annotation_relation_evidence(
                case=case,
                value=raw.get("relation_fidelity"),
                atom_rows=items,
            )
            issues.extend(
                f"annotation `{case_id}` {issue}"
                for issue in relation_evidence.issues
            )
            if not any(relation_evidence.keys.values()):
                issues.append(
                    f"annotation `{case_id}` commit outcome has no scored relations"
                )
        elif raw.get("relation_fidelity") is not None:
            issues.append(
                f"annotation `{case_id}` clarify outcome must not declare relation_fidelity"
            )
    missing = sorted(set(cases_by_id) - set(annotations))
    if missing:
        issues.append("final holdout lacks annotations for: " + ", ".join(missing))
    return annotations, tuple(issues)


def cross_split_membership_issues(
    *,
    tracked_cases: Sequence[GreenfieldMatrixCase],
    tracked_assignments: Mapping[str, str],
    final_holdout_cases: Sequence[GreenfieldMatrixCase],
    tracked_lineage: Any,
    final_holdout_lineage: Any,
) -> tuple[str, ...]:
    """Reject exact source identities or declared lineage crossing frozen splits."""

    issues: list[str] = []
    normalized_tracked, tracked_issues = _validated_case_lineage(
        cases=tracked_cases,
        value=tracked_lineage,
        label="tracked corpus",
    )
    normalized_holdout, holdout_issues = _validated_case_lineage(
        cases=final_holdout_cases,
        value=final_holdout_lineage,
        label="final holdout",
    )
    issues.extend((*tracked_issues, *holdout_issues))
    identity_members: dict[str, list[tuple[str, str]]] = {}
    for case in tracked_cases:
        case_id = _case_id(case)
        split = str(tracked_assignments.get(case_id) or "")
        for identity in _case_split_identities(case, normalized_tracked.get(case_id, {})):
            identity_members.setdefault(identity, []).append((case_id, split))
    for case in final_holdout_cases:
        case_id = _case_id(case)
        for identity in _case_split_identities(case, normalized_holdout.get(case_id, {})):
            identity_members.setdefault(identity, []).append((case_id, "final_holdout"))
    crossing_pairs: set[tuple[str, str, str, str]] = set()
    for members in identity_members.values():
        for index, left in enumerate(members):
            for right in members[index + 1 :]:
                if not left[1] or not right[1] or left[1] == right[1]:
                    continue
                crossing_pairs.add((left[1], right[1], left[0], right[0]))
    issues.extend(
        "one declared lineage or exact source identity crosses "
        f"{left_split} and {right_split}: {left_case}, {right_case}"
        for left_split, right_split, left_case, right_case in sorted(crossing_pairs)
    )
    return tuple(dict.fromkeys(issues))


def _validate_atomic_item(
    *,
    case: GreenfieldMatrixCase,
    case_id: str,
    index: int,
    item: Any,
    item_ids: set[str],
    issues: list[str],
) -> None:
    label = f"annotation `{case_id}` atoms[{index}]"
    if not isinstance(item, Mapping):
        issues.append(f"{label} must be an object")
        return
    expected_keys = {
        "id",
        "category",
        "evaluation_role",
        "materiality",
        "expected_custody",
        "expected_polarity",
        "source",
        "projection_links",
    }
    if set(item) != expected_keys:
        issues.append(f"{label} must use only the frozen v4 atom fields")
    item_id = str(item.get("id") or "").strip()
    if not item_id or item_id in item_ids:
        issues.append(f"{label} has duplicate or missing id")
    else:
        item_ids.add(item_id)
    category = str(item.get("category") or "")
    if category not in ATOMIC_CATEGORIES:
        issues.append(f"{label} has invalid category")
    if str(item.get("evaluation_role") or "") not in EVALUATION_ROLES:
        issues.append(f"{label} has invalid evaluation_role")
    if str(item.get("materiality") or "") not in MATERIALITY_VALUES:
        issues.append(f"{label} has invalid materiality")
    if str(item.get("expected_custody") or "") not in CUSTODY_VALUES:
        issues.append(f"{label} has invalid expected_custody")
    if str(item.get("expected_polarity") or "") not in POLARITY_VALUES:
        issues.append(f"{label} has invalid expected_polarity")
    source = item.get("source")
    if not isinstance(source, Mapping) or set(source) != {
        "source_id",
        "start_byte",
        "end_byte",
        "quote_sha256",
    }:
        issues.append(f"{label} has invalid source custody")
        return
    if str(source.get("source_id") or "") != "operator_evidence":
        issues.append(f"{label} has unsupported source_id")
    start = _nonnegative_int(source.get("start_byte"))
    end = _nonnegative_int(source.get("end_byte"))
    evidence_bytes = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=str(case.confirmed_intent_markdown or ""),
    ).encode("utf-8")
    if start is None or end is None or end <= start or end > len(evidence_bytes):
        issues.append(f"{label} has invalid source byte offsets")
        return
    try:
        actual = evidence_bytes[start:end].decode("utf-8")
    except UnicodeDecodeError:
        issues.append(f"{label} source byte offsets split a UTF-8 sequence")
        return
    if str(source.get("quote_sha256") or "") != hashlib.sha256(actual.encode("utf-8")).hexdigest():
        issues.append(f"{label} quote_sha256 does not match its prompt byte span")
    links = item.get("projection_links")
    if not _is_sequence(links) or (
        item.get("evaluation_role") == "scored" and not links
    ):
        issues.append(f"{label} has invalid projection_links")
        return
    link_keys: list[tuple[Any, ...]] = []
    for link_index, link in enumerate(links, start=1):
        link_label = f"{label} projection_links[{link_index}]"
        if not isinstance(link, Mapping) or set(link) != {
            "field",
            "path",
            "value_sha256",
            "projection_start_byte",
            "projection_end_byte",
            "relation_order",
            "relation_role",
        }:
            issues.append(f"{link_label} is malformed")
            continue
        field = str(link.get("field") or "")
        path = str(link.get("path") or "")
        projection_start = _nonnegative_int(link.get("projection_start_byte"))
        projection_end = _nonnegative_int(link.get("projection_end_byte"))
        relation_order = _nonnegative_int(link.get("relation_order"))
        relation_role = link.get("relation_role")
        if (
            not field
            or not path.startswith(f"/{field}")
            or not is_sha256(str(link.get("value_sha256") or ""))
            or projection_start is None
            or projection_end is None
            or projection_end <= projection_start
            or relation_order is None
            or not isinstance(relation_role, str)
            or (relation_order == 0 and relation_role != "")
            or (relation_order > 0 and relation_role not in _RELATION_ROLES)
        ):
            issues.append(f"{link_label} has invalid structural fields")
        link_keys.append(tuple(link.get(key) for key in sorted(link)))
    if link_keys != sorted(set(link_keys)):
        issues.append(f"{label} projection_links must be unique and deterministic")


def _validate_complexity(
    *,
    case: GreenfieldMatrixCase,
    case_id: str,
    value: Any,
    issues: list[str],
) -> None:
    if not isinstance(value, Mapping):
        issues.append(f"annotation `{case_id}` complexity must be an object")
        return
    if set(value) != set(COMPLEXITY_DIMENSIONS):
        issues.append(f"annotation `{case_id}` complexity must use the exact operating-envelope dimensions")
    for dimension in COMPLEXITY_DIMENSIONS:
        if _nonnegative_int(value.get(dimension)) is None:
            issues.append(f"annotation `{case_id}` complexity `{dimension}` must be a non-negative integer")
    for dimension, expected in expected_case_source_complexity(case).items():
        if value.get(dimension) != expected:
            issues.append(
                f"annotation `{case_id}` complexity `{dimension}` does not match frozen source evidence"
            )


def _annotation_atom_identity(value: Mapping[str, Any]) -> str:
    return json.dumps(
        {
            "category": value.get("category"),
            "expected_custody": value.get("expected_custody"),
            "expected_polarity": value.get("expected_polarity"),
            "source": value.get("source"),
            "projection_links": value.get("projection_links"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _validate_expected_clarification(
    *,
    case_id: str,
    expected_outcome: str,
    value: Any,
    issues: list[str],
) -> None:
    if expected_outcome == "commit":
        if value is not None:
            issues.append(f"annotation `{case_id}` commit outcome must not declare expected_clarification")
        return
    if not isinstance(value, Mapping) or set(value) != {"field", "question"}:
        issues.append(f"annotation `{case_id}` clarify outcome has invalid expected_clarification")
        return
    field = str(value.get("field") or "")
    question = str(value.get("question") or "")
    for field_issue in material_question_field_issues((field,), source_texts=()):
        issues.append(f"annotation `{case_id}` {field_issue}")
    if not question or len(question) > 280 or not question.endswith("?") or question.count("?") != 1:
        issues.append(f"annotation `{case_id}` expected clarification question is invalid")


def profile_confidence_sample_issues(
    *,
    cases: Sequence[GreenfieldMatrixCase],
    annotations: Mapping[str, Mapping[str, Any]],
    minimum: int,
) -> list[str]:
    """Ensure every profile-level confidence denominator can reach its gate."""

    if minimum <= 0:
        return ["model-profile confidence has no positive sample minimum"]
    active_outcomes = {
        str(annotation.get("expected_outcome") or "")
        for annotation in annotations.values()
        if str(annotation.get("expected_outcome") or "") in EXPECTED_OUTCOMES
    }
    outcome_counts: dict[str, Counter[str]] = defaultdict(Counter)
    slice_counts: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    atomic_counts: Counter[str] = Counter()
    relation_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for case in cases:
        case_id = _case_id(case)
        annotation = annotations.get(case_id)
        if annotation is None:
            continue
        profile = case_model_profile(case)
        outcome = str(annotation.get("expected_outcome") or "")
        outcome_counts[profile][outcome] += 1
        provenance = getattr(case, "provenance", None)
        profile_slices = {
            "input_style": str(case.input_style or "unspecified"),
            "expectation": str(case.expectation or "transaction_committed"),
            "source_family": str(
                getattr(provenance, "source_family", "") or "unspecified"
            ),
            "complexity_band": greenfield_complexity_band(
                _mapping(annotation.get("complexity"))
            ),
            "evidence_format": expected_case_evidence_format(case),
            "model_profile": profile,
        }
        for dimension, value in profile_slices.items():
            slice_counts[profile][(dimension, value)] += 1
        if outcome != "commit":
            continue
        atoms = annotation.get("atoms")
        atom_rows = (
            tuple(item for item in atoms if isinstance(item, Mapping))
            if _is_sequence(atoms)
            else ()
        )
        atomic_counts[profile] += sum(
            1 for item in atom_rows if item.get("evaluation_role") == "scored"
        )
        relations = annotation_relation_evidence(
            case=case,
            value=annotation.get("relation_fidelity"),
            atom_rows=atom_rows,
        )
        for family in RELATION_FAMILIES:
            relation_counts[profile][family] += max(
                len(relations.keys.get(family, ())),
                int(relations.minimum_samples.get(family, 0)),
            )

    issues: list[str] = []
    for profile in MODEL_PROFILES:
        total = sum(outcome_counts[profile].values())
        if total < minimum:
            issues.append(
                f"model profile `{profile}` has {total} total observation(s); "
                f"confidence requires at least {minimum}"
            )
        for outcome in sorted(active_outcomes):
            observed = int(outcome_counts[profile][outcome])
            if observed < minimum:
                issues.append(
                    f"model profile `{profile}` has {observed} `{outcome}` observation(s); "
                    f"confidence requires at least {minimum}"
                )
        observed_atoms = int(atomic_counts[profile])
        if "commit" in active_outcomes and observed_atoms < minimum:
            issues.append(
                f"model profile `{profile}` has {observed_atoms} scored atomic observation(s); "
                f"confidence requires at least {minimum}"
            )
        for (dimension, value), observed in sorted(slice_counts[profile].items()):
            if observed < minimum:
                issues.append(
                    f"model profile `{profile}` has {observed} sample(s) for "
                    f"{dimension} `{value}`; confidence requires at least {minimum}"
                )
        for family, observed in sorted(relation_counts[profile].items()):
            if observed and observed < minimum:
                issues.append(
                    f"model profile `{profile}` has {observed} `{family}` relation sample(s); "
                    f"confidence requires at least {minimum}"
                )
    return issues


def _frozen_floor_issues(value: Mapping[str, Any]) -> tuple[str, ...]:
    expected_keys = {"version", *_FROZEN_FLOOR_KEYS}
    if set(value) != expected_keys:
        return ("frozen_floors must use only the v4 acceptance and confidence fields",)
    issues: list[str] = []
    if value.get("version") != STRUCTURAL_FLOORS_VERSION:
        issues.append(f"frozen_floors must declare {STRUCTURAL_FLOORS_VERSION}")
    for name in sorted(_FROZEN_METRIC_FLOOR_KEYS):
        threshold = value.get(name)
        if (
            not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not 0.0 <= float(threshold) <= 1.0
        ):
            issues.append(f"frozen_floors `{name}` must be a number from 0 through 1")
        elif float(threshold) != _FROZEN_ACCEPTANCE_THRESHOLDS[name]:
            issues.append(
                f"frozen_floors `{name}` must preserve the exact "
                f"{_FROZEN_ACCEPTANCE_THRESHOLDS[name]:.1f} acceptance threshold"
            )
    minimum_samples = value.get("release_slice_minimum_samples")
    issues.extend(
        release_slice_minimum_sample_contract_issues(
            minimum_samples
        )
    )
    confidence = value.get("statistical_confidence")
    issues.extend(
        release_statistical_confidence_contract_issues(
            confidence,
            minimum_samples=minimum_samples if isinstance(minimum_samples, Mapping) else None,
        )
    )
    if isinstance(confidence, Mapping) and dict(confidence) != release_statistical_confidence_contract():
        issues.append("statistical confidence must match the published release contract")
    return tuple(issues)


def _validated_buckets(value: Mapping[str, Any]) -> tuple[list[tuple[str, int, int]], tuple[str, ...]]:
    issues: list[str] = []
    buckets: list[tuple[str, int, int]] = []
    for name in ("development", "regression", "private_validation"):
        bounds = value.get(name)
        if not _is_sequence(bounds) or len(bounds) != 2:
            issues.append(f"tracked split `{name}` must define two bucket bounds")
            continue
        lower = _nonnegative_int(bounds[0])
        upper = _nonnegative_int(bounds[1])
        if lower is None or upper is None or upper < lower or upper > 9999:
            issues.append(f"tracked split `{name}` has invalid bucket bounds")
            continue
        buckets.append((name, lower, upper))
    owners = [0] * 10000
    for _name, lower, upper in buckets:
        for bucket in range(lower, upper + 1):
            owners[bucket] += 1
    if any(owner != 1 for owner in owners):
        issues.append("tracked split buckets must cover 0..9999 exactly once")
    return buckets, tuple(issues)


def _validated_case_lineage(
    *,
    cases: Sequence[GreenfieldMatrixCase],
    value: Any,
    label: str,
) -> tuple[dict[str, dict[str, str]], tuple[str, ...]]:
    case_ids = {_case_id(case) for case in cases if _case_id(case)}
    if not isinstance(value, Mapping):
        if not case_ids:
            return {}, ()
        return {}, (f"{label} must declare semantic/template lineage for every case",)
    declared_ids = {str(case_id or "").strip() for case_id in value}
    issues: list[str] = []
    missing = sorted(case_ids - declared_ids)
    unknown = sorted(declared_ids - case_ids)
    if missing:
        issues.append(f"{label} lineage is missing cases: " + ", ".join(missing))
    if unknown:
        issues.append(f"{label} lineage references unknown cases: " + ", ".join(unknown))
    normalized: dict[str, dict[str, str]] = {}
    for case_id in sorted(case_ids & declared_ids):
        row = value.get(case_id)
        if not isinstance(row, Mapping) or set(row) != _LINEAGE_KEYS:
            issues.append(
                f"{label} lineage `{case_id}` must declare only semantic_family and template_family"
            )
            continue
        semantic_family = str(row.get("semantic_family") or "").strip()
        template_family = str(row.get("template_family") or "").strip()
        if not semantic_family or not template_family:
            issues.append(f"{label} lineage `{case_id}` has an empty family identity")
            continue
        normalized[case_id] = {
            "semantic_family": semantic_family,
            "template_family": template_family,
        }
    return normalized, tuple(issues)


def _lineage_component_identities(
    *,
    cases: Sequence[GreenfieldMatrixCase],
    lineage: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
    case_by_id = {_case_id(case): case for case in cases if _case_id(case)}
    parent = {case_id: case_id for case_id in case_by_id}

    def root(case_id: str) -> str:
        while parent[case_id] != case_id:
            parent[case_id] = parent[parent[case_id]]
            case_id = parent[case_id]
        return case_id

    def union(left: str, right: str) -> None:
        left_root = root(left)
        right_root = root(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    identity_owner: dict[str, str] = {}
    identities_by_case: dict[str, tuple[str, ...]] = {}
    for case_id, case in case_by_id.items():
        identities = _case_split_identities(case, lineage.get(case_id, {}))
        identities_by_case[case_id] = identities
        for identity in identities:
            prior_owner = identity_owner.setdefault(identity, case_id)
            union(case_id, prior_owner)
    component_identities: dict[str, set[str]] = {}
    for case_id, identities in identities_by_case.items():
        component_identities.setdefault(root(case_id), set()).update(identities)
    return {
        case_id: json.dumps(
            sorted(component_identities.get(root(case_id), ())),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for case_id in case_by_id
        if case_id in lineage
    }


def _case_split_identities(
    case: GreenfieldMatrixCase,
    lineage: Mapping[str, str],
) -> tuple[str, ...]:
    identities = {
        f"semantic_family:{str(lineage.get('semantic_family') or '').strip()}",
        f"template_family:{str(lineage.get('template_family') or '').strip()}",
        "prompt_sha256:" + hashlib.sha256(case.prompt.encode("utf-8")).hexdigest(),
    }
    metamorphic = str(case.metamorphic_group or "").strip()
    if metamorphic:
        identities.add(f"metamorphic_group:{metamorphic}")
    provenance = getattr(case, "provenance", None)
    source_hash = str(getattr(provenance, "source_artifact_sha256", "") or "").strip()
    if source_hash:
        identities.add(f"source_artifact_sha256:{source_hash}")
    return tuple(sorted(identity for identity in identities if not identity.endswith(":")))


def _require_file_hash(path: Path, *, expected: Any, issues: list[str], label: str) -> None:
    digest = str(expected or "").strip()
    if not is_sha256(digest):
        issues.append(f"{label} manifest reference is not SHA-256 bound")
        return
    if not path.is_file():
        issues.append(f"{label} file is unavailable")
        return
    if sha256_file(path) != digest:
        issues.append(f"{label} SHA-256 does not match the frozen manifest")


def _repo_path(root: Path, value: Any, *, issues: list[str], label: str) -> Path | None:
    token = str(value or "").strip()
    if not token:
        issues.append(f"{label} path is missing")
        return None
    path = (root / token).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        issues.append(f"{label} path escapes the repository")
        return None
    return path


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"unable to read {label}: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{label} is not valid JSON: {error}") from error
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def _outcome_counts(cases: Sequence[GreenfieldMatrixCase]) -> dict[str, int]:
    return dict(sorted(Counter(str(case.expectation) for case in cases).items()))


def _case_id(case: GreenfieldMatrixCase) -> str:
    return str(case.case_id or case.slug).strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _positive_int(value: Any) -> int:
    number = _nonnegative_int(value)
    return number if number is not None and number > 0 else 0


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _string_sequence(value: Any) -> tuple[str, ...]:
    if not _is_sequence(value):
        return ()
    return tuple(str(item or "").strip() for item in value if str(item or "").strip())


__all__ = [
    "ATOMIC_CATEGORIES",
    "EVALUATION_SPLIT_VERSION",
    "FINAL_HOLDOUT_VERSION",
    "POLARITY_VALUES",
    "STRUCTURAL_FLOORS_VERSION",
    "assign_tracked_splits",
    "cross_split_membership_issues",
    "evaluate_frozen_evaluation_contract",
    "profile_confidence_sample_issues",
    "validate_atomic_annotations",
]
