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
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_project_brief import project_brief_issues
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
_REGISTRY_REQUIRED_PROOF = (
    "Source boundary",
    "Trace links",
    "Successful path evidence",
    "Blocked input evidence",
    "Replay evidence",
)
_DOMAIN_READBACK_EXCLUDED_SURFACES = frozenset(
    {
        "Accepted project source launch",
    }
)
_DOMAIN_DISTRIBUTION_SURFACES = (
    ("Radar", ("Radar workstream",)),
    ("Registry", ("Registry component spec",)),
    ("Atlas", ("Atlas Mermaid",)),
    ("Project prompts", ("Project implementation prompt",)),
)
_EVALUATION_EVIDENCE_FIELDS = (
    ("method or protocol version", ("method_or_protocol",)),
    ("baseline or comparison evidence", ("reference_or_baseline",)),
    ("uncertainty or tolerance boundary", ("uncertainty_or_tolerance",)),
    ("reproducibility evidence", ("reproducibility",)),
)
_TERM_STOPWORDS = frozenset(
    {
        "accepted",
        "action",
        "artifact",
        "component",
        "complete",
        "evidence",
        "first",
        "governance",
        "greenfield",
        "implementation",
        "operator",
        "path",
        "product",
        "project",
        "proof",
        "record",
        "release",
        "review",
        "state",
        "system",
        "user",
        "workstream",
    }
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
    findings.extend(_project_prompt_findings(artifacts))
    findings.extend(_governed_readback_findings(package))
    findings.extend(_domain_readback_findings(package=package, artifacts=artifacts, proposal=proposal))
    findings.extend(_evaluation_evidence_findings(artifacts=artifacts, proposal=proposal))
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
    if word_count(record_text) < 80:
        return [_finding("product_manager", "persisted project brief readback is too shallow for release-quality review")]
    findings = _persisted_project_brief_structure_findings(raw_record_text)
    brief = package_mapping(proposal.get("project_brief"))
    if not brief:
        findings.append(_finding("product_manager", "independent package evidence missing project brief readback"))
        return findings
    findings.extend(
        _finding("product_manager", f"independent project brief evidence failed: {issue}")
        for issue in project_brief_issues(brief)
    )
    return findings


def _persisted_project_brief_structure_findings(record_text: str) -> list[PackageEvidenceFinding]:
    sections = _markdown_sections(record_text)
    brief_body = sections.get("brief", "")
    design_body = sections.get("project design board", "")
    governance_body = sections.get("governance package", "")
    findings: list[PackageEvidenceFinding] = []
    if "- outcome:" not in brief_body.casefold() or "- principle:" not in brief_body.casefold():
        findings.append(
            _finding("product_manager", "persisted project brief readback is missing outcome or principle lines")
        )
    if word_count(brief_body) < 40:
        findings.append(_finding("product_manager", "persisted project brief Brief section is too shallow"))
    if _bullet_count(design_body) < 4:
        findings.append(
            _finding("architect", "persisted project brief Project Design Board has fewer than four grounded rows")
        )
    if _bullet_count(governance_body) < 8:
        findings.append(
            _finding("engineer", "persisted project brief Governance Package has fewer than eight actionable rows")
        )
    if _section_term_overlap(brief_body, design_body, governance_body) < 3:
        findings.append(
            _finding("governance_traceability", "persisted project brief sections do not share enough semantic grounding")
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


def _bullet_count(section_text: str) -> int:
    return sum(1 for line in section_text.splitlines() if line.strip().startswith("-"))


def _section_term_overlap(*sections: str) -> int:
    term_sets = [set(_terms(section)) for section in sections if normalize_string(section)]
    if len(term_sets) < 2:
        return 0
    frequencies: dict[str, int] = {}
    for term_set in term_sets:
        for term in term_set - _TERM_STOPWORDS:
            frequencies[term] = frequencies.get(term, 0) + 1
    return sum(1 for count in frequencies.values() if count >= 2)


def _radar_findings(
    *,
    package: Any,
    artifacts: Sequence[RenderedArtifact],
    proposal: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    workstreams = [artifact for artifact in artifacts if artifact.surface == "Radar workstream"]
    if len(workstreams) < 4:
        findings.append(
            _finding("governance_depth", f"independent Radar readback has only {len(workstreams)} workstream artifact(s)")
        )
    for artifact in workstreams:
        missing = [section for section in _RADAR_REQUIRED_SECTIONS if section not in artifact.text]
        if missing:
            findings.append(
                _finding("product_manager", f"{artifact.identity} is missing release-quality sections: {', '.join(missing)}")
            )
        if word_count(artifact.text) < 80:
            findings.append(_finding("product_manager", f"{artifact.identity} is too shallow for release-quality review"))
    for index, row in enumerate(mapping_rows(proposal.get("backlog")), start=1):
        metrics = [normalize_string(item) for item in text_values(row.get("success_metrics")) if normalize_string(item)]
        if len(metrics) < 2:
            findings.append(_finding("product_manager", f"proposal backlog row {index} has fewer than two success metrics"))
            continue
        shallow = [metric for metric in metrics if word_count(metric) < 6 or len(_terms(metric)) < 3]
        if shallow:
            findings.append(_finding("product_manager", f"proposal backlog row {index} has shallow success metrics"))
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
    if len(specs) < max(3, len(active_components)):
        findings.append(
            _finding("architect", f"independent Registry readback has only {len(specs)} component spec artifact(s)")
        )
    for artifact in specs:
        missing = [phrase for phrase in _REGISTRY_REQUIRED_PROOF if phrase not in artifact.text]
        if missing:
            findings.append(_finding("engineer", f"{artifact.identity} is missing proof contract text: {', '.join(missing)}"))
        if word_count(artifact.text) < 70:
            findings.append(_finding("engineer", f"{artifact.identity} is too shallow for implementation ownership"))
    return findings


def _atlas_findings(*, artifacts: Sequence[RenderedArtifact], proposal: Mapping[str, Any]) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    diagrams = [artifact for artifact in artifacts if artifact.surface == "Atlas Mermaid"]
    if len(diagrams) < 4:
        findings.append(_finding("architect", f"independent Atlas readback has only {len(diagrams)} diagram artifact(s)"))
    source_terms = _proposal_topology_terms(proposal)
    for artifact in diagrams:
        labels = visible_mermaid_label_quality_texts(artifact.text)
        if len(labels) < 2:
            findings.append(_finding("architect", f"{artifact.identity} has too few visible topology labels"))
        if not any(operator in artifact.text for operator in ("-->", "-->>", "-.->", "==>", "->>")):
            findings.append(_finding("architect", f"{artifact.identity} has no visible topology edge"))
        label_terms = set().union(*(_terms(label) for label in labels)) if labels else set()
        if source_terms and label_terms and not (source_terms & label_terms):
            findings.append(_finding("architect", f"{artifact.identity} is not grounded in component or first-path terms"))
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
    if len(text_values(next_steps.get("verification_commands"))) < 2:
        findings.append(_finding("engineer", "operator next steps do not include at least two verification commands"))
    if len(text_values(next_steps.get("coding_readiness_gates"))) < 4:
        findings.append(_finding("engineer", "operator next steps do not include four coding-readiness gates"))
    prompts = package_mapping(getattr(package, "project_dashboard_preview", None)).get("host_handoff_prompts")
    if len(mapping_rows(prompts)) < 5:
        findings.append(_finding("operator_usefulness", "accepted Project readback does not expose five source-launch prompts"))
    return findings


def _prewrite_safety_findings(package: Any) -> list[PackageEvidenceFinding]:
    prewrite_safety = package_mapping(getattr(package, "prewrite_safety_preview", None))
    checks = package_mapping(prewrite_safety.get("checks"))
    if _gate_status(prewrite_safety) != "passed" or not checks or not all(bool(value) for value in checks.values()):
        return [_finding("engineer", "independent package evidence missing explicit prewrite safety checks")]
    return []


def _project_prompt_findings(artifacts: Sequence[RenderedArtifact]) -> list[PackageEvidenceFinding]:
    prompts = [artifact for artifact in artifacts if artifact.surface == "Project implementation prompt"]
    findings: list[PackageEvidenceFinding] = []
    if len(prompts) < 5:
        findings.append(_finding("implementation_prompts", f"independent Project readback has only {len(prompts)} prompt(s)"))
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
        )
    ]


def _domain_readback_findings(
    *,
    package: Any,
    artifacts: Sequence[RenderedArtifact],
    proposal: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    source_terms = _domain_source_terms(proposal)
    if len(source_terms) < 4:
        return [_finding("domain_expert", "semantic source has too few domain terms for independent review")]
    del package
    rendered_text = " ".join(
        artifact.text
        for artifact in artifacts
        if artifact.surface not in _DOMAIN_READBACK_EXCLUDED_SURFACES
    )
    rendered_terms = _terms(rendered_text)
    required = min(5, max(3, len(source_terms) // 4))
    if len(source_terms & rendered_terms) < required:
        return [
            _finding(
                "domain_expert",
                f"independent domain readback carried {len(source_terms & rendered_terms)} of {required} required semantic terms",
            )
        ]
    return _domain_surface_distribution_findings(artifacts=artifacts, source_terms=source_terms)


def _domain_surface_distribution_findings(
    *,
    artifacts: Sequence[RenderedArtifact],
    source_terms: set[str],
) -> list[PackageEvidenceFinding]:
    findings: list[PackageEvidenceFinding] = []
    required = min(2, len(source_terms))
    for label, surfaces in _DOMAIN_DISTRIBUTION_SURFACES:
        surface_artifacts = [artifact for artifact in artifacts if artifact.surface in surfaces]
        if not surface_artifacts:
            continue
        surface_terms = _terms(" ".join(artifact.text for artifact in surface_artifacts))
        carried = len(source_terms & surface_terms)
        if carried < required:
            findings.append(
                _finding(
                    "domain_expert",
                    f"independent domain readback carried only {carried} of {required} semantic terms on {label}",
                )
            )
    return findings


def _evaluation_evidence_findings(
    *,
    artifacts: Sequence[RenderedArtifact],
    proposal: Mapping[str, Any],
) -> list[PackageEvidenceFinding]:
    semantic = package_mapping(proposal.get("semantic_model"))
    evaluation = package_mapping(semantic.get("evaluation_semantics"))
    if not evaluation:
        return []
    rendered_text = normalize_string(
        " ".join(
            artifact.text
            for artifact in artifacts
            if artifact.surface not in _DOMAIN_READBACK_EXCLUDED_SURFACES
        )
    )
    rendered_terms = _terms(rendered_text)
    obligation_terms = _evaluation_obligation_terms(evaluation)
    missing = [
        label
        for label, required_terms in obligation_terms.items()
        if not required_terms or not (required_terms & rendered_terms)
    ]
    if not missing:
        return []
    return [
        _finding(
            "domain_expert",
            "scientific/evaluation readback missing evidence obligation(s): " + ", ".join(missing),
        )
    ]


def _evaluation_obligation_terms(evaluation: Mapping[str, Any]) -> dict[str, set[str]]:
    raw_terms: dict[str, set[str]] = {}
    for label, fields in _EVALUATION_EVIDENCE_FIELDS:
        raw_terms[label] = _terms(" ".join(text_values(tuple(evaluation.get(field) for field in fields))))
    result: dict[str, set[str]] = {}
    for label, terms in raw_terms.items():
        sibling_terms: set[str] = set()
        for sibling_label, sibling in raw_terms.items():
            if sibling_label != label:
                sibling_terms.update(sibling)
        result[label] = terms - sibling_terms or terms
    return result


def _active_components(proposal: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows = tuple(mapping_rows(proposal.get("components")))
    active = tuple(
        row
        for row in rows
        if normalize_string(row.get("component_id"))
        and normalize_string(row.get("release_scope")).casefold() not in {"deferred", "external", "out_of_scope"}
    )
    return active or tuple(row for row in rows if normalize_string(row.get("component_id")))


def _proposal_topology_terms(proposal: Mapping[str, Any]) -> set[str]:
    semantic = package_mapping(proposal.get("semantic_model"))
    first_path = package_mapping(semantic.get("first_path_contract"))
    return _terms(
        " ".join(
            text_values(
                [
                    proposal.get("components"),
                    first_path.get("capability"),
                    first_path.get("visible_result"),
                ]
            )
        )
    )


def _domain_source_terms(proposal: Mapping[str, Any]) -> set[str]:
    intent = package_mapping(proposal.get("intent"))
    semantic = package_mapping(proposal.get("semantic_model"))
    first_path = package_mapping(semantic.get("first_path_contract"))
    domain = package_mapping(semantic.get("domain_ontology"))
    return _terms(
        " ".join(
            text_values(
                [
                    intent.get("state_object"),
                    first_path.get("capability"),
                    first_path.get("visible_result"),
                    domain.get("proof_boundary"),
                    domain.get("external_systems"),
                    domain.get("internal_systems"),
                ]
            )
        )
    )


def _terms(value: str) -> set[str]:
    return set(
        ordered_terms(
            value,
            stopwords=_TERM_STOPWORDS,
            minimum=4,
            preserve_terms={"ai", "api", "ev", "glp", "ml", "sms", "ui", "ux"},
            stem_ing=True,
            stem_ing_minimum_length=5,
        )
    )


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
