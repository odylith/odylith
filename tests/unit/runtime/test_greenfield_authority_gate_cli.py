"""The authority decision is source-bound before Greenfield can stage a package."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_VERSION,
    SOURCE_DUTY_LEDGER_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    SOURCE_DUTY_DECISION_SET_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import (
    expand_compact_source_duty_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
    DUTY_SECTIONS,
    compact_source_duty_view as _compact_ledger,
    duty_references,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    write_synthetic_source_duty_receipt,
)
from tests.unit.runtime.test_greenfield_source_duty_ledger import _material_duty_case


def _gate_file(path: Path, decision: dict[str, object]) -> Path:
    path.write_text(json.dumps(decision), encoding="utf-8")
    return path


def _clarify() -> dict[str, object]:
    return {
        "decision": "clarify",
        "required_fields": ["first_path"],
        "owner_quote": "",
        "task_quote": "",
        "result_quote": "",
        "question": "Who should use the product, what should they do, and what result should they see?",
    }


def _admit() -> dict[str, object]:
    return {
        "decision": "admit",
        "required_fields": [],
        "owner_quote": "A coordinator",
        "task_quote": "opens an intake request",
        "result_quote": "verifies a decision receipt",
        "question": "",
    }


def _yes_decisions(decision_task: dict[str, object]) -> dict[str, object]:
    ledger = expand_compact_source_duty_ledger(decision_task["source_duty_ledger"])
    decisions = {}
    for section, _ in DUTY_SECTIONS:
        for row in ledger[section]:
            support, role = duty_references(section, row)
            decisions[row["id"]] = {
                "verdict": "yes",
                "support_ref_indexes": list(range(len(support))),
                "role_ref_indexes": list(range(len(role))),
            }
    return {
        "version": SOURCE_DUTY_DECISION_SET_VERSION,
        "verifier_task_sha256": decision_task["verifier_task_sha256"],
        "source_completeness": {"verdict": "yes", "omissions": []},
        "decisions": decisions,
    }


def test_candidate_contract_exposes_one_pre_author_gate(tmp_path: Path, capsys) -> None:
    prompt = "Build a service workspace. A coordinator opens an intake request and verifies a decision receipt."

    rc = greenfield_proposals_cli.main(
        [
            "candidate-contract",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
        ]
    )

    assert rc == 0
    contract = json.loads(capsys.readouterr().out)
    gate = contract["authority_gate"]
    assert gate["operator_request"] == prompt
    assert gate["operator_edit"] == ""
    assert gate["response_schema"]["additionalProperties"] is False
    assert contract["candidate_schema"]
    ledger_task = contract["source_ledger"]["task"]
    assert (
        "Return exactly one compact JSON value matching source_ledger_schema"
        in ledger_task
    )
    assert "Do not call a CLI, read or write files" in ledger_task
    assert "external controller performs structural preflight" in ledger_task
    assert "source-ledger-check" not in ledger_task


def test_public_cli_routes_source_ledger_preflight_and_decision_file(
    tmp_path: Path,
    capsys,
) -> None:
    prompt, ledger = _material_duty_case()
    ledger_path = tmp_path / "source-ledger.json"
    ledger_path.write_text(json.dumps(_compact_ledger(ledger)), encoding="utf-8")
    argv = [
        "greenfield",
        "source-ledger-check",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        prompt,
        "--ledger-file",
        str(ledger_path),
        "--format",
        "json",
    ]

    assert cli.main(argv) == 0
    preflight = json.loads(capsys.readouterr().out)
    assert preflight["mode"] == "source_duty_preflight"
    assert (
        len(
            preflight["decision_task"]["decision_set_schema"]["properties"][
                "decisions"
            ]["required"]
        )
        == 10
    )

    decision_path = tmp_path / "source-decisions.json"
    decision_path.write_text(
        json.dumps(_yes_decisions(preflight["decision_task"])), encoding="utf-8"
    )
    assert cli.main([*argv, "--decision-file", str(decision_path)]) == 0
    admitted = json.loads(capsys.readouterr().out)
    assert admitted["mode"] == "source_duty_admitted"
    assert admitted["receipt"]["version"] == SOURCE_DUTY_LEDGER_RECEIPT_VERSION
    assert admitted["receipt"]["decision_set"]["source_completeness"] == {
        "verdict": "yes",
        "omissions": [],
    }


def test_authority_check_clarifies_without_a_candidate_or_staging(
    tmp_path: Path, capsys
) -> None:
    prompt = "Build an agriculture product. Source repository: plantFEM. Source evidence: This software simulates crops."
    gate = _gate_file(tmp_path / "gate.json", _clarify())

    rc = greenfield_proposals_cli.main(
        [
            "authority-check",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--gate-file",
            str(gate),
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "clarification_required"
    assert payload["clarification"]["required_fields"] == ["first_path"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_propose_clarifies_before_candidate_load_and_never_stages(
    tmp_path: Path, capsys
) -> None:
    prompt = "Build an agriculture product. Source repository: plantFEM. Source evidence: This software simulates crops."
    gate = _gate_file(tmp_path / "gate.json", _clarify())

    rc = greenfield_proposals_cli.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--gate-file",
            str(gate),
            "--ledger-file",
            str(tmp_path / "unused-ledger.json"),
            "--format",
            "json",
        ]
    )

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "clarification_required"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_admitted_gate_does_not_replace_the_host_candidate(
    tmp_path: Path, capsys
) -> None:
    prompt = "Build a service workspace. A coordinator opens an intake request and verifies a decision receipt."
    gate = _gate_file(tmp_path / "gate.json", _admit())
    ledger = write_synthetic_source_duty_receipt(
        tmp_path.parent / f"{tmp_path.name}-source-ledger.json",
        {"result": {"status": "clarification_required"}},
        evidence_text=combined_prompt_evidence_source(prompt=prompt, edit_evidence=""),
    )

    rc = greenfield_proposals_cli.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--gate-file",
            str(gate),
            "--ledger-file",
            str(ledger),
            "--format",
            "json",
        ]
    )

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "error"
    assert "host-authored candidate" in payload["error"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_forged_gate_witness_fails_before_candidate_load(
    tmp_path: Path, capsys
) -> None:
    prompt = "Build a service workspace. A coordinator opens an intake request and verifies a decision receipt."
    gate_data = _admit()
    gate_data["result_quote"] = "a fabricated result"
    gate = _gate_file(tmp_path / "gate.json", gate_data)

    rc = greenfield_proposals_cli.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--gate-file",
            str(gate),
            "--ledger-file",
            str(tmp_path / "unused-ledger.json"),
            "--format",
            "json",
        ]
    )

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "error"
    assert "result_quote" in payload["error"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_source_ledger_check_requires_source_only_decisions_before_receipt(
    tmp_path: Path, capsys
) -> None:
    prompt = "A coordinator opens an intake request and verifies a decision receipt."
    ledger = write_synthetic_source_duty_receipt(
        tmp_path.parent / f"{tmp_path.name}-source-ledger.json",
        {"result": {"status": "clarification_required"}},
        evidence_text=combined_prompt_evidence_source(prompt=prompt, edit_evidence=""),
    )
    raw_ledger = json.loads(ledger.read_text(encoding="utf-8"))["ledger"]
    ledger.write_text(json.dumps(_compact_ledger(raw_ledger)), encoding="utf-8")

    command = [
        "source-ledger-check",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        prompt,
        "--ledger-file",
        str(ledger),
        "--format",
        "json",
    ]
    rc = greenfield_proposals_cli.main(command)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "source_duty_preflight"
    preflight = payload["preflight"]
    assert preflight["ledger"] == raw_ledger
    assert (
        expand_compact_source_duty_ledger(
            payload["decision_task"]["source_duty_ledger"]
        )
        == preflight["ledger"]
    )
    assert "claims" not in payload["decision_task"]
    assert payload["decision_task"]["verifier_task_sha256"]
    assert payload["decision_task"][
        "authority_source"
    ] == combined_prompt_evidence_source(
        prompt=prompt,
        edit_evidence="",
    )
    assert (
        payload["decision_task"]["decision_set_schema"]["additionalProperties"] is False
    )
    decision_path = tmp_path.parent / f"{tmp_path.name}-source-decisions.json"
    decision_path.write_text(
        json.dumps(_yes_decisions(payload["decision_task"])), encoding="utf-8"
    )

    rc = greenfield_proposals_cli.main(
        [*command, "--decision-file", str(decision_path)]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "source_duty_admitted"
    assert payload["receipt"]["ledger"] == raw_ledger
    assert payload["receipt"]["source_sha256"]
    assert payload["receipt"]["ledger_sha256"]
    assert (
        payload["receipt"]["verifier_task_sha256"]
        == payload["receipt"]["decision_set"]["verifier_task_sha256"]
    )
    assert payload["receipt"]["decision_set_sha256"]
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


def test_source_ledger_check_decides_every_material_duty_section(
    tmp_path: Path,
    capsys,
) -> None:
    prompt, raw_ledger = _material_duty_case()
    ledger_path = tmp_path.parent / f"{tmp_path.name}-all-duties.json"
    ledger_path.write_text(json.dumps(_compact_ledger(raw_ledger)), encoding="utf-8")
    command = [
        "source-ledger-check",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        prompt,
        "--ledger-file",
        str(ledger_path),
        "--format",
        "json",
    ]
    assert greenfield_proposals_cli.main(command) == 0
    task = json.loads(capsys.readouterr().out)["decision_task"]
    assert len(task["decision_set_schema"]["properties"]["decisions"]["required"]) == 10
    assert {
        section for section, _ in DUTY_SECTIONS if task["source_duty_ledger"][section]
    } == {
        "first_path_actions",
        "supporting_human_actions",
        "system_duties",
        "state_fields",
        "off_path_transitions",
        "conditional_guards",
        "boundaries",
        "proof_duties",
    }
    decisions = _yes_decisions(task)
    decision_path = tmp_path.parent / f"{tmp_path.name}-all-decisions.json"
    decision_path.write_text(json.dumps(decisions), encoding="utf-8")
    assert (
        greenfield_proposals_cli.main([*command, "--decision-file", str(decision_path)])
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)["receipt"]
    assert len(receipt["decision_set"]["decisions"]) == 10
    assert receipt["verifier_task_sha256"] == task["verifier_task_sha256"]

    decisions["decisions"][raw_ledger["state_fields"][0]["id"]]["verdict"] = "no"
    decision_path.write_text(json.dumps(decisions), encoding="utf-8")
    assert (
        greenfield_proposals_cli.main([*command, "--decision-file", str(decision_path)])
        == 2
    )
    assert "not affirmative" in json.loads(capsys.readouterr().out)["error"]
    decisions["decisions"][raw_ledger["state_fields"][0]["id"]]["verdict"] = "yes"

    decisions["source_completeness"] = {
        "verdict": "no",
        "omissions": [
            {
                "omission_id": "missing-proof-duty",
                "typed_role": "proof_duty",
                "source_ref": raw_ledger["proof_duties"][0]["source_refs"][0],
            }
        ],
    }
    decision_path.write_text(json.dumps(decisions), encoding="utf-8")
    assert (
        greenfield_proposals_cli.main([*command, "--decision-file", str(decision_path)])
        == 2
    )
    assert (
        "source completeness is not affirmative"
        in json.loads(capsys.readouterr().out)["error"]
    )
    decisions["source_completeness"] = {"verdict": "yes", "omissions": []}

    decisions["verifier_task_sha256"] = "0" * 64
    decision_path.write_text(json.dumps(decisions), encoding="utf-8")
    assert (
        greenfield_proposals_cli.main([*command, "--decision-file", str(decision_path)])
        == 2
    )
    assert (
        "source duty decision binding is invalid"
        in json.loads(capsys.readouterr().out)["error"]
    )


def test_source_ledger_check_rejects_citation_bank_change_after_preflight(
    tmp_path: Path,
    capsys,
) -> None:
    prompt, raw_ledger = _material_duty_case()
    compact = _compact_ledger(raw_ledger)
    ledger_path = tmp_path.parent / f"{tmp_path.name}-citation-bank.json"
    ledger_path.write_text(json.dumps(compact), encoding="utf-8")
    command = [
        "source-ledger-check",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        prompt,
        "--ledger-file",
        str(ledger_path),
        "--format",
        "json",
    ]
    assert greenfield_proposals_cli.main(command) == 0
    task = json.loads(capsys.readouterr().out)["decision_task"]
    decision_path = tmp_path.parent / f"{tmp_path.name}-citation-bank-decisions.json"
    decision_path.write_text(json.dumps(_yes_decisions(task)), encoding="utf-8")

    citation = compact["citations"][0]
    assert citation["q"] in prompt
    assert citation["c"] != prompt
    citation["c"] = prompt
    ledger_path.write_text(json.dumps(compact), encoding="utf-8")

    assert (
        greenfield_proposals_cli.main([*command, "--decision-file", str(decision_path)])
        == 2
    )
    assert (
        "source duty decision binding is invalid"
        in json.loads(capsys.readouterr().out)["error"]
    )


def test_source_ledger_check_rejects_negative_decision_before_candidate(
    tmp_path: Path, capsys
) -> None:
    prompt = "A coordinator opens an intake request and verifies a decision receipt."
    ledger = write_synthetic_source_duty_receipt(
        tmp_path.parent / f"{tmp_path.name}-source-ledger.json",
        {"result": {"status": "clarification_required"}},
        evidence_text=combined_prompt_evidence_source(prompt=prompt, edit_evidence=""),
    )
    raw_ledger = json.loads(ledger.read_text(encoding="utf-8"))["ledger"]
    ledger.write_text(json.dumps(_compact_ledger(raw_ledger)), encoding="utf-8")
    command = [
        "source-ledger-check",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        prompt,
        "--ledger-file",
        str(ledger),
        "--format",
        "json",
    ]
    assert greenfield_proposals_cli.main(command) == 0
    decision_task = json.loads(capsys.readouterr().out)["decision_task"]
    decision_set = _yes_decisions(decision_task)
    decision_set["decisions"][raw_ledger["first_path_actions"][0]["id"]][
        "verdict"
    ] = "no"
    decision_path = tmp_path.parent / f"{tmp_path.name}-source-decisions.json"
    decision_path.write_text(json.dumps(decision_set), encoding="utf-8")

    rc = greenfield_proposals_cli.main(
        [*command, "--decision-file", str(decision_path)]
    )

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "error"
    assert "not affirmative" in payload["error"]
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("tamper_field", "tamper_value", "expected_error"),
    (
        ("decision_set_sha256", "0" * 64, "source duty ledger receipt hash is invalid"),
        (
            "version",
            "odylith.greenfield.source-duty-ledger-receipt.v5",
            "source duty ledger receipt version is invalid",
        ),
    ),
)
def test_propose_rejects_tampered_source_only_decision_receipt_before_candidate(
    tmp_path: Path,
    capsys,
    tamper_field: str,
    tamper_value: str,
    expected_error: str,
) -> None:
    prompt = "Build a service workspace. A coordinator opens an intake request and verifies a decision receipt."
    gate = _gate_file(tmp_path / "gate.json", _admit())
    ledger_path = write_synthetic_source_duty_receipt(
        tmp_path.parent / f"{tmp_path.name}-source-ledger.json",
        {"result": {"status": "clarification_required"}},
        evidence_text=combined_prompt_evidence_source(prompt=prompt, edit_evidence=""),
    )
    receipt = json.loads(ledger_path.read_text(encoding="utf-8"))
    receipt[tamper_field] = tamper_value
    ledger_path.write_text(json.dumps(receipt), encoding="utf-8")

    rc = greenfield_proposals_cli.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--gate-file",
            str(gate),
            "--ledger-file",
            str(ledger_path),
            "--format",
            "json",
        ]
    )

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "error"
    assert expected_error in payload["error"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_source_ledger_check_surfaces_one_material_question(
    tmp_path: Path, capsys
) -> None:
    prompt = "Source code simulates crop growth."
    ledger = {
        "version": SOURCE_DUTY_LEDGER_VERSION,
        "status": "clarification_required",
        "question": "Who uses this product and what result should they see?",
        "evidence_controls": [],
        "first_path_actions": [],
        "supporting_human_actions": [],
        "system_duties": [],
        "state_fields": [],
        "off_path_transitions": [],
        "conditional_guards": [],
        "boundaries": [],
        "proof_duties": [],
    }
    ledger_path = tmp_path.parent / f"{tmp_path.name}-source-ledger.json"
    ledger_path.write_text(json.dumps(_compact_ledger(ledger)), encoding="utf-8")

    rc = greenfield_proposals_cli.main(
        [
            "source-ledger-check",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--ledger-file",
            str(ledger_path),
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "mode": "clarification_required",
        "clarification": {"question": ledger["question"]},
    }
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


def test_source_ledger_check_rejects_malformed_inventory(
    tmp_path: Path, capsys
) -> None:
    prompt = "A coordinator opens an intake request and verifies a decision receipt."
    ledger_path = tmp_path.parent / f"{tmp_path.name}-source-ledger.json"
    ledger_path.write_text('{"status":"inventory"}', encoding="utf-8")

    rc = greenfield_proposals_cli.main(
        [
            "source-ledger-check",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--ledger-file",
            str(ledger_path),
            "--format",
            "json",
        ]
    )

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "error"
    assert "object fields are invalid" in payload["error"]
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


def test_source_ledger_cli_normalizes_only_source_valid_unused_citations(
    tmp_path, capsys
) -> None:
    prompt, ledger = _material_duty_case()
    prompt += " Opening outcome: receipt ready."
    compact = _compact_ledger(ledger)
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(compact))
    command = [
        "source-ledger-check",
        "--repo-root",
        str(tmp_path),
        "--prompt",
        prompt,
        "--ledger-file",
        str(path),
        "--format",
        "json",
    ]
    assert greenfield_proposals_cli.main(command) == 0
    baseline = json.loads(capsys.readouterr().out)
    compact["citations"].append(
        {
            "id": "unused-outcome",
            "q": "receipt ready",
            "c": "Opening outcome: receipt ready.",
        }
    )
    path.write_text(json.dumps(compact))
    assert greenfield_proposals_cli.main(command) == 0
    normalized = json.loads(capsys.readouterr().out)
    assert normalized == baseline
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(_yes_decisions(normalized["decision_task"])))
    assert (
        greenfield_proposals_cli.main(
            [*command, "--decision-file", str(decisions_path)]
        )
        == 0
    )
    admitted = json.loads(capsys.readouterr().out)
    assert admitted["mode"] == "source_duty_admitted"
    assert admitted["receipt"]["ledger"] == ledger
    assert (
        admitted["receipt"]["ledger_sha256"] == baseline["preflight"]["ledger_sha256"]
    )

    for quote, context in [
        ("fabricated outcome", "fabricated outcome"),
        ("receipt ready", "Opening outcome: receipt ready. Invented suffix"),
        ("receipt ready", "A reviewer defines scope and audience"),
    ]:
        compact["citations"][-1].update({"q": quote, "c": context})
        path.write_text(json.dumps(compact))
        assert (
            greenfield_proposals_cli.main(
                [*command, "--decision-file", str(decisions_path)]
            )
            == 2
        )
        failed = json.loads(capsys.readouterr().out)
        assert failed["mode"] == "error"
        assert "source citation is invalid" in failed["error"]
    assert sorted(file.name for file in tmp_path.iterdir()) == [
        "decisions.json",
        "ledger.json",
    ]
