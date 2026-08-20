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
    SEMANTIC_CLARIFICATION_FIELDS,
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
from odylith.runtime.domain_intelligence.greenfield_semantic_source_claims import (
    require_source_claim_projection,
)


SEMANTIC_INTENT_IR_VERSION = "odylith.greenfield.semantic-intent-ir.v5"
SEMANTIC_INTENT_PACKET_VERSION = "odylith.greenfield.semantic-intent-packet.v13"

_CUSTODY_STATES = frozenset(
    {"source_fact", "bounded_interpretation", "visible_assumption"}
)
_OWNER_KINDS = frozenset({"none", "actor", "product", "system"})
_RELATION_CUSTODY_STATES = frozenset({"source_fact", "bounded_interpretation"})
_ATTRIBUTE_NAMES = frozenset(SEMANTIC_ATTRIBUTE_NAMES)


def require_semantic_intent_ir(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    source_claims: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate graph structure and citations without interpreting prose."""

    ir = _mapping(value, "Semantic Intent IR")
    _exact_keys(ir, {"version", "status", "clarification", "facts", "relations", "narratives"}, "Semantic Intent IR")
    if ir.get("version") != SEMANTIC_INTENT_IR_VERSION:
        raise ValueError("Semantic Intent IR uses an unsupported version")
    status = _enum(ir.get("status"), {"complete", "clarification_required"}, "status")
    clarification = _validate_clarification(
        ir.get("clarification"),
        evidence_sources=evidence_sources,
        required=status == "clarification_required",
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
    require_source_claim_projection(
        source_claims,
        facts=facts,
        relations=relations,
    )
    if status == "clarification_required":
        return dict(ir)
    if clarification["question"] or clarification["fields"]:
        raise ValueError("complete Semantic Intent IR carries a clarification request")
    _require_complete_material_graph(facts=facts, relations=relations, narratives=narratives)
    return dict(ir)


def semantic_intent_product_facts(ir: Mapping[str, Any]) -> dict[str, Any]:
    """Project canonical product facts from verified graph nodes."""

    if ir.get("status") != "complete":
        raise ValueError("clarification-bound Semantic Intent IR has no product-fact projection")
    facts = list(ir["facts"])
    by_kind = _facts_by_kind(facts)
    identity = by_kind["identity"][0]
    narratives = _narratives_by_field(ir["narratives"])
    projected: dict[str, Any] = {
        "title": identity["label"],
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
        "human_actors": [_actor_view(row) for row in by_kind["actor"]],
        "external_systems": [row["label"] for row in by_kind["external_system"]],
        "internal_systems": [row["statement"] for row in by_kind["internal_system"]],
        "component_responsibilities": [row["statement"] for row in by_kind["component_responsibility"]],
        "operational_constraints": [row["label"] for row in by_kind["operational_constraint"]],
        "non_goals": [row["label"] for row in by_kind["non_goal"]],
        "assumptions": [row["label"] for row in by_kind["assumption"]],
        "ambiguities": [row["label"] for row in by_kind["ambiguity"]],
    }
    source_title = _attribute(identity, "source_title")
    if source_title:
        projected["source_title"] = source_title
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
    """Canonicalize graph meaning without source coordinates or local IDs."""

    facts = sorted(
        (row for row in ir.get("facts", ()) if isinstance(row, Mapping)),
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
        (row for row in ir.get("relations", ()) if isinstance(row, Mapping)),
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
    narratives = sorted(
        (row for row in ir.get("narratives", ()) if isinstance(row, Mapping)),
        key=lambda row: (str(row.get("field") or ""), int(row.get("order") or 0)),
    )
    canonical_narratives = [
        {
            "field": row.get("field"),
            "order": row.get("order"),
            "text": row.get("text"),
            "fact_ids": sorted(
                canonical_ids.get(str(fact_id or ""), "")
                for fact_id in row.get("fact_ids", ())
            ),
        }
        for row in narratives
    ]
    return {
        "version": ir.get("version"),
        "status": ir.get("status"),
        "clarification": _without_source_refs(ir.get("clarification", {})),
        "facts": canonical_facts,
        "relations": canonical_relations,
        "narratives": canonical_narratives,
    }


def _validate_clarification(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    required: bool,
) -> dict[str, Any]:
    row = _mapping(value, "clarification")
    _exact_keys(row, {"question", "fields", "source_refs"}, "clarification")
    question = _text(row.get("question"), 600)
    fields = _text_rows(row.get("fields"), 3, "clarification fields")
    if any(field not in SEMANTIC_CLARIFICATION_FIELDS for field in fields):
        raise ValueError("Semantic Intent clarification names a non-canonical field")
    require_semantic_source_refs(
        row.get("source_refs"), evidence_sources=evidence_sources, allow_empty=not required
    )
    if required and (not question or not fields):
        raise ValueError("Semantic Intent clarification lacks one focused material question")
    return {"question": question, "fields": fields}


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
        _enum(row.get("custody"), _CUSTODY_STATES, "custody")
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


def semantic_state_transition(value: Mapping[str, Any]) -> dict[str, str] | None:
    """Return one atomic state transition or no transition."""

    transition = value.get("transition")
    if transition is None:
        return None
    row = _mapping(transition, "state transition")
    _exact_keys(row, {"from_state", "to_state"}, "state transition")
    before = _text(row.get("from_state"), 800)
    after = _text(row.get("to_state"), 800)
    if not before or not after:
        raise ValueError("Semantic Intent state transition is incomplete")
    if before == after:
        raise ValueError("Semantic Intent state transition does not change state")
    return {"from_state": before, "to_state": after}


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
    if by_kind["ambiguity"]:
        raise ValueError(
            "complete Semantic Intent IR carries unresolved material ambiguity"
        )
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
    fact_index = {row["fact_id"]: row for row in facts}
    owned_by = [row for row in relations if row["kind"] == "owned_by"]
    produces = [row for row in relations if row["kind"] == "produces"]
    changes = [row for row in relations if row["kind"] == "changes"]
    implements = [row for row in relations if row["kind"] == "implements"]
    actor_ids = {row["fact_id"] for row in by_kind["actor"]}
    output_ids = {row["fact_id"] for row in by_kind["visible_output"]}
    state_ids = {row["fact_id"] for row in by_kind["state_object"]}
    external_system_ids = {
        row["fact_id"] for row in by_kind["external_system"]
    }
    transitioned_state_ids = {
        row["fact_id"]
        for row in by_kind["state_object"]
        if semantic_state_transition(row) is not None
    }
    implementation_target_ids = {
        row["fact_id"]
        for kind in ("workflow_step", "state_object", "visible_output")
        for row in by_kind[kind]
    }
    first_path_system_ids = {
        row["fact_id"]
        for row in by_kind["internal_system"]
        if _attribute(row, "release_scope") == "first_path_required"
    }
    active_system_ids = {
        row["fact_id"]
        for row in by_kind["internal_system"]
        if _attribute(row, "release_scope") == "first_path_required"
    }
    for step in by_kind["workflow_step"]:
        owners = [row for row in owned_by if row["subject_id"] == step["fact_id"]]
        if step["owner_kind"] == "actor":
            if len(owners) != 1 or owners[0]["object_id"] not in actor_ids:
                raise ValueError("actor-owned Semantic Intent workflow lacks one typed owner relation")
        elif owners:
            raise ValueError("product/system Semantic Intent workflow carries a human owner relation")
    produced_output_ids = {
        row["object_id"]
        for row in produces
        if row["subject_id"] in fact_index and row["object_id"] in output_ids
    }
    if produced_output_ids != output_ids:
        raise ValueError(
            "complete Semantic Intent IR lacks typed producing coverage for every visible output"
        )
    changed_state_ids = {
        row["object_id"]
        for row in changes
        if row["subject_id"] in fact_index and row["object_id"] in state_ids
    }
    if changed_state_ids != transitioned_state_ids:
        raise ValueError(
            "complete Semantic Intent IR has invalid typed change coverage for state transitions"
        )
    if not first_path_system_ids:
        raise ValueError(
            "complete Semantic Intent IR lacks a first_path_required internal system"
        )
    implemented_targets = {
        row["object_id"]
        for row in implements
        if row["subject_id"] in active_system_ids
        and row["object_id"] in implementation_target_ids
    }
    if implemented_targets != implementation_target_ids:
        raise ValueError(
            "complete Semantic Intent IR lacks active typed implementation coverage"
        )
    result_system_ids = {
        row["subject_id"]
        for row in implements
        if row["subject_id"] in active_system_ids
        and row["object_id"] in implementation_target_ids
    }
    depends_on = [row for row in relations if row["kind"] == "depends_on"]
    assigned_external_system_ids = {
        row["object_id"]
        for row in depends_on
        if row["object_id"] in external_system_ids
    }
    if assigned_external_system_ids != external_system_ids:
        raise ValueError(
            "complete Semantic Intent IR leaves an external dependency unassigned"
        )
    boundary_relations = [
        row
        for row in relations
        if row["kind"] in {"depends_on", "constrained_by", "excludes"}
    ]
    for system_id in active_system_ids - result_system_ids:
        consumed = any(
            row["object_id"] == system_id
            and (
                row["subject_id"] in active_system_ids
                or fact_index[row["subject_id"]]["kind"] in {"identity", "workflow_step"}
            )
            for row in depends_on
        )
        owns_boundary = any(
            row["subject_id"] == system_id and row["object_id"] != system_id
            for row in boundary_relations
        )
        if not consumed or not owns_boundary:
            raise ValueError(
                "resultless first-path Semantic Intent system lacks typed supporting topology"
            )


def _facts_by_kind(facts: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    result = {kind: [] for kind in SEMANTIC_FACT_KINDS}
    for row in facts:
        result[row["kind"]].append(row)
    for rows in result.values():
        rows.sort(key=lambda row: row["order"])
    return result


def _require_unique_state_transitions(facts: Sequence[Mapping[str, Any]]) -> None:
    signatures: set[tuple[str, str, str]] = set()
    for fact in facts:
        transition = (
            semantic_state_transition(fact)
            if fact["kind"] == "state_object"
            else None
        )
        if transition is None:
            continue
        signature = (
            _attribute(fact, "object"),
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


def _actor_view(row: Mapping[str, Any]) -> str:
    label = str(row["label"])
    responsibility = _attribute(row, "responsibility")
    return f"{label}: {responsibility}" if responsibility else label


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
]
