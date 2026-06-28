"""Shared status modifier vocabulary for greenfield phrase normalization."""

from __future__ import annotations

TERMINAL_STATUS_MODIFIERS = frozenset(
    {
        "accepted",
        "active",
        "blocked",
        "closed",
        "complete",
        "completed",
        "current",
        "declined",
        "delivered",
        "denied",
        "draft",
        "eligible",
        "final",
        "finished",
        "invalid",
        "live",
        "missing",
        "open",
        "pending",
        "ready",
        "received",
        "rejected",
        "requested",
        "scheduled",
        "selected",
        "stale",
        "submitted",
        "trusted",
        "valid",
        "validated",
        "visible",
    }
)

RESULT_STATUS_MODIFIERS = TERMINAL_STATUS_MODIFIERS | frozenset(
    {
        "approved",
        "archived",
        "established",
        "exported",
        "finalized",
        "published",
        "recorded",
        "saved",
        "stored",
        "traceable",
        "verified",
        "viewable",
    }
)

RESULT_STATE_MODIFIER_LEADS = frozenset(
    {
        "accepted",
        "archived",
        "available",
        "completed",
        "exported",
        "published",
        "recorded",
        "reviewable",
        "saved",
        "stored",
        "traceable",
        "viewable",
        "visible",
    }
)

RESULT_STATE_MODIFIER_CONTEXT_TERMS = frozenset(
    {
        "archive",
        "audit",
        "comparison",
        "evidence",
        "history",
        "ledger",
        "log",
        "prior",
        "record",
        "review",
        "timeline",
    }
)

__all__ = [
    "RESULT_STATE_MODIFIER_CONTEXT_TERMS",
    "RESULT_STATE_MODIFIER_LEADS",
    "RESULT_STATUS_MODIFIERS",
    "TERMINAL_STATUS_MODIFIERS",
]
