"""Shared phrase cleanup for greenfield generated artifact text."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_text import clean_text

TERMINAL_STATUS_MODIFIERS = frozenset(
    {
        "accepted",
        "active",
        "blocked",
        "closed",
        "complete",
        "completed",
        "current",
        "declined",
        "delivered",
        "denied",
        "draft",
        "eligible",
        "final",
        "finished",
        "invalid",
        "live",
        "missing",
        "open",
        "pending",
        "ready",
        "received",
        "rejected",
        "requested",
        "scheduled",
        "selected",
        "stale",
        "submitted",
        "trusted",
        "valid",
        "validated",
        "visible",
    }
)

TRANSITION_ACTION_TERMS = frozenset({"advance", "advances", "advanced", "moving", "move", "moved", "moves", "transition", "transitioned", "transitions"})
TRANSITION_CONTEXT_TERMS = frozenset({"draft", "final", "from", "live", "scheduled", "state", "status"})
RELATION_TAIL_WORDS = frozenset({"against", "around", "for", "from", "into", "to", "toward", "towards", "with"})
TRAILING_RELATION_ACTIONS = frozenset(
    {
        "attach",
        "attaches",
        "attached",
        "belong",
        "belongs",
        "connect",
        "connects",
        "connected",
        "link",
        "links",
        "linked",
        "map",
        "mapped",
        "maps",
        "relate",
        "relates",
        "related",
        "remain",
        "remains",
    }
)


def normalize_artifact_tail(
    value: str,
    *,
    carrier_terms: Iterable[str],
    default_carrier: str = "state",
) -> str:
    """Repair common parser-tail debris without knowing the product domain."""

    words = _words(value)
    if not words:
        return ""
    carriers = _normalized_set(carrier_terms)
    words = _drop_relation_debris_after_carrier(words, carriers)
    words = _drop_generated_contract_tail(words, carriers)
    words = _normalize_history_modifier_order(words, carriers)
    words = _normalize_trailing_status_modifier(words, carriers)
    words = _normalize_lifecycle_status_state(words, carriers)
    words = _normalize_transition_status_state(words, carriers)
    words = _normalize_status_carrier(words, carriers)
    words = _complete_terminal_status_modifier(words, carriers, default_carrier=default_carrier)
    if words and _lower(words[-1]) in TERMINAL_STATUS_MODIFIERS and not any(_lower(word) in carriers for word in words):
        words.append(default_carrier)
        carriers.add(default_carrier)
        words = _drop_generated_contract_tail(words, carriers)
        words = _normalize_history_modifier_order(words, carriers)
        words = _normalize_trailing_status_modifier(words, carriers)
        words = _normalize_lifecycle_status_state(words, carriers)
        words = _normalize_transition_status_state(words, carriers)
        words = _normalize_status_carrier(words, carriers)
        words = _complete_terminal_status_modifier(words, carriers, default_carrier=default_carrier)
    return " ".join(words).strip(" .,;:")


def relation_object_phrase(value: str) -> str:
    """Return the object named by a dangling relation phrase, if present."""

    text = clean_text(value).casefold().strip(" .,;:")
    if not text:
        return ""
    direct = re.match(
        r"^(?:the\s+)?(?:entities|entity|records?|items?|objects?)\s+"
        r"(?P<object>.+?)\s+"
        r"(?:attach(?:es|ed)?|belong(?:s|ed)?|connect(?:s|ed)?|link(?:s|ed)?|map(?:s|ped)?|relate(?:s|d)?)\s+"
        r"(?:against|around|for|from|into|to|toward|towards|with)$",
        text,
        flags=re.IGNORECASE,
    )
    if direct:
        return _strip_low_signal_relation_object(direct.group("object"))
    words = text.split()
    if len(words) < 3 or words[-1] not in RELATION_TAIL_WORDS:
        return ""
    body = _strip_trailing_relation_action(words[:-1])
    body_text = " ".join(body).strip(" .,;:")
    body_text = re.sub(r"^(?:the\s+)?(?:entities|entity|records?|items?|objects?)\s+", "", body_text, flags=re.IGNORECASE)
    return _strip_low_signal_relation_object(body_text)


def reference_relation_description(value: str) -> str:
    relation_object = relation_object_phrase(value)
    if not relation_object:
        return ""
    return f"keeps reference entities linked to {relation_object}"


def singularize_last_word(value: str) -> str:
    words = clean_text(value).strip(" .,;:").split()
    if not words:
        return ""
    last = words[-1]
    lowered = last.casefold()
    if len(last) > 3 and lowered.endswith("ies"):
        words[-1] = f"{last[:-3]}y"
    elif len(last) > 4 and lowered.endswith(("ches", "shes", "xes", "zes")):
        words[-1] = last[:-2]
    elif len(last) > 3 and lowered.endswith("s") and not lowered.endswith("ss"):
        words[-1] = last[:-1]
    return " ".join(words)


def collapse_adjacent_duplicate_terms(value: str) -> str:
    """Collapse duplicate neighboring lexical terms in generated public text."""

    lines = str(value or "").splitlines()
    return "\n".join(_collapse_adjacent_duplicate_terms_line(line) for line in lines)


def collapse_adjacent_duplicate_terms_tree(value: object) -> object:
    """Return a public-copy tree with duplicate neighboring terms collapsed."""

    if isinstance(value, str):
        return collapse_adjacent_duplicate_terms(value)
    if isinstance(value, Mapping):
        return {key: collapse_adjacent_duplicate_terms_tree(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [collapse_adjacent_duplicate_terms_tree(nested) for nested in value]
    if isinstance(value, tuple):
        return tuple(collapse_adjacent_duplicate_terms_tree(nested) for nested in value)
    return value


def _drop_relation_debris_after_carrier(words: Sequence[str], carriers: set[str]) -> list[str]:
    result = list(words)
    while (
        len(result) > 2
        and _lower(result[-1]) in TRAILING_RELATION_ACTIONS
        and any(_lower(word) in carriers for word in result[:-1])
    ):
        result.pop()
    return result


def _drop_generated_contract_tail(words: Sequence[str], carriers: set[str]) -> list[str]:
    result = list(words)
    while len(result) >= 3 and _generated_contract_tail_should_drop(result, carriers):
        result.pop()
    return result


def _generated_contract_tail_should_drop(words: Sequence[str], carriers: set[str]) -> bool:
    tail = _lower(words[-1])
    if tail not in {"command", "proposal"}:
        return False
    if tail in carriers:
        return False
    return any(_lower(word) in carriers for word in words[:-1])


def _normalize_trailing_status_modifier(words: Sequence[str], carriers: set[str]) -> list[str]:
    lowered = [_lower(word) for word in words]
    if len(words) < 2 or lowered[-2] not in carriers or lowered[-1] not in TERMINAL_STATUS_MODIFIERS:
        return list(words)
    return [*words[:-2], words[-1], words[-2]]


def _normalize_lifecycle_status_state(words: Sequence[str], carriers: set[str]) -> list[str]:
    lowered = [_lower(word) for word in words]
    if len(words) < 4 or "lifecycle" not in lowered or lowered[-1] not in carriers:
        return list(words)
    core = [
        word
        for word in words[:-1]
        if _lower(word) not in TERMINAL_STATUS_MODIFIERS and _lower(word) != "lifecycle"
    ]
    if not core:
        return list(words)
    return [*core[:3], "lifecycle", words[-1]]


def _normalize_history_modifier_order(words: Sequence[str], carriers: set[str]) -> list[str]:
    lowered = [_lower(word) for word in words]
    if len(words) >= 4 and lowered[:2] == ["correction", "history"] and any(word in carriers for word in lowered[2:]):
        return [*words[2:5], "correction", "history"]
    if len(words) >= 3 and lowered[0] == "history" and any(word in carriers for word in lowered[1:]):
        return [*words[1:4], "history"]
    return list(words)


def _normalize_transition_status_state(words: Sequence[str], carriers: set[str]) -> list[str]:
    lowered = [_lower(word) for word in words]
    if len(words) < 3 or lowered[-1] not in carriers:
        return list(words)
    if lowered[-2:] == ["final", "state"]:
        return ["final", "status"]
    has_transition_action = any(word in TRANSITION_ACTION_TERMS for word in lowered[:-1])
    has_transition_context = lowered[-1] in {"state", "status"} or any(word in TRANSITION_CONTEXT_TERMS for word in lowered[:-1])
    if not (has_transition_action and has_transition_context):
        return list(words)
    core = [
        word
        for index, word in enumerate(words[:-1])
        if lowered[index] not in TRANSITION_ACTION_TERMS and lowered[index] not in TERMINAL_STATUS_MODIFIERS
    ]
    carrier = "status" if lowered[-1] == "status" else words[-1]
    return [*core[:3], "lifecycle", carrier] if core else ["lifecycle", carrier]


def _normalize_status_carrier(words: Sequence[str], carriers: set[str]) -> list[str]:
    lowered = [_lower(word) for word in words]
    if len(words) < 3 or lowered[-1] not in carriers:
        return list(words)
    if lowered[0].endswith("ing") and lowered[1] in TERMINAL_STATUS_MODIFIERS:
        return list(words[1:])
    modifier_count = sum(1 for word in lowered[:-1] if word in TERMINAL_STATUS_MODIFIERS)
    if modifier_count < 2:
        return list(words)
    core = [word for index, word in enumerate(words[:-1]) if lowered[index] not in TERMINAL_STATUS_MODIFIERS]
    return [*core[:4], words[-1]] if core else list(words)


def _complete_terminal_status_modifier(words: Sequence[str], carriers: set[str], *, default_carrier: str) -> list[str]:
    lowered = [_lower(word) for word in words]
    if len(words) < 3 or lowered[-1] not in TERMINAL_STATUS_MODIFIERS:
        return list(words)
    if lowered[-2] in carriers:
        return list(words)
    if not any(word in carriers for word in lowered[:-1]):
        return list(words)
    carrier = "status" if lowered[-1] == "final" else default_carrier
    return [*words, carrier]


def _strip_trailing_relation_action(words: Sequence[str]) -> list[str]:
    result = list(words)
    while result and result[-1] in TRAILING_RELATION_ACTIONS:
        result.pop()
    return result


def _strip_low_signal_relation_object(value: str) -> str:
    text = clean_text(value).casefold().strip(" .,;:")
    text = re.sub(r"^(?:the|a|an|those|these)\s+", "", text, flags=re.IGNORECASE).strip(" .,;:")
    if not text or text in {"entity", "entities", "record", "records", "item", "items", "object", "objects"}:
        return ""
    return text


def _words(value: str) -> list[str]:
    return clean_text(value).strip(" .,;:").split()


def _normalized_set(values: Iterable[str]) -> set[str]:
    return {clean_text(value).casefold().strip(" .,;:") for value in values if clean_text(value).strip(" .,;:")}


def _lower(value: str) -> str:
    return clean_text(value).casefold().strip(".,;:")


def _collapse_adjacent_duplicate_terms_line(value: str) -> str:
    words = str(value or "").split()
    if len(words) < 2:
        return str(value or "")
    result: list[str] = []
    previous = ""
    for word in words:
        key = _term_key(word)
        if key and key == previous and len(key) >= 4:
            continue
        result.append(word)
        previous = key
    return " ".join(result)


def _term_key(value: str) -> str:
    token = str(value or "").strip("`'\"“”‘’.,;:!?()[]{}<>")
    return token.casefold() if token else ""


__all__ = [
    "RELATION_TAIL_WORDS",
    "collapse_adjacent_duplicate_terms",
    "collapse_adjacent_duplicate_terms_tree",
    "normalize_artifact_tail",
    "reference_relation_description",
    "relation_object_phrase",
    "singularize_last_word",
]
