"""Source-bound contract for the Greenfield pre-author authority decision.

The host makes the semantic decision once. This module only presents that task
and validates its closed response against the supplied evidence bytes.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


GREENFIELD_AUTHORITY_GATE_CONTRACT_VERSION = "odylith.greenfield.authority-gate-contract.v1"
MAX_GREENFIELD_AUTHORITY_GATE_FILE_BYTES = 64 * 1024

_TASK = (
    "Act only as an independent first-path materiality gate, not a project author. "
    "Decide whether the operator-requested NEW product has an explicit owner or beneficiary, "
    "one usable task, and one observable result. Separately identified source repository/software "
    "descriptions are supporting references, not product intent; they cannot supply those three "
    "witnesses unless the operator explicitly assigns them a role in the requested product. "
    "Do not infer a new product workflow from a reference capability or its audience. "
    "If any witness is missing, choose clarify, required_fields [first_path], give one concise "
    "question, and leave all three witness quotes empty. If complete, choose admit, "
    "required_fields [], copy the three exact operator-intent witness quotes, and leave question "
    "empty. Do not generate components, workstreams, or a package. Output compact JSON."
)

GREENFIELD_AUTHORITY_GATE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["admit", "clarify"]},
        "required_fields": {
            "type": "array",
            "items": {"type": "string", "enum": ["first_path", "product_boundary"]},
            "maxItems": 2,
        },
        "owner_quote": {"type": "string"},
        "task_quote": {"type": "string"},
        "result_quote": {"type": "string"},
        "question": {"type": "string"},
    },
    "required": [
        "decision",
        "required_fields",
        "owner_quote",
        "task_quote",
        "result_quote",
        "question",
    ],
}

_RESPONSE_KEYS = frozenset(GREENFIELD_AUTHORITY_GATE_RESPONSE_SCHEMA["required"])
_QUOTE_KEYS = ("owner_quote", "task_quote", "result_quote")


def greenfield_authority_gate_contract(
    *, prompt: str, edit_evidence: str, evidence_source: str
) -> dict[str, Any]:
    """Present the fixed task and its exact operator evidence to one host pass."""

    if not all(isinstance(value, str) for value in (prompt, edit_evidence, evidence_source)):
        raise TypeError("Greenfield authority gate evidence must be text")
    if not evidence_source:
        raise ValueError("Greenfield authority gate evidence source must not be empty")
    return {
        "version": GREENFIELD_AUTHORITY_GATE_CONTRACT_VERSION,
        "task": _TASK,
        "operator_request": prompt,
        "operator_edit": edit_evidence,
        "response_schema": copy.deepcopy(GREENFIELD_AUTHORITY_GATE_RESPONSE_SCHEMA),
    }


def validate_greenfield_authority_gate(
    response: Mapping[str, Any], *, evidence_source: str
) -> dict[str, Any]:
    """Accept only a closed decision with exact, non-rewritten source witnesses."""

    if not isinstance(response, Mapping):
        raise TypeError("Greenfield authority gate response must be an object")
    if set(response) != _RESPONSE_KEYS:
        raise ValueError("Greenfield authority gate response has invalid fields")
    if not isinstance(evidence_source, str):
        raise TypeError("Greenfield authority gate evidence source must be text")

    decision = response["decision"]
    required_fields = response["required_fields"]
    question = response["question"]
    if decision not in ("admit", "clarify") or not isinstance(decision, str):
        raise ValueError("Greenfield authority gate decision must be admit or clarify")
    if not isinstance(required_fields, list) or any(
        not isinstance(field, str) for field in required_fields
    ):
        raise TypeError("Greenfield authority gate required_fields must be a string array")
    if not isinstance(question, str) or any(
        not isinstance(response[key], str) for key in _QUOTE_KEYS
    ):
        raise TypeError("Greenfield authority gate quotes and question must be strings")

    if decision == "admit":
        if required_fields or question:
            raise ValueError("Greenfield authority gate admit cannot request clarification")
        for key in _QUOTE_KEYS:
            quote = response[key]
            if not quote.strip() or quote not in evidence_source:
                raise ValueError(f"Greenfield authority gate {key} is not exact source evidence")
    elif (
        required_fields != ["first_path"]
        or not question.strip()
        or any(response[key] for key in _QUOTE_KEYS)
    ):
        raise ValueError("Greenfield authority gate clarify requires one first_path question")

    return {
        "decision": decision,
        "required_fields": list(required_fields),
        "owner_quote": response["owner_quote"],
        "task_quote": response["task_quote"],
        "result_quote": response["result_quote"],
        "question": question,
    }


def load_greenfield_authority_gate_file(path: Path) -> dict[str, Any]:
    """Load one bounded UTF-8 JSON response; validation remains a separate step."""

    try:
        with Path(path).expanduser().open("rb") as handle:
            payload = handle.read(MAX_GREENFIELD_AUTHORITY_GATE_FILE_BYTES + 1)
    except OSError as exc:
        raise RuntimeError("environment/IO failure while reading Greenfield authority gate") from exc
    if len(payload) > MAX_GREENFIELD_AUTHORITY_GATE_FILE_BYTES:
        raise ValueError("Greenfield authority gate response exceeds its input bound")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Greenfield authority gate response must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise TypeError("Greenfield authority gate response must be a JSON object")
    return value


__all__ = [
    "GREENFIELD_AUTHORITY_GATE_CONTRACT_VERSION",
    "GREENFIELD_AUTHORITY_GATE_RESPONSE_SCHEMA",
    "MAX_GREENFIELD_AUTHORITY_GATE_FILE_BYTES",
    "greenfield_authority_gate_contract",
    "validate_greenfield_authority_gate",
    "load_greenfield_authority_gate_file",
]
