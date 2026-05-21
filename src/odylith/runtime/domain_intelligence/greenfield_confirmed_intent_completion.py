"""Deterministic completion for accepted greenfield Product Intent."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


CORE_FIELD_MIN_WORDS = {
    "product_story": 28,
    "state_object": 12,
    "first_path": 18,
    "proof_boundary": 18,
}

_GENERIC_TITLE_WORDS = {
    "app",
    "application",
    "helper",
    "platform",
    "product",
    "service",
    "system",
    "tool",
    "tracker",
    "workspace",
}

_ROLE_WORDS = {
    "admin",
    "advocate",
    "analyst",
    "applicant",
    "auditor",
    "borrower",
    "buyer",
    "chief",
    "client",
    "coordinator",
    "crew",
    "customer",
    "decision",
    "director",
    "engineer",
    "expert",
    "finder",
    "helper",
    "inspector",
    "lead",
    "manager",
    "member",
    "operator",
    "owner",
    "planner",
    "reviewer",
    "renter",
    "resident",
    "seller",
    "staff",
    "submitter",
    "supervisor",
    "support",
    "technician",
    "user",
    "volunteer",
}

_SYSTEM_SUFFIXES = (
    "profile registry",
    "workflow planner",
    "evidence and decision log",
    "access and safety guardrail",
)


def complete_confirmed_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Fill reviewable fields that can be inferred from accepted intent text."""

    result = copy.deepcopy(dict(intent))
    title = _title(result)
    if not _completion_seed_is_sufficient(result):
        return result
    result["human_actors"] = _completed_actor_rows(result, title=title)
    result["internal_systems"] = _completed_system_rows(result, title=title)
    _complete_core_fields(result, title=title)
    _complete_product_posture(result, title=title)
    return result


def _completion_seed_is_sufficient(intent: Mapping[str, Any]) -> bool:
    core = " ".join(
        _clean(intent.get(key))
        for key in ("product_story", "state_object", "first_path", "proof_boundary", "problem", "product_view")
        if _clean(intent.get(key))
    )
    if _word_count(core) < 24:
        return False
    return len(_semantic_terms(core)) >= 6


def _complete_core_fields(intent: dict[str, Any], *, title: str) -> None:
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    first_path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    actors = _actor_labels(intent)
    systems = _system_labels(intent)

    if _word_count(story) < CORE_FIELD_MIN_WORDS["product_story"]:
        actor_text = _join(actors[:2]) or f"{_focus_label(title)} users"
        intent["product_story"] = _sentence(
            f"{title} helps {actor_text} complete the accepted first path without losing the state, evidence, decision, and risk context needed to trust the outcome. "
            f"The product keeps {_short(state, fallback='the first release state')} and {_short(first_path, fallback='the first user journey')} connected so reviewers can understand what changed and why."
        )
    if _word_count(state) < CORE_FIELD_MIN_WORDS["state_object"]:
        state_label = _state_label(state, title=title)
        intent["state_object"] = _sentence(
            f"{state_label} records the current status, actor, source input, decision, blocked reason, evidence links, timestamp, and version history for the accepted first path."
        )
    if _word_count(first_path) < CORE_FIELD_MIN_WORDS["first_path"]:
        primary = actors[0] if actors else f"{_focus_label(title)} operator"
        system_text = _join(systems[:2]) or f"{_focus_label(title)} product systems"
        intent["first_path"] = _sentence(
            f"{primary} starts one real {title.lower()} case, uses {system_text} to move it through input, review, decision, and follow-up, then sees a clear outcome with missing or blocked evidence called out."
        )
    if _word_count(proof) < CORE_FIELD_MIN_WORDS["proof_boundary"]:
        intent["proof_boundary"] = _sentence(
            f"Release 0.0.1 is trusted only when the accepted path can be replayed from input through state change, reviewer-visible evidence, blocked or degraded states, access posture, and final decision. "
            f"It must not claim live integrations, broad automation, regulated correctness, or production-scale operation beyond the confirmed {title.lower()} boundary."
        )


def _complete_product_posture(intent: dict[str, Any], *, title: str) -> None:
    actors = _actor_labels(intent)
    systems = _system_labels(intent)
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    first_path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    focus = _focus_label(title)

    if not _clean(intent.get("problem")):
        intent["problem"] = _sentence(
            f"{focus} work becomes hard to trust when the user path, state, evidence, decision, and follow-up are scattered or under-specified."
        )
    if not _clean(intent.get("customer")):
        intent["customer"] = _sentence(
            f"{_join(actors[:3]) or f'{focus} operators and reviewers'} who need the accepted outcome to be understandable before broader scope is built."
        )
    if not _clean(intent.get("opportunity")):
        intent["opportunity"] = _sentence(
            f"Turn the confirmed {title.lower()} intent into a narrow first release that proves one complete path before adding broader automation, integrations, or scale."
        )
    if not _clean(intent.get("product_view")):
        state_phrase = _lower_first(state) if state else "the accepted state object"
        intent["product_view"] = _sentence(
            f"{title} is useful when a reviewer can inspect {state_phrase}, the first-path result, risk posture, and evidence from {_join(systems[:3]) or 'the product-owned systems'} together."
        )
    if len(_strings(intent.get("success_metrics"))) < 3:
        intent["success_metrics"] = list(
            unique_text(
                [
                    *_strings(intent.get("success_metrics")),
                    f"One accepted path completes with state, evidence, actor, timestamp, and final outcome visible: {_short(first_path)}.",
                    "At least one blocked, missing-data, or degraded path is visible and does not get mistaken for success.",
                    f"Release readiness stays inside the confirmed proof boundary: {_short(proof)}.",
                ]
            )
        )
    if not _strings(intent.get("assumptions")):
        intent["assumptions"] = [
            f"The first release proves one concrete {title.lower()} path before broader scope or automation.",
            "External integrations can start as deterministic fixtures unless the accepted path cannot be proven without a live source.",
            f"Security, privacy, accessibility, safety, audit, and retention obligations scale with the {focus.lower()} data and decisions involved.",
        ]
    if not _strings(intent.get("ambiguities")):
        intent["ambiguities"] = [
            f"Which {focus.lower()} actor owns the final release decision when evidence is incomplete or disputed?",
            f"Which source, device, document, dataset, or external service is authoritative for the first {title.lower()} proof?",
            "Which privacy, safety, compliance, or access rule would change the first path if it is stricter than assumed?",
        ]
    if not _strings(intent.get("non_goals")):
        intent["non_goals"] = [
            f"No claim that {title} handles every user, integration, dataset, edge case, or operational scale in release 0.0.1.",
            "No irreversible automation, regulated decision, or live external dependency without a separately accepted proof boundary.",
        ]
    if not story:
        intent["product_story"] = _sentence(
            f"{title} helps {_join(actors[:2]) or f'{focus} users'} complete one accountable path with state, evidence, and decision context visible."
        )


def _completed_actor_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    rows = _strings(intent.get("human_actors"))
    labels = [_actor_label(row, title=title) for row in rows]
    labels = [label for label in labels if label]
    if len(labels) < 3:
        labels.extend(_derived_actor_labels(intent, title=title))
    labels = list(unique_text(labels))[:5]

    first_path = _short(_clean(intent.get("first_path")), fallback="the accepted first path")
    state = _short(_clean(intent.get("state_object")), fallback="the accepted state")
    proof = _short(_clean(intent.get("proof_boundary")), fallback="the release proof")
    completed: list[str] = []
    for index, label in enumerate(labels):
        original = rows[index] if index < len(rows) else label
        if _word_count(original) >= 7 and _semantic_overlap(original, f"{first_path} {state} {proof}") >= 1:
            completed.append(original)
            continue
        completed.append(_actor_description(label=label, index=index, title=title, first_path=first_path, state=state, proof=proof))
    return list(unique_text(completed))


def _actor_description(*, label: str, index: int, title: str, first_path: str, state: str, proof: str) -> str:
    if index == 0:
        body = f"uses {title} to complete the accepted first path, keep the result reviewable, and decide what should happen next"
    elif index == 1:
        body = "reviews shared product state, checks evidence quality, and challenges incomplete or disputed outcomes"
    elif index == 2:
        body = f"has limited or supporting access to the relevant task, evidence, or follow-up and must not see or change unrelated private state"
    elif index == 3:
        body = "owns release or operational readiness and verifies that release proof is strong enough before broader scope is accepted"
    else:
        body = "supports recovery, import, escalation, or troubleshooting with narrow audit-friendly access and clear privacy limits"
    return f"{label}: {body}."


def _completed_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    rows = _strings(intent.get("internal_systems")) or _strings(intent.get("component_responsibilities"))
    context = _context(intent)
    completed = [_system_row(row, context=context, title=title) for row in rows]
    completed = [row for row in completed if row]
    if len(completed) < 2:
        completed = _derived_system_rows(intent, title=title)
    return list(unique_text(completed))[:8]


def _system_row(row: str, *, context: str, title: str) -> str:
    raw = _clean(row)
    if not raw:
        return ""
    if "—" in raw or ":" in raw:
        name, description = re.split(r"\s+—\s+|:\s*", raw, maxsplit=1)
        if _word_count(description) >= 5:
            return f"{_title_case(name)} — {description.rstrip('.')}"
    name = _system_label(raw, title=title)
    if not name:
        return ""
    clause = _best_context_clause(name, context)
    if clause:
        return f"{name} — owns {name.lower()} behavior for the accepted path. Relevant evidence: {_short(clause, limit=180)}"
    return f"{name} — owns input capture, state change, validation evidence, blocked states, and handoff for the accepted {title.lower()} path"


def _derived_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    focus = _focus_label(title)
    state = _state_label(_clean(intent.get("state_object")), title=title)
    first_path = _short(_clean(intent.get("first_path")), fallback="the accepted first path")
    proof = _short(_clean(intent.get("proof_boundary")), fallback="the release proof")
    names = [f"{focus} {suffix}" for suffix in _SYSTEM_SUFFIXES]
    descriptions = [
        f"owns identity, current status, version history, and traceable changes for {state}",
        f"guides the first path, captures allowed commands, exposes blocked states, and keeps the next action clear: {first_path}",
        f"records source evidence, validation output, reviewer decision, failure reason, and release-readiness proof: {proof}",
        "keeps authorization, shared access, privacy, safety, retention, accessibility, reminders, and recovery behavior explicit before wider rollout",
    ]
    return [f"{_title_case(name)} — {description.rstrip('.')}" for name, description in zip(names, descriptions)]


def _derived_actor_labels(intent: Mapping[str, Any], *, title: str) -> list[str]:
    focus = _focus_label(title)
    context = _context(intent)
    candidates = _role_candidates(context)
    labels: list[str] = []
    for candidate in candidates:
        if _word_count(candidate) <= 5:
            labels.append(_title_case(candidate))
    labels.extend(
        [
            f"{focus} operator",
            f"{focus} reviewer",
            f"{focus} support owner",
            f"{focus} release decision owner",
        ]
    )
    return list(unique_text(labels))


def _role_candidates(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z/-]*", text)
    candidates: list[str] = []
    for index, word in enumerate(words):
        if word.casefold() not in _ROLE_WORDS:
            continue
        start = max(0, index - 2)
        phrase = " ".join(words[start : index + 1])
        phrase = re.sub(r"^(?:a|an|the|one|first|main|primary|current)\s+", "", phrase, flags=re.IGNORECASE)
        if phrase and not phrase.casefold().startswith(("product ", "project ", "workflow ")):
            candidates.append(phrase)
    return list(unique_text(candidates))


def _actor_label(row: str, *, title: str) -> str:
    raw = _clean(str(row).split("—", 1)[0].split(":", 1)[0])
    raw = re.sub(r"^(?:a|an|the|primary|main)\s+", "", raw, flags=re.IGNORECASE).strip()
    if not raw:
        return ""
    if raw.casefold() in {"operator", "reviewer", "user", "owner", "helper", "support", "admin"}:
        raw = f"{_focus_label(title)} {raw}"
    return _title_case(raw)


def _actor_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in _strings(intent.get("human_actors")):
        labels.append(_clean(row.split("—", 1)[0].split(":", 1)[0]))
    return [label for label in labels if label]


def _system_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in _strings(intent.get("internal_systems")):
        labels.append(_clean(row.split("—", 1)[0].split(":", 1)[0]))
    return [label for label in labels if label]


def _system_label(row: str, *, title: str) -> str:
    raw = _clean(row)
    if _word_count(raw) > 9:
        raw = " ".join(raw.split()[:7])
    raw = re.sub(r"^(?:a|an|the)\s+", "", raw, flags=re.IGNORECASE)
    return _title_case(raw or f"{_focus_label(title)} system")


def _state_label(value: str, *, title: str) -> str:
    text = _clean(value)
    if text:
        first = re.split(r"[.;]", text, maxsplit=1)[0]
        match = re.search(r"\b(?:state object is|primary state object is|is)\s+(?:a|an|the)?\s*(?P<label>[^.;:]+)", first, re.IGNORECASE)
        if match:
            return _title_case(match.group("label"))
        if _word_count(first) <= 8:
            return _title_case(first)
    return f"{_focus_label(title)} state profile"


def _title(intent: Mapping[str, Any]) -> str:
    return _clean(intent.get("title")) or "Greenfield Project"


def _focus_label(title: str) -> str:
    words = [
        word
        for word in re.findall(r"[A-Za-z0-9]+", title)
        if word.casefold() not in _GENERIC_TITLE_WORDS
    ]
    if not words:
        words = re.findall(r"[A-Za-z0-9]+", title)[:3]
    return _title_case(" ".join(words[:4]) or "Project")


def _context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("title")),
        _clean(intent.get("product_story")),
        _clean(intent.get("problem")),
        _clean(intent.get("customer")),
        _clean(intent.get("opportunity")),
        _clean(intent.get("product_view")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        _clean(intent.get("proof_boundary")),
        " ".join(_strings(intent.get("human_actors"))),
        " ".join(_strings(intent.get("external_systems"))),
        " ".join(_strings(intent.get("assumptions"))),
        " ".join(_strings(intent.get("ambiguities"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def _best_context_clause(name: str, context: str) -> str:
    terms = _semantic_terms(name)
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+", context)):
        clause = _clean(sentence).strip(" .")
        if _word_count(clause) < 6:
            continue
        overlap = len(terms & _semantic_terms(clause))
        if overlap:
            scored.append((overlap, -index, clause))
    scored.sort(reverse=True)
    return scored[0][2] if scored else ""


def _semantic_overlap(left: str, right: str) -> int:
    return len(_semantic_terms(left) & _semantic_terms(right))


def _semantic_terms(text: str) -> set[str]:
    stop = {
        "and",
        "are",
        "before",
        "can",
        "for",
        "from",
        "has",
        "have",
        "into",
        "that",
        "the",
        "this",
        "with",
        "without",
    }
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(text).casefold()):
        token = raw.strip("-_")
        if len(token) < 3 or token in stop:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = f"{token[:-3]}y"
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            token = token[:-1]
        if token not in stop:
            terms.add(token)
    return terms


def _strings(value: object) -> list[str]:
    return list(text_values(value))


def _join(values: Sequence[str]) -> str:
    cleaned = [_clean(value).rstrip(".") for value in values if _clean(value)]
    if len(cleaned) <= 1:
        return cleaned[0] if cleaned else ""
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def _short(value: str, *, fallback: str = "", limit: int = 220) -> str:
    text = _clean(value) or fallback
    if len(text) <= limit:
        return text.rstrip(".")
    clipped = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    words = clipped.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "to", "with", "for", "from", "of", "the", "a", "an", "required"}:
        words.pop()
    return " ".join(words).rstrip(".")


def _sentence(value: str) -> str:
    text = _clean(value).strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _lower_first(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    return text[:1].lower() + text[1:]


def _title_case(value: str) -> str:
    words: list[str] = []
    for word in _clean(value).split():
        lower = word.casefold()
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "ui", "ux"}:
            words.append(lower.upper())
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def _word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", _clean(value)))


def _clean(value: object) -> str:
    text = clean_text(value)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = ["complete_confirmed_intent"]
