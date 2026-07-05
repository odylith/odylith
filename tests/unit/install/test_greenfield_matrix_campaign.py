from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_matrix_campaign")


def _types_module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_matrix_types")


def _result(
    *,
    name: str,
    issue: str,
    scores: dict[str, int],
    failure_detail: str = "",
    manifest_summary: dict[str, object] | None = None,
):
    types = _types_module()
    return types.GreenfieldMatrixResult(
        name=name,
        status="failed",
        create_seconds=12.3,
        counts=types.GreenfieldArtifactCounts(),
        quality=types.GreenfieldQualityVerdict(
            passed=False,
            issues=(issue,),
            lenses={
                "product_manager": False,
                "architect": False,
                "engineer": False,
                "domain_expert": False,
            },
            scores=scores,
            score=min(scores.values()) if scores else 0,
            score_explanation=("diagnostic failure",),
        ),
        failure_detail=failure_detail,
        post_confirm_manifest_summary=manifest_summary or {},
    )


def test_telemetry_writer_flushes_jsonl_events_incrementally(tmp_path: Path) -> None:
    module = _module()
    telemetry_path = tmp_path / "campaign" / "progress.jsonl"
    writer = module.MatrixTelemetryWriter(telemetry_path)

    writer.emit("run_started", {"phase": "failed-subset", "case_count": 2})
    writer.emit("case_started", {"index": 1, "total": 2, "case": {"name": "case one"}})

    rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in rows] == ["run_started", "case_started"]
    assert rows[0]["version"] == module.CAMPAIGN_TELEMETRY_VERSION
    assert rows[0]["phase"] == "failed-subset"
    assert rows[1]["case"]["name"] == "case one"


def test_campaign_progress_console_line_reports_per_case_status() -> None:
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    progress = importlib.import_module("greenfield_matrix_campaign_progress")

    line = progress.progress_console_line(
        {
            "event": "case_completed",
            "tier": "volume-discovery",
            "shard": "volume-discovery-001",
            "matrix_telemetry": {
                "index": 7,
                "total": 30,
                "failure_cluster": "manifest.generated-copy-quality.atlas",
                "result": {
                    "case": {
                        "id": "case-007",
                        "name": "gene regulation simulator",
                        "stressors": ["scientific-casing", "atlas-label-pressure"],
                    },
                    "status": "failed",
                    "quality_passed": False,
                    "score": 4,
                    "create_seconds": 32.456,
                    "first_issue": "Atlas diagram repeated visible copy near `result result`",
                },
            },
        }
    )

    assert line.startswith("[greenfield-matrix] case 7/30 failed volume-discovery/volume-discovery-001")
    assert "gene regulation simulator" in line
    assert "score=4/10" in line
    assert "32.456s" in line
    assert "cluster=manifest.generated-copy-quality.atlas" in line
    assert "result result" in line


def test_failure_cluster_prefers_structured_manifest_issue_ownership() -> None:
    module = _module()
    first = _result(
        name="alpha review board",
        issue="post-confirm quality manifest has 4 issue(s)",
        scores={"completion": 0, "copy_semantic_clarity": 0, "architect": 0},
        manifest_summary={
            "issue_signatures": [
                "semantic-alignment.semantic-model-compiler.atlas.semanticmodelir-first-path-contract",
                "generated-copy-quality.atlas-renderer.atlas.artifactplanir-atlas",
            ]
        },
    )
    second = _result(
        name="beta review board",
        issue="post-confirm quality manifest has 4 issue(s)",
        scores={"completion": 0, "copy_semantic_clarity": 0, "architect": 0},
        manifest_summary={
            "issue_signatures": [
                "semantic-alignment.semantic-model-compiler.atlas.semanticmodelir-first-path-contract"
            ]
        },
    )

    assert module.failure_cluster_key(first).startswith(
        "manifest.semantic-alignment.semantic-model-compiler.atlas"
    )
    assert module.failure_cluster_key(second) == module.failure_cluster_key(first)
    reason = module.stop_reason(
        (first, second),
        module.MatrixCampaignConfig(proof_tier="discovery", stop_after_cluster_failures=2),
    )

    assert reason.startswith("cluster-threshold:manifest.semantic-alignment")
    assert reason.endswith(":2")


def test_failure_cluster_uses_actual_blocker_before_score_bucket() -> None:
    module = _module()
    result = _result(
        name="quantum review board",
        issue="post-confirm create exited with code 2",
        scores={"completion": 0, "copy_semantic_clarity": 0, "architect": 0},
        failure_detail=json.dumps(
            {
                "error": (
                    "greenfield post-confirm final write quality failed with 2 issue(s):\n"
                    "- Atlas Mermaid `odylith/atlas/source/domain-specific-first-path.mmd` "
                    "leaked mixed finite/base action in visible label"
                ),
                "mode": "error",
            }
        ),
    )

    assert (
        module.failure_cluster_key(result)
        == "atlas.mermaid.leaked.mixed.finite.base.action.visible.label"
    )


def test_failure_cluster_preserves_multiline_blocker_bullets() -> None:
    module = _module()
    result = _result(
        name="plain text gate failure",
        issue=(
            "greenfield post-confirm final write quality failed with 2 issue(s):\n"
            "Remediation: rerun from the accepted intent after platform repair.\n"
            "- Registry component spec Results Review Workspace has modal/base-form grammar drift near `to flags`"
        ),
        scores={"completion": 0, "copy_semantic_clarity": 0},
    )

    assert (
        module.failure_cluster_key(result)
        == "registry.component.spec.results.review.workspace.has.modal.base.form"
    )


def test_campaign_summary_keeps_discovery_boundary_and_stressor_coverage() -> None:
    module = _module()
    cases = (
        SimpleNamespace(name="case one", slug="case-one", tags=("science",), stressors=("modal-expert-lens",)),
        SimpleNamespace(name="case two", slug="case-two", tags=("ops",), stressors=("latency-pressure",)),
    )
    config = module.MatrixCampaignConfig(
        phase="60-case-regression",
        proof_tier="discovery",
        telemetry_jsonl=Path("/tmp/progress.jsonl"),
        stop_after_failures=1,
        required_stressors=("modal-expert-lens", "latency-pressure", "atlas-label-pressure"),
    )

    summary = module.campaign_summary(cases=cases, results=(), config=config, stopped_reason="")

    assert summary["phase"] == "60-case-regression"
    assert summary["proof_tier"] == "discovery"
    assert summary["release_readiness_boundary"].startswith("discovery proof may skip browser")
    assert summary["stressor_coverage"]["missing_required"] == ["atlas-label-pressure"]
    assert summary["stressor_variance"]["status"] == "failed"
    assert summary["stressor_variance"]["score"] < 10


def test_case_completed_event_carries_stable_case_identity() -> None:
    module = _module()
    result = _result(
        name="renamed display label",
        issue="post-confirm create exited with code 2",
        scores={"completion": 0},
    )
    result = _types_module().GreenfieldMatrixResult(
        **{
            **result.to_dict(),
            "counts": _types_module().GreenfieldArtifactCounts(),
            "quality": result.quality,
            "evidence": {
                "case": {
                    "id": "case-017",
                    "name": "source case name",
                    "slug": "source-case-name",
                    "stressors": ["registry-contract-pressure", "atlas-label-pressure"],
                    "prompt_sha256": "a" * 64,
                    "confirmed_intent_sha256": "b" * 64,
                }
            },
        }
    )

    event = module.case_completed_event(result=result, index=1, total=1)
    cluster = module.failure_clusters((result,))[0]

    assert event["result"]["case"]["id"] == "case-017"
    assert event["result"]["case"]["prompt_sha256"] == "a" * 64
    assert event["result"]["stressors"] == ["registry-contract-pressure", "atlas-label-pressure"]
    assert cluster["case_ids"] == ["case-017"]
    assert cluster["case_fingerprints"] == ["a" * 64, "b" * 64]
    assert cluster["stressors"] == ["registry-contract-pressure", "atlas-label-pressure"]


def test_campaign_summary_reports_failures_by_stressor_class() -> None:
    module = _module()
    result = _result(
        name="contract pressure case",
        issue="Registry component spec has clipped noun pile",
        scores={"copy_semantic_clarity": 0},
    )
    types = _types_module()
    result = types.GreenfieldMatrixResult(
        **{
            **result.to_dict(),
            "counts": types.GreenfieldArtifactCounts(),
            "quality": result.quality,
            "evidence": {
                "case": {
                    "id": "case-021",
                    "name": "contract pressure case",
                    "slug": "contract-pressure-case",
                    "stressors": ["registry-contract-pressure", "noun-verb-homonym"],
                    "prompt_sha256": "c" * 64,
                }
            },
        }
    )
    cases = (
        SimpleNamespace(
            name="contract pressure case",
            slug="contract-pressure-case",
            stressors=("registry-contract-pressure", "noun-verb-homonym"),
        ),
    )

    summary = module.campaign_summary(
        cases=cases,
        results=(result,),
        config=module.MatrixCampaignConfig(proof_tier="discovery"),
        stopped_reason="failure-threshold:1",
    )

    outcomes = summary["stressor_outcomes"]
    assert outcomes["status"] == "failed"
    assert outcomes["failed_stressors"] == ["noun-verb-homonym", "registry-contract-pressure"]
    rows = {row["stressor"]: row for row in outcomes["by_stressor"]}
    assert rows["registry-contract-pressure"]["failed_case_count"] == 1
    assert rows["registry-contract-pressure"]["failure_clusters"]


def test_required_stressors_are_normalized_without_duplicate_case() -> None:
    module = _module()

    required = module.required_stressors_from_values(
        ("Modal Expert Lens", "modal_expert_lens", "Latency Pressure"),
        use_default=False,
    )

    assert required == ("modal-expert-lens", "latency-pressure")


def test_default_release_cases_cover_the_high_variance_taxonomy() -> None:
    module = _module()
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    cases_module = importlib.import_module("greenfield_post_confirm_matrix_cases")

    cases = cases_module.default_cases()
    summary = module.stressor_coverage(cases, module.DEFAULT_HIGH_VARIANCE_STRESSORS)
    variance = module.variance_evaluation(cases, module.DEFAULT_HIGH_VARIANCE_STRESSORS)

    assert summary["missing_required"] == []
    assert summary["cases_without_stressors"] == []
    assert variance["status"] == "passed"
    assert variance["score"] == 10
    assert variance["stressor_density"] >= 2
