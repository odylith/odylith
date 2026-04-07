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

    audit = migration_audit.audit_legacy_odyssey_references(repo_root=repo_root)
    report_text = audit.report_path.read_text(encoding="utf-8")

    assert audit.file_count == 1
    assert audit.hit_count == 1
    assert audit.sample_paths == ("AGENTS.md",)
    assert "## AGENTS.md" in report_text
    assert "runtime tree" not in report_text
    assert "inside cache" not in report_text
    assert "previous report" not in report_text
