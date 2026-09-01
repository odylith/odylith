"""Stage one source-cited model-authored Greenfield intent before confirmation.

This is the shipped prompt-to-intent owner. It accepts one structured model
result, verifies and seals its cited evidence through the Product Intent
envelope, and stages the candidate for deterministic package compilation. It
contains no lexical semantic fallback.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY,
    authored_semantics_mapping,
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import (
    candidate_intent_stage_paths,
    render_candidate_intent_markdown,
    stage_candidate_intent,
)
from odylith.runtime.domain_intelligence.greenfield_material_clarification import (
    material_clarification_for_fields,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    build_product_intent_envelope,
    product_intent_authority_from_envelope,
    require_product_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    admit_greenfield_public_evidence,
)


class GreenfieldClarificationRequired(ValueError):
    """A single material user decision is required before package compilation."""

    def __init__(
        self,
        question: str,
        *,
        required_fields: tuple[str, ...] = ("first_path",),
        authoring_receipt: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(question)
        self.question = question
        self.required_fields = required_fields
        self.authoring_receipt = dict(authoring_receipt or {})


@dataclass(frozen=True, slots=True)
class GreenfieldPreparedAuthoringEvidence:
    """Exact admitted evidence prepared without provider discovery."""

    prompt: str
    edit_evidence: str
    evidence_source: str
    source_format: str
    source_document_count: int
    source_language: str
    admission: dict[str, Any]


def prepare_model_authoring_evidence(
    *,
    prompt: str,
    edit_evidence: str = "",
    source_language: str = "en",
) -> GreenfieldPreparedAuthoringEvidence:
    """Frame and structurally admit evidence before any provider setup."""

    if not prompt.strip():
        raise prompt_only_material_decision_error()
    raw_edit = _without_edit_command(edit_evidence)
    evidence_source = combined_prompt_evidence_source(prompt=prompt, edit_evidence=raw_edit)
    source_format = "operator_prompt_with_edit_evidence" if raw_edit else "operator_prompt"
    document_count = 2 if raw_edit else 1
    admission = admit_greenfield_public_evidence(
        evidence_text=evidence_source,
        source_format=source_format,
        source_document_count=document_count,
        source_language=source_language,
    )
    return GreenfieldPreparedAuthoringEvidence(
        prompt=prompt,
        edit_evidence=raw_edit,
        evidence_source=evidence_source,
        source_format=source_format,
        source_document_count=document_count,
        source_language=source_language,
        admission=admission,
    )


def materialize_model_authored_intent(
    *,
    prompt: str,
    repo_root: Path,
    edit_evidence: str = "",
    authoring_provider: Any,
    authoring_profile_id: str = STANDARD_PROFILE_ID,
    authoring_timeout_seconds: float | None = None,
    authoring_model: str = "",
    authoring_reasoning_effort: str = "",
    source_language: str = "en",
    prepared_evidence: GreenfieldPreparedAuthoringEvidence | None = None,
    authoring_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage one model-authored intent without a parser or lexical fallback."""

    prepared = prepared_evidence or prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
        source_language=source_language,
    )
    if prepared.prompt != prompt:
        raise ValueError("prepared Greenfield evidence does not match the operator prompt")
    authored = author_greenfield_intent(
        evidence_text=prepared.evidence_source,
        provider=authoring_provider,
        timeout_seconds=authoring_timeout_seconds,
        model=authoring_model,
        reasoning_effort=authoring_reasoning_effort,
        model_profile_id=authoring_profile_id,
        source_format=prepared.source_format,
        source_document_count=prepared.source_document_count,
        source_language=prepared.source_language,
    )
    receipt = _authoring_receipt(authored)
    if isinstance(authored, GreenfieldAuthoringClarification):
        clarification = material_clarification_for_fields(authored.required_fields)
        if authoring_receipt is not None:
            authoring_receipt.clear()
            authoring_receipt.update(receipt)
        raise GreenfieldClarificationRequired(
            clarification.question,
            required_fields=clarification.required_fields,
            authoring_receipt=receipt,
        )
    if not isinstance(authored, GreenfieldModelAuthoredIntent):
        raise RuntimeError("Greenfield model authoring returned an unsupported result")

    intent = _preserve_model_authored_intent(authored.intent)
    intent[AUTHORED_SEMANTICS_KEY] = authored_semantics_mapping(
        authored.first_path_relations,
        authored.component_responsibility_relations,
        first_path_context_relations=authored.first_path_context_relations,
    )
    root = Path(repo_root).expanduser().resolve()
    paths = candidate_intent_stage_paths(root)
    envelope = build_product_intent_envelope(
        intent,
        source_text=prepared.evidence_source,
        source_path=paths.evidence_markdown.relative_to(root),
        source_format=prepared.source_format,
        source_document_count=prepared.source_document_count,
        source_language=prepared.source_language,
        model_authoring=receipt["model_profile"],
        authored_source_spans=authored.source_spans,
        authored_atomic_claims=authored.atomic_claims,
        authored_source_sha256=authored.source_sha256,
    )
    materiality_gate = envelope.get("materiality_gate")
    if isinstance(materiality_gate, Mapping) and materiality_gate.get("status") != "passed":
        blocked = tuple(str(field) for field in materiality_gate.get("blocked_fields", ()) if str(field))
        clarification = material_clarification_for_fields(blocked)
        raise GreenfieldClarificationRequired(
            clarification.question,
            required_fields=clarification.required_fields,
        )
    authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=paths.structured.relative_to(root),
        markdown_source_path=paths.evidence_markdown.relative_to(root),
    )
    require_product_intent_authority(authority)
    candidate = stage_candidate_intent(
        repo_root=root,
        intent=intent,
        envelope=envelope,
        authority=authority,
        prompt=prompt,
        edit_evidence=prepared.edit_evidence,
        evidence_source=prepared.evidence_source,
    )
    candidate["prompt"] = prepared.evidence_source
    candidate[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    if authoring_receipt is not None:
        authoring_receipt.clear()
        authoring_receipt.update(receipt)
    return candidate


def _authoring_receipt(
    authored: GreenfieldModelAuthoredIntent | GreenfieldAuthoringClarification,
) -> dict[str, Any]:
    provider = authored.provider or {}
    model_profile = {
        "profile_id": authored.profile_id,
        "provider": str(provider.get("provider") or "").strip().casefold(),
        "model": str(provider.get("model") or "").strip(),
        "reasoning_effort": str(provider.get("reasoning_effort") or "").strip().casefold(),
        "effective_timeout_seconds": float(authored.effective_timeout_seconds),
        "authoring_tier": authored.tier,
    }
    consistency_spans = (
        authored.consistency_source_spans
        if isinstance(authored, GreenfieldAuthoringClarification)
        else tuple(
            span
            for span in authored.source_spans
            if str(span.get("span_id") or "").startswith("authoring:consistency:")
        )
    )
    return {
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "semantic_model_call_count": 1,
        "tier": authored.tier,
        "elapsed_seconds": authored.elapsed_seconds,
        "model_profile": model_profile,
        "consistency_assessment": {
            "status": authored.consistency_status,
            "source_spans": [dict(span) for span in consistency_spans],
        },
    }


def _preserve_model_authored_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for key, value in intent.items():
        if isinstance(value, list):
            copied[key] = [str(item) for item in value]
        else:
            copied[key] = str(value or "")
    return copied


def _without_edit_command(value: str) -> str:
    text = str(value or "").strip()
    command, separator, remainder = text.partition("\n")
    if command.casefold() == "edit":
        return remainder.strip() if separator else ""
    label, separator, remainder = text.partition(":")
    if separator and label.casefold() == "edit":
        return remainder.strip()
    return text


def render_product_intent_preview(intent: Mapping[str, Any]) -> str:
    """Render the typed candidate that directly supplies the transaction."""

    return render_candidate_intent_markdown(intent).replace(
        "Product Intent Confirmation", "Product Intent Preview", 1
    )


def prompt_only_material_decision_error() -> GreenfieldClarificationRequired:
    return GreenfieldClarificationRequired(
        "What is the first complete task the product should help a person finish, and what result should they see?"
    )


__all__ = [
    "GreenfieldClarificationRequired",
    "GreenfieldPreparedAuthoringEvidence",
    "combined_prompt_evidence_source",
    "materialize_model_authored_intent",
    "prepare_model_authoring_evidence",
    "prompt_only_material_decision_error",
    "render_product_intent_preview",
]
