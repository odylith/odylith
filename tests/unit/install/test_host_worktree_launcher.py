from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER_PATH = REPO_ROOT / ".agents" / "bin" / "odylith-host-launcher.py"


def _load_helper():
    spec = importlib.util.spec_from_file_location("odylith_host_launcher", HELPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_helper_prefers_local_bootstrap_when_main_launcher_exists(tmp_path: Path) -> None:
    module = _load_helper()
    repo_root = tmp_path / "repo"
    main_launcher = repo_root / ".odylith" / "bin" / "odylith"
    bootstrap = repo_root / ".odylith" / "bin" / "odylith-bootstrap"
    main_launcher.parent.mkdir(parents=True, exist_ok=True)
    main_launcher.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    bootstrap.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_exec(launcher: Path, argv, cwd: Path) -> int:
        captured["launcher"] = launcher
        captured["argv"] = list(argv)
        captured["cwd"] = cwd
        return 0

    exit_code = module.run(
        ["claude", "prompt-context", "--repo-root", "."],
        cwd=repo_root,
        exec_runner=_fake_exec,
    )

    assert exit_code == 0
    assert captured["launcher"] == bootstrap
    assert captured["argv"] == ["claude", "prompt-context", "--repo-root", "."]
    assert captured["cwd"] == repo_root


def test_helper_uses_main_launcher_when_bootstrap_is_missing(tmp_path: Path) -> None:
    module = _load_helper()
    repo_root = tmp_path / "repo"
    main_launcher = repo_root / ".odylith" / "bin" / "odylith"
    main_launcher.parent.mkdir(parents=True, exist_ok=True)
    main_launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_exec(launcher: Path, argv, cwd: Path) -> int:
        captured["launcher"] = launcher
        captured["argv"] = list(argv)
        captured["cwd"] = cwd
        return 0

    exit_code = module.run(
        ["codex", "prompt-context", "--repo-root", "."],
        cwd=repo_root,
        exec_runner=_fake_exec,
    )

    assert exit_code == 0
    assert captured["launcher"] == main_launcher
    assert captured["argv"] == ["codex", "prompt-context", "--repo-root", "."]
    assert captured["cwd"] == repo_root


def test_helper_seeds_hot_context_defaults_without_overriding_user_env(monkeypatch, tmp_path: Path) -> None:
    module = _load_helper()
    repo_root = tmp_path / "repo"
    main_launcher = repo_root / ".odylith" / "bin" / "odylith"
    main_launcher.parent.mkdir(parents=True, exist_ok=True)
    main_launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.delenv("ODYLITH_CONTEXT_ENGINE_ALLOW_WORKSPACE_PYTHON", raising=False)
    monkeypatch.delenv("ODYLITH_CONTEXT_ENGINE_ALLOW_BACKGROUND_AUTOSPAWN", raising=False)
    monkeypatch.setenv("ODYLITH_CONTEXT_ENGINE_AUTOSPAWN_IDLE_TIMEOUT_SECONDS", "300")

    def _fake_exec(launcher: Path, argv, cwd: Path) -> int:
        del launcher, argv, cwd
        assert os.environ["ODYLITH_CONTEXT_ENGINE_ALLOW_WORKSPACE_PYTHON"] == "1"
        assert os.environ["ODYLITH_CONTEXT_ENGINE_ALLOW_BACKGROUND_AUTOSPAWN"] == "1"
        assert os.environ["ODYLITH_CONTEXT_ENGINE_AUTOSPAWN_IDLE_TIMEOUT_SECONDS"] == "300"
        return 0

    exit_code = module.run(
        ["codex", "prompt-context", "--repo-root", "."],
        cwd=repo_root,
        exec_runner=_fake_exec,
    )

    assert exit_code == 0


def test_helper_repairs_nested_worktree_from_parent_launcher(monkeypatch, tmp_path: Path) -> None:
    module = _load_helper()
    parent_repo = tmp_path / "repo"
    worktree = parent_repo / ".claude" / "worktrees" / "slice"
    peer_launcher = parent_repo / ".odylith" / "bin" / "odylith"
    peer_launcher.parent.mkdir(parents=True, exist_ok=True)
    peer_launcher.write_text("#!/bin/sh\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_run(args, cwd, capture_output, text, check, timeout):
        del capture_output, text, check, timeout
        if args[:1] == ["git"]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        assert args[:2] == [str(peer_launcher), "doctor"]
        assert cwd == str(worktree)
        local_launcher = worktree / ".odylith" / "bin" / "odylith"
        local_launcher.parent.mkdir(parents=True, exist_ok=True)
        local_launcher.write_text("#!/bin/sh\n", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def _fake_exec(launcher: Path, argv, cwd: Path) -> int:
        captured["launcher"] = launcher
        captured["argv"] = list(argv)
        captured["cwd"] = cwd
        return 0

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.run(
        ["codex", "prompt-context", "--repo-root", "."],
        cwd=worktree,
        exec_runner=_fake_exec,
    )

    assert exit_code == 0
    assert captured["launcher"] == worktree / ".odylith" / "bin" / "odylith"
    assert captured["argv"] == ["codex", "prompt-context", "--repo-root", "."]
    assert captured["cwd"] == worktree


def test_helper_repairs_external_worktree_from_git_listed_peer(monkeypatch, tmp_path: Path) -> None:
    module = _load_helper()
    primary = tmp_path / "primary"
    external = tmp_path / "external"
    peer_launcher = primary / ".odylith" / "bin" / "odylith"
    peer_launcher.parent.mkdir(parents=True, exist_ok=True)
    peer_launcher.write_text("#!/bin/sh\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_run(args, cwd, capture_output, text, check, timeout):
        del capture_output, text, check, timeout
        if args[:3] == ["git", "worktree", "list"]:
            stdout = f"worktree {external}\n\nworktree {primary}\n"
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
        assert args[:2] == [str(peer_launcher), "doctor"]
        assert cwd == str(external)
        local_launcher = external / ".odylith" / "bin" / "odylith"
        local_launcher.parent.mkdir(parents=True, exist_ok=True)
        local_launcher.write_text("#!/bin/sh\n", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def _fake_exec(launcher: Path, argv, cwd: Path) -> int:
        captured["launcher"] = launcher
        captured["argv"] = list(argv)
        captured["cwd"] = cwd
        return 0

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.run(
        ["claude", "prompt-context", "--repo-root", "."],
        cwd=external,
        exec_runner=_fake_exec,
    )

    assert exit_code == 0
    assert captured["launcher"] == external / ".odylith" / "bin" / "odylith"
    assert captured["argv"] == ["claude", "prompt-context", "--repo-root", "."]
    assert captured["cwd"] == external


def test_helper_noops_after_uninstall_when_guidance_is_detached(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _load_helper()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    (repo_root / ".odylith" / "compass").mkdir(parents=True)
    (repo_root / ".odylith" / "compass" / "standup-brief-maintenance-state.v1.json").write_text(
        "{}\n",
        encoding="utf-8",
    )

    def _fake_run(args, cwd, capture_output, text, check, timeout):
        del cwd, capture_output, text, check, timeout
        if args[:3] == ["git", "worktree", "list"]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess call: {args}")

    def _fail_exec(launcher: Path, argv, cwd: Path) -> int:
        raise AssertionError(f"uninstalled repo must not exec {launcher} {argv} {cwd}")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.run(
        ["claude", "stop-summary", "--repo-root", "."],
        cwd=repo_root,
        exec_runner=_fail_exec,
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""


def test_helper_reports_missing_launcher_when_guidance_is_still_active(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _load_helper()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("<!-- odylith-scope:start -->\n<!-- odylith-scope:end -->\n", encoding="utf-8")

    def _fake_run(args, cwd, capture_output, text, check, timeout):
        del cwd, capture_output, text, check, timeout
        if args[:3] == ["git", "worktree", "list"]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.run(
        ["claude", "stop-summary", "--repo-root", "."],
        cwd=repo_root,
        exec_runner=lambda *_: 0,
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "could not find a usable launcher" in captured.err
