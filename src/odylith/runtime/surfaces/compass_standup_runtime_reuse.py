"""Shell-safe standup brief reuse helpers for Compass runtime refresh."""

from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_standup_brief_narrator

_REUSE_STATE_VERSION = "v1"


def _trimmed_list(items: Sequence[Any] | None, *, limit: int = 0) -> list[str]:
    normalized = [str(item or "").strip() for item in (items or []) if str(item or "").strip()]
    if limit > 0:
        return normalized[:limit]
    return normalized


def _mapping_list(items: Sequence[Mapping[str, Any]] | None, *, limit: int = 0) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in items or []:
        if not isinstance(item, Mapping):
            continue
        row = {
            "idea_id": str(item.get("idea_id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "action": str(item.get("action", "")).strip(),
            "summary": str(item.get("summary", "")).strip(),
            "source": str(item.get("source", "")).strip(),
            "kind": str(item.get("kind", "")).strip(),
        }
        if any(row.values()):
            rows.append(row)
        if limit > 0 and len(rows) >= limit:
            break
    return rows


def _self_host_signature(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    source = snapshot if isinstance(snapshot, Mapping) else {}
    return {
        "repo_role": str(source.get("repo_role", "")).strip(),
        "posture": str(source.get("posture", "")).strip(),
        "runtime_source": str(source.get("runtime_source", "")).strip(),
        "pinned_version": str(source.get("pinned_version", "")).strip(),
        "active_version": str(source.get("active_version", "")).strip(),
        "release_eligible": source.get("release_eligible"),
    }


def _brief_sections(brief: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_sections = brief.get("sections")
    return [dict(item) for item in raw_sections if isinstance(item, Mapping)] if isinstance(raw_sections, Sequence) else []


def prior_runtime_state(
    *,
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = payload if isinstance(payload, Mapping) else {}
    runtime_contract = source.get("runtime_contract")
    if not isinstance(runtime_contract, Mapping):
        return {}
    if str(runtime_contract.get("standup_brief_schema_version", "")).strip() != compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION:
        return {}
    runtime_state = source.get("standup_runtime")
    standup_brief = source.get("standup_brief")
    standup_brief_scoped = source.get("standup_brief_scoped")
    return {
        "runtime": dict(runtime_state) if isinstance(runtime_state, Mapping) else {},
        "global": dict(standup_brief) if isinstance(standup_brief, Mapping) else {},
        "scoped": dict(standup_brief_scoped) if isinstance(standup_brief_scoped, Mapping) else {},
    }


def window_runtime_state(
    prior_state: Mapping[str, Any] | None,
    *,
    window_key: str,
) -> dict[str, Any]:
    source = prior_state if isinstance(prior_state, Mapping) else {}
    runtime_state = source.get("runtime")
    if not isinstance(runtime_state, Mapping):
        return {}
    window_state = runtime_state.get(str(window_key).strip())
    return dict(window_state) if isinstance(window_state, Mapping) else {}


def window_global_brief(
    prior_state: Mapping[str, Any] | None,
    *,
    window_key: str,
) -> dict[str, Any]:
    source = prior_state if isinstance(prior_state, Mapping) else {}
    global_map = source.get("global")
    if not isinstance(global_map, Mapping):
        return {}
    brief = global_map.get(str(window_key).strip())
    return dict(brief) if isinstance(brief, Mapping) else {}


def window_scoped_briefs(
    prior_state: Mapping[str, Any] | None,
    *,
    window_key: str,
) -> dict[str, dict[str, Any]]:
    source = prior_state if isinstance(prior_state, Mapping) else {}
    scoped_map = source.get("scoped")
    if not isinstance(scoped_map, Mapping):
        return {}
    window_map = scoped_map.get(str(window_key).strip())
    if not isinstance(window_map, Mapping):
        return {}
    return {
        str(scope_id).strip(): dict(brief)
        for scope_id, brief in window_map.items()
        if str(scope_id).strip() and isinstance(brief, Mapping)
    }


def brief_ready_without_notice(brief: Mapping[str, Any] | None) -> bool:
    source = brief if isinstance(brief, Mapping) else {}
    return (
        str(source.get("status", "")).strip().lower() == "ready"
        and not isinstance(source.get("notice"), Mapping)
    )


def reuse_ready_brief(
    *,
    brief: Mapping[str, Any],
    generated_utc: str,
    fingerprint: str,
    sections: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_lookup = brief.get("evidence_lookup")
    cached_source = str(brief.get("source", "")).strip().lower()
    cache_mode = "fallback" if cached_source in {"provider", "cache"} else ""
    return compass_standup_brief_narrator._ready_brief(  # noqa: SLF001
        source="cache",
        fingerprint=str(fingerprint).strip(),
        generated_utc=str(generated_utc or "").strip(),
        sections=[
            dict(item)
            for item in (sections if isinstance(sections, Sequence) else _brief_sections(brief))
            if isinstance(item, Mapping)
        ],
        evidence_lookup=evidence_lookup if isinstance(evidence_lookup, Mapping) else {},
        cache_mode=cache_mode,
    )


def scoped_reuse_fingerprint(
    *,
    row: Mapping[str, Any],
    window_hours: int,
    next_action_tokens: Sequence[str],
    completed_deliverables: Sequence[str],
    execution_updates: Sequence[Mapping[str, Any]],
    transaction_updates: Sequence[Mapping[str, Any]],
    risk_summary: str,
    self_host_snapshot: Mapping[str, Any] | None,
) -> str:
    activity = row.get("activity")
    activity_window = (
        activity.get(f"{int(window_hours)}h", {})
        if isinstance(activity, Mapping)
        else {}
    )
    plan = row.get("plan") if isinstance(row.get("plan"), Mapping) else {}
    timeline = row.get("timeline") if isinstance(row.get("timeline"), Mapping) else {}
    payload = {
        "version": _REUSE_STATE_VERSION,
        "window_hours": int(window_hours),
        "idea_id": str(row.get("idea_id", "")).strip(),
        "title": str(row.get("title", "")).strip(),
        "status": str(row.get("status", "")).strip(),
        "release": str((row.get("release") or {}).get("release_id", "")).strip() if isinstance(row.get("release"), Mapping) else "",
        "activity": {
            "commit_count": int(activity_window.get("commit_count", 0) or 0),
            "local_change_count": int(activity_window.get("local_change_count", 0) or 0),
            "file_touch_count": int(activity_window.get("file_touch_count", 0) or 0),
        },
        "plan": {
            "progress_ratio": float(plan.get("progress_ratio", 0.0) or 0.0),
            "done_tasks": int(plan.get("done_tasks", 0) or 0),
            "total_tasks": int(plan.get("total_tasks", 0) or 0),
            "progress_classification": str(plan.get("progress_classification", "")).strip(),
            "display_progress_label": str(plan.get("display_progress_label", "")).strip(),
            "display_progress_state": str(plan.get("display_progress_state", "")).strip(),
            "next_tasks": _trimmed_list(plan.get("next_tasks") if isinstance(plan.get("next_tasks"), Sequence) else [], limit=2),
        },
        "timeline": {
            "last_activity_iso": str(timeline.get("last_activity_iso", "")).strip(),
            "eta_days": timeline.get("eta_days"),
            "eta_confidence": str(timeline.get("eta_confidence", "")).strip(),
        },
        "next_action_tokens": _trimmed_list(next_action_tokens, limit=2),
        "completed_deliverables": _trimmed_list(completed_deliverables, limit=2),
        "execution_updates": _mapping_list(execution_updates, limit=2),
        "transaction_updates": _mapping_list(transaction_updates, limit=2),
        "risk_summary": str(risk_summary or "").strip(),
        "self_host": _self_host_signature(self_host_snapshot),
    }
    return odylith_context_cache.fingerprint_payload(payload)


def global_reuse_fingerprint(
    *,
    window_hours: int,
    focus_rows: Sequence[Mapping[str, Any]],
    active_ws_rows: Sequence[Mapping[str, Any]],
    touched_workstreams: Sequence[str],
    next_actions: Sequence[Mapping[str, Any]],
    recent_completed: Sequence[Mapping[str, Any]],
    execution_updates: Sequence[Mapping[str, Any]],
    transaction_updates: Sequence[Mapping[str, Any]],
    kpis: Mapping[str, Any],
    risk_summary: str,
    self_host_snapshot: Mapping[str, Any] | None,
) -> str:
    payload = {
        "version": _REUSE_STATE_VERSION,
        "window_hours": int(window_hours),
        "focus_rows": [
            {
                "idea_id": str(row.get("idea_id", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "status": str(row.get("status", "")).strip(),
                "progress_ratio": float(((row.get("plan") or {}) if isinstance(row.get("plan"), Mapping) else {}).get("progress_ratio", 0.0) or 0.0),
                "progress_classification": str((((row.get("plan") or {}) if isinstance(row.get("plan"), Mapping) else {}).get("progress_classification", ""))).strip(),
                "display_progress_label": str((((row.get("plan") or {}) if isinstance(row.get("plan"), Mapping) else {}).get("display_progress_label", ""))).strip(),
                "display_progress_state": str((((row.get("plan") or {}) if isinstance(row.get("plan"), Mapping) else {}).get("display_progress_state", ""))).strip(),
            }
            for row in focus_rows[:3]
            if isinstance(row, Mapping)
        ],
        "active_ids": _trimmed_list(
            [str(row.get("idea_id", "")).strip() for row in active_ws_rows if isinstance(row, Mapping)],
            limit=16,
        ),
        "touched_workstreams": _trimmed_list(touched_workstreams, limit=16),
        "next_actions": _mapping_list(next_actions, limit=2),
        "recent_completed": _mapping_list(recent_completed, limit=4),
        "execution_updates": _mapping_list(execution_updates, limit=3),
        "transaction_updates": _mapping_list(transaction_updates, limit=3),
        "kpis": {
            "commits": int(kpis.get("commits", 0) or 0),
            "local_changes": int(kpis.get("local_changes", 0) or 0),
            "touched_workstreams": int(kpis.get("touched_workstreams", 0) or 0),
            "active_workstreams": int(kpis.get("active_workstreams", 0) or 0),
            "critical_risks": int(kpis.get("critical_risks", 0) or 0),
            "recent_completed_plans": int(kpis.get("recent_completed_plans", 0) or 0),
        },
        "risk_summary": str(risk_summary or "").strip(),
        "self_host": _self_host_signature(self_host_snapshot),
    }
    return odylith_context_cache.fingerprint_payload(payload)
