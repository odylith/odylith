"""Projection-surface scanning for greenfield semantic boundary checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import clean_text

PROJECTION_SCAN_ROOTS = (
    "accepted_project",
    "accepted_project_preview",
    "backlog",
    "components",
    "dashboard",
    "diagrams",
    "experience",
    "intent",
    "project_brief",
    "project_dashboard",
    "project_dashboard_preview",
    "project_experience",
    "project_intelligence",
)
PROOF_ONLY_PROJECTION_KEYS = frozenset(
    {
        "command",
        "commands",
        "host_independent_paths",
        "proof",
        "proof_boundary",
        "proof_obligations",
        "review_posture",
        "schema_version",
        "validation_strategy",
    }
)


def semantic_projection_values(proposal: Mapping[str, Any], intent: Mapping[str, Any]) -> list[tuple[str, Any]]:
    """Return human-visible projection values that can accidentally carry proof text."""

    values: list[tuple[str, Any]] = []
    for key in ("problem", "opportunity", "product_view", "success_metrics"):
        values.append((f"intent.{key}", intent.get(key)))
    for index, row in enumerate(mapping_rows(proposal.get("backlog"))):
        for key in ("problem", "opportunity", "product_view", "success_metrics"):
            values.append((f"backlog.{index}.{key}", row.get(key)))
    for root in PROJECTION_SCAN_ROOTS:
        if root in proposal:
            values.extend(projection_text_values(root, proposal.get(root)))
    deduped: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for path, value in values:
        if path in seen:
            continue
        seen.add(path)
        deduped.append((path, value))
    return deduped


def projection_text_values(path: str, value: Any) -> list[tuple[str, Any]]:
    """Walk a generated projection while skipping explicitly proof-only fields."""

    if projection_path_is_proof_only(path):
        return []
    if isinstance(value, Mapping):
        rows: list[tuple[str, Any]] = []
        for key, nested in value.items():
            key_text = str(key or "").strip()
            if key_text:
                rows.extend(projection_text_values(f"{path}.{key_text}", nested))
        return rows
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        rows: list[tuple[str, Any]] = []
        for index, nested in enumerate(value):
            rows.extend(projection_text_values(f"{path}.{index}", nested))
        return rows
    return [(path, value)] if clean_text(value) else []


def projection_path_is_proof_only(path: str) -> bool:
    parts = {part.casefold().strip() for part in str(path or "").replace("[", ".").replace("]", "").split(".")}
    return bool(parts & PROOF_ONLY_PROJECTION_KEYS)


__all__ = [
    "projection_path_is_proof_only",
    "projection_text_values",
    "semantic_projection_values",
]
