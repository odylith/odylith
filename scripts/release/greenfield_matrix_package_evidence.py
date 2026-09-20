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
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    decision_copy,
    provisional_proof_assumption,
    require_provisional_proof_decision,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    PROJECT_HANDOFF_STEP_SEQUENCE,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.surfaces.atlas_diagram_intelligence import parse_mermaid_graph
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
    "Component Snapshot",
    "Proposed responsibility",
    "Proposed inputs and outputs",
    "Proposed verification",
    "Source-event support",
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
    brief = package_mapping(proposal.get("project_brief"))
    return list(project_brief_readback_findings(
        record_text=str(getattr(package, "project_brief_record_text", "") or ""),
        project_brief=brief,
        intent=package_mapping(proposal.get("intent")),
    ))


def project_brief_readback_findings(
    *,
    record_text: str,
    project_brief: Mapping[str, Any],
    intent: Mapping[str, Any] | None = None,
) -> tuple[PackageEvidenceFinding, ...]:
    """Validate persisted brief text against its sealed typed brief without rendering it."""

    text = str(record_text or "").strip()
    brief = package_mapping(project_brief)
    if not text or not brief:
        return (_finding("product_manager", "independent package evidence missing persisted project brief readback"),)

    canonical_intent = package_mapping(intent)
    findings = _authored_project_brief_findings(brief, canonical_intent)
    expected_title = f"# {_brief_text(brief.get('project_name'))} Project Brief"
    if not _brief_text(brief.get("project_name")) or text.splitlines()[0:1] != [expected_title]:
        findings.append(_finding("product_manager", "persisted project brief readback is missing its typed title"))
    for marker in (
        "## Brief",
        "## Project Design Board",
        "- schema: odylith.greenfield.project_brief.v1",
        "- origin: greenfield",
    ):
        if marker not in text:
            findings.append(_finding("product_manager", f"persisted project brief readback is missing `{marker}`"))
    findings.extend(_persisted_project_brief_structure_findings(text, brief, canonical_intent))
    return _unique_findings(findings)


def _authored_project_brief_findings(
    brief: Mapping[str, Any],
    intent: Mapping[str, Any],
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
    required_labels = [
        "Source excerpt",
        "User problem",
        "First path",
    ]
    proof_label = ""
    try:
        require_provisional_proof_decision(intent)
    except ValueError:
        findings.append(_finding("product_manager", "canonical intent has an invalid exclusive proof decision"))
    else:
        proposed = bool(provisional_proof_assumption(intent.get("assumptions", [])))
        proof_label = "Proposed proof checkpoint" if proposed else "Proof"
        if proposed:
            if "Visible result" in labels:
                findings.append(
                    _finding(
                        "product_manager",
                        "proposed-proof project brief must not contain `Visible result`",
                    )
                )
            if brief.get("project_outcome") != decision_copy(intent, "proof_boundary"):
                findings.append(
                    _finding(
                        "product_manager",
                        "proposed-proof project outcome does not exactly match its canonical proof decision copy",
                    )
                )
        else:
            required_labels.append("Visible result")
    for label in required_labels:
        if label not in labels:
            findings.append(
                _finding("product_manager", f"independent project brief is missing `{label}`")
            )
    if proof_label and (
        labels.count(proof_label) != 1
        or any(label in labels for label in ({"Proof", "Proposed proof checkpoint"} - {proof_label}))
    ):
        findings.append(
            _finding("product_manager", f"independent project brief must contain exactly one `{proof_label}`")
        )
    for row in sections:
        if not normalize_string(row.get("must_capture")):
            label = normalize_string(row.get("section")) or "<unlabeled>"
            findings.append(
                _finding("product_manager", f"independent project brief section `{label}` is empty")
            )
    return findings


def _persisted_project_brief_structure_findings(
    record_text: str,
    brief: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    sections = _markdown_sections(record_text)
    findings: list[PackageEvidenceFinding] = []
    expected_brief = "\n".join((
        f"- outcome: {_brief_text(brief.get('project_outcome'))}",
        _typed_brief_fact_line(
            "Source excerpt", _brief_text(brief.get("operating_principle"))
        ),
    ))
    if sections.get("brief", "") != expected_brief:
        findings.append(
            _finding("product_manager", "persisted project brief readback does not exactly match its typed brief")
        )
    for label, value in (
        ("outcome", "project_outcome"),
        ("Source excerpt", "operating_principle"),
    ):
        expected = _typed_brief_fact_line(label, _brief_text(brief.get(value)))
        if not _brief_text(brief.get(value)) or expected not in sections.get("brief", ""):
            findings.append(_finding("product_manager", f"persisted project brief readback lost typed {label}"))
    expected_board = _typed_design_board(brief)
    if sections.get("project design board", "") != expected_board:
        findings.append(
            _finding(
                "product_manager",
                "persisted project brief readback does not exactly match its typed design board",
            )
        )
    for row in mapping_rows(brief.get("blueprint_sections")):
        label = _brief_text(row.get("section"))
        value = _brief_text(row.get("must_capture"))
        expected = _typed_brief_fact_line(label, value)
        if not label or not value or expected not in sections.get("project design board", ""):
            findings.append(
                _finding(
                    "product_manager",
                    f"persisted project brief readback lost typed `{label or 'section'}`",
                )
            )
    findings.extend(_intent_brief_custody_findings(brief, intent))
    findings.extend(_governance_package_findings(record_text, brief))
    return findings


def _typed_design_board(brief: Mapping[str, Any]) -> str:
    lines: list[str] = []
    for row in mapping_rows(brief.get("blueprint_sections")):
        label = _brief_text(row.get("section"))
        value = _brief_text(row.get("must_capture"))
        if not label or not value:
            continue
        lines.append(_typed_brief_fact_line(label, value))
        why = _brief_text(row.get("why_it_matters"))
        if why:
            lines.append(f"  - Why: {why}")
    return "\n".join(lines)


def _intent_brief_custody_findings(
    brief: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    if not intent:
        return [_finding("product_manager", "independent package evidence missing canonical intent custody")]
    try:
        require_provisional_proof_decision(intent)
        proposed = bool(provisional_proof_assumption(intent.get("assumptions", [])))
        proof = _brief_text(decision_copy(intent, "proof_boundary"))
    except ValueError:
        return [_finding("product_manager", "canonical intent has an invalid exclusive proof decision")]
    proof_label = "Proposed proof checkpoint" if proposed else "Proof"
    if not proof:
        findings.append(_finding("product_manager", "canonical intent has empty proof decision copy"))
    evidence_source = intent.get("evidence_requirements", ())
    if not isinstance(evidence_source, Sequence) or isinstance(
        evidence_source, (str, bytes, bytearray)
    ):
        findings.append(_finding("product_manager", "canonical intent has malformed `evidence_requirements`"))
        evidence = ""
    else:
        evidence = "\n".join(_brief_text(value) for value in evidence_source if _brief_text(value))
    rows = tuple(mapping_rows(brief.get("blueprint_sections")))
    for label, value, count in (
        (proof_label, proof, 1),
        ("Required evidence", evidence, 1 if evidence else 0),
    ):
        matches = tuple(row for row in rows if _brief_text(row.get("section")) == label)
        if len(matches) != count or (count and _brief_text(matches[0].get("must_capture")) != value):
            findings.append(_finding("product_manager", f"typed project brief lost canonical `{label}`"))
    return findings


def _brief_text(value: Any) -> str:
    return str(value or "").strip()


def _typed_brief_fact_line(label: str, value: str) -> str:
    return f"- {label}: “{value}”" if label == "Source excerpt" else f"- {label}: {value}"


def _governance_package_findings(record_text: str, brief: Mapping[str, Any]) -> list[PackageEvidenceFinding]:
    sections = _markdown_sections(record_text)
    expected = _typed_governance_package(brief)
    findings: list[PackageEvidenceFinding] = []
    if not expected:
        if any(key.startswith("governance package") for key in sections):
            findings.append(
                _finding("product_manager", "persisted project brief readback has stray governance package content")
            )
        return findings
    if sections.get("governance package", "") != expected:
        findings.append(
            _finding(
                "product_manager",
                "persisted project brief readback does not exactly match its typed governance package",
            )
        )
    return findings


def _typed_governance_package(brief: Mapping[str, Any]) -> str:
    gate_rows = brief.get("coding_readiness_gates", ())
    gates = (
        tuple(_brief_text(value) for value in gate_rows if _brief_text(value))
        if isinstance(gate_rows, Sequence) and not isinstance(gate_rows, (str, bytes, bytearray))
        else ()
    )
    paths = tuple(mapping_rows(brief.get("host_independent_paths")))
    lines: list[str] = []
    if gates:
        lines.append("- coding readiness gates:")
        lines.extend(f"  - {gate}" for gate in gates)
    if paths:
        lines.append("- host-independent customization paths:")
        for row in paths:
            values = tuple(_brief_text(row.get(key)) for key in ("path", "command", "works_in", "use_when"))
            if rendered := " | ".join(value for value in values if value):
                lines.append(f"  - {rendered}")
    return "\n".join(lines)


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
        sections = _markdown_sections(artifact.text)
        missing = [heading for heading in _REGISTRY_REQUIRED_SECTIONS if not sections.get(heading.casefold())]
        if missing:
            findings.append(
                _finding(
                    "engineer",
                    f"{artifact.identity} is missing or empty proposed component sections: {', '.join(missing)}",
                )
            )
    return findings


def _atlas_findings(*, artifacts: Sequence[RenderedArtifact], proposal: Mapping[str, Any]) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    diagrams = [artifact for artifact in artifacts if artifact.surface == "Atlas Mermaid"]
    diagram_rows = tuple(mapping_rows(proposal.get("diagrams")))
    expected_diagrams = len(diagram_rows)
    rows_by_name = {
        f"{normalize_string(row.get('slug'))}.mmd": row
        for row in diagram_rows
        if normalize_string(row.get("slug"))
    }
    if len(diagrams) != expected_diagrams:
        findings.append(
            _finding(
                "architect",
                "independent Atlas readback does not match the sealed diagram set: "
                f"expected {expected_diagrams}, found {len(diagrams)} artifact(s)",
            )
        )
    for artifact in diagrams:
        labels = {
            normalize_string(label).casefold()
            for label in visible_mermaid_label_quality_texts(artifact.text)
            if normalize_string(label)
        }
        diagram_row = rows_by_name.get(artifact.name, {})
        if len(labels) < 2:
            findings.append(
                _finding(
                    "architect",
                    f"{artifact.identity} does not expose two distinct typed concepts",
                )
            )
        if _has_self_nested_product_component(diagram_row):
            findings.append(
                _finding(
                    "architect",
                    f"{artifact.identity} repeats the product boundary as an identically named child component",
                )
            )
        if (
            not parse_mermaid_graph(artifact.text).edges
            and not _has_distinct_typed_containment(diagram_row)
        ):
            findings.append(
                _finding(
                    "architect",
                    f"{artifact.identity} has neither a typed edge nor a distinct containment relation",
                )
            )
    return findings


def _has_self_nested_product_component(diagram: Mapping[str, Any]) -> bool:
    if normalize_string(diagram.get("projection_origin")) != AUTHORED_PROJECTION_ORIGIN:
        return False
    boxes = tuple(mapping_rows(diagram.get("diagram_boxes")))
    product_labels = {
        normalize_string(box.get("label")).casefold()
        for box in boxes
        if normalize_string(box.get("role")).casefold() == "product boundary"
        and normalize_string(box.get("label"))
    }
    component_labels = {
        normalize_string(box.get("label")).casefold()
        for box in boxes
        if normalize_string(box.get("role")).casefold() == "product-owned component"
        and normalize_string(box.get("label"))
    }
    return bool(product_labels & component_labels)


def _has_distinct_typed_containment(diagram: Mapping[str, Any]) -> bool:
    if normalize_string(diagram.get("projection_origin")) != AUTHORED_PROJECTION_ORIGIN:
        return False
    boxes = tuple(mapping_rows(diagram.get("diagram_boxes")))
    container_labels = {
        normalize_string(box.get("label")).casefold()
        for box in boxes
        if normalize_string(box.get("role")).casefold() in {"container", "product boundary"}
        and normalize_string(box.get("label"))
    }
    child_labels = {
        normalize_string(box.get("label")).casefold()
        for box in boxes
        if normalize_string(box.get("role")).casefold() not in {"container", "product boundary"}
        and normalize_string(box.get("label"))
    }
    return any(child != container for container in container_labels for child in child_labels)


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
    "project_brief_readback_findings",
]
