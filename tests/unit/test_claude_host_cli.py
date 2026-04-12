from __future__ import annotations

from odylith import cli


def test_claude_host_cli_dispatches_baked_bash_guard(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []

    def _fake_run_module_main(module_name: str, argv: list[str]) -> int:
        seen.append((module_name, list(argv)))
        return 0

    monkeypatch.setattr(cli, "_run_module_main", _fake_run_module_main)

    exit_code = cli.main(["claude", "bash-guard", "--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_bash_guard",
            ["--repo-root", "/tmp/repo"],
        )
    ]


def test_claude_host_cli_dispatches_post_edit_checkpoint(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["claude", "post-edit-checkpoint", "--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_post_edit_checkpoint",
            ["--repo-root", "/tmp/repo"],
        )
    ]


def test_claude_host_cli_dispatches_session_start(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["claude", "session-start", "--repo-root", "/tmp/repo", "--quiet"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_session_brief",
            ["--repo-root", "/tmp/repo", "--quiet"],
        )
    ]


def test_claude_host_cli_dispatches_subagent_start(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["claude", "subagent-start", "--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_subagent_start",
            ["--repo-root", "/tmp/repo"],
        )
    ]


def test_claude_host_cli_dispatches_subagent_stop(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["claude", "subagent-stop", "--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_subagent_stop",
            ["--repo-root", "/tmp/repo"],
        )
    ]


def test_claude_host_cli_dispatches_stop_summary(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["claude", "stop-summary", "--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_stop_summary",
            ["--repo-root", "/tmp/repo"],
        )
    ]


def test_claude_host_cli_dispatches_prompt_context(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["claude", "prompt-context", "--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_prompt_context",
            ["--repo-root", "/tmp/repo"],
        )
    ]


def test_claude_host_cli_dispatches_compatibility_command(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["claude", "compatibility", "--repo-root", "/tmp/repo", "--json"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.claude_host_compatibility",
            ["--repo-root", "/tmp/repo", "--json"],
        )
    ]
