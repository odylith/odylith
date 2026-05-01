"""Budget and metadata finalization for Context Engine packets."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import tooling_context_budgeting as budgeting
from odylith.runtime.context_engine import tooling_context_quality as quality
from odylith.runtime.context_engine import tooling_context_routing as routing
from odylith.runtime.memory import tooling_memory_contracts

_PROCESS_HOT_PATH_PACKET_QUALITY_CACHE: dict[str, dict[str, Any]] = {}
_PROCESS_HOT_PATH_ROUTING_HANDOFF_CACHE: dict[str, dict[str, Any]] = {}


def assemble_finalized_candidate(
    *,
    base_payload: Mapping[str, Any],
    packet_metrics: Mapping[str, Any],
    packet_quality: Mapping[str, Any],
    routing_handoff: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    evidence_pack: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = dict(base_payload)
    candidate["packet_metrics"] = dict(packet_metrics)
    candidate["packet_quality"] = dict(packet_quality)
    candidate["routing_handoff"] = dict(routing_handoff)
    candidate["context_packet"] = dict(context_packet)
    if evidence_pack:
        candidate["evidence_pack"] = dict(evidence_pack)
    else:
        candidate.pop("evidence_pack", None)
    return candidate


def sync_packet_budget_truncation(
    packet: Mapping[str, Any],
    *,
    packet_metrics: Mapping[str, Any],
) -> dict[str, Any]:
    synced = dict(packet)
    truncation = dict(synced.get("truncation", {})) if isinstance(synced.get("truncation"), Mapping) else {}
    packet_budget = dict(truncation.get("packet_budget", {})) if isinstance(truncation.get("packet_budget"), Mapping) else {}
    packet_budget["within_budget"] = bool(packet_metrics.get("within_budget"))
    packet_budget["estimated_bytes"] = int(packet_metrics.get("estimated_bytes", 0) or 0)
    packet_budget["estimated_tokens"] = int(packet_metrics.get("estimated_tokens", 0) or 0)
    packet_budget["max_bytes"] = int(packet_metrics.get("max_bytes", 0) or 0)
    packet_budget["max_tokens"] = int(packet_metrics.get("max_tokens", 0) or 0)
    truncation["packet_budget"] = packet_budget
    synced["truncation"] = truncation
    return synced


def _compact_hot_path_finalize_workstream_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    selected = selection.get("selected_workstream")
    if isinstance(selected, Mapping):
        compact_selected = {
            key: selected.get(key)
            for key in ("entity_id", "title", "status", "confidence", "reason")
            if selected.get(key) not in ("", [], {}, None)
        }
        if compact_selected:
            compact["selected_workstream"] = compact_selected
    for key in ("selection_state", "selection_reason", "selection_confidence"):
        if selection.get(key) not in ("", [], {}, None):
            compact[key] = selection.get(key)
    return compact


def prune_hot_path_finalize_retrieval_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    keep_keys = {
        "packet_kind",
        "packet_state",
        "anchor_quality",
        "guidance_coverage",
        "ambiguity_class",
        "evidence_consensus",
        "routing_confidence",
        "precision_score",
        "selected_counts",
        "selected_docs",
        "selected_tests",
        "selected_commands",
        "validation_bundle",
        "governance_obligations",
        "route_readiness",
        "execution_ready_reasons",
        "miss_recovery",
    }
    compact = {
        key: value
        for key, value in plan.items()
        if key in keep_keys and value not in ("", [], {}, None)
    }
    for profile_key in ("evidence_profile", "actionability_profile", "validation_profile"):
        if isinstance(plan.get(profile_key), Mapping):
            profile = {
                key: value
                for key, value in dict(plan.get(profile_key, {})).items()
                if key in {"score", "status", "direct_guidance_count", "actionable_guidance_count", "selected_test_count"}
                and value not in ("", [], {}, None)
            }
            if profile:
                compact[profile_key] = profile
    if isinstance(plan.get("selected_guidance_chunks"), list):
        compact_chunks: list[dict[str, Any]] = []
        for row in plan.get("selected_guidance_chunks", [])[:2]:
            if not isinstance(row, Mapping):
                continue
            compact_row = {
                key: row.get(key)
                for key in ("chunk_id", "title", "canonical_source", "risk_class", "match_tier", "read_path")
                if row.get(key) not in ("", [], {}, None)
            }
            actionability = row.get("actionability")
            if isinstance(actionability, Mapping):
                compact_actionability = {
                    key: actionability.get(key)
                    for key in ("actionable", "read_path", "signals")
                    if actionability.get(key) not in ("", [], {}, None)
                }
                if compact_actionability:
                    compact_row["actionability"] = compact_actionability
            if compact_row:
                compact_chunks.append(compact_row)
        if compact_chunks:
            compact["selected_guidance_chunks"] = compact_chunks
    return compact


def prune_hot_path_finalize_base_payload(
    *,
    packet_kind: str,
    packet_state: str,
    base_payload: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(base_payload)
    normalized_kind = str(packet_kind or "").strip()
    gated_hot_path = str(packet_state or "").strip().startswith("gated_")
    if normalized_kind not in {"impact", "governance_slice", "session_brief", "bootstrap_session"} or not gated_hot_path:
        return payload
    if bool(payload.get("_retain_hot_path_internal_context")):
        return payload
    keep_keys = {
        "resolved",
        "changed_paths",
        "explicit_paths",
        "selection_state",
        "selection_reason",
        "selection_confidence",
        "context_packet_state",
        "full_scan_recommended",
        "full_scan_reason",
        "fallback_scan",
        "narrowing_guidance",
        "turn_context",
        "target_resolution",
        "presentation_policy",
        "miss_recovery",
        "packet_budget",
        "truncation",
        "inferred_workstream",
        "adaptive_packet_profile",
        "guidance_behavior_summary",
        "discipline_summary",
    }
    if normalized_kind in {"impact", "governance_slice"}:
        keep_keys.add("intent")
    if normalized_kind == "governance_slice":
        keep_keys.update(
            {
                "validation_bundle",
                "governance_obligations",
                "surface_refs",
                "diagram_watch_gaps",
            }
        )
    elif normalized_kind in {"session_brief", "bootstrap_session"}:
        keep_keys.update(
            {
                "relevant_docs",
                "recommended_commands",
                "recommended_tests",
                "validation_bundle",
            }
        )
    compact = {
        key: value
        for key, value in payload.items()
        if key in keep_keys and value not in ("", [], {}, None)
    }
    if isinstance(payload.get("workstream_selection"), Mapping):
        compact_selection = _compact_hot_path_finalize_workstream_selection(
            dict(payload.get("workstream_selection", {}))
        )
        if compact_selection:
            compact["workstream_selection"] = compact_selection
    if isinstance(payload.get("retrieval_plan"), Mapping):
        compact_plan = prune_hot_path_finalize_retrieval_plan(dict(payload.get("retrieval_plan", {})))
        if compact_plan:
            compact["retrieval_plan"] = compact_plan
    return compact


def finalize_packet_metadata(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    base_payload: Mapping[str, Any],
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
    build_evidence_pack: bool = True,
    max_iterations: int = 8,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    packet_metrics: dict[str, Any] = {}
    packet_quality: dict[str, Any] = {}
    routing_handoff: dict[str, Any] = {}
    context_packet: dict[str, Any] = {}
    evidence_pack: dict[str, Any] = {}
    candidate: dict[str, Any] = {}
    for _ in range(max(1, int(max_iterations))):
        candidate = assemble_finalized_candidate(
            base_payload=base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff=routing_handoff,
            context_packet=context_packet,
            evidence_pack=evidence_pack,
        )
        candidate = sync_packet_budget_truncation(candidate, packet_metrics=packet_metrics)
        measured = budgeting.estimate_packet_metrics(
            candidate,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        measured_candidate = sync_packet_budget_truncation(
            assemble_finalized_candidate(
                base_payload=base_payload,
                packet_metrics=measured,
                packet_quality=packet_quality,
                routing_handoff=routing_handoff,
                context_packet=context_packet,
                evidence_pack=evidence_pack,
            ),
            packet_metrics=measured,
        )
        quality_payload = quality.summarize_packet_quality(
            packet_kind=packet_kind,
            packet_state=packet_state,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            packet_metrics=measured,
            final_payload=measured_candidate,
        )
        handoff_payload = routing.build_routing_handoff(
            packet_kind=packet_kind,
            packet_state=packet_state,
            retrieval_plan=retrieval_plan,
            packet_quality=quality_payload,
            final_payload=sync_packet_budget_truncation(
                assemble_finalized_candidate(
                    base_payload=base_payload,
                    packet_metrics=measured,
                    packet_quality=quality_payload,
                    routing_handoff=routing_handoff,
                    context_packet=context_packet,
                    evidence_pack=evidence_pack,
                ),
                packet_metrics=measured,
            ),
        )
        refreshed_candidate = sync_packet_budget_truncation(
            assemble_finalized_candidate(
                base_payload=base_payload,
                packet_metrics=measured,
                packet_quality=quality_payload,
                routing_handoff=handoff_payload,
                context_packet=context_packet,
                evidence_pack=evidence_pack,
            ),
            packet_metrics=measured,
        )
        context_payload = tooling_memory_contracts.build_context_packet(
            packet_kind=packet_kind,
            packet_state=packet_state,
            payload=refreshed_candidate,
        )
        evidence_payload = (
            tooling_memory_contracts.build_evidence_pack(
                packet_kind=packet_kind,
                packet_state=packet_state,
                payload=refreshed_candidate,
            )
            if build_evidence_pack
            else {}
        )
        if (
            measured == packet_metrics
            and quality_payload == packet_quality
            and handoff_payload == routing_handoff
            and context_payload == context_packet
            and evidence_payload == evidence_pack
        ):
            packet_metrics = measured
            packet_quality = quality_payload
            routing_handoff = handoff_payload
            context_packet = context_payload
            evidence_pack = evidence_payload
            break
        packet_metrics = measured
        packet_quality = quality_payload
        routing_handoff = handoff_payload
        context_packet = context_payload
        evidence_pack = evidence_payload
    candidate = assemble_finalized_candidate(
        base_payload=base_payload,
        packet_metrics=packet_metrics,
        packet_quality=packet_quality,
        routing_handoff=routing_handoff,
        context_packet=context_packet,
        evidence_pack=evidence_pack,
    )
    candidate = sync_packet_budget_truncation(candidate, packet_metrics=packet_metrics)
    return candidate, packet_metrics, packet_quality, routing_handoff


def finalize_packet_metadata_hot_path(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    base_payload: Mapping[str, Any],
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    working_base_payload = prune_hot_path_finalize_base_payload(
        packet_kind=packet_kind,
        packet_state=packet_state,
        base_payload=base_payload,
    )
    packet_metrics = budgeting.estimate_packet_metrics(
        working_base_payload,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    measured_candidate = sync_packet_budget_truncation(
        assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality={},
            routing_handoff={},
            context_packet={},
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    quality_cache_key = odylith_context_cache.fingerprint_payload(
        {
            "packet_kind": str(packet_kind or "").strip(),
            "packet_state": str(packet_state or "").strip(),
            "selection_state": str(selection_state or "").strip(),
            "full_scan_recommended": bool(full_scan_recommended),
            "retrieval_plan": dict(retrieval_plan),
            "packet_metrics": dict(packet_metrics),
            "final_payload": dict(measured_candidate),
        }
    )
    cached_packet_quality = _PROCESS_HOT_PATH_PACKET_QUALITY_CACHE.get(quality_cache_key)
    if cached_packet_quality is None:
        cached_packet_quality = quality.summarize_packet_quality(
            packet_kind=packet_kind,
            packet_state=packet_state,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            packet_metrics=packet_metrics,
            final_payload=measured_candidate,
        )
        _PROCESS_HOT_PATH_PACKET_QUALITY_CACHE[quality_cache_key] = dict(cached_packet_quality)
    packet_quality = dict(cached_packet_quality)
    handoff_candidate = sync_packet_budget_truncation(
        assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff={},
            context_packet={},
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    routing_cache_key = odylith_context_cache.fingerprint_payload(
        {
            "packet_kind": str(packet_kind or "").strip(),
            "packet_state": str(packet_state or "").strip(),
            "retrieval_plan": dict(retrieval_plan),
            "packet_quality": dict(packet_quality),
            "final_payload": dict(handoff_candidate),
        }
    )
    cached_routing_handoff = _PROCESS_HOT_PATH_ROUTING_HANDOFF_CACHE.get(routing_cache_key)
    if cached_routing_handoff is None:
        cached_routing_handoff = routing.build_routing_handoff(
            packet_kind=packet_kind,
            packet_state=packet_state,
            retrieval_plan=retrieval_plan,
            packet_quality=packet_quality,
            final_payload=handoff_candidate,
        )
        _PROCESS_HOT_PATH_ROUTING_HANDOFF_CACHE[routing_cache_key] = dict(cached_routing_handoff)
    routing_handoff = dict(cached_routing_handoff)
    context_candidate = sync_packet_budget_truncation(
        assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff=routing_handoff,
            context_packet={},
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    context_packet = tooling_memory_contracts.build_context_packet(
        packet_kind=packet_kind,
        packet_state=packet_state,
        payload=context_candidate,
    )
    final_candidate = sync_packet_budget_truncation(
        assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff=routing_handoff,
            context_packet=context_packet,
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    final_metrics = budgeting.estimate_packet_metrics(
        final_candidate,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    final_candidate["packet_metrics"] = dict(final_metrics)
    final_candidate = sync_packet_budget_truncation(final_candidate, packet_metrics=final_metrics)
    return final_candidate, final_metrics, packet_quality, routing_handoff


__all__ = [
    "assemble_finalized_candidate",
    "finalize_packet_metadata",
    "finalize_packet_metadata_hot_path",
    "prune_hot_path_finalize_base_payload",
    "prune_hot_path_finalize_retrieval_plan",
    "sync_packet_budget_truncation",
]
