"""Bounded fixpoint engine for confirmed greenfield post-confirm packages."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import replace
import hashlib
import inspect
import json
import time
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_string_list
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionReport,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    assert_greenfield_completion_ready,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    raise_for_failed_greenfield_completion,
)
from odylith.runtime.artifact_quality.greenfield_quality_lenses import (
    build_greenfield_quality_lens_report,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_patchset import (
    patchset_request_from_findings,
)
from odylith.runtime.domain_intelligence.greenfield_patch_projection_scope import patch_expand_projection_scope
from odylith.runtime.domain_intelligence.greenfield_patch_projection_scope import patch_scope_requires_full_prewrite
from odylith.runtime.domain_intelligence.greenfield_post_confirm_repair import (
    repair_greenfield_package_until_clean,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    GreenfieldReviewFinding,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import review_finding
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    review_report_from_findings,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_rescue_probe import (
    RESCUE_PROBE_CODE,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_structured_rescue_proof import (
    STRUCTURED_RESCUE_PROOF_CODE,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    compile_greenfield_semantics,
)
from odylith.runtime.domain_intelligence.proposal_tribunal import (
    raise_for_failed_greenfield_tribunal,
)
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal


POST_CONFIRM_ENGINE_VERSION = "greenfield-post-confirm-fixpoint-v1"
POST_CONFIRM_QUALITY_MANIFEST_VERSION = "greenfield-post-confirm-quality-manifest-v1"
POST_CONFIRM_STANDARD_BUDGET_SECONDS = 60.0
POST_CONFIRM_RESCUE_BUDGET_SECONDS = 90.0
POST_CONFIRM_DEEP_BUDGET_SECONDS = 120.0
POST_CONFIRM_BUDGET_SECONDS = POST_CONFIRM_STANDARD_BUDGET_SECONDS
POST_CONFIRM_MAX_PASSES = 4
POST_CONFIRM_RESCUE_MAX_PASSES = 6
POST_CONFIRM_DEEP_MAX_PASSES = 8
POST_CONFIRM_REPAIR_TIERS = ("auto", "standard", "rescue", "deep")


@dataclass(frozen=True)
class GreenfieldPostConfirmIssue:
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
class GreenfieldPostConfirmPass:
    pass_index: int
    status: str
    elapsed_seconds: float
    package_repair_passes: int
    package_changed: bool
    issue_count: int
    issue_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldPostConfirmRepairContext:
    pass_index: int
    elapsed_seconds: float
    budget_seconds: float
    report: GreenfieldCompletionReport
    issues: tuple[GreenfieldPostConfirmIssue, ...]
    review_report: Mapping[str, Any]
    patchset_request: Mapping[str, Any]
    quality_lenses: Mapping[str, Any]
    semantic_compiler: Mapping[str, Any]
    repair_tier: str = "standard"
    rescue_activated: bool = False


@dataclass(frozen=True)
class GreenfieldPostConfirmEngineResult:
    proposal: Mapping[str, Any]
    tribunal: Any
    prewrite_build: Any
    report: GreenfieldCompletionReport
    manifest: dict[str, Any]


class GreenfieldPostConfirmEngineError(ValueError):
    """Post-confirm fixpoint failure with a structured quality manifest."""

    def __init__(self, message: str, *, manifest: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.manifest = dict(manifest)


def run_greenfield_post_confirm_engine(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    build_prewrite: Callable[[Mapping[str, Any], Any], Any],
    repair_proposal: Callable[..., Mapping[str, Any]],
    prepare_repair_context: Callable[
        [Mapping[str, Any], GreenfieldPostConfirmRepairContext],
        GreenfieldPostConfirmRepairContext,
    ]
    | None = None,
    rerender_prewrite: Callable[..., Any] | None = None,
    proposal_ready: bool = False,
    max_passes: int = POST_CONFIRM_MAX_PASSES,
    budget_seconds: float = POST_CONFIRM_BUDGET_SECONDS,
    repair_tier: str = "auto",
    clock: Callable[[], float] = time.perf_counter,
) -> GreenfieldPostConfirmEngineResult:
    """Build, repair, and revalidate post-confirm output before governed writes."""

    started = clock()
    requested_tier = _normalize_repair_tier(repair_tier)
    active_tier = _initial_active_tier(requested_tier)
    rescue_activated = active_tier in {"rescue", "deep"}
    active_budget_seconds = _tier_budget_seconds(active_tier, fallback=budget_seconds)
    effective_budget_seconds = active_budget_seconds
    seen_failures: set[str] = set()
    pass_records: list[GreenfieldPostConfirmPass] = []
    repaired_issue_codes: set[str] = set()
    last_report: GreenfieldCompletionReport | None = None
    last_prewrite_build: Any = None
    last_repair_patchset_request: Mapping[str, Any] | None = None
    pending_prewrite_build: Any = None
    pending_rerender_projections: tuple[str, ...] = ()
    current = proposal
    bounded_passes = max(1, int(max_passes))
    if active_tier == "rescue":
        bounded_passes = max(bounded_passes, POST_CONFIRM_RESCUE_MAX_PASSES)
    elif active_tier == "deep":
        bounded_passes = max(bounded_passes, POST_CONFIRM_DEEP_MAX_PASSES)
    stop_reason = "max_passes"
    tribunal: Any = None
    pass_index = 0

    while pass_index < bounded_passes:
        elapsed = max(0.0, clock() - started)
        if elapsed >= effective_budget_seconds:
            stop_reason = "time_budget_exhausted"
            break

        tribunal = run_greenfield_tribunal(current, release_selector=release_selector)
        raise_for_failed_greenfield_tribunal(tribunal)
        if not (proposal_ready and pass_index == 0):
            assert_greenfield_completion_ready(current, release_selector=release_selector)

        if pending_rerender_projections and pending_prewrite_build is not None and rerender_prewrite is not None:
            prewrite_build = rerender_prewrite(
                current_proposal=current,
                tribunal=tribunal,
                previous_prewrite_build=pending_prewrite_build,
                projections=pending_rerender_projections,
            )
        else:
            prewrite_build = build_prewrite(current, tribunal)
        pending_prewrite_build = None
        pending_rerender_projections = ()
        package_repair = repair_greenfield_package_until_clean(prewrite_build.package)
        initial_typed_issues = classify_greenfield_post_confirm_issues(package_repair.initial_report)
        if package_repair.changed:
            prewrite_build = _replace_prewrite_package(prewrite_build, package_repair.package)

        report = package_repair.report
        typed_issues = classify_greenfield_post_confirm_issues(report)
        quality_lenses = build_greenfield_quality_lens_report(prewrite_build.package)
        semantic_compiler = compile_greenfield_semantics(prewrite_build.package.proposal).to_dict()
        if package_repair.changed:
            repaired_issue_codes.update(
                issue.code
                for issue in initial_typed_issues
                if issue.repairability == "safe_package_repair"
            )
        pass_records.append(
            GreenfieldPostConfirmPass(
                pass_index=pass_index,
                status=report.status,
                elapsed_seconds=round(max(0.0, clock() - started), 3),
                package_repair_passes=package_repair.passes,
                package_changed=package_repair.changed,
                issue_count=len(report.issues),
                issue_codes=tuple(sorted({issue.code for issue in typed_issues})),
            )
        )

        last_report = report
        last_prewrite_build = prewrite_build
        if report.passed:
            stop_reason = "passed"
            return GreenfieldPostConfirmEngineResult(
                proposal=current,
                tribunal=tribunal,
                prewrite_build=prewrite_build,
                report=report,
                manifest=build_greenfield_post_confirm_manifest(
                    report=report,
                    status="passed",
                    stop_reason=stop_reason,
                    elapsed_seconds=max(0.0, clock() - started),
                    passes=len(pass_records),
                    pass_records=pass_records,
                    repaired_issue_codes=repaired_issue_codes,
                    max_passes=bounded_passes,
                    budget_seconds=active_budget_seconds,
                    requested_repair_tier=requested_tier,
                    active_repair_tier=active_tier,
                    rescue_activated=rescue_activated,
                    quality_lenses=quality_lenses,
                    semantic_compiler=semantic_compiler,
                    last_repair_patchset_request=last_repair_patchset_request,
                ),
            )

        failure_signature = _failure_signature(report)
        if failure_signature in seen_failures:
            stop_reason = "no_progress"
            break
        seen_failures.add(failure_signature)
        patchset_request = patchset_request_from_findings(report.findings).to_dict()
        direct_rerender_projections = _direct_rerender_projections(typed_issues)
        if direct_rerender_projections:
            if rerender_prewrite is None:
                last_report = _projection_rerender_contract_report(
                    report,
                    projections=direct_rerender_projections,
                )
                stop_reason = "missing_projection_rerender_callback"
                break
            pending_rerender_projections = direct_rerender_projections
            pending_prewrite_build = prewrite_build
            pass_index += 1
            continue
        if active_tier == "standard" and requested_tier == "auto":
            if not _rescue_eligible(typed_issues, patchset_request=patchset_request):
                stop_reason = "not_rescue_eligible"
                break
            active_tier = "rescue"
            rescue_activated = True
            active_budget_seconds = POST_CONFIRM_RESCUE_BUDGET_SECONDS
            effective_budget_seconds = POST_CONFIRM_RESCUE_BUDGET_SECONDS
            bounded_passes = max(bounded_passes, POST_CONFIRM_RESCUE_MAX_PASSES)
        previous = current
        repair_context = GreenfieldPostConfirmRepairContext(
            pass_index=pass_index,
            elapsed_seconds=round(max(0.0, clock() - started), 3),
            budget_seconds=float(active_budget_seconds),
            report=report,
            issues=typed_issues,
            review_report=review_report_from_findings(report.findings).to_dict(),
            patchset_request=patchset_request,
            quality_lenses=quality_lenses,
            semantic_compiler=semantic_compiler,
            repair_tier=active_tier,
            rescue_activated=rescue_activated,
        )
        if prepare_repair_context is not None:
            repair_context = prepare_repair_context(current, repair_context)
        if _patchset_has_operations(repair_context.patchset_request):
            last_repair_patchset_request = repair_context.patchset_request
        current = _repair_proposal_with_context(
            repair_proposal,
            current,
            repair_context,
        )
        if current != previous:
            repaired_issue_codes.update(
                issue.code
                for issue in typed_issues
                if issue.repairability in {"semantic_patch", "plan_patch"}
            )
        pending_rerender_projections = _scoped_rerender_projections(current)
        if pending_rerender_projections:
            pending_prewrite_build = prewrite_build
        proposal_ready = False
        pass_index += 1

    if last_report is None:
        last_report = GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=False,
            artifact_counts={},
            tribunal_status="not_run",
            issues=("post-confirm fixpoint exhausted before a package report could be built",),
        )
    manifest = build_greenfield_post_confirm_manifest(
        report=last_report,
        status="failed",
        stop_reason=stop_reason,
        elapsed_seconds=max(0.0, clock() - started),
        passes=len(pass_records),
        pass_records=pass_records,
        repaired_issue_codes=repaired_issue_codes,
        max_passes=bounded_passes,
        budget_seconds=active_budget_seconds,
        requested_repair_tier=requested_tier,
        active_repair_tier=active_tier,
        rescue_activated=rescue_activated,
        quality_lenses=(
            build_greenfield_quality_lens_report(last_prewrite_build.package)
            if last_prewrite_build is not None
            else None
        ),
        semantic_compiler=(
            compile_greenfield_semantics(last_prewrite_build.package.proposal).to_dict()
            if last_prewrite_build is not None
            else None
        ),
        last_repair_patchset_request=last_repair_patchset_request,
    )
    try:
        raise_for_failed_greenfield_completion(last_report)
    except ValueError as exc:
        raise GreenfieldPostConfirmEngineError(str(exc), manifest=manifest) from exc
    raise RuntimeError(f"greenfield post-confirm engine stopped before completion: {manifest['stop_reason']}")


def classify_greenfield_post_confirm_issues(
    report: GreenfieldCompletionReport,
) -> tuple[GreenfieldPostConfirmIssue, ...]:
    """Return issue records without deriving repair semantics from prose."""

    if report.findings:
        finding_messages = {normalize_string(finding.message) for finding in report.findings}
        legacy_issues = tuple(
            _legacy_untyped_issue(issue)
            for issue in report.issues
            if normalize_string(issue) and normalize_string(issue) not in finding_messages
        )
        return (
            *tuple(_issue_from_review_finding(finding) for finding in report.findings),
            *legacy_issues,
        )
    return tuple(_legacy_untyped_issue(issue) for issue in report.issues if str(issue or "").strip())


def _normalize_repair_tier(value: str) -> str:
    tier = str(value or "auto").strip().casefold().replace("_", "-")
    aliases = {
        "default": "auto",
        "premium": "deep",
        "deep-repair": "deep",
        "ci": "deep",
        "ci-simulation": "deep",
    }
    tier = aliases.get(tier, tier)
    if tier not in POST_CONFIRM_REPAIR_TIERS:
        return "auto"
    return tier


def _normalize_active_repair_tier(value: str) -> str:
    tier = _normalize_repair_tier(value)
    return "standard" if tier == "auto" else tier


def _initial_active_tier(requested_tier: str) -> str:
    tier = _normalize_repair_tier(requested_tier)
    return "standard" if tier == "auto" else tier


def _tier_budget_seconds(tier: str, *, fallback: float) -> float:
    active = _normalize_active_repair_tier(tier)
    if active == "deep":
        return POST_CONFIRM_DEEP_BUDGET_SECONDS
    if active == "rescue":
        return POST_CONFIRM_RESCUE_BUDGET_SECONDS
    try:
        value = float(fallback)
    except (TypeError, ValueError):
        value = POST_CONFIRM_STANDARD_BUDGET_SECONDS
    return min(value if value > 0 else POST_CONFIRM_STANDARD_BUDGET_SECONDS, POST_CONFIRM_STANDARD_BUDGET_SECONDS)


def _rescue_eligible(
    issues: Sequence[GreenfieldPostConfirmIssue],
    *,
    patchset_request: Mapping[str, Any] | None = None,
) -> bool:
    if not issues:
        return False
    if any(issue.repairability == "unrepairable" for issue in issues):
        return False
    if patchset_request is not None and not _patchset_has_operations(patchset_request):
        return False
    rescue_codes = {
        "artifact_shape_drift",
        "atlas_render_quality",
        "component_contract_quality",
        "generated_copy_quality",
        "missing_semantic_model",
        RESCUE_PROBE_CODE,
        STRUCTURED_RESCUE_PROOF_CODE,
        "post_confirm_contract",
        "proposal_quality_gate",
        "quality_lens_gap",
        "release_package_drift",
        "semantic_alignment",
        "semantic_compiler",
        "semantic_drift",
    }
    repairable_types = {"semantic_patch", "plan_patch", "safe_package_repair"}
    return any(issue.code in rescue_codes and issue.repairability in repairable_types for issue in issues)


def _patchset_has_operations(patchset_request: Mapping[str, Any]) -> bool:
    operations = patchset_request.get("operations")
    return isinstance(operations, Sequence) and not isinstance(operations, (str, bytes)) and bool(operations)


def _direct_rerender_projections(issues: Sequence[GreenfieldPostConfirmIssue]) -> tuple[str, ...]:
    projections = tuple(
        dict.fromkeys(
            issue.projection_id
            for issue in issues
            if issue.repairability == "projection_rerender" and issue.projection_id
        )
    )
    if not projections:
        return ()
    expanded = patch_expand_projection_scope(projections)
    if patch_scope_requires_full_prewrite(expanded):
        return ()
    return expanded


def _projection_rerender_contract_report(
    report: GreenfieldCompletionReport,
    *,
    projections: Sequence[str],
) -> GreenfieldCompletionReport:
    scope = ", ".join(projections) or "unknown projection"
    message = (
        "post-confirm projection rerender required for "
        f"{scope}, but no rerender_prewrite callback was configured"
    )
    finding = review_finding(
        code="post_confirm_contract",
        surface="post_confirm",
        target_path="rerender_prewrite",
        projection_id="review_report",
        semantic_node_id="PostConfirmEngine.rerender_prewrite",
        severity="critical",
        repairability="unrepairable",
        owner="post_confirm_engine",
        source="projection_rerender_contract",
        message=message,
    )
    return replace(
        report,
        status="failed",
        issues=(message, *tuple(report.issues)),
        findings=(finding, *tuple(report.findings)),
    )


def build_greenfield_post_confirm_manifest(
    *,
    report: GreenfieldCompletionReport,
    status: str,
    stop_reason: str,
    elapsed_seconds: float,
    passes: int,
    pass_records: Sequence[GreenfieldPostConfirmPass],
    repaired_issue_codes: set[str],
    max_passes: int,
    budget_seconds: float,
    requested_repair_tier: str = "standard",
    active_repair_tier: str = "standard",
    rescue_activated: bool = False,
    whole_project_elapsed_seconds: float | None = None,
    write_transaction_status: str = "not_started",
    quality_lenses: Mapping[str, Any] | None = None,
    semantic_compiler: Mapping[str, Any] | None = None,
    last_repair_patchset_request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the operator-visible quality manifest for the post-confirm path."""

    typed_issues = classify_greenfield_post_confirm_issues(report)
    hard_blocker = next((issue.to_dict() for issue in typed_issues if issue.repairability == "unrepairable"), None)
    manifest: dict[str, Any] = {
        "version": POST_CONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": POST_CONFIRM_ENGINE_VERSION,
        "status": status,
        "validation_status": report.status,
        "stop_reason": stop_reason,
        "budget_seconds": float(budget_seconds),
        "standard_budget_seconds": POST_CONFIRM_STANDARD_BUDGET_SECONDS,
        "rescue_budget_seconds": POST_CONFIRM_RESCUE_BUDGET_SECONDS,
        "deep_budget_seconds": POST_CONFIRM_DEEP_BUDGET_SECONDS,
        "requested_repair_tier": _normalize_repair_tier(requested_repair_tier),
        "repair_tier": _normalize_active_repair_tier(active_repair_tier),
        "rescue_activated": bool(rescue_activated),
        "repair_tier_policy": {
            "standard": "under 60s when no host-semantic rescue is needed",
            "rescue": "up to 90s only after a repairable final semantic or quality gate failure",
            "deep": "up to 120s only when explicitly requested for premium/deep repair or CI simulation",
        },
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "passes": int(passes),
        "max_passes": int(max_passes),
        "artifact_counts": dict(report.artifact_counts),
        "issue_count": len(typed_issues),
        "issue_codes": sorted({issue.code for issue in typed_issues}),
        "issues": [issue.to_dict() for issue in typed_issues],
        "review_report": review_report_from_findings(report.findings).to_dict(),
        "patchset_request": patchset_request_from_findings(report.findings).to_dict(),
        "repaired_issue_codes": sorted(repaired_issue_codes),
        "hard_blocker": hard_blocker,
        "pass_records": [record.to_dict() for record in pass_records],
        "quality_lenses": dict(quality_lenses or {}),
        "semantic_compiler": dict(semantic_compiler or {}),
        "write_transaction": {
            "status": write_transaction_status,
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": status == "passed",
        },
    }
    if last_repair_patchset_request is not None:
        manifest["last_repair_patchset_request"] = dict(last_repair_patchset_request)
    if whole_project_elapsed_seconds is not None:
        manifest["whole_project_elapsed_seconds"] = round(float(whole_project_elapsed_seconds), 3)
    return manifest


def finalize_greenfield_post_confirm_manifest(
    manifest: Mapping[str, Any],
    *,
    whole_project_elapsed_seconds: float,
    write_transaction_status: str,
) -> dict[str, Any]:
    """Attach final write evidence after the guarded write phase completes."""

    payload = dict(manifest)
    payload["whole_project_elapsed_seconds"] = round(float(whole_project_elapsed_seconds), 3)
    transaction = dict(payload.get("write_transaction") if isinstance(payload.get("write_transaction"), Mapping) else {})
    transaction["status"] = write_transaction_status
    transaction["rollback_guard"] = "enabled"
    payload["write_transaction"] = transaction
    return payload


def _replace_prewrite_package(prewrite_build: Any, package: Any) -> Any:
    try:
        return replace(
            prewrite_build,
            package=package,
            backlog_result=package.backlog_result or prewrite_build.backlog_result,
        )
    except TypeError:
        return prewrite_build


def _repair_proposal_with_context(
    repair_proposal: Callable[..., Mapping[str, Any]],
    proposal: Mapping[str, Any],
    context: GreenfieldPostConfirmRepairContext,
) -> Mapping[str, Any]:
    if _accepts_repair_context(repair_proposal):
        return repair_proposal(proposal, context)
    return repair_proposal(proposal)


def _accepts_repair_context(callback: Callable[..., Any]) -> bool:
    try:
        parameters = inspect.signature(callback).parameters.values()
    except (TypeError, ValueError):
        return True
    positional_capacity = 0
    for parameter in parameters:
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }:
            positional_capacity += 1
    return positional_capacity >= 2


def _scoped_rerender_projections(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    ledger = proposal.get("post_confirm_patch_application_ledger")
    if not isinstance(ledger, list) or not ledger:
        return ()
    latest = ledger[-1]
    if not isinstance(latest, Mapping):
        return ()
    if latest.get("rerender_scope") != "affected_projections":
        return ()
    if latest.get("full_prewrite_required"):
        return ()
    return tuple(normalize_string_list(latest.get("rerender_projections"), limit=16))


def _legacy_untyped_issue(message: str) -> GreenfieldPostConfirmIssue:
    text = str(message or "").strip()
    return GreenfieldPostConfirmIssue(
        code="legacy_untyped_report",
        surface="post_confirm",
        path="",
        severity="critical",
        repairability="unrepairable",
        owner="typed_review_report",
        message=text,
        source="legacy_untyped_report",
    )


def _issue_from_review_finding(finding: GreenfieldReviewFinding) -> GreenfieldPostConfirmIssue:
    return GreenfieldPostConfirmIssue(
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


def _failure_signature(report: GreenfieldCompletionReport) -> str:
    finding_signature = [
        {
            "code": finding.code,
            "surface": finding.surface,
            "target_path": finding.target_path,
            "projection_id": finding.projection_id,
            "semantic_node_id": finding.semantic_node_id,
            "repairability": finding.repairability,
            "source": finding.source,
            "message": finding.message,
        }
        for finding in report.findings
    ]
    payload = {
        "status": report.status,
        "findings": finding_signature,
        "issues": [] if finding_signature else list(report.issues),
        "artifact_counts": dict(report.artifact_counts),
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "GreenfieldPostConfirmEngineResult",
    "GreenfieldPostConfirmEngineError",
    "GreenfieldPostConfirmIssue",
    "GreenfieldPostConfirmRepairContext",
    "POST_CONFIRM_BUDGET_SECONDS",
    "POST_CONFIRM_DEEP_BUDGET_SECONDS",
    "POST_CONFIRM_ENGINE_VERSION",
    "POST_CONFIRM_MAX_PASSES",
    "POST_CONFIRM_QUALITY_MANIFEST_VERSION",
    "POST_CONFIRM_REPAIR_TIERS",
    "POST_CONFIRM_RESCUE_BUDGET_SECONDS",
    "POST_CONFIRM_STANDARD_BUDGET_SECONDS",
    "build_greenfield_post_confirm_manifest",
    "classify_greenfield_post_confirm_issues",
    "finalize_greenfield_post_confirm_manifest",
    "run_greenfield_post_confirm_engine",
]
