"""Atomic evidence custody for Greenfield canonical product facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import actor_signature
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import (
    coordinated_subjects,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import (
    declaration_subject_predicate,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import (
    without_source_metadata_clauses,
)
from odylith.runtime.domain_intelligence.greenfield_proof_boundary_text import (
    derived_proof_boundary_text,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


ATOMIC_FACT_LEDGER_VERSION = "odylith.product-intent-atomic-facts.v1"
ATOMIC_FACT_CATEGORIES = (
    "actors",
    "actions",
    "states",
    "outputs",
    "constraints",
    "dependencies",
    "assumptions",
    "ambiguities",
    "non_goals",
)
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
_ATOMIC_FIELD_CATEGORIES = {
    "human_actors": ("actors",),
    "customer": ("actors",),
    "first_path": ("actions", "states", "outputs"),
    "component_responsibilities": ("actions",),
    "state_object": ("states",),
    "success_metrics": ("outputs",),
    "proof_boundary": ("outputs",),
    "product_story": ("outputs",),
    "operational_constraints": ("constraints",),
    "external_systems": ("dependencies",),
    "internal_systems": ("actions",),
    "assumptions": ("assumptions",),
    "ambiguities": ("ambiguities",),
    "non_goals": ("constraints", "non_goals"),
}
_CONSTRAINT_FIELDS = frozenset(
    {"operational_constraints", "first_path", "success_metrics", "proof_boundary", "non_goals"}
)
ATOMIC_PROJECTION_FIELDS = frozenset(
    field
    for fields in ATOMIC_CATEGORY_FIELDS.values()
    for field in fields
)
MAX_ATOMIC_FACTS = 512
MAX_ATOMIC_VALUE_LENGTH = 1200

_TOKEN_RE = re.compile(r"[a-z0-9]+", flags=re.IGNORECASE)
_UNIT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|[;,:]\s*")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "before",
        "by",
        "can",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "one",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "with",
    }
)
_PROHIBITED_RE = re.compile(
    r"\b(?:must\s+not|do\s+not|does\s+not|never|no|without)\b|"
    r"\b(?:is|are)\s+(?:forbidden|prohibited)\b|"
    r"(?<!-)\b(?:forbidden|prohibited)\s+(?:from|to)\b",
    flags=re.IGNORECASE,
)
_REQUIRED_RE = re.compile(r"\b(?:must|required|requires?|shall)\b", flags=re.IGNORECASE)


def append_atomic_source_spans(spans: list[dict[str, Any]]) -> None:
    """Append exact evidence subspans used for atom-level entailment."""

    additions: list[dict[str, Any]] = []
    for span in tuple(spans):
        if not _is_entailment_source(span):
            continue
        text = clean_markdown_text(span.get("text"))
        units = _source_atomic_units(
            text,
            source_section_key=clean_markdown_text(span.get("section_key")),
        )
        if len(units) <= 1:
            continue
        parent_id = clean_markdown_text(span.get("span_id"))
        for index, unit in enumerate(units, start=1):
            additions.append(
                {
                    "span_id": f"{parent_id}:atom:{index}",
                    "section_key": "atomic_evidence",
                    "source_section_key": clean_markdown_text(span.get("section_key")),
                    "row_index": span.get("row_index", 0),
                    "classification": clean_markdown_text(span.get("classification")),
                    "parent_span_id": parent_id,
                    "text": unit,
                }
            )
    spans.extend(additions)


def build_atomic_fact_ledger(
    *,
    facts: Mapping[str, Any],
    spans: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Bind canonical fact atoms to exact source spans without accepting adjacency."""

    source_spans = _eligible_source_spans(spans)
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for field in sorted(ATOMIC_PROJECTION_FIELDS):
        if field not in facts:
            continue
        categories = _categories_for_field(field)
        for path, value in _projection_atoms(
            field=field,
            value=facts.get(field),
            human_actors=confirmed_text_values(facts.get("human_actors")),
            first_path=facts.get("first_path"),
        ):
            normalized_value = clean_markdown_text(value).strip(" .;:")
            if not normalized_value:
                continue
            polarity = _polarity(normalized_value)
            refs = _entailed_source_refs(
                value=normalized_value,
                polarity=polarity,
                spans=source_spans,
                field=field,
            )
            custody_state = "accepted_fact" if refs else (
                "assumption" if field == "assumptions" else "bounded_interpretation"
            )
            relationship = {
                "accepted_fact": "ordered_source_entailment",
                "assumption": "visible_assumption_from",
                "bounded_interpretation": "bounded_interpretation_of",
            }[custody_state]
            atom_categories = (
                {"constraints"}
                if polarity == "prohibited" and field in _CONSTRAINT_FIELDS
                else set(categories)
            )
            if field == "non_goals":
                atom_categories.add("non_goals")
            key = (_normalized_token_text(normalized_value), polarity)
            projection = {
                "field": field,
                "path": path,
                "value_sha256": _sha256_text(normalized_value),
            }
            existing = rows.get(key)
            if existing is None:
                rows[key] = {
                    "atom_id": _atom_id(normalized_value, polarity=polarity),
                    "categories": sorted(atom_categories),
                    "normalized_value": normalized_value,
                    "polarity": polarity,
                    "custody_state": custody_state,
                    "entailment_relationship": relationship,
                    "source_span_ids": [ref["span_id"] for ref in refs],
                    "source_span_refs": refs,
                    "projection_links": [projection],
                }
                continue
            existing["categories"] = sorted(set(existing["categories"]) | atom_categories)
            if projection not in existing["projection_links"]:
                existing["projection_links"].append(projection)
                existing["projection_links"].sort(key=lambda item: (item["field"], item["path"]))
            if refs and existing["custody_state"] != "accepted_fact":
                existing["custody_state"] = "accepted_fact"
                existing["entailment_relationship"] = "ordered_source_entailment"
                existing["source_span_ids"] = [ref["span_id"] for ref in refs]
                existing["source_span_refs"] = refs
    ledger = sorted(rows.values(), key=lambda row: row["atom_id"])
    require_atomic_fact_ledger(ledger, source_spans=source_spans, facts=facts)
    return ledger


def atomic_fact_ledger_hash(value: Sequence[Mapping[str, Any]]) -> str:
    """Return the stable digest over the complete atomic custody ledger."""

    return hashlib.sha256(_canonical_json_bytes(list(value))).hexdigest()


def require_atomic_fact_ledger(
    value: Any,
    *,
    source_spans: Sequence[Mapping[str, Any]] = (),
    facts: Mapping[str, Any] | None = None,
) -> None:
    """Reject malformed, unbounded, or adjacency-only atomic custody."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("ProductCreateTransaction atomic fact custody is malformed")
    rows = list(value)
    if not rows or len(rows) > MAX_ATOMIC_FACTS:
        raise ValueError("ProductCreateTransaction atomic fact custody is outside its bounded contract")
    projection_values = _projection_value_index(facts) if facts is not None else None
    atom_ids: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "atom_id",
            "categories",
            "normalized_value",
            "polarity",
            "custody_state",
            "entailment_relationship",
            "source_span_ids",
            "source_span_refs",
            "projection_links",
        }:
            raise ValueError("ProductCreateTransaction atomic fact custody is malformed")
        atom_id = str(row.get("atom_id") or "")
        if not re.fullmatch(r"AF-[0-9a-f]{16}", atom_id):
            raise ValueError("ProductCreateTransaction atomic fact custody has an invalid atom id")
        atom_ids.append(atom_id)
        _require_categories(row.get("categories"))
        normalized_value = row.get("normalized_value")
        if not isinstance(normalized_value, str) or not normalized_value or len(normalized_value) > MAX_ATOMIC_VALUE_LENGTH:
            raise ValueError("ProductCreateTransaction atomic fact custody has an invalid normalized value")
        polarity = row.get("polarity")
        if polarity not in {"affirmed", "required", "prohibited"}:
            raise ValueError("ProductCreateTransaction atomic fact custody has an invalid polarity")
        if atom_id != _atom_id(normalized_value, polarity=polarity):
            raise ValueError("ProductCreateTransaction atomic fact custody has an invalid atom id")
        _require_atomic_custody(row)
        if source_spans and row.get("custody_state") == "accepted_fact":
            _require_accepted_entailment(row, source_spans=source_spans)
        _require_projection_links(
            row.get("projection_links"),
            categories=row.get("categories"),
            normalized_value=normalized_value,
            projection_values=projection_values,
        )
    if atom_ids != sorted(atom_ids) or len(atom_ids) != len(set(atom_ids)):
        raise ValueError("ProductCreateTransaction atomic fact custody is not deterministic")


def _require_categories(value: Any) -> None:
    if not isinstance(value, list) or not value or value != sorted(set(value)):
        raise ValueError("ProductCreateTransaction atomic fact custody has invalid categories")
    if not set(value) <= set(ATOMIC_FACT_CATEGORIES):
        raise ValueError("ProductCreateTransaction atomic fact custody has invalid categories")


def _require_atomic_custody(row: Mapping[str, Any]) -> None:
    state = row.get("custody_state")
    relationship = row.get("entailment_relationship")
    span_ids = row.get("source_span_ids")
    refs = row.get("source_span_refs")
    if state == "accepted_fact":
        if relationship != "ordered_source_entailment" or not _valid_span_refs(refs, span_ids):
            raise ValueError("ProductCreateTransaction accepted atomic fact lacks source entailment custody")
        return
    expected = {
        "assumption": "visible_assumption_from",
        "bounded_interpretation": "bounded_interpretation_of",
    }.get(str(state or ""))
    if not expected or relationship != expected or span_ids != [] or refs != []:
        raise ValueError("ProductCreateTransaction atomic fact has invalid interpretation custody")


def _require_projection_links(
    value: Any,
    *,
    categories: Any,
    normalized_value: str,
    projection_values: Mapping[tuple[str, str], str] | None,
) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("ProductCreateTransaction atomic fact lacks a canonical projection")
    ordering: list[tuple[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {"field", "path", "value_sha256"}:
            raise ValueError("ProductCreateTransaction atomic fact has an invalid canonical projection")
        field = str(row.get("field") or "")
        path = str(row.get("path") or "")
        if field not in ATOMIC_PROJECTION_FIELDS or not path.startswith(f"/{field}"):
            raise ValueError("ProductCreateTransaction atomic fact has an invalid canonical projection")
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("value_sha256") or "")):
            raise ValueError("ProductCreateTransaction atomic fact has an invalid canonical projection")
        if projection_values is not None:
            projected_value = projection_values.get((field, path))
            if (
                projected_value is None
                or row.get("value_sha256") != _sha256_text(projected_value)
                or _normalized_token_text(projected_value) != _normalized_token_text(normalized_value)
            ):
                raise ValueError("ProductCreateTransaction atomic fact is not bound to its canonical projection")
        ordering.append((field, path))
    if ordering != sorted(set(ordering)):
        raise ValueError("ProductCreateTransaction atomic fact projections are not deterministic")
    linked_fields = {field for field, _path in ordering}
    if any(
        not linked_fields.intersection(ATOMIC_CATEGORY_FIELDS.get(str(category), ()))
        for category in categories
    ):
        raise ValueError("ProductCreateTransaction atomic fact category is not bound to a valid projection")


def _require_accepted_entailment(
    row: Mapping[str, Any],
    *,
    source_spans: Sequence[Mapping[str, Any]],
) -> None:
    spans_by_id = {
        clean_markdown_text(span.get("span_id")): span
        for span in source_spans
        if clean_markdown_text(span.get("span_id"))
    }
    value = str(row.get("normalized_value") or "")
    polarity = str(row.get("polarity") or "")
    refs = row.get("source_span_refs", ())
    linked_fields = {
        str(link.get("field") or "")
        for link in row.get("projection_links", ())
        if isinstance(link, Mapping)
    }
    for span_id, ref in zip(row.get("source_span_ids", ()), refs, strict=True):
        span = spans_by_id.get(str(span_id))
        if span is None:
            raise ValueError("ProductCreateTransaction accepted atomic fact lacks source entailment custody")
        text = clean_markdown_text(span.get("text"))
        text_sha256 = _sha256_text(text)
        if (
            not _is_entailment_source(span)
            or ref.get("classification") != span.get("classification")
            or ref.get("span_id") != span_id
            or ref.get("text_sha256") != text_sha256
            or span.get("text_sha256") != text_sha256
            or not any(_source_polarity(text, field=field) == polarity for field in linked_fields)
            or not _ordered_entailment(source=text, claim=value)
        ):
            raise ValueError("ProductCreateTransaction accepted atomic fact lacks source entailment custody")


def _valid_span_refs(value: Any, span_ids: Any) -> bool:
    if not isinstance(span_ids, list) or not span_ids:
        return False
    if not isinstance(value, list) or not value:
        return False
    actual_ids: list[str] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {"span_id", "classification", "text_sha256"}:
            return False
        span_id = str(row.get("span_id") or "")
        digest = str(row.get("text_sha256") or "")
        if not span_id or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return False
        actual_ids.append(span_id)
    return actual_ids == span_ids and len(actual_ids) == len(set(actual_ids))


def _eligible_source_spans(spans: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    atomic = tuple(
        span
        for span in spans
        if span.get("section_key") == "atomic_evidence" and _is_entailment_source(span)
    )
    if atomic:
        parent_ids = {str(span.get("parent_span_id") or "") for span in atomic}
        eligible = tuple(
            span
            for span in spans
            if _is_entailment_source(span)
            and str(span.get("span_id") or "") not in parent_ids
        )
    else:
        eligible = tuple(span for span in spans if _is_entailment_source(span))
    deduped: list[Mapping[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for span in eligible:
        key = (
            clean_markdown_text(span.get("classification")),
            clean_markdown_text(span.get("text_sha256")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(span)
    return tuple(deduped)


def _entailed_source_refs(
    *,
    value: str,
    polarity: str,
    spans: Sequence[Mapping[str, Any]],
    field: str,
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for span in spans:
        text = clean_markdown_text(span.get("text"))
        if _source_polarity(text, field=field) != polarity or not _ordered_entailment(source=text, claim=value):
            continue
        refs.append(
            {
                "span_id": clean_markdown_text(span.get("span_id")),
                "classification": clean_markdown_text(span.get("classification")),
                "text_sha256": clean_markdown_text(span.get("text_sha256")),
            }
        )
    return refs


def _projection_atoms(
    *,
    field: str,
    value: Any,
    human_actors: Sequence[str] = (),
    first_path: Any = "",
) -> tuple[tuple[str, str], ...]:
    values = confirmed_text_values(value)
    rows: list[tuple[str, str]] = []
    for index, item in enumerate(values):
        path = f"/{field}/{index}" if isinstance(value, Sequence) and not isinstance(value, str) else f"/{field}"
        if field == "human_actors":
            label = item.split(":", 1)[0]
            rows.append((path, label))
            source_actor = clean_markdown_text(actor_signature(first_path)).strip(" .;:")
            if source_actor and label.casefold().endswith(source_actor.casefold()) and label.casefold() != source_actor.casefold():
                rows.append((f"{path}/source_actor", source_actor))
            continue
        if field in {"external_systems", "internal_systems"}:
            rows.append((path, re.split(r"\s+[\u2013\u2014-]\s+|:\s+", item, maxsplit=1)[0]))
            continue
        if field == "state_object":
            match = re.search(
                r"\bprimary\s+state\s+object\s+is\s+(?:(?:a|an|the|one)\s+)?(?P<value>[^.;]+)",
                item,
                flags=re.IGNORECASE,
            )
            rows.append((path, match.group("value") if match else item))
            if transition := _relative_state_transition_atom(item):
                rows.append((f"{path}/transitions/0", transition))
                if transition_range := _state_transition_range_atom(transition):
                    rows.append((f"{path}/transition_ranges/0", transition_range))
            rows.extend(
                (f"{path}/transitions/{unit_index}", transition)
                for unit_index, unit in enumerate(_sentence_units(item)[1:], start=1)
                if (transition := _state_transition_atom(unit))
            )
            continue
        if field == "first_path":
            model = first_path_model(item)
            steps = list(model.steps) or [item]
            seen_values: set[str] = set()
            preserve_action_owners = _has_multiple_action_owners(human_actors)
            for step_index, step in enumerate(steps):
                subject = _typed_actor_prefix(step, human_actors=human_actors)
                action = step if preserve_action_owners or not subject else step[len(subject) :].strip()
                rows.append((f"{path}/steps/{step_index}", action))
                seen_values.add(_normalized_token_text(action))
            visible_outcome = clean_markdown_text(
                visible_result_object(model.visible_outcome) or model.visible_outcome
            ).strip(" .;:")
            visible_outcome_key = _normalized_token_text(visible_outcome)
            if visible_outcome_key and visible_outcome_key not in seen_values:
                rows.append((f"{path}/visible_outcome", visible_outcome))
                seen_values.add(visible_outcome_key)
            sentence_keys = {_normalized_token_text(unit) for unit in _sentence_units(item)}
            for unit_index, unit in enumerate(_source_atomic_units(item, source_section_key="first_path")):
                unit_key = _normalized_token_text(unit)
                if not unit_key or unit_key in seen_values:
                    continue
                if unit_key not in sentence_keys and not first_path_model(unit).material_action:
                    continue
                rows.append((f"{path}/source_units/{unit_index}", unit))
                seen_values.add(unit_key)
            continue
        units = _sentence_units(item)
        rows.extend(
            (f"{path}/units/{unit_index}", _derived_unit_atom(field=field, value=unit))
            for unit_index, unit in enumerate(units)
        )
        if field in {"product_story", "proof_boundary", "success_metrics"}:
            rows.extend(
                (f"{path}/visible_outputs/{unit_index}", output)
                for unit_index, unit in enumerate(units)
                if (output := clean_markdown_text(visible_result_object(unit)).strip(" .;:"))
                and _normalized_token_text(output) != _normalized_token_text(unit)
            )
    return tuple(rows)


def _derived_unit_atom(*, field: str, value: str) -> str:
    if field != "proof_boundary":
        return value
    return derived_proof_boundary_text(value)


def _source_polarity(value: str, *, field: str) -> str:
    semantic_value = _derived_unit_atom(field=field, value=value)
    return _polarity(semantic_value)


def _projection_value_index(facts: Mapping[str, Any]) -> dict[tuple[str, str], str]:
    values: dict[tuple[str, str], str] = {}
    for field in sorted(ATOMIC_PROJECTION_FIELDS):
        if field not in facts:
            continue
        for path, value in _projection_atoms(
            field=field,
            value=facts.get(field),
            human_actors=confirmed_text_values(facts.get("human_actors")),
            first_path=facts.get("first_path"),
        ):
            normalized_value = clean_markdown_text(value).strip(" .;:")
            if normalized_value:
                values[(field, path)] = normalized_value
    return values


def _typed_actor_prefix(value: str, *, human_actors: Sequence[str]) -> str:
    signature = clean_markdown_text(actor_signature(value)).strip(" .;:")
    actor_labels = tuple(
        clean_markdown_text(actor).partition(":")[0].strip(" .;:")
        for actor in human_actors
    )
    if signature and not any(
        label.casefold() == signature.casefold()
        or label.casefold().endswith(f" {signature.casefold()}")
        for label in actor_labels
    ):
        return ""
    candidates = (signature,) if signature else actor_labels
    for candidate in sorted(candidates, key=len, reverse=True):
        match = re.match(
            rf"^(?:a|an|the)?\s*(?P<actor>{re.escape(candidate)})\b",
            clean_markdown_text(value),
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(0).strip()
    return ""


def _has_multiple_action_owners(human_actors: Sequence[str]) -> bool:
    owners = 0
    for row in human_actors:
        _label, separator, responsibility = clean_markdown_text(row).partition(":")
        if not separator:
            continue
        action = re.sub(
            r"^needs\s+the\s+product\s+to\s+|\s+and\s+keep\s+the\s+result\b.*$",
            "",
            responsibility.strip(),
            flags=re.IGNORECASE,
        )
        if re.fullmatch(r"(?:changes?|moves?|transitions?)\s+from\s+.+?\s+to\s+.+", action, re.IGNORECASE):
            continue
        owners += 1
    return owners > 1


def _state_transition_atom(value: str) -> str:
    text = clean_markdown_text(value).strip(" .;:")
    pronoun = re.match(
        r"^(?:it|they|them)\s+(?:changes?|moves?|transitions?)\s+from\s+"
        r"(?P<before>.+?)\s+to\s+(?P<after>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if pronoun:
        return f"{pronoun.group('before')} to {pronoun.group('after')}"
    return text if re.search(r"\b(?:changes?|moves?|transitions?)\s+from\s+.+\s+to\s+", text, flags=re.IGNORECASE) else ""


def _relative_state_transition_atom(value: str) -> str:
    match = re.search(
        r"\bprimary\s+state\s+object\s+is\s+(?:(?:a|an|the|one)\s+)?"
        r"(?P<object>[^.;]+?)\s+that\s+(?P<predicate>(?:changes?|moves?|transitions?)\s+from\s+.+?\s+to\s+[^.;]+)",
        clean_markdown_text(value),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    subject = match.group("object").strip().rsplit(maxsplit=1)[-1]
    return f"{subject} {match.group('predicate').strip()}"


def _state_transition_range_atom(value: str) -> str:
    match = re.search(r"\bfrom\s+(?P<before>.+?)\s+to\s+(?P<after>.+)$", value, flags=re.IGNORECASE)
    return f"{match.group('before')} to {match.group('after')}" if match else ""


def _categories_for_field(field: str) -> tuple[str, ...]:
    return _ATOMIC_FIELD_CATEGORIES.get(field, ())


def _sentence_units(value: str) -> list[str]:
    text = clean_markdown_text(value)
    return [
        unit
        for row in re.split(r"(?<=[.!?])\s+|;\s*", text)
        if (unit := clean_markdown_text(row).strip(" .;:"))
    ]


def atomic_claim_units(value: Any) -> tuple[str, ...]:
    """Return sentence and local clause units for polarity-aware custody."""

    units: list[str] = []
    for sentence in _sentence_units(str(value or "")):
        units.append(sentence)
        shared_predicate, subject_units = _coordinated_subject_units(sentence)
        units.extend(subject_units)
        if shared_predicate:
            continue
        units.extend(
            unit
            for part in re.split(r"[,:]\s*|\s+\band\b\s+", sentence, flags=re.IGNORECASE)
            if (unit := clean_markdown_text(part).strip(" .;:")) and unit != sentence
        )
    return tuple(dict.fromkeys(units))


def _coordinated_subject_units(value: str) -> tuple[bool, tuple[str, ...]]:
    """Preserve each subject in an affirmed shared-predicate declaration."""

    subject, predicate = declaration_subject_predicate(value)
    subjects = coordinated_subjects(subject)
    if len(subjects) < 2:
        return False, ()
    predicate_tokens = {token.casefold() for token in _TOKEN_RE.findall(predicate)}
    if _polarity(value) == "prohibited" or predicate_tokens & {"forbidden", "not", "prohibited"}:
        return True, ()
    return True, subjects


def _source_atomic_units(value: str, *, source_section_key: str) -> list[str]:
    is_operator_evidence = (
        source_section_key.endswith("operator_prompt_evidence")
        or source_section_key.endswith("operator_edit_evidence")
    )
    split_action_clauses = source_section_key == "first_path" or is_operator_evidence
    source_text = without_source_metadata_clauses(value) if is_operator_evidence else value
    sentences = _sentence_units(source_text)
    if not split_action_clauses:
        return sentences
    return list(dict.fromkeys(unit for sentence in sentences for unit in atomic_claim_units(sentence)))


def _is_entailment_source(span: Mapping[str, Any]) -> bool:
    classification = clean_markdown_text(span.get("classification"))
    if classification == "product_claim":
        return True
    source_section_key = clean_markdown_text(
        span.get("source_section_key") or span.get("section_key")
    )
    return classification == "supporting_evidence" and source_section_key.endswith(
        ("operator_prompt_evidence", "operator_edit_evidence")
    )


def _ordered_entailment(*, source: str, claim: str) -> bool:
    source_tokens = _semantic_tokens(source)
    claim_tokens = _semantic_tokens(claim)
    if not claim_tokens or len(claim_tokens) > len(source_tokens):
        return False
    size = len(claim_tokens)
    return any(source_tokens[index : index + size] == claim_tokens for index in range(len(source_tokens) - size + 1))


def _semantic_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        _stem_token(token)
        for token in _TOKEN_RE.findall(value.casefold())
        if token not in _STOPWORDS
    )


def _normalized_token_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(clean_markdown_text(value).casefold()))


def _stem_token(value: str) -> str:
    if len(value) > 5 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 5 and value.endswith("ing"):
        stem = value[:-3]
        return stem[:-1] if len(stem) > 3 and stem[-1:] == stem[-2:-1] else stem
    if len(value) > 4 and value.endswith("ed"):
        stem = value[:-2]
        return stem[:-1] if len(stem) > 3 and stem[-1:] == stem[-2:-1] else stem
    if len(value) > 4 and value.endswith("es") and value[:-2].endswith(("ch", "o", "s", "sh", "x", "z")):
        value = value[:-2]
    elif len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        value = value[:-1]
    if len(value) > 5 and value.endswith("e"):
        return value[:-1]
    return value


def _polarity(value: str) -> str:
    if _PROHIBITED_RE.search(value):
        return "prohibited"
    if _REQUIRED_RE.search(value):
        return "required"
    return "affirmed"


def _atom_id(value: str, *, polarity: str) -> str:
    digest = hashlib.sha256(f"{polarity}\n{_normalized_token_text(value)}".encode("utf-8")).hexdigest()
    return f"AF-{digest[:16]}"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


__all__ = [
    "ATOMIC_CATEGORY_FIELDS",
    "ATOMIC_FACT_CATEGORIES",
    "ATOMIC_FACT_LEDGER_VERSION",
    "ATOMIC_PROJECTION_FIELDS",
    "append_atomic_source_spans",
    "atomic_claim_units",
    "atomic_fact_ledger_hash",
    "build_atomic_fact_ledger",
    "require_atomic_fact_ledger",
]
