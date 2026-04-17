from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import value_engine


def value_engine_benchmark_report(
    *,
    corpus: Mapping[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return advisory mechanism proof for visible intervention selection.

    This is not the public live `odylith_on` versus `odylith_off` proof. It is
    the fast deterministic utility report that checks duplicate suppression,
    must-surface recall, visibility-failure recovery, no-output behavior, and
    selector latency. The corpus quality state decides whether calibration
    claims are allowed; the v0.1.11 seed corpus is intentionally bootstrap.
    """

    active_corpus = (
        dict(corpus)
        if isinstance(corpus, Mapping)
        else value_engine.load_adjudication_corpus(repo_root=repo_root)
    )
    return value_engine.advisory_report(active_corpus)


def render_value_engine_benchmark_report(report: Mapping[str, Any]) -> str:
    payload = dict(report)
    metrics = dict(payload.get("metric_summary", {}))
    quality = dict(metrics.get("corpus_quality", {}))
    claims = dict(payload.get("proof_claims", {}))
    return "\n".join(
        [
            "Intervention Value Engine: advisory mechanism proof",
            f"- runtime posture: {payload.get('runtime_posture', value_engine.RUNTIME_POSTURE)}",
            f"- precision: {metrics.get('precision', 0.0)}",
            f"- must-surface recall: {metrics.get('recall', 0.0)}",
            f"- must-suppress accuracy: {metrics.get('must_suppress_accuracy', 0.0)}",
            f"- duplicate visible block rate: {metrics.get('duplicate_visible_block_rate', 1.0)}",
            f"- visibility failure recall: {metrics.get('visibility_failure_recall', 0.0)}",
            f"- selector p95 latency ms: {metrics.get('latency_p95_ms', 0.0)}",
            f"- calibration-counted cases: {metrics.get('calibration_case_count', 0)}",
            f"- synthetic gate cases: {metrics.get('synthetic_case_count', 0)}",
            f"- corpus quality state: {quality.get('quality_state', claims.get('corpus_quality_state', 'bootstrap'))}",
            f"- calibration publishable: {quality.get('publishable', claims.get('calibration_publishable', False))}",
            "- full proof remains odylith_on versus odylith_off live benchmark outcome.",
        ]
    )
