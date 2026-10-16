"""Contract tests for the source-bound Greenfield pre-author gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_authority_gate import (
    GREENFIELD_AUTHORITY_GATE_CONTRACT_VERSION,
    MAX_GREENFIELD_AUTHORITY_GATE_FILE_BYTES,
    greenfield_authority_gate_contract,
    load_greenfield_authority_gate_file,
    validate_greenfield_authority_gate,
)


def _admit(owner: str, task: str, result: str) -> dict[str, object]:
    return {
        "decision": "admit",
        "required_fields": [],
        "owner_quote": owner,
        "task_quote": task,
        "result_quote": result,
        "question": "",
    }


def _clarify(question: str = "Who will do what, and what result should they see?") -> dict[str, object]:
    return {
        "decision": "clarify",
        "required_fields": ["first_path"],
        "owner_quote": "",
        "task_quote": "",
        "result_quote": "",
        "question": question,
    }


def test_direct_product_path_is_admissible_without_rewriting_quotes() -> None:
    prompt = "Build a planner where growers schedule irrigation and see a water-use report."
    contract = greenfield_authority_gate_contract(
        prompt=prompt, edit_evidence="", evidence_source=prompt
    )
    response = _admit("growers", "schedule irrigation", "see a water-use report")

    assert contract["version"] == GREENFIELD_AUTHORITY_GATE_CONTRACT_VERSION
    assert contract["operator_request"] == prompt
    assert contract["operator_edit"] == ""
    assert contract["response_schema"]["additionalProperties"] is False
    assert "source repository/software descriptions are supporting references" in contract["task"]
    assert validate_greenfield_authority_gate(response, evidence_source=prompt) == response


def test_edit_evidence_can_supply_exact_product_witnesses() -> None:
    prompt = "Build an agriculture product."
    edit = "The growers will log crop inspections and receive a weekly field-status summary."
    source = f"# Operator prompt evidence\n{prompt}\n# Operator edit evidence\n{edit}\n"
    contract = greenfield_authority_gate_contract(
        prompt=prompt, edit_evidence=edit, evidence_source=source
    )
    response = _admit("The growers", "log crop inspections", "receive a weekly field-status summary")

    assert contract["operator_edit"] == edit
    assert validate_greenfield_authority_gate(response, evidence_source=source) == response


def test_explicit_adoption_of_reference_role_can_supply_witnesses() -> None:
    prompt = (
        "Build an agriculture product. Source repository: example/simulator. "
        "Use its farmers as the product operators: farmers will run field simulations "
        "and see yield forecasts."
    )
    response = _admit("farmers", "run field simulations", "see yield forecasts")

    assert validate_greenfield_authority_gate(response, evidence_source=prompt) == response
    assert "unless the operator explicitly assigns them a role" in greenfield_authority_gate_contract(
        prompt=prompt, edit_evidence="", evidence_source=prompt
    )["task"]


def test_source_only_reference_requires_one_first_path_question() -> None:
    prompt = (
        "Build an agriculture product. Source repository: example/simulator. "
        "Source evidence: This simulator helps farmers run field simulations and see forecasts."
    )
    response = _clarify()

    assert validate_greenfield_authority_gate(response, evidence_source=prompt) == response
    assert "Do not infer a new product workflow from a reference capability" in (
        greenfield_authority_gate_contract(prompt=prompt, edit_evidence="", evidence_source=prompt)[
            "task"
        ]
    )


@pytest.mark.parametrize(
    "response",
    [
        {**_admit("growers", "schedule irrigation", "see report"), "extra": "x"},
        {**_admit("growers", "schedule irrigation", "see report"), "required_fields": ["first_path"]},
        {**_admit("growers", "schedule irrigation", "see report"), "question": "Why?"},
        {**_clarify(), "owner_quote": "growers"},
        {**_clarify(), "required_fields": ["product_boundary"]},
        {**_clarify(), "question": "   "},
    ],
)
def test_rejects_invalid_decision_shapes(response: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_greenfield_authority_gate(response, evidence_source="growers schedule irrigation see report")


def test_rejects_non_source_and_empty_witnesses() -> None:
    source = "Growers schedule irrigation and see a report."
    with pytest.raises(ValueError, match="owner_quote"):
        validate_greenfield_authority_gate(
            _admit("Farmers", "schedule irrigation", "see a report"), evidence_source=source
        )
    with pytest.raises(ValueError, match="task_quote"):
        validate_greenfield_authority_gate(
            _admit("Growers", " ", "see a report"), evidence_source=source
        )


def test_file_loader_accepts_bounded_json_and_rejects_invalid_input(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    response = _clarify()
    path.write_text(json.dumps(response), encoding="utf-8")
    assert load_greenfield_authority_gate_file(path) == response

    path.write_bytes(b"x" * (MAX_GREENFIELD_AUTHORITY_GATE_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="input bound"):
        load_greenfield_authority_gate_file(path)

    path.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="UTF-8 JSON"):
        load_greenfield_authority_gate_file(path)

    path.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="JSON object"):
        load_greenfield_authority_gate_file(path)
