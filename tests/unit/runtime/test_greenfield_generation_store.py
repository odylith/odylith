"""Immutable generation readback and sole-entry publication identity."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_set(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    source = tmp_path / "repo"
    stage = tmp_path / "stage"
    _write(source / "odylith/index.html", "<!doctype html><title>Complete shell</title>\n")
    _write(source / "odylith/radar/source/keep.md", "before\n")
    _write(source / "odylith/radar/source/unchanged.md", "sealed unchanged\n")
    shutil.copytree(source / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/keep.md", "after\n")
    return source, greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )


def _publish(repo: Path, generation, write_set) -> str:
    entry = greenfield_generation_state.compile_greenfield_publication_entry(
        write_set_hash=generation.write_set_hash, generation_manifest_sha256=generation.manifest_sha256,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo, generation=generation, write_set=write_set, publication_entry_text=entry,
    )
    # Establish a preexisting protected layout; activation is tested by its owner.
    if not (repo / "odylith/tooling-shell.html").exists():
        shutil.copy2(generation.repository_root / "odylith/index.html", repo / "odylith/tooling-shell.html")
    return entry


def test_generation_materializes_only_sealed_after_image_and_pins_pointer(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    (repo / "odylith/radar/source/unchanged.md").write_text("live drift\n", encoding="utf-8")

    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )

    assert (generation.repository_root / "odylith/radar/source/keep.md").read_text() == "after\n"
    assert (generation.repository_root / "odylith/radar/source/unchanged.md").read_text() == (
        "sealed unchanged\n"
    )
    entry = _publish(repo, generation, write_set)
    pinned = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert pinned.write_set_hash == write_set["write_set_hash"]
    assert greenfield_generation_state.active_generation_identity(repo) == {
        "status": "active",
        "write_set_hash": generation.write_set_hash,
        "generation_manifest_sha256": generation.manifest_sha256,
        "publication_sha256": hashlib.sha256(entry.encode()).hexdigest(),
    }
    assert (repo / "odylith/index.html").read_text() == entry
    assert not (repo / ".odylith/runtime/greenfield/active-generation.v1.json").exists()
    assert (pinned.generation_root / "generation-manifest.v1.json").read_text() == manifest_text


def test_generation_pointer_compare_and_switch_rejects_stale_precondition(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )
    entry = _publish(repo, generation, write_set)

    with pytest.raises(ValueError, match="active generation changed"):
        _publish(repo, generation, write_set)
    assert (repo / "odylith/index.html").read_text() == entry


@pytest.mark.parametrize("change", ("missing", "replaced", "altered"))
def test_invalid_publication_cannot_select_a_live_fallback(tmp_path: Path, change: str) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )
    entry = _publish(repo, generation, write_set)
    path = repo / "odylith/index.html"
    if change == "missing":
        path.unlink()
    elif change == "replaced":
        path.write_text("<!doctype html><title>Unsealed current view</title>\n")
    else:
        path.write_text(entry.replace("location.replace(target.href)", "location.assign(target.href)"))
    with pytest.raises((ValueError, RuntimeError)):
        greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert generation.generation_root.is_dir()


@pytest.mark.parametrize("read", ("sealed", "active", "historical"))
def test_generation_tamper_fails_every_immutable_pin(tmp_path: Path, read: str) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )
    entry = _publish(repo, generation, write_set)
    (generation.repository_root / "odylith/radar/source/keep.md").write_text("tampered\n")

    with pytest.raises((ValueError, RuntimeError), match="sealed manifest|committed repository state changed"):
        if read == "active":
            greenfield_generation_store.pin_active_greenfield_generation(repo)
        else:
            greenfield_generation_store.pin_greenfield_generation(
                repo_root=repo, write_set_hash=generation.write_set_hash,
                expected_write_set=write_set if read == "sealed" else None,
            )
    assert (repo / "odylith/index.html").read_text() == entry


def test_canonical_reader_stays_on_old_generation_until_pointer_switch(tmp_path: Path) -> None:
    repo, first_write_set = _write_set(tmp_path)
    first_manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(first_write_set)
    first_generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=first_write_set,
        manifest_text=first_manifest_text,
    )
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=repo,
        write_set=first_write_set,
    )
    first_entry = _publish(repo, first_generation, first_write_set)
    first_identity = greenfield_generation_state.active_generation_identity(repo)

    second_stage = tmp_path / "second-stage"
    shutil.copytree(first_generation.repository_root / "odylith", second_stage / "odylith")
    _write(second_stage / "odylith/radar/source/keep.md", "second generation\n")
    second_write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=repo,
        staged_root=second_stage,
    )
    second_manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(second_write_set)
    second_generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=second_write_set,
        manifest_text=second_manifest_text,
    )

    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=repo,
        write_set=second_write_set,
    )
    reader_during_projection = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert reader_during_projection.write_set_hash == first_write_set["write_set_hash"]
    assert greenfield_generation_state.active_generation_identity(repo) == first_identity
    assert (repo / "odylith/index.html").read_text() == first_entry
    assert (reader_during_projection.repository_root / "odylith/radar/source/keep.md").read_text() == (
        "after\n"
    )

    second_entry = _publish(repo, second_generation, second_write_set)
    reader_after_publication = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert reader_after_publication.write_set_hash == second_write_set["write_set_hash"]
    assert greenfield_generation_state.active_generation_identity(repo)["publication_sha256"] == hashlib.sha256(second_entry.encode()).hexdigest()
    assert (reader_after_publication.repository_root / "odylith/radar/source/keep.md").read_text() == (
        "second generation\n"
    )
    assert greenfield_generation_store.pin_greenfield_generation(
        repo_root=repo, write_set_hash=first_generation.write_set_hash, expected_write_set=first_write_set,
    ) == first_generation


def test_generation_reuse_does_not_republish_or_approve_a_transaction(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=write_set, manifest_text=manifest_text,
    )
    entry = _publish(repo, generation, write_set)
    first_identity = greenfield_generation_state.active_generation_identity(repo)
    reused = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=write_set, manifest_text=manifest_text,
    )
    with pytest.raises(ValueError, match="active generation changed"):
        _publish(repo, reused, write_set)
    second_identity = greenfield_generation_state.active_generation_identity(repo)
    assert reused == generation
    assert generation.generation_root.name == write_set["write_set_hash"]
    assert "transaction_hash" not in first_identity
    assert second_identity == first_identity
    assert (repo / "odylith/index.html").read_text() == entry
    assert not (repo / ".odylith/runtime/greenfield/create-journal").exists()
    assert first_identity["write_set_hash"] == second_identity["write_set_hash"] == write_set["write_set_hash"]
    assert first_identity["generation_manifest_sha256"] == second_identity["generation_manifest_sha256"]
    assert greenfield_generation_store.pin_active_greenfield_generation(repo) == generation
    assert (generation.generation_root / "generation-manifest.v1.json").read_text() == manifest_text


def test_historical_generation_cannot_borrow_a_fresh_predecessor_bound_write_set(tmp_path: Path) -> None:
    repo, original_write_set = _write_set(tmp_path)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=original_write_set,
        manifest_text=greenfield_generation_store.compile_greenfield_generation_manifest(original_write_set),
    )
    entry = _publish(repo, generation, original_write_set)
    identity = greenfield_generation_state.active_generation_identity(repo)
    fresh_write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=generation.repository_root,
        staged_root=generation.repository_root,
        publication_precondition=identity,
    )
    assert fresh_write_set["write_set_hash"] != generation.write_set_hash
    with pytest.raises(ValueError, match="generation differs from its sealed write set"):
        _publish(repo, generation, fresh_write_set)
    assert greenfield_generation_state.active_generation_identity(repo) == identity
    assert (repo / "odylith/index.html").read_text() == entry
