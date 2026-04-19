"""Contract helpers for the Odylith governance proof state layer."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.common.value_coercion import normalize_string as _normalize_token

PROOF_STATUSES: tuple[str, ...] = (
    "diagnosed",
    "fixed_in_code",
    "unit_tested",
    "preview_tested",
    "deployed",
    "live_verified",
    "falsified_live",
)
WORK_CATEGORIES: tuple[str, ...] = (
    "primary_blocker",
    "adjacent_runtime",
    "observability",
    "governance",
    "test_hardening",
)
DEPLOYMENT_TRUTH_FIELDS: tuple[str, ...] = (
    "local_head",
    "pushed_head",
    "published_source_commit",
    "runner_fingerprint",
    "last_live_failing_commit",
)
CLAIM_GUARD_TERMS: tuple[str, ...] = ("fixed", "cleared", "resolved")
_STATUS_ORDER = {token: index for index, token in enumerate(PROOF_STATUSES)}
_STATUS_TO_EVIDENCE_TIER = {
    "diagnosed": "diagnosis_only",
    "fixed_in_code": "code_only",
    "unit_tested": "unit_tested",
    "preview_tested": "preview_tested",
    "deployed": "deployed_not_live_verified",
    "live_verified": "live_verified",
    "falsified_live": "falsified_live",
}

def _string_list(values: Any, *, allowed: tuple[str, ...] | None = None) -> list[str]:
    if not isinstance(values, list):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    allowed_values = set(allowed or ())
    for raw in values:
        token = _normalize_token(raw)
        if not token or token in seen:
            continue
        if allowed_values and token not in allowed_values:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def normalize_deployment_truth(value: Any) -> dict[str, str]:
    raw = dict(value) if isinstance(value, Mapping) else {}
    return {
        field: _normalize_token(raw.get(field)) or "unknown"
        for field in DEPLOYMENT_TRUTH_FIELDS
    }


def evidence_tier_for_status(status: str, explicit_value: Any = "") -> str:
    explicit = _normalize_token(explicit_value)
    if explicit:
        return explicit
    return _STATUS_TO_EVIDENCE_TIER.get(_normalize_token(status), "unknown")


def status_rank(status: Any) -> int:
    return int(_STATUS_ORDER.get(_normalize_token(status), -1))


def frontier_has_advanced(proof_state: Mapping[str, Any] | Any) -> bool:
    state = normalize_proof_state(proof_state)
    status = _normalize_token(state.get("proof_status"))
    if status == "live_verified":
        return True
    if status != "deployed":
        return False
    first_phase = _normalize_token(state.get("first_failing_phase"))
    frontier_phase = _normalize_token(state.get("frontier_phase"))
    return bool(first_phase and frontier_phase and frontier_phase != first_phase)


def normalize_proof_state(value: Any) -> dict[str, Any]:
    raw = dict(value) if isinstance(value, Mapping) else {}
    if not raw:
        return {}
    deployment_truth_signal = (
        isinstance(raw.get("deployment_truth"), Mapping)
        and any(_normalize_token(token) for token in raw.get("deployment_truth", {}).values())
    )
    has_signal = deployment_truth_signal or any(
        (
            _normalize_token(raw.get("lane_id")),
            _normalize_token(raw.get("current_blocker")),
            _normalize_token(raw.get("failure_fingerprint")),
            _normalize_token(raw.get("first_failing_phase")),
            _normalize_token(raw.get("frontier_phase")),
            _normalize_token(raw.get("clearance_condition")),
            _normalize_token(raw.get("proof_status")),
            _normalize_token(raw.get("evidence_tier")),
            _normalize_token(raw.get("linked_bug_id")),
            _normalize_token(raw.get("source")),
            _normalize_token(raw.get("source_path")),
            _normalize_token(raw.get("resolution_state")),
        )
    )
    if not has_signal:
        if isinstance(raw.get("last_falsification"), Mapping) and raw.get("last_falsification"):
            has_signal = True
        elif isinstance(raw.get("allowed_next_work"), list) and raw.get("allowed_next_work"):
            has_signal = True
        elif isinstance(raw.get("deprioritized_until_cleared"), list) and raw.get("deprioritized_until_cleared"):
            has_signal = True
        elif int(raw.get("repeated_fingerprint_count", 0) or 0) > 0:
            has_signal = True
        elif isinstance(raw.get("recent_work_categories"), list) and raw.get("recent_work_categories"):
            has_signal = True
        elif isinstance(raw.get("warnings"), list) and raw.get("warnings"):
            has_signal = True
    if not has_signal:
        return {}
    status = _normalize_token(raw.get("proof_status"))
    if status not in PROOF_STATUSES:
        status = "diagnosed"
    normalized = {
        "lane_id": _normalize_token(raw.get("lane_id")),
        "current_blocker": _normalize_token(raw.get("current_blocker")),
        "failure_fingerprint": _normalize_token(raw.get("failure_fingerprint")),
        "first_failing_phase": _normalize_token(raw.get("first_failing_phase")),
        "frontier_phase": _normalize_token(raw.get("frontier_phase")) or _normalize_token(raw.get("first_failing_phase")),
        "clearance_condition": _normalize_token(raw.get("clearance_condition")),
        "proof_status": status,
        "evidence_tier": evidence_tier_for_status(status, raw.get("evidence_tier")),
        "last_falsification": dict(raw.get("last_falsification", {})) if isinstance(raw.get("last_falsification"), Mapping) else {},
        "allowed_next_work": _string_list(raw.get("allowed_next_work")),
        "deprioritized_until_cleared": _string_list(raw.get("deprioritized_until_cleared")),
        "linked_bug_id": _normalize_token(raw.get("linked_bug_id")),
        "deployment_truth": normalize_deployment_truth(raw.get("deployment_truth")),
    }
    work_categories = _string_list(raw.get("recent_work_categories"), allowed=WORK_CATEGORIES)
    if work_categories:
        normalized["recent_work_categories"] = work_categories
    warnings = _string_list(raw.get("warnings"))
    if warnings:
        normalized["warnings"] = warnings
    repeated_fingerprint_count = int(raw.get("repeated_fingerprint_count", 0) or 0)
    if repeated_fingerprint_count > 0:
        normalized["repeated_fingerprint_count"] = repeated_fingerprint_count
    source = _normalize_token(raw.get("source"))
    if source:
        normalized["source"] = source
    source_path = _normalize_token(raw.get("source_path"))
    if source_path:
        normalized["source_path"] = source_path
    resolution_state = _normalize_token(raw.get("resolution_state"))
    if resolution_state:
        normalized["resolution_state"] = resolution_state
    return {key: value for key, value in normalized.items() if value not in ("", [], {})}


def build_claim_guard(proof_state: Mapping[str, Any] | Any) -> dict[str, Any]:
    state = normalize_proof_state(proof_state)
    status = _normalize_token(state.get("proof_status")) or "diagnosed"
    last_falsification = dict(state.get("last_falsification", {})) if isinstance(state.get("last_falsification"), Mapping) else {}
    failure_fingerprint = _normalize_token(state.get("failure_fingerprint"))
    falsified_fingerprint = _normalize_token(last_falsification.get("failure_fingerprint"))
    hosted_frontier_advanced = frontier_has_advanced(state)
    highest_truthful_claim = {
        "diagnosed": "diagnosed",
        "fixed_in_code": "fixed in code",
        "unit_tested": "unit-tested",
        "preview_tested": "preview-tested",
        "deployed": "deployed",
        "live_verified": "fixed live",
        "falsified_live": "falsified live",
    }.get(status, "diagnosed")
    if hosted_frontier_advanced:
        highest_truthful_claim = "fixed live"
    return {
        "proof_status": status,
        "same_fingerprint_as_last_falsification": bool(failure_fingerprint and falsified_fingerprint and failure_fingerprint == falsified_fingerprint),
        "hosted_frontier_advanced": hosted_frontier_advanced,
        "claim_scope": "live" if hosted_frontier_advanced else "code_or_preview",
        "highest_truthful_claim": highest_truthful_claim,
        "blocked_terms": [] if hosted_frontier_advanced else list(CLAIM_GUARD_TERMS),
    }


def build_claim_lint(claim_guard: Mapping[str, Any] | Any) -> dict[str, Any]:
    guard = dict(claim_guard) if isinstance(claim_guard, Mapping) else {}
    blocked_terms = [
        _normalize_token(token)
        for token in guard.get("blocked_terms", [])
        if _normalize_token(token)
    ] if isinstance(guard.get("blocked_terms"), list) else []
    highest_truthful_claim = _normalize_token(guard.get("highest_truthful_claim")) or "diagnosed"
    live_ok = bool(guard.get("hosted_frontier_advanced"))
    same_fingerprint = bool(guard.get("same_fingerprint_as_last_falsification"))
    claim_scope = _normalize_token(guard.get("claim_scope")) or ("live" if live_ok else "code_or_preview")
    forced_checks = [
        {
            "id": "same_failure_fingerprint",
            "question": "Is this the same failure fingerprint as the last falsification?",
            "answer": "yes" if same_fingerprint else "no_or_unknown",
        },
        {
            "id": "hosted_frontier_advanced",
            "question": "Has the hosted proof advanced past the prior failing phase?",
            "answer": "yes" if live_ok else "no",
        },
        {
            "id": "claim_scope",
            "question": "Is the claim code-only, preview-only, or live?",
            "answer": claim_scope or "unknown",
        },
    ]
    return {
        "status": "live_ok" if live_ok else "restricted",
        "highest_truthful_claim": highest_truthful_claim,
        "blocked_terms": blocked_terms,
        "checks": [
            "Is this the same failure fingerprint as the last falsification?",
            "Has the hosted proof advanced past the prior failing phase?",
            "Is the claim code-only, preview-only, or live?",
        ],
        "forced_checks": forced_checks,
        "replacement_hint": highest_truthful_claim,
        "gate": {
            "required": True,
            "state": "allow_unqualified_resolution_terms" if live_ok else "rewrite_or_block",
            "same_fingerprint_as_last_falsification": same_fingerprint,
            "hosted_frontier_advanced": live_ok,
            "claim_scope": claim_scope or "unknown",
        },
    }
