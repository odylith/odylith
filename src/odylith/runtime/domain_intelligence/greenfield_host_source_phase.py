"""Own the source inventory, structural preflight and source-only verifier phase."""
from __future__ import annotations
import hashlib
import json
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from odylith.runtime.domain_intelligence.greenfield_host_flow import (
    PROVISIONAL_SOURCE_LEDGER_TIMEOUT_SECONDS, PROVISIONAL_SOURCE_DUTY_VERIFIER_TIMEOUT_SECONDS,
    PROVISIONAL_SOURCE_CHECK_TIMEOUT_SECONDS, _remaining, _fail, _single_json_object,
    _retain_host_output, _text_stream, _sha256_text, _is_within, _stream_excerpt,
    _invoke_installed_source_ledger_check, SOURCE_DUTY_DECISION_SET_VERSION,
    SOURCE_DUTY_LEDGER_RECEIPT_VERSION, preflight_greenfield_source_duty_ledger,
    expand_compact_source_duty_ledger, source_duty_entailment_task,
)
from odylith.runtime.domain_intelligence.greenfield_host_transport import (
    qualify_host_candidate_argv, _resolved_host_argv,
)

@dataclass(frozen=True)
class SourceDutyPhaseOutcome:
    ledger_path: Path
    decision_path: Path | None
    receipt: Mapping[str, Any] | None
    clarification: Any = None
    elapsed_seconds: float = 0.0


def run_source_duty_phase(*, flow, contract, source, host_workspace, host_argv,
                          deadline, observation, invoke_host, check_payload) -> SourceDutyPhaseOutcome:
    repo_root = flow.repo_root
    request = contract["request"]
    ledger_started = verifier_started = None
    try:
        ledger_contract = contract.get("source_ledger")
        if not isinstance(ledger_contract, Mapping) or set(ledger_contract) != {
            "task", "source_ledger_schema",
        } or not str(ledger_contract.get("task") or "").strip() or not isinstance(
            ledger_contract.get("source_ledger_schema"), Mapping
        ):
            _fail("host-native candidate contract has no closed source ledger",
                  observation=observation, stage="contract")
        ledger_schema_path = host_workspace / "source-ledger-schema.json"
        ledger_schema_path.write_text(
            json.dumps(ledger_contract["source_ledger_schema"], ensure_ascii=False,
                       sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8",
        )
        ledger_argv, ledger_request = qualify_host_candidate_argv(
            _resolved_host_argv(host_argv, candidate_schema_path=ledger_schema_path),
            trusted_codex_executable=flow.trusted_codex_executable,
            expected_model=flow.expected_model,
            expected_reasoning_effort=flow.expected_reasoning_effort,
            expected_output_schema=str(ledger_schema_path),
            path_value=str(flow.env.get("PATH") or os.environ.get("PATH") or ""),
        )
        observation["source_ledger_request"] = ledger_request
        observation["source_ledger_schema_sha256"] = _sha256_text(
            ledger_schema_path.read_text(encoding="utf-8")
        )
        observation["stage"] = "source-ledger"
        ledger_started = time.monotonic()
        ledger_timeout = deadline.request_timeout(
            _remaining(ledger_started, PROVISIONAL_SOURCE_LEDGER_TIMEOUT_SECONDS)
        )
        observation["host_invocations"] = 2
        observation["source_ledger_host_invocations"] = 1
        ledger_result = invoke_host(
            ledger_argv,
            contract_text=json.dumps(
                {"source_ledger": dict(ledger_contract), "request": request,
                 "authority_admission": check_payload},
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ),
            cwd=host_workspace,
            env=flow.env,
            timeout=ledger_timeout,
        )
        observation["source_ledger_returncode"] = int(
            getattr(ledger_result, "returncode", 1)
        )
        _retain_host_output(flow, observation, ledger_result, flow.retain_source_ledger_bytes)
        ledger_text = _text_stream(getattr(ledger_result, "stdout", ""))
        ledger_bytes = ledger_text.encode("utf-8")
        observation["source_ledger_output_sha256"] = hashlib.sha256(ledger_bytes).hexdigest()
        observation["source_ledger_output_bytes"] = len(ledger_bytes)
        if observation["source_ledger_returncode"] != 0:
            _fail("host-native source ledger command returned nonzero",
                  observation=observation, stage="source-ledger",
                  terminal_error=getattr(ledger_result, "lifecycle_observer_error", None))
        deadline.remaining()
        host_ledger = _single_json_object(ledger_text, label="source ledger")
        ledger_path = host_workspace / "source-ledger.json"
        ledger_path.write_bytes(ledger_bytes)
        observation["source_ledger_temp_outside_repo"] = not _is_within(
            ledger_path, repo_root
        )
        if not observation["source_ledger_temp_outside_repo"]:
            _fail("host-native source ledger path is inside the consumer repo",
                  observation=observation, stage="source-ledger-file")
        observation["stage"] = "source-ledger-preflight"
        preflight_timeout = deadline.request_timeout(PROVISIONAL_SOURCE_CHECK_TIMEOUT_SECONDS)
        observation["source_ledger_check_command_invocations"] = 1
        preflight = _invoke_installed_source_ledger_check(
            flow, ledger_path=ledger_path,
            remaining=preflight_timeout,
        )
        deadline.remaining()
        observation["source_ledger_preflight_returncode"] = int(
            getattr(preflight, "returncode", 1)
        )
        preflight_text = _text_stream(getattr(preflight, "stdout", ""))
        if flow.retain_source_ledger_preflight_bytes is not None:
            flow.retain_source_ledger_preflight_bytes(preflight_text.encode("utf-8"))
            deadline.remaining()
        observation["source_ledger_preflight_stdout_sha256"] = _sha256_text(preflight_text)
        if observation["source_ledger_preflight_returncode"] != 0:
            _fail("installed source ledger preflight returned nonzero",
                  observation=observation, stage="source-ledger-preflight",
                  detail=_stream_excerpt(preflight))
        preflight_payload = _single_json_object(
            preflight_text, label="source ledger preflight"
        )
        observation["source_ledger_preflight_mode"] = preflight_payload.get("mode")
        ledger_elapsed = time.monotonic() - ledger_started

        observation["source_ledger_elapsed_seconds"] = round(ledger_elapsed, 3)
        if preflight_payload.get("mode") == "clarification_required":
            observation["response_kind"] = "clarification_required"
            observation["proposal_mode"] = "clarification_required"
            observation["candidate_temp_cleaned"] = True
            observation["status"] = "passed"
            return SourceDutyPhaseOutcome(ledger_path, None, None, preflight, ledger_elapsed)
        preflight_receipt = preflight_payload.get("preflight")
        decision_task = preflight_payload.get("decision_task")
        # Share the compiler's custody owners: the task's hashes live in the
        # preflight and schema, rather than duplicated top-level task fields.
        expected_preflight = preflight_greenfield_source_duty_ledger(
            expand_compact_source_duty_ledger(host_ledger, evidence_text=source),
            evidence_text=source,
        )
        expected_task = source_duty_entailment_task(
            expected_preflight, evidence_text=source,
        )
        if (preflight_payload.get("mode") != "source_duty_preflight"
                or not isinstance(preflight_receipt, Mapping)
                or preflight_receipt.get("source_sha256") != observation["source_sha256"]
                or preflight_receipt != expected_preflight
                or decision_task != expected_task):
            _fail("installed source ledger preflight lacks a bound decision task",
                  observation=observation, stage="source-ledger-preflight")
        observation["source_duty_verifier_task_sha256"] = decision_task["verifier_task_sha256"]
        decision_schema_path = host_workspace / "source-duty-decision-schema.json"
        decision_schema_path.write_text(
            json.dumps(decision_task["decision_set_schema"], ensure_ascii=False,
                       sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8",
        )
        decision_argv, decision_request = qualify_host_candidate_argv(
            _resolved_host_argv(host_argv, candidate_schema_path=decision_schema_path),
            trusted_codex_executable=flow.trusted_codex_executable,
            expected_model=flow.expected_model,
            expected_reasoning_effort=flow.expected_reasoning_effort,
            expected_output_schema=str(decision_schema_path),
            path_value=str(flow.env.get("PATH") or os.environ.get("PATH") or ""),
        )
        observation["source_duty_verifier_request"] = decision_request
        observation["source_duty_decision_schema_sha256"] = _sha256_text(
            decision_schema_path.read_text(encoding="utf-8")
        )
        observation["stage"] = "source-duty-verifier"
        verifier_started = time.monotonic()
        verifier_timeout = deadline.request_timeout(
            _remaining(verifier_started, PROVISIONAL_SOURCE_DUTY_VERIFIER_TIMEOUT_SECONDS)
        )
        observation["host_invocations"] = 3
        observation["source_duty_verifier_host_invocations"] = 1
        decision_result = invoke_host(
            decision_argv,
            contract_text=json.dumps(dict(decision_task), ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":")),
            cwd=host_workspace, env=flow.env,
            timeout=verifier_timeout,
        )
        observation["source_duty_verifier_returncode"] = int(
            getattr(decision_result, "returncode", 1)
        )
        _retain_host_output(flow, observation, decision_result, flow.retain_source_duty_decision_bytes)
        decision_text = _text_stream(getattr(decision_result, "stdout", ""))
        decision_bytes = decision_text.encode("utf-8")
        observation["source_duty_decision_output_sha256"] = hashlib.sha256(decision_bytes).hexdigest()
        observation["source_duty_decision_output_bytes"] = len(decision_bytes)
        if observation["source_duty_verifier_returncode"] != 0:
            _fail("host-native source duty verifier returned nonzero",
                  observation=observation, stage="source-duty-verifier",
                  terminal_error=getattr(decision_result, "lifecycle_observer_error", None))
        deadline.remaining()
        decision_set = _single_json_object(decision_text, label="source duty decision set")
        source_completeness = decision_set.get("source_completeness")
        observation["source_completeness_verdict"] = (
            str(source_completeness.get("verdict") or "")
            if isinstance(source_completeness, Mapping) else "missing"
        )
        omissions = (
            source_completeness.get("omissions")
            if isinstance(source_completeness, Mapping) else None
        )
        observation["source_completeness_omission_count"] = (
            len(omissions) if isinstance(omissions, list) else -1
        )
        decision_path = host_workspace / "source-duty-decisions.json"
        decision_path.write_bytes(decision_bytes)
        observation["source_duty_decision_temp_outside_repo"] = not _is_within(
            decision_path, repo_root
        )
        if not observation["source_duty_decision_temp_outside_repo"]:
            _fail("host-native source duty decision path is inside the consumer repo",
                  observation=observation, stage="source-duty-decision-file")
        observation["stage"] = "source-ledger-check"
        check_timeout = deadline.request_timeout(PROVISIONAL_SOURCE_CHECK_TIMEOUT_SECONDS)
        observation["source_ledger_check_command_invocations"] = 2
        ledger_check = _invoke_installed_source_ledger_check(
            flow, ledger_path=ledger_path, decision_path=decision_path,
            remaining=check_timeout,
        )
        deadline.remaining()
        observation["source_ledger_check_returncode"] = int(
            getattr(ledger_check, "returncode", 1)
        )
        ledger_check_text = _text_stream(getattr(ledger_check, "stdout", ""))
        if flow.retain_source_ledger_check_bytes is not None:
            flow.retain_source_ledger_check_bytes(ledger_check_text.encode("utf-8"))
            deadline.remaining()
        observation["source_ledger_check_stdout_sha256"] = _sha256_text(ledger_check_text)
        if observation["source_ledger_check_returncode"] != 0:
            _fail("installed source ledger decision check returned nonzero",
                  observation=observation, stage="source-ledger-check")
        ledger_check_payload = _single_json_object(
            ledger_check_text, label="source ledger decision check"
        )
        observation["source_ledger_check_mode"] = ledger_check_payload.get("mode")
        receipt = ledger_check_payload.get("receipt")
        if (ledger_check_payload.get("mode") != "source_duty_admitted"
                or not isinstance(receipt, Mapping)
                or receipt.get("version") != SOURCE_DUTY_LEDGER_RECEIPT_VERSION
                or receipt.get("source_sha256") != observation["source_sha256"]
                or receipt.get("ledger_sha256") != preflight_receipt.get("ledger_sha256")
                or receipt.get("verifier_task_sha256") != observation["source_duty_verifier_task_sha256"]
                or decision_set.get("version") != SOURCE_DUTY_DECISION_SET_VERSION
                or receipt.get("decision_set") != decision_set
                or not isinstance(decision_set.get("source_completeness"), Mapping)
                or decision_set["source_completeness"].get("verdict") != "yes"
                or decision_set["source_completeness"].get("omissions") != []
                or not isinstance(receipt.get("decision_set_sha256"), str)
                or not receipt["decision_set_sha256"]):
            _fail("installed source ledger decision check did not admit",
                  observation=observation, stage="source-ledger-check")
        ledger_path.write_text(
            json.dumps(dict(receipt), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n", encoding="utf-8",
        )
        verifier_elapsed = time.monotonic() - verifier_started

        observation["source_duty_verifier_elapsed_seconds"] = round(verifier_elapsed, 3)
        observation["source_ledger_sha256"] = str(receipt.get("ledger_sha256") or "")
        observation["source_duty_decision_set_sha256"] = receipt["decision_set_sha256"]
        return SourceDutyPhaseOutcome(ledger_path, decision_path, receipt,
                                      elapsed_seconds=ledger_elapsed + verifier_elapsed)
    finally:
        if ledger_started is not None and "source_ledger_elapsed_seconds" not in observation:
            observation["source_ledger_elapsed_seconds"] = round(time.monotonic()-ledger_started, 3)
        if verifier_started is not None and "source_duty_verifier_elapsed_seconds" not in observation:
            observation["source_duty_verifier_elapsed_seconds"] = round(time.monotonic()-verifier_started, 3)
