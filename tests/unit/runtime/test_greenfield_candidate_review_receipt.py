"""Three-call participant-first receipts survive sealing and bind final review."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_transaction as transactions
from odylith.runtime.domain_intelligence import greenfield_commit_transaction as commits
from odylith.runtime.domain_intelligence import greenfield_preconfirm_engine as engine
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from tests.unit.runtime.greenfield_authored_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
    approved_authored_quality_manifest_fixture,
)
from tests.unit.runtime.greenfield_proposal_fixtures import (
    compiled_greenfield_package_fixture,
)


def test_three_call_receipt_passes_quality_only_gate() -> None:
    transactions.require_product_create_transaction_quality_approved(
        approved_authored_quality_manifest_fixture(), authored_projection_verified=True,
    )


@pytest.mark.parametrize("role", ["participant", "author", "review", "all"])
def test_old_receipt_is_not_reinterpreted_under_the_shared_model_window(role) -> None:
    manifest = approved_authored_quality_manifest_fixture()
    receipt = manifest["model_authoring"]
    old_profile = "greenfield-standard-terra-low-complete-author-review-v14"
    if role in {"participant", "all"}:
        receipt["participant_selection"]["model_profile"]["profile_id"] = old_profile
    if role in {"author", "all"}:
        receipt["remaining_candidate_authoring"]["model_profile"]["profile_id"] = old_profile
    if role in {"review", "all"}:
        receipt["candidate_review"]["model_profile"]["profile_id"] = old_profile
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


def test_author_elapsed_cannot_exceed_its_own_recorded_dispatch_cap() -> None:
    manifest = approved_authored_quality_manifest_fixture(elapsed_seconds=4.0)
    receipt = manifest["model_authoring"]
    receipt["remaining_candidate_authoring"]["model_profile"]["effective_timeout_seconds"] = 1.0
    receipt["remaining_candidate_authoring"]["elapsed_seconds"] = 2.0
    receipt["candidate_review"]["elapsed_seconds"] = 0.25
    receipt["elapsed_seconds"] = 3.0
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


def test_review_dispatch_window_cannot_exceed_remaining_shared_window() -> None:
    manifest = approved_authored_quality_manifest_fixture()
    receipt = manifest["model_authoring"]
    receipt["participant_selection"]["elapsed_seconds"] = 20.0
    receipt["remaining_candidate_authoring"]["elapsed_seconds"] = 30.0
    receipt["candidate_review"]["model_profile"]["effective_timeout_seconds"] = 115.001
    receipt["candidate_review"]["elapsed_seconds"] = 1.0
    receipt["elapsed_seconds"] = 51.0
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("model_authoring", "semantic_model_call_count"), value) for value in (0, 1, 2, True, 3.0)
    ] + [
        (("semantic_compiler", "version"), "odylith.greenfield.authored-semantic-validation.v3"),
        (("semantic_compiler", "post_authoring_interpretation_calls"), 0),
        (("semantic_compiler", "post_authoring_interpretation_calls"), True),
        (("model_authoring", "candidate_review"), None),
        (("model_authoring", "candidate_review", "version"), "old"),
        (("model_authoring", "candidate_review", "status"), "denied"),
        (("model_authoring", "candidate_review", "status"), "repair_before_preview"),
        (("model_authoring", "candidate_review", "unexpected"), True),
        (("model_authoring", "candidate_review", "model_profile", "model"), "gpt-5.6-terra"),
        (("model_authoring", "candidate_review", "model_profile", "reasoning_effort"), "low"),
        (("model_authoring", "candidate_review", "model_profile", "authoring_tier"), "deep"),
        (("model_authoring", "candidate_review", "model_profile", "provider"), "unobserved"),
        (("model_authoring", "candidate_review", "model_profile", "request_role"), "initial_authoring"),
        (("model_authoring", "candidate_review", "model_profile", "effective_timeout_seconds"), 165.001),
        (("model_authoring", "participant_selection", "model_profile", "model"), "gpt-5.6-terra"),
        (("model_authoring", "participant_selection", "model_profile", "profile_id"),
         "greenfield-rescue-participant-first-luna-medium-v19"),
        (("model_authoring", "remaining_candidate_authoring", "model_profile", "model"), "gpt-5.6-terra"),
        (("model_authoring", "remaining_candidate_authoring", "model_profile", "request_role"),
         "remaining_candidate_authoring"),
        (("model_authoring", "participant_selection", "elapsed_seconds"), 55.0),
        (("model_authoring", "elapsed_seconds"), 165.001),
        (("model_authoring", "candidate_review", "elapsed_seconds"), 165.001),
        (("model_authoring", "candidate_review", "elapsed_seconds"), -0.001),
    ] + [
        (("model_authoring", "candidate_review", field), value)
        for field in ("source_sha256", "candidate_sha256", "product_facts_sha256")
        for value in (None, "a" * 63, "g" * 64, "A" * 64)
    ] + [
        (path, value)
        for path in (
            ("elapsed_seconds",), ("target_seconds",), ("operational_timeout_seconds",),
            ("model_authoring", "elapsed_seconds"),
            ("model_authoring", "effective_model_window_seconds"),
            ("model_authoring", "participant_selection", "elapsed_seconds"),
            ("model_authoring", "remaining_candidate_authoring", "elapsed_seconds"),
            ("model_authoring", "candidate_review", "elapsed_seconds"),
            ("model_authoring", "candidate_review", "model_profile", "effective_timeout_seconds"),
            ("model_authoring", "participant_selection", "model_profile", "effective_timeout_seconds"),
            ("model_authoring", "remaining_candidate_authoring", "model_profile", "effective_timeout_seconds"),
        )
        for value in (True, float("nan"), float("inf"), "0.1", 10 ** 1000)
    ],
)
def test_receipt_rejects_malformed_or_unqualified_observations(path: tuple[str, ...], value: object) -> None:
    manifest = approved_authored_quality_manifest_fixture()
    target = manifest
    for key in path[:-1]:
        target = target[key]
    original = target.get(path[-1])
    assert type(original) is not type(value) or original != value
    target[path[-1]] = value
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(
            manifest, authored_projection_verified=True,
        )


@pytest.mark.parametrize("key", [
    "participant_selection", "remaining_candidate_authoring", "candidate_review",
    "effective_model_window_seconds",
])
def test_receipt_requires_all_role_observations(key: str) -> None:
    manifest = approved_authored_quality_manifest_fixture()
    manifest["model_authoring"].pop(key)
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


def test_stage_elapsed_sum_cannot_exceed_total_shared_elapsed() -> None:
    manifest = approved_authored_quality_manifest_fixture()
    receipt = manifest["model_authoring"]
    receipt["participant_selection"]["elapsed_seconds"] = 1.0
    receipt["remaining_candidate_authoring"]["elapsed_seconds"] = 1.0
    receipt["candidate_review"]["elapsed_seconds"] = 1.0
    receipt["elapsed_seconds"] = 2.999
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


def test_author_dispatch_window_cannot_ignore_selector_time() -> None:
    manifest = approved_authored_quality_manifest_fixture()
    receipt = manifest["model_authoring"]
    receipt["participant_selection"]["elapsed_seconds"] = 10.0
    receipt["remaining_candidate_authoring"]["model_profile"][
        "effective_timeout_seconds"
    ] = 155.001
    receipt["elapsed_seconds"] = 11.0
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


def test_manifest_preserves_review_without_aliasing_mutable_input() -> None:
    receipt = approved_authored_quality_manifest_fixture()["model_authoring"]
    receipt["consistency_assessment"] = {"status": "consistent", "source_spans": []}
    result = engine.build_greenfield_preconfirm_manifest(
        report=engine.GreenfieldCompletionReport(
            status="passed", version="test", semantic_model=True,
            artifact_counts={}, tribunal_status="passed", issues=(),
        ),
        status="passed", stop_reason="passed", elapsed_seconds=1.0,
        pass_records=(), target_seconds=90.0, operational_timeout_seconds=180.0,
        model_authoring_receipt=receipt,
    )
    expected = deepcopy(receipt)
    expected.pop("consistency_assessment")
    assert result["model_authoring"] == expected
    receipt["candidate_review"]["model_profile"]["model"] = "changed"
    receipt["participant_selection"]["model_profile"]["model"] = "changed"
    assert result["model_authoring"]["candidate_review"]["model_profile"]["model"] == "gpt-6-astra"
    assert result["model_authoring"]["participant_selection"]["model_profile"]["model"] == "gpt-6-astra"


@pytest.fixture
def compiled_transaction(tmp_path: Path):
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    authority = proposal[PRODUCT_INTENT_AUTHORITY_KEY]
    package = compiled_greenfield_package_fixture(proposal, repo_root=tmp_path)
    return transactions.build_product_create_transaction(
        proposal=proposal, release_selector="0.0.1", validation_gate={"status": "passed"},
        prewrite_package=package, backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=approved_authored_quality_manifest_fixture(intent_authority=authority),
        repo_root=tmp_path,
    )


def test_serialized_receipt_keeps_all_timing_and_requires_no_model_on_readback(
    compiled_transaction, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from odylith.runtime.domain_intelligence import greenfield_participant_first_authoring as author

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Receipt verification must not call a model")

    monkeypatch.setattr(author, "author_greenfield_intent", forbidden)
    payload = transactions.product_create_transaction_to_dict(compiled_transaction)
    assert payload["quality_manifest"] == compiled_transaction.quality_manifest
    restored = transactions.product_create_transaction_from_dict(payload)
    assert restored.quality_manifest == compiled_transaction.quality_manifest
    target = tmp_path / "transaction.json"
    transactions.write_compiled_product_create_transaction_file(target, compiled_transaction)
    admitted = transactions.load_compiled_product_create_transaction_file(target)
    assert admitted.verified
    assert admitted.quality_manifest == compiled_transaction.quality_manifest
    committed = commits.load_sealed_product_create_commit(target)
    assert committed.verified
    assert committed.commit_manifest_preview == compiled_transaction.quality_manifest


@pytest.mark.parametrize("field", ["source_sha256", "product_facts_sha256"])
def test_replayed_review_fails_even_with_recomputed_transaction_hash(
    compiled_transaction, tmp_path: Path, field: str,
) -> None:
    manifest = deepcopy(compiled_transaction.quality_manifest)
    manifest["model_authoring"]["candidate_review"][field] = "0" * 64
    transactions.require_product_create_transaction_quality_approved(manifest)
    with pytest.raises(ValueError, match="candidate review does not match"):
        transactions.build_product_create_transaction(
            proposal=compiled_transaction.proposal, release_selector="0.0.1",
            validation_gate=compiled_transaction.validation_gate,
            prewrite_package=compiled_transaction.prewrite_package,
            backlog_result=compiled_transaction.backlog_result,
            intent_authority=compiled_transaction.intent_authority,
            quality_manifest=manifest, repo_root=tmp_path,
        )
    replayed = replace(compiled_transaction, quality_manifest=manifest)
    replayed = replace(replayed, transaction_hash=transactions.product_create_transaction_hash(replayed))
    assert not replayed.verified
    with pytest.raises(ValueError, match="candidate review does not match"):
        transactions.require_product_create_transaction_verified(replayed)
    with pytest.raises(ValueError, match="candidate review does not match"):
        transactions.product_create_transaction_from_dict(transactions.product_create_transaction_to_dict(replayed))


def test_missing_review_rejected_after_rehash_not_only_during_build(compiled_transaction) -> None:
    manifest = deepcopy(compiled_transaction.quality_manifest)
    manifest["model_authoring"].pop("candidate_review")
    changed = replace(compiled_transaction, quality_manifest=manifest)
    changed = replace(changed, transaction_hash=transactions.product_create_transaction_hash(changed))
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_verified(changed)


def test_timing_observation_is_sealed_not_volatile(compiled_transaction) -> None:
    manifest = deepcopy(compiled_transaction.quality_manifest)
    manifest["model_authoring"]["candidate_review"]["elapsed_seconds"] += 0.01
    changed = replace(compiled_transaction, quality_manifest=manifest)
    compiler_hash = transactions.product_create_transaction_hash(changed)
    assert compiler_hash != compiled_transaction.transaction_hash
    assert commits._payload_hash(transactions.product_create_transaction_to_dict(changed)) == compiler_hash


def test_final_consumer_clock_keeps_transaction_identity_and_persists(compiled_transaction) -> None:
    manifest = deepcopy(compiled_transaction.quality_manifest)
    manifest["elapsed_seconds"] = 59.0
    staged = replace(compiled_transaction, quality_manifest=manifest)
    assert transactions.product_create_transaction_hash(staged) == compiled_transaction.transaction_hash
    assert commits._payload_hash(transactions.product_create_transaction_to_dict(staged)) == compiled_transaction.transaction_hash
    transactions.require_product_create_transaction_verified(staged)
    payload = transactions.product_create_transaction_to_dict(staged)
    assert payload["quality_manifest"]["elapsed_seconds"] == 59.0
    assert transactions.product_create_transaction_from_dict(payload).quality_manifest == manifest


def test_role_elapsed_cannot_exceed_its_actual_dispatch_timeout() -> None:
    manifest = approved_authored_quality_manifest_fixture()
    receipt = manifest["model_authoring"]
    receipt["participant_selection"]["elapsed_seconds"] = 10.0
    receipt["remaining_candidate_authoring"]["elapsed_seconds"] = 20.0
    receipt["elapsed_seconds"] = 56.0
    receipt["candidate_review"]["elapsed_seconds"] = 25.0
    receipt["candidate_review"]["model_profile"]["effective_timeout_seconds"] = 24.5
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)
