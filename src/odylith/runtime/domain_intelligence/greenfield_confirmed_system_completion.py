"""Internal-system completion for accepted greenfield Product Intent."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import normalize_binary_action_control_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text as _title_case
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import (
    confirmed_system_description,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import (
    confirmed_system_name,
)
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


_SYSTEM_SUFFIXES = (
    "product record",
    "experience guide",
    "evidence log",
    "release guardrail",
)


def completed_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    """Return reviewable internal-system rows completed from accepted intent context."""

    rows = confirmed_text_values(intent.get("internal_systems")) or confirmed_text_values(
        intent.get("component_responsibilities")
    )
    context = _context(intent)
    completed = [_system_row(row, context=context, title=title, explicit=bool(rows)) for row in rows]
    completed = [row for row in completed if row]
    if not completed:
        completed = _derived_system_rows(intent, title=title)
    elif len(completed) < 3 and len(rows) < 2:
        completed = _complete_sparse_system_topology(completed, intent, title=title)
    return list(unique_text(completed))[:8]


def system_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in confirmed_text_values(intent.get("internal_systems")):
        labels.append(_system_label_head(row))
    return [label for label in labels if label]


def state_label(value: str, *, title: str) -> str:
    text = _clean(value)
    if text:
        shared_label = _domain_object_label(text, fallback="")
        if shared_label:
            return shared_label
        first = re.split(r"[.;]", text, maxsplit=1)[0]
        match = re.search(
            r"\b(?:state object is|primary state object is|is)\s+(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)",
            first,
            re.IGNORECASE,
        )
        if match:
            return _title_case(match.group("label"))
        match = re.match(
            r"^(?:the|an|a)\s+(?P<label>[A-Za-z][A-Za-z0-9 _-]{1,90}?)\s+"
            r"(?:tracks|records|stores|captures|moves|starts|changes)\b",
            first,
            flags=re.IGNORECASE,
        )
        if match:
            return _title_case(match.group("label"))
        if _word_count(first) <= 8:
            return _title_case(first)
    return f"{_focus_label(title)} state"


def _system_row(row: str, *, context: str, title: str, explicit: bool = False) -> str:
    raw = _clean(row)
    if not raw:
        return ""
    if " - " in raw and "—" not in raw and ":" not in raw:
        canonical_name = _flatten_parenthetical_label(confirmed_system_name(raw))
        canonical_description = _clean_system_description(confirmed_system_description(raw))
        if (
            canonical_name
            and canonical_description
            and canonical_name != canonical_description
            and _system_description_is_enough(canonical_description)
        ):
            return f"{_title_case_system_name(canonical_name)} — {canonical_description.rstrip('.')}"
    if "—" in raw or ":" in raw:
        name, description = re.split(r"\s+—\s+|:\s*", raw, maxsplit=1)
        name = _flatten_parenthetical_label(name)
        description = _clean_system_description(description)
        if _system_description_is_enough(description):
            return f"{_title_case_system_name(name)} — {description.rstrip('.')}"
    relative_name, relative_description = _relative_system_label_parts(raw)
    if relative_name and _system_description_is_enough(relative_description):
        return f"{_title_case_system_name(relative_name)} — {_clean_system_description(relative_description)}"
    name = _system_label(raw, title=title)
    if not name:
        return ""
    clause = _best_context_clause(name, context)
    if explicit:
        return f"{name} — {_explicit_system_description(name, context_clause=clause)}"
    if clause:
        return (
            f"{name} — owns its accepted inputs, blocked states, produced outputs, and handoff evidence. "
            f"Context: {_short(clause, limit=180)}"
        )
    return f"{name} — owns input capture, state change, validation evidence, blocked states, and handoff for the accepted {title.lower()} path"


def _explicit_system_description(name: str, *, context_clause: str) -> str:
    topic = _system_topic(name)
    lowered = name.casefold()
    path = "the accepted first path"
    if any(token in lowered for token in ("generator", "generation", "planner", "recommend", "suggest")):
        return f"generates {topic} for {path} and keeps required inputs, blocked cases, visible result, and handoff evidence clear"
    if any(token in lowered for token in ("assessment", "scoring", "model", "estimation", "calculation")):
        return f"evaluates {topic} for {path} and keeps input facts, result explanation, blocked cases, and review evidence together"
    if any(token in lowered for token in ("tracker", "history", "log", "store", "record")):
        return f"maintains {topic} state for {path} with actor, source, status, result, blocker, and recovery context visible"
    if any(token in lowered for token in ("rule", "guard", "safety", "escalation", "policy")):
        return f"checks {topic} rules for {path} and makes the reason, threshold, blocked state, and recovery action reviewable"
    if any(token in lowered for token in ("notification", "reminder", "handoff", "referral")):
        return f"delivers {topic} handoff for {path} without hiding the source context, owner, next action, or blocked state"
    if context_clause:
        return "owns the component responsibility named by the accepted intent while keeping required inputs, visible result, blockers, and proof evidence clear"
    return f"owns {topic} behavior for {path} with required input, visible result, blocker, and proof evidence clear"


def _system_topic(name: str) -> str:
    text = _clean(name).casefold().replace("/", " and ").replace("-", " ")
    text = re.sub(
        r"\b(?:service|services|system|systems|engine|engines|store|stores|surface|surfaces|"
        r"adapter|adapters|queue|queues|view|views|flow|flows|tracker|trackers|ledger|ledgers|"
        r"module|modules|dashboard|dashboards|record|records|manager|managers|generator|generators|"
        r"generation|planner|planners|recommender|recommenders|suggester|suggesters)\b",
        "",
        text,
    )
    return _clean(text).strip(" -_/") or _clean(name).casefold() or "component"


def _system_description_is_enough(value: str) -> bool:
    text = _clean(value)
    if _word_count(text) >= 5:
        return True
    return bool(
        _word_count(text) >= 3
        and re.search(
            r"\b(?:captures?|capturing|validates?|validating|computes?|computing|evaluates?|evaluating|"
            r"produces?|producing|proposes?|proposing|recommends?|recommending|suggests?|suggesting|"
            r"returns?|returning|routes?|routing|records?|recording|stores?|storing|"
            r"configures?|configuring|owned\s+by|keeps?)\b",
            text,
            re.IGNORECASE,
        )
    )


def _derived_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    focus = _focus_label(title)
    state = state_label(_clean(intent.get("state_object")), title=title)
    proof = _short(_clean(intent.get("proof_boundary")), fallback="the release proof")
    names = [_focus_system_name(focus, suffix) for suffix in _SYSTEM_SUFFIXES]
    descriptions = [
        f"owns identity, current status, version history, and traceable changes for {state}",
        "presents the current state, missing-information guidance, user-facing confirmation, and next useful action without owning source records",
        f"records the result, validation status, release decision, failure reason, and reviewable proof: {proof}",
        "shows the visible result, known limits, and recovery conditions before broader rollout",
    ]
    return [f"{_title_case_system_name(name)} — {description.rstrip('.')}" for name, description in zip(names, descriptions)]


def _complete_sparse_system_topology(rows: list[str], intent: Mapping[str, Any], *, title: str) -> list[str]:
    """Add semantic obligations when explicit systems under-model the first release."""

    completed = list(rows)
    candidates = _sparse_system_obligation_rows(intent, title=title)
    for candidate in candidates:
        if len(completed) >= 3:
            break
        if not _system_obligation_duplicates(candidate, completed):
            completed.append(candidate)
    return completed


def _sparse_system_obligation_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    state = state_label(_clean(intent.get("state_object")), title=title)
    proof = _clean(intent.get("proof_boundary"))
    first_path = _clean(intent.get("first_path"))
    proof_clause = _short(proof, fallback="release proof", limit=160).rstrip(".")
    path_clause = _short(first_path, fallback=f"the accepted {title.lower()} path", limit=180).rstrip(".")
    rows: list[str] = []
    if proof_clause:
        rows.append(
            f"{_proof_system_name(proof_clause, title=title)} — maintains reviewable proof covering {_definite_clause(proof_clause)} for the accepted first path, including decision status, blocked reason, evidence source, and handoff context"
        )
    if state:
        rows.append(
            f"{_title_case_system_name(state)} State Ledger — maintains {state.lower()} status, ownership, evidence links, version history, and recovery context for {path_clause}"
        )
    rows.append(
        f"{_focus_system_name(_focus_label(title), 'release guardrail')} — confirms the accepted path result, unresolved blockers, and first-release limits before broader rollout"
    )
    return rows


def _proof_system_name(proof_clause: str, *, title: str) -> str:
    proof = _clean(proof_clause).strip(" .")
    if not proof:
        return _focus_system_name(_focus_label(title), "proof ledger")
    name = _title_case_system_name(_short(proof, fallback="release proof", limit=80).rstrip("."))
    if re.search(r"\b(?:proof|evidence|ledger|log|record|review|decision|custody)\b", name, flags=re.IGNORECASE):
        return name
    return f"{name} Proof Ledger"


def _definite_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "the accepted proof boundary"
    first = text.split(maxsplit=1)[0].strip(".,;:").casefold()
    if first in {"a", "an", "the", "this", "that", "their", "one"}:
        return text
    return f"the {text}"


def _system_obligation_duplicates(candidate: str, rows: list[str]) -> bool:
    candidate_terms = _semantic_terms(candidate.split("—", 1)[0])
    if not candidate_terms:
        return True
    for row in rows:
        row_terms = _semantic_terms(row.split("—", 1)[0])
        if not row_terms:
            continue
        overlap = candidate_terms & row_terms
        if len(overlap) >= min(3, len(candidate_terms)):
            return True
    return False


def _focus_system_name(focus: str, suffix: str) -> str:
    focus_text = _clean(focus)
    focus_terms = {term.casefold().strip(".,;:") for term in focus_text.split() if term.strip(".,;:")}
    suffix_words = [word for word in _clean(suffix).split() if word.casefold().strip(".,;:") not in focus_terms]
    suffix_text = " ".join(suffix_words).strip()
    if not suffix_text:
        return focus_text
    return f"{focus_text} {suffix_text}".strip()


def _clean_system_description(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(r"^(?:hold|holds|holding)\s+", "maintains ", text, flags=re.IGNORECASE)
    text = normalize_binary_action_control_phrase(text)
    text = re.sub(
        r"\b(?:captures?|capturing)\s+user\s+actions?\b",
        "captures the product interaction",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:explains?|explaining)\s+blocked\s+states?\b",
        "explains missing or invalid information",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*(?:,?\s*and\s+)?(?:keeps?|keeping)\s+the\s+next\s+visible\s+step\s+tied\s+to\s*:\s*[^.]+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*,\s*,\s*", ", ", text)
    text = re.sub(r"\s*,\s*(?:and\s*)?$", "", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .,;:")


def _system_label_head(value: str) -> str:
    head = _flatten_parenthetical_label(_clean(value.split("—", 1)[0].split(":", 1)[0]))
    head = _strip_relative_system_label_clause(head)
    split = re.search(
        r"\s+(?=(?:owned\s+by|captures?|capturing|validates?|validating|computes?|computing|evaluates?|evaluating|"
        r"produces?|producing|proposes?|proposing|recommends?|recommending|suggests?|suggesting|"
        r"returns?|returning|routes?|routing|records?|recording|stores?|storing|"
        r"shows?|showing|renders?|rendering|generates?|generating|calculates?|calculating|"
        r"configures?|configuring|groups?|grouping|aligns?|aligning|tracks?|tracking|manages?|managing)\b)",
        head,
        flags=re.IGNORECASE,
    )
    if split:
        head = head[: split.start()].strip(" .:-")
    return head


def _system_label(row: str, *, title: str) -> str:
    raw = _flatten_parenthetical_label(_clean(row))
    raw = re.sub(r"^(?:a|an|the)\s+", "", raw, flags=re.IGNORECASE)
    raw = _strip_relative_system_label_clause(raw)
    raw = _repair_system_label_tail(raw)
    if _word_count(raw) > 14:
        raw = _compact_system_label(raw)
    return _title_case_system_name(raw or f"{_focus_label(title)} system")


def _title_case_system_name(value: str) -> str:
    text = _clean(value).strip(" .,:;")
    text = re.sub(
        r"^Reviewer\s+(?=(?:Dashboard|Export|Surface|View|Portal|Report|Package)\b)",
        "Review ",
        text,
        flags=re.IGNORECASE,
    )
    words: list[str] = []
    for index, raw in enumerate(text.split()):
        word = raw.strip()
        lower = word.casefold()
        if index > 0 and lower in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
            words.append(lower)
        elif _preserve_system_slash_token(word):
            words.append("/".join(_title_case_system_token(part) for part in word.split("/") if part))
        elif _preserve_system_hyphen_token(word):
            head, *tail = word.split("-")
            words.append("-".join([_title_case_system_token(head), *tail]))
        else:
            words.append(_title_case(word))
    return _clean(" ".join(words))


def _preserve_system_slash_token(value: str) -> bool:
    if "/" not in value or re.search(r"://|^/", value):
        return False
    lower = value.casefold().strip(".,;:()")
    return lower == "rule/threshold" or all(part.isupper() and len(part) <= 5 for part in value.split("/") if part)


def _preserve_system_hyphen_token(value: str) -> bool:
    if "-" not in value or value.startswith("-") or value.endswith("-"):
        return False
    lower = value.casefold().strip(".,;:()")
    return lower in {
        "conflict-of-interest",
        "reason-code",
        "revision-round",
        "role-based",
        "source-backed",
        "user-facing",
    }


def _title_case_system_token(value: str) -> str:
    token = _clean(value)
    return f"{token[:1].upper()}{token[1:]}" if token else ""


def _strip_relative_system_label_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    head, _body = _relative_system_label_parts(text)
    return head or text


def _relative_system_label_parts(value: str) -> tuple[str, str]:
    text = _clean(value).strip(" .")
    match = re.match(
        r"(?P<head>.+?)\s+(?:that|which|who)\s+(?P<body>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    head = _clean(match.group("head")).strip(" .")
    body = _clean(match.group("body")).strip(" .")
    if _relative_system_head_is_plausible(head) and _word_count(body) >= 2 and looks_like_finite_action(body):
        return head, body
    return "", ""


def _relative_system_head_is_plausible(value: str) -> bool:
    head = _clean(value).strip(" .")
    if not head or _word_count(head) > 12:
        return False
    if looks_like_finite_action(head):
        return False
    if re.search(r"\b(?:because|matter|must|while|still|enough|first path|product)\b", head, flags=re.IGNORECASE):
        return False
    return _word_count(head) >= 2


def _flatten_parenthetical_label(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"\(([^)]{3,160})\)", _parenthetical_label_replacement, text)
    return _clean(text)


def _parenthetical_label_replacement(match: re.Match[str]) -> str:
    body = _clean(match.group(1))
    if "," in body or _word_count(body) > 4:
        return ""
    return f" {body}"


def _repair_system_label_tail(value: str) -> str:
    text = _clean(value).strip(" ,;:.")
    words = text.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "for", "of", "the", "to", "with"}:
        words.pop()
    return " ".join(words).strip(" ,;:.")


def _compact_system_label(value: str) -> str:
    text = _repair_system_label_tail(value)
    if _word_count(text) <= 12:
        return text
    match = re.match(r"(?P<head>.+?\b(?:flow|capture|tracking|tracker|analytics|explanations|guardrails|controls|viewer|dashboard|workspace|workflow|service|engine|ledger|registry|store|journal|planner|generation|management|intake|versioning))\b", text, flags=re.IGNORECASE)
    if match and _word_count(match.group("head")) >= 2:
        return _repair_system_label_tail(match.group("head"))
    words = text.split()[:12]
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "for", "of", "the", "to", "with"}:
        words.pop()
    return " ".join(words)


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
        " ".join(confirmed_text_values(intent.get("human_actors"))),
        " ".join(confirmed_text_values(intent.get("external_systems"))),
        " ".join(confirmed_text_values(intent.get("assumptions"))),
        " ".join(confirmed_text_values(intent.get("ambiguities"))),
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


__all__ = ["completed_system_rows", "state_label", "system_labels"]
