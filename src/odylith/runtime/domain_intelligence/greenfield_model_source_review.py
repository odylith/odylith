"""One schema-derived source review inside the original Greenfield budget.

The review corrects named whole semantic fields or requests material clarification.
The authoring owner validates the outcome, so review cannot create source authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from time import monotonic
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    require_greenfield_model_profile_observation,
)
from odylith.runtime.reasoning import odylith_reasoning


_DEFAULT_FACT_DEFINITIONS = {
    "title": "An exact source phrase naming the product identity.",
    "product_story": (
        "The shortest complete source span about product behavior or outcome, excluding "
        "the operator's instruction to create or edit a proposal."
    ),
    "success_metrics": "Only source-stated measurable success criteria.",
    "evidence_requirements": "Only source-stated evidence or proof requirements.",
    "operational_constraints": "Only source-stated operating constraints.",
    "internal_systems": "Only source-stated systems inside product ownership.",
    "non_goals": "Only source-stated exclusions or explicitly deferred scope.",
}

_SYSTEM_PROMPT = """
Audit the supplied authored candidate against the original untrusted evidence.
An exact quote establishes custody, not the semantic role of that quote. Preserve
valid meaning and useful provisional decisions. Return a result containing either necessary whole-field corrections or the supplied
material-clarification result. An empty corrections list preserves a valid candidate.

Every authored semantic field is reviewable under its supplied schema. The initial authored
status is a provisional semantic decision, not source authority. When the original
evidence cannot support a usable product path or contains an unresolved material
contradiction, return the supplied clarification result instead of forcing an authored package. Paths beginning facts.
replace one fact; other paths replace the complete named result field. Never return
the same path twice. No path creates source authority. Use exact source citations
with one-based occurrences, and no unsupported roles, dependencies or claims.

Judge all facts, events, terminal, assumptions and component ownership coherently.
Preserve each required actor-owned action and its complete object in source order.
If related fields must change together, return all affected whole fields. Keep
explicit off-path recipients without inventing their activity or product dependency.
Products own their capabilities; humans own human actions. For a product enabling
human work, retain the enclosing capability as product responsibility.

For problem, customer, opportunity and product_view, use a valid source fact or
clear it and supply one short useful targeted assumption. Assumptions are labeled
provisional product decisions, not claimed source facts or extraction commentary.

All replacements are validated together against the complete original authoring
contract before admission. Return only the result in the supplied schema.
Fact meanings:
""".strip()

_RESOLVED_CITATIONS_NOTE = """

resolved_citations is the compiler's read-only binding view for the current
candidate, not new source evidence. It shows the exact selected source location
and surrounding source text. Judge whether that occurrence supports the selected
semantic role. Identical quote bytes at another location do not establish that.
Occurrences count literal substring matches, including matches embedded in larger
words. Any correction must select the intended quote and occurrence in the full
original evidence; do not silently reinterpret a bound source location.
""".rstrip()

_MATERIALITY_NOTE = (
    "Preserve a defensible, role-correct, consumer-usable source-grounded choice "
    "when an alternative would also be valid. Correct material meaning, custody "
    "and usefulness defects; do not revise a candidate solely to prefer a different "
    "valid participant inventory, evidence selection or provisional decision. "
    "A semantically sound usable package should return no corrections."
)


def _review_contract(
    authored_schemas: Mapping[str, Any],
    clarification_schema: Mapping[str, Any],
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    fields: dict[str, Any] = {}
    for name, schema in authored_schemas.items():
        if name == "status":
            continue
        if name == "facts":
            fields.update(
                (f"facts.{field}", value)
                for field, value in schema["properties"].items()
            )
        else:
            fields[name] = schema
    definitions = {
        field: schema.get("description")
        or _DEFAULT_FACT_DEFINITIONS.get(field, "")
        for field, schema in authored_schemas["facts"]["properties"].items()
    }
    prompt = _SYSTEM_PROMPT + "\n" + "\n".join(
        f"- {name}: {value}" for name, value in definitions.items() if value
    ) + _RESOLVED_CITATIONS_NOTE + "\n\n" + _MATERIALITY_NOTE
    correction_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["corrections"],
        "properties": {
            "corrections": {
                "type": "array",
                "maxItems": len(fields),
                "items": {
                    "anyOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["path", "value"],
                            "properties": {
                                "path": {"type": "string", "const": path},
                                "value": value,
                            },
                        }
                        for path, value in fields.items()
                    ]
                },
            }
        },
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["result"],
        "properties": {
            "result": {"anyOf": [correction_schema, clarification_schema]},
        },
    }
    return prompt, schema, fields


def _apply_review(
    response: Mapping[str, Any], reviewed: Any, *, fields: Mapping[str, Any]
) -> dict[str, Any]:
    if (
        not isinstance(reviewed, Mapping)
        or set(reviewed) != {"result"}
        or not isinstance(reviewed["result"], Mapping)
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review did not return a valid candidate"
        )
    result = reviewed["result"]
    if result.get("status") == "clarification_required":
        return {"version": response["version"], "result": deepcopy(dict(result))}
    if set(result) != {"corrections"} or not isinstance(result["corrections"], list):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review did not return a valid candidate"
        )
    corrected = deepcopy(dict(response))
    seen: set[str] = set()
    for row in result["corrections"]:
        if not isinstance(row, Mapping) or set(row) != {"path", "value"}:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield source review returned an invalid correction"
            )
        path = row["path"]
        if not isinstance(path, str) or path not in fields or path in seen:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield source review returned an unknown or duplicate schema path"
            )
        seen.add(path)
        keys = path.split(".")
        owner = corrected["result"]
        for key in keys[:-1]:
            owner = owner[key]
        owner[keys[-1]] = deepcopy(row["value"])
    return corrected


def review_semantic_source_claims(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
    provider: odylith_reasoning.ReasoningProvider,
    profile_id: str,
    remaining_seconds: float,
    observation: dict[str, Any],
    authored_schemas: Mapping[str, Any],
    clarification_schema: Mapping[str, Any],
    resolved_citations: Sequence[Mapping[str, Any]],
    validation_error: str = "",
) -> dict[str, Any]:
    """Return corrections or clarification, retaining the real request and response."""

    timeout = float(remaining_seconds)
    if timeout < 1.0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review has no remaining authoring time"
        )
    profile = get_greenfield_model_profile(profile_id)
    model = profile.source_review_model
    reasoning_effort = profile.source_review_reasoning_effort
    payload = {
        "evidence": evidence_text,
        "candidate": deepcopy(response["result"]),
        "resolved_citations": deepcopy(list(resolved_citations)),
    }
    if validation_error:
        payload["validation_error"] = validation_error
    prompt, output_schema, fields = _review_contract(authored_schemas, clarification_schema)
    observation.update(
        request=payload,
        timeout_seconds=timeout,
        model=model,
        reasoning_effort=reasoning_effort,
        profile_id=profile.profile_id,
        request_role="source_review",
    )
    provider_before_call = odylith_reasoning.provider_failure_metadata(provider)
    require_greenfield_model_profile_observation(
        profile_id=profile.profile_id,
        provider=provider_before_call.get("provider", ""),
        model=model,
        reasoning_effort=reasoning_effort,
        effective_timeout_seconds=timeout,
        request_role="source_review",
    )
    started = monotonic()
    reviewed = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt=prompt,
            schema_name="greenfield_semantic_source_review",
            output_schema=output_schema,
            prompt_payload=payload,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout_seconds=timeout,
        )
    )
    elapsed = max(0.0, monotonic() - started)
    metadata = odylith_reasoning.provider_failure_metadata(provider)
    metadata["model"] = metadata.get("model") or model
    metadata["reasoning_effort"] = (
        metadata.get("reasoning_effort") or reasoning_effort
    )
    observation.update(response=deepcopy(reviewed), elapsed_seconds=elapsed, provider=metadata)
    require_greenfield_model_profile_observation(
        profile_id=profile.profile_id,
        provider=metadata.get("provider", ""),
        model=metadata.get("model", ""),
        reasoning_effort=metadata.get("reasoning_effort", ""),
        effective_timeout_seconds=timeout,
        request_role="source_review",
    )
    if elapsed > timeout:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review exceeded its remaining authoring time"
        )
    return _apply_review(response, reviewed, fields=fields)
