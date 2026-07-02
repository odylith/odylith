"""Own proof, rationale, and semantic language shaping for confirmed backlog artifacts."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_item
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text as _compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_occurrences
from odylith.runtime.domain_intelligence.greenfield_deferral_predicates import has_terminal_deferral_predicate
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_adjacent_duplicate_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import _has_mechanical_need_to_turn
from odylith.runtime.domain_intelligence.greenfield_text import clean_text as _clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values as _text_values


_BACKLOG_TERM_STOPWORDS = frozenset(
    {
        "and",
        "can",
        "for",
        "from",
        "into",
        "must",
        "that",
        "then",
        "the",
        "this",
        "when",
        "with",
        "without",
    }
)
_PRODUCT_SHARE_STOPWORDS = _BACKLOG_TERM_STOPWORDS | frozenset(
    {
        "accepted",
        "action",
        "complete",
        "first",
        "path",
        "product",
        "release",
        "result",
        "state",
        "their",
        "user",
    }
)
_RESULT_ACTION_WORDS = frozenset(
    {
        "act",
        "acts",
        "acting",
        "get",
        "gets",
        "getting",
        "reach",
        "reaches",
        "reaching",
        "read",
        "reads",
        "reading",
        "receive",
        "receives",
        "receiving",
        "see",
        "sees",
        "seeing",
        "use",
        "uses",
        "using",
        "view",
        "views",
        "viewing",
    }
)
_INCOMPLETE_TERMINAL_WORDS = frozenset(
    {
        "a",
        "against",
        "an",
        "and",
        "around",
        "as",
        "at",
        "because",
        "between",
        "for",
        "from",
        "into",
        "of",
        "or",
        "plus",
        "the",
        "this",
        "through",
        "to",
        "toward",
        "towards",
        "until",
        "via",
        "when",
        "while",
        "with",
        "without",
    }
)
_INCOMPLETE_TERMINAL_MODIFIERS = frozenset(
    {
        "actionable",
        "accepted",
        "clear",
        "complete",
        "concrete",
        "daily",
        "final",
        "first",
        "reviewable",
        "safe",
        "safety",
        "specific",
        "trusted",
        "visible",
    }
)
_OPEN_CONNECTOR_INTERRUPTER_RE = re.compile(
    r"\b(?:and|or),\s+(?:after|although|as|before|because|if|once|until|when|where|while)\b[^,.;]*$",
    re.IGNORECASE,
)


def proof_claim_summary(value: str, *, limit: int = 260) -> str:
    raw_text = _compact_text(value).strip(" .")
    text = _strip_proof_claim_intro(raw_text)
    text = _drop_secondary_ranking_claims(text)
    text = _short_summary(text, limit=limit).strip(" .")
    text = _trim_incomplete_terminal_phrase(text)
    return text or _trim_incomplete_terminal_phrase(_short_summary(raw_text, limit=limit).strip(" ."))


def semantic_words(value: str) -> set[str]:
    return set(ordered_terms(value, minimum=3, stopwords=_BACKLOG_TERM_STOPWORDS))


def result_content_words(value: str) -> set[str]:
    """Return result terms without generic transition or perception verbs."""

    return {_canonical_result_word(word) for word in semantic_words(value)} - _RESULT_ACTION_WORDS


def _canonical_result_word(value: str) -> str:
    token = str(value or "").casefold().strip(" .,:;")
    if len(token) > 5 and token.endswith("ied"):
        return f"{token[:-3]}y"
    if len(token) > 5 and token.endswith("ed"):
        stem = token[:-2]
        if stem.endswith(("at", "it", "iz", "ag")):
            return f"{stem}e"
        return stem
    if len(token) > 6 and token.endswith("ing"):
        stem = token[:-3]
        if stem.endswith(("at", "it", "iz", "ag")):
            return f"{stem}e"
        return stem
    return token


def result_terms_covered(needle: str, haystack: str) -> bool:
    needle_terms = result_content_words(needle)
    if not needle_terms:
        return False
    return needle_terms <= result_content_words(haystack)


def sentence_fragment(value: str) -> str:
    text = drop_adjacent_duplicate_words(_short_summary(value, limit=260).strip(" ."))
    if not text:
        return ""
    if re.match(r"^[A-Z]{2,}\b", text):
        return text
    return text[:1].casefold() + text[1:]


def drop_adjacent_duplicate_words(value: str) -> str:
    words = str(value or "").split()
    cleaned: list[str] = []
    previous = ""
    for word in words:
        normalized = re.sub(r"[^a-z0-9]+", "", word.casefold())
        if normalized and normalized == previous and len(normalized) >= 4:
            continue
        cleaned.append(word)
        previous = normalized
    return " ".join(cleaned)


def proof_focus_phrase(value: str, *, fallback: str) -> str:
    candidates: list[tuple[int, int, str]] = []
    for index, clause in enumerate(re.split(r"\s*,\s*|\s+\band\b\s+", sentence_fragment(value))):
        text = sentence_fragment(clause).strip(" .")
        if not text or word_count(text) > 6:
            continue
        if not re.search(r"\b(?:approval|decision|judgment|outcome|reason|rejection|signoff|status)\b", text, re.I):
            continue
        score = 3
        if re.search(
            r"\b(?:actor|admin|administrator|coordinator|customer|human|manager|operator|owner|reviewer|user)\b",
            text,
            re.I,
        ):
            score += 4
        if re.search(r"\b(?:final|release|review|trusted)\b", text, re.I):
            score += 1
        candidates.append((score, -index, text))
    if not candidates:
        return fallback
    candidates.sort(reverse=True)
    return candidates[0][2]


def compact_workstream_title_connector(value: str) -> str:
    text = value.strip()
    marker = "while keeping "
    search_from = 0
    while True:
        index = text.casefold().find(marker, search_from)
        if index < 0:
            return text
        if index > 0 and text[index - 1].isalnum():
            search_from = index + len(marker)
            continue
        before = text[:index].rstrip()
        after = text[index + len(marker) :].lstrip()
        text = f"{before} with {after}".strip() if before else f"with {after}".strip()
        search_from = max(len(before), 0)


def dedupe_capability_phrase(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" .")
    if not text:
        return ""
    clauses = [part.strip(" ,") for part in re.split(r",\s+|\s+and\s+", text) if part.strip(" ,")]
    if len(clauses) <= 1:
        return text
    seen: set[str] = set()
    unique: list[str] = []
    for clause in clauses:
        key = _capability_clause_key(clause)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(clause)
    if len(unique) == len(clauses):
        return text
    if len(unique) == 1:
        return unique[0]
    if len(unique) == 2:
        return f"{unique[0]} and {unique[1]}"
    return f"{', '.join(unique[:-1])}, and {unique[-1]}"


def metric_capability_summary(value: str) -> str:
    text = _strip_leading_connector(_clean_text(value).strip(" ."))
    if text.casefold().startswith("the "):
        tail = text[4:].strip(" .")
        first_tail_word = tail.split(maxsplit=1)[0] if tail else ""
        if first_tail_word[:1].islower():
            text = tail
    if not text:
        return "the promised first-path result"
    parts = []
    for part in _text_values(text, split_scalar=True, split_commas=True):
        part = part.strip(" .")
        part = _strip_leading_connector(part)
        if part:
            parts.append(part)
    if len(parts) >= 2 and any(looks_like_action_clause(part) for part in parts):
        return "the completed first-path actions"
    if len(parts) >= 3:
        return f"{parts[0]} through the promised result"
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return parts[0] if parts else text


def evidence_scope_phrase(value: str, *, actor: str) -> str:
    text = _strip_leading_connector(_clean_text(value).strip(" ."))
    if not text:
        return "the promised first-path result"
    lowered = text.casefold()
    if lowered.startswith(("a ", "an ", "one ", "the ", "this ", "that ")):
        return text
    actor_subject = _clean_text(actor).strip(" .") or "the user"
    if re.match(r"^(?:a|an|the|one|this|that|each)\s+", actor_subject, flags=re.IGNORECASE):
        actor_subject = actor_subject[:1].casefold() + actor_subject[1:]
    elif re.match(r"^(?:people|users|customers|operators|reviewers)\b", actor_subject, flags=re.IGNORECASE):
        actor_subject = actor_subject[:1].casefold() + actor_subject[1:]
    else:
        actor_subject = f"the {actor_subject[:1].casefold()}{actor_subject[1:]}"
    if lowered.startswith("can "):
        return f"the path where {actor_subject} {text}"
    if looks_like_action_clause(text):
        return f"the path where {actor_subject} can {text}"
    return f"the first-path evidence for {text}"


def proof_focus_summary(value: str) -> str:
    text = _strip_leading_connector(_clean_text(value).strip(" ."))
    if not text:
        return "review evidence"
    parts: list[str] = []
    for part in _text_values(text, split_scalar=True, split_commas=True):
        parts.extend(
            normalized
            for candidate in part.split(" and ")
            if (normalized := _strip_leading_connector(candidate.strip(" .")))
        )
    if len(parts) >= 3:
        return f"{parts[0]}, {parts[1]}, and {parts[2]}"
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return parts[0] if parts else text


def rationale_lines(
    *,
    label: str,
    title: str,
    opportunity: str,
    first_slice: str,
    proof_boundary: str,
    deferred_scope: Sequence[str] = (),
) -> list[str]:
    why_now = _short_summary(opportunity, limit=180).strip(" .")
    expected_outcome = _short_summary(first_slice, limit=200).strip(" .")
    if looks_mechanical_summary(why_now):
        why_now = f"{title} proves a bounded part of the accepted {label} first path before adjacent scope expands"
    if looks_mechanical_summary(expected_outcome):
        expected_outcome = f"{title} produces reviewable state, blocker behavior, recovery evidence, and handoff proof"
    if not why_now:
        why_now = "Clarify the accepted product boundary before implementation starts"
    if not expected_outcome:
        expected_outcome = "Produce the first reviewable release outcome"
    scope_focus = rationale_scope_focus(first_slice, fallback=title)
    if _too_similar(why_now, expected_outcome):
        why_now = f"{title} gives release planning one complete, reviewable outcome before optional scope expands"
    if _too_similar(scope_focus, expected_outcome):
        scope_focus = _short_summary(title, limit=90).strip(" .") or _short_summary(label, limit=90).strip(" .") or "the accepted slice"
    deferred_focus = rationale_deferred_focus(
        value=proof_boundary,
        label=label,
        fallback=scope_focus,
        deferred_scope=deferred_scope,
    )
    proof_focus = rationale_proof_focus(proof_boundary, fallback=expected_outcome)
    release_basis = rationale_release_basis(title=title, label=label, first_slice=first_slice, proof_boundary=proof_boundary)
    deferred_rationale = _scoped_deferred_rationale(
        title=title,
        rationale=_deferred_rationale_sentence(deferred_focus),
    )
    lines = [
        f"- why now: {why_now}.",
        f"- expected outcome: {expected_outcome}.",
        f"- tradeoff: Keep this slice centered on {scope_focus} so implementation does not absorb unrelated release claims.",
        f"- deferred for now: {deferred_rationale}.",
        f"- ranking basis: {release_basis}.",
    ]
    return [collapse_adjacent_duplicate_terms(line) for line in lines]


def rationale_scope_focus(value: str, *, fallback: str) -> str:
    text = sentence_fragment(value)
    text = re.sub(r"^(?:deliver|implement|produce|start(?:\s+with)?|build)\s+(?:one\s+)?", "", text, flags=re.IGNORECASE)
    text = re.split(r"\s+without\s+|\s+and\s+explain\b|\s+and\s+see\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = _short_summary(text, limit=120).strip(" .")
    text = re.sub(r"^(?:with|where|when)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    return text or sentence_fragment(fallback) or "the accepted slice"


def rationale_proof_focus(value: str, *, fallback: str) -> str:
    text = proof_claim_summary(value, limit=160).strip(" .")
    text = re.split(r"\s+without\s+|\s+and\s+missing\b|\s+and\s+deferred\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    if word_count(text) > 14:
        text = _bounded_complete_proof_focus(text, max_words=18)
    return sentence_fragment(text or fallback) or "the proven first path"


def rationale_deferred_focus(*, value: str, label: str, fallback: str, deferred_scope: Sequence[str] = ()) -> str:
    """Return the explicit deferred scope without repeating the first-slice path."""

    for row in deferred_scope:
        selected = _deferred_focus_sentence(row) or boundary_clause_item(str(row), limit=120)
        if selected and not _too_similar(selected, fallback):
            return selected[:1].upper() + selected[1:]
    text = _compact_text(value).strip(" .")
    deferred: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        cleaned = _deferred_focus_sentence(sentence)
        if cleaned:
            deferred.append(cleaned)
    selected = _short_summary(deferred[0], limit=120).strip(" .") if deferred else ""
    if selected and not _too_similar(selected, fallback):
        return selected[:1].upper() + selected[1:]
    label_text = _short_summary(label, limit=90).strip(" .")
    return f"Adjacent {label_text or 'product'} workflows"


def rationale_release_basis(*, title: str, label: str, first_slice: str, proof_boundary: str) -> str:
    title_text = _short_summary(title, limit=90).strip(" .") or sentence_fragment(title)
    slice_terms = semantic_words(first_slice)
    proof_terms = semantic_words(proof_boundary)
    shared = sorted((slice_terms & proof_terms) - {"can", "must", "release", "result", "state"})
    if shared:
        proof_focus = rationale_proof_focus(proof_boundary, fallback=first_slice)
        if _release_gate_wrapper_focus(proof_focus):
            proof_focus = rationale_scope_focus(first_slice, fallback=title_text)
        return f"{title_text} ranks before optional expansion because {label} must prove {proof_focus} before adjacent scope enters the release"
    return f"{title_text} ranks before optional expansion because it ties the accepted path to reviewable {label} release evidence"


def looks_mechanical_summary(value: str) -> bool:
    text = _compact_text(value)
    if not text:
        return False
    lowered = text.casefold()
    repeated_required = word_occurrences(text, "required")
    return bool(
        repeated_required >= 2
        or re.search(r"\bactor identity,\s+validation context,\s+and upstream handoff\b", lowered)
        or re.search(r"\bblocker signal,\s+review rationale,\s+and downstream handoff\b", lowered)
        or re.search(r"\b(?:accepted\s+first\s+path|accepted\s+proof\s+boundary|first\s+path\s+entry)\b", lowered)
        or re.search(r"\b(?:visible[- ]result\s+event|rendered\s+dashboard|dashboard\s+renders?\s+the\s+visible\s+result)\b", lowered)
        or re.search(r"\b(?:source\s+evidence,\s+visible\s+blockers|systems\s+that\s+own\s+the\s+handoff)\b", lowered)
        or re.search(r"\bis\s+not\s+trustworthy\s+when\b", lowered)
        or _has_mechanical_need_to_turn(text)
        or re.search(r"\bfirst\s+release\s+can\s+collect\s+activity\b", lowered)
        or re.search(r"^on\s+save\b", lowered)
    )


def has_problem_tension(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:without|risk|harm|danger|fails?|failure|cannot|missing|unclear|blocked|drift|stale|unsupported|untrusted|needs?|must|if|when|unless|because|otherwise|prevents?|reduces?|no)\b",
            _compact_text(value).casefold(),
        )
    )


def shares_product_terms(left: str, right: str) -> bool:
    left_terms = set(ordered_terms(left, minimum=4, stopwords=_PRODUCT_SHARE_STOPWORDS))
    right_terms = set(ordered_terms(right, minimum=4, stopwords=_PRODUCT_SHARE_STOPWORDS))
    if not left_terms or not right_terms:
        return False
    return len(left_terms & right_terms) >= min(3, len(right_terms))


def _strip_proof_claim_intro(value: str) -> str:
    text = _compact_text(value).strip(" .")
    patterns = (
        r"^(?:the\s+)?first\s+version\s+is\s+proven\s+when\s+",
        r"^(?:the\s+)?product\s+is\s+proven\s+when\s+",
        r"^(?:release\s+[0-9.]+\s+)?(?:is\s+)?proven\s+when\s+",
        r"^(?:the\s+)?proof\s+boundary\s+(?:is|means)\s*:?\s*",
        r"^(?:the\s+)?first\s+thing\s+(?:the\s+)?product\s+must\s+prove\s+(?:is\s+)?(?:that\s+)?",
        r"^(?:the\s+)?first\s+complete\s+path\s+(?:the\s+)?product\s+must\s+prove\s+(?:is\s+)?(?:that\s+)?",
        r"^(?:the\s+)?first\s+release\s+must\s+prove\s+(?:that\s+)?",
    )
    previous = ""
    while text and text != previous:
        previous = text
        for pattern in patterns:
            text = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip(" .")
    return text


def _drop_secondary_ranking_claims(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    return re.split(
        r"\s+(?:A\s+close\s+second|Close\s+second|Second(?:arily)?|Next)\s+(?:is|would\s+be|should\s+be)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .")


def _trim_incomplete_terminal_phrase(value: str) -> str:
    text = _compact_text(value).strip(" .,;:")
    words = text.split()
    while words:
        tail = words[-1].casefold().strip(".,;:'")
        previous = words[-2].casefold().strip(".,;:'") if len(words) >= 2 else ""
        if tail in {"accepted", "complete", "safe", "trusted", "visible"} and previous in {
            "is",
            "are",
            "be",
            "being",
            "been",
            "was",
            "were",
        }:
            break
        if tail not in _INCOMPLETE_TERMINAL_WORDS and tail not in _INCOMPLETE_TERMINAL_MODIFIERS:
            break
        words.pop()
    text = " ".join(words).strip(" .,;:")
    text = re.sub(
        r"\b(?:result|proof|record|state|decision|status|output|handoff|review)\s+(?:is|are|was|were|be|being|been)$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .,;:")
    words = text.split()
    while words:
        tail = words[-1].casefold().strip(".,;:'")
        previous = words[-2].casefold().strip(".,;:'") if len(words) >= 2 else ""
        if tail in {"accepted", "complete", "safe", "trusted", "visible"} and previous in {
            "is",
            "are",
            "be",
            "being",
            "been",
            "was",
            "were",
        }:
            break
        if tail not in _INCOMPLETE_TERMINAL_WORDS and tail not in _INCOMPLETE_TERMINAL_MODIFIERS:
            break
        words.pop()
    text = " ".join(words).strip(" .,;:")
    while True:
        trimmed = _OPEN_CONNECTOR_INTERRUPTER_RE.sub("", text).strip(" .,;:")
        if trimmed == text:
            return text
        text = trimmed


def _deferred_rationale_sentence(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return "Adjacent scope waits for a separate owner, acceptance gate, and proof path"
    if has_terminal_deferral_predicate(text) or text.casefold().startswith("scope question remains open"):
        return f"{text}; separate owner, acceptance gate, and proof path required"
    if re.match(r"^(?:avoid|do\s+not|don't|never)\b", text, flags=re.IGNORECASE):
        return f"{text}; separate owner, acceptance gate, and proof path required"
    deferred_focus = _deferred_focus_sentence(text)
    if deferred_focus:
        text = deferred_focus[:1].upper() + deferred_focus[1:]
    verb = "wait" if _deferred_focus_is_plural(text) else "waits"
    return f"{text} {verb} for a separate owner, acceptance gate, and proof path"


def _scoped_deferred_rationale(*, title: str, rationale: str) -> str:
    text = _compact_text(rationale).strip(" .")
    title_focus = _short_summary(title, limit=90).strip(" .")
    if not text or not title_focus or title_focus.casefold() in text.casefold():
        return text
    return f"{title_focus}: {text}"


def _deferred_focus_is_plural(value: str) -> bool:
    text = _compact_text(value).strip(" .")
    lowered = text.casefold()
    if re.search(r"\b(?:and|or)\b", lowered) or "," in text:
        return True
    return bool(re.search(r"\b(?:integrations|roles|workflows|features|systems|services|exports|imports)\b", lowered))


def _deferred_focus_sentence(value: str) -> str:
    cleaned = _compact_text(value).strip(" .")
    if not cleaned:
        return ""
    lowered = cleaned.casefold()
    if not re.search(
        r"\b(?:out\s+of\s+scope|outside|deferred|future|later|not\s+included|not\s+required|"
        r"not\s+needed|not\s+necessary|must\s+not\s+claim|does\s+not\s+claim)\b",
        lowered,
    ):
        return ""
    scope_question = re.match(
        r"^(?:whether\s+)?(?:is|are|should|will|would|can|could|does|do)?\s*(?P<subject>.+?)\s+"
        r"(?:in\s+scope|included|part\s+of\s+(?:the\s+)?scope)\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    if scope_question:
        subject = _short_summary(scope_question.group("subject"), limit=90).strip(" .")
        if subject:
            return f"{subject[:1].upper()}{subject[1:]} scope remains deferred"
    not_required = re.match(
        r"^(?P<subject>.+?)\s+(?:is|are)\s+[^.]{0,120}?\bnot\s+(?:required|needed|necessary)\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not_required:
        subject = _short_summary(not_required.group("subject"), limit=90).strip(" .")
        if subject:
            return f"{subject[:1].upper()}{subject[1:]} scope remains deferred"
    cleaned = re.sub(
        r"\s+(?:are|is|stay|stays|remain|remains)\s+"
        r"(?:(?:explicitly|intentionally|currently)\s+)?"
        r"(?:out\s+of\s+scope|outside\s+(?:the\s+)?(?:first\s+)?(?:proof|release|scope))\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip(" .")
    cleaned = re.sub(r"^(?:outside\s+(?:the\s+)?(?:first\s+)?(?:proof|release|scope)\s*:?\s*)", "", cleaned, flags=re.IGNORECASE)
    return _short_summary(cleaned, limit=120).strip(" .")


def _bounded_complete_proof_focus(value: str, *, max_words: int) -> str:
    text = _compact_text(value).strip(" .")
    comma_segments = [segment.strip(" .") for segment in re.split(r"\s*,\s*", text) if segment.strip(" .")]
    if len(comma_segments) > 1:
        selected: list[str] = []
        for segment in comma_segments:
            selected.append(segment)
            candidate = _trim_incomplete_terminal_phrase(", ".join(selected))
            joined = ", ".join(selected).strip(" .,;:")
            if candidate and candidate == joined and word_count(candidate) >= 7:
                return candidate
    words = text.split()
    if len(words) <= max_words:
        return _trim_incomplete_terminal_phrase(text)
    return _trim_incomplete_terminal_phrase(" ".join(words[:max_words]))


def _release_gate_wrapper_focus(value: str) -> bool:
    text = _compact_text(value).casefold()
    return "succeeds when this first path is complete:" in text or "is proven when this first path is complete:" in text


def _too_similar(left: str, right: str) -> bool:
    left_terms = semantic_words(left)
    right_terms = semantic_words(right)
    if len(left_terms) < 4 or len(right_terms) < 4:
        return False
    overlap = len(left_terms & right_terms) / max(1, min(len(left_terms), len(right_terms)))
    return overlap >= 0.65


def _strip_leading_connector(value: str) -> str:
    text = _clean_text(value).strip(" .")
    lowered = text.casefold()
    for connector in ("and", "or", "then", "but"):
        prefix = f"{connector} "
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip(" .")
    return text


def _capability_clause_key(value: str) -> str:
    tokens: list[str] = []
    for raw in re.sub(r"[-/]", " ", str(value or "")).split():
        token = raw.strip(".,:;()[]{}").casefold()
        if len(token) < 4:
            continue
        if token in {"prove", "proves", "proved", "proven", "proof"}:
            token = "proof"
        tokens.append(token)
    return " ".join(tokens)


__all__ = [
    "compact_workstream_title_connector",
    "dedupe_capability_phrase",
    "drop_adjacent_duplicate_words",
    "evidence_scope_phrase",
    "has_problem_tension",
    "looks_mechanical_summary",
    "metric_capability_summary",
    "proof_claim_summary",
    "proof_focus_phrase",
    "proof_focus_summary",
    "rationale_deferred_focus",
    "rationale_lines",
    "rationale_proof_focus",
    "rationale_release_basis",
    "rationale_scope_focus",
    "result_content_words",
    "result_terms_covered",
    "semantic_words",
    "sentence_fragment",
    "shares_product_terms",
]
