"""First-path step derivation for confirmed greenfield Atlas output."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language


ACTION_VERB_PATTERN = (
    r"adds?|adjusts?|approves?|assigns?|attaches?|calculates?|captures?|checks?|chooses?|closes?|collects?|"
    r"compares?|completes?|computes?|confirms?|corrects?|creates?|decides?|declines?|deletes?|derives?|edits?|"
    r"enters?|evaluates?|exports?|fetches?|finds?|gets?|groups?|hands?|highlights?|imports?|lets?|links?|logs?|"
    r"displays?|moves?|notifies?|opens?|orders?|persists?|preserves?|produces?|publishes?|ranks?|reads?|receives?|records?|rejects?|"
    r"renders?|requests?|resolves?|returns?|reviews?|routes?|runs?|saves?|schedules?|screens?|sees?|selects?|sends?|"
    r"shows?|stores?|submits?|supplies?|tracks?|validates?|verifies?|views?|votes?"
)
_SPLIT_ACTION_VERB_PATTERN = ACTION_VERB_PATTERN.replace("schedules?", "schedules").replace("views?", "views")


def sequence_event_steps(
    first_path: str,
    *,
    semantic_model: Mapping[str, Any] | None = None,
    dedupe: bool = False,
) -> list[str]:
    """Return normalized first-path event steps for sequence-style Atlas diagrams."""

    steps = _drop_launcher_only_steps(_semantic_event_steps(semantic_model) or _first_path_steps(first_path))
    return _dedupe_steps(steps) if dedupe else steps


def _semantic_event_steps(semantic_model: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(semantic_model, Mapping):
        return []
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return []
    rows = contract.get("events")
    if not isinstance(rows, list):
        return []
    steps: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        text = _compact_text(str(row.get("text") or row.get("mutation") or ""))
        if text:
            text = _normalize_event_step(text)
            steps.append(text)
    return _dedupe_steps(_expand_compound_steps(steps))


def _drop_launcher_only_steps(values: list[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        if not rows and _launcher_only_step(value):
            continue
        rows.append(value)
    return rows


def _launcher_only_step(value: str) -> bool:
    text = _compact_text(value).strip(" .")
    return bool(
        len(label_terms(text)) <= 6
        and (
            re.search(r"\bopens?\s+(?:the\s+)?(?:app|web app|application|site|website|product)\b", text, flags=re.IGNORECASE)
            or re.search(r"\b(?:signs?\s+in|logs?\s+in|authenticates?)\b", text, flags=re.IGNORECASE)
        )
    )


def _normalize_event_step(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if re.search(r"\bvisible-result\s+event\b", text, re.IGNORECASE):
        text = re.sub(r"\s+is\s+the\s+visible-result\s+event\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
        text = re.sub(r"^\s*this\s+", "Show the ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+[\u2014-]\s*", ": ", text, count=1)
    if re.search(r"\brenders?\s+the\s+visible\s+result\s*:", text, re.IGNORECASE):
        text = re.sub(
            r"^.*?\brenders?\s+the\s+visible\s+result\s*:\s*"
            r"(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer|[A-Za-z][A-Za-z0-9/-]*(?:\s+[A-Za-z][A-Za-z0-9/-]*){0,3})\s+"
            r"(?:sees?|views?|receives?|gets?|reads?)\s+",
            "Show ",
            text,
            flags=re.IGNORECASE,
        )
    text = normalize_visible_result_language(text)
    return text


def _first_path_steps(value: str) -> list[str]:
    semantic_steps = list(first_path_steps(value))
    if semantic_steps:
        return _dedupe_steps(_expand_compound_steps(semantic_steps))
    text = _compact_text(value)
    if not text:
        return []
    numbered = [part.strip(" .") for part in re.split(r"(?:^|\s)\d+[.)]\s*", text) if part.strip(" .")]
    if len(numbered) > 1:
        first = numbered[0]
        if ":" in first:
            first = first.rsplit(":", 1)[-1].strip(" .")
        steps = [first, *numbered[1:]] if first else numbered[1:]
        return [_sentence(step).rstrip(".") for step in steps if len(label_terms(step)) >= 3]
    steps = [part.strip(" .") for part in re.split(r"(?<=[.!?])\s+|;\s+", text) if part.strip(" .")]
    expanded: list[str] = []
    for step in steps:
        expanded.extend(
            part.strip(" .")
            for part in re.split(r"\s+and\s+(?=(?:the\s+)?[A-Za-z]+\s+receives?\b)", step)
            if part.strip(" .")
        )
    steps = expanded
    split_steps: list[str] = []
    for step in steps:
        split_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf",\s+(?=(?:and\s+)?(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = split_steps
    expanded_steps: list[str] = []
    for step in steps:
        expanded_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf"\s+and\s+(?=(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = expanded_steps
    return [_sentence(step).rstrip(".") for step in steps if step]


def _expand_compound_steps(values: list[str]) -> list[str]:
    expanded: list[str] = []
    for value in values:
        parts = [
            part.strip(" .")
            for part in re.split(
                rf",\s+(?=(?:and\s+)?(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an|this|that)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
                _compact_text(value),
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        ]
        split_parts: list[str] = []
        for part in parts or [value]:
            split_parts.extend(
                segment.strip(" .")
                for segment in re.split(
                    rf"\s+and\s+(?=(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an|this|that)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
                    part,
                    flags=re.IGNORECASE,
                )
                if segment.strip(" .")
            )
        expanded.extend(_sentence(part).rstrip(".") for part in split_parts if part)
    return expanded


def _dedupe_steps(values: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _compact_text(value).strip(" .")
        key = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
        if not text or key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


def _sentence(value: str) -> str:
    text = clean_markdown_text(value).rstrip(".")
    if text:
        text = text[:1].upper() + text[1:]
    return f"{text}." if text else ""


def _compact_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


__all__ = ["ACTION_VERB_PATTERN", "sequence_event_steps"]
