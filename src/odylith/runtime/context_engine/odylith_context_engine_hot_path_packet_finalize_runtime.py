from __future__ import annotations

from typing import Any

from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bootstrap_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_core_runtime
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.context_engine import path_bundle_codec
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bindings
from odylith.runtime.governance import proof_state as proof_state_runtime

_BENCHMARK_RUNNER_REVIEWER_GUIDE = "docs/benchmarks/REVIEWER_GUIDE.md"
_BENCHMARK_IMPACT_COMPANION_DOC_EXPANSION_PATHS = {
    "README.md",
    "docs/benchmarks/README.md",
    "docs/benchmarks/METRICS_AND_PRIORITIES.md",
    _BENCHMARK_RUNNER_REVIEWER_GUIDE,
    "docs/benchmarks/release-baselines.v1.json",
    "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
    "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
    "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
    "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
    "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
    "tests/unit/runtime/test_odylith_benchmark_runner.py",
}

def bind(host: Any) -> None:
    odylith_context_engine_hot_path_packet_bindings.bind_hot_path_packet_runtime(globals(), host)

def _compact_hot_path_runtime_packet(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
    retain_internal_context: bool = False,
) -> dict[str, Any]:
    normalized_packet_kind = str(packet_kind or "").strip()
    if not retain_internal_context and normalized_packet_kind in {"bootstrap_session", "session_brief"}:
        return odylith_context_engine_hot_path_packet_bootstrap_runtime._compact_bootstrap_or_brief_hot_path_delivery(
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
        compact_narrowing_guidance = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_narrowing_guidance(
            narrowing_guidance
        )
        if compact_narrowing_guidance:
            compact["narrowing_guidance"] = compact_narrowing_guidance
    for key in contract_keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            compact[key] = dict(value)
        elif isinstance(value, list):
            compact[key] = [dict(row) if isinstance(row, Mapping) else row for row in value[:4]]
    if normalized_packet_kind == "governance_slice":
        normalized_proof_state = proof_state_runtime.normalize_proof_state(payload.get("proof_state"))
        if normalized_proof_state:
            compact["proof_state"] = normalized_proof_state
        proof_state_resolution = (
            dict(payload.get("proof_state_resolution", {}))
            if isinstance(payload.get("proof_state_resolution"), Mapping)
            else {}
        )
        if proof_state_resolution:
            compact["proof_state_resolution"] = proof_state_resolution
        claim_guard = (
            dict(payload.get("claim_guard", {}))
            if isinstance(payload.get("claim_guard"), Mapping)
            else proof_state_runtime.build_claim_guard(normalized_proof_state)
            if normalized_proof_state
            else {}
        )
        if claim_guard:
            compact["claim_guard"] = claim_guard
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
            compact_conflicts = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_active_conflicts(
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
            odylith_context_engine_hot_path_packet_bootstrap_runtime._compact_governance_surface_refs_for_hot_path(
                dict(payload.get("surface_refs", {}))
            )
            if isinstance(payload.get("surface_refs"), Mapping)
            else {}
        )
        governance_signal = odylith_context_engine_hot_path_packet_bootstrap_runtime._compact_governance_signal_for_hot_path(
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
        if compact_changed_paths and not odylith_context_engine_hot_path_packet_core_runtime._governance_changed_paths_shadow_redundant(
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
        routing_handoff_payload = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_routing_handoff(
            dict(payload.get("routing_handoff", {}))
        )
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
                and odylith_context_engine_hot_path_packet_core_runtime._hot_path_keep_architecture_audit(
                    compact_architecture_audit
                )
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
        compact["fallback_scan"] = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_fallback_scan(
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
        and odylith_context_engine_hot_path_packet_core_runtime._source_hot_path_within_budget(payload)
        and (
            str(packet_state or "").strip().startswith("gated_")
            or bool(source_route.get("route_ready"))
        )
    ):
        return odylith_context_engine_hot_path_packet_core_runtime._fast_finalize_compact_hot_path_packet(
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
    compact_packet_metrics = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_packet_metrics(
        packet_metrics
    )
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
        readiness = odylith_context_engine_hot_path_packet_core_runtime._hot_path_recomputed_readiness(
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
        compact_execution_profile_payload = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_route_execution_profile(
            execution_profile_payload
        )
        if isinstance(compact.get("routing_handoff"), Mapping):
            routing_handoff_payload = dict(compact.get("routing_handoff", {}))
            if compact_execution_profile_payload and (
                bool(readiness.get("route_ready"))
                or str(compact_execution_profile_payload.get("delegate_preference", "")).strip()
                not in {"", "hold_local"}
            ):
                routing_handoff_payload["execution_profile"] = odylith_context_engine_hot_path_packet_core_runtime._encode_hot_path_execution_profile(
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
    return odylith_context_engine_hot_path_packet_core_runtime._drop_redundant_hot_path_routing_handoff(compact)

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
        compact["fallback_scan"] = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_fallback_scan(
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
        and odylith_context_engine_hot_path_packet_core_runtime._source_hot_path_within_budget(merged)
        and (
            str(context_packet_payload.get("packet_state", "")).strip().startswith("gated_")
            or bool(source_route.get("route_ready"))
        )
    ):
        return odylith_context_engine_hot_path_packet_core_runtime._fast_finalize_compact_hot_path_packet(
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
    compact_packet_metrics = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_packet_metrics(
        packet_metrics
    )
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
    readiness = odylith_context_engine_hot_path_packet_core_runtime._hot_path_recomputed_readiness(
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
    compact_execution_profile_payload = odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_route_execution_profile(
        execution_profile_payload
    )
    if isinstance(compact.get("routing_handoff"), Mapping):
        routing_handoff_payload = dict(compact.get("routing_handoff", {}))
        if compact_execution_profile_payload and (
            bool(readiness.get("route_ready"))
            or str(compact_execution_profile_payload.get("delegate_preference", "")).strip() not in {"", "hold_local"}
        ):
            routing_handoff_payload["execution_profile"] = odylith_context_engine_hot_path_packet_core_runtime._encode_hot_path_execution_profile(
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
    return odylith_context_engine_hot_path_packet_core_runtime._drop_redundant_hot_path_routing_handoff(
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
        context_packet_payload = odylith_context_engine_hot_path_packet_core_runtime._trim_common_hot_path_context_packet(
            context_packet_payload=context_packet_payload,
            within_budget=odylith_context_engine_hot_path_packet_core_runtime._compact_hot_path_payload_within_budget(
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
        compact_profile = odylith_context_engine_hot_path_packet_core_runtime._decode_hot_path_execution_profile(
            routing_handoff_payload.get("execution_profile") or routing_handoff_payload.get("odylith_execution_profile")
        )
        if compact_profile:
            trimmed["routing_handoff"] = {
                "execution_profile": odylith_context_engine_hot_path_packet_core_runtime._encode_hot_path_execution_profile(
                    compact_profile
                )
            }
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
