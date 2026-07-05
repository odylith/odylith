"""Focus broad visible-result lists onto the smallest readable outcome."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_text

_RESULT_SUMMARY_NOUNS = frozenset(
    "answer answers decision decisions explanation explanations insight insights outcome outcomes readout readouts "
    "recommendation recommendations result results report reports status summary summaries view views".split()
)
_RESULT_QUALITY_TERMS = frozenset("actionable clear explainable plain readable specific understandable".split())
_NON_GOAL_TAIL_ACTIONS = frozenset(
    {
        "automating",
        "borrowing",
        "changing",
        "claiming",
        "commanding",
        "including",
        "making",
        "owning",
        "relying",
        "sending",
        "trusting",
    }
)


def focused_visible_result_object(value: str) -> str:
    """Return the most compact result object from a coordinated visible-result list."""

    text = strip_visible_result_non_goal_tail(clean_text(value).strip(" ."))
    if not text:
        return ""
    items = _coordinated_result_items(text)
    terminal_summary = _terminal_final_summary_item(items)
    if terminal_summary:
        return terminal_summary
    if len(items) < 4 and len(text.split()) < 24:
        return text
    ranked = sorted((_focus_score(item), item) for item in items)
    score, candidate = ranked[-1] if ranked else (0, "")
    if score < 4 or len(candidate.split()) < 3 or len(candidate.split()) >= len(text.split()):
        return text
    return candidate


def strip_visible_result_non_goal_tail(value: str) -> str:
    """Drop proof-boundary/non-goal tails from result objects."""

    words = clean_text(value).strip(" .").split()
    if '"' in value:
        return " ".join(words).strip(" .")
    if len(words) < 4:
        return " ".join(words).strip(" .")
    for index, word in enumerate(words[:-1]):
        token = word.casefold().strip(".,:;")
        next_token = words[index + 1].casefold().strip(".,:;")
        if token == "without" and next_token in _NON_GOAL_TAIL_ACTIONS and index >= 2:
            return " ".join(words[:index]).strip(" ,.;:")
    return " ".join(words).strip(" .")


def _coordinated_result_items(value: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in value:
        if char in {'"', "'"}:
            quote = None if quote == char else char if quote is None else quote
        if char == "," and quote is None:
            item = _clean_result_item("".join(current))
            if item:
                items.append(item)
            current = []
            continue
        current.append(char)
    tail = _clean_result_item("".join(current))
    if tail:
        items.append(tail)
    return items


def _clean_result_item(value: str) -> str:
    text = clean_text(value).strip(" ,.;:")
    for connector in ("and ", "or "):
        if text.casefold().startswith(connector):
            return text[len(connector) :].strip(" .")
    return text.strip(" .")


def _terminal_final_summary_item(items: list[str]) -> str:
    if len(items) < 2:
        return ""
    tail = clean_text(items[-1]).strip(" .")
    if not tail.casefold().startswith(("a final ", "an final ", "the final ")):
        return ""
    terms = semantic_terms(tail)
    if "final" not in terms:
        return ""
    if not terms & _RESULT_SUMMARY_NOUNS:
        return ""
    return tail


def _focus_score(value: str) -> int:
    text = clean_text(value)
    terms = semantic_terms(text)
    if not terms:
        return 0
    score = 0
    if terms & _RESULT_SUMMARY_NOUNS:
        score += 3
    if terms & _RESULT_QUALITY_TERMS:
        score += 1
    if '"' in text:
        score += 2
    if " without " in f" {text.casefold()} ":
        score += 1
    return score


__all__ = ["focused_visible_result_object", "strip_visible_result_non_goal_tail"]
