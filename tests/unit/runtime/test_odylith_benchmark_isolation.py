from __future__ import annotations

import errno
import os
from pathlib import Path
import shutil

import pytest
from odylith.runtime.evaluation import odylith_benchmark_isolation as isolation


def _write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scenario_workspace_self_reference_strip_paths_hide_benchmark_scaffold_but_preserve_explicit_paths(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-proof.v1.json", "{}\n")
    _write(repo_root / "docs" / "benchmarks" / "README.md")
    _write(repo_root / "docs" / "benchmarks" / "REVIEWER_GUIDE.md")
    _write(repo_root / "odylith" / "maintainer" / "agents-guidelines" / "RELEASE_BENCHMARKS.md")
    _write(
        repo_root / "odylith" / "maintainer" / "skills" / "release-benchmark-publishing" / "SKILL.md",
    )
    _write(repo_root / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json", "{}\n")
    _write(repo_root / "odylith" / "runtime" / "source" / "guidance-behavior-evaluation-corpus.v1.json", "{}\n")
    _write(repo_root / "odylith" / "runtime" / "source" / "discipline-evaluation-corpus.v1.json", "{}\n")
    _write(
        repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json",
        "{}\n",
    )
    _write(
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "runtime"
        / "source"
        / "guidance-behavior-evaluation-corpus.v1.json",
        "{}\n",
    )
    _write(
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "runtime"
        / "source"
        / "discipline-evaluation-corpus.v1.json",
        "{}\n",
    )
    _write(repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py")
    _write(repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py")
    _write(repo_root / "src" / "odylith" / "runtime" / "reasoning" / "odylith_reasoning.py")
    _write(repo_root / "src" / "odylith" / "runtime" / "reasoning" / "tribunal_engine.py")
    _write(repo_root / "src" / "odylith" / "runtime" / "reasoning" / "remediator.py")
    _write(repo_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_runner.py")

    rows = isolation.scenario_workspace_self_reference_strip_paths(
        repo_root=repo_root,
        scenario={"family": "browser_surface_reliability"},
        preserve_paths=[
            "docs/benchmarks/README.md",
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        ],
    )

    assert Path("docs/benchmarks/README.md") not in rows
    assert Path("src/odylith/runtime/evaluation/odylith_benchmark_runner.py") not in rows
    assert Path("docs/benchmarks/REVIEWER_GUIDE.md") in rows
    assert Path("src/odylith/runtime/evaluation/odylith_benchmark_graphs.py") in rows
    assert Path("src/odylith/runtime/reasoning/odylith_reasoning.py") in rows
    assert Path("src/odylith/runtime/reasoning/tribunal_engine.py") in rows
    assert Path("src/odylith/runtime/reasoning/remediator.py") in rows
    assert Path("odylith/runtime/source/optimization-evaluation-corpus.v1.json") in rows
    assert Path("odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json") in rows
    assert Path("odylith/runtime/source/discipline-evaluation-corpus.v1.json") in rows
    assert Path("src/odylith/bundle/assets/odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json") in rows
    assert Path("src/odylith/bundle/assets/odylith/runtime/source/discipline-evaluation-corpus.v1.json") in rows
    assert Path("tests/unit/runtime/test_odylith_benchmark_runner.py") in rows
    assert Path(".odylith/runtime/odylith-benchmarks/latest-proof.v1.json") in rows


def test_scenario_workspace_self_reference_strip_paths_skip_benchmark_families(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "docs" / "benchmarks" / "README.md")
    _write(repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py")

    rows = isolation.scenario_workspace_self_reference_strip_paths(
        repo_root=repo_root,
        scenario={"family": "release_publication"},
    )

    assert rows == []


def test_cleanup_temporary_directory_retries_enotempty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "workspace"
    (target / "nested").mkdir(parents=True, exist_ok=True)
    (target / "nested" / "artifact.pyc").write_text("bytecode", encoding="utf-8")
    calls: list[bool] = []
    real_rmtree = shutil.rmtree

    def _flaky_rmtree(path, *args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(bool(kwargs.get("ignore_errors")))
        if len(calls) == 1:
            raise OSError(errno.ENOTEMPTY, "Directory not empty")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(isolation.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(isolation.shutil, "rmtree", _flaky_rmtree)

    isolation.cleanup_temporary_directory(target)

    assert not target.exists()
    assert calls[0] is False
    assert len(calls) >= 2


def test_cleanup_temporary_directory_swallows_persistent_cleanup_noise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "workspace"
    (target / "nested").mkdir(parents=True, exist_ok=True)
    calls: list[bool] = []

    def _always_fail(path, *args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(bool(kwargs.get("ignore_errors")))
        if kwargs.get("ignore_errors"):
            return None
        raise OSError(errno.ENOTEMPTY, "Directory not empty")

    monkeypatch.setattr(isolation.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(isolation.shutil, "rmtree", _always_fail)

    isolation.cleanup_temporary_directory(target)

    assert calls[-1] is True
    shutil.rmtree(target, ignore_errors=True)


def test_capture_workspace_validator_truth_prefers_hardlinks_for_files_on_same_device(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    truth_root = tmp_path / "validator-truth"
    benchmark_report = workspace_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json"
    _write(benchmark_report, "{}\n")
    _write(workspace_root / "AGENTS.md", "root instructions\n")

    isolation.capture_workspace_validator_truth(
        workspace_root=workspace_root,
        truth_root=truth_root,
        strip_paths=[
            Path(".odylith/runtime/odylith-benchmarks/latest.v1.json"),
            Path("AGENTS.md"),
        ],
    )

    copied_report = truth_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json"
    copied_agents = truth_root / "AGENTS.md"

    assert copied_report.read_text(encoding="utf-8") == "{}\n"
    assert copied_agents.read_text(encoding="utf-8") == "root instructions\n"
    assert copied_report.samefile(benchmark_report)
    assert copied_agents.samefile(workspace_root / "AGENTS.md")


def test_overlay_workspace_repo_snapshot_copies_allowed_ignored_runtime_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = tmp_path / "workspace"
    runtime_snapshot = repo_root / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    _write(runtime_snapshot, '{"ready": true}\n')

    def _git_no_paths(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": "", "args": command})()

    monkeypatch.setattr(isolation.subprocess, "run", _git_no_paths)

    isolation.overlay_workspace_repo_snapshot(
        repo_root=repo_root,
        workspace_root=workspace_root,
        allowed_paths=[".odylith/runtime/odylith-compiler/projection-snapshot.v1.json"],
    )

    copied_snapshot = workspace_root / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    assert copied_snapshot.read_text(encoding="utf-8") == '{"ready": true}\n'


def test_capture_workspace_validator_truth_falls_back_to_copy_when_hardlinks_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    truth_root = tmp_path / "validator-truth"
    benchmark_report = workspace_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json"
    _write(benchmark_report, "{}\n")

    real_link = os.link

    def _raise_cross_device(source, target, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError(errno.EXDEV, "cross-device link")

    monkeypatch.setattr(isolation.os, "link", _raise_cross_device)

    isolation.capture_workspace_validator_truth(
        workspace_root=workspace_root,
        truth_root=truth_root,
        strip_paths=[Path(".odylith/runtime/odylith-benchmarks/latest.v1.json")],
    )

    copied_report = truth_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json"
    assert copied_report.read_text(encoding="utf-8") == "{}\n"
    assert not copied_report.samefile(benchmark_report)

    monkeypatch.setattr(isolation.os, "link", real_link)
