from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bootstrap_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_core_runtime
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.context_engine import odylith_context_engine_packet_runtime_bindings
from odylith.runtime.execution_engine import runtime_surface_governance
from odylith.runtime.governance import proof_state as proof_state_runtime

def bind(host: Any) -> None:
    odylith_context_engine_packet_runtime_bindings.bind_packet_runtime(globals(), host)

def _packet_summary_from_bootstrap_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    packet_metrics = dict(payload.get("packet_metrics", {})) if isinstance(payload.get("packet_metrics"), Mapping) else {}
    routing_handoff = dict(payload.get("routing_handoff", {})) if isinstance(payload.get("routing_handoff"), Mapping) else {}
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    optimization = (
        dict(context_packet.get("optimization", {}))
        if isinstance(context_packet.get("optimization"), Mapping)
        else {}
    )
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(payload.get("packet_quality", {}))
        if isinstance(payload.get("packet_quality"), Mapping)
        else dict(routing_handoff.get("packet_quality", {}))
        if isinstance(routing_handoff.get("packet_quality"), Mapping)
        else dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    utility_profile = (
        dict(packet_quality.get("utility_profile", {}))
        if isinstance(packet_quality.get("utility_profile"), Mapping)
        else {}
    )
    intent_profile = (
        dict(packet_quality.get("intent_profile", {}))
        if isinstance(packet_quality.get("intent_profile"), Mapping)
        else {
            key: value
            for key, value in {
                "family": str(packet_quality.get("intent_family", "")).strip(),
                "mode": str(packet_quality.get("intent_mode", "")).strip(),
                "critical_path": str(packet_quality.get("intent_critical_path", "")).strip(),
                "confidence": str(packet_quality.get("intent_confidence", "")).strip(),
                "explicit": bool(packet_quality.get("intent_explicit")),
            }.items()
            if value not in ("", [], {}, None, False)
        }
    )
    token_efficiency = (
        dict(utility_profile.get("token_efficiency", {}))
        if isinstance(utility_profile.get("token_efficiency"), Mapping)
        else {}
    )
    context_density = (
        dict(packet_quality.get("context_density", {}))
        if isinstance(packet_quality.get("context_density"), Mapping)
        else {
            key: value
            for key, value in {
                "score": int(packet_quality.get("context_density_score", 0) or 0),
                "level": str(packet_quality.get("context_density_level", "")).strip(),
            }.items()
            if value not in ("", [], {}, None, 0)
        }
    )
    reasoning_readiness = (
        dict(packet_quality.get("reasoning_readiness", {}))
        if isinstance(packet_quality.get("reasoning_readiness"), Mapping)
        else {
            key: value
            for key, value in {
                "score": int(packet_quality.get("reasoning_readiness_score", 0) or 0),
                "level": str(packet_quality.get("reasoning_readiness_level", "")).strip(),
                "mode": str(packet_quality.get("reasoning_readiness_mode", "")).strip(),
                "deep_reasoning_ready": bool(packet_quality.get("deep_reasoning_ready")),
            }.items()
            if value not in ("", [], {}, None, False, 0)
        }
    )
    evidence_diversity = (
        dict(packet_quality.get("evidence_diversity", {}))
        if isinstance(packet_quality.get("evidence_diversity"), Mapping)
        else {}
    )
    retrieval_plan = (
        dict(payload.get("retrieval_plan", {}))
        if isinstance(payload.get("retrieval_plan"), Mapping)
        else dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    odylith_execution = odylith_context_engine_hot_path_packet_core_runtime._decode_hot_path_execution_profile(
        routing_handoff.get("execution_profile") or routing_handoff.get("odylith_execution_profile")
    )
    if not odylith_execution and isinstance(context_packet.get("execution_profile"), Mapping):
        odylith_execution = dict(context_packet.get("execution_profile", {}))
    if odylith_execution and not str(odylith_execution.get("model", "")).strip():
        model, reasoning_effort = odylith_context_engine_hot_path_packet_core_runtime._hot_path_execution_profile_runtime_fields(
            str(odylith_execution.get("profile", "")).strip(),
            host_runtime=str(odylith_execution.get("host_runtime", "")).strip(),
        )
        if model:
            odylith_execution["model"] = model
        if reasoning_effort:
            odylith_execution["reasoning_effort"] = reasoning_effort
    odylith_execution_constraints = (
        dict(odylith_execution.get("constraints", {}))
        if isinstance(odylith_execution.get("constraints"), Mapping)
        else {}
    )
    odylith_execution_confidence = (
        dict(odylith_execution.get("confidence", {}))
        if isinstance(odylith_execution.get("confidence"), Mapping)
        else {}
    )
    miss_recovery = (
        dict(retrieval_plan.get("miss_recovery", {}))
        if isinstance(retrieval_plan.get("miss_recovery"), Mapping)
        else dict(payload.get("miss_recovery", {}))
        if isinstance(payload.get("miss_recovery"), Mapping)
        else dict(optimization.get("miss_recovery", {}))
        if isinstance(optimization.get("miss_recovery"), Mapping)
        else {}
    )
    adaptive_packet_profile = (
        dict(payload.get("adaptive_packet_profile", {}))
        if isinstance(payload.get("adaptive_packet_profile"), Mapping)
        else {}
    )
    if not adaptive_packet_profile:
        context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
        adaptive_packet_profile = (
            dict(context_packet.get("optimization", {}))
            if isinstance(context_packet.get("optimization"), Mapping)
            else {}
        )
    session_payload = dict(payload.get("session", {})) if isinstance(payload.get("session"), Mapping) else {}
    turn_context = (
        dict(payload.get("turn_context", {}))
        if isinstance(payload.get("turn_context"), Mapping)
        else dict(session_payload.get("turn_context", {}))
        if isinstance(session_payload.get("turn_context"), Mapping)
        else {}
    )
    target_resolution = (
        dict(payload.get("target_resolution", {}))
        if isinstance(payload.get("target_resolution"), Mapping)
        else {}
    )
    presentation_policy = (
        dict(payload.get("presentation_policy", {}))
        if isinstance(payload.get("presentation_policy"), Mapping)
        else {}
    )
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    selection_payload = dict(context_packet.get("selection", {})) if isinstance(context_packet.get("selection"), Mapping) else {}
    working_memory = dict(context_packet.get("working_memory", {})) if isinstance(context_packet.get("working_memory"), Mapping) else {}
    scratch = dict(working_memory.get("scratch", {})) if isinstance(working_memory.get("scratch"), Mapping) else {}
    validation_bundle = odylith_context_engine_hot_path_packet_bootstrap_runtime._hot_path_validation_bundle(
        payload,
        context_packet=context_packet,
    )
    governance_obligations = odylith_context_engine_hot_path_packet_bootstrap_runtime._hot_path_governance_obligations(
        payload,
        context_packet=context_packet,
    )
    selected_counts = _decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
    actionability_payload = (
        dict(packet_quality.get("actionability", {}))
        if isinstance(packet_quality.get("actionability"), Mapping)
        else {}
    )
    validation_pressure_payload = (
        dict(packet_quality.get("validation_pressure", {}))
        if isinstance(packet_quality.get("validation_pressure"), Mapping)
        else {}
    )
    context_density_payload = (
        dict(packet_quality.get("context_density", {}))
        if isinstance(packet_quality.get("context_density"), Mapping)
        else {}
    )
    evidence_quality_payload = (
        dict(packet_quality.get("evidence_quality", {}))
        if isinstance(packet_quality.get("evidence_quality"), Mapping)
        else {}
    )
    within_budget = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_payload_within_budget(
        payload=payload,
        context_packet=context_packet,
        packet_metrics=packet_metrics,
    )
    observed_route_ready = bool(routing_handoff.get("route_ready") or route.get("route_ready"))
    observed_native_spawn_ready = bool(routing_handoff.get("native_spawn_ready") or route.get("native_spawn_ready"))
    selected_doc_count = max(
        int(packet_quality.get("retained_doc_count", 0) or 0),
        odylith_context_engine_hot_path_packet_core_runtime._governance_closeout_doc_count(governance_obligations),
        len(_normalized_string_list(payload.get("docs"))),
    )
    selected_test_count = max(
        int(packet_quality.get("retained_test_count", 0) or 0),
        max(0, int(selected_counts.get("tests", 0) or 0)),
    )
    selected_command_count = max(
        int(packet_quality.get("retained_command_count", 0) or 0),
        max(0, int(selected_counts.get("commands", 0) or 0)),
    )
    strict_gate_command_count = odylith_context_engine_hot_path_packet_bootstrap_runtime._validation_bundle_command_count(
        validation_bundle,
        list_key="strict_gate_commands",
        count_key="strict_gate_command_count",
    )
    if not odylith_execution:
        odylith_execution = odylith_context_engine_hot_path_packet_core_runtime._hot_path_synthesized_execution_profile(
            packet_kind=_payload_packet_kind(payload, context_packet=context_packet),
            route_ready=bool(observed_route_ready or route.get("route_ready")),
            within_budget=within_budget,
            full_scan_recommended=bool(payload.get("full_scan_recommended") or context_packet.get("full_scan_recommended")),
            narrowing_required=bool(routing_handoff.get("narrowing_required") or route.get("narrowing_required")),
            routing_confidence=str(routing_handoff.get("routing_confidence", "")).strip()
            or str(packet_quality.get("routing_confidence", "")).strip(),
            intent_family=str(intent_profile.get("family", "")).strip(),
            validation_count=selected_test_count + selected_command_count,
            guidance_count=max(0, int(selected_counts.get("guidance", 0) or 0)),
            closeout_doc_count=odylith_context_engine_hot_path_packet_core_runtime._governance_closeout_doc_count(governance_obligations),
            strict_gate_command_count=strict_gate_command_count,
            plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
            governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
        )
    route_ready = routing.grounded_write_execution_ready(
        packet_kind=_payload_packet_kind(payload, context_packet=context_packet, routing_handoff=routing_handoff),
        packet_state=str(payload.get("context_packet_state", "")).strip() or str(context_packet.get("packet_state", "")).strip(),
        full_scan_recommended=bool(payload.get("full_scan_recommended") or context_packet.get("full_scan_recommended")),
        narrowing_required=bool(routing_handoff.get("narrowing_required") or route.get("narrowing_required")),
        within_budget=within_budget,
        routing_confidence=str(routing_handoff.get("routing_confidence", "")).strip() or str(packet_quality.get("routing_confidence", "")).strip(),
        has_non_shared_anchor=bool(anchors.get("has_non_shared_anchor")),
        ambiguity_class=str(packet_quality.get("ambiguity_class", "")).strip() or str(retrieval_plan.get("ambiguity_class", "")).strip(),
        guidance_coverage=str(packet_quality.get("guidance_coverage", "")).strip() or str(retrieval_plan.get("guidance_coverage", "")).strip(),
        intent_family=str(intent_profile.get("family", "")).strip(),
        actionability_score=int(actionability_payload.get("score", 0) or packet_quality.get("actionability_score", 0) or 0),
        validation_score=int(validation_pressure_payload.get("score", 0) or packet_quality.get("validation_pressure_score", 0) or 0),
        context_density_score=int(context_density_payload.get("score", 0) or packet_quality.get("context_density_score", 0) or 0),
        evidence_quality_score=int(evidence_quality_payload.get("score", 0) or packet_quality.get("evidence_quality_score", 0) or 0),
        evidence_consensus=str(packet_quality.get("evidence_consensus", "")).strip() or str(retrieval_plan.get("evidence_consensus", "")).strip(),
        precision_score=int(packet_quality.get("precision_score", 0) or retrieval_plan.get("precision_score", 0) or 0),
        direct_guidance_chunk_count=int(packet_quality.get("direct_guidance_chunk_count", 0) or selected_counts.get("guidance", 0) or 0),
        actionable_guidance_chunk_count=int(packet_quality.get("actionable_guidance_chunk_count", 0) or selected_counts.get("guidance", 0) or 0),
        selected_test_count=selected_test_count,
        selected_command_count=selected_command_count,
        selected_doc_count=selected_doc_count,
        strict_gate_command_count=strict_gate_command_count,
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
    )
    native_spawn_ready = routing.native_spawn_execution_ready(
        route_ready=route_ready,
        full_scan_recommended=bool(payload.get("full_scan_recommended") or context_packet.get("full_scan_recommended")),
        narrowing_required=bool(routing_handoff.get("narrowing_required") or route.get("narrowing_required")),
        within_budget=within_budget,
        delegate_preference=str(odylith_execution.get("delegate_preference", "")).strip(),
        model=str(odylith_execution.get("model", "")).strip(),
        reasoning_effort=str(odylith_execution.get("reasoning_effort", "")).strip(),
        agent_role=str(odylith_execution.get("agent_role", "")).strip(),
        selection_mode=str(odylith_execution.get("selection_mode", "")).strip(),
        selected_test_count=selected_test_count,
        selected_command_count=selected_command_count,
        selected_doc_count=selected_doc_count,
        strict_gate_command_count=strict_gate_command_count,
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
    )
    full_scan_reason = str(payload.get("full_scan_reason", "")).strip() or str(context_packet.get("full_scan_reason", "")).strip()
    changed_paths = _normalized_string_list(payload.get("changed_paths")) or _normalized_string_list(anchors.get("changed_paths"))
    explicit_paths = _normalized_string_list(payload.get("explicit_paths")) or _normalized_string_list(anchors.get("explicit_paths"))
    claimed_paths = _normalized_string_list(session_payload.get("claimed_paths"))
    path_tokens = _normalized_string_list([*changed_paths, *explicit_paths, *claimed_paths])
    packet_state = str(payload.get("context_packet_state", "")).strip() or str(context_packet.get("packet_state", "")).strip()
    packet_kind = _payload_packet_kind(payload, context_packet=context_packet, routing_handoff=routing_handoff)
    workstream_selection = odylith_context_engine_hot_path_packet_core_runtime._hot_path_workstream_selection(payload)
    selection_state = str(workstream_selection.get("state", "")).strip() or "none"
    proof_state = proof_state_runtime.normalize_proof_state(payload.get("proof_state"))
    if not proof_state and isinstance(context_packet.get("proof_state"), Mapping):
        proof_state = proof_state_runtime.normalize_proof_state(context_packet.get("proof_state"))
    proof_state_resolution = (
        dict(payload.get("proof_state_resolution", {}))
        if isinstance(payload.get("proof_state_resolution"), Mapping)
        else dict(context_packet.get("proof_state_resolution", {}))
        if isinstance(context_packet.get("proof_state_resolution"), Mapping)
        else {}
    )
    claim_guard = (
        dict(payload.get("claim_guard", {}))
        if isinstance(payload.get("claim_guard"), Mapping)
        else dict(context_packet.get("claim_guard", {}))
        if isinstance(context_packet.get("claim_guard"), Mapping)
        else proof_state_runtime.build_claim_guard(proof_state)
        if proof_state
        else {}
    )
    proof_reopen = proof_state_runtime.proof_reopen_signal(proof_state) if proof_state else {}
    proof_resolution_state = str(proof_state_resolution.get("state", "")).strip() or ("resolved" if proof_state else "none")
    execution_engine_payload = (
        dict(payload.get("execution_engine", {}))
        if isinstance(payload.get("execution_engine"), Mapping)
        else dict(context_packet.get("execution_engine", {}))
        if isinstance(context_packet.get("execution_engine"), Mapping)
        else runtime_surface_governance.build_packet_execution_engine_snapshot(
            payload=payload,
            context_packet=context_packet,
            routing_handoff=routing_handoff,
        )
    )
    summary = {
        "bootstrapped_at": str(payload.get("bootstrapped_at", "")).strip(),
        "session_id": str(session_payload.get("session_id", "")).strip() or str(scratch.get("session_id", "")).strip(),
        "workstream": _payload_workstream_hint(payload)
        or str(session_payload.get("workstream", "")).strip()
        or (
            _normalized_string_list(selection_payload.get("workstream_ids"))[0]
            if _normalized_string_list(selection_payload.get("workstream_ids"))
            else ""
        ),
        "packet_kind": packet_kind,
        "selection_state": selection_state,
        "packet_state": packet_state,
        "estimated_bytes": int(packet_metrics.get("estimated_bytes", 0) or 0),
        "estimated_tokens": int(packet_metrics.get("estimated_tokens", 0) or 0),
        "within_budget": within_budget,
        "observed_route_ready": observed_route_ready,
        "observed_native_spawn_ready": observed_native_spawn_ready,
        "route_ready": route_ready,
        "native_spawn_ready": native_spawn_ready,
        "routing_confidence": str(routing_handoff.get("routing_confidence", "")).strip()
        or str(packet_quality.get("routing_confidence", "")).strip(),
        "parallelism_hint": str(routing_handoff.get("parallelism_hint", "")).strip()
        or str(packet_quality.get("parallelism_hint", "")).strip(),
        "reasoning_bias": str(routing_handoff.get("reasoning_bias", "")).strip()
        or str(packet_quality.get("reasoning_bias", "")).strip(),
        "context_richness": str(packet_quality.get("context_richness", "")).strip(),
        "accuracy_posture": str(packet_quality.get("accuracy_posture", "")).strip(),
        "utility_score": int(utility_profile.get("score", 0) or 0),
        "utility_level": str(utility_profile.get("level", "")).strip(),
        "retained_signal_count": int(utility_profile.get("retained_signal_count", 0) or 0),
        "density_per_1k_tokens": float(utility_profile.get("density_per_1k_tokens", 0.0) or 0.0),
        "token_efficiency_score": int(token_efficiency.get("score", 0) or 0),
        "token_efficiency_level": str(token_efficiency.get("level", "")).strip(),
        "context_density_score": int(context_density.get("score", 0) or 0),
        "context_density_level": str(context_density.get("level", "")).strip(),
        "context_density_per_1k_tokens": float(context_density.get("density_per_1k_tokens", 0.0) or 0.0),
        "reasoning_readiness_score": int(reasoning_readiness.get("score", 0) or 0),
        "reasoning_readiness_level": str(reasoning_readiness.get("level", "")).strip(),
        "reasoning_readiness_mode": str(reasoning_readiness.get("mode", "")).strip(),
        "deep_reasoning_ready": bool(reasoning_readiness.get("deep_reasoning_ready")),
        "evidence_diversity_score": int(evidence_diversity.get("score", 0) or 0),
        "evidence_diversity_level": str(evidence_diversity.get("level", "")).strip(),
        "evidence_diversity_domain_count": int(evidence_diversity.get("domain_count", 0) or 0),
        "adaptive_packet_strategy": str(adaptive_packet_profile.get("packet_strategy", "")).strip(),
        "adaptive_budget_mode": str(adaptive_packet_profile.get("budget_mode", "")).strip(),
        "adaptive_retrieval_focus": str(adaptive_packet_profile.get("retrieval_focus", "")).strip(),
        "adaptive_speed_mode": str(adaptive_packet_profile.get("speed_mode", "")).strip(),
        "adaptive_reliability": str(adaptive_packet_profile.get("reliability", "")).strip(),
        "adaptive_selection_bias": str(adaptive_packet_profile.get("selection_bias", "")).strip(),
        "adaptive_budget_scale": float(adaptive_packet_profile.get("budget_scale", 0.0) or 0.0),
        "adaptive_source": str(adaptive_packet_profile.get("source", "")).strip(),
        "intent_family": str(intent_profile.get("family", "")).strip(),
        "intent_mode": str(intent_profile.get("mode", "")).strip(),
        "intent_critical_path": str(intent_profile.get("critical_path", "")).strip(),
        "intent_confidence": str(intent_profile.get("confidence", "")).strip(),
        "intent_explicit": bool(intent_profile.get("explicit")),
        "odylith_execution_profile": str(odylith_execution.get("profile", "")).strip(),
        "odylith_execution_model": str(odylith_execution.get("model", "")).strip(),
        "odylith_execution_reasoning_effort": str(odylith_execution.get("reasoning_effort", "")).strip(),
        "odylith_execution_agent_role": str(odylith_execution.get("agent_role", "")).strip(),
        "odylith_execution_selection_mode": str(odylith_execution.get("selection_mode", "")).strip(),
        "odylith_execution_delegate_preference": str(odylith_execution.get("delegate_preference", "")).strip(),
        "odylith_execution_source": str(odylith_execution.get("source", "")).strip(),
        "odylith_execution_confidence_score": int(odylith_execution_confidence.get("score", 0) or 0),
        "odylith_execution_confidence_level": str(odylith_execution_confidence.get("level", "")).strip(),
        "odylith_execution_route_ready": bool(odylith_execution_constraints.get("route_ready")),
        "odylith_execution_narrowing_required": bool(odylith_execution_constraints.get("narrowing_required")),
        "odylith_execution_spawn_worthiness": int(odylith_execution_constraints.get("spawn_worthiness", 0) or 0),
        "odylith_execution_merge_burden": int(odylith_execution_constraints.get("merge_burden", 0) or 0),
        "odylith_execution_reasoning_mode": str(odylith_execution_constraints.get("reasoning_mode", "")).strip(),
        "narrowing_required": bool(routing_handoff.get("narrowing_required") or route.get("narrowing_required")),
        "miss_recovery_active": bool(miss_recovery.get("active")),
        "miss_recovery_applied": bool(miss_recovery.get("applied")),
        "miss_recovery_mode": str(miss_recovery.get("mode", "")).strip(),
        "proof_state_present": bool(proof_state),
        "proof_resolution_state": proof_resolution_state,
        "proof_lane_id": str(proof_state.get("lane_id", "")).strip(),
        "proof_status": str(proof_state.get("proof_status", "")).strip(),
        "proof_failure_fingerprint": str(proof_state.get("failure_fingerprint", "")).strip(),
        "proof_frontier_phase": str(proof_state.get("frontier_phase", "")).strip(),
        "proof_first_failing_phase": str(proof_state.get("first_failing_phase", "")).strip(),
        "proof_linked_bug_id": str(proof_state.get("linked_bug_id", "")).strip(),
        "proof_evidence_tier": str(proof_state.get("evidence_tier", "")).strip(),
        "claim_guard_highest_truthful_claim": str(claim_guard.get("highest_truthful_claim", "")).strip(),
        "claim_guard_hosted_frontier_advanced": bool(claim_guard.get("hosted_frontier_advanced")),
        "claim_guard_same_fingerprint_as_last_falsification": bool(
            claim_guard.get("same_fingerprint_as_last_falsification")
        ),
        "claim_guard_claim_scope": str(claim_guard.get("claim_scope", "")).strip(),
        "claim_guard_gate_state": str(
            dict(claim_guard.get("gate", {})).get("state", "")
            if isinstance(claim_guard.get("gate"), Mapping)
            else ""
        ).strip(),
        "proof_same_fingerprint_reopened": bool(proof_reopen.get("same_fingerprint_reopened")),
        "proof_reopen_linked_bug_id": str(proof_reopen.get("linked_bug_id", "")).strip(),
        "proof_reopen_repeated_fingerprint_count": int(proof_reopen.get("repeated_fingerprint_count", 0) or 0),
        "selected_doc_count": selected_doc_count,
        "selected_test_count": selected_test_count,
        "selected_command_count": selected_command_count,
        "strict_gate_command_count": strict_gate_command_count,
        "plan_binding_required": bool(validation_bundle.get("plan_binding_required")),
        "governed_surface_sync_required": bool(validation_bundle.get("governed_surface_sync_required")),
        "turn_intent": str(turn_context.get("intent", "")).strip(),
        "turn_surface_count": len(_normalized_string_list(turn_context.get("surfaces"))),
        "turn_visible_text_count": len(_normalized_string_list(turn_context.get("visible_text"))),
        "turn_active_tab": str(turn_context.get("active_tab", "")).strip(),
        "turn_user_turn_id": str(turn_context.get("user_turn_id", "")).strip(),
        "turn_supersedes_turn_id": str(turn_context.get("supersedes_turn_id", "")).strip(),
        "target_resolution_lane": str(target_resolution.get("lane", "")).strip(),
        "target_resolution_candidate_count": len(
            [row for row in target_resolution.get("candidate_targets", []) if isinstance(row, Mapping)]
        ),
        "target_resolution_diagnostic_anchor_count": len(
            [row for row in target_resolution.get("diagnostic_anchors", []) if isinstance(row, Mapping)]
        ),
        "target_resolution_has_writable_targets": bool(target_resolution.get("has_writable_targets")),
        "target_resolution_requires_more_consumer_context": bool(
            target_resolution.get("requires_more_consumer_context")
        ),
        "target_resolution_consumer_failover": str(target_resolution.get("consumer_failover", "")).strip(),
        "presentation_policy_commentary_mode": str(presentation_policy.get("commentary_mode", "")).strip(),
        "presentation_policy_suppress_routing_receipts": bool(
            presentation_policy.get("suppress_routing_receipts")
        ),
        "presentation_policy_surface_fast_lane": bool(presentation_policy.get("surface_fast_lane")),
        "full_scan_reason": full_scan_reason,
        "changed_paths": changed_paths,
        "explicit_paths": explicit_paths,
        "claimed_paths": claimed_paths,
        "path_tokens": path_tokens,
    }
    summary.update(
        runtime_surface_governance.summary_fields_from_execution_engine(
            execution_engine_payload
        )
    )
    degraded_reason = _repo_scan_degraded_reason(summary)
    summary["repo_scan_degraded"] = bool(degraded_reason)
    summary["repo_scan_degraded_reason"] = degraded_reason
    hard_grounding_failure_reason = _hard_grounding_failure_reason(
        full_scan_reason=full_scan_reason,
        path_tokens=path_tokens,
    )
    soft_widening_reason = _soft_widening_reason(
        full_scan_reason=full_scan_reason,
        packet_state=packet_state,
        path_tokens=path_tokens,
    )
    visible_fallback_receipt_reason = _visible_fallback_receipt_reason(
        payload=payload,
        context_packet=context_packet,
        retrieval_plan=retrieval_plan,
        full_scan_reason=full_scan_reason,
        packet_state=packet_state,
        path_tokens=path_tokens,
    )
    summary["hard_grounding_failure"] = bool(hard_grounding_failure_reason)
    summary["hard_grounding_failure_reason"] = hard_grounding_failure_reason
    summary["soft_widening"] = bool(soft_widening_reason)
    summary["soft_widening_reason"] = soft_widening_reason
    summary["visible_fallback_receipt"] = bool(visible_fallback_receipt_reason)
    summary["visible_fallback_receipt_reason"] = visible_fallback_receipt_reason
    return summary


_SOFT_WIDENING_REASONS = {
    "broad_shared_paths",
    "working_tree_scope_degraded",
}

_VISIBLE_FALLBACK_RECEIPT_REASONS = {
    "broad_shared_paths",
    "working_tree_scope_degraded",
}


def _hard_grounding_failure_reason(
    *,
    full_scan_reason: str,
    path_tokens: Sequence[str],
) -> str:
    if _normalized_string_list(path_tokens):
        return ""
    return str(full_scan_reason or "").strip() or "no_grounded_paths"


def _soft_widening_reason(
    *,
    full_scan_reason: str,
    packet_state: str,
    path_tokens: Sequence[str],
) -> str:
    if not _normalized_string_list(path_tokens):
        return ""
    normalized_reason = str(full_scan_reason or "").strip()
    if normalized_reason in _SOFT_WIDENING_REASONS:
        return normalized_reason
    if str(packet_state or "").strip() == "gated_broad_scope":
        return normalized_reason or "gated_broad_scope"
    return ""


def _visible_fallback_receipt_reason(
    *,
    payload: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    retrieval_plan: Mapping[str, Any],
    full_scan_reason: str,
    packet_state: str,
    path_tokens: Sequence[str],
) -> str:
    if not _normalized_string_list(path_tokens):
        return ""
    fallback_scan = dict(payload.get("fallback_scan", {})) if isinstance(payload.get("fallback_scan"), Mapping) else {}
    reason_candidates = [
        str(full_scan_reason or "").strip(),
        str(context_packet.get("full_scan_reason", "")).strip(),
        str(retrieval_plan.get("full_scan_reason", "")).strip(),
        str(fallback_scan.get("reason", "")).strip(),
    ]
    for reason in reason_candidates:
        if reason in _VISIBLE_FALLBACK_RECEIPT_REASONS:
            return reason
    if fallback_scan and str(packet_state or "").strip() == "gated_broad_scope":
        return "fallback_scan_present"
    return ""
