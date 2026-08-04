"""Select and bind the one campaign case used by installed recovery proof."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from greenfield_matrix_release_audit_evidence import audit_request_for_case
from greenfield_matrix_release_audit_evidence import audit_request_sha256
from greenfield_preconfirm_matrix_cases import DEFAULT_CASE_EXPECTATION
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_evidence
from greenfield_preconfirm_matrix_cases import case_expectation


RECOVERY_CASE_SCOPE = "one_selected_campaign_case_all_recovery_phases"


def recovery_case_evidence(
    case: GreenfieldMatrixCase,
    *,
    require_release_binding: bool = False,
    release_audit_binding: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Return opaque case identity, requiring an audited edit for release proof."""

    prompt = str(case.prompt or "")
    if not prompt.strip():
        raise ValueError("installed recovery proof requires a non-empty case prompt")
    evidence = case_evidence(case)
    if not str(evidence.get("id") or "").strip():
        raise ValueError("installed recovery proof requires a stable case key")
    if not require_release_binding:
        evidence["binding_scope"] = "campaign-case-v1"
        return evidence

    confirmed_intent = str(case.confirmed_intent_markdown or "").strip()
    provenance = _mapping(evidence.get("provenance"))
    if not confirmed_intent:
        raise ValueError("release commit recovery proof requires confirmed intent evidence")
    if not case.case_id or provenance.get("corpus_tier") != "source_provenanced":
        raise ValueError("release commit recovery proof requires a source-provenanced case")
    if provenance.get("derived_prompt_sha256") != evidence.get("prompt_sha256"):
        raise ValueError("release commit recovery proof requires a case with a matching prompt hash")
    for key in ("source_id", "source_family", "source_artifact_sha256", "source_excerpt_sha256"):
        if not str(provenance.get(key) or "").strip():
            raise ValueError(f"release commit recovery proof requires provenance.{key}")

    audit_binding = _mapping(release_audit_binding)
    if audit_binding.get("confirmed_intent_sha256") != evidence.get("confirmed_intent_sha256"):
        raise ValueError("release commit recovery proof requires a matching audited confirmed intent hash")
    source_verification_method = str(audit_binding.get("source_verification_method") or "").strip()
    source_verification_uri = str(audit_binding.get("source_verification_uri") or "").strip()
    if not source_verification_method or not source_verification_uri:
        raise ValueError("release commit recovery proof requires audited source verification facts")
    audited_request_hash = str(audit_binding.get("audit_request_sha256") or "").strip()
    expected_audit_request = audit_request_for_case(
        case,
        source_verification_method=source_verification_method,
        source_verification_uri=source_verification_uri,
    )
    if audited_request_hash != audit_request_sha256(expected_audit_request):
        raise ValueError("release commit recovery proof requires an audited request bound to current case semantics")
    evidence["release_audit_binding"] = {
        "audit_request_sha256": audited_request_hash,
        "confirmed_intent_sha256": str(audit_binding.get("confirmed_intent_sha256") or ""),
    }
    evidence["binding_scope"] = "release-confirmed-intent-v1"
    return evidence


def select_recovery_case(
    cases: Sequence[GreenfieldMatrixCase],
    *,
    proof_tier: str,
    approved_audit_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    require_release_binding: bool | None = None,
) -> GreenfieldMatrixCase:
    """Choose one deterministic committed case for every recovery phase."""

    committed_cases = tuple(case for case in cases if case_expectation(case) == DEFAULT_CASE_EXPECTATION)
    if not committed_cases:
        raise RuntimeError("installed commit recovery proof requires a transaction_committed campaign case")
    release_required = (
        str(proof_tier or "").strip().casefold() == "release"
        if require_release_binding is None
        else bool(require_release_binding)
    )
    audit_bindings = approved_audit_bindings if isinstance(approved_audit_bindings, Mapping) else {}
    if release_required and not audit_bindings:
        raise RuntimeError("release commit recovery proof requires an approved audit binding")
    candidates = (
        tuple(
            case
            for case in committed_cases
            if str(case.confirmed_intent_markdown or "").strip() and str(case.case_id or "") in audit_bindings
        )
        if release_required
        else committed_cases
    )
    if not candidates:
        raise RuntimeError("release commit recovery proof requires an audited committed case with confirmed intent")
    selected = min(candidates, key=lambda case: (str(case.case_id or case.slug), str(case.name or "")))
    try:
        recovery_case_evidence(
            selected,
            require_release_binding=release_required,
            release_audit_binding=_mapping(audit_bindings.get(selected.case_id)),
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return selected


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["RECOVERY_CASE_SCOPE", "recovery_case_evidence", "select_recovery_case"]
