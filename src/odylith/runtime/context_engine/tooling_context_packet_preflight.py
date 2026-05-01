"""Preflight routing and enrichment for Context Engine packet finalization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.discipline import runtime as discipline_runtime
from odylith.runtime.context_engine import tooling_context_packet_compaction as packet_compaction
from odylith.runtime.context_engine import tooling_context_packet_profile as packet_profile
from odylith.runtime.context_engine import tooling_context_retrieval as retrieval
from odylith.runtime.context_engine import tooling_context_routing as routing
from odylith.runtime.context_engine import tooling_guidance_catalog
from odylith.runtime.governance import guidance_behavior_runtime


@dataclass(frozen=True)
class PacketPreflight:
    packet_state: str
    full_scan_recommended: bool
    full_scan_reason: str
    source_recommended_commands: tuple[str, ...]
    recommended_commands: tuple[str, ...]
    effective_recommended_commands: tuple[str, ...]
    guidance_behavior_summary: dict[str, Any]
    discipline_summary: dict[str, Any]
    catalog: dict[str, Any]
    guidance_catalog_summary: dict[str, Any]
    retrieval_bundle: dict[str, Any]
    selected_guidance_chunks: list[dict[str, Any]]
    selected_workstreams: list[dict[str, Any]]
    retrieval_plan: dict[str, Any]
    optimization: dict[str, Any]
    adaptive_packet_profile: dict[str, Any]


def _summary_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _selected_workstreams(
    *,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selected = workstream_selection.get("selected_workstream")
    if isinstance(selected, Mapping) and str(selected.get("entity_id", "")).strip():
        return [dict(selected)]
    return [dict(row) for row in candidate_workstreams if isinstance(row, Mapping)]


def _selected_guidance_chunks(retrieval_bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = retrieval_bundle.get("selected_guidance_chunks", [])
    return [dict(row) for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def _preflight_actionability_score(
    *,
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    selected_test_count: int,
    selected_command_count: int,
) -> tuple[int, int, int]:
    direct_guidance_count = sum(
        1 for row in selected_guidance_chunks if str(row.get("match_tier", "")).strip() == "direct_path"
    )
    actionable_guidance_count = sum(
        1
        for row in selected_guidance_chunks
        if isinstance(row.get("actionability"), Mapping)
        and bool(dict(row.get("actionability", {})).get("actionable"))
    )
    score = 0
    if actionable_guidance_count > 0 and (direct_guidance_count > 0 or selected_test_count > 0 or selected_command_count > 0):
        score = 3
    elif actionable_guidance_count > 0 or direct_guidance_count > 0:
        score = 2
    elif selected_test_count > 0 or selected_command_count > 0:
        score = 1
    return score, direct_guidance_count, actionable_guidance_count


def _preflight_validation_score(*, selected_test_count: int, selected_command_count: int) -> int:
    if selected_test_count > 0 and selected_command_count > 0:
        return 3
    if selected_test_count > 0 or selected_command_count > 0:
        return 2
    return 0


def _build_retrieval_plan(
    *,
    packet_kind: str,
    packet_state: str,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    shared_only_input: bool,
    selection_state: str,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    docs: Sequence[str],
    recommended_tests: Sequence[Mapping[str, Any]],
    effective_recommended_commands: Sequence[str],
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    miss_recovery: Mapping[str, Any],
    guidance_catalog_summary: Mapping[str, Any],
    full_scan_reason: str,
) -> dict[str, Any]:
    return dict(
        routing.build_retrieval_plan(
            packet_kind=packet_kind,
            packet_state=packet_state,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            shared_only_input=shared_only_input,
            selection_state=selection_state,
            workstream_selection=workstream_selection,
            candidate_workstreams=candidate_workstreams,
            components=components,
            diagrams=diagrams,
            docs=docs,
            recommended_tests=recommended_tests,
            recommended_commands=effective_recommended_commands,
            selected_guidance_chunks=selected_guidance_chunks,
            miss_recovery=miss_recovery or {},
            guidance_catalog_summary=guidance_catalog_summary,
            full_scan_reason=full_scan_reason,
        )
    )


def build_packet_preflight(
    *,
    repo_root: Path,
    packet_kind: str,
    packet_state: str,
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
    engineering_notes: Mapping[str, Sequence[Mapping[str, Any]]],
    miss_recovery: Mapping[str, Any],
    full_scan_recommended: bool,
    full_scan_reason: str,
    session_id: str,
    family_hint: str,
    guidance_catalog: Mapping[str, Any] | None,
    optimization_snapshot: Mapping[str, Any] | None,
    delivery_profile: str,
) -> PacketPreflight:
    root = Path(repo_root).resolve()
    source_recommended_commands = tuple(str(token).strip() for token in recommended_commands if str(token).strip())
    guidance_behavior_summary = _summary_dict(
        guidance_behavior_runtime.summary_for_packet(
            repo_root=root,
            family_hint=family_hint,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            docs=docs,
            recommended_commands=source_recommended_commands,
        )
    )
    discipline_summary = _summary_dict(
        discipline_runtime.summary_for_packet(
            repo_root=root,
            family_hint=family_hint,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            docs=docs,
            recommended_commands=source_recommended_commands,
        )
    )
    staged_commands: tuple[str, ...] = source_recommended_commands
    if guidance_behavior_summary:
        staged_commands = tuple(
            guidance_behavior_runtime.commands_with_validator(
                source_recommended_commands,
                guidance_behavior_summary,
                limit=16,
            )
        )
    if discipline_summary:
        staged_commands = tuple(
            discipline_runtime.commands_with_validator(
                staged_commands,
                discipline_summary,
                limit=16,
            )
        )
    effective_recommended_commands = tuple(str(token).strip() for token in staged_commands if str(token).strip())
    catalog = (
        dict(guidance_catalog)
        if isinstance(guidance_catalog, Mapping)
        else tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    )
    selected_workstreams = _selected_workstreams(
        workstream_selection=workstream_selection,
        candidate_workstreams=candidate_workstreams,
    )
    retrieval_bundle = dict(
        retrieval.compact_retrieval_bundle(
            packet_kind=packet_kind,
            family_hint=family_hint,
            repo_root=root,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            docs=docs,
            recommended_commands=effective_recommended_commands,
            recommended_tests=recommended_tests,
            components=components,
            selected_workstreams=selected_workstreams,
            engineering_notes=engineering_notes,
            guidance_catalog=catalog,
            session_id=session_id,
            selection_state=selection_state,
            build_working_memory=not agent_runtime_contract.is_agent_hot_path_profile(delivery_profile),
        )
    )
    selected_guidance_chunks = _selected_guidance_chunks(retrieval_bundle)
    selected_test_count = len([row for row in recommended_tests if isinstance(row, Mapping)])
    selected_command_count = len([token for token in effective_recommended_commands if token])
    actionability_score, direct_guidance_count, actionable_guidance_count = _preflight_actionability_score(
        selected_guidance_chunks=selected_guidance_chunks,
        selected_test_count=selected_test_count,
        selected_command_count=selected_command_count,
    )
    validation_score = _preflight_validation_score(
        selected_test_count=selected_test_count,
        selected_command_count=selected_command_count,
    )
    guidance_catalog_summary = tooling_guidance_catalog.compact_catalog_summary(catalog)
    plan = _build_retrieval_plan(
        packet_kind=packet_kind,
        packet_state=packet_state,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        shared_only_input=shared_only_input,
        selection_state=selection_state,
        workstream_selection=workstream_selection,
        candidate_workstreams=candidate_workstreams,
        components=components,
        diagrams=diagrams,
        docs=docs,
        recommended_tests=recommended_tests,
        effective_recommended_commands=effective_recommended_commands,
        selected_guidance_chunks=selected_guidance_chunks,
        miss_recovery=miss_recovery,
        guidance_catalog_summary=guidance_catalog_summary,
        full_scan_reason=full_scan_reason,
    )
    grounded_ambiguous_write = routing.grounded_ambiguous_write_candidate(
        anchor_quality=str(plan.get("anchor_quality", "")).strip(),
        guidance_coverage=str(plan.get("guidance_coverage", "")).strip(),
        ambiguity_class=str(plan.get("ambiguity_class", "")).strip(),
        evidence_consensus=str(plan.get("evidence_consensus", "")).strip(),
        precision_score=_int_value(plan.get("precision_score")),
        actionability_score=actionability_score,
        validation_score=validation_score,
        direct_guidance_chunk_count=direct_guidance_count,
        actionable_guidance_chunk_count=actionable_guidance_count,
        selected_test_count=selected_test_count,
        selected_command_count=selected_command_count,
    )
    full_scan_reason_token = str(full_scan_reason or "").strip()
    guidance_behavior_validator_grounded = bool(
        guidance_behavior_summary
        and selected_command_count > 0
        and full_scan_reason_token in {"", "selection_ambiguous", "selection_none", "adaptive_full_scan_fallback"}
    )
    discipline_validator_grounded = bool(
        discipline_summary
        and selected_command_count > 0
        and full_scan_reason_token in {"", "selection_ambiguous", "selection_none", "adaptive_full_scan_fallback"}
    )
    if (
        str(packet_state or "").strip() == "gated_ambiguous"
        and bool(full_scan_recommended)
        and (
            (full_scan_reason_token == "selection_ambiguous" and grounded_ambiguous_write)
            or guidance_behavior_validator_grounded
            or discipline_validator_grounded
        )
    ):
        packet_state = "expanded"
        full_scan_recommended = False
        full_scan_reason = ""
        plan = _build_retrieval_plan(
            packet_kind=packet_kind,
            packet_state=packet_state,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            shared_only_input=shared_only_input,
            selection_state=selection_state,
            workstream_selection=workstream_selection,
            candidate_workstreams=candidate_workstreams,
            components=components,
            diagrams=diagrams,
            docs=docs,
            recommended_tests=recommended_tests,
            effective_recommended_commands=effective_recommended_commands,
            selected_guidance_chunks=selected_guidance_chunks,
            miss_recovery=miss_recovery,
            guidance_catalog_summary=guidance_catalog_summary,
            full_scan_reason=full_scan_reason,
        )
    optimization = dict(optimization_snapshot) if isinstance(optimization_snapshot, Mapping) else {}
    adaptive_profile = packet_profile.adaptive_packet_profile(
        packet_kind=packet_kind,
        packet_state=packet_state,
        selection_state=selection_state,
        retrieval_plan=plan,
        optimization_snapshot=optimization,
        full_scan_recommended=full_scan_recommended,
    )
    return PacketPreflight(
        packet_state=str(packet_state or "").strip(),
        full_scan_recommended=bool(full_scan_recommended),
        full_scan_reason=str(full_scan_reason or "").strip(),
        source_recommended_commands=source_recommended_commands,
        recommended_commands=staged_commands,
        effective_recommended_commands=effective_recommended_commands,
        guidance_behavior_summary=guidance_behavior_summary,
        discipline_summary=discipline_summary,
        catalog=catalog,
        guidance_catalog_summary=dict(guidance_catalog_summary),
        retrieval_bundle=retrieval_bundle,
        selected_guidance_chunks=selected_guidance_chunks,
        selected_workstreams=selected_workstreams,
        retrieval_plan=plan,
        optimization=optimization,
        adaptive_packet_profile=adaptive_profile,
    )


def enrich_packet_payload(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
    changed_paths: Sequence[str],
    components: Sequence[Mapping[str, Any]],
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    miss_recovery: Mapping[str, Any],
    delivery_profile: str,
    preflight: PacketPreflight,
    proof_state_payload: Mapping[str, Any],
) -> dict[str, Any]:
    packet_state = preflight.packet_state
    plan = preflight.retrieval_plan
    retrieval_bundle = preflight.retrieval_bundle
    enriched = dict(payload)
    if preflight.guidance_behavior_summary:
        enriched["guidance_behavior_summary"] = dict(preflight.guidance_behavior_summary)
    if preflight.discipline_summary:
        enriched["discipline_summary"] = dict(preflight.discipline_summary)
    effective_commands = guidance_behavior_runtime.commands_with_validator(
        enriched.get("recommended_commands") or preflight.recommended_commands,
        preflight.guidance_behavior_summary,
        limit=16,
    )
    effective_commands = discipline_runtime.commands_with_validator(
        effective_commands,
        preflight.discipline_summary,
        limit=16,
    )
    if effective_commands:
        enriched["recommended_commands"] = effective_commands
    enriched["delivery_profile"] = agent_runtime_contract.canonical_delivery_profile(delivery_profile)
    enriched["adaptive_packet_profile"] = dict(preflight.adaptive_packet_profile)
    prioritized_docs = retrieval_bundle.get("prioritized_docs", [])
    if isinstance(prioritized_docs, list) and isinstance(enriched.get("docs"), list):
        enriched["docs"] = [str(token).strip() for token in prioritized_docs if str(token).strip()]
    if isinstance(enriched.get("relevant_docs"), list):
        doc_prioritizer = (
            retrieval.prioritize_bootstrap_docs
            if str(packet_kind or "").strip() == "bootstrap_session"
            else retrieval.prioritize_docs
        )
        enriched["relevant_docs"] = doc_prioritizer(
            enriched.get("relevant_docs", []),
            selected_guidance_chunks=retrieval_bundle.get("selected_guidance_chunks", []),
            components=components,
            changed_paths=changed_paths,
        )
    impact_payload = enriched.get("impact", {})
    if isinstance(impact_payload, Mapping) and isinstance(impact_payload.get("docs"), list):
        impact_updated = dict(impact_payload)
        impact_doc_prioritizer = (
            retrieval.prioritize_bootstrap_docs
            if str(packet_kind or "").strip() in {"session_brief", "bootstrap_session"}
            else retrieval.prioritize_docs
        )
        impact_updated["docs"] = impact_doc_prioritizer(
            impact_updated.get("docs", []),
            selected_guidance_chunks=retrieval_bundle.get("selected_guidance_chunks", []),
            components=components,
            changed_paths=changed_paths,
        )
        impact_updated["guidance_brief"] = retrieval_bundle.get("guidance_brief", [])
        enriched["impact"] = impact_updated
    enriched.update(dict(proof_state_payload))
    enriched["retrieval_plan"] = plan
    enriched["guidance_brief"] = retrieval_bundle.get("guidance_brief", [])
    enriched["context_packet_state"] = packet_state
    enriched["full_scan_recommended"] = preflight.full_scan_recommended
    enriched["full_scan_reason"] = preflight.full_scan_reason
    if isinstance(miss_recovery, Mapping):
        miss_recovery_summary = dict(plan.get("miss_recovery", {})) if isinstance(plan.get("miss_recovery"), Mapping) else {}
        enriched["miss_recovery"] = packet_compaction.compact_finalize_miss_recovery(
            miss_recovery_summary,
            packet_kind=packet_kind,
        )
    enriched["narrowing_guidance"] = routing.build_narrowing_guidance(
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=preflight.full_scan_recommended,
        full_scan_reason=preflight.full_scan_reason,
        workstream_selection=workstream_selection,
        retrieval_plan=plan,
        final_payload=enriched,
    )
    if retrieval_bundle.get("working_memory_tiers"):
        enriched["working_memory_tiers"] = retrieval_bundle["working_memory_tiers"]
    else:
        enriched.pop("working_memory_tiers", None)
    return enriched


__all__ = [
    "PacketPreflight",
    "build_packet_preflight",
    "enrich_packet_payload",
]
