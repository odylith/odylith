from __future__ import annotations

import ast
from copy import deepcopy
import inspect
from pathlib import Path

import pytest

import odylith.runtime.domain_intelligence.greenfield_semantic_final_adjudication as final
import odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet as packet_owner
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_completion_partitions import (
    require_semantic_dependency_architecture,
    semantic_architecture_edge_object_ids,
    semantic_unassigned_source_dependency_ids,
)


def test_final_schema_makes_fact_admission_and_relations_explicit() -> None:
    source = _source()
    schema = final.semantic_final_adjudication_schema(
        source=source,
        source_citation_ids=tuple(_citations()),
        source_ref_schema={"type": "object"},
        edge_object_ids=semantic_architecture_edge_object_ids(source),
        topology_mode="single_system",
    )

    graph_branch = schema["properties"]["result"]
    properties = graph_branch["properties"]
    assert "admitted_fact_ids" in graph_branch["required"]
    assert "discarded_source_refs" in schema["required"]
    assert "uniqueItems" not in properties["admitted_fact_ids"]
    assert set(properties["admitted_fact_ids"]["items"]["enum"]) == {
        "identity.0", "actor.0", "step.0", "output.0", "constraint.0"
    }
    assert set(
        properties["admitted_relation_ids"]["items"]["enum"]
    ) == {
        "relation.owned_by.0",
        "relation.produces.0",
        "relation.constrained_by.0",
    }
    assert "evidence_status_misclassification" not in set(
        properties["findings"]["items"]["properties"]["challenge"]["enum"]
    )
    assert graph_branch["properties"]["source_status"]["enum"] == [
        "approved", "rejected"
    ]
    resolution = graph_branch["properties"]["materiality_resolution"]
    assert resolution["properties"]["verdict"]["enum"] == ["accept_hypothesis"]


def test_clarification_schema_omits_unsealable_graph_authorship() -> None:
    source = _source()
    schema = final.semantic_final_adjudication_schema(
        source=source,
        source_citation_ids=tuple(_citations()),
        source_ref_schema={"type": "object"},
        edge_object_ids=semantic_architecture_edge_object_ids(source),
        topology_mode="single_system",
        clarification_only=True,
    )

    assert set(schema["required"]) == {"version", "result"}
    assert set(schema["properties"]) == set(schema["required"])
    assert set(schema["properties"]["result"]["required"]) == {
        "materiality_resolution"
    }
    resolution = schema["properties"]["result"]["properties"][
        "materiality_resolution"
    ]
    assert resolution["properties"]["verdict"]["enum"] == ["accept_hypothesis"]


def test_source_ambiguity_becomes_the_exact_host_authored_question() -> None:
    decision = {
        "outcome": {
            "decision": "authorize_graph",
            "clarification": {
                "field": "",
                "question": "",
                "source_refs": [],
                "alternatives": [],
            },
        },
        "fields": {"first_path": {"status": "explicit"}},
    }
    refs = [
        {"source_id": "operator_prompt", "quote": "Select the existing slip first.", "occurrence": 1},
        {"source_id": "operator_prompt", "quote": "Import a new slip first.", "occurrence": 1},
    ]

    resolved = final.clarification_from_source_ambiguity(
        decision,
        ambiguity={
            "materiality_field": "first_path",
            "question": "Which slip operation should happen first?",
            "source_refs": refs,
        },
    )

    assert resolved["fields"] == decision["fields"]
    assert resolved["outcome"] == {
        "decision": "clarification_required",
        "clarification": {
            "field": "first_path",
            "question": "Which slip operation should happen first?",
            "source_refs": refs,
            "alternatives": [],
        },
    }
def test_final_adjudication_can_remove_unsupported_candidate_without_prose_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def completion(value: object, **kwargs: object) -> dict:
        captured.update(kwargs)
        return {"version": "typed-completion", "status": "complete"}

    monkeypatch.setattr(final, "apply_semantic_implementation_assignments", completion)
    result = final.apply_final_adjudication(
        _adjudication(), source=_source(), citation_registry=_citations()
    )

    assert [row["fact_id"] for row in result["source"]["facts"]] == [
        "identity.0", "actor.0", "step.0", "output.0"
    ]
    assert [
        (row["relation_id"], row["kind"], row["subject_id"], row["object_id"])
        for row in result["source"]["relations"]
    ] == [
        ("relation.owned_by.0", "owned_by", "step.0", "actor.0"),
        ("relation.produces.0", "produces", "step.0", "output.0"),
    ]
    edge_ids = captured["edge_object_ids"]
    assert "constraint.0" not in {item for values in edge_ids.values() for item in values}
    assert result["completion"]["clarification"] == {
        "question": "", "fields": [], "source_refs": []
    }


def test_source_unassigned_dependency_is_bound_only_by_implementation_architecture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source()
    source["facts"].append(
        {
            "fact_id": "dependency.0",
            "kind": "external_system",
            "label": "Local duty roster",
            "source_refs": [deepcopy(next(iter(_citations().values()))["source_ref"])],
        }
    )
    value = _adjudication()
    value["result"]["admitted_fact_ids"].append("dependency.0")

    assert semantic_unassigned_source_dependency_ids(source) == ("dependency.0",)
    monkeypatch.setattr(
        final,
        "apply_semantic_implementation_assignments",
        lambda value, **kwargs: {
            "internal_systems": [
                {"depends_on": [{"object_id": "dependency.0"}]}
            ]
        },
    )

    result = final.apply_final_adjudication(
        value, source=source, citation_registry=_citations()
    )

    assert not any(
        row["kind"] == "depends_on" for row in result["source"]["relations"]
    )
    require_semantic_dependency_architecture(
        result["completion"], dependency_ids=("dependency.0",)
    )


def test_source_unassigned_dependency_fails_when_architecture_does_not_bind_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source()
    source["facts"].append(
        {
            "fact_id": "dependency.0",
            "kind": "external_system",
            "label": "Local duty roster",
            "source_refs": [deepcopy(next(iter(_citations().values()))["source_ref"])],
        }
    )
    value = _adjudication()
    value["result"]["admitted_fact_ids"].append("dependency.0")
    monkeypatch.setattr(
        final,
        "apply_semantic_implementation_assignments",
        lambda value, **kwargs: {"internal_systems": [{"depends_on": []}]},
    )

    with pytest.raises(ValueError, match="leaves a source dependency unassigned"):
        final.apply_final_adjudication(
            value, source=source, citation_registry=_citations()
        )


def test_final_materiality_accepts_without_field_recomposition() -> None:
    hypothesis = {
        "version": "odylith.greenfield.parallel-materiality-decision.v3",
        "outcome": {
            "decision": "authorize_graph",
            "clarification": {
                "field": "",
                "question": "",
                "source_refs": [],
                "alternatives": [],
            },
        },
        "fields": {"identity": {"status": "explicit"}},
    }

    assert final.resolve_final_materiality_decision(
        {"verdict": "accept_hypothesis"}, hypothesis=hypothesis
    ) == hypothesis
    with pytest.raises(ValueError, match="resolution is malformed"):
        final.resolve_final_materiality_decision(
            {
                "verdict": "clarification_required",
                "clarification": {
                    "field": "role",
                    "question": "Who owns the action?",
                    "source_refs": [],
                    "alternatives": [],
                },
            },
            hypothesis=hypothesis,
        )


def test_final_graph_stage_cannot_replace_prompt_only_materiality_authority() -> None:
    source_ref = {
        "source_id": "operator_prompt",
        "quote": "Never issue production commands.",
        "occurrence": 1,
    }
    fields = {
        name: {
            "status": "nonmaterial_assumption",
            "source_refs": [],
            "alternatives": [],
        }
        for name in SEMANTIC_CLARIFICATION_FIELDS
    }
    fields["non_goal"] = {
        "status": "explicit",
        "source_refs": [source_ref],
        "alternatives": [],
    }
    decision = {
        "version": "odylith.greenfield.parallel-materiality-decision.v3",
        "outcome": {
            "decision": "authorize_graph",
            "clarification": {
                "field": "",
                "question": "",
                "source_refs": [],
                "alternatives": [],
            },
        },
        "fields": fields,
    }

    with pytest.raises(ValueError, match="resolution is malformed"):
        final.resolve_final_materiality_decision(
            {"verdict": "replace_hypothesis", "decision": decision},
            hypothesis={"provisional": True},
        )


def test_final_discard_selection_removes_only_exact_nonproduct_custody() -> None:
    kept = {
        "source_id": "operator_prompt",
        "quote": "Build a queue view.",
        "occurrence": 1,
    }
    discarded = {
        "source_id": "operator_prompt",
        "quote": "Drop the placeholder phrase Golden Hinge.",
        "occurrence": 1,
    }
    decision = {
        "version": "odylith.greenfield.parallel-materiality-decision.v3",
        "outcome": {
            "decision": "authorize_graph",
            "clarification": {
                "field": "",
                "question": "",
                "source_refs": [],
                "alternatives": [],
            },
        },
        "fields": {
            "identity": {
                "status": "explicit",
                "source_refs": [kept, discarded],
                "alternatives": [],
            }
        },
    }

    filtered = final.remove_discarded_materiality_refs(
        decision, discarded_source_refs=[discarded]
    )

    assert filtered["fields"]["identity"]["source_refs"] == [kept]


def test_independent_source_authors_can_downgrade_discarded_optional_axis() -> None:
    prompt = "Route one note. Ignore the retired sketch name Linen Meteor."
    discarded = {
        "source_id": "operator_prompt",
        "quote": "Ignore the retired sketch name Linen Meteor.",
        "occurrence": 1,
    }
    decision = {
        "version": "odylith.greenfield.parallel-materiality-decision.v3",
        "outcome": {
            "decision": "authorize_graph",
            "clarification": {
                "field": "",
                "question": "",
                "source_refs": [],
                "alternatives": [],
            },
        },
        "fields": {
            "non_goal": {
                "status": "explicit",
                "source_refs": [discarded],
                "alternatives": [],
            }
        },
    }

    settled = final.settle_independently_confirmed_discarded_materiality_refs(
        decision,
        discarded_source_refs=[discarded],
        evidence_sources={"operator_prompt": prompt, "operator_edit": ""},
    )

    assert settled["fields"]["non_goal"] == {
        "status": "nonmaterial_assumption",
        "source_refs": [],
        "alternatives": [],
    }

    protected = deepcopy(decision)
    protected["fields"] = {"role": protected["fields"]["non_goal"]}
    with pytest.raises(ValueError, match="only materiality custody"):
        final.settle_independently_confirmed_discarded_materiality_refs(
            protected,
            discarded_source_refs=[discarded],
            evidence_sources={"operator_prompt": prompt, "operator_edit": ""},
        )


def test_final_graph_stage_cannot_reopen_settled_materiality() -> None:
    value = {
        "version": final.SEMANTIC_FINAL_ADJUDICATION_VERSION,
        "discarded_source_refs": [],
        "result": {
            "materiality_resolution": {"verdict": "clarification_required"},
            "source_status": "not_applicable",
            "findings": [],
            "admitted_fact_ids": [],
            "admitted_relation_ids": [],
            "completion": None,
        },
    }

    with pytest.raises(ValueError, match="cannot reopen settled materiality"):
        final.apply_final_adjudication(
            value,
            source=_source(),
            citation_registry=_citations(),
            clarification_only=False,
        )


def test_final_adjudication_fails_closed_on_fact_or_relation_custody_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        final,
        "apply_semantic_implementation_assignments",
        lambda value, **kwargs: {"version": "typed-completion", "status": "complete"},
    )
    duplicated = _adjudication()
    duplicated["result"]["admitted_fact_ids"].append("identity.0")
    with pytest.raises(ValueError, match="duplicated or unknown"):
        final.apply_final_adjudication(
            duplicated, source=_source(), citation_registry=_citations()
        )

    omitted_endpoint = _adjudication()
    omitted_endpoint["result"]["admitted_relation_ids"].append(
        "relation.constrained_by.0"
    )
    with pytest.raises(ValueError, match="omitted fact"):
        final.apply_final_adjudication(
            omitted_endpoint, source=_source(), citation_registry=_citations()
        )

    unknown_relation = _adjudication()
    unknown_relation["result"]["admitted_relation_ids"][0] = "relation.owned_by.missing"
    with pytest.raises(ValueError, match="duplicated or unknown"):
        final.apply_final_adjudication(
            unknown_relation, source=_source(), citation_registry=_citations()
        )


def test_final_adjudication_owner_has_no_regex_fuzzy_or_token_authority() -> None:
    for path in (
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_final_adjudication.py"),
        Path("scripts/release/greenfield_semantic_final_graph_author.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imports.isdisjoint(
            {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
        )


def test_sealed_authority_carries_only_accepted_evidence_text() -> None:
    accepted = {
        "source_id": "operator_prompt",
        "quote": "A reviewer publishes a receipt.",
        "occurrence": 1,
    }
    verified = packet_owner.VerifiedSemanticIntentPacket(
        semantic_intent={"facts": [{"source_refs": [deepcopy(accepted)]}]},
        product_facts={},
        resolved_source_refs=(),
        materiality_assessment={
            "source_candidates": {
                "candidates": [{"source_ref": deepcopy(accepted)}]
            }
        },
        materiality_assessment_sha256="0" * 64,
        source_candidate_adjudication={},
        source_claims={},
        critic_run={},
        author_run={},
        evidence_sha256="0" * 64,
        semantic_intent_sha256="0" * 64,
        semantic_meaning_sha256="0" * 64,
    )
    evidence = packet_owner.accepted_semantic_evidence_sources(
        verified,
        source_evidence={
            "operator_prompt": (
                "A reviewer publishes a receipt. "
                "The obsolete scratch label must not enter governed truth."
            ),
            "operator_edit": "",
        },
    )

    assert evidence == {
        "operator_prompt": "A reviewer publishes a receipt.",
        "operator_edit": "",
    }
    assert "obsolete scratch label" not in str(evidence)
    authority_source = inspect.getsource(packet_owner.semantic_intent_authority)
    assert "verified.resolved_source_refs" not in authority_source
    assert "resolved_semantic_source_refs(" in authority_source


def _source() -> dict:
    ref = {"source_id": "operator_prompt", "quote": "A reviewer publishes a receipt.", "occurrence": 1}
    return {
        "version": "odylith.greenfield.semantic-source-authoring-graph.v19",
        "facts": [
            {"fact_id": "identity.0", "kind": "identity", "label": "receipt board", "source_refs": [deepcopy(ref)]},
            {"fact_id": "actor.0", "kind": "actor", "label": "reviewer", "source_refs": [deepcopy(ref)]},
            {"fact_id": "step.0", "kind": "workflow_step", "label": "publish a receipt", "action": "publish a receipt", "action_phrase": "A reviewer publishes a receipt.", "owner_kind": "actor", "source_refs": [deepcopy(ref)]},
            {"fact_id": "output.0", "kind": "visible_output", "label": "receipt", "source_refs": [deepcopy(ref)]},
            {"fact_id": "constraint.0", "kind": "operational_constraint", "label": "invented restriction", "source_refs": [deepcopy(ref)]},
        ],
        "relations": [
            {
                "kind": "owned_by",
                "subject_id": "step.0",
                "object_id": "actor.0",
                "source_refs": [deepcopy(ref)],
            },
            {
                "kind": "produces",
                "subject_id": "step.0",
                "object_id": "output.0",
                "source_refs": [deepcopy(ref)],
            },
            {
                "kind": "constrained_by",
                "subject_id": "identity.0",
                "object_id": "constraint.0",
                "source_refs": [deepcopy(ref)],
            },
        ],
    }


def _citations() -> dict[str, dict]:
    ref = {"source_id": "operator_prompt", "quote": "A reviewer publishes a receipt.", "occurrence": 1}
    return {
        "citation.path": {"fact_ids": ("step.0", "actor.0", "output.0"), "source_ref": deepcopy(ref)},
        "citation.constraint": {"fact_ids": ("constraint.0",), "source_ref": deepcopy(ref)},
    }


def _adjudication() -> dict:
    return {
        "version": final.SEMANTIC_FINAL_ADJUDICATION_VERSION,
        "discarded_source_refs": [],
        "result": {
            "materiality_resolution": {"verdict": "accept_hypothesis"},
            "source_status": "approved",
            "findings": [],
            "admitted_fact_ids": ["identity.0", "actor.0", "step.0", "output.0"],
            "admitted_relation_ids": [
                "relation.owned_by.0",
                "relation.produces.0",
            ],
            "completion": {},
        },
    }
