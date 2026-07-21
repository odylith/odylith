"""Materialize prompt-only greenfield intent into typed custody files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import normalize_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import PRECONFIRM_STAGING_MARKER
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_typed_candidate_intent_files
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import (
    intent_hypothesis_from_operator_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import (
    internal_system_rows_from_recovered_title,
)
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_automated_actor
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_has_material_first_path_gap
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import confirmed_intent_sections
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import is_noncompleting_action_head
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import (
    proof_boundary_with_first_release_requirements,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_action_split import split_action_pieces
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraints_after_first_path_edit
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materiality import (
    title_supports_conservative_first_path,
)


_CONCRETE_DEVICE_BEHAVIOR_RE = re.compile(
    r"\b(?:device|controller|sensor|monitor)\b[^.!?]{0,160}\bthat\s+[a-z]",
    flags=re.IGNORECASE,
)
_ACTOR_MODAL_SUFFIX_RE = re.compile(r"\b(?:can|could|should|must|will)$", flags=re.IGNORECASE)


class GreenfieldClarificationRequired(ValueError):
    """A user decision is needed before a create transaction can be compiled."""

    def __init__(self, question: str, *, required_fields: tuple[str, ...] = ("first_path",)) -> None:
        super().__init__(question)
        self.question = question
        self.required_fields = required_fields


_ANAPHORIC_FIRST_PATH_ACTOR_RE = re.compile(
    r"^(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+"
    r"(?:can|should|must|needs?\s+to)\s+(?:complete|own|handle)\s+"
    r"(?:it|this|that|the\s+(?:first\s+)?(?:path|workflow|release))\.?$",
    flags=re.IGNORECASE,
)


def materialize_prompt_confirmed_intent(
    *,
    prompt: str,
    repo_root: Path,
    fallback_title: str,
) -> dict[str, Any]:
    """Persist prompt-only intent as Markdown plus typed JSON before transaction compile."""

    if not prompt or prompt == "new project":
        raise prompt_only_material_decision_error()
    try:
        intent = parse_confirmed_intent_text(prompt, prompt=prompt, fallback_title=fallback_title)
    except ValueError as exc:
        raise prompt_only_material_decision_error() from exc
    root = Path(repo_root).expanduser().resolve()
    path = root / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    atomic_write_text(path, _render_confirmed_intent_markdown(intent), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt=prompt, fallback_title=fallback_title)
    structured_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    authority = product_intent_authority_from_envelope(
        record.envelope,
        structured_intent_path=structured_path,
        markdown_source_path=path,
    )
    require_product_intent_authority(authority)
    accepted = dict(record.product_facts)
    accepted[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    return accepted


def materialize_prompt_intent_hypothesis(
    *,
    prompt: str,
    repo_root: Path,
    fallback_title: str,
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Stage a typed intent hypothesis from raw prompt and optional edit evidence."""

    if not prompt.strip():
        raise prompt_only_material_decision_error()
    raw_edit = _without_edit_command(edit_evidence)
    if _requires_first_path_clarification(prompt=prompt, edit_evidence=raw_edit):
        raise prompt_only_material_decision_error()
    baseline = normalize_confirmed_intent(
        intent_hypothesis_from_operator_evidence(prompt, prefer_product_title=True),
        prompt=prompt,
        fallback_title=fallback_title,
        allow_prompt_validation_recovery=False,
    )
    uses_title_only_first_path_hypothesis = _uses_title_only_first_path_hypothesis(
        prompt=prompt,
        edit_evidence=raw_edit,
    )
    if uses_title_only_first_path_hypothesis:
        _add_title_hypothesis_assumption(baseline)
    root = Path(repo_root).expanduser().resolve()
    intent = _merge_edit_evidence(
        baseline=baseline,
        prompt=prompt,
        edit_evidence=raw_edit,
        fallback_title=fallback_title,
    )
    if uses_title_only_first_path_hypothesis:
        _add_title_hypothesis_assumption(intent)
    path = root / ".odylith" / "runtime" / "greenfield" / "candidate-intent.md"
    atomic_write_text(
        path,
        f"{PRECONFIRM_STAGING_MARKER}\n{_render_confirmed_intent_markdown(intent)}",
        encoding="utf-8",
    )
    evidence_path = root / ".odylith" / "runtime" / "greenfield" / "candidate-evidence.md"
    prompt_evidence_path = root / ".odylith" / "runtime" / "greenfield" / "operator-prompt.txt"
    atomic_write_text(prompt_evidence_path, prompt.strip() + "\n", encoding="utf-8")
    if raw_edit:
        edit_evidence_path = root / ".odylith" / "runtime" / "greenfield" / "edit-evidence.md"
        atomic_write_text(edit_evidence_path, raw_edit + "\n", encoding="utf-8")
    evidence_source = combined_prompt_evidence_source(prompt=prompt, edit_evidence=raw_edit)
    atomic_write_text(evidence_path, evidence_source, encoding="utf-8")
    from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope

    envelope = build_product_intent_envelope(
        intent,
        source_text=evidence_source,
        source_path=evidence_path,
        source_format="operator_prompt_with_edit_evidence" if raw_edit else "operator_prompt",
    )
    envelope["source_evidence"]["evidence_sources"] = [
        {"source_id": "operator_prompt", "source_path": str(prompt_evidence_path)},
        *(
            [{"source_id": "operator_edit", "source_path": str(edit_evidence_path)}]
            if raw_edit
            else []
        ),
    ]
    structured_path, _evidence_ledger_path = write_typed_candidate_intent_files(
        path,
        intent,
        envelope=envelope,
        evidence_path=root / ".odylith" / "runtime" / "greenfield" / "candidate-evidence.v1.json",
    )
    authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=structured_path,
        markdown_source_path=evidence_path,
    )
    require_product_intent_authority(authority)
    candidate = dict(intent)
    candidate[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    return candidate


def render_product_intent_preview(intent: Mapping[str, Any]) -> str:
    """Render the typed candidate that directly supplies the compiled transaction."""

    return _render_confirmed_intent_markdown(intent).replace(
        "Product Intent Confirmation", "Product Intent Preview", 1
    )


def prompt_only_material_decision_error() -> GreenfieldClarificationRequired:
    return GreenfieldClarificationRequired(
        "What is the first complete task the product should help a person finish, and what result should they see?"
    )


def _requires_first_path_clarification(*, prompt: str, edit_evidence: str) -> bool:
    """Ask only when the supplied evidence has no usable first user path."""

    edit_sections = confirmed_intent_sections(edit_evidence)
    edited_first_path = _section_first_path_text(edit_sections)
    if edited_first_path and not _anaphoric_first_path_actor(edited_first_path):
        return not _has_usable_first_path_evidence(edit_evidence)
    if edit_evidence.strip() and _has_usable_first_path_evidence(edit_evidence):
        return False
    evidence_rows = tuple(value for value in (prompt, edit_evidence) if value.strip())
    if any(prompt_has_material_first_path_gap(value) for value in evidence_rows):
        return True
    return not any(
        _has_usable_first_path_evidence(value) or _title_supports_first_path_hypothesis(value)
        for value in evidence_rows
    )


def _uses_title_only_first_path_hypothesis(*, prompt: str, edit_evidence: str) -> bool:
    evidence = tuple(value for value in (prompt, edit_evidence) if value.strip())
    return not any(_has_usable_first_path_evidence(value) for value in evidence) and any(
        _title_supports_first_path_hypothesis(value) for value in evidence
    )


def _title_supports_first_path_hypothesis(evidence: str) -> bool:
    source = prompt_intent_source(evidence)
    return title_supports_conservative_first_path(title=source.title, evidence=evidence)


def _add_title_hypothesis_assumption(intent: dict[str, Any]) -> None:
    assumption = "The product title supplies the initial first-path hypothesis for this proposal."
    assumptions = confirmed_text_values(intent.get("assumptions"))
    if assumption not in assumptions:
        intent["assumptions"] = [*assumptions, assumption]


def _has_usable_first_path_evidence(evidence: str) -> bool:
    sections = confirmed_intent_sections(evidence)
    source = prompt_intent_source(evidence)
    path_source = _section_first_path_text(sections) or source.first_path
    path = first_path_model(path_source)
    if _CONCRETE_DEVICE_BEHAVIOR_RE.search(evidence):
        return True
    return len(path.steps) >= 2 or _has_explicit_single_step_actor_action(path_source)


def _has_explicit_single_step_actor_action(path_source: str) -> bool:
    """Accept one complete actor-action path without accepting a product noun phrase."""

    actor, action = actor_led_action_parts(path_source)
    if not actor or not action:
        return False
    actor_without_modal = _ACTOR_MODAL_SUFFIX_RE.sub("", actor).strip()
    actor_words = tuple(word.casefold().strip(".,;:()[]{}") for word in actor_without_modal.split())
    if is_automated_actor(actor_without_modal):
        return False
    has_human_role = any(
        word_has_actor_role_signal(word)
        or looks_actor_term(word[:-1] if word.casefold().endswith("s") else word)
        for word in actor_words
    )
    action_head = action.split(maxsplit=1)[0].casefold()
    return (
        has_human_role
        and not is_noncompleting_action_head(action_head)
        and bool(MATERIAL_ACTION_RE.match(action))
    )


def _section_first_path_text(sections: Mapping[str, Any]) -> str:
    return " ".join(confirmed_text_values(sections.get("first_path"))).strip()


def _anaphoric_first_path_actor(value: str) -> str:
    match = _ANAPHORIC_FIRST_PATH_ACTOR_RE.fullmatch(str(value or "").strip())
    return _sentence_start(match.group("actor")) if match else ""


def _render_confirmed_intent_markdown(intent: Mapping[str, Any]) -> str:
    title = str(intent.get("title") or "Greenfield Project").strip()
    lines = [
        f"# {title} - Product Intent Confirmation",
        "",
        "## Product story",
        str(intent.get("product_story") or "").strip(),
        "",
        "## State object",
        str(intent.get("state_object") or "").strip(),
        "",
        "## First complete path",
        str(intent.get("first_path") or "").strip(),
        "",
        "## Operational constraints",
        *_bullet_lines(
            intent.get("operational_constraints"),
            empty_text="No site or time constraint narrows the first proof path.",
        ),
        "",
        "## Human actors",
        *_bullet_lines(intent.get("human_actors"), empty_text="Primary user: completes the first proof path."),
        "",
        "## External systems",
        *_bullet_lines(
            intent.get("external_systems"),
            empty_text="No external systems are required for the first proof path.",
        ),
        "",
        "## Internal product systems",
        *_bullet_lines(intent.get("internal_systems"), empty_text="Core workspace: owns the first path state and proof."),
        "",
        "## Critical assumptions",
        *_bullet_lines(
            intent.get("assumptions"),
            empty_text="Release 0.0.1 proves one complete path before broader automation.",
        ),
        "",
        "## Ambiguities",
        *_bullet_lines(intent.get("ambiguities"), empty_text="No material ambiguity blocks the first proof path."),
        "",
        "## Proof boundary",
        str(intent.get("proof_boundary") or "").strip(),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _bullet_lines(value: Any, *, empty_text: str) -> list[str]:
    rows = confirmed_text_values(value)
    return [f"- {row}" for row in rows] if rows else [f"- {empty_text}"]


def _merge_edit_evidence(
    *,
    baseline: Mapping[str, Any],
    prompt: str,
    edit_evidence: str,
    fallback_title: str,
) -> dict[str, Any]:
    if not edit_evidence:
        return dict(baseline)
    sections = confirmed_intent_sections(edit_evidence)
    overrides = _explicit_edit_overrides(sections)
    actor_correction = _anaphoric_first_path_actor(_section_first_path_text(sections))
    if actor_correction:
        overrides.pop("first_path", None)
        overrides.update(_first_path_actor_overrides(actor=actor_correction, baseline=baseline))
    document_title = _document_title_override(edit_evidence)
    if document_title and "title" not in overrides:
        overrides["title"] = document_title
    plain_language_recovery = False
    if not overrides:
        overrides = _plain_language_edit_overrides(edit_evidence, baseline=baseline)
        plain_language_recovery = bool(overrides)
    if not overrides:
        raise ValueError(
            "What should change about the first complete path? "
            "Describe that correction in normal product language."
        )
    title_override = str(overrides.get("title") or "").strip()
    title_only_rebuild = bool(title_override and "first_path" not in overrides)
    if title_only_rebuild:
        merged = _recompile_title_only_baseline(title=title_override)
    else:
        merged = dict(baseline)
    if plain_language_recovery:
        _clear_first_path_derivatives(merged)
    elif _material_edit_rebuilds_dependent_facts(overrides) and not title_only_rebuild:
        _clear_stale_baseline_derivatives(merged, overrides=overrides)
        if "first_path" in overrides and _requires_first_path_clarification(prompt=prompt, edit_evidence=""):
            merged = _recompile_unusable_baseline_from_first_path(
                baseline=baseline,
                prompt=prompt,
                first_path=overrides["first_path"],
                title=str(overrides.get("title") or baseline.get("title") or "").strip(),
            )
    _rebuild_operational_constraints_after_first_path_edit(merged, overrides=overrides)
    merged.update(overrides)
    normalized = normalize_confirmed_intent(
        merged,
        prompt=prompt,
        fallback_title=fallback_title,
        allow_prompt_validation_recovery=False,
    )
    return normalized


def _explicit_edit_overrides(sections: Mapping[str, list[str]]) -> dict[str, Any]:
    editable = {
        "title",
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
        "evidence_requirements",
        "operational_constraints",
    }
    list_fields = {
        "success_metrics",
        "component_responsibilities",
        "human_actors",
        "external_systems",
        "internal_systems",
        "assumptions",
        "ambiguities",
        "non_goals",
        "evidence_requirements",
        "operational_constraints",
    }
    overrides: dict[str, Any] = {}
    for field, rows in sections.items():
        values = _edit_evidence_values(rows)
        if field not in editable:
            continue
        if field == "operational_constraints" and _explicitly_clears_operational_constraints(values):
            overrides[field] = []
            continue
        if not values:
            continue
        overrides[field] = values if field in list_fields else " ".join(values)
    return overrides


def _edit_evidence_values(rows: object) -> list[str]:
    values: list[str] = []
    for value in confirmed_text_values(rows):
        cleaned = re.sub(r"^\s*[-*]\s+", "", value).strip()
        if cleaned:
            values.append(cleaned)
    return values


def _explicitly_clears_operational_constraints(values: list[str]) -> bool:
    return bool(
        values
        and all(
            value.casefold().strip(" .")
            in {"none", "no constraints", "no operational constraints"}
            for value in values
        )
    )


def _document_title_override(value: str) -> str:
    """Recover an explicit document title when a normal-language EDIT supplies one."""

    for line in str(value or "").splitlines():
        match = re.match(r"^\s*#\s+(?P<title>.+?)\s*$", line)
        if not match:
            continue
        title = match.group("title").strip(" .")
        if title.casefold() not in {"product intent confirmation", "product intent preview"}:
            return title
    return ""


def _plain_language_edit_overrides(
    edit_evidence: str,
    *,
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover a direct actor-and-action correction without requiring Markdown headings.

    The correction remains untrusted evidence. This intentionally recognizes
    only a complete, user-visible action clause; vague edits still receive one
    focused materiality question instead of overwriting product facts.
    """

    text = " ".join(str(edit_evidence or "").split()).strip(" .")
    if not text:
        return {}
    match = re.fullmatch(
        r"(?:make|use|have)\s+(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+"
        r"(?:be\s+)?(?:the\s+(?:people|team|role|roles)\s+)?who\s+(?P<action>[A-Za-z][A-Za-z0-9 /&'(),-]{3,})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        actor = _sentence_start(match.group("actor"))
        action = match.group("action").strip(" .")
        if actor and action:
            return _first_path_actor_overrides(actor=actor, baseline=baseline, action=action)
    ownership_match = re.fullmatch(
        r"(?:the\s+)?first(?:\s+complete)?\s+path\s+(?:should|must|needs?\s+to)\s+"
        r"be\s+(?:completed|owned|handled)\s+by\s+(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)"
        r"(?:\s+(?:rather|instead)\s+than\s+[A-Za-z][A-Za-z0-9 /&'()-]{1,80})?",
        text,
        flags=re.IGNORECASE,
    )
    if ownership_match:
        actor = _sentence_start(ownership_match.group("actor"))
        if actor:
            return _first_path_actor_overrides(actor=actor, baseline=baseline)
    actor_match = re.fullmatch(
        r"(?:it|this(?:\s+(?:product|workflow|first\s+(?:path|release)))?|"
        r"the\s+(?:product|workflow|first\s+(?:path|release)))\s+"
        r"(?:is|should\s+be|must\s+be|needs?\s+to\s+be)\s+for\s+"
        r"(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)"
        r"(?:\s+(?:rather\s+than|instead\s+of)\s+[A-Za-z][A-Za-z0-9 /&'()-]{1,80})?",
        text,
        flags=re.IGNORECASE,
    )
    if actor_match:
        actor = _sentence_start(actor_match.group("actor"))
        if actor:
            return _first_path_actor_overrides(actor=actor, baseline=baseline)
    visible_result_match = re.fullmatch(
        r"(?:actually\s+)?(?:the\s+)?(?:visible\s+)?(?:result|outcome)\s+"
        r"(?:is|should\s+be|must\s+be|needs?\s+to\s+be)\s+"
        r"(?P<result>[A-Za-z][A-Za-z0-9 /&'(),-]{2,220})",
        text,
        flags=re.IGNORECASE,
    )
    if visible_result_match:
        result = visible_result_match.group("result").strip(" .")
        if result:
            return _first_path_visible_result_overrides(result=result, baseline=baseline)
    return {}


def _first_path_actor_overrides(
    *,
    actor: str,
    baseline: Mapping[str, Any],
    action: str = "",
) -> dict[str, Any]:
    baseline_actions = _baseline_first_path_actions(baseline)
    leading_action = action or "; then ".join(baseline_actions) or "complete the first path"
    first_path = f"{actor} can {leading_action}"
    if action and baseline_actions:
        first_path = f"{first_path}, then {'; then '.join(baseline_actions)}"
    return {
        "first_path": f"{first_path.rstrip(' .')}.",
        "human_actors": [f"{actor}: can {action or 'complete the first path'} and review the visible result."],
    }


def _first_path_visible_result_overrides(*, result: str, baseline: Mapping[str, Any]) -> dict[str, Any]:
    """Replace the terminal visible outcome while preserving the accepted path."""

    actor = _baseline_actor_label(baseline) or "The primary user"
    actions = _baseline_first_path_actions(baseline)
    visible_action = f"see {result.strip(' .')}"
    for index in range(len(actions) - 1, -1, -1):
        if _action_describes_visible_result(actions[index]):
            preceding_action = _action_before_visible_result(actions[index])
            actions[index : index + 1] = [preceding_action, visible_action] if preceding_action else [visible_action]
            break
    else:
        actions.append(visible_action)
    first_path = f"{actor} can {'; then '.join(actions)}." if actions else f"{actor} can {visible_action}."
    title = str(baseline.get("title") or "This product").strip()
    result_text = result.strip(" .")
    return {
        "first_path": first_path,
        "human_actors": [f"{actor}: completes the first path and reviews the visible result."],
        "product_story": (
            f"{title} helps the primary user complete the accepted first path and review {result_text}."
        ),
        "product_view": (
            f"{title} is ready when the primary user can complete the accepted first path and review {result_text}."
        ),
        "problem": "The product needs one clear visible outcome after the accepted first path completes.",
        "opportunity": f"Make the first release useful by showing {result_text} at the end of the accepted path.",
        "proof_boundary": (
            f"The first release works when a reviewer can inspect {result_text} with the related state and evidence."
        ),
        "success_metrics": [
            f"The completed first path displays {result_text}.",
            f"Reviewers can verify {result_text} with the related state and evidence.",
        ],
    }


def _action_describes_visible_result(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:see|view|review|receive|publish|show|confirm|result|receipt|report|status)\b",
            str(value or ""),
            flags=re.IGNORECASE,
        )
    )


def _action_before_visible_result(value: str) -> str:
    match = re.match(
        r"^(?P<action>.+?)(?:,\s*(?:and\s+)?|\s+and\s+)"
        r"(?:see|view|review|receive|publish|show|confirm)\b",
        str(value or "").strip(),
        flags=re.IGNORECASE,
    )
    return match.group("action").strip(" .,") if match else ""


def _sentence_start(value: str) -> str:
    text = str(value or "").strip()
    return text[:1].upper() + text[1:] if text else ""


def _baseline_first_path_actions(baseline: Mapping[str, Any]) -> list[str]:
    first_path = str(baseline.get("first_path") or "").strip()
    if not first_path:
        return []
    return [
        action
        for step in split_action_pieces(first_path)
        if (action := action_chain_fragment(step))
    ]


def _baseline_actor_label(baseline: Mapping[str, Any]) -> str:
    for row in confirmed_text_values(baseline.get("human_actors")):
        label = row.partition(":")[0].strip()
        if label:
            return label
    return ""


def _clear_first_path_derivatives(intent: dict[str, Any]) -> None:
    """Regenerate dependent product facts after a freeform first-path correction."""

    for field in (
        "customer",
        "problem",
        "opportunity",
        "product_story",
        "product_view",
        "proof_boundary",
        "success_metrics",
    ):
        intent.pop(field, None)


def _material_edit_rebuilds_dependent_facts(overrides: Mapping[str, Any]) -> bool:
    return bool(
        {
            "title",
            "product_story",
            "state_object",
            "first_path",
            "proof_boundary",
            "human_actors",
        }
        & set(overrides)
    )


def _clear_stale_baseline_derivatives(intent: dict[str, Any], *, overrides: Mapping[str, Any]) -> None:
    """Discard prompt-derived projections after a richer edit changes product facts."""

    for field in ("customer", "problem", "opportunity", "product_view", "success_metrics"):
        if field not in overrides:
            intent.pop(field, None)


def _recompile_unusable_baseline_from_first_path(
    *,
    baseline: Mapping[str, Any],
    prompt: str,
    first_path: Any,
    title: str,
) -> dict[str, Any]:
    """Build product facts from the accepted path when the original prompt needed clarification."""

    rebuilt = intent_hypothesis_from_operator_evidence(str(first_path), prefer_product_title=True)
    if title:
        rebuilt = _retitle_recompiled_intent(rebuilt, title=title)
        rebuilt["internal_systems"] = tuple(internal_system_rows_from_recovered_title(title))
    rebuilt["proof_boundary"] = proof_boundary_with_first_release_requirements(
        str(rebuilt.get("proof_boundary") or ""),
        prompt,
    )
    return rebuilt


def _recompile_title_only_baseline(*, title: str) -> dict[str, Any]:
    rebuilt = intent_hypothesis_from_operator_evidence(title, prefer_product_title=True)
    return _retitle_recompiled_intent(rebuilt, title=title)


def _retitle_recompiled_intent(intent: Mapping[str, Any], *, title: str) -> dict[str, Any]:
    """Keep regenerated projections aligned with the accepted product title."""

    rebuilt = dict(intent)
    previous_title = str(rebuilt.get("title") or "").strip()
    if not previous_title or previous_title.casefold() == title.casefold():
        rebuilt["title"] = title
        return rebuilt
    for key, value in tuple(rebuilt.items()):
        if isinstance(value, str):
            rebuilt[key] = re.sub(re.escape(previous_title), title, value, flags=re.IGNORECASE)
        elif isinstance(value, (list, tuple)):
            rows = [
                re.sub(re.escape(previous_title), title, row, flags=re.IGNORECASE)
                if isinstance(row, str)
                else row
                for row in value
            ]
            rebuilt[key] = tuple(rows) if isinstance(value, tuple) else rows
    rebuilt["title"] = title
    return rebuilt


def _rebuild_operational_constraints_after_first_path_edit(
    intent: dict[str, Any],
    *,
    overrides: Mapping[str, Any],
) -> None:
    """Apply path evidence without discarding unrelated accepted conditions."""

    if "operational_constraints" in overrides or "first_path" not in overrides:
        return
    intent["operational_constraints"] = list(
        operational_constraints_after_first_path_edit(
            intent.get("operational_constraints"),
            overrides["first_path"],
        )
    )


def _without_edit_command(value: str) -> str:
    text = str(value or "").strip()
    if text.casefold() == "edit":
        return ""
    if text.casefold().startswith("edit\n"):
        return text.split("\n", 1)[1].strip()
    if text.casefold().startswith("edit:"):
        return text.split(":", 1)[1].strip()
    return text


def combined_prompt_evidence_source(*, prompt: str, edit_evidence: str) -> str:
    """Render the exact staged evidence that pre-confirm authority seals."""

    rows = [PRECONFIRM_STAGING_MARKER, "", "# Operator prompt evidence", "", prompt.strip()]
    if edit_evidence:
        rows.extend(("", "# Operator edit evidence", "", edit_evidence.strip()))
    return "\n".join(rows).rstrip() + "\n"


__all__ = [
    "combined_prompt_evidence_source",
    "materialize_prompt_confirmed_intent",
    "materialize_prompt_intent_hypothesis",
    "prompt_only_material_decision_error",
    "render_product_intent_preview",
]
