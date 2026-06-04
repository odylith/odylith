"""Project-brief rendering for confirmed greenfield proposals."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import strip_dangling_tail
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
    external_systems: list[str] | None = None,
    assumptions: list[str] | None = None,
    ambiguities: list[str] | None = None,
    non_goals: list[str] | None = None,
) -> dict[str, Any]:
    label_lower = label.lower()
    state_label = domain_object_label(state_object, fallback=f"{label} state")
    evidence_label = domain_object_label(evidence_record, fallback=evidence_record)
    actor_summary = join_items(human_actors) or f"the first {label_lower} operator and reviewer"
    internal_summary = join_system_labels(internal_systems) or (
        f"{state_label.lower()} ownership and {evidence_label.lower()} review"
    )
    external_summary = join_items(external_systems) or "explicitly deferred external systems"
    story = product_story or (
        f"{label} turns the confirmed request into one usable product path with named users, "
        "owned state, and reviewable proof."
    )
    story_brief = _brief_clause(story, limit=420)
    first = _brief_clause(
        first_path
        or f"The first release proves one {label_lower} path from intake through state update and evidence review.",
        limit=300,
    )
    proof = _brief_clause(
        proof_boundary
        or (
            f"Release {release} succeeds only when {state_label.lower()} and "
            f"{evidence_label.lower()} can be reviewed together."
        ),
        limit=300,
    )
    non_goal_summary = (
        join_items(non_goals) or "wider automation, live irreversible integrations, and production scaling"
    )
    confirm_command = f"odylith greenfield propose --repo-root . --prompt {shell_quote(prompt)}"
    create_command = (
        f"odylith greenfield create --repo-root . --prompt {shell_quote(prompt)} "
        f"--intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release {release}"
    )
    audit_command = (
        f"odylith greenfield propose --repo-root . --prompt {shell_quote(prompt)} "
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
                    f"{state_label} changes through the first journey; {internal_summary} own the domain "
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
                f"Confirm this as the versioned state object: {state_label}.",
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
                f"Confirm whether release {release} needs {external_summary}.",
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
                f"Does one component own {state_label.lower()} and its version history?",
            ),
            _checkpoint(
                "Evidence path accepted",
                f"Can reviewers inspect {evidence_label.lower()} without trusting implementation prose?",
            ),
            _checkpoint(
                "Release proof accepted",
                f"Do the {release} gates block promotion when {label_lower} proof is missing?",
            ),
        ],
        "coding_readiness_gates": [
            f"The accepted product story is present before implementation planning: {story_brief}",
            f"The first path is accepted in domain language: {first}",
            (
                f"The {label_lower} components come from product systems named in the accepted product "
                f"direction: {internal_summary}."
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
        return f"{story_text}. Problem to solve: {problem_text}."
    first_text = _brief_clause(first, limit=240)
    if first_text:
        return f"{story_text}. Without this first path, users cannot trust the product result: {first_text}."
    return story_text


def _brief_clause(value: str, *, limit: int = 180) -> str:
    text = short_summary(value, limit=limit).strip(" .")
    text = re.sub(r"^the first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = _repair_show_actor_artifact(text)
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return strip_dangling_tail(clipped).rstrip(" ,;:")


def _repair_show_actor_artifact(value: str) -> str:
    return re.sub(
        r"\bshows\s+the\s+(?P<actor>[a-z][a-z '-]{1,40})\s+(?P<article>a|an|the)\s+"
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


def _checkpoint(name: str, question: str) -> dict[str, str]:
    return {
        "checkpoint": name,
        "operator_question": question,
        "done_when": "The answer is visible in the accepted proposal and reflected in validation gates.",
    }


__all__ = ["confirmed_project_brief"]
