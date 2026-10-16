"""Rendered greenfield artifact inventory and repair-path metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from odylith.runtime.common.mermaid_text import visible_mermaid_label_quality_texts
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values


@dataclass(frozen=True)
class ArtifactQualityUnit:
    projection_id: str
    surface: str
    source_path: str
    surface_role: str
    text_kind: str
    text: str
    semantic_node_id: str | None = None


@dataclass(frozen=True)
class RenderedArtifact:
    surface: str
    name: str
    text: str
    projection_id: str = "artifact_draft_set"
    repair_path: str = "prewrite_package.artifact_draft_set.copy_quality"
    kind: str = "prose"
    fields: Mapping[str, str] = field(default_factory=dict)
    contract: Mapping[str, Any] = field(default_factory=dict)
    semantic_node_id: str | None = None

    @property
    def identity(self) -> str:
        return f"{self.surface} `{self.name}`"


@dataclass(frozen=True)
class RenderedPackageQualityFinding:
    message: str
    projection_id: str
    target_path: str
    code: str = ""
    surface: str = ""
    semantic_node_id: str = ""
    severity: str = ""
    repairability: str = ""
    owner: str = ""
    source: str = ""
    sample: str = ""
    occurrence_count: int = 0
    artifact_count: int = 0
    occurrence_paths: tuple[str, ...] = ()
    occurrence_projections: tuple[str, ...] = ()
    occurrence_surfaces: tuple[str, ...] = ()


def collect_rendered_package_artifacts(package: Any) -> list[RenderedArtifact]:
    artifacts: list[RenderedArtifact] = []
    proposal = package_mapping(getattr(package, "proposal", None))
    typed_handoff = proposal.get("projection_origin") == AUTHORED_PROJECTION_ORIGIN
    backlog_result = package_mapping(getattr(package, "backlog_result", None))
    for path, text in package_mapping(backlog_result.get("idea_files")).items():
        name = _artifact_name(path)
        artifacts.append(
            RenderedArtifact(
                "Radar workstream",
                name,
                str(text or ""),
                "radar",
                f"prewrite_package.backlog_result.idea_files::{name}",
            )
        )
    index_text = normalize_string(backlog_result.get("backlog_index_text"))
    if index_text:
        artifacts.append(
            RenderedArtifact(
                "Radar index",
                "INDEX.md",
                index_text,
                "radar",
                "prewrite_package.backlog_result.backlog_index_text",
            )
        )

    for name, text in package_mapping(getattr(package, "rendered_component_specs", None)).items():
        artifact_name = _artifact_name(name)
        artifacts.append(
            RenderedArtifact(
                "Registry component spec",
                artifact_name,
                str(text or ""),
                "registry",
                f"prewrite_package.rendered_component_specs::{artifact_name}",
            )
        )

    for path, source in package_mapping(getattr(package, "rendered_atlas_sources", None)).items():
        name = _artifact_name(path)
        artifacts.append(
            RenderedArtifact(
                "Atlas Mermaid",
                name,
                str(source or ""),
                "atlas",
                f"prewrite_package.rendered_atlas_sources::{name}",
                kind="mermaid",
            )
        )

    project_brief_record_text = getattr(package, "project_brief_record_text", "")
    project_brief = str(project_brief_record_text or "")
    project_brief_name = "project-brief.v1.md"
    project_brief_path = "prewrite_package.project_brief_readback"
    if not normalize_string(project_brief):
        project_brief = _preview_text(getattr(package, "project_brief_preview", None))
        project_brief_name = "project_brief"
        project_brief_path = "prewrite_package.project_brief_preview"
    if project_brief:
        artifacts.append(
            RenderedArtifact(
                "Project brief",
                project_brief_name,
                project_brief,
                "project_brief",
                project_brief_path,
            )
        )

    next_steps = _preview_text(getattr(package, "next_steps_preview", None))
    if next_steps:
        artifacts.append(
            RenderedArtifact(
                "Operator next steps",
                "next_steps",
                next_steps,
                "next_steps",
                "prewrite_package.next_steps_preview",
                kind="typed_handoff" if typed_handoff else "prose",
            )
        )

    accepted_project = package_mapping(getattr(package, "accepted_project_preview", None))
    source_launch = package_mapping(accepted_project.get("source_launch"))
    if not source_launch:
        source_launch = package_mapping(getattr(package, "source_launch_readback", None))
    source_launch_prompt = normalize_string(source_launch.get("implementation_prompt"))
    if source_launch_prompt:
        artifacts.append(
            RenderedArtifact(
                "Accepted project source launch",
                "implementation_prompt",
                source_launch_prompt,
                "accepted_project",
                "prewrite_package.accepted_project_preview.source_launch.implementation_prompt",
                fields={"implementation_prompt": source_launch_prompt},
            )
        )

    artifacts.extend(
        _project_handoff_prompt_artifacts(
            getattr(package, "project_dashboard_preview", None),
            typed_handoff=typed_handoff,
        )
    )
    return artifacts


def artifact_quality_finding(artifact: RenderedArtifact, issue: str) -> RenderedPackageQualityFinding:
    return RenderedPackageQualityFinding(
        message=issue,
        projection_id=artifact.projection_id,
        target_path=artifact.repair_path,
    )


def package_quality_finding(
    issue: str,
    *,
    projection_id: str = "artifact_draft_set",
    target_path: str = "prewrite_package.package.copy_quality",
    code: str = "",
    surface: str = "",
    semantic_node_id: str = "",
    severity: str = "",
    repairability: str = "",
    owner: str = "",
    source: str = "",
    sample: str = "",
    occurrence_count: int = 0,
    artifact_count: int = 0,
    occurrence_paths: tuple[str, ...] = (),
    occurrence_projections: tuple[str, ...] = (),
    occurrence_surfaces: tuple[str, ...] = (),
) -> RenderedPackageQualityFinding:
    return RenderedPackageQualityFinding(
        message=issue,
        projection_id=projection_id,
        target_path=target_path,
        code=code,
        surface=surface,
        semantic_node_id=semantic_node_id,
        severity=severity,
        repairability=repairability,
        owner=owner,
        source=source,
        sample=sample,
        occurrence_count=occurrence_count,
        artifact_count=artifact_count,
        occurrence_paths=occurrence_paths,
        occurrence_projections=occurrence_projections,
        occurrence_surfaces=occurrence_surfaces,
    )


def artifact_quality_units(artifact: RenderedArtifact) -> tuple[ArtifactQualityUnit, ...]:
    """Return typed text units without flattening surface structure prematurely."""

    if artifact.kind == "mermaid":
        return tuple(
            _quality_unit(
                artifact,
                text=label,
                text_kind="mermaid_label",
                surface_role="label",
                source_path=f"{artifact.repair_path}.label[{index}]",
            )
            for index, label in enumerate(visible_mermaid_label_quality_texts(artifact.text))
            if normalize_string(label)
        )
    if artifact.fields:
        units: list[ArtifactQualityUnit] = []
        for key, value in artifact.fields.items():
            text = normalize_string(value)
            if not text:
                continue
            units.append(
                _quality_unit(
                    artifact,
                    text=text,
                    text_kind=_field_text_kind(str(key)),
                    surface_role=str(key),
                    source_path=f"{artifact.repair_path}.{key}",
                )
            )
        return tuple(units)
    text = normalize_string(artifact.text)
    if not text:
        return ()
    return (
        _quality_unit(
            artifact,
            text=text,
            text_kind="free_prose",
            surface_role="body",
            source_path=artifact.repair_path,
        ),
    )


def _quality_unit(
    artifact: RenderedArtifact,
    *,
    text: str,
    text_kind: str,
    surface_role: str,
    source_path: str,
) -> ArtifactQualityUnit:
    return ArtifactQualityUnit(
        projection_id=artifact.projection_id,
        surface=artifact.surface,
        source_path=source_path,
        surface_role=surface_role,
        text_kind=text_kind,
        text=text,
        semantic_node_id=artifact.semantic_node_id,
    )


def _field_text_kind(key: str) -> str:
    normalized = key.casefold().strip()
    if normalized in {"command", "commands", "verification_commands"}:
        return "command"
    if normalized in {"id", "key", "label", "position", "schema_version", "status", "version"}:
        return "metadata"
    if normalized in {"prompt", "result", "stop", "when", "implementation_prompt"}:
        return "prompt_field"
    return "semantic_fact"


def unique_package_quality_findings(
    findings: Sequence[RenderedPackageQualityFinding],
) -> list[RenderedPackageQualityFinding]:
    seen: set[str] = set()
    result: list[RenderedPackageQualityFinding] = []
    for finding in findings:
        key = "|".join((finding.message.casefold(), finding.projection_id, finding.target_path))
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def package_mapping(value: Any) -> Mapping[Any, Any]:
    return value if isinstance(value, Mapping) else {}


def _project_handoff_prompt_artifacts(
    value: Any,
    *,
    typed_handoff: bool,
) -> list[RenderedArtifact]:
    project = package_mapping(value)
    rows = _mapping_rows(project.get("host_handoff_prompts"))
    artifacts: list[RenderedArtifact] = []
    for index, row in enumerate(rows, start=1):
        fields = {key: _handoff_prompt_field(row, key) for key in ("label", "step_id", "when", "prompt", "result", "stop")}
        fields["position"] = str(index)
        label = fields.get("label") or f"Prompt {index}"
        text = "\n".join(f"{key}: {fields[key]}" for key in ("label", "when", "prompt", "result", "stop") if fields.get(key))
        artifacts.append(
            RenderedArtifact(
                "Project implementation prompt",
                label,
                text,
                "project_dashboard",
                f"prewrite_package.project_dashboard_preview.host_handoff_prompts[{index - 1}]",
                kind="typed_handoff" if typed_handoff else "prose",
                fields=fields,
                contract=package_mapping(row.get("contract")),
            )
        )
    return artifacts


def _handoff_prompt_field(row: Mapping[str, Any], key: str) -> str:
    if key == "step_id":
        return normalize_string(row.get("step_id") or row.get("id") or row.get("kind"))
    if key == "stop":
        return normalize_string(row.get("stop") or row.get("stop_condition"))
    return normalize_string(row.get(key))


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _artifact_name(value: Any) -> str:
    text = normalize_string(value)
    return text or "artifact"


def _preview_text(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    rows = [normalize_string(row).strip() for row in text_values(value)]
    bounded = [row if not row or row[-1] in ".!?" else f"{row}." for row in rows if row]
    return "\n".join(bounded)


__all__ = [
    "ArtifactQualityUnit",
    "RenderedArtifact",
    "RenderedPackageQualityFinding",
    "artifact_quality_finding",
    "artifact_quality_units",
    "collect_rendered_package_artifacts",
    "package_mapping",
    "package_quality_finding",
    "unique_package_quality_findings",
]
