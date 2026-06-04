"""Generic artifact-term extraction for greenfield component contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_terms import ROLEISH_TERMS
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_term_index import ordered_domain_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_text, unique_text

ACTION_VERBS = (
    "accept",
    "adjust",
    "apply",
    "approve",
    "assemble",
    "assign",
    "block",
    "build",
    "calculate",
    "capture",
    "choose",
    "compare",
    "complete",
    "compute",
    "connect",
    "create",
    "delete",
    "derive",
    "describe",
    "display",
    "edit",
    "explain",
    "export",
    "find",
    "grant",
    "group",
    "guide",
    "handoff",
    "handle",
    "highlight",
    "import",
    "inspect",
    "keep",
    "link",
    "leave",
    "log",
    "make",
    "maintain",
    "manage",
    "notify",
    "open",
    "order",
    "pair",
    "persist",
    "present",
    "prepare",
    "provide",
    "produce",
    "publish",
    "rank",
    "read",
    "receive",
    "record",
    "render",
    "request",
    "resolve",
    "respond",
    "review",
    "route",
    "save",
    "schedule",
    "score",
    "see",
    "select",
    "send",
    "show",
    "store",
    "submit",
    "summarize",
    "sync",
    "track",
    "validate",
    "verify",
    "view",
)

GENERIC_TERMS = {
    "accepted",
    "actor",
    "application",
    "boundary",
    "both",
    "candidate",
    "component",
    "contract",
    "domain",
    "evidence",
    "explicit",
    "explicitly",
    "first",
    "greenfield",
    "hand",
    "handoff",
    "help",
    "input",
    "later",
    "least",
    "local",
    "only",
    "off",
    "output",
    "path",
    "planned",
    "product",
    "project",
    "proof",
    "record",
    "release",
    "reviewer",
    "service",
    "single",
    "source",
    "state",
    "system",
    "validation",
    "made",
    "mistake",
    "person",
    "proven",
    "succeed",
    "success",
    "their",
    "they",
    "today",
    "with",
    "what",
    "whether",
    "working",
    "from",
    "into",
    "then",
}

ARTIFACT_CARRIER_TERMS = {
    "alternative",
    "alternatives",
    "answer",
    "answers",
    "assignment",
    "assignments",
    "blocker",
    "blockers",
    "confirmation",
    "confirmations",
    "criteria",
    "context",
    "decision",
    "description",
    "descriptions",
    "detail",
    "details",
    "evidence",
    "field",
    "fields",
    "flag",
    "flags",
    "form",
    "forms",
    "guardrail",
    "guardrails",
    "history",
    "input",
    "inputs",
    "journal",
    "journals",
    "ledger",
    "list",
    "lists",
    "marker",
    "markers",
    "metric",
    "metrics",
    "measurement",
    "note",
    "notes",
    "outcome",
    "outcomes",
    "output",
    "outputs",
    "option",
    "options",
    "package",
    "packet",
    "preference",
    "preferences",
    "rationale",
    "record",
    "records",
    "request",
    "result",
    "review",
    "reviews",
    "rule",
    "rubric",
    "rubrics",
    "score",
    "signal",
    "state",
    "status",
    "summary",
    "timeline",
    "unit",
    "units",
    "version",
    "versioning",
    "view",
    "visit",
    "visits",
}

NOUN_MODIFIER_ACTION_TERMS = {"review"}


def clean_artifact_phrases(values: Sequence[str]) -> list[str]:
    return unique_text(phrase for phrase in (clean_artifact_phrase(value) for value in values) if phrase)


def clean_artifact_phrase(value: str) -> str:
    text = trim_phrase(value).casefold()
    if not text:
        return ""
    text = _clean_visible_phrase_debris(text)
    text = _normalize_misplaced_artifact_modifiers(text)
    action_pattern = action_forms_pattern()
    text = re.sub(rf"^(?:[a-z0-9-]+\s+){{0,4}}can\s+(?:{action_pattern})\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:related path|failure avoided|relevant behavior)\s*:\s*.+$", "", text, flags=re.I)
    text = re.sub(r"\busing\s+(?:mocked|stubbed|simulated)\b.*$", "", text, flags=re.I)
    text = re.sub(r"\b(?:before|after|while|because|unless|without)\b.+$", "", text, flags=re.I)
    text = re.sub(r"^(?:release\s+)?good\s+enough\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:accepted|confirmed|needed|received|requested|trusted|visible)\b", "", text, flags=re.I)
    text = re.sub(r"\bkeep(?:s|ing)?\s+", "", text, flags=re.I)
    text = re.sub(r"\bexplicit(?:ly)?\b", "", text, flags=re.I)
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.I)
    leading_modifiers = "validated|candidate|selected|ranked|authorized"
    if "completeness" not in text:
        leading_modifiers = f"required|{leading_modifiers}"
    text = re.sub(rf"^(?:{leading_modifiers})\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:central|core|main|primary)\s+", "", text, flags=re.I)
    words = text.split()
    preserve_modifier = bool(
        len(words) >= 2 and words[0].casefold().endswith("ing") and words[1].casefold() in ARTIFACT_CARRIER_TERMS
    ) or bool(
        len(words) >= 2
        and words[0].casefold() in NOUN_MODIFIER_ACTION_TERMS
        and words[1].casefold() in ARTIFACT_CARRIER_TERMS
    )
    if not preserve_modifier:
        text = strip_action(text)
    text = re.sub(r"^[a-z0-9][a-z0-9 -]{0,80}\s+owns\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:and\s+)?keeps?\s+the\s+next\s+visible\s+step\s+tied\s+to\s*:\s*.+$", "next-step context", text, flags=re.I)
    text = re.sub(r"\btied\s+to\s*:\s*.+$", "", text, flags=re.I)
    text = re.sub(r"^(?:hold|holds|holding)\s+", "", text, flags=re.I)
    text = re.sub(
        r"\bhold\s+(?=(?:profile|record|state|history|log|entry|session|trip|event|timeline|measurement|metric|reading)\b)",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"^(?:them|it|their|they|this|that)\s+(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:them|it|their|they|this|that)\b", "", text, flags=re.I)
    text = re.sub(r"\bhas\s+enough\s+[a-z0-9-]+\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" .,;:")
    text = re.sub(
        r"\b(?:accepted|confirmed|needed|received|requested|trusted|visible)\b$",
        "",
        text,
        flags=re.I,
    ).strip(" .,;:")
    if not text:
        return ""
    lowered = text.casefold()
    if re.search(r"\b(?:runs?|evaluates?|checks?|computes?|returns?|produces?|captures?|validates?)\s+(?:it|them|their|they)\b", lowered):
        return ""
    if re.search(r"\b(?:gives?|runs?|evaluates?|checks?)\s+(?:it|them|their|they)\b", lowered):
        return ""
    if lowered in {
        "authorized actor",
        "blocker state",
        "blocked states",
        "handoff evidence",
        "local blockers",
        "prior result",
        "prior state",
        "source evidence",
        "validation command",
        "validation context",
        "validation notes",
    }:
        return lowered
    if lowered in GENERIC_TERMS:
        return ""
    if lowered in {"action", "actions", "user action", "user actions"}:
        return ""
    words = text.split()
    if len(words) > 8:
        return ""
    if len(words) == 1 and words[0] not in ARTIFACT_CARRIER_TERMS and words[0] != "blocker":
        return ""
    if set(words) & ARTIFACT_CARRIER_TERMS:
        keep_role_qualified_artifact = (
            2 <= len(words) <= 4
            and words[0].casefold() in ROLEISH_TERMS
            and words[-1].casefold() in ARTIFACT_CARRIER_TERMS
            and words[-1].casefold() not in {"action", "actions", "input", "inputs"}
            and (
                len(words) == 2
                or any(word.casefold() not in ROLEISH_TERMS and word.casefold() not in ARTIFACT_CARRIER_TERMS for word in words[1:-1])
            )
        )
        if not keep_role_qualified_artifact:
            words = [
                word
                for word in words
                if word.casefold() not in ROLEISH_TERMS and word.casefold() not in {"enough", "next"}
            ]
        text = " ".join(words).strip(" .,;:")
        text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.I)
        words = text.split()
        lowered = text.casefold()
        if not text:
            return ""
    if any(word.casefold() in ROLEISH_TERMS for word in words) and any(
        word.casefold() in {"action", "actions"} for word in words
    ):
        return ""
    if "enough" in {word.casefold() for word in words} and not (set(words) & ARTIFACT_CARRIER_TERMS):
        return ""
    if len(words) >= 3 and looks_actor_term(words[0]) and looks_action_form(words[1]):
        text = " ".join(words[2:]).strip(" .,;:")
        text = strip_action(text)
        words = text.split()
        lowered = text.casefold()
        if not text or text in GENERIC_TERMS:
            return ""
    if not content_terms(text):
        return ""
    action_hits = [
        word
        for word in re.findall(r"[a-z0-9]+", lowered)
        if looks_action_form(word) and word not in ARTIFACT_CARRIER_TERMS
    ]
    if action_hits and not (set(words) & ARTIFACT_CARRIER_TERMS):
        return ""
    return text


def _clean_visible_phrase_debris(value: str) -> str:
    text = clean_text(value).casefold()
    text = re.sub(r"^on\s+save,\s*", "", text, flags=re.I)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.I)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.I)
    text = re.sub(r"\balongside\b", "with", text, flags=re.I)
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.I)
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.I)
    text = re.sub(
        r"\s+and\s+the\s+(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        " and the ",
        text,
        flags=re.I,
    )
    text = re.sub(r"\b(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?", "", text, flags=re.I)
    text = re.sub(
        r"\bdashboard\s+visibly\s+updates?\s+(?P<object>[a-z0-9][a-z0-9 '-]{1,50})\b",
        r"\g<object> state",
        text,
        flags=re.I,
    )
    text = re.sub(r"\b(?P<object>[a-z0-9][a-z0-9 '-]{1,50})\s+visible\s+result\b", r"\g<object>", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" .,;:")


def _normalize_misplaced_artifact_modifiers(value: str) -> str:
    """Repair parser-order debris before it becomes a contract artifact."""

    text = clean_text(value).casefold().strip(" .,;:")
    if not text:
        return ""
    required = re.match(r"^[a-z0-9-]+\s+required\s+(?P<object>[a-z0-9][a-z0-9 '-]{1,80})$", text, flags=re.I)
    if required:
        text = f"required {required.group('object')}"
    missing = re.match(r"^[a-z0-9-]+\s+missing\s+(?P<object>[a-z0-9][a-z0-9 '-]{1,80})$", text, flags=re.I)
    if missing:
        missing_object = trim_phrase(missing.group("object"))
        if missing_object and not set(missing_object.split()) & ARTIFACT_CARRIER_TERMS:
            missing_object = f"{missing_object} detail"
        text = f"missing {missing_object}".strip()
    return re.sub(r"\s+", " ", text).strip(" .,;:")


def descriptor_anchor_phrases(label: str, description: str) -> list[str]:
    base = label_object_base(label)
    if not base:
        return []
    rows: list[str] = []
    base_terms = set(content_terms(base))
    for clause in clauses(description):
        phrase = trim_phrase(strip_action(object_clause_focus(clause))).casefold()
        phrase = re.sub(r"\b(?:before|after|while|because|unless|without)\b.+$", "", phrase, flags=re.I)
        phrase = re.sub(r"^(?:required|validated|candidate|selected|ranked|authorized)\s+", "", phrase, flags=re.I)
        terms = content_terms(phrase)
        if not terms or len(terms) > 3:
            continue
        if set(terms) & base_terms:
            continue
        if set(terms) & ARTIFACT_CARRIER_TERMS:
            continue
        if any(looks_action_term(term) for term in terms):
            continue
        rows.append(f"{base} {' '.join(terms)}")
    return unique_text(rows[:5])


def action_object_artifact_phrases(description: str) -> list[str]:
    rows: list[str] = []
    action_nouns = {
        "attach": "attachment",
        "block": "blocking",
        "capture": "capture",
        "create": "creation",
        "protect": "protection",
        "validate": "validation",
    }
    for clause in clauses(description):
        text = trim_phrase(clause).casefold()
        if not text:
            continue
        match = re.match(
            rf"(?P<action>{'|'.join(verb_forms_pattern(action) for action in action_nouns)})\s+(?P<object>.+)$",
            text,
            flags=re.I,
        )
        if not match:
            continue
        action = canonical_action(match.group("action"), action_nouns)
        artifact_noun = action_nouns.get(action, "")
        if not artifact_noun:
            continue
        object_text = trim_phrase(match.group("object"))
        missing_match = re.match(r"missing\s+(?:required\s+)?(?P<object>.+)$", object_text, flags=re.I)
        object_text = re.sub(r"\b(?:before|after|while|because|unless|without|and)\b.+$", "", object_text, flags=re.I)
        object_text = re.sub(r"^(?:missing\s+)?", "", object_text, flags=re.I).strip()
        object_text = singularize_last_word(object_text)
        if not object_text or len(object_text.split()) > 5 or not content_terms(object_text):
            continue
        if missing_match and artifact_noun == "blocking":
            missing_object = singularize_last_word(trim_phrase(missing_match.group("object")))
            missing_object = documentish_noun(missing_object)
            if missing_object and len(missing_object.split()) <= 4 and content_terms(missing_object):
                rows.append(f"missing {missing_object} blocking")
        if action == "protect" and "sensitive" in set(content_terms(object_text)):
            rows.append("sensitive access control")
        rows.append(f"{object_text} {artifact_noun}")
        required_match = re.search(r"\brequired\s+(?P<object>[a-z0-9][a-z0-9 -]{1,60})", clause, flags=re.I)
        if required_match:
            required_object = singularize_last_word(trim_phrase(required_match.group("object")))
            if required_object and len(required_object.split()) <= 4 and content_terms(required_object):
                rows.append(f"required {required_object} completeness")
    return unique_text(rows[:12])


def local_terms(label: str, description: str, proposal_context: str, object_phrases: Sequence[str]) -> list[str]:
    return unique_text(
        term
        for term in ordered_domain_terms(" ".join([label, description, proposal_context, *object_phrases]))
        if term not in GENERIC_TERMS and not term.isdigit()
    )


_OWNED_ARTIFACT_TERMS = {
    "case",
    "choice",
    "decision",
    "entry",
    "event",
    "finding",
    "item",
    "measurement",
    "note",
    "outcome",
    "record",
    "request",
    "result",
    "signal",
    "snapshot",
    "summary",
    "view",
}

_OWNED_ENRICHMENT_SKIP_RE = re.compile(
    r"\b(?:blocked-state|command|correction\s+marker|handoff\s+record|prior\s+state|"
    r"replayable\s+change\s+evidence|reviewer\s+explanation|validation\s+context)\b",
    re.IGNORECASE,
)


def enrich_owned_state_from_io(
    owned_state: Any,
    fields: Mapping[str, Any],
    *,
    noise_terms: set[str],
) -> str:
    """Keep material product artifacts in ownership, not only in IO lists."""

    owned_clauses = split_contract_clauses(owned_state)
    owned_terms = set(domain_terms(" ".join(owned_clauses), noise_terms=noise_terms))
    additions: list[str] = []
    for key in ("accepted_inputs", "produced_outputs"):
        for clause in split_contract_clauses(fields.get(key)):
            candidate = clean(re.sub(r"^(?:required|validated)\s+", "", clause, flags=re.IGNORECASE)).strip(" .")
            if not candidate or _OWNED_ENRICHMENT_SKIP_RE.search(candidate):
                continue
            terms = domain_terms(candidate, noise_terms=noise_terms)
            if len(terms) < 2:
                continue
            if not (set(terms) & _OWNED_ARTIFACT_TERMS):
                continue
            if len(set(terms) - owned_terms) < 1:
                continue
            additions.append(candidate)
            owned_terms.update(terms)
            if len(additions) >= 2:
                break
        if len(additions) >= 2:
            break
    return phrase([*owned_clauses, *additions])


def split_contract_clauses(value: Any) -> list[str]:
    return [
        cleaned
        for part in re.split(r",\s*(?=(?:and\s+)?[a-z0-9])", clean(value))
        if (cleaned := clean(re.sub(r"^(?:and|or)\s+", "", part, flags=re.IGNORECASE)).strip(" ."))
    ]


def domain_terms(value: Any, *, noise_terms: set[str]) -> list[str]:
    return [
        term
        for term in ordered_domain_terms(clean(value))
        if term not in noise_terms and not term.isdigit()
    ]


def phrase(values: Sequence[str]) -> str:
    return ", ".join(clean(value) for value in unique_text(values) if clean(value))


def natural_phrase(values: Sequence[str]) -> str:
    rows = [clean(value) for value in values if clean(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def term_phrase(values: Sequence[str]) -> str:
    return " ".join(clean(value) for value in values if clean(value))


def content_terms(value: str) -> list[str]:
    return unique_text(term for term in ordered_domain_terms(value) if term not in GENERIC_TERMS and not term.isdigit())


def phrase_identity_terms(value: str) -> set[str]:
    stopwords = GENERIC_TERMS - ARTIFACT_CARRIER_TERMS
    return set(ordered_terms(clean(value), stopwords=stopwords))


def strip_action(value: str) -> str:
    return clean(re.sub(rf"^(?:{action_forms_pattern()})\s+", "", value, flags=re.I))


def object_clause_focus(value: str) -> str:
    text = clean(value)
    if not text:
        return ""
    text = re.sub(r"\bhand(?:s|ed|ing)?\s+off\b", "handoff", text, flags=re.I)
    if re.search(r"\bor\b", text, flags=re.I):
        return text
    action_pattern = action_forms_pattern()
    article_subject = re.match(
        rf"^(?:a|an|the|one)\s+(?:[a-z][a-z0-9_-]*\s+){{1,5}}?(?:(?:can|must|should|will|may)\s+)?(?P<action>{action_pattern})\b(?P<tail>.*)$",
        text,
        flags=re.I,
    )
    if article_subject:
        return f"{article_subject.group('action')}{article_subject.group('tail')}"
    bare_subject = re.match(
        rf"^(?:[a-z][a-z0-9_-]*\s+){{1,4}}(?:(?:can|must|should|will|may)\s+)?(?P<action>{action_pattern})\b(?P<tail>.*)$",
        text,
        flags=re.I,
    )
    if bare_subject and len(content_terms(text[: bare_subject.start("action")])) <= 3:
        return f"{bare_subject.group('action')}{bare_subject.group('tail')}"
    return text


def looks_action_term(value: str) -> bool:
    token = str(value or "").casefold()
    if token in ACTION_VERBS:
        return True
    return token in _past_action_terms()


def looks_action_form(value: str) -> bool:
    token = str(value or "").casefold()
    return token in _action_form_set()


@lru_cache(maxsize=1)
def _action_form_set() -> frozenset[str]:
    return frozenset(form for verb in ACTION_VERBS for form in verb_forms(verb))


@lru_cache(maxsize=1)
def _past_action_terms() -> frozenset[str]:
    return frozenset(past_tense(verb) for verb in ACTION_VERBS)


@lru_cache(maxsize=1)
def action_forms_pattern() -> str:
    return "|".join(re.escape(form) for form in sorted(_action_form_set(), key=lambda value: (-len(value), value)))


@lru_cache(maxsize=128)
def verb_forms_pattern(verb: str) -> str:
    return "|".join(re.escape(form) for form in sorted(verb_forms(verb), key=lambda value: (-len(value), value)))


@lru_cache(maxsize=128)
def verb_forms(verb: str) -> frozenset[str]:
    forms = {verb, f"{verb}s", f"{verb}es", f"{verb}ed", f"{verb}ing"}
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in {"a", "e", "i", "o", "u"}:
        stem = verb[:-1]
        forms.update({f"{stem}ies", f"{stem}ied"})
    if verb.endswith("e") and len(verb) > 1:
        stem = verb[:-1]
        forms.update({f"{verb}d", f"{stem}ing"})
    return frozenset(forms)


def trim_phrase(value: str) -> str:
    text = clean(value).strip(" .,;:")
    text = re.sub(r"\b(?:so|because|before|after|while)\b.+$", "", text, flags=re.I)
    text = re.sub(r"^(?:a|an|the|one)\s+", "", text, flags=re.I)
    words = text.split()
    while words and words[-1].casefold() in {"a", "an", "and", "for", "from", "of", "or", "the", "to", "with"}:
        words.pop()
    return " ".join(words)


def clauses(value: str) -> list[str]:
    text = clean(value)
    if not text:
        return []
    parts = re.split(r"[.;]\s+|\s+[—-]\s+|\s*,\s+(?=(?:and\s+)?(?:[a-z]+\s+){0,2}[a-z]+(?:s|es|ed|ing)?\b)", text)
    return [
        trim_phrase(re.sub(r"^(?:and|or|the|a|an)\s+", "", part, flags=re.I))
        for part in parts
        if trim_phrase(part)
    ]


def canonical_action(value: str, action_nouns: Mapping[str, str]) -> str:
    token = str(value or "").casefold()
    for action in action_nouns:
        if token in verb_forms(action):
            return action
    return token


def singularize_last_word(value: str) -> str:
    words = trim_phrase(value).split()
    if not words:
        return ""
    if len(words[-1]) > 3 and words[-1].endswith("ies"):
        words[-1] = f"{words[-1][:-3]}y"
    elif len(words[-1]) > 3 and words[-1].endswith("s") and not words[-1].endswith("ss"):
        words[-1] = words[-1][:-1]
    return " ".join(words)


def documentish_noun(value: str) -> str:
    words = trim_phrase(value).split()
    if not words:
        return ""
    if words[-1].casefold() == "documentation":
        words[-1] = "document"
    return " ".join(words)


def label_object_base(label: str) -> str:
    terms = [
        term
        for term in content_terms(label)
        if term not in {"adapter", "client", "engine", "service", "surface", "system", "viewer"}
    ]
    if len(terms) < 2:
        return ""
    for index, term in enumerate(terms):
        if term in ARTIFACT_CARRIER_TERMS and index > 0:
            return " ".join(terms[index - 1 : index + 1])
    return " ".join(terms[:2])


def past_tense(value: str) -> str:
    verb = str(value or "").casefold()
    if verb == "choose":
        return "chosen"
    if verb == "leave":
        return "left"
    if verb == "log":
        return "logged"
    if verb == "make":
        return "made"
    if verb == "submit":
        return "submitted"
    if verb.endswith("e"):
        return f"{verb}d"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in {"a", "e", "i", "o", "u"}:
        return f"{verb[:-1]}ied"
    return f"{verb}ed"


def clean(value: Any) -> str:
    text = clean_text(value).replace("`", "").replace("(", " ").replace(")", " ")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "ACTION_VERBS",
    "ARTIFACT_CARRIER_TERMS",
    "GENERIC_TERMS",
    "action_forms_pattern",
    "action_object_artifact_phrases",
    "clean_artifact_phrase",
    "clean_artifact_phrases",
    "content_terms",
    "descriptor_anchor_phrases",
    "domain_terms",
    "enrich_owned_state_from_io",
    "local_terms",
    "looks_action_form",
    "looks_action_term",
    "looks_actor_term",
    "natural_phrase",
    "object_clause_focus",
    "phrase",
    "phrase_identity_terms",
    "split_contract_clauses",
    "strip_action",
    "term_phrase",
    "trim_phrase",
    "verb_forms_pattern",
]
