"""Shared semantic hygiene helpers for confirmed greenfield generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
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
            draft|
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

_MATERIAL_ACTION_RE = re.compile(
    r"\b(?:"
    r"add|adds|adjust|adjusts|approve|approves|attach|attaches|calculate|calculates|capture|captures|"
    r"check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|correct|corrects|"
    r"create|creates|delete|deletes|edit|edits|enter|enters|export|exports|fetch|fetches|finalize|finalizes|"
    r"highlight|highlights|import|imports|inspect|inspects|let|lets|log|logs|mark|marks|notify|notifies|persist|persists|play|plays|"
    r"preserve|preserves|publish|publishes|rank|ranks|read|reads|receive|receives|record|records|request|requests|review|reviews|"
    r"route|routes|run|runs|save|saves|schedule|schedules|see|sees|select|selects|send|sends|share|shares|"
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

_HEALTH_RE = re.compile(
    r"\b(?:health|medical|clinician|clinical|patient|caregiver|symptom|pain|medication|medicine|dose|dosage|"
    r"treatment|relief|emergency|pregnancy|underage|injury|diagnosis|diagnose|therapy|side effect)\b",
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
    if _scope_context_matches(deferred_text, terms, markers=_OUT_OF_SCOPE_MARKERS):
        return "out_of_scope"
    if _scope_context_matches(deferred_text, terms, markers=_DEFERRED_MARKERS):
        return "deferred"
    path_terms = _terms(" ".join((first_path, material_first_path_action(first_path))))
    proof_terms = _terms(proof_boundary)
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
    """Return generic safety obligations for health or medical self-tracking products."""

    text = _clean(" ".join(str(value or "") for value in values))
    if not _HEALTH_RE.search(text):
        return ()
    return (
        "Health safety: the product records user-entered health observations and must not diagnose, prescribe, or recommend medication dosing.",
        "Escalation safety: emergency symptoms, severe changes, pregnancy, underage use, or other red flags must direct the user to professional or emergency care instead of product guidance.",
        "Sensitive-data safety: health data, caregiver access, clinician sharing, export, deletion, retention, and consent state require explicit privacy and audit evidence.",
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
    if len(normalized) > 1 and _TRIVIAL_START_RE.match(normalized[0]):
        normalized = normalized[1:]
    return _unique(normalized)


def _material_action(steps: Sequence[str]) -> str:
    if not steps:
        return ""
    for step in steps:
        if _TRIVIAL_START_RE.match(step):
            continue
        match = _OPEN_PLUS_MATERIAL_RE.match(step)
        if match and _MATERIAL_ACTION_RE.search(match.group("material")):
            return _sentence_case(step)
        if _MATERIAL_ACTION_RE.search(step):
            return _sentence_case(step)
    return _sentence_case(steps[0])


def _visible_outcome(steps: Sequence[str]) -> str:
    for step in reversed(steps):
        if re.search(r"\b(?:see|sees|show|shows|view|views|review|reviews|receive|receives|export|exports|publish|publishes)\b", step, re.IGNORECASE):
            return _sentence_case(step)
    return _sentence_case(steps[-1]) if steps else ""


def _recovery_action(steps: Sequence[str]) -> str:
    for step in reversed(steps):
        if re.search(r"\b(?:edit|edits|correct|corrects|recover|recovers|retry|retries|delete|deletes|revise|revises)\b", step, re.IGNORECASE):
            return _sentence_case(step)
    return ""


def _clean_step(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(r"^(?:and|then)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\d+[.)]\s*", "", text)
    text = re.sub(r"\bthat single loop\b\s*[–—-]?\s*", "", text, flags=re.IGNORECASE)
    return _sentence_case(text)


def _split_action_pieces(value: str) -> list[str]:
    pieces: list[str] = []
    for segment in [part.strip(" .") for part in _ACTION_SPLIT_RE.split(value) if part.strip(" .")]:
        current = ""
        for part in [piece.strip(" .") for piece in re.split(r",\s+", segment) if piece.strip(" .")]:
            if current and _starts_new_action_clause(part):
                pieces.append(current.strip(" ."))
                current = part
            else:
                current = f"{current}, {part}" if current else part
        if current:
            pieces.append(current.strip(" ."))
    return pieces


def _starts_new_action_clause(value: str) -> bool:
    text = re.sub(r"^(?:and|then)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    if not text:
        return False
    if re.match(
        r"^(?:a|an|the|one|this|that|each|another|product|system|user|person|actor|app|application)\s+"
        r"(?:[A-Za-z0-9'-]+\s+){0,5}?"
        r"(?:"
        r"add|adds|adjust|adjusts|approve|approves|attach|attaches|calculate|calculates|capture|captures|"
        r"check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|correct|corrects|"
        r"create|creates|delete|deletes|edit|edits|enter|enters|export|exports|fetch|fetches|finalize|finalizes|"
        r"import|imports|inspect|inspects|log|logs|mark|marks|notify|notifies|persist|persists|preserve|preserves|"
        r"publish|publishes|rank|ranks|read|reads|receive|receives|record|records|request|requests|review|reviews|route|routes|"
        r"run|runs|save|saves|schedule|schedules|see|sees|select|selects|send|sends|share|shares|show|shows|"
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


def _scope_context_matches(text: str, terms: set[str], *, markers: Sequence[str]) -> bool:
    if not terms:
        return False
    for sentence in re.split(r"(?<=[.!?])\s+|;\s+|\n+", _clean(text)):
        lowered = sentence.casefold()
        for marker in markers:
            if marker not in lowered:
                continue
            head, tail = lowered.split(marker, 1)
            if terms & _terms(tail):
                return True
            if marker in _HEAD_SCOPED_MARKERS and _looks_like_head_scoped_clause(head) and terms & _terms(head):
                return True
    return False


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
        token = raw.strip("-_")
        if token.endswith("ies") and len(token) > 5:
            token = f"{token[:-3]}y"
        elif token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        elif token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
            token = token[:-1]
        if token.startswith("shar"):
            token = "share"
        if token.startswith("remind"):
            token = "reminder"
        if len(token) >= 4 and token not in stop:
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
    "first_path_model",
    "first_path_steps",
    "generated_semantic_slop_issues",
    "health_safety_obligations",
    "material_first_path_action",
    "normalize_project_title",
    "release_scope_for_component",
    "sentence_overlap_ratio",
]
