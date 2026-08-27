"""Compact source-cited semantic authority for pre-confirm Greenfield intent."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    COMPLETE_FACT_COUNTS as _COMPLETE_FACT_COUNTS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    FACT_REQUIRED_ATTRIBUTES as _FACT_REQUIRED_ATTRIBUTES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    INTERNAL_SYSTEM_COMPONENT_KINDS,
    INTERNAL_SYSTEM_RELEASE_SCOPES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    LIST_NARRATIVE_FIELDS as _LIST_NARRATIVE_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    RELATION_ENDPOINT_KINDS as _RELATION_ENDPOINT_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_ATTRIBUTE_NAMES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_FACT_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_NARRATIVE_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_RELATION_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SINGULAR_NARRATIVE_FIELDS as _SINGULAR_NARRATIVE_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    semantic_intent_authoring_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    require_semantic_source_refs,
)
SEMANTIC_INTENT_IR_VERSION = "odylith.greenfield.semantic-intent-ir.v23"
SEMANTIC_INTENT_PACKET_VERSION = "odylith.greenfield.semantic-intent-packet.v35"

_CUSTODY_STATES = frozenset({"source_fact", "visible_assumption"})
_OWNER_KINDS = frozenset({"none", "actor", "product", "system"})
_RELATION_CUSTODY_STATES = frozenset({"source_fact"})
_ATTRIBUTE_NAMES = frozenset(SEMANTIC_ATTRIBUTE_NAMES)


def require_semantic_intent_ir(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    allow_empty_clarification_source_refs: bool = False,
) -> dict[str, Any]:
    """Validate graph structure and citations without interpreting prose."""

    ir = _mapping(value, "Semantic Intent IR")
    _exact_keys(
        ir,
        {
            "version",
            "status",
            "presentation",
            "clarification",
            "facts",
            "relations",
            "narratives",
        },
        "Semantic Intent IR",
    )
    if ir.get("version") != SEMANTIC_INTENT_IR_VERSION:
        raise ValueError("Semantic Intent IR uses an unsupported version")
    status = _enum(ir.get("status"), {"complete", "clarification_required"}, "status")
    _validate_presentation(ir.get("presentation"), evidence_sources=evidence_sources)
    clarification = _validate_clarification(
        ir.get("clarification"),
        evidence_sources=evidence_sources,
        required=status == "clarification_required",
        allow_empty_source_refs=allow_empty_clarification_source_refs,
    )
    facts = _validate_facts(ir.get("facts"), evidence_sources=evidence_sources)
    fact_index = {row["fact_id"]: row for row in facts}
    fact_ids = set(fact_index)
    if len(fact_index) != len(facts):
        raise ValueError("Semantic Intent IR fact ids are not unique")
    _require_unique_state_transitions(facts)
    relations = _validate_relations(
        ir.get("relations"), evidence_sources=evidence_sources, fact_index=fact_index
    )
    narratives = _validate_narratives(
        ir.get("narratives"), evidence_sources=evidence_sources, fact_ids=fact_ids
    )
    if status == "clarification_required" and (
        facts or relations or narratives
    ):
        raise ValueError("clarification-bound Semantic Intent IR must not carry semantic graph rows")
    if status == "clarification_required":
        return dict(ir)
    if clarification["question"]:
        raise ValueError("complete Semantic Intent IR carries a clarification request")
    _require_complete_material_graph(
        facts=facts,
        relations=relations,
        narratives=narratives,
    )
    return dict(ir)


def semantic_intent_product_facts(ir: Mapping[str, Any]) -> dict[str, Any]:
    """Project canonical product facts from verified graph nodes."""

    if ir.get("status") != "complete":
        raise ValueError("clarification-bound Semantic Intent IR has no product-fact projection")
    facts = list(ir["facts"])
    by_kind = _facts_by_kind(facts)
    narratives = _narratives_by_field(ir["narratives"])
    projected: dict[str, Any] = {
        "product_story": narratives["product_story"][0]["text"],
        "state_objects": [row["label"] for row in by_kind["state_object"]],
        "visible_outputs": [row["label"] for row in by_kind["visible_output"]],
        "first_path": " ".join(_sentence(_attribute(row, "action_phrase")) for row in by_kind["workflow_step"]),
        "proof_boundary": narratives["proof_boundary"][0]["text"],
        "problem": narratives["problem"][0]["text"],
        "customer": narratives["customer"][0]["text"],
        "opportunity": narratives["opportunity"][0]["text"],
        "product_view": narratives["product_view"][0]["text"],
        "success_metrics": [row["text"] for row in narratives["success_metric"]],
        "evidence_requirements": [row["text"] for row in narratives["evidence_requirement"]],
        "human_actors": _actor_views(
            by_kind["actor"],
            by_kind["workflow_step"],
            ir["relations"],
        ),
        "entities": [
            {
                "entity_id": row["fact_id"],
                "label": row["label"],
            }
            for row in by_kind["entity"]
        ],
        "audiences": [
            {"kind": _attribute(row, "audience_kind"), "label": row["label"]}
            for row in by_kind["audience"]
        ],
        "external_systems": [row["label"] for row in by_kind["external_system"]],
        "internal_systems": [row["statement"] for row in by_kind["internal_system"]],
        "component_responsibilities": [row["statement"] for row in by_kind["component_responsibility"]],
        "product_boundaries": [row["statement"] for row in by_kind["product_boundary"]],
        "policy_boundaries": [
            _policy_boundary_view(
                row,
                relations=ir["relations"],
                fact_index={str(fact["fact_id"]): fact for fact in facts},
            )
            for row in by_kind["policy_boundary"]
        ],
        "assumptions": [row["label"] for row in by_kind["assumption"]],
    }
    return projected


def semantic_intent_product_facts_sha256(ir: Mapping[str, Any]) -> str:
    """Hash the exact canonical product-fact projection of one semantic graph."""

    return hashlib.sha256(_json_bytes(semantic_intent_product_facts(ir))).hexdigest()


def semantic_intent_fact_ids(ir: Mapping[str, Any]) -> set[str]:
    """Return every typed fact id carried by an IR."""

    return {
        _text(row.get("fact_id"), 100)
        for row in ir.get("facts", ())
        if isinstance(row, Mapping) and _text(row.get("fact_id"), 100)
    }


def semantic_intent_sha256(ir: Mapping[str, Any]) -> str:
    """Return the digest of the complete verified graph and citations."""

    return hashlib.sha256(_json_bytes(ir)).hexdigest()


def semantic_evidence_sha256(evidence_sources: Mapping[str, str]) -> str:
    """Bind Semantic Intent to the exact prompt and EDIT evidence bytes."""

    payload = {
        key: str(evidence_sources.get(key) or "")
        for key in ("operator_prompt", "operator_edit")
    }
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def semantic_intent_meaning_sha256(ir: Mapping[str, Any]) -> str:
    """Return an ID-, list-order-, and citation-independent meaning digest."""

    return hashlib.sha256(_json_bytes(semantic_intent_meaning_projection(ir))).hexdigest()


def semantic_intent_meaning_projection(ir: Mapping[str, Any]) -> dict[str, Any]:
    """Canonicalize source truth without presentation or implementation topology."""

    facts = sorted(
        (
            row
            for row in ir.get("facts", ())
            if isinstance(row, Mapping) and row.get("custody") == "source_fact"
        ),
        key=lambda row: (str(row.get("kind") or ""), int(row.get("order") or 0)),
    )
    canonical_ids = {
        str(row.get("fact_id") or ""): f"{row.get('kind')}.{index}"
        for index, row in enumerate(facts)
    }
    canonical_facts = [
        {
            key: _without_source_refs(value)
            for key, value in row.items()
            if key not in {"fact_id", "source_refs"}
        }
        for row in facts
    ]
    relations = sorted(
        (
            row
            for row in ir.get("relations", ())
            if isinstance(row, Mapping)
            and row.get("custody") == "source_fact"
            and str(row.get("subject_id") or "") in canonical_ids
            and str(row.get("object_id") or "") in canonical_ids
        ),
        key=lambda row: (str(row.get("kind") or ""), int(row.get("order") or 0)),
    )
    canonical_relations = [
        {
            "kind": row.get("kind"),
            "subject_id": canonical_ids.get(str(row.get("subject_id") or ""), ""),
            "object_id": canonical_ids.get(str(row.get("object_id") or ""), ""),
            "order": row.get("order"),
            "custody": row.get("custody"),
        }
        for row in relations
    ]
    return {
        "version": ir.get("version"),
        "status": ir.get("status"),
        "clarification": _without_source_refs(ir.get("clarification", {})),
        "facts": canonical_facts,
        "relations": canonical_relations,
    }


def _validate_clarification(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    required: bool,
    allow_empty_source_refs: bool,
) -> dict[str, Any]:
    row = _mapping(value, "clarification")
    _exact_keys(row, {"question", "source_refs"}, "clarification")
    question = _text(row.get("question"), 600)
    require_semantic_source_refs(
        row.get("source_refs"),
        evidence_sources=evidence_sources,
        allow_empty=not required or allow_empty_source_refs,
    )
    if required and not question:
        raise ValueError("Semantic Intent clarification lacks one focused material question")
    return {"question": question}


def _validate_presentation(
    value: Any, *, evidence_sources: Mapping[str, str]
) -> dict[str, Any]:
    row = _mapping(value, "presentation")
    _exact_keys(row, {"title", "status", "source_refs"}, "presentation")
    title = _text(row.get("title"), 200)
    if not title:
        raise ValueError("Semantic Intent presentation lacks a title")
    status = _enum(
        row.get("status"), {"source_declared", "working_assumption"}, "presentation status"
    )
    refs = require_semantic_source_refs(
        row.get("source_refs"),
        evidence_sources=evidence_sources,
        allow_empty=True,
    )
    if status == "source_declared" and not refs:
        raise ValueError("Source-declared Semantic Intent presentation lacks custody")
    if status == "working_assumption" and refs:
        raise ValueError("Working Semantic Intent presentation carries source custody")
    return {"title": title, "status": status, "source_refs": refs}


def _validate_facts(value: Any, *, evidence_sources: Mapping[str, str]) -> list[dict[str, Any]]:
    rows = _sequence(value, 128, "facts")
    keys = {
        "fact_id", "kind", "label", "statement", "order", "owner_kind",
        "custody", "attributes", "source_refs",
    }
    result: list[dict[str, Any]] = []
    for raw in rows:
        row = _mapping(raw, "fact")
        _fact_id(row.get("fact_id"), "fact")
        kind = _enum(row.get("kind"), set(SEMANTIC_FACT_KINDS), "fact kind")
        expected_keys = keys | ({"transition"} if kind == "state_object" else set())
        _exact_keys(row, expected_keys, "fact")
        if not _text(row.get("label"), 300) or not _text(row.get("statement"), 1600):
            raise ValueError("Semantic Intent fact is incomplete")
        if not isinstance(row.get("order"), int) or isinstance(row.get("order"), bool) or row["order"] < 0:
            raise ValueError("Semantic Intent fact order is invalid")
        owner_kind = _enum(row.get("owner_kind"), _OWNER_KINDS, "owner kind")
        custody = _enum(row.get("custody"), _CUSTODY_STATES, "custody")
        if custody == "visible_assumption" and kind != "assumption":
            raise ValueError(
                "Semantic Intent visible assumptions are limited to declared gaps"
            )
        attributes = _validate_attributes(row.get("attributes"), kind=kind)
        if kind == "state_object":
            semantic_state_transition(row)
        require_semantic_source_refs(row.get("source_refs"), evidence_sources=evidence_sources)
        _require_kind_contract(kind=kind, owner_kind=owner_kind, attributes=attributes)
        result.append(dict(row))
    _require_contiguous_order(result, key="kind", label="fact")
    return result


def _validate_attributes(value: Any, *, kind: str) -> dict[str, str]:
    rows = _sequence(value, 12, "fact attributes")
    attributes: dict[str, str] = {}
    for raw in rows:
        row = _mapping(raw, "fact attribute")
        _exact_keys(row, {"name", "value"}, "fact attribute")
        name = _enum(row.get("name"), _ATTRIBUTE_NAMES, "attribute name")
        if name in attributes:
            raise ValueError("Semantic Intent fact repeats an attribute")
        attributes[name] = _text(row.get("value"), 800)
    return attributes


def _require_kind_contract(*, kind: str, owner_kind: str, attributes: Mapping[str, str]) -> None:
    required_attributes = set(_FACT_REQUIRED_ATTRIBUTES.get(kind, ()))
    if not required_attributes <= set(attributes):
        raise ValueError(f"Semantic Intent {kind} lacks required typed attributes")
    if kind == "workflow_step" and owner_kind == "none":
        raise ValueError("Semantic Intent workflow step lacks an owner kind")
    if kind != "workflow_step" and owner_kind != "none":
        raise ValueError("non-workflow Semantic Intent fact carries an owner kind")
    if kind == "internal_system":
        if attributes["component_kind"] not in INTERNAL_SYSTEM_COMPONENT_KINDS:
            raise ValueError("Semantic Intent internal system has an invalid component kind")
        if attributes["release_scope"] not in INTERNAL_SYSTEM_RELEASE_SCOPES:
            raise ValueError("Semantic Intent internal system has an invalid release scope")


def semantic_state_transition(
    value: Mapping[str, Any],
) -> dict[str, str | None] | None:
    """Return one atomic state transition or no transition."""

    transition = value.get("transition")
    if transition is None:
        return None
    row = _mapping(transition, "state transition")
    _exact_keys(row, {"from_state", "to_state"}, "state transition")
    before = (
        None if row.get("from_state") is None else _text(row.get("from_state"), 800)
    )
    after = None if row.get("to_state") is None else _text(row.get("to_state"), 800)
    if before is None and after is None:
        raise ValueError("Semantic Intent state transition lacks a declared state")
    if before is not None and before == after:
        raise ValueError("Semantic Intent state transition does not change state")
    return {"from_state": before, "to_state": after}


def semantic_state_transition_phrase(value: Mapping[str, Any]) -> str:
    """Render only the transition endpoints actually declared by source truth."""

    transition = semantic_state_transition(value)
    if transition is None:
        return ""
    before = transition["from_state"]
    after = transition["to_state"]
    if before is None:
        return f"to {after}"
    if after is None:
        return f"from {before}"
    return f"from {before} to {after}"


def _validate_relations(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    fact_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = _sequence(value, 256, "relations")
    keys = {
        "relation_id",
        "kind",
        "subject_id",
        "object_id",
        "order",
        "custody",
        "source_refs",
    }
    result: list[dict[str, Any]] = []
    relation_ids: set[str] = set()
    for raw in rows:
        row = _mapping(raw, "relation")
        _exact_keys(row, keys, "relation")
        relation_id = _fact_id(row.get("relation_id"), "relation")
        if relation_id in relation_ids:
            raise ValueError("Semantic Intent relation ids are not unique")
        relation_ids.add(relation_id)
        kind = _enum(row.get("kind"), set(SEMANTIC_RELATION_KINDS), "relation kind")
        subject_id = row.get("subject_id")
        object_id = row.get("object_id")
        if subject_id not in fact_index or object_id not in fact_index:
            raise ValueError("Semantic Intent relation references an unknown fact")
        contract = _RELATION_ENDPOINT_KINDS[kind]
        if (
            fact_index[str(subject_id)]["kind"] not in contract["subject"]
            or fact_index[str(object_id)]["kind"] not in contract["object"]
        ):
            raise ValueError("Semantic Intent relation has invalid typed endpoints")
        if not isinstance(row.get("order"), int) or isinstance(row.get("order"), bool) or row["order"] < 0:
            raise ValueError("Semantic Intent relation order is invalid")
        _enum(row.get("custody"), _RELATION_CUSTODY_STATES, "relation custody")
        require_semantic_source_refs(row.get("source_refs"), evidence_sources=evidence_sources)
        result.append(dict(row))
    _require_contiguous_order(result, key="kind", label="relation")
    return result


def _validate_narratives(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    fact_ids: set[str],
) -> list[dict[str, Any]]:
    rows = _sequence(value, 64, "narratives")
    keys = {"field", "order", "text", "fact_ids", "source_refs"}
    result: list[dict[str, Any]] = []
    for raw in rows:
        row = _mapping(raw, "narrative")
        _exact_keys(row, keys, "narrative")
        _enum(row.get("field"), set(SEMANTIC_NARRATIVE_FIELDS), "narrative field")
        if not isinstance(row.get("order"), int) or isinstance(row.get("order"), bool) or row["order"] < 0:
            raise ValueError("Semantic Intent narrative order is invalid")
        if not _text(row.get("text"), 1600):
            raise ValueError("Semantic Intent narrative is empty")
        referenced = set(_text_rows(row.get("fact_ids"), 32, "narrative fact ids"))
        if not referenced or not referenced <= fact_ids:
            raise ValueError("Semantic Intent narrative references an unknown fact")
        require_semantic_source_refs(row.get("source_refs"), evidence_sources=evidence_sources)
        result.append(dict(row))
    _require_contiguous_order(result, key="field", label="narrative")
    return result


def _require_complete_material_graph(
    *,
    facts: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    narratives: Sequence[Mapping[str, Any]],
) -> None:
    by_kind = _facts_by_kind(facts)
    for kind, contract in _COMPLETE_FACT_COUNTS.items():
        if len(by_kind[kind]) < contract["minimum"]:
            raise ValueError(f"complete Semantic Intent IR lacks {kind}")
        maximum = contract.get("maximum")
        if maximum is not None and len(by_kind[kind]) > maximum:
            raise ValueError(
                f"complete Semantic Intent IR exceeds {kind} cardinality"
            )
    narrative_counts = Counter(row["field"] for row in narratives)
    if any(narrative_counts[field] != 1 for field in _SINGULAR_NARRATIVE_FIELDS):
        raise ValueError("complete Semantic Intent IR lacks a singular narrative field")
    if any(narrative_counts[field] < 1 for field in _LIST_NARRATIVE_FIELDS):
        raise ValueError("complete Semantic Intent IR lacks proof metrics")
    if narrative_counts["success_metric"] < 2:
        raise ValueError("complete Semantic Intent IR needs at least two product success metrics")
    owned_by = [row for row in relations if row["kind"] == "owned_by"]
    entity_relations = [
        row
        for row in relations
        if row["kind"] in {"input_entity", "target_entity"}
    ]
    creates = [row for row in relations if row["kind"] == "creates"]
    produces = [row for row in relations if row["kind"] == "produces"]
    output_of = [row for row in relations if row["kind"] == "output_of"]
    changes = [row for row in relations if row["kind"] == "changes"]
    maintains = [row for row in relations if row["kind"] == "maintains"]
    state_of = [row for row in relations if row["kind"] == "state_of"]
    actor_ids = {row["fact_id"] for row in by_kind["actor"]}
    entity_ids = {row["fact_id"] for row in by_kind["entity"]}
    entity_by_id = {str(row["fact_id"]): row for row in by_kind["entity"]}
    output_ids = {row["fact_id"] for row in by_kind["visible_output"]}
    state_ids = {row["fact_id"] for row in by_kind["state_object"]}
    transitioned_state_ids = {
        row["fact_id"]
        for row in by_kind["state_object"]
        if semantic_state_transition(row) is not None
    }
    stable_state_ids = state_ids - transitioned_state_ids
    for step in by_kind["workflow_step"]:
        owners = [row for row in owned_by if row["subject_id"] == step["fact_id"]]
        if step["owner_kind"] == "actor":
            if len(owners) != 1 or owners[0]["object_id"] not in actor_ids:
                raise ValueError("actor-owned Semantic Intent workflow lacks one typed owner relation")
        elif owners:
            raise ValueError("product/system Semantic Intent workflow carries a human owner relation")
        bound_entity_roles = [
            (row["kind"], row["object_id"])
            for row in entity_relations
            if row["subject_id"] == step["fact_id"]
        ]
        if len(bound_entity_roles) != len(set(bound_entity_roles)):
            raise ValueError("Semantic Intent workflow repeats one typed entity relation")
    if any(row["object_id"] not in entity_ids for row in entity_relations):
        raise ValueError("Semantic Intent workflow binding targets a non-entity fact")
    referenced_entity_ids = {
        row["object_id"]
        for row in (*entity_relations, *creates, *state_of, *output_of)
    }
    if referenced_entity_ids != entity_ids:
        raise ValueError("Semantic Intent carries an unbound canonical entity")
    if any(row["object_id"] not in output_ids for row in produces):
        raise ValueError("Semantic Intent produces relation targets a non-output fact")
    if any(row["object_id"] not in transitioned_state_ids for row in changes):
        raise ValueError("Semantic Intent changes relation targets an undeclared transition")
    if any(row["object_id"] not in stable_state_ids for row in maintains):
        raise ValueError("Semantic Intent maintains relation targets a transition")
    state_effect_ids = [row["object_id"] for row in (*changes, *maintains)]
    if set(state_effect_ids) != state_ids or len(state_effect_ids) != len(state_ids):
        raise ValueError("Semantic Intent state lacks one node-owned workflow effect")
    _require_entity_identity_edges(
        facts=by_kind["state_object"],
        relations=state_of,
        entities=entity_by_id,
        label="state",
    )
    _require_entity_identity_edges(
        facts=by_kind["visible_output"],
        relations=output_of,
        entities=entity_by_id,
        label="output",
    )


def _facts_by_kind(facts: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    result = {kind: [] for kind in SEMANTIC_FACT_KINDS}
    for row in facts:
        result[row["kind"]].append(row)
    for rows in result.values():
        rows.sort(key=lambda row: row["order"])
    return result


def _require_entity_identity_edges(
    *,
    facts: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    entities: Mapping[str, Mapping[str, Any]],
    label: str,
) -> None:
    """Require state and output identity to follow one typed entity edge."""

    for fact in facts:
        fact_id = str(fact["fact_id"])
        targets = [
            str(row["object_id"])
            for row in relations
            if row["subject_id"] == fact_id
        ]
        if len(targets) != 1 or targets[0] not in entities:
            raise ValueError(
                f"Semantic Intent {label} lacks one canonical entity identity"
            )
        if _attribute(fact, "entity_id") != targets[0]:
            raise ValueError(
                f"Semantic Intent {label} entity attribute disagrees with its typed edge"
            )
        entity = entities[targets[0]]
        if _attribute(fact, "object") and _attribute(fact, "object") != entity["label"]:
            raise ValueError(
                f"Semantic Intent {label} display identity disagrees with its entity"
            )
        if label == "output" and fact["label"] != entity["label"]:
            raise ValueError(
                "Semantic Intent output label disagrees with its entity"
            )


def _require_unique_state_transitions(facts: Sequence[Mapping[str, Any]]) -> None:
    signatures: set[tuple[str, str | None, str | None]] = set()
    for fact in facts:
        transition = (
            semantic_state_transition(fact)
            if fact["kind"] == "state_object"
            else None
        )
        if transition is None:
            continue
        signature = (
            _attribute(fact, "entity_id"),
            transition["from_state"],
            transition["to_state"],
        )
        if signature in signatures:
            raise ValueError("Semantic Intent repeats one typed state transition")
        signatures.add(signature)


def _narratives_by_field(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    result = {field: [] for field in SEMANTIC_NARRATIVE_FIELDS}
    for row in rows:
        result[row["field"]].append(row)
    for values in result.values():
        values.sort(key=lambda row: row["order"])
    return result


def _attribute(fact: Mapping[str, Any], name: str) -> str:
    return next(
        (str(row["value"]).strip() for row in fact.get("attributes", ()) if row.get("name") == name),
        "",
    )


def _policy_boundary_view(
    fact: Mapping[str, Any],
    *,
    relations: Sequence[Mapping[str, Any]],
    fact_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Project one neutral boundary and its exact typed scope."""

    modalities = tuple(
        value for value in _attribute(fact, "modalities").split(",") if value
    )
    targets = []
    for relation in relations:
        if relation.get("kind") != "applies_to" or relation.get("subject_id") != fact["fact_id"]:
            continue
        target = fact_index[str(relation["object_id"])]
        targets.append(
            {
                "fact_id": str(target["fact_id"]),
                "kind": str(target["kind"]),
                "label": str(target["label"]),
            }
        )
    return {
        "label": str(fact["label"]),
        "modalities": list(modalities),
        "statement": _attribute(fact, "statement"),
        "applies_to": targets,
    }


def _require_contiguous_order(rows: Sequence[Mapping[str, Any]], *, key: str, label: str) -> None:
    groups: dict[str, list[int]] = {}
    for row in rows:
        groups.setdefault(str(row[key]), []).append(int(row["order"]))
    if any(sorted(values) != list(range(len(values))) for values in groups.values()):
        raise ValueError(f"Semantic Intent {label} order is not contiguous")


def _without_source_refs(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _without_source_refs(nested) for key, nested in value.items() if key != "source_refs"}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_without_source_refs(nested) for nested in value]
    return value


def _fact_id(value: Any, label: str) -> str:
    token = _text(value, 100)
    if not token or any(character.isspace() for character in token):
        raise ValueError(f"Semantic Intent {label} has an invalid id")
    return token


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return value


def _sequence(value: Any, maximum: int, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{label} is malformed")
    rows = list(value)
    if len(rows) > maximum:
        raise ValueError(f"{label} exceeds its operating limit")
    return rows


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} has an invalid structure")


def _text(value: Any, maximum: int = 1600) -> str:
    if not isinstance(value, str):
        raise ValueError("Semantic Intent text value is malformed")
    token = value.strip()
    if len(token) > maximum:
        raise ValueError("Semantic Intent text value exceeds its operating limit")
    return token


def _text_rows(value: Any, maximum: int, label: str) -> list[str]:
    result: list[str] = []
    for row in _sequence(value, maximum, label):
        text = _text(row)
        if text:
            result.append(text)
    return result


def _enum(value: Any, allowed: set[str] | frozenset[str], label: str) -> str:
    token = _text(value, 100)
    if token not in allowed:
        raise ValueError(f"Semantic Intent {label} is invalid")
    return token


def _sentence(value: Any) -> str:
    text = _text(value, 1600).rstrip()
    sentence = f"{text[:1].upper()}{text[1:]}"
    return sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."


def _actor_views(
    actors: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project actor capability from typed ownership, never prejoined prose."""

    steps_by_id = {str(row["fact_id"]): row for row in steps}
    owned_step_ids: dict[str, list[str]] = {
        str(row["fact_id"]): [] for row in actors
    }
    for relation in relations:
        if relation.get("kind") != "owned_by":
            continue
        actor_id = str(relation["object_id"])
        step_id = str(relation["subject_id"])
        if actor_id in owned_step_ids and step_id in steps_by_id:
            owned_step_ids[actor_id].append(step_id)
    return [
        {
            "actor_fact_id": str(actor["fact_id"]),
            "label": str(actor["label"]),
            "owned_step_fact_ids": list(owned_step_ids[str(actor["fact_id"])]),
            "owned_actions": [
                str(steps_by_id[step_id]["label"])
                for step_id in owned_step_ids[str(actor["fact_id"])]
            ],
        }
        for actor in actors
    ]


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


__all__ = [
    "SEMANTIC_FACT_KINDS",
    "SEMANTIC_INTENT_IR_VERSION",
    "SEMANTIC_INTENT_PACKET_VERSION",
    "SEMANTIC_NARRATIVE_FIELDS",
    "SEMANTIC_RELATION_KINDS",
    "require_semantic_intent_ir",
    "semantic_evidence_sha256",
    "semantic_intent_authoring_contract",
    "semantic_intent_fact_ids",
    "semantic_intent_meaning_sha256",
    "semantic_intent_meaning_projection",
    "semantic_intent_product_facts",
    "semantic_intent_product_facts_sha256",
    "semantic_intent_sha256",
    "semantic_state_transition",
    "semantic_state_transition_phrase",
]
