from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    PARALLEL_MATERIALITY_DECISION_VERSION,
    admit_source_candidates_by_materiality,
    align_source_policy_kinds_to_materiality,
    assemble_parallel_materiality_assessment,
    authorized_source_assumption_fields,
    canonical_parallel_materiality_decision,
    materiality_policy_conflict_refs,
    materiality_authorization_view,
    parallel_materiality_decision_schema,
    policy_kind_disagreement_clarification,
    require_authorized_source_assumptions,
    require_materiality_source_coverage,
    source_with_authorized_assumptions,
    settle_independently_confirmed_policy_kinds,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
    SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
    combine_source_authoring_partitions,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_materiality_assessment,
)


def _decision() -> dict:
    assessment = semantic_materiality_assessment()
    fields = {
        row["field"]: {
            key: value for key, value in row.items() if key != "field"
        }
        for row in assessment["fields"]
    }
    if assessment["decision"] == "clarification_required":
        clarification = assessment["clarification"]
        fields[clarification["field"]] = {
            "status": "explicit",
            "source_refs": clarification["source_refs"],
            "alternatives": [],
        }
    return {
        "version": PARALLEL_MATERIALITY_DECISION_VERSION,
        "outcome": {
            "decision": assessment["decision"],
            "clarification": assessment["clarification"],
        },
        "fields": fields,
    }


def _workflow_candidate(source_refs: list[dict], label: str) -> dict:
    return {
        "label": label,
        "action": label,
        "action_phrase": label.lower(),
        "source_refs": deepcopy(source_refs),
    }


def test_parallel_materiality_joins_decision_and_untyped_spans_only() -> None:
    expected = semantic_materiality_assessment()
    assessment = assemble_parallel_materiality_assessment(
        _decision(),
        expected["source_candidates"],
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )

    assert assessment == expected
    schema = parallel_materiality_decision_schema()
    variants = schema["properties"]["outcome"]["anyOf"]
    assert len(variants) == 2
    assert variants[0]["properties"]["decision"]["enum"] == ["authorize_graph"]
    assert variants[1]["properties"]["decision"]["enum"] == [
        "clarification_required"
    ]
    assert set(schema["properties"]) == {"version", "outcome", "fields"}
    assert set(
        schema["properties"]["fields"]["required"]
    ) == {row["field"] for row in expected["fields"]}
    assert all(
        set(candidate) == {"candidate_id", "source_ref"}
        for candidate in assessment["source_candidates"]["candidates"]
    )


def test_materiality_authorization_does_not_turn_evidence_refs_into_semantic_kinds() -> None:
    authorization = materiality_authorization_view(
        canonical_parallel_materiality_decision(_decision())
    )

    assert authorization["decision"] == "authorize_graph"
    assert set(authorization["fields"]) == {
        row["field"] for row in semantic_materiality_assessment()["fields"]
    }
    assert "source_refs" not in str(authorization)


def test_final_materiality_citations_own_source_policy_semantic_kinds() -> None:
    broadcast_ref = {
        "source_id": "operator_prompt",
        "quote": "Do not broadcast the acceptance.",
        "occurrence": 0,
    }
    messaging_ref = {
        "source_id": "operator_prompt",
        "quote": "Do not call any messaging service.",
        "occurrence": 0,
    }
    unrelated_ref = {
        "source_id": "operator_prompt",
        "quote": "Keep the acceptance local.",
        "occurrence": 0,
    }
    decision = _decision()
    decision["fields"]["constraint"] = {
        "status": "explicit",
        "source_refs": [messaging_ref],
        "alternatives": [],
    }
    decision["fields"]["non_goal"] = {
        "status": "explicit",
        "source_refs": [broadcast_ref],
        "alternatives": [],
    }
    source = {
        "boundary": {
            "policies": [
                {
                    "label": "No broadcast",
                    "policy_kind": "operating_invariant",
                    "source_refs": [broadcast_ref],
                },
                {
                    "label": "No messaging service",
                    "policy_kind": "excluded_capability",
                    "source_refs": [messaging_ref],
                },
                {
                    "label": "Local acceptance",
                    "policy_kind": "operating_invariant",
                    "source_refs": [unrelated_ref],
                },
            ]
        }
    }

    aligned = align_source_policy_kinds_to_materiality(source, decision)

    assert [
        (row["label"], row["policy_kind"])
        for row in aligned["boundary"]["policies"]
    ] == [
        ("No broadcast", "excluded_capability"),
        ("No messaging service", "operating_invariant"),
        ("Local acceptance", "operating_invariant"),
    ]
    assert source["boundary"]["policies"][0]["policy_kind"] == "operating_invariant"


def test_one_source_policy_is_partitioned_by_exact_final_semantic_citations() -> None:
    broadcast_ref = {
        "source_id": "operator_prompt",
        "quote": "Do not broadcast the acceptance.",
        "occurrence": 0,
    }
    messaging_ref = {
        "source_id": "operator_prompt",
        "quote": "Do not call any messaging service.",
        "occurrence": 0,
    }
    decision = _decision()
    decision["fields"]["constraint"] = {
        "status": "explicit",
        "source_refs": [messaging_ref],
        "alternatives": [],
    }
    decision["fields"]["non_goal"] = {
        "status": "explicit",
        "source_refs": [broadcast_ref],
        "alternatives": [],
    }
    source = {
        "boundary": {
            "policies": [
                {
                    "label": "Communication boundary",
                    "policy_kind": "operating_invariant",
                    "source_refs": [broadcast_ref, messaging_ref],
                }
            ]
        }
    }

    aligned = align_source_policy_kinds_to_materiality(source, decision)

    assert aligned["boundary"]["policies"] == [
        {
            "label": "Do not broadcast the acceptance.",
            "policy_kind": "excluded_capability",
            "source_refs": [broadcast_ref],
        },
        {
            "label": "Do not call any messaging service.",
            "policy_kind": "operating_invariant",
            "source_refs": [messaging_ref],
        },
    ]
    assert source["boundary"]["policies"][0]["label"] == "Communication boundary"


def test_one_exact_citation_cannot_own_two_final_semantic_kinds() -> None:
    shared_ref = {
        "source_id": "operator_prompt",
        "quote": "Keep the accepted operation local.",
        "occurrence": 0,
    }
    decision = _decision()
    for field in ("constraint", "non_goal"):
        decision["fields"][field] = {
            "status": "explicit",
            "source_refs": [shared_ref],
            "alternatives": [],
        }
    source = {
        "boundary": {
            "policies": [
                {
                    "label": "Local operation",
                    "policy_kind": "operating_invariant",
                    "source_refs": [shared_ref],
                },
                {
                    "label": "Another boundary",
                    "policy_kind": "excluded_capability",
                    "source_refs": [
                        {
                            "source_id": "operator_prompt",
                            "quote": "Exclude a separate capability.",
                            "occurrence": 0,
                        }
                    ],
                },
            ]
        }
    }

    with pytest.raises(ValueError, match="source citation spans conflicting"):
        align_source_policy_kinds_to_materiality(source, decision)


def test_independent_policy_agreement_settles_or_clarifies_critic_conflation() -> None:
    shared_ref = {
        "source_id": "operator_prompt",
        "quote": "Do not notify anyone automatically.",
        "occurrence": 1,
    }
    decision = _decision()
    for field in ("constraint", "non_goal"):
        decision["fields"][field] = {
            "status": "explicit",
            "source_refs": [shared_ref],
            "alternatives": [],
        }

    assert materiality_policy_conflict_refs(decision) == [shared_ref]
    settled = settle_independently_confirmed_policy_kinds(
        decision,
        assignments={
            ("operator_prompt", shared_ref["quote"], 1): "operating_invariant"
        },
    )
    assert settled["fields"]["constraint"]["source_refs"] == [shared_ref]
    assert settled["fields"]["non_goal"] == {
        "status": "nonmaterial_assumption",
        "source_refs": [],
        "alternatives": [],
    }

    clarification = policy_kind_disagreement_clarification(
        decision,
        source_refs=[shared_ref],
    )
    assert clarification["outcome"]["decision"] == "clarification_required"
    assert clarification["outcome"]["clarification"]["field"] == "non_goal"
    assert canonical_parallel_materiality_decision(clarification)[
        "clarification"
    ]["source_refs"] == [shared_ref]


def test_critic_settled_axes_cannot_disappear_from_source_graph() -> None:
    decision = _decision()
    refs_by_field = {
        field: deepcopy(row["source_refs"])
        for field, row in decision["fields"].items()
    }
    source = {
        "facts": [
            {"kind": "identity", "source_refs": refs_by_field["identity"]},
            {"kind": "workflow_step", "source_refs": refs_by_field["first_path"]},
            {"kind": "state_object", "source_refs": refs_by_field["state_object"]},
            {"kind": "visible_output", "source_refs": refs_by_field["visible_result"]},
            {"kind": "external_system", "source_refs": refs_by_field["dependency"]},
        ]
    }
    evidence = {"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""}
    require_materiality_source_coverage(
        decision, source, evidence_sources=evidence
    )
    source["facts"] = [
        row for row in source["facts"] if row["kind"] != "external_system"
    ]

    with pytest.raises(ValueError, match="critic-settled `dependency`"):
        require_materiality_source_coverage(
            decision, source, evidence_sources=evidence
        )


def test_host_typed_dependency_action_is_valid_workflow_evidence() -> None:
    decision = _decision()
    refs_by_field = {
        field: deepcopy(row["source_refs"])
        for field, row in decision["fields"].items()
    }
    source = {
        "facts": [
            {"kind": "identity", "source_refs": refs_by_field["identity"]},
            {"kind": "workflow_step", "source_refs": refs_by_field["first_path"]},
            {"kind": "workflow_step", "source_refs": refs_by_field["dependency"]},
            {"kind": "state_object", "source_refs": refs_by_field["state_object"]},
            {"kind": "visible_output", "source_refs": refs_by_field["visible_result"]},
            {"kind": "external_system", "source_refs": refs_by_field["dependency"]},
        ]
    }

    require_materiality_source_coverage(
        decision,
        source,
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )


def test_source_graph_may_preserve_exact_facts_beyond_critic_examples() -> None:
    extra_evidence = "Supervisors record the accepted claim."
    alternate_state_evidence = "The accepted claim remains reviewable."
    prompt = f"{SEMANTIC_PROMPT} {extra_evidence} {alternate_state_evidence}"
    decision = _decision()
    refs = {
        field: deepcopy(row["source_refs"])
        for field, row in decision["fields"].items()
    }
    source = {
        "facts": [
            {"kind": "identity", "source_refs": refs["identity"]},
            {"kind": "workflow_step", "source_refs": refs["first_path"]},
            {
                "kind": "workflow_step",
                "source_refs": [{
                    "source_id": "operator_prompt",
                    "quote": extra_evidence,
                    "occurrence": 1,
                }],
            },
            {
                "kind": "state_object",
                "source_refs": [{
                    "source_id": "operator_prompt",
                    "quote": alternate_state_evidence,
                    "occurrence": 1,
                }],
            },
            {"kind": "visible_output", "source_refs": refs["visible_result"]},
            {"kind": "external_system", "source_refs": refs["dependency"]},
        ]
    }

    require_materiality_source_coverage(
        decision,
        source,
        evidence_sources={"operator_prompt": prompt, "operator_edit": ""},
    )


def test_state_and_output_events_are_valid_workflow_evidence() -> None:
    decision = _decision()
    refs = {
        field: deepcopy(row["source_refs"])
        for field, row in decision["fields"].items()
    }
    source = {
        "facts": [
            {"kind": "identity", "source_refs": refs["identity"]},
            {"kind": "workflow_step", "source_refs": refs["first_path"]},
            {"kind": "workflow_step", "source_refs": refs["state_object"]},
            {"kind": "workflow_step", "source_refs": refs["visible_result"]},
            {"kind": "state_object", "source_refs": refs["state_object"]},
            {"kind": "visible_output", "source_refs": refs["visible_result"]},
            {"kind": "external_system", "source_refs": refs["dependency"]},
        ]
    }

    require_materiality_source_coverage(
        decision,
        source,
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )


def test_admission_preserves_dependency_actions_and_their_typed_edges() -> None:
    decision = _decision()
    refs = {
        field: deepcopy(row["source_refs"])
        for field, row in decision["fields"].items()
    }
    source = combine_source_authoring_partitions(
        {
            "version": SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
            "path": {
                "identities": [
                    {
                        "label": "Claim desk",
                        "source_title": "Claim desk",
                        "source_refs": refs["identity"],
                    }
                ],
                "actors": [],
                "workflow_steps": [
                    {
                        "owner": {"kind": "product"},
                        "steps": [
                            _workflow_candidate(refs["first_path"], "Accept claim"),
                            _workflow_candidate(refs["dependency"], "Read ledger"),
                        ],
                    }
                ],
                "state_objects": [
                    {
                        "label": "Card claim state",
                        "object": "card",
                        "source_refs": refs["identity"],
                        "transition": {
                            "from_state": "ready",
                            "to_state": "claimed",
                            "step_index": 0,
                            "source_refs": refs["state_object"],
                        },
                    }
                ],
                "visible_outputs": [
                    {
                        "label": "Claim receipt",
                        "condition": None,
                        "producer": {
                            "step_index": 0,
                            "source_refs": refs["visible_result"],
                        },
                        "source_refs": refs["visible_result"],
                    }
                ],
                "relations": {},
            },
        },
        {
            "version": SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
            "boundary": {
                "external_systems": [
                    {
                        "label": "Claim ledger",
                        "access_mode": "read",
                        "consumer": {"kind": "workflow_step", "step_index": 1},
                        "source_refs": refs["dependency"],
                    }
                ],
                "policies": [],
                "assumptions": [],
                "discarded_evidence": [],
                "relations": {},
            },
        },
    )

    admission = admit_source_candidates_by_materiality(
        decision,
        source,
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )

    path = admission["source"]["path"]
    boundary = admission["source"]["boundary"]
    assert [
        step["label"]
        for group in path["workflow_steps"]
        for step in group["steps"]
    ] == ["Accept claim", "Read ledger"]
    assert path["state_objects"][0]["transition"]["to_state"] == "claimed"
    assert boundary["external_systems"][0]["consumer"] == {
        "kind": "workflow_step", "step_index": 1,
    }
    assert admission["rejected_candidates"] == []


def test_source_assumptions_require_independent_materiality_authorization() -> None:
    source = {
        "boundary": {"assumptions": [{"materiality_field": "role"}]},
    }
    with pytest.raises(ValueError, match="lacks materiality authorization"):
        require_authorized_source_assumptions(
            source, canonical_parallel_materiality_decision(_decision())
        )
    assert authorized_source_assumption_fields(
        canonical_parallel_materiality_decision(_decision())
    ) == ()
    admitted = source_with_authorized_assumptions(
        source, canonical_parallel_materiality_decision(_decision())
    )
    assert admitted["boundary"]["assumptions"] == []

    decision = _decision()
    decision["fields"]["identity"] = {
        "status": "nonmaterial_assumption", "source_refs": [], "alternatives": [],
    }
    source["boundary"]["assumptions"][0]["materiality_field"] = "identity"
    require_authorized_source_assumptions(
        source, canonical_parallel_materiality_decision(decision)
    )


def test_parallel_materiality_cannot_smuggle_semantic_types_through_span_rows() -> None:
    expected = semantic_materiality_assessment()
    candidates = expected["source_candidates"]
    candidates["candidates"][0]["kind"] = "identity"

    with pytest.raises(ValueError, match="fields do not match"):
        assemble_parallel_materiality_assessment(
            _decision(),
            candidates,
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
        )


def test_parallel_materiality_requires_every_canonical_field_in_the_host_schema() -> None:
    expected = semantic_materiality_assessment()
    decision = _decision()
    decision["fields"].pop("component_boundary")

    with pytest.raises(ValueError, match="exact field coverage"):
        assemble_parallel_materiality_assessment(
            decision,
            expected["source_candidates"],
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
        )


def test_dependency_evidence_may_ground_an_explicit_host_authored_read_step() -> None:
    prompt = SEMANTIC_PROMPT + " Read the local ledger. Select one claim and show a receipt."
    read_ref = {
        "source_id": "operator_prompt", "quote": "Read the local ledger.",
        "occurrence": 1,
    }
    path_ref = {
        "source_id": "operator_prompt",
        "quote": "Select one claim and show a receipt.", "occurrence": 1,
    }
    decision = _decision()
    decision["fields"]["dependency"] = {
        "status": "explicit", "source_refs": [read_ref], "alternatives": [],
    }
    decision["fields"]["first_path"] = {
        "status": "explicit", "source_refs": [path_ref], "alternatives": [],
    }
    decision["fields"]["visible_result"] = {
        "status": "explicit", "source_refs": [path_ref], "alternatives": [],
    }
    source = combine_source_authoring_partitions(
        {
            "version": SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
            "path": {
                "identities": [{"label": "Claim review", "source_title": "Claim review", "source_refs": [path_ref]}],
                "actors": [],
                "workflow_steps": [
                    {"owner": {"kind": "system"}, "steps": [
                        _workflow_candidate([read_ref], "Read the local ledger"),
                        _workflow_candidate([path_ref], "Select one claim and show a receipt"),
                    ]}
                ],
                "state_objects": [],
                "visible_outputs": [{
                    "label": "receipt", "condition": None,
                    "producer": {"step_index": 1, "source_refs": [path_ref]},
                    "source_refs": [path_ref],
                }],
                "relations": {},
            },
        },
        {
            "version": SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
            "boundary": {
                "external_systems": [{
                    "label": "local ledger", "access_mode": "read",
                    "consumer": {
                        "kind": "workflow_step", "step_index": 0,
                        "source_refs": [read_ref],
                    },
                    "source_refs": [read_ref],
                }],
                "policies": [], "assumptions": [], "discarded_evidence": [],
                "relations": {},
            },
        },
    )

    admitted = admit_source_candidates_by_materiality(
        decision, source,
        evidence_sources={"operator_prompt": prompt, "operator_edit": ""},
    )

    assert admitted["rejected_candidates"] == []
    assert [
        step["label"]
        for group in admitted["source"]["path"]["workflow_steps"]
        for step in group["steps"]
    ] == ["Read the local ledger", "Select one claim and show a receipt"]


def test_parallel_materiality_owner_has_no_regex_or_token_semantic_authority() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "src/odylith/runtime/domain_intelligence/greenfield_semantic_parallel_materiality.py"
    )
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
