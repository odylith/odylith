from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.common import command_surface
from odylith.runtime.evaluation import benchmark_compare as _real_benchmark_compare


def _parser_nodes(parser: argparse.ArgumentParser, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    nodes: set[tuple[str, ...]] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                path = (*prefix, name)
                nodes.add(path)
                nodes.update(_parser_nodes(child, path))
    return nodes


def _parser_leaf_paths(parser: argparse.ArgumentParser) -> set[tuple[str, ...]]:
    all_nodes = _parser_nodes(parser)
    return {path for path in all_nodes if not any(other[: len(path)] == path and other != path for other in all_nodes)}


def _assert_help_ok(argv: list[str]) -> None:
    try:
        rc = cli.main(argv)
    except SystemExit as exc:
        assert exc.code == 0
    else:
        assert rc == 0


def test_cli_help_smoke_covers_every_parser_node(monkeypatch, tmp_path: Path) -> None:
    parser = cli.build_parser()
    nodes = _parser_nodes(parser)

    monkeypatch.setattr(cli.subagent_router, "main", lambda argv: 0)
    monkeypatch.setattr(cli.subagent_orchestrator, "main", lambda argv: 0)

    _assert_help_ok(["--help"])
    for path in sorted(nodes):
        _assert_help_ok([*path, "--help"])


_HANDLER_CASES = [
    {
        "path": ("start",),
        "argv": lambda root: ["start", f"--repo-root={root}"],
        "handler": "_cmd_start",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("install",),
        "argv": lambda root: ["install", f"--repo-root={root}"],
        "handler": "_cmd_install",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("reinstall",),
        "argv": lambda root: ["reinstall", f"--repo-root={root}"],
        "handler": "_cmd_reinstall",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("upgrade",),
        "argv": lambda root: ["upgrade", f"--repo-root={root}"],
        "handler": "_cmd_upgrade",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("rollback",),
        "argv": lambda root: ["rollback", f"--repo-root={root}", "--previous"],
        "handler": "_cmd_rollback",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root) and bool(getattr(args, "previous", False)),
    },
    {
        "path": ("version",),
        "argv": lambda root: ["version", f"--repo-root={root}"],
        "handler": "_cmd_version",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("doctor",),
        "argv": lambda root: ["doctor", f"--repo-root={root}", "--repair"],
        "handler": "_cmd_doctor",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root) and bool(getattr(args, "repair", False)),
    },
    {
        "path": ("migrate-legacy-install",),
        "argv": lambda root: ["migrate-legacy-install", f"--repo-root={root}"],
        "handler": "_cmd_migrate_legacy_install",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("uninstall",),
        "argv": lambda root: ["uninstall", f"--repo-root={root}"],
        "handler": "_cmd_uninstall",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("on",),
        "argv": lambda root: ["on", f"--repo-root={root}"],
        "handler": "_cmd_on",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("off",),
        "argv": lambda root: ["off", f"--repo-root={root}"],
        "handler": "_cmd_off",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("sync",),
        "argv": lambda root: ["sync", f"--repo-root={root}", "--check-only"],
        "handler": "_cmd_sync",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root) and list(getattr(args, "forwarded", [])) == ["--check-only"],
    },
    {
        "path": ("dashboard", "refresh"),
        "argv": lambda root: ["dashboard", "refresh", f"--repo-root={root}"],
        "handler": "_cmd_dashboard_refresh",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("backlog", "create"),
        "argv": lambda root: ["backlog", "create", f"--repo-root={root}"],
        "handler": "_cmd_backlog",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root) and getattr(args, "backlog_command", "") == "create",
    },
    {
        "path": ("release", "list"),
        "argv": lambda root: ["release", "list", f"--repo-root={root}"],
        "handler": "_cmd_release",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root) and getattr(args, "release_command", "") == "list",
    },
    {
        "path": ("release", "show"),
        "argv": lambda root: ["release", "show", f"--repo-root={root}", "current"],
        "handler": "_cmd_release",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root)
        and getattr(args, "release_command", "") == "show"
        and list(getattr(args, "forwarded", [])) == ["current"],
    },
    {
        "path": ("release", "create"),
        "argv": lambda root: ["release", "create", f"--repo-root={root}", "release-0-1-11"],
        "handler": "_cmd_release",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root)
        and getattr(args, "release_command", "") == "create"
        and list(getattr(args, "forwarded", [])) == ["release-0-1-11"],
    },
    {
        "path": ("release", "update"),
        "argv": lambda root: ["release", "update", f"--repo-root={root}", "current", "--name", "Launch"],
        "handler": "_cmd_release",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root)
        and getattr(args, "release_command", "") == "update"
        and list(getattr(args, "forwarded", [])) == ["current", "--name", "Launch"],
    },
    {
        "path": ("release", "add"),
        "argv": lambda root: ["release", "add", f"--repo-root={root}", "B-101", "current"],
        "handler": "_cmd_release",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root)
        and getattr(args, "release_command", "") == "add"
        and list(getattr(args, "forwarded", [])) == ["B-101", "current"],
    },
    {
        "path": ("release", "remove"),
        "argv": lambda root: ["release", "remove", f"--repo-root={root}", "B-101", "current"],
        "handler": "_cmd_release",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root)
        and getattr(args, "release_command", "") == "remove"
        and list(getattr(args, "forwarded", [])) == ["B-101", "current"],
    },
    {
        "path": ("release", "move"),
        "argv": lambda root: ["release", "move", f"--repo-root={root}", "B-101", "next", "--from-release", "current"],
        "handler": "_cmd_release",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root)
        and getattr(args, "release_command", "") == "move"
        and list(getattr(args, "forwarded", [])) == ["B-101", "next", "--from-release", "current"],
    },
    {
        "path": ("compass", "log"),
        "argv": lambda root: ["compass", "log", f"--repo-root={root}"],
        "handler": "_cmd_compass_log",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("compass", "refresh"),
        "argv": lambda root: ["compass", "refresh", f"--repo-root={root}"],
        "handler": "_cmd_compass_refresh",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("compass", "update"),
        "argv": lambda root: ["compass", "update", f"--repo-root={root}"],
        "handler": "_cmd_compass_update",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("compass", "restore-history"),
        "argv": lambda root: ["compass", "restore-history", f"--repo-root={root}"],
        "handler": "_cmd_compass_restore_history",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("compass", "watch-transactions"),
        "argv": lambda root: ["compass", "watch-transactions", f"--repo-root={root}"],
        "handler": "_cmd_compass_watch_transactions",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("atlas", "render"),
        "argv": lambda root: ["atlas", "render", f"--repo-root={root}"],
        "handler": "_cmd_atlas_render",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("atlas", "auto-update"),
        "argv": lambda root: ["atlas", "auto-update", f"--repo-root={root}"],
        "handler": "_cmd_atlas_auto_update",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("atlas", "scaffold"),
        "argv": lambda root: ["atlas", "scaffold", f"--repo-root={root}"],
        "handler": "_cmd_atlas_scaffold",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
    {
        "path": ("atlas", "install-autosync-hook"),
        "argv": lambda root: ["atlas", "install-autosync-hook", f"--repo-root={root}"],
        "handler": "_cmd_atlas_install_autosync_hook",
        "check": lambda args, root: getattr(args, "repo_root", "") == str(root),
    },
]

for governance_command in (
    "normalize-plan-risk-mitigation",
    "backfill-workstream-traceability",
    "reconcile-plan-workstream-binding",
    "auto-promote-workstream-phase",
    "sync-component-spec-requirements",
    "version-truth",
    "validate-guidance-portability",
    "validate-plan-traceability",
):
    _HANDLER_CASES.append(
        {
            "path": ("governance", governance_command),
            "argv": lambda root, command=governance_command: ["governance", command, f"--repo-root={root}"],
            "handler": "_cmd_governance",
            "check": lambda args, root, command=governance_command: getattr(args, "repo_root", "") == str(root)
            and getattr(args, "governance_command", "") == command,
        }
    )


for program_command in (
    "create",
    "update",
    "list",
    "show",
    "status",
    "next",
):
    _HANDLER_CASES.append(
        {
            "path": ("program", program_command),
            "argv": lambda root, command=program_command: ["program", command, f"--repo-root={root}"],
            "handler": "_cmd_program",
            "check": lambda args, root, command=program_command: getattr(args, "repo_root", "") == str(root)
            and getattr(args, "program_command", "") == command,
        }
    )


for wave_command in (
    "create",
    "update",
    "assign",
    "unassign",
    "gate-add",
    "gate-remove",
    "status",
):
    _HANDLER_CASES.append(
        {
            "path": ("wave", wave_command),
            "argv": lambda root, command=wave_command: ["wave", command, f"--repo-root={root}"],
            "handler": "_cmd_wave",
            "check": lambda args, root, command=wave_command: getattr(args, "repo_root", "") == str(root)
            and getattr(args, "wave_command", "") == command,
        }
    )


for codex_command in (
    "bash-guard",
    "compatibility",
    "post-bash-checkpoint",
    "prompt-context",
    "session-start-ground",
    "stop-summary",
):
    _HANDLER_CASES.append(
        {
            "path": ("codex", codex_command),
            "argv": lambda root, command=codex_command: ["codex", command, f"--repo-root={root}"],
            "handler": "_cmd_codex_host_command",
            "check": lambda args, root, command=codex_command: getattr(args, "repo_root", "") == str(root)
            and getattr(args, "codex_command", "") == command,
        }
    )


for claude_command in (
    "bash-guard",
    "compatibility",
    "post-edit-checkpoint",
    "pre-compact-snapshot",
    "prompt-context",
    "session-start",
    "statusline",
    "stop-summary",
    "subagent-start",
    "subagent-stop",
):
    _HANDLER_CASES.append(
        {
            "path": ("claude", claude_command),
            "argv": lambda root, command=claude_command: ["claude", command, f"--repo-root={root}"],
            "handler": "_cmd_claude_host_command",
            "check": lambda args, root, command=claude_command: getattr(args, "repo_root", "") == str(root)
            and getattr(args, "claude_command", "") == command,
        }
    )


@pytest.mark.parametrize("case", _HANDLER_CASES, ids=lambda case: " ".join(case["path"]))
def test_cli_handler_dispatch_matrix(monkeypatch, tmp_path: Path, case: dict[str, object]) -> None:
    captured: dict[str, object] = {}

    def fake_handler(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 91

    monkeypatch.setattr(cli, str(case["handler"]), fake_handler)

    rc = cli.main(case["argv"](tmp_path))

    assert rc == 91
    assert "args" in captured
    assert case["check"](captured["args"], tmp_path)


_SHORTCUT_CASES = [
    {
        "path": ("bootstrap",),
        "argv": lambda root: ["bootstrap", f"--repo-root={root}"],
        "target_command": "bootstrap-session",
        "forwarded": ["--working-tree"],
    },
    {
        "path": ("context",),
        "argv": lambda root: ["context", f"--repo-root={root}", "entity-ref"],
        "target_command": "context",
        "forwarded": ["entity-ref"],
    },
    {
        "path": ("query",),
        "argv": lambda root: ["query", f"--repo-root={root}", "launchpad"],
        "target_command": "query",
        "forwarded": ["launchpad"],
    },
    {
        "path": ("session-brief",),
        "argv": lambda root: ["session-brief", f"--repo-root={root}"],
        "target_command": "session-brief",
        "forwarded": [],
    },
    {
        "path": ("impact",),
        "argv": lambda root: ["impact", f"--repo-root={root}"],
        "target_command": "impact",
        "forwarded": [],
    },
    {
        "path": ("architecture",),
        "argv": lambda root: ["architecture", f"--repo-root={root}"],
        "target_command": "architecture",
        "forwarded": [],
    },
    {
        "path": ("governance-slice",),
        "argv": lambda root: ["governance-slice", f"--repo-root={root}"],
        "target_command": "governance-slice",
        "forwarded": [],
    },
]


@pytest.mark.parametrize("case", _SHORTCUT_CASES, ids=lambda case: " ".join(case["path"]))
def test_cli_context_shortcut_dispatch_matrix(monkeypatch, tmp_path: Path, case: dict[str, object]) -> None:
    captured: dict[str, object] = {}

    def fake_dispatch_context_engine_shortcut(*, repo_root: str, target_command: str, forwarded: list[str]) -> int:
        captured["repo_root"] = repo_root
        captured["target_command"] = target_command
        captured["forwarded"] = list(forwarded)
        return 92

    monkeypatch.setattr(cli, "_dispatch_context_engine_shortcut", fake_dispatch_context_engine_shortcut)

    rc = cli.main(case["argv"](tmp_path))

    assert rc == 92
    assert captured["repo_root"] == str(tmp_path)
    assert captured["target_command"] == case["target_command"]
    assert captured["forwarded"] == case["forwarded"]


_DOWNSTREAM_ARGV_CASES = [
    {
        "path": ("lane", "status"),
        "argv": lambda root: ["lane", "status", f"--repo-root={root}"],
        "target_obj": cli.maintainer_lane_status,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "backlog-contract"),
        "argv": lambda root: ["validate", "backlog-contract", f"--repo-root={root}"],
        "target_obj": cli.validate_backlog_contract,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "component-registry"),
        "argv": lambda root: ["validate", "component-registry", f"--repo-root={root}"],
        "target_obj": cli.validate_component_registry_contract,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "component-registry-contract"),
        "argv": lambda root: ["validate", "component-registry-contract", f"--repo-root={root}"],
        "target_obj": cli.validate_component_registry_contract,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "guidance-portability"),
        "argv": lambda root: ["validate", "guidance-portability", f"--repo-root={root}"],
        "target_obj": cli.validate_guidance_portability,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "plan-risk-mitigation"),
        "argv": lambda root: ["validate", "plan-risk-mitigation", f"--repo-root={root}"],
        "target_obj": cli.validate_plan_risk_mitigation_contract,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "plan-risk-mitigation-contract"),
        "argv": lambda root: ["validate", "plan-risk-mitigation-contract", f"--repo-root={root}"],
        "target_obj": cli.validate_plan_risk_mitigation_contract,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "self-host-posture"),
        "argv": lambda root: ["validate", "self-host-posture", f"--repo-root={root}"],
        "target_obj": cli.validate_self_host_posture,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "plan-traceability"),
        "argv": lambda root: ["validate", "plan-traceability", f"--repo-root={root}"],
        "target_obj": cli.validate_plan_traceability_contract,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "plan-workstream-binding"),
        "argv": lambda root: ["validate", "plan-workstream-binding", f"--repo-root={root}"],
        "target_obj": cli.validate_plan_workstream_binding,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("validate", "version-truth"),
        "argv": lambda root: ["validate", "version-truth", f"--repo-root={root}"],
        "target_obj": cli.version_truth,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root), "check"],
    },
    {
        "path": ("context-engine",),
        "argv": lambda root: ["context-engine", f"--repo-root={root}"],
        "target_obj": cli.odylith_context_engine,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root)],
    },
    {
        "path": ("benchmark",),
        "argv": lambda root: ["benchmark", f"--repo-root={root}"],
        "target_obj": cli.odylith_context_engine,
        "target_attr": "main",
        "expected_argv": lambda root: ["--repo-root", str(root), "benchmark"],
    },
    {
        "path": ("subagent-router",),
        "argv": lambda root: ["subagent-router", f"--repo-root={root}", "show-tuning"],
        "target_obj": cli.subagent_router,
        "target_attr": "main",
        "expected_argv": lambda root: ["show-tuning", "--repo-root", str(root)],
    },
    {
        "path": ("subagent-orchestrator",),
        "argv": lambda root: ["subagent-orchestrator", f"--repo-root={root}", "show-tuning"],
        "target_obj": cli.subagent_orchestrator,
        "target_attr": "main",
        "expected_argv": lambda root: ["show-tuning", "--repo-root", str(root)],
    },
]


@pytest.mark.parametrize("case", _DOWNSTREAM_ARGV_CASES, ids=lambda case: " ".join(case["path"]))
def test_cli_downstream_argv_dispatch_matrix(monkeypatch, tmp_path: Path, case: dict[str, object]) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 93

    monkeypatch.setattr(case["target_obj"], case["target_attr"], fake_main)

    rc = cli.main(case["argv"](tmp_path))

    assert rc == 93
    assert captured["argv"] == case["expected_argv"](tmp_path)


def test_cli_benchmark_compare_dispatch_and_json(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}

    class _FakeResult:
        status = "pass"

        def as_dict(self) -> dict[str, object]:
            return {"status": "pass", "baseline": "golden"}

    monkeypatch.setattr(
        _real_benchmark_compare,
        "compare_latest_to_baseline",
        lambda *, repo_root, baseline: captured.update({"repo_root": repo_root, "baseline": baseline}) or _FakeResult(),
    )
    monkeypatch.setattr(_real_benchmark_compare, "render_compare_text", lambda result: "compare text")

    rc = cli.main(["benchmark", f"--repo-root={tmp_path}", "compare", "--baseline", "golden", "--json"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["baseline"] == "golden"
    assert '"status": "pass"' in output


def test_cli_dispatch_matrix_covers_every_parser_leaf() -> None:
    parser = cli.build_parser()
    leaf_paths = _parser_leaf_paths(parser)
    covered_paths = {tuple(case["path"]) for case in _HANDLER_CASES}
    covered_paths.update(tuple(case["path"]) for case in _SHORTCUT_CASES)
    covered_paths.update(tuple(case["path"]) for case in _DOWNSTREAM_ARGV_CASES)

    assert leaf_paths == covered_paths


def test_extract_repo_root_accepts_equals_syntax_and_stops_at_double_dash(tmp_path: Path) -> None:
    repo_root, forwarded = cli._extract_repo_root(  # noqa: SLF001
        [f"--repo-root={tmp_path}", "--force", "--", "--repo-root", "literal"]
    )

    assert repo_root == str(tmp_path)
    assert forwarded == ["--force", "--", "--repo-root", "literal"]


def test_extract_repo_root_rejects_blank_value() -> None:
    with pytest.raises(SystemExit, match="--repo-root requires a value"):
        cli._extract_repo_root(["--repo-root="])  # noqa: SLF001


def test_help_requested_ignores_literal_help_after_double_dash() -> None:
    assert cli._help_requested(["--check-only", "--", "--help"]) is False  # noqa: SLF001
    assert cli._help_requested(["--help", "--", "--check-only"]) is True  # noqa: SLF001


def test_forwarded_has_flag_ignores_literal_flag_after_double_dash() -> None:
    assert cli._forwarded_has_flag(["--", "--check-only"], "--check-only") is False  # noqa: SLF001
    assert cli._forwarded_has_flag(["--check-only", "--", "--force"], "--check-only") is True  # noqa: SLF001


def test_sync_double_dash_literal_check_only_does_not_bypass_main_branch_guard(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_guard_product_repo_main_branch", lambda **kwargs: 2)
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "main",
        lambda argv: (_ for _ in ()).throw(AssertionError("guarded sync should not run")),
    )

    rc = cli.main(["sync", f"--repo-root={tmp_path}", "--", "--check-only"])

    assert rc == 2


def test_sync_double_dash_literal_help_does_not_trigger_top_level_help(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_cmd_sync(args: argparse.Namespace) -> int:
        captured["forwarded"] = list(args.forwarded)
        captured["repo_root"] = args.repo_root
        return 94

    monkeypatch.setattr(cli, "_cmd_sync", fake_cmd_sync)

    rc = cli.main(["sync", f"--repo-root={tmp_path}", "--", "--help"])

    assert rc == 94
    assert captured["repo_root"] == str(tmp_path)
    assert captured["forwarded"] == ["--", "--help"]


@pytest.mark.parametrize("runtime_mode", ["auto", "standalone", "daemon"])
def test_dashboard_refresh_runtime_mode_choice_matrix(runtime_mode: str) -> None:
    args = cli.build_parser().parse_args(["dashboard", "refresh", "--runtime-mode", runtime_mode])

    assert args.runtime_mode == runtime_mode


@pytest.mark.parametrize("scope", ["repo", "session"])
def test_start_and_bootstrap_working_tree_scope_choice_matrix(scope: str) -> None:
    start_args = cli.build_parser().parse_args(["start", "--working-tree-scope", scope])
    bootstrap_args = cli.build_parser().parse_args(["bootstrap", "--working-tree-scope", scope])

    assert start_args.working_tree_scope == scope
    assert bootstrap_args.working_tree_scope == scope


def test_command_surface_helpers_accept_repo_root_equals_and_double_dash(tmp_path: Path) -> None:
    assert command_surface.has_repo_root_arg(argv=[f"--repo-root={tmp_path}", "--flag"]) is True
    assert command_surface.has_repo_root_arg(argv=["--", "--repo-root", str(tmp_path)]) is False
    assert command_surface.ensure_repo_root_args(
        repo_root=tmp_path,
        argv=[f"--repo-root={tmp_path}", "--flag"],
    ) == [f"--repo-root={tmp_path}", "--flag"]
    assert command_surface.ensure_nested_subcommand_repo_root_args(
        repo_root=tmp_path,
        argv=["show-tuning", "--", "--repo-root", "literal"],
    ) == ["show-tuning", "--repo-root", str(tmp_path), "--", "--repo-root", "literal"]


@pytest.mark.parametrize(
    ("argv", "helper"),
    [
        (["--repo-root="], "has_repo_root_arg"),
        (["--repo-root"], "has_repo_root_arg"),
        (["--repo-root="], "ensure_repo_root_args"),
        (["show-tuning", "--repo-root="], "ensure_nested_subcommand_repo_root_args"),
    ],
)
def test_command_surface_rejects_blank_forwarded_repo_root(
    tmp_path: Path,
    argv: list[str],
    helper: str,
) -> None:
    with pytest.raises(SystemExit, match="--repo-root requires a value"):
        if helper == "has_repo_root_arg":
            command_surface.has_repo_root_arg(argv=argv)
        elif helper == "ensure_repo_root_args":
            command_surface.ensure_repo_root_args(repo_root=tmp_path, argv=argv)
        else:
            command_surface.ensure_nested_subcommand_repo_root_args(repo_root=tmp_path, argv=argv)
