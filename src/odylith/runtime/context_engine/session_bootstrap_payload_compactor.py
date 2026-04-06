"""Compact duplicate bootstrap-session path receipts before packet finalization."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.memory import tooling_memory_contracts


def _string_rows(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    for item in value:
        token = str(item).strip()
        if token and token not in rows:
            rows.append(token)
    return rows


def _clean_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): item
        for key, item in value.items()
        if item not in ("", [], {}, None)
    }


def _mapping(value: Any) -> dict[str, Any]:
    return {str(key): item for key, item in dict(value).items()} if isinstance(value, Mapping) else {}


def _encode_selected_counts_token(value: Any) -> str:
    counts = _mapping(value)
    if not counts:
        token = str(value or "").strip()
        return token
    parts: list[str] = []
    for key, alias in (("commands", "c"), ("docs", "d"), ("tests", "t"), ("guidance", "g")):
        count = int(counts.get(key, 0) or 0)
        if count > 0:
            parts.append(f"{alias}{count}")
    return "".join(parts)


def _compact_narrowing_guidance(guidance: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    if bool(guidance.get("required")):
        compact["required"] = True
    reason = str(guidance.get("reason", "")).strip()
    if reason.startswith("Top candidate `") and reason.endswith("is too weak to auto-trust."):
        reason = "Need one code or contract path."
    elif reason.startswith("No workstream evidence matched"):
        reason = "Need one code path."
    elif reason.startswith("Current shared/control-plane context still needs one concrete code"):
        reason = "Need one code or contract path."
    elif len(reason) > 48:
        reason = f"{reason[:45].rstrip()}..."
    if reason:
        compact["reason"] = reason
    suggested_inputs = _string_rows(guidance.get("suggested_inputs"))
    if suggested_inputs:
        first = suggested_inputs[0]
        compact["suggested_inputs"] = [
            {
                "Provide at least one implementation, test, contract, or manifest path.": "Provide one code or contract path.",
                "Pin an explicit workstream with `--workstream B-###` when the slice is known.": "Pin `--workstream B-###` if known.",
                "Read the highest-signal guidance source directly when the packet exposes one.": "Read the strongest cited source first.",
                "If narrowing still fails, run the printed fallback command and then read the named source directly.": "Use the printed fallback command if narrowing fails.",
            }.get(first, first)
        ]
    if compact.get("reason") in {"Need one code path.", "Need one code or contract path."}:
        compact.pop("suggested_inputs", None)
    return compact


def _compact_session_payload(session: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "session_id": str(session.get("session_id", "")).strip(),
            "intent": str(session.get("intent", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    claimed_paths = _string_rows(session.get("claimed_paths"))
    if claimed_paths:
        compact["claimed_paths"] = claimed_paths[:4]
    return compact


def _compact_workstream_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
    selected_workstream = _mapping(selection.get("selected_workstream"))
    top_candidate = _mapping(selection.get("top_candidate")) or selected_workstream
    compact = {
        key: value
        for key, value in {
            "state": str(selection.get("state", "")).strip(),
            "confidence": str(selection.get("confidence", "")).strip(),
            "ambiguity_class": str(selection.get("ambiguity_class", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    if str(selected_workstream.get("entity_id", "")).strip():
        compact["selected_workstream"] = {"entity_id": str(selected_workstream.get("entity_id", "")).strip()}
    if str(top_candidate.get("entity_id", "")).strip():
        compact["top_candidate"] = {"entity_id": str(top_candidate.get("entity_id", "")).strip()}
    competing = [
        {"entity_id": str(row.get("entity_id", "")).strip()}
        for row in selection.get("competing_candidates", [])
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    ]
    if competing:
        compact["competing_candidates"] = competing[:2]
    return compact


def _compact_adaptive_packet_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "source": str(profile.get("source", "")).strip(),
            "packet_strategy": str(profile.get("packet_strategy", "")).strip(),
            "budget_mode": str(profile.get("budget_mode", "")).strip(),
            "retrieval_focus": str(profile.get("retrieval_focus", "")).strip(),
            "speed_mode": str(profile.get("speed_mode", "")).strip(),
            "reliability": str(profile.get("reliability", "")).strip(),
            "selection_bias": str(profile.get("selection_bias", "")).strip(),
            "budget_scale": float(profile.get("budget_scale", 0.0) or 0.0),
        }.items()
        if value not in ("", [], {}, None, 0.0)
    }


def _compact_fallback_scan(scan: Mapping[str, Any]) -> dict[str, Any]:
    results = [
        {
            key: value
            for key, value in {
                "path": str(row.get("path", "")).strip(),
                "kind": str(row.get("kind", "")).strip(),
            }.items()
            if value not in ("", [], {}, None)
        }
        for row in scan.get("results", [])
        if isinstance(row, Mapping) and str(row.get("path", "")).strip()
    ]
    if not bool(scan.get("performed")) and not results:
        return {}
    compact = {
        key: value
        for key, value in {
            "performed": bool(scan.get("performed")),
            "reason": str(scan.get("reason", "")).strip(),
            "reason_message": str(scan.get("reason_message", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    if results:
        compact["results"] = results[:2]
    return compact


def _compact_context_packet_anchors(
    anchors: Mapping[str, Any],
    *,
    changed_paths: list[str],
    explicit_paths: list[str],
) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "anchor_quality": str(anchors.get("anchor_quality", "")).strip(),
            "has_non_shared_anchor": bool(anchors.get("has_non_shared_anchor")),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    anchor_explicit_paths = _string_rows(anchors.get("explicit_paths"))
    if anchor_explicit_paths and anchor_explicit_paths != changed_paths and anchor_explicit_paths != explicit_paths:
        compact["explicit_paths"] = anchor_explicit_paths[:4]
    return compact


def _compact_context_packet_retrieval_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "ambiguity_class": str(plan.get("ambiguity_class", "")).strip(),
            "guidance_coverage": str(plan.get("guidance_coverage", "")).strip(),
            "evidence_consensus": str(plan.get("evidence_consensus", "")).strip(),
            "precision_score": int(plan.get("precision_score", 0) or 0),
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    selected_counts = plan.get("selected_counts")
    token = _encode_selected_counts_token(selected_counts)
    if token:
        compact["selected_counts"] = token
    return compact


def _compact_context_packet_quality(quality: Mapping[str, Any]) -> dict[str, Any]:
    return packet_quality_codec.compact_packet_quality({
        key: value
        for key, value in {
            "routing_confidence": str(quality.get("routing_confidence", "")).strip(),
            "intent_family": str(quality.get("intent_family", "")).strip(),
            "intent_mode": str(quality.get("intent_mode", "")).strip(),
            "intent_critical_path": str(quality.get("intent_critical_path", "")).strip(),
            "intent_confidence": str(quality.get("intent_confidence", "")).strip(),
            "intent_explicit": bool(quality.get("intent_explicit")),
            "context_density_level": str(quality.get("context_density_level", "")).strip(),
            "reasoning_readiness_level": str(quality.get("reasoning_readiness_level", "")).strip(),
            "context_richness": str(quality.get("context_richness", "")).strip(),
            "accuracy_posture": str(quality.get("accuracy_posture", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, False)
    })


def _compact_context_packet_route(route: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "route_ready": bool(route.get("route_ready")),
            "native_spawn_ready": bool(route.get("native_spawn_ready")),
            "narrowing_required": bool(route.get("narrowing_required")),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    parallelism_hint = str(route.get("parallelism_hint", "")).strip()
    if parallelism_hint:
        compact["p"] = parallelism_hint
    reasoning_bias = str(route.get("reasoning_bias", "")).strip()
    if reasoning_bias:
        compact["b"] = reasoning_bias
    return compact


def _compact_context_packet_execution_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "profile": str(profile.get("profile", "")).strip(),
            "agent_role": str(profile.get("agent_role", "")).strip(),
            "selection_mode": str(profile.get("selection_mode", "")).strip(),
            "delegate_preference": str(profile.get("delegate_preference", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    token = tooling_memory_contracts.encode_execution_profile_token(compact)
    return {"token": token} if token else {}


def _compact_context_packet_optimization(optimization: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "within_budget": bool(optimization.get("within_budget")),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    miss_recovery = _mapping(optimization.get("miss_recovery"))
    if any([bool(miss_recovery.get("active")), bool(miss_recovery.get("applied")), str(miss_recovery.get("mode", "")).strip()]):
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


def _compact_delivery_context_packet(
    *,
    context_packet: Mapping[str, Any],
    changed_paths: list[str],
    explicit_paths: list[str],
) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "packet_kind": str(context_packet.get("packet_kind", "")).strip(),
            "packet_state": str(context_packet.get("packet_state", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    anchors = _compact_context_packet_anchors(
        _mapping(context_packet.get("anchors")),
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
    )
    if anchors:
        compact["anchors"] = anchors
    retrieval_plan = _compact_context_packet_retrieval_plan(_mapping(context_packet.get("retrieval_plan")))
    if retrieval_plan:
        compact["retrieval_plan"] = retrieval_plan
    packet_quality = _compact_context_packet_quality(_mapping(context_packet.get("packet_quality")))
    if packet_quality:
        compact["packet_quality"] = packet_quality
    route = _compact_context_packet_route(_mapping(context_packet.get("route")))
    if route:
        compact["route"] = route
    execution_profile = _compact_context_packet_execution_profile(_mapping(context_packet.get("execution_profile")))
    if execution_profile:
        compact["execution_profile"] = execution_profile
    optimization = _compact_context_packet_optimization(_mapping(context_packet.get("optimization")))
    if optimization:
        compact["optimization"] = optimization
    return compact


def _compact_bootstrap_delivery_routing_handoff(
    *,
    routing_handoff: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    route_ready: bool,
) -> dict[str, Any]:
    if not route_ready or not routing_handoff:
        return {}
    compact = {
        key: value
        for key, value in {
            "packet_kind": str(routing_handoff.get("packet_kind", "")).strip(),
            "routing_confidence": str(routing_handoff.get("routing_confidence", "")).strip(),
            "route_ready": bool(routing_handoff.get("route_ready")),
            "narrowing_required": bool(routing_handoff.get("narrowing_required")),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    execution_profile = _mapping(routing_handoff.get("odylith_execution_profile"))
    if not execution_profile:
        execution_profile = _mapping(context_packet.get("execution_profile"))
    if execution_profile:
        compact["odylith_execution_profile"] = {
            key: value
            for key, value in {
                "profile": str(execution_profile.get("profile", "")).strip(),
                "agent_role": str(execution_profile.get("agent_role", "")).strip(),
                "selection_mode": str(execution_profile.get("selection_mode", "")).strip(),
                "delegate_preference": str(execution_profile.get("delegate_preference", "")).strip(),
                "source": str(execution_profile.get("source", "")).strip(),
            }.items()
            if value not in ("", [], {}, None)
        }
    return compact


def _compact_bootstrap_delivery_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    changed_paths = _string_rows(payload.get("changed_paths"))
    explicit_paths = _string_rows(payload.get("explicit_paths"))
    context_packet = _compact_delivery_context_packet(
        context_packet=_mapping(payload.get("context_packet")),
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
    )
    route = _mapping(context_packet.get("route"))
    route_ready = bool(payload.get("route_ready") or route.get("route_ready"))
    compact = {
        "changed_paths": changed_paths[:4],
        "selection_state": str(payload.get("selection_state", "")).strip(),
        "selection_reason": str(payload.get("selection_reason", "")).strip(),
        "selection_confidence": str(payload.get("selection_confidence", "")).strip(),
        "context_packet": context_packet,
    }
    if isinstance(payload.get("session"), Mapping):
        compact["session"] = _compact_session_payload(_mapping(payload.get("session")))
    if isinstance(payload.get("workstream_selection"), Mapping):
        compact["workstream_selection"] = _compact_workstream_selection(_mapping(payload.get("workstream_selection")))
    if isinstance(payload.get("adaptive_packet_profile"), Mapping):
        adaptive = _compact_adaptive_packet_profile(_mapping(payload.get("adaptive_packet_profile")))
        if adaptive:
            compact["adaptive_packet_profile"] = adaptive
    if isinstance(payload.get("narrowing_guidance"), Mapping):
        narrowing = _compact_narrowing_guidance(_mapping(payload.get("narrowing_guidance")))
        if narrowing:
            compact["narrowing_guidance"] = narrowing
    if isinstance(payload.get("routing_handoff"), Mapping):
        routing = _compact_bootstrap_delivery_routing_handoff(
            routing_handoff=_mapping(payload.get("routing_handoff")),
            context_packet=context_packet,
            route_ready=route_ready,
        )
        if routing:
            compact["routing_handoff"] = routing
    if isinstance(payload.get("fallback_scan"), Mapping):
        fallback = _compact_fallback_scan(_mapping(payload.get("fallback_scan")))
        if fallback:
            compact["fallback_scan"] = fallback
    inferred_workstream = str(payload.get("inferred_workstream", "")).strip()
    if inferred_workstream:
        compact["inferred_workstream"] = inferred_workstream
    if bool(payload.get("full_scan_recommended")):
        compact["full_scan_recommended"] = True
    full_scan_reason = str(payload.get("full_scan_reason", "")).strip()
    if full_scan_reason:
        compact["full_scan_reason"] = full_scan_reason
    relevant_docs = _string_rows(payload.get("relevant_docs"))
    if relevant_docs:
        compact["relevant_docs"] = relevant_docs[:2]
    recommended_commands = _string_rows(payload.get("recommended_commands"))
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
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}, None, False)
    }


def _compact_session_brief_impact(impact: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    primary_workstream = _mapping(impact.get("primary_workstream"))
    if str(primary_workstream.get("entity_id", "")).strip():
        compact["primary_workstream"] = {"entity_id": str(primary_workstream.get("entity_id", "")).strip()}
    docs = _string_rows(impact.get("docs"))
    if docs:
        compact["docs"] = docs[:2]
    commands = _string_rows(impact.get("recommended_commands"))
    if commands:
        compact["recommended_commands"] = commands[:2]
    tests = [
        {
            key: value
            for key, value in {
                "path": str(row.get("path", "")).strip(),
                "nodeid": str(row.get("nodeid", "")).strip(),
                "reason": str(row.get("reason", "")).strip(),
            }.items()
            if value not in ("", [], {}, None)
        }
        for row in impact.get("recommended_tests", [])
        if isinstance(row, Mapping)
    ]
    if tests:
        compact["recommended_tests"] = tests[:2]
    miss_recovery = _mapping(impact.get("miss_recovery"))
    if any([bool(miss_recovery.get("active")), bool(miss_recovery.get("applied")), str(miss_recovery.get("mode", "")).strip()]):
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


def _compact_session_brief_delivery_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    changed_paths = _string_rows(payload.get("changed_paths"))
    explicit_paths = _string_rows(payload.get("explicit_paths"))
    compact = {
        "changed_paths": changed_paths[:4],
        "selection_state": str(payload.get("selection_state", "")).strip(),
        "selection_reason": str(payload.get("selection_reason", "")).strip(),
        "selection_confidence": str(payload.get("selection_confidence", "")).strip(),
        "context_packet": _compact_delivery_context_packet(
            context_packet=_mapping(payload.get("context_packet")),
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
        ),
    }
    if isinstance(payload.get("session"), Mapping):
        compact["session"] = _compact_session_payload(_mapping(payload.get("session")))
    if isinstance(payload.get("workstream_selection"), Mapping):
        compact["workstream_selection"] = _compact_workstream_selection(_mapping(payload.get("workstream_selection")))
    if isinstance(payload.get("adaptive_packet_profile"), Mapping):
        adaptive = _compact_adaptive_packet_profile(_mapping(payload.get("adaptive_packet_profile")))
        if adaptive:
            compact["adaptive_packet_profile"] = adaptive
    if isinstance(payload.get("narrowing_guidance"), Mapping):
        narrowing = _compact_narrowing_guidance(_mapping(payload.get("narrowing_guidance")))
        if narrowing:
            compact["narrowing_guidance"] = narrowing
    if isinstance(payload.get("impact"), Mapping):
        impact = _compact_session_brief_impact(_mapping(payload.get("impact")))
        if impact:
            compact["impact"] = impact
    if isinstance(payload.get("workstream_context"), Mapping) and _mapping(payload.get("workstream_context")):
        compact["workstream_context"] = _mapping(payload.get("workstream_context"))
    if isinstance(payload.get("fallback_scan"), Mapping):
        fallback = _compact_fallback_scan(_mapping(payload.get("fallback_scan")))
        if fallback:
            compact["fallback_scan"] = fallback
    inferred_workstream = str(payload.get("inferred_workstream", "")).strip()
    if inferred_workstream:
        compact["inferred_workstream"] = inferred_workstream
    if bool(payload.get("full_scan_recommended")):
        compact["full_scan_recommended"] = True
    full_scan_reason = str(payload.get("full_scan_reason", "")).strip()
    if full_scan_reason:
        compact["full_scan_reason"] = full_scan_reason
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}, None, False)
    }


def compact_bootstrap_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Drop duplicate path lists that do not add bootstrap-session signal."""

    compacted = {str(key): value for key, value in dict(payload).items()}
    changed_paths = _string_rows(compacted.get("changed_paths"))
    explicit_paths = _string_rows(compacted.get("explicit_paths"))
    scoped_paths = _string_rows(compacted.get("scoped_working_tree_paths"))
    repo_dirty_paths = _string_rows(compacted.get("repo_dirty_paths"))

    if not explicit_paths or (changed_paths and explicit_paths == changed_paths):
        compacted.pop("explicit_paths", None)
        explicit_paths = []
    if changed_paths and scoped_paths == changed_paths:
        compacted.pop("scoped_working_tree_paths", None)
        scoped_paths = []
    if repo_dirty_paths and (
        repo_dirty_paths == changed_paths
        or (scoped_paths and repo_dirty_paths == scoped_paths)
    ):
        compacted.pop("repo_dirty_paths", None)

    session = (
        {str(key): value for key, value in dict(compacted.get("session", {})).items()}
        if isinstance(compacted.get("session"), Mapping)
        else {}
    )
    if not session:
        return compacted

    session_explicit_paths = _string_rows(session.get("explicit_paths"))
    session_analysis_paths = _string_rows(session.get("analysis_paths"))
    session_touched_paths = _string_rows(session.get("touched_paths"))

    if not session_explicit_paths or session_explicit_paths == explicit_paths or (
        changed_paths and session_explicit_paths == changed_paths
    ):
        session.pop("explicit_paths", None)
    if session_analysis_paths and (
        session_analysis_paths == changed_paths
        or (scoped_paths and session_analysis_paths == scoped_paths)
    ):
        session.pop("analysis_paths", None)
        session_analysis_paths = []
    if session_touched_paths and (
        session_touched_paths == changed_paths
        or (session_analysis_paths and session_touched_paths == session_analysis_paths)
    ):
        session.pop("touched_paths", None)
    if str(session.get("working_tree_scope", "")).strip() == str(compacted.get("working_tree_scope", "")).strip():
        session.pop("working_tree_scope", None)
    if str(session.get("selection_state", "")).strip() == str(compacted.get("selection_state", "")).strip():
        session.pop("selection_state", None)

    cleaned_session = _clean_mapping(session)
    if cleaned_session:
        compacted["session"] = cleaned_session
    else:
        compacted.pop("session", None)
    return compacted


def compact_finalized_bootstrap_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a slim bootstrap delivery payload while full telemetry stays internal."""

    return _compact_bootstrap_delivery_payload(payload)


def compact_finalized_session_brief_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a slim session-brief delivery payload while full telemetry stays internal."""

    return _compact_session_brief_delivery_payload(payload)


__all__ = [
    "compact_bootstrap_payload",
    "compact_finalized_bootstrap_payload",
    "compact_finalized_session_brief_payload",
]
