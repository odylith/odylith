from __future__ import annotations

import copy

import pytest

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    greenfield_operating_envelope_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    SEMANTIC_INTENT_PACKET_VERSION,
    require_semantic_intent_ir,
    semantic_intent_authoring_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_schema import (
    semantic_intent_output_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    INTERNAL_SYSTEM_COMPONENT_KINDS,
    INTERNAL_SYSTEM_RELEASE_SCOPES,
    SEMANTIC_FACT_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_request import (
    SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
    semantic_intent_authoring_request,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    PATH_EVIDENCE,
    SEMANTIC_PROMPT,
    STATE_EVIDENCE,
    semantic_fact,
    semantic_intent_packet,
    semantic_intent_with_authority,
    semantic_ref,
    semantic_relation,
)


def _nested_mapping_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for nested in value.values()
            for key in _nested_mapping_keys(nested)
        }
    if isinstance(value, list):
        return {
            key
            for nested in value
            for key in _nested_mapping_keys(nested)
        }
    return set()


def _actorless_stateless_multi_output_packet() -> dict[str, object]:
    packet = copy.deepcopy(semantic_intent_packet())
    graph = packet["semantic_intent"]
    assert isinstance(graph, dict)
    graph["facts"] = [
        row
        for row in graph["facts"]
        if row["kind"] not in {"actor", "state_object"}
        and row["fact_id"] != "system.1"
    ]
    for row in graph["facts"]:
        if row["kind"] == "workflow_step":
            row["owner_kind"] = "product"
    graph["facts"].append(
        semantic_fact(
            "output.1",
            "visible_output",
            "Claim audit view",
            "A claim audit view is visible.",
            1,
            PATH_EVIDENCE,
        )
    )
    graph["relations"] = [
        row
        for row in graph["relations"]
        if row["kind"] not in {"owned_by", "changes", "implements"}
        and row["subject_id"] != "system.1"
        and row["object_id"] != "system.1"
    ]
    graph["relations"].extend(
        [
            semantic_relation("produces", "step.0", "output.1", 1, PATH_EVIDENCE),
            semantic_relation("implements", "system.0", "step.0", 0, PATH_EVIDENCE),
            semantic_relation("implements", "system.0", "step.1", 1, PATH_EVIDENCE),
            semantic_relation("implements", "system.0", "output.0", 2, PATH_EVIDENCE),
            semantic_relation("implements", "system.0", "output.1", 3, PATH_EVIDENCE),
        ]
    )
    live_fact_ids = {row["fact_id"] for row in graph["facts"]}
    for narrative in graph["narratives"]:
        narrative["fact_ids"] = [
            fact_id
            for fact_id in narrative["fact_ids"]
            if fact_id in live_fact_ids
        ] or ["identity.0"]
    return packet


def _multi_state_multi_output_packet() -> dict[str, object]:
    packet = copy.deepcopy(semantic_intent_packet())
    graph = packet["semantic_intent"]
    assert isinstance(graph, dict)
    graph["facts"].extend(
        [
            semantic_fact(
                "state.1",
                "state_object",
                "Claim receipt",
                "The claim receipt moves from pending to visible.",
                1,
                STATE_EVIDENCE,
                attributes={"object": "claim receipt"},
                transition={"from_state": "pending", "to_state": "visible"},
            ),
            semantic_fact(
                "output.1",
                "visible_output",
                "Claim audit view",
                "A claim audit view is visible.",
                1,
                PATH_EVIDENCE,
            ),
        ]
    )
    graph["relations"].extend(
        [
            semantic_relation("changes", "step.1", "state.1", 1, STATE_EVIDENCE),
            semantic_relation("produces", "step.0", "output.1", 1, PATH_EVIDENCE),
            semantic_relation("implements", "system.0", "output.1", 4, PATH_EVIDENCE),
            semantic_relation("implements", "system.0", "state.1", 5, STATE_EVIDENCE),
        ]
    )
    return packet


def test_graph_v4_versions_and_authoring_cardinality_are_explicit() -> None:
    request = semantic_intent_authoring_request(prompt=SEMANTIC_PROMPT)
    contract = semantic_intent_authoring_contract()
    authority = semantic_intent_with_authority()["product_intent_authority"]

    assert SEMANTIC_INTENT_IR_VERSION.endswith(".v4")
    assert SEMANTIC_INTENT_PACKET_VERSION.endswith(".v7")
    assert SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION.endswith(".v11")
    assert request["version"] == SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION
    assert request["packet_header"]["version"] == SEMANTIC_INTENT_PACKET_VERSION
    assert request["authoring_contract_sha256"] == authority[
        "semantic_intent_authoring_contract_sha256"
    ]
    assert authority["semantic_intent_authoring_request_version"] == request["version"]
    assert request["authoring_protocol"]["mechanism_status"] == "provisional"
    assert request["authoring_protocol"]["mechanism_selection"] == (
        "pending_development_evidence"
    )
    assert "mechanism" not in request["authoring_protocol"]
    assert "stages" not in request["authoring_protocol"]
    assert request["authoring_protocol"]["mandatory_challenges"] == list(
        SEMANTIC_INTENT_MANDATORY_CHALLENGES
    )
    assert request["authoring_protocol"]["mandatory_challenges"][:4] == [
        "unsupported_addition",
        "supported_fact_omission",
        "ownership_mismatch",
        "cardinality_violation",
    ]
    assert request["authoring_protocol"]["mandatory_challenges"][-2:] == [
        "consumer_copy_specificity",
        "cross_surface_utility",
    ]
    assert {
        "evidence_status_misclassification",
        "semantic_kind_conflation",
        "explicit_axis_cardinality_loss",
        "partial_clarification_custody",
    } <= set(request["authoring_protocol"]["mandatory_challenges"])
    assert any(
        "never substitute generic phrases" in requirement
        for requirement in request["authoring_protocol"]["outcome_requirements"]
    )
    assert any(
        "evidence-noise labels" in requirement
        for requirement in request["authoring_protocol"]["outcome_requirements"]
    )
    optional = request["authoring_protocol"]["conditionally_optional_axes"]
    assert set(optional) == {
        "actors_and_ownership",
        "state_objects_and_transitions",
    }
    assert "human-facing interaction" in optional["actors_and_ownership"]
    assert "durable state" in optional["state_objects_and_transitions"]
    semantics = request["authoring_protocol"]["materiality_field_semantics"]
    assert set(semantics) == set(contract["status_contract"]["clarification_fields"])
    assert "not a visible result" in semantics["visible_result"]
    assert contract["status_contract"]["clarification_fields"] == [
        "identity",
        "role",
        "first_path",
        "state_object",
        "visible_result",
        "dependency",
        "constraint",
        "non_goal",
        "component_boundary",
    ]


def test_graph_author_schema_and_runtime_share_internal_system_value_contracts() -> None:
    request = semantic_intent_authoring_request(prompt=SEMANTIC_PROMPT)
    contract = semantic_intent_authoring_contract()
    schema = semantic_intent_output_schema()
    fact_rules = {
        row["properties"]["kind"]["enum"][0]: row["properties"]
        for row in schema["properties"]["facts"]["items"]["anyOf"]
    }
    internal_attributes = fact_rules["internal_system"]["attributes"]["items"][
        "anyOf"
    ]
    conditional_values = {
        row["properties"]["name"]["enum"][0]: row["properties"]["value"][
            "enum"
        ]
        for row in internal_attributes
        if row["properties"]["name"]["enum"]
        in (["component_kind"], ["release_scope"])
    }

    assert set(fact_rules) == set(SEMANTIC_FACT_KINDS)
    assert conditional_values == {
        "component_kind": list(INTERNAL_SYSTEM_COMPONENT_KINDS),
        "release_scope": list(INTERNAL_SYSTEM_RELEASE_SCOPES),
    }
    assert INTERNAL_SYSTEM_RELEASE_SCOPES == (
        "first_path_required",
        "deferred",
    )
    assert contract["fact_contracts"]["internal_system"][
        "attribute_value_contracts"
    ] == conditional_values
    scope_semantics = contract["fact_contracts"]["internal_system"][
        "release_scope_semantics"
    ]
    assert set(scope_semantics) == {
        "first_path_required",
        "deferred",
        "implementation_role",
    }
    assert "implements relations" in scope_semantics["implementation_role"]
    for kind, rule in fact_rules.items():
        assert rule["owner_kind"]["enum"] == contract["fact_contracts"][kind][
            "owner_kinds"
        ]
        allowed_names = {
            name
            for variant in rule["attributes"]["items"]["anyOf"]
            for name in variant["properties"]["name"]["enum"]
        }
        assert set(contract["fact_contracts"][kind]["required_attributes"]) <= allowed_names
        assert {"from_state", "to_state"}.isdisjoint(allowed_names)
        assert ("transition" in rule) == (kind == "state_object")
        assert ({"component_kind", "release_scope"} <= allowed_names) == (
            kind == "internal_system"
        )
    assert fact_rules["workflow_step"]["owner_kind"]["enum"] == [
        "actor",
        "product",
        "system",
    ]
    assert fact_rules["internal_system"]["owner_kind"]["enum"] == ["none"]
    transition_variants = fact_rules["state_object"]["transition"]["anyOf"]
    assert transition_variants[0] == {"type": "null"}
    assert transition_variants[1]["required"] == ["from_state", "to_state"]
    assert transition_variants[1]["additionalProperties"] is False
    forbidden_provider_keywords = {
        "allOf",
        "not",
        "if",
        "then",
        "else",
        "contains",
        "minContains",
        "maxContains",
        "const",
    }
    assert not forbidden_provider_keywords & _nested_mapping_keys(schema)

    packet = semantic_intent_packet()
    internal_system = next(
        row
        for row in packet["semantic_intent"]["facts"]
        if row["kind"] == "internal_system"
    )
    next(
        row
        for row in internal_system["attributes"]
        if row["name"] == "component_kind"
    )["value"] = "workflow_controller"
    with pytest.raises(ValueError, match="invalid component kind"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    assert any(
        "preserve every settled source-cited" in requirement
        for requirement in request["authoring_protocol"]["outcome_requirements"]
    )
    assert contract["fact_contracts"]["actor"] == {
        "semantic_role": (
            "one explicit human role or participant; preserve each declared role separately"
        ),
        "required_attributes": ["responsibility"],
        "owner_kinds": ["none"],
        "minimum": 0,
        "maximum": 64,
    }
    assert contract["fact_contracts"]["state_object"]["minimum"] == 0
    assert contract["fact_contracts"]["state_object"]["maximum"] == 16
    assert contract["fact_contracts"]["internal_system"]["minimum"] == 1
    assert "never a generic interface" in contract["fact_contracts"]["internal_system"][
        "semantic_role"
    ]
    assert "entire capability or outcome excluded" in contract["fact_contracts"]["non_goal"][
        "semantic_role"
    ]
    assert "regardless of grammatical form" in contract["fact_contracts"][
        "operational_constraint"
    ]["semantic_role"]
    assert contract["complete_graph_contract"][
        "maximum_transition_pairs_per_state_object"
    ] == 1


def test_clarification_ir_preserves_and_validates_its_settled_partial_graph() -> None:
    complete = semantic_intent_packet()["semantic_intent"]
    facts = [
        copy.deepcopy(row)
        for row in complete["facts"]
        if row["fact_id"] in {"identity.0", "actor.0", "step.0"}
    ]
    partial = {
        "version": SEMANTIC_INTENT_IR_VERSION,
        "status": "clarification_required",
        "clarification": {
            "question": "What visible result should the shift coordinator receive?",
            "fields": ["visible_result"],
            "source_refs": [semantic_ref(PATH_EVIDENCE)],
        },
        "facts": facts,
        "relations": [
            copy.deepcopy(
                next(
                    row
                    for row in complete["relations"]
                    if row["kind"] == "owned_by" and row["subject_id"] == "step.0"
                )
            )
        ],
        "narratives": [],
    }

    verified = require_semantic_intent_ir(
        partial,
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )

    assert [row["fact_id"] for row in verified["facts"]] == [
        "identity.0",
        "actor.0",
        "step.0",
    ]
    assert verified["relations"][0]["subject_id"] == "step.0"

    invalid_field = copy.deepcopy(partial)
    invalid_field["clarification"]["fields"] = ["ordered_actions"]
    with pytest.raises(ValueError, match="non-canonical field"):
        require_semantic_intent_ir(
            invalid_field,
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
        )

    invalid_relation = copy.deepcopy(partial)
    invalid_relation["relations"][0]["object_id"] = "missing.actor"
    with pytest.raises(ValueError, match="unknown fact"):
        require_semantic_intent_ir(
            invalid_relation,
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
        )


def test_graph_v4_rejects_v1_packets_without_a_compatibility_adapter() -> None:
    old_packet = semantic_intent_packet()
    old_packet["version"] = "odylith.greenfield.semantic-intent-packet.v1"
    with pytest.raises(ValueError, match="packet uses an unsupported version"):
        require_semantic_intent_packet(old_packet, prompt=SEMANTIC_PROMPT)

    old_ir = semantic_intent_packet()
    old_ir["semantic_intent"]["version"] = "odylith.greenfield.semantic-intent-ir.v1"
    with pytest.raises(ValueError, match="IR uses an unsupported version"):
        require_semantic_intent_packet(old_ir, prompt=SEMANTIC_PROMPT)


def test_graph_v4_accepts_no_actors_no_state_one_system_and_multiple_outputs() -> None:
    verified = require_semantic_intent_packet(
        _actorless_stateless_multi_output_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    facts = list(verified.semantic_intent["facts"])
    relations = list(verified.semantic_intent["relations"])
    outputs = sorted(
        (row for row in facts if row["kind"] == "visible_output"),
        key=lambda row: row["order"],
    )
    steps = sorted(
        (row for row in facts if row["kind"] == "workflow_step"),
        key=lambda row: row["order"],
    )

    assert verified.product_facts["human_actors"] == []
    assert verified.product_facts["state_objects"] == []
    assert verified.product_facts["visible_outputs"] == [
        "A claim receipt is visible.",
        "A claim audit view is visible.",
    ]
    assert len(verified.product_facts["internal_systems"]) == 1
    assert not [row for row in facts if row["kind"] == "state_object"]
    assert [(row["fact_id"], row["label"]) for row in outputs] == [
        ("output.0", "Claim receipt"),
        ("output.1", "Claim audit view"),
    ]
    assert all(row["owner_kind"] == "product" for row in steps)
    produced = {
        row["subject_id"]: row["object_id"]
        for row in relations
        if row["kind"] == "produces"
    }
    assert produced == {"step.0": "output.1", "step.1": "output.0"}


def test_graph_v4_projects_multiple_state_objects_and_outputs_without_collapse() -> None:
    verified = require_semantic_intent_packet(
        _multi_state_multi_output_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    facts = list(verified.semantic_intent["facts"])
    relations = list(verified.semantic_intent["relations"])
    states = sorted(
        (row for row in facts if row["kind"] == "state_object"),
        key=lambda row: row["order"],
    )
    outputs = sorted(
        (row for row in facts if row["kind"] == "visible_output"),
        key=lambda row: row["order"],
    )

    assert verified.product_facts["state_objects"] == [
        "The card moves from ready to claimed.",
        "The claim receipt moves from pending to visible.",
    ]
    assert [row["fact_id"] for row in states] == ["state.0", "state.1"]
    assert [
        (
            {item["name"]: item["value"] for item in row["attributes"]}["object"],
            row["transition"]["from_state"],
            row["transition"]["to_state"],
        )
        for row in states
    ] == [
        ("card", "ready", "claimed"),
        ("claim receipt", "pending", "visible"),
    ]
    assert [
        row["object_id"]
        for row in relations
        if row["kind"] == "changes" and row["subject_id"] == "step.1"
    ] == ["state.1"]
    assert [row["fact_id"] for row in outputs] == ["output.0", "output.1"]


@pytest.mark.parametrize(
    ("relation_kind", "message"),
    [
        ("produces", "producing coverage for every visible output"),
        ("changes", "change coverage for every state object"),
    ],
)
def test_graph_v4_rejects_orphaned_material_facts(
    relation_kind: str,
    message: str,
) -> None:
    packet = semantic_intent_packet()
    graph = packet["semantic_intent"]
    graph["relations"] = [
        row for row in graph["relations"] if row["kind"] != relation_kind
    ]

    with pytest.raises(ValueError, match=message):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_graph_v4_requires_one_first_path_system_and_active_implementation() -> None:
    all_deferred = semantic_intent_packet()
    for fact in all_deferred["semantic_intent"]["facts"]:
        if fact["kind"] == "internal_system":
            next(
                row for row in fact["attributes"] if row["name"] == "release_scope"
            )["value"] = "deferred"
    with pytest.raises(ValueError, match="lacks a first_path_required internal system"):
        require_semantic_intent_packet(all_deferred, prompt=SEMANTIC_PROMPT)

    deferred_implementation = semantic_intent_packet()
    system = next(
        fact
        for fact in deferred_implementation["semantic_intent"]["facts"]
        if fact["fact_id"] == "system.1"
    )
    next(
        row for row in system["attributes"] if row["name"] == "release_scope"
    )["value"] = "deferred"
    with pytest.raises(ValueError, match="active typed implementation coverage"):
        require_semantic_intent_packet(
            deferred_implementation,
            prompt=SEMANTIC_PROMPT,
        )


def test_graph_v4_derives_required_boundary_support_from_typed_relations() -> None:
    packet = semantic_intent_packet()
    graph = packet["semantic_intent"]
    for relation in graph["relations"]:
        if relation["kind"] == "implements" and relation["subject_id"] == "system.0":
            relation["subject_id"] = "system.1"

    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    system = next(
        row for row in verified.semantic_intent["facts"]
        if row["fact_id"] == "system.0"
    )
    assert next(
        row["value"] for row in system["attributes"]
        if row["name"] == "release_scope"
    ) == "first_path_required"

    graph["relations"] = [
        relation
        for relation in graph["relations"]
        if not (
            relation["kind"] == "depends_on"
            and relation["subject_id"] == "system.1"
            and relation["object_id"] == "system.0"
        )
    ]
    with pytest.raises(ValueError, match="lacks typed supporting topology"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_graph_v4_rejects_zero_internal_systems() -> None:
    packet = semantic_intent_packet()
    graph = packet["semantic_intent"]
    system_ids = {
        fact["fact_id"]
        for fact in graph["facts"]
        if fact["kind"] == "internal_system"
    }
    graph["facts"] = [
        fact for fact in graph["facts"] if fact["fact_id"] not in system_ids
    ]
    graph["relations"] = [
        relation
        for relation in graph["relations"]
        if relation["subject_id"] not in system_ids
        and relation["object_id"] not in system_ids
    ]

    with pytest.raises(ValueError, match="lacks internal_system"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


@pytest.mark.parametrize("target_id", ["state.0", "output.0"])
def test_graph_v4_requires_direct_active_implementation_for_state_and_output(
    target_id: str,
) -> None:
    packet = semantic_intent_packet()
    graph = packet["semantic_intent"]
    remaining = [
        relation
        for relation in graph["relations"]
        if not (
            relation["kind"] == "implements"
            and relation["object_id"] == target_id
        )
    ]
    for order, relation in enumerate(
        row for row in remaining if row["kind"] == "implements"
    ):
        relation["order"] = order
        relation["relation_id"] = f"relation.implements.{order}"
    graph["relations"] = remaining

    with pytest.raises(ValueError, match="active typed implementation coverage"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_graph_v4_rejects_more_than_sixteen_state_objects() -> None:
    packet = semantic_intent_packet()
    graph = packet["semantic_intent"]
    for order in range(1, 17):
        graph["facts"].append(
            semantic_fact(
                f"state.{order}",
                "state_object",
                f"State {order}",
                f"State object {order} changes.",
                order,
                STATE_EVIDENCE,
                attributes={"object": f"state object {order}"},
            )
        )
        graph["relations"].append(
            semantic_relation(
                "changes",
                "step.0",
                f"state.{order}",
                order,
                STATE_EVIDENCE,
            )
        )

    with pytest.raises(ValueError, match="exceeds state_object cardinality"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_graph_v4_rejects_a_non_atomic_state_transition() -> None:
    packet = semantic_intent_packet()
    state = next(
        fact
        for fact in packet["semantic_intent"]["facts"]
        if fact["fact_id"] == "state.0"
    )
    state["transition"] = {"from_state": "queued"}

    with pytest.raises(ValueError, match="state transition has an invalid structure"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_graph_v4_rejects_transition_custody_on_a_non_state_fact() -> None:
    packet = semantic_intent_packet()
    actor = next(
        fact
        for fact in packet["semantic_intent"]["facts"]
        if fact["fact_id"] == "actor.0"
    )
    actor["transition"] = None

    with pytest.raises(ValueError, match="fact has an invalid structure"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_graph_v4_product_facts_expose_no_scalar_state_or_output_adapter() -> None:
    verified = require_semantic_intent_packet(
        semantic_intent_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    assert "state_object" not in verified.product_facts
    assert "visible_output" not in verified.product_facts
    assert {"state_objects", "visible_outputs"} <= set(verified.product_facts)

    receipt = greenfield_operating_envelope_receipt(
        facts={"state_object": "legacy scalar must not count"},
        source_format="semantic_intent_packet",
        source_size_bytes=1,
    )
    assert receipt["complexity"]["dimensions"]["state_objects"] == 0
