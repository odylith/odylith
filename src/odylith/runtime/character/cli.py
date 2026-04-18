"""CLI helpers for the Odylith character layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.character import runtime as character_runtime
from odylith.runtime.character.contract import (
    CHARACTER_CONTRACT,
    FAMILY,
    HARD_LAWS,
    LEARNING_OUTCOMES,
    RETENTION_CLASSES,
)
from odylith.runtime.character.decision import evaluate_character_move
from odylith.runtime.character.support import SUPPORTED_HOST_FAMILIES, SUPPORTED_LANES, host_lane_matrix


DECISION_CACHE_RELATIVE = Path(".odylith/cache/agent-operating-character/decisions")

_HUMAN_LAW_REASONS = {
    "supported_host_lane": "This host or lane is outside the shared Codex/Claude discipline contract.",
    "cli_first_governed_truth": "This governed truth has an owning writer; use that path before hand edits.",
    "fresh_proof_completion": "Completion language needs fresh proof before it can be claimed.",
    "visible_intervention_proof": "Visible UX claims need status proof or a rendered fallback.",
    "queue_non_adoption": "Queued work is context until the operator explicitly authorizes implementation.",
    "bounded_delegation": "Delegation needs owner, goal, output, stop condition, owned scope, and validation.",
    "benchmark_public_claim": "Public shipped or proven product claims need benchmark proof first.",
    "consumer_mutation_guard": "Consumer-lane product mutation needs explicit authorization.",
    "explicit_model_credit": "Discipline checks must stay local unless the operator explicitly requests model spend.",
}

_HUMAN_ACTIONS = {
    "act_with_proof_obligation": "Proceed locally, then keep proof current before claiming completion.",
    "ask_for_explicit_authorization": "Ask for explicit authorization before adopting the queued work.",
    "check_platform_integration_contracts": "Check the platform integration contracts before changing behavior.",
    "choose_supported_host_lane": "Choose Codex or Claude on dev, dev-maintainer, dogfood, or consumer.",
    "diagnose_and_handoff": "Diagnose the issue and hand off unless product mutation is authorized.",
    "inspect_learning_feedback_loop": "Inspect the learning feedback loop without storing raw transcript data.",
    "inspect_voice_surfaces_without_scripted_copy": "Inspect voice surfaces without adding scripted copy.",
    "make_delegation_route_ready": "Make the delegation bounded, owned, terminable, and validated.",
    "narrow_context_first": "Narrow the context first, then choose the next admissible move.",
    "prove_visible_intervention_or_render_fallback": "Prove visibility with status evidence or render the fallback.",
    "run_benchmark_proof": "Run the required benchmark proof before publishing the claim.",
    "run_fresh_validation": "Run fresh validation before making the claim.",
    "stay_local_or_request_explicit_model_budget": "Stay local, or ask for explicit model budget before spending credits.",
    "use_cli_writer": "Use the owning CLI writer first.",
}

_HUMAN_PROOF = {
    "benchmark_proof_required": "benchmark proof before public product claims",
    "bounded_delegation_contract_required": "a bounded delegation contract",
    "fresh_validation_required": "fresh validation evidence",
    "governed_cli_writer_required": "the governed CLI writer path",
    "local_proof_obligation": "local proof before stronger claims",
    "matched_benchmark_proof_required": "matched benchmark proof before public product claims",
    "visible_intervention_proof_required": "visible status proof or rendered fallback",
}

_MACHINE_DETAIL_HINT = "Detailed verification stays behind --json."


def _json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="odylith discipline", description="Inspect local discipline behavior.")
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="character_command", required=True)
    status = subparsers.add_parser("status", help="Show current local discipline readiness.")
    status.add_argument("--json", action="store_true", dest="as_json")
    check = subparsers.add_parser("check", help="Evaluate a proposed move locally.")
    check.add_argument("--intent-file", required=True)
    check.add_argument("--host", default="codex")
    check.add_argument("--lane", default="dev")
    check.add_argument("--json", action="store_true", dest="as_json")
    explain = subparsers.add_parser("explain", help="Explain a prior decision id.")
    explain.add_argument("--decision-id", required=True)
    explain.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def _print(payload: Mapping[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(_json(payload), end="")
        return
    if str(payload.get("status", "")).strip() == "ready":
        _print_human_status(payload)
        return
    if str(payload.get("status", "")).strip() == "explained":
        _print_human_explanation(payload)
        return
    if "decision" in payload:
        _print_human_check(payload)
        return
    _print_human_fallback(payload)


def _clean_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list | tuple | set):
        candidates = list(value)
    else:
        candidates = []
    rows: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        token = str(candidate or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _decision_label(value: Any) -> str:
    token = str(value or "ready").strip()
    return {
        "admit": "admitted",
        "block": "blocked",
        "defer": "deferred",
        "escalate": "escalated",
        "institutionalize": "institutionalized",
        "nudge": "nudged",
        "silent": "ready",
    }.get(token, token or "ready")


def _human_law_reason(law_id: str) -> str:
    return _HUMAN_LAW_REASONS.get(law_id, "This move needs a lower-risk path before acting.")


def _human_action(action: Any) -> str:
    token = str(action or "").strip()
    return _HUMAN_ACTIONS.get(token, token.replace("_", " ") if token else "Choose the lowest-risk local move.")


def _human_proof(proof: Any) -> str:
    token = str(proof or "").strip()
    return _HUMAN_PROOF.get(token, token.replace("_", " ") if token else "")


def _violated_law_ids(payload: Mapping[str, Any]) -> list[str]:
    explicit = _clean_strings(payload.get("violated_laws"))
    if explicit:
        return explicit
    rows = payload.get("hard_law_results")
    if not isinstance(rows, list):
        return []
    violations: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping) or str(row.get("status", "")).strip() != "violated":
            continue
        law_id = str(row.get("law_id", "")).strip()
        if law_id:
            violations.append(law_id)
    return violations


def _budget_line(payload: Mapping[str, Any]) -> str:
    budget = payload.get("latency_budget")
    if not isinstance(budget, Mapping):
        return "Budget: local discipline path; use --json for counters."
    local_only = (
        int(budget.get("host_model_call_count", 0) or 0) == 0
        and int(budget.get("provider_call_count", 0) or 0) == 0
    )
    if local_only and bool(budget.get("hot_path_budget_passed")):
        return "Budget: local-only check; no host model or provider calls."
    return "Budget: review the detailed JSON before relying on this decision."


def _print_human_status(payload: Mapping[str, Any]) -> None:
    support = payload.get("host_lane_support") if isinstance(payload.get("host_lane_support"), Mapping) else {}
    hosts = ", ".join(_clean_strings(support.get("supported_host_families"))) or "unknown"
    lanes = ", ".join(_clean_strings(support.get("supported_lanes"))) or "unknown"
    latest = payload.get("last_decision") if isinstance(payload.get("last_decision"), Mapping) else {}
    print("Odylith Discipline: ready")
    print("Hot path: local and zero-credit by default.")
    print(f"Hosts: {hosts}")
    print(f"Lanes: {lanes}")
    if latest.get("decision"):
        next_action = _human_action(latest.get("nearest_admissible_action"))
        print(f"Last decision: {_decision_label(latest.get('decision'))}; next: {next_action}")
    benchmark = payload.get("benchmark_proof_freshness")
    if isinstance(benchmark, Mapping) and benchmark.get("state"):
        print("Benchmark proof: explicit benchmark run required for public claims.")
    print(_MACHINE_DETAIL_HINT)


def _print_human_check(payload: Mapping[str, Any]) -> None:
    print(f"Odylith Discipline: {_decision_label(payload.get('decision'))}")
    violations = _violated_law_ids(payload)
    if violations:
        for law_id in violations[:4]:
            print(f"Reason: {_human_law_reason(law_id)}")
    elif str(payload.get("decision", "")).strip() == "defer":
        print("Reason: The intent is still ambiguous enough to narrow before acting.")
    else:
        print("Reason: No hard law blocked this local move.")
    print(f"Next: {_human_action(payload.get('nearest_admissible_action'))}")
    proof = _human_proof(payload.get("proof_obligation"))
    if proof:
        print(f"Proof needed: {proof}")
    print(_budget_line(payload))
    print(_MACHINE_DETAIL_HINT)


def _print_human_explanation(payload: Mapping[str, Any]) -> None:
    decision_id = str(payload.get("decision_id", "")).strip()
    suffix = f" {decision_id}" if decision_id else ""
    print(f"Odylith Discipline decision{suffix}: {_decision_label(payload.get('decision'))}")
    violations = _violated_law_ids(payload)
    if violations:
        for law_id in violations[:4]:
            print(f"Why: {_human_law_reason(law_id)}")
    else:
        print("Why: No hard law violation was recorded for this decision.")
    print(f"Next: {_human_action(payload.get('nearest_admissible_action'))}")
    proof = _human_proof(payload.get("proof_obligation"))
    if proof:
        print(f"Proof needed: {proof}")
    print(_budget_line(payload))
    print(_MACHINE_DETAIL_HINT)


def _print_human_fallback(payload: Mapping[str, Any]) -> None:
    print(f"Odylith Discipline: {str(payload.get('status', 'unavailable')).strip() or 'unavailable'}")
    reason = str(payload.get("reason", "")).strip()
    if reason:
        print(f"Reason: {reason}")
    print(_MACHINE_DETAIL_HINT)


def _decision_cache_dir(repo_root: Path) -> Path:
    return repo_root / DECISION_CACHE_RELATIVE


def _decision_filename(decision_id: str) -> str:
    token = str(decision_id or "").strip()
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in token)
    return f"{safe or 'unknown'}.json"


def _record_decision(repo_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    decision_id = str(payload.get("decision_id", "")).strip()
    if not decision_id:
        return {"recorded": False, "reason": "missing_decision_id"}
    cache_dir = _decision_cache_dir(repo_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / _decision_filename(decision_id)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    latest_path = cache_dir / "latest.json"
    latest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "recorded": True,
        "decision_id": decision_id,
        "cache_scope": str(DECISION_CACHE_RELATIVE),
    }


def _load_decision(repo_root: Path, decision_id: str) -> dict[str, Any]:
    path = _decision_cache_dir(repo_root) / _decision_filename(decision_id)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _latest_decision(repo_root: Path) -> dict[str, Any]:
    path = _decision_cache_dir(repo_root) / "latest.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _decision_digest(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    learning = payload.get("learning_signal") if isinstance(payload.get("learning_signal"), Mapping) else {}
    budget = payload.get("latency_budget") if isinstance(payload.get("latency_budget"), Mapping) else {}
    return {
        "decision_id": str(payload.get("decision_id", "")).strip(),
        "decision": str(payload.get("decision", "")).strip(),
        "host_family": str(payload.get("host_family", "")).strip(),
        "lane": str(payload.get("lane", "")).strip(),
        "nearest_admissible_action": str(payload.get("nearest_admissible_action", "")).strip(),
        "proof_obligation": str(payload.get("proof_obligation", "")).strip(),
        "learning_outcome": str(learning.get("outcome", "")).strip(),
        "retention_class": str(learning.get("retention_class", "")).strip(),
        "hot_path_budget_passed": bool(budget.get("hot_path_budget_passed")),
        "provider_call_count": int(budget.get("provider_call_count", 0) or 0),
        "host_model_call_count": int(budget.get("host_model_call_count", 0) or 0),
    }


def _explain_decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    hard_laws = payload.get("hard_law_results") if isinstance(payload.get("hard_law_results"), list) else []
    violated = [
        row
        for row in hard_laws
        if isinstance(row, Mapping) and str(row.get("status", "")).strip() == "violated"
    ]
    recovery = [
        str(row.get("recovery", "")).strip()
        for row in violated
        if str(row.get("recovery", "")).strip()
    ]
    budget = payload.get("latency_budget") if isinstance(payload.get("latency_budget"), Mapping) else {}
    learning = payload.get("learning_signal") if isinstance(payload.get("learning_signal"), Mapping) else {}
    return {
        "contract": CHARACTER_CONTRACT,
        "status": "explained",
        "decision_id": str(payload.get("decision_id", "")).strip(),
        "decision": str(payload.get("decision", "")).strip(),
        "host_family": str(payload.get("host_family", "")).strip(),
        "lane": str(payload.get("lane", "")).strip(),
        "pressure_observations": list(payload.get("pressure_observations", []))
        if isinstance(payload.get("pressure_observations"), list)
        else [],
        "known_archetype_matches": list(payload.get("known_archetype_matches", []))
        if isinstance(payload.get("known_archetype_matches"), list)
        else [],
        "violated_laws": [str(row.get("law_id", "")).strip() for row in violated],
        "nearest_admissible_action": str(payload.get("nearest_admissible_action", "")).strip(),
        "proof_obligation": str(payload.get("proof_obligation", "")).strip(),
        "learning_outcome": str(learning.get("outcome", "")).strip(),
        "retention_class": str(learning.get("retention_class", "")).strip(),
        "what_would_change_result": recovery
        or ["Add concrete local evidence that lowers uncertainty, then rerun discipline check."],
        "practice_event": payload.get("practice_event", {})
        if isinstance(payload.get("practice_event"), Mapping)
        else {},
        "latency_budget": budget,
        "credit_budget": str(payload.get("credit_budget", "")).strip(),
        "source_refs": list(payload.get("source_refs", [])) if isinstance(payload.get("source_refs"), list) else [],
    }


def run_character(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    if args.character_command == "status":
        summary = character_runtime.runtime_summary(repo_root=repo_root)
        latest = _latest_decision(repo_root)
        payload = {
            "contract": CHARACTER_CONTRACT,
            "status": "ready",
            "family": FAMILY,
            "repo_root": str(repo_root),
            "runtime_summary": summary,
            "host_lane_support": {
                "supported_host_families": list(SUPPORTED_HOST_FAMILIES),
                "supported_lanes": list(SUPPORTED_LANES),
                "matrix": host_lane_matrix(),
            },
            "active_hard_laws": sorted(HARD_LAWS),
            "learning": {
                "outcomes": list(LEARNING_OUTCOMES),
                "retention_classes": list(RETENTION_CLASSES),
                "durable_learning_gate": "validator_benchmark_or_tribunal",
            },
            "last_decision": _decision_digest(latest),
            "benchmark_proof_freshness": {
                "state": "explicit_benchmark_required",
                "command": summary.get("benchmark_command", ""),
                "corpus_fingerprint": summary.get("corpus_fingerprint", ""),
            },
            "hot_path": {
                "provider_calls": 0,
                "host_model_calls": 0,
                "broad_scans": 0,
                "full_validations": 0,
                "projection_expansions": 0,
            },
            "commands": [
                "odylith discipline check --repo-root . --intent-file PATH --json",
                "odylith validate discipline --repo-root .",
                "odylith benchmark --profile quick --family discipline --no-write-report --json",
            ],
        }
        _print(payload, as_json=bool(args.as_json))
        return 0
    if args.character_command == "check":
        intent_path = Path(args.intent_file)
        if not intent_path.is_absolute():
            intent_path = repo_root / intent_path
        if not intent_path.is_file():
            print(f"intent file does not exist: {intent_path}")
            return 1
        payload = evaluate_character_move(
            intent=intent_path.read_text(encoding="utf-8"),
            host_family=args.host,
            lane=args.lane,
            source_refs=[str(intent_path.relative_to(repo_root)) if intent_path.is_relative_to(repo_root) else str(intent_path)],
        )
        payload["decision_record"] = _record_decision(repo_root, payload)
        _print(payload, as_json=bool(args.as_json))
        return 0
    decision_id = str(args.decision_id).strip()
    decision = _load_decision(repo_root, decision_id)
    if not decision:
        payload = {
            "contract": CHARACTER_CONTRACT,
            "decision_id": decision_id,
            "status": "not_found",
            "reason": "No local discipline decision record exists for this decision id.",
            "cache_scope": str(DECISION_CACHE_RELATIVE),
        }
        _print(payload, as_json=bool(args.as_json))
        return 1
    payload = _explain_decision(decision)
    _print(payload, as_json=bool(args.as_json))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_character(argv)
