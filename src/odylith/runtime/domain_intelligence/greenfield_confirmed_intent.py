"""Parse the small confirmed-intent artifact used by greenfield create."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent


FIELD_MIN_WORDS = {
    "product_story": 28,
    "state_object": 12,
    "first_path": 18,
    "proof_boundary": 18,
}
LIST_ROW_MIN_WORDS = 5
SYSTEM_ROW_MIN_WORDS = 5

_META_NARRATION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bturn\s+the\s+.+?\s+intent\s+into\s+a\s+clear\s+product\s+narrative\b",
        r"\bmake\s+.+?\s+readable\s+as\s+one\s+product\s+story\b",
        r"\bbefore\s+source\s+work\s+starts\b",
        r"\bbefore\s+implementation\s+begins\b",
        r"\bgenerated\s+from\s+the\s+accepted\s+greenfield\b",
        r"\bstart\s+with\s+the\s+.+?\s+first\s+workflow\b",
        r"(?<![-\w])first\s+workflow\b",
        r"\bworkflow\s+lead\b",
        r"\bworkflow\s+lead\s+and\s+beneficiary\b",
        r"\bperson\s+or\s+team\s+receiving\s+value\b",
        r"\bvisible\s+completion\b",
        r"\bproduct\s+promise\b",
        r"\brelease\s+claim\b",
        r"\bstate\s+record\b",
        r"\bevidence\s+packet\b",
        r"\bfixture-backed\s+inputs\b",
        r"\bdocumented\s+non-goals\b",
    )
]

_GENERIC_SYSTEM_NAME_KEYS = {
    "workflow service",
    "state store",
    "evidence review",
}

_SYSTEM_NAME_NOUNS = {
    "adapter",
    "adapters",
    "api",
    "apis",
    "client",
    "clients",
    "console",
    "consoles",
    "controller",
    "controllers",
    "coordinator",
    "coordinators",
    "dashboard",
    "dashboards",
    "engine",
    "engines",
    "flow",
    "flows",
    "gateway",
    "gateways",
    "harness",
    "harnesses",
    "integration",
    "integrations",
    "ledger",
    "ledgers",
    "manager",
    "managers",
    "module",
    "modules",
    "pipeline",
    "pipelines",
    "queue",
    "queues",
    "record",
    "records",
    "recorder",
    "recorders",
    "screen",
    "screens",
    "service",
    "services",
    "store",
    "stores",
    "surface",
    "surfaces",
    "tracker",
    "trackers",
    "view",
    "views",
    "workflow",
    "workflows",
}


def load_confirmed_intent_file(path: Path, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Load a host-visible Product Intent Confirmation from Markdown/text/JSON."""

    source = Path(path)
    if not source.is_file():
        raise ValueError(f"confirmed intent file was not found: {source}")
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"confirmed intent file is empty: {source}")
    if source.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"confirmed intent JSON is invalid: {exc}") from exc
        return normalize_confirmed_intent(payload, prompt=prompt, fallback_title=fallback_title)
    return parse_confirmed_intent_text(text, prompt=prompt, fallback_title=fallback_title)


def normalize_confirmed_intent(value: object, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Normalize JSON or already parsed confirmation data into the builder contract."""

    if isinstance(value, str):
        return parse_confirmed_intent_text(value, prompt=prompt, fallback_title=fallback_title)
    if not isinstance(value, Mapping):
        raise ValueError("confirmed intent must be Markdown text or a JSON object")
    payload = dict(value)
    title = _clean(payload.get("title") or payload.get("product_title") or fallback_title)
    component_rows = _role_or_system_rows(
        payload.get("component_responsibilities")
        or payload.get("component_rows")
        or payload.get("components")
        or payload.get("owned_capabilities")
    )
    result: dict[str, Any] = {
        "title": title,
        "prompt": _clean(payload.get("prompt") or prompt),
        "product_story": _clean(payload.get("product_story") or payload.get("story")),
        "state_object": _clean(payload.get("state_object") or payload.get("state_object_first_journey")),
        "first_path": _clean(payload.get("first_path") or payload.get("first_workflow")),
        "proof_boundary": _clean(payload.get("proof_boundary")),
        "problem": _clean(payload.get("problem") or payload.get("user_problem") or payload.get("user_problem_and_risk")),
        "customer": _clean(payload.get("customer")),
        "opportunity": _clean(payload.get("opportunity")),
        "product_view": _clean(payload.get("product_view")),
        "success_metrics": _strings(payload.get("success_metrics") or payload.get("proof_metrics")),
        "component_responsibilities": component_rows,
        "human_actors": _role_or_system_rows(payload.get("human_actors") or payload.get("actors")),
        "external_systems": _strings(payload.get("external_systems")),
        "internal_systems": [],
        "assumptions": _strings(payload.get("assumptions") or payload.get("critical_assumptions")),
        "ambiguities": _strings(
            payload.get("ambiguities") or payload.get("material_ambiguities") or payload.get("open_questions")
        ),
        "non_goals": _strings(payload.get("non_goals")),
    }
    result["internal_systems"] = _expand_internal_system_rows(
        _preferred_internal_rows(
            _role_or_system_rows(payload.get("internal_systems") or payload.get("internal_product_systems")),
            component_rows,
        ),
        context_text=_intent_context_text(result),
    )
    result = _complete_confirmed_intent_before_validation(result)
    _validate_confirmed_intent(result)
    return result


def structured_confirmed_intent_path(path: Path) -> Path:
    """Return the CLI-owned structured companion path for a confirmed intent file."""

    source = Path(path)
    if source.suffix.lower() == ".json":
        return source
    return source.with_suffix(".json")


def write_structured_confirmed_intent_file(path: Path, intent: Mapping[str, Any]) -> Path:
    """Persist the normalized confirmed intent beside the human Markdown record."""

    target = structured_confirmed_intent_path(path)
    if target == Path(path):
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    keys = (
        "title",
        "prompt",
        "product_story",
        "state_object",
        "first_path",
        "proof_boundary",
        "problem",
        "customer",
        "opportunity",
        "product_view",
        "success_metrics",
        "component_responsibilities",
        "human_actors",
        "external_systems",
        "internal_systems",
        "assumptions",
        "ambiguities",
        "non_goals",
    )
    payload = {key: intent.get(key) for key in keys if key in intent}
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _complete_confirmed_intent_before_validation(intent: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(intent)
    if _contains_meta_narration(result):
        return result
    if _contains_generic_system_scaffold(_strings(result.get("internal_systems"))):
        return result
    return complete_confirmed_intent(result)


def parse_confirmed_intent_text(text: str, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Parse the human Product Intent Confirmation that the host already showed."""

    sections = _sections(text)
    title = _title_from_text(text) or _title_from_sections(sections) or _title_from_preamble(sections) or fallback_title
    preamble_story = _preamble_story(sections, title)
    result: dict[str, Any] = {
        "title": _clean(title),
        "prompt": _clean(prompt),
        "product_story": _section_text(sections, "product_story") or preamble_story,
        "state_object": _section_text(sections, "state_object"),
        "first_path": _section_text(sections, "first_path"),
        "proof_boundary": _section_text(sections, "proof_boundary"),
        "problem": _section_text(sections, "problem"),
        "customer": _section_text(sections, "customer"),
        "opportunity": _section_text(sections, "opportunity"),
        "product_view": _section_text(sections, "product_view"),
        "success_metrics": _section_list(sections, "success_metrics"),
        "component_responsibilities": _section_list(sections, "component_responsibilities"),
        "human_actors": _section_list(sections, "human_actors"),
        "external_systems": _section_list(sections, "external_systems"),
        "internal_systems": [],
        "assumptions": _section_list(sections, "assumptions"),
        "ambiguities": _section_list(sections, "ambiguities"),
        "non_goals": _section_list(sections, "non_goals"),
    }
    result["internal_systems"] = _internal_system_rows(sections, context_text=_intent_context_text(result))
    result = _complete_confirmed_intent_before_validation(result)
    _validate_confirmed_intent(result)
    return result


def confirmed_intent_summary(intent: Mapping[str, Any] | None, key: str, fallback: str) -> str:
    if not isinstance(intent, Mapping):
        return fallback
    value = _clean(intent.get(key))
    return value or fallback


def confirmed_intent_list(intent: Mapping[str, Any] | None, key: str) -> list[str]:
    if not isinstance(intent, Mapping):
        return []
    return _strings(intent.get(key))


def confirmed_system_name(value: str) -> str:
    raw = re.split(r"\s+[—-]\s+|\s*:\s*", _clean(value), maxsplit=1)[0].strip()
    return _clean(raw) or "Product System"


def confirmed_system_description(value: str) -> str:
    parts = re.split(r"\s+[—-]\s+|\s*:\s*", _clean(value), maxsplit=1)
    if len(parts) > 1:
        return _clean(parts[1])
    return _clean(value)


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "preamble"
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        heading = _heading_key(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        if not line.strip() and current == "preamble":
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _heading_key(line: str) -> str:
    text = line.strip()
    if not text:
        return ""
    if text.startswith("#"):
        return _classify_heading(text.lstrip("#").strip())
    if text.endswith(":") and len(text.split()) <= 8:
        return _classify_heading(text[:-1].strip())
    return _classify_heading(text) if _looks_like_plain_heading(text) else ""


def _looks_like_plain_heading(text: str) -> bool:
    lowered = _normalize_heading(text)
    known = {
        "product story",
        "product title",
        "state object",
        "first complete path",
        "first path",
        "user problem",
        "user problem and risk",
        "problem",
        "customer",
        "opportunity",
        "product view",
        "success metrics",
        "proof metrics",
        "state object that changes through the first journey",
        "first complete path odylith should prove before broader scope",
        "first complete path the product should prove before broader scope",
        "human actors",
        "external systems",
        "external systems not owned by this product",
        "internal systems",
        "internal product systems",
        "assumptions",
        "critical assumptions",
        "ambiguities that would change the first path",
        "material ambiguities",
        "ambiguities",
        "open questions",
        "proof boundary",
        "next step",
        "non goals",
        "non-goals",
        "systems",
        "component responsibilities",
        "owned capabilities",
    }
    return lowered in known


def _classify_heading(value: str) -> str:
    normalized = _normalize_heading(value)
    if not normalized:
        return ""
    if "product intent confirmation" in normalized:
        return "title"
    if normalized in {"product title", "title"}:
        return "title"
    if "product story" in normalized:
        return "product_story"
    if normalized in {"user problem", "user problem and risk", "problem"}:
        return "problem"
    if normalized == "customer":
        return "customer"
    if normalized == "opportunity":
        return "opportunity"
    if normalized == "product view":
        return "product_view"
    if normalized in {"success metrics", "proof metrics"}:
        return "success_metrics"
    if "human actor" in normalized or normalized == "actors":
        return "human_actors"
    if normalized == "systems":
        return "systems"
    if "component responsibilit" in normalized or "owned capabilit" in normalized:
        return "component_responsibilities"
    if normalized.startswith("internal ") and (
        "internal product system" in normalized or "internal system" in normalized
    ):
        return "internal_systems"
    if normalized.startswith("external ") and "external system" in normalized:
        return "external_systems"
    if "internal product system" in normalized or "internal system" in normalized:
        return "internal_systems"
    if "external system" in normalized:
        return "external_systems"
    if "critical assumption" in normalized or normalized == "assumptions":
        return "assumptions"
    if "ambiguities" in normalized or "open question" in normalized:
        return "ambiguities"
    if "state object" in normalized:
        return "state_object"
    if "first complete path" in normalized or "first workflow" in normalized or "first path" in normalized:
        return "first_path"
    if "proof boundary" in normalized:
        return "proof_boundary"
    if normalized == "next step":
        return "next_step"
    if "non goal" in normalized or "non-goal" in normalized:
        return "non_goals"
    return ""


def _normalize_heading(value: str) -> str:
    text = re.sub(r"[*_`]+", " ", str(value or "")).strip().casefold()
    text = re.sub(r"[–—-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_from_text(text: str) -> str:
    for raw_line in str(text or "").splitlines():
        line = _clean(raw_line.lstrip("#").strip())
        if not line:
            continue
        match = re.match(r"(.+?)\s+[—-]\s+Product Intent Confirmation$", line)
        if match:
            return _clean(match.group(1))
        if "product intent confirmation" in line.casefold():
            candidate = _clean(re.sub(r"product intent confirmation", "", line, flags=re.IGNORECASE))
            if candidate:
                return candidate
    for raw_line in str(text or "").splitlines():
        raw = str(raw_line or "").strip()
        if not raw.startswith("#"):
            continue
        line = _clean(raw.lstrip("#").strip())
        if line and not _classify_heading(line):
            return line
    return ""


def _title_from_sections(sections: Mapping[str, list[str]]) -> str:
    for raw_line in sections.get("title", []):
        line = _clean(str(raw_line).lstrip("#").strip())
        if not line or line.casefold() == "product title:":
            continue
        if line.casefold().startswith("product title:"):
            line = _clean(line.split(":", 1)[1])
        if line and "product intent confirmation" not in line.casefold():
            return line
    return ""


def _title_from_preamble(sections: Mapping[str, list[str]]) -> str:
    lines = [
        _clean(str(raw_line).lstrip("#").strip())
        for raw_line in sections.get("preamble", [])
        if _clean(raw_line)
    ]
    for line in lines[:3]:
        if "product intent confirmation" in line.casefold():
            continue
        if _looks_like_bare_title(line):
            return line
    return ""


def _looks_like_bare_title(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or _classify_heading(text):
        return False
    if text[-1:] in ".!?":
        return False
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)
    if not 1 <= len(words) <= 10:
        return False
    lowered = text.casefold()
    if re.search(
        r"\b(?:wants?|needs?|helps?|uses?|creates?|submits?|reviews?|records?|tracks?|decides?|should|must|can|will)\b",
        lowered,
    ):
        return False
    return True


def _section_text(sections: Mapping[str, list[str]], key: str) -> str:
    lines = sections.get(key, [])
    return _clean(" ".join(line.strip("-* \t") for line in lines if line.strip()))


def _preamble_story(sections: Mapping[str, list[str]], title: str) -> str:
    lines: list[str] = []
    title_text = _clean(title).casefold()
    for raw_line in sections.get("preamble", []):
        line = _clean(str(raw_line or "").lstrip("#").strip())
        if not line:
            continue
        if title_text and line.casefold() == title_text:
            continue
        if _classify_heading(line):
            continue
        lines.append(line)
    return _clean(" ".join(lines))


def _section_list(sections: Mapping[str, list[str]], key: str) -> list[str]:
    values: list[str] = []
    for raw_line in sections.get(key, []):
        text = raw_line.strip()
        if not text:
            continue
        item = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", text).strip()
        if item:
            values.append(_clean(item))
    if values:
        return values
    paragraph = _section_text(sections, key)
    return [paragraph] if paragraph else []


def _internal_system_rows(sections: Mapping[str, list[str]], *, context_text: str = "") -> list[str]:
    rows = _section_list(sections, "internal_systems")
    component_rows = _section_list(sections, "component_responsibilities")
    rows = _preferred_internal_rows(rows, component_rows)
    if not rows:
        rows = component_rows
    else:
        expanded = _expand_internal_system_rows(rows, context_text=context_text)
        if component_rows and any(not _has_meaningful_system_description(row) for row in expanded):
            return _expand_internal_system_rows(component_rows, context_text=context_text)
        return expanded
    if not rows:
        rows = _combined_system_rows(sections, "internal")
    return _expand_internal_system_rows(rows, context_text=context_text)


def _preferred_internal_rows(rows: list[str], component_rows: list[str]) -> list[str]:
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


def _row_detail_score(row: str) -> int:
    text = _clean(row)
    name = confirmed_system_name(text)
    description = confirmed_system_description(text)
    score = _word_count(description)
    if name and name != description:
        score += 8
    if re.search(
        r"\b(?:receives?|produces?|records?|stores?|tracks?|links?|derives?|controls?|reviews?|"
        r"explains?|validates?|normalizes?|preserves?|routes?|captures?)\b",
        description,
        re.IGNORECASE,
    ):
        score += 6
    if re.search(r"\b(?:evidence|state|source|actor|decision|review|failure|blocked|history)\b", description, re.IGNORECASE):
        score += 4
    return score


def _combined_system_rows(sections: Mapping[str, list[str]], target: str) -> list[str]:
    text = _section_text(sections, "systems")
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
    return _role_or_system_rows(match.group(1))


def _expand_internal_system_rows(rows: list[str], *, context_text: str = "") -> list[str]:
    cleaned = [_clean(row) for row in rows if _clean(row)]
    sentence_rows = _system_sentence_rows(" ".join(cleaned), context_text=context_text)
    if len(cleaned) == 1 and len(sentence_rows) >= 2:
        return sentence_rows
    if len(cleaned) != 1:
        expanded: list[str] = []
        for row in cleaned:
            expanded.append(
                _system_sentence_row(row, context_text=context_text)
                or _concise_system_row(row, context_text=context_text)
                or row
            )
        return expanded
    paragraph = cleaned[0]
    candidates = _extract_internal_system_candidates(paragraph)
    if len(candidates) < 2:
        return cleaned
    rationale = _internal_system_rationale(paragraph)
    expanded: list[str] = []
    for candidate in candidates:
        description = _expanded_system_description(candidate, context_text=context_text, rationale=rationale)
        if rationale:
            description = f"{description}. Rationale: {rationale.rstrip('.')}"
        expanded.append(f"{_title_case_phrase(candidate)} — {description}")
    return expanded


def _intent_context_text(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("product_story")),
        _clean(intent.get("problem")),
        _clean(intent.get("customer")),
        _clean(intent.get("opportunity")),
        _clean(intent.get("product_view")),
        _clean(intent.get("first_path")),
        _clean(intent.get("state_object")),
        _clean(intent.get("proof_boundary")),
        ". ".join(_strings(intent.get("success_metrics"))),
        ". ".join(_strings(intent.get("component_responsibilities"))),
        ". ".join(_strings(intent.get("human_actors"))),
        ". ".join(_strings(intent.get("external_systems"))),
        ". ".join(_strings(intent.get("assumptions"))),
        ". ".join(_strings(intent.get("non_goals"))),
    ]
    return _clean(". ".join(part.strip(" .") for part in parts if part))


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
    clipped = text[: max(0, limit)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    words = clipped.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "to", "with", "for", "from", "of", "the", "a", "an"}:
        words.pop()
    return " ".join(words).rstrip(" ,;:")


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


def _role_or_system_rows(value: object) -> list[str]:
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
        if _usable_internal_system_candidate(name) and _word_count(body) >= 4:
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
    return _format_system_row(name, _concise_system_description(name, context_text=context_text), context_text="")


def _concise_system_description(name: str, *, context_text: str) -> str:
    subject = _clean(name).casefold()
    return (
        f"owns {subject} state, required inputs, rejected or blocked cases, evidence links, and handoff boundaries "
        "for the confirmed first path"
    )


def _format_system_row(name: str, body: str, *, context_text: str = "") -> str:
    return f"{_title_case_phrase(name)} — {_contextualized_system_body(name=name, body=body, context_text=context_text)}"


def _contextualized_system_body(*, name: str, body: str, context_text: str) -> str:
    description = _clean(body).strip(" .")
    if _word_count(description) >= 6:
        return description
    clause = _best_context_clause(f"{name} {description}", context_text) or _best_context_clause(description, context_text)
    if clause and _has_semantic_overlap(description, clause, minimum=2):
        clause = _brief_clause(clause, limit=120)
        return f"{description}. Related path: {clause}"
    return f"{description} while preserving traceable state, evidence, and handoff"


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
        if body:
            return candidate, body
    return None


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


def _internal_system_rationale(paragraph: str) -> str:
    text = _clean(paragraph)
    match = re.search(r"\bmatter\s+because\s+(.+?)(?:[.!?]|$)", text, re.IGNORECASE)
    if match:
        return _clean(match.group(1))
    match = re.search(r"\bmust\s+(.+?)(?:[.!?]|$)", text, re.IGNORECASE)
    if match:
        return "must " + _clean(match.group(1))
    return "keeps the accepted first path, product state, evidence, and proof boundary connected"


def _title_case_phrase(value: str) -> str:
    words = []
    for word in _clean(value).split():
        if word.isupper():
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def _validate_confirmed_intent(intent: Mapping[str, Any]) -> None:
    missing: list[str] = []
    for key, minimum in FIELD_MIN_WORDS.items():
        if _word_count(_clean(intent.get(key))) < minimum:
            missing.append(key)
    actor_rows = _strings(intent.get("human_actors"))
    if not actor_rows:
        missing.append("human_actors")
    elif any(_word_count(row) < LIST_ROW_MIN_WORDS for row in actor_rows):
        missing.append("human_actors")
    system_rows = _strings(intent.get("internal_systems"))
    if len(system_rows) < 2:
        missing.append("internal_systems")
    elif any(not _has_meaningful_system_description(row) for row in system_rows):
        missing.append("internal_systems")
    if _contains_meta_narration(intent):
        missing.append("product_narrative")
    if _contains_generic_system_scaffold(system_rows):
        missing.append("internal_systems")
    missing.extend(_qualitative_intent_gaps(intent))
    if missing:
        formatted = ", ".join(dict.fromkeys(missing))
        raise ValueError(
            "confirmed greenfield create needs the operator-confirmed Product Intent Confirmation; "
            f"missing or too thin: {formatted}. Write the visible confirmation to a Markdown file "
            "and pass it with --intent-file."
        )


def _qualitative_intent_gaps(intent: Mapping[str, Any]) -> list[str]:
    gaps: list[str] = []
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    actors = " ".join(_strings(intent.get("human_actors")))
    systems = " ".join(_strings(intent.get("internal_systems")))
    context = " ".join(part for part in (story, state, actors, systems, proof) if part)

    if story and not (
        _has_meaningful_story_shape(story) and _has_semantic_overlap(story, f"{actors} {systems} {state}", minimum=1)
    ):
        gaps.append("product_story")
    if state and not (_has_meaningful_sentences(state, minimum=1) and _has_progression_or_outcome(state)):
        gaps.append("state_object")
    if path and not (_has_progression_or_outcome(path) and _has_semantic_overlap(path, context, minimum=2)):
        gaps.append("first_path")
    if proof and not (_has_progression_or_outcome(proof) and _has_semantic_overlap(proof, f"{story} {state} {path} {systems}", minimum=1)):
        gaps.append("proof_boundary")
    if actors and not _has_semantic_overlap(actors, f"{story} {path}", minimum=1):
        gaps.append("human_actors")
    if systems and not _has_semantic_overlap(systems, f"{story} {state} {path} {proof}", minimum=2):
        gaps.append("internal_systems")
    return gaps


def _has_meaningful_system_description(row: str) -> bool:
    name = confirmed_system_name(row)
    description = confirmed_system_description(row)
    if not name or name == description:
        return False
    return _word_count(description) >= SYSTEM_ROW_MIN_WORDS


def _contains_meta_narration(intent: Mapping[str, Any]) -> bool:
    text = " ".join(
        [
            _clean(intent.get("product_story")),
            _clean(intent.get("first_path")),
            _clean(intent.get("proof_boundary")),
            " ".join(_strings(intent.get("human_actors"))),
            " ".join(_strings(intent.get("internal_systems"))),
        ]
    )
    return any(pattern.search(text) for pattern in _META_NARRATION_PATTERNS)


def _contains_generic_system_scaffold(system_rows: list[str]) -> bool:
    keys = {_system_name_key(confirmed_system_name(row)) for row in system_rows}
    keys.discard("")
    return _GENERIC_SYSTEM_NAME_KEYS.issubset(keys)


def _system_name_key(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s]+", " ", str(value or "").casefold())
    return re.sub(r"\s+", " ", text).strip()


def _has_meaningful_sentences(text: str, *, minimum: int) -> bool:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", _clean(text)) if _word_count(part) >= 8]
    return len(sentences) >= minimum or _word_count(_clean(text)) >= minimum * 18


def _has_meaningful_story_shape(text: str) -> bool:
    cleaned = _clean(text)
    if _has_meaningful_sentences(cleaned, minimum=2):
        return True
    if not _has_meaningful_sentences(cleaned, minimum=1):
        return False
    if _has_progression_or_outcome(cleaned):
        return True
    return bool(
        re.search(
            r"\b(?:need|needs|want|wants|help|helps|manage|manages|track|tracks|record|records|show|shows|"
            r"understand|decide|trust|review|route|collect|reduce|avoid|prevent|resolve|coordinate)\b",
            cleaned,
            re.IGNORECASE,
        )
    )


def _has_progression_or_outcome(text: str) -> bool:
    cleaned = _clean(text)
    if len(re.findall(r"\b(?:starts?|ends?|then|after|before|when|until|from|to|through|with|without)\b", cleaned, re.IGNORECASE)) >= 2:
        return True
    if len(re.findall(r"[,;:]", cleaned)) >= 2:
        return True
    return _word_count(cleaned) >= 24 and bool(re.search(r"\b(?:result|outcome|proof|evidence|state|status|decision|completed|blocked|accepted|rejected|safe|unsafe)\b", cleaned, re.IGNORECASE))


def _has_semantic_overlap(left: str, right: str, *, minimum: int) -> bool:
    left_terms = _semantic_terms(left)
    right_terms = _semantic_terms(right)
    return len(left_terms & right_terms) >= minimum


_TERM_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "cost",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "low",
    "of",
    "on",
    "or",
    "product",
    "project",
    "release",
    "should",
    "small",
    "system",
    "systems",
    "that",
    "the",
    "then",
    "this",
    "through",
    "to",
    "with",
    "without",
}


def _semantic_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(text).casefold()):
        token = raw.strip("-_")
        if len(token) < 3 or token in _TERM_STOPWORDS:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = f"{token[:-3]}y"
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            token = token[:-1]
        if token not in _TERM_STOPWORDS:
            terms.add(token)
    return terms


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = _clean(value)
        return [cleaned] if cleaned else []
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return []
    return [_clean(item) for item in value if _clean(item)]


def _word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", value))


def _clean(value: object) -> str:
    text = str(value or "").strip()
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "confirmed_intent_list",
    "confirmed_intent_summary",
    "confirmed_system_description",
    "confirmed_system_name",
    "load_confirmed_intent_file",
    "normalize_confirmed_intent",
    "parse_confirmed_intent_text",
    "structured_confirmed_intent_path",
    "write_structured_confirmed_intent_file",
]
