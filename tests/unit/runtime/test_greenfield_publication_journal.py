"""Stopped-writer publication laws with the production HTML entry and journal."""

from __future__ import annotations

from pathlib import Path
import shutil
import signal

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_prewrite_stage_root import staged_greenfield_prewrite_root
from tests.unit.runtime.test_greenfield_commit_journal import _kill_commit_child


def _protected_transition(root: Path):
    (root / "odylith/radar/source").mkdir(parents=True)
    (root / "odylith/index.html").write_text('<!doctype html><title>Baseline</title><p>Complete baseline</p>')
    for name in ("first", "second"):
        (root / f"odylith/radar/source/{name}.md").write_text(f"{name} before\n")
    baseline = kernel.compile_greenfield_repository_write_set(source_root=root, staged_root=root)
    manifest = store.compile_greenfield_generation_manifest(baseline)
    initial = store.materialize_immutable_greenfield_generation(repo_root=root, write_set=baseline, manifest_text=manifest)
    entry = state.compile_greenfield_publication_entry(
        write_set_hash=initial.write_set_hash, generation_manifest_sha256=initial.manifest_sha256,
    )
    store.publish_greenfield_generation(
        repo_root=root, generation=initial, write_set=baseline,
        publication_entry_text=entry,
    )
    shutil.copy2(initial.repository_root / "odylith/index.html", root / "odylith/tooling-shell.html")
    with staged_greenfield_prewrite_root(root) as stage:
        (stage / "odylith/index.html").write_text('<!doctype html><title>After</title><p>Complete after</p>')
        for name in ("first", "second"):
            (stage / f"odylith/radar/source/{name}.md").write_text(f"{name} after\n")
        transition = kernel.compile_greenfield_repository_write_set(source_root=root, staged_root=stage)
    return initial, entry.encode("utf-8"), transition


@pytest.mark.parametrize("phase", ["first_write", "before_pointer", "after_pointer"])
def test_sigkill_never_selects_partial_compatibility_files_before_recovery(tmp_path: Path, phase: str) -> None:
    root = tmp_path / "repo"
    baseline, entry, write_set = _protected_transition(root)
    child = _kill_commit_child(root=root, write_set=write_set, mode=phase)
    assert child.returncode == -signal.SIGKILL, child.stderr

    selected = store.pin_active_greenfield_generation(root)
    expected = "after" if phase == "after_pointer" else "before"
    for name in ("first", "second"):
        assert (selected.repository_root / f"odylith/radar/source/{name}.md").read_text() == f"{name} {expected}\n"
    if phase != "after_pointer":
        assert selected == baseline
        assert (root / "odylith/index.html").read_bytes() == entry
    journal = GreenfieldCommitJournal(repo_root=root, transaction_hash="a" * 64, write_set=write_set)
    assert "odylith/tooling-shell.html" in journal.paths
    assert "odylith/index.html" not in journal.paths
    result = journal.recover_or_return_committed()
    assert (result is not None) == (phase == "after_pointer")
    if phase != "after_pointer":
        assert (root / "odylith/index.html").read_bytes() == entry
        assert (root / "odylith/tooling-shell.html").read_bytes() == (
            baseline.repository_root / "odylith/index.html"
        ).read_bytes()


def test_pointer_equality_cannot_create_an_unadmitted_transaction_receipt(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _baseline, _entry, write_set = _protected_transition(root)
    child = _kill_commit_child(root=root, write_set=write_set, mode="after_pointer")
    assert child.returncode == -signal.SIGKILL, child.stderr
    wrong = GreenfieldCommitJournal(repo_root=root, transaction_hash="b" * 64, write_set=write_set)
    assert wrong.recover_or_return_committed() is None
    assert not wrong.root.exists()
    GreenfieldCommitJournal.recover_pending_journals(repo_root=root)
    assert state.active_generation_identity(root) != write_set["active_generation_precondition"]
    with pytest.raises(ValueError, match="preconditions changed"):
        kernel.require_greenfield_repository_preconditions(repo_root=root, write_set=write_set)
    assert not wrong.root.exists()
