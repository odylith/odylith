"""Execution Engine summary normalization for the subagent router."""

from __future__ import annotations

from typing import Any
from typing import Mapping

from odylith.runtime.context_engine import execution_engine_handshake
from odylith.runtime.execution_engine import runtime_surface_governance


def execution_engine_summary_from_context_sources(
    *,
    context_signals: Mapping[str, Any],
    root: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    execution_engine_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return router-ready summary fields from a Context-to-Execution snapshot."""

    if not execution_engine_payload:
        return {}
    execution_payload = dict(root) if isinstance(root, Mapping) else dict(context_signals)
    execution_payload["execution_engine"] = dict(execution_engine_payload)
    if context_packet:
        execution_payload.setdefault("context_packet", dict(context_packet))
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload=execution_payload,
        context_packet=context_packet,
    )
    return runtime_surface_governance.summary_fields_from_execution_engine(compact)


__all__ = ["execution_engine_summary_from_context_sources"]
