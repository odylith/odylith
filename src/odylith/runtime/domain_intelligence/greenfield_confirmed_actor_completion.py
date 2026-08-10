"""Actor row completion for accepted greenfield Product Intent records."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_base_action_token, looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_actor_terms import CONFIRMED_ACTOR_ROLE_TERMS as _ROLE_WORDS
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_non_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal as _word_has_role_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_descriptions import actor_head_contains_role
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_descriptions import actor_row_description
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_descriptions import (
    readable_actor_description,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_path_role import actor_path_role
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import is_deferred_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_confirmed_items as _join
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text as _title_case
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms as _label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_text import unique_text

_DANGLING_ACTOR_LABEL_TAILS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "because",
        "by",
        "for",
        "from",
        "if",
        "in",
        "into",
        "final",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "when",
        "while",
        "with",
        "without",
    }
)


_NON_ACTOR_SUBJECT_TAILS = frozenset(
    {"decision", "entry", "evidence", "note", "packet", "ready", "record", "report", "result", "summary", "view"}
)
_DERIVED_CONTEXT_ACTOR_MODIFIERS = frozenset(
    {
        "board",
        "console",
        "readiness",
        "record",
        "records",
        "state",
        "status",
        "system",
        "view",
        "workspace",
    }
)
_MODAL_ACTION_BOUNDARY_TAILS = frozenset({"can", "could", "may", "might", "must", "shall", "should", "will", "would"})
_GENERIC_CONFIRMED_ACTOR_LABELS = frozenset(
    {"user", "individual user", "person", "individual person", "participant", "individual participant"}
)


def completed_actor_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    rows = [row for row in confirmed_text_values(intent.get("human_actors")) if not _actor_row_is_meta(row)]
    labels = [_explicit_first_path_actor_label(row, intent, title=title) or _actor_label(row, title=title) for row in rows]
    labels = [label for label in labels if label and not _actor_label_has_clause_lead(label)]
    should_derive = _should_derive_missing_actor_labels(rows)
    if should_derive and len(rows) == 1 and _single_actor_covers_first_path(rows[0], intent):
        should_derive = False
    derived_labels = (
        _derived_actor_labels(intent, title=title, allow_generic_fallback=not labels)
        if should_derive
        else []
    )
    for label in derived_labels:
        if label and not _actor_label_duplicates_existing(label, labels):
            labels.append(label)
    labels = _dedupe_actor_labels(labels)[:8]

    first_path = _clean(intent.get("first_path")) or "the accepted first path"
    state = _short(_clean(intent.get("state_object")), fallback="the accepted state")
    completed: list[str] = []
    for index, label in enumerate(labels):
        original = rows[index] if index < len(rows) else label
        description = actor_row_description(original)
        if description and _word_count(description) >= 4 and _actor_label(original, title=title).casefold() == label.casefold():
            description = readable_actor_description(description)
            completed.append(_preserve_deferred_scope(f"{label}: {description}", original))
            continue
        completed.append(
            _preserve_deferred_scope(
                _actor_description(label=label, index=index, title=title, first_path=first_path, state=state),
                original,
            )
        )
    return list(unique_text(completed))


def actor_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in confirmed_text_values(intent.get("human_actors")):
        labels.append(_clean(row.split("—", 1)[0].split(":", 1)[0]))
    return [label for label in labels if label]


def _should_derive_missing_actor_labels(rows: Sequence[str]) -> bool:
    if not rows:
        return True
    if len(rows) < 2:
        return True
    return any(not _actor_row_has_usable_description(row) or _actor_row_description_is_generated(row) for row in rows)


def _single_actor_covers_first_path(row: str, intent: Mapping[str, Any]) -> bool:
    label = _actor_label(row, title="")
    if not label or not _actor_row_has_usable_description(row):
        return False
    first_path = _clean(intent.get("first_path"))
    subject = leading_subject_prefix(first_path) or _modal_subject_prefix(first_path)
    if not subject and first_path.casefold().startswith(f"{label.casefold()} "):
        return True
    return bool(subject and _actor_reference(subject) == _actor_reference(label))


def _explicit_first_path_actor_label(row: str, intent: Mapping[str, Any], *, title: str) -> str:
    label = _clean(str(row).split("—", 1)[0].split(":", 1)[0])
    first_path = _clean(intent.get("first_path"))
    subject = leading_subject_prefix(first_path) or _modal_subject_prefix(first_path)
    if label and subject and _actor_reference(subject) == _actor_reference(label):
        return _actor_label(row, title=title) if value_starts_with_generic_actor_label(label) else _title_case(label)
    return ""


def _actor_reference(value: str) -> str:
    return re.sub(r"^(?:a|an|the)\s+", "", _clean(value), flags=re.IGNORECASE).casefold().strip()


def _modal_subject_prefix(value: str) -> str:
    words = [word.strip(".,:;!?()[]{}") for word in _clean(value).split() if word.strip(".,:;!?()[]{}")]
    for index, word in enumerate(words[1:], start=1):
        if word.casefold() not in _MODAL_ACTION_BOUNDARY_TAILS:
            continue
        subject_words = words[:index]
        if 1 <= len(subject_words) <= 5:
            return " ".join(subject_words)
    return ""


def _actor_row_description_is_generated(row: str) -> bool:
    description = actor_row_description(row).casefold()
    return bool(
        ("need the product to" in description or "needs the product to" in description)
        and "keep the result visible and reviewable" in description
    )


def _actor_label_duplicates_existing(label: str, existing_labels: Sequence[str]) -> bool:
    candidate = _clean(label).casefold()
    if not candidate:
        return True
    for existing in existing_labels:
        current = _clean(existing).casefold()
        if candidate == current or candidate.endswith(f" {current}"):
            return True
        candidate_tail = candidate.rsplit(" ", 1)[-1]
        if current in _GENERIC_CONFIRMED_ACTOR_LABELS and candidate_tail == current.rsplit(" ", 1)[-1]:
            return True
        if current.endswith(f" {candidate}") or current.startswith(f"{candidate} "):
            return True
        if _actor_label_is_context_expanded_duplicate(candidate, current):
            return True
    return False


def _dedupe_actor_labels(labels: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    for label in unique_text(labels):
        cleaned = re.sub(r"^(?:one|first|main|primary)\s+", "", _clean(label), flags=re.IGNORECASE).strip()
        if cleaned and not _actor_label_duplicates_existing(cleaned, deduped):
            deduped.append(cleaned)
    return deduped


def _actor_label_is_context_expanded_duplicate(candidate: str, current: str) -> bool:
    candidate_tokens = _actor_label_context_tokens(candidate)
    current_tokens = _actor_label_context_tokens(current)
    if len(candidate_tokens) < 3 or len(current_tokens) < 3:
        return False
    if candidate_tokens[-1] != current_tokens[-1]:
        return False
    candidate_prefix = candidate_tokens[:-1]
    current_prefix = current_tokens[:-1]
    shorter, longer = (
        (candidate_prefix, current_prefix)
        if len(candidate_prefix) <= len(current_prefix)
        else (current_prefix, candidate_prefix)
    )
    if not shorter or len(longer) <= len(shorter):
        return False
    extra = longer[len(shorter) :]
    if longer[: len(shorter)] == shorter:
        return any(token in _DERIVED_CONTEXT_ACTOR_MODIFIERS for token in extra)
    if len(longer) > len(shorter) and longer[-len(shorter) :] == shorter:
        return True
    return False


def _actor_label_context_tokens(value: str) -> tuple[str, ...]:
    return tuple(token for token in _clean(value).casefold().replace("-", " ").split() if token)


def project_specific_actor_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    title = _clean(intent.get("title")) or "Project"
    for row in confirmed_text_values(intent.get("human_actors")):
        label = _clean(row.split("—", 1)[0].split(":", 1)[0]).strip(" .")
        if label and _actor_label_is_usable(label):
            labels.append(label)
            continue
        repaired = _actor_label(row, title=title)
        if repaired and _actor_label_is_usable(repaired):
            labels.append(repaired)
    return list(unique_text(labels))


def value_starts_with_generic_actor_label(value: Any) -> bool:
    words = [word.casefold().strip(".,:;()[]{}") for word in _clean(value).split()]
    words = [word for word in words if word]
    if not words or words[0] not in _GENERIC_ACTOR_VALUE_HEADS:
        return False
    if len(words) == 1:
        return True
    action = words[1]
    return bool(
        action in {"can", "cannot", "could", "is", "must", "needs", "need", "should", "will", "would"}
        or looks_like_finite_action_token(action)
    )


def _preserve_deferred_scope(row: str, source: str) -> str:
    text = _clean(row).rstrip(".")
    if not text or not is_deferred_actor(source) or is_deferred_actor(text):
        return row
    return f"{text}; deferred from the first path."


def _actor_row_is_meta(value: str) -> bool:
    """Reject generated summary rows that are not human participants."""

    text = _clean(value).casefold()
    return bool(
        re.search(r"\badditional\s+accepted\s+(?:items|actors|systems)\s+remain\b", text)
        or re.search(r"\bother\s+accepted\s+(?:items|actors|systems)\b", text)
        or re.search(r"\bplus\s+\d+\s+more\b", text)
        or text in {"human actors", "participants", "people named in the accepted product direction"}
    )


def _actor_description(*, label: str, index: int, title: str, first_path: str, state: str) -> str:
    label_text = label.casefold()
    if re.search(r"\b(public\s+figure|public\s+person|tracked|being\s+tracked|subject|official|executive|creator)\b", label_text):
        body = "is represented by lawful source records, evidence, confidence, and privacy limits; the product must not imply private access, endorsement, or guaranteed outcome"
        return f"{label}: {body}."
    path_role = actor_path_role(label=label, first_path=first_path, state=state)
    if path_role:
        return f"{label}: {path_role}."
    if re.search(r"\b(compliance|policy|privacy|legal|risk|safety)\b", label_text):
        body = "reviews access, privacy, policy, risk, and evidence boundaries"
    elif re.search(r"\b(user|person|people|individual|researcher|investor|analyst|operator)\b", label_text):
        body = f"uses {title} to complete the first product path, review the result, and decide what to do next"
    elif re.search(r"\b(author|applicant|submitter|requester|customer|client)\b", label_text):
        body = "provides the information the product needs and expects a clear result, explanation, and next step"
    elif re.search(r"\b(editor|manager|chair|coordinator|operator|supervisor|lead|owner|director)\b", label_text):
        body = "keeps the product outcome aligned with the real operational goal and decides when exceptions need human judgment"
    elif re.search(r"\bteam\b", label_text):
        body = "owns the operating context around the request, keeps expectations clear, and uses the product outcome to coordinate follow-up"
    elif re.search(r"\b(reviewer|inspector|evaluator|analyst|auditor|expert|approver|compliance)\b", label_text):
        body = "uses the product output to review quality, challenge weak results, and decide whether follow-up is needed"
    elif re.search(r"\b(coach|trainer|advisor|consultant|specialist)\b", label_text):
        body = "reviews progress, guidance quality, evidence, and escalation signals where the accepted path needs human support"
    elif re.search(r"\b(participant|observer|applicant)\b", label_text):
        body = "supplies input, context, or objections that must remain traceable to the first-path decision"
    elif re.search(r"\b(admin|administrator|config|maintainer|support|scheduler)\b", label_text):
        body = "owns the policies, settings, and operating limits that keep the product outcome reliable"
    else:
        body = (
            "supplies context, reviews the result, or takes the next step named by the first release"
        )
    return f"{label}: {body}."


def _actor_row_has_usable_description(value: str) -> bool:
    return bool(actor_row_description(value))


def _derived_actor_labels(intent: Mapping[str, Any], *, title: str, allow_generic_fallback: bool = True) -> list[str]:
    focus = _focus_label(title)
    title_reference = _actor_reference(title)
    first_path = _clean(intent.get("first_path"))
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    candidate_sources = [first_path]
    if allow_generic_fallback:
        candidate_sources.extend([state, story, _actor_context(intent)])
    candidates = unique_text(
        [
            *(
                candidate
                for source in candidate_sources
                for candidate in _role_candidates(source)
            ),
        ]
    )
    labels: list[str] = []
    for candidate in candidates:
        if _word_count(candidate) <= 5:
            label = _actor_label_display(candidate)
            if _actor_reference(label) == title_reference:
                continue
            if value_starts_with_generic_actor_label(label):
                role = label.casefold()
                label = _actor_label_display(f"{_role_focus(focus, role)} {role}")
            if _actor_label_is_usable(label) and _derived_actor_label_has_human_signal(label):
                labels.append(label)
    labels = _dedupe_actor_labels(list(unique_text(labels)))
    if allow_generic_fallback and not labels:
        labels.extend(
            [
                f"{focus} operator",
                f"{focus} reviewer",
                f"{focus} support owner",
                f"{focus} release decision owner",
            ]
        )
    return list(unique_text(labels))


def _derived_actor_label_has_human_signal(value: str) -> bool:
    words = [word.casefold().strip(".,;:()[]{}") for word in _clean(value).split()]
    return bool(
        has_human_actor_role_signal(value)
        or (
            words
            and _looks_like_derived_human_token(words[-1])
            and not has_non_human_actor_signal(value)
        )
    )


def _looks_like_derived_human_token(value: str) -> bool:
    token = value[:-1] if value.endswith("s") else value
    return len(token) >= 5 and token.endswith(("ant", "ent", "er", "ian", "ist", "or", "ee", "owner"))


def _role_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|;\s+", _clean(text)):
        subject = _subject_candidate(sentence)
        if subject:
            candidates.append(subject)
        words = _label_terms(sentence)
        for index, word in enumerate(words):
            role_word = word.casefold()
            if role_word not in _ROLE_WORDS and not (
                role_word.endswith("s") and role_word[:-1] in _ROLE_WORDS
            ):
                continue
            if _role_token_is_artifact_context(words, index):
                continue
            previous = words[index - 1].casefold().strip(".,;:-") if index > 0 else ""
            action_modifier = _has_action_shaped_role_modifier(words, index)
            start = (
                index - 1
                if action_modifier
                else (index if previous in {"by", "for", "to", "with"} else max(0, index - 2))
            )
            phrase = " ".join(words[start : index + 1])
            phrase = re.sub(
                r"^(?:a|an|and|the|one|first|main|primary|current)\s+",
                "",
                phrase,
                flags=re.IGNORECASE,
            )
            phrase_words = phrase.split()
            if (
                len(phrase_words) >= 3
                and phrase_words[-2].casefold() in {"a", "an", "the"}
                and phrase_words[0].casefold().endswith("ing")
            ):
                phrase = phrase_words[-1]
            if not action_modifier:
                phrase = _trim_non_actor_lead_words(phrase)
            if (
                phrase
                and phrase.casefold() not in {"team"}
                and not _actor_label_has_clause_lead(phrase)
                and not phrase.casefold().startswith(("product ", "project ", "workflow "))
            ):
                candidates.append(phrase)
    return list(unique_text(candidates))


def _subject_candidate(sentence: str) -> str:
    relative = re.match(
        r"^(?P<head>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+(?:who|that)\s+(?P<body>.+)$",
        _clean(sentence),
        flags=re.IGNORECASE,
    )
    if relative and actor_head_contains_role(relative.group("head")):
        return _trim_non_actor_lead_words(relative.group("head"))
    subject = leading_subject_prefix(sentence)
    if not subject:
        return ""
    subject = _actor_head_before_setup_action(subject) or subject
    subject = re.sub(r"^(?:a|an|the|one|this|that|each|another)\s+", "", subject, flags=re.IGNORECASE).strip(" .")
    subject = _strip_modal_subject_tail(subject)
    words = subject.split()
    if not 1 <= len(words) <= 4:
        return ""
    if words[-1].casefold().strip(".,;:()") in _NON_ACTOR_SUBJECT_TAILS:
        return ""
    lowered = subject.casefold()
    if lowered in {"app", "application", "product", "service", "system", "tool", "workspace"}:
        return ""
    if re.search(
        r"\b(?:app|application|console|dashboard|engine|platform|product|service|system|tool|workspace)\b",
        lowered,
    ):
        return ""
    return _trim_non_actor_lead_words(subject)


def _strip_modal_subject_tail(value: str) -> str:
    words = _clean(value).strip(" .").split()
    if len(words) < 2:
        return _clean(value).strip(" .")
    if words[-1].casefold().strip(".,;:()") not in _MODAL_ACTION_BOUNDARY_TAILS:
        return _clean(value).strip(" .")
    candidate = " ".join(words[:-1]).strip(" .")
    return candidate or _clean(value).strip(" .")


def _actor_head_before_setup_action(subject: str) -> str:
    tokens = [token.strip(".,;:()") for token in _clean(subject).split()]
    if len(tokens) < 3 or tokens[0].casefold() not in {"a", "an", "the", "one", "this", "that", "each", "another"}:
        return ""
    setup_verbs = {"open", "opens", "launch", "launches", "start", "starts", "enter", "enters"}
    for index, token in enumerate(tokens[1:], start=1):
        lower = token.casefold()
        if lower in setup_verbs or (
            lower in {"log", "logs", "sign", "signs"} and index + 1 < len(tokens) and tokens[index + 1].casefold() == "in"
        ):
            actor_words = tokens[1:index]
            if 1 <= len(actor_words) <= 4:
                return " ".join([tokens[0], *actor_words])
            return ""
    return ""


def _role_token_is_artifact_context(words: Sequence[str], index: int) -> bool:
    previous_token = words[index - 1].casefold().strip(".,;:-") if index > 0 else ""
    previous_previous_token = words[index - 2].casefold().strip(".,;:-") if index > 1 else ""
    next_token = words[index + 1].casefold().strip(".,;:-") if index + 1 < len(words) else ""
    sentence = " ".join(words).casefold()
    if re.search(r"\b(?:defer(?:red|s)?|out\s+of\s+scope|non[-\s]?goals?|later|future|not\s+included)\b", sentence):
        return True
    if previous_token in {"explicit", "using"}:
        return True
    if looks_like_base_action_token(previous_token) or looks_like_finite_action_token(previous_token):
        # Some human roles use an action-shaped noun as a modifier, as in
        # "release managers decide" or "support engineers deploy". The
        # following predicate makes that role boundary explicit.
        if not _has_action_shaped_role_modifier(words, index):
            return True
    if previous_previous_token in {"without", "instead", "before", "after"} and previous_token.endswith("ing"):
        return True
    artifact_neighbors = {
        "approval",
        "approvals",
        "confirmation",
        "contact",
        "console",
        "dashboard",
        "decision",
        "detail",
        "details",
        "field",
        "fields",
        "follow-up",
        "history",
        "information",
        "note",
        "notes",
        "record",
        "request",
        "ready",
        "status",
        "visible",
    }
    if index >= 2 and _looks_plural_object_token(previous_token) and (
        _looks_plural_object_token(next_token) or next_token in artifact_neighbors
    ):
        return True
    if previous_token in artifact_neighbors or next_token in artifact_neighbors:
        return True
    current = words[index].casefold()
    return "-" in current and any(part in artifact_neighbors for part in current.split("-"))


def _has_action_shaped_role_modifier(words: Sequence[str], index: int) -> bool:
    if index <= 0 or index + 1 >= len(words):
        return False
    previous = words[index - 1].casefold().strip(".,;:-")
    following = words[index + 1].casefold().strip(".,;:-")
    return bool(
        (looks_like_base_action_token(previous) or looks_like_finite_action_token(previous))
        and (looks_like_base_action_token(following) or looks_like_finite_action_token(following))
    )


def _looks_plural_object_token(value: str) -> bool:
    token = str(value or "").casefold().strip(".,;:-")
    if len(token) <= 3 or not token.endswith("s") or token.endswith(("ous", "ss")):
        return False
    singular = token[:-1]
    return singular not in _ROLE_WORDS


def _trim_non_actor_lead_words(value: str) -> str:
    words = _clean(value).split()
    non_actor_leads = {
        "a",
        "answer",
        "against",
        "an",
        "and",
        "after",
        "before",
        "because",
        "by",
        "displays",
        "decision",
        "detail",
        "details",
        "evidence",
        "for",
        "gives",
        "history",
        "in",
        "input",
        "places",
        "provides",
        "request",
        "note",
        "notes",
        "outcome",
        "path",
        "proof",
        "reason",
        "record",
        "release",
        "result",
        "returns",
        "scope",
        "shows",
        "state",
        "status",
        "summary",
        "the",
        "then",
        "to",
        "using",
        "when",
        "where",
        "which",
        "with",
    }
    while len(words) > 1 and words[0].casefold().strip(".,;:") in non_actor_leads:
        words.pop(0)
    while len(words) > 1 and _leading_action_token_with_role_tail(words):
        words.pop(0)
    if len(words) > 1 and words[-2].casefold().strip(".,;:") in non_actor_leads:
        words = words[-1:]
    return " ".join(words)


def _leading_action_token_with_role_tail(words: Sequence[str]) -> bool:
    if len(words) < 2:
        return False
    lead = words[0].casefold().strip(".,;:")
    if not lead or _word_has_role_signal(lead):
        return False
    if not (looks_like_base_action_token(lead) or looks_like_finite_action_token(lead)):
        return False
    return any(_word_has_role_signal(word.casefold().strip(".,;:")) for word in words[1:])


def _actor_label_has_clause_lead(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:and|or|where|when|if|because|so|that|which|what|why|how|with|against|from|until|before|after|"
            r"displays?|gives?|places?|provides?|returns?|shows?)\b",
            _clean(value).casefold(),
        )
    )


def _actor_label_has_dangling_tail(value: str) -> bool:
    words = [word.casefold().strip(".,;:()[]{}") for word in _clean(value).split()]
    return bool(words and words[-1] in _DANGLING_ACTOR_LABEL_TAILS)


def _actor_label_is_action_fragment(value: str) -> bool:
    words = [word for word in (raw.casefold().strip(".,;:()[]{}") for raw in _clean(value).split()) if word]
    has_human_signal = any(_word_has_role_signal(word) or _looks_like_derived_human_token(word) for word in words)
    return bool(
        words
        and not has_human_signal
        and (looks_like_base_action_token(words[0]) or looks_like_finite_action_token(words[0]) or words[0].endswith("ing"))
    )


def _actor_label_has_embedded_action(value: str) -> bool:
    words = [word for word in (raw.casefold().strip(".,;:()[]{}") for raw in _clean(value).split()) if word]
    for index, word in enumerate(words[1:], start=1):
        if _word_has_role_signal(word):
            continue
        if (
            any(_word_has_role_signal(previous) for previous in words[:index])
            and (looks_like_base_action_token(word) or looks_like_finite_action_token(word) or word.endswith("ing"))
        ):
            return True
    return False


def _actor_label_is_usable(value: str) -> bool:
    return (
        bool(_clean(value))
        and not value_starts_with_generic_actor_label(value)
        and not _actor_label_has_clause_lead(value)
        and not _actor_label_has_dangling_tail(value)
        and not _actor_label_is_action_fragment(value)
        and not _actor_label_has_embedded_action(value)
    )


def _actor_label(row: str, *, title: str) -> str:
    raw = _clean(str(row).split("—", 1)[0].split(":", 1)[0])
    raw = re.sub(r"^(?:a|an|the)\s+", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"^(?:one|first|main|primary)\s+", "", raw, flags=re.IGNORECASE).strip()
    if not raw:
        return ""
    generic_role = re.sub(r"^individual\s+", "", raw.casefold())
    if generic_role in {"person", "participant", "user"}:
        label = _actor_label_display(f"{_role_focus(_focus_label(title), generic_role)} {generic_role}")
        return label if _actor_label_is_usable(label) else ""
    accepted = accepted_actor_label(str(row), project_focus=_focus_label(title))
    if accepted:
        accepted = re.sub(r"^(?:one|first|main|primary)\s+", "", accepted, flags=re.IGNORECASE).strip()
        accepted = accepted if _actor_row_has_usable_description(str(row)) else _actor_label_display(accepted)
        return accepted if _actor_label_is_usable(accepted) else ""
    specific = _specific_role_label(raw)
    if specific:
        return specific if _actor_label_is_usable(specific) else ""
    if raw.casefold() in {"operator", "reviewer", "user", "owner", "helper", "support", "admin"}:
        raw = f"{_role_focus(_focus_label(title), raw)} {raw}"
    label = _actor_label_display(raw)
    return label if _actor_label_is_usable(label) else ""


def _actor_label_display(value: str) -> str:
    return _title_case(_clean(value))


def _specific_role_label(value: str) -> str:
    match = re.match(
        r"^(?P<role>author|reviewer|admin|administrator|editor|operator|manager|coordinator|supervisor|owner)\s+(?P<tail>.+)$",
        _clean(value),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    role = match.group("role")
    if match.group("tail").casefold().startswith("or "):
        return ""
    tail = re.sub(
        r"^(?:submitting|evaluating|configuring|managing|reviewing|approving|owning|operating|coordinating)\s+",
        "",
        match.group("tail"),
        flags=re.IGNORECASE,
    ).strip(" .")
    tail = re.sub(r"^(?:a|an|the)\s+", "", tail, flags=re.IGNORECASE)
    if _word_count(tail) < 2:
        return ""
    return _title_case(f"{_role_focus(tail, role)} {role}")


def _role_focus(focus: str, role: str) -> str:
    text = _clean(focus)
    words = text.split()
    while words and words[-1].casefold() in _DERIVED_CONTEXT_ACTOR_MODIFIERS:
        words.pop()
    text = " ".join(words)
    if role.casefold() == "reviewer":
        text = re.sub(r"\breview$", "", text, flags=re.IGNORECASE).strip()
    return text or _clean(focus) or "Project"


def _actor_context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("title")),
        _clean(intent.get("product_story")),
        _clean(intent.get("problem")),
        _clean(intent.get("customer")),
        _clean(intent.get("opportunity")),
        _clean(intent.get("product_view")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        " ".join(confirmed_text_values(intent.get("human_actors"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def customer_summary(actors: Sequence[str], *, title: str) -> str:
    """Return the primary customer label from completed actor rows."""

    labels = [_clean(value).split("—", 1)[0].split(":", 1)[0].strip(" .") for value in actors]
    labels = [label for label in labels if label]
    if not labels:
        return f"{_focus_label(title)} users"
    if len(labels) == 1 or _secondary_role_is_supporting(labels[1]):
        return labels[0]
    return _join(labels[:2])


def needs_verb(label: str) -> str:
    """Return the finite form for a completed customer label."""

    text = _clean(label).casefold()
    if not text or " and " in text or "," in text or text.endswith(("s", "team", "teams")):
        return "need"
    return "needs"


def _secondary_role_is_supporting(label: str) -> bool:
    return bool(
        re.search(
            r"\b(?:admin|administrator|advisor|analyst|approver|auditor|coach|coordinator|evaluator|expert|inspector|"
            r"lead|manager|officer|operator|reviewer|specialist|supervisor|support)\b",
            _clean(label),
            re.IGNORECASE,
        )
    )


_GENERIC_ACTOR_VALUE_HEADS = {
    "admin",
    "administrator",
    "customer",
    "operator",
    "owner",
    "participant",
    "person",
    "reviewer",
    "support",
    "user",
}
__all__ = [
    "actor_labels",
    "actor_row_description",
    "completed_actor_rows",
    "customer_summary",
    "needs_verb",
    "project_specific_actor_labels",
    "value_starts_with_generic_actor_label",
]
