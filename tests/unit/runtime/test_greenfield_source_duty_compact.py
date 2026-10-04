from __future__ import annotations
from copy import deepcopy
import pytest
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import (
    SOURCE_DUTY_COMPACT_VERSION,
    expand_compact_source_duty_ledger,
    greenfield_compact_source_duty_ledger_schema,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
)


def _compact() -> dict:
    return {
        "version": SOURCE_DUTY_COMPACT_VERSION,
        "status": "inventory",
        "question": "",
        "citations": [
            {
                "id": "event",
                "q": "A reviewer defines scope",
                "c": "A reviewer defines scope",
            },
            {"id": "actor", "q": "reviewer", "c": "A reviewer defines scope"},
            {"id": "role", "q": "First Complete Path:", "c": "First Complete Path:"},
            {"id": "control", "q": "Reference notes", "c": "Reference notes"},
            {
                "id": "state",
                "q": "Status records approval",
                "c": "Status records approval",
            },
        ],
        "evidence_controls": [{"ref": "control", "handling": "reference_context"}],
        "first_path_actions": [
            {
                "id": "A1",
                "source_refs": ["event"],
                "performer_role": "human_actor",
                "observable_result": "scope defined",
                "statement": "reviewer defines scope",
                "event_ref": "event",
                "actor_ref": "actor",
                "role_refs": ["role"],
                "action": "defines",
                "target": "scope",
            }
        ],
        "supporting_human_actions": [],
        "system_duties": [],
        "state_fields": [
            {
                "id": "F1",
                "source_refs": ["state"],
                "state_object": "approval",
                "field": "status",
                "meaning": "approval status",
            }
        ],
        "off_path_transitions": [],
        "conditional_guards": [],
        "boundaries": [],
        "proof_duties": [],
    }


def test_schema_is_closed_and_expansion_preserves_citations_and_order() -> None:
    schema = greenfield_compact_source_duty_ledger_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    expanded = expand_compact_source_duty_ledger(_compact())
    assert expanded["first_path_actions"][0]["event_ref"] == {
        "quote": "A reviewer defines scope",
        "context": "A reviewer defines scope",
    }
    assert expanded["evidence_controls"] == [
        {
            "quote": "Reference notes",
            "context": "Reference notes",
            "handling": "reference_context",
        }
    ]
    assert [row["id"] for row in expanded["first_path_actions"]] == ["A1"]
    assert expanded["state_fields"][0]["source_refs"] == [
        {"quote": "Status records approval", "context": "Status records approval"}
    ]


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda value: value["citations"].append(
                {"id": "event", "q": "other", "c": "other"}
            ),
            "IDs",
        ),
        (
            lambda value: value["citations"].append(
                {
                    "id": "other",
                    "q": "A reviewer defines scope",
                    "c": "A reviewer defines scope",
                }
            ),
            "pairs",
        ),
        (
            lambda value: value["first_path_actions"][0].__setitem__(
                "event_ref", "missing"
            ),
            "unknown",
        ),
        (
            lambda value: value["citations"].append(
                {"id": "unused", "q": "unused", "c": "unused"}
            ),
            "all be referenced",
        ),
        (
            lambda value: value["citations"][0].__setitem__("extra", "x"),
            "object fields",
        ),
    ],
)
def test_expansion_rejects_invalid_compact_references_and_shapes(
    mutate, match: str
) -> None:
    value = deepcopy(_compact())
    mutate(value)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match=match):
        expand_compact_source_duty_ledger(value)


def _source() -> str:
    return "First Complete Path: A reviewer defines scope. Status records approval. Reference notes. Opening outcome: scope is visible."


def test_source_checked_unused_bank_storage_does_not_change_any_material_row_or_hash() -> (
    None
):
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
        preflight_greenfield_source_duty_ledger,
    )

    value = _compact()
    evidence = _source()
    expected = expand_compact_source_duty_ledger(value, evidence_text=evidence)
    expected_preflight = preflight_greenfield_source_duty_ledger(
        expected, evidence_text=evidence
    )
    value["citations"].append(
        {
            "id": "unused-outcome",
            "q": "scope is visible",
            "c": "Opening outcome: scope is visible.",
        }
    )
    actual = expand_compact_source_duty_ledger(value, evidence_text=evidence)
    assert actual == expected
    assert (
        preflight_greenfield_source_duty_ledger(actual, evidence_text=evidence)
        == expected_preflight
    )
    assert value["citations"][-1]["id"] == "unused-outcome"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="all be referenced"):
        expand_compact_source_duty_ledger(value)


@pytest.mark.parametrize(
    "quote,context",
    [
        ("fabricated outcome", "fabricated outcome"),
        ("scope is visible", "First Complete Path: A reviewer defines scope."),
        ("scope is visible", "Opening outcome: scope is visible. Invented suffix"),
    ],
)
def test_unused_invalid_bank_citations_fail_exact_source_checks(quote, context) -> None:
    value = _compact()
    value["citations"].append({"id": "unused", "q": quote, "c": context})
    with pytest.raises(
        GreenfieldSourceDutyLedgerError, match="source citation is invalid"
    ):
        expand_compact_source_duty_ledger(value, evidence_text=_source())


@pytest.mark.parametrize(
    "mutate,match",
    [
        (
            lambda value: value["citations"].append(
                {"id": "actor", "q": "scope is visible", "c": "scope is visible"}
            ),
            "IDs must be distinct",
        ),
        (
            lambda value: value["citations"].append(
                {
                    "id": "unused",
                    "q": "A reviewer defines scope",
                    "c": "A reviewer defines scope",
                }
            ),
            "pairs must be distinct",
        ),
        (
            lambda value: value["first_path_actions"][0].update(
                {"event_ref": "unknown"}
            ),
            "reference is unknown",
        ),
    ],
)
def test_source_checked_normalization_keeps_reference_integrity_checks(
    mutate, match
) -> None:
    value = _compact()
    mutate(value)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match=match):
        expand_compact_source_duty_ledger(value, evidence_text=_source())


def test_unused_bank_normalization_preserves_all_eight_sections_and_claim_custody() -> (
    None
):
    from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
        compact_source_duty_view,
        DUTY_SECTIONS,
    )
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
        preflight_greenfield_source_duty_ledger,
    )
    from tests.unit.runtime.test_greenfield_source_duty_ledger import (
        _material_duty_case,
    )

    evidence, ledger = _material_duty_case()
    evidence += " Opening outcome: receipt ready."
    compact = compact_source_duty_view(ledger)
    compact["citations"].append(
        {
            "id": "unused-outcome",
            "q": "receipt ready",
            "c": "Opening outcome: receipt ready.",
        }
    )
    actual = expand_compact_source_duty_ledger(compact, evidence_text=evidence)
    assert all(actual[section] == ledger[section] for section, _ in DUTY_SECTIONS)
    expected = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    admitted_shape = preflight_greenfield_source_duty_ledger(
        actual, evidence_text=evidence
    )
    assert admitted_shape["ledger_sha256"] == expected["ledger_sha256"]
    assert admitted_shape["claims"] == expected["claims"]


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_compact_expansion_enforces_canonical_state_field_relationships(mutation) -> None:
    compact = _compact()
    compact["off_path_transitions"] = [{
        "id": "T1", "source_refs": ["state"], "trigger": "withdrawal",
        "governed_object": "approval",
        "effects": [{"field": "status", "change": "revoked", "observable_check": "approval inactive"}],
    }]
    if mutation == "missing":
        compact["off_path_transitions"][0]["effects"][0]["field"] = "status inputs"
    else:
        duplicate = deepcopy(compact["state_fields"][0])
        duplicate["id"] = "F2"
        compact["state_fields"].append(duplicate)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="state-field|identities"):
        expand_compact_source_duty_ledger(compact)
