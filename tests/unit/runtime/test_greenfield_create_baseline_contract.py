"""ProductCreate cannot defer first publication setup until after confirmation."""

from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_commit_transaction as commits
from odylith.runtime.domain_intelligence import greenfield_compiled_package_contract as packages
from odylith.runtime.domain_intelligence import greenfield_create_transaction as transactions
from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_proposals as proposals
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as writers
from odylith.runtime.domain_intelligence import greenfield_repository_lock as locks
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from tests.unit.runtime.greenfield_authored_proposal_fixtures import _canonical_model_authored_greenfield_fixture
from tests.unit.runtime.test_greenfield_transaction_provenance import _rewrite_sealed_transaction, _transaction


def _unactivated_envelope(root):
    write_set = kernel.compile_greenfield_repository_write_set(source_root=root, staged_root=root)
    manifest = store.compile_greenfield_generation_manifest(write_set)
    publication = state.compile_greenfield_publication_entry(
        write_set_hash=write_set["write_set_hash"],
        generation_manifest_sha256=hashlib.sha256(manifest.encode()).hexdigest(),
    )
    return {
        "repository_write_set": write_set,
        "generation_manifest_text": manifest,
        "publication_entry_text": publication,
    }


def test_direct_compiler_rejects_unactivated_repository_before_staging(tmp_path, monkeypatch):
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    before = kernel.greenfield_managed_fingerprints(tmp_path)
    monkeypatch.setattr(
        proposals, "_build_authored_prewrite_package",
        lambda **_: pytest.fail("unactivated repository reached staging"),
    )
    with pytest.raises((ValueError, RuntimeError), match="generation|baseline"):
        proposals.compile_greenfield_create_transaction(
            repo_root=tmp_path, proposal=proposal, release_selector="0.0.1", proposal_ready=True,
        )
    assert kernel.greenfield_managed_fingerprints(tmp_path) == before
    assert state.read_active_publication(tmp_path) is None
    assert not (tmp_path / ".odylith/runtime/greenfield/create-journal").exists()


def test_package_cannot_become_confirmable_with_an_unactivated_predecessor(tmp_path):
    transaction = _transaction(tmp_path / "active")
    envelope = _unactivated_envelope(tmp_path / "inactive")
    assert envelope["repository_write_set"]["active_generation_precondition"]["status"] == "none"
    # NONE is valid for the generic first-baseline kernel, not for ProductCreate.
    kernel.require_compiled_greenfield_repository_write_set(envelope["repository_write_set"])
    package = replace(transaction.prewrite_package, **envelope)
    with pytest.raises(ValueError, match="published baseline before confirmation"):
        packages.require_complete_compiled_greenfield_package(package, release_selector="0.0.1")


def test_commit_loader_rejects_unactivated_predecessor_even_with_rehashed_receipt(tmp_path):
    root = tmp_path / "active"
    transaction = _transaction(root)
    target = root / "transaction.json"
    transactions.write_compiled_product_create_transaction_file(target, transaction)
    payload = json.loads(target.read_text())
    payload["prewrite_package"].update(_unactivated_envelope(tmp_path / "inactive"))
    _rewrite_sealed_transaction(target, payload)
    before = kernel.greenfield_managed_fingerprints(root)
    publication = (root / "odylith/index.html").read_bytes()
    with pytest.raises(ValueError, match="published baseline before confirmation"):
        commits.load_sealed_product_create_commit(target, repo_root=root)
    assert kernel.greenfield_managed_fingerprints(root) == before
    assert (root / "odylith/index.html").read_bytes() == publication
    assert not (root / ".odylith/runtime/greenfield/create-journal").exists()


def _compiled_result(template):
    return (
        template.proposal,
        SimpleNamespace(to_dict=lambda: {"status": "passed", "issues": []}),
        SimpleNamespace(package=template.prewrite_package, backlog_result=template.backlog_result),
        template.quality_manifest,
    )


@pytest.mark.parametrize("phase", ("readiness", "staging", "verification"))
def test_compile_read_lock_excludes_writers_through_transaction_verification(tmp_path, monkeypatch, phase):
    template = _transaction(tmp_path)
    baseline = store.require_greenfield_working_generation(tmp_path)
    attempts = []
    writes = []

    def partial_writer(_descriptor):
        writes.append(True)
        return 1

    def assert_writer_blocked():
        attempts.append(phase)
        with pytest.raises(writers.GreenfieldManagedMutationBusyError, match="BUSY_NO_WRITE"):
            writers.run_with_greenfield_managed_mutation_boundary(
                repo_root=tmp_path, command_tokens=("casebook", "refresh"), operation=partial_writer,
            )

    original_readiness = store.require_greenfield_working_generation
    original_verify = proposals.require_product_create_transaction_verified

    def readiness(root):
        if phase == "readiness":
            assert_writer_blocked()
        return original_readiness(root)

    def build(**_):
        if phase == "staging":
            assert_writer_blocked()
        return _compiled_result(template)

    def verify(transaction):
        original_verify(transaction)
        if phase == "verification":
            assert_writer_blocked()

    monkeypatch.setattr(store, "require_greenfield_working_generation", readiness)
    monkeypatch.setattr(proposals, "_build_authored_prewrite_package", build)
    monkeypatch.setattr(proposals, "require_product_create_transaction_verified", verify)
    transaction = proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path, proposal=template.proposal, release_selector="0.0.1", proposal_ready=True,
    )
    assert attempts == [phase]
    assert writes == []
    assert transaction.prewrite_package.repository_write_set["before_fingerprints"] == baseline.manifest["after_fingerprints"]
    with locks.greenfield_repository_lock(tmp_path):
        assert kernel.greenfield_managed_fingerprints(tmp_path) == baseline.manifest["after_fingerprints"]


def test_existing_writer_rejects_compile_before_staging(tmp_path, monkeypatch):
    template = _transaction(tmp_path)
    before = kernel.greenfield_managed_fingerprints(tmp_path)
    monkeypatch.setattr(proposals, "_build_authored_prewrite_package", lambda **_: pytest.fail("staged while busy"))
    with locks.greenfield_repository_lock(tmp_path), pytest.raises(locks.GreenfieldRepositoryBusyError, match="BUSY_NO_WRITE"):
        proposals.compile_greenfield_create_transaction(
            repo_root=tmp_path, proposal=template.proposal, release_selector="0.0.1", proposal_ready=True,
        )
    assert kernel.greenfield_managed_fingerprints(tmp_path) == before


def test_compiler_allows_other_readers_and_releases_lock_on_failure(tmp_path, monkeypatch):
    template = _transaction(tmp_path)
    monkeypatch.setattr(proposals, "_build_authored_prewrite_package", lambda **_: _compiled_result(template))
    with locks.greenfield_repository_read_lock(tmp_path):
        transaction = proposals.compile_greenfield_create_transaction(
            repo_root=tmp_path, proposal=template.proposal, release_selector="0.0.1", proposal_ready=True,
        )
    assert transaction.verified

    def failure(**_):
        raise ValueError("deliberate staged-package failure")

    monkeypatch.setattr(proposals, "_build_authored_prewrite_package", failure)
    with pytest.raises(ValueError, match="deliberate staged-package failure"):
        proposals.compile_greenfield_create_transaction(
            repo_root=tmp_path, proposal=template.proposal, release_selector="0.0.1", proposal_ready=True,
        )
    with locks.greenfield_repository_lock(tmp_path):
        assert store.require_greenfield_working_generation(tmp_path)
