from __future__ import annotations

from typing import Any

from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_core_runtime
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.context_engine import path_bundle_codec
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bindings
from odylith.runtime.governance import proof_state as proof_state_runtime

def bind(host: Any) -> None:
    odylith_context_engine_hot_path_packet_bindings.bind_hot_path_packet_runtime(globals(), host)

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
    narrowing_guidance = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_narrowing_guidance(
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
        compact_fallback = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_fallback_scan(
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
