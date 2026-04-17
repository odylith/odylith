from __future__ import annotations

from odylith.runtime.evaluation import odylith_intervention_value_engine_benchmark as benchmark


def test_value_engine_benchmark_report_surfaces_material_quality_metrics() -> None:
    report = benchmark.value_engine_benchmark_report()

    assert report["family"] == "intervention_value_engine"
    assert report["runtime_posture"] == "deterministic_utility_v1"
    assert report["advisory_to_live_proof"] is True
    claims = report["proof_claims"]
    assert claims["duplicate_visible_block_rate"] == 0.0
    assert claims["visible_block_precision"] >= 0.95
    assert claims["must_surface_recall"] >= 0.85
    assert claims["must_suppress_accuracy"] == 1.0
    assert claims["visibility_failure_recall"] == 1.0
    assert claims["selector_latency_p95_ms"] <= 15.0
    assert claims["corpus_quality_state"] == "bootstrap"
    assert claims["calibration_publishable"] is False


def test_value_engine_benchmark_report_renders_as_advisory_not_live_proof() -> None:
    rendered = benchmark.render_value_engine_benchmark_report(
        benchmark.value_engine_benchmark_report()
    )

    assert "Intervention Value Engine" in rendered
    assert "must-suppress accuracy: 1.0" in rendered
    assert "duplicate visible block rate: 0.0" in rendered
    assert "calibration-counted cases: 4" in rendered
    assert "corpus quality state: bootstrap" in rendered
    assert "calibration publishable: False" in rendered
    assert "odylith_on versus odylith_off live benchmark" in rendered
