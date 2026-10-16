from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.evaluation import benchmark_compare, benchmark_metric_helpers, benchmark_snapshot_fallbacks
from odylith.runtime.evaluation import odylith_benchmark_publication as publication
from odylith.runtime.evaluation import odylith_benchmark_tree_identity as tree_identity_runtime


def _report(
    *,
    profile: str,
    claim: str,
    status: str,
    report_id: str,
) -> dict[str, object]:
    summary = {
        "report_id": report_id,
        "benchmark_profile": profile,
        "comparison_contract": claim,
        "comparison_primary_claim": claim,
        "generated_utc": "2026-04-12T23:59:59Z",
        "status": status,
        "scenario_count": 65,
        "published_cache_profiles": ["warm", "cold"] if profile == "proof" else ["warm"],
        "full_pair_count": 130 if profile == "proof" else 65,
        "published_pair_count": 65,
        "published_pair_median_wall_clock_ms": 123394.768 if profile == "proof" else 92.583,
        "published_pair_p95_wall_clock_ms": 240390.883 if profile == "proof" else 330.622,
        "published_pair_total_wall_clock_ms": 8849533.342 if profile == "proof" else 8010.51,
        "fairness_contract_passed": True,
        "fairness_findings": [],
        "corpus_seriousness_floor_passed": True,
        "corpus_full_coverage_rate": 1.0,
        "corpus_implementation_scenario_count": 60,
        "corpus_write_plus_validator_scenario_count": 43,
        "corpus_correctness_critical_scenario_count": 18,
        "corpus_mechanism_heavy_implementation_ratio": 0.3,
        "runtime_memory_storage": "lance_local_columnar",
        "runtime_memory_sparse_recall": "tantivy_sparse_recall",
        "runtime_remote_retrieval_status": "disabled",
        "runtime_memory_backed_retrieval_ready": profile != "proof",
        "odylith_auto_grounded_rate": 1.0 if profile == "proof" else 0.667,
        "odylith_grounded_delegate_rate": 0.0 if profile == "proof" else 0.25,
        "odylith_requires_widening_rate": 0.077 if profile == "proof" else 0.0,
        "odylith_workspace_daemon_reuse_rate": 0.0 if profile == "proof" else 0.667,
        "robustness_warm_cold_consistency_cleared": profile == "proof",
        "required_path_recall_delta": 0.25,
        "required_path_precision_delta": 0.11 if profile == "proof" else -0.02,
        "hallucinated_surface_rate_delta": -0.09 if profile == "proof" else 0.05,
        "validation_success_delta": 0.33,
        "critical_required_path_recall_delta": 0.22,
        "critical_validation_success_delta": 0.18,
        "expectation_success_delta": 0.41,
        "write_surface_precision_delta": 0.12,
        "unnecessary_widening_rate_delta": -0.07,
        "prompt_token_delta": -42000 if profile == "proof" else 53,
        "total_payload_token_delta": -43000 if profile == "proof" else 220,
        "latency_delta_ms": -12500 if profile == "proof" else 21.271,
        "weak_families": ["architecture", "browser_surface_reliability"],
        "hard_gate_failure_labels": ["selected cache profiles do not all clear the hard quality gate"]
        if status == "hold"
        else [],
    }
    table = {
        "display_mode_order": ["odylith_on", "odylith_off"],
        "rows": [
            {
                "label": "Lane role",
                "values": {
                    "odylith_on": "primary candidate",
                    "odylith_off": "odylith_off / raw host CLI honest baseline",
                },
                "delta": "Odylith policy vs raw host",
                "why_it_matters": "Keeps the benchmark honest.",
            },
            {
                "label": "Scenario count",
                "values": {"odylith_on": "65", "odylith_off": "65"},
                "delta": "+0",
                "why_it_matters": "Both lanes run the same corpus.",
            },
        ],
    }
    return {
        "published_summary": summary,
        "published_mode_table": table,
    }


def test_render_live_snapshot_markdown_uses_full_product_contract() -> None:
    report = _report(
        profile="proof",
        claim="full_product_assistance_vs_raw_agent",
        status="provisional_pass",
        report_id="proof-123",
    )

    rendered = publication.render_live_snapshot_markdown(report)

    assert "Current Live Benchmark report: `proof-123`" in rendered
    assert "The latest live benchmark ran `65` seeded scenarios across matched cache profile(s) `warm` and `cold`" in rendered
    assert "`full_product_assistance_vs_raw_agent`" in rendered
    assert "That produced `130` full matched pairs." in rendered
    assert "Current proof posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`." in rendered
    assert "Compared with `odylith_off`, Odylith moved:" in rendered
    assert "Current attention families on the published view:" in rendered
    assert "Operating-posture diagnostics: auto-grounded `100.0%`" in rendered


def test_render_live_snapshot_markdown_flags_stale_current_tree_report() -> None:
    report = _report(
        profile="proof",
        claim="full_product_assistance_vs_raw_agent",
        status="hold",
        report_id="proof-stale",
    )
    report["published_summary"]["current_tree_identity_match"] = False

    rendered = publication.render_live_snapshot_markdown(report)

    assert "This report does not match the current repo tree and is not current-head proof." in rendered
    assert "The selected report is stale relative to the current repo tree." in rendered


def test_render_diagnostic_snapshot_markdown_uses_packet_prompt_contract() -> None:
    report = _report(
        profile="diagnostic",
        claim="internal_packet_prompt_diagnostic",
        status="provisional_pass",
        report_id="diag-123",
    )

    rendered = publication.render_diagnostic_snapshot_markdown(report)

    assert "Current Internal Diagnostic Benchmark report: `diag-123`" in rendered
    assert "packet and prompt construction only" in rendered
    assert "Across the `65` diagnostic pairs" in rendered
    assert "Compared with the `odylith_off` prompt bundle, Odylith moved:" in rendered
    assert "`odylith_off` is the raw prompt-bundle control for this mechanism-evidence view." in rendered


def test_render_benchmark_tables_markdown_uses_current_tables() -> None:
    live_report = _report(
        profile="proof",
        claim="full_product_assistance_vs_raw_agent",
        status="provisional_pass",
        report_id="proof-123",
    )
    diagnostic_report = _report(
        profile="diagnostic",
        claim="internal_packet_prompt_diagnostic",
        status="hold",
        report_id="diag-123",
    )

    rendered = publication.render_benchmark_tables_markdown(
        live_report=live_report,
        diagnostic_report=diagnostic_report,
    )

    assert "## Internal Diagnostic Signal Table" in rendered
    assert "## Live Signal Table" in rendered
    assert "| Lane role | primary candidate | odylith_off / raw host CLI honest baseline | Odylith policy vs raw host | Keeps the benchmark honest. |" in rendered
    assert "Current live-proof status: `provisional_pass`." in rendered
    assert "Current diagnostic status: `hold`." in rendered
    assert "release-warn" not in rendered


def test_write_publication_artifacts_is_content_addressed(tmp_path: Path) -> None:
    live_report = _report(
        profile="proof",
        claim="full_product_assistance_vs_raw_agent",
        status="provisional_pass",
        report_id="proof-123",
    )
    diagnostic_report = _report(
        profile="diagnostic",
        claim="internal_packet_prompt_diagnostic",
        status="hold",
        report_id="diag-123",
    )

    changed = publication.write_publication_artifacts(
        repo_root=tmp_path,
        live_report=live_report,
        diagnostic_report=diagnostic_report,
    )

    assert set(changed) == {
        "docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md",
        "docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md",
        "docs/benchmarks/BENCHMARK_TABLES.md",
        "docs/benchmarks/latest-summary.v1.json",
        "docs/benchmarks/proof/odylith-benchmark-quality-frontier.svg",
        "docs/benchmarks/proof/odylith-benchmark-frontier.svg",
        "docs/benchmarks/proof/odylith-benchmark-family-heatmap.svg",
        "docs/benchmarks/proof/odylith-benchmark-operating-posture.svg",
        "docs/benchmarks/diagnostic/odylith-benchmark-quality-frontier.svg",
        "docs/benchmarks/diagnostic/odylith-benchmark-frontier.svg",
        "docs/benchmarks/diagnostic/odylith-benchmark-family-heatmap.svg",
        "docs/benchmarks/diagnostic/odylith-benchmark-operating-posture.svg",
    }

    latest_summary_path = tmp_path / "docs/benchmarks/latest-summary.v1.json"
    latest_summary = json.loads(latest_summary_path.read_text(encoding="utf-8"))
    assert latest_summary["report_id"] == "proof-123"
    assert latest_summary["comparison_primary_claim"] == "full_product_assistance_vs_raw_agent"
    assert (tmp_path / "docs" / "benchmarks" / "proof" / "odylith-benchmark-frontier.svg").is_file()
    assert (tmp_path / "docs" / "benchmarks" / "diagnostic" / "odylith-benchmark-frontier.svg").is_file()

    second_changed = publication.write_publication_artifacts(
        repo_root=tmp_path,
        live_report=live_report,
        diagnostic_report=diagnostic_report,
    )
    assert second_changed == []


def test_publication_main_refuses_explicit_stale_report(monkeypatch, tmp_path: Path) -> None:
    live_report = _report(
        profile="proof",
        claim="full_product_assistance_vs_raw_agent",
        status="provisional_pass",
        report_id="proof-stale",
    )
    diagnostic_report = _report(
        profile="diagnostic",
        claim="internal_packet_prompt_diagnostic",
        status="provisional_pass",
        report_id="diag-current",
    )
    live_path = tmp_path / "live.json"
    diagnostic_path = tmp_path / "diagnostic.json"
    live_path.write_text(json.dumps(live_report), encoding="utf-8")
    diagnostic_path.write_text(json.dumps(diagnostic_report), encoding="utf-8")
    monkeypatch.setattr(tree_identity_runtime, "benchmark_report_matches_current_tree", lambda **kwargs: False)

    try:
        publication.main(
            [
                "--repo-root",
                str(tmp_path),
                "--live-report",
                str(live_path),
                "--diagnostic-report",
                str(diagnostic_path),
            ]
        )
    except ValueError as exc:
        assert "does not match the current repo tree identity" in str(exc)
    else:
        raise AssertionError("expected stale explicit benchmark report publication to fail")


def _full_proof_report(*, report_id="proof-baseline", version="0.1.5", status="provisional_pass") -> dict:
    report = _report(
        profile="proof", claim="full_product_assistance_vs_raw_agent", status=status, report_id=report_id,
    )
    quality = {
        "required_path_recall_rate": 0.992,
        "validation_success_rate": 0.98,
        "critical_required_path_recall_rate": 0.979,
        "critical_validation_success_rate": 0.96,
        "hallucinated_surface_rate": 0.0,
        "unnecessary_widening_rate": 0.02,
    }
    report.update(
        report_id=report_id,
        product_version=version,
        git_commit="a" * 40,
        source_posture="source-local",
        selection_fingerprint="selection-fingerprint",
        corpus_fingerprint="corpus-fingerprint",
        generated_utc="2026-10-15T05:00:41Z",
        benchmark_profile="proof",
        comparison_contract="full_product_assistance_vs_raw_agent",
        latest_eligible=True,
        selection={"full_corpus_selected": True},
        cache_profiles=["warm", "cold"],
        published_cache_profiles=["warm", "cold"],
        published_view_strategy="conservative_multi_profile",
        acceptance={"status": status, "hard_quality_gate_cleared": status == "provisional_pass"},
        scenario_count=65,
        mode_summaries={"odylith_on": dict(quality), "raw_agent_baseline": dict(quality)},
        published_mode_summaries={"odylith_on": dict(quality), "raw_agent_baseline": dict(quality)},
        published_scenarios=[{"results": [{"mode": "odylith_on"}, {"mode": "raw_agent_baseline"}]} for _ in range(65)],
    )
    return report


def _compare_to_stored_summary(monkeypatch, tmp_path: Path, summary: dict):
    path = tmp_path / "docs/benchmarks/release-baselines.v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"0.1.5": summary}), encoding="utf-8")
    candidate = _full_proof_report(report_id="candidate", version="0.1.6")
    candidate["repo_root"] = str(tmp_path)
    monkeypatch.setattr(benchmark_compare, "product_source_version", lambda **kwargs: "0.1.6")
    monkeypatch.setattr(benchmark_compare.runner, "load_latest_benchmark_report", lambda **kwargs: candidate)
    monkeypatch.setattr(tree_identity_runtime, "benchmark_report_matches_current_tree", lambda **kwargs: True)
    monkeypatch.setattr(benchmark_compare, "_history_reports", lambda **kwargs: [])
    monkeypatch.setattr(benchmark_compare, "_latest_published_release_version", lambda **kwargs: "0.1.5")
    return benchmark_compare.compare_latest_to_baseline(repo_root=tmp_path)


@pytest.mark.parametrize("status,expected", [("provisional_pass", "pass"), ("hold", "warn")])
def test_canonical_publication_survives_stored_release_baseline_comparison(monkeypatch, tmp_path: Path, status, expected) -> None:
    proof = _full_proof_report(status=status)
    diagnostic = _report(profile="diagnostic", claim="internal_packet_prompt_diagnostic", status="hold", report_id="diagnostic")
    publication.write_publication_artifacts(repo_root=tmp_path, live_report=proof, diagnostic_report=diagnostic)
    canonical = json.loads((tmp_path / "docs/benchmarks/latest-summary.v1.json").read_text(encoding="utf-8"))

    assert canonical["absolute_odylith_on_quality"] == proof["published_mode_summaries"]["odylith_on"]
    assert canonical["critical_required_path_recall_delta"] == 0.22
    assert canonical["release_quality_evidence"]["contract"] == "odylith_release_quality_summary.v1"
    assert canonical["release_quality_evidence"]["git_commit"] == proof["git_commit"]
    assert canonical["release_quality_evidence"]["absolute_odylith_on_quality"] == canonical["absolute_odylith_on_quality"]
    result = _compare_to_stored_summary(monkeypatch, tmp_path, canonical)

    assert benchmark_snapshot_fallbacks.load_release_baseline_summary(repo_root=tmp_path, version="0.1.5") == canonical
    assert result.status == expected
    assert result.blocking is False
    assert result.baseline_report_id == "proof-baseline"
    assert result.summary["baseline"]["absolute_odylith_on_quality"]["critical_required_path_recall_rate"] == 0.979
    assert all(result.deltas[field] == 0.0 for field in benchmark_metric_helpers.RELEASE_QUALITY_FIELDS)


@pytest.mark.parametrize("section,field,value", [
    (None, "release_quality_evidence", None),
    ("release_quality_evidence", "contract", "legacy"),
    (None, "report_id", "other-report"),
    (None, "product_version", "0.1.4"),
    (None, "git_commit", ""),
    (None, "source_posture", ""),
    (None, "selection_fingerprint", ""),
    (None, "corpus_fingerprint", ""),
    (None, "status", "failed"),
    (None, "benchmark_profile", "diagnostic"),
    (None, "scenario_count", 0),
    (None, "evaluated_mode_count", 0),
    (None, "published_cache_profiles", ["warm"]),
    (None, "published_view_strategy", "primary_profile"),
    ("release_quality_evidence", "full_corpus_selected", False),
    ("release_quality_evidence", "published_scenario_count", 64),
    ("release_quality_evidence", "absolute_odylith_on_quality", {}),
    ("absolute_odylith_on_quality", "critical_required_path_recall_rate", None),
    ("absolute_odylith_on_quality", "critical_required_path_recall_rate", float("nan")),
    ("absolute_odylith_on_quality", "critical_required_path_recall_rate", 1.1),
])
def test_stored_release_summary_with_invalid_authority_fails_closed(monkeypatch, tmp_path: Path, section, field, value) -> None:
    summary = publication._summary(_full_proof_report())
    target = summary if section is None else summary[section]
    target[field] = value

    result = _compare_to_stored_summary(monkeypatch, tmp_path, summary)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.deltas == {}


def test_legacy_publication_without_absolute_evidence_cannot_authorize_comparison(monkeypatch, tmp_path: Path) -> None:
    legacy = publication.odylith_benchmark_runner.compact_report_summary(_full_proof_report())

    result = _compare_to_stored_summary(monkeypatch, tmp_path, legacy)

    assert result.status == "unavailable"
    assert result.blocking is True


@pytest.mark.parametrize("field", benchmark_metric_helpers.RELEASE_QUALITY_FIELDS.values())
@pytest.mark.parametrize("side", ["summary", "evidence"])
def test_stored_release_quality_value_tampering_is_rejected(monkeypatch, tmp_path: Path, field, side) -> None:
    summary = publication._summary(_full_proof_report())
    bound = summary["release_quality_evidence"]["absolute_odylith_on_quality"]
    assert bound is not summary["absolute_odylith_on_quality"]
    target = summary["absolute_odylith_on_quality"] if side == "summary" else bound
    target[field] = 0.5

    result = _compare_to_stored_summary(monkeypatch, tmp_path, summary)

    assert result.status == "unavailable"
    assert result.blocking is True
    assert result.deltas == {}


@pytest.mark.parametrize("side", ["summary", "evidence", "both"])
@pytest.mark.parametrize("change", ["missing", "extra"])
def test_stored_release_quality_maps_require_exact_complete_fields(monkeypatch, tmp_path: Path, side, change) -> None:
    summary = publication._summary(_full_proof_report())
    top = summary["absolute_odylith_on_quality"]
    bound = summary["release_quality_evidence"]["absolute_odylith_on_quality"]
    targets = [top, bound] if side == "both" else [top if side == "summary" else bound]
    for target in targets:
        if change == "missing":
            del target["critical_required_path_recall_rate"]
        else:
            target["unknown_quality_rate"] = 0.5

    result = _compare_to_stored_summary(monkeypatch, tmp_path, summary)

    assert result.status == "unavailable"
    assert result.blocking is True


@pytest.mark.parametrize("side", ["summary", "evidence"])
@pytest.mark.parametrize("value", [0, False])
def test_stored_release_quality_requires_exact_numeric_types(monkeypatch, tmp_path: Path, side, value) -> None:
    summary = publication._summary(_full_proof_report())
    target = summary if side == "summary" else summary["release_quality_evidence"]
    target["absolute_odylith_on_quality"]["hallucinated_surface_rate"] = value

    result = _compare_to_stored_summary(monkeypatch, tmp_path, summary)

    assert result.status == "unavailable"
    assert result.blocking is True


def test_diagnostic_publication_keeps_actual_metrics_without_release_authority() -> None:
    diagnostic = _report(profile="diagnostic", claim="internal_packet_prompt_diagnostic", status="hold", report_id="diagnostic")

    summary = publication._summary(diagnostic)

    assert summary["status"] == "hold"
    assert summary["benchmark_profile"] == "diagnostic"
    assert summary["prompt_token_delta"] == 53
    assert summary["critical_required_path_recall_delta"] == 0.22
    assert summary["absolute_odylith_on_quality"] == {}
    assert summary["release_quality_evidence"] == {}
    assert benchmark_metric_helpers.release_quality_measurements(summary, cache_profiles=("warm", "cold")) == {}


@pytest.mark.parametrize("field,value", [
    ("report_id", ""), ("product_version", ""), ("git_commit", ""), ("source_posture", ""),
    ("selection_fingerprint", ""), ("corpus_fingerprint", ""), ("generated_utc", ""),
    ("benchmark_profile", "diagnostic"),
    ("comparison_contract", "internal_packet_prompt_diagnostic"),
    ("latest_eligible", False),
    ("selection", {"full_corpus_selected": False}),
    ("cache_profiles", ["warm"]),
    ("published_scenarios", []),
])
def test_canonical_release_evidence_requires_completed_full_proof_source_metadata(field, value) -> None:
    proof = _full_proof_report()
    proof[field] = value

    summary = publication._summary(proof)

    assert summary["release_quality_evidence"] == {}
    assert summary["absolute_odylith_on_quality"] == {}
    assert summary["status"] == "provisional_pass"
