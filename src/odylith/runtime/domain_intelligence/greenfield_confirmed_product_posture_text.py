from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_completion import state_label as _state_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


def state_focus_phrase(state: str, *, title: str) -> str:
    text = _clean(state)
    if not text:
        return f"{_focus_label(title).lower()} state"
    state_label = _state_label(text, title=title)
    if 1 <= _word_count(state_label) <= 8:
        label = state_label.casefold()
        if not label.startswith(("a ", "an ", "the ")):
            label = f"the {label}"
        return label
    text = re.sub(r"^(?:the\s+)?(?:core|main|primary)\s+state\s+(?:is|object\s+is)\s+", "", text, flags=re.I)
    text = re.sub(r"^a\s+", "the ", text, flags=re.I)
    first_clause = re.split(r";|(?<=[.!?])\s+", text, maxsplit=1)[0].strip(" .")
    first_clause = re.split(r":\s*", first_clause, maxsplit=1)[-1].strip(" .")
    compact_label = _state_label_before_detail_list(first_clause)
    if compact_label:
        return compact_label
    return _short(first_clause, fallback=f"{_focus_label(title).lower()} state", limit=160).rstrip(".")


def _state_label_before_detail_list(value: str) -> str:
    text = _clean(value).strip(" .")
    match = re.match(
        r"^(?:a|an|the)?\s*(?P<label>[A-Za-z][A-Za-z0-9 '&/-]{1,80}?)\s+with\s+",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    label = _clean(match.group("label")).strip(" .")
    if not 2 <= _word_count(label) <= 6:
        return ""
    article = "an" if label[:1].casefold() in {"a", "e", "i", "o", "u"} else "a"
    return label if label.casefold().startswith(("a ", "an ", "the ")) else f"{article} {label.casefold()}"


def visible_outcome_phrase(first_path: str, *, proof: str = "") -> str:
    text = first_path_outcome_phrase(
        first_path,
        proof_boundary=proof,
        fallback="a visible, useful result",
        limit=190,
    ).rstrip(".")
    text = _strip_leading_outcome_connector(text)
    if re.match(r"^why\b", text, flags=re.I):
        text = f"the explanation for {text}"
    if not re.search(
        r"\b(?:answer|card|confirmation|consequence|decision|entry|explanation|history|"
        r"metrics?|outcome|plan|readout|recommendation|reflection|report|result|schedule|session|status|summary|"
        r"timeline|trend|view)\b",
        text,
        re.I,
    ):
        text = _nominal_visible_outcome_phrase(text)
    return text


def _strip_leading_outcome_connector(value: str) -> str:
    text = _clean(value).strip(" .")
    return re.sub(r"^(?:and|or|then)\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .") or text


def _nominal_visible_outcome_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    if re.match(r"^(?:a|an|the|both|each|one)\b", text, flags=re.I):
        return text
    if re.match(r"^(?:accepted|approved|completed|confirmed|persisted|recorded|saved)\b", text, flags=re.I):
        return f"the {text[:1].lower() + text[1:]}"
    return text


def proof_boundary_metric(proof_boundary: str, *, outcome: str = "") -> str:
    proof = _clean(proof_boundary)
    if not proof:
        target = outcome or "the promised user outcome"
        return f"Release readiness requires evidence that {target} is correct, visible, and limited to the first release."
    non_goal_hint = ""
    if re.search(r"\b(?:must not|without claiming|does not claim|no claim|non-goals?)\b", proof, re.IGNORECASE):
        non_goal_hint = " and keeps deferred or forbidden claims outside release readiness"
    target = outcome or "the promised user outcome"
    return f"Release readiness requires evidence that {target} is correct, visible, and reproducible{non_goal_hint}."


def path_capability(value: str, *, fallback: str, limit: int = 180) -> str:
    action = first_path_action_phrase(value, fallback=fallback, limit=limit, max_fragments=1)
    return _short(_capability_action_clause(action), fallback=fallback, limit=limit)


def _capability_action_clause(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return "complete the accepted path"
    if looks_like_action_clause(text):
        return base_action_clause(text)
    actor_action = _actor_action_clause(text)
    if actor_action:
        return actor_action
    converted = base_action_clause(text)
    if converted and converted != text.casefold():
        return converted
    return text[:1].lower() + text[1:]


def _actor_action_clause(value: str) -> str:
    text = re.sub(r"^(?:a|an|the)\s+", "", clean_text(value).strip(" ."), flags=re.IGNORECASE)
    words = text.split()
    for index in range(1, min(len(words), 6)):
        verb = words[index].strip(".,;:")
        base = _base_action_verb(verb)
        if base != verb.casefold():
            tail = " ".join(words[index + 1 :]).strip(" .")
            return base_action_clause(" ".join(part for part in (base, tail) if part))
    return ""


def _base_action_verb(value: str) -> str:
    token = str(value or "").casefold()
    overrides = {
        "chooses": "choose",
        "does": "do",
        "goes": "go",
        "has": "have",
        "is": "be",
        "receives": "receive",
        "sees": "see",
        "uses": "use",
    }
    if token in overrides:
        return overrides[token]
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


__all__ = ["path_capability", "proof_boundary_metric", "state_focus_phrase", "visible_outcome_phrase"]
