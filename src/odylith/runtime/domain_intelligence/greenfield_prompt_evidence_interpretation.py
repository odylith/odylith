"""Normalize structured prompt evidence and rank narrative first-path candidates."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_non_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_patterns import leading_actor_action_match
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import (
    contains_requirement_control_clause,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_release_evidence_requirement
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import (
    is_release_visible_result_statement,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_operator_review_lens_step
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import (
    is_external_dependency_clause,
)
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import is_source_obligation_clause
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import (
    word_sense_content_clause_describes_comparison,
)


@dataclass(frozen=True)
class StructuredPromptFacts:
    """Explicit product, actor, and path fields recovered without prose inference."""

    title: str = ""
    actor: str = ""
    first_path: str = ""


_TITLE_FIELDS = ("product", "product name", "title", "domain label")
_ACTOR_FIELDS = ("actor", "operator", "user", "first user")
_PATH_FIELDS = (
    "first complete path",
    "first path",
    "first path is fixed",
    "the first path is fixed",
    "path",
    "workflow",
)
_ROLE_FIELDS = ("role", "operator role", "user role")
_ACTION_FIELDS = ("objective", "action", "task", "user task")
_OUTPUT_FIELDS = ("visible result", "output", "result")
_INLINE_FIELD_NAMES = tuple(
    sorted(
        {
            *_TITLE_FIELDS,
            *_ACTOR_FIELDS,
            *_PATH_FIELDS,
            *_ROLE_FIELDS,
            *_ACTION_FIELDS,
            *_OUTPUT_FIELDS,
            "acceptance",
            "dependency",
            "domain",
            "proof boundary",
            "safety boundary",
            "state",
            "state model",
            "system",
        },
        key=len,
        reverse=True,
    )
)
_HARD_NON_PATH_RE = re.compile(
    r"\b(?:out\s+of\s+scope|unrelated|proof(?:\s+boundary)?|prove|success\s+means|"
    r"demonstrate|must\s+not|may\s+not|cannot|can't|do\s+not|never|boundary|"
    r"distinctive\s+project\s+vocabulary|"
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
_TITLE_REFERENCE_WORDS = frozenset({"a", "an", "it", "that", "the", "these", "this", "those"})
_PRODUCT_TITLE_TERMINALS = frozenset(
    {
        "app",
        "application",
        "archive",
        "board",
        "catalog",
        "console",
        "desk",
        "engine",
        "gate",
        "hub",
        "ledger",
        "manager",
        "notebook",
        "note",
        "package",
        "platform",
        "portal",
        "product",
        "record",
        "register",
        "registry",
        "service",
        "system",
        "tool",
        "tracker",
        "vault",
        "workspace",
    }
)
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
    r"\b(?P<name>[A-Z][A-Za-z0-9'/-]*),\s+(?P<article>a|an|the)\s+"
    r"(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,70}?),\s+"
    r"(?P<action>[a-z][^.!?]{2,})",
)
_NAMED_PRODUCT_GRANT_RE = re.compile(
    rf"(?:^|[.!?]\s+)(?P<title>{_TITLE_PHRASE})\s+"
    r"(?:gives|guides|helps|lets|enables|supports)\b",
)
_LEADING_NEED_ACTOR_RE = re.compile(
    r"(?:^|[.!?]\s+)(?:a|an|the)\s+"
    r"(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,90}?)\s+"
    r"(?:needs?|wants?)\s+(?:a|an|the)?\s*[^,.;!?]{1,100}?\s+(?:to|where|for)\b",
    flags=re.IGNORECASE,
)
_NAMED_PRODUCT_HELPER_TAIL_RE = re.compile(
    rf"(?:^|[.!?]\s+){_TITLE_PHRASE}\s+"
    r"(?:gives|guides|helps|lets|enables|supports)\s+(?P<tail>[^.;!?]+)",
    flags=re.IGNORECASE,
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
_INLINE_FIELD_RE = re.compile(
    r"(?:^|[\n.;]|//)\s*(?P<key>" + "|".join(re.escape(field) for field in _INLINE_FIELD_NAMES) + r")\s*:\s*",
    flags=re.IGNORECASE,
)
_PRODUCT_FOR_ACTOR_RE = re.compile(
    r"\b(?:build|create|design|make)\s+(?:a\s+|the\s+)?(?:greenfield\s+)?"
    r"(?:app|application|platform|product|service|system|tool|workspace)\s+for\s+"
    r"(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,90}?)\s+"
    r"(?:(?P<human_connector>who\s+needs?\s+to)|to)\s+"
    r"(?P<action>[a-z][^.!?;]{2,180}?)\s+in\s+"
    r"(?P<system>[A-Z][A-Za-z0-9'/-]*(?:\s+[A-Z][A-Za-z0-9'/-]*){0,4})\b",
    flags=re.IGNORECASE,
)
_IMPLEMENTATION_REQUEST_RE = re.compile(
    r"\bimplementation\s+request\s*:\s*(?:build|create|design|make)\s+"
    r"(?:a\s+|the\s+)?(?:app|application|platform|product|service|system|tool|workspace)\s+so\s+"
    r"(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,90}?)\s+can\s+"
    r"(?P<action>[a-z][^.!?;]{2,180})",
    flags=re.IGNORECASE,
)
_VISIBLE_OUTPUT_ACTION_RE = re.compile(
    r"\b(?:produce|produces|generate|generates|return|returns|show|shows|display|displays|provide|provides)\s+"
    r"(?P<output>(?:a|an|the)\s+[^,;.!?]{1,100})",
    flags=re.IGNORECASE,
)
_NEGATED_OUTPUT_SCOPE_RE = re.compile(
    r"(?:\b(?:not|never|cannot|can't|won't|shouldn't|mustn't)\b|"
    r"\b(?:forbidden|prohibited|barred|disallowed)\s+to\b|"
    r"\bnot\s+(?:allowed|permitted)\s+to\b)[^,;.!?]*$",
    flags=re.IGNORECASE,
)
_EVIDENCE_OWNED_OUTPUT_RE = re.compile(
    r"\bevidence\s+[A-Za-z0-9_-]+\s+says\s+(?:the\s+)?[^.!?]{1,100}?\s+owns\s+"
    r"(?P<output>(?:a|an|the)\s+[^.!?;]{1,100}?)"
    r"(?=\s+and\s+the\s+state\s+vocabulary\b|[.!?;])",
    flags=re.IGNORECASE,
)
_PATH_START_RE = re.compile(
    r"^(?:(?:the\s+)?first\s+path|it)?\s*(?:is\s+fixed\s*)?(?::\s*)?"
    r"begins?\s+with\s+(?P<start>.+)$",
    flags=re.IGNORECASE,
)
_PATH_NOMINAL_RESULT_RE = re.compile(
    r"^(?:the\s+)?first(?:\s+[A-Za-z0-9'-]+){0,3}\s+path\s+is\s+(?P<result>.+)$",
    flags=re.IGNORECASE,
)
_DOMAIN_LABEL_RE = re.compile(
    r"(?:^|[\n.!?]\s+)domain\s+label\s*:\s*(?P<title>[^.!?;/]+)",
    flags=re.IGNORECASE,
)


def structured_prompt_facts(value: str) -> StructuredPromptFacts:
    """Recover explicit facts from JSON, Markdown tables, or labeled rows."""

    text = str(value or "").strip()
    if not text:
        return StructuredPromptFacts()
    mapping = dict(_json_mapping(text))
    if not mapping:
        mapping.update(_markdown_field_mapping(text))
        mapping.update(_inline_field_mapping(text))
    natural_actor, natural_action = _natural_actor_action(text)
    title = _explicit_domain_label(text) or _first_field(mapping, _TITLE_FIELDS)
    actor = _first_field(mapping, _ACTOR_FIELDS) or natural_actor
    role = _first_field(mapping, _ROLE_FIELDS)
    if role and actor and role.casefold() not in actor.casefold():
        actor = f"{role} {actor}"
    path_value = _first_raw_field(mapping, _PATH_FIELDS)
    action_value = _first_raw_field(mapping, _ACTION_FIELDS) or natural_action
    output_value = _first_raw_field(mapping, _OUTPUT_FIELDS) or _natural_visible_output(text)
    first_path = _complete_structured_path(
        actor=actor,
        path_value=path_value,
        action_value=action_value,
        output_value=output_value,
    )
    return StructuredPromptFacts(title=title, actor=actor, first_path=first_path)


def ranked_first_path_evidence(value: str) -> str:
    """Return the complete ordered workflow evidence, not one high-scoring sentence."""

    structured = structured_prompt_facts(value)
    if structured.first_path:
        return structured.first_path
    rows = _narrative_rows(value)
    if not rows:
        return ""
    ordered: list[str] = []
    candidates: list[tuple[int, int, str]] = []
    for index, row in enumerate(rows):
        workflow_row = _workflow_row_projection(_workflow_claim_before_prohibition(row))
        if workflow_row and not _hard_non_path(workflow_row):
            score = _path_score(workflow_row)
            candidates.append((score, -index, workflow_row))
            if score >= 12 and _is_ordered_workflow_row(workflow_row):
                ordered.append(workflow_row)
        for workflow in _embedded_workflow_clauses(row):
            candidates.append((_path_score(workflow) + 4, -index, workflow))
        for granted_path in _embedded_product_grant_clauses(row):
            candidates.append((_path_score(granted_path) + 4, -index, granted_path))
        for evidence_clause in _embedded_evidence_clauses(row):
            candidates.append((_path_score(evidence_clause) + 2, -index, evidence_clause))
        if index + 1 < len(rows) and workflow_row and not _hard_non_path(workflow_row):
            release_result = _release_visible_result_action(rows[index + 1])
            if release_result:
                combined = f"{workflow_row}, and {release_result}"
                candidates.append((_path_score(combined), -index, combined))
            elif not _hard_non_path(rows[index + 1]):
                combined = f"{workflow_row}. {rows[index + 1]}"
                candidates.append((_path_score(combined), -index, combined))
    if ordered:
        return ". ".join(dict.fromkeys(row.rstrip(" .") for row in ordered))
    score, _position, candidate = max(candidates, default=(0, 0, ""))
    return candidate if score >= 12 else ""


def _workflow_row_projection(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text or re.match(r"^project\s+brief\s+for\b", text, flags=re.IGNORECASE):
        return ""
    grant = re.match(
        r"^(?:the\s+)?first\s+release\s+should\s+give\s+(?:the\s+)?"
        r"(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+a\s+complete\s+path\s+to\s+"
        r"(?P<action>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if grant and has_human_actor_signal(grant.group("actor")):
        action = re.sub(
            r"\s+without\s+automating\s+[^.;!?]+$",
            "",
            grant.group("action"),
            flags=re.IGNORECASE,
        ).strip(" .")
        return f"{grant.group('actor')} {action}"
    prefix, separator, tail = text.partition(" where ")
    if not separator:
        match = re.search(r"\swhere\s", text, flags=re.IGNORECASE)
        if match:
            prefix, tail = text[: match.start()], text[match.end() :]
            separator = " where "
    prefix_words = prefix.casefold().split()
    if separator and tail and (
        re.match(r"^focus\s+on\s+(?:a\s+)?governed\s+workflow$", prefix, flags=re.IGNORECASE)
        or _CREATE_REQUEST_WRAPPER_RE.match(prefix)
        or (prefix_words and prefix_words[-1] in _PRODUCT_TITLE_TERMINALS)
    ):
        projected = re.sub(r"^the\s+", "", tail, flags=re.IGNORECASE).strip(" .")
        return projected[:1].upper() + projected[1:] if re.match(r"^(?:a|an)\s+", projected) else projected
    return text


def _is_ordered_workflow_row(value: str) -> bool:
    """Keep product events while excluding setup context and operator review instructions."""

    text = _clean(value).strip(" .")
    if not text or is_operator_review_lens_step(text):
        return False
    if re.match(
        r"^(?:a|an|the)\s+.+?\s+needs?\s+(?:a|an|the)\s+product\s+for\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return not _hard_non_path(text)


def explicit_product_title_evidence(value: str) -> str:
    """Return an explicitly named product from structured or narrative evidence."""

    structured = structured_prompt_facts(value)
    if structured.title:
        return structured.title
    named_grant = _NAMED_PRODUCT_GRANT_RE.search(clean_markdown_text(str(value or "")))
    if named_grant:
        title = named_grant.group("title").strip(" .")
        if _credible_explicit_title(
            title,
            require_product_shape=False,
            allow_single_word_proper_name=True,
        ):
            return title
    candidates: list[tuple[int, str]] = []
    text = clean_markdown_text(str(value or ""))
    patterns = (
        (
            re.compile(
                rf"\b(?P<connector>uses?|using|in)\s+(?P<article>the\s+)?(?P<title>{_TITLE_PHRASE})\b"
            ),
            8,
            True,
        ),
        (
            re.compile(
                rf"(?:^|[.!?]\s+|:\s+)(?P<title>{_TITLE_PHRASE})\s+is\s+for\b"
            ),
            8,
            False,
        ),
        (
            re.compile(
                rf"(?:^|[.!?]\s+|:\s+)(?P<title>{_TITLE_PHRASE})\s+"
                r"(?:must|may|cannot|can't|reads?|imports?)\b"
            ),
            6,
            True,
        ),
    )
    for pattern, structural_score, require_product_shape in patterns:
        for match in pattern.finditer(text):
            title = match.group("title").strip(" .")
            words = title.split()
            connector = match.groupdict().get("connector", "").casefold()
            if (
                not words
                or len(words) > 5
                or not _credible_explicit_title(
                    title,
                    require_product_shape=require_product_shape,
                    allow_single_word_proper_name=connector in {"use", "uses"},
                )
            ):
                continue
            if (
                connector == "in"
                and len(words) == 1
                and not match.groupdict().get("article")
            ):
                continue
            score = structural_score + min(len(words), 4) + text.casefold().count(title.casefold())
            candidates.append((score, title))
    return max(candidates, default=(0, ""))[1]


def explicit_actor_has_human_grammar(value: str) -> bool:
    """Return whether prompt syntax explicitly marks the recovered actor as a person."""

    text = clean_markdown_text(str(value or ""))
    product_match = _PRODUCT_FOR_ACTOR_RE.search(text)
    if product_match and product_match.group("human_connector"):
        return True
    need_match = _LEADING_NEED_ACTOR_RE.search(text)
    if need_match and _has_actor_label_signal(need_match.group("actor")):
        return True
    if _named_product_helper_actor(text):
        return True
    return any(
        pattern.search(text)
        for pattern in (
            _APPOSITIVE_ACTOR_RE,
            _ROLE_NAMED_PERSON_RE,
            _ROLE_COMMA_PERSON_RE,
            _PERSON_ROLE_RE,
            _FOR_ROLE_PERSON_RE,
            _NAMED_ROLE_RE,
        )
    )


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
                if pattern is _APPOSITIVE_ACTOR_RE:
                    return f"{match.group('name')}, {match.group('article')} {role}".strip()
                return f"{role} {match.group('name')}".strip()
        need_match = _LEADING_NEED_ACTOR_RE.search(source)
        if need_match:
            actor = need_match.group("actor").strip(" ,")
            if _has_actor_label_signal(actor):
                return actor
        helper_actor = _named_product_helper_actor(source)
        if helper_actor:
            return helper_actor
    return ""


def _named_product_helper_actor(value: str) -> str:
    match = _NAMED_PRODUCT_HELPER_TAIL_RE.search(value)
    if not match:
        return ""
    tail = match.group("tail").strip(" ,")
    words = tuple(re.finditer(r"[A-Za-z0-9][A-Za-z0-9'/-]*", tail))
    for action_index in range(1, min(9, len(words))):
        actor = tail[: words[action_index].start()].strip(" ,")
        actor = re.sub(r"^(?:a|an|the)\s+", "", actor, flags=re.IGNORECASE)
        action = words[action_index].group(0)
        if _has_actor_label_signal(actor) and re.fullmatch(
            rf"(?:{_BASE_ACTION_PATTERN}|{_FINITE_ACTION_PATTERN})",
            action,
            flags=re.IGNORECASE,
        ):
            return actor
    return ""


def _has_actor_label_signal(value: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'/-]*", value)
    return bool(
        words
        and not has_non_human_actor_signal(value)
        and (has_human_actor_role_signal(value) or looks_actor_term(words[-1]))
    )


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


def _inline_field_mapping(value: str) -> dict[str, Any]:
    """Recover known labels when compact evidence places several fields on one line."""

    matches = list(_INLINE_FIELD_RE.finditer(value))
    fields: dict[str, Any] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
        field_value = value[match.end() : end].strip(" /\n\t.;")
        if field_value:
            fields[_field_key(match.group("key"))] = field_value
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


def _complete_structured_path(
    *,
    actor: str,
    path_value: Any,
    action_value: Any,
    output_value: Any,
) -> str:
    path = _clean(path_value).strip(" .")
    action = _clean(action_value).strip(" .")
    output = _clean(output_value).strip(" .")
    if not (actor or path or action):
        return ""
    start = _path_start_action(path)
    path_result = _path_nominal_result(path)
    if path and not start and not action and not output:
        return _structured_path(actor=actor, value=path_value)
    actions: list[str] = []
    if start:
        actions.append(start)
    elif path and not path_result:
        actions.append(path)
    if action and all(action.casefold() not in item.casefold() for item in actions):
        actions.append(action)
    path_result_action = _visible_output_action(path_result)
    if path_result_action:
        actions.append(path_result_action)
    output_action = _visible_output_action(output)
    if (
        output_action
        and not _output_already_present(output, actions)
    ):
        actions.append(output_action)
    return _structured_path(actor=actor, value=actions)


def _path_start_action(value: str) -> str:
    match = _PATH_START_RE.match(_clean(value).strip(" ."))
    if not match:
        return ""
    start = match.group("start").strip(" .")
    if not start:
        return ""
    return f"complete {start}"


def _path_nominal_result(value: str) -> str:
    match = _PATH_NOMINAL_RESULT_RE.match(_clean(value).strip(" ."))
    return match.group("result").strip(" .") if match else ""


def _visible_output_action(value: str) -> str:
    output = _clean(value).strip(" .")
    if not output or _NEGATED_OUTPUT_SCOPE_RE.search(output):
        return ""
    if re.match(r"^(?:produce|generate|return|show|display|provide|receive|get)\b", output, re.IGNORECASE):
        return output
    return f"receive {output}"


def _output_already_present(output: str, actions: list[str]) -> bool:
    candidates = {output.casefold()}
    without_system_context = re.sub(
        r"\s+in\s+[A-Z][A-Za-z0-9'/-]*(?:\s+[A-Z][A-Za-z0-9'/-]*){0,4}$",
        "",
        output,
    ).casefold()
    if without_system_context:
        candidates.add(without_system_context)
    return any(candidate in action.casefold() for candidate in candidates for action in actions)


def _natural_actor_action(value: str) -> tuple[str, str]:
    for pattern in (_IMPLEMENTATION_REQUEST_RE, _PRODUCT_FOR_ACTOR_RE):
        match = pattern.search(clean_markdown_text(value))
        if match:
            return match.group("actor").strip(" ,"), match.group("action").strip(" ,")
    return "", ""


def _natural_visible_output(value: str) -> str:
    text = clean_markdown_text(value)
    for match in _VISIBLE_OUTPUT_ACTION_RE.finditer(text):
        clause_start = max(
            text.rfind(boundary, 0, match.start())
            for boundary in (".", "!", "?", ";", "\n")
        )
        scope = text[clause_start + 1 : match.start()]
        contrast = tuple(re.finditer(r"\b(?:but|however|instead)\b", scope, flags=re.IGNORECASE))
        if contrast:
            scope = scope[contrast[-1].end() :]
        if _NEGATED_OUTPUT_SCOPE_RE.search(scope):
            continue
        return match.group("output").strip(" ,")
    evidence_match = _EVIDENCE_OWNED_OUTPUT_RE.search(text)
    return evidence_match.group("output").strip(" ,") if evidence_match else ""


def _explicit_domain_label(value: str) -> str:
    match = _DOMAIN_LABEL_RE.search(clean_markdown_text(value))
    return match.group("title").strip(" ,") if match else ""


def _credible_explicit_title(
    value: str,
    *,
    require_product_shape: bool,
    allow_single_word_proper_name: bool = False,
) -> bool:
    words = value.split()
    if not words or value.casefold() in _TITLE_REFERENCE_WORDS:
        return False
    if allow_single_word_proper_name and len(words) == 1:
        return True
    if not require_product_shape:
        return not (len(words) == 1 and words[0].casefold() in _PRODUCT_TITLE_TERMINALS)
    terminal = words[-1].casefold()
    branded = any(
        any(char.isupper() for char in word[1:])
        or any(char.isdigit() for char in word)
        or "-" in word
        or (len(word) > 1 and word.isupper())
        for word in words
    )
    return terminal in _PRODUCT_TITLE_TERMINALS or branded


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


def _workflow_claim_before_prohibition(value: str) -> str:
    text = _clean(value).strip(" .")
    starts = [
        match.start()
        for match in re.finditer(
            r"(?:^|;\s*)(?:it|the\s+(?:app|application|platform|product|service|system|tool|workspace))?\s*"
            r"(?:must\s+not|may\s+not|cannot|can't|do\s+not|never)\b",
            text,
            flags=re.IGNORECASE,
        )
    ]
    starts.extend(
        match.start()
        for match in re.finditer(r"\s+without\s+[^.;!?]+$", text, flags=re.IGNORECASE)
    )
    if not starts:
        return text
    return text[: min(starts)].rstrip(" ,.;:")


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
        clause = _without_word_sense_comparison_tail(match.group("clause").strip(" ."))
        has_subject_action = bool(
            _VISIBLE_RESULT_RE.search(clause)
            or _APPOSITIVE_ACTOR_RE.search(clause)
            or _NAMED_ROLE_RE.search(clause)
            or leading_actor_action_match(clause)
        )
        if clause and has_subject_action and not _hard_non_path(clause):
            clauses.append(clause)
    return tuple(clauses)


def _without_word_sense_comparison_tail(value: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9'-]+", value.casefold())
    if not word_sense_content_clause_describes_comparison(tokens):
        return value
    return re.split(r"\s+(?:as\s+both|both\s+as)\b", value, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")


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


def _release_visible_result_action(value: str) -> str:
    if not is_release_visible_result_statement(value):
        return ""
    match = re.search(r"\bshow\s+(?P<result>(?:a|an|one)\s+.+)$", _clean(value), flags=re.IGNORECASE)
    return f"show {match.group('result').strip(' .')}" if match else ""


def _hard_non_path(value: str) -> bool:
    if is_release_visible_result_statement(value):
        return False
    return bool(
        _HARD_NON_PATH_RE.search(value)
        or _PRODUCT_IDENTITY_DECLARATION_RE.search(_clean(value))
        or _CREATE_REQUEST_WRAPPER_RE.search(_clean(value))
        or is_external_dependency_clause(value)
        or is_release_evidence_requirement(value)
        or _is_policy_only_obligation(value)
        or contains_requirement_control_clause(value)
        or contains_word_sense_metadata_clause(value)
    )


def _is_policy_only_obligation(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not is_source_obligation_clause(text):
        return False
    model = first_path_model(text)
    return bool(
        len(model.steps) <= 1
        and not _VISIBLE_RESULT_RE.search(text)
        and not _SEQUENCE_RE.search(text)
    )


def _clean(value: object) -> str:
    return " ".join(clean_markdown_text(str(value or "")).split()).strip()


__all__ = [
    "StructuredPromptFacts",
    "explicit_actor_has_human_grammar",
    "explicit_actor_evidence",
    "explicit_product_title_evidence",
    "ranked_first_path_evidence",
    "structured_prompt_facts",
]
