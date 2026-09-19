"""Sealed custody for a provisional proof choice that is not a source fact."""

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
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
    product_intent_authority_from_envelope,
    require_product_intent_authority,
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
    _authored_inputs,
)


_PROVISIONAL_PROOF = {
    "applies_to": "proof_boundary",
    "statement": "Use a reviewable readiness record as the proposed proof checkpoint.",
}
_NON_PROOF_SOURCE = "Background context has no proof checkpoint"


def _model_authoring() -> dict[str, Any]:
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    common = {
        "profile_id": profile.profile_id,
        "provider": profile.provider,
        "effective_timeout_seconds": profile.model_timeout_seconds,
        "authoring_tier": profile.repair_tier,
    }
    return {
        "participant_selection": {
            **common,
            "model": profile.participant_model,
            "reasoning_effort": profile.participant_reasoning_effort,
        },
        "remaining_candidate_authoring": {
            **common,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
        },
    }


def _provisional_inputs() -> tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    source, authored, intent = _authored_inputs()
    source_proof = str(intent["proof_boundary"])
    assert len(source_proof.encode("utf-8")) == len(_NON_PROOF_SOURCE.encode("utf-8"))
    source = source.replace(source_proof, _NON_PROOF_SOURCE, 1)

    provisional = copy.deepcopy(intent)
    provisional["proof_boundary"] = ""
    provisional["assumptions"] = [copy.deepcopy(_PROVISIONAL_PROOF)]
    relations = [
        {**row, "visible_result_quote": ""}
        for row in authored.first_path_relations
    ]
    provisional[AUTHORED_SEMANTICS_KEY] = authored_semantics_mapping(
        relations,
        authored.component_responsibility_relations,
        first_path_context_relations=authored.first_path_context_relations,
        provisional_design=authored.provisional_design,
    )
    spans = [
        copy.deepcopy(row)
        for row in authored.source_spans
        if row["section_key"] != "proof_boundary"
    ]
    claims = [
        copy.deepcopy(row)
        for row in authored.atomic_claims
        if row["field"] != "proof_boundary"
    ]
    return source, provisional, spans, claims


def _build_provisional_envelope() -> dict[str, Any]:
    source, intent, spans, claims = _provisional_inputs()
    return build_product_intent_envelope(
        intent,
        source_text=source,
        source_path="evidence.txt",
        source_format="operator_prompt",
        model_authoring=_model_authoring(),
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


def test_provisional_proof_is_sealed_as_assumption_without_source_authority() -> None:
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


def test_provisional_proof_missing_competing_malformed_or_fact_overlap_fails() -> None:
    source, intent, spans, claims = _provisional_inputs()

    missing = copy.deepcopy(intent)
    missing["assumptions"] = []
    with pytest.raises(ValueError, match="one source fact or one assumption"):
        build_product_intent_envelope(
            missing,
            source_text=source,
            source_path="evidence.txt",
            source_format="operator_prompt",
            model_authoring=_model_authoring(),
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
                source_format="operator_prompt",
                model_authoring=_model_authoring(),
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
