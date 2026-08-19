from __future__ import annotations

import json
import subprocess

import greenfield_semantic_structured_host as host


def test_structured_host_never_inherits_caller_stdin(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class Process:
        returncode = 0

        def poll(self) -> int:
            return 0

    def popen(command, **kwargs):
        observed["command"] = command
        observed["stdin"] = kwargs["stdin"]
        stdout = kwargs["stdout"]
        stdout.write(json.dumps({"type": "item.started", "item": {"type": "reasoning"}}) + "\n")
        stdout.write(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": '{"ok":true}'},
                }
            )
            + "\n"
        )
        stdout.write(
            json.dumps({"type": "turn.completed", "usage": {"total_tokens": 1}})
            + "\n"
        )
        stdout.flush()
        return Process()

    monkeypatch.setattr(host.shutil, "which", lambda _: "/bin/codex")
    monkeypatch.setattr(host.subprocess, "Popen", popen)

    candidate, usage, _ = host.run_structured_host(
        schema={"type": "object"},
        prompt="author one graph",
        model="test-model",
        reasoning_effort="low",
        budget_seconds=1,
        temporary_prefix="structured-host-test-",
    )

    assert observed["stdin"] is subprocess.DEVNULL
    assert candidate == {"ok": True}
    assert usage == {"total_tokens": 1}


def test_structured_host_rejects_explicit_host_failure_events() -> None:
    payload = json.dumps({"type": "turn.failed", "error": {"message": "capacity"}})

    try:
        host._codex_result(payload)
    except RuntimeError as error:
        assert "turn.failed" in str(error)
        assert "capacity" in str(error)
    else:
        raise AssertionError("explicit host failure must fail closed")


def test_nonzero_host_failure_prefers_the_structured_failure_receipt() -> None:
    stdout = json.dumps(
        {"type": "turn.failed", "error": {"message": "capacity unavailable"}}
    )

    failure = host._codex_failure(stdout, "state database warning")

    assert "capacity unavailable" in failure
    assert "state database warning" not in failure


def test_claude_host_uses_provider_schema_without_tools_or_session_state(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    class Process:
        returncode = 0

        def poll(self) -> int:
            return 0

    def popen(command, **kwargs):
        observed["command"] = command
        observed["stdin"] = kwargs["stdin"]
        kwargs["stdout"].write(
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "structured_output": {"ok": True},
                    "usage": {"input_tokens": 4, "output_tokens": 2},
                }
            )
        )
        kwargs["stdout"].flush()
        return Process()

    monkeypatch.setattr(host.subprocess, "Popen", popen)
    candidate, usage, _ = host.run_structured_host(
        schema={"type": "object"},
        prompt="author one graph",
        model="claude-test",
        reasoning_effort="low",
        budget_seconds=1,
        temporary_prefix="structured-claude-test-",
        host_profile="claude",
        host_binary="/bin/claude",
    )

    command = observed["command"]
    assert observed["stdin"] is subprocess.DEVNULL
    assert command[0] == "/bin/claude"
    assert command[command.index("--tools") + 1] == ""
    assert "--no-session-persistence" in command
    assert command[command.index("--json-schema") + 1] == '{"type":"object"}'
    assert candidate == {"ok": True}
    assert usage == {"input_tokens": 4, "output_tokens": 2}


def test_claude_host_failure_preserves_the_provider_outcome() -> None:
    payload = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": True,
            "result": "Not logged in",
        }
    )

    try:
        host._claude_result(payload)
    except RuntimeError as error:
        assert "Not logged in" in str(error)
    else:
        raise AssertionError("explicit Claude environment failure must fail closed")
