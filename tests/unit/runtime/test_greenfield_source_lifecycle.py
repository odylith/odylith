from __future__ import annotations

from copy import deepcopy
import json

import pytest

from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    SOURCE_DUTY_BINDING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_VERSION,
    GreenfieldSourceDutyLedgerError,
)
from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import (
    GreenfieldSourceLifecycleError,
    SOURCE_LIFECYCLE_VERSION,
    project_greenfield_source_lifecycle,
    require_verified_greenfield_source_lifecycle,
    _sha256,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    synthetic_source_duty_receipt_for_ledger,
)


def _citation(quote: str, context: str | None = None) -> dict[str, str]:
    return {"quote": quote, "context": context or quote}


def _case(noun: str) -> tuple[str, dict, dict, dict]:
    evidence = (
        f"A steward opens the {noun}. A reviewer approves the {noun}. "
        f"Withdrawal closes {noun} access and erases the cached copy."
    )
    ledger = {
        "version": SOURCE_DUTY_LEDGER_VERSION,
        "status": "inventory",
        "question": "",
        "evidence_controls": [],
        "first_path_actions": [
            {
                "id": "A1", "source_refs": [],
                "action": "opens", "target": f"the {noun}",
                "performer_role": "human_actor",
                "observable_result": f"{noun} opened",
                "event_ref": _citation(f"steward opens the {noun}"),
                "actor_ref": {"quote": "steward", "context": f"A steward opens the {noun}"},
                "statement": f"steward opens the {noun}",
                "role_refs": [_citation(f"steward opens the {noun}")],
            },
            {
                "id": "A2", "source_refs": [],
                "action": "approves", "target": f"the {noun}",
                "performer_role": "human_actor",
                "observable_result": f"{noun} approved",
                "event_ref": _citation(f"reviewer approves the {noun}"),
                "actor_ref": _citation("reviewer"),
                "statement": f"reviewer approves the {noun}",
                "role_refs": [_citation(f"reviewer approves the {noun}")],
            },
        ],
        "supporting_human_actions": [],
        "system_duties": [],
        "state_fields": [
            {
                "id": "F1", "source_refs": [_citation(f"{noun} access")],
                "state_object": noun, "field": "access", "meaning": "access status",
            },
            {
                "id": "F2", "source_refs": [_citation("cached copy")],
                "state_object": noun, "field": "cache", "meaning": "cached copy",
            },
        ],
        "off_path_transitions": [
            {
                "id": "T1",
                "source_refs": [_citation(
                    f"Withdrawal closes {noun} access and erases the cached copy"
                )],
                "trigger": "withdrawal", "governed_object": noun,
                "effects": [
                    {"field": "access", "change": "closed", "observable_check": "access closed"},
                    {"field": "cache", "change": "erased", "observable_check": "cache empty"},
                ],
            }
        ],
        "conditional_guards": [], "boundaries": [], "proof_duties": [],
    }
    receipt = synthetic_source_duty_receipt_for_ledger(
        ledger, evidence_text=evidence
    )
    candidate = {
        "status": "authored",
        "events": [
            {
                "actor_fact": {"field": "human_actors", "row": 1},
            },
            {
                "actor_fact": {"field": "human_actors", "row": 2},
            },
        ],
        "facts": {"human_actors": [
            {"quote": "steward", "context": f"A steward opens the {noun}"},
            _citation("reviewer"),
        ]},
        "terminal": {"event_order": 2},
        "provisional_design": {
            "first_run": {"event_orders": [1, 2]},
            "components": [{"key": "record-state"}],
            "workstreams": [
                {"key": "record-delivery", "component_keys": ["record-state"]}
            ],
        },
    }
    binding = {
        "version": SOURCE_DUTY_BINDING_VERSION,
        "source_sha256": receipt["source_sha256"],
        "ledger_sha256": receipt["ledger_sha256"],
        "first_path_actions": [
            {"duty_id": "A1", "event_order": 1},
            {"duty_id": "A2", "event_order": 2},
        ],
        "supporting_human_actions": [],
        "system_duties": [],
        "off_path_transitions": [
            {
                "duty_id": "T1", "component_key": "record-state",
                "workstream_key": "record-delivery",
                "effects": [
                    {"effect_index": 1, "state_field_id": "F1"},
                    {"effect_index": 2, "state_field_id": "F2"},
                ],
            }
        ],
        "conditional_guards": [],
        "boundaries": [],
        "proof_duties": [],
    }
    return evidence, receipt, candidate, binding


@pytest.mark.parametrize("noun", ("dossier", "shipment"))
def test_passive_transition_preserves_two_cited_field_effects(noun: str) -> None:
    evidence, receipt, candidate, binding = _case(noun)
    lifecycle = project_greenfield_source_lifecycle(
        ledger_receipt=receipt, binding=binding,
        candidate_result=candidate, evidence_text=evidence,
    )
    assert lifecycle["version"] == SOURCE_LIFECYCLE_VERSION
    assert len(lifecycle["lifecycle_sha256"]) == 64
    assert [row["duty_id"] for row in lifecycle["state_fields"]] == ["F1", "F2"]
    assert [row["source_refs"][0]["quote"] for row in lifecycle["state_fields"]] == [
        f"{noun} access", "cached copy"
    ]
    transition = lifecycle["off_path_transitions"][0]
    assert transition["trigger"] == "withdrawal"
    assert transition["governed_object"] == noun
    assert transition["component_key"] == "record-state"
    assert transition["workstream_key"] == "record-delivery"
    assert transition["source_refs"][0]["quote"].startswith("Withdrawal closes")
    assert transition["effects"] == [
        {"state_field_id": "F1", "field": "access", "change": "closed", "observable_check": "access closed"},
        {"state_field_id": "F2", "field": "cache", "change": "erased", "observable_check": "cache empty"},
    ]
    assert "actor" not in json.dumps(transition)
    assert "performer" not in json.dumps(transition)
    assert project_greenfield_source_lifecycle(
        ledger_receipt=receipt, binding=binding,
        candidate_result=candidate, evidence_text=evidence,
    ) == lifecycle


def test_projection_rejects_tampered_receipt_and_missing_binding() -> None:
    evidence, receipt, candidate, binding = _case("dossier")
    tampered = deepcopy(receipt)
    tampered["ledger"]["off_path_transitions"][0]["trigger"] = "approval"
    with pytest.raises(GreenfieldSourceLifecycleError, match="custody"):
        project_greenfield_source_lifecycle(
            ledger_receipt=tampered, binding=binding,
            candidate_result=candidate, evidence_text=evidence,
        )
    binding["off_path_transitions"].clear()
    with pytest.raises(GreenfieldSourceLifecycleError, match="custody"):
        project_greenfield_source_lifecycle(
            ledger_receipt=receipt, binding=binding,
            candidate_result=candidate, evidence_text=evidence,
        )


def test_projection_rejects_field_or_object_identity_mismatch() -> None:
    evidence, receipt, candidate, binding = _case("dossier")
    binding["off_path_transitions"][0]["effects"][0]["state_field_id"] = "F2"
    with pytest.raises(GreenfieldSourceLifecycleError, match="custody"):
        project_greenfield_source_lifecycle(
            ledger_receipt=receipt, binding=binding,
            candidate_result=candidate, evidence_text=evidence,
        )

    evidence, receipt, candidate, binding = _case("dossier")
    changed = deepcopy(receipt["ledger"])
    changed["state_fields"][0]["state_object"] = "another dossier"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="no declared state-field identity"):
        synthetic_source_duty_receipt_for_ledger(changed, evidence_text=evidence)


def test_projection_preserves_typed_design_duties_and_exact_citations() -> None:
    evidence, receipt, candidate, binding = _case("dossier")
    evidence += (
        " Before approval, consent must be active."
        " Only stewards may approve."
        " Audit dossier must show the approval decision."
    )
    ledger = deepcopy(receipt["ledger"])
    ledger["conditional_guards"] = [{
        "id": "G1", "source_refs": [_citation("Before approval, consent must be active")],
        "trigger": "before approval", "protected_action": "approval",
        "rule": "consent must be active",
    }]
    ledger["boundaries"] = [{
        "id": "B1", "source_refs": [_citation("Only stewards may approve")],
        "kind": "authority", "rule": "Only stewards may approve",
    }]
    ledger["proof_duties"] = [{
        "id": "P1", "source_refs": [_citation("Audit dossier must show the approval decision")],
        "dossier_or_artifact": "Audit dossier", "must_show": "the approval decision",
    }]
    receipt = synthetic_source_duty_receipt_for_ledger(
        ledger, evidence_text=evidence
    )
    binding["source_sha256"] = receipt["source_sha256"]
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    for role, duty_id in (
        ("conditional_guards", "G1"), ("boundaries", "B1"), ("proof_duties", "P1"),
    ):
        binding[role] = [{
            "duty_id": duty_id, "component_key": "record-state",
            "workstream_key": "record-delivery",
        }]
    lifecycle = project_greenfield_source_lifecycle(
        ledger_receipt=receipt, binding=binding,
        candidate_result=candidate, evidence_text=evidence,
    )
    assert lifecycle["conditional_guards"][0]["rule"] == "consent must be active"
    assert lifecycle["boundaries"][0]["kind"] == "authority"
    assert lifecycle["proof_duties"][0]["must_show"] == "the approval decision"
    for role in ("conditional_guards", "boundaries", "proof_duties"):
        projected = lifecycle[role][0]
        assert projected["duty_id"] == binding[role][0]["duty_id"]
        assert projected["source_refs"][0] == {
            "quote": ledger[role][0]["source_refs"][0]["quote"], "occurrence": 1,
        }
    source_duty = {"ledger_receipt": receipt, "binding": binding, "lifecycle": lifecycle}
    require_verified_greenfield_source_lifecycle(
        source_duty, evidence_text=evidence, provisional_design=candidate["provisional_design"],
    )
    for role in ("conditional_guards", "boundaries", "proof_duties"):
        changed = deepcopy(source_duty)
        changed["lifecycle"][role][0]["source_refs"][0]["occurrence"] = 999
        _rehash_lifecycle(changed)
        with pytest.raises(GreenfieldSourceLifecycleError, match="accepted duty projection"):
            require_verified_greenfield_source_lifecycle(
                changed, evidence_text=evidence, provisional_design=candidate["provisional_design"],
            )


def test_ordered_distinct_effects_can_share_one_canonical_parent_field() -> None:
    evidence, receipt, candidate, binding = _case("dossier")
    evidence += " Dossier state includes access and the cached copy."
    ledger = deepcopy(receipt["ledger"])
    ledger["state_fields"] = [{
        "id": "F1", "state_object": "dossier", "field": "state",
        "meaning": "access and cached copy state",
        "source_refs": [_citation("Dossier state includes access and the cached copy")],
    }]
    for effect in ledger["off_path_transitions"][0]["effects"]:
        effect["field"] = "state"
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence)
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    binding["source_sha256"] = receipt["source_sha256"]
    for effect in binding["off_path_transitions"][0]["effects"]:
        effect["state_field_id"] = "F1"
    lifecycle = project_greenfield_source_lifecycle(
        ledger_receipt=receipt, binding=binding, candidate_result=candidate, evidence_text=evidence,
    )
    assert lifecycle["off_path_transitions"][0]["effects"] == [
        {"state_field_id": "F1", "field": "state", "change": "closed", "observable_check": "access closed"},
        {"state_field_id": "F1", "field": "state", "change": "erased", "observable_check": "cache empty"},
    ]


def _rehash_lifecycle(source_duty):
    lifecycle = source_duty["lifecycle"]
    lifecycle["binding_sha256"] = _sha256(source_duty["binding"])
    lifecycle["lifecycle_sha256"] = _sha256({
        key: value for key, value in lifecycle.items() if key != "lifecycle_sha256"
    })


@pytest.mark.parametrize("noun", ["dossier", "shipment"])
def test_full_lifecycle_readback_preserves_original_admission_projection(noun):
    evidence, receipt, candidate, binding = _case(noun)
    lifecycle = project_greenfield_source_lifecycle(
        ledger_receipt=receipt, binding=binding, candidate_result=candidate, evidence_text=evidence,
    )
    source_duty = {"ledger_receipt": receipt, "binding": binding, "lifecycle": lifecycle}
    original = deepcopy(source_duty)
    require_verified_greenfield_source_lifecycle(
        source_duty, evidence_text=evidence, provisional_design=candidate["provisional_design"],
    )
    assert source_duty == original
    assert lifecycle["off_path_transitions"][0]["effects"] == [
        {"state_field_id": "F1", "field": "access", "change": "closed", "observable_check": "access closed"},
        {"state_field_id": "F2", "field": "cache", "change": "erased", "observable_check": "cache empty"},
    ]


@pytest.mark.parametrize("damage", [
    "version", "extra_field", "missing_field", "state_meaning", "state_object", "state_quote",
    "state_occurrence", "boolean_occurrence", "state_coverage", "effect_change", "effect_check",
    "effect_field", "effect_order", "effect_coverage", "binding_owner", "coordinated_binding_owner",
    "binding_workstream", "binding_state_field", "binding_effect_index", "binding_extra_field",
])
def test_rehashed_passive_lifecycle_cannot_replace_accepted_meaning_or_ownership(damage):
    evidence, receipt, candidate, binding = _case("dossier")
    lifecycle = project_greenfield_source_lifecycle(
        ledger_receipt=receipt, binding=binding, candidate_result=candidate, evidence_text=evidence,
    )
    source_duty = {"ledger_receipt": receipt, "binding": binding, "lifecycle": lifecycle}
    if damage == "version":
        lifecycle["version"] = "attacker.v1"
    elif damage == "extra_field":
        lifecycle["extra"] = []
    elif damage == "missing_field":
        lifecycle.pop("state_fields")
    elif damage == "state_meaning":
        lifecycle["state_fields"][0]["meaning"] = "invented meaning"
    elif damage == "state_object":
        lifecycle["state_fields"][0]["state_object"] = "other dossier"
    elif damage == "state_quote":
        lifecycle["state_fields"][0]["source_refs"][0]["quote"] = "invented witness"
    elif damage in {"state_occurrence", "boolean_occurrence"}:
        lifecycle["state_fields"][0]["source_refs"][0]["occurrence"] = 999 if damage == "state_occurrence" else True
    elif damage == "state_coverage":
        lifecycle["state_fields"].pop()
    elif damage == "effect_change":
        lifecycle["off_path_transitions"][0]["effects"][0]["change"] = "invented effect"
    elif damage == "effect_check":
        lifecycle["off_path_transitions"][0]["effects"][0]["observable_check"] = "invented check"
    elif damage == "effect_field":
        lifecycle["off_path_transitions"][0]["effects"][0]["field"] = "cache"
    elif damage == "effect_order":
        lifecycle["off_path_transitions"][0]["effects"].reverse()
    elif damage == "effect_coverage":
        lifecycle["off_path_transitions"][0]["effects"].pop()
    elif damage in {"binding_owner", "coordinated_binding_owner"}:
        binding["off_path_transitions"][0]["component_key"] = "missing-component"
        if damage == "coordinated_binding_owner":
            lifecycle["off_path_transitions"][0]["component_key"] = "missing-component"
    elif damage == "binding_workstream":
        candidate["provisional_design"]["workstreams"][0]["component_keys"] = []
    elif damage == "binding_state_field":
        binding["off_path_transitions"][0]["effects"][0]["state_field_id"] = "F2"
    elif damage == "binding_effect_index":
        binding["off_path_transitions"][0]["effects"][0]["effect_index"] = 2
    elif damage == "binding_extra_field":
        binding["off_path_transitions"][0]["extra"] = []
    _rehash_lifecycle(source_duty)
    with pytest.raises(GreenfieldSourceLifecycleError):
        require_verified_greenfield_source_lifecycle(
            source_duty, evidence_text=evidence, provisional_design=candidate["provisional_design"],
        )
