from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence
from pathlib import Path

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.consumer_profile import load_consumer_profile
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.intervention_engine import conversation_runtime


def _first_present(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            if _normalize_string(value):
                return value
            continue
        if value is not None:
            return value
    return None


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    token = _normalize_token(value)
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"", "0", "false", "no", "off"}:
        return False
    return bool(value)


def bind(host_module: Any) -> None:
    globals().update({
        "OrchestrationRequest": getattr(host_module, "OrchestrationRequest"),
        "OrchestrationDecision": getattr(host_module, "OrchestrationDecision"),
        "SubtaskSlice": getattr(host_module, "SubtaskSlice"),
        "leaf_router": getattr(host_module, "leaf_router"),
        "odylith_store": getattr(host_module, "odylith_store"),
        "_normalize_string": getattr(host_module, "_normalize_string"),
        "_normalize_token": getattr(host_module, "_normalize_token"),
        "_normalize_list": getattr(host_module, "_normalize_list"),
        "_normalize_context_signals": getattr(host_module, "_normalize_context_signals"),
        "_extract_context_signals_payload": getattr(host_module, "_extract_context_signals_payload"),
        "_dedupe_strings": getattr(host_module, "_dedupe_strings"),
        "_mapping_lookup": getattr(host_module, "_mapping_lookup"),
        "_nested_mapping": getattr(host_module, "_nested_mapping"),
        "_execution_profile_mapping": getattr(host_module, "_execution_profile_mapping"),
        "_int_value": getattr(host_module, "_int_value"),
        "_normalized_rate": getattr(host_module, "_normalized_rate"),
        "_request_seed_paths": getattr(host_module, "_request_seed_paths"),
        "_request_has_odylith_seeds": getattr(host_module, "_request_has_odylith_seeds"),
        "_payload_packet_kind": getattr(host_module, "_payload_packet_kind"),
        "_merge_context_signals": getattr(host_module, "_merge_context_signals"),
        "_clamp_confidence": getattr(host_module, "_clamp_confidence"),
        "_compact_selection_state_parts": getattr(host_module, "_compact_selection_state_parts"),
        "_odylith_payload_full_scan_recommended": getattr(host_module, "_odylith_payload_full_scan_recommended"),
        "_odylith_payload_diagram_watch_gap_count": getattr(host_module, "_odylith_payload_diagram_watch_gap_count"),
        "_odylith_payload_selection_state": getattr(host_module, "_odylith_payload_selection_state"),
        "_odylith_payload_routing_confidence": getattr(host_module, "_odylith_payload_routing_confidence"),
        "_odylith_payload_route_ready": getattr(host_module, "_odylith_payload_route_ready"),
        "_odylith_payload_paths": getattr(host_module, "_odylith_payload_paths"),
        "_odylith_payload_workstreams": getattr(host_module, "_odylith_payload_workstreams"),
        "_odylith_payload_component_ids": getattr(host_module, "_odylith_payload_component_ids"),
        "_CODEX_HOT_PATH_PROFILE": getattr(host_module, "_CODEX_HOT_PATH_PROFILE"),
        "_ARCHITECTURE_GROUNDING_KEYWORDS": getattr(host_module, "_ARCHITECTURE_GROUNDING_KEYWORDS"),
        "_GOVERNANCE_GROUNDING_KEYWORDS": getattr(host_module, "_GOVERNANCE_GROUNDING_KEYWORDS"),
    })


def _architecture_context_signals(payload: Mapping[str, Any]) -> dict[str, Any]:
    audit = dict(payload) if isinstance(payload, Mapping) else {}
    if not audit:
        return {}
    coverage = _nested_mapping(audit, "coverage")
    execution_hint = _nested_mapping(audit, "execution_hint")
    authority_graph_counts = _nested_mapping(_nested_mapping(audit, "authority_graph"), "counts")
    confidence_tier = _normalize_token(_mapping_lookup(coverage, "confidence_tier"))
    mode = _normalize_token(_mapping_lookup(execution_hint, "mode"))
    fanout = _normalize_token(_mapping_lookup(execution_hint, "fanout"))
    risk_tier = _normalize_token(_mapping_lookup(execution_hint, "risk_tier"))
    full_scan_recommended = bool(_mapping_lookup(audit, "full_scan_recommended"))
    diagram_watch_gaps = audit.get("diagram_watch_gaps", [])
    diagram_watch_gap_count = len(diagram_watch_gaps) if isinstance(diagram_watch_gaps, list) else 0
    changed_paths = _normalize_list(_mapping_lookup(audit, "changed_paths"))
    explicit_paths = _normalize_list(_mapping_lookup(audit, "explicit_paths")) or list(changed_paths)
    required_reads = _normalize_list(_mapping_lookup(audit, "required_reads"))
    validation_obligations = _mapping_lookup(audit, "validation_obligations")
    validation_obligation_count = (
        len(validation_obligations)
        if isinstance(validation_obligations, list)
        else _int_value(_mapping_lookup(audit, "validation_obligation_count"))
    )
    authority_graph_edge_count = _int_value(_mapping_lookup(authority_graph_counts, "edges"))
    resolved = bool(_mapping_lookup(audit, "resolved"))
    route_ready = bool(
        resolved
        and not full_scan_recommended
        and diagram_watch_gap_count <= 0
        and confidence_tier in {"medium", "high"}
        and mode in {"bounded_analysis", "local_or_single_leaf"}
        and fanout in {"", "optional", "bounded_single_leaf_only", "bounded_parallel_candidate"}
    )
    parallelism_hint = "bounded_parallel_candidate" if fanout == "bounded_parallel_candidate" else "serial_preferred"
    routing_confidence = "high" if confidence_tier == "high" else "medium" if confidence_tier == "medium" else "low"
    validation_score = 3 if validation_obligation_count > 0 else 1 if required_reads else 0
    context_density_score = 3 if len(required_reads) >= 2 else 2 if required_reads else 1 if changed_paths else 0
    reasoning_readiness_score = 3 if confidence_tier == "high" else 2 if route_ready else 0
    utility_score = 4 if authority_graph_edge_count >= 6 else 3 if authority_graph_edge_count >= 3 or required_reads else 2 if route_ready else 1
    confidence_score = 4 if confidence_tier == "high" else 3 if confidence_tier == "medium" else 1
    selection_mode = "architecture_grounding" if risk_tier == "high" or mode == "local_or_single_leaf" else "architecture_synthesis"
    profile_token = (
        agent_runtime_contract.FRONTIER_HIGH_PROFILE
        if risk_tier == "high"
        else agent_runtime_contract.ANALYSIS_HIGH_PROFILE
    )
    default_model, default_reasoning_effort = agent_runtime_contract.execution_profile_runtime_fields(
        profile_token,
    )
    requested_model = _normalize_string(_mapping_lookup(execution_hint, "model"))
    model = requested_model if default_model and requested_model else default_model
    reasoning_effort = _normalize_string(_mapping_lookup(execution_hint, "reasoning_effort")) or default_reasoning_effort
    agent_role = "worker" if risk_tier == "high" or mode == "local_or_single_leaf" else "explorer"
    delegate_preference = "delegate" if route_ready else "hold_local"
    native_spawn_ready = bool(
        route_ready
        and delegate_preference == "delegate"
        and all((model, reasoning_effort, agent_role, selection_mode))
        and (required_reads or validation_obligation_count > 0 or authority_graph_edge_count >= 3)
    )
    execution_profile = {
        "profile": (
            profile_token
        ),
        "model": model,
        "reasoning_effort": reasoning_effort,
        "agent_role": agent_role,
        "selection_mode": selection_mode,
        "delegate_preference": delegate_preference,
        "source": "odylith_runtime_packet",
        "confidence": {
            "score": confidence_score,
            "level": "high" if confidence_score >= 4 else "medium" if confidence_score >= 3 else "low",
        },
        "constraints": {
            "route_ready": route_ready,
            "narrowing_required": False,
            "within_budget": True,
            "native_spawn_ready": native_spawn_ready,
            "context_density_score": context_density_score,
            "reasoning_readiness_score": reasoning_readiness_score,
            "validation_pressure_score": validation_score,
            "utility_score": utility_score,
            "risk_score": 3 if risk_tier == "high" else 2 if risk_tier else 1,
        },
    }
    packet_quality = {
        "routing_confidence": routing_confidence,
        "reasoning_bias": "accuracy_first",
        "parallelism_hint": parallelism_hint,
        "native_spawn_ready": native_spawn_ready,
        "within_budget": True,
        "context_richness": "focused" if route_ready else "narrowing",
        "evidence_quality": {
            "score": confidence_score,
            "level": "high" if confidence_score >= 4 else "medium" if confidence_score >= 3 else "low",
        },
        "validation_pressure": {
            "score": validation_score,
            "level": "high" if validation_score >= 3 else "low" if validation_score <= 1 else "medium",
        },
        "context_density": {
            "score": context_density_score,
            "level": "high" if context_density_score >= 4 else "medium" if context_density_score >= 2 else "low",
        },
        "reasoning_readiness": {
            "score": reasoning_readiness_score,
            "level": "high" if reasoning_readiness_score >= 4 else "medium" if reasoning_readiness_score >= 2 else "low",
            "mode": "bounded_analysis" if route_ready else "narrow_first",
            "deep_reasoning_ready": bool(route_ready and confidence_tier == "high"),
        },
        "intent_profile": {
            "family": "architecture",
            "mode": "architecture_grounding",
            "critical_path": "analysis_first",
            "confidence": routing_confidence,
            "explicit": True,
        },
        "utility_profile": {
            "score": utility_score * 20,
            "level": "high" if utility_score >= 4 else "medium" if utility_score >= 2 else "low",
            "token_efficiency": {
                "score": 3 if route_ready else 1,
                "level": "medium" if route_ready else "low",
            },
        },
    }
    routing_handoff = {
        "contract": "routing_handoff.v1",
        "version": "v2",
        "packet_kind": "architecture",
        "packet_state": "expanded",
        "selection_state": "explicit" if route_ready else "ambiguous",
        "routing_confidence": routing_confidence,
        "within_budget": True,
        "narrowing_required": False,
        "route_ready": route_ready,
        "native_spawn_ready": native_spawn_ready,
        "primary_anchor_path": changed_paths[0] if changed_paths else (required_reads[0] if required_reads else ""),
        "grounding": {
            "grounded": route_ready,
            "score": 4 if confidence_tier == "high" else 3 if confidence_tier == "medium" else 1,
        },
        "intent": {
            "family": "architecture",
            "mode": "architecture_grounding",
            "critical_path": "analysis_first",
            "confidence": routing_confidence,
            "explicit": True,
        },
        "parallelism": {
            "hint": parallelism_hint,
        },
        "packet_quality": packet_quality,
        "odylith_execution_profile": execution_profile,
    }
    context_packet = {
        "contract": "context_packet.v1",
        "version": "v1",
        "packet_kind": "architecture",
        "packet_state": "expanded",
        "full_scan_recommended": full_scan_recommended,
        "full_scan_reason": _normalize_string(_mapping_lookup(audit, "full_scan_reason")),
        "selection_state": "explicit" if route_ready else "ambiguous",
        "anchors": {
            "changed_paths": changed_paths,
            "explicit_paths": explicit_paths,
            "has_non_shared_anchor": bool(changed_paths or explicit_paths),
        },
        "route": {
            "route_ready": route_ready,
            "native_spawn_ready": native_spawn_ready,
            "narrowing_required": False,
            "reasoning_bias": "accuracy_first",
            "parallelism_hint": parallelism_hint,
        },
        "packet_quality": {
            **packet_quality,
            "intent_family": "architecture",
            "intent_mode": "architecture_grounding",
            "intent_critical_path": "analysis_first",
            "intent_confidence": routing_confidence,
            "intent_explicit": True,
        },
        "execution_profile": execution_profile,
    }
    payload = {
        "architecture_audit": audit,
        "routing_handoff": routing_handoff,
        "context_packet": context_packet,
    }
    if isinstance(diagram_watch_gaps, list):
        payload["diagram_watch_gaps"] = list(diagram_watch_gaps)
    return payload


def _odylith_payload_grounded(payload: Mapping[str, Any]) -> bool:
    if _odylith_payload_full_scan_recommended(payload):
        return False
    if _odylith_payload_diagram_watch_gap_count(payload) > 0:
        return False
    selection_state = _odylith_payload_selection_state(payload)
    routing_confidence = _odylith_payload_routing_confidence(payload)
    return bool(
        _odylith_payload_route_ready(payload)
        or selection_state in {"explicit", "inferred_confident"}
        or routing_confidence in {"medium", "high"}
        or bool(payload.get("resolved"))
    )


def _request_with_consumer_write_policy(
    request: OrchestrationRequest,
    *,
    repo_root: Path,
) -> OrchestrationRequest:
    if not request.needs_write:
        return request
    profile = load_consumer_profile(repo_root=Path(repo_root).resolve())
    policy = dict(profile.get("odylith_write_policy", {})) if isinstance(profile.get("odylith_write_policy"), Mapping) else {}
    if not policy:
        return request
    merged_signals = _merge_context_signals(
        _normalize_context_signals(request.context_signals),
        {"odylith_write_policy": policy},
    )
    if merged_signals == request.context_signals:
        return request
    return OrchestrationRequest(
        prompt=request.prompt,
        acceptance_criteria=list(request.acceptance_criteria),
        candidate_paths=list(request.candidate_paths),
        workstreams=list(request.workstreams),
        components=list(request.components),
        validation_commands=list(request.validation_commands),
        accuracy_preference=request.accuracy_preference,
        repo_work=request.repo_work,
        task_kind=request.task_kind,
        phase=request.phase,
        needs_write=request.needs_write,
        latency_sensitive=request.latency_sensitive,
        correctness_critical=request.correctness_critical,
        requires_multi_agent_adjudication=request.requires_multi_agent_adjudication,
        evolving_context_required=request.evolving_context_required,
        evidence_cone_grounded=request.evidence_cone_grounded,
        use_working_tree=request.use_working_tree,
        working_tree_scope=request.working_tree_scope,
        session_id=request.session_id,
        claimed_paths=list(request.claimed_paths),
        intent=request.intent,
        odylith_operation=request.odylith_operation,
        odylith_auto_ground=request.odylith_auto_ground,
        context_signals=merged_signals,
    )


def _request_odylith_adoption(request: OrchestrationRequest) -> dict[str, Any]:
    base = _normalize_context_signals(request.context_signals)
    routing_handoff = _nested_mapping(base, "routing_handoff")
    context_packet = _nested_mapping(base, "context_packet")
    architecture_audit = _nested_mapping(base, "architecture_audit")
    evidence_pack = _nested_mapping(base, "evidence_pack")
    auto_grounding = _nested_mapping(base, "orchestration_auto_grounding")
    runtime_execution = _nested_mapping(auto_grounding, "runtime_execution")
    odylith_write_policy = _nested_mapping(base, "odylith_write_policy")
    execution_engine_summary = _nested_mapping(base, "execution_engine_summary")
    packet_summary = _nested_mapping(base, "packet_summary")
    target_resolution = _nested_mapping(base, "target_resolution")
    presentation_policy = _nested_mapping(base, "presentation_policy")
    route = _nested_mapping(context_packet, "route")
    context_packet_target_resolution = _nested_mapping(context_packet, "target_resolution")
    context_packet_presentation_policy = _nested_mapping(context_packet, "presentation_policy")
    packet_quality = packet_quality_codec.expand_packet_quality(_nested_mapping(context_packet, "packet_quality"))
    diagram_watch_gaps = architecture_audit.get("diagram_watch_gaps", [])
    diagram_watch_gap_count = max(
        _int_value(auto_grounding.get("diagram_watch_gap_count")),
        len(diagram_watch_gaps) if isinstance(diagram_watch_gaps, list) else 0,
    )
    full_scan_recommended = bool(
        auto_grounding.get("full_scan_recommended")
        or context_packet.get("full_scan_recommended")
        or architecture_audit.get("full_scan_recommended")
    )
    selection_state, _ = _compact_selection_state_parts(context_packet.get("selection_state"))
    selection_state = _normalize_token(selection_state)
    routing_confidence = _normalize_token(
        routing_handoff.get("routing_confidence") or packet_quality.get("routing_confidence")
    )
    route_ready = bool(routing_handoff.get("route_ready") or route.get("route_ready"))
    native_spawn_ready = bool(routing_handoff.get("native_spawn_ready") or route.get("native_spawn_ready"))
    narrowing_required = bool(routing_handoff.get("narrowing_required") or route.get("narrowing_required"))
    packet_present = bool(routing_handoff or context_packet or architecture_audit or evidence_pack)
    auto_grounding_applied = bool(auto_grounding.get("applied"))
    grounded = bool(
        not full_scan_recommended
        and diagram_watch_gap_count <= 0
        and (
            request.evidence_cone_grounded
            or bool(auto_grounding.get("grounded"))
            or route_ready
            or selection_state in {"explicit", "inferred_confident"}
            or routing_confidence in {"medium", "high"}
        )
    )
    grounding_source = "none"
    if auto_grounding_applied:
        grounding_source = "auto_grounded"
    elif packet_present:
        grounding_source = "supplied_packet"
    packet_kind = _payload_packet_kind(base, context_packet=context_packet, routing_handoff=routing_handoff) or _normalize_token(
        auto_grounding.get("operation")
    )
    protected_roots = [
        str(token).strip().strip("/")
        for token in odylith_write_policy.get("protected_roots", [])
        if str(token).strip().strip("/")
    ]
    execution_engine_target_lane = _normalize_token(
        _first_present(
            _mapping_lookup(execution_engine_summary, "execution_engine_target_lane"),
            _mapping_lookup(base, "execution_engine_target_lane"),
            _mapping_lookup(base, "latest_execution_engine_target_lane"),
            _mapping_lookup(target_resolution, "lane"),
            _mapping_lookup(packet_summary, "target_resolution_lane"),
            _mapping_lookup(context_packet_target_resolution, "lane"),
        )
    )
    execution_engine_has_writable_targets = _bool_value(
        _first_present(
            _mapping_lookup(execution_engine_summary, "execution_engine_has_writable_targets"),
            _mapping_lookup(base, "execution_engine_has_writable_targets"),
            _mapping_lookup(base, "latest_execution_engine_has_writable_targets"),
            _mapping_lookup(target_resolution, "has_writable_targets"),
            _mapping_lookup(packet_summary, "target_resolution_has_writable_targets"),
            _mapping_lookup(context_packet_target_resolution, "has_writable_targets"),
        )
    )
    execution_engine_requires_more_consumer_context = _bool_value(
        _first_present(
            _mapping_lookup(execution_engine_summary, "execution_engine_requires_more_consumer_context"),
            _mapping_lookup(base, "execution_engine_requires_more_consumer_context"),
            _mapping_lookup(base, "latest_execution_engine_requires_more_consumer_context"),
            _mapping_lookup(target_resolution, "requires_more_consumer_context"),
            _mapping_lookup(packet_summary, "target_resolution_requires_more_consumer_context"),
            _mapping_lookup(context_packet_target_resolution, "requires_more_consumer_context"),
        )
    )
    execution_engine_consumer_failover = _normalize_string(
        _first_present(
            _mapping_lookup(execution_engine_summary, "execution_engine_consumer_failover"),
            _mapping_lookup(base, "execution_engine_consumer_failover"),
            _mapping_lookup(base, "latest_execution_engine_consumer_failover"),
            _mapping_lookup(target_resolution, "consumer_failover"),
            _mapping_lookup(packet_summary, "target_resolution_consumer_failover"),
            _mapping_lookup(context_packet_target_resolution, "consumer_failover"),
        )
    )
    execution_engine_commentary_mode = _normalize_token(
        _first_present(
            _mapping_lookup(execution_engine_summary, "execution_engine_commentary_mode"),
            _mapping_lookup(base, "execution_engine_commentary_mode"),
            _mapping_lookup(base, "latest_execution_engine_commentary_mode"),
            _mapping_lookup(presentation_policy, "commentary_mode"),
            _mapping_lookup(packet_summary, "presentation_policy_commentary_mode"),
            _mapping_lookup(context_packet_presentation_policy, "commentary_mode"),
        )
    )
    execution_engine_suppress_routing_receipts = _bool_value(
        _first_present(
            _mapping_lookup(execution_engine_summary, "execution_engine_suppress_routing_receipts"),
            _mapping_lookup(base, "execution_engine_suppress_routing_receipts"),
            _mapping_lookup(base, "latest_execution_engine_suppress_routing_receipts"),
            _mapping_lookup(presentation_policy, "suppress_routing_receipts"),
            _mapping_lookup(packet_summary, "presentation_policy_suppress_routing_receipts"),
            _mapping_lookup(context_packet_presentation_policy, "suppress_routing_receipts"),
        )
    )
    execution_engine_surface_fast_lane = _bool_value(
        _first_present(
            _mapping_lookup(execution_engine_summary, "execution_engine_surface_fast_lane"),
            _mapping_lookup(base, "execution_engine_surface_fast_lane"),
            _mapping_lookup(base, "latest_execution_engine_surface_fast_lane"),
            _mapping_lookup(presentation_policy, "surface_fast_lane"),
            _mapping_lookup(packet_summary, "presentation_policy_surface_fast_lane"),
            _mapping_lookup(context_packet_presentation_policy, "surface_fast_lane"),
        )
    )
    return {
        "packet_present": packet_present,
        "grounding_source": grounding_source,
        "auto_grounding_applied": auto_grounding_applied,
        "operation": _normalize_token(auto_grounding.get("operation")) or packet_kind,
        "packet_kind": packet_kind,
        "grounded": grounded,
        "route_ready": route_ready,
        "native_spawn_ready": native_spawn_ready,
        "narrowing_required": narrowing_required,
        "full_scan_recommended": full_scan_recommended,
        "diagram_watch_gap_count": diagram_watch_gap_count,
        "requires_widening": bool(full_scan_recommended or diagram_watch_gap_count > 0),
        "selection_state": selection_state,
        "routing_confidence": routing_confidence,
        "runtime_source": _normalize_token(runtime_execution.get("source")) or "none",
        "runtime_transport": _normalize_token(runtime_execution.get("transport")) or "none",
        "workspace_daemon_reused": bool(runtime_execution.get("workspace_daemon_reused")),
        "session_namespaced": bool(runtime_execution.get("session_namespaced")),
        "session_namespace": str(runtime_execution.get("session_namespace", "")).strip(),
        "request_namespace": str(runtime_execution.get("request_namespace", "")).strip(),
        "mixed_local_fallback": bool(runtime_execution.get("mixed_local_fallback")),
        "odylith_fix_mode": _normalize_token(odylith_write_policy.get("odylith_fix_mode")) or "unknown",
        "allow_odylith_mutations": bool(odylith_write_policy.get("allow_odylith_mutations")),
        "protected_roots": protected_roots,
        "execution_engine_target_lane": execution_engine_target_lane,
        "execution_engine_has_writable_targets": execution_engine_has_writable_targets,
        "execution_engine_requires_more_consumer_context": execution_engine_requires_more_consumer_context,
        "execution_engine_consumer_failover": execution_engine_consumer_failover,
        "execution_engine_commentary_mode": execution_engine_commentary_mode,
        "execution_engine_suppress_routing_receipts": execution_engine_suppress_routing_receipts,
        "execution_engine_surface_fast_lane": execution_engine_surface_fast_lane,
    }


def _decision_odylith_adoption(
    *,
    repo_root: Path | None,
    request: OrchestrationRequest,
    decision: OrchestrationDecision,
    final_changed_paths: Sequence[str] | None = None,
    changed_path_source: str = "",
) -> dict[str, Any]:
    summary = _request_odylith_adoption(request)
    summary["delegate"] = bool(decision.delegate)
    summary["mode"] = _normalize_token(decision.mode)
    summary["manual_review_recommended"] = bool(decision.manual_review_recommended)
    summary["grounded_delegate"] = bool(summary.get("grounded") and decision.delegate)
    conversation_bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=decision,
        adoption=summary,
        repo_root=repo_root,
        final_changed_paths=final_changed_paths,
        changed_path_source=changed_path_source,
    )
    closeout_bundle = dict(conversation_bundle.get("closeout_bundle", {}))
    summary["conversation_bundle"] = conversation_bundle
    summary["ambient_signals"] = dict(conversation_bundle.get("ambient_signals", {}))
    summary["closeout_bundle"] = closeout_bundle
    summary["closeout_assist"] = (
        dict(closeout_bundle.get("assist", {}))
        if isinstance(closeout_bundle.get("assist"), Mapping)
        else {}
    )
    return summary


def _request_prefers_architecture_grounding(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> bool:
    if request.odylith_operation == "architecture":
        return True
    task_kind = _normalize_token(request.task_kind)
    if task_kind == "architecture":
        return True
    prompt_surface = _normalize_token(" ".join([request.prompt, *request.acceptance_criteria, *request.components]))
    if any(keyword.replace("-", "_").replace(" ", "_") in prompt_surface for keyword in _ARCHITECTURE_GROUNDING_KEYWORDS):
        return True
    return bool(
        not request.needs_write
        and assessment.task_family in {"analysis_review", "coordination_heavy", "critical_change"}
        and assessment.semantic_signals.get("open_ended_scope")
        and any(keyword.replace("-", "_").replace(" ", "_") in prompt_surface for keyword in ("control_plane", "shared", "architecture"))
    )


def _request_prefers_governance_grounding(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> bool:
    if request.odylith_operation == "governance_slice":
        return True
    normalized_paths = [str(path).strip() for path in request.candidate_paths if str(path).strip()]
    implementation_like_paths_present = any(
        path.startswith(("src/odylith/", "tests/", "services/", "contracts/", "odylith/runtime/contracts/"))
        for path in normalized_paths
    )
    prompt_surface = _normalize_token(
        " ".join(
            [
                request.prompt,
                *request.acceptance_criteria,
                *request.candidate_paths,
                *request.workstreams,
                *request.components,
            ]
        )
    )
    if (
        any(keyword.replace("-", "_").replace(" ", "_") in prompt_surface for keyword in _GOVERNANCE_GROUNDING_KEYWORDS)
        and not implementation_like_paths_present
    ):
        return True
    governance_prefixes = (
        "odylith/technical-plans/",
        "odylith/casebook/bugs/",
        "odylith/radar/",
        "odylith/registry/",
        "odylith/compass/",
        "docs/runbooks/",
    )
    if normalized_paths and all(path.startswith(governance_prefixes) for path in normalized_paths):
        return True
    return False


def _auto_odylith_operation(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> str:
    if request.odylith_operation != "auto":
        return request.odylith_operation
    if (request.session_id or request.use_working_tree or request.claimed_paths) and not request.candidate_paths:
        return "bootstrap_session"
    if _request_prefers_governance_grounding(request, assessment):
        return "governance_slice"
    if _request_prefers_architecture_grounding(request, assessment):
        return "architecture"
    return "impact"


def _auto_ground_request_with_odylith(
    request: OrchestrationRequest,
    *,
    repo_root: Path,
    assessment: leaf_router.TaskAssessment,
) -> OrchestrationRequest:
    request = _request_with_consumer_write_policy(request, repo_root=repo_root)
    explicit_context_signals = {
        str(key): value
        for key, value in _normalize_context_signals(request.context_signals).items()
        if str(key) != "odylith_write_policy"
    }
    if explicit_context_signals or not request.repo_work or not request.odylith_auto_ground:
        return request
    if not _request_has_odylith_seeds(request):
        return request
    changed_paths = _request_seed_paths(request)
    if not changed_paths and request.needs_write:
        return request
    operation = _auto_odylith_operation(request, assessment)
    workstream_hint = request.workstreams[0] if request.workstreams else ""
    component_hint = request.components[0] if request.components else ""
    base_kwargs = {
        "repo_root": Path(repo_root).resolve(),
        "changed_paths": changed_paths,
        "use_working_tree": request.use_working_tree,
        "working_tree_scope": request.working_tree_scope or ("session" if request.session_id else "repo"),
        "session_id": request.session_id,
        "claimed_paths": list(request.claimed_paths),
        "runtime_mode": "auto",
        "intent": request.intent or request.phase or request.task_kind,
        "validation_command_hints": list(request.validation_commands),
    }
    if operation == "bootstrap_session":
        daemon_result = odylith_store.request_runtime_daemon(
            repo_root=Path(repo_root).resolve(),
            command="bootstrap-session",
            payload={
                "paths": list(changed_paths),
                "use_working_tree": request.use_working_tree,
                "working_tree_scope": request.working_tree_scope or ("session" if request.session_id else "repo"),
                "session_id": request.session_id,
                "workstream": workstream_hint,
                "intent": request.intent or request.phase or request.task_kind,
                "claim_paths": list(request.claimed_paths),
                "runtime_mode": "auto",
                "delivery_profile": _CODEX_HOT_PATH_PROFILE,
                "family_hint": assessment.task_family,
                "validation_command_hints": list(request.validation_commands),
            },
        )
        if daemon_result is not None:
            payload, runtime_execution = daemon_result
        else:
            payload = odylith_store.build_session_bootstrap(
                **base_kwargs,
                workstream=workstream_hint,
                delivery_profile=_CODEX_HOT_PATH_PROFILE,
                family_hint=assessment.task_family,
            )
            runtime_execution = odylith_store._local_runtime_execution_summary(  # noqa: SLF001
                repo_root=Path(repo_root).resolve(),
                command="bootstrap-session",
                changed_paths=changed_paths,
                session_id=request.session_id,
                claimed_paths=list(request.claimed_paths),
                working_tree_scope=request.working_tree_scope or ("session" if request.session_id else "repo"),
            )
    elif operation == "session_brief":
        daemon_result = odylith_store.request_runtime_daemon(
            repo_root=Path(repo_root).resolve(),
            command="session-brief",
            payload={
                "paths": list(changed_paths),
                "use_working_tree": request.use_working_tree,
                "working_tree_scope": request.working_tree_scope or ("session" if request.session_id else "repo"),
                "session_id": request.session_id,
                "workstream": workstream_hint,
                "intent": request.intent or request.phase or request.task_kind,
                "claim_paths": list(request.claimed_paths),
                "runtime_mode": "auto",
                "delivery_profile": _CODEX_HOT_PATH_PROFILE,
                "family_hint": assessment.task_family,
                "validation_command_hints": list(request.validation_commands),
            },
        )
        if daemon_result is not None:
            payload, runtime_execution = daemon_result
        else:
            payload = odylith_store.build_session_brief(
                **base_kwargs,
                workstream=workstream_hint,
                delivery_profile=_CODEX_HOT_PATH_PROFILE,
                family_hint=assessment.task_family,
            )
            runtime_execution = odylith_store._local_runtime_execution_summary(  # noqa: SLF001
                repo_root=Path(repo_root).resolve(),
                command="session-brief",
                changed_paths=changed_paths,
                session_id=request.session_id,
                claimed_paths=list(request.claimed_paths),
                working_tree_scope=request.working_tree_scope or ("session" if request.session_id else "repo"),
            )
    elif operation == "governance_slice":
        daemon_result = odylith_store.request_runtime_daemon(
            repo_root=Path(repo_root).resolve(),
            command="governance-slice",
            payload={
                "paths": list(changed_paths),
                "workstream": workstream_hint,
                "component": component_hint,
                "use_working_tree": request.use_working_tree,
                "working_tree_scope": request.working_tree_scope or ("session" if request.session_id else "repo"),
                "session_id": request.session_id,
                "claim_paths": list(request.claimed_paths),
                "runtime_mode": "auto",
                "delivery_profile": _CODEX_HOT_PATH_PROFILE,
                "family_hint": assessment.task_family,
                "validation_command_hints": list(request.validation_commands),
            },
        )
        if daemon_result is not None:
            payload, runtime_execution = daemon_result
        else:
            payload = odylith_store.build_governance_slice(
                **base_kwargs,
                workstream=workstream_hint,
                component=component_hint,
                delivery_profile=_CODEX_HOT_PATH_PROFILE,
                family_hint=assessment.task_family,
            )
            runtime_execution = odylith_store._local_runtime_execution_summary(  # noqa: SLF001
                repo_root=Path(repo_root).resolve(),
                command="governance-slice",
                changed_paths=changed_paths,
                session_id=request.session_id,
                claimed_paths=list(request.claimed_paths),
                working_tree_scope=request.working_tree_scope or ("session" if request.session_id else "repo"),
            )
    elif operation == "architecture":
        daemon_result = odylith_store.request_runtime_daemon(
            repo_root=Path(repo_root).resolve(),
            command="architecture",
            payload={
                "paths": list(changed_paths),
                "use_working_tree": request.use_working_tree,
                "working_tree_scope": request.working_tree_scope or ("session" if request.session_id else "repo"),
                "session_id": request.session_id,
                "claim_paths": list(request.claimed_paths),
                "runtime_mode": "auto",
                "detail_level": "packet",
            },
        )
        if daemon_result is not None:
            payload, runtime_execution = daemon_result
        else:
            payload = odylith_store.build_architecture_audit(
                repo_root=Path(repo_root).resolve(),
                changed_paths=changed_paths,
                use_working_tree=request.use_working_tree,
                working_tree_scope=request.working_tree_scope or ("session" if request.session_id else "repo"),
                session_id=request.session_id,
                claimed_paths=list(request.claimed_paths),
                runtime_mode="auto",
                detail_level="packet",
            )
            runtime_execution = odylith_store._local_runtime_execution_summary(  # noqa: SLF001
                repo_root=Path(repo_root).resolve(),
                command="architecture",
                changed_paths=changed_paths,
                session_id=request.session_id,
                claimed_paths=list(request.claimed_paths),
                working_tree_scope=request.working_tree_scope or ("session" if request.session_id else "repo"),
            )
    else:
        adaptive = odylith_store.build_adaptive_coding_packet_reusing_daemon(
            **base_kwargs,
            family_hint=assessment.task_family,
            workstream_hint=workstream_hint,
        )
        payload = dict(adaptive.get("payload", {})) if isinstance(adaptive.get("payload"), Mapping) else {}
        operation = _normalize_token(adaptive.get("packet_source", "")) or "impact"
        runtime_execution = (
            dict(adaptive.get("runtime_execution", {}))
            if isinstance(adaptive.get("runtime_execution"), Mapping)
            else {}
        )
    if not isinstance(payload, Mapping) or not payload:
        return request
    grounded = _odylith_payload_grounded(payload)
    payload_signals = _extract_context_signals_payload(payload)
    if operation == "architecture":
        payload_signals = _merge_context_signals(
            payload_signals,
            _architecture_context_signals(payload),
        )
    merged_signals = _merge_context_signals(
        _normalize_context_signals(request.context_signals),
        payload_signals,
    )
    merged_signals = _merge_context_signals(
        merged_signals,
        {
            "orchestration_auto_grounding": {
                "applied": True,
                "operation": operation,
                "grounded": grounded,
                "full_scan_recommended": _odylith_payload_full_scan_recommended(payload),
                "diagram_watch_gap_count": _odylith_payload_diagram_watch_gap_count(payload),
                "runtime_execution": runtime_execution,
            }
        },
    )
    return OrchestrationRequest(
        prompt=request.prompt,
        acceptance_criteria=list(request.acceptance_criteria),
        candidate_paths=_dedupe_strings([*request.candidate_paths, *_odylith_payload_paths(payload)]),
        workstreams=_dedupe_strings([*request.workstreams, *_odylith_payload_workstreams(payload)]),
        components=_dedupe_strings([*request.components, *_odylith_payload_component_ids(payload)]),
        validation_commands=list(request.validation_commands),
        accuracy_preference=request.accuracy_preference,
        repo_work=request.repo_work,
        task_kind=request.task_kind,
        phase=request.phase,
        needs_write=request.needs_write,
        latency_sensitive=request.latency_sensitive,
        correctness_critical=request.correctness_critical,
        requires_multi_agent_adjudication=request.requires_multi_agent_adjudication,
        evolving_context_required=request.evolving_context_required,
        evidence_cone_grounded=grounded,
        use_working_tree=request.use_working_tree,
        working_tree_scope=request.working_tree_scope,
        session_id=request.session_id,
        claimed_paths=list(request.claimed_paths),
        intent=request.intent,
        odylith_operation=request.odylith_operation,
        odylith_auto_ground=request.odylith_auto_ground,
        context_signals=merged_signals,
    )


def _score_level(score: int) -> str:
    clamped = max(0, min(4, int(score)))
    if clamped >= 4:
        return "high"
    if clamped >= 2:
        return "medium"
    if clamped >= 1:
        return "low"
    return "none"


def _intent_confidence_score(value: Any) -> int:
    token = _normalize_token(value)
    if token == "high":
        return 4
    if token == "medium":
        return 2
    if token == "low":
        return 1
    return 0


def _profile_runtime_fields(profile_token: str) -> tuple[str, str, str]:
    profile = _normalize_token(profile_token)
    model, reasoning_effort = agent_runtime_contract.execution_profile_runtime_fields(profile)
    if profile in {
        leaf_router.RouterProfile.MINI_MEDIUM.value,
        leaf_router.RouterProfile.MINI_HIGH.value,
    }:
        return model, reasoning_effort, "explorer"
    if profile == leaf_router.RouterProfile.SPARK_MEDIUM.value:
        return model, reasoning_effort, "worker"
    if profile in {
        leaf_router.RouterProfile.CODEX_MEDIUM.value,
        leaf_router.RouterProfile.CODEX_HIGH.value,
    }:
        return model, reasoning_effort, "worker"
    if profile in {
        leaf_router.RouterProfile.GPT54_HIGH.value,
        leaf_router.RouterProfile.GPT54_XHIGH.value,
    }:
        return model, reasoning_effort, "worker"
    return "", "", "main_thread"


def _subtask_odylith_execution_profile(
    *,
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    subtask: SubtaskSlice,
    intent_profile: Mapping[str, Any],
    architecture_audit: Mapping[str, Any],
    base_root: Mapping[str, Any],
    base_context_packet: Mapping[str, Any],
    base_optimization_snapshot: Mapping[str, Any],
    route_ready: bool,
    narrowing_required: bool,
    validation_pressure: int,
    utility_score: int,
    token_efficiency_score: int,
    routing_confidence_score: int,
    spawn_worthiness: int,
    merge_burden: int,
) -> dict[str, Any]:
    base_execution = (
        _execution_profile_mapping(_mapping_lookup(base_root, "odylith_execution_profile"))
        or _execution_profile_mapping(_mapping_lookup(base_root, "execution_profile"))
        or _execution_profile_mapping(_mapping_lookup(base_context_packet, "execution_profile"))
        or _execution_profile_mapping(_mapping_lookup(base_optimization_snapshot, "execution_profile"))
    )
    base_profile = leaf_router._preferred_router_profile_from_execution_profile(base_execution)  # noqa: SLF001
    base_packet_quality = _nested_mapping(base_root, "packet_quality")
    base_optimization_packet_posture = _nested_mapping(base_optimization_snapshot, "packet_posture")
    base_optimization_quality_posture = _nested_mapping(base_optimization_snapshot, "quality_posture")
    base_optimization_orchestration_posture = _nested_mapping(base_optimization_snapshot, "orchestration_posture")
    architecture_execution_hint = _nested_mapping(architecture_audit, "execution_hint")
    architecture_coverage = _nested_mapping(architecture_audit, "coverage")
    architecture_graph_counts = _nested_mapping(_nested_mapping(architecture_audit, "authority_graph"), "counts")
    architecture_family = _normalize_token(_mapping_lookup(intent_profile, "family")) == "architecture"
    architecture_mode = _normalize_token(_mapping_lookup(architecture_execution_hint, "mode"))
    architecture_fanout = _normalize_token(_mapping_lookup(architecture_execution_hint, "fanout"))
    architecture_risk_tier = _normalize_token(_mapping_lookup(architecture_execution_hint, "risk_tier"))
    architecture_confidence_tier = _normalize_token(_mapping_lookup(architecture_coverage, "confidence_tier"))
    architecture_full_scan_recommended = bool(_mapping_lookup(architecture_audit, "full_scan_recommended"))
    architecture_authority_graph_edge_count = _int_value(_mapping_lookup(architecture_graph_counts, "edges"))
    base_context_density_score = max(
        _int_value(_nested_mapping(base_packet_quality, "context_density").get("score")),
        _int_value(_mapping_lookup(base_optimization_quality_posture, "avg_context_density_score")),
    )
    base_reasoning_readiness_score = max(
        _int_value(_nested_mapping(base_packet_quality, "reasoning_readiness").get("score")),
        _int_value(_mapping_lookup(base_optimization_quality_posture, "avg_reasoning_readiness_score")),
    )
    base_evidence_diversity_score = max(
        _int_value(_nested_mapping(base_packet_quality, "evidence_diversity").get("score")),
        _int_value(_mapping_lookup(base_optimization_quality_posture, "avg_evidence_diversity_score")),
    )
    deep_reasoning_ready = bool(_nested_mapping(base_packet_quality, "reasoning_readiness").get("deep_reasoning_ready"))
    history_within_budget_rate = _normalized_rate(_mapping_lookup(base_optimization_packet_posture, "within_budget_rate"))
    history_route_ready_rate = _normalized_rate(_mapping_lookup(base_optimization_quality_posture, "route_ready_rate"))
    history_native_spawn_ready_rate = _normalized_rate(
        _mapping_lookup(base_optimization_quality_posture, "native_spawn_ready_rate")
    )
    history_deep_reasoning_ready_rate = _normalized_rate(
        _mapping_lookup(base_optimization_quality_posture, "deep_reasoning_ready_rate")
    )
    history_delegated_lane_rate = _normalized_rate(
        _mapping_lookup(base_optimization_orchestration_posture, "delegated_lane_rate")
    )
    history_hold_local_rate = _normalized_rate(
        _mapping_lookup(base_optimization_orchestration_posture, "hold_local_rate")
    )
    history_runtime_backed_execution_rate = _normalized_rate(
        _mapping_lookup(base_optimization_orchestration_posture, "runtime_backed_execution_rate")
    )
    history_supports_deep_reasoning = bool(
        history_within_budget_rate >= 0.75
        and history_route_ready_rate >= 0.5
        and history_deep_reasoning_ready_rate >= 0.5
    )
    history_supports_runtime_delegation = bool(
        history_native_spawn_ready_rate >= 0.5
        and history_runtime_backed_execution_rate >= 0.5
    )
    history_prefers_hold_local = bool(
        history_hold_local_rate >= 0.5 and history_hold_local_rate > history_delegated_lane_rate
    )
    profile = _normalize_token(base_execution.get("profile"))
    selection_mode = _normalize_token(base_execution.get("selection_mode"))
    if narrowing_required and spawn_worthiness <= 2:
        profile = leaf_router.RouterProfile.MAIN_THREAD.value
        selection_mode = "narrow_first"
    elif architecture_family:
        if architecture_full_scan_recommended or architecture_mode == "local_only" or architecture_confidence_tier == "low":
            profile = leaf_router.RouterProfile.MAIN_THREAD.value
            selection_mode = "architecture_grounding_local"
        elif architecture_risk_tier == "high":
            profile = leaf_router.RouterProfile.GPT54_HIGH.value
            selection_mode = "architecture_grounding"
        elif request.needs_write and subtask.scope_role in {"implementation", "contract"}:
            profile = leaf_router.RouterProfile.CODEX_HIGH.value
            selection_mode = "architecture_change"
        elif architecture_confidence_tier == "high" and route_ready and utility_score >= 50:
            profile = leaf_router.RouterProfile.MINI_HIGH.value
            selection_mode = "architecture_synthesis"
        else:
            profile = leaf_router.RouterProfile.MINI_MEDIUM.value
            selection_mode = "architecture_scoping"
    elif subtask.scope_role == "validation":
        if subtask.correctness_critical or assessment.task_family == "critical_change" or (
            (deep_reasoning_ready and base_reasoning_readiness_score >= 3)
            or history_supports_deep_reasoning
        ):
            profile = leaf_router.RouterProfile.GPT54_HIGH.value
            selection_mode = "deep_validation"
        else:
            profile = (
                leaf_router.RouterProfile.CODEX_HIGH.value
                if validation_pressure >= 3 or utility_score >= 70
                else leaf_router.RouterProfile.CODEX_MEDIUM.value
            )
            selection_mode = "validation_support"
    elif subtask.scope_role in {"implementation", "contract"}:
        if subtask.correctness_critical or assessment.task_family == "critical_change":
            profile = leaf_router.RouterProfile.GPT54_HIGH.value
            selection_mode = "critical_accuracy"
        elif (
            (deep_reasoning_ready and base_context_density_score >= 3 and base_reasoning_readiness_score >= 3)
            or (
                history_supports_deep_reasoning
                and base_context_density_score >= 2
                and base_reasoning_readiness_score >= 2
            )
        ):
            profile = leaf_router.RouterProfile.GPT54_HIGH.value
            selection_mode = "implementation_primary"
        elif utility_score >= 70 or base_reasoning_readiness_score >= 3 or history_supports_runtime_delegation:
            profile = leaf_router.RouterProfile.CODEX_HIGH.value
            selection_mode = "implementation_primary"
        else:
            profile = leaf_router.RouterProfile.CODEX_MEDIUM.value
            selection_mode = "implementation_primary"
    elif subtask.execution_group_kind == "support" and subtask.scope_role in {"docs", "governance"}:
        profile = (
            leaf_router.RouterProfile.SPARK_MEDIUM.value
            if utility_score >= 45 or token_efficiency_score >= 3
            else leaf_router.RouterProfile.MINI_MEDIUM.value
        )
        selection_mode = "support_fast_lane"
    elif not request.needs_write:
        profile = (
            leaf_router.RouterProfile.MINI_HIGH.value
            if base_reasoning_readiness_score >= 2 or base_context_density_score >= 2 or history_supports_deep_reasoning
            else leaf_router.RouterProfile.MINI_MEDIUM.value
        )
        selection_mode = "analysis_synthesis" if profile == leaf_router.RouterProfile.MINI_HIGH.value else "analysis_scout"
    if not profile:
        profile = leaf_router.RouterProfile.CODEX_MEDIUM.value if request.needs_write else leaf_router.RouterProfile.MINI_MEDIUM.value
    if (
        not subtask.correctness_critical
        and profile in {leaf_router.RouterProfile.GPT54_HIGH.value, leaf_router.RouterProfile.GPT54_XHIGH.value}
        and history_within_budget_rate < 0.5
        and history_deep_reasoning_ready_rate < 0.5
        and not (architecture_family and architecture_risk_tier == "high")
    ):
        profile = (
            leaf_router.RouterProfile.CODEX_HIGH.value
            if request.needs_write
            else leaf_router.RouterProfile.MINI_HIGH.value
        )
        selection_mode = "history_budget_guard"
    if (
        not subtask.correctness_critical
        and history_prefers_hold_local
        and not route_ready
        and spawn_worthiness <= 1
    ):
        profile = leaf_router.RouterProfile.MAIN_THREAD.value
        selection_mode = "narrow_first"
    current_profile = leaf_router._router_profile_from_token(profile)  # noqa: SLF001
    if (
        base_profile is not None
        and base_profile is not leaf_router.RouterProfile.MAIN_THREAD
        and current_profile is not None
        and current_profile is not leaf_router.RouterProfile.MAIN_THREAD
        and route_ready
        and not narrowing_required
        and (
            subtask.execution_group_kind != "support"
            or subtask.scope_role == "validation"
        )
        and leaf_router._PROFILE_PRIORITY.get(current_profile.value, 0)  # noqa: SLF001
        < leaf_router._PROFILE_PRIORITY.get(base_profile.value, 0)  # noqa: SLF001
    ):
        # Routed primary leaves should not silently downshift below an explicit
        # parent execution profile once the slice is route-ready.
        profile = base_profile.value
    model, reasoning_effort, agent_role = _profile_runtime_fields(profile)
    utility_signal_score = _clamp_confidence(int(round(max(0, utility_score) / 25.0)))
    ambiguity_score = 3 if narrowing_required and not route_ready else 2 if not route_ready else 1 if spawn_worthiness <= 1 else 0
    expected_delegation_value_score = _clamp_confidence(
        int(
            round(
                (
                    spawn_worthiness
                    + utility_signal_score
                    + (1 if route_ready else 0)
                    + (1 if request.evidence_cone_grounded else 0)
                    - (1 if narrowing_required else 0)
                )
                / 2.0
            )
        )
    )
    confidence_score = _clamp_confidence(
        max(
            _int_value(_nested_mapping(base_execution, "confidence").get("score")),
            routing_confidence_score,
            3 if route_ready else 0,
            2 if spawn_worthiness >= 3 else 0,
        )
        + (1 if subtask.execution_group_kind == "primary" and profile in {
            leaf_router.RouterProfile.CODEX_HIGH.value,
            leaf_router.RouterProfile.GPT54_HIGH.value,
            leaf_router.RouterProfile.GPT54_XHIGH.value,
        } else 0)
        - (1 if subtask.execution_group_kind == "support" and profile == leaf_router.RouterProfile.GPT54_HIGH.value else 0)
    )
    return {
        "profile": profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "agent_role": agent_role,
        "selection_mode": selection_mode or "bounded_write",
        "delegate_preference": (
            "delegate"
            if (
                profile != leaf_router.RouterProfile.MAIN_THREAD.value
                and route_ready
                and (history_supports_runtime_delegation or spawn_worthiness >= 3)
            )
            else "hold_local"
        ),
        "source": "odylith_orchestrator_leaf",
        "confidence": {
            "score": confidence_score,
            "level": _score_level(confidence_score),
        },
        "constraints": {
            "route_ready": route_ready,
            "narrowing_required": narrowing_required,
            "spawn_worthiness": spawn_worthiness,
            "merge_burden": merge_burden,
            "reasoning_mode": selection_mode or "bounded_write",
            "context_density_score": base_context_density_score,
            "reasoning_readiness_score": base_reasoning_readiness_score,
            "evidence_diversity_score": base_evidence_diversity_score,
            "validation_pressure_score": validation_pressure,
            "utility_score": utility_score,
            "history_within_budget_rate": round(history_within_budget_rate, 3),
            "history_route_ready_rate": round(history_route_ready_rate, 3),
            "history_native_spawn_ready_rate": round(history_native_spawn_ready_rate, 3),
            "history_deep_reasoning_ready_rate": round(history_deep_reasoning_ready_rate, 3),
            "history_delegated_lane_rate": round(history_delegated_lane_rate, 3),
            "history_hold_local_rate": round(history_hold_local_rate, 3),
            "history_runtime_backed_execution_rate": round(history_runtime_backed_execution_rate, 3),
            "architecture_mode": architecture_mode,
            "architecture_fanout": architecture_fanout,
            "architecture_risk_tier": architecture_risk_tier,
            "architecture_confidence_tier": architecture_confidence_tier,
            "architecture_full_scan_recommended": architecture_full_scan_recommended,
            "architecture_authority_graph_edge_count": architecture_authority_graph_edge_count,
        },
        "signals": {
            "grounding": {
                "score": 4 if request.evidence_cone_grounded else 0,
                "level": _score_level(4 if request.evidence_cone_grounded else 0),
                "anchored": bool(request.evidence_cone_grounded),
            },
            "ambiguity": {
                "score": ambiguity_score,
                "level": _score_level(ambiguity_score),
                "class": "narrowing_required" if narrowing_required else "bounded_leaf",
            },
            "density": {
                "score": max(base_context_density_score, 1 if request.evidence_cone_grounded else 0),
                "level": _score_level(max(base_context_density_score, 1 if request.evidence_cone_grounded else 0)),
            },
            "actionability": {
                "score": spawn_worthiness,
                "level": _score_level(spawn_worthiness),
            },
            "validation_pressure": {
                "score": validation_pressure,
                "level": _score_level(validation_pressure),
            },
            "merge_burden": {
                "score": merge_burden,
                "level": _score_level(merge_burden),
            },
            "expected_delegation_value": {
                "score": expected_delegation_value_score,
                "level": _score_level(expected_delegation_value_score),
                "route_ready": route_ready,
            },
            "architecture": {
                "score": 4 if architecture_family and architecture_confidence_tier == "high" else 3 if architecture_family and architecture_confidence_tier == "medium" else 1 if architecture_family else 0,
                "level": "high" if architecture_family and architecture_confidence_tier == "high" else "medium" if architecture_family and architecture_confidence_tier == "medium" else "low" if architecture_family else "none",
                "full_scan_recommended": architecture_full_scan_recommended,
                "risk_tier": architecture_risk_tier or "low",
                "authority_graph_edge_count": architecture_authority_graph_edge_count,
            },
        },
    }
