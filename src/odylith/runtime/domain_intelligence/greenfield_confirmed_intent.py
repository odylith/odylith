"""Parse the small confirmed-intent artifact used by greenfield create."""

from __future__ import annotations

import json
import re
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import (
    contains_meta_narration as _contains_meta_narration,
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    derived_first_path_paragraph as _derived_first_path_paragraph,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    derived_product_story as _derived_product_story,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    derived_proof_boundary_paragraph as _derived_proof_boundary_paragraph,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    derived_state_paragraph as _derived_state_paragraph,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    has_explicit_section_boundaries as _has_explicit_section_boundaries,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    looks_like_operator_instruction_line as _looks_like_operator_instruction_line,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    preamble_story as _preamble_story,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    product_context_paragraphs as _product_context_paragraphs,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    strip_list_marker as _strip_list_marker,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    title_from_preamble as _title_from_preamble,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    title_from_sections as _title_from_sections,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import (
    title_from_text as _title_from_text,
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
    product_facts_hash,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_payload,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_heading_key as _heading_key,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import (
    confirmed_intent_sections as _sections,
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
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import has_presentation_only_title_marker
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


def is_host_guidance_envelope(value: str) -> bool:
    """Return whether input is a host-control envelope rather than product evidence."""

    return _looks_like_host_guidance_envelope(value)


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
        verified_markdown = _verified_markdown_source_for_json(source, payload)
        if verified_markdown:
            markdown_path, markdown_text = verified_markdown
            intent = parse_confirmed_intent_text(
                markdown_text,
                prompt=prompt,
                fallback_title=fallback_title,
                _allow_prompt_validation_recovery=False,
            )
            envelope = build_product_intent_envelope(
                intent,
                source_text=markdown_text,
                source_path=markdown_path,
                source_format="markdown",
            )
            return ConfirmedIntentRecord(product_facts=intent, envelope=envelope)
        if is_product_intent_envelope(payload):
            raise ValueError(
                "confirmed intent JSON envelope could not be verified against its recorded Markdown source"
            )
        intent = normalize_confirmed_intent(
            _json_projection_payload(payload),
            prompt=prompt,
            fallback_title=fallback_title,
            allow_prompt_validation_recovery=False,
        )
        envelope = build_product_intent_envelope(
            intent,
            source_text=text,
            source_path=source,
            source_format="json",
        )
        return ConfirmedIntentRecord(product_facts=intent, envelope=envelope)
    intent = parse_confirmed_intent_text(
        text,
        prompt=prompt,
        fallback_title=fallback_title,
        _allow_prompt_validation_recovery=False,
    )
    source_sections = _sections(text)
    source_format = (
        "operator_prompt"
        if not _has_explicit_section_boundaries(source_sections) and _thin_operator_intent_source(text, prompt="")
        else "markdown"
    )
    envelope = build_product_intent_envelope(
        intent,
        source_text=text,
        source_path=source,
        source_format=source_format,
    )
    return ConfirmedIntentRecord(product_facts=intent, envelope=envelope)


def confirmed_intent_product_facts(record: ConfirmedIntentRecord | Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical product facts from a record or legacy mapping."""

    if isinstance(record, ConfirmedIntentRecord):
        return dict(record.product_facts)
    return dict(record)


def normalize_confirmed_intent(
    value: object,
    *,
    prompt: str = "",
    fallback_title: str = "",
    allow_prompt_validation_recovery: bool = True,
) -> dict[str, Any]:
    """Normalize JSON or already parsed confirmation data into the builder contract."""

    if isinstance(value, str):
        return parse_confirmed_intent_text(
            value,
            prompt=prompt,
            fallback_title=fallback_title,
            _allow_prompt_validation_recovery=allow_prompt_validation_recovery,
        )
    if not isinstance(value, Mapping):
        raise ValueError("confirmed intent must be Markdown text or a JSON object")
    payload = _json_projection_payload(value) if is_product_intent_envelope(value) else dict(value)
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
        "evidence_requirements": confirmed_text_values(payload.get("evidence_requirements")),
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
    if title_normalization.changed and not has_presentation_only_title_marker(title_normalization.raw_title):
        result["source_title"] = title_normalization.raw_title
    result["internal_systems"] = _expand_internal_system_rows(
        _preferred_internal_rows(
            _role_or_system_rows(payload.get("internal_systems") or payload.get("internal_product_systems")),
            component_rows,
        ),
        context_text=_intent_context_text(result, strings=confirmed_text_values),
    )
    result = _complete_confirmed_intent_before_validation(result)
    return _validate_or_prompt_recover_intent(
        result,
        prompt=prompt,
        fallback_title=fallback_title,
        allow_prompt_recovery=allow_prompt_validation_recovery,
    )


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


def _verified_markdown_source_for_json(source: Path, payload: object) -> tuple[Path, str] | None:
    if not is_product_intent_envelope(payload) or not isinstance(payload, Mapping):
        return None
    evidence = payload.get("source_evidence")
    if not isinstance(evidence, Mapping):
        return None
    expected_hash = _clean(evidence.get("source_sha256"))
    if not expected_hash:
        return None
    candidates: list[Path] = []
    source_path = _clean(evidence.get("source_path"))
    if source_path:
        candidate = Path(source_path)
        candidates.append(candidate if candidate.is_absolute() else source.parent / candidate)
    candidates.extend([source.with_suffix(".md"), source.with_suffix(".markdown")])
    seen: set[Path] = set()
    for candidate in candidates:
        path = candidate.expanduser()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        if path.resolve() == source.resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if hashlib.sha256(text.encode("utf-8")).hexdigest() == expected_hash:
            return path, text
    return None


def _json_projection_payload(payload: object) -> object:
    if not isinstance(payload, Mapping):
        return payload
    result = dict(payload)
    for key in (
        "schema_version",
        "product_facts",
        "custody_ledger",
        "source_evidence",
        "materiality_gate",
        "decision_record",
    ):
        result.pop(key, None)
    return result


def _complete_confirmed_intent_before_validation(intent: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(intent)
    if _contains_meta_narration(result):
        return result
    if _contains_generic_system_scaffold(confirmed_text_values(result.get("internal_systems"))):
        return result
    return complete_confirmed_intent(result)


def parse_confirmed_intent_text(
    text: str,
    *,
    prompt: str = "",
    fallback_title: str = "",
    _allow_prompt_validation_recovery: bool = True,
) -> dict[str, Any]:
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
        "evidence_requirements": _section_list(sections, "evidence_requirements"),
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
    if title_normalization.changed and not has_presentation_only_title_marker(title_normalization.raw_title):
        result["source_title"] = title_normalization.raw_title
    result["internal_systems"] = _internal_system_rows(
        sections,
        section_list=_section_list,
        section_text=_section_text,
        context_text=_intent_context_text(result, strings=confirmed_text_values),
    )
    result = _restore_prompt_material_first_path(result, generated_confirmation=generated_confirmation)
    result = _complete_confirmed_intent_before_validation(result)
    return _validate_or_prompt_recover_intent(
        result,
        prompt=prompt,
        fallback_title=fallback_title,
        allow_prompt_recovery=_allow_prompt_validation_recovery,
    )


def _validate_or_prompt_recover_intent(
    intent: dict[str, Any],
    *,
    prompt: str,
    fallback_title: str,
    allow_prompt_recovery: bool,
) -> dict[str, Any]:
    try:
        _validate_confirmed_intent(intent)
    except ValueError as exc:
        if allow_prompt_recovery:
            source = _thin_operator_intent_source(prompt, prompt="")
            if source:
                try:
                    return parse_confirmed_intent_text(
                        confirmation_from_operator_intent(source, prefer_product_title=True),
                        prompt=source,
                        fallback_title=fallback_title,
                        _allow_prompt_validation_recovery=False,
                    )
                except ValueError:
                    pass
        raise _material_intent_blocker(exc) from exc
    return intent


def _material_intent_blocker(error: ValueError) -> ValueError:
    detail = _clean(str(error))
    suffix = f" Material gaps: {detail}" if detail else ""
    return ValueError(
        "Odylith needs one material product decision before it can compile a create transaction: "
        "who uses the product, what state changes, what first path completes, and what visible proof counts. "
        "Provide that as normal text; do not repair JSON or schema fields."
        + suffix
    )


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



def _section_text(sections: Mapping[str, list[str]], key: str) -> str:
    lines = sections.get(key, [])
    return _clean(
        " ".join(
            _strip_list_marker(line)
            for line in lines
            if line.strip() and not _looks_like_operator_instruction_line(_strip_list_marker(line))
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
