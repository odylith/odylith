from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_intent_authority
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import render_product_intent_preview
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_FACTS_HASH_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_snapshot_hash,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import atomic_fact_ledger_hash
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_greenfield_package_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import canonical_model_authored_intent_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _canonical_model_authored_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import approved_authored_quality_manifest_fixture


def _approved_quality_manifest() -> dict[str, Any]:
    return approved_authored_quality_manifest_fixture(
        semantic_compiler={
            "version": "odylith.greenfield.authored-semantic-validation.v3",
            "status": "passed",
            "semantic_owner": "validated_model_authored_intent",
            "post_authoring_interpretation_calls": 0,
        }
    )


def _recorded_authority(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    candidate = canonical_model_authored_intent_fixture(tmp_path)
    authority = dict(candidate[PRODUCT_INTENT_AUTHORITY_KEY])
    facts = {
        key: value
        for key, value in candidate.items()
        if key != PRODUCT_INTENT_AUTHORITY_KEY
    }
    source_path = tmp_path / str(authority["markdown_source_path"])
    return source_path, facts, authority


def _transaction(tmp_path: Path, *, authority: dict[str, Any] | None = None) -> Any:
    _path, _facts, file_authority = _recorded_authority(tmp_path)
    intent_authority = authority or file_authority
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    package = compiled_greenfield_package_fixture(
        proposal=proposal,
        repo_root=tmp_path,
    )
    return build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=intent_authority,
        quality_manifest=_approved_quality_manifest(),
        repo_root=tmp_path,
    )


def test_product_create_transaction_carries_confirmed_intent_authority_block(tmp_path: Path) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    payload = product_create_transaction_to_dict(transaction)

    persisted = payload["intent_authority"]
    assert persisted["version"] == "odylith.product-intent-authority.v10"
    assert persisted["origin"] == "verified_typed_envelope"
    assert persisted["decision"] == "confirmed_intent_accepted"
    assert persisted["fact_authority"] == "product_facts"
    assert persisted["markdown_authority"] == "ingest_only"
    assert persisted[PRODUCT_FACTS_HASH_KEY] == authority[PRODUCT_FACTS_HASH_KEY]
    assert persisted["markdown_source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert persisted["markdown_source_path"] == str(path.relative_to(tmp_path))
    assert persisted["structured_intent_path"] == authority["structured_intent_path"]
    assert persisted["source_format"] == "operator_prompt"
    assert persisted["materiality_status"] == "passed"
    assert persisted["material_custody_sha256"]
    assert persisted["atomic_ledger_version"] == "odylith.product-intent-atomic-facts.v3"
    assert persisted["atomic_facts"]
    assert persisted["atomic_custody_sha256"] == atomic_fact_ledger_hash(persisted["atomic_facts"])
    assert persisted["operating_envelope"]["status"] == "supported"
    assert persisted["authority_snapshot_sha256"] == product_intent_authority_snapshot_hash(persisted)
    assert persisted["material_fields"]["first_path"]["custody_state"] == "accepted_fact"
    assert payload["transaction_hash"] == transaction.transaction_hash

    restored = product_create_transaction_from_dict(payload)

    assert restored.intent_authority[PRODUCT_FACTS_HASH_KEY] == authority[PRODUCT_FACTS_HASH_KEY]
    assert restored.summary()["product_facts_sha256"] == authority[PRODUCT_FACTS_HASH_KEY]


def test_serialized_authored_transaction_contains_only_sealed_component_relation_identity(
    tmp_path: Path,
) -> None:
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    candidate = canonical_model_authored_intent_fixture(tmp_path)
    authority = dict(candidate[PRODUCT_INTENT_AUTHORITY_KEY])
    intent = {
        key: value
        for key, value in candidate.items()
        if key != PRODUCT_INTENT_AUTHORITY_KEY
    }
    proposal = {
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "intent": intent,
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
        "backlog": [],
        "components": [],
        "diagrams": [],
    }
    package = compiled_greenfield_package_fixture(proposal, repo_root=tmp_path)
    quality_manifest = {
        **_approved_quality_manifest(),
        "semantic_compiler": {
            "version": "odylith.greenfield.authored-semantic-validation.v3",
            "status": "passed",
            "semantic_owner": "validated_model_authored_intent",
            "post_authoring_interpretation_calls": 0,
        },
        "model_authoring": {
            "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "semantic_model_call_count": 1,
            "tier": "standard",
            "elapsed_seconds": 1.0,
            "model_profile": {
                "profile_id": profile.profile_id,
                "provider": profile.provider,
                "model": profile.model,
                "reasoning_effort": profile.reasoning_effort,
                "effective_timeout_seconds": profile.model_timeout_seconds,
                "authoring_tier": profile.repair_tier,
            },
        },
    }
    transaction = build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=quality_manifest,
        repo_root=tmp_path,
    )

    payload = product_create_transaction_to_dict(transaction)
    sealed_relations = payload["proposal"]["intent"]["authored_semantics"][
        "component_responsibility_relations"
    ]
    serialized = json.dumps(payload, sort_keys=True)

    assert sealed_relations
    assert all(isinstance(row["first_path_event_order"], int) for row in sealed_relations)
    assert "responsibility_fact_index" not in serialized
    assert "owner_system_fact_index" not in serialized


def test_product_create_transaction_rejects_missing_intent_authority_payload(tmp_path: Path) -> None:
    payload = product_create_transaction_to_dict(_transaction(tmp_path))
    payload.pop("intent_authority")

    with pytest.raises(ValueError, match="Product Intent authority"):
        product_create_transaction_from_dict(payload)


def test_product_create_transaction_rejects_v3_authority_with_rebuild_instruction(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    legacy = {**authority, "version": "odylith.product-intent-authority.v3"}

    with pytest.raises(ValueError, match="unsupported version; rebuild the proposal before confirmation"):
        _transaction(tmp_path, authority=legacy)


def test_product_create_transaction_rejects_v4_authority_for_sealed_retry(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    legacy = {
        **authority,
        "version": "odylith.product-intent-authority.v4",
        "envelope_schema_version": "odylith.product-intent-envelope.v4",
        "ledger_version": "odylith.product-intent-custody-ledger.v3",
    }
    legacy["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(legacy)

    with pytest.raises(ValueError, match="unsupported version; rebuild the proposal before confirmation"):
        _transaction(tmp_path, authority=legacy)


@pytest.mark.parametrize(
    ("authority_version", "envelope_version", "ledger_version", "atomic_version"),
    (
        (6, 6, 5, None),
        (7, 7, 6, None),
        (8, 8, 6, None),
        (9, 9, 6, 2),
    ),
)
def test_product_create_transaction_rejects_legacy_authority_without_reinterpretation(
    tmp_path: Path,
    authority_version: int,
    envelope_version: int,
    ledger_version: int,
    atomic_version: int | None,
) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    legacy = {
        **authority,
        "version": f"odylith.product-intent-authority.v{authority_version}",
        "envelope_schema_version": f"odylith.product-intent-envelope.v{envelope_version}",
        "ledger_version": f"odylith.product-intent-custody-ledger.v{ledger_version}",
    }
    if atomic_version is not None:
        legacy["atomic_ledger_version"] = (
            f"odylith.product-intent-atomic-facts.v{atomic_version}"
        )
    legacy["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(legacy)

    with pytest.raises(ValueError, match="unsupported version; rebuild the proposal before confirmation"):
        _transaction(tmp_path, authority=legacy)


def test_product_create_transaction_rejects_blocked_materiality_authority(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    blocked = {
        **authority,
        "materiality_status": "clarification_required",
        "blocked_material_fields": ["first_path"],
    }
    blocked["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(blocked)

    with pytest.raises(ValueError, match="did not pass materiality"):
        _transaction(tmp_path, authority=blocked)


def test_product_create_transaction_rejects_inferred_material_custody(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "custody_state": "inferred_fact",
        "derivation": "normalization_or_completion",
        "confidence": "medium",
        "source_span_ids": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="unresolved material custody"):
        _transaction(tmp_path, authority=mutated)


def test_product_create_transaction_rejects_tampered_atomic_fact_custody(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    atomic_facts = [dict(row) for row in authority["atomic_facts"]]
    atomic_facts[0] = {**atomic_facts[0], "normalized_value": "unbound replacement claim"}
    mutated = {
        **authority,
        "atomic_facts": atomic_facts,
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="invalid atom id"):
        _transaction(tmp_path, authority=mutated)


def test_product_create_transaction_rejects_accepted_material_fact_without_source_custody(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "source_span_ids": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="missing material source custody"):
        _transaction(tmp_path, authority=mutated)


def test_product_create_transaction_rejects_material_fact_without_resolvable_span_receipts(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "source_span_refs": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="invalid material source spans"):
        _transaction(tmp_path, authority=mutated)


def test_product_create_transaction_rejects_tampered_material_evidence_text(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = json.loads(json.dumps(authority["material_fields"]))
    material_fields["first_path"]["source_span_refs"][0]["evidence_text"] = "tampered evidence"
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="invalid material source spans"):
        _transaction(tmp_path, authority=mutated)


def test_product_create_transaction_rejects_actor_injected_after_sealing(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    proposal = json.loads(json.dumps(transaction.proposal))
    proposal["intent"]["human_actors"].append(
        "Coach or Clinician: receives a read-only summary later."
    )
    mutated = replace(transaction, proposal=proposal)

    with pytest.raises(ValueError, match="proposal facts do not match"):
        require_product_create_transaction_verified(mutated)


def test_product_create_transaction_rejects_markdown_material_fact_without_product_claim_custody(
    tmp_path: Path,
) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "product_claim_span_ids": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="missing material product-claim custody"):
        _transaction(tmp_path, authority=mutated)


def test_product_intent_preview_lists_operational_constraints_before_human_actors() -> None:
    preview = render_product_intent_preview(
        {
            "title": "Berth Turnaround Control",
            "first_path": "A berth planner reviews one vessel call and sees the handoff receipt.",
            "operational_constraints": ["Pier 7"],
            "human_actors": ["Berth planner"],
        }
    )

    assert "## Operational constraints\n- Pier 7" in preview
    assert preview.index("## Operational constraints") < preview.index("## Human actors")


def test_transaction_rejects_typed_intent_drift_from_its_sealed_authority(tmp_path: Path) -> None:
    _path, facts, authority = _recorded_authority(tmp_path)
    valid_proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    package = compiled_greenfield_package_fixture(proposal=valid_proposal, repo_root=tmp_path)
    proposal = {
        **valid_proposal,
        "intent": {**facts, "title": "Different Product Identity"},
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
    }
    package = replace(package, proposal=proposal)

    with pytest.raises(ValueError, match="proposal facts do not match its sealed Product Intent authority"):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="0.0.1",
            validation_gate={"status": "passed", "issues": []},
            prewrite_package=package,
            backlog_result=package.backlog_result or {},
            intent_authority=authority,
            quality_manifest=_approved_quality_manifest(),
            repo_root=tmp_path,
        )


@pytest.mark.parametrize("damage", ("missing_sidecar", "invalid_sidecar", "source_drift", "envelope_drift"))
def test_product_create_transaction_intent_authority_uses_sealed_snapshot(
    tmp_path: Path,
    damage: str,
) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    structured_path = tmp_path / str(authority["structured_intent_path"])
    if damage == "missing_sidecar":
        structured_path.unlink()
    elif damage == "invalid_sidecar":
        structured_path.write_text("{not-json", encoding="utf-8")
    elif damage == "source_drift":
        path.write_text(path.read_text(encoding="utf-8") + "\nDrifted after compile.\n", encoding="utf-8")
    elif damage == "envelope_drift":
        payload = json.loads(structured_path.read_text(encoding="utf-8"))
        payload["decision_record"] = {
            **dict(payload["decision_record"]),
            "fact_authority": "markdown_projection",
        }
        structured_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    require_product_create_transaction_intent_authority(transaction, repo_root=tmp_path)


def test_product_create_transaction_hash_rejects_intent_authority_mutation(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    mutated = replace(
        transaction,
        intent_authority={**dict(transaction.intent_authority), PRODUCT_FACTS_HASH_KEY: "forged"},
    )

    assert not mutated.verified
    with pytest.raises(ValueError, match="hash mismatch"):
        require_product_create_transaction_verified(mutated)


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
