"""Shared visibility semantics for Odylith intervention delivery."""

from __future__ import annotations

import hashlib
from typing import Any
from typing import Mapping

VISIBLE_DELIVERY_STATUSES: frozenset[str] = frozenset(
    {
        "assistant_chat_confirmed",
        "best_effort_visible",
        "manual_visible",
        "stop_continuation_ready",
    }
)
VISIBLE_DELIVERY_CHANNELS: frozenset[str] = frozenset(
    {
        "assistant_chat_transcript",
        "manual_visible_command",
        "stdout_teaser",
        "stop_one_shot_guard",
    }
)
CHAT_CONFIRMATION_STATUSES: frozenset[str] = frozenset(
    {
        "assistant_fallback_ready",
        "assistant_render_required",
    }
)
CHAT_CONFIRMATION_CHANNELS: frozenset[str] = frozenset(
    {
        "assistant_visible_fallback",
        "system_message_and_assistant_fallback",
    }
)
ASSISTANT_RENDER_REQUIRED_STATUS = "assistant_render_required"
ASSISTANT_RENDER_REQUIRED_CHANNEL = "assistant_visible_fallback"
LIVE_BOUNDARY = "---"
LIVE_BOUNDARY_REQUIRED_KINDS: frozenset[str] = frozenset(
    {
        "ambient_signal",
        "capture_proposed",
        "intervention_card",
        "intervention_teaser",
    }
)
VISIBILITY_FAMILIES: tuple[str, ...] = (
    "ambient",
    "intervention",
    "assist",
    "teaser",
    "other",
)


def normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def normalize_block_string(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    rows: list[str] = []
    blank_run = 0
    for raw_line in text.split("\n"):
        line = str(raw_line).rstrip()
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            rows.append("")
            continue
        blank_run = 0
        rows.append(line)
    return "\n".join(rows).strip()


def normalize_token(value: Any) -> str:
    return normalize_string(value).lower().replace(" ", "_").replace("-", "_")


def strip_live_boundary(value: Any) -> str:
    text = normalize_block_string(value)
    if text.startswith(f"{LIVE_BOUNDARY}\n") and text.endswith(f"\n{LIVE_BOUNDARY}"):
        return normalize_block_string(text[len(LIVE_BOUNDARY) + 1 : -(len(LIVE_BOUNDARY) + 1)])
    return text


def wrap_live_boundary(value: Any) -> str:
    text = strip_live_boundary(value)
    if not text:
        return ""
    return f"{LIVE_BOUNDARY}\n\n{text}\n\n{LIVE_BOUNDARY}"


def event_requires_live_boundary(row: Mapping[str, Any]) -> bool:
    return normalize_token(row.get("kind")) in LIVE_BOUNDARY_REQUIRED_KINDS


def event_display_text(row: Mapping[str, Any]) -> str:
    return normalize_block_string(row.get("display_markdown")) or normalize_block_string(row.get("display_plain"))


def event_canonical_display_text(row: Mapping[str, Any]) -> str:
    display = event_display_text(row)
    if not display:
        return ""
    if event_visibility_family(row) == "assist":
        return strip_live_boundary(display)
    if event_requires_live_boundary(row):
        return wrap_live_boundary(display)
    return display


def _display_fingerprint(value: Any) -> str:
    display = strip_live_boundary(value)
    if not display:
        return ""
    encoded = normalize_block_string(display).casefold().encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def event_confirmation_key(row: Mapping[str, Any]) -> str:
    display = event_display_text(row) or normalize_string(row.get("summary"))
    display_fingerprint = _display_fingerprint(display)
    kind = normalize_token(row.get("kind")) or "event"
    intervention_key = normalize_string(row.get("intervention_key"))
    if intervention_key and display_fingerprint:
        return f"{intervention_key}|{kind}|{display_fingerprint}"
    if intervention_key:
        return f"{intervention_key}|{kind}"
    if display_fingerprint:
        return f"{kind}|{display_fingerprint}"
    return kind


def event_host_family(row: Mapping[str, Any]) -> str:
    host = normalize_token(row.get("host_family"))
    if host:
        return host
    surface = normalize_token(row.get("render_surface"))
    if surface.startswith("codex_") or "_codex_" in surface:
        return "codex"
    if surface.startswith("claude_") or "_claude_" in surface:
        return "claude"
    return ""


def event_visibility_family(row: Mapping[str, Any]) -> str:
    label_text = " ".join(
        normalize_string(row.get(field)).lower()
        for field in ("display_markdown", "display_plain", "summary")
    )
    if "odylith assist" in label_text:
        return "assist"
    if any(label in label_text for label in ("odylith risks", "odylith history", "odylith insight")):
        return "ambient"
    if "odylith observation" in label_text or "odylith proposal" in label_text:
        return "intervention"
    kind = normalize_token(row.get("kind"))
    if kind == "ambient_signal":
        return "ambient"
    if kind in {"intervention_card", "capture_proposed"}:
        return "intervention"
    if kind == "assist_closeout":
        return "assist"
    if kind == "intervention_teaser":
        return "teaser"
    return "other"


def event_visible(row: Mapping[str, Any]) -> bool:
    status = normalize_token(row.get("delivery_status"))
    channel = normalize_token(row.get("delivery_channel"))
    return status in VISIBLE_DELIVERY_STATUSES or channel in VISIBLE_DELIVERY_CHANNELS


def event_chat_confirmed(row: Mapping[str, Any]) -> bool:
    status = normalize_token(row.get("delivery_status"))
    channel = normalize_token(row.get("delivery_channel"))
    return status == "assistant_chat_confirmed" or channel == "assistant_chat_transcript"


def event_requires_chat_confirmation(row: Mapping[str, Any]) -> bool:
    if event_visible(row):
        return False
    status = normalize_token(row.get("delivery_status"))
    channel = normalize_token(row.get("delivery_channel"))
    if status not in CHAT_CONFIRMATION_STATUSES and channel not in CHAT_CONFIRMATION_CHANNELS:
        return False
    return bool(normalize_string(row.get("display_markdown")) or normalize_string(row.get("display_plain")))


def event_needs_chat_confirmation(row: Mapping[str, Any]) -> bool:
    if event_chat_confirmed(row):
        return False
    if event_visibility_family(row) not in {"ambient", "intervention", "assist", "teaser"}:
        return False
    return bool(event_display_text(row))


def delivery_is_visible(*, channel: Any = "", status: Any = "") -> bool:
    return (
        normalize_token(status) in VISIBLE_DELIVERY_STATUSES
        or normalize_token(channel) in VISIBLE_DELIVERY_CHANNELS
    )


def proof_status_from_counts(
    *,
    visible_count: int,
    chat_confirmed_count: int,
    unconfirmed_count: int,
    static_ready: bool = True,
) -> str:
    visible = int(visible_count)
    chat_confirmed = int(chat_confirmed_count)
    unconfirmed = int(unconfirmed_count)
    if chat_confirmed > 0 and unconfirmed > 0:
        return "chat_confirmed_with_pending_confirmation"
    if visible > 0 and unconfirmed > 0:
        return "ledger_visible_with_pending_confirmation"
    if unconfirmed > 0:
        return "pending_confirmation"
    if chat_confirmed > 0:
        return "proven_this_session"
    if visible > 0:
        return "ledger_visible_unconfirmed"
    if static_ready:
        return "unproven_this_session"
    return "degraded"


def proof_status_from_snapshot(snapshot: Mapping[str, Any], *, static_ready: bool = True) -> str:
    return proof_status_from_counts(
        visible_count=int(snapshot.get("visible_event_count") or 0),
        chat_confirmed_count=int(snapshot.get("chat_confirmed_event_count") or 0),
        unconfirmed_count=int(snapshot.get("unconfirmed_event_count") or 0),
        static_ready=static_ready,
    )
