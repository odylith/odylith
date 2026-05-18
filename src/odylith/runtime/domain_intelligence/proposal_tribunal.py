"""Deterministic Tribunal gate for confirmed greenfield proposals.

The host model authors open-world project reasoning. Odylith's job is to keep
the write path governed: fail before source-truth writes when the proposal does
not form a coherent workstream/component/diagram/program/release topology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.artifact_enrichment import tribunal_actor_projection
from odylith.runtime.domain_intelligence.greenfield_text import collect_text_values
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.project_intelligence_binding import project_intelligence_binding_issues
from odylith.runtime.domain_intelligence.proposal_validation import format_proposal_issue_report

_WORKSTREAM_REF_FIELDS = (
    "workstreams",
    "workstream_ids",
    "workstream_titles",
    "related_workstreams",
    "related_workstream_ids",
    "related_workstream_titles",
    "backlog",
    "backlog_titles",
    "target_workstreams",
    "target_workstream_titles",
    "primary_workstreams",
    "workstream_focus",
)
_COMPONENT_REF_FIELDS = (
    "component_focus",
    "component_ids",
    "components",
    "related_components",
    "related_component_ids",
)
_DIAGRAM_REF_FIELDS = (
    "diagram_slugs",
    "related_diagram_slugs",
    "related_diagrams",
    "diagrams",
)
_SECURITY_POSTURE_FIELDS = (
    "security_compliance",
    "security_posture",
    "compliance_posture",
    "domain_risk",
    "risk_posture",
)
_RISK_TOKENS = (
    "risk",
    "failure",
    "fallback",
    "rollback",
    "mitigation",
    "blast radius",
    "slo",
    "sla",
    "recovery",
    "degraded",
    "scope",
    "operational",
)
_SECURITY_TOKENS = (
    "security",
    "auth",
    "authentication",
    "authorization",
    "credential",
    "permission",
    "session",
    "secret",
    "token",
    "access",
    "ownership",
    "private",
    "abuse",
    "threat",
    "payment",
    "pii",
    "data risk",
)
_POLICY_TOKENS = (
    "compliance",
    "policy",
    "privacy",
    "retention",
    "audit",
    "regulated",
    "gdpr",
    "hipaa",
    "pci",
    "soc2",
    "moderation",
    "accessibility",
    "public",
    "private",
    "safety",
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
    """Adjudicate proposal coherence before greenfield source-truth writes."""

    backlog = _mapping_rows(proposal.get("backlog"))
    components = _mapping_rows(proposal.get("components"))
    diagrams = _mapping_rows(proposal.get("diagrams"))
    program = proposal.get("program", {}) if isinstance(proposal.get("program"), Mapping) else {}
    waves = _mapping_rows(program.get("waves"))
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    issues: list[str] = []
    warnings: list[str] = []
    dimensions: dict[str, str] = {}
    visible_actors = tribunal_actor_projection(proposal)

    issues.extend(project_intelligence_binding_issues(proposal))
    dimensions["product_story"] = (
        "accepted product story, first path, release boundary, and proof boundary stay connected"
    )

    _check_release_plan(
        release_plan=release_plan,
        selector=selector,
        waves=waves,
        issues=issues,
        warnings=warnings,
    )
    dimensions["release_boundary"] = "first release selector, target scope, and promotion criteria are present"

    _check_program_waves(waves=waves, issues=issues)
    dimensions["delivery_waves"] = "waves carry labels, goals, validation gates, and product capability focus"

    _check_backlog_topology(
        backlog=backlog,
        components=components,
        diagrams=diagrams,
        issues=issues,
    )
    dimensions["work_items"] = "child work items carry component, diagram, dependency, and proof expectations"

    _check_component_specs(components=components, diagrams=diagrams, issues=issues)
    dimensions["component_ownership"] = "candidate components carry planned ownership, interfaces, dependencies, and proof"

    _check_diagram_traceability(
        proposal=proposal,
        diagrams=diagrams,
        backlog=backlog,
        components=components,
        issues=issues,
    )
    dimensions["architecture_views"] = "diagrams carry explicit work item and component traceability hints"

    _check_domain_security_posture(proposal=proposal, issues=issues)
    dimensions["domain_security"] = "explicit domain risk, security, compliance, policy, and abuse posture present"
    _check_visible_tribunal_actors(visible_actors=visible_actors, issues=issues)
    actor_labels = ", ".join(row["visible_actor"] for row in visible_actors[:4])
    dimensions["validation_roles"] = f"stable judgment roles render as domain-specific actors: {actor_labels}"

    dimensions["record_refresh"] = "accepted product records refresh after all writes"
    status = "failed" if issues else "passed"
    summary = (
        "Accepted product direction is coherent enough to create project records."
        if not issues
        else "Accepted product direction is not coherent enough to create project records."
    )
    return GreenfieldTribunalDecision(
        status=status,
        version="greenfield-validation-gate-v1",
        summary=summary,
        dimensions=dimensions,
        issues=tuple(issues),
        warnings=tuple(warnings),
        visible_actors=visible_actors,
    )


def raise_for_failed_greenfield_tribunal(decision: GreenfieldTribunalDecision) -> None:
    if decision.passed:
        return
    raise ValueError(format_proposal_issue_report("validation gate", list(decision.issues)))


def _check_release_plan(
    *,
    release_plan: Mapping[str, Any],
    selector: str,
    waves: Sequence[Mapping[str, Any]],
    issues: list[str],
    warnings: list[str],
) -> None:
    if not selector:
        issues.append("release plan must resolve to a release selector")
    if not _has_text(release_plan, "label") and not _has_text(release_plan, "provisional_release_id"):
        issues.append("release plan must name the first governed release")
    if not _has_any_text(
        release_plan,
        ("target_workstreams", "target_workstream_titles", "target_workstream_ids"),
    ):
        first_wave = waves[0] if waves else {}
        if not _has_any_text(first_wave, ("workstreams", "workstream_titles", "primary_workstreams")):
            warnings.append(
                "release plan does not explicitly name first-wave workstreams; apply will infer from wave membership"
            )
    if not _has_any_text(
        release_plan,
        ("release_stages", "milestones", "promotion_criteria", "strategy"),
    ):
        issues.append("release plan must include stages, milestones, promotion criteria, or strategy")


def _check_program_waves(*, waves: Sequence[Mapping[str, Any]], issues: list[str]) -> None:
    if not waves:
        issues.append("program must include at least one execution wave")
        return
    for index, wave in enumerate(waves, start=1):
        if not _has_any_text(wave, ("label", "name", "wave_id", "wave")):
            issues.append(f"program wave {index} must have a label or wave id")
        if not _has_any_text(wave, ("goal", "summary")):
            issues.append(f"program wave {index} must state the delivery goal")
        if not _has_any_text(wave, ("validation", "validation_gate", "exit_gate")):
            issues.append(f"program wave {index} must state the validation or exit gate")
        if not _has_any_text(wave, (*_WORKSTREAM_REF_FIELDS, *_COMPONENT_REF_FIELDS)):
            issues.append(f"program wave {index} must name workstream or component focus")


def _check_backlog_topology(
    *,
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    issues: list[str],
) -> None:
    component_aliases = _component_aliases(components)
    diagram_slugs = {
        slugify(str(row.get("slug", "")))
        for row in diagrams
        if str(row.get("slug", "")).strip()
    }
    for index, row in enumerate(backlog[1:], start=2):
        title = str(row.get("title", f"row {index}")).strip() or f"row {index}"
        component_refs = _slug_values(collect_text_values(row, _COMPONENT_REF_FIELDS))
        diagram_refs = _slug_values(collect_text_values(row, _DIAGRAM_REF_FIELDS))
        if not component_refs:
            issues.append(f"child backlog `{title}` must name component_focus or related_components")
        elif component_aliases and not (component_refs & component_aliases):
            issues.append(f"child backlog `{title}` component_focus does not match a planned component")
        if not diagram_refs:
            issues.append(f"child backlog `{title}` must name related_diagram_slugs or related_diagrams")
        elif diagram_slugs and not (diagram_refs & diagram_slugs):
            issues.append(f"child backlog `{title}` diagram reference does not match a planned architecture diagram")
        if not _has_any_text(row, ("dependencies", "depends_on", "interfaces", "interface_changes")):
            issues.append(f"child backlog `{title}` must carry dependency or interface expectations")
        if not _has_any_text(row, ("validation", "validation_gate", "test_strategy", "success_metrics")):
            issues.append(f"child backlog `{title}` must carry validation or test strategy")


def _check_component_specs(
    *,
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    issues: list[str],
) -> None:
    diagram_component_aliases = _diagram_component_aliases(diagrams)
    for index, row in enumerate(components, start=1):
        label = str(row.get("component_id", "") or row.get("label", "") or f"component {index}").strip()
        if not _has_text(row, "boundary"):
            issues.append(f"component `{label}` must describe its planned boundary")
        if not _has_any_text(row, ("interfaces", "interface_changes")):
            issues.append(f"component `{label}` must describe planned interfaces")
        if not _has_any_text(row, ("dependencies", "depends_on")):
            issues.append(f"component `{label}` must describe dependency expectations")
        if not _has_any_text(row, ("validation", "test_strategy")):
            issues.append(f"component `{label}` must describe validation or proof expectations")
        aliases = _slug_values(
            (
                str(row.get("component_id", "")),
                str(row.get("label", "")),
                str(row.get("name", "")),
            )
        )
        if diagram_component_aliases and not (aliases & diagram_component_aliases):
            issues.append(f"component `{label}` must appear in at least one planned architecture diagram")


def _check_diagram_traceability(
    *,
    proposal: Mapping[str, Any],
    diagrams: Sequence[Mapping[str, Any]],
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    issues: list[str],
) -> None:
    backlog_aliases = _backlog_aliases(backlog)
    component_aliases = _component_aliases(components)
    project_title_slugs = _project_title_slugs(proposal)
    for index, row in enumerate(diagrams, start=1):
        slug = str(row.get("slug", f"diagram {index}")).strip() or f"diagram {index}"
        title = str(row.get("title", "")).strip()
        title_slug = slugify(title)
        if title_slug and any(
            title_slug == project_slug or title_slug.startswith(f"{project_slug}-")
            for project_slug in project_title_slugs
        ):
            issues.append(
                f"diagram `{slug}` title must name the architecture view, not repeat the project title"
            )
        refs = _slug_values(collect_text_values(row, _WORKSTREAM_REF_FIELDS))
        if not refs:
            issues.append(f"diagram `{slug}` must name related workstream or backlog focus")
        elif backlog_aliases and not (refs & backlog_aliases):
            issues.append(f"diagram `{slug}` workstream focus does not match proposed backlog ids or titles")
        aliases = _diagram_component_aliases((row,))
        if component_aliases and not (aliases & component_aliases):
            issues.append(f"diagram `{slug}` components do not match planned components")


def _check_domain_security_posture(*, proposal: Mapping[str, Any], issues: list[str]) -> None:
    explicit_posture = collect_text_values(proposal, _SECURITY_POSTURE_FIELDS)
    if not explicit_posture:
        issues.append("proposal must include explicit security_compliance, security_posture, or domain risk posture")
        return
    text = " ".join((*explicit_posture, *text_values(proposal))).casefold()
    if not _contains_any(text, _RISK_TOKENS):
        issues.append("proposal security_compliance posture must assess domain, delivery, or operational risk")
    if not _contains_any(text, _SECURITY_TOKENS):
        issues.append("proposal security_compliance posture must assess security posture")
    if not _contains_any(text, _POLICY_TOKENS):
        issues.append("proposal security_compliance posture must assess compliance, policy, privacy, accessibility, or safety posture")


_GENERIC_VISIBLE_TRIBUNAL_ACTORS = {
    "operator",
    "maintainer",
    "reviewer",
    "primary user",
    "project operator",
    "domain reviewer",
    "implementation owner",
    "evidence owner",
    "end-user advocate",
    "workflow operator",
    "risk reviewer",
    "proof reviewer",
    "build owner",
    "release owner",
    "project release owner",
}
_STABLE_ROLE_LABELS = {
    "beneficiary advocate",
    "domain operator",
    "risk owner",
    "evidence owner",
    "implementation owner",
    "release owner",
}


def _check_visible_tribunal_actors(
    *,
    visible_actors: Sequence[Mapping[str, str]],
    issues: list[str],
) -> None:
    labels = [str(row.get("visible_actor", "")).strip() for row in visible_actors]
    generic = [
        label
        for label in labels
        if label.casefold() in _GENERIC_VISIBLE_TRIBUNAL_ACTORS
        or label.casefold().replace("_", " ") in _STABLE_ROLE_LABELS
    ]
    if generic:
        issues.append(
            "Tribunal visible actors must be project-specific, not stable-role placeholders: "
            + ", ".join(generic)
        )


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _project_title_slugs(proposal: Mapping[str, Any]) -> set[str]:
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    candidates = {
        slugify(str(intent.get("title", ""))),
        slugify(str(intent.get("project_slug", ""))),
    }
    return {candidate for candidate in candidates if candidate}


def _has_text(row: Mapping[str, Any], key: str) -> bool:
    return any(text_values(row.get(key)))


def _has_any_text(row: Mapping[str, Any], keys: Sequence[str]) -> bool:
    return any(_has_text(row, key) for key in keys)


def _contains_any(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def _slug_values(values: Sequence[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        slug = slugify(str(value))
        if slug:
            result.add(slug)
            result.add(slug.replace("-", ""))
    return result


def _component_aliases(components: Sequence[Mapping[str, Any]]) -> set[str]:
    aliases: set[str] = set()
    for row in components:
        aliases.update(
            _slug_values(
                (
                    str(row.get("component_id", "")),
                    str(row.get("label", "")),
                    str(row.get("name", "")),
                )
            )
        )
    return aliases


def _backlog_aliases(backlog: Sequence[Mapping[str, Any]]) -> set[str]:
    aliases: set[str] = set()
    for row in backlog:
        aliases.update(
            _slug_values(
                (
                    str(row.get("id", "")),
                    str(row.get("idea_id", "")),
                    str(row.get("workstream_id", "")),
                    str(row.get("title", "")),
                )
            )
        )
    return aliases


def _diagram_component_aliases(diagrams: Sequence[Mapping[str, Any]]) -> set[str]:
    aliases: set[str] = set()
    for row in diagrams:
        aliases.update(_slug_values(collect_text_values(row, _COMPONENT_REF_FIELDS)))
        for component in row.get("components", []) if isinstance(row.get("components"), list) else []:
            if isinstance(component, Mapping):
                aliases.update(
                    _slug_values(
                        (
                            str(component.get("component_id", "")),
                            str(component.get("label", "")),
                            str(component.get("name", "")),
                        )
                    )
                )
            else:
                aliases.update(_slug_values((str(component),)))
    return aliases


__all__ = [
    "GreenfieldTribunalDecision",
    "raise_for_failed_greenfield_tribunal",
    "run_greenfield_tribunal",
]
