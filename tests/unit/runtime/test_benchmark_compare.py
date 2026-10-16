from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from odylith.install.release_assets import ReleaseInfo
from odylith.runtime.evaluation import benchmark_compare
from odylith.runtime.evaluation import benchmark_metric_helpers
from odylith.runtime.evaluation import odylith_benchmark_tree_identity as tree_identity_runtime


def _quality(**changes: float) -> dict[str, float]:
    return {
        "required_path_recall_rate": 0.95,
        "validation_success_rate": 0.95,
        "critical_required_path_recall_rate": 0.95,
        "critical_validation_success_rate": 0.95,
        "hallucinated_surface_rate": 0.1,
        "unnecessary_widening_rate": 0.1,
        **changes,
    }


def _report(report_id: str, version: str, *, latest_eligible: bool = True) -> dict:
    return {
        "report_id": report_id,
        "product_version": version,
        "benchmark_profile": "proof",
        "comparison_contract": "full_product_assistance_vs_raw_agent",
        "git_commit": "a" * 40,
        "source_posture": "source-local",
        "selection_fingerprint": "selection-fingerprint",
        "corpus_fingerprint": "corpus-fingerprint",
        "generated_utc": "2026-10-15T05:00:41Z",
        "latest_eligible": latest_eligible,
        "selection": {"full_corpus_selected": True},
        "cache_profiles": ["warm", "cold"],
        "published_cache_profiles": ["warm", "cold"],
        "published_view_strategy": "conservative_multi_profile",
        "acceptance": {"status": "provisional_pass", "hard_quality_gate_cleared": True},
        "scenario_count": 1,
        "mode_summaries": {"odylith_on": _quality(), "raw_agent_baseline": _quality()},
        "published_mode_summaries": {"odylith_on": _quality(), "raw_agent_baseline": _quality()},
        "published_scenarios": [{"results": [{"mode": "odylith_on"}, {"mode": "raw_agent_baseline"}]}],
        "published_comparison": {
            "candidate_mode": "odylith_on",
            "baseline_mode": "odylith_off",
            **{field: 0.0 for field in benchmark_compare._ABSOLUTE_QUALITY_FIELDS},
        },
    }


def _summary_fields(report_id: str, version: str, *, quality: dict | None = None) -> dict:
    report = _report(report_id, version)
    if quality is not None:
        report["published_mode_summaries"]["odylith_on"] = quality
    return benchmark_compare._comparison_summary(report)


def _compare_reports(monkeypatch, tmp_path: Path, candidate: dict, baseline: dict):
    candidate["repo_root"] = str(tmp_path)
    baseline["repo_root"] = str(tmp_path)
    monkeypatch.setattr(benchmark_compare, "product_source_version", lambda **kwargs: candidate["product_version"])
    monkeypatch.setattr(benchmark_compare.runner, "load_latest_benchmark_report", lambda **kwargs: candidate)
    monkeypatch.setattr(tree_identity_runtime, "benchmark_report_matches_current_tree", lambda **kwargs: True)
    monkeypatch.setattr(benchmark_compare, "_history_reports", lambda **kwargs: [baseline])
    monkeypatch.setattr(benchmark_compare, "_latest_published_release_version", lambda **kwargs: baseline["product_version"])
    return benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)


def _write_override(tmp_path: Path, version: str = "0.1.9") -> None:
    path = tmp_path / "odylith" / "runtime" / "source" / "release-maintainer-overrides.v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "{\n"
            '  "contract": "odylith_release_maintainer_overrides.v1",\n'
            '  "benchmark_proof_overrides": [\n'
            "    {\n"
            f'      "version": "{version}",\n'
            '      "mode": "skip_proof_and_compare",\n'
            '      "reason": "Maintainer special request.",\n'
            '      "owner": "freedom-research",\n'
            '      "updated_utc": "2026-04-07T22:05:00Z"\n'
            "    }\n"
            "  ]\n"
            "}\n"
        ),
        encoding="utf-8",
    )


def test_compare_latest_to_baseline_returns_unavailable_without_latest_report(tmp_path: Path) -> None:
    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.baseline_source == "missing-latest"


def test_compare_latest_to_baseline_warns_without_latest_report_when_override_is_active(monkeypatch, tmp_path: Path) -> None:
    _write_override(tmp_path)
    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.9",
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "warn"
    assert result.blocking is False
    assert result.baseline_source == "missing-latest"
    assert any("Maintainer benchmark override active for v0.1.9" in item for item in result.notes)


def test_compare_latest_to_baseline_warns_when_no_release_has_shipped(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: candidate_report,
    )
    candidate_report = (
        {
            **_summary_fields("candidate-1", "0.1.6"),
            "report_id": "candidate-1",
            "product_version": "0.1.6",
            "status": "provisional_pass",
            "current_tree_identity_match": True,
            "absolute_odylith_on_quality": _quality(),
        },
        "latest-runtime-report",
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_baseline_report",
        lambda **kwargs: (None, "missing-last-shipped"),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_latest_published_release_version",
        lambda **kwargs: "",
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "warn"
    assert result.blocking is False
    assert result.baseline_source == "first-release-no-last-shipped"
    assert any("first-release warning" in item for item in result.notes)


def test_resolve_baseline_report_uses_latest_published_release_not_reserved_tag(monkeypatch, tmp_path: Path) -> None:
    candidate_report = _report("candidate-1", "0.1.5")
    baseline_report = _report("baseline-1", "0.1.5")

    monkeypatch.setattr(
        benchmark_compare,
        "_history_reports",
        lambda **kwargs: [candidate_report, baseline_report],
    )
    monkeypatch.setattr(
        benchmark_compare,
        "fetch_release",
        lambda **kwargs: ReleaseInfo(version="0.1.5", tag="v0.1.5", assets={}),
    )

    report, source = benchmark_compare._resolve_baseline_report(
        repo_root=tmp_path,
        baseline="last-shipped",
        candidate_report=candidate_report,
    )

    assert report["report_id"] == "baseline-1"
    assert report["product_version"] == "0.1.5"
    assert source == "last-shipped"


def test_resolve_candidate_summary_falls_back_to_tracked_summary(monkeypatch, tmp_path: Path) -> None:
    tracked_summary = {
        "report_id": "tracked-1",
        "product_version": "0.1.5",
        "status": "provisional_pass",
    }

    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        benchmark_compare,
        "load_tracked_latest_summary",
        lambda **kwargs: tracked_summary,
    )

    summary, source = benchmark_compare._resolve_candidate_summary(repo_root=tmp_path)

    assert summary["report_id"] == "tracked-1"
    assert summary["tracked_summary_only"] is True
    assert summary["tracked_summary_backing_report_present"] is False
    assert summary["tracked_summary_backing_report_missing"] is True
    assert summary["current_tree_identity_match"] is False
    assert source == "tracked-latest-summary"


def test_resolve_candidate_summary_marks_stale_runtime_report_without_tracked_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    candidate_report = _report("candidate-1", "0.1.6")

    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: candidate_report,
    )
    monkeypatch.setattr(tree_identity_runtime, "benchmark_report_matches_current_tree", lambda **kwargs: False)
    monkeypatch.setattr(
        benchmark_compare.runner,
        "compact_report_summary",
        lambda report: {
            "report_id": str(report["report_id"]),
            "product_version": str(report["product_version"]),
            "status": "hold",
        },
    )
    monkeypatch.setattr(
        benchmark_compare,
        "load_tracked_latest_summary",
        lambda **kwargs: {"report_id": "tracked-1", "status": "provisional_pass"},
    )

    summary, source = benchmark_compare._resolve_candidate_summary(repo_root=tmp_path)

    assert summary["report_id"] == "candidate-1"
    assert summary["stale_runtime_report"] is True
    assert summary["current_tree_identity_match"] is False
    assert source == "latest-runtime-report-stale"


def test_resolve_baseline_report_falls_back_to_tracked_release_baseline(monkeypatch, tmp_path: Path) -> None:
    candidate_report = {"report_id": "candidate-1", "product_version": "0.1.6"}
    tracked_baseline = {
        "report_id": "baseline-1",
        "product_version": "0.1.5",
        "status": "provisional_pass",
    }

    monkeypatch.setattr(
        benchmark_compare,
        "_history_reports",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        benchmark_compare,
        "fetch_release",
        lambda **kwargs: ReleaseInfo(version="0.1.5", tag="v0.1.5", assets={}),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "load_release_baseline_summary",
        lambda **kwargs: tracked_baseline,
    )

    report, source = benchmark_compare._resolve_baseline_report(
        repo_root=tmp_path,
        baseline="last-shipped",
        candidate_report=candidate_report,
    )

    assert report == {**tracked_baseline, "absolute_odylith_on_quality": {}}
    assert source == "last-shipped"


def test_compare_latest_to_baseline_flags_blocking_regressions(monkeypatch, tmp_path: Path) -> None:
    baseline_summary = {
        **_summary_fields("baseline-1", "0.1.5"),
        "report_id": "baseline-1",
        "product_version": "0.1.5",
        "status": "provisional_pass",
        "latency_delta_ms": 0.0,
        "prompt_token_delta": 0.0,
        "required_path_recall_delta": 0.0,
        "validation_success_delta": 0.0,
        "critical_required_path_recall_delta": 0.0,
        "critical_validation_success_delta": 0.0,
        "hallucinated_surface_rate_delta": 0.0,
        "unnecessary_widening_rate_delta": 0.0,
        "absolute_odylith_on_quality": _quality(),
    }

    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: (
            {
                **_summary_fields("candidate-1", "0.1.6", quality=_quality(
                    required_path_recall_rate=0.87,
                    validation_success_rate=0.89,
                    critical_required_path_recall_rate=0.93,
                    critical_validation_success_rate=0.93,
                    hallucinated_surface_rate=0.13,
                    unnecessary_widening_rate=0.13,
                )),
                "report_id": "candidate-1",
                "product_version": "0.1.6",
                "status": "provisional_pass",
                "current_tree_identity_match": True,
                "latency_delta_ms": 24.0,
                "prompt_token_delta": 55.0,
                "required_path_recall_delta": -0.08,
                "validation_success_delta": -0.06,
                "critical_required_path_recall_delta": -0.02,
                "critical_validation_success_delta": -0.02,
                "hallucinated_surface_rate_delta": 0.03,
                "unnecessary_widening_rate_delta": 0.03,
            },
            "latest-runtime-report",
        ),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_baseline_report",
        lambda **kwargs: (baseline_summary, "last-shipped"),
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "fail"
    assert result.blocking is True
    assert any("prompt cost regressed" in item for item in result.notes)
    assert any("required-path recall regressed" in item for item in result.notes)


def test_compare_latest_to_baseline_passes_when_metrics_hold(monkeypatch, tmp_path: Path) -> None:
    baseline_summary = {
        **_summary_fields("baseline-1", "0.1.5"),
        "report_id": "baseline-1",
        "product_version": "0.1.5",
        "status": "provisional_pass",
        "latency_delta_ms": 0.0,
        "prompt_token_delta": 0.0,
        "required_path_recall_delta": 0.0,
        "validation_success_delta": 0.0,
        "critical_required_path_recall_delta": 0.0,
        "critical_validation_success_delta": 0.0,
        "hallucinated_surface_rate_delta": 0.0,
        "unnecessary_widening_rate_delta": 0.0,
        "absolute_odylith_on_quality": _quality(),
    }

    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: (
            {
                **_summary_fields("candidate-1", "0.1.6"),
                "report_id": "candidate-1",
                "product_version": "0.1.6",
                "status": "provisional_pass",
                "current_tree_identity_match": True,
                "latency_delta_ms": 1.0,
                "prompt_token_delta": 4.0,
                "required_path_recall_delta": 0.0,
                "validation_success_delta": 0.0,
                "critical_required_path_recall_delta": 0.0,
                "critical_validation_success_delta": 0.0,
                "hallucinated_surface_rate_delta": 0.0,
                "unnecessary_widening_rate_delta": 0.0,
                "absolute_odylith_on_quality": _quality(),
            },
            "latest-runtime-report",
        ),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_baseline_report",
        lambda **kwargs: (baseline_summary, "last-shipped"),
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "pass"
    assert result.blocking is False
    assert result.baseline_source == "last-shipped"


def test_compare_unchanged_on_quality_with_improved_raw_is_diagnostic_only(monkeypatch, tmp_path: Path) -> None:
    candidate = _report("candidate", "0.1.6")
    baseline = _report("baseline", "0.1.5")
    for delta, field in benchmark_compare._ABSOLUTE_QUALITY_FIELDS.items():
        on = candidate["published_mode_summaries"]["odylith_on"][field]
        direction = 1 if field in ("hallucinated_surface_rate", "unnecessary_widening_rate") else -1
        baseline["published_mode_summaries"]["raw_agent_baseline"][field] = on + direction * 0.2
        candidate["published_mode_summaries"]["raw_agent_baseline"][field] = on + direction * 0.1
        baseline["published_comparison"][delta] = -direction * 0.2
        candidate["published_comparison"][delta] = -direction * 0.1

    result = _compare_reports(monkeypatch, tmp_path, candidate, baseline)

    assert result.status == "pass"
    assert result.blocking is False
    assert all(result.deltas[field] == 0.0 for field in benchmark_compare._ABSOLUTE_QUALITY_FIELDS)
    diagnostics = result.summary["relative_advantage_diagnostics"]
    assert diagnostics["candidate"]["critical_required_path_recall_delta"] == 0.1
    assert diagnostics["baseline"]["critical_required_path_recall_delta"] == 0.2
    assert diagnostics["change"]["critical_required_path_recall_delta"] == -0.1
    assert "diagnostic only" in diagnostics["basis"]
    text = benchmark_compare.render_compare_text(result)
    assert "quality_comparison_basis: conservative absolute Odylith On" in text
    assert "diagnostic_on_minus_raw_advantage_change.critical_required_path_recall_delta: -0.100" in text


def test_compare_blocks_real_on_decline_despite_worse_raw(monkeypatch, tmp_path: Path) -> None:
    candidate = _report("candidate", "0.1.6")
    baseline = _report("baseline", "0.1.5")
    field = "critical_required_path_recall_rate"
    candidate["published_mode_summaries"]["odylith_on"][field] = 0.93
    candidate["published_mode_summaries"]["raw_agent_baseline"][field] = 0.63
    baseline["published_mode_summaries"]["raw_agent_baseline"][field] = 0.75
    candidate["published_comparison"]["critical_required_path_recall_delta"] = 0.3
    baseline["published_comparison"]["critical_required_path_recall_delta"] = 0.2

    result = _compare_reports(monkeypatch, tmp_path, candidate, baseline)

    assert result.status == "fail"
    assert result.blocking is True
    assert result.deltas["critical_required_path_recall_delta"] == -0.02
    assert result.summary["relative_advantage_diagnostics"]["change"]["critical_required_path_recall_delta"] == 0.1


def test_compare_preserves_completed_hold_baseline_warning(monkeypatch, tmp_path: Path) -> None:
    baseline = _report("baseline", "0.1.5")
    baseline["acceptance"] = {"status": "hold", "hard_quality_gate_cleared": False}

    result = _compare_reports(monkeypatch, tmp_path, _report("candidate", "0.1.6"), baseline)

    assert result.status == "warn"
    assert result.blocking is False
    assert "baseline report status is `hold`" in result.notes


def test_comparison_summary_preserves_measured_zero_quality() -> None:
    report = _report("measured-zero", "0.1.6")
    quality = {field: 0.0 for field in benchmark_compare._ABSOLUTE_QUALITY_FIELDS.values()}
    report["published_mode_summaries"]["odylith_on"] = quality

    summary = benchmark_compare._comparison_summary(report)

    assert summary["absolute_odylith_on_quality"] == quality
    bound = summary["release_quality_evidence"]["absolute_odylith_on_quality"]
    assert bound == quality
    assert bound is not summary["absolute_odylith_on_quality"]
    stored = json.loads(json.dumps(summary))
    assert benchmark_metric_helpers.release_quality_measurements(stored, cache_profiles=("warm", "cold")) == quality


def test_compare_still_blocks_unchanged_on_below_contemporary_raw(monkeypatch, tmp_path: Path) -> None:
    candidate = _report("candidate", "0.1.6")
    baseline = _report("baseline", "0.1.5")
    candidate["published_mode_summaries"]["raw_agent_baseline"]["critical_required_path_recall_rate"] = 0.98
    candidate["published_comparison"]["critical_required_path_recall_delta"] = -0.03
    candidate["acceptance"] = {
        "status": "hold",
        "hard_quality_gate_cleared": False,
        "hard_gate_failures": ["critical_required_path_recall_not_worse"],
    }

    result = _compare_reports(monkeypatch, tmp_path, candidate, baseline)

    assert result.status == "fail"
    assert result.blocking is True
    assert result.deltas["critical_required_path_recall_delta"] == 0.0
    assert any("latest report status is `hold`" in note for note in result.notes)


@pytest.mark.parametrize("side", ["candidate", "baseline"])
@pytest.mark.parametrize("field", benchmark_compare._ABSOLUTE_QUALITY_FIELDS.values())
def test_compare_missing_absolute_quality_fails_closed(monkeypatch, tmp_path: Path, side: str, field: str) -> None:
    candidate = _report("candidate", "0.1.6")
    baseline = _report("baseline", "0.1.5")
    report = candidate if side == "candidate" else baseline
    del report["published_mode_summaries"]["odylith_on"][field]

    result = _compare_reports(monkeypatch, tmp_path, candidate, baseline)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.deltas == {}
    assert f"{side}.{field}" in result.notes
    assert "required_path_recall_delta: unavailable" in benchmark_compare.render_compare_text(result)
    story = benchmark_compare.build_benchmark_story(repo_root=tmp_path)
    assert all(metric["direction"] == "unavailable" and metric["value"] == "unavailable" for metric in story["metrics"])


@pytest.mark.parametrize("value", [None, "0.95", True, float("nan"), float("inf"), -0.1, 1.1, 10**400])
def test_compare_invalid_absolute_quality_fails_closed(monkeypatch, tmp_path: Path, value) -> None:
    candidate = _report("candidate", "0.1.6")
    candidate["published_mode_summaries"]["odylith_on"]["required_path_recall_rate"] = value

    result = _compare_reports(monkeypatch, tmp_path, candidate, _report("baseline", "0.1.5"))

    assert result.status == "unavailable"
    assert result.blocking is True


@pytest.mark.parametrize("field,value", [
    ("published_view_strategy", "primary_profile"),
    ("published_cache_profiles", ["warm"]),
    ("published_mode_summaries", {}),
])
def test_compare_does_not_use_primary_profile_as_conservative_quality(monkeypatch, tmp_path: Path, field, value) -> None:
    candidate = _report("candidate", "0.1.6")
    candidate[field] = value

    result = _compare_reports(monkeypatch, tmp_path, candidate, _report("baseline", "0.1.5"))

    assert result.status == "unavailable"
    assert result.blocking is True


def test_compare_tracked_baseline_without_absolute_backing_fails_closed(monkeypatch, tmp_path: Path) -> None:
    candidate = _report("candidate", "0.1.6")
    baseline = _report("baseline", "0.1.5")
    _compare_reports(monkeypatch, tmp_path, candidate, baseline)
    monkeypatch.setattr(benchmark_compare, "_history_reports", lambda **kwargs: [])
    monkeypatch.setattr(benchmark_compare, "load_release_baseline_summary", lambda **kwargs: {
        "report_id": "legacy", "product_version": "0.1.5", "status": "provisional_pass",
        "critical_required_path_recall_delta": 0.2,
    })

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.baseline_report_id == "legacy"


def test_first_release_warning_cannot_authorize_missing_candidate_measurements(monkeypatch, tmp_path: Path) -> None:
    candidate = _report("candidate", "0.1.6")
    candidate["published_mode_summaries"] = {}
    _compare_reports(monkeypatch, tmp_path, candidate, _report("baseline", "0.1.5"))
    monkeypatch.setattr(benchmark_compare, "_latest_published_release_version", lambda **kwargs: "")

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert "candidate.required_path_recall_rate" in result.notes


@pytest.mark.parametrize("field,direction,warn,fail", [
    ("required_path_recall_rate", -1, 0.02, 0.05),
    ("validation_success_rate", -1, 0.02, 0.05),
    ("critical_required_path_recall_rate", -1, 0.005, 0.01),
    ("critical_validation_success_rate", -1, 0.005, 0.01),
    ("hallucinated_surface_rate", 1, 0.02, 0.05),
    ("unnecessary_widening_rate", 1, 0.01, 0.02),
])
@pytest.mark.parametrize("boundary,extra,expected", [
    ("warn", 0.0, "pass"), ("warn", 0.001, "warn"),
    ("fail", 0.0, "warn"), ("fail", 0.001, "fail"),
])
def test_compare_preserves_quality_threshold_boundaries(
    monkeypatch, tmp_path: Path, field, direction, warn, fail, boundary, extra, expected,
) -> None:
    candidate = _report("candidate", "0.1.6")
    baseline = _report("baseline", "0.1.5")
    baseline["published_mode_summaries"]["odylith_on"][field] = 0.5
    candidate["published_mode_summaries"]["odylith_on"][field] = 0.5 + direction * ((warn if boundary == "warn" else fail) + extra)

    result = _compare_reports(monkeypatch, tmp_path, candidate, baseline)

    assert result.status == expected
    assert result.blocking is (expected == "fail")


@pytest.mark.parametrize("field,value", [
    ("acceptance", {"status": "failed"}),
    ("acceptance", {"status": "running"}),
    ("acceptance", {"status": ["hold"]}),
    ("acceptance", {"status": "hold", "checks": {"benchmark_run_completed": False}}),
    ("acceptance", {"status": "hold", "checks": {"benchmark_run_completed": 0}}),
    ("status", "running"),
    ("status", ["hold"]),
    ("mode_summaries", {}),
    ("published_mode_summaries", []),
    ("published_scenarios", []),
    ("published_scenarios", [{"results": []}]),
    ("scenario_count", "1"),
    ("scenario_count", 2),
])
def test_incomplete_or_malformed_reports_are_not_release_baselines(field, value) -> None:
    report = _report("incomplete", "0.1.5")
    report[field] = value

    assert benchmark_compare._eligible_release_report(report) is False


def test_tied_history_selects_completed_hold_instead_of_interrupted_receipt(monkeypatch, tmp_path: Path) -> None:
    completed = _report("a9-completed", "0.1.5")
    completed["generated_utc"] = "2026-10-15T05:00:41Z"
    completed["acceptance"] = {"status": "hold", "hard_quality_gate_cleared": False}
    interrupted = copy.deepcopy(completed)
    interrupted.update(report_id="4b-interrupted", mode_summaries={}, published_mode_summaries={}, published_scenarios=[])
    interrupted["acceptance"] = {"status": "failed", "checks": {"benchmark_run_completed": False}}
    for report in (interrupted, completed):
        (tmp_path / f"{report['report_id']}.json").write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(benchmark_compare.runner, "benchmark_root", lambda **kwargs: tmp_path)
    monkeypatch.setattr(benchmark_compare, "_latest_published_release_version", lambda **kwargs: "0.1.5")

    summary, source = benchmark_compare._resolve_baseline_report(
        repo_root=tmp_path, baseline="last-shipped", candidate_report={"report_id": "candidate"},
    )

    assert summary["report_id"] == "a9-completed"
    assert summary["status"] == "hold"
    assert source == "last-shipped"


def test_compare_latest_to_baseline_stays_blocking_when_release_exists_but_baseline_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: (
            {
                "report_id": "candidate-1",
                "product_version": "0.1.6",
                "status": "provisional_pass",
                "current_tree_identity_match": True,
            },
            "latest-runtime-report",
        ),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_baseline_report",
        lambda **kwargs: (None, "missing-last-shipped"),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_latest_published_release_version",
        lambda **kwargs: "0.1.5",
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.baseline_source == "missing-last-shipped"


def test_compare_latest_to_baseline_blocks_stale_candidate_version(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: (
            {
                "report_id": "candidate-1",
                "product_version": "0.1.7",
                "status": "provisional_pass",
                "current_tree_identity_match": True,
            },
            "latest-runtime-report",
        ),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.8",
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.candidate_product_version == "0.1.7"
    assert result.baseline_source == "latest-runtime-report"
    assert any("does not match current source version `0.1.8`" in item for item in result.notes)


def test_compare_latest_to_baseline_blocks_tracked_summary_candidate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.8",
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: (
            {
                "report_id": "tracked-1",
                "product_version": "0.1.8",
                "status": "provisional_pass",
                "current_tree_identity_match": False,
                "tracked_summary_only": True,
                "tracked_summary_backing_report_missing": True,
            },
            "tracked-latest-summary",
        ),
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.baseline_source == "tracked-latest-summary"
    assert any("No current-tree authoritative proof candidate is available" in item for item in result.notes)
    assert any("missing runtime report artifact" in item for item in result.notes)


def test_compare_latest_to_baseline_blocks_stale_runtime_candidate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.8",
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: (
            {
                "report_id": "candidate-1",
                "product_version": "0.1.8",
                "status": "hold",
                "current_tree_identity_match": False,
                "stale_runtime_report": True,
            },
            "latest-runtime-report-stale",
        ),
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.baseline_source == "latest-runtime-report-stale"
    assert any("current-tree authoritative proof candidate" in item for item in result.notes)


def test_compare_latest_to_baseline_downgrades_stale_candidate_version_under_override(monkeypatch, tmp_path: Path) -> None:
    _write_override(tmp_path)
    monkeypatch.setattr(
        benchmark_compare,
        "_resolve_candidate_summary",
        lambda **kwargs: (
            {
                "report_id": "candidate-1",
                "product_version": "0.1.8",
                "status": "provisional_pass",
                "current_tree_identity_match": True,
            },
            "latest-runtime-report",
        ),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.9",
    )

    result = benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)

    assert result.status == "warn"
    assert result.blocking is False
    assert any("Maintainer benchmark override active for v0.1.9" in item for item in result.notes)


def test_build_benchmark_story_summarizes_compare_and_history(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        benchmark_compare,
        "compare_latest_to_baseline",
        lambda **kwargs: benchmark_compare.BenchmarkComparison(
            status="warn",
            candidate_report_id="candidate-1",
            candidate_product_version="0.1.6",
            baseline_report_id="baseline-1",
            baseline_product_version="0.1.5",
            baseline_source="last-shipped",
            summary={
                "candidate": {"product_version": "0.1.6"},
                "baseline": {"product_version": "0.1.5"},
            },
            deltas={
                "prompt_token_delta": 22.0,
                "latency_delta_ms": 5.0,
                "required_path_recall_delta": 0.01,
                "validation_success_delta": -0.01,
            },
            notes=("Benchmark compare raised release warnings.",),
            blocking=False,
        ),
    )
    monkeypatch.setattr(
        benchmark_compare,
        "_history_reports",
        lambda **kwargs: [
            {"report_id": "candidate-1", "product_version": "0.1.6", "generated_utc": "2026-03-31T05:00:00Z"},
            {"report_id": "baseline-1", "product_version": "0.1.5", "generated_utc": "2026-03-30T05:00:00Z"},
        ],
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "compact_report_summary",
        lambda report: dict(report),
    )

    story = benchmark_compare.build_benchmark_story(repo_root=tmp_path)

    assert story["show"] is True
    assert story["status"] == "warn"
    assert story["summary"] == "Benchmark compare raised release warnings."
    assert story["metrics"][0]["label"] == "Prompt tokens"
    assert story["metrics"][0]["direction"] == "worse"
    assert story["history"][0]["badge"] == "Current"
    assert story["history"][1]["badge"] == "Baseline"
