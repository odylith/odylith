"""Visible delivery and transcript-proof helpers for Odylith chat beats.

This module owns the last-mile text contract for ambient, intervention, and
assist delivery. It decides how branded Markdown is canonicalized, how
assistant-visible fallback instructions are phrased, and how transcript checks
decide whether a beat already appeared in chat. Host payload transport stays in
`host_surface_runtime`; the visible-delivery contract lives here.
"""

from __future__ import annotations

from odylith.runtime.intervention_engine import visibility_contract

_normalize_block_string = visibility_contract.normalize_block_string

_VISIBLE_DELIVERY_BEGIN = "<odylith-visible-markdown>"
_VISIBLE_DELIVERY_END = "</odylith-visible-markdown>"
_LIVE_DELIVERY_LABELS: tuple[str, ...] = (
    "**Odylith Observation:**",
    "Odylith Observation:",
    "Odylith Proposal:",
    "**Odylith Insight:**",
    "Odylith Insight:",
    "**Odylith History:**",
    "Odylith History:",
    "**Odylith Risks:**",
    "Odylith Risks:",
)
_DELIVERY_TAIL_LABELS: tuple[str, ...] = (
    *_LIVE_DELIVERY_LABELS,
    "Odylith is tracking this signal:",
)
_ASSIST_LABELS: tuple[str, ...] = (
    "**Odylith Assist:**",
    "Odylith Assist:",
)


def strip_visible_delivery_boundary(value: str) -> str:
    text = _normalize_block_string(value)
    if text.startswith("---\n") and text.endswith("\n---"):
        return _normalize_block_string(text[4:-4])
    return text


def split_assist_suffix(value: str) -> tuple[str, str]:
    text = _normalize_block_string(value)
    positions = [index for label in _ASSIST_LABELS if (index := text.find(label)) >= 0]
    if not positions:
        return text, ""
    first = min(positions)
    return _normalize_block_string(text[:first]), _normalize_block_string(text[first:])


def canonical_live_delivery_text(value: str) -> str:
    text = _normalize_block_string(value)
    if not text:
        return ""
    body = strip_visible_delivery_boundary(text)
    if text.startswith("---\n") and text.endswith("\n---"):
        return f"---\n\n{body}\n\n---"
    if any(label in text for label in _LIVE_DELIVERY_LABELS):
        return f"---\n\n{text}\n\n---"
    return text


def canonical_visible_delivery_text(value: str) -> str:
    text = _normalize_block_string(value)
    if not text:
        return ""
    live_part, assist_suffix = split_assist_suffix(text)
    live = canonical_live_delivery_text(live_part)
    if live and assist_suffix:
        return f"{live}\n\n{assist_suffix}"
    return live or assist_suffix


def assistant_visible_fallback_context(visible_text: str) -> str:
    visible = canonical_visible_delivery_text(visible_text)
    if not visible:
        return ""
    return "\n".join(
        [
            "Odylith visible delivery fallback:",
            (
                "The Odylith moment has not been seen in this chat. In the next visible "
                "assistant message, before any other text, emit the exact Markdown between "
                "the tags verbatim once if it is not already visible. Do not paraphrase it, "
                "do not summarize it, and do not use a code fence."
            ),
            "",
            _VISIBLE_DELIVERY_BEGIN,
            visible,
            _VISIBLE_DELIVERY_END,
        ]
    ).strip()


def strip_visible_delivery_tail(value: str) -> str:
    text = _normalize_block_string(value)
    if not text:
        return ""
    positions = [
        index
        for label in (*_DELIVERY_TAIL_LABELS, *_ASSIST_LABELS)
        if (index := text.find(label)) >= 0
    ]
    if not positions:
        return text
    prefix = _normalize_block_string(text[: min(positions)])
    while prefix.endswith("---"):
        prefix = _normalize_block_string(prefix[:-3])
    return prefix


def visible_delivery_already_present(*, last_assistant_message: str, visible_text: str) -> bool:
    last = _normalize_block_string(last_assistant_message)
    visible = canonical_visible_delivery_text(visible_text)
    if not last or not visible:
        return False
    if visible in last:
        return True
    if visible.startswith("---\n") and visible.endswith("\n---"):
        return False
    visible_body = strip_visible_delivery_boundary(visible)
    return bool(visible_body and visible_body in last)


def stop_visible_delivery_reason(visible_text: str) -> str:
    visible = canonical_visible_delivery_text(visible_text)
    if not visible:
        return ""
    return "\n\n".join(
        [
            (
                "Before ending, render the Odylith closeout below in the next visible "
                "assistant message if it is not already visible. Keep it as normal "
                "Markdown, do not wrap it in a code fence, and do not mention hook internals."
            ),
            visible,
        ]
    ).strip()


def visible_delivery_with_assist(
    *,
    developer_context: str,
    visible_text: str,
    include_assist: bool,
) -> str:
    visible = canonical_visible_delivery_text(visible_text)
    if not include_assist:
        return visible
    if visible and any(label in visible for label in _ASSIST_LABELS):
        return visible
    _live_context, assist_suffix = split_assist_suffix(developer_context)
    assist = _normalize_block_string(assist_suffix)
    if visible and assist:
        return f"{visible}\n\n{assist}"
    return visible or assist


def developer_context_with_visible_fallback(
    *,
    developer_context: str,
    visible_text: str,
    include_assist_in_visible_fallback: bool,
) -> str:
    context = _normalize_block_string(developer_context)
    visible = visible_delivery_with_assist(
        developer_context=context,
        visible_text=visible_text,
        include_assist=include_assist_in_visible_fallback,
    )
    fallback = assistant_visible_fallback_context(visible)
    if not fallback:
        return context
    if visible:
        if canonical_visible_delivery_text(context) == visible:
            context = ""
        elif visible in context:
            context = _normalize_block_string(context.replace(visible, "", 1))
        context = strip_visible_delivery_tail(context)
    if not context:
        return fallback
    return f"{fallback}\n\nOdylith developer continuity:\n{context}".strip()


__all__ = [
    "assistant_visible_fallback_context",
    "canonical_live_delivery_text",
    "canonical_visible_delivery_text",
    "developer_context_with_visible_fallback",
    "stop_visible_delivery_reason",
    "strip_visible_delivery_boundary",
    "strip_visible_delivery_tail",
    "split_assist_suffix",
    "visible_delivery_already_present",
    "visible_delivery_with_assist",
]
