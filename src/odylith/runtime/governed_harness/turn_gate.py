"""Product-owned Turn Gate decisions for governed harness callers."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "odylith.turn-gate.v1"
RECEIPT_SOURCE = "product_turn_gate"
DECISION_TYPES = {
    "answer_only",
    "early_exit_proof",
    "diagnostic",
    "bounded_edit",
    "open_ended_implementation",
    "unsafe_needs_user_decision",
}
GATE_MODES = {"observe", "advise", "enforce"}
TOOL_OUTCOMES = {"allow", "deny", "ask", "defer", "rewrite"}


@dataclass(frozen=True)
class EvidenceGateReport:
    selected_evidence_refs: list[str]
    validator_selectors: list[str]
    proof_state_tier: str
    cache_key: str
    cache_hit_status: str
    sufficiency_verdict: bool
    sufficiency_basis: str


@dataclass(frozen=True)
class ExecutionCapsule:
    capsule_id: str
    owned_paths: list[str]
    denied_paths: list[str]
    allowed_commands: list[str]
    validation_obligations: list[str]
    route_constraints: list[str]
    dirty_worktree_constraints: list[str]
    completion_claim_limits: list[str]


@dataclass(frozen=True)
class HarnessReceipt:
    receipt_id: str
    decision_id: str
    source: str
    host_trace_ids: list[str]
    proof_card: dict[str, Any]
    benchmark_row_id: str
    cross_engine_evidence_ids: list[str]


@dataclass(frozen=True)
class TurnGateDecision:
    schema_version: str
    decision_id: str
    mode: str
    host: str
    repo_head: str
    dirty_fingerprint: str
    prompt_class: str
    decision_type: str
    confidence: float
    evidence_report: EvidenceGateReport
    execution_capsule: ExecutionCapsule
    receipt: HarnessReceipt

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolGateDecision:
    schema_version: str
    decision_id: str
    outcome: str
    reason: str
    rewritten_input: dict[str, Any]
    capsule_id: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_turn(
    *,
    repo_root: str | Path,
    host: str,
    mode: str,
    prompt_payload: Mapping[str, Any],
    persist_receipt: bool = False,
) -> TurnGateDecision:
    resolved_repo_root = Path(repo_root).expanduser().resolve()
    normalized_mode = _normalize_token(mode, default="advise", allowed=GATE_MODES)
    normalized_host = _single_line(host) or "unknown"
    payload = dict(prompt_payload or {})
    repo_head = _repo_head(resolved_repo_root)
    dirty_fingerprint = _dirty_fingerprint(resolved_repo_root)
    prompt_class = _prompt_class(payload)
    validation_commands = _string_list(payload.get("validation_commands"))
    focused_checks = _string_list(payload.get("focused_local_checks"))
    owned_paths = _string_list(payload.get("owned_paths")) or _string_list(payload.get("expected_write_paths"))
    denied_paths = _string_list(payload.get("denied_paths"))
    allowed_commands = _dedupe([*focused_checks, *validation_commands, *_string_list(payload.get("allowed_commands"))])
    non_mutating_allowed = _non_mutating_closure_allowed(payload)
    evidence_sufficient, sufficiency_basis = _early_exit_evidence_sufficient(
        payload=payload,
        focused_checks=focused_checks,
        validation_commands=validation_commands,
    )
    if _unsafe_prompt(payload):
        decision_type = "unsafe_needs_user_decision"
        confidence = 0.88
    elif non_mutating_allowed and evidence_sufficient:
        decision_type = "early_exit_proof"
        confidence = 0.94
        owned_paths = []
    elif prompt_class == "answer_only":
        decision_type = "answer_only"
        confidence = 0.82
    elif owned_paths:
        decision_type = "bounded_edit"
        confidence = 0.78
    elif validation_commands:
        decision_type = "diagnostic"
        confidence = 0.72
    else:
        decision_type = "open_ended_implementation"
        confidence = 0.62

    cache_key = _stable_hash(
        {
            "repo_head": repo_head,
            "dirty_fingerprint": dirty_fingerprint,
            "prompt_class": prompt_class,
            "validation_commands": validation_commands,
            "focused_checks": focused_checks,
            "owned_paths": owned_paths,
        }
    )
    capsule_id = "capsule:" + cache_key[:16]
    decision_id = "tg:" + _stable_hash(
        {
            "schema_version": SCHEMA_VERSION,
            "host": normalized_host,
            "mode": normalized_mode,
            "repo_head": repo_head,
            "dirty_fingerprint": dirty_fingerprint,
            "prompt_class": prompt_class,
            "decision_type": decision_type,
            "cache_key": cache_key,
        }
    )[:24]
    receipt_id = "receipt:" + decision_id.removeprefix("tg:")
    evidence_report = EvidenceGateReport(
        selected_evidence_refs=_evidence_refs(payload=payload, focused_checks=focused_checks),
        validator_selectors=validation_commands,
        proof_state_tier="validator_backed" if decision_type == "early_exit_proof" else "policy_advisory",
        cache_key=cache_key,
        cache_hit_status=str(payload.get("cache_hit_status", "")).strip() or "not_checked",
        sufficiency_verdict=bool(decision_type == "early_exit_proof"),
        sufficiency_basis=sufficiency_basis if decision_type == "early_exit_proof" else "not_applicable",
    )
    capsule = ExecutionCapsule(
        capsule_id=capsule_id,
        owned_paths=owned_paths,
        denied_paths=denied_paths,
        allowed_commands=allowed_commands,
        validation_obligations=validation_commands,
        route_constraints=_route_constraints(decision_type=decision_type, payload=payload),
        dirty_worktree_constraints=_dirty_constraints(dirty_fingerprint=dirty_fingerprint),
        completion_claim_limits=_completion_claim_limits(decision_type=decision_type, validation_commands=validation_commands),
    )
    receipt = HarnessReceipt(
        receipt_id=receipt_id,
        decision_id=decision_id,
        source=RECEIPT_SOURCE,
        host_trace_ids=_string_list(payload.get("host_trace_ids")),
        proof_card=_proof_card(
            decision_type=decision_type,
            repo_head=repo_head,
            dirty_fingerprint=dirty_fingerprint,
            evidence_report=evidence_report,
            capsule=capsule,
        ),
        benchmark_row_id=_single_line(payload.get("benchmark_row_id")),
        cross_engine_evidence_ids=_cross_engine_ids(payload),
    )
    decision = TurnGateDecision(
        schema_version=SCHEMA_VERSION,
        decision_id=decision_id,
        mode=normalized_mode,
        host=normalized_host,
        repo_head=repo_head,
        dirty_fingerprint=dirty_fingerprint,
        prompt_class=prompt_class,
        decision_type=decision_type,
        confidence=confidence,
        evidence_report=evidence_report,
        execution_capsule=capsule,
        receipt=receipt,
    )
    if persist_receipt:
        _write_receipt(repo_root=resolved_repo_root, decision=decision)
    return decision


def check_tool(
    *,
    repo_root: str | Path,
    host: str,
    decision_id: str,
    tool_input: Mapping[str, Any],
) -> ToolGateDecision:
    resolved_repo_root = Path(repo_root).expanduser().resolve()
    decision = _load_decision(repo_root=resolved_repo_root, decision_id=decision_id)
    if not decision:
        return ToolGateDecision(
            schema_version=SCHEMA_VERSION,
            decision_id=_single_line(decision_id),
            outcome="defer",
            reason="missing_turn_gate_receipt",
            rewritten_input={},
            capsule_id="",
        )
    capsule = _capsule_from_decision(decision)
    tool_rows = dict(tool_input or {})
    tool_name = _single_line(tool_rows.get("tool") or tool_rows.get("name")).lower()
    command = _single_line(tool_rows.get("command") or _mapping_get(tool_rows.get("args"), "command"))
    path = _single_line(tool_rows.get("path") or _mapping_get(tool_rows.get("args"), "path"))
    if _path_denied(path=path, denied_paths=capsule.denied_paths):
        return _tool_decision(decision_id=decision_id, outcome="deny", reason="path_denied_by_capsule", capsule=capsule)
    if command and _command_allowed(command=command, allowed_commands=capsule.allowed_commands):
        return _tool_decision(decision_id=decision_id, outcome="allow", reason="command_allowed_by_capsule", capsule=capsule)
    if path and _path_owned(path=path, owned_paths=capsule.owned_paths):
        return _tool_decision(decision_id=decision_id, outcome="allow", reason="path_owned_by_capsule", capsule=capsule)
    if tool_name in {"edit", "write", "multiedit", "apply_patch"} or path:
        return _tool_decision(decision_id=decision_id, outcome="ask", reason="write_outside_capsule_requires_decision", capsule=capsule)
    if command:
        return _tool_decision(decision_id=decision_id, outcome="ask", reason="command_not_declared_in_capsule", capsule=capsule)
    return _tool_decision(decision_id=decision_id, outcome="allow", reason=f"tool_allowed_for_host:{_single_line(host) or 'unknown'}", capsule=capsule)


def check_stop(
    *,
    repo_root: str | Path,
    host: str,
    decision_id: str,
    transcript_text: str,
) -> dict[str, Any]:
    resolved_repo_root = Path(repo_root).expanduser().resolve()
    decision = _load_decision(repo_root=resolved_repo_root, decision_id=decision_id)
    if not decision:
        return {
            "schema_version": SCHEMA_VERSION,
            "decision_id": _single_line(decision_id),
            "outcome": "defer",
            "reason": "missing_turn_gate_receipt",
            "host": _single_line(host) or "unknown",
        }
    capsule = _capsule_from_decision(decision)
    text = _single_line(transcript_text).lower()
    claims_done = any(token in text for token in ("fixed", "resolved", "done", "complete", "completed"))
    if decision.get("decision_type") == "early_exit_proof":
        return {
            "schema_version": SCHEMA_VERSION,
            "decision_id": _single_line(decision_id),
            "outcome": "allow",
            "reason": "early_exit_proof_already_receipted",
            "host": _single_line(host) or "unknown",
        }
    if claims_done and capsule.validation_obligations and "validation" not in text and "test" not in text:
        return {
            "schema_version": SCHEMA_VERSION,
            "decision_id": _single_line(decision_id),
            "outcome": "deny",
            "reason": "completion_claim_missing_validation_obligation",
            "host": _single_line(host) or "unknown",
            "validation_obligations": capsule.validation_obligations,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_id": _single_line(decision_id),
        "outcome": "allow",
        "reason": "stop_claim_within_capsule",
        "host": _single_line(host) or "unknown",
    }


def non_mutating_completion_admitted(
    *,
    prompt_payload: Mapping[str, Any],
    structured_output: Mapping[str, Any],
    candidate_write_paths: Sequence[str],
    required_path_misses: Sequence[str],
    focused_check_result: Mapping[str, Any],
    validator_result: Mapping[str, Any],
) -> bool:
    payload = dict(prompt_payload or {})
    if not _non_mutating_closure_allowed(payload):
        return False
    focused_checks = _string_list(payload.get("focused_local_checks"))
    validation_commands = _string_list(payload.get("validation_commands"))
    if not _focused_checks_cover_contract(
        payload=payload,
        focused_checks=focused_checks,
        validation_commands=validation_commands,
    ):
        return False
    if any(str(token).strip() for token in candidate_write_paths):
        return False
    if any(str(token).strip() for token in required_path_misses):
        return False
    if not (
        _validator_passed(focused_check_result)
        or _focused_check_failure_matches_validator_failure(
            focused_check_result=focused_check_result,
            validator_result=validator_result,
        )
    ):
        return False
    if _validator_passed(validator_result):
        return False
    return _structured_output_declares_external_drift(structured_output) or _validator_tail_declares_external_drift(
        validator_result
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv or sys.argv[1:]))
    if args.turn_gate_command == "decide":
        payload = _read_json_arg(args.prompt_json, label="--prompt-json")
        decision = decide_turn(
            repo_root=args.repo_root,
            host=args.host,
            mode=args.mode,
            prompt_payload=payload,
            persist_receipt=True,
        )
        _emit(decision.as_dict(), as_json=bool(args.as_json))
        return 0
    if args.turn_gate_command == "tool-check":
        tool_input = _read_json_arg(args.tool_input_json, label="--tool-input-json")
        decision = check_tool(
            repo_root=args.repo_root,
            host=args.host,
            decision_id=args.decision_id,
            tool_input=tool_input,
        )
        _emit(decision.as_dict(), as_json=bool(args.as_json))
        return 0 if decision.outcome in {"allow", "ask", "rewrite"} else 2
    transcript_text = _read_text_file(args.transcript)
    stop_decision = check_stop(
        repo_root=args.repo_root,
        host=args.host,
        decision_id=args.decision_id,
        transcript_text=transcript_text,
    )
    _emit(stop_decision, as_json=bool(args.as_json))
    return 0 if stop_decision.get("outcome") in {"allow", "ask"} else 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odylith turn-gate", description="Evaluate product Turn Gate decisions.")
    subparsers = parser.add_subparsers(dest="turn_gate_command", required=True)
    decide = subparsers.add_parser("decide", help="Classify a turn and build a governed harness decision.")
    decide.add_argument("--repo-root", default=".", help="Repository root.")
    decide.add_argument("--host", required=True, help="Host family or adapter.")
    decide.add_argument("--mode", choices=sorted(GATE_MODES), default="advise", help="Gate operating mode.")
    decide.add_argument("--prompt-json", required=True, help="Prompt payload JSON or '-' for stdin.")
    decide.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON.")
    tool_check = subparsers.add_parser("tool-check", help="Evaluate one host tool call against a Turn Gate capsule.")
    tool_check.add_argument("--repo-root", default=".", help="Repository root.")
    tool_check.add_argument("--host", required=True, help="Host family or adapter.")
    tool_check.add_argument("--decision-id", required=True, help="Turn Gate decision id.")
    tool_check.add_argument("--tool-input-json", required=True, help="Tool input JSON or '-' for stdin.")
    tool_check.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON.")
    stop_check = subparsers.add_parser("stop-check", help="Evaluate finalization claims against Turn Gate proof.")
    stop_check.add_argument("--repo-root", default=".", help="Repository root.")
    stop_check.add_argument("--host", required=True, help="Host family or adapter.")
    stop_check.add_argument("--decision-id", required=True, help="Turn Gate decision id.")
    stop_check.add_argument("--transcript", required=True, help="Transcript path to inspect.")
    stop_check.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON.")
    return parser


def _emit(payload: Mapping[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print("turn-gate")
    for key in ("decision_id", "decision_type", "outcome", "reason", "mode", "host"):
        value = payload.get(key)
        if value not in (None, "", []):
            print(f"- {key}: {value}")


def _read_json_arg(value: str, *, label: str) -> dict[str, Any]:
    raw = sys.stdin.read() if str(value).strip() == "-" else str(value)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit(f"{label} must decode to a JSON object")
    return parsed


def _read_text_file(path: str) -> str:
    resolved = Path(path).expanduser()
    try:
        return resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"--transcript could not be read: {exc}") from exc


def _write_receipt(*, repo_root: Path, decision: TurnGateDecision) -> None:
    target = _receipt_dir(repo_root) / (decision.decision_id.replace(":", "_") + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(decision.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_decision(*, repo_root: Path, decision_id: str) -> dict[str, Any]:
    target = _receipt_dir(repo_root) / (_single_line(decision_id).replace(":", "_") + ".json")
    try:
        parsed = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _receipt_dir(repo_root: Path) -> Path:
    return repo_root / ".odylith" / "runtime" / "governed-harness" / "receipts"


def _capsule_from_decision(decision: Mapping[str, Any]) -> ExecutionCapsule:
    raw = decision.get("execution_capsule")
    rows = raw if isinstance(raw, Mapping) else {}
    return ExecutionCapsule(
        capsule_id=_single_line(rows.get("capsule_id")),
        owned_paths=_string_list(rows.get("owned_paths")),
        denied_paths=_string_list(rows.get("denied_paths")),
        allowed_commands=_string_list(rows.get("allowed_commands")),
        validation_obligations=_string_list(rows.get("validation_obligations")),
        route_constraints=_string_list(rows.get("route_constraints")),
        dirty_worktree_constraints=_string_list(rows.get("dirty_worktree_constraints")),
        completion_claim_limits=_string_list(rows.get("completion_claim_limits")),
    )


def _tool_decision(*, decision_id: str, outcome: str, reason: str, capsule: ExecutionCapsule) -> ToolGateDecision:
    return ToolGateDecision(
        schema_version=SCHEMA_VERSION,
        decision_id=_single_line(decision_id),
        outcome=_normalize_token(outcome, default="defer", allowed=TOOL_OUTCOMES),
        reason=_single_line(reason),
        rewritten_input={},
        capsule_id=capsule.capsule_id,
    )


def _repo_head(repo_root: Path) -> str:
    return _git_output(repo_root, ["rev-parse", "--short=12", "HEAD"]) or "unavailable"


def _dirty_fingerprint(repo_root: Path) -> str:
    status = _git_output(repo_root, ["status", "--short"])
    if status:
        return "dirty:" + hashlib.sha256(status.encode("utf-8")).hexdigest()[:16]
    if _git_output(repo_root, ["rev-parse", "--is-inside-work-tree"]) == "true":
        return "clean"
    return "nogit"


def _git_output(repo_root: Path, args: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    return str(completed.stdout or "").strip()


def _prompt_class(payload: Mapping[str, Any]) -> str:
    explicit = _single_line(payload.get("prompt_class"))
    if explicit:
        return explicit
    policy_hints = payload.get("policy_hints")
    if isinstance(policy_hints, Mapping) and _truthy(policy_hints.get("answer_only")):
        return "answer_only"
    text = _single_line(payload.get("prompt")).lower()
    if text.startswith(("what ", "why ", "explain ", "summarize ", "do we ", "does ")):
        return "answer_only"
    if _string_list(payload.get("expected_write_paths")) or _string_list(payload.get("owned_paths")):
        return "implementation"
    if _string_list(payload.get("validation_commands")):
        return "diagnostic"
    return "open_ended"


def _unsafe_prompt(payload: Mapping[str, Any]) -> bool:
    text = _single_line(payload.get("prompt")).lower()
    return any(token in text for token in ("rm -rf /", "delete everything", "ignore safety", "disable guard"))


def _non_mutating_closure_allowed(payload: Mapping[str, Any]) -> bool:
    policy_hints = payload.get("policy_hints")
    if isinstance(policy_hints, Mapping) and _truthy(policy_hints.get("non_mutating_closure_allowed")):
        return True
    return _truthy(payload.get("non_mutating_closure_allowed")) or _truthy(payload.get("allow_noop_completion"))


def _early_exit_evidence_sufficient(
    *,
    payload: Mapping[str, Any],
    focused_checks: Sequence[str],
    validation_commands: Sequence[str],
) -> tuple[bool, str]:
    focused_result = payload.get("focused_check_result")
    if not isinstance(focused_result, Mapping):
        return False, "missing_focused_check_result"
    if not _validator_passed(focused_result):
        return False, "focused_check_result_not_passed"
    if not _focused_checks_cover_contract(
        payload=payload,
        focused_checks=focused_checks,
        validation_commands=validation_commands,
    ):
        return False, "focused_checks_do_not_cover_contract"
    return True, "validator_backed_non_mutating_closure"


def _focused_checks_cover_contract(
    *,
    payload: Mapping[str, Any],
    focused_checks: Sequence[str],
    validation_commands: Sequence[str],
) -> bool:
    policy_hints = payload.get("policy_hints")
    if isinstance(policy_hints, Mapping) and _truthy(policy_hints.get("focused_checks_cover_contract")):
        return bool(focused_checks)
    return bool(focused_checks) and list(focused_checks) == list(validation_commands)


def _validator_passed(result: Mapping[str, Any]) -> bool:
    return _single_line(result.get("status")) in {"passed", "not_applicable"}


def _failed_validator_command_signatures(result: Mapping[str, Any]) -> set[tuple[str, int]]:
    rows = result.get("results")
    if not isinstance(rows, list):
        return set()
    signatures: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, Mapping) or _single_line(row.get("status")) != "failed":
            continue
        command = _single_line(row.get("command"))
        if not command:
            continue
        try:
            exit_code = int(row.get("exit_code", 0) or 0)
        except (TypeError, ValueError):
            exit_code = 0
        signatures.add((command, exit_code))
    return signatures


def _focused_check_failure_matches_validator_failure(
    *,
    focused_check_result: Mapping[str, Any],
    validator_result: Mapping[str, Any],
) -> bool:
    if _validator_passed(focused_check_result) or _validator_passed(validator_result):
        return False
    focused_failures = _failed_validator_command_signatures(focused_check_result)
    validator_failures = _failed_validator_command_signatures(validator_result)
    return bool(focused_failures) and focused_failures.issubset(validator_failures)


def _structured_output_declares_external_drift(structured_output: Mapping[str, Any]) -> bool:
    text = " ".join(
        token
        for token in (
            _single_line(structured_output.get("summary")),
            _single_line(structured_output.get("validation_summary")),
            " ".join(_string_list(structured_output.get("notes"))),
        )
        if token
    ).lower()
    if not text:
        return False
    boundary = any(token in text for token in ("outside", "out-of-scope", "out of scope", "pre-existing", "stale"))
    scoped = any(token in text for token in ("allowed", "permitted", "slice", "working set", "bounded", "scope"))
    return boundary and scoped


def _validator_tail_declares_external_drift(validator_result: Mapping[str, Any]) -> bool:
    rows = validator_result.get("results")
    if not isinstance(rows, list):
        return False
    text_parts: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        text_parts.extend([_single_line(row.get("stdout_tail")), _single_line(row.get("stderr_tail"))])
    text = " ".join(text_parts).lower()
    return "without rewriting governed truth" in text and "odylith/" in text


def _proof_card(
    *,
    decision_type: str,
    repo_head: str,
    dirty_fingerprint: str,
    evidence_report: EvidenceGateReport,
    capsule: ExecutionCapsule,
) -> dict[str, Any]:
    return {
        "label": "early-exit proof" if decision_type == "early_exit_proof" else "turn-gate decision",
        "decision_type": decision_type,
        "repo_head": repo_head,
        "workspace_state": dirty_fingerprint,
        "checks": list(evidence_report.validator_selectors),
        "evidence": list(evidence_report.selected_evidence_refs),
        "confidence_basis": evidence_report.sufficiency_basis,
        "owned_paths": list(capsule.owned_paths),
    }


def _route_constraints(*, decision_type: str, payload: Mapping[str, Any]) -> list[str]:
    explicit = _string_list(payload.get("route_constraints"))
    if explicit:
        return explicit
    if decision_type == "early_exit_proof":
        return ["do_not_call_host_model", "do_not_mutate_workspace"]
    if decision_type == "bounded_edit":
        return ["stay_within_owned_paths", "run_validation_obligations"]
    if decision_type == "unsafe_needs_user_decision":
        return ["ask_user_before_side_effects"]
    return ["preserve_turn_gate_receipt"]


def _dirty_constraints(*, dirty_fingerprint: str) -> list[str]:
    if dirty_fingerprint == "clean":
        return []
    if dirty_fingerprint == "nogit":
        return ["repo_state_unavailable"]
    return ["preserve_unowned_dirty_worktree_state"]


def _completion_claim_limits(*, decision_type: str, validation_commands: Sequence[str]) -> list[str]:
    if decision_type == "early_exit_proof":
        return ["claim_only_validator_backed_non_mutating_closure"]
    if validation_commands:
        return ["do_not_claim_done_until_validation_obligations_are_satisfied"]
    return ["qualify_completion_claim_with_available_evidence"]


def _evidence_refs(*, payload: Mapping[str, Any], focused_checks: Sequence[str]) -> list[str]:
    refs = _string_list(payload.get("selected_evidence_refs"))
    command_refs = [f"validator:{command}" for command in focused_checks]
    return _dedupe([*refs, *command_refs])


def _cross_engine_ids(payload: Mapping[str, Any]) -> list[str]:
    ids = _string_list(payload.get("cross_engine_evidence_ids"))
    for key in ("context_packet_id", "execution_snapshot_id", "proof_state_lane_id"):
        value = _single_line(payload.get(key))
        if value:
            ids.append(value)
    return _dedupe(ids)


def _path_denied(*, path: str, denied_paths: Sequence[str]) -> bool:
    return bool(path) and any(path == denied or path.startswith(denied.rstrip("/") + "/") for denied in denied_paths)


def _path_owned(*, path: str, owned_paths: Sequence[str]) -> bool:
    return bool(path) and any(path == owned or path.startswith(owned.rstrip("/") + "/") for owned in owned_paths)


def _command_allowed(*, command: str, allowed_commands: Sequence[str]) -> bool:
    return bool(command) and any(command == allowed or command.startswith(allowed + " ") for allowed in allowed_commands)


def _mapping_get(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, Mapping) else ""


def _normalize_token(value: object, *, default: str, allowed: set[str]) -> str:
    token = _single_line(value)
    return token if token in allowed else default


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple | set):
        return []
    return _dedupe([_single_line(token) for token in value])


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        token = _single_line(value)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _single_line(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _stable_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
