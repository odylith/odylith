"""Completion cycle for Context Engine packet assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import tooling_context_budgeting as budgeting
from odylith.runtime.context_engine import tooling_context_packet_compaction as packet_compaction
from odylith.runtime.context_engine import tooling_context_packet_context_views as packet_context_views
from odylith.runtime.context_engine import tooling_context_packet_finalization as packet_finalization
from odylith.runtime.context_engine import tooling_context_packet_profile as packet_profile
from odylith.runtime.context_engine import tooling_context_quality as quality
from odylith.runtime.context_engine import tooling_context_routing as routing
from odylith.runtime.memory import tooling_memory_contracts


def finalize_packet_without_odylith(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
    packet_state: str,
    odylith_switch: Mapping[str, Any],
) -> dict[str, Any]:
    budget_meta = budgeting.packet_budget(packet_kind=packet_kind, packet_state=packet_state)
    trimmed, _trim_budget, _content_metrics, budget_truncation = budgeting.apply_packet_budget(
        dict(payload),
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget_override=budget_meta,
    )
    final_payload = dict(trimmed)
    truncation = dict(final_payload.get("truncation", {})) if isinstance(final_payload.get("truncation"), Mapping) else {}
    packet_budget_truncation = dict(budget_truncation)
    packet_budget_truncation["retry_index"] = 0
    truncation["packet_budget"] = packet_budget_truncation
    final_payload["packet_budget"] = dict(budget_meta)
    final_payload["truncation"] = truncation
    final_payload.pop("retrieval_plan", None)
    final_payload.pop("guidance_brief", None)
    final_payload.pop("narrowing_guidance", None)
    final_payload.pop("working_memory_tiers", None)
    final_payload.pop("packet_quality", None)
    final_payload.pop("routing_handoff", None)
    final_payload.pop("context_packet", None)
    final_payload.pop("evidence_pack", None)
    final_payload["odylith_switch"] = dict(odylith_switch)
    final_payload["odylith_ablation"] = {
        "status": "disabled",
        "reason": "odylith_switch_off",
        "suppressed_contracts": [
            "retrieval_plan.v1",
            "routing_handoff.v1",
            "context_packet.v1",
            "evidence_pack.v1",
            "optimization_snapshot.v1",
        ],
    }
    packet_metrics = budgeting.estimate_packet_metrics(
        final_payload,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    final_payload["packet_metrics"] = dict(packet_metrics)
    final_payload = packet_finalization.sync_packet_budget_truncation(final_payload, packet_metrics=packet_metrics)
    if isinstance(final_payload.get("truncation"), Mapping):
        final_payload = packet_compaction.compact_finalize_metadata(final_payload, budget_meta=budget_meta)
        refreshed_metrics = budgeting.estimate_packet_metrics(
            final_payload,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        final_payload["packet_metrics"] = dict(refreshed_metrics)
        final_payload = packet_finalization.sync_packet_budget_truncation(final_payload, packet_metrics=refreshed_metrics)
    return final_payload


def complete_packet(
    *,
    repo_root: Path,
    packet_kind: str,
    packet_state: str,
    enriched_payload: Mapping[str, Any],
    selection_state: str,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    shared_only_input: bool,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    docs: Sequence[str],
    recommended_tests: Sequence[Mapping[str, Any]],
    miss_recovery: Mapping[str, Any],
    full_scan_recommended: bool,
    full_scan_reason: str,
    session_id: str,
    delivery_profile: str,
    retrieval_plan: Mapping[str, Any],
    retrieval_bundle: Mapping[str, Any],
    guidance_catalog_summary: Mapping[str, Any],
    effective_recommended_commands: Sequence[str],
    adaptive_packet_profile: Mapping[str, Any],
    optimization: Mapping[str, Any],
) -> dict[str, Any]:
    budget_meta = budgeting.packet_budget(packet_kind=packet_kind, packet_state=packet_state)
    final_plan: dict[str, Any] = dict(retrieval_plan)
    working_budget = packet_profile.apply_adaptive_budget_profile(
        packet_profile.content_budget(
            budget_meta,
            trim_order_paths=packet_profile.reorder_trim_paths(
                packet_kind=packet_kind,
                packet_state=packet_state,
                selection_state=selection_state,
                retrieval_plan=final_plan,
                adaptive_packet_profile=adaptive_packet_profile,
            ),
        ),
        adaptive_packet_profile=adaptive_packet_profile,
    )
    build_evidence_pack = not agent_runtime_contract.is_agent_hot_path_profile(delivery_profile)
    hot_path = not build_evidence_pack
    final_packet: dict[str, Any] = {}
    final_metrics: dict[str, Any] = {}
    hot_path_context_views = {
        "retrieval_plan": dict(final_plan),
        "guidance_brief": [dict(row) for row in retrieval_bundle.get("guidance_brief", []) if isinstance(row, Mapping)]
        if isinstance(retrieval_bundle.get("guidance_brief"), list)
        else [],
        "narrowing_guidance": dict(enriched_payload.get("narrowing_guidance", {}))
        if isinstance(enriched_payload.get("narrowing_guidance"), Mapping)
        else {},
    }
    for retry_index in range(3):
        trimmed, _trim_budget, _content_metrics, budget_truncation = budgeting.apply_packet_budget(
            dict(enriched_payload),
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_override=working_budget,
        )
        truncation = dict(trimmed.get("truncation", {})) if isinstance(trimmed.get("truncation"), Mapping) else {}
        packet_budget_truncation = dict(budget_truncation)
        packet_budget_truncation["retry_index"] = retry_index
        truncation["packet_budget"] = packet_budget_truncation
        base_payload = dict(trimmed)
        base_payload["packet_budget"] = dict(budget_meta)
        base_payload["truncation"] = truncation
        if packet_context_views.can_reuse_hot_path_context_views(
            packet_kind=packet_kind,
            build_working_memory_tiers=build_evidence_pack,
            payload=base_payload,
        ):
            base_payload, final_plan = packet_context_views.reuse_hot_path_context_views(
                payload=base_payload,
                retrieval_plan=hot_path_context_views["retrieval_plan"],
                guidance_brief=hot_path_context_views["guidance_brief"],
                narrowing_guidance=hot_path_context_views["narrowing_guidance"],
            )
        else:
            base_payload, final_plan = packet_context_views.refresh_context_views(
                repo_root=repo_root,
                packet_kind=packet_kind,
                packet_state=packet_state,
                payload=base_payload,
                changed_paths=changed_paths,
                explicit_paths=explicit_paths,
                shared_only_input=shared_only_input,
                selection_state=selection_state,
                workstream_selection=workstream_selection,
                candidate_workstreams=candidate_workstreams,
                components=components,
                diagrams=diagrams,
                docs=docs,
                recommended_commands=effective_recommended_commands,
                recommended_tests=recommended_tests,
                fallback_guidance_chunks=retrieval_bundle.get("selected_guidance_chunks", []),
                miss_recovery=miss_recovery or {},
                guidance_catalog_summary=guidance_catalog_summary,
                full_scan_recommended=full_scan_recommended,
                full_scan_reason=full_scan_reason,
                session_id=session_id,
                build_working_memory_tiers=build_evidence_pack,
            )
        base_payload["adaptive_packet_profile"] = packet_profile.adaptive_packet_profile(
            packet_kind=packet_kind,
            packet_state=packet_state,
            selection_state=selection_state,
            retrieval_plan=final_plan,
            optimization_snapshot=optimization,
            full_scan_recommended=full_scan_recommended,
        )
        if hot_path:
            final_packet, final_metrics, _packet_quality, _routing_handoff = packet_finalization.finalize_packet_metadata_hot_path(
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget_meta=budget_meta,
                base_payload=base_payload,
                selection_state=selection_state,
                full_scan_recommended=full_scan_recommended,
                retrieval_plan=final_plan,
            )
        else:
            final_packet, final_metrics, _packet_quality, _routing_handoff = packet_finalization.finalize_packet_metadata(
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget_meta=budget_meta,
                base_payload=base_payload,
                selection_state=selection_state,
                full_scan_recommended=full_scan_recommended,
                retrieval_plan=final_plan,
                build_evidence_pack=build_evidence_pack,
                max_iterations=8,
            )
        if bool(final_metrics.get("within_budget")):
            break
        over_bytes = max(0, int(final_metrics.get("estimated_bytes", 0) or 0) - int(budget_meta.get("max_bytes", 0) or 0))
        over_tokens = max(0, int(final_metrics.get("estimated_tokens", 0) or 0) - int(budget_meta.get("max_tokens", 0) or 0))
        if over_bytes <= 0 and over_tokens <= 0:
            break
        working_budget = dict(working_budget)
        working_budget["max_bytes"] = max(1_000, int(working_budget.get("max_bytes", 0) or 0) - max(over_bytes, 384))
        working_budget["max_tokens"] = max(250, int(working_budget.get("max_tokens", 0) or 0) - max(over_tokens, 96))
    return _stabilize_completed_packet(
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget_meta=budget_meta,
        packet=final_packet,
        packet_metrics=final_metrics,
        selection_state=selection_state,
        full_scan_recommended=full_scan_recommended,
        retrieval_plan=final_plan,
        build_evidence_pack=build_evidence_pack,
        hot_path=hot_path,
    )


def _stabilize_completed_packet(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    packet: Mapping[str, Any],
    packet_metrics: Mapping[str, Any],
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
    build_evidence_pack: bool,
    hot_path: bool,
) -> dict[str, Any]:
    final_packet = packet_finalization.sync_packet_budget_truncation(packet, packet_metrics=packet_metrics)
    final_metrics = dict(packet_metrics)
    if hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        final_metrics = dict(final_packet.get("packet_metrics", {}))
        final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_metrics)
    elif isinstance(final_packet.get("truncation"), Mapping):
        final_packet = packet_compaction.compact_finalize_metadata(final_packet, budget_meta=budget_meta)
        final_packet, _reconciled_metrics, _reconciled_quality, _reconciled_handoff = packet_finalization.finalize_packet_metadata(
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_meta=budget_meta,
            base_payload=final_packet,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            build_evidence_pack=build_evidence_pack,
            max_iterations=1 if hot_path else 8,
        )
        if isinstance(final_packet.get("packet_metrics"), Mapping):
            final_metrics = dict(final_packet.get("packet_metrics", {}))
            final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_metrics)
    if not hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        final_packet, final_metrics = _reconcile_full_packet_metadata(
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_meta=budget_meta,
            packet=final_packet,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            build_evidence_pack=build_evidence_pack,
        )
    if hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        final_metrics = dict(final_packet.get("packet_metrics", {}))
    elif isinstance(final_packet.get("packet_metrics"), Mapping):
        final_packet, final_metrics = _stabilize_direct_metrics(
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_meta=budget_meta,
            packet=final_packet,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            build_evidence_pack=build_evidence_pack,
            hot_path=hot_path,
        )
    final_truth_metrics = (
        dict(final_packet.get("packet_metrics", {}))
        if hot_path and isinstance(final_packet.get("packet_metrics"), Mapping)
        else budgeting.estimate_packet_metrics(
            final_packet,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
    )
    if not bool(final_truth_metrics.get("within_budget")) and isinstance(final_packet.get("truncation"), Mapping):
        final_packet, final_truth_metrics = _compact_until_within_budget(
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_meta=budget_meta,
            packet=final_packet,
            packet_metrics=final_truth_metrics,
        )
    final_packet["packet_metrics"] = dict(final_truth_metrics)
    final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_truth_metrics)
    final_packet = _stamp_within_budget_truth(final_packet, within_budget=bool(final_truth_metrics.get("within_budget")))
    if not hot_path:
        final_packet = _stabilize_full_packet_truth(
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_meta=budget_meta,
            packet=final_packet,
        )
    return final_packet


def _reconcile_full_packet_metadata(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    packet: Mapping[str, Any],
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
    build_evidence_pack: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    final_packet = dict(packet)
    final_metrics = dict(final_packet.get("packet_metrics", {})) if isinstance(final_packet.get("packet_metrics"), Mapping) else {}
    for _ in range(3):
        reconciled_packet, reconciled_metrics, _reconciled_quality, _reconciled_handoff = packet_finalization.finalize_packet_metadata(
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_meta=budget_meta,
            base_payload=final_packet,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            build_evidence_pack=build_evidence_pack,
            max_iterations=8,
        )
        reconciled_packet = packet_finalization.sync_packet_budget_truncation(
            reconciled_packet,
            packet_metrics=reconciled_metrics,
        )
        if _metadata_snapshots_match(reconciled_packet, final_packet, reconciled_metrics):
            break
        final_packet = reconciled_packet
        final_metrics = reconciled_metrics
    return final_packet, final_metrics


def _metadata_snapshots_match(
    reconciled_packet: Mapping[str, Any],
    current_packet: Mapping[str, Any],
    reconciled_metrics: Mapping[str, Any],
) -> bool:
    return (
        dict(reconciled_metrics) == dict(current_packet.get("packet_metrics", {}))
        and dict(reconciled_packet.get("packet_quality", {})) == dict(current_packet.get("packet_quality", {}))
        and dict(reconciled_packet.get("routing_handoff", {})) == dict(current_packet.get("routing_handoff", {}))
        and dict(reconciled_packet.get("context_packet", {})) == dict(current_packet.get("context_packet", {}))
        and dict(reconciled_packet.get("evidence_pack", {})) == dict(current_packet.get("evidence_pack", {}))
    )


def _stabilize_direct_metrics(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    packet: Mapping[str, Any],
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
    build_evidence_pack: bool,
    hot_path: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    final_packet = dict(packet)
    final_metrics = dict(final_packet.get("packet_metrics", {})) if isinstance(final_packet.get("packet_metrics"), Mapping) else {}
    for _ in range(1 if hot_path else 4):
        direct_metrics = budgeting.estimate_packet_metrics(
            final_packet,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        if direct_metrics == dict(final_packet.get("packet_metrics", {})):
            break
        final_packet["packet_metrics"] = dict(direct_metrics)
        final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=direct_metrics)
        direct_quality = quality.summarize_packet_quality(
            packet_kind=packet_kind,
            packet_state=packet_state,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            packet_metrics=direct_metrics,
            final_payload=final_packet,
        )
        final_packet["packet_quality"] = dict(direct_quality)
        direct_handoff = routing.build_routing_handoff(
            packet_kind=packet_kind,
            packet_state=packet_state,
            retrieval_plan=retrieval_plan,
            packet_quality=direct_quality,
            final_payload=final_packet,
        )
        final_packet["routing_handoff"] = dict(direct_handoff)
        final_packet["context_packet"] = tooling_memory_contracts.build_context_packet(
            packet_kind=packet_kind,
            packet_state=packet_state,
            payload=final_packet,
        )
        if build_evidence_pack:
            final_packet["evidence_pack"] = tooling_memory_contracts.build_evidence_pack(
                packet_kind=packet_kind,
                packet_state=packet_state,
                payload=final_packet,
            )
        else:
            final_packet.pop("evidence_pack", None)
        final_metrics = direct_metrics
    return final_packet, final_metrics


def _compact_until_within_budget(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    packet: Mapping[str, Any],
    packet_metrics: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    final_packet = dict(packet)
    final_truth_metrics = dict(packet_metrics)
    for _ in range(3):
        compacted_packet = packet_compaction.compact_finalize_metadata(final_packet, budget_meta=budget_meta)
        if compacted_packet == final_packet:
            break
        final_packet = compacted_packet
        final_truth_metrics = budgeting.estimate_packet_metrics(
            final_packet,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        final_packet["packet_metrics"] = dict(final_truth_metrics)
        final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_truth_metrics)
        if bool(final_truth_metrics.get("within_budget")):
            break
    return final_packet, final_truth_metrics


def _stamp_within_budget_truth(packet: Mapping[str, Any], *, within_budget: bool) -> dict[str, Any]:
    final_packet = dict(packet)
    if isinstance(final_packet.get("packet_quality"), Mapping):
        packet_quality_payload = dict(final_packet.get("packet_quality", {}))
        packet_quality_payload["within_budget"] = within_budget
        final_packet["packet_quality"] = packet_quality_payload
    if isinstance(final_packet.get("routing_handoff"), Mapping):
        routing_handoff_payload = dict(final_packet.get("routing_handoff", {}))
        routing_handoff_payload["within_budget"] = within_budget
        if isinstance(routing_handoff_payload.get("packet_quality"), Mapping):
            handoff_quality_payload = dict(routing_handoff_payload.get("packet_quality", {}))
            handoff_quality_payload["within_budget"] = within_budget
            routing_handoff_payload["packet_quality"] = handoff_quality_payload
        if isinstance(routing_handoff_payload.get("optimization"), Mapping):
            handoff_optimization_payload = dict(routing_handoff_payload.get("optimization", {}))
            handoff_optimization_payload["within_budget"] = within_budget
            routing_handoff_payload["optimization"] = handoff_optimization_payload
        if isinstance(routing_handoff_payload.get("odylith_execution_profile"), Mapping):
            execution_profile_payload = dict(routing_handoff_payload.get("odylith_execution_profile", {}))
            if isinstance(execution_profile_payload.get("constraints"), Mapping):
                execution_constraints = dict(execution_profile_payload.get("constraints", {}))
                execution_constraints["within_budget"] = within_budget
                execution_profile_payload["constraints"] = execution_constraints
            routing_handoff_payload["odylith_execution_profile"] = execution_profile_payload
        final_packet["routing_handoff"] = routing_handoff_payload
    return final_packet


def _stabilize_full_packet_truth(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    final_packet = dict(packet)
    final_truth_metrics = budgeting.estimate_packet_metrics(
        final_packet,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    final_packet["packet_metrics"] = dict(final_truth_metrics)
    final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_truth_metrics)
    for _ in range(4):
        stabilized_metrics = budgeting.estimate_packet_metrics(
            final_packet,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        if stabilized_metrics == dict(final_packet.get("packet_metrics", {})):
            break
        final_packet["packet_metrics"] = dict(stabilized_metrics)
        final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=stabilized_metrics)
    return final_packet


__all__ = ["complete_packet", "finalize_packet_without_odylith"]
