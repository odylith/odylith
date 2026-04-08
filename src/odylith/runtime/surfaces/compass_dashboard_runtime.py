"""Compass runtime payload, digest, and history builders.

This module owns the high-churn runtime shaping that used to live inside the
monolithic Compass renderer file. It deliberately imports the shared Compass
base helpers wholesale so the first decomposition slice can stay behavior
identical while the facade remains stable.
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.surfaces import compass_outcome_digest_runtime
from odylith.runtime.surfaces import compass_narrative_runtime
from odylith.runtime.surfaces import compass_refresh_contract
from odylith.runtime.surfaces import compass_standup_fact_packets
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import compass_self_host_runtime
from odylith.runtime.surfaces import compass_transaction_runtime
from odylith.runtime.surfaces import compass_execution_focus_runtime
from odylith.runtime.surfaces import compass_runtime_payload_runtime
from odylith.runtime.governance import execution_wave_view_model
from odylith.runtime.evaluation import odylith_reasoning
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.context_engine import odylith_runtime_surface_summary
from odylith.runtime.surfaces.compass_dashboard_base import *  # noqa: F401,F403


_CURRENT_WORKSTREAM_MAX_ROWS = 12
_FRESHNESS_LIVE_MAX_MINUTES = 90
_FRESHNESS_RECENT_MAX_MINUTES = 6 * 60
_FRESHNESS_AGING_MAX_MINUTES = 24 * 60
DEFAULT_HISTORY_RETENTION_DAYS = 15


def _global_brief_should_use_provider(
    *,
    repo_root: Path,
    fact_packet: Mapping[str, Any],
    window_hours: int,
) -> bool:
    if int(window_hours) in {24, 48}:
        return True
    return not compass_standup_brief_narrator.has_reusable_cached_brief(
        repo_root=repo_root,
        fact_packet=fact_packet,
    )


def _global_brief_provider_allowed(
    *,
    repo_root: Path,
    fact_packet: Mapping[str, Any],
    window_hours: int,
    refresh_profile: str,
) -> bool:
    if not compass_refresh_contract.full_refresh_requested(refresh_profile):
        return False
    return _global_brief_should_use_provider(
        repo_root=repo_root,
        fact_packet=fact_packet,
        window_hours=window_hours,
    )


def _timeline_event_priority(row: Mapping[str, Any]) -> int:
    kind = str(row.get("kind", "")).strip().lower()
    kind_score = {
        "implementation": 100,
        "decision": 95,
        "statement": 90,
        "plan_completion": 84,
        "plan_update": 80,
        "bug_resolved": 74,
        "bug_update": 70,
        "bug_watch": 66,
        "commit": 58,
        "local_change": 44,
    }.get(kind, 50)

    ws = [str(item).strip() for item in row.get("workstreams", []) if str(item).strip()]
    if ws:
        kind_score += 24

    files = [str(item).strip() for item in row.get("files", []) if str(item).strip()]
    source_files, generated_files = _split_source_vs_generated_files(files)
    if source_files:
        kind_score += min(12, len(source_files))
    if generated_files and not source_files:
        kind_score -= 36
    elif generated_files:
        kind_score -= 8
    return kind_score


def _select_timeline_source_events(
    *,
    events: Sequence[Mapping[str, Any]],
    now: dt.datetime,
    lookback_hours: int = _TIMELINE_EVENT_LOOKBACK_HOURS,
    max_rows: int = _TIMELINE_EVENT_MAX_ROWS,
) -> list[dict[str, Any]]:
    typed: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        ts = event.get("ts")
        if not isinstance(ts, dt.datetime):
            continue
        typed.append(dict(event))

    if not typed:
        return []

    lookback = max(24, int(lookback_hours))
    cutoff = now - dt.timedelta(hours=lookback)
    recent = [row for row in typed if isinstance(row.get("ts"), dt.datetime) and row["ts"] >= cutoff]
    pool = recent if recent else typed

    ranked = sorted(
        pool,
        key=lambda row: (
            _timeline_event_priority(row),
            row.get("ts", now),
            str(row.get("id", "")).strip(),
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    generated_noise: list[dict[str, Any]] = []
    max_allowed = max(64, int(max_rows))
    for row in ranked:
        kind = str(row.get("kind", "")).strip().lower()
        files = [str(item).strip() for item in row.get("files", []) if str(item).strip()]
        source_files, generated_files = _split_source_vs_generated_files(files)
        generated_only_local = kind == "local_change" and not source_files and bool(generated_files)
        if generated_only_local:
            generated_noise.append(row)
            continue
        selected.append(row)
        if len(selected) >= max_allowed:
            break

    if len(selected) < max_allowed and generated_noise:
        dynamic_noise_budget = max(16, max_allowed // 4)
        noise_budget = min(
            _TIMELINE_GENERATED_NOISE_MAX_ROWS,
            dynamic_noise_budget,
            max_allowed - len(selected),
        )
        selected.extend(generated_noise[:noise_budget])

    selected.sort(
        key=lambda row: (
            row.get("ts", now),
            str(row.get("id", "")).strip(),
        ),
        reverse=True,
    )
    return selected


def _event_public_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    ts = event.get("ts")
    ts_iso = str(event.get("ts_iso", "")).strip()
    if not ts_iso and isinstance(ts, dt.datetime):
        ts_iso = _safe_iso(ts)
    return {
        "id": str(event.get("id", "")).strip(),
        "kind": str(event.get("kind", "")).strip(),
        "ts_iso": ts_iso,
        "summary": str(event.get("summary", "")).strip(),
        "author": str(event.get("author", "")).strip(),
        "sha": str(event.get("sha", "")).strip(),
        "workstreams": [
            str(item).strip()
            for item in event.get("workstreams", [])
            if str(item).strip()
        ],
        "files": [
            str(item).strip()
            for item in event.get("files", [])
            if str(item).strip()
        ][:64],
        "source": str(event.get("source", "")).strip(),
        "session_id": str(event.get("session_id", "")).strip(),
        "transaction_id": str(event.get("transaction_id", "")).strip(),
        "transaction_seq": event.get("transaction_seq"),
        "transaction_boundary": str(event.get("transaction_boundary", "")).strip(),
        "context": str(event.get("context", "")).strip(),
        "headline_hint": str(event.get("headline_hint", "")).strip(),
    }


def _self_host_snapshot(*, repo_root: Path) -> dict[str, Any]:
    return compass_self_host_runtime.self_host_snapshot(repo_root=repo_root)


def _self_host_risk_rows(*, snapshot: Mapping[str, Any], local_date: str) -> list[dict[str, Any]]:
    return compass_self_host_runtime.self_host_risk_rows(snapshot=snapshot, local_date=local_date)


def _self_host_release_eligibility_label(value: object) -> str:
    return compass_self_host_runtime.self_host_release_eligibility_label(value)


def _self_host_status_fact(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    return compass_self_host_runtime.self_host_status_fact(
        snapshot,
        standup_fact_builder=_standup_fact,
    )


def _transaction_scope_phrase(workstreams: Sequence[str]) -> str:
    return compass_transaction_runtime._transaction_scope_phrase(workstreams)


def _is_generated_narrative_file(path: str) -> bool:
    return compass_transaction_runtime._is_generated_narrative_file(path)


def _is_generated_narrative_token(token: str) -> bool:
    return compass_transaction_runtime._is_generated_narrative_token(token)


def _split_source_vs_generated_files_cached(files: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return compass_transaction_runtime._split_source_vs_generated_files_cached(files)


def _normalized_file_tuple(files: Sequence[str]) -> tuple[str, ...]:
    return compass_transaction_runtime._normalized_file_tuple(files)


def _split_source_vs_generated_files(files: Sequence[str]) -> tuple[list[str], list[str]]:
    return compass_transaction_runtime._split_source_vs_generated_files(files)


def _local_change_surface_label(path: str) -> str:
    return compass_transaction_runtime._local_change_surface_label(path)


def _is_generated_only_local_change_event(row: Mapping[str, Any]) -> bool:
    return compass_transaction_runtime._is_generated_only_local_change_event(row)


def _is_generated_only_transaction(row: Mapping[str, Any]) -> bool:
    return compass_transaction_runtime._is_generated_only_transaction(row)


def _local_change_headline_phrase(
    *,
    local_events: Sequence[Mapping[str, Any]],
    files_count: int,
) -> str:
    return compass_transaction_runtime._local_change_headline_phrase(
        local_events=local_events,
        files_count=files_count,
    )


def _is_generic_transaction_headline(text: str) -> bool:
    return compass_transaction_runtime._is_generic_transaction_headline(text)


def _select_transaction_headline_hint(tx_events: Sequence[Mapping[str, Any]]) -> str:
    return compass_transaction_runtime._select_transaction_headline_hint(tx_events)


def _plan_update_headline(*, summary: str, scope: str) -> str:
    return compass_transaction_runtime._plan_update_headline(summary=summary, scope=scope)


def _lineage_transaction_headline(*, summaries: Sequence[str], scope: str) -> str:
    return compass_transaction_runtime._lineage_transaction_headline(summaries=summaries, scope=scope)


def _build_transaction_headline(
    *,
    tx_events: Sequence[Mapping[str, Any]],
    tx_context: str,
    workstreams: Sequence[str],
    files_count: int,
) -> str:
    return compass_transaction_runtime._build_transaction_headline(
        tx_events=tx_events,
        tx_context=tx_context,
        workstreams=workstreams,
        files_count=files_count,
    )


def _is_transaction_support_file(path: str, *, repo_root: Path | None = None) -> bool:
    return compass_transaction_runtime._is_transaction_support_file(path, repo_root=repo_root)


def _transaction_shadow_facts(
    row: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    return compass_transaction_runtime._transaction_shadow_facts(row, repo_root=repo_root)


def _should_suppress_shadowed_auto_transaction_facts(
    candidate_facts: Mapping[str, Any],
    other_facts: Mapping[str, Any],
    *,
    proximity_minutes: int = 10,
) -> bool:
    return compass_transaction_runtime._should_suppress_shadowed_auto_transaction_facts(
        candidate_facts,
        other_facts,
        proximity_minutes=proximity_minutes,
    )


def _compact_shadowed_auto_transactions(
    payloads: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    return compass_transaction_runtime._compact_shadowed_auto_transactions(payloads, repo_root=repo_root)


def _build_prompt_transactions(
    *,
    events: Sequence[Mapping[str, Any]],
    inactivity_minutes: int = 2,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    return compass_transaction_runtime._build_prompt_transactions(
        events=events,
        inactivity_minutes=inactivity_minutes,
        repo_root=repo_root,
    )


def _build_execution_focus_payload(
    *,
    transactions: Sequence[Mapping[str, Any]],
    now: dt.datetime,
    active_window_minutes: int = _DEFAULT_ACTIVE_WINDOW_MINUTES,
    recent_window_minutes: int = _DEFAULT_RECENT_FOCUS_WINDOW_MINUTES,
) -> dict[str, Any]:
    return compass_execution_focus_runtime._build_execution_focus_payload(
        transactions=transactions,
        now=now,
        active_window_minutes=active_window_minutes,
        recent_window_minutes=recent_window_minutes,
    )


def _cost_base_index(*, sizing: str, complexity: str) -> int:
    size = _SIZE_SCORE.get(str(sizing or "").strip(), 3)
    comp = _COMPLEXITY_SCORE.get(str(complexity or "").strip(), 2)
    raw = (size * 10) + (comp * 8)
    min_raw = (_SIZE_SCORE["XS"] * 10) + (_COMPLEXITY_SCORE["Low"] * 8)
    max_raw = (_SIZE_SCORE["XL"] * 10) + (_COMPLEXITY_SCORE["VeryHigh"] * 8)
    if max_raw <= min_raw:
        return 50
    ratio = (raw - min_raw) / (max_raw - min_raw)
    return int(max(0, min(100, round(ratio * 100))))


def _cost_with_activity(base_index: int, *, commit_count: int, local_count: int) -> tuple[int, str]:
    intensity = min(1.0, ((commit_count * 2) + local_count) / 12.0)
    modifier = int(round(intensity * 20))
    score = int(max(0, min(100, base_index + modifier)))
    if score >= 70:
        band = "High"
    elif score >= 40:
        band = "Medium"
    else:
        band = "Low"
    return score, band


def _timeline_projection(*, age_days: int, total_tasks: int, done_tasks: int) -> tuple[int | None, str]:
    if total_tasks <= 0:
        return None, "low"
    if done_tasks <= 0:
        return None, "low"
    if done_tasks >= total_tasks:
        return 0, "high"
    if age_days < 2 or total_tasks < 3:
        return None, "low"

    throughput = done_tasks / max(age_days, 1)
    if throughput <= 0:
        return None, "low"
    remaining = max(0, total_tasks - done_tasks)
    eta = int(math.ceil(remaining / throughput))

    if total_tasks >= 10 and done_tasks >= 4:
        confidence = "high"
    elif total_tasks >= 5 and done_tasks >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    return eta, confidence


def _collect_recent_completed_plan_rows(
    plan_index_path: Path,
    *,
    repo_root: Path,
    now: dt.datetime,
    hours: int,
) -> list[dict[str, str]]:
    content = _read_text(plan_index_path)
    rows: list[dict[str, str]] = []
    cutoff = now - dt.timedelta(hours=max(1, int(hours)))
    for line in content.splitlines():
        if not line.startswith("| `odylith/technical-plans/done/"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        plan_token = cells[0].strip("`")
        status = cells[1]
        updated_token = cells[3]
        backlog_token = cells[4].strip("`")
        if not _WORKSTREAM_ID_RE.fullmatch(backlog_token):
            continue
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(updated_token)
            if updated_date is None:
                continue
            # Plan index rows only carry dates; keep inclusion day-based so
            # completed-plan metrics remain stable across time-of-day.
            if not _is_bug_date_within_window(date_token=updated_date.isoformat(), now=now, hours=hours):
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)
        elif ts < cutoff:
            continue
        rows.append(
            {
                "plan": plan_token,
                "status": status,
                "updated": ts.date().isoformat(),
                "backlog": backlog_token,
            }
        )
    return rows


def _collect_recent_completed_plan_rows_for_timeline(
    plan_index_path: Path,
    *,
    repo_root: Path,
    now: dt.datetime,
    hours: int,
) -> list[dict[str, str]]:
    content = _read_text(plan_index_path)
    rows: list[dict[str, str]] = []
    cutoff = now - dt.timedelta(hours=max(1, int(hours)))
    for line in content.splitlines():
        if not line.startswith("| `odylith/technical-plans/done/"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        plan_token = cells[0].strip("`")
        status = cells[1]
        updated_token = cells[3]
        backlog_token = cells[4].strip("`")
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(updated_token)
            if updated_date is None:
                continue
            # Plan index rows only carry dates; keep inclusion day-based so
            # timeline completion events do not flap with local run time.
            if not _is_bug_date_within_window(date_token=updated_date.isoformat(), now=now, hours=hours):
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)
        elif ts < cutoff:
            continue
        rows.append(
            {
                "plan": plan_token,
                "status": status,
                "updated": ts.date().isoformat(),
                "backlog": backlog_token,
            }
        )
    return rows


def _collect_plan_checked_signals(plan_path: Path) -> tuple[list[str], list[str]]:
    decisions: list[str] = []
    completed_tasks: list[str] = []
    if not plan_path.is_file():
        return decisions, completed_tasks

    for raw in plan_path.read_text(encoding="utf-8").splitlines():
        match = _CHECKBOX_RE.match(raw)
        if match is None:
            continue
        if str(match.group("mark")).lower() != "x":
            continue
        body = " ".join(str(match.group("body")).split()).strip()
        if not body:
            continue
        lowered = body.lower()
        if lowered.startswith("risk:") or lowered.startswith("mitigation:"):
            continue
        if lowered.startswith("decision:"):
            decision = body.split(":", 1)[1].strip() if ":" in body else body
            if decision and decision not in decisions:
                decisions.append(decision)
            continue
        if body not in completed_tasks:
            completed_tasks.append(body)

    return decisions[:3], completed_tasks[:4]


def _clip_sentence(text: str, *, limit: int = 160) -> str:
    token = " ".join(str(text or "").split()).strip()
    if not token:
        return ""
    return _truncate_sentence(token, limit=limit)


def _narrative_excerpt(text: str, *, max_sentences: int = 1, max_chars: int = 220) -> str:
    token = " ".join(str(text or "").split()).strip()
    if not token:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", token)
    chosen: list[str] = []
    current_len = 0
    for sentence in sentences:
        part = sentence.strip()
        if not part:
            continue
        projected = current_len + (1 if chosen else 0) + len(part)
        if chosen and projected > max_chars:
            break
        if not chosen and len(part) > max_chars:
            return _truncate_sentence(part, limit=max_chars)
        chosen.append(part)
        current_len = projected
        if len(chosen) >= max_sentences:
            break
    if chosen:
        return " ".join(chosen)
    return _truncate_sentence(token, limit=max_chars)


def _truncate_sentence(text: str, *, limit: int) -> str:
    token = " ".join(str(text or "").split()).strip()
    if not token:
        return ""
    if len(token) <= limit:
        return token
    if limit <= 4:
        return token[:limit]
    hard_limit = max(1, limit - 3)
    boundary = token.rfind(" ", 0, hard_limit + 1)
    if boundary < int(hard_limit * 0.6):
        boundary = hard_limit
    clipped = token[:boundary].rstrip(" ,;:-")
    if not clipped:
        clipped = token[:hard_limit].rstrip()
    return f"{clipped}..."


def _normalize_sentence(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _periodize(text: str) -> str:
    token = _normalize_sentence(text)
    if not token:
        return ""
    if token[-1] in ".!?":
        return token
    return f"{token}."


def _risk_phrase(risk_posture: str) -> str:
    token = _normalize_sentence(risk_posture)
    if not token:
        return "no critical blockers are currently surfaced"
    lowered = token.lower()
    if lowered.startswith("risk posture:"):
        token = token.split(":", 1)[1].strip()
    return token.rstrip(" .")


_OPERATOR_IMPACT_LEADS = (
    "lowers ",
    "reduces ",
    "improves ",
    "keeps ",
    "makes ",
    "gives ",
    "protects ",
    "preserves ",
    "supports ",
    "unlocks ",
)


def _sentence_without_period(text: str) -> str:
    return _normalize_sentence(text).rstrip(" .")


def _use_story_text(*, customer: str, problem: str, fallback: str = "") -> str:
    customer_token = _sentence_without_period(customer)
    problem_token = _sentence_without_period(problem)
    fallback_token = _sentence_without_period(fallback)
    if customer_token and problem_token:
        lowered_problem = problem_token.lower()
        if lowered_problem.startswith("need "):
            return f"{customer_token} need {problem_token[5:]}."
        if lowered_problem.startswith("needs "):
            return f"{customer_token} need {problem_token[6:]}."
        return f"For {customer_token}, {_decapitalize_clause(problem_token)}."
    if customer_token and fallback_token:
        return f"For {customer_token}, {_decapitalize_clause(fallback_token)}."
    if fallback_token:
        return _periodize(fallback_token)
    return ""


_WHY_PRIORITY_LEAD_RE = re.compile(
    r"^(?:for\s+)?(?:[-*]\s*)?(?:primary|secondary|tertiary)\s*:\s*",
    re.IGNORECASE,
)


def _normalize_why_fragment(text: str) -> str:
    token = _sentence_without_period(text)
    while token:
        normalized = _WHY_PRIORITY_LEAD_RE.sub("", token, count=1).strip()
        if normalized == token:
            return token
        token = normalized
    return ""


def _architecture_consequence_text(*, proposed_solution: str, benefit: str) -> str:
    solution_token = _sentence_without_period(proposed_solution)
    benefit_token = _sentence_without_period(benefit)
    if solution_token:
        solution_clause = _decapitalize_clause(solution_token)
        move_clause = solution_clause if solution_clause.lower().startswith("to ") else f"to {solution_clause}"
        return (
            f"The architecture move is {move_clause}, which gives operators a clearer contract and lower coordination risk."
        )
    if benefit_token:
        benefit_clause = _decapitalize_clause(benefit_token)
        if benefit_clause.lower().startswith(_OPERATOR_IMPACT_LEADS):
            return f"This gives operators a clearer contract and {benefit_clause}."
    return "This gives operators a clearer contract and lower coordination risk across dependent lanes."


def _ws_why_context(row: Mapping[str, Any]) -> dict[str, str]:
    why = row.get("why", {})
    if not isinstance(why, Mapping):
        return {
            "problem": "",
            "customer": "",
            "proposed_solution": "",
            "opportunity": "",
            "why_now": "",
            "founder_pov": "",
            "purpose": "",
            "benefit": "",
            "use_story": "",
            "architecture_consequence": "",
        }
    problem = _normalize_why_fragment(
        _narrative_excerpt(str(why.get("problem", "")).strip(), max_sentences=1, max_chars=220)
    )
    customer = _normalize_why_fragment(
        _narrative_excerpt(str(why.get("customer", "")).strip(), max_sentences=1, max_chars=160)
    )
    proposed_solution = _normalize_why_fragment(
        _narrative_excerpt(
            str(why.get("proposed_solution", "")).strip(),
            max_sentences=1,
            max_chars=220,
        )
    )
    why_now = _normalize_why_fragment(
        _narrative_excerpt(str(why.get("why_now", "")).strip(), max_sentences=1, max_chars=280)
    )
    opportunity = _normalize_why_fragment(
        _narrative_excerpt(str(why.get("opportunity", "")).strip(), max_sentences=1, max_chars=280)
    )
    founder = _normalize_why_fragment(
        _narrative_excerpt(str(why.get("founder_pov", "")).strip(), max_sentences=1, max_chars=280)
    )
    purpose = why_now or opportunity or founder or problem
    benefit = opportunity or founder or why_now or purpose
    use_story = _use_story_text(customer=customer, problem=problem, fallback=purpose)
    architecture_consequence = _architecture_consequence_text(
        proposed_solution=proposed_solution,
        benefit=benefit,
    )
    return {
        "problem": problem,
        "customer": customer,
        "proposed_solution": proposed_solution,
        "opportunity": opportunity,
        "why_now": why_now,
        "founder_pov": founder,
        "purpose": purpose,
        "benefit": benefit,
        "use_story": use_story,
        "architecture_consequence": architecture_consequence,
    }


def _ws_why_summary(row: Mapping[str, Any]) -> tuple[str, str]:
    context = _ws_why_context(row)
    purpose = context.get("purpose", "")
    benefit = context.get("benefit", "")
    return purpose, benefit


def _ws_label(row: Mapping[str, Any]) -> str:
    idea_id = str(row.get("idea_id", "")).strip()
    title = str(row.get("title", "")).strip()
    if idea_id and title and title != idea_id:
        return f"{title} ({idea_id})"
    return idea_id or title or "unknown workstream"


def _plan_deliverable_label(plan_token: str) -> str:
    path = str(plan_token or "").strip()
    if not path:
        return ""
    name = Path(path).name.replace(".md", "")
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    token = " ".join(name.replace("-", " ").split()).strip()
    return _narrative_excerpt(token, max_sentences=1, max_chars=96)


def _build_plan_timeline_events(
    *,
    repo_root: Path,
    now: dt.datetime,
    plan_index_path: Path,
    active_plan_rows: Sequence[Mapping[str, str]],
    ws_path_index: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for idx, row in enumerate(active_plan_rows, start=1):
        plan_token = str(row.get("Plan", "")).strip().strip("`")
        if not plan_token:
            continue
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(str(row.get("Updated", "")).strip())
            if updated_date is None:
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)

        backlog_token = str(row.get("Backlog", "")).strip().strip("`")
        status_token = str(row.get("Status", "")).strip() or "In progress"
        deliverable = _plan_deliverable_label(plan_token) or Path(plan_token).name.replace(".md", "")

        ws_ids: list[str] = []
        if _WORKSTREAM_ID_RE.fullmatch(backlog_token):
            ws_ids.append(backlog_token)
        ws_ids.extend(_map_paths_to_workstreams([plan_token], ws_path_index))
        ws_ids = sorted({token for token in ws_ids if _WORKSTREAM_ID_RE.fullmatch(token)})
        ws_scope = ws_ids[0] if ws_ids else "unscoped"

        progress = _collect_plan_progress(plan_path)
        done_tasks = int(progress.get("done_tasks", 0) or 0)
        total_tasks = int(progress.get("total_tasks", 0) or 0)
        if total_tasks > 0:
            summary = (
                f"Plan updated: {deliverable} ({ws_scope}) is {status_token}; "
                f"checklist {done_tasks}/{total_tasks} complete."
            )
        else:
            summary = (
                f"Plan updated: {deliverable} ({ws_scope}) is {status_token}; "
                "checklist baseline is being finalized."
            )
        events.append(
            {
                "id": f"plan:update:{idx}:{plan_token}",
                "kind": "plan_update",
                "ts": ts,
                "ts_iso": _safe_iso(ts),
                "summary": _normalize_sentence(summary),
                "author": "plan",
                "sha": "",
                "files": [plan_token],
                "workstreams": ws_ids,
                "source": "plan_index",
            }
        )

        decisions, completed_tasks = _collect_plan_checked_signals(plan_path)
        if decisions:
            decision_summary = f"Decision captured in {deliverable}: {decisions[0]}."
            events.append(
                {
                    "id": f"plan:decision:{idx}:{plan_token}",
                    "kind": "decision",
                    "ts": ts,
                    "ts_iso": _safe_iso(ts),
                    "summary": _normalize_sentence(decision_summary),
                    "author": "plan",
                    "sha": "",
                    "files": [plan_token],
                    "workstreams": ws_ids,
                    "source": "plan_file",
                }
            )
        if completed_tasks:
            impl_summary = f"Implementation checkpoint in {deliverable}: completed {completed_tasks[0]}."
            events.append(
                {
                    "id": f"plan:implementation:{idx}:{plan_token}",
                    "kind": "implementation",
                    "ts": ts,
                    "ts_iso": _safe_iso(ts),
                    "summary": _normalize_sentence(impl_summary),
                    "author": "plan",
                    "sha": "",
                    "files": [plan_token],
                    "workstreams": ws_ids,
                    "source": "plan_file",
                }
            )

    completed_rows = _collect_recent_completed_plan_rows_for_timeline(
        plan_index_path=plan_index_path,
        repo_root=repo_root,
        now=now,
        hours=48,
    )
    for idx, row in enumerate(completed_rows, start=1):
        plan_token = str(row.get("plan", "")).strip()
        if not plan_token:
            continue
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(str(row.get("updated", "")).strip())
            if updated_date is None:
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)

        backlog_token = str(row.get("backlog", "")).strip()
        ws_ids: list[str] = []
        if _WORKSTREAM_ID_RE.fullmatch(backlog_token):
            ws_ids.append(backlog_token)
        ws_ids.extend(_map_paths_to_workstreams([plan_token], ws_path_index))
        ws_ids = sorted({token for token in ws_ids if _WORKSTREAM_ID_RE.fullmatch(token)})

        deliverable = _plan_deliverable_label(plan_token) or Path(plan_token).name.replace(".md", "")
        if ws_ids:
            summary = f"Plan milestone completed: {deliverable} closed for {ws_ids[0]}."
        else:
            summary = f"Plan milestone completed: {deliverable} closed."
        events.append(
            {
                "id": f"plan:complete:{idx}:{plan_token}",
                "kind": "plan_completion",
                "ts": ts,
                "ts_iso": _safe_iso(ts),
                "summary": _normalize_sentence(summary),
                "author": "plan",
                "sha": "",
                "files": [plan_token],
                "workstreams": ws_ids,
                "source": "plan_index",
            }
        )

    return events


def _build_bug_timeline_events(
    *,
    repo_root: Path,
    now: dt.datetime,
    bugs_index_path: Path,
    bug_rows: Sequence[Mapping[str, str]],
    ws_path_index: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    cutoff = now - dt.timedelta(hours=48)

    for idx, row in enumerate(bug_rows, start=1):
        severity = str(row.get("Severity", "")).strip().upper()
        if severity not in {"P0", "P1", "P2", "P3"}:
            continue
        status = str(row.get("Status", "")).strip()
        title = " ".join(str(row.get("Title", "")).split()).strip() or "Untitled bug"

        link_path = _resolve_index_link_to_repo_path(
            repo_root=repo_root,
            index_path=bugs_index_path,
            markdown_link=str(row.get("Link", "")),
        )
        bug_path = _resolve(repo_root, link_path) if link_path else None
        ts = _file_mtime(bug_path) if bug_path is not None else None
        if ts is None:
            date_token = _parse_date(str(row.get("Date", "")).strip())
            if date_token is not None:
                ts = _date_midday_local(date_token, tz=now.tzinfo)
            else:
                ts = now

        ws_ids: list[str] = []
        ws_ids.extend(_extract_workstream_tokens_from_text(title))
        if link_path:
            ws_ids.extend(_map_paths_to_workstreams([link_path], ws_path_index))
        ws_ids = sorted({token for token in ws_ids if _WORKSTREAM_ID_RE.fullmatch(token)})

        files = [link_path] if link_path else []
        status_lower = status.lower()
        is_resolved = status_lower in {"fixed", "closed"}
        is_critical = severity in {"P0", "P1"}

        if is_critical and not is_resolved:
            summary = f"Critical bug remains open ({severity}): {title}."
            events.append(
                {
                    "id": f"bug:watch:{idx}:{severity}",
                    "kind": "bug_watch",
                    "ts": ts,
                    "ts_iso": _safe_iso(ts),
                    "summary": _normalize_sentence(summary),
                    "author": "bugs",
                    "sha": "",
                    "files": files,
                    "workstreams": ws_ids,
                    "source": "bugs_index",
                }
            )
            continue

        if ts < cutoff:
            continue

        if is_critical and is_resolved:
            kind = "bug_resolved"
            summary = f"Critical bug resolved ({severity}): {title}."
        else:
            kind = "bug_update"
            summary = f"Bug status update ({severity}, {status or 'Unknown'}): {title}."
        events.append(
            {
                "id": f"bug:{kind}:{idx}:{severity}",
                "kind": kind,
                "ts": ts,
                "ts_iso": _safe_iso(ts),
                "summary": _normalize_sentence(summary),
                "author": "bugs",
                "sha": "",
                "files": files,
                "workstreams": ws_ids,
                "source": "bugs_index",
            }
        )

    return events


def _estimate_remaining_days(row: Mapping[str, Any]) -> tuple[int, str]:
    timeline = row.get("timeline", {})
    if isinstance(timeline, Mapping):
        eta_days = timeline.get("eta_days")
        confidence = str(timeline.get("eta_confidence", "")).strip().lower()
        if isinstance(eta_days, int) and eta_days >= 0:
            source = f"model-{confidence}" if confidence else "model"
            return eta_days, source

    plan = row.get("plan", {})
    progress_ratio = float(plan.get("progress_ratio", 0.0) or 0.0) if isinstance(plan, Mapping) else 0.0
    sizing = str(row.get("sizing", "")).strip()
    complexity = str(row.get("complexity", "")).strip()
    status = str(row.get("status", "")).strip().lower()

    base_days = _SIZE_DAY_BASE.get(sizing, 10) + _COMPLEXITY_DAY_DELTA.get(complexity, 2)
    remaining_factor = max(0.2, 1.0 - progress_ratio)
    estimate = int(math.ceil(base_days * remaining_factor))
    if status == "planning" and progress_ratio <= 0.01:
        estimate += 2
    estimate = max(1, int(math.ceil(estimate * _HEURISTIC_AI_ACCELERATION_FACTOR)))
    return estimate, "heuristic"


def _build_completed_group_lines(
    recent_completed: Sequence[Mapping[str, str]],
    *,
    ws_index: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    groups: dict[str, dict[str, Any]] = {}
    for row in recent_completed:
        ws_id = str(row.get("backlog", "")).strip()
        if not _WORKSTREAM_ID_RE.fullmatch(ws_id):
            continue
        ws_row = ws_index.get(ws_id, {})
        label = _ws_label(ws_row) if ws_row else ws_id
        bucket = groups.setdefault(
            ws_id,
            {
                "label": label,
                "deliverables": [],
            },
        )
        deliverable = _plan_deliverable_label(str(row.get("plan", "")).strip())
        if deliverable and deliverable not in bucket["deliverables"]:
            bucket["deliverables"].append(deliverable)

    ordered = sorted(groups.items(), key=lambda item: (-len(item[1]["deliverables"]), item[0]))
    lines: list[str] = []
    for _ws_id, payload in ordered[:2]:
        label = str(payload.get("label", "")).strip()
        deliverables = [str(item).strip() for item in payload.get("deliverables", []) if str(item).strip()]
        if not label:
            continue
        if not deliverables:
            lines.append(f"{label} milestone closeout")
            continue
        if len(deliverables) == 1:
            lines.append(f"{label} -> {deliverables[0]}")
            continue
        if len(deliverables) == 2:
            lines.append(f"{label} -> {deliverables[0]}; {deliverables[1]}")
            continue
        lines.append(f"{label} -> {deliverables[0]}; {deliverables[1]} plus follow-on closeout deliverables")
    return lines


def _action_tokens_for_workstream(next_actions: Sequence[Mapping[str, str]], ws_id: str, *, max_items: int = 2) -> list[str]:
    tokens: list[str] = []
    for row in next_actions:
        if str(row.get("idea_id", "")).strip() != ws_id:
            continue
        action = _normalize_action_task(
            _narrative_excerpt(str(row.get("action", "")).strip().rstrip(".; "), max_sentences=1, max_chars=180)
        ).rstrip(" .;")
        if not action:
            continue
        if action.lower() in {token.lower() for token in tokens}:
            continue
        tokens.append(action)
        if len(tokens) >= max_items:
            break
    return tokens


def _build_window_event_counts(
    window_events: Sequence[Mapping[str, Any]],
    *,
    max_workstream_fanout: int = 4,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in window_events:
        ws_tokens = sorted(
            {
                str(token).strip()
                for token in event.get("workstreams", [])
                if str(token).strip()
            }
        )
        if not ws_tokens:
            continue
        if len(ws_tokens) > max_workstream_fanout:
            continue
        for ws_id in ws_tokens:
            counts[ws_id] = counts.get(ws_id, 0) + 1

    if counts:
        return counts

    # Fallback: if every event is high-fanout, keep a conservative signal instead of going empty.
    fallback: dict[str, int] = {}
    for event in window_events:
        ws_tokens = {
            str(token).strip()
            for token in event.get("workstreams", [])
            if str(token).strip()
        }
        for ws_id in ws_tokens:
            fallback[ws_id] = fallback.get(ws_id, 0) + 1
    return fallback


def _humanize_commit_subject(summary: str) -> str:
    token = _normalize_sentence(summary).replace("`", "")
    if not token:
        return ""
    token = _CONVENTIONAL_COMMIT_PREFIX_RE.sub("", token).strip()
    lowered = token.lower()
    replacements: tuple[tuple[str, str], ...] = (
        ("add ", "added "),
        ("fix ", "fixed "),
        ("update ", "updated "),
        ("refactor ", "refactored "),
        ("remove ", "removed "),
        ("improve ", "improved "),
        ("align ", "aligned "),
        ("implement ", "implemented "),
        ("make ", "made "),
    )
    for prefix, replacement in replacements:
        if lowered.startswith(prefix):
            return f"{replacement}{token[len(prefix):].strip()}"
    return token


def _humanize_execution_event_summary(*, kind: str, summary: str) -> str:
    token = _normalize_sentence(summary).rstrip(".;")
    if not token:
        return ""
    if kind == "commit":
        token = _humanize_commit_subject(token)
    token = token.replace("`", "")
    return _narrative_excerpt(token, max_sentences=1, max_chars=220).strip()


_CHECKLIST_RATIO_RE = re.compile(r"checklist\s+\d+\s*/\s*\d+\s+complete", re.IGNORECASE)
_GENERIC_CHURN_RE = re.compile(
    r"^(?:updated|modified|touched)\s+(?:tooling assets?|dashboard assets?|generated artifacts?|tooling(?:\s+\w+)*)\b|"
    r"^(?:updated|modified|changed)\s+(?:backlog source|workflow docs|skills docs|implementation plan|docs|tests)\b|"
    r"\band\s+\d+\s+other\s+(?:areas|files|artifacts|surfaces)\b",
    re.IGNORECASE,
)
_STRONG_NARRATIVE_VERB_RE = re.compile(
    r"^(?:added|implemented|landed|built|wired|enabled|introduced|created|closed|promoted|seeded|shipped|cut|"
    r"hardened|reconciled|backfilled|migrated|bound|verified|documented)\b",
    re.IGNORECASE,
)
_PASSIVE_ACTION_RE = re.compile(
    r"^(?P<subject>.+?)\s+are\s+(?P<verb>backfilled|updated|documented|refreshed|reconciled|migrated|validated|"
    r"linked|seeded|bound|described)\b(?P<rest>.*)$",
    re.IGNORECASE,
)
_LOW_SIGNAL_SURFACE_PREFIXES: tuple[str, ...] = (
    "odylith/radar/source/",
    "odylith/technical-plans/",
    "docs/",
    "agents-guidelines/",
    "skills/",
)
_HIGH_SIGNAL_SURFACE_PREFIXES: tuple[str, ...] = (
    "src/odylith/",
    "app/",
    "service-deploy/",
    "services/",
    "odylith/runtime/contracts/",
    "contracts/",
    "configs/",
    "infra/",
    "policies/",
)
_PASSIVE_ACTION_VERB_MAP: dict[str, str] = {
    "backfilled": "backfill",
    "updated": "update",
    "documented": "document",
    "refreshed": "refresh",
    "reconciled": "reconcile",
    "migrated": "migrate",
    "validated": "validate",
    "linked": "link",
    "seeded": "seed",
    "bound": "bind",
    "described": "describe",
}


def _sanitize_digest_summary(summary: str) -> str:
    token = _normalize_sentence(summary).rstrip(".")
    if not token:
        return ""
    token = _CHECKLIST_RATIO_RE.sub("checklist progress updated", token)
    token = re.sub(r"\b\d+\s*/\s*\d+\b", "", token)
    token = _normalize_sentence(token).rstrip(".")
    return token


def _looks_generic_churn_summary(summary: str) -> bool:
    token = _normalize_sentence(summary)
    if not token:
        return True
    return bool(_GENERIC_CHURN_RE.search(token))


def _surface_signal_score(files: Sequence[str]) -> int:
    score = 0
    for raw in files:
        token = _normalize_repo_token(str(raw)).lower()
        if not token:
            continue
        if token.startswith(_HIGH_SIGNAL_SURFACE_PREFIXES):
            score += 8
        if token.startswith(_LOW_SIGNAL_SURFACE_PREFIXES):
            score -= 4
        if token.startswith("tests/"):
            score -= 2
    return score


def _narrative_signal_score(summary: str, *, files: Sequence[str] = ()) -> int:
    token = _normalize_sentence(summary)
    lower = token.lower()
    if not token:
        return -100
    score = 0
    if _STRONG_NARRATIVE_VERB_RE.match(token):
        score += 40
    if any(
        marker in lower
        for marker in (
            "component",
            "registry",
            "license",
            "binding",
            "onboarding",
            "auth",
            "policy",
            "runtime",
            "postgres",
            "tier",
            "service plane",
            "trust",
            "cutover",
        )
    ):
        score += 14
    if "backlog source" in lower:
        score -= 80
    if "workflow docs" in lower or "skills docs" in lower:
        score -= 45
    if lower.startswith(("updated docs", "modified docs", "updated tests", "modified tests")):
        score -= 28
    score += _surface_signal_score(files)
    return score


def _ordered_update_candidates(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    ranked = sorted(
        [dict(item) for item in candidates if isinstance(item, Mapping)],
        key=lambda item: (
            int(item.get("_score", 0) or 0),
            float(item.get("_sort_ts", 0.0) or 0.0),
            str(item.get("summary", "")).strip(),
        ),
        reverse=True,
    )
    return [
        {
            "kind": str(item.get("kind", "")).strip(),
            "summary": str(item.get("summary", "")).strip(),
        }
        for item in ranked
        if str(item.get("summary", "")).strip()
    ]


def _is_synthetic_plan_execution_signal(*, kind: str, source: str, summary: str) -> bool:
    kind_token = str(kind or "").strip().lower()
    source_token = str(source or "").strip().lower()
    summary_token = _normalize_sentence(summary).lower()
    if source_token == "plan_file" and kind_token in {"implementation", "decision"}:
        return True
    if source_token == "plan_index" and kind_token in {"plan_update", "plan_completion"}:
        return True
    if summary_token.startswith("implementation checkpoint in ") or summary_token.startswith("decision captured in "):
        return True
    return False


def _collect_window_execution_updates(
    window_events: Sequence[Mapping[str, Any]],
    *,
    ws_id: str | None = None,
    max_items: int = 2,
    max_workstream_fanout: int = 4,
) -> list[dict[str, str]]:
    allowed = {
        "statement",
        "implementation",
        "decision",
        "plan_completion",
        "commit",
        "plan_update",
    }
    primary_updates: list[dict[str, str]] = []
    secondary_updates: list[dict[str, str]] = []
    seen: set[str] = set()

    for event in window_events:
        kind = str(event.get("kind", "")).strip()
        if kind not in allowed:
            continue
        ws_tokens = {
            str(token).strip()
            for token in event.get("workstreams", [])
            if str(token).strip()
        }
        strict_signal_kind = kind in {"statement", "implementation", "decision"}
        if max_workstream_fanout > 0 and len(ws_tokens) > max_workstream_fanout and not strict_signal_kind:
            continue
        if ws_id and ws_id not in ws_tokens:
            continue
        source = str(event.get("source", "")).strip()
        summary = _humanize_execution_event_summary(
            kind=kind,
            summary=str(event.get("summary", "")).strip(),
        )
        normalized_summary = _sanitize_digest_summary(summary)
        if not normalized_summary:
            continue
        if _looks_generic_churn_summary(normalized_summary):
            continue
        if normalized_summary.lower() in {"execution update", "updated code"}:
            continue
        key = normalized_summary.lower()
        if key in seen:
            continue
        seen.add(key)
        ts = event.get("ts")
        sort_ts = ts.timestamp() if isinstance(ts, dt.datetime) else 0.0
        candidate_score = _narrative_signal_score(
            normalized_summary,
            files=[str(item) for item in event.get("files", []) if str(item).strip()],
        )
        candidate = {
            "kind": kind,
            "summary": normalized_summary,
            "_score": candidate_score,
            "_sort_ts": sort_ts,
        }
        is_primary_kind = kind in {"statement", "implementation", "decision", "commit"}
        is_synthetic = _is_synthetic_plan_execution_signal(
            kind=kind,
            source=source,
            summary=normalized_summary,
        )
        if is_primary_kind and not is_synthetic:
            candidate["_score"] = int(candidate.get("_score", 0) or 0) + 60
            primary_updates.append(candidate)
        else:
            secondary_updates.append(candidate)

    updates: list[dict[str, str]] = []
    for bucket in (
        _ordered_update_candidates(primary_updates),
        _ordered_update_candidates(secondary_updates),
    ):
        for candidate in bucket:
            updates.append(candidate)
            if len(updates) >= max_items:
                return updates
    return updates


def _transaction_end_ts(row: Mapping[str, Any]) -> dt.datetime | None:
    end_ts = _parse_iso_ts(str(row.get("end_ts_iso", "")).strip())
    if end_ts is not None:
        return end_ts.astimezone(_COMPASS_TZ)
    start_ts = _parse_iso_ts(str(row.get("start_ts_iso", "")).strip())
    if start_ts is not None:
        return start_ts.astimezone(_COMPASS_TZ)
    return None


def _filter_transactions_by_window(
    transactions: Sequence[Mapping[str, Any]],
    *,
    now: dt.datetime,
    hours: int,
) -> list[dict[str, Any]]:
    cutoff = now - dt.timedelta(hours=max(1, int(hours)))
    selected: list[dict[str, Any]] = []
    for row in transactions:
        if not isinstance(row, Mapping):
            continue
        ts = _transaction_end_ts(row)
        if ts is None or ts < cutoff:
            continue
        selected.append(dict(row))
    selected.sort(
        key=lambda row: (
            _transaction_end_ts(row) or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
            str(row.get("id", "")).strip(),
        ),
        reverse=True,
    )
    return selected


def _collect_window_transaction_updates(
    window_transactions: Sequence[Mapping[str, Any]],
    *,
    ws_id: str | None = None,
    max_items: int = 2,
    max_workstream_fanout: int = 16,
) -> list[dict[str, str]]:
    return compass_outcome_digest_runtime._collect_window_transaction_updates(
        window_transactions,
        ws_id=ws_id,
        max_items=max_items,
        max_workstream_fanout=max_workstream_fanout,
    )


def _progress_story(*, done_tasks: int, total_tasks: int) -> str:
    if total_tasks <= 0:
        return "execution checklist baseline is being finalized"
    if done_tasks <= 0:
        return "execution checklist is defined, but closure work has not started yet"
    if done_tasks >= total_tasks:
        return "execution checklist closure is complete for the scoped plan"
    return "execution checklist closure is underway while implementation execution remains active"


def _execution_status_phrase(*, status: str, has_execution_signal: bool, progress_ratio: float) -> str:
    token = str(status or "").strip().lower()
    if not token:
        return "currently unknown"
    if token == "planning":
        if has_execution_signal or progress_ratio > 0:
            return "in planning, with implementation now underway"
        return "in planning, preparing the first implementation slice"
    if token == "implementation":
        return "in active implementation"
    if token == "finished":
        return "completed"
    if token == "queued":
        return "queued for execution"
    return token.replace("_", " ")


def _clean_execution_clause(text: str) -> str:
    return _periodize(str(text or "")).rstrip(".").replace("`", "").strip()


def _normalize_action_task(text: str) -> str:
    token = _clean_execution_clause(text)
    if not token:
        return ""
    match = _PASSIVE_ACTION_RE.match(token)
    if match is None:
        return token
    subject = _normalize_sentence(str(match.group("subject") or "").strip())
    verb = _PASSIVE_ACTION_VERB_MAP.get(str(match.group("verb") or "").strip().lower(), "")
    rest = _normalize_sentence(str(match.group("rest") or "").strip())
    if not subject or not verb:
        return token
    rebuilt = f"{verb} {subject}"
    if rest:
        rebuilt = f"{rebuilt}{(' ' if not rest.startswith((',', ';', ':')) else '')}{rest}"
    return rebuilt.strip()


def _action_clause_for_narrative(text: str) -> str:
    return compass_narrative_runtime.action_clause_for_narrative(
        text,
        normalize_action_task=_normalize_action_task,
    )


def _timeline_clause(*, eta_days: int, eta_source: str, status: str, has_execution_signal: bool) -> str:
    return compass_narrative_runtime.timeline_clause(
        eta_days=eta_days,
        eta_source=eta_source,
        status=status,
        has_execution_signal=has_execution_signal,
    )


def _build_outcome_digest_for_workstream(
    *,
    row: Mapping[str, Any],
    next_actions: list[dict[str, str]],
    recent_completed: list[dict[str, str]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    risk_posture: str,
) -> list[str]:
    return compass_outcome_digest_runtime._build_outcome_digest_for_workstream(
        row=row,
        next_actions=next_actions,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
        risk_posture=risk_posture,
    )


def _build_outcome_digest_global(
    *,
    ws_rows: list[dict[str, Any]],
    ws_index: Mapping[str, Mapping[str, Any]],
    active_ws_rows: Sequence[Mapping[str, Any]],
    event_counts_by_ws: Mapping[str, int],
    next_actions: list[dict[str, str]],
    recent_completed: list[dict[str, str]],
    risks_summary: str,
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    window_hours: int,
) -> list[str]:
    return compass_outcome_digest_runtime._build_outcome_digest_global(
        ws_rows=ws_rows,
        ws_index=ws_index,
        active_ws_rows=active_ws_rows,
        event_counts_by_ws=event_counts_by_ws,
        next_actions=next_actions,
        recent_completed=recent_completed,
        risks_summary=risks_summary,
        window_events=window_events,
        window_transactions=window_transactions,
        window_hours=window_hours,
    )


def _build_risk_posture_summary(
    *,
    open_critical: int,
    traceability_risks: Sequence[Mapping[str, Any]],
    stale_diagrams: Sequence[Mapping[str, Any]],
) -> str:
    flags: list[str] = []
    if open_critical > 0:
        flags.append("critical bugs require immediate containment")
    if len(traceability_risks) > 0:
        flags.append("traceability warnings need cleanup")
    if len(stale_diagrams) > 0:
        flags.append("diagram reviews are stale")
    if not flags:
        return "Risk posture: no critical blockers are currently surfaced."
    if len(flags) == 1:
        return f"Risk posture: {flags[0]}."
    return f"Risk posture: {'; '.join(flags)}."


def _decapitalize_clause(text: str) -> str:
    token = _normalize_sentence(text).rstrip(".")
    if not token:
        return ""
    if len(token) == 1:
        return token.lower()
    return token[:1].lower() + token[1:]


def _standup_fact(
    *,
    section_key: str,
    voice_hint: str,
    priority: int,
    text: str,
    source: str,
    kind: str,
    workstreams: Sequence[str] | None = None,
) -> dict[str, Any]:
    sentence = _periodize(text).strip()
    return {
        "section_key": str(section_key).strip(),
        "voice_hint": str(voice_hint).strip().lower(),
        "priority": int(priority),
        "text": sentence,
        "source": str(source).strip(),
        "kind": str(kind).strip(),
        "workstreams": [
            str(token).strip()
            for token in (workstreams or [])
            if str(token).strip()
        ],
    }


def _finalize_standup_fact_packet(
    *,
    window_key: str,
    scope: Mapping[str, Any],
    summary: Mapping[str, Any],
    section_candidates: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    fact_counter = 1
    for section_key, label in compass_standup_brief_narrator.STANDUP_BRIEF_SECTIONS:
        seen_text: set[str] = set()
        ranked_candidates = sorted(
            [
                dict(item)
                for item in section_candidates.get(section_key, [])
                if isinstance(item, Mapping)
                and _normalize_sentence(str(item.get("text", "")).strip())
            ],
            key=lambda row: (
                int(row.get("priority", 0) or 0),
                str(row.get("text", "")).strip(),
            ),
            reverse=True,
        )
        section_facts: list[dict[str, Any]] = []
        for candidate in ranked_candidates:
            normalized_text = _normalize_sentence(str(candidate.get("text", "")).strip())
            if not normalized_text:
                continue
            dedupe_key = normalized_text.lower()
            if dedupe_key in seen_text:
                continue
            seen_text.add(dedupe_key)
            fact_id = f"F-{fact_counter:03d}"
            fact_counter += 1
            fact = {
                "id": fact_id,
                "section_key": section_key,
                "voice_hint": str(candidate.get("voice_hint", "")).strip().lower() or "operator",
                "priority": int(candidate.get("priority", 0) or 0),
                "text": normalized_text,
                "source": str(candidate.get("source", "")).strip(),
                "kind": str(candidate.get("kind", "")).strip(),
                "workstreams": [
                    str(token).strip()
                    for token in candidate.get("workstreams", [])
                    if str(token).strip()
                ],
            }
            facts.append(fact)
            section_facts.append(fact)
            if len(section_facts) >= 6:
                break
        sections.append(
            {
                "key": section_key,
                "label": label,
                "facts": section_facts,
            }
        )
    return {
        "version": compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "window": str(window_key).strip(),
        "scope": dict(scope),
        "summary": dict(summary),
        "sections": sections,
        "facts": facts,
    }


def _wave_context_summary(row: Mapping[str, Any]) -> str:
    programs = row.get("execution_wave_programs", [])
    if not isinstance(programs, Sequence) or not programs:
        return ""
    program = programs[0]
    if not isinstance(program, Mapping):
        return ""
    wave_span_label = str(program.get("wave_span_label", "")).strip()
    role_label = str(program.get("role_label", "")).strip()
    umbrella_id = str(program.get("umbrella_id", "")).strip()
    next_label = str(program.get("program_next_label", "")).strip()
    parts: list[str] = []
    if role_label and wave_span_label:
        parts.append(f"{role_label} in {wave_span_label}")
    elif wave_span_label:
        parts.append(wave_span_label)
    if umbrella_id:
        parts.append(f"under {umbrella_id}")
    if next_label:
        parts.append(f"next gate {next_label}")
    return "Execution wave context: " + "; ".join(parts) if parts else ""


def _lineage_context_summary(row: Mapping[str, Any]) -> str:
    lineage = row.get("lineage", {})
    if not isinstance(lineage, Mapping):
        return ""
    labels: tuple[tuple[str, str], ...] = (
        ("reopens", "reopens"),
        ("reopened_by", "reopened by"),
        ("split_from", "split from"),
        ("split_into", "split into"),
        ("merged_into", "merged into"),
        ("merged_from", "merged from"),
    )
    for key, label in labels:
        values = [str(token).strip() for token in lineage.get(key, []) if str(token).strip()]
        if values:
            joined = ", ".join(values[:3])
            suffix = " plus related lineage" if len(values) > 3 else ""
            return f"Lineage context: {label} {joined}{suffix}."
    return ""


def _forcing_function_text(*, action: str, label: str, purpose: str = "") -> str:
    token = _action_clause_for_narrative(action)
    if not token:
        return ""
    purpose_clause = _decapitalize_clause(purpose)
    if purpose_clause:
        return f"Immediate forcing function is to {token} so {purpose_clause}."
    if label:
        return f"Immediate forcing function is to {token} for {label}."
    return f"Immediate forcing function is to {token}."


def _follow_on_text(*, action: str, label: str, benefit: str = "") -> str:
    token = _action_clause_for_narrative(action)
    if not token:
        return ""
    benefit_clause = _decapitalize_clause(benefit)
    if benefit_clause:
        return f"Then {token} to extend {benefit_clause}."
    if label:
        return f"Then {token} to keep {label} moving."
    return f"Then {token}."


def _scope_risk_rows(
    *,
    ws_id: str | None,
    bug_items: Sequence[Mapping[str, Any]],
    traceability_risks: Sequence[Mapping[str, Any]],
    stale_diagrams: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    scope_token = str(ws_id or "").strip()
    bugs: list[dict[str, Any]] = []
    for row in bug_items:
        if not isinstance(row, Mapping) or not bool(row.get("is_open_critical")):
            continue
        workstreams = [str(token).strip() for token in row.get("workstreams", []) if str(token).strip()]
        if scope_token and scope_token not in workstreams:
            continue
        bugs.append(dict(row))
    trace: list[dict[str, Any]] = []
    for row in traceability_risks:
        if not isinstance(row, Mapping):
            continue
        idea_id = str(row.get("idea_id", "")).strip()
        if scope_token and idea_id and idea_id != scope_token:
            continue
        if scope_token and not idea_id:
            continue
        trace.append(dict(row))
    stale: list[dict[str, Any]] = []
    for row in stale_diagrams:
        if not isinstance(row, Mapping):
            continue
        workstreams = [str(token).strip() for token in row.get("workstreams", []) if str(token).strip()]
        if scope_token and scope_token not in workstreams:
            continue
        stale.append(dict(row))
    return {
        "bugs": bugs,
        "traceability": trace,
        "stale_diagrams": stale,
    }


def _risk_facts(
    *,
    ws_id: str | None,
    risk_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    risk_summary: str,
    fallback_text: str = "",
) -> list[dict[str, Any]]:
    workstreams = [str(ws_id).strip()] if str(ws_id or "").strip() else []
    facts: list[dict[str, Any]] = []
    bugs = [
        dict(item)
        for item in risk_rows.get("bugs", [])
        if isinstance(item, Mapping)
    ]
    trace = [
        dict(item)
        for item in risk_rows.get("traceability", [])
        if isinstance(item, Mapping)
    ]
    stale = [
        dict(item)
        for item in risk_rows.get("stale_diagrams", [])
        if isinstance(item, Mapping)
    ]
    if bugs:
        first = bugs[0]
        severity = str(first.get("severity", "")).strip() or "critical"
        title = _narrative_excerpt(str(first.get("title", "")).strip(), max_sentences=1, max_chars=220)
        facts.append(
            _standup_fact(
                section_key="risks_to_watch",
                voice_hint="operator",
                priority=100,
                text=f"Primary blocker is an open {severity} bug: {title}.",
                source="bugs",
                kind="bug",
                workstreams=workstreams,
            )
        )
    if trace:
        first = trace[0]
        message = _narrative_excerpt(
            str(first.get("message", "")).strip() or str(first.get("category", "")).strip(),
            max_sentences=1,
            max_chars=220,
        )
        facts.append(
            _standup_fact(
                section_key="risks_to_watch",
                voice_hint="operator",
                priority=92,
                text=f"Governance gap still needs cleanup: {message}.",
                source="traceability",
                kind="traceability",
                workstreams=workstreams,
            )
        )
    if stale:
        first = stale[0]
        diagram_id = str(first.get("diagram_id", "")).strip()
        age_days = int(first.get("age_days", 0) or 0)
        title = _narrative_excerpt(str(first.get("title", "")).strip(), max_sentences=1, max_chars=140)
        text = f"Operator context is aging: diagram {diagram_id} {title} has been stale for {age_days} days."
        facts.append(
            _standup_fact(
                section_key="risks_to_watch",
                voice_hint="operator",
                priority=84,
                text=text,
                source="atlas",
                kind="stale_diagram",
                workstreams=workstreams,
            )
        )
    if not facts:
        fallback = _periodize(_normalize_sentence(fallback_text)) if _normalize_sentence(fallback_text) else ""
        facts.append(
            _standup_fact(
                section_key="risks_to_watch",
                voice_hint="operator",
                priority=72,
                text=fallback or _periodize(_risk_phrase(risk_summary).capitalize()),
                source="risk_summary",
                kind="risk_posture",
                workstreams=workstreams,
            )
        )
    return facts[:3]


def _wave_context_clause(wave_context: str) -> str:
    token = _normalize_sentence(wave_context)
    if not token:
        return ""
    lowered = token.lower()
    if lowered.startswith("execution wave context:"):
        token = token.split(":", 1)[1].strip()
    return _decapitalize_clause(token)


def _latest_window_activity_iso(rows: Sequence[Mapping[str, Any]]) -> str:
    latest: dt.datetime | None = None
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        timeline = row.get("timeline", {})
        if not isinstance(timeline, Mapping):
            continue
        parsed = _parse_iso_ts(str(timeline.get("last_activity_iso", "")).strip())
        if parsed is None:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return _safe_iso(latest) if latest else ""


def _matches_freshness_scope(tokens: Sequence[str], ws_id: str | None) -> bool:
    scope_token = str(ws_id or "").strip()
    if not scope_token:
        return True
    return scope_token in {
        str(token).strip()
        for token in tokens
        if str(token).strip()
    }


def _latest_evidence_marker(
    *,
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    ws_id: str | None,
    fallback_last_activity_iso: str = "",
) -> tuple[dt.datetime | None, str]:
    latest: dt.datetime | None = None
    source_kind = "none"
    for row in window_events:
        if not isinstance(row, Mapping):
            continue
        workstreams = row.get("workstreams", [])
        if not isinstance(workstreams, Sequence) or not _matches_freshness_scope(workstreams, ws_id):
            continue
        ts = row.get("ts")
        candidate = ts if isinstance(ts, dt.datetime) else _parse_iso_ts(str(row.get("ts_iso", "")).strip())
        if candidate is None:
            continue
        if latest is None or candidate > latest:
            latest = candidate
            source_kind = "event"
    for row in window_transactions:
        if not isinstance(row, Mapping):
            continue
        workstreams = row.get("workstreams", [])
        if not isinstance(workstreams, Sequence) or not _matches_freshness_scope(workstreams, ws_id):
            continue
        candidate = _parse_iso_ts(str(row.get("end_ts_iso", "")).strip()) or _parse_iso_ts(
            str(row.get("start_ts_iso", "")).strip()
        )
        if candidate is None:
            continue
        if latest is None or candidate > latest:
            latest = candidate
            source_kind = "transaction"
    if latest is None and str(fallback_last_activity_iso).strip():
        fallback = _parse_iso_ts(str(fallback_last_activity_iso).strip())
        if fallback is not None:
            latest = fallback
            source_kind = "last_activity"
    return latest, source_kind


def _freshness_bucket(*, latest_ts: dt.datetime | None, now: dt.datetime) -> str:
    if latest_ts is None:
        return "stale"
    age_minutes = max(0, int((now - latest_ts).total_seconds() // 60))
    if age_minutes <= _FRESHNESS_LIVE_MAX_MINUTES:
        return "live"
    if age_minutes <= _FRESHNESS_RECENT_MAX_MINUTES:
        return "recent"
    if age_minutes <= _FRESHNESS_AGING_MAX_MINUTES:
        return "aging"
    return "stale"


def _freshness_age_label(*, latest_ts: dt.datetime | None, now: dt.datetime) -> str:
    if latest_ts is None:
        return "no fresh linked execution proof in the current window"
    age_minutes = max(0, int((now - latest_ts).total_seconds() // 60))
    if age_minutes <= _FRESHNESS_LIVE_MAX_MINUTES:
        return "under ninety minutes old"
    if age_minutes <= _FRESHNESS_RECENT_MAX_MINUTES:
        return "within the last six hours"
    if age_minutes <= _FRESHNESS_AGING_MAX_MINUTES:
        return "more than six hours old"
    return "more than a day old"


def _freshness_fact_text(
    *,
    label: str,
    freshness_bucket: str,
    freshness_age_label: str,
    source_kind: str,
) -> str:
    normalized_label = label or "this lane"
    if freshness_bucket == "aging":
        if source_kind == "last_activity":
            return (
                f"Freshness signal is aging: latest known activity for {normalized_label} is {freshness_age_label}, "
                "so treat momentum as waiting for another proving checkpoint."
            )
        if source_kind == "none":
            return (
                f"Freshness signal is aging: {normalized_label} has no fresh linked execution proof in the current window, "
                "so current posture is leaning on metadata more than live implementation evidence."
            )
        return (
            f"Freshness signal is aging: latest linked execution proof for {normalized_label} is {freshness_age_label}, "
            "so live momentum still needs another proving checkpoint."
        )
    if freshness_bucket == "stale":
        if source_kind == "last_activity":
            return (
                f"Freshness signal is stale: latest known activity for {normalized_label} is {freshness_age_label}, "
                "so Compass needs a new execution checkpoint before claiming live traction."
            )
        if source_kind == "none":
            return (
                f"Freshness signal is stale: no linked execution proof landed in the current window for {normalized_label}, "
                "so the next checkpoint needs to refresh the narrative before momentum claims stay credible."
            )
        return (
            f"Freshness signal is stale: latest linked execution proof for {normalized_label} is {freshness_age_label}, "
            "so a new checkpoint is needed before momentum claims stay credible."
        )
    return ""


def _scoped_fallback_next_text(
    *,
    label: str,
    purpose: str,
    status: str,
    done_tasks: int,
    total_tasks: int,
    freshness_bucket: str,
) -> str:
    purpose_clause = _decapitalize_clause(purpose)
    remaining_tasks = max(0, int(total_tasks) - int(done_tasks))
    if remaining_tasks > 0 and purpose_clause:
        return (
            f"Immediate forcing function is to turn the next open checklist item into a named checkpoint for {label} "
            f"so {purpose_clause}."
        )
    if remaining_tasks > 0:
        return f"Immediate forcing function is to turn the next open checklist item into a named checkpoint for {label}."
    if freshness_bucket in {"aging", "stale"}:
        return (
            f"Immediate forcing function is to log the next concrete checkpoint for {label} "
            "so Compass stops leaning on aging evidence."
        )
    if str(status or "").strip().lower() == "planning":
        return f"Immediate forcing function is to define the first implementation checkpoint for {label}."
    return f"Immediate forcing function is to capture the next verified checkpoint for {label}."


def _global_fallback_next_text(
    *,
    primary_label: str,
    primary_purpose: str,
    active_count: int,
    freshness_bucket: str,
) -> str:
    purpose_clause = _decapitalize_clause(primary_purpose)
    if primary_label and purpose_clause:
        return f"Immediate forcing function is to name the next checkpoint on {primary_label} so {purpose_clause}."
    if primary_label and freshness_bucket in {"aging", "stale"}:
        return (
            f"Immediate forcing function is to log the next checkpoint on {primary_label} "
            "so portfolio steering stops leaning on aging proof."
        )
    if active_count > 0:
        return "Immediate forcing function is to turn the active flagship lane into a named next checkpoint."
    return "Immediate forcing function is to name the next concrete checkpoint before portfolio steering drifts."


def _scoped_fallback_risk_text(
    *,
    label: str,
    total_tasks: int,
    done_tasks: int,
    eta_days: int,
    eta_source: str,
    wave_context: str,
    risk_summary: str,
    freshness_bucket: str,
    freshness_text: str,
) -> str:
    remaining_tasks = max(0, int(total_tasks) - int(done_tasks))
    if remaining_tasks > 0 and wave_context:
        return (
            f"Primary watch item is sequencing discipline: {remaining_tasks} plan items remain open while "
            f"{_wave_context_clause(wave_context)}."
        )
    if remaining_tasks > 0:
        return f"Primary watch item is closure discipline: {remaining_tasks} plan items remain open for {label}."
    if freshness_bucket in {"aging", "stale"} and freshness_text:
        return freshness_text
    if str(eta_source or "").strip().lower() == "heuristic":
        return f"Primary watch item is timeline confidence: {label} is still projected heuristically at roughly {eta_days} days."
    return _periodize(_risk_phrase(risk_summary).capitalize())


def _global_fallback_risk_text(
    *,
    active_ws_rows: Sequence[Mapping[str, Any]],
    primary_label: str,
    eta_days: int,
    eta_source: str,
    risk_summary: str,
    freshness_bucket: str,
    freshness_text: str,
) -> str:
    active_labels = [
        _ws_label(row)
        for row in active_ws_rows
        if isinstance(row, Mapping) and _ws_label(row)
    ]
    active_labels = list(dict.fromkeys(active_labels))
    if len(active_labels) >= 2:
        return (
            f"Primary watch item is execution coherence across {active_labels[0]} and {active_labels[1]} "
            "while shared dependencies remain open."
        )
    if active_labels:
        return f"Primary watch item is keeping {active_labels[0]} tight so live execution does not diffuse into portfolio churn."
    if freshness_bucket in {"aging", "stale"} and freshness_text:
        return freshness_text
    if str(eta_source or "").strip().lower() == "heuristic" and primary_label:
        return f"Primary watch item is timeline confidence on {primary_label}: delivery is still projected heuristically at roughly {eta_days} days."
    return _periodize(_risk_phrase(risk_summary).capitalize())


def _build_scoped_standup_fact_packet(
    *,
    row: Mapping[str, Any],
    next_actions: Sequence[Mapping[str, str]],
    recent_completed: Sequence[Mapping[str, str]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    window_hours: int,
    risk_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    risk_summary: str,
    self_host_snapshot: Mapping[str, Any] | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    return compass_standup_fact_packets._build_scoped_standup_fact_packet(
        row=row,
        next_actions=next_actions,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
        window_hours=window_hours,
        risk_rows=risk_rows,
        risk_summary=risk_summary,
        self_host_snapshot=self_host_snapshot,
        now=now,
    )


def _build_global_standup_fact_packet(
    *,
    ws_rows: Sequence[Mapping[str, Any]],
    ws_index: Mapping[str, Mapping[str, Any]],
    active_ws_rows: Sequence[Mapping[str, Any]],
    event_counts_by_ws: Mapping[str, int],
    next_actions: Sequence[Mapping[str, str]],
    recent_completed: Sequence[Mapping[str, str]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    window_hours: int,
    risk_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    risk_summary: str,
    kpis: Mapping[str, Any],
    self_host_snapshot: Mapping[str, Any],
    self_host_risks: Sequence[Mapping[str, Any]],
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    return compass_standup_fact_packets._build_global_standup_fact_packet(
        ws_rows=ws_rows,
        ws_index=ws_index,
        active_ws_rows=active_ws_rows,
        event_counts_by_ws=event_counts_by_ws,
        next_actions=next_actions,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
        window_hours=window_hours,
        risk_rows=risk_rows,
        risk_summary=risk_summary,
        kpis=kpis,
        self_host_snapshot=self_host_snapshot,
        self_host_risks=self_host_risks,
        now=now,
    )


def _select_current_workstream_rows(
    *,
    all_rows: Sequence[Mapping[str, Any]],
    window_events_48h: Sequence[Mapping[str, Any]],
    recent_completed_rows_48h: Sequence[Mapping[str, str]],
    max_rows: int = _CURRENT_WORKSTREAM_MAX_ROWS,
) -> list[dict[str, Any]]:
    """Select the rows Compass should surface as current execution lanes.

    Compass needs a full workstream catalog for lookups and deep links, but the
    live "Current Workstreams" panel and scoped AI standup generation should
    stay limited to the lanes with real near-term execution relevance.
    """

    by_id: dict[str, dict[str, Any]] = {}
    ordered_rows: list[dict[str, Any]] = []
    for raw in all_rows:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        idea_id = str(row.get("idea_id", "")).strip()
        if not idea_id or idea_id in by_id:
            continue
        by_id[idea_id] = row
        ordered_rows.append(row)

    required_ids: list[str] = []
    optional_ids: list[str] = []
    seen_ids: set[str] = set()

    def _append(ws_id: str, *, required: bool = False) -> None:
        token = str(ws_id).strip()
        if not token or token in seen_ids or token not in by_id:
            return
        seen_ids.add(token)
        if required:
            required_ids.append(token)
            return
        optional_ids.append(token)

    for row in ordered_rows:
        status = str(row.get("status", "")).strip().lower()
        if status in {"implementation", "planning"}:
            _append(str(row.get("idea_id", "")).strip(), required=True)

    event_counts_by_ws = _build_window_event_counts(window_events_48h)
    for ws_id, _count in sorted(event_counts_by_ws.items(), key=lambda item: (-int(item[1]), item[0])):
        _append(ws_id)

    for item in recent_completed_rows_48h:
        if not isinstance(item, Mapping):
            continue
        _append(str(item.get("backlog", "")).strip())

    for row in ordered_rows:
        programs = row.get("execution_wave_programs", [])
        if not isinstance(programs, Sequence):
            continue
        if any(bool(program.get("has_active_wave")) for program in programs if isinstance(program, Mapping)):
            _append(str(row.get("idea_id", "")).strip())

    if not required_ids and not optional_ids:
        for row in ordered_rows[: max(1, int(max_rows))]:
            _append(str(row.get("idea_id", "")).strip())

    limit = max(1, int(max_rows))
    if len(required_ids) >= limit:
        selected_ids = list(required_ids)
    else:
        selected_ids = [*required_ids, *optional_ids[: max(0, limit - len(required_ids))]]
    return [by_id[ws_id] for ws_id in selected_ids if ws_id in by_id]


def _execution_wave_program_member_ids(program: Mapping[str, Any]) -> set[str]:
    """Collect all member workstream ids referenced by one execution-wave program."""

    member_ids: set[str] = set()
    for wave in program.get("waves", []):
        if not isinstance(wave, Mapping):
            continue
        for member in wave.get("all_workstreams", []):
            if not isinstance(member, Mapping):
                continue
            token = str(member.get("idea_id", "")).strip()
            if token:
                member_ids.add(token)
    return member_ids


def _is_fully_closed_execution_wave_program(program: Mapping[str, Any]) -> bool:
    """Return whether a program is fully closed and therefore optional in Compass."""

    umbrella_status = str(program.get("umbrella_status", "")).strip().lower()
    terminal_umbrella = umbrella_status in {"finished", "parked", "superseded"}
    waves = [wave for wave in program.get("waves", []) if isinstance(wave, Mapping)]
    if not terminal_umbrella or not waves:
        return False
    return all(str(wave.get("status", "")).strip().lower() == "complete" for wave in waves)


def _filter_execution_wave_payload_for_current_context(
    *,
    payload: Mapping[str, Any],
    current_workstream_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bound Compass execution-wave programs to live context while keeping a catalog."""

    programs = [row for row in payload.get("programs", []) if isinstance(row, Mapping)]
    workstreams = payload.get("workstreams", {})
    if not isinstance(workstreams, Mapping):
        workstreams = {}

    live_ids = {
        str(row.get("idea_id", "")).strip()
        for row in current_workstream_rows
        if isinstance(row, Mapping) and str(row.get("idea_id", "")).strip()
    }
    filtered_programs: list[Mapping[str, Any]] = []
    for program in programs:
        if not _is_fully_closed_execution_wave_program(program):
            filtered_programs.append(program)
            continue
        umbrella_id = str(program.get("umbrella_id", "")).strip()
        member_ids = _execution_wave_program_member_ids(program)
        if umbrella_id in live_ids or member_ids.intersection(live_ids):
            filtered_programs.append(program)

    return {
        "summary": {
            "program_count": len(filtered_programs),
            "catalog_program_count": len(programs),
            "wave_count": sum(int(row.get("wave_count", 0) or 0) for row in filtered_programs),
            "active_wave_count": sum(int(row.get("active_wave_count", 0) or 0) for row in filtered_programs),
            "blocked_wave_count": sum(int(row.get("blocked_wave_count", 0) or 0) for row in filtered_programs),
            "workstream_count": len(workstreams),
        },
        "programs": list(filtered_programs),
        "program_catalog": list(programs),
        "workstreams": dict(workstreams),
    }


def _is_bug_date_within_window(*, date_token: str, now: dt.datetime, hours: int) -> bool:
    """Return whether a bug index row should count in a rolling window KPI.

    Bug rows only carry a calendar date (no timestamp), so this uses day-level
    inclusion anchored to the current Compass timezone date window.
    """

    raw = str(date_token).strip()
    if not raw:
        return True
    parsed = _parse_date(raw)
    if parsed is None:
        return True
    window_start_date = (now - dt.timedelta(hours=max(1, int(hours)))).date()
    window_end_date = now.date()
    return window_start_date <= parsed <= window_end_date


def _compact_odylith_runtime_summary(*, repo_root: Path) -> dict[str, Any]:
    """Return a bounded Odylith runtime posture summary for Compass."""
    return odylith_runtime_surface_summary.load_runtime_surface_summary(repo_root=repo_root)


def _build_runtime_payload(
    *,
    repo_root: Path,
    backlog_index_path: Path,
    plan_index_path: Path,
    bugs_index_path: Path,
    traceability_graph_path: Path,
    mermaid_catalog_path: Path,
    codex_stream_path: Path,
    max_review_age_days: int,
    active_window_minutes: int,
    runtime_mode: str,
    refresh_profile: str = "shell-safe",
) -> dict[str, Any]:
    return compass_runtime_payload_runtime._build_runtime_payload(
        repo_root=repo_root,
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
        max_review_age_days=max_review_age_days,
        active_window_minutes=active_window_minutes,
        runtime_mode=runtime_mode,
        refresh_profile=refresh_profile,
    )


def _prune_history(history_dir: Path, *, retention_days: int, today: dt.date) -> list[str]:
    history_dir.mkdir(parents=True, exist_ok=True)
    kept: list[str] = []
    for path in sorted(history_dir.glob("*.v1.json")):
        if path.name == "index.v1.json":
            continue
        token = path.name.replace(".v1.json", "")
        date = _parse_date(token)
        if date is None:
            continue
        age = (today - date).days
        if age > retention_days:
            path.unlink(missing_ok=True)
            continue
        kept.append(date.isoformat())
    kept.sort(reverse=True)
    return kept


def _history_archive_dir(history_dir: Path) -> Path:
    return history_dir / "archive"


def _history_restore_pins_path(history_dir: Path) -> Path:
    return history_dir / "restore-pins.v1.json"


def _history_archive_path(*, history_dir: Path, date_token: str) -> Path:
    return _history_archive_dir(history_dir) / f"{date_token}.v1.json.gz"


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"
    tmp_path.write_bytes(content)
    tmp_path.replace(path)


def _normalize_history_date_tokens(values: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            continue
        parsed = _parse_date(token)
        if parsed is None or parsed.isoformat() != token:
            raise ValueError(f"invalid Compass history date: {raw}")
        if token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    normalized.sort(reverse=True)
    return normalized


def _scan_archived_dates(history_dir: Path) -> list[str]:
    archive_dir = _history_archive_dir(history_dir)
    if not archive_dir.is_dir():
        return []
    dates: list[str] = []
    for path in sorted(archive_dir.glob("*.v1.json.gz")):
        token = path.name.replace(".v1.json.gz", "")
        parsed = _parse_date(token)
        if parsed is None:
            continue
        dates.append(parsed.isoformat())
    dates.sort(reverse=True)
    return dates


def _load_restore_pins(history_dir: Path) -> list[str]:
    path = _history_restore_pins_path(history_dir)
    if not path.is_file():
        return []
    try:
        payload = _load_json(path)
    except Exception:
        return []
    if not isinstance(payload, Mapping):
        return []
    dates = payload.get("dates")
    if not isinstance(dates, list):
        return []
    try:
        return _normalize_history_date_tokens([str(item) for item in dates])
    except ValueError:
        return []


def _write_restore_pins(*, repo_root: Path, history_dir: Path, dates: Sequence[str]) -> Path:
    path = _history_restore_pins_path(history_dir)
    payload = {
        "version": "v1",
        "generated_utc": _safe_iso(dt.datetime.now(tz=dt.timezone.utc)),
        "dates": _normalize_history_date_tokens(dates),
    }
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(path),
    )
    return path


def _archive_daily_snapshot(*, active_path: Path, archive_path: Path) -> None:
    try:
        raw = active_path.read_bytes()
        json.loads(raw.decode("utf-8"))
    except Exception:
        return
    _write_bytes_atomic(archive_path, gzip.compress(raw, compresslevel=9))
    active_path.unlink(missing_ok=True)


def _rehydrate_restored_history(*, history_dir: Path, restored_dates: Sequence[str]) -> list[str]:
    realized: list[str] = []
    for token in _normalize_history_date_tokens(restored_dates):
        active_path = history_dir / f"{token}.v1.json"
        if active_path.is_file():
            realized.append(token)
            continue
        archive_path = _history_archive_path(history_dir=history_dir, date_token=token)
        if not archive_path.is_file():
            continue
        try:
            raw = gzip.decompress(archive_path.read_bytes())
            json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        _write_bytes_atomic(active_path, raw)
        realized.append(token)
    realized.sort(reverse=True)
    return realized


def _archive_history(
    history_dir: Path,
    *,
    retention_days: int,
    today: dt.date,
    restored_dates: Sequence[str],
) -> list[str]:
    history_dir.mkdir(parents=True, exist_ok=True)
    restored = set(_normalize_history_date_tokens(restored_dates))
    kept: list[str] = []
    for path in sorted(history_dir.glob("*.v1.json")):
        token = path.name.replace(".v1.json", "")
        date = _parse_date(token)
        if date is None:
            continue
        age = (today - date).days
        if age > retention_days and token not in restored:
            _archive_daily_snapshot(
                active_path=path,
                archive_path=_history_archive_path(history_dir=history_dir, date_token=token),
            )
            continue
        kept.append(date.isoformat())
    kept.sort(reverse=True)
    return kept


def _history_archive_meta(history_dir: Path) -> dict[str, Any]:
    archived_dates = _scan_archived_dates(history_dir)
    return {
        "compressed": True,
        "path": "archive",
        "count": len(archived_dates),
        "dates": archived_dates,
        "newest_date": archived_dates[0] if archived_dates else "",
        "oldest_date": archived_dates[-1] if archived_dates else "",
    }


def load_history_retention_days(*, runtime_dir: Path) -> int:
    history_dir = runtime_dir / "history"
    for path in (history_dir / "index.v1.json", runtime_dir / "current.v1.json"):
        if not path.is_file():
            continue
        try:
            payload = _load_json(path)
        except Exception:
            continue
        history = payload.get("history") if path.name == "current.v1.json" and isinstance(payload, Mapping) else payload
        if isinstance(history, Mapping):
            value = history.get("retention_days")
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed >= 1:
                return parsed
    return DEFAULT_HISTORY_RETENTION_DAYS


def restore_archived_history_dates(
    *,
    repo_root: Path,
    runtime_dir: Path,
    dates: Sequence[str],
) -> tuple[list[str], list[str], Path]:
    history_dir = runtime_dir / "history"
    requested = _normalize_history_date_tokens(dates)
    if not requested:
        raise ValueError("provide at least one --date YYYY-MM-DD")

    missing: list[str] = []
    already_active: list[str] = []
    for token in requested:
        active_path = history_dir / f"{token}.v1.json"
        archive_path = _history_archive_path(history_dir=history_dir, date_token=token)
        if active_path.is_file():
            already_active.append(token)
            continue
        if not archive_path.is_file():
            missing.append(token)
    if missing:
        raise ValueError("missing archived Compass history for: " + ", ".join(missing))

    restored: list[str] = []
    for token in requested:
        active_path = history_dir / f"{token}.v1.json"
        if active_path.is_file():
            continue
        archive_path = _history_archive_path(history_dir=history_dir, date_token=token)
        raw = gzip.decompress(archive_path.read_bytes())
        json.loads(raw.decode("utf-8"))
        _write_bytes_atomic(active_path, raw)
        restored.append(token)

    pins = sorted(set(_load_restore_pins(history_dir)) | set(requested), reverse=True)
    pins_path = _write_restore_pins(repo_root=repo_root, history_dir=history_dir, dates=pins)
    return restored, already_active, pins_path


def _build_embedded_history_payload(
    *,
    history_dir: Path,
    kept_dates: Sequence[str],
    history_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the local-file-safe retained history map used by Compass HTML.

    Browsers routinely block `fetch()` against sibling `file:` JSON resources, but they
    still permit static `<script src>` loading for local JS files. Compass therefore
    publishes a generated history JS bundle that mirrors retained daily snapshots and
    normalizes each embedded payload onto the current retained-history metadata so the
    calendar controls remain stable while switching between past days.
    """

    restored_dates_raw = history_meta.get("restored_dates", [])
    restored_dates = (
        [str(item) for item in restored_dates_raw]
        if isinstance(restored_dates_raw, Sequence) and not isinstance(restored_dates_raw, (str, bytes))
        else []
    )
    archive_meta = history_meta.get("archive", {})
    archive_dates_raw = archive_meta.get("dates", []) if isinstance(archive_meta, Mapping) else []
    archive_dates = (
        [str(item) for item in archive_dates_raw]
        if isinstance(archive_dates_raw, Sequence) and not isinstance(archive_dates_raw, (str, bytes))
        else []
    )
    known_dates = _normalize_history_date_tokens(
        [*[str(item) for item in kept_dates], *restored_dates, *archive_dates]
    )
    if known_dates:
        newest_known_date = _parse_date(known_dates[0])
    else:
        newest_known_date = None
    window_floor = newest_known_date - dt.timedelta(days=29) if newest_known_date is not None else None

    snapshots: dict[str, Any] = {}
    for token in known_dates:
        token_date = _parse_date(token)
        if window_floor is not None and token_date is not None and token_date < window_floor:
            continue
        path = history_dir / f"{token}.v1.json"
        archive_path = _history_archive_path(history_dir=history_dir, date_token=token)
        try:
            if path.is_file():
                snapshot = _load_json(path)
            elif archive_path.is_file():
                snapshot = json.loads(gzip.decompress(archive_path.read_bytes()).decode("utf-8"))
            else:
                continue
        except Exception:
            continue
        snapshot_history = snapshot.get("history")
        if isinstance(snapshot_history, Mapping):
            merged_history = dict(snapshot_history)
        else:
            merged_history = {}
        merged_history["retention_days"] = int(history_meta.get("retention_days", 0) or 0)
        merged_history["dates"] = list(history_meta.get("dates", [])) if isinstance(history_meta.get("dates"), list) else []
        merged_history["restored_dates"] = (
            list(history_meta.get("restored_dates", []))
            if isinstance(history_meta.get("restored_dates"), list)
            else []
        )
        merged_history["archive"] = (
            dict(history_meta.get("archive", {}))
            if isinstance(history_meta.get("archive"), Mapping)
            else {}
        )
        snapshot["history"] = merged_history
        snapshots[token] = snapshot
    return {
        "version": "v1",
        "generated_utc": str(history_meta.get("generated_utc", "")).strip(),
        "retention_days": int(history_meta.get("retention_days", 0) or 0),
        "dates": list(history_meta.get("dates", [])) if isinstance(history_meta.get("dates"), list) else [],
        "restored_dates": (
            list(history_meta.get("restored_dates", []))
            if isinstance(history_meta.get("restored_dates"), list)
            else []
        ),
        "archive": dict(history_meta.get("archive", {})) if isinstance(history_meta.get("archive"), Mapping) else {},
        "snapshots": snapshots,
    }


def _write_runtime_snapshots(
    *,
    repo_root: Path,
    runtime_dir: Path,
    payload: dict[str, Any],
    retention_days: int,
) -> tuple[Path, Path, Path, Path, Path]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    history_dir = runtime_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_js_path = history_dir / "embedded.v1.js"

    today = dt.datetime.now(tz=_COMPASS_TZ).date()
    daily_path = history_dir / f"{today.isoformat()}.v1.json"
    current_json_path = runtime_dir / "current.v1.json"
    current_js_path = runtime_dir / "current.v1.js"

    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_json_path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(current_json_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_js_path,
        content="window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        lock_key=str(current_js_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=daily_path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(daily_path),
    )

    requested_restored_dates = _load_restore_pins(history_dir)
    realized_restored_dates = _rehydrate_restored_history(
        history_dir=history_dir,
        restored_dates=requested_restored_dates,
    )
    kept_dates = _archive_history(
        history_dir,
        retention_days=retention_days,
        today=today,
        restored_dates=realized_restored_dates,
    )
    active_restored_dates = sorted(set(realized_restored_dates) & set(kept_dates), reverse=True)
    archive_meta = _history_archive_meta(history_dir)
    index_payload = {
        "version": "v1",
        "generated_utc": payload.get("generated_utc", ""),
        "retention_days": retention_days,
        "dates": kept_dates,
        "restored_dates": active_restored_dates,
        "archive": archive_meta,
    }
    index_path = history_dir / "index.v1.json"
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=index_path,
        content=json.dumps(index_payload, indent=2) + "\n",
        lock_key=str(index_path),
    )

    history = payload.get("history")
    if isinstance(history, dict):
        history["retention_days"] = retention_days
        history["dates"] = kept_dates
        history["restored_dates"] = active_restored_dates
        history["archive"] = archive_meta
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=current_json_path,
            content=json.dumps(payload, indent=2) + "\n",
            lock_key=str(current_json_path),
        )
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=current_js_path,
            content="window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
            lock_key=str(current_js_path),
        )
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=daily_path,
            content=json.dumps(payload, indent=2) + "\n",
            lock_key=str(daily_path),
        )

    embedded_history_payload = _build_embedded_history_payload(
        history_dir=history_dir,
        kept_dates=kept_dates,
        history_meta=index_payload,
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=history_js_path,
        content="window.__ODYLITH_COMPASS_HISTORY__ = " + json.dumps(embedded_history_payload, separators=(",", ":")) + ";\n",
        lock_key=str(history_js_path),
    )

    return current_json_path, current_js_path, daily_path, index_path, history_js_path


__all__ = [
    name
    for name in globals()
    if name.startswith('_') and name not in {'__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__'}
]
