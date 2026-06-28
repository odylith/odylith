"""Host-authored product-intent confirmation contract for greenfield work."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


INTENT_CONFIRMATION_SCHEMA_VERSION = "odylith.greenfield.product_intent_confirmation.v3"


def build_product_intent_confirmation(
    *,
    prompt: str,
    title: str,
    repo_name: str,
    observed_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a no-write request for live host reasoning about product intent."""

    clean_prompt = _clean(prompt) or "new project"
    evidence = dict(observed_source or {})
    source_posture = _clean(evidence.get("source_posture")) or "unknown"
    return {
        "schema_version": INTENT_CONFIRMATION_SCHEMA_VERSION,
        "mode": "product_intent_reasoning_request",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "host_reason_product_intent_before_confirmed_greenfield_create",
        "intent": {
            "prompt": clean_prompt,
            "working_title": _clean(title),
            "repo_name": repo_name,
            "evidence_tier": "user_intent",
        },
        "observed_source": evidence,
        "source_posture": source_posture,
        "host_reasoning_task": {
            "task": "Write the Product Intent Confirmation in chat before Odylith builds any proposal records.",
            "time_budget": "20_to_30_seconds_to_read",
            "format_contract": [
                "Render the visible confirmation as sectioned Markdown, not as one long paragraph.",
                "Use this order: Product story; State object; First complete path; Human actors; External systems; Internal product systems; Critical assumptions; Ambiguities; Proof boundary; Next step.",
                "Keep Product story, State object, First complete path, and Proof boundary as short paragraphs.",
                "Use bullets for Human actors, External systems, Internal product systems, Critical assumptions, and Ambiguities so the reader can scan the interpretation.",
                "Render Next step as three separate bullet lines: Confirm, Edit, and Reject.",
                "Use plain prose for domain nouns; do not wrap ordinary product, actor, state, or component names in code ticks or decorative bold markers.",
            ],
            "must_include": [
                "a short product title that names the actual product, not the command",
                "the product story you believe the user means, written as concise narrative prose",
                "the state object that changes through the first journey",
                "the first complete path the product should prove before broader scope",
                "the main human actors and why each matters",
                "external systems separated from internal product systems",
                "the critical assumptions you are making about origin, maturity, safety, money, data, runtime, or integrations",
                "the few ambiguities that would materially change the first path, risk posture, topology, or proof bar",
                "the proof boundary: what would count as evidence and what must not be claimed yet",
                "a clear Next step block with three separate bullet lines for Confirm, Edit, and Reject; each choice must say exactly what happens next",
                "after confirmation, write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md so create can preserve it and normalize structured intent internally",
            ],
            "must_not": [
                "echo command instructions as the product name",
                "use the repository directory as the project title when the prompt names a product",
                "use generic actor placeholders instead of project-specific human roles",
                "collapse the confirmation into a wall of prose without clear sections",
                "use Markdown emphasis or code formatting around normal domain words",
                "turn the product story into a list of governance artifacts",
                "invent source-backed implementation evidence",
                "generate implementation records, architecture records, release waves, validation obligations, or proposal JSON before confirmation",
                "dump a generic template or domain catalog",
            ],
            "reasoning_standard": (
                "Infer the product shape live from the operator prompt and any observed repo source. "
                "If the prompt is broad, name the strongest plausible interpretation and only the few questions that change the first path, risk posture, topology, or proof bar. "
                "Keep the answer human and product-first: no scaffolding language, no copied prompt-as-title, no artifact inventory before the product makes sense."
            ),
        },
        "confirmation_gate": {
            "status": "waiting_for_host_authored_product_intent",
            "proceed": "If the interpretation is right, ask the operator to confirm so Odylith can build the governed proposal, run deterministic validation, and apply accepted project records.",
            "edit": "If anything is wrong or missing, ask the operator to reply with corrections before proposal expansion.",
            "reject": "If this is not the intended product, stop and write no records.",
        },
        "commands": {
            "confirmed_create_after_confirmation": (
                "odylith greenfield create --repo-root . --prompt "
                + _shell_quote(clean_prompt)
                + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1"
            ),
            "optional_review_json_after_confirmation": (
                "odylith greenfield propose --repo-root . --prompt "
                + _shell_quote(clean_prompt)
                + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json"
            ),
        },
    }


def format_product_intent_confirmation_text(confirmation: Mapping[str, Any]) -> str:
    """Render the no-write confirmation as the exact artifact safe to confirm."""

    intent = _mapping(confirmation.get("intent"))
    commands = _mapping(confirmation.get("commands"))
    prompt = _clean(intent.get("prompt"))
    confirmed_create = _clean(commands.get("confirmed_create_after_confirmation"))
    try:
        from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import (
            confirmation_from_operator_intent,
        )
    except ImportError:
        confirmation_from_operator_intent = None
    if confirmation_from_operator_intent is None:
        title = _clean(intent.get("working_title")) or _clean(intent.get("repo_name")) or "Greenfield Project"
        body = _fallback_confirmation_markdown(prompt=prompt, title=title)
    else:
        body = confirmation_from_operator_intent(prompt, prefer_product_title=True).rstrip()
    lines = [body, "", "Next step"]
    lines.extend(
        [
            "- Confirm: if this interpretation is right, save this same Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md, then run greenfield create with --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm.",
            "- Edit: if the product story, actors, systems, assumptions, first path, or proof boundary is wrong, revise those sections before create.",
            "- Reject: if this is not the intended product, stop here and write no records.",
        ]
    )
    if confirmed_create:
        lines.append(f"Confirmed CLI after confirmation: {confirmed_create}")
    return "\n".join(lines).rstrip() + "\n"


def _fallback_confirmation_markdown(*, prompt: str, title: str) -> str:
    clean_prompt = prompt or title
    lines = [
        f"# {title} - Product Intent Confirmation",
        "",
        "Product story",
        f"{title} gives the first user a clear way to complete the requested path: {clean_prompt}.",
        "",
        "State object",
        f"A {title.lower()} record tracks source input, owner, status, blocker, evidence, and version history.",
        "",
        "First complete path",
        f"The first user provides the source input, reviews the result, and sees the {title.lower()} status with proof.",
        "",
        "Human actors",
        f"- Primary user: completes the first {title.lower()} path and reviews the result.",
        "",
        "External systems",
        "",
        "",
        "Internal product systems",
        f"- {title} Intake Register — records source input, owner, status, blocker, and version history.",
        f"- {title} Review Workspace — presents current state, missing input, confirmation, and next action.",
        f"- {title} Proof Ledger — keeps validation results, decisions, failure reasons, and replayable evidence.",
        "",
        "Critical assumptions",
        "- Release 0.0.1 proves one complete path before broader automation or integrations.",
        "",
        "Ambiguities",
        "- Exact policies, integrations, and operational ownership can be refined after the first proof path is accepted.",
        "",
        "Proof boundary",
        f"Release 0.0.1 succeeds when the first {title.lower()} path is complete, reviewable, blocked when required, and backed by replayable evidence.",
    ]
    return "\n".join(lines)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"
