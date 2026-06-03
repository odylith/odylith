"""Typed first-path records shared by greenfield parsers and renderers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FirstPathModel:
    raw_path: str
    steps: tuple[str, ...]
    material_action: str
    visible_outcome: str
    recovery_action: str


@dataclass(frozen=True)
class FirstPathClauses:
    """Reusable first-path prose clauses rendered by greenfield surfaces."""

    model: FirstPathModel
    action_chain: str
    capability_chain: str
    visible_result: str


__all__ = ["FirstPathClauses", "FirstPathModel"]
