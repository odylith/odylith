"""History Rules helpers for the Odylith execution engine layer."""

from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.execution_engine.contract import AdmissibilityDecision
from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.execution_engine.contract import ResourceClosure


def _string(value: Any) -> str:
    return str(value or "").strip()


def _token(value: Any) -> str:
    return "_".join(_string(value).lower().replace("-", " ").split())


def canonicalize_history_rule(value: Any) -> str:
    raw = _string(value)
    token = _token(value)
    if not token:
        return ""
    if token in {
        "partial_scope_requires_closure",
        "destructive_subset_blocked",
        "repeated_rediscovery_detected",
        "contradiction_blocked_preflight",
        "reanchor_triggered",
        "lane_drift_preflight",
        "user_correction_requires_promotion",
        "context_exhaustion_detected",
        "subagent_timeout_detected",
    }:
        return token
    if "destructive" in token and ("subset" in token or "prune" in token):
        return "destructive_subset_blocked"
    if "partial" in token and ("scope" in token or "closure" in token):
        return "partial_scope_requires_closure"
    if "rediscovery" in token or "same_fingerprint_reopened" in token:
        return "repeated_rediscovery_detected"
    if "contradiction" in token:
        return "contradiction_blocked_preflight"
    if "lane" in token and "drift" in token:
        return "lane_drift_preflight"
    if "user" in token and "correction" in token:
        return "user_correction_requires_promotion"
    if "reanchor" in token:
        return "reanchor_triggered"
    if "context" in token and any(sub in token for sub in ("exhaust", "pressure", "compact")):
        return "context_exhaustion_detected"
    if "subagent" in token and "timeout" in token:
        return "subagent_timeout_detected"
    if raw.startswith("CB-"):
        return f"casebook:{raw}"
    return token


def _history_tokens_from_value(value: Any) -> list[str]:
    if isinstance(value, str):
        token = canonicalize_history_rule(value)
        return [token] if token else []
    if isinstance(value, Mapping):
        rows: list[str] = []
        for key in ("rule", "token", "failure_class", "class", "category", "bug_id"):
            token = canonicalize_history_rule(value.get(key))
            if token:
                rows.append(token)
        return rows
    if isinstance(value, list):
        rows: list[str] = []
        for item in value:
            rows.extend(_history_tokens_from_value(item))
        return rows
    return []


def collect_history_rule_hits(
    *,
    closure: ResourceClosure,
    admissibility: AdmissibilityDecision,
    contradictions: Sequence[ContradictionRecord],
    proof_same_fingerprint_reopened: bool,
    carried_history: Sequence[Any] = (),
) -> tuple[str, ...]:
    hits: list[str] = []
    if closure.classification == "incomplete":
        hits.append("partial_scope_requires_closure")
    if closure.classification == "destructive":
        hits.append("destructive_subset_blocked")
    if proof_same_fingerprint_reopened:
        hits.append("repeated_rediscovery_detected")
    if any(row.blocks_execution for row in contradictions):
        hits.append("contradiction_blocked_preflight")
    if admissibility.requires_reanchor:
        hits.append("reanchor_triggered")
    for item in carried_history:
        hits.extend(_history_tokens_from_value(item))
    return tuple(dict.fromkeys(token for token in hits if token))


__all__ = ["canonicalize_history_rule", "collect_history_rule_hits"]
