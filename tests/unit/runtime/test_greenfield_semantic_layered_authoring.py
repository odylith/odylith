from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    semantic_intent_product_facts,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_COMPLETION_GRAPH_VERSION,
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
    compile_layered_authoring_graph,
    compile_layered_source_authority,
    compile_partitioned_authoring_graph,
    semantic_completion_graph_schema,
    semantic_partitioned_author_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_completion_partitions import (
    apply_semantic_implementation_assignments,
    semantic_architecture_edge_object_ids,
    semantic_completion_citation_registry,
    semantic_graph_completion_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_partition_custody import (
    accepted_partitioned_evidence_catalog,
    completion_without_discarded_citations,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
    SEMANTIC_SOURCE_GRAPH_VERSION,
    SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
    SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION,
    SOURCE_ACCESS_MODES,
    SOURCE_BOUNDARY_COLLECTIONS,
    SOURCE_BOUNDARY_RELATION_KINDS,
    SOURCE_PATH_COLLECTIONS,
    SOURCE_PATH_RELATION_KINDS,
    compile_source_partitioned_graph,
    semantic_source_boundary_graph_schema,
    semantic_source_partitioned_graph_schema,
    semantic_source_path_graph_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    bind_semantic_evidence_blocks,
    semantic_evidence_block_catalog,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


COLLECTIONS = {
    "identity": "identities",
    "actor": "actors",
    "workflow_step": "workflow_steps",
    "state_object": "state_objects",
    "visible_output": "visible_outputs",
    "external_system": "external_systems",
    "internal_system": "internal_systems",
    "component_responsibility": "component_responsibilities",
    "operational_constraint": "operational_constraints",
    "non_goal": "non_goals",
    "assumption": "assumptions",
    "ambiguity": "ambiguities",
}
RELATIONS = (
    "owned_by", "produces", "changes", "depends_on", "implements",
    "constrained_by", "excludes",
)


def test_layered_authors_compile_to_the_exact_full_production_packet() -> None:
    expected = semantic_intent_packet()
    source, completion = _layers(expected)

    author_output = compile_layered_authoring_graph(
        source,
        completion,
        assessment=expected["materiality_assessment"],
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )
    packet = build_semantic_intent_packet(
        expected["materiality_assessment"],
        author_output,
        prompt=SEMANTIC_PROMPT,
        critic_run_id="layered-critic",
        author_run_id="layered-author",
        critic_host_profile="codex",
    )

    assert {
        (row["fact_id"], row["kind"], row["label"])
        for row in packet["semantic_intent"]["facts"]
    } == {
        (row["fact_id"], row["kind"], row["label"])
        for row in expected["semantic_intent"]["facts"]
        if row["kind"] != "component_responsibility"
    }
    assert {
        (row["kind"], row["subject_id"], row["object_id"])
        for row in packet["semantic_intent"]["relations"]
    } == {
        (row["kind"], row["subject_id"], row["object_id"])
        for row in expected["semantic_intent"]["relations"]
    }
    actual_narratives = packet["semantic_intent"]["narratives"]
    assert [row["field"] for row in actual_narratives[:6]] == [
        "product_story", "problem", "customer", "opportunity",
        "product_view", "proof_boundary",
    ]
    assert len([row for row in actual_narratives if row["field"] == "success_metric"]) >= 2
    assert all("%" not in row["text"] for row in actual_narratives)
    assert len({row["text"] for row in actual_narratives}) == len(actual_narratives)
    known_fact_ids = {
        row["fact_id"] for row in packet["semantic_intent"]["facts"]
    }
    assert all(
        row["fact_ids"] and set(row["fact_ids"]) <= known_fact_ids
        for row in packet["semantic_intent"]["narratives"]
    )
    assert set(actual_narratives[0]["fact_ids"]) <= known_fact_ids


def test_source_authority_compiles_without_granting_completion_custody() -> None:
    expected = semantic_intent_packet()
    source, _ = _layers(expected)

    authority = compile_layered_source_authority(
        source,
        assessment=expected["materiality_assessment"],
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )

    assert authority["source"] == source
    adjudication = authority["source_candidate_adjudication"]
    assert adjudication["candidate_decisions"] == expected[
        "source_candidate_adjudication"
    ]["candidate_decisions"]
    assert {
        row["fact"]["fact_id"] for row in adjudication["source_claims"]["facts"]
    } == {
        row["fact"]["fact_id"]
        for row in expected["source_candidate_adjudication"]["source_claims"]["facts"]
    }


def test_completion_cannot_author_governance_narratives() -> None:
    expected = semantic_intent_packet()
    source, completion = _layers(expected)
    completion["narratives"] = {"product_view": {"text": "unsupported"}}

    try:
        compile_layered_authoring_graph(
            source,
            completion,
            assessment=expected["materiality_assessment"],
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
        )
    except ValueError as error:
        assert str(error) == "Semantic completion authoring graph has unsupported or missing fields"
    else:
        raise AssertionError("completion-authored narrative fact identity must fail closed")


def test_single_partitioned_author_adds_only_deterministic_boundary_custody() -> None:
    expected = semantic_intent_packet()
    source, completion = _layers(expected)
    completion["internal_systems"] = completion["internal_systems"][:1]
    compact_completion = deepcopy(completion)
    for row in compact_completion["internal_systems"]:
        row.pop("fact_id", None)
        for relation_kind in ("depends_on", "implements", "constrained_by", "excludes"):
            row.pop(relation_kind)
    candidate = {
        "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
        "source": _partitioned_source(source),
        "completion": compact_completion,
    }

    author_output = compile_partitioned_authoring_graph(
        candidate,
        assessment=expected["materiality_assessment"],
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )

    legacy_output = compile_layered_authoring_graph(
        source,
        completion,
        assessment=expected["materiality_assessment"],
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )
    new_claims = author_output["source_candidate_adjudication"]["source_claims"]
    legacy_claims = legacy_output["source_candidate_adjudication"]["source_claims"]
    assert new_claims["facts"] == legacy_claims["facts"]
    new_relations = {
        (row["relation"]["kind"], row["relation"]["subject_id"], row["relation"]["object_id"])
        for row in new_claims["relations"]
    }
    legacy_relations = {
        (row["relation"]["kind"], row["relation"]["subject_id"], row["relation"]["object_id"])
        for row in legacy_claims["relations"]
    }
    assert legacy_relations < new_relations
    assert ("constrained_by", "identity.0", "constraint.0") in new_relations
    def semantic_edges(value: dict) -> set[tuple[str, str, str]]:
        return {
            (node["fact"]["fact_id"], relation_kind, edge["object_id"])
            for node in value["semantic_extension"]["nodes"]
            for relation_kind in ("depends_on", "implements", "constrained_by", "excludes")
            for edge in node[relation_kind]
        }

    assert semantic_edges(author_output) == semantic_edges(legacy_output)


def test_layered_schemas_are_bounded_and_source_semantics_have_one_owner() -> None:
    source = json.dumps(semantic_source_partitioned_graph_schema(), separators=(",", ":"))
    completion = json.dumps(semantic_completion_graph_schema(), separators=(",", ":"))
    author = json.dumps(semantic_partitioned_author_schema(), separators=(",", ":"))

    assert len(source) < 30_000
    assert len(completion) < 14_000
    assert len(author) < 45_000
    assert "narratives" not in semantic_source_partitioned_graph_schema()["properties"]
    assert "facts" not in semantic_completion_graph_schema()["properties"]
    assert "component_responsibilities" not in semantic_completion_graph_schema()[
        "properties"
    ]
    completion_system = semantic_completion_graph_schema()["properties"][
        "internal_systems"
    ]["items"]
    assert "fact_id" not in completion_system["properties"]
    assert "narratives" not in semantic_completion_graph_schema()["properties"]
    single_system = semantic_completion_graph_schema(system_count=1)["properties"][
        "internal_systems"
    ]
    assert single_system["minItems"] == single_system["maxItems"] == 1
    assert all(
        kind not in single_system["items"]["properties"]
        for kind in ("depends_on", "implements", "constrained_by", "excludes")
    )
    assert single_system["items"]["properties"]["component_kind"]["enum"] == [
        "adapter", "interface", "library", "service", "worker",
    ]
    assert single_system["items"]["properties"]["release_scope"]["enum"] == [
        "first_path_required", "deferred",
    ]
    complete_only = semantic_completion_graph_schema(complete_only=True)
    assert "clarification" not in complete_only["required"]
    assert "clarification" not in complete_only["properties"]
    assert complete_only["properties"]["status"]["enum"] == ["complete"]
    boundary = semantic_source_partitioned_graph_schema()["properties"]["boundary"][
        "properties"
    ]
    assert "internal_systems" not in boundary
    assert "component_responsibilities" not in boundary
    assert boundary["ambiguities"]["maxItems"] == 1
    assert boundary["ambiguities"]["items"]["properties"]["source_refs"][
        "minItems"
    ] == 1
    assert {"materiality_field", "question"} <= set(
        boundary["ambiguities"]["items"]["required"]
    )
    assert "implements" not in boundary["relations"]["properties"]
    assert "operational_constraints" not in boundary
    assert "non_goals" not in boundary
    assert boundary["policies"]["items"]["properties"]["policy_kind"]["enum"] == [
        "operating_invariant", "excluded_capability",
    ]
    assert boundary["external_systems"]["items"]["properties"]["access_mode"] == {
        "anyOf": [
            {"type": "string", "enum": list(SOURCE_ACCESS_MODES)},
            {"type": "null"},
        ]
    }
    assert "access_mode" in boundary["external_systems"]["items"]["required"]
    assert "consumer" in boundary["external_systems"]["items"]["required"]
    assert {"type": "null"} in boundary["external_systems"]["items"]["properties"][
        "consumer"
    ]["anyOf"]
    assert "materiality_field" in boundary["assumptions"]["items"]["required"]
    assert set(semantic_source_path_graph_schema()["properties"]) == {
        "version", "path",
    }
    assert set(semantic_source_boundary_graph_schema()["properties"]) == {
        "version", "boundary",
    }
    path = semantic_source_partitioned_graph_schema()["properties"]["path"]["properties"]
    assert path["identities"]["minItems"] == path["identities"]["maxItems"] == 1
    assert path["workflow_steps"]["minItems"] == 1
    assert path["visible_outputs"].get("minItems", 0) == 0
    assert "responsibility" not in path["actors"]["items"]["properties"]
    workflow_group = path["workflow_steps"]["items"]
    assert workflow_group["required"] == ["owner", "steps"]
    step = workflow_group["properties"]["steps"]["items"]
    assert "action" in step["required"]
    assert "changes" not in step["properties"]
    assert "produces" not in step["properties"]
    transition = path["state_objects"]["items"]["properties"]["transition"]
    transition_object = transition["anyOf"][0]
    assert transition_object["required"] == [
        "step_index", "from_state", "to_state", "source_refs",
    ]
    producer = path["visible_outputs"]["items"]["properties"]["producer"]
    assert producer["required"] == ["step_index", "source_refs"]
    assert "responsibility" not in step["properties"]
    assert "owner_kind" not in step["properties"]
    assert "state_semantics" not in path["state_objects"]["items"]["properties"]
    assert "transition" in path["state_objects"]["items"]["required"]
    assert "producer" in path["visible_outputs"]["items"]["required"]
    assert "condition" in path["visible_outputs"]["items"]["properties"]
    assert "condition" in path["visible_outputs"]["items"]["required"]
    assert "owned_by" not in path["relations"]["properties"]
    assert semantic_source_partitioned_graph_schema()["properties"]["boundary"][
        "properties"
    ]["relations"]["required"] == []
    assert semantic_source_boundary_graph_schema(assumption_fields=())["properties"][
        "boundary"
    ]["properties"]["assumptions"]["maxItems"] == 0


def test_completion_assignments_are_the_only_implementation_and_release_authority() -> None:
    source, completion = _layers(semantic_intent_packet())
    edge_ids = semantic_architecture_edge_object_ids(source)
    citation_registry = semantic_completion_citation_registry(source)
    raw_candidate = deepcopy(completion)
    raw_candidate.pop("clarification")
    candidate = _citation_completion_candidate(raw_candidate, citation_registry)
    candidate["self_challenge"] = {
        row["challenge"]: row["status"] for row in candidate["self_challenge"]
    }
    assignments: dict[str, dict] = {}
    for system_index, system in enumerate(candidate["internal_systems"]):
        system.pop("release_scope")
        for edge in system.pop("implements"):
            assignment = assignments.setdefault(
                edge["object_id"],
                {
                    "system_indices": [],
                    "source_citation_ids": deepcopy(edge["source_citation_ids"]),
                },
            )
            assignment["system_indices"].append(system_index)
    candidate["supporting_systems"] = []
    candidate["implementation_assignments"] = assignments

    schema = semantic_graph_completion_schema(
        source_citation_ids=tuple(citation_registry),
        edge_object_ids=edge_ids,
        topology_mode="adaptive",
    )
    system_schema = schema["properties"]["internal_systems"]["items"]
    assert "implements" not in system_schema["properties"]
    assert "release_scope" not in system_schema["properties"]
    assert "supporting_consumers" not in system_schema["properties"]
    supporting_schema = schema["properties"]["supporting_systems"]["items"]
    assert "implements" not in supporting_schema["properties"]
    assert "release_scope" not in supporting_schema["properties"]
    assert "supporting_consumers" in supporting_schema["required"]
    consumer_indices = supporting_schema["properties"]["supporting_consumers"][
        "properties"
    ]["system_indices"]
    assert consumer_indices["items"] == {
        "type": "integer",
        "minimum": 0,
        "maximum": 127,
    }
    assert "boundary_links" in supporting_schema["required"]
    assert "depends_on" not in supporting_schema["properties"]
    assert "source_refs" not in json.dumps(schema)
    assert "source_citation_ids" in json.dumps(schema)
    assert schema["$defs"]["source_citation_ids"]["maxItems"] == 8
    assert schema["properties"]["self_challenge"]["type"] == "object"
    assert "$ref" in json.dumps(schema["properties"]["internal_systems"])
    assert "allOf" not in json.dumps(schema)
    assert set(schema["properties"]["implementation_assignments"]["required"]) == set(
        edge_ids["implements"]
    )
    standard_schema = semantic_graph_completion_schema(
        source_citation_ids=tuple(citation_registry),
        edge_object_ids=edge_ids,
        topology_mode="single_system",
    )
    assert standard_schema["properties"]["internal_systems"]["maxItems"] == 1
    assert standard_schema["properties"]["supporting_systems"]["maxItems"] == 0
    projected = apply_semantic_implementation_assignments(
        candidate, edge_object_ids=edge_ids, citation_registry=citation_registry
    )
    projected["clarification"] = {"question": "", "fields": [], "source_refs": []}
    assert projected == completion

def test_completion_schema_binds_each_typed_object_to_its_exact_citations() -> None:
    object_citations = {
        "step.0": ("citation.step",),
        "dependency.0": ("citation.dependency",),
        "constraint.0": ("citation.constraint",),
        "non_goal.0": ("citation.non-goal",),
    }
    edge_ids = {
        "implements": ("step.0",),
        "depends_on": ("dependency.0",),
        "constrained_by": ("constraint.0",),
        "excludes": ("non_goal.0",),
    }
    schema = semantic_graph_completion_schema(
        source_citation_ids=tuple(
            citation_id
            for values in object_citations.values()
            for citation_id in values
        ),
        edge_object_ids=edge_ids,
        topology_mode="adaptive",
        object_citation_ids=object_citations,
    )

    systems = schema["properties"]["internal_systems"]["items"]["properties"]
    for kind, object_id in (
        ("depends_on", "dependency.0"),
        ("constrained_by", "constraint.0"),
        ("excludes", "non_goal.0"),
    ):
        choice = systems[kind]["items"]["anyOf"][0]
        assert choice["properties"]["object_id"]["enum"] == [object_id]
        assert choice["properties"]["source_citation_ids"]["items"]["enum"] == [
            object_citations[object_id][0]
        ]

    assignment = schema["properties"]["implementation_assignments"]["properties"][
        "step.0"
    ]
    assert assignment["properties"]["source_citation_ids"]["items"]["enum"] == [
        "citation.step"
    ]
    boundary_choices = schema["properties"]["supporting_systems"]["items"][
        "properties"
    ]["boundary_links"]["items"]["anyOf"]
    assert {
        (
            choice["properties"]["kind"]["enum"][0],
            choice["properties"]["object_id"]["enum"][0],
            choice["properties"]["source_citation_ids"]["items"]["enum"][0],
        )
        for choice in boundary_choices
    } == {
        ("depends_on", "dependency.0", "citation.dependency"),
        ("constrained_by", "constraint.0", "citation.constraint"),
        ("excludes", "non_goal.0", "citation.non-goal"),
    }
    assert "oneOf" not in json.dumps(schema)


def test_narrative_projection_is_typed_distinct_and_quantity_safe() -> None:
    source, completion = _layers(semantic_intent_packet())
    expected = semantic_intent_packet()
    author = compile_layered_authoring_graph(
        source,
        completion,
        assessment=expected["materiality_assessment"],
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )
    narratives = author["semantic_extension"]["narratives"]
    texts = [row["text"] for row in narratives]

    assert len(texts) == len(set(texts))
    assert all("%" not in text and "100" not in text for text in texts)
    assert all(row["fact_ids"] and row["source_refs"] for row in narratives)
    assert max(len(row["source_refs"]) for row in narratives) <= 8
    assert any("visible" in row["text"] for row in narratives if row["field"] == "success_metric")
    assert any(
        row["text"]
        == (
            "When the “Receive receipt” step completes, the path makes "
            "the “Claim receipt” result visible."
        )
        for row in narratives
    )
    assert any(
        row["text"]
        == (
            "Evidence must show that the “Receive receipt” step produced "
            "the “Claim receipt” result."
        )
        for row in narratives
    )
    assert all(not row["text"].startswith("After ") for row in narratives)


def test_product_fact_projection_never_reuses_raw_source_envelope_copy() -> None:
    semantic_intent = deepcopy(semantic_intent_packet()["semantic_intent"])
    raw_envelope = '{"product_intent":{"first_path":"opaque source envelope"}}'
    source_kinds = {
        "workflow_step",
        "state_object",
        "visible_output",
        "external_system",
        "operational_constraint",
        "non_goal",
        "assumption",
        "ambiguity",
    }
    for fact in semantic_intent["facts"]:
        if fact["kind"] in source_kinds:
            fact["statement"] = raw_envelope
        if fact["kind"] == "actor":
            fact["attributes"] = [
                row for row in fact["attributes"] if row["name"] != "responsibility"
            ]

    projected = semantic_intent_product_facts(semantic_intent)

    assert raw_envelope not in json.dumps(projected, sort_keys=True)
    assert projected["first_path"] == "Claim one ready card. Receive a claim receipt."
    assert projected["state_objects"] == ["Card"]
    assert projected["visible_outputs"] == ["Claim receipt"]
    assert projected["operational_constraints"] == ["Read local duty roster"]
    assert projected["non_goals"] == ["No automatic reassignment"]
    assert projected["human_actors"] == ["Shift coordinator"]


def test_completion_derives_active_supporting_topology_from_disjoint_system_roles() -> None:
    source_ref = {"source_id": "operator_prompt", "quote": "evidence", "occurrence": 1}
    candidate = {
        "internal_systems": [
            {
                "depends_on": [],
            }
        ],
        "supporting_systems": [
            {
                "boundary_links": [
                    {
                        "kind": "depends_on",
                        "object_id": "dependency.0",
                        "source_citation_ids": ["citation.0"],
                    }
                ],
                "supporting_consumers": {
                    "system_indices": [0, 0],
                    "source_citation_ids": ["citation.0"],
                },
            },
        ],
        "implementation_assignments": {
            "step.0": {
                "system_indices": [0],
                "source_citation_ids": ["citation.0"],
            }
        },
    }

    projected = apply_semantic_implementation_assignments(
        candidate,
        edge_object_ids={"implements": ("step.0",), "depends_on": ("dependency.0",)},
        citation_registry={
            "citation.0": {"source_ref": source_ref, "fact_ids": ("fact.0",)}
        },
    )

    assert projected["internal_systems"][0]["release_scope"] == "first_path_required"
    assert projected["internal_systems"][0]["depends_on"] == [
        {"object_id": "system.1", "source_refs": [source_ref]}
    ]
    assert projected["internal_systems"][1]["release_scope"] == "first_path_required"
    assert projected["internal_systems"][1]["depends_on"] == [
        {"object_id": "dependency.0", "source_refs": [source_ref]}
    ]


def test_resultless_completion_system_without_typed_consumer_fails_closed() -> None:
    candidate = {
        "internal_systems": [
            {"depends_on": []},
        ],
        "supporting_systems": [
            {
                "boundary_links": [],
                "supporting_consumers": {
                    "system_indices": [],
                    "source_citation_ids": ["citation.0"],
                },
            },
        ],
        "implementation_assignments": {
            "step.0": {
                "system_indices": [0],
                "source_citation_ids": ["citation.0"],
            }
        },
    }

    with pytest.raises(
        ValueError, match="resultless Semantic Intent system lacks typed supporting topology"
    ):
        apply_semantic_implementation_assignments(
            candidate,
            edge_object_ids={"implements": ("step.0",)},
            citation_registry={
                "citation.0": {
                    "source_ref": {"source_id": "x", "quote": "y", "occurrence": 1},
                    "fact_ids": ("fact.0",),
                }
            },
        )


def test_supporting_boundary_cannot_cross_typed_relation_domains() -> None:
    source_ref = {"source_id": "operator_prompt", "quote": "evidence", "occurrence": 1}
    candidate = {
        "internal_systems": [{"depends_on": []}],
        "supporting_systems": [
            {
                "boundary_links": [
                    {
                        "kind": "depends_on",
                        "object_id": "constraint.0",
                        "source_citation_ids": ["citation.0"],
                    }
                ],
                "supporting_consumers": {
                    "system_indices": [0],
                    "source_citation_ids": ["citation.0"],
                },
            }
        ],
        "implementation_assignments": {
            "step.0": {
                "system_indices": [0],
                "source_citation_ids": ["citation.0"],
            }
        },
    }

    with pytest.raises(
        ValueError, match="Semantic supporting boundary has an invalid typed target"
    ):
        apply_semantic_implementation_assignments(
            candidate,
            edge_object_ids={
                "implements": ("step.0",),
                "depends_on": ("dependency.0",),
                "constrained_by": ("constraint.0",),
            },
            citation_registry={
                "citation.0": {"source_ref": source_ref, "fact_ids": ("fact.0",)}
            },
        )


def test_completion_citations_cannot_bypass_or_escape_atomic_custody() -> None:
    source_ref = {"source_id": "operator_prompt", "quote": "evidence", "occurrence": 1}
    edge_ids = {"implements": ()}
    registry = {
        "citation.0": {"source_ref": source_ref, "fact_ids": ("fact.0",)}
    }

    with pytest.raises(ValueError, match="bypasses typed atomic citations"):
        apply_semantic_implementation_assignments(
            {"source_refs": [source_ref]},
            edge_object_ids=edge_ids,
            citation_registry=registry,
        )
    with pytest.raises(ValueError, match="invalid source citation"):
        apply_semantic_implementation_assignments(
            {"source_citation_ids": ["citation.missing"]},
            edge_object_ids=edge_ids,
            citation_registry=registry,
        )


def test_atomic_citation_handles_enforce_the_final_eight_span_limit() -> None:
    refs = [
        {
            "source_id": "operator_prompt",
            "quote": f"evidence {index}",
            "occurrence": 1,
        }
        for index in range(9)
    ]
    registry = {
        f"citation.{index}": {
            "source_ref": ref,
            "fact_ids": (f"fact.{index // 3}",),
        }
        for index, ref in enumerate(refs)
    }
    candidate = {
        "source_citation_ids": list(registry)[:8],
        "internal_systems": [],
        "supporting_systems": [],
        "implementation_assignments": {},
    }
    accepted = apply_semantic_implementation_assignments(
        candidate,
        edge_object_ids={"implements": ()},
        citation_registry=registry,
    )
    assert accepted["source_refs"] == refs[:8]
    with pytest.raises(ValueError, match="invalid source citation"):
        apply_semantic_implementation_assignments(
            {**candidate, "source_citation_ids": list(registry)},
            edge_object_ids={"implements": ()},
            citation_registry=registry,
        )


def test_external_dependency_does_not_invent_an_unspecified_access_mode() -> None:
    source, _ = _layers(semantic_intent_packet())
    partitioned = _partitioned_source(source)
    dependency = partitioned["boundary"]["external_systems"][0]
    dependency["access_mode"] = None

    compiled = compile_source_partitioned_graph(partitioned)

    external = next(row for row in compiled["facts"] if row["kind"] == "external_system")
    assert "access_mode" not in external


def test_source_dependency_consumer_preserves_exact_workflow_ownership() -> None:
    source, _ = _layers(semantic_intent_packet())
    partitioned = _partitioned_source(source)
    dependency = partitioned["boundary"]["external_systems"][0]
    dependency["consumer"] = {"kind": "workflow_step", "step_index": 0}

    compiled = compile_source_partitioned_graph(partitioned)
    dependency_relation = next(
        row for row in compiled["relations"] if row["kind"] == "depends_on"
    )

    assert dependency_relation["subject_id"] == "step.0"
    assert dependency_relation["object_id"] == "dependency.0"


def test_source_dependency_without_supported_consumer_emits_no_relation() -> None:
    source, _ = _layers(semantic_intent_packet())
    partitioned = _partitioned_source(source)
    partitioned["boundary"]["external_systems"][0]["consumer"] = None

    compiled = compile_source_partitioned_graph(partitioned)

    assert any(row["kind"] == "external_system" for row in compiled["facts"])
    assert not any(row["kind"] == "depends_on" for row in compiled["relations"])


def test_source_step_edges_are_kind_typed_before_graph_compilation() -> None:
    source, _ = _layers(semantic_intent_packet())
    partitioned = _partitioned_source(source)

    compiled = compile_source_partitioned_graph(partitioned)

    assert all(
        row["object_id"].startswith("state.")
        for row in compiled["relations"]
        if row["kind"] == "changes"
    )
    assert all(
        row["object_id"].startswith("output.")
        for row in compiled["relations"]
        if row["kind"] == "produces"
    )

    invalid = deepcopy(partitioned)
    invalid["path"]["visible_outputs"][0]["producer"]["step_index"] = 999
    try:
        compile_source_partitioned_graph(invalid)
    except ValueError as error:
        assert str(error) == "Semantic source output producer has an invalid step"
    else:
        raise AssertionError("an invalid output producer must fail closed")

    stable = deepcopy(partitioned)
    transition = next(
        row["transition"] for row in stable["path"]["state_objects"]
        if row["transition"] is not None
    )
    transition["to_state"] = transition["from_state"]
    try:
        compile_source_partitioned_graph(stable)
    except ValueError as error:
        assert str(error) == "Semantic workflow transition does not change state"
    else:
        raise AssertionError("a no-op transition must fail closed")


def test_layered_authoring_owner_has_no_regex_fuzzy_or_token_authority() -> None:
    for source in (
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_layered_authoring.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_narrative_projection.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_source_authoring.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_source_hypothesis_comparison.py"),
        Path("scripts/release/greenfield_semantic_authoring_wave.py"),
        Path("scripts/release/greenfield_semantic_standard_path_experiment.py"),
    ):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imports.isdisjoint(
            {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
        )


def test_provider_handle_binding_removes_source_transcription_authorship() -> None:
    evidence = {"operator_prompt": "card then card", "operator_edit": ""}
    catalog = semantic_evidence_block_catalog(evidence)
    bound = bind_semantic_evidence_blocks(
        {"source_refs": [{"ref_id": "operator_prompt.block.0"}]}, catalog=catalog
    )

    assert bound == {
        "source_refs": [
            {
                "source_id": "operator_prompt",
                "quote": "card then card",
                "occurrence": 1,
            }
        ]
    }


def test_completion_and_presentation_receive_only_source_bound_evidence() -> None:
    catalog = {
        "operator_prompt.block.0": {"quote": "accepted"},
        "operator_prompt.block.1": {"quote": "discarded"},
    }
    core = {
        "version": "test",
        "source": {
            "version": "source",
            "path": {"source_refs": [{"ref_id": "operator_prompt.block.0"}]},
            "boundary": {
                "discarded_evidence": [
                    {"source_refs": [{"ref_id": "operator_prompt.block.1"}]}
                ]
            },
        },
        "completion": {
            "facts": {"source_refs": [{"ref_id": "operator_prompt.block.0"}]}
        },
    }

    assert accepted_partitioned_evidence_catalog(core, catalog=catalog) == {
        "operator_prompt.block.0": {"quote": "accepted"}
    }

    core["completion"]["facts"]["source_refs"] = [
        {"ref_id": "operator_prompt.block.1"}
    ]
    try:
        accepted_partitioned_evidence_catalog(core, catalog=catalog)
    except ValueError as error:
        assert str(error) == (
            "Semantic completion cites evidence not bound to source truth"
        )
    else:
        raise AssertionError("completion-only evidence must fail before presentation")


def test_discarded_evidence_is_not_compiled_as_product_truth() -> None:
    expected = semantic_intent_packet()
    source, _ = _layers(expected)
    candidate = _partitioned_source(source)
    candidate["boundary"]["discarded_evidence"] = [
        {
            "label": "retired brainstorm label",
            "source_refs": [deepcopy(source["facts"][0]["source_refs"][0])],
        }
    ]

    compiled = compile_source_partitioned_graph(candidate)

    assert all(row["kind"] != "discarded_evidence" for row in compiled["facts"])
    assert "retired brainstorm label" not in json.dumps(compiled)


def test_source_material_ambiguity_is_typed_before_product_graph_compilation() -> None:
    source, _ = _layers(semantic_intent_packet())
    candidate = _partitioned_source(source)
    candidate["boundary"]["ambiguities"] = [
        {
            "label": "First workflow step has two incompatible instructions",
            "materiality_field": "first_path",
            "question": "Should the existing record be selected or a new record be imported first?",
            "source_refs": [
                deepcopy(source["facts"][1]["source_refs"][0]),
                deepcopy(source["facts"][2]["source_refs"][0]),
            ],
        }
    ]

    compiled = compile_source_partitioned_graph(candidate)
    ambiguity = next(row for row in compiled["facts"] if row["kind"] == "ambiguity")

    assert ambiguity["materiality_field"] == "first_path"
    assert ambiguity["question"].startswith("Should the existing record")


def test_partitioned_completion_cannot_reintroduce_a_discarded_label() -> None:
    expected = semantic_intent_packet()
    source, completion = _layers(expected)
    for row in completion["internal_systems"]:
        row.pop("fact_id", None)
    candidate = _partitioned_source(source)
    discarded_ref = {
        "source_id": "operator_prompt",
        "quote": "Rejected interpretations stay inspectable as evidence but never enter the "
        "accepted acceptance state.",
        "occurrence": 1,
    }
    candidate["boundary"]["discarded_evidence"] = [{
        "label": "Rejected interpretations",
        "source_refs": [discarded_ref],
    }]
    completion["internal_systems"][0]["outside_boundary"] = (
        "Rejected interpretations"
    )

    with pytest.raises(ValueError, match="contains a discarded label"):
        compile_partitioned_authoring_graph(
            {
                "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
                "source": candidate,
                "completion": completion,
            },
            assessment=expected["materiality_assessment"],
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
        )


def test_completion_overcitation_drops_only_the_discarded_exact_citation() -> None:
    accepted = {
        "source_id": "operator_prompt",
        "quote": "Generate a simulated sequence.",
        "occurrence": 1,
    }
    discarded = {
        "source_id": "operator_prompt",
        "quote": "The trial label Mossy Compass is excluded.",
        "occurrence": 1,
    }
    completion = {
        "internal_systems": [
            {
                "label": "Sequence Preview Service",
                "source_refs": [accepted, discarded],
            }
        ]
    }

    filtered = completion_without_discarded_citations(
        [{"label": "Trial label Mossy Compass", "source_refs": [discarded]}],
        completion,
    )

    assert filtered["internal_systems"][0]["source_refs"] == [accepted]
    with pytest.raises(ValueError, match="only discarded evidence"):
        completion_without_discarded_citations(
            [{"label": "Trial label Mossy Compass", "source_refs": [discarded]}],
            {"internal_systems": [{"source_refs": [discarded]}]},
        )


def test_explicit_nonmaterial_output_detail_stays_on_the_output_not_an_assumption() -> None:
    expected = semantic_intent_packet()
    source, _ = _layers(expected)
    candidate = _partitioned_source(source)
    for output in candidate["path"]["visible_outputs"]:
        output["condition"] = None
    candidate["path"]["visible_outputs"][0]["condition"] = (
        "No wording or icon scheme is provided."
    )

    compiled = compile_source_partitioned_graph(candidate)
    visible_output = next(
        row for row in compiled["facts"] if row["kind"] == "visible_output"
    )

    assert visible_output["condition"] == "No wording or icon scheme is provided."
    assert all(row["kind"] != "assumption" for row in compiled["facts"])


def test_provider_catalog_does_not_offer_an_overbroad_whole_prompt_handle() -> None:
    evidence = {
        "operator_prompt": "First fact. Second fact. Third fact.",
        "operator_edit": "",
    }

    catalog = semantic_evidence_block_catalog(evidence)

    assert [row["quote"] for row in catalog.values()] == [
        "First fact.", "Second fact.", "Third fact."
    ]


def test_repeated_atomic_span_is_one_canonical_critic_candidate() -> None:
    from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
        ATOMIC_SOURCE_CANDIDATES_VERSION,
        require_atomic_source_candidates,
    )

    candidates = require_atomic_source_candidates(
        {
            "version": ATOMIC_SOURCE_CANDIDATES_VERSION,
            "candidates": [
                {
                    "candidate_id": "actor",
                    "source_ref": {
                        "source_id": "operator_prompt",
                        "quote": "Reviewer selects a record.",
                        "occurrence": 1,
                    },
                },
                {
                    "candidate_id": "action",
                    "source_ref": {
                        "source_id": "operator_prompt",
                        "quote": "Reviewer selects a record.",
                        "occurrence": 1,
                    },
                },
            ],
        },
        evidence_sources={
            "operator_prompt": "Reviewer selects a record.",
            "operator_edit": "",
        },
    )

    assert [row["candidate_id"] for row in candidates["candidates"]] == ["actor"]


def _layers(packet: dict) -> tuple[dict, dict]:
    source_facts = []
    bounded_facts = {"internal_systems": []}
    for raw in packet["semantic_intent"]["facts"]:
        row = deepcopy(raw)
        kind = row.pop("kind")
        custody = row.pop("custody")
        if kind != "workflow_step":
            row.pop("owner_kind")
        if custody == "source_fact":
            row.pop("statement")
            row.pop("order")
            attributes = {
                attribute["name"]: attribute["value"]
                for attribute in row.pop("attributes")
            }
            row.update(attributes)
            source_facts.append({**row, "kind": kind})
        else:
            if kind != "internal_system":
                continue
            row.pop("order")
            attributes = {
                attribute["name"]: attribute["value"]
                for attribute in row.pop("attributes")
            }
            row.update(attributes)
            if kind == "internal_system":
                row.update(
                    {
                        edge_kind: []
                        for edge_kind in (
                            "depends_on", "implements", "constrained_by", "excludes"
                        )
                    }
                )
            bounded_facts[COLLECTIONS[kind]].append(row)
    source_relations = []
    for raw in packet["semantic_intent"]["relations"]:
        row = deepcopy(raw)
        kind = row.pop("kind")
        row.pop("fact_id", None)
        custody = row.pop("custody")
        if custody == "source_fact":
            row.pop("relation_id")
            row.pop("order")
            source_relations.append({**row, "kind": kind})
        else:
            row.pop("relation_id")
            row.pop("order")
            subject_id = row.pop("subject_id")
            systems = [
                system
                for system in bounded_facts["internal_systems"]
                if system["fact_id"] == subject_id
            ]
            assert len(systems) == 1
            systems[0][kind].append(row)
    source = {
        "version": SEMANTIC_SOURCE_GRAPH_VERSION,
        "facts": source_facts,
        "relations": source_relations,
    }
    completion = {
        "version": SEMANTIC_COMPLETION_GRAPH_VERSION,
        "status": "complete",
        "clarification": {"question": "", "fields": [], "source_refs": []},
        "internal_systems": bounded_facts["internal_systems"],
        "self_challenge": [
            {"challenge": challenge, "status": "passed"}
            for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
        ],
    }
    return source, completion


def _citation_completion_candidate(
    value: object,
    citation_registry: dict[str, dict],
) -> object:
    if isinstance(value, list):
        return [
            _citation_completion_candidate(item, citation_registry)
            for item in value
        ]
    if not isinstance(value, dict):
        return deepcopy(value)
    result = {
        key: _citation_completion_candidate(item, citation_registry)
        for key, item in value.items()
        if key != "source_refs"
    }
    if "source_refs" not in value:
        return result
    expected = {
        (ref["source_id"], ref["quote"], ref["occurrence"])
        for ref in value["source_refs"]
    }
    matching = [
        citation_id
        for citation_id, row in citation_registry.items()
        if (
            row["source_ref"]["source_id"],
            row["source_ref"]["quote"],
            row["source_ref"]["occurrence"],
        ) in expected
    ]
    actual = {
        (
            citation_registry[citation_id]["source_ref"]["source_id"],
            citation_registry[citation_id]["source_ref"]["quote"],
            citation_registry[citation_id]["source_ref"]["occurrence"],
        )
        for citation_id in matching
    }
    assert actual == expected
    result["source_citation_ids"] = matching
    return result


def _partitioned_source(source: dict) -> dict:
    path = {name: [] for name in SOURCE_PATH_COLLECTIONS}
    boundary = {name: [] for name in SOURCE_BOUNDARY_COLLECTIONS}
    path["relations"] = {kind: [] for kind in SOURCE_PATH_RELATION_KINDS}
    boundary["relations"] = {kind: [] for kind in SOURCE_BOUNDARY_RELATION_KINDS}
    collection_by_kind = {
        kind: (path, name) for name, kind in SOURCE_PATH_COLLECTIONS.items()
    } | {
        kind: (boundary, name) for name, kind in SOURCE_BOUNDARY_COLLECTIONS.items()
    }
    actor_owners = {
        row["subject_id"]: row["object_id"]
        for row in source["relations"]
        if row["kind"] == "owned_by"
    }
    transitions = {
        row["fact_id"]: row["transition"]
        for row in source["facts"] if row["kind"] == "state_object"
    }
    axis_relations = {
        kind: {
            row["object_id"]: row
            for row in source["relations"] if row["kind"] == kind
        }
        for kind in ("changes", "produces")
    }
    workflow_index = 0
    for raw in source["facts"]:
        row = deepcopy(raw)
        kind = row.pop("kind")
        fact_id = row.pop("fact_id")
        if kind in {"operational_constraint", "non_goal"}:
            target, collection = boundary, "policies"
            row["policy_kind"] = {
                "operational_constraint": "operating_invariant",
                "non_goal": "excluded_capability",
            }[kind]
        else:
            target, collection = collection_by_kind[kind]
        if kind == "state_object":
            relation = axis_relations["changes"].get(fact_id)
            row["transition"] = (
                {
                    "step_index": int(relation["subject_id"].removeprefix("step.")),
                    **deepcopy(transitions[fact_id]),
                    "source_refs": deepcopy(relation["source_refs"]),
                }
                if relation is not None else None
            )
        if kind == "external_system":
            relation = next(
                item for item in source["relations"]
                if item["kind"] == "depends_on" and item["object_id"] == fact_id
            )
            subject_id = relation["subject_id"]
            row["consumer"] = (
                {"kind": "identity"} if subject_id == "identity.0"
                else {"kind": "workflow_step", "step_index": int(subject_id.removeprefix("step."))}
            )
        if kind == "visible_output":
            row.setdefault("condition", None)
            relation = axis_relations["produces"][fact_id]
            row["producer"] = {
                "step_index": int(relation["subject_id"].removeprefix("step.")),
                "source_refs": deepcopy(relation["source_refs"]),
            }
        if kind == "workflow_step":
            step_id = f"step.{workflow_index}"
            owner_kind = row.pop("owner_kind")
            owner = {"kind": owner_kind}
            if owner_kind == "actor":
                owner["actor_id"] = actor_owners[step_id]
            groups = target[collection]
            if groups and groups[-1]["owner"] == owner:
                groups[-1]["steps"].append(row)
            else:
                groups.append({"owner": owner, "steps": [row]})
            workflow_index += 1
            continue
        target[collection].append(row)
    for raw in source["relations"]:
        row = deepcopy(raw)
        kind = row.pop("kind")
        if kind in {
            "owned_by", "changes", "produces",
            "depends_on", "constrained_by", "excludes",
        }:
            continue
        target = path if kind in SOURCE_PATH_RELATION_KINDS else boundary
        target["relations"][kind].append(row)
    return {
        "version": SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION,
        "path": path,
        "boundary": boundary,
    }
    apply_semantic_implementation_assignments,
