from __future__ import annotations

from typing import Any

from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.context_engine import path_bundle_codec


_BENCHMARK_IMPACT_COMPANION_DOC_EXPANSION_PATHS = frozenset(
    {
        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
    }
)
_BENCHMARK_RUNNER_REVIEWER_GUIDE = "docs/benchmarks/REVIEWER_GUIDE.md"


def bind(host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in ('Any', 'Mapping', 'Path', 'Sequence', '_compact_architecture_audit_for_packet', '_compact_hot_path_auto_escalation', '_compact_hot_path_session_payload', '_compact_hot_path_workstream_context', '_compact_selection_state_parts', '_companion_context_paths_for_normalized_changed_paths', '_decode_compact_selected_counts', '_dedupe_strings', '_encode_compact_selected_counts', '_encode_compact_selection_state', '_governance_diagram_catalog_companions', '_normalized_string_list', '_payload_workstream_hint', '_truncate_text', '_workstream_token', 'actionability', 'actionability_score', 'active_session_count', 'agent_role', 'ambiguity_class', 'anchor', 'anchor_kinds', 'anchors', 'anchors_payload', 'audit', 'authoritative_governance_docs', 'bucket', 'bucket_name', 'budget_meta', 'bundle', 'candidate_count', 'changed_anchor_paths', 'changed_paths', 'claim_paths', 'closeout_doc_count', 'closeout_docs', 'compact', 'compact_architecture_audit', 'compact_auto_escalation', 'compact_changed_paths', 'compact_conflicts', 'compact_docs', 'compact_execution_profile', 'compact_execution_profile_payload', 'compact_fallback', 'compact_narrowing_guidance', 'compact_obligations', 'compact_packet_metrics', 'compact_payload', 'compact_profile', 'compact_selected_counts', 'compact_state', 'compact_validation', 'compact_workstream', 'compact_workstream_context', 'compacted_reason', 'companion_docs', 'confidence', 'confidence_score', 'conflicts', 'context_density', 'context_execution_profile', 'context_packet', 'context_packet_payload', 'contract_keys', 'count_key', 'coverage', 'current_native_spawn_ready', 'current_route_ready', 'diagram_count', 'doc', 'effective_changed_paths', 'effective_full_scan_reason', 'effective_full_scan_recommended', 'effective_surface_count', 'entity_id', 'evidence', 'evidence_diversity', 'evidence_quality', 'execution_profile', 'execution_profile_payload', 'execution_signals', 'explicit_anchor_paths', 'explicit_paths', 'fallback_scan', 'family', 'field', 'field_name', 'full_scan_reason', 'full_scan_recommended', 'governance', 'governance_contract', 'governance_hot_path_docs', 'governance_obligations', 'governance_obligations_payload', 'governance_signal', 'governed_surface_sync_required', 'grouped_reasons', 'grouped_surface_union', 'guidance', 'guidance_count', 'impacted', 'inferred_workstream', 'input_anchors', 'input_context_packet', 'intent', 'intent_family', 'intent_profile', 'is_component_spec_path', 'item', 'keep', 'keep_scalar', 'key', 'linked_bug_count', 'linked_bugs', 'list_key', 'merged', 'metadata', 'metrics', 'miss_recovery', 'miss_recovery_payload', 'model', 'narrowing_guidance', 'narrowing_payload', 'narrowing_required', 'native_spawn_ready', 'non_anchor_docs', 'normalized', 'obligations', 'optimization', 'optimization_payload', 'packet', 'packet_budget', 'packet_budget_payload', 'packet_kind', 'packet_metrics', 'packet_metrics_payload', 'packet_quality', 'packet_quality_payload', 'packet_state', 'parallelism_hint', 'part', 'parts', 'payload', 'plan', 'plan_binding_required', 'prefix', 'prioritized_docs', 'profile', 'raw_score', 'readiness', 'reason', 'reasoning_bias', 'reasoning_effort', 'reasoning_readiness', 'recommended_commands', 'redundant_keys', 'required_diagrams', 'retain_internal_context', 'retrieval_plan', 'retrieval_plan_payload', 'route', 'route_payload', 'route_ready', 'routing', 'routing_confidence', 'routing_execution_profile', 'routing_handoff', 'routing_handoff_payload', 'row', 'rows', 'selected', 'selected_counts', 'selected_counts_payload', 'selected_domains', 'selected_id', 'selected_workstream', 'selection', 'selection_mode', 'selection_state', 'session_payload', 'session_seed_paths', 'source_context_packet', 'source_fallback', 'source_route', 'state', 'strict_gate_command_count', 'strict_gate_commands', 'strong_candidate_count', 'suggested_inputs', 'suggestion_map', 'summary', 'supportive_contract', 'suppress_governance_architecture_audit', 'surface', 'surface_count', 'surface_refs', 'surface_refs_payload', 'surfaces', 'text', 'token', 'token_efficiency', 'tooling_context_budgeting', 'tooling_memory_contracts', 'top_candidate', 'top_candidate_id', 'touched_component_ids', 'touched_components', 'touched_workstream_ids', 'touched_workstreams', 'trimmed', 'utility_profile', 'validation_bundle', 'validation_bundle_payload', 'validation_count', 'validation_pressure', 'validation_score', 'value', 'within_budget', 'workstream_context', 'workstream_hint', 'workstream_state_actions'):
        try:
            globals()[name] = getter(name)
        except (AttributeError, KeyError):
            continue


def _compact_hot_path_active_conflicts(conflicts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in conflicts[:4]:
        if not isinstance(row, Mapping):
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
                    "shared_paths": _normalized_string_list(row.get("shared_paths"))[:3],
                    "shared_surfaces": _normalized_string_list(row.get("shared_surfaces"))[:3],
                }.items()
                if value not in ("", [], {}, None, False)
            }
        )
    return compact

def _hot_path_keep_architecture_audit(audit: Mapping[str, Any]) -> bool:
    if not isinstance(audit, Mapping) or not audit:
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
    coverage = dict(audit.get("coverage", {})) if isinstance(audit.get("coverage"), Mapping) else {}
    return int(coverage.get("score", 0) or 0) > 0

def _hot_path_workstream_selection(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    selection = dict(payload.get("workstream_selection", {})) if isinstance(payload.get("workstream_selection"), Mapping) else {}
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), Mapping)
        else {}
    )
    compact_state, compact_workstream = _compact_selection_state_parts(
        str(payload.get("selection_state", "")).strip()
        or str(context_packet.get("selection_state", "")).strip()
    )
    state = compact_state or str(selection.get("state", "")).strip()
    inferred_workstream = _payload_workstream_hint(payload, include_selection=False)
    if not state and inferred_workstream:
        state = "inferred_confident"
    if not state:
        return {}
    selected_workstream = (
        dict(selection.get("selected_workstream", {}))
        if isinstance(selection.get("selected_workstream"), Mapping)
        else {}
    )
    top_candidate = (
        dict(selection.get("top_candidate", {}))
        if isinstance(selection.get("top_candidate"), Mapping)
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
            if isinstance(selection.get("competing_candidates"), list) and isinstance(row, Mapping)
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
    selected = dict(selection.get("selected_workstream", {})) if isinstance(selection.get("selected_workstream"), Mapping) else {}
    top_candidate = dict(selection.get("top_candidate", {})) if isinstance(selection.get("top_candidate"), Mapping) else {}
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
    selected_domains = _normalized_string_list(plan.get("selected_domains"))
    if selected_domains:
        compact["selected_domains"] = selected_domains[:4]
    miss_recovery = dict(plan.get("miss_recovery", {})) if isinstance(plan.get("miss_recovery"), Mapping) else {}
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
    utility_profile = dict(summary.get("utility_profile", {})) if isinstance(summary.get("utility_profile"), Mapping) else {}
    token_efficiency = dict(utility_profile.get("token_efficiency", {})) if isinstance(utility_profile.get("token_efficiency"), Mapping) else {}
    intent_profile = dict(summary.get("intent_profile", {})) if isinstance(summary.get("intent_profile"), Mapping) else {}
    context_density = dict(summary.get("context_density", {})) if isinstance(summary.get("context_density"), Mapping) else {}
    reasoning_readiness = (
        dict(summary.get("reasoning_readiness", {})) if isinstance(summary.get("reasoning_readiness"), Mapping) else {}
    )
    evidence_quality = dict(summary.get("evidence_quality", {})) if isinstance(summary.get("evidence_quality"), Mapping) else {}
    actionability = dict(summary.get("actionability", {})) if isinstance(summary.get("actionability"), Mapping) else {}
    validation_pressure = (
        dict(summary.get("validation_pressure", {})) if isinstance(summary.get("validation_pressure"), Mapping) else {}
    )
    evidence_diversity = (
        dict(summary.get("evidence_diversity", {})) if isinstance(summary.get("evidence_diversity"), Mapping) else {}
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
    intent = dict(summary.get("intent", {})) if isinstance(summary.get("intent"), Mapping) else {}
    packet_quality = dict(summary.get("packet_quality", {})) if isinstance(summary.get("packet_quality"), Mapping) else {}
    intent_profile = dict(packet_quality.get("intent_profile", {})) if isinstance(packet_quality.get("intent_profile"), Mapping) else {}
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
    if isinstance(value, Mapping):
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
    profile = "mini_medium"
    model = "gpt-5.4-mini"
    reasoning_effort = "medium"
    agent_role = "explorer"
    selection_mode = "analysis_scout"
    if family in {"implementation", "write", "bugfix"}:
        if governance_contract and strict_gate_command_count > 0:
            profile = "gpt54_high"
            model = "gpt-5.4"
            reasoning_effort = "high"
            selection_mode = "deep_validation"
        else:
            profile = "codex_high" if confidence == "high" and (validation_count > 0 or guidance_count >= 2) else "codex_medium"
            model = "gpt-5.3-codex"
            reasoning_effort = "high" if profile == "codex_high" else "medium"
            selection_mode = "bounded_write"
        agent_role = "worker"
    elif family == "validation":
        profile = "codex_high" if confidence == "high" or validation_count >= 2 or strict_gate_command_count > 0 else "codex_medium"
        model = "gpt-5.3-codex"
        reasoning_effort = "high" if profile == "codex_high" else "medium"
        agent_role = "worker"
        selection_mode = "validation_focused"
    elif family in {"docs", "governance"}:
        profile = "spark_medium" if governance_contract else "mini_medium"
        model = "gpt-5.3-codex-spark" if profile == "spark_medium" else "gpt-5.4-mini"
        reasoning_effort = "medium"
        agent_role = "worker" if profile == "spark_medium" else "explorer"
        selection_mode = "support_fast_lane" if profile == "spark_medium" else "analysis_scout"
    elif family in {"analysis", "review", "diagnosis"}:
        profile = "mini_high" if confidence == "high" or supportive_contract else "mini_medium"
        model = "gpt-5.4-mini"
        reasoning_effort = "high" if profile == "mini_high" else "medium"
        agent_role = "explorer"
        selection_mode = "analysis_synthesis" if profile == "mini_high" else "analysis_scout"
    confidence_score = 4 if confidence == "high" else 3 if confidence == "medium" else 2
    return {
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

def _hot_path_recomputed_readiness(
    *,
    packet_kind: str,
    packet_state: str,
    compact_payload: Mapping[str, Any],
    within_budget: bool,
) -> dict[str, Any]:
    routing_handoff = dict(compact_payload.get("routing_handoff", {})) if isinstance(compact_payload.get("routing_handoff"), Mapping) else {}
    context_packet = dict(compact_payload.get("context_packet", {})) if isinstance(compact_payload.get("context_packet"), Mapping) else {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
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
    retrieval_plan = dict(context_packet.get("retrieval_plan", {})) if isinstance(context_packet.get("retrieval_plan"), Mapping) else {}
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {})) if isinstance(context_packet.get("packet_quality"), Mapping) else {}
    )
    execution_profile = (
        dict(context_packet.get("execution_profile", {}))
        if isinstance(context_packet.get("execution_profile"), Mapping)
        else {}
    )
    execution_signals = (
        dict(execution_profile.get("signals", {}))
        if isinstance(execution_profile.get("signals"), Mapping)
        else {}
    )
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    if not context_packet or not retrieval_plan or not anchors:
        return {
            "route_ready": current_route_ready,
            "native_spawn_ready": current_native_spawn_ready,
            "execution_profile": execution_profile,
        }
    selected_counts = _decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
    validation_count = max(
        0,
        int(selected_counts.get("tests", 0) or 0),
    ) + max(
        0,
        int(selected_counts.get("commands", 0) or 0),
    )
    validation_bundle = _hot_path_validation_bundle(compact_payload, context_packet=context_packet)
    governance_obligations = _hot_path_governance_obligations(compact_payload, context_packet=context_packet)
    actionability_score = max(
        _hot_path_signal_score(execution_signals.get("actionability")),
        3 if max(0, int(selected_counts.get("guidance", 0) or 0)) >= 2 and validation_count > 0 else 2 if validation_count > 0 else 0,
    )
    validation_score = max(
        _hot_path_signal_score(execution_signals.get("validation_pressure")),
        3 if int(selected_counts.get("tests", 0) or 0) > 0 and int(selected_counts.get("commands", 0) or 0) > 0 else 2 if validation_count > 0 else 0,
    )
    route_ready = routing.grounded_write_execution_ready(
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
        strict_gate_command_count=_validation_bundle_command_count(
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
            strict_gate_command_count=_validation_bundle_command_count(
                validation_bundle,
                list_key="strict_gate_commands",
                count_key="strict_gate_command_count",
            ),
            plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
            governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
        )
    native_spawn_ready = routing.native_spawn_execution_ready(
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
        strict_gate_command_count=_validation_bundle_command_count(
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
    claim_paths = _normalized_string_list(summary.get("claim_paths"))
    if claim_paths:
        compact["claim_paths"] = claim_paths[:4]
    execution_profile = _compact_hot_path_route_execution_profile(
        dict(summary.get("odylith_execution_profile", {}))
        if isinstance(summary.get("odylith_execution_profile"), Mapping)
        else {}
    )
    compact_execution_profile = _encode_hot_path_execution_profile(execution_profile)
    if compact_execution_profile:
        compact["execution_profile"] = compact_execution_profile
    return compact

def _compact_hot_path_route_execution_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    return tooling_memory_contracts.compact_execution_profile_mapping(profile)

def _encode_hot_path_execution_profile(profile: Mapping[str, Any]) -> str:
    return tooling_memory_contracts.encode_execution_profile_token(profile)

def _decode_hot_path_execution_profile(value: Any) -> dict[str, Any]:
    return tooling_memory_contracts.compact_execution_profile_mapping(value)

def _hot_path_execution_profile_runtime_fields(profile: str) -> tuple[str, str]:
    token = str(profile or "").strip()
    if token == "mini_medium":
        return "gpt-5.4-mini", "medium"
    if token == "mini_high":
        return "gpt-5.4-mini", "high"
    if token == "spark_medium":
        return "gpt-5.3-codex-spark", "medium"
    if token == "codex_medium":
        return "gpt-5.3-codex", "medium"
    if token == "codex_high":
        return "gpt-5.3-codex", "high"
    if token == "gpt54_high":
        return "gpt-5.4", "high"
    if token == "gpt54_xhigh":
        return "gpt-5.4", "xhigh"
    return "", ""

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
        if isinstance(context_packet.get("optimization"), Mapping)
        else {}
    )
    if "within_budget" in optimization:
        return bool(optimization.get("within_budget"))
    packet_budget = (
        dict(context_packet.get("packet_budget", {}))
        if isinstance(context_packet.get("packet_budget"), Mapping)
        else {}
    )
    if "within_budget" in packet_budget:
        return bool(packet_budget.get("within_budget"))
    packet_state = str(context_packet.get("packet_state", "")).strip()
    return bool(context_packet) and not isinstance(payload.get("packet_metrics"), Mapping) and packet_state in {
        "compact",
        "gated_ambiguous",
        "gated_broad_scope",
        "gated_low_signal",
    }

def _synthesized_hot_path_execution_profile_from_context_packet(context_packet: Mapping[str, Any]) -> dict[str, Any]:
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    governance = governance_signal_codec.expand_governance_signal(
        dict(route.get("governance", {})) if isinstance(route.get("governance"), Mapping) else {}
    )
    selected_counts = _decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
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
    )

def _governance_closeout_doc_count(obligations: Mapping[str, Any]) -> int:
    return _governance_obligation_count(
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
    normalized_changed = _normalized_string_list(changed_paths)
    if not normalized_changed:
        return False
    route_payload = (
        dict(context_packet_payload.get("route", {}))
        if isinstance(context_packet_payload.get("route"), Mapping)
        else {}
    )
    if not bool(route_payload.get("route_ready")):
        return False
    anchors_payload = (
        dict(context_packet_payload.get("anchors", {}))
        if isinstance(context_packet_payload.get("anchors"), Mapping)
        else {}
    )
    anchor_changed = _normalized_string_list(anchors_payload.get("changed_paths"))
    if not anchor_changed:
        return False
    covered_paths = set(anchor_changed)
    covered_paths.update(_normalized_string_list(docs))
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
        if isinstance(compact.get("route"), Mapping)
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
        if isinstance(compact.get("anchors"), Mapping)
        else {}
    )
    if anchors_payload:
        changed_anchor_paths = _normalized_string_list(anchors_payload.get("changed_paths"))
        explicit_anchor_paths = _normalized_string_list(anchors_payload.get("explicit_paths"))
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
        if isinstance(compact.get("execution_profile"), Mapping)
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
        if isinstance(compact.get("retrieval_plan"), Mapping)
        else {}
    )
    if retrieval_plan_payload:
        ambiguity_class = str(retrieval_plan_payload.get("ambiguity_class", "")).strip()
        retrieval_plan_payload.pop("selected_domains", None)
        selected_counts_payload = _decode_compact_selected_counts(
            retrieval_plan_payload.get("selected_counts")
        )
        if selected_counts_payload:
            compact_selected_counts = _encode_compact_selected_counts(selected_counts_payload)
            if compact_selected_counts:
                retrieval_plan_payload["selected_counts"] = compact_selected_counts
            else:
                retrieval_plan_payload.pop("selected_counts", None)
        if str(retrieval_plan_payload.get("guidance_coverage", "")).strip() in {"", "none"}:
            retrieval_plan_payload.pop("guidance_coverage", None)
        if not route_ready and str(retrieval_plan_payload.get("evidence_consensus", "")).strip() in {"", "none", "mixed"}:
            retrieval_plan_payload.pop("evidence_consensus", None)
        if packet_kind == "impact" and not route_ready and ambiguity_class in {"no_candidates", "low_signal", "selection_ambiguous"}:
            retrieval_plan_payload.pop("selected_counts", None)
        if not route_ready and ambiguity_class in {"no_candidates", "low_signal", "selection_ambiguous"}:
            retrieval_plan_payload.pop("precision_score", None)
        miss_recovery_payload = (
            dict(retrieval_plan_payload.get("miss_recovery", {}))
            if isinstance(retrieval_plan_payload.get("miss_recovery"), Mapping)
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
        if isinstance(compact.get("packet_quality"), Mapping)
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
        if isinstance(compact.get("packet_budget"), Mapping)
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
            else _truncate_text(reason, max_chars=40)
        )
    suggestion_map = {
        "Provide at least one implementation, test, contract, or manifest path.": "Provide one code or contract path.",
        "Pin an explicit workstream with `--workstream B-###` when the slice is known.": "Pin `--workstream B-###` if known.",
        "Read the highest-signal guidance source directly when the packet exposes one.": "Read the strongest cited source first.",
        "If narrowing still fails, run the printed fallback command and then read the named source directly.": "Use the printed fallback command if narrowing fails.",
    }
    suggested_inputs = [
        suggestion_map.get(text, text)
        for text in _normalized_string_list(guidance.get("suggested_inputs"))[:1]
    ]
    if suggested_inputs:
        compact["suggested_inputs"] = suggested_inputs
    anchors = []
    for row in guidance.get("next_best_anchors", [])[:1]:
        if not isinstance(row, Mapping):
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
    # spend hot-path Codex prompt budget on terminal syntax once the compact
    # guidance already tells the model that one concrete code path is needed.
    if (
        compact.get("reason") == "Top candidate is not grounded yet."
        and compact.get("suggested_inputs") == ["Provide one code or contract path."]
        and anchors
        and len(anchors) == 1
        and _workstream_token(str(anchors[0].get("value", "")).strip())
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
        if isinstance(row, Mapping)
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
        if isinstance(payload.get("packet_metrics"), Mapping)
        else {}
    )
    if packet_metrics:
        return bool(packet_metrics.get("within_budget", True))
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), Mapping)
        else {}
    )
    packet_budget = (
        dict(context_packet.get("packet_budget", {}))
        if isinstance(context_packet.get("packet_budget"), Mapping)
        else {}
    )
    return bool(packet_budget.get("within_budget", True))

def _fast_finalize_compact_hot_path_packet(
    *,
    compact: Mapping[str, Any],
    within_budget: bool,
    full_scan_recommended: bool,
) -> dict[str, Any]:
    trimmed: dict[str, Any] = {
        key: (
            dict(value)
            if isinstance(value, Mapping)
            else [dict(row) if isinstance(row, Mapping) else row for row in value]
            if isinstance(value, list)
            else value
        )
        for key, value in compact.items()
    }
    context_packet_payload = (
        dict(trimmed.get("context_packet", {}))
        if isinstance(trimmed.get("context_packet"), Mapping)
        else {}
    )
    if context_packet_payload:
        trimmed["context_packet"] = _trim_common_hot_path_context_packet(
            context_packet_payload=context_packet_payload,
            within_budget=within_budget,
        )
    trimmed.pop("packet_metrics", None)
    return _drop_redundant_hot_path_routing_handoff(
        _trim_route_ready_hot_path_prompt_payload(
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
            if isinstance(value, Mapping)
            else [dict(row) if isinstance(row, Mapping) else row for row in value]
            if isinstance(value, list)
            else value
        )
        for key, value in payload.items()
    }
    routing_handoff = (
        dict(compact.get("routing_handoff", {}))
        if isinstance(compact.get("routing_handoff"), Mapping)
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
            and isinstance(compact.get("context_packet"), Mapping)
        ):
            context_packet = dict(compact.get("context_packet", {}))
            context_execution_profile = _compact_hot_path_route_execution_profile(
                dict(context_packet.get("execution_profile", {}))
                if isinstance(context_packet.get("execution_profile"), Mapping)
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
    compact_fallback = {
        "recommended": True,
        "reason": str(full_scan_reason or "").strip() or str(fallback_scan.get("reason", "")).strip(),
        "performed": True,
    }
    if isinstance(fallback_scan.get("results"), list):
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
            if isinstance(row, Mapping) and str(row.get("path", "")).strip()
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
    if not compact_fallback.get("results"):
        return {}
    return compact_fallback


def _compact_bootstrap_or_brief_hot_path_context_packet(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
    changed_paths: Sequence[str],
) -> tuple[dict[str, Any], bool]:
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), Mapping)
        else {}
    )
    anchors = (
        dict(context_packet.get("anchors", {}))
        if isinstance(context_packet.get("anchors"), Mapping)
        else {}
    )
    packet_state = str(context_packet.get("packet_state", "")).strip()
    has_non_shared_anchor = bool(anchors.get("has_non_shared_anchor"))
    anchor_quality = str(anchors.get("anchor_quality", "")).strip()
    if not anchor_quality:
        if has_non_shared_anchor:
            anchor_quality = "non_shared"
        elif changed_paths:
            anchor_quality = "shared_only"

    compact_context_packet = {
        key: value
        for key, value in {
            "packet_kind": str(context_packet.get("packet_kind", "")).strip() or str(packet_kind or "").strip(),
            "packet_state": packet_state,
        }.items()
        if value not in ("", [], {}, None)
    }

    compact_anchors: dict[str, Any] = {}
    if anchor_quality and anchor_quality != "non_shared":
        compact_anchors["anchor_quality"] = anchor_quality
    if has_non_shared_anchor:
        compact_anchors["has_non_shared_anchor"] = True
    if compact_anchors:
        compact_context_packet["anchors"] = compact_anchors

    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    ambiguity_class = str(retrieval_plan.get("ambiguity_class", "")).strip()
    if ambiguity_class in {"", "none"}:
        if packet_state == "gated_broad_scope":
            ambiguity_class = "low_signal"
        elif packet_state == "gated_ambiguous" and has_non_shared_anchor:
            ambiguity_class = "no_candidates"
    guidance_coverage = str(retrieval_plan.get("guidance_coverage", "")).strip() or (
        "none" if packet_state.startswith("gated_") else ""
    )
    evidence_consensus = str(retrieval_plan.get("evidence_consensus", "")).strip()
    if evidence_consensus in {"", "weak"} and packet_state.startswith("gated_"):
        evidence_consensus = "mixed"
    precision_score = int(retrieval_plan.get("precision_score", 0) or 0)
    if packet_state == "gated_ambiguous" and has_non_shared_anchor and precision_score < 27:
        precision_score = 27
    selected_counts_payload = _decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
    selected_counts_token = _encode_compact_selected_counts(selected_counts_payload)
    retrieval_miss_recovery = (
        dict(retrieval_plan.get("miss_recovery", {}))
        if isinstance(retrieval_plan.get("miss_recovery"), Mapping)
        else {}
    )
    compact_retrieval_plan = {
        key: value
        for key, value in {
            "ambiguity_class": ambiguity_class,
            "guidance_coverage": guidance_coverage,
            "evidence_consensus": evidence_consensus,
            "precision_score": precision_score,
            "selected_counts": selected_counts_token,
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    if any(
        [
            bool(retrieval_miss_recovery.get("active")),
            bool(retrieval_miss_recovery.get("applied")),
            str(retrieval_miss_recovery.get("mode", "")).strip(),
        ]
    ):
        compact_retrieval_plan["miss_recovery"] = {
            key: value
            for key, value in {
                "active": bool(retrieval_miss_recovery.get("active")),
                "applied": bool(retrieval_miss_recovery.get("applied")),
                "mode": str(retrieval_miss_recovery.get("mode", "")).strip(),
            }.items()
            if value not in ("", [], {}, None, False)
        }
    if str(packet_kind or "").strip() == "session_brief":
        compact_retrieval_plan.pop("selected_counts", None)
        if ambiguity_class in {"low_signal", "selection_ambiguous", "no_candidates"}:
            compact_retrieval_plan.pop("guidance_coverage", None)
            compact_retrieval_plan.pop("evidence_consensus", None)
            compact_retrieval_plan.pop("precision_score", None)
    if compact_retrieval_plan:
        compact_context_packet["retrieval_plan"] = compact_retrieval_plan

    packet_quality_payload = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    if packet_state.startswith("gated_"):
        packet_quality_payload.setdefault("context_richness", "narrowing")
        packet_quality_payload.setdefault("reasoning_readiness_level", "none")
        density_level = str(packet_quality_payload.get("context_density_level", "")).strip()
        if packet_state == "gated_broad_scope" and density_level in {"", "none"}:
            packet_quality_payload["context_density_level"] = (
                "none" if str(packet_kind or "").strip() == "session_brief" else "low"
            )
        elif packet_state == "gated_ambiguous" and density_level in {"", "none", "low"}:
            packet_quality_payload["context_density_level"] = (
                "low"
                if str(packet_kind or "").strip() == "session_brief"
                else "medium"
                if has_non_shared_anchor
                else "low"
            )
        if not str(packet_quality_payload.get("accuracy_posture", "")).strip():
            if packet_state == "gated_broad_scope":
                packet_quality_payload["accuracy_posture"] = "broad_guarded"
            elif packet_state == "gated_ambiguous":
                packet_quality_payload["accuracy_posture"] = "fail_closed" if has_non_shared_anchor else "anchored_but_ambiguous"
    compact_packet_quality = packet_quality_codec.compact_packet_quality(packet_quality_payload)
    if compact_packet_quality:
        compact_context_packet["packet_quality"] = compact_packet_quality

    route_payload = (
        dict(context_packet.get("route", {}))
        if isinstance(context_packet.get("route"), Mapping)
        else {}
    )
    route_ready = bool(route_payload.get("route_ready"))
    compact_route = {
        key: value
        for key, value in {
            "route_ready": route_ready,
            "native_spawn_ready": bool(route_payload.get("native_spawn_ready")),
            "narrowing_required": bool(route_payload.get("narrowing_required")) or packet_state.startswith("gated_"),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    parallelism_hint = str(route_payload.get("parallelism_hint", "")).strip()
    if not parallelism_hint and not route_ready and packet_state.startswith("gated_"):
        parallelism_hint = "serial_guarded"
    if parallelism_hint:
        compact_route["p"] = parallelism_hint
    reasoning_bias = str(route_payload.get("reasoning_bias", "")).strip()
    if not reasoning_bias and not route_ready and packet_state.startswith("gated_"):
        reasoning_bias = "guarded_narrowing"
    if reasoning_bias:
        compact_route["b"] = reasoning_bias
    if compact_route:
        compact_context_packet["route"] = compact_route

    execution_profile = tooling_memory_contracts.compact_execution_profile_mapping(
        dict(context_packet.get("execution_profile", {}))
        if isinstance(context_packet.get("execution_profile"), Mapping)
        else {}
    )
    if not execution_profile and packet_state.startswith("gated_"):
        execution_profile = {
            "profile": "main_thread",
            "agent_role": "main_thread",
            "selection_mode": "narrow_first",
            "delegate_preference": "hold_local",
        }
    execution_profile_token = tooling_memory_contracts.encode_execution_profile_token(execution_profile)
    if execution_profile_token and str(packet_kind or "").strip() not in {"session_brief", "bootstrap_session"}:
        compact_context_packet["execution_profile"] = {"token": execution_profile_token}

    optimization_payload = (
        dict(context_packet.get("optimization", {}))
        if isinstance(context_packet.get("optimization"), Mapping)
        else {}
    )
    optimization_miss_recovery = (
        dict(optimization_payload.get("miss_recovery", {}))
        if isinstance(optimization_payload.get("miss_recovery"), Mapping)
        else retrieval_miss_recovery
    )
    compact_optimization = {
        key: value
        for key, value in {
            "within_budget": bool(optimization_payload.get("within_budget", True)),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    if any(
        [
            bool(optimization_miss_recovery.get("active")),
            bool(optimization_miss_recovery.get("applied")),
            str(optimization_miss_recovery.get("mode", "")).strip(),
        ]
    ):
        compact_optimization["miss_recovery"] = {
            key: value
            for key, value in {
                "active": bool(optimization_miss_recovery.get("active")),
                "applied": bool(optimization_miss_recovery.get("applied")),
                "mode": str(optimization_miss_recovery.get("mode", "")).strip(),
            }.items()
            if value not in ("", [], {}, None, False)
        }
    if compact_optimization and str(packet_kind or "").strip() not in {"session_brief", "bootstrap_session"}:
        compact_context_packet["optimization"] = compact_optimization

    full_scan_reason = str(payload.get("full_scan_reason", "")).strip() or str(context_packet.get("full_scan_reason", "")).strip()
    if full_scan_reason:
        compact_context_packet["full_scan_reason"] = full_scan_reason
    if bool(payload.get("full_scan_recommended") or context_packet.get("full_scan_recommended")):
        compact_context_packet["full_scan_recommended"] = True
    selection_state = str(context_packet.get("selection_state", "")).strip()
    if selection_state and not (
        str(packet_kind or "").strip() == "session_brief"
        and selection_state in {"none", "ambiguous"}
    ):
        compact_context_packet["selection_state"] = selection_state
    if str(packet_kind or "").strip() == "session_brief":
        compact_context_packet.pop("packet_kind", None)
    return compact_context_packet, has_non_shared_anchor


def _compact_bootstrap_or_brief_hot_path_delivery(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), Mapping)
        else {}
    )
    anchors = (
        dict(context_packet.get("anchors", {}))
        if isinstance(context_packet.get("anchors"), Mapping)
        else {}
    )
    changed_paths = (
        _normalized_string_list(payload.get("changed_paths"))
        or _normalized_string_list(anchors.get("changed_paths"))
        or _normalized_string_list(anchors.get("explicit_paths"))
    )
    compact_context_packet, has_non_shared_anchor = _compact_bootstrap_or_brief_hot_path_context_packet(
        packet_kind=packet_kind,
        payload=payload,
        changed_paths=changed_paths,
    )
    narrowing_guidance = _compact_hot_path_narrowing_guidance(
        dict(payload.get("narrowing_guidance", {}))
        if isinstance(payload.get("narrowing_guidance"), Mapping)
        else {}
    )
    if str(narrowing_guidance.get("reason", "")).strip() in {
        "selection_ambiguous",
        "The current slice is still too broad to…",
        "Broad shared guidance remains intention…",
    }:
        narrowing_guidance["reason"] = (
            "Need one code path." if has_non_shared_anchor else "Need one code or contract path."
        )
        narrowing_guidance.pop("suggested_inputs", None)
        narrowing_guidance.pop("next_best_anchors", None)

    compact: dict[str, Any] = {}
    if changed_paths:
        compact["changed_paths"] = changed_paths[:4]
    if compact_context_packet:
        compact["context_packet"] = compact_context_packet
    if narrowing_guidance:
        compact["narrowing_guidance"] = narrowing_guidance
    relevant_docs = _normalized_string_list(payload.get("relevant_docs"))
    if relevant_docs:
        compact["relevant_docs"] = relevant_docs[:2]
    recommended_commands = _normalized_string_list(payload.get("recommended_commands"))
    if recommended_commands:
        compact["recommended_commands"] = recommended_commands[:2]
    recommended_tests = [
        {
            key: value
            for key, value in {
                "path": str(row.get("path", "")).strip(),
                "nodeid": str(row.get("nodeid", "")).strip(),
                "reason": str(row.get("reason", "")).strip(),
            }.items()
            if value not in ("", [], {}, None)
        }
        for row in payload.get("recommended_tests", [])
        if isinstance(row, Mapping)
    ]
    if recommended_tests:
        compact["recommended_tests"] = recommended_tests[:2]
    fallback_scan = (
        dict(payload.get("fallback_scan", {}))
        if isinstance(payload.get("fallback_scan"), Mapping)
        else {}
    )
    if fallback_scan:
        compact_fallback = _compact_hot_path_fallback_scan(
            full_scan_reason=str(compact_context_packet.get("full_scan_reason", "")).strip(),
            changed_paths=changed_paths,
            context_packet=compact_context_packet,
            fallback_scan=fallback_scan,
        )
        if compact_fallback:
            compact["fallback_scan"] = compact_fallback
    return compact

def _compact_governance_validation_bundle_for_hot_path(bundle: Mapping[str, Any]) -> dict[str, Any]:
    recommended_commands = _normalized_string_list(bundle.get("recommended_commands"))
    strict_gate_commands = _normalized_string_list(bundle.get("strict_gate_commands"))
    compact = {
        "recommended_command_count": len(recommended_commands),
        "strict_gate_command_count": len(strict_gate_commands),
        "governed_surface_sync_required": bool(bundle.get("governed_surface_sync_required")),
        "plan_binding_required": bool(bundle.get("plan_binding_required")),
    }
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}, None, False)
    }

def _compact_hot_path_surface_reason_token(token: str) -> str:
    normalized = str(token or "").strip()
    if not normalized:
        return ""
    prefix = ""
    if normalized.startswith("fallback:"):
        prefix = "fallback:"
        normalized = normalized.split("fallback:", 1)[1].strip()
    if normalized in {"explicit_workstream_seed", "explicit_component_seed", "force/full-mode", "no-changed-paths"}:
        return f"{prefix}{normalized}" if prefix else normalized
    parts = [part for part in normalized.split("/") if part]
    if len(parts) >= 3 and parts[0] in {"odylith", "src", "docs"}:
        normalized = "/".join(parts[-2:])
    elif len(parts) >= 3:
        normalized = "/".join(parts[-3:])
    elif len(parts) >= 2:
        normalized = "/".join(parts[-2:])
    return f"{prefix}{normalized}" if prefix else normalized

def _compact_governance_obligations_for_hot_path(obligations: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    touched_workstreams = obligations.get("touched_workstreams", [])
    if isinstance(touched_workstreams, list):
        touched_workstream_ids = [
            str(row.get("entity_id", "")).strip()
            for row in touched_workstreams
            if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
        ]
        if touched_workstream_ids:
            compact["touched_workstream_count"] = len(touched_workstream_ids)
            compact["primary_workstream_id"] = touched_workstream_ids[0]
    touched_components = obligations.get("touched_components", [])
    if isinstance(touched_components, list):
        touched_component_ids = [
            str(row.get("entity_id", "")).strip()
            for row in touched_components
            if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
        ]
        if touched_component_ids:
            compact["touched_component_count"] = len(touched_component_ids)
            compact["primary_component_id"] = touched_component_ids[0]
    required_diagrams = obligations.get("required_diagrams", [])
    if isinstance(required_diagrams, list):
        diagram_count = len(
            [
                row
                for row in required_diagrams
                if (
                    isinstance(row, Mapping)
                    and (
                        str(row.get("source_mmd", "")).strip()
                        or str(row.get("path", "")).strip()
                        or str(row.get("diagram_id", "")).strip()
                    )
                )
                or (not isinstance(row, Mapping) and str(row).strip())
            ]
        )
        if diagram_count > 0:
            compact["required_diagram_count"] = diagram_count
    linked_bugs = obligations.get("linked_bugs", [])
    if isinstance(linked_bugs, list):
        linked_bug_count = len(
            [
                row
                for row in linked_bugs
                if isinstance(row, Mapping)
                and (str(row.get("bug_key", "")).strip() or str(row.get("path", "")).strip())
            ]
        )
        if linked_bug_count > 0:
            compact["linked_bug_count"] = linked_bug_count
    closeout_docs = _normalized_string_list(obligations.get("closeout_docs"))
    if closeout_docs:
        compact["closeout_doc_count"] = len(closeout_docs)
    workstream_state_actions = _normalized_string_list(obligations.get("workstream_state_actions"))
    if workstream_state_actions:
        compact["workstream_state_action_count"] = len(workstream_state_actions)
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}, None)
    }

def _compact_governance_surface_refs_for_hot_path(surface_refs: Mapping[str, Any]) -> dict[str, Any]:
    impacted = [
        str(key).strip()
        for key, value in dict(surface_refs.get("impacted_surfaces", {})).items()
        if str(key).strip() and str(key).strip() != "tooling_shell" and bool(value)
    ] if isinstance(surface_refs.get("impacted_surfaces"), Mapping) else []
    grouped_reasons: dict[str, list[str]] = {}
    if isinstance(surface_refs.get("reasons"), Mapping):
        for key, value in dict(surface_refs.get("reasons", {})).items():
            surface = str(key).strip()
            if not surface or surface == "tooling_shell":
                continue
            compacted_reason = next(
                (
                    token
                    for token in [
                        _compact_hot_path_surface_reason_token(token)
                        for token in _normalized_string_list(value)[:1]
                    ]
                    if token
                ),
                "",
            )
            if not compacted_reason:
                continue
            grouped_reasons.setdefault(compacted_reason, []).append(surface)
    compact: dict[str, Any] = {}
    if grouped_reasons:
        compact["reason_group_count"] = len(grouped_reasons)
        compact["reason_tokens"] = [
            reason
            for reason, _surfaces in sorted(
                grouped_reasons.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )[:2]
            if reason
        ]
    grouped_surface_union = sorted(
        _dedupe_strings(
            surface
            for reason, surfaces in grouped_reasons.items()
            if reason
            for surface in surfaces
        )
    )
    effective_surface_count = len(grouped_surface_union) if grouped_surface_union else len(_dedupe_strings(impacted))
    if effective_surface_count > 0:
        compact["surface_count"] = effective_surface_count
    return compact

def _compact_governance_signal_for_hot_path(
    *,
    validation_bundle: Mapping[str, Any],
    governance_obligations: Mapping[str, Any],
    surface_refs: Mapping[str, Any],
) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    compact_validation = _compact_governance_validation_bundle_for_hot_path(validation_bundle)
    compact_obligations = _compact_governance_obligations_for_hot_path(governance_obligations)
    for key in (
        "strict_gate_command_count",
        "plan_binding_required",
        "governed_surface_sync_required",
    ):
        value = compact_validation.get(key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    for key in (
        "primary_workstream_id",
        "primary_component_id",
        "required_diagram_count",
        "linked_bug_count",
        "closeout_doc_count",
    ):
        value = compact_obligations.get(key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    surface_count = max(
        int(surface_refs.get("surface_count", 0) or 0),
        len(_normalized_string_list(surface_refs.get("surfaces"))),
    )
    if surface_count > 0:
        compact["surface_count"] = surface_count
    return governance_signal_codec.compact_governance_signal(compact)

def _embedded_governance_signal(
    payload: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = (
        dict(context_packet)
        if isinstance(context_packet, Mapping)
        else dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), Mapping)
        else {}
    )
    route = dict(packet.get("route", {})) if isinstance(packet.get("route"), Mapping) else {}
    return governance_signal_codec.expand_governance_signal(
        dict(route.get("governance", {})) if isinstance(route.get("governance"), Mapping) else {}
    )

def _hot_path_validation_bundle(
    payload: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(payload.get("validation_bundle"), Mapping):
        return dict(payload.get("validation_bundle", {}))
    if isinstance(context_packet, Mapping) and isinstance(context_packet.get("validation_bundle"), Mapping):
        return dict(context_packet.get("validation_bundle", {}))
    governance = _embedded_governance_signal(payload, context_packet=context_packet)
    compact: dict[str, Any] = {}
    for key in (
        "recommended_command_count",
        "strict_gate_command_count",
        "plan_binding_required",
        "governed_surface_sync_required",
    ):
        value = governance.get(key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact

def _hot_path_governance_obligations(
    payload: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(payload.get("governance_obligations"), Mapping):
        return dict(payload.get("governance_obligations", {}))
    if isinstance(context_packet, Mapping) and isinstance(context_packet.get("governance_obligations"), Mapping):
        return dict(context_packet.get("governance_obligations", {}))
    governance = _embedded_governance_signal(payload, context_packet=context_packet)
    compact: dict[str, Any] = {}
    for key in (
        "touched_workstream_count",
        "primary_workstream_id",
        "touched_component_count",
        "primary_component_id",
        "required_diagram_count",
        "linked_bug_count",
        "closeout_doc_count",
        "workstream_state_action_count",
    ):
        value = governance.get(key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact

def _validation_bundle_command_count(bundle: Mapping[str, Any], *, list_key: str, count_key: str) -> int:
    return max(
        len(_normalized_string_list(bundle.get(list_key))),
        int(bundle.get(count_key, 0) or 0),
    )

def _governance_obligation_count(obligations: Mapping[str, Any], *, list_key: str, count_key: str) -> int:
    value = obligations.get(list_key)
    return max(
        len(value) if isinstance(value, list) else 0,
        int(obligations.get(count_key, 0) or 0),
    )

def _compact_hot_path_runtime_packet(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
    retain_internal_context: bool = False,
) -> dict[str, Any]:
    normalized_packet_kind = str(packet_kind or "").strip()
    if not retain_internal_context and normalized_packet_kind in {"bootstrap_session", "session_brief"}:
        return _compact_bootstrap_or_brief_hot_path_delivery(
            packet_kind=normalized_packet_kind,
            payload=payload,
        )
    packet_state = str(payload.get("context_packet_state", "")).strip()
    compact: dict[str, Any] = {}
    changed_paths = _normalized_string_list(payload.get("changed_paths"))
    explicit_paths = _normalized_string_list(payload.get("explicit_paths"))
    input_context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    input_anchors = (
        dict(input_context_packet.get("anchors", {}))
        if isinstance(input_context_packet.get("anchors"), Mapping)
        else {}
    )
    effective_changed_paths = (
        changed_paths
        or _normalized_string_list(input_anchors.get("changed_paths"))
        or _normalized_string_list(input_anchors.get("explicit_paths"))
        or explicit_paths
    )
    full_scan_recommended = bool(payload.get("full_scan_recommended") or input_context_packet.get("full_scan_recommended"))
    full_scan_reason = str(payload.get("full_scan_reason", "")).strip() or str(input_context_packet.get("full_scan_reason", "")).strip()
    contract_keys = (
        "context_packet",
        "packet_metrics",
    )
    workstream_hint = _payload_workstream_hint(payload, include_selection=False)
    if workstream_hint:
        compact["ws"] = workstream_hint
    if retain_internal_context and isinstance(payload.get("session"), Mapping):
        session_payload = _compact_hot_path_session_payload(dict(payload.get("session", {})))
        if session_payload:
            compact["session"] = session_payload
    narrowing_guidance = dict(payload.get("narrowing_guidance", {})) if isinstance(payload.get("narrowing_guidance"), Mapping) else {}
    if narrowing_guidance and (
        bool(narrowing_guidance.get("required"))
        or full_scan_recommended
        or str(narrowing_guidance.get("reason", "")).strip() not in {"", "grounded"}
    ):
        compact_narrowing_guidance = _compact_hot_path_narrowing_guidance(narrowing_guidance)
        if compact_narrowing_guidance:
            compact["narrowing_guidance"] = compact_narrowing_guidance
    for key in contract_keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            compact[key] = dict(value)
        elif isinstance(value, list):
            compact[key] = [dict(row) if isinstance(row, Mapping) else row for row in value[:4]]
    if str(packet_kind or "").strip() in {"session_brief", "bootstrap_session"}:
        if isinstance(payload.get("session"), Mapping):
            session_payload = _compact_hot_path_session_payload(dict(payload.get("session", {})))
            if session_payload:
                compact["session"] = session_payload
        if isinstance(payload.get("workstream_context"), Mapping):
            compact_workstream_context = _compact_hot_path_workstream_context(
                dict(payload.get("workstream_context", {}))
            )
            if compact_workstream_context:
                compact["workstream_context"] = compact_workstream_context
        if isinstance(payload.get("active_conflicts"), list):
            compact_conflicts = _compact_hot_path_active_conflicts(
                [dict(row) for row in payload.get("active_conflicts", []) if isinstance(row, Mapping)]
            )
            if compact_conflicts:
                compact["active_conflicts"] = compact_conflicts
        active_session_count = int(payload.get("active_session_count", 0) or 0)
        if active_session_count > 0:
            compact["active_session_count"] = active_session_count
        session_seed_paths = _normalized_string_list(payload.get("session_seed_paths"))
        if session_seed_paths:
            compact["session_seed_paths"] = session_seed_paths[:4]
    if str(packet_kind or "").strip() == "governance_slice":
        validation_bundle_payload = (
            dict(payload.get("validation_bundle", {}))
            if isinstance(payload.get("validation_bundle"), Mapping)
            else {}
        )
        governance_obligations_payload = (
            dict(payload.get("governance_obligations", {}))
            if isinstance(payload.get("governance_obligations"), Mapping)
            else {}
        )
        surface_refs_payload = (
            _compact_governance_surface_refs_for_hot_path(dict(payload.get("surface_refs", {})))
            if isinstance(payload.get("surface_refs"), Mapping)
            else {}
        )
        governance_signal = _compact_governance_signal_for_hot_path(
            validation_bundle=validation_bundle_payload,
            governance_obligations=governance_obligations_payload,
            surface_refs=surface_refs_payload,
        )
        if governance_signal and isinstance(compact.get("context_packet"), Mapping):
            context_packet_payload = dict(compact.get("context_packet", {}))
            route_payload = (
                dict(context_packet_payload.get("route", {}))
                if isinstance(context_packet_payload.get("route"), Mapping)
                else {}
            )
            route_payload["governance"] = governance_signal
            context_packet_payload["route"] = route_payload
            compact["context_packet"] = context_packet_payload
        compact_changed_paths = effective_changed_paths
        compact_docs = _normalized_string_list(payload.get("docs"))
        authoritative_governance_docs = bool(payload.get("governance_hot_path_docs_authoritative"))
        governance_hot_path_docs = _normalized_string_list(payload.get("governance_hot_path_docs"))
        if authoritative_governance_docs:
            prioritized_docs = governance_hot_path_docs
        else:
            companion_docs = _companion_context_paths_for_normalized_changed_paths(compact_changed_paths)
            non_anchor_docs = [doc for doc in compact_docs if doc not in compact_changed_paths]
            prioritized_docs = _dedupe_strings(
                [
                    *_governance_diagram_catalog_companions(
                        changed_paths=compact_changed_paths,
                        diagrams=[
                            row
                            for row in payload.get("diagrams", [])
                            if isinstance(payload.get("diagrams"), list) and isinstance(row, Mapping)
                        ],
                    ),
                    *[doc for doc in companion_docs if doc not in compact_changed_paths],
                    *non_anchor_docs,
                    *compact_docs,
                ]
            )
        if prioritized_docs:
            compact["docs"] = prioritized_docs[:4]
        context_packet_payload = (
            dict(compact.get("context_packet", {}))
            if isinstance(compact.get("context_packet"), Mapping)
            else {}
        )
        if compact_changed_paths and not _governance_changed_paths_shadow_redundant(
            changed_paths=compact_changed_paths,
            context_packet_payload=context_packet_payload,
            docs=compact.get("docs", []) if isinstance(compact.get("docs"), list) else [],
        ):
            compact["changed_paths"] = compact_changed_paths[:8]
    elif str(packet_kind or "").strip() == "impact":
        companion_docs = [
            doc
            for doc in _companion_context_paths_for_normalized_changed_paths(effective_changed_paths)
            if doc not in effective_changed_paths
        ]
        if companion_docs:
            benchmark_runner_companions = any(
                path in _BENCHMARK_IMPACT_COMPANION_DOC_EXPANSION_PATHS for path in effective_changed_paths
            )
            if benchmark_runner_companions and _BENCHMARK_RUNNER_REVIEWER_GUIDE not in companion_docs:
                companion_docs = [
                    *companion_docs[:2],
                    _BENCHMARK_RUNNER_REVIEWER_GUIDE,
                    *companion_docs[2:],
                ]
            limit = 3 if benchmark_runner_companions else 2
            compact["docs"] = companion_docs[:limit]
    if retain_internal_context:
        for key in (
            "primary_workstream",
            "components",
            "diagrams",
            "candidate_workstreams",
            "workstream_selection",
            "engineering_notes",
            "docs",
            "code_neighbors",
            "guidance_brief",
            "recommended_commands",
            "recommended_tests",
            "miss_recovery",
        ):
            value = payload.get(key)
            if isinstance(value, Mapping):
                compact[key] = dict(value)
            elif isinstance(value, list):
                compact[key] = [dict(row) if isinstance(row, Mapping) else row for row in value]
    if isinstance(payload.get("routing_handoff"), Mapping):
        routing_handoff_payload = _compact_hot_path_routing_handoff(dict(payload.get("routing_handoff", {})))
        if routing_handoff_payload:
            compact["routing_handoff"] = routing_handoff_payload
    if isinstance(payload.get("architecture_audit"), Mapping):
        compact_architecture_audit = _compact_architecture_audit_for_packet(
            dict(payload.get("architecture_audit", {})),
            packet_state=packet_state,
        )
        suppress_governance_architecture_audit = (
            str(packet_kind or "").strip() == "governance_slice"
            and str(packet_state or "").strip() == "compact"
            and not full_scan_recommended
        )
        if (
            not suppress_governance_architecture_audit
            and _hot_path_keep_architecture_audit(compact_architecture_audit)
        ):
            compact["architecture_audit"] = compact_architecture_audit
    if isinstance(payload.get("benchmark_selector_diagnostics"), Mapping):
        compact["benchmark_selector_diagnostics"] = dict(payload.get("benchmark_selector_diagnostics", {}))
    if retain_internal_context and isinstance(payload.get("auto_escalation"), Mapping):
        compact_auto_escalation = _compact_hot_path_auto_escalation(dict(payload.get("auto_escalation", {})))
        if compact_auto_escalation:
            compact["auto_escalation"] = compact_auto_escalation
    if full_scan_recommended:
        fallback_scan = dict(payload.get("fallback_scan", {})) if isinstance(payload.get("fallback_scan"), Mapping) else {}
        compact["fallback_scan"] = _compact_hot_path_fallback_scan(
            full_scan_reason=full_scan_reason,
            changed_paths=changed_paths,
            context_packet=dict(compact.get("context_packet", {})),
            fallback_scan=fallback_scan,
        )
    source_route = (
        dict(input_context_packet.get("route", {}))
        if isinstance(input_context_packet.get("route"), Mapping)
        else {}
    )
    if (
        not retain_internal_context
        and isinstance(compact.get("context_packet"), Mapping)
        and not isinstance(compact.get("routing_handoff"), Mapping)
        and _source_hot_path_within_budget(payload)
        and (
            str(packet_state or "").strip().startswith("gated_")
            or bool(source_route.get("route_ready"))
        )
    ):
        return _fast_finalize_compact_hot_path_packet(
            compact=compact,
            within_budget=True,
            full_scan_recommended=full_scan_recommended,
        )
    budget_meta = tooling_context_budgeting.packet_budget(
        packet_kind=packet_kind,
        packet_state=packet_state,
    )
    packet_metrics = tooling_context_budgeting.estimate_packet_metrics(
        compact,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    compact_packet_metrics = _compact_hot_path_packet_metrics(packet_metrics)
    if compact_packet_metrics:
        compact["packet_metrics"] = compact_packet_metrics
    else:
        compact.pop("packet_metrics", None)
    within_budget = bool(packet_metrics.get("within_budget"))
    if isinstance(compact.get("context_packet"), Mapping):
        context_packet_payload = dict(compact.get("context_packet", {}))
        if isinstance(context_packet_payload.get("optimization"), Mapping):
            optimization_payload = dict(context_packet_payload.get("optimization", {}))
            optimization_payload["within_budget"] = within_budget
            context_packet_payload["optimization"] = optimization_payload
        if isinstance(context_packet_payload.get("packet_budget"), Mapping):
            packet_budget_payload = dict(context_packet_payload.get("packet_budget", {}))
            packet_budget_payload["within_budget"] = within_budget
            context_packet_payload["packet_budget"] = packet_budget_payload
        compact["context_packet"] = context_packet_payload
    if isinstance(compact.get("context_packet"), Mapping):
        readiness = _hot_path_recomputed_readiness(
            packet_kind=packet_kind,
            packet_state=packet_state,
            compact_payload=compact,
            within_budget=within_budget,
        )
        execution_profile_payload = (
            dict(readiness.get("execution_profile", {}))
            if isinstance(readiness.get("execution_profile"), Mapping)
            else {}
        )
        compact_execution_profile_payload = _compact_hot_path_route_execution_profile(execution_profile_payload)
        if isinstance(compact.get("routing_handoff"), Mapping):
            routing_handoff_payload = dict(compact.get("routing_handoff", {}))
            if compact_execution_profile_payload and (
                bool(readiness.get("route_ready"))
                or str(compact_execution_profile_payload.get("delegate_preference", "")).strip()
                not in {"", "hold_local"}
            ):
                routing_handoff_payload["execution_profile"] = _encode_hot_path_execution_profile(
                    compact_execution_profile_payload
                )
                routing_handoff_payload.pop("odylith_execution_profile", None)
            else:
                routing_handoff_payload.pop("execution_profile", None)
                routing_handoff_payload.pop("odylith_execution_profile", None)
            if routing_handoff_payload:
                compact["routing_handoff"] = routing_handoff_payload
            else:
                compact.pop("routing_handoff", None)
        context_packet_payload = dict(compact.get("context_packet", {}))
        route_payload = (
            dict(context_packet_payload.get("route", {}))
            if isinstance(context_packet_payload.get("route"), Mapping)
            else {}
        )
        route_payload["route_ready"] = bool(readiness.get("route_ready"))
        route_payload["native_spawn_ready"] = bool(readiness.get("native_spawn_ready"))
        context_packet_payload["route"] = route_payload
        if compact_execution_profile_payload and (
            bool(readiness.get("route_ready"))
            or str(compact_execution_profile_payload.get("delegate_preference", "")).strip() not in {"", "hold_local"}
        ):
            context_packet_payload["execution_profile"] = compact_execution_profile_payload
        else:
            context_packet_payload.pop("execution_profile", None)
        compact["context_packet"] = context_packet_payload
    compact = _trim_route_ready_hot_path_prompt_payload(
        compact=compact,
        full_scan_recommended=full_scan_recommended,
    )
    return _drop_redundant_hot_path_routing_handoff(compact)

def _hot_path_payload_is_compact(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload.get("context_packet"), Mapping):
        return False
    return not any(
        key in payload
        for key in (
            "context_packet_state",
            "primary_workstream",
            "components",
            "diagrams",
            "candidate_workstreams",
            "workstream_selection",
            "engineering_notes",
            "docs",
            "code_neighbors",
            "guidance_brief",
            "recommended_commands",
            "recommended_tests",
            "miss_recovery",
            "auto_escalation",
        )
    )

def _update_compact_hot_path_runtime_packet(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
    retain_internal_context: bool = False,
    full_scan_recommended: bool | None = None,
    full_scan_reason: str | None = None,
    fallback_scan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(payload)
    if full_scan_recommended is not None:
        merged["full_scan_recommended"] = bool(full_scan_recommended)
    if full_scan_reason is not None:
        merged["full_scan_reason"] = str(full_scan_reason or "").strip()
    if fallback_scan is not None:
        if fallback_scan:
            merged["fallback_scan"] = dict(fallback_scan)
        else:
            merged.pop("fallback_scan", None)
    if not _hot_path_payload_is_compact(merged):
        return _compact_hot_path_runtime_packet(
            packet_kind=packet_kind,
            payload=merged,
            retain_internal_context=retain_internal_context,
        )

    compact: dict[str, Any] = {
        key: (
            dict(value)
            if isinstance(value, Mapping)
            else [dict(row) if isinstance(row, Mapping) else row for row in value]
            if isinstance(value, list)
            else value
        )
        for key, value in merged.items()
        if key not in {"packet_metrics", "inferred_workstream"}
    }
    workstream_hint = _payload_workstream_hint(merged, include_selection=False)
    if workstream_hint:
        compact["ws"] = workstream_hint
    else:
        compact.pop("ws", None)
    if not retain_internal_context:
        for key in (
            "session",
            "primary_workstream",
            "components",
            "diagrams",
            "candidate_workstreams",
            "workstream_selection",
            "engineering_notes",
            "docs",
            "code_neighbors",
            "guidance_brief",
            "recommended_commands",
            "recommended_tests",
            "miss_recovery",
            "auto_escalation",
        ):
            compact.pop(key, None)

    context_packet_payload = dict(compact.get("context_packet", {}))
    if full_scan_recommended is not None:
        context_packet_payload["full_scan_recommended"] = bool(full_scan_recommended)
    if full_scan_reason is not None:
        if str(full_scan_reason or "").strip():
            context_packet_payload["full_scan_reason"] = str(full_scan_reason or "").strip()
        else:
            context_packet_payload.pop("full_scan_reason", None)
    compact["context_packet"] = context_packet_payload
    effective_full_scan_recommended = bool(
        compact.get("full_scan_recommended") or context_packet_payload.get("full_scan_recommended")
    )
    effective_full_scan_reason = str(compact.get("full_scan_reason", "")).strip() or str(
        context_packet_payload.get("full_scan_reason", "")
    ).strip()
    if effective_full_scan_recommended:
        source_fallback = (
            dict(fallback_scan)
            if isinstance(fallback_scan, Mapping)
            else dict(compact.get("fallback_scan", {}))
            if isinstance(compact.get("fallback_scan"), Mapping)
            else {}
        )
        compact["fallback_scan"] = _compact_hot_path_fallback_scan(
            full_scan_reason=effective_full_scan_reason,
            changed_paths=_normalized_string_list(compact.get("changed_paths")),
            context_packet=context_packet_payload,
            fallback_scan=source_fallback,
        )
    else:
        compact.pop("fallback_scan", None)
    if full_scan_recommended is not None and isinstance(compact.get("narrowing_guidance"), Mapping):
        narrowing_payload = dict(compact.get("narrowing_guidance", {}))
        if bool(full_scan_recommended):
            narrowing_payload["required"] = True
            if str(full_scan_reason or "").strip():
                narrowing_payload["reason"] = str(full_scan_reason or "").strip()
        compact["narrowing_guidance"] = narrowing_payload
    source_context_packet = (
        dict(merged.get("context_packet", {}))
        if isinstance(merged.get("context_packet"), Mapping)
        else {}
    )
    source_route = (
        dict(source_context_packet.get("route", {}))
        if isinstance(source_context_packet.get("route"), Mapping)
        else {}
    )
    if (
        not retain_internal_context
        and isinstance(compact.get("context_packet"), Mapping)
        and not isinstance(compact.get("routing_handoff"), Mapping)
        and _source_hot_path_within_budget(merged)
        and (
            str(context_packet_payload.get("packet_state", "")).strip().startswith("gated_")
            or bool(source_route.get("route_ready"))
        )
    ):
        return _fast_finalize_compact_hot_path_packet(
            compact=compact,
            within_budget=True,
            full_scan_recommended=effective_full_scan_recommended,
        )

    budget_meta = tooling_context_budgeting.packet_budget(
        packet_kind=packet_kind,
        packet_state=str(context_packet_payload.get("packet_state", "")).strip(),
    )
    packet_metrics = tooling_context_budgeting.estimate_packet_metrics(
        compact,
        packet_kind=packet_kind,
        packet_state=str(context_packet_payload.get("packet_state", "")).strip(),
        budget=budget_meta,
    )
    compact_packet_metrics = _compact_hot_path_packet_metrics(packet_metrics)
    if compact_packet_metrics:
        compact["packet_metrics"] = compact_packet_metrics
    else:
        compact.pop("packet_metrics", None)
    within_budget = bool(packet_metrics.get("within_budget"))
    context_packet_payload = dict(compact.get("context_packet", {}))
    if isinstance(context_packet_payload.get("optimization"), Mapping):
        optimization_payload = dict(context_packet_payload.get("optimization", {}))
        optimization_payload["within_budget"] = within_budget
        context_packet_payload["optimization"] = optimization_payload
    if isinstance(context_packet_payload.get("packet_budget"), Mapping):
        packet_budget_payload = dict(context_packet_payload.get("packet_budget", {}))
        packet_budget_payload["within_budget"] = within_budget
        context_packet_payload["packet_budget"] = packet_budget_payload
    compact["context_packet"] = context_packet_payload
    readiness = _hot_path_recomputed_readiness(
        packet_kind=packet_kind,
        packet_state=str(context_packet_payload.get("packet_state", "")).strip(),
        compact_payload=compact,
        within_budget=within_budget,
    )
    execution_profile_payload = (
        dict(readiness.get("execution_profile", {}))
        if isinstance(readiness.get("execution_profile"), Mapping)
        else {}
    )
    compact_execution_profile_payload = _compact_hot_path_route_execution_profile(execution_profile_payload)
    if isinstance(compact.get("routing_handoff"), Mapping):
        routing_handoff_payload = dict(compact.get("routing_handoff", {}))
        if compact_execution_profile_payload and (
            bool(readiness.get("route_ready"))
            or str(compact_execution_profile_payload.get("delegate_preference", "")).strip() not in {"", "hold_local"}
        ):
            routing_handoff_payload["execution_profile"] = _encode_hot_path_execution_profile(
                compact_execution_profile_payload
            )
            routing_handoff_payload.pop("odylith_execution_profile", None)
        else:
            routing_handoff_payload.pop("execution_profile", None)
            routing_handoff_payload.pop("odylith_execution_profile", None)
        if routing_handoff_payload:
            compact["routing_handoff"] = routing_handoff_payload
        else:
            compact.pop("routing_handoff", None)
    route_payload = (
        dict(context_packet_payload.get("route", {}))
        if isinstance(context_packet_payload.get("route"), Mapping)
        else {}
    )
    route_payload["route_ready"] = bool(readiness.get("route_ready"))
    route_payload["native_spawn_ready"] = bool(readiness.get("native_spawn_ready"))
    context_packet_payload["route"] = route_payload
    if compact_execution_profile_payload and (
        bool(readiness.get("route_ready"))
        or str(compact_execution_profile_payload.get("delegate_preference", "")).strip() not in {"", "hold_local"}
    ):
        context_packet_payload["execution_profile"] = compact_execution_profile_payload
    else:
        context_packet_payload.pop("execution_profile", None)
    compact["context_packet"] = context_packet_payload
    return _drop_redundant_hot_path_routing_handoff(
        _trim_route_ready_hot_path_prompt_payload(
        compact=compact,
        full_scan_recommended=effective_full_scan_recommended,
        )
    )

def _trim_route_ready_hot_path_prompt_payload(
    *,
    compact: Mapping[str, Any],
    full_scan_recommended: bool,
) -> dict[str, Any]:
    trimmed: dict[str, Any] = {
        key: (
            dict(value)
            if isinstance(value, Mapping)
            else [dict(row) if isinstance(row, Mapping) else row for row in value]
            if isinstance(value, list)
            else value
        )
        for key, value in compact.items()
    }
    context_packet_payload = (
        dict(trimmed.get("context_packet", {}))
        if isinstance(trimmed.get("context_packet"), Mapping)
        else {}
    )
    routing_handoff_payload = (
        dict(trimmed.get("routing_handoff", {}))
        if isinstance(trimmed.get("routing_handoff"), Mapping)
        else {}
    )
    route_payload = (
        dict(context_packet_payload.get("route", {}))
        if isinstance(context_packet_payload.get("route"), Mapping)
        else {}
    )
    route_ready = bool(
        trimmed.get("route_ready")
        or routing_handoff_payload.get("route_ready")
        or route_payload.get("route_ready")
    )
    if context_packet_payload:
        packet_metrics_payload = (
            dict(trimmed.get("packet_metrics", {}))
            if isinstance(trimmed.get("packet_metrics"), Mapping)
            else {}
        )
        context_packet_payload = _trim_common_hot_path_context_packet(
            context_packet_payload=context_packet_payload,
            within_budget=_compact_hot_path_payload_within_budget(
                payload=trimmed,
                context_packet=context_packet_payload,
                packet_metrics=packet_metrics_payload,
            ),
        )
        trimmed["context_packet"] = context_packet_payload
    current_full_scan_reason = str(trimmed.get("full_scan_reason", "")).strip() or str(
        context_packet_payload.get("full_scan_reason", "")
    ).strip()
    retained_anchor_paths = _dedupe_strings(
        [
            *_normalized_string_list(trimmed.get("changed_paths")),
            *_normalized_string_list(trimmed.get("explicit_paths")),
            *_normalized_string_list(
                dict(context_packet_payload.get("anchors", {})).get("changed_paths")
                if isinstance(context_packet_payload.get("anchors"), Mapping)
                else []
            ),
        ]
    )
    suppress_duplicate_scan_receipt = current_full_scan_reason in {
        "working_tree_scope_degraded",
        "broad_shared_paths",
        "selection_ambiguous",
    } and bool(retained_anchor_paths)
    if suppress_duplicate_scan_receipt:
        trimmed.pop("fallback_scan", None)
        trimmed.pop("full_scan_reason", None)
        retrieval_plan_payload = (
            dict(context_packet_payload.get("retrieval_plan", {}))
            if isinstance(context_packet_payload.get("retrieval_plan"), Mapping)
            else {}
        )
        if retrieval_plan_payload:
            retrieval_plan_payload.pop("full_scan_reason", None)
            context_packet_payload["retrieval_plan"] = retrieval_plan_payload
        if current_full_scan_reason == "selection_ambiguous":
            anchors_payload = (
                dict(context_packet_payload.get("anchors", {}))
                if isinstance(context_packet_payload.get("anchors"), Mapping)
                else {}
            )
            changed_anchor_paths = _normalized_string_list(anchors_payload.get("changed_paths"))
            current_changed_paths = _normalized_string_list(trimmed.get("changed_paths"))
            if current_changed_paths and changed_anchor_paths:
                anchors_payload.pop("changed_paths", None)
                if anchors_payload:
                    context_packet_payload["anchors"] = anchors_payload
                else:
                    context_packet_payload.pop("anchors", None)
        context_packet_payload.pop("full_scan_reason", None)
        trimmed["context_packet"] = context_packet_payload
    if not route_ready or bool(full_scan_recommended):
        return trimmed
    narrowing_payload = (
        dict(trimmed.get("narrowing_guidance", {}))
        if isinstance(trimmed.get("narrowing_guidance"), Mapping)
        else {}
    )
    if narrowing_payload and not bool(narrowing_payload.get("required")):
        trimmed.pop("narrowing_guidance", None)
    if context_packet_payload:
        anchors_payload = (
            dict(context_packet_payload.get("anchors", {}))
            if isinstance(context_packet_payload.get("anchors"), Mapping)
            else {}
        )
        if anchors_payload:
            changed_anchor_paths = _normalized_string_list(anchors_payload.get("changed_paths"))
            explicit_anchor_paths = _normalized_string_list(anchors_payload.get("explicit_paths"))
            if explicit_anchor_paths and explicit_anchor_paths == changed_anchor_paths:
                anchors_payload.pop("explicit_paths", None)
            if not _normalized_string_list(anchors_payload.get("shared_anchor_paths")):
                anchors_payload.pop("shared_anchor_paths", None)
            context_packet_payload["anchors"] = anchors_payload
        retrieval_plan_payload = (
            dict(context_packet_payload.get("retrieval_plan", {}))
            if isinstance(context_packet_payload.get("retrieval_plan"), Mapping)
            else {}
        )
        if retrieval_plan_payload:
            selection_state, _ = _compact_selection_state_parts(
                str(context_packet_payload.get("selection_state", "")).strip()
            )
            if selection_state == "explicit":
                for key in ("guidance_coverage", "evidence_consensus"):
                    retrieval_plan_payload.pop(key, None)
                if str(retrieval_plan_payload.get("ambiguity_class", "")).strip() == "explicit":
                    retrieval_plan_payload.pop("ambiguity_class", None)
            if route_ready:
                retrieval_plan_payload.pop("precision_score", None)
            context_packet_payload["retrieval_plan"] = retrieval_plan_payload
        packet_quality_payload = (
            dict(context_packet_payload.get("packet_quality", {}))
            if isinstance(context_packet_payload.get("packet_quality"), Mapping)
            else {}
        )
        if packet_quality_payload:
            packet_quality_payload.pop("utility_score", None)
            compact_packet_quality = packet_quality_codec.compact_packet_quality(packet_quality_payload)
            if compact_packet_quality:
                context_packet_payload["packet_quality"] = compact_packet_quality
            else:
                context_packet_payload.pop("packet_quality", None)
        route_payload = (
            dict(context_packet_payload.get("route", {}))
            if isinstance(context_packet_payload.get("route"), Mapping)
            else {}
        )
        governance_route = isinstance(route_payload.get("governance"), Mapping)
        if governance_route:
            selection_state, _ = _compact_selection_state_parts(
                str(context_packet_payload.get("selection_state", "")).strip()
            )
            if selection_state in {"explicit", "inferred_confident"}:
                # Route-ready governance packets already retain the primary workstream and
                # component/count signal under route.governance, so the full selection lists
                # are pure prompt overhead at this stage.
                context_packet_payload.pop("selection", None)
            if route_ready:
                context_packet_payload.pop("packet_kind", None)
            anchors_changed_paths = _normalized_string_list(
                dict(context_packet_payload.get("anchors", {})).get("changed_paths", [])
                if isinstance(context_packet_payload.get("anchors"), Mapping)
                else []
            )
            if anchors_changed_paths:
                current_changed_paths = _normalized_string_list(trimmed.get("changed_paths"))
                effective_changed_paths = current_changed_paths or anchors_changed_paths
                compact_changed_paths = path_bundle_codec.compact_path_rows(effective_changed_paths)
                if compact_changed_paths:
                    trimmed["changed_paths"] = compact_changed_paths
                anchors_payload = (
                    dict(context_packet_payload.get("anchors", {}))
                    if isinstance(context_packet_payload.get("anchors"), Mapping)
                    else {}
                )
                anchors_payload.pop("changed_paths", None)
                if anchors_payload:
                    context_packet_payload["anchors"] = anchors_payload
                else:
                    context_packet_payload.pop("anchors", None)
        context_packet_payload.pop("working_memory", None)
        context_packet_payload.pop("execution_profile", None)
        if not bool(context_packet_payload.get("full_scan_recommended")):
            context_packet_payload.pop("full_scan_recommended", None)
        if not str(context_packet_payload.get("full_scan_reason", "")).strip():
            context_packet_payload.pop("full_scan_reason", None)
        trimmed["context_packet"] = context_packet_payload
    context_packet_payload = (
        dict(trimmed.get("context_packet", {}))
        if isinstance(trimmed.get("context_packet"), Mapping)
        else {}
    )
    selection_state, _ = _compact_selection_state_parts(str(context_packet_payload.get("selection_state", "")).strip())
    workstream_hint = _payload_workstream_hint(trimmed, include_selection=False)
    if context_packet_payload and workstream_hint and selection_state in {"explicit", "inferred_confident"}:
        context_packet_payload["selection_state"] = _encode_compact_selection_state(
            state=selection_state,
            workstream=workstream_hint,
        )
        if (
            route_ready
            and str(context_packet_payload.get("packet_kind", "")).strip() == "impact"
            and not isinstance(dict(context_packet_payload.get("route", {})).get("governance"), Mapping)
        ):
            context_packet_payload.pop("packet_kind", None)
        trimmed["context_packet"] = context_packet_payload
        trimmed.pop("ws", None)
    routing_handoff_payload = (
        dict(trimmed.get("routing_handoff", {}))
        if isinstance(trimmed.get("routing_handoff"), Mapping)
        else {}
    )
    if routing_handoff_payload:
        compact_profile = _decode_hot_path_execution_profile(
            routing_handoff_payload.get("execution_profile") or routing_handoff_payload.get("odylith_execution_profile")
        )
        if compact_profile:
            trimmed["routing_handoff"] = {"execution_profile": _encode_hot_path_execution_profile(compact_profile)}
        else:
            trimmed.pop("routing_handoff", None)
    trimmed.pop("session_seed_paths", None)
    workstream_context = (
        dict(trimmed.get("workstream_context", {}))
        if isinstance(trimmed.get("workstream_context"), Mapping)
        else {}
    )
    if workstream_context and not bool(workstream_context.get("resolved")):
        if not any(
            [
                bool(workstream_context.get("lookup")),
                bool(workstream_context.get("candidate_matches")),
                bool(workstream_context.get("full_scan_recommended")),
                str(workstream_context.get("full_scan_reason", "")).strip(),
                bool(workstream_context.get("fallback_scan")),
            ]
        ):
            trimmed.pop("workstream_context", None)
    return trimmed

def _compact_workstream_metadata_for_packet(metadata: Mapping[str, Any]) -> dict[str, Any]:
    keep = ("priority", "ordering_score", "date", "promoted_to_plan")
    return {
        field: str(metadata.get(field, "")).strip()
        for field in keep
        if str(metadata.get(field, "")).strip()
    }

def _compact_workstream_evidence_for_packet(evidence: Mapping[str, Any]) -> dict[str, Any]:
    keep_scalar = (
        "score",
        "strong_signal_count",
        "weak_signal_count",
        "broad_shared_signal_count",
        "non_shared_signal_count",
        "broad_only",
        "overshadowed_by_child",
        "lineage_successor_bonus",
        "lineage_predecessor_downgraded",
        "summary",
    )
    compact: dict[str, Any] = {
        field: evidence.get(field)
        for field in keep_scalar
        if evidence.get(field) not in (None, "", [], {})
    }
    if isinstance(evidence.get("path_signal_counts"), Mapping):
        compact["path_signal_counts"] = dict(evidence.get("path_signal_counts", {}))
    if isinstance(evidence.get("counters"), Mapping):
        compact["counters"] = dict(evidence.get("counters", {}))
    compact["matched_paths"] = [str(token).strip() for token in evidence.get("matched_paths", [])[:4] if str(token).strip()] if isinstance(evidence.get("matched_paths"), list) else []
    compact["matched_components"] = [str(token).strip() for token in evidence.get("matched_components", [])[:3] if str(token).strip()] if isinstance(evidence.get("matched_components"), list) else []
    compact["matched_diagrams"] = [str(token).strip() for token in evidence.get("matched_diagrams", [])[:3] if str(token).strip()] if isinstance(evidence.get("matched_diagrams"), list) else []
    return compact

def _compact_workstream_row_for_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        "entity_id": str(row.get("entity_id", "")).strip(),
        "title": str(row.get("title", "")).strip(),
        "status": str(row.get("status", "")).strip(),
        "rank": int(row.get("rank", 0) or 0),
    }
    metadata = row.get("metadata", {})
    if isinstance(metadata, Mapping):
        compact["metadata"] = _compact_workstream_metadata_for_packet(metadata)
    evidence = row.get("evidence", {})
    if isinstance(evidence, Mapping):
        compact["evidence"] = _compact_workstream_evidence_for_packet(evidence)
    return compact

def _compact_workstream_reference_for_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "entity_id": str(row.get("entity_id", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "status": str(row.get("status", "")).strip(),
            "rank": int(row.get("rank", 0) or 0),
        }.items()
        if value not in ("", [], {}, None)
    }

def _compact_workstream_selection_for_packet(selection: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        "state": str(selection.get("state", "")).strip(),
        "reason": str(selection.get("reason", "")).strip(),
        "why_selected": str(selection.get("why_selected", selection.get("reason", ""))).strip(),
        "score_gap": selection.get("score_gap"),
        "confidence": str(selection.get("confidence", "")).strip(),
        "candidate_count": int(selection.get("candidate_count", 0) or 0),
        "strong_candidate_count": int(selection.get("strong_candidate_count", 0) or 0),
        "ambiguity_class": str(selection.get("ambiguity_class", "")).strip(),
    }
    selected = selection.get("selected_workstream")
    compact["selected_workstream"] = (
        _compact_workstream_row_for_packet(selected)
        if isinstance(selected, Mapping) and str(selected.get("entity_id", "")).strip()
        else {}
    )
    top_candidate = selection.get("top_candidate")
    top_candidate_id = str(top_candidate.get("entity_id", "")).strip() if isinstance(top_candidate, Mapping) else ""
    compact["top_candidate"] = (
        _compact_workstream_row_for_packet(top_candidate)
        if isinstance(top_candidate, Mapping) and top_candidate_id
        else {}
    )
    selected_id = (
        str(selected.get("entity_id", "")).strip()
        if isinstance(selected, Mapping)
        else ""
    )
    compact["competing_candidates"] = [
        _compact_workstream_row_for_packet(row)
        for row in selection.get("competing_candidates", [])
        if isinstance(row, Mapping)
        and str(row.get("entity_id", "")).strip()
        and str(row.get("entity_id", "")).strip() not in {selected_id, top_candidate_id}
    ][:2] if isinstance(selection.get("competing_candidates"), list) else []
    return compact

def _compact_bootstrap_workstream_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        "state": str(selection.get("state", "")).strip(),
        "reason": str(selection.get("reason", "")).strip(),
        "why_selected": str(selection.get("why_selected", selection.get("reason", ""))).strip(),
        "confidence": str(selection.get("confidence", "")).strip(),
        "candidate_count": int(selection.get("candidate_count", 0) or 0),
        "strong_candidate_count": int(selection.get("strong_candidate_count", 0) or 0),
        "ambiguity_class": str(selection.get("ambiguity_class", "")).strip(),
    }
    selected = selection.get("selected_workstream")
    if isinstance(selected, Mapping) and str(selected.get("entity_id", "")).strip():
        compact["selected_workstream"] = _compact_workstream_reference_for_packet(selected)
    top_candidate = selection.get("top_candidate")
    if isinstance(top_candidate, Mapping) and str(top_candidate.get("entity_id", "")).strip():
        compact["top_candidate"] = _compact_workstream_reference_for_packet(top_candidate)
    compact["competing_candidates"] = [
        _compact_workstream_reference_for_packet(row)
        for row in selection.get("competing_candidates", [])
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    ][:1] if isinstance(selection.get("competing_candidates"), list) else []
    return compact

def _compact_neighbor_row_for_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    keep = ("path", "kind", "reason", "title", "entity_id")
    return {
        field: row.get(field)
        for field in keep
        if row.get(field) not in (None, "", [], {})
    }

def _prioritized_neighbor_rows(bucket_name: str, bucket: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [_compact_neighbor_row_for_packet(row) for row in bucket if isinstance(row, Mapping)]
    if bucket_name == "documented_by":
        rows.sort(
            key=lambda row: (
                0 if is_component_spec_path(str(row.get("path", "")), repo_root=Path.cwd()) else 1,
                str(row.get("path", "")),
            )
        )
    elif bucket_name == "covered_by_runbooks":
        rows.sort(
            key=lambda row: (
                0 if str(row.get("path", "")).startswith("docs/runbooks/") else 1,
                str(row.get("path", "")),
            )
        )
    return rows
