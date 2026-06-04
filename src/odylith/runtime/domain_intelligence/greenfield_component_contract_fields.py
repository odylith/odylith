"""Render clear component contract fields from semantic component facts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_component_terms import ACTION_VERBS
from odylith.runtime.domain_intelligence.greenfield_component_terms import ARTIFACT_CARRIER_TERMS
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def contract_focus(
    *,
    object_list: str,
    action_terms: Sequence[str],
    fallback: str,
    role: str,
    contract_terms: Sequence[str] = (),
) -> str:
    focus = _safe_artifact_focus(_clean(object_list) or _clean(fallback).casefold() or "accepted state")
    focus = _strip_trailing_status_only_focus(focus)
    adjustment = _adjustment_artifact(focus) if _component_owns_adjustment(contract_terms) else ""
    if adjustment and any(action in action_terms for action in ("adjust", "calculate", "compute", "derive")):
        support = _supporting_artifacts(focus, exclude_terms=set(content_terms(adjustment)))
        if role == "input":
            return f"{adjustment} request, {support}, prior state, and explanation context"
        rationale_terms = set(content_terms(focus)) | set(contract_terms)
        rationale = "adjustment rationale" if "rationale" in rationale_terms else "review rationale"
        return f"{adjustment} result, {rationale}, blocked-state detail, and next-step context"
    if role == "input":
        if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "score")):
            return f"{focus} inputs, rule context, prior result, and validation command"
        if any(action in action_terms for action in ("capture", "create", "edit", "log", "record", "save", "store", "submit")):
            return f"required {focus} command, required fields, prior state, and explanation context"
        if any(action in action_terms for action in ("compare", "order", "rank")):
            return f"candidate {focus} set, comparison criteria, tie-break rule, and prior selection state"
        if any(action in action_terms for action in ("select", "choose")):
            return f"candidate {focus} set, selection criteria, tie-break rule, and prior selection state"
        if any(action in action_terms for action in ("export", "delete")):
            return f"authorized {focus} request, actor authority, protected-state reference, and policy context"
        if "request" in action_terms:
            return f"{focus}, actor context, prior state, and validation context"
        return f"required {focus} input, prior state, explanation context, and validation command"
    if any(action in action_terms for action in ("capture", "create", "edit", "log", "record", "save", "store", "submit")):
        return f"validated {focus} state, correction marker, and replayable change evidence"
    if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "score")):
        return f"{focus} result, rule explanation, and review evidence"
    if any(action in action_terms for action in ("compare", "order", "rank")):
        return f"{_ranked_output_artifact(focus)}, comparison explanation, and selection rationale"
    if any(action in action_terms for action in ("select", "choose")):
        return f"selected {focus} result, selection explanation, and selection rationale"
    if any(action in action_terms for action in ("export", "delete")):
        return f"{focus} decision, allowed or blocked marker, and lifecycle evidence"
    if "request" in action_terms:
        return f"{focus} state update, allowed or blocked marker, and next-step context"
    return f"{focus} result, state update, and review detail"


def produced_outputs_text(output_focus: str) -> str:
    text = _clean(output_focus).rstrip(" .")
    lowered = text.casefold()
    suffixes = []
    if "blocked-state" not in lowered and "blocker" not in lowered:
        suffixes.append("blocked-state detail")
    if "rationale" not in lowered and "explanation" not in lowered:
        suffixes.append("reviewer explanation")
    if "next-step context" not in lowered:
        suffixes.append("next-step context")
    if "handoff" not in lowered:
        suffixes.append("handoff context")
    if not suffixes:
        return contract_list_text(text)
    if len(suffixes) == 1:
        suffix_text = suffixes[0]
    else:
        suffix_text = f"{', '.join(suffixes[:-1])}, and {suffixes[-1]}"
    return contract_list_text(text, suffix_text)


def accepted_inputs_text(input_focus: str) -> str:
    rows = _contract_text_items(input_focus)
    required = ("authorized actor", "validation context")
    return contract_list_text(*rows, *required)


def contract_list_text(*values: str) -> str:
    return ", ".join(_contract_text_items(", ".join(value for value in values if _clean(value))))


def state_transition_text(
    *,
    action_terms: Sequence[str],
    object_phrases: Sequence[str],
    context_text: str = "",
    anchor_terms: Sequence[str] = (),
) -> str:
    verbs = [_past_tense(verb) for verb in action_terms if verb != "sync"]
    transitions = _transition_terms(object_phrases, context_text=context_text, anchor_terms=anchor_terms)
    states = unique_text(
        [
            *transitions,
            "requested",
            "received",
            *verbs,
            "validated",
            "blocked",
            "revised",
            "ready-for-next-step",
        ]
    )
    return ", ".join(state for state in states[:18] if state not in {"needed", "required"})


def outside_boundary(*, sibling_focus: str) -> str:
    rows = [
        "adjacent component state owned elsewhere",
        "original input facts and upstream source truth",
        "release approval and broader rollout decisions",
    ]
    if sibling_focus:
        rows[0] = sibling_focus
    return "; ".join(unique_text(_clean_boundary_clause(row) for row in rows if _clean_boundary_clause(row)))


def proof_rows(
    *,
    label: str,
    object_list: str,
    critical: str,
    input_focus: str,
    output_focus: str,
    sibling_label: str,
    sibling_focus: str,
) -> list[str]:
    proof_focus = _proof_focus(critical=critical, output_focus=output_focus, object_list=object_list)
    rows = [
        f"{label} shows {proof_focus} on a successful path with enough explanation for a reviewer to understand it.",
        f"When required input is missing or malformed, {label} stops before showing a trusted result and explains what must change.",
        f"A replay of {label} still connects the actor, input facts, status, and explanation.",
    ]
    if sibling_label:
        rows.append(
            f"{sibling_label} can consume the result but cannot rewrite {label}'s local state"
            + (f" while {sibling_focus} remains sibling-owned." if sibling_focus else ".")
        )
    return rows


def component_shell_artifact(value: str) -> bool:
    text = _clean(value).casefold()
    if not text:
        return False
    if text in {"context", "detail", "details", "description"}:
        return True
    return bool(
        re.fullmatch(
            r"[a-z0-9][a-z0-9 '-]{0,60}\s+(?:adapter|client|component|engine|queue|service|store|surface|system|view)",
            text,
        )
        or re.fullmatch(
            r"[a-z0-9][a-z0-9 '-]{0,60}\s+(?:adapter|client|component|engine|queue|service|store|surface|system|view)\s+state\s+update",
            text,
        )
    )


def status_only_artifact_fragment(value: str) -> bool:
    text = _clean(value).casefold()
    if re.fullmatch(r"(?:[a-z][a-z'-]*ed\s+){1,4}(?:state\s+)?(?:update|marker|result|decision)", text):
        return True
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if not words:
        return False
    if any(word in {"state", "status", "record", "result", "summary", "decision", "request"} for word in words):
        return False
    return all(word.endswith("ed") or word in {"allowed", "blocked", "rejected", "scheduled"} for word in words)


def literal_label_terms(label: str) -> list[str]:
    drop = {
        "adapter",
        "and",
        "client",
        "component",
        "engine",
        "for",
        "in",
        "of",
        "on",
        "service",
        "store",
        "surface",
        "system",
        "the",
        "to",
        "view",
        "viewer",
        "with",
        "workspace",
    }
    return [
        word
        for word in re.findall(r"[a-z0-9][a-z0-9'-]*", _clean(label).casefold())
        if word not in drop
    ]


def label_compound_rank(value: str) -> tuple[int, str]:
    words = value.split()
    if len(words) < 2:
        return (5, value)
    left, right = words[0], words[1]
    if right in ARTIFACT_CARRIER_TERMS and (left.endswith("ing") or left in ARTIFACT_CARRIER_TERMS):
        return (0, value)
    if right in ARTIFACT_CARRIER_TERMS:
        return (1, value)
    if left in ARTIFACT_CARRIER_TERMS:
        return (2, value)
    return (3, value)


def _contract_text_items(value: str) -> list[str]:
    rows: list[str] = []
    for raw in re.split(r",\s+", _clean(value), flags=re.IGNORECASE):
        raw = re.sub(r"^(?:and|or)\s+", "", raw, flags=re.IGNORECASE)
        phrase = _ranked_contract_phrase(raw) or clean_artifact_phrase(raw)
        if component_shell_artifact(phrase):
            continue
        if status_only_artifact_fragment(phrase):
            continue
        if phrase and phrase not in rows:
            rows.append(phrase)
    return rows


def _strip_trailing_status_only_focus(value: str) -> str:
    text = _clean(value).strip(" .,;")
    if not text or "," not in text:
        return text
    parts = [part.strip(" .,;") for part in text.split(",") if part.strip(" .,;")]
    while len(parts) > 1 and status_only_artifact_fragment(parts[-1]):
        parts.pop()
    return _clean(", ".join(parts)) or text


def _ranked_output_artifact(value: str) -> str:
    text = _clean(value).strip(" .,;")
    lowered = text.casefold()
    if re.search(r"\balternatives?\b", lowered):
        return "ranked alternatives"
    if re.search(r"\boptions?\b", lowered):
        return "ranked options"
    if re.search(r"\bcandidates?\b", lowered):
        return "ranked candidates"
    match = re.match(r"(?P<entity>[a-z][a-z0-9 /_-]{2,64}?)\s+by\b", lowered)
    if match:
        entity = clean_artifact_phrase(match.group("entity"))
        if entity and not status_only_artifact_fragment(entity):
            return f"ranked {entity}"
    return f"ranked {text} result"


def _safe_artifact_focus(value: str) -> str:
    text = _clean(value).strip(" .")
    if re.match(
        r"^(?:operator|maintainer|reviewer|primary user|project operator|domain reviewer|implementation owner|"
        r"evidence owner|workflow operator|risk reviewer|proof reviewer)(?:\s|:|[-–—]|$)",
        text,
        flags=re.IGNORECASE,
    ):
        return f"local {text[:1].lower()}{text[1:]}"
    return text


def _ranked_contract_phrase(value: str) -> str:
    text = _clean(value).strip(" .,;").casefold()
    if not re.match(r"^ranked\s+", text):
        return ""
    words = re.findall(r"[a-z][a-z0-9'-]*", text)
    if len(words) < 2 or len(words) > 4:
        return ""
    if set(words[1:]) & {"alternatives", "alternative", "options", "option", "candidates", "candidate"}:
        return text
    if any(word in {"state", "status", "marker", "evidence", "context", "rationale"} for word in words[1:]):
        return ""
    return text


def _adjustment_artifact(value: str) -> str:
    phrases = [phrase.strip() for phrase in _clean(value).casefold().split(",") if phrase.strip()]
    primary_terms = content_terms(", ".join(phrases[:5]))
    if "plan" in primary_terms and (
        "adjusted" in primary_terms or "adjustment" in primary_terms or "target" in primary_terms
    ):
        return "plan adjustment"
    for phrase in phrases[:5]:
        phrase_terms = content_terms(phrase)
        if "adjusted" in phrase_terms and len(phrase_terms) >= 2:
            subject = next((term for term in phrase_terms if term != "adjusted"), "")
            if subject:
                return f"{subject} adjustment"
    return ""


def _component_owns_adjustment(terms: Sequence[str]) -> bool:
    local = set(terms)
    return bool(local & {"adjustment", "recommendation", "target"} and local & {"plan", "target", "recommendation"})


def _supporting_artifacts(value: str, *, exclude_terms: set[str]) -> str:
    phrases: list[str] = []
    for candidate in [part.strip() for part in _clean(value).casefold().split(",") if part.strip()]:
        terms = set(content_terms(candidate))
        if not terms or terms & exclude_terms or "rationale" in terms:
            continue
        phrases.append(candidate)
        if len(phrases) >= 3:
            break
    return phrase(phrases) or "accepted input detail"


def _transition_terms(
    object_phrases: Sequence[str],
    *,
    context_text: str = "",
    anchor_terms: Sequence[str] = (),
) -> list[str]:
    state_words = {_past_tense(verb) for verb in ACTION_VERBS if verb}
    state_words.update({"sent", "stale", "ready", "open", "closed", "pending", "visible", "hidden"})
    rows: list[str] = []
    phrases = [*_context_transition_clauses(context_text, anchor_terms=anchor_terms), *object_phrases]
    for phrase in phrases:
        for term in _transition_candidate_terms(phrase):
            if term in {"required", "succeed", "succeeded"}:
                continue
            if term in state_words or (len(term) > 4 and term.endswith("ed")):
                rows.append(term)
    return unique_text(rows)


def _transition_candidate_terms(value: str) -> list[str]:
    return ordered_terms(_clean(value), stopwords=())


def _context_transition_clauses(context_text: str, *, anchor_terms: Sequence[str]) -> list[str]:
    text = _clean(context_text)
    if not text:
        return []
    anchors = set(anchor_terms)
    anchors.update({"status", "lifecycle", "history", "timeline", "event", "progress"})
    rows: list[str] = []
    for clause in re.split(r"(?<=[.!?])\s+|;\s+", text):
        terms = set(content_terms(clause))
        if terms & anchors:
            rows.append(clause)
    return rows[:8]


def _past_tense(value: str) -> str:
    verb = str(value or "").strip()
    if not verb:
        return ""
    irregular = {
        "build": "built",
        "choose": "chosen",
        "find": "found",
        "keep": "kept",
        "log": "logged",
        "make": "made",
        "read": "read",
        "see": "seen",
        "send": "sent",
        "show": "shown",
        "submit": "submitted",
    }
    if verb in irregular:
        return irregular[verb]
    if verb.endswith("e"):
        return f"{verb}d"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in {"a", "e", "i", "o", "u"}:
        return f"{verb[:-1]}ied"
    return f"{verb}ed"


def _proof_focus(*, critical: str, output_focus: str, object_list: str) -> str:
    for candidate in (critical, output_focus, object_list):
        text = clean_artifact_phrase(_clean(candidate))
        if not text:
            continue
        lowered = text.casefold()
        if re.search(r"\b(?:guide|guides|keep|keeps)\s+(?:the\s+)?first\s+path\b", lowered):
            continue
        if lowered in {"visible result", "result", "local result", "the local result"}:
            continue
        if re.search(r"\b(?:reaches|produces|returns|accepts|validates)\b", lowered):
            continue
        return text
    return "the local result"


def _clean_boundary_clause(value: str) -> str:
    text = clean_artifact_phrase(_clean(value))
    text = re.sub(r"\bresponsibilities\s+not\s+named\s+by\s+(?:this\s+)?component\s+boundary\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:guide|guides|guided|guiding)\s+(?:the\s+)?first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:capture|captures|captured|capturing)\s+allowed\s+commands?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:expose|exposes|exposed|exposing)\s+blocked\s+states?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:local\s+)?blockers?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brecovery\s+context\s+owned\s+elsewhere\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmutation\s+of\s+(?:original|upstream)\s+(?:input\s+)?facts\b", "original input facts", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*(?:and\s+)?\s*", ", ", text)
    text = re.sub(r"\s*;\s*", "; ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"^\s*(?:(?:and|or)\b|,|;)+\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(?:(?:and|or)\b|,|;)+\s*$", "", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .,;")


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "").replace("(", " ").replace(")", " ")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "accepted_inputs_text",
    "component_shell_artifact",
    "contract_focus",
    "contract_list_text",
    "label_compound_rank",
    "literal_label_terms",
    "outside_boundary",
    "produced_outputs_text",
    "proof_rows",
    "state_transition_text",
    "status_only_artifact_fragment",
]
