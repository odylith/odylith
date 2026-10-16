"""Compiled traceability helpers for greenfield commit-only writes."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_traceability


def compiled_traceability_plan(
    raw_plan: Any,
    *,
    required: bool = True,
) -> greenfield_traceability.GreenfieldTraceabilityPlan | None:
    """Return a precompiled traceability plan without rebuilding product topology."""

    if isinstance(raw_plan, greenfield_traceability.GreenfieldTraceabilityPlan):
        plan = raw_plan
    elif isinstance(raw_plan, Mapping):
        plan = greenfield_traceability.traceability_plan_from_payload(raw_plan)
    else:
        plan = None
    if plan is not None and plan.workstreams:
        return plan
    if plan is not None and not required:
        return plan
    if required:
        raise ValueError(
            "compiled greenfield package is incomplete; rebuild the ProductCreateTransaction before commit: "
            "missing compiled traceability_plan"
        )
    return None


def compiled_traceability_diagram_issues(
    *,
    traceability_plan: greenfield_traceability.GreenfieldTraceabilityPlan,
    diagram_ids: Sequence[str],
) -> list[str]:
    """Return issues for compiled Atlas links that lost backlog topology."""

    links_by_id = {str(link.diagram_id).strip(): link for link in traceability_plan.diagram_links}
    missing_links = [diagram_id for diagram_id in diagram_ids if diagram_id and diagram_id not in links_by_id]
    issues: list[str] = []
    if missing_links:
        issues.append("missing compiled traceability diagram links")
    unlinked = [
        diagram_id
        for diagram_id in diagram_ids
        if diagram_id in links_by_id
        and (
            not links_by_id[diagram_id].related_workstream_ids
            or not links_by_id[diagram_id].related_backlog_paths
        )
    ]
    if unlinked:
        issues.append("compiled traceability diagram links missing backlog/workstream references")
    return issues


def rebase_compiled_traceability_plan(
    plan: greenfield_traceability.GreenfieldTraceabilityPlan,
    *,
    backlog_result: Mapping[str, Any],
) -> greenfield_traceability.GreenfieldTraceabilityPlan:
    """Point compiled links at final backlog paths instead of the dry-run root."""

    paths_by_id = {
        str(row.get("idea_id", "")).strip().upper(): str(row.get("idea_path", "")).strip()
        for row in _mapping_rows(backlog_result.get("created"))
        if str(row.get("idea_id", "")).strip() and str(row.get("idea_path", "")).strip()
    }
    if not paths_by_id:
        return plan
    return replace(
        plan,
        workstreams=tuple(
            replace(workstream, path=Path(paths_by_id.get(workstream.idea_id, str(workstream.path))))
            for workstream in plan.workstreams
        ),
        diagram_links=tuple(_rebased_diagram_link(link, paths_by_id=paths_by_id) for link in plan.diagram_links),
    )


def _rebased_diagram_link(
    link: greenfield_traceability.DiagramLink,
    *,
    paths_by_id: Mapping[str, str],
) -> greenfield_traceability.DiagramLink:
    paths = [paths_by_id[idea_id] for idea_id in link.related_workstream_ids if idea_id in paths_by_id]
    return replace(link, related_backlog_paths=tuple(paths) if paths else link.related_backlog_paths)


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    rows = value if isinstance(value, list | tuple) else ()
    return tuple(row for row in rows if isinstance(row, Mapping))
