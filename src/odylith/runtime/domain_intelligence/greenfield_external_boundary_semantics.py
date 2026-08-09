"""Typed external-boundary facts for confirmed greenfield intent."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import action_token_form
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import coordinated_subjects
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import declaration_subject_predicate
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
        "gauge",
        "gauges",
        "gateway",
        "gateways",
        "import",
        "imports",
        "ledger",
        "ledgers",
        "laboratory",
        "laboratories",
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
        "portal",
        "portals",
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
_LEXEME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9&'/_-]*")
_FROM_ACTIONS = frozenset(
    "came come comes get gets import imported imports load loaded loads provide provided provides read reads "
    "receive receives retrieve retrieved retrieves source sourced sources supplied supplies".split()
)
_SUPPLIER_ACTIONS = frozenset("feeds flags provides publishes reports sends supplies".split())
_DIRECT_SOURCE_ACTIONS = frozenset(
    "check checking checks consult consults cross-reference cross-references ingest ingesting ingests query queries "
    "read reads reference references use uses using".split()
)
_DEPENDENCY_ACTIONS = frozenset({"depend", "depends", "rely", "relies"})
_COMPARISON_ACTIONS = frozenset(
    "check checking checks compare compares comparing correlate correlates correlating cross-reference "
    "cross-references match matches matching".split()
)
_CO_VARIATION_ACTIONS = frozenset({"change", "changes", "changing", "vary", "varies", "varying"})
_RECIPIENT_ACTIONS = frozenset(
    "collect collects collecting deliver delivers delivering route routes routing send sends sending submit submits "
    "submitting upload uploads uploading".split()
)
_SOURCE_PREPOSITIONS = frozenset({"through", "using", "via"})
_SOURCE_PREPOSITION_ACTIONS = {
    "against": _COMPARISON_ACTIONS,
    "for": _RECIPIENT_ACTIONS,
    "from": _FROM_ACTIONS,
    "on": _DEPENDENCY_ACTIONS,
    "to": _RECIPIENT_ACTIONS,
    "with": _COMPARISON_ACTIONS | _CO_VARIATION_ACTIONS,
}
_ARTIFACT_SOURCE_CARRIERS = frozenset(
    "dataset datasets document documents file files form forms import imports log logs message messages record records "
    "report reports source sources submission submissions transcript transcripts upload uploads".split()
)
_DIRECT_BOUNDARY_CARRIERS = _SOURCE_LABEL_CARRIERS - _ARTIFACT_SOURCE_CARRIERS


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


def source_boundary_rows_from_evidence(
    value: Any,
    *,
    excluded_labels: Sequence[str] = (),
) -> list[str]:
    """Extract named external sources without copying surrounding prompt prose."""

    rows, is_structured = _structured_source_rows(value)
    text = clean_text(value)
    if text and not is_structured:
        rows.extend(_dependency_frame_sources(text))
    excluded = {_boundary_key(label) for label in excluded_labels if _boundary_key(label)}
    normalized = [_source_label(row) for row in rows]
    return list(unique_text(row for row in normalized if row and _boundary_key(row) not in excluded))[:8]


def is_external_dependency_clause(value: Any) -> bool:
    """Return whether one non-human clause states only an external dependency."""

    text = clean_text(value).strip(" .")
    tokens = _LEXEME_RE.findall(text)
    lowered = [token.casefold() for token in tokens]
    model = first_path_model(text)
    if not tokens or len(model.steps) > 1:
        return False
    if _declared_external_sources(text):
        return True
    if _external_supplier_only_clause(text):
        return True
    for index, token in enumerate(lowered[:-1]):
        if token not in _DEPENDENCY_ACTIONS or lowered[index + 1] != "on":
            continue
        subject = " ".join(tokens[:index]).strip()
        source = _source_object(tokens, start=index + 2)
        prior_action = any(action_token_form(word) for word in tokens[:index])
        purpose_action = any(
            lowered[purpose_index] == "to" and action_token_form(tokens[purpose_index + 1])
            for purpose_index in range(index + 2, len(tokens) - 1)
        )
        if subject and source and not prior_action and not purpose_action and not has_human_actor_signal(subject):
            return True
    return False


def _external_supplier_only_clause(value: str) -> bool:
    tokens = _LEXEME_RE.findall(value)
    for index, token in enumerate(tokens):
        if token.casefold() not in _SUPPLIER_ACTIONS:
            continue
        if any(action_token_form(following) for following in tokens[index + 1 :]):
            continue
        subject = _supplier_subject(tokens[:index])
        if subject and not has_human_actor_role_signal(subject) and _source_label(subject):
            return True
    return False


def _dependency_frame_sources(value: str) -> list[str]:
    rows: list[str] = []
    text = clean_text(value)
    for sentence in re.split(r"[.;!?\n]+", text):
        rows.extend(_declared_external_sources(sentence))
    for clause in re.split(r"[,.;:!?\n]+", text):
        tokens = _LEXEME_RE.findall(clause)
        lowered = [token.casefold() for token in tokens]
        if not tokens or lowered[0] in {"if", "unless", "when", "while"}:
            continue
        for index, token in enumerate(lowered):
            if token in _SUPPLIER_ACTIONS:
                rows.append(_supplier_subject(tokens[:index]))
            if token in _SOURCE_PREPOSITIONS:
                candidate = _source_object(tokens, start=index + 1)
                if _system_boundary_candidate(candidate):
                    rows.append(candidate)
            prior_actions = set(lowered[max(0, index - 8) : index])
            required_actions = _SOURCE_PREPOSITION_ACTIONS.get(token, frozenset())
            if required_actions and prior_actions & required_actions:
                candidate = _source_object(tokens, start=index + 1)
                if token not in {"against", "with"} or _system_boundary_candidate(candidate):
                    rows.append(candidate)
            if token in _DIRECT_SOURCE_ACTIONS and (index + 1 >= len(tokens) or lowered[index + 1] != "from"):
                candidate = _source_object(tokens, start=index + 1, stop_at_source_relation=True)
                if _system_boundary_candidate(candidate):
                    rows.append(candidate)
    return [row for row in rows if row]


def _declared_external_sources(value: str) -> list[str]:
    """Read explicit ``<name> is/are external source/system`` declarations."""

    subject, predicate_text = declaration_subject_predicate(value)
    subject_tokens = {token.casefold() for token in _LEXEME_RE.findall(subject)}
    predicate = {token.casefold() for token in _LEXEME_RE.findall(predicate_text)}
    if not subject or {"no", "neither", "nor"} & subject_tokens:
        return []
    if {"forbidden", "never", "not", "prohibited", "without"} & predicate:
        return []
    if "external" not in predicate or not predicate & {"source", "sources", "system", "systems"}:
        return []
    return _declared_source_labels(subject)


def _declared_source_labels(value: str) -> list[str]:
    labels = [_source_label(subject, explicit=True) for subject in coordinated_subjects(value)]
    return [label for label in labels if label and not has_human_actor_signal(label)]


def _supplier_subject(tokens: Sequence[str]) -> str:
    subject = _source_subject(tokens)
    if any(action_token_form(token) for token in _LEXEME_RE.findall(subject)):
        return ""
    return subject


def _source_subject(tokens: Sequence[str]) -> str:
    start = 0
    for index, token in enumerate(tokens):
        if token.casefold() in {"and", "but", "then"} and any(
            action_token_form(prior) for prior in tokens[:index]
        ):
            start = index + 1
    while start < len(tokens) and tokens[start].casefold() in {"a", "an", "and", "but", "the", "then"}:
        start += 1
    return " ".join(tokens[start:])


def _source_object(
    tokens: Sequence[str],
    *,
    start: int,
    stop_at_source_relation: bool = False,
) -> str:
    while start < len(tokens) and tokens[start].casefold() in {"a", "an", "the"}:
        start += 1
    selected = list(tokens[start:])
    if stop_at_source_relation:
        for index, token in enumerate(selected):
            if token.casefold() in _SOURCE_PREPOSITION_ACTIONS or token.casefold() in _SOURCE_PREPOSITIONS:
                selected = selected[:index]
                break
    for index, token in enumerate(selected):
        if token.casefold() in {"and", "but", "then"} and any(
            action_token_form(following) for following in selected[index + 1 :]
        ):
            selected = selected[:index]
            break
    carrier_indexes = [
        index for index, token in enumerate(selected) if token.casefold() in _DIRECT_BOUNDARY_CARRIERS
    ]
    return " ".join(selected[: carrier_indexes[-1] + 1]) if carrier_indexes else " ".join(selected)


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


def _source_label(value: Any, *, explicit: bool = False) -> str:
    text = clean_text(value).strip(" .,:;\"'")
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    words = text.split()
    if not words or len(words) > 12:
        return ""
    lowered = {word.casefold().strip(".,;:()[]{}") for word in words}
    if lowered <= _NON_SYSTEM_SOURCE_LABELS:
        return ""
    if not explicit and not (
        lowered & _SOURCE_LABEL_CARRIERS
        or any(word.isupper() and len(word) >= 2 for word in words)
        or any(word[:1].isupper() for word in words)
    ):
        return ""
    return " ".join(words)


def _boundary_key(value: Any) -> str:
    return " ".join(_LEXEME_RE.findall(clean_text(value).casefold()))


def _system_boundary_candidate(value: Any) -> bool:
    return bool({word.casefold() for word in _LEXEME_RE.findall(clean_text(value))} & _DIRECT_BOUNDARY_CARRIERS)


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
    "is_external_dependency_clause",
    "source_boundary_rows_from_evidence",
]
