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
    render_selected_workstream_scope,
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
from odylith.runtime.domain_intelligence.greenfield_experience import build_next_steps
from odylith.runtime.project_intelligence import greenfield
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
    structural_design_fixture,
)


FIRST_PATH = (
    "Registry Custodian QuOrates one Æther packet. "
    "Meridian Engine vitrifies the Æther packet into Ω-Receipt."
)
PROPOSED_FIRST_RUN = (
    "Proposed first run:\nRegistry Custodian QuOrates one Æther packet.\n"
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
    """Unusual source semantics projected through the real canonical package builder."""
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
    intent = {
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
            provisional_design=structural_design_fixture((1, 2)),
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
    }
    return build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1", confirmed_intent=intent,
    )


def _accepted_preview(*, proposal: dict[str, object], root: Path) -> dict[str, object]:
    return {
        "accepted_at": "2026-08-31T12:00:00Z",
        "origin": "greenfield",
        "evidence_tier": "user_intent",
        "created": {
            "workstreams": [
                {"idea_id": f"B-{index:03d}", "title": row["title"],
                 "idea_path": str(root / f"workstream-{index}.md")}
                for index, row in enumerate(proposal["backlog"], 701)
            ],
            "diagrams": [f"D-{index:03d}" for index, _ in enumerate(proposal["diagrams"], 701)],
        },
        "source_path": "odylith/runtime/source/accepted-project.v1.json",
        "validation_gate": {"status": "pass"},
    }


def _source_launch_context(*, proposal: dict[str, object], root: Path) -> dict[str, object]:
    created = _accepted_preview(proposal=proposal, root=root)["created"]["workstreams"]
    return build_next_steps(
        proposal=proposal, backlog_result={"created": created},
        first_release_workstreams=tuple(row["idea_id"] for row in created),
        release_selector="0.0.1",
    )


def _handoff_scope_proposal(*, constraints: tuple[str, ...], non_goals: tuple[str, ...]) -> dict[str, object]:
    proposal = _proposal()
    intent = proposal["intent"]
    intent["operational_constraints"] = list(constraints)
    intent["non_goals"] = list(non_goals)
    contexts = intent["authored_semantics"]["first_path_context_relations"]
    contexts[:] = [row for row in contexts if row["context_kind"] != "operational_constraint"]
    cursor = max(row["source_end_byte"] for row in contexts) + 1
    for index, quote in enumerate(constraints):
        end = cursor + len(quote.encode("utf-8"))
        contexts.append({
            "context_kind": "operational_constraint", "fact_path": f"/operational_constraints/{index}",
            "fact_quote": quote, "source_start_byte": cursor, "source_end_byte": end,
            "first_path_event_order": 0,
        })
        cursor = end + 1
    return proposal


def _result_first_proposal(*, include_actor_review: bool = False) -> dict[str, object]:
    """Project projection control with source inventory deliberately nonchronological."""

    proposal = _proposal()
    intent = proposal["intent"]
    semantics = intent["authored_semantics"]
    relations = list(reversed(semantics["first_path_relations"]))
    if include_actor_review:
        review = {
            **relations[1],
            "event_quote": "Registry Custodian reviews Ω-Receipt.",
            "action_verb_quote": "reviews",
            "target_quote": "Ω-Receipt",
            "visible_result_quote": "Ω-Receipt",
        }
        relations[0]["visible_result_quote"] = ""
        relations = [review, relations[1], relations[0]]
    cursor = 0
    for order, row in enumerate(relations, start=1):
        end = cursor + len(row["event_quote"].encode("utf-8"))
        row.update(
            order=order, source_start_byte=cursor, source_end_byte=end,
            event_start_byte=cursor, event_end_byte=end,
        )
        cursor = end + 1
    intent["first_path"] = " ".join(row["event_quote"] for row in relations)
    semantics["first_path_relations"] = relations
    if include_actor_review:
        semantics["provisional_design"] = structural_design_fixture((1, 2, 3))
    semantics["provisional_design"]["first_run"] = {
        "event_orders": [2, 3, 1] if include_actor_review else [2, 1],
        "rationale": "Prepare the packet and produce its receipt before the final result review.",
    }
    product_event_order = 3 if include_actor_review else 1
    state_start = relations[product_event_order - 1]["source_start_byte"] + len(
        "Meridian Engine vitrifies the ".encode("utf-8")
    )
    semantics["first_path_context_relations"][0].update(
        first_path_event_order=product_event_order, source_start_byte=state_start,
        source_end_byte=state_start + len("Æther packet".encode("utf-8")),
    )
    independent_start = len(intent["first_path"].encode("utf-8")) + 1
    for context in semantics["first_path_context_relations"][1:]:
        context["source_start_byte"] = independent_start
        context["source_end_byte"] = independent_start + len(context["fact_quote"].encode("utf-8"))
        independent_start = context["source_end_byte"] + 1
    return proposal


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
        provisional_design=intent["authored_semantics"]["provisional_design"],
    )
    proposal["intent"] = intent
    return proposal


def _completion_package(
    *,
    proposal: dict[str, object],
    dashboard: dict[str, object],
    root: Path,
) -> GreenfieldCompletionPackage:
    accepted = _accepted_preview(proposal=proposal, root=root)
    created = accepted["created"]["workstreams"]
    return GreenfieldCompletionPackage(
        proposal=proposal,
        backlog_result={"created": created},
        release_workstream_ids=tuple(row["idea_id"] for row in created),
        project_dashboard_preview=dashboard,
        next_steps_preview=_source_launch_context(proposal=proposal, root=root),
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
    proposal = _proposal()

    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )

    assert payload["title"] == "eXact Ω Forge"
    assert payload["intro"] == PRODUCT_STORY
    assert payload["focus"] == PROPOSED_FIRST_RUN
    assert payload["desired"] == "Ω-Receipt"
    assert payload["actors"] == [
        (
            "Human actor",
            "Registry Custodian",
            "Registry Custodian QuOrates one Æther packet.",
        ),
        (
            "Participant",
            "Field Ombud",
            "Named in project evidence; no first-path action is assigned.",
        ),
    ]
    assert payload["scenario_details"] == [
        ("Proposed first run", PROPOSED_FIRST_RUN),
        ("Visible result", "Ω-Receipt"),
        ("Proof boundary", PROOF_BOUNDARY),
    ]
    cards = {
        row["semantic_slot"]: row["body"]
        for row in payload["product_story"]["release_contract"]
    }
    design = proposal["intent"]["authored_semantics"]["provisional_design"]
    assert cards["owned_capabilities"] == "\n".join([
        "Proposed capabilities:",
        *(f"{row['name']}: {row['responsibility']}" for row in design["components"]),
    ])
    assert cards["product_boundary"] == (
        "Proposed logical components (not deployment commitments):\n"
        + "\n".join(row["name"] for row in design["components"]) + "\n"
        "Source-stated systems:\nMeridian Engine\nExternal systems:\nAPIv7 Archive\n"
        "Excluded from the first release:\nBatch Æther migration"
    )
    assert payload["risk_items"] == []
    assert payload["risk_classes"] == []
    assert payload["governance_titles"] == {
        **{f"B-{index:03d}": row["title"] for index, row in enumerate(proposal["backlog"], 701)},
        **{f"D-{index:03d}": row["title"] for index, row in enumerate(proposal["diagrams"], 701)},
    }
    assert payload["projection"]["origin"] == AUTHORED_PROJECTION_ORIGIN
    assert payload["authored_facts"]["first_path"] == FIRST_PATH
    assert payload["authored_facts"]["source_precedence"] == []
    assert payload["authored_facts"]["human_actors"] == [
        "Registry Custodian",
        "Field Ombud",
    ]
    assert payload["authored_facts"]["first_path_relations"][0][
        "action_verb_quote"
    ] == "QuOrates"
    assert len(payload["authored_facts"]["first_path_context_relations"]) == 3
    assert payload["authored_facts"]["component_responsibility_relations"] == []
    assert payload["authored_facts"]["first_path_relations"][1][
        "owner_system_quote"
    ] == "Meridian Engine"
    prompts = payload["host_handoff_prompts"]
    assert isinstance(prompts, list)
    assert tuple(row["step_id"] for row in prompts) == EXPECTED_HANDOFF_STEPS
    expected_bindings = {
        "project_title": "eXact Ω Forge",
        "accepted_first_path": PROPOSED_FIRST_RUN,
        "first_release_workstream_refs": ("B-701", "B-702", "B-703", "B-704"),
        "implementation_target": _source_launch_context(proposal=proposal, root=tmp_path)["implementation_target"],
        "proof_boundary": PROOF_BOUNDARY,
        "visible_result": "Ω-Receipt",
        "operational_constraints": ("Preserve APIv7 casing",),
        "excluded_scope": ("Batch Æther migration",),
        "component_refs": tuple(row["key"] for row in design["components"]),
        "verification_commands": tuple(_source_launch_context(proposal=proposal, root=tmp_path)["verification_commands"]),
    }
    for row, expected_step_id in zip(prompts, EXPECTED_HANDOFF_STEPS, strict=True):
        contract = row["contract"]
        assert contract["schema_version"] == PROJECT_HANDOFF_STEP_SCHEMA_VERSION
        assert contract["step_id"] == expected_step_id
        assert contract["semantic_authority"] == "typed_canonical_intent"
        assert contract["projection_policy"] == "structural_copy_only"
        assert contract["fact_bindings"] == expected_bindings
        assert row["prompt"].startswith(render_selected_workstream_scope(expected_bindings["implementation_target"]))
        assert project_handoff_step_contract_issues(
            contract,
            expected_step_id=expected_step_id,
        ) == ()
    assert PROPOSED_FIRST_RUN in prompts[0]["prompt"]
    assert "QuOrates" in prompts[1]["prompt"]
    assert prompts[3]["verification_commands"] == list(expected_bindings["verification_commands"])


@pytest.mark.parametrize("constraints,non_goals", [
    (("Preserve APIv7 casing",), ()),
    ((), ("Batch Æther migration",)),
    (("Preserve APIv7 casing",), ("Batch Æther migration",)),
    (("Preserve APIv7 casing", "Preserve APIv7 casing"), ()),
    ((), ()),
])
def test_authored_handoff_exposes_operating_requirements_and_only_non_goals_as_exclusions(
    tmp_path: Path, constraints: tuple[str, ...], non_goals: tuple[str, ...],
) -> None:
    proposal = _handoff_scope_proposal(constraints=constraints, non_goals=non_goals)
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    expected_scope = (
        "Operational constraints — preserve these requirements:\n"
        + ("\n".join(constraints) if constraints else "None stated.")
        + "\n\nExcluded scope — preserve these exclusions:\n"
        + ("\n".join(non_goals) if non_goals else "None stated.")
    )
    for handoff in payload["host_handoff_prompts"]:
        bindings = handoff["contract"]["fact_bindings"]
        assert bindings["operational_constraints"] == constraints
        assert bindings["excluded_scope"] == non_goals
        assert handoff["prompt"].endswith(expected_scope)
    assert project_dashboard_preview_issues(
        _completion_package(proposal=proposal, dashboard=payload, root=tmp_path), payload, model_authored=True,
    ) == []


@pytest.mark.parametrize("damage", [
    "swap_bindings", "drop_constraints", "drop_exclusions", "swap_copy", "swap_both", "drop_copy",
])
def test_authored_handoff_preconfirm_rejects_lost_or_swapped_scope_categories(
    tmp_path: Path, damage: str,
) -> None:
    proposal = _proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)
    assert project_dashboard_preview_issues(package, payload, model_authored=True) == []
    handoff = payload["host_handoff_prompts"][1]
    bindings = handoff["contract"]["fact_bindings"]
    if damage in {"swap_bindings", "swap_both"}:
        bindings["operational_constraints"], bindings["excluded_scope"] = (
            bindings["excluded_scope"], bindings["operational_constraints"],
        )
    elif damage == "drop_constraints":
        bindings.pop("operational_constraints", None)
    elif damage == "drop_exclusions":
        bindings.pop("excluded_scope")
    if damage in {"swap_copy", "swap_both"}:
        handoff["prompt"] = (
            "Create the implementation plan.\n\n"
            "Operational constraints — preserve these requirements:\nBatch Æther migration\n\n"
            "Excluded scope — preserve these exclusions:\nPreserve APIv7 casing"
        )
    elif damage == "drop_copy":
        handoff["prompt"] = "Create the implementation plan."
    issues = project_dashboard_preview_issues(package, payload, model_authored=True)
    assert any("step 2" in issue and ("scope" in issue or "operational constraints" in issue) for issue in issues)


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
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )

    assert payload["open_label"] == "Assumptions"
    assert payload["open"] == [assumption]
    assert payload["unknown"] == []
    assert payload["blockers"] == []


def test_authored_dashboard_separates_proposed_walkthrough_from_result_first_source(
    tmp_path: Path,
) -> None:
    proposal = _result_first_proposal()
    source_intent = deepcopy(proposal["intent"])
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )

    assert payload["focus"] == PROPOSED_FIRST_RUN
    assert payload["scenario_details"][0] == ("Proposed first run", PROPOSED_FIRST_RUN)
    assert payload["desired"] == "Ω-Receipt"
    assert payload["authored_facts"]["first_path"] == source_intent["first_path"]
    assert payload["authored_facts"]["first_path_relations"] == source_intent["authored_semantics"]["first_path_relations"]
    assert payload["authored_facts"]["source_precedence"] == source_intent["authored_semantics"]["source_precedence"]
    assert [row["order"] for row in payload["authored_facts"]["first_path_relations"]] == [1, 2]
    cards = {row["semantic_slot"]: row["body"] for row in payload["product_story"]["release_contract"]}
    assert cards["first_path"] == PROPOSED_FIRST_RUN
    for prompt in payload["host_handoff_prompts"]:
        assert prompt["contract"]["fact_bindings"]["accepted_first_path"] == PROPOSED_FIRST_RUN
    assert proposal["intent"] == source_intent


def test_authored_dashboard_preserves_archive_after_the_published_result(tmp_path: Path) -> None:
    events = (
        "Coordinator publishes a report.",
        "Coordinator archives the report evidence.",
    )
    constraint = "Coordinator publishes the report before archiving its evidence."
    intent = {
        "title": "Report Desk",
        "product_story": "Coordinators publish reviewable reports and retain their evidence.",
        "problem": "Report evidence is lost after publication.",
        "customer": "Coordinator",
        "opportunity": "Keep published reports and evidence reviewable together.",
        "product_view": "A report publication and evidence retention workspace.",
        "first_path": " ".join(events),
        "state_object": "report",
        "proof_boundary": "The published report is visible and its evidence can be retrieved.",
        "human_actors": ["Coordinator"],
        "internal_systems": [], "external_systems": [],
        "component_responsibilities": [], "assumptions": [], "ambiguities": [],
        "non_goals": [], "operational_constraints": [constraint],
        "evidence_requirements": ["Retrieve the archived report evidence."],
        "success_metrics": ["The published report remains visible."],
    }
    relations = tuple(
        {
            "actor_kind": "human", "actor_fact_quote": "Coordinator",
            "event_quote": event, "action_verb_quote": action, "target_quote": target,
            "visible_result_quote": "report" if index == 0 else "",
        }
        for index, (event, action, target) in enumerate(zip(
            events, ("publishes", "archives"), ("a report", "report evidence"), strict=True,
        ))
    )
    precedence = [{"before_event": 1, "after_event": 2, "constraint_index": 1}]
    source = "\n".join(
        str(item) for value in intent.values()
        for item in (value if isinstance(value, list) else [value]) if str(item)
    )
    authored = materialize_model_authored_intent(
        prompt=source, repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(authored_response(
            intent, evidence_text=source, first_path_relations=relations,
            source_precedence=precedence,
        )),
        authoring_timeout_seconds=60, authoring_profile_id=STANDARD_PROFILE_ID,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1", confirmed_intent=authored,
    )
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    proposed_run = "Proposed first run:\n" + "\n".join(events)
    assert payload["focus"] == proposed_run
    assert payload["desired"] == "report"
    assert payload["authored_facts"]["visible_result"] == "report"
    assert payload["authored_facts"]["source_precedence"] == precedence
    assert [row["visible_result_quote"] for row in payload["authored_facts"]["first_path_relations"]] == ["report", ""]
    assert payload["actors"][0][2] == "\n".join(events)
    cards = {row["semantic_slot"]: row["body"] for row in payload["product_story"]["release_contract"]}
    assert cards["first_path"] == proposed_run
    for handoff in payload["host_handoff_prompts"]:
        assert handoff["contract"]["fact_bindings"]["accepted_first_path"] == proposed_run
    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)
    assert project_dashboard_preview_issues(package, payload, model_authored=True) == []


@pytest.mark.parametrize("mutation", ["source_precedence", "first_path"])
def test_authored_dashboard_preconfirm_rejects_order_authority_drift(
    tmp_path: Path, mutation: str,
) -> None:
    proposal = _result_first_proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)
    assert project_dashboard_preview_issues(package, payload, model_authored=True) == []
    if mutation == "source_precedence":
        payload["authored_facts"]["source_precedence"] = [
            {"before_event": 2, "after_event": 1, "constraint_index": 1},
        ]
        expected_issue = "model-authored Project dashboard drifted from source prerequisites"
    else:
        card = next(
            row for row in payload["product_story"]["release_contract"] if row["semantic_slot"] == "first_path"
        )
        card["body"] = proposal["intent"]["first_path"]
        expected_issue = "model-authored Project dashboard drifted from typed first_path"
    assert expected_issue in project_dashboard_preview_issues(package, payload, model_authored=True)


def test_authored_dashboard_same_actor_cards_follow_proposed_order_and_preconfirm_parity(
    tmp_path: Path,
) -> None:
    proposal = _result_first_proposal(include_actor_review=True)
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    expected = "Registry Custodian QuOrates one Æther packet.\nRegistry Custodian reviews Ω-Receipt."
    assert payload["actors"][0][2] == expected
    assert payload["product_story"]["actors"][0]["body"] == expected
    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)
    assert project_dashboard_preview_issues(package, payload, model_authored=True) == []
    source_actor_order = "\n".join(
        row["event_quote"] for row in payload["authored_facts"]["first_path_relations"]
        if row["actor_kind"] == "human"
    )
    assert source_actor_order != expected
    payload["product_story"]["actors"][0]["body"] = source_actor_order
    assert "model-authored Project dashboard drifted from typed actor identities" in (
        project_dashboard_preview_issues(package, payload, model_authored=True)
    )


def test_authored_dashboard_validates_contracts_independently_of_introductory_prompt_copy(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    prompts = payload["host_handoff_prompts"]
    assert isinstance(prompts, list)
    for index, row in enumerate(prompts, start=1):
        row["label"] = f"Reworded visible phase {index}"
        row["when"] = "Use this visible explanation whenever the typed gate permits it."
        row["prompt"] = (
            render_selected_workstream_scope(row["contract"]["fact_bindings"]["implementation_target"]) + "\n\n"
            "Follow the attached typed action and fact bindings.\n\n"
            "Operational constraints — preserve these requirements:\nPreserve APIv7 casing\n\n"
            "Excluded scope — preserve these exclusions:\nBatch Æther migration"
        )
        row["result"] = "The structurally declared output is produced."
        row["stop"] = "Honor the structurally declared stop policy."

    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)

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
        _completion_package(proposal=proposal, dashboard=corrupted, root=tmp_path),
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
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )

    capability_card = next(
        row
        for row in payload["product_story"]["release_contract"]
        if row["semantic_slot"] == "owned_capabilities"
    )
    design = proposal["intent"]["authored_semantics"]["provisional_design"]
    assert capability_card["body"] == "\n".join([
        "Proposed capabilities:",
        *(f"{row['name']}: {row['responsibility']}" for row in design["components"]),
    ])

    capability_card["body"] = capability_card["body"].replace(":", ";", 1)
    issues = project_dashboard_preview_issues(
        _completion_package(proposal=proposal, dashboard=payload, root=tmp_path),
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
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
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
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )

    assert payload["actors"][0] == (
        "Human actor",
        "Registry Custodian",
        "She QuOrates one Æther packet.",
    )
    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)
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
            _completion_package(proposal=proposal, dashboard=corrupted, root=tmp_path),
            corrupted,
            model_authored=True,
        )
    )


def test_authored_dashboard_projects_proposed_capabilities_without_changing_source_actors(
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
        "human_actors": ["Dock attendant Ivo", "Port observer"],
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

    design = authored["authored_semantics"]["provisional_design"]
    assert cards["owned_capabilities"] == "\n".join([
        "Proposed capabilities:",
        *(f"{row['name']}: {row['responsibility']}" for row in design["components"]),
    ])
    assert cards["product_boundary"] == "\n".join([
        "Proposed logical components (not deployment commitments):",
        *(row["name"] for row in design["components"]),
    ])
    assert all(cards.values())
    assert proposal["intent"]["human_actors"] == ["Dock attendant Ivo", "Port observer"]
    assert proposal["project_intelligence"]["operators"] == ["Dock attendant Ivo"]
    assert payload["participants"][1] == (
        "Participant", "Port observer",
        "Named in project evidence; no first-path action is assigned.",
    )


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
