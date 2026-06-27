"""Neutral projection-scope helpers for typed greenfield PatchSet application."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string_list
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_expand_projection_scope
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_scope_requires_full_prewrite
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_projection_id


def patch_operation_explicit_affected_projections(operation: Mapping[str, Any]) -> tuple[str, ...]:
    """Return only explicit affected projection IDs carried by a PatchSet operation."""

    affected = operation.get("affected_projections")
    if not isinstance(affected, Sequence) or isinstance(affected, (str, bytes, bytearray)):
        return ()
    projections = tuple(
        projection
        for projection in (artifact_projection_id(row) for row in normalize_string_list(affected, limit=16))
        if projection
    )
    return tuple(dict.fromkeys(projections))


def patch_operations_explicit_affected_projections(operations: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return deduplicated explicit projection scope from a sequence of PatchSet operations."""

    return tuple(
        dict.fromkeys(
            projection
            for operation in operations
            for projection in patch_operation_explicit_affected_projections(operation)
        )
    )


def patch_expand_projection_scope(projections: Sequence[Any]) -> tuple[str, ...]:
    """Expand projection IDs through package-preview dependencies."""

    return artifact_plan_expand_projection_scope(projections)


def patch_scope_requires_full_prewrite(projections: Sequence[Any]) -> bool:
    """Return true when projection scope must restage Radar/program outputs."""

    return artifact_plan_scope_requires_full_prewrite(projections)


__all__ = [
    "patch_expand_projection_scope",
    "patch_operation_explicit_affected_projections",
    "patch_operations_explicit_affected_projections",
    "patch_scope_requires_full_prewrite",
]
