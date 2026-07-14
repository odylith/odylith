"""Typed custody envelope for confirmed greenfield product intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_sections,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    is_confirmed_intent_ignored_section,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    is_confirmed_intent_supporting_section,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import (
    is_first_path_meta_control_language,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import (
    is_terminal_first_path_meta_loop_summary,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import (
    split_unpunctuated_first_path_meta_control,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION = "odylith.product-intent-envelope.v2"
PRODUCT_INTENT_LEDGER_VERSION = "odylith.product-intent-custody-ledger.v1"
PRODUCT_INTENT_AUTHORITY_VERSION = "odylith.product-intent-authority.v2"
PRODUCT_INTENT_AUTHORITY_KEY = "product_intent_authority"
PRODUCT_FACTS_HASH_KEY = "product_facts_sha256"

PRODUCT_FACT_KEYS = (
    "title",
    "source_title",
    "prompt",
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
    }
)

MATERIAL_FACT_KEYS = (
    "product_story",
    "state_object",
    "first_path",
    "proof_boundary",
    "human_actors",
)

_STRUCTURED_SOURCE_FORMATS = frozenset(
    {
        "compiled_proposal_intent",
        "in_memory_confirmed_intent",
        "legacy_json",
        "operator_prompt",
        "operator_prompt_with_edit_evidence",
        "typed_envelope_json",
    }
)


def is_product_intent_envelope(value: object) -> bool:
    """Return true when a JSON object carries the v2 product-intent envelope."""

    return isinstance(value, Mapping) and str(value.get("schema_version") or "") == PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION


def product_facts_from_envelope(value: object, *, source_text: str = "") -> dict[str, Any] | None:
    """Extract canonical product facts from a source-verified v2 envelope."""

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
        payload = product_facts_payload(facts)
        expected_hash = _envelope_product_facts_hash(value)
        if expected_hash and expected_hash != product_facts_hash(payload):
            return None
        return payload
    return None


def product_facts_hash(intent: Mapping[str, Any]) -> str:
    """Return a stable integrity hash for canonical product facts."""

    payload = product_facts_payload(intent)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def product_facts_payload(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Return only canonical product fact fields from a normalized intent."""

    payload: dict[str, Any] = {}
    for key in PRODUCT_FACT_KEYS:
        if key not in intent:
            continue
        value = intent.get(key)
        if key in LIST_FACT_KEYS:
            rows = confirmed_text_values(value)
            if rows:
                payload[key] = rows
            continue
        text = clean_markdown_text(value)
        if text:
            payload[key] = text
    return payload


def build_product_intent_envelope(
    intent: Mapping[str, Any],
    *,
    source_text: str = "",
    source_path: Path | str | None = None,
    source_format: str = "",
) -> dict[str, Any]:
    """Build the typed custody record that post-confirm compilers can trust."""

    facts = product_facts_payload(intent)
    sections = confirmed_intent_sections(source_text) if source_text else {}
    spans, source_span_ids_by_field, product_claim_span_ids_by_field = _source_spans(sections)
    _add_source_title_span(
        facts,
        spans=spans,
        source_span_ids_by_field=source_span_ids_by_field,
        product_claim_span_ids_by_field=product_claim_span_ids_by_field,
        source_text=source_text,
    )
    _add_source_story_span(
        facts,
        spans=spans,
        source_span_ids_by_field=source_span_ids_by_field,
        product_claim_span_ids_by_field=product_claim_span_ids_by_field,
        source_text=source_text,
    )
    ignored = [span for span in spans if span.get("classification") == "ignored_instruction"]
    supporting = [span for span in spans if span.get("classification") == "supporting_evidence"]
    source_sha256 = hashlib.sha256(str(source_text or "").encode("utf-8")).hexdigest() if source_text else ""
    return {
        "schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "product_facts": facts,
        "custody_ledger": {
            "version": PRODUCT_INTENT_LEDGER_VERSION,
            "fields": _field_custody(
                facts,
                source_span_ids_by_field=source_span_ids_by_field,
                product_claim_span_ids_by_field=product_claim_span_ids_by_field,
                source_format=source_format,
            ),
            "ignored_instructions": ignored,
            "supporting_evidence": supporting,
        },
        "source_evidence": {
            "source_format": source_format or "unknown",
            "source_path": str(source_path or ""),
            "source_sha256": source_sha256,
            "spans": spans,
        },
        "materiality_gate": _materiality_gate(facts),
        "decision_record": {
            "decision": "confirmed_intent_accepted",
            "fact_authority": "product_facts",
            "markdown_authority": "ingest_only",
            PRODUCT_FACTS_HASH_KEY: product_facts_hash(facts),
        },
    }


def product_intent_authority_from_envelope(
    envelope: Mapping[str, Any],
    *,
    structured_intent_path: Path | str | None = None,
    markdown_source_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return the compact transaction-bound authority snapshot for an envelope."""

    source_evidence = envelope.get("source_evidence") if isinstance(envelope.get("source_evidence"), Mapping) else {}
    custody_ledger = envelope.get("custody_ledger") if isinstance(envelope.get("custody_ledger"), Mapping) else {}
    decision_record = envelope.get("decision_record") if isinstance(envelope.get("decision_record"), Mapping) else {}
    materiality_gate = envelope.get("materiality_gate") if isinstance(envelope.get("materiality_gate"), Mapping) else {}
    fields = custody_ledger.get("fields") if isinstance(custody_ledger.get("fields"), Mapping) else {}
    material_fields: dict[str, dict[str, Any]] = {}
    for key in MATERIAL_FACT_KEYS:
        field = fields.get(key) if isinstance(fields.get(key), Mapping) else {}
        material_fields[key] = {
            "custody_state": clean_markdown_text(field.get("custody_state")),
            "derivation": clean_markdown_text(field.get("derivation")),
            "confidence": clean_markdown_text(field.get("confidence")),
            "source_span_ids": confirmed_text_values(field.get("source_span_ids")),
            "product_claim_span_ids": confirmed_text_values(field.get("product_claim_span_ids")),
        }
    material_custody_sha256 = _stable_sha256(material_fields)
    authority = {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "origin": "verified_typed_envelope",
        "structured_intent_path": clean_markdown_text(structured_intent_path),
        "markdown_source_path": clean_markdown_text(markdown_source_path or source_evidence.get("source_path")),
        "envelope_schema_version": clean_markdown_text(envelope.get("schema_version")),
        "ledger_version": clean_markdown_text(custody_ledger.get("version")),
        "decision": clean_markdown_text(decision_record.get("decision")),
        "fact_authority": clean_markdown_text(decision_record.get("fact_authority")),
        "markdown_authority": clean_markdown_text(decision_record.get("markdown_authority")),
        PRODUCT_FACTS_HASH_KEY: clean_markdown_text(decision_record.get(PRODUCT_FACTS_HASH_KEY)),
        "markdown_source_sha256": clean_markdown_text(source_evidence.get("source_sha256")),
        "source_format": clean_markdown_text(source_evidence.get("source_format")) or "unknown",
        "materiality_status": clean_markdown_text(materiality_gate.get("status")),
        "blocked_material_fields": confirmed_text_values(materiality_gate.get("blocked_fields")),
        "clarification_policy": clean_markdown_text(materiality_gate.get("clarification_policy")),
        "material_fields": material_fields,
        "material_custody_sha256": material_custody_sha256,
    }
    authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(authority)
    return authority


def product_intent_authority_from_intent(
    intent: Mapping[str, Any],
    *,
    source_text: str = "",
    source_path: Path | str | None = None,
    source_format: str = "in_memory_confirmed_intent",
) -> dict[str, Any]:
    """Build compact intent authority from an accepted in-memory intent mapping."""

    envelope = build_product_intent_envelope(
        product_facts_payload(intent),
        source_text=source_text,
        source_path=source_path,
        source_format=source_format,
    )
    return product_intent_authority_from_envelope(envelope)


def product_intent_authority_from_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return embedded authority from already accepted Product Intent data."""

    embedded = value.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if isinstance(embedded, Mapping):
        return dict(embedded)
    raise ValueError("confirmed Product Intent authority is missing; rebuild from a typed custody envelope")


def product_intent_authority_snapshot_hash(authority: Mapping[str, Any]) -> str:
    """Return the hash over compact authority fields, excluding the hash itself."""

    return _stable_sha256(_authority_snapshot_payload(authority))


def require_product_intent_authority(authority: Mapping[str, Any]) -> None:
    """Fail closed when a transaction lacks valid product-intent authority."""

    if not isinstance(authority, Mapping):
        raise ValueError("ProductCreateTransaction is missing confirmed Product Intent authority")
    required = {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "origin": "verified_typed_envelope",
        "envelope_schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "ledger_version": PRODUCT_INTENT_LEDGER_VERSION,
        "decision": "confirmed_intent_accepted",
        "fact_authority": "product_facts",
        "markdown_authority": "ingest_only",
    }
    for key, expected in required.items():
        if clean_markdown_text(authority.get(key)) != expected:
            raise ValueError("ProductCreateTransaction confirmed Product Intent authority is invalid")
    if not clean_markdown_text(authority.get("structured_intent_path")):
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority is missing structured custody")
    if not clean_markdown_text(authority.get("markdown_source_path")):
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority is missing Markdown source custody")
    if not clean_markdown_text(authority.get(PRODUCT_FACTS_HASH_KEY)):
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority is missing the product facts hash")
    if not clean_markdown_text(authority.get("markdown_source_sha256")):
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority is missing source hash custody")
    if clean_markdown_text(authority.get("materiality_status")) != "passed":
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority did not pass materiality")
    if confirmed_text_values(authority.get("blocked_material_fields")):
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority still has blocked material fields")
    material_fields = authority.get("material_fields") if isinstance(authority.get("material_fields"), Mapping) else {}
    source_format = clean_markdown_text(authority.get("source_format"))
    for key in MATERIAL_FACT_KEYS:
        field = material_fields.get(key) if isinstance(material_fields.get(key), Mapping) else {}
        if clean_markdown_text(field.get("custody_state")) != "accepted_fact":
            raise ValueError(
                "ProductCreateTransaction confirmed Product Intent authority has unresolved material custody"
            )
        if source_format not in _STRUCTURED_SOURCE_FORMATS:
            if not confirmed_text_values(field.get("source_span_ids")):
                raise ValueError(
                    "ProductCreateTransaction confirmed Product Intent authority is missing material source custody"
                )
            if not confirmed_text_values(field.get("product_claim_span_ids")):
                raise ValueError(
                    "ProductCreateTransaction confirmed Product Intent authority is missing material product-claim custody"
                )
    if clean_markdown_text(authority.get("material_custody_sha256")) != _stable_sha256(
        {key: material_fields.get(key) for key in MATERIAL_FACT_KEYS}
    ):
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority custody hash mismatch")
    if clean_markdown_text(authority.get("authority_snapshot_sha256")) != product_intent_authority_snapshot_hash(authority):
        raise ValueError("ProductCreateTransaction confirmed Product Intent authority snapshot hash mismatch")


def _authority_snapshot_payload(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": clean_markdown_text(authority.get("version")),
        "origin": clean_markdown_text(authority.get("origin")),
        "structured_intent_path": clean_markdown_text(authority.get("structured_intent_path")),
        "markdown_source_path": clean_markdown_text(authority.get("markdown_source_path")),
        "envelope_schema_version": clean_markdown_text(authority.get("envelope_schema_version")),
        "ledger_version": clean_markdown_text(authority.get("ledger_version")),
        "decision": clean_markdown_text(authority.get("decision")),
        "fact_authority": clean_markdown_text(authority.get("fact_authority")),
        "markdown_authority": clean_markdown_text(authority.get("markdown_authority")),
        PRODUCT_FACTS_HASH_KEY: clean_markdown_text(authority.get(PRODUCT_FACTS_HASH_KEY)),
        "markdown_source_sha256": clean_markdown_text(authority.get("markdown_source_sha256")),
        "source_format": clean_markdown_text(authority.get("source_format")),
        "materiality_status": clean_markdown_text(authority.get("materiality_status")),
        "blocked_material_fields": confirmed_text_values(authority.get("blocked_material_fields")),
        "clarification_policy": clean_markdown_text(authority.get("clarification_policy")),
        "material_fields": authority.get("material_fields") if isinstance(authority.get("material_fields"), Mapping) else {},
        "material_custody_sha256": clean_markdown_text(authority.get("material_custody_sha256")),
    }


def _stable_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _envelope_product_facts_hash(value: Mapping[str, Any]) -> str:
    decision_record = value.get("decision_record")
    if not isinstance(decision_record, Mapping):
        return ""
    return clean_markdown_text(decision_record.get(PRODUCT_FACTS_HASH_KEY))


def _envelope_source_hash(value: Mapping[str, Any]) -> str:
    evidence = value.get("source_evidence")
    if not isinstance(evidence, Mapping):
        return ""
    return clean_markdown_text(evidence.get("source_sha256"))


def _source_spans(
    sections: Mapping[str, Sequence[str]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    spans: list[dict[str, Any]] = []
    source_span_ids_by_field: dict[str, list[str]] = {}
    product_claim_span_ids_by_field: dict[str, list[str]] = {}
    for section_key, rows in sections.items():
        section_classification = _span_classification(section_key)
        for index, row in enumerate(rows, start=1):
            text = clean_markdown_text(row)
            if not text:
                continue
            classified_units = (
                _canonical_source_units(text, section_key=section_key)
                if section_classification == "product_claim" and section_key in PRODUCT_FACT_KEYS
                else [(text, section_classification)]
            )
            for unit_index, (unit_text, classification) in enumerate(classified_units, start=1):
                span_id = f"{section_key}:{index}"
                if len(classified_units) > 1:
                    span_id = f"{span_id}.{unit_index}"
                span = {
                    "span_id": span_id,
                    "section_key": section_key,
                    "row_index": index,
                    "classification": classification,
                    "text": unit_text,
                }
                spans.append(span)
                if section_key in PRODUCT_FACT_KEYS:
                    source_span_ids_by_field.setdefault(section_key, []).append(span_id)
                    if classification == "product_claim":
                        product_claim_span_ids_by_field.setdefault(section_key, []).append(span_id)
    return spans, source_span_ids_by_field, product_claim_span_ids_by_field


def _canonical_source_units(text: str, *, section_key: str) -> list[tuple[str, str]]:
    units: list[tuple[str, str]] = []
    for sentence in _sentence_units(text):
        if section_key == "first_path" and is_terminal_first_path_meta_loop_summary(sentence):
            units.append((sentence, "supporting_evidence"))
            continue
        inline_meta = split_unpunctuated_first_path_meta_control(sentence) if section_key == "first_path" else None
        if inline_meta is not None:
            before, meta, after = inline_meta
            units.extend(
                (fragment, classification)
                for fragment, classification in (
                    (before, "product_claim"),
                    (meta, "supporting_evidence"),
                    (after, "product_claim"),
                )
                if fragment
            )
            continue
        clauses = _clause_units(sentence)
        if section_key == "first_path" and any(
            _is_first_path_supporting_clause(clause)
            for clause in clauses
        ):
            units.extend(
                (
                    clause,
                    "supporting_evidence"
                    if _is_first_path_supporting_clause(clause)
                    else "product_claim",
                )
                for clause in clauses
            )
            continue
        units.append((sentence, "product_claim"))
    return units


def _sentence_units(value: str) -> list[str]:
    rows = re.split(r"(?<=[.!?])\s+", clean_markdown_text(value))
    return [text for row in rows if (text := clean_markdown_text(row))]


def _clause_units(value: str) -> list[str]:
    rows = re.split(r"\s+(?:[\u2013\u2014]|-)\s+|[;,]\s+", clean_markdown_text(value))
    return [text for row in rows if (text := clean_markdown_text(row).strip(" .;"))]


def _is_first_path_supporting_clause(value: str) -> bool:
    """Keep editorial product-proof summaries out of product-claim custody."""

    text = clean_markdown_text(value)
    if not is_first_path_meta_control_language(text):
        return False
    return not bool(
        re.search(
            r"\b(?:can|will|needs?\s+to)\b|\bfrom\b.+\bthrough\b|\b(?:by|after|before)\s+\w+ing\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _add_source_title_span(
    facts: Mapping[str, Any],
    *,
    spans: list[dict[str, Any]],
    source_span_ids_by_field: dict[str, list[str]],
    product_claim_span_ids_by_field: dict[str, list[str]],
    source_text: str,
) -> None:
    if source_span_ids_by_field.get("title"):
        return
    title = clean_markdown_text(facts.get("title"))
    if not title or title.casefold() not in clean_markdown_text(source_text).casefold():
        return
    span_id = "title:source-heading"
    spans.append(
        {
            "span_id": span_id,
            "section_key": "title",
            "row_index": 0,
            "classification": "product_claim",
            "text": title,
        }
    )
    source_span_ids_by_field["title"] = [span_id]
    product_claim_span_ids_by_field["title"] = [span_id]


def _add_source_story_span(
    facts: Mapping[str, Any],
    *,
    spans: list[dict[str, Any]],
    source_span_ids_by_field: dict[str, list[str]],
    product_claim_span_ids_by_field: dict[str, list[str]],
    source_text: str,
) -> None:
    if source_span_ids_by_field.get("product_story"):
        return
    story = clean_markdown_text(facts.get("product_story"))
    if not story or story.casefold() not in clean_markdown_text(source_text).casefold():
        return
    span_id = "product_story:source-preamble"
    spans.append(
        {
            "span_id": span_id,
            "section_key": "product_story",
            "row_index": 0,
            "classification": "product_claim",
            "text": story,
        }
    )
    source_span_ids_by_field["product_story"] = [span_id]
    product_claim_span_ids_by_field["product_story"] = [span_id]


def _span_classification(section_key: str) -> str:
    if section_key in PRODUCT_FACT_KEYS:
        return "product_claim"
    if is_confirmed_intent_ignored_section(section_key):
        return "ignored_instruction"
    if is_confirmed_intent_supporting_section(section_key) or section_key == "preamble":
        return "supporting_evidence"
    return "supporting_evidence"


def _field_custody(
    facts: Mapping[str, Any],
    *,
    source_span_ids_by_field: Mapping[str, Sequence[str]],
    product_claim_span_ids_by_field: Mapping[str, Sequence[str]],
    source_format: str,
) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    structured_source = source_format in _STRUCTURED_SOURCE_FORMATS
    for key in PRODUCT_FACT_KEYS:
        if key not in facts or not _has_fact_value(facts.get(key)):
            continue
        source_span_ids = list(source_span_ids_by_field.get(key, ()))
        product_claim_span_ids = list(product_claim_span_ids_by_field.get(key, ()))
        canonical_claim = bool(product_claim_span_ids)
        state = _custody_state(
            key=key,
            span_ids=product_claim_span_ids,
            structured_source=structured_source,
        )
        fields[key] = {
            "custody_state": state,
            "derivation": (
                "canonical_product_section"
                if canonical_claim
                else _derivation_for(
                    state=state,
                    span_ids=product_claim_span_ids,
                    structured_source=structured_source,
                )
            ),
            "confidence": _confidence_for(state),
            "source_span_ids": source_span_ids,
            "product_claim_span_ids": product_claim_span_ids,
        }
    return fields


def _custody_state(*, key: str, span_ids: Sequence[str], structured_source: bool) -> str:
    if key == "assumptions":
        return "assumption"
    if span_ids or structured_source:
        return "accepted_fact"
    return "inferred_fact"


def _derivation_for(*, state: str, span_ids: Sequence[str], structured_source: bool) -> str:
    if span_ids:
        return "canonical_product_section"
    if structured_source:
        return "structured_intent_fact"
    if state == "assumption":
        return "visible_assumption"
    return "normalization_or_completion"


def _confidence_for(state: str) -> str:
    if state == "accepted_fact":
        return "high"
    if state == "assumption":
        return "visible"
    return "medium"


def _materiality_gate(facts: Mapping[str, Any]) -> dict[str, Any]:
    missing = [key for key in MATERIAL_FACT_KEYS if not _has_fact_value(facts.get(key))]
    return {
        "status": "clarification_required" if missing else "passed",
        "blocked_fields": missing,
        "clarification_policy": "block_only_material_unknowns",
    }


def _has_fact_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(clean_markdown_text(value))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(clean_markdown_text(row) for row in value)
    return value is not None


__all__ = [
    "PRODUCT_FACT_KEYS",
    "PRODUCT_FACTS_HASH_KEY",
    "PRODUCT_INTENT_AUTHORITY_KEY",
    "PRODUCT_INTENT_AUTHORITY_VERSION",
    "PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION",
    "PRODUCT_INTENT_LEDGER_VERSION",
    "build_product_intent_envelope",
    "is_product_intent_envelope",
    "product_intent_authority_from_envelope",
    "product_intent_authority_from_intent",
    "product_intent_authority_from_mapping",
    "product_intent_authority_snapshot_hash",
    "product_facts_from_envelope",
    "product_facts_payload",
    "require_product_intent_authority",
]
