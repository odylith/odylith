"""Greenfield Product Story card narration for the Project dashboard."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

from odylith.runtime.project_intelligence.utils import display_text, sentence, strings


_CARD_LABELS = ("User Problem", "First Path", "Product Boundary", "Owned Capabilities", "Proof")

_GENERIC_CARD_PATTERNS = (
    r"\baccepted\s+first\s+path\b",
    r"\badditional\s+accepted\s+capabilities\b",
    r"\bbroader\s+variants\s+stay\s+outside\b",
    r"\bcomponent(?:s)?\b",
    r"\bgovernance\b",
    r"\bimplementation\b",
    r"\bproof\s+boundary\s+blocks\b",
    r"\bradar|registry|atlas|compass|casebook\b",
    r"\bvalidation,\s*replay,\s*access,\s*privacy,\s*safety\b",
)

_STOPWORDS = {
    "about",
    "accepted",
    "after",
    "against",
    "before",
    "boundary",
    "broader",
    "card",
    "complete",
    "does",
    "during",
    "every",
    "first",
    "from",
    "have",
    "into",
    "keeps",
    "must",
    "only",
    "other",
    "path",
    "people",
    "product",
    "release",
    "result",
    "same",
    "state",
    "system",
    "their",
    "there",
    "they",
    "this",
    "through",
    "until",
    "using",
    "when",
    "where",
    "which",
    "with",
    "without",
}


@dataclass(frozen=True)
class _StoryCardContext:
    title: str
    story: str
    problem: str
    outcome: str
    first_path: str
    state_object: str
    proof_boundary: str
    non_goals: str
    actor: str
    participant: str


def build_greenfield_story_cards(
    *,
    title: str,
    intent: Mapping[str, Any],
    project: Mapping[str, Any],
    objective: str,
    outcome: str,
    first_path: str,
    actors: Sequence[tuple[str, str, str]],
    validation: Sequence[str] = (),
) -> list[dict[str, str]]:
    """Return product-specific dashboard cards from accepted intent, never component labels."""

    ctx = _context(
        title=title,
        intent=intent,
        project=project,
        objective=objective,
        outcome=outcome,
        first_path=first_path,
        actors=actors,
        validation=validation,
    )
    rows = [
        ("User Problem", _user_problem_card(ctx)),
        ("First Path", _first_path_card(ctx)),
        ("Product Boundary", _product_boundary_card(ctx)),
        ("Owned Capabilities", _owned_capabilities_card(ctx)),
        ("Proof", _proof_card(ctx)),
    ]
    return [{"label": label, "body": _repair_card(label=label, body=body, ctx=ctx)} for label, body in rows]


def _context(
    *,
    title: str,
    intent: Mapping[str, Any],
    project: Mapping[str, Any],
    objective: str,
    outcome: str,
    first_path: str,
    actors: Sequence[tuple[str, str, str]],
    validation: Sequence[str],
) -> _StoryCardContext:
    story = _product_sentence(intent.get("product_story")) or _product_sentence(objective)
    problem = _product_sentence(intent.get("problem")) or _project_line(project, "problem") or _problem_from_story(story)
    resolved_outcome = (
        _product_sentence(outcome)
        or _project_line(project, "user or stakeholder outcome")
        or _outcome_from_text(story)
        or _outcome_from_text(first_path)
        or _product_sentence(intent.get("state_object"))
    )
    proof = _product_sentence(intent.get("proof_boundary")) or _best_product_sentence(validation)
    actor = _actor_title(actors, index=0) or "the primary user"
    participant = _actor_title(actors, index=1) or _actor_title(actors, index=2) or "the next participant"
    return _StoryCardContext(
        title=_display_title(title),
        story=story,
        problem=problem,
        outcome=resolved_outcome,
        first_path=_product_sentence(first_path),
        state_object=_product_sentence(intent.get("state_object")),
        proof_boundary=proof,
        non_goals=_project_line(project, "non-goals") or _product_sentence(intent.get("non_goals")),
        actor=actor,
        participant=participant,
    )


def _user_problem_card(ctx: _StoryCardContext) -> str:
    source = ctx.problem or ctx.story
    if source and _specific_enough(source, ctx):
        return _limit_card(_ensure_period(source), limit=520)
    outcome = _lower_first(_outcome_phrase(ctx))
    actor = _lower_first(ctx.actor)
    return _ensure_period(
        f"{ctx.actor} needs a clear way to reach {outcome}. Without {ctx.title}, {actor} has to piece together "
        "inputs, decisions, and follow-up by hand, which creates delay, uncertainty, and avoidable mistakes."
    )


def _first_path_card(ctx: _StoryCardContext) -> str:
    path = _clean_first_path(ctx.first_path)
    outcome = _outcome_phrase(ctx)
    if path and _mentions_outcome(path, outcome):
        return _limit_card(_ensure_period(_upper_first(path)), limit=560)
    if path:
        return _ensure_period(f"{_upper_first(path).rstrip('.')}. The path is complete only when the product produces {outcome}")
    return _ensure_period(f"{ctx.actor} uses {ctx.title} to move from the first request to {outcome}")


def _product_boundary_card(ctx: _StoryCardContext) -> str:
    outcome = _outcome_phrase(ctx)
    if ctx.non_goals:
        excluded = _clean_boundary_exclusion(ctx.non_goals)
        if excluded:
            return _ensure_period(f"This release stops at {outcome}. It does not promise {excluded} until those outcomes can be proven with the same clarity")
    return _ensure_period(
        f"This release stops at {outcome}. It does not claim every variant, exception, external handoff, or scaled operating path until those outcomes can be explained from the same user-visible result"
    )


def _owned_capabilities_card(ctx: _StoryCardContext) -> str:
    input_focus = _input_focus(ctx.first_path) or "the user request and required context"
    outcome = _outcome_phrase(ctx)
    return _ensure_period(
        f"The product owns the whole path: {input_focus}. It gathers the necessary context, turns that activity into {outcome}, shows the result in language the user can understand, and keeps the record available for follow-up"
    )


def _proof_card(ctx: _StoryCardContext) -> str:
    path = _clean_first_path(ctx.first_path)
    outcome = _outcome_phrase(ctx)
    participant = _lower_first(ctx.participant)
    if path:
        return _ensure_period(
            f"To prove it works, {ctx.actor} must complete the real path and receive {outcome}. The same run must leave enough context for {participant} to understand the result, see why it happened, and decide the next step"
        )
    return _ensure_period(
        f"Proof means {ctx.actor} can use {ctx.title} and receive {outcome}; the result must remain explainable enough for {participant} to review or act on it"
    )


def _repair_card(*, label: str, body: str, ctx: _StoryCardContext) -> str:
    text = _limit_card(_ensure_period(body), limit=620)
    if not _weak_card(text, ctx):
        return text
    fallback = {
        "User Problem": _user_problem_card(ctx),
        "First Path": _first_path_card(ctx),
        "Product Boundary": _product_boundary_card(ctx),
        "Owned Capabilities": _owned_capabilities_card(ctx),
        "Proof": _proof_card(ctx),
    }.get(label, text)
    fallback = _limit_card(_ensure_period(fallback), limit=620)
    if not _weak_card(fallback, ctx):
        return fallback
    outcome = _outcome_phrase(ctx)
    return _ensure_period(f"{ctx.title} is useful when {ctx.actor} can reach {outcome} and {ctx.participant} can understand what happened next")


def _weak_card(value: str, ctx: _StoryCardContext) -> bool:
    text = _clean(value)
    if len(text.split()) < 18:
        return True
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in _GENERIC_CARD_PATTERNS):
        return True
    if _specific_term_count(text, ctx) < 3:
        return True
    if text.count(",") >= 5 and len(re.findall(r"\b(?:accepts?|checks?|chooses?|creates?|does|enters?|gives|keeps|makes|produces?|records?|returns?|reviews?|sends?|shows?|uses)\b", text, flags=re.IGNORECASE)) < 2:
        return True
    return False


def _specific_enough(value: str, ctx: _StoryCardContext) -> bool:
    return len(_clean(value).split()) >= 16 and _specific_term_count(value, ctx) >= 3


def _specific_term_count(value: str, ctx: _StoryCardContext) -> int:
    domain_source = " ".join([ctx.title, ctx.story, ctx.problem, ctx.first_path, ctx.outcome, ctx.state_object])
    domain_terms = set(_terms(domain_source))
    return len(set(_terms(value)) & domain_terms)


def _terms(value: str) -> list[str]:
    rows: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(value).casefold()):
        token = raw.replace("_", "-").strip("-")
        if len(token) < 4 or token in _STOPWORDS:
            continue
        if token.endswith("s") and len(token) > 5:
            token = token[:-1]
        rows.append(token)
    return list(dict.fromkeys(rows))


def _clean_first_path(value: str) -> str:
    text = _product_sentence(value)
    text = re.sub(r"^the\s+first\s+complete\s+path\s+(?:the\s+product\s+must\s+prove\s+)?(?:is|should\s+be)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+first\s+complete\s+path\s+to\s+prove\s+should\s+be:?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+first\s+path\s+(?:is|should\s+be)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+accepted\s+path\s+(?:is|should\s+be)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[^:]{0,80}\bflow\s*:\s*", "", text, flags=re.IGNORECASE)
    if re.search(r"\b1[.)]\s+", text):
        text = _numbered_path_text(text)
    text = re.sub(r"^((?:A|An|The|One)\s+[^,.;]{1,90}?)\s+opens\s+[^,.;]+,\s*", r"\1 ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthey\s+submit\.?\s*", "the product accepts the completed request. ", text, flags=re.IGNORECASE)
    return _ensure_period(text) if text else ""


def _numbered_path_text(value: str) -> str:
    parts = re.split(r"\s+\d+[.)]\s+", f" {value}")
    steps = [_clean_numbered_step(part) for part in parts[1:]]
    steps = [step for step in steps if step]
    if not steps:
        return value
    if len(steps) == 1:
        return steps[0]
    if len(steps) == 2:
        return f"{steps[0]}, then {steps[1]}"
    return f"{', '.join(steps[:-1])}, and finally {steps[-1]}"


def _clean_numbered_step(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(
        r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant))\s+opens\s+[^,.;]+?\s+and\s+(.+)$",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant))\s+opens\s+[^,.;]+$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^((?:the\s+)?product|(?:the\s+)?system|(?:the\s+)?app)\s+opens\s+[^,.;]+(?:\s+and\s+)?", "", text, flags=re.IGNORECASE)
    text = _clean(text).strip(" .")
    if re.match(r"^user\s+", text, flags=re.IGNORECASE):
        text = f"the {text[:1].lower()}{text[1:]}"
    return _lower_first(text)


def _input_focus(value: str) -> str:
    text = _clean_first_path(value).rstrip(".")
    if not text:
        return ""
    segments = [part.strip(" .") for part in re.split(r",\s+|\bthen\b|\band finally\b", text, flags=re.IGNORECASE) if part.strip(" .")]
    useful = [
        segment
        for segment in segments[:4]
        if not re.search(r"\b(?:shows?|displays?|returns?|produces?|receives?|sees?|review|act)\b", segment, flags=re.IGNORECASE)
    ]
    if not useful:
        useful = segments[:2]
    phrase = ", ".join(useful[:3]).strip(" .")
    return _lower_first(phrase)


def _outcome_phrase(ctx: _StoryCardContext) -> str:
    for value in (ctx.outcome, _outcome_from_text(ctx.story), _outcome_from_text(ctx.first_path), ctx.state_object):
        text = _product_sentence(value).rstrip(".")
        if text:
            return _outcome_as_noun(_limit_card(text, limit=180).rstrip("."))
    return "a clear result that the next participant can understand"


def _outcome_as_noun(value: str) -> str:
    text = _lower_first(value).strip(" .")
    match = re.match(r"^(?P<article>a|an|the)\s+(?P<subject>[a-z0-9][a-z0-9 ,&/'()-]{1,90}?)\s+can\s+(?P<verb>.+)$", text, flags=re.IGNORECASE)
    if match:
        article = match.group("article").casefold()
        subject = _clean(match.group("subject")).strip(" .")
        verb = _clean(match.group("verb")).strip(" .")
        if subject and verb:
            return f"a result that lets {article} {subject} {verb}"
    match = re.match(r"^(?P<subject>[a-z0-9][a-z0-9 ,&/'()-]{1,70}?)\s+can\s+(?P<verb>.+)$", text, flags=re.IGNORECASE)
    if match:
        subject = _clean(match.group("subject")).strip(" .")
        verb = _clean(match.group("verb")).strip(" .")
        if subject and verb:
            return f"a result that lets {subject} {verb}"
    return text


def _outcome_from_text(value: str) -> str:
    text = _product_sentence(value)
    if not text:
        return ""
    sentences = _sentences(text)
    outcome_markers = r"\b(?:available|decision|displays?|explains?|made\s+available|offers?|outcome|produces?|records?|returns?|result|shows?|summary|visible)\b"
    for row in reversed(sentences):
        if re.search(outcome_markers, row, re.IGNORECASE):
            return row
    clauses = [part.strip(" .") for part in re.split(r",\s+|\bthen\b", text, flags=re.IGNORECASE) if part.strip(" .")]
    for clause in reversed(clauses):
        if re.search(outcome_markers, clause, re.IGNORECASE):
            return clause
    return ""


def _problem_from_story(value: str) -> str:
    rows = _sentences(value)
    if not rows:
        return ""
    for row in reversed(rows):
        if re.search(r"\b(?:cannot|cost|delay|friction|miss|need|needs|risk|uncertain|without|wants?)\b", row, re.IGNORECASE):
            return row
    return rows[0] if len(rows) == 1 else rows[-1]


def _mentions_outcome(path: str, outcome: str) -> bool:
    outcome_terms = set(_terms(outcome))
    path_terms = set(_terms(path))
    return bool(outcome_terms and len(outcome_terms & path_terms) >= min(2, len(outcome_terms)))


def _clean_boundary_exclusion(value: str) -> str:
    text = _product_sentence(value).rstrip(".")
    text = re.sub(r"^(?:non[- ]?goals?|out\s+of\s+scope)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:in\s+the\s+first\s+release|for\s+release\s+[0-9.]+)\b", "", text, flags=re.IGNORECASE)
    text = _clean(text).strip(" .")
    if not text or any(re.search(pattern, text, re.IGNORECASE) for pattern in _GENERIC_CARD_PATTERNS):
        return ""
    return _lower_first(text)


def _project_line(project: Mapping[str, Any], prefix: str) -> str:
    needle = prefix.strip().casefold()
    for raw in strings(project.get("intent")):
        head, sep, body = str(raw).partition(":")
        if sep and head.strip().casefold() == needle:
            return _product_sentence(body)
    return ""


def _best_product_sentence(values: Sequence[str]) -> str:
    for value in values:
        text = _product_sentence(value)
        if text and not any(re.search(pattern, text, re.IGNORECASE) for pattern in _GENERIC_CARD_PATTERNS):
            return text
    return ""


def _product_sentence(value: Any) -> str:
    text = _clean(display_text(value))
    text = text.replace("`", "")
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\b(?:radar|registry|atlas|compass|casebook)\b.+$", "", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .")


def _actor_title(actors: Sequence[tuple[str, str, str]], *, index: int) -> str:
    if len(actors) <= index:
        return ""
    title = _clean(display_text(actors[index][1])).strip(" .")
    title = re.split(r"\b(?:who|that|with|and)\b", title, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .,:;")
    words = title.split()
    if len(words) > 6:
        title = " ".join(words[:6])
    return title[:1].upper() + title[1:] if title else ""


def _sentences(value: str) -> list[str]:
    return [row.strip() for row in re.split(r"(?<=[.!?])\s+(?=[A-Z])", _clean(value)) if row.strip()]


def _limit_card(value: str, *, limit: int) -> str:
    text = _clean(value)
    if len(text) <= limit:
        return text
    selected: list[str] = []
    total = 0
    for row in _sentences(text):
        row_len = len(row) + (1 if selected else 0)
        if selected and total + row_len > limit:
            break
        if not selected and len(row) > limit:
            break
        selected.append(row)
        total += row_len
    if selected:
        return _ensure_period(" ".join(selected).rstrip("."))
    words: list[str] = []
    total = 0
    for word in text.split():
        next_total = total + len(word) + (1 if words else 0)
        if next_total > limit:
            break
        words.append(word)
        total = next_total
    while words and words[-1].casefold().strip(".,;:") in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        words.pop()
    return _ensure_period(" ".join(words).rstrip(" ,;:"))


def _display_title(value: object) -> str:
    text = _clean(display_text(value)).strip(" -–—:·|.")
    return text or "Project"


def _ensure_period(value: str) -> str:
    text = _clean(value).strip()
    if not text:
        return ""
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _lower_first(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    return text[:1].lower() + text[1:]


def _upper_first(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    return text[:1].upper() + text[1:]


def _clean(value: Any) -> str:
    text = sentence(value)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = ["build_greenfield_story_cards"]
