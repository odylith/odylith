"""Typed custody envelope for confirmed greenfield product intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION = "odylith.product-intent-envelope.v2"
PRODUCT_INTENT_LEDGER_VERSION = "odylith.product-intent-custody-ledger.v1"
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
    "internal_systems",
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
    spans, span_ids_by_field = _source_spans(sections)
    _add_source_title_span(facts, spans=spans, span_ids_by_field=span_ids_by_field, source_text=source_text)
    ignored = [span for span in spans if span.get("classification") == "ignored_instruction"]
    supporting = [span for span in spans if span.get("classification") == "supporting_evidence"]
    source_sha256 = hashlib.sha256(str(source_text or "").encode("utf-8")).hexdigest() if source_text else ""
    return {
        "schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "product_facts": facts,
        "custody_ledger": {
            "version": PRODUCT_INTENT_LEDGER_VERSION,
            "fields": _field_custody(facts, span_ids_by_field=span_ids_by_field, source_format=source_format),
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


def _source_spans(sections: Mapping[str, Sequence[str]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    spans: list[dict[str, Any]] = []
    span_ids_by_field: dict[str, list[str]] = {}
    for section_key, rows in sections.items():
        classification = _span_classification(section_key)
        for index, row in enumerate(rows, start=1):
            text = clean_markdown_text(row)
            if not text:
                continue
            span_id = f"{section_key}:{index}"
            span = {
                "span_id": span_id,
                "section_key": section_key,
                "row_index": index,
                "classification": classification,
                "text": text,
            }
            spans.append(span)
            if classification == "product_claim" and section_key in PRODUCT_FACT_KEYS:
                span_ids_by_field.setdefault(section_key, []).append(span_id)
    return spans, span_ids_by_field


def _add_source_title_span(
    facts: Mapping[str, Any],
    *,
    spans: list[dict[str, Any]],
    span_ids_by_field: dict[str, list[str]],
    source_text: str,
) -> None:
    if span_ids_by_field.get("title"):
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
    span_ids_by_field["title"] = [span_id]


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
    span_ids_by_field: Mapping[str, Sequence[str]],
    source_format: str,
) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    structured_source = source_format in {"legacy_json", "typed_envelope_json"}
    for key in PRODUCT_FACT_KEYS:
        if key not in facts or not _has_fact_value(facts.get(key)):
            continue
        span_ids = list(span_ids_by_field.get(key, ()))
        state = _custody_state(key=key, span_ids=span_ids, structured_source=structured_source)
        fields[key] = {
            "custody_state": state,
            "derivation": _derivation_for(state=state, span_ids=span_ids, structured_source=structured_source),
            "confidence": _confidence_for(state),
            "source_span_ids": span_ids,
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
    "PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION",
    "PRODUCT_INTENT_LEDGER_VERSION",
    "build_product_intent_envelope",
    "is_product_intent_envelope",
    "product_facts_from_envelope",
    "product_facts_payload",
]
