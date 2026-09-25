"""Contract proof for the host-native Greenfield candidate boundary."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence.greenfield_authored_relation_validation import (
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
    canonical_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_receipt_approval import (
    greenfield_model_authoring_receipt_approved,
)
from tests.unit.runtime.greenfield_baseline_fixtures import (
    activate_greenfield_baseline_fixture,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    StructuredAuthoringProvider,
    clarification_response,
    structural_design_fixture,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _host_response(evidence: str) -> dict[str, object]:
    response = deepcopy(_response(evidence))
    result = response["result"]
    facts = result["facts"]
    path_citations = facts.pop("first_path")
    for event, citation in zip(result["events"], path_citations, strict=True):
        event["source_citation"] = citation
    response["version"] = HOST_CANDIDATE_FORMAT_VERSION
    return response


def _host_clarification(response: dict[str, object]) -> dict[str, object]:
    candidate = deepcopy(response)
    candidate["version"] = HOST_CANDIDATE_FORMAT_VERSION
    return candidate


def test_host_candidate_uses_shared_validator_reviewer_and_custody(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _host_response(evidence)
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
    response = _host_clarification(clarification_response(
        question="",
        material_dimension="first_path",
        evidence_quotes=(),
    ))

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
        host_candidate=_host_response(evidence),
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
            host_candidate=_host_response(evidence),
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
    assert payload["candidate_version"] == HOST_CANDIDATE_FORMAT_VERSION
    assert payload["candidate_schema"]["additionalProperties"] is False
    authored = payload["candidate_schema"]["properties"]["result"]["anyOf"][0]
    assert "first_path" not in authored["properties"]["facts"]["properties"]
    assert "source_citation" in authored["properties"]["events"]["items"]["required"]
    source_precedence = authored["properties"]["source_precedence"]
    assert "every explicit source-stated ordering requirement" in source_precedence["description"]
    assert "proposed first-run walkthrough" in source_precedence["description"]
    assert any(
        "Use exactly one proof authority" in requirement
        and "facts.proof_boundary and terminal to null" in requirement
        for requirement in payload["requirements"]
    )
    assert payload["request"]["evidence"].endswith(
        "Create one reviewable harbor plan.\n"
    )


def test_host_candidate_preserves_canonical_source_precedence() -> None:
    evidence = combined_prompt_evidence_source(prompt=_source(), edit_evidence="")
    response = _host_response(evidence)
    expected = deepcopy(response["result"]["source_precedence"])

    canonical = canonical_greenfield_host_candidate(response)

    assert canonical["result"]["source_precedence"] == expected


def test_host_candidate_preserves_multiple_events_on_one_exact_source_fact(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _host_response(evidence)
    shared_event = (
        "Dock attendant Ivo enters a vessel tag and the product records berth "
        "occupancy before the berth map shows the placement"
    )
    shared_citation = {
        "quote": shared_event,
        "occurrence": 1,
    }
    for event in response["result"]["events"]:
        event["source_citation"] = deepcopy(shared_citation)

    candidate = materialize_host_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=response,
        review_provider_factory=AdmittingReviewProvider,
    )

    relations = candidate["authored_semantics"]["first_path_relations"]
    assert candidate["first_path"] == shared_event
    assert [row["action_verb_quote"] for row in relations] == [
        "enters",
        "records",
        "shows",
    ]
    assert len(
        {(row["source_start_byte"], row["source_end_byte"]) for row in relations}
    ) == 1
    assert len(
        {(row["event_start_byte"], row["event_end_byte"]) for row in relations}
    ) == 1


def test_host_candidate_rejects_partially_overlapping_event_citations(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _host_response(evidence)
    response["result"]["events"][0]["source_citation"] = {
        "quote": (
            "Dock attendant Ivo enters a vessel tag and the product records berth "
            "occupancy before the berth map shows the placement"
        ),
        "occurrence": 1,
    }

    with pytest.raises(
        GreenfieldModelAuthoringError,
        match="overlapping first-path events",
    ):
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=response,
            review_provider_factory=AdmittingReviewProvider,
        )


def test_host_candidate_rejects_duplicate_event_with_terminal_annotation(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _host_response(evidence)
    response["result"]["events"].append(
        deepcopy(response["result"]["events"][-1])
    )
    response["result"]["terminal"]["event_order"] = 4
    response["result"]["provisional_design"] = structural_design_fixture(
        [1, 2, 3, 4]
    )

    with pytest.raises(
        GreenfieldAuthoredSemanticsError,
        match="invalid first-path relations",
    ):
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=response,
            review_provider_factory=AdmittingReviewProvider,
        )


def test_host_candidate_rejects_shared_human_event_as_component_responsibility(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _host_response(evidence)
    shared_citation = {
        "quote": (
            "Dock attendant Ivo enters a vessel tag and the product records berth "
            "occupancy before the berth map shows the placement"
        ),
        "occurrence": 1,
    }
    for event in response["result"]["events"]:
        event["source_citation"] = deepcopy(shared_citation)
    response["result"]["components"][0]["responsibilities"][0] = {
        "quote": "Dock attendant Ivo enters a vessel tag",
        "occurrence": 1,
    }

    with pytest.raises(
        GreenfieldModelAuthoringError,
        match="non-product event as a component responsibility",
    ):
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=response,
            review_provider_factory=AdmittingReviewProvider,
        )


def test_public_propose_accepts_a_host_candidate_file(
    tmp_path, monkeypatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    activate_greenfield_baseline_fixture(tmp_path)
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    candidate_path = tmp_path / "host-candidate.json"
    candidate_path.write_text(
        json.dumps(_host_response(evidence)),
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


def test_public_propose_exposes_one_typed_candidate_review_denial(
    tmp_path, monkeypatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    activate_greenfield_baseline_fixture(tmp_path)
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    candidate_path = tmp_path / "host-candidate.json"
    candidate_path.write_text(
        json.dumps(_host_response(evidence)),
        encoding="utf-8",
    )
    reviewer = StructuredAuthoringProvider({
        "admissible": False,
        "issues": [{
            "path": "candidate.accepted_source.events[0]",
            "reason": "The selected event assigns the action to the wrong actor.",
        }],
    })

    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (reviewer, "test-reviewer", "medium"),
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

    assert rc == 2
    assert payload["mode"] == "error"
    assert payload["candidate_review"]["status"] == "denied"
    assert payload["candidate_review"]["issue"] == {
        "path": "candidate.accepted_source.events[0]",
        "reason": "The selected event assigns the action to the wrong actor.",
    }


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
            host_candidate=_host_response(initial_evidence),
        )
    )
    correction = "Keep the accepted source facts unchanged and make the review layout accessible."
    edited_evidence = combined_prompt_evidence_source(
        prompt=source,
        edit_evidence=correction,
    )
    candidate_path = tmp_path / "edited-host-candidate.json"
    candidate_path.write_text(
        json.dumps(_host_response(edited_evidence)),
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


def test_host_candidate_projection_moves_event_citations_without_rewriting() -> None:
    evidence = combined_prompt_evidence_source(prompt=_source(), edit_evidence="")
    host = _host_response(evidence)
    frozen = deepcopy(host)

    canonical = canonical_greenfield_host_candidate(host)

    assert host == frozen
    assert canonical["version"] != host["version"]
    assert canonical["result"]["facts"]["first_path"] == [
        event["source_citation"] for event in host["result"]["events"]
    ]
    assert all(
        "source_citation" not in event for event in canonical["result"]["events"]
    )
