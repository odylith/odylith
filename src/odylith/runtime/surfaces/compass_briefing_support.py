"""Shared Compass workstream briefing helpers.

This module owns the narrative, digest, and standup helper functions that are
shared across Compass outcome digests, standup fact packets, and hot-path
update indexing. Keeping them here prevents extracted runtime slices from
tunneling back into the monolithic dashboard runtime.
"""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.surfaces import compass_dashboard_base as compass_base
from odylith.runtime.surfaces import compass_narrative_runtime
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import compass_transaction_runtime


_FRESHNESS_LIVE_MAX_MINUTES = 90
_FRESHNESS_RECENT_MAX_MINUTES = 6 * 60
_FRESHNESS_AGING_MAX_MINUTES = 24 * 60
_OPERATOR_IMPACT_LEADS = (
    "help operators ",
    "let operators ",
    "gives operators ",
    "gives teams ",
    "keeps operators ",
)
_WHY_PRIORITY_LEAD_RE = re.compile(
    r"^(?:for\s+)?(?:[-*]\s*)?(?:primary|secondary|tertiary)\s*:\s*",
    re.IGNORECASE,
)
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


def _periodize(text: str) -> str:
    token = compass_base._normalize_sentence(text)
    if not token:
        return ""
    if token[-1] in ".!?":
        return token
    return f"{token}."


def _decapitalize_clause(text: str) -> str:
    token = compass_base._normalize_sentence(text).rstrip(".")
    if not token:
        return ""
    if len(token) == 1:
        return token.lower()
    return token[:1].lower() + token[1:]


def _risk_phrase(risk_posture: str) -> str:
    token = compass_base._normalize_sentence(risk_posture)
    if not token:
        return "no critical blockers are currently surfaced"
    lowered = token.lower()
    if lowered.startswith("risk posture:"):
        token = token.split(":", 1)[1].strip()
    return token.rstrip(" .")


def _sentence_without_period(text: str) -> str:
    return compass_base._normalize_sentence(text).rstrip(" .")


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
        compass_base._narrative_excerpt(str(why.get("problem", "")).strip(), max_sentences=1, max_chars=220)
    )
    customer = _normalize_why_fragment(
        compass_base._narrative_excerpt(str(why.get("customer", "")).strip(), max_sentences=1, max_chars=160)
    )
    proposed_solution = _normalize_why_fragment(
        compass_base._narrative_excerpt(
            str(why.get("proposed_solution", "")).strip(),
            max_sentences=1,
            max_chars=220,
        )
    )
    why_now = _normalize_why_fragment(
        compass_base._narrative_excerpt(str(why.get("why_now", "")).strip(), max_sentences=1, max_chars=280)
    )
    opportunity = _normalize_why_fragment(
        compass_base._narrative_excerpt(str(why.get("opportunity", "")).strip(), max_sentences=1, max_chars=280)
    )
    founder = _normalize_why_fragment(
        compass_base._narrative_excerpt(str(why.get("founder_pov", "")).strip(), max_sentences=1, max_chars=280)
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
    return context.get("purpose", ""), context.get("benefit", "")


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
    return compass_base._narrative_excerpt(token, max_sentences=1, max_chars=96)


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

    base_days = compass_base._SIZE_DAY_BASE.get(sizing, 10) + compass_base._COMPLEXITY_DAY_DELTA.get(complexity, 2)
    remaining_factor = max(0.2, 1.0 - progress_ratio)
    estimate = int(math.ceil(base_days * remaining_factor))
    if status == "planning" and progress_ratio <= 0.01:
        estimate += 2
    estimate = max(1, int(math.ceil(estimate * compass_base._HEURISTIC_AI_ACCELERATION_FACTOR)))
    return estimate, "heuristic"


def _build_completed_group_lines(
    recent_completed: Sequence[Mapping[str, str]],
    *,
    ws_index: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    groups: dict[str, dict[str, Any]] = {}
    for row in recent_completed:
        ws_id = str(row.get("backlog", "")).strip()
        if not compass_base._WORKSTREAM_ID_RE.fullmatch(ws_id):
            continue
        ws_row = ws_index.get(ws_id, {})
        label = _ws_label(ws_row) if ws_row else ws_id
        bucket = groups.setdefault(ws_id, {"label": label, "deliverables": []})
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


def _clean_execution_clause(text: str) -> str:
    return _periodize(str(text or "")).rstrip(".").replace("`", "").strip()


def _normalize_action_task(text: str) -> str:
    token = _clean_execution_clause(text)
    if not token:
        return ""
    match = _PASSIVE_ACTION_RE.match(token)
    if match is None:
        return token
    subject = compass_base._normalize_sentence(str(match.group("subject") or "").strip())
    verb = _PASSIVE_ACTION_VERB_MAP.get(str(match.group("verb") or "").strip().lower(), "")
    rest = compass_base._normalize_sentence(str(match.group("rest") or "").strip())
    if not subject or not verb:
        return token
    rebuilt = f"{verb} {subject}"
    if rest:
        rebuilt = f"{rebuilt}{(' ' if not rest.startswith((',', ';', ':')) else '')}{rest}"
    return rebuilt.strip()


def _action_tokens_for_workstream(
    next_actions: Sequence[Mapping[str, str]],
    ws_id: str,
    *,
    max_items: int = 2,
) -> list[str]:
    tokens: list[str] = []
    for row in next_actions:
        if str(row.get("idea_id", "")).strip() != ws_id:
            continue
        action = _normalize_action_task(
            compass_base._narrative_excerpt(
                str(row.get("action", "")).strip().rstrip(".; "),
                max_sentences=1,
                max_chars=180,
            )
        ).rstrip(" .;")
        if not action:
            continue
        if action.lower() in {token.lower() for token in tokens}:
            continue
        tokens.append(action)
        if len(tokens) >= max_items:
            break
    return tokens


def _sanitize_digest_summary(summary: str) -> str:
    token = compass_base._normalize_sentence(summary).rstrip(".")
    if not token:
        return ""
    token = _CHECKLIST_RATIO_RE.sub("checklist progress updated", token)
    token = re.sub(r"\b\d+\s*/\s*\d+\b", "", token)
    token = compass_base._normalize_sentence(token).rstrip(".")
    return token


def _looks_generic_churn_summary(summary: str) -> bool:
    token = compass_base._normalize_sentence(summary)
    if not token:
        return True
    return bool(_GENERIC_CHURN_RE.search(token))


def _surface_signal_score(files: Sequence[str]) -> int:
    score = 0
    for raw in files:
        token = compass_base._normalize_repo_token(str(raw)).lower()
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
    token = compass_base._normalize_sentence(summary)
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
    summary_token = compass_base._normalize_sentence(summary).lower()
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
        summary = compass_base._humanize_execution_event_summary(
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
                and compass_base._normalize_sentence(str(item.get("text", "")).strip())
            ],
            key=lambda row: (
                int(row.get("priority", 0) or 0),
                str(row.get("text", "")).strip(),
            ),
            reverse=True,
        )
        section_facts: list[dict[str, Any]] = []
        for candidate in ranked_candidates:
            normalized_text = compass_base._normalize_sentence(str(candidate.get("text", "")).strip())
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
        sections.append({"key": section_key, "label": label, "facts": section_facts})
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
    return {"bugs": bugs, "traceability": trace, "stale_diagrams": stale}


def _risk_facts(
    *,
    ws_id: str | None,
    risk_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    risk_summary: str,
    fallback_text: str = "",
) -> list[dict[str, Any]]:
    workstreams = [str(ws_id).strip()] if str(ws_id or "").strip() else []
    facts: list[dict[str, Any]] = []
    bugs = [dict(item) for item in risk_rows.get("bugs", []) if isinstance(item, Mapping)]
    trace = [dict(item) for item in risk_rows.get("traceability", []) if isinstance(item, Mapping)]
    stale = [dict(item) for item in risk_rows.get("stale_diagrams", []) if isinstance(item, Mapping)]
    if bugs:
        first = bugs[0]
        severity = str(first.get("severity", "")).strip() or "critical"
        title = compass_base._narrative_excerpt(str(first.get("title", "")).strip(), max_sentences=1, max_chars=220)
        severity_label = severity.upper()
        bug_text = _periodize(title)
        if severity_label:
            bug_text = bug_text.rstrip(".") + f". It is still open at {severity_label}."
        facts.append(
            _standup_fact(
                section_key="risks_to_watch",
                voice_hint="operator",
                priority=100,
                text=bug_text,
                source="bugs",
                kind="bug",
                workstreams=workstreams,
            )
        )
    if trace:
        first = trace[0]
        message = compass_base._narrative_excerpt(
            str(first.get("message", "")).strip() or str(first.get("category", "")).strip(),
            max_sentences=1,
            max_chars=220,
        )
        trace_text = _periodize(message)
        if trace_text:
            trace_text = trace_text.rstrip(".") + ". It still needs cleanup."
        facts.append(
            _standup_fact(
                section_key="risks_to_watch",
                voice_hint="operator",
                priority=92,
                text=trace_text,
                source="traceability",
                kind="traceability",
                workstreams=workstreams,
            )
        )
    if stale:
        first = stale[0]
        diagram_id = str(first.get("diagram_id", "")).strip()
        age_days = int(first.get("age_days", 0) or 0)
        title = compass_base._narrative_excerpt(str(first.get("title", "")).strip(), max_sentences=1, max_chars=140)
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
        fallback = _periodize(compass_base._normalize_sentence(fallback_text)) if compass_base._normalize_sentence(fallback_text) else ""
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
    token = compass_base._normalize_sentence(wave_context)
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
        parsed = compass_base._parse_iso_ts(str(timeline.get("last_activity_iso", "")).strip())
        if parsed is None:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return compass_base._safe_iso(latest) if latest else ""


def _matches_freshness_scope(tokens: Sequence[str], ws_id: str | None) -> bool:
    scope_token = str(ws_id or "").strip()
    if not scope_token:
        return True
    return scope_token in {str(token).strip() for token in tokens if str(token).strip()}


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
        candidate = ts if isinstance(ts, dt.datetime) else compass_base._parse_iso_ts(str(row.get("ts_iso", "")).strip())
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
        candidate = compass_base._parse_iso_ts(str(row.get("end_ts_iso", "")).strip()) or compass_base._parse_iso_ts(
            str(row.get("start_ts_iso", "")).strip()
        )
        if candidate is None:
            continue
        if latest is None or candidate > latest:
            latest = candidate
            source_kind = "transaction"
    if latest is None and str(fallback_last_activity_iso).strip():
        fallback = compass_base._parse_iso_ts(str(fallback_last_activity_iso).strip())
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
