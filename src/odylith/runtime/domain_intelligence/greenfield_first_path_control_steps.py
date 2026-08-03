"""Control-step predicates for confirmed greenfield first paths."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import (
    WORD_SENSE_CONTROL_CUSTODY_TERMS as _WORD_SENSE_CONTROL_CUSTODY_TERMS,
)
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import (
    WORD_SENSE_DESCRIPTOR_TERMS as _WORD_SENSE_DESCRIPTOR_TERMS,
)
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import (
    word_sense_tail_has_control_obligation as _word_sense_tail_has_control_obligation,
)
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import (
    word_sense_tail_starts_content_clause as _word_sense_tail_starts_content_clause,
)

_ARCHITECTURE_CONTROL_TERMS = frozenset(
    {
        "architecture",
        "architect",
        "architectural",
        "bounded",
        "boundaries",
        "boundary",
        "component",
        "components",
        "event",
        "events",
        "ownership",
        "projection",
        "projections",
        "topology",
    }
)
_GOVERNANCE_DELIVERY_TERMS = frozenset(
    {
        "artifact",
        "artifacts",
        "budget",
        "confirm",
        "create",
        "finish",
        "governance",
        "post",
        "project",
        "standard",
    }
)
_REQUEST_CONTROL_TERMS = frozenset({"instruction", "instructions", "prompt", "request"})
_OUTPUT_CONTROL_TERMS = frozenset({"artifact", "artifacts", "content", "copy", "output", "outputs", "surface", "surfaces"})
_QUALITY_CONTROL_TERMS = frozenset(
    {
        "accurate",
        "clarity",
        "clear",
        "coherent",
        "cohesive",
        "depth",
        "domain",
        "grammar",
        "grammatical",
        "jargon",
        "legible",
        "premium",
        "quality",
        "readable",
        "semantic",
        "specialist",
    }
)
_STATE_CONTROL_TERMS = frozenset({"approval", "release", "review", "separate", "state", "states"})
_FIRST_RELEASE_BOUNDARY_RE = re.compile(
    r"\b(?:the\s+)?first\s+release(?:\s+boundary)?\s*(?:(?:is|includes?|covers?)\s+|:\s*)(?P<items>[^.!?]+)",
    flags=re.IGNORECASE,
)
_FIRST_RELEASE_EXCLUSION_TAIL_RE = re.compile(
    r"\s*(?:;\s*|,?\s+(?:while|but|with)\s+|,?\s+and\s+(?!(?:a|an|the|one)\b))[^.!?]*"
    r"\b(?:exclude(?:s|d|ing)?|(?:does|do|did)\s+not\s+include|not\s+(?:include(?:d)?|part)|"
    r"out(?:\s+of)?\s+scope|outside)\b[^.!?]*$",
    flags=re.IGNORECASE,
)
_OPERATOR_LENS_ROLE_PHRASES = {
    "architect": "architect",
    "domain expert": "domain-expert",
    "domain reviewer": "domain-reviewer",
    "engineer": "engineer",
    "product manager": "product-manager",
    "project manager": "project-manager",
    "scientific reviewer": "scientific-reviewer",
    "subject matter expert": "subject-matter-expert",
    "technical reviewer": "technical-reviewer",
}
_OPERATOR_LENS_ACTION_TERMS = frozenset(
    {"approve", "approves", "expect", "expects", "inspect", "inspects", "review", "reviews", "see", "sees", "verify", "verifies"}
)
_OPERATOR_LENS_CONTROL_TERMS = frozenset(
    {
        "acceptance",
        "actor",
        "actors",
        "claim",
        "claims",
        "complete",
        "criteria",
        "depth",
        "domain",
        "evidence",
        "expert",
        "first",
        "goal",
        "goals",
        "implementable",
        "metric",
        "metrics",
        "non-goal",
        "non-goals",
        "path",
        "scientific",
        "success",
        "testable",
        "uncertainty",
        "unsupported",
        "value",
        "validation",
    }
)
_REQUIREMENT_SUBJECT_TERMS = frozenset(
    {
        "artifact",
        "artifacts",
        "it",
        "output",
        "outputs",
        "path",
        "product",
        "release",
        "result",
        "scope",
        "system",
        "tool",
        "version",
        "workflow",
        "workspace",
    }
)
_RELEASE_BOUNDARY_SUBJECT_TERMS = frozenset({"release", "scope", "version"})
_REQUIREMENT_ACTION_TERMS = frozenset(
    {
        "avoid",
        "capture",
        "complete",
        "finish",
        "include",
        "keep",
        "make",
        "name",
        "pass",
        "preserve",
        "record",
        "show",
        "support",
    }
)
_EVIDENCE_OBLIGATION_TERMS = frozenset(
    {
        "audit",
        "baseline",
        "claim",
        "claims",
        "comparison",
        "confidence",
        "constraint",
        "constraints",
        "evidence",
        "limit",
        "measurement",
        "method",
        "model",
        "proof",
        "quality",
        "record",
        "reproducibility",
        "reproducible",
        "result",
        "review",
        "source",
        "trail",
        "tolerance",
        "uncertainty",
        "unit",
        "unsupported",
        "validation",
    }
)
_VOCABULARY_METADATA_TERMS = frozenset({"terminology", "terms", "vocabulary"})
_VOCABULARY_METADATA_ACTIONS = frozenset({"include", "includes", "list", "lists", "name", "names"})


def drop_requirement_control_steps(values: Sequence[str]) -> list[str]:
    rows = [_clean(value).strip(" .") for value in values if _clean(value).strip(" .")]
    if len(rows) <= 1:
        return rows
    lens_bundle = _has_operator_lens_bundle(rows)
    cleaned = [
        row
        for row in rows
        if not is_requirement_control_step(row) and not (lens_bundle and is_operator_review_lens_step(row))
    ]
    return cleaned or rows


def strip_trailing_requirement_control_steps(value: str) -> str:
    """Drop trailing operator-review criteria after a recoverable product path."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    rows = _sentence_fragments(text)
    if len(rows) <= 1:
        return text
    kept: list[str] = []
    dropped_tail = False
    for row in rows:
        if kept and (is_requirement_control_step(row) or is_operator_review_lens_step(row)):
            dropped_tail = True
            break
        kept.append(row)
    if not dropped_tail:
        return text
    return ". ".join(kept).strip(" .") or text


def contains_requirement_control_clause(value: str) -> bool:
    """Return whether text contains a release/proof constraint rather than path behavior."""

    return _requirement_control_start(value) >= 0


def contains_word_sense_metadata_clause(value: str) -> bool:
    """Return whether text describes prompt word senses instead of product behavior."""

    return _word_sense_metadata_start(value) >= 0


def word_sense_metadata_start(value: str) -> int:
    """Return the start offset for prompt word-sense metadata, or -1."""

    return _word_sense_metadata_start(value)


def is_declarative_visible_result_prefix(value: str) -> bool:
    """Return whether text only introduces a visible result without naming it."""

    text = _clean(value).strip(" .")
    return bool(
        re.fullmatch(
            r"(?:the\s+)?visible\s+result\s+(?:is|will\s+be|should\s+be|must\s+be)?",
            text,
            flags=re.IGNORECASE,
        )
        or re.search(r"\b(?:is|are|was|were|be|being)$", text, flags=re.IGNORECASE)
    )


def strip_requirement_control_tail(value: str) -> str:
    """Remove a trailing requirement/proof clause accidentally fused into a path event."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    text = _strip_pre_release_state_tail(text)
    start = _requirement_control_start(text)
    if start <= 0:
        return text if start != 0 else ""
    return text[:start].strip(" ,.;:")


def _strip_pre_release_state_tail(value: str) -> str:
    """Drop a lifecycle control noun that follows an otherwise complete action list."""

    match = re.search(
        r"(?:,\s*and\s+|\s+and\s+)"
        r"(?:(?:recovery|approval|review|release)\s+)?(?:state|status|approval|review)\s+before\s+"
        r"(?:a|an|the)\s+[^.]{1,80}?\s+is\s+(?:released|approved|deployed|published)$",
        value,
        flags=re.IGNORECASE,
    )
    return value[: match.start()].strip(" ,.;:") if match else value


def is_requirement_control_step(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    modal = r"(?:must|should|needs?\s+to|has\s+to|have\s+to)\b"
    words = _words(text)
    return bool(
        re.match(
            r"^(?:(?:the|this|that)\s+)?(?:first|initial)\s+(?:release|version)\s+"
            rf"{modal}",
            text,
            flags=re.IGNORECASE,
        )
        or re.match(
            r"^(?:(?:the|this|that)\s+)?"
            r"(?:accepted\s+path|application|app|artifact|artifacts|generated\s+artifacts|"
            r"flow|journey|output|path|product|result|system|tool|workflow|workspace|it)"
            rf"\s+{modal}",
            text,
            flags=re.IGNORECASE,
        )
        or re.match(rf"^(?:(?:the|this|that)\s+)?first\s+path\s+{modal}", text, flags=re.IGNORECASE)
        or (
            _has_modal(text)
            and (
                len(words & _ARCHITECTURE_CONTROL_TERMS) >= 2
                or len(words & _GOVERNANCE_DELIVERY_TERMS) >= 3
                or (bool(words & _REQUEST_CONTROL_TERMS) and len(words & _STATE_CONTROL_TERMS) >= 3)
                or (
                    bool(words & _REQUEST_CONTROL_TERMS)
                    and bool(words & _OUTPUT_CONTROL_TERMS)
                    and bool(words & _QUALITY_CONTROL_TERMS)
                )
            )
        )
        or _requirement_control_start(text) == 0
    )


def is_release_evidence_requirement(value: str) -> bool:
    """Return whether a release clause names evidence to preserve, not path behavior."""

    text = _clean(value).strip(" .")
    return bool(
        re.match(
            r"^(?:(?:the|this)\s+)?(?:first|initial)\s+(?:release|version)\s+"
            r"(?:must|should|needs?\s+to|has\s+to)\s+"
            r"(?:capture|include|keep|name|preserve|record|show)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def is_operator_review_lens_step(value: str) -> bool:
    """Return whether a clause is an expert-review criterion, not product behavior."""

    text = _clean(value).strip(" .")
    if not text or not _has_modal(text):
        return False
    if not _operator_lens_role(text):
        return False
    words = _words(text)
    if not words & _OPERATOR_LENS_ACTION_TERMS:
        return False
    control_terms = (
        _ARCHITECTURE_CONTROL_TERMS
        | _GOVERNANCE_DELIVERY_TERMS
        | _OUTPUT_CONTROL_TERMS
        | _QUALITY_CONTROL_TERMS
        | _REQUEST_CONTROL_TERMS
        | _STATE_CONTROL_TERMS
        | _OPERATOR_LENS_CONTROL_TERMS
    )
    return bool(words & control_terms)


def operator_review_lens_obligations(value: str) -> list[str]:
    """Return explicit reviewer obligations without turning reviewers into product actors."""

    rows: list[str] = []
    seen: set[str] = set()
    for sentence in _sentence_fragments(value):
        row = _operator_review_lens_obligation(sentence)
        key = row.casefold() if row else ""
        if row and key not in seen:
            seen.add(key)
            rows.append(row)
    return rows


def first_release_boundary_requirements(value: str) -> tuple[str, ...]:
    """Return affirmative requirements explicitly named for the first release."""

    requirements: list[str] = []
    seen: set[str] = set()
    for match in _FIRST_RELEASE_BOUNDARY_RE.finditer(_clean(value)):
        items = re.sub(
            r"\s*;\s*[^.!?]*\b(?:exclude(?:s|d|ing)?|(?:does|do|did)\s+not\s+include|"
            r"not\s+(?:include(?:d)?|part)|out(?:\s+of)?\s+scope|outside)\b[^.!?]*$",
            "",
            match.group("items"),
            flags=re.IGNORECASE,
        )
        items = _FIRST_RELEASE_EXCLUSION_TAIL_RE.sub("", items).strip(" ,;.")
        for item in re.split(r",\s*|\s+and\s+(?=(?:a|an|the|one)\b)", items, flags=re.IGNORECASE):
            requirement = re.sub(r"^(?:and\s+)", "", item, flags=re.IGNORECASE).strip(" ,;.")
            key = requirement.casefold()
            if requirement and key not in seen:
                seen.add(key)
                requirements.append(requirement)
    return tuple(requirements)


def first_release_boundary_summary(value: str) -> str:
    """Render affirmative first-release scope from the same parsed requirements."""

    requirements = first_release_boundary_requirements(value)
    return f"The first release includes {_join_requirement_phrases(requirements)}." if requirements else ""


def proof_boundary_with_first_release_requirements(proof_boundary: str, source: str) -> str:
    """Keep explicit release scope in the hash-bound proof contract."""

    proof = str(proof_boundary or "").strip()
    requirements = first_release_boundary_requirements(source)
    if not requirements:
        return proof
    normalized_proof = proof.rstrip(" .")
    missing = tuple(requirement for requirement in requirements if requirement.casefold() not in normalized_proof.casefold())
    if not missing:
        return normalized_proof
    summary = _join_requirement_phrases(missing)
    suffix = f"The first release includes {summary}."
    return f"{normalized_proof}. {suffix}" if normalized_proof else suffix


def _join_requirement_phrases(values: Sequence[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def is_scope_or_deferred_statement(value: str) -> bool:
    """Return whether a clause describes release limits, not first-path behavior."""

    text = _clean(value).strip(" .")
    if not text:
        return False
    lowered = text.casefold()
    if re.search(r"\b(?:act|follow(?:-|\s+)up|research|respond|retry|return)\s+later\b", lowered) and MATERIAL_ACTION_RE.search(text):
        return bool(re.search(r"\b(?:defer|deferred|future|not\s+included|not\s+claim|outside|release|scope)\b", lowered))
    if re.search(
        r"\b(?:out\s+of\s+scope|outside\s+(?:the\s+)?(?:first\s+)?release|outside\s+scope|"
        r"stay\s+outside|stays\s+outside|deferred|future|not\s+included|not\s+claim|"
        r"must\s+not\s+claim|does\s+not\s+claim)\b",
        lowered,
    ):
        return True
    return bool(
        re.search(r"\b(?:multi|external|automated|long-term|broader|production-scale|fleet-wide)\b", lowered)
        and re.search(r"\b(?:scope|release|stay|stays|outside|deferred|later|future|not)\b", lowered)
    )


def _clean(value: object) -> str:
    return clean_first_path_text(value)


def _has_modal(value: str) -> bool:
    return bool(re.search(r"\b(?:must|should|needs?\s+to|has\s+to|have\s+to)\b", _clean(value), flags=re.IGNORECASE))


def _has_operator_lens_bundle(values: Sequence[str]) -> bool:
    roles = {_operator_lens_role(value) for value in values}
    roles.discard("")
    return len(roles) >= 2


def _operator_lens_role(value: str) -> str:
    text = re.sub(r"^(?:a|an|the)\s+", "", _clean(value).casefold().strip(" ."))
    for phrase, role in _OPERATOR_LENS_ROLE_PHRASES.items():
        if text.startswith(f"{phrase} "):
            return role
    return ""


def _operator_review_lens_obligation(value: str) -> str:
    if not is_operator_review_lens_step(value):
        return ""
    role_label = _operator_lens_role_label(value)
    obligation = _operator_lens_obligation(value)
    if not role_label or not obligation:
        return ""
    return f"{role_label} review must verify {obligation}"


def _operator_lens_role_label(value: str) -> str:
    text = re.sub(r"^(?:a|an|the)\s+", "", _clean(value).strip(" ."), flags=re.IGNORECASE)
    for phrase in _OPERATOR_LENS_ROLE_PHRASES:
        if text.casefold().startswith(f"{phrase} "):
            return " ".join(word[:1].upper() + word[1:] for word in phrase.split())
    return ""


def _operator_lens_obligation(value: str) -> str:
    text = re.sub(r"^(?:a|an|the)\s+", "", _clean(value).strip(" ."), flags=re.IGNORECASE)
    match = re.match(
        r"^[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?\s+"
        r"(?:must|should|needs?\s+to|has\s+to|have\s+to)\s+"
        r"(?:approve|expect|inspect|review|see|verify)s?\s+(?P<tail>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    tail = _clean(match.group("tail")).strip(" .") if match else ""
    return _normalize_lens_obligation(tail)


def _normalize_lens_obligation(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"\bwith\s+no\b", "without", text, flags=re.IGNORECASE)
    return text[:1].casefold() + text[1:]


def _sentence_fragments(value: str) -> list[str]:
    text = _clean(value).strip(" .")
    return [row.strip(" .") for row in re.split(r"(?<=[.!?])\s+", text) if row.strip(" .")]


def _words(value: str) -> set[str]:
    return {
        word.casefold()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", _clean(value).replace("-", " "))
        if word
    }


def _requirement_control_start(value: str) -> int:
    tokens = _word_spans(value)
    word_sense_start = _word_sense_metadata_start_from_tokens(tokens)
    if word_sense_start >= 0:
        return word_sense_start
    for index, token in enumerate(tokens):
        if (
            _tokens_start_vocabulary_metadata(tokens, index)
            or _tokens_start_subject_modal_requirement(tokens, index)
            or _tokens_start_control_resolution_requirement(tokens, index)
        ):
            return token[1]
    return -1


def _word_sense_metadata_start(value: str) -> int:
    return _word_sense_metadata_start_from_tokens(_word_spans(value))


def _word_sense_metadata_start_from_tokens(tokens: Sequence[tuple[str, int]]) -> int:
    for index, token in enumerate(tokens):
        if _tokens_start_word_sense_metadata(tokens, index):
            return token[1]
    return -1


def _tokens_start_vocabulary_metadata(tokens: Sequence[tuple[str, int]], index: int) -> bool:
    window = [token for token, _start in tokens[index : index + 8]]
    if not window:
        return False
    return bool(set(window[:5]) & _VOCABULARY_METADATA_TERMS and set(window) & _VOCABULARY_METADATA_ACTIONS)


def _tokens_start_word_sense_metadata(tokens: Sequence[tuple[str, int]], index: int) -> bool:
    window = [token for token, _start in tokens[index : index + 28]]
    if len(window) < 5:
        return False
    subject_index = index
    if tokens[subject_index][0] in {"a", "an", "the", "this", "that"}:
        subject_index += 1
    if subject_index + 2 >= len(tokens):
        return False
    subject = tokens[subject_index][0]
    verb = tokens[subject_index + 1][0]
    tail = [token for token, _start in tokens[subject_index + 2 : subject_index + 28]]
    if subject in {"instruction", "instructions", "prompt", "request"} and verb in {
        "calls",
        "describes",
        "frames",
        "mentions",
        "treats",
        "uses",
    }:
        return _word_sense_tail_describes_metadata(tail)
    if subject in {"instruction", "instructions", "prompt", "request"} and verb in {
        "adds",
        "clarifies",
        "explains",
        "indicates",
        "notes",
        "says",
        "specifies",
        "states",
        "warns",
    }:
        if _word_sense_tail_starts_content_clause(tail):
            return _word_sense_tail_has_control_obligation(tail)
        return _word_sense_tail_describes_metadata(tail) or _word_sense_tail_contains_copular_metadata(tail)
    if verb in {"is", "are"}:
        return _word_sense_tail_describes_metadata(tail) and _word_sense_tail_has_control_custody(tail)
    return False


def _word_sense_tail_describes_metadata(tokens: Sequence[str]) -> bool:
    token_set = set(tokens)
    if not ("both" in token_set or sum(1 for token in tokens if token == "as") >= 2 or ("as" in token_set and "and" in token_set)):
        return False
    descriptor_tokens = _word_sense_descriptor_tail(tokens)
    return len({token for token in descriptor_tokens if token in _WORD_SENSE_DESCRIPTOR_TERMS}) >= 2


def _word_sense_tail_has_control_custody(tokens: Sequence[str]) -> bool:
    return bool(set(tokens) & _WORD_SENSE_CONTROL_CUSTODY_TERMS)


def _word_sense_tail_contains_copular_metadata(tokens: Sequence[str]) -> bool:
    for index, token in enumerate(tokens):
        if token not in {"is", "are"}:
            continue
        tail = tokens[index + 1 :]
        if _word_sense_tail_describes_metadata(tail) and _word_sense_tail_has_control_custody(tail):
            return True
    return False


def _word_sense_descriptor_tail(tokens: Sequence[str]) -> Sequence[str]:
    if "as" in tokens:
        return tokens[tokens.index("as") + 1 :]
    if "both" in tokens:
        return tokens[tokens.index("both") + 1 :]
    return tokens


def _tokens_start_subject_modal_requirement(tokens: Sequence[tuple[str, int]], index: int) -> bool:
    subject_index = index
    if tokens[subject_index][0] in {"a", "an", "the", "this", "that"}:
        subject_index += 1
    if subject_index >= len(tokens):
        return False
    if tokens[subject_index][0] in {"accepted", "current", "first"}:
        subject_index += 1
    if subject_index >= len(tokens):
        return False
    subject = tokens[subject_index][0]
    if subject not in _REQUIREMENT_SUBJECT_TERMS:
        return False
    modal_index = _modal_index(tokens, subject_index + 1)
    if modal_index < 0:
        return False
    tail = {token for token, _start in tokens[modal_index + 1 : modal_index + 14]}
    if subject in _RELEASE_BOUNDARY_SUBJECT_TERMS:
        if tail & _REQUIREMENT_ACTION_TERMS and tail & _EVIDENCE_OBLIGATION_TERMS:
            return False
        return True
    return bool(tail & _REQUIREMENT_ACTION_TERMS and tail & _EVIDENCE_OBLIGATION_TERMS)


def _tokens_start_control_resolution_requirement(tokens: Sequence[tuple[str, int]], index: int) -> bool:
    subject_index = index
    if tokens[subject_index][0] in {"a", "an", "the", "this", "that"}:
        subject_index += 1
    if subject_index >= len(tokens):
        return False
    subject = tokens[subject_index][0]
    if subject not in {"ambiguity", "custody", "governance", "ownership"}:
        return False
    modal_index = _modal_index(tokens, subject_index + 1)
    if modal_index < 0:
        return False
    tail = {token for token, _start in tokens[modal_index + 1 : modal_index + 10]}
    return bool(tail & {"explicit", "owned", "resolved"})


def _modal_index(tokens: Sequence[tuple[str, int]], index: int) -> int:
    if index >= len(tokens):
        return -1
    token = tokens[index][0]
    if token in {"must", "should"}:
        return index
    if token in {"need", "needs"}:
        return index if index + 1 < len(tokens) and tokens[index + 1][0] == "to" else -1
    if token in {"has", "have"}:
        return index if index + 1 < len(tokens) and tokens[index + 1][0] == "to" else -1
    return -1


def _word_spans(value: str) -> list[tuple[str, int]]:
    return [(match.group(0).casefold(), match.start()) for match in re.finditer(r"[A-Za-z][A-Za-z0-9'-]*", _clean(value))]


__all__ = [
    "drop_requirement_control_steps",
    "contains_requirement_control_clause",
    "contains_word_sense_metadata_clause",
    "first_release_boundary_requirements",
    "first_release_boundary_summary",
    "is_declarative_visible_result_prefix",
    "is_operator_review_lens_step",
    "is_release_evidence_requirement",
    "is_requirement_control_step",
    "operator_review_lens_obligations",
    "proof_boundary_with_first_release_requirements",
    "is_scope_or_deferred_statement",
    "strip_requirement_control_tail",
    "strip_trailing_requirement_control_steps",
    "word_sense_metadata_start",
]
