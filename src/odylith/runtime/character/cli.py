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


def _json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="odylith character", description="Inspect adaptive Agent Operating Character state.")
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="character_command", required=True)
    status = subparsers.add_parser("status", help="Show current local character readiness.")
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
    print(f"contract: {payload.get('contract', CHARACTER_CONTRACT)}")
    print(f"status: {payload.get('status', payload.get('decision', 'ready'))}")
    if payload.get("nearest_admissible_action"):
        print(f"next: {payload['nearest_admissible_action']}")
    budget = payload.get("latency_budget")
    if isinstance(budget, Mapping):
        print(f"hot_path_budget_passed: {str(budget.get('hot_path_budget_passed')).lower()}")
        print(f"host_model_call_count: {budget.get('host_model_call_count', 0)}")


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
        or ["Add concrete local evidence that lowers uncertainty, then rerun character check."],
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
                "odylith character check --repo-root . --intent-file PATH --json",
                "odylith validate agent-operating-character --repo-root .",
                "odylith benchmark --profile quick --family agent_operating_character --no-write-report --json",
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
            "reason": "No local character decision record exists for this decision id.",
            "cache_scope": str(DECISION_CACHE_RELATIVE),
        }
        _print(payload, as_json=bool(args.as_json))
        return 1
    payload = _explain_decision(decision)
    _print(payload, as_json=bool(args.as_json))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_character(argv)
