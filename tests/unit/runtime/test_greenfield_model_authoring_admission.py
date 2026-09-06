"""Profile budgets and materiality admission for Greenfield model authoring."""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GREENFIELD_MODEL_PROOF_FD_ENV,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    combined_prompt_evidence_source,
    materialize_model_authored_intent,
    render_product_intent_preview,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    get_greenfield_model_profile,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
    clarification_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _fact_source(intent: dict[str, Any]) -> str:
    return ". ".join(
        str(row)
        for field, value in intent.items()
        if field not in {"assumptions", "ambiguities"}
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."


def _product_only_intent() -> dict[str, Any]:
    return {
        "title": "Autonomous Feed Sentinel",
        "product_story": "Autonomous Feed Sentinel records a reviewable feed health receipt",
        "state_object": "feed health record",
        "first_path": "Receipt Engine records a feed health receipt",
        "proof_boundary": "feed health receipt",
        "problem": "Feed health has no durable receipt",
        "customer": "",
        "opportunity": "A durable receipt keeps feed health reviewable",
        "product_view": "Autonomous Feed Sentinel exposes the feed health receipt",
        "success_metrics": ["The feed health receipt is reviewable"],
        "evidence_requirements": [
            "Retain the feed status",
            "Retain the feed health receipt",
        ],
        "operational_constraints": [],
        "component_responsibilities": [
            "Record the feed health receipt",
            "Store the feed health record",
        ],
        "human_actors": [],
        "external_systems": [],
        "internal_systems": ["Receipt Engine", "Health Archive"],
        "assumptions": [
            {
                "applies_to": "customer",
                "statement": "Service owners are the primary beneficiaries of feed health receipts.",
            }
        ],
        "ambiguities": [],
        "non_goals": ["Do not control the source feed"],
    }


def _external_only_intent() -> dict[str, Any]:
    return {
        "title": "External Signal Intake",
        "product_story": "External Signal Intake retains signed health receipts",
        "state_object": "signed health receipt",
        "first_path": "Telemetry Gateway publishes a signed health receipt",
        "proof_boundary": "signed health receipt",
        "problem": "External health signals lack a reviewable receipt",
        "customer": "",
        "opportunity": "A signed receipt makes external health signals reviewable",
        "product_view": "External Signal Intake exposes each signed health receipt",
        "success_metrics": ["The signed health receipt is reviewable"],
        "evidence_requirements": ["Retain the signed health receipt"],
        "operational_constraints": [],
        "component_responsibilities": ["Retain signed health receipts"],
        "human_actors": [],
        "external_systems": ["Telemetry Gateway"],
        "internal_systems": ["Receipt Archive"],
        "assumptions": [
            {
                "applies_to": "customer",
                "statement": "Service owners are the primary beneficiaries of signed receipts.",
            }
        ],
        "ambiguities": [],
        "non_goals": [],
    }


def _machine_response(
    intent: dict[str, Any],
    *,
    evidence_text: str,
    actor_kind: str,
    actor_fact_quote: str,
    owners: list[str],
) -> dict[str, Any]:
    event = str(intent["first_path"])
    visible_result = str(intent["proof_boundary"])
    relation = {
        "actor_kind": actor_kind,
        "actor_fact_quote": actor_fact_quote,
        "event_quote": event,
        "action_verb_quote": "records" if actor_kind == "product" else "publishes",
        "target_quote": f"a {visible_result}",
        "visible_result_quote": visible_result,
    }
    if actor_kind == "product":
        relation["owner_system_quote"] = actor_fact_quote
    return authored_response(
        intent,
        evidence_text=evidence_text,
        first_path_relations=[relation],
        component_responsibility_owners=owners,
    )


def test_product_only_path_builds_complete_source_bound_proposal_without_a_fake_human(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    intent = _product_only_intent()
    prompt = _fact_source(intent)
    evidence = combined_prompt_evidence_source(prompt=prompt, edit_evidence="")
    provider = StructuredAuthoringProvider(
        _machine_response(
            intent,
            evidence_text=evidence,
            actor_kind="product",
            actor_fact_quote="Receipt Engine",
            owners=["Receipt Engine", "Health Archive"],
        )
    )

    candidate = materialize_model_authored_intent(
        prompt=prompt,
        repo_root=tmp_path,
        authoring_provider=provider,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=candidate,
    )

    assert provider.calls == 2
    assert "human_actors" not in candidate
    assert candidate["authored_semantics"]["first_path_relations"][0][
        "actor_fact_path"
    ] == "/internal_systems/0"
    authority = candidate["product_intent_authority"]
    assert authority["materiality_status"] == "passed"
    assert "human_actors" not in authority["material_fields"]
    assert all(
        not link["path"].startswith("/human_actors/")
        for atom in authority["atomic_facts"]
        for link in atom["projection_links"]
    )

    preview = render_product_intent_preview(candidate)
    assert "No human participants are stated in the source." in preview
    assert "Primary user" not in preview
    assert proposal["backlog"] and proposal["components"] and proposal["diagrams"]
    customer_ref = "/assumptions/0"
    assert [row["workstream_role"] for row in proposal["backlog"]] == ["project"]
    for row in proposal["backlog"]:
        semantics = row["authored_workstream_semantics"]
        assert semantics["rendered_field_refs"]["customer"] == [customer_ref]
        assert row["customer"] == (
            "Assumption — Service owners are the primary beneficiaries of feed health receipts."
        )
    context = next(
        row for row in proposal["diagrams"] if row["slug"].endswith("system-context")
    )
    assert not any(box["role"] == "Human actor" for box in context["diagram_boxes"])
    assert "actor1" not in context["mermaid_source"]


@pytest.mark.parametrize("malformed_humans", (None, "invented operator"))
def test_product_only_proposal_accepts_omission_but_rejects_malformed_present_humans(
    tmp_path,
    malformed_humans: object,
) -> None:  # type: ignore[no-untyped-def]
    intent = _product_only_intent()
    prompt = _fact_source(intent)
    evidence = combined_prompt_evidence_source(prompt=prompt, edit_evidence="")
    candidate = materialize_model_authored_intent(
        prompt=prompt,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(
            _machine_response(
                intent,
                evidence_text=evidence,
                actor_kind="product",
                actor_fact_quote="Receipt Engine",
                owners=["Receipt Engine", "Health Archive"],
            )
        ),
    )
    candidate["human_actors"] = malformed_humans

    with pytest.raises(ValueError, match="missing typed human actors"):
        build_authored_greenfield_proposal(
            observed_source={},
            release_selector="0.0.1",
            confirmed_intent=candidate,
        )


def test_external_only_path_retains_exact_external_actor_custody() -> None:
    intent = _external_only_intent()
    source = _fact_source(intent)
    provider = StructuredAuthoringProvider(
        _machine_response(
            intent,
            evidence_text=source,
            actor_kind="external_system",
            actor_fact_quote="Telemetry Gateway",
            owners=["Receipt Archive"],
        )
    )

    result = author_greenfield_intent(
        evidence_text=source,
        provider=provider,
        clock=lambda: 0.0,
    )

    assert provider.calls == 2
    assert result.intent["human_actors"] == []
    assert result.first_path_relations[0]["actor_kind"] == "external_system"
    assert result.first_path_relations[0]["actor_fact_path"] == "/external_systems/0"
    assert result.first_path_relations[0]["actor_fact_quote"] == "Telemetry Gateway"


@pytest.mark.parametrize(
    ("actor_kind", "removed_field"),
    (
        ("human", "human_actors"),
        ("product", "internal_systems"),
        ("external_system", "external_systems"),
    ),
)
def test_each_event_actor_kind_requires_one_selected_typed_actor_fact(
    actor_kind: str,
    removed_field: str,
) -> None:
    if actor_kind == "human":
        source = _source()
        response = _response(source)
    else:
        intent = (
            _product_only_intent()
            if actor_kind == "product"
            else _external_only_intent()
        )
        source = _fact_source(intent)
        response = _machine_response(
            intent,
            evidence_text=source,
            actor_kind=actor_kind,
            actor_fact_quote=(
                "Receipt Engine" if actor_kind == "product" else "Telemetry Gateway"
            ),
            owners=(
                ["Receipt Engine", "Health Archive"]
                if actor_kind == "product"
                else ["Receipt Archive"]
            ),
        )
    response["result"]["facts"][removed_field] = []  # type: ignore[index]

    with pytest.raises(
        GreenfieldModelAuthoringError,
        match="unbound first-path actor fact",
    ):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_late_packet_completes_mandatory_source_review_inside_rescue() -> None:
    source = _source()
    provider = StructuredAuthoringProvider(_response(source))
    ticks = iter((0.0, 55.0, 55.0, 55.0))

    result = author_greenfield_intent(
        evidence_text=source,
        provider=provider,
        timeout_seconds=84,
        model_profile_id=RESCUE_PROFILE_ID,
        clock=lambda: next(ticks),
    )

    assert result.tier == "rescue"
    assert provider.calls == 2


@pytest.mark.parametrize(
    ("profile_id", "expected_tier"),
    ((RESCUE_PROFILE_ID, "rescue"), (DEEP_PROFILE_ID, "deep")),
)
def test_pinned_nonstandard_profile_does_not_relabel_a_fast_response_as_standard(
    profile_id: str,
    expected_tier: str,
) -> None:
    source = _source()
    profile = get_greenfield_model_profile(profile_id)
    ticks = iter((0.0, 1.0, 1.0, 1.0))

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(_response(source)),
        timeout_seconds=profile.model_timeout_seconds,
        model_profile_id=profile_id,
        clock=lambda: next(ticks),
    )

    assert result.tier == expected_tier
    assert result.profile_id == profile_id


def test_authoring_keeps_one_material_question_separate_from_any_package() -> None:
    response = clarification_response(
        question="What visible result should the first user see after completing the task?",
        material_dimension="visible_result",
        evidence_quotes=(),
    )

    result = author_greenfield_intent(
        evidence_text="A project needs a clear outcome.",
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert isinstance(result, GreenfieldAuthoringClarification)
    assert result.required_fields == ("visible_result",)


def test_component_ownership_clarification_is_one_plain_question_without_staging(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    prompt = "Create a comparison product with two possible responsibility owners."
    response = clarification_response(
        question="ignored model wording",
        material_dimension="component_ownership",
        evidence_quotes=(),
    )

    with pytest.raises(GreenfieldClarificationRequired) as exc_info:
        materialize_model_authored_intent(
            prompt=prompt,
            repo_root=tmp_path,
            authoring_provider=StructuredAuthoringProvider(response),
            authoring_timeout_seconds=84,
            authoring_profile_id=RESCUE_PROFILE_ID,
        )

    assert exc_info.value.question == (
        "Which product-owned system should own the stated responsibility?"
    )
    assert exc_info.value.required_fields == ("component_ownership",)
    assessment = exc_info.value.authoring_receipt["consistency_assessment"]
    assert assessment["status"] == "material_ambiguity"
    assert [row["text"] for row in assessment["source_spans"]] == [
        combined_prompt_evidence_source(prompt=prompt, edit_evidence="")
    ]
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_source_bound_material_contradiction_returns_one_no_write_clarification(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    first_claim = "Retain source notes for seven years."
    second_claim = "Delete source notes after thirty days."
    prompt = f"Create an evidence workspace. {first_claim} {second_claim}"
    response = clarification_response(
        question="ignored model wording",
        material_dimension="operational_constraints",
        consistency_status="material_contradiction",
        evidence_quotes=(first_claim, second_claim),
    )

    with pytest.raises(GreenfieldClarificationRequired) as exc_info:
        materialize_model_authored_intent(
            prompt=prompt,
            repo_root=tmp_path,
            authoring_provider=StructuredAuthoringProvider(response),
            authoring_timeout_seconds=84,
            authoring_profile_id=RESCUE_PROFILE_ID,
        )

    assessment = exc_info.value.authoring_receipt["consistency_assessment"]
    assert assessment["status"] == "material_contradiction"
    assert [row["text"] for row in assessment["source_spans"]] == [first_claim, second_claim]
    assert exc_info.value.required_fields == ("operational_constraints",)
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_source_bound_nonmaterial_conflict_increases_sealed_ambiguity(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    first_claim = "Retain source notes for seven years"
    second_claim = "Delete source notes after thirty days"
    source = f"{_source()} {second_claim}."
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    response = _response(staged_evidence)
    response["result"]["ambiguities"] = ["The evidence gives two retention periods that require later resolution."]
    response["result"]["consistency"] = {
        "status": "non_material_ambiguity",
        "evidence_quotes": [first_claim, second_claim],
    }

    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(response),
        authoring_timeout_seconds=84,
        authoring_profile_id=RESCUE_PROFILE_ID,
    )

    envelope = candidate["product_intent_authority"]["operating_envelope"]
    assert envelope["complexity"]["dimensions"]["contradictions"] == 0
    assert envelope["complexity"]["dimensions"]["ambiguities"] == 1
    staged_consistency = (
        tmp_path / ".odylith/runtime/greenfield/candidate-evidence.v1.json"
    )
    assert staged_consistency.is_file()
    envelope_payload = json.loads(staged_consistency.read_text(encoding="utf-8"))
    consistency_spans = [
        span
        for span in envelope_payload["source_evidence"]["spans"]
        if span["span_id"].startswith("authoring:consistency:")
    ]
    assert [span["text"] for span in consistency_spans] == [first_claim, second_claim]


@pytest.mark.parametrize(
    ("failure_code", "diagnostic_detail"),
    (
        ("timeout", "Codex CLI exceeded 60.0s."),
        ("unavailable", "Codex CLI is unavailable."),
        ("transport_error", "Provider connection reset during authoring."),
        ("invalid_response", "invalid provider output " * 20),
    ),
)
def test_initial_non_mapping_response_retains_bounded_failure_observation(
    tmp_path,
    monkeypatch,
    failure_code: str,
    diagnostic_detail: str,
) -> None:  # type: ignore[no-untyped-def]
    provider = StructuredAuthoringProvider(None)
    provider.last_failure_code = failure_code
    provider.last_failure_detail = diagnostic_detail
    observation = tmp_path / "model-failure-observation.json"
    descriptor = os.open(observation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(descriptor))
    ticks = iter((0.0, 61.805))
    try:
        with pytest.raises(GreenfieldModelAuthoringError) as exc_info:
            author_greenfield_intent(
                evidence_text="Create a source-cited project.",
                provider=provider,
                model_profile_id=RESCUE_PROFILE_ID,
                timeout_seconds=80.0,
                clock=lambda: next(ticks),
            )
    finally:
        os.close(descriptor)

    assert str(exc_info.value) == (
        "A verified source-cited Greenfield package could not be produced; "
        "no records were created."
    )
    retained = json.loads(observation.read_text(encoding="utf-8"))
    assert retained["authoring_version"] == GREENFIELD_INTENT_AUTHORING_VERSION
    assert retained["semantic_model_call_count"] == 1
    assert "response" not in retained
    assert retained["failure"] == {
        "stage": "initial_authoring",
        "profile_id": RESCUE_PROFILE_ID,
        "effective_timeout_seconds": 60.0,
        "elapsed_seconds": pytest.approx(61.805),
        "response_shape": "NoneType",
        "provider": {
            "provider": "codex-cli",
            "code": failure_code,
            "model": "gpt-5.6-terra",
            "reasoning_effort": "medium",
        },
    }
    assert diagnostic_detail not in observation.read_text(encoding="utf-8")
    assert provider.calls == 1


def test_initial_non_mapping_response_without_proof_fd_keeps_public_error_exact(
    monkeypatch,
) -> None:
    monkeypatch.delenv(GREENFIELD_MODEL_PROOF_FD_ENV, raising=False)
    provider = StructuredAuthoringProvider(None)
    provider.last_failure_code = "unavailable"
    provider.last_failure_detail = "Codex CLI is unavailable."

    with pytest.raises(GreenfieldModelAuthoringError) as exc_info:
        author_greenfield_intent(
            evidence_text="Create a source-cited project.",
            provider=provider,
            clock=lambda: 0.0,
        )

    assert str(exc_info.value) == (
        "A verified source-cited Greenfield package could not be produced; "
        "no records were created."
    )
    assert provider.calls == 1
