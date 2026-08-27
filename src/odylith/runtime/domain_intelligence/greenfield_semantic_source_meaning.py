"""Bind and validate one holistic, node-owned Greenfield meaning graph.

The host owns semantic judgment over the complete source. Runtime code checks
typed structure, exact citations, indexes, and causal endpoints, then projects
the accepted bytes without interpreting words or repairing meaning.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_ir_compiler import (
    compile_semantic_source_meaning,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    bind_semantic_evidence_blocks,
    require_semantic_source_refs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning_contract import (
    SEMANTIC_SOURCE_MEANING_CONTRACT_VERSION,
    SEMANTIC_SOURCE_MEANING_GRAPH_VERSION,
    SOURCE_MEANING_AUDIENCE_KINDS,
    SOURCE_MEANING_COLLECTIONS,
    SOURCE_MEANING_ENTITY_EFFECT_KINDS,
    SOURCE_MEANING_MODALITIES,
    semantic_source_meaning_contract,
    semantic_source_meaning_graph_schema,
    semantic_source_meaning_provider_schema,
)


SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION = (
    "odylith.greenfield.semantic-source-meaning-author-run.v20"
)


def semantic_source_meaning_contract_sha256() -> str:
    """Hash the prompt-independent semantic ownership contract."""

    return _sha256(semantic_source_meaning_contract())


def bind_semantic_source_meaning_graph(
    value: Any,
    *,
    evidence_catalog: Mapping[str, Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Resolve opaque evidence handles, then validate the immutable graph."""

    return require_semantic_source_meaning_graph(
        bind_semantic_evidence_blocks(value, catalog=evidence_catalog),
        evidence_sources=evidence_sources,
    )


def apply_semantic_source_meaning_completeness_gate(value: Any) -> dict[str, Any]:
    """Turn structurally incomplete product meaning into one safe question.

    This gate inspects only typed graph membership. It never interprets source text,
    repairs accepted facts, or changes a complete semantic graph.
    """

    graph = deepcopy(_mapping(value, "Semantic source-meaning graph"))
    clarification = graph.get("clarification")
    if isinstance(clarification, Mapping) and clarification.get("required") is True:
        return graph
    workflow = graph.get("workflow")
    if not isinstance(workflow, Sequence) or isinstance(
        workflow, (str, bytes, bytearray)
    ):
        return graph
    rows = [row for row in workflow if isinstance(row, Mapping)]
    refs = _ordered_source_refs(
        ref
        for row in rows
        for ref in (
            row.get("source_refs")
            if isinstance(row.get("source_refs"), Sequence)
            and not isinstance(row.get("source_refs"), (str, bytes, bytearray))
            else []
        )
    )
    actors = graph.get("actors")
    audiences = graph.get("audiences")
    has_participant = bool(actors) or bool(audiences) or any(
        row.get("owner_actor_index") is not None for row in rows
    )
    has_visible_result = any(
        isinstance(effect, Mapping) and effect.get("kind") == "visible_result"
        for row in rows
        for effect in (
            row.get("entity_effects")
            if isinstance(row.get("entity_effects"), Sequence)
            and not isinstance(row.get("entity_effects"), (str, bytes, bytearray))
            else []
        )
    )
    if not has_participant:
        graph["clarification"] = {
            "required": True,
            "question": "Which human role uses the product and owns or directs its first path?",
            "source_refs": refs,
        }
    elif not has_visible_result:
        graph["clarification"] = {
            "required": True,
            "question": "What should the first usable path show or return when it succeeds?",
            "source_refs": refs,
        }
    return graph


def require_semantic_source_meaning_graph(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Validate exact node ownership and source custody without prose inference."""

    graph = _mapping(value, "Semantic source-meaning graph")
    _exact_keys(
        graph,
        {
            "version",
            "presentation",
            *SOURCE_MEANING_COLLECTIONS,
            "clarification",
        },
    )
    if graph.get("version") != SEMANTIC_SOURCE_MEANING_GRAPH_VERSION:
        raise ValueError("Semantic source-meaning graph uses an unsupported version")
    presentation = _mapping(graph.get("presentation"), "presentation")
    _exact_keys(presentation, {"title", "status", "source_refs"})
    _text(presentation.get("title"), 200)
    presentation_status = _enum(
        presentation.get("status"), {"source_declared", "working_assumption"}
    )
    presentation_refs = _refs(
        presentation.get("source_refs"),
        evidence_sources,
        allow_empty=True,
    )
    if presentation_status == "source_declared" and not presentation_refs:
        raise ValueError("Source-declared presentation lacks exact source custody")
    if presentation_status == "working_assumption" and presentation_refs:
        raise ValueError("Working presentation assumption carries source custody")

    audiences = _rows(graph.get("audiences"), 64, "audiences")
    for row in audiences:
        _exact_keys(row, {"kind", "label", "source_refs"})
        _enum(row.get("kind"), set(SOURCE_MEANING_AUDIENCE_KINDS))
        _text(row.get("label"), 200)
        _refs(row.get("source_refs"), evidence_sources)

    actors = _rows(graph.get("actors"), 64, "actors")
    for row in actors:
        _exact_keys(row, {"canonical_label", "source_refs"})
        _text(row.get("canonical_label"), 200)
        _refs(row.get("source_refs"), evidence_sources)

    entities = _rows(graph.get("entities"), 64, "entities")
    for row in entities:
        _exact_keys(row, {"label", "source_refs"})
        _text(row.get("label"), 300)
        _refs(row.get("source_refs"), evidence_sources)

    workflow = _rows(graph.get("workflow"), 64, "workflow")
    if not workflow:
        raise ValueError("Semantic source meaning lacks a first-path workflow")
    output_count = 0
    referenced_entity_indexes: set[int] = set()
    creation_entity_indexes: list[int] = []
    for row in workflow:
        _exact_keys(
            row,
            {
                "action",
                "entity_effects",
                "owner_actor_index",
                "source_refs",
            },
        )
        _text(row.get("action"), 200)
        owner = row.get("owner_actor_index")
        _optional_index(owner, len(actors), "workflow actor")
        _refs(row.get("source_refs"), evidence_sources)
        effect_keys: set[tuple[int, str]] = set()
        for effect in _rows(row.get("entity_effects"), 64, "workflow entity effects"):
            kind = _enum(effect.get("kind"), set(SOURCE_MEANING_ENTITY_EFFECT_KINDS))
            expected = {"kind", "entity_index", "source_refs"}
            if kind in {"created", "changed", "stable", "visible_result"}:
                expected.add("edge_source_refs")
            if kind == "changed":
                expected.update({"from_state", "to_state"})
            if kind == "stable":
                expected.add("stable_state")
            if kind == "visible_result":
                expected.add("visible_to")
            _exact_keys(effect, expected)
            entity_index = _required_index(
                effect.get("entity_index"), len(entities), "workflow effect entity"
            )
            effect_key = (entity_index, kind)
            if effect_key in effect_keys:
                raise ValueError("Semantic source-meaning repeats one typed entity effect")
            effect_keys.add(effect_key)
            referenced_entity_indexes.add(entity_index)
            _refs(effect.get("source_refs"), evidence_sources)
            if kind == "created":
                creation_entity_indexes.append(entity_index)
                _refs(effect.get("edge_source_refs"), evidence_sources)
            elif kind == "changed":
                before = _text(effect.get("from_state"), 200)
                after = _text(effect.get("to_state"), 200)
                if before == after:
                    raise ValueError("Semantic source-meaning state does not change")
                _refs(effect.get("edge_source_refs"), evidence_sources)
            elif kind == "stable":
                _text(effect.get("stable_state"), 200)
                _refs(effect.get("edge_source_refs"), evidence_sources)
            elif kind == "visible_result":
                output_count += 1
                _refs(effect.get("edge_source_refs"), evidence_sources)
                for recipient in _rows(
                    effect.get("visible_to"), 64, "output recipients"
                ):
                    _exact_keys(recipient, {"kind", "index", "source_refs"})
                    recipient_kind = _enum(
                        recipient.get("kind"), {"actor", "audience"}
                    )
                    size = len(actors) if recipient_kind == "actor" else len(audiences)
                    _required_index(recipient.get("index"), size, "output recipient")
                    _refs(recipient.get("source_refs"), evidence_sources)

    dependencies = _rows(graph.get("dependencies"), 64, "dependencies")
    for row in dependencies:
        _exact_keys(row, {"label", "access_mode", "source_refs"})
        _text(row.get("label"), 300)
        _enum(row.get("access_mode"), {"read", "read_only", "unspecified"})
        _refs(row.get("source_refs"), evidence_sources)

    product_boundaries = _rows(
        graph.get("product_boundaries"), 32, "product boundaries"
    )
    for row in product_boundaries:
        _exact_keys(row, {"statement", "source_refs"})
        _text(row.get("statement"), 500)
        _refs(row.get("source_refs"), evidence_sources)

    policies = _rows(graph.get("policy_boundaries"), 32, "policy boundaries")
    for row in policies:
        expected = {"modalities", "statement", "source_refs"}
        if "applies_to_dependency_index" in row or "attachment_source_refs" in row:
            expected.update(
                {"applies_to_dependency_index", "attachment_source_refs"}
            )
        _exact_keys(row, expected)
        modalities = [
            _enum(token, set(SOURCE_MEANING_MODALITIES))
            for token in _sequence(row.get("modalities"), 4, "policy modalities")
        ]
        if not modalities or len(set(modalities)) != len(modalities):
            raise ValueError("Semantic source-meaning policy modalities are invalid")
        _text(row.get("statement"), 500)
        _refs(row.get("source_refs"), evidence_sources)
        if "applies_to_dependency_index" in row:
            _required_index(
                row.get("applies_to_dependency_index"),
                len(dependencies),
                "policy dependency attachment",
            )
            _refs(row.get("attachment_source_refs"), evidence_sources)

    gaps = _rows(graph.get("non_material_gaps"), 32, "non-material gaps")
    provenance = _rows(graph.get("provenance_only"), 32, "provenance-only evidence")
    for row in [*gaps, *provenance]:
        _exact_keys(row, {"statement", "source_refs"})
        _text(row.get("statement"), 500)
        _refs(row.get("source_refs"), evidence_sources)

    clarification = _mapping(graph.get("clarification"), "clarification")
    _exact_keys(clarification, {"required", "question", "source_refs"})
    required = clarification.get("required")
    if not isinstance(required, bool):
        raise ValueError("Semantic source-meaning clarification flag is invalid")
    question = _text(clarification.get("question"), 600, allow_empty=True)
    refs = _refs(
        clarification.get("source_refs"), evidence_sources, allow_empty=not required
    )
    if required:
        if not question or not refs:
            raise ValueError("Semantic source-meaning clarification is incomplete")
    elif question or refs:
        raise ValueError("Complete source meaning carries clarification residue")
    if not required and output_count == 0:
        raise ValueError("Complete source meaning lacks an observable result")
    if referenced_entity_indexes != set(range(len(entities))):
        raise ValueError("Semantic source meaning carries an unbound entity")
    if len(creation_entity_indexes) != len(set(creation_entity_indexes)):
        raise ValueError("Complete source meaning repeats one canonical created effect")
    if not required and not audiences and not any(
        row["owner_actor_index"] is not None for row in workflow
    ):
        raise ValueError("Interactive source meaning lacks a participant or audience")
    return dict(graph)


def semantic_source_meaning_sha256(graph: Mapping[str, Any]) -> str:
    """Hash the exact accepted source meaning and citation custody."""

    return _sha256(graph)


def _validate_label_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    evidence_sources: Mapping[str, str],
) -> None:
    for row in rows:
        _exact_keys(row, {"label", "source_refs"})
        _text(row.get("label"), 300)
        _refs(row.get("source_refs"), evidence_sources)


def _ordered_source_refs(values: Any) -> list[Any]:
    refs: list[Any] = []
    seen: set[str] = set()
    for value in values:
        token = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        if token in seen:
            continue
        seen.add(token)
        refs.append(deepcopy(value))
        if len(refs) == 8:
            break
    return refs


def _refs(
    value: Any,
    evidence_sources: Mapping[str, str],
    *,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    return require_semantic_source_refs(
        value, evidence_sources=evidence_sources, allow_empty=allow_empty
    )


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return value


def _sequence(value: Any, maximum: int, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"Semantic source-meaning {label} is malformed")
    rows = list(value)
    if len(rows) > maximum:
        raise ValueError(f"Semantic source-meaning {label} exceeds its limit")
    return rows


def _rows(value: Any, maximum: int, label: str) -> list[Mapping[str, Any]]:
    rows = _sequence(value, maximum, label)
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError(f"Semantic source-meaning {label} is malformed")
    return rows


def _text(value: Any, maximum: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) > maximum:
        raise ValueError("Semantic source-meaning text is malformed")
    if not value and not allow_empty:
        raise ValueError("Semantic source-meaning text is empty")
    return value


def _enum(value: Any, allowed: set[str]) -> str:
    token = _text(value, 100)
    if token not in allowed:
        raise ValueError("Semantic source-meaning enum value is invalid")
    return token


def _optional_index(value: Any, size: int, label: str) -> None:
    if value is not None:
        _required_index(value, size, label)


def _required_index(value: Any, size: int, label: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value >= size
    ):
        raise ValueError(f"Semantic source-meaning {label} index is dangling")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError("Semantic source-meaning structure is invalid")


def _sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION",
    "SEMANTIC_SOURCE_MEANING_CONTRACT_VERSION",
    "SEMANTIC_SOURCE_MEANING_GRAPH_VERSION",
    "apply_semantic_source_meaning_completeness_gate",
    "bind_semantic_source_meaning_graph",
    "compile_semantic_source_meaning",
    "require_semantic_source_meaning_graph",
    "semantic_source_meaning_contract",
    "semantic_source_meaning_contract_sha256",
    "semantic_source_meaning_graph_schema",
    "semantic_source_meaning_provider_schema",
    "semantic_source_meaning_sha256",
]
