"""Component Registry Review Policy helpers for the Odylith governance layer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_TRUTHY_TOKENS = {"1", "true", "yes", "required", "review"}


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    token = str(value or "").strip().lower()
    return token in _TRUTHY_TOKENS


def catalog_component_requests_inventory_review(raw_component: Mapping[str, Any] | Any) -> bool:
    """Return true when an Atlas component annotation opts into Registry review.

    Atlas component labels usually describe diagram-local stages, seams, or
    contracts. They should not be treated as first-class Registry candidates
    unless the author explicitly marks them for inventory review.
    """

    if not isinstance(raw_component, Mapping):
        return False
    for key in (
        "inventory_candidate",
        "inventory_review_required",
        "candidate_component_review",
    ):
        if _is_truthy(raw_component.get(key)):
            return True
    return False


def should_emit_deep_skill_policy_warning(row: Mapping[str, Any] | Any) -> bool:
    """Return true when a deep-skill policy result should surface as a warning."""

    if not isinstance(row, Mapping):
        return False
    missing = [
        str(token or "").strip()
        for token in row.get("missing", [])
        if str(token or "").strip()
    ] if isinstance(row.get("missing"), list) else []
    if bool(row.get("exists")):
        return bool(missing)
    if bool(row.get("required")):
        return bool(missing)
    return missing != ["component_missing"]
