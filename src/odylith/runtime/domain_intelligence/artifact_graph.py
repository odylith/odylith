"""Shared Domain Intelligence graph normalization for artifact projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.text_values import clean_text
from odylith.runtime.common.text_values import text_values
from odylith.runtime.common.text_values import unique_text


@dataclass(frozen=True)
class DomainIntelligenceGraph:
    family: str
    primary_lens: str
    state_objects: tuple[str, ...]
    actors: tuple[str, ...]
    operators: tuple[str, ...]
    approvers: tuple[str, ...]
    risk_owners: tuple[str, ...]
    proof_standards: tuple[str, ...]
    invariants: tuple[str, ...]
    workflows: tuple[str, ...]
    exception_paths: tuple[str, ...]
    evidence_types: tuple[str, ...]
    validation_obligations: tuple[str, ...]
    glossary: tuple[str, ...]
    maturity_and_origin: tuple[str, ...]


def domain_graph_from_workstream(
    value: Any,
    *,
    row: Mapping[str, Any] | None = None,
    proposal: Mapping[str, Any] | None = None,
) -> DomainIntelligenceGraph:
    """Normalize existing workstream intelligence into the shared graph shape."""

    data = value if isinstance(value, Mapping) else {}
    intent = (proposal or {}).get("intent") if isinstance(proposal, Mapping) else {}
    title = clean_text((row or {}).get("title")) or clean_text(
        intent.get("title") if isinstance(intent, Mapping) else ""
    )
    family = clean_text(data.get("family")) or "general_project"
    glossary = graph_layer(data, "ontology")
    proof = unique_text([*graph_layer(data, "evidence_model"), *graph_layer(data, "evidence")])
    validation = graph_layer(data, "validation_obligations")
    explicit_actors = graph_layer(data, "actors")
    owners = graph_layer(data, "owners")
    authority = graph_layer(data, "authority")
    risks = graph_layer(data, "risks")
    constraints = graph_layer(data, "constraints")
    operators = graph_layer(data, "operators")
    state = graph_layer(data, "state")
    source_truth = graph_layer(data, "source_of_truth_map")
    invariants = graph_layer(data, "invariants")
    invalidation = graph_layer(data, "invalidation_rules")
    conflicts = graph_layer(data, "conflict_model")

    return DomainIntelligenceGraph(
        family=family,
        primary_lens=_primary_lens(family=family, title=title, glossary=glossary),
        state_objects=tuple(_pick_state_objects(glossary, state)),
        actors=tuple(
            unique_text([*explicit_actors, *_pick_actor_rows([*owners, *authority, *operators, *glossary])])[:8]
        ),
        operators=tuple(operators),
        approvers=tuple(_pick_approval_rows([*authority, *operators, *validation])),
        risk_owners=tuple(unique_text([*risks, *authority, *owners])[:8]),
        proof_standards=tuple(unique_text([*proof, *validation])[:10]),
        invariants=tuple(invariants),
        workflows=tuple(unique_text([*graph_layer(data, "intent"), *state, *operators])[:12]),
        exception_paths=tuple(unique_text([*constraints, *risks, *invalidation, *conflicts])[:10]),
        evidence_types=tuple(unique_text([*proof, *source_truth])[:10]),
        validation_obligations=tuple(validation),
        glossary=tuple(glossary),
        maturity_and_origin=tuple(
            unique_text([*constraints, *graph_layer(data, "assumptions"), *source_truth])[:8]
        ),
    )


def graph_layer(value: Any, key: str | None = None) -> list[str]:
    target = value.get(key) if key and isinstance(value, Mapping) else value
    return [item for item in text_values(target) if clean_text(item)]


def _primary_lens(*, family: str, title: str, glossary: list[str]) -> str:
    family_label = clean_text(family).replace("_", " ")
    if family_label and family_label not in {"general project", "host reasoned project"}:
        return family_label
    for row in glossary:
        first = clean_text(row).split(":", 1)[0].strip()
        if first and first.casefold() not in {"actor", "state object", "evidence record", "release gate"}:
            return first
    return slugify(title).replace("-", " ") or "project workflow"


def _pick_state_objects(glossary: list[str], state: list[str]) -> list[str]:
    rows = []
    for value in [*glossary, *state]:
        if not _looks_like_state_object(value):
            continue
        lowered = value.casefold()
        if any(
            token in lowered
            for token in (
                "object",
                "state",
                "subject",
                "record",
                "workflow item",
                "tracked item",
            )
        ):
            rows.append(value)
    fallback = [value for value in [*glossary, *state] if _looks_like_state_object(value)]
    return unique_text(rows)[:5] or unique_text(fallback)[:3]


def _looks_like_state_object(value: str) -> bool:
    text = clean_text(value)
    lowered = text.casefold()
    if not text:
        return False
    actor_markers = (
        "human actor",
        "actors include",
        "actor:",
        "first-release actor",
        "operator",
        "reviewer",
        "owner",
        "maintainer",
        "lead",
        "user:",
    )
    if any(marker in lowered for marker in actor_markers):
        return False
    return True


def _pick_actor_rows(values: list[str]) -> list[str]:
    rows = [
        value
        for value in values
        if any(
            token in value.casefold()
            for token in (
                "actor",
                "advocate",
                "operator",
                "owner",
                "lead",
                "maintainer",
                "reviewer",
                "coordinator",
                "approver",
            )
        )
    ]
    return unique_text(rows)[:8]


def _pick_approval_rows(values: list[str]) -> list[str]:
    rows = [
        value
        for value in values
        if any(
            token in value.casefold()
            for token in ("approve", "review", "decision", "gate", "authority")
        )
    ]
    return unique_text(rows)[:6]


__all__ = ["DomainIntelligenceGraph", "domain_graph_from_workstream", "graph_layer"]
