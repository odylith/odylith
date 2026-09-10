"""Keep source citation identity separate from a proposed executable first run."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_first_run import (
    authored_first_run_relations,
    authored_first_run_text,
)
from odylith.runtime.domain_intelligence.artifact_graph import canonical_graph_from_workstream
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    first_path_relations_from_intent,
    require_relation_authority_parity,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import (
    candidate_intent_stage_paths,
)
from odylith.runtime.domain_intelligence.greenfield_experience import (
    build_next_steps,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
    render_product_intent_preview,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    product_facts_payload,
)
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    semantic_diagram_alignment_issues,
)
from odylith.runtime.domain_intelligence.proposal_validation import validate_host_reasoned_proposal
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    StructuredAuthoringProvider,
    authored_response,
    structural_design_fixture,
)


def _result_first_response(*, include_precedence=True, archive_after_result=False):
    events = [
        dict(actor_kind="product", owner_system_quote="Receipt Desk",
             event_quote="Receipt Desk publishes the review receipt", action_verb_quote="publishes",
             target_quote="the review receipt", visible_result_quote="the review receipt"),
        dict(actor_kind="human", actor_fact_quote="Reviewer Mara",
             event_quote="Reviewer Mara records one draft", action_verb_quote="records",
             target_quote="one draft", visible_result_quote=""),
        dict(actor_kind="product", owner_system_quote="Receipt Desk",
             event_quote="Receipt Desk validates one draft", action_verb_quote="validates",
             target_quote="one draft", visible_result_quote=""),
    ]
    if archive_after_result:
        events[2] = dict(actor_kind="product", owner_system_quote="Receipt Desk",
            event_quote="Receipt Desk archives the review receipt", action_verb_quote="archives",
            target_quote="the review receipt", visible_result_quote="")
    constraints = ([
        "Reviewer Mara must record one draft before Receipt Desk publishes the review receipt",
        "Receipt Desk must publish the review receipt before it archives the review receipt",
    ] if archive_after_result else [
        "Reviewer Mara must record one draft before Receipt Desk validates one draft",
    ])
    precedence = ([
        {"before_event": 2, "after_event": 1, "constraint_index": 1},
        {"before_event": 1, "after_event": 3, "constraint_index": 2},
    ] if archive_after_result else [{"before_event": 2, "after_event": 3, "constraint_index": 1}])
    intent = dict(
        title="Receipt Desk", product_story="Receipt Desk supports a complete draft review",
        state_object="one draft", first_path=". ".join(row["event_quote"] for row in events),
        proof_boundary="the review receipt", problem="Scattered drafts delay reviews",
        customer="Reviewer Mara", opportunity="A shared receipt would reduce rework",
        product_view="Receipt Desk keeps a complete review trail", human_actors=["Reviewer Mara"],
        external_systems=[], internal_systems=[], component_responsibilities=[], assumptions=[],
        ambiguities=[], success_metrics=[], evidence_requirements=[], non_goals=[],
        operational_constraints=constraints,
    )
    source = ". ".join(str(row) for value in intent.values()
                       for row in (value if isinstance(value, list) else [value]) if row)
    design = structural_design_fixture((1, 2, 3),
        first_run_event_orders=(2, 1, 3) if archive_after_result else (2, 3, 1))
    design["first_run"]["rationale"] = (
        "Record the draft, publish its receipt, then archive it as the source requires."
        if archive_after_result else
        "Propose recording the draft, validating it, then publishing the receipt; "
        "the source only explicitly orders recording before validation."
    )
    response = authored_response(
        intent, evidence_text=source, first_path_relations=events, provisional_design=design,
        **({"source_precedence": precedence}
           if include_precedence else {}),
    )
    return source, response, events


def test_post_result_action_survives_authoring_custody_and_all_projections(tmp_path):
    source, response, events = _result_first_response(archive_after_result=True)
    provider = StructuredAuthoringProvider(response)
    candidate = materialize_model_authored_intent(
        prompt=source, repo_root=tmp_path, authoring_provider=provider,
        review_provider_factory=AdmittingReviewProvider,
    )
    assert provider.calls == 1
    relations = require_relation_authority_parity(candidate, candidate[PRODUCT_INTENT_AUTHORITY_KEY])
    assert relations[0]["visible_result_quote"] == "the review receipt"
    assert not relations[2]["visible_result_quote"]
    proposal = build_greenfield_proposal(repo_root=tmp_path, prompt=source,
        release_selector="0.0.1", confirmed_intent=candidate, require_completion_ready=False)
    validate_host_reasoned_proposal(proposal)
    assert semantic_diagram_alignment_issues(proposal, proposal["semantic_model"]) == []
    run = proposal["semantic_model"]["first_path_contract"]["events"]
    assert [row["source_event_order"] for row in run] == [2, 1, 3]
    assert [row["visible_result"] for row in run] == [False, True, False]
    atlas = proposal["diagrams"][1]["mermaid_source"]
    assert 'event1 -->|"source constraint 2"| event3' in atlas
    assert 'event3 -. "proposed next step" .-> event1' not in atlas
    for owner, contract in (("components", "component_contract"), ("backlog", "provisional_workstream_contract")):
        supported = [event["event_quote"] for row in proposal[owner] for event in row[contract]["supporting_events"]]
        assert events[2]["event_quote"] in supported
    created = [{"idea_id": f"B-{index:03d}", "title": row["title"], "idea_path": str(tmp_path / f"workstream-{index}.md")}
               for index, row in enumerate(proposal["backlog"], 1)]
    handoff = build_next_steps(proposal=proposal, backlog_result={"created": created},
        first_release_workstreams=tuple(row["idea_id"] for row in created), release_selector="0.0.1")
    proposed = authored_first_run_text(candidate)
    assert proposed.endswith(events[2]["event_quote"])
    assert handoff["coding_readiness_contract"]["source_facts"]["accepted_first_path"] == proposed
    assert proposed in render_product_intent_preview(candidate)


@pytest.fixture
def ordered_package(tmp_path):
    source, response, events = _result_first_response()
    provider = StructuredAuthoringProvider(response)
    candidate = materialize_model_authored_intent(
        prompt=source, repo_root=tmp_path, authoring_provider=provider,
        review_provider_factory=AdmittingReviewProvider,
    )
    assert provider.calls == 1
    proposal = build_greenfield_proposal(
        repo_root=tmp_path, prompt=source, release_selector="0.0.1",
        confirmed_intent=candidate, require_completion_ready=False,
    )
    validate_host_reasoned_proposal(proposal)
    assert candidate["prompt"].endswith(source + "\n")
    return candidate["prompt"], candidate, proposal, events


def test_citation_identity_survives_proposed_reordering_and_sealed_custody(ordered_package):
    source, candidate, _, events = ordered_package
    source_relations = first_path_relations_from_intent(candidate)
    proposed_relations = authored_first_run_relations(candidate)
    assert [row["order"] for row in source_relations] == [1, 2, 3]
    assert [row["order"] for row in proposed_relations] == [2, 3, 1]
    assert candidate["first_path"] == "\n".join(row["event_quote"] for row in events)
    assert candidate["authored_semantics"]["source_precedence"] == [
        {"before_event": 2, "after_event": 3, "constraint_index": 1},
    ]
    assert source_relations[0]["visible_result_quote"] == "the review receipt"
    assert all(not row["visible_result_quote"] for row in source_relations[1:])
    for row in source_relations:
        assert source.encode()[row["source_start_byte"]:row["source_end_byte"]].decode() == row["event_quote"]
    assert require_relation_authority_parity(
        candidate, candidate[PRODUCT_INTENT_AUTHORITY_KEY],
    ) == source_relations
    assert "source_precedence" not in product_facts_payload(candidate)
    assert "first_run" not in product_facts_payload(candidate)

    changed = deepcopy(candidate)
    changed["authored_semantics"]["source_precedence"] = []
    with pytest.raises(ValueError, match="do not match sealed"):
        require_relation_authority_parity(changed, candidate[PRODUCT_INTENT_AUTHORITY_KEY])


def test_project_and_semantic_views_use_the_labeled_proposed_run(ordered_package):
    _, candidate, proposal, events = ordered_package
    proposed = "Proposed first run:\n" + "\n".join(events[index - 1]["event_quote"] for index in (2, 3, 1))
    assert authored_first_run_text(candidate) == proposed
    assert proposal["project_intelligence"]["scope"] == [proposed]
    assert any(row["must_capture"] == proposed for row in proposal["project_brief"]["blueprint_sections"])
    contract = proposal["semantic_model"]["first_path_contract"]
    assert contract["raw_path"] == proposed
    assert contract["capability"] == proposed
    assert [row["text"] for row in contract["events"]] == [events[index - 1]["event_quote"] for index in (2, 3, 1)]
    assert [row["source_event_order"] for row in contract["events"]] == [2, 3, 1]
    assert [row["index"] for row in contract["events"]] == [1, 2, 3]
    assert contract["events"][-1]["visible_result"] is True
    assert len(proposal["components"]) == len(proposal["backlog"]) == 4
    assert len(proposal["diagrams"]) >= 5


def test_cli_and_staged_markdown_show_the_proposed_run_without_rewriting_source_facts(
    ordered_package, tmp_path,
):
    _, candidate, _, _ = ordered_package
    proposed = authored_first_run_text(candidate)
    stage = candidate_intent_stage_paths(tmp_path)
    for view in (render_product_intent_preview(candidate), stage.markdown.read_text()):
        assert "## First complete path\nProposed first run:\n" in view
        assert proposed in view
        assert "## First complete path\n" + candidate["first_path"] not in view


def test_atlas_proposes_order_but_registry_and_radar_keep_source_support_ids(ordered_package):
    _, _, proposal, events = ordered_package
    sequence = next(row for row in proposal["diagrams"] if row["slug"] == "receipt-desk-first-path")
    assert sequence["authority_kind"] == "provisional_design"
    mermaid = sequence["mermaid_source"]
    assert 'event2 -->|"source constraint 1"| event3' in mermaid
    assert 'event3 -. "proposed next step" .-> event1' in mermaid
    assert 'event2 -. "proposed next step" .-> event3' not in mermaid
    assert "event3 --> event1" not in mermaid
    assert "event1 --> event2" not in mermaid
    assert "source order" not in sequence["summary"].casefold()
    for owner, contract_key in (("components", "component_contract"), ("backlog", "provisional_workstream_contract")):
        for row in proposal[owner]:
            contract = row[contract_key]
            for ref, support in zip(contract["support_event_refs"], contract["supporting_events"], strict=True):
                assert ref == f"/authored_semantics/first_path_relations/{support['order'] - 1}"
                assert support["event_quote"] == events[support["order"] - 1]["event_quote"]


def test_implementation_handoffs_follow_the_same_proposed_walk(ordered_package, tmp_path):
    _, candidate, proposal, _ = ordered_package
    proposed = authored_first_run_text(candidate)
    created = [{"idea_id": f"B-{index:03d}", "title": row["title"], "idea_path": str(tmp_path / f"workstream-{index}.md")}
               for index, row in enumerate(proposal["backlog"], 1)]
    workstreams = tuple(row["idea_id"] for row in created)
    handoff = build_next_steps(
        proposal=proposal, backlog_result={"created": created},
        first_release_workstreams=workstreams, release_selector="0.0.1",
    )
    assert proposed in handoff["implementation_prompt"]
    assert handoff["coding_readiness_contract"]["source_facts"]["accepted_first_path"] == proposed


def test_shared_fixture_never_derives_source_precedence_from_delivery_dependencies():
    _, response, _ = _result_first_response(include_precedence=False)
    assert response["result"]["provisional_design"]["workstreams"][1]["depends_on"]
    assert response["result"]["source_precedence"] == []
    assert response["result"]["terminal"]["event_order"] == 1


def test_artifact_workflow_uses_the_canonical_proposed_walk(ordered_package):
    _, candidate, proposal, _ = ordered_package
    row = proposal["backlog"][0]
    graph = canonical_graph_from_workstream(row=row, proposal=proposal)

    assert graph.workflows == (
        authored_first_run_text(candidate), row["recommended_first_slice"],
    )
    assert candidate["first_path"] not in graph.workflows


def test_non_authored_artifact_workflow_preserves_its_existing_projection():
    graph = canonical_graph_from_workstream(
        proposal={"intent": {"title": "Existing project", "first_path": "Record a draft\nthen review it"}},
        row={"recommended_first_slice": "  Review one draft  "},
    )

    assert graph.workflows == ("Record a draft then review it", "Review one draft")


def test_preconfirm_event_alignment_accepts_the_canonical_proposed_run(ordered_package):
    _, _, proposal, _ = ordered_package

    assert semantic_diagram_alignment_issues(proposal, proposal["semantic_model"]) == []


@pytest.mark.parametrize("damage", ["order", "text", "source_id", "source_kind", "boolean_id"])
def test_synchronized_event_drift_cannot_pass_by_agreeing_with_itself(ordered_package, damage):
    _, _, proposal, _ = ordered_package
    semantic = deepcopy(proposal["semantic_model"])
    changed = deepcopy(semantic["first_path_contract"]["events"])
    if damage == "order":
        changed = sorted(changed, key=lambda row: row["source_event_order"])
        for index, row in enumerate(changed, 1):
            row["index"] = index
    elif damage == "text":
        changed[0]["text"] = "A different, unsupported event"
    elif damage == "source_id":
        changed[0]["source_event_order"] = 1
    elif damage == "source_kind":
        changed[0]["source_kind"] = "accepted_first_path"
    else:
        changed[-1]["source_event_order"] = True
    semantic["first_path_contract"]["events"] = changed
    semantic["diagram_event_graph"]["events"] = deepcopy(changed)

    issues = semantic_diagram_alignment_issues(proposal, semantic)

    assert any("FirstPathContract events" in issue for issue in issues)
    assert any("DiagramEventGraph events" in issue for issue in issues)


@pytest.mark.parametrize("damage", ["authority", "precedence", "design"])
def test_preconfirm_rejects_reinterpreted_order_authority(ordered_package, damage):
    _, _, proposal, _ = ordered_package
    semantic = deepcopy(proposal["semantic_model"])
    if damage == "authority":
        semantic["first_path_contract"]["authority_kind"] = "source_grounded"
    elif damage == "precedence":
        semantic["source_precedence"] = []
    else:
        semantic["provisional_design"]["first_run"]["rationale"] = "A different proposed rationale"

    assert semantic_diagram_alignment_issues(proposal, semantic)
