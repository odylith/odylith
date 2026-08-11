"""Generic artifact-term extraction for greenfield component contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_finite_action, looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_terms import ROLEISH_TERMS
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_term_constants import ACTION_VERBS
from odylith.runtime.domain_intelligence.greenfield_component_term_constants import ARTIFACT_CARRIER_TERMS
from odylith.runtime.domain_intelligence.greenfield_component_term_constants import GENERIC_TERMS
from odylith.runtime.domain_intelligence.greenfield_component_term_index import ordered_domain_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import normalize_artifact_tail
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import singularize_last_word
from odylith.runtime.domain_intelligence.greenfield_relative_clause_artifacts import normalize_relative_clause_artifacts
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text, clean_text, normalize_visible_result_language, unique_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words
from odylith.runtime.domain_intelligence.greenfield_transfer_phrases import transfer_object_phrase

NOUN_MODIFIER_ACTION_TERMS = {"check", "review"}
COMPONENT_SHELL_TERMS = frozenset({"adapter", "client", "engine", "service", "surface", "system", "viewer"})
RELATION_TAIL_TERMS = {
    "after", "against", "because", "before", "by", "for", "from", "into", "plus",
    "through", "to", "unless", "until", "using", "when", "while", "with", "without",
}


def clean_artifact_phrases(values: Sequence[str]) -> list[str]:
    return unique_text(phrase for phrase in (clean_artifact_phrase(value) for value in values) if phrase)


def clean_artifact_phrase(value: str) -> str:
    text = trim_phrase(value).casefold()
    if not text:
        return ""
    text = _clean_visible_phrase_debris(text)
    text = transfer_object_phrase(text) or text
    text = _normalize_fragmented_artifact_phrase(text)
    text = _normalize_misplaced_artifact_modifiers(text)
    if re.fullmatch(r"pass\s+or\s+block\s+outcomes?", text, flags=re.I):
        return text
    action_pattern = action_forms_pattern()
    text = re.sub(rf"^(?:[a-z0-9-]+\s+){{0,4}}can\s+(?:{action_pattern})\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:related path|failure avoided|relevant behavior)\s*:\s*.+$", "", text, flags=re.I)
    text = re.sub(r"\busing\s+(?:mocked|stubbed|simulated)\b.*$", "", text, flags=re.I)
    text = re.sub(r"\b(?:before|after|while|because|unless|without)\b.+$", "", text, flags=re.I)
    text = re.sub(r"^(?:release\s+)?good\s+enough\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:accepted|confirmed|needed|received|requested|trusted)\b", "", text, flags=re.I)
    text = re.sub(r"\s+for\s+(?:the\s+)?first\s+path\b.*$", "", text, flags=re.I)
    text = re.sub(
        r"\bvisible\b(?!\s+(?:blockers?|evidence|outcomes?|results?|state|status|summaries|summary|timelines?|views?)\b)",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\bkeep(?:s|ing)?\s+", "", text, flags=re.I)
    text = re.sub(r"\bexplicit(?:ly)?\b", "", text, flags=re.I)
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.I)
    leading_modifiers = "validated|candidate|selected|ranked|authorized"
    if "completeness" not in text:
        leading_modifiers = f"required|{leading_modifiers}"
    text = re.sub(rf"^(?:{leading_modifiers})\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:central|core|main|primary)\s+", "", text, flags=re.I)
    words = text.split()
    if words and words[-1] == "command" and _qualified_boundary_artifact(" ".join(words[:-1])):
        words = words[:-1]
        text = " ".join(words)
    preserve_modifier = bool(
        len(words) >= 2 and words[0].casefold().endswith("ing") and words[1].casefold() in ARTIFACT_CARRIER_TERMS
    ) or bool(
        len(words) >= 2
        and words[0].casefold() in NOUN_MODIFIER_ACTION_TERMS
        and words[1].casefold() in ARTIFACT_CARRIER_TERMS
    ) or bool(
        len(words) >= 2
        and words[0].casefold() == "handoff"
        and words[-1].casefold() in {"boundary", "boundaries"}
    ) or bool(
        len(words) >= 4
        and words[1].casefold() == "or"
        and words[-1].casefold() in ARTIFACT_CARRIER_TERMS
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
    text = _normalize_fragmented_artifact_phrase(text)
    text = _normalize_misplaced_artifact_modifiers(text)
    text = _drop_misplaced_action_modifier_before_carrier(text)
    text = _trim_relation_window(text)
    text = normalize_artifact_tail(text, carrier_terms=ARTIFACT_CARRIER_TERMS)
    if not _qualified_boundary_artifact(text):
        text = _strip_relation_tail(text)
    text = re.sub(
        r"\b(?:accepted|confirmed|needed|received|requested|trusted|visible)\b$",
        "",
        text,
        flags=re.I,
    ).strip(" .,;:")
    if not text:
        return ""
    lowered = text.casefold()
    if _abstract_label_residue_fragment(lowered):
        return ""
    if re.search(r"\bstays?\s+outside\b", lowered):
        return ""
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
    if _looks_like_long_command_noun_pile(words):
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
    action_index = _actor_led_action_index(words)
    if action_index is not None:
        text = " ".join(words[action_index + 1 :]).strip(" .,;:")
        text = strip_action(text)
        words = text.split()
        lowered = text.casefold()
        if not text or text in GENERIC_TERMS:
            return ""
    role_stripped = _strip_leading_artifact_role(text)
    if role_stripped != text:
        text = role_stripped
        words = text.split()
        lowered = text.casefold()
        if not text or text in GENERIC_TERMS:
            return ""
    if not content_terms(text) and not _qualified_boundary_artifact(text):
        return ""
    action_hits = [
        word
        for word in visible_words(lowered)
        if looks_action_form(word) and word not in ARTIFACT_CARRIER_TERMS
    ]
    if action_hits and not (set(words) & ARTIFACT_CARRIER_TERMS):
        return ""
    return text


def _strip_relation_tail(value: str) -> str:
    words = clean_text(value).split()
    while words and words[-1].casefold().strip(".,;:") in RELATION_TAIL_TERMS:
        words.pop()
    return " ".join(words).strip(" .,;:")


def _abstract_label_residue_fragment(value: str) -> bool:
    words = [word.casefold() for word in visible_words(value) if word[:1].isalpha()]
    abstract = {"approval", "approvals", "gate", "gates", "name", "result", "status", "story"}
    return len(words) >= 3 and all(word in abstract for word in words)


def _qualified_boundary_artifact(value: str) -> bool:
    words = [word.casefold().strip(".,;:") for word in visible_words(value) if word.strip(".,;:")]
    return len(words) >= 2 and words[-1] in {"boundary", "boundaries"}


def _looks_like_long_command_noun_pile(words: Sequence[str]) -> bool:
    if len(words) <= 3 or words[-1].casefold().strip(".,;:") != "command":
        return False
    return not any(looks_action_form(word) for word in words[:-1])


def _actor_led_action_index(words: Sequence[str]) -> int | None:
    for index in range(1, min(len(words), 6)):
        actor_prefix = " ".join(words[:index])
        candidate = " ".join(words[index:])
        if (looks_actor_term(words[index - 1]) or looks_actor_term(actor_prefix)) and (
            looks_action_form(words[index]) or looks_like_finite_action(candidate)
        ):
            return index
    return None


def _strip_leading_artifact_role(value: str) -> str:
    text = clean_text(value).casefold().strip(" .,;:")
    words = text.split()
    if len(words) < 2:
        return text
    qualifiers = {"active", "current", "example", "individual", "primary", "representative", "sample", "selected"}
    index = 0
    while index < len(words) - 1 and words[index] in qualifiers:
        index += 1
    candidate = ""
    if 0 < index < len(words) - 1 and words[index] in ROLEISH_TERMS:
        candidate = " ".join(words[index + 1 :]).strip(" .,;:")
    return candidate if candidate and content_terms(candidate) and not looks_like_finite_action(candidate) else text


def _normalize_fragmented_artifact_phrase(value: str) -> str:
    text = clean_text(value).casefold().strip(" .,;:")
    if not text:
        return ""
    text = normalize_relative_clause_artifacts(text)
    text = re.sub(r"\bdata\s+such(?:\s+as)?\b", "data", text, flags=re.I)
    text = re.sub(r"\bsuch(?:\s+as)?\b", "", text, flags=re.I)
    text = re.sub(r"\bdescriptions?\s+mechanisms?\b", "descriptions", text, flags=re.I)
    text = re.sub(r"\bmechanisms?\s+typical\b", "typical", text, flags=re.I)
    text = re.sub(r"\bvalues?\s+relevant\s+conditions?\b", "relevant condition", text, flags=re.I)
    text = re.sub(r"\bconditions?\s+context\s+justified\b", "condition context", text, flags=re.I)
    if re.search(
        r"\b(?:out\s+of\s+scope|outside\s+(?:the\s+)?(?:first\s+)?scope|future\s+scope|later\s+wave|not\s+claimed|do\s+not\s+claim)\b",
        text,
        flags=re.I,
    ):
        return ""
    words = text.split()
    for index, word in enumerate(words[:-2]):
        if word in {"metric", "metrics"} and words[index + 1] in {"changed", "moved", "trended"}:
            context = [row for row in words[index + 2 :] if row not in {"against", "for", "that", "the", "this", "with"}]
            if context:
                text = f"{' '.join(context)} metric"
            break
    text = re.sub(r"\bmoved\s+(?=[a-z0-9])", "", text, flags=re.I)
    text = re.sub(r"\bcombines?\s+(?=reference|range|ranges|data|input|inputs)\b", "", text, flags=re.I)
    text = re.sub(r"\bnormalize\s+(?=[a-z0-9])", "normalized ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" .,;:")


def _clean_visible_phrase_debris(value: str) -> str:
    text = clean_text(value).casefold()
    text = normalize_visible_result_language(text)
    text = re.sub(r"^on\s+save,\s*", "", text, flags=re.I)
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.I)
    text = re.sub(r"\s+as\s+(?:a|the)\s+visible\s+result\b.*$", "", text, flags=re.I)
    text = re.sub(
        r"\s+and\s+the\s+(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        " and the ",
        text,
        flags=re.I,
    )
    text = re.sub(r"\b(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?", "", text, flags=re.I)
    text = re.sub(
        r"\bdashboard\s+visibly\s+updates?\s+(?P<object>[a-z0-9][a-z0-9 '/-]{1,50})\b",
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
    words = text.split()
    if len(words) >= 3 and words[-1] == "next" and words[-2] in ARTIFACT_CARRIER_TERMS:
        text = " ".join([words[-1], *words[:-1]])
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


def _drop_misplaced_action_modifier_before_carrier(value: str) -> str:
    """Remove action-window debris when a verb landed before an artifact carrier."""

    words = clean_text(value).casefold().strip(" .,;:").split()
    if len(words) < 2:
        return " ".join(words)
    if _qualified_boundary_artifact(" ".join(words)):
        return " ".join(words)
    carriers = {index for index, word in enumerate(words) if word in ARTIFACT_CARRIER_TERMS}
    if not carriers:
        return " ".join(words)
    kept: list[str] = []
    for index, word in enumerate(words):
        later_carriers = {words[carrier_index] for carrier_index in carriers if carrier_index > index}
        if word in {"move", "moves", "moved", "moving"} and later_carriers == {"state"}:
            kept.append(word)
            continue
        next_word = words[index + 1] if index + 1 < len(words) else ""
        noun_modifier = (
            word in ARTIFACT_CARRIER_TERMS
            or any(word in verb_forms(term) for term in NOUN_MODIFIER_ACTION_TERMS)
            or word.endswith("ing")
        ) and next_word in ARTIFACT_CARRIER_TERMS
        actor_led_action = bool(
            kept
            and (looks_actor_term(kept[-1]) or looks_actor_term(" ".join(kept)))
        )
        if looks_action_form(word) and later_carriers and not noun_modifier and not actor_led_action:
            continue
        kept.append(word)
    return " ".join(kept).strip(" .,;:")


def _trim_relation_window(value: str) -> str:
    words = clean_text(value).casefold().strip(" .,;:").split()
    if len(words) < 3:
        return " ".join(words)
    relation_terms = {"after", "before", "because", "through", "unless", "until", "using", "when", "while", "without"}
    for index, word in enumerate(words):
        if word not in relation_terms:
            continue
        left = words[:index]
        right = words[index + 1 :]
        if not _relation_window_has_action_debris(left, right):
            continue
        if left:
            return " ".join(left).strip(" .,;:")
        return " ".join(right).strip(" .,;:")
    return " ".join(words).strip(" .,;:")


def _relation_window_has_action_debris(left: Sequence[str], right: Sequence[str]) -> bool:
    if not right:
        return any(looks_action_form(word) for word in left)
    if not left:
        return any(looks_action_form(word) for word in right)
    return any(looks_action_form(word) for word in (*left[-2:], *right[:2]))


def descriptor_anchor_phrases(label: str, description: str) -> list[str]:
    base = label_object_base(label)
    if not base:
        return []
    description_clauses = clauses(description)
    rows: list[str] = []
    base_terms = set(content_terms(base))
    if len(set(content_terms(label)) - base_terms) >= 2:
        return []
    base_words = {word.casefold() for word in visible_words(base)}
    label_words = [word.casefold() for word in visible_words(label) if word.casefold() not in COMPONENT_SHELL_TERMS]
    if looks_action_form(base.split()[0]) and label_words and looks_action_form(label_words[-1]):
        return []
    for clause in description_clauses:
        phrase = trim_phrase(strip_action(object_clause_focus(clause))).casefold()
        phrase = re.sub(r"\b(?:before|after|while|because|unless|without)\b.+$", "", phrase, flags=re.I)
        phrase = re.sub(r"^(?:required|validated|candidate|selected|ranked|authorized)\s+", "", phrase, flags=re.I)
        terms = content_terms(phrase)
        if not terms or len(terms) > 3:
            continue
        if len(terms) == 1 and terms[0] not in ARTIFACT_CARRIER_TERMS:
            continue
        if set(terms) & base_terms:
            continue
        if base_words & {word.casefold() for word in visible_words(phrase)}:
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


def split_contract_clauses(value: Any) -> list[str]:
    return [
        cleaned
        for part in re.split(r"\s*;\s*|,\s*(?=(?:and\s+)?[a-z0-9])", clean(value))
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
    boundary_terms = {"boundary", "boundaries"}
    return unique_text(
        term
        for term in ordered_domain_terms(value)
        if (term not in GENERIC_TERMS or term in boundary_terms) and not term.isdigit()
    )


def phrase_identity_terms(value: str) -> set[str]:
    stopwords = GENERIC_TERMS - ARTIFACT_CARRIER_TERMS
    return set(ordered_terms(clean(value), stopwords=stopwords))


def drop_subsumed_singletons(values: Sequence[str]) -> list[str]:
    identities = [(value, phrase_identity_terms(value)) for value in values]
    result: list[str] = []
    for value, terms in identities:
        if value.casefold() == "source evidence" or (terms == {"boundary"} and len(value.split()) >= 2):
            result.append(value)
            continue
        if len(terms) == 1 and any(terms < other for candidate, other in identities if candidate != value):
            continue
        if terms & {"incomplete", "missing", "recent", "unavailable"} and any(
            terms < other for candidate, other in identities if candidate != value
        ):
            continue
        result.append(value)
    return result


def strip_action(value: str) -> str:
    return clean(re.sub(rf"^(?:{action_forms_pattern()})\s+", "", value, flags=re.I))


def finite_action_clause(value: str) -> tuple[str, bool]:
    _actor, actor_action = actor_led_action_parts(value)
    if actor_action:
        return actor_action, True
    words = value.split()
    candidates = [index for index, word in enumerate(words) if looks_like_finite_action_token(word)]
    if len(candidates) == 1:
        return " ".join(words[candidates[0] :]), True
    transfer_candidates = [
        index
        for index in candidates
        if transfer_object_phrase(" ".join(words[index:]))
    ]
    if len(transfer_candidates) == 1:
        return " ".join(words[transfer_candidates[0] :]), True
    if candidates and candidates[0] == 0:
        return value, True
    return value, False


def finite_action_object_clause(value: str) -> tuple[str, bool]:
    action_clause, owns_action = finite_action_clause(value)
    if not owns_action:
        return value, False
    words = action_clause.split()
    return transfer_object_phrase(action_clause) or " ".join(words[1:]), True


def object_clause_focus(value: str) -> str:
    text = clean(value)
    if not text:
        return ""
    transfer_object = transfer_object_phrase(text)
    if transfer_object:
        return transfer_object
    text = re.sub(r"\bhand(?:s|ed|ing)?\s+off\b", "handoff", text, flags=re.I)
    if re.search(r"\bor\b", text, flags=re.I):
        return text
    action_pattern = action_forms_pattern()
    article_subject = re.match(
        rf"^(?:a|an|the|one)\s+(?:[a-z][a-z0-9_-]*\s+){{1,5}}?(?:(?:can|must|should|will|may)\s+)?(?P<action>{action_pattern})\b(?P<tail>.*)$",
        text,
        flags=re.I,
    )
    if article_subject and trim_phrase(article_subject.group("tail")):
        return f"{article_subject.group('action')}{article_subject.group('tail')}"
    bare_subject = re.match(
        rf"^(?:[a-z][a-z0-9_-]*\s+){{1,4}}(?:(?:can|must|should|will|may)\s+)?(?P<action>{action_pattern})\b(?P<tail>.*)$",
        text,
        flags=re.I,
    )
    if (
        bare_subject
        and trim_phrase(bare_subject.group("tail"))
        and len(content_terms(text[: bare_subject.start("action")])) <= 3
    ):
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


def material_contract_phrase(value: str, *, label_terms: Sequence[str], description_terms: Sequence[str]) -> bool:
    text = clean_artifact_text(value, split_parentheses=True)
    terms = content_terms(text)
    if not terms and not _qualified_boundary_artifact(text):
        return False
    if not terms:
        terms = ["boundary"]
    term_set = set(terms)
    first = terms[0]
    last = terms[-1]
    visible = [word.casefold().strip(".,;:") for word in visible_words(text) if word.strip(".,;:")]
    visible_set = set(visible)
    visible_last = visible[-1] if visible else ""
    carriers = (term_set | visible_set) & ARTIFACT_CARRIER_TERMS
    if not carriers:
        return False
    if first == "scenario" and last not in ARTIFACT_CARRIER_TERMS:
        return False
    if looks_action_term(first) and last not in ARTIFACT_CARRIER_TERMS:
        return False
    if "reviewable" in term_set and last not in ARTIFACT_CARRIER_TERMS:
        return False
    if last in ARTIFACT_CARRIER_TERMS:
        return True
    if visible_last in ARTIFACT_CARRIER_TERMS and len(visible) >= 2:
        return True
    if carriers & {"evidence", "history", "ledger", "record", "result", "state", "status"}:
        return True
    return bool(carriers and term_set & set(description_terms))


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
    if verb.endswith("g") and len(verb) > 2 and verb[-2] in {"a", "e", "i", "o", "u"}:
        forms.update({f"{verb}ged", f"{verb}ging"})
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
        if term not in COMPONENT_SHELL_TERMS
    ]
    if len(terms) < 2:
        terms = [
            term
            for term in ordered_terms(clean(label), stopwords=GENERIC_TERMS - ARTIFACT_CARRIER_TERMS)
            if not term.isdigit() and term not in COMPONENT_SHELL_TERMS
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
    if verb == "flag":
        return "flagged"
    if verb == "make":
        return "made"
    if verb == "run":
        return "run"
    if verb == "submit":
        return "submitted"
    if verb.endswith("e"):
        return f"{verb}d"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in {"a", "e", "i", "o", "u"}:
        return f"{verb[:-1]}ied"
    return f"{verb}ed"


def clean(value: Any) -> str:
    return clean_artifact_text(value, split_parentheses=True)


__all__ = [
    "ACTION_VERBS", "ARTIFACT_CARRIER_TERMS", "GENERIC_TERMS",
    "action_forms_pattern", "action_object_artifact_phrases", "clean_artifact_phrase",
    "clean_artifact_phrases", "content_terms", "descriptor_anchor_phrases", "domain_terms",
    "drop_subsumed_singletons", "local_terms", "looks_action_form", "looks_action_term", "material_contract_phrase",
    "looks_actor_term", "natural_phrase", "object_clause_focus", "phrase", "phrase_identity_terms",
    "split_contract_clauses", "strip_action", "term_phrase", "trim_phrase", "verb_forms_pattern",
]
