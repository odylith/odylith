from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from odylith.runtime.evaluation import odylith_benchmark_tree_identity as tree_identity_runtime


def test_snapshot_overlay_paths_exclude_mutable_runtime_state() -> None:
    scenario_reports = [
        {
            "results": [
                {
                    "live_execution": {
                        "effective_snapshot_paths": [
                            "README.md",
                            ".odylith/runtime/odylith-benchmarks/latest.v1.json",
                            "./.odylith/runtime/odylith-compiler/projection-snapshot.v1.json",
                            "docs/benchmarks/README.md",
                        ]
                    }
                }
            ]
        }
    ]

    assert tree_identity_runtime.report_snapshot_overlay_paths(scenario_reports) == [
        "README.md",
        "docs/benchmarks/README.md",
    ]


def test_tree_identity_stays_current_when_ignored_runtime_reports_change(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bench@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Benchmark"], cwd=repo_root, check=True)
    (repo_root / ".gitignore").write_text(".odylith/\n", encoding="utf-8")
    (repo_root / "README.md").write_text("repo\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "README.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo_root, text=True, capture_output=True, check=True)

    report_path = repo_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"report_id": "old"}), encoding="utf-8")
    snapshot_paths = tree_identity_runtime.report_snapshot_overlay_paths(
        [
            {
                "results": [
                    {
                        "live_execution": {
                            "effective_snapshot_paths": [
                                "README.md",
                                ".odylith/runtime/odylith-benchmarks/latest.v1.json",
                            ]
                        }
                    }
                ]
            }
        ]
    )
    report = tree_identity_runtime.benchmark_tree_identity(
        repo_root=repo_root,
        selection={},
        snapshot_paths=snapshot_paths,
    )
    report["snapshot_overlay_paths"] = snapshot_paths

    report_path.write_text(json.dumps({"report_id": "new"}), encoding="utf-8")

    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=repo_root, report=report)


@pytest.fixture
def overlay_repo(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".gitignore").write_text(".odylith/\noverlay/\n", encoding="utf-8")
    for args in (
        ["init"], ["config", "user.email", "bench@example.com"], ["config", "user.name", "Benchmark"],
        ["add", ".gitignore"], ["commit", "-m", "base"],
    ):
        subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)
    (root / "overlay/__pycache__").mkdir(parents=True)
    (root / "overlay/source.py").write_bytes(b"one\n")
    (root / "overlay/__pycache__/source.pyc").write_bytes(b"old\n")
    monkeypatch.setattr(tree_identity_runtime, "_benchmark_source_posture", lambda **kwargs: "source-local")
    return root


def _serialized_report(root: Path, paths: list[str], *, legacy: bool = False) -> dict:
    selection = {"full_corpus_selected": True}
    kwargs = {"overlay_fingerprint_version": "legacy-metadata"} if legacy else {}
    report = tree_identity_runtime.benchmark_tree_identity(repo_root=root, selection=selection, snapshot_paths=paths, **kwargs)
    report.update(selection=selection, snapshot_overlay_paths=paths)
    return json.loads(json.dumps(report))


def test_content_report_accepts_same_bytes_after_mtime_changes(overlay_repo: Path) -> None:
    report = _serialized_report(overlay_repo, ["overlay"])
    cache_before = tree_identity_runtime.odylith_context_cache.fingerprint_paths([overlay_repo / "overlay"])
    for path in (overlay_repo / "overlay", *(overlay_repo / "overlay").rglob("*")):
        metadata = path.stat()
        os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 2_000_000_000))

    assert report["snapshot_overlay_fingerprint"].startswith("content-v1:")
    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)
    assert tree_identity_runtime.odylith_context_cache.fingerprint_paths([overlay_repo / "overlay"]) != cache_before


@pytest.mark.parametrize("change", ["content", "mode", "deletion"])
def test_content_report_rejects_file_changes(overlay_repo: Path, change: str) -> None:
    source = overlay_repo / "overlay/source.py"
    report = _serialized_report(overlay_repo, ["overlay/source.py"])
    if change == "content":
        metadata = source.stat()
        source.write_bytes(b"two\n")
        os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    elif change == "mode":
        source.chmod(source.stat().st_mode ^ 0o100)
    else:
        source.unlink()

    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)
    current = tree_identity_runtime.benchmark_tree_identity(repo_root=overlay_repo, selection=report["selection"], snapshot_paths=report["snapshot_overlay_paths"])
    assert current["repo_dirty_paths"] == report["repo_dirty_paths"] == []
    assert current["snapshot_overlay_fingerprint"] != report["snapshot_overlay_fingerprint"]


@pytest.mark.parametrize("change", ["addition", "content", "mode", "deletion", "empty_directory"])
def test_directory_content_report_includes_ignored_descendant_inventory(overlay_repo: Path, change: str) -> None:
    source = overlay_repo / "overlay/__pycache__/source.pyc"
    report = _serialized_report(overlay_repo, ["overlay"])
    if change == "addition":
        source.with_name("added.pyc").write_bytes(b"new\n")
    elif change == "content":
        metadata = source.stat()
        source.write_bytes(b"new\n")
        os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    elif change == "mode":
        source.chmod(source.stat().st_mode ^ 0o100)
    elif change == "empty_directory":
        source.with_name("empty").mkdir()
    else:
        source.unlink()

    assert tree_identity_runtime.dirty_repo_paths(overlay_repo) == []
    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


def test_content_report_distinguishes_absent_input_from_empty_overlay_and_empty_file(overlay_repo: Path) -> None:
    empty_overlay = _serialized_report(overlay_repo, [])
    absent_input = _serialized_report(overlay_repo, ["overlay/missing.py"])
    assert empty_overlay["snapshot_overlay_fingerprint"].startswith("content-v1:")
    assert empty_overlay["snapshot_overlay_fingerprint"] != absent_input["snapshot_overlay_fingerprint"]
    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=empty_overlay)
    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=absent_input)

    (overlay_repo / "overlay/missing.py").write_bytes(b"")

    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=empty_overlay)
    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=absent_input)


def test_content_fingerprint_uses_canonical_relative_paths_and_deterministic_order(overlay_repo: Path, tmp_path: Path) -> None:
    first = _serialized_report(overlay_repo, ["overlay/source.py", "overlay/__pycache__/source.pyc"])
    equivalent = _serialized_report(overlay_repo, ["./overlay/__pycache__/source.pyc", "overlay/source.py", "overlay/source.py"])
    assert first["snapshot_overlay_fingerprint"] == equivalent["snapshot_overlay_fingerprint"]
    other = tmp_path / "other"
    for token in ("overlay/source.py", "overlay/__pycache__/source.pyc"):
        source, target = overlay_repo / token, other / token
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        target.chmod(source.stat().st_mode)
    relocated = tree_identity_runtime.benchmark_tree_identity(repo_root=other, selection=first["selection"], snapshot_paths=first["snapshot_overlay_paths"])
    assert relocated["snapshot_overlay_fingerprint"] == first["snapshot_overlay_fingerprint"]


@pytest.mark.parametrize("fingerprint", ["content-v2:" + "0" * 64, "content-v1:", "content-v1:" + "z" * 64, "unknown"])
def test_unknown_or_malformed_content_version_is_refused(overlay_repo: Path, fingerprint: str) -> None:
    report = _serialized_report(overlay_repo, ["overlay"])
    report["snapshot_overlay_fingerprint"] = fingerprint

    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


@pytest.mark.parametrize("field", ["snapshot_overlay_paths", "snapshot_overlay_fingerprint"])
def test_content_identity_does_not_normalize_missing_report_inputs_to_empty(overlay_repo: Path, field: str) -> None:
    report = _serialized_report(overlay_repo, [])
    del report[field]

    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


@pytest.mark.parametrize("token", ["../outside", "/outside", "overlay/../../outside", "C:\\outside", "", ".", None])
def test_unsafe_overlay_paths_fail_closed(overlay_repo: Path, token) -> None:
    report = _serialized_report(overlay_repo, ["overlay"])
    report["snapshot_overlay_paths"] = [token]

    with pytest.raises(ValueError):
        tree_identity_runtime.benchmark_tree_identity(repo_root=overlay_repo, selection={}, snapshot_paths=[token])
    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_directory_symlink_escapes_fail_closed(overlay_repo: Path, tmp_path: Path, kind: str) -> None:
    report = _serialized_report(overlay_repo, ["overlay"])
    outside = tmp_path / "outside"
    if kind == "directory":
        outside.mkdir()
        (outside / "source.py").write_bytes(b"outside\n")
    else:
        outside.write_bytes(b"outside\n")
    (overlay_repo / "overlay/link").symlink_to(outside, target_is_directory=kind == "directory")

    with pytest.raises(ValueError, match="escapes"):
        tree_identity_runtime.benchmark_tree_identity(repo_root=overlay_repo, selection={}, snapshot_paths=["overlay"])
    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


def test_internal_file_symlinks_follow_consumed_bytes_and_directory_cycles_refuse(overlay_repo: Path) -> None:
    (overlay_repo / "overlay/link.py").symlink_to("source.py")
    report = _serialized_report(overlay_repo, ["overlay"])
    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)
    (overlay_repo / "overlay/cycle").symlink_to(".", target_is_directory=True)

    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_unreadable_overlay_sources_fail_closed(overlay_repo: Path, monkeypatch, kind: str) -> None:
    report = _serialized_report(overlay_repo, ["overlay"])
    method = "open" if kind == "file" else "iterdir"
    original = getattr(Path, method)
    unreadable = overlay_repo / ("overlay/source.py" if kind == "file" else "overlay")

    def refuse(path, *args, **kwargs):
        if path == unreadable:
            raise PermissionError("unreadable benchmark source")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, method, refuse)
    with pytest.raises(PermissionError):
        tree_identity_runtime.benchmark_tree_identity(repo_root=overlay_repo, selection={}, snapshot_paths=["overlay"])
    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


@pytest.mark.parametrize("paths", [[], ["overlay/source.py"], ["overlay"]])
def test_legacy_report_keeps_exact_metadata_matching_without_content_reconciliation(overlay_repo: Path, paths: list[str]) -> None:
    report = _serialized_report(overlay_repo, paths, legacy=True)
    expected = tree_identity_runtime.odylith_context_cache.fingerprint_paths([(overlay_repo / token).resolve() for token in paths]) if paths else ""
    assert report["snapshot_overlay_fingerprint"] == expected
    assert not report["snapshot_overlay_fingerprint"].startswith("content-v1:")
    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)
    if paths:
        source = overlay_repo / paths[0]
        metadata = source.stat()
        os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 2_000_000_000))
        assert tree_identity_runtime.dirty_repo_paths(overlay_repo) == []
        assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)


@pytest.mark.parametrize("field", ["git_branch", "git_commit", "git_dirty", "repo_dirty_paths", "selection_fingerprint", "corpus_fingerprint", "source_posture"])
def test_content_reports_preserve_all_other_identity_checks(overlay_repo: Path, field: str) -> None:
    report = _serialized_report(overlay_repo, ["overlay"])
    report[field] = True if field == "git_dirty" else (["other"] if field == "repo_dirty_paths" else "other")

    assert not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=overlay_repo, report=report)
