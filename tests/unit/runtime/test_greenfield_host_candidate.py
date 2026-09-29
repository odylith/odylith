"""Contract proof for the host-native Greenfield candidate boundary."""

from __future__ import annotations

import json
import os
from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence import (
    greenfield_host_candidate_materialization,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    admit_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_review_custody import (
    candidate_review_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    PRODUCT_STORY_ROLE_DEFINITION,
    REFERENCE_PROVENANCE_ROLE_CONTRACT,
    REVIEW_PROMPT,
)
from odylith.runtime.domain_intelligence.greenfield_event_ordering import (
    validate_source_precedence,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_proof_observation import (
    GREENFIELD_MODEL_PROOF_FD_ENV,
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
    admitted_review_response,
    clarification_response,
    host_candidate_response,
    structural_design_fixture,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _host_response(evidence: str) -> dict[str, object]:
    return host_candidate_response(_response(evidence), evidence_text=evidence)


def _host_clarification(response: dict[str, object]) -> dict[str, object]:
    candidate = deepcopy(response)
    candidate["version"] = HOST_CANDIDATE_FORMAT_VERSION
    return candidate


def _base_component_custody() -> dict[str, object]:
    return {
        "event_responsibilities": [
            {
                "event_order": 2,
                "responsibility_citation": {
                    "quote": "the product records berth occupancy",
                    "occurrence": 1,
                },
            },
            {
                "event_order": 3,
                "responsibility_citation": {
                    "quote": "the berth map shows the placement",
                    "occurrence": 1,
                },
            },
        ],
        "additional_responsibilities": [
            {
                "owner_fact": {"field": "internal_systems", "row": 1},
                "responsibility_citation": {
                    "quote": "Record berth occupancy",
                    "occurrence": 1,
                },
            }
        ],
    }


def test_host_candidate_uses_shared_validator_reviewer_and_custody(
    tmp_path, monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _host_response(evidence)
    frozen = deepcopy(response)
    receipt: dict[str, object] = {}

    proof_path = tmp_path / "host-reviewer-admitted-proof.json"
    descriptor = os.open(proof_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(descriptor))
    try:
        candidate = materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=response,
            review_provider_factory=AdmittingReviewProvider,
            authoring_receipt=receipt,
        )
    finally:
        os.close(descriptor)

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
    retained = json.loads(proof_path.read_text(encoding="utf-8"))
    assert retained["origin"] == "host_native"
    assert retained["host_candidate"] == receipt["host_candidate"]
    assert retained["candidate_review"]["status"] == "admitted"
    assert retained["candidate_review"]["admission_witness"] == receipt[
        "candidate_review"
    ]["admission_witness"]

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


def test_reviewer_input_hash_matches_unprojected_candidate_and_changes_with_input() -> None:
    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _host_response(evidence)
    authored, _receipt = admit_greenfield_host_candidate(
        response,
        evidence_text=evidence,
        review_provider_factory=AdmittingReviewProvider,
    )

    canonical = canonical_greenfield_host_candidate(response, evidence_text=evidence)
    expected = candidate_review_sha256(canonical["result"])
    review = getattr(authored, "candidate_review", {})
    assert review["review_input_candidate_sha256"] == expected
    assert len(review["candidate_sha256"]) == 64

    mutated = deepcopy(response)
    mutated["result"]["provisional_design"]["first_run"]["rationale"] += (
        " Keep the decision provisional."
    )
    mutated_canonical = canonical_greenfield_host_candidate(mutated, evidence_text=evidence)
    assert candidate_review_sha256(mutated_canonical["result"]) != expected


def test_host_candidate_clarification_never_dispatches_review(
    tmp_path, monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    source = "Draft a product-first greenfield proposal for an assay drift model."
    response = _host_clarification(clarification_response(
        question="",
        material_dimension="first_path",
        evidence_quotes=(),
    ))

    def forbidden_review() -> object:
        raise AssertionError("clarification must not dispatch candidate review")

    receipt: dict[str, object] = {}
    proof_path = tmp_path / "direct-host-clarification-proof.json"
    descriptor = os.open(proof_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(descriptor))
    try:
        with pytest.raises(GreenfieldClarificationRequired) as raised:
            materialize_host_authored_intent(
                prompt=source,
                repo_root=tmp_path,
                host_candidate=response,
                review_provider_factory=forbidden_review,
                authoring_receipt=receipt,
            )
    finally:
        os.close(descriptor)

    assert raised.value.required_fields == ("first_path",)
    assert raised.value.question == (
        "Who uses this product first, what complete task do they finish, and what result do they see?"
    )
    assert receipt["runtime_semantic_model_call_count"] == 0
    assert "candidate_review" not in receipt
    assert "basis" not in receipt["consistency_assessment"]
    assert proof_path.read_bytes() == b""


def test_reviewer_source_insufficiency_becomes_a_bound_first_path_question(
    tmp_path, monkeypatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    """A civic-style first-path gap stops before any candidate can be staged."""

    source = _source()
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    reviewer = StructuredAuthoringProvider({
        "outcome": "clarification_required",
        "issue": None,
        "clarification": {"material_dimension": "first_path"},
        "admission_witness": None,
    })

    def forbidden_stage(**_kwargs: object) -> object:
        raise AssertionError("reviewer clarification must stop before staging")

    monkeypatch.setattr(
        greenfield_host_candidate_materialization,
        "stage_validated_authored_intent",
        forbidden_stage,
    )
    receipt: dict[str, object] = {}
    proof_path = tmp_path / "host-reviewer-clarification-proof.json"
    descriptor = os.open(proof_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(descriptor))
    try:
        with pytest.raises(GreenfieldClarificationRequired) as raised:
            materialize_host_authored_intent(
                prompt=source,
                repo_root=tmp_path,
                host_candidate=_host_response(evidence),
                review_provider_factory=lambda: reviewer,
                authoring_receipt=receipt,
            )
    finally:
        os.close(descriptor)

    assert raised.value.required_fields == ("first_path",)
    assert receipt["candidate_review"]["status"] == "clarification_required"
    assert receipt["candidate_review"]["source_sha256"] == receipt["host_candidate"]["source_sha256"]
    assert len(receipt["candidate_review"]["review_input_candidate_sha256"]) == 64
    assert "candidate_sha256" not in receipt["candidate_review"]
    assert receipt["consistency_assessment"] == {
        "status": "material_ambiguity",
        "source_spans": [],
        "basis": "complete_source_missingness",
    }
    retained = json.loads(proof_path.read_text(encoding="utf-8"))
    assert retained["origin"] == "host_native"
    assert retained["host_candidate"] == receipt["host_candidate"]
    assert retained["candidate_review"] == receipt["candidate_review"]
    assert set(retained["candidate_review"]) == {
        "version", "status", "source_sha256", "review_input_candidate_sha256",
        "model_profile", "elapsed_seconds", "clarification",
    }
    greenfield_proposals_cli._print_greenfield_clarification(
        raised.value,
        as_json=True,
    )
    public = json.loads(capsys.readouterr().out)
    assert set(public) == {"mode", "clarification"}
    assert public["clarification"]["consistency_assessment"] == receipt[
        "consistency_assessment"
    ]
    assert public["clarification"]["question"] == raised.value.question
    assert public["clarification"]["required_fields"] == ["first_path"]
    assert "candidate_review" not in public["clarification"]
    assert reviewer.calls == 1


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
        "_greenfield_review_provider",
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
        "_greenfield_review_provider",
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
    assert payload["version"] == "odylith.greenfield.host-candidate-contract.v30"
    assert payload["candidate_version"] == "odylith.greenfield.host-candidate-format.v16"
    assert any(
        "exact scope_paths" in requirement
        and "Odylith derives" in requirement
        for requirement in payload["requirements"]
    )
    assert any(
        "distinct exact contiguous source_citation" in requirement
        and "never reuse or partially overlap event citations" in requirement
        for requirement in payload["requirements"]
    )
    assert any(
        "supplied source evidence" in requirement
        and "inputs to this authoring transaction" in requirement
        and "do not cite, restate or paraphrase them" in requirement
        and "manages evidence, provenance or source identity as domain data" in requirement
        for requirement in payload["requirements"]
    )
    assert any(
        "complete requested workflow" in requirement
        and "remains the product-intent authority" in requirement
        and "reference provenance" in requirement
        and "not a competing product boundary" in requirement
        and "explicitly assigns that reference" in requirement
        and "inside-versus-outside responsibility" in requirement
        and "cannot safely remain an explicit assumption" in requirement
        and "workflow need not be incomplete" in requirement
        for requirement in payload["requirements"]
    )
    assert REFERENCE_PROVENANCE_ROLE_CONTRACT in payload["requirements"]
    assert any(
        "complete source action owned by its actor" in requirement
        and "full joined action phrase" in requirement
        and "only one branch verb" in requirement
        and "truncated branch action is not admissible" in requirement
        for requirement in payload["requirements"]
    )
    assert any(
        "facts.operational_constraints" in requirement
        and "independent reviewer owns" in requirement
        for requirement in payload["requirements"]
    )
    assert payload["candidate_schema"]["additionalProperties"] is False
    authored = payload["candidate_schema"]["properties"]["result"]["anyOf"][0]
    assert "components" not in authored["required"]
    assert "components" not in authored["properties"]
    risk_item = authored["properties"]["provisional_design"]["properties"][
        "risk_posture"
    ]["properties"]["items"]["items"]
    assert set(risk_item["properties"]) == {
        "key", "category", "statement", "trigger", "mitigation", "verification",
        "scope_paths",
    }
    assert (
        authored["properties"]["facts"]["properties"]["product_story"][
            "description"
        ]
        == PRODUCT_STORY_ROLE_DEFINITION
    )
    assert "first_path" not in authored["properties"]["facts"]["properties"]
    assert "source_citation" in authored["properties"]["events"]["items"]["required"]
    source_citation = authored["properties"]["events"]["items"]["properties"][
        "source_citation"
    ]
    assert source_citation["required"] == ["quote", "context"]
    assert source_citation["properties"]["context"]["type"] == "string"
    assert "occurrence" not in source_citation["properties"]
    assert "responsibility_citation" not in authored["properties"]["events"]["items"][
        "properties"
    ]
    action_quote = authored["properties"]["events"]["items"]["properties"][
        "action_quote"
    ]
    assert "complete joined action" in action_quote["description"]
    assert "do not reduce that disjunctive action" in action_quote["description"]
    provisional_component = authored["properties"]["provisional_design"]["properties"][
        "components"
    ]["items"]["properties"]
    assert "cover every source event" in provisional_component[
        "supported_event_orders"
    ]["description"]
    first_run_orders = authored["properties"]["provisional_design"]["properties"][
        "first_run"
    ]["properties"]["event_orders"]
    assert "one coherent proposed walkthrough" in first_run_orders["description"].lower()
    assert "mutually exclusive outcomes" in first_run_orders["description"]
    assert "remain retained and component-supported" in first_run_orders["description"]
    assert any(
        "including human actions" in requirement
        for requirement in payload["requirements"]
    )
    pending = [("$", payload["candidate_schema"])]
    while pending:
        path, value = pending.pop()
        if isinstance(value, dict):
            properties = value.get("properties")
            if value.get("type") == "object" and isinstance(properties, dict):
                assert set(value.get("required", ())) == set(properties), path
            pending.extend((f"{path}.{key}", child) for key, child in value.items())
        elif isinstance(value, list):
            pending.extend((f"{path}[{index}]", child) for index, child in enumerate(value))
    source_precedence = authored["properties"]["source_precedence"]
    assert "every explicit source-stated ordering requirement" in source_precedence["description"]
    assert "proposed first-run walkthrough" in source_precedence["description"]
    constraint_item = authored["properties"]["facts"]["properties"][
        "operational_constraints"
    ]["items"]
    assert constraint_item["required"] == ["quote", "context"]
    assert set(constraint_item["properties"]) == {"quote", "context"}
    assert any(
        "Use exactly one proof authority" in requirement
        and "cannot make an authored candidate admission-ready" in requirement
        for requirement in payload["requirements"]
    )
    assert any(
        "source-supported participant, beneficiary" in requirement
        and "explicit product/system task owner" in requirement
        and "source-supported terminal result event" in requirement
        and "authoring deliverable as contextual" in requirement
        and "direct workflow actor outranks a broader authoring audience" in requirement
        and "clarification_required for first_path" in requirement
        for requirement in payload["requirements"]
    )
    participant_role = authored["properties"]["facts"]["properties"][
        "human_actors"
    ]["description"]
    assert "audience for a request, brief, report, proposal" in participant_role
    assert "separately states that it uses, benefits from, participates in" in participant_role
    assert "direct workflow names its actor" in participant_role
    assert any(
        "copy quote and locator context byte-for-byte" in requirement
        and "never normalize or rewrite either value" in requirement
        and "When the quote occurs once, repeat the quote as context" in requirement
        for requirement in payload["requirements"]
    )
    assert any(
        "independent reviewer owns all accepted component-responsibility custody"
        in requirement
        for requirement in payload["requirements"]
    )
    assert payload["request"]["evidence"].endswith(
        "Create one reviewable harbor plan.\n"
    )


@pytest.mark.parametrize("command", ("propose", "compile-transaction"))
def test_public_authoring_help_requires_the_returned_candidate_schema(
    command: str,
    capsys,
) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(SystemExit) as raised:
        greenfield_proposals_cli.main([command, "--help"])

    output = " ".join(capsys.readouterr().out.split())
    assert raised.value.code == 0
    assert "--candidate-file CANDIDATE_FILE" in output
    assert "matching the returned candidate-contract schema" in output
    assert "v68 typed candidate" not in output


@pytest.mark.parametrize("command", ("propose", "compile-transaction"))
def test_public_authoring_rejects_missing_candidate_before_provider_dispatch(
    command: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_review_provider",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("missing candidate reached provider dispatch")
        ),
    )

    with pytest.raises(SystemExit) as raised:
        greenfield_proposals_cli.main(
            [command, "--repo-root", ".", "--prompt", "Create one product."]
        )

    assert raised.value.code == 2


def test_host_candidate_preserves_canonical_source_precedence() -> None:
    old_source = _source()
    old_constraint = "Retain source notes for seven years"
    ordering_constraint = "The vessel-tag entry must precede berth-occupancy recording"
    source = old_source.replace(old_constraint, ordering_constraint)
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = deepcopy(_response(old_source))
    response["result"]["facts"]["operational_constraints"][0] = {
        "quote": ordering_constraint,
        "occurrence": 1,
    }
    response["result"]["source_precedence"] = [
        {"before_event": 1, "after_event": 2, "constraint_index": 1}
    ]
    response = host_candidate_response(response, evidence_text=evidence)
    expected = deepcopy(response["result"]["source_precedence"])

    canonical = canonical_greenfield_host_candidate(response, evidence_text=evidence)

    assert canonical["result"]["source_precedence"] == expected
    assert "components" not in canonical["result"]


def test_host_candidate_preserves_duplicate_precedence_for_validator_rejection() -> None:
    old_source = _source()
    old_constraint = "Retain source notes for seven years"
    ordering_constraint = "The vessel-tag entry must precede berth-occupancy recording"
    source = old_source.replace(old_constraint, ordering_constraint)
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = deepcopy(_response(old_source))
    response["result"]["facts"]["operational_constraints"][0] = {
        "quote": ordering_constraint,
        "occurrence": 1,
    }
    binding = {"before_event": 1, "after_event": 2, "constraint_index": 1}
    response["result"]["source_precedence"] = [
        binding,
        deepcopy(binding),
    ]
    response = host_candidate_response(response, evidence_text=evidence)

    canonical = canonical_greenfield_host_candidate(response, evidence_text=evidence)

    assert canonical["result"]["source_precedence"] == [
        binding,
        binding,
    ]
    with pytest.raises(ValueError, match="duplicate binding"):
        validate_source_precedence(
            canonical["result"]["source_precedence"],
            event_orders=(1, 2),
            operational_constraints=("Review before publish.",),
        )


def test_host_candidate_rejects_reused_event_citation_across_actor_owners() -> None:
    evidence = combined_prompt_evidence_source(prompt=_source(), edit_evidence="")
    response = _host_response(evidence)
    shared_event = (
        "Dock attendant Ivo enters a vessel tag and the product records berth "
        "occupancy before the berth map shows the placement"
    )
    shared_citation = {"quote": shared_event, "context": shared_event}
    for event in response["result"]["events"]:
        event["source_citation"] = deepcopy(shared_citation)

    with pytest.raises(ValueError, match="distinct non-overlapping source citations"):
        canonical_greenfield_host_candidate(response, evidence_text=evidence)


def test_host_candidate_rejects_reused_event_citation_for_one_actor() -> None:
    evidence = combined_prompt_evidence_source(prompt=_source(), edit_evidence="")
    response = _host_response(evidence)
    shared_event = (
        "the product records berth occupancy before the berth map shows the placement"
    )
    shared_citation = {"quote": shared_event, "context": shared_event}
    response["result"]["events"][1]["source_citation"] = deepcopy(shared_citation)
    response["result"]["events"][2]["source_citation"] = deepcopy(shared_citation)

    with pytest.raises(ValueError, match="distinct non-overlapping source citations"):
        canonical_greenfield_host_candidate(response, evidence_text=evidence)


def test_host_candidate_rejects_superseded_component_and_event_custody_fields() -> None:
    evidence = combined_prompt_evidence_source(prompt=_source(), edit_evidence="")
    response = _host_response(evidence)
    response["result"]["components"] = []

    with pytest.raises(ValueError, match="invalid shape"):
        canonical_greenfield_host_candidate(response, evidence_text=evidence)

    response = _host_response(evidence)
    response["result"]["events"][0]["responsibility_citation"] = None
    with pytest.raises(ValueError, match="event has invalid fields"):
        canonical_greenfield_host_candidate(response, evidence_text=evidence)


def test_reviewer_projects_product_constraint_from_global_host_fact() -> None:
    old_source = _source()
    old_constraint = "Retain source notes for seven years"
    product_constraint = "Harbor Desk keeps draft evidence private until publication"
    evidence = combined_prompt_evidence_source(
        prompt=old_source.replace(old_constraint, product_constraint),
        edit_evidence="",
    )
    response = deepcopy(_response(old_source))
    result = response["result"]
    facts = result["facts"]
    facts["operational_constraints"][0] = {
        "quote": product_constraint,
        "occurrence": 1,
    }
    candidate = host_candidate_response(response, evidence_text=evidence)
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=evidence)
    authored, _receipt = admit_greenfield_host_candidate(
        candidate,
        evidence_text=evidence,
        review_provider_factory=lambda: StructuredAuthoringProvider(
            admitted_review_response(
                component_custody=_base_component_custody(),
                constraint_custody=[{
                    "constraint_index": 1,
                    "kind": "product_owned",
                    "owner_fact": {"field": "title", "row": 1},
                }]
            )
        ),
    )

    constraints = canonical["result"]["facts"]["operational_constraints"]
    assert [row["quote"] for row in constraints] == [product_constraint]
    assert "components" not in canonical["result"]
    assert sum(
        row["responsibility_quote"] == product_constraint
        for row in authored.component_responsibility_relations
    ) == 1


def test_reviewer_preserves_one_clause_as_event_and_constraint_custody() -> None:
    evidence = combined_prompt_evidence_source(prompt=_source(), edit_evidence="")
    response = deepcopy(_response(_source()))
    event_citation = deepcopy(response["result"]["facts"]["first_path"][1])
    response["result"]["facts"]["operational_constraints"] = [event_citation]
    candidate = host_candidate_response(response, evidence_text=evidence)

    authored, _receipt = admit_greenfield_host_candidate(
        candidate,
        evidence_text=evidence,
        review_provider_factory=lambda: StructuredAuthoringProvider(
            admitted_review_response(
                component_custody=_base_component_custody(),
                constraint_custody=[
                    {
                        "constraint_index": 1,
                        "kind": "product_owned",
                        "owner_fact": {"field": "internal_systems", "row": 1},
                    }
                ],
            )
        ),
    )

    event_quote = event_citation["quote"]
    assert sum(
        row["responsibility_quote"] == event_quote
        for row in authored.component_responsibility_relations
    ) == 1
    witness = authored.candidate_review["admission_witness"]
    assert witness["component_custody"]["event_responsibilities"][0][
        "responsibility_citation"
    ] == event_citation
    assert witness["constraint_custody"] == [
        {
            "constraint_index": 1,
            "kind": "product_owned",
            "owner_fact": {"field": "internal_systems", "row": 1},
        }
    ]


def test_host_candidate_projects_constraint_that_contains_a_human_event_condition() -> None:
    old_source = _source()
    old_path = (
        "Dock attendant Ivo enters a vessel tag and the product records berth "
        "occupancy before the berth map shows the placement"
    )
    privacy_constraint = (
        "Harbor Desk keeps draft evidence private until Dock attendant Ivo enters a vessel tag"
    )
    new_path = (
        f"{privacy_constraint}, and the product records berth occupancy before the berth map "
        "shows the placement"
    )
    source = old_source.replace(old_path, new_path)
    evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = deepcopy(_response(old_source))
    response["result"]["facts"]["operational_constraints"][0] = {
        "quote": privacy_constraint,
        "occurrence": 1,
    }
    response["result"]["source_precedence"] = [
        {"before_event": 1, "after_event": 2, "constraint_index": 1}
    ]

    candidate = host_candidate_response(response, evidence_text=evidence)
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=evidence)
    authored, _receipt = admit_greenfield_host_candidate(
        candidate,
        evidence_text=evidence,
        review_provider_factory=lambda: StructuredAuthoringProvider(
            admitted_review_response(
                component_custody=_base_component_custody(),
                constraint_custody=[{
                    "constraint_index": 1,
                    "kind": "product_owned",
                    "owner_fact": {"field": "title", "row": 1},
                }]
            )
        ),
    )

    relation = next(
        row
        for row in authored.component_responsibility_relations
        if row["responsibility_quote"] == privacy_constraint
    )
    assert relation["owner_system_path"] == "/title"
    assert relation["first_path_event_order"] == 1
    assert "components" not in canonical["result"]
    assert canonical["result"]["source_precedence"] == [
        {"before_event": 1, "after_event": 2, "constraint_index": 1}
    ]


def test_candidate_review_owns_complete_typed_component_custody() -> None:
    assert "author\ndoes not own accepted component composition" in REVIEW_PROMPT
    assert "exactly one row for every accepted event" in REVIEW_PROMPT
    assert "additional_responsibilities" in REVIEW_PROMPT
    assert "source-custody control" in REVIEW_PROMPT
    assert "admission_witness.component_custody" in REVIEW_PROMPT
    assert "admission_witness.constraint_custody" in REVIEW_PROMPT
    assert "cannot substitute for accepted custody" in REVIEW_PROMPT


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
        "context": (
            "Dock attendant Ivo enters a vessel tag and the product records berth "
            "occupancy before the berth map shows the placement"
        ),
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
    with pytest.raises(ValueError, match="distinct non-overlapping source citations"):
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
    custody = _base_component_custody()
    custody["event_responsibilities"].insert(0, {
        "event_order": 1,
        "responsibility_citation": {
            "quote": "Dock attendant Ivo enters a vessel tag",
            "occurrence": 1,
        },
    })

    with pytest.raises(RuntimeError, match="invalid component custody"):
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=response,
            review_provider_factory=lambda: AdmittingReviewProvider(
                component_custody=custody,
            ),
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
        "_greenfield_review_provider",
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
        "outcome": "denied",
        "issue": {
            "path": "candidate.accepted_source.events[0]",
            "reason": "The selected event assigns the action to the wrong actor.",
        },
        "clarification": None,
        "admission_witness": None,
    })

    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_review_provider",
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
        "_greenfield_review_provider",
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

    missing_rc = greenfield_proposals_cli.rebuild_pending_transaction(
        repo_root=tmp_path,
        transaction_hash=original.transaction_hash,
        edit_evidence=correction,
        edit_evidence_file="",
        as_json=True,
    )
    missing_payload = json.loads(capsys.readouterr().out)

    assert missing_rc == 2
    assert "requires one host-authored candidate matching" in missing_payload["error"]
    assert requested_roles == ["candidate_review"]

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

    canonical = canonical_greenfield_host_candidate(host, evidence_text=evidence)

    assert host == frozen
    assert canonical["version"] != host["version"]
    assert [
        citation["quote"]
        for citation in canonical["result"]["facts"]["first_path"]
    ] == [event["source_citation"]["quote"] for event in host["result"]["events"]]
    assert all(
        "source_citation" not in event for event in canonical["result"]["events"]
    )
