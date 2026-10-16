"""Validate independent semantic review of frozen Greenfield holdout truth."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
import hashlib
from typing import Any


ANNOTATION_REVIEW_VERSION = "odylith.greenfield.final-holdout-annotation-review.v1"
ANNOTATION_REVIEW_CLAIM_CLASS = "blinded-independent-annotation-review"
MINIMUM_REVIEW_CONTEXTS = 5
MAXIMUM_CASES_PER_REVIEW_CONTEXT = 8
_REVIEW_FIELDS = {
    "case_id",
    "prompt_sha256",
    "expected_outcome",
    "expected_clarification",
    "review_context_label",
    "review_method",
    "reviewed_on",
    "review_status",
    "outcome_basis_assessment",
    "rationale",
}


def validate_holdout_annotation_review(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    value: Any,
) -> tuple[dict[str, Mapping[str, Any]], tuple[str, ...]]:
    """Require an explicit source-sufficiency verdict for every frozen outcome."""

    if not isinstance(value, Mapping):
        return {}, ("final holdout annotation_review must be an object",)
    issues: list[str] = []
    if set(value) != {"version", "claim_class", "reviews"}:
        issues.append("final holdout annotation_review must use only the frozen review fields")
    if value.get("version") != ANNOTATION_REVIEW_VERSION:
        issues.append(f"final holdout annotation_review must declare {ANNOTATION_REVIEW_VERSION}")
    if value.get("claim_class") != ANNOTATION_REVIEW_CLAIM_CLASS:
        issues.append(
            "final holdout annotation_review must declare the blinded independent "
            "review claim class"
        )
    rows = value.get("reviews")
    if not _is_sequence(rows):
        return {}, tuple((*issues, "final holdout annotation_review reviews must be an array"))

    cases_by_id = {_case_id(case): case for case in cases if _case_id(case)}
    reviews: dict[str, Mapping[str, Any]] = {}
    context_counts: Counter[str] = Counter()
    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, Mapping):
            issues.append(f"annotation review {index} must be an object")
            continue
        case_id = str(raw.get("case_id") or "").strip()
        if not case_id or case_id in reviews:
            issues.append(f"annotation review {index} has duplicate or missing case_id `{case_id}`")
            continue
        case = cases_by_id.get(case_id)
        annotation = annotations.get(case_id)
        if case is None or annotation is None:
            issues.append(f"annotation review references unknown case_id `{case_id}`")
            continue
        reviews[case_id] = dict(raw)
        if set(raw) != _REVIEW_FIELDS:
            issues.append(
                f"annotation review `{case_id}` must use only the frozen semantic review fields"
            )
        expected_prompt_hash = hashlib.sha256(
            str(getattr(case, "prompt", "") or "").encode("utf-8")
        ).hexdigest()
        if str(raw.get("prompt_sha256") or "") != expected_prompt_hash:
            issues.append(f"annotation review `{case_id}` prompt_sha256 does not match its case")
        expected_outcome = str(annotation.get("expected_outcome") or "").strip()
        if raw.get("expected_outcome") != expected_outcome:
            issues.append(
                f"annotation review `{case_id}` expected_outcome does not match its annotation"
            )
        if raw.get("expected_clarification") != annotation.get("expected_clarification"):
            issues.append(
                f"annotation review `{case_id}` expected_clarification does not match its annotation"
            )
        context = _single_line(raw.get("review_context_label"))
        if not context:
            issues.append(f"annotation review `{case_id}` must name a review_context_label")
        else:
            context_counts[context] += 1
            derivation_author = _single_line(
                getattr(getattr(case, "provenance", None), "derivation_author", "")
            )
            if derivation_author and context == derivation_author:
                issues.append(
                    f"annotation review `{case_id}` context must differ from its derivation author"
                )
        review_method = _single_line(raw.get("review_method"))
        if not review_method:
            issues.append(f"annotation review `{case_id}` must name a review_method")
        else:
            derivation_method = _single_line(
                getattr(getattr(case, "provenance", None), "derivation_method", "")
            )
            if derivation_method and review_method == derivation_method:
                issues.append(
                    f"annotation review `{case_id}` method must differ from its derivation method"
                )
        if not _is_iso_date(raw.get("reviewed_on")):
            issues.append(f"annotation review `{case_id}` must use an ISO reviewed_on date")
        if raw.get("review_status") != "approved":
            issues.append(f"annotation review `{case_id}` is not approved")
        required_assessment = (
            "source_supports_commit"
            if expected_outcome == "commit"
            else "material_clarification_required"
        )
        if raw.get("outcome_basis_assessment") != required_assessment:
            issues.append(
                f"annotation review `{case_id}` must declare outcome_basis_assessment "
                f"`{required_assessment}`"
            )
        if not _single_line(raw.get("rationale")):
            issues.append(f"annotation review `{case_id}` must include a rationale")

    missing = sorted(set(cases_by_id) - set(reviews))
    if missing:
        issues.append("final holdout lacks annotation reviews for: " + ", ".join(missing))
    required_contexts = min(MINIMUM_REVIEW_CONTEXTS, len(cases_by_id))
    if len(context_counts) < required_contexts:
        issues.append(
            "final holdout annotation review requires at least "
            f"{required_contexts} distinct review contexts; received {len(context_counts)}"
        )
    overloaded = sorted(
        context
        for context, count in context_counts.items()
        if count > MAXIMUM_CASES_PER_REVIEW_CONTEXT
    )
    if overloaded:
        issues.append(
            "final holdout annotation review caps cases per review context at "
            f"{MAXIMUM_CASES_PER_REVIEW_CONTEXT}: " + ", ".join(overloaded)
        )
    return reviews, tuple(issues)


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or "").strip()


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _is_iso_date(value: Any) -> bool:
    try:
        date.fromisoformat(_single_line(value))
    except ValueError:
        return False
    return True


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


__all__ = [
    "ANNOTATION_REVIEW_CLAIM_CLASS",
    "ANNOTATION_REVIEW_VERSION",
    "MAXIMUM_CASES_PER_REVIEW_CONTEXT",
    "MINIMUM_REVIEW_CONTEXTS",
    "validate_holdout_annotation_review",
]
