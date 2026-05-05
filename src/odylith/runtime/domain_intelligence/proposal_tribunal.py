"""Deterministic Tribunal gate for confirmed greenfield proposals.

The host model authors open-world project reasoning. Odylith's job is to keep
the write path governed: fail before source-truth writes when the proposal does
not form a coherent Radar/Registry/Atlas/program/release topology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs

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


@dataclass(frozen=True)
class GreenfieldTribunalDecision:
    status: str
    version: str
    summary: str
    dimensions: dict[str, str]
    issues: tuple[str, ...]
    warnings: tuple[str, ...]

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

    _check_release_plan(
        release_plan=release_plan,
        selector=selector,
        waves=waves,
        issues=issues,
        warnings=warnings,
    )
    dimensions["release"] = "first release selector and target refs present"

    _check_program_waves(waves=waves, issues=issues)
    dimensions["program"] = "waves carry labels, goals, validation gates, and focus"

    _check_backlog_topology(
        backlog=backlog,
        components=components,
        diagrams=diagrams,
        issues=issues,
    )
    dimensions["radar"] = "child workstreams carry component, diagram, dependency, and proof hints"

    _check_component_specs(components=components, diagrams=diagrams, issues=issues)
    dimensions["registry"] = "candidate components carry planned ownership, interfaces, dependencies, and proof"

    _check_diagram_traceability(
        diagrams=diagrams,
        backlog=backlog,
        components=components,
        issues=issues,
    )
    dimensions["atlas"] = "diagrams carry explicit workstream and component traceability hints"

    dimensions["surfaces"] = "apply refreshes Radar, Registry, Atlas, and Compass after all writes"
    status = "failed" if issues else "passed"
    summary = (
        "Greenfield proposal is coherent enough to write governed source truth."
        if not issues
        else "Greenfield proposal is not coherent enough to write governed source truth."
    )
    return GreenfieldTribunalDecision(
        status=status,
        version="greenfield-tribunal-v1",
        summary=summary,
        dimensions=dimensions,
        issues=tuple(issues),
        warnings=tuple(warnings),
    )


def raise_for_failed_greenfield_tribunal(decision: GreenfieldTribunalDecision) -> None:
    if decision.passed:
        return
    detail = "; ".join(decision.issues[:5])
    raise ValueError(f"greenfield proposal Tribunal rejected: {detail}")


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
        component_refs = _slug_values(_collect_values(row, _COMPONENT_REF_FIELDS))
        diagram_refs = _slug_values(_collect_values(row, _DIAGRAM_REF_FIELDS))
        if not component_refs:
            issues.append(f"child backlog `{title}` must name component_focus or related_components")
        elif component_aliases and not (component_refs & component_aliases):
            issues.append(f"child backlog `{title}` component_focus does not match a planned Registry component")
        if not diagram_refs:
            issues.append(f"child backlog `{title}` must name related_diagram_slugs or related_diagrams")
        elif diagram_slugs and not (diagram_refs & diagram_slugs):
            issues.append(f"child backlog `{title}` diagram reference does not match a planned Atlas diagram")
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
            issues.append(f"component `{label}` must appear in at least one planned Atlas diagram")


def _check_diagram_traceability(
    *,
    diagrams: Sequence[Mapping[str, Any]],
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    issues: list[str],
) -> None:
    backlog_titles = {
        slugify(str(row.get("title", "")))
        for row in backlog
        if str(row.get("title", "")).strip()
    }
    component_aliases = _component_aliases(components)
    for index, row in enumerate(diagrams, start=1):
        slug = str(row.get("slug", f"diagram {index}")).strip() or f"diagram {index}"
        refs = _slug_values(_collect_values(row, _WORKSTREAM_REF_FIELDS))
        if not refs:
            issues.append(f"diagram `{slug}` must name related workstream or backlog focus")
        elif backlog_titles and not (refs & backlog_titles):
            issues.append(f"diagram `{slug}` workstream focus does not match proposed backlog titles")
        aliases = _diagram_component_aliases((row,))
        if component_aliases and not (aliases & component_aliases):
            issues.append(f"diagram `{slug}` components do not match planned Registry components")


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _has_text(row: Mapping[str, Any], key: str) -> bool:
    return any(str(item).strip() for item in _text_items(row.get(key)))


def _has_any_text(row: Mapping[str, Any], keys: Sequence[str]) -> bool:
    return any(_has_text(row, key) for key in keys)


def _collect_values(row: Mapping[str, Any], fields: Sequence[str]) -> list[str]:
    values: list[str] = []
    for field in fields:
        values.extend(_text_items(row.get(field)))
    return values


def _text_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        items: list[str] = []
        for nested in value.values():
            items.extend(_text_items(nested))
        return items
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for nested in value:
            items.extend(_text_items(nested))
        return items
    token = str(value).strip()
    return [token] if token else []


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


def _diagram_component_aliases(diagrams: Sequence[Mapping[str, Any]]) -> set[str]:
    aliases: set[str] = set()
    for row in diagrams:
        aliases.update(_slug_values(_collect_values(row, _COMPONENT_REF_FIELDS)))
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
