"""Typed custody envelope for confirmed greenfield product intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import assumption_rows

from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    ATOMIC_FACT_LEDGER_VERSION,
    append_atomic_source_spans,
    atomic_fact_ledger_hash,
    build_atomic_fact_ledger,
    require_atomic_fact_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_SET_SHA256_KEY,
    AUTHORED_SEMANTICS_KEY,
    authored_relation_set_sha256,
    component_responsibility_relations_from_intent,
    first_path_context_relations_from_intent,
    first_path_relations_from_intent,
    require_authored_relation_source_custody,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    MATERIAL_FACT_KEYS,
    PRODUCT_INTENT_AUTHORITY_KEY,
    PRODUCT_INTENT_AUTHORITY_VERSION,
    PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
    PRODUCT_INTENT_LEDGER_VERSION,
    product_intent_authority_snapshot_hash as _sealed_product_intent_authority_snapshot_hash,
    product_intent_material_custody_hash,
    require_product_intent_authority_structure,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import greenfield_operating_envelope_receipt


PRODUCT_FACTS_HASH_KEY = "product_facts_sha256"

PRODUCT_FACT_KEYS = (
    "title",
    "source_title",
    "product_story",
    "state_object",
    "first_path",
    "proof_boundary",
    "problem",
    "customer",
    "opportunity",
    "product_view",
    "success_metrics",
    "component_responsibilities",
    "human_actors",
    "external_systems",
    "internal_systems",
    "assumptions",
    "ambiguities",
    "non_goals",
    "evidence_requirements",
    "operational_constraints",
)

LIST_FACT_KEYS = frozenset(
    {
        "success_metrics",
        "component_responsibilities",
        "human_actors",
        "external_systems",
        "internal_systems",
        "assumptions",
        "ambiguities",
        "non_goals",
        "evidence_requirements",
        "operational_constraints",
    }
)


def is_product_intent_envelope(value: object) -> bool:
    """Return true only for the current authored-custody envelope shape."""

    if not isinstance(value, Mapping):
        return False
    if value.get("schema_version") != PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION:
        return False
    ledger = value.get("custody_ledger")
    return bool(isinstance(ledger, Mapping) and _is_sha256(ledger.get(AUTHORED_RELATION_SET_SHA256_KEY)))


def product_facts_from_envelope(value: object, *, source_text: str = "") -> dict[str, Any] | None:
    """Extract canonical product facts from a source-verified envelope."""

    if not is_product_intent_envelope(value):
        return None
    if not source_text:
        return None
    expected_source_hash = _envelope_source_hash(value)
    if not expected_source_hash:
        return None
    actual_source_hash = hashlib.sha256(str(source_text or "").encode("utf-8")).hexdigest()
    if actual_source_hash != expected_source_hash:
        return None
    facts = value.get("product_facts")
    if isinstance(facts, Mapping):
        try:
            payload = product_facts_payload(facts)
        except ValueError:
            return None
        if set(facts) != set(payload):
            return None
        expected_hash = _envelope_product_facts_hash(value)
        if not expected_hash or expected_hash != product_facts_hash(payload):
            return None
        custody_ledger = value.get("custody_ledger")
        source_evidence = value.get("source_evidence")
        if not isinstance(custody_ledger, Mapping) or not isinstance(source_evidence, Mapping):
            return None
        source_spans = source_evidence.get("spans")
        if not isinstance(source_spans, Sequence) or isinstance(source_spans, (str, bytes, bytearray)):
            return None
        try:
            require_atomic_fact_ledger(
                custody_ledger.get("atomic_facts"),
                source_spans=source_spans,
                facts=payload,
            )
        except ValueError:
            return None
        return payload
    return None


def product_facts_hash(intent: Mapping[str, Any]) -> str:
    """Return a stable integrity hash for canonical product facts."""

    payload = product_facts_payload(intent)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def product_facts_payload(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical product fact bytes without reinterpreting normalized intent."""

    payload: dict[str, Any] = {}
    for key in PRODUCT_FACT_KEYS:
        if key not in intent:
            continue
        value = intent.get(key)
        if key == "assumptions":
            rows = assumption_rows(value)
            if rows:
                payload[key] = rows
            continue
        if key in LIST_FACT_KEYS:
            rows = _exact_string_rows(value)
            if rows:
                payload[key] = rows
            continue
        if not isinstance(value, str):
            raise ValueError(f"model-authored Product Intent fact {key} must be an exact string")
        text = value
        if text:
            payload[key] = text
    return payload


def _exact_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _exact_string_rows(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("model-authored Product Intent list fact must be an exact string list")
    if any(not isinstance(row, str) or not row for row in value):
        raise ValueError("model-authored Product Intent list fact must be an exact string list")
    return list(value)


def rebind_authoritative_product_facts(
    intent: Mapping[str, Any],
    *,
    authoritative_intent: Mapping[str, Any],
) -> dict[str, Any]:
    """Restore sealed product facts after proposal-only completion adds derived metadata."""

    rebound = copy.deepcopy(dict(intent))
    for key in PRODUCT_FACT_KEYS:
        rebound.pop(key, None)
    if AUTHORED_SEMANTICS_KEY not in authoritative_intent:
        raise ValueError("authoritative Product Intent must retain sealed authored semantics")
    authoritative_facts = product_facts_payload(authoritative_intent)
    rebound.update(copy.deepcopy(authoritative_facts))
    return rebound


def build_product_intent_envelope(
    intent: Mapping[str, Any],
    *,
    source_text: str = "",
    source_path: Path | str | None = None,
    source_format: str = "",
    source_document_count: int = 1,
    source_language: str = "en",
    model_authoring: Mapping[str, Any] | None = None,
    authored_source_spans: Sequence[Mapping[str, Any]] | None = None,
    authored_atomic_claims: Sequence[Mapping[str, Any]] | None = None,
    authored_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Build the typed custody record trusted by pre-confirm compilers."""

    if AUTHORED_SEMANTICS_KEY not in intent:
        raise ValueError(
            "Product Intent envelope construction requires sealed model-authored semantics"
        )
    authored_relations = first_path_relations_from_intent(intent)
    first_path_context_relations = first_path_context_relations_from_intent(intent)
    component_responsibility_relations = component_responsibility_relations_from_intent(
        intent
    )
    if not authored_relations:
        raise ValueError(
            "model-authored Product Intent requires exact relation custody"
        )
    authored_relation_set_sha256_value = authored_relation_set_sha256(
        authored_relations,
        component_responsibility_relations,
        first_path_context_relations=first_path_context_relations,
    )
    facts = product_facts_payload(intent)
    source_bytes = str(source_text or "").encode("utf-8")
    source_sha256 = hashlib.sha256(source_bytes).hexdigest() if source_text else ""
    if authored_source_spans is None or authored_atomic_claims is None:
        raise ValueError("model-authored Product Intent requires exact source spans and atomic claims")
    if not source_bytes or authored_source_sha256 != source_sha256:
        raise ValueError(
            "model-authored Product Intent source custody does not match the exact authoring evidence digest"
        )
    spans, source_span_ids_by_field, product_claim_span_ids_by_field = _authored_source_spans(
        authored_source_spans,
        source_bytes=source_bytes,
        facts=facts,
    )
    _verify_authored_atomic_claim_source(
        authored_atomic_claims,
        source_bytes=source_bytes,
        source_spans=spans,
    )
    require_authored_relation_source_custody(
        authored_relations,
        context_relations=first_path_context_relations,
        source_bytes=source_bytes,
        source_spans=spans,
    )
    append_atomic_source_spans(
        spans,
        authored_atomic_claims=authored_atomic_claims,
    )
    _add_span_digests(spans)
    fields = _field_custody(
        facts,
        source_span_ids_by_field=source_span_ids_by_field,
        product_claim_span_ids_by_field=product_claim_span_ids_by_field,
        spans=spans,
    )
    atomic_facts = build_atomic_fact_ledger(
        facts=facts,
        spans=spans,
        authored_atomic_claims=authored_atomic_claims,
    )
    supporting = [span for span in spans if span.get("classification") == "supporting_evidence"]
    operating_envelope = greenfield_operating_envelope_receipt(
        facts=facts,
        source_format=source_format or "unknown",
        source_size_bytes=len(str(source_text or "").encode("utf-8")),
        source_document_count=source_document_count,
        source_language=source_language,
        model_authoring=model_authoring,
    )
    return {
        "schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "product_facts": facts,
        "custody_ledger": {
            "version": PRODUCT_INTENT_LEDGER_VERSION,
            AUTHORED_RELATION_SET_SHA256_KEY: authored_relation_set_sha256_value,
            "fields": fields,
            "atomic_facts": atomic_facts,
            "ignored_instructions": [],
            "supporting_evidence": supporting,
        },
        "source_evidence": {
            "source_format": source_format or "unknown",
            "source_path": str(source_path or ""),
            "source_sha256": source_sha256,
            "spans": spans,
        },
        "materiality_gate": _materiality_gate(facts, fields=fields),
        "operating_envelope": operating_envelope,
        "decision_record": {
            "decision": "confirmed_intent_accepted",
            "fact_authority": "product_facts",
            "markdown_authority": "ingest_only",
            PRODUCT_FACTS_HASH_KEY: product_facts_hash(facts),
        },
    }


def _authored_source_spans(
    values: Sequence[Mapping[str, Any]],
    *,
    source_bytes: bytes,
    facts: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    """Reverify every authored span against the exact envelope source bytes."""

    spans: list[dict[str, Any]] = []
    source_span_ids_by_field: dict[str, list[str]] = {}
    product_claim_span_ids_by_field: dict[str, list[str]] = {}
    seen_ids: set[str] = set()
    common_fields = {
        "span_id",
        "section_key",
        "row_index",
        "classification",
        "text",
        "source_start_byte",
        "source_end_byte",
        "quote_sha256",
    }
    projection_fields = {
        "projection_path",
        "projection_start_byte",
        "projection_end_byte",
    }
    for raw in values:
        classification = (
            raw.get("classification")
            if isinstance(raw, Mapping) and isinstance(raw.get("classification"), str)
            else ""
        )
        expected_fields = (
            common_fields | projection_fields
            if classification == "product_claim"
            else common_fields
        )
        if not isinstance(raw, Mapping) or set(raw) != expected_fields:
            raise ValueError("model-authored Product Intent source custody is malformed")
        span_id = raw.get("span_id") if isinstance(raw.get("span_id"), str) else ""
        field = raw.get("section_key") if isinstance(raw.get("section_key"), str) else ""
        text = raw.get("text") if isinstance(raw.get("text"), str) else ""
        row_index = raw.get("row_index")
        start = raw.get("source_start_byte")
        end = raw.get("source_end_byte")
        projection_path = raw.get("projection_path")
        projection_start = raw.get("projection_start_byte")
        projection_end = raw.get("projection_end_byte")
        quote_sha256 = raw.get("quote_sha256") if isinstance(raw.get("quote_sha256"), str) else ""
        text_bytes = text.encode("utf-8")
        projection_bytes = _projection_value_bytes(facts, projection_path)
        if (
            not span_id
            or span_id in seen_ids
            or field not in PRODUCT_FACT_KEYS
            or not text
            or classification not in {"product_claim", "supporting_evidence"}
            or not isinstance(row_index, int)
            or isinstance(row_index, bool)
            or row_index < 1
            or not _valid_authored_byte_range(start, end, limit=len(source_bytes))
            or (
                classification == "product_claim"
                and (
                    not isinstance(projection_path, str)
                    or not projection_path
                    or not _valid_authored_byte_range(
                        projection_start,
                        projection_end,
                        limit=len(projection_bytes or b""),
                    )
                    or projection_end - projection_start != len(text_bytes)
                    or projection_bytes is None
                    or projection_bytes[projection_start:projection_end] != text_bytes
                )
            )
            or source_bytes[start:end] != text_bytes
            or quote_sha256 != hashlib.sha256(text_bytes).hexdigest()
        ):
            raise ValueError("model-authored Product Intent source custody is malformed")
        seen_ids.add(span_id)
        span = {
            "span_id": span_id,
            "section_key": field,
            "row_index": row_index,
            "classification": classification,
            "text": text,
            "source_start_byte": start,
            "source_end_byte": end,
            "quote_sha256": quote_sha256,
        }
        if classification == "product_claim":
            span.update(
                {
                    "projection_path": projection_path,
                    "projection_start_byte": projection_start,
                    "projection_end_byte": projection_end,
                }
            )
        spans.append(span)
        source_span_ids_by_field.setdefault(field, []).append(span_id)
        if classification == "product_claim":
            product_claim_span_ids_by_field.setdefault(field, []).append(span_id)
    return spans, source_span_ids_by_field, product_claim_span_ids_by_field


def _projection_value_bytes(facts: Mapping[str, Any], path: Any) -> bytes | None:
    if not isinstance(path, str) or not path.startswith("/"):
        return None
    parts = path.split("/")[1:]
    if len(parts) not in {1, 2} or parts[0] not in PRODUCT_FACT_KEYS:
        return None
    value = facts.get(parts[0])
    if len(parts) == 2:
        if not isinstance(value, list):
            return None
        try:
            index = int(parts[1])
        except ValueError:
            return None
        if str(index) != parts[1] or index < 0 or index >= len(value):
            return None
        value = value[index]
    if not isinstance(value, str):
        return None
    return value.encode("utf-8")


def _verify_authored_atomic_claim_source(
    values: Sequence[Mapping[str, Any]],
    *,
    source_bytes: bytes,
    source_spans: Sequence[Mapping[str, Any]],
) -> None:
    """Reject atomic coordinates that were derived from different evidence bytes."""

    if (
        not isinstance(values, Sequence)
        or isinstance(values, (str, bytes, bytearray))
        or not values
    ):
        raise ValueError("model-authored Product Intent atomic source custody is malformed")
    parent_ranges: dict[str, list[tuple[int, int]]] = {}
    for span in source_spans:
        if span.get("classification") != "product_claim":
            continue
        parent_ranges.setdefault(str(span.get("section_key") or ""), []).append(
            (int(span["source_start_byte"]), int(span["source_end_byte"]))
        )
    expected_fields = {
        "field",
        "category",
        "polarity",
        "source_start_byte",
        "source_end_byte",
        "quote",
        "quote_sha256",
        "projection_path",
        "projection_start_byte",
        "projection_end_byte",
        "projection_value_sha256",
        "relation_order",
        "relation_role",
    }
    for claim in values:
        if not isinstance(claim, Mapping) or set(claim) != expected_fields:
            raise ValueError("model-authored Product Intent atomic source custody is malformed")
        field = claim.get("field") if isinstance(claim.get("field"), str) else ""
        quote = claim.get("quote") if isinstance(claim.get("quote"), str) else ""
        start = claim.get("source_start_byte")
        end = claim.get("source_end_byte")
        quote_bytes = quote.encode("utf-8")
        if (
            not field
            or not quote
            or not _valid_authored_byte_range(start, end, limit=len(source_bytes))
            or source_bytes[start:end] != quote_bytes
            or claim.get("quote_sha256") != hashlib.sha256(quote_bytes).hexdigest()
            or not any(
                parent_start <= start and end <= parent_end
                for parent_start, parent_end in parent_ranges.get(field, ())
            )
        ):
            raise ValueError(
                "model-authored Product Intent atomic source custody does not match the exact envelope source"
            )


def _valid_authored_byte_range(start: Any, end: Any, *, limit: int) -> bool:
    return bool(
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= start < end <= limit
    )


def _authority_string_list(value: Any, *, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(row, str) or not row for row in value):
        raise ValueError(
            f"confirmed Product Intent authority field {field_name} must be an exact string list"
        )
    return list(value)


def product_intent_authority_from_envelope(
    envelope: Mapping[str, Any],
    *,
    structured_intent_path: Path | str | None = None,
    markdown_source_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return the compact transaction-bound authority snapshot for an envelope."""

    if not is_product_intent_envelope(envelope):
        raise ValueError("Product Intent authority requires a current authored-custody envelope")

    source_evidence = envelope.get("source_evidence") if isinstance(envelope.get("source_evidence"), Mapping) else {}
    custody_ledger = envelope.get("custody_ledger") if isinstance(envelope.get("custody_ledger"), Mapping) else {}
    decision_record = envelope.get("decision_record") if isinstance(envelope.get("decision_record"), Mapping) else {}
    materiality_gate = envelope.get("materiality_gate") if isinstance(envelope.get("materiality_gate"), Mapping) else {}
    fields = custody_ledger.get("fields") if isinstance(custody_ledger.get("fields"), Mapping) else {}
    atomic_facts = custody_ledger.get("atomic_facts")
    if not isinstance(atomic_facts, Sequence) or isinstance(atomic_facts, (str, bytes, bytearray)):
        atomic_facts = []
    facts = envelope.get("product_facts") if isinstance(envelope.get("product_facts"), Mapping) else {}
    facts_payload = product_facts_payload(facts)
    if set(facts) != set(facts_payload):
        raise ValueError("confirmed Product Intent product facts are malformed")
    expected_facts_hash = _exact_text(decision_record.get(PRODUCT_FACTS_HASH_KEY))
    if expected_facts_hash != product_facts_hash(facts_payload):
        raise ValueError("confirmed Product Intent product facts hash mismatch")
    source_spans = source_evidence.get("spans")
    if not isinstance(source_spans, Sequence) or isinstance(source_spans, (str, bytes, bytearray)):
        raise ValueError("confirmed Product Intent atomic source custody is malformed")
    require_atomic_fact_ledger(atomic_facts, source_spans=source_spans, facts=facts)
    operating_envelope = (
        envelope.get("operating_envelope") if isinstance(envelope.get("operating_envelope"), Mapping) else {}
    )
    material_fields: dict[str, dict[str, Any]] = {}
    for key in MATERIAL_FACT_KEYS:
        field = fields.get(key) if isinstance(fields.get(key), Mapping) else {}
        material_fields[key] = {
            "custody_state": _exact_text(field.get("custody_state")),
            "derivation": _exact_text(field.get("derivation")),
            "confidence": _exact_text(field.get("confidence")),
            "entailment_relationship": _exact_text(field.get("entailment_relationship")),
            "source_span_ids": _authority_string_list(
                field.get("source_span_ids"),
                field_name=f"{key}.source_span_ids",
            ),
            "product_claim_span_ids": _authority_string_list(
                field.get("product_claim_span_ids"),
                field_name=f"{key}.product_claim_span_ids",
            ),
            "source_span_refs": _authority_span_refs(field.get("source_span_refs")),
        }
    material_custody_sha256 = product_intent_material_custody_hash(material_fields)
    authority = {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "origin": "verified_typed_envelope",
        "structured_intent_path": _path_text(structured_intent_path),
        "markdown_source_path": _path_text(
            markdown_source_path or source_evidence.get("source_path")
        ),
        "envelope_schema_version": _exact_text(envelope.get("schema_version")),
        "ledger_version": _exact_text(custody_ledger.get("version")),
        "decision": _exact_text(decision_record.get("decision")),
        "fact_authority": _exact_text(decision_record.get("fact_authority")),
        "markdown_authority": _exact_text(decision_record.get("markdown_authority")),
        PRODUCT_FACTS_HASH_KEY: _exact_text(decision_record.get(PRODUCT_FACTS_HASH_KEY)),
        "markdown_source_sha256": _exact_text(source_evidence.get("source_sha256")),
        "source_format": _exact_text(source_evidence.get("source_format")) or "unknown",
        "materiality_status": _exact_text(materiality_gate.get("status")),
        "blocked_material_fields": _authority_string_list(
            materiality_gate.get("blocked_fields"),
            field_name="materiality_gate.blocked_fields",
        ),
        "clarification_policy": _exact_text(materiality_gate.get("clarification_policy")),
        "operating_envelope": copy.deepcopy(dict(operating_envelope)),
        "material_fields": material_fields,
        "material_custody_sha256": material_custody_sha256,
        "atomic_ledger_version": ATOMIC_FACT_LEDGER_VERSION,
        "atomic_facts": copy.deepcopy(list(atomic_facts)),
        "atomic_custody_sha256": atomic_fact_ledger_hash(atomic_facts),
        AUTHORED_RELATION_SET_SHA256_KEY: _exact_text(
            custody_ledger.get(AUTHORED_RELATION_SET_SHA256_KEY)
        ),
    }
    authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(authority)
    return authority


def product_intent_authority_from_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return embedded authority from already accepted Product Intent data."""

    embedded = value.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if isinstance(embedded, Mapping):
        return dict(embedded)
    raise ValueError("confirmed Product Intent authority is missing; rebuild from a typed custody envelope")


def product_intent_authority_snapshot_hash(authority: Mapping[str, Any]) -> str:
    """Return the hash over compact authority fields, excluding the hash itself."""

    return _sealed_product_intent_authority_snapshot_hash(authority)


def require_product_intent_authority(authority: Mapping[str, Any]) -> None:
    """Fail closed when a transaction lacks valid product-intent authority."""

    try:
        require_product_intent_authority_structure(authority)
    except ValueError as error:
        raise ValueError(str(error).replace("sealed Product Intent authority", "confirmed Product Intent authority")) from error


def _envelope_product_facts_hash(value: Mapping[str, Any]) -> str:
    decision_record = value.get("decision_record")
    if not isinstance(decision_record, Mapping):
        return ""
    return _exact_text(decision_record.get(PRODUCT_FACTS_HASH_KEY))


def _envelope_source_hash(value: Mapping[str, Any]) -> str:
    evidence = value.get("source_evidence")
    if not isinstance(evidence, Mapping):
        return ""
    return _exact_text(evidence.get("source_sha256"))


def _field_custody(
    facts: Mapping[str, Any],
    *,
    source_span_ids_by_field: Mapping[str, Sequence[str]],
    product_claim_span_ids_by_field: Mapping[str, Sequence[str]],
    spans: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    span_refs = {str(span.get("span_id") or ""): span for span in spans}
    for key in PRODUCT_FACT_KEYS:
        if key not in facts or not _has_fact_value(facts.get(key)):
            continue
        direct_source_span_ids = list(source_span_ids_by_field.get(key, ()))
        product_claim_span_ids = list(product_claim_span_ids_by_field.get(key, ()))
        canonical_claim = bool(product_claim_span_ids)
        state = _custody_state(
            key=key,
            span_ids=product_claim_span_ids,
        )
        source_span_ids = direct_source_span_ids
        fields[key] = {
            "custody_state": state,
            "derivation": (
                "exact_authored_projection"
                if canonical_claim
                else "unresolved_authored_fact"
            ),
            "confidence": _confidence_for(state),
            "entailment_relationship": _entailment_relationship(state, canonical_claim=canonical_claim),
            "source_span_ids": source_span_ids,
            "product_claim_span_ids": product_claim_span_ids,
            "source_span_refs": [
                _span_ref(span_refs[span_id])
                for span_id in source_span_ids
                if span_id in span_refs
            ],
        }
    return fields


def _custody_state(
    *,
    key: str,
    span_ids: Sequence[str],
) -> str:
    if key == "assumptions":
        return "assumption"
    if span_ids:
        return "accepted_fact"
    return "inferred_fact"


def _confidence_for(state: str) -> str:
    if state == "accepted_fact":
        return "high"
    if state == "assumption":
        return "visible"
    if state == "bounded_interpretation":
        return "review_required"
    return "medium"


def _entailment_relationship(state: str, *, canonical_claim: bool) -> str:
    if state == "accepted_fact":
        return "direct_product_claim" if canonical_claim else "normalized_product_claim"
    if state == "bounded_interpretation":
        return "bounded_interpretation_of"
    if state == "assumption":
        return "visible_assumption_from"
    return "unresolved"


def _materiality_gate(
    facts: Mapping[str, Any],
    *,
    fields: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    missing = [key for key in MATERIAL_FACT_KEYS if not _has_fact_value(facts.get(key))]
    unresolved = [
        key
        for key in MATERIAL_FACT_KEYS
        if key not in missing
        and str((fields.get(key) or {}).get("custody_state") or "")
        not in {"accepted_fact", "bounded_interpretation"}
    ]
    blocked = [*missing, *unresolved]
    return {
        "status": "clarification_required" if blocked else "passed",
        "blocked_fields": blocked,
        "clarification_policy": "block_only_material_unknowns",
    }


def _add_span_digests(spans: Sequence[dict[str, Any]]) -> None:
    for span in spans:
        text = _exact_text(span.get("text"))
        span["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()


def _span_ref(span: Mapping[str, Any]) -> dict[str, str]:
    ref = {
        "span_id": _exact_text(span.get("span_id")),
        "classification": _exact_text(span.get("classification")),
        "text_sha256": _exact_text(span.get("text_sha256")),
    }
    if ref["classification"] == "supporting_evidence":
        evidence_text = _exact_text(span.get("evidence_text") or span.get("text"))
        if evidence_text:
            ref["evidence_text"] = evidence_text
    return ref


def _authority_span_refs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [
        _span_ref(row)
        for row in value
        if isinstance(row, Mapping)
    ]


def _has_fact_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(bool(row) for row in value)
    return value is not None


def _path_text(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return _exact_text(value)


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "LIST_FACT_KEYS",
    "PRODUCT_FACT_KEYS",
    "PRODUCT_FACTS_HASH_KEY",
    "PRODUCT_INTENT_AUTHORITY_KEY",
    "PRODUCT_INTENT_AUTHORITY_VERSION",
    "PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION",
    "PRODUCT_INTENT_LEDGER_VERSION",
    "build_product_intent_envelope",
    "is_product_intent_envelope",
    "product_intent_authority_from_envelope",
    "product_intent_authority_from_mapping",
    "product_intent_authority_snapshot_hash",
    "product_facts_from_envelope",
    "product_facts_payload",
    "rebind_authoritative_product_facts",
    "require_product_intent_authority",
]
