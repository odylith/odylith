from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.execution_engine import runtime_lane_policy

def bind(host_module: Any) -> None:
    globals().update({
        "RouterProfile": getattr(host_module, "RouterProfile"),
        "TaskAssessment": getattr(host_module, "TaskAssessment"),
        "TuningState": getattr(host_module, "TuningState"),
        "_mapping_value": getattr(host_module, "_mapping_value"),
        "_context_lookup": getattr(host_module, "_context_lookup"),
        "_context_signal_bool": getattr(host_module, "_context_signal_bool"),
        "_execution_profile_candidate": getattr(host_module, "_execution_profile_candidate"),
        "_synthesized_execution_profile_candidate": getattr(host_module, "_synthesized_execution_profile_candidate"),
        "_router_profile_from_token": getattr(host_module, "_router_profile_from_token"),
        "_router_profile_from_runtime": getattr(host_module, "_router_profile_from_runtime"),
        "_agent_role_for_assessment": getattr(host_module, "_agent_role_for_assessment"),
        "_normalize_token": getattr(host_module, "_normalize_token"),
        "_clamp_score": getattr(host_module, "_clamp_score"),
        "_normalized_rate": getattr(host_module, "_normalized_rate"),
        "_RUNTIME_EARNED_DEPTH_SELECTION_MODES": getattr(host_module, "_RUNTIME_EARNED_DEPTH_SELECTION_MODES"),
        "_RUNTIME_SUPPORT_SELECTION_MODES": getattr(host_module, "_RUNTIME_SUPPORT_SELECTION_MODES"),
        "_PROFILE_PRIORITY": getattr(host_module, "_PROFILE_PRIORITY"),
        "_tuning_bias_for_profile": getattr(host_module, "_tuning_bias_for_profile"),
        "_profile_reliability_summary": getattr(host_module, "_profile_reliability_summary"),
        "_sanitize_user_facing_text": getattr(host_module, "_sanitize_user_facing_text"),
        "_sanitize_user_facing_lines": getattr(host_module, "_sanitize_user_facing_lines"),
    })


def _execution_profile_mapping(
    *,
    root: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    evidence_pack: Mapping[str, Any],
    optimization_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    latest_packet = _mapping_value(optimization_snapshot, "latest_packet")
    optimization_latest_profile = {
        key: value
        for key, value in {
            "profile": str(_context_lookup(latest_packet, "odylith_execution_profile") or "").strip(),
            "model": str(_context_lookup(latest_packet, "odylith_execution_model") or "").strip(),
            "reasoning_effort": str(_context_lookup(latest_packet, "odylith_execution_reasoning_effort") or "").strip(),
            "agent_role": str(_context_lookup(latest_packet, "odylith_execution_agent_role") or "").strip(),
            "selection_mode": str(_context_lookup(latest_packet, "odylith_execution_selection_mode") or "").strip(),
            "delegate_preference": str(_context_lookup(latest_packet, "odylith_execution_delegate_preference") or "").strip(),
            "source": (
                str(_context_lookup(latest_packet, "odylith_execution_source") or "optimization_snapshot_latest_packet").strip()
                if latest_packet
                else ""
            ),
            "confidence": {
                "score": int(_context_lookup(latest_packet, "odylith_execution_confidence_score") or 0),
                "level": str(_context_lookup(latest_packet, "odylith_execution_confidence_level") or "").strip(),
            },
            "constraints": {
                "route_ready": _context_signal_bool(_context_lookup(latest_packet, "odylith_execution_route_ready")),
                "narrowing_required": _context_signal_bool(
                    _context_lookup(latest_packet, "odylith_execution_narrowing_required")
                ),
                "spawn_worthiness": int(_context_lookup(latest_packet, "odylith_execution_spawn_worthiness") or 0),
                "merge_burden": int(_context_lookup(latest_packet, "odylith_execution_merge_burden") or 0),
                "reasoning_mode": str(_context_lookup(latest_packet, "odylith_execution_reasoning_mode") or "").strip(),
            }
            if latest_packet
            else {},
        }.items()
        if (
            value not in ("", [], {}, None)
            and (
                key not in {"confidence", "constraints"}
                or (
                    key == "confidence"
                    and (int(value.get("score", 0) or 0) > 0 or str(value.get("level", "")).strip())
                )
                or (
                    key == "constraints"
                    and any(subvalue not in ("", [], {}, None, 0, False) for subvalue in value.values())
                )
            )
        )
    }
    candidates = (
        _execution_profile_candidate(root.get("odylith_execution_profile")),
        _execution_profile_candidate(root.get("execution_profile")),
        _execution_profile_candidate(context_packet.get("execution_profile")),
        _execution_profile_candidate(_context_lookup(evidence_pack, "routing_handoff", "odylith_execution_profile")),
        _execution_profile_candidate(_context_lookup(evidence_pack, "routing_handoff", "execution_profile")),
        _execution_profile_candidate(optimization_snapshot.get("execution_profile")),
        _execution_profile_candidate(_context_lookup(optimization_snapshot, "latest_packet", "odylith_execution_profile")),
        optimization_latest_profile,
    )
    scored_candidates: list[tuple[int, int, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        if not candidate:
            continue
        confidence = dict(candidate.get("confidence", {})) if isinstance(candidate.get("confidence"), Mapping) else {}
        constraints = dict(candidate.get("constraints", {})) if isinstance(candidate.get("constraints"), Mapping) else {}
        richness = sum(
            1
            for key in ("profile", "model", "reasoning_effort", "agent_role", "selection_mode", "delegate_preference", "source")
            if str(candidate.get(key, "")).strip()
        )
        if confidence:
            richness += sum(
                1 for key in ("score", "level") if str(confidence.get(key, "")).strip() or int(confidence.get(key, 0) or 0) > 0
            )
        if constraints:
            richness += sum(1 for value in constraints.values() if value not in ("", [], {}, None, False))
        scored_candidates.append((richness, index, candidate))
    if not scored_candidates:
        return _synthesized_execution_profile_candidate(context_packet=context_packet)
    merged: dict[str, Any] = {}
    for _, _, candidate in sorted(scored_candidates, key=lambda item: (item[0], item[1])):
        for key, value in candidate.items():
            if value in ("", [], {}, None, False):
                continue
            if isinstance(value, Mapping):
                existing = dict(merged.get(key, {})) if isinstance(merged.get(key), Mapping) else {}
                merged[key] = {
                    **existing,
                    **{subkey: subvalue for subkey, subvalue in value.items() if subvalue not in ("", [], {}, None, False)},
                }
                continue
            merged[key] = value
    profile = _router_profile_from_token(merged.get("profile"))
    if profile is None:
        profile = _router_profile_from_runtime(merged.get("model"), merged.get("reasoning_effort"))
        if profile is not None:
            merged["profile"] = profile.value
    if profile is not None:
        merged["model"] = profile.model
        merged["reasoning_effort"] = profile.reasoning_effort
    if not str(merged.get("profile", "")).strip():
        synthesized = _synthesized_execution_profile_candidate(context_packet=context_packet)
        if synthesized:
            merged = {**synthesized, **merged}
    return merged


def _preferred_router_profile_from_execution_profile(profile: Mapping[str, Any]) -> RouterProfile | None:
    explicit = _router_profile_from_token(profile.get("profile"))
    if explicit is not None:
        return explicit
    return _router_profile_from_runtime(
        profile.get("model"),
        profile.get("reasoning_effort"),
    )


def _decision_odylith_execution_profile(
    *,
    assessment: TaskAssessment,
    selected: RouterProfile | None = None,
) -> dict[str, Any]:
    summary = dict(assessment.context_signal_summary or {})
    recommended_profile = str(summary.get("odylith_execution_profile", "")).strip()
    if not recommended_profile:
        return {}
    payload = {
        "recommended_profile": recommended_profile,
        "recommended_model": str(summary.get("odylith_execution_model", "")).strip(),
        "recommended_reasoning_effort": str(summary.get("odylith_execution_reasoning_effort", "")).strip(),
        "recommended_agent_role": str(summary.get("odylith_execution_agent_role", "")).strip(),
        "source": str(summary.get("odylith_execution_source", "")).strip(),
        "selection_mode": str(summary.get("odylith_execution_selection_mode", "")).strip(),
        "delegate_preference": str(summary.get("odylith_execution_delegate_preference", "")).strip(),
        "confidence": {
            "score": int(summary.get("odylith_execution_confidence_score", 0) or 0),
            "level": str(summary.get("odylith_execution_confidence_level", "")).strip(),
        },
    }
    if selected is not None and selected is not RouterProfile.MAIN_THREAD:
        payload.update(
            {
                "selected_profile": selected.value,
                "selected_model": selected.model,
                "selected_reasoning_effort": selected.reasoning_effort,
                "selected_agent_role": _agent_role_for_assessment(assessment, profile=selected),
            }
        )
    return {key: value for key, value in payload.items() if value not in ("", [], {}, None)}


def _odylith_execution_guard_reason(assessment: TaskAssessment) -> str:
    summary = dict(assessment.context_signal_summary or {})
    governance_guard = runtime_lane_policy.delegation_guard(summary)
    if governance_guard.blocked:
        return governance_guard.reason
    recommended = _router_profile_from_token(summary.get("odylith_execution_profile", ""))
    confidence = _clamp_score(summary.get("odylith_execution_confidence_score", 0) or 0)
    source = _normalize_token(summary.get("odylith_execution_source", ""))
    if source not in {"odylith_runtime_packet", "odylith_runtime"}:
        return ""
    if confidence < 3:
        return ""
    delegate_preference = _normalize_token(summary.get("odylith_execution_delegate_preference", ""))
    route_ready = bool(summary.get("route_ready") or summary.get("odylith_execution_route_ready"))
    native_spawn_ready = bool(summary.get("native_spawn_ready"))
    narrowing_required = bool(summary.get("narrowing_required") or summary.get("odylith_execution_narrowing_required"))
    spawn_worthiness = _clamp_score(summary.get("spawn_worthiness_score", 0) or summary.get("odylith_execution_spawn_worthiness", 0) or 0)
    merge_burden = _clamp_score(summary.get("merge_burden_score", 0) or summary.get("odylith_execution_merge_burden", 0) or 0)
    expected_delegation_value = _clamp_score(summary.get("expected_delegation_value_score", 0) or 0)
    ambiguity = _clamp_score(summary.get("odylith_execution_ambiguity_score", 0) or 0)
    selection_mode = _normalize_token(summary.get("odylith_execution_selection_mode", ""))
    if delegate_preference != "hold_local" and recommended is not RouterProfile.MAIN_THREAD:
        return ""
    if recommended is RouterProfile.MAIN_THREAD:
        return "the slice should stay in the main thread for now"
    if narrowing_required or selection_mode in {"narrow_first", "guarded_narrowing"}:
        return "the slice still needs local narrowing before delegation"
    if ambiguity >= 3 and expected_delegation_value <= 2 and not assessment.correctness_critical:
        return "the slice is still ambiguous enough that local narrowing is cheaper than early delegation"
    if not route_ready or not native_spawn_ready:
        return "the slice is not ready for delegation yet"
    if spawn_worthiness <= 1:
        return "the slice is still too small to benefit from delegation"
    if expected_delegation_value <= 1:
        return "the current slice does not yet justify delegated spend"
    if merge_burden >= 3 and not assessment.correctness_critical:
        return "the slice still needs local coordination before delegation"
    return ""


def _apply_odylith_execution_priors(
    *,
    scorecard: Mapping[str, float],
    assessment: TaskAssessment,
    allow_xhigh: bool,
) -> tuple[dict[str, float], list[str]]:
    summary = dict(assessment.context_signal_summary or {})
    recommended = _router_profile_from_token(summary.get("odylith_execution_profile", ""))
    confidence = _clamp_score(summary.get("odylith_execution_confidence_score", 0) or 0)
    if recommended is None or recommended is RouterProfile.MAIN_THREAD or confidence <= 0:
        return {key: float(value) for key, value in scorecard.items()}, []
    if recommended is RouterProfile.GPT54_XHIGH and not allow_xhigh:
        recommended = RouterProfile.GPT54_HIGH
    adjusted = {key: float(value) for key, value in scorecard.items()}
    if recommended.value not in adjusted:
        return adjusted, []
    route_ready = bool(summary.get("route_ready") or summary.get("odylith_execution_route_ready"))
    native_spawn_ready = bool(summary.get("native_spawn_ready"))
    narrowing_required = bool(summary.get("narrowing_required") or summary.get("odylith_execution_narrowing_required"))
    support_leaf = bool(summary.get("support_leaf"))
    selection_mode = _normalize_token(summary.get("odylith_execution_selection_mode", ""))
    delegate_preference = _normalize_token(summary.get("odylith_execution_delegate_preference", ""))
    spawn_worthiness = _clamp_score(summary.get("spawn_worthiness_score", 0) or summary.get("odylith_execution_spawn_worthiness", 0) or 0)
    merge_burden = _clamp_score(summary.get("merge_burden_score", 0) or summary.get("odylith_execution_merge_burden", 0) or 0)
    reasoning_readiness = _clamp_score(summary.get("reasoning_readiness_score", 0) or 0)
    context_density = _clamp_score(summary.get("context_density_score", 0) or 0)
    evidence_diversity = _clamp_score(summary.get("evidence_diversity_score", 0) or 0)
    expected_delegation_value = _clamp_score(summary.get("expected_delegation_value_score", 0) or 0)
    ambiguity = _clamp_score(summary.get("odylith_execution_ambiguity_score", 0) or 0)
    history_within_budget_rate = _normalized_rate(summary.get("optimization_within_budget_rate", 0.0))
    history_route_ready_rate = _normalized_rate(summary.get("optimization_route_ready_rate", 0.0))
    history_native_spawn_ready_rate = _normalized_rate(summary.get("optimization_native_spawn_ready_rate", 0.0))
    history_deep_reasoning_ready_rate = _normalized_rate(summary.get("optimization_deep_reasoning_ready_rate", 0.0))
    history_delegated_lane_rate = _normalized_rate(summary.get("optimization_delegated_lane_rate", 0.0))
    history_hold_local_rate = _normalized_rate(summary.get("optimization_hold_local_rate", 0.0))
    history_runtime_backed_execution_rate = _normalized_rate(
        summary.get("optimization_runtime_backed_execution_rate", 0.0)
    )
    history_high_execution_confidence_rate = _normalized_rate(
        summary.get("optimization_high_execution_confidence_rate", 0.0)
    )
    history_effective_yield_score = max(
        0.0,
        min(1.0, float(summary.get("optimization_avg_effective_yield_score", 0.0) or 0.0)),
    )
    history_high_yield_rate = _normalized_rate(summary.get("optimization_high_yield_rate", 0.0))
    history_reliable_high_yield_rate = _normalized_rate(
        summary.get("optimization_reliable_high_yield_rate", 0.0)
    )
    history_yield_state = _normalize_token(summary.get("optimization_yield_state", ""))
    history_packet_alignment_rate = _normalized_rate(summary.get("optimization_packet_alignment_rate", 0.0))
    history_reliable_packet_alignment_rate = _normalized_rate(
        summary.get("optimization_reliable_packet_alignment_rate", 0.0)
    )
    history_packet_alignment_state = _normalize_token(summary.get("optimization_packet_alignment_state", ""))
    history_latency_pressure_score = _clamp_score(summary.get("optimization_latency_pressure_score", 0) or 0)
    control_advisory_state = _normalize_token(summary.get("control_advisory_state", ""))
    control_advisory_confidence = _clamp_score(summary.get("control_advisory_confidence_score", 0) or 0)
    control_advisory_reasoning_mode = _normalize_token(summary.get("control_advisory_reasoning_mode", ""))
    control_advisory_depth = _normalize_token(summary.get("control_advisory_depth", ""))
    control_advisory_delegation = _normalize_token(summary.get("control_advisory_delegation", ""))
    control_advisory_parallelism = _normalize_token(summary.get("control_advisory_parallelism", ""))
    control_advisory_packet_strategy = _normalize_token(summary.get("control_advisory_packet_strategy", ""))
    control_advisory_budget_mode = _normalize_token(summary.get("control_advisory_budget_mode", ""))
    control_advisory_retrieval_focus = _normalize_token(summary.get("control_advisory_retrieval_focus", ""))
    control_advisory_speed_mode = _normalize_token(summary.get("control_advisory_speed_mode", ""))
    control_advisory_freshness_bucket = _normalize_token(summary.get("control_advisory_freshness_bucket", ""))
    control_advisory_evidence_strength = _clamp_score(summary.get("control_advisory_evidence_strength_score", 0) or 0)
    control_advisory_signal_conflict = bool(summary.get("control_advisory_signal_conflict"))
    advisory_present = bool(
        control_advisory_state
        or control_advisory_reasoning_mode
        or control_advisory_depth
        or control_advisory_delegation
        or control_advisory_parallelism
        or control_advisory_packet_strategy
        or control_advisory_budget_mode
        or control_advisory_retrieval_focus
        or control_advisory_speed_mode
        or control_advisory_freshness_bucket
        or control_advisory_confidence > 0
        or control_advisory_evidence_strength > 0
        or control_advisory_signal_conflict
    )
    advisory_reliable = bool(
        advisory_present
        and
        control_advisory_confidence >= 3
        and control_advisory_evidence_strength >= 3
        and control_advisory_freshness_bucket in {"fresh", "recent"}
        and not control_advisory_signal_conflict
        and history_packet_alignment_state not in {"drifting"}
        and (history_reliable_packet_alignment_rate == 0.0 or history_reliable_packet_alignment_rate >= 0.7)
    )
    advisory_guarded = bool(
        advisory_present
        and (
            control_advisory_freshness_bucket in {"aging", "stale"}
            or control_advisory_evidence_strength <= 1
            or control_advisory_signal_conflict
            or history_packet_alignment_state == "drifting"
            or (history_reliable_packet_alignment_rate > 0.0 and history_reliable_packet_alignment_rate < 0.7)
        )
    )
    runtime_depth_mode = selection_mode in _RUNTIME_EARNED_DEPTH_SELECTION_MODES
    runtime_support_mode = selection_mode in _RUNTIME_SUPPORT_SELECTION_MODES

    recommended_delta = 0.18 * confidence
    if route_ready:
        recommended_delta += 0.12
    if native_spawn_ready:
        recommended_delta += 0.08
    if not narrowing_required:
        recommended_delta += 0.06
    if runtime_depth_mode:
        recommended_delta += 0.08
    if runtime_support_mode:
        recommended_delta += 0.04
    if reasoning_readiness >= 3 and context_density >= 2:
        recommended_delta += 0.08
    if evidence_diversity >= 2:
        recommended_delta += 0.04
    if expected_delegation_value >= 3:
        recommended_delta += 0.1
    elif expected_delegation_value <= 1:
        recommended_delta -= 0.08
    if ambiguity >= 3 and not assessment.correctness_critical:
        recommended_delta -= 0.08
    if history_within_budget_rate >= 0.75:
        recommended_delta += 0.06
    if history_route_ready_rate >= 0.5:
        recommended_delta += 0.04
    if history_native_spawn_ready_rate >= 0.5:
        recommended_delta += 0.04
    if history_deep_reasoning_ready_rate >= 0.5 and reasoning_readiness >= 3:
        recommended_delta += 0.06
    if history_runtime_backed_execution_rate >= 0.5:
        recommended_delta += 0.04
    if history_high_execution_confidence_rate >= 0.5:
        recommended_delta += 0.04
    if assessment.earned_depth >= 3:
        recommended_delta += 0.08
    elif assessment.earned_depth <= 1 and not assessment.correctness_critical:
        recommended_delta -= 0.04
    if assessment.delegation_readiness >= 3:
        recommended_delta += 0.08
    elif assessment.delegation_readiness <= 1 and not assessment.correctness_critical:
        recommended_delta -= 0.08
    if history_effective_yield_score >= 0.72 and history_high_yield_rate >= 0.6:
        recommended_delta += 0.06
    elif history_yield_state == "wasteful":
        recommended_delta -= 0.12
    if history_packet_alignment_rate >= 0.75:
        recommended_delta += 0.04
    elif history_packet_alignment_state == "drifting":
        recommended_delta -= 0.12
    if (
        control_advisory_depth == "promote_when_grounded"
        and advisory_reliable
        and route_ready
        and not narrowing_required
    ):
        recommended_delta += 0.08
    if control_advisory_reasoning_mode == "earn_depth" and advisory_reliable and context_density >= 3 and reasoning_readiness >= 3:
        recommended_delta += 0.06
    if (
        control_advisory_delegation == "runtime_backed_delegate"
        and advisory_reliable
        and expected_delegation_value >= 3
    ):
        recommended_delta += 0.05
    if advisory_guarded:
        recommended_delta -= 0.16
    adjusted[recommended.value] = round(adjusted[recommended.value] + recommended_delta, 3)
    if history_packet_alignment_state == "drifting" and not assessment.correctness_critical:
        adjusted[recommended.value] = round(adjusted[recommended.value] - (0.55 * confidence), 3)
    if history_yield_state == "wasteful" and not assessment.correctness_critical:
        adjusted[recommended.value] = round(adjusted[recommended.value] - (0.45 * confidence), 3)

    if delegate_preference == "hold_local" or control_advisory_delegation == "hold_local_bias":
        global_penalty = 0.09 * confidence
        if not route_ready:
            global_penalty += 0.12
        if narrowing_required:
            global_penalty += 0.08
        if spawn_worthiness <= 1:
            global_penalty += 0.05
        if history_hold_local_rate > history_delegated_lane_rate:
            global_penalty += 0.06
        if control_advisory_confidence >= 3:
            global_penalty += 0.05
        for profile_key in list(adjusted):
            adjusted[profile_key] = round(adjusted[profile_key] - global_penalty, 3)
        adjusted[recommended.value] = round(adjusted[recommended.value] + (global_penalty * 0.6), 3)

    if support_leaf or runtime_support_mode:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - (0.08 * max(confidence, 1)), 3)
        for profile_key in (RouterProfile.SPARK_MEDIUM.value, RouterProfile.MINI_MEDIUM.value, RouterProfile.MINI_HIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.05 * max(confidence, 1), 3)

    if merge_burden >= 3:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.1, 3)
    if spawn_worthiness <= 1:
        for profile_key in adjusted:
            adjusted[profile_key] = round(adjusted[profile_key] - 0.05, 3)
    if control_advisory_depth == "narrow_first" or control_advisory_reasoning_mode == "guarded_narrowing":
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.1, 3)
        for profile_key in (RouterProfile.CODEX_MEDIUM.value, RouterProfile.CODEX_HIGH.value, RouterProfile.MINI_HIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.04, 3)
    if control_advisory_packet_strategy == "precision_first" and context_density <= 2:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.08, 3)
    if control_advisory_budget_mode == "tight" and not assessment.correctness_critical:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.09, 3)
        for profile_key in (RouterProfile.SPARK_MEDIUM.value, RouterProfile.CODEX_MEDIUM.value, RouterProfile.CODEX_HIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.04, 3)
    if (
        control_advisory_budget_mode == "spend_when_grounded"
        and advisory_reliable
        and route_ready
        and reasoning_readiness >= 3
        and context_density >= 3
    ):
        for profile_key in (RouterProfile.CODEX_HIGH.value, RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.04, 3)
    if control_advisory_speed_mode == "accelerate_grounded" and advisory_reliable and route_ready and native_spawn_ready and not assessment.correctness_critical:
        for profile_key in (RouterProfile.SPARK_MEDIUM.value, RouterProfile.CODEX_MEDIUM.value, RouterProfile.CODEX_HIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.03, 3)
    if control_advisory_speed_mode == "conserve" and not assessment.correctness_critical:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.06, 3)
    if history_within_budget_rate < 0.5 and history_deep_reasoning_ready_rate < 0.5:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.12, 3)
        for profile_key in (RouterProfile.CODEX_MEDIUM.value, RouterProfile.CODEX_HIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.05, 3)
    if history_latency_pressure_score >= 3 and not assessment.correctness_critical:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.08, 3)
        for profile_key in (RouterProfile.SPARK_MEDIUM.value, RouterProfile.MINI_MEDIUM.value, RouterProfile.CODEX_MEDIUM.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.04, 3)
    if history_packet_alignment_state == "drifting":
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.14, 3)
        for profile_key in (RouterProfile.SPARK_MEDIUM.value, RouterProfile.MINI_HIGH.value, RouterProfile.CODEX_MEDIUM.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.05, 3)
    if advisory_guarded:
        for profile_key in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] - 0.16, 3)
        for profile_key in (RouterProfile.MINI_HIGH.value, RouterProfile.CODEX_MEDIUM.value, RouterProfile.CODEX_HIGH.value):
            if profile_key in adjusted:
                adjusted[profile_key] = round(adjusted[profile_key] + 0.05, 3)
        if recommended.value in (RouterProfile.GPT54_HIGH.value, RouterProfile.GPT54_XHIGH.value):
            adjusted[recommended.value] = round(adjusted[recommended.value] - 0.12, 3)

    note_parts = [f"`{recommended.value}` guidance", f"confidence={confidence}"]
    if selection_mode:
        note_parts.append(f"mode={selection_mode}")
    if route_ready and not narrowing_required:
        note_parts.append("delegation_ready")
    if narrowing_required:
        note_parts.append("needs_narrowing")
    if support_leaf:
        note_parts.append("support_slice")
    if history_within_budget_rate >= 0.75:
        note_parts.append(f"budget_rate={round(history_within_budget_rate, 2)}")
    if history_deep_reasoning_ready_rate >= 0.5:
        note_parts.append(f"deep_ready_rate={round(history_deep_reasoning_ready_rate, 2)}")
    if history_hold_local_rate > history_delegated_lane_rate and history_hold_local_rate >= 0.5:
        note_parts.append(f"local_rate={round(history_hold_local_rate, 2)}")
    if history_yield_state == "wasteful":
        note_parts.append("yield=wasteful")
    if history_packet_alignment_state == "drifting":
        note_parts.append("execution_fit=unstable")
    return adjusted, [
        _sanitize_user_facing_text(
            f"Measured execution guidance adjusted tier scoring ({', '.join(note_parts)})"
        )
    ]


def _score_profile(profile: RouterProfile, assessment: TaskAssessment, tuning: TuningState) -> float:
    tuning_bias = _tuning_bias_for_profile(profile, assessment, tuning)
    if profile is RouterProfile.MINI_MEDIUM:
        return (
            (1.1 * assessment.ambiguity)
            + (0.9 * assessment.context_breadth)
            + (0.8 * assessment.requested_depth)
            + (0.4 * assessment.earned_depth if not assessment.needs_write else -0.8 * assessment.earned_depth)
            + (0.7 * assessment.acceptance_clarity)
            + (0.7 * assessment.artifact_specificity)
            + (0.6 * assessment.validation_clarity)
            + (0.2 * assessment.delegation_readiness if not assessment.needs_write else -0.5 * assessment.delegation_readiness)
            + (1.4 if not assessment.needs_write and assessment.task_kind in {"analysis", "review"} else 0.0)
            - (1.5 if assessment.needs_write else 0.0)
            - (1.0 * assessment.blast_radius)
            - (1.0 * assessment.reversibility_risk)
            - (0.8 * assessment.accuracy_bias)
            - (0.7 * assessment.latency_pressure)
            + tuning_bias
        )
    if profile is RouterProfile.MINI_HIGH:
        return (
            (1.5 * assessment.ambiguity)
            + (1.2 * assessment.context_breadth)
            + (1.3 * assessment.requested_depth)
            + (0.7 * assessment.earned_depth if not assessment.needs_write else -0.9 * assessment.earned_depth)
            + (1.0 * assessment.acceptance_clarity)
            + (0.8 * assessment.artifact_specificity)
            + (0.7 * assessment.validation_clarity)
            + (0.3 * assessment.delegation_readiness if not assessment.needs_write else -0.6 * assessment.delegation_readiness)
            + (1.5 if not assessment.needs_write and assessment.task_kind in {"analysis", "review"} else 0.0)
            - (1.3 if assessment.needs_write else 0.0)
            - (0.8 * assessment.latency_pressure)
            - (0.7 * assessment.mechanicalness)
            + tuning_bias
        )
    if profile is RouterProfile.SPARK_MEDIUM:
        return (
            (2.4 * assessment.mechanicalness)
            + (1.8 * assessment.latency_pressure)
            + (1.0 * assessment.write_scope_clarity)
            + (0.8 * assessment.acceptance_clarity)
            + (0.6 * assessment.validation_clarity)
            + (0.5 * assessment.artifact_specificity)
            - (0.9 * assessment.earned_depth)
            - (0.8 * assessment.delegation_readiness)
            - (1.6 * assessment.ambiguity)
            - (1.5 * assessment.blast_radius)
            - (1.3 * assessment.context_breadth)
            - (1.4 * assessment.reversibility_risk)
            - (1.2 * assessment.requested_depth)
            - (1.5 * assessment.accuracy_bias)
            - (1.5 if assessment.feature_implementation else 0.0)
            - (1.2 if assessment.correctness_critical else 0.0)
            - (2.5 if not assessment.needs_write else 0.0)
            + tuning_bias
        )
    if profile is RouterProfile.CODEX_MEDIUM:
        return (
            (1.2 * assessment.write_scope_clarity if assessment.needs_write else 0.0)
            + (1.0 * assessment.acceptance_clarity)
            + (0.9 * assessment.validation_clarity)
            + (0.8 * assessment.artifact_specificity)
            + (0.8 * assessment.earned_depth)
            + (0.9 * assessment.delegation_readiness)
            + (0.7 * assessment.mechanicalness)
            + (0.6 if assessment.needs_write else -3.6)
            + (0.7 if assessment.task_family == "bounded_bugfix" and assessment.needs_write else 0.0)
            - (0.9 * assessment.ambiguity)
            - (1.0 * assessment.blast_radius)
            - (0.8 * assessment.context_breadth)
            - (0.9 * assessment.reversibility_risk)
            - (0.8 * assessment.requested_depth)
            - (0.6 * assessment.latency_pressure)
            - (0.9 if assessment.correctness_critical else 0.0)
            + tuning_bias
        )
    if profile is RouterProfile.CODEX_HIGH:
        return (
            (1.5 * assessment.ambiguity)
            + (1.2 * assessment.blast_radius)
            + (1.1 * assessment.context_breadth)
            + (1.2 * assessment.requested_depth)
            + (1.1 * assessment.accuracy_bias)
            + (1.2 * assessment.earned_depth)
            + (1.0 * assessment.delegation_readiness)
            + (1.0 * assessment.reversibility_risk)
            + (0.8 * assessment.write_scope_clarity if assessment.needs_write else 0.0)
            + (0.9 * assessment.acceptance_clarity)
            + (0.9 * assessment.validation_clarity)
            + (0.6 * assessment.artifact_specificity)
            + (1.0 if assessment.feature_implementation else 0.0)
            + (0.6 if assessment.needs_write else -2.5)
            - (0.5 if assessment.delegation_readiness <= 1 and not assessment.correctness_critical else 0.0)
            - (0.5 * assessment.latency_pressure)
            + tuning_bias
        )
    if profile is RouterProfile.GPT54_HIGH:
        return (
            (1.8 * assessment.ambiguity)
            + (1.6 * assessment.blast_radius)
            + (1.5 * assessment.context_breadth)
            + (1.6 * assessment.requested_depth)
            + (1.6 * assessment.reversibility_risk)
            + (1.7 * assessment.accuracy_bias)
            + (1.4 * assessment.earned_depth)
            + (0.8 * assessment.delegation_readiness)
            + (0.9 * assessment.acceptance_clarity)
            + (0.9 * assessment.validation_clarity)
            + (0.5 * assessment.artifact_specificity)
            + (1.2 if assessment.feature_implementation else 0.0)
            + (1.1 if assessment.correctness_critical else 0.0)
            + (0.8 if assessment.task_family in {"bounded_feature", "critical_change"} else 0.0)
            + (0.4 if assessment.needs_write else -0.5 if assessment.correctness_critical else -2.5)
            - (0.8 if assessment.delegation_readiness <= 1 and not assessment.correctness_critical else 0.0)
            - (0.3 * assessment.latency_pressure)
            + tuning_bias
        )
    if profile is RouterProfile.GPT54_XHIGH:
        return (
            (2.2 * assessment.ambiguity)
            + (2.0 * assessment.blast_radius)
            + (1.8 * assessment.context_breadth)
            + (2.1 * assessment.requested_depth)
            + (2.1 * assessment.reversibility_risk)
            + (1.8 * assessment.accuracy_bias)
            + (1.5 * assessment.earned_depth)
            + (0.8 * assessment.delegation_readiness)
            + (1.0 * assessment.acceptance_clarity)
            + (1.0 * assessment.validation_clarity)
            + (1.2 if assessment.correctness_critical else 0.0)
            + (1.0 if assessment.task_family in {"bounded_feature", "critical_change"} else 0.0)
            - (0.9 if assessment.delegation_readiness <= 1 and not assessment.correctness_critical else 0.0)
        )
    return -9999.0


def _score_margin(selected: RouterProfile, scorecard: Mapping[str, float]) -> float:
    ordered = sorted(scorecard.items(), key=lambda item: (item[1], _PROFILE_PRIORITY.get(item[0], 0)), reverse=True)
    if len(ordered) < 2:
        return round(float(scorecard.get(selected.value, 0.0) or 0.0), 3)
    for candidate, score in ordered:
        if candidate == selected.value:
            continue
        return round(float(scorecard.get(selected.value, 0.0) or 0.0) - float(score), 3)
    return 0.0


def _routing_confidence(selected: RouterProfile, assessment: TaskAssessment, scorecard: Mapping[str, float]) -> int:
    confidence = assessment.base_confidence
    margin = _score_margin(selected, scorecard)
    if margin >= 2.5:
        confidence += 1
    elif margin <= 0.75:
        confidence -= 1
    if assessment.correctness_critical and selected in {RouterProfile.GPT54_HIGH, RouterProfile.GPT54_XHIGH}:
        confidence += 1
    if assessment.feature_implementation and selected in {
        RouterProfile.MINI_MEDIUM,
        RouterProfile.MINI_HIGH,
        RouterProfile.SPARK_MEDIUM,
    }:
        confidence -= 1
    if (
        selected in {RouterProfile.CODEX_HIGH, RouterProfile.GPT54_HIGH, RouterProfile.GPT54_XHIGH}
        and assessment.earned_depth >= 3
        and assessment.delegation_readiness >= 3
    ):
        confidence += 1
    elif (
        selected in {RouterProfile.CODEX_HIGH, RouterProfile.GPT54_HIGH, RouterProfile.GPT54_XHIGH}
        and assessment.delegation_readiness <= 1
        and not assessment.correctness_critical
    ):
        confidence -= 1
    return _clamp_score(confidence)


def _apply_accuracy_backstop(
    *,
    selected: RouterProfile,
    assessment: TaskAssessment,
    scorecard: Mapping[str, float],
) -> tuple[RouterProfile, int, list[str]]:
    routing_confidence = _routing_confidence(selected, assessment, scorecard)
    lines: list[str] = []
    if (
        selected in {
            RouterProfile.MINI_MEDIUM,
            RouterProfile.MINI_HIGH,
            RouterProfile.SPARK_MEDIUM,
        }
        and assessment.needs_write
        and (assessment.accuracy_bias >= 2 or (assessment.earned_depth >= 3 and assessment.delegation_readiness >= 3))
        and routing_confidence <= 1
    ):
        upgraded = (
            RouterProfile.GPT54_HIGH
            if assessment.task_family == "critical_change" or assessment.correctness_critical
            else RouterProfile.CODEX_HIGH
            if assessment.task_family == "bounded_feature" or assessment.feature_implementation
            else RouterProfile.CODEX_MEDIUM
        )
        lines.append(
            f"confidence backstop promoted low-confidence write routing from `{selected.value}` to `{upgraded.value}` for accuracy"
        )
        selected = upgraded
        routing_confidence = _clamp_score(routing_confidence + 1)
    elif (
        selected is RouterProfile.CODEX_MEDIUM
        and assessment.needs_write
        and assessment.earned_depth >= 3
        and assessment.delegation_readiness >= 3
        and assessment.validation_clarity >= 2
        and routing_confidence <= 2
    ):
        upgraded = (
            RouterProfile.GPT54_HIGH
            if assessment.correctness_critical or assessment.task_family == "critical_change"
            else RouterProfile.CODEX_HIGH
        )
        lines.append(
            f"confidence backstop promoted grounded route-ready write work from `{selected.value}` to `{upgraded.value}`"
        )
        selected = upgraded
        routing_confidence = _clamp_score(routing_confidence + 1)
    elif (
        selected is RouterProfile.CODEX_MEDIUM
        and assessment.feature_implementation
        and assessment.accuracy_preference in {"accuracy", "max_accuracy", "maximum_accuracy"}
        and routing_confidence <= 1
    ):
        lines.append(
            "confidence backstop promoted low-confidence feature work from "
            f"`{RouterProfile.WRITE_MEDIUM.value}` to `{RouterProfile.WRITE_HIGH.value}`"
        )
        selected = RouterProfile.CODEX_HIGH
        routing_confidence = _clamp_score(routing_confidence + 1)
    elif (
        selected is RouterProfile.CODEX_HIGH
        and (assessment.correctness_critical or assessment.task_family == "critical_change")
        and routing_confidence <= 1
    ):
        lines.append(
            "confidence backstop promoted low-confidence critical work from "
            f"`{RouterProfile.WRITE_HIGH.value}` to `{RouterProfile.FRONTIER_HIGH.value}`"
        )
        selected = RouterProfile.GPT54_HIGH
        routing_confidence = _clamp_score(routing_confidence + 1)
    elif (
        selected is RouterProfile.MINI_MEDIUM
        and not assessment.needs_write
        and assessment.requested_depth >= 3
        and routing_confidence <= 1
    ):
        lines.append(
            "confidence backstop promoted low-confidence analysis from "
            f"`{RouterProfile.ANALYSIS_MEDIUM.value}` to `{RouterProfile.ANALYSIS_HIGH.value}`"
        )
        selected = RouterProfile.MINI_HIGH
        routing_confidence = _clamp_score(routing_confidence + 1)
    return selected, routing_confidence, lines


def _next_stronger_profile(profile: RouterProfile, assessment: TaskAssessment) -> RouterProfile:
    if profile in {RouterProfile.MINI_MEDIUM, RouterProfile.MINI_HIGH}:
        if assessment.needs_write:
            return (
                RouterProfile.GPT54_HIGH
                if assessment.correctness_critical or assessment.task_family == "critical_change"
                else RouterProfile.CODEX_HIGH
                if assessment.feature_implementation or assessment.task_family == "bounded_feature"
                else RouterProfile.CODEX_MEDIUM
            )
        return RouterProfile.MINI_HIGH if profile is RouterProfile.MINI_MEDIUM else RouterProfile.GPT54_HIGH
    if profile is RouterProfile.SPARK_MEDIUM:
        return (
            RouterProfile.GPT54_HIGH
            if assessment.correctness_critical or assessment.task_family == "critical_change"
            else RouterProfile.CODEX_HIGH
            if assessment.feature_implementation or assessment.accuracy_bias >= 2
            else RouterProfile.CODEX_MEDIUM
        )
    if profile is RouterProfile.CODEX_MEDIUM:
        return (
            RouterProfile.GPT54_HIGH
            if assessment.correctness_critical or assessment.task_family == "critical_change"
            else RouterProfile.CODEX_HIGH
        )
    if profile is RouterProfile.CODEX_HIGH and (
        assessment.correctness_critical or assessment.task_family == "critical_change"
    ):
        return RouterProfile.GPT54_HIGH
    return profile


def _apply_reliability_backstop(
    *,
    selected: RouterProfile,
    assessment: TaskAssessment,
    tuning: TuningState,
    routing_confidence: int,
) -> tuple[RouterProfile, int, list[str]]:
    summary = _profile_reliability_summary(selected, assessment, tuning)
    lines: list[str] = []
    if summary["total"] >= 2:
        lines.append(
            "reliability_history="
            f"{summary['posture']}[{summary['source']}] accepted={summary['accepted']} "
            f"failures={summary['failures']} severe_failures={summary['severe_failures']} "
            f"token_efficient={summary['token_efficient']}"
        )
    if summary["posture"] != "weak":
        return selected, routing_confidence, lines
    if not (
        assessment.needs_write
        or assessment.requested_depth >= 3
        or assessment.correctness_critical
        or assessment.feature_implementation
    ):
        return selected, routing_confidence, lines
    upgraded = _next_stronger_profile(selected, assessment)
    if upgraded is selected:
        return selected, routing_confidence, lines
    lines.append(
        f"reliability backstop promoted `{selected.value}` to `{upgraded.value}` because prior outcomes for this slice were weak"
    )
    return upgraded, _clamp_score(routing_confidence + 1), lines


def _apply_odylith_execution_alignment(
    *,
    selected: RouterProfile,
    assessment: TaskAssessment,
    scorecard: Mapping[str, float],
    routing_confidence: int,
    allow_xhigh: bool,
) -> tuple[RouterProfile, int, list[str]]:
    summary = dict(assessment.context_signal_summary or {})
    recommended = _router_profile_from_token(summary.get("odylith_execution_profile", ""))
    confidence = _clamp_score(summary.get("odylith_execution_confidence_score", 0) or 0)
    if recommended is None or recommended is RouterProfile.MAIN_THREAD or confidence <= 0:
        return selected, routing_confidence, []
    if recommended is RouterProfile.GPT54_XHIGH and not allow_xhigh:
        recommended = RouterProfile.GPT54_HIGH
    lines: list[str] = []
    packet_alignment_state = _normalize_token(summary.get("optimization_packet_alignment_state", ""))
    yield_state = _normalize_token(summary.get("optimization_yield_state", ""))
    if (
        selected in {RouterProfile.GPT54_HIGH, RouterProfile.GPT54_XHIGH}
        and packet_alignment_state == "drifting"
    ):
        capped_profiles = [
            profile
            for profile in (
                RouterProfile.CODEX_HIGH,
                RouterProfile.CODEX_MEDIUM,
                RouterProfile.MINI_HIGH,
                RouterProfile.SPARK_MEDIUM,
            )
            if profile.value in scorecard
        ]
        if capped_profiles:
            selected = max(
                capped_profiles,
                key=lambda profile: (float(scorecard.get(profile.value, 0.0) or 0.0), _PROFILE_PRIORITY.get(profile.value, 0)),
            )
            routing_confidence = min(
                routing_confidence,
                _clamp_score(max(1, _routing_confidence(selected, assessment, scorecard) - 1)),
            )
            lines.append(
                f"the routed tier stayed at `{selected.value}` because recent execution fit is still unstable on comparable slices"
            )
        return selected, routing_confidence, lines
    if (
        selected in {RouterProfile.GPT54_HIGH, RouterProfile.GPT54_XHIGH}
        and not assessment.correctness_critical
        and yield_state == "wasteful"
    ):
        capped_profiles = [
            profile
            for profile in (
                RouterProfile.CODEX_HIGH,
                RouterProfile.CODEX_MEDIUM,
                RouterProfile.MINI_HIGH,
                RouterProfile.SPARK_MEDIUM,
            )
            if profile.value in scorecard
        ]
        if capped_profiles:
            selected = max(
                capped_profiles,
                key=lambda profile: (float(scorecard.get(profile.value, 0.0) or 0.0), _PROFILE_PRIORITY.get(profile.value, 0)),
            )
            routing_confidence = min(
                routing_confidence,
                _clamp_score(max(1, _routing_confidence(selected, assessment, scorecard) - 1)),
            )
            lines.append(
                f"the routed tier stayed at `{selected.value}` because recent execution spend has been low-yield on comparable slices"
            )
        return selected, routing_confidence, lines
    if recommended is selected:
        return selected, max(routing_confidence, _routing_confidence(selected, assessment, scorecard)), lines
    recommended_priority = _PROFILE_PRIORITY.get(recommended.value, 0)
    selected_priority = _PROFILE_PRIORITY.get(selected.value, 0)
    selection_mode = _normalize_token(summary.get("odylith_execution_selection_mode", ""))
    runtime_depth_mode = selection_mode in _RUNTIME_EARNED_DEPTH_SELECTION_MODES
    runtime_support_mode = selection_mode in _RUNTIME_SUPPORT_SELECTION_MODES
    support_leaf = bool(summary.get("support_leaf"))
    route_ready = bool(summary.get("route_ready") or summary.get("odylith_execution_route_ready"))
    narrowing_required = bool(summary.get("narrowing_required") or summary.get("odylith_execution_narrowing_required"))
    spawn_worthiness = _clamp_score(summary.get("odylith_execution_spawn_worthiness", 0) or 0)
    history_budget_fragile = bool(
        _normalized_rate(summary.get("optimization_within_budget_rate", 0.0)) < 0.5
        and _normalized_rate(summary.get("optimization_deep_reasoning_ready_rate", 0.0)) < 0.5
    )
    history_prefers_local = bool(
        _normalized_rate(summary.get("optimization_hold_local_rate", 0.0)) >= 0.5
        and _normalized_rate(summary.get("optimization_hold_local_rate", 0.0))
        > _normalized_rate(summary.get("optimization_delegated_lane_rate", 0.0))
    )
    history_latency_pressure = _clamp_score(summary.get("optimization_latency_pressure_score", 0) or 0) >= 3
    stronger_alignment = (
        recommended_priority > selected_priority
        and route_ready
        and not narrowing_required
        and packet_alignment_state != "drifting"
        and not (yield_state == "wasteful" and not assessment.correctness_critical)
        and not (
            recommended in {RouterProfile.GPT54_HIGH, RouterProfile.GPT54_XHIGH}
            and (
                history_budget_fragile
                or history_prefers_local
                or (history_latency_pressure and not assessment.correctness_critical)
            )
        )
        and (
            confidence >= 3
            or (
                confidence >= 2
                and (
                    assessment.correctness_critical
                    or assessment.feature_implementation
                    or assessment.requested_depth >= 3
                    or assessment.earned_depth >= 3
                    or assessment.delegation_readiness >= 3
                    or runtime_depth_mode
                )
            )
        )
    )
    lighter_alignment = (
        recommended_priority < selected_priority
        and confidence >= 3
        and support_leaf
        and spawn_worthiness <= 2
        and not assessment.correctness_critical
        and not assessment.feature_implementation
        and runtime_support_mode
        and assessment.delegation_readiness <= 2
    )
    if stronger_alignment:
        selected = recommended
        routing_confidence = max(routing_confidence, _routing_confidence(selected, assessment, scorecard))
        lines.append(
            f"measured execution guidance raised the routed tier to `{selected.value}`"
        )
    elif lighter_alignment:
        selected = recommended
        routing_confidence = max(routing_confidence, _routing_confidence(selected, assessment, scorecard))
        lines.append(
            f"measured execution guidance lowered the routed tier to `{selected.value}` for a support slice"
        )
    return selected, routing_confidence, _sanitize_user_facing_lines(lines)


def _top_score_lines(
    *,
    selected: RouterProfile,
    scorecard: Mapping[str, float],
    assessment: TaskAssessment,
    task_class_policy_lines: Sequence[str],
    allow_xhigh: bool,
    routing_confidence: int,
    score_margin: float,
    backstop_lines: Sequence[str],
) -> list[str]:
    ordered = sorted(scorecard.items(), key=lambda item: (item[1], _PROFILE_PRIORITY.get(item[0], 0)), reverse=True)
    lines: list[str] = []
    if selected is RouterProfile.MAIN_THREAD:
        return lines
    lines.append(f"task_family={assessment.task_family}")
    lines.extend(task_class_policy_lines)
    lines.append(f"routing_confidence={routing_confidence}/4")
    top_drivers: list[str] = []
    if assessment.feature_implementation:
        top_drivers.append("feature implementation biases toward stronger coding-optimized or GPT-5.4 profiles")
    if not assessment.needs_write and assessment.task_family == "analysis_review":
        top_drivers.append("read-only analysis keeps the winner set on explorer and deep-read tiers, not write-oriented code tiers")
    if assessment.feature_reasons.get("grounding"):
        top_drivers.extend(_sanitize_user_facing_lines(assessment.feature_reasons["grounding"]))
    context_signal_summary = dict(assessment.context_signal_summary or {})
    if context_signal_summary.get("grounding_score", 0) >= 3:
        top_drivers.append(f"context_grounding={context_signal_summary['grounding_score']}")
    if context_signal_summary.get("actionability_score", 0) >= 3:
        top_drivers.append(f"context_actionability={context_signal_summary['actionability_score']}")
    if context_signal_summary.get("validation_burden_score", 0) >= 3:
        top_drivers.append(f"context_validation_burden={context_signal_summary['validation_burden_score']}")
    if context_signal_summary.get("utility_score", 0) >= 1:
        top_drivers.append(f"context_utility={context_signal_summary['utility_score']}")
    if context_signal_summary.get("token_efficiency_score", 0) >= 1:
        top_drivers.append(f"context_token_efficiency={context_signal_summary['token_efficiency_score']}")
    if context_signal_summary.get("optimization_within_budget_rate", 0.0) >= 0.5:
        top_drivers.append(
            f"optimization_budget_rate={round(float(context_signal_summary['optimization_within_budget_rate']), 2)}"
        )
    if context_signal_summary.get("optimization_deep_reasoning_ready_rate", 0.0) >= 0.5:
        top_drivers.append(
            "optimization_deep_ready="
            f"{round(float(context_signal_summary['optimization_deep_reasoning_ready_rate']), 2)}"
        )
    if context_signal_summary.get("intent_family"):
        top_drivers.append(f"context_intent={context_signal_summary['intent_family']}")
    if assessment.earned_depth >= 2:
        top_drivers.append(f"earned_depth={assessment.earned_depth}")
    if assessment.delegation_readiness >= 2:
        top_drivers.append(f"delegation_readiness={assessment.delegation_readiness}")
    if context_signal_summary.get("support_leaf"):
        top_drivers.append("support_leaf=true")
    if context_signal_summary.get("primary_leaf"):
        top_drivers.append("primary_leaf=true")
    if assessment.ambiguity >= 2:
        top_drivers.append(f"ambiguity={assessment.ambiguity}")
    if assessment.blast_radius >= 2:
        top_drivers.append(f"blast_radius={assessment.blast_radius}")
    if assessment.context_breadth >= 2:
        top_drivers.append(f"context_breadth={assessment.context_breadth}")
    if assessment.reversibility_risk >= 2:
        top_drivers.append(f"reversibility_risk={assessment.reversibility_risk}")
    if assessment.mechanicalness >= 2 and selected is RouterProfile.SPARK_MEDIUM:
        top_drivers.append(f"mechanicalness={assessment.mechanicalness}")
    if (
        not assessment.needs_write
        and selected in {RouterProfile.MINI_MEDIUM, RouterProfile.MINI_HIGH}
        and assessment.artifact_specificity >= 1
    ):
        top_drivers.append("bounded read-only analysis fits the mini explorer ladder")
    if assessment.evolving_context_required and assessment.evidence_cone_grounded:
        top_drivers.append("grounded locally before routing, so evolving context no longer blocks delegation")
    if assessment.write_scope_clarity >= 3:
        top_drivers.append(f"write_scope_clarity={assessment.write_scope_clarity}")
    if assessment.acceptance_clarity >= 2:
        top_drivers.append(f"acceptance_clarity={assessment.acceptance_clarity}")
    if assessment.validation_clarity >= 2:
        top_drivers.append(f"validation_clarity={assessment.validation_clarity}")
    if assessment.requested_depth >= 2:
        top_drivers.append(f"requested_depth={assessment.requested_depth}")
    if top_drivers:
        lines.append(f"drivers: {', '.join(top_drivers)}")
    lines.extend(_sanitize_user_facing_lines(backstop_lines))
    if len(ordered) >= 2:
        raw_winner, _ = ordered[0]
        if raw_winner != selected.value:
            lines.append(f"raw-score winner was `{raw_winner}`, but the confidence backstop promoted `{selected.value}`")
        else:
            runner_up, _ = next((item for item in ordered if item[0] != selected.value), ordered[0])
            lines.append(f"runner-up `{runner_up}` trailed by {score_margin} points")
    if routing_confidence <= 1:
        lines.append("manual review is recommended because the route confidence stayed low after assessment")
    if not allow_xhigh:
        lines.append("`gpt-5.4 + xhigh` stayed gated because no critical-risk or prior-failure trigger was present")
    return _sanitize_user_facing_lines(lines)
