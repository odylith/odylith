from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    PARALLEL_MATERIALITY_DECISION_VERSION,
    admit_source_candidates_by_materiality,
    assemble_parallel_materiality_assessment,
    authorized_source_assumption_fields,
    canonical_parallel_materiality_decision,
    materiality_authorization_view,
    parallel_materiality_decision_schema,
    require_authorized_source_assumptions,
    require_materiality_source_coverage,
    source_with_authorized_assumptions,
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


def test_dependency_evidence_cannot_be_duplicated_as_a_first_path_step() -> None:
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

    with pytest.raises(ValueError, match="outside critic-settled `first_path`"):
        require_materiality_source_coverage(
            decision,
            source,
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
        )


def test_admission_removes_cross_kind_candidates_and_rebinds_typed_edges() -> None:
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
                "state_objects": [],
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
    ] == ["Accept claim"]
    assert boundary["external_systems"][0]["consumer"] is None
    assert {(row["kind"], row["reason"]) for row in admission["rejected_candidates"]} == {
        ("workflow_step", "outside_settled_evidence"),
        ("depends_on", "rejected_subject"),
    }


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
