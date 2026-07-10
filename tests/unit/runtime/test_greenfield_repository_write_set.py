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

    def fail_second(path: Path, data: bytes) -> Path:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise failure
        return real_write(path, data)

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

    def corrupt(path: Path, data: bytes) -> Path:
        return real_write(path, data + b"corrupt")

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
