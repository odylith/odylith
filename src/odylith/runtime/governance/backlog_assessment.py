"""Shared assessment policy for Radar source, authoring, and projections."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

UNASSESSED = "unassessed"
GREENFIELD_PROVENANCE = "greenfield_provisional_design"
NUMERIC_FIELDS = ("commercial_value", "product_impact", "market_value", "ordering_score")
LABEL_FIELDS = ("priority", "sizing", "complexity", "confidence")
UNASSESSED_BACKLOG_METADATA = MappingProxyType({
    "assessment_status": UNASSESSED,
    "assessment_provenance": GREENFIELD_PROVENANCE,
    **dict.fromkeys(LABEL_FIELDS, UNASSESSED),
    **dict.fromkeys(NUMERIC_FIELDS),
})
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_SIZING = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}
VALID_COMPLEXITY = {"Low": 1, "Medium": 2, "High": 3, "VeryHigh": 5}


def is_unassessed(metadata: Mapping[str, Any]) -> bool:
    return metadata.get("assessment_status") == UNASSESSED


def numeric_value(value: Any) -> int | None:
    """Decode an explicit unknown without inventing a numeric assessment."""
    if value is None or value in ("", UNASSESSED):
        return None
    return int(value)


def typed_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(metadata)
    if is_unassessed(metadata):
        for field in NUMERIC_FIELDS:
            payload[field] = numeric_value(metadata.get(field))
    return payload


def markdown_value(value: Any) -> str:
    return UNASSESSED if value is None else str(value).strip()


def score_sort_key(value: Any) -> tuple[bool, int]:
    score = numeric_value(value)
    return (score is None, -score if score is not None else 0)


def unassessed_errors(metadata: Mapping[str, Any], *, path: Path) -> list[str]:
    errors = []
    for field, expected in UNASSESSED_BACKLOG_METADATA.items():
        actual = metadata.get(field)
        valid = (field in metadata and actual in (None, UNASSESSED)) if expected is None else actual == expected
        if not valid:
            errors.append(f"{path}: unassessed record requires `{field}` = `{markdown_value(expected)}`")
    if str(metadata.get("founder_override", "no")).strip().lower() != "no":
        errors.append(f"{path}: unassessed record cannot declare `founder_override`")
    return errors


def validate_assessment(metadata: Mapping[str, Any], *, errors: list[str], path: Path) -> None:
    if is_unassessed(metadata):
        errors.extend(unassessed_errors(metadata, path=path))
        return
    status = metadata.get("assessment_status", "")
    if status not in ("", "assessed"):
        errors.append(f"{path}: invalid `assessment_status` `{status}`")
    if metadata.get("assessment_provenance") == GREENFIELD_PROVENANCE:
        errors.append(f"{path}: provisional Greenfield assessment must remain unassessed")
    priority = str(metadata.get("priority", "")).strip()
    if priority and priority not in VALID_PRIORITIES:
        errors.append(f"{path}: invalid `priority` `{priority}`")
    confidence = str(metadata.get("confidence", "")).strip().lower()
    if confidence and confidence not in {"low", "medium", "high"}:
        errors.append(f"{path}: invalid `confidence` `{confidence}`")
    declared_score = parse_int_in_range(
        value=metadata.get("ordering_score", ""), field="ordering_score",
        low=0, high=100, errors=errors, path=path,
    )
    computed_score = compute_score(metadata, errors=errors, path=path)
    if (
        declared_score is not None and computed_score is not None
        and declared_score != computed_score
        and str(metadata.get("founder_override", "no")).lower() != "yes"
    ):
        errors.append(f"{path}: `ordering_score` ({declared_score}) does not match formula ({computed_score})")


def author_assessment(args: Any) -> dict[str, str]:
    payload = {field: getattr(args, field, "") for field in (*LABEL_FIELDS, *NUMERIC_FIELDS)}
    for field in ("assessment_status", "assessment_provenance"):
        if getattr(args, field, ""):
            payload[field] = getattr(args, field)
    payload["founder_override"] = "yes" if bool(args.founder_override) else "no"
    if is_unassessed(payload):
        errors = unassessed_errors(payload, path=Path("<generated>"))
    else:
        errors = []
        computed = compute_score(payload, errors=errors, path=Path("<generated>"))
        if not errors:
            declared = numeric_value(payload["ordering_score"])
            if declared is None:
                declared = computed
            if declared != computed and not args.founder_override:
                errors.append(
                    f"ordering_score override `{declared}` requires --founder-override "
                    f"because the computed score is `{computed}`"
                )
            payload["ordering_score"] = declared
            validate_assessment(payload, errors=errors, path=Path("<generated>"))
    if errors:
        raise ValueError("; ".join(errors))
    return {field: markdown_value(value) for field, value in payload.items()}


def index_score(value: str, *, metadata: Mapping[str, Any], errors: list[str], path: Path, idea_id: str) -> int | None:
    if is_unassessed(metadata):
        errors.extend(unassessed_errors(metadata, path=path))
        if value != UNASSESSED:
            errors.append(f"{path}: unassessed index score for `{idea_id}` must be `{UNASSESSED}`")
        return None
    return parse_int_in_range(value=value, field=f"ordering_score ({idea_id})", low=0, high=100, errors=errors, path=path)


def parse_int_in_range(
    *,
    value: Any,
    field: str,
    low: int,
    high: int,
    errors: list[str],
    path: Path,
) -> int | None:
    token = "" if value is None else str(value).strip()
    if not token:
        errors.append(f"{path}: missing `{field}`")
        return None
    try:
        parsed = int(token)
    except ValueError:
        errors.append(f"{path}: `{field}` must be an integer, got `{token}`")
        return None
    if parsed < low or parsed > high:
        errors.append(f"{path}: `{field}` out of range [{low}, {high}], got `{parsed}`")
        return None
    return parsed


def compute_score(metadata: Mapping[str, Any], *, errors: list[str], path: Path) -> int | None:
    if is_unassessed(metadata):
        errors.extend(unassessed_errors(metadata, path=path))
        return None
    commercial = parse_int_in_range(
        value=metadata.get("commercial_value", ""),
        field="commercial_value",
        low=1,
        high=5,
        errors=errors,
        path=path,
    )
    product = parse_int_in_range(
        value=metadata.get("product_impact", ""),
        field="product_impact",
        low=1,
        high=5,
        errors=errors,
        path=path,
    )
    market = parse_int_in_range(
        value=metadata.get("market_value", ""),
        field="market_value",
        low=1,
        high=5,
        errors=errors,
        path=path,
    )
    sizing = str(metadata.get("sizing", "")).strip()
    complexity = str(metadata.get("complexity", "")).strip()
    if sizing not in VALID_SIZING:
        errors.append(f"{path}: `sizing` must be one of {sorted(VALID_SIZING)}, got `{sizing}`")
        return None
    if complexity not in VALID_COMPLEXITY:
        errors.append(
            f"{path}: `complexity` must be one of {sorted(VALID_COMPLEXITY)}, got `{complexity}`"
        )
        return None
    if commercial is None or product is None or market is None:
        return None

    opportunity = (0.40 * commercial) + (0.35 * product) + (0.25 * market)
    execution_drag = (0.60 * VALID_SIZING[sizing]) + (0.40 * VALID_COMPLEXITY[complexity])
    raw_score = (opportunity / execution_drag) * 100
    rounded = int(raw_score + 0.5)
    return max(0, min(100, rounded))
