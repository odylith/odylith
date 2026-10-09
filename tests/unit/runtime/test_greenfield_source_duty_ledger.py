from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import pytest
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    GreenfieldSourceDutyEntailmentError,
    SOURCE_DUTY_DECISION_SET_VERSION,
    greenfield_source_duty_decision_set_schema,
    source_duty_entailment_task,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    SOURCE_DUTY_LEDGER_VERSION,
    greenfield_source_duty_ledger_schema,
    preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
    verify_greenfield_source_duty_ledger_receipt,
)

EVIDENCE = "Review workspace. First Complete Path: A reviewer defines scope and audience. Human Actors: The reviewer checks a submission. Product Systems: A portal records the submission. Reference notes govern the template."
EXTERNAL_ACTOR_EVIDENCE = "Product Systems: Berth map is the product. First Complete Path: Dock attendant Ivo enters a vessel tag and the product records berth occupancy."


def _citation(quote: str, context: str | None = None) -> dict[str, str]:
    return {"quote": quote, "context": context or quote}


def _ledger() -> dict:
    clause = _citation("A reviewer defines scope and audience")
    first = {
        "id": "A1",
        "source_refs": [clause],
        "performer_role": "human_actor",
        "observable_result": "scope defined",
        "statement": "reviewer defines scope",
        "event_ref": clause,
        "actor_ref": _citation("reviewer", "A reviewer defines scope and audience"),
        "role_refs": [_citation("First Complete Path:")],
        "action": "defines",
        "target": "scope",
    }
    supporting = {
        "id": "H1",
        "source_refs": [clause],
        "statement": "reviewer defines audience",
        "event_ref": clause,
        "actor_ref": _citation("reviewer", "A reviewer defines scope and audience"),
        "role_refs": [_citation("Human Actors:")],
        "action": "defines",
        "target": "audience",
    }
    system = {
        "execution_kind": "discrete_action",
        "id": "S1",
        "performer_role": "internal_system",
        "source_refs": [_citation("A portal records the submission")],
        "statement": "portal records the submission",
        "event_ref": _citation("A portal records the submission"),
        "actor_ref": _citation("portal"),
        "role_refs": [_citation("Product Systems:")],
        "action": "records",
        "target": "the submission",
    }
    return {
        "version": SOURCE_DUTY_LEDGER_VERSION,
        "product_identity": {"basis": "explicit_name", "source_ref": _citation("Review workspace")},
        "status": "inventory",
        "question": "",
        "evidence_controls": [
            {
                **_citation("Reference notes govern the template"),
                "handling": "reference_context",
            }
        ],
        "first_path_actions": [first],
        "supporting_human_actions": [supporting],
        "system_duties": [system],
        "state_fields": [],
        "off_path_transitions": [],
        "conditional_guards": [],
        "boundaries": [],
        "proof_duties": [],
    }


def _yes_decisions(preflight: dict, *, evidence_text: str = EVIDENCE) -> dict:
    return {
        "version": source_duty_entailment_task(preflight, evidence_text=evidence_text)["decision_set_schema"]["properties"]["version"]["enum"][0],
        **({"product_identity": {"verdict": "yes"}} if "product_identity" in preflight["ledger"] else {}),
        "verifier_task_sha256": source_duty_entailment_task(
            preflight, evidence_text=evidence_text
        )["verifier_task_sha256"],
        "decisions": {
            claim["duty_id"]: {
                "verdict": "yes",
                "support_ref_indexes": list(range(len(claim["source_refs"]))),
                "role_ref_indexes": list(range(len(claim["role_refs"]))),
            }
            for claim in preflight["claims"]
        },
        "source_completeness": {"verdict": "yes", "omissions": []},
    }


def _external_actor_ledger() -> dict:
    ledger = _ledger()
    ledger["product_identity"]["source_ref"] = _citation("Berth map")
    ledger["evidence_controls"] = []
    ledger["supporting_human_actions"] = []
    first = ledger["first_path_actions"][0]
    first_event = _citation("Dock attendant Ivo enters a vessel tag")
    first.update(
        {
            "source_refs": [first_event],
            "observable_result": "vessel tag entered",
            "statement": "Dock attendant Ivo enters a vessel tag",
            "event_ref": first_event,
            "actor_ref": _citation("Dock attendant Ivo"),
            "action": "enters",
            "target": "a vessel tag",
        }
    )
    system = ledger["system_duties"][0]
    system_event = _citation("the product records berth occupancy")
    actor = _citation("Berth map")
    system.update(
        {
            "source_refs": [system_event],
            "statement": "Berth map records berth occupancy",
            "event_ref": system_event,
            "actor_ref": actor,
            "role_refs": [_citation("Product Systems:")],
            "action": "records",
            "target": "berth occupancy",
        }
    )
    return ledger


def _material_duty_case() -> tuple[str, dict]:
    evidence = (
        EVIDENCE
        + " Consent status records whether approval is active. Consent access records access availability. Consent cache records the cached copy. Withdrawal closes access and purges the cache. Before approval, consent must be active. Only designated stewards may approve. Audit dossier must show the approval decision."
    )
    ledger = _ledger()
    ledger["state_fields"] = [
        {
            "id": "F1",
            "source_refs": [
                _citation("Consent status records whether approval is active")
            ],
            "state_object": "consent",
            "field": "status",
            "meaning": "approval is active",
        },
        {
            "id": "F2", "source_refs": [_citation("Consent access records access availability")],
            "state_object": "consent", "field": "access", "meaning": "access availability",
        },
        {
            "id": "F3", "source_refs": [_citation("Consent cache records the cached copy")],
            "state_object": "consent", "field": "cache", "meaning": "cached copy",
        },
    ]
    ledger["off_path_transitions"] = [
        {
            "id": "T1",
            "source_refs": [_citation("Withdrawal closes access and purges the cache")],
            "trigger": "withdrawal",
            "governed_object": "consent",
            "effects": [
                {
                    "field": "access",
                    "change": "closed",
                    "observable_check": "access closed",
                },
                {
                    "field": "cache",
                    "change": "purged",
                    "observable_check": "cache empty",
                },
            ],
        }
    ]
    ledger["conditional_guards"] = [
        {
            "id": "G1",
            "source_refs": [_citation("Before approval, consent must be active")],
            "trigger": "before approval",
            "protected_action": "approval",
            "rule": "consent must be active",
        }
    ]
    ledger["boundaries"] = [
        {
            "id": "B1",
            "source_refs": [_citation("Only designated stewards may approve")],
            "kind": "authority",
            "rule": "Only designated stewards may approve",
        }
    ]
    ledger["proof_duties"] = [
        {
            "id": "P1",
            "source_refs": [_citation("Audit dossier must show the approval decision")],
            "dossier_or_artifact": "Audit dossier",
            "must_show": "the approval decision",
        }
    ]
    return (evidence, ledger)


def test_preflight_is_structural_and_accepted_receipt_binds_decisions() -> None:
    schema = greenfield_source_duty_ledger_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["first_path_actions"]["maxItems"] <= 32
    assert greenfield_source_duty_decision_set_schema()["additionalProperties"] is False
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    assert preflight["source_sha256"] == hashlib.sha256(EVIDENCE.encode()).hexdigest()
    assert (
        preflight["ledger_sha256"]
        == hashlib.sha256(
            json.dumps(
                ledger, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )
    assert "decision_set" not in preflight
    task = source_duty_entailment_task(preflight, evidence_text=EVIDENCE)
    assert task["authority_source"] == EVIDENCE
    assert list(
        task["decision_set_schema"]["properties"]["decisions"]["properties"]
    ) == ["A1", "H1", "S1"]
    assert "claims" not in task
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=EVIDENCE, decision_set=_yes_decisions(preflight)
    )
    assert (
        receipt["decision_set_sha256"]
        == hashlib.sha256(
            json.dumps(
                receipt["decision_set"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )
    assert (
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=EVIDENCE)
        == receipt
    )
    ledger["first_path_actions"].clear()
    assert len(receipt["ledger"]["first_path_actions"]) == 1


def test_entailment_task_requires_exact_complete_authority_source() -> None:
    preflight = preflight_greenfield_source_duty_ledger(
        _ledger(), evidence_text=EVIDENCE
    )
    task = source_duty_entailment_task(preflight, evidence_text=EVIDENCE)
    assert task["authority_source"].endswith("Reference notes govern the template.")
    for changed_source in ("", EVIDENCE.replace("Reference notes", "Other notes")):
        with pytest.raises(GreenfieldSourceDutyEntailmentError):
            source_duty_entailment_task(preflight, evidence_text=changed_source)


def test_shared_full_clause_can_cite_two_cross_role_actions() -> None:
    preflight = preflight_greenfield_source_duty_ledger(
        _ledger(), evidence_text=EVIDENCE
    )
    first, supporting = preflight["claims"][:2]
    assert first["event_ref"] == supporting["event_ref"]
    assert first["action"] == supporting["action"]
    assert first["target"] != supporting["target"]
    assert first["statement"] == "reviewer defines scope"
    assert supporting["statement"] == "reviewer defines audience"


def test_material_receipt_requires_verdicts_for_all_eight_sections() -> None:
    evidence, ledger = _material_duty_case()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    decisions = _yes_decisions(preflight, evidence_text=evidence)
    assert len(decisions["decisions"]) == 10
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence, decision_set=decisions
    )
    assert receipt["verifier_task_sha256"] == decisions["verifier_task_sha256"]
    assert (
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=evidence)
        == receipt
    )
    action_only = deepcopy(decisions)
    action_only["decisions"] = {
        key: value
        for key, value in action_only["decisions"].items()
        if key in ("A1", "H1", "S1")
    }
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="incomplete"):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=evidence, decision_set=action_only
        )


def test_source_wide_verdict_blocks_omitted_guard_boundary_and_proof() -> None:
    evidence = (
        EVIDENCE
        + " Verify both definitions before use. Do not publish definitions. Keep source notes in the dossier."
    )
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    assert len(preflight["claims"]) == 3
    decisions = _yes_decisions(preflight, evidence_text=evidence)
    decisions["source_completeness"] = {
        "verdict": "no",
        "omissions": [
            {
                "omission_id": "G-omitted",
                "typed_role": "conditional_guard",
                "source_ref": _citation("Verify both definitions before use"),
            },
            {
                "omission_id": "B-omitted",
                "typed_role": "boundary",
                "source_ref": _citation("Do not publish definitions"),
            },
            {
                "omission_id": "P-omitted",
                "typed_role": "proof_duty",
                "source_ref": _citation("Keep source notes in the dossier"),
            },
        ],
    }
    assert all((row["verdict"] == "yes" for row in decisions["decisions"].values()))
    with pytest.raises(
        GreenfieldSourceDutyLedgerError, match="source completeness is not affirmative"
    ):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=evidence, decision_set=decisions
        )


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (
            lambda decision: decision["source_completeness"].update(
                {
                    "omissions": [
                        {
                            "omission_id": "G-omitted",
                            "typed_role": "conditional_guard",
                            "source_ref": _citation(
                                "Verify both definitions before use"
                            ),
                        }
                    ]
                }
            ),
            "verdict and omissions disagree",
        ),
        (
            lambda decision: decision["source_completeness"].update({"verdict": "no"}),
            "verdict and omissions disagree",
        ),
        (
            lambda decision: decision.pop("source_completeness"),
            "decision set is malformed",
        ),
        (
            lambda decision: decision["source_completeness"].update(
                {
                    "verdict": "uncertain",
                    "omissions": [
                        {
                            "omission_id": "G-omitted",
                            "typed_role": "conditional_guard",
                            "source_ref": _citation("fabricated source duty"),
                        }
                    ],
                }
            ),
            "invalid source citation",
        ),
        (
            lambda decision: decision["source_completeness"].update(
                {
                    "verdict": "no",
                    "omissions": [
                        {
                            "omission_id": "G-omitted",
                            "typed_role": "invented_role",
                            "source_ref": _citation(
                                "Verify both definitions before use"
                            ),
                        }
                    ],
                }
            ),
            "invalid identity",
        ),
    ],
)
def test_source_wide_verdict_rejects_wrong_yes_shape_and_bad_omission(
    mutate, expected: str
) -> None:
    evidence = EVIDENCE + " Verify both definitions before use."
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    decisions = _yes_decisions(preflight, evidence_text=evidence)
    mutate(decisions)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match=expected):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=evidence, decision_set=decisions
        )


@pytest.mark.parametrize(
    "section,mutate",
    [
        ("state_fields", lambda row: row.update({"meaning": "approval is revoked"})),
        (
            "off_path_transitions",
            lambda row: row["effects"][0].update({"change": "opened"}),
        ),
        (
            "conditional_guards",
            lambda row: row.update({"rule": "consent may be inactive"}),
        ),
        ("boundaries", lambda row: row.update({"rule": "Any visitor may approve"})),
        (
            "proof_duties",
            lambda row: row.update({"must_show": "omit the approval decision"}),
        ),
    ],
)
def test_inverted_material_duty_requires_a_fresh_affirmative_verdict(
    section, mutate
) -> None:
    evidence, ledger = _material_duty_case()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    assert [claim["section"] for claim in preflight["claims"]] == [
        "first_path_actions",
        "supporting_human_actions",
        "system_duties",
        "state_fields",
        "state_fields",
        "state_fields",
        "off_path_transitions",
        "conditional_guards",
        "boundaries",
        "proof_duties",
    ]
    original = next(
        (claim for claim in preflight["claims"] if claim["section"] == section)
    )
    old_decisions = _yes_decisions(preflight, evidence_text=evidence)
    changed = deepcopy(ledger)
    mutate(changed[section][0])
    changed_preflight = preflight_greenfield_source_duty_ledger(
        changed, evidence_text=evidence
    )
    inverted = next(
        (claim for claim in changed_preflight["claims"] if claim["section"] == section)
    )
    assert inverted["claim_sha256"] != original["claim_sha256"]
    assert inverted["material_row"] == changed[section][0]
    task = source_duty_entailment_task(changed_preflight, evidence_text=evidence)
    assert task["authority_source"] == evidence
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
        validate_greenfield_source_duty_ledger(
            changed, evidence_text=evidence, decision_set=old_decisions
        )
    decisions = _yes_decisions(changed_preflight, evidence_text=evidence)
    duty_index = next(
        (
            i
            for i, claim in enumerate(changed_preflight["claims"])
            if claim["section"] == section
        )
    )
    decisions["decisions"][changed_preflight["claims"][duty_index]["duty_id"]].update(
        {"verdict": "no", "support_ref_indexes": [], "role_ref_indexes": []}
    )
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="not affirmative"):
        validate_greenfield_source_duty_ledger(
            changed, evidence_text=evidence, decision_set=decisions
        )


def test_external_actor_may_be_a_span_within_an_explicit_role_reference() -> None:
    ledger = _ledger()
    first = ledger["first_path_actions"][0]
    first["actor_ref"] = _citation("The reviewer", "The reviewer checks a submission")
    first["statement"] = "The reviewer defines scope"
    first["role_refs"] = [_citation("The reviewer checks a submission")]
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    assert preflight["claims"][0]["actor_ref"]["quote"] == "The reviewer"
    first["role_refs"] = [_citation("First Complete Path:")]
    separate_context = preflight_greenfield_source_duty_ledger(
        ledger, evidence_text=EVIDENCE
    )
    assert separate_context["claims"][0]["role_refs"] == [
        first["actor_ref"], first["role_refs"][0]
    ]


def test_canonical_actor_is_reused_across_distinct_action_occurrences() -> None:
    evidence = (
        "Review workspace. Human Actors: Reviewer Mara is the designated reviewer. "
        "First Complete Path: Reviewer Mara approves the record. "
        "Supporting Human Work: Reviewer Mara verifies the record."
    )
    ledger = _ledger()
    ledger["evidence_controls"] = []
    ledger["system_duties"] = []
    actor = _citation("Reviewer Mara", "Reviewer Mara is the designated reviewer.")
    for section, statement, action, context in (
        (
            "first_path_actions", "Reviewer Mara approves the record.", "approves",
            "First Complete Path: Reviewer Mara approves the record.",
        ),
        (
            "supporting_human_actions", "Reviewer Mara verifies the record.", "verifies",
            "Supporting Human Work: Reviewer Mara verifies the record.",
        ),
    ):
        row = ledger[section][0]
        row.update(
            source_refs=[], statement=statement, event_ref=_citation(statement),
            actor_ref=deepcopy(actor), role_refs=[_citation(context)],
            action=action, target="the record",
        )
    ledger["first_path_actions"][0]["observable_result"] = "record approved"
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    first, supporting = preflight["claims"]
    assert first["event_ref"] != supporting["event_ref"]
    assert first["actor_ref"] == supporting["actor_ref"] == actor
    assert first["role_refs"][0] == supporting["role_refs"][0] == actor
    aliased = deepcopy(ledger)
    for section in ("first_path_actions", "supporting_human_actions"):
        aliased[section][0]["role_refs"].insert(0, deepcopy(actor))
    alias_preflight = preflight_greenfield_source_duty_ledger(
        aliased, evidence_text=evidence
    )
    for original, with_alias in zip(preflight["claims"], alias_preflight["claims"]):
        assert original["source_refs"] == with_alias["source_refs"]
        assert original["role_refs"] == with_alias["role_refs"]
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence,
        decision_set=_yes_decisions(preflight, evidence_text=evidence),
    )
    assert verify_greenfield_source_duty_ledger_receipt(
        receipt, evidence_text=evidence
    ) == receipt


def test_normalized_action_does_not_require_an_invented_verb_microcitation() -> None:
    evidence = "Review workspace. First Complete Path: A reviewer defines scope and audience."
    ledger = _ledger()
    ledger["evidence_controls"] = []
    ledger["supporting_human_actions"] = []
    ledger["system_duties"] = []
    first = ledger["first_path_actions"][0]
    first.update(
        {
            "event_ref": _citation("and audience"),
            "source_refs": [],
            "actor_ref": _citation("A reviewer"),
            "role_refs": [_citation("A reviewer defines scope and audience")],
            "action": "defines",
            "target": "audience",
            "statement": "A reviewer defines audience",
        }
    )
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    assert preflight["claims"][0]["action"] == "defines"
    validate_greenfield_source_duty_ledger(
        ledger,
        evidence_text=evidence,
        decision_set=_yes_decisions(preflight, evidence_text=evidence),
    )


def test_external_actor_reference_requires_explicit_custody_and_semantic_yes() -> None:
    ledger = _external_actor_ledger()
    preflight = preflight_greenfield_source_duty_ledger(
        ledger, evidence_text=EXTERNAL_ACTOR_EVIDENCE
    )
    assert preflight["claims"][1]["actor_ref"]["quote"] == "Berth map"
    validate_greenfield_source_duty_ledger(
        ledger,
        evidence_text=EXTERNAL_ACTOR_EVIDENCE,
        decision_set=_yes_decisions(preflight, evidence_text=EXTERNAL_ACTOR_EVIDENCE),
    )
    assert preflight["claims"][1]["role_refs"] == [
        ledger["system_duties"][0]["actor_ref"], _citation("Product Systems:")
    ]
    false_actor = deepcopy(ledger)
    system = false_actor["system_duties"][0]
    system["actor_ref"] = _citation("Dock attendant Ivo")
    system["statement"] = "Dock attendant Ivo records berth occupancy"
    false_preflight = preflight_greenfield_source_duty_ledger(
        false_actor, evidence_text=EXTERNAL_ACTOR_EVIDENCE
    )
    decisions = _yes_decisions(false_preflight, evidence_text=EXTERNAL_ACTOR_EVIDENCE)
    decisions["decisions"]["S1"].update(
        {"verdict": "no", "support_ref_indexes": [], "role_ref_indexes": []}
    )
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="not affirmative"):
        validate_greenfield_source_duty_ledger(
            false_actor, evidence_text=EXTERNAL_ACTOR_EVIDENCE, decision_set=decisions
        )


def test_human_performer_reassignment_requires_source_verifier_refusal() -> None:
    ledger = _external_actor_ledger()
    ledger["first_path_actions"][0]["performer_role"] = "internal_system"
    preflight = preflight_greenfield_source_duty_ledger(
        ledger, evidence_text=EXTERNAL_ACTOR_EVIDENCE
    )
    assert preflight["claims"][0]["performer_role"] == "internal_system"
    task = source_duty_entailment_task(preflight, evidence_text=EXTERNAL_ACTOR_EVIDENCE)
    assert task["source_duty_ledger"]["result"]["first_path_actions"][0]["performer_role"] == "internal_system"
    decisions = _yes_decisions(preflight, evidence_text=EXTERNAL_ACTOR_EVIDENCE)
    decisions["decisions"]["A1"].update(
        {"verdict": "no", "support_ref_indexes": [], "role_ref_indexes": []}
    )
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="not affirmative"):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=EXTERNAL_ACTOR_EVIDENCE, decision_set=decisions
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda item: item["first_path_actions"][0].update({"unexpected": "x"}),
        lambda item: item["first_path_actions"][0].update({"action": "not present"}),
        lambda item: item["first_path_actions"][0].update({"role_refs": []}),
        lambda item: item["first_path_actions"][0].update({"statement": " "}),
        lambda item: item["first_path_actions"][0].update({"action": " "}),
        lambda item: item["first_path_actions"][0].update({"target": "submission"}),
        lambda item: item["first_path_actions"][0].update(
            {"actor_ref": _citation("portal")}
        ),
        lambda item: item["first_path_actions"].clear(),
        lambda item: item["supporting_human_actions"][0].update({"id": "A1"}),
    ],
)
def test_preflight_fails_closed_on_shape_or_citation_defects(mutate) -> None:
    ledger = _ledger()
    mutate(ledger)
    with pytest.raises(GreenfieldSourceDutyLedgerError):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)


def test_duplicate_action_atom_is_rejected_but_distinct_target_is_allowed() -> None:
    ledger = _ledger()
    ledger["supporting_human_actions"][0]["target"] = "scope"
    ledger["supporting_human_actions"][0][
        "statement"
    ] = "Another redundant reviewer statement defines scope"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="duplicated"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)


def test_reference_only_source_cannot_be_promoted_to_action_event() -> None:
    ledger = _ledger()
    row = ledger["system_duties"][0]
    row.update(
        {
            "source_refs": [_citation("Reference notes govern the template")],
            "event_ref": _citation("Reference notes govern the template"),
            "actor_ref": _citation("notes"),
            "statement": "notes govern the template",
            "action": "govern",
            "target": "the template",
        }
    )
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="reference-only"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    ledger = _ledger()
    row = ledger["system_duties"][0]
    row["actor_ref"] = _citation("notes")
    row["statement"] = "notes records the submission"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="reference-only"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)


def test_clarification_preflight_has_no_claims_and_cannot_admit() -> None:
    ledger = _ledger()
    ledger["status"] = "clarification_required"
    ledger["product_identity"] = None
    ledger["question"] = "Who approves scope?"
    for field, value in ledger.items():
        if isinstance(value, list):
            ledger[field] = []
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    assert preflight["claims"] == []
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="clarification cannot"):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=EVIDENCE, decision_set={}
        )


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (lambda item: item["decisions"].pop("A1"), "incomplete"),
        (
            lambda item: item["decisions"].update(
                {"unexpected": item["decisions"]["A1"]}
            ),
            "incomplete",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"verdict": "no"}),
            "not affirmative",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"verdict": "uncertain"}),
            "not affirmative",
        ),
        (
            lambda item: item["decisions"]["A1"].update(
                {"verdict": "no", "support_ref_indexes": [], "role_ref_indexes": []}
            ),
            "not affirmative",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"claim_sha256": "0" * 64}),
            "malformed",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"support_ref_indexes": [5]}),
            "support indexes",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"role_ref_indexes": []}),
            "role indexes",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"role_ref_indexes": [True]}),
            "role indexes",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"role_ref_indexes": [1]}),
            "omits actor",
        ),
        (
            lambda item: item["decisions"]["A1"].update({"role_ref_indexes": [0]}),
            "omits actor or role",
        ),
        (lambda item: item.update({"source_sha256": "0" * 64}), "malformed"),
        (lambda item: item.update({"verifier_task_sha256": "0" * 64}), "binding"),
        (lambda item: item.update({"version": "old"}), "binding"),
    ],
)
def test_semantic_admission_requires_complete_ordered_custodied_yes(
    mutate, expected
) -> None:
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    decisions = _yes_decisions(preflight)
    mutate(decisions)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match=expected):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=EVIDENCE, decision_set=decisions
        )


def test_receipt_rejects_changed_source_ledger_decision_or_hash() -> None:
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=EVIDENCE, decision_set=_yes_decisions(preflight)
    )
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="receipt hash"):
        verify_greenfield_source_duty_ledger_receipt(
            receipt, evidence_text=EVIDENCE.replace("audience", "listeners")
        )
    for field in (
        "ledger",
        "decision_set",
        "decision_set_sha256",
        "verifier_task_sha256",
    ):
        changed = deepcopy(receipt)
        if field == "ledger":
            changed[field]["first_path_actions"][0][
                "statement"
            ] = "reviewer approves scope"
        elif field == "decision_set":
            changed[field]["decisions"]["A1"]["verdict"] = "no"
        else:
            changed[field] = "0" * 64
        with pytest.raises(GreenfieldSourceDutyLedgerError):
            verify_greenfield_source_duty_ledger_receipt(
                changed, evidence_text=EVIDENCE
            )
    changed = deepcopy(receipt)
    changed["decision_set"]["source_completeness"] = {"verdict": "no", "omissions": []}
    with pytest.raises(GreenfieldSourceDutyLedgerError):
        verify_greenfield_source_duty_ledger_receipt(changed, evidence_text=EVIDENCE)


def test_key_order_does_not_change_workflow_or_receipt_custody() -> None:
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    decisions = _yes_decisions(preflight)
    expected = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=EVIDENCE, decision_set=decisions
    )
    decisions["decisions"] = dict(reversed(list(decisions["decisions"].items())))
    accepted = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=EVIDENCE, decision_set=decisions
    )
    assert accepted == expected
    assert list(accepted["decision_set"]["decisions"]) == ["A1", "H1", "S1"]
    assert [row["id"] for row in accepted["ledger"]["first_path_actions"]] == ["A1"]


def test_verifier_view_is_lossless_and_owns_one_copy_of_material_rows() -> None:
    from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import (
        expand_compact_source_duty_ledger,
    )

    evidence, ledger = _material_duty_case()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    task = source_duty_entailment_task(preflight, evidence_text=evidence)
    assert expand_compact_source_duty_ledger(task["source_duty_ledger"]) == ledger
    assert "claims" not in task and "evidence_controls" not in task
    assert "claim_sha256" not in json.dumps(task)
    assert task["authority_source"] == evidence
    keyed_schema = task["decision_set_schema"]["properties"]["decisions"]
    assert set(keyed_schema["required"]) == {
        claim["duty_id"] for claim in preflight["claims"]
    }
    assert keyed_schema["additionalProperties"] is False


def test_derived_fifth_reference_is_bounded_and_can_be_selected() -> None:
    ledger = _ledger()
    first = ledger["first_path_actions"][0]
    first["source_refs"] = [
        _citation("First Complete Path:"),
        _citation("defines"),
        _citation("scope"),
        _citation("audience"),
    ]
    first["role_refs"] = list(first["source_refs"])
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    assert len(preflight["claims"][0]["source_refs"]) == 5
    assert len(preflight["claims"][0]["role_refs"]) == 5
    validate_greenfield_source_duty_ledger(
        ledger, evidence_text=EVIDENCE, decision_set=_yes_decisions(preflight)
    )
    bad = _yes_decisions(preflight)
    bad["decisions"]["A1"]["role_ref_indexes"] = [0, 1, 2, 3, 4, 5]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="role indexes"):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=EVIDENCE, decision_set=bad
        )


def test_duplicate_json_keys_are_rejected_before_judgment_admission(tmp_path) -> None:
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
        load_greenfield_source_duty_file,
    )

    path = tmp_path / "decisions.json"
    path.write_text('{"decisions":{"A1":{"verdict":"no"},"A1":{"verdict":"yes"}}}')
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="duplicate object keys"):
        load_greenfield_source_duty_file(path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("action", "reviews"),
        ("target", "audience"),
        ("statement", "Another reviewer defines scope"),
    ],
)
def test_changed_normalized_meaning_invalidates_prior_task_hash(field, value) -> None:
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    old = _yes_decisions(preflight)
    changed = deepcopy(ledger)
    row = changed["first_path_actions"][0]
    row[field] = value
    if field == "action":
        row["statement"] = "reviewer reviews scope"
    elif field == "target":
        row["statement"] = "reviewer defines audience"
        changed["supporting_human_actions"] = []
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
        validate_greenfield_source_duty_ledger(
            changed, evidence_text=EVIDENCE, decision_set=old
        )


@pytest.mark.parametrize("mutation", ["missing_field", "wrong_object", "duplicate_identity"])
def test_state_field_relationships_fail_before_verifier(mutation) -> None:
    evidence, ledger = _material_duty_case()
    if mutation == "missing_field":
        ledger["off_path_transitions"][0]["effects"][0]["field"] = "access input"
    elif mutation == "wrong_object":
        ledger["off_path_transitions"][0]["governed_object"] = "another consent"
    else:
        field = deepcopy(ledger["state_fields"][0])
        field["id"] = "F4"
        ledger["state_fields"].append(field)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="state-field|identities"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)


def test_receipt_revalidation_rejects_changed_effect_identity() -> None:
    evidence, ledger = _material_duty_case()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence, decision_set=_yes_decisions(preflight, evidence_text=evidence),
    )
    receipt["ledger"]["off_path_transitions"][0]["effects"][0]["field"] = "missing access"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="no declared state-field identity"):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=evidence)


def test_fresh_system_kind_is_a_hash_bound_claim_in_the_same_source_only_task():
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    claims = {row["duty_id"]: row for row in preflight["claims"]}
    assert claims["H1"]["performer_role"] == "human_actor"
    assert claims["S1"]["performer_role"] == "internal_system"
    task = source_duty_entailment_task(preflight, evidence_text=EVIDENCE)
    assert "same exact canonical actor_ref source occurrence" in task["task"]
    changed = deepcopy(ledger)
    changed["system_duties"][0]["performer_role"] = "external_system"
    other = preflight_greenfield_source_duty_ledger(changed, evidence_text=EVIDENCE)
    assert other["claims"][2]["claim_sha256"] != claims["S1"]["claim_sha256"]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
        validate_greenfield_source_duty_ledger(changed, evidence_text=EVIDENCE, decision_set=_yes_decisions(preflight))


def test_aggregate_thirty_three_action_duties_refuse_before_candidate_authoring():
    ledger = _ledger()
    ledger["supporting_human_actions"] = []
    original = deepcopy(ledger["system_duties"][0])
    extras = [f"A portal retains item {index}" for index in range(1, 33)]
    evidence = EVIDENCE + " " + ". ".join(extras) + "."
    ledger["system_duties"] = [{
        **deepcopy(original), "id": f"system-{index}",
        "event_ref": _citation(event), "source_refs": [],
        "actor_ref": _citation("portal", "A portal records the submission"),
        "statement": f"portal retains item {index}", "action": "retains", "target": f"item {index}",
    } for index, event in enumerate(extras, 1)]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="existing event bound"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)


def test_exact_v5_receipt_task_and_hashes_remain_passive_and_refuse_fresh_use():
    ledger = _ledger()
    ledger["version"] = "odylith.greenfield.source-duty-ledger.v5"
    ledger.pop("product_identity")
    evidence = EVIDENCE.removeprefix("Review workspace. ")
    del ledger["system_duties"][0]["performer_role"]
    del ledger["system_duties"][0]["execution_kind"]
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence, _passive_source_version="odylith.greenfield.source-duty-ledger.v5")
    task = source_duty_entailment_task(preflight, evidence_text=evidence)
    # Frozen from the actual fe4a1eff runtime, not regenerated expected task text.
    assert task["verifier_task_sha256"] == "be6bd40552eace271454ddfb4c81ae5d2fa7f192b5706ff46ee893439a56b73b"
    assert preflight["ledger_sha256"] == "635cdbd8c5119476ae943e91ea4f38878a744e1f35c1b12cd621c754293d7693"
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence, decision_set=_yes_decisions(preflight, evidence_text=evidence), _passive_source_version="odylith.greenfield.source-duty-ledger.v5",
    )
    assert receipt["version"] == "odylith.greenfield.source-duty-ledger-receipt.v7"
    assert receipt["decision_set_sha256"] == "44f40ad2d1905da9445d4e9a0e3f29ba61953e809bb8f16adb4d59001a0c05d6"
    assert verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=evidence) == receipt
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="version"):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=evidence, allow_legacy_edit=False)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="invalid"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
