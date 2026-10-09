"""Presentation of Compass narration availability and provider failures."""

from __future__ import annotations

from typing import Any, Mapping


def unavailable_brief_message(
    reason: str,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> str:
    token = str(reason or "").strip().lower()
    if token == "skipped_not_worth_calling":
        return "The recorded facts have not changed enough for a new summary."
    if token == "provider_deferred":
        return "No summary is available for this view."
    if token == "rate_limited":
        return "The summary service is busy. Try again later."
    if token == "credits_exhausted":
        return "The summary service may be out of credits. Check its account or budget."
    if token == "timeout":
        return "The summary service took too long. Try again later."
    if token == "provider_unavailable":
        return "The summary service could not be reached."
    if token == "transport_error":
        return "The summary service could not be reached. Try again later."
    if token == "auth_error":
        return "The summary service rejected the request. Check account access."
    if token == "provider_empty":
        return "The summary service returned no usable summary."
    if token == "provider_error":
        return "The summary service failed. Try again later."
    if token == "invalid_batch":
        return "The summary could not be used. Try again later."
    if token == "validation_failed":
        return "The summary did not pass validation."
    return "A current summary is unavailable."


def unavailable_brief_title(
    reason: str,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> str:
    token = str(reason or "").strip().lower()
    if token == "skipped_not_worth_calling":
        return "No new summary"
    if token == "provider_deferred":
        return "Summary unavailable"
    if token == "rate_limited":
        return "Summary service busy"
    if token == "credits_exhausted":
        return "Summary usage limit"
    if token == "timeout":
        return "Summary timed out"
    if token == "provider_unavailable":
        return "Summary service unavailable"
    if token == "transport_error":
        return "Summary service unavailable"
    if token == "auth_error":
        return "Summary access failed"
    if token == "provider_empty":
        return "Summary unavailable"
    if token == "provider_error":
        return "Summary unavailable"
    if token == "invalid_batch":
        return "Summary unavailable"
    if token == "validation_failed":
        return "Summary validation failed"
    return "Summary unavailable"
