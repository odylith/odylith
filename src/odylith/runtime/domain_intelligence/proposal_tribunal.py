"""Deterministic Tribunal gate for confirmed greenfield proposals.

The host model authors open-world project reasoning. Odylith's job is to keep
the write path governed: fail before source-truth writes when the proposal does
not form a coherent workstream/component/diagram/program/release topology.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.artifact_enrichment import tribunal_actor_projection
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_text import collect_text_values
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token
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
    issues.extend(f"quality gate: {issue}" for issue in greenfield_quality_issues(proposal))
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

    _check_confirmed_artifact_substance(
        proposal=proposal,
        backlog=backlog,
        components=components,
        diagrams=diagrams,
        issues=issues,
    )
    dimensions["artifact_substance"] = "confirmed Radar, Registry, and Atlas records carry product-specific substance"

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


def _check_confirmed_artifact_substance(
    *,
    proposal: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    issues: list[str],
) -> None:
    if not _is_confirmed_generated_proposal(proposal):
        return
    project_terms = _project_terms(proposal)
    component_label_terms = _term_set(" ".join(str(row.get("label", "")) for row in components))
    required_terms = project_terms | component_label_terms
    _check_confirmed_radar_substance(
        backlog=backlog,
        required_terms=required_terms,
        accepted_text=_accepted_public_text(proposal),
        issues=issues,
    )
    _check_confirmed_registry_substance(components=components, issues=issues)
    _check_confirmed_atlas_substance(
        proposal=proposal,
        diagrams=diagrams,
        required_terms=required_terms,
        issues=issues,
    )


def _is_confirmed_generated_proposal(proposal: Mapping[str, Any]) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return str(intent.get("reasoning_mode", "")).strip() == "odylith_confirmed_governed_proposal"


def _check_confirmed_radar_substance(
    *,
    backlog: Sequence[Mapping[str, Any]],
    required_terms: set[str],
    accepted_text: str,
    issues: list[str],
) -> None:
    for index, row in enumerate(backlog, start=1):
        title = str(row.get("title", f"row {index}")).strip() or f"row {index}"
        body = _joined_fields(
            row,
            "problem",
            "customer",
            "opportunity",
            "product_view",
            "recommended_first_slice",
            "success_metrics",
            "dependencies",
            "interfaces",
            "validation",
        )
        local_terms = _term_set(body)
        if index > 1 and len(local_terms) < 14:
            issues.append(f"confirmed Radar workstream `{title}` is too thin to guide implementation")
        if index > 1 and required_terms and len(local_terms & required_terms) < 4:
            issues.append(f"confirmed Radar workstream `{title}` is not anchored to enough project-specific nouns")
        if _repeated_scaffold_count(body, accepted_text=accepted_text) >= 6:
            issues.append(f"confirmed Radar workstream `{title}` repeats scaffold language instead of adding new product detail")
        metrics = [text for text in text_values(row.get("success_metrics")) if str(text).strip()]
        if index > 1 and len({_normalized_text(metric) for metric in metrics}) < min(2, len(metrics)):
            issues.append(f"confirmed Radar workstream `{title}` repeats success metrics")


def _check_confirmed_registry_substance(
    *,
    components: Sequence[Mapping[str, Any]],
    issues: list[str],
) -> None:
    for index, row in enumerate(components, start=1):
        label = str(row.get("label", "") or row.get("component_id", "") or f"component {index}").strip()
        contract = row.get("component_contract")
        if not isinstance(contract, Mapping):
            issues.append(f"confirmed Registry component `{label}` is missing component_contract")
            continue
        contract_text = _joined_fields(
            contract,
            "owned_state",
            "accepted_inputs",
            "produced_outputs",
            "states_or_transitions",
            "outside_boundary",
            "local_proof",
            "upstream_truth",
            "downstream_consumers",
            "unique_failure",
        )
        if len(_term_set(contract_text)) < 12:
            issues.append(f"confirmed Registry component `{label}` contract is too thin to guide implementation")
        proofs = [text for text in text_values(contract.get("local_proof")) if str(text).strip()]
        if len(proofs) < 3:
            issues.append(f"confirmed Registry component `{label}` must carry at least three local proof obligations")
        if len({_normalized_text(proof) for proof in proofs}) != len(proofs):
            issues.append(f"confirmed Registry component `{label}` repeats local proof obligations")
        label_text = label.casefold()
        owned_text = " ".join(text_values(contract.get("owned_state"))).casefold()
        if re.search(r"\b(surface|screen|view|dashboard|display|presentation|portal|ui|client)\b", label_text) and re.search(
            r"\b(ranking rule|calculation rule|cost rule|model rule|source truth)\b",
            owned_text,
        ):
            issues.append(
                f"confirmed Registry component `{label}` is a presentation boundary but owns computation or source-truth state"
            )
        contract_lower = contract_text.casefold()
        ownership_context = _joined_fields(
            contract,
            "owned_state",
            "accepted_inputs",
            "produced_outputs",
            "states_or_transitions",
            "outside_boundary",
            "upstream_truth",
            "downstream_consumers",
            "unique_failure",
        ).casefold()
        label_and_contract = f"{label_text} {ownership_context}"
        lifecycle_proof_terms = _proof_anchor_terms(contract_lower, proof_phrase="lifecycle proof")
        if lifecycle_proof_terms and not (lifecycle_proof_terms & _term_set(label_and_contract)):
            issues.append(f"confirmed Registry component `{label}` uses lifecycle proof outside its ownership boundary")
        if "privacy lifecycle proof" in contract_lower and not re.search(
            r"\b(privacy|consent|retention|deletion|delete|export|protected|access)\b",
            label_and_contract,
        ):
            issues.append(
                f"confirmed Registry component `{label}` uses privacy lifecycle proof for a non-privacy ownership boundary"
            )
        non_question_context = re.sub(r"\bquestion\s+list\b", "", label_and_contract)
        if "question list" in contract_lower and not re.search(
            r"\b(question|questions|issue|issues|response|answer|follow-up|followup)\b",
            non_question_context,
        ):
            issues.append(
                f"confirmed Registry component `{label}` imports question-tracking state without a question or response boundary"
            )


def _check_confirmed_atlas_substance(
    *,
    proposal: Mapping[str, Any],
    diagrams: Sequence[Mapping[str, Any]],
    required_terms: set[str],
    issues: list[str],
) -> None:
    banned_nodes = (
        "Accepted<br/>user action",
        "Reviewer can trace<br/>claim to source",
        "Reviewer decision<br/>accept, revise, or block",
        "Release claim<br/>can move forward",
    )
    for index, row in enumerate(diagrams, start=1):
        title = str(row.get("title", "") or row.get("slug", "") or f"diagram {index}").strip()
        text = _joined_fields(row, "summary", "read_guide", "mermaid_source")
        terms = _term_set(text)
        if required_terms and len(terms & required_terms) < 4:
            issues.append(f"confirmed Atlas diagram `{title}` is not anchored to enough project-specific nouns")
        source = str(row.get("mermaid_source", "") or "")
        if any(node in source for node in banned_nodes):
            issues.append(f"confirmed Atlas diagram `{title}` still contains generic scaffold nodes")
        if source.lstrip().startswith("sequenceDiagram") and source.count("->>") < 3:
            issues.append(f"confirmed Atlas sequence diagram `{title}` collapses the first path into too few events")
        if source.lstrip().startswith("sequenceDiagram"):
            _check_sequence_preserves_first_path_tail(
                proposal=proposal,
                title=title,
                source=source,
                issues=issues,
            )
            _check_sequence_starts_at_first_boundary(
                proposal=proposal,
                title=title,
                source=source,
                issues=issues,
            )
        if title == "First Path Sequence" and source.lstrip().startswith("flowchart"):
            _check_first_path_flowchart(
                proposal=proposal,
                title=title,
                source=source,
                issues=issues,
            )


def _check_first_path_flowchart(
    *,
    proposal: Mapping[str, Any],
    title: str,
    source: str,
    issues: list[str],
) -> None:
    step_count = len(re.findall(r"\bS\d+\[\"", source))
    if step_count < 3:
        issues.append(f"confirmed Atlas flowchart `{title}` collapses the first path into too few events")
    if "C4-" in source or re.search(r"\bparticipant\b", source, re.IGNORECASE):
        issues.append(f"confirmed Atlas flowchart `{title}` contains sequence/parser debris")
    if re.search(r"\bDone means\b|parser debris|accepted user action", source, re.IGNORECASE):
        issues.append(f"confirmed Atlas flowchart `{title}` contains mechanical parser copy")
    _check_atlas_source_preserves_first_path_tail(
        proposal=proposal,
        title=title,
        source=source,
        kind="flowchart",
        issues=issues,
    )
    _check_flowchart_starts_at_first_boundary(
        proposal=proposal,
        title=title,
        source=source,
        issues=issues,
    )


def _check_sequence_preserves_first_path_tail(
    *,
    proposal: Mapping[str, Any],
    title: str,
    source: str,
    issues: list[str],
) -> None:
    _check_atlas_source_preserves_first_path_tail(
        proposal=proposal,
        title=title,
        source=source,
        kind="sequence diagram",
        issues=issues,
    )


def _check_atlas_source_preserves_first_path_tail(
    *,
    proposal: Mapping[str, Any],
    title: str,
    source: str,
    kind: str,
    issues: list[str],
) -> None:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    first_path = " ".join(text_values(intent.get("first_path")))
    if not first_path:
        return
    final_clause = re.split(r",\s+and\s+|;\s+and\s+|[.!?]\s+", first_path.strip(" ."))[-1]
    tail = final_clause if len(_term_set(final_clause)) >= 2 else " ".join(first_path.split()[max(0, len(first_path.split()) - 18) :])
    tail_terms = _term_set(tail)
    if not tail_terms:
        return
    source_terms = _term_set(source)
    required_tail_hits = min(2, len(tail_terms))
    if len(tail_terms & source_terms) < required_tail_hits:
        issues.append(f"confirmed Atlas {kind} `{title}` omits the tail of the accepted first path")


def _check_sequence_starts_at_first_boundary(
    *,
    proposal: Mapping[str, Any],
    title: str,
    source: str,
    issues: list[str],
) -> None:
    components = _mapping_rows(proposal.get("components"))
    if not components:
        return
    first_component = str(components[0].get("label", "") or components[0].get("component_id", "")).casefold()
    if not re.search(r"\b(intake|import|capture|request|signal|submission|adapter|entry)\b", first_component):
        return
    first_arrow = re.search(r"\bA\d+->>C(?P<target>\d+):\s*(?P<message>.+)", source)
    if not first_arrow:
        return
    message = first_arrow.group("message").casefold()
    if first_arrow.group("target") != "1" and re.search(
        r"\b(open|opens|import|imports|enter|enters|submit|submits|request|requests|capture|captures)\b",
        message,
    ):
        issues.append(f"confirmed Atlas sequence diagram `{title}` routes the first material path action away from the first boundary")


def _check_flowchart_starts_at_first_boundary(
    *,
    proposal: Mapping[str, Any],
    title: str,
    source: str,
    issues: list[str],
) -> None:
    components = _mapping_rows(proposal.get("components"))
    if not components:
        return
    first_component = str(components[0].get("label", "") or components[0].get("component_id", "")).casefold()
    if not re.search(r"\b(intake|import|capture|request|signal|submission|adapter|entry|application)\b", first_component):
        return
    first_step = re.search(r'\bS1\["(?P<label>[^"]+)"\]\s*\n\s*S1\s+-->\s+C(?P<target>\d+)', source)
    if not first_step:
        return
    label = first_step.group("label").replace("<br/>", " ").casefold()
    if first_step.group("target") != "1" and re.search(
        r"\b(open|import|enter|submit|request|capture|select|record|log)\b",
        label,
    ):
        issues.append(f"confirmed Atlas flowchart `{title}` routes the first material path action away from the first boundary")


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
    normalized = [label.casefold() for label in labels if label]
    repeated = sorted({label for label in normalized if normalized.count(label) > 1})
    if repeated:
        issues.append(
            "Tribunal visible actors must distinguish stable judgment roles instead of reusing one label: "
            + ", ".join(repeated)
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


def _project_terms(proposal: Mapping[str, Any]) -> set[str]:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    project = proposal.get("project_intelligence") if isinstance(proposal.get("project_intelligence"), Mapping) else {}
    text = " ".join(
        [
            *text_values(intent.get("title")),
            *text_values(intent.get("product_story")),
            *text_values(intent.get("first_path")),
            *text_values(intent.get("proof_boundary")),
            *text_values(project.get("intent")),
            *text_values(project.get("ontology")),
            *text_values(project.get("evidence")),
        ]
    )
    return _term_set(text)


def _joined_fields(row: Mapping[str, Any], *keys: str) -> str:
    return " ".join(text for key in keys for text in text_values(row.get(key)) if str(text).strip())


def _proof_anchor_terms(value: str, *, proof_phrase: str) -> set[str]:
    index = value.find(proof_phrase)
    if index < 0:
        return set()
    prefix = value[max(0, index - 80) : index]
    return _term_set(prefix)


def _term_set(value: str) -> set[str]:
    stop = {
        "accepted",
        "actor",
        "after",
        "before",
        "blocked",
        "boundary",
        "candidate",
        "component",
        "context",
        "decision",
        "downstream",
        "evidence",
        "first",
        "greenfield",
        "handoff",
        "input",
        "local",
        "output",
        "owned",
        "owner",
        "path",
        "product",
        "proof",
        "record",
        "release",
        "review",
        "reviewer",
        "source",
        "state",
        "system",
        "trusted",
        "upstream",
        "validation",
        "visible",
        "workstream",
    }
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", str(value or "").casefold()):
        token = normalize_domain_token(raw, stopwords=stop)
        if token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        if token:
            terms.add(token)
    return terms


def _accepted_public_text(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return " ".join(
        text_values(
            [
                intent.get("product_story"),
                intent.get("state_object"),
                intent.get("first_path"),
                intent.get("proof_boundary"),
                intent.get("human_actors"),
                intent.get("internal_systems"),
                intent.get("external_systems"),
            ]
        )
    ).casefold()


def _repeated_scaffold_count(text: str, *, accepted_text: str = "") -> int:
    lowered = str(text or "").casefold()
    accepted_terms = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", accepted_text.casefold()))
    product_phrases = {"evidence record", "reviewer decision"}
    return sum(
        lowered.count(phrase)
        for phrase in (
            "state object",
            "evidence record",
            "reviewer decision",
            "adjacent responsibilities",
        )
        if phrase not in accepted_text
        and not (phrase in product_phrases and set(phrase.split()) <= accepted_terms)
    )


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip(" .")


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
