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
from odylith.runtime.domain_intelligence.greenfield_post_confirm_repair import (
    repair_greenfield_package_until_clean,
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
POST_CONFIRM_BUDGET_SECONDS = 60.0
POST_CONFIRM_MAX_PASSES = 4


@dataclass(frozen=True)
class GreenfieldPostConfirmIssue:
    code: str
    surface: str
    path: str
    severity: str
    repairability: str
    owner: str
    message: str

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
    quality_lenses: Mapping[str, Any]
    semantic_compiler: Mapping[str, Any]


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
    proposal_ready: bool = False,
    max_passes: int = POST_CONFIRM_MAX_PASSES,
    budget_seconds: float = POST_CONFIRM_BUDGET_SECONDS,
    clock: Callable[[], float] = time.perf_counter,
) -> GreenfieldPostConfirmEngineResult:
    """Build, repair, and revalidate post-confirm output before governed writes."""

    started = clock()
    seen_failures: set[str] = set()
    pass_records: list[GreenfieldPostConfirmPass] = []
    repaired_issue_codes: set[str] = set()
    last_report: GreenfieldCompletionReport | None = None
    last_prewrite_build: Any = None
    current = proposal
    bounded_passes = max(1, int(max_passes))
    stop_reason = "max_passes"
    tribunal: Any = None

    for pass_index in range(bounded_passes):
        elapsed = max(0.0, clock() - started)
        if elapsed >= budget_seconds:
            stop_reason = "time_budget_exhausted"
            break

        tribunal = run_greenfield_tribunal(current, release_selector=release_selector)
        raise_for_failed_greenfield_tribunal(tribunal)
        if not (proposal_ready and pass_index == 0):
            assert_greenfield_completion_ready(current, release_selector=release_selector)

        prewrite_build = build_prewrite(current, tribunal)
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
                    budget_seconds=budget_seconds,
                    quality_lenses=quality_lenses,
                    semantic_compiler=semantic_compiler,
                ),
            )

        failure_signature = _failure_signature(report)
        if failure_signature in seen_failures:
            stop_reason = "no_progress"
            break
        seen_failures.add(failure_signature)
        current = _repair_proposal_with_context(
            repair_proposal,
            current,
            GreenfieldPostConfirmRepairContext(
                pass_index=pass_index,
                elapsed_seconds=round(max(0.0, clock() - started), 3),
                budget_seconds=float(budget_seconds),
                report=report,
                issues=typed_issues,
                quality_lenses=quality_lenses,
                semantic_compiler=semantic_compiler,
            ),
        )
        proposal_ready = False

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
        budget_seconds=budget_seconds,
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
    )
    try:
        raise_for_failed_greenfield_completion(last_report)
    except ValueError as exc:
        raise GreenfieldPostConfirmEngineError(str(exc), manifest=manifest) from exc
    raise RuntimeError(f"greenfield post-confirm engine stopped before completion: {manifest['stop_reason']}")


def classify_greenfield_post_confirm_issues(
    report: GreenfieldCompletionReport,
) -> tuple[GreenfieldPostConfirmIssue, ...]:
    """Classify completion report strings into stable issue records."""

    return tuple(_classify_issue(issue) for issue in report.issues)


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
    whole_project_elapsed_seconds: float | None = None,
    write_transaction_status: str = "not_started",
    quality_lenses: Mapping[str, Any] | None = None,
    semantic_compiler: Mapping[str, Any] | None = None,
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
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "passes": int(passes),
        "max_passes": int(max_passes),
        "artifact_counts": dict(report.artifact_counts),
        "issue_count": len(typed_issues),
        "issue_codes": sorted({issue.code for issue in typed_issues}),
        "issues": [issue.to_dict() for issue in typed_issues],
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


def _classify_issue(message: str) -> GreenfieldPostConfirmIssue:
    text = str(message or "").strip()
    code = _issue_code(text)
    return GreenfieldPostConfirmIssue(
        code=code,
        surface=_issue_surface(text),
        path=_issue_path(text),
        severity=_issue_severity(code),
        repairability=_issue_repairability(code, text),
        owner=_issue_owner(code, text),
        message=text,
    )


def _issue_code(message: str) -> str:
    lowered = message.casefold()
    if "provider-free" in lowered or "provider call" in lowered:
        return "provider_call_leak"
    if "requires greenfieldsemanticmodel" in lowered or "semantic model" in lowered and "requires" in lowered:
        return "missing_semantic_model"
    if "greenfieldsemanticcompiler" in lowered:
        return "semantic_compiler"
    if "semantic" in lowered and "drift" in lowered:
        return "semantic_drift"
    if "semantic" in lowered and ("alignment" in lowered or "coverage" in lowered or "missing" in lowered):
        return "semantic_alignment"
    if "tribunal" in lowered or "validation gate" in lowered:
        return "validation_gate_failure"
    if "release" in lowered and ("assignment" in lowered or "target" in lowered):
        return "release_package_drift"
    if "quality lens" in lowered:
        return "quality_lens_gap"
    if "must render one" in lowered or "drifted from" in lowered or "missing rendered" in lowered:
        return "artifact_shape_drift"
    if "mermaid" in lowered or "atlas" in lowered:
        return "atlas_render_quality"
    if _copy_quality_message(lowered):
        return "generated_copy_quality"
    if "component" in lowered and ("label" in lowered or "registry" in lowered or "spec" in lowered):
        return "component_contract_quality"
    return "post_confirm_contract"


def _copy_quality_message(lowered: str) -> bool:
    return any(
        token in lowered
        for token in (
            "grammar drift",
            "malformed",
            "mixed finite/base",
            "invalid verb",
            "clipped",
            "dangling",
            "punctuation",
            "sentence-fragment",
            "repeats",
            "placeholder",
            "vague",
            "copy",
        )
    )


def _issue_surface(message: str) -> str:
    if " `" in message:
        return message.split(" `", 1)[0].strip() or "post_confirm"
    lowered = message.casefold()
    if "radar" in lowered:
        return "radar"
    if "registry" in lowered or "component" in lowered:
        return "registry"
    if "atlas" in lowered or "mermaid" in lowered or "diagram" in lowered:
        return "atlas"
    if "project brief" in lowered:
        return "project_brief"
    if "next steps" in lowered:
        return "next_steps"
    if "release" in lowered:
        return "release"
    return "post_confirm"


def _issue_path(message: str) -> str:
    if "`" not in message:
        return ""
    parts = message.split("`")
    return parts[1].strip() if len(parts) > 1 else ""


def _issue_severity(code: str) -> str:
    if code in {"provider_call_leak", "missing_semantic_model", "validation_gate_failure"}:
        return "critical"
    if code in {"semantic_compiler", "semantic_drift", "semantic_alignment", "artifact_shape_drift", "quality_lens_gap"}:
        return "high"
    return "medium"


def _issue_repairability(code: str, message: str) -> str:
    lowered = message.casefold()
    if code in {"provider_call_leak", "validation_gate_failure"}:
        return "unrepairable"
    if "modal/base-form grammar drift" in lowered or "mixed finite/base action prose" in lowered:
        return "safe_package_repair"
    if "malformed ownership verb pair" in lowered or "malformed component responsibility" in lowered:
        return "safe_package_repair"
    if "malformed verb pair" in lowered and code == "generated_copy_quality":
        return "safe_package_repair"
    if code in {"generated_copy_quality", "semantic_compiler", "semantic_alignment", "semantic_drift", "component_contract_quality"}:
        return "proposal_repair"
    if code in {
        "missing_semantic_model",
        "artifact_shape_drift",
        "atlas_render_quality",
        "release_package_drift",
        "quality_lens_gap",
    }:
        return "proposal_repair"
    return "proposal_repair"


def _issue_owner(code: str, message: str) -> str:
    lowered = message.casefold()
    if code == "quality_lens_gap":
        return "quality_lens_contract"
    if "radar" in lowered:
        return "radar_renderer"
    if "registry" in lowered or "component" in lowered:
        return "registry_renderer"
    if "atlas" in lowered or "mermaid" in lowered or "diagram" in lowered:
        return "atlas_renderer"
    if "next steps" in lowered:
        return "operator_experience_renderer"
    if code in {"semantic_compiler", "semantic_drift", "semantic_alignment", "missing_semantic_model"}:
        return "semantic_model_compiler"
    if code == "generated_copy_quality":
        return "generated_copy_quality_kernel"
    return "post_confirm_engine"


def _failure_signature(report: GreenfieldCompletionReport) -> str:
    payload = {
        "status": report.status,
        "issues": list(report.issues),
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
    "POST_CONFIRM_ENGINE_VERSION",
    "POST_CONFIRM_MAX_PASSES",
    "POST_CONFIRM_QUALITY_MANIFEST_VERSION",
    "build_greenfield_post_confirm_manifest",
    "classify_greenfield_post_confirm_issues",
    "finalize_greenfield_post_confirm_manifest",
    "run_greenfield_post_confirm_engine",
]
