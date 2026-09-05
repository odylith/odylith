"""Keep provisional decision copy in the canonical assumption namespace."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
    MAX_AUTHORED_LIST_ITEMS,
)

DECISION_FIELDS = ("problem", "customer", "opportunity", "product_view")
ASSUMPTION_SCHEMA = {
    "type": "array",
    "maxItems": MAX_AUTHORED_LIST_ITEMS,
    "items": {
        "type": "object",
        "description": (
            "One useful provisional product decision for the consumer, not a note "
            "about quote extraction, actor classification, or authoring mechanics."
        ),
        "additionalProperties": False,
        "required": ["applies_to", "statement"],
        "properties": {
            "applies_to": {"type": "string", "enum": ["general", *DECISION_FIELDS]},
            "statement": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
            },
        },
    },
}


def assumption_rows(value: Any) -> list[dict[str, str]]:
    """Validate typed assumptions without promoting statements to source facts."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("Greenfield assumptions must be typed decision rows")
    if len(value) > MAX_AUTHORED_LIST_ITEMS:
        raise ValueError("Greenfield assumptions exceed the declared item limit")
    rows: list[dict[str, str]] = []
    targets: set[str] = set()
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {"applies_to", "statement"}:
            raise ValueError("Greenfield assumptions must be typed decision rows")
        target, statement = row["applies_to"], row["statement"]
        if (
            target not in ("general", *DECISION_FIELDS)
            or not isinstance(statement, str)
            or not statement.strip()
            or len(statement) > MAX_AUTHORED_FIELD_VALUE_CHARS
        ):
            raise ValueError("Greenfield assumption has an invalid target or statement")
        if target != "general" and target in targets:
            raise ValueError("Greenfield decision has competing assumptions")
        targets.add(target)
        rows.append({"applies_to": target, "statement": statement})
    return rows


def require_decision_assumptions(intent: Mapping[str, Any]) -> None:
    """Every optional decision has either a cited fact or one visible assumption."""

    targets = assumption_targets(intent.get("assumptions", []))
    for field in DECISION_FIELDS:
        if bool(intent.get(field)) == (field in targets):
            raise ValueError(f"Greenfield {field} requires one fact or one assumption")


def assumption_targets(value: Any) -> dict[str, str]:
    return {
        row["applies_to"]: f"/assumptions/{index}"
        for index, row in enumerate(assumption_rows(value))
        if row["applies_to"] != "general"
    }


def assumption_statements(value: Any) -> list[str]:
    return [row["statement"] for row in assumption_rows(value)]


def assumption_preview_values(value: Any) -> list[str]:
    """Expose every sealed decision target in the human confirmation view."""

    return [
        f"{row['applies_to'].replace('_', ' ').capitalize()} assumption — {row['statement']}"
        for row in assumption_rows(value)
    ]


def decision_copy(intent: Mapping[str, Any], field: str) -> str:
    """Render a decision while retaining the distinction from accepted fact."""

    fact = intent.get(field)
    if isinstance(fact, str) and fact:
        return fact
    for row in assumption_rows(intent.get("assumptions", [])):
        if row["applies_to"] == field:
            return f"Assumption — {row['statement']}"
    return ""
