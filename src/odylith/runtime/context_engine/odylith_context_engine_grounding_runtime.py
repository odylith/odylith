"""Governance and impact grounding helpers extracted from the context engine store."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine.grounding_component_priority import prioritize_governance_components


def _host():
    from odylith.runtime.context_engine import odylith_context_engine_store as host

    return host


def build_governance_slice(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    workstream: str = "",
    component: str = "",
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    delivery_profile: str = "full",
    family_hint: str = "",
    intent: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    host = _host()
    _delivery_profile_hot_path = host._delivery_profile_hot_path
    tooling_guidance_catalog = host.tooling_guidance_catalog
    load_runtime_optimization_snapshot = host.load_runtime_optimization_snapshot
    load_backlog_detail = host.load_backlog_detail
    load_registry_detail = host.load_registry_detail
    component_registry = host.component_registry
    _dedupe_strings = host._dedupe_strings
    _fallback_scan_payload = host._fallback_scan_payload
    tooling_context_packet_builder = host.tooling_context_packet_builder
    _compact_hot_path_runtime_packet = host._compact_hot_path_runtime_packet
    _elapsed_stage_ms = host._elapsed_stage_ms
    _governance_requires_architecture_audit = host._governance_requires_architecture_audit
    build_architecture_audit = host.build_architecture_audit
    _compact_workstream_row_for_packet = host._compact_workstream_row_for_packet
    _compact_component_entry_for_governance_packet = host._compact_component_entry_for_governance_packet
    _compact_diagram_row_for_packet = host._compact_diagram_row_for_packet
    _normalize_family_hint = host._normalize_family_hint
    _governance_explicit_slice_grounded = host._governance_explicit_slice_grounded
    _compact_bug_row_for_governance_packet = host._compact_bug_row_for_governance_packet
    _governance_closeout_docs = host._governance_closeout_docs
    _governance_diagram_catalog_companions = host._governance_diagram_catalog_companions
    _companion_context_paths = host._companion_context_paths
    _governance_surface_refs = host._governance_surface_refs
    display_command = host.display_command
    _hot_path_workstream_selection = host._hot_path_workstream_selection
    _bounded_explicit_governance_closeout_docs = host._bounded_explicit_governance_closeout_docs
    _broad_shared_only_input = host._broad_shared_only_input
    _governance_state_actions = host._governance_state_actions
    _compact_architecture_audit_for_packet = host._compact_architecture_audit_for_packet
    _governance_hot_path_docs = host._governance_hot_path_docs
    _governance_can_skip_runtime_warmup = host._governance_can_skip_runtime_warmup
    record_runtime_timing = host.record_runtime_timing
    _compact_stage_timings = host._compact_stage_timings

    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}
    hot_path = _delivery_profile_hot_path(delivery_profile)
    explicit_workstream = str(workstream or "").strip().upper()
    explicit_component = str(component or "").strip().lower()
    stage_started = time.perf_counter()
    guidance_catalog = tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    optimization_snapshot = {} if hot_path else load_runtime_optimization_snapshot(repo_root=root)
    stage_timings["guidance_catalog"] = _elapsed_stage_ms(stage_started)

    stage_started = time.perf_counter()
    should_prefetch_seed_details = not bool(changed_paths)
    component_detail_level = "grounding_light" if hot_path else "full"
    workstream_detail_level = "grounding_light" if hot_path else "full"
    workstream_detail = (
        load_backlog_detail(
            repo_root=root,
            workstream_id=explicit_workstream,
            runtime_mode=runtime_mode,
            detail_level=workstream_detail_level,
        )
        if explicit_workstream and should_prefetch_seed_details
        else None
    )
    component_detail = (
        load_registry_detail(
            repo_root=root,
            component_id=explicit_component,
            runtime_mode=runtime_mode,
            detail_level=component_detail_level,
        )
        if explicit_component and should_prefetch_seed_details
        else None
    )
    stage_timings["seed_detail"] = _elapsed_stage_ms(stage_started)

    derived_paths: list[str] = []
    if not changed_paths:
        if isinstance(workstream_detail, Mapping):
            derived_paths.extend(
                [
                    str(workstream_detail.get("idea_file", "")).strip(),
                    str(workstream_detail.get("promoted_to_plan", "")).strip(),
                ]
            )
        if isinstance(component_detail, Mapping):
            component_entry = component_detail.get("component")
            if isinstance(component_entry, component_registry.ComponentEntry):
                derived_paths.append(str(component_entry.spec_ref).strip())
            traceability = dict(component_detail.get("traceability", {})) if isinstance(component_detail.get("traceability"), Mapping) else {}
            for bucket in ("developer_docs", "runbooks", "code_references"):
                if isinstance(traceability.get(bucket), list):
                    derived_paths.extend(str(token).strip() for token in traceability.get(bucket, []) if str(token).strip())
    effective_paths = _dedupe_strings([*changed_paths, *derived_paths])[:8]

    if not effective_paths and not explicit_workstream and not explicit_component:
        payload = {
            "resolved": False,
            "changed_paths": [],
            "explicit_paths": [],
            "intent": str(intent or "").strip(),
            "selection_state": "none",
            "selection_reason": "No paths, workstream, or component seeds were provided for governance grounding.",
            "selection_confidence": "none",
            "candidate_workstreams": [],
            "components": [],
            "diagrams": [],
            "docs": [],
            "validation_bundle": {
                "recommended_commands": [],
                "strict_gate_commands": [],
                "governed_surface_sync_required": False,
                "plan_binding_required": False,
            },
            "governance_obligations": {
                "touched_workstreams": [],
                "touched_components": [],
                "linked_bugs": [],
                "required_diagrams": [],
                "closeout_docs": [],
                "workstream_state_actions": ["widen_to_direct_reads"],
            },
            "surface_refs": {
                "impacted_surfaces": {
                    "radar": False,
                    "atlas": False,
                    "compass": False,
                    "registry": False,
                    "casebook": False,
                    "tooling_shell": False,
                },
                "reasons": {},
            },
            "diagram_watch_gaps": [],
            "full_scan_recommended": True,
            "full_scan_reason": "no_governance_seeds",
            "fallback_scan": _fallback_scan_payload(
                repo_root=root,
                reason="no_governance_seeds",
                changed_paths=[],
                delivery_profile=delivery_profile,
            ),
        }
        payload = tooling_context_packet_builder.finalize_packet(
            repo_root=root,
            packet_kind="governance_slice",
            payload=payload,
            packet_state="gated_ambiguous",
            changed_paths=[],
            explicit_paths=[],
            shared_only_input=False,
            selection_state="none",
            workstream_selection={"state": "none", "reason": "No governance seeds were available."},
            candidate_workstreams=[],
            components=[],
            diagrams=[],
            docs=[],
            recommended_commands=[],
            recommended_tests=[],
            engineering_notes={},
            miss_recovery={},
            full_scan_recommended=True,
            full_scan_reason="no_governance_seeds",
            session_id=session_id,
            family_hint=family_hint or "governance_slice",
            guidance_catalog=guidance_catalog,
            optimization_snapshot=optimization_snapshot,
            delivery_profile=delivery_profile,
        )
        return _compact_hot_path_runtime_packet(packet_kind="governance_slice", payload=payload) if hot_path else payload

    stage_started = time.perf_counter()
    impact_payload = build_impact_report(
        repo_root=root,
        changed_paths=effective_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
        runtime_mode=runtime_mode,
        intent="governance grounding",
        delivery_profile=delivery_profile,
        family_hint=family_hint or "governance_slice",
        workstream_hint=explicit_workstream,
        validation_command_hints=validation_command_hints,
        retain_hot_path_internal_context=hot_path,
        guidance_catalog_snapshot=guidance_catalog,
        optimization_snapshot=optimization_snapshot,
        skip_runtime_warmup=_governance_can_skip_runtime_warmup(
            repo_root=root,
            changed_paths=effective_paths,
            workstream_hint=explicit_workstream,
            component_hint=explicit_component,
            runtime_mode=runtime_mode,
            delivery_profile=delivery_profile,
            family_hint=family_hint,
            use_working_tree=use_working_tree,
            claimed_paths=claimed_paths,
        ),
        finalize_packet=not hot_path,
        component_hint=explicit_component,
    )
    stage_timings["impact"] = _elapsed_stage_ms(stage_started)

    if _governance_requires_architecture_audit(
        changed_paths=effective_paths,
        family_hint=family_hint,
    ):
        stage_started = time.perf_counter()
        architecture_payload = build_architecture_audit(
            repo_root=root,
            changed_paths=effective_paths,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            claimed_paths=claimed_paths,
            runtime_mode=runtime_mode,
            detail_level="packet",
        )
        stage_timings["architecture"] = _elapsed_stage_ms(stage_started)
    else:
        architecture_payload = {
            "resolved": False,
            "changed_paths": list(effective_paths),
            "topology_domains": [],
            "linked_components": [],
            "linked_diagrams": [],
            "required_reads": [],
            "diagram_watch_gaps": [],
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "coverage": {},
            "authority_chain": [],
            "validation_obligations": [],
        }
        stage_timings["architecture"] = 0.0

    candidate_workstreams = [
        dict(row)
        for row in impact_payload.get("candidate_workstreams", [])
        if isinstance(impact_payload.get("candidate_workstreams"), list) and isinstance(row, Mapping)
    ]
    stage_started = time.perf_counter()
    workstream_details: list[dict[str, Any]] = []
    workstream_ids = _dedupe_strings(
        [
            explicit_workstream,
            *(
                str(row.get("entity_id", "")).strip().upper()
                for row in candidate_workstreams
                if str(row.get("entity_id", "")).strip()
            ),
        ]
    )[:4]
    for workstream_id in workstream_ids:
        detail = workstream_detail if workstream_detail and workstream_id == explicit_workstream else load_backlog_detail(
            repo_root=root,
            workstream_id=workstream_id,
            runtime_mode=runtime_mode,
            detail_level=workstream_detail_level,
        )
        if isinstance(detail, Mapping):
            if workstream_id == explicit_workstream and workstream_detail is None:
                workstream_detail = dict(detail)
            workstream_details.append(dict(detail))

    component_rows = [
        dict(row)
        for row in impact_payload.get("components", [])
        if isinstance(impact_payload.get("components"), list) and isinstance(row, Mapping)
    ]
    component_details: list[dict[str, Any]] = []
    component_ids = _dedupe_strings(
        [
            explicit_component,
            *(
                str(row.get("component_id", "")).strip().lower()
                for row in component_rows
                if str(row.get("component_id", "")).strip()
            ),
        ]
    )[:4]
    for component_id in component_ids:
        detail = (
            component_detail
            if component_detail and component_id == explicit_component
            else load_registry_detail(
                repo_root=root,
                component_id=component_id,
                runtime_mode=runtime_mode,
                detail_level=component_detail_level,
            )
        )
        if isinstance(detail, Mapping):
            if component_id == explicit_component and component_detail is None:
                component_detail = dict(detail)
            component_details.append(dict(detail))
            component_entry = detail.get("component")
            if isinstance(component_entry, component_registry.ComponentEntry):
                workstream_ids = _dedupe_strings([*workstream_ids, *component_entry.workstreams])[:4]
    stage_timings["detail_lookup"] = _elapsed_stage_ms(stage_started)

    compact_workstreams = [
        _compact_workstream_row_for_packet(row)
        for row in candidate_workstreams
        if isinstance(row, Mapping)
    ]
    if explicit_workstream and explicit_workstream not in {
        str(row.get("entity_id", "")).strip().upper()
        for row in compact_workstreams
        if isinstance(row, Mapping)
    }:
        for detail in workstream_details:
            metadata = dict(detail.get("metadata", {})) if isinstance(detail.get("metadata"), Mapping) else {}
            if str(detail.get("idea_id", "")).strip().upper() != explicit_workstream:
                continue
            compact_workstreams.insert(
                0,
                {
                    "entity_id": explicit_workstream,
                    "title": str(metadata.get("title", "")).strip(),
                    "status": str(metadata.get("status", "")).strip(),
                    "path": str(detail.get("idea_file", "")).strip(),
                },
            )
            break
    compact_components = prioritize_governance_components(
        rows=component_rows,
        changed_paths=effective_paths,
        explicit_component=explicit_component,
    )
    if explicit_component:
        explicit_component_rows = [
            row
            for row in compact_components
            if isinstance(row, Mapping) and str(row.get("component_id", "")).strip().lower() == explicit_component
        ]
        compact_components = [
            *explicit_component_rows,
            *[
                row
                for row in compact_components
                if not (
                    isinstance(row, Mapping)
                    and str(row.get("component_id", "")).strip().lower() == explicit_component
                )
            ],
        ]
        if not explicit_component_rows:
            for detail in component_details:
                component_entry = detail.get("component")
                if not isinstance(component_entry, component_registry.ComponentEntry):
                    continue
                if str(component_entry.component_id).strip().lower() != explicit_component:
                    continue
                compact_components.insert(0, _compact_component_entry_for_governance_packet(component_entry))
                break

    compact_diagrams = [
        _compact_diagram_row_for_packet(row)
        for row in impact_payload.get("diagrams", [])
        if isinstance(impact_payload.get("diagrams"), list) and isinstance(row, Mapping)
    ]
    architecture_diagrams = [
        _compact_diagram_row_for_packet(row)
        for row in architecture_payload.get("linked_diagrams", [])
        if isinstance(architecture_payload.get("linked_diagrams"), list) and isinstance(row, Mapping)
    ]
    compact_diagrams = list(
        {
            (str(row.get("diagram_id", "")).strip(), str(row.get("path", "")).strip()): row
            for row in [*compact_diagrams, *architecture_diagrams]
            if isinstance(row, Mapping)
        }.values()
    )
    normalized_family_hint = _normalize_family_hint(family_hint)
    governance_hot_path_docs = _governance_hot_path_docs(
        repo_root=root,
        changed_paths=effective_paths,
        family_hint=family_hint,
        workstream_detail=workstream_detail,
    )
    exact_governed_slice = _governance_explicit_slice_grounded(
        repo_root=root,
        changed_paths=effective_paths,
        explicit_workstream=explicit_workstream,
        explicit_component=explicit_component,
        workstream_detail=workstream_detail,
        component_detail=component_detail,
        diagrams=compact_diagrams,
    )

    compact_bugs = [
        _compact_bug_row_for_governance_packet(row)
        for row in impact_payload.get("bugs", [])
        if isinstance(impact_payload.get("bugs"), list) and isinstance(row, Mapping)
    ]
    if hot_path and governance_hot_path_docs is not None and normalized_family_hint != "governed_surface_sync":
        closeout_docs = _dedupe_strings(governance_hot_path_docs)
    else:
        closeout_docs = _governance_closeout_docs(
            docs=impact_payload.get("docs", []) if isinstance(impact_payload.get("docs"), list) else [],
            workstream_details=workstream_details,
            component_details=component_details,
        )
        closeout_docs = _dedupe_strings(
            [
                *(
                    [
                        "odylith/atlas/source/odylith-delivery-governance-topology.mmd",
                        "odylith/casebook/bugs/INDEX.md",
                    ]
                    if normalized_family_hint == "governed_surface_sync"
                    else []
                ),
                *_governance_diagram_catalog_companions(
                    changed_paths=effective_paths,
                    diagrams=compact_diagrams,
                ),
                *_companion_context_paths(changed_paths=effective_paths, repo_root=root),
                *closeout_docs,
            ]
        )
    recommended_commands = _dedupe_strings(
        [
            *(
                str(token).strip()
                for token in impact_payload.get("recommended_commands", [])
                if isinstance(impact_payload.get("recommended_commands"), list) and str(token).strip()
            ),
            *(
                str(token).strip()
                for token in validation_command_hints
                if str(token).strip()
            ),
        ]
    )
    strict_gate_commands = _dedupe_strings(
        [
            display_command("sync", "--repo-root", ".", "--force", "--check-only", "--check-clean"),
        ]
    )

    diagram_watch_gaps = [
        dict(row)
        for row in architecture_payload.get("diagram_watch_gaps", [])
        if isinstance(architecture_payload.get("diagram_watch_gaps"), list) and isinstance(row, Mapping)
    ]
    disagreement_reason = ""
    if explicit_workstream and workstream_detail is None:
        disagreement_reason = "unknown_workstream"
    elif explicit_component and component_detail is None:
        disagreement_reason = "unknown_component"
    elif explicit_workstream and component_detail is not None:
        component_entry = component_detail.get("component")
        if isinstance(component_entry, component_registry.ComponentEntry) and explicit_workstream not in {
            str(token).strip().upper() for token in component_entry.workstreams if str(token).strip()
        }:
            disagreement_reason = "workstream_component_disagree"

    impact_selection = _hot_path_workstream_selection(impact_payload)
    if exact_governed_slice and explicit_workstream and not disagreement_reason:
        explicit_title = ""
        explicit_path = ""
        if isinstance(workstream_detail, Mapping):
            metadata = (
                dict(workstream_detail.get("metadata", {}))
                if isinstance(workstream_detail.get("metadata"), Mapping)
                else {}
            )
            explicit_title = str(metadata.get("title", "")).strip()
            explicit_path = str(workstream_detail.get("idea_file", "")).strip()
        impact_selection = {
            "state": "explicit",
            "reason": f"Using explicit governed slice `{explicit_workstream}` with direct component and diagram evidence.",
            "why_selected": f"Explicit workstream `{explicit_workstream}` agrees with the component boundary and touched governed paths.",
            "selected_workstream": {
                "entity_id": explicit_workstream,
                **({"title": explicit_title} if explicit_title else {}),
                **({"path": explicit_path} if explicit_path else {}),
            },
            "top_candidate": {
                "entity_id": explicit_workstream,
                **({"title": explicit_title} if explicit_title else {}),
                **({"path": explicit_path} if explicit_path else {}),
            },
            "score_gap": None,
            "confidence": "high",
            "candidate_count": max(1, len(compact_workstreams)),
            "strong_candidate_count": 1,
            "ambiguity_class": "resolved",
            "competing_candidates": [],
        }
    selected_workstream_row = (
        dict(impact_selection.get("selected_workstream", {}))
        if isinstance(impact_selection.get("selected_workstream"), Mapping)
        else dict(impact_selection.get("top_candidate", {}))
        if isinstance(impact_selection.get("top_candidate"), Mapping)
        else {}
    )
    selected_workstream_id = str(selected_workstream_row.get("entity_id", "")).strip().upper()
    if selected_workstream_id:
        workstream_ids = _dedupe_strings([selected_workstream_id, *workstream_ids])[:4]
        if selected_workstream_id not in {
            str(row.get("entity_id", "")).strip().upper()
            for row in compact_workstreams
            if isinstance(row, Mapping)
        }:
            compact_workstreams.insert(
                0,
                {
                    "entity_id": selected_workstream_id,
                    **(
                        {"title": str(selected_workstream_row.get("title", "")).strip()}
                        if str(selected_workstream_row.get("title", "")).strip()
                        else {}
                    ),
                    **(
                        {"path": str(selected_workstream_row.get("path", "")).strip()}
                        if str(selected_workstream_row.get("path", "")).strip()
                        else {}
                    ),
                },
            )
    surface_refs = _governance_surface_refs(
        repo_root=root,
        changed_paths=effective_paths,
        workstream_ids=workstream_ids,
        component_ids=component_ids,
    )
    impacted_surfaces = (
        dict(surface_refs.get("impacted_surfaces", {}))
        if isinstance(surface_refs.get("impacted_surfaces"), Mapping)
        else {}
    )
    governed_surface_sync_required = any(bool(value) for value in impacted_surfaces.values())
    plan_binding_required = bool(workstream_ids)
    selection_state = str(impact_selection.get("state", "")).strip() or ("explicit" if explicit_workstream else "none")
    selection_reason = str(impact_selection.get("reason", "")).strip()
    selection_confidence = str(impact_selection.get("confidence", "")).strip() or ("explicit" if explicit_workstream else "low")

    impact_full_scan_reason = str(impact_payload.get("full_scan_reason", "")).strip()
    impact_full_scan_recommended = bool(impact_payload.get("full_scan_recommended"))
    if (
        exact_governed_slice
        and not disagreement_reason
        and not diagram_watch_gaps
        and impact_full_scan_reason == "selection_ambiguous"
    ):
        impact_full_scan_reason = ""
        impact_full_scan_recommended = False

    architecture_full_scan_reason = str(architecture_payload.get("full_scan_reason", "")).strip()
    architecture_full_scan_recommended = bool(architecture_payload.get("full_scan_recommended"))
    if (
        exact_governed_slice
        and not disagreement_reason
        and not diagram_watch_gaps
        and architecture_full_scan_reason == "coverage_weak"
    ):
        architecture_full_scan_reason = ""
        architecture_full_scan_recommended = False
    full_scan_reason = (
        disagreement_reason
        or ("diagram_watch_gaps" if diagram_watch_gaps else "")
        or impact_full_scan_reason
        or architecture_full_scan_reason
    )
    full_scan_recommended = bool(
        disagreement_reason
        or diagram_watch_gaps
        or impact_full_scan_recommended
        or architecture_full_scan_recommended
    )
    closeout_docs = _bounded_explicit_governance_closeout_docs(
        repo_root=root,
        docs=closeout_docs,
        enabled=bool(
            normalized_family_hint == "explicit_workstream"
            and explicit_workstream
            and not disagreement_reason
            and not full_scan_recommended
        ),
    )
    packet_state = (
        "compact"
        if not full_scan_recommended and selection_state == "explicit"
        else str(impact_payload.get("context_packet_state", "")).strip()
        or "gated_ambiguous"
    )
    workstream_selection = impact_selection or {"state": selection_state, "reason": selection_reason}

    payload = {
        "resolved": not full_scan_recommended and bool(compact_workstreams or compact_components or effective_paths),
        "intent": str(intent or "").strip(),
        "changed_paths": list(effective_paths),
        "explicit_paths": list(effective_paths),
        "repo_dirty_paths": list(impact_payload.get("repo_dirty_paths", [])) if isinstance(impact_payload.get("repo_dirty_paths"), list) else [],
        "scoped_working_tree_paths": list(impact_payload.get("scoped_working_tree_paths", []))
        if isinstance(impact_payload.get("scoped_working_tree_paths"), list)
        else [],
        "working_tree_scope": str(impact_payload.get("working_tree_scope", "")).strip() or str(working_tree_scope or "").strip(),
        "working_tree_scope_degraded": bool(impact_payload.get("working_tree_scope_degraded")),
        "selection_state": selection_state,
        "selection_reason": selection_reason,
        "selection_confidence": selection_confidence,
        "inferred_workstream": str(impact_payload.get("inferred_workstream", "")).strip().upper() or explicit_workstream,
        "candidate_workstreams": compact_workstreams[:4],
        "workstream_selection": workstream_selection,
        "components": compact_components[:4],
        "diagrams": compact_diagrams[:4],
        "docs": closeout_docs[:8],
        "benchmark_selector_diagnostics": dict(impact_payload.get("benchmark_selector_diagnostics", {}))
        if isinstance(impact_payload.get("benchmark_selector_diagnostics"), Mapping)
        else {},
        "recommended_commands": recommended_commands[:8],
        "validation_bundle": {
            "recommended_commands": recommended_commands[:8],
            "strict_gate_commands": strict_gate_commands[:8],
            "governed_surface_sync_required": governed_surface_sync_required,
            "plan_binding_required": plan_binding_required,
        },
        "governance_obligations": {
            "touched_workstreams": compact_workstreams[:4],
            "touched_components": compact_components[:4],
            "linked_bugs": compact_bugs[:4],
            "required_diagrams": compact_diagrams[:4],
            "closeout_docs": closeout_docs[:8],
            "workstream_state_actions": _governance_state_actions(
                governed_surface_sync_required=governed_surface_sync_required,
                plan_binding_required=plan_binding_required,
                diagram_watch_gaps=diagram_watch_gaps,
                full_scan_recommended=full_scan_recommended,
            ),
        },
        "surface_refs": surface_refs,
        "diagram_watch_gaps": diagram_watch_gaps[:4],
        "architecture_audit": _compact_architecture_audit_for_packet(architecture_payload, packet_state=packet_state),
        "full_scan_recommended": full_scan_recommended,
        "full_scan_reason": full_scan_reason,
        "fallback_scan": dict(impact_payload.get("fallback_scan", {}))
        if isinstance(impact_payload.get("fallback_scan"), Mapping)
        else _fallback_scan_payload(
            repo_root=root,
            reason=full_scan_reason,
            changed_paths=effective_paths,
            delivery_profile=delivery_profile,
        ),
    }
    stage_started = time.perf_counter()
    finalized = tooling_context_packet_builder.finalize_packet(
        repo_root=root,
        packet_kind="governance_slice",
        payload=payload,
        packet_state=packet_state,
        changed_paths=payload.get("changed_paths", []) if isinstance(payload.get("changed_paths"), list) else [],
        explicit_paths=payload.get("explicit_paths", []) if isinstance(payload.get("explicit_paths"), list) else [],
        shared_only_input=_broad_shared_only_input(payload.get("changed_paths", []) if isinstance(payload.get("changed_paths"), list) else []),
        selection_state=selection_state,
        workstream_selection=workstream_selection,
        candidate_workstreams=compact_workstreams[:4],
        components=compact_components[:4],
        diagrams=compact_diagrams[:4],
        docs=closeout_docs[:8],
        recommended_commands=recommended_commands[:8],
        recommended_tests=[],
        engineering_notes={},
        miss_recovery={},
        full_scan_recommended=full_scan_recommended,
        full_scan_reason=full_scan_reason,
        session_id=session_id,
        family_hint=normalized_family_hint or str(family_hint or "").strip(),
        guidance_catalog=guidance_catalog,
        optimization_snapshot=optimization_snapshot,
        delivery_profile=delivery_profile,
    )
    if governance_hot_path_docs is not None and normalized_family_hint != "governed_surface_sync":
        finalized["governance_hot_path_docs"] = governance_hot_path_docs[:8]
        finalized["governance_hot_path_docs_authoritative"] = True
    stage_timings["finalize"] = _elapsed_stage_ms(stage_started)
    record_runtime_timing(
        repo_root=root,
        category="reasoning",
        operation="governance_slice",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "changed_path_count": len(effective_paths),
            "workstream_count": len(compact_workstreams),
            "component_count": len(compact_components),
            "diagram_watch_gap_count": len(diagram_watch_gaps),
            "packet_state": packet_state,
            "full_scan_recommended": full_scan_recommended,
            "stage_timings": _compact_stage_timings(stage_timings),
        },
    )
    if hot_path:
        return _compact_hot_path_runtime_packet(packet_kind="governance_slice", payload=finalized)
    return finalized


def build_impact_report(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    test_limit: int = 12,
    intent: str = "",
    delivery_profile: str = "full",
    family_hint: str = "",
    workstream_hint: str = "",
    component_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    retain_hot_path_internal_context: bool = False,
    guidance_catalog_snapshot: Mapping[str, Any] | None = None,
    optimization_snapshot: Mapping[str, Any] | None = None,
    skip_runtime_warmup: bool = False,
    finalize_packet: bool = True,
) -> dict[str, Any]:
    host = _host()
    _delivery_profile_hot_path = host._delivery_profile_hot_path
    _impact_family_profile = host._impact_family_profile
    tooling_guidance_catalog = host.tooling_guidance_catalog
    load_runtime_optimization_snapshot = host.load_runtime_optimization_snapshot
    _elapsed_stage_ms = host._elapsed_stage_ms
    _resolve_changed_path_scope_context = host._resolve_changed_path_scope_context
    _broad_shared_only_input = host._broad_shared_only_input
    _fallback_scan_payload = host._fallback_scan_payload
    tooling_context_packet_builder = host.tooling_context_packet_builder
    _impact_packet_state = host._impact_packet_state
    _compact_hot_path_runtime_packet = host._compact_hot_path_runtime_packet
    _hot_path_can_stay_fail_closed_without_full_scan = host._hot_path_can_stay_fail_closed_without_full_scan
    _warm_runtime = host._warm_runtime
    _connect = host._connect
    _load_judgment_workstream_hint = host._load_judgment_workstream_hint
    select_impacted_diagrams = host.select_impacted_diagrams
    _collect_impacted_components = host._collect_impacted_components
    _entity_by_kind_id = host._entity_by_kind_id
    _base_workstream_candidate = host._base_workstream_candidate
    _workstream_selection = host._workstream_selection
    _collect_impacted_workstreams = host._collect_impacted_workstreams
    _collect_relevant_notes = host._collect_relevant_notes
    _collect_code_neighbors = host._collect_code_neighbors
    _collect_recommended_tests = host._collect_recommended_tests
    _collect_component_validation_commands = host._collect_component_validation_commands
    _dedupe_strings = host._dedupe_strings
    _companion_context_paths = host._companion_context_paths
    _collect_relevant_bugs = host._collect_relevant_bugs
    _collect_retrieval_miss_recovery = host._collect_retrieval_miss_recovery
    _impact_budget_profile = host._impact_budget_profile
    _limit_mappings = host._limit_mappings
    _compact_workstream_row_for_packet = host._compact_workstream_row_for_packet
    _compact_workstream_selection_for_packet = host._compact_workstream_selection_for_packet
    _compact_component_row_for_packet = host._compact_component_row_for_packet
    _compact_diagram_row_for_packet = host._compact_diagram_row_for_packet
    _compact_engineering_notes = host._compact_engineering_notes
    _limit_strings = host._limit_strings
    _recommended_validation_commands = host._recommended_validation_commands
    _compact_test_row_for_packet = host._compact_test_row_for_packet
    _component_grounded_selection_none = host._component_grounded_selection_none
    _compact_architecture_audit_for_packet = host._compact_architecture_audit_for_packet
    build_architecture_audit = host.build_architecture_audit
    _compact_code_neighbors_for_packet = host._compact_code_neighbors_for_packet
    _compact_miss_recovery_for_packet = host._compact_miss_recovery_for_packet
    record_runtime_timing = host.record_runtime_timing
    _compact_stage_timings = host._compact_stage_timings
    _compact_hot_path_payload_within_budget = host._compact_hot_path_payload_within_budget

    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}

    def _record_and_return(payload: Mapping[str, Any], *, component_count: int = 0) -> dict[str, Any]:
        payload_mapping = dict(payload)
        record_runtime_timing(
            repo_root=root,
            category="reasoning",
            operation="impact",
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            metadata={
                "changed_path_count": len(normalized),
                "component_count": int(component_count or 0),
                "workstream_count": len(payload_mapping.get("candidate_workstreams", []))
                if isinstance(payload_mapping.get("candidate_workstreams"), list)
                else 0,
                "test_count": len(payload_mapping.get("recommended_tests", []))
                if isinstance(payload_mapping.get("recommended_tests"), list)
                else 0,
                "packet_state": str(payload_mapping.get("context_packet_state", "")).strip(),
                "full_scan_recommended": bool(payload_mapping.get("full_scan_recommended")),
                "candidate_truncated": bool(
                    dict(payload_mapping.get("truncation", {})).get("candidate_workstreams", {}).get("truncated")
                )
                if isinstance(payload_mapping.get("truncation"), Mapping)
                else False,
                "notes_truncated": bool(
                    dict(payload_mapping.get("truncation", {})).get("engineering_notes", {}).get("truncated")
                )
                if isinstance(payload_mapping.get("truncation"), Mapping)
                else False,
                "estimated_bytes": int(dict(payload_mapping.get("packet_metrics", {})).get("estimated_bytes", 0) or 0)
                if isinstance(payload_mapping.get("packet_metrics"), Mapping)
                else 0,
                "estimated_tokens": int(dict(payload_mapping.get("packet_metrics", {})).get("estimated_tokens", 0) or 0)
                if isinstance(payload_mapping.get("packet_metrics"), Mapping)
                else 0,
                "within_budget": _compact_hot_path_payload_within_budget(
                    payload=payload_mapping,
                    context_packet=dict(payload_mapping.get("context_packet", {}))
                    if isinstance(payload_mapping.get("context_packet"), Mapping)
                    else {},
                    packet_metrics=dict(payload_mapping.get("packet_metrics", {}))
                    if isinstance(payload_mapping.get("packet_metrics"), Mapping)
                    else {},
                ),
                "stage_timings": _compact_stage_timings(stage_timings),
                "family_hint": str(family_profile.get("family", "")).strip(),
            },
        )
        return payload_mapping

    hot_path = _delivery_profile_hot_path(delivery_profile)
    family_profile = _impact_family_profile(
        hot_path=hot_path,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        component_hint=component_hint,
    )
    stage_started = time.perf_counter()
    guidance_catalog = (
        dict(guidance_catalog_snapshot)
        if isinstance(guidance_catalog_snapshot, Mapping)
        else tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    )
    optimization = (
        dict(optimization_snapshot)
        if isinstance(optimization_snapshot, Mapping)
        else {}
        if hot_path
        else load_runtime_optimization_snapshot(repo_root=root)
    )
    stage_timings["guidance_catalog"] = _elapsed_stage_ms(stage_started)
    stage_started = time.perf_counter()
    path_scope = _resolve_changed_path_scope_context(
        repo_root=root,
        explicit_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
        intent=intent,
    )
    stage_timings["path_scope"] = _elapsed_stage_ms(stage_started)
    normalized = list(path_scope["analysis_paths"])
    shared_only_input = _broad_shared_only_input(normalized)
    if not normalized:
        full_scan_reason = (
            "working_tree_scope_degraded"
            if bool(path_scope.get("working_tree_scope_degraded"))
            else "no_grounded_paths"
        )
        packet_state = _impact_packet_state(shared_only=False, selection_state="none")
        workstream_selection = {
            "state": "none",
            "reason": "No grounded paths were available for deterministic routing.",
            "selected_workstream": {},
            "top_candidate": {},
            "candidate_count": 0,
            "competing_candidates": [],
        }
        payload = {
            "changed_paths": [],
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "intent": str(intent or "").strip(),
            "resolved": False,
            "selection_state": "none",
            "selection_reason": str(workstream_selection.get("reason", "")).strip(),
            "selection_confidence": "none",
            "workstream_selection": workstream_selection,
            "context_packet_state": packet_state,
            "full_scan_recommended": True,
            "full_scan_reason": full_scan_reason,
            "fallback_scan": _fallback_scan_payload(
                repo_root=root,
                reason=full_scan_reason,
                changed_paths=[
                    *list(path_scope["explicit_paths"]),
                    *list(path_scope["repo_dirty_paths"]),
                ],
                delivery_profile=delivery_profile,
            ),
        }
        if not finalize_packet:
            stage_timings["finalize"] = 0.0
            return _record_and_return(payload)
        payload = tooling_context_packet_builder.finalize_packet(
            repo_root=root,
            packet_kind="impact",
            payload=payload,
            packet_state=packet_state,
            changed_paths=[],
            explicit_paths=list(path_scope["explicit_paths"]),
            shared_only_input=False,
            selection_state="none",
            workstream_selection=workstream_selection,
            candidate_workstreams=[],
            components=[],
            diagrams=[],
            docs=[],
            recommended_commands=[],
            recommended_tests=[],
            engineering_notes={},
            miss_recovery={},
            full_scan_recommended=True,
            full_scan_reason=full_scan_reason,
            session_id=session_id,
            family_hint=str(family_profile.get("family", "")).strip() or family_hint,
            guidance_catalog=guidance_catalog,
            optimization_snapshot=optimization,
            delivery_profile=delivery_profile,
        )
        if hot_path:
            payload = _compact_hot_path_runtime_packet(
                packet_kind="impact",
                payload=payload,
                retain_internal_context=retain_hot_path_internal_context,
            )
        return payload
    if (
        hot_path
        and str(family_profile.get("family", "")).strip() == "broad_shared_scope"
        and _hot_path_can_stay_fail_closed_without_full_scan(
            family_hint=str(family_profile.get("family", "")).strip(),
            changed_paths=normalized,
            explicit_paths=path_scope["explicit_paths"],
            selection_state="none",
            shared_only_input=shared_only_input,
            working_tree_scope_degraded=bool(path_scope.get("working_tree_scope_degraded")),
        )
    ):
        packet_state = _impact_packet_state(shared_only=shared_only_input, selection_state="none")
        payload = {
            "changed_paths": normalized,
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "intent": str(intent or "").strip(),
            "resolved": True,
            "selection_state": "none",
            "selection_reason": "Broad shared guidance remains intentionally fail-closed until the slice narrows.",
            "selection_confidence": "low",
            "workstream_selection": {
                "state": "none",
                "reason": "Broad shared guidance remains intentionally fail-closed until the slice narrows.",
                "selected_workstream": {},
                "top_candidate": {},
                "candidate_count": 0,
                "competing_candidates": [],
            },
            "candidate_workstreams": [],
            "components": [],
            "diagrams": [],
            "engineering_notes": {},
            "bugs": [],
            "docs": [],
            "code_neighbors": {},
            "architecture_audit": {},
            "recommended_tests": [],
            "recommended_commands": [],
            "miss_recovery": {},
            "context_packet_state": packet_state,
            "truncation": {},
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": _fallback_scan_payload(
                repo_root=root,
                reason="",
                changed_paths=normalized,
                delivery_profile=delivery_profile,
            ),
        }
        if not finalize_packet:
            stage_timings["finalize"] = 0.0
            return _record_and_return(payload)
        payload = tooling_context_packet_builder.finalize_packet(
            repo_root=root,
            packet_kind="impact",
            payload=payload,
            packet_state=packet_state,
            changed_paths=normalized,
            explicit_paths=list(path_scope["explicit_paths"]),
            shared_only_input=shared_only_input,
            selection_state="none",
            workstream_selection=payload["workstream_selection"],
            candidate_workstreams=[],
            components=[],
            diagrams=[],
            docs=[],
            recommended_commands=[],
            recommended_tests=[],
            engineering_notes={},
            miss_recovery={},
            full_scan_recommended=False,
            full_scan_reason="",
            session_id=session_id,
            family_hint=str(family_profile.get("family", "")).strip() or family_hint,
            guidance_catalog=guidance_catalog,
            optimization_snapshot=optimization,
            delivery_profile=delivery_profile,
        )
        payload = _compact_hot_path_runtime_packet(
            packet_kind="impact",
            payload=payload,
            retain_internal_context=retain_hot_path_internal_context,
        )
        return payload
    if bool(skip_runtime_warmup):
        stage_timings["runtime_warmup"] = 0.0
    else:
        stage_started = time.perf_counter()
        if not _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="impact", scope="reasoning"):
            stage_timings["runtime_warmup"] = _elapsed_stage_ms(stage_started)
            packet_state = _impact_packet_state(shared_only=shared_only_input, selection_state="none")
            workstream_selection = {
                "state": "none",
                "reason": "Runtime projections are unavailable for deterministic routing.",
                "selected_workstream": {},
                "top_candidate": {},
                "candidate_count": 0,
                "competing_candidates": [],
            }
            payload = {
                "changed_paths": normalized,
                "explicit_paths": list(path_scope["explicit_paths"]),
                "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
                "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
                "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
                "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
                "intent": str(intent or "").strip(),
                "resolved": False,
                "selection_state": "none",
                "selection_reason": str(workstream_selection.get("reason", "")).strip(),
                "selection_confidence": "none",
                "workstream_selection": workstream_selection,
                "context_packet_state": packet_state,
                "full_scan_recommended": True,
                "full_scan_reason": "runtime_unavailable",
                "fallback_scan": _fallback_scan_payload(
                    repo_root=root,
                    reason="runtime_unavailable",
                    changed_paths=normalized,
                    delivery_profile=delivery_profile,
                ),
            }
            if not finalize_packet:
                stage_timings["finalize"] = 0.0
                return _record_and_return(payload)
            payload = tooling_context_packet_builder.finalize_packet(
                repo_root=root,
                packet_kind="impact",
                payload=payload,
                packet_state=packet_state,
                changed_paths=normalized,
                explicit_paths=list(path_scope["explicit_paths"]),
                shared_only_input=shared_only_input,
                selection_state="none",
                workstream_selection=workstream_selection,
                candidate_workstreams=[],
                components=[],
                diagrams=[],
                docs=[],
                recommended_commands=[],
                recommended_tests=[],
                engineering_notes={},
                miss_recovery={},
                full_scan_recommended=True,
                full_scan_reason="runtime_unavailable",
                session_id=session_id,
                family_hint=str(family_profile.get("family", "")).strip() or family_hint,
                guidance_catalog=guidance_catalog,
                optimization_snapshot=optimization,
                delivery_profile=delivery_profile,
            )
            if hot_path:
                payload = _compact_hot_path_runtime_packet(
                    packet_kind="impact",
                    payload=payload,
                    retain_internal_context=retain_hot_path_internal_context,
                )
            return payload
        stage_timings["runtime_warmup"] = _elapsed_stage_ms(stage_started)
    connection = _connect(root)
    try:
        stage_started = time.perf_counter()
        judgment_workstream_hint = _load_judgment_workstream_hint(repo_root=root, changed_paths=normalized)
        impacted_diagrams = (
            select_impacted_diagrams(
                repo_root=root,
                changed_paths=normalized,
                runtime_mode=runtime_mode,
                skip_runtime_warmup=skip_runtime_warmup,
            )
            if bool(family_profile.get("include_diagrams", True))
            else []
        )
        diagram_ids = [str(row["diagram_id"]).strip() for row in impacted_diagrams]
        if bool(family_profile.get("prefer_explicit_component")):
            explicit_component_row = _entity_by_kind_id(
                connection,
                kind="component",
                entity_id=str(component_hint or "").strip().lower(),
            )
            components = [dict(explicit_component_row)] if isinstance(explicit_component_row, Mapping) else []
            component_selector_diagnostics = {
                "component_fast_selector_used": False,
                "component_selector_cache_hit": False,
                "component_selector_candidate_row_count": len(components),
                "component_explicit_short_circuit": True,
            }
        elif bool(family_profile.get("include_components", True)):
            components, component_selector_diagnostics = _collect_impacted_components(
                connection,
                repo_root=root,
                changed_paths=normalized,
                return_diagnostics=True,
            )
        else:
            components = []
            component_selector_diagnostics = {
                "component_fast_selector_used": False,
                "component_selector_cache_hit": False,
                "component_selector_candidate_row_count": 0,
                "component_explicit_short_circuit": False,
            }
        component_ids = [str(row["entity_id"]).strip() for row in components]
        if bool(family_profile.get("prefer_explicit_workstream")):
            explicit_workstream_row = _entity_by_kind_id(
                connection,
                kind="workstream",
                entity_id=str(workstream_hint or "").strip().upper(),
            )
            ranked_workstreams = (
                [_base_workstream_candidate(explicit_workstream_row)]
                if explicit_workstream_row is not None
                else []
            )
            workstream_selector_diagnostics = {
                "fast_selector_used": False,
                "selector_cache_hit": False,
                "selector_candidate_row_count": len(ranked_workstreams),
                "explicit_short_circuit": True,
            }
            workstream_selection = _workstream_selection(
                connection=connection,
                candidates=ranked_workstreams,
                explicit_workstream=str(workstream_hint or "").strip(),
                judgment_hint=judgment_workstream_hint,
            )
        else:
            if bool(family_profile.get("include_workstreams", True)):
                workstreams, workstream_selector_diagnostics = _collect_impacted_workstreams(
                    connection,
                    repo_root=root,
                    changed_paths=normalized,
                    component_ids=component_ids,
                    diagram_ids=diagram_ids,
                    return_diagnostics=True,
                )
                ranked_workstreams = list(workstreams)
            else:
                ranked_workstreams = []
                workstream_selector_diagnostics = {
                    "fast_selector_used": False,
                    "selector_cache_hit": False,
                    "selector_candidate_row_count": 0,
                }
            workstream_selection = _workstream_selection(
                connection=connection,
                candidates=ranked_workstreams,
                judgment_hint=judgment_workstream_hint,
            )
        primary_workstream = dict(workstream_selection.get("top_candidate", {})) if isinstance(
            workstream_selection.get("top_candidate"), Mapping
        ) else {}
        workstream_ids = [str(row["entity_id"]).strip() for row in ranked_workstreams]
        stage_timings["selection"] = _elapsed_stage_ms(stage_started)
        stage_started = time.perf_counter()
        notes = (
            _collect_relevant_notes(
                connection,
                repo_root=root,
                changed_paths=normalized,
                component_ids=component_ids,
                workstream_ids=workstream_ids,
            )
            if bool(family_profile.get("include_notes", True))
            else {}
        )
        code_neighbors = (
            _collect_code_neighbors(connection, repo_root=root, changed_paths=normalized)
            if bool(family_profile.get("include_code_neighbors", True))
            else {}
        )
        tests = (
            _collect_recommended_tests(
                connection,
                repo_root=root,
                changed_paths=normalized,
                code_neighbors=code_neighbors,
                limit=test_limit,
            )
            if bool(family_profile.get("include_tests", True))
            else []
        )
        component_commands = _collect_component_validation_commands(
            connection,
            component_ids=component_ids,
        )
        specs = _dedupe_strings([str(row.get("path", "")).strip() for row in components if str(row.get("path", "")).strip()])
        code_neighbor_docs = _dedupe_strings(
            [
                str(row.get("path", "")).strip()
                for bucket_name, bucket in code_neighbors.items()
                if bucket_name in {"documented_by", "covered_by_runbooks", "documents", "runbook_covers"}
                for row in bucket
                if isinstance(row, Mapping) and str(row.get("path", "")).strip()
            ]
        )
        companion_docs = _companion_context_paths(changed_paths=normalized, repo_root=root)
        docs = _dedupe_strings(
            [
                *companion_docs,
                *specs,
                *code_neighbor_docs,
                *[str(row.get("source_path", "")).strip() for bucket in notes.values() for row in bucket],
            ]
        )
        bugs = (
            _collect_relevant_bugs(connection, repo_root=root, component_ids=component_ids, changed_paths=normalized)
            if bool(family_profile.get("include_bugs", True))
            else []
        )
        selection_state = str(workstream_selection.get("state", "")).strip()
        miss_recovery_started = time.perf_counter()
        if bool(family_profile.get("allow_miss_recovery", True)):
            miss_recovery = _collect_retrieval_miss_recovery(
                connection,
                repo_root=root,
                changed_paths=normalized,
                shared_only_input=shared_only_input,
                selection_state=selection_state,
                component_ids=component_ids,
                docs=docs,
                tests=tests,
            )
        else:
            miss_recovery = {
                "active": False,
                "activation_reason": "family_fail_closed_grounded",
            }
        stage_timings["miss_recovery"] = _elapsed_stage_ms(miss_recovery_started)
        stage_timings["evidence"] = _elapsed_stage_ms(stage_started)
        recovery_docs = (
            [str(token).strip() for token in miss_recovery.get("recovered_docs", []) if str(token).strip()]
            if isinstance(miss_recovery.get("recovered_docs"), list)
            else []
        )
        recovery_tests = (
            [dict(row) for row in miss_recovery.get("recovered_tests", []) if isinstance(row, Mapping)]
            if isinstance(miss_recovery.get("recovered_tests"), list)
            else []
        )
        if recovery_docs:
            docs = _dedupe_strings([*recovery_docs, *docs])
        if recovery_tests:
            tests = [*recovery_tests, *tests]
        budgets = _impact_budget_profile(shared_only=shared_only_input, selection_state=selection_state)
        compact_workstreams, workstream_truncation = _limit_mappings(
            ranked_workstreams,
            limit=budgets["workstreams"],
        )
        packet_workstreams = [_compact_workstream_row_for_packet(row) for row in compact_workstreams]
        packet_workstream_selection = _compact_workstream_selection_for_packet(workstream_selection)
        packet_primary_workstream = _compact_workstream_row_for_packet(primary_workstream)
        inferred_workstream = (
            str(packet_primary_workstream.get("entity_id", "")).strip().upper()
            if selection_state in {"explicit", "inferred_confident"}
            else ""
        )
        packet_components = [_compact_component_row_for_packet(row) for row in components if isinstance(row, Mapping)]
        packet_diagrams = [_compact_diagram_row_for_packet(row) for row in impacted_diagrams if isinstance(row, Mapping)]
        compact_notes, notes_truncation = _compact_engineering_notes(
            notes,
            total_limit=budgets["notes_total"],
            per_kind_limit=budgets["notes_per_kind"],
        )
        compact_docs, docs_truncation = _limit_strings(docs, limit=budgets["docs"])
        compact_commands, commands_truncation = _limit_strings(
            _recommended_validation_commands(
                command_hints=validation_command_hints,
                component_commands=component_commands,
                tests=tests,
                changed_paths=normalized,
                notes=notes,
            ),
            limit=budgets["commands"],
        )
        compact_test_rows, tests_truncation = _limit_mappings(tests, limit=budgets["tests"])
        compact_tests = [_compact_test_row_for_packet(row) for row in compact_test_rows]
        component_grounded_selection_none = _component_grounded_selection_none(
            shared_only_input=shared_only_input,
            selection_state=selection_state,
            components=packet_components,
            diagrams=packet_diagrams,
            docs=compact_docs,
            tests=compact_tests,
            recommended_commands=compact_commands,
        )
        bounded_without_full_scan = hot_path and _hot_path_can_stay_fail_closed_without_full_scan(
            family_hint=str(family_profile.get("family", "")).strip(),
            changed_paths=normalized,
            explicit_paths=path_scope["explicit_paths"],
            selection_state=selection_state,
            shared_only_input=shared_only_input,
            working_tree_scope_degraded=bool(path_scope.get("working_tree_scope_degraded")),
        )
        full_scan_reason = ""
        if bool(path_scope.get("working_tree_scope_degraded")):
            full_scan_reason = "working_tree_scope_degraded"
        elif shared_only_input and not bounded_without_full_scan:
            full_scan_reason = "broad_shared_paths"
        elif selection_state == "ambiguous" and not bounded_without_full_scan:
            full_scan_reason = "selection_ambiguous"
        elif selection_state == "none" and not component_grounded_selection_none and not bounded_without_full_scan:
            full_scan_reason = "selection_none"
        packet_state = _impact_packet_state(shared_only=shared_only_input, selection_state=selection_state)
        architecture_audit = (
            _compact_architecture_audit_for_packet(
                build_architecture_audit(
                    repo_root=root,
                    changed_paths=normalized,
                    use_working_tree=False,
                    working_tree_scope=str(path_scope.get("working_tree_scope", "repo")).strip() or "repo",
                    session_id=str(path_scope.get("session_id", "")).strip(),
                    claimed_paths=[
                        str(token).strip()
                        for token in path_scope.get("claimed_paths", [])
                        if str(token).strip()
                    ]
                    if isinstance(path_scope.get("claimed_paths"), list)
                    else (),
                    runtime_mode=runtime_mode,
                    detail_level="packet",
                ),
                packet_state=packet_state,
            )
            if not hot_path
            else {}
        )
        payload = {
            "intent": str(intent or "").strip(),
            "resolved": True,
            "changed_paths": normalized,
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "components": packet_components,
            "primary_workstream": packet_primary_workstream,
            "inferred_workstream": inferred_workstream,
            "workstreams": packet_workstreams,
            "candidate_workstreams": packet_workstreams,
            "workstream_selection": packet_workstream_selection,
            "selection_state": selection_state,
            "selection_reason": str(packet_workstream_selection.get("reason", "")).strip(),
            "selection_confidence": str(packet_workstream_selection.get("confidence", "")).strip(),
            "diagrams": packet_diagrams,
            "engineering_notes": compact_notes,
            "bugs": bugs,
            "docs": compact_docs,
            "benchmark_selector_diagnostics": {
                **workstream_selector_diagnostics,
                **component_selector_diagnostics,
            },
            "code_neighbors": _compact_code_neighbors_for_packet(
                code_neighbors,
                summary_only=True,
            ),
            "architecture_audit": architecture_audit,
            "recommended_tests": compact_tests,
            "recommended_commands": compact_commands,
            "miss_recovery": _compact_miss_recovery_for_packet(miss_recovery),
            "context_packet_state": packet_state,
            "truncation": {
                "candidate_workstreams": workstream_truncation,
                "docs": docs_truncation,
                "recommended_commands": commands_truncation,
                "recommended_tests": tests_truncation,
                "engineering_notes": notes_truncation,
            },
            "full_scan_recommended": bool(full_scan_reason),
            "full_scan_reason": full_scan_reason,
            "fallback_scan": _fallback_scan_payload(
                repo_root=root,
                reason=full_scan_reason,
                changed_paths=normalized,
                delivery_profile=delivery_profile,
            ),
        }
        if hot_path and retain_hot_path_internal_context:
            payload["_retain_hot_path_internal_context"] = True
        if not finalize_packet:
            stage_timings["finalize"] = 0.0
            return _record_and_return(payload, component_count=len(components))
        stage_started = time.perf_counter()
        payload = tooling_context_packet_builder.finalize_packet(
            repo_root=root,
            packet_kind="impact",
            payload=payload,
            packet_state=packet_state,
            changed_paths=normalized,
            explicit_paths=list(path_scope["explicit_paths"]),
            shared_only_input=shared_only_input,
            selection_state=selection_state,
            workstream_selection=packet_workstream_selection,
            candidate_workstreams=packet_workstreams,
            components=packet_components,
            diagrams=packet_diagrams,
            docs=compact_docs,
            recommended_commands=compact_commands,
            recommended_tests=compact_tests,
            engineering_notes=compact_notes,
            miss_recovery=miss_recovery,
            full_scan_recommended=bool(full_scan_reason),
            full_scan_reason=full_scan_reason,
            session_id=session_id,
            family_hint=str(family_profile.get("family", "")).strip() or family_hint,
            guidance_catalog=guidance_catalog,
            optimization_snapshot=optimization,
            delivery_profile=delivery_profile,
        )
        stage_timings["finalize"] = _elapsed_stage_ms(stage_started)
        if hot_path:
            payload = _compact_hot_path_runtime_packet(
                packet_kind="impact",
                payload=payload,
                retain_internal_context=retain_hot_path_internal_context,
            )
        return _record_and_return(payload, component_count=len(components))
    finally:
        connection.close()
