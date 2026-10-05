"""Exact independent relation evidence for Greenfield semantic release scoring."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from greenfield_matrix_release_artifacts import is_sha256
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_ROLES,
    COMPONENT_RESPONSIBILITY_SOURCES,
    FIRST_PATH_ACTOR_KINDS,
    FIRST_PATH_CONTEXT_KINDS,
    GreenfieldAuthoredSemanticsError,
    authored_relation_set_sha256,
    combined_prompt_evidence_source,
    expected_first_path_context_event_order,
    component_responsibility_relations_from_intent,
    first_path_context_relations_from_intent,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    atomic_fact_ledger_hash,
    require_atomic_fact_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_hash,
    require_verified_source_action_relations,
)
from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import require_verified_greenfield_source_lifecycle


RELATION_FIDELITY_ANNOTATION_VERSION = "odylith.greenfield.relation-fidelity-annotation.v4"
RELATION_FAMILIES = (
    "first_path_events",
    "context_relations",
    "component_responsibility_relations",
)
_ANNOTATION_FIELDS = frozenset({"version", *RELATION_FAMILIES})
_EVENT_FIELDS = frozenset(
    {
        "order",
        "source_start_byte",
        "source_end_byte",
        "event_start_byte",
        "event_end_byte",
        "event_sha256",
        "actor_kind",
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
_EVENT_OWNER_PATH_INDEX = 10
_EVENT_OWNER_SHA_INDEX = 11
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
        return _empty_evidence("relation_fidelity must use the exact typed fields")
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
                sum(selected_responsibilities.values())
            ),
        },
        issues=tuple(dict.fromkeys(issues)),
    )


def snapshot_relation_evidence(
    *,
    case: Any,
    snapshot: Mapping[str, Any],
) -> RelationFidelityEvidence:
    """Validate exported custody using producer owners, then serialize relation identities.

    The snapshot omits raw candidate citations and source-span records. These
    checks do not reconstruct those records or constitute semantic qualification.
    """
    facts = _mapping(snapshot.get("facts"))
    semantics = snapshot.get("authored_semantics")
    if not isinstance(semantics, Mapping):
        return _empty_evidence("sealed semantic snapshot lacks authored_semantics")
    source_text = combined_prompt_evidence_source(
        prompt=str(getattr(case, "prompt", "") or ""),
        edit_evidence=str(getattr(case, "confirmed_intent_markdown", "") or ""),
    )
    source_bytes = source_text.encode("utf-8")
    intent = {**facts, "authored_semantics": semantics, "prompt": source_text}
    try:
        events = first_path_relations_from_intent(intent)
        contexts = first_path_context_relations_from_intent(intent)
        components = component_responsibility_relations_from_intent(intent)
        digest = authored_relation_set_sha256(
            events, components, first_path_context_relations=contexts,
            source_precedence=semantics["source_precedence"],
            source_duty=semantics["source_duty"],
            provisional_design=semantics["provisional_design"],
        )
        if snapshot.get("authored_relation_set_sha256") != digest:
            raise ValueError("sealed authored_semantics does not match its authority digest")
        require_verified_source_action_relations(
            events, source_duty=semantics["source_duty"], source_text=source_text,
        )
        if semantics["source_duty"] is not None:
            require_verified_greenfield_source_lifecycle(
                semantics["source_duty"], evidence_text=source_text,
                provisional_design=semantics["provisional_design"],
            )
        atoms = snapshot.get("atomic_facts")
        require_atomic_fact_ledger(atoms, facts=facts)
        if snapshot.get("atomic_custody_sha256") != atomic_fact_ledger_hash(atoms):
            raise ValueError("sealed atomic facts do not match their authority digest")
        if snapshot.get("product_facts_sha256") != product_facts_hash(facts):
            raise ValueError("sealed product facts do not match their authority digest")
        for atom in atoms:
            for witness in atom["source_span_refs"]:
                if not _source_hash_matches(
                    source_bytes, _range(witness["source_start_byte"], witness["source_end_byte"]),
                    witness["text_sha256"],
                ):
                    raise ValueError("sealed atomic witness does not match the exact source bytes")
        exact_rows = contexts if semantics["source_duty"] is not None else (*events, *contexts)
        for row in exact_rows:
            quote = row.get("event_quote", row.get("fact_quote"))
            if not _exact_slice(
                source_bytes, _range(row["source_start_byte"], row["source_end_byte"]), quote,
            ):
                raise ValueError("sealed relation does not match the exact source bytes")
    except (ValueError, TypeError, KeyError) as exc:
        return _empty_evidence(str(exc))

    event_keys = tuple(
        ("event", row["order"], row["source_start_byte"], row["source_end_byte"],
         row["event_start_byte"], row["event_end_byte"], _sha256(row["event_quote"]),
         row["actor_kind"], row["actor_fact_path"], _sha256(row["actor_fact_quote"]),
         row["owner_system_path"], _sha256(row["owner_system_quote"]) if row["owner_system_quote"] else "",
         _sha256(row["action_verb_quote"]), _sha256(row["target_quote"]) if row["target_quote"] else "",
         _sha256(row["visible_result_quote"]) if row["visible_result_quote"] else "")
        for row in events
    )
    context_keys = tuple(
        ("context", row["context_kind"], row["fact_path"], _sha256(row["fact_quote"]),
         row["source_start_byte"], row["source_end_byte"], row["first_path_event_order"])
        for row in contexts
    )
    component_keys = tuple(
        ("component", row["responsibility_path"], _sha256(row["responsibility_quote"]),
         row["owner_system_path"], _sha256(row["owner_system_quote"]),
         row["first_path_event_order"], row["responsibility_source"])
        for row in components
    )
    return RelationFidelityEvidence(
        keys={"first_path_events": event_keys, "context_relations": context_keys,
              "component_responsibility_relations": component_keys},
        minimum_samples={"first_path_events": len(events), "context_relations": len(contexts),
                         "component_responsibility_relations": len(components)},
        issues=(),
    )


def canonical_evidence_sha256(value: Any) -> str:
    """Hash a complete JSON value; source witness hashes instead hash exact bytes."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()


def observed_semantic_universe(*, case: Any, snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Enumerate all exported claims after canonical R1 custody validation.

    A fact outside the atomic ledger still needs reverse support.  Separate
    lifecycle effects and supporting events retain separate audit identities.
    """
    evidence = snapshot_relation_evidence(case=case, snapshot=snapshot)
    if evidence.issues:
        raise ValueError("; ".join(evidence.issues))
    universe: dict[str, dict[str, Any]] = {}
    semantics = snapshot["authored_semantics"]
    source = combined_prompt_evidence_source(prompt=case.prompt, edit_evidence=case.confirmed_intent_markdown).encode("utf-8")
    first_run = set(semantics["provisional_design"]["first_run"]["event_orders"])

    def add(path: str, value: Any, kind: str, *, row: Mapping[str, Any] | None = None) -> None:
        witness = ""
        roles: dict[str, str] = {}
        if row is not None:
            start, end = row.get("source_start_byte"), row.get("source_end_byte")
            if type(start) is int and type(end) is int:
                witness = hashlib.sha256(source[start:end]).hexdigest()
            roles = {key: _sha256(row[key]) for key in AUTHORED_RELATION_ROLES if isinstance(row.get(key), str) and row[key]}
        universe[path] = {"id": path, "kind": kind, "destination_sha256": canonical_evidence_sha256(value),
                          "source_witness_sha256": witness, "normalized_role_sha256": roles,
                          "custody_state": row.get("custody_state", "accepted_fact") if row else (
                              "assumption" if path.startswith("/facts/assumptions/") else
                              "ambiguity" if path.startswith("/facts/ambiguities/") else "accepted_fact")}

    def facts(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                facts(nested, path + "/" + str(key).replace("~", "~0").replace("/", "~1"))
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                facts(nested, path + "/" + str(index))
        elif isinstance(value, str) and value:
            add(path, value, "semantic_fact")

    facts(snapshot["facts"], "/facts")
    for index, row in enumerate(snapshot["atomic_facts"]):
        add(f"/atomic_facts/{index}", row, "atomic_fact", row=row)
    for family in RELATION_FAMILIES:
        field = "first_path_relations" if family == "first_path_events" else "first_path_context_relations" if family == "context_relations" else family
        for index, row in enumerate(semantics[field]):
            kind = family
            if family == "first_path_events":
                kind = "main_event" if row["order"] in first_run else "supporting_event"
            add(f"/authored_semantics/{field}/{index}", row, kind, row=row)
    material_custody = snapshot.get("material_custody", {})
    if not isinstance(material_custody, Mapping):
        raise ValueError("sealed material custody must be an object")
    for field, value in material_custody.items():
        if not isinstance(value, Mapping) or not isinstance(value.get("custody_state"), str) or not value["custody_state"].strip():
            raise ValueError(f"sealed material custody `{field}` must be an object with its actual custody state")
        add(f"/material_custody/{field}", value, "material_custody", row=value)
    design = semantics["provisional_design"]
    for field, value in design.items():
        if isinstance(value, list):
            for index, row in enumerate(value):
                add(f"/authored_semantics/provisional_design/{field}/{index}", row, "provisional_design")
        else:
            add(f"/authored_semantics/provisional_design/{field}", value, "provisional_design")
    for index, row in enumerate(semantics["source_precedence"]):
        add(f"/authored_semantics/source_precedence/{index}", row, "source_precedence")
    duty = semantics["source_duty"]
    if duty is not None:
        for family in ("state_fields", "off_path_transitions", "conditional_guards", "boundaries", "proof_duties"):
            for index, row in enumerate(duty["lifecycle"][family]):
                path = f"/authored_semantics/source_duty/lifecycle/{family}/{index}"
                add(path, row, "lifecycle_" + family)
                for effect_index, effect in enumerate(row.get("effects", ())):
                    add(path + f"/effects/{effect_index}", effect, "lifecycle_effect")
    return universe


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
        if not _actor_path_matches_kind(actor_path, actor_kind):
            issues.append(f"{label} actor fact path is invalid for its actor kind")
        if (actor_path, actor_fact_sha) not in projection_identities:
            issues.append(f"{label} actor fact identity is not atom-grounded")
        if role_hashes.get((index, "actor_fact_quote"), frozenset()) != frozenset(
            {actor_fact_sha}
        ):
            issues.append(f"{label} actor fact is not atom-grounded at its event order")
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
    if rows is None:
        return (), ("relation_fidelity component responsibility ownership must be an array",)
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
    complete = (
        accepted == selected
        and len(observed) == sum(accepted.values())
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
