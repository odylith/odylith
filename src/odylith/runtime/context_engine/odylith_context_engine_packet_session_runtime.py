"""Odylith Context Engine Packet Session Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import odylith_context_engine_grounding_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_core_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_summary_runtime
from odylith.runtime.context_engine import session_bootstrap_payload_compactor
from odylith.runtime.context_engine import tooling_context_packet_builder
from odylith.runtime.context_engine import turn_context_runtime

_hot_path_workstream_selection = odylith_context_engine_hot_path_packet_core_runtime._hot_path_workstream_selection
build_impact_report = odylith_context_engine_grounding_runtime.build_impact_report

def build_session_brief(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    use_working_tree: bool = False,
    working_tree_scope: str = "session",
    runtime_mode: str = "auto",
    session_id: str = "",
    workstream: str = "",
    generated_surfaces: Sequence[str] = (),
    intent: str = "",
    visible_text: Sequence[str] = (),
    active_tab: str = "",
    user_turn_id: str = "",
    supersedes_turn_id: str = "",
    claim_mode: str = "shared",
    claimed_paths: Sequence[str] = (),
    lease_seconds: int = 15 * 60,
    delivery_profile: str = "full",
    family_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    impact_override: Mapping[str, Any] | None = None,
    retain_impact_internal_context: bool | None = None,
    skip_impact_runtime_warmup: bool = False,
    compact_delivery: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}
    hot_path = context_engine_store._delivery_profile_hot_path(delivery_profile)
    normalized_turn_context = turn_context_runtime.normalize_turn_context(
        intent=intent,
        surfaces=generated_surfaces,
        visible_text=visible_text,
        active_tab=active_tab,
        user_turn_id=user_turn_id,
        supersedes_turn_id=supersedes_turn_id,
    )
    semantic_intent = turn_context_runtime.operator_ask_text(normalized_turn_context) or str(intent or "").strip()
    stage_started = time.perf_counter()
    guidance_catalog = context_engine_store.tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    optimization_snapshot = {} if hot_path else context_engine_store.load_runtime_optimization_snapshot(repo_root=root)
    stage_timings["guidance_catalog"] = context_engine_store._elapsed_stage_ms(stage_started)
    stage_started = time.perf_counter()
    effective_session_id = agent_runtime_contract.fallback_session_token(session_id)
    path_scope = context_engine_store._resolve_changed_path_scope_context(
        repo_root=root,
        explicit_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=effective_session_id,
        claimed_paths=claimed_paths,
        intent=intent,
    )
    stage_timings["path_scope"] = context_engine_store._elapsed_stage_ms(stage_started)
    effective_paths = list(path_scope["analysis_paths"])
    explicit = list(path_scope["explicit_paths"])
    explicit_claims = list(path_scope["explicit_claim_paths"])
    if isinstance(impact_override, Mapping):
        impact = dict(impact_override)
        stage_timings["impact_reused"] = 0.0
    else:
        retain_internal_context = (
            hot_path if retain_impact_internal_context is None else bool(retain_impact_internal_context)
        )
        stage_started = time.perf_counter()
        impact_kwargs = {
            "repo_root": root,
            "changed_paths": changed_paths,
            "use_working_tree": use_working_tree,
            "working_tree_scope": working_tree_scope,
            "session_id": effective_session_id,
            "claimed_paths": claimed_paths,
            "runtime_mode": runtime_mode,
            "intent": semantic_intent,
            "delivery_profile": delivery_profile,
            "family_hint": family_hint,
            "workstream_hint": workstream,
            "validation_command_hints": validation_command_hints,
            "retain_hot_path_internal_context": retain_internal_context,
            "guidance_catalog_snapshot": guidance_catalog,
            "optimization_snapshot": optimization_snapshot,
            "skip_runtime_warmup": bool(skip_impact_runtime_warmup),
            "finalize_packet": not hot_path,
        }
        try:
            impact = build_impact_report(**impact_kwargs)
        except TypeError as exc:
            message = str(exc)
            if "skip_runtime_warmup" not in message and "finalize_packet" not in message:
                raise
            impact_kwargs.pop("skip_runtime_warmup", None)
            impact_kwargs.pop("finalize_packet", None)
            impact = build_impact_report(**impact_kwargs)
        stage_timings["impact"] = context_engine_store._elapsed_stage_ms(stage_started)
    if isinstance(impact.get("changed_paths"), list):
        effective_paths = [str(token) for token in impact.get("changed_paths", []) if str(token).strip()]
    candidate_workstreams = (
        [dict(row) for row in impact.get("candidate_workstreams", []) if isinstance(row, Mapping)]
        if isinstance(impact.get("candidate_workstreams"), list)
        else []
    )
    stage_started = time.perf_counter()
    impact_selection = _hot_path_workstream_selection(impact) if hot_path else {}
    if hot_path and str(workstream or "").strip():
        explicit_workstream = str(workstream or "").strip().upper()
        selection_reason = f"Using explicit workstream override `{explicit_workstream}`."
        selection = {
            "state": "explicit",
            "reason": selection_reason,
            "why_selected": selection_reason,
            "selected_workstream": {"entity_id": explicit_workstream},
            "top_candidate": {"entity_id": explicit_workstream},
            "score_gap": None,
            "confidence": "explicit",
            "candidate_count": len(candidate_workstreams),
            "ambiguity_class": "explicit",
            "strong_candidate_count": 1,
            "competing_candidates": [],
        }
    elif hot_path and impact_selection:
        selection = impact_selection
    else:
        try:
            connection = context_engine_store._connect(root)
        except RuntimeError:
            explicit_workstream = str(workstream or "").strip().upper()
            top_candidate = dict(candidate_workstreams[0]) if candidate_workstreams else {}
            competing_candidates = [dict(row) for row in candidate_workstreams[1:4]]
            selection_reason = (
                f"Explicit workstream `{explicit_workstream}` cannot resolve because runtime projections are unavailable."
                if explicit_workstream
                else "Runtime projections are unavailable for deterministic session routing."
            )
            selection = {
                "state": "none",
                "reason": selection_reason,
                "why_selected": selection_reason,
                "selected_workstream": {},
                "top_candidate": top_candidate if not explicit_workstream else {},
                "score_gap": None,
                "confidence": "none",
                "candidate_count": len(candidate_workstreams),
                "ambiguity_class": "runtime_unavailable",
                "strong_candidate_count": sum(
                    1
                    for row in candidate_workstreams
                    if int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0) > 0
                ),
                "competing_candidates": competing_candidates,
            }
        else:
            try:
                judgment_workstream_hint = context_engine_store._load_judgment_workstream_hint(repo_root=root, changed_paths=effective_paths)
                selection = context_engine_store._workstream_selection(
                    connection=connection,
                    candidates=candidate_workstreams,
                    explicit_workstream=str(workstream or "").strip(),
                    judgment_hint=judgment_workstream_hint,
                )
            finally:
                connection.close()
    stage_timings["selection"] = context_engine_store._elapsed_stage_ms(stage_started)
    selection_state = str(selection.get("state", "")).strip()
    selected_workstream = (
        dict(selection.get("selected_workstream", {}))
        if isinstance(selection.get("selected_workstream"), Mapping)
        else {}
    )
    inferred_workstream = (
        str(selected_workstream.get("entity_id", "")).strip().upper()
        if selection_state in {"explicit", "inferred_confident"}
        else ""
    )
    dossier = (
        context_engine_store.load_context_dossier(repo_root=root, ref=inferred_workstream, kind="workstream", runtime_mode=runtime_mode)
        if inferred_workstream and not hot_path
        else {"resolved": False}
    )
    auto_claim_paths = list(explicit)
    stage_started = time.perf_counter()
    explicit_claim_paths = [str(token).strip() for token in explicit_claims if str(token).strip()]
    track_hot_path_session_state = bool(
        hot_path and (str(session_id or "").strip() or explicit_claim_paths or generated_surfaces)
    )
    if hot_path:
        session_state = {
            "session_id": effective_session_id if track_hot_path_session_state else "",
            "workstream": inferred_workstream,
            "intent": str(intent or "").strip(),
            "turn_context": turn_context_runtime.compact_turn_context(normalized_turn_context),
            "claim_mode": context_engine_store._normalize_claim_mode(claim_mode),
            "explicit_paths": explicit,
            "claimed_paths": context_engine_store._dedupe_strings([*auto_claim_paths, *explicit_claim_paths, *effective_paths]),
            "analysis_paths": effective_paths,
            "generated_surfaces": context_engine_store._dedupe_strings([str(token).strip() for token in generated_surfaces if str(token).strip()]),
            "selection_state": selection_state,
            "selection_reason": str(selection.get("reason", "")).strip(),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "branch_name": context_engine_store._git_branch_name(repo_root=root) if track_hot_path_session_state else "",
            "head_oid": context_engine_store._git_head_oid(repo_root=root) if track_hot_path_session_state else "",
            "updated_utc": context_engine_store._utc_now(),
        }
        active_sessions = context_engine_store.list_session_states(repo_root=root, prune=False) if track_hot_path_session_state else []
    else:
        session_state = context_engine_store.register_session_state(
            repo_root=root,
            session_id=effective_session_id,
            workstream=inferred_workstream,
            touched_paths=effective_paths,
            explicit_paths=explicit,
            repo_dirty_paths=path_scope["repo_dirty_paths"],
            analysis_paths=effective_paths,
            generated_surfaces=generated_surfaces,
            intent=intent,
            turn_context=turn_context_runtime.compact_turn_context(normalized_turn_context),
            claim_mode=claim_mode,
            selection_state=selection_state,
            selection_reason=str(selection.get("reason", "")).strip(),
            working_tree_scope=str(path_scope.get("working_tree_scope", "")).strip(),
            auto_claim_paths=auto_claim_paths,
            claimed_paths=explicit_claims,
            lease_seconds=lease_seconds,
        )
        active_sessions = context_engine_store.list_session_states(repo_root=root)
    stage_timings["session_state"] = context_engine_store._elapsed_stage_ms(stage_started)
    conflicts = (
        context_engine_store._session_conflicts(
            current_session_id=effective_session_id,
            workstream=inferred_workstream,
            changed_paths=session_state.get("claimed_paths", []),
            generated_surfaces=context_engine_store._dedupe_strings([str(token) for token in generated_surfaces]),
            session_rows=active_sessions,
            claim_mode=context_engine_store._normalize_claim_mode(claim_mode),
            current_branch_name=str(session_state.get("branch_name", "")).strip(),
            current_head_oid=str(session_state.get("head_oid", "")).strip(),
        )
        if (not hot_path or track_hot_path_session_state)
        else []
    )
    if conflicts:
        severity_rank = {"high": 0, "medium": 1, "low": 2}
        conflicts.sort(key=lambda row: (severity_rank.get(str(row.get("severity", "")).strip(), 99), str(row.get("session_id", ""))))
    packet_state = (
        "compact"
        if selection_state == "explicit"
        else (
            str(impact.get("context_packet_state", "")).strip()
            or context_engine_store._impact_packet_state(
                shared_only=context_engine_store._broad_shared_only_input(effective_paths),
                selection_state=selection_state,
            )
        )
    )
    packet_selection = context_engine_store._compact_workstream_selection_for_packet(selection)
    compact_turn_context = turn_context_runtime.compact_turn_context(normalized_turn_context)
    target_resolution = turn_context_runtime.compact_target_resolution(
        turn_context_runtime.resolve_turn_targets(
            repo_root=root,
            turn_context=normalized_turn_context,
            changed_paths=effective_paths,
            explicit_paths=explicit,
            claimed_paths=session_state.get("claimed_paths", [])
            if isinstance(session_state.get("claimed_paths"), list)
            else [],
            inferred_workstream=inferred_workstream,
            runtime_mode=runtime_mode,
        )
    )
    presentation_policy = turn_context_runtime.compact_presentation_policy(
        turn_context_runtime.derive_presentation_policy(normalized_turn_context)
    )
    session_seed_paths = (
        list(path_scope["session_seed_paths"])
        if (
            not hot_path
            or track_hot_path_session_state
            or bool(impact.get("full_scan_recommended"))
        )
        else []
    )
    impact_summary = context_engine_store._impact_summary_payload(impact)
    impact_commands = (
        [str(token).strip() for token in impact_summary.get("recommended_commands", []) if str(token).strip()]
        if isinstance(impact_summary.get("recommended_commands"), list)
        else []
    )
    hint_commands = [str(token).strip() for token in validation_command_hints if str(token).strip()]
    impact_recommended_commands = context_engine_store._dedupe_strings([*impact_commands, *hint_commands])
    if impact_recommended_commands:
        impact_summary["recommended_commands"] = impact_recommended_commands
    payload = {
        "session": session_state,
        "changed_paths": effective_paths,
        "explicit_paths": explicit,
        "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
        "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
        "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
        "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
        "session_seed_paths": session_seed_paths,
        "turn_context": compact_turn_context,
        "target_resolution": target_resolution,
        "presentation_policy": presentation_policy,
        "inferred_workstream": inferred_workstream,
        "selection_state": selection_state,
        "selection_reason": str(selection.get("reason", "")).strip(),
        "selection_confidence": str(selection.get("confidence", "")).strip(),
        "candidate_workstreams": impact.get("candidate_workstreams", []),
        "workstream_selection": packet_selection,
        "impact": impact_summary,
        "workstream_context": (
            context_engine_store._compact_context_dossier(
                dossier,
                relation_limit_per_kind=2,
                event_limit=2,
                delivery_limit=1,
            )
            if not hot_path
            else {}
        ),
        "context_packet_state": packet_state,
        "truncation": context_engine_store._compact_truncation_for_summary(impact.get("truncation", {}))
        if isinstance(impact.get("truncation"), Mapping)
        else {},
        "full_scan_recommended": bool(impact.get("full_scan_recommended")) and selection_state != "explicit",
        "full_scan_reason": "" if selection_state == "explicit" else str(impact.get("full_scan_reason", "")).strip(),
        "fallback_scan": dict(impact.get("fallback_scan", {}))
        if isinstance(impact.get("fallback_scan"), Mapping)
        else {},
        "active_conflicts": [dict(row) for row in conflicts[:4] if isinstance(row, Mapping)],
        "active_session_count": len(active_sessions) if (not hot_path or track_hot_path_session_state) else 0,
    }
    if isinstance(payload.get("impact"), Mapping):
        impact_summary = dict(payload.get("impact", {}))
        docs = impact_summary.get("docs", [])
        if isinstance(docs, list):
            impact_summary["docs"] = context_engine_store._bootstrap_relevant_docs(
                [str(token).strip() for token in docs if str(token).strip()],
                guidance_rows=[dict(row) for row in impact_summary.get("guidance_brief", []) if isinstance(row, Mapping)]
                if isinstance(impact_summary.get("guidance_brief"), list)
                else [],
                limit=len(docs),
            )
        payload["impact"] = impact_summary
    impact_payload = payload.get("impact", {}) if isinstance(payload.get("impact"), Mapping) else {}
    stage_started = time.perf_counter()
    payload = tooling_context_packet_builder.finalize_packet(
        repo_root=root,
        packet_kind="session_brief",
        payload=payload,
        packet_state=packet_state,
        changed_paths=effective_paths,
        explicit_paths=explicit,
        shared_only_input=context_engine_store._broad_shared_only_input(effective_paths),
        selection_state=selection_state,
        workstream_selection=packet_selection,
        candidate_workstreams=payload.get("candidate_workstreams", [])
        if isinstance(payload.get("candidate_workstreams"), list)
        else [],
        components=impact_payload.get("components", []) if isinstance(impact_payload.get("components"), list) else [],
        diagrams=impact_payload.get("diagrams", []) if isinstance(impact_payload.get("diagrams"), list) else [],
        docs=impact_payload.get("docs", []) if isinstance(impact_payload.get("docs"), list) else [],
        recommended_commands=impact_payload.get("recommended_commands", [])
        if isinstance(impact_payload.get("recommended_commands"), list)
        else [],
        recommended_tests=impact_payload.get("recommended_tests", [])
        if isinstance(impact_payload.get("recommended_tests"), list)
        else [],
        engineering_notes=impact_payload.get("engineering_notes", {})
        if isinstance(impact_payload.get("engineering_notes"), Mapping)
        else {},
        miss_recovery=impact_payload.get("miss_recovery", {})
        if isinstance(impact_payload.get("miss_recovery"), Mapping)
        else {},
        full_scan_recommended=bool(payload.get("full_scan_recommended")),
        full_scan_reason=str(payload.get("full_scan_reason", "")).strip(),
        session_id=effective_session_id,
        family_hint=str(family_hint or "").strip(),
        guidance_catalog=guidance_catalog,
        optimization_snapshot=optimization_snapshot,
        delivery_profile=delivery_profile,
    )
    stage_timings["finalize"] = context_engine_store._elapsed_stage_ms(stage_started)
    timing_payload = payload
    if hot_path:
        payload = context_engine_store._compact_hot_path_runtime_packet(
            packet_kind="session_brief",
            payload=payload,
        )
    context_engine_store.record_runtime_timing(
        repo_root=root,
        category="reasoning",
        operation="session_brief",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "changed_path_count": len(effective_paths),
            "has_workstream": bool(inferred_workstream),
            "conflict_count": len(payload.get("active_conflicts", []))
            if isinstance(payload.get("active_conflicts"), list)
            else 0,
            "selection_state": str(_hot_path_workstream_selection(payload).get("state", "")).strip(),
            "packet_state": str(payload.get("context_packet_state", "")).strip(),
            "estimated_bytes": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_bytes", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "estimated_tokens": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_tokens", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "stage_timings": context_engine_store._compact_stage_timings(stage_timings),
            "family_hint": context_engine_store._normalize_family_hint(family_hint),
        },
    )
    if hot_path or not compact_delivery:
        return payload
    return session_bootstrap_payload_compactor.compact_finalized_session_brief_payload(timing_payload)


def build_session_bootstrap(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    use_working_tree: bool = False,
    working_tree_scope: str = "session",
    runtime_mode: str = "auto",
    session_id: str = "",
    workstream: str = "",
    generated_surfaces: Sequence[str] = (),
    intent: str = "",
    visible_text: Sequence[str] = (),
    active_tab: str = "",
    user_turn_id: str = "",
    supersedes_turn_id: str = "",
    claim_mode: str = "shared",
    claimed_paths: Sequence[str] = (),
    lease_seconds: int = 15 * 60,
    doc_limit: int = 8,
    command_limit: int = 10,
    test_limit: int = 8,
    delivery_profile: str = "full",
    family_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    retain_impact_internal_context: bool | None = None,
    skip_impact_runtime_warmup: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}
    hot_path = context_engine_store._delivery_profile_hot_path(delivery_profile)
    optimization_snapshot = {} if hot_path else context_engine_store.load_runtime_optimization_snapshot(repo_root=root)
    stage_started = time.perf_counter()
    guidance_catalog = context_engine_store.tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    stage_timings["guidance_catalog"] = context_engine_store._elapsed_stage_ms(stage_started)
    stage_started = time.perf_counter()
    brief = build_session_brief(
        repo_root=root,
        changed_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        runtime_mode=runtime_mode,
        session_id=session_id,
        workstream=workstream,
        generated_surfaces=generated_surfaces,
        intent=intent,
        visible_text=visible_text,
        active_tab=active_tab,
        user_turn_id=user_turn_id,
        supersedes_turn_id=supersedes_turn_id,
        claim_mode=claim_mode,
        claimed_paths=claimed_paths,
        lease_seconds=lease_seconds,
        delivery_profile=delivery_profile,
        family_hint=family_hint,
        validation_command_hints=validation_command_hints,
        retain_impact_internal_context=retain_impact_internal_context,
        skip_impact_runtime_warmup=skip_impact_runtime_warmup,
        compact_delivery=False,
    )
    stage_timings["session_brief"] = context_engine_store._elapsed_stage_ms(stage_started)
    impact = brief.get("impact", {}) if isinstance(brief.get("impact"), Mapping) else {}
    impact_doc_candidates: list[str] = []
    if isinstance(impact.get("docs"), list):
        impact_doc_candidates.extend(str(token).strip() for token in impact.get("docs", []) if str(token).strip())
    code_neighbors = impact.get("code_neighbors", {})
    if isinstance(code_neighbors, Mapping):
        for bucket_name in ("documented_by", "covered_by_runbooks"):
            bucket = code_neighbors.get(bucket_name, [])
            if not isinstance(bucket, list):
                continue
            impact_doc_candidates.extend(
                str(row.get("path", "")).strip()
                for row in bucket
                if isinstance(row, Mapping) and str(row.get("path", "")).strip()
            )
    relevant_docs = context_engine_store._bootstrap_relevant_docs(
        impact_doc_candidates,
        guidance_rows=[dict(row) for row in impact.get("guidance_brief", []) if isinstance(row, Mapping)]
        if isinstance(impact.get("guidance_brief"), list)
        else [],
        limit=max(1, int(doc_limit)),
    )
    recommended_commands = [
        str(token).strip()
        for token in impact.get("recommended_commands", [])[: max(1, int(command_limit))]
        if str(token).strip()
    ] if isinstance(impact.get("recommended_commands"), list) else []
    recommended_tests = [
        context_engine_store._compact_test_row_for_packet(row)
        for row in impact.get("recommended_tests", [])[: max(1, int(test_limit))]
        if isinstance(row, Mapping)
    ] if isinstance(impact.get("recommended_tests"), list) else []
    stage_started = time.perf_counter()
    timing_summary = context_engine_store.load_runtime_timing_summary(repo_root=root, limit=12) if not hot_path else {}
    runtime_state = context_engine_store.read_runtime_state(repo_root=root) if not hot_path else {}
    stage_timings["runtime_state"] = context_engine_store._elapsed_stage_ms(stage_started)
    brief_context_packet = dict(brief.get("context_packet", {})) if isinstance(brief.get("context_packet"), Mapping) else {}
    brief_route = dict(brief_context_packet.get("route", {})) if isinstance(brief_context_packet.get("route"), Mapping) else {}
    brief_selection = _hot_path_workstream_selection(brief)
    payload = {
        "bootstrapped_at": context_engine_store._utc_now(),
        "session": dict(brief.get("session", {})) if isinstance(brief.get("session"), Mapping) else {},
        "turn_context": dict(brief.get("turn_context", {})) if isinstance(brief.get("turn_context"), Mapping) else {},
        "target_resolution": dict(brief.get("target_resolution", {})) if isinstance(brief.get("target_resolution"), Mapping) else {},
        "presentation_policy": dict(brief.get("presentation_policy", {})) if isinstance(brief.get("presentation_policy"), Mapping) else {},
        "changed_paths": list(brief.get("changed_paths", []))
        if isinstance(brief.get("changed_paths"), list) and brief.get("changed_paths")
        else [str(token).strip() for token in changed_paths if str(token).strip()],
        "explicit_paths": list(brief.get("explicit_paths", []))
        if isinstance(brief.get("explicit_paths"), list) and brief.get("explicit_paths")
        else [str(token).strip() for token in changed_paths if str(token).strip()],
        "repo_dirty_paths": list(brief.get("repo_dirty_paths", [])) if isinstance(brief.get("repo_dirty_paths"), list) else [],
        "scoped_working_tree_paths": list(brief.get("scoped_working_tree_paths", []))
        if isinstance(brief.get("scoped_working_tree_paths"), list)
        else [],
        "working_tree_scope": str(brief.get("working_tree_scope", "")).strip(),
        "working_tree_scope_degraded": bool(brief.get("working_tree_scope_degraded")),
        "inferred_workstream": context_engine_store._payload_workstream_hint(brief, include_selection=False),
        "selection_state": str(brief_selection.get("state", "")).strip()
        or str(brief_context_packet.get("selection_state", "")).strip(),
        "selection_reason": str(brief_selection.get("reason", "")).strip(),
        "selection_confidence": str(brief_selection.get("confidence", "")).strip(),
        "candidate_workstreams": [
            context_engine_store._compact_workstream_reference_for_packet(row)
            for row in brief.get("candidate_workstreams", [])
            if isinstance(row, Mapping)
        ]
        if isinstance(brief.get("candidate_workstreams"), list)
        else [],
        "workstream_selection": context_engine_store._compact_bootstrap_workstream_selection(brief.get("workstream_selection", {}))
        if isinstance(brief.get("workstream_selection"), Mapping)
        else {},
        "context_packet_state": str(brief.get("context_packet_state", "")).strip()
        or str(brief_context_packet.get("packet_state", "")).strip(),
        "truncation": dict(brief.get("truncation", {})) if isinstance(brief.get("truncation"), Mapping) else {},
        "full_scan_recommended": bool(brief.get("full_scan_recommended") or brief_context_packet.get("full_scan_recommended")),
        "full_scan_reason": str(brief.get("full_scan_reason", "")).strip()
        or str(brief_context_packet.get("full_scan_reason", "")).strip(),
        "fallback_scan": dict(brief.get("fallback_scan", {}))
        if isinstance(brief.get("fallback_scan"), Mapping)
        else {},
        "impact_summary": {
            "primary_workstream": context_engine_store._compact_workstream_row_for_packet(impact.get("primary_workstream", {}))
            if isinstance(impact.get("primary_workstream"), Mapping)
            else {},
            "components": [context_engine_store._compact_component_row_for_packet(row) for row in impact.get("components", []) if isinstance(row, Mapping)]
            if isinstance(impact.get("components"), list)
            else [],
            "workstreams": [
                context_engine_store._compact_workstream_reference_for_packet(row)
                for row in brief.get("candidate_workstreams", [])
                if isinstance(row, Mapping)
            ]
            if isinstance(brief.get("candidate_workstreams"), list)
            else [],
            "diagrams": [context_engine_store._compact_diagram_row_for_packet(row) for row in impact.get("diagrams", []) if isinstance(row, Mapping)]
            if isinstance(impact.get("diagrams"), list)
            else [],
            "guidance_brief": [dict(row) for row in impact.get("guidance_brief", []) if isinstance(row, Mapping)]
            if isinstance(impact.get("guidance_brief"), list)
            else [],
            "miss_recovery": context_engine_store._compact_miss_recovery_for_packet(impact.get("miss_recovery", {}))
            if isinstance(impact.get("miss_recovery"), Mapping)
            else {},
        },
        "relevant_docs": relevant_docs,
        "recommended_commands": recommended_commands,
        "recommended_tests": recommended_tests,
        "top_engineering_notes": context_engine_store._compact_engineering_notes(
            impact.get("engineering_notes", {}) if isinstance(impact.get("engineering_notes"), Mapping) else {},
            total_limit=3,
            per_kind_limit=1,
        )[0],
        "workstream_context": dict(brief.get("workstream_context", {})) if isinstance(brief.get("workstream_context"), Mapping) else {},
        "active_conflicts": [dict(row) for row in brief.get("active_conflicts", [])[:4] if isinstance(row, Mapping)]
        if isinstance(brief.get("active_conflicts"), list)
        else [],
        "active_session_count": int(brief.get("active_session_count", 0) or 0),
        "runtime": {
            "projection_fingerprint": str(runtime_state.get("projection_fingerprint", "")).strip(),
            "projection_scope": str(runtime_state.get("projection_scope", "")).strip(),
            "updated_utc": str(runtime_state.get("updated_utc", "")).strip(),
            "timings": context_engine_store._compact_runtime_timing_rows_for_packet(timing_summary)
            if isinstance(timing_summary, Mapping)
            else {},
        },
        "narrowing_required": bool(brief.get("narrowing_required") or brief_route.get("narrowing_required")),
        "route_ready": bool(brief.get("route_ready") or brief_route.get("route_ready")),
    }
    payload = session_bootstrap_payload_compactor.compact_bootstrap_payload(payload)
    stage_started = time.perf_counter()
    payload = tooling_context_packet_builder.finalize_packet(
        repo_root=root,
        packet_kind="bootstrap_session",
        payload=payload,
        packet_state=str(payload.get("context_packet_state", "")).strip(),
        changed_paths=payload.get("changed_paths", []) if isinstance(payload.get("changed_paths"), list) else [],
        explicit_paths=payload.get("explicit_paths", []) if isinstance(payload.get("explicit_paths"), list) else [],
        shared_only_input=context_engine_store._broad_shared_only_input(
            payload.get("changed_paths", []) if isinstance(payload.get("changed_paths"), list) else []
        ),
        selection_state=str(payload.get("selection_state", "")).strip(),
        workstream_selection=payload.get("workstream_selection", {})
        if isinstance(payload.get("workstream_selection"), Mapping)
        else {},
        candidate_workstreams=payload.get("candidate_workstreams", [])
        if isinstance(payload.get("candidate_workstreams"), list)
        else [],
        components=payload.get("impact_summary", {}).get("components", [])
        if isinstance(payload.get("impact_summary"), Mapping) and isinstance(payload.get("impact_summary", {}).get("components"), list)
        else [],
        diagrams=payload.get("impact_summary", {}).get("diagrams", [])
        if isinstance(payload.get("impact_summary"), Mapping) and isinstance(payload.get("impact_summary", {}).get("diagrams"), list)
        else [],
        docs=relevant_docs,
        recommended_commands=recommended_commands,
        recommended_tests=recommended_tests,
        engineering_notes=payload.get("top_engineering_notes", {})
        if isinstance(payload.get("top_engineering_notes"), Mapping)
        else {},
        miss_recovery=payload.get("impact_summary", {}).get("miss_recovery", {})
        if isinstance(payload.get("impact_summary"), Mapping)
        and isinstance(payload.get("impact_summary", {}).get("miss_recovery"), Mapping)
        else {},
        full_scan_recommended=bool(payload.get("full_scan_recommended")),
        full_scan_reason=str(payload.get("full_scan_reason", "")).strip(),
        session_id=str(dict(payload.get("session", {})).get("session_id", "")).strip()
        if isinstance(payload.get("session"), Mapping)
        else "",
        family_hint=str(family_hint or "").strip(),
        guidance_catalog=guidance_catalog,
        optimization_snapshot=optimization_snapshot,
        delivery_profile=delivery_profile,
    )
    stage_timings["finalize"] = context_engine_store._elapsed_stage_ms(stage_started)
    timing_payload = payload
    if hot_path:
        payload = context_engine_store._compact_hot_path_runtime_packet(
            packet_kind="bootstrap_session",
            payload=payload,
        )
    else:
        payload = session_bootstrap_payload_compactor.compact_finalized_bootstrap_payload(payload)
    if isinstance(timing_payload.get("session"), Mapping) and not hot_path:
        session_payload = dict(timing_payload.get("session", {}))
        target = context_engine_store._bootstrap_record_path(repo_root=root, session_id=str(session_payload.get("session_id", "")).strip())
        context_engine_store.odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=target,
            payload=timing_payload,
            lock_key=str(target),
        )
        context_engine_store.prune_runtime_records(repo_root=root)
    if not hot_path:
        packet_summary = odylith_context_engine_packet_summary_runtime._packet_summary_from_bootstrap_payload(timing_payload)
        benchmark_summary = context_engine_store._packet_benchmark_summary_for_runtime_packet(
            repo_root=root,
            packet=packet_summary,
        )
        control_advisories = dict(context_engine_store.load_runtime_optimization_snapshot(repo_root=root).get("control_advisories", {}))
        context_engine_store.odylith_evaluation_ledger.append_event(
            repo_root=root,
            event_type="packet",
            event_id=(
                f"{str(packet_summary.get('session_id', '')).strip()}::"
                f"{str(packet_summary.get('bootstrapped_at', '')).strip()}"
            ),
            payload=context_engine_store.odylith_evaluation_ledger.packet_event_payload(
                packet_summary=packet_summary,
                benchmark_summary=benchmark_summary,
                control_advisories=control_advisories,
            ),
            recorded_at=str(packet_summary.get("bootstrapped_at", "")).strip(),
        )
    context_engine_store.record_runtime_timing(
        repo_root=root,
        category="reasoning",
        operation="bootstrap_session",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "changed_path_count": len(payload.get("changed_paths", [])) if isinstance(payload.get("changed_paths"), list) else 0,
            "doc_count": len(relevant_docs),
            "command_count": len(recommended_commands),
            "test_count": len(recommended_tests),
            "packet_state": str(payload.get("context_packet_state", "")).strip(),
            "estimated_bytes": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_bytes", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "estimated_tokens": int(dict(timing_payload.get("packet_metrics", {})).get("estimated_tokens", 0) or 0)
            if isinstance(timing_payload.get("packet_metrics"), Mapping)
            else 0,
            "stage_timings": context_engine_store._compact_stage_timings(stage_timings),
            "family_hint": context_engine_store._normalize_family_hint(family_hint),
        },
    )
    return payload
# Keep the store dependency explicit without pulling it through module bootstrap.
from odylith.runtime.context_engine import odylith_context_engine_store as context_engine_store
