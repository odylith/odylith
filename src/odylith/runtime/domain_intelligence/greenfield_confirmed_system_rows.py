"""Internal system row parsing for confirmed greenfield intent records."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text as _title_case_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import reference_relation_description
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language


_GENERIC_SYSTEM_NAME_KEYS = {
    "workflow service",
    "state store",
    "evidence review",
}

_SYSTEM_NAME_NOUNS = frozenset(
    """
    adapter adapters api apis client clients console consoles controller controllers coordinator coordinators
    dashboard dashboards engine engines flow flows gateway gateways harness harnesses integration integrations
    libraries library ledger ledgers log logging manager managers model models module modules monitor monitoring
    nudge nudges pipeline pipelines queue queues record records recorder recorders register registers reminder reminders schedule
    schedules scheduling screen screens service services store stores surface surfaces tracker trackers tracking view
    views workflow workflows
    """.split()
)

def confirmed_system_name(value: str) -> str:
    cleaned = _strip_scope_prefix(_clean(value))
    raw = re.split(r"\s+[—-]\s+|\s*:\s*", cleaned, maxsplit=1)[0].strip()
    raw = _flatten_parenthetical_label(raw)
    raw, _description = _split_system_action_clause(raw)
    return _clean(raw) or "Product System"


def confirmed_system_description(value: str) -> str:
    cleaned = _strip_scope_prefix(_clean(value))
    parts = re.split(r"\s+[—-]\s+|\s*:\s*", cleaned, maxsplit=2)
    if len(parts) > 2:
        middle = _clean(parts[1])
        body = _clean(parts[2])
        if middle and _looks_generated_system_description(body):
            if _word_count(middle) < 5:
                return _normalize_system_description(
                    f"{middle} while keeping required inputs, blockers, and proof evidence clear"
                )
            return _normalize_system_description(middle)
        if middle and not _looks_generated_system_description(middle):
            return _normalize_system_description(middle)
    if len(parts) > 1:
        head = _clean(parts[0])
        _name, head_description = _split_system_action_clause(head)
        body = _clean(parts[1])
        if head_description and _looks_generated_system_description(body):
            return _normalize_system_description(head_description)
        if _looks_generated_system_description(body):
            return _normalize_system_description(_concise_system_description(confirmed_system_name(head), context_text=""))
        return _normalize_system_description(body)
    _name, description = _split_system_action_clause(cleaned)
    descriptor = _descriptor_parenthetical_text(cleaned)
    if not description and descriptor:
        return _normalize_system_description(
            _descriptor_system_description(confirmed_system_name(cleaned), descriptor)
        )
    return _normalize_system_description(description or cleaned)


def _strip_scope_prefix(value: str) -> str:
    text = _clean(value)
    return re.sub(
        r"^(?:optional|optionally|deferred|future|later|if\s+needed|if\s+available)(?:\s*:\s*|\s+)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def _descriptor_parenthetical_text(value: str) -> str:
    match = re.search(r"\(([^)]{3,160})\)", _clean(value))
    if not match:
        return ""
    body = _clean(match.group(1))
    if "," in body or _word_count(body) > 4:
        return body
    return ""


def _flatten_parenthetical_label(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"\(([^)]{3,160})\)", _parenthetical_label_replacement, text)
    return _clean(text)


def _parenthetical_label_replacement(match: re.Match[str]) -> str:
    body = _clean(match.group(1))
    if "," in body or _word_count(body) > 4:
        return ""
    return f" {body}"


def internal_system_rows(
    sections: Mapping[str, list[str]],
    *,
    section_list: Any,
    section_text: Any,
    context_text: str = "",
) -> list[str]:
    rows = section_list(sections, "internal_systems")
    component_rows = section_list(sections, "component_responsibilities")
    rows = preferred_internal_rows(rows, component_rows)
    if not rows:
        rows = component_rows
    else:
        expanded = expand_internal_system_rows(rows, context_text=context_text)
        if component_rows and any(not has_meaningful_system_description(row) for row in expanded):
            return expand_internal_system_rows(component_rows, context_text=context_text)
        return expanded
    if not rows:
        rows = _combined_system_rows(sections, "internal", section_text=section_text)
    return expand_internal_system_rows(rows, context_text=context_text)


def preferred_internal_rows(rows: list[str], component_rows: list[str]) -> list[str]:
    """Prefer rows that already describe component responsibility in reviewable terms."""

    if not rows:
        return component_rows
    if not component_rows:
        return rows
    row_score = sum(_row_detail_score(row) for row in rows)
    component_score = sum(_row_detail_score(row) for row in component_rows)
    if component_score > row_score:
        return component_rows
    return rows


def expand_internal_system_rows(rows: list[str], *, context_text: str = "") -> list[str]:
    cleaned = [_clean(row) for row in rows if _clean(row)]
    if len(cleaned) == 1:
        descriptor_row = _descriptor_system_row(cleaned[0], context_text=context_text)
        if descriptor_row:
            return [descriptor_row]
    if len(cleaned) == 1 and _explicit_system_row(cleaned[0]):
        return [_system_sentence_row(cleaned[0], context_text=context_text) or cleaned[0]]
    if len(cleaned) == 1:
        system_name, description = _split_system_action_clause(cleaned[0])
        if description and system_name != cleaned[0] and _system_name_head_is_plausible(system_name):
            return [_format_system_row(system_name, description, context_text=context_text)]
    sentence_rows = _system_sentence_rows(" ".join(cleaned), context_text=context_text)
    if len(cleaned) == 1 and len(sentence_rows) >= 2:
        return sentence_rows
    if len(cleaned) != 1:
        expanded: list[str] = []
        for row in cleaned:
            descriptor_row = _descriptor_system_row(row, context_text=context_text)
            if descriptor_row:
                expanded.append(descriptor_row)
                continue
            expanded.append(
                _system_sentence_row(row, context_text=context_text)
                or _concise_system_row(row, context_text=context_text)
                or row
            )
        return expanded
    paragraph = cleaned[0]
    candidates = _extract_internal_system_candidates(paragraph)
    if len(candidates) < 2:
        system_name, description = _split_system_action_clause(paragraph)
        if description:
            return [_format_system_row(system_name, description, context_text=context_text)]
        return cleaned
    rationale = _internal_system_rationale(paragraph)
    expanded: list[str] = []
    for candidate in candidates:
        description = _expanded_system_description(candidate, context_text=context_text, rationale=rationale)
        if rationale:
            description = f"{description}. Rationale: {rationale.rstrip('.')}"
        expanded.append(f"{_title_case_phrase(candidate)} — {description}")
    return expanded


def intent_context_text(intent: Mapping[str, Any], *, strings: Any) -> str:
    parts = [
        _clean(intent.get("product_story")),
        _clean(intent.get("problem")),
        _clean(intent.get("customer")),
        _clean(intent.get("opportunity")),
        _clean(intent.get("product_view")),
        _clean(intent.get("first_path")),
        _clean(intent.get("state_object")),
        _clean(intent.get("proof_boundary")),
        ". ".join(strings(intent.get("success_metrics"))),
        ". ".join(strings(intent.get("component_responsibilities"))),
        ". ".join(strings(intent.get("human_actors"))),
        ". ".join(strings(intent.get("external_systems"))),
        ". ".join(strings(intent.get("assumptions"))),
        ". ".join(strings(intent.get("non_goals"))),
    ]
    return _clean(". ".join(part.strip(" .") for part in parts if part))


def role_or_system_rows(value: object) -> list[str]:
    if isinstance(value, Mapping):
        row = _row_from_mapping(value)
        return [row] if row else []
    if isinstance(value, str):
        return _rows_from_text(value)
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return []
    rows: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            row = _row_from_mapping(item)
            if row:
                rows.append(row)
            continue
        rows.extend(_rows_from_text(str(item or "")))
    return [_clean(row) for row in rows if _clean(row)]


def has_meaningful_system_description(row: str, *, minimum_words: int = 5) -> bool:
    name = confirmed_system_name(row)
    description = confirmed_system_description(row)
    if not name or name == description:
        return False
    if _word_count(description) >= minimum_words:
        return True
    return bool(
        _word_count(description) >= 3
        and re.search(
            r"\b(?:blocks?|blocking|captures?|capturing|owns?|owning|validates?|validating|computes?|computing|evaluates?|evaluating|"
            r"explains?|explaining|prevents?|preventing|protects?|protecting|produces?|producing|proposes?|proposing|"
            r"recommends?|recommending|suggests?|suggesting|"
            r"returns?|returning|routes?|routing|records?|recording|stores?|storing|preserves?|preserving|"
            r"configures?|configuring|supports?|supporting|owned\s+by)\b",
            description,
            re.IGNORECASE,
        )
    )


def contains_generic_system_scaffold(system_rows: list[str]) -> bool:
    keys = {_system_name_key(confirmed_system_name(row)) for row in system_rows}
    keys.discard("")
    return _GENERIC_SYSTEM_NAME_KEYS.issubset(keys)


def _normalize_system_description(value: str) -> str:
    text = normalize_visible_result_language(_clean(value))
    relation = reference_relation_description(text)
    if relation:
        return relation
    text = re.sub(r"^(?:hold|holds|holding)\s+", "maintains ", text, flags=re.IGNORECASE)
    text = re.sub(r"^combines?\s+reference\s+ranges?\s+with\b", "evaluates reference ranges against", text, flags=re.IGNORECASE)
    return _clean(text)


def _looks_generated_system_description(value: str) -> bool:
    text = _clean(value).casefold()
    return bool(
        not text
        or "required inputs" in text
        or "blocked-case evidence links" in text
        or "handoff boundaries for the confirmed first path" in text
        or re.search(r"\bkeeps? .+ state, validation result, blocker state, and handoff evidence together\b", text)
    )


def _split_system_action_clause(value: str) -> tuple[str, str]:
    """Split compact system rows like "Rules engine computing ratios" generically."""

    text = _clean(value)
    if not text:
        return "", ""
    purpose = _split_system_purpose_clause(text)
    if purpose[0] or purpose[1]:
        return purpose
    descriptor = _split_system_descriptor_clause(text)
    if descriptor[0] or descriptor[1]:
        return descriptor
    relative = _split_relative_system_action_clause(text)
    if relative[0] or relative[1]:
        return relative
    split_pattern = re.compile(
        r"\s+(?=(?:owned\s+by|"
        r"blocks?|blocking|captures?|capturing|owns?|owning|validates?|validating|computes?|computing|evaluates?|evaluating|"
        r"exposes?|exposing|explains?|explaining|prevents?|preventing|protects?|protecting|"
        r"produces?|producing|proposes?|proposing|recommends?|recommending|suggests?|suggesting|"
        r"returns?|returning|routes?|routing|records?|recording|stores?|storing|"
        r"shows?|showing|renders?|rendering|generates?|generating|calculates?|calculating|"
        r"configures?|configuring|groups?|grouping|aligns?|aligning|tracks?|tracking|manages?|managing)\b)",
        re.IGNORECASE,
    )
    for match in split_pattern.finditer(text):
        head = text[: match.start()].strip(" .")
        tail = text[match.start() :].strip(" .")
        if _split_would_clip_system_name(head):
            continue
        if _system_name_head_is_plausible(head) and _word_count(tail) >= 2:
            return _clean_system_name_head(head), tail
    return _clean_system_name_head(text), ""


def _split_would_clip_system_name(head: str) -> bool:
    words = _clean(head).casefold().strip(".,;:").split()
    return bool(words and words[-1] in {"and", "or"})


def _split_relative_system_action_clause(value: str) -> tuple[str, str]:
    text = _clean(value)
    match = re.match(
        r"(?P<head>.+?\b(?:adapter|application|boundary|capture|console|dashboard|engine|flow|ledger|"
        r"library|log|management|manager|model|module|nudge|portal|queue|record|reminder|schedule|service|store|"
        r"surface|tracker|tracking|view|workspace))\s+(?:that|which|who)\s+(?P<body>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    head = _clean(match.group("head")).strip(" .")
    body = _clean(match.group("body")).strip(" .")
    if _system_name_head_is_plausible(head) and _word_count(body) >= 2 and looks_like_finite_action(body):
        return _clean_system_name_head(head), body
    return "", ""


def _split_system_descriptor_clause(value: str) -> tuple[str, str]:
    text = _clean(value)
    match = re.match(
        r"(?P<head>.+?\b(?:adapter|application|capture|console|dashboard|engine|flow|ledger|library|log|"
        r"management|manager|model|module|nudge|portal|queue|record|reminder|schedule|service|store|"
        r"surface|tracker|tracking|view|workspace))\s+with\s+(?P<body>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    head = _clean(match.group("head")).strip(" .")
    body = _clean(match.group("body")).strip(" .")
    if _system_name_head_is_plausible(head) and _word_count(body) >= 2:
        return _clean_system_name_head(head), f"supports {body}"
    return "", ""


def _split_system_purpose_clause(value: str) -> tuple[str, str]:
    text = _clean(value)
    match = re.match(r"(?P<head>.+?)\s+to\s+(?P<purpose>[a-z][A-Za-z0-9 ',/&-]{3,120})$", text, flags=re.IGNORECASE)
    if not match:
        return "", ""
    head = _clean(match.group("head")).strip(" .")
    purpose = _clean(match.group("purpose")).strip(" .")
    if not _system_name_head_is_plausible(head) or _word_count(purpose) < 3:
        return "", ""
    return _clean_system_name_head(head), f"supports {_purpose_object(purpose)}"


def _purpose_object(value: str) -> str:
    text = _clean(value).strip(" .")
    match = re.match(
        r"^(?:accept|act|add|advance|alert|approve|build|capture|check|choose|compare|complete|connect|create|decide|deliver|display|explain|"
        r"help|highlight|improve|keep|log|lower|maintain|make|notify|process|record|reduce|remind|review|route|send|show|store|support|"
        r"sustain|track|update|validate)\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    obj = _clean(match.group("object")).strip(" .")
    return obj or text


def _clean_system_name_head(value: str) -> str:
    return _clean(value)


def _system_name_head_is_plausible(value: str) -> bool:
    head = _clean(value)
    if not head or _word_count(head) > 8:
        return False
    return bool(
        re.search(
            r"\b(adapter|application|console|dashboard|engine|flow|ledger|library|log|logging|model|monitoring|nudge|portal|queue|record|register|registry|reminder|schedule|scheduling|service|store|surface|tracker|tracking|trail|view|workspace)\b",
            head,
            flags=re.IGNORECASE,
        )
    )


def _row_detail_score(row: str) -> int:
    text = _clean(row)
    name = confirmed_system_name(text)
    description = confirmed_system_description(text)
    score = _word_count(description)
    if name and name != description:
        score += 8
    if re.search(
        r"\b(?:receives?|produces?|proposes?|recommends?|suggests?|records?|stores?|tracks?|links?|derives?|controls?|reviews?|"
        r"explains?|validates?|normalizes?|preserves?|routes?|captures?)\b",
        description,
        re.IGNORECASE,
    ):
        score += 6
    if re.search(r"\b(?:evidence|state|source|actor|decision|review|failure|blocked|history)\b", description, re.IGNORECASE):
        score += 4
    return score


def _combined_system_rows(sections: Mapping[str, list[str]], target: str, *, section_text: Any) -> list[str]:
    text = section_text(sections, "systems")
    if not text:
        return []
    target_pattern = (
        r"internal(?:\s+product)?\s+systems?"
        if target == "internal"
        else r"external(?:\s+product)?\s+systems?"
    )
    other_pattern = (
        r"external(?:\s+product)?\s+systems?"
        if target == "internal"
        else r"internal(?:\s+product)?\s+systems?"
    )
    match = re.search(
        rf"\b{target_pattern}\b\s*(?:are|include|includes|:)\s*(.+?)(?=\b{other_pattern}\b\s*(?:are|include|includes|:)|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return []
    return role_or_system_rows(match.group(1))


def _explicit_system_row(value: str) -> bool:
    text = _clean(value)
    separator = re.search(r"\s+[—-]\s+|:\s+", text)
    if not separator:
        return False
    name = _clean(text[: separator.start()])
    body = _clean(text[separator.end() :])
    return _usable_explicit_system_candidate(name) and _word_count(body) >= 4


def _expanded_system_description(candidate: str, *, context_text: str, rationale: str) -> str:
    subject = candidate.lower()
    clause = _best_context_clause(candidate, context_text)
    if clause:
        return f"Owns {subject}. Relevant behavior: {_brief_clause(clause, limit=240)}"
    if rationale:
        return f"Defines how {subject} receives input, changes state, produces output, and exposes review evidence"
    return f"Defines how {subject} receives input, changes state, produces output, and exposes review evidence"


def _best_context_clause(candidate: str, context_text: str) -> str:
    terms = _semantic_terms(candidate)
    if not terms:
        return ""
    scored: list[tuple[int, int, str]] = []
    for index, clause in enumerate(_context_clauses(context_text)):
        clause_terms = _semantic_terms(clause)
        overlap = len(terms & clause_terms)
        if overlap <= 0:
            continue
        exact = sum(1 for term in terms if re.search(rf"\b{re.escape(term)}\w*\b", clause, flags=re.IGNORECASE))
        pronoun_penalty = 6 if re.match(r"^(?:it|they|this|that|the\s+primary\s+state\s+object)\b", clause, flags=re.IGNORECASE) else 0
        scored.append((overlap * 10 + exact - pronoun_penalty, -index, clause))
    if not scored:
        return ""
    scored.sort(reverse=True)
    return scored[0][2]


def _context_clauses(text: str) -> list[str]:
    clauses: list[str] = []
    context = re.sub(r"([.!?][\"'])\s+", "\\1\n", _clean(text))
    context = re.sub(r"([.!?])\s+", "\\1\n", context)
    for sentence in context.splitlines():
        for clause in re.split(r"\s*;\s*|\s+,\s+(?=(?:and|or|then|when|while|without)\b)", sentence):
            cleaned = _clean(clause).strip(" .")
            if _word_count(cleaned) >= 6:
                clauses.append(cleaned)
    return clauses


def _brief_clause(value: str, *, limit: int) -> str:
    text = _clean(value).strip(" .")
    if len(text) <= limit:
        return text
    return clip_text_at_word_boundary(
        text,
        limit=limit,
        dangling_words={"a", "an", "and", "for", "from", "of", "or", "the", "to", "with"},
    )


def _extract_internal_system_candidates(paragraph: str) -> list[str]:
    text = _clean(paragraph)
    if not text:
        return []
    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    body = first_sentence
    match = re.search(
        r"\b(?:combine|combines|include|includes|contain|contains|consist(?:s)?\s+of|uses?|use)\b\s+(.+?)(?:\s+into\s+|\s+as\s+one\s+|\s+within\s+one\s+|[.!?]|$)",
        first_sentence,
        re.IGNORECASE,
    )
    if match:
        body = match.group(1)
    body = re.sub(r"^(?:the\s+)?internal\s+(?:product\s+)?systems?\s+", "", body, flags=re.IGNORECASE)
    body = re.sub(r"^(?:a|an|the)\s+", "", body, flags=re.IGNORECASE)
    pieces = re.split(r"\s*(?:;|,|\band\b)\s+", body)
    candidates: list[str] = []
    for piece in pieces:
        candidate = _clean(re.sub(r"^(?:a|an|the|and)\s+", "", piece, flags=re.IGNORECASE))
        candidate = re.sub(r"\b(?:into|for|so)\b.*$", "", candidate, flags=re.IGNORECASE).strip()
        if _usable_internal_system_candidate(candidate):
            normalized = _clean(candidate)
            if normalized.casefold() not in {value.casefold() for value in candidates}:
                candidates.append(normalized)
    return candidates[:8]


def _descriptor_system_row(value: str, *, context_text: str = "") -> str:
    descriptor = _descriptor_parenthetical_text(value)
    if not descriptor:
        return ""
    name = confirmed_system_name(value)
    if not _usable_internal_system_candidate(name):
        return ""
    return _format_system_row(
        name,
        _descriptor_system_description(name, descriptor),
        context_text=context_text,
    )


def _descriptor_system_description(name: str, descriptor: str) -> str:
    subject = _readable_descriptor_list(descriptor)
    name_text = _clean(name).casefold()
    if re.search(r"\b(?:view|surface|dashboard|interface|screen|portal)\b", name_text):
        return f"presents {subject} while keeping source facts and blockers clear"
    if re.search(r"\b(?:library|store|registry|ledger|log|record|tracker)\b", name_text):
        return f"keeps {subject} with required inputs, blockers, and proof evidence clear"
    return f"supports {subject} while keeping required inputs, blockers, and proof evidence clear"


def _readable_descriptor_list(value: str) -> str:
    text = _clean(value).strip(" .")
    parts = [_clean(part).strip(" .") for part in text.split(",") if _clean(part).strip(" .")]
    if len(parts) >= 2:
        return ", ".join(parts[:-1]) + f" and {parts[-1]}"
    return text


def _row_from_mapping(value: Mapping[str, Any]) -> str:
    name = _clean(
        value.get("name")
        or value.get("title")
        or value.get("role")
        or value.get("actor")
        or value.get("system")
        or value.get("component")
    )
    description = _clean(
        value.get("description")
        or value.get("summary")
        or value.get("responsibility")
        or value.get("purpose")
        or value.get("value")
    )
    if name and description:
        return f"{name}: {description}"
    return name or description


def _rows_from_text(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    line_rows: list[str] = []
    for raw_line in str(value or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if line:
            line_rows.append(_clean(line))
    if len(line_rows) > 1:
        return line_rows
    labeled = _labeled_span_rows(text)
    if len(labeled) >= 2:
        return labeled
    sentence_rows = _system_sentence_rows(text)
    if len(sentence_rows) >= 2:
        return sentence_rows
    return [text]


def _labeled_span_rows(text: str) -> list[str]:
    matches = list(
        re.finditer(
            r"(?:(?<=^)|(?<=[.;]\s))(?P<label>[A-Z][A-Za-z0-9 /&(),-]{1,72}?):\s*",
            text,
        )
    )
    if len(matches) < 2:
        return []
    rows: list[str] = []
    for index, match in enumerate(matches):
        label = _clean(match.group("label"))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = _clean(text[match.end() : end].strip(" .;"))
        if label and body:
            rows.append(f"{label}: {body}")
    return rows


def _system_sentence_rows(text: str, *, context_text: str = "") -> list[str]:
    rows: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", _clean(text)):
        row = _system_sentence_row(sentence, context_text=context_text)
        if row:
            rows.append(row)
    return rows


def _system_sentence_row(sentence: str, *, context_text: str = "") -> str:
    text = _clean(sentence).strip(" .")
    if not text:
        return ""
    separator = re.search(r"\s+[—-]\s+|:\s+", text)
    if separator:
        name = _clean(text[: separator.start()])
        body = _clean(text[separator.end() :])
        if _usable_explicit_system_candidate(name) and _word_count(body) >= 4:
            return _format_system_row(name, body, context_text=context_text)
    relative = re.match(r"(?P<name>.+?)\s+(?:that|which|who|where|whose)\s+(?P<body>.+)$", text, re.IGNORECASE)
    if relative:
        name = _clean(relative.group("name"))
        body = _clean(relative.group("body"))
        if _looks_like_system_name(name) and _word_count(body) >= 4:
            return _format_system_row(name, body, context_text=context_text)
    prefix = _system_name_prefix(text)
    if prefix:
        name, body = prefix
        if _word_count(body) >= 4:
            return _format_system_row(name, body, context_text=context_text)
    name = _leading_title_phrase(text)
    if not name:
        return ""
    body = _clean(text[len(name) :].strip(" ,:;.-"))
    if _word_count(body) < 4:
        return ""
    return _format_system_row(name, body, context_text=context_text)


def _concise_system_row(value: str, *, context_text: str = "") -> str:
    name = _clean(value).strip(" .")
    if not _usable_internal_system_candidate(name):
        return ""
    if re.search(r"\b(?:because|therefore|should|must|needs?|proves?|proof|release)\b", name, re.IGNORECASE):
        return ""
    system_name, description = _split_system_action_clause(name)
    if description:
        return _format_system_row(system_name, description, context_text="")
    return _format_system_row(name, _concise_system_description(name, context_text=context_text), context_text="")


def _concise_system_description(name: str, *, context_text: str) -> str:
    subject = _clean(name).casefold()
    return (
        f"owns {subject} state, required inputs, blocked-case evidence links, and handoff boundaries "
        "for the confirmed first path"
    )


def _format_system_row(name: str, body: str, *, context_text: str = "") -> str:
    return f"{_title_case_system_name(name)} — {_contextualized_system_body(name=name, body=body, context_text=context_text)}"


def _title_case_system_name(value: str) -> str:
    value = re.sub(
        r"^Reviewer\s+(?=(?:Dashboard|Export|Surface|View|Portal|Report|Package)\b)",
        "Review ",
        _clean(value),
        flags=re.IGNORECASE,
    )
    words: list[str] = []
    for index, raw in enumerate(value.split()):
        word = raw.strip()
        lower = word.casefold()
        if index > 0 and lower in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
            words.append(lower)
            continue
        if _preserve_system_slash_token(word):
            label_word = "/".join(_title_case_system_token(part) for part in word.split("/") if part)
        elif _preserve_system_hyphen_token(word):
            head, *tail = word.split("-")
            label_word = "-".join([_title_case_system_token(head), *tail])
        else:
            label_word = _title_case_phrase(word)
        if _append_slash_conjunction_system_word(words, raw_word=word, label_word=label_word):
            continue
        words.append(label_word)
    return _clean(" ".join(words))


def _append_slash_conjunction_system_word(words: list[str], *, raw_word: str, label_word: str) -> bool:
    if not words or words[-1].casefold() != "and":
        return False
    if "/" not in raw_word or " and " not in label_word or re.search(r"://|^/", raw_word):
        return False
    parts = [part.strip() for part in label_word.split(" and ") if part.strip()]
    if len(parts) < 2:
        return False
    words.pop()
    if words:
        words[-1] = words[-1].rstrip(",") + ","
    for part in parts[:-1]:
        words.append(part.rstrip(",") + ",")
    words.append("and")
    words.append(parts[-1])
    return True


def _preserve_system_slash_token(value: str) -> bool:
    if "/" not in value or re.search(r"://|^/", value):
        return False
    lower = value.casefold().strip(".,;:()")
    return lower == "rule/threshold" or all(part.isupper() and len(part) <= 5 for part in value.split("/") if part)


def _preserve_system_hyphen_token(value: str) -> bool:
    if "-" not in value or value.startswith("-") or value.endswith("-"):
        return False
    lower = value.casefold().strip(".,;:()")
    return lower in {
        "conflict-of-interest",
        "reason-code",
        "revision-round",
        "role-based",
        "source-backed",
        "user-facing",
    }


def _title_case_system_token(value: str) -> str:
    token = _clean(value)
    return f"{token[:1].upper()}{token[1:]}" if token else ""


def _contextualized_system_body(*, name: str, body: str, context_text: str) -> str:
    description = _repair_system_description(name=name, description=_clean(body).strip(" ."))
    if _usable_system_description(description) and _word_count(description) >= 4:
        return description
    if _usable_system_description(description):
        return f"{description} while keeping blocker state and handoff evidence visible"
    topic = _system_topic_from_name(name)
    return f"keeps {topic} state, validation result, blocker state, and handoff evidence together"


def _repair_system_description(*, name: str, description: str) -> str:
    text = normalize_visible_result_language(_clean(description)).strip(" .;:")
    relation = reference_relation_description(text)
    if relation:
        return relation
    text = re.sub(r"^(?:and|or)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRelated path\s*:\s*[^.;]+[.;]?", "", text, flags=re.IGNORECASE).strip(" .;:")
    purpose = _for_purpose_description(text)
    if purpose:
        return purpose
    text = re.sub(r"^with\s+", "keeps ", text, flags=re.IGNORECASE)
    if re.match(r"^owned\s+by\s+", text, flags=re.IGNORECASE):
        return f"keeps {_system_topic_from_name(name)} state under the named owner with validation and change evidence"
    if re.search(r"\b(?:runs?|evaluates?|checks?)\s+it\s+against\b", text, flags=re.IGNORECASE):
        return ""
    if re.match(r"^(?:their|they|them|it|this|that|who|which|where)\b", text, flags=re.IGNORECASE):
        return ""
    return text


def _for_purpose_description(value: str) -> str:
    text = _clean(value).strip(" .;:")
    match = re.match(r"^for\s+(?P<body>.+)$", text, flags=re.IGNORECASE)
    if not match:
        return ""
    body = _clean(match.group("body")).strip(" .,;:")
    if not body:
        return ""
    return f"supports {body} with visible state, blocker handling, and proof evidence"


def _usable_system_description(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    if re.search(r"\bRelated path\s*:", text, flags=re.IGNORECASE):
        return False
    if re.match(r"^(?:and|or|their|they|them|it|this|that|who|which|where)\b", text, flags=re.IGNORECASE):
        return False
    return _word_count(text) >= 3


def _system_topic_from_name(name: str) -> str:
    text = _clean(name).casefold()
    text = re.sub(
        r"\b(?:service|services|system|systems|engine|engines|store|stores|surface|surfaces|"
        r"adapter|adapters|queue|queues|view|views|flow|flows|tracker|trackers|ledger|ledgers|"
        r"module|modules|dashboard|dashboards|record|records|manager|managers)\b",
        "",
        text,
    )
    text = _clean(text)
    return text or _clean(name).casefold() or "component"


def _leading_title_phrase(text: str) -> str:
    tokens = text.split()
    if len(tokens) < 3:
        return ""
    name_tokens: list[str] = []
    for token in tokens:
        cleaned = token.strip(".,;:()[]")
        if not cleaned:
            break
        if _looks_like_name_token(cleaned) or (
            name_tokens and cleaned.casefold() in {"and", "or", "of", "for", "to", "the", "&"}
        ):
            name_tokens.append(cleaned)
            continue
        break
    while name_tokens and name_tokens[-1].casefold() in {"and", "or", "of", "for", "to", "the", "&"}:
        name_tokens.pop()
    if len(name_tokens) < 2 or len(name_tokens) > 9:
        return ""
    candidate = _clean(" ".join(name_tokens))
    return candidate if _usable_internal_system_candidate(candidate) else ""


def _system_name_prefix(text: str) -> tuple[str, str] | None:
    tokens = text.split()
    if len(tokens) < 4:
        return None
    max_name_words = min(9, len(tokens) - 3)
    for index in range(2, max_name_words + 1):
        candidate = _clean(" ".join(tokens[:index]).strip(" ,:;.-"))
        if not _looks_like_system_name(candidate):
            continue
        body = _clean(" ".join(tokens[index:]).strip(" ,:;.-"))
        if body and looks_like_finite_action(body):
            return candidate, body
    for index in range(max_name_words, 1, -1):
        candidate = _clean(" ".join(tokens[:index]).strip(" ,:;.-"))
        qualifier = re.search(r"\b(for|with)\b", candidate, flags=re.IGNORECASE)
        if qualifier:
            prefix = _clean(candidate[: qualifier.start()].strip(" ,:;.-"))
            tail = _qualified_tail_from_source(text, prefix) or _clean(
                " ".join([candidate[qualifier.start() :], *tokens[index:]]).strip(" ,:;.-")
            )
            if _looks_like_system_name(prefix) and _word_count(tail) >= 4:
                return prefix, tail
        if not _looks_like_system_name(candidate):
            continue
        body = _clean(" ".join(tokens[index:]).strip(" ,:;.-"))
        if body:
            return candidate, body
    return None


def _qualified_tail_from_source(text: str, prefix: str) -> str:
    source = _clean(text).strip(" .")
    head = _clean(prefix).strip(" .")
    if not source or not head:
        return ""
    pattern = rf"^{re.escape(head)}\s+(?P<tail>(?:for|with)\b.+)$"
    match = re.match(pattern, source, flags=re.IGNORECASE)
    return _clean(match.group("tail")).strip(" ,:;.-") if match else ""


def _looks_like_system_name(value: str) -> bool:
    candidate = _clean(re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.IGNORECASE))
    if not _usable_internal_system_candidate(candidate):
        return False
    tokens = [token.strip(".,;:()[]").casefold() for token in candidate.split()]
    return any(token in _SYSTEM_NAME_NOUNS for token in tokens)


def _looks_like_name_token(value: str) -> bool:
    if value.isupper() and len(value) > 1:
        return True
    return bool(re.match(r"^[A-Z][A-Za-z0-9&/-]*$", value))


def _usable_internal_system_candidate(candidate: str) -> bool:
    words = _word_count(candidate)
    if words < 2 or words > 9:
        return False
    lowered = candidate.casefold()
    if lowered in {"internal product systems", "internal systems"}:
        return False
    if re.match(r"^(?:one|single)\s+.+\s+architecture$", lowered):
        return False
    if re.search(r"\b(?:because|matter|must|while|still|enough|first path|product)\b", lowered):
        return False
    return True


def _usable_explicit_system_candidate(candidate: str) -> bool:
    """Allow concise reviewed labels when a row provides its own description."""

    text = _clean(candidate)
    words = _word_count(text)
    if words < 1 or words > 9:
        return False
    lowered = text.casefold()
    if lowered in {"internal product systems", "internal systems"}:
        return False
    if re.search(r"\b(?:because|matter|must|while|still|enough|first path|product)\b", lowered):
        return False
    return bool(re.search(r"[A-Za-z]", text))


def _internal_system_rationale(paragraph: str) -> str:
    text = _clean(paragraph)
    match = re.search(r"\bmatter\s+because\s+(.+?)(?:[.!?]|$)", text, re.IGNORECASE)
    if match:
        return _clean(match.group(1))
    match = re.search(r"\bmust\s+(.+?)(?:[.!?]|$)", text, re.IGNORECASE)
    if match:
        return "must " + _clean(match.group(1))
    return "keeps the accepted first path, product state, evidence, and proof boundary connected"


def _system_name_key(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s]+", " ", str(value or "").casefold())
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "confirmed_system_description",
    "confirmed_system_name",
    "contains_generic_system_scaffold",
    "expand_internal_system_rows",
    "has_meaningful_system_description",
    "internal_system_rows",
    "intent_context_text",
    "preferred_internal_rows",
    "role_or_system_rows",
]
