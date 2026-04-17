"""Compact alignment payloads for chat-visible intervention surfaces.

Host hooks run on hot paths, so this module only reads already-local runtime
artifacts: session intervention stream, delivery ledger, compact runtime
surface summary, and precomputed Tribunal delivery intelligence. It does not
expand the Context Engine store, run provider calls, or scan the repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import execution_engine_handshake
from odylith.runtime.context_engine import odylith_runtime_surface_summary
from odylith.runtime.execution_engine import runtime_surface_governance
from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import delivery_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine import visibility_broker


_VISIBILITY_WORKSTREAM = "B-096"
_VISIBILITY_BUG = "CB-122"
_VISIBILITY_DIAGRAM = "D-038"
_INTERVENTION_COMPONENT = "governance-intervention-engine"
_ALIGNMENT_COMPONENTS: tuple[str, ...] = (
    _INTERVENTION_COMPONENT,
    "odylith-context-engine",
    "execution-engine",
    "odylith-memory-backend",
    "tribunal",
)


def _normalize_string(value: Any) -> str:
    return visibility_contract.normalize_string(value)


def _normalize_token(value: Any) -> str:
    return visibility_contract.normalize_token(value)


def _normalize_string_list(value: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        token = _normalize_string(value)
        return [token] if token else []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def _merge_strings(*values: Any, limit: int = 12) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        for token in _normalize_string_list(value, limit=limit):
            if token in seen:
                continue
            seen.add(token)
            rows.append(token)
            if len(rows) >= max(1, int(limit)):
                return rows
    return rows


def _runtime_surface_compact(repo_root: Path) -> dict[str, Any]:
    try:
        summary = odylith_runtime_surface_summary.load_runtime_surface_summary(repo_root=repo_root)
    except Exception:
        return {"status": "unavailable"}
    wanted = (
        "status",
        "enabled",
        "memory_status",
        "memory_backend_label",
        "memory_standardization_state",
        "route_ready_rate",
        "latest_packet_state",
        "latest_intent_family",
        "latest_packet_strategy",
        "latest_execution_engine_present",
        "latest_execution_engine_mode",
        "latest_execution_engine_next_move",
        "latest_execution_engine_outcome",
        "latest_execution_engine_snapshot_reuse_status",
        "visible_fallback_receipt_rate",
    )
    return {
        key: summary.get(key)
        for key in wanted
        if summary.get(key) not in ("", [], {}, None)
    }


def _visibility_summary(delivery_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    visible_count = int(delivery_snapshot.get("visible_event_count") or 0)
    chat_confirmed_count = int(delivery_snapshot.get("chat_confirmed_event_count") or 0)
    event_count = int(delivery_snapshot.get("event_count") or 0)
    unconfirmed_count = int(delivery_snapshot.get("unconfirmed_event_count") or 0)
    latest = delivery_snapshot.get("latest_event")
    latest_visible = delivery_snapshot.get("latest_visible_event")
    latest_unconfirmed = delivery_snapshot.get("latest_unconfirmed_event")
    proof_status = visibility_contract.proof_status_from_counts(
        visible_count=visible_count,
        chat_confirmed_count=chat_confirmed_count,
        unconfirmed_count=unconfirmed_count,
    )
    return {
        "chat_visible_proof": proof_status,
        "event_count": event_count,
        "visible_event_count": visible_count,
        "chat_confirmed_event_count": chat_confirmed_count,
        "unconfirmed_event_count": unconfirmed_count,
        "latest_delivery_status": (
            _normalize_token(latest.get("delivery_status"))
            if isinstance(latest, Mapping)
            else ""
        ),
        "latest_delivery_channel": (
            _normalize_token(latest.get("delivery_channel"))
            if isinstance(latest, Mapping)
            else ""
        ),
        "latest_visible_delivery_status": (
            _normalize_token(latest_visible.get("delivery_status"))
            if isinstance(latest_visible, Mapping)
            else ""
        ),
        "latest_unconfirmed_delivery_status": (
            _normalize_token(latest_unconfirmed.get("delivery_status"))
            if isinstance(latest_unconfirmed, Mapping)
            else ""
        ),
    }


def _target_resolution(
    *,
    changed_paths: Sequence[str],
    workstreams: Sequence[str],
    components: Sequence[str],
    bugs: Sequence[str],
    diagrams: Sequence[str],
) -> dict[str, Any]:
    candidate_targets = [
        {
            "path": path,
            "source": "host_intervention_alignment",
            "reason": "changed_path",
            "surface": "host_hook",
            "writable": True,
        }
        for path in _normalize_string_list(changed_paths, limit=8)
    ]
    diagnostic_anchors: list[dict[str, Any]] = []
    for kind, values in (
        ("workstream", workstreams),
        ("component", components),
        ("bug", bugs),
        ("diagram", diagrams),
    ):
        for token in _normalize_string_list(values, limit=8):
            diagnostic_anchors.append(
                {
                    "kind": kind,
                    "value": token,
                    "label": token,
                    "surface": "host_hook",
                    "source": "host_intervention_alignment",
                }
            )
    return {
        "lane": "odylith_product_repo",
        "candidate_targets": candidate_targets,
        "diagnostic_anchors": diagnostic_anchors[:12],
        "has_writable_targets": bool(candidate_targets),
        "requires_more_consumer_context": False,
        "consumer_failover": "",
    }


def _presentation_policy() -> dict[str, Any]:
    return {
        "commentary_mode": "task_first",
        "suppress_routing_receipts": True,
        "surface_fast_lane": True,
    }


def _packet_quality(*, visibility_failure: bool, surface_summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "intent_profile": {
            "family": "intervention_visibility" if visibility_failure else "host_intervention_checkpoint",
            "latency_sensitive": True,
            "quality_gate": "chat_visible_delivery" if visibility_failure else "earned_signal_delivery",
        },
        "evidence_profile": {
            "context_surface_status": _normalize_string(surface_summary.get("status")),
            "memory_status": _normalize_string(surface_summary.get("memory_status")),
            "execution_snapshot_available": bool(surface_summary.get("latest_execution_engine_present")),
        },
    }


def _context_packet(
    *,
    host_family: str,
    turn_phase: str,
    session_id: str,
    prompt_excerpt: str,
    assistant_summary: str,
    changed_paths: Sequence[str],
    workstreams: Sequence[str],
    components: Sequence[str],
    bugs: Sequence[str],
    diagrams: Sequence[str],
    visibility_failure: bool,
    surface_summary: Mapping[str, Any],
    target_resolution: Mapping[str, Any],
) -> dict[str, Any]:
    route_ready = bool(changed_paths or workstreams or components or bugs or diagrams or visibility_failure)
    packet_state = (
        "visibility_recovery"
        if visibility_failure
        else ("route_ready" if route_ready else "observing")
    )
    return {
        "packet_kind": "governance_slice" if route_ready else "host_intervention_context",
        "packet_state": packet_state,
        "component_id": _INTERVENTION_COMPONENT,
        "components": _normalize_string_list(components, limit=8),
        "workstreams": _normalize_string_list(workstreams, limit=8),
        "bugs": _normalize_string_list(bugs, limit=6),
        "diagrams": _normalize_string_list(diagrams, limit=6),
        "host_family": _normalize_token(host_family),
        "turn_phase": _normalize_token(turn_phase),
        "session_id": _normalize_string(session_id),
        "anchors": {
            "changed_paths": _normalize_string_list(changed_paths, limit=8),
            "workstreams": _normalize_string_list(workstreams, limit=8),
            "components": _normalize_string_list(components, limit=8),
            "bugs": _normalize_string_list(bugs, limit=6),
            "diagrams": _normalize_string_list(diagrams, limit=6),
        },
        "route": {
            "route_ready": route_ready,
            "native_spawn_ready": False,
            "narrowing_required": not route_ready,
        },
        "turn_context": {
            "intent": prompt_excerpt or assistant_summary,
            "surfaces": [_normalize_token(turn_phase)],
            "visible_text": [],
            "user_turn_id": _normalize_string(session_id),
        },
        "target_resolution": dict(target_resolution),
        "presentation_policy": _presentation_policy(),
        "packet_quality": _packet_quality(
            visibility_failure=visibility_failure,
            surface_summary=surface_summary,
        ),
        "runtime_surface_summary": dict(surface_summary),
    }


def _execution_summary(
    *,
    host_family: str,
    context_packet: Mapping[str, Any],
    changed_paths: Sequence[str],
    workstreams: Sequence[str],
    components: Sequence[str],
    prompt_excerpt: str,
    assistant_summary: str,
    visibility_failure: bool,
    target_resolution: Mapping[str, Any],
) -> dict[str, Any]:
    validation_bundle = {
        "strict_gate_command_count": 1 if visibility_failure else 0,
        "strict_gate_commands": ["prove_chat_visible_intervention"] if visibility_failure else [],
        "plan_binding_required": visibility_failure,
        "governed_surface_sync_required": False,
    }
    proof_state = (
        {
            "frontier_phase": "visibility_recovery",
            "current_blocker": "chat-visible Odylith intervention proof is unproven for this session",
            "known_failure_classes": ["hidden_hook_payload_not_chat_visible"],
        }
        if visibility_failure
        else {}
    )
    payload = {
        "packet_kind": context_packet.get("packet_kind"),
        "context_packet_state": context_packet.get("packet_state"),
        "component_id": "execution-engine",
        "target_component_ids": _merge_strings(("execution-engine",), components, limit=8),
        "changed_paths": _normalize_string_list(changed_paths, limit=8),
        "ws": _normalize_string_list(workstreams, limit=1)[0] if workstreams else "",
        "turn_context": {
            "intent": prompt_excerpt or assistant_summary,
            "surfaces": [_normalize_token(context_packet.get("turn_phase"))],
            "visible_text": [],
            "user_turn_id": _normalize_string(context_packet.get("session_id")),
        },
        "presentation_policy": _presentation_policy(),
        "target_resolution": dict(target_resolution),
        "validation_bundle": validation_bundle,
        "recommended_commands": ["odylith visible-intervention"] if visibility_failure else [],
        "proof_state": proof_state,
    }
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload=payload,
        context_packet=context_packet,
        routing_handoff=dict(context_packet.get("route", {}))
        if isinstance(context_packet.get("route"), Mapping)
        else {},
        host_candidates=(_normalize_token(host_family),),
        context_pressure="hot_path_visibility",
    )
    summary = runtime_surface_governance.summary_fields_from_execution_engine(compact)
    summary["execution_engine_host_family"] = (
        summary.get("execution_engine_host_family") or _normalize_token(host_family)
    )
    summary["execution_engine_snapshot_reuse_status"] = (
        summary.get("execution_engine_snapshot_reuse_status")
        or compact.get("snapshot_reuse_status")
        or "built_for_host_intervention"
    )
    return summary


def _tribunal_signals(
    *,
    visibility_failure: bool,
    workstreams: Sequence[str],
    components: Sequence[str],
    bugs: Sequence[str],
) -> dict[str, Any]:
    if not visibility_failure:
        return {}
    return {
        "scope_signals": [
            {
                "scope_type": "workstream",
                "scope_id": _VISIBILITY_WORKSTREAM,
                "scope_key": f"workstream:{_VISIBILITY_WORKSTREAM}",
                "scope_label": "Conversation observation and governed proposal flow",
                "case_refs": _normalize_string_list(bugs, limit=4),
                "operator_readout": {
                    "primary_scenario": "chat_visibility_regression",
                    "severity": "p0",
                    "issue": "Generated intervention payloads are not proven visible in chat.",
                    "action": "force assistant-rendered Odylith Markdown until chat confirmation lands.",
                },
            },
            {
                "scope_type": "component",
                "scope_id": _INTERVENTION_COMPONENT,
                "scope_key": f"component:{_INTERVENTION_COMPONENT}",
                "scope_label": "Governance Intervention Engine",
                "case_refs": _normalize_string_list(bugs, limit=4),
                "operator_readout": {
                    "primary_scenario": "visibility_broker_required",
                    "severity": "p0",
                    "issue": "Host-local visibility policy cannot be trusted without a delivery ledger proof.",
                    "action": "consume one broker decision across Context, Execution, Memory, and Tribunal signals.",
                },
            },
        ],
        "case_queue": [
            {
                "id": _VISIBILITY_BUG,
                "scope_key": f"component:{_INTERVENTION_COMPONENT}",
                "headline": "Intervention hooks report ready while chat sees zero visible Odylith beats",
                "brief": "Treat hidden hook payloads as non-visible until exact Markdown is confirmed in chat.",
                "systemic_theme_tags": ["chat_visibility", "host_hooks", "delivery_proof"],
            }
        ],
        "systemic_brief": {
            "headline": "Chat-visible intervention proof is the gate.",
            "summary": (
                "Context packets, execution posture, session memory, and Tribunal signals must feed the same "
                "broker decision before a host adapter can claim an Odylith Observation, Proposal, or Assist is active."
            ),
            "latent_causes": [
                "hidden hook payload counted as product success",
                "surface-local visibility policy forks",
                "delivery ledger missing chat transcript confirmation",
            ],
            "systemic_theme_tags": ["chat_visibility", "brand_signal", "brokered_delivery"],
        },
        "source": "intervention_alignment_context",
        "workstreams": _normalize_string_list(workstreams, limit=4),
        "components": _normalize_string_list(components, limit=6),
    }


def _compact_tribunal_summary(
    *,
    repo_root: Path,
    context_payload: Mapping[str, Any],
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    anchors: list[dict[str, str]] = []
    for kind in ("workstreams", "components", "bugs", "diagrams"):
        singular = {
            "workstreams": "workstream",
            "components": "component",
            "bugs": "bug",
            "diagrams": "diagram",
        }[kind]
        for token in _normalize_string_list(context_packet.get(kind), limit=6):
            anchors.append({"kind": singular, "id": token, "path": "", "label": token})
    return delivery_runtime.tribunal_context(
        context_payload=context_payload,
        repo_root=repo_root,
        anchor_artifacts=anchors,
    )


def build_host_alignment_context(
    *,
    repo_root: Path | str,
    host_family: str,
    turn_phase: str,
    session_id: str = "",
    prompt_excerpt: str = "",
    assistant_summary: str = "",
    changed_paths: Sequence[str] = (),
    workstreams: Sequence[str] = (),
    components: Sequence[str] = (),
) -> dict[str, Any]:
    """Return the shared evidence payload consumed by all visible host lanes."""

    root = Path(repo_root).expanduser().resolve()
    host = _normalize_token(host_family)
    phase = _normalize_token(turn_phase)
    prompt = _normalize_string(prompt_excerpt)
    summary = _normalize_string(assistant_summary)
    visibility_failure = visibility_broker.reports_visibility_failure(
        prompt=prompt,
        summary=summary,
    )
    resolved_workstreams = _merge_strings(
        workstreams,
        [_VISIBILITY_WORKSTREAM] if visibility_failure else [],
        limit=8,
    )
    resolved_components = _merge_strings(
        components,
        _ALIGNMENT_COMPONENTS if visibility_failure else [],
        limit=8,
    )
    bugs = [_VISIBILITY_BUG] if visibility_failure else []
    diagrams = [_VISIBILITY_DIAGRAM] if visibility_failure else []
    paths = _normalize_string_list(changed_paths, limit=12)
    delivery_snapshot = delivery_ledger.delivery_snapshot(
        repo_root=root,
        host_family=host,
        session_id=session_id,
    )
    surface_summary = _runtime_surface_compact(root)
    visibility_summary = _visibility_summary(delivery_snapshot)
    memory_summary = stream_state.session_memory_snapshot(
        repo_root=root,
        session_id=session_id,
    )
    memory_summary.update(
        {
            "visibility_complaint": visibility_failure,
            "delivery_event_count": int(delivery_snapshot.get("event_count") or 0),
            "visible_event_count": int(delivery_snapshot.get("visible_event_count") or 0),
            "host_family": host,
            "session_id": _normalize_string(session_id),
        }
    )
    target_resolution = _target_resolution(
        changed_paths=paths,
        workstreams=resolved_workstreams,
        components=resolved_components,
        bugs=bugs,
        diagrams=diagrams,
    )
    context_packet = _context_packet(
        host_family=host,
        turn_phase=phase,
        session_id=session_id,
        prompt_excerpt=prompt,
        assistant_summary=summary,
        changed_paths=paths,
        workstreams=resolved_workstreams,
        components=resolved_components,
        bugs=bugs,
        diagrams=diagrams,
        visibility_failure=visibility_failure,
        surface_summary=surface_summary,
        target_resolution=target_resolution,
    )
    execution_summary = _execution_summary(
        host_family=host,
        context_packet=context_packet,
        changed_paths=paths,
        workstreams=resolved_workstreams,
        components=resolved_components,
        prompt_excerpt=prompt,
        assistant_summary=summary,
        visibility_failure=visibility_failure,
        target_resolution=target_resolution,
    )
    tribunal_signals = _tribunal_signals(
        visibility_failure=visibility_failure,
        workstreams=resolved_workstreams,
        components=resolved_components,
        bugs=bugs,
    )
    context_payload: dict[str, Any] = {
        "host_family": host,
        "context_packet": context_packet,
        "execution_engine_summary": execution_summary,
        "memory_summary": memory_summary,
        "visibility_summary": visibility_summary,
        "delivery_snapshot": dict(delivery_snapshot),
    }
    if tribunal_signals:
        context_payload["tribunal_signals"] = tribunal_signals
    tribunal_summary = _compact_tribunal_summary(
        repo_root=root,
        context_payload=context_payload,
        context_packet=context_packet,
    )
    context_payload.update(
        {
            "tribunal_summary": tribunal_summary,
            "workstreams": resolved_workstreams,
            "components": resolved_components,
            "bugs": bugs,
            "diagrams": diagrams,
            "alignment_summary": {
                "visibility_failure": visibility_failure,
                "context_packet_present": bool(context_packet),
                "execution_engine_present": bool(execution_summary.get("execution_engine_present")),
                "memory_event_count": int(memory_summary.get("recent_event_count") or 0),
                "tribunal_signal_present": bool(tribunal_summary),
                "delivery_visible_event_count": int(delivery_snapshot.get("visible_event_count") or 0),
            },
        }
    )
    return context_payload


__all__ = ["build_host_alignment_context"]
