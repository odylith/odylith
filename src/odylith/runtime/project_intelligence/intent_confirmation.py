"""Host-authored product-intent confirmation contract for greenfield work."""

from __future__ import annotations

import re
from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any


INTENT_CONFIRMATION_SCHEMA_VERSION = "odylith.greenfield.product_intent_confirmation.v5"


def build_product_intent_confirmation(
    *,
    prompt: str,
    title: str,
    repo_name: str,
    observed_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a no-write host preview contract for precompiled product intent."""

    clean_prompt = _clean(prompt) or "new project"
    evidence = dict(observed_source or {})
    source_posture = _clean(evidence.get("source_posture")) or "unknown"
    return {
        "schema_version": INTENT_CONFIRMATION_SCHEMA_VERSION,
        "mode": "product_intent_preview_request",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "precompile_transaction_before_confirm",
        "intent": {
            "prompt": clean_prompt,
            "working_title": _clean(title),
            "repo_name": repo_name,
            "evidence_tier": "user_intent",
        },
        "observed_source": evidence,
        "source_posture": source_posture,
        "host_reasoning_task": {
            "task": "Render the typed Product Intent Preview as a view of precompiled prompt evidence.",
            "time_budget": "20_to_30_seconds_to_read",
            "format_contract": [
                "Render the visible confirmation as sectioned Markdown, not as one long paragraph.",
                "Use this order: Product story; State object; First complete path; Operational constraints when present; Human actors; External systems; Internal product systems; Critical assumptions; Evidence requirements when present; Non-goals when present; Ambiguities; Proof boundary.",
                "Keep Product story, State object, First complete path, and Proof boundary as short paragraphs.",
                "Use bullets for Human actors, External systems, Internal product systems, Critical assumptions, and Ambiguities so the reader can scan the interpretation.",
                "Do not render CONFIRM, EDIT, or REJECT in this preview. Odylith must compile and validate the complete transaction first, then render the sole command rail from that transaction.",
                "Use plain prose for domain nouns; do not wrap ordinary product, actor, state, or component names in code ticks or decorative bold markers.",
            ],
            "must_include": [
                "a short product title that names the actual product, not the command",
                "the product story you believe the user means, written as concise narrative prose",
                "the state object that changes through the first journey",
                "the first complete path the product should prove before broader scope",
                "source-stated operating constraints such as a specific site or time window, kept separate from proof evidence",
                "the main human actors and why each matters",
                "external systems separated from internal product systems",
                "the critical assumptions you are making about origin, maturity, safety, money, data, runtime, or integrations",
                "the few ambiguities that would materially change the first path, risk posture, topology, or proof bar",
                "the proof boundary: what would count as evidence and what must not be claimed yet",
                "source-stated non-goals kept visible and separate from the positive first path",
                "any concrete evidence, measurement, method, vocabulary, safety, or reproducibility requirements stated by the user, kept as concise visible evidence requirements rather than hidden prompt text",
                "when the request includes a paper, PRD, slide deck, memo, issue dump, or long pasted narrative: distill the source into product facts and evidence boundaries instead of mirroring document sections, citations, author metadata, report boilerplate, or implementation instructions",
                "for scientific, research, model, simulation, prediction, or evaluation requests: name the observed quantity, source data or evidence, method or model boundary, variables or parameters, baseline or comparison expectation, uncertainty or tolerance, reproducibility proof, and excluded claims so the final governed artifacts preserve scientific depth without inventing facts",
                "a clear product preview that lets the compiler determine whether material clarification is required before any final command rail appears",
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
                "claim the advisory preview is the final confirmation or write accepted project records before the hash-bound CONFIRM command",
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
            "status": "precompile_before_final_confirmation",
            "proceed": "Compile and validate the ProductCreateTransaction from prompt evidence, then show the sole hash-ready commit-only gate before Odylith writes accepted project records.",
            "edit": "If anything is wrong or missing, treat the reply as new Product Intent evidence and rebuild the ProductCreateTransaction.",
            "reject": "If this is not the intended product, stop and write no records.",
        },
        "commands": {
            "compile_transaction_from_prompt_evidence": (
                "odylith greenfield propose --repo-root . --prompt "
                + _shell_quote(clean_prompt)
            ),
            "commit_transaction_after_hash_confirmation": (
                "odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/pending/<hash>/product-create-transaction.v1.json --transaction-hash <hash> --confirm"
            ),
            "optional_review_json_before_confirmation": (
                "odylith greenfield propose --repo-root . --prompt "
                + _shell_quote(clean_prompt)
                + " --format json"
            ),
        },
    }


def format_product_intent_confirmation_text(confirmation: Mapping[str, Any]) -> str:
    """Render the typed intent preview; the transaction owns the command rail."""

    intent = _mapping(confirmation.get("intent"))
    prompt = _clean(intent.get("prompt"))
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
    return body.replace("Product Intent Confirmation", "Product Intent Preview").rstrip() + "\n"


def format_confirmation_choice_lines(choices: Sequence[tuple[str, str]]) -> list[str]:
    """Return the canonical visible command block for greenfield confirmations."""

    lines = [
        "## Choose one command",
        "",
        "Use one complete command below. Copy CONFIRM or REJECT exactly. For EDIT, replace `<corrections>` with "
        "your changes. The approval code binds your choice to this reviewed package.",
    ]
    for label, detail in choices:
        command = _clean(label)
        verb = command.partition(" ")[0].upper()
        text = _clean(detail)
        if command and text:
            lines.extend(
                [
                    "",
                    f"### {verb}",
                    f"```text\n{command}\n```",
                    text,
                ]
            )
    return lines


def _fallback_confirmation_markdown(*, prompt: str, title: str) -> str:
    clean_prompt = prompt or title
    try:
        from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraint_phrases
    except ImportError:
        operational_constraints = ()
    else:
        operational_constraints = operational_constraint_phrases(clean_prompt)
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
        *(
            [
                "",
                "Operational constraints",
                *(f"- {row}" for row in operational_constraints),
            ]
            if operational_constraints
            else []
        ),
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
