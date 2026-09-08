from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary
from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction


TX_HASH = "c" * 64


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _active_repository(tmp_path: Path) -> tuple[Path, greenfield_generation_store.PinnedGreenfieldGeneration]:
    repo = tmp_path / "repo"
    stage = tmp_path / "stage"
    _write(repo / "odylith/radar/source/keep.md", "before\n")
    _write(repo / "odylith/index.html", "before dashboard\n")
    shutil.copytree(repo / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/keep.md", "reviewed\n")
    _write(stage / "odylith/index.html", "reviewed dashboard\n")
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
        journal.mark_projecting(result, generation_manifest_sha256=generation.manifest_sha256)
        greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
            repo_root=repo, write_set=write_set, temporary_directory=journal.staging_root,
        )
        greenfield_repository_write_set.require_greenfield_repository_after_state(
            repo_root=repo, write_set=write_set,
        )
        transaction.publish(
            lambda: greenfield_generation_store.publish_greenfield_generation(
                repo_root=repo, generation=generation,
                expected_active_identity=write_set["active_generation_precondition"], transaction_hash=TX_HASH,
            ),
            published_probe=lambda: greenfield_generation_state.active_generation_is(
                repo_root=repo, transaction_hash=TX_HASH, write_set_hash=generation.write_set_hash,
                generation_manifest_sha256=generation.manifest_sha256,
            ),
        )
        journal.mark_published(result, generation_manifest_sha256=generation.manifest_sha256)
        journal.mark_closed(result, generation_manifest_sha256=generation.manifest_sha256)
    journal.discard_committed_snapshot()
    return repo, generation


def _run(repo: Path, operation) -> int:
    return greenfield_managed_mutation_boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo,
        command_tokens=("radar", "refresh"),
        operation=operation,
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


def test_successful_changed_writer_supersedes_only_after_operation_returns(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)
    observed: list[tuple[Path, str]] = []

    def operation() -> int:
        _write(repo / "odylith/radar/source/keep.md", "writer partial\n")
        observed.append(greenfield_post_confirm_handoff.canonical_current_project_root(repo))
        _write(repo / "odylith/radar/source/keep.md", "writer complete\n")
        return 0

    assert _run(repo, operation) == 0
    assert observed == [(generation.repository_root, "active_generation_during_managed_write")]
    state = greenfield_generation_state.read_active_generation_state(repo)
    assert state is not None and state["status"] == greenfield_generation_state.SUPERSEDED
    assert greenfield_post_confirm_handoff.canonical_current_project_root(repo) == (
        repo,
        "live_after_supersession",
    )


def test_noop_writer_keeps_reviewed_generation_active(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)

    assert _run(repo, lambda: 0) == 0

    assert greenfield_post_confirm_handoff.canonical_current_project_root(repo) == (
        generation.repository_root,
        "active_generation",
    )


def test_failed_writer_does_not_supersede_or_expose_partial_live_tree(tmp_path: Path) -> None:
    repo, generation = _active_repository(tmp_path)

    def operation() -> int:
        _write(repo / "odylith/radar/source/keep.md", "failed partial\n")
        return 1

    assert _run(repo, operation) == 1
    state = greenfield_generation_state.read_active_generation_state(repo)
    assert state is not None and state["status"] == greenfield_generation_state.ACTIVE
    with pytest.raises(
        greenfield_post_confirm_handoff.GreenfieldCanonicalViewUnavailableError,
        match="potentially partial live view",
    ):
        greenfield_post_confirm_handoff.canonical_current_project_root(repo)
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
    assert current["view_status"] == "live_after_supersession"
    assert current["dashboard_path"] == str((repo / "odylith/index.html").resolve())


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
