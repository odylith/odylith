"""Exact independent relation evidence for Greenfield semantic release scoring."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from typing import Any

from greenfield_matrix_release_artifacts import is_sha256
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_ROLES,
    AUTHORED_SEMANTICS_VERSION,
    COMPONENT_RESPONSIBILITY_RELATION_FIELDS,
    COMPONENT_RESPONSIBILITY_SOURCES,
    FIRST_PATH_ACTOR_KINDS,
    FIRST_PATH_CONTEXT_KINDS,
    FIRST_PATH_CONTEXT_RELATION_FIELDS,
    FIRST_PATH_RELATION_FIELDS,
    GreenfieldAuthoredSemanticsError,
    authored_relation_set_sha256,
    combined_prompt_evidence_source,
    expected_first_path_context_event_order,
)
from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    event_target_is_source_bound,
    intent_terminal_result_values,
)


RELATION_FIDELITY_ANNOTATION_VERSION = "odylith.greenfield.relation-fidelity-annotation.v2"
RELATION_FAMILIES = (
    "first_path_events",
    "context_relations",
    "component_responsibility_relations",
)
_ANNOTATION_FIELDS = frozenset({"version", *RELATION_FAMILIES})
_SEMANTICS_FIELDS = frozenset(
    {
        "version",
        "first_path_relations",
        "first_path_context_relations",
        "component_responsibility_relations",
    }
)
_EVENT_FIELDS = frozenset(
    {
        "order",
        "source_start_byte",
        "source_end_byte",
        "event_start_byte",
        "event_end_byte",
        "event_sha256",
        "actor_kind",
        "actor_sha256",
        "actor_fact_path",
        "actor_fact_sha256",
        "product_owner_path",
        "product_owner_sha256",
        "action_verb_sha256",
        "target_sha256",
        "visible_result_sha256",
    }
)
_EVENT_ACTOR_KIND_INDEX = 7
_EVENT_OWNER_PATH_INDEX = 11
_EVENT_OWNER_SHA_INDEX = 12
_EVENT_VISIBLE_SHA_INDEX = 15
_CONTEXT_FIELDS = frozenset(
    {
        "context_kind",
        "fact_path",
        "fact_sha256",
        "source_start_byte",
        "source_end_byte",
        "first_path_event_order",
    }
)
_COMPONENT_FIELDS = frozenset(
    {
        "responsibility_path",
        "responsibility_sha256",
        "product_owner_path",
        "product_owner_sha256",
        "first_path_event_order",
        "responsibility_source",
    }
)


@dataclass(frozen=True)
class RelationFidelityEvidence:
    """Canonical relation identities plus structural evidence issues."""

    keys: Mapping[str, tuple[tuple[Any, ...], ...]]
    minimum_samples: Mapping[str, int]
    issues: tuple[str, ...]
    @property
    def sample_count(self) -> int:
        return sum(
            max(len(self.keys.get(family, ())), int(self.minimum_samples.get(family, 0)))
            for family in RELATION_FAMILIES
        )


def annotation_relation_evidence(
    *,
    case: Any,
    value: Any,
    atom_rows: Any,
) -> RelationFidelityEvidence:
    """Validate independently authored relation truth against exact source custody."""

    issues: list[str] = []
    if not isinstance(value, Mapping) or set(value) != _ANNOTATION_FIELDS:
        return _empty_evidence("relation_fidelity must use the exact v2 typed fields")
    if value.get("version") != RELATION_FIDELITY_ANNOTATION_VERSION:
        issues.append(
            "relation_fidelity must declare "
            f"{RELATION_FIDELITY_ANNOTATION_VERSION}"
        )
    source_bytes = combined_prompt_evidence_source(
        prompt=str(getattr(case, "prompt", "") or ""),
        edit_evidence=str(getattr(case, "confirmed_intent_markdown", "") or ""),
    ).encode("utf-8")
    projection_identities, role_hashes = _annotation_atom_indexes(atom_rows)
    events, event_issues = _annotation_event_keys(
        value.get("first_path_events"),
        source_bytes=source_bytes,
        projection_identities=projection_identities,
        role_hashes=role_hashes,
    )
    issues.extend(event_issues)
    event_by_order = {
        int(key[1]): key
        for key in events
        if isinstance(key[1], int) and not isinstance(key[1], bool)
    }
    contexts, context_issues = _annotation_context_keys(
        value.get("context_relations"),
        source_bytes=source_bytes,
        first_path_relations=_mapping_rows(value.get("first_path_events")) or (),
        projection_identities=projection_identities,
    )
    issues.extend(context_issues)
    selected_contexts = _annotation_context_facts(projection_identities)
    issues.extend(
        _context_completeness_issues(
            expected=selected_contexts,
            observed=Counter((key[1], key[2], key[3]) for key in contexts),
            label="relation_fidelity",
        )
    )
    components, component_issues = _annotation_component_keys(
        value.get("component_responsibility_relations"),
        event_by_order=event_by_order,
        projection_identities=projection_identities,
    )
    issues.extend(component_issues)
    selected_responsibilities = _annotation_responsibility_facts(
        projection_identities
    )
    issues.extend(
        _component_completeness_issues(
            selected=selected_responsibilities,
            observed=components,
            label="relation_fidelity",
        )
    )
    return RelationFidelityEvidence(
        keys={
            "first_path_events": events,
            "context_relations": contexts,
            "component_responsibility_relations": components,
        },
        minimum_samples={
            "first_path_events": len(events),
            "context_relations": sum(selected_contexts.values()),
            "component_responsibility_relations": (
                sum(selected_responsibilities.values()) or 1
            ),
        },
        issues=tuple(dict.fromkeys(issues)),
    )


def snapshot_relation_evidence(
    *,
    case: Any,
    snapshot: Mapping[str, Any],
) -> RelationFidelityEvidence:
    """Read exact sealed relation identities without reinterpreting their language."""

    facts = _mapping(snapshot.get("facts"))
    semantics = snapshot.get("authored_semantics")
    if not isinstance(semantics, Mapping):
        return _empty_evidence("sealed semantic snapshot lacks authored_semantics")
    if (
        semantics.get("version") != AUTHORED_SEMANTICS_VERSION
        or set(semantics) != _SEMANTICS_FIELDS
    ):
        return _empty_evidence("sealed authored_semantics has an invalid closed schema")
    events = _mapping_rows(semantics.get("first_path_relations"))
    contexts = _mapping_rows(semantics.get("first_path_context_relations"))
    components = _mapping_rows(semantics.get("component_responsibility_relations"))
    if events is None or contexts is None or components is None:
        return _empty_evidence("sealed authored_semantics contains malformed relation rows")
    try:
        digest = authored_relation_set_sha256(
            events,
            components,
            first_path_context_relations=contexts,
        )
    except (TypeError, ValueError):
        return _empty_evidence("sealed authored_semantics relation set is malformed")
    if str(snapshot.get("authored_relation_set_sha256") or "") != digest:
        return _empty_evidence("sealed authored_semantics does not match its authority digest")

    source_bytes = combined_prompt_evidence_source(
        prompt=str(getattr(case, "prompt", "") or ""),
        edit_evidence=str(getattr(case, "confirmed_intent_markdown", "") or ""),
    ).encode("utf-8")
    event_keys, event_issues = _snapshot_event_keys(
        events,
        facts=facts,
        source_bytes=source_bytes,
    )
    context_keys, context_issues = _snapshot_context_keys(
        contexts,
        facts=facts,
        source_bytes=source_bytes,
        first_path_relations=events,
    )
    selected_contexts = _snapshot_context_facts(facts)
    context_issues = (
        *context_issues,
        *_context_completeness_issues(
            expected=selected_contexts,
            observed=Counter((key[1], key[2], key[3]) for key in context_keys),
            label="sealed authored_semantics",
        ),
    )
    component_keys, component_issues = _snapshot_component_keys(
        components,
        facts=facts,
        events_by_order={
            order: row
            for row in events
            if (order := _positive_int(row.get("order"))) is not None
        },
    )
    selected_responsibilities = _snapshot_responsibility_facts(facts)
    component_issues = (
        *component_issues,
        *_component_completeness_issues(
            selected=selected_responsibilities,
            observed=component_keys,
            label="sealed authored_semantics",
        ),
    )
    return RelationFidelityEvidence(
        keys={
            "first_path_events": event_keys,
            "context_relations": context_keys,
            "component_responsibility_relations": component_keys,
        },
        minimum_samples={
            "first_path_events": len(event_keys),
            "context_relations": sum(selected_contexts.values()),
            "component_responsibility_relations": (
                sum(selected_responsibilities.values()) or 1
            ),
        },
        issues=tuple(
            dict.fromkeys((*event_issues, *context_issues, *component_issues))
        ),
    )


def _annotation_event_keys(
    value: Any,
    *,
    source_bytes: bytes,
    projection_identities: frozenset[tuple[str, str]],
    role_hashes: Mapping[tuple[int, str], frozenset[str]],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[str, ...]]:
    rows = _mapping_rows(value)
    if rows is None or not rows:
        return (), ("relation_fidelity requires at least one first_path event",)
    issues: list[str] = []
    keys: list[tuple[Any, ...]] = []
    projection_cursor = 0
    for index, row in enumerate(rows, start=1):
        label = f"relation_fidelity first_path_events[{index}]"
        if set(row) != _EVENT_FIELDS:
            issues.append(f"{label} must use the exact typed event fields")
            continue
        order = _positive_int(row.get("order"))
        source_range = _range(row.get("source_start_byte"), row.get("source_end_byte"))
        projection_range = _range(row.get("event_start_byte"), row.get("event_end_byte"))
        event_sha = str(row.get("event_sha256") or "")
        actor_kind = str(row.get("actor_kind") or "")
        actor_sha = str(row.get("actor_sha256") or "")
        actor_path = str(row.get("actor_fact_path") or "")
        actor_fact_sha = str(row.get("actor_fact_sha256") or "")
        owner_path = str(row.get("product_owner_path") or "")
        owner_sha = str(row.get("product_owner_sha256") or "")
        action_sha = str(row.get("action_verb_sha256") or "")
        target_sha = str(row.get("target_sha256") or "")
        visible_sha = str(row.get("visible_result_sha256") or "")
        if order != index:
            issues.append(f"{label} order must be contiguous and one-based")
        if not _source_hash_matches(source_bytes, source_range, event_sha):
            issues.append(f"{label} event source custody is invalid")
        if (
            projection_range is None
            or projection_range[0] < projection_cursor
            or source_range is None
            or projection_range[1] - projection_range[0]
            != source_range[1] - source_range[0]
        ):
            issues.append(f"{label} event projection custody is invalid")
        else:
            projection_cursor = projection_range[1]
        if actor_kind not in FIRST_PATH_ACTOR_KINDS:
            issues.append(f"{label} actor_kind is invalid")
        if not is_sha256(actor_sha):
            issues.append(f"{label} actor_sha256 is invalid")
        if not _actor_path_matches_kind(actor_path, actor_kind):
            issues.append(f"{label} actor fact path is invalid for its actor kind")
        if (actor_path, actor_fact_sha) not in projection_identities:
            issues.append(f"{label} actor fact identity is not atom-grounded")
        if role_hashes.get((index, "actor_quote"), frozenset()) != frozenset({actor_sha}):
            issues.append(f"{label} actor quote is not atom-grounded at its event order")
        if actor_kind == "product":
            if (
                owner_path != actor_path or owner_sha != actor_fact_sha
                or not _product_owner_path(owner_path)
            ):
                issues.append(f"{label} product owner identity is invalid")
        elif owner_path or owner_sha:
            issues.append(f"{label} non-product event must not declare a product owner")
        if not is_sha256(action_sha) or role_hashes.get(
            (index, "action_verb_quote"), frozenset()
        ) != frozenset({action_sha}):
            issues.append(f"{label} action verb is not atom-grounded")
        if target_sha:
            if not is_sha256(target_sha) or role_hashes.get(
                (index, "target_quote"), frozenset()
            ) != frozenset({target_sha}):
                issues.append(f"{label} target is not atom-grounded")
        elif role_hashes.get((index, "target_quote"), frozenset()):
            issues.append(f"{label} omits an atom-grounded target")
        if visible_sha:
            if not is_sha256(visible_sha):
                issues.append(f"{label} visible_result_sha256 is invalid")
            if role_hashes.get((index, "visible_result_quote"), frozenset()) != frozenset(
                {visible_sha}
            ):
                issues.append(f"{label} visible result is not atom-grounded")
        elif role_hashes.get((index, "visible_result_quote"), frozenset()):
            issues.append(f"{label} omits an atom-grounded visible result")
        keys.append(
            (
                "event",
                order,
                *(source_range or (-1, -1)),
                *(projection_range or (-1, -1)),
                event_sha,
                actor_kind,
                actor_sha,
                actor_path,
                actor_fact_sha,
                owner_path,
                owner_sha,
                action_sha,
                target_sha,
                visible_sha,
            )
        )
    if len(keys) != len(set(keys)):
        issues.append("relation_fidelity first_path events must have unique exact identities")
    return tuple(keys), tuple(issues)


def _annotation_context_keys(
    value: Any,
    *,
    source_bytes: bytes,
    first_path_relations: Sequence[Mapping[str, Any]],
    projection_identities: frozenset[tuple[str, str]],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[str, ...]]:
    rows = _mapping_rows(value)
    if rows is None:
        return (), ("relation_fidelity context_relations must be an array",)
    issues: list[str] = []
    keys: list[tuple[Any, ...]] = []
    for index, row in enumerate(rows, start=1):
        label = f"relation_fidelity context_relations[{index}]"
        if set(row) != _CONTEXT_FIELDS:
            issues.append(f"{label} must use the exact typed context fields")
            continue
        kind = str(row.get("context_kind") or "")
        path = str(row.get("fact_path") or "")
        fact_sha = str(row.get("fact_sha256") or "")
        source_range = _range(row.get("source_start_byte"), row.get("source_end_byte"))
        event_order = _nonnegative_int(row.get("first_path_event_order"))
        if kind not in FIRST_PATH_CONTEXT_KINDS or not _context_path_matches_kind(path, kind):
            issues.append(f"{label} context fact identity is invalid")
        if (path, fact_sha) not in projection_identities:
            issues.append(f"{label} context fact identity is not atom-grounded")
        if not _source_hash_matches(source_bytes, source_range, fact_sha):
            issues.append(f"{label} context source custody is invalid")
        if event_order is None or event_order != _product_context_event_order(
            source_range=source_range,
            first_path_relations=first_path_relations,
        ):
            issues.append(f"{label} event linkage is invalid")
        keys.append(
            (
                "context",
                kind,
                path,
                fact_sha,
                *(source_range or (-1, -1)),
                event_order if event_order is not None else -1,
            )
        )
    if len(keys) != len(set(keys)):
        issues.append("relation_fidelity context relations must have unique exact identities")
    return tuple(keys), tuple(issues)


def _annotation_component_keys(
    value: Any,
    *,
    event_by_order: Mapping[int, tuple[Any, ...]],
    projection_identities: frozenset[tuple[str, str]],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[str, ...]]:
    rows = _mapping_rows(value)
    if rows is None or not rows:
        return (), ("relation_fidelity requires component responsibility ownership",)
    issues: list[str] = []
    keys: list[tuple[Any, ...]] = []
    for index, row in enumerate(rows, start=1):
        label = f"relation_fidelity component_responsibility_relations[{index}]"
        if set(row) != _COMPONENT_FIELDS:
            issues.append(f"{label} must use the exact typed component fields")
            continue
        responsibility_path = str(row.get("responsibility_path") or "")
        responsibility_sha = str(row.get("responsibility_sha256") or "")
        owner_path = str(row.get("product_owner_path") or "")
        owner_sha = str(row.get("product_owner_sha256") or "")
        event_order = _nonnegative_int(row.get("first_path_event_order"))
        source = str(row.get("responsibility_source") or "")
        event = event_by_order.get(event_order or -1)
        if not _product_owner_path(owner_path) or (owner_path, owner_sha) not in projection_identities:
            issues.append(f"{label} product owner identity is not atom-grounded")
        if event_order is None or (event_order and event is None):
            issues.append(f"{label} event linkage is invalid")
        if event is not None and event[_EVENT_ACTOR_KIND_INDEX] == "product" and (
            owner_path != event[_EVENT_OWNER_PATH_INDEX]
            or owner_sha != event[_EVENT_OWNER_SHA_INDEX]
        ):
            issues.append(f"{label} product owner contradicts its linked event")
        if source not in COMPONENT_RESPONSIBILITY_SOURCES:
            issues.append(f"{label} responsibility_source is invalid")
        elif source == "accepted_fact":
            if not _list_path(responsibility_path, "component_responsibilities") or (
                responsibility_path,
                responsibility_sha,
            ) not in projection_identities:
                issues.append(f"{label} accepted responsibility is not atom-grounded")
        elif (
            responsibility_path != "/first_path"
            or event is None
            or not responsibility_sha
            or responsibility_sha != event[_EVENT_VISIBLE_SHA_INDEX]
        ):
            issues.append(f"{label} terminal responsibility does not match its visible result")
        keys.append(
            (
                "component",
                responsibility_path,
                responsibility_sha,
                owner_path,
                owner_sha,
                event_order if event_order is not None else -1,
                source,
            )
        )
    if len(keys) != len(set(keys)):
        issues.append("relation_fidelity component relations must have unique exact identities")
    return tuple(keys), tuple(issues)


def _snapshot_event_keys(
    rows: Sequence[Mapping[str, Any]],
    *,
    facts: Mapping[str, Any],
    source_bytes: bytes,
) -> tuple[tuple[tuple[Any, ...], ...], tuple[str, ...]]:
    first_path = str(facts.get("first_path") or "")
    path_bytes = first_path.encode("utf-8")
    issues: list[str] = []
    keys: list[tuple[Any, ...]] = []
    cursor = 0
    for index, row in enumerate(rows, start=1):
        label = f"sealed first_path_relations[{index}]"
        if set(row) != FIRST_PATH_RELATION_FIELDS:
            issues.append(f"{label} has an invalid closed schema")
            continue
        order = _positive_int(row.get("order"))
        source_range = _range(row.get("source_start_byte"), row.get("source_end_byte"))
        projection_range = _range(row.get("event_start_byte"), row.get("event_end_byte"))
        event_quote = str(row.get("event_quote") or "")
        actor_kind = str(row.get("actor_kind") or "")
        actor_quote = str(row.get("actor_quote") or "")
        actor_is_carried = row.get("actor_is_carried")
        actor_fact_path = str(row.get("actor_fact_path") or "")
        actor_fact_quote = str(row.get("actor_fact_quote") or "")
        owner_path = str(row.get("owner_system_path") or "")
        owner_quote = str(row.get("owner_system_quote") or "")
        action_quote = str(row.get("action_verb_quote") or "")
        target_quote = str(row.get("target_quote") or "")
        visible_quote = str(row.get("visible_result_quote") or "")
        if order != index:
            issues.append(f"{label} order is not contiguous and one-based")
        if not _exact_slice(source_bytes, source_range, event_quote):
            issues.append(f"{label} source range does not contain its exact event")
        if (
            projection_range is None
            or projection_range[0] < cursor
            or not _exact_slice(path_bytes, projection_range, event_quote)
        ):
            issues.append(f"{label} projection range does not contain its exact event")
        else:
            cursor = projection_range[1]
        if (
            actor_kind not in FIRST_PATH_ACTOR_KINDS
            or not actor_quote
            or not isinstance(actor_is_carried, bool)
        ):
            issues.append(f"{label} actor identity is invalid")
        if not action_quote or action_quote not in event_quote:
            issues.append(f"{label} action is not exactly grounded in its event")
        if not event_target_is_source_bound(
            event_quote=event_quote,
            target_quote=target_quote,
        ):
            issues.append(f"{label} target is not exactly grounded in its event")
        if (
            not _actor_path_matches_kind(actor_fact_path, actor_kind)
            or _projection_value(facts, actor_fact_path) != actor_fact_quote
        ):
            issues.append(f"{label} actor fact does not match its exact selected fact")
        if (
            actor_quote != actor_fact_quote
            or isinstance(actor_is_carried, bool)
            and actor_is_carried == (actor_fact_quote in event_quote)
        ):
            issues.append(f"{label} actor carry state does not match its selected fact")
        if actor_kind == "product":
            if (
                owner_path != actor_fact_path
                or owner_quote != actor_fact_quote
                or not _product_owner_path(owner_path)
            ):
                issues.append(f"{label} product owner is not bound to its exact selected fact")
        elif owner_path or owner_quote:
            issues.append(f"{label} non-product event declares a product owner")
        if visible_quote and not any(
            visible_quote in fact for fact in intent_terminal_result_values(facts)
        ):
            issues.append(f"{label} visible result is not bound to an eligible source fact")
        keys.append(
            (
                "event",
                order,
                *(source_range or (-1, -1)),
                *(projection_range or (-1, -1)),
                _sha256(event_quote),
                actor_kind,
                _sha256(actor_quote),
                actor_fact_path,
                _sha256(actor_fact_quote) if actor_fact_quote else "",
                owner_path,
                _sha256(owner_quote) if owner_quote else "",
                _sha256(action_quote) if action_quote else "",
                _sha256(target_quote) if target_quote else "",
                _sha256(visible_quote) if visible_quote else "",
            )
        )
    if not keys:
        issues.append("sealed authored_semantics has no first_path events")
    if len(keys) != len(set(keys)):
        issues.append("sealed first_path event identities are duplicated")
    return tuple(keys), tuple(issues)


def _snapshot_context_keys(
    rows: Sequence[Mapping[str, Any]],
    *,
    facts: Mapping[str, Any],
    source_bytes: bytes,
    first_path_relations: Sequence[Mapping[str, Any]],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[str, ...]]:
    issues: list[str] = []
    keys: list[tuple[Any, ...]] = []
    for index, row in enumerate(rows, start=1):
        label = f"sealed first_path_context_relations[{index}]"
        if set(row) != FIRST_PATH_CONTEXT_RELATION_FIELDS:
            issues.append(f"{label} has an invalid closed schema")
            continue
        kind = str(row.get("context_kind") or "")
        path = str(row.get("fact_path") or "")
        quote = str(row.get("fact_quote") or "")
        source_range = _range(row.get("source_start_byte"), row.get("source_end_byte"))
        event_order = _nonnegative_int(row.get("first_path_event_order"))
        if kind not in FIRST_PATH_CONTEXT_KINDS or not _context_path_matches_kind(path, kind):
            issues.append(f"{label} has an invalid typed fact path")
        if _projection_value(facts, path) != quote:
            issues.append(f"{label} does not match its exact selected fact")
        if not _exact_slice(source_bytes, source_range, quote):
            issues.append(f"{label} does not match its exact source range")
        if event_order is None or event_order != _product_context_event_order(
            source_range=source_range,
            first_path_relations=first_path_relations,
        ):
            issues.append(f"{label} has an invalid event linkage")
        keys.append(
            (
                "context",
                kind,
                path,
                _sha256(quote),
                *(source_range or (-1, -1)),
                event_order if event_order is not None else -1,
            )
        )
    if len(keys) != len(set(keys)):
        issues.append("sealed context relation identities are duplicated")
    return tuple(keys), tuple(issues)


def _product_context_event_order(
    *,
    source_range: tuple[int, int] | None,
    first_path_relations: Sequence[Mapping[str, Any]],
) -> int | None:
    if source_range is None:
        return None
    try:
        return expected_first_path_context_event_order(
            source_start=source_range[0],
            source_end=source_range[1],
            first_path_relations=first_path_relations,
        )
    except GreenfieldAuthoredSemanticsError:
        return None


def _snapshot_component_keys(
    rows: Sequence[Mapping[str, Any]],
    *,
    facts: Mapping[str, Any],
    events_by_order: Mapping[int, Mapping[str, Any]],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[str, ...]]:
    issues: list[str] = []
    keys: list[tuple[Any, ...]] = []
    for index, row in enumerate(rows, start=1):
        label = f"sealed component_responsibility_relations[{index}]"
        if set(row) != COMPONENT_RESPONSIBILITY_RELATION_FIELDS:
            issues.append(f"{label} has an invalid closed schema")
            continue
        responsibility_path = str(row.get("responsibility_path") or "")
        responsibility_quote = str(row.get("responsibility_quote") or "")
        owner_path = str(row.get("owner_system_path") or "")
        owner_quote = str(row.get("owner_system_quote") or "")
        event_order = _nonnegative_int(row.get("first_path_event_order"))
        source = str(row.get("responsibility_source") or "")
        event = events_by_order.get(event_order or -1)
        if _projection_value(facts, owner_path) != owner_quote or not _product_owner_path(owner_path):
            issues.append(f"{label} does not match its exact product owner")
        if event_order is None or (event_order and event is None):
            issues.append(f"{label} has an invalid event linkage")
        if event is not None and str(event.get("actor_kind") or "") == "product" and (
            str(event.get("owner_system_path") or "") != owner_path
        ):
            issues.append(f"{label} contradicts its linked product event owner")
        if source == "accepted_fact":
            if _projection_value(facts, responsibility_path) != responsibility_quote:
                issues.append(f"{label} does not match its exact responsibility fact")
        elif source == "terminal_visible_result":
            if (
                responsibility_path != "/first_path"
                or event is None
                or str(event.get("visible_result_quote") or "") != responsibility_quote
            ):
                issues.append(f"{label} does not match its exact terminal visible result")
        else:
            issues.append(f"{label} has an invalid responsibility_source")
        keys.append(
            (
                "component",
                responsibility_path,
                _sha256(responsibility_quote),
                owner_path,
                _sha256(owner_quote),
                event_order if event_order is not None else -1,
                source,
            )
        )
    if not keys:
        issues.append("sealed authored_semantics has no component responsibility ownership")
    if len(keys) != len(set(keys)):
        issues.append("sealed component relation identities are duplicated")
    return tuple(keys), tuple(issues)


def _annotation_atom_indexes(
    value: Any,
) -> tuple[frozenset[tuple[str, str]], Mapping[tuple[int, str], frozenset[str]]]:
    projections: set[tuple[str, str]] = set()
    roles: dict[tuple[int, str], set[str]] = {}
    for atom in _mapping_rows(value) or ():
        source = _mapping(atom.get("source"))
        quote_sha = str(source.get("quote_sha256") or "")
        for link in _mapping_rows(atom.get("projection_links")) or ():
            path = str(link.get("path") or "")
            value_sha = str(link.get("value_sha256") or "")
            if path and value_sha:
                projections.add((path, value_sha))
            order = _positive_int(link.get("relation_order"))
            role = str(link.get("relation_role") or "")
            if order and role in AUTHORED_RELATION_ROLES and quote_sha:
                roles.setdefault((order, role), set()).add(quote_sha)
    return frozenset(projections), {
        key: frozenset(values) for key, values in roles.items()
    }


def _projection_value(facts: Mapping[str, Any], path: str) -> str | None:
    if not path.startswith("/"):
        return None
    parts = path.split("/")[1:]
    if len(parts) == 1:
        value = facts.get(parts[0])
        return value if isinstance(value, str) and value else None
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    rows = _string_rows(facts.get(parts[0]))
    index = int(parts[1])
    return rows[index] if index < len(rows) else None


def _actor_path_matches_kind(path: str, kind: str) -> bool:
    if kind == "human":
        return _list_path(path, "human_actors")
    if kind == "external_system":
        return _list_path(path, "external_systems")
    return kind == "product" and _product_owner_path(path)


def _context_path_matches_kind(path: str, kind: str) -> bool:
    return {
        "state_object": path == "/state_object",
        "external_system": _list_path(path, "external_systems"),
        "operational_constraint": _list_path(path, "operational_constraints"),
    }.get(kind, False)


def _annotation_context_facts(
    projections: frozenset[tuple[str, str]],
) -> Counter[tuple[str, str, str]]:
    return Counter(
        (kind, path, digest)
        for path, digest in projections
        if (kind := _context_kind_for_path(path))
    )


def _snapshot_context_facts(
    facts: Mapping[str, Any],
) -> Counter[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    state = facts.get("state_object")
    if isinstance(state, str) and state:
        rows.append(("state_object", "/state_object", _sha256(state)))
    for kind, field in (
        ("external_system", "external_systems"),
        ("operational_constraint", "operational_constraints"),
    ):
        rows.extend(
            (kind, f"/{field}/{index}", _sha256(value))
            for index, value in enumerate(_string_rows(facts.get(field)))
        )
    return Counter(rows)


def _context_kind_for_path(path: str) -> str:
    if path == "/state_object":
        return "state_object"
    if _list_path(path, "external_systems"):
        return "external_system"
    if _list_path(path, "operational_constraints"):
        return "operational_constraint"
    return ""


def _context_completeness_issues(
    *,
    expected: Counter[tuple[str, str, str]],
    observed: Counter[tuple[str, str, str]],
    label: str,
) -> tuple[str, ...]:
    if expected == observed:
        return ()
    return (f"{label} context relations do not exactly cover selected context facts",)


def _annotation_responsibility_facts(
    projections: frozenset[tuple[str, str]],
) -> Counter[tuple[str, str]]:
    return Counter(
        (path, digest)
        for path, digest in projections
        if _list_path(path, "component_responsibilities")
    )


def _snapshot_responsibility_facts(
    facts: Mapping[str, Any],
) -> Counter[tuple[str, str]]:
    return Counter(
        (f"/component_responsibilities/{index}", _sha256(value))
        for index, value in enumerate(
            _string_rows(facts.get("component_responsibilities"))
        )
    )


def _component_completeness_issues(
    *,
    selected: Counter[tuple[str, str]],
    observed: Sequence[tuple[Any, ...]],
    label: str,
) -> tuple[str, ...]:
    accepted = Counter(
        (str(key[1]), str(key[2]))
        for key in observed
        if len(key) == 7 and key[6] == "accepted_fact"
    )
    terminal_count = sum(
        1
        for key in observed
        if len(key) == 7 and key[6] == "terminal_visible_result"
    )
    complete = (
        accepted == selected
        and terminal_count == 0
        and len(observed) == sum(accepted.values())
        if selected
        else len(observed) == 1 and terminal_count == 1 and not accepted
    )
    if complete:
        return ()
    return (
        f"{label} component relations do not exactly cover selected responsibilities",
    )


def _product_owner_path(path: str) -> bool:
    return path == "/title" or _list_path(path, "internal_systems")


def _list_path(path: str, field: str) -> bool:
    prefix = f"/{field}/"
    index = path.removeprefix(prefix) if path.startswith(prefix) else ""
    return bool(index.isdigit() and path == f"{prefix}{int(index)}")


def _source_hash_matches(
    source_bytes: bytes,
    byte_range: tuple[int, int] | None,
    expected_sha: str,
) -> bool:
    return bool(
        byte_range is not None
        and is_sha256(expected_sha)
        and _sha256_bytes(source_bytes[byte_range[0] : byte_range[1]]) == expected_sha
        and byte_range[1] <= len(source_bytes)
    )


def _exact_slice(
    source: bytes,
    byte_range: tuple[int, int] | None,
    value: str,
) -> bool:
    return bool(
        byte_range is not None
        and byte_range[1] <= len(source)
        and source[byte_range[0] : byte_range[1]] == value.encode("utf-8")
    )


def _range(start: Any, end: Any) -> tuple[int, int] | None:
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
    ):
        return None
    return start, end


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    if not all(isinstance(row, Mapping) for row in value):
        return None
    return tuple(value)


def _string_rows(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, str) and row)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sha256(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _empty_evidence(issue: str) -> RelationFidelityEvidence:
    return RelationFidelityEvidence(
        keys={family: () for family in RELATION_FAMILIES},
        minimum_samples={family: 0 for family in RELATION_FAMILIES},
        issues=(issue,),
    )

__all__ = [
    "RELATION_FAMILIES",
    "RELATION_FIDELITY_ANNOTATION_VERSION",
    "RelationFidelityEvidence",
    "annotation_relation_evidence",
    "snapshot_relation_evidence",
]
