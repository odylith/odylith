"""Later writers retain immutable views and settle admitted creates first."""

from __future__ import annotations

import json
from pathlib import Path
import signal
import shutil
import threading

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary
from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from tests.unit.runtime.test_greenfield_commit_journal import _kill_commit_child
from tests.unit.runtime.test_greenfield_generation_store import _publish
from tests.unit.runtime.test_greenfield_baseline_activation import _activate, _complete


TX_HASH = "c" * 64


def test_inactive_writer_blocks_activation_until_its_complete_result(tmp_path):
    _complete(tmp_path)
    first_write, finish = threading.Event(), threading.Event()
    results = []

    def operation():
        (tmp_path / "odylith/radar/radar.html").write_bytes(b"NEW RADAR\n")
        first_write.set()
        assert finish.wait(5), "test writer was not released"
        (tmp_path / "odylith/registry/registry.html").write_bytes(b"NEW REGISTRY\n")
        return 0

    def run():
        try:
            results.append(_run(tmp_path, operation))
        except BaseException as exc:
            results.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert first_write.wait(5), "test writer did not start"
        with pytest.raises(greenfield_repository_lock.GreenfieldRepositoryBusyError):
            _activate(tmp_path)
        assert greenfield_generation_state.read_active_publication(tmp_path) is None
    finally:
        finish.set()
        worker.join(5)
    assert not worker.is_alive()
    assert results == [0]
    _activate(tmp_path)
    published = greenfield_generation_store.pin_active_greenfield_generation(tmp_path)
    assert (published.repository_root / "odylith/radar/radar.html").read_bytes() == b"NEW RADAR\n"
    assert (published.repository_root / "odylith/registry/registry.html").read_bytes() == b"NEW REGISTRY\n"


def test_inactive_publication_state_is_read_under_lock(tmp_path, monkeypatch):
    observed = []
    read = greenfield_generation_state.read_active_publication

    def read_locked(root):
        with pytest.raises(greenfield_repository_lock.GreenfieldRepositoryBusyError):
            with greenfield_repository_lock.greenfield_repository_lock(root):
                pytest.fail("publication read preceded lock admission")
        observed.append(True)
        return read(root)

    monkeypatch.setattr(greenfield_generation_state, "read_active_publication", read_locked)
    assert _run(tmp_path, lambda: 0) == 0
    assert observed


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _active_repository(tmp_path: Path) -> tuple[Path, greenfield_generation_store.PinnedGreenfieldGeneration]:
    repo = tmp_path / "repo"
    stage = tmp_path / "stage"
    _write(repo / "odylith/radar/source/keep.md", "before\n")
    _write(repo / "odylith/index.html", "<!doctype html><title>Before dashboard</title>\n")
    baseline_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(source_root=repo, staged_root=repo)
    baseline = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=baseline_set,
        manifest_text=greenfield_generation_store.compile_greenfield_generation_manifest(baseline_set),
    )
    _publish(repo, baseline, baseline_set)
    shutil.copytree(baseline.repository_root / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/keep.md", "reviewed\n")
    _write(stage / "odylith/index.html", "<!doctype html><title>Reviewed dashboard</title>\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=repo,
        staged_root=stage,
    )
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    journal = GreenfieldCommitJournal(repo_root=repo, transaction_hash=TX_HASH, write_set=write_set)
    journal.prepare()
    result = {"status": "created", "transaction_hash": TX_HASH}
    with GreenfieldApplyTransaction(
        repo, paths=journal.paths, snapshot_root=journal.snapshot_root, retain_snapshot=True,
    ) as transaction:
        journal.mark_prepared()
        generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
            repo_root=repo, write_set=write_set, manifest_text=manifest_text,
        )
        publication = greenfield_generation_state.compile_greenfield_publication_entry(
            write_set_hash=generation.write_set_hash, generation_manifest_sha256=generation.manifest_sha256,
        )
        journal.mark_projecting(
            result, generation_manifest_sha256=generation.manifest_sha256, publication_entry_text=publication,
        )
        greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
            repo_root=repo, write_set=write_set, temporary_directory=journal.staging_root,
        )
        greenfield_repository_write_set.require_greenfield_repository_after_state(
            repo_root=repo, write_set=write_set,
        )
        transaction.publish(
            lambda: greenfield_generation_store.publish_greenfield_generation(
                repo_root=repo, generation=generation,
                write_set=write_set, publication_entry_text=publication,
            ),
            published_probe=journal.publication_is_active,
        )
        journal.mark_published(result, generation_manifest_sha256=generation.manifest_sha256)
        journal.mark_closed(result, generation_manifest_sha256=generation.manifest_sha256)
    journal.discard_committed_snapshot()
    return repo, generation


def _run(repo: Path, operation) -> int:
    return greenfield_managed_mutation_boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo,
        command_tokens=("radar", "refresh"),
        operation=lambda _descriptor: operation(),
    )


@pytest.mark.parametrize(
    ("tokens", "expected"),
    (
        (("radar", "refresh"), True),
        (("future-writer", "apply"), True),
        (("validate", "component-registry"), False),
        (("atlas", "render", "--check-only"), False),
        (("codex", "prompt-context"), False),
        (("claude", "prompt-bundle"), False),
        (("greenfield", "create"), False),
    ),
)
def test_command_classification_defaults_unknown_commands_to_writer(
    tokens: tuple[str, ...],
    expected: bool,
) -> None:
    assert greenfield_managed_mutation_boundary.command_may_mutate_greenfield_managed_paths(tokens) is expected


def test_successful_changed_writer_publishes_immutable_successor_only_after_return(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)
    observed: list[tuple[Path, str]] = []

    def operation() -> int:
        _write(repo / "odylith/radar/source/keep.md", "writer partial\n")
        observed.append(greenfield_post_confirm_handoff.canonical_current_project_root(repo))
        _write(repo / "odylith/radar/source/keep.md", "writer complete\n")
        return 0

    assert _run(repo, operation) == 0
    assert observed == [(generation.repository_root, "active_generation_during_managed_write")]
    current = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert current.write_set_hash != generation.write_set_hash
    assert (current.repository_root / "odylith/radar/source/keep.md").read_text() == "writer complete\n"
    assert (generation.repository_root / "odylith/radar/source/keep.md").read_text() == "reviewed\n"
    assert greenfield_post_confirm_handoff.canonical_current_project_root(repo) == (
        current.repository_root,
        "active_generation",
    )


def test_noop_writer_keeps_reviewed_generation_active(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)
    entry = repo / "odylith/index.html"
    original = (entry.read_bytes(), entry.stat().st_mtime_ns)

    assert _run(repo, lambda: 0) == 0

    assert greenfield_post_confirm_handoff.canonical_current_project_root(repo) == (
        generation.repository_root,
        "active_generation",
    )
    assert (entry.read_bytes(), entry.stat().st_mtime_ns) == original


def test_failed_writer_retains_published_view_and_blocks_the_next_operation(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)
    entry = (repo / "odylith/index.html").read_bytes()

    def operation() -> int:
        _write(repo / "odylith/radar/source/keep.md", "failed partial\n")
        return 1

    assert _run(repo, operation) == 1
    assert (repo / "odylith/index.html").read_bytes() == entry
    assert greenfield_post_confirm_handoff.canonical_current_project_root(repo) == (
        generation.repository_root, "active_generation",
    )
    called = []
    with pytest.raises(RuntimeError, match="RECOVERY_REQUIRED"):
        _run(repo, lambda: called.append("must not run") or 0)
    assert called == []
    assert (repo / "odylith/radar/source/keep.md").read_text() == "failed partial\n"
    reviewed = greenfield_post_confirm_handoff.post_confirm_navigation(repo, transaction_hash=TX_HASH)
    assert reviewed["generation_transaction_hash"] == TX_HASH
    assert reviewed["dashboard_path"] == str(
        (generation.repository_root / "odylith/index.html").resolve()
    )


def test_reviewed_generation_link_remains_exact_after_later_success(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)

    assert _run(
        repo,
        lambda: (_write(repo / "odylith/radar/source/keep.md", "later truth\n") or 0),
    ) == 0

    reviewed = greenfield_post_confirm_handoff.post_confirm_navigation(repo, transaction_hash=TX_HASH)
    current = greenfield_post_confirm_handoff.post_confirm_navigation(repo)
    assert reviewed["view_status"] == "reviewed_generation"
    assert reviewed["generation_transaction_hash"] == TX_HASH
    assert reviewed["dashboard_path"] == str(
        (generation.repository_root / "odylith/index.html").resolve()
    )
    successor = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert current["view_status"] == "active_generation"
    assert current["dashboard_path"] == str(successor.repository_root / "odylith/index.html")
    assert successor.generation_root != generation.generation_root


def test_competing_writer_returns_busy_without_running_operation(tmp_path: Path) -> None:
    repo, _generation = _active_repository(tmp_path)
    called = False

    def operation() -> int:
        nonlocal called
        called = True
        return 0

    with greenfield_repository_lock.greenfield_repository_lock(repo):
        with pytest.raises(
            greenfield_managed_mutation_boundary.GreenfieldManagedMutationBusyError,
            match="BUSY_NO_WRITE",
        ):
            _run(repo, operation)
    assert called is False


def test_later_writer_closes_sigkilled_create_receipt_before_running(tmp_path: Path) -> None:
    repo, original = _active_repository(tmp_path)
    stage = tmp_path / "next-stage"
    shutil.copytree(original.repository_root / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/keep.md", "next reviewed create\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(source_root=repo, staged_root=stage)
    child = _kill_commit_child(root=repo, write_set=write_set, mode="after_pointer")
    assert child.returncode == -signal.SIGKILL, child.stderr
    transaction_hash = "a" * 64
    record_path = repo / ".odylith/runtime/greenfield/create-journal" / transaction_hash / "state.v1.json"
    assert json.loads(record_path.read_text())["state"] == "projecting"
    killed_generation = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert killed_generation.write_set_hash == write_set["write_set_hash"]
    observed = []

    def operation() -> int:
        observed.append(json.loads(record_path.read_text())["state"])
        assert greenfield_generation_store.pin_active_greenfield_generation(repo) == killed_generation
        _write(repo / "odylith/radar/source/keep.md", "complete later writer\n")
        return 0

    assert _run(repo, operation) == 0
    assert observed == ["closed"]
    successor = greenfield_generation_store.pin_active_greenfield_generation(repo)
    assert (successor.repository_root / "odylith/radar/source/keep.md").read_text() == "complete later writer\n"
    assert successor.write_set_hash != killed_generation.write_set_hash
    for reviewed_hash, expected in ((TX_HASH, original), (transaction_hash, killed_generation)):
        reviewed = greenfield_post_confirm_handoff.post_confirm_navigation(repo, transaction_hash=reviewed_hash)
        assert reviewed["generation_transaction_hash"] == reviewed_hash
        assert reviewed["dashboard_path"] == str(expected.repository_root / "odylith/index.html")


def test_corrupt_immutable_generation_blocks_later_operation(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)
    entry = (repo / "odylith/index.html").read_bytes()
    _write(generation.repository_root / "odylith/radar/source/keep.md", "corrupted immutable source\n")
    called = []
    with pytest.raises(RuntimeError, match="sealed manifest"):
        _run(repo, lambda: called.append("must not run") or 0)
    assert called == []
    assert (repo / "odylith/index.html").read_bytes() == entry
