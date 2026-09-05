"""Deterministic Tribunal for sealed authored Greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    AUTHORED_SEMANTICS_KEY,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.project_intelligence_binding import (
    PROJECT_INTELLIGENCE_BINDING_KEY,
    project_intelligence_binding_issues,
)
from odylith.runtime.domain_intelligence.proposal_validation import format_proposal_issue_report


_AUTHORED_TRIBUNAL_ROLES = (
    (
        "beneficiary_advocate",
        "Project beneficiary advocate",
        "Protects the person or team receiving the value.",
    ),
    (
        "risk_owner",
        "Project risk reviewer",
        "Owns loss, harm, compliance, safety, or operational exposure.",
    ),
    (
        "evidence_owner",
        "Project proof reviewer",
        "Decides what proof is strong enough to trust.",
    ),
    (
        "implementation_owner",
        "Project implementation owner",
        "Owns source paths, interfaces, and build sequence.",
    ),
    (
        "release_owner",
        "Project release owner",
        "Owns release boundary, rollback, and promotion readiness.",
    ),
)


_AUTHORED_EXACT_PROJECTION_FIELDS = (
    "schema_version",
    "mode",
    "provider_calls",
    "host_agnostic",
    "write_policy",
    "projection_origin",
    "classification",
    "greenfield_ux",
    "assumptions",
    "open_questions",
    "risks",
    "security_compliance",
    "validation_strategy",
    "project_brief",
    "project_intelligence",
    "release_plan",
    "backlog",
    "components",
    "semantic_model",
    "diagrams",
    "apply_commands",
)
_ARTIFACT_BOUND_PROJECTION_FIELDS = frozenset(
    {"release_plan", "backlog", "components", "diagrams"}
)


@dataclass(frozen=True)
class GreenfieldTribunalDecision:
    status: str
    version: str
    summary: str
    dimensions: dict[str, str]
    issues: tuple[str, ...]
    warnings: tuple[str, ...]
    visible_actors: tuple[dict[str, str], ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "version": self.version,
            "summary": self.summary,
            "dimensions": dict(self.dimensions),
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "visible_actors": [dict(row) for row in self.visible_actors],
        }


def run_greenfield_tribunal(
    proposal: Mapping[str, Any],
    *,
    release_selector: str = "",
) -> GreenfieldTribunalDecision:
    """Adjudicate exact authored projection coherence before source-truth writes."""

    intent_value = proposal.get("intent")
    intent = intent_value if isinstance(intent_value, Mapping) else {}
    if (
        proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN
        and AUTHORED_SEMANTICS_KEY not in intent
    ):
        raise ValueError("Greenfield Tribunal requires a sealed authored projection")
    return _run_authored_projection_tribunal(
        proposal,
        intent=intent,
        release_selector=release_selector,
    )


def _run_authored_projection_tribunal(
    proposal: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    release_selector: str,
) -> GreenfieldTribunalDecision:
    issues: list[str] = []
    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        issues.append("authored proposal must preserve its projection origin")
    try:
        relations = first_path_relations_from_intent(intent)
    except (TypeError, ValueError):
        relations = ()
    if not relations:
        issues.append("authored proposal must preserve valid first_path_relations")
    issues.extend(project_intelligence_binding_issues(proposal))

    rows = {
        key: mapping_rows(proposal.get(key))
        for key in ("backlog", "components", "diagrams")
    }
    for key, projected in rows.items():
        raw = proposal.get(key)
        if not isinstance(raw, list) or not raw or len(raw) != len(projected):
            issues.append(f"authored proposal `{key}` must be a non-empty list of objects")
    issues.extend(
        _authored_projection_binding_issues(
            proposal=proposal,
            intent=intent,
            release_selector=release_selector,
        )
    )

    visible_actors = _authored_visible_actors(relations)
    dimensions = {
        "typed_intent": f"checked {len(relations)} typed first-path relation(s) from the authored intent",
        "artifact_topology": (
            f"checked {len(rows['backlog'])} backlog row(s), "
            f"{len(rows['components'])} component(s), and {len(rows['diagrams'])} diagram(s) "
            "for exact authored identifiers and references"
        ),
        "semantic_projection": (
            f"checked {len(_authored_events(relations))} authored event(s) against the "
            "semantic model, component sequence, and workstream projection"
        ),
        "provenance": (
            "checked the authored projection origin and project-intelligence bindings "
            "to intent.authored_semantics"
        ),
    }
    return GreenfieldTribunalDecision(
        status="failed" if issues else "passed",
        version="greenfield-validation-gate-v1",
        summary="Accepted typed product direction is structurally complete for project records."
        if not issues
        else "Accepted typed product direction is not structurally complete for project records.",
        dimensions=dimensions,
        issues=tuple(dict.fromkeys(issues)),
        warnings=(),
        visible_actors=visible_actors,
    )


def _authored_visible_actors(
    relations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], ...]:
    """Expose fixed Tribunal review roles without classifying actor prose."""

    human_relation = next(
        (row for row in relations if row.get("actor_kind") == "human"),
        None,
    )
    rows = [
        {
            "stable_role": role,
            "visible_actor": label,
            "actor_source": "governance_role",
            "responsibility": responsibility,
        }
        for role, label, responsibility in _AUTHORED_TRIBUNAL_ROLES
    ]
    if isinstance(human_relation, Mapping):
        rows.insert(
            1,
            {
                "stable_role": "domain_operator",
                "visible_actor": str(human_relation.get("actor_fact_quote") or ""),
                "actor_source": "explicit_intent_actor",
                "responsibility": str(human_relation.get("event_quote") or ""),
            },
        )
    else:
        rows.insert(
            1,
            {
                "stable_role": "domain_operator",
                "visible_actor": "Project workflow operator",
                "actor_source": "governance_role",
                "responsibility": "Checks that the workflow is operationally coherent.",
            },
        )
    return tuple(rows)


def _authored_projection_binding_issues(
    *,
    proposal: Mapping[str, Any],
    intent: Mapping[str, Any],
    release_selector: str,
) -> tuple[str, ...]:
    release_value = proposal.get("release_plan")
    release_plan = release_value if isinstance(release_value, Mapping) else {}
    selector = str(release_selector or release_plan.get("selector") or "").strip()
    try:
        expected = build_authored_greenfield_proposal(
            observed_source={},
            release_selector=selector,
            confirmed_intent=intent,
        )
    except (TypeError, ValueError):
        return ("authored proposal could not be reproduced from its sealed typed intent",)

    actual_view = _authored_projection_view(proposal)
    expected_view = _authored_projection_view(expected)
    drifted = [
        field
        for field in _AUTHORED_EXACT_PROJECTION_FIELDS
        if actual_view[field] != expected_view[field]
    ]
    if not drifted:
        return ()
    return (
        "authored proposal must exactly match the deterministic projection of its sealed typed intent: "
        + ", ".join(drifted),
    )


def _authored_projection_view(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Return builder-owned fields without later provenance decoration."""

    view: dict[str, Any] = {}
    for field in _AUTHORED_EXACT_PROJECTION_FIELDS:
        value = deepcopy(proposal.get(field))
        if field in _ARTIFACT_BOUND_PROJECTION_FIELDS:
            value = _without_project_intelligence_binding(value)
        view[field] = value
    return view


def _without_project_intelligence_binding(value: Any) -> Any:
    if isinstance(value, Mapping):
        row = dict(value)
        row.pop(PROJECT_INTELLIGENCE_BINDING_KEY, None)
        return row
    if isinstance(value, list):
        return [
            _without_project_intelligence_binding(row) if isinstance(row, Mapping) else row
            for row in value
        ]
    return value


def _authored_events(relations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "actor": row.get("actor_fact_quote"),
            "owner_system": row.get("owner_system_quote"),
            "action": row.get("action_verb_quote"),
            "target_entity": row.get("target_quote"),
            "mutation": row.get("event_quote"),
            "visible_result": bool(row.get("visible_result_quote")),
            "text": row.get("event_quote"),
            "source_kind": "accepted_first_path",
        }
        for index, row in enumerate(relations, start=1)
    ]


def raise_for_failed_greenfield_tribunal(decision: GreenfieldTribunalDecision) -> None:
    if decision.passed:
        return
    raise ValueError(format_proposal_issue_report("validation gate", list(decision.issues)))
