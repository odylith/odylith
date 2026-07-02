"""Section parsing for human greenfield Product Intent Confirmations."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


def confirmed_intent_sections(text: str) -> dict[str, list[str]]:
    """Return normalized section rows from heading and inline-label Markdown."""

    sections: dict[str, list[str]] = {}
    current = "preamble"
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        inline_heading = confirmed_intent_inline_heading_value(line)
        if inline_heading:
            current, value = inline_heading
            sections.setdefault(current, [])
            if value:
                sections[current].append(value)
            continue
        heading = confirmed_intent_heading_key(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        if not line.strip() and current == "preamble":
            continue
        sections.setdefault(current, []).append(line)
    return sections


def confirmed_intent_heading_key(line: str) -> str:
    text = line.strip()
    if not text:
        return ""
    if text.startswith("#"):
        return classify_confirmed_intent_heading(text.lstrip("#").strip())
    if text.endswith(":") and len(text.split()) <= 8:
        return classify_confirmed_intent_heading(text[:-1].strip())
    return classify_confirmed_intent_heading(text) if _looks_like_plain_heading(text) else ""


def confirmed_intent_inline_heading_value(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text or ":" not in text:
        return None
    label, value = text.split(":", 1)
    if len(label.split()) > 8:
        return None
    heading = classify_confirmed_intent_heading(label.strip())
    if not heading:
        return None
    return heading, clean_markdown_text(value)


def _looks_like_plain_heading(text: str) -> bool:
    lowered = normalize_confirmed_intent_heading(text)
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
        "primary actors",
        "main actors",
        "participants",
        "stakeholders",
        "people who participate",
        "who participates",
        "external systems",
        "external systems not owned by this product",
        "internal systems",
        "internal product systems",
        "primary systems",
        "primary product systems",
        "product systems",
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


def classify_confirmed_intent_heading(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
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
    if "human actor" in normalized or normalized in {
        "actors",
        "primary actors",
        "main actors",
        "participants",
        "stakeholders",
        "people who participate",
        "who participates",
    }:
        return "human_actors"
    if normalized in {"primary systems", "primary product systems", "product systems"}:
        return "internal_systems"
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


def normalize_confirmed_intent_heading(value: str) -> str:
    text = re.sub(r"[*_`]+", " ", str(value or "")).strip().casefold()
    text = re.sub(r"[–—-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "classify_confirmed_intent_heading",
    "confirmed_intent_heading_key",
    "confirmed_intent_inline_heading_value",
    "confirmed_intent_sections",
    "normalize_confirmed_intent_heading",
]
