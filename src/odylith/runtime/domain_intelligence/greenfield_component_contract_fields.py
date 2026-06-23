"""Render clear component contract fields from semantic component facts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_terms import generic_actor_label_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_terms import localize_generic_actor_label
from odylith.runtime.domain_intelligence.greenfield_component_terms import ACTION_VERBS
from odylith.runtime.domain_intelligence.greenfield_component_terms import ARTIFACT_CARRIER_TERMS
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words

_PROOF_RESULT_TERMS = frozenset(
    {
        "answer",
        "decision",
        "estimate",
        "evidence",
        "number",
        "outcome",
        "output",
        "recommendation",
        "result",
        "score",
        "summary",
    }
)


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
    recommendation = (
        _recommendation_artifact(focus, action_terms=action_terms)
        if _component_owns_recommendation(action_terms, contract_terms)
        else ""
    )
    if recommendation:
        support = _supporting_artifacts(focus, exclude_terms=set(content_terms(recommendation)))
        rationale = _guidance_rationale_noun(recommendation, action_terms=action_terms)
        if role == "input":
            return f"{support}, goal or constraint context, prior state, and explanation context"
        return f"{recommendation}, {rationale}, blocked-state detail, and next-step context"
    adjustment = _adjustment_artifact(focus) if _component_owns_adjustment(contract_terms) else ""
    if adjustment and any(action in action_terms for action in ("adjust", "calculate", "compute", "derive")):
        support = _supporting_artifacts(focus, exclude_terms=set(content_terms(adjustment)))
        if role == "input":
            return f"{adjustment} request, {support}, prior state, and explanation context"
        rationale_terms = set(content_terms(focus)) | set(contract_terms)
        rationale = "adjustment rationale" if "rationale" in rationale_terms else "review rationale"
        return f"{adjustment} result, {rationale}, blocked-state detail, and next-step context"
    if role == "input":
        if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "forecast", "optimize", "predict", "score")):
            input_focus = f"input facts for {focus}" if _ends_with_term(focus, "state") else f"{focus} inputs"
            return f"{input_focus}, rule context, prior result, and validation command"
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
        return f"validated {_state_focus(focus)}, correction marker, and replayable change evidence"
    if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "forecast", "optimize", "predict", "score")):
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


def _ends_with_term(value: str, term: str) -> bool:
    words = visible_words(value)
    return bool(words and words[-1].casefold() == term.casefold())


def _state_focus(value: str) -> str:
    text = _clean(value).strip(" .")
    if _ends_with_term(text, "state"):
        return text
    return f"{text} state" if text else "state"


def produced_outputs_text(output_focus: str) -> str:
    text = _dedupe_adjacent_words(_clean(output_focus).rstrip(" ."))
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
    proof_focus = component_kind_echo_safe_phrase(
        label=label,
        phrase=_proof_focus(critical=critical, output_focus=output_focus, object_list=object_list),
    )
    handoff_focus = noun_slot_artifact_phrase(proof_focus)
    rows = [
        f"Successful path evidence for {label}: {proof_focus}, required inputs, visible result, and reviewer explanation.",
        f"Blocked input evidence for {label}: missing or malformed input, stops before a trusted result, and recovery explanation.",
        f"Replay evidence for {label}: actor, input facts, status, explanation, and proof trail.",
    ]
    if sibling_label:
        rows.append(
            f"Handoff evidence for {label}: {label} passes {handoff_focus} to {sibling_label} without letting either boundary rewrite the other's state."
            + (f" {sibling_focus} remains outside the boundary owned by {label}." if sibling_focus else "")
        )
    return rows


def noun_slot_artifact_phrase(value: str) -> str:
    """Return a grammatical artifact phrase for contexts that require a noun."""

    text = clean_artifact_text(value).strip(" .")
    if not text:
        return "local proof evidence"
    if looks_like_action_clause(text):
        action = base_action_clause(text).strip(" .")
        return f"evidence for {action}" if action else "local proof evidence"
    artifact = clean_artifact_phrase(text).strip(" .") or text
    artifact_terms = {word.casefold().strip(".,;:") for word in artifact.split()}
    if artifact_terms & ARTIFACT_CARRIER_TERMS:
        return artifact
    if not artifact.casefold().startswith(("evidence ", "evidence for ", "proof ", "proof for ")):
        return f"evidence for {artifact}"
    return artifact


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
    words = [word.casefold() for word in visible_words(text) if any(char.isalpha() for char in word)]
    if not words:
        return False
    abstract = {"approval", "approvals", "gate", "gates", "name", "result", "status", "story"}
    if len(words) >= 3 and all(word in abstract for word in words):
        return True
    if any(word in {"state", "status", "record", "result", "summary", "decision", "request"} for word in words):
        return False
    return all(word.endswith("ed") or word in {"allowed", "blocked", "rejected", "scheduled"} for word in words)


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
        phrase = _preserved_relation_phrase(raw) or _dedupe_adjacent_words(_ranked_contract_phrase(raw) or clean_artifact_phrase(raw))
        if component_shell_artifact(phrase):
            continue
        if status_only_artifact_fragment(phrase):
            continue
        if phrase and phrase not in rows:
            rows.append(phrase)
    return _drop_marked_detail_subsets(rows)


def _preserved_relation_phrase(value: str) -> str:
    text = clean_artifact_text(value).casefold().strip(" .")
    if not re.search(r"\b(?:related|linked|mapped)\b", text):
        return ""
    if len(content_terms(text)) < 4:
        return ""
    return text


def _drop_marked_detail_subsets(values: Sequence[str]) -> list[str]:
    identities = [(value, _detail_identity_terms(value)) for value in values]
    result: list[str] = []
    for value, terms in identities:
        if terms & {"incomplete", "missing", "recent", "unavailable"} and any(
            terms < other_terms for other_value, other_terms in identities if other_value != value
        ):
            continue
        result.append(value)
    return result


def _detail_identity_terms(value: str) -> set[str]:
    return {word.casefold() for word in visible_words(value) if word}


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
    if generic_actor_label_prefix(text):
        cleaned = clean_artifact_phrase(text)
        if cleaned and not generic_actor_label_prefix(cleaned):
            return cleaned
        return localize_generic_actor_label(text)
    return text


def _ranked_contract_phrase(value: str) -> str:
    text = _clean(value).strip(" .,;").casefold()
    if not re.match(r"^ranked\s+", text):
        return ""
    words = [word.casefold() for word in visible_words(text) if word[:1].isalpha()]
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


def _component_owns_recommendation(action_terms: Sequence[str], contract_terms: Sequence[str]) -> bool:
    local = set(contract_terms)
    actions = set(action_terms)
    return bool(actions & {"propose", "recommend", "suggest"} or local & {"recommendation", "suggestion", "adjustment"})


def _recommendation_artifact(value: str, *, action_terms: Sequence[str] = ()) -> str:
    text = _clean(value).strip(" .,;")
    if not text:
        return f"{_guidance_noun(action_terms)} result"
    phrases = [phrase.strip() for phrase in text.casefold().split(",") if phrase.strip()]
    scored: list[tuple[int, int, str]] = []
    for index, candidate in enumerate(phrases[:8]):
        terms = set(content_terms(candidate))
        if not terms:
            continue
        score = 0
        if terms & {"recommendation", "suggestion"}:
            score += 40
        if "adjustment" in terms:
            score += 32
        if terms & {"next", "action", "option", "choice", "decision", "plan"}:
            score += 10
        if terms & {"input", "stats", "body", "field", "fields", "source"}:
            score -= 12
        if score > 0:
            scored.append((score, -index, candidate))
    if scored:
        _score, _index, best = max(scored)
    else:
        best = phrases[0] if phrases else text
    best_terms = set(content_terms(best))
    if best_terms & {"recommendation", "suggestion", "proposal"}:
        return best
    return f"{best} {_guidance_noun(action_terms)}"


def _guidance_noun(action_terms: Sequence[str]) -> str:
    actions = set(action_terms)
    if "suggest" in actions:
        return "recommendation"
    if "propose" in actions:
        return "proposal"
    return "recommendation"


def _guidance_rationale_noun(value: str, *, action_terms: Sequence[str]) -> str:
    terms = set(content_terms(value))
    if "suggestion" in terms:
        return "suggestion rationale"
    if "proposal" in terms or "propose" in set(action_terms):
        return "proposal rationale"
    return "recommendation rationale"


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
        "flag": "flagged",
        "intake": "received",
        "keep": "kept",
        "leave": "left",
        "log": "logged",
        "make": "made",
        "read": "read",
        "run": "run",
        "see": "seen",
        "send": "sent",
        "set": "set",
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


_COMPONENT_KIND_TERMS = frozenset(
    {
        "adapter",
        "client",
        "component",
        "engine",
        "module",
        "queue",
        "service",
        "store",
        "surface",
        "system",
        "view",
    }
)


def component_kind_echo_safe_phrase(*, label: str, phrase: str) -> str:
    """Avoid proof phrases that echo the component kind right after the label."""

    text = _clean(phrase).strip(" .")
    if not text:
        return ""
    label_words = [word.casefold() for word in visible_words(label) if word.strip()]
    phrase_words = text.split()
    if not label_words or len(phrase_words) < 2:
        return text
    label_kind = label_words[-1]
    phrase_kind = phrase_words[0].casefold().strip(".,;:")
    if label_kind not in _COMPONENT_KIND_TERMS or phrase_kind != label_kind:
        return text
    stem = " ".join(label_words[:-1]).strip()
    tail = " ".join(phrase_words[1:]).strip()
    if stem:
        return f"{stem} {tail}".strip(" .")
    return tail or text


def _proof_focus(*, critical: str, output_focus: str, object_list: str) -> str:
    preferred = _proof_result_phrase(output_focus) or _proof_result_phrase(object_list)
    for candidate in (preferred, critical, output_focus, object_list):
        text = _dedupe_adjacent_words(clean_artifact_phrase(_clean(candidate)))
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


def _proof_result_phrase(value: str) -> str:
    best_score = 0
    best = ""
    for part in _clean(value).split(","):
        text = _dedupe_adjacent_words(clean_artifact_phrase(part))
        if not text:
            continue
        terms = set(content_terms(text))
        score = len(terms & _PROOF_RESULT_TERMS) * 10
        if "result" in terms:
            score += 20
        if "recommendation" in terms or "decision" in terms:
            score += 12
        if status_only_artifact_fragment(text):
            score -= 30
        if score > best_score:
            best_score = score
            best = text
    return best


def _dedupe_adjacent_words(value: str) -> str:
    words = _clean(value).split()
    result: list[str] = []
    for word in words:
        current = word.casefold().strip(".,;:")
        previous = result[-1].casefold().strip(".,;:") if result else ""
        if current and current == previous:
            continue
        result.append(word)
    return " ".join(result).strip(" .,;")


def _clean_boundary_clause(value: str) -> str:
    text = clean_artifact_phrase(_clean(value))
    text = re.sub(r"\bresponsibilities\s+not\s+named\s+by\s+(?:this\s+)?component\s+boundary\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:guide|guides|guided|guiding)\s+(?:the\s+)?first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:capture|captures|captured|capturing)\s+allowed\s+commands?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:expose|exposes|exposed|exposing)\s+blocked\s+states?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:local\s+)?blockers?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brecovery\s+context\s+owned\s+elsewhere\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brecovery\s+context\s+owned\s+by\s+[^,;]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bowns?\s+required\s+blocked-case\s+link\s+confirmed\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmaintains?\s+[a-z0-9 -]*\bcore\s+unit\s+protocol\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmutation\s+of\s+(?:original|upstream)\s+(?:input\s+)?facts\b", "original input facts", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcombines?\s+(?=reference|range|ranges|data|input|inputs)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*(?:and\s+)?\s*", ", ", text)
    text = re.sub(r"\s*;\s*", "; ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"^\s*(?:(?:and|or)\b\s*|,|;)+\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(?:(?:and|or)\b\s*|,|;)+\s*$", "", text, flags=re.IGNORECASE)
    return _strip_dangling_relation_tail(_clean(text).strip(" .,;"))


def _strip_dangling_relation_tail(value: str) -> str:
    words = _clean(value).strip(" .,;").split()
    dangling = {"against", "by", "for", "from", "into", "paired", "plus", "to", "using", "with", "without"}
    while words and words[-1].casefold().strip(".,;:") in dangling:
        words.pop()
    return " ".join(words).strip(" .,;")


def _clean(value: Any) -> str:
    return clean_artifact_text(value, split_parentheses=True)


__all__ = [
    "accepted_inputs_text",
    "component_kind_echo_safe_phrase",
    "component_shell_artifact",
    "contract_focus",
    "contract_list_text",
    "label_compound_rank",
    "noun_slot_artifact_phrase",
    "outside_boundary",
    "produced_outputs_text",
    "proof_rows",
    "state_transition_text",
    "status_only_artifact_fragment",
]
