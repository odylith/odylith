"""Separate operator product evidence from host instructions and source metadata."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import is_contextual_gerund_phrase
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


REQUEST_COMMAND_WORDS = frozenset(
    {
        "build",
        "create",
        "design",
        "draft",
        "generate",
        "make",
        "plan",
        "propose",
        "scaffold",
        "write",
    }
)
_ORIGINAL_INTENT_BOUNDARY_HEADINGS = frozenset(
    {
        "next step",
        "confirmed cli after confirmation",
        "visible format contract",
        "write in chat",
        "do not",
    }
)
_SOURCE_METADATA_LABEL_RE = re.compile(
    r"\b(?:source\s+evidence|source\s+repository|repository\s+description)\s*(?::|-)\s*",
    flags=re.IGNORECASE,
)
_SOURCE_METADATA_CLAUSE_RE = re.compile(
    r"^(?:source\s+evidence|source\s+repository|repository\s+description)\s*(?::|-)\s*",
    flags=re.IGNORECASE,
)
_EXPLICIT_INTENT_LABEL_RE = re.compile(
    r"\b(?:user|product)\s+intent\s*(?::|-)\s*",
    flags=re.IGNORECASE,
)
_INLINE_EXPLICIT_INTENT_LABEL_RE = re.compile(
    r"(?:--\s*)?\b(?:user|product)\s+intent\s*(?::|-)\s*",
    flags=re.IGNORECASE,
)
_SOURCE_METADATA_BOUNDARY_PUNCTUATION = (".", "!", "?", "-", ";", ":", ",")
_SOURCE_EVIDENCE_SECTION_HEADINGS = frozenset(
    {
        "source evidence",
        "source repository",
        "repository description",
    }
)
_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}(?:\s+|$)")
_DECLARATION_COPULA_RE = re.compile(r"\b(?:is|are)\b", flags=re.IGNORECASE)
_SUBJECT_CONJUNCTION_RE = re.compile(r"\s*(?:,|\band\b|\bor\b)\s*", flags=re.IGNORECASE)
_CONFIRMATION_EVIDENCE_LABELS = frozenset({"changed", "keep"})


def product_intent_source_text(value: str) -> str:
    """Return product intent without host wrappers or source-evidence bodies."""

    original_intent = _operator_original_intent_block_text(value) or str(value or "")
    return _without_inline_source_metadata_clauses(_without_source_evidence_sections(original_intent))


def markdown_section_text(value: str, *, headings: frozenset[str]) -> str:
    """Return one explicit Markdown section without adjoining headings."""

    rows: list[str] = []
    collecting = False
    for row in str(value or "").splitlines():
        heading = _markdown_heading_key(row)
        if heading:
            if collecting:
                break
            if heading in headings:
                collecting = True
            continue
        if collecting:
            rows.append(row)
    return clean_markdown_text("\n".join(rows)).strip(" .")


def operator_context_from_product_text(value: str) -> str:
    """Recover target context without treating source metadata as product truth."""

    operator_text = _EXPLICIT_INTENT_LABEL_RE.split(str(value or ""), maxsplit=1)[0]
    for sentence in re.split(r"(?<=[.!?])\s+", operator_text):
        match = re.search(
            r"^\s*project\s+brief\s+for\s+"
            r"(?P<context>(?:a|an|the)\s+[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)(?:[.!?]|$)",
            sentence,
            flags=re.IGNORECASE,
        )
        if match:
            context = clean_markdown_text(match.group("context")).strip(" .")
            if context:
                return context
    return ""


def confirmed_direction_evidence_text(value: str) -> str:
    """Return inline evidence carried by a compact Confirmed direction heading."""

    prefix = "confirmed direction "
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        while line.startswith("#"):
            line = line[1:].lstrip()
        if line.casefold().startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def declaration_subject_predicate(value: str) -> tuple[str, str]:
    """Split one bounded subject declaration at its first is/are predicate."""

    text = clean_markdown_text(value).strip(" .")
    match = _DECLARATION_COPULA_RE.search(text)
    if not match:
        return "", ""
    return text[: match.start()].strip(" ,;:"), text[match.end() :].strip(" ,;:")


def coordinated_subjects(value: str) -> tuple[str, ...]:
    """Return subjects from a comma, and, or or Oxford-comma list."""

    text = clean_markdown_text(value).strip(" ,;:")
    if not text:
        return ()
    subjects = tuple(
        part
        for raw in _SUBJECT_CONJUNCTION_RE.split(text)
        if (part := clean_markdown_text(raw).strip(" ,;:"))
    )
    return subjects or (text,)


def without_confirmation_evidence_label(value: str) -> str:
    """Remove a compact confirmation field label while preserving its evidence."""

    text = clean_markdown_text(value).strip()
    label, separator, evidence = text.partition(":")
    if separator and label.strip().casefold() in _CONFIRMATION_EVIDENCE_LABELS:
        return evidence.strip()
    return text


def sentence_fragments(value: str) -> list[str]:
    words = request_words(value)
    rows: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if word.endswith((".", "!", "?")):
            rows.append(" ".join(current).strip(" ."))
            current = []
    if current:
        rows.append(" ".join(current).strip(" ."))
    return [row for row in rows if row]


def strip_leading_contextual_gerund_sentence(value: str) -> str:
    """Start a recovered path at its first action, not audience context."""

    rows = sentence_fragments(value)
    while len(rows) > 1 and is_contextual_gerund_phrase(rows[0]):
        rows.pop(0)
    return ". ".join(rows).strip(" .")


def strip_trailing_operator_instruction_sentences(value: str) -> str:
    rows = sentence_fragments(value)
    if len(rows) <= 1:
        return clean_markdown_text(value).strip(" .")
    kept = list(rows)
    while len(kept) > 1 and looks_like_trailing_operator_instruction(kept[-1]):
        kept.pop()
    return clean_markdown_text(". ".join(kept)).strip(" .")


def is_source_metadata_clause(value: str) -> bool:
    return bool(_SOURCE_METADATA_CLAUSE_RE.match(clean_markdown_text(value).strip()))


def without_source_metadata_clauses(value: str) -> str:
    """Retain operator text before the first standalone source metadata field."""

    return _without_inline_source_metadata_clauses(clean_markdown_text(value).strip())


def without_leading_explicit_intent_label(value: str) -> str:
    text = clean_markdown_text(value).strip()
    label = _EXPLICIT_INTENT_LABEL_RE.match(text)
    return text[label.end() :].strip() if label else text


def word_key(value: str) -> str:
    return str(value or "").casefold().strip(".,:;")


def request_words(value: str) -> list[str]:
    return [
        word.strip("()[]{}\"'")
        for word in clean_markdown_text(value).replace("/", " ").split()
        if word.strip("()[]{}\"'")
    ]


def _operator_original_intent_block_text(value: str) -> str:
    rows = str(value or "").splitlines()
    collected: list[str] = []
    collecting = False
    for row in rows:
        key = _heading_key(row)
        if collecting and key in _ORIGINAL_INTENT_BOUNDARY_HEADINGS:
            break
        if collecting:
            collected.append(row)
            continue
        if key == "original user intent":
            collecting = True
            if ":" in row:
                tail = row.split(":", 1)[1].strip()
                if tail:
                    collected.append(tail)
    return "\n".join(collected).strip()


def _without_source_evidence_sections(value: str) -> str:
    kept: list[str] = []
    skipping_source_evidence = False
    for row in str(value or "").splitlines():
        heading = _markdown_heading_key(row)
        if heading:
            if heading in _SOURCE_EVIDENCE_SECTION_HEADINGS:
                skipping_source_evidence = True
                continue
            if skipping_source_evidence:
                skipping_source_evidence = False
        if not skipping_source_evidence:
            kept.append(row)
    return "\n".join(kept)


def _markdown_heading_key(value: str) -> str:
    row = str(value or "")
    if not _MARKDOWN_HEADING_RE.match(row):
        return ""
    return _heading_key(row)


def _heading_key(value: str) -> str:
    text = str(value or "").strip()
    while text and text[0] in "#-* ":
        text = text[1:].strip()
    return text.rstrip(":").strip().casefold()


def looks_like_trailing_operator_instruction(value: str) -> bool:
    text = clean_markdown_text(value).strip(" .")
    if not text:
        return False
    normalized = _strip_leading_instruction_adverb(text).casefold()
    words = [word_key(word) for word in request_words(normalized)]
    if not words:
        return False
    command = words[0]
    control_text = " ".join(words)
    if normalized.startswith(("do not ", "don't ", "make sure ", "ensure ")):
        return True
    if (
        "post-confirm" in words
        and {"create", "finish", "governance", "artifact", "artifacts"}.intersection(words)
    ):
        return True
    if command not in REQUEST_COMMAND_WORDS | {"run", "execute", "install", "commit", "push", "edit", "reject"}:
        return False
    control_terms = {
        "after confirmation",
        "artifact",
        "artifacts",
        "command",
        "commands",
        "confirm",
        "greenfield",
        "implementation plan",
        "intent file",
        "next step",
        "post confirm",
        "post-confirm",
        "proposal",
    }
    return any(term in normalized or term in control_text for term in control_terms)


def _strip_leading_instruction_adverb(value: str) -> str:
    words = request_words(value)
    if words and word_key(words[0]) in {"also", "then", "next", "please"}:
        return " ".join(words[1:]).strip(" .")
    return clean_markdown_text(value).strip(" .")


def _without_inline_source_metadata_clauses(value: str) -> str:
    text = str(value or "").strip()
    labels = _source_metadata_labels(text)
    if not labels:
        return _INLINE_EXPLICIT_INTENT_LABEL_RE.sub("", text).strip()
    operator_text = text[: labels[0].start()].rstrip(" \t-;:,")
    return _INLINE_EXPLICIT_INTENT_LABEL_RE.sub("", operator_text).strip()


def _source_metadata_labels(value: str) -> list[re.Match[str]]:
    labels: list[re.Match[str]] = []
    for label in _SOURCE_METADATA_LABEL_RE.finditer(value):
        prefix = value[: label.start()]
        if not prefix or prefix.rstrip().endswith(_SOURCE_METADATA_BOUNDARY_PUNCTUATION):
            labels.append(label)
    return labels


__all__ = [
    "REQUEST_COMMAND_WORDS",
    "coordinated_subjects",
    "confirmed_direction_evidence_text",
    "declaration_subject_predicate",
    "is_source_metadata_clause",
    "looks_like_trailing_operator_instruction",
    "markdown_section_text",
    "operator_context_from_product_text",
    "product_intent_source_text",
    "request_words",
    "sentence_fragments",
    "strip_leading_contextual_gerund_sentence",
    "strip_trailing_operator_instruction_sentences",
    "without_leading_explicit_intent_label",
    "without_confirmation_evidence_label",
    "without_source_metadata_clauses",
    "word_key",
]
