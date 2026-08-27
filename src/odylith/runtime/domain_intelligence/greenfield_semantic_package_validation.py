"""Exact validation for graph-native Greenfield proposal and package projections.

The source-cited Semantic Intent graph is the sole meaning authority on this
path.  These checks compare typed identities, relations, artifact bindings,
and sealed transaction evidence.  They never infer meaning from rendered
prose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import datetime as dt
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_prewrite_commit_result
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence.greenfield_completion_types import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_semantic_component_package import (
    render_semantic_component_specs,
    semantic_component_authoring_inputs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_delivery import (
    semantic_first_release_workstream_ids,
    semantic_next_steps,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_memory import (
    semantic_project_dashboard_payload,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_validation import (
    semantic_projection_issues,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_traceability import (
    build_semantic_traceability_plan,
    require_persisted_semantic_projection_plan,
    semantic_projection_component_rows,
    semantic_projection_diagram_rows,
    semantic_projection_workstream_rows,
)
from odylith.runtime.domain_intelligence.greenfield_traceability_contract import (
    GreenfieldTraceabilityPlan,
)


SEMANTIC_PACKAGE_VALIDATION_VERSION = "odylith.greenfield.semantic-package-validation.v2"


@dataclass(frozen=True)
class VerifiedSemanticValidation:
    """Typed validation evidence for one graph-native projection phase."""

    phase: str
    issues: tuple[str, ...]
    artifact_counts: dict[str, int]

    @property
    def status(self) -> str:
        return "failed" if self.issues else "passed"

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEMANTIC_PACKAGE_VALIDATION_VERSION,
            "status": self.status,
            "phase": self.phase,
            "summary": "Exact graph and artifact bindings passed." if self.passed else "Exact graph or artifact bindings failed.",
            "dimensions": {
                "semantic_graph": "exact",
                "artifact_bindings": "exact" if self.phase == "prewrite_package" else "pending",
                "transaction_integrity": "sealed" if self.phase == "prewrite_package" else "pending",
            },
            "issues": list(self.issues),
            "artifact_counts": dict(self.artifact_counts),
        }


def validate_verified_semantic_proposal(
    proposal: Mapping[str, Any], *, intent_authority: Mapping[str, Any], release_selector: str
) -> VerifiedSemanticValidation:
    """Validate exact graph projection before any staged artifact rendering."""

    issues = list(
        semantic_projection_issues(proposal, intent_authority=intent_authority)
    )
    try:
        require_persisted_semantic_projection_plan(proposal)
        components = semantic_projection_component_rows(proposal)
        backlog = semantic_projection_workstream_rows(proposal)
        diagrams = semantic_projection_diagram_rows(proposal)
    except ValueError as exc:
        issues.append(str(exc))
        components = ()
        backlog = ()
        diagrams = ()
    issues.extend(_unique_required_values(components, "component_id", "component"))
    issues.extend(_unique_required_values(backlog, "title", "Radar workstream"))
    issues.extend(_unique_required_values(diagrams, "slug", "Atlas diagram"))
    if not components:
        issues.append("verified semantic proposal lacks graph-projected components")
    if not backlog:
        issues.append("verified semantic proposal lacks graph-projected workstreams")
    if not diagrams:
        issues.append("verified semantic proposal lacks graph-projected diagrams")
    selector = str(release_selector or "").strip()
    if not selector:
        issues.append("verified semantic package lacks a release selector")
    if not isinstance(proposal.get("project_brief"), Mapping):
        issues.append("verified semantic proposal lacks its typed project brief")
    if len(_strings(proposal.get("validation_strategy"))) < 3:
        issues.append("verified semantic proposal lacks its typed validation strategy")
    return VerifiedSemanticValidation(
        phase="proposal_projection",
        issues=_dedupe(issues),
        artifact_counts=_artifact_counts(proposal, None),
    )


def validate_verified_semantic_package(
    package: GreenfieldCompletionPackage,
    *,
    intent_authority: Mapping[str, Any],
    release_selector: str,
) -> VerifiedSemanticValidation:
    """Validate exact graph-to-artifact bindings and sealed write evidence."""

    proposal = package.proposal if isinstance(package.proposal, Mapping) else {}
    issues = list(
        validate_verified_semantic_proposal(
            proposal,
            intent_authority=intent_authority,
            release_selector=release_selector,
        ).issues
    )
    try:
        components = semantic_projection_component_rows(proposal)
        backlog = semantic_projection_workstream_rows(proposal)
        diagrams = semantic_projection_diagram_rows(proposal)
    except ValueError as exc:
        components = ()
        backlog = ()
        diagrams = ()
        issues.append(str(exc))
    backlog_result = _mapping(package.backlog_result)
    created = mapping_rows(backlog_result.get("created"))
    expected_titles = tuple(str(row.get("title") or "").strip() for row in backlog)
    actual_titles = tuple(str(row.get("title") or "").strip() for row in created)
    if actual_titles != expected_titles:
        issues.append("compiled Radar workstreams differ from the exact graph projection")
    issues.extend(_unique_required_values(created, "idea_id", "compiled Radar workstream"))

    diagram_ids = tuple(str(value).strip().upper() for value in package.atlas_diagram_ids)
    if len(diagram_ids) != len(diagrams) or len(set(diagram_ids)) != len(diagram_ids) or any(not value for value in diagram_ids):
        issues.append("compiled Atlas identifiers differ from the exact graph projection")
    issues.extend(_atlas_issues(package, diagrams=diagrams, diagram_ids=diagram_ids))
    issues.extend(
        _component_issues(
            package,
            components=components,
            backlog_result=backlog_result,
            diagram_ids=diagram_ids,
            release_selector=release_selector,
        )
    )
    issues.extend(_artifact_residue_issues(package))
    issues.extend(
        _traceability_issues(
            package,
            proposal=proposal,
            created=created,
            diagram_ids=diagram_ids,
        )
    )
    expected_release_ids = tuple(
        semantic_first_release_workstream_ids(proposal=proposal, created_backlog=created)
    )
    if tuple(package.release_workstream_ids) != expected_release_ids:
        issues.append("compiled release workstreams differ from exact graph bindings")
    expected_next_steps: Mapping[str, Any] = {}
    try:
        expected_next_steps = semantic_next_steps(
            proposal=proposal,
            backlog_result=backlog_result,
            first_release_workstreams=expected_release_ids,
            release_selector=release_selector,
        )
        if package.next_steps_preview != expected_next_steps:
            issues.append("compiled operator handoff differs from exact graph bindings")
    except ValueError as exc:
        issues.append(str(exc))
    issues.extend(
        _memory_issues(
            package,
            proposal=proposal,
            release_ids=expected_release_ids,
            source_launch=expected_next_steps,
        )
    )
    issues.extend(_release_issues(package, release_selector=release_selector, release_ids=expected_release_ids))
    issues.extend(_transaction_evidence_issues(package))
    return VerifiedSemanticValidation(
        phase="prewrite_package",
        issues=_dedupe(issues),
        artifact_counts=_artifact_counts(proposal, package),
    )


def require_verified_semantic_proposal(
    proposal: Mapping[str, Any], *, intent_authority: Mapping[str, Any], release_selector: str
) -> VerifiedSemanticValidation:
    report = validate_verified_semantic_proposal(
        proposal,
        intent_authority=intent_authority,
        release_selector=release_selector,
    )
    _raise_for_failed(report)
    return report


def require_verified_semantic_package(
    package: GreenfieldCompletionPackage,
    *,
    intent_authority: Mapping[str, Any],
    release_selector: str,
) -> VerifiedSemanticValidation:
    report = validate_verified_semantic_package(
        package,
        intent_authority=intent_authority,
        release_selector=release_selector,
    )
    _raise_for_failed(report)
    return report


def _component_issues(
    package: GreenfieldCompletionPackage,
    *,
    components: tuple[Mapping[str, Any], ...],
    backlog_result: Mapping[str, Any],
    diagram_ids: tuple[str, ...],
    release_selector: str,
) -> list[str]:
    issues: list[str] = []
    try:
        expected_inputs = semantic_component_authoring_inputs(
            proposal=package.proposal,
            release_selector=release_selector,
            backlog_result=backlog_result,
            diagram_ids=diagram_ids,
        )
        expected_specs = render_semantic_component_specs(
            proposal=package.proposal,
            release_selector=release_selector,
            backlog_result=backlog_result,
            diagram_ids=diagram_ids,
        )
    except ValueError as exc:
        return [str(exc)]
    if package.rendered_component_specs != expected_specs:
        issues.append("compiled Registry specs differ from exact typed component contracts")
    previews = tuple(package.component_registry_preview)
    if len(previews) != len(components) or len(previews) != len(expected_inputs):
        issues.append("compiled Registry previews differ from component cardinality")
        return issues
    for component, expected, preview in zip(components, expected_inputs, previews, strict=True):
        if not isinstance(preview, Mapping):
            issues.append("compiled Registry preview is not a mapping")
            continue
        component_id = str(component.get("component_id") or "").strip()
        if preview.get("authoring_input") != expected:
            issues.append(f"compiled Registry authoring input for `{component_id}` differs from its typed contract")
        if preview.get("implementation_handoff") != expected.get("implementation_handoff"):
            issues.append(f"compiled Registry handoff for `{component_id}` differs from its exact Radar binding")
        gate = _mapping(preview.get("validation_gate"))
        if gate.get("status") != "passed":
            issues.append(f"compiled Registry artifact tribunal did not pass for `{component_id}`")
        entry = _mapping(preview.get("registry_entry"))
        expected_entry = {
            "component_id": component_id,
            "name": component.get("label"),
            "kind": component.get("kind"),
            "qualification": component.get("qualification"),
            "path_prefixes": [component.get("intended_path")],
            "workstreams": list(expected.get("workstreams", ())),
            "diagrams": list(expected.get("diagrams", ())),
        }
        for key, value in expected_entry.items():
            if entry.get(key) != value:
                issues.append(f"compiled Registry entry `{component_id}` has drifted `{key}`")
    return issues


def _atlas_issues(
    package: GreenfieldCompletionPackage,
    *,
    diagrams: tuple[Mapping[str, Any], ...],
    diagram_ids: tuple[str, ...],
) -> list[str]:
    issues: list[str] = []
    expected_sources = {
        f"odylith/atlas/source/{str(row.get('slug') or '').strip()}.mmd":
            str(row.get("mermaid_source") or "").rstrip() + "\n"
        for row in diagrams
    }
    if package.rendered_atlas_sources != expected_sources:
        issues.append("compiled Atlas sources differ from exact graph diagram projections")
    rows = tuple(package.atlas_catalog_rows)
    if len(rows) != len(diagrams):
        issues.append("compiled Atlas catalog differs from diagram cardinality")
    else:
        for diagram, diagram_id, row in zip(diagrams, diagram_ids, rows, strict=True):
            slug = str(diagram.get("slug") or "").strip()
            if not isinstance(row, Mapping) or (
                row.get("diagram_id") != diagram_id
                or row.get("slug") != slug
                or row.get("source_mmd") != f"odylith/atlas/source/{slug}.mmd"
                or row.get("projection_origin") != "verified_semantic_intent_graph"
                or row.get("diagram_boxes") != diagram.get("diagram_boxes")
            ):
                issues.append(f"compiled Atlas catalog binding drifted for `{slug}`")
    try:
        dt.date.fromisoformat(str(package.atlas_review_date or "").strip())
    except ValueError:
        issues.append("compiled Atlas review date is missing or invalid")
    return issues


def _traceability_issues(
    package: GreenfieldCompletionPackage,
    *,
    proposal: Mapping[str, Any],
    created: tuple[Mapping[str, Any], ...],
    diagram_ids: tuple[str, ...],
) -> list[str]:
    try:
        expected = build_semantic_traceability_plan(
            proposal=proposal,
            created_backlog=created,
            diagram_ids=diagram_ids,
        )
    except ValueError as exc:
        return [str(exc)]
    actual = package.traceability_plan
    if not isinstance(actual, GreenfieldTraceabilityPlan):
        return ["compiled package lacks a typed graph traceability plan"]
    if actual != expected:
        return ["compiled traceability plan differs from exact graph artifact bindings"]
    return []


def _memory_issues(
    package: GreenfieldCompletionPackage,
    *,
    proposal: Mapping[str, Any],
    release_ids: tuple[str, ...],
    source_launch: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    accepted = _mapping(package.accepted_project_preview)
    accepted_proposal = _mapping(accepted.get("proposal"))
    if accepted_proposal.get("projection_plan") != proposal.get("projection_plan"):
        issues.append("compiled accepted-project memory differs from the persisted projection plan")
    if package.project_brief_preview != proposal.get("project_brief"):
        issues.append("compiled project-brief preview differs from the exact proposal")
    if not str(package.project_brief_record_text or "").strip():
        issues.append("compiled project-brief record is missing")
    compass = _mapping(package.compass_memory_preview)
    if tuple(_strings(compass.get("workstreams"))) != release_ids:
        issues.append("compiled Compass memory differs from exact release workstreams")
    expected_dashboard = semantic_project_dashboard_payload(
        proposal=proposal,
        accepted_project=accepted,
        source_launch=source_launch,
    )
    if package.project_dashboard_preview != expected_dashboard:
        issues.append("compiled project dashboard differs from exact semantic projections")
    return issues


def _artifact_residue_issues(package: GreenfieldCompletionPackage) -> list[str]:
    """Reject superseded scalar and wave fields by exact structural key."""

    issues: list[str] = []
    forbidden_contract_keys = {
        "owned_state",
        "produced_outputs",
        "states_or_transitions",
        "state_object",
        "visible_output",
    }
    for preview in package.component_registry_preview:
        if not isinstance(preview, Mapping):
            continue
        authoring_input = _mapping(preview.get("authoring_input"))
        handoff = _mapping(authoring_input.get("implementation_handoff"))
        if {"wave_label", "wave_status"} & set(handoff):
            issues.append("compiled Registry handoff retains superseded wave fields")
        contract = _mapping(authoring_input.get("component_contract"))
        if forbidden_contract_keys & set(contract):
            issues.append("compiled Registry contract retains scalar state or output aliases")
        state_objects = _strings(contract.get("state_objects"))
        if bool(state_objects) != bool(contract.get("stateful")):
            issues.append("compiled Registry contract stateful flag differs from plural states")
    return issues


def _release_issues(
    package: GreenfieldCompletionPackage,
    *,
    release_selector: str,
    release_ids: tuple[str, ...],
) -> list[str]:
    if not str(release_selector or "").strip():
        return []
    target = _mapping(package.release_target_result)
    assignment = _mapping(package.release_assignment_result)
    issues: list[str] = []
    if target.get("dry_run") is not True:
        issues.append("compiled release target is not a pre-confirm dry run")
    if assignment.get("dry_run") is not True:
        issues.append("compiled release assignment is not a pre-confirm dry run")
    if tuple(_strings(assignment.get("workstream_ids"))) != release_ids:
        issues.append("compiled release assignment differs from exact release workstreams")
    return issues


def _transaction_evidence_issues(package: GreenfieldCompletionPackage) -> list[str]:
    issues: list[str] = []
    safety = _mapping(package.prewrite_safety_preview)
    checks = _mapping(safety.get("checks"))
    if safety.get("status") != "passed" or not checks or not all(value is True for value in checks.values()):
        issues.append("compiled prewrite safety proof did not pass")
    issues.extend(greenfield_surface_refresh_proof.surface_refresh_preview_issues(package.surface_refresh_preview))
    for function, value in (
        (greenfield_repository_write_set.require_compiled_greenfield_repository_write_set, package.repository_write_set),
        (greenfield_prewrite_commit_result.require_greenfield_commit_result_preview, package.commit_result_preview),
    ):
        try:
            function(value)
        except ValueError as exc:
            issues.append(str(exc))
    if not isinstance(package.baseline_writes, Mapping):
        issues.append("compiled baseline writes are missing")
    if not isinstance(package.brand_asset_writes, Mapping):
        issues.append("compiled brand assets are missing")
    return issues


def _artifact_counts(
    proposal: Mapping[str, Any], package: GreenfieldCompletionPackage | None
) -> dict[str, int]:
    try:
        plan = require_persisted_semantic_projection_plan(proposal)
    except ValueError:
        plan = {}
    counts = {
        "workstreams": len(mapping_rows(plan.get("workstreams"))),
        "components": len(mapping_rows(plan.get("components"))),
        "diagrams": len(mapping_rows(plan.get("diagrams"))),
    }
    if package is None:
        return counts
    counts.update(
        {
            "rendered_component_specs": len(_mapping(package.rendered_component_specs)),
            "rendered_workstream_files": len(_mapping(_mapping(package.backlog_result).get("idea_files"))),
            "rendered_atlas_sources": len(_mapping(package.rendered_atlas_sources)),
            "atlas_catalog_rows": len(package.atlas_catalog_rows),
            "component_registry_previews": len(package.component_registry_preview),
            "project_brief_previews": int(isinstance(package.project_brief_preview, Mapping)),
            "tribunal_previews": int(isinstance(package.tribunal_preview, Mapping)),
            "accepted_project_previews": int(isinstance(package.accepted_project_preview, Mapping)),
            "compass_memory_previews": int(isinstance(package.compass_memory_preview, Mapping)),
            "next_steps_previews": int(isinstance(package.next_steps_preview, Mapping)),
            "surface_refresh_previews": int(isinstance(package.surface_refresh_preview, Mapping)),
            "release_assignment_previews": int(isinstance(package.release_assignment_result, Mapping)),
            "release_workstream_ids": len(package.release_workstream_ids),
        }
    )
    return counts


def _raise_for_failed(report: VerifiedSemanticValidation) -> None:
    if report.passed:
        return
    raise ValueError("verified Semantic Intent projection failed: " + "; ".join(report.issues))


def _unique_required_values(
    rows: Sequence[Mapping[str, Any]], key: str, label: str
) -> list[str]:
    values = tuple(str(row.get(key) or "").strip() for row in rows)
    issues: list[str] = []
    if any(not value for value in values):
        issues.append(f"verified semantic {label} lacks `{key}`")
    if len(set(values)) != len(values):
        issues.append(f"verified semantic {label} `{key}` values are not unique")
    return issues


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


__all__ = [
    "SEMANTIC_PACKAGE_VALIDATION_VERSION",
    "VerifiedSemanticValidation",
    "require_verified_semantic_package",
    "require_verified_semantic_proposal",
    "validate_verified_semantic_package",
    "validate_verified_semantic_proposal",
]
