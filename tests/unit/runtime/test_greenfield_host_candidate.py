"""Contract proof for the host-native Greenfield candidate boundary."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_model_receipt_approval import (
    greenfield_model_authoring_receipt_approved,
)
from tests.unit.runtime.greenfield_baseline_fixtures import (
    activate_greenfield_baseline_fixture,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    clarification_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def test_host_candidate_uses_shared_validator_reviewer_and_custody(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _response(evidence)
    frozen = deepcopy(response)
    receipt: dict[str, object] = {}

    candidate = materialize_host_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=response,
        review_provider_factory=AdmittingReviewProvider,
        authoring_receipt=receipt,
    )

    assert response == frozen
    assert receipt["authoring_origin"] == "host_native"
    assert receipt["runtime_semantic_model_call_count"] == 1
    assert "participant_selection" not in receipt
    assert "remaining_candidate_authoring" not in receipt
    assert receipt["candidate_review"]["status"] == "admitted"
    assert receipt["candidate_review"]["product_facts_sha256"] == (
        candidate["product_intent_authority"]["product_facts_sha256"]
    )
    observed = candidate["product_intent_authority"]["operating_envelope"][
        "model_contract"
    ]["observed"]
    assert observed["origin"] == "host_native"
    assert observed["host_candidate"] == receipt["host_candidate"]

    manifest_receipt = {
        key: deepcopy(receipt[key])
        for key in (
            "authoring_origin",
            "authoring_version",
            "runtime_semantic_model_call_count",
            "tier",
            "elapsed_seconds",
            "effective_model_window_seconds",
            "host_candidate",
            "candidate_review",
        )
    }
    assert greenfield_model_authoring_receipt_approved(
        model_authoring=manifest_receipt,
        semantic_compiler={
            "version": "odylith.greenfield.authored-semantic-validation.v4",
            "status": "passed",
            "semantic_owner": "validated_model_authored_intent",
            "post_authoring_interpretation_calls": 1,
        },
        requested_repair_tier="standard",
    )


def test_host_candidate_clarification_never_dispatches_review(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = "Draft a product-first greenfield proposal for an assay drift model."
    response = clarification_response(
        question="",
        material_dimension="first_path",
        evidence_quotes=(),
    )

    def forbidden_review() -> object:
        raise AssertionError("clarification must not dispatch candidate review")

    receipt: dict[str, object] = {}
    with pytest.raises(GreenfieldClarificationRequired) as raised:
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=response,
            review_provider_factory=forbidden_review,
            authoring_receipt=receipt,
        )

    assert raised.value.required_fields == ("first_path",)
    assert receipt["runtime_semantic_model_call_count"] == 0
    assert "candidate_review" not in receipt


def test_host_candidate_receipt_fails_closed_when_origin_is_rewritten(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    receipt: dict[str, object] = {}
    materialize_host_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=_response(evidence),
        review_provider_factory=AdmittingReviewProvider,
        authoring_receipt=receipt,
    )
    manifest_receipt = {
        key: deepcopy(receipt[key])
        for key in (
            "authoring_origin",
            "authoring_version",
            "runtime_semantic_model_call_count",
            "tier",
            "elapsed_seconds",
            "effective_model_window_seconds",
            "host_candidate",
            "candidate_review",
        )
    }
    manifest_receipt["authoring_origin"] = "participant_first"

    assert not greenfield_model_authoring_receipt_approved(
        model_authoring=manifest_receipt,
        semantic_compiler={
            "version": "odylith.greenfield.authored-semantic-validation.v4",
            "status": "passed",
            "semantic_owner": "validated_model_authored_intent",
            "post_authoring_interpretation_calls": 1,
        },
        requested_repair_tier="standard",
    )


def test_host_candidate_compiles_the_existing_transaction_without_runtime_authoring(
    tmp_path, monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    activate_greenfield_baseline_fixture(tmp_path)
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    reviewer = AdmittingReviewProvider()
    requested_roles: list[str] = []

    def provider_factory(**kwargs: object) -> tuple[object, str, str]:
        role = str(kwargs.get("request_role") or "")
        requested_roles.append(role)
        if role != "candidate_review":
            raise AssertionError(f"unexpected runtime authoring role: {role}")
        return reviewer, "test-reviewer", "medium"

    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        provider_factory,
    )
    candidate, transaction, transaction_path = (
        greenfield_proposals_cli._compile_prompt_evidence_transaction(
            repo_root=tmp_path,
            prompt=source,
            edit_evidence="",
            release_selector="",
            host_candidate=_response(evidence),
        )
    )

    assert requested_roles == ["candidate_review"]
    assert reviewer.calls == 1
    assert candidate["title"] == "Harbor Desk"
    assert transaction.quality_manifest["model_authoring"]["authoring_origin"] == (
        "host_native"
    )
    assert transaction.quality_manifest["status"] == "passed"
    assert transaction_path.is_file()


def test_candidate_contract_is_provider_free_and_supplies_the_canonical_schema(
    tmp_path, monkeypatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("candidate contract must not discover a provider")
        ),
    )
    rc = greenfield_proposals_cli.main([
        "candidate-contract",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        "Create one reviewable harbor plan.",
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["version"] == HOST_CANDIDATE_CONTRACT_VERSION
    assert payload["candidate_schema"]["additionalProperties"] is False
    assert payload["request"]["evidence"].endswith(
        "Create one reviewable harbor plan.\n"
    )


def test_public_propose_accepts_a_host_candidate_file(
    tmp_path, monkeypatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    activate_greenfield_baseline_fixture(tmp_path)
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    candidate_path = tmp_path / "host-candidate.json"
    candidate_path.write_text(
        json.dumps(_response(evidence)),
        encoding="utf-8",
    )
    reviewer = AdmittingReviewProvider()

    def provider_factory(**kwargs: object) -> tuple[object, str, str]:
        assert kwargs.get("request_role") == "candidate_review"
        return reviewer, "test-reviewer", "medium"

    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        provider_factory,
    )
    rc = greenfield_proposals_cli.main([
        "propose",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        source,
        "--candidate-file",
        str(candidate_path),
        "--format",
        "json",
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0, payload
    assert payload["mode"] == "product_create_transaction"
    assert payload["intent_hypothesis"]["title"] == "Harbor Desk"
    assert reviewer.calls == 1


def test_edit_rebuild_accepts_a_new_host_candidate_and_preserves_old_seal(
    tmp_path, monkeypatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    activate_greenfield_baseline_fixture(tmp_path)
    source = _source()
    initial_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    reviewer = AdmittingReviewProvider()
    requested_roles: list[str] = []

    def provider_factory(**kwargs: object) -> tuple[object, str, str]:
        role = str(kwargs.get("request_role") or "")
        requested_roles.append(role)
        assert role == "candidate_review"
        return reviewer, "test-reviewer", "medium"

    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        provider_factory,
    )
    _candidate, original, original_path = (
        greenfield_proposals_cli._compile_prompt_evidence_transaction(
            repo_root=tmp_path,
            prompt=source,
            edit_evidence="",
            release_selector="",
            host_candidate=_response(initial_evidence),
        )
    )
    correction = "Keep the accepted source facts unchanged and make the review layout accessible."
    edited_evidence = combined_prompt_evidence_source(
        prompt=source,
        edit_evidence=correction,
    )
    candidate_path = tmp_path / "edited-host-candidate.json"
    candidate_path.write_text(
        json.dumps(_response(edited_evidence)),
        encoding="utf-8",
    )

    rc = greenfield_proposals_cli.rebuild_pending_transaction(
        repo_root=tmp_path,
        transaction_hash=original.transaction_hash,
        edit_evidence=correction,
        edit_evidence_file="",
        as_json=True,
        host_candidate_file=str(candidate_path),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0, payload
    assert payload["mode"] == "product_create_transaction"
    assert payload["product_create_transaction"]["transaction_hash"] != (
        original.transaction_hash
    )
    assert original_path.is_file()
    assert requested_roles == ["candidate_review", "candidate_review"]
