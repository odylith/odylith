"""Governance-graph analysis for the Project tab projection."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from odylith.runtime.project_intelligence.personas import audience_emphasis_rows
from odylith.runtime.project_intelligence.summary import concise_text
from odylith.runtime.project_intelligence.utils import list_value, sentence, short, strings


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _execution_focus(compass: Mapping[str, Any]) -> dict[str, Any]:
    focus = _dict(compass.get("execution_focus"))
    return _dict(focus.get("global"))


def _source_meta(repo_root: Path, label: str, path: str, *, count: int = 0, required: bool = True) -> dict[str, Any]:
    source_path = repo_root / path
    exists = source_path.exists()
    modified = datetime.fromtimestamp(source_path.stat().st_mtime, tz=timezone.utc) if exists else None
    age_hours = None
    freshness = "missing" if required else "optional missing"
    if modified:
        age_hours = max(0.0, (datetime.now(timezone.utc) - modified).total_seconds() / 3600)
        if age_hours <= 24:
            freshness = "fresh"
        elif age_hours <= 24 * 7:
            freshness = "recent"
        else:
            freshness = "stale"
    return {
        "surface": label,
        "path": path,
        "count": count,
        "exists": exists,
        "refreshed": modified.isoformat(timespec="seconds").replace("+00:00", "Z") if modified else "not found",
        "freshness": freshness,
        "age_hours": round(age_hours, 1) if age_hours is not None else None,
    }


def _surface_health(source: Mapping[str, Any]) -> str:
    if not source.get("exists"):
        return "missing"
    if str(source.get("freshness")) == "stale":
        return "stale"
    if int(source.get("count", 0) or 0) <= 0:
        return "thin"
    return "covered"


def _evidence_maturity(source: Mapping[str, Any], *, validated: bool = False, operational: bool = False) -> str:
    if operational:
        return "operational"
    if validated:
        return "validated"
    if not source.get("exists"):
        return "inferred"
    if str(source.get("freshness")) == "stale":
        return "stale"
    return "source-backed"


def _claim_row(
    claim: str,
    value: object,
    source: Mapping[str, Any],
    owner: str,
    *,
    validated: bool = False,
    operational: bool = False,
) -> dict[str, str]:
    return {
        "claim": claim,
        "value": short(value, limit=130, fallback="Unknown"),
        "evidence": _evidence_maturity(source, validated=validated, operational=operational),
        "freshness": sentence(source.get("freshness"), "unknown"),
        "refreshed": sentence(source.get("refreshed"), "not found"),
        "owner": owner or "owner unknown",
        "source": sentence(source.get("surface"), "unknown"),
    }


def _workstream_ids(rows: object) -> set[str]:
    ids: set[str] = set()
    for row in list_value(rows):
        if not isinstance(row, Mapping):
            continue
        for key in ("idea_id", "Idea ID", "Backlog", "backlog", "workstream", "Workstream"):
            ids.update(re.findall(r"\bB-\d+\b", str(row.get(key, "")).strip()))
    return ids


def _work_mode(*, focus: Mapping[str, Any], plans: Mapping[str, Any], worktree: Mapping[str, Any], actions: Sequence[Mapping[str, Any]]) -> str:
    text = " ".join(
        [
            sentence(focus.get("headline")),
            " ".join(sentence(action.get("action")) for action in actions),
            sentence(worktree.get("status")),
        ]
    ).lower()
    if any(word in text for word in ("recover", "rollback", "incident", "repair")):
        return "Recovering"
    if any(word in text for word in ("release", "publish", "ship")):
        return "Releasing"
    if any(word in text for word in ("validate", "proof", "test", "benchmark")):
        return "Validating"
    if any(word in text for word in ("refactor", "migration", "cleanup")):
        return "Refactoring"
    if int(plans.get("active_count", 0) or 0) > 0 or any(word in text for word in ("implement", "build", "update")):
        return "Implementing"
    if int(plans.get("parked_count", 0) or 0) > 0:
        return "Planning"
    return "Orienting"


def _maturity_gradient(
    *,
    components: Sequence[Mapping[str, Any]],
    backlog: Mapping[str, Any],
    plans: Mapping[str, Any],
    atlas: Mapping[str, Any],
    casebook: Mapping[str, Any],
    release: Mapping[str, Any],
    compass: Mapping[str, Any],
) -> str:
    score = 0
    score += 2 if len(components) >= 10 else 1 if components else 0
    score += 2 if int(atlas.get("active_count", 0) or 0) >= 5 else 1 if int(atlas.get("active_count", 0) or 0) else 0
    score += 2 if int(plans.get("active_count", 0) or 0) or int(plans.get("completed_recent_count", 0) or 0) else 0
    score += 1 if int(backlog.get("finished_count", 0) or 0) else 0
    score += 1 if release else 0
    score += 1 if compass.get("timeline_events") or compass.get("history") else 0
    score -= 1 if int(casebook.get("critical_count", 0) or 0) >= 5 else 0
    if score >= 8:
        return "Operational product"
    if score >= 6:
        return "Mature build"
    if score >= 4:
        return "Built but moving"
    if score >= 2:
        return "Young project"
    return "Greenfield or thin evidence"


def _topology_profile(*, components: Sequence[Mapping[str, Any]], atlas: Mapping[str, Any], casebook: Mapping[str, Any], plans: Mapping[str, Any], evidence_sources: Sequence[str]) -> list[str]:
    profile: list[str] = []
    if len(components) >= 20:
        profile.append("component-heavy")
    if int(atlas.get("active_count", 0) or 0) >= 10:
        profile.append("topology-heavy")
    if int(casebook.get("critical_count", 0) or 0) >= 3:
        profile.append("risk-heavy")
    if int(plans.get("active_count", 0) or 0) >= 3:
        profile.append("plan-heavy")
    if len(evidence_sources) >= 4:
        profile.append("evidence-heavy")
    return profile or ["simple spine"]


def _risk_classes(casebook: Mapping[str, Any], worktree: Mapping[str, Any]) -> list[dict[str, str]]:
    classes: dict[str, str] = {}
    for bug in [row for row in casebook.get("critical", []) if isinstance(row, Mapping)]:
        text = f"{bug.get('title', '')} {bug.get('components', '')}".lower()
        if any(word in text for word in ("security", "secret", "auth")):
            classes["Security"] = "Security or access-control risk appears in open Casebook records."
        if any(word in text for word in ("release", "migration", "upgrade", "rollback")):
            classes["Release"] = "Release, migration, or rollback risk is open."
        if any(word in text for word in ("dashboard", "surface", "ui", "browser")):
            classes["Operator UX"] = "Operator-facing surface proof is at risk."
        if any(word in text for word in ("atlas", "registry", "compass", "radar", "casebook", "governance")):
            classes["Governance spine"] = "Governance artifact integrity is at risk."
    if int(worktree.get("meaningful_changed_count", 0) or 0) > 0:
        classes.setdefault("Uncommitted change", "Meaningful source changes are active in the current worktree.")
    return [{"risk": key, "meaning": value} for key, value in classes.items()] or [
        {"risk": "No dominant class", "meaning": "No specific risk class dominates the current projection."}
    ]


def _artifact_coverage(sources: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "surface": sentence(source.get("surface"), "Unknown"),
            "coverage": _surface_health(source),
            "count": str(source.get("count", 0) or 0),
            "freshness": sentence(source.get("freshness"), "unknown"),
            "source": sentence(source.get("path"), "not found"),
        }
        for source in sources
    ]


def _topology_spine(
    *,
    components: Sequence[Mapping[str, Any]],
    backlog: Mapping[str, Any],
    plans: Mapping[str, Any],
    atlas: Mapping[str, Any],
    casebook: Mapping[str, Any],
    compass: Mapping[str, Any],
) -> list[dict[str, str]]:
    return [
        {"link": "Radar -> Plans", "health": "covered" if int(backlog.get("execution_count", 0) or 0) and int(plans.get("active_count", 0) or 0) else "thin", "detail": f"{backlog.get('execution_count', 0)} implementation workstreams and {plans.get('active_count', 0)} active plans."},
        {"link": "Plans -> Registry", "health": "covered" if plans.get("active_count") and components else "thin", "detail": f"{plans.get('active_count', 0)} active plans can resolve against {len(components)} components."},
        {"link": "Registry -> Atlas", "health": "covered" if components and int(atlas.get("active_count", 0) or 0) else "missing", "detail": f"{len(components)} components and {atlas.get('active_count', 0)} active diagrams."},
        {"link": "Risks -> Validation", "health": "blocked" if int(casebook.get("critical_count", 0) or 0) else "covered", "detail": f"{casebook.get('critical_count', 0)} critical Casebook blockers are open."},
        {"link": "Runtime -> Decisions", "health": "covered" if compass.get("execution_focus") and compass.get("next_actions") else "thin", "detail": "Compass current runtime links focus and next actions." if compass else "Compass current runtime is missing."},
    ]


def _contradictions(
    *,
    backlog: Mapping[str, Any],
    release: Mapping[str, Any],
    focus: Mapping[str, Any],
    actions: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
) -> list[str]:
    issues: list[str] = []
    radar_ids = _workstream_ids(backlog.get("queued")) | _workstream_ids(backlog.get("execution")) | _workstream_ids(backlog.get("finished"))
    compass_ids = set(strings(focus.get("workstreams"))) | set(strings(release.get("active_workstreams")))
    missing = sorted(token for token in compass_ids if token and token not in radar_ids)
    if missing:
        issues.append(f"Compass references workstreams not present in Radar index: {', '.join(missing[:5])}.")
    expected_count = release.get("active_workstream_count")
    if expected_count is not None and int(expected_count or 0) != len(strings(release.get("active_workstreams"))):
        issues.append("Compass release active-workstream count differs from the listed active workstreams.")
    action_ids = {token for action in actions for token in re.findall(r"\bB-\d+\b", " ".join(str(value) for value in action.values()))}
    missing_actions = sorted(token for token in action_ids if token not in radar_ids)
    if missing_actions:
        issues.append(f"Next action references workstreams not present in Radar index: {', '.join(missing_actions[:5])}.")
    component_ids = {str(row.get("component_id", "")).strip() for row in components if str(row.get("component_id", "")).strip()}
    for row in components:
        for child in strings(row.get("subcomponents")):
            if child and child not in component_ids:
                issues.append(f"Registry component {row.get('component_id')} references missing subcomponent {child}.")
                break
        if len(issues) >= 4:
            break
    return issues or ["No cross-surface contradiction detected in the current projection."]


def _history_snapshot(repo_root: Path) -> dict[str, Any]:
    index = _read_json(repo_root / "odylith" / "compass" / "runtime" / "history" / "index.v1.json")
    dates = strings(index.get("dates"))
    if len(dates) < 2:
        return {}
    return _read_json(repo_root / "odylith" / "compass" / "runtime" / "history" / f"{dates[1]}.v1.json")


def _snapshot_delta(current: Mapping[str, Any], previous: Mapping[str, Any], *, casebook: Mapping[str, Any]) -> list[str]:
    if not previous:
        return ["No previous Compass history snapshot is available for comparison."]
    current_focus = _execution_focus(current)
    previous_focus = _execution_focus(previous)
    deltas: list[str] = []
    current_headline = sentence(current_focus.get("headline"))
    previous_headline = sentence(previous_focus.get("headline"))
    if current_headline and current_headline != previous_headline:
        deltas.append(f"Focus changed from '{concise_text(previous_headline, limit=70)}' to '{concise_text(current_headline, limit=70)}'.")
    current_ws = set(strings(current_focus.get("workstreams")))
    previous_ws = set(strings(previous_focus.get("workstreams")))
    added = sorted(current_ws - previous_ws)
    removed = sorted(previous_ws - current_ws)
    if added:
        deltas.append(f"New active workstream signals: {', '.join(added[:6])}.")
    if removed:
        deltas.append(f"Workstream signals no longer active: {', '.join(removed[:6])}.")
    current_generated = sentence(current.get("generated_utc"))
    previous_generated = sentence(previous.get("generated_utc"))
    if current_generated and current_generated != previous_generated:
        deltas.append(f"Runtime snapshot advanced from {previous_generated or 'unknown'} to {current_generated}.")
    if int(casebook.get("critical_count", 0) or 0):
        deltas.append(f"{casebook.get('critical_count', 0)} critical blockers remain open in the current Casebook projection.")
    return deltas or ["No material delta detected from the previous Compass history snapshot."]


def _validation_posture(*, evidence: str, critical_count: int, sources: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    missing = [source for source in sources if not source.get("exists")]
    stale = [source for source in sources if source.get("freshness") == "stale"]
    understanding = "High" if evidence == "Source-backed runtime" and not missing else "Medium" if evidence != "Inferred" else "Low"
    recommendation = "Low" if critical_count else "High" if evidence == "Source-backed runtime" and not stale else "Medium"
    return [
        {"posture": "Project understanding", "level": understanding, "meaning": "How well the graph explains the current project shape from source artifacts."},
        {"posture": "Recommendation proof", "level": recommendation, "meaning": "How safe the next action is based on current evidence, blockers, and freshness."},
    ]


def _degraded_state(sources: Sequence[Mapping[str, Any]], contradictions: Sequence[str]) -> list[str]:
    gaps = [f"{source.get('surface')} source missing at {source.get('path')}" for source in sources if not source.get("exists")]
    gaps.extend(issue for issue in contradictions if "No cross-surface contradiction" not in issue)
    return gaps or ["No degraded source condition detected for the current projection."]


def build_governance_graph_projection(
    *,
    repo_root: Path,
    components: Sequence[Mapping[str, Any]],
    backlog: Mapping[str, Any],
    plans: Mapping[str, Any],
    atlas: Mapping[str, Any],
    casebook: Mapping[str, Any],
    compass: Mapping[str, Any],
    focus: Mapping[str, Any],
    release: Mapping[str, Any],
    actions: Sequence[Mapping[str, Any]],
    worktree: Mapping[str, Any],
    evidence: str,
    evidence_sources: Sequence[str],
    blockers: Sequence[tuple[str, str, str]],
    project_title: str,
    project_intro: str,
    current_focus: str,
    release_label: str,
    next_action_text: str,
    next_action: Mapping[str, Any],
) -> dict[str, Any]:
    """Return time-bound governance graph facts for the rendered Project page."""

    source_metas = [
        _source_meta(repo_root, "Registry", "odylith/registry/source/component_registry.v1.json", count=len(components)),
        _source_meta(repo_root, "Radar", "odylith/radar/source/INDEX.md", count=int(backlog.get("queued_count", 0) or 0) + int(backlog.get("execution_count", 0) or 0)),
        _source_meta(repo_root, "Plans", "odylith/technical-plans/INDEX.md", count=int(plans.get("active_count", 0) or 0)),
        _source_meta(repo_root, "Atlas", "odylith/atlas/source/catalog/diagrams.v1.json", count=int(atlas.get("active_count", 0) or 0)),
        _source_meta(repo_root, "Casebook", "odylith/casebook/bugs/INDEX.md", count=int(casebook.get("open_count", 0) or 0)),
        _source_meta(repo_root, "Compass", "odylith/compass/runtime/current.v1.json", count=1 if compass else 0),
    ]
    source_by_surface = {str(source.get("surface")): source for source in source_metas}
    work_mode = _work_mode(focus=focus, plans=plans, worktree=worktree, actions=actions)
    maturity = _maturity_gradient(components=components, backlog=backlog, plans=plans, atlas=atlas, casebook=casebook, release=release, compass=compass)
    topology_profile = _topology_profile(components=components, atlas=atlas, casebook=casebook, plans=plans, evidence_sources=evidence_sources)
    contradictions = _contradictions(backlog=backlog, release=release, focus=focus, actions=actions, components=components)
    delta = _snapshot_delta(compass, _history_snapshot(repo_root), casebook=casebook)
    refreshed_at = sentence(compass.get("generated_utc")) or sentence(focus.get("last_event_iso")) or sentence(source_by_surface["Compass"].get("refreshed"))
    return {
        "projection": {
            "refreshed_at": refreshed_at,
            "origin": "",
            "maturity": maturity,
            "work_mode": work_mode,
            "topology_profile": ", ".join(topology_profile),
        },
        "claim_evidence": [
            _claim_row("Project identity", project_title, source_by_surface["Registry"], "Registry"),
            _claim_row("Project explanation", project_intro, source_by_surface["Registry"], "Registry"),
            _claim_row("Current focus", current_focus, source_by_surface["Compass"], "Compass", operational=bool(compass)),
            _claim_row("Current release", release_label, source_by_surface["Compass"], "Compass", operational=bool(release)),
            _claim_row("Next action", next_action_text, source_by_surface["Compass"], sentence(next_action.get("source"), "Compass")),
            _claim_row("Risk posture", blockers[0][0] if blockers else "No blocker", source_by_surface["Casebook"], "Casebook"),
            _claim_row("Topology evidence", f"{atlas.get('active_count', 0)} active diagrams", source_by_surface["Atlas"], "Atlas"),
            _claim_row("Implementation plan", f"{plans.get('active_count', 0)} active plans", source_by_surface["Plans"], "Plans"),
        ],
        "artifact_coverage": _artifact_coverage(source_metas),
        "topology_spine": _topology_spine(components=components, backlog=backlog, plans=plans, atlas=atlas, casebook=casebook, compass=compass),
        "contradictions": contradictions,
        "delta": delta,
        "risk_classes": _risk_classes(casebook, worktree),
        "validation_posture": _validation_posture(evidence=evidence, critical_count=int(casebook.get("critical_count", 0) or 0), sources=source_metas),
        "audience_emphasis": audience_emphasis_rows(
            work_mode=work_mode,
            topology_profile=topology_profile,
            evidence_sources=evidence_sources,
            critical_count=int(casebook.get("critical_count", 0) or 0),
        ),
        "degraded_state": _degraded_state(source_metas, contradictions),
        "maturity": maturity,
        "work_mode": work_mode,
        "refreshed_at": refreshed_at,
    }
