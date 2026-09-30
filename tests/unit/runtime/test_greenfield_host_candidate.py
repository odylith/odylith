"""One-pass host-candidate authority contracts."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
    admit_greenfield_host_candidate,
    greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
    canonical_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    prepare_model_authoring_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    clarification_response,
    host_candidate_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _candidate() -> tuple[str, dict[str, object]]:
    source = _source()
    return source, host_candidate_response(_response(source), evidence_text=source)


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def test_contract_requires_one_complete_host_candidate() -> None:
    source, _ = _candidate()
    contract = greenfield_host_candidate_contract(source)
    authored = contract["candidate_schema"]["properties"]["result"]["anyOf"][0]

    assert contract["version"] == HOST_CANDIDATE_CONTRACT_VERSION
    assert contract["candidate_version"] == HOST_CANDIDATE_FORMAT_VERSION
    assert {"components", "source_precedence"} <= set(authored["required"])
    assert "review" not in contract["task"].casefold()


def test_admission_validates_once_and_seals_raw_and_canonical_hashes() -> None:
    source, candidate = _candidate()
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=source)

    authored, receipt = admit_greenfield_host_candidate(
        candidate,
        evidence_text=source,
    )

    assert receipt == {
        "version": HOST_CANDIDATE_RECEIPT_VERSION,
        "contract_version": HOST_CANDIDATE_CONTRACT_VERSION,
        "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "raw_candidate_sha256": _sha256(candidate),
        "canonical_candidate_sha256": _sha256(canonical),
    }
    assert authored.semantic_model_call_count == 0
    assert [row["order"] for row in authored.first_path_relations] == [1, 2, 3]
    assert authored.source_precedence == ()
    assert authored.component_responsibility_relations


def test_passive_timing_does_not_invent_a_precedence_edge() -> None:
    source, candidate = _candidate()
    candidate["result"]["source_precedence"] = []

    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source)

    assert authored.source_precedence == ()


def test_candidate_tampering_fails_closed() -> None:
    source, candidate = _candidate()
    candidate["result"]["events"][0]["source_citation"]["quote"] = "not in source"

    with pytest.raises((GreenfieldModelAuthoringError, ValueError)):
        admit_greenfield_host_candidate(candidate, evidence_text=source)


def test_material_ambiguity_asks_once_and_writes_nothing(tmp_path) -> None:
    source = "Build a useful product, but the first task and visible result are unspecified."
    response = clarification_response(
        question="Which task and result should the product prove first?",
        material_dimension="first_path",
        evidence_quotes=(),
        consistency_status="material_ambiguity",
    )
    candidate = host_candidate_response(response, evidence_text=source)

    with pytest.raises(GreenfieldClarificationRequired) as raised:
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=candidate,
        )

    assert raised.value.required_fields == ("first_path",)
    assert not (tmp_path / ".odylith").exists()
    assert not (tmp_path / "odylith").exists()


def test_partial_component_constraint_overlap_is_rejected() -> None:
    source, candidate = _candidate()
    constraint = candidate["result"]["facts"]["operational_constraints"][0]
    quote = constraint["quote"]
    if len(quote) < 2:
        pytest.skip("fixture constraint is too short for a partial-overlap control")
    candidate["result"]["components"][0]["responsibilities"][0] = {
        "quote": quote[:-1],
        "occurrence": 1,
    }

    with pytest.raises(GreenfieldModelAuthoringError, match="overlap only"):
        admit_greenfield_host_candidate(candidate, evidence_text=source)


def test_exact_component_constraint_dual_role_is_retained() -> None:
    source, candidate = _candidate()
    constraint = candidate["result"]["facts"]["operational_constraints"][0]
    candidate["result"]["components"][0]["responsibilities"][0] = {
        "quote": constraint["quote"],
        "occurrence": 1,
    }

    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source)

    exact = [
        row
        for row in authored.component_responsibility_relations
        if row["responsibility_quote"] == constraint["quote"]
    ]
    assert len(exact) == 1
    assert exact[0]["owner_system_quote"] == "Berth map"


def test_multisource_receipt_preserves_exact_combined_evidence_and_citations(
    tmp_path,
) -> None:
    prompt = _source()
    edit_evidence = "Keep the accepted Harbor Desk scope; record this correction as evidence."
    prepared = prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
    )
    candidate = host_candidate_response(
        _response(prepared.evidence_source),
        evidence_text=prepared.evidence_source,
    )
    authored, receipt = admit_greenfield_host_candidate(
        candidate,
        evidence_text=prepared.evidence_source,
    )

    materialized = materialize_host_authored_intent(
        prompt=prompt,
        edit_evidence=edit_evidence,
        repo_root=tmp_path,
        host_candidate=candidate,
        prepared_evidence=prepared,
    )

    authority = materialized[PRODUCT_INTENT_AUTHORITY_KEY]
    assert prepared.source_document_count == 2
    assert authority["operating_envelope"]["evidence_contract"]["observed"][
        "documents"
    ] == 2
    assert receipt["source_sha256"] == hashlib.sha256(
        prepared.evidence_source.encode("utf-8")
    ).hexdigest()
    assert authority["markdown_source_sha256"] == receipt["source_sha256"]
    evidence_bytes = prepared.evidence_source.encode("utf-8")
    for span in authored.source_spans:
        exact = evidence_bytes[
            span["source_start_byte"] : span["source_end_byte"]
        ].decode("utf-8")
        assert exact == span["text"]


def test_canonical_candidate_hash_changes_on_semantic_tamper() -> None:
    source, candidate = _candidate()
    _, receipt = admit_greenfield_host_candidate(candidate, evidence_text=source)
    tampered = copy.deepcopy(candidate)
    tampered["result"]["ambiguities"] = ["A new unsealed ambiguity"]

    _, tampered_receipt = admit_greenfield_host_candidate(
        tampered,
        evidence_text=source,
    )

    assert tampered_receipt["canonical_candidate_sha256"] != receipt[
        "canonical_candidate_sha256"
    ]
