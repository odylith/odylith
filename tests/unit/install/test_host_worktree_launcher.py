from __future__ import annotations

import importlib.util
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
