"""Report an upstream Greenfield stop without inventing downstream failures."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import json
from typing import Any

from greenfield_matrix_proof_scope import commit_manifest_summary
from greenfield_matrix_quality_scoring import QUALITY_SCORE_DIMENSIONS
from greenfield_matrix_quality_scoring import command_excerpt
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict


COMPILED_RECEIPT_STATUS = "compiled"
_DOWNSTREAM_STAGES = (
    "transaction_commit",
    "generated_artifact_readback",
    "confirmation_navigation",
    "browser_surface_proof",
)


def upstream_stop_status(receipt: Mapping[str, Any]) -> str:
    status = str(receipt.get("status") or "").strip()
    return status if status and status != COMPILED_RECEIPT_STATUS else ""


def upstream_stop_quality_verdict(
    *,
    receipt_status: str,
    create_payload: Mapping[str, Any],
    failure_detail: str,
    score_dimensions: Sequence[str] = QUALITY_SCORE_DIMENSIONS,
) -> GreenfieldQualityVerdict:
    primary = _primary_failure(
        receipt_status=receipt_status,
        create_payload=create_payload,
        failure_detail=failure_detail,
    )
    scores = {str(dimension): -1 for dimension in score_dimensions}
    scores["semantic_manifest"] = 0
    return GreenfieldQualityVerdict(
        passed=False,
        issues=(primary,),
        lenses={},
        scores=scores,
        score=0,
        score_explanation=(
            "pre-confirm compilation stopped; transaction, artifact, navigation, and browser checks are not applicable",
        ),
        score_basis="upstream_preconfirm_stop",
    )


def build_upstream_stop_result(
    *,
    case: Any,
    create: Any,
    create_seconds: float,
    create_payload: Mapping[str, Any],
    receipt: Mapping[str, Any],
    counts: GreenfieldArtifactCounts,
    evidence_builder: Callable[[GreenfieldQualityVerdict], Mapping[str, Any]],
    model_profile: Mapping[str, Any],
) -> GreenfieldMatrixResult:
    """Build one failed result whose downstream proof stages are explicitly N/A."""

    receipt_status = upstream_stop_status(receipt)
    detail = str(getattr(create, "stderr", "") or getattr(create, "stdout", "") or "")
    quality = upstream_stop_quality_verdict(
        receipt_status=receipt_status,
        create_payload=create_payload,
        failure_detail=detail,
    )
    evidence = dict(evidence_builder(quality))
    evidence["preconfirm_dry_run"] = dict(receipt)
    evidence["confirmation_contract"] = {
        "status": "not_applicable",
        "reason": "pre-confirm compilation did not produce a commit-ready transaction",
        "decision_rail_issues": [],
        "post_confirm_navigation_issues": [],
    }
    evidence["evaluation_stages"] = upstream_stop_stage_evidence(
        receipt_status=receipt_status,
        primary_issue=quality.issues[0],
    )
    evidence["model_profile"] = dict(model_profile)
    return GreenfieldMatrixResult(
        name=str(getattr(case, "name", "") or ""),
        status="failed",
        create_seconds=create_seconds,
        counts=counts,
        quality=quality,
        create_returncode=int(getattr(create, "returncode", 1)),
        failure_detail=command_excerpt(detail),
        create_stdout_excerpt=command_excerpt(getattr(create, "stdout", "")),
        create_stderr_excerpt=command_excerpt(getattr(create, "stderr", "")),
        platform_leakage_terms=(),
        commit_manifest_summary=commit_manifest_summary(_mapping(create_payload.get("commit_manifest"))),
        evidence=evidence,
    )


def upstream_stop_stage_evidence(*, receipt_status: str, primary_issue: str) -> dict[str, Any]:
    stages: dict[str, Any] = {
        "preconfirm_compilation": {
            "status": "failed",
            "receipt_status": str(receipt_status),
            "issue": str(primary_issue),
        }
    }
    stages.update(
        {
            stage: {
                "status": "not_applicable",
                "reason": "pre-confirm compilation did not produce a commit-ready transaction",
            }
            for stage in _DOWNSTREAM_STAGES
        }
    )
    return {
        "status": "failed",
        "primary_stage": "preconfirm_compilation",
        "stages": stages,
    }


def _primary_failure(
    *,
    receipt_status: str,
    create_payload: Mapping[str, Any],
    failure_detail: str,
) -> str:
    if receipt_status == "clarification_required":
        clarification = _mapping(create_payload.get("clarification"))
        question = str(clarification.get("question") or "").strip()
        suffix = f": {question}" if question else ""
        return f"unexpected material clarification stopped pre-confirm compilation{suffix}"
    manifest = _mapping(create_payload.get("commit_manifest"))
    messages = tuple(
        str(_mapping(row).get("message") or "").strip()
        for row in manifest.get("issues", ())
        if str(_mapping(row).get("message") or "").strip()
    )
    if messages:
        return "pre-confirm compilation stopped: " + "; ".join(dict.fromkeys(messages))
    error = str(create_payload.get("error") or "").strip()
    if error:
        return f"pre-confirm compilation stopped: {error}"
    detail = _compact_failure_detail(failure_detail)
    return f"pre-confirm compilation stopped ({receipt_status})" + (f": {detail}" if detail else "")


def _compact_failure_detail(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, Mapping):
        text = str(decoded.get("error") or decoded.get("message") or "").strip() or text
    text = " ".join(text.split())
    return text if len(text) <= 800 else f"{text[:800].rstrip()}...[truncated]"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "build_upstream_stop_result",
    "upstream_stop_quality_verdict",
    "upstream_stop_stage_evidence",
    "upstream_stop_status",
]
