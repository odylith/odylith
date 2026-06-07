"""Internal-system completion for accepted greenfield Product Intent."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text as _title_case
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
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
    if "—" in raw or ":" in raw:
        name, description = re.split(r"\s+—\s+|:\s*", raw, maxsplit=1)
        name = _flatten_parenthetical_label(name)
        description = _clean_system_description(description)
        if _system_description_is_enough(description):
            return f"{_title_case(name)} — {description.rstrip('.')}"
    name = _system_label(raw, title=title)
    if not name:
        return ""
    clause = _best_context_clause(name, context)
    if explicit:
        if clause:
            return f"{name} — {_short(clause, limit=180)}"
        return name
    if clause:
        return (
            f"{name} — owns its accepted inputs, blocked states, produced outputs, and handoff evidence. "
            f"Context: {_short(clause, limit=180)}"
        )
    return f"{name} — owns input capture, state change, validation evidence, blocked states, and handoff for the accepted {title.lower()} path"


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
    names = [f"{focus} {suffix}" for suffix in _SYSTEM_SUFFIXES]
    descriptions = [
        f"owns identity, current status, version history, and traceable changes for {state}",
        "presents the current state, missing-information guidance, user-facing confirmation, and next useful action without owning source records",
        f"records the result, validation status, release decision, failure reason, and reviewable proof: {proof}",
        "shows the visible result, known limits, and recovery conditions before broader rollout",
    ]
    return [f"{_title_case(name)} — {description.rstrip('.')}" for name, description in zip(names, descriptions)]


def _clean_system_description(value: str) -> str:
    text = _clean(value).strip(" .")
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
    raw = _repair_system_label_tail(raw)
    if _word_count(raw) > 14:
        raw = _compact_system_label(raw)
    return _title_case(raw or f"{_focus_label(title)} system")


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
