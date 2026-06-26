"""Validation and rendering support for confirmed project briefs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import normalize_text_list
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


PROJECT_BRIEF_SCHEMA_VERSION = "odylith.greenfield.project_brief.v1"
PROJECT_OUTCOME_MIN_WORDS = 10
_PROJECT_OUTCOME_LIMIT = 300


def normalize_project_brief(
    value: Any,
    *,
    intent: Mapping[str, Any],
    release_selector: str,
) -> dict[str, Any]:
    """Normalize a proposal project brief without inventing beyond accepted intent."""

    if not isinstance(value, Mapping):
        return {}

    result = dict(value)
    result.setdefault("schema_version", PROJECT_BRIEF_SCHEMA_VERSION)
    result["project_outcome"] = project_outcome_text(
        result.get("project_outcome"),
        intent=intent,
        release_selector=release_selector,
    )
    result["blueprint_sections"] = _normalize_brief_rows(
        result.get("blueprint_sections"),
        required_keys=("section", "must_capture", "why_it_matters"),
    )
    result["customization_options"] = _normalize_brief_rows(
        result.get("customization_options") or result.get("direction_options"),
        required_keys=("id", "decision", "recommended", "choices", "impact"),
    )
    result["customization_prompts"] = normalize_text_list(result.get("customization_prompts"))
    result["pre_coding_checkpoints"] = _normalize_brief_rows(
        result.get("pre_coding_checkpoints") or result.get("checkpoints"),
        required_keys=("checkpoint", "operator_question", "done_when"),
    )
    result["coding_readiness_gates"] = normalize_text_list(result.get("coding_readiness_gates"))
    result["host_independent_paths"] = _normalize_brief_rows(
        result.get("host_independent_paths"),
        required_keys=("path", "command", "works_in", "use_when"),
    )
    return result


def project_outcome_text(
    value: Any,
    *,
    intent: Mapping[str, Any],
    release_selector: str = "",
    fallback: Any = "",
) -> str:
    """Return a release-outcome clause that satisfies the project-brief floor."""

    for candidate in _project_outcome_candidates(
        value,
        intent=intent,
        release_selector=release_selector,
        fallback=fallback,
    ):
        text = _brief_field_text(candidate, limit=_PROJECT_OUTCOME_LIMIT)
        text = _readable_project_outcome(text, intent=intent, release_selector=release_selector)
        if word_count(text) >= PROJECT_OUTCOME_MIN_WORDS:
            return text
    return _brief_field_text(value or fallback, limit=_PROJECT_OUTCOME_LIMIT)


def project_brief_issues(value: Any) -> list[str]:
    """Return validation issues for the proposal project-first brief."""

    issues: list[str] = []
    if not isinstance(value, Mapping):
        return ["proposal `project_brief` must be an object"]
    _require_text(value, "purpose", owner="proposal `project_brief`", issues=issues, min_words=10)
    _require_text(value, "operating_principle", owner="proposal `project_brief`", issues=issues, min_words=12)
    _require_text(value, "project_outcome", owner="proposal `project_brief`", issues=issues, min_words=10)
    _require_rows(
        value.get("blueprint_sections"),
        owner="proposal `project_brief.blueprint_sections`",
        issues=issues,
        min_rows=4,
        required_keys=("section", "must_capture", "why_it_matters"),
    )
    _require_rows(
        value.get("customization_options"),
        owner="proposal `project_brief.customization_options`",
        issues=issues,
        min_rows=5,
        required_keys=("id", "decision", "recommended", "choices", "impact"),
    )
    _require_rows(
        value.get("pre_coding_checkpoints"),
        owner="proposal `project_brief.pre_coding_checkpoints`",
        issues=issues,
        min_rows=4,
        required_keys=("checkpoint", "operator_question", "done_when"),
    )
    prompts = normalize_text_list(value.get("customization_prompts"))
    if len(prompts) < 3:
        issues.append("proposal `project_brief.customization_prompts` must include at least three host-independent examples")
    elif any(word_count(prompt) < 6 for prompt in prompts):
        issues.append("proposal `project_brief.customization_prompts` contains a shallow example")
    gates = normalize_text_list(value.get("coding_readiness_gates"))
    if len(gates) < 4:
        issues.append("proposal `project_brief.coding_readiness_gates` must include at least four gates")
    elif any(word_count(gate) < 6 for gate in gates):
        issues.append("proposal `project_brief.coding_readiness_gates` contains a shallow gate")
    _require_rows(
        value.get("host_independent_paths"),
        owner="proposal `project_brief.host_independent_paths`",
        issues=issues,
        min_rows=3,
        required_keys=("path", "command", "works_in", "use_when"),
    )
    return issues


def _project_outcome_candidates(
    value: Any,
    *,
    intent: Mapping[str, Any],
    release_selector: str,
    fallback: Any,
) -> list[str]:
    existing = clean_text(value)
    proof_boundary = clean_text(intent.get("proof_boundary"))
    first_path = clean_text(intent.get("first_path"))
    state_object = clean_text(intent.get("state_object"))
    title = clean_text(intent.get("title") or intent.get("source_title"))
    release = clean_text(release_selector) or "the first release"
    candidates: list[str] = [existing]
    candidates.extend(_sentence_candidates(proof_boundary))
    candidates.append(_brief_field_text(proof_boundary, limit=_PROJECT_OUTCOME_LIMIT))
    if first_path and proof_boundary:
        candidates.append(f"{first_path} Proof remains bounded to {proof_boundary}")
    if first_path:
        candidates.append(
            f"Release {release} is ready when the accepted first path is complete, reviewable, "
            f"and backed by evidence: {first_path}"
        )
    if proof_boundary:
        candidates.append(
            f"Release {release} is ready only when the accepted proof boundary is visible and reviewable: "
            f"{proof_boundary}"
        )
    if state_object:
        candidates.append(
            f"Release {release} must leave {state_object} reviewable with evidence for the accepted first path."
        )
    if title:
        candidates.append(
            f"Release {release} proves the accepted {title} direction through one reviewable first path."
        )
    candidates.append(clean_text(fallback))
    return unique_text(candidates)


def _sentence_candidates(value: str) -> list[str]:
    sentences = _split_sentences(value)
    candidates: list[str] = [*sentences]
    for index in range(len(sentences) - 1):
        candidates.append(f"{sentences[index]} {sentences[index + 1]}")
    return candidates


def _split_sentences(value: str) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    for marker in (".", "!", "?"):
        text = text.replace(f"{marker} ", f"{marker}\n")
    return [part.strip(" .!?") for part in text.splitlines() if part.strip(" .!?")]


def _brief_field_text(value: Any, *, limit: int) -> str:
    text = clean_text(value).strip(" .")
    if len(text) <= limit:
        return text
    return clip_text_at_word_boundary(text, limit=limit).strip(" .")


def _readable_project_outcome(value: str, *, intent: Mapping[str, Any], release_selector: str) -> str:
    text = clean_text(value).strip(" .")
    if text.count(",") < 5 and len(text) <= _PROJECT_OUTCOME_LIMIT:
        return text
    title = clean_text(intent.get("title") or intent.get("source_title")) or "the accepted project"
    state_object = _brief_state_label(clean_text(intent.get("state_object")) or "the product state")
    release = clean_text(release_selector) or "the first release"
    return (
        f"Release {release} proves one accepted {title} path. "
        f"The visible result and {state_object} stay connected with blocked-path and review evidence."
    )


def _brief_state_label(value: str) -> str:
    text = clean_text(value).strip(" .")
    label = domain_object_label(text, fallback="")
    if label:
        return label
    parts = list(text_values(text, split_scalar=True, split_commas=True))
    if len(parts) >= 3:
        return parts[0]
    return text or "the product state"


def render_project_brief_lines(project_brief: Mapping[str, Any]) -> list[str]:
    """Render the project-first brief used in proposal review text."""

    if not project_brief:
        return []
    lines: list[str] = []
    principle = clean_text(project_brief.get("operating_principle"))
    outcome = clean_text(project_brief.get("project_outcome"))
    posture = clean_text(project_brief.get("review_posture"))
    if outcome:
        lines.append(f"- outcome: {outcome}")
    if principle:
        lines.append(f"- principle: {principle}")
    if posture:
        lines.append(f"- review posture: {posture}")
    blueprint_lines = _blueprint_section_lines(project_brief.get("blueprint_sections"))
    if blueprint_lines:
        _append_section(lines, "## Project Design Board")
        lines.extend(f"- {line}" for line in blueprint_lines[:7])
    option_lines = _project_option_lines(project_brief.get("customization_options"))
    prompt_lines = _text_list_lines(project_brief.get("customization_prompts"))
    checkpoint_lines = _project_checkpoint_lines(project_brief.get("pre_coding_checkpoints"))
    gates = _text_list_lines(project_brief.get("coding_readiness_gates"))
    paths = _project_path_lines(project_brief.get("host_independent_paths"))
    if option_lines or prompt_lines or checkpoint_lines or gates or paths:
        _append_section(lines, "## Governance Package")
    if option_lines:
        lines.extend(["- choose before coding:"])
        lines.extend(f"  - {line}" for line in option_lines[:8])
    if prompt_lines:
        lines.extend(["- customize by saying:"])
        lines.extend(f"  - {line}" for line in prompt_lines[:4])
    if checkpoint_lines:
        lines.extend(["- checkpoints:"])
        lines.extend(f"  - {line}" for line in checkpoint_lines[:5])
    if gates:
        lines.extend(["- coding readiness gates:"])
        lines.extend(f"  - {gate}" for gate in gates[:5])
    if paths:
        lines.extend(["- host-independent customization paths:"])
        lines.extend(f"  - {line}" for line in paths[:3])
    return lines


def _append_section(lines: list[str], heading: str) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(heading)


def _normalize_brief_rows(value: Any, *, required_keys: Sequence[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        if any(_has_text_or_list(row.get(key)) for key in required_keys):
            rows.append(row)
    return rows


def _has_text_or_list(value: Any) -> bool:
    if isinstance(value, list):
        return any(clean_text(item) for item in value)
    return bool(clean_text(value))


def _require_rows(
    value: Any,
    *,
    owner: str,
    issues: list[str],
    min_rows: int,
    required_keys: Sequence[str],
) -> None:
    if not isinstance(value, list) or len(value) < min_rows:
        issues.append(f"{owner} must include at least {min_rows} rows")
        return
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            issues.append(f"{owner}[{index}] must be an object")
            continue
        for key in required_keys:
            if not _has_text_or_list(raw.get(key)):
                issues.append(f"{owner}[{index}] `{key}` must be non-empty")


def _require_text(value: Mapping[str, Any], key: str, *, owner: str, issues: list[str], min_words: int) -> None:
    text = clean_text(value.get(key))
    if not text:
        issues.append(f"{owner} `{key}` must be non-empty")
        return
    if word_count(text) < min_words:
        issues.append(f"{owner} `{key}` must contain at least {min_words} meaningful words")


def _blueprint_section_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        section = clean_text(row.get("section"))
        must_capture = clean_text(row.get("must_capture"))
        why = clean_text(row.get("why_it_matters"))
        if section and must_capture:
            detail_parts = _long_detail_parts(must_capture)
            if detail_parts:
                block = [f"{section}:", *(f"  - {part}" for part in detail_parts[:6])]
                if why:
                    block.append(f"  - Why: {why}")
                lines.append("\n".join(block))
                continue
            if why and _combined_detail_is_hard_to_scan(section=section, detail=must_capture, why=why):
                lines.append("\n".join([f"{section}: {must_capture}", f"  - Why: {why}"]))
                continue
            suffix = f" Why: {why}" if why else ""
            lines.append(f"{section}: {must_capture}{suffix}")
    return lines


def _combined_detail_is_hard_to_scan(*, section: str, detail: str, why: str) -> bool:
    combined = f"{section}: {detail} Why: {why}"
    return len(combined) > 260 or (combined.count(",") >= 6 and len(combined) > 180)


def _long_detail_parts(value: str) -> list[str]:
    text = clean_text(value)
    has_long_comma_list = len(text) > 220 and text.count(",") >= 4
    if len(text) <= 320 and text.count(";") < 3 and not has_long_comma_list:
        return []
    candidates: list[str] = []
    for sentence in text.split(". "):
        candidates.extend(text_values(sentence, split_scalar=True, split_commas=False))
    parts = [part.strip(" .") for part in candidates if part.strip(" .")]
    return [part for part in (_brief_list_fragment(part) for part in parts) if word_count(part) >= 3]


def _project_option_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        decision = clean_text(row.get("decision"))
        recommended = clean_text(row.get("recommended"))
        choices = row.get("choices", [])
        rendered_choices = (
            ", ".join(clean_text(item) for item in choices if clean_text(item))
            if isinstance(choices, list)
            else clean_text(choices)
        )
        impact = clean_text(row.get("impact"))
        if decision and recommended:
            block = _option_line_block(
                decision=decision,
                recommended=recommended,
                rendered_choices=rendered_choices,
                impact=impact,
            )
            if block:
                lines.append(block)
    return lines


def _option_line_block(*, decision: str, recommended: str, rendered_choices: str, impact: str) -> str:
    detail_parts = _long_detail_parts(recommended)
    if detail_parts:
        rows = [f"{decision}:", *(f"    - {part}" for part in detail_parts[:6])]
    else:
        rows = [f"{decision}: {recommended}"]
    if rendered_choices:
        rows.append(f"    - Options: {rendered_choices}.")
    if impact:
        rows.append(f"    - Impact: {impact}")
    return "\n".join(rows)


def _text_list_lines(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [line for line in (_brief_list_fragment(clean_text(item)) for item in value) if line]


def _brief_list_fragment(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    lowered = text.casefold()
    for connector in ("and", "then", "or", "but"):
        prefix = f"{connector} "
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip(" .")
            break
    lowered = text.casefold()
    broader_prefix = "broader operational scale until "
    if lowered.startswith(broader_prefix):
        return f"Broader operational scale stays deferred until {text[len(broader_prefix):].strip(' .')}"
    operational_prefix = "operational scale until "
    if lowered.startswith(operational_prefix):
        return f"Operational scale stays deferred until {text[len(operational_prefix):].strip(' .')}"
    return f"{text[:1].upper()}{text[1:]}" if text and text[:1].islower() else text


def _project_checkpoint_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        checkpoint = clean_text(row.get("checkpoint"))
        question = clean_text(row.get("operator_question"))
        done_when = clean_text(row.get("done_when"))
        if checkpoint and question:
            question_text = question.rstrip(".?!")
            done_text = _checkpoint_done_when_fragment(done_when)
            lines.append(f"{checkpoint}: {question_text}; done when {done_text}.")
    return lines


def _checkpoint_done_when_fragment(value: str) -> str:
    text = clean_text(value).strip(" .?!")
    return re.sub(r"^done\s+when\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .?!")


def _project_path_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        path = clean_text(row.get("path"))
        command = clean_text(row.get("command"))
        works_in = clean_text(row.get("works_in"))
        if path and command:
            lines.append(f"{path}: `{command}` ({works_in})")
    return lines


__all__ = [
    "PROJECT_BRIEF_SCHEMA_VERSION",
    "normalize_project_brief",
    "project_brief_issues",
    "render_project_brief_lines",
]
