"""Stage one source-cited model-authored Greenfield intent before confirmation.

This is the shipped prompt-to-intent owner. It accepts one fully validated
canonical model result, verifies and seals its cited evidence through the
Product Intent envelope, and stages the candidate for deterministic package
compilation. It contains no lexical semantic fallback.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_SET_SHA256_KEY,
    AUTHORED_SEMANTICS_KEY,
    authored_relation_set_sha256,
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
from odylith.runtime.domain_intelligence.greenfield_model_authoring_receipt import (
    envelope_authoring_observation,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    admit_greenfield_public_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    build_product_intent_envelope,
    product_intent_authority_from_envelope,
    require_product_intent_authority,
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


def stage_validated_authored_intent(
    *,
    prompt: str,
    repo_root: Path,
    prepared: GreenfieldPreparedAuthoringEvidence,
    authored: GreenfieldModelAuthoredIntent,
    receipt: dict[str, Any],
    source_duty: Mapping[str, Any],
    authoring_receipt: dict[str, Any] | None,
    clarification_error: Callable[..., Exception],
) -> dict[str, Any]:
    """Seal one validated host candidate through the canonical custody path."""

    host_receipt = receipt.get("host_candidate")
    if (
        not isinstance(host_receipt, dict)
        or receipt.get("authoring_origin") != "host_native"
        or receipt.get("runtime_semantic_model_call_count") != 0
    ):
        raise ValueError("Greenfield admitted candidate is missing its canonical host receipt")
    canonical_candidate_sha256 = str(
        host_receipt.get("canonical_candidate_sha256") or ""
    )
    if (
        not isinstance(source_duty, Mapping)
        or set(source_duty) != {"ledger_receipt", "binding", "lifecycle"}
        or source_duty["ledger_receipt"].get("ledger_sha256")
        != host_receipt.get("source_duty_ledger_sha256")
        or source_duty["ledger_receipt"].get("source_sha256")
        != host_receipt.get("source_sha256")
        or source_duty["ledger_receipt"].get("verifier_task_sha256")
        != host_receipt.get("source_duty_verifier_task_sha256")
        or source_duty["ledger_receipt"].get("decision_set_sha256")
        != host_receipt.get("source_duty_decision_set_sha256")
        or source_duty["lifecycle"].get("binding_sha256")
        != host_receipt.get("source_duty_binding_sha256")
    ):
        raise ValueError("Greenfield source duties do not match the admitted host candidate")
    intent = deepcopy(dict(authored.intent))
    intent[AUTHORED_SEMANTICS_KEY] = authored_semantics_mapping(
        authored.first_path_relations,
        authored.component_responsibility_relations,
        first_path_context_relations=authored.first_path_context_relations,
        source_precedence=authored.source_precedence,
        source_duty=source_duty,
        provisional_design=authored.provisional_design,
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
        canonical_candidate_sha256=canonical_candidate_sha256,
        model_authoring=envelope_authoring_observation(receipt),
        authored_source_spans=authored.source_spans,
        authored_atomic_claims=authored.atomic_claims,
        authored_source_sha256=authored.source_sha256,
    )
    materiality_gate = envelope.get("materiality_gate")
    if isinstance(materiality_gate, Mapping) and materiality_gate.get("status") != "passed":
        blocked = tuple(str(field) for field in materiality_gate.get("blocked_fields", ()) if str(field))
        clarification = material_clarification_for_fields(blocked)
        raise clarification_error(
            clarification.question,
            required_fields=clarification.required_fields,
        )
    authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=paths.structured.relative_to(root),
        markdown_source_path=paths.evidence_markdown.relative_to(root),
    )
    require_product_intent_authority(authority)
    canonical_relation_hash = authored_relation_set_sha256(
        authored.first_path_relations,
        authored.component_responsibility_relations,
        first_path_context_relations=authored.first_path_context_relations,
        source_precedence=authored.source_precedence,
        source_duty=source_duty,
        provisional_design=authored.provisional_design,
    )
    if canonical_relation_hash != authority[AUTHORED_RELATION_SET_SHA256_KEY]:
        raise ValueError("Greenfield host candidate does not match its sealed authored design")
    receipt["canonical_authority"] = {
        "canonical_candidate_sha256": canonical_candidate_sha256,
        "source_sha256": authority["markdown_source_sha256"],
        "product_facts_sha256": authority["product_facts_sha256"],
        AUTHORED_RELATION_SET_SHA256_KEY: canonical_relation_hash,
    }
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
    "prepare_model_authoring_evidence",
    "prompt_only_material_decision_error",
    "render_product_intent_preview",
]
