"""Initial document custody through the release harness, without lifecycle EDIT."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_preconfirm_matrix as matrix
import greenfield_matrix_journey as journey
from greenfield_matrix_case_file import canonical_case_text, load_case_file
from greenfield_matrix_release_artifacts import RetainedEvidenceCase
from greenfield_matrix_statistics import expected_case_evidence_format, expected_case_source_complexity
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase, case_evidence
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import combined_prompt_evidence_source
from odylith.runtime.domain_intelligence import greenfield_proposals_cli


def _case() -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        name="reviewed initial evidence",
        prompt="  A reviewer records a café decision.\r\nPreserve the cited résumé.  ",
        confirmed_intent_markdown="\nReviewed first path: record → inspect → retain the decision.\n",
        required_terms=("decision",),
    )


@pytest.mark.parametrize("source", (
    "Retain capacity. Capacity remains attributable.",
    "Record that that reviewer approved the request.",
    "  Café capacity. Capacity stays cited.\r\n\r\n  Preserve  two words.  ",
))
def test_loader_preserves_source_words_without_generated_prose_deduplication(tmp_path: Path, source: str) -> None:
    expected = "\n".join(" ".join(line.split()) for line in source.strip().splitlines()).strip()
    correction = "  Add capacity. Capacity needs a dated receipt.\r\n"
    path = tmp_path / "source-words.json"
    path.write_text(json.dumps([{
        "name": "source words", "prompt": source,
        "confirmed_intent_markdown": source, "lifecycle_correction": correction,
    }]), encoding="utf-8")
    case = load_case_file(path, enforce_lexical_controls=False)[0]
    assert case.prompt == expected
    assert case.confirmed_intent_markdown == expected
    assert case.lifecycle_correction == correction
    assert canonical_case_text(source) == expected
    assert case.initial_prompt == expected + "\n\n# Operator edit evidence\n\n" + expected
    assert case_evidence(case)["prompt_sha256"] == hashlib.sha256(expected.encode()).hexdigest()
    assert case_evidence(case)["confirmed_intent_sha256"] == hashlib.sha256(expected.encode()).hexdigest()
    assert case.model_evidence.edit_evidence == correction.strip()


@pytest.mark.parametrize("field,absent_term", (
    ("required_terms", "mission evidence evidence"),
    ("leakage_terms", "mission evidence evidence review"),
))
def test_loader_refuses_ungrounded_repeated_word_controls(tmp_path: Path, field: str, absent_term: str) -> None:
    row = {
        "name": "mission evidence review", "prompt": "Create a mission evidence review workspace.",
        "required_terms": ["mission evidence"], "leakage_terms": ["mission evidence review"],
    }
    row[field] = [absent_term]
    source = tmp_path / "absent-control.json"
    source.write_text(json.dumps([row]), encoding="utf-8")
    with pytest.raises(RuntimeError, match=f"ungrounded {field}: {absent_term}"):
        load_case_file(source)


def test_initial_source_preserves_both_documents_and_truthful_source_format() -> None:
    case = _case()
    original_identity = case_evidence(case)
    initial = case.initial_prompt
    assert initial == case.prompt.strip() + "\n\n# Operator edit evidence\n\n" + case.confirmed_intent_markdown.strip()
    prepared = prepare_model_authoring_evidence(prompt=initial)

    assert prepared.prompt == initial
    assert prepared.edit_evidence == ""
    assert prepared.source_format == "operator_prompt"
    assert prepared.source_document_count == 1
    assert expected_case_evidence_format(case) == prepared.source_format
    assert expected_case_source_complexity(case) == {
        "evidence_bytes": len(prepared.evidence_source.encode("utf-8")), "documents": 1,
    }
    assert case.initial_input_streams == {
        "input.prompt": initial, "input.initial-request": case.prompt,
        "input.confirmed-intent": case.confirmed_intent_markdown, "input.edit-evidence": "",
    }
    assert case_evidence(case) == original_identity
    assert original_identity["prompt_sha256"] == hashlib.sha256(case.prompt.encode()).hexdigest()


@pytest.mark.parametrize("prompt,confirmed", (
    ("Initial evidence.", "Reviewed first path."),
    ("  Café résumé → décision.\r\n ", "\n  Review preserves εvidence.\r\n "),
    ("\nFirst line.\n\nSecond line.\n", "\n# Reviewed source\n\nRetain all lines.\n"),
    ("\nPlain request.\r\n", ""),
))
def test_initial_normalization_retains_exact_frozen_model_source_frame(prompt: str, confirmed: str) -> None:
    case = GreenfieldMatrixCase(name="initial source", prompt=prompt, confirmed_intent_markdown=confirmed, required_terms=())
    assert combined_prompt_evidence_source(prompt=case.initial_prompt, edit_evidence="") == combined_prompt_evidence_source(
        prompt=prompt, edit_evidence=confirmed,
    )


def test_plain_initial_prompt_is_byte_preserving() -> None:
    case = GreenfieldMatrixCase(name="plain", prompt="\nUnicode é → evidence\r\n", required_terms=())
    assert case.initial_prompt == case.prompt


def test_initial_documents_reach_candidate_flow_and_retention_without_edit_authority(tmp_path: Path, monkeypatch) -> None:
    case = _case()
    launcher = tmp_path / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    calls = []

    class ReachedInitialBoundary(Exception):
        pass

    def invoke(**kwargs):
        calls.append(kwargs)
        argv = matrix._greenfield_propose_arguments(prompt=kwargs["prompt"], edit_evidence=kwargs["edit_evidence"])
        assert argv[argv.index("--prompt") + 1] == case.initial_prompt
        assert "--edit" not in argv and "--edit-evidence" not in argv
        return SimpleNamespace(returncode=0)

    def journey(**kwargs):
        assert kwargs["raw_streams"] == case.initial_input_streams
        assert kwargs["invoke_propose"](315).returncode == 0
        raise ReachedInitialBoundary

    monkeypatch.setattr(matrix, "_local_release_env", lambda **kwargs: {})
    monkeypatch.setattr(matrix, "_run_host_candidate_propose", invoke)
    monkeypatch.setattr(matrix, "run_compiled_greenfield_journey", journey)
    monkeypatch.setattr(matrix, "_run", lambda **kwargs: pytest.fail("Initial boundary test cannot execute commands"))
    with pytest.raises(ReachedInitialBoundary):
        matrix._run_case(
            case=case, repo_root=tmp_path, install_script=tmp_path / "unused",
            base_url="unused", version="0.1.15", skip_install=True,
        )
    assert len(calls) == 1
    assert calls[0]["prompt"] == case.initial_input_streams["input.prompt"]
    assert calls[0]["edit_evidence"] == ""


def test_retention_keeps_invocation_bytes_and_original_document_bytes(tmp_path: Path, monkeypatch) -> None:
    case = _case()
    observed = {}
    monkeypatch.setattr(journey, "record_retained_case_text", lambda retained, path, value: observed.setdefault(path, value))
    monkeypatch.setattr(journey, "record_retained_case_json", lambda *args, **kwargs: None)
    journey.record_retained_execution(
        retained_case=SimpleNamespace(staging_root=tmp_path), proposal_payload={},
        dry_run_receipt={}, create_payload={}, raw_streams=case.initial_input_streams,
    )
    for name, value in case.initial_input_streams.items():
        assert observed[f"commands/{name}"] == value


def test_real_edit_flag_and_prior_custody_refusal_remain_intact(tmp_path: Path) -> None:
    correction = "Change the review policy."
    argv = matrix._greenfield_propose_arguments(prompt=_case().prompt, edit_evidence=correction)
    assert argv[argv.index("--edit") + 1] == correction
    with pytest.raises(ValueError, match="prior transaction hash"):
        greenfield_proposals_cli._edit_transaction_from_args(
            argparse.Namespace(transaction_hash=None, completion_receipt=None),
            repo_root=tmp_path, correction=correction,
        )
    assert list(tmp_path.iterdir()) == []


def test_optional_lifecycle_correction_preserves_all_original_public_frames_and_identities(tmp_path: Path) -> None:
    fixture = SCRIPTS_ROOT.parents[1] / "tests/fixtures/greenfield-release-corpus/live-subsets/greenfield-release-public-operating-envelope.v2.json"
    original = load_case_file(fixture, enforce_lexical_controls=False)
    raw = json.loads(fixture.read_text())
    for row in raw["cases"]:
        row["lifecycle_correction"] = ""
    successor = tmp_path / "explicit-empty.json"
    successor.write_text(json.dumps(raw))
    loaded = load_case_file(successor, enforce_lexical_controls=False)
    assert len(loaded) == len(original) == 40
    for prior, current in zip(original, loaded):
        assert current.initial_prompt.encode() == prior.initial_prompt.encode()
        assert current.model_evidence == prior.model_evidence
        assert case_evidence(replace(current, source_file=prior.source_file)) == case_evidence(prior)
    correction = "Retain the café reviewer’s decision.\r\n  Keep its exact source.\n"
    row = next(row for row in raw["cases"] if row.get("expectation", "transaction_committed") == "transaction_committed")
    row["lifecycle_correction"] = correction
    successor.write_text(json.dumps([row]))
    edited = load_case_file(successor, enforce_lexical_controls=False)[0]
    assert edited.lifecycle_correction.encode() == correction.encode()
    assert edited.model_evidence.source_format == "operator_prompt_with_edit_evidence"
    assert edited.model_evidence.source_document_count == 2
    assert edited.initial_input_streams["input.edit-evidence"] == ""


@pytest.mark.parametrize("correction", [None, True, {}, [], " \n "])
def test_loader_refuses_unusable_lifecycle_correction(tmp_path: Path, correction) -> None:
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps([{"name": "invalid", "prompt": "Retain a reviewed record.", "lifecycle_correction": correction}]))
    with pytest.raises(RuntimeError, match="invalid lifecycle_correction"):
        load_case_file(source, enforce_lexical_controls=False)


def _preservation_fixture():
    from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case, _admit
    from tests.unit.runtime.test_greenfield_source_duty_ledger import _yes_decisions
    from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt_for_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import source_duty_entailment_task
    case = list(_edit_case())
    source, ledger, context, _, old_decisions = case
    initial = source.split("\n\n# Operator edit evidence\n\n")[0] + "\n"
    source = prepare_model_authoring_evidence(prompt=initial, edit_evidence=context["correction"]).evidence_source
    from tests.unit.runtime.greenfield_model_authoring_fixtures import edit_action_context_fixture, preserved_edit_decisions_fixture
    prior_receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=initial)
    prior_design = {
        "components": [{"key": "record-state", "supported_event_orders": [1, 2], "verification_event_orders": [1, 2]}],
        "workstreams": [{"key": "record-delivery", "component_keys": ["record-state"], "verification_event_orders": [1, 2]}],
    }
    context = edit_action_context_fixture(prior_source=initial, prior_receipt=prior_receipt,
        prior_lifecycle=context["prior_lifecycle"], design=prior_design,
        transaction_hash=context["transaction_hash"], correction=context["correction"])
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=old_decisions["version"], verifier_task_sha256=task["verifier_task_sha256"],
        identity_preservation=deepcopy(old_decisions["identity_preservation"]),
        **preserved_edit_decisions_fixture(context))
    case = (source, ledger, context, task, decisions)
    from tests.unit.runtime.greenfield_model_authoring_fixtures import prior_transaction_custody_fixture
    previous = prior_transaction_custody_fixture(prior_source=initial, prior_receipt=prior_receipt,
        context=context, design=prior_design)
    edited = SimpleNamespace(transaction_hash="b" * 64,
        proposal={"intent": {"prompt": source, "authored_semantics": {"source_duty": {"ledger_receipt": _admit(case)}}}})
    return initial, context["correction"], previous, edited, case


@pytest.mark.parametrize("damage", [None, "missing", "uncertain", "authorized_change", "prior_guard", "prior_identity", "source"])
def test_additive_release_family_requires_verified_preservation_of_every_prior_duty(damage) -> None:
    from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _admit
    initial, correction, previous, edited, case = _preservation_fixture()
    if damage in {"missing", "uncertain", "authorized_change"}:
        table = case[-1]["edit_preservation"]
        key = "conditional_guards/G1"
        if damage == "missing":
            del table[key]
        elif damage == "uncertain":
            table[key]["verdict"] = "uncertain"
        else:
            table[key].update(verdict="changed", correction_authorization="yes")
            edited.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"] = _admit(case)
        if damage != "authorized_change":
            edited.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["decision_set"] = case[-1]
    elif damage == "prior_guard":
        previous.proposal["semantic_model"]["source_lifecycle"]["conditional_guards"][0]["rule"] = "Permit publication without review."
    elif damage == "prior_identity":
        previous.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"].pop("product_identity")
    elif damage == "source":
        initial += "A new decision maker owns approval."
    if damage:
        with pytest.raises(ValueError):
            journey._require_preserved_duties(previous=previous, edited=edited, initial_source=initial, correction=correction)
    else:
        verified = journey._require_preserved_duties(previous=previous, edited=edited, initial_source=initial, correction=correction)
        assert len(verified["decision_set"]["edit_preservation"]) == 6


@pytest.mark.parametrize("damage", [None, "initial_clarification", "initial_failure", "edited_clarification", "edited_failure", "same_hash", "mutated_prior", "terminal_failure", "terminal_mutated_prior", "terminal_mode_change", "prepare_only",
    "edited_failure_mutated_prior", "edited_clarification_mutated_prior", "edited_malformed_mutated_prior", "edited_exception_mutated_prior", "terminal_failure_mutated_prior"])
def test_lifecycle_journey_confirms_only_the_edited_seal_and_preserves_initial_custody(tmp_path: Path, monkeypatch, damage) -> None:
    from greenfield_matrix_transaction_evidence import CompiledCreateExecution
    from greenfield_matrix_release_artifacts import (
        begin_retained_case_evidence, finalize_retained_case_evidence,
        prepare_retained_evidence_output_dir, retained_evidence_manifest_issues,
        write_retained_evidence_manifest,
    )
    initial, correction, previous, edited, _ = _preservation_fixture()
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    evidence_root = prepare_retained_evidence_output_dir(output_dir=tmp_path / "retained", temp_parent=consumer)
    retained = begin_retained_case_evidence(evidence_root=evidence_root, case_id="receipt-edit")
    staging = retained.staging_root
    paths = {}
    for phase, transaction in (("initial", previous), ("edited", edited)):
        directory = consumer / ".odylith/runtime/greenfield/pending" / transaction.transaction_hash
        directory.mkdir(parents=True)
        path = directory / "product-create-transaction.v1.json"
        path.write_text(phase + " compiler bytes")
        (directory / ".bounded-journey.v1.json").write_text(phase + " bounded marker")
        (directory / (path.name + ".compiler-receipt.v1.json")).write_text(phase + " compiler receipt")
        receipt = consumer / f"{phase}-delivered.json"
        receipt.write_text(phase + " delivered bytes")
        paths[phase] = (transaction, path, receipt)
    calls, confirms, emitted_streams = [], [], {}
    native_error = RuntimeError("native EDIT transport failed")
    native_error.stdout, native_error.stderr = b"partial native stdout\n", b"primary native stderr\n"
    terminal_error = SimpleNamespace(returncode=2, stdout="primary CONFIRM stdout", stderr="primary CONFIRM stderr")
    tick = iter(float(value) for value in range(100))
    monkeypatch.setattr(journey.time, "perf_counter", lambda: next(tick))
    monkeypatch.setattr(journey, "_pending_phase", lambda **kwargs: paths["initial" if kwargs["payload"]["phase"] == "initial" else "edited"])
    monkeypatch.setattr(journey, "model_profile_evidence", lambda *args, **kwargs: {"issues": []})
    monkeypatch.setattr(journey, "authored_model_result_binding_issues", lambda **kwargs: ())

    def invoke(command, timeout):
        calls.append(tuple(command))
        if "show" in command:
            return SimpleNamespace(returncode=0, stdout="Odylith read this repo", stderr="")
        assert command[2] == "prepare" and timeout == 675
        phase = "edited" if "--transaction-hash" in command else "initial"
        assert ("--prompt" in command) == (phase == "initial")
        if phase == "edited":
            assert command[command.index("--completion-receipt") + 1] == str(paths["initial"][2])
            assert command[command.index("--edit") + 1] == correction
            if damage == "mutated_prior" or damage in {
                    "edited_failure_mutated_prior", "edited_clarification_mutated_prior",
                    "edited_malformed_mutated_prior", "edited_exception_mutated_prior"}:
                paths["initial"][1].write_text("mutated baseline")
            if damage == "same_hash":
                edited.transaction_hash = previous.transaction_hash
        diagnostic = Path(command[command.index("--diagnostic-evidence-dir") + 1])
        diagnostic.mkdir()
        (diagnostic / "candidate.stdout").write_text(json.dumps({"phase": phase}))
        ledger = {} if phase == "initial" else edited.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]
        (diagnostic / "source-ledger-check.stdout").write_text(json.dumps({"receipt": ledger}))
        clarification = damage in {f"{phase}_clarification", f"{phase}_clarification_mutated_prior"}
        failed = damage in {f"{phase}_failure", f"{phase}_failure_mutated_prior"}
        if phase == "edited" and damage == "edited_exception_mutated_prior":
            emitted_streams[phase] = {"stdout": native_error.stdout, "stderr": native_error.stderr}
            raise native_error
        payload = {"phase": phase, "mode": "clarification_required" if clarification else "product_create_transaction",
            "bounded_journey": {"elapsed_seconds": 0.25, "whole_journey_seconds": 0.5}}
        stdout = '{"truncated EDIT response' if phase == "edited" and damage == "edited_malformed_mutated_prior" else json.dumps(payload)
        emitted_streams[phase] = {"stdout": stdout.encode(), "stderr": b"failure" if failed else b""}
        return SimpleNamespace(returncode=2 if failed else 0, stdout=stdout, stderr="failure" if failed else "")

    def confirm(**kwargs):
        confirms.append(kwargs)
        assert json.loads(kwargs["proposed"].stdout)["phase"] == "edited"
        assert kwargs["proposed"].completion_receipt_path == str(paths["edited"][2])
        if damage in {"terminal_mutated_prior", "terminal_failure_mutated_prior"}:
            paths["initial"][1].write_text("changed during confirmation")
        elif damage == "terminal_mode_change":
            path = paths["initial"][1]
            path.chmod((path.stat().st_mode & 0o777) ^ 0o040)
        return CompiledCreateExecution(decision=SimpleNamespace(returncode=0), retry_decision=SimpleNamespace(returncode=0),
            commit_payload={"closed": True}, failure=terminal_error if damage in {"terminal_failure", "terminal_failure_mutated_prior"} else None,
            proposal_seconds=0.25, confirmation_seconds=0.1, retry_seconds=0.1, dry_run_receipt={}, proposal_payload={},
            terminal_journal={} if damage == "prepare_only" else {
                "state": "closed", "lifecycle_state": "CLOSED", "transaction_hash": edited.transaction_hash,
            })

    monkeypatch.setattr(journey, "commit_precompiled_transaction", confirm)
    evidence, raw = {}, {"input.edit-evidence": ""}
    kwargs = dict(repo_root=consumer, env={"ODYLITH_GREENFIELD_MODEL_PROFILE": journey.model_profile_id_for_repair_tier("standard")}, repair_tier="standard",
        invoke_cli=invoke, invoke_propose=lambda timeout: pytest.fail("EDIT family cannot use the initial manual host flow"),
        read_proposal_stage_seconds=lambda: pytest.fail("Native prepare supplies its own measured stage"),
        initial_prompt=initial.split("# Operator prompt evidence\n\n", 1)[1].rstrip(),
        lifecycle_correction=correction, retained_case=retained,
        lifecycle_evidence=evidence, raw_streams=raw)
    raises = damage in {"initial_clarification", "initial_failure", "edited_clarification", "edited_failure", "same_hash", "mutated_prior",
        "edited_failure_mutated_prior", "edited_clarification_mutated_prior", "edited_malformed_mutated_prior", "edited_exception_mutated_prior"}
    if raises:
        with pytest.raises((RuntimeError, ValueError)) as caught:
            journey.run_compiled_greenfield_journey(**kwargs)
        assert confirms == []
        assert evidence["status"] != "edited_seal_confirmed"
        if damage == "edited_exception_mutated_prior":
            assert caught.value is native_error
        elif damage == "edited_malformed_mutated_prior":
            assert isinstance(caught.value, json.JSONDecodeError)
        elif damage in {"edited_failure_mutated_prior", "edited_clarification_mutated_prior"}:
            assert str(caught.value) == "lifecycle edited preparation did not return a pending sealed package"
    else:
        execution = journey.run_compiled_greenfield_journey(**kwargs)
        assert len(confirms) == 1
        assert evidence["status"] == ("edited_seal_prepared" if damage else "edited_seal_confirmed")
        assert execution.proposal_seconds == 0.25
        assert raw["input.edit-evidence"] == correction
        assert (staging / "semantic/lifecycle-initial/product-create-transaction.v1.json").read_text() == "initial compiler bytes"
        assert json.loads((staging / "semantic/host-candidate.raw.v1.json").read_text()) == {"phase": "edited"}
        assert evidence["initial"]["observation"]["whole_journey_seconds"] == 0.5
        assert evidence["edited"]["observation"]["whole_journey_seconds"] == 0.5
        assert evidence["timing_qualification"] == "unqualified"
        if damage in {"terminal_mutated_prior", "terminal_mode_change", "terminal_failure_mutated_prior"}:
            assert "initial_artifacts_after_confirm" not in evidence
            assert execution.failure is not None
        else:
            assert evidence["initial_artifacts_after_confirm"] == {
                token: {key: row[key] for key in ("sha256", "mode")}
                for token, row in evidence["initial"]["artifacts"].items()
            }
        if damage in {"terminal_failure", "terminal_failure_mutated_prior"}:
            assert execution.failure is terminal_error
            assert evidence["failure"]["message"] == terminal_error.stderr
    assert len(calls) == (2 if damage in {"initial_clarification", "initial_failure"} else 3)
    structured = staging / "semantic/receipt-bound-edit.v1.json"
    assert json.loads(structured.read_text()) == evidence
    if damage:
        assert evidence["failure"]
    if damage and damage.endswith("_mutated_prior"):
        changed = str(paths["initial"][1])
        observed = evidence["initial_artifacts_on_failure"][changed]
        assert observed["sha256"] == hashlib.sha256(paths["initial"][1].read_bytes()).hexdigest()
        assert observed["sha256"] != evidence["initial"]["artifacts"][changed]["sha256"]
        assert evidence["custody_issues"]
        if damage.startswith("edited_"):
            attempt = evidence["prepare_attempts"]["edited"]
            assert attempt["wall_seconds"] > 0
            for stream in ("stdout", "stderr"):
                assert (staging / attempt[f"{stream}_path"]).read_bytes() == emitted_streams["edited"][stream]
        before = staging / evidence["initial"]["artifacts"][changed]["retained_path"]
        assert before.read_bytes() == b"initial compiler bytes"
        case_manifest = finalize_retained_case_evidence(case=retained, repo_root=consumer,
            result_payload={"status": "failed", "evidence": {"lifecycle_edit": evidence}})
        manifest = write_retained_evidence_manifest(root=evidence_root, expected_case_ids=(retained.case_id,))
        shutil.rmtree(consumer)
        assert retained_evidence_manifest_issues(manifest) == ()
        assert json.loads((case_manifest.parent / "semantic/receipt-bound-edit.v1.json").read_text()) == evidence


@pytest.mark.parametrize("damage", [None, "missing_receipt", "wrong_hash", "foreign_receipt", "stale_receipt", "source_byte", "transaction_byte", "compiler_receipt_byte", "standalone"])
def test_lifecycle_pending_boundary_uses_real_compiler_and_receipt_validation(tmp_path: Path, monkeypatch, damage) -> None:
    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as pending
    from odylith.runtime.domain_intelligence import greenfield_process as process
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    transaction = _transaction(consumer)
    journey_id, nonce = "c" * 64, "d" * 64
    marker = {"version": "odylith.greenfield.journey-supervision.v1", "journey_id": journey_id,
        "completion_digest": hashlib.sha256(nonce.encode("ascii")).hexdigest()}
    # Only guardian registration is mocked. Compiler, bounded completion writer,
    # delivered-receipt writer and both seal readers are the real owners.
    monkeypatch.setattr(process, "register_bounded_pending_transaction", lambda path: None if damage == "standalone" else marker)
    path = pending.stage_pending_transaction(repo_root=consumer, transaction=transaction)
    if damage != "standalone":
        process._write_journey_completion(path.parent, journey_id=journey_id, finished=1.0, deadline=2.0)
    receipt = pending.write_completion_receipt_delivery(repo_root=consumer, receipt={
        "version": "odylith.greenfield.completion-receipt.v1", "journey_id": journey_id,
        "transaction_hash": transaction.transaction_hash, "nonce": nonce,
    })
    source = transaction.proposal["intent"]["prompt"]
    payload = {"product_create_transaction": {"transaction_hash": transaction.transaction_hash},
        "transaction_file": str(path), "completion_receipt": str(receipt)}
    if damage == "missing_receipt":
        del payload["completion_receipt"]
    elif damage == "wrong_hash":
        payload["product_create_transaction"]["transaction_hash"] = "a" * 64
    elif damage == "foreign_receipt":
        foreign = tmp_path / "foreign-receipt.json"
        foreign.write_bytes(receipt.read_bytes())
        payload["completion_receipt"] = str(foreign)
    elif damage == "stale_receipt":
        stale = json.loads(receipt.read_text())
        stale["journey_id"] = "e" * 64
        receipt.write_text(json.dumps(stale))
    elif damage == "source_byte":
        source += " "
    elif damage == "transaction_byte":
        path.write_bytes(path.read_bytes() + b" ")
    elif damage == "compiler_receipt_byte":
        compiler_receipt = path.with_name(path.name + ".compiler-receipt.v1.json")
        compiler_receipt.write_bytes(compiler_receipt.read_bytes() + b" ")
    if damage:
        with pytest.raises((OSError, ValueError)):
            journey._pending_phase(repo_root=consumer, payload=payload, expected_source=source)
    else:
        loaded, loaded_path, delivered = journey._pending_phase(repo_root=consumer, payload=payload, expected_source=source)
        assert loaded.transaction_hash == transaction.transaction_hash
        assert loaded_path == path and delivered == receipt


def test_lifecycle_artifact_references_survive_atomic_retention_and_consumer_cleanup(tmp_path: Path) -> None:
    from greenfield_matrix_release_artifacts import (
        begin_retained_case_evidence, finalize_retained_case_evidence,
        prepare_retained_evidence_output_dir, repo_artifact_path,
        retained_evidence_manifest_issues, write_retained_evidence_manifest,
    )
    consumer = tmp_path / "consumer"
    pending = consumer / "pending"
    pending.mkdir(parents=True)
    transaction = pending / "compiled-bytes.json"
    transaction.write_bytes(b"exact compiler fixture bytes\n")
    receipt = consumer / "delivered-receipt.json"
    receipt.write_bytes(b"exact delivered receipt fixture bytes\n")
    root = prepare_retained_evidence_output_dir(output_dir=tmp_path / "retained", temp_parent=consumer)
    case = begin_retained_case_evidence(evidence_root=root, case_id="custody-without-credit")
    artifacts = journey._retain_pending(retained_case=case, phase="initial", path=transaction, receipt=receipt)
    after = journey._require_pending_unchanged(artifacts)
    case_manifest = finalize_retained_case_evidence(case=case, repo_root=consumer,
        result_payload={"status": "failed", "evidence": {"lifecycle_edit": {
            "initial": {"artifacts": artifacts}, "initial_artifacts_after_confirm": after,
        }}})
    manifest = write_retained_evidence_manifest(root=root, expected_case_ids=(case.case_id,))
    shutil.rmtree(consumer)
    assert not case.staging_root.exists() and case_manifest.is_file()
    assert retained_evidence_manifest_issues(manifest) == ()
    authenticated_lifecycle = json.loads((case_manifest.parent / "case-result.v1.json").read_text())["evidence"]["lifecycle_edit"]
    authenticated = authenticated_lifecycle["initial"]["artifacts"]
    assert authenticated_lifecycle["initial_artifacts_after_confirm"] == {
        token: {key: row[key] for key in ("sha256", "mode")} for token, row in authenticated.items()
    }
    for row in authenticated.values():
        retained = repo_artifact_path(case_manifest.parent, row["retained_path"])
        assert retained is not None and retained.is_file()
        assert hashlib.sha256(retained.read_bytes()).hexdigest() == row["sha256"]
        assert retained.stat().st_mode & 0o777 == row["retained_mode"] == 0o600
