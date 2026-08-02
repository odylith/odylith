"""Observed release proof for Greenfield model execution profiles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from greenfield_matrix_proof_scope import commit_manifest_summary
from greenfield_matrix_types import GreenfieldRescueSmokeResult
from greenfield_model_profiles import model_profile_environment
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    structured_rescue_proof_env,
)


def provider_failure_rescue_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Force an installed rescue run through an unavailable local provider."""

    values = model_profile_environment("lower-capability-safe-v1", environ)
    return structured_rescue_proof_env(values)


def provider_failure_observation(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return redacted proof only when provider failure and safe fallback were observed."""

    summary = commit_manifest_summary(manifest)
    proven = (
        summary.get("tribunal_patch_plan_status") == "provider_failed"
        and summary.get("structured_patch_fallback_status") == "applied"
        and summary.get("structured_patch_fallback_source") == "source_anchored_semantic_fact"
        and int(summary.get("structured_patch_fallback_operation_count") or 0) > 0
        and bool(str(summary.get("structured_patch_fallback_provider") or "").strip())
        and bool(str(summary.get("structured_patch_fallback_provider_failure_code") or "").strip())
    )
    return {
        "proven": proven,
        "provider": str(summary.get("structured_patch_fallback_provider") or ""),
        "failure_code": str(summary.get("structured_patch_fallback_provider_failure_code") or ""),
        "fallback_status": str(summary.get("structured_patch_fallback_status") or ""),
        "fallback_source": str(summary.get("structured_patch_fallback_source") or ""),
        "fallback_operation_count": int(summary.get("structured_patch_fallback_operation_count") or 0),
    }


def combine_natural_rescue_results(
    bounded: GreenfieldRescueSmokeResult,
    provider_failure: GreenfieldRescueSmokeResult,
) -> GreenfieldRescueSmokeResult:
    """Combine bounded-provider and provider-failure installed proof as one gate."""

    issues = tuple(
        [f"bounded reasoning: {issue}" for issue in bounded.issues]
        + [f"provider failure: {issue}" for issue in provider_failure.issues]
    )
    return GreenfieldRescueSmokeResult(
        status="passed" if bounded.passed and provider_failure.passed else "failed",
        cli_create_seconds=bounded.cli_create_seconds + provider_failure.cli_create_seconds,
        counts=bounded.counts,
        issues=issues,
        manifest=bounded.manifest,
        proof_scope="real_installed_structured_patch_plan_and_provider_failure_cases",
        natural_rescue_quality_proven=bool(
            bounded.natural_rescue_quality_proven
            and provider_failure.natural_rescue_quality_proven
        ),
        provider_failure_fallback_proven=provider_failure.provider_failure_fallback_proven,
        provider_failure_observation=provider_failure.provider_failure_observation,
        create_returncode=max(bounded.create_returncode, provider_failure.create_returncode),
    )


__all__ = [
    "combine_natural_rescue_results",
    "provider_failure_observation",
    "provider_failure_rescue_env",
]
