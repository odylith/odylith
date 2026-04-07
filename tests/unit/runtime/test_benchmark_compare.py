from __future__ import annotations

from pathlib import Path

from odylith.install.release_assets import ReleaseInfo
from odylith.runtime.evaluation import benchmark_compare


def _report(report_id: str, version: str, *, latest_eligible: bool = True) -> dict[str, object]:
    return {
        "report_id": report_id,
        "product_version": version,
        "latest_eligible": latest_eligible,
        "selection": {"full_corpus_selected": True},
        "cache_profiles": ["warm", "cold"],
    }


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
    candidate_report = _report("candidate-1", "0.1.6")

    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: candidate_report,
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

    assert summary == tracked_summary
    assert source == "tracked-latest-summary"


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

    assert report == tracked_baseline
    assert source == "last-shipped"


def test_compare_latest_to_baseline_flags_blocking_regressions(monkeypatch, tmp_path: Path) -> None:
    candidate_report = _report("candidate-1", "0.1.6")
    baseline_summary = {
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
    }

    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: candidate_report,
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "compact_report_summary",
        lambda report: {
            "report_id": str(report["report_id"]),
            "status": "provisional_pass",
            "latency_delta_ms": 24.0 if report["report_id"] == "candidate-1" else 0.0,
            "prompt_token_delta": 55.0 if report["report_id"] == "candidate-1" else 0.0,
            "required_path_recall_delta": -0.08 if report["report_id"] == "candidate-1" else 0.0,
            "validation_success_delta": -0.06 if report["report_id"] == "candidate-1" else 0.0,
            "critical_required_path_recall_delta": -0.02 if report["report_id"] == "candidate-1" else 0.0,
            "critical_validation_success_delta": -0.02 if report["report_id"] == "candidate-1" else 0.0,
            "hallucinated_surface_rate_delta": 0.03 if report["report_id"] == "candidate-1" else 0.0,
            "unnecessary_widening_rate_delta": 0.03 if report["report_id"] == "candidate-1" else 0.0,
        },
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
    candidate_report = _report("candidate-1", "0.1.6")
    baseline_summary = {
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
    }

    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: candidate_report,
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "compact_report_summary",
        lambda report: {
            "report_id": str(report["report_id"]),
            "status": "provisional_pass",
            "latency_delta_ms": 1.0 if report["report_id"] == "candidate-1" else 0.0,
            "prompt_token_delta": 4.0 if report["report_id"] == "candidate-1" else 0.0,
            "required_path_recall_delta": 0.0,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "hallucinated_surface_rate_delta": 0.0,
            "unnecessary_widening_rate_delta": 0.0,
        },
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


def test_compare_latest_to_baseline_stays_blocking_when_release_exists_but_baseline_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    candidate_report = _report("candidate-1", "0.1.6")

    monkeypatch.setattr(
        benchmark_compare,
        "product_source_version",
        lambda **kwargs: "0.1.6",
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: candidate_report,
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
    candidate_report = _report("candidate-1", "0.1.7")

    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: candidate_report,
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "compact_report_summary",
        lambda report: {
            "report_id": str(report["report_id"]),
            "product_version": str(report["product_version"]),
            "status": "provisional_pass",
        },
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


def test_compare_latest_to_baseline_downgrades_stale_candidate_version_under_override(monkeypatch, tmp_path: Path) -> None:
    _write_override(tmp_path)
    candidate_report = _report("candidate-1", "0.1.8")

    monkeypatch.setattr(
        benchmark_compare.runner,
        "load_latest_benchmark_report",
        lambda **kwargs: candidate_report,
    )
    monkeypatch.setattr(
        benchmark_compare.runner,
        "compact_report_summary",
        lambda report: {
            "report_id": str(report["report_id"]),
            "product_version": str(report["product_version"]),
            "status": "provisional_pass",
        },
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
