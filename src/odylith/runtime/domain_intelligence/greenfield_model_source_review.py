"""One source-claim review inside the original Greenfield authoring budget.

This operation reviews product claims and human selections. The authoring owner
validates the complete candidate again; the review cannot rewrite event bindings
or create source authority on its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from time import monotonic
from typing import Any

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

_SYSTEM_PROMPT = """
Review product claims and human selections against the original untrusted evidence.
Return only product_story, complete minimal components, and complete human_actors,
using exact citations. Preserve valid claims; correct only unsupported selections.
product_story describes the product's behavior or outcome, not the operator's
instruction to create or edit a proposal. Preserve an already valid product story;
otherwise select the shortest complete source-backed product claim. The original
instruction remains provenance, never the product's objective.
A product owns its stated capabilities; humans own their stated actions. When a
product helps or enables people, cite that enclosing product capability as its
responsibility, while leaving the human workflow unchanged. Preserve valid
product-performed actions. Use only selected internal_systems or title as owners.
Every responsibility quote must be an exact source substring with its occurrence.
Do not add responsibilities, dependencies, authority, or implementation claims.
For human_actors, check whether each cited phrase actually denotes a source-stated
person or human role in context, rather than a modifier of an activity, artifact,
or output purpose. Do not infer a participant merely because an output needs one.
Preserve explicit participants and output recipients even when they perform no
first-path action. Use an empty array when no human participant is stated. Events
and their actor bindings are immutable; never invent an action to justify a person.
""".strip()


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
    product_story_schema: Mapping[str, Any],
    human_actors_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one candidate correction, retaining the real request and response."""

    timeout = min(MAX_SOURCE_REVIEW_SECONDS, remaining_seconds)
    if timeout < 1.0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review has no remaining authoring time"
        )
    payload = {"evidence": evidence_text, "candidate": deepcopy(response["result"])}
    observation.update(
        request=payload, timeout_seconds=timeout, model=model,
        reasoning_effort=reasoning_effort,
    )
    started = monotonic()
    reviewed = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt=_SYSTEM_PROMPT,
            schema_name="greenfield_semantic_source_review",
            output_schema={
                "type": "object", "additionalProperties": False,
                "required": ["product_story", "components", "human_actors"],
                "properties": {
                    "product_story": dict(product_story_schema),
                    "components": MODEL_COMPONENT_SCHEMA,
                    "human_actors": human_actors_schema,
                },
            },
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
    if not isinstance(reviewed, Mapping) or set(reviewed) != {"product_story", "components", "human_actors"}:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield source review did not return a valid candidate"
        )
    corrected = deepcopy(dict(response))
    corrected["result"]["components"] = deepcopy(reviewed["components"])
    corrected["result"]["facts"]["product_story"] = deepcopy(reviewed["product_story"])
    corrected["result"]["facts"]["human_actors"] = deepcopy(reviewed["human_actors"])
    return corrected
