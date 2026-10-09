"""Retain installed initial and receipt-bound EDIT confirmation journeys."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import math
import time
from types import SimpleNamespace
from typing import Any

from greenfield_matrix_release_artifacts import (
    RetainedEvidenceCase, record_retained_case_bytes, record_retained_case_json,
    record_retained_case_text,
)
from greenfield_matrix_transaction_evidence import CompiledCreateExecution, commit_precompiled_transaction
from greenfield_model_profile_proof import authored_model_result_binding_issues
from greenfield_model_profiles import model_profile_evidence
from greenfield_model_profile_proof import sealed_model_profile_observation
from odylith.runtime.domain_intelligence.greenfield_create_transaction import load_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence.greenfield_pending_transaction_store import resolve_pending_transaction
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    GREENFIELD_COMPLETION_RESERVE_SECONDS, STANDARD_PROFILE_ID, get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import greenfield_edit_preservation_context
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import verify_greenfield_source_duty_ledger_receipt
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS


def run_compiled_greenfield_journey(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    repair_tier: str,
    invoke_cli: Callable[[Sequence[str], int], Any],
    invoke_propose: Callable[[int], Any],
    read_proposal_stage_seconds: Callable[[], float],
    raw_streams: dict[str, str] | None = None,
    initial_prompt: str = "",
    lifecycle_correction: str = "",
    retained_case: RetainedEvidenceCase | None = None,
    lifecycle_evidence: dict[str, Any] | None = None,
) -> CompiledCreateExecution:
    profile_id = model_profile_id_for_repair_tier(repair_tier)
    if str(env.get("ODYLITH_GREENFIELD_MODEL_PROFILE") or "").strip() != profile_id:
        raise ValueError("release proof repair tier does not match its configured model profile")
    shown = invoke_cli(("./.odylith/bin/odylith", "show", "--repo-root", "."), 60)
    if raw_streams is not None:
        raw_streams.update({"show.stdout": shown.stdout, "show.stderr": shown.stderr})
    if shown.returncode != 0 or "Odylith read this repo" not in shown.stdout:
        raise RuntimeError("installed Greenfield journey failed its initial capability show")
    if lifecycle_correction:
        return _run_receipt_bound_edit(
            repo_root=repo_root, env=env, profile_id=profile_id, invoke_cli=invoke_cli,
            initial_prompt=initial_prompt, correction=lifecycle_correction,
            retained_case=retained_case, raw_streams=raw_streams,
            evidence=lifecycle_evidence,
        )
    started = time.perf_counter()
    proposed = invoke_propose(int(get_greenfield_model_profile(profile_id).operational_timeout_seconds))
    whole_journey_seconds = round(time.perf_counter() - started, 3)
    proposal_seconds = read_proposal_stage_seconds()
    if (type(proposal_seconds) is not float or not math.isfinite(proposal_seconds)
            or proposal_seconds <= 0.0 or proposal_seconds > whole_journey_seconds + 1.0):
        raise RuntimeError("installed Greenfield journey lacks measured proposal-stage timing")
    if raw_streams is not None:
        raw_streams["timing.whole-journey-seconds"] = str(whole_journey_seconds)
    execution = commit_precompiled_transaction(
        repo_root=repo_root, proposed=proposed, proposal_seconds=proposal_seconds,
        invoke_cli=lambda command: invoke_cli(command, 60),
    )
    if raw_streams is not None:
        raw_streams["terminal-journal.v1.json"] = execution.terminal_journal_text
        for label, result in (
            ("propose", proposed), ("decide", execution.decision),
            ("retry-decide", execution.retry_decision),
        ):
            for stream in ("stdout", "stderr"):
                raw_streams[f"{label}.{stream}"] = str(getattr(result, stream, "") or "")
    return execution


def record_retained_execution(
    *, retained_case: RetainedEvidenceCase, proposal_payload: Mapping[str, Any],
    dry_run_receipt: Mapping[str, Any], create_payload: Mapping[str, Any],
    raw_streams: Mapping[str, str],
) -> None:
    for name in (
        "input.prompt", "input.initial-request", "input.confirmed-intent", "input.edit-evidence",
        "show.stdout", "show.stderr", "propose.stdout", "propose.stderr", "decide.stdout", "decide.stderr",
        "retry-decide.stdout", "retry-decide.stderr", "terminal-journal.v1.json",
    ):
        record_retained_case_text(retained_case, f"commands/{name}", str(raw_streams.get(name) or ""))
    record_retained_case_json(retained_case, "semantic/proposal-payload.v1.json", dict(proposal_payload))
    if dry_run_receipt:
        record_retained_case_json(retained_case, "semantic/dry-run-receipt.v2.json", dict(dry_run_receipt))
    if create_payload:
        record_retained_case_json(retained_case, "semantic/create-payload.v1.json", dict(create_payload))


def _prepared_phase(
    *, repo_root: Path, invoke_cli: Callable[[Sequence[str], int], Any],
    retained_case: RetainedEvidenceCase, phase: str, request: Sequence[str],
    evidence: dict[str, Any],
) -> tuple[Any, Mapping[str, Any], Mapping[str, Any], float]:
    diagnostic = retained_case.staging_root / f"diagnostics-{phase}"
    allowance = int(PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS + GREENFIELD_COMPLETION_RESERVE_SECONDS)
    started = time.perf_counter()
    attempt = evidence.setdefault("prepare_attempts", {}).setdefault(phase, {})
    result = failure = None
    try:
        result = invoke_cli((
            "./.odylith/bin/odylith", "greenfield", "prepare", "--repo-root", ".",
            *request, "--diagnostic-evidence-dir", str(diagnostic), "--format", "json",
        ), allowance)
        wall_seconds = round(time.perf_counter() - started, 3)
        attempt.update(returncode=result.returncode, wall_seconds=wall_seconds)
        payload = json.loads(result.stdout)
        observation = payload.get("bounded_journey") if isinstance(payload, Mapping) else None
        if isinstance(observation, Mapping):
            attempt["observation"] = dict(observation)
        if result.returncode != 0 or not isinstance(payload, Mapping) or payload.get("mode") != "product_create_transaction":
            raise RuntimeError(f"lifecycle {phase} preparation did not return a pending sealed package")
        if not isinstance(observation, Mapping):
            raise RuntimeError(f"lifecycle {phase} preparation has no measured observation")
        stage = observation.get("elapsed_seconds")
        whole = observation.get("whole_journey_seconds")
        if any(type(value) is not float or not math.isfinite(value) or value <= 0 for value in (stage, whole)) or stage > whole + 1 or whole > wall_seconds + 1:
            raise RuntimeError(f"lifecycle {phase} preparation lacks measured stage/whole timing")
        return result, payload, observation, wall_seconds
    except BaseException as exc:
        failure = exc
        attempt["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        if "wall_seconds" not in attempt:
            attempt["wall_seconds"] = round(time.perf_counter() - started, 3)
        for stream in ("stdout", "stderr"):
            relative = f"commands/{phase}-prepare.{stream}"
            value = getattr(result if result is not None else failure, stream, "") or ""
            data = value if isinstance(value, bytes) else str(value).encode("utf-8")
            try:
                record_retained_case_bytes(retained_case, relative, data)
                attempt[f"{stream}_path"] = relative
            except Exception as exc:
                attempt.setdefault("retention_issues", []).append(str(exc))
                if failure is None:
                    raise
                failure.add_note(f"lifecycle {phase} {stream} retention failed: {exc}")


def _pending_phase(
    *, repo_root: Path, payload: Mapping[str, Any], expected_source: str,
) -> tuple[Any, Path, Path]:
    digest = payload["product_create_transaction"]["transaction_hash"]
    receipt = payload.get("completion_receipt")
    if not isinstance(receipt, str) or not receipt:
        raise ValueError("lifecycle preparation lacks its delivered completion receipt")
    path = resolve_pending_transaction(repo_root=repo_root, transaction_hash=digest, completion_receipt=receipt)
    # Standalone source-custody packages are valid product inputs but cannot prove
    # that this release journey delivered a bounded preparation receipt.
    if not (path.parent / ".bounded-journey.v1.json").is_file():
        raise ValueError("lifecycle release proof requires a bounded pending package")
    returned_path = Path(str(payload.get("transaction_file") or ""))
    if not returned_path.is_absolute():
        returned_path = repo_root / returned_path
    if returned_path.resolve() != path.resolve():
        raise ValueError("lifecycle preparation returned a foreign transaction file")
    transaction = load_compiled_product_create_transaction_file(path)
    if transaction.transaction_hash != digest or transaction.proposal["intent"]["prompt"] != expected_source:
        raise ValueError("lifecycle pending seal does not retain the exact source frame")
    receipt_path = Path(receipt).expanduser()
    if not receipt_path.is_absolute():
        receipt_path = repo_root / receipt_path
    receipt_path = receipt_path.resolve()
    if not receipt_path.is_relative_to(repo_root.resolve()):
        raise ValueError("lifecycle completion receipt is outside its consumer")
    return transaction, path, receipt_path


def _retain_pending(
    *, retained_case: RetainedEvidenceCase, phase: str, path: Path, receipt: Path,
) -> dict[str, Any]:
    paths = sorted(path.parent.iterdir()) + [receipt]
    snapshot = {}
    for artifact in paths:
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError("lifecycle pending artifact is unsafe")
        data = artifact.read_bytes()
        label = "completion-receipt.json" if artifact == receipt else artifact.name
        retained_path = f"semantic/lifecycle-{phase}/{label}"
        retained = record_retained_case_bytes(retained_case, retained_path, data)
        snapshot[str(artifact)] = {
            "sha256": hashlib.sha256(data).hexdigest(), "mode": artifact.stat().st_mode & 0o777,
            "retained_path": retained_path, "kind": "completion_receipt" if artifact == receipt else "pending",
            "retained_mode": retained.stat().st_mode & 0o777,
        }
    return snapshot


def _observe_pending(snapshot: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    observed, issues = {}, []
    for token, expected in snapshot.items():
        path = Path(token)
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("missing or unsafe artifact")
            observed[token] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": path.stat().st_mode & 0o777,
            }
            if observed[token] != {key: expected[key] for key in ("sha256", "mode")}:
                issues.append(f"lifecycle initial pending artifacts changed: {token}")
        except (OSError, ValueError) as exc:
            issues.append(f"lifecycle initial pending artifacts changed: {token}: {exc}")
    pending = {Path(token) for token, row in snapshot.items() if row["kind"] == "pending"}
    for directory in {path.parent for path in pending}:
        try:
            if set(directory.iterdir()) != {path for path in pending if path.parent == directory}:
                issues.append(f"lifecycle initial pending artifact membership changed: {directory}")
        except OSError as exc:
            issues.append(f"lifecycle initial pending artifact membership changed: {directory}: {exc}")
    return observed, tuple(issues)


def _require_pending_unchanged(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    observed, issues = _observe_pending(snapshot)
    if issues:
        raise ValueError("; ".join(issues))
    return observed


def _phase_model_evidence(
    *, retained_case: RetainedEvidenceCase, phase: str, observation: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    directory = retained_case.staging_root / f"diagnostics-{phase}"
    candidate_bytes = (directory / "candidate.stdout").read_bytes()
    ledger_bytes = (directory / "source-ledger-check.stdout").read_bytes()
    candidate, checked = json.loads(candidate_bytes), json.loads(ledger_bytes)
    if not isinstance(candidate, Mapping) or not isinstance(checked, Mapping) or not isinstance(checked.get("receipt"), Mapping):
        raise ValueError("lifecycle preparation did not retain candidate/source receipt evidence")
    if phase == "edited":
        # Existing scoring owns these names; initial diagnostics stay isolated.
        record_retained_case_bytes(retained_case, "semantic/host-candidate.raw.v1.json", candidate_bytes)
        record_retained_case_bytes(retained_case, "semantic/host-source-ledger-check.raw.v1.json", ledger_bytes)
        record_retained_case_json(retained_case, "semantic/host-authoring-observation.v1.json", dict(observation))
    return candidate, checked["receipt"]


def _require_preserved_duties(
    *, previous: Any, edited: Any, initial_source: str, correction: str,
) -> Mapping[str, Any]:
    prepared = prepare_model_authoring_evidence(prompt=initial_source, edit_evidence=correction)
    context = greenfield_edit_preservation_context(
        transaction_hash=previous.transaction_hash,
        prior_lifecycle=previous.proposal["semantic_model"]["source_lifecycle"],
        correction=prepared.edit_evidence, evidence_text=prepared.evidence_source,
    )
    receipt = edited.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]
    verified = verify_greenfield_source_duty_ledger_receipt(
        receipt, evidence_text=prepared.evidence_source, edit_preservation=context, allow_legacy_edit=False,
    )
    for disposition in verified["decision_set"]["edit_preservation"].values():
        if disposition["verdict"] != "preserved" or disposition["correction_authorization"] != "not_required":
            raise ValueError("additive lifecycle release family cannot change or remove prior duties")
    return verified


def _run_receipt_bound_edit(
    *, repo_root: Path, env: Mapping[str, str], profile_id: str,
    invoke_cli: Callable[[Sequence[str], int], Any], initial_prompt: str, correction: str,
    retained_case: RetainedEvidenceCase | None, raw_streams: dict[str, str] | None,
    evidence: dict[str, Any] | None,
) -> CompiledCreateExecution:
    if retained_case is None or evidence is None:
        raise ValueError("lifecycle release proof requires retained evidence and an evidence sink")
    if profile_id != STANDARD_PROFILE_ID:
        raise ValueError("installed lifecycle preparation requires its pinned standard model profile")
    started = time.perf_counter()
    initial_source = prepare_model_authoring_evidence(prompt=initial_prompt).evidence_source
    edited_evidence = prepare_model_authoring_evidence(prompt=initial_source, edit_evidence=correction)
    if not edited_evidence.edit_evidence:
        raise ValueError("lifecycle release proof requires a material correction")
    if raw_streams is not None:
        raw_streams["input.edit-evidence"] = correction
    record_retained_case_bytes(retained_case, "commands/lifecycle.initial-request", initial_prompt.encode("utf-8"))
    record_retained_case_bytes(retained_case, "commands/lifecycle.correction", correction.encode("utf-8"))
    evidence.update(version="odylith.greenfield.matrix.receipt-bound-edit.v1", status="started",
        timing_qualification="unqualified",
        outer_transport_allowance_seconds=PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS + GREENFIELD_COMPLETION_RESERVE_SECONDS,
        inner_diagnostic_cap_seconds=PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS,
        initial_request_sha256=hashlib.sha256(initial_prompt.encode("utf-8")).hexdigest(),
        correction_sha256=hashlib.sha256(correction.encode("utf-8")).hexdigest())
    snapshot, phase, failure, execution = {}, "initial_prepare", None, None
    try:
        _initial_result, initial_payload, initial_observation, initial_wall = _prepared_phase(
            repo_root=repo_root, invoke_cli=invoke_cli, retained_case=retained_case,
            phase="initial", request=("--prompt", initial_prompt), evidence=evidence,
        )
        phase = "initial_custody"
        previous, initial_path, initial_receipt = _pending_phase(
            repo_root=repo_root, payload=initial_payload, expected_source=initial_source,
        )
        snapshot = _retain_pending(retained_case=retained_case, phase="initial", path=initial_path, receipt=initial_receipt)
        evidence["initial"] = {"transaction_hash": previous.transaction_hash, "transaction_file": str(initial_path),
            "completion_receipt_path": str(initial_receipt), "source_sha256": hashlib.sha256(initial_source.encode()).hexdigest(),
            "artifacts": snapshot, "observation": dict(initial_observation), "wall_seconds": initial_wall}
        initial_candidate, initial_ledger = _phase_model_evidence(
            retained_case=retained_case, phase="initial", observation=initial_observation,
        )
        initial_model = model_profile_evidence(profile_id, env,
            observed=sealed_model_profile_observation(proposal=previous.proposal), stage_observation=initial_observation,
            raw_candidate=initial_candidate, source_duty_receipt=initial_ledger, expected_source=initial_source)
        initial_issues = authored_model_result_binding_issues(
            stage_observation=initial_observation, raw_candidate=initial_candidate,
            source_duty_receipt=initial_ledger, create_payload={"commit_manifest": previous.quality_manifest},
            expected_source=initial_source,
        )
        evidence["initial"].update(model_profile=initial_model, model_binding_issues=list(initial_issues))
        if initial_issues or initial_model.get("issues"):
            raise ValueError("lifecycle initial model/source custody did not pass")
        phase = "edited_prepare"
        edited_result, edited_payload, edited_observation, edited_wall = _prepared_phase(
            repo_root=repo_root, invoke_cli=invoke_cli, retained_case=retained_case, phase="edited",
            request=("--transaction-hash", previous.transaction_hash, "--completion-receipt", str(initial_receipt), "--edit", correction),
            evidence=evidence,
        )
        phase = "edited_custody"
        _require_pending_unchanged(snapshot)
        edited_source = edited_evidence.evidence_source
        edited, edited_path, edited_receipt = _pending_phase(
            repo_root=repo_root, payload=edited_payload, expected_source=edited_source,
        )
        if edited.transaction_hash == previous.transaction_hash:
            raise ValueError("equal or no-op seals cannot supply a committed lifecycle EDIT sample")
        edited_snapshot = _retain_pending(retained_case=retained_case, phase="edited", path=edited_path, receipt=edited_receipt)
        evidence["edited"] = {"transaction_hash": edited.transaction_hash, "transaction_file": str(edited_path),
            "completion_receipt_path": str(edited_receipt), "source_sha256": hashlib.sha256(edited_source.encode()).hexdigest(),
            "artifacts": edited_snapshot, "observation": dict(edited_observation), "wall_seconds": edited_wall}
        preserved = _require_preserved_duties(previous=previous, edited=edited, initial_source=initial_source, correction=correction)
        evidence["edited"]["source_duty_receipt"] = preserved
        _phase_model_evidence(retained_case=retained_case, phase="edited", observation=edited_observation)
        evidence["status"] = "edited_seal_prepared"
        phase = "edited_confirmation"
        execution = commit_precompiled_transaction(repo_root=repo_root,
            proposed=SimpleNamespace(returncode=edited_result.returncode, stdout=edited_result.stdout,
                stderr=edited_result.stderr, completion_receipt_path=str(edited_receipt)),
            proposal_seconds=edited_observation["elapsed_seconds"], invoke_cli=lambda command: invoke_cli(command, 60))
        try:
            evidence["initial_artifacts_after_confirm"] = _require_pending_unchanged(snapshot)
        except (OSError, ValueError) as exc:
            execution = replace(execution,
                failure=execution.failure if execution.failure is not None else SimpleNamespace(returncode=2, stdout="", stderr=str(exc)),
                output_contract_issues=(*execution.output_contract_issues, str(exc)))
        if execution.failure is None and not execution.output_contract_issues and not execution.terminal_proof_issues:
            journal = execution.terminal_journal
            if (execution.decision is not None and execution.retry_decision is not None
                    and journal.get("state") == "closed" and journal.get("lifecycle_state") == "CLOSED"
                    and journal.get("transaction_hash") == edited.transaction_hash and execution.commit_payload):
                evidence["status"] = "edited_seal_confirmed"
            else:
                issue = "lifecycle EDIT was not confirmed through its edited CLOSED journal"
                execution = replace(execution, failure=SimpleNamespace(returncode=2, stdout="", stderr=issue),
                    output_contract_issues=(*execution.output_contract_issues, issue))
        if execution.failure is not None:
            evidence["failure"] = {"phase": phase, "type": type(execution.failure).__name__,
                "message": str(getattr(execution.failure, "stderr", "") or ""),
                "returncode": getattr(execution.failure, "returncode", None)}
        elif execution.output_contract_issues or execution.terminal_proof_issues:
            evidence["failure"] = {"phase": phase, "type": "ExecutionProofError",
                "message": "; ".join((*execution.output_contract_issues, *execution.terminal_proof_issues))}
        if raw_streams is not None:
            raw_streams["timing.whole-journey-seconds"] = str(edited_observation["whole_journey_seconds"])
            raw_streams["terminal-journal.v1.json"] = execution.terminal_journal_text
            for label, result in (("propose", edited_result), ("decide", execution.decision), ("retry-decide", execution.retry_decision)):
                for stream in ("stdout", "stderr"):
                    raw_streams[f"{label}.{stream}"] = str(getattr(result, stream, "") or "")
    except BaseException as exc:
        failure = exc
        evidence["failure"] = {"phase": phase, "type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        if snapshot and "failure" in evidence:
            observed, custody_issues = _observe_pending(snapshot)
            evidence["initial_artifacts_on_failure"] = observed
            evidence["custody_issues"] = list(custody_issues)
        evidence["lifecycle_wall_seconds"] = round(time.perf_counter() - started, 3)
        endpoint = "edited CONFIRM, same-hash retry" if phase == "edited_confirmation" else f"{phase} failure"
        evidence["lifecycle_wall_scope"] = f"initial source framing through {endpoint} and prior-artifact readback; excludes show and final evidence serialization"
        try:
            record_retained_case_json(retained_case, "semantic/receipt-bound-edit.v1.json", evidence)
        except Exception as exc:
            if failure is not None:
                failure.add_note(f"lifecycle structured evidence retention failed: {exc}")
            elif execution is not None and execution.failure is not None:
                execution = replace(execution, output_contract_issues=(*execution.output_contract_issues, str(exc)))
            else:
                raise
    return execution
