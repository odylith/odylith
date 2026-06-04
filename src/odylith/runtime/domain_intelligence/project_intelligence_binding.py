"""Project-intelligence root bindings for greenfield proposal artifacts."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from odylith.runtime.common.value_coercion import mapping_copy
from odylith.runtime.domain_intelligence.greenfield_text import clean_text

PROJECT_INTELLIGENCE_BINDING_KEY = "project_intelligence_binding"
ARTIFACT_DERIVATION_KEY = "artifact_derivation"
PROJECT_INTELLIGENCE_ROOT = "project_intelligence"

_DERIVED_ARTIFACTS = (
    "program",
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
    base = _base_binding(project_intelligence=project_intelligence, intent=intent)
    result[ARTIFACT_DERIVATION_KEY] = {
        "root": PROJECT_INTELLIGENCE_ROOT,
        "root_schema_version": base["schema_version"],
        "project_title": base["project_title"],
        "project_slug": base["project_slug"],
        "derived_artifacts": list(_DERIVED_ARTIFACTS),
        "validation_gate": "greenfield-validation-gate-v1",
        "rule": (
            "Greenfield governance artifacts are projected from project_intelligence first; "
            "artifact-specific writers may shape the native surface but must preserve purpose, "
            "scope, state, proof, ownership, risk, and validation posture."
        ),
    }

    result["release_plan"] = _bind_mapping(
        result.get("release_plan"),
        base=base,
        artifact_kind="release_plan",
        artifact_id=_release_identifier(result.get("release_plan")),
    )
    result["program"] = _bind_program(result.get("program"), base=base)
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
    expected_schema = clean_text(project_intelligence.get("schema_version"))
    if not expected_schema:
        issues.append("proposal project_intelligence must include schema_version before artifact projection")
    derivation = proposal.get(ARTIFACT_DERIVATION_KEY)
    if not isinstance(derivation, Mapping):
        issues.append("proposal artifact_derivation must declare project_intelligence as the root")
    else:
        if clean_text(derivation.get("root")) != PROJECT_INTELLIGENCE_ROOT:
            issues.append("proposal artifact_derivation.root must be project_intelligence")
        if expected_schema and clean_text(derivation.get("root_schema_version")) != expected_schema:
            issues.append("proposal artifact_derivation.root_schema_version must match project_intelligence")

    _check_mapping_binding(
        proposal.get("release_plan"),
        owner="release_plan",
        expected_schema=expected_schema,
        issues=issues,
    )
    _check_mapping_binding(
        proposal.get("program"),
        owner="program",
        expected_schema=expected_schema,
        issues=issues,
    )
    program = proposal.get("program")
    waves = program.get("waves") if isinstance(program, Mapping) else None
    _check_row_bindings(
        waves,
        owner="program wave",
        expected_schema=expected_schema,
        issues=issues,
    )
    _check_row_bindings(
        proposal.get("backlog"),
        owner="backlog row",
        expected_schema=expected_schema,
        issues=issues,
    )
    _check_row_bindings(
        proposal.get("components"),
        owner="component row",
        expected_schema=expected_schema,
        issues=issues,
    )
    _check_row_bindings(
        proposal.get("diagrams"),
        owner="diagram row",
        expected_schema=expected_schema,
        issues=issues,
    )
    return issues


def _base_binding(*, project_intelligence: Mapping[str, Any], intent: Mapping[str, Any]) -> dict[str, str]:
    return {
        "source": PROJECT_INTELLIGENCE_ROOT,
        "schema_version": clean_text(project_intelligence.get("schema_version")),
        "project_title": clean_text(intent.get("title")) or clean_text(project_intelligence.get("project_name")),
        "project_slug": clean_text(intent.get("project_slug")),
        "evidence_boundary": "derived_from_project_intelligence",
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


def _bind_program(value: Any, *, base: Mapping[str, str]) -> dict[str, Any]:
    program = _bind_mapping(value, base=base, artifact_kind="greenfield_program", artifact_id="program")
    program["waves"] = _bind_rows(program.get("waves"), base=base, artifact_kind="greenfield_program_wave")
    return program


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
    return (
        clean_text(row.get("provisional_release_id"))
        or clean_text(row.get("selector"))
        or clean_text(row.get("label"))
        or "release_plan"
    )


def _artifact_identifier(row: Mapping[str, Any], *, fallback: str) -> str:
    for key in ("id", "workstream_id", "idea_id", "component_id", "slug", "wave_id", "label", "title"):
        token = clean_text(row.get(key))
        if token:
            return token
    return fallback


def _check_mapping_binding(
    value: Any,
    *,
    owner: str,
    expected_schema: str,
    issues: list[str],
) -> None:
    if not isinstance(value, Mapping):
        issues.append(f"{owner} must be an object before project_intelligence binding can be checked")
        return
    _check_binding(value, owner=owner, expected_schema=expected_schema, issues=issues)


def _check_row_bindings(
    value: Any,
    *,
    owner: str,
    expected_schema: str,
    issues: list[str],
) -> None:
    if not isinstance(value, list) or not value:
        issues.append(f"{owner} collection must be non-empty before project_intelligence binding can be checked")
        return
    for index, row in enumerate(value, start=1):
        if not isinstance(row, Mapping):
            issues.append(f"{owner} {index} must be an object before project_intelligence binding can be checked")
            continue
        _check_binding(row, owner=f"{owner} {index}", expected_schema=expected_schema, issues=issues)


def _check_binding(
    row: Mapping[str, Any],
    *,
    owner: str,
    expected_schema: str,
    issues: list[str],
) -> None:
    binding = row.get(PROJECT_INTELLIGENCE_BINDING_KEY)
    if not isinstance(binding, Mapping):
        issues.append(f"{owner} must carry project_intelligence_binding")
        return
    if clean_text(binding.get("source")) != PROJECT_INTELLIGENCE_ROOT:
        issues.append(f"{owner} project_intelligence_binding.source must be project_intelligence")
    if expected_schema and clean_text(binding.get("schema_version")) != expected_schema:
        issues.append(f"{owner} project_intelligence_binding.schema_version must match project_intelligence")
    if not clean_text(binding.get("artifact_kind")):
        issues.append(f"{owner} project_intelligence_binding.artifact_kind must be present")
    if not clean_text(binding.get("artifact_id")):
        issues.append(f"{owner} project_intelligence_binding.artifact_id must be present")


__all__ = [
    "ARTIFACT_DERIVATION_KEY",
    "PROJECT_INTELLIGENCE_BINDING_KEY",
    "PROJECT_INTELLIGENCE_ROOT",
    "attach_project_intelligence_bindings",
    "project_intelligence_binding_issues",
]
