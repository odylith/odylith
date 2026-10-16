"""Passive proof-assumption custody and strict current source-proof authority."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldModelAuthoredIntent,
    validate_greenfield_authoring_response,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
    product_intent_authority_from_envelope,
    require_product_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import (
    project_greenfield_source_lifecycle,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    project_greenfield_source_event_catalog,
    validate_greenfield_source_duty_binding,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_VERSION,
    PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
    PRODUCT_INTENT_LEDGER_VERSION,
    product_intent_authority_snapshot_hash,
    product_intent_material_custody_hash,
    require_sealed_product_intent_authority_bytes,
)
from tests.unit.runtime.test_greenfield_product_intent_envelope import (
    _INTENT,
    _RELATIONS,
    _authored_inputs,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    _unique_context_citation,
    authored_response,
    structural_design_fixture,
    synthetic_source_duty_receipt_for_ledger,
)


_PROVISIONAL_PROOF = {
    "applies_to": "proof_boundary",
    "statement": "Use a reviewable readiness record as the proposed proof checkpoint.",
}
_NON_PROOF_SOURCE = "Background context has no proof checkpoint"


def _model_authoring() -> dict[str, Any]:
    return {
        "origin": "host_native",
        "host_candidate": {
            "version": HOST_CANDIDATE_RECEIPT_VERSION,
            "contract_version": HOST_CANDIDATE_CONTRACT_VERSION,
            "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "source_sha256": "a" * 64,
            "raw_candidate_sha256": "b" * 64,
            "canonical_candidate_sha256": "c" * 64,
            "source_duty_ledger_sha256": "d" * 64,
            "source_duty_verifier_task_sha256": "c" * 64,
            "source_duty_decision_set_sha256": "f" * 64,
            "source_duty_binding_sha256": "e" * 64,
        },
        "runtime_semantic_model_call_count": 0,
    }


def _passive_provisional_inputs() -> tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Construct synthetic ledger8/design6 compatibility custody, never fresh proof.

    These are declared historical contract versions, not retained model output.
    Source bytes are final before every citation, verifier fixture and seal.
    """
    intent = copy.deepcopy(_INTENT)
    intent.update(
        proof_boundary="", assumptions=[copy.deepcopy(_PROVISIONAL_PROOF)],
        component_responsibilities=[],
    )
    relations = [{**row, "visible_result_quote": ""} for row in _RELATIONS]
    source = ". ".join(
        str(row)
        for field, value in intent.items()
        if field not in {"assumptions", "ambiguities"}
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + ". " + _NON_PROOF_SOURCE + "."

    def cite(quote: str) -> dict[str, str]:
        return _unique_context_citation(source, {"quote": quote, "occurrence": 1})

    ledger = {
        "version": "odylith.greenfield.source-duty-ledger.v8",
        "status": "inventory", "question": "", "evidence_controls": [],
        "product_identity": {"basis": "explicit_name", "source_ref": cite(intent["title"])},
        "first_path_actions": [
            {
                "id": f"A{order}", "source_refs": [],
                "performer_role": "human_actor" if row["actor_kind"] == "human" else "internal_system",
                "statement": row["event_quote"], "event_ref": cite(row["event_quote"]),
                "actor_ref": cite(row["actor_fact_quote"]),
                "role_refs": [cite(row["actor_fact_quote"]), cite(row["event_quote"])],
                "action": row["action_verb_quote"], "target": row["target_quote"],
                "observable_result": "The declared source action is observable.",
            }
            for order, row in enumerate(relations, start=1)
        ],
        **{field: [] for field in (
            "supporting_human_actions", "system_duties", "state_fields",
            "off_path_transitions", "conditional_guards", "boundaries", "proof_duties",
        )},
    }
    ledger_receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    catalog = project_greenfield_source_event_catalog(ledger_receipt, evidence_text=source, _passive=True)
    binding = {
        "version": "odylith.greenfield.source-duty-binding.v3",
        "source_sha256": ledger_receipt["source_sha256"],
        "ledger_sha256": ledger_receipt["ledger_sha256"],
        **catalog["action_bindings"],
        **{field: [] for field in ("off_path_transitions", "conditional_guards", "boundaries", "proof_duties")},
    }
    response = authored_response(
        intent, evidence_text=source, first_path_relations=_RELATIONS,
        provisional_design=structural_design_fixture(
            (1, 2, 3), version="odylith.greenfield.provisional-design.v6",
        ),
    )
    response["result"]["terminal"] = None
    response["result"]["components"] = []
    binding_candidate = {
        **response["result"],
        "facts": {
            field: [cite(ref["quote"]) for ref in response["result"]["facts"][field]]
            for field in ("human_actors", "internal_systems", "external_systems")
        },
        "events": [{"actor_fact": row["actor_fact"]} for row in response["result"]["events"]],
    }
    binding = validate_greenfield_source_duty_binding(
        binding, ledger_receipt=ledger_receipt, candidate_result=binding_candidate, evidence_text=source,
    )
    authored = validate_greenfield_authoring_response(
        response, evidence_text=source, elapsed_seconds=1.0,
        provider={"provider": "synthetic_passive_fixture"}, profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=10.0, semantic_model_call_count=0,
        allow_zero_semantic_calls=True, first_path_event_orders=(1, 2, 3),
        accepted_source_duties=ledger_receipt, accepted_source_duty_binding=binding,
    )
    assert isinstance(authored, GreenfieldModelAuthoredIntent)
    source_duty = {
        "ledger_receipt": ledger_receipt,
        "binding": binding,
        "lifecycle": project_greenfield_source_lifecycle(
            ledger_receipt=ledger_receipt,
            binding=binding,
            candidate_result=binding_candidate,
            evidence_text=source,
        ),
    }
    provisional = {**authored.intent, AUTHORED_SEMANTICS_KEY: authored_semantics_mapping(
        authored.source_event_relations,
        authored.component_responsibility_relations,
        first_path_context_relations=authored.first_path_context_relations,
        provisional_design=authored.provisional_design,
        source_duty=source_duty,
    )}
    assert ledger_receipt["version"] == "odylith.greenfield.source-duty-ledger-receipt.v14"
    assert provisional[AUTHORED_SEMANTICS_KEY]["version"] == "odylith.greenfield.authored-semantics.v19"
    assert authored.provisional_design["version"] == "odylith.greenfield.provisional-design.v6"
    return source, provisional, list(authored.source_spans), list(authored.atomic_claims)


def _build_provisional_envelope() -> dict[str, Any]:
    source, intent, spans, claims = _passive_provisional_inputs()
    return build_product_intent_envelope(
        intent,
        source_text=source,
        source_path="evidence.txt",
        source_format="in_memory_confirmed_intent",
        canonical_candidate_sha256="a" * 64,
        authored_source_spans=spans,
        authored_atomic_claims=claims,
        authored_source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
    )


def _authority(envelope: dict[str, Any]) -> dict[str, Any]:
    return product_intent_authority_from_envelope(
        envelope,
        structured_intent_path="candidate-intent.json",
        markdown_source_path="evidence.txt",
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _rebind_authority_hashes(authority: dict[str, Any]) -> None:
    authority["material_custody_sha256"] = product_intent_material_custody_hash(
        authority["material_fields"]
    )
    authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(
        authority
    )


def test_passive_provisional_proof_is_sealed_as_assumption_without_source_authority() -> None:
    """Synthetic source8/design6 retains proof-assumption authority, not fresh admission."""
    envelope = _build_provisional_envelope()

    assert envelope["schema_version"] == PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION
    assert envelope["custody_ledger"]["version"] == PRODUCT_INTENT_LEDGER_VERSION
    assert "proof_boundary" not in envelope["product_facts"]
    assert envelope["product_facts"]["assumptions"] == [_PROVISIONAL_PROOF]
    assert envelope["materiality_gate"] == {
        "status": "passed",
        "blocked_fields": [],
        "clarification_policy": "block_only_material_unknowns",
    }
    custody = envelope["custody_ledger"]["fields"]["proof_boundary"]
    assert custody == {
        "custody_state": "assumption",
        "derivation": "sealed_provisional_assumption",
        "confidence": "visible",
        "entailment_relationship": "visible_assumption_from",
        "source_span_ids": [],
        "product_claim_span_ids": [],
        "source_span_refs": [],
        "assumption": _PROVISIONAL_PROOF,
    }
    assert all(
        row["section_key"] not in {"proof_boundary", "assumptions"}
        for row in envelope["source_evidence"]["spans"]
    )
    assert all(
        link["field"] != "proof_boundary"
        for row in envelope["custody_ledger"]["atomic_facts"]
        for link in row["projection_links"]
    )

    authority = _authority(envelope)
    require_product_intent_authority(authority)
    assert authority["version"] == PRODUCT_INTENT_AUTHORITY_VERSION
    assert authority["material_fields"]["proof_boundary"] == custody


def test_source_stated_proof_retains_strict_source_custody() -> None:
    source, authored, intent = _authored_inputs()
    envelope = build_product_intent_envelope(
        intent,
        source_text=source,
        source_path="evidence.txt",
        source_format="operator_prompt",
        canonical_candidate_sha256="a" * 64,
        model_authoring=_model_authoring(),
        authored_source_spans=authored.source_spans,
        authored_atomic_claims=authored.atomic_claims,
        authored_source_sha256=authored.source_sha256,
    )
    authority = _authority(envelope)
    require_product_intent_authority(authority)

    custody = authority["material_fields"]["proof_boundary"]
    assert custody["custody_state"] == "accepted_fact"
    assert custody["source_span_ids"]
    assert custody["product_claim_span_ids"]
    assert "assumption" not in custody


def test_current_source14_rejects_proof_assumption_substitution() -> None:
    source, authored, intent = _authored_inputs()
    proposed = copy.deepcopy(intent)
    proposed["proof_boundary"] = ""
    proposed["assumptions"] = [copy.deepcopy(_PROVISIONAL_PROOF)]
    semantics = proposed[AUTHORED_SEMANTICS_KEY]
    assert semantics["source_duty"]["ledger_receipt"]["ledger"]["version"] == (
        "odylith.greenfield.source-duty-ledger.v14"
    )
    semantics["source_event_relations"] = [
        {**row, "visible_result_quote": ""} for row in authored.source_event_relations
    ]
    before = copy.deepcopy(proposed)

    with pytest.raises(ValueError, match="canonical complete run differs from its verified source plan"):
        build_product_intent_envelope(
            proposed, source_text=source, source_path="evidence.txt",
            source_format="operator_prompt", canonical_candidate_sha256="a" * 64,
            model_authoring=_model_authoring(), authored_source_spans=authored.source_spans,
            authored_atomic_claims=authored.atomic_claims,
            authored_source_sha256=authored.source_sha256,
        )
    assert proposed == before


def test_provisional_proof_missing_competing_malformed_or_fact_overlap_fails() -> None:
    source, intent, spans, claims = _passive_provisional_inputs()

    missing = copy.deepcopy(intent)
    missing["assumptions"] = []
    with pytest.raises(ValueError, match="one source fact or one assumption"):
        build_product_intent_envelope(
            missing,
            source_text=source,
            source_path="evidence.txt",
            source_format="in_memory_confirmed_intent",
            canonical_candidate_sha256="a" * 64,
            authored_source_spans=spans,
            authored_atomic_claims=claims,
            authored_source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        )

    for assumptions in (
        [_PROVISIONAL_PROOF, _PROVISIONAL_PROOF],
        [{"applies_to": "proof_boundary", "statement": ""}],
    ):
        invalid = copy.deepcopy(intent)
        invalid["assumptions"] = copy.deepcopy(assumptions)
        with pytest.raises(ValueError):
            build_product_intent_envelope(
                invalid,
                source_text=source,
                source_path="evidence.txt",
                source_format="in_memory_confirmed_intent",
                canonical_candidate_sha256="a" * 64,
                authored_source_spans=spans,
                authored_atomic_claims=claims,
                authored_source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            )

    source_fact, authored, source_intent = _authored_inputs()
    overlap = copy.deepcopy(source_intent)
    overlap["assumptions"] = [copy.deepcopy(_PROVISIONAL_PROOF)]
    with pytest.raises(ValueError, match="one source fact or one assumption"):
        build_product_intent_envelope(
            overlap,
            source_text=source_fact,
            source_path="evidence.txt",
            source_format="operator_prompt",
            canonical_candidate_sha256="a" * 64,
            model_authoring=_model_authoring(),
            authored_source_spans=authored.source_spans,
            authored_atomic_claims=authored.atomic_claims,
            authored_source_sha256=authored.source_sha256,
        )


def test_provisional_proof_bytes_and_hashes_reject_tampering() -> None:
    envelope = _build_provisional_envelope()
    altered_envelope = copy.deepcopy(envelope)
    altered_envelope["custody_ledger"]["fields"]["proof_boundary"]["assumption"][
        "statement"
    ] += " changed"
    with pytest.raises(ValueError, match="invalid provisional proof custody"):
        _authority(altered_envelope)

    extra_custody = copy.deepcopy(envelope)
    extra_custody["custody_ledger"]["fields"]["proof_boundary"]["legacy"] = True
    with pytest.raises(ValueError, match="invalid provisional proof custody"):
        _authority(extra_custody)

    authority = _authority(envelope)
    sealed_bytes = _canonical_bytes(authority)
    require_sealed_product_intent_authority_bytes(
        authority,
        authority_bytes=sealed_bytes,
        preconfirm_provenance_bytes=sealed_bytes,
    )

    missing = copy.deepcopy(authority)
    missing["material_fields"]["proof_boundary"].pop("assumption")
    _rebind_authority_hashes(missing)
    with pytest.raises(ValueError, match="invalid provisional proof custody"):
        require_product_intent_authority(missing)

    competing = copy.deepcopy(authority)
    competing["material_fields"]["proof_boundary"]["assumption"] = [
        _PROVISIONAL_PROOF,
        _PROVISIONAL_PROOF,
    ]
    _rebind_authority_hashes(competing)
    with pytest.raises(ValueError, match="invalid provisional proof custody"):
        require_product_intent_authority(competing)

    retired = copy.deepcopy(authority)
    retired["version"] = "odylith.product-intent-authority.v10"
    retired["envelope_schema_version"] = "odylith.product-intent-envelope.v10"
    retired["ledger_version"] = "odylith.product-intent-custody-ledger.v7"
    retired["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(
        retired
    )
    with pytest.raises(ValueError, match="unsupported version"):
        require_product_intent_authority(retired)

    tampered = copy.deepcopy(authority)
    tampered["material_fields"]["proof_boundary"]["assumption"]["statement"] += (
        " changed"
    )
    _rebind_authority_hashes(tampered)
    tampered_bytes = _canonical_bytes(tampered)
    assert tampered["material_custody_sha256"] != authority["material_custody_sha256"]
    assert tampered["authority_snapshot_sha256"] != authority["authority_snapshot_sha256"]
    with pytest.raises(ValueError, match="pre-confirm provenance bytes"):
        require_sealed_product_intent_authority_bytes(
            tampered,
            authority_bytes=tampered_bytes,
            preconfirm_provenance_bytes=sealed_bytes,
        )
