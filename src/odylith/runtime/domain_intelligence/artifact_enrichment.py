"""Artifact-native projections from the domain intelligence graph.

Domain intelligence is source substrate. It should shape Radar, Registry,
Atlas, Casebook, Compass, Project, and Tribunal records in each artifact's
native language instead of being pasted into every artifact as a generic
``Domain Intelligence`` section.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_by_key
from odylith.runtime.domain_intelligence import artifact_tribunal_actors
from odylith.runtime.domain_intelligence.artifact_graph import DomainIntelligenceGraph
from odylith.runtime.domain_intelligence.artifact_graph import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.artifact_graph import graph_layer as _layer
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import normalize_connector_sequence
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class ArtifactEnrichment:
    radar_sections: dict[str, str]
    registry_contract: dict[str, tuple[str, ...]]
    atlas_contract: dict[str, tuple[str, ...]]
    plan_contract: dict[str, tuple[str, ...]]
    casebook_contract: dict[str, tuple[str, ...]]
    compass_contract: dict[str, tuple[str, ...]]
    project_contract: dict[str, tuple[str, ...]]
    tribunal_actors: tuple[dict[str, str], ...]


def build_artifact_enrichment(
    *,
    row: Mapping[str, Any],
    proposal: Mapping[str, Any] | None = None,
) -> ArtifactEnrichment:
    """Project one workstream's domain graph into artifact-native payloads."""

    graph = domain_graph_from_workstream(row.get("domain_intelligence"), row=row, proposal=proposal or {})
    return ArtifactEnrichment(
        radar_sections=radar_enrichment_sections(row=row, graph=graph),
        registry_contract=registry_projection(graph),
        atlas_contract=atlas_projection(graph),
        plan_contract=technical_plan_projection(graph),
        casebook_contract=casebook_projection(graph),
        compass_contract=compass_projection(graph),
        project_contract=project_projection(graph),
        tribunal_actors=artifact_tribunal_actors.tribunal_actor_projection(proposal or {"backlog": [row]}),
    )


def radar_enrichment_sections(
    *,
    row: Mapping[str, Any],
    graph: DomainIntelligenceGraph,
) -> dict[str, str]:
    """Return Radar-native sections shaped by domain intelligence."""

    first_slice = _workstream_first_slice(row=row, graph=graph)
    focus = _radar_workstream_focus(row)
    sections: dict[str, str] = {}

    first_path = _bullets(
        [
            *_first_path_enrichment_lines(focus=focus, first_slice=first_slice),
            _scoped_sentence("State object", focus, _first(graph.state_objects)),
            _scoped_sentence("Boundary", focus, _first(_layer(row, "scope")) or _first(graph.maturity_and_origin)),
        ]
    )
    if first_path:
        sections["First Path And Boundary"] = first_path

    proof = _bullets(
        [
            *_scoped_named_rows(
                ("Evidence record", "Evidence contents", "Review condition", "Trace requirement"),
                focus,
                graph.proof_standards[:4],
            ),
            *_scoped_named_rows(
                ("Validation gate", "State gate", "Recovery gate", "Scope gate", "Readiness gate"),
                focus,
                graph.validation_obligations[:5],
            ),
        ]
    )
    if proof:
        sections["Proof And Acceptance Gates"] = proof

    ownership = _bullets(
        [
            *_scoped_labelled_rows("Owner", focus, graph.actors[:2]),
            *_scoped_labelled_rows("Risk", focus, graph.risk_owners[:2]),
            *_scoped_labelled_rows("Control", focus, graph.exception_paths[:2]),
        ]
    )
    if ownership:
        sections["Ownership And Risk"] = ownership

    return sections


def registry_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return component-spec shaping hints from the domain graph."""

    return {
        "boundaries": _tuple_limit([*graph.state_objects, *graph.invariants], 6),
        "interfaces": _tuple_limit(graph.operators, 5),
        "failure_modes": _tuple_limit(graph.exception_paths, 6),
        "proof_obligations": _tuple_limit(graph.proof_standards, 6),
    }


def atlas_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return diagram-shaping hints from the domain graph."""

    return {
        "actors": _tuple_limit(graph.actors, 6),
        "state_objects": _tuple_limit(graph.state_objects, 6),
        "flows": _tuple_limit(graph.workflows, 8),
        "controls": _tuple_limit([*graph.approvers, *graph.exception_paths], 8),
        "evidence": _tuple_limit(graph.evidence_types, 6),
    }


def technical_plan_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return implementation-plan shaping hints from the domain graph."""

    return {
        "sequence": _tuple_limit(graph.workflows, 6),
        "validation": _tuple_limit(graph.validation_obligations, 6),
        "rollback_or_recovery": _tuple_limit(graph.exception_paths, 5),
        "release_gates": _tuple_limit([*graph.proof_standards, *graph.invariants], 6),
    }


def casebook_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return bug-record shaping hints from the domain graph."""

    return {
        "impact_model": _tuple_limit(graph.risk_owners, 6),
        "affected_actor": _tuple_limit(graph.actors, 4),
        "repro_evidence": _tuple_limit(graph.evidence_types, 6),
        "prevention_rules": _tuple_limit([*graph.invariants, *graph.exception_paths], 6),
    }


def compass_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return current-work narration hints from the domain graph."""

    return {
        "work_language": _tuple_limit(graph.workflows, 5),
        "decision_language": _tuple_limit([*graph.approvers, *graph.operators], 5),
        "proof_boundary": _tuple_limit(graph.proof_standards, 5),
        "open_risk": _tuple_limit(graph.exception_paths, 5),
    }


def project_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return Project-tab shaping hints from the domain graph."""

    return {
        "lens": (graph.primary_lens,),
        "participants": _tuple_limit(graph.actors, 8),
        "state_objects": _tuple_limit(graph.state_objects, 6),
        "first_path": _tuple_limit(graph.workflows, 6),
        "proof": _tuple_limit(graph.proof_standards, 6),
        "unknowns": _tuple_limit(graph.exception_paths, 6),
    }


def _first(values: Sequence[str]) -> str:
    return clean_text(values[0]) if values else ""


def _sentence(label: str, value: str) -> str:
    text = _without_existing_label(label=label, value=clean_text(value))
    return f"{label}: {text}" if text else ""


def _scoped_sentence(label: str, focus: str, value: str) -> str:
    text = _without_existing_label(label=label, value=clean_text(value))
    if not text:
        return ""
    focus_text = clean_text(focus).strip(" .")
    focus_label = _compact_focus_label(focus_text)
    detail = _compact_detail_text(_drop_boundary_repeated_lead(focus_text, text))
    if focus_text and focus_text.casefold() not in text.casefold():
        return f"{label}: {focus_label} — {detail}"
    return f"{label}: {_compact_detail_text(text)}"


def _first_path_enrichment_lines(*, focus: str, first_slice: str) -> list[str]:
    text = _without_existing_label(label="First path", value=clean_text(first_slice)).strip(" .")
    if not text:
        return []
    if len(text) <= 240 or text.count(",") < 5:
        return [_scoped_sentence("First path", focus, text)]
    lead, separator, detail = text.partition(":")
    if not separator:
        lead = "Accepted first path"
        detail = text
    segments = [
        _first_path_segment(segment)
        for segment in text_values(detail, split_scalar=True, split_commas=True)
    ]
    segments = [segment for segment in segments if segment]
    if len(segments) < 3:
        return [_scoped_sentence("First path", focus, text)]
    midpoint = max(2, min(len(segments) - 1, (len(segments) + 1) // 2))
    return [
        _scoped_sentence("First path", focus, f"{lead.strip(' .:')}."),
        f"Path actions: {'; '.join(segments[:midpoint]).strip(' ;.')}.",
        f"Completion check: {'; '.join(segments[midpoint:]).strip(' ;.')}.",
    ]


def _first_path_segment(value: str) -> str:
    text = clean_text(value).strip(" .")
    lowered = text.casefold()
    for connector in ("and", "or", "then"):
        prefix = f"{connector} "
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip(" .")
    return text


def _compact_focus_label(value: str) -> str:
    text = clean_text(value).strip(" .")
    parts = _readable_phrase_parts(text)
    if len(parts) >= 3:
        return _join_compact_phrase_parts(parts[:2])
    return text


def _compact_detail_text(value: str) -> str:
    text = clean_text(value).strip(" .")
    if "do not expand beyond " in text.casefold() and len(text) <= 420:
        return text
    if text.count(",") < 4 and len(text) <= 260:
        return text
    if len(text) <= 260 and _preserve_complete_validation_predicate(text):
        return text
    parts = _readable_phrase_parts(text)
    if len(parts) < 4:
        return text
    return _join_compact_phrase_parts(parts[:3])


def _join_compact_phrase_parts(parts: list[str]) -> str:
    rows = [clean_text(part).strip(" .") for part in parts if clean_text(part).strip(" .")]
    if len(rows) <= 1:
        return rows[0] if rows else ""
    if len(rows) == 2:
        connector = "" if rows[1].casefold().startswith(("and ", "or ")) else "and "
        return normalize_connector_sequence(f"{rows[0]} {connector}{rows[1]}")
    connector = "" if rows[2].casefold().startswith(("and ", "or ")) else "and "
    return normalize_connector_sequence(f"{rows[0]}, {rows[1]}, {connector}{rows[2]}")


def _preserve_complete_validation_predicate(value: str) -> bool:
    lowered = clean_text(value).casefold()
    return any(
        marker in lowered
        for marker in (
            "fails closed when",
            "validate that",
            "is missing",
            "are missing",
            "cannot explain",
            "instead of producing",
        )
    )


def _readable_phrase_parts(value: str) -> list[str]:
    parts: list[str] = []
    for part in text_values(value, split_scalar=True, split_commas=True):
        for and_part in part.split(" and "):
            token = clean_text(and_part).strip(" .")
            if token:
                parts.append(token)
    return parts


def _drop_boundary_repeated_lead(focus: str, value: str) -> str:
    focus_terms = _boundary_terms(focus)
    value_terms = _boundary_terms(value)
    if not focus_terms or not value_terms or focus_terms[-1] != value_terms[0]:
        return value
    text = clean_text(value)
    lead = value_terms[0]
    repaired = text[len(lead) :].strip(" ,;:.") if text.casefold().startswith(lead) else text
    return repaired if len(_boundary_terms(repaired)) >= 2 else value


def _boundary_terms(value: str) -> list[str]:
    text = clean_text(value).replace("-", " ")
    for punctuation in ",.;:!?()[]{}\"`":
        text = text.replace(punctuation, " ")
    return [token.strip("'").casefold() for token in text.split() if token[:1].isalpha()]


def _without_existing_label(*, label: str, value: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    label_text = clean_text(label).casefold()
    lowered = text.casefold()
    prefix = f"{label_text}:"
    if lowered.startswith(prefix):
        return clean_text(text[len(prefix) :])
    word_prefix = f"{label_text} "
    if lowered.startswith(word_prefix):
        return clean_text(text[len(label_text) :])
    return text


def _scoped_labelled_rows(label: str, focus: str, values: Sequence[str]) -> list[str]:
    return [_scoped_sentence(label, focus, value) for value in values if clean_text(value)]


def _scoped_named_rows(labels: Sequence[str], focus: str, values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    fallback = clean_text(labels[-1]) if labels else "Detail"
    for index, value in enumerate(values):
        label = clean_text(labels[index]) if index < len(labels) else fallback
        row = _scoped_sentence(label or fallback, focus, value)
        if row:
            rows.append(row)
    return rows


def _radar_workstream_focus(row: Mapping[str, Any]) -> str:
    return clean_text(row.get("title")) or clean_text(row.get("recommended_first_slice")) or "this workstream"


def _workstream_first_slice(*, row: Mapping[str, Any], graph: DomainIntelligenceGraph) -> str:
    explicit = clean_text(row.get("recommended_first_slice")) or clean_text(row.get("first_slice_proof"))
    if explicit:
        return explicit
    for value in [*graph.workflows, *graph.operators, *graph.state_objects, *graph.maturity_and_origin]:
        text = clean_text(value)
        if text:
            return text
    focus = _radar_workstream_focus(row)
    return f"Define the smallest source-backed behavior, state boundary, and proof gate for {focus}."


def _bullets(values: Sequence[str]) -> str:
    rows = dedupe_by_key(
        (text for value in values if (text := clean_text(value))),
        _bullet_dedupe_key,
    )
    return "\n".join(f"- {row}" for row in rows)


def _bullet_dedupe_key(value: str) -> str:
    text = clean_text(value).casefold()
    for label in ("proof", "gate", "risk", "control", "owner", "boundary", "first path", "state object"):
        prefix = f"{label}:"
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    for punctuation in ",.;:!?()[]{}\"'`-/":
        text = text.replace(punctuation, " ")
    ignored = {"proof", "gate", "risk", "control", "owner", "boundary"}
    return " ".join(word for word in text.split() if word and word not in ignored)


def _tuple_limit(values: Sequence[str], limit: int) -> tuple[str, ...]:
    return tuple(unique_text(clean_text(value) for value in values if clean_text(value))[:limit])


__all__ = [
    "ArtifactEnrichment",
    "atlas_projection",
    "build_artifact_enrichment",
    "casebook_projection",
    "compass_projection",
    "project_projection",
    "radar_enrichment_sections",
    "registry_projection",
    "technical_plan_projection",
]
