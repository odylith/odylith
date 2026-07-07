"""Parse the small confirmed-intent artifact used by greenfield create."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import combined_system_rows as _combined_system_rows
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
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_FACTS_HASH_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    is_product_intent_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_hash,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_payload,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    classify_confirmed_intent_heading as _classify_heading,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_heading_key as _heading_key,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_inline_heading_value as _inline_heading_value,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_sections as _sections,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    is_confirmed_intent_supporting_section as _is_supporting_section,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    normalize_confirmed_intent_heading as _normalize_heading,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms as _label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import (
    clean_first_path_text as _clean_first_path,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_requirement_control_tail
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


@dataclass(frozen=True)
class ConfirmedIntentRecord:
    """Confirmed product facts plus their typed custody envelope."""

    product_facts: dict[str, Any]
    envelope: dict[str, Any]


_PROMPT_MATERIAL_TERM_STOPWORDS = frozenset(
    {
        "accepted",
        "action",
        "artifact",
        "complete",
        "evidence",
        "first",
        "greenfield",
        "intent",
        "path",
        "product",
        "project",
        "proof",
        "proposal",
        "record",
        "release",
        "result",
        "review",
        "source",
        "state",
        "system",
        "user",
        "workspace",
    }
)


def load_confirmed_intent_file(path: Path, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Load a host-visible Product Intent Confirmation from Markdown/text/JSON."""

    return load_confirmed_intent_record(path, prompt=prompt, fallback_title=fallback_title).product_facts


def load_confirmed_intent_record(path: Path, *, prompt: str = "", fallback_title: str = "") -> ConfirmedIntentRecord:
    """Load confirmed intent and return the typed custody envelope."""

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
        intent = normalize_confirmed_intent(payload, prompt=prompt, fallback_title=fallback_title)
        envelope = (
            _canonicalized_loaded_envelope(payload, intent)
            if is_product_intent_envelope(payload)
            else build_product_intent_envelope(
                intent,
                source_text=text,
                source_path=source,
                source_format="legacy_json",
            )
        )
        return ConfirmedIntentRecord(product_facts=intent, envelope=envelope)
    intent = parse_confirmed_intent_text(text, prompt=prompt, fallback_title=fallback_title)
    envelope = build_product_intent_envelope(
        intent,
        source_text=text,
        source_path=source,
        source_format="markdown",
    )
    return ConfirmedIntentRecord(product_facts=intent, envelope=envelope)


def confirmed_intent_product_facts(record: ConfirmedIntentRecord | Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical product facts from a record or legacy mapping."""

    if isinstance(record, ConfirmedIntentRecord):
        return dict(record.product_facts)
    return dict(record)


def normalize_confirmed_intent(value: object, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Normalize JSON or already parsed confirmation data into the builder contract."""

    if isinstance(value, str):
        return parse_confirmed_intent_text(value, prompt=prompt, fallback_title=fallback_title)
    if not isinstance(value, Mapping):
        raise ValueError("confirmed intent must be Markdown text or a JSON object")
    envelope_facts = product_facts_from_envelope(value)
    if envelope_facts is not None:
        return normalize_confirmed_intent(envelope_facts, prompt=prompt, fallback_title=fallback_title)
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
        "first_path": _accepted_first_path(payload.get("first_path") or payload.get("first_workflow")),
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


def write_structured_confirmed_intent_file(
    path: Path,
    intent: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any] | None = None,
) -> Path:
    """Persist the normalized confirmed intent beside the human Markdown record."""

    target = structured_confirmed_intent_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(envelope) if isinstance(envelope, Mapping) else build_product_intent_envelope(intent)
    facts = product_facts_payload(intent)
    payload["product_facts"] = facts
    decision_record = dict(payload.get("decision_record")) if isinstance(payload.get("decision_record"), Mapping) else {}
    decision_record[PRODUCT_FACTS_HASH_KEY] = product_facts_hash(facts)
    payload["decision_record"] = decision_record
    payload = {**payload, **facts}
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _canonicalized_loaded_envelope(payload: Mapping[str, Any], intent: Mapping[str, Any]) -> dict[str, Any]:
    envelope = dict(payload)
    envelope["product_facts"] = product_facts_payload(intent)
    decision_record = dict(envelope.get("decision_record")) if isinstance(envelope.get("decision_record"), Mapping) else {}
    decision_record[PRODUCT_FACTS_HASH_KEY] = product_facts_hash(envelope["product_facts"])
    envelope["decision_record"] = decision_record
    return envelope


def _complete_confirmed_intent_before_validation(intent: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(intent)
    if _contains_meta_narration(result):
        return result
    if _contains_generic_system_scaffold(confirmed_text_values(result.get("internal_systems"))):
        return result
    return complete_confirmed_intent(result)


def parse_confirmed_intent_text(text: str, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Parse the human Product Intent Confirmation that the host already showed."""

    generated_confirmation = _looks_like_host_guidance_envelope(text)
    text = _recover_host_guidance_confirmation(text, prompt=prompt)
    sections = _sections(text)
    raw_title_candidate = _title_from_sections(sections) or _title_from_text(text) or _title_from_preamble(sections) or fallback_title
    if not _has_structured_body_sections(sections) and not _has_unheaded_confirmation_shape(
        text,
        sections,
        raw_title_candidate,
    ):
        thin_source = _thin_operator_intent_source(
            _thin_recovery_source_text(text, sections, raw_title_candidate),
            prompt=prompt,
        )
        if thin_source:
            text = confirmation_from_operator_intent(thin_source, prefer_product_title=True)
            generated_confirmation = True
            sections = _sections(text)
    raw_title = _title_from_sections(sections) or _title_from_text(text) or _title_from_preamble(sections) or fallback_title
    title_normalization = normalize_project_title(raw_title, fallback=fallback_title or "Greenfield Project")
    title = title_normalization.canonical_title
    preamble_story = _preamble_story(sections, title)
    preamble_paragraphs = _product_context_paragraphs(text, sections, title)
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
        "first_path": _accepted_first_path(_section_text(sections, "first_path") or derived_first_path),
        "proof_boundary": _section_text(sections, "proof_boundary") or derived_proof,
        "problem": _section_text(sections, "problem"),
        "customer": _section_text(sections, "customer"),
        "opportunity": _section_text(sections, "opportunity"),
        "product_view": _section_text(sections, "product_view"),
        "success_metrics": _section_list(sections, "success_metrics"),
        "component_responsibilities": _section_list(sections, "component_responsibilities"),
        "human_actors": _section_list(sections, "human_actors"),
        "external_systems": _section_list(sections, "external_systems")
        + _combined_system_rows(sections, "external", section_list=_section_list, section_text=_section_text),
        "internal_systems": [],
        "assumptions": _section_list(sections, "assumptions"),
        "ambiguities": _section_list(sections, "ambiguities"),
        "non_goals": _section_list(sections, "non_goals"),
    }
    _split_embedded_ambiguity_rows(result)
    if title_normalization.changed:
        result["source_title"] = title_normalization.raw_title
    result["internal_systems"] = _internal_system_rows(
        sections,
        section_list=_section_list,
        section_text=_section_text,
        context_text=_intent_context_text(result, strings=confirmed_text_values),
    )
    result = _restore_prompt_material_first_path(result, generated_confirmation=generated_confirmation)
    result = _complete_confirmed_intent_before_validation(result)
    _validate_confirmed_intent(result)
    return result


def _split_embedded_ambiguity_rows(intent: dict[str, Any]) -> None:
    non_goals: list[str] = []
    ambiguities = list(confirmed_text_values(intent.get("ambiguities")))
    changed = False
    for row in confirmed_text_values(intent.get("non_goals")):
        non_goal, ambiguity = _split_embedded_ambiguity(row)
        if non_goal:
            non_goals.append(non_goal)
        if ambiguity:
            ambiguities.append(ambiguity)
            changed = True
        changed |= bool(ambiguity)
    if changed:
        intent["non_goals"] = list(dict.fromkeys(non_goals))
        intent["ambiguities"] = list(dict.fromkeys(ambiguities))


def _split_embedded_ambiguity(value: str) -> tuple[str, str]:
    text = _clean(value).strip(" .")
    if not text:
        return "", ""
    match = re.search(
        r"\b(?:remaining\s+ambiguity|ambiguity|open\s+question|open\s+product\s+question)\s*:\s*",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text, ""
    return text[: match.start()].strip(" ."), text[match.end() :].strip(" .")


def _restore_prompt_material_first_path(
    intent: Mapping[str, Any],
    *,
    generated_confirmation: bool,
) -> dict[str, Any]:
    """Restore a richer prompt first path only for internally synthesized confirmations."""

    result = dict(intent)
    if not generated_confirmation:
        return result
    prompt_source = _clean(result.get("prompt"))
    if not prompt_source:
        return result
    prompt_first_path = _accepted_first_path(prompt_first_path_source(prompt_source))
    current_first_path = _accepted_first_path(result.get("first_path"))
    if not prompt_first_path or prompt_first_path.casefold() == current_first_path.casefold():
        return result
    prompt_model = first_path_model(prompt_first_path)
    current_model = first_path_model(current_first_path)
    if len(prompt_model.steps) < 2:
        return result
    source_terms = _material_prompt_terms(prompt_first_path)
    accepted_terms = _material_prompt_terms(
        " ".join(
            str(result.get(key) or "")
            for key in ("product_story", "state_object", "first_path", "proof_boundary")
        )
    )
    missing_terms = source_terms - accepted_terms
    lost_steps = len(prompt_model.steps) > max(1, len(current_model.steps))
    lost_material_terms = len(missing_terms) >= max(2, min(4, len(source_terms) // 4))
    if not (lost_steps or lost_material_terms):
        return result
    result["first_path"] = prompt_first_path
    return result


def _accepted_first_path(value: Any) -> str:
    return strip_requirement_control_tail(_clean_first_path(value))


def _material_prompt_terms(value: Any) -> set[str]:
    terms: set[str] = set()
    for term in _label_terms(value):
        for token in str(term).casefold().replace("-", " ").replace("/", " ").split():
            token = token.strip(".,:;()[]{}\"'")
            if len(token) < 4 or token in _PROMPT_MATERIAL_TERM_STOPWORDS:
                continue
            terms.add(token)
    return terms


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


def _thin_recovery_source_text(text: str, sections: Mapping[str, list[str]], title: str) -> str:
    if not _has_explicit_section_boundaries(sections):
        return _clean(text)
    paragraphs = _product_context_paragraphs(text, sections, title)
    title_text = _clean(title)
    source = _clean(". ".join([title_text, *paragraphs] if title_text else paragraphs))
    return source or _clean(text)


def _has_unheaded_confirmation_shape(text: str, sections: Mapping[str, list[str]], title: str) -> bool:
    paragraphs = _product_context_paragraphs(text, sections, title)
    if len(paragraphs) < 3:
        return False
    state = _derived_state_paragraph(paragraphs)
    first_path = _derived_first_path_paragraph(paragraphs)
    proof = _derived_proof_boundary_paragraph(paragraphs)
    story = _derived_product_story(paragraphs, state=state, first_path=first_path, proof_boundary=proof)
    return bool(state and first_path and story)


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


def _host_guidance_boundary_heading(line: str, normalized: str) -> bool:
    if normalized in _HOST_GUIDANCE_BOUNDARY_HEADINGS:
        return True
    if line.casefold().startswith("confirmed cli after confirmation:"):
        return True
    return bool(_heading_key(line) and normalized != "original user intent")


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


def _title_from_text(text: str) -> str:
    for raw_line in str(text or "").splitlines():
        raw = str(raw_line or "").strip()
        if not raw.startswith("#"):
            continue
        line = _clean(raw.lstrip("#").strip())
        candidate = title_from_product_intent_line(line)
        if candidate:
            return candidate
        candidate = _title_from_export_line(line)
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
        inline_heading = _inline_heading_value(line)
        if inline_heading:
            heading, value = inline_heading
            if heading == "title" and value:
                return value
            continue
        candidate = title_from_product_intent_line(line)
        if candidate:
            return candidate
        candidate = _title_from_export_line(line)
        if candidate:
            return candidate
        candidate = _title_from_is_for_line(line)
        if candidate:
            return candidate
        if _looks_like_bare_title(line):
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
    words = _label_terms(text)
    if not 1 <= len(words) <= 10:
        return False
    title_like_words = [
        word
        for word in str(text or "").split()
        if word.strip("()[]{}.,:;")
    ]
    title_like_count = sum(
        1
        for word in title_like_words
        if word.strip("()[]{}.,:;")[:1].isupper() or word.strip("()[]{}.,:;").isupper()
    )
    title_like = bool(title_like_words) and title_like_count >= max(1, len(title_like_words) - 1)
    lowered = text.casefold()
    if not title_like and re.search(
        r"\b(?:wants?|needs?|helps?|uses?|creates?|submits?|reviews?|records?|tracks?|decides?|should|must|can|will)\b",
        lowered,
    ):
        return False
    return True


def _title_from_is_for_line(value: str) -> str:
    text = _clean(value).strip()
    match = re.match(r"^(?P<title>[A-Z][A-Za-z0-9&/:' -]{3,90}?)\s+is\s+for\s+", text)
    if not match:
        return ""
    candidate = _clean(match.group("title")).strip(" .")
    words = _label_terms(candidate)
    if not 2 <= len(words) <= 10:
        return ""
    if not any(word[:1].isupper() or word.isupper() for word in candidate.split()):
        return ""
    return candidate


def _title_from_export_line(value: str) -> str:
    text = _clean(value).strip()
    match = re.match(
        r"^(?:deck\s+export|slide\s+deck|presentation|slides|document|source\s+document)\s+[—-]\s+(?P<title>.+)$",
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


def _section_text(sections: Mapping[str, list[str]], key: str) -> str:
    lines = sections.get(key, [])
    return _clean(
        " ".join(
            _strip_list_marker(line)
            for line in lines
            if line.strip() and not _looks_like_operator_instruction_line(_strip_list_marker(line))
        )
    )


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
        if _looks_like_operator_instruction_line(line):
            continue
        lines.append(line)
    return _clean(" ".join(lines))


def _product_context_paragraphs(text: str, sections: Mapping[str, list[str]], title: str) -> list[str]:
    if not _has_explicit_section_boundaries(sections):
        return _preamble_paragraphs(text, title)
    paragraphs: list[str] = []
    if sections.get("preamble"):
        paragraphs.extend(_preamble_paragraphs(_raw_preamble_text(text), title))
    rows: list[str] = []
    for key, lines in sections.items():
        if key == "preamble" or not _is_supporting_section(key):
            continue
        rows.extend(lines)
        rows.append("")
    paragraphs.extend(_paragraphs_from_lines(rows, title, keep_list_items=True))
    return _expand_narrative_cue_paragraphs(paragraphs)


def _raw_preamble_text(text: str) -> str:
    return re.split(r"(?m)^#{2,6}\s+", str(text or ""), maxsplit=1)[0]


def _has_explicit_section_boundaries(sections: Mapping[str, list[str]]) -> bool:
    return any(key != "preamble" for key in sections)


def _preamble_paragraphs(text: str, title: str) -> list[str]:
    rows: list[str] = []
    for raw in re.split(r"\n\s*\n+", str(text or "")):
        row_lines: list[str] = []
        for line in raw.splitlines():
            cleaned = _clean(line.lstrip("#").strip())
            if not cleaned:
                continue
            if _heading_key(line):
                continue
            if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line):
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
    if _word_count(text) < 35:
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
    rows: list[str] = []
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
    for row in (story, state, first_path, proof):
        cleaned = _clean(row).strip(" .")
        if cleaned and _word_count(cleaned) >= 6:
            rows.append(cleaned)
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
        if _heading_key(raw_text):
            continue
        list_item = re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", raw_text)
        if list_item and not keep_list_items:
            continue
        cleaned = _strip_list_marker(cleaned)
        if _looks_like_operator_instruction_line(cleaned):
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
    if not paragraph:
        return
    if title_text and paragraph.casefold() == title_text:
        return
    if _looks_like_operator_instruction_line(paragraph):
        return
    paragraphs.append(paragraph)


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
        or re.match(r"^(?:a|an|the)\s+[^.]{1,80}\b(?:can|must|should)\s+reproduce\b", text, re.IGNORECASE)
        or re.search(r"\breproduce\s+(?:the\s+)?(?:accepted|blocked|rejected|same)\b", text, re.IGNORECASE)
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


def _section_list(sections: Mapping[str, list[str]], key: str) -> list[str]:
    values: list[str] = []
    for raw_line in sections.get(key, []):
        text = raw_line.strip()
        if not text:
            continue
        item = _strip_list_marker(text)
        if _looks_like_operator_instruction_line(item):
            continue
        if item:
            values.append(_clean(item))
    if values:
        return values
    paragraph = _section_text(sections, key)
    return [paragraph] if paragraph else []


def _clean(value: object) -> str:
    return clean_markdown_text(value)


def _strip_list_marker(value: object) -> str:
    return re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(value or "")).strip()


def _looks_like_operator_instruction_line(value: str) -> bool:
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


__all__ = [
    "ConfirmedIntentRecord",
    "confirmed_intent_list",
    "confirmed_intent_product_facts",
    "confirmed_intent_summary",
    "confirmed_system_description",
    "confirmed_system_name",
    "load_confirmed_intent_file",
    "load_confirmed_intent_record",
    "normalize_confirmed_intent",
    "parse_confirmed_intent_text",
    "structured_confirmed_intent_path",
    "write_structured_confirmed_intent_file",
]
