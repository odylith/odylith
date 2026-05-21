"""Source-derived narration helpers for Project intelligence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from odylith.runtime.project_intelligence.summary import action_sentence, concise_text
from odylith.runtime.project_intelligence.utils import humanize, sentence


def primary_lens(
    root_component: Mapping[str, object],
    *,
    fallback: str,
    components: Sequence[Mapping[str, object]] = (),
) -> str:
    """Return the human-facing project type from source-owned component metadata."""

    source = _lens_source(root_component=root_component, components=components)
    explicit = root_component.get("primary_lens") or root_component.get("domain_lens")
    if explicit:
        return _clean_lens_label(str(explicit), source=source, fallback=fallback)
    inferred = _inferred_project_type(source)
    if inferred:
        return inferred
    category = root_component.get("category")
    if category:
        return _clean_lens_label(str(category), source=source, fallback=fallback)
    return humanize(fallback, "project").lower()


def _lens_source(*, root_component: Mapping[str, object], components: Sequence[Mapping[str, object]]) -> str:
    values: list[str] = []
    for key in ("name", "kind", "category", "what_it_is", "why_tracked"):
        value = str(root_component.get(key) or "").strip()
        if value:
            values.append(value)
    for value in root_component.get("aliases") or ():
        if isinstance(value, str) and value.strip():
            values.append(value)
    for component in components:
        for key in ("component_id", "name", "kind", "category", "product_layer", "what_it_is", "why_tracked"):
            value = str(component.get(key) or "").strip()
            if value:
                values.append(value)
    return " ".join(values).lower()


def _clean_lens_label(value: str, *, source: str, fallback: str) -> str:
    token = humanize(value, fallback).lower()
    if token == "governance engine":
        inferred = _inferred_project_type(source)
        return inferred or "governance product"
    if token.endswith(" engine"):
        return token.removesuffix(" engine").strip() or token
    return token


def _inferred_project_type(source: str) -> str:
    if "agent" in source and any(token in source for token in ("repo", "repository", "codebase", "coding")):
        if any(token in source for token in ("govern", "admiss", "control", "tribunal", "execution")):
            return "coding-agent governance"
        return "coding-agent tooling"
    if any(token in source for token in ("funding", "capital", "lending", "repayment", "treasury")):
        return "capital product"
    if any(token in source for token in ("experiment", "hypothesis", "assay", "perturbation", "reproducib")):
        return "research workflow"
    if any(token in source for token in ("codebase", "migration", "pull request", "ci", "rollback")):
        return "developer tooling"
    if any(token in source for token in ("order", "shipment", "asset", "fulfillment", "handoff")):
        return "operations workflow"
    return ""


def evidence_source_phrase(evidence_sources: Sequence[str]) -> str:
    """Describe active source surfaces without turning them into project facts."""

    source_terms = {
        "Compass": "current runtime state",
        "Radar": "active workstreams",
        "Registry": "component records",
        "Atlas": "topology records",
        "Casebook": "open risk records",
        "Plans": "technical plans",
    }
    selected = [
        source_terms[source]
        for source in ("Compass", "Radar", "Registry", "Atlas", "Casebook", "Plans")
        if source in evidence_sources
    ]
    selected.extend(f"{source.lower()} records" for source in evidence_sources if source not in source_terms)
    if not selected:
        return "available source records"
    if len(selected) == 1:
        return selected[0]
    if len(selected) == 2:
        return f"{selected[0]} and {selected[1]}"
    return f"{', '.join(selected[:-1])}, and {selected[-1]}"


def evidence_boundary_phrase(evidence_sources: Sequence[str]) -> str:
    """Name source surfaces and the kind of proof each one contributes."""

    source_terms = {
        "Compass": "Compass runtime state",
        "Radar": "Radar workstreams",
        "Registry": "Registry component records",
        "Atlas": "Atlas topology records",
        "Casebook": "Casebook risk records",
        "Plans": "Plans implementation records",
    }
    selected = [
        source_terms[source]
        for source in ("Compass", "Radar", "Registry", "Atlas", "Casebook", "Plans")
        if source in evidence_sources
    ]
    selected.extend(f"{source} records" for source in evidence_sources if source not in source_terms)
    if not selected:
        return "available source records"
    if len(selected) == 1:
        return selected[0]
    if len(selected) == 2:
        return f"{selected[0]} and {selected[1]}"
    return f"{', '.join(selected[:-1])}, and {selected[-1]}"


def scenario(
    *,
    project_title: str,
    release_label: str,
    work_mode: str,
    current_focus: str,
    next_title: str,
    next_action_text: str,
    critical_count: int,
    evidence_sources: Sequence[str],
    active_workstream_count: int,
    action_count: int,
) -> list[str]:
    """Render the scenario from source facts without leaking raw runtime fragments."""

    headline = _scenario_headline(release_label=release_label, work_mode=work_mode)
    caption = _scenario_caption(
        active_workstream_count=active_workstream_count,
        action_count=action_count,
        critical_count=critical_count,
    )
    focus_sentence = _focus_sentence(
        project_title=project_title,
        release_label=release_label,
        work_mode=work_mode,
        current_focus=current_focus,
    )
    next_sentence = _next_sentence(next_action_text)
    risk_sentence = _risk_sentence(critical_count)
    return [
        "Current work",
        project_title,
        headline,
        caption,
        " ".join(part for part in (focus_sentence, next_sentence, risk_sentence) if part),
    ]


def scenario_details(
    *,
    current_focus: str,
    next_action_text: str,
    critical_count: int,
    evidence_sources: Sequence[str],
) -> list[tuple[str, str]]:
    """Return the scenario detail rows that replace dense inline prose."""

    rows = [
        ("Active work", concise_text(current_focus, limit=180, fallback="Current focus is not available.")),
        ("Next move", action_sentence(next_action_text)),
        ("Proof boundary", evidence_boundary_phrase(evidence_sources)),
    ]
    if critical_count:
        noun = "blocker" if critical_count == 1 else "blockers"
        verb = "remains" if critical_count == 1 else "remain"
        rows.append(("Open risk", f"{critical_count} critical {noun} {verb} open."))
    return rows


def section_narration(
    *,
    project_title: str,
    release_label: str,
    work_mode: str,
    maturity: str,
    evidence_sources: Sequence[str],
    active_workstream_count: int,
    action_count: int,
    critical_count: int,
) -> dict[str, object]:
    """Return project-facing copy generated from projection facts."""

    title = sentence(project_title, "Project")
    mode = sentence(work_mode, "current").lower()
    release = sentence(release_label, "current release")
    evidence_phrase = evidence_source_phrase(evidence_sources)
    return {
        "scenario_title": f"Current {mode} work",
        "scenario_note": (
            f"Summarized from {release}, {_count_phrase(active_workstream_count, 'active workstream')}, "
            f"{_count_phrase(action_count, 'runtime action')}, and {_count_phrase(len(evidence_sources), 'evidence source')}."
        ),
        "claim_evidence_title": "What can be trusted right now?",
        "claim_evidence_note": (
            f"This separates current facts projected from {evidence_phrase} from stale records, conflicts, "
            "and proof gaps."
        ),
        "topology_spine_title": "Topology spine",
        "topology_spine_note": (
            "The projection checks whether backlog, plans, components, diagrams, risks, validation, "
            "and runtime state still connect."
        ),
        "artifact_coverage_title": "Source coverage",
        "artifact_coverage_note": (
            f"Coverage is measured against the {len(evidence_sources)} active surfaces backing this projection."
        ),
        "trust_title": "What changed or conflicts?",
        "trust_note": "Only material deltas, contradictions, or degraded source conditions appear here.",
        "delta_label": "Delta from previous state",
        "contradictions_label": "Contradictions",
        "degraded_label": "Source problems",
        "posture_title": "What risk matters?",
        "posture_note": (
            f"{critical_count} critical blockers shape the recommendation proof."
        ),
        "validation_label": "Validation posture",
        "risk_label": "Risk classes",
        "work_state_kicker": "Status now",
        "state_title": "Where does this stand?",
        "state_note": f"Current state is projected from the {mode} source records.",
        "current_state_label": "Current state",
        "desired_state_label": "Desired state",
        "next_title": "What should move next?",
        "next_note": "The next action comes from runtime state, active workstreams, and open blockers.",
        "proof_title": "What is known and unproven?",
        "proof_note": f"Confidence is point-in-time; maturity is {sentence(maturity, 'unknown').lower()}.",
        "known_label": "Known from source records",
        "unknown_label": "Unresolved in current projection",
        "confidence_label": "Confidence",
    }


def table_columns() -> dict[str, tuple[tuple[str, str], ...]]:
    """Column labels remain structural; rows and values come from source truth."""

    return {
        "claim_evidence_columns": (
            ("claim", "Claim"),
            ("value", "Value"),
            ("evidence", "Evidence"),
            ("freshness", "Freshness"),
            ("owner", "Owner"),
            ("source", "Source"),
        ),
        "topology_spine_columns": (
            ("link", "Spine link"),
            ("health", "Health"),
            ("detail", "Detail"),
        ),
        "artifact_coverage_columns": (
            ("surface", "Surface"),
            ("coverage", "Coverage"),
            ("count", "Count"),
            ("freshness", "Freshness"),
            ("source", "Source"),
        ),
    }


def _focus_sentence(*, project_title: str, release_label: str, work_mode: str, current_focus: str) -> str:
    focus = concise_text(current_focus, limit=140, fallback="the current work")
    mode = sentence(work_mode).lower()
    release = sentence(release_label)
    if mode and mode != "unknown":
        prefix = f"For {release}, " if release else ""
        return f"{prefix}{project_title} is in {mode} mode; the active focus is {_lower_first(focus)}."
    return f"{project_title} is focused on {_lower_first(focus)}."


def _scenario_headline(*, release_label: str, work_mode: str) -> str:
    release = sentence(release_label, "current release")
    mode = sentence(work_mode, "current").lower()
    if mode and mode != "unknown":
        return f"{release} {mode} work"
    return f"{release} current work"


def _scenario_caption(*, active_workstream_count: int, action_count: int, critical_count: int) -> str:
    parts = [
        _count_phrase(active_workstream_count, "active workstream"),
        _count_phrase(action_count, "runtime action"),
    ]
    if critical_count:
        parts.append(_count_phrase(critical_count, "critical blocker"))
    return "; ".join(part for part in parts if part) + "."


def _count_phrase(count: int, noun: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{count} {noun}{suffix}"


def _next_sentence(next_action_text: str) -> str:
    action = action_sentence(next_action_text)
    if not action:
        return ""
    return f"The next move is to {_lower_first(action).rstrip('.')}."


def _risk_sentence(critical_count: int) -> str:
    if critical_count <= 0:
        return ""
    noun = "blocker remains" if critical_count == 1 else "blockers remain"
    return f"{critical_count} critical {noun} open, so proof must stay attached to source records."


def _source_name_phrase(evidence_sources: Sequence[str]) -> str:
    names = [sentence(source) for source in evidence_sources if sentence(source)]
    if not names:
        return "available project records"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _lower_first(value: str) -> str:
    return f"{value[:1].lower()}{value[1:]}" if value else value
