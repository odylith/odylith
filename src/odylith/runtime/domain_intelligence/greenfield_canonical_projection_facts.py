"""Canonical semantic facts that renderers may repeat across projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import replace
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import gerund_action_verb
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
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
_BASE_ACTION_CONTEXTS = frozenset(
    {"can", "could", "may", "might", "must", "shall", "should", "to", "will", "would"}
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


@dataclass(frozen=True)
class _FirstPathActionTerms:
    base: frozenset[str]
    finite: frozenset[str]
    gerund: frozenset[str]


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
    action_terms = _first_path_action_terms(first_path)
    values: list[str] = []
    for key in ("raw_path", "capability", "visible_result", "mutation", "recovery_path"):
        values.extend(_first_path_projection_values(first_path.get(key), action_terms))
    values.extend(
        value
        for step in _first_path_step_values(first_path.get("raw_path"))
        for value in _first_path_projection_values(step, action_terms)
    )
    events = first_path.get("events")
    if isinstance(events, Sequence) and not isinstance(events, (str, bytes, bytearray)):
        for item in events:
            if not isinstance(item, Mapping):
                continue
            for key in ("text", "mutation", "target_entity", "action"):
                values.extend(_first_path_projection_values(item.get(key), action_terms))
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


def _first_path_projection_values(value: Any, action_terms: _FirstPathActionTerms) -> list[str]:
    rows: list[str] = []
    for text in text_values(value):
        normalized = normalize_string(text)
        if not normalized:
            continue
        rows.append(normalized)
        rows.extend(_action_complement_projection_variants(normalized, action_terms))
    return list(unique_text(rows))


def _first_path_action_terms(first_path: Mapping[str, Any]) -> _FirstPathActionTerms:
    raw_terms: list[str] = []
    raw_terms.extend(text_values(first_path.get("action")))
    events = first_path.get("events")
    if isinstance(events, Sequence) and not isinstance(events, (str, bytes, bytearray)):
        for item in events:
            if isinstance(item, Mapping):
                raw_terms.extend(text_values(item.get("action")))
    base_terms: set[str] = set()
    finite_terms: set[str] = set()
    gerund_terms: set[str] = set()
    for raw_term in raw_terms:
        token = _first_word_token(raw_term).casefold()
        if not token:
            continue
        base = _first_word_token(base_action_clause(token)).casefold()
        if not base:
            continue
        finite = _first_word_token(third_person_action_verb(base)).casefold()
        gerund = _first_word_token(gerund_action_verb(base)).casefold()
        base_terms.add(base)
        if finite:
            finite_terms.add(finite)
        if gerund:
            gerund_terms.add(gerund)
    return _FirstPathActionTerms(
        base=frozenset(base_terms),
        finite=frozenset(finite_terms),
        gerund=frozenset(gerund_terms),
    )


def _action_complement_projection_variants(value: str, action_terms: _FirstPathActionTerms) -> list[str]:
    """Return coordinated object-list projections owned by a first-path action."""

    text = normalize_string(value).strip(" .")
    if not text or not (action_terms.base or action_terms.finite or action_terms.gerund):
        return []
    variants: list[str] = []
    for complement in _action_complement_candidates(text, action_terms):
        variants.extend(_coordinated_complement_projection_variants(complement))
    return list(unique_text(variants))


def _action_complement_candidates(value: str, action_terms: _FirstPathActionTerms) -> list[str]:
    rows: list[str] = []
    tokens = _word_token_spans(value)
    for index, (token, _start, end) in enumerate(tokens):
        if not _token_starts_action_complement(tokens, index, action_terms):
            continue
        complement = value[end:].strip(" ,.;:-")
        if complement:
            rows.append(complement)
    return list(unique_text(rows))


def _token_starts_action_complement(
    tokens: Sequence[tuple[str, int, int]],
    index: int,
    action_terms: _FirstPathActionTerms,
) -> bool:
    token = tokens[index][0].casefold()
    if token in action_terms.finite or token in action_terms.gerund:
        return True
    if token not in action_terms.base:
        return False
    previous = tokens[index - 1][0].casefold() if index > 0 else ""
    if previous in _BASE_ACTION_CONTEXTS:
        return True
    return index == 0 and not _next_token_looks_like_title_continuation(tokens, index)


def _next_token_looks_like_title_continuation(tokens: Sequence[tuple[str, int, int]], index: int) -> bool:
    if index + 1 >= len(tokens):
        return False
    token = tokens[index + 1][0]
    return bool(token[:1].isupper() and not token.isupper())


def _coordinated_complement_projection_variants(value: str) -> list[str]:
    text = normalize_string(value).strip(" .")
    if not _meaningful_projection_prefix(text) or not _looks_like_coordinated_projection(text):
        return []
    variants = [text]
    _head, separator, tail = text.partition(",")
    if separator:
        tail = tail.strip(" ,.;:-")
        if _meaningful_projection_prefix(tail) and _looks_like_coordinated_projection(tail):
            variants.append(tail)
    return list(unique_text(variants))


def _looks_like_coordinated_projection(value: str) -> bool:
    text = normalize_string(value)
    return "," in text or " and " in text.casefold()


def _first_word_token(value: Any) -> str:
    tokens = _word_tokens(value)
    return tokens[0] if tokens else ""


def _word_tokens(value: Any) -> list[str]:
    return [token for token, _start, _end in _word_token_spans(str(value or ""))]


def _word_token_spans(value: str) -> list[tuple[str, int, int]]:
    text = str(value or "")
    rows: list[tuple[str, int, int]] = []
    start: int | None = None
    current: list[str] = []
    for index, char in enumerate(text):
        if char.isalnum() or char in {"'", "-"}:
            if start is None:
                start = index
            current.append(char)
            continue
        if current and start is not None:
            rows.append(("".join(current).strip("-'"), start, index))
            current = []
            start = None
    if current and start is not None:
        rows.append(("".join(current).strip("-'"), start, len(text)))
    return [(token, start, end) for token, start, end in rows if token]


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
    return list(
        unique_text(
            step
            for step in (*first_path_model(raw).steps, *sequence_event_steps(raw))
            if normalize_string(step)
        )
    )


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
