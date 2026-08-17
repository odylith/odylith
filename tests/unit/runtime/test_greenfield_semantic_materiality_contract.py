from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_VERSION,
    product_intent_authority_snapshot_hash,
    require_product_intent_authority_structure,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    SEMANTIC_INTENT_PACKET_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_request import (
    semantic_intent_authoring_request,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_MATERIALITY_ASSESSMENT_VERSION,
    SEMANTIC_NONMATERIAL_ASSUMPTION_FIELDS,
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
    semantic_materiality_assessment_schema,
    semantic_materiality_assessment_sha256,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    PATH_EVIDENCE,
    SEMANTIC_PROMPT,
    semantic_clarification_packet,
    semantic_intent_packet,
    semantic_ref,
    stateless_semantic_intent_packet,
)


def _rehash_assessment(packet: dict[str, object]) -> None:
    assessment = packet["materiality_assessment"]
    assert isinstance(assessment, dict)
    packet["materiality_assessment_sha256"] = semantic_materiality_assessment_sha256(
        assessment
    )


def test_prompt_only_gate_accepts_complete_and_actorless_stateless_graphs() -> None:
    stateless_packet, stateless_prompt = stateless_semantic_intent_packet()
    complete = require_semantic_intent_packet(
        semantic_intent_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    support = require_semantic_intent_packet(
        stateless_packet,
        prompt=stateless_prompt,
    )

    assert complete.materiality_assessment["decision"] == "authorize_graph"
    assert complete.product_facts is not None
    assert support.product_facts is not None
    assert support.product_facts["human_actors"] == []
    assert support.product_facts["state_objects"] == []


def test_prompt_only_gate_accepts_one_aligned_clarification_but_cannot_seal_it() -> None:
    verified = require_semantic_intent_packet(
        semantic_clarification_packet(),
        prompt=SEMANTIC_PROMPT,
    )

    assert verified.product_facts is None
    assert verified.semantic_intent["clarification"]["fields"] == ["visible_result"]
    with pytest.raises(ValueError, match="clarification-bound"):
        semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_coverage", "exact canonical field coverage"),
        ("critic_downgrade", "capability profile was downgraded"),
        ("author_downgrade", "capability profile was downgraded"),
        ("same_run", "runs are not distinct"),
        ("wrong_packet_evidence", "does not match the supplied evidence"),
        ("wrong_packet_contract", "different authoring contract"),
        ("wrong_assessment_evidence", "does not match source evidence"),
        ("wrong_assessment_contract", "does not match the authoring contract"),
        ("post_candidate", "not prompt-only and pre-graph"),
        ("candidate_aware", "invalid structure"),
        ("resolved_alternatives", "resolved materiality field carries alternatives"),
        ("required_field_assumed_nonmaterial", "cannot be assumed nonmaterial: role"),
        ("decision_mismatch", "materiality clarification does not match"),
    ],
)
def test_prompt_only_gate_rejects_tamper_and_mechanism_drift(
    mutation: str,
    message: str,
) -> None:
    packet = copy.deepcopy(semantic_intent_packet())
    assessment = packet["materiality_assessment"]
    assert isinstance(assessment, dict)
    if mutation == "missing_coverage":
        assessment["fields"].pop()
        _rehash_assessment(packet)
    elif mutation == "critic_downgrade":
        packet["critic_run"]["capability_profile"] = "balanced_semantic_reasoning"
    elif mutation == "author_downgrade":
        packet["author_run"]["capability_profile"] = "balanced_semantic_reasoning"
    elif mutation == "same_run":
        packet["author_run"]["author_run_id"] = packet["critic_run"]["critic_run_id"]
    elif mutation == "wrong_packet_evidence":
        packet["evidence_sha256"] = "0" * 64
    elif mutation == "wrong_packet_contract":
        packet["authoring_contract_sha256"] = "0" * 64
    elif mutation == "wrong_assessment_evidence":
        assessment["evidence_sha256"] = "0" * 64
        _rehash_assessment(packet)
    elif mutation == "wrong_assessment_contract":
        assessment["authoring_contract_sha256"] = "0" * 64
        _rehash_assessment(packet)
    elif mutation == "post_candidate":
        assessment["assessment_basis"] = "post_candidate"
        _rehash_assessment(packet)
    elif mutation == "candidate_aware":
        assessment["candidate_sha256"] = "0" * 64
        _rehash_assessment(packet)
    elif mutation == "resolved_alternatives":
        assessment["fields"][0]["alternatives"] = ["one", "two"]
        _rehash_assessment(packet)
    elif mutation == "required_field_assumed_nonmaterial":
        assessment["fields"][1]["status"] = "nonmaterial_assumption"
        assessment["fields"][1]["source_refs"] = []
        _rehash_assessment(packet)
    else:
        assessment["decision"] = "clarification_required"
        assessment["clarification"] = {
            "field": "visible_result",
            "question": "Which visible result is required?",
            "source_refs": [semantic_ref(PATH_EVIDENCE)],
            "alternatives": ["receipt", "audit view"],
        }
        assessment["fields"] = [
            row for row in assessment["fields"] if row["field"] != "visible_result"
        ]
        _rehash_assessment(packet)

    with pytest.raises(ValueError, match=message):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_materiality_clarification_requires_two_alternatives_only() -> None:
    packet = semantic_clarification_packet()
    assessment = packet["materiality_assessment"]
    assert isinstance(assessment, dict)
    assessment["clarification"]["alternatives"] = ["claim receipt"]
    _rehash_assessment(packet)

    with pytest.raises(ValueError, match="citation, and two alternatives"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_provider_schema_encodes_materiality_status_invariants() -> None:
    schema = semantic_materiality_assessment_schema()
    clarification = schema["properties"]["clarification"]["anyOf"]
    variants = schema["properties"]["fields"]["items"]["anyOf"]

    assert clarification[0]["properties"] == {
        "field": {"type": "string", "enum": [""]},
        "question": {"type": "string", "enum": [""]},
        "source_refs": {"type": "array", "minItems": 0, "maxItems": 0},
        "alternatives": {"type": "array", "minItems": 0, "maxItems": 0},
    }
    assert clarification[1]["properties"]["question"]["minLength"] == 1
    assert clarification[1]["properties"]["source_refs"]["minItems"] == 1
    assert clarification[1]["properties"]["alternatives"]["minItems"] == 2
    assert schema["properties"]["fields"]["minItems"] == 8
    assert schema["properties"]["fields"]["maxItems"] == 9
    assert variants[0]["properties"]["status"]["enum"] == [
        "explicit",
        "source_entailable",
    ]
    assert variants[0]["properties"]["source_refs"]["minItems"] == 1
    assert variants[0]["properties"]["alternatives"]["maxItems"] == 0
    assert variants[1]["properties"]["status"]["enum"] == [
        "nonmaterial_assumption"
    ]
    assert variants[1]["properties"]["field"]["enum"] == list(
        SEMANTIC_NONMATERIAL_ASSUMPTION_FIELDS
    )
    assert variants[1]["properties"]["source_refs"]["maxItems"] == 0
    assert variants[1]["properties"]["alternatives"]["maxItems"] == 0
    assert len(variants) == 2


def test_authority_seals_assessment_hash_and_distinct_run_evidence() -> None:
    verified = require_semantic_intent_packet(
        semantic_intent_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    authority = semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT)

    assert authority["version"] == PRODUCT_INTENT_AUTHORITY_VERSION
    assert authority["semantic_materiality_assessment"] == verified.materiality_assessment
    assert authority["semantic_materiality_critic_run"]["critic_run_id"] != (
        authority["semantic_intent_author_run"]["author_run_id"]
    )
    tampered = copy.deepcopy(authority)
    tampered["semantic_intent_author_run"]["author_run_id"] = (
        tampered["semantic_materiality_critic_run"]["critic_run_id"]
    )
    tampered["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(
        tampered
    )
    with pytest.raises(ValueError, match="runs are not distinct"):
        require_product_intent_authority_structure(tampered)


def test_v5_request_requires_prompt_only_schema_constrained_independent_runs() -> None:
    request = semantic_intent_authoring_request(prompt=SEMANTIC_PROMPT)
    protocol = request["authoring_protocol"]

    assert SEMANTIC_INTENT_IR_VERSION.endswith(".v2")
    assert SEMANTIC_INTENT_PACKET_VERSION.endswith(".v3")
    assert SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION.endswith(".v5")
    assert SEMANTIC_MATERIALITY_ASSESSMENT_VERSION.endswith(".v3")
    assert request["materiality_gate"]["order"] == "before_graph_authoring"
    assert request["materiality_gate"]["candidate_access"] == "forbidden"
    assert request["materiality_gate"]["structured_output"] == (
        "exact_schema_constrained_when_available"
    )
    assert request["materiality_gate"]["schema_failure_action"] == (
        "block_or_start_fresh_independent_author_run"
    )
    assert request["packet_structured_output"] == "exact_schema_constrained_when_available"
    assert protocol["structured_output_contract"]["forbidden_action"] == (
        "validation_error_driven_field_repair"
    )
    assert protocol["mechanism_status"] == "provisional"
    assert protocol["replacement_discipline"]["status"] == "evidence_led"
    assert "explicitly names" in protocol["component_boundary_custody"]["source_fact"]
    assert "specific and differentiated" in protocol["component_boundary_custody"][
        "bounded_interpretation"
    ]
    assert protocol["component_boundary_custody"]["runtime_detection"] == "forbidden"
    assert protocol["semantic_kind_disambiguation"]["decision_basis"] == (
        "relationship_to_accepted_behavior_not_tokens_or_grammar"
    )
    assert protocol["semantic_kind_disambiguation"]["challenge"] == (
        "semantic_kind_conflation"
    )
    assert protocol["semantic_kind_disambiguation"]["runtime_detection"] == "forbidden"
    assert "consumer can observe" in protocol["materiality_field_semantics"]["visible_result"]
    assert "human-facing interaction" in protocol["materiality_field_semantics"]["role"]
    assert any(
        "internal transition" in rule
        for rule in protocol["materiality_decision_rules"]
    )
    assert any(
        "other eight settled canonical fields" in rule
        for rule in protocol["materiality_decision_rules"]
    )
    assert request["packet_header"]["authoring_contract_sha256"] == (
        semantic_intent_authoring_contract_sha256()
    )
    assert request["packet_schema"]["properties"]["critic_run"]["properties"][
        "capability_profile"
    ]["enum"] == [SEMANTIC_REASONING_CAPABILITY_PROFILE]


def test_materiality_gate_has_no_prose_matching_or_parser_dependency() -> None:
    root = Path(__file__).resolve().parents[3]
    prohibited = {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    modules = (
        "greenfield_semantic_source_citations.py",
        "greenfield_semantic_materiality_contract.py",
        "greenfield_semantic_authoring_contract.py",
        "greenfield_semantic_intent_request.py",
        "greenfield_semantic_intent_packet.py",
        "greenfield_sealed_product_intent_authority.py",
    )
    violations: dict[str, list[str]] = {}
    for name in modules:
        path = root / "src/odylith/runtime/domain_intelligence" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            str(node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        if found := sorted(prohibited & imports):
            violations[name] = found

    assert violations == {}

    intent_contract = (
        root
        / "src/odylith/runtime/domain_intelligence/greenfield_semantic_intent_contract.py"
    ).read_text(encoding="utf-8")
    assert "def _validate_source_refs" not in intent_contract
    assert "def _resolve_source_ref" not in intent_contract
    assert "def _nth_occurrence" not in intent_contract
