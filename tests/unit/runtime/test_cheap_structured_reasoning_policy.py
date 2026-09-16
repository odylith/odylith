"""Current cheap-model transitions preserve failure and retry ownership."""

from copy import deepcopy
from dataclasses import replace
import subprocess

import pytest

from odylith.runtime.reasoning import odylith_reasoning as reasoning
from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance
from odylith.runtime.surfaces import compass_standup_brief_maintenance_worker as worker


@pytest.fixture
def config(monkeypatch):
    def refuse_native_dispatch(*_args, **_kwargs):
        raise AssertionError("Policy controls must not dispatch native providers")

    monkeypatch.setattr(reasoning.subprocess, "run", refuse_native_dispatch)
    return reasoning.ReasoningConfig(
        mode="auto", provider="codex-cli", model="", base_url="", api_key="",
        scope_cap=5, timeout_seconds=20.0,
    )


@pytest.mark.parametrize("model,next_model", [
    ("gpt-5.3-codex-spark", "gpt-5.6-luna"),
    ("gpt-5.6-luna", "gpt-5.6-terra"),
    ("gpt-5.6-terra", "gpt-5.6-terra"),
])
@pytest.mark.parametrize("error,returncode,code,may_advance", [
    ("Unknown model: {model}. This model is not supported when using Codex with a ChatGPT account.",
     1, "provider_error", True),
    ("You've hit your usage limit.", 1, "credits_exhausted", True),
    ("Rate limit reached.", 1, "rate_limited", True),
    ("Authentication failed.", 1, "auth_error", False),
    ("The response is not JSON.", 0, "invalid_response", False),
])
def test_native_failure_drives_only_existing_ladder_advancement(
    tmp_path, monkeypatch, config, model, next_model, error, returncode, code, may_advance,
):
    monkeypatch.setattr(reasoning.shutil, "which", lambda _token: "/mock/codex")
    monkeypatch.setattr(reasoning.subprocess, "run", lambda command, **_kwargs:
                        subprocess.CompletedProcess(command, returncode, "", error.format(model=model)))
    provider = reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path, codex_bin="codex", model=model,
        timeout_seconds=20.0, reasoning_effort="medium",
    )
    result = provider.generate_structured(request=reasoning.StructuredReasoningRequest(
        system_prompt="Return the supplied data.", schema_name="policy_control",
        output_schema={"type": "object"}, prompt_payload={},
    ))
    assert result is None
    assert provider.last_failure_code == code
    assert provider.last_request_model == model
    failure = {"previous_model": model, "failure_code": provider.last_failure_code,
               "failure_detail": provider.last_failure_detail}
    assert reasoning.cheap_structured_reasoning_failure_can_advance(
        provider="codex-cli", **failure,
    ) is (may_advance and model != "gpt-5.6-terra")
    profile = reasoning.cheap_structured_reasoning_profile(
        replace(config, model=model), environ={}, **failure,
    )
    assert profile.model == (next_model if may_advance else model)
    assert profile.reasoning_effort == "medium"


@pytest.mark.parametrize("model", ["gpt-5.4", "gpt-5.4-mini", "custom-user-model"])
def test_cheap_policy_keeps_existing_membership_rule(config, model):
    profile = reasoning.cheap_structured_reasoning_profile(replace(config, model=model), environ={})
    assert profile.model == "gpt-5.3-codex-spark"
    assert not reasoning.cheap_structured_reasoning_failure_can_advance(
        provider="codex-cli", previous_model=model,
        failure_code="provider_error", failure_detail=f"Unknown model: {model}",
    )


def test_complete_api_configuration_keeps_explicit_model(config):
    profile = reasoning.cheap_structured_reasoning_profile(replace(
        config, provider="openai-compatible", model="gpt-5.4",
        base_url="https://api.example.invalid/v1", api_key="test-only",
    ), environ={})
    assert (profile.provider, profile.model, profile.reasoning_effort) == (
        "openai-compatible", "gpt-5.4", "",
    )


@pytest.mark.parametrize("fingerprint", ["same-facts", "new-facts"])
def test_retired_model_history_does_not_bypass_matching_future_backoff(config, fingerprint):
    entry = {
        "fingerprint": "same-facts", "status": "failed", "attempt_count": 3,
        "provider_name": "CodexCliReasoningProvider", "attempted_utc": "2026-09-15T17:38:05Z",
        "next_retry_utc": "2099-01-01T00:00:00Z",
        "diagnostics": {"provider": "codex-cli", "provider_model": "gpt-5.4",
                        "provider_failure_code": "provider_error",
                        "provider_failure_detail": "Unknown model: gpt-5.4"},
    }
    request = {"global": {"24h": {"fingerprint": fingerprint, "fact_packet": {"facts": []}}}}
    state = {"entries": {"global:24h": entry}}
    original = deepcopy((request, state))
    delay = worker.pending_request_delay_seconds(
        request=request, state_entries=state["entries"], current_provider_name="CodexCliReasoningProvider",
    )
    assert delay is not None
    assert (delay > 0) if fingerprint == "same-facts" else (delay == 0)
    failure = maintenance._requested_state_failure_context(state=state, request=request)
    assert failure.get("previous_model", "") == ("gpt-5.4" if fingerprint == "same-facts" else "")
    assert reasoning.cheap_structured_reasoning_profile(config, environ={}, **failure).model == "gpt-5.3-codex-spark"
    assert not maintenance._provider_failure_can_retry_immediately(entry["diagnostics"])
    assert (request, state) == original
