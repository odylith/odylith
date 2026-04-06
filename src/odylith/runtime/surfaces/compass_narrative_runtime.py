"""Narrative helper functions extracted from Compass runtime."""

from __future__ import annotations

import re
from collections.abc import Callable

_ACTION_LEAD_VERB_RE = re.compile(
    r"^(?:add|align|audit|backfill|bind|build|capture|clean(?:\s+up)?|close|codify|complete|convert|cut|"
    r"define|deliver|document|enable|enforce|finish|harden|implement|introduce|land|migrate|move|publish|"
    r"reconcile|refresh|remove|replace|seed|ship|stabilize|tighten|update|validate|verify|wire)\b",
    re.IGNORECASE,
)


def action_clause_for_narrative(
    text: str,
    *,
    normalize_action_task: Callable[[str], str],
) -> str:
    """Normalize an action string into a narrative clause."""

    token = normalize_action_task(text)
    if not token:
        return ""
    if _ACTION_LEAD_VERB_RE.match(token):
        return token
    return f"land {token}"


def timeline_clause(*, eta_days: int, eta_source: str, status: str, has_execution_signal: bool) -> str:
    """Describe the current ETA posture in narrative form."""

    source = str(eta_source or "").strip().lower()
    token = str(status or "").strip().lower()
    if source.startswith("model-"):
        confidence = source.split("-", 1)[1] or "medium"
        return f"projected at roughly {eta_days} days ({confidence} confidence)"
    if source == "heuristic":
        if token == "planning" and not has_execution_signal:
            return f"provisional at roughly {eta_days} days while planning details stabilize"
        return f"projected at roughly {eta_days} days and expected to tighten as execution closes checklist items"
    return f"projected at roughly {eta_days} days"
