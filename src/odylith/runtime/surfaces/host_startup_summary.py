"""Host-neutral startup summary helpers for chat-visible Odylith hooks."""

from __future__ import annotations

import json
from typing import Any, Mapping


NARROWING_CHAT_SUMMARY = (
    "needs a narrower target before implementation. "
    "Name one code path, workstream, component, bug, or file."
)

_NARROWING_MARKERS = (
    "lane: fallback",
    "lane: narrowing",
    "need one code path",
    "gated_ambiguous",
)


def _json_payload_from_output(output: str) -> Mapping[str, Any]:
    lines = [line.strip() for line in str(output or "").splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads("\n".join(lines[index:]))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, Mapping) else {}
    return {}


def _header_before_json(output: str) -> str:
    lines: list[str] = []
    for raw_line in str(output or "").splitlines():
        line = raw_line.strip()
        if line.startswith("{"):
            break
        if line:
            lines.append(line)
    return "\n".join(lines)


def _mapping_value(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, Mapping) else {}


def startup_output_needs_narrowing(output: str) -> bool:
    """Return true when startup diagnostics should be summarized as narrowing.

    The check accepts both legacy text/json output and the current compact
    summary, so host hooks do not leak machine packet internals across Codex,
    Claude Code, or future host adapters.
    """
    text = str(output or "").strip()
    if not text:
        return False
    payload = _json_payload_from_output(text)
    if payload:
        narrowing = _mapping_value(payload, "narrowing_guidance")
        if narrowing.get("required") is True:
            return True
        context_packet = _mapping_value(payload, "context_packet")
        packet_state = str(
            context_packet.get("packet_state")
            or context_packet.get("state")
            or payload.get("packet_state")
            or ""
        ).strip().casefold()
        if packet_state == "gated_ambiguous":
            return True
        route = _mapping_value(context_packet, "route") or _mapping_value(payload, "route")
        if route.get("narrowing_required") is True:
            return True
        normalized_header = _header_before_json(text).casefold()
        return any(marker in normalized_header for marker in _NARROWING_MARKERS)
    normalized = text.casefold()
    if any(marker in normalized for marker in _NARROWING_MARKERS):
        return True
    return False


def narrowing_chat_summary(*, prefix: str = "") -> str:
    if not prefix:
        return NARROWING_CHAT_SUMMARY
    return f"{prefix}: {NARROWING_CHAT_SUMMARY}"
