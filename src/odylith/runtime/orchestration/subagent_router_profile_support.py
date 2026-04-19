"""Shared router-profile helpers for routing policy and user-facing explanations."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token

_USER_FACING_CHATTER_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("The current runtime handoff", "The current slice"),
    ("the current runtime handoff", "the current slice"),
    ("The retained runtime handoff", "The current slice"),
    ("the retained runtime handoff", "the current slice"),
    ("The retained context packet", "The current slice"),
    ("the retained context packet", "the current slice"),
    ("The current retained packet", "The current slice"),
    ("the current retained packet", "the current slice"),
    ("The retained packet", "The current slice"),
    ("the retained packet", "the current slice"),
    ("runtime handoff", "current slice"),
    ("runtime context packet", "current slice"),
    ("Control advisories", "Recent execution evidence"),
    ("control advisories", "recent execution evidence"),
    ("advisory loop", "recent execution evidence"),
    ("packetizer alignment", "execution fit"),
    ("runtime-backed", "measured"),
    ("native-spawn-ready", "delegation-ready"),
    ("route-ready", "ready for delegation"),
    ("hold-local", "local-first"),
    ("runtime memory contracts", "grounded evidence"),
    ("runtime contracts", "grounded contracts"),
    ("runtime optimization posture", "recent execution posture"),
    ("retained evidence pack", "current evidence set"),
)


class RouterProfile(str, Enum):
    MAIN_THREAD = "main_thread"
    ANALYSIS_MEDIUM = agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
    ANALYSIS_HIGH = agent_runtime_contract.ANALYSIS_HIGH_PROFILE
    FAST_WORKER = agent_runtime_contract.FAST_WORKER_PROFILE
    WRITE_MEDIUM = agent_runtime_contract.WRITE_MEDIUM_PROFILE
    WRITE_HIGH = agent_runtime_contract.WRITE_HIGH_PROFILE
    FRONTIER_HIGH = agent_runtime_contract.FRONTIER_HIGH_PROFILE
    FRONTIER_XHIGH = agent_runtime_contract.FRONTIER_XHIGH_PROFILE
    MINI_MEDIUM = agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
    MINI_HIGH = agent_runtime_contract.ANALYSIS_HIGH_PROFILE
    SPARK_MEDIUM = agent_runtime_contract.FAST_WORKER_PROFILE
    CODEX_MEDIUM = agent_runtime_contract.WRITE_MEDIUM_PROFILE
    CODEX_HIGH = agent_runtime_contract.WRITE_HIGH_PROFILE
    GPT54_HIGH = agent_runtime_contract.FRONTIER_HIGH_PROFILE
    GPT54_XHIGH = agent_runtime_contract.FRONTIER_XHIGH_PROFILE

    @property
    def model(self) -> str:
        model, _ = agent_runtime_contract.execution_profile_runtime_fields(self.value)
        return model

    @property
    def reasoning_effort(self) -> str:
        _, reasoning_effort = agent_runtime_contract.execution_profile_runtime_fields(self.value)
        return reasoning_effort


def router_profile_from_token(value: Any) -> RouterProfile | None:
    token = agent_runtime_contract.canonical_execution_profile(_normalize_token(value))
    try:
        return RouterProfile(token)
    except ValueError:
        return None


def router_profile_from_runtime(model: Any, reasoning_effort: Any) -> RouterProfile | None:
    runtime_model = _normalize_string(model)
    runtime_reasoning = _normalize_token(reasoning_effort)
    if runtime_model == "gpt-5.4-mini":
        if runtime_reasoning == "high":
            return RouterProfile.ANALYSIS_HIGH
        if runtime_reasoning == "medium":
            return RouterProfile.ANALYSIS_MEDIUM
    if runtime_model == "gpt-5.3-codex-spark" and runtime_reasoning == "medium":
        return RouterProfile.FAST_WORKER
    if runtime_model == "gpt-5.3-codex":
        if runtime_reasoning == "high":
            return RouterProfile.WRITE_HIGH
        if runtime_reasoning == "medium":
            return RouterProfile.WRITE_MEDIUM
    if runtime_model == "gpt-5.4":
        if runtime_reasoning == "xhigh":
            return RouterProfile.FRONTIER_XHIGH
        if runtime_reasoning == "high":
            return RouterProfile.FRONTIER_HIGH
    return None


def sanitize_user_facing_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for needle, replacement in _USER_FACING_CHATTER_REPLACEMENTS:
        text = text.replace(needle, replacement)
    return " ".join(text.split()).strip()


def sanitize_user_facing_lines(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        token = sanitize_user_facing_text(value)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def clamp_score(value: int | float) -> int:
    return max(0, min(4, int(round(float(value)))))


def agent_role_for_assessment(
    assessment: Any,
    *,
    profile: RouterProfile | None = None,
) -> str:
    if bool(getattr(assessment, "needs_write", False)):
        return "worker"
    summary = dict(getattr(assessment, "context_signal_summary", {}) or {})
    recommended_role = _normalize_token(summary.get("odylith_execution_agent_role", ""))
    confidence = clamp_score(summary.get("odylith_execution_confidence_score", 0) or 0)
    if recommended_role in {"explorer", "worker"} and confidence >= 3:
        return recommended_role
    if profile in {RouterProfile.MINI_MEDIUM, RouterProfile.MINI_HIGH} and getattr(assessment, "task_family", "") == "analysis_review":
        return "explorer"
    if not bool(getattr(assessment, "needs_write", False)) and getattr(assessment, "task_family", "") == "analysis_review":
        return "explorer"
    return "worker"


def _reliability_bias(counts: Mapping[str, int]) -> float:
    successes = int(counts.get("accepted", 0) or 0)
    failures = sum(
        int(counts.get(label, 0) or 0)
        for label in ("blocked", "ambiguous", "artifact_missing", "quality_too_weak", "broader_coordination")
    )
    total = successes + failures
    if total < 3:
        return 0.0
    return max(-0.25, min(0.25, ((successes - failures) / total) * 0.25))


def _count_total_labels(counts: Mapping[str, int], labels: Sequence[str]) -> int:
    return sum(int(counts.get(label, 0) or 0) for label in labels)


def _combined_counts(*rows: Mapping[str, int]) -> dict[str, int]:
    combined: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        for key, value in row.items():
            token = _normalize_token(key)
            if not token:
                continue
            combined[token] = int(combined.get(token, 0) or 0) + max(0, int(value or 0))
    return combined


def profile_reliability_summary(profile: RouterProfile, assessment: Any, tuning: Any) -> dict[str, Any]:
    task_family = str(getattr(assessment, "task_family", "") or "")
    outcome_counts = dict(getattr(tuning, "outcome_counts", {}) or {})
    family_outcome_counts = dict(getattr(tuning, "family_outcome_counts", {}) or {})
    global_counts = dict(outcome_counts.get(profile.value, {}))
    family_counts = dict(family_outcome_counts.get(task_family, {}).get(profile.value, {}))
    family_total = _count_total_labels(
        family_counts,
        (
            "accepted",
            "blocked",
            "ambiguous",
            "artifact_missing",
            "quality_too_weak",
            "broader_coordination",
            "escalated",
            "token_efficient",
        ),
    )
    counts = family_counts if family_total >= 2 else _combined_counts(global_counts, family_counts)
    accepted = int(counts.get("accepted", 0) or 0)
    blocked = int(counts.get("blocked", 0) or 0)
    ambiguous = int(counts.get("ambiguous", 0) or 0)
    artifact_missing = int(counts.get("artifact_missing", 0) or 0)
    quality_too_weak = int(counts.get("quality_too_weak", 0) or 0)
    broader_coordination = int(counts.get("broader_coordination", 0) or 0)
    token_efficient = int(counts.get("token_efficient", 0) or 0)
    failures = blocked + ambiguous + artifact_missing + quality_too_weak + broader_coordination
    severe_failures = blocked + ambiguous + quality_too_weak
    total = accepted + failures
    if total < 2:
        posture = "unknown"
    elif failures == 0 and accepted >= 3:
        posture = "strong"
    elif severe_failures >= 2 or failures > accepted:
        posture = "weak"
    else:
        posture = "mixed"
    return {
        "source": "family" if family_total >= 2 else "combined",
        "posture": posture,
        "accepted": accepted,
        "failures": failures,
        "severe_failures": severe_failures,
        "token_efficient": token_efficient,
        "total": total,
    }


def tuning_bias_for_profile(profile: RouterProfile, assessment: Any, tuning: Any) -> float:
    task_family = str(getattr(assessment, "task_family", "") or "")
    profile_bias = float(dict(getattr(tuning, "profile_bias", {}) or {}).get(profile.value, 0.0) or 0.0)
    family_profile_bias = dict(getattr(tuning, "family_profile_bias", {}) or {})
    family_outcome_counts = dict(getattr(tuning, "family_outcome_counts", {}) or {})
    outcome_counts = dict(getattr(tuning, "outcome_counts", {}) or {})
    family_bias = float(family_profile_bias.get(task_family, {}).get(profile.value, 0.0) or 0.0)
    return (
        profile_bias
        + family_bias
        + _reliability_bias(outcome_counts.get(profile.value, {}))
        + _reliability_bias(family_outcome_counts.get(task_family, {}).get(profile.value, {}))
    )


__all__ = [
    "RouterProfile",
    "agent_role_for_assessment",
    "clamp_score",
    "profile_reliability_summary",
    "router_profile_from_runtime",
    "router_profile_from_token",
    "sanitize_user_facing_lines",
    "sanitize_user_facing_text",
    "tuning_bias_for_profile",
]
