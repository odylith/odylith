"""Context-view refresh and reuse helpers for packet finalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import mapping_copy as _mapping_value
from odylith.runtime.common.value_coercion import string_rows as _string_rows
from odylith.runtime.context_engine import tooling_context_packet_compaction as packet_compaction
from odylith.runtime.context_engine import tooling_context_retrieval as retrieval
from odylith.runtime.context_engine import tooling_context_routing as routing


def _guidance_brief_limit(packet_kind: str) -> int:
    if str(packet_kind or "").strip() == "session_brief":
        return 3
    if str(packet_kind or "").strip() == "bootstrap_session":
        return 2
    if str(packet_kind or "").strip() == "governance_slice":
        return 2
    return 4


def _retained_components(payload: Mapping[str, Any], fallback: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    for key in ("components",):
        rows = packet_compaction.mapping_rows(payload.get(key))
        if rows:
            return rows
    for key in ("impact_summary", "impact"):
        rows = packet_compaction.mapping_rows(packet_compaction.nested_mapping(payload, key).get("components"))
        if rows:
            return rows
    return packet_compaction.mapping_rows(fallback)


def _retained_diagrams(payload: Mapping[str, Any], fallback: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    for key in ("diagrams",):
        rows = packet_compaction.mapping_rows(payload.get(key))
        if rows:
            return rows
    for key in ("impact_summary", "impact"):
        rows = packet_compaction.mapping_rows(packet_compaction.nested_mapping(payload, key).get("diagrams"))
        if rows:
            return rows
    return packet_compaction.mapping_rows(fallback)


def _retained_docs(payload: Mapping[str, Any], fallback: Sequence[str]) -> list[str]:
    for key in ("docs", "relevant_docs"):
        rows = _string_rows(payload.get(key))
        if rows:
            return rows
    for key in ("impact_summary", "impact"):
        rows = _string_rows(packet_compaction.nested_mapping(payload, key).get("docs"))
        if rows:
            return rows
    return _string_rows(fallback)


def _retained_commands(payload: Mapping[str, Any], fallback: Sequence[str]) -> list[str]:
    rows = _string_rows(payload.get("recommended_commands"))
    if rows:
        return rows
    for key in ("impact_summary", "impact"):
        rows = _string_rows(packet_compaction.nested_mapping(payload, key).get("recommended_commands"))
        if rows:
            return rows
    return _string_rows(fallback)


def _retained_tests(payload: Mapping[str, Any], fallback: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = packet_compaction.mapping_rows(payload.get("recommended_tests"))
    if rows:
        return rows
    for key in ("impact_summary", "impact"):
        rows = packet_compaction.mapping_rows(packet_compaction.nested_mapping(payload, key).get("recommended_tests"))
        if rows:
            return rows
    return packet_compaction.mapping_rows(fallback)


def _retained_workstreams(
    payload: Mapping[str, Any],
    *,
    workstream_selection: Mapping[str, Any],
    fallback: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selection = _mapping_value(payload.get("workstream_selection")) or _mapping_value(workstream_selection)
    selected = _mapping_value(selection.get("selected_workstream"))
    if str(selected.get("entity_id", "")).strip():
        return [selected]
    rows = packet_compaction.mapping_rows(payload.get("candidate_workstreams"))
    if rows:
        return rows
    return packet_compaction.mapping_rows(fallback)


def _retained_guidance(
    payload: Mapping[str, Any],
    fallback: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    retrieval_plan = _mapping_value(payload.get("retrieval_plan"))
    rows = packet_compaction.mapping_rows(retrieval_plan.get("selected_guidance_chunks"))
    guidance_brief = packet_compaction.mapping_rows(payload.get("guidance_brief"))
    impact_rows: list[dict[str, Any]] = []
    for key in ("impact_summary", "impact"):
        impact_rows.extend(packet_compaction.mapping_rows(packet_compaction.nested_mapping(payload, key).get("guidance_brief")))
    warm = packet_compaction.nested_mapping(packet_compaction.nested_mapping(payload, "working_memory_tiers"), "warm")
    warm_rows = packet_compaction.mapping_rows(warm.get("guidance_chunks"))
    detail_rows = [*guidance_brief, *impact_rows, *warm_rows, *packet_compaction.mapping_rows(fallback)]
    if rows:
        return packet_compaction.merge_guidance_rows(rows, detail_rows=detail_rows)
    if guidance_brief:
        return packet_compaction.merge_guidance_rows(
            guidance_brief,
            detail_rows=[*impact_rows, *warm_rows, *packet_compaction.mapping_rows(fallback)],
        )
    if impact_rows:
        return packet_compaction.merge_guidance_rows(
            impact_rows,
            detail_rows=[*warm_rows, *packet_compaction.mapping_rows(fallback)],
        )
    if warm_rows:
        return packet_compaction.merge_guidance_rows(warm_rows, detail_rows=packet_compaction.mapping_rows(fallback))
    return packet_compaction.mapping_rows(fallback)


def refresh_context_views(
    *,
    repo_root: Path,
    packet_kind: str,
    packet_state: str,
    payload: Mapping[str, Any],
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    shared_only_input: bool,
    selection_state: str,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    docs: Sequence[str],
    recommended_commands: Sequence[str],
    recommended_tests: Sequence[Mapping[str, Any]],
    fallback_guidance_chunks: Sequence[Mapping[str, Any]],
    miss_recovery: Mapping[str, Any],
    guidance_catalog_summary: Mapping[str, Any],
    full_scan_recommended: bool,
    full_scan_reason: str,
    session_id: str,
    build_working_memory_tiers: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    refreshed = dict(payload)
    retained_workstreams = _retained_workstreams(
        refreshed,
        workstream_selection=workstream_selection,
        fallback=candidate_workstreams,
    )
    retained_components = _retained_components(refreshed, components)
    retained_diagrams = _retained_diagrams(refreshed, diagrams)
    retained_docs = _retained_docs(refreshed, docs)
    retained_commands = _string_rows(recommended_commands)
    retained_tests = _retained_tests(refreshed, recommended_tests)
    if str(packet_kind or "").strip() == "bootstrap_session" and str(packet_state or "").strip().startswith("gated_"):
        retained_tests = packet_compaction.compact_finalize_test_rows(retained_tests, limit=1)
    retained_guidance = _retained_guidance(refreshed, fallback_guidance_chunks)
    refreshed_plan = routing.build_retrieval_plan(
        packet_kind=packet_kind,
        packet_state=packet_state,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        shared_only_input=shared_only_input,
        selection_state=selection_state,
        workstream_selection=workstream_selection,
        candidate_workstreams=retained_workstreams,
        components=retained_components,
        diagrams=retained_diagrams,
        docs=retained_docs,
        recommended_tests=retained_tests,
        recommended_commands=retained_commands,
        selected_guidance_chunks=retained_guidance,
        miss_recovery=miss_recovery,
        guidance_catalog_summary=guidance_catalog_summary,
        full_scan_reason=full_scan_reason,
    )
    refreshed["retrieval_plan"] = refreshed_plan
    refreshed["guidance_brief"] = retrieval.compact_guidance_brief(
        retained_guidance,
        limit=_guidance_brief_limit(packet_kind),
    )
    refreshed["narrowing_guidance"] = routing.build_narrowing_guidance(
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=full_scan_recommended,
        full_scan_reason=full_scan_reason,
        workstream_selection=workstream_selection,
        retrieval_plan=refreshed_plan,
        final_payload=refreshed,
    )
    if build_working_memory_tiers:
        refreshed["working_memory_tiers"] = retrieval.build_working_memory_tiers(
            packet_kind=packet_kind,
            repo_root=repo_root,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            docs=retained_docs,
            recommended_commands=retained_commands,
            recommended_tests=retained_tests,
            components=retained_components,
            selected_workstreams=retained_workstreams,
            selected_guidance_chunks=retained_guidance,
            session_id=session_id,
            selection_state=selection_state,
        )
    else:
        refreshed.pop("working_memory_tiers", None)
    return refreshed, dict(refreshed_plan)


def can_reuse_hot_path_context_views(
    *,
    packet_kind: str,
    build_working_memory_tiers: bool,
    payload: Mapping[str, Any],
) -> bool:
    if build_working_memory_tiers or str(packet_kind or "").strip() not in {"impact", "governance_slice"}:
        return False
    return bool(_mapping_value(payload.get("retrieval_plan")) and _mapping_value(payload.get("narrowing_guidance")))


def reuse_hot_path_context_views(
    *,
    payload: Mapping[str, Any],
    retrieval_plan: Mapping[str, Any],
    guidance_brief: Sequence[Mapping[str, Any]],
    narrowing_guidance: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    reused = dict(payload)
    reused["retrieval_plan"] = dict(retrieval_plan)
    reused["guidance_brief"] = [dict(row) for row in guidance_brief if isinstance(row, Mapping)]
    reused["narrowing_guidance"] = dict(narrowing_guidance)
    reused.pop("working_memory_tiers", None)
    return reused, dict(retrieval_plan)


__all__ = [
    "can_reuse_hot_path_context_views",
    "refresh_context_views",
    "reuse_hot_path_context_views",
]
