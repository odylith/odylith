"""Logical shell custody across protected live, staged and immutable layouts."""

from __future__ import annotations

import base64
from pathlib import Path
import shutil

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from odylith.runtime.domain_intelligence.greenfield_prewrite_stage_root import staged_greenfield_prewrite_root


def _shell(root: Path, text: bytes = b"<html>Complete shell</html>\n") -> None:
    (root / "odylith/radar/source").mkdir(parents=True)
    (root / "odylith/index.html").write_bytes(text)
    (root / "odylith/tooling-payload.v1.js").write_bytes(b"window.payload = {};\n")
    (root / "odylith/radar/source/record.md").write_bytes(b"# Governed record\n")


def _protect(root: Path) -> bytes:
    shutil.copy2(root / "odylith/index.html", root / "odylith/tooling-shell.html")
    entry = state.compile_greenfield_publication_entry(
        write_set_hash="a" * 64, generation_manifest_sha256="b" * 64,
    ).encode("utf-8")
    (root / "odylith/index.html").write_bytes(entry)
    return entry


@pytest.mark.parametrize("protected", (False, True))
def test_layout_maps_only_the_logical_shell(tmp_path: Path, protected: bool) -> None:
    layout = kernel.GreenfieldRepositoryLayout(repo_root=tmp_path, publication_protected=protected)
    for logical in kernel.GREENFIELD_REPOSITORY_WRITE_PATHS:
        physical = "odylith/tooling-shell.html" if protected and logical == "odylith/index.html" else logical
        assert layout.target_path(logical) == tmp_path / physical
    assert layout.target_path("odylith/radar/source/record.md") == tmp_path / "odylith/radar/source/record.md"


@pytest.mark.parametrize("logical", ("../outside", "/tmp/outside", "odylith/index.html/../../outside", "other.txt"))
def test_layout_rejects_unmanaged_paths(tmp_path: Path, logical: str) -> None:
    layout = kernel.GreenfieldRepositoryLayout(repo_root=tmp_path, publication_protected=True)
    with pytest.raises(ValueError, match="escapes the managed boundary"):
        layout.target_path(logical)


def test_live_staged_and_immutable_shell_bytes_have_one_logical_identity(tmp_path: Path) -> None:
    live, stage, immutable = (tmp_path / name for name in ("live", "stage", "immutable"))
    _shell(live)
    _shell(stage, b"<html>Revised complete shell</html>\n")
    entry = _protect(live)

    write_set = kernel.compile_greenfield_repository_write_set(source_root=live, staged_root=stage)
    after = {row["path"]: base64.b64decode(row["content_base64"]) for row in write_set["after_image"]["files"]}
    assert after["odylith/index.html"] == (stage / "odylith/index.html").read_bytes()
    assert "odylith/tooling-shell.html" not in after
    assert entry not in after.values()
    kernel.apply_compiled_greenfield_repository_write_set(repo_root=live, write_set=write_set)
    kernel.materialize_compiled_greenfield_after_image(destination_root=immutable, write_set=write_set)

    assert (live / "odylith/index.html").read_bytes() == entry
    assert (live / "odylith/tooling-shell.html").read_bytes() == after["odylith/index.html"]
    assert (immutable / "odylith/index.html").read_bytes() == after["odylith/index.html"]
    assert not (immutable / "odylith/tooling-shell.html").exists()
    assert kernel.greenfield_managed_fingerprints(live) == kernel.greenfield_managed_fingerprints(stage)
    assert kernel.greenfield_managed_fingerprints(live) == kernel.greenfield_managed_fingerprints(immutable)
    assert kernel.require_greenfield_repository_after_state(repo_root=live, write_set=write_set)


def test_prewrite_copy_uses_working_bytes_and_never_copies_publication(tmp_path: Path) -> None:
    live = tmp_path / "repository"
    _shell(live)
    entry = _protect(live)
    expected = (live / "odylith/tooling-shell.html").read_bytes()

    with staged_greenfield_prewrite_root(live) as stage:
        assert (stage / "odylith/index.html").read_bytes() == expected
        assert not (stage / "odylith/tooling-shell.html").exists()
        assert (stage / "odylith/radar/source/record.md").read_bytes() == b"# Governed record\n"
        assert not kernel.greenfield_repository_layout(stage).publication_protected
    assert (live / "odylith/index.html").read_bytes() == entry


def test_shell_delete_targets_working_bytes_not_publication(tmp_path: Path) -> None:
    live, stage = tmp_path / "live", tmp_path / "stage"
    _shell(live)
    _shell(stage)
    (stage / "odylith/index.html").unlink()
    entry = _protect(live)
    write_set = kernel.compile_greenfield_repository_write_set(source_root=live, staged_root=stage)

    assert "odylith/index.html" in {row["path"] for row in write_set["deletes"]}
    kernel.apply_compiled_greenfield_repository_write_set(repo_root=live, write_set=write_set)
    assert (live / "odylith/index.html").read_bytes() == entry
    assert not (live / "odylith/tooling-shell.html").exists()
    assert kernel.greenfield_managed_fingerprints(live) == kernel.greenfield_managed_fingerprints(stage)


def test_recovery_owner_mapping_preserves_logical_delta_keys(tmp_path: Path) -> None:
    live, stage = tmp_path / "live", tmp_path / "stage"
    _shell(live)
    _shell(stage, b"<html>After</html>\n")
    entry = _protect(live)
    write_set = kernel.compile_greenfield_repository_write_set(source_root=live, staged_root=stage)
    layout = kernel.greenfield_repository_layout(live)

    logical_owners = kernel.greenfield_repository_recovery_paths(write_set)
    physical_owners = tuple(layout.target_path(path).relative_to(live).as_posix() for path in logical_owners)
    assert logical_owners == ("odylith/index.html",)
    assert physical_owners == ("odylith/tooling-shell.html",)
    physical_writes = {
        layout.target_path(row["path"]).relative_to(live).as_posix(): row["sha256"]
        for row in write_set["writes"]
    }
    assert set(physical_writes) == set(physical_owners)
    assert kernel.require_greenfield_repository_recovery_preconditions(repo_root=live, write_set=write_set)
    assert (live / "odylith/index.html").read_bytes() == entry


def test_protected_working_shell_symlink_is_not_captured(tmp_path: Path) -> None:
    live, stage = tmp_path / "live", tmp_path / "stage"
    _shell(live)
    _shell(stage)
    entry = _protect(live)
    working = live / "odylith/tooling-shell.html"
    working.unlink()
    working.symlink_to(stage / "odylith/index.html")
    with pytest.raises(ValueError, match="managed symlink"):
        kernel.compile_greenfield_repository_write_set(source_root=live, staged_root=stage)
    assert (live / "odylith/index.html").read_bytes() == entry


def test_invalid_identified_publication_cannot_fall_back_to_the_full_shell(tmp_path: Path) -> None:
    _shell(tmp_path)
    _protect(tmp_path)
    path = tmp_path / "odylith/index.html"
    path.write_bytes(path.read_bytes().replace(b'"write_set_hash":"a', b'"write_set_hash":"z', 1))
    with pytest.raises((RuntimeError, ValueError)):
        kernel.greenfield_repository_layout(tmp_path)


def test_explicit_layout_cannot_be_reused_for_another_repository(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    _shell(first)
    _shell(second)
    write_set = kernel.compile_greenfield_repository_write_set(source_root=first, staged_root=second)
    layout = kernel.GreenfieldRepositoryLayout(repo_root=second, publication_protected=False)
    with pytest.raises(ValueError, match="different root"):
        kernel.require_greenfield_repository_after_state(repo_root=first, write_set=write_set, layout=layout)
