"""Frozen split, holdout, and atomic-annotation contracts for Greenfield release proof."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_matrix_release_artifacts import sha256_file
from greenfield_matrix_input_axes import RELEASE_INPUT_STYLES
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


EVALUATION_SPLIT_VERSION = "odylith.greenfield.evaluation-splits.v1"
FINAL_HOLDOUT_VERSION = "odylith.greenfield.final-holdout.v1"
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
    "material_questions",
)
MATERIALITY_VALUES = frozenset({"material", "non_material"})
CUSTODY_VALUES = frozenset({"accepted_fact", "bounded_interpretation", "assumption", "ambiguity"})
POLARITY_VALUES = frozenset({"affirmative", "prohibited"})
EXPECTED_OUTCOMES = frozenset({"commit", "clarify"})
COMPLEXITY_DIMENSIONS = (
    "evidence_bytes",
    "documents",
    "actors",
    "state_objects",
    "paths",
    "external_systems",
    "contradictions",
    "ambiguities",
    "safety_boundaries",
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_POLARITY_TOKENS = frozenset(
    {
        "avoid",
        "cannot",
        "exclude",
        "excluded",
        "excluding",
        "forbid",
        "forbidden",
        "never",
        "no",
        "not",
        "prohibit",
        "prohibited",
        "without",
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
    declared_styles = _string_sequence(profiles.get("evidence_styles"))
    unknown_styles = sorted(set(declared_styles) - set(RELEASE_INPUT_STYLES))
    if unknown_styles:
        issues.append("evaluation profiles declare unsupported evidence styles: " + ", ".join(unknown_styles))
    input_style_counts = Counter(str(case.input_style) for case in holdout_cases)
    missing_styles = [style for style in declared_styles if input_style_counts.get(style, 0) == 0]
    if missing_styles:
        issues.append("final holdout has no cases for declared evidence styles: " + ", ".join(missing_styles))
    issues.extend(
        cross_split_leakage_issues(
            tracked_cases=tracked_cases,
            tracked_assignments=assignments,
            final_holdout_cases=holdout_cases,
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
            "metamorphic_group_count": len(
                {
                    str(case.metamorphic_group or "").strip()
                    for case in holdout_cases
                    if str(case.metamorphic_group or "").strip()
                }
            ),
        },
        "frozen_floors": dict(_mapping(manifest.get("frozen_floors"))),
        "profiles": dict(profiles),
    }


def assign_tracked_splits(
    cases: Sequence[GreenfieldMatrixCase],
    *,
    assignment: Mapping[str, Any],
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Assign identity groups so equivalent or same-source cases cannot cross splits."""

    issues: list[str] = []
    if assignment.get("algorithm") != "metamorphic-or-source-group-sha256-bucket-v1":
        issues.append("tracked split assignment algorithm is unsupported")
    seed = str(assignment.get("seed") or "").strip()
    if not is_sha256(seed):
        issues.append("tracked split assignment seed must be a SHA-256 value")
    bucket_rows = _mapping(assignment.get("buckets"))
    buckets, bucket_issues = _validated_buckets(bucket_rows)
    issues.extend(bucket_issues)
    assignments: dict[str, str] = {}
    seen_ids: set[str] = set()
    for case in cases:
        case_id = _case_id(case)
        if not case_id or case_id in seen_ids:
            issues.append(f"tracked corpus has duplicate or missing case ID `{case_id}`")
            continue
        seen_ids.add(case_id)
        digest = hashlib.sha256(f"{seed}:{_group_identity(case)}".encode("utf-8")).hexdigest()
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
    """Validate blinded semantic truth as source-bound atomic claims."""

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
        expected_hash = hashlib.sha256(case.prompt.encode("utf-8")).hexdigest()
        if str(raw.get("prompt_sha256") or "") != expected_hash:
            issues.append(f"annotation `{case_id}` prompt_sha256 does not match its case")
        expected_outcome = str(raw.get("expected_outcome") or "").strip()
        if expected_outcome not in EXPECTED_OUTCOMES:
            issues.append(f"annotation `{case_id}` has invalid expected_outcome")
        case_outcome = "clarify" if str(case.expectation) == "clarification_required" else "commit"
        if expected_outcome != case_outcome:
            issues.append(f"annotation `{case_id}` expected_outcome does not match case expectation")
        _validate_complexity(case_id, raw.get("complexity"), issues)
        item_ids: set[str] = set()
        for category in ATOMIC_CATEGORIES:
            items = raw.get(category)
            if not _is_sequence(items):
                issues.append(f"annotation `{case_id}` category `{category}` must be an array")
                continue
            for item_index, item in enumerate(items, start=1):
                _validate_atomic_item(
                    case=case,
                    case_id=case_id,
                    category=category,
                    index=item_index,
                    item=item,
                    item_ids=item_ids,
                    issues=issues,
                )
    missing = sorted(set(cases_by_id) - set(annotations))
    if missing:
        issues.append("final holdout lacks annotations for: " + ", ".join(missing))
    return annotations, tuple(issues)


def cross_split_leakage_issues(
    *,
    tracked_cases: Sequence[GreenfieldMatrixCase],
    tracked_assignments: Mapping[str, str],
    final_holdout_cases: Sequence[GreenfieldMatrixCase],
    threshold: float = 0.85,
) -> tuple[str, ...]:
    """Reject exact or near-duplicate prompts crossing any frozen split."""

    issues: list[str] = []
    rows: list[tuple[str, str, str, frozenset[str]]] = []
    for case in tracked_cases:
        case_id = _case_id(case)
        rows.append(
            (
                case_id,
                str(tracked_assignments.get(case_id) or ""),
                _canonical(case.prompt),
                _tokens(case.prompt),
            )
        )
    for case in final_holdout_cases:
        rows.append((_case_id(case), "final_holdout", _canonical(case.prompt), _tokens(case.prompt)))
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            if not left[1] or not right[1] or left[1] == right[1]:
                continue
            if left[2] == right[2]:
                issues.append(f"exact prompt leakage crosses {left[1]} and {right[1]}: {left[0]}, {right[0]}")
                continue
            similarity = _jaccard(left[3], right[3])
            if similarity >= threshold:
                issues.append(
                    f"near-duplicate prompt leakage ({similarity:.3f}) crosses "
                    f"{left[1]} and {right[1]}: {left[0]}, {right[0]}"
                )
    return tuple(issues)


def _validate_atomic_item(
    *,
    case: GreenfieldMatrixCase,
    case_id: str,
    category: str,
    index: int,
    item: Any,
    item_ids: set[str],
    issues: list[str],
) -> None:
    label = f"annotation `{case_id}` {category}[{index}]"
    if not isinstance(item, Mapping):
        issues.append(f"{label} must be an object")
        return
    item_id = str(item.get("id") or "").strip()
    value = str(item.get("value") or "").strip()
    quote = str(item.get("source_quote") or "")
    if not item_id or item_id in item_ids:
        issues.append(f"{label} has duplicate or missing id")
    else:
        item_ids.add(item_id)
    if not value:
        issues.append(f"{label} has no value")
    if str(item.get("materiality") or "") not in MATERIALITY_VALUES:
        issues.append(f"{label} has invalid materiality")
    if str(item.get("expected_custody") or "") not in CUSTODY_VALUES:
        issues.append(f"{label} has invalid expected_custody")
    start = _nonnegative_int(item.get("source_start"))
    end = _nonnegative_int(item.get("source_end"))
    prompt_bytes = case.prompt.encode("utf-8")
    if start is None or end is None or end <= start or end > len(prompt_bytes):
        issues.append(f"{label} has invalid source byte offsets")
        return
    try:
        actual = prompt_bytes[start:end].decode("utf-8")
    except UnicodeDecodeError:
        issues.append(f"{label} source byte offsets split a UTF-8 sequence")
        return
    if actual != quote:
        issues.append(f"{label} source_quote does not match its prompt byte span")
        return
    normalized_value = _canonical(value)
    normalized_quote = _canonical(quote)
    expected_custody = str(item.get("expected_custody") or "").strip()
    if expected_custody == "accepted_fact" and (
        not normalized_value or normalized_value not in normalized_quote
    ):
        issues.append(f"{label} value is not directly entailed by its source_quote")
    if expected_custody == "accepted_fact" and category in {"constraints", "non_goals"}:
        expected_polarity = str(item.get("expected_polarity") or "").strip()
        if expected_polarity not in POLARITY_VALUES:
            issues.append(f"{label} has invalid expected_polarity")
            return
        source_context = _source_clause(prompt_bytes, start=start, end=end)
        source_polarity = _polarity_tokens(f"{source_context} {quote}")
        claim_polarity = _polarity_tokens(value)
        if expected_polarity == "prohibited" and not source_polarity:
            issues.append(f"{label} declares prohibited polarity without source support")
        if expected_polarity == "prohibited" and not claim_polarity:
            issues.append(f"{label} drops governing prohibition polarity from its source clause")
    declared_category = str(item.get("category") or "").strip()
    if declared_category and declared_category != category:
        issues.append(f"{label} declares the wrong category `{declared_category}`")


def _validate_complexity(case_id: str, value: Any, issues: list[str]) -> None:
    if not isinstance(value, Mapping):
        issues.append(f"annotation `{case_id}` complexity must be an object")
        return
    for dimension in COMPLEXITY_DIMENSIONS:
        if _nonnegative_int(value.get(dimension)) is None:
            issues.append(f"annotation `{case_id}` complexity `{dimension}` must be a non-negative integer")


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


def _group_identity(case: GreenfieldMatrixCase) -> str:
    metamorphic = str(case.metamorphic_group or "").strip()
    if metamorphic:
        return f"metamorphic:{metamorphic}"
    provenance = getattr(case, "provenance", None)
    source_hash = str(getattr(provenance, "source_artifact_sha256", "") or "").strip()
    if source_hash:
        return f"source:{source_hash}"
    return "prompt:" + hashlib.sha256(case.prompt.encode("utf-8")).hexdigest()


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


def _tokens(value: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(str(value or "").casefold()))


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _canonical(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(str(value or "").casefold()))


def _polarity_tokens(value: str) -> frozenset[str]:
    return _tokens(value) & _POLARITY_TOKENS


def _source_clause(prompt: bytes, *, start: int, end: int) -> str:
    single_boundaries = tuple(bytes((marker,)) for marker in b".!?\n,;")
    phrase_boundaries = (b" but ", b" except ", b" however ")
    boundaries = (*single_boundaries, *phrase_boundaries)
    left_boundary = max((prompt.rfind(marker, 0, start) for marker in boundaries), default=-1)
    left = left_boundary + 1
    if left_boundary >= 0:
        matched = next((marker for marker in boundaries if prompt.startswith(marker, left_boundary)), b"")
        left = left_boundary + len(matched)
    right_candidates = [position for marker in boundaries if (position := prompt.find(marker, end)) >= 0]
    right = min(right_candidates, default=len(prompt))
    return prompt[left:right].decode("utf-8", errors="strict")


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
    "assign_tracked_splits",
    "cross_split_leakage_issues",
    "evaluate_frozen_evaluation_contract",
    "validate_atomic_annotations",
]
