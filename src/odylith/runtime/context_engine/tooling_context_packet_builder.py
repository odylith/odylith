"""Packet-plane helpers for Odylith Context Engine context assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.evaluation import odylith_ablation
from odylith.runtime.context_engine import tooling_context_packet_completion as packet_completion
from odylith.runtime.context_engine import tooling_context_packet_preflight as packet_preflight
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
        return packet_completion.finalize_packet_without_odylith(
            packet_kind=packet_kind,
            payload=payload,
            packet_state=packet_state,
            odylith_switch=odylith_switch,
        )
    preflight = packet_preflight.build_packet_preflight(
        repo_root=root,
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
        recommended_commands=recommended_commands,
        recommended_tests=recommended_tests,
        engineering_notes=engineering_notes,
        miss_recovery=miss_recovery,
        full_scan_recommended=full_scan_recommended,
        full_scan_reason=full_scan_reason,
        session_id=session_id,
        family_hint=family_hint,
        guidance_catalog=guidance_catalog,
        optimization_snapshot=optimization_snapshot,
        delivery_profile=delivery_profile,
    )
    packet_state = preflight.packet_state
    full_scan_recommended = preflight.full_scan_recommended
    full_scan_reason = preflight.full_scan_reason
    plan = preflight.retrieval_plan
    retrieval_bundle = preflight.retrieval_bundle
    guidance_catalog_summary = preflight.guidance_catalog_summary
    effective_recommended_commands = preflight.effective_recommended_commands
    adaptive_packet_profile = preflight.adaptive_packet_profile
    optimization = preflight.optimization
    enriched = packet_preflight.enrich_packet_payload(
        packet_kind=packet_kind,
        payload=payload,
        changed_paths=changed_paths,
        components=components,
        workstream_selection=workstream_selection,
        candidate_workstreams=candidate_workstreams,
        diagrams=diagrams,
        miss_recovery=miss_recovery,
        delivery_profile=delivery_profile,
        preflight=preflight,
        proof_state_payload=_packet_proof_state(
            repo_root=root,
            workstream_selection=workstream_selection,
            candidate_workstreams=candidate_workstreams,
            components=components,
            diagrams=diagrams,
        ),
    )
    return packet_completion.complete_packet(
        repo_root=root,
        packet_kind=packet_kind,
        packet_state=packet_state,
        enriched_payload=enriched,
        selection_state=selection_state,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        shared_only_input=shared_only_input,
        workstream_selection=workstream_selection,
        candidate_workstreams=candidate_workstreams,
        components=components,
        diagrams=diagrams,
        docs=docs,
        recommended_tests=recommended_tests,
        miss_recovery=miss_recovery,
        full_scan_recommended=full_scan_recommended,
        full_scan_reason=full_scan_reason,
        session_id=session_id,
        delivery_profile=delivery_profile,
        retrieval_plan=plan,
        retrieval_bundle=retrieval_bundle,
        guidance_catalog_summary=guidance_catalog_summary,
        effective_recommended_commands=effective_recommended_commands,
        adaptive_packet_profile=adaptive_packet_profile,
        optimization=optimization,
    )


__all__ = ["finalize_packet"]
