from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from odylith.install import fs as install_fs
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction


def _stage_from_source(source: Path, stage: Path) -> None:
    stage.mkdir(parents=True, exist_ok=True)
    if (source / "odylith").is_dir():
        shutil.copytree(source / "odylith", stage / "odylith")
    bundle = source / "src/odylith/bundle/assets/odylith"
    if bundle.is_dir():
        shutil.copytree(bundle, stage / "src/odylith/bundle/assets/odylith")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_repository_write_set_applies_exact_staged_tree(tmp_path: Path) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    _write(source / "odylith/radar/source/keep.md", "before\n")
    _write(source / "odylith/radar/source/delete.md", "remove\n")
    _write(source / "src/odylith/bundle/assets/odylith/radar/radar-app.v1.js", "old\n")
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/keep.md", "after\n")
    (stage / "odylith/radar/source/delete.md").unlink()
    _write(stage / "odylith/radar/source/new/created.md", "created\n")
    _write(stage / "src/odylith/bundle/assets/odylith/radar/radar-app.v1.js", "new\n")

    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )

    assert write_set["write_count"] == 3
    assert write_set["delete_count"] == 1
    result = greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=source,
        write_set=write_set,
    )
    assert result["status"] == "passed"
    assert (source / "odylith/radar/source/keep.md").read_text(encoding="utf-8") == "after\n"
    assert not (source / "odylith/radar/source/delete.md").exists()
    assert (source / "odylith/radar/source/new/created.md").read_text(encoding="utf-8") == "created\n"
    assert (
        source / "src/odylith/bundle/assets/odylith/radar/radar-app.v1.js"
    ).read_text(encoding="utf-8") == "new\n"


def test_repository_after_image_matches_prefix_related_component_directories(tmp_path: Path) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    source.mkdir()
    _write(stage / "odylith/registry/source/components/community-sports-organizers/CURRENT_SPEC.md", "one\n")
    _write(
        stage
        / "odylith/registry/source/components/community-sports-organizers-workspace-fixtures-publication/CURRENT_SPEC.md",
        "two\n",
    )

    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )

    assert greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(write_set) == write_set


def test_repository_write_set_reports_changed_after_image_root(tmp_path: Path) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    _write(source / "odylith/radar/source/keep.md", "before\n")
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/keep.md", "after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )
    write_set["after_fingerprints"]["odylith/radar"] = "0" * 64

    with pytest.raises(ValueError, match=r"after-image fingerprint mismatch for odylith/radar"):
        greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(write_set)


def test_repository_write_set_removes_sealed_empty_directories(tmp_path: Path) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    removed = source / "odylith/radar/source/ideas/gone/nested"
    removed.mkdir(parents=True)
    _stage_from_source(source, stage)
    (stage / "odylith/radar/source/ideas/gone/nested").rmdir()
    (stage / "odylith/radar/source/ideas/gone").rmdir()

    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )

    assert [row["path"] for row in write_set["directory_deletes"]] == [
        "odylith/radar/source/ideas/gone/nested",
        "odylith/radar/source/ideas/gone",
    ]
    result = greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=source,
        write_set=write_set,
    )

    assert result["directory_delete_count"] == 2
    assert not (source / "odylith/radar/source/ideas/gone").exists()


def test_repository_write_set_syncs_directory_only_creation_through_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    source.mkdir()
    created = source / "odylith/radar/source/empty"
    (stage / "odylith/radar/source/empty").mkdir(parents=True)
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )
    calls: list[Path] = []
    real_sync = greenfield_repository_write_set.fsync_directory

    def record_sync(path: Path) -> None:
        calls.append(Path(path))
        real_sync(path)

    monkeypatch.setattr(greenfield_repository_write_set, "fsync_directory", record_sync)

    result = greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=source,
        write_set=write_set,
    )

    assert result["write_count"] == 0
    assert result["directory_count"] == 3
    assert created.is_dir()
    assert created in calls
    assert source in calls


def test_repository_write_set_rejects_repo_drift_before_first_write(tmp_path: Path) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    target = source / "odylith/radar/source/INDEX.md"
    _write(target, "before\n")
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/INDEX.md", "compiled\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )
    target.write_text("operator edit\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repo preconditions changed"):
        greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
            repo_root=source,
            write_set=write_set,
        )

    assert target.read_text(encoding="utf-8") == "operator edit\n"


def test_repository_write_set_refuses_managed_symlinks(tmp_path: Path) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside.md"
    _write(outside, "outside\n")
    link = source / "odylith/radar/source/link.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    stage.mkdir()

    with pytest.raises(ValueError, match="refuses managed symlink"):
        greenfield_repository_write_set.compile_greenfield_repository_write_set(
            source_root=source,
            staged_root=stage,
        )


@pytest.mark.parametrize(
    "failure",
    [OSError("disk full"), ValueError("symlink race"), KeyboardInterrupt()],
)
def test_repository_write_set_rolls_back_mid_write_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    first = source / "odylith/radar/source/first.md"
    second = source / "odylith/radar/source/second.md"
    _write(first, "first before\n")
    _write(second, "second before\n")
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/first.md", "first after\n")
    _write(stage / "odylith/radar/source/second.md", "second after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )
    real_write = greenfield_repository_write_set.atomic_write_bytes
    calls = 0

    def fail_second(
        path: Path,
        data: bytes,
        *,
        mode: int | None = None,
        temporary_directory: Path | None = None,
    ) -> Path:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise failure
        return real_write(path, data, mode=mode, temporary_directory=temporary_directory)

    monkeypatch.setattr(greenfield_repository_write_set, "atomic_write_bytes", fail_second)
    paths = greenfield_repository_write_set.greenfield_repository_write_paths(write_set)
    transaction = GreenfieldApplyTransaction(source, paths=paths)
    with pytest.raises(type(failure)):
        with transaction:
            greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
                repo_root=source,
                write_set=write_set,
            )

    assert transaction.rollback_status == "rolled_back"
    assert first.read_text(encoding="utf-8") == "first before\n"
    assert second.read_text(encoding="utf-8") == "second before\n"


def test_repository_write_set_rolls_back_after_file_delete_when_directory_delete_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    kept = source / "odylith/radar/source/keep.md"
    deleted = source / "odylith/radar/source/delete.md"
    removed_directory = source / "odylith/radar/source/obsolete/empty"
    _write(kept, "keep before\n")
    _write(deleted, "delete before\n")
    removed_directory.mkdir(parents=True)
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/keep.md", "keep after\n")
    (stage / "odylith/radar/source/delete.md").unlink()
    (stage / "odylith/radar/source/obsolete/empty").rmdir()
    (stage / "odylith/radar/source/obsolete").rmdir()
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )
    real_rmdir = greenfield_repository_write_set.Path.rmdir

    def fail_removed_directory(path: Path) -> None:
        if path == removed_directory:
            raise OSError("directory delete failed")
        real_rmdir(path)

    monkeypatch.setattr(greenfield_repository_write_set.Path, "rmdir", fail_removed_directory)
    paths = greenfield_repository_write_set.greenfield_repository_write_paths(write_set)
    transaction = GreenfieldApplyTransaction(source, paths=paths)

    with pytest.raises(OSError, match="directory delete failed"):
        with transaction:
            greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
                repo_root=source,
                write_set=write_set,
            )

    assert transaction.rollback_status == "rolled_back"
    greenfield_repository_write_set.require_greenfield_repository_recovery_preconditions(
        repo_root=source,
        write_set=write_set,
    )
    assert kept.read_text(encoding="utf-8") == "keep before\n"
    assert deleted.read_text(encoding="utf-8") == "delete before\n"
    assert removed_directory.is_dir()


def test_atomic_write_removes_temp_sibling_when_interrupted_after_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "INDEX.md"
    target.write_bytes(b"before\n")

    def interrupt_fsync(_fd: int) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(install_fs.os, "fsync", interrupt_fsync)

    with pytest.raises(KeyboardInterrupt):
        install_fs.atomic_write_bytes(target, b"after\n")

    assert target.read_bytes() == b"before\n"
    assert list(tmp_path.glob(".INDEX.md.*.tmp")) == []


def test_atomic_write_with_journal_staging_syncs_both_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "governed" / "INDEX.md"
    staging = tmp_path / "journal" / "staging"
    calls: list[Path] = []
    real_sync = install_fs.fsync_directory

    def record_sync(path: Path) -> None:
        calls.append(Path(path))
        real_sync(path)

    monkeypatch.setattr(install_fs, "fsync_directory", record_sync)
    install_fs.atomic_write_bytes(target, b"after\n", temporary_directory=staging)

    assert target.read_bytes() == b"after\n"
    assert target.parent in calls
    assert staging in calls


def test_repository_write_set_readback_failure_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    target = source / "odylith/radar/source/INDEX.md"
    _write(target, "before\n")
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/INDEX.md", "after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )
    real_write = greenfield_repository_write_set.atomic_write_bytes

    def corrupt(
        path: Path,
        data: bytes,
        *,
        mode: int | None = None,
        temporary_directory: Path | None = None,
    ) -> Path:
        return real_write(path, data + b"corrupt", mode=mode, temporary_directory=temporary_directory)

    monkeypatch.setattr(greenfield_repository_write_set, "atomic_write_bytes", corrupt)
    paths = greenfield_repository_write_set.greenfield_repository_write_paths(write_set)
    transaction = GreenfieldApplyTransaction(source, paths=paths)
    with pytest.raises(RuntimeError, match="readback drifted"):
        with transaction:
            greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
                repo_root=source,
                write_set=write_set,
            )

    assert transaction.rollback_status == "rolled_back"
    assert target.read_text(encoding="utf-8") == "before\n"


def test_repository_write_set_rolls_back_when_target_directory_sync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    target = source / "odylith/radar/source/INDEX.md"
    _write(target, "before\n")
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/INDEX.md", "after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )
    real_sync = greenfield_repository_write_set.fsync_directory
    calls = 0

    def fail_once(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("directory sync failed")
        real_sync(path)

    monkeypatch.setattr(greenfield_repository_write_set, "fsync_directory", fail_once)
    paths = greenfield_repository_write_set.greenfield_repository_write_paths(write_set)
    transaction = GreenfieldApplyTransaction(source, paths=paths)

    with pytest.raises(OSError, match="directory sync failed"):
        with transaction:
            greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
                repo_root=source,
                write_set=write_set,
            )

    assert transaction.rollback_status == "rolled_back"
    assert target.read_text(encoding="utf-8") == "before\n"


def test_repository_write_set_rolls_back_when_target_file_sync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    target = source / "odylith/radar/source/INDEX.md"
    _write(target, "before\n")
    _stage_from_source(source, stage)
    _write(stage / "odylith/radar/source/INDEX.md", "after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )

    def fail_sync(_path: Path) -> None:
        raise OSError("file sync failed")

    monkeypatch.setattr(greenfield_repository_write_set, "fsync_file", fail_sync)
    paths = greenfield_repository_write_set.greenfield_repository_write_paths(write_set)
    transaction = GreenfieldApplyTransaction(source, paths=paths)

    with pytest.raises(OSError, match="file sync failed"):
        with transaction:
            greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
                repo_root=source,
                write_set=write_set,
            )

    assert transaction.rollback_status == "rolled_back"
    assert target.read_text(encoding="utf-8") == "before\n"
