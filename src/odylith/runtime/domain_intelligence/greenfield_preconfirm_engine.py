"""Fail-closed pre-confirm validation for sealed model-authored Greenfield packages."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import time
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import (
    sealed_authored_projection,
)
from odylith.runtime.domain_intelligence.greenfield_create_manifest import (
    PRECONFIRM_ENGINE_VERSION,
    PRECONFIRM_QUALITY_MANIFEST_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
    normalize_greenfield_model_repair_tier,
    supported_greenfield_model_repair_tiers,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import (
    GreenfieldCompletionReport,
    assert_greenfield_completion_ready,
    build_greenfield_package_report,
    raise_for_failed_greenfield_completion,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import (
    GreenfieldReviewFinding,
    review_report_from_findings,
)
from odylith.runtime.domain_intelligence.proposal_tribunal import (
    raise_for_failed_greenfield_tribunal,
    run_greenfield_tribunal,
)


PRECONFIRM_STANDARD_BUDGET_SECONDS = get_greenfield_model_profile(
    STANDARD_PROFILE_ID
).consumer_budget_seconds
PRECONFIRM_RESCUE_BUDGET_SECONDS = get_greenfield_model_profile(
    RESCUE_PROFILE_ID
).consumer_budget_seconds
PRECONFIRM_DEEP_BUDGET_SECONDS = get_greenfield_model_profile(
    DEEP_PROFILE_ID
).consumer_budget_seconds
PRECONFIRM_BUDGET_SECONDS = PRECONFIRM_STANDARD_BUDGET_SECONDS
PRECONFIRM_REPAIR_TIERS = ("auto", *supported_greenfield_model_repair_tiers())


@dataclass(frozen=True)
class GreenfieldPreconfirmIssue:
    code: str
    surface: str
    path: str
    severity: str
    repairability: str
    owner: str
    message: str
    projection_id: str = ""
    semantic_node_id: str = ""
    source: str = ""
    lens: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldPreconfirmPass:
    pass_index: int
    status: str
    elapsed_seconds: float
    issue_count: int
    issue_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldPreconfirmEngineResult:
    proposal: Mapping[str, Any]
    tribunal: Any
    prewrite_build: Any
    report: GreenfieldCompletionReport
    manifest: dict[str, Any]


class GreenfieldPreconfirmEngineError(ValueError):
    """Pre-confirm validation failure with a structured quality manifest."""

    def __init__(self, message: str, *, manifest: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.manifest = dict(manifest)


def run_greenfield_preconfirm_engine(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    build_prewrite: Callable[[Mapping[str, Any], Any], Any],
    proposal_ready: bool = False,
    repair_tier: str = "auto",
    elapsed_before_start_seconds: float = 0.0,
    model_authoring_tier: str = "",
    model_authoring_receipt: Mapping[str, Any] | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> GreenfieldPreconfirmEngineResult:
    """Validate one exact authored package without reparsing, repair, or rerender.

    The bounded model-authoring calls, custody staging, package compilation, and
    this gate share the selected 60/90/120-second consumer budget.
    """

    if not sealed_authored_projection(proposal):
        raise ValueError("Greenfield pre-confirm accepts only sealed model-authored proposals")
    started = clock()
    prior_elapsed_seconds = _nonnegative_seconds(elapsed_before_start_seconds)
    requested_tier = normalize_greenfield_model_repair_tier(repair_tier)
    selected_profile = get_greenfield_model_profile(
        model_profile_id_for_repair_tier(requested_tier)
    )
    active_tier = selected_profile.repair_tier
    authored_tier = str(model_authoring_tier or active_tier).strip().casefold()
    if authored_tier != active_tier:
        raise ValueError("Greenfield model authoring receipt does not match the selected pre-call profile")
    budget_seconds = selected_profile.consumer_budget_seconds

    def elapsed() -> float:
        return prior_elapsed_seconds + max(0.0, clock() - started)

    if elapsed() >= budget_seconds:
        report = _preconfirm_contract_report(
            "Greenfield proposal exhausted its selected consumer budget before package validation"
        )
        manifest = build_greenfield_preconfirm_manifest(
            report=report,
            status="failed",
            stop_reason="time_budget_exhausted",
            elapsed_seconds=elapsed(),
            pass_records=(),
            budget_seconds=budget_seconds,
            requested_repair_tier=requested_tier,
            active_repair_tier=active_tier,
            model_authoring_receipt=model_authoring_receipt,
        )
        raise GreenfieldPreconfirmEngineError(report.issues[0], manifest=manifest)

    tribunal = run_greenfield_tribunal(proposal, release_selector=release_selector)
    raise_for_failed_greenfield_tribunal(tribunal)
    if not proposal_ready:
        assert_greenfield_completion_ready(proposal, release_selector=release_selector)
    prewrite_build = build_prewrite(proposal, tribunal)
    report = build_greenfield_package_report(prewrite_build.package, model_authored=True)
    typed_issues = classify_greenfield_preconfirm_issues(report)
    pass_record = GreenfieldPreconfirmPass(
        pass_index=0,
        status=report.status,
        elapsed_seconds=round(elapsed(), 3),
        issue_count=len(typed_issues),
        issue_codes=tuple(sorted({issue.code for issue in typed_issues})),
    )
    if elapsed() >= budget_seconds:
        status = "failed"
        stop_reason = "time_budget_exhausted"
    elif report.passed:
        status = "passed"
        stop_reason = "passed"
    else:
        status = "failed"
        stop_reason = "model_authored_validation_failed"
    manifest = build_greenfield_preconfirm_manifest(
        report=report,
        status=status,
        stop_reason=stop_reason,
        elapsed_seconds=elapsed(),
        pass_records=(pass_record,),
        budget_seconds=budget_seconds,
        requested_repair_tier=requested_tier,
        active_repair_tier=active_tier,
        model_authoring_receipt=model_authoring_receipt,
    )
    if status == "passed":
        return GreenfieldPreconfirmEngineResult(
            proposal=proposal,
            tribunal=tribunal,
            prewrite_build=prewrite_build,
            report=report,
            manifest=manifest,
        )
    try:
        raise_for_failed_greenfield_completion(report)
    except ValueError as exc:
        raise GreenfieldPreconfirmEngineError(str(exc), manifest=manifest) from exc
    raise GreenfieldPreconfirmEngineError(
        "Greenfield proposal exceeded its selected consumer budget; no records were created.",
        manifest=manifest,
    )


def classify_greenfield_preconfirm_issues(
    report: GreenfieldCompletionReport,
) -> tuple[GreenfieldPreconfirmIssue, ...]:
    """Preserve typed findings; never infer repair semantics from issue prose."""

    finding_messages = {normalize_string(finding.message) for finding in report.findings}
    uncategorized = tuple(
        _uncategorized_issue(issue)
        for issue in report.issues
        if normalize_string(issue) and normalize_string(issue) not in finding_messages
    )
    return (
        *tuple(_issue_from_review_finding(finding) for finding in report.findings),
        *uncategorized,
    )


def build_greenfield_preconfirm_manifest(
    *,
    report: GreenfieldCompletionReport,
    status: str,
    stop_reason: str,
    elapsed_seconds: float,
    pass_records: Sequence[GreenfieldPreconfirmPass],
    budget_seconds: float,
    requested_repair_tier: str = "standard",
    active_repair_tier: str = "standard",
    write_transaction_status: str = "not_started",
    model_authoring_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the sealed authored-package quality receipt."""

    typed_issues = classify_greenfield_preconfirm_issues(report)
    hard_blocker = next(
        (issue.to_dict() for issue in typed_issues if issue.repairability == "unrepairable"),
        None,
    )
    manifest: dict[str, Any] = {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
        "status": status,
        "validation_status": report.status,
        "stop_reason": stop_reason,
        "budget_seconds": float(budget_seconds),
        "standard_budget_seconds": PRECONFIRM_STANDARD_BUDGET_SECONDS,
        "rescue_budget_seconds": PRECONFIRM_RESCUE_BUDGET_SECONDS,
        "deep_budget_seconds": PRECONFIRM_DEEP_BUDGET_SECONDS,
        "requested_repair_tier": normalize_greenfield_model_repair_tier(requested_repair_tier),
        "repair_tier": get_greenfield_model_profile(
            model_profile_id_for_repair_tier(active_repair_tier)
        ).repair_tier,
        "rescue_activated": active_repair_tier in {"rescue", "deep"},
        "repair_tier_policy": {
            "standard": "pinned pre-call profile; the complete proposal must remain under 60s",
            "rescue": "pinned pre-call profile; the complete proposal must remain under 90s",
            "deep": "pinned pre-call profile; the complete proposal must remain under 120s",
        },
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "passes": len(pass_records),
        "validation_passes": len(pass_records),
        "artifact_counts": dict(report.artifact_counts),
        "issue_count": len(typed_issues),
        "issue_codes": sorted({issue.code for issue in typed_issues}),
        "issues": [issue.to_dict() for issue in typed_issues],
        "review_report": review_report_from_findings(report.findings).to_dict(),
        "hard_blocker": hard_blocker,
        "pass_records": [record.to_dict() for record in pass_records],
        "quality_lenses": {
            "status": "not_applicable",
            "lenses": {},
            "reason": "typed_structural_validation",
        },
        "semantic_compiler": {
            "version": "odylith.greenfield.authored-semantic-validation.v2",
            "status": "passed",
            "semantic_owner": "validated_model_authored_intent",
            "post_authoring_interpretation_calls": 0,
        },
        "write_transaction": {
            "status": write_transaction_status,
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": status == "passed",
        },
    }
    if model_authoring_receipt is not None:
        manifest["model_authoring"] = _model_authoring_manifest(model_authoring_receipt)
    return manifest


def _model_authoring_manifest(receipt: Mapping[str, Any]) -> dict[str, Any]:
    model_profile = receipt.get("model_profile")
    model_profile = model_profile if isinstance(model_profile, Mapping) else {}
    return {
        key: receipt.get(key)
        for key in ("authoring_version", "semantic_model_call_count", "tier", "elapsed_seconds")
    } | {
        "model_profile": {
            key: model_profile.get(key)
            for key in (
                "profile_id",
                "provider",
                "model",
                "reasoning_effort",
                "effective_timeout_seconds",
                "authoring_tier",
            )
        }
    }


def _preconfirm_contract_report(message: str) -> GreenfieldCompletionReport:
    return GreenfieldCompletionReport(
        status="failed",
        version="greenfield-pre-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={},
        tribunal_status="not_run",
        issues=(message,),
    )


def _nonnegative_seconds(value: float) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _uncategorized_issue(message: str) -> GreenfieldPreconfirmIssue:
    return GreenfieldPreconfirmIssue(
        code="uncategorized_quality_issue",
        surface="preconfirm",
        path="",
        severity="critical",
        repairability="unrepairable",
        owner="typed_package_artifact_gate",
        message=normalize_string(message),
        source="package_quality",
    )


def _issue_from_review_finding(finding: GreenfieldReviewFinding) -> GreenfieldPreconfirmIssue:
    return GreenfieldPreconfirmIssue(
        code=finding.code,
        surface=finding.surface,
        path=finding.target_path,
        severity=finding.severity,
        repairability=finding.repairability,
        owner=finding.owner,
        message=finding.message,
        projection_id=finding.projection_id,
        semantic_node_id=finding.semantic_node_id,
        source=finding.source,
        lens=finding.lens,
    )


__all__ = [
    "GreenfieldPreconfirmEngineError",
    "GreenfieldPreconfirmEngineResult",
    "GreenfieldPreconfirmIssue",
    "PRECONFIRM_BUDGET_SECONDS",
    "PRECONFIRM_DEEP_BUDGET_SECONDS",
    "PRECONFIRM_ENGINE_VERSION",
    "PRECONFIRM_QUALITY_MANIFEST_VERSION",
    "PRECONFIRM_REPAIR_TIERS",
    "PRECONFIRM_RESCUE_BUDGET_SECONDS",
    "PRECONFIRM_STANDARD_BUDGET_SECONDS",
    "build_greenfield_preconfirm_manifest",
    "classify_greenfield_preconfirm_issues",
    "run_greenfield_preconfirm_engine",
]
