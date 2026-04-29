"""Packet-plane helpers for Odylith Context Engine context assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.common.value_coercion import mapping_copy as _mapping_value
from odylith.runtime.common.value_coercion import string_rows as _string_rows
from odylith.runtime.discipline import runtime as discipline_runtime
from odylith.runtime.evaluation import odylith_ablation
from odylith.runtime.context_engine import tooling_context_budgeting as budgeting
from odylith.runtime.context_engine import tooling_context_packet_compaction as packet_compaction
from odylith.runtime.context_engine import tooling_context_packet_finalization as packet_finalization
from odylith.runtime.context_engine import tooling_context_packet_profile as packet_profile
from odylith.runtime.memory import tooling_memory_contracts
from odylith.runtime.context_engine import tooling_context_quality as quality
from odylith.runtime.context_engine import tooling_context_retrieval as retrieval
from odylith.runtime.context_engine import tooling_context_routing as routing
from odylith.runtime.context_engine import tooling_guidance_catalog
from odylith.runtime.governance import delivery_intelligence_engine
from odylith.runtime.governance import guidance_behavior_runtime
from odylith.runtime.governance import proof_state


def _delivery_scope_lookup(repo_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Mapping[str, Any]]]:
    payload = delivery_intelligence_engine.load_delivery_intelligence_artifact(repo_root=repo_root)
    scopes = payload.get("scopes", []) if isinstance(payload.get("scopes"), list) else []
    indexes = payload.get("indexes", {}) if isinstance(payload.get("indexes"), Mapping) else {}
    scope_lookup = {
        str(row.get("scope_key", "")).strip(): dict(row)
        for row in scopes
        if isinstance(row, Mapping) and str(row.get("scope_key", "")).strip()
    }
    return scope_lookup, indexes


def _packet_proof_anchor_scope_keys(
    *,
    indexes: Mapping[str, Any],
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
) -> list[str]:
    rows: list[str] = []
    workstream_index = indexes.get("workstreams", {}) if isinstance(indexes.get("workstreams"), Mapping) else {}
    component_index = indexes.get("components", {}) if isinstance(indexes.get("components"), Mapping) else {}
    diagram_index = indexes.get("diagrams", {}) if isinstance(indexes.get("diagrams"), Mapping) else {}
    selected = workstream_selection.get("selected_workstream")
    if isinstance(selected, Mapping):
        token = str(selected.get("entity_id", "")).strip()
        if token and token in workstream_index:
            rows.append(str(workstream_index.get(token, "")).strip())
    for row in candidate_workstreams:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("entity_id", "")).strip()
        if token and token in workstream_index:
            rows.append(str(workstream_index.get(token, "")).strip())
    for row in components:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("component_id", row.get("entity_id", ""))).strip()
        if token and token in component_index:
            rows.append(str(component_index.get(token, "")).strip())
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("diagram_id", row.get("entity_id", ""))).strip()
        if token and token in diagram_index:
            rows.append(str(diagram_index.get(token, "")).strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for token in rows:
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _packet_proof_state(
    *,
    repo_root: Path,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected = workstream_selection.get("selected_workstream")
    has_candidate_anchor = bool(
        (isinstance(selected, Mapping) and str(selected.get("entity_id", "")).strip())
        or any(isinstance(row, Mapping) and str(row.get("entity_id", "")).strip() for row in candidate_workstreams)
        or any(
            isinstance(row, Mapping) and str(row.get("component_id", row.get("entity_id", ""))).strip()
            for row in components
        )
        or any(
            isinstance(row, Mapping) and str(row.get("diagram_id", row.get("entity_id", ""))).strip()
            for row in diagrams
        )
    )
    if not has_candidate_anchor:
        return proof_state.resolve_scope_collection_proof_state([])
    scope_lookup, indexes = _delivery_scope_lookup(repo_root)
    candidate_scope_keys = _packet_proof_anchor_scope_keys(
        indexes=indexes,
        workstream_selection=workstream_selection,
        candidate_workstreams=candidate_workstreams,
        components=components,
        diagrams=diagrams,
    )
    candidate_scopes = [
        scope_lookup[key]
        for key in candidate_scope_keys
        if key in scope_lookup and isinstance(scope_lookup[key], Mapping)
    ]
    return proof_state.resolve_scope_collection_proof_state(candidate_scopes)


def _odylith_switch_snapshot(*, repo_root: Path) -> dict[str, Any]:
    return dict(odylith_ablation.build_odylith_switch_snapshot(repo_root=Path(repo_root).resolve()))


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
        return packet_compaction.merge_guidance_rows(guidance_brief, detail_rows=[*impact_rows, *warm_rows, *packet_compaction.mapping_rows(fallback)])
    if impact_rows:
        return packet_compaction.merge_guidance_rows(impact_rows, detail_rows=[*warm_rows, *packet_compaction.mapping_rows(fallback)])
    if warm_rows:
        return packet_compaction.merge_guidance_rows(warm_rows, detail_rows=packet_compaction.mapping_rows(fallback))
    return packet_compaction.mapping_rows(fallback)


def _refresh_context_views(
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
    return refreshed, refreshed_plan


def _can_reuse_hot_path_context_views(
    *,
    packet_kind: str,
    build_working_memory_tiers: bool,
    payload: Mapping[str, Any],
) -> bool:
    if build_working_memory_tiers or str(packet_kind or "").strip() not in {"impact", "governance_slice"}:
        return False
    return bool(_mapping_value(payload.get("retrieval_plan")) and _mapping_value(payload.get("narrowing_guidance")))


def _reuse_hot_path_context_views(
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


def _finalize_packet_without_odylith(
    *,
    repo_root: Path,
    packet_kind: str,
    payload: Mapping[str, Any],
    packet_state: str,
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
    final_payload["odylith_switch"] = _odylith_switch_snapshot(repo_root=repo_root)
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


def finalize_packet(
    *,
    repo_root: Path,
    packet_kind: str,
    payload: Mapping[str, Any],
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
    session_id: str = "",
    family_hint: str = "",
    guidance_catalog: Mapping[str, Any] | None = None,
    optimization_snapshot: Mapping[str, Any] | None = None,
    delivery_profile: str = "full",
) -> dict[str, Any]:
    """Attach routing, retrieval, budgeting, and quality metadata to a packet."""

    root = Path(repo_root).resolve()
    odylith_switch = _odylith_switch_snapshot(repo_root=root)
    if not bool(odylith_switch.get("enabled", True)):
        return _finalize_packet_without_odylith(
            repo_root=root,
            packet_kind=packet_kind,
            payload=payload,
            packet_state=packet_state,
        )
    source_recommended_commands = tuple(
        str(token).strip() for token in recommended_commands if str(token).strip()
    )
    guidance_behavior_summary = guidance_behavior_runtime.summary_for_packet(
        repo_root=root,
        family_hint=family_hint,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        docs=docs,
        recommended_commands=source_recommended_commands,
    )
    discipline_summary = discipline_runtime.summary_for_packet(
        repo_root=root,
        family_hint=family_hint,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        docs=docs,
        recommended_commands=source_recommended_commands,
    )
    recommended_commands = source_recommended_commands
    if guidance_behavior_summary:
        recommended_commands = tuple(
            guidance_behavior_runtime.commands_with_validator(
                source_recommended_commands,
                guidance_behavior_summary,
                limit=16,
            )
        )
    if discipline_summary:
        recommended_commands = tuple(
            discipline_runtime.commands_with_validator(
                recommended_commands,
                discipline_summary,
                limit=16,
            )
        )
    effective_recommended_commands = tuple(
        str(token).strip() for token in recommended_commands if str(token).strip()
    )
    catalog = (
        dict(guidance_catalog)
        if isinstance(guidance_catalog, Mapping)
        else tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    )
    selected = workstream_selection.get("selected_workstream")
    selected_workstreams = (
        [dict(selected)]
        if isinstance(selected, Mapping) and str(selected.get("entity_id", "")).strip()
        else [dict(row) for row in candidate_workstreams if isinstance(row, Mapping)]
    )
    retrieval_bundle = retrieval.compact_retrieval_bundle(
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
    selected_guidance_chunks = (
        [dict(row) for row in retrieval_bundle.get("selected_guidance_chunks", []) if isinstance(row, Mapping)]
        if isinstance(retrieval_bundle.get("selected_guidance_chunks"), list)
        else []
    )
    direct_guidance_chunk_count = sum(
        1 for row in selected_guidance_chunks if str(row.get("match_tier", "")).strip() == "direct_path"
    )
    actionable_guidance_chunk_count = sum(
        1
        for row in selected_guidance_chunks
        if isinstance(row.get("actionability"), Mapping)
        and bool(dict(row.get("actionability", {})).get("actionable"))
    )
    selected_test_count = len([row for row in recommended_tests if isinstance(row, Mapping)])
    selected_command_count = len([str(token).strip() for token in effective_recommended_commands if str(token).strip()])
    preflight_actionability_score = 0
    if actionable_guidance_chunk_count > 0 and (direct_guidance_chunk_count > 0 or selected_test_count > 0 or selected_command_count > 0):
        preflight_actionability_score = 3
    elif actionable_guidance_chunk_count > 0 or direct_guidance_chunk_count > 0:
        preflight_actionability_score = 2
    elif selected_test_count > 0 or selected_command_count > 0:
        preflight_actionability_score = 1
    preflight_validation_score = 0
    if selected_test_count > 0 and selected_command_count > 0:
        preflight_validation_score = 3
    elif selected_test_count > 0 or selected_command_count > 0:
        preflight_validation_score = 2
    guidance_catalog_summary = tooling_guidance_catalog.compact_catalog_summary(catalog)
    plan = routing.build_retrieval_plan(
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
    grounded_ambiguous_write = routing.grounded_ambiguous_write_candidate(
        anchor_quality=str(plan.get("anchor_quality", "")).strip(),
        guidance_coverage=str(plan.get("guidance_coverage", "")).strip(),
        ambiguity_class=str(plan.get("ambiguity_class", "")).strip(),
        evidence_consensus=str(plan.get("evidence_consensus", "")).strip(),
        precision_score=_int_value(plan.get("precision_score")),
        actionability_score=preflight_actionability_score,
        validation_score=preflight_validation_score,
        direct_guidance_chunk_count=direct_guidance_chunk_count,
        actionable_guidance_chunk_count=actionable_guidance_chunk_count,
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
        plan = routing.build_retrieval_plan(
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
    optimization = dict(optimization_snapshot) if isinstance(optimization_snapshot, Mapping) else {}
    adaptive_packet_profile = packet_profile.adaptive_packet_profile(
        packet_kind=packet_kind,
        packet_state=packet_state,
        selection_state=selection_state,
        retrieval_plan=plan,
        optimization_snapshot=optimization,
        full_scan_recommended=full_scan_recommended,
    )
    enriched = dict(payload)
    if guidance_behavior_summary:
        enriched["guidance_behavior_summary"] = dict(guidance_behavior_summary)
    if discipline_summary:
        enriched["discipline_summary"] = dict(discipline_summary)
    effective_commands = guidance_behavior_runtime.commands_with_validator(
        enriched.get("recommended_commands") or recommended_commands,
        guidance_behavior_summary,
        limit=16,
    )
    effective_commands = discipline_runtime.commands_with_validator(
        effective_commands,
        discipline_summary,
        limit=16,
    )
    if effective_commands:
        enriched["recommended_commands"] = effective_commands
    enriched["delivery_profile"] = agent_runtime_contract.canonical_delivery_profile(delivery_profile)
    enriched["adaptive_packet_profile"] = dict(adaptive_packet_profile)
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
    enriched.update(
        _packet_proof_state(
            repo_root=root,
            workstream_selection=workstream_selection,
            candidate_workstreams=candidate_workstreams,
            components=components,
            diagrams=diagrams,
        )
    )
    enriched["retrieval_plan"] = plan
    enriched["guidance_brief"] = retrieval_bundle.get("guidance_brief", [])
    enriched["context_packet_state"] = str(packet_state or "").strip()
    enriched["full_scan_recommended"] = bool(full_scan_recommended)
    enriched["full_scan_reason"] = str(full_scan_reason or "").strip()
    if isinstance(miss_recovery, Mapping):
        miss_recovery_summary = (
            dict(plan.get("miss_recovery", {}))
            if isinstance(plan.get("miss_recovery"), Mapping)
            else {}
        )
        enriched["miss_recovery"] = packet_compaction.compact_finalize_miss_recovery(
            miss_recovery_summary,
            packet_kind=packet_kind,
        )
    enriched["narrowing_guidance"] = routing.build_narrowing_guidance(
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=full_scan_recommended,
        full_scan_reason=full_scan_reason,
        workstream_selection=workstream_selection,
        retrieval_plan=plan,
        final_payload=enriched,
    )
    if retrieval_bundle.get("working_memory_tiers"):
        enriched["working_memory_tiers"] = retrieval_bundle["working_memory_tiers"]
    else:
        enriched.pop("working_memory_tiers", None)
    budget_meta = budgeting.packet_budget(packet_kind=packet_kind, packet_state=packet_state)
    working_budget = packet_profile.apply_adaptive_budget_profile(
        packet_profile.content_budget(
            budget_meta,
            trim_order_paths=packet_profile.reorder_trim_paths(
                packet_kind=packet_kind,
                packet_state=packet_state,
                selection_state=selection_state,
                retrieval_plan=plan,
                adaptive_packet_profile=adaptive_packet_profile,
            ),
        ),
        adaptive_packet_profile=adaptive_packet_profile,
    )
    build_evidence_pack = not agent_runtime_contract.is_agent_hot_path_profile(delivery_profile)
    hot_path = not build_evidence_pack
    final_packet: dict[str, Any] = {}
    final_metrics: dict[str, Any] = {}
    final_plan: dict[str, Any] = plan
    budget_truncation: dict[str, Any] = {}
    hot_path_context_views = {
        "retrieval_plan": dict(plan),
        "guidance_brief": [dict(row) for row in retrieval_bundle.get("guidance_brief", []) if isinstance(row, Mapping)]
        if isinstance(retrieval_bundle.get("guidance_brief"), list)
        else [],
        "narrowing_guidance": dict(enriched.get("narrowing_guidance", {}))
        if isinstance(enriched.get("narrowing_guidance"), Mapping)
        else {},
    }
    for retry_index in range(3):
        trimmed, _trim_budget, _content_metrics, budget_truncation = budgeting.apply_packet_budget(
            enriched,
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
        if _can_reuse_hot_path_context_views(
            packet_kind=packet_kind,
            build_working_memory_tiers=build_evidence_pack,
            payload=base_payload,
        ):
            base_payload, final_plan = _reuse_hot_path_context_views(
                payload=base_payload,
                retrieval_plan=hot_path_context_views["retrieval_plan"],
                guidance_brief=hot_path_context_views["guidance_brief"],
                narrowing_guidance=hot_path_context_views["narrowing_guidance"],
            )
        else:
            base_payload, final_plan = _refresh_context_views(
                repo_root=root,
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
    final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_metrics)
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
            retrieval_plan=final_plan,
            build_evidence_pack=build_evidence_pack,
            max_iterations=1 if hot_path else 8,
        )
        if isinstance(final_packet.get("packet_metrics"), Mapping):
            final_metrics = dict(final_packet.get("packet_metrics", {}))
            final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_metrics)
    if not hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        for _ in range(3):
            reconciled_packet, reconciled_metrics, _reconciled_quality, _reconciled_handoff = packet_finalization.finalize_packet_metadata(
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget_meta=budget_meta,
                base_payload=final_packet,
                selection_state=selection_state,
                full_scan_recommended=full_scan_recommended,
                retrieval_plan=final_plan,
                build_evidence_pack=build_evidence_pack,
                max_iterations=1 if hot_path else 8,
            )
            reconciled_packet = packet_finalization.sync_packet_budget_truncation(
                reconciled_packet,
                packet_metrics=reconciled_metrics,
            )
            current_metrics = dict(final_packet.get("packet_metrics", {}))
            current_quality = dict(final_packet.get("packet_quality", {}))
            current_handoff = dict(final_packet.get("routing_handoff", {}))
            current_context_packet = dict(final_packet.get("context_packet", {}))
            current_evidence_pack = dict(final_packet.get("evidence_pack", {}))
            if (
                reconciled_metrics == current_metrics
                and dict(reconciled_packet.get("packet_quality", {})) == current_quality
                and dict(reconciled_packet.get("routing_handoff", {})) == current_handoff
                and dict(reconciled_packet.get("context_packet", {})) == current_context_packet
                and dict(reconciled_packet.get("evidence_pack", {})) == current_evidence_pack
            ):
                break
            final_packet = reconciled_packet
            final_metrics = reconciled_metrics
    if hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        final_metrics = dict(final_packet.get("packet_metrics", {}))
    elif isinstance(final_packet.get("packet_metrics"), Mapping):
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
                retrieval_plan=final_plan,
                packet_metrics=direct_metrics,
                final_payload=final_packet,
            )
            final_packet["packet_quality"] = dict(direct_quality)
            direct_handoff = routing.build_routing_handoff(
                packet_kind=packet_kind,
                packet_state=packet_state,
                retrieval_plan=final_plan,
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
    final_packet["packet_metrics"] = dict(final_truth_metrics)
    final_packet = packet_finalization.sync_packet_budget_truncation(final_packet, packet_metrics=final_truth_metrics)
    final_within_budget = bool(final_truth_metrics.get("within_budget"))
    if isinstance(final_packet.get("packet_quality"), Mapping):
        packet_quality_payload = dict(final_packet.get("packet_quality", {}))
        packet_quality_payload["within_budget"] = final_within_budget
        final_packet["packet_quality"] = packet_quality_payload
    if isinstance(final_packet.get("routing_handoff"), Mapping):
        routing_handoff_payload = dict(final_packet.get("routing_handoff", {}))
        routing_handoff_payload["within_budget"] = final_within_budget
        if isinstance(routing_handoff_payload.get("packet_quality"), Mapping):
            handoff_quality_payload = dict(routing_handoff_payload.get("packet_quality", {}))
            handoff_quality_payload["within_budget"] = final_within_budget
            routing_handoff_payload["packet_quality"] = handoff_quality_payload
        if isinstance(routing_handoff_payload.get("optimization"), Mapping):
            handoff_optimization_payload = dict(routing_handoff_payload.get("optimization", {}))
            handoff_optimization_payload["within_budget"] = final_within_budget
            routing_handoff_payload["optimization"] = handoff_optimization_payload
        if isinstance(routing_handoff_payload.get("odylith_execution_profile"), Mapping):
            execution_profile_payload = dict(routing_handoff_payload.get("odylith_execution_profile", {}))
            if isinstance(execution_profile_payload.get("constraints"), Mapping):
                execution_constraints = dict(execution_profile_payload.get("constraints", {}))
                execution_constraints["within_budget"] = final_within_budget
                execution_profile_payload["constraints"] = execution_constraints
            routing_handoff_payload["odylith_execution_profile"] = execution_profile_payload
        final_packet["routing_handoff"] = routing_handoff_payload
    if not hot_path:
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


__all__ = ["finalize_packet"]
