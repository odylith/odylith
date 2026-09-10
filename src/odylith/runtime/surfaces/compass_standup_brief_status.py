"""Presentation of Compass narration availability and provider failures."""

from __future__ import annotations

from typing import Any, Mapping


def _provider_display_name(provider: str) -> str:
    token = str(provider or "").strip().lower()
    if token == "codex-cli":
        return "Codex CLI"
    if token == "claude-cli":
        return "Claude Code"
    if token == "openai-compatible":
        return "OpenAI-compatible endpoint"
    if token == "auto-local":
        return "local provider"
    return str(provider or "").strip()


def _provider_attempt_label(*, diagnostics: Mapping[str, Any] | None = None) -> str:
    if not isinstance(diagnostics, Mapping):
        return ""
    provider_label = _provider_display_name(str(diagnostics.get("provider", "")).strip())
    model_label = str(diagnostics.get("provider_model", "") or diagnostics.get("model", "")).strip()
    if provider_label and model_label:
        return f"{provider_label} using {model_label}"
    return provider_label or model_label


def unavailable_brief_message(
    reason: str,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> str:
    token = str(reason or "").strip().lower()
    if token == "skipped_not_worth_calling":
        return "Compass skipped a fresh narrator call because the winning narrative facts did not materially change."
    if token == "provider_deferred":
        return "Compass is showing local runtime facts; a narrated brief is not available for this view."
    if token == "rate_limited":
        return "Compass hit narration provider capacity while warming this brief. It will retry on backoff."
    if token == "credits_exhausted":
        attempt_label = _provider_attempt_label(diagnostics=diagnostics)
        if attempt_label:
            return (
                "Compass could not warm this brief because the last narration attempt through "
                f"{attempt_label} may have hit a credit or budget limit. It will retry on backoff."
            )
        return "Compass could not warm this brief because the narration provider may have hit a credit or budget limit. It will retry on backoff."
    if token == "timeout":
        return "The narration provider timed out. Compass is showing local runtime facts when available and will retry on backoff."
    if token == "provider_unavailable":
        return "Compass is live. The optional narrated brief is not ready yet because the narration provider was not reachable and no exact replay exists for this packet."
    if token == "transport_error":
        return "Compass is live. The optional narrated brief could not reach the provider on the last attempt and will retry later."
    if token == "auth_error":
        return "Compass could not warm this brief because the narration provider rejected the request. Check provider access before trusting another retry."
    if token == "provider_empty":
        return "Compass did not receive a usable narration reply, and there was no exact current-packet brief to replay."
    if token == "provider_error":
        return "The narration provider failed on the last attempt. Compass will retry on backoff."
    if token == "invalid_batch":
        return "Compass received a narration reply for this brief, but the result was not usable yet. It will retry on backoff."
    if token == "validation_failed":
        return "Compass received an invalid brief, and there was no exact current-packet brief to replay."
    return "Compass could not build a current standup brief for this packet."


def unavailable_brief_title(
    reason: str,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> str:
    token = str(reason or "").strip().lower()
    if token == "skipped_not_worth_calling":
        return "Brief reused last validated narration"
    if token == "provider_deferred":
        return "Local runtime facts"
    if token == "rate_limited":
        return "Brief is waiting on provider capacity"
    if token == "credits_exhausted":
        provider_label = ""
        if isinstance(diagnostics, Mapping):
            provider_label = _provider_display_name(str(diagnostics.get("provider", "")).strip())
        if provider_label:
            return f"Brief is waiting on {provider_label} budget"
        return "Brief is waiting on provider budget"
    if token == "timeout":
        return "Narration timed out"
    if token == "provider_unavailable":
        return "Narrated brief not ready yet"
    if token == "transport_error":
        return "Narrated brief will retry"
    if token == "auth_error":
        return "Brief provider access failed"
    if token == "provider_empty":
        return "Brief provider returned nothing usable"
    if token == "provider_error":
        return "Brief unavailable right now"
    if token == "invalid_batch":
        return "Brief needs another provider pass"
    if token == "validation_failed":
        return "Brief failed validation"
    return "Standup brief unavailable"
