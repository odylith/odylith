"""Independent package evidence checks for greenfield release scoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.artifact_quality.greenfield_project_prompt_quality import (
    project_implementation_prompt_issues,
)
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import (
    collect_rendered_package_artifacts,
)
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import package_mapping
from odylith.runtime.common.mermaid_text import visible_mermaid_label_quality_texts
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    PROJECT_HANDOFF_STEP_SEQUENCE,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from greenfield_matrix_governed_readback import governed_readback_findings


@dataclass(frozen=True)
class PackageEvidenceFinding:
    dimension: str
    message: str


_RADAR_REQUIRED_SECTIONS = (
    "## Problem",
    "## Customer",
    "## Opportunity",
    "## Product View",
    "## Success Metrics",
    "## Validation",
)
_REGISTRY_REQUIRED_SECTIONS = (
    "Source boundary",
    "Source-custodied responsibility",
    "Source-custodied owner relations",
    "Trace links",
    "Feature History",
)
def package_evidence_findings(package: Any) -> tuple[PackageEvidenceFinding, ...]:
    """Return independent readback findings that should block premium scores."""

    artifacts = collect_rendered_package_artifacts(package)
    proposal = package_mapping(getattr(package, "proposal", None))
    findings: list[PackageEvidenceFinding] = []
    findings.extend(_project_brief_findings(package=package, proposal=proposal))
    findings.extend(_radar_findings(package=package, artifacts=artifacts, proposal=proposal))
    findings.extend(_registry_findings(package=package, artifacts=artifacts, proposal=proposal))
    findings.extend(_atlas_findings(artifacts=artifacts, proposal=proposal))
    findings.extend(_next_step_findings(package))
    findings.extend(_prewrite_safety_findings(package))
    findings.extend(_project_prompt_findings(package=package, artifacts=artifacts))
    findings.extend(_governed_readback_findings(package))
    return _unique_findings(findings)


def evidence_finding_messages(findings: Sequence[PackageEvidenceFinding]) -> tuple[str, ...]:
    return tuple(unique_text(finding.message for finding in findings if finding.message.strip()))


def evidence_blocks_dimension(findings: Sequence[PackageEvidenceFinding], dimension: str) -> bool:
    return any(finding.dimension == dimension for finding in findings)


def _project_brief_findings(*, package: Any, proposal: Mapping[str, Any]) -> list[PackageEvidenceFinding]:
    raw_record_text = str(getattr(package, "project_brief_record_text", "") or "").strip()
    record_text = normalize_string(raw_record_text)
    if not raw_record_text:
        return [_finding("product_manager", "independent package evidence missing persisted project brief readback")]
    required_markers = ("# ", "## Brief", "## Project Design Board", "## Governance Package")
    missing_markers = [marker for marker in required_markers if marker not in record_text]
    if missing_markers:
        return [
            _finding(
                "product_manager",
                f"persisted project brief readback is missing required section marker(s): {', '.join(missing_markers)}",
            )
        ]
    findings = _persisted_project_brief_structure_findings(raw_record_text)
    brief = package_mapping(proposal.get("project_brief"))
    if not brief:
        findings.append(_finding("product_manager", "independent package evidence missing project brief readback"))
        return findings
    findings.extend(_authored_project_brief_findings(brief))
    return findings


def _authored_project_brief_findings(
    brief: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    """Validate the typed authored brief without reparsing its prose."""

    findings: list[PackageEvidenceFinding] = []
    if normalize_string(brief.get("schema_version")) != "odylith.greenfield.project_brief.v1":
        findings.append(
            _finding("product_manager", "independent project brief has an unsupported schema version")
        )
    if normalize_string(brief.get("projection_origin")) != AUTHORED_PROJECTION_ORIGIN:
        findings.append(
            _finding("product_manager", "independent project brief is not the sealed authored projection")
        )
    for field in ("purpose", "operating_principle", "project_outcome"):
        if not normalize_string(brief.get(field)):
            findings.append(
                _finding("product_manager", f"independent project brief is missing `{field}`")
            )
    sections = tuple(mapping_rows(brief.get("blueprint_sections")))
    labels = tuple(normalize_string(row.get("section")) for row in sections)
    required_labels = (
        "Product outcome",
        "User problem",
        "First path",
        "Visible result",
        "Proof",
    )
    for label in required_labels:
        if label not in labels:
            findings.append(
                _finding("product_manager", f"independent project brief is missing `{label}`")
            )
    for row in sections:
        if not normalize_string(row.get("must_capture")):
            label = normalize_string(row.get("section")) or "<unlabeled>"
            findings.append(
                _finding("product_manager", f"independent project brief section `{label}` is empty")
            )
    return findings


def _persisted_project_brief_structure_findings(record_text: str) -> list[PackageEvidenceFinding]:
    sections = _markdown_sections(record_text)
    brief_body = sections.get("brief", "")
    findings: list[PackageEvidenceFinding] = []
    if "- outcome:" not in brief_body.casefold() or "- principle:" not in brief_body.casefold():
        findings.append(
            _finding("product_manager", "persisted project brief readback is missing outcome or principle lines")
        )
    return findings


def _markdown_sections(record_text: str) -> dict[str, str]:
    current = ""
    sections: dict[str, list[str]] = {"": []}
    for raw_line in record_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current = normalize_string(line[3:]).casefold()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(raw_line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _radar_findings(
    *,
    package: Any,
    artifacts: Sequence[RenderedArtifact],
    proposal: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    workstreams = [artifact for artifact in artifacts if artifact.surface == "Radar workstream"]
    expected_workstreams = len(mapping_rows(proposal.get("backlog")))
    if expected_workstreams == 0:
        findings.append(
            _finding(
                "governance_depth",
                "independent Radar readback has no sealed workstream set",
            )
        )
    elif len(workstreams) != expected_workstreams:
        findings.append(
            _finding(
                "governance_depth",
                "independent Radar readback does not match the sealed workstream set: "
                f"expected {expected_workstreams}, found {len(workstreams)} artifact(s)",
            )
        )
    for artifact in workstreams:
        missing = [section for section in _RADAR_REQUIRED_SECTIONS if section not in artifact.text]
        if missing:
            findings.append(
                _finding("product_manager", f"{artifact.identity} is missing release-quality sections: {', '.join(missing)}")
            )
    backlog_result = package_mapping(getattr(package, "backlog_result", None))
    if _gate_status(package_mapping(backlog_result.get("validation_gate"))) != "passed":
        findings.append(_finding("engineer", "independent Radar readback missing passed validation gate"))
    return findings


def _registry_findings(
    *,
    package: Any,
    artifacts: Sequence[RenderedArtifact],
    proposal: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    specs = [artifact for artifact in artifacts if artifact.surface == "Registry component spec"]
    active_components = _active_components(proposal)
    if len(specs) != len(active_components):
        findings.append(
            _finding(
                "architect",
                "independent Registry readback does not match the accepted component set: "
                f"expected {len(active_components)}, found {len(specs)} component spec artifact(s)",
            )
        )
    for artifact in specs:
        missing = [phrase for phrase in _REGISTRY_REQUIRED_SECTIONS if phrase not in artifact.text]
        if missing:
            findings.append(
                _finding(
                    "engineer",
                    f"{artifact.identity} is missing authored component sections: {', '.join(missing)}",
                )
            )
    return findings


def _atlas_findings(*, artifacts: Sequence[RenderedArtifact], proposal: Mapping[str, Any]) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    diagrams = [artifact for artifact in artifacts if artifact.surface == "Atlas Mermaid"]
    expected_diagrams = len(mapping_rows(proposal.get("diagrams")))
    if len(diagrams) != expected_diagrams:
        findings.append(
            _finding(
                "architect",
                "independent Atlas readback does not match the sealed diagram set: "
                f"expected {expected_diagrams}, found {len(diagrams)} artifact(s)",
            )
        )
    for artifact in diagrams:
        labels = visible_mermaid_label_quality_texts(artifact.text)
        if len(labels) < 2:
            findings.append(_finding("architect", f"{artifact.identity} has too few visible topology labels"))
        if not any(operator in artifact.text for operator in ("-->", "-->>", ".->", "==>", "->>")):
            findings.append(_finding("architect", f"{artifact.identity} has no visible topology edge"))
    return findings


def _next_step_findings(package: Any) -> list[PackageEvidenceFinding]:
    next_steps = package_mapping(getattr(package, "source_launch_readback", None))
    if not next_steps:
        return [_finding("operator_usefulness", "independent package evidence missing persisted accepted source-launch readback")]
    findings: list[PackageEvidenceFinding] = []
    prompt = normalize_string(next_steps.get("implementation_prompt"))
    start_id = normalize_string(next_steps.get("start_workstream_id"))
    if not prompt or not start_id or start_id.upper() not in prompt.upper():
        findings.append(_finding("operator_usefulness", "operator next steps do not bind to a governed workstream"))
    return findings


def _prewrite_safety_findings(package: Any) -> list[PackageEvidenceFinding]:
    prewrite_safety = package_mapping(getattr(package, "prewrite_safety_preview", None))
    checks = package_mapping(prewrite_safety.get("checks"))
    if _gate_status(prewrite_safety) != "passed" or not checks or not all(bool(value) for value in checks.values()):
        return [_finding("engineer", "independent package evidence missing explicit prewrite safety checks")]
    return []


def _project_prompt_findings(*, package: Any, artifacts: Sequence[RenderedArtifact]) -> list[PackageEvidenceFinding]:
    prompts = [artifact for artifact in artifacts if artifact.surface == "Project implementation prompt"]
    findings: list[PackageEvidenceFinding] = []
    declared = mapping_rows(
        package_mapping(getattr(package, "project_dashboard_preview", None)).get("host_handoff_prompts")
    )
    if len(declared) != len(PROJECT_HANDOFF_STEP_SEQUENCE):
        findings.append(
            _finding(
                "implementation_prompts",
                "independent Project prompt declaration does not carry the exact typed handoff sequence: "
                f"expected {len(PROJECT_HANDOFF_STEP_SEQUENCE)}, found {len(declared)}",
            )
        )
    if len(prompts) != len(declared):
        findings.append(
            _finding(
                "implementation_prompts",
                "independent Project prompt readback does not match the sealed prompt set: "
                f"expected {len(declared)}, found {len(prompts)}",
            )
        )
    for prompt in prompts:
        findings.extend(_finding("implementation_prompts", issue) for issue in project_implementation_prompt_issues(prompt))
    return findings


def _governed_readback_findings(package: Any) -> list[PackageEvidenceFinding]:
    readback = getattr(package, "governed_readback", None)
    if readback is None:
        return [_finding("completion", "independent package evidence missing governed record readback")]
    return [
        _finding(dimension, message)
        for dimension, message in governed_readback_findings(
            readback,
            release_selector=str(getattr(package, "release_selector", "") or ""),
            release_workstream_ids=tuple(str(item) for item in getattr(package, "release_workstream_ids", ())),
            expected_radar_workstreams=len(mapping_rows(package_mapping(getattr(package, "proposal", None)).get("backlog"))),
            expected_registry_components=len(_active_components(package_mapping(getattr(package, "proposal", None)))),
            expected_atlas_diagrams=len(mapping_rows(package_mapping(getattr(package, "proposal", None)).get("diagrams"))),
        )
    ]


def _active_components(proposal: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows = tuple(mapping_rows(proposal.get("components")))
    active = tuple(
        row
        for row in rows
        if normalize_string(row.get("component_id"))
        and normalize_string(row.get("release_scope")).casefold() not in {"deferred", "external", "out_of_scope"}
    )
    return active or tuple(row for row in rows if normalize_string(row.get("component_id")))
def _gate_status(value: Mapping[str, Any]) -> str:
    return normalize_string(value.get("status")).casefold()


def _finding(dimension: str, message: str) -> PackageEvidenceFinding:
    return PackageEvidenceFinding(dimension=dimension, message=message)


def _unique_findings(findings: Sequence[PackageEvidenceFinding]) -> tuple[PackageEvidenceFinding, ...]:
    seen: set[tuple[str, str]] = set()
    result: list[PackageEvidenceFinding] = []
    for finding in findings:
        key = (finding.dimension, finding.message.casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return tuple(result)


__all__ = [
    "PackageEvidenceFinding",
    "evidence_blocks_dimension",
    "evidence_finding_messages",
    "package_evidence_findings",
]
