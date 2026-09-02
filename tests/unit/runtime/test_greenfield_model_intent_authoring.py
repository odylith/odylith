"""Contract proof for source-cited Greenfield model intent authoring."""

from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from odylith.runtime.domain_intelligence import (
    greenfield_experience,
    greenfield_preconfirm_engine,
    greenfield_proposals,
    greenfield_proposals_cli,
    greenfield_source_casing,
    greenfield_traceability,
)
from odylith.runtime.domain_intelligence import greenfield_preconfirm_handoff_quality
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import (
    build_confirmed_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    authored_component_relation_facts,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_intent_shaping_prompt import (
    accepted_intent_shaping_prompt,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    combined_prompt_evidence_source,
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
    clarification_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import (
    _LIST_FIELDS,
    _TEXT_FIELDS,
    _response,
    _source,
)


def test_accepted_intent_shaping_preserves_source_punctuation_without_double_periods() -> None:
    prompt = accepted_intent_shaping_prompt(
        {
            "title": "PulseHIIT",
            "problem": "A trainee needs hands-free interval cues.",
            "product_view": "PulseHIIT preserves the completed session in history.",
        },
        fallback_title="Fallback",
    )

    assert prompt.splitlines() == [
        "Product: PulseHIIT",
        "Problem: A trainee needs hands-free interval cues.",
        "Product view: PulseHIIT preserves the completed session in history.",
    ]
    assert ".." not in prompt


def test_model_authored_intent_reaches_staged_product_intent_without_parser_recovery(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    receipt: dict[str, object] = {}
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(_response(staged_evidence)),
        authoring_timeout_seconds=84,
        authoring_profile_id=RESCUE_PROFILE_ID,
        authoring_receipt=receipt,
    )

    assert candidate["first_path"].rstrip(".") == _TEXT_FIELDS["first_path"]
    assert candidate["human_actors"] == ["Dock attendant Ivo"]
    assert candidate["internal_systems"] == ["Berth map"]
    assert receipt["tier"] == "rescue"
    assert receipt["authoring_version"] == GREENFIELD_INTENT_AUTHORING_VERSION
    assert receipt["semantic_model_call_count"] == 1
    assert candidate["authored_semantics"]["first_path_relations"][0]["action_verb_quote"] == "enters"
    assert "model_authoring" not in candidate
    assert candidate["product_intent_authority"]["material_fields"]["first_path"]["source_span_ids"] == [
        "authoring:first_path:1:4"
    ]
    envelope = candidate["product_intent_authority"]["operating_envelope"]
    observed_evidence = envelope["evidence_contract"]["observed"]
    observed_model = envelope["model_contract"]["observed"]
    profile = get_greenfield_model_profile(RESCUE_PROFILE_ID)
    assert observed_evidence == {
        "format": "operator_prompt",
        "source_kind": "public_evidence",
        "bytes": len(staged_evidence.encode("utf-8")),
        "documents": 1,
        "language": "en",
        "language_assurance": "explicit_operator_contract_not_content_detection",
    }
    assert observed_model == receipt["model_profile"]
    assert observed_model == {
        "profile_id": RESCUE_PROFILE_ID,
        "provider": profile.provider,
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "effective_timeout_seconds": profile.model_timeout_seconds,
        "authoring_tier": "rescue",
    }


def test_edit_evidence_reauthors_one_new_typed_candidate_with_one_model_call(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    edited_path = (
        "Dock attendant Ivo scans a vessel tag and the product records berth occupancy "
        "before the berth map shows the reviewed placement"
    )
    edit_evidence = f"Harbor Desk Plus. {edited_path}. The berth map shows the reviewed placement."
    edited_intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Harbor Desk Plus",
        "first_path": edited_path,
        "success_metrics": ["The berth map shows the reviewed placement"],
    }
    provider = StructuredAuthoringProvider(
        authored_response(
            edited_intent,
            evidence_text=combined_prompt_evidence_source(
                prompt=source,
                edit_evidence=edit_evidence,
            ),
            component_responsibility_owners=["Berth map"],
            first_path_relations=[
                {
                    "actor_kind": "human",
                    "actor_quote": "Dock attendant Ivo",
                    "event_quote": "Dock attendant Ivo scans a vessel tag",
                    "action_verb_quote": "scans",
                    "target_quote": "a vessel tag",
                    "visible_result_quote": "",
                    "recovery_path": False,
                },
                {
                    "actor_kind": "product",
                    "actor_quote": "the product",
                    "owner_system_quote": "Berth map",
                    "event_quote": "the product records berth occupancy",
                    "action_verb_quote": "records",
                    "target_quote": "berth occupancy",
                    "visible_result_quote": "",
                    "recovery_path": False,
                },
                {
                    "actor_kind": "product",
                    "actor_quote": "the berth map",
                    "owner_system_quote": "Berth map",
                    "event_quote": "the berth map shows the reviewed placement",
                    "action_verb_quote": "shows",
                    "target_quote": "the reviewed placement",
                    "visible_result_quote": "the berth map shows the reviewed placement",
                    "recovery_path": False,
                },
            ],
        )
    )

    candidate = materialize_model_authored_intent(
        prompt=source,
        edit_evidence=edit_evidence,
        repo_root=tmp_path,
        authoring_provider=provider,
        authoring_timeout_seconds=84,
        authoring_profile_id=RESCUE_PROFILE_ID,
    )

    assert candidate["title"] == "Harbor Desk Plus"
    assert candidate["first_path"] == edited_path
    assert candidate["authored_semantics"]["first_path_relations"][0]["action_verb_quote"] == "scans"
    assert candidate["product_intent_authority"]["source_format"] == "operator_prompt_with_edit_evidence"
    assert provider.calls == 1


def test_model_authored_multi_component_events_bind_to_exact_source_owned_systems(tmp_path) -> None:
    first_path = (
        "Applicant Nia submits a permit packet. "
        "Intake Desk records the permit application. "
        "Review Board approves the permit application. "
        "Review Board shows Applicant Nia the approval receipt"
    )
    intent = {
        "title": "Permit Relay",
        "product_story": "Applicant Nia receives a reviewable permit decision",
        "state_object": "permit application",
        "first_path": first_path,
        "proof_boundary": "Applicant Nia sees the approval receipt",
        "problem": "Permit decisions are difficult to follow",
        "customer": "Applicant Nia",
        "opportunity": "One reviewable permit path",
        "product_view": "Permit Relay gives Applicant Nia a reviewable permit path",
        "success_metrics": ["Applicant Nia sees the approval receipt"],
        "evidence_requirements": ["Retain the permit decision receipt"],
        "operational_constraints": ["Preserve the submitted permit packet"],
        "component_responsibilities": [
            "Intake Desk records the permit application",
            "Review Board approves the permit application",
        ],
        "human_actors": ["Applicant Nia"],
        "external_systems": ["Permit Archive"],
        "internal_systems": ["Intake Desk", "Review Board"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Do not issue construction schedules"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Intake Desk", "Review Board"],
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Applicant Nia",
                "event_quote": "Applicant Nia submits a permit packet.",
                "action_verb_quote": "submits",
                "target_quote": "a permit packet",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Intake Desk",
                "owner_system_quote": "Intake Desk",
                "event_quote": "Intake Desk records the permit application.",
                "action_verb_quote": "records",
                "target_quote": "the permit application",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Review Board",
                "owner_system_quote": "Review Board",
                "event_quote": "Review Board approves the permit application.",
                "action_verb_quote": "approves",
                "target_quote": "the permit application",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Review Board",
                "owner_system_quote": "Review Board",
                "event_quote": "Review Board shows Applicant Nia the approval receipt",
                "action_verb_quote": "shows",
                "target_quote": "the approval receipt",
                "visible_result_quote": "the approval receipt",
                "recovery_path": False,
            },
        ],
    )
    candidate = materialize_model_authored_intent(
        prompt=source,
        edit_evidence="",
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(response),
        authoring_timeout_seconds=84,
        authoring_profile_id=RESCUE_PROFILE_ID,
    )

    proposal = build_confirmed_greenfield_proposal(
        prompt=source,
        title="Permit Relay",
        observed_source={},
        confirmed_intent=candidate,
    )

    assert [row["label"] for row in proposal["components"]] == ["Intake Desk", "Review Board"]
    assert proposal["components"][0]["component_contract"]["responsibility_facts"] == [
        "Intake Desk records the permit application"
    ]
    assert proposal["components"][1]["component_contract"]["responsibility_facts"] == [
        "Review Board approves the permit application"
    ]
    assert "Review Board approves" not in proposal["components"][0]["responsibility"]
    assert "Intake Desk records" not in proposal["components"][1]["responsibility"]
    assert [row["workstream_role"] for row in proposal["backlog"]] == [
        "project",
        "boundary",
    ]
    assert proposal["backlog"][0]["component_focus"] == ["intake-desk", "review-board"]
    assert set(
        proposal["backlog"][1]["authored_workstream_semantics"]["fact_refs"]
    ) == {
        "/external_systems/0",
        "/non_goals/0",
        "/internal_systems/0",
        "/internal_systems/1",
        "/component_responsibilities/0",
        "/component_responsibilities/1",
    }
    assert proposal["security_compliance"] == {}
    for component in proposal["components"]:
        assert component["kind"] == "component"
        assert component["boundary"] == ""
        assert component["dependencies"] == []
        assert component["interfaces"] == []
        assert component["validation"] == []
        assert set(component["component_contract"]) == {
            "owner_system",
            "responsibility_facts",
            "owner_bound_events",
            "event_targets",
            "visible_results",
            "recovery_events",
            "state_context",
            "external_dependencies",
            "operational_constraints",
        }
        rendered_component = json.dumps(component, ensure_ascii=False)
        assert intent["proof_boundary"] not in rendered_component
        assert intent["non_goals"][0] not in rendered_component
        assert intent["external_systems"][0] not in rendered_component
        assert intent["operational_constraints"][0] not in rendered_component
    assert [
        event["owner_system"]
        for event in proposal["semantic_model"]["first_path_contract"]["events"]
    ] == ["", "Intake Desk", "Review Board", "Review Board"]
    first_path_contract = proposal["semantic_model"]["first_path_contract"]
    assert first_path_contract["required_fields"] == []
    assert first_path_contract["mutation"] == ""
    assert first_path_contract["deferred_scope"] == []

    context = next(row for row in proposal["diagrams"] if row["title"] == "System Context View")
    boundary = next(row for row in proposal["diagrams"] if row["title"] == "Component Boundary View")
    assert "external1 -->" not in context["mermaid_source"]
    assert "component1 --> component2" not in boundary["mermaid_source"]
    assert "--> component1" not in boundary["mermaid_source"]
    assert "-. deferred .->" not in boundary["mermaid_source"]


def test_model_authored_project_seals_one_package_with_justified_boundary(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    provider = StructuredAuthoringProvider(_response(staged_evidence))
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )

    candidate, transaction, transaction_path = greenfield_proposals_cli._compile_prompt_evidence_transaction(
        repo_root=tmp_path,
        prompt=source,
        edit_evidence="",
        release_selector="",
    )

    assert candidate["title"] == "Harbor Desk"
    assert provider.calls == 1
    assert [row["workstream_role"] for row in transaction.proposal["backlog"]] == [
        "project",
        "boundary",
    ]
    assert len(transaction.proposal["components"]) == 1
    assert len(transaction.proposal["diagrams"]) == 4
    assert "Berth placement is hard to track" in transaction.proposal["project_brief"]["purpose"]
    assert transaction.proposal["artifact_derivation"]["root"] == "intent.authored_semantics"
    assert transaction.prewrite_package is not None
    next_steps = transaction.prewrite_package.next_steps_preview
    assert next_steps is not None
    assert next_steps["coding_readiness_contract"]["source_facts"]["accepted_first_path"] == _TEXT_FIELDS[
        "first_path"
    ]
    assert [
        row["gate_id"] for row in next_steps["coding_readiness_contract"]["gates"]
    ] == [
        "implementation_environment",
        "source_boundary",
        "scope_boundary",
        "proof_boundary",
    ]
    dashboard = transaction.prewrite_package.project_dashboard_preview
    assert dashboard is not None
    assert [row["step_id"] for row in dashboard["host_handoff_prompts"]] == [
        "choose_language",
        "create_plan",
        "build_slice",
        "prove_behavior",
        "refresh_governance",
    ]
    assert all(row["contract"]["projection_policy"] == "structural_copy_only" for row in dashboard["host_handoff_prompts"])
    for artifact in (
        transaction.proposal["release_plan"],
        *transaction.proposal["backlog"],
        *transaction.proposal["components"],
        *transaction.proposal["diagrams"],
    ):
        assert artifact["project_intelligence_binding"]["source"] == "intent.authored_semantics"
    accepted_events = [
        event
        for event in transaction.proposal["semantic_model"]["first_path_contract"]["events"]
        if event["source_kind"] == "accepted_first_path"
    ]
    assert [(event["actor"], event["action"]) for event in accepted_events] == [
        ("Dock attendant Ivo", "enters"),
        ("the product", "records"),
        ("the berth map", "shows"),
    ]
    assert transaction_path.is_file()


def test_public_propose_cli_uses_one_model_call_and_returns_hash_bound_choices(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    provider = StructuredAuthoringProvider(_response(staged_evidence))
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )

    rc = greenfield_proposals_cli.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", source, "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0, payload
    assert payload["mode"] == "product_create_transaction"
    assert provider.calls == 1
    assert payload["transaction_file"].endswith("product-create-transaction.v1.json")
    choices = payload["confirmation"]["choices"]
    assert [choice["command"].split(maxsplit=1)[0] for choice in choices] == [
        "CONFIRM",
        "EDIT",
        "REJECT",
    ]
    assert not (tmp_path / "odylith/radar/source").exists()


def test_public_authored_propose_bypasses_the_legacy_completion_cascade(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    provider = StructuredAuthoringProvider(_response(staged_evidence))
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("authored Greenfield propose must not enter the legacy completion cascade")

    for name in (
        "complete_confirmed_proposal",
        "complete_greenfield_semantic_apply_payload",
        "apply_greenfield_patchset_repairs",
        "build_artifact_enrichment",
        "collapse_adjacent_duplicate_terms",
        "derive_greenfield_impacted_parts",
        "domain_risk_for_row",
        "_security_posture_for_row",
    ):
        assert not hasattr(greenfield_proposals, name)
    for name in (
        "active_release_components",
        "build_artifact_enrichment",
        "collapse_adjacent_duplicate_terms",
        "proposal_risk_lines",
        "workstream_risk_lines",
        "_semantic_tokens",
    ):
        if hasattr(greenfield_traceability, name):
            monkeypatch.setattr(greenfield_traceability, name, forbidden)
    for name in (
        "proposal_source_casing_text",
        "restore_source_casing_in_public_copy",
        "package_with_source_casing",
    ):
        monkeypatch.setattr(greenfield_source_casing, name, forbidden)
    for name in (
        "_first_path_summary",
        "_first_release_requirement_sentence",
        "_preview_safe_fragment",
        "_semantic_anchor_gate",
    ):
        if hasattr(greenfield_experience, name):
            monkeypatch.setattr(greenfield_experience, name, forbidden)
    assert not hasattr(
        greenfield_preconfirm_handoff_quality,
        "generated_public_copy_issues",
    )

    rc = greenfield_proposals_cli.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", source, "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0, payload
    assert provider.calls == 1
    assert payload["mode"] == "product_create_transaction"
    assert payload["transaction_file"].endswith("product-create-transaction.v1.json")


def test_public_propose_cli_returns_one_model_question_without_a_transaction(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:  # type: ignore[no-untyped-def]
    provider = StructuredAuthoringProvider(
        clarification_response(
            question="What result should the dock attendant see after the first task?",
            material_dimension="visible_result",
        )
    )
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )

    rc = greenfield_proposals_cli.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", "Create Harbor Desk", "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["mode"] == "clarification_required"
    assert payload["clarification"]["required_fields"] == ["visible_result"]
    assert payload["clarification"]["model_profile"]["profile_id"] == STANDARD_PROFILE_ID
    assert payload["clarification"]["model_profile"]["provider"] == "codex-cli"
    assert payload["clarification"]["model_profile"]["model"] == get_greenfield_model_profile(
        STANDARD_PROFILE_ID
    ).model
    assert provider.calls == 1
    assert not (tmp_path / ".odylith/runtime/greenfield/pending").exists()


def test_model_authored_preconfirm_exposes_no_repair_callback() -> None:
    assert not hasattr(greenfield_proposals, "_repair_confirmed_apply_payload")
    parameters = inspect.signature(
        greenfield_preconfirm_engine.run_greenfield_preconfirm_engine
    ).parameters
    assert "repair_proposal" not in parameters
    assert "prepare_repair_context" not in parameters
    assert "rerender_prewrite" not in parameters


def test_authoring_calculates_citation_hashes_from_the_exact_source_bytes() -> None:
    source = _source()
    response = _response(source)
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert result.source_spans[0]["quote_sha256"] == hashlib.sha256(b"Harbor Desk").hexdigest()


def test_authoring_collapses_exact_duplicate_typed_fact_rows() -> None:
    source = _source()
    response = _response(source)
    facts = response["facts"]
    assert isinstance(facts, list)
    path_fact_index = next(
        index for index, fact in enumerate(facts) if fact["field"] == "first_path"
    )
    facts.insert(path_fact_index + 1, dict(facts[path_fact_index]))

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert result.intent["first_path"] == _TEXT_FIELDS["first_path"]
    assert sum(
        1 for span in result.source_spans if span["section_key"] == "first_path"
    ) == 1


def test_authoring_accepts_an_explicit_repeated_quote_occurrence_without_first_match_rebinding() -> None:
    source = f"Harbor Desk. {_source()}"
    response = _response(source)
    second_start = source.encode("utf-8").find(b"Harbor Desk", 1)
    response["facts"][0]["occurrence"] = 2  # type: ignore[index]

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert result.source_spans[0]["source_start_byte"] == second_start
    assert result.atomic_claims[0]["source_start_byte"] == second_start


def test_authoring_rejects_an_impossible_occurrence_for_a_repeated_quote() -> None:
    source = f"Harbor Desk. {_source()}"
    response = _response(source)
    response["facts"][0]["occurrence"] = source.count("Harbor Desk") + 1  # type: ignore[index]

    with pytest.raises(GreenfieldModelAuthoringError, match="quote occurrence that is not present"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_derives_atomic_custody_without_a_second_model_semantic_payload() -> None:
    source = _source()
    response = _response(source)
    assert "atomic_claims" not in response

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    relation_atoms = {
        (row["relation_order"], row["relation_role"])
        for row in result.atomic_claims
        if row["relation_order"]
    }
    assert relation_atoms == {
        (relation["order"], role)
        for relation in result.first_path_relations
        for role in (
            "actor_quote",
            "action_verb_quote",
            "target_quote",
            "visible_result_quote",
        )
        if relation[role]
    }


def test_authoring_rejects_the_retired_model_atomic_payload() -> None:
    source = _source()
    response = _response(source)
    response["atomic_claims"] = []

    with pytest.raises(GreenfieldModelAuthoringError, match="unsupported response contract"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_rejects_a_source_quote_that_is_not_present() -> None:
    source = _source()
    response = _response(source)
    response["facts"][0] = {  # type: ignore[index]
        "field": "title",
        "quote": "Not in evidence",
        "occurrence": 1,
    }

    with pytest.raises(GreenfieldModelAuthoringError, match="quote occurrence that is not present"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_rejects_fragment_stitching_for_a_singular_field() -> None:
    source = _source()
    response = _response(source)
    facts = [
        row
        for row in response["facts"]  # type: ignore[union-attr]
        if row["field"] != "state_object"
    ]
    facts.extend(
        [
            {
                "field": "state_object",
                "quote": "berth",
                "occurrence": 1,
            },
            {
                "field": "state_object",
                "quote": "occupancy",
                "occurrence": 1,
            },
        ]
    )
    response["facts"] = facts

    with pytest.raises(GreenfieldModelAuthoringError, match="singular field"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_rejects_an_action_relation_not_present_in_the_accepted_path() -> None:
    source = _source()
    response = _response(source)
    response["events"][0]["action_quote"] = "deletes"  # type: ignore[index]

    with pytest.raises(GreenfieldModelAuthoringError, match="ungrounded first-path event"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_rejects_a_missing_component_responsibility_owner() -> None:
    source = _source()
    response = _response(source)
    response["components"] = []

    with pytest.raises(GreenfieldModelAuthoringError, match="invalid component ownership"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_rejects_a_duplicate_component_responsibility_owner() -> None:
    source = _source()
    response = _response(source)
    relations = response["components"]
    assert isinstance(relations, list)
    relations.append(dict(relations[0]))

    with pytest.raises(GreenfieldModelAuthoringError, match="duplicated component ownership"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_rejects_a_component_owner_that_is_not_a_product_system_fact() -> None:
    source = _source()
    response = _response(source)
    facts = response["facts"]
    assert isinstance(facts, list)
    human_fact_quote = next(
        fact["quote"]
        for fact in facts
        if fact["field"] == "human_actors"
    )
    response["components"][0]["owner_fact_quote"] = human_fact_quote  # type: ignore[index]

    with pytest.raises(GreenfieldModelAuthoringError, match="unbound component owner"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_canonicalizes_component_owner_rows_to_responsibility_order() -> None:
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "component_responsibilities": ["Record berth occupancy", "Show berth placement"],
    }
    source = ". ".join(
        [
            *_TEXT_FIELDS.values(),
            *(str(row) for key, rows in intent.items() if key in _LIST_FIELDS for row in rows),
        ]
    ) + "."
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Berth map", "Berth map"],
    )
    response["components"].reverse()

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert [
        row["responsibility_quote"] for row in result.component_responsibility_relations
    ] == ["Record berth occupancy", "Show berth placement"]


def test_authoring_uses_the_selected_title_fact_as_an_explicit_owner_fallback() -> None:
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "internal_systems": [],
    }
    source = ". ".join(
        [
            *_TEXT_FIELDS.values(),
            *(str(row) for key, rows in intent.items() if key in _LIST_FIELDS for row in rows),
        ]
    ) + "."

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                component_responsibility_owners=["Harbor Desk"],
            )
        ),
        clock=lambda: 0.0,
    )

    assert result.component_responsibility_relations[0]["owner_system_path"] == "/title"
    assert result.component_responsibility_relations[0]["owner_system_quote"] == "Harbor Desk"


def test_envelope_rejects_authored_spans_rebound_to_different_source_bytes() -> None:
    source = _source()
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(_response(source)),
        clock=lambda: 0.0,
    )
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            result.first_path_relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }

    with pytest.raises(ValueError, match="exact authoring evidence digest"):
        build_product_intent_envelope(
            sealed_intent,
            source_text=f"{source} unselected source B",
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )


def test_envelope_reverifies_atomic_claim_bytes_against_the_exact_source() -> None:
    source = _source()
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(_response(source)),
        clock=lambda: 0.0,
    )
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            result.first_path_relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }
    claims = [dict(row) for row in result.atomic_claims]
    claims[0]["source_start_byte"] += 1
    claims[0]["source_end_byte"] += 1

    with pytest.raises(ValueError, match="atomic source custody does not match"):
        build_product_intent_envelope(
            sealed_intent,
            source_text=source,
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=claims,
            authored_source_sha256=result.source_sha256,
        )


def test_authoring_derives_the_exact_event_link_for_an_overlapping_responsibility() -> None:
    product_event = "Intake Desk records the permit application"
    first_path = f"Applicant Nia submits a permit packet, then {product_event}"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Permit Relay",
        "state_object": "permit application",
        "first_path": first_path,
        "component_responsibilities": ["records the permit application"],
        "human_actors": ["Applicant Nia"],
        "internal_systems": ["Intake Desk"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Intake Desk"],
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Applicant Nia",
                "event_quote": "Applicant Nia submits a permit packet",
                "action_verb_quote": "submits",
                "target_quote": "a permit packet",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Intake Desk",
                "owner_system_quote": "Intake Desk",
                "event_quote": product_event,
                "action_verb_quote": "records",
                "target_quote": "the permit application",
                "visible_result_quote": product_event,
                "recovery_path": False,
            },
        ],
    )

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert result.component_responsibility_relations[0][
        "first_path_event_order"
    ] == 2


def test_authoring_rejects_a_repeated_owner_on_one_typed_product_event() -> None:
    product_event = "Intake Desk records the permit application"
    first_path = f"Applicant Nia submits a permit packet, then {product_event}"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Permit Relay",
        "state_object": "permit application",
        "first_path": first_path,
        "component_responsibilities": [product_event],
        "human_actors": ["Applicant Nia"],
        "internal_systems": ["Intake Desk", "Review Board"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Review Board"],
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Applicant Nia",
                "event_quote": "Applicant Nia submits a permit packet",
                "action_verb_quote": "submits",
                "target_quote": "a permit packet",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Intake Desk",
                "owner_system_quote": "Intake Desk",
                "event_quote": product_event,
                "action_verb_quote": "records",
                "target_quote": "the permit application",
                "visible_result_quote": product_event,
                "recovery_path": False,
            },
        ],
    )

    component_relations = response["components"]
    assert isinstance(component_relations, list)
    component_relations[0]["owner_fact_quote"] = "Review Board"

    with pytest.raises(GreenfieldModelAuthoringError, match="contradictory component owners"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_authoring_rejects_duplicate_labels_for_distinct_owner_paths() -> None:
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Harbor Desk",
        "internal_systems": ["Harbor Desk"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )

    with pytest.raises(GreenfieldModelAuthoringError, match="ambiguous product owner"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(
                authored_response(
                    intent,
                    evidence_text=source,
                    component_responsibility_owners=["Harbor Desk"],
                )
            ),
            clock=lambda: 0.0,
        )


def test_product_owned_terminal_result_uses_the_typed_event_owner() -> None:
    first_path = "Applicant Nia enters one item and Permit Relay shows it listed"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Permit Relay",
        "state_object": "one item",
        "first_path": first_path,
        "component_responsibilities": [],
        "human_actors": ["Applicant Nia"],
        "internal_systems": [],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                terminal_component_owner="Permit Relay",
                first_path_relations=[
                    {
                        "actor_kind": "human",
                        "actor_quote": "Applicant Nia",
                        "event_quote": "Applicant Nia enters one item",
                        "action_verb_quote": "enters",
                        "target_quote": "one item",
                        "visible_result_quote": "",
                        "recovery_path": False,
                    },
                    {
                        "actor_kind": "product",
                        "actor_quote": "Permit Relay",
                        "owner_system_quote": "Permit Relay",
                        "event_quote": "Permit Relay shows it listed",
                        "action_verb_quote": "shows",
                        "target_quote": "it",
                        "visible_result_quote": "it listed",
                        "recovery_path": False,
                    },
                ],
            )
        ),
        clock=lambda: 0.0,
    )

    assert result.component_responsibility_relations == (
        {
            "responsibility_path": "/first_path",
            "responsibility_quote": "it listed",
            "owner_system_path": "/title",
            "owner_system_quote": "Permit Relay",
            "first_path_event_order": 2,
            "responsibility_source": "terminal_visible_result",
        },
    )
    contracts = authored_component_relation_facts(
        title="Permit Relay",
        internal_systems=(),
        relations=result.first_path_relations,
        component_responsibility_relations=result.component_responsibility_relations,
    )
    assert contracts[0]["responsibility_facts"] == ["it listed"]


def test_terminal_result_keeps_exact_proof_fact_custody_outside_final_event() -> None:
    result_quote = "pickup readiness"
    proof_boundary = "Verify pickup readiness after each released batch"
    first_path = (
        "Coordinator Nia records each donation and "
        "Pickup Relay releases each batch"
    )
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Pickup Relay",
        "state_object": "donation batch",
        "first_path": first_path,
        "proof_boundary": proof_boundary,
        "success_metrics": ["Each donation batch is released"],
        "component_responsibilities": [],
        "human_actors": ["Coordinator Nia"],
        "external_systems": [],
        "internal_systems": [],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                terminal_component_owner="Pickup Relay",
                first_path_relations=[
                    {
                        "actor_kind": "human",
                        "actor_quote": "Coordinator Nia",
                        "event_quote": "Coordinator Nia records each donation",
                        "action_verb_quote": "records",
                        "target_quote": "each donation",
                        "visible_result_quote": "",
                        "recovery_path": False,
                    },
                    {
                        "actor_kind": "product",
                        "actor_quote": "Pickup Relay",
                        "owner_system_quote": "Pickup Relay",
                        "event_quote": "Pickup Relay releases each batch",
                        "action_verb_quote": "releases",
                        "target_quote": "each batch",
                        "visible_result_quote": result_quote,
                        "recovery_path": False,
                    },
                ],
            )
        ),
        clock=lambda: 0.0,
    )

    terminal_event = result.first_path_relations[-1]
    assert result_quote not in terminal_event["event_quote"]
    assert terminal_event["visible_result_quote"] == result_quote
    assert result.component_responsibility_relations[0]["responsibility_path"] == "/proof_boundary"
    visible_claim = next(
        row
        for row in result.atomic_claims
        if row["relation_role"] == "visible_result_quote"
    )
    assert visible_claim["projection_path"] == "/proof_boundary"
    assert visible_claim["projection_start_byte"] == proof_boundary.index(result_quote)
    source_bytes = source.encode("utf-8")
    assert (
        source_bytes[
            visible_claim["source_start_byte"] : visible_claim["source_end_byte"]
        ].decode("utf-8")
        == result_quote
    )


def test_human_terminal_result_uses_one_explicit_grounded_product_owner() -> None:
    first_path = "Applicant Nia enters one item and sees it listed"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Permit Relay",
        "state_object": "one item",
        "first_path": first_path,
        "component_responsibilities": [],
        "human_actors": ["Applicant Nia"],
        "internal_systems": [],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                terminal_component_owner="Permit Relay",
            )
        ),
        clock=lambda: 0.0,
    )

    assert result.component_responsibility_relations == (
        {
            "responsibility_path": "/first_path",
            "responsibility_quote": first_path,
            "owner_system_path": "/title",
            "owner_system_quote": "Permit Relay",
            "first_path_event_order": 1,
            "responsibility_source": "terminal_visible_result",
        },
    )


def test_human_only_path_cannot_reach_staging_without_component_viability() -> None:
    first_path = "Applicant Nia enters one item and sees it listed"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Permit Relay",
        "state_object": "one item",
        "first_path": first_path,
        "component_responsibilities": [],
        "human_actors": ["Applicant Nia"],
        "internal_systems": [],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    response = authored_response(
        intent,
        evidence_text=source,
        terminal_component_owner="Permit Relay",
    )
    response["components"] = []

    with pytest.raises(GreenfieldModelAuthoringError, match="invalid component ownership"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_sealed_semantics_drop_all_provider_fact_indices(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(_response(source)),
        authoring_timeout_seconds=84,
        authoring_profile_id=RESCUE_PROFILE_ID,
    )
    serialized = json.dumps(candidate["authored_semantics"], ensure_ascii=False, sort_keys=True)

    assert "responsibility_fact_index" not in serialized
    assert "owner_system_fact_index" not in serialized


def test_component_relation_order_is_unicode_and_domain_neutral() -> None:
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "component_responsibilities": ["Žurnalo įrašas", "航路記録"],
        "internal_systems": ["Sąsaja", "航路"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Sąsaja", "航路"],
    )
    response["components"].reverse()

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert [
        row["responsibility_quote"] for row in result.component_responsibility_relations
    ] == ["Žurnalo įrašas", "航路記録"]


def test_authoring_preserves_model_owned_roles_without_a_lexical_post_filter() -> None:
    source = f"{_source()} Proof reviewer validates the retention record."
    response = authored_response(
        {
            **_TEXT_FIELDS,
            **_LIST_FIELDS,
            "human_actors": ["Dock attendant Ivo", "Proof reviewer"],
            "component_responsibilities": [
                "Record berth occupancy",
                "Proof reviewer validates the retention record.",
            ],
        },
        evidence_text=source,
        component_responsibility_owners=["Berth map", "Berth map"],
    )

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert result.intent["human_actors"] == ["Dock attendant Ivo", "Proof reviewer"]
    assert result.intent["component_responsibilities"] == [
        "Record berth occupancy",
        "Proof reviewer validates the retention record.",
    ]


def test_late_packet_enters_rescue_without_a_second_model_call() -> None:
    source = _source()
    provider = StructuredAuthoringProvider(_response(source))
    ticks = iter((0.0, 55.0))

    result = author_greenfield_intent(
        evidence_text=source,
        provider=provider,
        timeout_seconds=84,
        model_profile_id=RESCUE_PROFILE_ID,
        clock=lambda: next(ticks),
    )

    assert result.tier == "rescue"
    assert provider.calls == 1


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
    ticks = iter((0.0, 1.0))

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
    response = clarification_response(
        question="ignored model wording",
        material_dimension="component_ownership",
    )

    with pytest.raises(GreenfieldClarificationRequired) as exc_info:
        materialize_model_authored_intent(
            prompt="Create a comparison product with two possible responsibility owners.",
            repo_root=tmp_path,
            authoring_provider=StructuredAuthoringProvider(response),
            authoring_timeout_seconds=84,
            authoring_profile_id=RESCUE_PROFILE_ID,
        )

    assert exc_info.value.question == (
        "Which product-owned system should own the stated responsibility?"
    )
    assert exc_info.value.required_fields == ("component_ownership",)
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
        conflicting_quotes=(first_claim, second_claim),
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
    response["ambiguities"] = ["The evidence gives two retention periods that require later resolution."]
    response["consistency"] = {
        "status": "non_material_ambiguity",
        "conflicting_quotes": [first_claim, second_claim],
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
