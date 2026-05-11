"""Build the source-backed Project tab projection."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.project_intelligence.answers import source_answer_cards as _source_answer_cards
from odylith.runtime.project_intelligence.focus import backlog_rows_by_id as _backlog_rows_by_id
from odylith.runtime.project_intelligence.focus import project_focus_text as _project_focus_text
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload
from odylith.runtime.project_intelligence.greenfield import proposal_from_sources
from odylith.runtime.project_intelligence.governance_graph import build_governance_graph_projection
from odylith.runtime.project_intelligence.narration import (
    primary_lens as _primary_lens,
    scenario as _scenario,
    scenario_details as _scenario_details,
    section_narration as _section_narration,
    table_columns as _table_columns,
)
from odylith.runtime.project_intelligence.personas import source_persona_cards as _source_persona_cards
from odylith.runtime.project_intelligence.summary import concise_text as _concise_text
from odylith.runtime.project_intelligence.summary import project_intro as _project_intro
from odylith.runtime.project_intelligence.utils import (
    dict_value as _dict,
    humanize as _humanize,
    list_value as _list,
    sentence as _sentence,
    short as _short,
    strings as _strings,
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _repo_name(repo_root: Path, shell_payload: Mapping[str, Any]) -> str:
    name = str(shell_payload.get("shell_repo_name", "")).strip()
    return name or Path(repo_root).resolve().name


def _load_components(repo_root: Path) -> list[dict[str, Any]]:
    payload = _read_json(repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json")
    return [dict(row) for row in _list(payload.get("components")) if isinstance(row, Mapping)]


def _component_by_id(components: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for component in components:
        component_id = str(component.get("component_id", "")).strip()
        if component_id:
            index[component_id] = dict(component)
    return index


def _component(component_index: Mapping[str, Mapping[str, Any]], component_id: str) -> dict[str, Any]:
    return dict(component_index.get(component_id, {}))


def _component_name(component: Mapping[str, Any], fallback: str) -> str:
    return _sentence(component.get("name"), fallback)


def _component_summary(component: Mapping[str, Any], fallback: str) -> str:
    return _short(component.get("what_it_is") or component.get("why_tracked"), limit=150, fallback=fallback)


def _parse_markdown_tables(path: Path) -> dict[str, list[dict[str, str]]]:
    if not path.is_file():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    sections: dict[str, list[dict[str, str]]] = {}
    section = ""
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("## "):
            section = line.removeprefix("## ").strip()
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|"):
            headers = [_clean_table_cell(cell) for cell in line.strip("|").split("|")]
            separator = lines[index + 1].strip()
            if not all(set(cell.strip()) <= {"-", ":", " "} for cell in separator.strip("|").split("|")):
                index += 1
                continue
            rows: list[dict[str, str]] = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                values = [_clean_table_cell(cell) for cell in lines[index].strip().strip("|").split("|")]
                row = {
                    header: values[position] if position < len(values) else ""
                    for position, header in enumerate(headers)
                    if header
                }
                if any(row.values()):
                    rows.append(row)
                index += 1
            sections.setdefault(section or "Table", []).extend(rows)
            continue
        index += 1
    return sections


def _clean_table_cell(value: str) -> str:
    token = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(value or "").strip())
    token = token.replace("`", "")
    return " ".join(token.split())


def _backlog_snapshot(repo_root: Path) -> dict[str, Any]:
    sections = _parse_markdown_tables(repo_root / "odylith" / "radar" / "source" / "INDEX.md")
    active = sections.get("Ranked Active Backlog", [])
    execution = sections.get("In Planning/Implementation (Linked to odylith/technical-plans/in-progress or an active parent wave)", [])
    if not execution:
        execution = next((rows for name, rows in sections.items() if name.startswith("In Planning/Implementation")), [])
    finished = next((rows for name, rows in sections.items() if name.startswith("Finished")), [])
    return {
        "queued": active,
        "execution": execution,
        "finished": finished,
        "queued_count": len(active),
        "execution_count": len(execution),
        "finished_count": len(finished),
    }


def _plan_snapshot(repo_root: Path) -> dict[str, Any]:
    sections = _parse_markdown_tables(repo_root / "odylith" / "technical-plans" / "INDEX.md")
    active = sections.get("Active Plans", [])
    parked = sections.get("Parked Plans", [])
    completed = [
        row
        for name, rows in sections.items()
        if name.startswith("Recently Completed")
        for row in rows
    ]
    return {
        "active": active,
        "parked": parked,
        "completed_recent": completed,
        "active_count": len(active),
        "parked_count": len(parked),
        "completed_recent_count": len(completed),
    }


def _casebook_snapshot(repo_root: Path, compass: Mapping[str, Any]) -> dict[str, Any]:
    risks = _dict(compass.get("risks"))
    risk_bugs = [dict(row) for row in _list(risks.get("bugs")) if isinstance(row, Mapping)]
    if risk_bugs:
        bugs = risk_bugs
    else:
        sections = _parse_markdown_tables(repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md")
        bugs = [dict(row) for row in sections.get("Open Bugs", [])]
    open_bugs = [
        bug
        for bug in bugs
        if str(bug.get("status", bug.get("Status", ""))).strip().lower() == "open"
    ]
    critical = [
        bug
        for bug in bugs
        if str(bug.get("is_open_critical", "")).lower() == "true"
        or (
            str(bug.get("Severity", bug.get("severity", ""))).strip().upper() in {"P0", "P1"}
            and str(bug.get("Status", bug.get("status", ""))).strip().lower() == "open"
        )
    ]
    return {
        "bugs": bugs,
        "open": open_bugs,
        "critical": critical,
        "open_count": len(open_bugs),
        "critical_count": len(critical),
    }


def _atlas_snapshot(repo_root: Path) -> dict[str, Any]:
    payload = _read_json(repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json")
    diagrams = [dict(row) for row in _list(payload.get("diagrams")) if isinstance(row, Mapping)]
    active = [row for row in diagrams if str(row.get("status", "")).strip().lower() == "active"]
    return {
        "diagrams": diagrams,
        "active": active,
        "active_count": len(active),
    }


def _compass_snapshot(repo_root: Path) -> dict[str, Any]:
    return _read_json(repo_root / "odylith" / "compass" / "runtime" / "current.v1.json")



def _evidence_state(*, components: Sequence[Mapping[str, Any]], backlog: Mapping[str, Any], compass: Mapping[str, Any], atlas: Mapping[str, Any], casebook: Mapping[str, Any]) -> str:
    score = 0
    score += 1 if components else 0
    score += 1 if int(backlog.get("execution_count", 0) or 0) or int(backlog.get("queued_count", 0) or 0) else 0
    score += 1 if compass else 0
    score += 1 if int(atlas.get("active_count", 0) or 0) else 0
    score += 1 if int(casebook.get("open_count", 0) or 0) else 0
    if score >= 4:
        return "Source-backed runtime"
    if score >= 2:
        return "Source-backed"
    return "Inferred"


def _origin_label(self_host: Mapping[str, Any]) -> str:
    repo_role = str(self_host.get("repo_role", "")).strip()
    posture = str(self_host.get("posture", "")).strip()
    if repo_role == "product_repo":
        if posture == "detached_source_local":
            return "source-local"
        return "product repo"
    if repo_role:
        return _humanize(repo_role)
    return "Existing repo"


def _complexity_label(*, components: Sequence[Mapping[str, Any]], backlog: Mapping[str, Any], casebook: Mapping[str, Any]) -> str:
    total = len(components) + int(backlog.get("execution_count", 0) or 0) + int(casebook.get("critical_count", 0) or 0)
    if total >= 35:
        return "High complexity"
    if total >= 10:
        return "Medium complexity"
    return "Low complexity"


def _current_release(compass: Mapping[str, Any]) -> dict[str, Any]:
    release_summary = _dict(compass.get("release_summary"))
    return _dict(release_summary.get("current_release"))


def _execution_focus(compass: Mapping[str, Any]) -> dict[str, Any]:
    focus = _dict(compass.get("execution_focus"))
    return _dict(focus.get("global"))


def _next_actions(compass: Mapping[str, Any], backlog: Mapping[str, Any]) -> list[dict[str, Any]]:
    actions = [dict(row) for row in _list(compass.get("next_actions")) if isinstance(row, Mapping)]
    if actions:
        return actions
    return [
        {
            "idea_id": row.get("idea_id", ""),
            "title": row.get("title", ""),
            "action": f"Advance {row.get('title', 'the selected workstream')}",
            "source": "radar",
        }
        for row in list(backlog.get("execution", []))[:3]
        if isinstance(row, Mapping)
    ]


def _release_label(release: Mapping[str, Any]) -> str:
    version = str(release.get("display_label") or release.get("version") or "").strip()
    name = str(release.get("effective_name") or release.get("inherited_name") or "").strip()
    if version and name and version != name:
        return f"{version}: {name}"
    return version or name or "No active release detected"


def _status_count_label(count: int, noun: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{count} {noun}{suffix}"


def _project_jobs(
    *,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    release_label: str,
    next_title: str,
    next_action_text: str,
    blockers: Sequence[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    rows_by_id = _backlog_rows_by_id(backlog)
    jobs: list[tuple[str, str, str]] = []
    seen_titles: set[str] = set()

    def add(title: object, body: object, status: str) -> None:
        clean_title = _short(title, limit=78)
        clean_body = _short(body, limit=145)
        if not clean_title or clean_title.lower() in seen_titles:
            return
        seen_titles.add(clean_title.lower())
        jobs.append((clean_title, clean_body, status))

    for workstream_id in active_workstreams[:4]:
        row = rows_by_id.get(str(workstream_id).strip(), {})
        title = row.get("title") or workstream_id
        priority = _sentence(row.get("priority"), "active")
        status = _sentence(row.get("status"), "implementation")
        add(title, f"{workstream_id} is {status} in {release_label}; priority {priority}.", "Current release")

    add(next_title, _short(next_action_text, limit=145), "Next action")

    for title, detail, owner in blockers[:2]:
        if "evidence gap" in str(title).lower():
            continue
        add(f"Resolve {title}", f"{detail}. Source: {owner}.", "Open risk")

    return jobs[:6]


def _boundary_included(
    *,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    current_focus: str,
    next_title: str,
    next_action_text: str,
    release_label: str,
) -> list[str]:
    rows_by_id = _backlog_rows_by_id(backlog)
    included: list[str] = []
    for workstream_id in active_workstreams[:4]:
        row = rows_by_id.get(str(workstream_id).strip(), {})
        title = _sentence(row.get("title"), workstream_id)
        included.append(f"{workstream_id}: {title}")
    included.append(f"Focus: {_concise_text(current_focus, limit=135)}")
    included.append(f"Next: {_concise_text(next_title, limit=80)}")
    included.append(f"Release: {_short(release_label, limit=80)}")
    included.append(f"Recommended action: {_concise_text(next_action_text, limit=135)}")
    deduped: list[str] = []
    seen: set[str] = set()
    for item in included:
        if not item.strip() or item.lower() in seen:
            continue
        seen.add(item.lower())
        deduped.append(item)
    return deduped[:6] or ["No current source-backed work slice found."]


def _boundary_unresolved(*, graph: Mapping[str, Any], blockers: Sequence[tuple[str, str, str]]) -> list[str]:
    degraded = [
        str(item).strip()
        for item in _list(graph.get("degraded_state"))
        if str(item or "").strip()
        and "No degraded source condition" not in str(item)
    ]
    contradictions = [
        str(item).strip()
        for item in _list(graph.get("contradictions"))
        if str(item or "").strip()
        and "No cross-surface contradiction" not in str(item)
    ]
    unresolved = degraded + contradictions
    unresolved.extend(f"{title}: {detail}" for title, detail, _owner in blockers if str(title or "").strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for item in unresolved:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:6] or ["No unresolved boundary item found in current source records."]


def _known_claims(claim_evidence: Sequence[Mapping[str, Any]]) -> list[str]:
    known: list[str] = []
    for row in claim_evidence:
        if not isinstance(row, Mapping):
            continue
        evidence = str(row.get("evidence", "")).strip().lower()
        if evidence in {"inferred", "stale"}:
            continue
        claim = _claim_label(row.get("claim"))
        value = _concise_text(row.get("value"), limit=135)
        if value:
            known.append(f"{claim}: {value} ({evidence}).")
    return known[:5] or ["No current source-backed claim is strong enough to summarize."]


def _claim_label(value: object) -> str:
    labels = {
        "current focus": "Focus",
        "current release": "Release",
        "next action": "Next",
        "project explanation": "Project",
        "project identity": "Identity",
        "risk posture": "Risk",
        "topology evidence": "Topology",
        "implementation plan": "Plan",
    }
    token = _sentence(value, "Claim")
    return labels.get(token.lower(), token)


def _unproven_claims(
    *,
    claim_evidence: Sequence[Mapping[str, Any]],
    contradictions: Sequence[str],
    blockers: Sequence[tuple[str, str, str]],
    degraded_state: Sequence[str],
) -> list[str]:
    unproven = [
        f"{_claim_label(row.get('claim'))}: {_concise_text(row.get('value'), limit=120)} ({row.get('evidence')})."
        for row in claim_evidence
        if isinstance(row, Mapping) and str(row.get("evidence", "")).strip().lower() in {"inferred", "stale"}
    ]
    unproven.extend(item for item in contradictions if "No cross-surface contradiction" not in str(item))
    unproven.extend(item for item in degraded_state if "No degraded source condition" not in str(item))
    unproven.extend(title for title, _detail, _owner in blockers if str(title or "").strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for item in unproven:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(str(item).strip())
    return deduped[:5] or ["No unresolved claim surfaced in the current projection."]


def _has_uncertain_claims(claim_evidence: Sequence[Mapping[str, Any]]) -> bool:
    uncertain = {"inferred", "needs validation", "contradicted"}
    return any(str(row.get("evidence", "")).strip().lower() in uncertain for row in claim_evidence if isinstance(row, Mapping))


def _has_meaningful_items(items: Sequence[str], *, empty_prefix: str) -> bool:
    return any(str(item or "").strip() and not str(item).strip().startswith(empty_prefix) for item in items)


def _has_material_posture(risk_classes: Sequence[Mapping[str, Any]], validation_posture: Sequence[Mapping[str, Any]]) -> bool:
    risk_tokens = {
        "safety",
        "money",
        "capital",
        "credit",
        "compliance",
        "security",
        "privacy",
        "customer",
        "patient",
        "regulatory",
        "data loss",
        "rollback",
        "operational",
        "autonomy",
    }
    risk_text = " ".join(
        f"{row.get('risk', '')} {row.get('meaning', '')}".lower()
        for row in risk_classes
        if isinstance(row, Mapping)
    )
    if any(token in risk_text for token in risk_tokens):
        return True
    return any(
        str(row.get("level", "")).strip().lower() in {"low", "blocked", "missing"}
        for row in validation_posture
        if isinstance(row, Mapping)
    )


def _visible_sections(
    *,
    origin: str,
    actors: Sequence[tuple[str, str, str]],
    jobs: Sequence[tuple[str, str, str]],
    claim_evidence: Sequence[Mapping[str, Any]],
    delta: Sequence[str],
    contradictions: Sequence[str],
    degraded_state: Sequence[str],
    risk_classes: Sequence[Mapping[str, Any]],
    validation_posture: Sequence[Mapping[str, Any]],
    included: Sequence[str],
    excluded: Sequence[str],
) -> list[str]:
    sections = ["scenario"]
    if actors:
        sections.append("participants")
    if jobs:
        sections.append("jobs")
    if "greenfield" in origin.lower() or _has_uncertain_claims(claim_evidence):
        sections.append("claim_evidence")
    if (
        _has_meaningful_items(contradictions, empty_prefix="No cross-surface contradiction")
        or _has_meaningful_items(degraded_state, empty_prefix="No degraded source condition")
    ):
        sections.append("trust")
    if _has_material_posture(risk_classes, validation_posture):
        sections.append("posture")
    if included or excluded:
        sections.append("boundary")
    sections.extend(["state", "next", "proof"])
    return sections


def build_project_intelligence_payload(
    *,
    repo_root: Path,
    shell_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile the dashboard Project tab from current repo truth."""

    root = Path(repo_root).resolve()
    shell = dict(shell_payload or {})
    greenfield_proposal = proposal_from_sources(repo_root=root, shell_payload=shell)
    if greenfield_proposal:
        return build_greenfield_payload(proposal=greenfield_proposal, repo_root=root)
    components = _load_components(root)
    component_index = _component_by_id(components)
    repo = _repo_name(root, shell)
    root_component = _component(component_index, "odylith") or (dict(components[0]) if components else {})
    compass = _compass_snapshot(root)
    backlog = _backlog_snapshot(root)
    plans = _plan_snapshot(root)
    atlas = _atlas_snapshot(root)
    casebook = _casebook_snapshot(root, compass)
    self_host = _dict(shell.get("self_host"))
    live_refresh = _dict(shell.get("live_refresh"))
    worktree = _dict(live_refresh.get("worktree"))
    focus = _execution_focus(compass)
    release = _current_release(compass)
    actions = _next_actions(compass, backlog)
    next_action = actions[0] if actions else {}
    active_workstreams = _strings(release.get("active_workstreams")) or _strings(focus.get("workstreams"))
    critical_bugs = [dict(row) for row in casebook.get("critical", []) if isinstance(row, Mapping)]
    open_bugs = [dict(row) for row in casebook.get("open", []) if isinstance(row, Mapping)]
    project_title = _sentence(root_component.get("name"), _humanize(repo, "Project"))
    repo_role = _sentence(self_host.get("repo_role"), "repo")
    project_intro = _project_intro(
        project_title=project_title,
        root_component=root_component,
        components=components,
        repo_role=repo_role,
    )
    release_label = _release_label(release)
    current_focus = _project_focus_text(
        focus.get("headline"),
        active_workstreams=active_workstreams,
        backlog=backlog,
        release_label=release_label,
        fallback=f"{_status_count_label(int(backlog.get('execution_count', 0) or 0), 'implementation workstream')} and {_status_count_label(int(plans.get('active_count', 0) or 0), 'active plan')} are recorded.",
    )
    next_action_text = _concise_text(next_action.get("action"), limit=145, fallback="Create or accept project truth before implementation starts.")
    next_title = _concise_text(next_action.get("title"), limit=90, fallback="Create or accept project truth")
    primary_lens = _primary_lens(root_component, components=components, fallback=_humanize(repo, "Project"))
    origin = _origin_label(self_host)
    evidence = _evidence_state(components=components, backlog=backlog, compass=compass, atlas=atlas, casebook=casebook)
    complexity = _complexity_label(components=components, backlog=backlog, casebook=casebook)
    evidence_sources = [
        "Registry" if components else "",
        "Radar" if int(backlog.get("queued_count", 0) or 0) or int(backlog.get("execution_count", 0) or 0) else "",
        "Compass" if compass else "",
        "Atlas" if int(atlas.get("active_count", 0) or 0) else "",
        "Casebook" if int(casebook.get("open_count", 0) or 0) else "",
    ]
    evidence_sources = [source for source in evidence_sources if source]
    current_state = (
        f"{current_focus}. Current release: {release_label}. "
        f"Worktree: {_sentence(worktree.get('status'), 'unknown')} with "
        f"{worktree.get('meaningful_changed_count', 0) or 0} meaningful and "
        f"{worktree.get('generated_changed_count', 0) or 0} generated changed paths."
    )
    desired_state = (
        f"The Project page explains {project_title} from "
        f"{', '.join(evidence_sources) or 'available repo evidence'} before users open expert records."
    )
    blockers = [
        (
            _sentence(bug.get("title") or bug.get("Title"), "Open bug"),
            f"{_sentence(bug.get('severity') or bug.get('Severity'), 'P?')} · {_sentence(bug.get('status') or bug.get('Status'), 'Open')}",
            _sentence(bug.get("components") or bug.get("Components"), "casebook"),
        )
        for bug in critical_bugs[:4]
    ]
    if not blockers and open_bugs:
        blockers = [
            (
                _sentence(bug.get("title") or bug.get("Title"), "Open bug"),
                f"{_sentence(bug.get('severity') or bug.get('Severity'), 'P?')} · {_sentence(bug.get('status') or bug.get('Status'), 'Open')}",
                _sentence(bug.get("components") or bug.get("Components"), "casebook"),
            )
            for bug in open_bugs[:4]
        ]
    if not blockers:
        blockers = [("Evidence gap", "No open Casebook blocker was found in the current projection.", "casebook")]
    graph = build_governance_graph_projection(
        repo_root=root,
        components=components,
        backlog=backlog,
        plans=plans,
        atlas=atlas,
        casebook=casebook,
        compass=compass,
        focus=focus,
        release=release,
        actions=actions,
        worktree=worktree,
        evidence=evidence,
        evidence_sources=evidence_sources,
        blockers=blockers,
        project_title=project_title,
        project_intro=project_intro,
        current_focus=current_focus,
        release_label=release_label,
        next_action_text=next_action_text,
        next_action=next_action,
    )
    graph["projection"]["origin"] = origin
    maturity = str(graph.get("maturity", "Unknown"))
    work_mode = str(graph.get("work_mode", "Unknown"))
    refreshed_at = str(graph.get("refreshed_at", "not recorded"))
    confidence = "High" if evidence == "Source-backed runtime" and not critical_bugs else "Medium" if evidence != "Inferred" else "Low"
    section_copy = _section_narration(
        project_title=project_title,
        release_label=release_label,
        work_mode=work_mode,
        maturity=maturity,
        evidence_sources=evidence_sources,
        active_workstream_count=len(active_workstreams),
        action_count=len(actions),
        critical_count=int(casebook.get("critical_count", 0) or 0),
    )
    claim_evidence = [dict(row) for row in _list(graph.get("claim_evidence")) if isinstance(row, Mapping)]
    contradictions = [str(item).strip() for item in _list(graph.get("contradictions")) if str(item or "").strip()]
    degraded_state = [str(item).strip() for item in _list(graph.get("degraded_state")) if str(item or "").strip()]
    actors = _source_persona_cards(
        audience_emphasis=graph.get("audience_emphasis", []),
        repo_role=repo_role,
        work_mode=work_mode,
        evidence_sources=evidence_sources,
        critical_count=int(casebook.get("critical_count", 0) or 0),
    )
    jobs = _project_jobs(
        active_workstreams=active_workstreams,
        backlog=backlog,
        release_label=release_label,
        next_title=next_title,
        next_action_text=next_action_text,
        blockers=blockers,
    )
    included = _boundary_included(
        active_workstreams=active_workstreams,
        backlog=backlog,
        current_focus=current_focus,
        next_title=next_title,
        next_action_text=next_action_text,
        release_label=release_label,
    )
    excluded = _boundary_unresolved(graph=graph, blockers=blockers)
    return {
        "eyebrow": f"Project type: {primary_lens}",
        "title": project_title,
        "intro": project_intro,
        "chips": [
            primary_lens,
            evidence,
            complexity,
        ],
        "focus_label": f"Current {project_title} focus",
        "focus": current_focus,
        "open_label": f"Open {project_title} risks",
        "open": [row[0] for row in blockers[:4]],
        "answers": _source_answer_cards(
            project_title=project_title,
            repo_role=repo_role,
            root_component=root_component,
            components=components,
            current_focus=current_focus,
            next_title=next_title,
            next_action_text=next_action_text,
            critical_count=int(casebook.get("critical_count", 0) or 0),
            blockers=blockers,
            evidence_sources=evidence_sources,
        ),
        "scenario": _scenario(
            project_title=project_title,
            release_label=release_label,
            work_mode=work_mode,
            current_focus=current_focus,
            next_title=next_title,
            next_action_text=next_action_text,
            critical_count=int(casebook.get("critical_count", 0) or 0),
            evidence_sources=evidence_sources,
            active_workstream_count=len(active_workstreams),
            action_count=len(actions),
        ),
        "scenario_details": _scenario_details(
            current_focus=current_focus,
            next_action_text=next_action_text,
            critical_count=int(casebook.get("critical_count", 0) or 0),
            evidence_sources=evidence_sources,
        ),
        "actors": actors,
        "participants": actors,
        "participants_title": f"Who participates in {project_title}?",
        "participants_note": "People who decide, change, and review the current work.",
        "jobs": jobs,
        "jobs_title": f"What is active for {release_label}?",
        "jobs_note": f"Generated from {len(active_workstreams)} release workstreams, {len(actions)} runtime actions, and {casebook.get('critical_count', 0)} critical blockers.",
        "boundary_title": f"What is inside the current {work_mode.lower()} boundary?",
        "boundary_note": "Boundary rows describe the active work slice, not the whole artifact inventory.",
        "included_label": "In current slice",
        "excluded_label": "Outside or unresolved",
        "included": included,
        "excluded": excluded,
        "current": current_state,
        "desired": desired_state,
        "question": f"What should happen next for {release_label}?",
        "recommendation": next_action_text,
        "options": [
            ("A", _sentence(action.get("title"), f"Action {index + 1}"), _sentence(action.get("action"), "Advance this source-backed action."))
            for index, action in enumerate(actions[:3])
        ]
        or [("A", "Create or accept project truth", "Draft a greenfield proposal or refresh source-backed project records.")],
        "next": [
            next_title,
            next_action_text,
            _sentence(next_action.get("idea_id"), "Project"),
            _sentence(next_action.get("source"), "Source-backed dashboard update"),
            "Current source records are present",
            blockers[0][0] if blockers else "Project claims drift from evidence",
        ],
        "projection": graph.get("projection", {}),
        "claim_evidence": claim_evidence,
        "artifact_coverage": graph.get("artifact_coverage", []),
        "topology_spine": graph.get("topology_spine", []),
        "contradictions": contradictions,
        "delta": graph.get("delta", []),
        "risk_classes": graph.get("risk_classes", []),
        "validation_posture": graph.get("validation_posture", []),
        "audience_emphasis": graph.get("audience_emphasis", []),
        "degraded_state": degraded_state,
        "known": _known_claims(claim_evidence),
        "unknown": _unproven_claims(
            claim_evidence=claim_evidence,
            contradictions=contradictions,
            blockers=blockers,
            degraded_state=degraded_state,
        ),
        "confidence": confidence,
        "blockers": blockers,
        "sections": _visible_sections(
            origin=origin,
            actors=actors,
            jobs=jobs,
            claim_evidence=claim_evidence,
            delta=[str(item).strip() for item in _list(graph.get("delta")) if str(item or "").strip()],
            contradictions=contradictions,
            degraded_state=degraded_state,
            risk_classes=[dict(row) for row in _list(graph.get("risk_classes")) if isinstance(row, Mapping)],
            validation_posture=[dict(row) for row in _list(graph.get("validation_posture")) if isinstance(row, Mapping)],
            included=included,
            excluded=excluded,
        ),
        **section_copy,
        **_table_columns(),
        "sources": {
            "registry": "odylith/registry/source/component_registry.v1.json",
            "radar": "odylith/radar/source/INDEX.md",
            "plans": "odylith/technical-plans/INDEX.md",
            "casebook": "odylith/casebook/bugs/INDEX.md",
            "atlas": "odylith/atlas/source/catalog/diagrams.v1.json",
            "compass": "odylith/compass/runtime/current.v1.json",
        },
    }
