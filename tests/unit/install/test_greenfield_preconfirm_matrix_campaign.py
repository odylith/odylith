from __future__ import annotations

import importlib.util
import json
import subprocess
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
    profile_id = module.model_profile_id_for_repair_tier("standard")
    profile = module.get_greenfield_model_profile(profile_id)
    return module.GreenfieldMatrixResult(
        name=name,
        status="passed" if passed else "failed",
        proposal_seconds=18.0,
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
        evidence={
            "case": {"id": name},
            "model_profile": {
                "profile_id": profile_id,
                "status": "passed",
                "issues": [],
                "observed": {
                    "profile_id": profile_id,
                    "provider": profile.provider,
                    "model": profile.model,
                    "reasoning_effort": profile.reasoning_effort,
                    "effective_timeout_seconds": profile.model_timeout_seconds,
                    "authoring_tier": profile.repair_tier,
                },
            },
        },
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


def test_run_matrix_emits_redacted_process_lifecycle_events(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    secret_prompt = "--customer-private launch narrative"

    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (_Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_with_platform_leakage_issues", lambda **kwargs: tuple(kwargs["results"]))

    def fake_run_case(**kwargs):
        kwargs["repo_root"].mkdir(parents=True, exist_ok=True)
        completed = module._run(
            cwd=kwargs["repo_root"],
            env={},
            command=[sys.executable, "-c", "print('ok')", "--prompt", secret_prompt],
            timeout=5,
        )
        assert completed.returncode == 0
        return _result(module, name=kwargs["case"].name)

    monkeypatch.setattr(module, "_run_case", fake_run_case)
    telemetry_path = tmp_path / "telemetry" / "progress.jsonl"

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(_case(module, "alpha review"),),
        install_mode="full",
        telemetry_jsonl=telemetry_path,
        proof_tier="discovery",
    )

    rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    command_rows = [row for row in rows if row["event"].startswith("command_")]
    serialized = json.dumps(command_rows, sort_keys=True)
    assert results[0].status == "passed"
    assert [row["event"] for row in command_rows] == ["command_started", "command_completed"]
    assert command_rows[0]["option_count"] == 2
    assert command_rows[1]["returncode"] == 0
    assert secret_prompt not in serialized
    assert "print('ok')" not in serialized


def test_seeded_matrix_emits_lifecycle_events_for_prepare_and_clone_subprocesses(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (_Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_with_platform_leakage_issues", lambda **kwargs: tuple(kwargs["results"]))

    def fake_prepare_seed_repo(*, seed_repo, **_kwargs):
        seed_repo.mkdir(parents=True)
        module._run(cwd=seed_repo, env={}, command=[sys.executable, "-c", ""], timeout=5)
        return subprocess.CompletedProcess(["bash", "install.sh"], 0, stdout="", stderr="")

    def fake_clone_seed_repo(*, repo_root, **_kwargs):
        repo_root.mkdir(parents=True)
        module._run(cwd=repo_root, env={}, command=[sys.executable, "-c", ""], timeout=5)

    monkeypatch.setattr(module, "_prepare_seed_repo", fake_prepare_seed_repo)
    monkeypatch.setattr(module, "_clone_seed_repo", fake_clone_seed_repo)
    monkeypatch.setattr(module, "_run_case", lambda **kwargs: _result(module, name=kwargs["case"].name))
    telemetry_path = tmp_path / "telemetry" / "progress.jsonl"

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(_case(module, "alpha review"),),
        install_mode="seeded",
        telemetry_jsonl=telemetry_path,
        proof_tier="discovery",
    )

    rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    command_rows = [row for row in rows if row["event"].startswith("command_")]
    assert results[0].status == "passed"
    assert [row["event"] for row in command_rows] == [
        "command_started",
        "command_completed",
        "command_started",
        "command_completed",
    ]


def test_run_matrix_reports_terminal_telemetry_failure_without_mislabeling_the_command(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    original_emit = module.MatrixTelemetryWriter.emit

    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (_Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_with_platform_leakage_issues", lambda **kwargs: tuple(kwargs["results"]))

    def fail_after_terminal_event(self, event, payload):  # noqa: ANN001
        original_emit(self, event, payload)
        if event == "command_completed":
            raise OSError("fsync unavailable")

    def fake_run_case(**kwargs):
        kwargs["repo_root"].mkdir(parents=True, exist_ok=True)
        module._run(cwd=kwargs["repo_root"], env={}, command=[sys.executable, "-c", "pass"], timeout=5)
        return _result(module, name=kwargs["case"].name)

    monkeypatch.setattr(module.MatrixTelemetryWriter, "emit", fail_after_terminal_event)
    monkeypatch.setattr(module, "_run_case", fake_run_case)
    telemetry_path = tmp_path / "telemetry" / "progress.jsonl"

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(_case(module, "alpha review"),),
        install_mode="full",
        telemetry_jsonl=telemetry_path,
        proof_tier="discovery",
    )

    assert results[0].status == "command-lifecycle-telemetry-failed"
    assert "terminal_state=completed" in results[0].quality.issues[0]
    assert "returncode=0" not in results[0].quality.issues[0]


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
    execution_order: list[str] = []
    telemetry_path = tmp_path / "progress.jsonl"

    def fake_run_matrix(**kwargs):
        execution_order.append("matrix")
        matrix_kwargs.update(kwargs)
        return (_result(module, name="matrix case"),)

    monkeypatch.setattr(module, "run_matrix", fake_run_matrix)
    def fake_commit_recovery(**kwargs):
        execution_order.append("commit_recovery")
        module._run(
            cwd=kwargs["temp_parent"],
            env={},
            command=[sys.executable, "-c", "pass"],
            timeout=5,
        )
        return module.GreenfieldInstalledCommitRecoveryProof(status="passed", issues=())

    monkeypatch.setattr(module, "run_installed_commit_recovery_proof", fake_commit_recovery)
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
            str(telemetry_path),
                "--stop-after-failures",
                "2",
                "--include-commit-recovery-proof",
                "--allow-skipped-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert matrix_kwargs["proof_tier"] == "discovery"
    assert matrix_kwargs["campaign_phase"] == "60-case-regression"
    assert matrix_kwargs["stop_after_failures"] == 2
    assert execution_order[:2] == ["matrix", "commit_recovery"]
    assert payload["proof_scope"]["commit_recovery_path"] == module.COMMIT_RECOVERY_PROOF_SCOPE
    assert payload["commit_recovery_proof"]["status"] == "passed"
    assert payload["campaign"]["phase"] == "60-case-regression"
    assert payload["campaign"]["proof_tier"] == "discovery"
    assert payload["campaign"]["release_readiness_boundary"].startswith("discovery proof may skip browser")
    telemetry_rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in telemetry_rows if row["event"].startswith("command_")] == [
        "command_started",
        "command_completed",
    ]


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


def test_main_release_policy_does_not_require_retired_rescue_proofs(tmp_path: Path) -> None:
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
        assert "release proof must include installed commit recovery proof" in str(exc)
    else:
        raise AssertionError("release proof without commit recovery proof should be rejected")


def test_main_rejects_release_policy_without_installed_commit_recovery_proof(tmp_path: Path) -> None:
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
        assert "release proof must include installed commit recovery proof" in str(exc)
    else:
        raise AssertionError("release proof without installed commit recovery proof should be rejected")
