"""Project-brief rendering for confirmed greenfield proposals."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_labels import actor_display_label
from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import is_deferred_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import proof_claim_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_restates_label_with_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import strip_dangling_tail
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import base_adverbial_note_action
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import looks_like_visible_result
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary


def confirmed_project_brief(
    *,
    label: str,
    prompt: str,
    release: str,
    state_object: str,
    evidence_record: str,
    product_story: str = "",
    first_path: str = "",
    proof_boundary: str = "",
    problem: str = "",
    human_actors: list[str] | None = None,
    internal_systems: list[str] | None = None,
    component_labels: list[str] | None = None,
    external_systems: list[str] | None = None,
    assumptions: list[str] | None = None,
    ambiguities: list[str] | None = None,
    non_goals: list[str] | None = None,
) -> dict[str, Any]:
    label_lower = sentence_label(label)
    state_label = domain_object_label(state_object, fallback=f"{label} state")
    state_reference = _state_reference_text(state_object, state_label=state_label)
    evidence_label = domain_object_label(evidence_record, fallback=evidence_record)
    state_ref = sentence_label(state_label)
    evidence_ref = sentence_label(evidence_label)
    actor_summary = _actor_boundary_text(human_actors, project_focus=label) or f"the first {label_lower} operator and reviewer"
    internal_summary = join_system_labels(internal_systems, limit=8) or (
        f"{state_ref} ownership and {evidence_ref} review"
    )
    component_summary = join_system_labels(component_labels, limit=8) or internal_summary
    external_summary = boundary_clause_text(external_systems) or "explicitly deferred external systems"
    story = product_story or (
        f"{label} turns the confirmed request into one usable product path with named users, "
        "owned state, and reviewable proof."
    )
    story_brief = _brief_clause(story, limit=420)
    story_gate = _story_readiness_summary(story, fallback=story_brief, limit=260)
    first = _first_path_brief(
        first_path
        or f"The first release proves one {label_lower} path from intake through state update and evidence review.",
        human_actors=human_actors,
        label=label,
        limit=300,
    )
    proof_source = proof_boundary or (
        f"Release {release} succeeds only when {state_ref} and "
        f"{evidence_ref} can be reviewed together."
    )
    proof = _brief_clause(proof_claim_summary(proof_source, limit=300), limit=300)
    first_gate = _first_path_readiness_summary(
        first_path or first,
        fallback=first,
        proof_boundary=proof_source,
        limit=260,
    )
    non_goal_summary = (
        boundary_clause_text(non_goals) or "wider automation, live irreversible integrations, and production scaling"
    )
    command_prompt = _command_prompt(label=label, first=first, fallback=prompt)
    confirm_command = f"odylith greenfield propose --repo-root . --prompt {shell_quote(command_prompt)}"
    create_command = (
        f"odylith greenfield create --repo-root . --prompt {shell_quote(command_prompt)} "
        f"--intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release {release}"
    )
    audit_command = (
        f"odylith greenfield propose --repo-root . --prompt {shell_quote(command_prompt)} "
        "--intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json"
    )
    return {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "purpose": _purpose_text(story=story, problem=problem, first=first),
        "operating_principle": (
            f"Every release {release} claim must stay attached to the user capability, domain state, "
            "result explanation, and review conditions accepted in the product direction."
        ),
        "project_outcome": proof,
        "blueprint_sections": [
            {
                "section": "Product story",
                "must_capture": story_brief,
                "why_it_matters": (
                    "Readers need to understand the product, user, problem, and real-world outcome before "
                    f"{label_lower} implementation boundaries appear."
                ),
            },
            {
                "section": "First path",
                "must_capture": first,
                "why_it_matters": (
                    "A narrow first path keeps the first release testable and prevents broad platform drift."
                ),
            },
            {
                "section": "State and ownership",
                "must_capture": (
                    f"{state_reference} changes through the first journey; {internal_summary} own the domain "
                    "records needed to trust it."
                ),
                "why_it_matters": "Clear ownership prevents silent state changes and unclear accountability.",
            },
            {
                "section": "Proof obligations",
                "must_capture": proof,
                "why_it_matters": "Release readiness depends on evidence rather than persuasive prose.",
            },
            {
                "section": "Actors and systems",
                "must_capture": f"Actors include {actor_summary}. External systems include {external_summary}.",
                "why_it_matters": "Actor and system boundaries keep user value separate from implementation mechanics.",
            },
        ],
        "customization_options": [
            _brief_option(
                "D1",
                "First user",
                f"Confirm the first people and teams: {actor_summary}.",
                "Changes path steps and permission expectations.",
            ),
            _brief_option(
                "D2",
                "State object",
                f"Confirm this as the versioned state object: {state_reference}.",
                "Changes storage ownership and replay proof.",
            ),
            _brief_option(
                "D3",
                "Evidence level",
                f"Confirm the proof boundary: {proof}",
                "Changes security posture and release confidence.",
            ),
            _brief_option(
                "D4",
                "External systems",
                f"Confirm whether release {release} needs these external systems: {external_summary}.",
                "Changes adapters, credentials, and failure modes.",
            ),
            _brief_option(
                "D5",
                "Release ambition",
                f"Keep {release} to the accepted first path and non-goals: {non_goal_summary}.",
                "Changes planning depth and validation cost.",
            ),
        ],
        "customization_prompts": [
            f"Revise the {label_lower} story if the first user, first path, or state object is wrong.",
            (
                "Decide whether the first release needs a live external source, a simulated source, or an "
                "explicitly deferred integration."
            ),
            f"Tighten the {label_lower} proof bar so release readiness depends on the promised user-visible result.",
        ],
        "pre_coding_checkpoints": [
            _checkpoint(
                "Product story accepted",
                f"Does the {label_lower} story name the user, problem, first path, and non-goals?",
            ),
            _checkpoint(
                "State ownership accepted",
                f"Does one component own {state_ref} and its version history?",
            ),
            _checkpoint(
                "Evidence path accepted",
                f"Can reviewers inspect {evidence_ref} without trusting implementation prose?",
            ),
            _checkpoint(
                "Release proof accepted",
                f"Do the {release} gates block promotion when {label_lower} proof is missing?",
            ),
        ],
        "coding_readiness_gates": [
            f"The accepted product story names the user problem: {_sentence_text(story_gate)}",
            f"The first implementation lane is ready when it covers: {_sentence_text(first_gate)}",
            (
                f"The {label_lower} components come from product systems named in the accepted product "
                f"direction: {component_summary}."
            ),
            f"Release {release} has validation gates for success, failure, replay, access, and review evidence.",
            f"External dependencies for {label_lower} are simulated, sandboxed, source-backed, or explicitly deferred.",
        ],
        "host_independent_paths": [
            {
                "path": "Confirm product intent",
                "command": confirm_command,
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use before records are written so the operator can confirm or edit the interpretation.",
            },
            {
                "path": "Create confirmed records",
                "command": create_command,
                "works_in": "shell, Codex, Claude Code",
                "use_when": (
                    "Use after writing the already-shown confirmation to the intent file so the records build from "
                    "the accepted narrative."
                ),
            },
            {
                "path": "Explicit file review",
                "command": audit_command,
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use only when a reviewer explicitly asks for a governed proposal audit artifact.",
            },
        ],
    }


def _purpose_text(*, story: str, problem: str, first: str) -> str:
    story_text = compact_text(story).strip(" .")
    problem_text = _brief_clause(problem, limit=260)
    if problem_text:
        return f"{_sentence_text(story_text)} Problem to solve: {problem_text}."
    first_text = _brief_clause(first, limit=240)
    if first_text:
        return f"{_sentence_text(story_text)} Without this first path, users cannot trust the product result: {first_text}."
    return story_text


def _sentence_text(value: str) -> str:
    text = compact_text(value).strip()
    if not text:
        return ""
    if text[-1] in ".!?":
        return text
    if text.endswith(('."', '!"', '?"')):
        return text
    return f"{text}."


def _actor_boundary_text(items: list[str] | None, *, project_focus: str = "", limit: int = 4) -> str:
    values = [_actor_boundary_item(item, project_focus=project_focus) for item in (items or []) if str(item or "").strip()]
    values = [value for value in values if value]
    return "; ".join(values[:limit])


def _actor_boundary_item(value: str, *, project_focus: str = "") -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    label, sep, body = _split_actor_boundary_item(text)
    if sep and label:
        label = actor_display_label(text, project_focus=project_focus) or label
        if is_deferred_actor(text):
            return f"{label}: supplies context and support; deferred from the first path"
        if body:
            return f"{label}: {body}"
        return label
    return boundary_clause_text([text])


def _split_actor_boundary_item(value: str) -> tuple[str, str, str]:
    for separator in (":", " — ", " – ", " - "):
        head, sep, body = value.partition(separator)
        label = compact_text(head).strip(" .:-")
        detail = compact_text(body).strip(" .")
        if sep and label and _word_count(label) <= 10:
            return label, sep, detail
    return "", "", ""


def _command_prompt(*, label: str, first: str, fallback: str) -> str:
    prompt = compact_text(f"{label}: {first}").strip(" .:")
    if prompt and len(prompt) <= 240:
        return prompt
    return _brief_clause(prompt or fallback or label, limit=240)


def _brief_clause(value: str, *, limit: int = 180) -> str:
    text = short_summary(value, limit=limit).strip(" .")
    text = re.sub(r"^the first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = _repair_show_actor_artifact(text)
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return _remove_orphan_without_it_tail(strip_dangling_tail(clipped).rstrip(" ,;:"))


def _first_path_brief(value: str, *, human_actors: list[str] | None = None, label: str = "", limit: int = 180) -> str:
    steps = first_path_steps(value)
    if steps:
        text = base_adverbial_note_action(_first_path_step_summary(list(steps), limit=limit))
    else:
        text = base_adverbial_note_action(value)
    return _brief_clause(
        localize_leading_actor_reference(
            text,
            actor_rows=[value for value in human_actors or [] if not is_deferred_actor(str(value))],
            project_focus=label,
            fallback=f"{sentence_label(label)} user" if label else "first user",
        ),
        limit=limit,
    )


def _first_path_step_summary(steps: list[str], *, limit: int) -> str:
    rows = [compact_text(step).strip(" .") for step in steps if compact_text(step).strip(" .")]
    if not rows:
        return ""
    candidate = ". ".join(rows)
    if len(candidate) <= limit:
        return candidate
    terminal = rows[-1]
    if len(rows) > 2 and looks_like_visible_result(terminal):
        without_intermediate_visible = [
            row for row in rows[:-1] if not looks_like_visible_result(row)
        ]
        candidate = ". ".join([*without_intermediate_visible, terminal])
        if len(candidate) <= limit:
            return candidate
        for head_count in (3, 2, 1):
            head = rows[:head_count]
            if terminal in head:
                candidate = ". ".join(head)
            else:
                candidate = ". ".join([*head, terminal])
            if len(candidate) <= limit:
                return candidate
    return ". ".join(rows)


def _story_readiness_summary(value: str, *, fallback: str, limit: int = 220) -> str:
    candidates = [
        _remove_colon_action_list(sentence)
        for sentence in _summary_sentences(value)
        if _remove_colon_action_list(sentence)
    ]
    candidates.append(_remove_colon_action_list(fallback))
    for candidate in candidates:
        summary = _brief_clause(candidate, limit=limit)
        if len(summary.split()) >= 6:
            return summary
    return _brief_clause(fallback, limit=limit)


def _first_path_readiness_summary(
    value: str,
    *,
    fallback: str,
    proof_boundary: str,
    limit: int = 220,
) -> str:
    clauses = first_path_clauses(
        value,
        proof_boundary=proof_boundary,
        action_fallback=fallback,
        capability_fallback=fallback,
        outcome_fallback="",
        action_limit=limit,
        capability_limit=limit,
        outcome_limit=limit,
    )
    capability = _dedupe_repeated_capability(clauses.capability_chain)
    text = capability or clauses.action_chain or fallback
    outcome = compact_text(clauses.visible_result).strip(" .")
    if outcome and not _result_terms_covered(outcome, text):
        text = f"{text} and validate the promised result: {outcome}"
    return _brief_clause(base_adverbial_note_action(text), limit=limit)


def _result_terms_covered(result: str, text: str) -> bool:
    result_terms = {
        word.strip(".,:;()[]{}").casefold()
        for word in compact_text(result).replace("-", " ").split()
        if len(word.strip(".,:;()[]{}")) >= 4
    }
    text_terms = {
        word.strip(".,:;()[]{}").casefold()
        for word in compact_text(text).replace("-", " ").split()
        if len(word.strip(".,:;()[]{}")) >= 4
    }
    return bool(result_terms and result_terms <= text_terms)


def _summary_sentences(value: str) -> list[str]:
    text = compact_text(value).strip()
    if not text:
        return []
    return [part.strip(" .") for part in re.split(r"(?<=[.!?])\s+", text) if part.strip(" .")]


def _remove_colon_action_list(value: str) -> str:
    text = compact_text(value).strip(" .")
    head, separator, tail = text.partition(":")
    if separator and looks_like_action_clause(tail):
        return head.strip(" .")
    return text


def _dedupe_repeated_capability(value: str) -> str:
    text = compact_text(value).strip(" .")
    parts = text.split(" and ")
    for index in range(1, len(parts)):
        left = " and ".join(parts[:index]).strip()
        right = " and ".join(parts[index:]).strip()
        if left and left.casefold() == right.casefold():
            return left
    return text


def _remove_orphan_without_it_tail(value: str) -> str:
    text = value.rstrip(" ,;:.")
    lowered = text.casefold()
    for tail in ("; without it", ". without it"):
        if lowered.endswith(tail):
            return text[: -len(tail)].rstrip(" ,;:")
    return text


def _repair_show_actor_artifact(value: str) -> str:
    return re.sub(
        r"\bshows\s+the\s+(?P<actor>[a-z][a-z'-]*(?:\s+(?!a\b|an\b|the\b|with\b|for\b|to\b|by\b|from\b|on\b|in\b|of\b)[a-z][a-z'-]*){0,3})\s+"
        r"(?P<article>a|an|the)\s+"
        r"(?P<object>[a-z][a-z0-9 '&/-]{1,90}?)(?=,\s+and\b|[.;]|$)",
        lambda match: (
            f"shows {match.group('article')} {match.group('object').strip()} "
            f"to the {match.group('actor').strip()}"
        ),
        value,
        flags=re.IGNORECASE,
    )


def _brief_option(identifier: str, decision: str, recommended: str, impact: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "decision": decision,
        "recommended": recommended,
        "choices": ["accept default", "revise before apply", "defer from first release"],
        "impact": impact,
    }


def _state_reference_text(state_object: str, *, state_label: str) -> str:
    text = compact_text(state_object)
    if text and ":" not in text:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        if len(sentences) <= 1:
            detail = state_detail_summary(text, state_label=state_label, limit=220)
            if (
                detail
                and not detail.casefold().endswith((" and", " for", " of", " through", " with"))
                and not state_detail_restates_label_with_finite_action(detail, state_label=state_label)
            ):
                return sentence_label(detail)
    return sentence_label(state_label)


def _checkpoint(name: str, question: str) -> dict[str, str]:
    return {
        "checkpoint": name,
        "operator_question": question,
        "done_when": "The answer is visible in the accepted proposal and reflected in validation gates.",
    }


__all__ = ["confirmed_project_brief"]
