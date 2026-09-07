"""Source precedence is cited authority; a first-run sequence remains design."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_event_ordering import (
    FIRST_RUN_SCHEMA,
    SOURCE_PRECEDENCE_SCHEMA,
    validate_first_run,
    validate_source_precedence,
)


def _edge(before=2, after=1, constraint=1):
    return {"before_event": before, "after_event": after, "constraint_index": constraint}


def _validate(edges, *, events=(1, 2, 3), constraints=("Publish only after review.",)):
    return validate_source_precedence(
        edges, event_orders=events, operational_constraints=constraints,
    )


def _walk(orders=(3, 2, 1)):
    return {"event_orders": list(orders), "rationale": "Prepare and review before publication."}


def test_unordered_capabilities_do_not_acquire_source_edges():
    assert _validate([]) == ()
    for orders in ((2, 3, 1), (3, 2, 1)):
        assert validate_first_run(
            _walk(orders), event_orders=(1, 2, 3), source_precedence=(), result_event_order=1,
        ) == _walk(orders)


def test_partial_precedence_leaves_independent_preparations_unordered():
    edges = _validate([_edge(2), _edge(3)])
    for orders in ((2, 3, 1), (3, 2, 1)):
        assert validate_first_run(
            _walk(orders), event_orders=(1, 2, 3), source_precedence=edges, result_event_order=1,
        ) == _walk(orders)


def test_precedence_retains_the_64_edge_prototype_bound():
    events = tuple(range(1, 14))
    edges = [_edge(before, after) for after in events for before in events if before < after]
    assert SOURCE_PRECEDENCE_SCHEMA["maxItems"] == 64
    assert _validate(edges[:64], events=events) == tuple(edges[:64])
    with pytest.raises(ValueError, match="edge list"):
        _validate(edges[:65], events=events)
    assert validate_first_run(
        _walk(events), event_orders=events, source_precedence=edges[:64], result_event_order=13,
    ) == _walk(events)
    with pytest.raises(ValueError, match="edge list"):
        validate_first_run(
            _walk(events), event_orders=events, source_precedence=edges[:65], result_event_order=13,
        )


def test_first_run_retains_the_1000_character_rationale_prototype_bound():
    assert FIRST_RUN_SCHEMA["properties"]["rationale"]["maxLength"] == 1000
    walk = {**_walk(), "rationale": "x" * 1000}
    assert validate_first_run(
        walk, event_orders=(1, 2, 3), source_precedence=(), result_event_order=1,
    ) == walk
    with pytest.raises(ValueError, match="rationale"):
        validate_first_run(
            {**walk, "rationale": "x" * 1001}, event_orders=(1, 2, 3),
            source_precedence=(), result_event_order=1,
        )


@pytest.mark.parametrize("edges", [
    None, {}, "2 before 1", [_edge(0)], [_edge(True)], [_edge(4)],
    [_edge(after=4)], [_edge(constraint=0)], [_edge(constraint=True)],
    [_edge(constraint=2)], [_edge(1)], [_edge(), _edge()],
    [_edge(), _edge(1, 2)], [{**_edge(), "quote": "Publish only after review."}],
    [{"before_event": 2, "after_event": 1}],
])
def test_invalid_source_precedence_fails_closed(edges):
    with pytest.raises(ValueError):
        _validate(edges)


def test_same_edge_cannot_be_repeated_under_another_constraint():
    with pytest.raises(ValueError, match="duplicate"):
        _validate([_edge(), _edge(constraint=2)], constraints=("Review before publication.", "Publish after review."))


@pytest.mark.parametrize("orders", [(1, 2), (2, 2, 1), (2, 3, 4), (True, 2, 3)])
def test_first_run_requires_each_event_once(orders):
    with pytest.raises(ValueError):
        validate_first_run(
            _walk(orders), event_orders=(1, 2, 3), source_precedence=(), result_event_order=1,
        )


def test_first_run_preserves_required_actions_after_the_observable_result():
    walk = {"event_orders": [1, 2], "rationale": "Publish the report, then archive the evidence."}
    precedence = _validate(
        [_edge(1, 2)], events=(1, 2),
        constraints=("Publish the report before archiving the evidence.",),
    )
    assert validate_first_run(
        walk, event_orders=(1, 2), source_precedence=precedence, result_event_order=1,
    ) == walk
    with pytest.raises(ValueError, match="precedence"):
        validate_first_run(
            {**walk, "event_orders": [2, 1]}, event_orders=(1, 2),
            source_precedence=precedence, result_event_order=1,
        )


def test_unordered_post_result_action_is_not_forced_before_its_result_producer():
    assert validate_first_run(
        _walk((2, 1, 3)), event_orders=(1, 2, 3), source_precedence=(), result_event_order=1,
    ) == _walk((2, 1, 3))


@pytest.mark.parametrize("result_order", [0, True, 4, 1.0, "1"])
def test_first_run_still_requires_a_valid_explicit_result_reference(result_order):
    with pytest.raises(ValueError, match="result event"):
        validate_first_run(
            _walk(), event_orders=(1, 2, 3), source_precedence=(), result_event_order=result_order,
        )


def test_walk_cannot_reverse_cited_precedence_even_if_result_is_last():
    with pytest.raises(ValueError, match="precedence"):
        validate_first_run(
            _walk((3, 2, 1)), event_orders=(1, 2, 3),
            source_precedence=_validate([_edge(2, 3)]), result_event_order=1,
        )


@pytest.mark.parametrize("walk", [None, {}, {**_walk(), "rationale": " "}, {**_walk(), "branch": []}])
def test_walk_has_one_closed_nonblank_design_contract(walk):
    with pytest.raises(ValueError):
        validate_first_run(walk, event_orders=(1, 2, 3), source_precedence=(), result_event_order=1)


@pytest.mark.parametrize("edges", [None, [{}], [_edge(4)], [_edge(True)], [_edge(), _edge()]])
def test_first_run_rejects_malformed_precedence_bindings(edges):
    with pytest.raises(ValueError):
        validate_first_run(_walk(), event_orders=(1, 2, 3), source_precedence=edges, result_event_order=1)


def test_validators_copy_values_without_rewriting_or_deriving_precedence():
    raw_edges, raw_walk = [_edge()], _walk()
    edges = _validate(raw_edges)
    walk = validate_first_run(raw_walk, event_orders=(1, 2, 3), source_precedence=edges, result_event_order=1)
    raw_edges[0]["before_event"] = 3
    raw_walk["event_orders"].reverse()
    assert edges == (_edge(),)
    assert walk == _walk()
    assert set(SOURCE_PRECEDENCE_SCHEMA["items"]["properties"]) == set(_edge())
    assert set(FIRST_RUN_SCHEMA["properties"]) == set(_walk())


def _authored_input():
    from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring as author
    from odylith.runtime.domain_intelligence.greenfield_provisional_design import PROVISIONAL_DESIGN_VERSION

    story = "Les bénévoles publient la liste prête, vérifient les demandes et enregistrent les demandes"
    constraints = ["La publication suit la vérification", "la vérification suit l’enregistrement"]
    source = f"Créer Agora. {story}. {constraints[0]}; {constraints[1]}."
    citation = lambda quote: {"quote": quote, "occurrence": 1}
    facts = {
        field: None if field in author._SINGULAR_SOURCE_FIELDS else []
        for field in author._SOURCE_FACT_FIELDS
    }
    facts.update({
        "title": citation("Agora"), "product_story": citation(story),
        "state_object": citation("demandes"), "proof_boundary": citation("liste prête"),
        "customer": citation("bénévoles"), "human_actors": [citation("bénévoles")],
        "first_path": [citation(quote) for quote in (
            "Les bénévoles publient la liste prête", "vérifient les demandes", "enregistrent les demandes",
        )],
        "operational_constraints": [citation(constraints[0]), citation(constraints[0]), citation(constraints[1])],
    })
    design = {
        "version": PROVISIONAL_DESIGN_VERSION, "authority_kind": "provisional_design",
        "components": [
            {"key": f"boundary-{index}", "name": f"Boundary {index}", "responsibility": "Review requests.",
             "supported_event_orders": [min(index, 3)], "verification": "Inspect reviewed requests."}
            for index in range(1, 5)
        ],
        "workstreams": [
            {"key": f"work-{index}", "title": f"Implement boundary {index}",
             "component_keys": [f"boundary-{index}"], "depends_on": [],
             "deliverable": "Reviewed requests.", "verification": "Inspect a recorded review."}
            for index in range(1, 5)
        ],
        "exchanges": [], "first_run": _walk(),
    }
    response = {
        "version": author.GREENFIELD_INTENT_AUTHORING_VERSION,
        "result": {
            "status": "authored", "consistency": {"status": "consistent", "evidence_quotes": []},
            "facts": facts,
            "events": [
                {"actor_fact_quote": "bénévoles", "action_quote": action, "target_quote": target}
                for action, target in (("publient", "la liste prête"), ("vérifient", "les demandes"), ("enregistrent", "les demandes"))
            ],
            "terminal": {
                "result_fact": {"field": "proof_boundary", "row": 1},
                "result_quote": "liste prête", "result_occurrence": 1, "event_order": 1,
            },
            "components": [], "ambiguities": [],
            "assumptions": [
                {"applies_to": field, "statement": statement}
                for field, statement in (
                    ("problem", "Coordinate request handling."),
                    ("opportunity", "Make reviewed requests available."),
                    ("product_view", "Volunteers review requests before publication."),
                )
            ],
            "source_precedence": [_edge(2, 1, 2), _edge(3, 2, 3)],
            "provisional_design": design,
        },
    }
    return source, response


def _selected_input():
    from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import _intent_from_typed_source_spans

    source, response = _authored_input()
    result = response["result"]
    intent, spans, selected = _intent_from_typed_source_spans(
        result["facts"], component_rows=(), evidence_text=source,
        assumptions=result["assumptions"], ambiguities=[],
    )
    return source, result, intent, spans, selected


def test_utf8_precedence_reuses_existing_citation_custody_and_preserves_duplicate_indexes():
    source, result, intent, spans, _ = _selected_input()
    edges = _validate(result["source_precedence"], constraints=intent["operational_constraints"])
    constraint_spans = [span for span in spans if span["section_key"] == "operational_constraints"]
    assert len(constraint_spans) == 3
    assert [span["row_index"] for span in constraint_spans] == [1, 2, 3]
    assert [span["projection_path"] for span in constraint_spans] == [f"/operational_constraints/{index}" for index in range(3)]
    for edge in edges:
        span = constraint_spans[edge["constraint_index"] - 1]
        exact = source.encode("utf-8")[span["source_start_byte"]:span["source_end_byte"]].decode("utf-8")
        assert exact == intent["operational_constraints"][edge["constraint_index"] - 1]
    assert constraint_spans[0]["source_start_byte"] == constraint_spans[1]["source_start_byte"]
    assert edges[-1]["constraint_index"] == 3


def test_result_documented_first_stays_bound_to_its_explicit_event():
    from odylith.runtime.domain_intelligence.greenfield_model_direct_evidence_graph import derive_model_relations

    source, result, intent, _, selected = _selected_input()
    derived = derive_model_relations(
        events=result["events"], terminal=result["terminal"], components=[],
        selected_facts=selected, first_path=intent["first_path"], evidence_text=source,
    )
    assert [row["visible_result_quote"] for row in derived.first_path_relations] == ["liste prête", "", ""]
    assert [row["order"] for row in derived.first_path_relations] == [1, 2, 3]


@pytest.mark.parametrize("event_order", [0, True, 4, None])
def test_terminal_reference_cannot_default_to_last_event(event_order):
    from odylith.runtime.domain_intelligence.greenfield_authored_semantics import GreenfieldAuthoredSemanticsError
    from odylith.runtime.domain_intelligence.greenfield_model_direct_evidence_graph import derive_model_relations

    source, result, intent, _, selected = _selected_input()
    result["terminal"]["event_order"] = event_order
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="terminal event"):
        derive_model_relations(
            events=result["events"], terminal=result["terminal"], components=[],
            selected_facts=selected, first_path=intent["first_path"], evidence_text=source,
        )


def test_authoring_boundary_retains_precedence_and_proposed_first_run():
    from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import _validated_authoring_response
    from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID

    source, response = _authored_input()
    authored = _validated_authoring_response(
        response, evidence_text=source, elapsed_seconds=1, provider={},
        profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=55,
    )
    assert authored.source_precedence == tuple(response["result"]["source_precedence"])
    assert authored.provisional_design["first_run"] == _walk()
    assert authored.first_path_relations[0]["visible_result_quote"] == "liste prête"


@pytest.mark.parametrize("missing", ["source_precedence", "terminal_event", "first_run"])
def test_authoring_requires_order_authority_instead_of_migrating_old_response(missing):
    from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
        GreenfieldModelAuthoringError, _validated_authoring_response,
    )
    from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID

    source, response = _authored_input()
    if missing == "terminal_event":
        response["result"]["terminal"].pop("event_order")
    elif missing == "first_run":
        response["result"]["provisional_design"].pop("first_run")
    else:
        response["result"].pop(missing)
    with pytest.raises(GreenfieldModelAuthoringError):
        _validated_authoring_response(
            response, evidence_text=source, elapsed_seconds=1, provider={},
            profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=55,
        )


def test_design_validation_requires_the_explicit_first_run_binding():
    from odylith.runtime.domain_intelligence.greenfield_provisional_design import validate_provisional_design

    _, response = _authored_input()
    result = response["result"]
    design = deepcopy(result["provisional_design"])
    design["first_run"] = _walk((2, 3, 1))
    with pytest.raises(ValueError, match="precedence"):
        validate_provisional_design(
            design, event_orders=(1, 2, 3), source_precedence=result["source_precedence"], result_event_order=1,
        )
