"""Human-facing terminal decisions stay thin, exact, and fail closed."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from odylith.runtime.domain_intelligence import greenfield_cli
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    build_product_create_transaction,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
)
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.surfaces import greenfield_host_confirmation
from tests.unit.runtime.test_greenfield_host_confirmation import _stage_pending_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import (
    compiled_greenfield_package_fixture,
)
from tests.unit.runtime.test_greenfield_transaction_provenance import (
    _executed_source_files,
)
from tests.unit.runtime.test_greenfield_transaction_provenance import (
    _transaction as _source_retaining_transaction,
)


_HASH = "a" * 64


@pytest.mark.parametrize("command,status", [("CONFIRM", "CLOSED"), ("REJECT", "ABORTED")])
def test_public_cli_dispatches_terminal_decisions_without_a_provider(tmp_path, monkeypatch, capsys, command, status):
    from odylith import cli
    from odylith.runtime.reasoning import odylith_reasoning

    _transaction, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")
    monkeypatch.setattr(
        odylith_reasoning, "provider_from_config",
        lambda *_args, **_kwargs: pytest.fail("A terminal decision must not resolve a model provider"),
    )
    assert cli.main([
        "greenfield", "decide", "--repo-root", str(tmp_path), command, transaction_hash, "--json",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == status


def _decision(*, command: str, status: str, visible: str) -> dict[str, object]:
    return {
        "version": "odylith.greenfield.host-confirmation-callback.v1",
        "status": status,
        "command": command,
        "transaction_hash": _HASH,
        "visible_markdown": visible,
        "developer_context": "",
    }


def _call_without_argparse_escape(argv: list[str]) -> int:
    try:
        result = greenfield_cli.main(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    return int(result)


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
    return digest.hexdigest()


def _write_candidate_stub(tmp_path: Path) -> Path:
    path = tmp_path.parent / f"{tmp_path.name}-host-candidate.json"
    path.write_text("{}\n", encoding="utf-8")
    return path


def test_terminal_decision_prints_human_completion_without_json_wrapper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, object]] = []

    def handle(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return _decision(command="CONFIRM", status="CLOSED", visible="**Published**\n\nExact readback passed.")

    monkeypatch.setattr(greenfield_host_confirmation, "handle_greenfield_decision", handle)

    assert greenfield_cli.main([
        "decide", "CONFIRM", _HASH, "--repo-root", str(tmp_path),
    ]) == 0

    output = capsys.readouterr().out
    assert "Published" in output
    assert "Exact readback passed." in output
    assert '"visible_markdown"' not in output
    assert '"developer_context"' not in output
    assert calls == [{
        "repo_root": tmp_path.resolve(),
        "command": "CONFIRM",
        "transaction_hash": _HASH,
        "edit_evidence": None,
    }]


def test_terminal_decision_json_is_explicit_opt_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        greenfield_host_confirmation,
        "handle_greenfield_decision",
        lambda **_kwargs: _decision(command="REJECT", status="ABORTED", visible="Rejected without writes."),
    )

    assert greenfield_cli.main([
        "decide", "REJECT", _HASH, "--repo-root", str(tmp_path), "--json",
    ]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ABORTED"
    assert payload["command"] == "REJECT"
    assert payload["transaction_hash"] == _HASH
    assert payload["visible_markdown"] == "Rejected without writes."


@pytest.mark.parametrize(
    "argv",
    [
        ["decide"],
        ["decide", "CONFIRM"],
        ["decide", "PUBLISH", _HASH],
        ["decide", "CONFIRM", "not-a-hash"],
        ["decide", "CONFIRM", _HASH, "unexpected"],
        ["decide", "CONFIRM", _HASH, "--edit", "change it"],
        ["decide", "CONFIRM", _HASH, "--edit", ""],
        ["decide", "REJECT", _HASH, "--edit", "change it"],
        ["decide", "REJECT", _HASH, "--edit-evidence", ""],
        ["decide", "EDIT", _HASH, "--edit", "one", "--edit-evidence", "two.md"],
    ],
)
def test_terminal_decision_rejects_missing_or_incompatible_inputs_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        greenfield_host_confirmation,
        "handle_greenfield_decision",
        lambda **kwargs: calls.append(dict(kwargs)) or pytest.fail("invalid decision reached the kernel"),
    )

    assert _call_without_argparse_escape([*argv, "--repo-root", str(tmp_path)]) != 0
    assert calls == []
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


def test_terminal_edit_without_evidence_requests_a_correction_without_compiling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, object]] = []

    def handle(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return _decision(
            command="EDIT",
            status="edit_evidence_required",
            visible="stale host copy that the terminal adapter must replace",
        )

    monkeypatch.setattr(greenfield_host_confirmation, "handle_greenfield_decision", handle)
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "rebuild_pending_transaction",
        lambda **_kwargs: pytest.fail("missing EDIT evidence reached proposal compilation"),
    )

    assert greenfield_cli.main([
        "decide", "EDIT", _HASH, "--repo-root", str(tmp_path),
    ]) == 0

    output = capsys.readouterr().out
    assert "What would you like to change?" in output
    assert "--edit '<corrections>'" in output
    assert "nothing has been published" in output
    assert "same reply" not in output
    assert calls == [{
        "repo_root": tmp_path.resolve(),
        "command": "EDIT",
        "transaction_hash": _HASH,
        "edit_evidence": None,
    }]
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


def test_terminal_edit_rebuilds_once_from_verified_retained_source_and_correction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = _source_retaining_transaction(tmp_path)
    pending_path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=tmp_path,
        transaction=previous,
    )
    correction = "Require the operator to record the recovery outcome."
    new_hash = "b" * 64
    new_path = pending_path.parent.parent / new_hash / pending_path.name
    compile_calls: list[dict[str, object]] = []
    review_calls: list[dict[str, object]] = []

    def compile_once(**kwargs: object) -> tuple[dict[str, str], object, Path]:
        compile_calls.append(dict(kwargs))
        return {"title": "Rebuilt"}, type("Transaction", (), {"transaction_hash": new_hash})(), new_path

    monkeypatch.setattr(greenfield_proposals_cli, "_compile_prompt_evidence_transaction", compile_once)
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_print_transaction_review",
        lambda **kwargs: review_calls.append(dict(kwargs)),
    )
    governed_before = _tree_digest(tmp_path / "odylith")
    candidate_path = _write_candidate_stub(tmp_path)

    assert greenfield_cli.main([
        "decide", "EDIT", previous.transaction_hash,
        "--repo-root", str(tmp_path), "--edit", correction,
        "--candidate-file", str(candidate_path),
    ]) == 0

    assert len(compile_calls) == 1
    call = compile_calls[0]
    assert call["repo_root"] == tmp_path.resolve()
    assert call["prompt"] == previous.proposal["intent"]["prompt"]
    assert call["edit_evidence"] == correction
    assert call["release_selector"] == previous.release_selector
    assert call["repair_tier"] == previous.quality_manifest["requested_repair_tier"]
    assert call["source_language"] == "en"
    assert call["host_candidate"] == {}
    assert isinstance(call["started_at"], float)
    assert len(review_calls) == 1
    assert review_calls[0]["candidate_intent"] == {"title": "Rebuilt"}
    assert review_calls[0]["transaction"].transaction_hash == new_hash
    assert review_calls[0]["transaction_path"] == new_path
    assert review_calls[0]["as_json"] is False
    assert pending_path.is_file()
    assert _tree_digest(tmp_path / "odylith") == governed_before


def test_terminal_edit_without_retained_source_fails_closed_before_compilation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    retained = _source_retaining_transaction(tmp_path)
    proposal = {
        **retained.proposal,
        "intent": {**retained.proposal["intent"], "prompt": ""},
    }
    package = compiled_greenfield_package_fixture(proposal, repo_root=tmp_path)
    legacy = build_product_create_transaction(
        proposal=proposal,
        release_selector=retained.release_selector,
        validation_gate=retained.validation_gate,
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=retained.intent_authority,
        quality_manifest=retained.quality_manifest,
        repo_root=tmp_path,
    )
    pending_path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=tmp_path,
        transaction=legacy,
    )
    governed_before = _tree_digest(tmp_path / "odylith")
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_compile_prompt_evidence_transaction",
        lambda **_kwargs: pytest.fail("missing retained source reached proposal compilation"),
    )

    assert greenfield_cli.main([
        "decide", "EDIT", legacy.transaction_hash, "--repo-root", str(tmp_path),
        "--edit", "Keep the correction bounded.",
    ]) == 2

    assert "no retained source evidence" in capsys.readouterr().out
    assert pending_path.is_file()
    assert _tree_digest(tmp_path / "odylith") == governed_before


@pytest.mark.parametrize(
    ("outcome", "expected_result", "expected_text"),
    [
        ("failure", 2, "authoring failed"),
        ("clarification", 0, "Which operator owns the decision?"),
        ("same_hash", 2, "did not produce a new reviewed package"),
    ],
)
def test_terminal_edit_non_success_preserves_the_original_reviewed_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
    expected_result: int,
    expected_text: str,
) -> None:
    previous = _source_retaining_transaction(tmp_path)
    pending_path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=tmp_path,
        transaction=previous,
    )
    governed_before = _tree_digest(tmp_path / "odylith")
    compile_calls: list[dict[str, object]] = []
    candidate_path = _write_candidate_stub(tmp_path)

    def compile_once(**kwargs: object) -> tuple[dict[str, str], object, Path]:
        compile_calls.append(dict(kwargs))
        if outcome == "failure":
            raise RuntimeError("authoring failed")
        if outcome == "clarification":
            raise GreenfieldClarificationRequired("Which operator owns the decision?")
        return (
            {"title": "Unchanged"},
            type("Transaction", (), {"transaction_hash": previous.transaction_hash})(),
            pending_path,
        )

    monkeypatch.setattr(greenfield_proposals_cli, "_compile_prompt_evidence_transaction", compile_once)
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_print_transaction_review",
        lambda **_kwargs: pytest.fail("unsuccessful EDIT rendered a new review"),
    )

    assert greenfield_cli.main([
        "decide", "EDIT", previous.transaction_hash,
        "--repo-root", str(tmp_path), "--edit", "Clarify the owner.",
        "--candidate-file", str(candidate_path),
    ]) == expected_result

    assert expected_text in capsys.readouterr().out
    assert len(compile_calls) == 1
    assert pending_path.is_file()
    assert _tree_digest(tmp_path / "odylith") == governed_before


def test_terminal_confirm_uses_real_kernel_and_same_hash_retry_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _transaction, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")

    assert greenfield_cli.main([
        "decide", "CONFIRM", transaction_hash, "--repo-root", str(tmp_path),
    ]) == 0
    first_output = capsys.readouterr().out
    journal = tmp_path / ".odylith/runtime/greenfield/create-journal" / transaction_hash
    first_journal = _tree_digest(journal)

    assert "published" in first_output.casefold()
    assert "readback" in first_output.casefold()
    assert journal.is_dir()

    assert greenfield_cli.main([
        "decide", "CONFIRM", transaction_hash, "--repo-root", str(tmp_path),
    ]) == 0
    retry_output = capsys.readouterr().out

    assert "published" in retry_output.casefold()
    assert _tree_digest(journal) == first_journal


def test_terminal_confirm_executes_only_the_postconfirm_decision_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _transaction, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")
    source_root = Path(__file__).resolve().parents[3] / "src" / "odylith"
    adapter = source_root / "runtime/domain_intelligence/greenfield_cli.py"
    forbidden_semantic_sources = {
        source_root / "runtime/domain_intelligence/greenfield_atomic_fact_ledger.py",
        source_root / "runtime/domain_intelligence/greenfield_authored_semantics.py",
        source_root / "runtime/domain_intelligence/greenfield_model_intent_authoring.py",
        source_root / "runtime/domain_intelligence/greenfield_model_intent_materialization.py",
        source_root / "runtime/domain_intelligence/greenfield_preconfirm_engine.py",
        source_root / "runtime/domain_intelligence/greenfield_product_intent_envelope.py",
        source_root / "runtime/domain_intelligence/greenfield_proposals_cli.py",
        source_root / "runtime/reasoning/odylith_reasoning.py",
    }

    with _executed_source_files(source_root) as executed:
        assert greenfield_cli.main([
            "decide", "CONFIRM", transaction_hash, "--repo-root", str(tmp_path),
        ]) == 0

    capsys.readouterr()
    assert adapter in executed
    assert executed.isdisjoint(forbidden_semantic_sources)


def test_terminal_reject_uses_real_kernel_without_governed_writes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _transaction, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    governed_before = _tree_digest(tmp_path / "odylith")

    assert greenfield_cli.main([
        "decide", "REJECT", transaction_hash, "--repo-root", str(tmp_path),
    ]) == 0

    output = capsys.readouterr().out
    assert "rejected" in output.casefold()
    assert "no governed records were written" in output.casefold()
    assert not greenfield_pending_transaction_store.pending_transaction_directory(
        tmp_path, transaction_hash,
    ).exists()
    assert _tree_digest(tmp_path / "odylith") == governed_before


@pytest.mark.parametrize("command", ["CONFIRM", "REJECT"])
def test_terminal_confirm_and_reject_import_no_proposal_or_model_runtime_in_fresh_process(
    tmp_path: Path,
    command: str,
) -> None:
    _transaction, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    source_root = Path(__file__).resolve().parents[3] / "src"
    script = """
import json
from pathlib import Path
import sys

from odylith.runtime.domain_intelligence import greenfield_cli

forbidden = (
    "odylith.runtime.domain_intelligence.greenfield_proposals_cli",
    "odylith.runtime.domain_intelligence.greenfield_proposals",
    "odylith.runtime.domain_intelligence.greenfield_preconfirm_engine",
    "odylith.runtime.domain_intelligence.greenfield_model_intent_authoring",
    "odylith.runtime.domain_intelligence.greenfield_model_intent_materialization",
    "odylith.runtime.reasoning.odylith_reasoning",
)
loaded_after_import = sorted(name for name in forbidden if name in sys.modules)
result = greenfield_cli.main([
    "decide", sys.argv[2], sys.argv[3], "--repo-root", sys.argv[1], "--json",
])
print("IMPORT_PROOF=" + json.dumps({
    "result": result,
    "loaded_after_import": loaded_after_import,
    "loaded_after_decision": sorted(name for name in forbidden if name in sys.modules),
}, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), command, transaction_hash],
        check=False,
        capture_output=True,
        env={**os.environ, "ODYLITH_NO_BROWSER": "1", "PYTHONPATH": str(source_root)},
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    proof_line = next(line for line in completed.stdout.splitlines() if line.startswith("IMPORT_PROOF="))
    assert json.loads(proof_line.removeprefix("IMPORT_PROOF=")) == {
        "result": 0,
        "loaded_after_import": [],
        "loaded_after_decision": [],
    }
