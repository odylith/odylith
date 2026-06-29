"""Canonical semantic facts that renderers may repeat across projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import replace
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text

_SUPPORTING_PROJECTION_TAIL_TERMS = frozenset(
    {
        "audit",
        "available",
        "browsable",
        "compare",
        "compared",
        "comparison",
        "evidence",
        "history",
        "historical",
        "log",
        "proof",
        "prior",
        "previous",
        "record",
        "report",
        "review",
        "reviewable",
        "run",
        "runs",
        "saved",
        "status",
        "stored",
        "trace",
        "update",
        "viewable",
    }
)


@dataclass(frozen=True)
class CanonicalProjectionFact:
    """A source-owned semantic fact that may appear in rendered artifacts."""

    text: str
    source_layer: str
    semantic_node_id: str
    source_path: str
    allowed_projection_ids: tuple[str, ...]
    allowed_surface_roles: tuple[str, ...]
    repair_owner: str


def canonical_projection_facts(proposal: Mapping[str, Any]) -> tuple[CanonicalProjectionFact, ...]:
    """Return typed source facts that can be projected without being slop."""

    semantic_model = _mapping(proposal.get("semantic_model"))
    if not _complete_semantic_source(semantic_model):
        return ()
    first_path = _mapping(semantic_model.get("first_path_contract"))
    facts: list[CanonicalProjectionFact] = []
    facts.extend(_first_path_facts(first_path))
    facts.extend(_component_facts(proposal.get("components")))
    return _canonical_projection_variants(facts)


def canonical_projection_text_values(proposal: Mapping[str, Any]) -> list[str]:
    return [fact.text for fact in canonical_projection_facts(proposal)]


def _first_path_facts(first_path: Mapping[str, Any]) -> list[CanonicalProjectionFact]:
    values: list[str] = []
    for key in ("raw_path", "capability", "visible_result", "mutation", "recovery_path"):
        values.extend(text_values(first_path.get(key)))
    values.extend(_first_path_step_values(first_path.get("raw_path")))
    events = first_path.get("events")
    if isinstance(events, Sequence) and not isinstance(events, (str, bytes, bytearray)):
        for item in events:
            if not isinstance(item, Mapping):
                continue
            for key in ("text", "mutation", "target_entity", "action"):
                values.extend(text_values(item.get(key)))
    return [
        CanonicalProjectionFact(
            text=value,
            source_layer="semantic_model",
            semantic_node_id="first_path_contract",
            source_path="proposal.semantic_model.first_path_contract",
            allowed_projection_ids=("radar", "registry", "atlas", "project_brief", "next_steps", "accepted_project"),
            allowed_surface_roles=("summary", "first_path", "proof", "implementation_prompt"),
            repair_owner="semantic_projection_custody",
        )
        for value in values
        if normalize_string(value)
    ]


def _component_facts(value: Any) -> list[CanonicalProjectionFact]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    rows: list[CanonicalProjectionFact] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue
        values = [
            normalize_string(item.get("label")),
            " ".join(
                part
                for part in (normalize_string(item.get("component_id")), normalize_string(item.get("label")))
                if part
            ),
        ]
        rows.extend(
            CanonicalProjectionFact(
                text=text,
                source_layer="component_contract",
                semantic_node_id=f"components[{index}]",
                source_path="proposal.components",
                allowed_projection_ids=("registry", "atlas", "project_brief", "next_steps"),
                allowed_surface_roles=("component_label", "routing", "implementation_prompt"),
                repair_owner="semantic_projection_custody",
            )
            for text in values
            if normalize_string(text)
        )
    return rows


def _first_path_step_values(value: Any) -> list[str]:
    raw = normalize_string(value)
    if not raw:
        return []
    return [step for step in first_path_model(raw).steps if normalize_string(step)]


def _canonical_projection_variants(
    facts: Sequence[CanonicalProjectionFact],
) -> tuple[CanonicalProjectionFact, ...]:
    rows: list[CanonicalProjectionFact] = []
    seen: set[str] = set()
    for fact in facts:
        values = [normalize_string(fact.text), *_compact_source_projection_variants(fact.text)]
        for index, value in enumerate(values):
            text = normalize_string(value)
            if not text:
                continue
            key = "|".join(
                (
                    fact.source_layer,
                    fact.semantic_node_id,
                    fact.source_path,
                    text.casefold(),
                )
            )
            if key in seen:
                continue
            seen.add(key)
            semantic_node_id = fact.semantic_node_id if index == 0 else f"{fact.semantic_node_id}:projection:{index}"
            rows.append(replace(fact, text=text, semantic_node_id=semantic_node_id))
    return tuple(rows)


def _compact_source_projection_variants(value: str) -> list[str]:
    """Return shorter grammatical projections of one typed source fact."""

    text = normalize_string(value).strip(" .")
    if not text:
        return []
    variants: list[str] = []
    for head, tail in _supporting_tail_candidates(text):
        if _meaningful_projection_prefix(head) and _supporting_projection_tail(tail):
            variants.append(head.strip(" ."))
    return list(unique_text(variants))


def _supporting_tail_candidates(value: str) -> list[tuple[str, str]]:
    text = normalize_string(value).strip(" .")
    if not text:
        return []
    head, separator, tail = text.rpartition(", ")
    if separator and _supporting_projection_tail(tail):
        return [(head.strip(" .,"), tail.strip(" .,"))]
    head, separator, tail = text.rpartition(" and ")
    if separator:
        return [(head.strip(" .,"), tail.strip(" .,"))]
    return []


def _meaningful_projection_prefix(value: str) -> bool:
    words = [word for word in normalize_string(value).split() if word.strip(".,;:")]
    return len(words) >= 7 and len(" ".join(words)) >= 52


def _supporting_projection_tail(value: str) -> bool:
    words = {
        word.strip(".,;:()[]{}").casefold()
        for word in normalize_string(value).split()
        if word.strip(".,;:()[]{}")
    }
    return bool(words & _SUPPORTING_PROJECTION_TAIL_TERMS)


def _complete_semantic_source(semantic_model: Mapping[str, Any]) -> bool:
    return bool(
        semantic_model
        and isinstance(semantic_model.get("first_path_contract"), Mapping)
        and isinstance(semantic_model.get("domain_ontology"), Mapping)
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "CanonicalProjectionFact",
    "canonical_projection_facts",
    "canonical_projection_text_values",
]
