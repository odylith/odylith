"""Host-authored product-intent confirmation contract for greenfield work."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
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
                "a clear Next step block with Confirm, Edit, and Reject choices; each choice must say exactly what happens next",
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
    """Render the host task without pretending deterministic code authored the story."""

    intent = _mapping(confirmation.get("intent"))
    source_posture = _clean(confirmation.get("source_posture")) or "unknown"
    task = _mapping(confirmation.get("host_reasoning_task"))
    commands = _mapping(confirmation.get("commands"))
    prompt = _clean(intent.get("prompt"))
    confirmed_create = _clean(commands.get("confirmed_create_after_confirmation"))
    lines = [
        "Product Intent Confirmation needed",
        f"No files changed. Source posture: {source_posture}.",
        "",
        f"Host reasoning task: {_clean(task.get('reasoning_standard'))}",
        "",
        "Visible format contract",
    ]
    lines.append(
        "- Render the visible confirmation as sectioned Markdown in this order: "
        "Product story; State object; First complete path; Human actors; External systems; "
        "Internal product systems; Critical assumptions; Ambiguities; Proof boundary; Next step. "
        "Use bullets for Human actors, External systems, Internal product systems, Critical assumptions, "
        "and Ambiguities; do not collapse it into a wall of prose."
    )
    lines.extend(
        [
            "",
            "Write in chat",
        ]
    )
    lines.extend(
        [
            "- product title, Product story, State object, and First complete path",
            "- Human actors, External systems, and Internal product systems",
            "- Critical assumptions, Ambiguities, and Proof boundary",
            "- Confirm/Edit/Reject next step with what happens next",
        ]
    )
    lines.extend(
        [
            "",
            "Do not",
        ]
    )
    lines.extend(f"- {item}" for item in _strings(task.get("must_not")))
    lines.extend(
        [
            "",
            "Original user intent",
            prompt,
            "Next step",
            "- Confirm: if the interpretation is right, write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md, then run greenfield create with --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm so Odylith normalizes the accepted narrative internally, validates it, and applies accepted project records. Do not ask the operator to inspect proposal JSON.",
            "- Edit: if the product story, actors, systems, assumptions, first path, or proof boundary is wrong, ask for corrections and rerun this confirmation.",
            "- Reject: if this is not the intended product, stop here and write nothing.",
        ]
    )
    if confirmed_create:
        lines.append(f"Confirmed CLI after confirmation: {confirmed_create}")
    return "\n".join(line for line in lines if line is not None).rstrip() + "\n"


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [_clean(item) for item in value if _clean(item)]


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"
