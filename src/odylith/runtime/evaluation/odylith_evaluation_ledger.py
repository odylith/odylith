"""Local JSONL evaluation ledger for Odylith self-improvement signals.

This module keeps one compact local-only event stream that ties together:

- packet/runtime bootstrap quality;
- subagent router outcomes; and
- orchestration feedback.

The goal is not to replace the packet contracts. It provides a persistent,
append-friendly learning substrate so Odylith can summarize how recent
execution actually performed and feed those signals back into runtime control.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache


LEDGER_FILENAME = "odylith-evaluation.v1.jsonl"
LEDGER_CONTRACT = "odylith_evaluation_event.v1"
LEDGER_VERSION = "v1"
MAX_LEDGER_EVENTS = 2048
_FRESH_EVENT_MAX_HOURS = 6.0
_RECENT_EVENT_MAX_HOURS = 24.0
_AGING_EVENT_MAX_HOURS = 72.0
_STALE_EVENT_MAX_HOURS = 7 * 24.0


def ledger_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / LEDGER_FILENAME).resolve()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace(" ", "_")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    token = _normalize_token(value)
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return bool(value)


def _mapping_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if limit is not None and len(rows) >= max(1, int(limit)):
            break
    return rows


def _context_signal_score(value: Any) -> int:
    if isinstance(value, Mapping):
        score = value.get("score")
        if score not in (None, ""):
            return max(0, min(4, _int_value(score)))
        token = _normalize_token(value.get("level"))
        if token in {"high", "strong"}:
            return 4
        if token in {"medium", "balanced"}:
            return 2
        if token in {"low", "guarded", "weak"}:
            return 1
        if "anchored" in value:
            return 4 if _bool_value(value.get("anchored")) else 0
        if "route_ready" in value:
            return 4 if _bool_value(value.get("route_ready")) else 0
        return 0
    token = _normalize_token(value)
    if token in {"high", "strong", "grounded", "route_ready", "true", "yes"}:
        return 4
    if token in {"medium", "balanced"}:
        return 2
    if token in {"low", "guarded", "weak"}:
        return 1
    return max(0, min(4, _int_value(value)))


def _parse_utc(value: Any) -> dt.datetime | None:
    token = _normalize_string(value)
    if not token:
        return None
    normalized = token.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with target.open("r", encoding="utf-8") as handle:
            for line in handle:
                token = line.strip()
                if not token:
                    continue
                try:
                    payload = json.loads(token)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, Mapping):
                    rows.append(dict(payload))
    except OSError:
        return []
    return rows


def _write_rows(*, repo_root: Path, path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    target = Path(path).resolve()
    rendered = "".join(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def append_event(
    *,
    repo_root: Path,
    event_type: str,
    payload: Mapping[str, Any],
    event_id: str = "",
    recorded_at: str = "",
) -> Path:
    root = Path(repo_root).resolve()
    target = ledger_path(repo_root=root)
    row = {
        "contract": LEDGER_CONTRACT,
        "version": LEDGER_VERSION,
        "event_type": _normalize_token(event_type) or "unknown",
        "event_id": _normalize_string(event_id),
        "recorded_at": _normalize_string(recorded_at) or _utc_now(),
        "payload": dict(payload),
    }
    with odylith_context_cache.advisory_lock(repo_root=root, key=str(target)):
        rows = _read_rows(target)
        rows.append(row)
        if len(rows) > MAX_LEDGER_EVENTS:
            rows = rows[-MAX_LEDGER_EVENTS:]
        _write_rows(repo_root=root, path=target, rows=rows)
    return target


def packet_event_payload(
    *,
    packet_summary: Mapping[str, Any],
    benchmark_summary: Mapping[str, Any] | None = None,
    control_advisories: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    benchmark = dict(benchmark_summary) if isinstance(benchmark_summary, Mapping) else {}
    advisories = dict(control_advisories) if isinstance(control_advisories, Mapping) else {}
    advisory_confidence = (
        dict(advisories.get("confidence", {}))
        if isinstance(advisories.get("confidence"), Mapping)
        else {}
    )
    advisory_freshness = (
        dict(advisories.get("freshness", {}))
        if isinstance(advisories.get("freshness"), Mapping)
        else {}
    )
    advisory_evidence_strength = (
        dict(advisories.get("evidence_strength", {}))
        if isinstance(advisories.get("evidence_strength"), Mapping)
        else {}
    )
    return {
        "session_id": _normalize_string(packet_summary.get("session_id")),
        "workstream": _normalize_string(packet_summary.get("workstream")),
        "packet_state": _normalize_string(packet_summary.get("packet_state")),
        "intent_family": _normalize_string(packet_summary.get("intent_family")),
        "routing_confidence": _normalize_string(packet_summary.get("routing_confidence")),
        "within_budget": _bool_value(packet_summary.get("within_budget")),
        "route_ready": _bool_value(packet_summary.get("route_ready")),
        "native_spawn_ready": _bool_value(packet_summary.get("native_spawn_ready")),
        "narrowing_required": _bool_value(packet_summary.get("narrowing_required")),
        "utility_score": _int_value(packet_summary.get("utility_score")),
        "context_density_score": _int_value(packet_summary.get("context_density_score")),
        "reasoning_readiness_score": _int_value(packet_summary.get("reasoning_readiness_score")),
        "deep_reasoning_ready": _bool_value(packet_summary.get("deep_reasoning_ready")),
        "evidence_diversity_score": _int_value(packet_summary.get("evidence_diversity_score")),
        "density_per_1k_tokens": _float_value(packet_summary.get("density_per_1k_tokens")),
        "estimated_tokens": _int_value(packet_summary.get("estimated_tokens")),
        "odylith_execution_profile": _normalize_string(packet_summary.get("odylith_execution_profile")),
        "odylith_execution_model": _normalize_string(packet_summary.get("odylith_execution_model")),
        "odylith_execution_reasoning_effort": _normalize_string(packet_summary.get("odylith_execution_reasoning_effort")),
        "odylith_execution_delegate_preference": _normalize_string(packet_summary.get("odylith_execution_delegate_preference")),
        "odylith_execution_source": _normalize_string(packet_summary.get("odylith_execution_source")),
        "packet_strategy": _normalize_token(packet_summary.get("adaptive_packet_strategy")),
        "budget_mode": _normalize_token(packet_summary.get("adaptive_budget_mode")),
        "retrieval_focus": _normalize_token(packet_summary.get("adaptive_retrieval_focus")),
        "speed_mode": _normalize_token(packet_summary.get("adaptive_speed_mode")),
        "packet_reliability": _normalize_token(packet_summary.get("adaptive_reliability")),
        "selection_bias": _normalize_token(packet_summary.get("adaptive_selection_bias")),
        "advisory_state": _normalize_token(advisories.get("state")),
        "advisory_packet_strategy": _normalize_token(advisories.get("packet_strategy")),
        "advisory_budget_mode": _normalize_token(advisories.get("budget_mode")),
        "advisory_retrieval_focus": _normalize_token(advisories.get("retrieval_focus")),
        "advisory_speed_mode": _normalize_token(advisories.get("speed_mode")),
        "advisory_reasoning_mode": _normalize_token(advisories.get("reasoning_mode")),
        "advisory_confidence_score": _int_value(advisory_confidence.get("score")),
        "advisory_freshness_bucket": _normalize_token(advisory_freshness.get("bucket")),
        "advisory_evidence_strength_score": _int_value(advisory_evidence_strength.get("score")),
        "advisory_sample_balance": _normalize_token(advisory_evidence_strength.get("sample_balance")),
        "advisory_signal_conflict": _bool_value(advisories.get("signal_conflict")),
        "benchmark": {
            "matched_case_count": _int_value(benchmark.get("matched_case_count")),
            "satisfied_case_count": _int_value(benchmark.get("satisfied_case_count")),
            "matched_case_ids": _string_list(benchmark.get("matched_case_ids"), limit=6),
            "drift_case_ids": _string_list(benchmark.get("drift_case_ids"), limit=6),
        },
    }


def router_outcome_event_payload(
    *,
    decision: Mapping[str, Any],
    outcome: Mapping[str, Any],
    request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    assessed = _mapping_value(decision.get("assessment"))
    context_summary = _mapping_value(assessed.get("context_signal_summary"))
    request_payload = dict(request) if isinstance(request, Mapping) else {}
    return {
        "decision_id": _normalize_string(decision.get("decision_id")),
        "task_family": _normalize_string(decision.get("task_family") or assessed.get("task_family")),
        "profile": _normalize_string(decision.get("profile")),
        "model": _normalize_string(decision.get("model")),
        "reasoning_effort": _normalize_string(decision.get("reasoning_effort")),
        "delegate": _bool_value(decision.get("delegate")),
        "routing_confidence": _int_value(decision.get("routing_confidence")),
        "accepted": _bool_value(outcome.get("accepted")),
        "blocked": _bool_value(outcome.get("blocked")),
        "ambiguous": _bool_value(outcome.get("ambiguous")),
        "artifact_missing": _bool_value(outcome.get("artifact_missing")),
        "quality_too_weak": _bool_value(outcome.get("quality_too_weak")),
        "escalated": _bool_value(outcome.get("escalated")),
        "broader_coordination": _bool_value(outcome.get("broader_coordination")),
        "needs_write": _bool_value(assessed.get("needs_write", request_payload.get("needs_write"))),
        "correctness_critical": _bool_value(
            assessed.get("correctness_critical", request_payload.get("correctness_critical"))
        ),
        "latency_sensitive": _bool_value(request_payload.get("latency_sensitive")),
        "route_ready": _bool_value(context_summary.get("route_ready")),
        "narrowing_required": _bool_value(context_summary.get("narrowing_required")),
        "within_budget": _float_value(context_summary.get("optimization_within_budget_rate")) >= 0.5,
        "grounding_score": _int_value(context_summary.get("grounding_score")),
        "context_density_score": _int_value(context_summary.get("context_density_score")),
        "reasoning_readiness_score": _int_value(context_summary.get("reasoning_readiness_score")),
        "expected_delegation_value_score": _int_value(context_summary.get("expected_delegation_value_score")),
        "odylith_execution_profile": _normalize_string(context_summary.get("odylith_execution_profile")),
        "odylith_execution_delegate_preference": _normalize_string(
            context_summary.get("odylith_execution_delegate_preference")
        ),
    }


def orchestration_feedback_event_payload(
    *,
    decision: Mapping[str, Any],
    feedback: Mapping[str, Any],
    decision_ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    subtasks = decision.get("subtasks")
    subtask_count = len(subtasks) if isinstance(subtasks, list) else 0
    predicted_signals = _orchestration_predicted_signals(decision)
    closeout = _decision_closeout_summary(decision_ledger)
    return {
        "decision_id": _normalize_string(decision.get("decision_id")),
        "task_family": _normalize_string(decision.get("task_family")),
        "mode": _normalize_string(decision.get("mode")),
        "delegate": _bool_value(decision.get("delegate")),
        "confidence": _int_value(decision.get("confidence")),
        "subtask_count": subtask_count,
        "accepted": _bool_value(feedback.get("accepted")),
        "merge_conflicts": _int_value(feedback.get("merge_conflicts")),
        "rescope_required": _bool_value(feedback.get("rescope_required")),
        "false_parallelization": _bool_value(feedback.get("false_parallelization")),
        "escalated_leaves": _int_value(feedback.get("escalated_leaves")),
        "token_efficient": _bool_value(feedback.get("token_efficient")),
        "predicted_signal_count": _int_value(predicted_signals.get("signal_count")),
        "predicted_grounding_score": _int_value(predicted_signals.get("grounding_score")),
        "predicted_density_score": _int_value(predicted_signals.get("density_score")),
        "predicted_actionability_score": _int_value(predicted_signals.get("actionability_score")),
        "predicted_validation_pressure_score": _int_value(predicted_signals.get("validation_pressure_score")),
        "predicted_merge_burden_score": _int_value(predicted_signals.get("merge_burden_score")),
        "predicted_expected_delegation_value_score": _int_value(
            predicted_signals.get("expected_delegation_value_score")
        ),
        "predicted_route_ready_rate": _float_value(predicted_signals.get("route_ready_rate")),
        "predicted_primary_leaf_count": _int_value(predicted_signals.get("primary_leaf_count")),
        "predicted_support_leaf_count": _int_value(predicted_signals.get("support_leaf_count")),
        "closure_available": _bool_value(closeout.get("available")),
        "closure_state": _normalize_token(closeout.get("closure_state")),
        "clean_closeout_rate": _float_value(closeout.get("clean_closeout_rate")),
        "validated_closeout_rate": _float_value(closeout.get("validated_closeout_rate")),
        "integrated_closeout_rate": _float_value(closeout.get("integrated_closeout_rate")),
        "followup_active_rate": _float_value(closeout.get("followup_active_rate")),
        "stalled_closeout_rate": _float_value(closeout.get("stalled_closeout_rate")),
        "closeout_closed_rate": _float_value(closeout.get("closeout_closed_rate")),
    }


def _score_average(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(_int_value(row.get(key)) for row in rows) / float(len(rows)), 3)


def _score_max(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    if not rows:
        return 0
    return max(_int_value(row.get(key)) for row in rows)


def _rate_from_rows(rows: Sequence[Mapping[str, Any]], predicate) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if predicate(row)) / float(len(rows)), 3)


def _orchestration_predicted_signal_rows(decision: Mapping[str, Any]) -> list[dict[str, Any]]:
    subtasks = decision.get("subtasks")
    rows: list[dict[str, Any]] = []
    if isinstance(subtasks, list):
        for raw in subtasks:
            if not isinstance(raw, Mapping):
                continue
            route_profile = _mapping_value(raw.get("route_odylith_execution_profile"))
            if not route_profile:
                route_profile = _mapping_value(raw.get("execution_profile"))
            signals = _mapping_value(route_profile.get("signals"))
            constraints = _mapping_value(route_profile.get("constraints"))
            rows.append(
                {
                    "grounding_score": _context_signal_score(signals.get("grounding")),
                    "density_score": _context_signal_score(signals.get("density")),
                    "actionability_score": _context_signal_score(signals.get("actionability")),
                    "validation_pressure_score": _context_signal_score(signals.get("validation_pressure")),
                    "merge_burden_score": max(
                        _context_signal_score(signals.get("merge_burden")),
                        _context_signal_score(constraints.get("merge_burden")),
                    ),
                    "expected_delegation_value_score": _context_signal_score(
                        signals.get("expected_delegation_value")
                    ),
                    "route_ready": _bool_value(constraints.get("route_ready")),
                    "scope_role": _normalize_token(raw.get("scope_role")),
                    "group_kind": _normalize_token(raw.get("execution_group_kind")),
                }
            )
    if rows:
        return rows
    request = _mapping_value(decision.get("request"))
    context_signals = _mapping_value(request.get("context_signals"))
    execution_profile = _mapping_value(context_signals.get("odylith_execution_profile"))
    signals = _mapping_value(execution_profile.get("signals"))
    constraints = _mapping_value(execution_profile.get("constraints"))
    if not signals and not constraints:
        return []
    return [
        {
            "grounding_score": _context_signal_score(signals.get("grounding")),
            "density_score": _context_signal_score(signals.get("density")),
            "actionability_score": _context_signal_score(signals.get("actionability")),
            "validation_pressure_score": _context_signal_score(signals.get("validation_pressure")),
            "merge_burden_score": max(
                _context_signal_score(signals.get("merge_burden")),
                _context_signal_score(constraints.get("merge_burden")),
            ),
            "expected_delegation_value_score": _context_signal_score(signals.get("expected_delegation_value")),
            "route_ready": _bool_value(constraints.get("route_ready")),
            "scope_role": "analysis",
            "group_kind": "",
        }
    ]


def _orchestration_predicted_signals(decision: Mapping[str, Any]) -> dict[str, Any]:
    rows = _orchestration_predicted_signal_rows(decision)
    return {
        "signal_count": len(rows),
        "grounding_score": _score_max(rows, "grounding_score"),
        "density_score": round(_score_average(rows, "density_score")),
        "actionability_score": round(_score_average(rows, "actionability_score")),
        "validation_pressure_score": _score_max(rows, "validation_pressure_score"),
        "merge_burden_score": _score_max(rows, "merge_burden_score"),
        "expected_delegation_value_score": round(_score_average(rows, "expected_delegation_value_score")),
        "route_ready_rate": _rate_from_rows(rows, lambda row: _bool_value(row.get("route_ready"))),
        "primary_leaf_count": sum(
            1 for row in rows if _normalize_token(row.get("group_kind")) in {"primary", "implementation"}
        ),
        "support_leaf_count": sum(
            1 for row in rows if _normalize_token(row.get("group_kind")) == "support"
        ),
    }


def _decision_closeout_summary(decision_ledger: Mapping[str, Any] | None) -> dict[str, Any]:
    ledger = dict(decision_ledger) if isinstance(decision_ledger, Mapping) else {}
    subtasks = ledger.get("subtasks")
    if not isinstance(subtasks, list) or not subtasks:
        return {"available": False}
    total = 0
    clean_closeouts = 0
    validated_closeouts = 0
    integrated_closeouts = 0
    active_followups = 0
    stalled_closeouts = 0
    closed_closeouts = 0
    for raw in subtasks:
        if not isinstance(raw, Mapping):
            continue
        total += 1
        state = _mapping_value(raw.get("inspection_state"))
        result_handoff = _mapping_value(state.get("result_handoff"))
        followup = _mapping_value(state.get("followup"))
        closeout = _mapping_value(state.get("closeout"))
        status = _normalize_token(state.get("status"))
        result_status = _normalize_token(result_handoff.get("status"))
        followup_status = _normalize_token(followup.get("status"))
        closeout_status = _normalize_token(closeout.get("status"))
        has_active_followup = followup_status in {"claimed", "queued", "sent", "running"}
        if has_active_followup:
            active_followups += 1
        if closeout_status == "closed":
            closed_closeouts += 1
        if result_status in {"validated", "accepted"}:
            validated_closeouts += 1
        if result_status in {"integrated", "validated", "accepted"}:
            integrated_closeouts += 1
        if closeout_status == "closed" and result_status in {"integrated", "validated", "accepted"} and not has_active_followup:
            clean_closeouts += 1
        if status in {"waiting_on_instruction", "waiting", "idle"} and not has_active_followup and closeout_status != "closed":
            stalled_closeouts += 1
    if total <= 0:
        return {"available": False}
    clean_closeout_rate = round(clean_closeouts / float(total), 3)
    validated_closeout_rate = round(validated_closeouts / float(total), 3)
    integrated_closeout_rate = round(integrated_closeouts / float(total), 3)
    followup_active_rate = round(active_followups / float(total), 3)
    stalled_closeout_rate = round(stalled_closeouts / float(total), 3)
    closeout_closed_rate = round(closed_closeouts / float(total), 3)
    closure_state = "mixed"
    if clean_closeouts == total:
        closure_state = "clean"
    elif stalled_closeouts > 0:
        closure_state = "stalled"
    elif followup_active_rate >= 0.34:
        closure_state = "followup_heavy"
    elif integrated_closeouts == total and active_followups == 0:
        closure_state = "integrated_pending_closeout"
    elif closeout_closed_rate < 0.34:
        closure_state = "partial"
    return {
        "available": True,
        "subtask_count": total,
        "clean_closeout_rate": clean_closeout_rate,
        "validated_closeout_rate": validated_closeout_rate,
        "integrated_closeout_rate": integrated_closeout_rate,
        "followup_active_rate": followup_active_rate,
        "stalled_closeout_rate": stalled_closeout_rate,
        "closeout_closed_rate": closeout_closed_rate,
        "closure_state": closure_state,
    }


def load_events(
    *,
    repo_root: Path,
    limit: int = 256,
    event_types: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    rows = _read_rows(ledger_path(repo_root=repo_root))
    allowed = {_normalize_token(token) for token in (event_types or []) if _normalize_token(token)}
    if allowed:
        rows = [row for row in rows if _normalize_token(row.get("event_type")) in allowed]
    if limit > 0:
        rows = rows[-max(1, int(limit)) :]
    rows.reverse()
    return rows


def _rate(rows: Sequence[Mapping[str, Any]], predicate) -> float:
    total = len(rows)
    if total <= 0:
        return 0.0
    return round(sum(1 for row in rows if predicate(row)) / float(total), 3)


def _avg(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(_float_value(row.get(key)) for row in rows) / float(len(rows)), 3)


def _unit_interval(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _packet_yield_score(row: Mapping[str, Any]) -> float:
    utility = _unit_interval(_float_value(row.get("utility_score")) / 100.0)
    density = _unit_interval(_float_value(row.get("context_density_score")) / 4.0)
    density_per_1k = _unit_interval(_float_value(row.get("density_per_1k_tokens")) / 2.5)
    diversity = _unit_interval(_float_value(row.get("evidence_diversity_score")) / 4.0)
    readiness = _unit_interval(_float_value(row.get("reasoning_readiness_score")) / 4.0)
    within_budget = 1.0 if _bool_value(row.get("within_budget")) else 0.0
    route_ready = 1.0 if _bool_value(row.get("route_ready")) else 0.0
    native_spawn_ready = 1.0 if _bool_value(row.get("native_spawn_ready")) else 0.0
    score = (
        (0.28 * utility)
        + (0.16 * density)
        + (0.14 * density_per_1k)
        + (0.10 * diversity)
        + (0.12 * readiness)
        + (0.10 * within_budget)
        + (0.06 * route_ready)
        + (0.04 * native_spawn_ready)
    )
    return round(_unit_interval(score), 3)


def _event_age_hours(row: Mapping[str, Any], *, now: dt.datetime) -> float | None:
    recorded_at = _parse_utc(row.get("_recorded_at"))
    if recorded_at is None:
        recorded_at = _parse_utc(row.get("recorded_at"))
    if recorded_at is None:
        return None
    return max(0.0, (now - recorded_at).total_seconds() / 3600.0)


def _freshness_bucket(age_hours: float | None) -> str:
    if age_hours is None:
        return "unknown"
    if age_hours <= _FRESH_EVENT_MAX_HOURS:
        return "fresh"
    if age_hours <= _RECENT_EVENT_MAX_HOURS:
        return "recent"
    if age_hours <= _AGING_EVENT_MAX_HOURS:
        return "aging"
    return "stale"


def _event_weight(row: Mapping[str, Any], *, now: dt.datetime) -> float:
    age_hours = _event_age_hours(row, now=now)
    bucket = _freshness_bucket(age_hours)
    if bucket == "fresh":
        return 1.0
    if bucket == "recent":
        return 0.85
    if bucket == "aging":
        return 0.55
    if bucket == "stale":
        return 0.2 if age_hours is not None and age_hours > _STALE_EVENT_MAX_HOURS else 0.3
    return 0.45


def _weighted_rate(rows: Sequence[Mapping[str, Any]], predicate, *, now: dt.datetime) -> float:
    if not rows:
        return 0.0
    weighted_total = 0.0
    weighted_hits = 0.0
    for row in rows:
        weight = _event_weight(row, now=now)
        weighted_total += weight
        if predicate(row):
            weighted_hits += weight
    if weighted_total <= 0.0:
        return 0.0
    return round(weighted_hits / weighted_total, 3)


def _freshness_snapshot(rows: Sequence[Mapping[str, Any]], *, now: dt.datetime) -> dict[str, Any]:
    ages = [age for age in (_event_age_hours(row, now=now) for row in rows) if age is not None]
    newest_age = min(ages) if ages else None
    return {
        "bucket": _freshness_bucket(newest_age),
        "newest_age_hours": round(float(newest_age), 2) if newest_age is not None else None,
        "count": len(rows),
    }


def _evidence_strength(
    *,
    packet_count: int,
    router_count: int,
    orchestration_count: int,
    freshness_bucket: str,
    signal_conflict: bool,
) -> dict[str, Any]:
    score = 0
    if packet_count >= 8:
        score += 1
    elif packet_count >= 4:
        score += 0.5
    if router_count >= 4:
        score += 1
    elif router_count >= 2:
        score += 0.5
    if orchestration_count >= 4:
        score += 1
    elif orchestration_count >= 2:
        score += 0.5
    if freshness_bucket in {"fresh", "recent"}:
        score += 1
    elif freshness_bucket == "aging":
        score -= 0.5
    elif freshness_bucket == "stale":
        score -= 1.5
    if signal_conflict:
        score -= 1

    balanced = packet_count >= 4 and router_count >= 2 and orchestration_count >= 2
    partial = (
        (packet_count >= 1 and router_count >= 1 and orchestration_count >= 1)
        or (packet_count >= 2 and (router_count >= 1 or orchestration_count >= 1))
    )
    sample_balance = "balanced" if balanced else "partial" if partial else "thin" if (packet_count or router_count or orchestration_count) else "none"
    if sample_balance == "balanced":
        score += 0.5
    elif sample_balance == "thin":
        score -= 0.5

    score = max(0.0, min(4.0, score))
    score = max(0, min(4, int(score + 0.5)))
    return {
        "score": score,
        "level": _confidence_level(score),
        "sample_balance": sample_balance,
        "freshness_bucket": freshness_bucket,
        "signal_conflict": signal_conflict,
    }


def _split_recent(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized = [dict(row) for row in rows if isinstance(row, Mapping)]
    if len(normalized) < 4:
        return normalized, []
    half = max(1, len(normalized) // 2)
    return normalized[:half], normalized[half : half * 2]


def _trend_label(current: float, previous: float, *, higher_is_better: bool = True) -> str:
    if previous == 0.0 and current == 0.0:
        return "unknown"
    delta = current - previous if higher_is_better else previous - current
    if delta >= 0.08:
        return "improving"
    if delta <= -0.08:
        return "regressing"
    return "stable"


def _confidence_level(score: int) -> str:
    clamped = max(0, min(4, int(score)))
    if clamped >= 4:
        return "high"
    if clamped >= 2:
        return "medium"
    if clamped >= 1:
        return "low"
    return "none"


def _actual_merge_friction_score(row: Mapping[str, Any]) -> int:
    score = 0
    merge_conflicts = _int_value(row.get("merge_conflicts"))
    if merge_conflicts > 0:
        score = max(score, min(4, 1 + merge_conflicts))
    if _bool_value(row.get("false_parallelization")):
        score = max(score, 4)
    if _bool_value(row.get("rescope_required")):
        score = max(score, 3 if merge_conflicts else 2)
    closure_state = _normalize_token(row.get("closure_state"))
    followup_active_rate = _float_value(row.get("followup_active_rate"))
    if closure_state == "stalled":
        score = max(score, 4)
    elif closure_state == "followup_heavy" or followup_active_rate >= 0.34:
        score = max(score, 3)
    elif followup_active_rate > 0.0:
        score = max(score, 2)
    return max(0, min(4, score))


def _actual_validation_friction_score(row: Mapping[str, Any]) -> int:
    score = 0
    if _bool_value(row.get("rescope_required")):
        score = max(score, 3)
    escalated = _int_value(row.get("escalated_leaves"))
    if escalated > 0:
        score = max(score, min(4, 1 + escalated))
    closure_state = _normalize_token(row.get("closure_state"))
    if closure_state == "stalled":
        score = max(score, 4)
    elif closure_state == "followup_heavy" or _float_value(row.get("followup_active_rate")) >= 0.34:
        score = max(score, 3)
    elif _bool_value(row.get("accepted")) and not _bool_value(row.get("token_efficient")):
        score = max(score, 2)
    return max(0, min(4, score))


def _actual_delegation_value_score(row: Mapping[str, Any]) -> int:
    closure_state = _normalize_token(row.get("closure_state"))
    if closure_state == "stalled":
        return 0
    if _bool_value(row.get("false_parallelization")) or _int_value(row.get("merge_conflicts")) > 1:
        return 0
    if _bool_value(row.get("rescope_required")) or _int_value(row.get("merge_conflicts")) == 1:
        return 1
    if not _bool_value(row.get("accepted")):
        return 1 if _bool_value(row.get("delegate")) else 2
    if _bool_value(row.get("token_efficient")) and closure_state == "clean":
        return 4
    if closure_state in {"clean", "integrated_pending_closeout"}:
        return 3
    if _bool_value(row.get("token_efficient")):
        return 3
    return 2


def _weighted_calibration_metrics(
    rows: Sequence[Mapping[str, Any]],
    *,
    predicted_key: str,
    actual_score,
    now: dt.datetime,
) -> dict[str, Any]:
    coverage = 0
    weighted_total = 0.0
    weighted_hits = 0.0
    weighted_under = 0.0
    weighted_over = 0.0
    weighted_gap = 0.0
    for row in rows:
        if _int_value(row.get("predicted_signal_count")) <= 0:
            continue
        predicted = _int_value(row.get(predicted_key))
        actual = int(actual_score(row))
        weight = _event_weight(row, now=now)
        coverage += 1
        weighted_total += weight
        gap = actual - predicted
        weighted_gap += weight * abs(gap)
        if abs(gap) <= 1:
            weighted_hits += weight
        if gap >= 2:
            weighted_under += weight
        elif gap <= -2:
            weighted_over += weight
    if weighted_total <= 0.0:
        return {
            "coverage": coverage,
            "rate": 0.0,
            "underestimate_rate": 0.0,
            "overestimate_rate": 0.0,
            "avg_gap": 0.0,
        }
    return {
        "coverage": coverage,
        "rate": round(weighted_hits / weighted_total, 3),
        "underestimate_rate": round(weighted_under / weighted_total, 3),
        "overestimate_rate": round(weighted_over / weighted_total, 3),
        "avg_gap": round(weighted_gap / weighted_total, 3),
    }


def _decision_quality_confidence(
    *,
    orchestration_count: int,
    closeout_count: int,
    merge_coverage: int,
    validation_coverage: int,
    delegation_coverage: int,
    freshness_bucket: str,
    signal_conflict: bool,
) -> dict[str, Any]:
    closeout_observation_rate = round(
        closeout_count / float(max(1, orchestration_count)),
        3,
    ) if orchestration_count > 0 else 0.0
    calibration_coverages = [merge_coverage, validation_coverage, delegation_coverage]
    calibration_ready_count = sum(1 for value in calibration_coverages if int(value or 0) >= 2)
    calibration_strong_count = sum(1 for value in calibration_coverages if int(value or 0) >= 4)
    calibration_observation_rate = round(
        sum(min(orchestration_count, max(0, int(value or 0))) for value in calibration_coverages)
        / float(max(1, orchestration_count * max(1, len(calibration_coverages)))),
        3,
    ) if orchestration_count > 0 else 0.0

    score = 0.0
    if orchestration_count >= 10:
        score += 1.0
    elif orchestration_count >= 5:
        score += 0.5
    if closeout_count >= 6:
        score += 1.0
    elif closeout_count >= 3:
        score += 0.5
    if calibration_strong_count >= 2:
        score += 1.0
    elif calibration_ready_count >= 2:
        score += 0.5
    if closeout_observation_rate >= 0.6:
        score += 0.5
    elif closeout_observation_rate < 0.34 and orchestration_count > 0:
        score -= 0.5
    if freshness_bucket in {"fresh", "recent"}:
        score += 1.0
    elif freshness_bucket == "aging":
        score -= 0.5
    elif freshness_bucket == "stale":
        score -= 1.0
    if signal_conflict:
        score -= 0.5

    sample_balance = "none"
    if orchestration_count > 0:
        sample_balance = "thin"
        if (
            orchestration_count >= 5
            and closeout_count >= 3
            and calibration_ready_count >= 2
        ):
            sample_balance = "balanced"
        elif (
            orchestration_count >= 2
            and closeout_count >= 1
            and calibration_ready_count >= 1
        ):
            sample_balance = "partial"
    if sample_balance == "balanced":
        score += 0.5
    elif sample_balance == "thin":
        score -= 0.5

    confidence_score = max(0, min(4, int(score + 0.5)))
    state = "insufficient"
    if orchestration_count > 0:
        state = "bootstrap" if confidence_score <= 1 else "provisional" if confidence_score == 2 else "trusted"
    return {
        "score": confidence_score,
        "level": _confidence_level(confidence_score),
        "state": state,
        "sample_balance": sample_balance,
        "closeout_observation_rate": closeout_observation_rate,
        "calibration_observation_rate": calibration_observation_rate,
    }


def _decision_quality_score(
    *,
    delegation_regret_rate: float,
    clean_closeout_rate: float,
    followup_churn_rate: float,
    merge_calibration_rate: float,
    validation_calibration_rate: float,
    delegation_value_calibration_rate: float,
) -> float:
    score = (
        (0.24 * (1.0 - _unit_interval(delegation_regret_rate)))
        + (0.22 * _unit_interval(clean_closeout_rate))
        + (0.16 * (1.0 - _unit_interval(followup_churn_rate)))
        + (0.14 * _unit_interval(merge_calibration_rate))
        + (0.14 * _unit_interval(validation_calibration_rate))
        + (0.10 * _unit_interval(delegation_value_calibration_rate))
    )
    return round(_unit_interval(score), 3)


def summarize(
    *,
    repo_root: Path,
    limit: int = 256,
) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc)
    rows = load_events(repo_root=repo_root, limit=limit)
    packet_rows = [
        {"_recorded_at": _normalize_string(row.get("recorded_at")), **_mapping_value(row.get("payload"))}
        for row in rows
        if _normalize_token(row.get("event_type")) == "packet"
    ]
    router_rows = [
        {"_recorded_at": _normalize_string(row.get("recorded_at")), **_mapping_value(row.get("payload"))}
        for row in rows
        if _normalize_token(row.get("event_type")) == "router_outcome"
    ]
    orchestration_rows = [
        {"_recorded_at": _normalize_string(row.get("recorded_at")), **_mapping_value(row.get("payload"))}
        for row in rows
        if _normalize_token(row.get("event_type")) == "orchestration_feedback"
    ]

    packet_benchmark_matches = [
        {
            "_recorded_at": _normalize_string(row.get("_recorded_at")),
            **_mapping_value(row.get("benchmark")),
        }
        for row in packet_rows
        if isinstance(row.get("benchmark"), Mapping)
    ]
    packet_match_rate = _weighted_rate(packet_benchmark_matches, lambda row: _int_value(row.get("matched_case_count")) > 0, now=now)
    packet_satisfaction_rate = _weighted_rate(
        packet_benchmark_matches,
        lambda row: _int_value(row.get("satisfied_case_count")) > 0,
        now=now,
    )
    within_budget_rate = _weighted_rate(packet_rows, lambda row: _bool_value(row.get("within_budget")), now=now)
    route_ready_rate = _weighted_rate(packet_rows, lambda row: _bool_value(row.get("route_ready")), now=now)
    deep_reasoning_ready_rate = _weighted_rate(
        packet_rows,
        lambda row: _bool_value(row.get("deep_reasoning_ready")),
        now=now,
    )
    avg_effective_yield_score = round(
        sum(_packet_yield_score(row) for row in packet_rows) / float(max(1, len(packet_rows))),
        3,
    )
    high_yield_rate = _weighted_rate(
        packet_rows,
        lambda row: _packet_yield_score(row) >= 0.72,
        now=now,
    )

    router_acceptance_rate = _weighted_rate(router_rows, lambda row: _bool_value(row.get("accepted")), now=now)
    router_failure_rate = _weighted_rate(
        router_rows,
        lambda row: any(
            _bool_value(row.get(key))
            for key in ("blocked", "ambiguous", "artifact_missing", "quality_too_weak", "broader_coordination")
        ),
        now=now,
    )
    router_escalation_rate = _weighted_rate(router_rows, lambda row: _bool_value(row.get("escalated")), now=now)
    router_hold_local_pressure_rate = _weighted_rate(
        router_rows,
        lambda row: _normalize_token(row.get("odylith_execution_delegate_preference")) == "hold_local",
        now=now,
    )

    orchestration_acceptance_rate = _weighted_rate(
        orchestration_rows,
        lambda row: _bool_value(row.get("accepted")),
        now=now,
    )
    orchestration_token_efficiency_rate = _weighted_rate(
        orchestration_rows,
        lambda row: _bool_value(row.get("token_efficient")),
        now=now,
    )
    orchestration_parallel_failure_rate = _weighted_rate(
        orchestration_rows,
        lambda row: _bool_value(row.get("false_parallelization")) or _int_value(row.get("merge_conflicts")) > 0,
        now=now,
    )
    orchestration_rescope_rate = _weighted_rate(
        orchestration_rows,
        lambda row: _bool_value(row.get("rescope_required")),
        now=now,
    )
    orchestration_closeout_rows = [
        row for row in orchestration_rows if _bool_value(row.get("closure_available"))
    ]
    clean_closeout_rate = _weighted_rate(
        orchestration_closeout_rows,
        lambda row: _float_value(row.get("clean_closeout_rate")) >= 0.99,
        now=now,
    )
    followup_churn_rate = _weighted_rate(
        orchestration_closeout_rows,
        lambda row: _normalize_token(row.get("closure_state")) in {"followup_heavy", "stalled"}
        or _float_value(row.get("followup_active_rate")) >= 0.34,
        now=now,
    )
    stalled_closeout_rate = _weighted_rate(
        orchestration_closeout_rows,
        lambda row: _normalize_token(row.get("closure_state")) == "stalled"
        or _float_value(row.get("stalled_closeout_rate")) > 0.0,
        now=now,
    )
    delegation_regret_rate = _weighted_rate(
        orchestration_rows,
        lambda row: _actual_delegation_value_score(row) <= 1,
        now=now,
    )
    merge_calibration = _weighted_calibration_metrics(
        orchestration_rows,
        predicted_key="predicted_merge_burden_score",
        actual_score=_actual_merge_friction_score,
        now=now,
    )
    validation_calibration = _weighted_calibration_metrics(
        orchestration_rows,
        predicted_key="predicted_validation_pressure_score",
        actual_score=_actual_validation_friction_score,
        now=now,
    )
    delegation_value_calibration = _weighted_calibration_metrics(
        orchestration_rows,
        predicted_key="predicted_expected_delegation_value_score",
        actual_score=_actual_delegation_value_score,
        now=now,
    )

    packet_recent, packet_previous = _split_recent(packet_rows)
    router_recent, router_previous = _split_recent(router_rows)
    orchestration_recent, orchestration_previous = _split_recent(orchestration_rows)

    packet_trend = _trend_label(
        _rate(packet_recent, lambda row: _bool_value(row.get("within_budget")) and _bool_value(row.get("route_ready"))),
        _rate(packet_previous, lambda row: _bool_value(row.get("within_budget")) and _bool_value(row.get("route_ready"))),
    )
    router_trend = _trend_label(
        _rate(router_recent, lambda row: _bool_value(row.get("accepted"))),
        _rate(router_previous, lambda row: _bool_value(row.get("accepted"))),
    )
    orchestration_trend = _trend_label(
        _rate(orchestration_recent, lambda row: _bool_value(row.get("token_efficient")) and not _bool_value(row.get("rescope_required"))),
        _rate(orchestration_previous, lambda row: _bool_value(row.get("token_efficient")) and not _bool_value(row.get("rescope_required"))),
    )

    improving_votes = sum(1 for token in (packet_trend, router_trend, orchestration_trend) if token == "improving")
    regressing_votes = sum(1 for token in (packet_trend, router_trend, orchestration_trend) if token == "regressing")
    learning_state = "improving" if improving_votes > regressing_votes else "regressing" if regressing_votes > improving_votes else "stable"
    signal_conflict = improving_votes > 0 and regressing_votes > 0
    freshness = {
        "overall": _freshness_snapshot(rows, now=now),
        "packet": _freshness_snapshot(packet_rows, now=now),
        "router": _freshness_snapshot(router_rows, now=now),
        "orchestration": _freshness_snapshot(orchestration_rows, now=now),
    }
    evidence_strength = _evidence_strength(
        packet_count=len(packet_rows),
        router_count=len(router_rows),
        orchestration_count=len(orchestration_rows),
        freshness_bucket=str(freshness["overall"].get("bucket", "")).strip(),
        signal_conflict=signal_conflict,
    )
    decision_quality_confidence = _decision_quality_confidence(
        orchestration_count=len(orchestration_rows),
        closeout_count=len(orchestration_closeout_rows),
        merge_coverage=int(merge_calibration.get("coverage", 0) or 0),
        validation_coverage=int(validation_calibration.get("coverage", 0) or 0),
        delegation_coverage=int(delegation_value_calibration.get("coverage", 0) or 0),
        freshness_bucket=str(freshness["orchestration"].get("bucket", "")).strip(),
        signal_conflict=signal_conflict,
    )
    decision_quality_score = _decision_quality_score(
        delegation_regret_rate=delegation_regret_rate,
        clean_closeout_rate=clean_closeout_rate,
        followup_churn_rate=followup_churn_rate,
        merge_calibration_rate=float(merge_calibration.get("rate", 0.0) or 0.0),
        validation_calibration_rate=float(validation_calibration.get("rate", 0.0) or 0.0),
        delegation_value_calibration_rate=float(delegation_value_calibration.get("rate", 0.0) or 0.0),
    )
    decision_quality_reliable = bool(
        int(decision_quality_confidence.get("score", 0) or 0) >= 3
        and float(decision_quality_confidence.get("closeout_observation_rate", 0.0) or 0.0) >= 0.34
    )
    decision_quality_state = str(decision_quality_confidence.get("state", "")).strip() or "insufficient"
    if decision_quality_reliable:
        if decision_quality_score >= 0.72:
            decision_quality_state = "trusted"
        elif decision_quality_score >= 0.55:
            decision_quality_state = "balanced"
        else:
            decision_quality_state = "fragile"
    alignment_field_pairs = (
        ("packet_strategy", "advisory_packet_strategy"),
        ("budget_mode", "advisory_budget_mode"),
        ("retrieval_focus", "advisory_retrieval_focus"),
        ("speed_mode", "advisory_speed_mode"),
    )
    alignment_scores: list[float] = []
    reliable_alignment_scores: list[float] = []
    reliable_packet_rows: list[dict[str, Any]] = []
    for row in packet_rows:
        comparisons = 0
        matches = 0
        for actual_key, advisory_key in alignment_field_pairs:
            actual_value = _normalize_token(row.get(actual_key))
            advisory_value = _normalize_token(row.get(advisory_key))
            if not actual_value or not advisory_value:
                continue
            comparisons += 1
            if actual_value == advisory_value:
                matches += 1
        if comparisons == 0:
            continue
        score = matches / comparisons
        alignment_scores.append(score)
        if (
            _int_value(row.get("advisory_confidence_score")) >= 3
            and _int_value(row.get("advisory_evidence_strength_score")) >= 3
            and _normalize_token(row.get("advisory_freshness_bucket")) in {"fresh", "recent"}
            and not _bool_value(row.get("advisory_signal_conflict"))
        ):
            reliable_alignment_scores.append(score)
            reliable_packet_rows.append(dict(row))
    packet_alignment_coverage = len(alignment_scores)
    packet_alignment_rate = round(sum(alignment_scores) / max(1, packet_alignment_coverage), 3)
    reliable_packet_alignment_count = len(reliable_alignment_scores)
    reliable_packet_alignment_rate = round(
        sum(reliable_alignment_scores) / max(1, reliable_packet_alignment_count),
        3,
    )
    reliable_high_yield_rate = _weighted_rate(
        reliable_packet_rows,
        lambda row: _packet_yield_score(row) >= 0.72,
        now=now,
    )
    packet_alignment_state = "insufficient"
    if packet_alignment_coverage:
        packet_alignment_state = "aligned"
        if packet_alignment_rate < 0.6:
            packet_alignment_state = "drifting"
        elif packet_alignment_rate < 0.8:
            packet_alignment_state = "mixed"
        if reliable_packet_alignment_count >= 2 and reliable_packet_alignment_rate < 0.6:
            packet_alignment_state = "drifting"
        elif (
            reliable_packet_alignment_count >= 2
            and reliable_packet_alignment_rate < 0.8
            and packet_alignment_state == "aligned"
        ):
            packet_alignment_state = "mixed"
    packet_alignment_guarded = (
        packet_alignment_coverage >= 2
        and (
            packet_alignment_state == "drifting"
            or (reliable_packet_alignment_count >= 2 and reliable_packet_alignment_rate < 0.7)
        )
    )
    yield_state = "insufficient"
    if packet_rows:
        yield_state = "efficient"
        if avg_effective_yield_score < 0.55 or high_yield_rate < 0.4:
            yield_state = "wasteful"
        elif avg_effective_yield_score < 0.72 or high_yield_rate < 0.6:
            yield_state = "mixed"
        if reliable_packet_rows and reliable_high_yield_rate < 0.45:
            yield_state = "wasteful"
    yield_guarded = bool(packet_rows) and (
        yield_state == "wasteful"
        or (yield_state == "mixed" and avg_effective_yield_score < 0.6)
    )

    depth_posture = "guarded"
    if (
        packet_satisfaction_rate >= 0.6
        and route_ready_rate >= 0.6
        and deep_reasoning_ready_rate >= 0.5
        and router_acceptance_rate >= 0.6
        and router_failure_rate <= 0.2
        and (
            not decision_quality_reliable
            or validation_calibration.get("underestimate_rate", 0.0) < 0.25
        )
    ):
        depth_posture = "promote_when_grounded"
    elif (
        router_failure_rate >= 0.35
        or packet_satisfaction_rate < 0.4
        or (
            decision_quality_reliable
            and (
                validation_calibration.get("underestimate_rate", 0.0) >= 0.25
                or stalled_closeout_rate >= 0.25
            )
        )
    ):
        depth_posture = "narrow_first"

    delegation_posture = "balanced"
    if (
        router_acceptance_rate >= 0.7
        and router_failure_rate <= 0.2
        and route_ready_rate >= 0.6
        and (
            not decision_quality_reliable
            or (
                delegation_regret_rate < 0.2
                and followup_churn_rate < 0.2
            )
        )
    ):
        delegation_posture = "runtime_backed_delegate"
    elif (
        router_failure_rate >= 0.35
        or router_hold_local_pressure_rate >= 0.5
        or (
            decision_quality_reliable
            and (
                delegation_regret_rate >= 0.25
                or delegation_value_calibration.get("overestimate_rate", 0.0) >= 0.25
                or followup_churn_rate >= 0.25
            )
        )
    ):
        delegation_posture = "hold_local_bias"

    parallelism_posture = "balanced"
    if (
        orchestration_parallel_failure_rate >= 0.25
        or orchestration_rescope_rate >= 0.25
        or (
            decision_quality_reliable
            and (
                merge_calibration.get("underestimate_rate", 0.0) >= 0.2
                or followup_churn_rate >= 0.25
            )
        )
    ):
        parallelism_posture = "guarded"
    elif (
        orchestration_acceptance_rate >= 0.7
        and orchestration_token_efficiency_rate >= 0.6
        and merge_calibration.get("rate", 0.0) >= 0.65
        and clean_closeout_rate >= 0.6
    ):
        parallelism_posture = "allow_when_disjoint"

    packet_strategy = "balanced"
    if within_budget_rate < 0.75 or router_failure_rate >= 0.3:
        packet_strategy = "precision_first"
    elif within_budget_rate >= 0.85 and packet_satisfaction_rate >= 0.6 and _avg(packet_rows, "context_density_score") >= 2.5:
        packet_strategy = "density_first"

    retrieval_focus = "balanced"
    if packet_match_rate < 0.6:
        retrieval_focus = "expand_coverage"
    elif packet_satisfaction_rate < 0.4:
        retrieval_focus = "precision_repair"
    elif within_budget_rate < 0.75 and packet_match_rate >= 0.6:
        retrieval_focus = "compact_grounded"

    budget_mode = "balanced"
    if (
        within_budget_rate < 0.75
        or (orchestration_rows and orchestration_token_efficiency_rate < 0.4)
        or (decision_quality_reliable and followup_churn_rate >= 0.25)
    ):
        budget_mode = "tight"
    elif (
        within_budget_rate >= 0.85
        and packet_satisfaction_rate >= 0.6
        and route_ready_rate >= 0.6
        and deep_reasoning_ready_rate >= 0.5
    ):
        budget_mode = "spend_when_grounded"

    reasoning_mode = "balanced"
    if depth_posture == "promote_when_grounded" and packet_strategy == "density_first":
        reasoning_mode = "earn_depth"
    elif (
        depth_posture == "narrow_first"
        or packet_strategy == "precision_first"
        or (
            decision_quality_reliable
            and validation_calibration.get("underestimate_rate", 0.0) >= 0.25
        )
    ):
        reasoning_mode = "guarded_narrowing"

    speed_mode = "balanced"
    if delegation_posture == "runtime_backed_delegate" and parallelism_posture == "allow_when_disjoint":
        speed_mode = "accelerate_grounded"
    elif delegation_posture == "hold_local_bias" or budget_mode == "tight":
        speed_mode = "conserve"

    control_focus_areas: list[str] = []
    if packet_match_rate < 0.6:
        control_focus_areas.append("coverage")
    if packet_satisfaction_rate < 0.5:
        control_focus_areas.append("grounding")
    if route_ready_rate < 0.6:
        control_focus_areas.append("route_readiness")
    if within_budget_rate < 0.75:
        control_focus_areas.append("budget")
    if router_failure_rate >= 0.3:
        control_focus_areas.append("delegation")
    if orchestration_parallel_failure_rate >= 0.25:
        control_focus_areas.append("parallelism")
    if orchestration_rows and orchestration_token_efficiency_rate < 0.5:
        control_focus_areas.append("token_efficiency")
    if decision_quality_reliable and delegation_regret_rate >= 0.25:
        control_focus_areas.append("delegation_regret")
    if decision_quality_reliable and merge_calibration.get("rate", 0.0) and merge_calibration.get("rate", 0.0) < 0.65:
        control_focus_areas.append("merge_calibration")
    if decision_quality_reliable and validation_calibration.get("rate", 0.0) and validation_calibration.get("rate", 0.0) < 0.65:
        control_focus_areas.append("validation_calibration")
    if decision_quality_reliable and (followup_churn_rate >= 0.25 or stalled_closeout_rate >= 0.2):
        control_focus_areas.append("closeout_quality")
    if not decision_quality_reliable and orchestration_rows:
        control_focus_areas.append("decision_quality_confidence")
    if packet_alignment_guarded:
        control_focus_areas.append("packetizer_alignment")
    if yield_guarded:
        control_focus_areas.append("evidence_yield")

    advisory_confidence_score = int(evidence_strength.get("score", 0) or 0)
    advisory_state = learning_state if advisory_confidence_score >= 2 else "bootstrap"
    if str(freshness["overall"].get("bucket", "")).strip() == "stale" and advisory_confidence_score <= 2:
        advisory_state = "stale"
    if packet_alignment_guarded and advisory_state not in {"bootstrap", "stale"}:
        advisory_state = "guarded"
    if yield_guarded and advisory_state not in {"bootstrap", "stale"}:
        advisory_state = "guarded"

    regressions: list[str] = []
    if router_failure_rate >= 0.35:
        regressions.append("delegated_router_failure_rate_high")
    if orchestration_parallel_failure_rate >= 0.25:
        regressions.append("parallel_orchestration_regression")
    if packet_satisfaction_rate < 0.4 and packet_rows:
        regressions.append("benchmark_satisfaction_weak")
    if within_budget_rate < 0.75 and packet_rows:
        regressions.append("packet_budget_regression")
    if decision_quality_reliable and delegation_regret_rate >= 0.25:
        regressions.append("delegation_regret_high")
    if decision_quality_reliable and merge_calibration.get("underestimate_rate", 0.0) >= 0.2:
        regressions.append("merge_burden_underestimated")
    if decision_quality_reliable and validation_calibration.get("underestimate_rate", 0.0) >= 0.25:
        regressions.append("validation_pressure_underestimated")
    if decision_quality_reliable and followup_churn_rate >= 0.25:
        regressions.append("followup_churn_high")
    if decision_quality_reliable and stalled_closeout_rate >= 0.2:
        regressions.append("closeout_stall_detected")
    if decision_quality_reliable and decision_quality_state == "fragile":
        regressions.append("decision_quality_fragile")
    if signal_conflict:
        regressions.append("mixed_learning_signals")
    if str(freshness["overall"].get("bucket", "")).strip() == "stale" and rows:
        regressions.append("stale_learning_history")
    if packet_alignment_guarded:
        regressions.append("packetizer_alignment_drift")
    if yield_guarded:
        regressions.append("packet_yield_regression")

    recommendations: list[str] = []
    if str(freshness["overall"].get("bucket", "")).strip() in {"aging", "stale"} and rows:
        recommendations.append(
            "Recent self-evaluation evidence is aging or stale; prefer guarded local execution until fresh packet and router outcomes refresh the advisory loop."
        )
    if str(evidence_strength.get("sample_balance", "")).strip() in {"thin", "partial"} and rows:
        recommendations.append(
            "Advisory evidence is still thin or imbalanced; treat control posture as provisional until more packet, router, and orchestration outcomes accumulate."
        )
    if orchestration_rows and not decision_quality_reliable:
        recommendations.append(
            "Decision-quality evidence is still thin or only partially observed; treat delegation regret and closeout calibration as provisional until more delegated slices fully close out."
        )
    if packet_rows and packet_strategy == "precision_first":
        recommendations.append(
            "Prefer tighter anchor selection and earlier compaction because recent packets are missing budget or drifting on outcome quality."
        )
    if yield_guarded:
        recommendations.append(
            "Recent retained packets are not delivering enough grounded signal per budget; tighten evidence selection and depth spend until effective yield improves."
        )
    if delegation_posture == "hold_local_bias":
        recommendations.append(
            "Bias toward hold-local or narrower delegated slices until router acceptance recovers on grounded packets."
        )
    if decision_quality_reliable and delegation_regret_rate >= 0.25:
        recommendations.append(
            "Recent delegated slices are producing regret or churn after execution; shrink delegated scope and require stronger route readiness before spending more fan-out."
        )
    if decision_quality_reliable and merge_calibration.get("underestimate_rate", 0.0) >= 0.2:
        recommendations.append(
            "Odylith is underpredicting merge burden on recent delegated slices; guard parallel write fan-out until predicted merge cost matches actual closeout friction."
        )
    if decision_quality_reliable and validation_calibration.get("underestimate_rate", 0.0) >= 0.25:
        recommendations.append(
            "Odylith is underpredicting validation pressure on recent delegated slices; favor narrower packets and stronger validation-oriented reasoning until calibration recovers."
        )
    if decision_quality_reliable and (followup_churn_rate >= 0.25 or stalled_closeout_rate >= 0.2):
        recommendations.append(
            "Recent delegated leaves are accumulating follow-up churn or stalled closeout; treat clean integration as a first-class success gate instead of trusting raw acceptance alone."
        )
    if parallelism_posture == "guarded":
        recommendations.append(
            "Keep write orchestration serial unless the slice is explicitly disjoint and route-ready; recent parallel outcomes show avoidable merge or false-parallel risk."
        )
    if depth_posture == "promote_when_grounded":
        recommendations.append(
            "Spend deeper reasoning only on grounded route-ready slices; recent evidence shows those lanes are earning the extra depth."
        )
    if packet_alignment_guarded:
        recommendations.append(
            "Packetizer alignment is drifting from recent measured advice; keep depth and delegation conservative until retained packet strategy and budget mode match the measured advisory loop again."
        )

    return {
        "contract": "odylith_learning_summary.v1",
        "version": "v1",
        "generated_utc": _utc_now(),
        "event_count": len(rows),
        "packet_events": {
            "count": len(packet_rows),
            "within_budget_rate": within_budget_rate,
            "route_ready_rate": route_ready_rate,
            "deep_reasoning_ready_rate": deep_reasoning_ready_rate,
            "avg_context_density_score": _avg(packet_rows, "context_density_score"),
            "avg_reasoning_readiness_score": _avg(packet_rows, "reasoning_readiness_score"),
            "avg_effective_yield_score": avg_effective_yield_score,
            "high_yield_rate": high_yield_rate,
            "reliable_high_yield_rate": reliable_high_yield_rate,
            "yield_state": yield_state,
            "benchmark_match_rate": packet_match_rate,
            "benchmark_satisfaction_rate": packet_satisfaction_rate,
            "advisory_alignment_rate": packet_alignment_rate,
            "advisory_alignment_coverage": packet_alignment_coverage,
            "reliable_advisory_alignment_rate": reliable_packet_alignment_rate,
            "reliable_advisory_alignment_count": reliable_packet_alignment_count,
            "alignment_state": packet_alignment_state,
        },
        "router_outcomes": {
            "count": len(router_rows),
            "acceptance_rate": router_acceptance_rate,
            "failure_rate": router_failure_rate,
            "escalation_rate": router_escalation_rate,
            "hold_local_pressure_rate": router_hold_local_pressure_rate,
        },
        "orchestration_feedback": {
            "count": len(orchestration_rows),
            "acceptance_rate": orchestration_acceptance_rate,
            "token_efficiency_rate": orchestration_token_efficiency_rate,
            "parallel_failure_rate": orchestration_parallel_failure_rate,
            "rescope_rate": orchestration_rescope_rate,
            "delegation_regret_rate": delegation_regret_rate,
            "clean_closeout_rate": clean_closeout_rate,
            "followup_churn_rate": followup_churn_rate,
            "stalled_closeout_rate": stalled_closeout_rate,
        },
        "decision_quality": {
            "coverage": {
                "orchestration_rows": len(orchestration_rows),
                "closeout_rows": len(orchestration_closeout_rows),
                "merge_calibration_rows": int(merge_calibration.get("coverage", 0) or 0),
                "validation_calibration_rows": int(validation_calibration.get("coverage", 0) or 0),
                "delegation_value_rows": int(delegation_value_calibration.get("coverage", 0) or 0),
            },
            "aggregate_score": decision_quality_score,
            "state": decision_quality_state,
            "confidence": decision_quality_confidence,
            "closeout_observation_rate": float(
                decision_quality_confidence.get("closeout_observation_rate", 0.0) or 0.0
            ),
            "calibration_observation_rate": float(
                decision_quality_confidence.get("calibration_observation_rate", 0.0) or 0.0
            ),
            "delegation_regret_rate": delegation_regret_rate,
            "clean_closeout_rate": clean_closeout_rate,
            "followup_churn_rate": followup_churn_rate,
            "stalled_closeout_rate": stalled_closeout_rate,
            "merge_burden_calibration_rate": float(merge_calibration.get("rate", 0.0) or 0.0),
            "merge_burden_underestimate_rate": float(
                merge_calibration.get("underestimate_rate", 0.0) or 0.0
            ),
            "validation_pressure_calibration_rate": float(validation_calibration.get("rate", 0.0) or 0.0),
            "validation_pressure_underestimate_rate": float(
                validation_calibration.get("underestimate_rate", 0.0) or 0.0
            ),
            "delegation_value_calibration_rate": float(
                delegation_value_calibration.get("rate", 0.0) or 0.0
            ),
            "delegation_overreach_rate": float(
                delegation_value_calibration.get("overestimate_rate", 0.0) or 0.0
            ),
        },
        "trend_posture": {
            "packet_trend": packet_trend,
            "router_trend": router_trend,
            "orchestration_trend": orchestration_trend,
            "learning_state": learning_state,
            "signal_conflict": signal_conflict,
        },
        "control_posture": {
            "depth": depth_posture,
            "delegation": delegation_posture,
            "parallelism": parallelism_posture,
            "packet_strategy": packet_strategy,
            "budget_mode": budget_mode,
            "retrieval_focus": retrieval_focus,
            "speed_mode": speed_mode,
            "packet_alignment_state": packet_alignment_state,
            "yield_state": yield_state,
        },
        "freshness": freshness,
        "evidence_strength": evidence_strength,
        "control_advisories": {
            "state": advisory_state,
            "confidence": {
                "score": advisory_confidence_score,
                "level": _confidence_level(advisory_confidence_score),
            },
            "reasoning_mode": reasoning_mode,
            "depth": depth_posture,
            "delegation": delegation_posture,
            "parallelism": parallelism_posture,
            "packet_strategy": packet_strategy,
            "budget_mode": budget_mode,
            "retrieval_focus": retrieval_focus,
            "speed_mode": speed_mode,
            "freshness": dict(freshness["overall"]),
            "evidence_strength": dict(evidence_strength),
            "packet_alignment_rate": packet_alignment_rate,
            "packet_alignment_coverage": packet_alignment_coverage,
            "reliable_packet_alignment_rate": reliable_packet_alignment_rate,
            "reliable_packet_alignment_count": reliable_packet_alignment_count,
            "packet_alignment_state": packet_alignment_state,
            "effective_yield_score": avg_effective_yield_score,
            "high_yield_rate": high_yield_rate,
            "reliable_high_yield_rate": reliable_high_yield_rate,
            "yield_state": yield_state,
            "signal_conflict": signal_conflict,
            "decision_quality_score": decision_quality_score,
            "decision_quality_state": decision_quality_state,
            "decision_quality_confidence": decision_quality_confidence,
            "delegation_regret_rate": delegation_regret_rate,
            "clean_closeout_rate": clean_closeout_rate,
            "followup_churn_rate": followup_churn_rate,
            "merge_burden_calibration_rate": float(merge_calibration.get("rate", 0.0) or 0.0),
            "validation_pressure_calibration_rate": float(validation_calibration.get("rate", 0.0) or 0.0),
            "delegation_value_calibration_rate": float(
                delegation_value_calibration.get("rate", 0.0) or 0.0
            ),
            "focus_areas": control_focus_areas[:4],
            "regressions": regressions[:4],
        },
        "regressions": regressions,
        "recommendations": recommendations[:4],
    }


__all__ = [
    "LEDGER_CONTRACT",
    "LEDGER_FILENAME",
    "append_event",
    "ledger_path",
    "load_events",
    "orchestration_feedback_event_payload",
    "packet_event_payload",
    "router_outcome_event_payload",
    "summarize",
]
