"""Benchmark Compare helpers for the Odylith evaluation layer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from odylith.install.manager import product_source_version
from odylith.install.release_assets import fetch_release
from odylith.install.state import AUTHORITATIVE_RELEASE_REPO
from odylith.runtime.evaluation import odylith_benchmark_runner as runner
from odylith.runtime.evaluation import benchmark_metric_helpers
from odylith.runtime.evaluation.benchmark_snapshot_fallbacks import (
    load_release_baseline_summary,
    load_tracked_latest_summary,
)
from odylith.runtime.governance.release_maintainer_overrides import (
    BenchmarkProofOverride,
    load_benchmark_proof_override,
)

_FAIL_LATENCY_DELTA_MS = 20.0
_WARN_LATENCY_DELTA_MS = 10.0
_FAIL_PROMPT_TOKEN_DELTA = 40.0
_WARN_PROMPT_TOKEN_DELTA = 20.0
_FAIL_RATE_DELTA = 0.05
_WARN_RATE_DELTA = 0.02
_FAIL_CRITICAL_RATE_DELTA = 0.01
_WARN_CRITICAL_RATE_DELTA = 0.005
_FAIL_WIDENING_RATE_DELTA = 0.02
_WARN_WIDENING_RATE_DELTA = 0.01
_SUMMARY_DELTA_FIELDS = {
    "latency_delta_ms": "latency_delta_ms",
    "prompt_token_delta": "prompt_token_delta",
    "required_path_recall_delta": "required_path_recall_delta",
    "validation_success_delta": "validation_success_delta",
    "critical_required_path_recall_delta": "critical_required_path_recall_delta",
    "critical_validation_success_delta": "critical_validation_success_delta",
    "hallucinated_surface_rate_delta": "hallucinated_surface_rate_delta",
    "unnecessary_widening_rate_delta": "unnecessary_widening_rate_delta",
}


@dataclass(frozen=True)
class BenchmarkComparison:
    status: str
    candidate_report_id: str
    candidate_product_version: str
    baseline_report_id: str
    baseline_product_version: str
    baseline_source: str
    summary: dict[str, Any]
    deltas: dict[str, float]
    notes: tuple[str, ...]
    blocking: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidate_report_id": self.candidate_report_id,
            "candidate_product_version": self.candidate_product_version,
            "baseline_report_id": self.baseline_report_id,
            "baseline_product_version": self.baseline_product_version,
            "baseline_source": self.baseline_source,
            "summary": self.summary,
            "deltas": self.deltas,
            "notes": list(self.notes),
            "blocking": self.blocking,
        }

def _history_reports(*, repo_root: Path) -> list[dict[str, Any]]:
    root = runner.benchmark_root(repo_root=repo_root)
    if not root.is_dir():
        return []
    reports: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        if path.name == "latest.v1.json" or path.name == "progress.v1.json" or path.name.startswith("latest-"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            reports.append(payload)
    reports.sort(key=lambda item: str(item.get("generated_utc") or ""), reverse=True)
    return reports


def _latest_published_release_version(*, repo_root: Path, repo: str = AUTHORITATIVE_RELEASE_REPO) -> str:
    try:
        release = fetch_release(repo_root=repo_root, repo=repo, version="latest")
    except Exception:
        return ""
    return str(getattr(release, "version", "") or "").strip()


def _report_product_version(report: Mapping[str, Any]) -> str:
    return str(report.get("product_version") or report.get("source_version") or "").strip()


def _summary_with_version(summary: Mapping[str, Any], *, product_version: str) -> dict[str, Any]:
    merged = dict(summary)
    version = str(merged.get("product_version") or product_version or "").strip()
    if version:
        merged["product_version"] = version
    return merged


def _eligible_release_report(report: Mapping[str, Any]) -> bool:
    selection = dict(report.get("selection", {})) if isinstance(report.get("selection"), Mapping) else {}
    cache_profiles = report.get("cache_profiles")
    return bool(
        report.get("latest_eligible")
        and bool(selection.get("full_corpus_selected"))
        and isinstance(cache_profiles, list)
        and [str(token).strip() for token in cache_profiles if str(token).strip()] == list(runner.DEFAULT_CACHE_PROFILES)
    )


def _resolve_candidate_summary(*, repo_root: Path) -> tuple[dict[str, Any] | None, str]:
    candidate_report = runner.load_latest_benchmark_report(repo_root=repo_root)
    if candidate_report and runner.benchmark_report_matches_current_tree(repo_root=repo_root, report=candidate_report):
        return _summary_with_version(
            runner.compact_report_summary(candidate_report),
            product_version=_report_product_version(candidate_report),
        ), "latest-runtime-report"
    if candidate_report:
        stale_summary = _summary_with_version(
            runner.compact_report_summary(candidate_report),
            product_version=_report_product_version(candidate_report),
        )
        stale_summary["current_tree_identity_match"] = False
        stale_summary["stale_runtime_report"] = True
        return stale_summary, "latest-runtime-report-stale"
    tracked_summary = load_tracked_latest_summary(repo_root=repo_root)
    if tracked_summary:
        summary = dict(tracked_summary)
        tracked_report_id = str(summary.get("report_id") or "").strip()
        summary.setdefault("current_tree_identity_match", False)
        summary["tracked_summary_only"] = True
        summary["tracked_summary_backing_report_present"] = bool(
            tracked_report_id and runner.history_report_path(repo_root=repo_root, report_id=tracked_report_id).is_file()
        )
        if tracked_report_id and not bool(summary.get("tracked_summary_backing_report_present")):
            summary["tracked_summary_backing_report_missing"] = True
        return summary, "tracked-latest-summary"
    return None, "missing-latest"


def _resolve_baseline_report(*, repo_root: Path, baseline: str, candidate_report: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    normalized = str(baseline or "").strip().lower() or "last-shipped"
    reports = _history_reports(repo_root=repo_root)
    candidate_report_id = str(candidate_report.get("report_id") or "").strip()
    if normalized != "last-shipped":
        for report in reports:
            if str(report.get("report_id") or "").strip() != candidate_report_id:
                return _summary_with_version(
                    runner.compact_report_summary(report),
                    product_version=_report_product_version(report),
                ), "latest-history"
        return None, "missing-history"

    published_version = _latest_published_release_version(repo_root=repo_root)
    if published_version:
        for report in reports:
            if (
                str(report.get("report_id") or "").strip() != candidate_report_id
                and _eligible_release_report(report)
                and _report_product_version(report) == published_version
            ):
                return _summary_with_version(
                    runner.compact_report_summary(report),
                    product_version=_report_product_version(report),
                ), "last-shipped"
        baseline_summary = load_release_baseline_summary(repo_root=repo_root, version=published_version)
        if baseline_summary:
            return baseline_summary, "last-shipped"
    return None, "missing-last-shipped"


def _override_notes(override: BenchmarkProofOverride) -> tuple[str, str]:
    return (
        f"Maintainer benchmark override active for v{override.version}: {override.reason}",
        "Benchmark proof and compare are advisory for this release and return as warnings instead of blockers.",
    )


def _override_unavailable(
    *,
    override: BenchmarkProofOverride,
    baseline_source: str,
    candidate_report_id: str,
    candidate_product_version: str,
    summary: dict[str, Any],
    notes: tuple[str, ...],
) -> BenchmarkComparison:
    return BenchmarkComparison(
        status="warn",
        candidate_report_id=candidate_report_id,
        candidate_product_version=candidate_product_version,
        baseline_report_id="",
        baseline_product_version="",
        baseline_source=baseline_source,
        summary=summary,
        deltas={},
        notes=(*_override_notes(override), *notes),
        blocking=False,
    )


def _downgrade_blocking_result(
    result: BenchmarkComparison,
    *,
    override: BenchmarkProofOverride,
) -> BenchmarkComparison:
    return BenchmarkComparison(
        status="warn",
        candidate_report_id=result.candidate_report_id,
        candidate_product_version=result.candidate_product_version,
        baseline_report_id=result.baseline_report_id,
        baseline_product_version=result.baseline_product_version,
        baseline_source=result.baseline_source,
        summary=result.summary,
        deltas=result.deltas,
        notes=(*_override_notes(override), *result.notes),
        blocking=False,
    )


def compare_latest_to_baseline(*, repo_root: str | Path, baseline: str = "last-shipped") -> BenchmarkComparison:
    root = Path(repo_root).expanduser().resolve()
    source_version = product_source_version(repo_root=root)
    override = load_benchmark_proof_override(repo_root=root, version=source_version)
    candidate_summary, candidate_source = _resolve_candidate_summary(repo_root=root)
    if candidate_summary is None:
        if override is not None:
            return _override_unavailable(
                override=override,
                baseline_source=candidate_source,
                candidate_report_id="",
                candidate_product_version=source_version,
                summary={},
                notes=("No latest benchmark report is available under `.odylith/runtime/odylith-benchmarks/latest.v1.json`.",),
            )
        return BenchmarkComparison(
            status="unavailable",
            candidate_report_id="",
            candidate_product_version="",
            baseline_report_id="",
            baseline_product_version="",
            baseline_source=candidate_source,
            summary={},
            deltas={},
            notes=("No latest benchmark report is available under `.odylith/runtime/odylith-benchmarks/latest.v1.json`.",),
            blocking=True,
        )
    candidate_version = str(candidate_summary.get("product_version", "")).strip()
    current_tree_identity_match = bool(
        candidate_summary.get(
            "current_tree_identity_match",
            candidate_source == "latest-runtime-report",
        )
    )
    if candidate_source != "latest-runtime-report" or not current_tree_identity_match:
        notes = [
            "No current-tree authoritative proof candidate is available for benchmark compare.",
            f"Candidate source `{candidate_source}` is not a current-head proof report.",
            "Record a fresh current-tree proof report before treating compare as a release gate.",
        ]
        if bool(candidate_summary.get("tracked_summary_backing_report_missing")):
            notes.append(
                "Tracked benchmark publication summary points at a missing runtime report artifact and is not safe benchmark authority."
            )
        notes = tuple(notes)
        if override is not None:
            return _override_unavailable(
                override=override,
                baseline_source=candidate_source,
                candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
                candidate_product_version=candidate_version or source_version,
                summary={"candidate": candidate_summary, "baseline": {}},
                notes=notes,
            )
        return BenchmarkComparison(
            status="unavailable",
            candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
            candidate_product_version=candidate_version,
            baseline_report_id="",
            baseline_product_version="",
            baseline_source=candidate_source,
            summary={"candidate": candidate_summary, "baseline": {}},
            deltas={},
            notes=notes,
            blocking=True,
        )
    if source_version and candidate_version and candidate_version != source_version:
        if override is not None:
            return _override_unavailable(
                override=override,
                baseline_source=candidate_source,
                candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
                candidate_product_version=candidate_version,
                summary={"candidate": candidate_summary, "baseline": {}},
                notes=(
                    f"Latest benchmark candidate version `{candidate_version}` does not match current source version `{source_version}`.",
                    "Record a fresh benchmark report for the current source version before treating compare as a release gate.",
                ),
            )
        return BenchmarkComparison(
            status="unavailable",
            candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
            candidate_product_version=candidate_version,
            baseline_report_id="",
            baseline_product_version="",
            baseline_source=candidate_source,
            summary={"candidate": candidate_summary, "baseline": {}},
            deltas={},
            notes=(
                f"Latest benchmark candidate version `{candidate_version}` does not match current source version `{source_version}`.",
                "Record a fresh benchmark report for the current source version before treating compare as a release gate.",
            ),
            blocking=True,
        )
    baseline_summary, baseline_source = _resolve_baseline_report(
        repo_root=root,
        baseline=baseline,
        candidate_report=candidate_summary,
    )
    if baseline_summary is None:
        published_version = _latest_published_release_version(repo_root=repo_root)
        if not published_version and baseline_source == "missing-last-shipped":
            notes = (
                "No published release exists yet, so there is no last-shipped benchmark baseline to compare against.",
                "Treat this as a first-release warning; record the baseline after the first release ships.",
            )
            return BenchmarkComparison(
                status="warn",
                candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
                candidate_product_version=str(candidate_summary.get("product_version", "")).strip(),
                baseline_report_id="",
                baseline_product_version="",
                baseline_source="first-release-no-last-shipped",
                summary={"candidate": candidate_summary, "baseline": {}},
                deltas={},
                notes=notes,
                blocking=False,
            )
        if override is not None:
            return _override_unavailable(
                override=override,
                baseline_source=baseline_source,
                candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
                candidate_product_version=str(candidate_summary.get("product_version", "")).strip(),
                summary={"candidate": candidate_summary, "baseline": {}},
                notes=(
                    "No eligible benchmark baseline is available for comparison.",
                    "Record a full-corpus default-cache benchmark on the last shipped release before treating compare as a hard gate.",
                ),
            )
        return BenchmarkComparison(
            status="unavailable",
            candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
            candidate_product_version=str(candidate_summary.get("product_version", "")).strip(),
            baseline_report_id="",
            baseline_product_version="",
            baseline_source=baseline_source,
            summary={"candidate": candidate_summary, "baseline": {}},
            deltas={},
            notes=(
                "No eligible benchmark baseline is available for comparison.",
                "Record a full-corpus default-cache benchmark on the last shipped release before treating compare as a hard gate.",
            ),
            blocking=True,
        )
    deltas = benchmark_metric_helpers.summary_deltas(
        candidate=candidate_summary,
        baseline=baseline_summary,
        field_map=_SUMMARY_DELTA_FIELDS,
    )
    notes: list[str] = []
    failures: list[str] = []
    warnings: list[str] = []
    candidate_status = str(candidate_summary.get("status", "")).strip()
    baseline_status = str(baseline_summary.get("status", "")).strip()
    if candidate_status != "provisional_pass":
        failures.append(f"latest report status is `{candidate_status or 'unknown'}`")
    if baseline_status != "provisional_pass":
        warnings.append(f"baseline report status is `{baseline_status or 'unknown'}`")
    if deltas["latency_delta_ms"] > _FAIL_LATENCY_DELTA_MS:
        failures.append(f"latency regressed by {deltas['latency_delta_ms']:.3f}ms")
    elif deltas["latency_delta_ms"] > _WARN_LATENCY_DELTA_MS:
        warnings.append(f"latency regressed by {deltas['latency_delta_ms']:.3f}ms")
    if deltas["prompt_token_delta"] > _FAIL_PROMPT_TOKEN_DELTA:
        failures.append(f"prompt cost regressed by {deltas['prompt_token_delta']:.3f} tokens")
    elif deltas["prompt_token_delta"] > _WARN_PROMPT_TOKEN_DELTA:
        warnings.append(f"prompt cost regressed by {deltas['prompt_token_delta']:.3f} tokens")
    if deltas["required_path_recall_delta"] < -_FAIL_RATE_DELTA:
        failures.append(f"required-path recall regressed by {abs(deltas['required_path_recall_delta']):.3f}")
    elif deltas["required_path_recall_delta"] < -_WARN_RATE_DELTA:
        warnings.append(f"required-path recall regressed by {abs(deltas['required_path_recall_delta']):.3f}")
    if deltas["validation_success_delta"] < -_FAIL_RATE_DELTA:
        failures.append(f"validation success regressed by {abs(deltas['validation_success_delta']):.3f}")
    elif deltas["validation_success_delta"] < -_WARN_RATE_DELTA:
        warnings.append(f"validation success regressed by {abs(deltas['validation_success_delta']):.3f}")
    if deltas["critical_required_path_recall_delta"] < -_FAIL_CRITICAL_RATE_DELTA:
        failures.append(f"critical required-path recall regressed by {abs(deltas['critical_required_path_recall_delta']):.3f}")
    elif deltas["critical_required_path_recall_delta"] < -_WARN_CRITICAL_RATE_DELTA:
        warnings.append(f"critical required-path recall regressed by {abs(deltas['critical_required_path_recall_delta']):.3f}")
    if deltas["critical_validation_success_delta"] < -_FAIL_CRITICAL_RATE_DELTA:
        failures.append(f"critical validation success regressed by {abs(deltas['critical_validation_success_delta']):.3f}")
    elif deltas["critical_validation_success_delta"] < -_WARN_CRITICAL_RATE_DELTA:
        warnings.append(f"critical validation success regressed by {abs(deltas['critical_validation_success_delta']):.3f}")
    if deltas["hallucinated_surface_rate_delta"] > _FAIL_RATE_DELTA:
        failures.append(f"hallucinated-surface drift worsened by {deltas['hallucinated_surface_rate_delta']:.3f}")
    elif deltas["hallucinated_surface_rate_delta"] > _WARN_RATE_DELTA:
        warnings.append(f"hallucinated-surface drift worsened by {deltas['hallucinated_surface_rate_delta']:.3f}")
    if deltas["unnecessary_widening_rate_delta"] > _FAIL_WIDENING_RATE_DELTA:
        failures.append(f"unnecessary widening worsened by {deltas['unnecessary_widening_rate_delta']:.3f}")
    elif deltas["unnecessary_widening_rate_delta"] > _WARN_WIDENING_RATE_DELTA:
        warnings.append(f"unnecessary widening worsened by {deltas['unnecessary_widening_rate_delta']:.3f}")
    if failures:
        notes.append("Benchmark compare failed the current release threshold.")
        notes.extend(failures)
        status = "fail"
        blocking = True
    elif warnings:
        notes.append("Benchmark compare raised release warnings.")
        notes.extend(warnings)
        status = "warn"
        blocking = False
    else:
        notes.append("Benchmark compare passed against the stored release baseline.")
        status = "pass"
        blocking = False
    result = BenchmarkComparison(
        status=status,
        candidate_report_id=str(candidate_summary.get("report_id", "")).strip(),
        candidate_product_version=str(candidate_summary.get("product_version", "")).strip(),
        baseline_report_id=str(baseline_summary.get("report_id", "")).strip(),
        baseline_product_version=str(baseline_summary.get("product_version", "")).strip(),
        baseline_source=baseline_source,
        summary={"candidate": candidate_summary, "baseline": baseline_summary},
        deltas=deltas,
        notes=tuple(notes),
        blocking=blocking,
    )
    if override is not None and result.blocking:
        return _downgrade_blocking_result(result, override=override)
    return result


def _delta_direction(*, value: float, lower_is_better: bool, tolerance: float) -> str:
    numeric = float(value or 0.0)
    if abs(numeric) <= tolerance:
        return "unchanged"
    if lower_is_better:
        return "better" if numeric < 0.0 else "worse"
    return "better" if numeric > 0.0 else "worse"


def _format_delta_value(*, value: float, suffix: str, signed: bool = True, scale: float = 1.0) -> str:
    numeric = float(value or 0.0) * float(scale)
    token = f"{numeric:+.1f}" if signed else f"{numeric:.1f}"
    return f"{token} {suffix}".strip()


def build_benchmark_story(*, repo_root: str | Path, baseline: str = "last-shipped", limit: int = 4) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    comparison = compare_latest_to_baseline(repo_root=root, baseline=baseline)
    reports = _history_reports(repo_root=root)
    summary = dict(comparison.summary.get("candidate", {})) if isinstance(comparison.summary, Mapping) else {}
    baseline_summary = (
        dict(comparison.summary.get("baseline", {}))
        if isinstance(comparison.summary, Mapping)
        else {}
    )
    metrics = [
        {
            "label": "Prompt tokens",
            "direction": _delta_direction(
                value=float(comparison.deltas.get("prompt_token_delta", 0.0) or 0.0),
                lower_is_better=True,
                tolerance=1.0,
            ),
            "value": _format_delta_value(
                value=float(comparison.deltas.get("prompt_token_delta", 0.0) or 0.0),
                suffix="tokens",
            ),
        },
        {
            "label": "Latency",
            "direction": _delta_direction(
                value=float(comparison.deltas.get("latency_delta_ms", 0.0) or 0.0),
                lower_is_better=True,
                tolerance=1.0,
            ),
            "value": _format_delta_value(
                value=float(comparison.deltas.get("latency_delta_ms", 0.0) or 0.0),
                suffix="ms",
            ),
        },
        {
            "label": "Required-path recall",
            "direction": _delta_direction(
                value=float(comparison.deltas.get("required_path_recall_delta", 0.0) or 0.0),
                lower_is_better=False,
                tolerance=0.005,
            ),
            "value": _format_delta_value(
                value=float(comparison.deltas.get("required_path_recall_delta", 0.0) or 0.0),
                suffix="pts",
                scale=100.0,
            ),
        },
        {
            "label": "Validation success",
            "direction": _delta_direction(
                value=float(comparison.deltas.get("validation_success_delta", 0.0) or 0.0),
                lower_is_better=False,
                tolerance=0.005,
            ),
            "value": _format_delta_value(
                value=float(comparison.deltas.get("validation_success_delta", 0.0) or 0.0),
                suffix="pts",
                scale=100.0,
            ),
        },
    ]
    history_rows: list[dict[str, str]] = []
    candidate_report_id = comparison.candidate_report_id
    baseline_report_id = comparison.baseline_report_id
    for report in reports[: max(1, int(limit))]:
        compact = runner.compact_report_summary(report)
        report_id = str(compact.get("report_id", "")).strip()
        product_version = str(compact.get("product_version", "")).strip() or str(compact.get("source_version", "")).strip()
        badge = "History"
        if report_id and report_id == candidate_report_id:
            badge = "Current"
        elif report_id and report_id == baseline_report_id:
            badge = "Baseline"
        history_rows.append(
            {
                "badge": badge,
                "version": f"v{product_version}" if product_version and product_version[:1].isdigit() else (product_version or "unknown"),
                "status": str(compact.get("status", "")).strip() or "unknown",
                "report_id": report_id or "unknown",
                "generated_utc": str(compact.get("generated_utc", "")).strip() or "unknown",
            }
        )
    note = str(comparison.notes[0]).strip() if comparison.notes else ""
    candidate_version = str(summary.get("product_version", "")).strip() or comparison.candidate_product_version
    baseline_version = str(baseline_summary.get("product_version", "")).strip() or comparison.baseline_product_version
    return {
        "show": bool(candidate_version or comparison.status != "unavailable"),
        "status": comparison.status,
        "blocking": comparison.blocking,
        "headline": "Benchmark compare versus last shipped release",
        "summary": note or "Benchmark compare has no recorded note yet.",
        "candidate_version": candidate_version,
        "baseline_version": baseline_version,
        "baseline_source": comparison.baseline_source,
        "metrics": metrics,
        "history": history_rows,
        "notes": list(comparison.notes),
    }


def render_compare_text(result: BenchmarkComparison) -> str:
    return "\n".join(
        [
            "odylith benchmark compare",
            f"- status: {result.status}",
            f"- candidate_report_id: {result.candidate_report_id or '<none>'}",
            f"- candidate_product_version: {result.candidate_product_version or '<none>'}",
            f"- baseline_report_id: {result.baseline_report_id or '<none>'}",
            f"- baseline_product_version: {result.baseline_product_version or '<none>'}",
            f"- baseline_source: {result.baseline_source or '<none>'}",
            f"- latency_delta_ms: {float(result.deltas.get('latency_delta_ms', 0.0) or 0.0):.3f}",
            f"- prompt_token_delta: {float(result.deltas.get('prompt_token_delta', 0.0) or 0.0):.3f}",
            f"- required_path_recall_delta: {float(result.deltas.get('required_path_recall_delta', 0.0) or 0.0):.3f}",
            f"- validation_success_delta: {float(result.deltas.get('validation_success_delta', 0.0) or 0.0):.3f}",
            f"- critical_required_path_recall_delta: {float(result.deltas.get('critical_required_path_recall_delta', 0.0) or 0.0):.3f}",
            f"- critical_validation_success_delta: {float(result.deltas.get('critical_validation_success_delta', 0.0) or 0.0):.3f}",
            f"- hallucinated_surface_rate_delta: {float(result.deltas.get('hallucinated_surface_rate_delta', 0.0) or 0.0):.3f}",
            f"- unnecessary_widening_rate_delta: {float(result.deltas.get('unnecessary_widening_rate_delta', 0.0) or 0.0):.3f}",
            *[f"- note: {item}" for item in result.notes],
        ]
    )
