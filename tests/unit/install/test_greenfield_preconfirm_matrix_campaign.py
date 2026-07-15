from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(
        SCRIPTS_ROOT / "greenfield_preconfirm_matrix.py",
        "greenfield_preconfirm_matrix_campaign_test",
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _case(module, name: str, *, stressors: tuple[str, ...] = ()):
    return module.GreenfieldMatrixCase(
        name=name,
        prompt=f"Create a greenfield proposal for {name} evidence review.",
        required_terms=tuple(name.split()[:1]) or ("case",),
        leakage_terms=(f"{name} sentinel",),
        stressors=stressors,
    )


def _result(module, *, name: str, passed: bool = True):
    score = 10 if passed else 0
    return module.GreenfieldMatrixResult(
        name=name,
        status="passed" if passed else "failed",
        create_seconds=18.0,
        counts=module.GreenfieldArtifactCounts(),
        quality=module.GreenfieldQualityVerdict(
            passed=passed,
            issues=() if passed else ("commit-only create did not write records",),
            lenses={
                "product_manager": passed,
                "architect": passed,
                "engineer": passed,
                "domain_expert": passed,
            },
            scores={dimension: score for dimension in module.QUALITY_SCORE_DIMENSIONS},
            score=score,
            score_explanation=("campaign test verdict",),
        ),
    )


class _Server:
    def shutdown(self) -> None:
        return None

    def server_close(self) -> None:
        return None


def test_run_matrix_writes_incremental_telemetry_and_stops_on_failure_threshold(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    calls: list[str] = []

    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (_Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_with_platform_leakage_issues", lambda **kwargs: tuple(kwargs["results"]))

    def fake_run_case(**kwargs):
        case = kwargs["case"]
        calls.append(case.name)
        return _result(module, name=case.name, passed=False)

    monkeypatch.setattr(module, "_run_case", fake_run_case)
    telemetry_path = tmp_path / "telemetry" / "progress.jsonl"
    incremental_output = tmp_path / "matrix" / "partial.json"

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(
            _case(module, "alpha review", stressors=("modal-expert-lens",)),
            _case(module, "beta review", stressors=("latency-pressure",)),
        ),
        include_browser_proof=False,
        install_mode="full",
        telemetry_jsonl=telemetry_path,
        campaign_phase="failed-subset",
        proof_tier="discovery",
        stop_after_failures=1,
        required_stressors=("modal-expert-lens",),
        incremental_output_json=incremental_output,
    )

    rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    incremental_payload = json.loads(incremental_output.read_text(encoding="utf-8"))
    assert calls == ["alpha review"]
    assert len(results) == 1
    assert [row["event"] for row in rows] == [
        "run_started",
        "case_started",
        "case_completed",
        "run_stopped",
        "run_finished",
    ]
    assert rows[0]["phase"] == "failed-subset"
    assert rows[2]["failure_cluster"] == "commit.only.create.did.not.write.records"
    assert rows[3]["reason"] == "failure-threshold:1"


def test_run_matrix_emits_failed_case_completion_when_run_case_raises(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (_Server(), "http://127.0.0.1:8123"))

    def fake_run_case(**_kwargs):  # noqa: ANN001
        raise RuntimeError("forced matrix case explosion")

    monkeypatch.setattr(module, "_run_case", fake_run_case)
    telemetry_path = tmp_path / "telemetry" / "progress.jsonl"
    incremental_output = tmp_path / "matrix" / "partial.json"

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(_case(module, "alpha review"),),
        include_browser_proof=False,
        install_mode="full",
        telemetry_jsonl=telemetry_path,
        campaign_phase="volume-discovery",
        proof_tier="discovery",
        incremental_output_json=incremental_output,
    )

    rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    incremental_payload = json.loads(incremental_output.read_text(encoding="utf-8"))
    assert [row["event"] for row in rows] == [
        "run_started",
        "case_started",
        "case_completed",
        "run_stopped",
        "run_finished",
    ]
    assert results[0].status == "case-execution-exception"
    assert rows[2]["failure_cluster"] == "forced.matrix.case.explosion"
    assert rows[3]["reason"] == "case-execution-exception"
    assert incremental_payload["status"] == "failed"
    assert incremental_payload["campaign"]["failed_case_count"] == 1
    assert "forced matrix case explosion" in incremental_payload["results"][0]["failure_detail"]
    assert rows[4]["summary"]["completed_case_count"] == 1
    assert rows[4]["summary"]["stopped_early"] is False
    assert incremental_payload["incremental"] is True
    assert incremental_payload["status"] == "failed"
    assert incremental_payload["results"][0]["name"] == "alpha review"
    assert incremental_payload["campaign"]["completed_case_count"] == 1


def test_run_matrix_applies_platform_leakage_before_live_stop(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    calls: list[str] = []

    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (_Server(), "http://127.0.0.1:8123"))

    def fake_run_case(**kwargs):
        case = kwargs["case"]
        calls.append(case.name)
        return replace(_result(module, name=case.name), platform_leakage_terms=("zephyr sentinel",))

    def fake_leakage(**kwargs):
        result = tuple(kwargs["results"])[0]
        quality = replace(
            result.quality,
            passed=False,
            issues=("platform domain leakage after generated artifact readback: src/x.py:1 leaked `zephyr sentinel`",),
            score=0,
        )
        return (replace(result, status="failed", quality=quality, platform_leakage_issues=quality.issues),)

    monkeypatch.setattr(module, "_run_case", fake_run_case)
    monkeypatch.setattr(module, "_with_platform_leakage_issues", fake_leakage)
    telemetry_path = tmp_path / "telemetry" / "progress.jsonl"
    incremental_output = tmp_path / "matrix" / "partial.json"

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(
            _case(module, "alpha review", stressors=("modal-expert-lens",)),
            _case(module, "beta review", stressors=("latency-pressure",)),
        ),
        include_browser_proof=False,
        install_mode="full",
        telemetry_jsonl=telemetry_path,
        campaign_phase="volume-discovery",
        proof_tier="discovery",
        stop_after_failures=1,
        incremental_output_json=incremental_output,
    )

    rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    incremental_payload = json.loads(incremental_output.read_text(encoding="utf-8"))
    assert calls == ["alpha review"]
    assert len(results) == 1
    assert results[0].platform_leakage_issues
    assert rows[2]["event"] == "case_completed"
    assert rows[2]["result"]["quality_passed"] is False
    assert rows[3]["reason"] == "failure-threshold:1"
    assert incremental_payload["status"] == "failed"
    assert incremental_payload["results"][0]["platform_leakage_issues"]
    assert incremental_payload["campaign"]["failed_case_count"] == 1


def test_run_matrix_flushes_failed_incremental_payload_before_cleanup_abort(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (_Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_with_platform_leakage_issues", lambda **kwargs: tuple(kwargs["results"]))
    monkeypatch.setattr(module, "_run_case", lambda **kwargs: _result(module, name=kwargs["case"].name))
    monkeypatch.setattr(
        module,
        "_cleanup_repo_before_next",
        lambda _repo_root: (_ for _ in ()).throw(RuntimeError("forced cleanup failure")),
    )
    telemetry_path = tmp_path / "telemetry" / "progress.jsonl"
    incremental_output = tmp_path / "matrix" / "partial.json"

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(_case(module, "alpha review"),),
        include_browser_proof=False,
        install_mode="full",
        telemetry_jsonl=telemetry_path,
        campaign_phase="failed-subset",
        proof_tier="discovery",
        incremental_output_json=incremental_output,
    )

    rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    incremental_payload = json.loads(incremental_output.read_text(encoding="utf-8"))
    assert results[0].status == "failed"
    assert "temp cleanup failed" in results[0].quality.issues[0]
    assert rows[2]["event"] == "case_completed"
    assert rows[2]["result"]["quality_passed"] is False
    assert rows[3]["reason"] == "temp-cleanup-failed"
    assert incremental_payload["status"] == "failed"
    assert incremental_payload["campaign"]["stop_reason"] == "temp-cleanup-failed"
    assert "forced cleanup failure" in incremental_payload["results"][0]["failure_detail"]


def test_main_persists_campaign_summary_for_discovery_runs(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    matrix_kwargs: dict[str, object] = {}

    def fake_run_matrix(**kwargs):
        matrix_kwargs.update(kwargs)
        return (_result(module, name="matrix case"),)

    monkeypatch.setattr(module, "run_matrix", fake_run_matrix)
    monkeypatch.setattr(
        module,
        "run_rescue_smoke",
        lambda **_kwargs: module.GreenfieldRescueSmokeResult(
            status="passed",
            cli_create_seconds=3.0,
            counts=module.GreenfieldArtifactCounts(),
            issues=(),
            manifest={},
        ),
    )

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--proof-tier",
            "discovery",
            "--campaign-phase",
            "60-case-regression",
            "--telemetry-jsonl",
            str(tmp_path / "progress.jsonl"),
            "--stop-after-failures",
            "2",
            "--allow-skipped-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert matrix_kwargs["proof_tier"] == "discovery"
    assert matrix_kwargs["campaign_phase"] == "60-case-regression"
    assert matrix_kwargs["stop_after_failures"] == 2
    assert payload["campaign"]["phase"] == "60-case-regression"
    assert payload["campaign"]["proof_tier"] == "discovery"
    assert payload["campaign"]["release_readiness_boundary"].startswith("discovery proof may skip browser")


def test_main_rejects_release_policy_without_browser_proof(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")

    try:
        module.main(
            [
                "--dist-dir",
                str(dist_dir),
                "--version",
                "0.1.15",
                "--temp-parent",
                str(tmp_path),
                "--proof-tier",
                "release",
            ]
        )
    except RuntimeError as exc:
        assert "release proof must include browser proof" in str(exc)
    else:
        raise AssertionError("release proof without browser proof should be rejected")


def test_main_rejects_release_policy_without_natural_rescue_proof(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")

    try:
        module.main(
            [
                "--dist-dir",
                str(dist_dir),
                "--version",
                "0.1.15",
                "--temp-parent",
                str(tmp_path),
                "--proof-tier",
                "release",
                "--include-browser-proof",
            ]
        )
    except RuntimeError as exc:
        assert "release proof must include natural rescue proof" in str(exc)
    else:
        raise AssertionError("release proof without natural rescue proof should be rejected")
