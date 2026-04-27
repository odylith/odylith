from __future__ import annotations

from odylith import cli


def test_codex_host_cli_dispatches_to_the_expected_module(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []

    def _fake_run_module_main(module_name: str, argv: list[str]) -> int:
        seen.append((module_name, list(argv)))
        return 0

    monkeypatch.setattr(cli, "_run_module_main", _fake_run_module_main)

    exit_code = cli.main(["codex", "bash-guard", "--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.codex_host_bash_guard",
            ["--repo-root", "/tmp/repo"],
        )
    ]


def test_codex_host_cli_fast_path_handles_repo_root_and_forwarded_args(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["codex", "prompt-context", "--repo-root", "/tmp/repo", "--"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.codex_host_prompt_context",
            ["--repo-root", "/tmp/repo", "--"],
        )
    ]


def test_codex_host_cli_dispatches_compatibility_command(monkeypatch) -> None:
    seen: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cli,
        "_run_module_main",
        lambda module_name, argv: seen.append((module_name, list(argv))) or 0,
    )

    exit_code = cli.main(["codex", "compatibility", "--repo-root", "/tmp/repo", "--json"])

    assert exit_code == 0
    assert seen == [
        (
            "odylith.runtime.surfaces.codex_host_compatibility",
            ["--repo-root", "/tmp/repo", "--json"],
        )
    ]
