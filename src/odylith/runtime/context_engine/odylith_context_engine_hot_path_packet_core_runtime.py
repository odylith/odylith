"""Odylith Context Engine Hot Path Packet Core Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

def _store():
    from odylith.runtime.context_engine import odylith_context_engine_store as store

    return store


from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bootstrap_runtime
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.context_engine import path_bundle_codec
from odylith.runtime.governance import proof_state as proof_state_runtime

def _compact_hot_path_active_conflicts(conflicts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in conflicts[:4]:
        if not isinstance(row, _store().Mapping):
            continue
        compact.append(
            {
                key: value
                for key, value in {
                    "session_id": str(row.get("session_id", "")).strip(),
                    "workstream": str(row.get("workstream", "")).strip(),
                    "claim_mode": str(row.get("claim_mode", "")).strip(),
                    "severity": str(row.get("severity", "")).strip(),
                    "same_workstream": bool(row.get("same_workstream")),
                    "repo_context_mismatch": bool(row.get("repo_context_mismatch")),
                    "shared_paths": _store()._normalized_string_list(row.get("shared_paths"))[:3],
                    "shared_surfaces": _store()._normalized_string_list(row.get("shared_surfaces"))[:3],
                }.items()
                if value not in ("", [], {}, None, False)
            }
        )
    return compact

def _hot_path_keep_architecture_audit(audit: Mapping[str, Any]) -> bool:
    if not isinstance(audit, _store().Mapping) or not audit:
        return False
    if bool(audit.get("resolved")) or bool(audit.get("full_scan_recommended")):
        return True
    if int(audit.get("required_read_count", 0) or 0) > 0:
        return True
    if int(audit.get("diagram_watch_gap_count", 0) or 0) > 0:
        return True
    if int(audit.get("linked_component_count", 0) or 0) > 0:
        return True
    if int(audit.get("linked_diagram_count", 0) or 0) > 0:
        return True
    if int(audit.get("contract_touchpoint_count", 0) or 0) > 0:
        return True
    coverage = dict(audit.get("coverage", {})) if isinstance(audit.get("coverage"), _store().Mapping) else {}
    return int(coverage.get("score", 0) or 0) > 0

def _hot_path_workstream_selection(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, _store().Mapping):
        return {}
    selection = dict(payload.get("workstream_selection", {})) if isinstance(payload.get("workstream_selection"), _store().Mapping) else {}
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), _store().Mapping)
        else {}
    )
    compact_state, compact_workstream = _store()._compact_selection_state_parts(
        str(payload.get("selection_state", "")).strip()
        or str(context_packet.get("selection_state", "")).strip()
    )
    state = compact_state or str(selection.get("state", "")).strip()
    inferred_workstream = _store()._payload_workstream_hint(payload, include_selection=False)
    if not state and inferred_workstream:
        state = "inferred_confident"
    if not state:
        return {}
    selected_workstream = (
        dict(selection.get("selected_workstream", {}))
        if isinstance(selection.get("selected_workstream"), _store().Mapping)
        else {}
    )
    top_candidate = (
        dict(selection.get("top_candidate", {}))
        if isinstance(selection.get("top_candidate"), _store().Mapping)
        else {}
    )
    if inferred_workstream and state in {"explicit", "inferred_confident"}:
        selected_workstream = {
            **({"entity_id": inferred_workstream} if inferred_workstream else {}),
            **selected_workstream,
        }
        top_candidate = top_candidate or dict(selected_workstream)
    elif compact_workstream and state in {"explicit", "inferred_confident"}:
        selected_workstream = {
            **({"entity_id": compact_workstream} if compact_workstream else {}),
            **selected_workstream,
        }
        top_candidate = top_candidate or dict(selected_workstream)
    confidence = (
        str(payload.get("selection_confidence", "")).strip()
        or str(selection.get("confidence", "")).strip()
        or ("high" if state in {"explicit", "inferred_confident"} and selected_workstream else "low")
    )
    reason = (
        str(payload.get("selection_reason", "")).strip()
        or str(selection.get("reason", "")).strip()
        or ("Reusing hot-path impact selection." if selected_workstream or top_candidate else "")
    )
    candidate_count = int(selection.get("candidate_count", 0) or 0)
    strong_candidate_count = int(selection.get("strong_candidate_count", 0) or 0)
    if candidate_count <= 0 and (selected_workstream or top_candidate):
        candidate_count = 1
    if strong_candidate_count <= 0 and state in {"explicit", "inferred_confident"} and selected_workstream:
        strong_candidate_count = 1
    ambiguity_class = str(selection.get("ambiguity_class", "")).strip()
    if not ambiguity_class:
        ambiguity_class = (
            "resolved"
            if state in {"explicit", "inferred_confident"}
            else "selection_ambiguous"
            if state == "ambiguous"
            else "none"
        )
    return {
        "state": state,
        "reason": reason,
        "why_selected": str(selection.get("why_selected", "")).strip() or reason,
        "selected_workstream": selected_workstream,
        "top_candidate": top_candidate or dict(selected_workstream),
        "score_gap": selection.get("score_gap"),
        "confidence": confidence,
        "candidate_count": candidate_count,
        "strong_candidate_count": strong_candidate_count,
        "ambiguity_class": ambiguity_class,
        "competing_candidates": [
            dict(row)
            for row in selection.get("competing_candidates", [])
            if isinstance(selection.get("competing_candidates"), list) and isinstance(row, _store().Mapping)
        ][:3],
    }

def _compact_hot_path_workstream_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "state": str(selection.get("state", "")).strip(),
            "reason": str(selection.get("reason", "")).strip(),
            "confidence": str(selection.get("confidence", "")).strip(),
            "ambiguity_class": str(selection.get("ambiguity_class", "")).strip(),
            "candidate_count": int(selection.get("candidate_count", 0) or 0),
            "strong_candidate_count": int(selection.get("strong_candidate_count", 0) or 0),
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    selected = dict(selection.get("selected_workstream", {})) if isinstance(selection.get("selected_workstream"), _store().Mapping) else {}
    top_candidate = dict(selection.get("top_candidate", {})) if isinstance(selection.get("top_candidate"), _store().Mapping) else {}
    for field_name, row in (("selected_workstream", selected), ("top_candidate", top_candidate)):
        entity_id = str(row.get("entity_id", "")).strip()
        if entity_id:
            compact[field_name] = {
                key: value
                for key, value in {
                    "entity_id": entity_id,
                    "title": str(row.get("title", "")).strip(),
                }.items()
                if value not in ("", [], {}, None)
            }
    return compact

def _compact_hot_path_retrieval_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "packet_kind": str(plan.get("packet_kind", "")).strip(),
            "packet_state": str(plan.get("packet_state", "")).strip(),
            "anchor_quality": str(plan.get("anchor_quality", "")).strip(),
            "guidance_coverage": str(plan.get("guidance_coverage", "")).strip(),
            "evidence_consensus": str(plan.get("evidence_consensus", "")).strip(),
            "precision_score": int(plan.get("precision_score", 0) or 0),
            "ambiguity_class": str(plan.get("ambiguity_class", "")).strip(),
            "routing_confidence": str(plan.get("routing_confidence", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    selected_domains = _store()._normalized_string_list(plan.get("selected_domains"))
    if selected_domains:
        compact["selected_domains"] = selected_domains[:4]
    miss_recovery = dict(plan.get("miss_recovery", {})) if isinstance(plan.get("miss_recovery"), _store().Mapping) else {}
    if miss_recovery:
        compact["miss_recovery"] = {
            key: value
            for key, value in {
                "active": bool(miss_recovery.get("active")),
                "applied": bool(miss_recovery.get("applied")),
                "mode": str(miss_recovery.get("mode", "")).strip(),
            }.items()
            if value not in ("", [], {}, None, False)
        }
    return compact

def _compact_hot_path_packet_quality(summary: Mapping[str, Any]) -> dict[str, Any]:
    utility_profile = dict(summary.get("utility_profile", {})) if isinstance(summary.get("utility_profile"), _store().Mapping) else {}
    token_efficiency = dict(utility_profile.get("token_efficiency", {})) if isinstance(utility_profile.get("token_efficiency"), _store().Mapping) else {}
    intent_profile = dict(summary.get("intent_profile", {})) if isinstance(summary.get("intent_profile"), _store().Mapping) else {}
    context_density = dict(summary.get("context_density", {})) if isinstance(summary.get("context_density"), _store().Mapping) else {}
    reasoning_readiness = (
        dict(summary.get("reasoning_readiness", {})) if isinstance(summary.get("reasoning_readiness"), _store().Mapping) else {}
    )
    evidence_quality = dict(summary.get("evidence_quality", {})) if isinstance(summary.get("evidence_quality"), _store().Mapping) else {}
    actionability = dict(summary.get("actionability", {})) if isinstance(summary.get("actionability"), _store().Mapping) else {}
    validation_pressure = (
        dict(summary.get("validation_pressure", {})) if isinstance(summary.get("validation_pressure"), _store().Mapping) else {}
    )
    evidence_diversity = (
        dict(summary.get("evidence_diversity", {})) if isinstance(summary.get("evidence_diversity"), _store().Mapping) else {}
    )
    compact = {
        key: value
        for key, value in {
            "context_richness": str(summary.get("context_richness", "")).strip(),
            "accuracy_posture": str(summary.get("accuracy_posture", "")).strip(),
            "routing_confidence": str(summary.get("routing_confidence", "")).strip(),
            "ambiguity_class": str(summary.get("ambiguity_class", "")).strip(),
            "reasoning_bias": str(summary.get("reasoning_bias", "")).strip(),
            "parallelism_hint": str(summary.get("parallelism_hint", "")).strip(),
            "native_spawn_ready": bool(summary.get("native_spawn_ready")),
            "within_budget": bool(summary.get("within_budget")),
            "utility_profile": {
                key: value
                for key, value in {
                    "score": int(utility_profile.get("score", 0) or 0),
                    "level": str(utility_profile.get("level", "")).strip(),
                    "token_efficiency": {
                        "score": int(token_efficiency.get("score", 0) or 0),
                        "level": str(token_efficiency.get("level", "")).strip(),
                    }
                    if token_efficiency
                    else {},
                }.items()
                if value not in ("", [], {}, None, 0)
            }
            if utility_profile
            else {},
            "intent_profile": {
                key: value
                for key, value in {
                    "family": str(intent_profile.get("family", "")).strip(),
                    "mode": str(intent_profile.get("mode", "")).strip(),
                    "critical_path": str(intent_profile.get("critical_path", "")).strip(),
                    "confidence": str(intent_profile.get("confidence", "")).strip(),
                    "explicit": bool(intent_profile.get("explicit")),
                }.items()
                if value not in ("", [], {}, None, False)
            }
            if intent_profile
            else {},
            "context_density": {
                key: value
                for key, value in {
                    "score": int(context_density.get("score", 0) or 0),
                    "level": str(context_density.get("level", "")).strip(),
                }.items()
                if value not in ("", [], {}, None, 0)
            }
            if context_density
            else {},
            "reasoning_readiness": {
                key: value
                for key, value in {
                    "score": int(reasoning_readiness.get("score", 0) or 0),
                    "level": str(reasoning_readiness.get("level", "")).strip(),
                    "mode": str(reasoning_readiness.get("mode", "")).strip(),
                    "deep_reasoning_ready": bool(reasoning_readiness.get("deep_reasoning_ready")),
                }.items()
                if value not in ("", [], {}, None, False, 0)
            }
            if reasoning_readiness
            else {},
            "evidence_quality": evidence_quality,
            "actionability": actionability,
            "validation_pressure": validation_pressure,
            "evidence_diversity": {
                key: value
                for key, value in {
                    "score": int(evidence_diversity.get("score", 0) or 0),
                    "level": str(evidence_diversity.get("level", "")).strip(),
                    "domain_count": int(evidence_diversity.get("domain_count", 0) or 0),
                }.items()
                if value not in ("", [], {}, None, 0)
            }
            if evidence_diversity
            else {},
        }.items()
        if value not in ("", [], {}, None, False)
    }
    return compact

def _compact_hot_path_intent(summary: Mapping[str, Any]) -> dict[str, Any]:
    intent = dict(summary.get("intent", {})) if isinstance(summary.get("intent"), _store().Mapping) else {}
    packet_quality = dict(summary.get("packet_quality", {})) if isinstance(summary.get("packet_quality"), _store().Mapping) else {}
    intent_profile = dict(packet_quality.get("intent_profile", {})) if isinstance(packet_quality.get("intent_profile"), _store().Mapping) else {}
    compact = {
        key: value
        for key, value in {
            "family": str(intent.get("family", "")).strip() or str(intent_profile.get("family", "")).strip(),
            "mode": str(intent.get("mode", "")).strip() or str(intent_profile.get("mode", "")).strip(),
            "critical_path": str(intent.get("critical_path", "")).strip() or str(intent_profile.get("critical_path", "")).strip(),
            "confidence": str(intent.get("confidence", "")).strip() or str(intent_profile.get("confidence", "")).strip(),
            "explicit": bool(intent.get("explicit") or intent_profile.get("explicit")),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    return compact

def _hot_path_signal_score(value: Any) -> int:
    if isinstance(value, _store().Mapping):
        try:
            raw_score = int(value.get("score", 0) or 0)
        except (TypeError, ValueError):
            raw_score = 0
        if raw_score > 0:
            return max(0, min(4, raw_score))
        token = str(value.get("level", "")).strip().lower()
    else:
        token = str(value or "").strip().lower()
    if token in {"high", "strong", "grounded", "actionable", "deep_validation"}:
        return 4
    if token in {"medium", "moderate", "balanced", "accuracy_first", "bounded_parallel_candidate"}:
        return 3
    if token in {"low", "guarded", "guarded_narrowing", "serial_preferred"}:
        return 2
    if token in {"minimal", "serial_guarded"}:
        return 1
    return 0

def _hot_path_synthesized_execution_profile(
    *,
    packet_kind: str,
    route_ready: bool,
    within_budget: bool,
    full_scan_recommended: bool,
    narrowing_required: bool,
    routing_confidence: str,
    intent_family: str,
    validation_count: int,
    guidance_count: int,
    closeout_doc_count: int,
    strict_gate_command_count: int,
    plan_binding_required: bool,
    governed_surface_sync_required: bool,
    host_runtime: str = "",
) -> dict[str, Any]:
    if not route_ready or not within_budget or full_scan_recommended or narrowing_required:
        return {}
    family = str(intent_family or "").strip().lower()
    confidence = str(routing_confidence or "").strip().lower()
    governance_contract = bool(
        closeout_doc_count > 0
        or strict_gate_command_count > 0
        or plan_binding_required
        or governed_surface_sync_required
    )
    supportive_contract = bool(governance_contract or validation_count > 0 or guidance_count > 0)
    profile = agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
    agent_role = "explorer"
    selection_mode = "analysis_scout"
    if family in {"implementation", "write", "bugfix", "ui_layout", "surface_copy", "surface_binding"}:
        if governance_contract and strict_gate_command_count > 0:
            profile = agent_runtime_contract.FRONTIER_HIGH_PROFILE
            selection_mode = "deep_validation"
        else:
            profile = (
                agent_runtime_contract.WRITE_HIGH_PROFILE
                if confidence == "high" and (validation_count > 0 or guidance_count >= 2)
                else agent_runtime_contract.WRITE_MEDIUM_PROFILE
            )
            selection_mode = "bounded_write"
        agent_role = "worker"
    elif family == "validation":
        profile = (
            agent_runtime_contract.WRITE_HIGH_PROFILE
            if confidence == "high" or validation_count >= 2 or strict_gate_command_count > 0
            else agent_runtime_contract.WRITE_MEDIUM_PROFILE
        )
        agent_role = "worker"
        selection_mode = "validation_focused"
    elif family in {"docs", "governance"}:
        profile = (
            agent_runtime_contract.FAST_WORKER_PROFILE
            if governance_contract
            else agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
        )
        agent_role = "worker" if profile == agent_runtime_contract.FAST_WORKER_PROFILE else "explorer"
        selection_mode = "support_fast_lane" if profile == agent_runtime_contract.FAST_WORKER_PROFILE else "analysis_scout"
    elif family in {"analysis", "review", "diagnosis"}:
        profile = (
            agent_runtime_contract.ANALYSIS_HIGH_PROFILE
            if confidence == "high" or supportive_contract
            else agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
        )
        agent_role = "explorer"
        selection_mode = "analysis_synthesis" if profile == agent_runtime_contract.ANALYSIS_HIGH_PROFILE else "analysis_scout"
    model, reasoning_effort = agent_runtime_contract.execution_profile_runtime_fields(
        profile,
        host_runtime=host_runtime,
    )
    confidence_score = 4 if confidence == "high" else 3 if confidence == "medium" else 2
    payload = {
        "profile": profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "agent_role": agent_role,
        "selection_mode": selection_mode,
        "delegate_preference": "delegate",
        "source": "odylith_runtime_packet",
        "confidence": {
            "score": confidence_score,
            "level": "high" if confidence_score >= 4 else "medium" if confidence_score >= 3 else "low",
        },
    }
    if host_runtime:
        payload["host_runtime"] = host_runtime
    return payload

def _hot_path_recomputed_readiness(
    *,
    packet_kind: str,
    packet_state: str,
    compact_payload: Mapping[str, Any],
    within_budget: bool,
) -> dict[str, Any]:
    routing_handoff = dict(compact_payload.get("routing_handoff", {})) if isinstance(compact_payload.get("routing_handoff"), _store().Mapping) else {}
    context_packet = dict(compact_payload.get("context_packet", {})) if isinstance(compact_payload.get("context_packet"), _store().Mapping) else {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), _store().Mapping) else {}
    current_route_ready = bool(
        compact_payload.get("route_ready")
        or routing_handoff.get("route_ready")
        or route.get("route_ready")
    )
    current_native_spawn_ready = bool(
        compact_payload.get("native_spawn_ready")
        or routing_handoff.get("native_spawn_ready")
        or route.get("native_spawn_ready")
    )
    retrieval_plan = dict(context_packet.get("retrieval_plan", {})) if isinstance(context_packet.get("retrieval_plan"), _store().Mapping) else {}
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {})) if isinstance(context_packet.get("packet_quality"), _store().Mapping) else {}
    )
    execution_profile = (
        dict(context_packet.get("execution_profile", {}))
        if isinstance(context_packet.get("execution_profile"), _store().Mapping)
        else {}
    )
    execution_signals = (
        dict(execution_profile.get("signals", {}))
        if isinstance(execution_profile.get("signals"), _store().Mapping)
        else {}
    )
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), _store().Mapping) else {}
    if not context_packet or not retrieval_plan or not anchors:
        return {
            "route_ready": current_route_ready,
            "native_spawn_ready": current_native_spawn_ready,
            "execution_profile": execution_profile,
        }
    selected_counts = _store()._decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
    validation_count = max(
        0,
        int(selected_counts.get("tests", 0) or 0),
    ) + max(
        0,
        int(selected_counts.get("commands", 0) or 0),
    )
    validation_bundle = odylith_context_engine_hot_path_packet_bootstrap_runtime._hot_path_validation_bundle(
        compact_payload,
        context_packet=context_packet,
    )
    governance_obligations = odylith_context_engine_hot_path_packet_bootstrap_runtime._hot_path_governance_obligations(
        compact_payload,
        context_packet=context_packet,
    )
    actionability_score = max(
        _hot_path_signal_score(execution_signals.get("actionability")),
        3 if max(0, int(selected_counts.get("guidance", 0) or 0)) >= 2 and validation_count > 0 else 2 if validation_count > 0 else 0,
    )
    validation_score = max(
        _hot_path_signal_score(execution_signals.get("validation_pressure")),
        3 if int(selected_counts.get("tests", 0) or 0) > 0 and int(selected_counts.get("commands", 0) or 0) > 0 else 2 if validation_count > 0 else 0,
    )
    route_ready = _store().routing.grounded_write_execution_ready(
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=bool(compact_payload.get("full_scan_recommended")),
        narrowing_required=bool(route.get("narrowing_required")),
        within_budget=within_budget,
        routing_confidence=str(packet_quality.get("routing_confidence", "")).strip() or str(compact_payload.get("routing_confidence", "")).strip(),
        has_non_shared_anchor=bool(anchors.get("has_non_shared_anchor")),
        ambiguity_class=str(retrieval_plan.get("ambiguity_class", "")).strip(),
        guidance_coverage=str(retrieval_plan.get("guidance_coverage", "")).strip(),
        intent_family=str(packet_quality.get("intent_family", "")).strip(),
        actionability_score=actionability_score,
        validation_score=validation_score,
        context_density_score=_hot_path_signal_score(packet_quality.get("context_density_level")),
        evidence_quality_score=max(
            _hot_path_signal_score(execution_signals.get("grounding")),
            4 if int(retrieval_plan.get("precision_score", 0) or 0) >= 75 else 3 if int(retrieval_plan.get("precision_score", 0) or 0) >= 50 else 2 if int(retrieval_plan.get("precision_score", 0) or 0) >= 25 else 0,
        ),
        evidence_consensus=str(retrieval_plan.get("evidence_consensus", "")).strip(),
        precision_score=int(retrieval_plan.get("precision_score", 0) or 0),
        direct_guidance_chunk_count=max(0, int(selected_counts.get("guidance", 0) or 0)),
        actionable_guidance_chunk_count=max(0, int(selected_counts.get("guidance", 0) or 0)),
        selected_test_count=max(0, int(selected_counts.get("tests", 0) or 0)),
        selected_command_count=max(0, int(selected_counts.get("commands", 0) or 0)),
        selected_doc_count=_governance_closeout_doc_count(governance_obligations),
        strict_gate_command_count=odylith_context_engine_hot_path_packet_bootstrap_runtime._validation_bundle_command_count(
            validation_bundle,
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        ),
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
    )
    routing_confidence = str(packet_quality.get("routing_confidence", "")).strip() or str(compact_payload.get("routing_confidence", "")).strip()
    if route_ready and (
        not execution_profile
        or str(execution_profile.get("delegate_preference", "")).strip() != "delegate"
        or not all(
            str(execution_profile.get(key, "")).strip()
            for key in ("model", "reasoning_effort", "agent_role", "selection_mode")
        )
    ):
        execution_profile = _hot_path_synthesized_execution_profile(
            packet_kind=packet_kind,
            route_ready=route_ready,
            within_budget=within_budget,
            full_scan_recommended=bool(compact_payload.get("full_scan_recommended")),
            narrowing_required=bool(route.get("narrowing_required")),
            routing_confidence=routing_confidence,
            intent_family=str(packet_quality.get("intent_family", "")).strip(),
            validation_count=validation_count,
            guidance_count=max(0, int(selected_counts.get("guidance", 0) or 0)),
            closeout_doc_count=_governance_closeout_doc_count(governance_obligations),
            strict_gate_command_count=odylith_context_engine_hot_path_packet_bootstrap_runtime._validation_bundle_command_count(
                validation_bundle,
                list_key="strict_gate_commands",
                count_key="strict_gate_command_count",
            ),
            plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
            governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
            host_runtime=str(execution_profile.get("host_runtime", "")).strip(),
        )
    native_spawn_ready = _store().routing.native_spawn_execution_ready(
        route_ready=route_ready,
        full_scan_recommended=bool(compact_payload.get("full_scan_recommended")),
        narrowing_required=bool(route.get("narrowing_required")),
        within_budget=within_budget,
        delegate_preference=str(execution_profile.get("delegate_preference", "")).strip(),
        model=str(execution_profile.get("model", "")).strip(),
        reasoning_effort=str(execution_profile.get("reasoning_effort", "")).strip(),
        agent_role=str(execution_profile.get("agent_role", "")).strip(),
        selection_mode=str(execution_profile.get("selection_mode", "")).strip(),
        selected_test_count=max(0, int(selected_counts.get("tests", 0) or 0)),
        selected_command_count=max(0, int(selected_counts.get("commands", 0) or 0)),
        selected_doc_count=_governance_closeout_doc_count(governance_obligations),
        strict_gate_command_count=odylith_context_engine_hot_path_packet_bootstrap_runtime._validation_bundle_command_count(
            validation_bundle,
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        ),
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
    )
    return {
        "route_ready": route_ready,
        "native_spawn_ready": native_spawn_ready,
        "execution_profile": execution_profile,
    }

def _compact_hot_path_routing_handoff(summary: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "session_id": str(summary.get("session_id", "")).strip(),
            "working_tree_scope": str(summary.get("working_tree_scope", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    claim_paths = _store()._normalized_string_list(summary.get("claim_paths"))
    if claim_paths:
        compact["claim_paths"] = claim_paths[:4]
    execution_profile = _compact_hot_path_route_execution_profile(
        dict(summary.get("odylith_execution_profile", {}))
        if isinstance(summary.get("odylith_execution_profile"), _store().Mapping)
        else {}
    )
    compact_execution_profile = _encode_hot_path_execution_profile(execution_profile)
    if compact_execution_profile:
        compact["execution_profile"] = compact_execution_profile
    return compact

def _compact_hot_path_route_execution_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    return _store().tooling_memory_contracts.compact_execution_profile_mapping(profile)

def _encode_hot_path_execution_profile(profile: Mapping[str, Any]) -> str:
    return _store().tooling_memory_contracts.encode_execution_profile_token(profile)

def _decode_hot_path_execution_profile(value: Any) -> dict[str, Any]:
    return _store().tooling_memory_contracts.compact_execution_profile_mapping(value)

def _hot_path_execution_profile_runtime_fields(profile: str, *, host_runtime: str = "") -> tuple[str, str]:
    return agent_runtime_contract.execution_profile_runtime_fields(
        profile,
        host_runtime=host_runtime,
    )

def _compact_hot_path_payload_within_budget(
    *,
    payload: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    packet_metrics: Mapping[str, Any],
) -> bool:
    if packet_metrics:
        return bool(packet_metrics.get("within_budget"))
    optimization = (
        dict(context_packet.get("optimization", {}))
        if isinstance(context_packet.get("optimization"), _store().Mapping)
        else {}
    )
    if "within_budget" in optimization:
        return bool(optimization.get("within_budget"))
    packet_budget = (
        dict(context_packet.get("packet_budget", {}))
        if isinstance(context_packet.get("packet_budget"), _store().Mapping)
        else {}
    )
    if "within_budget" in packet_budget:
        return bool(packet_budget.get("within_budget"))
    packet_state = str(context_packet.get("packet_state", "")).strip()
    return bool(context_packet) and not isinstance(payload.get("packet_metrics"), _store().Mapping) and packet_state in {
        "compact",
        "gated_ambiguous",
        "gated_broad_scope",
        "gated_low_signal",
    }

def _synthesized_hot_path_execution_profile_from_context_packet(context_packet: Mapping[str, Any]) -> dict[str, Any]:
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), _store().Mapping) else {}
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), _store().Mapping)
        else {}
    )
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), _store().Mapping)
        else {}
    )
    governance = governance_signal_codec.expand_governance_signal(
        dict(route.get("governance", {})) if isinstance(route.get("governance"), _store().Mapping) else {}
    )
    selected_counts = _store()._decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
    return _hot_path_synthesized_execution_profile(
        packet_kind=str(context_packet.get("packet_kind", "")).strip(),
        route_ready=bool(route.get("route_ready")),
        within_budget=True,
        full_scan_recommended=bool(context_packet.get("full_scan_recommended")),
        narrowing_required=bool(route.get("narrowing_required")),
        routing_confidence=str(packet_quality.get("routing_confidence", "")).strip(),
        intent_family=str(packet_quality.get("intent_family", "")).strip(),
        validation_count=max(0, int(selected_counts.get("tests", 0) or 0))
        + max(0, int(selected_counts.get("commands", 0) or 0)),
        guidance_count=max(0, int(selected_counts.get("guidance", 0) or 0)),
        closeout_doc_count=max(0, int(governance.get("closeout_doc_count", 0) or 0)),
        strict_gate_command_count=max(0, int(governance.get("strict_gate_command_count", 0) or 0)),
        plan_binding_required=bool(governance.get("plan_binding_required")),
        governed_surface_sync_required=bool(governance.get("governed_surface_sync_required")),
        host_runtime=str(context_packet.get("host_runtime", "")).strip(),
    )

def _governance_closeout_doc_count(obligations: Mapping[str, Any]) -> int:
    return odylith_context_engine_hot_path_packet_bootstrap_runtime._governance_obligation_count(
        obligations,
        list_key="closeout_docs",
        count_key="closeout_doc_count",
    )


def _governance_changed_paths_shadow_redundant(
    *,
    changed_paths: Sequence[str],
    context_packet_payload: Mapping[str, Any],
    docs: Sequence[str],
) -> bool:
    normalized_changed = _store()._normalized_string_list(changed_paths)
    if not normalized_changed:
        return False
    route_payload = (
        dict(context_packet_payload.get("route", {}))
        if isinstance(context_packet_payload.get("route"), _store().Mapping)
        else {}
    )
    if not bool(route_payload.get("route_ready")):
        return False
    anchors_payload = (
        dict(context_packet_payload.get("anchors", {}))
        if isinstance(context_packet_payload.get("anchors"), _store().Mapping)
        else {}
    )
    anchor_changed = _store()._normalized_string_list(anchors_payload.get("changed_paths"))
    if not anchor_changed:
        return False
    covered_paths = set(anchor_changed)
    covered_paths.update(_store()._normalized_string_list(docs))
    return not any(path not in covered_paths for path in normalized_changed)

def _trim_common_hot_path_context_packet(
    *,
    context_packet_payload: Mapping[str, Any],
    within_budget: bool,
) -> dict[str, Any]:
    compact = dict(context_packet_payload)
    packet_kind = str(compact.get("packet_kind", "")).strip()
    if packet_kind == "impact":
        compact.pop("packet_kind", None)
    route_payload = (
        dict(compact.get("route", {}))
        if isinstance(compact.get("route"), _store().Mapping)
        else {}
    )
    route_ready = bool(route_payload.get("route_ready"))
    if route_payload:
        if not bool(route_payload.get("native_spawn_ready")):
            route_payload.pop("native_spawn_ready", None)
        if not route_ready:
            route_payload.pop("route_ready", None)
            route_payload.pop("reasoning_bias", None)
            route_payload.pop("parallelism_hint", None)
        else:
            parallelism_hint = str(route_payload.get("parallelism_hint", "")).strip()
            reasoning_bias = str(route_payload.get("reasoning_bias", "")).strip()
            if parallelism_hint:
                route_payload["p"] = parallelism_hint
                route_payload.pop("parallelism_hint", None)
            if reasoning_bias:
                route_payload["b"] = reasoning_bias
                route_payload.pop("reasoning_bias", None)
        compact["route"] = route_payload
    anchors_payload = (
        dict(compact.get("anchors", {}))
        if isinstance(compact.get("anchors"), _store().Mapping)
        else {}
    )
    if anchors_payload:
        changed_anchor_paths = _store()._normalized_string_list(anchors_payload.get("changed_paths"))
        explicit_anchor_paths = _store()._normalized_string_list(anchors_payload.get("explicit_paths"))
        if changed_anchor_paths:
            anchors_payload["changed_paths"] = changed_anchor_paths[:5]
        if explicit_anchor_paths and explicit_anchor_paths != changed_anchor_paths:
            anchors_payload["explicit_paths"] = explicit_anchor_paths[:5]
        else:
            anchors_payload.pop("explicit_paths", None)
        anchors_payload.pop("anchor_quality", None)
        if not bool(anchors_payload.get("has_non_shared_anchor")):
            anchors_payload.pop("has_non_shared_anchor", None)
        compact["anchors"] = anchors_payload
    execution_profile_payload = _compact_hot_path_route_execution_profile(
        dict(compact.get("execution_profile", {}))
        if isinstance(compact.get("execution_profile"), _store().Mapping)
        else {}
    )
    if execution_profile_payload:
        if route_ready or str(execution_profile_payload.get("delegate_preference", "")).strip() not in {
            "",
            "hold_local",
        }:
            compact["execution_profile"] = execution_profile_payload
        else:
            compact.pop("execution_profile", None)
    else:
        compact.pop("execution_profile", None)
    selection_state = str(compact.get("selection_state", "")).strip()
    if selection_state == "none" or (packet_kind == "impact" and selection_state == "ambiguous"):
        compact.pop("selection_state", None)
    retrieval_plan_payload = (
        dict(compact.get("retrieval_plan", {}))
        if isinstance(compact.get("retrieval_plan"), _store().Mapping)
        else {}
    )
    if retrieval_plan_payload:
        ambiguity_class = str(retrieval_plan_payload.get("ambiguity_class", "")).strip()
        has_guidance_behavior_summary = isinstance(compact.get("guidance_behavior_summary"), _store().Mapping)
        retrieval_plan_payload.pop("selected_domains", None)
        selected_counts_payload = _store()._decode_compact_selected_counts(
            retrieval_plan_payload.get("selected_counts")
        )
        if selected_counts_payload:
            compact_selected_counts = _store()._encode_compact_selected_counts(selected_counts_payload)
            if compact_selected_counts:
                retrieval_plan_payload["selected_counts"] = compact_selected_counts
            else:
                retrieval_plan_payload.pop("selected_counts", None)
        if str(retrieval_plan_payload.get("guidance_coverage", "")).strip() in {"", "none"}:
            retrieval_plan_payload.pop("guidance_coverage", None)
        if not route_ready and str(retrieval_plan_payload.get("evidence_consensus", "")).strip() in {"", "none", "mixed"}:
            retrieval_plan_payload.pop("evidence_consensus", None)
        if (
            (packet_kind == "impact" or (not packet_kind and not has_guidance_behavior_summary))
            and not route_ready
            and ambiguity_class in {"no_candidates", "low_signal", "selection_ambiguous"}
        ):
            retrieval_plan_payload.pop("selected_counts", None)
        if not route_ready and ambiguity_class in {"no_candidates", "low_signal", "selection_ambiguous"}:
            retrieval_plan_payload.pop("precision_score", None)
        miss_recovery_payload = (
            dict(retrieval_plan_payload.get("miss_recovery", {}))
            if isinstance(retrieval_plan_payload.get("miss_recovery"), _store().Mapping)
            else {}
        )
        if miss_recovery_payload and not any(
            [
                bool(miss_recovery_payload.get("active")),
                bool(miss_recovery_payload.get("applied")),
                str(miss_recovery_payload.get("mode", "")).strip(),
            ]
        ):
            retrieval_plan_payload.pop("miss_recovery", None)
        compact["retrieval_plan"] = retrieval_plan_payload
    packet_quality_payload = (
        dict(compact.get("packet_quality", {}))
        if isinstance(compact.get("packet_quality"), _store().Mapping)
        else {}
    )
    if packet_quality_payload:
        for key in ("context_density_level", "reasoning_readiness_level", "context_richness", "accuracy_posture", "utility_score"):
            packet_quality_payload.pop(key, None)
        compact_packet_quality = packet_quality_codec.compact_packet_quality(packet_quality_payload)
        if compact_packet_quality:
            compact["packet_quality"] = compact_packet_quality
        else:
            compact.pop("packet_quality", None)
    packet_budget_payload = (
        dict(compact.get("packet_budget", {}))
        if isinstance(compact.get("packet_budget"), _store().Mapping)
        else {}
    )
    if packet_budget_payload and (within_budget or bool(packet_budget_payload.get("within_budget"))):
        compact.pop("packet_budget", None)
    compact.pop("packet_metrics", None)
    compact.pop("optimization", None)
    compact.pop("provenance_summary", None)
    for key in ("contract", "engine", "security_posture", "version"):
        compact.pop(key, None)
    if not bool(compact.get("full_scan_recommended")):
        compact.pop("full_scan_recommended", None)
    if not str(compact.get("full_scan_reason", "")).strip():
        compact.pop("full_scan_reason", None)
    return compact

def _compact_hot_path_narrowing_guidance(guidance: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    if bool(guidance.get("required")):
        compact["required"] = True
    reason = str(guidance.get("reason", "")).strip()
    if reason:
        compact["reason"] = (
            "Top candidate is not grounded yet."
            if reason.startswith("Top candidate `") and reason.endswith("is too weak to auto-trust.")
            else _store()._truncate_text(reason, max_chars=40)
        )
    suggestion_map = {
        "Provide at least one implementation, test, contract, or manifest path.": "Provide one code or contract path.",
        "Pin an explicit workstream with `--workstream B-###` when the slice is known.": "Pin `--workstream B-###` if known.",
        "Read the highest-signal guidance source directly when the packet exposes one.": "Read the strongest cited source first.",
        "If narrowing still fails, run the printed fallback command and then read the named source directly.": "Use the printed fallback command if narrowing fails.",
    }
    suggested_inputs = [
        suggestion_map.get(text, text)
        for text in _store()._normalized_string_list(guidance.get("suggested_inputs"))[:1]
    ]
    if suggested_inputs:
        compact["suggested_inputs"] = suggested_inputs
    anchors = []
    for row in guidance.get("next_best_anchors", [])[:1]:
        if not isinstance(row, _store().Mapping):
            continue
        value = str(row.get("value", "")).strip()
        if not value:
            continue
        anchor = {
            key: value
            for key, value in {
                "kind": ""
                if str(row.get("kind", "")).strip() == "workstream"
                else str(row.get("kind", "")).strip(),
                "value": value,
            }.items()
            if value not in ("", [], {}, None)
        }
        if anchor:
            anchors.append(anchor)
        if len(anchors) >= 2:
            break
    if anchors:
        compact["next_best_anchors"] = anchors
    # Keep shell fallback commands in the bootstrap/operator lane, but do not
    # spend hot-path prompt budget on terminal syntax once the compact
    # guidance already tells the model that one concrete code path is needed.
    if (
        compact.get("reason") == "Top candidate is not grounded yet."
        and compact.get("suggested_inputs") == ["Provide one code or contract path."]
        and anchors
        and len(anchors) == 1
        and _store()._workstream_token(str(anchors[0].get("value", "")).strip())
    ):
        compact["reason"] = "Need one code or contract path."
        compact.pop("suggested_inputs", None)
        compact.pop("next_best_anchors", None)
    if (
        str(compact.get("reason", "")).startswith("No workstream evidence matched")
        and compact.get("suggested_inputs") == ["Provide one code or contract path."]
        and not anchors
    ):
        compact["reason"] = "Need one code path."
        compact.pop("suggested_inputs", None)
    anchor_kinds = {
        str(row.get("kind", "")).strip()
        for row in anchors
        if isinstance(row, _store().Mapping)
    }
    if (
        compact.get("suggested_inputs") == ["Provide one code or contract path."]
        and anchor_kinds
        and anchor_kinds.issubset({"doc"})
    ):
        compact["reason"] = "Need one code path."
        compact.pop("suggested_inputs", None)
        compact.pop("next_best_anchors", None)
    if (
        str(compact.get("reason", "")).strip() == "selection_ambiguous"
        and compact.get("suggested_inputs") == ["Provide one code or contract path."]
    ):
        compact["reason"] = "Need one code or contract path."
        compact.pop("suggested_inputs", None)
        compact.pop("next_best_anchors", None)
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}, None, False)
    }

def _source_hot_path_within_budget(payload: Mapping[str, Any]) -> bool:
    packet_metrics = (
        dict(payload.get("packet_metrics", {}))
        if isinstance(payload.get("packet_metrics"), _store().Mapping)
        else {}
    )
    if packet_metrics:
        return bool(packet_metrics.get("within_budget", True))
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), _store().Mapping)
        else {}
    )
    packet_budget = (
        dict(context_packet.get("packet_budget", {}))
        if isinstance(context_packet.get("packet_budget"), _store().Mapping)
        else {}
    )
    return bool(packet_budget.get("within_budget", True))

def _fast_finalize_compact_hot_path_packet(
    *,
    compact: Mapping[str, Any],
    within_budget: bool,
    full_scan_recommended: bool,
) -> dict[str, Any]:
    from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_finalize_runtime

    trimmed: dict[str, Any] = {
        key: (
            dict(value)
            if isinstance(value, _store().Mapping)
            else [dict(row) if isinstance(row, _store().Mapping) else row for row in value]
            if isinstance(value, list)
            else value
        )
        for key, value in compact.items()
    }
    context_packet_payload = (
        dict(trimmed.get("context_packet", {}))
        if isinstance(trimmed.get("context_packet"), _store().Mapping)
        else {}
    )
    if context_packet_payload:
        trimmed["context_packet"] = _trim_common_hot_path_context_packet(
            context_packet_payload=context_packet_payload,
            within_budget=within_budget,
        )
    trimmed.pop("packet_metrics", None)
    return _drop_redundant_hot_path_routing_handoff(
        odylith_context_engine_hot_path_packet_finalize_runtime._trim_route_ready_hot_path_prompt_payload(
            compact=trimmed,
            full_scan_recommended=full_scan_recommended,
        )
    )

def _compact_hot_path_packet_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    if bool(metrics.get("within_budget")):
        return {}
    compact = {
        key: value
        for key, value in {
            "estimated_tokens": int(metrics.get("estimated_tokens", 0) or 0),
            "within_budget": bool(metrics.get("within_budget")),
        }.items()
        if value not in ("", [], {}, None, 0, False)
    }
    if "within_budget" not in compact:
        compact["within_budget"] = bool(metrics.get("within_budget"))
    return compact

def _drop_redundant_hot_path_routing_handoff(payload: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: (
            dict(value)
            if isinstance(value, _store().Mapping)
            else [dict(row) if isinstance(row, _store().Mapping) else row for row in value]
            if isinstance(value, list)
            else value
        )
        for key, value in payload.items()
    }
    routing_handoff = (
        dict(compact.get("routing_handoff", {}))
        if isinstance(compact.get("routing_handoff"), _store().Mapping)
        else {}
    )
    if not routing_handoff:
        compact.pop("routing_handoff", None)
        return compact
    if any(
        key in routing_handoff
        for key in ("odylith_execution_profile", "execution_profile", "claim_paths", "session_id", "working_tree_scope")
    ):
        if (
            set(routing_handoff).issubset({"odylith_execution_profile", "execution_profile"})
            and isinstance(compact.get("context_packet"), _store().Mapping)
        ):
            context_packet = dict(compact.get("context_packet", {}))
            context_execution_profile = _compact_hot_path_route_execution_profile(
                dict(context_packet.get("execution_profile", {}))
                if isinstance(context_packet.get("execution_profile"), _store().Mapping)
                else _synthesized_hot_path_execution_profile_from_context_packet(context_packet)
            )
            routing_execution_profile = _decode_hot_path_execution_profile(
                routing_handoff.get("execution_profile") or routing_handoff.get("odylith_execution_profile")
            )
            if context_execution_profile and context_execution_profile == routing_execution_profile:
                compact.pop("routing_handoff", None)
        return compact
    redundant_keys = {
        "packet_kind",
        "routing_confidence",
        "within_budget",
        "narrowing_required",
        "route_ready",
        "native_spawn_ready",
        "reasoning_bias",
        "parallelism_hint",
    }
    if set(routing_handoff).issubset(redundant_keys):
        compact.pop("routing_handoff", None)
    return compact

def _compact_hot_path_fallback_scan(
    *,
    full_scan_reason: str,
    changed_paths: Sequence[str],
    context_packet: Mapping[str, Any],
    fallback_scan: Mapping[str, Any],
) -> dict[str, Any]:
    if not bool(fallback_scan.get("performed")):
        return {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), _store().Mapping) else {}
    packet_state = str(context_packet.get("packet_state", "")).strip()
    suppress_result_paths = bool(
        packet_state in {"gated_ambiguous", "gated_broad_scope"}
        or bool(route.get("narrowing_required"))
        or not bool(route.get("route_ready"))
    )
    compact_fallback = {
        "recommended": True,
        "reason": str(full_scan_reason or "").strip() or str(fallback_scan.get("reason", "")).strip(),
        "performed": True,
    }
    if not suppress_result_paths and isinstance(fallback_scan.get("results"), list):
        results = [
            {
                key: value
                for key, value in {
                    "path": str(row.get("path", "")).strip(),
                    "kind": str(row.get("kind", "")).strip(),
                }.items()
                if value not in ("", [], {}, None)
            }
            for row in fallback_scan.get("results", [])
            if isinstance(row, _store().Mapping) and str(row.get("path", "")).strip()
        ]
        deduped_results: list[dict[str, Any]] = []
        seen_paths: set[str] = set()
        for row in results:
            path = str(row.get("path", "")).strip()
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            deduped_results.append(row)
            if len(deduped_results) >= 2:
                break
        if deduped_results:
            compact_fallback["results"] = deduped_results
    return compact_fallback
