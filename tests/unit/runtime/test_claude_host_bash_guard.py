from __future__ import annotations

import io
import json

from odylith.runtime.surfaces import claude_host_bash_guard


def test_evaluate_bash_command_blocks_destructive_forms() -> None:
    assert claude_host_bash_guard.evaluate_bash_command("rm -rf build")[0] is True
    assert claude_host_bash_guard.evaluate_bash_command("rm -fr build")[0] is True
    assert claude_host_bash_guard.evaluate_bash_command("git reset --hard HEAD")[0] is True
    assert claude_host_bash_guard.evaluate_bash_command("git checkout -- .")[0] is True
    assert claude_host_bash_guard.evaluate_bash_command("git push --force-with-lease")[0] is True
    assert claude_host_bash_guard.evaluate_bash_command("git clean -fdx")[0] is True


def test_evaluate_bash_command_routes_odylith_raw_deletion_to_uninstall() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command(
        "rm -rf .odylith odylith .agents .codex .claude AGENTS.md CLAUDE.md"
    )

    assert blocked is True
    assert "./.odylith/bin/odylith uninstall --repo-root ." in reason
    assert "raw deletion and hook bypasses are blocked" in reason


def test_evaluate_bash_command_blocks_python_rmtree_odylith_bypass() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command(
        "python3 -c \"import shutil; shutil.rmtree('odylith')\""
    )

    assert blocked is True
    assert "./.odylith/bin/odylith uninstall --repo-root ." in reason


def test_evaluate_bash_command_allows_supported_odylith_uninstall() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command(
        "./.odylith/bin/odylith uninstall --repo-root ."
    )

    assert blocked is False
    assert reason == ""


def test_evaluate_bash_command_allows_non_destructive_commands() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command("pytest -q")
    assert blocked is False
    assert reason == ""


def test_render_deny_payload_uses_canonical_pre_tool_use_shape() -> None:
    payload = claude_host_bash_guard.render_deny_payload("blocked")
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert payload["hookSpecificOutput"]["permissionDecisionReason"] == "blocked"


def test_main_writes_deny_payload_for_blocked_bash(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "git clean -fdx"}})),
    )

    exit_code = claude_host_bash_guard.main(["--repo-root", "."])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_emits_no_payload_when_command_is_allowed(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "pytest -q"}})),
    )

    exit_code = claude_host_bash_guard.main(["--repo-root", "."])

    assert exit_code == 0
    assert capsys.readouterr().out == ""
