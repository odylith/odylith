"""Host-authored product-intent confirmation contract for greenfield work."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


INTENT_CONFIRMATION_SCHEMA_VERSION = "odylith.greenfield.product_intent_confirmation.v2"


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
        "write_policy": "host_reason_product_intent_before_greenfield_proposal",
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
            "must_include": [
                "a short product title that names the actual product, not the command",
                "the product story you believe the user means, written as concise narrative prose",
                "the state object that changes through the first journey",
                "the first complete path Odylith should prove before broader scope",
                "the main human actors and why each matters",
                "external systems separated from internal product systems",
                "the critical assumptions you are making about origin, maturity, safety, money, data, runtime, or integrations",
                "the few ambiguities that would materially change the first path, risk posture, topology, or proof bar",
                "the proof boundary: what would count as evidence and what must not be claimed yet",
                "a proceed, edit, or reject confirmation gate",
            ],
            "must_not": [
                "echo command instructions as the product name",
                "use the repository directory as the project title when the prompt names a product",
                "use generic actor placeholders instead of project-specific human roles",
                "turn the product story into a list of governance artifacts",
                "invent source-backed implementation evidence",
                "generate backlog, Registry, Atlas, release waves, validation obligations, or proposal JSON before confirmation",
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
            "proceed": "After the operator confirms the host-authored intent, build the full greenfield proposal.",
            "edit": "If the interpretation is off, rerun with the corrected product intent.",
            "reject": "If the product shape is wrong, stop without writing records.",
        },
        "commands": {
            "proposal_contract_after_confirmation": (
                "odylith greenfield propose --repo-root . --prompt "
                + _shell_quote(clean_prompt)
                + " --confirm-intent"
            ),
            "apply_after_host_authored_proposal": (
                "odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release 0.0.1"
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
    proposal_contract = _clean(commands.get("proposal_contract_after_confirmation"))
    lines = [
        "Product Intent Confirmation needed",
        f"No files changed. Source posture: {source_posture}.",
        "",
        "Host reasoning task",
        _clean(task.get("reasoning_standard")),
        "",
        "Write in chat",
    ]
    lines.extend(f"- {item}" for item in _strings(task.get("must_include")))
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
            "",
            "Confirm",
            "Ask the operator to proceed, edit, or reject the interpretation. Do not write governance records until they confirm.",
        ]
    )
    if proposal_contract:
        lines.append(f"CLI after confirmation: {proposal_contract}")
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
