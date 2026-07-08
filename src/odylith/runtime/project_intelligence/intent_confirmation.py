"""Host-authored product-intent confirmation contract for greenfield work."""

from __future__ import annotations

import re
from collections.abc import Mapping
from collections.abc import Sequence
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
                "Use this order: Product story; State object; First complete path; Human actors; External systems; Internal product systems; Critical assumptions; Ambiguities; Proof boundary; Choose one command.",
                "Keep Product story, State object, First complete path, and Proof boundary as short paragraphs.",
                "Use bullets for Human actors, External systems, Internal product systems, Critical assumptions, and Ambiguities so the reader can scan the interpretation.",
                "Render Choose one command as three separate bullet lines with visually highlighted command labels: CONFIRM, EDIT, and REJECT.",
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
                "when the request includes a paper, PRD, slide deck, memo, issue dump, or long pasted narrative: distill the source into product facts and evidence boundaries instead of mirroring document sections, citations, author metadata, report boilerplate, or implementation instructions",
                "for scientific, research, model, simulation, prediction, or evaluation requests: name the observed quantity, source data or evidence, method or model boundary, variables or parameters, baseline or comparison expectation, uncertainty or tolerance, reproducibility proof, and excluded claims so the final governed artifacts preserve scientific depth without inventing facts",
                "a clear Choose one command block with three separate bullet lines for CONFIRM, EDIT, and REJECT; each choice must say exactly what happens next",
                "for Confirm, say that Odylith compiles a validated ProductCreateTransaction from the accepted intent before any governed records are written",
            ],
            "must_not": [
                "echo command instructions as the product name",
                "use the repository directory as the project title when the prompt names a product",
                "use generic actor placeholders instead of project-specific human roles",
                "collapse the confirmation into a wall of prose without clear sections",
                "use Markdown emphasis or code formatting around normal domain words",
                "turn the product story into a list of governance artifacts",
                "invent source-backed implementation evidence",
                "promote references, citations, authors, equations, benchmark tables, slide captions, legal boilerplate, or coding instructions into product actors, product systems, assumptions, or proof claims",
                "generate implementation records, architecture records, release waves, validation obligations, or proposal JSON before confirmation",
                "dump a generic template or domain catalog",
            ],
            "reasoning_standard": (
                "Infer the product shape live from the operator prompt and any observed repo source. "
                "If the prompt is broad, name the strongest plausible interpretation and only the few questions that change the first path, risk posture, topology, or proof bar. "
                "If the prompt includes a long document or attachment-derived text, segment it mentally into product evidence, supporting context, and non-product scaffolding; only product evidence should appear in the confirmation. "
                "When the request is scientific, research, model, simulation, prediction, or evaluation oriented, preserve scientific depth without inventing domain facts: carry source evidence, method boundaries, variables, uncertainty, baselines, reproducibility, and excluded claims into the confirmation so create can project them into Radar, Registry, Atlas, and proof artifacts. "
                "Keep the answer human and product-first: no scaffolding language, no copied prompt-as-title, no artifact inventory before the product makes sense."
            ),
        },
        "confirmation_gate": {
            "status": "waiting_for_host_authored_product_intent",
            "proceed": "If the interpretation is right, ask the operator to confirm the compiled ProductCreateTransaction hash before Odylith commits accepted project records.",
            "edit": "If anything is wrong or missing, treat the reply as new evidence and rebuild the ProductCreateTransaction.",
            "reject": "If this is not the intended product, stop and write no records.",
        },
        "commands": {
            "compile_transaction_after_intent_confirmation": (
                "odylith greenfield compile-transaction --repo-root . --prompt "
                + _shell_quote(clean_prompt)
                + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release 0.0.1"
            ),
            "commit_transaction_after_hash_confirmation": (
                "odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm"
            ),
            "optional_review_json_after_confirmation": (
                "odylith greenfield compile-transaction --repo-root . --prompt "
                + _shell_quote(clean_prompt)
                + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --format json --release 0.0.1"
            ),
        },
    }


def format_product_intent_confirmation_text(confirmation: Mapping[str, Any]) -> str:
    """Render the no-write confirmation as the exact artifact safe to confirm."""

    intent = _mapping(confirmation.get("intent"))
    commands = _mapping(confirmation.get("commands"))
    prompt = _clean(intent.get("prompt"))
    compile_transaction = _clean(commands.get("compile_transaction_after_intent_confirmation"))
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
    lines = [
        body,
        "",
        *format_confirmation_choice_lines(
            (
                (
                    "CONFIRM",
                    "Accept this interpretation. Odylith compiles a validated ProductCreateTransaction and shows its hash before any governed records are written.",
                ),
                ("EDIT", "Reply with corrections. Odylith treats edits as new evidence and rebuilds before asking again."),
                ("REJECT", "Stop here. Odylith writes no governed records."),
            )
        ),
    ]
    if compile_transaction:
        lines.extend(
            [
                "",
                "Command after **CONFIRM**",
                f"- Compile transaction: {compile_transaction}",
                "- After the transaction is ready, Odylith shows the hash and the commit-only confirmation screen.",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def format_confirmation_choice_lines(choices: Sequence[tuple[str, str]]) -> list[str]:
    """Return the canonical visible command block for greenfield confirmations."""

    lines = ["**Choose one command**"]
    for label, detail in choices:
        command = _clean(label).upper()
        text = _clean(detail)
        if command and text:
            lines.append(f"- **{command}** - {text}")
    return lines


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
        "- No external systems are required for the first proof path unless the operator adds one during edit.",
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
