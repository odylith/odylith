from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.evaluation import odylith_benchmark_publication as publication


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
        "fairness_contract_passed": True,
        "fairness_findings": [],
        "corpus_seriousness_floor_passed": True,
        "corpus_full_coverage_rate": 1.0,
        "corpus_implementation_scenario_count": 60,
        "corpus_write_plus_validator_scenario_count": 43,
        "corpus_correctness_critical_scenario_count": 18,
        "corpus_mechanism_heavy_implementation_ratio": 0.3,
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
                "delta": "full Odylith vs raw agent",
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

    assert "proof-123" in rendered
    assert "`full_product_assistance_vs_raw_agent`" in rendered
    assert "Fairness contract passed: `True`." in rendered
    assert "Compared with `odylith_off`, Odylith moved:" in rendered
    assert "Current attention families:" in rendered


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
    assert "| Lane role | primary candidate | odylith_off / raw host CLI honest baseline | full Odylith vs raw agent | Keeps the benchmark honest. |" in rendered
    assert "Current live-proof status: `provisional_pass`." in rendered
    assert "Current diagnostic status: `hold`." in rendered


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

    assert changed == [
        "docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md",
        "docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md",
        "docs/benchmarks/BENCHMARK_TABLES.md",
        "docs/benchmarks/latest-summary.v1.json",
    ]

    latest_summary_path = tmp_path / "docs/benchmarks/latest-summary.v1.json"
    latest_summary = json.loads(latest_summary_path.read_text(encoding="utf-8"))
    assert latest_summary["report_id"] == "proof-123"
    assert latest_summary["comparison_primary_claim"] == "full_product_assistance_vs_raw_agent"

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
    monkeypatch.setattr(
        publication.odylith_benchmark_runner,
        "benchmark_report_matches_current_tree",
        lambda **kwargs: False,
    )

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
