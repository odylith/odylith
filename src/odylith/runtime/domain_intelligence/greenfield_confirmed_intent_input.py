"""Recover and normalize source text for confirmed greenfield intent."""

from __future__ import annotations

from collections.abc import Mapping
import re

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    has_explicit_section_boundaries,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    product_context_paragraphs,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import (
    confirmation_from_operator_intent,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_heading_key,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    normalize_confirmed_intent_heading,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import (
    prompt_first_path_source,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import (
    prompt_has_material_first_path_gap,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import (
    prompt_intent_source,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materiality import (
    title_supports_conservative_first_path,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_HOST_GUIDANCE_BOUNDARY_HEADINGS = frozenset(
    {
        "confirmed cli after confirmation",
        "do not",
        "host reasoning task",
        "next step",
        "visible format contract",
        "write in chat",
    }
)


def is_host_guidance_envelope(value: str) -> bool:
    """Return whether input is a host-control envelope rather than product evidence."""

    lowered = str(value or "").casefold()
    return (
        "product intent confirmation needed" in lowered
        and "visible format contract" in lowered
        and "original user intent" in lowered
    )


def recover_host_guidance_confirmation(text: str, *, prompt: str = "") -> str:
    """Recover product intent when an Odylith guidance envelope is passed by mistake."""

    raw = str(text or "")
    if not is_host_guidance_envelope(raw):
        return raw
    intent_text = _host_guidance_original_intent(raw) or _clean(prompt)
    if not intent_text:
        return raw
    return confirmation_from_operator_intent(intent_text, prefer_product_title=True)


def thin_operator_intent_source(text: str, *, prompt: str = "") -> str:
    """Return an operator request that can be lifted into a full confirmation."""

    raw = _clean(text)
    if not raw:
        return ""
    for candidate in (raw, _clean(prompt)):
        source = _operator_request_source(candidate)
        if source:
            return source
    return ""


def thin_recovery_source_text(text: str, sections: Mapping[str, list[str]], title: str) -> str:
    """Preserve product-context paragraphs when recovering a thin confirmation."""

    if not has_explicit_section_boundaries(sections):
        return _clean(text)
    paragraphs = product_context_paragraphs(text, sections, title)
    if not paragraphs:
        return ""
    title_text = _clean(title)
    return _clean(". ".join([title_text, *paragraphs] if title_text else paragraphs))


def has_structured_body_sections(sections: Mapping[str, list[str]]) -> bool:
    """Return whether parsed confirmation text has its substantive sections."""

    return any(
        key
        in {
            "state_object",
            "first_path",
            "proof_boundary",
            "human_actors",
            "internal_systems",
            "external_systems",
            "component_responsibilities",
        }
        for key in sections
    )


def canonical_prompt_text(value: object, *, title_normalization: object) -> str:
    """Keep raw provisional title text out of normalized public prompt fields."""

    text = _clean(value)
    if not text:
        return ""
    raw_title = _clean(getattr(title_normalization, "raw_title", ""))
    canonical_title = _clean(getattr(title_normalization, "canonical_title", ""))
    if raw_title and canonical_title and text.casefold() == raw_title.casefold():
        return canonical_title
    if raw_title and canonical_title and raw_title != canonical_title:
        text = re.sub(re.escape(raw_title), canonical_title, text, flags=re.IGNORECASE)
    text = prompt_first_path_source(text)
    text = normalize_project_title(text, fallback=canonical_title or "Greenfield Project").canonical_title
    return _clean(text)


def _operator_request_source(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    prompt_source = prompt_intent_source(text)
    first_path_source = prompt_source.first_path
    if word_count(first_path_source) < 6:
        return text if title_supports_conservative_first_path(title=prompt_source.title, evidence=text) else ""
    model = first_path_model(first_path_source)
    if prompt_has_material_first_path_gap(text):
        return ""
    if len(model.steps) >= 2 or model.material_action or model.visible_outcome:
        return text
    return text if title_supports_conservative_first_path(title=prompt_source.title, evidence=text) else ""


def _host_guidance_original_intent(text: str) -> str:
    lines = str(text or "").splitlines()
    collecting = False
    values: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        normalized = normalize_confirmed_intent_heading(line.rstrip(":"))
        if normalized == "original user intent":
            collecting = True
            if ":" in line:
                tail = _clean(line.split(":", 1)[1])
                if tail:
                    values.append(tail)
            continue
        if collecting and _host_guidance_boundary_heading(line, normalized):
            break
        if collecting and line:
            values.append(line)
    return _clean(" ".join(values))


def _host_guidance_boundary_heading(line: str, normalized: str) -> bool:
    if normalized in _HOST_GUIDANCE_BOUNDARY_HEADINGS:
        return True
    if line.casefold().startswith("confirmed cli after confirmation:"):
        return True
    return bool(confirmed_intent_heading_key(line) and normalized != "original user intent")


def _clean(value: object) -> str:
    return clean_markdown_text(value)
