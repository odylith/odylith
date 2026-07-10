"""Document-context extraction for confirmed greenfield Product Intent."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    classify_confirmed_intent_heading,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_heading_key,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_inline_heading_value,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    is_confirmed_intent_supporting_section,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import FIELD_MIN_WORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import has_progression_or_outcome
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_extraction import (
    looks_like_confirmation_instruction,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_extraction import (
    title_from_product_intent_line,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


def title_from_text(text: str) -> str:
    for raw_line in str(text or "").splitlines():
        raw = str(raw_line or "").strip()
        if not raw.startswith("#"):
            continue
        line = _clean(raw.lstrip("#").strip())
        candidate = title_from_product_intent_line(line) or _title_from_export_line(line)
        if candidate:
            return candidate
        if line and not classify_confirmed_intent_heading(line):
            return line
    for raw_line in str(text or "").splitlines():
        if looks_like_confirmation_instruction(raw_line):
            continue
        line = _clean(raw_line.lstrip("#").strip())
        if not line:
            continue
        inline_heading = confirmed_intent_inline_heading_value(line)
        if inline_heading:
            heading, value = inline_heading
            if heading == "title" and value:
                return value
            continue
        for candidate in (
            title_from_product_intent_line(line),
            _title_from_export_line(line),
            _title_from_is_for_line(line),
        ):
            if candidate:
                return candidate
        if _looks_like_bare_title(line):
            return line
    return ""


def title_from_sections(sections: Mapping[str, list[str]]) -> str:
    for raw_line in sections.get("title", []):
        line = _clean(str(raw_line).lstrip("#").strip())
        if not line or line.casefold() == "product title:":
            continue
        if line.casefold().startswith("product title:"):
            line = _clean(line.split(":", 1)[1])
        if line and "product intent confirmation" not in line.casefold():
            return line
    return ""


def title_from_preamble(sections: Mapping[str, list[str]]) -> str:
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


def preamble_story(sections: Mapping[str, list[str]], title: str) -> str:
    lines: list[str] = []
    title_text = _clean(title).casefold()
    for raw_line in sections.get("preamble", []):
        line = _clean(str(raw_line or "").lstrip("#").strip())
        if not line or (title_text and line.casefold() == title_text):
            continue
        if classify_confirmed_intent_heading(line) or looks_like_operator_instruction_line(line):
            continue
        lines.append(line)
    return _clean(" ".join(lines))


def product_context_paragraphs(
    text: str,
    sections: Mapping[str, list[str]],
    title: str,
) -> list[str]:
    if not has_explicit_section_boundaries(sections):
        return _preamble_paragraphs(text, title)
    paragraphs: list[str] = []
    if sections.get("preamble"):
        paragraphs.extend(_preamble_paragraphs(_raw_preamble_text(text), title))
    rows: list[str] = []
    for key, lines in sections.items():
        if key == "preamble" or not is_confirmed_intent_supporting_section(key):
            continue
        rows.extend(lines)
        rows.append("")
    paragraphs.extend(_paragraphs_from_lines(rows, title, keep_list_items=True))
    return _expand_narrative_cue_paragraphs(paragraphs)


def derived_state_paragraph(paragraphs: Sequence[str]) -> str:
    for paragraph in paragraphs:
        if _looks_like_state_paragraph(paragraph) and word_count(paragraph) >= FIELD_MIN_WORDS["state_object"]:
            return paragraph
    return ""


def derived_first_path_paragraph(paragraphs: Sequence[str]) -> str:
    scored: list[tuple[int, int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        if word_count(paragraph) < FIELD_MIN_WORDS["first_path"]:
            continue
        if _looks_like_proof_or_scope_paragraph(paragraph) or _looks_like_state_paragraph(paragraph):
            continue
        if not _has_material_first_path_action(paragraph):
            continue
        model = first_path_model(paragraph)
        action_count = sum(1 for step in model.steps if has_progression_or_outcome(step))
        score = action_count * 3
        if model.visible_outcome:
            score += 5
        if re.search(
            r"\b(?:opens?|starts?|adds?|enters?|logs?|records?|submits?|saves?|corrects?)\b",
            paragraph,
            re.IGNORECASE,
        ):
            score += 2
        if re.search(r"\b(?:shows?|displays?|returns?|receives?|sees?|views?|reviews?)\b", paragraph, re.IGNORECASE):
            score += 2
        if _looks_like_explicit_first_path_paragraph(paragraph):
            score += 8
        if _looks_like_product_story_paragraph(paragraph):
            score -= 6
        if score >= 7:
            scored.append((score, -index, paragraph))
    scored.sort(reverse=True)
    return scored[0][2] if scored else ""


def derived_proof_boundary_paragraph(paragraphs: Sequence[str]) -> str:
    for paragraph in paragraphs:
        if word_count(paragraph) >= FIELD_MIN_WORDS["proof_boundary"] and _looks_like_proof_or_scope_paragraph(
            paragraph
        ):
            return paragraph
    return ""


def derived_product_story(
    paragraphs: Sequence[str],
    *,
    state: str,
    first_path: str,
    proof_boundary: str = "",
) -> str:
    story_rows: list[str] = []
    state_key = _clean(state).casefold()
    path_key = _clean(first_path).casefold()
    proof_key = _clean(proof_boundary).casefold()
    for paragraph in paragraphs:
        lowered = paragraph.casefold()
        if lowered in {state_key, path_key, proof_key}:
            continue
        if _looks_like_state_paragraph(paragraph) or _looks_like_proof_or_scope_paragraph(paragraph):
            continue
        if word_count(paragraph) >= 12:
            story_rows.append(paragraph)
        if len(story_rows) >= 2:
            break
    return _clean(" ".join(story_rows))


def strip_list_marker(value: object) -> str:
    return re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", str(value or "")).strip()


def looks_like_operator_instruction_line(value: str) -> bool:
    text = _clean(value).strip()
    if not text:
        return False
    lowered = text.casefold()
    exact_or_prefixes = (
        "confirmed cli after confirmation",
        "confirm this interpretation",
        "edit any section",
        "host reasoning task",
        "no files changed",
        "reject it to stop",
        "source posture:",
        "visible format contract",
        "write in chat",
        "write this same visible",
    )
    if lowered.startswith(exact_or_prefixes):
        return True
    blocked_fragments = (
        ".odylith/runtime/greenfield/confirmed-intent",
        "--intent-file",
        "--repo-root",
        "after confirmation should",
        "child boundaries after confirmation",
        "coding should start",
        "confirm: write",
        "od ylith greenfield create",
        "odylith greenfield create",
        "technical plan and proof target",
    )
    return any(fragment in lowered for fragment in blocked_fragments)


def _looks_like_bare_title(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or classify_confirmed_intent_heading(text) or text[-1:] in ".!?":
        return False
    words = label_terms(text)
    if not 1 <= len(words) <= 10:
        return False
    title_like_words = [word for word in text.split() if word.strip("()[]{}.,:;")]
    title_like_count = sum(
        1
        for word in title_like_words
        if word.strip("()[]{}.,:;")[:1].isupper() or word.strip("()[]{}.,:;").isupper()
    )
    title_like = bool(title_like_words) and title_like_count >= max(1, len(title_like_words) - 1)
    if not title_like and re.search(
        r"\b(?:wants?|needs?|helps?|uses?|creates?|submits?|reviews?|records?|tracks?|decides?|should|must|can|will)\b",
        text,
        re.IGNORECASE,
    ):
        return False
    return True


def _title_from_is_for_line(value: str) -> str:
    text = _clean(value).strip()
    match = re.match(r"^(?P<title>[A-Z][A-Za-z0-9&/:' -]{3,90}?)\s+is\s+for\s+", text)
    if not match:
        return ""
    candidate = _clean(match.group("title")).strip(" .")
    words = label_terms(candidate)
    if not 2 <= len(words) <= 10:
        return ""
    if not any(word[:1].isupper() or word.isupper() for word in candidate.split()):
        return ""
    return candidate


def _title_from_export_line(value: str) -> str:
    text = _clean(value).strip()
    match = re.match(
        r"^(?:deck\s+export|slide\s+deck|presentation|slides|document|source\s+document)\s+[\u2014-]\s+(?P<title>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.match(
            r"^(?:rfp\s+attachment\s+excerpt\s+for|attachment\s+excerpt\s+for|source\s+excerpt\s+for)\s+(?P<title>.+)$",
            text,
            flags=re.IGNORECASE,
        )
    if not match:
        return ""
    candidate = _clean(match.group("title")).strip(" .")
    return candidate if _looks_like_bare_title(candidate) else ""


def _raw_preamble_text(text: str) -> str:
    return re.split(r"(?m)^#{2,6}\s+", str(text or ""), maxsplit=1)[0]


def has_explicit_section_boundaries(sections: Mapping[str, list[str]]) -> bool:
    return any(key != "preamble" for key in sections)


def _preamble_paragraphs(text: str, title: str) -> list[str]:
    rows: list[str] = []
    for raw in re.split(r"\n\s*\n+", str(text or "")):
        row_lines: list[str] = []
        for line in raw.splitlines():
            cleaned = _clean(line.lstrip("#").strip())
            if not cleaned or confirmed_intent_heading_key(line):
                continue
            if re.match(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", line):
                continue
            row_lines.append(cleaned)
        rows.append(" ".join(row_lines))
        rows.append("")
    return _expand_narrative_cue_paragraphs(_paragraphs_from_lines(rows, title, keep_list_items=False))


def _expand_narrative_cue_paragraphs(paragraphs: Sequence[str]) -> list[str]:
    expanded: list[str] = []
    for paragraph in paragraphs:
        split = _narrative_cue_paragraphs(paragraph)
        expanded.extend(split or [paragraph])
    return expanded


def _narrative_cue_paragraphs(value: str) -> list[str]:
    text = _clean(value).strip(" .")
    if word_count(text) < 35:
        return []
    state_match = re.search(
        r"\b(?:the\s+main\s+thing\s+(?:the\s+)?product\s+keeps\s+is\s+this|"
        r"core\s+record|state\s+object|main\s+record|central\s+record)\s*:?\s*",
        text,
        flags=re.IGNORECASE,
    )
    first_match = re.search(
        r"\b(?:for\s+the\s+first\s+release|first\s+complete\s+path|first\s+path|first\s+workflow|"
        r"first\s+journey|first\s+version)\s*(?:,|:|\bis\b)?\s*",
        text,
        flags=re.IGNORECASE,
    )
    proof_match = re.search(
        r"\b(?:proof\s+is\s+intentionally\s+narrow|proof\s+boundary|done\s+when|acceptance)\s*:?\s*"
        r"|\brelease\s+[A-Za-z0-9_.-]+\s+succeeds\s+when\b",
        text,
        flags=re.IGNORECASE,
    )
    if not (state_match and first_match and proof_match):
        return []
    if not (state_match.start() < first_match.start() < proof_match.start()):
        return []
    story = text[: state_match.start()].strip(" .")
    state = text[state_match.end() : first_match.start()].strip(" .")
    first_path = text[first_match.end() : proof_match.start()].strip(" .")
    proof_start = proof_match.start() if text[proof_match.start() :].casefold().startswith("release ") else proof_match.end()
    proof = text[proof_start:].strip(" .")
    proof = re.split(
        r"\b(?:the\s+user\s+can\s+edit|these\s+are\s+the\s+product\s+facts|implementation\s+prompt|next\s+steps?)\b",
        proof,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .")
    rows = [_clean(row).strip(" .") for row in (story, state, first_path, proof)]
    rows = [row for row in rows if row and word_count(row) >= 6]
    return rows if len(rows) >= 3 else []


def _paragraphs_from_lines(lines: Sequence[str], title: str, *, keep_list_items: bool) -> list[str]:
    title_text = _clean(title).casefold()
    paragraphs: list[str] = []
    current: list[str] = []
    for raw_line in lines:
        raw_text = str(raw_line or "")
        cleaned = _clean(raw_text.lstrip("#").strip())
        if not cleaned:
            _append_context_paragraph(paragraphs, current, title_text=title_text)
            current = []
            continue
        if title_text and cleaned.casefold() == title_text:
            continue
        if confirmed_intent_heading_key(raw_text):
            continue
        list_item = re.match(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", raw_text)
        if list_item and not keep_list_items:
            continue
        cleaned = strip_list_marker(cleaned)
        if looks_like_operator_instruction_line(cleaned):
            continue
        if list_item:
            _append_context_paragraph(paragraphs, current, title_text=title_text)
            current = []
            _append_context_paragraph(paragraphs, [cleaned], title_text=title_text)
            continue
        current.append(cleaned)
    _append_context_paragraph(paragraphs, current, title_text=title_text)
    return paragraphs


def _append_context_paragraph(paragraphs: list[str], lines: Sequence[str], *, title_text: str) -> None:
    paragraph = _clean(" ".join(line for line in lines if line))
    if not paragraph or (title_text and paragraph.casefold() == title_text):
        return
    if not looks_like_operator_instruction_line(paragraph):
        paragraphs.append(paragraph)


def _looks_like_explicit_first_path_paragraph(value: str) -> bool:
    text = _clean(value)
    return bool(
        re.match(
            r"^(?:the\s+)?(?:first\s+complete\s+path|first\s+path|first\s+journey|first\s+version\s+path)\b",
            text,
            re.IGNORECASE,
        )
        or re.match(
            r"^(?:a|an|the)\s+[^.]{1,80}\b(?:opens?|starts?|adds?|enters?|logs?|records?|submits?|chooses?|selects?|describes?)\b",
            text,
            re.IGNORECASE,
        )
    )


def _looks_like_product_story_paragraph(value: str) -> bool:
    text = _clean(value)
    return bool(
        re.match(
            r"^[^.]{1,80}\bneed(?:s)?\b[^.]{0,120}\b(?:way|place|product|tool|experience)\b",
            text,
            re.IGNORECASE,
        )
        or re.match(
            r"^[^.]{1,80}\b(?:want|wants)\b[^.]{0,120}\b(?:way|place|product|tool|experience)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:helps?|gives?)\s+[^.]{1,80}\b(?:receive|understand|avoid|decide|keep)\b",
            text,
            re.IGNORECASE,
        )
    )


def _looks_like_proof_or_scope_paragraph(value: str) -> bool:
    text = _clean(value)
    return bool(
        re.match(
            r"^(?:the\s+)?(?:first\s+)?release(?:\s+[0-9.]+)?\s+"
            r"(?:(?:is|works?|succeeds?|passes?|ready)\b|(?:is\s+)?(?:good\s+enough|proven|done|complete)\b)",
            text,
            re.IGNORECASE,
        )
        or re.match(r"^(?:release\s+[0-9.]+\s+)?(?:succeeds?|is\s+proven|proven|proof)\b", text, re.IGNORECASE)
        or re.match(r"^(?:a|an|the)\s+[^.]{1,80}\b(?:can|must|should)\s+reproduce\b", text, re.IGNORECASE)
        or re.search(r"\breproduce\s+(?:the\s+)?(?:accepted|blocked|rejected|same)\b", text, re.IGNORECASE)
        or re.search(
            r"\b(?:first\s+release|release\s+[0-9.]+)\s+(?:is\s+)?(?:proven|good\s+enough|ready|succeeds?|works?)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(r"\b(?:out\s+of\s+scope|deferred|not\s+included|non[- ]goals?)\b", text, re.IGNORECASE)
    )


def _looks_like_state_paragraph(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    return bool(
        re.search(
            r"\b(?:central|core|main|primary)\s+(?:object|state)\b"
            r"|\b(?:case|decision|entity|history|item|ledger|object|package|plan|profile|record|request|review|snapshot|state|ticket)\s+"
            r"(?:is|records?|keeps?|carries?|tracks?|stores?|maintains?)\b"
            r"|\bworkflow\s+where\s+[^.]{1,120}\brecords?\b"
            r"|\b(?:the\s+)?(?:product|system|application|app)\s+(?:keeps?|records?|stores?|tracks?|maintains?|captures?)\s+"
            r"(?:a|an|the)\s+",
            text,
            flags=re.IGNORECASE,
        )
    )


def _has_material_first_path_action(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:adds?|chooses?|clicks?|corrects?|creates?|describes?|edits?|enters?|fills?|imports?|logs?|"
            r"opens?|records?|saves?|selects?|starts?|submits?|uploads?)\b",
            _clean(value),
            flags=re.IGNORECASE,
        )
    )


def _clean(value: object) -> str:
    return clean_markdown_text(value)


__all__ = [
    "derived_first_path_paragraph",
    "derived_product_story",
    "derived_proof_boundary_paragraph",
    "derived_state_paragraph",
    "looks_like_operator_instruction_line",
    "preamble_story",
    "product_context_paragraphs",
    "strip_list_marker",
    "title_from_preamble",
    "title_from_sections",
    "title_from_text",
]
