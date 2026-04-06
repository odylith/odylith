from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.context_engine import session_bootstrap_payload_compactor


def bind(host: Any) -> None:
    lookup = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    globals().update({
        "_CODEX_HOT_PATH_PROFILE": lookup("_CODEX_HOT_PATH_PROFILE"),
        "_HOT_PATH_AUTO_ESCALATION_ARCHITECTURE_FAMILIES": lookup("_HOT_PATH_AUTO_ESCALATION_ARCHITECTURE_FAMILIES"),
        "_HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES": lookup("_HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES"),
        "_HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES": lookup("_HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES"),
        "_HOT_PATH_SUMMARY_ONLY_FALLBACK_FAMILIES": lookup("_HOT_PATH_SUMMARY_ONLY_FALLBACK_FAMILIES"),
        "_PROCESS_ARCHITECTURE_PACKET_CACHE": lookup("_PROCESS_ARCHITECTURE_PACKET_CACHE"),
        "_architecture_bundle_mermaid_signature_hash": lookup("_architecture_bundle_mermaid_signature_hash"),
        "_bootstrap_record_path": lookup("_bootstrap_record_path"),
        "_bootstrap_relevant_docs": lookup("_bootstrap_relevant_docs"),
        "_broad_shared_only_input": lookup("_broad_shared_only_input"),
        "_compact_bootstrap_workstream_selection": lookup("_compact_bootstrap_workstream_selection"),
        "_compact_component_row_for_packet": lookup("_compact_component_row_for_packet"),
        "_compact_context_dossier": lookup("_compact_context_dossier"),
        "_compact_diagram_row_for_packet": lookup("_compact_diagram_row_for_packet"),
        "_compact_engineering_notes": lookup("_compact_engineering_notes"),
        "_compact_hot_path_payload_within_budget": lookup("_compact_hot_path_payload_within_budget"),
        "_compact_hot_path_runtime_packet": lookup("_compact_hot_path_runtime_packet"),
        "_compact_miss_recovery_for_packet": lookup("_compact_miss_recovery_for_packet"),
        "_compact_packet_level_architecture_audit": lookup("_compact_packet_level_architecture_audit"),
        "_compact_runtime_timing_rows_for_packet": lookup("_compact_runtime_timing_rows_for_packet"),
        "_compact_stage_timings": lookup("_compact_stage_timings"),
        "_compact_test_row_for_packet": lookup("_compact_test_row_for_packet"),
        "_compact_truncation_for_summary": lookup("_compact_truncation_for_summary"),
        "_compact_workstream_reference_for_packet": lookup("_compact_workstream_reference_for_packet"),
        "_compact_workstream_row_for_packet": lookup("_compact_workstream_row_for_packet"),
        "_compact_workstream_selection_for_packet": lookup("_compact_workstream_selection_for_packet"),
        "_companion_context_paths": lookup("_companion_context_paths"),
        "_connect": lookup("_connect"),
        "_decode_compact_selected_counts": lookup("_decode_compact_selected_counts"),
        "_decode_hot_path_execution_profile": lookup("_decode_hot_path_execution_profile"),
        "_dedupe_strings": lookup("_dedupe_strings"),
        "_delivery_profile_hot_path": lookup("_delivery_profile_hot_path"),
        "_elapsed_stage_ms": lookup("_elapsed_stage_ms"),
        "_fallback_scan_payload": lookup("_fallback_scan_payload"),
        "_full_scan_guidance": lookup("_full_scan_guidance"),
        "_git_branch_name": lookup("_git_branch_name"),
        "_git_head_oid": lookup("_git_head_oid"),
        "_governance_closeout_doc_count": lookup("_governance_closeout_doc_count"),
        "_hot_path_auto_escalation_trigger": lookup("_hot_path_auto_escalation_trigger"),
        "_hot_path_can_hold_local_narrowing_without_full_scan": lookup("_hot_path_can_hold_local_narrowing_without_full_scan"),
        "_hot_path_execution_profile_runtime_fields": lookup("_hot_path_execution_profile_runtime_fields"),
        "_hot_path_full_scan_reason": lookup("_hot_path_full_scan_reason"),
        "_hot_path_full_scan_recommended": lookup("_hot_path_full_scan_recommended"),
        "_hot_path_governance_obligations": lookup("_hot_path_governance_obligations"),
        "_hot_path_packet_rank": lookup("_hot_path_packet_rank"),
        "_hot_path_payload_is_compact": lookup("_hot_path_payload_is_compact"),
        "_hot_path_route_ready": lookup("_hot_path_route_ready"),
        "_hot_path_routing_confidence": lookup("_hot_path_routing_confidence"),
        "_hot_path_synthesized_execution_profile": lookup("_hot_path_synthesized_execution_profile"),
        "_hot_path_validation_bundle": lookup("_hot_path_validation_bundle"),
        "_hot_path_workstream_selection": lookup("_hot_path_workstream_selection"),
        "_impact_packet_state": lookup("_impact_packet_state"),
        "_impact_summary_payload": lookup("_impact_summary_payload"),
        "_load_judgment_workstream_hint": lookup("_load_judgment_workstream_hint"),
        "_local_runtime_execution_summary": lookup("_local_runtime_execution_summary"),
        "_normalize_claim_mode": lookup("_normalize_claim_mode"),
        "_normalize_family_hint": lookup("_normalize_family_hint"),
        "_normalized_string_list": lookup("_normalized_string_list"),
        "_packet_benchmark_summary_for_runtime_packet": lookup("_packet_benchmark_summary_for_runtime_packet"),
        "_payload_packet_kind": lookup("_payload_packet_kind"),
        "_payload_workstream_hint": lookup("_payload_workstream_hint"),
        "_projection_cache_signature": lookup("_projection_cache_signature"),
        "_repo_scan_degraded_reason": lookup("_repo_scan_degraded_reason"),
        "_resolve_changed_path_scope_context": lookup("_resolve_changed_path_scope_context"),
        "_session_conflicts": lookup("_session_conflicts"),
        "_should_escalate_hot_path_to_session_brief": lookup("_should_escalate_hot_path_to_session_brief"),
        "_update_compact_hot_path_runtime_packet": lookup("_update_compact_hot_path_runtime_packet"),
        "_utc_now": lookup("_utc_now"),
        "_validation_bundle_command_count": lookup("_validation_bundle_command_count"),
        "_warm_runtime": lookup("_warm_runtime"),
        "_workstream_selection": lookup("_workstream_selection"),
        "build_impact_report": lookup("build_impact_report"),
        "list_session_states": lookup("list_session_states"),
        "load_context_dossier": lookup("load_context_dossier"),
        "load_runtime_optimization_snapshot": lookup("load_runtime_optimization_snapshot"),
        "load_runtime_timing_summary": lookup("load_runtime_timing_summary"),
        "odylith_architecture_mode": lookup("odylith_architecture_mode"),
        "odylith_context_cache": lookup("odylith_context_cache"),
        "odylith_evaluation_ledger": lookup("odylith_evaluation_ledger"),
        "prune_runtime_records": lookup("prune_runtime_records"),
        "read_runtime_state": lookup("read_runtime_state"),
        "record_runtime_timing": lookup("record_runtime_timing"),
        "register_session_state": lookup("register_session_state"),
        "request_runtime_daemon": lookup("request_runtime_daemon"),
        "routing": lookup("routing"),
        "tooling_context_packet_builder": lookup("tooling_context_packet_builder"),
        "tooling_guidance_catalog": lookup("tooling_guidance_catalog"),
    })


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
    odylith_execution = _decode_hot_path_execution_profile(
        routing_handoff.get("execution_profile") or routing_handoff.get("odylith_execution_profile")
    )
    if not odylith_execution and isinstance(context_packet.get("execution_profile"), Mapping):
        odylith_execution = dict(context_packet.get("execution_profile", {}))
    if odylith_execution and not str(odylith_execution.get("model", "")).strip():
        model, reasoning_effort = _hot_path_execution_profile_runtime_fields(
            str(odylith_execution.get("profile", "")).strip()
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
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    selection_payload = dict(context_packet.get("selection", {})) if isinstance(context_packet.get("selection"), Mapping) else {}
    working_memory = dict(context_packet.get("working_memory", {})) if isinstance(context_packet.get("working_memory"), Mapping) else {}
    scratch = dict(working_memory.get("scratch", {})) if isinstance(working_memory.get("scratch"), Mapping) else {}
    validation_bundle = _hot_path_validation_bundle(payload, context_packet=context_packet)
    governance_obligations = _hot_path_governance_obligations(payload, context_packet=context_packet)
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
    within_budget = _compact_hot_path_payload_within_budget(
        payload=payload,
        context_packet=context_packet,
        packet_metrics=packet_metrics,
    )
    observed_route_ready = bool(routing_handoff.get("route_ready") or route.get("route_ready"))
    observed_native_spawn_ready = bool(routing_handoff.get("native_spawn_ready") or route.get("native_spawn_ready"))
    selected_doc_count = max(
        int(packet_quality.get("retained_doc_count", 0) or 0),
        _governance_closeout_doc_count(governance_obligations),
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
    strict_gate_command_count = _validation_bundle_command_count(
        validation_bundle,
        list_key="strict_gate_commands",
        count_key="strict_gate_command_count",
    )
    if not odylith_execution:
        odylith_execution = _hot_path_synthesized_execution_profile(
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
            closeout_doc_count=_governance_closeout_doc_count(governance_obligations),
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
        "selected_doc_count": selected_doc_count,
        "selected_test_count": selected_test_count,
        "selected_command_count": selected_command_count,
        "strict_gate_command_count": strict_gate_command_count,
        "plan_binding_required": bool(validation_bundle.get("plan_binding_required")),
        "governed_surface_sync_required": bool(validation_bundle.get("governed_surface_sync_required")),
        "full_scan_reason": full_scan_reason,
        "changed_paths": changed_paths,
        "explicit_paths": explicit_paths,
        "claimed_paths": claimed_paths,
        "path_tokens": path_tokens,
    }
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


def build_architecture_audit(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    detail_level: str = "compact",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}

    def _record_architecture_timing(payload: Mapping[str, Any]) -> dict[str, Any]:
        sanitized = dict(payload)
        stage_timings = _compact_stage_timings(
            dict(sanitized.pop("_stage_timings", {}))
            if isinstance(sanitized.get("_stage_timings"), Mapping)
            else {}
        )
        coverage = dict(payload.get("coverage", {})) if isinstance(payload.get("coverage"), Mapping) else {}
        benchmark_summary = (
            dict(payload.get("benchmark_summary", {})) if isinstance(payload.get("benchmark_summary"), Mapping) else {}
        )
        execution_hint = dict(payload.get("execution_hint", {})) if isinstance(payload.get("execution_hint"), Mapping) else {}
        authority_graph = dict(payload.get("authority_graph", {})) if isinstance(payload.get("authority_graph"), Mapping) else {}
        encoded = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        record_runtime_timing(
            repo_root=root,
            category="reasoning",
            operation="architecture",
            duration_ms=round((time.perf_counter() - started_at) * 1000.0, 3),
            metadata={
                "resolved": bool(sanitized.get("resolved")),
                "changed_paths": [str(token).strip() for token in sanitized.get("changed_paths", []) if str(token).strip()]
                if isinstance(sanitized.get("changed_paths"), list)
                else [],
                "explicit_paths": [str(token).strip() for token in sanitized.get("explicit_paths", []) if str(token).strip()]
                if isinstance(sanitized.get("explicit_paths"), list)
                else [],
                "domain_ids": [
                    str(row.get("domain_id", "")).strip()
                    for row in sanitized.get("topology_domains", [])
                    if isinstance(row, Mapping) and str(row.get("domain_id", "")).strip()
                ]
                if isinstance(sanitized.get("topology_domains"), list)
                else [],
                "confidence_tier": str(coverage.get("confidence_tier", "")).strip(),
                "full_scan_recommended": bool(sanitized.get("full_scan_recommended")),
                "full_scan_reason": str(sanitized.get("full_scan_reason", "")).strip(),
                "contract_touchpoint_count": (
                    len(sanitized.get("contract_touchpoints", []))
                    if isinstance(sanitized.get("contract_touchpoints"), list)
                    else int(sanitized.get("contract_touchpoint_count", 0) or 0)
                ),
                "execution_hint_mode": str(execution_hint.get("mode", "")).strip(),
                "risk_tier": str(execution_hint.get("risk_tier", "")).strip(),
                "estimated_bytes": len(encoded.encode("utf-8")),
                "estimated_tokens": max(1, len(encoded.encode("utf-8")) // 4),
                "benchmark_matched_case_count": int(benchmark_summary.get("matched_case_count", 0) or 0),
                "benchmark_satisfied_case_count": int(benchmark_summary.get("satisfied_case_count", 0) or 0),
                "authority_graph_edge_count": int(dict(authority_graph.get("counts", {})).get("edges", 0) or 0)
                if isinstance(authority_graph.get("counts"), Mapping)
                else 0,
                "authority_graph_traceability_edges": int(
                    dict(authority_graph.get("counts", {})).get("traceability_edges", 0) or 0
                )
                if isinstance(authority_graph.get("counts"), Mapping)
                else 0,
                "stage_timings": stage_timings,
            },
        )
        return sanitized

    path_scope = _resolve_changed_path_scope_context(
        repo_root=root,
        explicit_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
    )
    normalized = list(path_scope["analysis_paths"])
    if not normalized:
        full_scan_reason = (
            "working_tree_scope_degraded"
            if bool(path_scope.get("working_tree_scope_degraded"))
            else "no_grounded_paths"
        )
        return _record_architecture_timing({
            "resolved": False,
            "changed_paths": [],
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "topology_domains": [],
            "linked_components": [],
            "linked_diagrams": [],
            "required_reads": [],
            "diagram_watch_gaps": [],
            "full_scan_recommended": True,
            "full_scan_reason": full_scan_reason,
            "fallback_scan": _full_scan_guidance(
                repo_root=root,
                reason=full_scan_reason,
                changed_paths=[
                    *list(path_scope["explicit_paths"]),
                    *list(path_scope["repo_dirty_paths"]),
                ],
            ),
        })
    if not _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="architecture", scope="reasoning"):
        return _record_architecture_timing({
            "resolved": False,
            "changed_paths": normalized,
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "topology_domains": [],
            "linked_components": [],
            "linked_diagrams": [],
            "required_reads": [],
            "diagram_watch_gaps": [],
            "full_scan_recommended": True,
            "full_scan_reason": "runtime_unavailable",
            "fallback_scan": _full_scan_guidance(
                repo_root=root,
                reason="runtime_unavailable",
                changed_paths=normalized,
            ),
        })
    architecture_bundle = odylith_architecture_mode.load_architecture_bundle(repo_root=root)
    cache_key = json.dumps(
        {
            "fingerprint": _projection_cache_signature(repo_root=root, scope="reasoning"),
            "bundle_signature": odylith_architecture_mode._architecture_bundle_signature(  # noqa: SLF001
                repo_root=root,
                bundle=architecture_bundle,
            ),
            "benchmark_cases_hash": odylith_architecture_mode._architecture_benchmark_cases_hash(repo_root=root),  # noqa: SLF001
            "mermaid_drift_hash": _architecture_bundle_mermaid_signature_hash(
                repo_root=root,
                bundle=architecture_bundle,
            ),
            "changed_paths": normalized,
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "detail_level": str(detail_level or "compact").strip() or "compact",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    cached_payload = _PROCESS_ARCHITECTURE_PACKET_CACHE.get(cache_key)
    if isinstance(cached_payload, Mapping):
        cached = dict(cached_payload)
        cached["_stage_timings"] = {"cache_hit": 0.0}
        return _record_architecture_timing(cached)
    stage_started = time.perf_counter()
    payload = odylith_architecture_mode.build_architecture_dossier(
        repo_root=root,
        changed_paths=normalized,
        explicit_paths=list(path_scope["explicit_paths"]),
        repo_dirty_paths=list(path_scope["repo_dirty_paths"]),
        scoped_working_tree_paths=list(path_scope["scoped_working_tree_paths"]),
        working_tree_scope=str(path_scope.get("working_tree_scope", "")).strip(),
        working_tree_scope_degraded=bool(path_scope.get("working_tree_scope_degraded")),
        detail_level=detail_level,
    )
    payload["required_reads"] = _dedupe_strings(
        [
            *_companion_context_paths(changed_paths=normalized, repo_root=root),
            *(
                str(token).strip()
                for token in payload.get("required_reads", [])
                if isinstance(payload.get("required_reads"), list) and str(token).strip()
            ),
        ]
    )
    payload_stage_timings = dict(payload.get("_stage_timings", {})) if isinstance(payload.get("_stage_timings"), Mapping) else {}
    for key, value in payload_stage_timings.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        try:
            stage_timings[normalized_key] = float(value or 0.0)
        except (TypeError, ValueError):
            continue
    stage_timings.setdefault("structural_core", _elapsed_stage_ms(stage_started))
    payload["fallback_scan"] = _full_scan_guidance(
        repo_root=root,
        reason=str(payload.get("full_scan_reason", "")).strip(),
        changed_paths=normalized,
    )
    if str(detail_level or "compact").strip() == "packet":
        payload = _compact_packet_level_architecture_audit(payload)
    payload["_stage_timings"] = dict(stage_timings)
    _PROCESS_ARCHITECTURE_PACKET_CACHE[cache_key] = {
        key: value
        for key, value in payload.items()
        if key != "_stage_timings"
    }
    return _record_architecture_timing(payload)


def build_session_brief(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    use_working_tree: bool = False,
    working_tree_scope: str = "session",
    runtime_mode: str = "auto",
    session_id: str = "",
    workstream: str = "",
    generated_surfaces: Sequence[str] = (),
    intent: str = "",
    claim_mode: str = "shared",
    claimed_paths: Sequence[str] = (),
    lease_seconds: int = 15 * 60,
    delivery_profile: str = "full",
    family_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    impact_override: Mapping[str, Any] | None = None,
    retain_impact_internal_context: bool | None = None,
    skip_impact_runtime_warmup: bool = False,
    compact_delivery: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}
    hot_path = _delivery_profile_hot_path(delivery_profile)
    stage_started = time.perf_counter()
    guidance_catalog = tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    optimization_snapshot = {} if hot_path else load_runtime_optimization_snapshot(repo_root=root)
    stage_timings["guidance_catalog"] = _elapsed_stage_ms(stage_started)
    stage_started = time.perf_counter()
    effective_session_id = re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "").strip()).strip("-") or f"codex-{os.getpid()}"
    path_scope = _resolve_changed_path_scope_context(
        repo_root=root,
        explicit_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=effective_session_id,
        claimed_paths=claimed_paths,
        intent=intent,
    )
    stage_timings["path_scope"] = _elapsed_stage_ms(stage_started)
    effective_paths = list(path_scope["analysis_paths"])
    explicit = list(path_scope["explicit_paths"])
    explicit_claims = list(path_scope["explicit_claim_paths"])
    if isinstance(impact_override, Mapping):
        impact = dict(impact_override)
        stage_timings["impact_reused"] = 0.0
    else:
        retain_internal_context = (
            hot_path if retain_impact_internal_context is None else bool(retain_impact_internal_context)
        )
        stage_started = time.perf_counter()
        impact_kwargs = {
            "repo_root": root,
            "changed_paths": changed_paths,
            "use_working_tree": use_working_tree,
            "working_tree_scope": working_tree_scope,
            "session_id": effective_session_id,
            "claimed_paths": claimed_paths,
            "runtime_mode": runtime_mode,
            "intent": intent,
            "delivery_profile": delivery_profile,
            "family_hint": family_hint,
            "workstream_hint": workstream,
            "validation_command_hints": validation_command_hints,
            "retain_hot_path_internal_context": retain_internal_context,
            "guidance_catalog_snapshot": guidance_catalog,
            "optimization_snapshot": optimization_snapshot,
            "skip_runtime_warmup": bool(skip_impact_runtime_warmup),
            "finalize_packet": not hot_path,
        }
        try:
            impact = build_impact_report(**impact_kwargs)
        except TypeError as exc:
            message = str(exc)
            if "skip_runtime_warmup" not in message and "finalize_packet" not in message:
                raise
            impact_kwargs.pop("skip_runtime_warmup", None)
            impact_kwargs.pop("finalize_packet", None)
            impact = build_impact_report(**impact_kwargs)
        stage_timings["impact"] = _elapsed_stage_ms(stage_started)
    if isinstance(impact.get("changed_paths"), list):
        effective_paths = [str(token) for token in impact.get("changed_paths", []) if str(token).strip()]
    candidate_workstreams = (
        [dict(row) for row in impact.get("candidate_workstreams", []) if isinstance(row, Mapping)]
        if isinstance(impact.get("candidate_workstreams"), list)
        else []
    )
    stage_started = time.perf_counter()
    impact_selection = _hot_path_workstream_selection(impact) if hot_path else {}
    if hot_path and str(workstream or "").strip():
        explicit_workstream = str(workstream or "").strip().upper()
        selection_reason = f"Using explicit workstream override `{explicit_workstream}`."
        selection = {
            "state": "explicit",
            "reason": selection_reason,
            "why_selected": selection_reason,
            "selected_workstream": {"entity_id": explicit_workstream},
            "top_candidate": {"entity_id": explicit_workstream},
            "score_gap": None,
            "confidence": "explicit",
            "candidate_count": len(candidate_workstreams),
            "ambiguity_class": "explicit",
            "strong_candidate_count": 1,
            "competing_candidates": [],
        }
    elif hot_path and impact_selection:
        selection = impact_selection
    else:
        try:
            connection = _connect(root)
        except RuntimeError:
            explicit_workstream = str(workstream or "").strip().upper()
            top_candidate = dict(candidate_workstreams[0]) if candidate_workstreams else {}
            competing_candidates = [dict(row) for row in candidate_workstreams[1:4]]
            selection_reason = (
                f"Explicit workstream `{explicit_workstream}` cannot resolve because runtime projections are unavailable."
                if explicit_workstream
                else "Runtime projections are unavailable for deterministic session routing."
            )
            selection = {
                "state": "none",
                "reason": selection_reason,
                "why_selected": selection_reason,
                "selected_workstream": {},
                "top_candidate": top_candidate if not explicit_workstream else {},
                "score_gap": None,
                "confidence": "none",
                "candidate_count": len(candidate_workstreams),
                "ambiguity_class": "runtime_unavailable",
                "strong_candidate_count": sum(
                    1
                    for row in candidate_workstreams
                    if int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0) > 0
                ),
                "competing_candidates": competing_candidates,
            }
        else:
            try:
                judgment_workstream_hint = _load_judgment_workstream_hint(repo_root=root, changed_paths=effective_paths)
                selection = _workstream_selection(
                    connection=connection,
                    candidates=candidate_workstreams,
                    explicit_workstream=str(workstream or "").strip(),
                    judgment_hint=judgment_workstream_hint,
                )
            finally:
                connection.close()
    stage_timings["selection"] = _elapsed_stage_ms(stage_started)
    selection_state = str(selection.get("state", "")).strip()
    selected_workstream = (
        dict(selection.get("selected_workstream", {}))
        if isinstance(selection.get("selected_workstream"), Mapping)
        else {}
    )
    inferred_workstream = (
        str(selected_workstream.get("entity_id", "")).strip().upper()
        if selection_state in {"explicit", "inferred_confident"}
        else ""
    )
    dossier = (
        load_context_dossier(repo_root=root, ref=inferred_workstream, kind="workstream", runtime_mode=runtime_mode)
        if inferred_workstream and not hot_path
        else {"resolved": False}
    )
    auto_claim_paths = list(explicit)
    stage_started = time.perf_counter()
    explicit_claim_paths = [str(token).strip() for token in explicit_claims if str(token).strip()]
    track_hot_path_session_state = bool(
        hot_path and (str(session_id or "").strip() or explicit_claim_paths or generated_surfaces)
    )
    if hot_path:
        session_state = {
            "session_id": effective_session_id if track_hot_path_session_state else "",
            "workstream": inferred_workstream,
            "intent": str(intent or "").strip(),
            "claim_mode": _normalize_claim_mode(claim_mode),
            "explicit_paths": explicit,
            "claimed_paths": _dedupe_strings([*auto_claim_paths, *explicit_claim_paths, *effective_paths]),
            "analysis_paths": effective_paths,
            "generated_surfaces": _dedupe_strings([str(token).strip() for token in generated_surfaces if str(token).strip()]),
            "selection_state": selection_state,
            "selection_reason": str(selection.get("reason", "")).strip(),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "branch_name": _git_branch_name(repo_root=root) if track_hot_path_session_state else "",
            "head_oid": _git_head_oid(repo_root=root) if track_hot_path_session_state else "",
            "updated_utc": _utc_now(),
        }
        active_sessions = list_session_states(repo_root=root, prune=False) if track_hot_path_session_state else []
    else:
        session_state = register_session_state(
            repo_root=root,
            session_id=effective_session_id,
            workstream=inferred_workstream,
            touched_paths=effective_paths,
            explicit_paths=explicit,
            repo_dirty_paths=path_scope["repo_dirty_paths"],
            analysis_paths=effective_paths,
            generated_surfaces=generated_surfaces,
            intent=intent,
            claim_mode=claim_mode,
            selection_state=selection_state,
            selection_reason=str(selection.get("reason", "")).strip(),
            working_tree_scope=str(path_scope.get("working_tree_scope", "")).strip(),
            auto_claim_paths=auto_claim_paths,
            claimed_paths=explicit_claims,
            lease_seconds=lease_seconds,
        )
        active_sessions = list_session_states(repo_root=root)
    stage_timings["session_state"] = _elapsed_stage_ms(stage_started)
    conflicts = (
        _session_conflicts(
            current_session_id=effective_session_id,
            workstream=inferred_workstream,
            changed_paths=session_state.get("claimed_paths", []),
            generated_surfaces=_dedupe_strings([str(token) for token in generated_surfaces]),
            session_rows=active_sessions,
            claim_mode=_normalize_claim_mode(claim_mode),
            current_branch_name=str(session_state.get("branch_name", "")).strip(),
            current_head_oid=str(session_state.get("head_oid", "")).strip(),
        )
        if (not hot_path or track_hot_path_session_state)
        else []
    )
    if conflicts:
        severity_rank = {"high": 0, "medium": 1, "low": 2}
        conflicts.sort(key=lambda row: (severity_rank.get(str(row.get("severity", "")).strip(), 99), str(row.get("session_id", ""))))
    packet_state = (
        "compact"
        if selection_state == "explicit"
        else (
            str(impact.get("context_packet_state", "")).strip()
            or _impact_packet_state(
                shared_only=_broad_shared_only_input(effective_paths),
                selection_state=selection_state,
            )
        )
    )
    packet_selection = _compact_workstream_selection_for_packet(selection)
    session_seed_paths = (
        list(path_scope["session_seed_paths"])
        if (
            not hot_path
            or track_hot_path_session_state
            or bool(impact.get("full_scan_recommended"))
        )
        else []
    )
    payload = {
        "session": session_state,
        "changed_paths": effective_paths,
        "explicit_paths": explicit,
        "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
        "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
        "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
        "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
        "session_seed_paths": session_seed_paths,
        "inferred_workstream": inferred_workstream,
        "selection_state": selection_state,
        "selection_reason": str(selection.get("reason", "")).strip(),
        "selection_confidence": str(selection.get("confidence", "")).strip(),
        "candidate_workstreams": impact.get("candidate_workstreams", []),
        "workstream_selection": packet_selection,
        "impact": _impact_summary_payload(impact),
        "workstream_context": (
            _compact_context_dossier(
                dossier,
                relation_limit_per_kind=2,
                event_limit=2,
                delivery_limit=1,
            )
            if not hot_path
            else {}
        ),
        "context_packet_state": packet_state,
        "truncation": _compact_truncation_for_summary(impact.get("truncation", {}))
        if isinstance(impact.get("truncation"), Mapping)
        else {},
        "full_scan_recommended": bool(impact.get("full_scan_recommended")) and selection_state != "explicit",
        "full_scan_reason": "" if selection_state == "explicit" else str(impact.get("full_scan_reason", "")).strip(),
        "fallback_scan": dict(impact.get("fallback_scan", {}))
        if isinstance(impact.get("fallback_scan"), Mapping)
        else {},
        "active_conflicts": [dict(row) for row in conflicts[:4] if isinstance(row, Mapping)],
        "active_session_count": len(active_sessions) if (not hot_path or track_hot_path_session_state) else 0,
    }
    if isinstance(payload.get("impact"), Mapping):
        impact_summary = dict(payload.get("impact", {}))
        docs = impact_summary.get("docs", [])
        if isinstance(docs, list):
            impact_summary["docs"] = _bootstrap_relevant_docs(
                [str(token).strip() for token in docs if str(token).strip()],
                guidance_rows=[dict(row) for row in impact_summary.get("guidance_brief", []) if isinstance(row, Mapping)]
                if isinstance(impact_summary.get("guidance_brief"), list)
                else [],
                limit=len(docs),
            )
        payload["impact"] = impact_summary
    impact_payload = payload.get("impact", {}) if isinstance(payload.get("impact"), Mapping) else {}
    stage_started = time.perf_counter()
    payload = tooling_context_packet_builder.finalize_packet(
        repo_root=root,
        packet_kind="session_brief",
        payload=payload,
        packet_state=packet_state,
        changed_paths=effective_paths,
        explicit_paths=explicit,
        shared_only_input=_broad_shared_only_input(effective_paths),
        selection_state=selection_state,
        workstream_selection=packet_selection,
        candidate_workstreams=payload.get("candidate_workstreams", [])
        if isinstance(payload.get("candidate_workstreams"), list)
        else [],
        components=impact_payload.get("components", []) if isinstance(impact_payload.get("components"), list) else [],
        diagrams=impact_payload.get("diagrams", []) if isinstance(impact_payload.get("diagrams"), list) else [],
        docs=impact_payload.get("docs", []) if isinstance(impact_payload.get("docs"), list) else [],
        recommended_commands=impact_payload.get("recommended_commands", [])
        if isinstance(impact_payload.get("recommended_commands"), list)
        else [],
        recommended_tests=impact_payload.get("recommended_tests", [])
        if isinstance(impact_payload.get("recommended_tests"), list)
        else [],
        engineering_notes=impact_payload.get("engineering_notes", {})
        if isinstance(impact_payload.get("engineering_notes"), Mapping)
        else {},
        miss_recovery=impact_payload.get("miss_recovery", {})
        if isinstance(impact_payload.get("miss_recovery"), Mapping)
        else {},
        full_scan_recommended=bool(payload.get("full_scan_recommended")),
        full_scan_reason=str(payload.get("full_scan_reason", "")).strip(),
        session_id=effective_session_id,
        family_hint=str(family_hint or "").strip(),
        guidance_catalog=guidance_catalog,
        optimization_snapshot=optimization_snapshot,
        delivery_profile=delivery_profile,
    )
    stage_timings["finalize"] = _elapsed_stage_ms(stage_started)
    timing_payload = payload
    if hot_path:
        payload = _compact_hot_path_runtime_packet(
            packet_kind="session_brief",
            payload=payload,
        )
    record_runtime_timing(
        repo_root=root,
        category="reasoning",
        operation="session_brief",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "changed_path_count": len(effective_paths),
            "has_workstream": bool(inferred_workstream),
            "conflict_count": len(payload.get("active_conflicts", []))
            if isinstance(payload.get("active_conflicts"), list)
            else 0,
            "selection_state": str(_hot_path_workstream_selection(payload).get("state", "")).strip(),
            "packet_state": str(payload.get("context_packet_state", "")).strip(),
            "estimated_bytes": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_bytes", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "estimated_tokens": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_tokens", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "stage_timings": _compact_stage_timings(stage_timings),
            "family_hint": _normalize_family_hint(family_hint),
        },
    )
    if hot_path or not compact_delivery:
        return payload
    return session_bootstrap_payload_compactor.compact_finalized_session_brief_payload(timing_payload)


def build_session_bootstrap(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    use_working_tree: bool = False,
    working_tree_scope: str = "session",
    runtime_mode: str = "auto",
    session_id: str = "",
    workstream: str = "",
    generated_surfaces: Sequence[str] = (),
    intent: str = "",
    claim_mode: str = "shared",
    claimed_paths: Sequence[str] = (),
    lease_seconds: int = 15 * 60,
    doc_limit: int = 8,
    command_limit: int = 10,
    test_limit: int = 8,
    delivery_profile: str = "full",
    family_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    retain_impact_internal_context: bool | None = None,
    skip_impact_runtime_warmup: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}
    hot_path = _delivery_profile_hot_path(delivery_profile)
    optimization_snapshot = {} if hot_path else load_runtime_optimization_snapshot(repo_root=root)
    stage_started = time.perf_counter()
    guidance_catalog = tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    stage_timings["guidance_catalog"] = _elapsed_stage_ms(stage_started)
    stage_started = time.perf_counter()
    brief = build_session_brief(
        repo_root=root,
        changed_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        runtime_mode=runtime_mode,
        session_id=session_id,
        workstream=workstream,
        generated_surfaces=generated_surfaces,
        intent=intent,
        claim_mode=claim_mode,
        claimed_paths=claimed_paths,
        lease_seconds=lease_seconds,
        delivery_profile=delivery_profile,
        family_hint=family_hint,
        validation_command_hints=validation_command_hints,
        retain_impact_internal_context=retain_impact_internal_context,
        skip_impact_runtime_warmup=skip_impact_runtime_warmup,
        compact_delivery=False,
    )
    stage_timings["session_brief"] = _elapsed_stage_ms(stage_started)
    impact = brief.get("impact", {}) if isinstance(brief.get("impact"), Mapping) else {}
    impact_doc_candidates: list[str] = []
    if isinstance(impact.get("docs"), list):
        impact_doc_candidates.extend(str(token).strip() for token in impact.get("docs", []) if str(token).strip())
    code_neighbors = impact.get("code_neighbors", {})
    if isinstance(code_neighbors, Mapping):
        for bucket_name in ("documented_by", "covered_by_runbooks"):
            bucket = code_neighbors.get(bucket_name, [])
            if not isinstance(bucket, list):
                continue
            impact_doc_candidates.extend(
                str(row.get("path", "")).strip()
                for row in bucket
                if isinstance(row, Mapping) and str(row.get("path", "")).strip()
            )
    relevant_docs = _bootstrap_relevant_docs(
        impact_doc_candidates,
        guidance_rows=[dict(row) for row in impact.get("guidance_brief", []) if isinstance(row, Mapping)]
        if isinstance(impact.get("guidance_brief"), list)
        else [],
        limit=max(1, int(doc_limit)),
    )
    recommended_commands = [
        str(token).strip()
        for token in impact.get("recommended_commands", [])[: max(1, int(command_limit))]
        if str(token).strip()
    ] if isinstance(impact.get("recommended_commands"), list) else []
    recommended_tests = [
        _compact_test_row_for_packet(row)
        for row in impact.get("recommended_tests", [])[: max(1, int(test_limit))]
        if isinstance(row, Mapping)
    ] if isinstance(impact.get("recommended_tests"), list) else []
    stage_started = time.perf_counter()
    timing_summary = load_runtime_timing_summary(repo_root=root, limit=12) if not hot_path else {}
    runtime_state = read_runtime_state(repo_root=root) if not hot_path else {}
    stage_timings["runtime_state"] = _elapsed_stage_ms(stage_started)
    brief_context_packet = dict(brief.get("context_packet", {})) if isinstance(brief.get("context_packet"), Mapping) else {}
    brief_route = dict(brief_context_packet.get("route", {})) if isinstance(brief_context_packet.get("route"), Mapping) else {}
    brief_selection = _hot_path_workstream_selection(brief)
    payload = {
        "bootstrapped_at": _utc_now(),
        "session": dict(brief.get("session", {})) if isinstance(brief.get("session"), Mapping) else {},
        "changed_paths": list(brief.get("changed_paths", []))
        if isinstance(brief.get("changed_paths"), list) and brief.get("changed_paths")
        else [str(token).strip() for token in changed_paths if str(token).strip()],
        "explicit_paths": list(brief.get("explicit_paths", []))
        if isinstance(brief.get("explicit_paths"), list) and brief.get("explicit_paths")
        else [str(token).strip() for token in changed_paths if str(token).strip()],
        "repo_dirty_paths": list(brief.get("repo_dirty_paths", [])) if isinstance(brief.get("repo_dirty_paths"), list) else [],
        "scoped_working_tree_paths": list(brief.get("scoped_working_tree_paths", []))
        if isinstance(brief.get("scoped_working_tree_paths"), list)
        else [],
        "working_tree_scope": str(brief.get("working_tree_scope", "")).strip(),
        "working_tree_scope_degraded": bool(brief.get("working_tree_scope_degraded")),
        "inferred_workstream": _payload_workstream_hint(brief, include_selection=False),
        "selection_state": str(brief_selection.get("state", "")).strip()
        or str(brief_context_packet.get("selection_state", "")).strip(),
        "selection_reason": str(brief_selection.get("reason", "")).strip(),
        "selection_confidence": str(brief_selection.get("confidence", "")).strip(),
        "candidate_workstreams": [
            _compact_workstream_reference_for_packet(row)
            for row in brief.get("candidate_workstreams", [])
            if isinstance(row, Mapping)
        ]
        if isinstance(brief.get("candidate_workstreams"), list)
        else [],
        "workstream_selection": _compact_bootstrap_workstream_selection(brief.get("workstream_selection", {}))
        if isinstance(brief.get("workstream_selection"), Mapping)
        else {},
        "context_packet_state": str(brief.get("context_packet_state", "")).strip()
        or str(brief_context_packet.get("packet_state", "")).strip(),
        "truncation": dict(brief.get("truncation", {})) if isinstance(brief.get("truncation"), Mapping) else {},
        "full_scan_recommended": bool(brief.get("full_scan_recommended") or brief_context_packet.get("full_scan_recommended")),
        "full_scan_reason": str(brief.get("full_scan_reason", "")).strip()
        or str(brief_context_packet.get("full_scan_reason", "")).strip(),
        "fallback_scan": dict(brief.get("fallback_scan", {}))
        if isinstance(brief.get("fallback_scan"), Mapping)
        else {},
        "impact_summary": {
            "primary_workstream": _compact_workstream_row_for_packet(impact.get("primary_workstream", {}))
            if isinstance(impact.get("primary_workstream"), Mapping)
            else {},
            "components": [_compact_component_row_for_packet(row) for row in impact.get("components", []) if isinstance(row, Mapping)]
            if isinstance(impact.get("components"), list)
            else [],
            "workstreams": [
                _compact_workstream_reference_for_packet(row)
                for row in brief.get("candidate_workstreams", [])
                if isinstance(row, Mapping)
            ]
            if isinstance(brief.get("candidate_workstreams"), list)
            else [],
            "diagrams": [_compact_diagram_row_for_packet(row) for row in impact.get("diagrams", []) if isinstance(row, Mapping)]
            if isinstance(impact.get("diagrams"), list)
            else [],
            "guidance_brief": [dict(row) for row in impact.get("guidance_brief", []) if isinstance(row, Mapping)]
            if isinstance(impact.get("guidance_brief"), list)
            else [],
            "miss_recovery": _compact_miss_recovery_for_packet(impact.get("miss_recovery", {}))
            if isinstance(impact.get("miss_recovery"), Mapping)
            else {},
        },
        "relevant_docs": relevant_docs,
        "recommended_commands": recommended_commands,
        "recommended_tests": recommended_tests,
        "top_engineering_notes": _compact_engineering_notes(
            impact.get("engineering_notes", {}) if isinstance(impact.get("engineering_notes"), Mapping) else {},
            total_limit=3,
            per_kind_limit=1,
        )[0],
        "workstream_context": dict(brief.get("workstream_context", {})) if isinstance(brief.get("workstream_context"), Mapping) else {},
        "active_conflicts": [dict(row) for row in brief.get("active_conflicts", [])[:4] if isinstance(row, Mapping)]
        if isinstance(brief.get("active_conflicts"), list)
        else [],
        "active_session_count": int(brief.get("active_session_count", 0) or 0),
        "runtime": {
            "projection_fingerprint": str(runtime_state.get("projection_fingerprint", "")).strip(),
            "projection_scope": str(runtime_state.get("projection_scope", "")).strip(),
            "updated_utc": str(runtime_state.get("updated_utc", "")).strip(),
            "timings": _compact_runtime_timing_rows_for_packet(timing_summary)
            if isinstance(timing_summary, Mapping)
            else {},
        },
        "narrowing_required": bool(brief.get("narrowing_required") or brief_route.get("narrowing_required")),
        "route_ready": bool(brief.get("route_ready") or brief_route.get("route_ready")),
    }
    payload = session_bootstrap_payload_compactor.compact_bootstrap_payload(payload)
    stage_started = time.perf_counter()
    payload = tooling_context_packet_builder.finalize_packet(
        repo_root=root,
        packet_kind="bootstrap_session",
        payload=payload,
        packet_state=str(payload.get("context_packet_state", "")).strip(),
        changed_paths=payload.get("changed_paths", []) if isinstance(payload.get("changed_paths"), list) else [],
        explicit_paths=payload.get("explicit_paths", []) if isinstance(payload.get("explicit_paths"), list) else [],
        shared_only_input=_broad_shared_only_input(
            payload.get("changed_paths", []) if isinstance(payload.get("changed_paths"), list) else []
        ),
        selection_state=str(payload.get("selection_state", "")).strip(),
        workstream_selection=payload.get("workstream_selection", {})
        if isinstance(payload.get("workstream_selection"), Mapping)
        else {},
        candidate_workstreams=payload.get("candidate_workstreams", [])
        if isinstance(payload.get("candidate_workstreams"), list)
        else [],
        components=payload.get("impact_summary", {}).get("components", [])
        if isinstance(payload.get("impact_summary"), Mapping) and isinstance(payload.get("impact_summary", {}).get("components"), list)
        else [],
        diagrams=payload.get("impact_summary", {}).get("diagrams", [])
        if isinstance(payload.get("impact_summary"), Mapping) and isinstance(payload.get("impact_summary", {}).get("diagrams"), list)
        else [],
        docs=relevant_docs,
        recommended_commands=recommended_commands,
        recommended_tests=recommended_tests,
        engineering_notes=payload.get("top_engineering_notes", {})
        if isinstance(payload.get("top_engineering_notes"), Mapping)
        else {},
        miss_recovery=payload.get("impact_summary", {}).get("miss_recovery", {})
        if isinstance(payload.get("impact_summary"), Mapping)
        and isinstance(payload.get("impact_summary", {}).get("miss_recovery"), Mapping)
        else {},
        full_scan_recommended=bool(payload.get("full_scan_recommended")),
        full_scan_reason=str(payload.get("full_scan_reason", "")).strip(),
        session_id=str(dict(payload.get("session", {})).get("session_id", "")).strip()
        if isinstance(payload.get("session"), Mapping)
        else "",
        family_hint=str(family_hint or "").strip(),
        guidance_catalog=guidance_catalog,
        optimization_snapshot=optimization_snapshot,
        delivery_profile=delivery_profile,
    )
    stage_timings["finalize"] = _elapsed_stage_ms(stage_started)
    timing_payload = payload
    if hot_path:
        payload = _compact_hot_path_runtime_packet(
            packet_kind="bootstrap_session",
            payload=payload,
        )
    else:
        payload = session_bootstrap_payload_compactor.compact_finalized_bootstrap_payload(payload)
    if isinstance(timing_payload.get("session"), Mapping) and not hot_path:
        session_payload = dict(timing_payload.get("session", {}))
        target = _bootstrap_record_path(repo_root=root, session_id=str(session_payload.get("session_id", "")).strip())
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=target,
            payload=timing_payload,
            lock_key=str(target),
        )
        prune_runtime_records(repo_root=root)
    if not hot_path:
        packet_summary = _packet_summary_from_bootstrap_payload(timing_payload)
        benchmark_summary = _packet_benchmark_summary_for_runtime_packet(
            repo_root=root,
            packet=packet_summary,
        )
        control_advisories = dict(load_runtime_optimization_snapshot(repo_root=root).get("control_advisories", {}))
        odylith_evaluation_ledger.append_event(
            repo_root=root,
            event_type="packet",
            event_id=(
                f"{str(packet_summary.get('session_id', '')).strip()}::"
                f"{str(packet_summary.get('bootstrapped_at', '')).strip()}"
            ),
            payload=odylith_evaluation_ledger.packet_event_payload(
                packet_summary=packet_summary,
                benchmark_summary=benchmark_summary,
                control_advisories=control_advisories,
            ),
            recorded_at=str(packet_summary.get("bootstrapped_at", "")).strip(),
        )
    record_runtime_timing(
        repo_root=root,
        category="reasoning",
        operation="bootstrap_session",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "changed_path_count": len(payload.get("changed_paths", [])) if isinstance(payload.get("changed_paths"), list) else 0,
            "doc_count": len(relevant_docs),
            "command_count": len(recommended_commands),
            "test_count": len(recommended_tests),
            "packet_state": str(payload.get("context_packet_state", "")).strip(),
            "estimated_bytes": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_bytes", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "estimated_tokens": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_tokens", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "stage_timings": _compact_stage_timings(stage_timings),
            "family_hint": _normalize_family_hint(family_hint),
        },
    )
    return payload


def build_adaptive_coding_packet(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    intent: str = "",
    family_hint: str = "",
    workstream_hint: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    family = _normalize_family_hint(family_hint)
    attempts: list[dict[str, Any]] = []
    initial_source = "impact"
    retain_impact_internal_context = bool(
        family in _HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES
        or (
            str(workstream_hint or "").strip()
            and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
        )
    )
    impact_payload = build_impact_report(
        repo_root=root,
        changed_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
        runtime_mode=runtime_mode,
        intent=intent,
        delivery_profile=_CODEX_HOT_PATH_PROFILE,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        validation_command_hints=validation_command_hints,
        retain_hot_path_internal_context=retain_impact_internal_context,
    )
    initial_trigger = _hot_path_auto_escalation_trigger(
        packet_kind="impact",
        family_hint=family_hint,
        payload=impact_payload,
    )
    attempts.append(
        {
            "stage": 1,
            "label": "compact_packet",
            "trigger": initial_trigger,
            "accepted": True,
            "route_ready": _hot_path_route_ready(impact_payload),
            "full_scan_recommended": _hot_path_full_scan_recommended(impact_payload),
            "routing_confidence": _hot_path_routing_confidence(impact_payload),
        }
    )
    should_escalate, reasons = _should_escalate_hot_path_to_session_brief(
        payload=impact_payload,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        validation_command_hints=validation_command_hints,
    )
    explicit_workstream_unresolved = bool(
        family == "explicit_workstream"
        and str(workstream_hint or "").strip()
        and str(_hot_path_workstream_selection(impact_payload).get("state", "")).strip() != "explicit"
    )
    if should_escalate and not explicit_workstream_unresolved:
        session_brief_payload = build_session_brief(
            repo_root=root,
            changed_paths=changed_paths,
            use_working_tree=use_working_tree,
            working_tree_scope="session" if str(working_tree_scope or "").strip() == "repo" else working_tree_scope,
            session_id=session_id,
            workstream=workstream_hint,
            intent=intent,
            claimed_paths=claimed_paths,
            runtime_mode=runtime_mode,
            delivery_profile=_CODEX_HOT_PATH_PROFILE,
            family_hint=family_hint,
            validation_command_hints=validation_command_hints,
            impact_override=impact_payload,
        )
        session_brief_accepted = _hot_path_packet_rank(session_brief_payload) >= _hot_path_packet_rank(impact_payload)
        attempts.append(
            {
                "stage": 2,
                "label": "expanded_context",
                "trigger": reasons[0] if reasons else initial_trigger,
                "accepted": session_brief_accepted,
                "route_ready": _hot_path_route_ready(session_brief_payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(session_brief_payload),
                "routing_confidence": _hot_path_routing_confidence(session_brief_payload),
            }
        )
        payload = session_brief_payload if session_brief_accepted else impact_payload
        final_source = "session_brief" if session_brief_accepted else initial_source
        stage = "session_brief_rescue" if session_brief_accepted else "compact_success"
    else:
        if explicit_workstream_unresolved:
            reasons = _dedupe_strings([*reasons, "explicit_workstream_unresolved"])
        payload = impact_payload
        final_source = initial_source
        stage = "compact_success"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    architecture_rescue_applied = False
    if (
        current_trigger
        and family in _HOT_PATH_AUTO_ESCALATION_ARCHITECTURE_FAMILIES
        and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
    ):
        architecture_payload = build_architecture_audit(
            repo_root=root,
            changed_paths=changed_paths,
            use_working_tree=use_working_tree,
            working_tree_scope="session" if str(working_tree_scope or "").strip() == "repo" else working_tree_scope,
            session_id=session_id,
            claimed_paths=claimed_paths,
            runtime_mode=runtime_mode,
            detail_level="packet",
        )
        attempts.append(
            {
                "stage": 3,
                "label": "architecture_assist",
                "trigger": current_trigger,
                "accepted": bool(architecture_payload.get("resolved")),
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(payload),
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        if bool(architecture_payload.get("resolved")):
            architecture_rescue_applied = True
            stage = "architecture_assist"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    if current_trigger and (
        not _hot_path_can_hold_local_narrowing_without_full_scan(
            family_hint=family_hint,
            payload=payload,
        )
        and (
        _hot_path_full_scan_recommended(payload)
        or (
            family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
            and not _hot_path_route_ready(payload)
            and not architecture_rescue_applied
        )
        )
    ):
        fallback_reason = _hot_path_full_scan_reason(payload) or "adaptive_full_scan_fallback"
        fallback_scan = _fallback_scan_payload(
            repo_root=root,
            reason=fallback_reason,
            query=str(intent or "").strip(),
            changed_paths=changed_paths,
            perform_scan=family not in _HOT_PATH_SUMMARY_ONLY_FALLBACK_FAMILIES,
            result_limit=8,
            delivery_profile=_CODEX_HOT_PATH_PROFILE,
        )
        attempts.append(
            {
                "stage": 4,
                "label": "full_scan_fallback",
                "trigger": current_trigger,
                "accepted": True,
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": True,
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=payload,
            full_scan_recommended=True,
            full_scan_reason=fallback_reason,
            fallback_scan=fallback_scan,
        )
        stage = "full_scan_fallback"
    adaptive_escalation = {
        "stage": stage,
        "initial_source": initial_source,
        "final_source": final_source,
        "auto_escalated": bool(should_escalate or architecture_rescue_applied or stage == "full_scan_fallback"),
        "reasons": _dedupe_strings([*reasons, initial_trigger, current_trigger]),
        "attempts": attempts,
    }
    if retain_impact_internal_context and final_source == "impact":
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind="impact",
            payload=payload,
            retain_internal_context=False,
        )
    elif not _hot_path_payload_is_compact(payload):
        payload = _compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=dict(payload),
        )
    selector_diagnostics = (
        dict(payload.pop("benchmark_selector_diagnostics", {}))
        if isinstance(payload.get("benchmark_selector_diagnostics"), Mapping)
        else {}
    )
    if selector_diagnostics:
        adaptive_escalation["benchmark_selector_diagnostics"] = selector_diagnostics
    return {
        "packet_source": final_source,
        "payload": payload,
        "adaptive_escalation": adaptive_escalation,
    }


def build_adaptive_coding_packet_reusing_daemon(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    intent: str = "",
    family_hint: str = "",
    workstream_hint: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    family = _normalize_family_hint(family_hint)
    attempts: list[dict[str, Any]] = []
    initial_source = "impact"
    retain_impact_internal_context = bool(
        family in _HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES
        or (
            str(workstream_hint or "").strip()
            and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
        )
    )
    impact_request = {
        "paths": [str(path).strip() for path in changed_paths if str(path).strip()],
        "use_working_tree": bool(use_working_tree),
        "working_tree_scope": str(working_tree_scope or "repo").strip() or "repo",
        "session_id": str(session_id or "").strip(),
        "claim_paths": [str(token).strip() for token in claimed_paths if str(token).strip()],
        "runtime_mode": str(runtime_mode or "auto").strip() or "auto",
        "intent": str(intent or "").strip(),
        "delivery_profile": _CODEX_HOT_PATH_PROFILE,
        "family_hint": str(family_hint or "").strip(),
        "workstream_hint": str(workstream_hint or "").strip(),
        "validation_command_hints": [str(token).strip() for token in validation_command_hints if str(token).strip()],
        "retain_hot_path_internal_context": retain_impact_internal_context,
    }
    impact_result = request_runtime_daemon(
        repo_root=root,
        command="impact",
        payload=impact_request,
    )
    if impact_result is None:
        adaptive = build_adaptive_coding_packet(
            repo_root=root,
            changed_paths=changed_paths,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            claimed_paths=claimed_paths,
            runtime_mode=runtime_mode,
            intent=intent,
            family_hint=family_hint,
            workstream_hint=workstream_hint,
            validation_command_hints=validation_command_hints,
        )
        adaptive["runtime_execution"] = _local_runtime_execution_summary(
            repo_root=root,
            command="impact",
            changed_paths=changed_paths,
            session_id=session_id,
            claimed_paths=claimed_paths,
            working_tree_scope=working_tree_scope,
        )
        return adaptive
    impact_payload, runtime_execution = impact_result
    any_daemon_reuse = bool(runtime_execution.get("workspace_daemon_reused"))
    initial_trigger = _hot_path_auto_escalation_trigger(
        packet_kind="impact",
        family_hint=family_hint,
        payload=impact_payload,
    )
    attempts.append(
        {
            "stage": 1,
            "label": "compact_packet",
            "trigger": initial_trigger,
            "accepted": True,
            "route_ready": _hot_path_route_ready(impact_payload),
            "full_scan_recommended": _hot_path_full_scan_recommended(impact_payload),
            "routing_confidence": _hot_path_routing_confidence(impact_payload),
        }
    )
    should_escalate, reasons = _should_escalate_hot_path_to_session_brief(
        payload=impact_payload,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        validation_command_hints=validation_command_hints,
    )
    explicit_workstream_unresolved = bool(
        family == "explicit_workstream"
        and str(workstream_hint or "").strip()
        and str(_hot_path_workstream_selection(impact_payload).get("state", "")).strip() != "explicit"
    )
    if should_escalate and not explicit_workstream_unresolved:
        session_scope = "session" if str(working_tree_scope or "").strip() == "repo" else str(working_tree_scope or "").strip()
        session_request = {
            "paths": [str(path).strip() for path in changed_paths if str(path).strip()],
            "use_working_tree": bool(use_working_tree),
            "working_tree_scope": session_scope or "session",
            "session_id": str(session_id or "").strip(),
            "workstream": str(workstream_hint or "").strip(),
            "intent": str(intent or "").strip(),
            "claim_paths": [str(token).strip() for token in claimed_paths if str(token).strip()],
            "runtime_mode": str(runtime_mode or "auto").strip() or "auto",
            "delivery_profile": _CODEX_HOT_PATH_PROFILE,
            "family_hint": str(family_hint or "").strip(),
            "validation_command_hints": [str(token).strip() for token in validation_command_hints if str(token).strip()],
        }
        session_result = request_runtime_daemon(
            repo_root=root,
            command="session-brief",
            payload=session_request,
        )
        if session_result is not None:
            session_brief_payload, session_runtime_execution = session_result
        else:
            session_brief_payload = build_session_brief(
                repo_root=root,
                changed_paths=changed_paths,
                use_working_tree=use_working_tree,
                working_tree_scope=session_scope or "session",
                session_id=session_id,
                workstream=workstream_hint,
                intent=intent,
                claimed_paths=claimed_paths,
                runtime_mode=runtime_mode,
                delivery_profile=_CODEX_HOT_PATH_PROFILE,
                family_hint=family_hint,
                validation_command_hints=validation_command_hints,
                impact_override=impact_payload,
            )
            session_runtime_execution = _local_runtime_execution_summary(
                repo_root=root,
                command="session-brief",
                changed_paths=changed_paths,
                session_id=session_id,
                claimed_paths=claimed_paths,
                working_tree_scope=session_scope or "session",
            )
        session_brief_accepted = _hot_path_packet_rank(session_brief_payload) >= _hot_path_packet_rank(impact_payload)
        attempts.append(
            {
                "stage": 2,
                "label": "expanded_context",
                "trigger": reasons[0] if reasons else initial_trigger,
                "accepted": session_brief_accepted,
                "route_ready": _hot_path_route_ready(session_brief_payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(session_brief_payload),
                "routing_confidence": _hot_path_routing_confidence(session_brief_payload),
            }
        )
        payload = session_brief_payload if session_brief_accepted else impact_payload
        final_source = "session_brief" if session_brief_accepted else initial_source
        stage = "session_brief_rescue" if session_brief_accepted else "compact_success"
        if bool(session_runtime_execution.get("workspace_daemon_reused")):
            any_daemon_reuse = True
        if session_brief_accepted:
            runtime_execution = session_runtime_execution
    else:
        if explicit_workstream_unresolved:
            reasons = _dedupe_strings([*reasons, "explicit_workstream_unresolved"])
        payload = impact_payload
        final_source = initial_source
        stage = "compact_success"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    architecture_rescue_applied = False
    if (
        current_trigger
        and family in _HOT_PATH_AUTO_ESCALATION_ARCHITECTURE_FAMILIES
        and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
    ):
        architecture_scope = "session" if str(working_tree_scope or "").strip() == "repo" else str(working_tree_scope or "").strip()
        architecture_request = {
            "paths": [str(path).strip() for path in changed_paths if str(path).strip()],
            "use_working_tree": bool(use_working_tree),
            "working_tree_scope": architecture_scope or "session",
            "session_id": str(session_id or "").strip(),
            "claim_paths": [str(token).strip() for token in claimed_paths if str(token).strip()],
            "runtime_mode": str(runtime_mode or "auto").strip() or "auto",
            "detail_level": "packet",
        }
        architecture_result = request_runtime_daemon(
            repo_root=root,
            command="architecture",
            payload=architecture_request,
        )
        if architecture_result is not None:
            architecture_payload, architecture_runtime_execution = architecture_result
        else:
            architecture_payload = build_architecture_audit(
                repo_root=root,
                changed_paths=changed_paths,
                use_working_tree=use_working_tree,
                working_tree_scope=architecture_scope or "session",
                session_id=session_id,
                claimed_paths=claimed_paths,
                runtime_mode=runtime_mode,
                detail_level="packet",
            )
            architecture_runtime_execution = _local_runtime_execution_summary(
                repo_root=root,
                command="architecture",
                changed_paths=changed_paths,
                session_id=session_id,
                claimed_paths=claimed_paths,
                working_tree_scope=architecture_scope or "session",
            )
        attempts.append(
            {
                "stage": 3,
                "label": "architecture_assist",
                "trigger": current_trigger,
                "accepted": bool(architecture_payload.get("resolved")),
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(payload),
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        if bool(architecture_runtime_execution.get("workspace_daemon_reused")):
            any_daemon_reuse = True
        if bool(architecture_payload.get("resolved")):
            architecture_rescue_applied = True
            stage = "architecture_assist"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    if current_trigger and (
        not _hot_path_can_hold_local_narrowing_without_full_scan(
            family_hint=family_hint,
            payload=payload,
        )
        and (
        _hot_path_full_scan_recommended(payload)
        or (
            family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
            and not _hot_path_route_ready(payload)
            and not architecture_rescue_applied
        )
        )
    ):
        fallback_reason = _hot_path_full_scan_reason(payload) or "adaptive_full_scan_fallback"
        fallback_scan = _fallback_scan_payload(
            repo_root=root,
            reason=fallback_reason,
            query=str(intent or "").strip(),
            changed_paths=changed_paths,
            perform_scan=family not in _HOT_PATH_SUMMARY_ONLY_FALLBACK_FAMILIES,
            result_limit=8,
            delivery_profile=_CODEX_HOT_PATH_PROFILE,
        )
        attempts.append(
            {
                "stage": 4,
                "label": "full_scan_fallback",
                "trigger": current_trigger,
                "accepted": True,
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": True,
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=payload,
            full_scan_recommended=True,
            full_scan_reason=fallback_reason,
            fallback_scan=fallback_scan,
        )
        stage = "full_scan_fallback"
    adaptive_escalation = {
        "stage": stage,
        "initial_source": initial_source,
        "final_source": final_source,
        "auto_escalated": bool(should_escalate or architecture_rescue_applied or stage == "full_scan_fallback"),
        "reasons": _dedupe_strings([*reasons, initial_trigger, current_trigger]),
        "attempts": attempts,
    }
    if retain_impact_internal_context and final_source == "impact":
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind="impact",
            payload=payload,
            retain_internal_context=False,
        )
    elif not _hot_path_payload_is_compact(payload):
        payload = _compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=dict(payload),
        )
    runtime_execution = dict(runtime_execution)
    runtime_execution["workspace_daemon_reused"] = bool(any_daemon_reuse)
    runtime_execution["mixed_local_fallback"] = bool(
        any_daemon_reuse and str(runtime_execution.get("source", "")).strip() != "workspace_daemon"
    )
    return {
        "packet_source": final_source,
        "payload": payload,
        "adaptive_escalation": adaptive_escalation,
        "runtime_execution": runtime_execution,
    }
