"""Greenfield Product Story card narration for the Project dashboard."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
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
        _outcome_from_text(first_path)
        or _product_sentence(outcome)
        or _project_line(project, "user or stakeholder outcome")
        or _outcome_from_text(story)
        or _product_sentence(intent.get("state_object"))
    )
    proof = _product_sentence(intent.get("proof_boundary")) or _best_product_sentence(validation)
    non_goals = (
        _project_line(project, "non-goals")
        or _product_items_sentence(intent.get("non_goals"))
        or _proof_exclusion(intent.get("proof_boundary"))
    )
    actor = _actor_title(actors, index=0) or "the primary user"
    participant = _actor_title(actors, index=1) or _actor_title(actors, index=2) or "the next participant"
    return _StoryCardContext(
        title=_display_title(title),
        story=story,
        problem=problem,
        outcome=resolved_outcome,
        first_path=_path_sentence(first_path),
        state_object=_product_sentence(intent.get("state_object")),
        proof_boundary=proof,
        non_goals=non_goals,
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
            return _ensure_period(f"This release stops at {outcome}. It leaves {excluded} for a later release unless those outcomes can be shown just as clearly")
    return _ensure_period(
        f"This release stops at {outcome}. It does not claim every variant, exception, external handoff, or scaled operating path until those outcomes can be explained from the same user-visible result"
    )


def _owned_capabilities_card(ctx: _StoryCardContext) -> str:
    input_focus = _input_focus(ctx.first_path) or "the user request and required context"
    outcome = _outcome_phrase(ctx)
    return _ensure_period(
        f"The product is responsible for the first usable loop: {input_focus}. It turns that activity into {outcome}, shows the result plainly, keeps the underlying record available for follow-up, and does not ask another participant to reconstruct what happened by hand"
    )


def _proof_card(ctx: _StoryCardContext) -> str:
    path = _clean_first_path(ctx.first_path)
    outcome = _outcome_phrase(ctx)
    actor = _participant_phrase(ctx.actor)
    participant = _participant_phrase(ctx.participant)
    if path:
        return _ensure_period(
            f"To prove it works, {actor} must complete the real path and receive {outcome}. The same run must leave enough context for {participant} to understand the result, see why it happened, and decide the next step"
        )
    return _ensure_period(
        f"Proof means {actor} can use {ctx.title} and receive {outcome}; the result must remain explainable enough for {participant} to review or act on it"
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
    domain_source = " ".join([ctx.title, ctx.story, ctx.problem, ctx.first_path, ctx.outcome, ctx.state_object, ctx.non_goals])
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
    text = _path_sentence(value)
    text = re.sub(r"^the\s+first\s+complete\s+path\s+(?:the\s+product\s+must\s+prove\s+)?(?:is|should\s+be)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+first\s+complete\s+path\s+to\s+prove\s+should\s+be:?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+first\s+path\s+(?:is|should\s+be)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+accepted\s+path\s+(?:is|should\s+be)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[^:]{0,80}\bflow\s*:\s*", "", text, flags=re.IGNORECASE)
    if re.search(r"\b1[.)]\s+", text):
        text = _numbered_path_text(text)
    text = re.sub(r"^((?:A|An|The|One)\s+[^,.;]{1,90}?)\s+opens\s+[^,.;]+,\s*", r"\1 ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthey\s+submit\.?\s*", "", text, flags=re.IGNORECASE)
    model = first_path_model(text)
    if model.steps:
        steps = [_story_step(step) for step in model.steps if _story_step(step)]
        if steps:
            steps[0] = _clean_opening_launcher_step(steps[0])
            steps = [step for step in steps if step]
            steps = [_subjectify_story_step(step) for step in steps]
        if len(steps) >= 2 and _same_visible_outcome(steps[-2], steps[-1]):
            steps = steps[:-1]
        if steps:
            return _ensure_period(_join_steps(steps[:5]))
    return _ensure_period(text) if text else ""


def _story_step(value: str) -> str:
    text = _product_sentence(value).strip(" .")
    if re.match(r"^(?:this|the)\s+.+\bvisible[- ]result\b", text, flags=re.IGNORECASE):
        return ""
    text = re.sub(r"^on\s+save,\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.sub(
        r"\s+and\s+the\s+(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        " and the ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+[–—-]\s+(?P<detail>[^–—-]+?)\s+[–—-]\s*$", r" with \g<detail>", text)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.IGNORECASE)
    text = re.sub(r"\balongside\b", "with", text, flags=re.IGNORECASE)
    text = _normalize_embedded_action_verbs(text)
    if re.fullmatch(r"(?:they|the\s+user|user|the\s+actor|actor)\s+submits?", text, flags=re.IGNORECASE):
        return ""
    if re.fullmatch(r"on\s+save", text, flags=re.IGNORECASE):
        return ""
    return text


def _clean_opening_launcher_step(value: str) -> str:
    text = _product_sentence(value).strip(" .")
    actor_open_then = re.sub(
        r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant|owner|requester|applicant|performer))\s+opens\s+[^,.;]+?\s+and\s+(.+)$",
        r"\1 \2",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    if actor_open_then != text:
        text = actor_open_then
    else:
        text = re.sub(
            r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant|owner|requester|applicant|performer))\s+opens\s+[^,.;]+$",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    text = re.sub(r"^((?:the\s+)?product|(?:the\s+)?system|(?:the\s+)?app)\s+opens\s+[^,.;]+(?:\s+and\s+)?", "", text, count=1, flags=re.IGNORECASE)
    if re.match(r"^user\s+", text, flags=re.IGNORECASE):
        text = f"the {text[:1].lower()}{text[1:]}"
    return _lower_first(_clean(text).strip(" ."))


def _subjectify_story_step(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    subject_action = re.match(
        r"^(?P<subject>(?:a|the)\s+(?:user|person|customer|actor|operator|participant|owner|requester|applicant|performer))\s+"
        r"(?P<verb>add|adds|answer|answers|capture|captures|choose|chooses|click|clicks|dismiss|dismisses|enter|enters|log|logs|record|records|save|saves|select|selects|submit|submits|tap|taps)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if subject_action:
        verb = third_person_action_verb(subject_action.group("verb"))
        tail = _third_person_compound_tail(subject_action.group("tail"))
        return f"{_lower_first(subject_action.group('subject'))} {verb}{tail}".strip()
    adverb_action = re.match(
        r"^(?P<prefix>immediately|later|then)\s+(?P<verb>receive|receives|see|sees|view|views|read|reads|get|gets)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if adverb_action:
        verb = third_person_action_verb(adverb_action.group("verb"))
        return f"the user {adverb_action.group('prefix').casefold()} {verb}{adverb_action.group('tail')}".strip()
    product_action = re.match(
        r"^(?P<verb>compare|compares|mark|marks|prompt|prompts|return|returns|show|shows|surface|surfaces|update|updates)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if product_action:
        verb = third_person_action_verb(product_action.group("verb"))
        return f"the product {verb}{product_action.group('tail')}".strip()
    action = re.match(
        r"^(?P<prefix>manually\s+|periodically\s+|regularly\s+)?"
        r"(?P<verb>add|adds|answer|answers|capture|captures|choose|chooses|click|clicks|dismiss|dismisses|enter|enters|log|logs|record|records|save|saves|select|selects|submit|submits|tap|taps)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if action:
        prefix = action.group("prefix") or ""
        verb = third_person_action_verb(action.group("verb"))
        tail = _third_person_compound_tail(action.group("tail"))
        if prefix:
            return f"{prefix.casefold()}{verb}{tail}".strip()
        return f"the user {prefix}{verb}{tail}".strip()
    return text


def _same_visible_outcome(previous: str, current: str) -> bool:
    if re.search(r"\b(?:accept|accepts|click|clicks|choose|chooses|dismiss|dismisses)\b", current, flags=re.IGNORECASE):
        return False
    previous_terms = set(_terms(previous))
    current_terms = set(_terms(current))
    return bool(current_terms and len(previous_terms & current_terms) >= min(3, len(current_terms)))


def _join_steps(steps: Sequence[str]) -> str:
    rows = [step.strip(" .") for step in steps if step.strip(" .")]
    if not rows:
        return ""
    rows = _join_subjectless_continuations(rows)
    rows = [rows[0], *[_upper_first(row) for row in rows[1:]]] if rows else rows
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]}. {rows[1]}"
    return ". ".join(rows)


def _join_subjectless_continuations(steps: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for step in steps:
        if rows:
            same_subject_tail = _same_subject_continuation(rows[-1], step)
            if same_subject_tail:
                rows[-1] = f"{rows[-1]} and {same_subject_tail}"
                continue
        if rows and _subjectless_action_continuation(step):
            rows[-1] = f"{rows[-1]} and {_lower_first(step)}"
            continue
        rows.append(step)
    return rows


def _same_subject_continuation(previous: str, current: str) -> str:
    previous_text = _clean(previous).strip(" .")
    current_text = _clean(current).strip(" .")
    for subject in ("the user", "the owner", "the operator", "the participant", "the customer", "the applicant"):
        if not previous_text.casefold().startswith(f"{subject} "):
            continue
        prefix = f"{subject} "
        if not current_text.casefold().startswith(prefix):
            continue
        tail = current_text[len(prefix) :].strip(" .")
        if re.match(r"^(?:manually|periodically|regularly)\s+", tail, flags=re.IGNORECASE) and _subjectless_action_continuation(tail):
            return _lower_first(tail)
    return ""


def _subjectless_action_continuation(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if re.match(r"^(?:a|an|the|one|this|that)\s+", text, flags=re.IGNORECASE):
        return False
    if re.match(r"^[A-Z][A-Za-z0-9_-]{2,}\s+", text) and not re.match(
        r"^(?:Manually|Periodically|Regularly)\b",
        text,
    ):
        return False
    return bool(
        re.match(
            r"^(?:manually\s+|periodically\s+|regularly\s+)?"
            r"(?:adds?|attaches?|chooses?|clicks?|enters?|logs?|records?|reviews?|saves?|selects?|submits?|updates?)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


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
    text = re.split(r"\.\s+on\s+save\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .") or text
    segments = [
        part.strip(" .")
        for part in re.split(r"(?<=[.!?])\s+|,\s+|\bthen\b|\band finally\b", text, flags=re.IGNORECASE)
        if part.strip(" .")
    ]
    useful = [
        segment
        for segment in segments[:4]
        if not re.search(r"\b(?:shows?|displays?|returns?|produces?|receives?|sees?|review|act)\b", segment, flags=re.IGNORECASE)
        and not re.fullmatch(r"on\s+save", segment, flags=re.IGNORECASE)
        and not _looks_like_internal_processing_step(segment)
        and _looks_like_user_input_step(segment)
    ]
    if not useful:
        useful = segments[:2]
    phrase = _join_input_segments(useful[:3]).strip(" .")
    return _lower_first(phrase)


def _join_input_segments(values: Sequence[str]) -> str:
    rows = [
        _lower_first(_normalize_embedded_action_verbs(_clean(value).strip(" .")))
        for value in values
        if _clean(value).strip(" .")
    ]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]}, then {rows[1]}"
    return f"{', '.join(rows[:-1])}, then {rows[-1]}"


def _normalize_embedded_action_verbs(value: str) -> str:
    text = _clean(value).strip(" .")
    return re.sub(
        r",\s+and\s+(manually\s+)?(answers?|logs?|enters?|selects?|submits?|saves?|chooses?|clicks?|accepts?|dismisses?|records?|captures?|reviews?)\b",
        r" and \1\2",
        text,
        flags=re.IGNORECASE,
    )


def _third_person_compound_tail(value: str) -> str:
    return re.sub(
        r"\b(and|or)\s+(answer|answers|capture|captures|choose|chooses|click|clicks|dismiss|dismisses|enter|enters|log|logs|record|records|save|saves|select|selects|submit|submits|tap|taps)\b",
        lambda match: match.group(0) if match.group(2)[:1].isupper() else f"{match.group(1)} {third_person_action_verb(match.group(2))}",
        value,
        flags=re.IGNORECASE,
    )


def _looks_like_internal_processing_step(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    system_verb = (
        r"calculates?|computes?|derives?|evaluates?|forecasts?|generates?|optimizes?|pulls?|renders?|returns?|runs?|"
        r"scores?|updates?|validates?"
    )
    if re.match(rf"^(?:the\s+)?(?:product|system|app|application|service|platform|tool)\s+{system_verb}\b", text, flags=re.IGNORECASE):
        return True
    return bool(re.match(rf"^[A-Z][A-Za-z0-9_-]{{2,}}\s+{system_verb}\b", text))


def _looks_like_user_input_step(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:accept|accepts|add|adds|attach|attaches|choose|chooses|click|clicks|complete|completes|"
            r"answer|answers|capture|captures|connect|connects|create|creates|dismiss|dismisses|edit|edits|enter|enters|log|logs|record|records|save|saves|"
            r"select|selects|submit|submits|update|updates)\b",
            _clean(value),
            flags=re.IGNORECASE,
        )
    )


def _outcome_phrase(ctx: _StoryCardContext) -> str:
    for value in (ctx.outcome, _outcome_from_text(ctx.story), _outcome_from_text(ctx.first_path), ctx.state_object):
        text = _product_sentence(value).rstrip(".")
        if text:
            return _outcome_as_noun(_limit_card(text, limit=180).rstrip("."))
    return "a clear result that the next participant can understand"


def _outcome_as_noun(value: str) -> str:
    text = _lower_first(value).strip(" .")
    product_result = re.match(
        r"^(?:the\s+)?(?:product|system|app|application|tool|dashboard|screen|view)\s+"
        r"(?:displays?|offers?|produces?|returns?|shows?)\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if product_result:
        return _clean(product_result.group("object")).strip(" .")
    visible = re.match(
        r"^(?:the\s+)?[a-z0-9][a-z0-9 ,&/'()-]{1,70}?\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if visible:
        return _clean(visible.group("object")).strip(" .")
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
    text = _path_sentence(value)
    if not text:
        return ""
    model = first_path_model(text)
    if model.visible_outcome:
        visible = _story_step(model.visible_outcome)
        if visible:
            return visible
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
    text = re.sub(r"\s+(?:are|is)\s+out\s+of\s+scope\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:is|are)\s+(?:a\s+)?later\s+enhancements?\b.*$", "", text, flags=re.IGNORECASE)
    text = _clean(text).strip(" .")
    if not text or any(re.search(pattern, text, re.IGNORECASE) for pattern in _GENERIC_CARD_PATTERNS):
        return ""
    return _lower_first(text)


def _proof_exclusion(value: Any) -> str:
    text = _clean(display_text(value))
    if not text:
        return ""
    sentences = _sentences(text)
    rows = [
        sentence
        for sentence in sentences
        if re.search(r"\b(?:out\s+of\s+scope|later|not\s+claim|does\s+not\s+claim|outside)\b", sentence, flags=re.IGNORECASE)
    ]
    if rows:
        return " ".join(rows)
    match = re.search(r"(?P<tail>[^.]{8,260}\bout\s+of\s+scope\b[^.]*)(?:\.|$)", text, flags=re.IGNORECASE)
    return match.group("tail") if match else ""


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
    text = re.sub(r"^on\s+save,\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\s+and\s+the\s+(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        " and the ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+[–—-]\s+(?P<detail>[^–—-]+?)\s+[–—-]\s*$", r" with \g<detail>", text)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.IGNORECASE)
    text = re.sub(r"\balongside\b", "with", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .")


def _path_sentence(value: Any) -> str:
    text = _clean(display_text(value))
    text = text.replace("`", "")
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\b(?:radar|registry|atlas|compass|casebook)\b.+$", "", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .")


def _product_items_sentence(value: Any) -> str:
    rows = [_product_sentence(item) for item in strings(value)]
    rows = [row.rstrip(".") for row in rows if row]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _actor_title(actors: Sequence[tuple[str, str, str]], *, index: int) -> str:
    if len(actors) <= index:
        return ""
    title = _clean(display_text(actors[index][1])).strip(" .")
    title = re.split(r"\b(?:who|that|with|and)\b", title, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .,:;")
    words = title.split()
    if len(words) > 6:
        title = " ".join(words[:6])
    return title[:1].upper() + title[1:] if title else ""


def _participant_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "the relevant participant"
    if re.match(r"^(?:a|an|the)\s+", text, flags=re.IGNORECASE):
        return text
    return f"the {text}"


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
