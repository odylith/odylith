"""Project typed Greenfield semantics into exact atomic custody rows.

The authoring model owns fact selection and typed relations. Atomic ledger rows
repeat those choices with coordinates and hashes, so deterministic code owns
that bookkeeping instead of asking the model to restate its semantics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_ROLES,
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    intent_text_at_path,
)


_FACT_ATOM_POLICY = {
    "title": ("states", "affirmed"),
    "product_story": ("outputs", "affirmed"),
    "state_object": ("states", "affirmed"),
    "first_path": ("actions", "affirmed"),
    "proof_boundary": ("constraints", "required"),
    "problem": ("states", "affirmed"),
    "customer": ("actors", "affirmed"),
    "opportunity": ("outputs", "affirmed"),
    "product_view": ("outputs", "affirmed"),
    "success_metrics": ("outputs", "affirmed"),
    "evidence_requirements": ("constraints", "required"),
    "operational_constraints": ("constraints", "required"),
    "component_responsibilities": ("actions", "affirmed"),
    "human_actors": ("actors", "affirmed"),
    "external_systems": ("dependencies", "affirmed"),
    "internal_systems": ("states", "affirmed"),
    "non_goals": ("non_goals", "prohibited"),
}
_RELATION_ATOM_CATEGORY = {
    "actor_quote": "actors",
    "action_verb_quote": "actions",
    "target_quote": "states",
    "visible_result_quote": "outputs",
}


def derive_model_atomic_claims(
    *,
    intent: Mapping[str, Any],
    selected_facts: Sequence[Mapping[str, Any]],
    first_path_relations: Sequence[Mapping[str, Any]],
    terminal_result_fact: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Derive redundant atomic custody from model-owned facts and relations."""

    facts = tuple(selected_facts)
    facts_by_path = {
        str(fact.get("projection_path") or ""): fact
        for fact in facts
        if str(fact.get("projection_path") or "") != "/first_path"
    }
    rows = [_whole_fact_claim(intent=intent, fact=fact) for fact in facts]
    for relation in first_path_relations:
        event = str(relation.get("event_quote") or "")
        for role in AUTHORED_RELATION_ROLES:
            quote = str(relation.get(role) or "")
            if not quote:
                continue
            if role == "visible_result_quote":
                rows.append(
                    _terminal_result_claim(
                        intent=intent,
                        relation=relation,
                        terminal_result_fact=terminal_result_fact,
                    )
                )
                continue
            if role == "actor_quote" and quote not in event:
                rows.append(
                    _implicit_actor_claim(
                        intent=intent,
                        relation=relation,
                        actor_fact=facts_by_path.get(
                            str(relation.get("actor_fact_path") or "")
                        ),
                    )
                )
                continue
            rows.append(
                _path_relation_claim(
                    intent=intent,
                    selected_facts=facts,
                    relation=relation,
                    role=role,
                )
            )
    return tuple(rows)


def _terminal_result_claim(
    *,
    intent: Mapping[str, Any],
    relation: Mapping[str, Any],
    terminal_result_fact: Mapping[str, Any],
) -> dict[str, Any]:
    quote = str(relation.get("visible_result_quote") or "")
    if quote != str(terminal_result_fact.get("terminal_result_quote") or ""):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an ungrounded terminal result"
        )
    return _claim(
        intent=intent,
        fact=terminal_result_fact,
        quote=quote,
        category="outputs",
        polarity="affirmed",
        source_start=_integer(
            terminal_result_fact.get("terminal_result_source_start_byte")
        ),
        projection_start=_integer(
            terminal_result_fact.get("terminal_result_projection_start_byte")
        ),
        relation_order=_integer(relation.get("order")),
        relation_role="visible_result_quote",
    )


def _whole_fact_claim(
    *,
    intent: Mapping[str, Any],
    fact: Mapping[str, Any],
) -> dict[str, Any]:
    field = str(fact.get("field") or "")
    try:
        category, polarity = _FACT_ATOM_POLICY[field]
    except KeyError as exc:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unsupported typed fact"
        ) from exc
    quote = str(fact.get("quote") or "")
    return _claim(
        intent=intent,
        fact=fact,
        quote=quote,
        category=category,
        polarity=polarity,
        source_start=_integer(fact.get("source_start_byte")),
        projection_start=_integer(fact.get("projection_start_byte")),
    )


def _path_relation_claim(
    *,
    intent: Mapping[str, Any],
    selected_facts: Sequence[Mapping[str, Any]],
    relation: Mapping[str, Any],
    role: str,
) -> dict[str, Any]:
    event = str(relation.get("event_quote") or "")
    quote = str(relation.get(role) or "")
    role_start = event.encode("utf-8").find(quote.encode("utf-8"))
    if role_start < 0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an ungrounded atomic relation"
        )
    source_start = _integer(relation.get("source_start_byte")) + role_start
    source_end = source_start + len(quote.encode("utf-8"))
    path_fact = next(
        (
            fact
            for fact in selected_facts
            if str(fact.get("field") or "") == "first_path"
            and _integer(fact.get("source_start_byte")) <= source_start
            and source_end <= _integer(fact.get("source_end_byte"))
        ),
        None,
    )
    if path_fact is None:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unbound atomic relation"
        )
    return _claim(
        intent=intent,
        fact=path_fact,
        quote=quote,
        category=_RELATION_ATOM_CATEGORY[role],
        polarity="affirmed",
        source_start=source_start,
        projection_start=_integer(relation.get("event_start_byte")) + role_start,
        relation_order=_integer(relation.get("order")),
        relation_role=role,
    )


def _implicit_actor_claim(
    *,
    intent: Mapping[str, Any],
    relation: Mapping[str, Any],
    actor_fact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    actor_fact_quote = str(relation.get("actor_fact_quote") or "")
    if (
        actor_fact is None
        or relation.get("actor_is_carried") is not True
        or actor_fact_quote != str(actor_fact.get("quote") or "")
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an ungrounded atomic actor"
        )
    return _claim(
        intent=intent,
        fact=actor_fact,
        quote=actor_fact_quote,
        category="actors",
        polarity="affirmed",
        source_start=_integer(actor_fact.get("source_start_byte")),
        projection_start=_integer(actor_fact.get("projection_start_byte")),
        relation_order=_integer(relation.get("order")),
        relation_role="actor_quote",
    )


def _claim(
    *,
    intent: Mapping[str, Any],
    fact: Mapping[str, Any],
    quote: str,
    category: str,
    polarity: str,
    source_start: int,
    projection_start: int,
    relation_order: int = 0,
    relation_role: str = "",
) -> dict[str, Any]:
    if not quote:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an empty atomic fact"
        )
    field = str(fact.get("field") or "")
    projection_path = str(fact.get("projection_path") or "")
    projection_value = intent_text_at_path(intent, projection_path)
    if not projection_value:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid atomic projection"
        )
    quote_bytes = quote.encode("utf-8")
    return {
        "field": field,
        "category": category,
        "polarity": polarity,
        "source_start_byte": source_start,
        "source_end_byte": source_start + len(quote_bytes),
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote_bytes).hexdigest(),
        "projection_path": projection_path,
        "projection_start_byte": projection_start,
        "projection_end_byte": projection_start + len(quote_bytes),
        "projection_value_sha256": hashlib.sha256(
            projection_value.encode("utf-8")
        ).hexdigest(),
        "relation_order": relation_order,
        "relation_role": relation_role,
    }


def _integer(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid atomic coordinates"
        )
    return value


__all__ = ["derive_model_atomic_claims"]
