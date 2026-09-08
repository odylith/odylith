from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence import greenfield_commit_transaction
from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_commit_journal
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from tests.unit.runtime.test_greenfield_transaction_provenance import _transaction, _rewrite_sealed_transaction


def _sealed_input(tmp_path: Path) -> tuple[Path, dict, str]:
    repo, staged = tmp_path / "repo", tmp_path / "staged"
    repo.mkdir()
    (staged / "odylith/radar/source").mkdir(parents=True)
    (staged / "odylith/radar/source/project.md").write_text("Reviewed project\n")
    write_set = write_sets.compile_greenfield_repository_write_set(source_root=repo, staged_root=staged)
    return repo, write_set, generations.compile_greenfield_generation_manifest(write_set)


def test_generation_identity_and_exact_manifest_exist_before_transaction_hash(tmp_path, monkeypatch):
    repo, write_set, manifest_text = _sealed_input(tmp_path)
    manifest = json.loads(manifest_text)
    assert "transaction_hash" not in manifest
    assert manifest["write_set_hash"] == write_set["write_set_hash"]

    def forbidden(*args, **kwargs):
        raise AssertionError("generation manifest compilation ran after sealing")

    monkeypatch.setattr(generations, "compile_greenfield_generation_manifest", forbidden)
    pinned = generations.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=write_set, manifest_text=manifest_text,
    )
    assert pinned.generation_root.name == write_set["write_set_hash"]
    assert (pinned.generation_root / "generation-manifest.v1.json").read_bytes() == manifest_text.encode()
    assert pinned.manifest_sha256 == hashlib.sha256(manifest_text.encode()).hexdigest()
    assert (pinned.repository_root / "odylith/radar/source/project.md").read_text() == "Reviewed project\n"


@pytest.mark.parametrize("change", ["missing", "format", "binding", "counts", "fingerprints", "extra"])
def test_invalid_sealed_generation_manifest_fails_before_materialization(tmp_path, change):
    repo, write_set, manifest_text = _sealed_input(tmp_path)
    manifest = json.loads(manifest_text)
    if change == "missing":
        manifest_text = ""
    elif change == "format":
        manifest_text = json.dumps(manifest)
    else:
        if change == "binding":
            manifest["write_set_hash"] = "f" * 64
        elif change == "counts":
            manifest["file_count"] += 1
        elif change == "fingerprints":
            manifest["after_fingerprints"]["odylith/radar"] = "f" * 64
        else:
            manifest["unreviewed"] = "new metadata"
        manifest_text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with pytest.raises((ValueError, RuntimeError)):
        generations.materialize_immutable_greenfield_generation(
            repo_root=repo, write_set=write_set, manifest_text=manifest_text,
        )
    assert not (repo / ".odylith/runtime/greenfield/generations").exists()


def test_real_confirm_copies_sealed_manifest_and_history_survives_pending_cleanup(tmp_path, monkeypatch):
    transaction = _transaction(tmp_path)
    path = tmp_path / "proposal.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(path, transaction)
    sealed_manifest = transaction.prewrite_package.generation_manifest_text
    write_hash = transaction.prewrite_package.repository_write_set["write_set_hash"]

    def forbidden(*args, **kwargs):
        raise AssertionError("manifest generation is forbidden after CONFIRM")

    monkeypatch.setattr(generations, "compile_greenfield_generation_manifest", forbidden)
    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path, transaction_file=path, transaction_hash=transaction.transaction_hash, confirm=True,
    )
    assert result["product_create_transaction"]["transaction_hash"] == transaction.transaction_hash
    generation = GreenfieldCommitJournal.pin_reviewed_generation(
        repo_root=tmp_path, transaction_hash=transaction.transaction_hash,
    )
    assert generation.generation_root.name == write_hash
    assert (generation.generation_root / "generation-manifest.v1.json").read_bytes() == sealed_manifest.encode()
    retry = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path, transaction_file=path, transaction_hash=transaction.transaction_hash, confirm=True,
    )
    assert retry == result
    path.unlink()
    path.with_name(path.name + ".compiler-receipt.v1.json").unlink()
    navigation = greenfield_post_confirm_handoff.post_confirm_navigation(
        tmp_path, transaction_hash=transaction.transaction_hash,
    )
    assert Path(navigation["dashboard_path"]) == generation.repository_root / "odylith/index.html"
    assert navigation["generation_transaction_hash"] == transaction.transaction_hash


@pytest.mark.parametrize("change", ["missing", "bytes", "binding"])
def test_commit_loader_rejects_invalid_manifest_even_with_rehashed_outer_receipt(tmp_path, change):
    transaction = _transaction(tmp_path)
    path = tmp_path / "proposal.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(path, transaction)
    payload = json.loads(path.read_text())
    package = payload["prewrite_package"]
    if change == "missing":
        package.pop("generation_manifest_text")
    elif change == "bytes":
        package["generation_manifest_text"] += " "
    else:
        manifest = json.loads(package["generation_manifest_text"])
        manifest["write_set_hash"] = "f" * 64
        package["generation_manifest_text"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _rewrite_sealed_transaction(path, payload)
    before = write_sets.greenfield_managed_fingerprints(tmp_path)
    with pytest.raises((RuntimeError, ValueError), match="manifest|binding"):
        greenfield_commit_transaction.load_sealed_product_create_commit(path, repo_root=tmp_path)
    assert write_sets.greenfield_managed_fingerprints(tmp_path) == before
    assert not (tmp_path / ".odylith/runtime/greenfield/create-journal").exists()


def test_shared_generation_does_not_approve_a_different_transaction(tmp_path):
    first = _transaction(tmp_path)
    second = replace(first, quality_manifest={**first.quality_manifest, "audit_note": "Separate reviewed transaction"})
    second = replace(second, transaction_hash=greenfield_create_transaction.product_create_transaction_hash(second))
    assert first.transaction_hash != second.transaction_hash
    assert first.prewrite_package.repository_write_set == second.prewrite_package.repository_write_set
    first_path, second_path = tmp_path / "first.json", tmp_path / "second.json"
    for transaction, path in ((first, first_path), (second, second_path)):
        greenfield_create_transaction.write_compiled_product_create_transaction_file(path, transaction)
    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path, transaction_file=first_path, transaction_hash=first.transaction_hash, confirm=True,
    )
    before = write_sets.greenfield_managed_fingerprints(tmp_path)
    with pytest.raises(ValueError, match="active generation changed"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path, transaction_file=second_path, transaction_hash=second.transaction_hash, confirm=True,
        )
    assert write_sets.greenfield_managed_fingerprints(tmp_path) == before
    assert greenfield_generation_state.active_generation_identity(tmp_path)["transaction_hash"] == first.transaction_hash
    assert not (tmp_path / ".odylith/runtime/greenfield/create-journal" / second.transaction_hash).exists()
    GreenfieldCommitJournal.pin_reviewed_generation(repo_root=tmp_path, transaction_hash=first.transaction_hash)


def test_abort_cannot_collect_another_transactions_noncurrent_historical_generation(tmp_path):
    first = _transaction(tmp_path)
    path = tmp_path / "first.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(path, first)
    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path, transaction_file=path, transaction_hash=first.transaction_hash, confirm=True,
    )
    historical = GreenfieldCommitJournal.pin_reviewed_generation(repo_root=tmp_path, transaction_hash=first.transaction_hash)

    # Exercise collection against a noncurrent closed reference, independently of admission.
    later_write_set = write_sets.compile_greenfield_repository_write_set(source_root=tmp_path, staged_root=tmp_path)
    later = generations.materialize_immutable_greenfield_generation(
        repo_root=tmp_path, write_set=later_write_set,
        manifest_text=generations.compile_greenfield_generation_manifest(later_write_set),
    )
    generations.publish_greenfield_generation(
        repo_root=tmp_path, generation=later, transaction_hash="c" * 64,
        expected_active_identity=later_write_set["active_generation_precondition"],
    )
    assert later.generation_root != historical.generation_root
    aborted = GreenfieldCommitJournal(
        repo_root=tmp_path, transaction_hash="b" * 64, write_set=first.prewrite_package.repository_write_set,
    )
    aborted.prepare()
    aborted.mark_aborted()
    assert GreenfieldCommitJournal.pin_reviewed_generation(
        repo_root=tmp_path, transaction_hash=first.transaction_hash,
    ) == historical


@pytest.mark.parametrize("state", ["projecting", "closed"])
def test_legacy_journal_is_preserved_without_new_layout_recovery(tmp_path, state):
    repo, write_set, _ = _sealed_input(tmp_path)
    journal = GreenfieldCommitJournal(repo_root=repo, transaction_hash="a" * 64, write_set=write_set)
    journal.prepare()
    record = json.loads(journal.state_path.read_text())
    record.pop("record_hash")
    record.update(version="odylith.greenfield.commit_journal.v3", state=state)
    record["record_hash"] = greenfield_commit_journal._record_hash(record)
    greenfield_commit_journal._write_journal_record(journal.root, record)
    before = journal.state_path.read_bytes()
    if state == "projecting":
        with pytest.raises(greenfield_commit_journal.GreenfieldCommitJournalError, match="recorded runtime"):
            GreenfieldCommitJournal.recover_pending_journals(repo_root=repo, excluding_transaction_hash="b" * 64)
    else:
        GreenfieldCommitJournal.recover_pending_journals(repo_root=repo, excluding_transaction_hash="b" * 64)
    assert journal.state_path.read_bytes() == before
    assert not (journal.root.parent / "manual-recovery").exists()


@pytest.mark.parametrize("relative", [".odylith/runtime/greenfield/generations", ".odylith/runtime/greenfield"])
def test_reviewed_navigation_rejects_generation_ancestor_symlinks(tmp_path, relative):
    repo = tmp_path / "repo"
    repo.mkdir()
    transaction = _transaction(repo)
    path = repo / "proposal.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(path, transaction)
    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=repo, transaction_file=path, transaction_hash=transaction.transaction_hash, confirm=True,
    )
    source = repo / relative
    outside = tmp_path / "relocated"
    source.rename(outside)
    source.symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError, match="unsafe"):
        greenfield_post_confirm_handoff.post_confirm_navigation(repo, transaction_hash=transaction.transaction_hash)
