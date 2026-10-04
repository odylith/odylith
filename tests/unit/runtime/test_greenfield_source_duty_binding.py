from __future__ import annotations
from copy import deepcopy
import pytest
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    GreenfieldSourceDutyBindingError,
    SOURCE_DUTY_BINDING_VERSION,
    greenfield_source_duty_binding_schema,
    validate_greenfield_source_duty_binding,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_VERSION,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    synthetic_source_duty_receipt_for_ledger,
)


def _citation(quote: str, context: str | None = None) -> dict[str, str]:
    return {"quote": quote, "context": context or quote}


def _case(domain: str) -> tuple[str, dict, dict, dict]:
    evidence = f"A {domain} operator opens a record. A {domain} reviewer approves the record. A {domain} clerk prepares the record. A scheduler indexes the record. Withdrawal closes access and erases the cache."
    ledger = {
        "version": SOURCE_DUTY_LEDGER_VERSION,
        "status": "inventory",
        "question": "",
        "evidence_controls": [],
        "first_path_actions": [
            {
                "id": "A1",
                "source_refs": [_citation(f"{domain} operator opens a record")],
                "performer_role": "human_actor",
                "observable_result": "record opened",
                "event_ref": _citation(f"{domain} operator opens a record"),
                "actor_ref": _citation(f"{domain} operator"),
                "statement": f"{domain} operator opens a record",
                "role_refs": [_citation(f"{domain} operator opens a record")],
                "action": "opens",
                "target": "a record",
            },
            {
                "id": "A2",
                "source_refs": [_citation(f"{domain} reviewer approves the record")],
                "performer_role": "human_actor",
                "observable_result": "record approved",
                "event_ref": _citation(f"{domain} reviewer approves the record"),
                "actor_ref": _citation(f"{domain} reviewer"),
                "statement": f"{domain} reviewer approves the record",
                "role_refs": [_citation(f"{domain} reviewer approves the record")],
                "action": "approves",
                "target": "the record",
            },
        ],
        "supporting_human_actions": [
            {
                "id": "H1",
                "source_refs": [_citation(f"{domain} clerk prepares the record")],
                "event_ref": _citation(f"{domain} clerk prepares the record"),
                "actor_ref": _citation(f"{domain} clerk"),
                "statement": f"{domain} clerk prepares the record",
                "role_refs": [_citation(f"{domain} clerk prepares the record")],
                "action": "prepares",
                "target": "the record",
            }
        ],
        "system_duties": [
            {
                "id": "S1",
                "source_refs": [_citation("scheduler indexes the record")],
                "event_ref": _citation("scheduler indexes the record"),
                "actor_ref": _citation("scheduler"),
                "statement": "scheduler indexes the record",
                "role_refs": [_citation("scheduler indexes the record")],
                "action": "indexes",
                "target": "the record",
            }
        ],
        "state_fields": [
            {
                "id": "F1",
                "source_refs": [_citation("closes access")],
                "state_object": "record",
                "field": "access",
                "meaning": "access status",
            },
            {
                "id": "F2",
                "source_refs": [_citation("erases the cache")],
                "state_object": "record",
                "field": "cache",
                "meaning": "cached copy",
            },
        ],
        "off_path_transitions": [
            {
                "id": "T1",
                "source_refs": [
                    _citation("Withdrawal closes access and erases the cache")
                ],
                "trigger": "withdrawal",
                "governed_object": "record",
                "effects": [
                    {
                        "field": "access",
                        "change": "closed",
                        "observable_check": "closed status",
                    },
                    {
                        "field": "cache",
                        "change": "erased",
                        "observable_check": "empty cache",
                    },
                ],
            }
        ],
        "conditional_guards": [],
        "boundaries": [],
        "proof_duties": [],
    }
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence)
    candidate = {
        "status": "authored",
        "events": [
            {"actor_fact": {"field": "internal_systems", "row": 1}},
            {"actor_fact": {"field": "human_actors", "row": 1}},
            {"actor_fact": {"field": "human_actors", "row": 2}},
            {"actor_fact": {"field": "human_actors", "row": 3}},
        ],
        "facts": {
            "internal_systems": [_citation("scheduler")],
            "human_actors": [
                _citation(f"{domain} operator"),
                _citation(f"{domain} reviewer"),
                _citation(f"{domain} clerk"),
            ],
        },
        "terminal": {"event_order": 3},
        "provisional_design": {
            "first_run": {"event_orders": [2, 3], "rationale": "operator to reviewer"},
            "components": [{"key": "record-store"}],
            "workstreams": [
                {"key": "record-delivery", "component_keys": ["record-store"]}
            ],
        },
    }
    binding = {
        "version": SOURCE_DUTY_BINDING_VERSION,
        "source_sha256": receipt["source_sha256"],
        "ledger_sha256": receipt["ledger_sha256"],
        "first_path_actions": [
            {"duty_id": "A1", "event_order": 2},
            {"duty_id": "A2", "event_order": 3},
        ],
        "supporting_human_actions": [{"duty_id": "H1", "event_order": 4}],
        "system_duties": [{"duty_id": "S1", "event_order": 1}],
        "off_path_transitions": [
            {
                "duty_id": "T1",
                "component_key": "record-store",
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
    return (evidence, receipt, candidate, binding)


def _with_design_duties(
    evidence: str, receipt: dict, binding: dict
) -> tuple[str, dict, dict]:
    evidence += " Before approval, consent must be active. Only stewards may approve. Audit dossier must show the approval decision."
    ledger = deepcopy(receipt["ledger"])
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
            "source_refs": [_citation("Only stewards may approve")],
            "kind": "authority",
            "rule": "Only stewards may approve",
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
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence)
    binding["source_sha256"] = receipt["source_sha256"]
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    for role, duty_id in (
        ("conditional_guards", "G1"),
        ("boundaries", "B1"),
        ("proof_duties", "P1"),
    ):
        binding[role] = [
            {
                "duty_id": duty_id,
                "component_key": "record-store",
                "workstream_key": "record-delivery",
            }
        ]
    return (evidence, receipt, binding)


@pytest.mark.parametrize("domain", ("harbor", "orchard"))
def test_binding_covers_first_path_and_off_path_in_distinct_domains(
    domain: str,
) -> None:
    evidence, receipt, candidate, binding = _case(domain)
    assert (
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )
        == binding
    )
    assert set(greenfield_source_duty_binding_schema()["required"]) == set(binding)


def test_first_run_rejects_supporting_or_system_event_pollution() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["provisional_design"]["first_run"]["event_orders"] = [1, 2, 3]
    with pytest.raises(GreenfieldSourceDutyBindingError, match="first run"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_first_run_cannot_reverse_admitted_binding_order() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["provisional_design"]["first_run"]["event_orders"] = [3, 2]
    with pytest.raises(GreenfieldSourceDutyBindingError, match="ledger workflow order"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


@pytest.mark.parametrize("orders", ([2], [2, 3, 4], [2, 2, 3]))
def test_first_run_rejects_missing_extra_or_duplicate_bound_event(
    orders: list[int],
) -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["provisional_design"]["first_run"]["event_orders"] = orders
    with pytest.raises(GreenfieldSourceDutyBindingError, match="exactly once"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_binding_rejects_candidate_event_without_a_source_duty_role() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["events"].append({"actor_fact": {"field": "human_actors", "row": 4}})
    with pytest.raises(GreenfieldSourceDutyBindingError, match="exactly one"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_binding_rejects_one_event_assigned_to_two_roles() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    event = _citation("harbor operator opens a record")
    receipt["ledger"]["supporting_human_actions"][0].update(
        {
            "source_refs": [event],
            "event_ref": event,
            "actor_ref": _citation("harbor operator"),
            "statement": "harbor operator opens",
            "role_refs": [event],
            "action": "opens",
            "target": "",
        }
    )
    receipt = synthetic_source_duty_receipt_for_ledger(
        receipt["ledger"], evidence_text=evidence
    )
    binding["source_sha256"] = receipt["source_sha256"]
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    binding["supporting_human_actions"][0]["event_order"] = 2
    with pytest.raises(GreenfieldSourceDutyBindingError, match="exactly one"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


@pytest.mark.parametrize(
    ("role", "order", "field"),
    (
        ("supporting_human_actions", 4, "internal_systems"),
        ("system_duties", 1, "human_actors"),
    ),
)
def test_binding_rejects_incompatible_actor_fact_role(
    role: str, order: int, field: str
) -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["events"][order - 1]["actor_fact"]["field"] = field
    with pytest.raises(
        GreenfieldSourceDutyBindingError, match="incompatible event actor"
    ):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_first_path_rejects_human_duty_reassigned_to_system_fact_with_same_citation() -> (
    None
):
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["facts"]["internal_systems"].append(
        deepcopy(candidate["facts"]["human_actors"][0])
    )
    candidate["events"][1]["actor_fact"] = {"field": "internal_systems", "row": 2}
    with pytest.raises(
        GreenfieldSourceDutyBindingError, match="incompatible event actor"
    ):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_first_path_accepts_explicit_typed_system_performer() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    system = receipt["ledger"]["system_duties"].pop()
    receipt["ledger"]["first_path_actions"].append(
        {
            "id": system["id"],
            "source_refs": system["source_refs"],
            "performer_role": "internal_system",
            "observable_result": "record indexed",
            "event_ref": system["event_ref"],
            "actor_ref": system["actor_ref"],
            "statement": system["statement"],
            "role_refs": system["role_refs"],
            "action": system["action"],
            "target": system["target"],
        }
    )
    receipt = synthetic_source_duty_receipt_for_ledger(
        receipt["ledger"], evidence_text=evidence
    )
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    system_binding = binding["system_duties"].pop()
    candidate["events"].insert(2, candidate["events"].pop(0))
    binding["first_path_actions"][0]["event_order"] = 1
    binding["first_path_actions"][1]["event_order"] = 2
    system_binding["event_order"] = 3
    binding["first_path_actions"].append(system_binding)
    candidate["provisional_design"]["first_run"]["event_orders"] = [1, 2, 3]
    assert (
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )
        == binding
    )


def test_two_action_duties_cannot_collapse_into_one_event() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    evidence = evidence.replace(
        "scheduler indexes the record", "scheduler indexes and audits the record"
    )
    event = _citation("scheduler indexes and audits the record")
    receipt["ledger"]["system_duties"][0].update(
        {
            "source_refs": [event],
            "event_ref": event,
            "action": "indexes",
            "target": "the record",
            "statement": "scheduler indexes the record",
            "role_refs": [event],
        }
    )
    receipt["ledger"]["system_duties"].append(
        {
            "id": "S2",
            "source_refs": [event],
            "event_ref": event,
            "actor_ref": _citation("scheduler"),
            "statement": "scheduler audits the record",
            "role_refs": [event],
            "action": "audits",
            "target": "the record",
        }
    )
    receipt = synthetic_source_duty_receipt_for_ledger(
        receipt["ledger"], evidence_text=evidence
    )
    binding["source_sha256"] = receipt["source_sha256"]
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    binding["system_duties"].append({"duty_id": "S2", "event_order": 1})
    with pytest.raises(GreenfieldSourceDutyBindingError, match="distinct events"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_first_run_rejects_boolean_event_identity() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["provisional_design"]["first_run"]["event_orders"] = [True, 3]
    with pytest.raises(GreenfieldSourceDutyBindingError, match="first run"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_binding_rejects_actor_disjoint_event_even_when_identity_exists() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    binding["first_path_actions"][0]["event_order"] = 3
    with pytest.raises(GreenfieldSourceDutyBindingError, match="actor differs"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda b, c: b["first_path_actions"].pop(), "first_path_actions"),
        (
            lambda b, c: b["first_path_actions"].append(
                {"duty_id": "A3", "event_order": 2}
            ),
            "first_path_actions",
        ),
        (
            lambda b, c: b["first_path_actions"][0].update({"duty_id": "A2"}),
            "source order",
        ),
        (
            lambda b, c: b["first_path_actions"][0].update({"event_order": 5}),
            "unknown event",
        ),
        (
            lambda b, c: b["supporting_human_actions"].clear(),
            "supporting_human_actions",
        ),
        (lambda b, c: b["system_duties"].clear(), "system_duties"),
        (lambda b, c: b["off_path_transitions"].clear(), "off_path_transitions"),
        (
            lambda b, c: b["off_path_transitions"][0].update({"duty_id": "T2"}),
            "source order",
        ),
        (
            lambda b, c: b["off_path_transitions"][0]["effects"].pop(),
            "off-path effects",
        ),
        (
            lambda b, c: b["off_path_transitions"][0]["effects"][0].update(
                {"state_field_id": "F9"}
            ),
            "unknown state field",
        ),
        (
            lambda b, c: b["off_path_transitions"][0].update(
                {"workstream_key": "missing"}
            ),
            "unknown design owner",
        ),
        (
            lambda b, c: c["provisional_design"]["workstreams"][0].update(
                {"component_keys": []}
            ),
            "does not own",
        ),
    ),
)
def test_binding_rejects_missing_extra_or_wrong_references(
    mutation, message: str
) -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    mutation(binding, candidate)
    with pytest.raises(GreenfieldSourceDutyBindingError, match=message):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_binding_rejects_wrong_digest_or_changed_source() -> None:
    evidence, receipt, candidate, binding = _case("orchard")
    binding["ledger_sha256"] = "0" * 64
    with pytest.raises(GreenfieldSourceDutyBindingError, match="digest mismatch"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    with pytest.raises(GreenfieldSourceDutyBindingError, match="receipt is invalid"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence.replace("orchard", "harbor"),
        )


def test_binding_detaches_validated_result_and_rejects_extra_fields() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    accepted = validate_greenfield_source_duty_binding(
        binding,
        ledger_receipt=receipt,
        candidate_result=candidate,
        evidence_text=evidence,
    )
    binding["first_path_actions"].clear()
    assert len(accepted["first_path_actions"]) == 2
    changed = deepcopy(accepted)
    changed["new_role"] = "ignored"
    with pytest.raises(GreenfieldSourceDutyBindingError, match="invalid fields"):
        validate_greenfield_source_duty_binding(
            changed,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_v1_binding_requires_regeneration_for_exhaustive_role_coverage() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    binding["version"] = "odylith.greenfield.source-duty-binding.v1"
    with pytest.raises(GreenfieldSourceDutyBindingError, match="version is invalid"):
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )


def test_guard_boundary_and_proof_duty_require_source_ordered_design_bindings() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    evidence, receipt, binding = _with_design_duties(evidence, receipt, binding)
    assert (
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )
        == binding
    )
    for role in ("conditional_guards", "boundaries", "proof_duties"):
        missing = deepcopy(binding)
        missing[role].clear()
        with pytest.raises(GreenfieldSourceDutyBindingError, match=role):
            validate_greenfield_source_duty_binding(
                missing,
                ledger_receipt=receipt,
                candidate_result=candidate,
                evidence_text=evidence,
            )
        stale = deepcopy(binding)
        stale[role][0]["duty_id"] = "stale-duty"
        with pytest.raises(GreenfieldSourceDutyBindingError, match="source order"):
            validate_greenfield_source_duty_binding(
                stale,
                ledger_receipt=receipt,
                candidate_result=candidate,
                evidence_text=evidence,
            )
        unrelated = deepcopy(binding)
        unrelated[role][0]["component_key"] = "unrelated"
        with pytest.raises(
            GreenfieldSourceDutyBindingError, match="unknown design owner"
        ):
            validate_greenfield_source_duty_binding(
                unrelated,
                ledger_receipt=receipt,
                candidate_result=candidate,
                evidence_text=evidence,
            )


def test_first_path_binding_accepts_coordinated_citation_slot_renumbering() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    original_receipt = deepcopy(receipt)
    candidate["events"][1], candidate["events"][2] = (
        candidate["events"][2],
        candidate["events"][1],
    )
    binding["first_path_actions"][0]["event_order"] = 3
    binding["first_path_actions"][1]["event_order"] = 2
    candidate["provisional_design"]["first_run"]["event_orders"] = [3, 2]
    assert (
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )
        == binding
    )
    assert receipt == original_receipt


def test_supporting_events_can_interleave_source_workflow() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    candidate["events"][2], candidate["events"][3] = (
        candidate["events"][3],
        candidate["events"][2],
    )
    binding["first_path_actions"][1]["event_order"] = 4
    binding["supporting_human_actions"][0]["event_order"] = 3
    candidate["provisional_design"]["first_run"]["event_orders"] = [2, 4]
    candidate["terminal"]["event_order"] = 4
    assert (
        validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate,
            evidence_text=evidence,
        )
        == binding
    )


def test_complete_host_admission_rejects_first_run_only_reordering() -> None:
    from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
        admit_greenfield_host_candidate,
    )
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    from tests.unit.runtime.greenfield_model_authoring_fixtures import (
        synthetic_source_duty_receipt,
    )

    source, candidate = _candidate()
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    original_receipt = deepcopy(receipt)
    first_run = candidate["result"]["provisional_design"]["first_run"]["event_orders"]
    first_run[0], first_run[1] = first_run[1], first_run[0]
    with pytest.raises(GreenfieldSourceDutyBindingError, match="ledger workflow order"):
        admit_greenfield_host_candidate(
            candidate, evidence_text=source, source_duty_receipt=receipt
        )
    assert receipt == original_receipt


def test_complete_host_admission_accepts_coordinated_citation_slot_renumbering() -> (
    None
):
    from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
        admit_greenfield_host_candidate,
    )
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    from tests.unit.runtime.greenfield_model_authoring_fixtures import (
        synthetic_source_duty_receipt,
    )

    source, candidate = _candidate()
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    original_receipt = deepcopy(receipt)
    baseline, _ = admit_greenfield_host_candidate(
        candidate, evidence_text=source, source_duty_receipt=receipt
    )
    result = candidate["result"]
    bindings = result["source_duty_binding"]["first_path_actions"]
    left, right = bindings[0]["event_order"], bindings[1]["event_order"]
    result["events"][left - 1], result["events"][right - 1] = (
        result["events"][right - 1],
        result["events"][left - 1],
    )
    bindings[0]["event_order"], bindings[1]["event_order"] = right, left
    first_run = result["provisional_design"]["first_run"]["event_orders"]
    first_run[0], first_run[1] = first_run[1], first_run[0]
    # Every slot reference follows the same identity renumbering; duty order stays fixed.
    for relation in result["source_precedence"]:
        for key in ("before_event", "after_event"):
            if relation[key] in (left, right):
                relation[key] = right if relation[key] == left else left
    terminal = result["terminal"]
    if terminal["event_order"] in (left, right):
        terminal["event_order"] = right if terminal["event_order"] == left else left
    authored, _ = admit_greenfield_host_candidate(
        candidate, evidence_text=source, source_duty_receipt=receipt
    )

    def workflow(admitted):
        relations = {row["order"]: row for row in admitted.first_path_relations}
        return [
            (relations[order]["actor_fact_quote"], relations[order]["event_quote"])
            for order in admitted.provisional_design["first_run"]["event_orders"]
        ]

    assert workflow(authored) == workflow(baseline)
    assert receipt == original_receipt


def test_same_field_label_on_different_objects_resolves_exact_declared_identity() -> None:
    evidence, receipt, candidate, binding = _case("harbor")
    evidence += " Another record access indicates availability."
    ledger = deepcopy(receipt["ledger"])
    another = deepcopy(ledger["state_fields"][0])
    another.update({"id": "F3", "state_object": "another record",
                    "source_refs": [_citation("Another record access indicates availability")]})
    ledger["state_fields"].append(another)
    from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt_for_ledger
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence)
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    binding["source_sha256"] = receipt["source_sha256"]
    assert validate_greenfield_source_duty_binding(
        binding, ledger_receipt=receipt, candidate_result=candidate, evidence_text=evidence,
    ) == binding
    binding["off_path_transitions"][0]["effects"][0]["state_field_id"] = "F3"
    with pytest.raises(GreenfieldSourceDutyBindingError, match="different state field"):
        validate_greenfield_source_duty_binding(
            binding, ledger_receipt=receipt, candidate_result=candidate, evidence_text=evidence,
        )
