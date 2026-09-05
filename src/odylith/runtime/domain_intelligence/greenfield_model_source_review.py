"""One sparse source review inside the original Greenfield authoring budget.

The review replaces only named whole facts, assumptions, or components. The
authoring owner validates the complete candidate again; event bindings and the
first path remain immutable, and review cannot create source authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from time import monotonic
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    ASSUMPTION_SCHEMA,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_model_direct_evidence_graph import (
    MODEL_COMPONENT_SCHEMA,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    require_greenfield_model_profile_observation,
)
from odylith.runtime.reasoning import odylith_reasoning


MAX_SOURCE_REVIEW_SECONDS = 20.0

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
An exact quote is custody, not proof that the quote has the selected semantic role.
Preserve every valid fact, relation, event, useful assumption, and product capability;
return only the smallest whole-field corrections needed for source fidelity and useful
product decisions. Do not rewrite for style or add unsupported meaning.

fact_corrections replaces only the named existing facts field. Never return first_path:
events, first_path, terminal, consistency, ambiguities, and status are immutable. Use
an exact citation with one-based occurrence for a singular source fact, null only to
clear a nullable decision fact, and a complete citation list for a repeated fact.
Use no duplicate fields. Empty fact_corrections means preserve all facts.

assumptions is null when the complete existing list stays valid; otherwise return the
complete replacement list in the existing typed assumption schema. When problem,
customer, opportunity, or product_view lacks a source statement meeting its field
definition, clear that nullable fact and provide one short, useful assumption targeted
to the field. Assumptions are proposed consumer decisions, never extraction commentary.

components is null when the existing groups stay valid; otherwise return the complete
minimal replacement groups. Products own stated capabilities and humans own human
actions. When a product lets or enables people to work, retain the human events but cite
the enclosing product capability as product responsibility. Do not infer an owner,
dependency, authority, event, or implementation claim.

Judge the candidate coherently across all facts. Field definitions:
{field_definitions}

Return exactly fact_corrections, assumptions, and components in the supplied schema.
""".strip()


def _review_contract(fact_schemas: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    editable = {field: schema for field, schema in fact_schemas.items() if field != "first_path"}
    definitions = {
        **_DEFAULT_FACT_DEFINITIONS,
        **{
            field: str(schema["description"])
            for field, schema in editable.items() if schema.get("description")
        },
    }
    prompt = _SYSTEM_PROMPT.format(
        field_definitions="\n".join(f"- {field}: {definitions[field]}" for field in editable)
    )
    schema = {
        "type": "object", "additionalProperties": False,
        "required": ["fact_corrections", "assumptions", "components"],
        "properties": {
            "fact_corrections": {
                "type": "array", "maxItems": len(editable),
                "items": {"anyOf": [
                    {
                        "type": "object", "additionalProperties": False,
                        "required": ["field", "value"],
                        "properties": {
                            "field": {"type": "string", "const": field},
                            "value": value_schema,
                        },
                    }
                    for field, value_schema in editable.items()
                ]},
            },
            "assumptions": {"anyOf": [ASSUMPTION_SCHEMA, {"type": "null"}]},
            "components": {"anyOf": [MODEL_COMPONENT_SCHEMA, {"type": "null"}]},
        },
    }
    return prompt, schema


def _apply_review(
    response: Mapping[str, Any], reviewed: Any, *, fact_schemas: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(reviewed, Mapping) or set(reviewed) != {
        "fact_corrections", "assumptions", "components",
    } or not isinstance(reviewed["fact_corrections"], list):
        raise GreenfieldAuthoredSemanticsError("Greenfield source review did not return a valid candidate")
    corrected = deepcopy(dict(response))
    seen: set[str] = set()
    for row in reviewed["fact_corrections"]:
        if not isinstance(row, Mapping) or set(row) != {"field", "value"}:
            raise GreenfieldAuthoredSemanticsError("Greenfield source review returned an invalid fact correction")
        field = row["field"]
        if not isinstance(field, str) or field not in fact_schemas or field == "first_path" or field in seen:
            raise GreenfieldAuthoredSemanticsError("Greenfield source review returned an unknown, protected, or duplicate fact")
        seen.add(field)
        corrected["result"]["facts"][field] = deepcopy(row["value"])
    for field in ("assumptions", "components"):
        if reviewed[field] is not None:
            corrected["result"][field] = deepcopy(reviewed[field])
    return corrected


def review_semantic_source_claims(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
    provider: odylith_reasoning.ReasoningProvider,
    model: str,
    reasoning_effort: str,
    profile_id: str,
    remaining_seconds: float,
    observation: dict[str, Any],
    fact_schemas: Mapping[str, Any],
    validation_error: str = "",
) -> dict[str, Any]:
    """Return one candidate correction, retaining the real request and response."""

    timeout = min(MAX_SOURCE_REVIEW_SECONDS, remaining_seconds)
    if timeout < 1.0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review has no remaining authoring time"
        )
    payload = {"evidence": evidence_text, "candidate": deepcopy(response["result"])}
    if validation_error:
        payload["validation_error"] = validation_error
    observation.update(
        request=payload, timeout_seconds=timeout, model=model,
        reasoning_effort=reasoning_effort,
    )
    system_prompt, output_schema = _review_contract(fact_schemas)
    started = monotonic()
    reviewed = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt=system_prompt,
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
    observation.update(response=deepcopy(reviewed), elapsed_seconds=elapsed, provider=metadata)
    require_greenfield_model_profile_observation(
        profile_id=profile_id,
        provider=metadata.get("provider", ""),
        model=metadata.get("model") or model,
        reasoning_effort=metadata.get("reasoning_effort") or reasoning_effort,
        effective_timeout_seconds=timeout,
    )
    if elapsed > timeout:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review exceeded its remaining authoring time"
        )
    return _apply_review(response, reviewed, fact_schemas=fact_schemas)
