"""Semantic-model compiler for confirmed greenfield apply payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import select_visible_result_candidate
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import completed_external_boundary_rows
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import word_count


APPLY_SEMANTIC_INPUT_VERSION = "odylith.greenfield.apply_semantic_input.v1"
_VISIBLE_RESULT_CONFIDENCE_FLOOR = 0.9
_FIRST_PATH_EVENT_VISIBLE_RESULT_CONFIDENCE_FLOOR = 0.8


@dataclass(frozen=True)
class GreenfieldApplySemanticInput:
    """Source-owned inputs for compiling legacy proposal payloads into SemanticModelIR."""

    schema_version: str
    title: str
    state_object: str
    first_path: str
    visible_result: str
    proof_boundary: str
    components: tuple[Mapping[str, Any], ...]
    human_actors: tuple[str, ...]
    internal_systems: tuple[str, ...]
    external_systems: tuple[str, ...]
    non_goals: tuple[str, ...]
    workstreams: tuple[Mapping[str, Any], ...]
    source_requirements: tuple[str, ...]
    source_paths: tuple[tuple[str, str], ...]


def ensure_apply_semantic_model(proposal: dict[str, Any], *, refresh: bool = False) -> dict[str, Any]:
    """Compile legacy confirmed apply payloads into the pre-confirm semantic model."""

    existing_model = isinstance(proposal.get("semantic_model"), Mapping)
    existing_input = _has_current_apply_semantic_input(proposal)
    if not refresh and existing_model and existing_input:
        return proposal
    compiler_input = greenfield_apply_semantic_input(proposal)
    proposal["apply_semantic_input"] = apply_semantic_input_mapping(compiler_input)
    if not refresh and existing_model:
        return proposal
    proposal["semantic_model"] = semantic_model_mapping(
        build_greenfield_semantic_model(
            title=compiler_input.title,
            state_object=compiler_input.state_object,
            first_path=compiler_input.first_path,
            visible_result=compiler_input.visible_result,
            proof_boundary=compiler_input.proof_boundary,
            components=compiler_input.components,
            human_actors=compiler_input.human_actors,
            internal_systems=compiler_input.internal_systems,
            external_systems=compiler_input.external_systems,
            non_goals=compiler_input.non_goals,
            workstreams=compiler_input.workstreams,
            source_requirements=compiler_input.source_requirements,
        )
    )
    return proposal


def apply_semantic_input_mapping(compiler_input: GreenfieldApplySemanticInput) -> dict[str, Any]:
    """Serialize the source-mapped compiler input for downstream repair/audit."""

    return {
        "schema_version": compiler_input.schema_version,
        "title": compiler_input.title,
        "state_object": compiler_input.state_object,
        "first_path": compiler_input.first_path,
        "visible_result": compiler_input.visible_result,
        "proof_boundary": compiler_input.proof_boundary,
        "human_actors": list(compiler_input.human_actors),
        "internal_systems": list(compiler_input.internal_systems),
        "external_systems": list(compiler_input.external_systems),
        "non_goals": list(compiler_input.non_goals),
        "source_requirements": list(compiler_input.source_requirements),
        "components": [dict(row) for row in compiler_input.components],
        "workstreams": [dict(row) for row in compiler_input.workstreams],
        "source_paths": dict(compiler_input.source_paths),
    }


def greenfield_apply_semantic_input(proposal: Mapping[str, Any]) -> GreenfieldApplySemanticInput:
    """Return the typed compiler input used to build the greenfield semantic model."""

    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    release_plan = proposal.get("release_plan") if isinstance(proposal.get("release_plan"), Mapping) else {}
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    title, title_source = _first_text_with_source(
        ("intent.title", intent.get("title")),
        ("proposal.title", proposal.get("title")),
        fallback=("default.title", "Greenfield Project"),
    )
    state_object, state_source = _first_text_with_source(
        ("intent.state_object", intent.get("state_object")),
        ("project_brief.state_object", brief.get("state_object")),
        fallback=("default.state_object", f"{title} state"),
    )
    proof_boundary, proof_source = _proof_boundary_text(
        title=title,
        intent=intent,
        brief=brief,
        release_plan=release_plan,
        proposal=proposal,
    )
    first_path, first_path_source = _first_path_text(
        title=title,
        intent=intent,
        brief=brief,
        backlog_rows=backlog_rows,
        state_object=state_object,
        proof_boundary=proof_boundary,
    )
    visible_candidate = select_visible_result_candidate(
        first_path,
        proof_boundary=proof_boundary,
        product_view=intent.get("product_view"),
        state_object=state_object,
    )
    visible_result = visible_candidate.text if _is_apply_visible_result_candidate(visible_candidate) else ""
    external_systems, _external_source = _external_system_rows(intent=intent, first_path=first_path)
    return GreenfieldApplySemanticInput(
        schema_version=APPLY_SEMANTIC_INPUT_VERSION,
        title=title,
        state_object=state_object,
        first_path=first_path,
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        components=tuple(row for row in proposal.get("components", []) if isinstance(row, Mapping)),
        human_actors=tuple(text_values(intent.get("human_actors"))),
        internal_systems=tuple(text_values(intent.get("internal_systems"))),
        external_systems=tuple(external_systems),
        non_goals=tuple(text_values(proposal.get("non_goals") or intent.get("non_goals"))),
        workstreams=tuple(backlog_rows),
        source_requirements=tuple(text_values(intent.get("evidence_requirements"))),
        source_paths=(
            ("title", title_source),
            ("state_object", state_source),
            ("first_path", first_path_source),
            ("visible_result", visible_candidate.source_path if visible_result else ""),
            ("proof_boundary", proof_source),
            ("components", "proposal.components"),
            ("human_actors", "intent.human_actors"),
            ("internal_systems", "intent.internal_systems"),
            ("external_systems", _external_source),
            ("non_goals", "proposal.non_goals|intent.non_goals"),
            ("workstreams", "proposal.backlog"),
            ("source_requirements", "intent.evidence_requirements"),
        ),
    )


def _external_system_rows(*, intent: Mapping[str, Any], first_path: str) -> tuple[tuple[str, ...], str]:
    rows = tuple(text_values(intent.get("external_systems")))
    if rows:
        return rows, "intent.external_systems"
    inferred_rows, _ambiguities = completed_external_boundary_rows({**dict(intent), "first_path": first_path})
    if inferred_rows:
        return tuple(inferred_rows), "semantic_inference.first_path_external_boundary"
    return (
        (
            "No live external system is accepted for the first release - manual or fixture-backed input supplies "
            "the accepted first-path evidence before product state changes.",
        ),
        "semantic_inference.deferred_external_boundary",
    )


def _first_path_text(
    *,
    title: str,
    intent: Mapping[str, Any],
    brief: Mapping[str, Any],
    backlog_rows: list[Mapping[str, Any]],
    state_object: str,
    proof_boundary: str,
) -> tuple[str, str]:
    first_path, source = _first_text_with_source(
        ("intent.first_path", intent.get("first_path")),
        ("project_brief.first_path", brief.get("first_path")),
        ("backlog.recommended_first_slice", _first_nonempty_backlog_value(backlog_rows, "recommended_first_slice")),
        ("backlog.product_view", _first_nonempty_backlog_value(backlog_rows, "product_view")),
        ("intent.summary", intent.get("summary")),
        fallback=("default.first_path", f"{title} creates, preserves, and reviews the accepted first-path result"),
    )
    if not _first_path_has_visible_result(
        first_path,
        proof_boundary=proof_boundary,
        product_view=intent.get("product_view"),
        state_object=state_object,
    ):
        first_path = f"{first_path.rstrip(' .,;:!?')}. The product shows the accepted result for review."
        source = f"{source}+semantic_visible_result_fallback"
    return first_path, source


def _first_nonempty_backlog_value(rows: list[Mapping[str, Any]], key: str) -> str:
    for row in rows:
        value = clean_text(row.get(key))
        if value:
            return value
    return ""


def _proof_boundary_text(
    *,
    title: str,
    intent: Mapping[str, Any],
    brief: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> tuple[str, str]:
    validation_text = " ".join(
        clean_text(value)
        for value in text_values(proposal.get("validation_strategy"))
        if clean_text(value)
    )
    return _first_text_with_source(
        ("intent.proof_boundary", intent.get("proof_boundary")),
        ("project_brief.proof", brief.get("proof")),
        ("release_plan.promotion_criteria", release_plan.get("promotion_criteria")),
        ("validation_strategy", validation_text),
        fallback=(
            "default.proof_boundary",
            f"{title} proof links state, visible result, validation, and release evidence",
        ),
    )


def _first_text_with_source(
    *candidates: tuple[str, Any],
    fallback: tuple[str, str],
) -> tuple[str, str]:
    for source, value in candidates:
        text = _candidate_source_text(value)
        if text:
            return text, source
    return fallback[1], fallback[0]


def _candidate_source_text(value: Any) -> str:
    if not isinstance(value, str):
        rows = text_values(value)
        if rows:
            return clean_text(" ".join(rows))
    return clean_text(value)


def _first_path_has_visible_result(value: str, *, proof_boundary: str, product_view: Any = "", state_object: Any = "") -> bool:
    candidate = select_visible_result_candidate(
        value,
        proof_boundary=proof_boundary,
        product_view=product_view,
        state_object=state_object,
    )
    if candidate.source_path == "intent.product_view.visible_result" and word_count(candidate.text) >= 2:
        return True
    if not candidate.source_path.startswith("first_path."):
        return False
    if candidate.source_path == "first_path.visible_result" and candidate.confidence >= 0.8 and word_count(candidate.text) >= 2:
        return True
    if candidate.source_path.startswith("first_path.events.") and candidate.confidence >= 0.55 and word_count(candidate.text) >= 2:
        return True
    if candidate.source_kind == "first_path_event" and candidate.confidence < _VISIBLE_RESULT_CONFIDENCE_FLOOR:
        return _has_compound_first_path_result_shape(candidate.text) and (
            candidate.confidence >= _FIRST_PATH_EVENT_VISIBLE_RESULT_CONFIDENCE_FLOOR
        )
    confidence_floor = (
        _FIRST_PATH_EVENT_VISIBLE_RESULT_CONFIDENCE_FLOOR
        if candidate.source_kind == "first_path_event"
        else _VISIBLE_RESULT_CONFIDENCE_FLOOR
    )
    return candidate.confidence >= confidence_floor


def _is_apply_visible_result_candidate(candidate: Any) -> bool:
    if clean_text(getattr(candidate, "source_kind", "")) not in {
        "first_path_event",
        "first_path_event_refined_by_proof_boundary",
        "intent_context",
    }:
        return False
    return word_count(getattr(candidate, "text", "")) >= 2


def _has_compound_first_path_result_shape(value: str) -> bool:
    text = clean_text(value).strip(" .")
    return word_count(text) >= 10 and "," in text


def _has_current_apply_semantic_input(proposal: Mapping[str, Any]) -> bool:
    compiler_input = proposal.get("apply_semantic_input")
    return (
        isinstance(compiler_input, Mapping)
        and clean_text(compiler_input.get("schema_version")) == APPLY_SEMANTIC_INPUT_VERSION
        and isinstance(compiler_input.get("source_paths"), Mapping)
    )


__all__ = [
    "APPLY_SEMANTIC_INPUT_VERSION",
    "GreenfieldApplySemanticInput",
    "apply_semantic_input_mapping",
    "ensure_apply_semantic_model",
    "greenfield_apply_semantic_input",
]
