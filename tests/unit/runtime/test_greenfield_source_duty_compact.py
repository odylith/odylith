from __future__ import annotations
from copy import deepcopy
import json
from jsonschema import Draft202012Validator, ValidationError
import pytest
from odylith.runtime.domain_intelligence.greenfield_source_duty_authoring import (
    SOURCE_DUTY_AUTHORING_VERSION,
    decode_source_duty_inventory,
    greenfield_source_duty_authoring_schema,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import SOURCE_DUTY_COMPACT_VERSION
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    greenfield_source_duty_ledger_schema,
    preflight_greenfield_source_duty_ledger,
)


def _compact() -> dict:
    return {
        "version": "odylith.greenfield.source-duty-compact.v7",
        "result": {
        "product_identity": {"basis": "product_description", "source_ref": "state"},
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
        },
    }


def _inline(ledger: dict | None = None) -> dict:
    result = deepcopy(decode_source_duty_inventory(_compact()) if ledger is None else ledger)
    result.pop("version")
    if ledger is None:
        result["nonperforming_participants"] = {field: [] for field in ("human_actors", "internal_systems", "external_systems")}
        result.update(source_precedence=[], first_run={"duty_ids": ["A1"]},
            terminal={"duty_id": "A1", "proof_boundary": deepcopy(result["first_path_actions"][0]["event_ref"]),
                      "result_fact": {"field": "first_path", "duty_id": "A1"},
                      "result_quote": "scope", "result_occurrence": 1})
    return {"version": SOURCE_DUTY_AUTHORING_VERSION, "result": result}


def test_schema_is_closed_and_expansion_preserves_citations_and_order() -> None:
    schema = greenfield_source_duty_authoring_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    expanded = decode_source_duty_inventory(_compact())
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
            lambda value: value["result"]["citations"].append(
                {"id": "event", "q": "other", "c": "other"}
            ),
            "IDs",
        ),
        (
            lambda value: value["result"]["citations"].append(
                {
                    "id": "other",
                    "q": "A reviewer defines scope",
                    "c": "A reviewer defines scope",
                }
            ),
            "pairs",
        ),
        (
            lambda value: value["result"]["first_path_actions"][0].__setitem__(
                "event_ref", "missing"
            ),
            "unknown",
        ),
        (
            lambda value: value["result"]["citations"].append(
                {"id": "unused", "q": "unused", "c": "unused"}
            ),
            "all be referenced",
        ),
        (
            lambda value: value["result"]["citations"][0].__setitem__("extra", "x"),
            "closed result branch",
        ),
    ],
)
def test_expansion_rejects_invalid_compact_references_and_shapes(
    mutate, match: str
) -> None:
    value = deepcopy(_compact())
    mutate(value)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match=match):
        decode_source_duty_inventory(value)


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
    expected = decode_source_duty_inventory(value, evidence_text=evidence)
    expected_preflight = preflight_greenfield_source_duty_ledger(
        expected, evidence_text=evidence, _passive_source_version="odylith.greenfield.source-duty-ledger.v9"
    )
    value["result"]["citations"].append(
        {
            "id": "unused-outcome",
            "q": "scope is visible",
            "c": "Opening outcome: scope is visible.",
        }
    )
    actual = decode_source_duty_inventory(value, evidence_text=evidence)
    assert actual == expected
    assert (
        preflight_greenfield_source_duty_ledger(actual, evidence_text=evidence, _passive_source_version="odylith.greenfield.source-duty-ledger.v9")
        == expected_preflight
    )
    assert value["result"]["citations"][-1]["id"] == "unused-outcome"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="all be referenced"):
        decode_source_duty_inventory(value)


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
    value["result"]["citations"].append({"id": "unused", "q": quote, "c": context})
    with pytest.raises(
        GreenfieldSourceDutyLedgerError, match="source citation is invalid"
    ):
        decode_source_duty_inventory(value, evidence_text=_source())


@pytest.mark.parametrize(
    "mutate,match",
    [
        (
            lambda value: value["result"]["citations"].append(
                {"id": "actor", "q": "scope is visible", "c": "scope is visible"}
            ),
            "IDs must be distinct",
        ),
        (
            lambda value: value["result"]["citations"].append(
                {
                    "id": "unused",
                    "q": "A reviewer defines scope",
                    "c": "A reviewer defines scope",
                }
            ),
            "pairs must be distinct",
        ),
        (
            lambda value: value["result"]["first_path_actions"][0].update(
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
        decode_source_duty_inventory(value, evidence_text=_source())


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
    compact["result"]["citations"].append(
        {
            "id": "unused-outcome",
            "q": "receipt ready",
            "c": "Opening outcome: receipt ready.",
        }
    )
    actual = decode_source_duty_inventory(compact, evidence_text=evidence)
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
    compact["result"]["off_path_transitions"] = [{
        "id": "T1", "source_refs": ["state"], "trigger": "withdrawal",
        "governed_object": "approval",
        "effects": [{"field": "status", "change": "revoked", "observable_check": "approval inactive"}],
    }]
    if mutation == "missing":
        compact["result"]["off_path_transitions"][0]["effects"][0]["field"] = "status inputs"
    else:
        duplicate = deepcopy(compact["result"]["state_fields"][0])
        duplicate["id"] = "F2"
        compact["result"]["state_fields"].append(duplicate)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="state-field|identities"):
        decode_source_duty_inventory(compact)


def test_fresh_schema_uses_ledger_citation_values_and_never_model_authored_aliases() -> None:
    schema = greenfield_source_duty_authoring_schema()
    Draft202012Validator.check_schema(schema)
    properties = schema["properties"]["result"]["anyOf"][0]["properties"]
    ledger = greenfield_source_duty_ledger_schema()["properties"]
    assert schema["properties"]["version"]["enum"] == [SOURCE_DUTY_AUTHORING_VERSION]
    assert "citations" not in properties
    for section in (
        "first_path_actions", "supporting_human_actions", "system_duties", "state_fields",
        "off_path_transitions", "conditional_guards", "boundaries", "proof_duties",
    ):
        assert properties[section] == ledger[section]
    assert properties["evidence_controls"] == ledger["evidence_controls"]
    assert properties["product_identity"] == ledger["product_identity"]["anyOf"][0]
    Draft202012Validator(schema).validate(_inline())
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(_compact())


def _complete_inline_case() -> tuple[str, dict]:
    from tests.unit.runtime.test_greenfield_source_duty_ledger import _material_duty_case
    source, ledger = _material_duty_case()
    ledger["state_fields"][0]["source_refs"].append(deepcopy(ledger["state_fields"][1]["source_refs"][0]))
    actor = deepcopy(ledger["first_path_actions"][0]["actor_ref"])
    ledger["supporting_human_actions"].append({
        "id": "H2", "source_refs": [], "statement": "reviewer checks a submission",
        "action": "checks", "target": "a submission", "actor_ref": actor,
        "event_ref": {"quote": "The reviewer checks a submission", "context": "The reviewer checks a submission"},
        "role_refs": [{"quote": "Human Actors:", "context": "Human Actors:"}],
    })
    assert source.count(actor["quote"]) > 1
    assert len(ledger["state_fields"][0]["source_refs"]) == 2
    return source, ledger


def test_inline_round_trip_preserves_complete_canonical_ledger_claims_and_compiler_view() -> None:
    from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view, DUTY_SECTIONS
    source, ledger = _complete_inline_case()
    wire = _inline(ledger)
    before = deepcopy(wire)
    actual = decode_source_duty_inventory(json.loads(json.dumps(wire)), evidence_text=source)
    assert actual == ledger
    assert all(actual[section] for section, _ in DUTY_SECTIONS)
    assert preflight_greenfield_source_duty_ledger(actual, evidence_text=source) == preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    assert compact_source_duty_view(actual) == compact_source_duty_view(ledger)
    assert compact_source_duty_view(actual)["version"] == SOURCE_DUTY_COMPACT_VERSION
    assert wire == before


@pytest.mark.parametrize("change", ["quote", "context", "alias"])
def test_inline_citations_keep_exact_ledger_validation(change: str) -> None:
    wire = _inline()
    citation = wire["result"]["state_fields"][0]["source_refs"][0]
    if change == "alias":
        wire["result"]["state_fields"][0]["source_refs"][0] = "c15 author's"
    else:
        citation[change] = "fabricated source"
    with pytest.raises(GreenfieldSourceDutyLedgerError):
        decode_source_duty_inventory(wire, evidence_text=_source())


def test_historical_compact_suffix_is_not_coerced_to_an_existing_id() -> None:
    value = _compact()
    value["result"]["citations"][-1]["id"] = "c15"
    value["result"]["product_identity"]["source_ref"] = "c15"
    value["result"]["state_fields"][0]["source_refs"] = ["c15", "c15 author's"]
    before = deepcopy(value)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="reference is unknown"):
        decode_source_duty_inventory(value, evidence_text=_source())
    assert value == before
