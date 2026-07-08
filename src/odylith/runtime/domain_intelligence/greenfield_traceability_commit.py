"""Compiled traceability helpers for greenfield commit-only writes."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
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
