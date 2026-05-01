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
    assert "./.odylith/bin/odylith uninstall --repo-root . --dry-run" in reason
    assert "raw deletion and hook bypasses are blocked" in reason
    assert "detaches Odylith hook entries" in reason
    assert "`.claude/`, `.codex/`, and `.agents/` stay in place" in reason


def test_evaluate_bash_command_blocks_host_config_cleanup_without_saying_uninstall_removes_it() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command("rm -rf .claude .codex .agents")

    assert blocked is True
    assert "./.odylith/bin/odylith uninstall --repo-root ." in reason
    assert "./.odylith/bin/odylith uninstall --repo-root . --dry-run" in reason
    assert "removes `.odylith/` runtime state" in reason
    assert "detaches Odylith hook entries" in reason
    assert "`odylith/` governed source truth" in reason
    assert "`.claude/`, `.codex/`, and `.agents/` stay in place" in reason


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


def test_evaluate_bash_command_blocks_claude_backlog_complexity_mistranslation() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command(
        "./.odylith/bin/odylith backlog create --repo-root . "
        "--title 'Release governance' --complexity moderate"
    )

    assert blocked is True
    assert "Claude generated a non-canonical Odylith backlog complexity `moderate`" in reason
    assert "--complexity Medium" in reason
    assert "Low, Medium, High, VeryHigh" in reason


def test_evaluate_bash_command_allows_canonical_backlog_complexity() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command(
        "./.odylith/bin/odylith backlog create --repo-root . "
        "--title 'Release governance' --complexity Medium --sizing M"
    )

    assert blocked is False
    assert reason == ""


def test_evaluate_bash_command_blocks_claude_backlog_sizing_mistranslation() -> None:
    blocked, reason = claude_host_bash_guard.evaluate_bash_command(
        "./.odylith/bin/odylith backlog create --repo-root . "
        "--title 'Release governance' --sizing medium"
    )

    assert blocked is True
    assert "Claude generated a non-canonical Odylith backlog sizing `medium`" in reason
    assert "--sizing M" in reason
    assert "XS, S, M, L, XL" in reason


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
