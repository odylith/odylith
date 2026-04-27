"""Compact context-dossier payloads for delivery-facing context-engine surfaces."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import execution_engine_handshake
from odylith.runtime.context_engine import odylith_context_engine_hot_path_delivery_runtime

_condense_delivery_scope = odylith_context_engine_hot_path_delivery_runtime._condense_delivery_scope


def compact_context_dossier_for_delivery(
    dossier: Mapping[str, Any],
    *,
    relation_limit_per_kind: int = 2,
    event_limit: int = 2,
    delivery_limit: int = 1,
) -> dict[str, Any]:
    return _compact_context_dossier(
        dossier,
        relation_limit_per_kind=max(1, int(relation_limit_per_kind)),
        event_limit=max(1, int(event_limit)),
        delivery_limit=max(1, int(delivery_limit)),
    )


def _compact_context_dossier(
    dossier: Mapping[str, Any],
    *,
    relation_limit_per_kind: int = 4,
    event_limit: int = 5,
    delivery_limit: int = 3,
) -> dict[str, Any]:
    if not bool(dossier.get("resolved")):
        return {
            "resolved": False,
            "lookup": dict(dossier.get("lookup", {})) if isinstance(dossier.get("lookup"), Mapping) else {},
            "candidate_matches": dossier.get("matches", [])[:3] if isinstance(dossier.get("matches"), list) else [],
            "full_scan_recommended": bool(dossier.get("full_scan_recommended")),
            "full_scan_reason": str(dossier.get("full_scan_reason", "")).strip(),
            "fallback_scan": dict(dossier.get("fallback_scan", {}))
            if isinstance(dossier.get("fallback_scan"), Mapping)
            else {},
        }
    related = dossier.get("related_entities", {})
    entity_payload = dict(dossier.get("entity", {})) if isinstance(dossier.get("entity"), Mapping) else {}
    compact_entity = {
        key: value
        for key, value in {
            "entity_id": str(entity_payload.get("entity_id", "")).strip(),
            "title": str(entity_payload.get("title", "")).strip(),
            "status": str(entity_payload.get("status", "")).strip(),
            "priority": str(entity_payload.get("priority", "")).strip(),
            "owner": str(entity_payload.get("owner", "")).strip(),
            "workstream_type": str(entity_payload.get("workstream_type", "")).strip(),
            "plan_ref": str(entity_payload.get("plan_ref", "")).strip(),
            "diagram_id_count": len(entity_payload.get("related_diagram_ids", []))
            if isinstance(entity_payload.get("related_diagram_ids"), list)
            else 0,
            "child_count": len(entity_payload.get("workstream_children", []))
            if isinstance(entity_payload.get("workstream_children"), list)
            else 0,
            "dependency_count": len(entity_payload.get("workstream_depends_on", []))
            if isinstance(entity_payload.get("workstream_depends_on"), list)
            else 0,
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    compact_related: dict[str, list[dict[str, Any]]] = {}
    if isinstance(related, Mapping):
        for kind, rows in related.items():
            if not isinstance(rows, list):
                continue
            compact_rows = [
                _compact_related_row(row)
                for row in rows[: max(1, int(relation_limit_per_kind))]
                if isinstance(row, Mapping)
            ]
            if compact_rows:
                compact_related[str(kind)] = compact_rows
    events = dossier.get(agent_runtime_contract.AGENT_EVENT_KEY, dossier.get("recent_codex_events", []))
    compact_events = []
    if isinstance(events, list):
        for row in events[: max(1, int(event_limit))]:
            if not isinstance(row, Mapping):
                continue
            compact_events.append(
                {
                    "ts_iso": str(row.get("ts_iso", "")).strip(),
                    "kind": str(row.get("kind", "")).strip(),
                    "summary": str(row.get("summary", "")).strip(),
                    "workstreams": [str(token).strip() for token in row.get("workstreams", []) if str(token).strip()][:2]
                    if isinstance(row.get("workstreams"), list) and row.get("workstreams")
                    else [],
                    "components": [str(token).strip() for token in row.get("components", []) if str(token).strip()][:2]
                    if isinstance(row.get("components"), list) and row.get("components")
                    else [],
                }
            )
    scopes = dossier.get("delivery_scopes", [])
    compact_scopes = []
    if isinstance(scopes, list):
        compact_scopes = [
            _condense_delivery_scope(scope)
            for scope in scopes[: max(1, int(delivery_limit))]
            if isinstance(scope, Mapping)
        ]
    relations = dossier.get("relations", [])
    relation_count = len(relations) if isinstance(relations, list) else 0
    result = {
        "resolved": True,
        "entity": compact_entity,
        "lookup": dict(dossier.get("lookup", {})) if isinstance(dossier.get("lookup"), Mapping) else {},
        "related_entities": compact_related,
        agent_runtime_contract.AGENT_EVENT_KEY: compact_events,
        "delivery_scope_summaries": compact_scopes,
        "relation_count": relation_count,
        "candidate_matches": dossier.get("matches", [])[:3] if isinstance(dossier.get("matches"), list) else [],
        "full_scan_recommended": bool(dossier.get("full_scan_recommended")),
        "full_scan_reason": str(dossier.get("full_scan_reason", "")).strip(),
    }
    execution_payload = {
        "packet_kind": "context_dossier",
        "full_scan_recommended": bool(dossier.get("full_scan_recommended")),
        "full_scan_reason": str(dossier.get("full_scan_reason", "")).strip(),
    }
    result = execution_engine_handshake.attach_execution_engine_handshake(
        result,
        payload=execution_payload,
    )
    compact_execution = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload=execution_payload,
        context_packet=result,
    )
    if compact_execution:
        result["execution_engine"] = compact_execution
    return result


def _compact_related_row(row: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "entity_id": str(row.get("entity_id", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "status": str(row.get("status", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    path = str(row.get("path", "")).strip()
    entity_id = str(row.get("entity_id", "")).strip()
    if path and path != entity_id:
        compact["path"] = path
    return compact


__all__ = ["compact_context_dossier_for_delivery"]
