from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import (
    preview_project_dashboard_payload,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    GreenfieldAuthoredSemanticsError,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_completion_types import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    PROJECT_HANDOFF_STEP_SCHEMA_VERSION,
    project_handoff_step_contract_issues,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_handoff_quality import (
    project_dashboard_preview_issues,
)
from odylith.runtime.project_intelligence import greenfield
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


FIRST_PATH = (
    "Registry Custodian QuOrates one Æther packet. "
    "Meridian Engine vitrifies the Æther packet into Ω-Receipt."
)
PRODUCT_STORY = (
    "People preserve APIv7 evidence while Ω-case casing remains source-authored."
)
PROOF_BOUNDARY = (
    "A reviewer replays the exact two-event path and observes Ω-Receipt."
)
EXPECTED_HANDOFF_STEPS = (
    "choose_language",
    "create_plan",
    "build_slice",
    "prove_behavior",
    "refresh_governance",
)


def _event_span(event: str) -> tuple[int, int]:
    character_start = FIRST_PATH.index(event)
    start = len(FIRST_PATH[:character_start].encode("utf-8"))
    return start, start + len(event.encode("utf-8"))


def _proposal() -> dict[str, object]:
    first_event = "Registry Custodian QuOrates one Æther packet."
    second_event = "Meridian Engine vitrifies the Æther packet into Ω-Receipt."
    first_start, first_end = _event_span(first_event)
    second_start, second_end = _event_span(second_event)
    state_start = second_start + len("Meridian Engine vitrifies the ".encode("utf-8"))
    independent_context_start = len(FIRST_PATH.encode("utf-8")) + 1
    external_context_end = independent_context_start + len("APIv7 Archive".encode("utf-8"))
    relations = (
        {
            "order": 1,
            "source_start_byte": first_start,
            "source_end_byte": first_end,
            "event_start_byte": first_start,
            "event_end_byte": first_end,
            "actor_kind": "human",
            "actor_fact_path": "/human_actors/0",
            "actor_fact_quote": "Registry Custodian",
            "owner_system_path": "",
            "owner_system_quote": "",
            "event_quote": first_event,
            "action_verb_quote": "QuOrates",
            "target_quote": "Æther packet",
            "visible_result_quote": "",
        },
        {
            "order": 2,
            "source_start_byte": second_start,
            "source_end_byte": second_end,
            "event_start_byte": second_start,
            "event_end_byte": second_end,
            "actor_kind": "product",
            "actor_fact_path": "/internal_systems/0",
            "actor_fact_quote": "Meridian Engine",
            "owner_system_path": "/internal_systems/0",
            "owner_system_quote": "Meridian Engine",
            "event_quote": second_event,
            "action_verb_quote": "vitrifies",
            "target_quote": "Æther packet",
            "visible_result_quote": "Ω-Receipt",
        },
    )
    return {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "intent": {
            "title": "eXact Ω Forge",
            "product_story": PRODUCT_STORY,
            "problem": "APIv7 evidence loses exact custody during manual relay.",
            "customer": "Registry Custodian",
            "opportunity": "Preserve one reviewable evidence transfer.",
            "product_view": "A source-custodied Æther transfer product.",
            "first_path": FIRST_PATH,
            "state_object": "Æther packet",
            "proof_boundary": PROOF_BOUNDARY,
            "human_actors": ["Registry Custodian", "Field Ombud"],
            "internal_systems": ["Meridian Engine"],
            "external_systems": ["APIv7 Archive"],
            "non_goals": ["Batch Æther migration"],
            "operational_constraints": ["Preserve APIv7 casing"],
            "evidence_requirements": ["Replay the two exact event quotes"],
            "success_metrics": ["One Ω-Receipt is visible"],
            "authored_semantics": authored_semantics_mapping(
                relations,
                (
                    {
                        "responsibility_path": "/first_path",
                        "responsibility_quote": "Ω-Receipt",
                        "owner_system_path": "/internal_systems/0",
                        "owner_system_quote": "Meridian Engine",
                        "first_path_event_order": 2,
                        "responsibility_source": "terminal_visible_result",
                    },
                ),
                first_path_context_relations=(
                    {
                        "context_kind": "state_object",
                        "fact_path": "/state_object",
                        "fact_quote": "Æther packet",
                        "source_start_byte": state_start,
                        "source_end_byte": state_start + len("Æther packet".encode("utf-8")),
                        "first_path_event_order": 2,
                    },
                    {
                        "context_kind": "external_system",
                        "fact_path": "/external_systems/0",
                        "fact_quote": "APIv7 Archive",
                        "source_start_byte": independent_context_start,
                        "source_end_byte": external_context_end,
                        "first_path_event_order": 0,
                    },
                    {
                        "context_kind": "operational_constraint",
                        "fact_path": "/operational_constraints/0",
                        "fact_quote": "Preserve APIv7 casing",
                        "source_start_byte": external_context_end + 1,
                        "source_end_byte": external_context_end
                        + 1
                        + len("Preserve APIv7 casing".encode("utf-8")),
                        "first_path_event_order": 0,
                    },
                ),
            ),
        },
        "observed_source": {"source_posture": "operator prompt evidence"},
        "classification": {"method": "model_authored_typed_intent"},
        "assumptions": [],
        "open_questions": [],
        "risks": [],
        "validation_strategy": [PROOF_BOUNDARY],
        "project_brief": {"purpose": PRODUCT_STORY},
        "project_intelligence": {
            "projection_origin": AUTHORED_PROJECTION_ORIGIN,
            "purpose": PRODUCT_STORY,
        },
        "release_plan": {
            "selector": "0.0.1",
            "label": "eXact Ω Forge 0.0.1",
            "strategy": PROOF_BOUNDARY,
        },
        "backlog": [
            {
                "idea_id": "B-701",
                "title": "Preserve Æther custody",
                "problem": "APIv7 evidence loses exact custody during manual relay.",
                "product_view": "A source-custodied Æther transfer product.",
                "recommended_first_slice": FIRST_PATH,
                "evidence_tier": "user_intent",
                "projection_origin": AUTHORED_PROJECTION_ORIGIN,
            }
        ],
        "components": [
            {
                "component_id": "meridian-engine",
                "label": "Meridian Engine",
                "responsibility": "Meridian Engine vitrifies the Æther packet into Ω-Receipt.",
                "projection_origin": AUTHORED_PROJECTION_ORIGIN,
            }
        ],
        "diagrams": [
            {
                "diagram_id": "D-701",
                "title": "Æther custody sequence",
                "projection_origin": AUTHORED_PROJECTION_ORIGIN,
            }
        ],
    }


def _accepted_preview() -> dict[str, object]:
    return {
        "accepted_at": "2026-08-31T12:00:00Z",
        "origin": "greenfield",
        "evidence_tier": "user_intent",
        "created": {
            "workstreams": [
                {"idea_id": "B-701", "title": "Preserve Æther custody"}
            ],
            "diagrams": ["D-701"],
        },
        "source_path": "odylith/runtime/source/accepted-project.v1.json",
        "validation_gate": {"status": "pass"},
    }


def _pronoun_proposal() -> dict[str, object]:
    proposal = _proposal()
    intent = deepcopy(proposal["intent"])
    first_event = "She QuOrates one Æther packet."
    second_event = "Meridian Engine vitrifies the Æther packet into Ω-Receipt."
    first_path = f"{first_event} {second_event}"
    second_start = len(f"{first_event} ".encode("utf-8"))
    second_end = second_start + len(second_event.encode("utf-8"))
    state_start = second_start + len("Meridian Engine vitrifies the ".encode("utf-8"))
    independent_start = len(first_path.encode("utf-8")) + 1
    relations = deepcopy(intent["authored_semantics"]["first_path_relations"])
    relations[0].update(
        {
            "source_start_byte": 0,
            "source_end_byte": len(first_event.encode("utf-8")),
            "event_start_byte": 0,
            "event_end_byte": len(first_event.encode("utf-8")),
            "actor_fact_path": "/human_actors/0",
            "actor_fact_quote": "Registry Custodian",
            "event_quote": first_event,
        }
    )
    relations[1].update(
        {
            "source_start_byte": second_start,
            "source_end_byte": second_end,
            "event_start_byte": second_start,
            "event_end_byte": second_end,
        }
    )
    contexts = deepcopy(intent["authored_semantics"]["first_path_context_relations"])
    contexts[0].update(
        {
            "source_start_byte": state_start,
            "source_end_byte": state_start + len("Æther packet".encode("utf-8")),
        }
    )
    contexts[1].update(
        {
            "source_start_byte": independent_start,
            "source_end_byte": independent_start + len("APIv7 Archive".encode("utf-8")),
        }
    )
    contexts[2].update(
        {
            "source_start_byte": contexts[1]["source_end_byte"] + 1,
            "source_end_byte": contexts[1]["source_end_byte"]
            + 1
            + len("Preserve APIv7 casing".encode("utf-8")),
        }
    )
    intent["first_path"] = first_path
    intent["authored_semantics"] = authored_semantics_mapping(
        relations,
        intent["authored_semantics"]["component_responsibility_relations"],
        first_path_context_relations=contexts,
    )
    proposal["intent"] = intent
    return proposal


def _completion_package(
    *,
    proposal: dict[str, object],
    dashboard: dict[str, object],
) -> GreenfieldCompletionPackage:
    return GreenfieldCompletionPackage(
        proposal=proposal,
        backlog_result={"created": [{"idea_id": "B-701"}]},
        project_dashboard_preview=dashboard,
        next_steps_preview={
            "start_workstream_id": "B-701",
            "verification_commands": ["verify-Ω --APIv7"],
        },
    )


def _assert_legacy_greenfield_owners_retired() -> None:
    for name in (
        "_dashboard_risk_source",
        "_text_rows",
        "_clean_labeled_text",
        "_non_goal_rows",
        "_lens",
        "_first_path",
        "summarize_first_path",
        "_project_intro",
        "_display_title",
        "_dashboard_open_items",
        "_claim_evidence",
        "_known",
        "_unknown",
        "_actors",
        "_jobs",
        "build_greenfield_product_story",
        "_risk_items",
        "_risk_classes",
        "build_source_launch_handoff",
        "_scenario_body",
        "_scenario_details",
        "_desired_state",
        "_host_handoff_prompts",
        "_governance_titles",
        "sentence",
        "complete_text",
        "dict_value",
        "list_value",
    ):
        assert not hasattr(greenfield, name)


def test_authored_dashboard_bypasses_legacy_projection_and_preserves_exact_facts(
    tmp_path: Path,
) -> None:
    _assert_legacy_greenfield_owners_retired()

    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=_proposal(),
        accepted_project_preview=_accepted_preview(),
        source_launch_context={
            "start_workstream_id": "B-701",
            "verification_commands": ["verify-Ω --APIv7"],
        },
    )

    assert payload["title"] == "eXact Ω Forge"
    assert payload["intro"] == PRODUCT_STORY
    assert payload["focus"] == FIRST_PATH
    assert payload["desired"] == "Ω-Receipt"
    assert payload["actors"] == [
        (
            "Human actor",
            "Registry Custodian",
            "Registry Custodian QuOrates one Æther packet.",
        ),
        (
            "Human actor",
            "Field Ombud",
            "Named in the model-authored product intent.",
        ),
    ]
    assert payload["scenario_details"] == [
        ("First path", FIRST_PATH),
        ("Visible result", "Ω-Receipt"),
        ("Proof boundary", PROOF_BOUNDARY),
    ]
    cards = {
        row["semantic_slot"]: row["body"]
        for row in payload["product_story"]["release_contract"]
    }
    assert cards["owned_capabilities"] == (
        "Meridian Engine: Meridian Engine vitrifies the Æther packet into Ω-Receipt."
    )
    assert cards["product_boundary"] == (
        "Product-owned systems:\nMeridian Engine\nExternal systems:\nAPIv7 Archive\n"
        "Excluded from the first release:\nBatch Æther migration"
    )
    assert payload["risk_items"] == []
    assert payload["risk_classes"] == []
    assert payload["governance_titles"] == {
        "B-701": "Preserve Æther custody",
        "D-701": "Æther custody sequence",
    }
    assert payload["projection"]["origin"] == AUTHORED_PROJECTION_ORIGIN
    assert payload["authored_facts"]["first_path"] == FIRST_PATH
    assert payload["authored_facts"]["human_actors"] == [
        "Registry Custodian",
        "Field Ombud",
    ]
    assert payload["authored_facts"]["first_path_relations"][0][
        "action_verb_quote"
    ] == "QuOrates"
    assert len(payload["authored_facts"]["first_path_context_relations"]) == 3
    assert len(payload["authored_facts"]["component_responsibility_relations"]) == 1
    prompts = payload["host_handoff_prompts"]
    assert isinstance(prompts, list)
    assert tuple(row["step_id"] for row in prompts) == EXPECTED_HANDOFF_STEPS
    expected_bindings = {
        "project_title": "eXact Ω Forge",
        "accepted_first_path": FIRST_PATH,
        "first_release_workstream_refs": ("B-701",),
        "proof_boundary": PROOF_BOUNDARY,
        "visible_result": "Ω-Receipt",
        "excluded_scope": ("Preserve APIv7 casing", "Batch Æther migration"),
        "component_refs": ("meridian-engine",),
        "verification_commands": ("verify-Ω --APIv7",),
    }
    for row, expected_step_id in zip(prompts, EXPECTED_HANDOFF_STEPS, strict=True):
        contract = row["contract"]
        assert contract["schema_version"] == PROJECT_HANDOFF_STEP_SCHEMA_VERSION
        assert contract["step_id"] == expected_step_id
        assert contract["semantic_authority"] == "typed_canonical_intent"
        assert contract["projection_policy"] == "structural_copy_only"
        assert contract["fact_bindings"] == expected_bindings
        assert project_handoff_step_contract_issues(
            contract,
            expected_step_id=expected_step_id,
        ) == ()
    assert FIRST_PATH in prompts[0]["prompt"]
    assert "QuOrates" in prompts[1]["prompt"]
    assert prompts[3]["verification_commands"] == ["verify-Ω --APIv7"]


def test_authored_dashboard_labels_assumptions_without_promoting_them_to_blockers(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    assumption = "The product title is the sole component owner until source names a subsystem."
    proposal["assumptions"] = [
        {"applies_to": "general", "assumption": assumption}
    ]

    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(),
        source_launch_context={
            "start_workstream_id": "B-701",
            "verification_commands": ["verify-Ω --APIv7"],
        },
    )

    assert payload["open_label"] == "Assumptions"
    assert payload["open"] == [assumption]
    assert payload["unknown"] == []
    assert payload["blockers"] == []


def test_authored_dashboard_validates_contracts_independently_of_visible_prompt_copy(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(),
        source_launch_context={
            "start_workstream_id": "B-701",
            "verification_commands": ["verify-Ω --APIv7"],
        },
    )
    prompts = payload["host_handoff_prompts"]
    assert isinstance(prompts, list)
    for index, row in enumerate(prompts, start=1):
        row["label"] = f"Reworded visible phase {index}"
        row["when"] = "Use this visible explanation whenever the typed gate permits it."
        row["prompt"] = "Follow the attached typed action and fact bindings."
        row["result"] = "The structurally declared output is produced."
        row["stop"] = "Honor the structurally declared stop policy."

    package = _completion_package(proposal=proposal, dashboard=payload)

    assert project_dashboard_preview_issues(
        package,
        payload,
        model_authored=True,
    ) == []

    corrupted = deepcopy(payload)
    corrupted_prompts = corrupted["host_handoff_prompts"]
    assert isinstance(corrupted_prompts, list)
    corrupted_contract = corrupted_prompts[1]["contract"]
    corrupted_contract["fact_bindings"]["project_title"] = "Reinterpreted project"

    issues = project_dashboard_preview_issues(
        _completion_package(proposal=proposal, dashboard=corrupted),
        corrupted,
        model_authored=True,
    )

    assert "model-authored Project handoff step 2 drifted from intent.title" in issues


def test_authored_dashboard_checks_exact_capability_view_value_without_punctuation_repair(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(),
        source_launch_context={
            "start_workstream_id": "B-701",
            "verification_commands": ["verify-Ω --APIv7"],
        },
    )

    capability_card = next(
        row
        for row in payload["product_story"]["release_contract"]
        if row["semantic_slot"] == "owned_capabilities"
    )
    assert capability_card["body"] == (
        "Meridian Engine: Meridian Engine vitrifies the Æther packet into Ω-Receipt."
    )

    capability_card["body"] = capability_card["body"].replace(":", ";", 1)
    issues = project_dashboard_preview_issues(
        _completion_package(proposal=proposal, dashboard=payload),
        payload,
        model_authored=True,
    )

    assert "model-authored Project dashboard drifted from typed owned_capabilities" in issues


def test_authored_dashboard_labels_provisional_problem_without_repeating_it(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    intent = deepcopy(proposal["intent"])
    assert isinstance(intent, dict)
    intent["problem"] = ""
    assumption = "Operators need a consistent way to preserve the packet receipt."
    intent["assumptions"] = [{"applies_to": "problem", "statement": assumption}]
    proposal["intent"] = intent
    proposal["assumptions"] = [{"applies_to": "problem", "assumption": assumption}]

    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(),
        source_launch_context={},
    )
    cards = {
        row["semantic_slot"]: row["body"]
        for row in payload["product_story"]["release_contract"]
    }

    assert cards["user_problem"] == f"Assumption — {assumption}"
    assert cards["user_problem"] != PRODUCT_STORY
    assert assumption not in payload["open"]


def test_authored_dashboard_uses_canonical_actor_fact_for_aliased_events(
    tmp_path: Path,
) -> None:
    proposal = _pronoun_proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(),
        source_launch_context={
            "start_workstream_id": "B-701",
            "verification_commands": ["verify-Ω --APIv7"],
        },
    )

    assert payload["actors"][0] == (
        "Human actor",
        "Registry Custodian",
        "She QuOrates one Æther packet.",
    )
    package = _completion_package(proposal=proposal, dashboard=payload)
    assert project_dashboard_preview_issues(
        package,
        payload,
        model_authored=True,
    ) == []

    corrupted = deepcopy(payload)
    corrupted["product_story"]["actors"][0]["body"] = (
        "Named in the model-authored product intent."
    )
    assert "model-authored Project dashboard drifted from typed actor identities" in (
        project_dashboard_preview_issues(
            _completion_package(proposal=proposal, dashboard=corrupted),
            corrupted,
            model_authored=True,
        )
    )


def test_authored_dashboard_projects_title_owned_capability_without_empty_cards(
    tmp_path: Path,
) -> None:
    first_path = (
        "Dock attendant Ivo enters a vessel tag. "
        "Harbor Desk records berth occupancy. "
        "Harbor Desk shows the placement."
    )
    intent = {
        "title": "Harbor Desk",
        "product_story": "Dock attendants need a reviewable berth placement.",
        "state_object": "berth occupancy",
        "first_path": first_path,
        "proof_boundary": "A reviewer verifies the recorded placement.",
        "problem": "Berth placement is hard to review.",
        "customer": "Dock attendants",
        "opportunity": "Keep one reviewable berth path.",
        "product_view": "Harbor Desk records and shows berth placement.",
        "success_metrics": ["The placement is visible."],
        "evidence_requirements": ["Replay the recorded placement."],
        "operational_constraints": [],
        "component_responsibilities": [],
        "human_actors": ["Dock attendant Ivo"],
        "external_systems": [],
        "internal_systems": [],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": [],
    }
    relations = (
        {
            "actor_kind": "human",
            "actor_fact_quote": "Dock attendant Ivo",
            "event_quote": "Dock attendant Ivo enters a vessel tag",
            "action_verb_quote": "enters",
            "target_quote": "vessel tag",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_fact_quote": "Harbor Desk",
            "owner_system_quote": "Harbor Desk",
            "event_quote": "Harbor Desk records berth occupancy",
            "action_verb_quote": "records",
            "target_quote": "berth occupancy",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_fact_quote": "Harbor Desk",
            "owner_system_quote": "Harbor Desk",
            "event_quote": "Harbor Desk shows the placement",
            "action_verb_quote": "shows",
            "target_quote": "placement",
            "visible_result_quote": "the placement",
        },
    )
    source = ". ".join(
        str(item)
        for value in intent.values()
        for item in (value if isinstance(value, list) else [value])
        if str(item)
    )
    authored = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                first_path_relations=relations,
                terminal_component_owner="Harbor Desk",
            )
        ),
        authoring_timeout_seconds=60,
        authoring_profile_id=STANDARD_PROFILE_ID,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1",
        confirmed_intent=authored,
    )
    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview={},
        source_launch_context={},
    )
    cards = {
        row["semantic_slot"]: row["body"]
        for row in payload["product_story"]["release_contract"]
    }

    assert cards["owned_capabilities"] == "Harbor Desk: the placement"
    assert cards["product_boundary"] == "Product-owned systems:\nHarbor Desk"
    assert all(cards.values())


def test_authored_dashboard_fails_closed_before_legacy_fallback(
    tmp_path: Path,
) -> None:
    _assert_legacy_greenfield_owners_retired()
    proposal = _proposal()
    intent = deepcopy(proposal["intent"])
    assert isinstance(intent, dict)
    intent["authored_semantics"] = {}
    proposal["intent"] = intent

    with pytest.raises(
        GreenfieldAuthoredSemanticsError,
        match="authored semantics are malformed",
    ):
        greenfield.build_greenfield_payload(proposal=proposal, repo_root=tmp_path)


def test_non_authored_proposal_fails_closed_without_a_legacy_owner(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    proposal["projection_origin"] = "legacy_projection"
    proposal.pop("_accepted_project", None)
    with pytest.raises(
        ValueError,
        match="requires a sealed authored projection",
    ):
        greenfield.build_greenfield_payload(proposal=proposal, repo_root=tmp_path)
