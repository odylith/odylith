"""The authority decision is source-bound before Greenfield can stage a package."""

from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals_cli


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


def test_candidate_contract_exposes_one_pre_author_gate(tmp_path: Path, capsys) -> None:
    prompt = "Build a service workspace. A coordinator opens an intake request and verifies a decision receipt."

    rc = greenfield_proposals_cli.main([
        "candidate-contract", "--repo-root", str(tmp_path), "--prompt", prompt,
    ])

    assert rc == 0
    contract = json.loads(capsys.readouterr().out)
    gate = contract["authority_gate"]
    assert gate["operator_request"] == prompt
    assert gate["operator_edit"] == ""
    assert gate["response_schema"]["additionalProperties"] is False
    assert contract["candidate_schema"]


def test_authority_check_clarifies_without_a_candidate_or_staging(tmp_path: Path, capsys) -> None:
    prompt = "Build an agriculture product. Source repository: plantFEM. Source evidence: This software simulates crops."
    gate = _gate_file(tmp_path / "gate.json", _clarify())

    rc = greenfield_proposals_cli.main([
        "authority-check", "--repo-root", str(tmp_path), "--prompt", prompt,
        "--gate-file", str(gate), "--format", "json",
    ])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "clarification_required"
    assert payload["clarification"]["required_fields"] == ["first_path"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_propose_clarifies_before_candidate_load_and_never_stages(tmp_path: Path, capsys) -> None:
    prompt = "Build an agriculture product. Source repository: plantFEM. Source evidence: This software simulates crops."
    gate = _gate_file(tmp_path / "gate.json", _clarify())

    rc = greenfield_proposals_cli.main([
        "propose", "--repo-root", str(tmp_path), "--prompt", prompt,
        "--gate-file", str(gate), "--format", "json",
    ])

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "clarification_required"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_admitted_gate_does_not_replace_the_host_candidate(tmp_path: Path, capsys) -> None:
    prompt = "Build a service workspace. A coordinator opens an intake request and verifies a decision receipt."
    gate = _gate_file(tmp_path / "gate.json", _admit())

    rc = greenfield_proposals_cli.main([
        "propose", "--repo-root", str(tmp_path), "--prompt", prompt,
        "--gate-file", str(gate), "--format", "json",
    ])

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "error"
    assert "host-authored candidate" in payload["error"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]


def test_forged_gate_witness_fails_before_candidate_load(tmp_path: Path, capsys) -> None:
    prompt = "Build a service workspace. A coordinator opens an intake request and verifies a decision receipt."
    gate_data = _admit()
    gate_data["result_quote"] = "a fabricated result"
    gate = _gate_file(tmp_path / "gate.json", gate_data)

    rc = greenfield_proposals_cli.main([
        "propose", "--repo-root", str(tmp_path), "--prompt", prompt,
        "--gate-file", str(gate), "--format", "json",
    ])

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "error"
    assert "result_quote" in payload["error"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gate.json"]
