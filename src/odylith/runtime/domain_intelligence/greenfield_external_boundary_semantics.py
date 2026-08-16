"""Typed external-boundary facts for confirmed greenfield intent."""

from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import action_token_form
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import coordinated_subjects
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import authoritative_prompt_evidence_text
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import declaration_subject_predicate
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import is_discarded_evidence_clause
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_fields import prompt_field_values
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
_EXTERNAL_FIELD_NAMES = (
    "external system",
    "external systems",
    "upstream system",
    "upstream systems",
    "dependency",
    "dependencies",
    "data source",
    "data sources",
    "source",
    "sources",
    "system",
    "systems",
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
        "relay",
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
_EXPLICIT_DEPENDENCY_COMMAND_RE = re.compile(
    r"^(?:also\s+)?(?:(?:depend|rely)\s+on\s+|(?:read|use)\s+(?:only\s+from\s+|from\s+)?)"
    r"(?:a\s+|an\s+|the\s+)?"
    r"(?P<label>[^.;!?]+)$",
    flags=re.IGNORECASE,
)
_SOLE_DEPENDENCY_RE = re.compile(
    r"^(?:(?:keep|use)\s+(?:a\s+|an\s+|the\s+)?(?P<label>[^.;!?]+?)\s+as|"
    r"(?:a\s+|an\s+|the\s+)?(?P<declared_label>[^.;!?]+?)\s+is)\s+"
    r"(?:the\s+)?(?:only|sole)\s+dependency$",
    flags=re.IGNORECASE,
)
_READ_ONLY_SOURCE_RE = re.compile(
    r"^(?:a\s+|an\s+|the\s+)?(?P<label>[^.;!?]{2,120}?)\s+is\s+read[- ]only$",
    flags=re.IGNORECASE,
)
_JSON_DEPENDENCY_FIELD_RE = re.compile(
    r'"(?:dependency|dependencies|data_source|data_sources|external_system|external_systems)"\s*:\s*"(?P<label>[^"\\]+)"',
    flags=re.IGNORECASE,
)
_GENERIC_DEPENDENCY_SUBJECTS = frozenset(
    {"app", "application", "product", "report", "reports", "service", "system", "tool", "workspace"}
)


@dataclass(frozen=True)
class ExternalBoundaryFact:
    """One inferred boundary fact from accepted intent semantics."""

    label: str
    evidence: str
    confidence: str
    question: str = ""

    @property
    def row(self) -> str:
        return f"{self.label} - supplies accepted first-path input before the product changes state."

    @property
    def ambiguity(self) -> str:
        if self.question:
            return self.question
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

    return [
        fact.label
        for fact in source_boundary_facts_from_evidence(value, excluded_labels=excluded_labels)
        if fact.confidence == "source"
    ][:8]


def source_boundary_facts_from_evidence(
    value: Any,
    *,
    excluded_labels: Sequence[str] = (),
) -> list[ExternalBoundaryFact]:
    """Return source-backed boundaries and unresolved named-location hypotheses."""

    text = str(value or "")
    final_text = authoritative_prompt_evidence_text(text)
    facts = _boundary_facts_from_text(final_text)
    if final_text != text.strip() and not facts:
        facts = _boundary_facts_from_text(text)
    excluded = {_boundary_key(label) for label in excluded_labels if _boundary_key(label)}
    return [fact for fact in _unique_facts(facts) if _boundary_key(fact.label) not in excluded][:8]


def _boundary_facts_from_text(text: str) -> list[ExternalBoundaryFact]:
    facts = [
        ExternalBoundaryFact(label=label, evidence=clean_text(row), confidence="source")
        for row in prompt_field_values(text, names=_EXTERNAL_FIELD_NAMES)
        if (label := _source_label(_bounded_dependency_text(row)))
    ]
    facts.extend(_dependency_frame_facts(text))
    return _unique_facts(facts)


def is_external_dependency_clause(value: Any) -> bool:
    """Return whether one non-human clause states only an external dependency."""

    text = clean_text(value).strip(" .")
    tokens = _LEXEME_RE.findall(text)
    lowered = [token.casefold() for token in tokens]
    model = first_path_model(text)
    if not tokens or len(model.steps) > 1:
        return False
    declarations = _explicit_dependency_declarations(text)
    if declarations and not any(has_workflow_tail for _label, has_workflow_tail in declarations):
        return True
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
    return [fact.label for fact in _dependency_frame_facts(value) if fact.confidence == "source"]


def _dependency_frame_facts(value: str) -> list[ExternalBoundaryFact]:
    facts = [
        ExternalBoundaryFact(label=label, evidence=clean_text(value), confidence="source")
        for label in _explicit_dependency_labels(value)
    ]
    text = str(value or "")
    for sentence in re.split(r"[.;!?\n]+", text):
        if is_discarded_evidence_clause(sentence):
            continue
        facts.extend(_source_facts(_declared_external_sources(sentence), evidence=sentence))
    for clause in re.split(r"[,.;:!?\n]+", text):
        if is_discarded_evidence_clause(clause):
            continue
        tokens = _LEXEME_RE.findall(clause)
        lowered = [token.casefold() for token in tokens]
        if not tokens or lowered[0] in {"if", "unless", "when", "while"}:
            continue
        for index, token in enumerate(lowered):
            if token in _SUPPLIER_ACTIONS:
                facts.extend(_source_facts((_supplier_subject(tokens[:index]),), evidence=clause))
            if token in _SOURCE_PREPOSITIONS:
                candidate = _source_object(tokens, start=index + 1)
                if _system_boundary_candidate(candidate):
                    facts.extend(_source_facts((candidate,), evidence=clause))
            if token == "in":
                candidate = _source_object(tokens, start=index + 1)
                if _in_scopes_dependency_system(lowered, index=index):
                    facts.extend(_source_facts((candidate,), evidence=clause))
                elif _named_in_system_boundary_candidate(candidate):
                    facts.extend(_source_facts((candidate,), evidence=clause))
                elif (label := _source_label(candidate)) and not has_human_actor_signal(label):
                    facts.append(
                        ExternalBoundaryFact(
                            label=label,
                            evidence=clean_text(clause),
                            confidence="ambiguous",
                            question=(
                                f"Is {label} an external system required by the first path, or is it a location "
                                "or product-owned label?"
                            ),
                        )
                    )
            if token == "from":
                if _from_starts_state_transition(lowered, start=index + 1):
                    continue
                candidate = _source_object(tokens, start=index + 1)
                if _named_system_boundary_candidate(candidate):
                    facts.extend(_source_facts((candidate,), evidence=clause))
            prior_actions = set(lowered[max(0, index - 8) : index])
            required_actions = _SOURCE_PREPOSITION_ACTIONS.get(token, frozenset())
            if required_actions and prior_actions & required_actions:
                candidate = _source_object(tokens, start=index + 1)
                if token not in {"against", "with"} or _system_boundary_candidate(candidate):
                    facts.extend(_source_facts((candidate,), evidence=clause))
            if token in _DIRECT_SOURCE_ACTIONS and (index + 1 >= len(tokens) or lowered[index + 1] != "from"):
                candidate = _source_object(tokens, start=index + 1, stop_at_source_relation=True)
                if _system_boundary_candidate(candidate):
                    facts.extend(_source_facts((candidate,), evidence=clause))
    return _unique_facts(facts)


def _explicit_dependency_labels(value: str) -> tuple[str, ...]:
    """Recover bounded noun phrases from explicit dependency grammar."""

    return tuple(label for label, _has_workflow_tail in _explicit_dependency_declarations(value))


def _explicit_dependency_declarations(value: str) -> tuple[tuple[str, bool], ...]:
    declarations: dict[str, bool] = {}
    text = str(value or "")
    for raw in re.split(r"[.!?\n]+", text):
        clause = clean_text(raw).strip(" .")
        if not clause or is_discarded_evidence_clause(clause):
            continue
        clause = re.sub(r"^(?:correction|edit|final\s+edit)\s*:\s*", "", clause, flags=re.IGNORECASE)
        clause = clause.partition(",")[0]
        command = _SOLE_DEPENDENCY_RE.match(clause) or _EXPLICIT_DEPENDENCY_COMMAND_RE.match(clause)
        read_only = _READ_ONLY_SOURCE_RE.match(clause)
        candidate = (
            command.groupdict().get("label") or command.groupdict().get("declared_label", "")
            if command
            else read_only.group("label") if read_only else ""
        )
        candidate, has_workflow_tail = _dependency_label_and_workflow_tail(candidate)
        if label := _explicit_dependency_label(candidate):
            declarations[label] = declarations.get(label, False) or has_workflow_tail
    for match in _JSON_DEPENDENCY_FIELD_RE.finditer(text):
        if label := _explicit_dependency_label(match.group("label")):
            declarations.setdefault(label, False)
    return tuple(declarations.items())


def _dependency_label_and_workflow_tail(value: str) -> tuple[str, bool]:
    text = clean_text(value).strip(" .,:;")
    words = tuple(_LEXEME_RE.finditer(text))
    for index, word in enumerate(words[:-1]):
        if word.group(0).casefold() == "to" and action_token_form(words[index + 1].group(0)):
            return text[: word.start()].strip(" .,:;"), True
    return text, False


def _explicit_dependency_label(value: Any) -> str:
    text = _bounded_dependency_text(value)
    words = _LEXEME_RE.findall(text)
    lowered = {word.casefold() for word in words}
    if not 1 <= len(words) <= 12:
        return ""
    if len(words) == 1 and not _source_label(text):
        return ""
    if has_human_actor_signal(text) or lowered <= _NON_SYSTEM_SOURCE_LABELS:
        return ""
    if words[0].casefold() in _GENERIC_DEPENDENCY_SUBJECTS:
        return ""
    return text


def _bounded_dependency_text(value: Any) -> str:
    text = clean_text(value).strip(" .,:;\"'")
    text = re.split(
        r"\s+as\s+(?:the\s+)?(?:only|sole)\s+dependency\b|\s+for\s+|\s*;",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .,:;\"'")
    return re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)


def _in_scopes_dependency_system(tokens: Sequence[str], *, index: int) -> bool:
    """Treat ``in <name>`` as sourced when it qualifies an explicit dependency."""

    dependency_index = next(
        (position for position in range(index - 1, -1, -1) if tokens[position] in _DEPENDENCY_ACTIONS),
        -1,
    )
    return bool(
        dependency_index >= 0
        and "on" in tokens[dependency_index + 1 : index]
    )


def _source_facts(values: Sequence[str], *, evidence: str) -> list[ExternalBoundaryFact]:
    return [
        ExternalBoundaryFact(label=label, evidence=clean_text(evidence), confidence="source")
        for value in values
        if (label := _source_label(value))
    ]


def _from_starts_state_transition(tokens: Sequence[str], *, start: int) -> bool:
    tail = list(tokens[start:])
    to_index = next((index for index, token in enumerate(tail) if token == "to"), -1)
    if to_index < 0:
        return False
    carrier_index = next(
        (index for index, token in enumerate(tail) if token in _DIRECT_BOUNDARY_CARRIERS),
        -1,
    )
    return carrier_index < 0 or to_index < carrier_index


def _declared_external_sources(value: str) -> list[str]:
    """Read explicit external-system and named-source declarations."""

    subject, predicate_text = declaration_subject_predicate(value)
    subject_tokens = {token.casefold() for token in _LEXEME_RE.findall(subject)}
    predicate = {token.casefold() for token in _LEXEME_RE.findall(predicate_text)}
    if not subject or {"no", "neither", "nor"} & subject_tokens:
        return []
    if {"forbidden", "never", "not", "prohibited", "without"} & predicate:
        return []
    if "external" in predicate and predicate & {"source", "sources", "system", "systems"}:
        return _declared_source_labels(subject)
    if "source" in predicate and predicate & {"for", "of"} and "truth" not in predicate:
        label = _source_label(subject, explicit=True)
        if label and _system_boundary_candidate(label) and not has_human_actor_signal(label):
            return [label]
    return []


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


def _named_system_boundary_candidate(value: Any) -> bool:
    label = _source_label(value)
    if not label or has_human_actor_signal(label):
        return False
    words = _LEXEME_RE.findall(label)
    return _system_boundary_candidate(label) or any(
        word.isupper() or any(character.isupper() for character in word[1:])
        for word in words
        if len(word) >= 2
    )


def _named_in_system_boundary_candidate(value: Any) -> bool:
    """Require a system-bearing name before treating ``in`` as a dependency relation."""

    label = _source_label(value)
    if not label or has_human_actor_signal(label):
        return False
    return bool(set(_identifier_terms(label)) & _DIRECT_BOUNDARY_CARRIERS)


def _identifier_terms(value: str) -> tuple[str, ...]:
    terms: list[str] = []
    for token in _LEXEME_RE.findall(clean_text(value)):
        for segment in re.split(r"[/_-]+", token):
            terms.extend(
                part.casefold()
                for part in re.findall(r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+", segment)
            )
    return tuple(terms)


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
    result: dict[str, ExternalBoundaryFact] = {}
    for fact in facts:
        key = fact.label.casefold()
        if not key:
            continue
        wider = next((known for known in result if f" {key} " in f" {known} "), "")
        if wider:
            continue
        narrower = next((known for known in result if f" {known} " in f" {key} "), "")
        if narrower:
            result.pop(narrower)
        current = result.get(key)
        if current is None or (current.confidence != "source" and fact.confidence == "source"):
            result[key] = fact
    return list(result.values())


__all__ = [
    "ExternalBoundaryFact",
    "completed_external_boundary_rows",
    "external_boundary_facts",
    "is_external_dependency_clause",
    "source_boundary_facts_from_evidence",
    "source_boundary_rows_from_evidence",
]
