"""Parse the small confirmed-intent artifact used by greenfield create."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import FIELD_MIN_WORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import (
    contains_meta_narration as _contains_meta_narration,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import (
    has_progression_or_outcome as _has_progression_or_outcome,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import (
    validate_confirmed_intent as _validate_confirmed_intent,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import confirmed_system_description
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import confirmed_system_name
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import (
    contains_generic_system_scaffold as _contains_generic_system_scaffold,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import (
    expand_internal_system_rows as _expand_internal_system_rows,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import internal_system_rows as _internal_system_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import intent_context_text as _intent_context_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import preferred_internal_rows as _preferred_internal_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import role_or_system_rows as _role_or_system_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import confirmation_from_operator_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_first_path_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_extraction import (
    looks_like_confirmation_instruction,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_extraction import (
    title_from_product_intent_line,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms as _label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import (
    clean_first_path_text as _clean_first_path,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


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
    raw_title = _clean(payload.get("title") or payload.get("product_title") or fallback_title)
    title_normalization = normalize_project_title(raw_title, fallback=fallback_title or "Greenfield Project")
    title = title_normalization.canonical_title
    component_rows = _role_or_system_rows(
        payload.get("component_responsibilities")
        or payload.get("component_rows")
        or payload.get("components")
        or payload.get("owned_capabilities")
    )
    result: dict[str, Any] = {
        "title": title,
        "prompt": _canonical_prompt_text(payload.get("prompt") or prompt, title_normalization=title_normalization),
        "product_story": _clean(payload.get("product_story") or payload.get("story")),
        "state_object": _clean(payload.get("state_object") or payload.get("state_object_first_journey")),
        "first_path": _clean_first_path(payload.get("first_path") or payload.get("first_workflow")),
        "proof_boundary": _clean(payload.get("proof_boundary")),
        "problem": _clean(payload.get("problem") or payload.get("user_problem") or payload.get("user_problem_and_risk")),
        "customer": _clean(payload.get("customer")),
        "opportunity": _clean(payload.get("opportunity")),
        "product_view": _clean(payload.get("product_view")),
        "success_metrics": confirmed_text_values(payload.get("success_metrics") or payload.get("proof_metrics")),
        "component_responsibilities": component_rows,
        "human_actors": _role_or_system_rows(payload.get("human_actors") or payload.get("actors")),
        "external_systems": confirmed_text_values(payload.get("external_systems")),
        "internal_systems": [],
        "assumptions": confirmed_text_values(payload.get("assumptions") or payload.get("critical_assumptions")),
        "ambiguities": confirmed_text_values(
            payload.get("ambiguities") or payload.get("material_ambiguities") or payload.get("open_questions")
        ),
        "non_goals": confirmed_text_values(payload.get("non_goals")),
    }
    if title_normalization.changed:
        result["source_title"] = title_normalization.raw_title
    result["internal_systems"] = _expand_internal_system_rows(
        _preferred_internal_rows(
            _role_or_system_rows(payload.get("internal_systems") or payload.get("internal_product_systems")),
            component_rows,
        ),
        context_text=_intent_context_text(result, strings=confirmed_text_values),
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
        "source_title",
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
    if _contains_generic_system_scaffold(confirmed_text_values(result.get("internal_systems"))):
        return result
    return complete_confirmed_intent(result)


def parse_confirmed_intent_text(text: str, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Parse the human Product Intent Confirmation that the host already showed."""

    text = _recover_host_guidance_confirmation(text, prompt=prompt)
    sections = _sections(text)
    raw_title_candidate = _title_from_text(text) or _title_from_sections(sections) or _title_from_preamble(sections) or fallback_title
    if not _has_structured_body_sections(sections) and not _has_unheaded_confirmation_shape(text, raw_title_candidate):
        thin_source = _thin_operator_intent_source(text, prompt=prompt)
        if thin_source:
            text = confirmation_from_operator_intent(thin_source, prefer_product_title=True)
            sections = _sections(text)
    raw_title = _title_from_text(text) or _title_from_sections(sections) or _title_from_preamble(sections) or fallback_title
    title_normalization = normalize_project_title(raw_title, fallback=fallback_title or "Greenfield Project")
    title = title_normalization.canonical_title
    preamble_story = _preamble_story(sections, title)
    preamble_paragraphs = _preamble_paragraphs(text, title)
    derived_proof = _derived_proof_boundary_paragraph(preamble_paragraphs)
    derived_state = _derived_state_paragraph(preamble_paragraphs)
    derived_first_path = _derived_first_path_paragraph(preamble_paragraphs)
    derived_story = _derived_product_story(
        preamble_paragraphs,
        state=derived_state,
        first_path=derived_first_path,
        proof_boundary=derived_proof,
    )
    structured_preamble_story = preamble_story if _has_structured_body_sections(sections) else ""
    result: dict[str, Any] = {
        "title": _clean(title),
        "prompt": _canonical_prompt_text(prompt, title_normalization=title_normalization),
        "product_story": _section_text(sections, "product_story") or structured_preamble_story or derived_story or preamble_story,
        "state_object": _section_text(sections, "state_object") or derived_state,
        "first_path": _clean_first_path(_section_text(sections, "first_path") or derived_first_path),
        "proof_boundary": _section_text(sections, "proof_boundary") or derived_proof,
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
    if title_normalization.changed:
        result["source_title"] = title_normalization.raw_title
    result["internal_systems"] = _internal_system_rows(
        sections,
        section_list=_section_list,
        section_text=_section_text,
        context_text=_intent_context_text(result, strings=confirmed_text_values),
    )
    result = _complete_confirmed_intent_before_validation(result)
    _validate_confirmed_intent(result)
    return result


def _recover_host_guidance_confirmation(text: str, *, prompt: str = "") -> str:
    """Recover product intent when an Odylith guidance envelope is passed by mistake."""

    raw = str(text or "")
    if not _looks_like_host_guidance_envelope(raw):
        return raw
    intent_text = _host_guidance_original_intent(raw) or _clean(prompt)
    if not intent_text:
        sections = _sections(raw)
        if _has_structured_body_sections(sections):
            return raw
        return raw
    return confirmation_from_operator_intent(intent_text, prefer_product_title=True)


def _thin_operator_intent_source(text: str, *, prompt: str = "") -> str:
    """Return an operator request that can be lifted into a full confirmation."""

    raw = _clean(text)
    if not raw:
        return ""
    for candidate in (raw, _clean(prompt)):
        source = _operator_request_source(candidate)
        if source:
            return source
    return ""


def _has_unheaded_confirmation_shape(text: str, title: str) -> bool:
    paragraphs = _preamble_paragraphs(text, title)
    if len(paragraphs) < 3:
        return False
    state = _derived_state_paragraph(paragraphs)
    first_path = _derived_first_path_paragraph(paragraphs)
    proof = _derived_proof_boundary_paragraph(paragraphs)
    story = _derived_product_story(paragraphs, state=state, first_path=first_path, proof_boundary=proof)
    return bool(state and first_path and proof and story)


def _operator_request_source(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    first_path_source = prompt_first_path_source(text)
    if _word_count(first_path_source) < 6:
        return ""
    model = first_path_model(first_path_source)
    if len(model.steps) >= 2 or model.material_action or model.visible_outcome:
        return text
    return ""


def _looks_like_host_guidance_envelope(text: str) -> bool:
    lowered = str(text or "").casefold()
    return (
        "product intent confirmation needed" in lowered
        and "visible format contract" in lowered
        and "original user intent" in lowered
    )


def _host_guidance_original_intent(text: str) -> str:
    lines = str(text or "").splitlines()
    collecting = False
    values: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        normalized = _normalize_heading(line.rstrip(":"))
        if normalized == "original user intent":
            collecting = True
            continue
        if collecting and (
            normalized in {"next step", "confirmed cli after confirmation"}
            or line.casefold().startswith("confirmed cli after confirmation:")
        ):
            break
        if collecting and line:
            values.append(line)
    return _clean(" ".join(values))


def _has_structured_body_sections(sections: Mapping[str, list[str]]) -> bool:
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


def _canonical_prompt_text(value: Any, *, title_normalization: Any) -> str:
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


def confirmed_intent_summary(intent: Mapping[str, Any] | None, key: str, fallback: str) -> str:
    if not isinstance(intent, Mapping):
        return fallback
    value = _clean(intent.get(key))
    return value or fallback


def confirmed_intent_list(intent: Mapping[str, Any] | None, key: str) -> list[str]:
    if not isinstance(intent, Mapping):
        return []
    return confirmed_text_values(intent.get(key))


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


def _normalize_heading(value: str) -> str:
    text = re.sub(r"[*_`]+", " ", str(value or "")).strip().casefold()
    text = re.sub(r"[–—-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_from_text(text: str) -> str:
    for raw_line in str(text or "").splitlines():
        raw = str(raw_line or "").strip()
        if not raw.startswith("#"):
            continue
        line = _clean(raw.lstrip("#").strip())
        candidate = title_from_product_intent_line(line)
        if candidate:
            return candidate
        if line and not _classify_heading(line):
            return line
    for raw_line in str(text or "").splitlines():
        if looks_like_confirmation_instruction(raw_line):
            continue
        line = _clean(raw_line.lstrip("#").strip())
        if not line:
            continue
        candidate = title_from_product_intent_line(line)
        if candidate:
            return candidate
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
    words = _label_terms(text)
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


def _preamble_paragraphs(text: str, title: str) -> list[str]:
    title_text = _clean(title).casefold()
    paragraphs: list[str] = []
    for raw in re.split(r"\n\s*\n+", str(text or "")):
        lines: list[str] = []
        for line in raw.splitlines():
            cleaned = _clean(line.lstrip("#").strip())
            if not cleaned:
                continue
            if title_text and cleaned.casefold() == title_text:
                continue
            if _heading_key(line):
                continue
            if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line):
                continue
            lines.append(cleaned)
        paragraph = _clean(" ".join(lines))
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def _derived_state_paragraph(paragraphs: Sequence[str]) -> str:
    for paragraph in paragraphs:
        if _looks_like_state_paragraph(paragraph) and _word_count(paragraph) >= FIELD_MIN_WORDS["state_object"]:
            return paragraph
    return ""


def _derived_first_path_paragraph(paragraphs: Sequence[str]) -> str:
    scored: list[tuple[int, int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        if _word_count(paragraph) < FIELD_MIN_WORDS["first_path"]:
            continue
        if _looks_like_proof_or_scope_paragraph(paragraph) or _looks_like_state_paragraph(paragraph):
            continue
        if not _has_material_first_path_action(paragraph):
            continue
        model = first_path_model(paragraph)
        action_count = sum(1 for step in model.steps if _has_progression_or_outcome(step))
        score = action_count * 3
        if model.visible_outcome:
            score += 5
        if re.search(r"\b(?:opens?|starts?|adds?|enters?|logs?|records?|submits?|saves?|corrects?)\b", paragraph, re.IGNORECASE):
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
        re.match(r"^[^.]{1,80}\bneed(?:s)?\b[^.]{0,120}\b(?:way|place|product|tool|experience)\b", text, re.IGNORECASE)
        or re.match(r"^[^.]{1,80}\b(?:want|wants)\b[^.]{0,120}\b(?:way|place|product|tool|experience)\b", text, re.IGNORECASE)
        or re.search(r"\b(?:helps?|gives?)\s+[^.]{1,80}\b(?:receive|understand|avoid|decide|keep)\b", text, re.IGNORECASE)
    )


def _derived_proof_boundary_paragraph(paragraphs: Sequence[str]) -> str:
    for paragraph in paragraphs:
        if _word_count(paragraph) >= FIELD_MIN_WORDS["proof_boundary"] and _looks_like_proof_or_scope_paragraph(paragraph):
            return paragraph
    return ""


def _derived_product_story(paragraphs: Sequence[str], *, state: str, first_path: str, proof_boundary: str = "") -> str:
    story_rows: list[str] = []
    state_key = _clean(state).casefold()
    path_key = _clean(first_path).casefold()
    proof_key = _clean(proof_boundary).casefold()
    for paragraph in paragraphs:
        lowered = paragraph.casefold()
        if lowered == state_key or lowered == path_key or lowered == proof_key:
            continue
        if _looks_like_state_paragraph(paragraph) or _looks_like_proof_or_scope_paragraph(paragraph):
            continue
        if _word_count(paragraph) >= 12:
            story_rows.append(paragraph)
        if len(story_rows) >= 2:
            break
    return _clean(" ".join(story_rows))


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
        or re.search(r"\b(?:first\s+release|release\s+[0-9.]+)\s+(?:is\s+)?(?:proven|good\s+enough|ready|succeeds?|works?)\b", text, re.IGNORECASE)
        or re.search(r"\b(?:out\s+of\s+scope|deferred|not\s+included|non[- ]goals?)\b", text, re.IGNORECASE)
    )


def _looks_like_state_paragraph(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    return bool(
        re.search(
            r"\b(?:central|core|main|primary)\s+(?:object|state)\b"
            r"|\b(?:state|record|history)\s+(?:is|records?|keeps?|carries?|tracks?|stores?|maintains?)\b"
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


def _clean(value: object) -> str:
    return clean_markdown_text(value)


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
