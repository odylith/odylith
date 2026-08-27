"""Project first-release operator handoff from typed v7 proposal bindings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    SEMANTIC_SYSTEM_POLICY_CUSTODY,
    semantic_evidence_tier,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_traceability import (
    require_persisted_semantic_projection_plan,
    semantic_projection_workstream_rows,
)


def semantic_first_release_workstream_ids(
    *, proposal: Mapping[str, Any], created_backlog: Sequence[Mapping[str, Any]]
) -> list[str]:
    """Resolve release workstreams by exact graph-projected titles."""

    plan = require_persisted_semantic_projection_plan(proposal)
    semantic_projection_workstream_rows(proposal)
    created = [row for row in created_backlog if isinstance(row, Mapping)]
    if not created:
        return []
    by_title: dict[str, str] = {}
    for row in created:
        title = str(row.get("title") or "").strip()
        idea_id = str(row.get("idea_id") or "").strip().upper()
        if not title or not idea_id or title in by_title:
            raise ValueError("verified semantic release lacks unique created Radar bindings")
        by_title[title] = idea_id
    planned = mapping_rows(plan.get("workstreams"))
    if len(by_title) != len(planned):
        raise ValueError("verified semantic release workstream depth drifted from its plan")
    selected: list[str] = []
    for workstream in planned:
        title = _required_text(workstream, "title")
        idea_id = by_title.get(title, "")
        if not idea_id:
            raise ValueError(
                f"verified semantic release target `{title}` lacks an exact Radar binding"
            )
        selected.append(idea_id)
    return selected


def semantic_next_steps(
    *,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    first_release_workstreams: Sequence[str],
    release_selector: str,
) -> dict[str, Any]:
    """Render an operator handoff without reparsing accepted first-path prose."""

    created = mapping_rows(backlog_result.get("created"))
    by_id = {
        str(row.get("idea_id") or "").strip().upper(): row
        for row in created
        if str(row.get("idea_id") or "").strip()
    }
    plan = require_persisted_semantic_projection_plan(proposal)
    semantic_projection_workstream_rows(proposal)
    workstream_plans = mapping_rows(plan.get("workstreams"))
    product_plans = tuple(row for row in workstream_plans if row.get("kind") == "product")
    if len(product_plans) != 1:
        raise ValueError("verified semantic operator handoff lacks one planned product workstream")
    project_title_ref = _required_text(product_plans[0], "title")
    start_plan = _start_workstream_plan(plan)
    start_title_ref = _required_text(start_plan, "title")
    ids_by_title = {
        str(row.get("title") or "").strip(): idea_id
        for idea_id, row in by_id.items()
    }
    project_id = ids_by_title.get(project_title_ref, "")
    start_id = ids_by_title.get(start_title_ref, "")
    release_ids = tuple(
        str(value).strip().upper()
        for value in first_release_workstreams
        if str(value).strip()
    )
    expected_release_ids = tuple(
        semantic_first_release_workstream_ids(
            proposal=proposal,
            created_backlog=created,
        )
    )
    if release_ids != expected_release_ids:
        raise ValueError("verified semantic operator handoff drifted from typed release membership")
    if not start_id or start_id not in by_id:
        raise ValueError("verified semantic operator handoff lacks an exact start workstream")
    start = by_id[start_id]
    project = by_id.get(project_id, start)
    title = str(start.get("title") or "").strip()
    project_title = str(project.get("title") or "").strip()
    node_by_id = {
        _required_text(row, "fact_id"): row
        for row in mapping_rows(plan.get("nodes"))
    }
    axes = plan.get("axes")
    if not isinstance(axes, Mapping):
        raise ValueError("verified semantic operator handoff lacks typed projection axes")
    workflow_ids = _strings(axes.get("workflow_step_fact_ids"))
    state_ids = _strings(axes.get("state_fact_ids"))
    output_ids = _strings(axes.get("visible_output_fact_ids"))
    workflow_labels = _labels(node_by_id, workflow_ids)
    state_labels = _labels(node_by_id, state_ids)
    output_labels = _labels(node_by_id, output_ids)
    if not workflow_labels or not output_labels:
        raise ValueError("verified semantic operator handoff lacks workflow or visible outputs")
    topology_prompt = (
        f"Implement workflow facts {_quoted(workflow_ids)}. "
        f"Make every accepted visible output available: {_plain(output_labels)}."
    )
    state_prompt = (
        f" Preserve state objects: {_plain(state_labels)}. Prove their typed transitions."
        if state_labels
        else " Preserve the explicit stateless boundary; do not introduce durable state."
    )
    validation_gates = [
        f"Verify every visible output relation for {_plain(output_labels)}.",
        "Verify every component and dependency binding against the persisted projection plan.",
        "Reject any package whose authority or repository write-set hash changes.",
    ]
    if state_labels:
        validation_gates.insert(
            1,
            f"Reconstruct every state object and transition for {_plain(state_labels)}.",
        )
    single_workstream = project_id == start_id
    project_first_prompt = (
        f"Begin `{start_id}` {title} after its graph proof is accepted."
        if single_workstream
        else (
            f"Review `{project_id}` {project_title}, then open `{start_id}` {title} "
            "only after its graph proof is accepted."
        )
    )
    release_review_step = (
        f"Compare `{start_id}` with its component and proof links for release `{release_selector}`."
        if single_workstream
        else (
            f"Open `{start_id}` and compare its component and proof links with "
            f"release `{release_selector}`."
        )
    )
    return {
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        "project_workstream_id": project_id,
        "project_workstream_title": project_title,
        "start_workstream_id": start_id,
        "start_workstream_title": title,
        "release_selector": str(release_selector).strip(),
        "project_first_prompt": project_first_prompt,
        "implementation_prompt": (
            f"Start `{start_id}` {title}. {topology_prompt}{state_prompt} "
            "Do not change the sealed fact, relation, component, diagram, or workstream topology."
        ),
        "customization_options": [],
        "coding_readiness_gates": [
            "The source-cited Semantic Intent graph passes structural and citation validation.",
            f"All {len(mapping_rows(plan.get('components')))} Registry components match the persisted projection plan.",
            f"All {len(mapping_rows(plan.get('diagrams')))} Atlas diagrams match the persisted projection plan.",
            "The pre-confirm package passes quality, provenance, and transaction-integrity gates.",
        ],
        "validation_gates": validation_gates,
        "operator_sequence": [
            "Review the accepted project brief and source-cited Semantic Intent graph.",
            release_review_step,
            "Resolve any graph contradiction before authoring a technical plan or changing source.",
            f"After the gates pass, author the first technical plan for `{start_id}`.",
        ],
        "verification_commands": [
            f"./.odylith/bin/odylith context --repo-root . {start_id}",
            "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
            "./.odylith/bin/odylith validate plan-traceability --repo-root .",
        ],
    }


def _start_workstream_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    workstreams = mapping_rows(plan.get("workstreams"))
    product = next((row for row in workstreams if row.get("kind") == "product"), None)
    if product is None:
        raise ValueError("persisted semantic projection plan lacks a product workstream")
    if len(workstreams) == 1:
        return product
    component_id = _required_text(plan, "start_component_id")
    result_owner = next(
        (
            row
            for row in mapping_rows(plan.get("components"))
            if row.get("component_id") == component_id
            and row.get("component_role") == "result_implementing"
        ),
        None,
    )
    if result_owner is None:
        raise ValueError("persisted semantic projection plan has an invalid start component")
    matches = tuple(
        row
        for row in workstreams
        if row.get("kind") == "component"
        and _strings(row.get("component_ids")) == (component_id,)
    )
    if len(matches) != 1:
        raise ValueError("persisted semantic projection plan lacks one start workstream")
    return matches[0]


def _labels(
    nodes: Mapping[str, Mapping[str, Any]],
    fact_ids: Sequence[str],
) -> tuple[str, ...]:
    return tuple(_required_text(nodes[fact_id], "label") for fact_id in fact_ids)


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise ValueError(f"verified semantic delivery lacks `{key}`")
    return value


def _quoted(values: Sequence[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def _plain(values: Sequence[str]) -> str:
    return ", ".join(
        str(value).strip().rstrip(" .!?")
        for value in values
        if str(value).strip().rstrip(" .!?")
    )


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(row).strip() for row in value if str(row).strip())


__all__ = ["semantic_first_release_workstream_ids", "semantic_next_steps"]
