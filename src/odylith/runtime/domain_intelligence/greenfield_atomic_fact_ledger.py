"""Exact model-authored atomic evidence custody for Greenfield intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    ATOMIC_FACT_CATEGORIES,
    ATOMIC_POLARITIES,
    AUTHORED_RELATION_ROLES,
)


ATOMIC_FACT_LEDGER_VERSION = "odylith.product-intent-atomic-facts.v3"
ATOMIC_CATEGORY_FIELDS = {
    "actors": ("human_actors", "customer"),
    "actions": ("first_path", "internal_systems", "component_responsibilities"),
    "states": ("state_object", "first_path"),
    "outputs": ("first_path", "success_metrics", "proof_boundary", "product_story"),
    "constraints": (
        "operational_constraints",
        "first_path",
        "success_metrics",
        "proof_boundary",
        "non_goals",
    ),
    "dependencies": ("external_systems",),
    "assumptions": ("assumptions",),
    "ambiguities": ("ambiguities",),
    "non_goals": ("non_goals",),
}
ATOMIC_PROJECTION_FIELDS = frozenset(
    {
        "title",
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
    }
)
MAX_ATOMIC_FACTS = 512
MAX_ATOMIC_VALUE_LENGTH = 1200

_CLAIM_FIELDS = frozenset(
    {
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
)
_LEDGER_FIELDS = frozenset(
    {
        "atom_id",
        "categories",
        "normalized_value",
        "polarity",
        "custody_state",
        "entailment_relationship",
        "source_span_ids",
        "source_span_refs",
        "projection_links",
    }
)
_EXACT_PROJECTION_FIELDS = frozenset(
    {
        "field",
        "path",
        "value_sha256",
        "projection_start_byte",
        "projection_end_byte",
        "relation_order",
        "relation_role",
    }
)
_EXACT_SOURCE_REF_FIELDS = frozenset(
    {
        "span_id",
        "classification",
        "text_sha256",
        "source_start_byte",
        "source_end_byte",
    }
)


def append_atomic_source_spans(
    spans: list[dict[str, Any]],
    *,
    authored_atomic_claims: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    """Append exact model-authored claim spans; prose decomposition is unsupported."""

    claims = _require_authored_claims(authored_atomic_claims)
    for index, claim in enumerate(claims, start=1):
        quote = _claim_quote(claim)
        start = claim["source_start_byte"]
        end = claim["source_end_byte"]
        quote_sha256 = str(claim["quote_sha256"])
        spans.append(
            {
                "span_id": _authored_span_id(
                    index=index,
                    start=start,
                    end=end,
                    quote_sha256=quote_sha256,
                ),
                "section_key": "atomic_evidence",
                "source_section_key": str(claim["field"]),
                "row_index": index,
                "classification": "product_claim",
                "text": quote,
                "text_sha256": _sha256_text(quote),
                "source_start_byte": start,
                "source_end_byte": end,
                "quote_sha256": quote_sha256,
            }
        )


def build_atomic_fact_ledger(
    *,
    facts: Mapping[str, Any],
    spans: Sequence[Mapping[str, Any]],
    authored_atomic_claims: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Seal exact model-authored atoms without tokenizing or classifying prose."""

    claims = _require_authored_claims(authored_atomic_claims)
    atomic_spans = {
        str(span.get("span_id") or ""): span
        for span in spans
        if span.get("section_key") == "atomic_evidence"
    }
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(claims, start=1):
        quote = _claim_quote(claim)
        start = claim["source_start_byte"]
        end = claim["source_end_byte"]
        quote_sha256 = str(claim["quote_sha256"])
        span_id = _authored_span_id(
            index=index,
            start=start,
            end=end,
            quote_sha256=quote_sha256,
        )
        span = atomic_spans.get(span_id)
        if span is None or str(span.get("text") or "") != quote:
            raise ValueError("model-authored Product Intent atomic source custody is malformed")
        projection = {
            "field": str(claim["field"]),
            "path": str(claim["projection_path"]),
            "value_sha256": str(claim["projection_value_sha256"]),
            "projection_start_byte": claim["projection_start_byte"],
            "projection_end_byte": claim["projection_end_byte"],
            "relation_order": claim["relation_order"],
            "relation_role": str(claim["relation_role"]),
        }
        source_ref = {
            "span_id": span_id,
            "classification": "product_claim",
            "text_sha256": _sha256_text(quote),
            "source_start_byte": start,
            "source_end_byte": end,
        }
        row = {
            "atom_id": "",
            "categories": [str(claim["category"])],
            "normalized_value": quote,
            "polarity": str(claim["polarity"]),
            "custody_state": "accepted_fact",
            "entailment_relationship": "exact_source_span",
            "source_span_ids": [span_id],
            "source_span_refs": [source_ref],
            "projection_links": [projection],
        }
        row["atom_id"] = _authored_atom_id(row)
        rows.append(row)
    rows.sort(key=lambda row: row["atom_id"])
    require_atomic_fact_ledger(rows, source_spans=spans, facts=facts)
    return rows


def atomic_fact_ledger_hash(value: Sequence[Mapping[str, Any]]) -> str:
    """Return the stable digest over the complete atomic custody ledger."""

    return hashlib.sha256(_canonical_json_bytes(list(value))).hexdigest()


def require_atomic_fact_ledger(
    value: Any,
    *,
    source_spans: Sequence[Mapping[str, Any]] = (),
    facts: Mapping[str, Any] | None = None,
) -> None:
    """Accept only exact model-authored atoms bound to exact source and fact bytes."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("ProductCreateTransaction atomic fact custody is malformed")
    rows = list(value)
    if not rows or len(rows) > MAX_ATOMIC_FACTS:
        raise ValueError("ProductCreateTransaction atomic fact custody is outside its bounded contract")
    projection_values = _exact_projection_value_index(facts) if facts is not None else None
    atom_ids: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != _LEDGER_FIELDS:
            raise ValueError("ProductCreateTransaction atomic fact custody is malformed")
        atom_id = str(row.get("atom_id") or "")
        if not _is_atom_id(atom_id) or atom_id != _authored_atom_id(row):
            raise ValueError("ProductCreateTransaction atomic fact custody has an invalid atom id")
        atom_ids.append(atom_id)
        _require_categories(row.get("categories"))
        quote = row.get("normalized_value")
        if not isinstance(quote, str) or not quote or len(quote) > MAX_ATOMIC_VALUE_LENGTH:
            raise ValueError("ProductCreateTransaction atomic fact custody has an invalid normalized value")
        if row.get("polarity") not in ATOMIC_POLARITIES:
            raise ValueError("ProductCreateTransaction atomic fact custody has an invalid polarity")
        if (
            row.get("custody_state") != "accepted_fact"
            or row.get("entailment_relationship") != "exact_source_span"
            or not _valid_exact_span_refs(row.get("source_span_refs"), row.get("source_span_ids"))
        ):
            raise ValueError("ProductCreateTransaction accepted atomic fact lacks exact source custody")
        if source_spans:
            _require_exact_source_custody(row, source_spans=source_spans)
        _require_projection_links(
            row.get("projection_links"),
            normalized_value=quote,
            projection_values=projection_values,
        )
    if atom_ids != sorted(atom_ids) or len(atom_ids) != len(set(atom_ids)):
        raise ValueError("ProductCreateTransaction atomic fact custody is not deterministic")


def atomic_claim_units(value: Any) -> tuple[str, ...]:
    """Return one exact authored value; runtime prose splitting is retired."""

    return (value,) if isinstance(value, str) and value else ()


def _require_authored_claims(
    value: Sequence[Mapping[str, Any]] | None,
) -> tuple[Mapping[str, Any], ...]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
        or any(not isinstance(claim, Mapping) or set(claim) != _CLAIM_FIELDS for claim in value)
    ):
        raise ValueError("model-authored Product Intent requires exact atomic claims")
    return tuple(value)


def _claim_quote(claim: Mapping[str, Any]) -> str:
    quote = claim.get("quote")
    start = claim.get("source_start_byte")
    end = claim.get("source_end_byte")
    digest = claim.get("quote_sha256")
    if (
        not isinstance(quote, str)
        or not quote
        or not _valid_byte_range(start, end, limit=2**63 - 1)
        or end - start != len(quote.encode("utf-8"))
        or not isinstance(digest, str)
        or digest != _sha256_text(quote)
    ):
        raise ValueError("model-authored Product Intent atomic source custody is malformed")
    return quote


def _require_categories(value: Any) -> None:
    if not isinstance(value, list) or not value or value != sorted(set(value)):
        raise ValueError("ProductCreateTransaction atomic fact custody has invalid categories")
    if not set(value) <= set(ATOMIC_FACT_CATEGORIES):
        raise ValueError("ProductCreateTransaction atomic fact custody has invalid categories")


def _require_projection_links(
    value: Any,
    *,
    normalized_value: str,
    projection_values: Mapping[tuple[str, str], str] | None,
) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("ProductCreateTransaction atomic fact lacks a canonical projection")
    ordering: list[tuple[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != _EXACT_PROJECTION_FIELDS:
            raise ValueError("ProductCreateTransaction atomic fact has an invalid canonical projection")
        field = str(row.get("field") or "")
        path = str(row.get("path") or "")
        start = row.get("projection_start_byte")
        end = row.get("projection_end_byte")
        relation_order = row.get("relation_order")
        relation_role = str(row.get("relation_role") or "")
        if field not in ATOMIC_PROJECTION_FIELDS or not path.startswith(f"/{field}"):
            raise ValueError("ProductCreateTransaction atomic fact has an invalid canonical projection")
        if not _is_sha256(row.get("value_sha256")):
            raise ValueError("ProductCreateTransaction atomic fact has an invalid canonical projection")
        if (
            not isinstance(relation_order, int)
            or isinstance(relation_order, bool)
            or relation_order < 0
            or (relation_order == 0 and relation_role)
            or (relation_order > 0 and relation_role not in AUTHORED_RELATION_ROLES)
        ):
            raise ValueError("ProductCreateTransaction atomic fact has an invalid relation binding")
        if projection_values is None:
            if not _valid_byte_range(start, end, limit=MAX_ATOMIC_VALUE_LENGTH * 8):
                raise ValueError("ProductCreateTransaction atomic fact has an invalid canonical projection")
        else:
            projected_value = projection_values.get((field, path))
            projected_bytes = projected_value.encode("utf-8") if projected_value is not None else b""
            if (
                projected_value is None
                or row.get("value_sha256") != _sha256_text(projected_value)
                or not _valid_byte_range(start, end, limit=len(projected_bytes))
                or projected_bytes[start:end] != normalized_value.encode("utf-8")
            ):
                raise ValueError("ProductCreateTransaction atomic fact is not bound to its canonical projection")
        ordering.append((field, path))
    if ordering != sorted(set(ordering)):
        raise ValueError("ProductCreateTransaction atomic fact projections are not deterministic")


def _require_exact_source_custody(
    row: Mapping[str, Any],
    *,
    source_spans: Sequence[Mapping[str, Any]],
) -> None:
    spans_by_id = {
        str(span.get("span_id") or ""): span
        for span in source_spans
        if str(span.get("span_id") or "")
    }
    span_id = row["source_span_ids"][0]
    ref = row["source_span_refs"][0]
    span = spans_by_id.get(span_id)
    quote = str(row["normalized_value"])
    if (
        span is None
        or span.get("classification") != "product_claim"
        or span.get("section_key") != "atomic_evidence"
        or span.get("text") != quote
        or span.get("text_sha256") != _sha256_text(quote)
        or ref.get("span_id") != span_id
        or ref.get("classification") != "product_claim"
        or ref.get("text_sha256") != _sha256_text(quote)
        or ref.get("source_start_byte") != span.get("source_start_byte")
        or ref.get("source_end_byte") != span.get("source_end_byte")
    ):
        raise ValueError("ProductCreateTransaction accepted atomic fact lacks exact source custody")


def _valid_exact_span_refs(value: Any, span_ids: Any) -> bool:
    if not isinstance(span_ids, list) or len(span_ids) != 1:
        return False
    if not isinstance(value, list) or len(value) != 1:
        return False
    row = value[0]
    return bool(
        isinstance(row, Mapping)
        and set(row) == _EXACT_SOURCE_REF_FIELDS
        and row.get("span_id") == span_ids[0]
        and row.get("classification") == "product_claim"
        and _is_sha256(row.get("text_sha256"))
        and _valid_byte_range(
            row.get("source_start_byte"),
            row.get("source_end_byte"),
            limit=2**63 - 1,
        )
    )


def _exact_projection_value_index(facts: Mapping[str, Any]) -> dict[tuple[str, str], str]:
    values: dict[tuple[str, str], str] = {}
    for field in ATOMIC_PROJECTION_FIELDS:
        value = facts.get(field)
        if isinstance(value, str) and value:
            values[(field, f"/{field}")] = value
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, item in enumerate(value):
                if isinstance(item, str) and item:
                    values[(field, f"/{field}/{index}")] = item
    return values


def _authored_atom_id(row: Mapping[str, Any]) -> str:
    payload = {
        "categories": row.get("categories"),
        "quote_sha256": _sha256_text(str(row.get("normalized_value") or "")),
        "polarity": row.get("polarity"),
        "source_span_refs": row.get("source_span_refs"),
        "projection_links": row.get("projection_links"),
    }
    return f"AF-{hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()[:16]}"


def _authored_span_id(*, index: int, start: Any, end: Any, quote_sha256: str) -> str:
    return f"authoring-atom:{index}:{start}:{end}:{quote_sha256[:16]}"


def _is_atom_id(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and value.startswith("AF-")
        and len(value) == 19
        and _is_hex(value[3:])
    )


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return bool(value) and all(character in "0123456789abcdef" for character in value)


def _valid_byte_range(start: Any, end: Any, *, limit: int) -> bool:
    return bool(
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= start < end <= limit
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


__all__ = [
    "ATOMIC_CATEGORY_FIELDS",
    "ATOMIC_FACT_CATEGORIES",
    "ATOMIC_FACT_LEDGER_VERSION",
    "ATOMIC_POLARITIES",
    "ATOMIC_PROJECTION_FIELDS",
    "AUTHORED_RELATION_ROLES",
    "append_atomic_source_spans",
    "atomic_claim_units",
    "atomic_fact_ledger_hash",
    "build_atomic_fact_ledger",
    "require_atomic_fact_ledger",
]
