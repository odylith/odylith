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
