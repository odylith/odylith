"""Typed custody envelope for confirmed greenfield product intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    ATOMIC_FACT_LEDGER_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    append_atomic_source_spans,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    atomic_fact_ledger_hash,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    build_atomic_fact_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    require_atomic_fact_ledger,
)
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
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    MATERIAL_FACT_KEYS,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_LEDGER_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    TYPED_SOURCE_FORMATS,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    product_intent_authority_snapshot_hash as _sealed_product_intent_authority_snapshot_hash,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    product_intent_material_custody_hash,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    require_product_intent_authority_structure,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    greenfield_operating_envelope_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_typed_source_spans import (
    append_typed_product_claim_spans,
)


PRODUCT_FACTS_HASH_KEY = "product_facts_sha256"
LEGACY_PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSIONS = frozenset(
    {"odylith.product-intent-envelope.v3"}
)

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
    """Return true when a JSON object carries the current product-intent envelope."""

    return isinstance(value, Mapping) and str(value.get("schema_version") or "") == PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION


def is_legacy_product_intent_envelope(value: object) -> bool:
    """Return true for a supported legacy envelope that requires pre-confirm migration."""

    return bool(
        isinstance(value, Mapping)
        and str(value.get("schema_version") or "") in LEGACY_PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSIONS
    )


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
        payload = product_facts_payload(facts)
        expected_hash = _envelope_product_facts_hash(value)
        if expected_hash and expected_hash != product_facts_hash(payload):
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


def product_facts_from_legacy_envelope(value: object, *, source_text: str = "") -> dict[str, Any] | None:
    """Recover hash-bound legacy facts for a current pre-confirm envelope rebuild."""

    if not is_legacy_product_intent_envelope(value) or not isinstance(value, Mapping) or not source_text:
        return None
    expected_source_hash = _envelope_source_hash(value)
    actual_source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if not expected_source_hash or expected_source_hash != actual_source_hash:
        return None
    facts = value.get("product_facts")
    if not isinstance(facts, Mapping):
        return None
    payload = product_facts_payload(facts)
    expected_facts_hash = _envelope_product_facts_hash(value)
    if not expected_facts_hash or expected_facts_hash != product_facts_hash(payload):
        return None
    return payload


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


def rebind_authoritative_product_facts(
    intent: Mapping[str, Any],
    *,
    authoritative_intent: Mapping[str, Any],
) -> dict[str, Any]:
    """Restore sealed product facts after proposal-only completion adds derived metadata."""

    rebound = copy.deepcopy(dict(intent))
    for key in PRODUCT_FACT_KEYS:
        rebound.pop(key, None)
    rebound.update(copy.deepcopy(product_facts_payload(authoritative_intent)))
    return rebound


def build_product_intent_envelope(
    intent: Mapping[str, Any],
    *,
    source_text: str = "",
    source_path: Path | str | None = None,
    source_format: str = "",
) -> dict[str, Any]:
    """Build the typed custody record trusted by pre-confirm compilers."""

    facts = product_facts_payload(intent)
    sections = (
        confirmed_intent_sections(source_text)
        if source_text and source_format not in TYPED_SOURCE_FORMATS
        else {}
    )
    spans, source_span_ids_by_field, product_claim_span_ids_by_field = _source_spans(sections)
    if source_format not in TYPED_SOURCE_FORMATS:
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
        _add_unheaded_material_source_spans(
            facts,
            spans=spans,
            source_span_ids_by_field=source_span_ids_by_field,
            product_claim_span_ids_by_field=product_claim_span_ids_by_field,
            source_sections=sections,
        )
    append_typed_product_claim_spans(
        facts=facts,
        spans=spans,
        source_span_ids_by_field=source_span_ids_by_field,
        product_claim_span_ids_by_field=product_claim_span_ids_by_field,
        source_text=source_text,
        source_format=source_format,
        typed_source_formats=TYPED_SOURCE_FORMATS,
    )
    append_atomic_source_spans(spans)
    _add_span_digests(spans)
    evidence_span_ids = _evidence_span_ids(spans)
    fields = _field_custody(
        facts,
        source_span_ids_by_field=source_span_ids_by_field,
        product_claim_span_ids_by_field=product_claim_span_ids_by_field,
        evidence_span_ids=evidence_span_ids,
        spans=spans,
        source_format=source_format,
    )
    atomic_facts = build_atomic_fact_ledger(facts=facts, spans=spans)
    ignored = [span for span in spans if span.get("classification") == "ignored_instruction"]
    supporting = [span for span in spans if span.get("classification") == "supporting_evidence"]
    source_sha256 = hashlib.sha256(str(source_text or "").encode("utf-8")).hexdigest() if source_text else ""
    operating_envelope = greenfield_operating_envelope_receipt(
        facts=facts,
        source_format=source_format or "unknown",
        source_size_bytes=len(str(source_text or "").encode("utf-8")),
    )
    return {
        "schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "product_facts": facts,
        "custody_ledger": {
            "version": PRODUCT_INTENT_LEDGER_VERSION,
            "fields": fields,
            "atomic_facts": atomic_facts,
            "ignored_instructions": ignored,
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
    atomic_facts = custody_ledger.get("atomic_facts")
    if not isinstance(atomic_facts, Sequence) or isinstance(atomic_facts, (str, bytes, bytearray)):
        atomic_facts = []
    facts = envelope.get("product_facts") if isinstance(envelope.get("product_facts"), Mapping) else {}
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
            "custody_state": clean_markdown_text(field.get("custody_state")),
            "derivation": clean_markdown_text(field.get("derivation")),
            "confidence": clean_markdown_text(field.get("confidence")),
            "entailment_relationship": clean_markdown_text(field.get("entailment_relationship")),
            "source_span_ids": confirmed_text_values(field.get("source_span_ids")),
            "product_claim_span_ids": confirmed_text_values(field.get("product_claim_span_ids")),
            "source_span_refs": _authority_span_refs(field.get("source_span_refs")),
        }
    material_custody_sha256 = product_intent_material_custody_hash(material_fields)
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
        "operating_envelope": copy.deepcopy(dict(operating_envelope)),
        "material_fields": material_fields,
        "material_custody_sha256": material_custody_sha256,
        "atomic_ledger_version": ATOMIC_FACT_LEDGER_VERSION,
        "atomic_facts": copy.deepcopy(list(atomic_facts)),
        "atomic_custody_sha256": atomic_fact_ledger_hash(atomic_facts),
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

    facts = product_facts_payload(intent)
    if not source_text and source_format in TYPED_SOURCE_FORMATS:
        source_text = json.dumps(facts, ensure_ascii=True, sort_keys=True)
    envelope = build_product_intent_envelope(
        facts,
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


def _add_unheaded_material_source_spans(
    facts: Mapping[str, Any],
    *,
    spans: list[dict[str, Any]],
    source_span_ids_by_field: dict[str, list[str]],
    product_claim_span_ids_by_field: dict[str, list[str]],
    source_sections: Mapping[str, Sequence[str]],
) -> None:
    """Preserve paragraph-level custody when a complete intent has no headings."""

    if any(key != "preamble" for key in source_sections):
        return
    preamble_rows = [
        (index, clean_markdown_text(row))
        for index, row in enumerate(source_sections.get("preamble", ()), start=1)
        if clean_markdown_text(row)
    ]
    for key in MATERIAL_FACT_KEYS:
        if source_span_ids_by_field.get(key):
            continue
        matched_rows = _unheaded_source_rows_for_fact(key=key, value=facts.get(key), rows=preamble_rows)
        if not matched_rows:
            continue
        span_ids: list[str] = []
        for row_index, text in matched_rows:
            span_id = f"{key}:source-preamble:{row_index}"
            spans.append(
                {
                    "span_id": span_id,
                    "section_key": key,
                    "row_index": row_index,
                    "classification": "product_claim",
                    "text": text,
                }
            )
            span_ids.append(span_id)
        source_span_ids_by_field[key] = span_ids
        product_claim_span_ids_by_field[key] = span_ids


def _unheaded_source_rows_for_fact(
    *,
    key: str,
    value: Any,
    rows: Sequence[tuple[int, str]],
) -> list[tuple[int, str]]:
    if key != "human_actors":
        fact = clean_markdown_text(value).casefold()
        return [(index, text) for index, text in rows if fact and fact in text.casefold()]
    labels = [
        clean_markdown_text(actor).split(":", 1)[0].casefold()
        for actor in confirmed_text_values(value)
        if clean_markdown_text(actor)
    ]
    matched: list[tuple[int, str]] = []
    for label in labels:
        row = next(((index, text) for index, text in rows if label and label in text.casefold()), None)
        if row is None:
            return []
        if row not in matched:
            matched.append(row)
    return matched


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
    evidence_span_ids: Sequence[str],
    spans: Sequence[Mapping[str, Any]],
    source_format: str,
) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    typed_source = source_format in TYPED_SOURCE_FORMATS
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
            evidence_span_ids=evidence_span_ids,
            typed_source=typed_source,
        )
        source_span_ids = direct_source_span_ids or (
            list(evidence_span_ids) if state in {"bounded_interpretation", "assumption"} else []
        )
        fields[key] = {
            "custody_state": state,
            "derivation": (
                "canonical_product_section"
                if canonical_claim
                else _derivation_for(
                    state=state,
                    span_ids=product_claim_span_ids,
                    typed_source=typed_source,
                )
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
    evidence_span_ids: Sequence[str],
    typed_source: bool,
) -> str:
    if key == "assumptions":
        return "assumption"
    if span_ids:
        return "accepted_fact"
    if evidence_span_ids:
        return "bounded_interpretation"
    if typed_source:
        return "inferred_fact"
    return "inferred_fact"


def _derivation_for(*, state: str, span_ids: Sequence[str], typed_source: bool) -> str:
    if span_ids:
        return "canonical_product_section"
    if state == "assumption":
        return "visible_assumption"
    if state == "bounded_interpretation":
        return "bounded_interpretation_from_evidence"
    if typed_source:
        return "unresolved_typed_source_fact"
    return "normalization_or_completion"


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
        text = clean_markdown_text(span.get("text"))
        span["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()


def _evidence_span_ids(spans: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        str(span.get("span_id"))
        for span in spans
        if str(span.get("span_id") or "")
        and span.get("classification") == "supporting_evidence"
        and not clean_markdown_text(span.get("text")).startswith("<!-- odylith:")
    ]


def _span_ref(span: Mapping[str, Any]) -> dict[str, str]:
    return {
        "span_id": clean_markdown_text(span.get("span_id")),
        "classification": clean_markdown_text(span.get("classification")),
        "text_sha256": clean_markdown_text(span.get("text_sha256")),
    }


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
        return bool(clean_markdown_text(value))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(clean_markdown_text(row) for row in value)
    return value is not None


__all__ = [
    "LEGACY_PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSIONS",
    "PRODUCT_FACT_KEYS",
    "PRODUCT_FACTS_HASH_KEY",
    "PRODUCT_INTENT_AUTHORITY_KEY",
    "PRODUCT_INTENT_AUTHORITY_VERSION",
    "PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION",
    "PRODUCT_INTENT_LEDGER_VERSION",
    "build_product_intent_envelope",
    "is_legacy_product_intent_envelope",
    "is_product_intent_envelope",
    "product_intent_authority_from_envelope",
    "product_intent_authority_from_intent",
    "product_intent_authority_from_mapping",
    "product_intent_authority_snapshot_hash",
    "product_facts_from_envelope",
    "product_facts_from_legacy_envelope",
    "product_facts_payload",
    "rebind_authoritative_product_facts",
    "require_product_intent_authority",
]
