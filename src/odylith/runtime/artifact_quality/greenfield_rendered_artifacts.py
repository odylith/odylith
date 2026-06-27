"""Rendered greenfield artifact inventory and repair-path metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_text import text_values


@dataclass(frozen=True)
class RenderedArtifact:
    surface: str
    name: str
    text: str
    projection_id: str = "artifact_draft_set"
    repair_path: str = "prewrite_package.artifact_draft_set.copy_quality"
    kind: str = "prose"
    fields: Mapping[str, str] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        return f"{self.surface} `{self.name}`"


@dataclass(frozen=True)
class RenderedPackageQualityFinding:
    message: str
    projection_id: str
    target_path: str


def collect_rendered_package_artifacts(package: Any) -> list[RenderedArtifact]:
    artifacts: list[RenderedArtifact] = []
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

    project_brief = _preview_text(getattr(package, "project_brief_preview", None))
    if project_brief:
        artifacts.append(
            RenderedArtifact(
                "Project brief preview",
                "project_brief",
                project_brief,
                "project_brief",
                "prewrite_package.project_brief_preview",
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
            )
        )

    artifacts.extend(_project_handoff_prompt_artifacts(getattr(package, "project_dashboard_preview", None)))
    return artifacts


def artifact_quality_finding(artifact: RenderedArtifact, issue: str) -> RenderedPackageQualityFinding:
    return RenderedPackageQualityFinding(
        message=issue,
        projection_id=artifact.projection_id,
        target_path=artifact.repair_path,
    )


def package_quality_finding(issue: str) -> RenderedPackageQualityFinding:
    return RenderedPackageQualityFinding(
        message=issue,
        projection_id="artifact_draft_set",
        target_path="prewrite_package.package.copy_quality",
    )


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


def _project_handoff_prompt_artifacts(value: Any) -> list[RenderedArtifact]:
    project = package_mapping(value)
    rows = _mapping_rows(project.get("host_handoff_prompts"))
    artifacts: list[RenderedArtifact] = []
    for index, row in enumerate(rows, start=1):
        fields = {key: _handoff_prompt_field(row, key) for key in ("label", "when", "prompt", "result", "stop")}
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
                fields=fields,
            )
        )
    return artifacts


def _handoff_prompt_field(row: Mapping[str, Any], key: str) -> str:
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
    "RenderedArtifact",
    "RenderedPackageQualityFinding",
    "artifact_quality_finding",
    "collect_rendered_package_artifacts",
    "package_mapping",
    "package_quality_finding",
    "unique_package_quality_findings",
]
