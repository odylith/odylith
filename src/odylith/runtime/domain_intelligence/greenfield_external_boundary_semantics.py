"""Typed external-boundary facts for confirmed greenfield intent."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


_INPUT_ACTIONS = frozenset(
    {
        "add",
        "attach",
        "capture",
        "collect",
        "connect",
        "enter",
        "import",
        "ingest",
        "load",
        "provide",
        "receive",
        "record",
        "select",
        "submit",
        "sync",
        "upload",
    }
)
_SOURCE_CARRIERS = frozenset(
    {
        "api",
        "apis",
        "dataset",
        "datasets",
        "document",
        "documents",
        "feed",
        "feeds",
        "file",
        "files",
        "form",
        "forms",
        "import",
        "imports",
        "ledger",
        "ledgers",
        "log",
        "logs",
        "message",
        "messages",
        "record",
        "records",
        "report",
        "reports",
        "sensor",
        "sensors",
        "source",
        "sources",
        "submission",
        "submissions",
        "transcript",
        "transcripts",
        "upload",
        "uploads",
    }
)
_AMBIGUOUS_INPUT_CARRIERS = frozenset(
    {
        "constraint",
        "constraints",
        "limit",
        "limits",
        "need",
        "needs",
        "policy",
        "policies",
        "preference",
        "preferences",
        "requirement",
        "requirements",
        "rule",
        "rules",
    }
)
_BOUNDARY_STOPWORDS = frozenset(
    {
        "accepted",
        "actor",
        "before",
        "boundary",
        "current",
        "first",
        "input",
        "path",
        "product",
        "proof",
        "source",
        "state",
        "system",
        "user",
    }
)
_STRUCTURED_SOURCE_KEYS = frozenset(
    {
        "data_source",
        "data_sources",
        "external_system",
        "external_systems",
        "source",
        "sources",
        "upstream_system",
        "upstream_systems",
    }
)
_SOURCE_LABEL_CARRIERS = _SOURCE_CARRIERS | frozenset(
    {
        "archive",
        "calendar",
        "catalog",
        "database",
        "directory",
        "gazette",
        "index",
        "map",
        "provider",
        "registry",
        "repository",
        "roster",
        "service",
        "shelf",
        "system",
    }
)
_NON_SYSTEM_SOURCE_LABELS = frozenset(
    {
        "customer",
        "customers",
        "database",
        "interview",
        "interviews",
        "notes",
        "operator",
        "operators",
        "people",
        "product",
        "requirements",
        "service",
        "source",
        "staff",
        "system",
        "team",
        "teams",
        "tool",
        "user",
        "users",
    }
)
_TRAILING_SOURCE_ACTION_RE = re.compile(
    r"\s+\band\s+(?:can(?:not|'t)?|cannot|displays?|is|are|shows?|shown|uses?|used|was|were)\b.*$",
    flags=re.IGNORECASE,
)
_FROM_SOURCE_RE = re.compile(
    r"\b(?:come|comes|came|read|reads|loaded|loads|imported|imports|retrieved|retrieves|"
    r"sourced|sources|provided|provides|supplied|supplies)\s+from\s+(?:the\s+)?(?P<source>[^,.;!?\n]+)",
    flags=re.IGNORECASE,
)
_ACTION_FROM_SOURCE_RE = re.compile(
    r"\b(?:imports?|loads?|reads?|retrieves?|sources?)\b[^,.;!?\n]{1,100}?\bfrom\s+"
    r"(?:the\s+)?(?P<source>[^,.;!?\n]+)",
    flags=re.IGNORECASE,
)
_SUPPLIER_RE = re.compile(
    r"^(?:the\s+)?(?P<source>[A-Za-z0-9][A-Za-z0-9&'/_-]*(?:\s+[A-Za-z0-9][A-Za-z0-9&'/_-]*){0,7})"
    r"\s+(?:feeds|provides|publishes|supplies)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ExternalBoundaryFact:
    """One inferred boundary fact from accepted intent semantics."""

    label: str
    evidence: str
    confidence: str

    @property
    def row(self) -> str:
        return f"{self.label} - supplies accepted first-path input before the product changes state."

    @property
    def ambiguity(self) -> str:
        return (
            f"Whether {self.label[:1].lower()}{self.label[1:]} is manually entered or supplied by an "
            "external source for the accepted first path."
        )


def completed_external_boundary_rows(intent: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Return external rows and ambiguity rows derived from accepted first-path facts."""

    explicit_rows = confirmed_text_values(intent.get("external_systems"))
    if explicit_rows:
        return explicit_rows, []

    first_path = clean_text(intent.get("first_path"))
    if not first_path:
        return [], []

    facts = external_boundary_facts(first_path)
    external_rows = [fact.row for fact in facts if fact.confidence == "source"]
    ambiguity_rows = [fact.ambiguity for fact in facts if fact.confidence == "ambiguous"]
    return list(unique_text(external_rows))[:4], list(unique_text(ambiguity_rows))[:4]


def source_boundary_rows_from_evidence(value: Any) -> list[str]:
    """Extract named external sources without copying surrounding prompt prose."""

    rows, is_structured = _structured_source_rows(value)
    text = clean_text(value)
    if text and not is_structured:
        rows.extend(match.group("source") for match in _FROM_SOURCE_RE.finditer(text))
        rows.extend(match.group("source") for match in _ACTION_FROM_SOURCE_RE.finditer(text))
        for sentence in re.split(r"[.;!?]+", text):
            match = _SUPPLIER_RE.match(clean_text(sentence))
            if match:
                rows.append(match.group("source"))
    normalized = [_source_label(row) for row in rows]
    return list(unique_text(row for row in normalized if row))[:8]


def _structured_source_rows(value: Any) -> tuple[list[str], bool]:
    if not isinstance(value, str):
        return [], False
    text = value.strip()
    if not text.startswith(("{", "[")):
        return [], False
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return [], False
    rows: list[str] = []
    _collect_structured_source_rows(payload, rows)
    return rows, True


def _collect_structured_source_rows(value: Any, rows: list[str], *, key: str = "") -> None:
    if isinstance(value, Mapping):
        for item_key, item in value.items():
            _collect_structured_source_rows(item, rows, key=str(item_key).casefold())
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _collect_structured_source_rows(item, rows, key=key)
        return
    if key in _STRUCTURED_SOURCE_KEYS:
        text = clean_text(value)
        if text:
            rows.append(text)


def _source_label(value: Any) -> str:
    text = clean_text(value).strip(" .,:;\"'")
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    text = _TRAILING_SOURCE_ACTION_RE.sub("", text).strip(" .,:;\"'")
    text = re.split(r"\s+\b(?:although|before|but|unless|while)\b\s+", text, maxsplit=1, flags=re.IGNORECASE)[0]
    words = text.split()
    if not words or len(words) > 12:
        return ""
    lowered = {word.casefold().strip(".,;:()[]{}") for word in words}
    if lowered <= _NON_SYSTEM_SOURCE_LABELS:
        return ""
    if not (
        lowered & _SOURCE_LABEL_CARRIERS
        or any(word.isupper() and len(word) >= 2 for word in words)
        or any(word[:1].isupper() for word in words)
    ):
        return ""
    return " ".join(words)


def external_boundary_facts(first_path: Any) -> list[ExternalBoundaryFact]:
    """Infer input-source boundary facts from typed first-path steps."""

    model = first_path_model(first_path)
    facts: list[ExternalBoundaryFact] = []
    for step in model.steps:
        body = _input_body(step)
        if not body:
            continue
        for segment in _input_segments(body):
            label = _boundary_label(segment)
            if not label:
                continue
            terms = {term.casefold() for term in label_terms(label, stopwords=_BOUNDARY_STOPWORDS)}
            if terms & _SOURCE_CARRIERS:
                facts.append(ExternalBoundaryFact(label=label, evidence=clean_text(step), confidence="source"))
            elif terms & _AMBIGUOUS_INPUT_CARRIERS:
                facts.append(ExternalBoundaryFact(label=label, evidence=clean_text(step), confidence="ambiguous"))
    return _unique_facts(facts)


def _input_body(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    words = text.split()
    lowered = [word.strip(".,;:()[]{}").casefold() for word in words]
    for index, token in enumerate(lowered):
        base = token[:-1] if token.endswith("s") and len(token) > 4 else token
        if token in _INPUT_ACTIONS or base in _INPUT_ACTIONS:
            body = " ".join(words[index + 1 :]).strip(" .,;:")
            return _drop_terminal_outcome_clause(body)
    return ""


def _drop_terminal_outcome_clause(value: str) -> str:
    text = clean_text(value).strip(" .,;:")
    if not text:
        return ""
    parts = re.split(r"\s+\bthen\b\s+", text, maxsplit=1, flags=re.IGNORECASE)
    return parts[0].strip(" .,;:")


def _input_segments(value: str) -> list[str]:
    rows = [
        row.strip(" .,;:")
        for row in re.split(r"\s*,\s*|\s+\band\b\s+", clean_text(value), flags=re.IGNORECASE)
        if row.strip(" .,;:")
    ]
    return [row for row in rows if len(label_terms(row, stopwords=_BOUNDARY_STOPWORDS)) >= 2]


def _boundary_label(value: str) -> str:
    text = clean_text(value).strip(" .,;:")
    if not text:
        return ""
    text = re.sub(r"^(?:and|or)\s+", "", text, flags=re.IGNORECASE).strip(" .,;:")
    text = re.sub(r"^(?:a|an|the|their|this|that|these|those)\s+", "", text, flags=re.IGNORECASE)
    if _starts_with_action_tail(text):
        return ""
    words = text.split()
    if len(words) > 8:
        return ""
    return text[:1].upper() + text[1:]


def _starts_with_action_tail(value: str) -> bool:
    first = clean_text(value).split(maxsplit=1)[0].strip(".,;:").casefold() if clean_text(value) else ""
    return first in {"and", "or", "then", "publish", "show", "review", "return", "create", "update"}


def _unique_facts(facts: Sequence[ExternalBoundaryFact]) -> list[ExternalBoundaryFact]:
    result: list[ExternalBoundaryFact] = []
    seen: set[str] = set()
    for fact in facts:
        key = fact.label.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)
    return result


__all__ = [
    "ExternalBoundaryFact",
    "completed_external_boundary_rows",
    "external_boundary_facts",
    "source_boundary_rows_from_evidence",
]
