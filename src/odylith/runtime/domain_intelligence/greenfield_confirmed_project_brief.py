"""Project-brief rendering for confirmed greenfield proposals."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import is_deferred_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import proof_claim_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_confirmed_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_object_descriptor
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import strip_dangling_tail
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_first_path_common import inline_first_path_scope_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import base_adverbial_note_action
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import looks_like_visible_result
from odylith.runtime.domain_intelligence.greenfield_first_path_step_roles import is_supporting_setup_step
from odylith.runtime.domain_intelligence.greenfield_project_brief import project_outcome_text
from odylith.runtime.domain_intelligence.greenfield_project_brief_fields import actor_boundary_text as _actor_boundary_text
from odylith.runtime.domain_intelligence.greenfield_project_brief_fields import brief_option as _brief_option
from odylith.runtime.domain_intelligence.greenfield_project_brief_fields import checkpoint as _checkpoint
from odylith.runtime.domain_intelligence.greenfield_project_brief_fields import state_reference_text as _state_reference_text
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import normalize_confirmed_proof_boundary_sentence


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
    evidence_requirements: list[str] | None = None,
    visible_result: str = "",
) -> dict[str, Any]:
    label_lower = sentence_label(label)
    state_label = compact_domain_object_label(state_object, fallback=f"{label} state")
    state_exact_label = domain_object_label(state_object, fallback=state_label)
    state_reference = _state_reference_text(state_object, state_label=state_label)
    state_reference = _state_reference_with_label(state_reference, state_label=state_exact_label)
    state_descriptor = state_object_descriptor(state_reference)
    evidence_label = domain_object_label(evidence_record, fallback=evidence_record)
    state_ref = sentence_label(state_label)
    evidence_ref = sentence_label(evidence_label)
    actor_summary = _actor_boundary_text(human_actors, project_focus=label, limit=8) or f"the first {label_lower} operator and reviewer"
    internal_summary = join_system_labels(internal_systems, limit=8) or (
        f"{state_ref} ownership and {evidence_ref} review"
    )
    component_summary = _join_component_display_labels(component_labels, limit=8) or internal_summary
    external_summary = boundary_clause_text(external_systems) or "explicitly deferred external systems"
    story = product_story or (
        f"{label} turns the confirmed request into one usable product path with named users, "
        "owned state, and reviewable proof."
    )
    story_brief = _brief_clause(story, limit=420)
    story_gate = _story_readiness_summary(story, fallback=story_brief, limit=420)
    first = _first_path_brief(
        first_path
        or f"The first release proves one {label_lower} path from intake through state update and evidence review.",
        human_actors=human_actors,
        label=label,
        limit=520,
    )
    raw_proof_source = proof_boundary or (
        f"Release {release} succeeds only when {state_ref} and "
        f"{evidence_ref} can be reviewed together."
    )
    proof_source = normalize_confirmed_proof_boundary_sentence(raw_proof_source) or raw_proof_source
    proof = project_outcome_text(
        _brief_clause(proof_claim_summary(proof_source, limit=300), limit=300),
        intent={
            "title": label,
            "first_path": first_path or first,
            "proof_boundary": proof_source,
            "state_object": state_object,
        },
        release_selector=release,
    )
    first_gate = _first_path_readiness_summary(
        first_path or first,
        fallback=first,
        proof_boundary=proof_source,
        visible_result=visible_result,
        limit=520,
    )
    evidence_summary = _brief_clause(join_confirmed_items((evidence_requirements or [])[:8]), limit=520)
    non_goal_summary = (
        boundary_clause_text(non_goals) or "wider automation, live irreversible integrations, and production scaling"
    )
    release_scope_summary = _release_scope_summary(
        first_path=first_path or first,
        first_slice=first,
        non_goal_summary=non_goal_summary,
    )
    assumption_summary = boundary_clause_text(assumptions) or "accepted first-release assumptions"
    command_prompt = _command_prompt(label=label, first=first, fallback=prompt)
    proposal_command = f"odylith greenfield propose --repo-root . --prompt {shell_quote(command_prompt)}"
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
            *(
                [
                    {
                        "section": "Evidence anchors",
                        "must_capture": evidence_summary,
                        "why_it_matters": "Domain reviewers need the accepted evidence vocabulary to survive planning, implementation, and proof.",
                    }
                ]
                if evidence_summary
                else []
            ),
            {
                "section": "Actors and systems",
                "must_capture": f"Actors include {actor_summary}. External systems include {external_summary}.",
                "why_it_matters": "Actor and system boundaries keep user value separate from implementation mechanics.",
            },
            {
                "section": "Critical assumptions",
                "must_capture": assumption_summary,
                "why_it_matters": "Assumptions that affect trust, safety, scope, or release confidence must remain visible.",
            },
        ],
        "customization_options": [
            _brief_option(
                "D1",
                "First user",
                f"Confirm who participates in the first path: {actor_summary}.",
                "Changes path steps and permission expectations.",
            ),
            _brief_option(
                "D2",
                state_descriptor,
                f"Confirm this as the versioned {state_descriptor.casefold()}: {state_reference}.",
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
                f"Keep {release} to the accepted first path and non-goals: {release_scope_summary}.",
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
                f"Is one component accountable for {state_ref} and its version history?",
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
            f"Release {release} has proof checks for success, failure, replay, access, and review evidence.",
            *([f"Source and proof must preserve prompt-grounded evidence anchors: {evidence_summary}."] if evidence_summary else []),
            f"External dependencies for {label_lower} are simulated, sandboxed, source-backed, or explicitly deferred.",
        ],
        "host_independent_paths": [
            {
                "path": "Review the creation-ready transaction",
                "command": proposal_command,
                "works_in": "shell, Codex, Claude Code",
                "use_when": (
                    "Odylith compiles and validates the package before showing CONFIRM, EDIT, and REJECT. "
                    "CONFIRM commits the displayed hash-bound transaction; EDIT rebuilds from new evidence; "
                    "REJECT stops without writes."
                ),
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


def _command_prompt(*, label: str, first: str, fallback: str) -> str:
    first_prompt = _command_first_path_summary(first)
    if _prompt_boundary_repeats(label, first_prompt):
        prompt = compact_text(first_prompt).strip(" .:")
    else:
        prompt = compact_text(f"{label}: {first_prompt}").strip(" .:")
    if prompt and len(prompt) <= 240:
        return prompt
    return _brief_clause(prompt or fallback or label, limit=240)


def _prompt_boundary_repeats(label: str, first_prompt: str) -> bool:
    left = _prompt_boundary_words(label)
    right = _prompt_boundary_words(first_prompt)
    return bool(left and right and left[-1] == right[0] and len(left[-1]) >= 4)


def _prompt_boundary_words(value: str) -> list[str]:
    return [word.casefold().strip(".,;:'\"()[]{}") for word in compact_text(value).split() if word.strip(".,;:'\"()[]{}")]


def _command_first_path_summary(value: str) -> str:
    text = _brief_clause(value, limit=160).strip(" .")
    text = text.replace(",.", ".").replace(", .", ".")
    if text.count(",") >= 3:
        head = text.split(",", 1)[0].strip(" .")
        return f"{head} through the accepted first path" if head else "accepted first path"
    if ". " in text:
        return text.split(". ", 1)[0].strip(" .")
    return text or "accepted first path"


def _release_scope_summary(*, first_path: str, first_slice: str, non_goal_summary: str) -> str:
    path = _brief_clause(first_path or first_slice, limit=620).strip(" .")
    if not path:
        return non_goal_summary
    return f"Do not expand beyond {inline_first_path_scope_fragment(path)} until the first outcome works"


def _state_reference_with_label(value: str, *, state_label: str) -> str:
    text = compact_text(value)
    label = compact_text(state_label).strip(" .")
    if not text or not label:
        return text
    if label.casefold() in text.casefold():
        return text
    return f"{label}: {text}"


def _brief_clause(value: str, *, limit: int = 180) -> str:
    source = compact_text(value).strip(" .")
    text = short_summary(value, limit=limit).strip(" .")
    for phrase in ("the first complete path to prove should be", "first complete path to prove should be"):
        lowered = text.casefold()
        if lowered.startswith(phrase):
            text = text[len(phrase) :].lstrip(" :").strip(" .")
            break
    lowered = text.casefold()
    for connector in ("and", "or", "then", "but"):
        prefix = f"{connector} "
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip(" .")
            break
    text = _repair_show_actor_artifact(text)
    text = _polish_brief_clause(text, clipped=_summary_is_clipped_prefix(text, source, limit=limit))
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return _polish_brief_clause(clipped, clipped=True)


def _summary_is_clipped_prefix(summary: str, source: str, *, limit: int) -> bool:
    if len(source) <= limit:
        return False
    summary_text = compact_text(summary).strip(" .")
    source_text = compact_text(source).strip()
    if not summary_text or not source_text.casefold().startswith(summary_text.casefold()):
        return False
    remainder = source_text[len(summary_text) :].lstrip()
    return bool(remainder and not remainder.startswith((".", "!", "?")))


def _polish_brief_clause(value: str, *, clipped: bool = False) -> str:
    text = strip_dangling_tail(compact_text(value).rstrip(" ,;:"))
    text = _repair_incomplete_clause_tail(text, clipped=clipped)
    return _remove_orphan_without_it_tail(text)


def _repair_incomplete_clause_tail(value: str, *, clipped: bool = False) -> str:
    text = compact_text(value).rstrip(" ,;:.")
    while True:
        words = text.split()
        if len(words) < 3:
            return text
        repaired = _drop_clipped_list_tail(text) if clipped else ""
        if not repaired:
            last = words[-1].strip(".,;:").casefold()
            previous = words[-2].strip(".,;:").casefold()
            if previous in {"a", "an", "the"} and _looks_like_unfinished_modifier(last):
                repaired = _drop_trailing_clause_or_words(text, drop_words=2)
            elif _looks_like_incomplete_terminal_verb(last):
                if _terminal_clause_is_complete_action(text):
                    return text
                repaired = _drop_trailing_clause_or_words(text, drop_words=1)
            else:
                return text
        repaired = strip_dangling_tail(repaired).rstrip(" ,;:.")
        if not repaired or repaired == text:
            return text
        text = repaired


def _terminal_clause_is_complete_action(value: str) -> bool:
    text = compact_text(value).rstrip(" ,;:.")
    separator_index = max(text.rfind(separator) for separator in (",", ";", ":"))
    if separator_index < 0:
        return False
    tail = text[separator_index + 1 :].strip(" ,;:.")
    tail = re.sub(r"^(?:and|or|then|but)\s+", "", tail, flags=re.IGNORECASE).strip(" .")
    if _word_count(tail) < 4 or not looks_like_action_clause(tail):
        return False
    last = tail.split()[-1].strip(".,;:").casefold()
    return not _looks_like_unfinished_modifier(last)


def _drop_clipped_list_tail(value: str) -> str:
    head, separator, tail = compact_text(value).rstrip(" ,;:.").rpartition(",")
    if not separator:
        return ""
    tail_words = tail.strip().split()
    if not 1 <= len(tail_words) <= 3:
        return ""
    if any(word.strip(".,;:").casefold() in {"and", "or"} for word in tail_words):
        return ""
    prefix = head.rstrip(" ,;:.")
    return prefix if _word_count(prefix) >= 6 else ""


def _looks_like_unfinished_modifier(value: str) -> bool:
    token = value.strip(".,;:").casefold()
    return len(token) >= 5 and token.endswith(("able", "ible", "ive", "al", "ful", "less", "ous", "ed", "ing"))


def _looks_like_incomplete_terminal_verb(value: str) -> bool:
    return value.strip(".,;:").casefold() in {
        "cover",
        "covers",
        "display",
        "displays",
        "include",
        "includes",
        "keep",
        "keeps",
        "make",
        "makes",
        "present",
        "presents",
        "produce",
        "produces",
        "provide",
        "provides",
        "record",
        "records",
        "return",
        "returns",
        "show",
        "shows",
        "surface",
        "surfaces",
    }


def _drop_trailing_clause_or_words(value: str, *, drop_words: int) -> str:
    text = compact_text(value).rstrip(" ,;:.")
    separator_indexes = [text.rfind(separator) for separator in (",", ";", ":")]
    separator_index = max(separator_indexes)
    if separator_index > 0:
        prefix = text[:separator_index].rstrip(" ,;:.")
        if _word_count(prefix) >= 6:
            return prefix
    words = text.split()
    if len(words) > drop_words:
        return " ".join(words[:-drop_words]).rstrip(" ,;:.")
    return text


def _first_path_brief(value: str, *, human_actors: list[str] | None = None, label: str = "", limit: int = 180) -> str:
    steps = sequence_event_steps(value)
    if steps and _sequence_steps_are_structural_actions(steps):
        text = base_adverbial_note_action(_first_path_step_summary(list(steps), limit=limit))
    else:
        text = base_adverbial_note_action(value)
    return _brief_clause(
        localize_leading_actor_reference(
            text,
            actor_rows=[value for value in human_actors or [] if not is_deferred_actor(str(value))],
            project_focus=label,
            fallback=f"{sentence_label(label)} user" if label else "first user",
            sentence_context=True,
        ),
        limit=limit,
    )


def _sequence_steps_are_structural_actions(steps: list[str]) -> bool:
    if not steps:
        return False
    for step in steps:
        if is_supporting_setup_step(step):
            continue
        action = action_chain_fragment(step)
        if not action or not looks_like_action_clause(action):
            return False
    return True


def _first_path_step_summary(steps: list[str], *, limit: int) -> str:
    rows = [
        compact_text(step).strip(" .")
        for step in steps
        if compact_text(step).strip(" .") and not is_supporting_setup_step(step)
    ]
    rows = _merge_connector_led_summary_rows(rows)
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


def _merge_connector_led_summary_rows(rows: list[str]) -> list[str]:
    merged: list[str] = []
    for row in rows:
        text = compact_text(row).strip(" .")
        if not text:
            continue
        match = re.match(r"^(?P<connector>and|or)\s+(?P<tail>.+)$", text, flags=re.IGNORECASE)
        if merged and match:
            connector = match.group("connector").casefold()
            tail = match.group("tail").strip(" .")
            merged[-1] = f"{merged[-1].rstrip(' ,;')}, {connector} {tail[:1].casefold()}{tail[1:]}".strip(" .")
            continue
        merged.append(text)
    return merged


def _story_readiness_summary(value: str, *, fallback: str, limit: int = 220) -> str:
    candidates = [
        _readiness_sentence_focus(_remove_colon_action_list(sentence), limit=limit)
        for sentence in _summary_sentences(value)
        if _remove_colon_action_list(sentence)
    ]
    candidates.append(_readiness_sentence_focus(_remove_colon_action_list(fallback), limit=limit))
    for candidate in candidates:
        summary = _brief_clause(candidate, limit=limit)
        if len(summary.split()) >= 6:
            return summary
    return _brief_clause(fallback, limit=limit)


def _readiness_sentence_focus(value: str, *, limit: int) -> str:
    text = compact_text(value).strip(" .")
    if len(text) <= limit:
        return text
    for marker in (" where ", " so that ", " so "):
        head, separator, tail = text.partition(marker)
        if separator and 8 <= _word_count(tail) and len(tail) <= limit:
            return tail.strip(" .")
    return text


def _first_path_readiness_summary(
    value: str,
    *,
    fallback: str,
    proof_boundary: str,
    visible_result: str = "",
    limit: int = 220,
) -> str:
    structured_action = _first_path_action_step_summary(value, limit=limit)
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
    text = _prefer_more_complete_action_summary(structured_action, capability or clauses.action_chain) or fallback
    if not structured_action:
        text = _readiness_action_head(text)
    outcome = compact_text(visible_result or clauses.model.visible_outcome or clauses.visible_result).strip(" .")
    if (
        outcome
        and not _result_terms_covered(outcome, text)
        and not _outcome_action_covered(outcome, text)
    ):
        appended = f"{text} and validate the promised result: {outcome}"
        if len(base_adverbial_note_action(appended)) <= limit:
            text = appended
    return _brief_clause(base_adverbial_note_action(text), limit=limit)


def _readiness_action_head(value: str) -> str:
    text = compact_text(value).strip(" .")
    if text.count(",") < 4:
        return text
    head = text.split(",", 1)[0].strip(" .")
    return head if head and looks_like_action_clause(head) else text


def _outcome_action_covered(outcome: str, text: str) -> bool:
    action = action_chain_fragment(outcome)
    if not action:
        return False
    action_terms = _coverage_terms(action)
    text_terms = _coverage_terms(text)
    return bool(action_terms and action_terms <= text_terms)


def _result_terms_covered(result: str, text: str) -> bool:
    result_terms = _coverage_terms(result)
    text_terms = _coverage_terms(text)
    return bool(result_terms and result_terms <= text_terms)


def _coverage_terms(value: str) -> set[str]:
    return {
        _coverage_term(word)
        for word in compact_text(value).replace("-", " ").split()
        if len(word.strip(".,:;()[]{}")) >= 4
    }


def _coverage_term(value: str) -> str:
    token = value.strip(".,:;()[]{}").casefold()
    if token in {"prove", "proves", "proved", "proven", "proof"}:
        return "proof"
    return token


def _first_path_action_step_summary(value: str, *, limit: int) -> str:
    actions: list[str] = []
    for step in sequence_event_steps(value):
        if is_supporting_setup_step(step):
            continue
        action = action_chain_fragment(step)
        if action and looks_like_action_clause(action):
            actions.append(action)
    summary = _join_capability_clauses(_dedupe_action_rows(actions))
    if not summary:
        return ""
    return _brief_clause(summary, limit=limit)


def _dedupe_action_rows(values: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = compact_text(value).strip(" .")
        key = " ".join(sorted(_coverage_terms(text)))
        if not text or key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


def _prefer_more_complete_action_summary(primary: str, secondary: str) -> str:
    first = compact_text(primary).strip(" .")
    second = compact_text(secondary).strip(" .")
    if not first:
        return second
    if not second:
        return first
    return first if len(_coverage_terms(first)) >= len(_coverage_terms(second)) else second


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
    clauses = [part.strip(" ,") for part in re.split(r",\s+|\s+and\s+", text) if part.strip(" ,")]
    if len(clauses) <= 1:
        return text
    seen: set[str] = set()
    unique: list[str] = []
    for clause in clauses:
        key = _capability_clause_key(clause)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(clause)
    if len(unique) != len(clauses):
        return _join_capability_clauses(unique)
    return text


def _capability_clause_key(value: str) -> str:
    tokens = [
        _coverage_term(word)
        for word in compact_text(value).replace("-", " ").split()
        if len(word.strip(".,:;()[]{}")) >= 4
    ]
    return " ".join(tokens)


def _join_capability_clauses(values: list[str]) -> str:
    rows = [row.strip(" ,") for row in values if row.strip(" ,")]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


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


def _join_component_display_labels(items: list[str] | None, *, limit: int) -> str:
    values: list[str] = []
    for item in items or []:
        label = compact_text(item).strip(" .")
        if label and label not in values:
            values.append(label)
    return ", ".join(values[:limit])


__all__ = ["confirmed_project_brief"]
