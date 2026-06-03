"""First-path parsing and prose helpers for confirmed greenfield generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_following_action_verbs
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token

_TRIVIAL_START_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,40}?\b(?:open|opens|launch|launches|start|starts)\s+"
    r"(?:the\s+)?(?:(?:web\s+)?app(?:lication)?|product|tool|site|website|screen|page|dashboard|portal|console)\b\s*$",
    re.IGNORECASE,
)
_TRIVIAL_NAMED_PRODUCT_START_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,40}?\b(?:open|opens|launch|launches|start|starts)\s+"
    r"[A-Z][A-Za-z0-9_-]{2,40}\b\s*$"
)
_TRIVIAL_AUTH_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,60}?\b(?:authenticates?|logs?\s+in|signs?\s+in)\b\s*$",
    re.IGNORECASE,
)

_MATERIAL_ACTION_RE = re.compile(
    r"\b(?:"
    r"accept|accepts|add|adds|adjust|adjusts|approve|approves|assign|assigns|attach|attaches|calculate|calculates|capture|captures|"
    r"book|books|check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|correct|corrects|decide|decides|"
    r"click|clicks|create|creates|delete|deletes|describe|describes|dismiss|dismisses|edit|edits|enter|enters|export|exports|fetch|fetches|finalize|finalizes|"
    r"display|displays|highlight|highlights|import|imports|inspect|inspects|let|lets|log|logs|mark|marks|notify|notifies|persist|persists|play|plays|"
    r"preserve|preserves|produce|produces|provide|provides|publish|publishes|rank|ranks|read|reads|receive|receives|record|records|render|renders|request|requests|review|reviews|"
    r"return|returns|route|routes|run|runs|save|saves|schedule|schedules|screen|screens|see|sees|select|selects|send|sends|share|shares|"
    r"show|shows|stop|stops|store|stores|submit|submits|sync|syncs|tap|taps|track|tracks|update|updates|"
    r"validate|validates|view|views"
    r")\b",
    re.IGNORECASE,
)
_ACTION_BASE_VERB_PATTERN = action_base_verb_pattern()

_OPEN_PLUS_MATERIAL_RE = re.compile(
    r"^\s*(?P<subject>(?:a|an|the)?\s*[^,.;]{0,80}?)\b(?:open|opens|launch|launches)\b"
    r"(?P<object>\s+[^,.;]{1,80}?)\s+\band\b\s+(?P<material>.+)$",
    re.IGNORECASE,
)

_ACTION_SPLIT_RE = re.compile(r"\s*(?:;|(?<=[.!?])\s+|\s+\bthen\b\s+)\s*", re.IGNORECASE)

_FIRST_PATH_PREFIXES = (
    r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
    r"^the first complete path starts? (?:when|with)\s+",
    r"^first complete path starts? (?:when|with)\s+",
    r"^the first complete path to prove should be\s*:?\s*",
    r"^first complete path to prove should be\s*:?\s*",
    r"^the first path starts? (?:when|with)\s+",
    r"^first path starts? (?:when|with)\s+",
    r"^the first path is\s+",
    r"^first path\s*:?\s*",
)

@dataclass(frozen=True)
class FirstPathModel:
    raw_path: str
    steps: tuple[str, ...]
    material_action: str
    visible_outcome: str
    recovery_action: str


@dataclass(frozen=True)
class FirstPathClauses:
    """Reusable first-path prose clauses rendered by greenfield surfaces."""

    model: FirstPathModel
    action_chain: str
    capability_chain: str
    visible_result: str


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
    text = _first_path_capability_text(model, fallback=fallback, limit=limit, gerund=gerund, max_fragments=max_fragments)
    return text or _clean(fallback)


def first_path_clauses(
    value: Any,
    *,
    proof_boundary: Any = "",
    action_fallback: str = "complete the first product action",
    capability_fallback: str = "accepted first path",
    outcome_fallback: str = "the promised user-visible result",
    action_limit: int = 220,
    capability_limit: int = 220,
    outcome_limit: int = 220,
) -> FirstPathClauses:
    """Compile a first path once into the clauses shared by all renderers."""

    model = first_path_model(value)
    return FirstPathClauses(
        model=model,
        action_chain=_first_path_action_text(model, fallback=action_fallback, limit=action_limit, max_fragments=3),
        capability_chain=_first_path_capability_text(
            model,
            fallback=capability_fallback,
            limit=capability_limit,
            gerund=False,
            max_fragments=7,
        ),
        visible_result=_first_path_outcome_text(
            model,
            proof_boundary=proof_boundary,
            fallback=outcome_fallback,
            limit=outcome_limit,
        ),
    )


def _first_path_capability_text(
    model: FirstPathModel,
    *,
    fallback: str,
    limit: int,
    gerund: bool,
    max_fragments: int,
) -> str:
    steps = [step for step in model.steps if step and not _is_trivial_start(step)]
    selected: list[str] = []
    primary_actor = _primary_actor_signature(model)
    if model.material_action and not _is_system_generated_action(model.material_action):
        selected.append(model.material_action)
    selected_fragments = {_action_chain_fragment(row).casefold() for row in selected if _action_chain_fragment(row)}
    included_visible_result = False
    visible_seen = False
    for step in steps:
        fragment_key = _action_chain_fragment(step).casefold()
        if fragment_key and fragment_key in selected_fragments:
            continue
        visible_object = _visible_result_object(step)
        visible_step = bool(visible_object and _looks_like_visible_result(step))
        if _is_system_generated_action(step):
            visible_seen = visible_seen or visible_step
            continue
        if primary_actor and _actor_signature(step) and _actor_signature(step) != primary_actor and visible_seen:
            continue
        if visible_object and _clean(visible_object).casefold() == _clean(model.visible_outcome).casefold():
            included_visible_result = True
        if len(selected) >= max(1, max_fragments):
            break
        if _MATERIAL_ACTION_RE.search(step) or re.search(
            r"\b(?:display|displays|produce|produces|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            step,
            re.IGNORECASE,
        ):
            selected.append(step)
            if fragment_key:
                selected_fragments.add(fragment_key)
        visible_seen = visible_seen or visible_step
    fragmenter = _gerund_action_fragment if gerund else _action_chain_fragment
    fragments = _unique([fragmenter(step) for step in selected])
    if not gerund and model.visible_outcome and not included_visible_result:
        outcome = _visible_result_object(model.visible_outcome) or _clean(model.visible_outcome)
        if outcome:
            fragments.append(_outcome_capability_fragment(outcome))
    text = _join_series(fragments[: max(1, max_fragments)]) or _clean(fallback)
    return _clip_phrase(text, limit=limit) or _clean(fallback)


def _first_path_action_text(
    model: FirstPathModel,
    *,
    fallback: str,
    limit: int,
    max_fragments: int,
) -> str:
    visible = _clean(model.visible_outcome).casefold()
    primary_actor = _primary_actor_signature(model)
    fragments: list[str] = []
    visible_seen = False
    for step in model.steps:
        visible_object = _clean(_visible_result_object(step)).casefold()
        visible_step = bool(visible_object and _looks_like_visible_result(step))
        if _is_trivial_start(step):
            continue
        if _is_system_generated_action(step):
            visible_seen = visible_seen or visible_step
            continue
        if primary_actor and _actor_signature(step) and _actor_signature(step) != primary_actor and visible_seen:
            continue
        if fragments and (visible_object == visible or (_looks_like_visible_result(step) and visible_object)):
            visible_seen = visible_seen or visible_step
            continue
        fragment = _action_chain_fragment(step)
        if fragment:
            fragments.append(fragment)
        if len(fragments) >= max(1, max_fragments):
            break
        visible_seen = visible_seen or visible_step
    if not fragments and model.material_action:
        fragments.append(_action_chain_fragment(model.material_action))
    return _clip_phrase(_join_series(_unique(fragments)), limit=limit) or _clean(fallback)


def first_path_action_phrase(
    value: Any,
    *,
    fallback: str = "complete the first product action",
    limit: int = 220,
    max_fragments: int = 3,
) -> str:
    """Return only the user-side action chain from a first path."""

    model = first_path_model(value)
    return _first_path_action_text(model, fallback=fallback, limit=limit, max_fragments=max_fragments)


def _first_path_outcome_text(
    model: FirstPathModel,
    *,
    proof_boundary: Any,
    fallback: str,
    limit: int,
) -> str:
    visible = _clean(model.visible_outcome)
    proof = _clean(proof_boundary)
    text = proof if _is_low_information_visible_outcome(visible) and proof else visible or proof or _clean(model.raw_path)
    text = _visible_result_object(text) or _action_chain_fragment(text) or text
    text = _lowercase_leading_article(text)
    text = re.sub(r"^(?:It|Them|They|This|That)\b", lambda match: match.group(0).casefold(), text)
    return _clip_phrase(text, limit=limit) or _clean(fallback)


def _is_low_information_visible_outcome(value: str) -> bool:
    text = _clean(value).casefold().strip(" .")
    return text in {
        "next action",
        "next step",
        "the next action",
        "the next step",
        "what happened next",
        "what happens next",
    }


def first_path_outcome_phrase(
    value: Any,
    *,
    proof_boundary: Any = "",
    fallback: str = "the promised user-visible result",
    limit: int = 220,
) -> str:
    """Return the object/result a participant can use after the first path."""

    model = first_path_model(value)
    return _first_path_outcome_text(model, proof_boundary=proof_boundary, fallback=fallback, limit=limit)

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
            return _sentence_case(_action_chain_fragment(step))
        if _MATERIAL_ACTION_RE.search(step):
            return _sentence_case(_action_chain_fragment(step))
    return _sentence_case(_action_chain_fragment(steps[0]))


def _visible_outcome(steps: Sequence[str]) -> str:
    preferred: list[str] = []
    fallback: list[str] = []
    for step in reversed(steps):
        if _is_meta_visible_result_summary(step) or _is_scope_or_deferred_statement(step):
            continue
        if _looks_like_visible_result(step):
            cleaned = _clean_visible_result_phrase(step) or step
            if re.search(r"\b(?:see|sees|show|shows|view|views|receive|receives|render|renders|return|returns|display|displays|produce|produces)\b", cleaned, flags=re.IGNORECASE) and not re.search(
                r"\b(?:accept|accepts|click|clicks|choose|chooses|dismiss|dismisses)\b",
                cleaned,
                flags=re.IGNORECASE,
            ):
                preferred.append(_visible_action_clause(cleaned) or _visible_result_object(cleaned) or cleaned)
            else:
                fallback.append(_visible_action_clause(cleaned) or _visible_result_object(cleaned) or cleaned)
    if preferred:
        return _sentence_case(preferred[0])
    if fallback:
        return _sentence_case(fallback[0])
    for step in reversed(steps):
        if not _is_scope_or_deferred_statement(step):
            return _sentence_case(step)
    return ""


def _is_meta_visible_result_summary(value: str) -> bool:
    """Return whether a step only names the parser's visible-result marker."""

    text = _clean(value)
    if not text:
        return False
    lowered = text.casefold()
    if "visible-result event" in lowered:
        return True
    return bool(re.match(r"^(?:this|the)\s+.+\bis\s+the\s+visible\s+result\b", text, flags=re.IGNORECASE))


def _visible_action_clause(value: str) -> str:
    text = _strip_action_subject(_clean_visible_result_phrase(value) or _clean(value))
    if re.match(r"^(?:gets?|reads?|receives?|sees?|views?)\b", text, flags=re.IGNORECASE):
        return _action_chain_fragment(text)
    return ""


def _is_system_generated_action(value: str) -> bool:
    """Return whether a first-path clause describes internal processing, not a user capability."""

    text = _clean(value)
    if not text:
        return False
    system_verb = (
        r"asks?|calculates?|checks?|computes?|derives?|displays?|evaluates?|generates?|presents?|renders?|returns?|runs?|"
        r"persists?|saves?|scores?|shows?|stores?|updates?|validates?"
    )
    system_subject = (
        r"product|system|app|application|service|platform|tool|workspace|engine|calculator|dashboard|view|model"
    )
    if re.match(rf"^(?:the\s+)?(?:{system_subject})\s+(?:{system_verb})\b", text, flags=re.IGNORECASE):
        return True
    return bool(re.match(rf"^[A-Z][A-Za-z0-9_-]{{2,}}\s+(?:{system_verb})\b", text))


def _looks_like_visible_result(value: str) -> bool:
    text = _clean(value)
    return bool(
        re.search(
            r"\b(?:decide|decides|display|displays|export|exports|highlight|highlights|present|presents|produce|produces|publish|publishes|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
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
    text = re.sub(
        r"^(?:(?:release\s+\S+|the\s+first\s+release|first\s+release)\s+)?"
        r"(?:succeeds?|is\s+trusted|is\s+proven|works)\s+when\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^\d+[.)]\s*", "", text)
    text = re.sub(r"\bthat single loop\b\s*[–—-]?\s*", "", text, flags=re.IGNORECASE)
    if _is_meta_visible_result_summary(text):
        return ""
    text = _clean_visible_result_phrase(text) or text
    text = _normalize_role_can_step(text)
    text = _normalize_subjectless_action_step(text)
    return _sentence_case(text)


def _normalize_role_can_step(value: str) -> str:
    text = _clean(value).strip(" .")
    match = re.match(
        r"^(?:a|an|the|one)\s+(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?)\s+can\s+"
        r"(?P<verb>[A-Za-z]+)\b(?P<rest>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    role = match.group("role").strip()
    rest = _normalize_role_can_rest(match.group("rest"))
    return f"{role} {third_person_action_verb(match.group('verb'))}{rest}".strip(" .")


def _normalize_role_can_rest(value: str) -> str:
    rest = str(value or "")

    def replace_comma(match: re.Match[str]) -> str:
        prefix = " and " if match.group("and") else ", "
        return f"{prefix}{third_person_action_verb(match.group('verb'))}"

    rest = re.sub(
        rf"\s*,\s+(?P<and>and\s+)?(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b",
        replace_comma,
        rest,
        flags=re.IGNORECASE,
    )
    return re.sub(
        rf"\s+and\s+(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b",
        lambda match: f" and {third_person_action_verb(match.group('verb'))}",
        rest,
        flags=re.IGNORECASE,
    )


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
    text = base_following_action_verbs(text)
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
        r"^(?:a|an|the|one|this|that|each|another|product|system|user|person|actor|app|application|workspace|engine|dashboard|view)\s+"
        r"(?:[A-Za-z0-9'-]+\s+){0,5}?"
        r"(?:"
        r"accept|accepts|add|adds|adjust|adjusts|approve|approves|assign|assigns|attach|attaches|book|books|calculate|calculates|capture|captures|"
        r"check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|correct|corrects|"
        r"click|clicks|create|creates|decide|decides|delete|deletes|describe|describes|dismiss|dismisses|edit|edits|enter|enters|export|exports|fetch|fetches|finalize|finalizes|"
        r"display|displays|import|imports|inspect|inspects|log|logs|mark|marks|notify|notifies|persist|persists|preserve|preserves|"
        r"produce|produces|provide|provides|publish|publishes|rank|ranks|read|reads|receive|receives|record|records|render|renders|request|requests|review|reviews|return|returns|route|routes|"
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
    if _is_scope_or_deferred_statement(text):
        return False
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)
    if len(words) < 2:
        return False
    if len(words) <= 3 and not _MATERIAL_ACTION_RE.search(text):
        return False
    if re.fullmatch(r"(?:capture|view|edit|create|done|path|mean|person)(?:\s*,\s*(?:capture|view|edit|create|done|path|mean|person))*", text, re.IGNORECASE):
        return False
    return True


def _is_scope_or_deferred_statement(value: str) -> bool:
    """Return whether a clause describes release limits, not first-path behavior."""

    text = _clean(value).strip(" .")
    if not text:
        return False
    lowered = text.casefold()
    if re.search(
        r"\b(?:out\s+of\s+scope|outside\s+(?:the\s+)?(?:first\s+)?release|outside\s+scope|"
        r"stay\s+outside|stays\s+outside|deferred|later|future|not\s+included|not\s+claim|"
        r"must\s+not\s+claim|does\s+not\s+claim)\b",
        lowered,
    ):
        return True
    return bool(
        re.search(r"\b(?:multi|external|automated|long-term|broader|production-scale|fleet-wide)\b", lowered)
        and re.search(r"\b(?:scope|release|stay|stays|outside|deferred|later|future|not)\b", lowered)
    )


def _is_trivial_start(value: str) -> bool:
    text = _clean(value).strip(" .")
    if re.search(r"\b(?:opens?|launches?|starts?)\b", text, flags=re.IGNORECASE) and re.search(
        r"(?:,\s*|\s+and\s+).*\b(?:add|adds|choose|chooses|describe|describes|enter|enters|log|logs|provide|provides|record|records|select|selects|submit|submits)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return bool(_TRIVIAL_START_RE.match(text) or _TRIVIAL_NAMED_PRODUCT_START_RE.match(text) or _TRIVIAL_AUTH_RE.match(text))



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
        stripped = _strip_action_subject(text)
        if re.match(r"^(?:checks?|decides?|inspects?|reads?|reviews?|sees?|uses?|views?)\b", stripped, flags=re.IGNORECASE):
            return base_action_clause(stripped).strip(" .")
        return f"review {_lowercase_leading_article(outcome)}".strip(" .")
    click = re.search(r"\bclicks?\s+(?P<object>.+?)(?:\s+and\s+.+)?$", text, flags=re.IGNORECASE)
    if click:
        clicked = _clean(click.group("object"))
        clicked = re.sub(r"\bon\s+that\b", "on the", clicked, flags=re.IGNORECASE)
        return _clip_phrase(f"choose {clicked.casefold()}", limit=120)
    text = _strip_action_subject(text)
    text = _drop_launcher_prefix(text)
    text = base_action_clause(text)
    text = base_following_action_verbs(text)
    text = re.sub(r",\s+and\s+", " and ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.")
    return text[:1].casefold() + text[1:] if text else ""


def _drop_launcher_prefix(value: str) -> str:
    """Remove app-opening setup when a real action follows in the same clause."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    match = re.match(
        r"^(?:opens?|launches?|starts?)\s+"
        r"(?:(?:the\s+)?(?:(?:web\s+)?app(?:lication)?|product|tool|site|website|screen|page|dashboard|portal|console)"
        r"|[A-Z][A-Za-z0-9_-]{2,})"
        r"(?:\s*,\s*|\s+and\s+)(?P<tail>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    tail = _clean(match.group("tail")).strip(" .")
    if not _MATERIAL_ACTION_RE.search(tail):
        return text
    return tail


def _visible_result_object(value: str) -> str:
    text = _clean_visible_result_phrase(value) or _clean(value)
    text = _strip_action_subject(text)
    patterns = (
        r":\s*(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer)\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+(?P<object>.+)$",
        r"\b(?:decides?|displays?|highlights?|presents?|produces?|renders?|returns?|sees?|shows?|views?|receives?|gets?|reads?|reviews?|checks?|uses?|inspects?)\s+(?P<object>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            result = match.group("object")
            result = re.split(r"(?<=[.!?])\s+", result, maxsplit=1)[0]
            result = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", result, flags=re.IGNORECASE)
            result = re.sub(r"^(?:it|them)\s+(?=(?:on|in|with|as)\b)", "the result ", result, flags=re.IGNORECASE)
            result = _drop_result_recipient(result)
            result = re.sub(
                r",?\s+and\s+(?:reads?|receives?|sees?|views?)\b.+$",
                "",
                result,
                flags=re.IGNORECASE,
            ).strip(" .")
            result = re.sub(
                r",?\s+and\s+(?:adds?|checks?|makes?|places?|records?|routes?|saves?|stores?|updates?)\b.+$",
                "",
                result,
                flags=re.IGNORECASE,
            ).strip(" .")
            return _clip_phrase(result, limit=150)
    if not _MATERIAL_ACTION_RE.search(text) and _looks_like_visible_result(text):
        return _clip_phrase(re.sub(r"^(?:this|the)\s+", "", text, flags=re.IGNORECASE), limit=150)
    return ""


def _drop_result_recipient(value: str) -> str:
    """Remove a short recipient phrase before the actual visible result object."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    text = re.sub(
        r"^(?:the\s+)?[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,3}\s+"
        r"(?=(?:a|an|the|their|its|what|whether|when|where|why)\b)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")
    return text


def _outcome_capability_fragment(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    fragment = _action_chain_fragment(text)
    if fragment and _MATERIAL_ACTION_RE.match(fragment):
        return fragment
    return f"see {_lowercase_leading_article(text)}".strip(" .")


def _strip_action_subject(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"^on\s+save,\s*", "save, ", text, flags=re.IGNORECASE)
    match = _MATERIAL_ACTION_RE.search(text)
    if match and match.start() > 0:
        prefix = text[: match.start()].strip(" ,")
        prefix_words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", prefix)
        if re.search(r"\b(?:if|that|when|where|which|while)\b", prefix, flags=re.IGNORECASE):
            return text
        if len(prefix_words) <= 6 and (
            re.search(
                r"\b(?:actor|applicant|borrower|coordinator|customer|owner|participant|patient|person|requester|reviewer|supervisor|user)\b",
                prefix,
                flags=re.IGNORECASE,
            )
            or re.search(r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b", prefix, flags=re.IGNORECASE)
            or (
                re.match(r"^(?:a|an|the|one)\s+", prefix, flags=re.IGNORECASE)
                and not re.search(
                    r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
                    prefix,
                    flags=re.IGNORECASE,
                )
            )
        ):
            text = text[match.start() :]
    return text


def _actor_signature(value: str) -> str:
    subject = _leading_subject_prefix(value)
    if not subject:
        text = _clean(value)
        match = _MATERIAL_ACTION_RE.search(text)
        if match and match.start() > 0:
            candidate = text[: match.start()].strip(" ,")
            if len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", candidate)) <= 6 and (
                re.search(
                    r"\b(?:actor|applicant|borrower|coordinator|customer|owner|participant|patient|person|requester|reviewer|supervisor|user)\b",
                    candidate,
                    flags=re.IGNORECASE,
                )
                or (
                    re.match(r"^(?:a|an|the|one)\s+", candidate, flags=re.IGNORECASE)
                    and not re.search(
                        r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
                        candidate,
                        flags=re.IGNORECASE,
                    )
                )
            ):
                subject = candidate
    if not subject:
        return ""
    subject = re.sub(r"^(?:a|an|the|one)\s+", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\s+can\s*$", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\b(?:product|system|app|application|workspace|engine|dashboard|view)\b", "", subject, flags=re.IGNORECASE)
    tokens = [
        normalize_domain_token(token, minimum=3, stopwords={"the", "one", "can"})
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", subject.casefold())
    ]
    return " ".join(token for token in tokens if token)


def _primary_actor_signature(model: FirstPathModel) -> str:
    """Return the actor for the first material user action, if the path names one."""

    actor = _actor_signature(model.material_action)
    if actor:
        return actor
    for step in model.steps:
        if _is_trivial_start(step) or _is_system_generated_action(step):
            continue
        if not _MATERIAL_ACTION_RE.search(step):
            continue
        actor = _actor_signature(step)
        if actor:
            return actor
    return ""


def _lowercase_leading_article(value: str) -> str:
    text = _clean(value).strip(" .")
    return re.sub(r"^(?:A|An|The)\b", lambda match: match.group(0).casefold(), text)


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
        "receive": "receiving",
        "receives": "receiving",
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
    "FirstPathClauses",
    "FirstPathModel",
    "first_path_action_phrase",
    "first_path_clauses",
    "first_path_capability_phrase",
    "first_path_model",
    "first_path_outcome_phrase",
    "first_path_steps",
    "material_first_path_action",
]
