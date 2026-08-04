"""Normalize structured prompt evidence and rank narrative first-path candidates."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_patterns import leading_actor_action_match
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


@dataclass(frozen=True)
class StructuredPromptFacts:
    """Explicit product, actor, and path fields recovered without prose inference."""

    title: str = ""
    actor: str = ""
    first_path: str = ""


_TITLE_FIELDS = ("product", "product name", "title")
_ACTOR_FIELDS = ("actor", "operator", "user", "first user")
_PATH_FIELDS = ("first complete path", "first path", "path", "workflow")
_ROLE_FIELDS = ("role", "operator role", "user role")
_HARD_NON_PATH_RE = re.compile(
    r"\b(?:out\s+of\s+scope|unrelated|proof(?:\s+boundary)?|prove|success\s+means|"
    r"demonstrate|must\s+not|may\s+not|cannot|can't|do\s+not|never|boundary|"
    r"(?:the\s+)?(?:request|prompt|source)\s+(?:says|states|mentions|describes)|"
    r"comes?\s+from|suppl(?:y|ies|ied)\s+by?|provid(?:e|es|ed)\s+by?|"
    r"read\s+from|imports?\b|visible\s+only|staff\s+paste)\b",
    flags=re.IGNORECASE,
)
_VISIBLE_RESULT_RE = re.compile(
    r"\b(?:see|sees|show|shows|display|displays|receive|receives|view|views|"
    r"return|returns|get|gets|publish|publishes)\b",
    flags=re.IGNORECASE,
)
_SEQUENCE_RE = re.compile(r"(?:->|\b(?:first|then|after|before|next|finally)\b|;)", flags=re.IGNORECASE)
_LABELED_PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _/-]{1,60}:\s*")
_TITLE_TOKEN = r"[A-Z][A-Za-z0-9'/-]*"
_TITLE_PHRASE = rf"{_TITLE_TOKEN}(?:\s+{_TITLE_TOKEN}){{0,4}}"
_PRODUCT_IDENTITY_DECLARATION_RE = re.compile(rf"^(?:{_TITLE_PHRASE})\s+is\s+for\b")
_CREATE_REQUEST_WRAPPER_RE = re.compile(
    r"^(?:build|create|design|draft|generate|make|prepare|propose)\b",
    flags=re.IGNORECASE,
)
_FINITE_ACTION_PATTERN = action_verb_pattern(include_base=False, include_finite=True)
_BASE_ACTION_PATTERN = action_verb_pattern(include_base=True, include_finite=False)
_PRODUCT_GRANT_RE = re.compile(
    r"^(?:the\s+)?(?:app|application|platform|product|service|system|tool|workspace)\s+"
    r"(?:(?:can|could|must|should|will|would)\s+)?(?:allows?|enables?|lets?)\s+"
    r"(?:a|an|the)\s+(?P<tail>.+)$",
    flags=re.IGNORECASE,
)
_APPOSITIVE_ACTOR_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z0-9'/-]*),\s+(?:a|an|the)\s+"
    r"(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,70}?),\s+"
    r"(?P<action>[a-z][^.!?]{2,})",
)
_NAMED_ROLE_RE = re.compile(
    r"\b(?:[Aa]|[Aa]n|[Tt]he)\s+(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?)\s+"
    r"(?:named\s+)?(?P<name>[A-Z][A-Za-z0-9'/-]*)\s+"
    rf"(?:{_FINITE_ACTION_PATTERN})\b",
)
_ROLE_NAMED_PERSON_RE = re.compile(
    r"\b(?:[Aa]|[Aa]n|[Tt]he)\s+(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?)\s+named\s+"
    r"(?P<name>[A-Z][A-Za-z0-9'/-]*)\b",
)
_ROLE_COMMA_PERSON_RE = re.compile(
    r"\b(?:[Aa]|[Aa]n|[Tt]he)\s+(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?),\s+"
    r"(?P<name>[A-Z][A-Za-z0-9'/-]*),\s+"
    rf"(?:{_FINITE_ACTION_PATTERN})\b",
)
_PERSON_ROLE_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z0-9'/-]*)\s+(?:works\s+as|is)\s+(?:[Aa]|[Aa]n|[Tt]he)\s+"
    r"(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?)(?:\s+(?:in|using)\b|[.!?:])",
)
_FOR_ROLE_PERSON_RE = re.compile(
    r"\bfor\s+(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?)\s+"
    r"(?P<name>[A-Z][A-Za-z0-9'/-]*)\b",
)
_INVALID_ROLE_TRAILING_RE = re.compile(r"\b(?:at|for|from|in|on|to|with|within)$", flags=re.IGNORECASE)


def structured_prompt_facts(value: str) -> StructuredPromptFacts:
    """Recover explicit facts from JSON, Markdown tables, or labeled rows."""

    text = str(value or "").strip()
    if not text:
        return StructuredPromptFacts()
    mapping = _json_mapping(text) or _markdown_field_mapping(text)
    if not mapping:
        return StructuredPromptFacts()
    title = _first_field(mapping, _TITLE_FIELDS)
    actor = _first_field(mapping, _ACTOR_FIELDS)
    role = _first_field(mapping, _ROLE_FIELDS)
    if role and actor and role.casefold() not in actor.casefold():
        actor = f"{role} {actor}"
    path_value = _first_raw_field(mapping, _PATH_FIELDS)
    first_path = _structured_path(actor=actor, value=path_value)
    return StructuredPromptFacts(title=title, actor=actor, first_path=first_path)


def ranked_first_path_evidence(value: str) -> str:
    """Return the strongest actor-action-outcome evidence, not the first plausible sentence."""

    structured = structured_prompt_facts(value)
    if structured.first_path:
        return structured.first_path
    rows = _narrative_rows(value)
    if not rows:
        return ""
    candidates: list[tuple[int, int, str]] = []
    for index, row in enumerate(rows):
        if not _hard_non_path(row):
            candidates.append((_path_score(row), -index, row))
        for workflow in _embedded_workflow_clauses(row):
            candidates.append((_path_score(workflow) + 4, -index, workflow))
        for granted_path in _embedded_product_grant_clauses(row):
            candidates.append((_path_score(granted_path) + 4, -index, granted_path))
        for evidence_clause in _embedded_evidence_clauses(row):
            candidates.append((_path_score(evidence_clause) + 2, -index, evidence_clause))
        if index + 1 < len(rows) and not _hard_non_path(row) and not _hard_non_path(rows[index + 1]):
            combined = f"{row}. {rows[index + 1]}"
            candidates.append((_path_score(combined), -index, combined))
    score, _position, candidate = max(candidates, default=(0, 0, ""))
    return candidate if score >= 12 else ""


def explicit_product_title_evidence(value: str) -> str:
    """Return an explicitly named product from structured or narrative evidence."""

    structured = structured_prompt_facts(value)
    if structured.title:
        return structured.title
    candidates: list[tuple[int, str]] = []
    text = clean_markdown_text(str(value or ""))
    patterns = (
        (
            re.compile(
                rf"\b(?P<connector>uses?|using|in)\s+(?P<article>the\s+)?(?P<title>{_TITLE_PHRASE})\b"
            ),
            8,
        ),
        (
            re.compile(
                rf"(?:^|[.!?]\s+|:\s+)(?P<title>{_TITLE_PHRASE})\s+"
                r"(?:must|may|cannot|can't|is\s+for|reads?|imports?)\b"
            ),
            6,
        ),
    )
    for pattern, structural_score in patterns:
        for match in pattern.finditer(text):
            title = match.group("title").strip(" .")
            words = title.split()
            if not words or len(words) > 5:
                continue
            if (
                match.groupdict().get("connector", "").casefold() == "in"
                and len(words) == 1
                and not match.groupdict().get("article")
            ):
                continue
            score = structural_score + min(len(words), 4) + text.casefold().count(title.casefold())
            candidates.append((score, title))
    return max(candidates, default=(0, ""))[1]


def explicit_actor_evidence(value: str) -> str:
    """Return one normalized human actor label from the strongest path evidence."""

    structured = structured_prompt_facts(value)
    if structured.actor:
        return _structured_actor_subject(structured.actor).removeprefix("The ")
    ranked = ranked_first_path_evidence(value)
    patterns = (
        _APPOSITIVE_ACTOR_RE,
        _ROLE_NAMED_PERSON_RE,
        _ROLE_COMMA_PERSON_RE,
        _PERSON_ROLE_RE,
        _FOR_ROLE_PERSON_RE,
        _NAMED_ROLE_RE,
    )
    for source in tuple(dict.fromkeys(item for item in (ranked, str(value or "")) if item)):
        for pattern in patterns:
            match = pattern.search(source)
            if match:
                role = re.sub(
                    r"^(?:a|an|the)\s+",
                    "",
                    match.group("role"),
                    flags=re.IGNORECASE,
                ).strip(" ,")
                if _INVALID_ROLE_TRAILING_RE.search(role):
                    continue
                return f"{role} {match.group('name')}".strip()
    return ""


def _json_mapping(value: str) -> Mapping[str, Any]:
    if not value.startswith("{"):
        return {}
    try:
        payload = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _markdown_field_mapping(value: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for raw_row in value.splitlines():
        row = raw_row.strip()
        if not row:
            continue
        if row.startswith("|") and row.endswith("|"):
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            if len(cells) >= 2 and not all(set(cell) <= {"-", ":", " "} for cell in cells):
                key = _field_key(cells[0])
                if key not in {"field", "key"}:
                    fields[key] = cells[1]
            continue
        match = re.match(
            r"^\s*(?:[-*]\s*)?(?:\*\*)?(?P<key>[A-Za-z][A-Za-z ]{1,40})(?:\*\*)?\s*:\s*(?P<value>.+)$",
            raw_row,
        )
        if match:
            fields[_field_key(match.group("key"))] = match.group("value").strip()
    return fields


def _field_key(value: object) -> str:
    return " ".join(str(value or "").casefold().replace("_", " ").split())


def _first_field(mapping: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    value = _first_raw_field(mapping, fields)
    if isinstance(value, (list, tuple)):
        return "; ".join(_clean(item) for item in value if _clean(item))
    return _clean(value)


def _first_raw_field(mapping: Mapping[str, Any], fields: tuple[str, ...]) -> Any:
    normalized = {_field_key(key): value for key, value in mapping.items()}
    for field in fields:
        if field in normalized:
            return normalized[field]
    return ""


def _structured_path(*, actor: str, value: Any) -> str:
    if isinstance(value, (list, tuple)):
        actions = [_clean(item).strip(" .") for item in value if _clean(item).strip(" .")]
    else:
        path = _clean(value).replace("->", ";")
        actions = [part.strip(" .") for part in re.split(r"\s*;\s*", path) if part.strip(" .")]
    if not actions:
        return ""
    action_chain = _join_actions(actions)
    subject = _structured_actor_subject(actor)
    if subject and not action_chain.casefold().startswith(subject.casefold() + " "):
        action_chain = action_chain[:1].lower() + action_chain[1:]
        return f"{subject} can {action_chain}".strip(" .")
    return action_chain.strip(" .")


def _structured_actor_subject(value: str) -> str:
    actor = _clean(value).strip(" .")
    if not actor:
        return ""
    if "," not in actor:
        words = actor.split()
        if len(words) >= 2 and words[-1][:1].isupper():
            return f"{words[-1]}, a {' '.join(words[:-1])},"
        return actor[:1].upper() + actor[1:]
    name, role = (part.strip() for part in actor.split(",", 1))
    role = re.sub(r"^(?:a|an|the)\s+", "", role, flags=re.IGNORECASE).strip()
    return f"{name}, a {role}," if name and role else actor.replace(",", "")


def _join_actions(actions: list[str]) -> str:
    if len(actions) == 1:
        return actions[0]
    if len(actions) == 2:
        return f"{actions[0]} and {actions[1]}"
    return f"{', '.join(actions[:-1])}, and {actions[-1]}"


def _narrative_rows(value: str) -> list[str]:
    rows: list[str] = []
    for raw_line in str(value or "").splitlines() or [str(value or "")]:
        line = raw_line.strip()
        if not line or re.match(r"^#{1,6}\s+", line):
            continue
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"^\s*[-*]\s+", "", line)
        text = clean_markdown_text(line).strip()
        for fragment in re.split(r"(?<=[.!?])\s+", text):
            row = _LABELED_PREFIX_RE.sub("", fragment).strip(" .")
            if row:
                rows.append(row)
    return rows


def _embedded_workflow_clauses(value: str) -> tuple[str, ...]:
    clauses: list[str] = []
    for match in re.finditer(r"\bwhere\s+(?P<clause>.+)$", value, flags=re.IGNORECASE):
        clause = re.sub(r"^(?:a|an|the)\s+", "", match.group("clause"), flags=re.IGNORECASE).strip(" .")
        if clause and has_human_actor_signal(clause) and not _hard_non_path(clause):
            clauses.append(clause)
    return tuple(clauses)


def _embedded_evidence_clauses(value: str) -> tuple[str, ...]:
    if contains_word_sense_metadata_clause(value):
        return ()
    pattern = re.compile(
        r"\b(?:the\s+)?(?:request|prompt|source)\s+(?:says|states|mentions|describes)"
        r"(?:\s+that)?\s+(?P<clause>.+)$",
        flags=re.IGNORECASE,
    )
    clauses: list[str] = []
    for match in pattern.finditer(value):
        clause = match.group("clause").strip(" .")
        has_subject_action = bool(
            _VISIBLE_RESULT_RE.search(clause)
            or _APPOSITIVE_ACTOR_RE.search(clause)
            or _NAMED_ROLE_RE.search(clause)
            or leading_actor_action_match(clause)
        )
        if clause and has_subject_action and not _hard_non_path(clause):
            clauses.append(clause)
    return tuple(clauses)


def _embedded_product_grant_clauses(value: str) -> tuple[str, ...]:
    match = _PRODUCT_GRANT_RE.match(value.strip(" ."))
    if not match:
        return ()
    tail = match.group("tail").strip(" .")
    action = re.search(rf"\b(?:to\s+)?(?P<verb>{_BASE_ACTION_PATTERN})\b", tail, flags=re.IGNORECASE)
    if not action:
        return ()
    actor = tail[: action.start()].strip(" ,")
    action_text = tail[action.start("verb") :].strip(" .")
    if (
        not actor
        or len(actor.split()) > 8
        or _INVALID_ROLE_TRAILING_RE.search(actor)
        or not action_text
    ):
        return ()
    return (f"{actor} can {action_text}",)


def _path_score(value: str) -> int:
    text = _clean(value).strip(" .")
    if not text:
        return -100
    model = first_path_model(text)
    score = min(len(model.steps), 5) * 7
    score += 8 if model.material_action else 0
    score += 8 if model.visible_outcome or _VISIBLE_RESULT_RE.search(text) else 0
    score += 4 if has_human_actor_signal(text) else 0
    score += 3 if _SEQUENCE_RE.search(text) else 0
    score -= 35 if _hard_non_path(text) else 0
    score -= 8 if len(text.split()) < 6 else 0
    return score


def _hard_non_path(value: str) -> bool:
    return bool(
        _HARD_NON_PATH_RE.search(value)
        or _PRODUCT_IDENTITY_DECLARATION_RE.search(_clean(value))
        or _CREATE_REQUEST_WRAPPER_RE.search(_clean(value))
        or contains_word_sense_metadata_clause(value)
    )


def _clean(value: object) -> str:
    return " ".join(clean_markdown_text(str(value or "")).split()).strip()


__all__ = [
    "StructuredPromptFacts",
    "explicit_actor_evidence",
    "explicit_product_title_evidence",
    "ranked_first_path_evidence",
    "structured_prompt_facts",
]
