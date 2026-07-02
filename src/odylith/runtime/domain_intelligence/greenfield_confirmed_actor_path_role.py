"""Accepted-path role descriptions for completed greenfield actors."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import looks_like_base_action_token, looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_terms import CONFIRMED_ACTOR_ROLE_TERMS as _ROLE_WORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import capability_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps


def actor_path_role(*, label: str, first_path: str, state: str) -> str:
    """Prefer accepted-path language over generic role templates."""

    del state
    terms = _actor_path_terms(label)
    if not terms or not _clean(first_path):
        return ""
    if _generic_user_label(label):
        return ""
    scored: list[tuple[int, int, int, str]] = []
    for index, clause in enumerate(_path_clauses(first_path)):
        if _generic_user_label(label) and not (leading_subject_prefix(clause) or _explicit_clause_subject(clause)):
            continue
        if not _clause_subject_matches_actor(clause, label=label):
            continue
        overlap = len(terms & _actor_match_terms(clause))
        if overlap > 0:
            scored.append((overlap * 10 + 12, overlap, -index, clause))
    if not scored:
        return ""
    scored.sort(reverse=True)
    clause = _short(scored[0][3], limit=170)
    if not clause:
        return ""
    clause = _focus_clause_on_actor_label(clause, label=label)
    clause = re.sub(r"^(?:a|an|the)\s+", "", clause, flags=re.IGNORECASE)
    clause = _strip_actor_subject_from_clause(clause, label=label)
    clause = _trim_following_actor_transition(clause)
    if not clause:
        return ""
    action = _sentence_action_fragment(
        readable_action_chain_phrase(clause, fallback=capability_action_clause(clause), limit=170, max_steps=3)
    )
    return f"uses the product to {action}; the outcome stays clear enough to choose the next step"


def _generic_user_label(label: str) -> bool:
    terms = _actor_match_terms(label)
    return "user" in terms and len(_actor_path_terms(label)) <= 1


def _sentence_action_fragment(value: str) -> str:
    text = _clean(value).strip(" .")
    if len(text) >= 2 and text[:1].isupper() and not text[:2].isupper():
        return f"{text[:1].casefold()}{text[1:]}"
    return text


def _trim_following_actor_transition(value: str) -> str:
    text = _clean(value).strip(" .,;:")
    if not text:
        return ""
    split = re.split(
        r",\s+(?:and\s+)?(?:a|an|the)\s+[a-z][a-z0-9'/-]*(?:\s+[a-z][a-z0-9'/-]*){0,5}\s+"
        r"(?:adds?|approves?|assigns?|checks?|chooses?|closes?|confirms?|creates?|enters?|intakes?|opens?|picks?|"
        r"records?|reviews?|routes?|saves?|selects?|signs?|submits?|updates?|uses?)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return split.strip(" .,;:") or text


def _clause_subject_matches_actor(value: str, *, label: str) -> bool:
    """Reject object-term overlap when another actor owns the clause."""

    subject = leading_subject_prefix(value) or _explicit_clause_subject(value)
    if not subject:
        return True
    subject_terms = _actor_match_terms(subject)
    actor_terms = _actor_path_terms(label)
    generic_subject = subject_terms & {"person", "user", "participant", "customer", "client"}
    if generic_subject and re.search(r"\b(person|user|participant|customer|client)\b", label, re.IGNORECASE):
        return True
    overlap = subject_terms & actor_terms
    if not overlap:
        return False
    subject_specific = subject_terms - _ROLE_WORDS
    actor_specific = actor_terms - _ROLE_WORDS
    if subject_specific and actor_specific and not (subject_specific & actor_specific):
        return False
    return True


def _explicit_clause_subject(value: str) -> str:
    words = [word.strip(".,;:") for word in _clean(value).split() if word.strip(".,;:")]
    if len(words) < 2:
        return ""
    for index, word in enumerate(words):
        if not looks_like_finite_action_token(word):
            continue
        subject_words = words[:index]
        if not subject_words:
            return ""
        subject = " ".join(subject_words).strip(" .,;:")
        subject = re.sub(
            r"^(?:a|an|the|one|this|that|each|another)\s+",
            "",
            subject,
            flags=re.IGNORECASE,
        )
        if len(subject.split()) > 6:
            return ""
        if re.search(r"\b(?:at|by|for|from|in|of|on|through|to|via|with|without)\b", subject, re.IGNORECASE):
            return ""
        return subject
    return ""


def _actor_path_terms(label: str) -> set[str]:
    return _actor_match_terms(label) - {
        "actor",
        "client",
        "customer",
        "individual",
        "manage",
        "manager",
        "managing",
        "owner",
        "participant",
        "people",
        "person",
        "track",
        "tracking",
        "user",
    }


def _actor_match_terms(value: str) -> set[str]:
    terms = set(_semantic_terms(value))
    expanded = set(terms)
    for term in terms:
        for part in re.split(r"[-_]+", term):
            if len(part) >= 3:
                expanded.add(part)
    return expanded


def _focus_clause_on_actor_label(value: str, *, label: str) -> str:
    """Focus a multi-actor clause on the actor label being described."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    role_words = _actor_path_terms(label) & _ROLE_WORDS
    if not role_words:
        return text
    words = text.split()
    for index, raw_word in enumerate(words):
        token = raw_word.strip(".,;:()").casefold()
        if token not in role_words:
            continue
        start = max(0, index - 1)
        return " ".join(words[start:]).strip(" .,;:")
    return text


def _strip_actor_subject_from_clause(value: str, *, label: str) -> str:
    """Remove a role label when it was copied into a clause as the subject."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    label_surface = _clean(label).strip(" .")
    if label_surface:
        surface_pattern = r"\s+".join(re.escape(word) for word in label_surface.split())
        text = re.sub(
            rf"^(?:a|an|the|one)?\s*{surface_pattern}\s+",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip(" .")
        text = re.sub(
            rf"^(?:a|an|the|one)?\s*(?:[A-Za-z0-9/&'()-]+\s+){{1,8}}{surface_pattern}\s+"
            r"(?=(?:can|could|must|should|will)\b)",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip(" .")
        text = _strip_leading_label_suffix_subject(text, label_surface)
    label_terms = sorted(_semantic_terms(label), key=len, reverse=True)
    if label_terms:
        lead = r"(?:a|an|the|one)?\s*(?:" + "|".join(re.escape(term) for term in label_terms) + r")"
        for _ in range(4):
            cleaned = re.sub(rf"^{lead}\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .")
            if cleaned == text:
                break
            text = cleaned
    if re.search(r"\b(person|user|participant|customer|client)\b", label, re.IGNORECASE):
        text = re.sub(
            r"^(?:a|an|the|one)\s+(?:new\s+)?(?:person|user|participant|customer|client)\s+",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip(" .")
    text = re.sub(
        r"^(?:signs?|opens?|starts?)\s+(?:in|into|the\s+app|the\s+product|the\s+site|the\s+web\s+app)\b[,.]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip(" .")


def _strip_leading_label_suffix_subject(value: str, label_surface: str) -> str:
    text = _clean(value).strip(" .")
    label_words = [word.casefold().strip(".,;:()") for word in _clean(label_surface).split() if word.strip(".,;:()")]
    words = [word for word in text.split() if word.strip(".,;:()")]
    if not label_words or len(words) <= len(label_words):
        return text
    lowered = [word.casefold().strip(".,;:()") for word in words]
    for start in range(0, len(words) - len(label_words)):
        if lowered[start : start + len(label_words)] != label_words:
            continue
        tail = words[start + len(label_words) :]
        if not tail:
            continue
        first = tail[0].casefold().strip(".,;:")
        if looks_like_base_action_token(first) or looks_like_finite_action_token(first):
            return " ".join(tail).strip(" .")
    return text


def _path_clauses(value: str) -> list[str]:
    rows = [_clean(step).strip(" .") for step in first_path_steps(value)]
    return [row for row in rows if _word_count(row) >= 4]


__all__ = ["actor_path_role"]
