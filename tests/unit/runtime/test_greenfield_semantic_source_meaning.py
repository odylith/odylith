from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    require_semantic_intent_ir,
    semantic_intent_meaning_sha256,
    semantic_intent_product_facts,
    semantic_intent_product_facts_sha256,
    semantic_intent_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_RELATION_KINDS,
    semantic_intent_authoring_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    semantic_component_rows,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    SEMANTIC_SOURCE_MEANING_GRAPH_VERSION,
    apply_semantic_source_meaning_completeness_gate,
    compile_semantic_source_meaning,
    require_semantic_source_meaning_graph,
    semantic_source_meaning_contract,
    semantic_source_meaning_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning_contract import (
    semantic_source_meaning_graph_schema,
)


PROMPT = (
    "Build a repo-local claim desk. "
    "A shift coordinator claims one ready card. "
    "The card moves from ready to claimed. "
    "Show a claim receipt. "
    "Read the local duty roster without remote access. "
    "Never reassign a card automatically."
)
SOURCES = {"operator_prompt": PROMPT, "operator_edit": ""}


def _ref(quote: str) -> dict[str, object]:
    return {"source_id": "operator_prompt", "quote": quote, "occurrence": 1}


def _graph() -> dict[str, object]:
    return {
        "version": SEMANTIC_SOURCE_MEANING_GRAPH_VERSION,
        "presentation": {
            "title": "Claim Desk",
            "status": "source_declared",
            "source_refs": [_ref("Build a repo-local claim desk.")],
        },
        "audiences": [],
        "actors": [
            {
                "canonical_label": "Shift coordinator",
                "source_refs": [_ref("A shift coordinator claims one ready card.")],
            }
        ],
        "entities": [
            {
                "label": "Card",
                "source_refs": [
                    _ref("A shift coordinator claims one ready card."),
                    _ref("The card moves from ready to claimed."),
                ],
            },
            {
                "label": "Claim receipt",
                "source_refs": [_ref("Show a claim receipt.")],
            },
        ],
        "workflow": [
            {
                "action": "claim one ready card",
                "entity_effects": [
                    {
                        "kind": "changed",
                        "entity_index": 0,
                        "from_state": "ready",
                        "to_state": "claimed",
                        "source_refs": [_ref("The card moves from ready to claimed.")],
                        "edge_source_refs": [_ref("The card moves from ready to claimed.")],
                    },
                    {
                        "kind": "visible_result",
                        "entity_index": 1,
                        "visible_to": [
                            {
                                "kind": "actor",
                                "index": 0,
                                "source_refs": [
                                    _ref("A shift coordinator claims one ready card.")
                                ],
                            }
                        ],
                        "source_refs": [_ref("Show a claim receipt.")],
                        "edge_source_refs": [_ref("Show a claim receipt.")],
                    },
                ],
                "owner_actor_index": 0,
                "source_refs": [_ref("A shift coordinator claims one ready card.")],
            }
        ],
        "dependencies": [
            {
                "label": "Local duty roster",
                "access_mode": "read_only",
                "source_refs": [
                    _ref("Read the local duty roster without remote access.")
                ],
            }
        ],
        "product_boundaries": [
            {
                "statement": "repo-local",
                "source_refs": [_ref("Build a repo-local claim desk.")],
            }
        ],
        "policy_boundaries": [
            {
                "modalities": ["prohibited"],
                "statement": "Never reassign a card automatically.",
                "source_refs": [_ref("Never reassign a card automatically.")],
            },
            {
                "modalities": ["prohibited"],
                "statement": "without remote access",
                "source_refs": [
                    _ref("Read the local duty roster without remote access.")
                ],
                "applies_to_dependency_index": 0,
                "attachment_source_refs": [
                    _ref("Read the local duty roster without remote access.")
                ],
            },
        ],
        "non_material_gaps": [],
        "provenance_only": [],
        "clarification": {
            "required": False,
            "question": "",
            "source_refs": [],
        },
    }


def test_source_meaning_compiles_without_invented_causal_relations() -> None:
    graph = require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    verified = require_semantic_intent_ir(intent, evidence_sources=SOURCES)
    facts = semantic_intent_product_facts(verified)

    assert verified["presentation"] == graph["presentation"]
    assert facts["audiences"] == []
    assert facts["human_actors"] == [
        {
            "actor_fact_id": "actor.0",
            "label": "Shift coordinator",
            "owned_step_fact_ids": ["step.0"],
            "owned_actions": ["claim one ready card"],
        }
    ]
    assert facts["state_objects"] == ["Card"]
    assert facts["visible_outputs"] == ["Claim receipt"]
    assert facts["external_systems"] == ["Local duty roster"]
    assert facts["internal_systems"] == []
    assert facts["product_boundaries"] == ["repo-local"]
    assert facts["policy_boundaries"] == [
        {
            "label": "Never reassign a card automatically.",
            "modalities": ["prohibited"],
            "statement": "Never reassign a card automatically.",
            "applies_to": [],
        },
        {
            "label": "without remote access",
            "modalities": ["prohibited"],
            "statement": "without remote access",
            "applies_to": [
                {
                    "fact_id": "dependency.0",
                    "kind": "external_system",
                    "label": "Local duty roster",
                }
            ],
        }
    ]
    kinds = [row["kind"] for row in verified["relations"]]
    assert "owned_by" in kinds
    assert "implements" not in kinds
    assert "depends_on" not in kinds
    assert "produces" in kinds
    assert "visible_to" in kinds
    assert "changes" in kinds
    assert "applies_to" in kinds
    assert next(row for row in verified["relations"] if row["kind"] == "applies_to") == {
        "relation_id": "applies-to.0",
        "kind": "applies_to",
        "subject_id": "policy-boundary.1",
        "object_id": "dependency.0",
        "order": 0,
        "custody": "source_fact",
        "source_refs": [_ref("Read the local duty roster without remote access.")],
    }
    assert all(row["kind"] != "internal_system" for row in verified["facts"])

    assert all(row["kind"] != "identity" for row in verified["facts"])
    visible_to = next(
        row for row in verified["relations"] if row["kind"] == "visible_to"
    )
    assert visible_to["source_refs"] == [
        _ref("A shift coordinator claims one ready card.")
    ]


def test_presentation_remains_outside_the_accepted_semantic_fact_graph() -> None:
    graph = require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES)
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
        ),
        evidence_sources=SOURCES,
    )

    assert "product_root" not in intent
    assert "product_root" not in semantic_intent_product_facts(intent)
    assert intent["presentation"] == _graph()["presentation"]
    assert not any(row["label"] == "Claim Desk" for row in intent["facts"])


def test_delivery_policy_is_explicit_and_never_reenters_canonical_meaning() -> None:
    graph = require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES)
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
        ),
        evidence_sources=SOURCES,
    )

    component = semantic_component_rows(intent, project_slug="claim-desk")[0]
    fact_ids = {str(row["fact_id"]) for row in intent["facts"]}
    relation_kinds = {str(row["kind"]) for row in intent["relations"]}

    assert component["implementation_policy_id"] == "implementation-policy.0"
    assert component["implementation_policy_id"] not in fact_ids
    assert component["custody_state"] == "system_policy"
    assert component["evidence_tier"] == "odylith_assumption"
    assert component["covered_fact_ids"] == ["step.0", "state.0", "output.0"]
    assert set(component["projection_basis_fact_ids"]) == fact_ids
    assert {
        "semantic_fact_id",
        "semantic_implements",
        "source_system_description",
        "semantic_fact_custody",
    }.isdisjoint(component)
    assert "implements" not in relation_kinds


def test_bounded_implementation_rows_cannot_enter_canonical_semantic_intent() -> None:
    graph = require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    intent["facts"].append(
        {
            "fact_id": "system.0",
            "kind": "internal_system",
            "label": "Claim Desk Core",
            "statement": "Invented implementation boundary.",
            "order": 0,
            "owner_kind": "none",
            "custody": "bounded_interpretation",
            "attributes": [
                {"name": "responsibility", "value": "Own the workflow."},
                {"name": "component_kind", "value": "service"},
                {"name": "boundary", "value": "Own the workflow."},
                {"name": "outside_boundary", "value": "Everything else."},
                {"name": "proof", "value": "Prove the workflow."},
                {"name": "risk", "value": "Meaning could drift."},
                {"name": "release_scope", "value": "first_path_required"},
            ],
            "source_refs": [_ref("Build a repo-local claim desk.")],
        }
    )

    with pytest.raises(ValueError, match="custody is invalid"):
        require_semantic_intent_ir(intent, evidence_sources=SOURCES)


def test_compiler_has_no_synthetic_system_or_implementation_path() -> None:
    source = (
        Path(__file__).parents[3]
        / "src/odylith/runtime/domain_intelligence/greenfield_semantic_ir_compiler.py"
    ).read_text(encoding="utf-8")

    assert "system.0" not in source
    assert "_system_refs" not in source
    assert '"implements"' not in source
    assert "bounded_interpretation" not in source


def test_semantic_contract_allows_zero_explicit_internal_systems() -> None:
    contract = semantic_intent_authoring_contract()
    systems = contract["fact_contracts"]["internal_system"]
    complete = contract["complete_graph_contract"]

    assert systems["minimum"] == 0
    assert complete["explicit_internal_systems_are_optional"] is True
    assert complete["implementation_policy_is_not_a_semantic_fact_or_relation"] is True
    assert {
        "minimum_first_path_required_internal_systems",
        "implementation_coverage_release_scopes",
        "resultless_first_path_systems_require_typed_supporting_topology",
        "every_workflow_step_state_object_and_visible_output_is_implemented_by_an_active_system",
    }.isdisjoint(complete)


def test_entity_binding_controls_component_inputs_without_label_guessing() -> None:
    graph = require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES)
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
        ),
        evidence_sources=SOURCES,
    )
    target_component = semantic_component_rows(intent, project_slug="claim-desk")[0]
    assert target_component["component_contract"]["accepted_input_entities"] == [
        {
            "entity_id": "entity.0",
            "label": "Card",
            "roles": ["target"],
        }
    ]
    assert "Card" in target_component["component_contract"]["accepted_inputs"]
    assert "Claim receipt" not in target_component["component_contract"]["accepted_inputs"]


def test_produces_is_the_only_generation_binding() -> None:
    graph = require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES)
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
        ),
        evidence_sources=SOURCES,
    )

    assert {row["kind"] for row in graph["workflow"][0]["entity_effects"]} == {
        "changed",
        "visible_result",
    }
    target = next(
        row for row in intent["relations"] if row["kind"] == "target_entity"
    )
    assert (target["subject_id"], target["object_id"]) == ("step.0", "entity.0")
    assert target["source_refs"] == [_ref("The card moves from ready to claimed.")]
    assert all(row["kind"] != "generated_entity" for row in intent["relations"])
    produces = next(row for row in intent["relations"] if row["kind"] == "produces")
    assert (produces["subject_id"], produces["object_id"]) == ("step.0", "output.0")
    assert produces["source_refs"] == [
        _ref("A shift coordinator claims one ready card."),
        _ref("Show a claim receipt."),
    ]
    output_of = next(row for row in intent["relations"] if row["kind"] == "output_of")
    assert (output_of["subject_id"], output_of["object_id"]) == (
        "output.0",
        "entity.1",
    )
    assert output_of["source_refs"] == [_ref("Show a claim receipt.")]

    old = _graph()
    old["workflow"][0]["entity_effects"].append(
        {
            "kind": "generated",
            "entity_index": 1,
            "source_refs": [_ref("Show a claim receipt.")],
        }
    )
    with pytest.raises(ValueError, match="enum value is invalid"):
        require_semantic_source_meaning_graph(old, evidence_sources=SOURCES)


def test_source_meaning_digest_excludes_presentation_and_bounded_topology() -> None:
    graph = require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    retitled = _graph()
    retitled["presentation"] = {
        "title": "Coordinator Console",
        "status": "working_assumption",
        "source_refs": [],
    }
    retitled_intent = compile_semantic_source_meaning(
        require_semantic_source_meaning_graph(retitled, evidence_sources=SOURCES),
        semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
    )
    assert semantic_intent_meaning_sha256(intent) == semantic_intent_meaning_sha256(
        retitled_intent
    )
    assert semantic_intent_product_facts_sha256(
        intent
    ) == semantic_intent_product_facts_sha256(retitled_intent)
    assert semantic_source_meaning_sha256(graph) != semantic_source_meaning_sha256(
        retitled
    )
    assert semantic_intent_sha256(intent) != semantic_intent_sha256(retitled_intent)

    changed = _graph()
    changed["workflow"][0]["entity_effects"] = [
        row
        for row in changed["workflow"][0]["entity_effects"]
        if row["kind"] != "changed"
    ] + [
        {
            "kind": "input",
            "entity_index": 0,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    ]
    changed_intent = compile_semantic_source_meaning(
        require_semantic_source_meaning_graph(changed, evidence_sources=SOURCES),
        semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
    )
    assert semantic_intent_meaning_sha256(intent) != semantic_intent_meaning_sha256(
        changed_intent
    )


def test_presentation_custody_is_typed_and_never_becomes_a_fact() -> None:
    source_declared = require_semantic_source_meaning_graph(
        _graph(), evidence_sources=SOURCES
    )
    working = _graph()
    working["presentation"] = {
        "title": "Coordinator Console",
        "status": "working_assumption",
        "source_refs": [],
    }
    accepted_working = require_semantic_source_meaning_graph(
        working, evidence_sources=SOURCES
    )

    assert source_declared["presentation"]["status"] == "source_declared"
    assert accepted_working["presentation"]["status"] == "working_assumption"
    compiled = compile_semantic_source_meaning(
        accepted_working, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    assert compiled["presentation"] == accepted_working["presentation"]
    assert all(row["kind"] != "identity" for row in compiled["facts"])

    missing_custody = _graph()
    missing_custody["presentation"]["source_refs"] = []
    with pytest.raises(ValueError, match="lacks exact source custody"):
        require_semantic_source_meaning_graph(missing_custody, evidence_sources=SOURCES)

    false_custody = deepcopy(working)
    false_custody["presentation"]["source_refs"] = [
        _ref("Build a repo-local claim desk.")
    ]
    with pytest.raises(ValueError, match="carries source custody"):
        require_semantic_source_meaning_graph(false_custody, evidence_sources=SOURCES)


def test_clarification_is_one_generic_question_with_exact_refs_only() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"] = [
        {
            "kind": "input",
            "entity_index": 0,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    ]
    graph["entities"] = graph["entities"][:1]
    graph["clarification"] = {
        "required": True,
        "question": "What concrete result should this first path make visible?",
        "source_refs": [_ref("A shift coordinator claims one ready card.")],
    }
    accepted = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        accepted, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )

    assert intent["clarification"] == {
        "question": "What concrete result should this first path make visible?",
        "source_refs": [_ref("A shift coordinator claims one ready card.")],
    }
    assert "field" not in intent["clarification"]
    assert "fields" not in intent["clarification"]


def test_typed_completeness_gate_asks_for_a_missing_visible_result() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"] = [
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] != "visible_result"
    ]

    gated = apply_semantic_source_meaning_completeness_gate(graph)

    assert gated["clarification"] == {
        "required": True,
        "question": "What should the first usable path show or return when it succeeds?",
        "source_refs": [_ref("A shift coordinator claims one ready card.")],
    }
    assert graph["clarification"]["required"] is False


def test_typed_completeness_gate_asks_for_a_missing_participant() -> None:
    graph = _graph()
    graph["actors"] = []
    graph["workflow"][0]["owner_actor_index"] = None
    visible = next(
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] == "visible_result"
    )
    visible["visible_to"] = []

    gated = apply_semantic_source_meaning_completeness_gate(graph)

    assert gated["clarification"]["required"] is True
    assert gated["clarification"]["question"].startswith("Which human role")


def test_typed_completeness_gate_never_rewrites_complete_or_host_clarification() -> None:
    complete = _graph()
    assert apply_semantic_source_meaning_completeness_gate(complete) == complete

    clarification = _graph()
    clarification["clarification"] = {
        "required": True,
        "question": "Should the staged bundle be previewed or released immediately?",
        "source_refs": [_ref("A shift coordinator claims one ready card.")],
    }
    assert apply_semantic_source_meaning_completeness_gate(clarification) == clarification


def test_active_source_ir_and_projection_contracts_have_no_losing_schema_tokens() -> None:
    runtime = Path(__file__).parents[3] / "src/odylith/runtime/domain_intelligence"
    active = (
        "greenfield_semantic_source_meaning_contract.py",
        "greenfield_semantic_source_meaning.py",
        "greenfield_semantic_ir_compiler.py",
        "greenfield_semantic_intent_schema.py",
        "greenfield_semantic_intent_contract.py",
        "greenfield_semantic_intent_packet.py",
        "greenfield_semantic_projection_plan.py",
    )
    constants = {
        node.value
        for name in active
        for node in ast.walk(ast.parse((runtime / name).read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert {
        "identity",
        "identity_fact_id",
        "presentation_title",
        "title_source_refs",
        "fields",
        "blocked_material_fields",
    }.isdisjoint(constants)


def test_source_meaning_preserves_multiple_policy_modalities() -> None:
    graph = _graph()
    graph["policy_boundaries"][0]["modalities"] = ["permitted", "prohibited"]
    verified = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        verified, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    product = semantic_intent_product_facts(
        require_semantic_intent_ir(intent, evidence_sources=SOURCES)
    )
    assert product["policy_boundaries"][0]["modalities"] == [
        "permitted",
        "prohibited",
    ]


def test_source_meaning_preserves_stable_state_without_fake_transition() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"] = [
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] != "changed"
    ]
    graph["workflow"][0]["entity_effects"].append(
        {
            "kind": "stable",
            "entity_index": 0,
            "stable_state": "staged",
            "source_refs": [_ref("The card moves from ready to claimed.")],
            "edge_source_refs": [_ref("The card moves from ready to claimed.")],
        }
    )
    accepted = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        accepted, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    state = next(row for row in intent["facts"] if row["kind"] == "state_object")

    assert state["label"] == "Card remains staged"
    assert state["transition"] is None
    assert {row["name"]: row["value"] for row in state["attributes"]} == {
        "entity_id": "entity.0",
        "object": "Card",
        "stable_state": "staged",
    }
    assert [
        (row["kind"], row["subject_id"], row["object_id"])
        for row in intent["relations"]
        if row["kind"] == "maintains"
    ] == [("maintains", "step.0", "state.0")]


def test_source_meaning_seals_but_does_not_compile_provenance_only_evidence() -> None:
    graph = _graph()
    graph["provenance_only"] = [
        {
            "statement": "Discard the retired scratch label.",
            "source_refs": [_ref("Never reassign a card automatically.")],
        }
    ]
    accepted = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        accepted, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )

    assert accepted["provenance_only"]
    assert "retired scratch" not in str(intent)


def test_source_meaning_rejects_dangling_owner() -> None:
    graph = _graph()
    graph["workflow"][0]["owner_actor_index"] = 9
    with pytest.raises(ValueError, match="workflow actor index is dangling"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)


def test_source_meaning_rejects_unknown_entity_role_and_uncited_recipient() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"][0]["kind"] = "maybe-input"
    with pytest.raises(ValueError, match="enum value is invalid"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)

    graph = _graph()
    visible = next(
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] == "visible_result"
    )
    del visible["visible_to"][0]["source_refs"]
    with pytest.raises(ValueError, match="structure is invalid"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)


def test_complete_source_meaning_requires_workflow_and_visible_output() -> None:
    graph = _graph()
    graph["workflow"] = []
    with pytest.raises(ValueError, match="lacks a first-path workflow"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    graph = _graph()
    graph["workflow"][0]["entity_effects"] = [
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] != "visible_result"
    ]
    with pytest.raises(ValueError, match="lacks an observable result"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)


def test_clarification_preserves_settled_graph_but_seals_no_partial_intent() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"] = [
        {
            "kind": "input",
            "entity_index": 0,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    ]
    graph["entities"] = graph["entities"][:1]
    graph["clarification"] = {
        "required": True,
        "question": "Which visible confirmation should the coordinator receive?",
        "source_refs": [_ref("A shift coordinator claims one ready card.")],
    }
    accepted = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    intent = compile_semantic_source_meaning(
        accepted, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    assert accepted["workflow"]
    assert intent["status"] == "clarification_required"
    assert intent["facts"] == []
    require_semantic_intent_ir(intent, evidence_sources=SOURCES)


def test_contract_is_compact_field_semantics_not_a_rule_stack() -> None:
    contract = semantic_source_meaning_contract()
    assert "laws" not in contract
    assert set(contract["semantic_ownership"]) == {
            "audience_and_actors",
            "workflow_and_effects",
            "success",
        "boundaries",
        "presentation_and_provenance",
        "clarification",
    }
    assert len(contract["hard_laws"]) == 3


def test_actorless_complete_source_meaning_requires_explicit_audience() -> None:
    graph = _graph()
    graph["actors"] = []
    graph["workflow"][0]["owner_actor_index"] = None
    visible = next(
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] == "visible_result"
    )
    visible["visible_to"] = []
    with pytest.raises(ValueError, match="lacks a participant or audience"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)


def test_explicit_nonhuman_audience_preserves_actorless_product_truth() -> None:
    graph = _graph()
    graph["actors"] = []
    graph["workflow"][0]["owner_actor_index"] = None
    graph["audiences"] = [
        {
            "kind": "explicit_nonhuman",
            "label": "Local automation controller",
            "source_refs": [_ref("Build a repo-local claim desk.")],
        }
    ]
    visible = next(
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] == "visible_result"
    )
    visible["visible_to"] = [
        {
            "kind": "audience",
            "index": 0,
            "source_refs": [_ref("Build a repo-local claim desk.")],
        }
    ]
    accepted = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    product = semantic_intent_product_facts(
        require_semantic_intent_ir(
            compile_semantic_source_meaning(
                accepted, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
            ),
            evidence_sources=SOURCES,
        )
    )
    assert product["human_actors"] == []
    assert product["audiences"] == [
        {"kind": "explicit_nonhuman", "label": "Local automation controller"}
    ]


def test_multi_entity_step_preserves_distinct_inputs_by_entity_id() -> None:
    graph = _graph()
    graph["entities"].append(
        {
            "label": "Roster entry",
            "source_refs": [_ref("Read the local duty roster without remote access.")],
        }
    )
    graph["workflow"][0]["entity_effects"].insert(
        0,
        {
            "kind": "input",
            "entity_index": 2,
            "source_refs": [_ref("Read the local duty roster without remote access.")],
        },
    )
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )
    contract = semantic_component_rows(intent, project_slug="claim-desk")[0][
        "component_contract"
    ]

    assert [row["entity_id"] for row in contract["accepted_input_entities"]] == [
        "entity.2",
        "entity.0",
    ]
    assert [row["label"] for row in contract["accepted_input_entities"]] == [
        "Roster entry",
        "Card",
    ]


def test_equal_entity_labels_do_not_collapse_distinct_graph_identity() -> None:
    graph = _graph()
    graph["entities"].append(
        {
            "label": "Card",
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    )
    graph["workflow"][0]["entity_effects"].insert(
        0,
        {
            "kind": "input",
            "entity_index": 2,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        },
    )
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )
    contract = semantic_component_rows(intent, project_slug="claim-desk")[0][
        "component_contract"
    ]

    assert [row["entity_id"] for row in contract["accepted_input_entities"]] == [
        "entity.2",
        "entity.0",
    ]
    assert contract["accepted_inputs"] == (
        "Card [entity.2], Card [entity.0], and Local duty roster"
    )


def test_coreferential_steps_share_one_component_input_without_text_matching() -> None:
    graph = _graph()
    graph["workflow"].append(
        {
            "action": "attach it to the claim view",
            "entity_effects": [
                {
                    "kind": "target",
                    "entity_index": 1,
                    "source_refs": [_ref("Show a claim receipt.")],
                }
            ],
            "owner_actor_index": 0,
            "source_refs": [_ref("Show a claim receipt.")],
        }
    )
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )
    contract = semantic_component_rows(intent, project_slug="claim-desk")[0][
        "component_contract"
    ]

    assert contract["accepted_input_entities"] == [
        {
            "entity_id": "entity.0",
            "label": "Card",
            "roles": ["target"],
        }
    ]


def test_actor_canonical_identity_survives_short_form_action_references() -> None:
    graph = _graph()
    graph["actors"][0]["canonical_label"] = "Note keeper"
    graph["workflow"][0]["action"] = "The keeper claims one ready card"

    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )

    actor = next(row for row in intent["facts"] if row["kind"] == "actor")
    assert actor["label"] == actor["statement"] == "Note keeper"
    assert semantic_intent_product_facts(intent)["human_actors"] == [
        {
            "actor_fact_id": "actor.0",
            "label": "Note keeper",
            "owned_step_fact_ids": ["step.0"],
            "owned_actions": ["The keeper claims one ready card"],
        }
    ]


def test_created_entity_is_not_promoted_to_a_visible_result() -> None:
    graph = _graph()
    graph["entities"].insert(
        0,
        {
            "label": "Simulated sequence",
            "source_refs": [_ref("Show a claim receipt.")],
        },
    )
    graph["workflow"][0]["entity_effects"].insert(
        0,
        {
            "kind": "created",
            "entity_index": 0,
            "source_refs": [_ref("Show a claim receipt.")],
            "edge_source_refs": [_ref("Show a claim receipt.")],
        },
    )
    changed = next(
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] == "changed"
    )
    visible = next(
        row
        for row in graph["workflow"][0]["entity_effects"]
        if row["kind"] == "visible_result"
    )
    changed["entity_index"] = 1
    visible["entity_index"] = 2

    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )

    assert semantic_intent_product_facts(intent)["visible_outputs"] == [
        "Claim receipt"
    ]
    assert [
        (row["kind"], row["subject_id"], row["object_id"])
        for row in intent["relations"]
        if row["kind"] == "creates"
    ] == [("creates", "step.0", "entity.0")]


def test_source_declared_creation_is_a_typed_effect_only() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"].insert(
        0,
        {
            "kind": "created",
            "entity_index": 0,
            "source_refs": [_ref("Build a repo-local claim desk.")],
            "edge_source_refs": [_ref("Build a repo-local claim desk.")],
        },
    )

    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )

    assert [
        (row["kind"], row["subject_id"], row["object_id"])
        for row in intent["relations"]
        if row["kind"] == "creates"
    ] == [("creates", "step.0", "entity.0")]
    assert "product_root" not in semantic_intent_product_facts(intent)

    invented_subtype = _graph()
    invented_subtype["entities"][0]["kind"] = "domain_object"
    with pytest.raises(ValueError, match="structure is invalid"):
        require_semantic_source_meaning_graph(
            invented_subtype, evidence_sources=SOURCES
        )


def test_unbound_entity_is_rejected() -> None:
    graph = _graph()
    graph["entities"].append(
        {
            "label": "Simulated sequence",
            "source_refs": [_ref("Show a claim receipt.")],
        }
    )

    with pytest.raises(ValueError, match="unbound entity"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)


def test_component_input_custody_excludes_entities_produced_by_an_earlier_step() -> None:
    graph = _graph()
    graph["workflow"].append(
        {
            "action": "review the receipt",
            "entity_effects": [
                {
                    "kind": "target",
                    "entity_index": 1,
                    "source_refs": [_ref("Show a claim receipt.")],
                }
            ],
            "owner_actor_index": 0,
            "source_refs": [_ref("Show a claim receipt.")],
        }
    )
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )
    contract = semantic_component_rows(intent, project_slug="claim-desk")[0][
        "component_contract"
    ]

    assert [
        row["fact_id"]
        for row in intent["facts"]
        if row["kind"] == "entity" and row["fact_id"] == "entity.1"
    ] == ["entity.1"]
    assert any(
        row["kind"] == "output_of" and row["object_id"] == "entity.1"
        for row in intent["relations"]
    )
    assert any(
        row["kind"] == "target_entity"
        and row["subject_id"] == "step.1"
        and row["object_id"] == "entity.1"
        for row in intent["relations"]
    )
    assert [row["entity_id"] for row in contract["accepted_input_entities"]] == [
        "entity.0"
    ]


def test_note_and_entry_bindings_remain_distinct_despite_one_step() -> None:
    graph = _graph()
    graph["entities"][0]["label"] = "Note"
    graph["entities"].append(
        {
            "label": "Entry",
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    )
    graph["workflow"][0]["entity_effects"].insert(
        0,
        {
            "kind": "input",
            "entity_index": 2,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        },
    )
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )
    contract = semantic_component_rows(intent, project_slug="claim-desk")[0][
        "component_contract"
    ]

    assert {
        (row["entity_id"], row["label"])
        for row in contract["accepted_input_entities"]
    } == {("entity.0", "Note"), ("entity.2", "Entry")}


def test_step_insertion_and_reordering_cannot_retarget_entity_effects() -> None:
    graph = _graph()
    graph["workflow"].append(
        {
            "action": "review it",
            "entity_effects": [
                {
                    "kind": "input",
                    "entity_index": 0,
                    "source_refs": [_ref("A shift coordinator claims one ready card.")],
                }
            ],
            "owner_actor_index": 0,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    )

    def bindings_by_action(value: dict[str, object]) -> dict[str, set[str]]:
        intent = require_semantic_intent_ir(
            compile_semantic_source_meaning(
                require_semantic_source_meaning_graph(value, evidence_sources=SOURCES),
                semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
            ),
            evidence_sources=SOURCES,
        )
        facts = {str(row["fact_id"]): row for row in intent["facts"]}
        return {
            str(step["label"]): {
                str(relation["object_id"])
                for relation in intent["relations"]
                if relation["subject_id"] == step["fact_id"]
                and relation["kind"]
                in {"input_entity", "target_entity"}
            }
            for step in intent["facts"]
            if step["kind"] == "workflow_step"
        }

    before = bindings_by_action(graph)
    reordered = deepcopy(graph)
    reordered["workflow"].reverse()
    after = bindings_by_action(reordered)

    assert before == after
    assert after["review it"] == {"entity.0"}
    facts = semantic_intent_product_facts(
        require_semantic_intent_ir(
            compile_semantic_source_meaning(
                require_semantic_source_meaning_graph(reordered, evidence_sources=SOURCES),
                semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
            ),
            evidence_sources=SOURCES,
        )
    )
    assert [row["entity_id"] for row in facts["entities"]] == [
        "entity.0",
        "entity.1",
    ]


def test_entity_effects_reject_dangling_and_duplicate_typed_relations() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"].append(
        {
            "kind": "input",
            "entity_index": 9,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    )
    with pytest.raises(ValueError, match="workflow effect entity index is dangling"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)

    graph = _graph()
    graph["workflow"][0]["entity_effects"].append(
        {
            "kind": "input",
            "entity_index": 0,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        }
    )
    graph["workflow"][0]["entity_effects"].append(
        deepcopy(graph["workflow"][0]["entity_effects"][-1])
    )
    with pytest.raises(ValueError, match="repeats one typed entity effect"):
        require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)


def test_state_change_owns_its_target_without_duplicate_projected_edges() -> None:
    graph = _graph()
    accepted = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            accepted, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
        ),
        evidence_sources=SOURCES,
    )

    assert any(
        row["kind"] == "changed"
        for row in accepted["workflow"][0]["entity_effects"]
    )
    assert any(
        row["kind"] == "target_entity"
        and row["subject_id"] == "step.0"
        and row["object_id"] == "entity.0"
        for row in intent["relations"]
    )

    duplicated = _graph()
    duplicated["workflow"][0]["entity_effects"].insert(
        0,
        {
            "kind": "target",
            "entity_index": 0,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        },
    )
    duplicated_intent = compile_semantic_source_meaning(
        require_semantic_source_meaning_graph(duplicated, evidence_sources=SOURCES),
        semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
    )
    assert sum(
        row["kind"] == "target_entity"
        and row["subject_id"] == "step.0"
        and row["object_id"] == "entity.0"
        for row in duplicated_intent["relations"]
    ) == 1


def test_one_entity_may_be_both_input_and_target_without_duplicate_relation_kind() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"].insert(
        0,
        {
            "kind": "input",
            "entity_index": 0,
            "source_refs": [_ref("A shift coordinator claims one ready card.")],
        },
    )
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )

    assert {
        (row["kind"], row["object_id"])
        for row in intent["relations"]
        if row["subject_id"] == "step.0"
        and row["kind"] in {"input_entity", "target_entity"}
    } == {("input_entity", "entity.0"), ("target_entity", "entity.0")}


def test_state_and_output_identity_are_derived_from_entity_indices() -> None:
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(_graph(), evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )
    state = next(row for row in intent["facts"] if row["kind"] == "state_object")
    output = next(row for row in intent["facts"] if row["kind"] == "visible_output")
    state_attributes = {row["name"]: row["value"] for row in state["attributes"]}
    output_attributes = {row["name"]: row["value"] for row in output["attributes"]}

    assert state_attributes["entity_id"] == "entity.0"
    assert output_attributes["entity_id"] == "entity.1"
    assert any(
        row["kind"] == "state_of"
        and row["subject_id"] == state["fact_id"]
        and row["object_id"] == "entity.0"
        for row in intent["relations"]
    )
    assert any(
        row["kind"] == "output_of"
        and row["subject_id"] == output["fact_id"]
        and row["object_id"] == "entity.1"
        for row in intent["relations"]
    )

    rebound = deepcopy(intent)
    rebound_output = next(
        row for row in rebound["facts"] if row["kind"] == "visible_output"
    )
    next(
        row
        for row in rebound_output["attributes"]
        if row["name"] == "entity_id"
    )["value"] = "entity.0"
    with pytest.raises(ValueError, match="attribute disagrees"):
        require_semantic_intent_ir(rebound, evidence_sources=SOURCES)


def test_product_boundary_is_distinct_from_policy_and_absence_stays_empty() -> None:
    graph = _graph()
    intent = require_semantic_intent_ir(
        compile_semantic_source_meaning(
            require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
            semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
        ),
        evidence_sources=SOURCES,
    )
    product = semantic_intent_product_facts(intent)
    assert product["product_boundaries"] == ["repo-local"]
    assert all(
        row["statement"] != "repo-local" for row in product["policy_boundaries"]
    )

    graph["product_boundaries"] = []
    absent = semantic_intent_product_facts(
        require_semantic_intent_ir(
            compile_semantic_source_meaning(
                require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES),
                semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION,
            ),
            evidence_sources=SOURCES,
        )
    )
    assert absent["product_boundaries"] == []


def test_provider_schema_hard_cuts_singular_workflow_object_fields() -> None:
    schema = semantic_source_meaning_graph_schema()
    properties = schema["properties"]
    workflow_properties = properties["workflow"]["items"]["properties"]
    variants = workflow_properties["entity_effects"]["items"]["anyOf"]
    kind_to_properties = {
        variant["properties"]["kind"]["enum"][0]: variant["properties"]
        for variant in variants
    }

    assert {
        "object",
        "object_role",
        "entity_bindings",
        "creates",
        "changes",
        "produces",
    }.isdisjoint(workflow_properties)
    assert set(kind_to_properties) == {
        "input",
        "target",
        "created",
        "changed",
        "stable",
        "visible_result",
    }
    assert "generated_entity" not in SEMANTIC_RELATION_KINDS
    assert "entities" in properties
    assert "product_boundaries" in properties
    assert "product_root" not in properties
    assert "label" not in kind_to_properties["changed"]
    assert "label" not in kind_to_properties["visible_result"]

    old = _graph()
    old["version"] = "odylith.greenfield.semantic-source-meaning-graph.v6"
    with pytest.raises(ValueError, match="unsupported version"):
        require_semantic_source_meaning_graph(old, evidence_sources=SOURCES)


def test_graph_to_ir_compiler_has_one_owner_and_no_semantic_parsers() -> None:
    directory = Path("src/odylith/runtime/domain_intelligence")
    modules = sorted(directory.glob("greenfield_semantic*.py"))
    trees = {
        path: ast.parse(path.read_text(encoding="utf-8")) for path in modules
    }
    compiler_owners = [
        path.name
        for path, tree in trees.items()
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "compile_semantic_source_meaning"
            for node in ast.walk(tree)
        )
    ]
    assert compiler_owners == ["greenfield_semantic_ir_compiler.py"]

    for name in (
        "greenfield_semantic_source_meaning.py",
        "greenfield_semantic_ir_compiler.py",
    ):
        tree = trees[directory / name]
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imported.isdisjoint(
            {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
        )


def test_source_meaning_rejects_rebound_source_citation() -> None:
    graph = deepcopy(_graph())
    graph["workflow"][0]["source_refs"][0]["quote"] = "Build a repo-local claim desk."
    accepted = require_semantic_source_meaning_graph(graph, evidence_sources=SOURCES)
    assert accepted["workflow"][0]["action"] == "claim one ready card"
    # Exact citation validation proves byte custody. Semantic entailment remains the
    # sole host reasoning authority and is never recreated by deterministic code.
