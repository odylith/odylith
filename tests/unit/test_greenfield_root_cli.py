from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_proposals_cli, greenfield_repository_write_set
from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture


def test_greenfield_help_describes_complete_preconfirm_package(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "--help"])

    output = capsys.readouterr().out.lower()
    assert excinfo.value.code == 0
    assert "provider-free" not in output
    assert "complete" in output
    assert "before confirmation" in output


def test_greenfield_create_help_exposes_precompiled_transaction_contract(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "create", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith greenfield create" in output
    assert "--transaction-file" in output
    assert "--transaction-hash" in output
    assert "--completion-receipt" in output
    assert "--confirm" in output
    assert "--intent-file" not in output
    assert "--confirm-intent" not in output


def test_greenfield_authority_check_is_routed_by_root_cli(tmp_path: Path, capsys) -> None:
    gate_path = tmp_path / "authority-gate.json"
    gate_path.write_text(json.dumps({
        "decision": "clarify",
        "required_fields": ["first_path"],
        "owner_quote": "",
        "task_quote": "",
        "result_quote": "",
        "question": "Who uses the product, for which task, and with what result?",
    }), encoding="utf-8")

    rc = cli.main([
        "greenfield", "authority-check", "--repo-root", str(tmp_path),
        "--prompt", "Build a service workspace", "--gate-file", str(gate_path),
        "--format", "json",
    ])

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "clarification_required"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["authority-gate.json"]


def test_greenfield_propose_command_returns_one_pre_author_clarification(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from odylith.runtime.reasoning import odylith_reasoning

    def unexpected_work(*_args, **_kwargs):
        pytest.fail("Authority clarification must precede ledger, candidate, model, and compiler work")

    for name in ("_source_duty_receipt_from_args", "_host_candidate_from_args", "_compile_prompt_evidence_transaction"):
        monkeypatch.setattr(greenfield_proposals_cli, name, unexpected_work)
    monkeypatch.setattr(odylith_reasoning, "provider_from_config", unexpected_work)
    activate_greenfield_baseline_fixture(tmp_path)
    publication = (tmp_path / "odylith/index.html").read_bytes()
    baseline = greenfield_repository_write_set.greenfield_managed_fingerprints(tmp_path)
    prompt = "Build an ecommerce site"
    gate_path = tmp_path.parent / f"{tmp_path.name}-authority-gate.json"
    ledger_path = tmp_path.parent / f"{tmp_path.name}-unused-ledger.json"
    assert not ledger_path.exists()
    baseline_paths = set(tmp_path.rglob("*"))
    gate_path.write_text(json.dumps({
        "decision": "clarify",
        "required_fields": ["first_path"],
        "owner_quote": "",
        "task_quote": "",
        "result_quote": "",
        "question": "Who uses this product first, what complete task do they finish, and what result do they see?",
    }), encoding="utf-8")
    rc = cli.main(
        [
            "greenfield",
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--gate-file",
            str(gate_path),
            "--ledger-file",
            str(ledger_path),
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["mode"] == "clarification_required"
    clarification = payload["clarification"]
    assert clarification["question"] == "Who uses this product first, what complete task do they finish, and what result do they see?"
    assert clarification["required_fields"] == ["first_path"]
    assert (tmp_path / "odylith/index.html").read_bytes() == publication
    assert greenfield_repository_write_set.greenfield_managed_fingerprints(tmp_path) == baseline
    assert set(tmp_path.rglob("*")) == baseline_paths
    assert not ledger_path.exists()
    assert not (tmp_path / ".odylith/runtime/greenfield/pending").exists()
    assert "provider_calls" not in payload
    assert "host_reasoning_task" not in payload
    assert "backlog" not in payload
    assert "components" not in payload
    assert "diagrams" not in payload
