from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


TX_HASH = "a" * 64
NEXT_TX_HASH = "b" * 64


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_set(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    source = tmp_path / "repo"
    stage = tmp_path / "stage"
    _write(source / "odylith/radar/source/keep.md", "before\n")
    _write(source / "odylith/radar/source/unchanged.md", "sealed unchanged\n")
    shutil.copytree(source / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/keep.md", "after\n")
    return source, greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=source,
        staged_root=stage,
    )


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
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=generation,
        expected_active_identity=write_set["active_generation_precondition"],
        transaction_hash=TX_HASH,
    )
    pinned = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert pinned.write_set_hash == write_set["write_set_hash"]
    assert greenfield_generation_state.active_generation_identity(repo)["transaction_hash"] == TX_HASH
    assert (pinned.generation_root / "generation-manifest.v1.json").read_text() == manifest_text


def test_generation_pointer_compare_and_switch_rejects_stale_precondition(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=generation,
        expected_active_identity=write_set["active_generation_precondition"],
        transaction_hash=TX_HASH,
    )

    with pytest.raises(ValueError, match="active generation changed"):
        greenfield_generation_store.publish_greenfield_generation(
            repo_root=repo,
            generation=generation,
            expected_active_identity=greenfield_generation_state.no_active_generation_identity(),
            transaction_hash=NEXT_TX_HASH,
        )


def test_superseded_generation_is_not_an_active_canonical_read(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=generation,
        expected_active_identity=write_set["active_generation_precondition"],
        transaction_hash=TX_HASH,
    )
    greenfield_generation_state.supersede_active_generation(
        repo_root=repo,
        expected_transaction_hash=TX_HASH,
    )

    with pytest.raises(RuntimeError, match="no active immutable generation"):
        greenfield_generation_store.pin_active_greenfield_generation(repo)


def test_generation_tamper_fails_sealed_readback(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )
    (generation.repository_root / "odylith/radar/source/keep.md").write_text("tampered\n")

    with pytest.raises(ValueError, match="committed repository state changed"):
        greenfield_generation_store.pin_greenfield_generation(
            repo_root=repo,
            write_set_hash=str(write_set["write_set_hash"]),
            expected_write_set=write_set,
        )


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
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=first_generation,
        expected_active_identity=first_write_set["active_generation_precondition"],
        transaction_hash=TX_HASH,
    )

    second_stage = tmp_path / "second-stage"
    shutil.copytree(repo / "odylith", second_stage / "odylith")
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
    assert greenfield_generation_state.active_generation_identity(repo)["transaction_hash"] == TX_HASH
    assert (reader_during_projection.repository_root / "odylith/radar/source/keep.md").read_text() == (
        "after\n"
    )

    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=second_generation,
        expected_active_identity=second_write_set["active_generation_precondition"],
        transaction_hash=NEXT_TX_HASH,
    )
    reader_after_publication = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert reader_after_publication.write_set_hash == second_write_set["write_set_hash"]
    assert greenfield_generation_state.active_generation_identity(repo)["transaction_hash"] == NEXT_TX_HASH
    assert (reader_after_publication.repository_root / "odylith/radar/source/keep.md").read_text() == (
        "second generation\n"
    )


def test_write_set_address_is_reused_without_reusing_outer_transaction_identity(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=write_set, manifest_text=manifest_text,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo, generation=generation,
        expected_active_identity=write_set["active_generation_precondition"], transaction_hash=TX_HASH,
    )
    first_identity = greenfield_generation_state.active_generation_identity(repo)
    reused = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=write_set, manifest_text=manifest_text,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo, generation=reused,
        expected_active_identity=first_identity, transaction_hash=NEXT_TX_HASH,
    )
    second_identity = greenfield_generation_state.active_generation_identity(repo)
    assert reused == generation
    assert generation.generation_root.name == write_set["write_set_hash"]
    assert first_identity["transaction_hash"] == TX_HASH
    assert second_identity["transaction_hash"] == NEXT_TX_HASH
    assert first_identity["write_set_hash"] == second_identity["write_set_hash"] == write_set["write_set_hash"]
    assert first_identity["generation_manifest_sha256"] == second_identity["generation_manifest_sha256"]
    assert greenfield_generation_store.pin_active_greenfield_generation(repo) == generation
    assert (generation.generation_root / "generation-manifest.v1.json").read_text() == manifest_text
