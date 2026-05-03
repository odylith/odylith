"""Provider budgeting and prompt helpers for Compass standup brief batching."""

from __future__ import annotations

import os

from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator

DEFAULT_BUNDLE_PROVIDER_MAX_CHARS = 18000
DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES = 4

# Context window budgets per host family. Use roughly 40% of the model's context
# window for the prompt payload to leave room for system prompt, schema, and output.
_HOST_CONTEXT_BUDGET: dict[str, tuple[int, int]] = {
    "claude": (160000, 24),
    "codex": (160000, 24),
    "unknown": (DEFAULT_BUNDLE_PROVIDER_MAX_CHARS, DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES),
}
_ABORT_FANOUT_FAILURE_CODES = frozenset(
    {
        "auth_error",
        "credits_exhausted",
        "provider_error",
        "provider_unavailable",
        "rate_limited",
        "timeout",
        "transport_error",
        "unavailable",
    }
)


def host_aware_bundle_budget(
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> tuple[int, int]:
    """Return the provider bundle budget for the resolved host family."""
    if config is None:
        return DEFAULT_BUNDLE_PROVIDER_MAX_CHARS, DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES
    provider_token = str(config.provider or "").strip().lower()
    if "claude" in provider_token:
        return _HOST_CONTEXT_BUDGET["claude"]
    if "codex" in provider_token:
        return _HOST_CONTEXT_BUDGET["codex"]
    detected = host_runtime_contract.detect_host_runtime(environ=os.environ)
    if detected == "claude_cli":
        return _HOST_CONTEXT_BUDGET["claude"]
    if detected == "codex_cli":
        return _HOST_CONTEXT_BUDGET["codex"]
    return _HOST_CONTEXT_BUDGET["unknown"]


def provider_failure_should_abort_fanout(provider: odylith_reasoning.ReasoningProvider) -> bool:
    """Return whether a provider failure should stop the remaining fanout packs."""
    metadata = odylith_reasoning.provider_failure_metadata(provider)
    return str(metadata.get("code", "")).strip().lower() in _ABORT_FANOUT_FAILURE_CODES


def batch_provider_system_prompt() -> str:
    """Return the provider prompt for one batch of scoped briefs."""
    return (
        narrator._provider_system_prompt()  # noqa: SLF001
        + " You are writing multiple scoped briefs in one batch. "
        "Return one independent four-section brief per scope_id. "
        "Never mix facts, fact ids, or workstream meaning across scopes. "
        "If one scope has thin evidence, keep that scope plainer rather than borrowing tone or detail from another scope."
    )


def window_batch_provider_system_prompt() -> str:
    """Return the provider prompt for one batch of global window briefs."""
    return (
        narrator._provider_system_prompt()  # noqa: SLF001
        + " You are writing multiple global Compass briefs in one batch. "
        "Return one independent four-section brief per window_key. "
        "Keep the 24h and 48h briefs isolated to their own fact packets. "
        "Do not flatten the two windows into one shared answer."
    )
