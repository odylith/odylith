"""Confirmed artifact substance checks for the greenfield Tribunal."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import text_values


_SUBSTANCE_TERM_STOPWORDS = {
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

_ATLAS_ACTION_ALIASES = {
    "adds": "add",
    "approves": "approve",
    "blocks": "block",
    "checks": "check",
    "compares": "compare",
    "creates": "create",
    "displays": "display",
    "enters": "enter",
    "exports": "export",
    "imports": "import",
    "logs": "log",
    "opens": "open",
    "publishes": "publish",
    "reads": "read",
    "records": "record",
    "reviews": "review",
    "saves": "save",
    "sees": "see",
    "shows": "show",
    "submits": "submit",
    "traces": "trace",
    "views": "view",
}
_ATLAS_ACTION_ROOTS = frozenset(_ATLAS_ACTION_ALIASES.values())


def check_confirmed_artifact_substance(
    *,
    proposal: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    issues: list[str],
) -> None:
    """Fail confirmed proposals whose generated artifacts are too thin or generic."""

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
        components=components,
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
    components: Sequence[Mapping[str, Any]],
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
                components=components,
                title=title,
                source=source,
                issues=issues,
            )
        if title == "First Path Sequence" and source.lstrip().startswith("flowchart"):
            _check_first_path_flowchart(
                proposal=proposal,
                components=components,
                title=title,
                source=source,
                issues=issues,
            )


def _check_first_path_flowchart(
    *,
    proposal: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
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
        components=components,
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
    tail_terms = _atlas_tail_term_set(tail)
    if not tail_terms:
        return
    source_terms = _atlas_tail_term_set(source)
    required_tail_hits = min(2, len(tail_terms))
    if len(tail_terms & source_terms) < required_tail_hits:
        issues.append(f"confirmed Atlas {kind} `{title}` omits the tail of the accepted first path")


def _check_sequence_starts_at_first_boundary(
    *,
    components: Sequence[Mapping[str, Any]],
    title: str,
    source: str,
    issues: list[str],
) -> None:
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
    components: Sequence[Mapping[str, Any]],
    title: str,
    source: str,
    issues: list[str],
) -> None:
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
    return set(ordered_terms(value, stopwords=_SUBSTANCE_TERM_STOPWORDS, stem_ing=True))


def _atlas_tail_term_set(value: str) -> set[str]:
    terms = set(_term_set(value))
    for token in ordered_terms(value, minimum=3, stem_ing=True):
        action = _ATLAS_ACTION_ALIASES.get(token, token)
        if action in _ATLAS_ACTION_ROOTS:
            terms.add(action)
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


__all__ = ["check_confirmed_artifact_substance"]
