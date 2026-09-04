"""Project-intelligence root bindings for greenfield proposal artifacts."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.value_coercion import mapping_copy
from odylith.runtime.common.value_coercion import normalize_string as clean_text
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    AUTHORED_SEMANTICS_KEY,
    AUTHORED_SEMANTICS_VERSION,
    first_path_relations_from_intent,
)

PROJECT_INTELLIGENCE_BINDING_KEY = "project_intelligence_binding"
ARTIFACT_DERIVATION_KEY = "artifact_derivation"
PROJECT_INTELLIGENCE_ROOT = "project_intelligence"
AUTHORED_SEMANTICS_ROOT = f"intent.{AUTHORED_SEMANTICS_KEY}"

_DERIVED_ARTIFACTS = (
    "release_plan",
    "backlog",
    "components",
    "diagrams",
)


def attach_project_intelligence_bindings(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Attach project-intelligence provenance to every generated artifact row."""

    result = copy.deepcopy(dict(proposal))
    project_intelligence = mapping_copy(result.get("project_intelligence"))
    intent = mapping_copy(result.get("intent"))
    root, root_schema_version, evidence_boundary, rule = _projection_authority(
        result,
        project_intelligence=project_intelligence,
        intent=intent,
    )
    base = _base_binding(
        project_intelligence=project_intelligence,
        intent=intent,
        source=root,
        schema_version=root_schema_version,
        evidence_boundary=evidence_boundary,
    )
    result[ARTIFACT_DERIVATION_KEY] = {
        "root": root,
        "root_schema_version": base["schema_version"],
        "project_title": base["project_title"],
        "project_slug": base["project_slug"],
        "derived_artifacts": list(_DERIVED_ARTIFACTS),
        "validation_gate": "greenfield-validation-gate-v1",
        "rule": rule,
    }

    result["release_plan"] = _bind_mapping(
        result.get("release_plan"),
        base=base,
        artifact_kind="release_plan",
        artifact_id=_release_identifier(result.get("release_plan")),
    )
    result["backlog"] = _bind_rows(result.get("backlog"), base=base, artifact_kind="radar_workstream")
    result["components"] = _bind_rows(result.get("components"), base=base, artifact_kind="registry_component")
    result["diagrams"] = _bind_rows(result.get("diagrams"), base=base, artifact_kind="atlas_diagram")
    return _place_derivation_after_project_intelligence(result)


def project_intelligence_binding_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return binding failures that would let artifacts drift from project intelligence."""

    issues: list[str] = []
    project_intelligence = proposal.get("project_intelligence")
    if not isinstance(project_intelligence, Mapping):
        return ["proposal project_intelligence must exist before artifact projection"]
    intent = mapping_copy(proposal.get("intent"))
    try:
        expected_root, expected_schema, _, _ = _projection_authority(
            proposal,
            project_intelligence=project_intelligence,
            intent=intent,
        )
    except ValueError as exc:
        return [str(exc)]
    if not expected_schema:
        issues.append("proposal semantic authority must include a schema version before artifact projection")
    derivation = proposal.get(ARTIFACT_DERIVATION_KEY)
    if not isinstance(derivation, Mapping):
        issues.append(f"proposal artifact_derivation must declare {expected_root} as the root")
    else:
        if clean_text(derivation.get("root")) != expected_root:
            issues.append(f"proposal artifact_derivation.root must be {expected_root}")
        if expected_schema and clean_text(derivation.get("root_schema_version")) != expected_schema:
            issues.append("proposal artifact_derivation.root_schema_version must match its semantic authority")

    _check_mapping_binding(
        proposal.get("release_plan"),
        owner="release_plan",
        expected_schema=expected_schema,
        expected_source=expected_root,
        expected_artifact_kind="release_plan",
        expected_artifact_id=_release_identifier(proposal.get("release_plan")),
        issues=issues,
    )
    _check_row_bindings(
        proposal.get("backlog"),
        owner="backlog row",
        expected_schema=expected_schema,
        expected_source=expected_root,
        artifact_kind="radar_workstream",
        issues=issues,
    )
    _check_row_bindings(
        proposal.get("components"),
        owner="component row",
        expected_schema=expected_schema,
        expected_source=expected_root,
        artifact_kind="registry_component",
        issues=issues,
    )
    _check_row_bindings(
        proposal.get("diagrams"),
        owner="diagram row",
        expected_schema=expected_schema,
        expected_source=expected_root,
        artifact_kind="atlas_diagram",
        issues=issues,
    )
    return issues


def _projection_authority(
    proposal: Mapping[str, Any],
    *,
    project_intelligence: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> tuple[str, str, str, str]:
    if proposal.get("projection_origin") == AUTHORED_PROJECTION_ORIGIN:
        if not first_path_relations_from_intent(intent):
            raise ValueError("model-authored artifact projection requires verified authored semantics")
        semantics = mapping_copy(intent.get(AUTHORED_SEMANTICS_KEY))
        if semantics.get("version") != AUTHORED_SEMANTICS_VERSION:
            raise ValueError("model-authored artifact projection requires a supported authored-semantics version")
        return (
            AUTHORED_SEMANTICS_ROOT,
            AUTHORED_SEMANTICS_VERSION,
            "projected_from_verified_authored_semantics",
            (
                "Greenfield governance artifacts copy verified authored relations and accepted facts; "
                "project_intelligence is a derived view and must not reinterpret canonical meaning."
            ),
        )
    return (
        PROJECT_INTELLIGENCE_ROOT,
        clean_text(project_intelligence.get("schema_version")),
        "derived_from_project_intelligence",
        (
            "Greenfield governance artifacts are projected from project_intelligence first; "
            "artifact-specific writers may shape the native surface but must preserve purpose, "
            "scope, state, proof, ownership, risk, and validation posture."
        ),
    )


def _base_binding(
    *,
    project_intelligence: Mapping[str, Any],
    intent: Mapping[str, Any],
    source: str,
    schema_version: str,
    evidence_boundary: str,
) -> dict[str, str]:
    return {
        "source": source,
        "schema_version": schema_version,
        "project_title": clean_text(intent.get("title")) or clean_text(project_intelligence.get("project_name")),
        "project_slug": clean_text(intent.get("project_slug")),
        "evidence_boundary": evidence_boundary,
    }


def _place_derivation_after_project_intelligence(proposal: dict[str, Any]) -> dict[str, Any]:
    if ARTIFACT_DERIVATION_KEY not in proposal or "project_intelligence" not in proposal:
        return proposal
    derivation = proposal.pop(ARTIFACT_DERIVATION_KEY)
    ordered: dict[str, Any] = {}
    inserted = False
    for key, value in proposal.items():
        ordered[key] = value
        if key == "project_intelligence":
            ordered[ARTIFACT_DERIVATION_KEY] = derivation
            inserted = True
    if not inserted:
        ordered[ARTIFACT_DERIVATION_KEY] = derivation
    return ordered


def _bind_mapping(value: Any, *, base: Mapping[str, str], artifact_kind: str, artifact_id: str) -> dict[str, Any]:
    row = dict(value) if isinstance(value, Mapping) else {}
    row[PROJECT_INTELLIGENCE_BINDING_KEY] = _binding_for(base, artifact_kind=artifact_kind, artifact_id=artifact_id)
    return row


def _bind_rows(value: Any, *, base: Mapping[str, str], artifact_kind: str) -> list[Any]:
    if not isinstance(value, list):
        return []
    result: list[Any] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            result.append(item)
            continue
        row = dict(item)
        row[PROJECT_INTELLIGENCE_BINDING_KEY] = _binding_for(
            base,
            artifact_kind=artifact_kind,
            artifact_id=_artifact_identifier(row, fallback=f"{artifact_kind}-{index}"),
        )
        result.append(row)
    return result


def _binding_for(base: Mapping[str, str], *, artifact_kind: str, artifact_id: str) -> dict[str, str]:
    binding = dict(base)
    binding["artifact_kind"] = artifact_kind
    binding["artifact_id"] = clean_text(artifact_id)
    return binding


def _release_identifier(value: Any) -> str:
    row = mapping_copy(value)
    label = clean_text(row.get("label"))
    return (
        clean_text(row.get("provisional_release_id"))
        or clean_text(row.get("selector"))
        or (slugify(label) if label else "")
        or "release_plan"
    )


def _artifact_identifier(row: Mapping[str, Any], *, fallback: str) -> str:
    for key in ("id", "workstream_id", "idea_id", "component_id", "slug", "wave_id"):
        token = clean_text(row.get(key))
        if token:
            return token
    for key in ("label", "title"):
        display = clean_text(row.get(key))
        token = slugify(display) if display else ""
        if token:
            return token
    return fallback


def _check_mapping_binding(
    value: Any,
    *,
    owner: str,
    expected_schema: str,
    expected_source: str,
    expected_artifact_kind: str,
    expected_artifact_id: str,
    issues: list[str],
) -> None:
    if not isinstance(value, Mapping):
        issues.append(f"{owner} must be an object before project_intelligence binding can be checked")
        return
    _check_binding(
        value,
        owner=owner,
        expected_schema=expected_schema,
        expected_source=expected_source,
        expected_artifact_kind=expected_artifact_kind,
        expected_artifact_id=expected_artifact_id,
        issues=issues,
    )


def _check_row_bindings(
    value: Any,
    *,
    owner: str,
    expected_schema: str,
    expected_source: str,
    artifact_kind: str,
    issues: list[str],
) -> None:
    if not isinstance(value, list) or not value:
        issues.append(f"{owner} collection must be non-empty before project_intelligence binding can be checked")
        return
    for index, row in enumerate(value, start=1):
        if not isinstance(row, Mapping):
            issues.append(f"{owner} {index} must be an object before project_intelligence binding can be checked")
            continue
        _check_binding(
            row,
            owner=f"{owner} {index}",
            expected_schema=expected_schema,
            expected_source=expected_source,
            expected_artifact_kind=artifact_kind,
            expected_artifact_id=_artifact_identifier(row, fallback=f"{artifact_kind}-{index}"),
            issues=issues,
        )


def _check_binding(
    row: Mapping[str, Any],
    *,
    owner: str,
    expected_schema: str,
    expected_source: str,
    expected_artifact_kind: str,
    expected_artifact_id: str,
    issues: list[str],
) -> None:
    binding = row.get(PROJECT_INTELLIGENCE_BINDING_KEY)
    if not isinstance(binding, Mapping):
        issues.append(f"{owner} must carry project_intelligence_binding")
        return
    if clean_text(binding.get("source")) != expected_source:
        issues.append(f"{owner} project_intelligence_binding.source must be {expected_source}")
    if expected_schema and clean_text(binding.get("schema_version")) != expected_schema:
        issues.append(f"{owner} project_intelligence_binding.schema_version must match its semantic authority")
    if clean_text(binding.get("artifact_kind")) != expected_artifact_kind:
        issues.append(
            f"{owner} project_intelligence_binding.artifact_kind must be {expected_artifact_kind}"
        )
    if clean_text(binding.get("artifact_id")) != expected_artifact_id:
        issues.append(
            f"{owner} project_intelligence_binding.artifact_id must match its stable artifact identifier"
        )


__all__ = [
    "ARTIFACT_DERIVATION_KEY",
    "AUTHORED_SEMANTICS_ROOT",
    "PROJECT_INTELLIGENCE_BINDING_KEY",
    "PROJECT_INTELLIGENCE_ROOT",
    "attach_project_intelligence_bindings",
    "project_intelligence_binding_issues",
]
