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
        heading_text = text.lstrip("#").strip()
        return classify_confirmed_intent_heading(heading_text) or _noncanonical_section_key(heading_text)
    if text.endswith(":") and len(text.split()) <= 8:
        heading_text = text[:-1].strip()
        return classify_confirmed_intent_heading(heading_text) or _noncanonical_section_key(heading_text)
    return classify_confirmed_intent_heading(text) or _noncanonical_section_key(text) if _looks_like_plain_heading(text) else ""


def confirmed_intent_inline_heading_value(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text or ":" not in text:
        return None
    label, value = text.split(":", 1)
    if len(label.split()) > 8:
        return None
    normalized_label = normalize_confirmed_intent_heading(label)
    if re.search(r"\b(?:are|contains?|is|tracks?)\b", normalized_label):
        return None
    heading = classify_confirmed_intent_heading(label.strip())
    if not heading:
        return None
    return heading, clean_markdown_text(value)


def _looks_like_plain_heading(text: str) -> bool:
    lowered = normalize_confirmed_intent_heading(text)
    known = {
        "accepted facts",
        "acceptance",
        "acceptance proof",
        "abstract",
        "appendix",
        "background",
        "benchmarks",
        "business goals",
        "conclusion",
        "conclusions",
        "contributions",
        "discussion",
        "evidence",
        "experimental results",
        "experiments",
        "findings",
        "acknowledgements",
        "acknowledgments",
        "author information",
        "authors",
        "bibliography",
        "citations",
        "copyright",
        "limitations",
        "license",
        "market",
        "methods",
        "personas",
        "prd",
        "references",
        "requirements",
        "research findings",
        "results",
        "scope",
        "use cases",
        "user stories",
        "product story",
        "product overview",
        "overview",
        "summary",
        "goal",
        "goals",
        "mission",
        "why",
        "intent",
        "narrative",
        "product title",
        "project title",
        "product name",
        "project name",
        "state object",
        "state",
        "core state",
        "core object",
        "primary object",
        "state model",
        "record",
        "record model",
        "first complete path",
        "first path",
        "first journey",
        "first workflow",
        "workflow",
        "user journey",
        "happy path",
        "golden path",
        "user problem",
        "user problem and risk",
        "problem",
        "customer",
        "customers",
        "opportunity",
        "product view",
        "success metrics",
        "proof metrics",
        "state object that changes through the first journey",
        "first complete path odylith should prove before broader scope",
        "first complete path the product should prove before broader scope",
        "human actors",
        "users",
        "user roles",
        "roles",
        "primary actors",
        "main actors",
        "participants",
        "stakeholders",
        "people who participate",
        "who participates",
        "external systems",
        "external dependencies",
        "integrations",
        "dependencies",
        "external systems not owned by this product",
        "internal systems",
        "internal product systems",
        "owned systems",
        "product modules",
        "modules",
        "capabilities",
        "primary systems",
        "primary product systems",
        "product systems",
        "assumptions",
        "critical assumptions",
        "constraints",
        "ambiguities that would change the first path",
        "material ambiguities",
        "ambiguities",
        "open questions",
        "proof boundary",
        "proof",
        "evidence boundary",
        "release proof",
        "done when",
        "next step",
        "non goals",
        "non-goals",
        "systems",
        "component responsibilities",
        "owned capabilities",
    }
    if lowered in known:
        return True
    if re.match(r"^(?:[0-9]+(?:\.[0-9]+)*|[a-z])\s+[a-z0-9][a-z0-9 ]{2,100}$", lowered):
        return not re.search(r"\b(?:can|could|may|must|shall|should|will|would)\b", lowered)
    words = text.split()
    if not 1 <= len(words) <= 10:
        return False
    if text.endswith((".", "!", "?")):
        return False
    content_words = [word.strip("()[]{}.,:;") for word in words if word.strip("()[]{}.,:;")]
    if not content_words:
        return False
    title_like = sum(1 for word in content_words if word[:1].isupper() or word.isupper())
    if title_like < max(1, len(content_words) - 1):
        return False
    lowered_words = {word.casefold() for word in content_words}
    if lowered_words & {
        "abstract",
        "appendix",
        "architecture",
        "background",
        "benchmark",
        "benchmarks",
        "business",
        "conclusion",
        "contributions",
        "evidence",
        "experiment",
        "experiments",
        "limitations",
        "market",
        "method",
        "methods",
        "requirements",
        "results",
        "scope",
        "references",
    }:
        return True
    return False


def classify_confirmed_intent_heading(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    if "product intent confirmation" in normalized:
        return "title"
    if normalized in {"product title", "project title", "product name", "project name", "name", "title"}:
        return "title"
    if (
        "product story" in normalized
        or normalized
        in {
            "accepted facts",
            "business goal",
            "business goals",
            "intent",
            "mission",
            "narrative",
            "overview",
            "product narrative",
            "product overview",
            "summary",
            "why",
            "why this exists",
        }
        or normalized.startswith(("goal", "goals"))
    ):
        return "product_story"
    if normalized in {"user problem", "user problem and risk", "problem"}:
        return "problem"
    if normalized in {"customer", "customers"}:
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
        "people",
        "personas",
        "stakeholders",
        "people who participate",
        "roles",
        "user roles",
        "users",
        "who participates",
    }:
        return "human_actors"
    if normalized in {
        "capabilities",
        "modules",
        "owned capabilities",
        "owned systems",
        "primary systems",
        "primary product systems",
        "product capabilities",
        "product modules",
        "product systems",
    }:
        return "internal_systems"
    if normalized == "systems":
        return "systems"
    if "component responsibilit" in normalized or "owned capabilit" in normalized:
        return "component_responsibilities"
    if normalized.startswith("internal ") and (
        "internal product system" in normalized or "internal system" in normalized
    ):
        return "internal_systems"
    if normalized in {"dependencies", "external dependencies", "integrations"}:
        return "external_systems"
    if normalized.startswith("external ") and "external system" in normalized:
        return "external_systems"
    if "internal product system" in normalized or "internal system" in normalized:
        return "internal_systems"
    if "external system" in normalized:
        return "external_systems"
    if "critical assumption" in normalized or normalized in {"assumptions", "constraints"}:
        return "assumptions"
    if "ambiguities" in normalized or "open question" in normalized:
        return "ambiguities"
    if (
        "state object" in normalized
        or normalized
        in {
            "core object",
            "core record",
            "core state",
            "primary object",
            "record",
            "record model",
            "state",
            "state model",
        }
    ):
        return "state_object"
    if (
        "first complete path" in normalized
        or "first workflow" in normalized
        or "first path" in normalized
        or normalized
        in {
            "first journey",
            "golden path",
            "happy path",
            "use case",
            "use cases",
            "user journey",
            "workflow",
        }
    ):
        return "first_path"
    if (
        "proof boundary" in normalized
        or normalized
        in {"acceptance", "acceptance proof", "done when", "evidence boundary", "proof", "release proof"}
    ):
        return "proof_boundary"
    if "non goal" in normalized or "non-goal" in normalized:
        return "non_goals"
    return ""


def normalize_confirmed_intent_heading(value: str) -> str:
    text = re.sub(r"[*_`]+", " ", str(value or "")).strip().casefold()
    text = re.sub(r"[–—-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def is_confirmed_intent_ignored_section(key: str) -> bool:
    return str(key or "").startswith("__ignored__:")


def is_confirmed_intent_supporting_section(key: str) -> bool:
    return str(key or "").startswith("__supporting__:")


def _noncanonical_section_key(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    if _looks_like_operator_instruction_heading(normalized):
        return _ignored_section_key(normalized)
    return _supporting_section_key(normalized)


def _looks_like_operator_instruction_heading(normalized: str) -> bool:
    if normalized in {
        "after confirmation",
        "child boundaries",
        "coding notes",
        "confirmed cli after confirmation",
        "development notes",
        "do not",
        "execution plan",
        "host reasoning task",
        "implementation notes",
        "implementation plan",
        "next step",
        "next steps",
        "operator instructions",
        "implementation prompt",
        "planning notes",
        "program formation",
        "program plan",
        "release selector",
        "technical plan",
        "visible format contract",
        "write in chat",
        "acknowledgements",
        "acknowledgments",
        "author information",
        "authors",
        "bibliography",
        "citations",
        "copyright",
        "license",
        "references",
    }:
        return True
    instruction_terms = {
        "after confirmation",
        "claude",
        "cli",
        "codex",
        "command",
        "instruction",
        "next step",
        "write in chat",
    }
    planning_terms = {"backlog", "child", "implementation", "plan", "program", "roadmap", "wave"}
    return bool(set(normalized.split()) & instruction_terms) or bool(
        ("formation" in normalized or "notes" in normalized) and set(normalized.split()) & planning_terms
    )


def _ignored_section_key(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    return "__ignored__:" + normalized.replace(" ", "_")


def _supporting_section_key(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    return "__supporting__:" + normalized.replace(" ", "_")


__all__ = [
    "classify_confirmed_intent_heading",
    "confirmed_intent_heading_key",
    "confirmed_intent_inline_heading_value",
    "confirmed_intent_sections",
    "is_confirmed_intent_ignored_section",
    "is_confirmed_intent_supporting_section",
    "normalize_confirmed_intent_heading",
]
