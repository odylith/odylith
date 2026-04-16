from __future__ import annotations

from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import packet_quality_codec


def bind(host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in ('Any', 'Mapping', 'Path', 'Sequence', '_CODEX_HOT_PATH_PROFILE', '_HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES', '_HOT_PATH_AUTO_ESCALATION_WRITE_FAMILIES', '_HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES', '_broad_shared_only_input', '_compact_bootstrap_workstream_selection', '_compact_budget_meta_for_summary', '_compact_code_neighbors_for_packet', '_compact_component_row_for_packet', '_compact_diagram_row_for_packet', '_compact_engineering_notes', '_compact_hot_path_payload_within_budget', '_compact_miss_recovery_for_packet', '_compact_packet_metrics_for_summary', '_compact_test_row_for_packet', '_compact_truncation_for_summary', '_compact_workstream_reference_for_packet', '_decode_compact_selected_counts', '_dedupe_strings', '_delivery_profile_hot_path', '_full_scan_guidance', '_hot_path_dashboard_surface_like', '_hot_path_full_scan_recommended', '_hot_path_routing_confidence_rank', '_hot_path_selected_validation_count', '_hot_path_workstream_selection', '_is_governance_sync_command', '_normalize_family_hint', '_normalized_string_list', '_prioritized_neighbor_rows', '_workstream_status_rank', 'display_command', 'json', 'time'):
        try:
            globals()[name] = getter(name)
        except (AttributeError, KeyError):
            continue


def _impact_summary_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    engineering_notes = payload.get("engineering_notes", {})
    code_neighbors = payload.get("code_neighbors", {})
    summary_payload = {
        "resolved": bool(payload.get("resolved")),
        "changed_paths": list(payload.get("changed_paths", [])) if isinstance(payload.get("changed_paths"), list) else [],
        "context_packet_state": str(payload.get("context_packet_state", "")).strip(),
        "full_scan_recommended": bool(payload.get("full_scan_recommended")),
        "full_scan_reason": str(payload.get("full_scan_reason", "")).strip(),
        "truncation": _compact_truncation_for_summary(payload.get("truncation", {}))
        if isinstance(payload.get("truncation"), Mapping)
        else {},
        "primary_workstream": _compact_workstream_reference_for_packet(payload.get("primary_workstream", {}))
        if isinstance(payload.get("primary_workstream"), Mapping)
        else {},
        "workstream_selection": _compact_bootstrap_workstream_selection(payload.get("workstream_selection", {}))
        if isinstance(payload.get("workstream_selection"), Mapping)
        else {},
        "components": [_compact_component_row_for_packet(row) for row in payload.get("components", []) if isinstance(row, Mapping)]
        if isinstance(payload.get("components"), list)
        else [],
        "diagrams": [_compact_diagram_row_for_packet(row) for row in payload.get("diagrams", []) if isinstance(row, Mapping)]
        if isinstance(payload.get("diagrams"), list)
        else [],
        "docs": [str(token).strip() for token in payload.get("docs", []) if str(token).strip()]
        if isinstance(payload.get("docs"), list)
        else [],
        "recommended_commands": [str(token).strip() for token in payload.get("recommended_commands", []) if str(token).strip()]
        if isinstance(payload.get("recommended_commands"), list)
        else [],
        "recommended_tests": [_compact_test_row_for_packet(row) for row in payload.get("recommended_tests", []) if isinstance(row, Mapping)]
        if isinstance(payload.get("recommended_tests"), list)
        else [],
        "guidance_brief": [dict(row) for row in payload.get("guidance_brief", []) if isinstance(row, Mapping)]
        if isinstance(payload.get("guidance_brief"), list)
        else [],
        "miss_recovery": _compact_miss_recovery_for_packet(payload.get("miss_recovery", {}))
        if isinstance(payload.get("miss_recovery"), Mapping)
        else {},
        "engineering_notes": _compact_engineering_notes(
            engineering_notes if isinstance(engineering_notes, Mapping) else {},
            total_limit=4,
            per_kind_limit=1,
        )[0],
        "packet_budget": _compact_budget_meta_for_summary(payload.get("packet_budget", {}))
        if isinstance(payload.get("packet_budget"), Mapping)
        else {},
        "packet_metrics": _compact_packet_metrics_for_summary(payload.get("packet_metrics", {}))
        if isinstance(payload.get("packet_metrics"), Mapping)
        else {},
    }
    compact_neighbors = _compact_code_neighbors_for_packet(
        code_neighbors if isinstance(code_neighbors, Mapping) else {},
        summary_only=True,
    )
    if compact_neighbors:
        summary_payload["code_neighbors"] = compact_neighbors
    return summary_payload

def _delivery_profile_hot_path(delivery_profile: str) -> bool:
    return agent_runtime_contract.is_agent_hot_path_profile(delivery_profile)

def _elapsed_stage_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000.0, 3)

def _compact_stage_timings(stage_timings: Mapping[str, Any]) -> dict[str, float]:
    compact: dict[str, float] = {}
    for key, value in stage_timings.items():
        token = str(key).strip()
        if not token:
            continue
        try:
            duration = round(float(value or 0.0), 3)
        except (TypeError, ValueError):
            continue
        if duration < 0.0:
            continue
        compact[token] = duration
    return compact

def _normalize_family_hint(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    architecture_aliases = {
        "auth",
        "auth_boundary",
        "control_plane",
        "identity_boundary",
        "platform_topology",
        "service_account_boundary",
        "tenant_boundary",
        "topology",
    }
    if normalized in architecture_aliases:
        return "architecture"
    return normalized

def _impact_family_profile(
    *,
    hot_path: bool,
    family_hint: str,
    workstream_hint: str = "",
    component_hint: str = "",
) -> dict[str, Any]:
    if not hot_path:
        return {
            "family": "",
            "prefer_explicit_workstream": False,
            "prefer_explicit_component": False,
            "allow_miss_recovery": True,
            "include_notes": True,
            "include_bugs": True,
            "include_code_neighbors": True,
            "include_components": True,
            "include_diagrams": True,
            "include_tests": True,
            "include_workstreams": True,
        }
    family = _normalize_family_hint(family_hint)
    prefer_explicit_workstream = bool(str(workstream_hint or "").strip()) and family != "architecture"
    prefer_explicit_component = bool(str(component_hint or "").strip()) and family in {
        "component_governance",
        "execution_engine",
        "live_proof_discipline",
        "release_publication",
    }
    governance_runtime_first_families = {
        "agent_activation",
        "component_governance",
        "cross_surface_governance_sync",
        "daemon_security",
        "execution_engine",
        "governed_surface_sync",
        "install_upgrade_runtime",
        "live_proof_discipline",
    }
    fail_closed_support_families = {
        "component_governance",
        "compass_brief_freshness",
        "consumer_profile_compatibility",
        "cross_file_feature",
        "daemon_security",
        "exact_anchor_recall",
        "execution_engine",
        "explicit_workstream",
        "live_proof_discipline",
        "orchestration_feedback",
        "orchestration_intelligence",
    }
    note_light_families = {
        "broad_shared_scope",
        "compass_brief_freshness",
        "consumer_profile_compatibility",
        "cross_file_feature",
        "exact_anchor_recall",
        "docs_code_closeout",
        "execution_engine",
        "orchestration_feedback",
        "orchestration_intelligence",
        "retrieval_miss_recovery",
        "explicit_workstream",
        "governed_surface_sync",
        "live_proof_discipline",
        "release_publication",
        *governance_runtime_first_families,
    }
    bug_light_families = {
        "broad_shared_scope",
        "compass_brief_freshness",
        "consumer_profile_compatibility",
        "cross_file_feature",
        "exact_anchor_recall",
        "docs_code_closeout",
        "execution_engine",
        "orchestration_feedback",
        "orchestration_intelligence",
        "retrieval_miss_recovery",
        "explicit_workstream",
        "governed_surface_sync",
        "live_proof_discipline",
        "release_publication",
        *governance_runtime_first_families,
    }
    code_neighbor_light_families = {
        "broad_shared_scope",
        "compass_brief_freshness",
        "consumer_profile_compatibility",
        "cross_file_feature",
        "exact_anchor_recall",
        "governed_surface_sync",
        "execution_engine",
        "live_proof_discipline",
        "orchestration_feedback",
        "orchestration_intelligence",
        "retrieval_miss_recovery",
        "release_publication",
        *governance_runtime_first_families,
    }
    component_light_families = {
        "broad_shared_scope",
        "exact_path_ambiguity",
        "execution_engine",
        "explicit_workstream",
        "install_upgrade_runtime",
        "live_proof_discipline",
        "daemon_security",
        "agent_activation",
        "cross_surface_governance_sync",
        "release_publication",
        "retrieval_miss_recovery",
    }
    diagram_light_families = {
        "broad_shared_scope",
        "compass_brief_freshness",
        "component_governance",
        "consumer_profile_compatibility",
        "cross_file_feature",
        "cross_surface_governance_sync",
        "daemon_security",
        "execution_engine",
        "exact_anchor_recall",
        "exact_path_ambiguity",
        "explicit_workstream",
        "install_upgrade_runtime",
        "agent_activation",
        "live_proof_discipline",
        "orchestration_feedback",
        "orchestration_intelligence",
        "retrieval_miss_recovery",
        "release_publication",
    }
    test_light_families = {
        "agent_activation",
        "component_governance",
        "compass_brief_freshness",
        "consumer_profile_compatibility",
        "cross_file_feature",
        "cross_surface_governance_sync",
        "daemon_security",
        "docs_code_closeout",
        "exact_anchor_recall",
        "explicit_workstream",
        "governed_surface_sync",
        "install_upgrade_runtime",
        "live_proof_discipline",
        "orchestration_feedback",
        "orchestration_intelligence",
        "release_publication",
    }
    workstream_light_families = {
        "broad_shared_scope",
        "cross_file_feature",
        "dashboard_surface",
        "exact_anchor_recall",
        "orchestration_feedback",
        "orchestration_intelligence",
        "retrieval_miss_recovery",
    }
    return {
        "family": family,
        "prefer_explicit_workstream": prefer_explicit_workstream,
        "prefer_explicit_component": prefer_explicit_component,
        "allow_miss_recovery": family not in {"governed_surface_sync", *fail_closed_support_families},
        "include_notes": family not in note_light_families,
        "include_bugs": family not in bug_light_families,
        "include_code_neighbors": family not in code_neighbor_light_families,
        "include_components": prefer_explicit_component or family not in component_light_families,
        "include_diagrams": family not in diagram_light_families,
        "include_tests": family not in test_light_families,
        "include_workstreams": family not in workstream_light_families,
    }

def _hot_path_dashboard_surface_like(
    *,
    family_hint: str,
    payload: Mapping[str, Any],
) -> bool:
    family = _normalize_family_hint(family_hint)
    if family == "dashboard_surface":
        return True
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    changed_paths = (
        _normalized_string_list(payload.get("changed_paths"))
        or _normalized_string_list(anchors.get("changed_paths"))
        or _normalized_string_list(anchors.get("explicit_paths"))
    )
    if not changed_paths or _broad_shared_only_input(changed_paths):
        return False
    governed_dashboard_paths = {
        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
        "src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py",
        "src/odylith/runtime/surfaces/render_registry_dashboard.py",
        "src/odylith/runtime/surfaces/compass_dashboard_shell.py",
        "src/odylith/runtime/surfaces/render_backlog_ui.py",
        "src/odylith/runtime/surfaces/render_compass_dashboard.py",
        "src/odylith/runtime/surfaces/render_casebook_dashboard.py",
        "src/odylith/runtime/surfaces/render_mermaid_catalog.py",
        "odylith/index.html",
        "odylith/radar/radar.html",
        "odylith/atlas/atlas.html",
        "odylith/compass/compass.html",
        "odylith/registry/registry.html",
        "odylith/casebook/casebook.html",
    }
    script_or_tool_only = all(
        path.startswith(("src/odylith/runtime/surfaces/", "odylith/"))
        for path in changed_paths
    )
    dashboard_named = any("dashboard" in Path(path).name.lower() for path in changed_paths)
    governed_dashboard_hit = any(path in governed_dashboard_paths for path in changed_paths)
    return script_or_tool_only and (dashboard_named or governed_dashboard_hit)

def _hot_path_routing_confidence_rank(value: str) -> int:
    token = str(value or "").strip().lower()
    if token in {"high", "strong"}:
        return 4
    if token in {"medium", "moderate", "grounded"}:
        return 3
    if token in {"guarded", "low"}:
        return 2
    if token:
        return 1
    return 0

def _hot_path_packet_rank(payload: Mapping[str, Any]) -> tuple[int, int, int, int, int, int]:
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    precision_score = max(0, min(100, int(retrieval_plan.get("precision_score", 0) or 0)))
    return (
        0 if bool(payload.get("full_scan_recommended")) else 1,
        1 if bool(payload.get("route_ready")) else 0,
        1 if bool(payload.get("native_spawn_ready")) else 0,
        _hot_path_routing_confidence_rank(str(payload.get("routing_confidence", "")).strip()),
        1
        if _compact_hot_path_payload_within_budget(
            payload=payload,
            context_packet=dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {},
            packet_metrics=dict(payload.get("packet_metrics", {}))
            if isinstance(payload.get("packet_metrics"), Mapping)
            else {},
        )
        else 0,
        precision_score,
    )

def _hot_path_auto_escalation_trigger(
    *,
    packet_kind: str,
    family_hint: str,
    payload: Mapping[str, Any],
) -> str:
    family = _normalize_family_hint(family_hint)
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    full_scan_recommended = bool(payload.get("full_scan_recommended") or context_packet.get("full_scan_recommended"))
    if full_scan_recommended:
        return "full_scan_recommended"
    if family in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES or _hot_path_dashboard_surface_like(
        family_hint=family_hint,
        payload=payload,
    ):
        return ""
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    packet_quality = (
        packet_quality_codec.expand_packet_quality(
            dict(context_packet.get("packet_quality", {}))
            if isinstance(context_packet.get("packet_quality"), Mapping)
            else {}
        )
    )
    selected_counts = _decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
    validation_count = max(0, int(selected_counts.get("tests", 0) or 0)) + max(
        0, int(selected_counts.get("commands", 0) or 0)
    )
    if not bool(payload.get("route_ready")) and family in _HOT_PATH_AUTO_ESCALATION_WRITE_FAMILIES:
        return "route_not_ready"
    if _hot_path_routing_confidence_rank(str(payload.get("routing_confidence", "")).strip()) <= 2:
        return "routing_confidence_thin"
    if (
        validation_count > 0
        and not bool(payload.get("route_ready"))
        and str(packet_quality.get("intent_family", "")).strip() in {"implementation", "write", "validation", "ui_layout", "surface_copy", "surface_binding"}
    ):
        return "validation_grounding_thin"
    if (
        str(packet_kind or "").strip() in {"impact", "session_brief"}
        and bool(route.get("narrowing_required"))
        and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
    ):
        return "narrowing_required"
    return ""

def _hot_path_can_hold_local_narrowing_without_full_scan(
    *,
    family_hint: str,
    payload: Mapping[str, Any],
) -> bool:
    if not _hot_path_dashboard_surface_like(family_hint=family_hint, payload=payload):
        return False
    if _hot_path_full_scan_recommended(payload):
        return False
    packet_metrics = dict(payload.get("packet_metrics", {})) if isinstance(payload.get("packet_metrics"), Mapping) else {}
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    if not _compact_hot_path_payload_within_budget(
        payload=payload,
        context_packet=context_packet,
        packet_metrics=packet_metrics,
    ):
        return False
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    changed_paths = (
        _normalized_string_list(payload.get("changed_paths"))
        or _normalized_string_list(anchors.get("changed_paths"))
        or _normalized_string_list(anchors.get("explicit_paths"))
    )
    return bool(
        changed_paths
        and not _broad_shared_only_input(changed_paths)
        and bool(route.get("narrowing_required"))
        and not bool(route.get("route_ready"))
    )

def _compact_hot_path_auto_escalation(summary: Mapping[str, Any]) -> dict[str, Any]:
    final_stage = str(summary.get("final_stage", "")).strip() or str(summary.get("stage", "")).strip()
    if final_stage in {"", "compact_success", "bootstrap_direct"}:
        return {}
    compact = {
        "stage": final_stage,
        "auto_escalated": bool(summary.get("auto_escalated") or summary.get("applied") or final_stage != "compact_success"),
    }
    final_source = str(summary.get("final_source", "")).strip()
    if final_source and final_source != str(summary.get("initial_source", "")).strip():
        compact["final_source"] = final_source
    reasons = _normalized_string_list(summary.get("reasons"))
    if reasons:
        compact["reason"] = reasons[0]
    return compact

def _hot_path_selected_validation_count(payload: Mapping[str, Any]) -> int:
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    selected_counts = _decode_compact_selected_counts(retrieval_plan.get("selected_counts"))
    return max(0, int(selected_counts.get("tests", 0) or 0)) + max(
        0,
        int(selected_counts.get("commands", 0) or 0),
    )

def _hot_path_route_ready(payload: Mapping[str, Any]) -> bool:
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    routing_handoff = dict(payload.get("routing_handoff", {})) if isinstance(payload.get("routing_handoff"), Mapping) else {}
    return bool(payload.get("route_ready") or route.get("route_ready") or routing_handoff.get("route_ready"))

def _hot_path_full_scan_recommended(payload: Mapping[str, Any]) -> bool:
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    return bool(payload.get("full_scan_recommended") or context_packet.get("full_scan_recommended"))

def _hot_path_full_scan_reason(payload: Mapping[str, Any]) -> str:
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    return str(payload.get("full_scan_reason", "")).strip() or str(context_packet.get("full_scan_reason", "")).strip()

def _hot_path_routing_confidence(payload: Mapping[str, Any]) -> str:
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    packet_quality = (
        packet_quality_codec.expand_packet_quality(
            dict(context_packet.get("packet_quality", {}))
            if isinstance(context_packet.get("packet_quality"), Mapping)
            else {}
        )
    )
    routing_handoff = dict(payload.get("routing_handoff", {})) if isinstance(payload.get("routing_handoff"), Mapping) else {}
    return (
        str(payload.get("routing_confidence", "")).strip()
        or str(routing_handoff.get("routing_confidence", "")).strip()
        or str(packet_quality.get("routing_confidence", "")).strip()
    )

def _should_escalate_hot_path_to_session_brief(
    *,
    payload: Mapping[str, Any],
    family_hint: str,
    workstream_hint: str,
    validation_command_hints: Sequence[str],
) -> tuple[bool, list[str]]:
    family = _normalize_family_hint(family_hint)
    if family in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES:
        return False, []
    if _hot_path_dashboard_surface_like(family_hint=family_hint, payload=payload):
        return False, []
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    packet_quality = (
        packet_quality_codec.expand_packet_quality(
            dict(context_packet.get("packet_quality", {}))
            if isinstance(context_packet.get("packet_quality"), Mapping)
            else {}
        )
    )
    selection_state = str(_hot_path_workstream_selection(payload).get("state", "")).strip()
    routing_confidence = (
        str(payload.get("routing_confidence", "")).strip()
        or str(packet_quality.get("routing_confidence", "")).strip()
    )
    route_ready = bool(payload.get("route_ready") or route.get("route_ready"))
    narrowing_required = bool(payload.get("narrowing_required") or route.get("narrowing_required"))
    full_scan_recommended = bool(payload.get("full_scan_recommended") or context_packet.get("full_scan_recommended"))
    validation_count = _hot_path_selected_validation_count(payload)
    reasons: list[str] = []
    if family == "explicit_workstream" and str(workstream_hint or "").strip() and selection_state != "explicit":
        reasons.append("explicit_workstream_not_grounded")
    if selection_state in {"ambiguous", "none"}:
        reasons.append(f"selection_{selection_state}")
    if routing_confidence in {"", "low"}:
        reasons.append("routing_confidence_low")
    if not route_ready:
        reasons.append("route_not_ready")
    if narrowing_required:
        reasons.append("narrowing_required")
    if validation_command_hints and validation_count <= 0:
        reasons.append("validation_grounding_missing")
    if full_scan_recommended and str(payload.get("full_scan_reason", "")).strip() in {
        "selection_ambiguous",
        "selection_none",
        "working_tree_scope_degraded",
    }:
        reasons.append(str(payload.get("full_scan_reason", "")).strip())
    if not reasons:
        return False, []
    if family in _HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES:
        return True, reasons
    if bool(str(workstream_hint or "").strip()) and selection_state != "explicit":
        return True, reasons
    if validation_command_hints and (not route_ready or validation_count <= 0):
        return True, reasons
    return False, []

def _fallback_scan_payload(
    *,
    repo_root: Path,
    reason: str,
    changed_paths: Sequence[str],
    query: str = "",
    perform_scan: bool = False,
    result_limit: int = 12,
    delivery_profile: str = "full",
) -> dict[str, Any]:
    normalized_reason = str(reason or "").strip()
    normalized_paths = [str(token).strip() for token in changed_paths if str(token).strip()]
    if not normalized_reason:
        return {}
    if _delivery_profile_hot_path(delivery_profile) and not perform_scan:
        return {
            "recommended": True,
            "summary_only": True,
            "reason": normalized_reason,
            "changed_paths": normalized_paths[:6],
            "query": str(query or "").strip(),
        }
    return _full_scan_guidance(
        repo_root=repo_root,
        reason=normalized_reason,
        query=str(query or "").strip(),
        changed_paths=normalized_paths,
        perform_scan=perform_scan,
        result_limit=result_limit,
    )

def _compact_hot_path_session_payload(session_payload: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "session_id": str(session_payload.get("session_id", "")).strip(),
            "workstream": str(session_payload.get("workstream", "")).strip(),
            "claim_mode": str(session_payload.get("claim_mode", "")).strip(),
            "working_tree_scope": str(session_payload.get("working_tree_scope", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    claimed_paths = _normalized_string_list(session_payload.get("claimed_paths"))
    if claimed_paths:
        compact["claimed_paths"] = claimed_paths[:4]
    return compact

def _compact_hot_path_workstream_context(context: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(context, Mapping) or not context:
        return {}
    resolved = bool(context.get("resolved"))
    if not resolved:
        lookup = dict(context.get("lookup", {})) if isinstance(context.get("lookup"), Mapping) else {}
        candidate_matches = (
            [dict(row) for row in context.get("candidate_matches", [])[:2] if isinstance(row, Mapping)]
            if isinstance(context.get("candidate_matches"), list)
            else []
        )
        full_scan_recommended = bool(context.get("full_scan_recommended"))
        full_scan_reason = str(context.get("full_scan_reason", "")).strip()
        fallback_scan = dict(context.get("fallback_scan", {})) if isinstance(context.get("fallback_scan"), Mapping) else {}
        if not lookup and not candidate_matches and not full_scan_recommended and not full_scan_reason and not fallback_scan:
            return {}
        return {
            key: value
            for key, value in {
                "resolved": False,
                "lookup": lookup,
                "candidate_matches": candidate_matches,
                "full_scan_recommended": full_scan_recommended,
                "full_scan_reason": full_scan_reason,
                "fallback_scan": fallback_scan,
            }.items()
            if value not in ("", [], {}, None, False)
        }
    entity = dict(context.get("entity", {})) if isinstance(context.get("entity"), Mapping) else {}
    compact_entity = {
        key: value
        for key, value in {
            "entity_id": str(entity.get("entity_id", "")).strip(),
            "title": str(entity.get("title", "")).strip(),
            "status": str(entity.get("status", "")).strip(),
            "plan_ref": str(entity.get("plan_ref", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    return {
        key: value
        for key, value in {
            "resolved": True,
            "entity": compact_entity,
            "relation_count": int(context.get("relation_count", 0) or 0),
            "full_scan_recommended": bool(context.get("full_scan_recommended")),
            "full_scan_reason": str(context.get("full_scan_reason", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, 0, False)
    }

def _compact_code_neighbors_for_packet(
    code_neighbors: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    summary_only: bool,
) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    for bucket_name, bucket in code_neighbors.items():
        if not isinstance(bucket, list) or not bucket:
            continue
        summary[bucket_name] = {
            "total": len(bucket),
            "top_paths": [
                str(row.get("path", "")).strip()
                for row in bucket[:2]
                if isinstance(row, Mapping) and str(row.get("path", "")).strip()
            ],
        }
        if summary_only and bucket_name not in {"documented_by", "covered_by_runbooks", "invoked_by_make", "imports", "imported_by"}:
            continue
        if bucket_name in {"documented_by", "covered_by_runbooks", "invoked_by_make", "imports", "imported_by"}:
            compact[bucket_name] = _prioritized_neighbor_rows(bucket_name, bucket)[:3]
    if summary:
        compact["summary"] = summary
    return compact

def _collect_component_validation_commands(
    connection: Any,
    *,
    component_ids: Sequence[str],
) -> list[str]:
    ordered_component_ids = [str(token).strip() for token in component_ids if str(token).strip()]
    if not ordered_component_ids:
        return []
    placeholders = ",".join("?" for _ in ordered_component_ids)
    rows = connection.execute(
        f"SELECT component_id, metadata_json FROM components WHERE component_id IN ({placeholders})",
        tuple(ordered_component_ids),
    ).fetchall()
    metadata_by_component = {
        str(row["component_id"]): json.loads(str(row["metadata_json"] or "{}"))
        for row in rows
    }
    commands: list[str] = []
    for component_id in ordered_component_ids:
        metadata = metadata_by_component.get(component_id, {})
        if not isinstance(metadata, Mapping):
            continue
        for row in metadata.get("validation_playbook_commands", []):
            if not isinstance(row, Mapping):
                continue
            command = str(row.get("command", "")).strip()
            if command:
                commands.append(command)
    return _dedupe_strings(commands)

def _recommended_validation_commands(
    *,
    command_hints: Sequence[str],
    component_commands: Sequence[str],
    tests: Sequence[Mapping[str, Any]],
    changed_paths: Sequence[str],
    notes: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[str]:
    hinted_commands = [
        str(command).strip()
        for command in command_hints
        if str(command).strip()
    ]
    primary_component_commands = [
        str(command).strip()
        for command in component_commands
        if str(command).strip() and not _is_governance_sync_command(str(command))
    ]
    component_sync_commands = [
        str(command).strip()
        for command in component_commands
        if str(command).strip() and _is_governance_sync_command(str(command))
    ]
    commands: list[str] = [*hinted_commands, *primary_component_commands]
    make_targets = _dedupe_strings(
        [
            str(row.get("title", "")).strip()
            for row in notes.get("make_target", [])
            if isinstance(row, Mapping) and str(row.get("title", "")).strip()
        ]
    )
    commands.extend(f"make {target}" for target in make_targets[:3])
    unique_test_paths = _dedupe_strings([str(row.get("test_path", "")).strip() for row in tests if str(row.get("test_path", "")).strip()])
    if unique_test_paths:
        commands.append("pytest " + " ".join(unique_test_paths[:8]))
    commands.extend(component_sync_commands)
    if changed_paths:
        commands.append(
            display_command("sync", "--repo-root", ".", "--check-only", *changed_paths[:8])
        )
    return _dedupe_strings(commands)

def _is_governance_sync_command(command: str) -> bool:
    token = str(command).strip().lower()
    return token.startswith("odylith sync") or "sync_workstream_artifacts" in token

def _workstream_status_rank(status: str) -> int:
    token = str(status or "").strip().lower()
    order = {
        "implementation": 0,
        "planning": 1,
        "queued": 2,
        "parked": 3,
        "finished": 4,
        "superseded": 5,
    }
    return order.get(token, 99)

def _workstream_rank_tuple(row: Mapping[str, Any]) -> tuple[int, str]:
    return (
        _workstream_status_rank(str(row.get("status", ""))),
        str(row.get("entity_id", "")),
    )

def _condense_delivery_scope(scope: Mapping[str, Any]) -> dict[str, Any]:
    linked = scope.get("linked", {}) if isinstance(scope.get("linked"), Mapping) else {}
    return {
        "scope_key": str(scope.get("scope_key", "")).strip(),
        "scope_type": str(scope.get("scope_type", "")).strip(),
        "scope_id": str(scope.get("scope_id", "")).strip(),
        "trajectory": str(scope.get("trajectory", "")).strip(),
        "linked_components": [str(token).strip() for token in linked.get("components", []) if str(token).strip()]
        if isinstance(linked.get("components"), list)
        else [],
        "linked_diagrams": [str(token).strip() for token in linked.get("diagrams", []) if str(token).strip()]
        if isinstance(linked.get("diagrams"), list)
        else [],
        "linked_surfaces": [str(token).strip() for token in linked.get("surfaces", []) if str(token).strip()]
        if isinstance(linked.get("surfaces"), list)
        else [],
    }
