"""Shared semantic hygiene helpers for confirmed greenfield generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token
from odylith.runtime.domain_intelligence.greenfield_text import text_values


_PROVISIONAL_TITLE_RE = re.compile(
    r"""
    (?:\s*[\(\[\{]\s*
        (?:
            working\s+title|
            draft|
            placeholder|
            tbd|
            t\.b\.d\.|
            temporary\s+title|
            title\s+tbd|
            name\s+tbd
        )
        \s*[\)\]\}]\s*)+
    |
    (?:\s*(?:[-:;]|[–—])\s*
        (?:
            working\s+title|
            placeholder|
            tbd|
            temporary\s+title|
            title\s+tbd|
            name\s+tbd
        )
        \s*)$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_TRIVIAL_START_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,40}?\b(?:open|opens|launch|launches|start|starts)\s+"
    r"(?:the\s+)?(?:app|application|product|tool|site|website|screen|page|dashboard)\b\s*$",
    re.IGNORECASE,
)
_TRIVIAL_NAMED_PRODUCT_START_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,40}?\b(?:open|opens|launch|launches|start|starts)\s+"
    r"[A-Z][A-Za-z0-9_-]{2,40}\b\s*$"
)

_MATERIAL_ACTION_RE = re.compile(
    r"\b(?:"
    r"accept|accepts|add|adds|adjust|adjusts|approve|approves|assign|assigns|attach|attaches|calculate|calculates|capture|captures|"
    r"check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|correct|corrects|"
    r"click|clicks|create|creates|delete|deletes|dismiss|dismisses|edit|edits|enter|enters|export|exports|fetch|fetches|finalize|finalizes|"
    r"display|displays|highlight|highlights|import|imports|inspect|inspects|let|lets|log|logs|mark|marks|notify|notifies|persist|persists|play|plays|"
    r"preserve|preserves|produce|produces|publish|publishes|rank|ranks|read|reads|receive|receives|record|records|render|renders|request|requests|review|reviews|"
    r"return|returns|route|routes|run|runs|save|saves|schedule|schedules|screen|screens|see|sees|select|selects|send|sends|share|shares|"
    r"show|shows|stop|stops|store|stores|submit|submits|sync|syncs|tap|taps|track|tracks|update|updates|"
    r"validate|validates|view|views"
    r")\b",
    re.IGNORECASE,
)

_OPEN_PLUS_MATERIAL_RE = re.compile(
    r"^\s*(?P<subject>(?:a|an|the)?\s*[^,.;]{0,80}?)\b(?:open|opens|launch|launches)\b"
    r"(?P<object>\s+[^,.;]{1,80}?)\s+\band\b\s+(?P<material>.+)$",
    re.IGNORECASE,
)

_ACTION_SPLIT_RE = re.compile(r"\s*(?:;|(?<=[.!?])\s+|\s+\bthen\b\s+)\s*", re.IGNORECASE)

_FIRST_PATH_PREFIXES = (
    r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
    r"^the first complete path to prove should be\s*:?\s*",
    r"^first complete path to prove should be\s*:?\s*",
    r"^the first path is\s+",
    r"^first path\s*:?\s*",
)

_NGRAM_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
}

_DEFERRED_MARKERS = (
    "defer",
    "deferred",
    "later",
    "later wave",
    "future",
    "out of scope",
    "outside scope",
    "not claim",
    "without claiming",
    "without claim",
)
_OUT_OF_SCOPE_MARKERS = ("out of scope", "must not claim", "should not claim", "without claiming", "not included", "not in release")
_FIRST_PATH_REQUIRED_MARKERS = ("must", "required", "need", "needs", "first path", "first release", "succeeds when")
_HEAD_SCOPED_MARKERS = frozenset({"deferred", "out of scope", "outside scope", "not included", "not in release"})
_SINGLE_TERM_SCOPE_TERMS = frozenset(
    {
        "integration",
        "lifecycle",
        "live",
        "multi",
        "reminder",
        "share",
        "sharing",
        "triage",
    }
)

_SAFETY_RE = re.compile(
    r"\b(?:safety|safe|sensitive|protected|regulated|compliance|consent|private|privacy|"
    r"emergency|critical|restricted|retention|audit|access)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TitleNormalization:
    raw_title: str
    canonical_title: str
    changed: bool


@dataclass(frozen=True)
class FirstPathModel:
    raw_path: str
    steps: tuple[str, ...]
    material_action: str
    visible_outcome: str
    recovery_action: str


def normalize_project_title(value: Any, *, fallback: str = "Greenfield Project") -> TitleNormalization:
    """Strip provisional qualifiers from the canonical project title."""

    raw = _clean(value).strip(" .")
    if not raw:
        raw = _clean(fallback).strip(" .") or "Greenfield Project"
    canonical = raw
    previous = ""
    while canonical != previous:
        previous = canonical
        canonical = _PROVISIONAL_TITLE_RE.sub(" ", canonical)
        canonical = re.sub(r"\s+", " ", canonical).strip(" .:-–—")
    if not canonical:
        canonical = _clean(fallback).strip(" .") or "Greenfield Project"
    return TitleNormalization(raw_title=raw, canonical_title=canonical, changed=canonical != raw)


def contains_provisional_title_marker(value: Any) -> bool:
    return bool(_PROVISIONAL_TITLE_RE.search(_clean(value)))


def first_path_model(value: Any) -> FirstPathModel:
    raw = _clean(value)
    steps = tuple(_first_path_steps(raw))
    material = _material_action(steps) or (steps[0] if steps else "")
    visible = _visible_outcome(steps)
    recovery = _recovery_action(steps)
    return FirstPathModel(
        raw_path=raw,
        steps=steps,
        material_action=material,
        visible_outcome=visible,
        recovery_action=recovery,
    )


def material_first_path_action(value: Any, *, fallback: str = "") -> str:
    model = first_path_model(value)
    return model.material_action or _clean(fallback)


def first_path_steps(value: Any) -> tuple[str, ...]:
    return first_path_model(value).steps


def first_path_capability_phrase(
    value: Any,
    *,
    fallback: str = "accepted first path",
    limit: int = 180,
    gerund: bool = False,
    max_fragments: int = 4,
) -> str:
    """Return a compact action-chain phrase for Radar and project-story prose."""

    model = first_path_model(value)
    steps = [step for step in model.steps if step and not _is_trivial_start(step)]
    selected: list[str] = []
    if model.material_action and not _is_system_generated_action(model.material_action):
        selected.append(model.material_action)
    for step in steps:
        if len(selected) >= max(1, max_fragments):
            break
        if model.material_action and _clean(step).casefold() == _clean(model.material_action).casefold():
            continue
        if _is_system_generated_action(step):
            continue
        if _MATERIAL_ACTION_RE.search(step) or re.search(
            r"\b(?:display|displays|produce|produces|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            step,
            re.IGNORECASE,
        ):
            selected.append(step)
    if model.visible_outcome:
        selected.append(model.visible_outcome)
    fragmenter = _gerund_action_fragment if gerund else _action_chain_fragment
    fragments = _unique([fragmenter(step) for step in selected])
    text = _join_series(fragments[: max(1, max_fragments)]) or _clean(fallback)
    return _clip_phrase(text, limit=limit) or _clean(fallback)


def release_scope_for_component(
    component: Mapping[str, Any],
    *,
    first_path: str,
    proof_boundary: str,
    non_goals: Sequence[str] = (),
) -> str:
    """Classify a greenfield component's first-release relationship."""

    label = _clean(component.get("label") or component.get("name") or component.get("component_id"))
    body = _clean(
        " ".join(
            text_values(
                [
                    label,
                    component.get("source_system_description"),
                    component.get("responsibility"),
                    component.get("boundary"),
                ]
            )
        )
    )
    terms = _terms(body)
    if not terms:
        return "supporting"
    deferred_text = " ".join([proof_boundary, *non_goals])
    path_terms = _terms(" ".join((first_path, material_first_path_action(first_path))))
    proof_terms = _terms(proof_boundary)
    if _scope_context_matches(deferred_text, terms, markers=_OUT_OF_SCOPE_MARKERS):
        return "out_of_scope"
    if _scope_context_matches(deferred_text, terms, markers=_DEFERRED_MARKERS):
        return "deferred"
    if _material_overlap(terms, path_terms) >= 2:
        return "first_path_required"
    if terms & path_terms:
        return "first_path_required"
    if terms & proof_terms:
        return "supporting"
    if _scope_context_matches(" ".join(non_goals), terms, markers=_DEFERRED_MARKERS + _OUT_OF_SCOPE_MARKERS):
        return "deferred"
    return "supporting"


def active_release_components(components: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows = [
        row
        for row in components
        if str(row.get("release_scope", "")).strip() not in {"deferred", "out_of_scope", "external"}
    ]
    return rows or list(components)


def health_safety_obligations(*values: Any) -> tuple[str, ...]:
    """Return generic safety obligations when the accepted intent raises safety pressure."""

    text = _clean(" ".join(str(value or "") for value in values))
    if not _SAFETY_RE.search(text):
        return ()
    return (
        "Safety posture: the product records accepted user-entered facts without expanding into advice, authority, or decisions outside the confirmed boundary.",
        "Escalation posture: high-risk or explicitly restricted states must block ordinary readiness and route to the owner or external authority named by the accepted intent.",
        "Sensitive-data posture: protected state, lifecycle actions, retention, consent, and access require explicit policy and audit evidence when the accepted intent names them.",
    )


def generated_semantic_slop_issues(value: Any, *, root: str = "artifact") -> list[str]:
    """Detect visible generated prose that should never pass a greenfield gate."""

    issues: list[str] = []
    for path, text in _text_leaves(value):
        location = f"{root}.{path}" if path else root
        lowered = text.casefold()
        if contains_provisional_title_marker(text):
            issues.append(f"provisional title qualifier leaked at {location}")
        if re.search(r"\bowns\s+maintains\b", lowered):
            issues.append(f"malformed ownership verb pair leaked at {location}")
        if re.search(r"\bprevents\s+[^.]{1,120}\bcan\s+\w+", lowered):
            issues.append(f"malformed prevents/can clause leaked at {location}")
        if re.search(r"\bdone,\s*path,\s*mean,\s*person,\s*create,\s*view,\s*edit\b", lowered):
            issues.append(f"token-soup proof language leaked at {location}")
        if re.search(r"\bfirst\s+accepted\s+action\b", lowered):
            issues.append(f"mechanical first-action scaffold leaked at {location}")
        if re.search(r"\bfirst\s+path\s+entry\b", lowered):
            issues.append(f"mechanical first-path-entry scaffold leaked at {location}")
        if re.search(r"\bis\s+not\s+trustworthy\s+when\b", lowered):
            issues.append(f"mechanical trust scaffold leaked at {location}")
        if re.search(r"\bneed\s+[A-Z]?[A-Za-z0-9][^.;]{0,120}\s+to\s+turn\b", text):
            issues.append(f"mechanical need-to-turn problem scaffold leaked at {location}")
        if re.search(r"\bfirst\s+release\s+can\s+collect\s+activity\b", lowered):
            issues.append(f"mechanical activity-without-result scaffold leaked at {location}")
        if re.search(r"\baccepted\s+path\s+lets\s+users\b", lowered):
            issues.append(f"mechanical success-metric scaffold leaked at {location}")
        if re.search(r"\bsource\s+evidence,\s+visible\s+blockers,\s+and\s+the\s+systems?\s+that\s+own\b", lowered):
            issues.append(f"governance-scaffold problem language leaked at {location}")
        if re.search(r"\bkeeps?\s+the\s+accepted\s+path\s+step\s+reviewable\b", lowered):
            issues.append(f"mechanical path-review scaffold leaked at {location}")
        if re.search(r"\bproves\s+one\s+successful\s+local\s+state\s+transition\b", lowered):
            issues.append(f"mechanical local-transition metric leaked at {location}")
        if re.search(r"\bcan\s+act\s+where\s+the\s+accepted\s+path\s+requires\b", lowered):
            issues.append(f"mechanical actor-path scaffold leaked at {location}")
        if re.search(r"\bexpected\s+local\s+output\s*:", lowered):
            issues.append(f"generic local-output scaffold leaked at {location}")
        if re.search(r"\bit\s+owns\s+for\b", lowered) or re.search(r"\bit\s+owns\s+the\s+central\s+object\s+is\b", lowered):
            issues.append(f"malformed ownership sentence leaked at {location}")
        if re.search(r"\bevidence\s+evidence\b", lowered):
            issues.append(f"duplicated evidence word leaked at {location}")
        if re.search(r"\b[a-z][a-z-]*\b(?:metrics?|state|input|output|record|proof)[)](?:\s|[.,;:]|$)", lowered):
            issues.append(f"dangling close-parenthesis token leaked at {location}")
        if re.search(r"\bmulti-user\s+roles\s+are\s*[.]?$", lowered):
            issues.append(f"clipped out-of-scope sentence leaked at {location}")
        if re.search(r"\bhand\s+[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,4}\s+(?:identity|state|evidence|result|record)\b", lowered):
            issues.append(f"handoff verb leaked as an artifact noun at {location}")
        if (
            re.search(r"\bas a later\s*[.]?$", lowered)
            or re.search(r"\bvalid\s+transition\s+display,\s*stale\b", lowered)
            or re.search(r"\brejected\s+or\s+blocked\s+cases,\s*evidence\s*[.;:]?$", lowered)
        ):
            issues.append(f"clipped generated sentence leaked at {location}")
    return _unique(issues)


def sentence_overlap_ratio(left: str, right: str, *, ngram: int = 5) -> float:
    left_grams = _ngrams(left, ngram=ngram)
    right_grams = _ngrams(right, ngram=ngram)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / max(1, min(len(left_grams), len(right_grams)))


def _first_path_steps(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    for pattern in _FIRST_PATH_PREFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\bthat\s+single\s+loop\s*[–—-]\s*", "", text, flags=re.IGNORECASE)
    value_tail = ""
    value_match = re.search(
        r"\bso\s+the\s+(?:first\s+)?(?:end-to-end\s+)?value\s+is\s*:\s*(?P<tail>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if value_match:
        value_tail = value_match.group("tail")
        text = text[: value_match.start()].strip(" ,.;:")
    if not re.search(r"\b\d+[.)]\s*", text):
        text = re.sub(r"\s+(?:flow|journey|path)\s*:\s*.*$", "", text, flags=re.IGNORECASE)
    numbered = [part.strip(" .") for part in re.split(r"(?:^|\s)\d+[.)]\s*", text) if part.strip(" .")]
    if len(numbered) > 1:
        pieces = numbered
        if ":" in pieces[0]:
            pieces[0] = pieces[0].rsplit(":", 1)[-1].strip(" .")
    else:
        pieces = _split_action_pieces(text)
    normalized: list[str] = []
    for piece in pieces:
        cleaned = _clean_step(piece)
        if _valid_step(cleaned):
            normalized.append(cleaned)
    if value_tail:
        for piece in _split_action_pieces(value_tail):
            cleaned = _clean_step(piece)
            if _valid_step(cleaned) and re.search(
                r"\b(?:see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
                cleaned,
                re.IGNORECASE,
            ):
                normalized.append(cleaned)
    if len(normalized) > 1 and _is_trivial_start(normalized[0]):
        normalized = normalized[1:]
    return _unique(normalized)


def _material_action(steps: Sequence[str]) -> str:
    if not steps:
        return ""
    for step in steps:
        if _is_trivial_start(step):
            continue
        match = _OPEN_PLUS_MATERIAL_RE.match(step)
        if match and _MATERIAL_ACTION_RE.search(match.group("material")):
            return _sentence_case(step)
        if _MATERIAL_ACTION_RE.search(step):
            return _sentence_case(step)
    return _sentence_case(steps[0])


def _visible_outcome(steps: Sequence[str]) -> str:
    preferred: list[str] = []
    fallback: list[str] = []
    for step in reversed(steps):
        if _is_meta_visible_result_summary(step):
            continue
        if _looks_like_visible_result(step):
            cleaned = _clean_visible_result_phrase(step) or step
            if re.search(r"\b(?:see|sees|show|shows|view|views|receive|receives|render|renders|return|returns|display|displays|produce|produces)\b", cleaned, flags=re.IGNORECASE) and not re.search(
                r"\b(?:accept|accepts|click|clicks|choose|chooses|dismiss|dismisses)\b",
                cleaned,
                flags=re.IGNORECASE,
            ):
                preferred.append(cleaned)
            else:
                fallback.append(cleaned)
    if preferred:
        return _sentence_case(preferred[0])
    if fallback:
        return _sentence_case(fallback[0])
    return _sentence_case(steps[-1]) if steps else ""


def _is_meta_visible_result_summary(value: str) -> bool:
    """Return whether a step only names the parser's visible-result marker."""

    text = _clean(value)
    if not text:
        return False
    lowered = text.casefold()
    if "visible-result event" in lowered:
        return True
    return bool(re.match(r"^(?:this|the)\s+.+\bis\s+the\s+visible\s+result\b", text, flags=re.IGNORECASE))


def _is_system_generated_action(value: str) -> bool:
    """Return whether a first-path clause describes internal processing, not a user capability."""

    text = _clean(value)
    if not text:
        return False
    system_verb = (
        r"calculates?|computes?|derives?|evaluates?|generates?|renders?|returns?|runs?|"
        r"scores?|updates?|validates?"
    )
    if re.match(rf"^(?:the\s+)?(?:product|system|app|application|service|platform|tool)\s+{system_verb}\b", text, flags=re.IGNORECASE):
        return True
    return bool(re.match(rf"^[A-Z][A-Za-z0-9_-]{{2,}}\s+{system_verb}\b", text))


def _looks_like_visible_result(value: str) -> bool:
    text = _clean(value)
    return bool(
        re.search(
            r"\b(?:display|displays|export|exports|present|presents|produce|produces|publish|publishes|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:card|dashboard|indicator|readout|recommendation|result|summary|timeline|trend|view)\b",
            text,
            re.IGNORECASE,
        )
    )


def _recovery_action(steps: Sequence[str]) -> str:
    for step in reversed(steps):
        if re.search(r"\b(?:edit|edits|correct|corrects|recover|recovers|retry|retries|delete|deletes|revise|revises)\b", step, re.IGNORECASE):
            return _sentence_case(step)
    return ""


def _clean_step(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\d+[.)]\s*", "", text)
    text = re.sub(r"\bthat single loop\b\s*[–—-]?\s*", "", text, flags=re.IGNORECASE)
    if _is_meta_visible_result_summary(text):
        return ""
    text = _clean_visible_result_phrase(text) or text
    text = _normalize_subjectless_action_step(text)
    return _sentence_case(text)


def _normalize_subjectless_action_step(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text or _leading_subject_prefix(text):
        return text
    if _MATERIAL_ACTION_RE.match(text):
        text = base_action_clause(text)
    else:
        adverbial = re.match(
            r"^(?P<prefix>[A-Za-z]+ly\s+)(?P<verb>[A-Za-z]+s)\b(?P<tail>.*)$",
            text,
            flags=re.IGNORECASE,
        )
        if adverbial and _MATERIAL_ACTION_RE.match(adverbial.group("verb")):
            text = f"{adverbial.group('prefix')}{base_action_clause(adverbial.group('verb'))}{adverbial.group('tail')}"
    text = _base_following_action_verbs(text)
    text = re.sub(r",\s+and\s+", " and ", text, flags=re.IGNORECASE)
    return text.strip(" .")


def _clean_visible_result_phrase(value: str) -> str:
    """Remove parser metadata from a visible-result phrase without losing the product outcome."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^on\s+save,\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    match = re.match(
        r"^(?:this|the)\s+(?P<head>.+?)\s+[–—-]\s+(?P<detail>.+?)\s+[–—-]\s+is\s+the\s+visible\s+result\b.*$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        text = f"{match.group('head')} with {match.group('detail')}"
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
    visible_tail = re.match(
        r"^.+\s+and\s+(?P<tail>(?:the\s+)?[A-Za-z0-9][A-Za-z0-9 '-]{1,60}\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if visible_tail:
        text = visible_tail.group("tail")
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.IGNORECASE)
    text = re.sub(r"\balongside\b", "with", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:this|the)\s+rendered\b", "rendered", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def _split_action_pieces(value: str) -> list[str]:
    pieces: list[str] = []
    for segment in [part.strip(" .") for part in _ACTION_SPLIT_RE.split(value) if part.strip(" .")]:
        current = ""
        subject_prefix = ""
        for part in [piece.strip(" .") for piece in re.split(r",\s+", segment) if piece.strip(" .")]:
            if current and _starts_new_action_clause(part):
                pieces.append(current.strip(" ."))
                current = _with_carried_subject(part, subject_prefix)
            else:
                current = f"{current}, {part}" if current else part
            explicit_subject = _leading_subject_prefix(current)
            if explicit_subject:
                subject_prefix = explicit_subject
        if current:
            pieces.append(current.strip(" ."))
    return pieces


def _with_carried_subject(value: str, subject_prefix: str) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    if not subject_prefix or _leading_subject_prefix(text):
        return text
    if _MATERIAL_ACTION_RE.match(text):
        return f"{subject_prefix} {text[:1].lower()}{text[1:]}"
    return text


def _leading_subject_prefix(value: str) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    match = _MATERIAL_ACTION_RE.search(text)
    if not match or match.start() == 0:
        return ""
    subject = text[: match.start()].strip()
    if not re.match(r"^(?:a|an|the|one|this|that|each|another)\s+", subject, flags=re.IGNORECASE):
        return ""
    if len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", subject)) > 6:
        return ""
    return subject


def _starts_new_action_clause(value: str) -> bool:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    if not text:
        return False
    if re.match(
        r"^(?:a|an|the|one|this|that|each|another|product|system|user|person|actor|app|application)\s+"
        r"(?:[A-Za-z0-9'-]+\s+){0,5}?"
        r"(?:"
        r"accept|accepts|add|adds|adjust|adjusts|approve|approves|assign|assigns|attach|attaches|calculate|calculates|capture|captures|"
        r"check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|correct|corrects|"
        r"click|clicks|create|creates|delete|deletes|dismiss|dismisses|edit|edits|enter|enters|export|exports|fetch|fetches|finalize|finalizes|"
        r"display|displays|import|imports|inspect|inspects|log|logs|mark|marks|notify|notifies|persist|persists|preserve|preserves|"
        r"produce|produces|publish|publishes|rank|ranks|read|reads|receive|receives|record|records|render|renders|request|requests|review|reviews|return|returns|route|routes|"
        r"run|runs|save|saves|schedule|schedules|screen|screens|see|sees|select|selects|send|sends|share|shares|show|shows|"
        r"store|stores|submit|submits|sync|syncs|tap|taps|track|tracks|update|updates|validate|validates|view|views"
        r")\b",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    return bool(_MATERIAL_ACTION_RE.match(text) and len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)) >= 2)


def _valid_step(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)
    if len(words) < 2:
        return False
    if len(words) <= 3 and not _MATERIAL_ACTION_RE.search(text):
        return False
    if re.fullmatch(r"(?:capture|view|edit|create|done|path|mean|person)(?:\s*,\s*(?:capture|view|edit|create|done|path|mean|person))*", text, re.IGNORECASE):
        return False
    return True


def _is_trivial_start(value: str) -> bool:
    text = _clean(value).strip(" .")
    return bool(_TRIVIAL_START_RE.match(text) or _TRIVIAL_NAMED_PRODUCT_START_RE.match(text))


def _scope_context_matches(text: str, terms: set[str], *, markers: Sequence[str]) -> bool:
    if not terms:
        return False
    for sentence in re.split(r"(?<=[.!?])\s+|;\s+|\n+", _clean(text)):
        lowered = sentence.casefold()
        for marker in markers:
            if marker not in lowered:
                continue
            head, tail = lowered.split(marker, 1)
            tail_terms = _terms(tail)
            if _material_overlap(terms, tail_terms) >= 2 or terms & tail_terms & _SINGLE_TERM_SCOPE_TERMS:
                return True
            head_terms = _terms(head)
            if (
                marker in _HEAD_SCOPED_MARKERS
                and _looks_like_head_scoped_clause(head)
                and (_material_overlap(terms, head_terms) >= 2 or terms & head_terms & _SINGLE_TERM_SCOPE_TERMS)
            ):
                return True
    return False


def _material_overlap(left: set[str], right: set[str]) -> int:
    return len(left & right)


def _looks_like_head_scoped_clause(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    words = re.findall(r"[a-z0-9]+", text.casefold())
    if len(words) > 14:
        return False
    if re.search(r"\b(?:is|are|stays?|remains?|keeps?|kept|explicitly|currently)\s*$", text, re.IGNORECASE):
        return True
    if re.search(r"[:,-]\s*$", text):
        return True
    if len(words) <= 6:
        return True
    return False


def _text_leaves(value: Any, *, path: tuple[str, ...] = ()) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        rows: list[tuple[str, str]] = []
        for key, nested in value.items():
            if str(key).casefold() in {"source_title"}:
                continue
            rows.extend(_text_leaves(nested, path=(*path, str(key))))
        return tuple(rows)
    if isinstance(value, (list, tuple, set)):
        rows: list[tuple[str, str]] = []
        for index, nested in enumerate(value):
            rows.extend(_text_leaves(nested, path=(*path, str(index))))
        return tuple(rows)
    text = _clean(value)
    return ((".".join(path), text),) if text else ()


def _terms(value: Any) -> set[str]:
    stop = {
        "accepted",
        "action",
        "adjacent",
        "actor",
        "app",
        "application",
        "assigned",
        "boundary",
        "component",
        "data",
        "decision",
        "deferred",
        "depend",
        "evidence",
        "explicitly",
        "first",
        "handoff",
        "input",
        "internal",
        "other",
        "output",
        "outside",
        "path",
        "presentation",
        "product",
        "produce",
        "proof",
        "record",
        "release",
        "responsibility",
        "review",
        "rule",
        "scope",
        "service",
        "source",
        "state",
        "stay",
        "system",
        "this",
        "truth",
        "unless",
        "user",
    }
    result: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(value).casefold()):
        token = normalize_domain_token(raw, stopwords=stop)
        if token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        if token.startswith("shar"):
            token = "share"
        if token.startswith("remind"):
            token = "reminder"
        if token:
            result.add(token)
    return result


def _ngrams(value: str, *, ngram: int) -> set[tuple[str, ...]]:
    tokens = [
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(value).casefold())
        if token not in _NGRAM_STOPWORDS
    ]
    return {tuple(tokens[index : index + ngram]) for index in range(max(0, len(tokens) - ngram + 1))}


def _sentence_case(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return text[:1].upper() + text[1:]


def _action_chain_fragment(value: str) -> str:
    text = _clean_visible_result_phrase(value) or _clean(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and,\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+if\b.+$", "", text, flags=re.IGNORECASE)
    outcome = _visible_result_object(text)
    if outcome and not re.search(r"\b(?:receives?|gets?)\b", text, flags=re.IGNORECASE):
        return f"review {outcome}".strip(" .")
    click = re.search(r"\bclicks?\s+(?P<object>.+?)(?:\s+and\s+.+)?$", text, flags=re.IGNORECASE)
    if click:
        clicked = _clean(click.group("object"))
        clicked = re.sub(r"\bon\s+that\b", "on the", clicked, flags=re.IGNORECASE)
        return _clip_phrase(f"choose {clicked.casefold()}", limit=120)
    text = _strip_action_subject(text)
    text = base_action_clause(text)
    text = _base_following_action_verbs(text)
    text = re.sub(r",\s+and\s+", " and ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.")
    return text[:1].casefold() + text[1:] if text else ""


def _visible_result_object(value: str) -> str:
    text = _clean_visible_result_phrase(value) or _clean(value)
    patterns = (
        r":\s*(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer)\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+(?P<object>.+)$",
        r"\b(?:sees?|views?|receives?|gets?|reads?)\s+(?P<object>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            result = match.group("object")
            result = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", result, flags=re.IGNORECASE)
            return _clip_phrase(result, limit=150)
    if not _MATERIAL_ACTION_RE.search(text) and _looks_like_visible_result(text):
        return _clip_phrase(re.sub(r"^(?:this|the)\s+", "", text, flags=re.IGNORECASE), limit=150)
    return ""


def _strip_action_subject(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"^on\s+save,\s*", "save, ", text, flags=re.IGNORECASE)
    match = _MATERIAL_ACTION_RE.search(text)
    if match and match.start() > 0:
        prefix = text[: match.start()].strip(" ,")
        prefix_words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", prefix)
        if len(prefix_words) <= 6:
            text = text[match.start() :]
    return text


def _base_following_action_verbs(value: str) -> str:
    text = _clean(value)
    verb_pairs = {
        "adds": "add",
        "calculates": "calculate",
        "clicks": "click",
        "displays": "display",
        "enters": "enter",
        "logs": "log",
        "produces": "produce",
        "records": "record",
        "renders": "render",
        "returns": "return",
        "saves": "save",
        "sees": "see",
        "shows": "show",
        "submits": "submit",
        "updates": "update",
    }
    for finite, base in verb_pairs.items():
        text = re.sub(
            rf"\b(and|or)\s+((?:[a-z]+ly\s+)?)({finite})\b",
            rf"\1 \2{base}",
            text,
            flags=re.IGNORECASE,
        )
    return text


def _gerund_action_fragment(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and,\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+if\b.+$", "", text, flags=re.IGNORECASE)
    verb_map = {
        "add": "adding",
        "adds": "adding",
        "adjust": "adjusting",
        "adjusts": "adjusting",
        "approve": "approving",
        "approves": "approving",
        "check": "checking",
        "checks": "checking",
        "choose": "choosing",
        "chooses": "choosing",
        "compare": "comparing",
        "compares": "comparing",
        "complete": "completing",
        "completes": "completing",
        "create": "creating",
        "creates": "creating",
        "edit": "editing",
        "edits": "editing",
        "enter": "entering",
        "enters": "entering",
        "export": "exporting",
        "exports": "exporting",
        "fetch": "fetching",
        "fetches": "fetching",
        "finalize": "finalizing",
        "finalizes": "finalizing",
        "highlight": "highlighting",
        "highlights": "highlighting",
        "import": "importing",
        "imports": "importing",
        "let": "letting",
        "lets": "letting",
        "log": "logging",
        "logs": "logging",
        "publish": "publishing",
        "publishes": "publishing",
        "rank": "ranking",
        "ranks": "ranking",
        "read": "reading",
        "reads": "reading",
        "record": "recording",
        "records": "recording",
        "review": "reviewing",
        "reviews": "reviewing",
        "save": "saving",
        "saves": "saving",
        "see": "seeing",
        "sees": "seeing",
        "select": "selecting",
        "selects": "selecting",
        "show": "showing",
        "shows": "showing",
        "store": "storing",
        "stores": "storing",
        "submit": "submitting",
        "submits": "submitting",
        "validate": "validating",
        "validates": "validating",
        "view": "viewing",
        "views": "viewing",
    }
    pattern = "|".join(re.escape(item) for item in sorted(verb_map, key=len, reverse=True))
    for match in re.finditer(rf"\b(?P<verb>{pattern})\b", text, flags=re.IGNORECASE):
        verb = match.group("verb").casefold()
        tail = text[match.end() :]
        if verb in {"record", "records"} and re.match(
            r"\s+(?:owner|reviewer|recipient|actor|user|operator|publisher)\b",
            tail,
            flags=re.IGNORECASE,
        ):
            continue
        return _gerund_following_action_verbs(f"{verb_map[verb]}{tail}").strip(" ,.")
    return text[:1].casefold() + text[1:] if text else ""


def _gerund_following_action_verbs(value: str) -> str:
    text = _clean(value)
    verb_pairs = {
        "add": "adding",
        "adds": "adding",
        "calculate": "calculating",
        "calculates": "calculating",
        "click": "clicking",
        "clicks": "clicking",
        "display": "displaying",
        "displays": "displaying",
        "enter": "entering",
        "enters": "entering",
        "log": "logging",
        "logs": "logging",
        "produce": "producing",
        "produces": "producing",
        "record": "recording",
        "records": "recording",
        "render": "rendering",
        "renders": "rendering",
        "return": "returning",
        "returns": "returning",
        "save": "saving",
        "saves": "saving",
        "see": "seeing",
        "sees": "seeing",
        "show": "showing",
        "shows": "showing",
        "submit": "submitting",
        "submits": "submitting",
        "update": "updating",
        "updates": "updating",
    }
    for finite, gerund in verb_pairs.items():
        text = re.sub(
            rf"\b(and|or)\s+((?:[a-z]+ly\s+)?)({finite})\b",
            rf"\1 \2{gerund}",
            text,
            flags=re.IGNORECASE,
        )
    return re.sub(r",\s+and\s+", " and ", text, flags=re.IGNORECASE)


def _join_series(values: Sequence[str]) -> str:
    rows = [_clean(value).strip(" .") for value in values if _clean(value).strip(" .")]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _clip_phrase(value: str, *, limit: int) -> str:
    text = _clean(value).strip(" .")
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 1)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|for|from|if|in|into|of|on|or|required|that|the|this|to|when|while|with|alongside)$",
            "",
            clipped,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:")
        if cleaned == clipped:
            return cleaned
        clipped = cleaned


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


__all__ = [
    "FirstPathModel",
    "TitleNormalization",
    "active_release_components",
    "contains_provisional_title_marker",
    "first_path_capability_phrase",
    "first_path_model",
    "first_path_steps",
    "generated_semantic_slop_issues",
    "health_safety_obligations",
    "material_first_path_action",
    "normalize_project_title",
    "release_scope_for_component",
    "sentence_overlap_ratio",
]
