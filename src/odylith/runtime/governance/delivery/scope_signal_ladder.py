"""Deterministic scope-signal ladder shared across governance surfaces.

The ladder decides three things consistently:
- whether a scope is promoted by default;
- how strongly it should be ranked when visible;
- whether it may spend expensive downstream compute.

The contract is intentionally provider-neutral so Codex-, Claude-, and future
hosts can all map the same ladder onto their local execution budgets.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.governance import proof_state
from odylith.runtime.governance import workstream_inference

SCOPED_FANOUT_CAP = 4
DEFAULT_PROMOTED_DEFAULT_RANK = 3
GOVERNANCE_ONLY_PREFIXES = (
    "odylith/radar/source/",
    "odylith/technical-plans/",
    "odylith/casebook/",
    "odylith/atlas/source/",
    "odylith/registry/source/",
)

BUDGET_CLASS_NONE = "none"
BUDGET_CLASS_CACHE_ONLY = "cache_only"
BUDGET_CLASS_FAST_SIMPLE = "fast_simple"
BUDGET_CLASS_ESCALATED_REASONING = "escalated_reasoning"

_RUNG_SPECS: dict[int, tuple[str, str, str]] = {
    0: ("R0", "suppressed_noise", "Suppressed noise"),
    1: ("R1", "background_trace", "Background trace"),
    2: ("R2", "verified_local", "Verified local"),
    3: ("R3", "active_scope", "Active scope"),
    4: ("R4", "actionable_priority", "Actionable priority"),
    5: ("R5", "blocking_frontier", "Blocking frontier"),
}
_RANKS_BY_TOKEN = {token: rank for rank, (_rung, token, _label) in _RUNG_SPECS.items()}
_VALID_BUDGET_CLASSES = frozenset(
    {
        BUDGET_CLASS_NONE,
        BUDGET_CLASS_CACHE_ONLY,
        BUDGET_CLASS_FAST_SIMPLE,
        BUDGET_CLASS_ESCALATED_REASONING,
    }
)
_CAP_REASON_LABELS: dict[str, str] = {
    "generated_only_churn": "Only generated churn was observed.",
    "governance_only_local_change": "Only governance-owned local changes were observed.",
    "broad_fanout": "The signal fans across too many scopes to promote directly.",
    "window_inactive": "This scope has no verified activity in the selected window.",
}
_POSITIVE_REASON_LABELS: dict[str, str] = {
    "verified_completion": "A recent verified completion was recorded.",
    "narrow_verified_signal": "A narrow verified scoped signal was recorded.",
    "meaningful_scope_activity": "Meaningful scope-local implementation evidence is present.",
    "decision_evidence": "Explicit decision evidence is present.",
    "implementation_evidence": "Explicit implementation evidence is present.",
    "open_warning": "An open warning or operator recommendation is still unresolved.",
    "cross_surface_conflict": "Linked surfaces still disagree on the current state.",
    "stale_authority": "The current authority signal is stale.",
    "unsafe_closeout": "Closeout is ahead of the latest trustworthy proof.",
    "proof_blocker": "A live proof blocker is still open.",
    "child_rollup": "Child scopes lift this parent above the local baseline.",
}


def _normalize_path_token(value: Any) -> str:
    return workstream_inference.normalize_repo_token(str(value or "")).strip()


def _normalize_bool(value: Any) -> bool:
    return bool(value)


def _normalize_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _budget_class_for_rank(rank: int) -> str:
    if rank <= 0:
        return BUDGET_CLASS_NONE
    if rank <= 2:
        return BUDGET_CLASS_CACHE_ONLY
    if rank == 3:
        return BUDGET_CLASS_FAST_SIMPLE
    return BUDGET_CLASS_ESCALATED_REASONING


def scope_signal_rank(signal: Mapping[str, Any] | Any) -> int:
    if not isinstance(signal, Mapping):
        return 0
    raw_rank = signal.get("rank")
    if isinstance(raw_rank, int):
        return max(0, min(5, raw_rank))
    rung = str(signal.get("rung", "")).strip().upper()
    if rung.startswith("R") and rung[1:].isdigit():
        return max(0, min(5, int(rung[1:])))
    token = str(signal.get("token", "")).strip().lower()
    return max(0, min(5, int(_RANKS_BY_TOKEN.get(token, 0))))


def _rung_parts(rank: int) -> tuple[str, str, str]:
    return _RUNG_SPECS.get(max(0, min(5, int(rank))), _RUNG_SPECS[0])


def budget_class_allows_fresh_provider(budget_class: str) -> bool:
    return str(budget_class or "").strip().lower() == BUDGET_CLASS_ESCALATED_REASONING


def budget_class_allows_reasoning(budget_class: str) -> bool:
    token = str(budget_class or "").strip().lower()
    return token in {BUDGET_CLASS_FAST_SIMPLE, BUDGET_CLASS_ESCALATED_REASONING}


def validate_scope_signal(signal: Mapping[str, Any] | Any) -> list[str]:
    if not isinstance(signal, Mapping):
        return ["scope_signal must be an object"]
    errors: list[str] = []
    rank = scope_signal_rank(signal)
    rung, token, label = _rung_parts(rank)
    if str(signal.get("rung", "")).strip() and str(signal.get("rung", "")).strip() != rung:
        errors.append("scope_signal rung does not match rank")
    if str(signal.get("token", "")).strip() and str(signal.get("token", "")).strip() != token:
        errors.append("scope_signal token does not match rank")
    if str(signal.get("label", "")).strip() and str(signal.get("label", "")).strip() != label:
        errors.append("scope_signal label does not match rank")
    reasons = signal.get("reasons", [])
    if not isinstance(reasons, list):
        errors.append("scope_signal reasons must be a list")
    caps = signal.get("caps", [])
    if not isinstance(caps, list):
        errors.append("scope_signal caps must be a list")
    budget_class = str(signal.get("budget_class", "")).strip()
    if budget_class and budget_class not in _VALID_BUDGET_CLASSES:
        errors.append("scope_signal budget_class is invalid")
    return errors


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = " ".join(str(raw or "").split()).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _caps_from_features(features: Mapping[str, Any]) -> tuple[int, list[str], list[str]]:
    cap_rank = 5
    cap_tokens: list[str] = []
    cap_reasons: list[str] = []
    if _normalize_bool(features.get("generated_only_churn")):
        cap_rank = min(cap_rank, 0)
        cap_tokens.append("generated_only_churn")
    if _normalize_bool(features.get("governance_only_local_change")):
        cap_rank = min(cap_rank, 1)
        cap_tokens.append("governance_only_local_change")
    if _normalize_bool(features.get("broad_fanout")):
        cap_rank = min(cap_rank, 1)
        cap_tokens.append("broad_fanout")
    if _normalize_bool(features.get("window_inactive")):
        cap_rank = min(cap_rank, 1)
        cap_tokens.append("window_inactive")
    for token in cap_tokens:
        label = _CAP_REASON_LABELS.get(token)
        if label:
            cap_reasons.append(label)
    return cap_rank, cap_tokens, _dedupe_strings(cap_reasons)


def _base_activity_rank(features: Mapping[str, Any], *, cap_rank: int) -> tuple[int, list[str]]:
    reasons: list[str] = []
    activity_rank = 0
    has_any_signal = any(
        (
            _normalize_bool(features.get("has_any_signal")),
            _normalize_int(features.get("explicit_count")) > 0,
            _normalize_int(features.get("synthetic_count")) > 0,
            _normalize_int(features.get("meaningful_change_count")) > 0,
        )
    )
    if has_any_signal:
        activity_rank = 1
    if _normalize_bool(features.get("verified_completion")):
        activity_rank = max(activity_rank, 2)
        reasons.append(_POSITIVE_REASON_LABELS["verified_completion"])
    if _normalize_bool(features.get("narrow_verified_signal")):
        activity_rank = max(activity_rank, 2)
        reasons.append(_POSITIVE_REASON_LABELS["narrow_verified_signal"])
    if _normalize_bool(features.get("decision_evidence")):
        activity_rank = max(activity_rank, 3)
        reasons.append(_POSITIVE_REASON_LABELS["decision_evidence"])
    if _normalize_bool(features.get("implementation_evidence")):
        activity_rank = max(activity_rank, 3)
        reasons.append(_POSITIVE_REASON_LABELS["implementation_evidence"])
    if _normalize_bool(features.get("meaningful_scope_activity")):
        activity_rank = max(activity_rank, 3)
        reasons.append(_POSITIVE_REASON_LABELS["meaningful_scope_activity"])
    if _normalize_bool(features.get("has_any_signal")) and not reasons and activity_rank == 1:
        reasons.append("Recent signal exists, but it is not strong enough to promote by default.")
    return min(activity_rank, cap_rank), _dedupe_strings(reasons)


def _posture_rank(features: Mapping[str, Any]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    posture_rank = 0
    for token in ("open_warning", "cross_surface_conflict", "stale_authority"):
        if _normalize_bool(features.get(token)):
            posture_rank = max(posture_rank, 4)
            reasons.append(_POSITIVE_REASON_LABELS[token])
    for token in ("unsafe_closeout", "proof_blocker"):
        if _normalize_bool(features.get(token)):
            posture_rank = max(posture_rank, 5)
            reasons.append(_POSITIVE_REASON_LABELS[token])
    return posture_rank, _dedupe_strings(reasons)


def _rollup_rank(child_signals: Sequence[Mapping[str, Any]]) -> tuple[int, list[str]]:
    child_ranks = [scope_signal_rank(signal) for signal in child_signals if isinstance(signal, Mapping)]
    if not child_ranks:
        return 0, []
    highest = max(child_ranks)
    corroborating_verified = sum(1 for rank in child_ranks if rank >= 2)
    if highest >= 5:
        return 5, ["A linked child scope is carrying a live blocker frontier."]
    if highest >= 4:
        return 4, ["A linked child scope is already in actionable warning posture."]
    if highest >= 3:
        return 3, ["A linked child scope is already an active default focus."]
    if corroborating_verified >= 2:
        return 3, ["Multiple verified child scopes lift this parent into active default focus."]
    if corroborating_verified == 1:
        return 2, ["A verified child scope keeps this parent visible in focused views."]
    if highest >= 1:
        return 1, ["Only low-signal child traces are currently present."]
    return 0, []


def build_scope_signal(
    *,
    feature_vector: Mapping[str, Any],
    child_signals: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    features = dict(feature_vector) if isinstance(feature_vector, Mapping) else {}
    cap_rank, cap_tokens, cap_reasons = _caps_from_features(features)
    activity_rank, activity_reasons = _base_activity_rank(features, cap_rank=cap_rank)
    posture_rank, posture_reasons = _posture_rank(features)
    rollup_rank, rollup_reasons = _rollup_rank(child_signals)
    rank = max(activity_rank, posture_rank, rollup_rank)
    rung, token, label = _rung_parts(rank)
    reasons = _dedupe_strings([*cap_reasons, *activity_reasons, *posture_reasons, *rollup_reasons])
    return {
        "rank": rank,
        "rung": rung,
        "token": token,
        "label": label,
        "reasons": reasons,
        "caps": cap_tokens,
        "promoted_default": rank >= DEFAULT_PROMOTED_DEFAULT_RANK,
        "budget_class": _budget_class_for_rank(rank),
        "feature_vector": {
            key: value
            for key, value in features.items()
            if isinstance(value, (bool, int, float, str, list, dict))
        },
    }


def _governance_only_paths(paths: Sequence[str]) -> bool:
    normalized = [_normalize_path_token(path) for path in paths if _normalize_path_token(path)]
    if not normalized:
        return False
    return all(
        any(path.startswith(prefix) for prefix in GOVERNANCE_ONLY_PREFIXES)
        for path in normalized
    )


def _generated_only_paths(paths: Sequence[str]) -> bool:
    normalized = [_normalize_path_token(path) for path in paths if _normalize_path_token(path)]
    if not normalized:
        return False
    return all(workstream_inference.is_generated_or_global_path(path) for path in normalized)


def _delivery_feature_vector(
    *,
    snapshot: Mapping[str, Any],
    scope_lookup: Mapping[str, Mapping[str, Any]],
    control_posture: Mapping[str, Any],
) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    scores = snapshot.get("scores", {}) if isinstance(snapshot.get("scores"), Mapping) else {}
    scope_type = str(snapshot.get("scope_type", "")).strip()
    changed_artifacts = [
        _normalize_path_token(path)
        for path in evidence.get("changed_artifacts", [])
        if _normalize_path_token(path)
    ] if isinstance(evidence.get("changed_artifacts"), list) else []
    code_references = [
        _normalize_path_token(path)
        for path in evidence.get("code_references", [])
        if _normalize_path_token(path)
    ] if isinstance(evidence.get("code_references"), list) else []
    linked_surfaces = [
        str(token).strip()
        for token in evidence.get("linked_surfaces", [])
        if str(token).strip()
    ] if isinstance(evidence.get("linked_surfaces"), list) else []
    linked_workstreams = [
        str(token).strip()
        for token in evidence.get("linked_workstreams", [])
        if str(token).strip()
    ] if isinstance(evidence.get("linked_workstreams"), list) else []
    child_keys: list[str] = []
    if scope_type in {"surface", "grid"}:
        child_keys = [
            str(token).strip()
            for token in diagnostics.get("child_scope_keys", [])
            if str(token).strip() and str(token).strip() in scope_lookup
        ] if isinstance(diagnostics.get("child_scope_keys"), list) else []
    elif scope_type in {"component", "diagram"}:
        child_keys = [
            f"workstream:{token}"
            for token in linked_workstreams
            if f"workstream:{token}" in scope_lookup
        ]
    child_signals = [
        dict(scope_lookup[key].get("scope_signal", {}))
        for key in child_keys
        if key in scope_lookup and isinstance(scope_lookup[key].get("scope_signal"), Mapping)
    ]
    explicit_count = _normalize_int(diagnostics.get("explicit_count"))
    decision_count = _normalize_int(diagnostics.get("decision_count"))
    implementation_count = _normalize_int(diagnostics.get("implementation_count"))
    synthetic_count = _normalize_int(diagnostics.get("synthetic_count"))
    proof_row = proof_state.normalize_proof_state(snapshot.get("proof_state", {}))
    proof_status = str(proof_row.get("proof_status", "")).strip().lower()
    current_blocker = str(proof_row.get("current_blocker", "")).strip()
    frontier_phase = str(proof_row.get("frontier_phase", "")).strip()
    generated_only = _generated_only_paths(changed_artifacts)
    governance_only = _governance_only_paths(changed_artifacts) and not code_references
    has_meaningful_change = any(
        _normalize_int(snapshot.get("change_vector", {}).get(bucket))
        > 0
        for bucket in ("contract", "spec", "runtime", "policy", "runbook", "build_ci", "cli")
        if isinstance(snapshot.get("change_vector"), Mapping)
    ) or bool(code_references)
    closeout_signal = str(diagnostics.get("closeout_signal", "")).strip().lower()
    basis = str(evidence.get("basis", "")).strip().lower()
    freshness = str(evidence.get("freshness", "")).strip().lower()
    stale_diagram = _normalize_bool(diagnostics.get("stale_diagram"))
    blast_radius_class = str(diagnostics.get("blast_radius_class", evidence.get("blast_radius_class", ""))).strip().lower()
    linked_surface_count = len(linked_surfaces)
    cross_surface_conflict = (
        blast_radius_class == "cross-surface"
        and linked_surface_count >= 2
        and _normalize_int(scores.get("cross_surface_convergence")) < 62
    )
    status = str(diagnostics.get("status", "")).strip().lower()
    verified_completion = status == "finished" and explicit_count > 0
    narrow_verified_signal = explicit_count > 0 and len(linked_workstreams or [str(snapshot.get("scope_id", "")).strip()]) <= SCOPED_FANOUT_CAP
    feature_vector = {
        "has_any_signal": bool(
            explicit_count
            or synthetic_count
            or changed_artifacts
            or code_references
            or str(evidence.get("latest_event_ts_iso", "")).strip()
        ),
        "explicit_count": explicit_count,
        "synthetic_count": synthetic_count,
        "decision_count": decision_count,
        "implementation_count": implementation_count,
        "meaningful_change_count": len(changed_artifacts) + len(code_references),
        "generated_only_churn": generated_only and explicit_count == 0 and implementation_count == 0 and decision_count == 0,
        "governance_only_local_change": governance_only and explicit_count == 0,
        "broad_fanout": len(linked_workstreams) > SCOPED_FANOUT_CAP,
        "verified_completion": verified_completion,
        "narrow_verified_signal": narrow_verified_signal,
        "meaningful_scope_activity": has_meaningful_change and (decision_count > 0 or implementation_count > 0 or explicit_count > 0),
        "decision_evidence": decision_count > 0,
        "implementation_evidence": implementation_count > 0,
        "open_warning": (
            basis == "inferred"
            or _normalize_bool(diagnostics.get("live_actionable"))
            or str(status).strip() == "finished" and closeout_signal == "direct_activity_drift"
            or _scope_has_posture_problem(snapshot=snapshot, control_posture=control_posture)
        ),
        "cross_surface_conflict": cross_surface_conflict,
        "stale_authority": stale_diagram or freshness == "stale",
        "unsafe_closeout": closeout_signal == "direct_activity_drift",
        "proof_blocker": bool(current_blocker) and not proof_state.frontier_has_advanced(proof_row),
        "proof_status": proof_status,
        "frontier_phase": frontier_phase,
        "linked_child_count": len(child_keys),
        "linked_surface_count": linked_surface_count,
        "blast_radius_class": blast_radius_class,
    }
    return feature_vector, child_signals


def _scope_has_posture_problem(*, snapshot: Mapping[str, Any], control_posture: Mapping[str, Any]) -> bool:
    policy = control_posture.get("policy", {}) if isinstance(control_posture.get("policy"), Mapping) else {}
    breaches = policy.get("breaches", []) if isinstance(policy.get("breaches"), list) else []
    recommendations = control_posture.get("recommendations", []) if isinstance(control_posture.get("recommendations"), list) else []
    workstreams = {
        str(token).strip()
        for token in snapshot.get("evidence_context", {}).get("linked_workstreams", [])
        if isinstance(snapshot.get("evidence_context"), Mapping)
        and isinstance(snapshot.get("evidence_context", {}).get("linked_workstreams"), list)
        and str(token).strip()
    }
    if str(snapshot.get("scope_type", "")).strip() == "workstream":
        token = str(snapshot.get("scope_id", "")).strip()
        if token:
            workstreams.add(token)
    for rows in (breaches, recommendations):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            status = str(row.get("status", "")).strip().lower()
            if rows is recommendations and status == "verified":
                continue
            row_workstreams = {
                str(token).strip()
                for token in row.get("workstreams", [])
                if str(token).strip()
            } if isinstance(row.get("workstreams"), list) else set()
            singular = str(row.get("workstream", "")).strip()
            if singular:
                row_workstreams.add(singular)
            if workstreams & row_workstreams:
                return True
    return False


def annotate_delivery_scope_signals(
    *,
    scopes: Sequence[Mapping[str, Any]],
    control_posture: Mapping[str, Any],
) -> list[dict[str, Any]]:
    prepared = [dict(snapshot) for snapshot in scopes]
    scope_lookup = {
        str(snapshot.get("scope_key", "")).strip(): snapshot
        for snapshot in prepared
        if str(snapshot.get("scope_key", "")).strip()
    }

    # Evaluate leaf scopes first so parent rollups can use child signals.
    ordered = sorted(
        prepared,
        key=lambda snapshot: {"workstream": 0, "component": 1, "diagram": 1, "surface": 2, "grid": 3}.get(
            str(snapshot.get("scope_type", "")).strip(),
            9,
        ),
    )
    for snapshot in ordered:
        features, child_signals = _delivery_feature_vector(
            snapshot=snapshot,
            scope_lookup=scope_lookup,
            control_posture=control_posture,
        )
        snapshot["scope_signal"] = build_scope_signal(
            feature_vector=features,
            child_signals=child_signals,
        )
    return prepared


def compass_window_scope_signal(
    *,
    scope_id: str,
    workstream_row: Mapping[str, Any],
    delivery_snapshot: Mapping[str, Any] | None,
    has_any_window_signal: bool,
    verified_completion: bool,
    verified_row_count: int,
    broad_fanout_only: bool,
    governance_only_local_change: bool,
    window_active: bool,
) -> dict[str, Any]:
    delivery_signal = (
        dict(delivery_snapshot.get("scope_signal", {}))
        if isinstance(delivery_snapshot, Mapping) and isinstance(delivery_snapshot.get("scope_signal"), Mapping)
        else {}
    )
    delivery_rank = scope_signal_rank(delivery_signal)
    verified_local = bool(verified_completion or verified_row_count > 0)
    if not verified_local:
        return build_scope_signal(
            feature_vector={
                "has_any_signal": has_any_window_signal,
                "window_inactive": not has_any_window_signal,
                "governance_only_local_change": governance_only_local_change,
                "broad_fanout": broad_fanout_only,
            }
        )
    feature_vector = {
        "has_any_signal": has_any_window_signal or verified_local,
        "verified_completion": verified_completion,
        "narrow_verified_signal": verified_row_count > 0,
        "meaningful_scope_activity": window_active,
        "decision_evidence": False,
        "implementation_evidence": str(workstream_row.get("status", "")).strip() in {"planning", "implementation"},
        "open_warning": delivery_rank >= 4 and scope_signal_rank(delivery_signal) < 5,
        "cross_surface_conflict": str(delivery_signal.get("token", "")).strip() == "actionable_priority"
        and "cross-surface" in " ".join(str(item) for item in delivery_signal.get("reasons", [])),
        "stale_authority": any("stale" in str(item).lower() for item in delivery_signal.get("reasons", [])),
        "unsafe_closeout": any("closeout" in str(item).lower() for item in delivery_signal.get("reasons", [])),
        "proof_blocker": delivery_rank >= 5,
    }
    return build_scope_signal(feature_vector=feature_vector)
