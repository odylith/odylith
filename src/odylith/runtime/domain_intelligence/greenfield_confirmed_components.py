"""Component and project-brief helpers for confirmed greenfield proposals."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify


_STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "application",
    "build",
    "create",
    "for",
    "from",
    "in",
    "me",
    "of",
    "on",
    "platform",
    "product",
    "project",
    "repo",
    "system",
    "the",
    "to",
    "tool",
    "with",
}


def domain_label(title: str, prompt: str) -> str:
    source = title or prompt or "Greenfield Project"
    words = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", source):
        token = raw.strip("-_")
        if not token or token.casefold() in _STOPWORDS:
            continue
        words.append(token)
    if not words:
        words = ["Greenfield", "Workflow"]
    selected = words[:4] if len(words) <= 4 else words[:3]
    return " ".join(_title_word(word) for word in selected)


def shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def confirmed_components(*, label: str, label_slug: str) -> list[dict[str, Any]]:
    path_slug = _path_slug(label_slug)
    return [
        {
            "component_id": _component_id(label_slug, "workflow"),
            "label": f"{label} Workflow Service",
            "kind": "service",
            "intended_path": f"src/{path_slug}/workflow",
            "responsibility": f"Own the {label.lower()} first workflow, operator actions, state transitions, and visible failure handling.",
            "boundary": f"Owns only the {label.lower()} workflow commands, state movement, and user-visible completion status.",
            "dependencies": [
                f"Depends on the {label.lower()} state store for durable state and the evidence review component for release proof."
            ],
            "interfaces": [
                f"Submit {label.lower()} workflow command, read current workflow status, and expose structured failure details."
            ],
            "validation": [
                f"End-to-end {label.lower()} workflow test proves success, validation failure, and recovery messaging."
            ],
            "status": "planned",
            "qualification": "candidate",
            "evidence_tier": "user_intent",
        },
        {
            "component_id": _component_id(label_slug, "state"),
            "label": f"{label} State Store",
            "kind": "service",
            "intended_path": f"src/{path_slug}/state",
            "responsibility": f"Own durable {label.lower()} state records, state versioning, state reads, and change audit references.",
            "boundary": f"Owns the {label.lower()} state object and version history; it does not own workflow orchestration.",
            "dependencies": [
                f"Depends on authenticated workflow commands and supplies state snapshots to {label.lower()} evidence review."
            ],
            "interfaces": [
                f"Create, update, read, and replay {label.lower()} state records with stable identifiers and timestamps."
            ],
            "validation": [
                f"State replay test reconstructs the {label.lower()} record from accepted inputs and change history."
            ],
            "status": "planned",
            "qualification": "candidate",
            "evidence_tier": "user_intent",
        },
        {
            "component_id": _component_id(label_slug, "evidence"),
            "label": f"{label} Evidence Review",
            "kind": "service",
            "intended_path": f"src/{path_slug}/evidence",
            "responsibility": f"Own {label.lower()} proof packets, release evidence review, validation summaries, and audit-ready exports.",
            "boundary": f"Owns proof assembly and review status for {label.lower()}; it does not mutate product state directly.",
            "dependencies": [
                f"Depends on workflow results, state snapshots, validation output, and authorized reviewer identity."
            ],
            "interfaces": [
                f"Assemble {label.lower()} proof packet, record reviewer decision, and export release evidence summary."
            ],
            "validation": [
                f"Proof packet test shows every {label.lower()} release claim maps to a state record and validation result."
            ],
            "status": "planned",
            "qualification": "candidate",
            "evidence_tier": "user_intent",
        },
    ]


def confirmed_project_brief(
    *,
    label: str,
    prompt: str,
    release: str,
    state_object: str,
    evidence_record: str,
) -> dict[str, Any]:
    label_lower = label.lower()
    return {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "purpose": (
            f"Turn the {label_lower} intent into a clear product narrative, first workflow, state object, "
            "and proof boundary before implementation begins."
        ),
        "operating_principle": (
            f"Every {label_lower} release claim must cite the workflow step, state record, owner, and evidence "
            "that made the claim trustworthy."
        ),
        "project_outcome": (
            f"Release {release} proves one usable {label_lower} workflow with accountable ownership, replayable "
            "state, explicit non-goals, and reviewable evidence."
        ),
        "blueprint_sections": [
            {
                "section": "Product story",
                "must_capture": f"Who uses {label_lower}, what real-world job it supports, and why the first workflow matters.",
                "why_it_matters": "Readers need the product in plain language before implementation boundaries appear.",
            },
            {
                "section": "First workflow",
                "must_capture": f"The first operator path from intake through {state_object.lower()} update and review.",
                "why_it_matters": "A narrow workflow keeps the first release testable and prevents broad platform drift.",
            },
            {
                "section": "State and ownership",
                "must_capture": f"Which component owns {state_object.lower()}, which actor can change it, and who reviews it.",
                "why_it_matters": "Clear ownership prevents silent state changes and unclear accountability.",
            },
            {
                "section": "Proof obligations",
                "must_capture": f"How {evidence_record.lower()} proves the release and which claims remain non-goals.",
                "why_it_matters": "Release readiness depends on evidence rather than persuasive prose.",
            },
        ],
        "customization_options": [
            _brief_option("D1", "First user", f"Name the first {label_lower} operator and beneficiary.", "Changes workflow steps and permission expectations."),
            _brief_option("D2", "State object", f"Confirm whether {state_object.lower()} is the right object to version.", "Changes storage ownership and replay proof."),
            _brief_option("D3", "Evidence level", f"Choose local fixture, sandbox, or live read-only evidence for {label_lower}.", "Changes security posture and release confidence."),
            _brief_option("D4", "External systems", f"Keep {label_lower} integrations deferred unless the first workflow needs them.", "Changes adapters, credentials, and failure modes."),
            _brief_option("D5", "Release ambition", f"Keep {release} to one {label_lower} workflow unless the owner accepts extra proof.", "Changes workstream depth and validation cost."),
        ],
        "customization_prompts": [
            f"Revise the {label_lower} story if the first user, workflow, or state object is wrong.",
            f"Add the external source that {label_lower} must trust in release {release}, or keep it fixture-backed.",
            f"Tighten the {label_lower} proof bar so release readiness depends on replayable evidence.",
        ],
        "pre_coding_checkpoints": [
            _checkpoint("Product story accepted", f"Does the {label_lower} story name the user, problem, workflow, and non-goals?"),
            _checkpoint("State ownership accepted", f"Does one component own {state_object.lower()} and its version history?"),
            _checkpoint("Evidence path accepted", f"Can reviewers inspect {evidence_record.lower()} without trusting implementation prose?"),
            _checkpoint("Release proof accepted", f"Do the {release} gates block promotion when {label_lower} proof is missing?"),
        ],
        "coding_readiness_gates": [
            f"The {label_lower} first workflow is accepted with user, state object, non-goals, and failure path.",
            f"The {label_lower} workflow, state, and evidence components have boundaries, interfaces, and proof obligations.",
            f"Release {release} has validation gates for success, failure, replay, access, and review evidence.",
            f"External dependencies for {label_lower} are fixture-backed, sandboxed, source-backed, or explicitly deferred.",
        ],
        "host_independent_paths": [
            {
                "path": "Confirm product intent",
                "command": f"odylith greenfield propose --repo-root . --prompt {shell_quote(prompt)}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use before records are written so the operator can confirm or edit the interpretation.",
            },
            {
                "path": "Create confirmed records",
                "command": f"odylith greenfield create --repo-root . --prompt {shell_quote(prompt)} --confirm --release {release}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use after Product Intent confirmation to let Odylith build, validate, gate, write, and refresh records.",
            },
            {
                "path": "Explicit file review",
                "command": f"odylith greenfield propose --repo-root . --prompt {shell_quote(prompt)} --confirm-intent --format json",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use only when a reviewer explicitly asks to inspect the apply-ready JSON before apply.",
            },
        ],
    }


def _title_word(value: str) -> str:
    lower = value.casefold()
    if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "pwa", "ui", "ux"}:
        return lower.upper()
    return value[:1].upper() + value[1:]


def _component_id(label_slug: str, suffix: str) -> str:
    return slugify(f"{label_slug}-{suffix}")


def _path_slug(label_slug: str) -> str:
    return slugify(label_slug).replace("-", "_") or "greenfield"


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


__all__ = [
    "confirmed_components",
    "confirmed_project_brief",
    "domain_label",
    "shell_quote",
]
