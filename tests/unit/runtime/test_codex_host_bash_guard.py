from __future__ import annotations

import io
import json

from odylith.runtime.surfaces import codex_host_bash_guard


def test_blocked_bash_reason_catches_destructive_commands() -> None:
    assert codex_host_bash_guard.blocked_bash_reason("rm -rf build") != ""
    assert codex_host_bash_guard.blocked_bash_reason("rm -fr build") != ""
    assert codex_host_bash_guard.blocked_bash_reason("git reset --hard HEAD") != ""
    assert codex_host_bash_guard.blocked_bash_reason("pytest -q") == ""


def test_blocked_bash_reason_routes_odylith_raw_deletion_to_uninstall() -> None:
    reason = codex_host_bash_guard.blocked_bash_reason(
        "rm -rf .odylith odylith .agents .codex .claude AGENTS.md CLAUDE.md"
    )

    assert "./.odylith/bin/odylith uninstall --repo-root ." in reason
    assert "./.odylith/bin/odylith uninstall --repo-root . --dry-run" in reason
    assert "raw deletion and hook bypasses are blocked" in reason
    assert "`.claude/`, `.codex/`, and `.agents/` stay in place" in reason


def test_blocked_bash_reason_blocks_host_config_cleanup_without_saying_uninstall_removes_it() -> None:
    reason = codex_host_bash_guard.blocked_bash_reason("rm -rf .claude .codex .agents")

    assert "./.odylith/bin/odylith uninstall --repo-root ." in reason
    assert "./.odylith/bin/odylith uninstall --repo-root . --dry-run" in reason
    assert "removes `.odylith/` runtime state only" in reason
    assert "`odylith/` governed source truth" in reason
    assert "`.claude/`, `.codex/`, and `.agents/` stay in place" in reason


def test_blocked_bash_reason_blocks_python_rmtree_odylith_bypass() -> None:
    reason = codex_host_bash_guard.blocked_bash_reason(
        "python3 -c \"import shutil; shutil.rmtree('odylith')\""
    )

    assert "./.odylith/bin/odylith uninstall --repo-root ." in reason


def test_blocked_bash_reason_allows_supported_odylith_uninstall() -> None:
    assert codex_host_bash_guard.blocked_bash_reason(
        "./.odylith/bin/odylith uninstall --repo-root ."
    ) == ""


def test_main_writes_deny_payload_for_blocked_bash(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "git clean -fdx"}})),
    )

    exit_code = codex_host_bash_guard.main(["--repo-root", "."])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
