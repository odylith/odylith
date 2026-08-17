"""Render accepted v7 memory directly from typed graph projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_acceptance_contract import (
    PROJECT_BRIEF_SOURCE_PATH,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    SEMANTIC_SYSTEM_POLICY_CUSTODY,
    semantic_evidence_tier,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_traceability import (
    require_persisted_semantic_projection_plan,
    semantic_projection_component_rows,
    semantic_projection_diagram_rows,
    semantic_projection_workstream_rows,
)


SEMANTIC_PROJECT_DASHBOARD_VERSION = "odylith.greenfield.semantic-project-dashboard.v1"


def semantic_acceptance_event_preview(
    *,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    accepted_at: str = "prewrite",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Build Compass evidence from exact governed artifact identifiers."""

    plan = require_persisted_semantic_projection_plan(proposal)
    workstream_rows = semantic_projection_workstream_rows(proposal)
    component_rows = semantic_projection_component_rows(proposal)
    semantic_projection_diagram_rows(proposal)
    backlog_items = _ordered_rows(
        backlog_items,
        key="title",
        expected=tuple(_required_text(row, "title") for row in workstream_rows),
        label="accepted Radar workstream",
    )
    component_items = _ordered_rows(
        component_items,
        key="component_id",
        expected=tuple(_required_text(row, "component_id") for row in component_rows),
        label="accepted Registry component",
    )
    diagram_ids = _exact_diagram_ids(plan, diagram_ids)
    workstreams = _values(backlog_items, "idea_id", upper=True)
    components = _values(component_items, "component_id")
    artifacts = _dedupe(
        (
            PROJECT_BRIEF_SOURCE_PATH,
            *(_portable(row.get("idea_path"), repo_root=repo_root) for row in backlog_items),
            *(_portable(row.get("spec_path"), repo_root=repo_root) for row in component_items),
        )
    )
    title = _identity_label(plan)
    release = _release_label(release_selector, release_id)
    return {
        "version": "v1",
        "kind": "decision",
        "summary": (
            f"Accepted graph-native project {title}: {len(workstreams)} workstreams, "
            f"{len(components)} components, {len(tuple(diagram_ids))} diagrams, release {release}."
        ),
        "ts_iso": str(accepted_at or "prewrite").strip(),
        "author": "odylith",
        "source": "domain-intelligence",
        "workstreams": list(workstreams),
        "artifacts": list(artifacts),
        "components": list(components),
        "context": "source-cited Semantic Intent graph and exact artifact bindings",
        "headline_hint": f"Greenfield proposal accepted for {title}",
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        "work_category": "governance",
    }


def semantic_accepted_project_payload(
    *,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    validation_gate: Mapping[str, Any] | None,
    source_launch_context: Mapping[str, Any] | None = None,
    accepted_at: str = "",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Build durable accepted memory without reparsing or rewriting proposal prose."""

    plan = require_persisted_semantic_projection_plan(proposal)
    workstream_rows = semantic_projection_workstream_rows(proposal)
    component_rows = semantic_projection_component_rows(proposal)
    semantic_projection_diagram_rows(proposal)
    backlog_items = _ordered_rows(
        backlog_items,
        key="title",
        expected=tuple(_required_text(row, "title") for row in workstream_rows),
        label="accepted Radar workstream",
    )
    component_items = _ordered_rows(
        component_items,
        key="component_id",
        expected=tuple(_required_text(row, "component_id") for row in component_rows),
        label="accepted Registry component",
    )
    diagram_ids = _exact_diagram_ids(plan, diagram_ids)
    memory_proposal = _portable(copy.deepcopy(dict(proposal)), repo_root=repo_root)
    if isinstance(memory_proposal, dict):
        memory_proposal.pop(PRODUCT_INTENT_AUTHORITY_KEY, None)
    return {
        "schema_version": "odylith.accepted_project.v1",
        "origin": "greenfield",
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        "accepted_at": str(accepted_at or "").strip(),
        "title": _identity_label(plan),
        "source": "greenfield_apply",
        "proposal": memory_proposal,
        "created": {
            "workstreams": [_durable_row(row, repo_root=repo_root) for row in backlog_items],
            "components": [_durable_row(row, repo_root=repo_root) for row in component_items],
            "diagrams": [str(value).strip() for value in diagram_ids if str(value).strip()],
            "release_selector": str(release_selector or "").strip(),
            "release_id": str(release_id or "").strip(),
        },
        "source_launch": copy.deepcopy(dict(source_launch_context or {})),
        "validation_gate": copy.deepcopy(dict(validation_gate or {})),
    }


def semantic_project_brief_markdown(
    *,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    accepted_at: str = "",
) -> str:
    """Render the typed project brief without narrative cleanup rules."""

    plan = require_persisted_semantic_projection_plan(proposal)
    workstreams = semantic_projection_workstream_rows(proposal)
    components = semantic_projection_component_rows(proposal)
    diagrams = semantic_projection_diagram_rows(proposal)
    _ordered_rows(
        backlog_items,
        key="title",
        expected=tuple(_required_text(row, "title") for row in workstreams),
        label="project brief Radar workstream",
    )
    _ordered_rows(
        component_items,
        key="component_id",
        expected=tuple(_required_text(row, "component_id") for row in components),
        label="project brief Registry component",
    )
    _exact_diagram_ids(plan, diagram_ids)
    title = _identity_label(plan)
    node_by_id = _plan_nodes(plan)
    axes = _plan_axes(plan)
    workflow_nodes = tuple(
        node_by_id[fact_id]
        for fact_id in _strings(axes.get("workflow_step_fact_ids"))
    )
    state_nodes = tuple(
        node_by_id[fact_id]
        for fact_id in _strings(axes.get("state_fact_ids"))
    )
    output_nodes = tuple(
        node_by_id[fact_id]
        for fact_id in _strings(axes.get("visible_output_fact_ids"))
    )
    lines = [
        f"# {title} Project Brief",
        "",
        "- schema: odylith.greenfield.project_brief.v1",
        "- origin: greenfield",
        f"- accepted_at: {str(accepted_at or 'prewrite').strip()}",
        f"- release: {_release_label(release_selector, release_id)}",
        f"- custody_state: {SEMANTIC_SYSTEM_POLICY_CUSTODY}",
        f"- evidence_tier: {semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY)}",
        f"- workstreams: {len(workstreams)}",
        f"- components: {len(components)}",
        f"- diagrams: {len(diagrams)}",
        "",
        "## Accepted Product Topology",
        "",
        f"Identity fact: `{plan['identity_fact_id']}` — {title}",
        "",
        "## Workflow Facts",
        "",
        *(
            f"- `{row['fact_id']}` — {row['label']}: {row['statement']}"
            for row in workflow_nodes
        ),
        "",
        "## Visible Outputs",
        "",
        *(
            f"- `{row['fact_id']}` — {row['label']}: {row['statement']}"
            for row in output_nodes
        ),
        "",
    ]
    if state_nodes:
        lines.extend(
            (
                "## State Objects",
                "",
                *(
                    f"- `{row['fact_id']}` — {row['label']}: {row['statement']}"
                    for row in state_nodes
                ),
                "",
            )
        )
    lines.extend(
        (
            "## Planned Governance Artifacts",
            "",
            *(
                f"- Radar: {row['title']}"
                for row in workstreams
            ),
            *(
                f"- Registry: `{row['component_id']}` — {row['label']}"
                for row in components
            ),
            *(
                f"- Atlas: `{row['slug']}` — {row['title']}"
                for row in diagrams
            ),
            "",
            "## Readiness Gates",
            "",
            "- Every artifact must retain the persisted fact and relation bindings.",
            "- Every visible output must have exact component and workflow custody.",
            "- The sealed authority and repository write-set hashes must remain unchanged.",
        )
    )
    if state_nodes:
        lines.append("- Every state object must retain its typed transition evidence.")
    return "\n".join(lines).rstrip() + "\n"


def semantic_project_brief_with_accepted_at(text: str, *, accepted_at: str) -> str:
    """Replace the single typed acceptance metadata row without pattern matching."""

    prefix = "- accepted_at: "
    lines = str(text or "").rstrip().splitlines()
    matching = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(matching) != 1:
        raise ValueError("graph-native project brief lacks one accepted_at metadata row")
    lines[matching[0]] = f"{prefix}{accepted_at or 'prewrite'}"
    return "\n".join(lines).rstrip() + "\n"


def semantic_project_dashboard_payload(
    *,
    proposal: Mapping[str, Any],
    accepted_project: Mapping[str, Any],
    source_launch: Mapping[str, Any],
) -> dict[str, Any]:
    """Project the accepted dashboard from typed fields without interpreting prose."""

    plan = require_persisted_semantic_projection_plan(proposal)
    workstreams = semantic_projection_workstream_rows(proposal)
    components = semantic_projection_component_rows(proposal)
    diagrams = semantic_projection_diagram_rows(proposal)
    nodes = mapping_rows(plan.get("nodes"))
    node_by_id = _plan_nodes(plan)
    axes = _plan_axes(plan)
    workflow_nodes = tuple(
        node_by_id[fact_id]
        for fact_id in _strings(axes.get("workflow_step_fact_ids"))
    )
    state_nodes = tuple(
        node_by_id[fact_id]
        for fact_id in _strings(axes.get("state_fact_ids"))
    )
    output_nodes = tuple(
        node_by_id[fact_id]
        for fact_id in _strings(axes.get("visible_output_fact_ids"))
    )
    title = _identity_label(plan)
    identity = node_by_id[_required_text(plan, "identity_fact_id")]
    workflow_labels = tuple(_required_text(row, "label") for row in workflow_nodes)
    state_labels = tuple(_required_text(row, "label") for row in state_nodes)
    output_labels = tuple(_required_text(row, "label") for row in output_nodes)
    component_labels = tuple(_required_text(row, "label") for row in components)
    actors = [_dashboard_actor_node(row) for row in nodes if row.get("kind") == "actor"]
    non_goals = tuple(
        _required_text(row, "statement") for row in nodes if row.get("kind") == "non_goal"
    )
    open_items = tuple(
        _required_text(row, "statement")
        for row in nodes
        if row.get("kind") in {"assumption", "ambiguity"}
    )
    created = _mapping(accepted_project.get("created"))
    created_workstreams = mapping_rows(created.get("workstreams"))
    backlog = (
        _ordered_rows(
            created_workstreams,
            key="title",
            expected=tuple(_required_text(row, "title") for row in workstreams),
            label="dashboard Radar workstream",
        )
        if created_workstreams
        else workstreams
    )
    risks = mapping_rows(proposal.get("risks"))
    policy_tier = semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY)
    cards = [
        {
            "label": "Workflow Facts",
            "semantic_slot": "workflow_facts",
            "body": "; ".join(workflow_labels),
            "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
            "evidence_tier": policy_tier,
        },
        {
            "label": "Visible Outputs",
            "semantic_slot": "visible_outputs",
            "body": "; ".join(output_labels),
            "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
            "evidence_tier": policy_tier,
        },
        {
            "label": "Component Boundaries",
            "semantic_slot": "component_boundaries",
            "body": "; ".join(component_labels),
            "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
            "evidence_tier": policy_tier,
        },
    ]
    if state_labels:
        cards.insert(
            2,
            {
                "label": "State Objects",
                "semantic_slot": "state_objects",
                "body": "; ".join(state_labels),
                "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
                "evidence_tier": policy_tier,
            },
        )
    prompts = _semantic_handoff_prompts(source_launch=source_launch, title=title)
    known = [
        _required_text(identity, "statement"),
        *(_required_text(row, "statement") for row in workflow_nodes),
        *(_required_text(row, "statement") for row in state_nodes),
        *(_required_text(row, "statement") for row in output_nodes),
        *component_labels,
        *non_goals,
    ]
    status_title = "Stateful delivery status" if state_labels else "Stateless delivery status"
    return {
        "schema_version": SEMANTIC_PROJECT_DASHBOARD_VERSION,
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": policy_tier,
        "eyebrow": "Project type: source-cited greenfield governance",
        "title": title,
        "intro": _required_text(identity, "statement"),
        "chips": ["verified semantic graph", "accepted greenfield project", "source cited"],
        "focus_label": "Accepted focus",
        "focus": str(source_launch.get("start_workstream_title") or workstreams[0]["title"]),
        "open_label": "Open questions",
        "open": list(open_items) or ["No unresolved semantic ambiguity."],
        "product_story_title": "Product Story",
        "product_story_note": "Every card follows the single persisted projection plan.",
        "product_story": {
            "headline": title,
            "standfirst": "",
            "paragraphs": [
                _required_text(identity, "statement"),
                *(_required_text(row, "statement") for row in workflow_nodes),
                *(_required_text(row, "statement") for row in output_nodes),
            ],
            "supporting_records": [],
            "release_contract": cards,
            "actors": [
                {"title": actor[1], "body": actor[2]}
                for actor in actors
            ],
        },
        "answers": [],
        "risk_title": "Risks",
        "risk_note": "Typed component failures that must be controlled before release.",
        "risk_items": [
            {
                "title": str(row.get("title") or row.get("statement") or "Product risk").strip(),
                "description": str(row.get("statement") or row.get("mitigation") or "").strip(),
            }
            for row in risks
        ],
        "scenario": ["Accepted typed topology", title, *workflow_labels, *output_labels, *state_labels],
        "scenario_details": list(_strings(source_launch.get("validation_gates"))),
        "actors": actors,
        "participants": actors,
        "participants_title": "Who participates?",
        "participants_note": "People named by source-cited actor facts.",
        "jobs": [
            {
                "title": str(row.get("title") or "").strip(),
                "body": str(row.get("recommended_first_slice") or row.get("opportunity") or "").strip(),
                "status": "accepted direction",
                "workstream_id": str(row.get("idea_id") or "").strip(),
                "custody_state": str(row.get("custody_state") or SEMANTIC_SYSTEM_POLICY_CUSTODY),
                "evidence_tier": str(row.get("evidence_tier") or policy_tier),
            }
            for row in backlog
        ],
        "jobs_title": "What is planned for the first release?",
        "jobs_note": "Work is bound to exact projection-plan components and diagrams.",
        "current": f"{title} is accepted product direction; implementation proof does not exist yet.",
        "desired": "; ".join(output_labels),
        "question": "What should move next?",
        "recommendation": str(source_launch.get("project_first_prompt") or "").strip(),
        "options": [
            ("A", "Open the first workstream", str(source_launch.get("start_workstream_title") or "").strip()),
            ("B", "Revise source evidence", "Rebuild the semantic transaction before changing product meaning."),
            ("C", "Pause", "Keep the accepted direction visible without starting source work."),
        ],
        "host_handoff_title": "Start source creation",
        "host_handoff_note": "Follow the persisted topology; stop when an exact binding fails.",
        "host_handoff_steps": list(_strings(source_launch.get("operator_sequence"))),
        "host_handoff_prompts": prompts,
        "projection": {
            "refreshed_at": str(accepted_project.get("accepted_at") or "prewrite"),
            "origin": "accepted greenfield project",
            "maturity": "accepted source-cited direction",
            "work_mode": "orienting",
            "topology_profile": "semantic-graph-first",
        },
        "claim_evidence": [],
        "artifact_coverage": [],
        "topology_spine": [
            {
                "fact_id": _required_text(row, "fact_id"),
                "kind": _required_text(row, "kind"),
                "label": _required_text(row, "label"),
            }
            for row in (*workflow_nodes, *state_nodes, *output_nodes)
        ],
        "contradictions": [],
        "delta": ["This accepted project begins from source-cited intent; implementation evidence is still required."],
        "risk_classes": [
            {
                "risk": str(row.get("title") or "Product risk").strip(),
                "meaning": str(row.get("statement") or "").strip(),
            }
            for row in risks
        ],
        "audience_emphasis": [actor[1] for actor in actors],
        "degraded_state": ["Accepted intent is not implementation or release evidence."],
        "known": [value for value in known if value],
        "unknown": list(open_items),
        "confidence": "High for accepted intent; unproven for implementation",
        "blockers": [(value, "Open", "accepted intent") for value in open_items[:4]],
        "sections": ["product_story", "participants", "risks", "jobs", "next"],
        "work_state_kicker": "Status now",
        "state_title": status_title,
        "state_note": "Accepted semantic direction remains distinct from implementation proof.",
        "current_state_label": "Current status",
        "desired_state_label": "Desired outputs",
        "next_title": "Start source creation",
        "next_note": "Begin only from the exact planned start workstream.",
        "governance_titles": [str(row.get("title") or "").strip() for row in backlog],
        "artifact_depth": {
            "workstreams": len(workstreams),
            "components": len(components),
            "diagrams": len(diagrams),
            "state_objects": len(state_nodes),
            "visible_outputs": len(output_nodes),
        },
        "sources": {"proposal": "odylith/runtime/source/accepted-project.v1.json"},
    }


def _dashboard_actor_node(node: Mapping[str, Any]) -> tuple[str, str, str]:
    attributes = {
        _required_text(row, "name"): _required_text(row, "value")
        for row in mapping_rows(node.get("attributes"))
    }
    return (
        "",
        _required_text(node, "label"),
        attributes.get("responsibility", _required_text(node, "statement")),
    )


def _semantic_handoff_prompts(
    *, source_launch: Mapping[str, Any], title: str
) -> list[dict[str, str]]:
    project_prompt = str(source_launch.get("project_first_prompt") or "").strip()
    implementation = str(source_launch.get("implementation_prompt") or "").strip()
    commands = _strings(source_launch.get("verification_commands"))
    rows = [
        ("review_project", "Review accepted project", project_prompt),
        ("create_plan", "Create first implementation plan", implementation),
        (
            "prove_behavior",
            "Run behavior proof",
            " ".join(_strings(source_launch.get("validation_gates"))),
        ),
        (
            "verify_governance",
            "Verify governed bindings",
            " Run ".join(commands),
        ),
        (
            "refresh_governance",
            "Refresh governed records",
            f"Refresh {title} only after the accepted behavior and governance checks pass.",
        ),
    ]
    return [
        {
            "step_id": step_id,
            "label": label,
            "when": "Use this step only after the preceding graph-bound gate passes.",
            "prompt": prompt,
            "result": "Evidence for the next graph-bound decision.",
            "stop": "Stop on contradiction, missing evidence, or scope drift.",
        }
        for step_id, label, prompt in rows
        if prompt
    ]


def _ordered_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    key: str,
    expected: Sequence[str],
    label: str,
) -> tuple[Mapping[str, Any], ...]:
    by_value: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _required_text(row, key)
        if value in by_value:
            raise ValueError(f"verified semantic {label} `{key}` values are not unique")
        by_value[value] = row
    if set(by_value) != set(expected):
        raise ValueError(f"verified semantic {label} depth differs from its projection plan")
    return tuple(by_value[value] for value in expected)


def _exact_diagram_ids(
    plan: Mapping[str, Any],
    diagram_ids: Sequence[str],
) -> tuple[str, ...]:
    expected = len(mapping_rows(plan.get("diagrams")))
    values = tuple(str(value).strip() for value in diagram_ids if str(value).strip())
    if len(values) != expected or len(set(values)) != len(values):
        raise ValueError("verified semantic diagram allocation differs from its projection plan")
    return values


def _plan_nodes(plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        _required_text(row, "fact_id"): row
        for row in mapping_rows(plan.get("nodes"))
    }


def _plan_axes(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    axes = plan.get("axes")
    if not isinstance(axes, Mapping):
        raise ValueError("persisted semantic projection plan lacks typed axes")
    return axes


def _identity_label(plan: Mapping[str, Any]) -> str:
    identity_id = _required_text(plan, "identity_fact_id")
    return _required_text(_plan_nodes(plan)[identity_id], "label")


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise ValueError(f"verified semantic memory lacks `{key}`")
    return value


def _durable_row(row: Mapping[str, Any], *, repo_root: Path | None) -> dict[str, Any]:
    return {
        str(key): _portable(value, repo_root=repo_root)
        for key, value in row.items()
    }


def _portable(value: Any, *, repo_root: Path | None) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _portable(item, repo_root=repo_root) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable(item, repo_root=repo_root) for item in value]
    if isinstance(value, tuple):
        return tuple(_portable(item, repo_root=repo_root) for item in value)
    if not isinstance(value, (str, Path)) or repo_root is None:
        return value
    token = str(value).strip()
    if not token:
        return token
    path = Path(token).expanduser()
    if not path.is_absolute():
        return token
    try:
        return path.resolve().relative_to(Path(repo_root).expanduser().resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _values(rows: Sequence[Mapping[str, Any]], key: str, *, upper: bool = False) -> tuple[str, ...]:
    values = tuple(str(row.get(key) or "").strip() for row in rows if str(row.get(key) or "").strip())
    return tuple(value.upper() for value in values) if upper else values


def _release_label(selector: str, release_id: str) -> str:
    left = str(selector or "").strip()
    right = str(release_id or "").strip()
    return f"{left}->{right}" if left and right else left or right or "none"


def _dedupe(values: Sequence[Any]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


__all__ = [
    "SEMANTIC_PROJECT_DASHBOARD_VERSION",
    "semantic_acceptance_event_preview",
    "semantic_accepted_project_payload",
    "semantic_project_dashboard_payload",
    "semantic_project_brief_markdown",
    "semantic_project_brief_with_accepted_at",
]
