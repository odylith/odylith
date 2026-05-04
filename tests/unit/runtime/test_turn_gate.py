from __future__ import annotations

from pathlib import Path

from odylith.runtime.governed_harness import turn_gate


def _closure_payload() -> dict[str, object]:
    command = "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_turn_gate.py"
    return {
        "prompt": "Verify whether this bounded contract is already satisfied.",
        "policy_hints": {
            "non_mutating_closure_allowed": True,
            "focused_checks_cover_contract": True,
        },
        "focused_local_checks": [command],
        "validation_commands": [command],
        "focused_check_result": {
            "status": "passed",
            "results": [{"status": "passed", "command": command}],
        },
        "selected_evidence_refs": ["tests/unit/runtime/test_turn_gate.py"],
    }


def test_decide_turn_emits_product_early_exit_receipt(tmp_path: Path) -> None:
    decision = turn_gate.decide_turn(
        repo_root=tmp_path,
        host="codex",
        mode="observe",
        prompt_payload=_closure_payload(),
    )

    rows = decision.as_dict()
    assert rows["schema_version"] == "odylith.turn-gate.v1"
    assert rows["decision_type"] == "early_exit_proof"
    assert rows["evidence_report"]["sufficiency_verdict"] is True
    assert rows["execution_capsule"]["owned_paths"] == []
    assert rows["receipt"]["source"] == "product_turn_gate"
    assert rows["receipt"]["proof_card"]["label"] == "early-exit proof"


def test_tool_check_uses_persisted_execution_capsule(tmp_path: Path) -> None:
    command = "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_turn_gate.py"
    decision = turn_gate.decide_turn(
        repo_root=tmp_path,
        host="codex",
        mode="advise",
        prompt_payload={
            "prompt": "Edit a bounded runtime file and validate it.",
            "expected_write_paths": ["src/odylith/runtime/governed_harness/turn_gate.py"],
            "validation_commands": [command],
        },
        persist_receipt=True,
    )

    allowed = turn_gate.check_tool(
        repo_root=tmp_path,
        host="codex",
        decision_id=decision.decision_id,
        tool_input={"tool": "Bash", "command": command},
    )
    outside_write = turn_gate.check_tool(
        repo_root=tmp_path,
        host="codex",
        decision_id=decision.decision_id,
        tool_input={"tool": "Edit", "path": "README.md"},
    )

    assert allowed.outcome == "allow"
    assert outside_write.outcome == "ask"
    assert outside_write.reason == "write_outside_capsule_requires_decision"


def test_stop_check_blocks_completion_claim_without_validation(tmp_path: Path) -> None:
    decision = turn_gate.decide_turn(
        repo_root=tmp_path,
        host="codex",
        mode="enforce",
        prompt_payload={
            "prompt": "Edit a bounded runtime file and validate it.",
            "expected_write_paths": ["src/odylith/runtime/governed_harness/turn_gate.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_turn_gate.py"],
        },
        persist_receipt=True,
    )

    stop = turn_gate.check_stop(
        repo_root=tmp_path,
        host="codex",
        decision_id=decision.decision_id,
        transcript_text="Done.",
    )

    assert stop["outcome"] == "deny"
    assert stop["reason"] == "completion_claim_missing_validation_obligation"
