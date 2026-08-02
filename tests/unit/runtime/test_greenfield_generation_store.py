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
    (repo / "odylith/radar/source/unchanged.md").write_text("live drift\n", encoding="utf-8")

    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        transaction_hash=TX_HASH,
        write_set=write_set,
    )

    assert (generation.repository_root / "odylith/radar/source/keep.md").read_text() == "after\n"
    assert (generation.repository_root / "odylith/radar/source/unchanged.md").read_text() == (
        "sealed unchanged\n"
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=generation,
        expected_active_identity=write_set["active_generation_precondition"],
    )
    assert greenfield_generation_store.pin_active_greenfield_generation(repo).transaction_hash == TX_HASH


def test_generation_pointer_compare_and_switch_rejects_stale_precondition(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        transaction_hash=TX_HASH,
        write_set=write_set,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=generation,
        expected_active_identity=write_set["active_generation_precondition"],
    )

    with pytest.raises(ValueError, match="active generation changed"):
        greenfield_generation_store.publish_greenfield_generation(
            repo_root=repo,
            generation=generation,
            expected_active_identity=greenfield_generation_state.no_active_generation_identity(),
        )


def test_superseded_generation_is_not_an_active_canonical_read(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        transaction_hash=TX_HASH,
        write_set=write_set,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=generation,
        expected_active_identity=write_set["active_generation_precondition"],
    )
    greenfield_generation_state.supersede_active_generation(
        repo_root=repo,
        expected_transaction_hash=TX_HASH,
    )

    with pytest.raises(RuntimeError, match="no active immutable generation"):
        greenfield_generation_store.pin_active_greenfield_generation(repo)


def test_generation_tamper_fails_sealed_readback(tmp_path: Path) -> None:
    repo, write_set = _write_set(tmp_path)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        transaction_hash=TX_HASH,
        write_set=write_set,
    )
    (generation.repository_root / "odylith/radar/source/keep.md").write_text("tampered\n")

    with pytest.raises(ValueError, match="committed repository state changed"):
        greenfield_generation_store.pin_greenfield_generation(
            repo_root=repo,
            transaction_hash=TX_HASH,
            expected_write_set=write_set,
        )


def test_canonical_reader_stays_on_old_generation_until_pointer_switch(tmp_path: Path) -> None:
    repo, first_write_set = _write_set(tmp_path)
    first_generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        transaction_hash=TX_HASH,
        write_set=first_write_set,
    )
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=repo,
        write_set=first_write_set,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=first_generation,
        expected_active_identity=first_write_set["active_generation_precondition"],
    )

    second_stage = tmp_path / "second-stage"
    shutil.copytree(repo / "odylith", second_stage / "odylith")
    _write(second_stage / "odylith/radar/source/keep.md", "second generation\n")
    second_write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=repo,
        staged_root=second_stage,
    )
    second_generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        transaction_hash=NEXT_TX_HASH,
        write_set=second_write_set,
    )

    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=repo,
        write_set=second_write_set,
    )
    reader_during_projection = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert reader_during_projection.transaction_hash == TX_HASH
    assert (reader_during_projection.repository_root / "odylith/radar/source/keep.md").read_text() == (
        "after\n"
    )

    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo,
        generation=second_generation,
        expected_active_identity=second_write_set["active_generation_precondition"],
    )
    reader_after_publication = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert reader_after_publication.transaction_hash == NEXT_TX_HASH
    assert (reader_after_publication.repository_root / "odylith/radar/source/keep.md").read_text() == (
        "second generation\n"
    )
