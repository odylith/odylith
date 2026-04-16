from __future__ import annotations

from odylith.runtime.common import agent_runtime_contract


def test_default_event_metadata_is_host_neutral() -> None:
    assert agent_runtime_contract.default_event_metadata() == ("assistant", "assistant")


def test_default_host_session_id_accepts_host_session_environment_keys() -> None:
    assert agent_runtime_contract.default_host_session_id(
        environ={"CLAUDE_CODE_SESSION_ID": "claude-session-7"}
    ) == "claude-session-7"


def test_fallback_session_token_uses_neutral_prefix_when_missing() -> None:
    assert agent_runtime_contract.fallback_session_token("", pid=42) == "agent-42"


def test_timeline_event_id_uses_agent_prefix() -> None:
    assert (
        agent_runtime_contract.timeline_event_id(
            kind="implementation",
            index=3,
            ts_iso="2026-04-11T18:22:00Z",
        )
        == "agent:implementation:3:2026-04-11T18:22:00Z"
    )


# Canonical Codex model tuples pinned by the B-072 execution-engine
# contract. These must remain byte-identical across B-084 host-family
# axis refactors; drift here is a Codex execution-ladder regression and
# must be caught by this test before it reaches the router or orchestrator.
_CODEX_CANONICAL_PROFILE_LADDER: dict[str, tuple[str, str]] = {
    agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE: ("gpt-5.4-mini", "medium"),
    agent_runtime_contract.ANALYSIS_HIGH_PROFILE: ("gpt-5.4-mini", "high"),
    agent_runtime_contract.FAST_WORKER_PROFILE: ("gpt-5.3-codex-spark", "medium"),
    agent_runtime_contract.WRITE_MEDIUM_PROFILE: ("gpt-5.3-codex", "medium"),
    agent_runtime_contract.WRITE_HIGH_PROFILE: ("gpt-5.3-codex", "high"),
    agent_runtime_contract.FRONTIER_HIGH_PROFILE: ("gpt-5.4", "high"),
    agent_runtime_contract.FRONTIER_XHIGH_PROFILE: ("gpt-5.4", "xhigh"),
}

# Canonical Claude model tuples introduced by B-084 so the execution profile
# ladder resolves to a real, differentiated model on Claude Code. Haiku serves
# analysis and fast-worker leaves, sonnet serves write-tier leaves, opus serves
# frontier-tier leaves. Reasoning effort carries the same semantic tier signal
# as the Codex column so routers that depend on the tier stay portable.
_CLAUDE_CANONICAL_PROFILE_LADDER: dict[str, tuple[str, str]] = {
    agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE: ("claude-haiku-4-5", "medium"),
    agent_runtime_contract.ANALYSIS_HIGH_PROFILE: ("claude-haiku-4-5", "high"),
    agent_runtime_contract.FAST_WORKER_PROFILE: ("claude-haiku-4-5", "medium"),
    agent_runtime_contract.WRITE_MEDIUM_PROFILE: ("claude-sonnet-4-6", "medium"),
    agent_runtime_contract.WRITE_HIGH_PROFILE: ("claude-sonnet-4-6", "high"),
    agent_runtime_contract.FRONTIER_HIGH_PROFILE: ("claude-opus-4-6", "high"),
    agent_runtime_contract.FRONTIER_XHIGH_PROFILE: ("claude-opus-4-6", "xhigh"),
}


def test_codex_execution_profile_ladder_is_byte_identical() -> None:
    for profile in agent_runtime_contract.CANONICAL_EXECUTION_PROFILES:
        fields = agent_runtime_contract.execution_profile_runtime_fields(
            profile, host_runtime="codex_cli"
        )
        assert fields == _CODEX_CANONICAL_PROFILE_LADDER[profile], (
            f"Codex profile ladder drifted for {profile}: {fields}"
        )


def test_claude_execution_profile_ladder_returns_per_profile_models() -> None:
    for profile in agent_runtime_contract.CANONICAL_EXECUTION_PROFILES:
        fields = agent_runtime_contract.execution_profile_runtime_fields(
            profile, host_runtime="claude_cli"
        )
        assert fields == _CLAUDE_CANONICAL_PROFILE_LADDER[profile], (
            f"Claude profile ladder drifted for {profile}: {fields}"
        )


def test_every_validated_host_resolves_to_non_empty_model_for_every_profile() -> None:
    # Core invariant from CB-103: no canonical profile may resolve to an
    # empty model on any validated host family. Regressing this invariant
    # means the execution profile ladder silently has no effect on that
    # host, which is the exact silent-degradation failure CB-103 fixed.
    for host_runtime in ("codex_cli", "claude_cli"):
        for profile in agent_runtime_contract.CANONICAL_EXECUTION_PROFILES:
            model, reasoning_effort = (
                agent_runtime_contract.execution_profile_runtime_fields(
                    profile, host_runtime=host_runtime
                )
            )
            assert model, (
                f"validated host {host_runtime!r} returned empty model for "
                f"canonical profile {profile!r}"
            )
            assert reasoning_effort, (
                f"validated host {host_runtime!r} returned empty reasoning "
                f"effort for canonical profile {profile!r}"
            )


def test_claude_and_codex_columns_do_not_share_models() -> None:
    # Per-host differentiation check: every canonical profile must map to a
    # distinct model family across the two validated host families. If a
    # future edit accidentally copies a Codex string into the Claude column
    # (or vice versa), this test catches the drift before it ships.
    for profile in agent_runtime_contract.CANONICAL_EXECUTION_PROFILES:
        codex_model, _ = agent_runtime_contract.execution_profile_runtime_fields(
            profile, host_runtime="codex_cli"
        )
        claude_model, _ = agent_runtime_contract.execution_profile_runtime_fields(
            profile, host_runtime="claude_cli"
        )
        assert codex_model != claude_model, (
            f"Codex and Claude columns collide on profile {profile!r}: "
            f"{codex_model!r}"
        )


def test_unknown_host_fails_closed_to_empty_model() -> None:
    # Unknown hosts must not receive a silent fallback model. CB-103's
    # prevention rule: fail closed rather than guess a cross-host default.
    model, _ = agent_runtime_contract.execution_profile_runtime_fields(
        agent_runtime_contract.FRONTIER_HIGH_PROFILE,
        host_runtime="unknown",
    )
    assert model == ""


def test_execution_profile_aliases_resolve_through_host_axis() -> None:
    # Aliased Codex profile names should also resolve correctly on both
    # validated hosts. `gpt54_high` is the legacy alias for frontier_high.
    codex_alias = agent_runtime_contract.execution_profile_runtime_fields(
        "gpt54_high", host_runtime="codex_cli"
    )
    claude_alias = agent_runtime_contract.execution_profile_runtime_fields(
        "gpt54_high", host_runtime="claude_cli"
    )
    assert codex_alias == ("gpt-5.4", "high")
    assert claude_alias == ("claude-opus-4-6", "high")
