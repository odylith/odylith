from __future__ import annotations

import subprocess
from pathlib import Path

from odylith.install import migration_audit


def test_audit_reports_only_tracked_text_files_outside_managed_trees(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    tracked_doc = repo_root / "docs" / "guide.md"
    tracked_doc.parent.mkdir(parents=True, exist_ok=True)
    tracked_doc.write_text("Legacy Odyssey reference.\n", encoding="utf-8")

    tracked_runtime = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3" / "notes.md"
    tracked_runtime.parent.mkdir(parents=True, exist_ok=True)
    tracked_runtime.write_text("Odyssey should be ignored here.\n", encoding="utf-8")

    tracked_cache = repo_root / ".odylith" / "cache" / "cache.md"
    tracked_cache.parent.mkdir(parents=True, exist_ok=True)
    tracked_cache.write_text("Odyssey cache should be ignored.\n", encoding="utf-8")

    tracked_report = repo_root / ".odylith" / "state" / "migration" / "existing.md"
    tracked_report.parent.mkdir(parents=True, exist_ok=True)
    tracked_report.write_text("Odyssey report should be ignored.\n", encoding="utf-8")

    tracked_binary = repo_root / "docs" / "image.png"
    tracked_binary.write_text("Odyssey in unsupported suffix.\n", encoding="utf-8")

    untracked_doc = repo_root / "notes" / "untracked.md"
    untracked_doc.parent.mkdir(parents=True, exist_ok=True)
    untracked_doc.write_text("Odyssey untracked.\n", encoding="utf-8")

    def _fake_run(args, capture_output, check):  # noqa: ANN001
        assert args == ["git", "-C", str(repo_root), "ls-files", "-z"]
        assert capture_output is True
        assert check is False
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                b"docs/guide.md\0"
                b".odylith/runtime/versions/1.2.3/notes.md\0"
                b".odylith/cache/cache.md\0"
                b".odylith/state/migration/existing.md\0"
                b"docs/image.png\0"
            ),
            stderr=b"",
        )

    monkeypatch.setattr(migration_audit.subprocess, "run", _fake_run)

    audit = migration_audit.audit_legacy_odyssey_references(repo_root=repo_root)
    report_text = audit.report_path.read_text(encoding="utf-8")

    assert audit.file_count == 1
    assert audit.hit_count == 1
    assert audit.sample_paths == ("docs/guide.md",)
    assert "## docs/guide.md" in report_text
    assert ".odylith/runtime/versions/1.2.3/notes.md" not in report_text
    assert ".odylith/cache/cache.md" not in report_text
    assert ".odylith/state/migration/existing.md" not in report_text
    assert "notes/untracked.md" not in report_text
    assert "docs/image.png" not in report_text


def test_audit_excludes_generated_surfaces_but_keeps_source_truth(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    candidates = {
        "docs/guide.md": "Legacy odyssey reference in user docs.\n",
        "odylith/radar/source/INDEX.md": "Source truth says odyssey here.\n",
        "odylith/casebook/bugs/bug.md": "Bug source says odyssey here.\n",
        "odylith/registry/source/component_registry.v1.json": '{"note": "odyssey source truth"}\n',
        "odylith/index.html": "Generated shell mentions odyssey.\n",
        "odylith/radar/backlog-payload.v1.js": "Generated Radar mentions odyssey.\n",
        "odylith/radar/backlog-document-shard-001.v1.js": "Generated Radar shard mentions odyssey.\n",
        "odylith/casebook/casebook-detail-shard-001.v1.js": "Generated Casebook shard mentions odyssey.\n",
        "odylith/compass/runtime/current.v1.json": '{"generated": "odyssey"}\n',
    }
    for relative_path, text in candidates.items():
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _fake_run(args, capture_output, check):  # noqa: ANN001
        assert args == ["git", "-C", str(repo_root), "ls-files", "-z"]
        assert capture_output is True
        assert check is False
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=b"\0".join(relative_path.encode("utf-8") for relative_path in candidates) + b"\0",
            stderr=b"",
        )

    monkeypatch.setattr(migration_audit.subprocess, "run", _fake_run)

    audit = migration_audit.audit_legacy_odyssey_references(repo_root=repo_root)
    report_text = audit.report_path.read_text(encoding="utf-8")

    assert audit.file_count == 4
    assert audit.hit_count == 4
    assert audit.sample_paths == (
        "docs/guide.md",
        "odylith/radar/source/INDEX.md",
        "odylith/casebook/bugs/bug.md",
        "odylith/registry/source/component_registry.v1.json",
    )
    assert "## docs/guide.md" in report_text
    assert "## odylith/radar/source/INDEX.md" in report_text
    assert "## odylith/casebook/bugs/bug.md" in report_text
    assert "## odylith/registry/source/component_registry.v1.json" in report_text
    assert "odylith/index.html" not in report_text
    assert "backlog-payload.v1.js" not in report_text
    assert "backlog-document-shard-001.v1.js" not in report_text
    assert "casebook-detail-shard-001.v1.js" not in report_text
    assert "odylith/compass/runtime/current.v1.json" not in report_text


def test_audit_fallback_scan_excludes_managed_trees_without_git_metadata(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    included_doc = repo_root / "AGENTS.md"
    included_doc.write_text("odyssey still appears here.\n", encoding="utf-8")

    ignored_runtime = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3" / "README.md"
    ignored_runtime.parent.mkdir(parents=True, exist_ok=True)
    ignored_runtime.write_text("odyssey inside runtime tree.\n", encoding="utf-8")

    ignored_cache = repo_root / ".odylith" / "cache" / "cache.md"
    ignored_cache.parent.mkdir(parents=True, exist_ok=True)
    ignored_cache.write_text("odyssey inside cache.\n", encoding="utf-8")

    ignored_report = repo_root / ".odylith" / "state" / "migration" / "prior.md"
    ignored_report.parent.mkdir(parents=True, exist_ok=True)
    ignored_report.write_text("odyssey inside previous report.\n", encoding="utf-8")

    ignored_ledger = repo_root / ".odylith" / "state" / "migrations" / "legacy.json"
    ignored_ledger.parent.mkdir(parents=True, exist_ok=True)
    ignored_ledger.write_text('{"note": "odyssey inside migration ledger"}\n', encoding="utf-8")

    ignored_generated_surface = repo_root / "odylith" / "radar" / "backlog-payload.v1.js"
    ignored_generated_surface.parent.mkdir(parents=True, exist_ok=True)
    ignored_generated_surface.write_text("odyssey inside generated surface.\n", encoding="utf-8")

    ignored_tmp_clone = repo_root / "tmp" / "sim3" / "README.md"
    ignored_tmp_clone.parent.mkdir(parents=True, exist_ok=True)
    ignored_tmp_clone.write_text("odyssey inside root tmp clone.\n", encoding="utf-8")

    ignored_vendor = repo_root / "node_modules" / "pkg" / "README.md"
    ignored_vendor.parent.mkdir(parents=True, exist_ok=True)
    ignored_vendor.write_text("odyssey inside vendor tree.\n", encoding="utf-8")

    ignored_dist = repo_root / "dist" / "bundle.js"
    ignored_dist.parent.mkdir(parents=True, exist_ok=True)
    ignored_dist.write_text("odyssey inside dist output.\n", encoding="utf-8")

    audit = migration_audit.audit_legacy_odyssey_references(repo_root=repo_root)
    report_text = audit.report_path.read_text(encoding="utf-8")

    assert audit.file_count == 1
    assert audit.hit_count == 1
    assert audit.sample_paths == ("AGENTS.md",)
    assert "## AGENTS.md" in report_text
    assert "runtime tree" not in report_text
    assert "inside cache" not in report_text
    assert "previous report" not in report_text
    assert "migration ledger" not in report_text
    assert "generated surface" not in report_text
    assert "root tmp clone" not in report_text
    assert "vendor tree" not in report_text
    assert "dist output" not in report_text
