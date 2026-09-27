from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tests.unit.install.test_greenfield_preconfirm_matrix_proof_scope import (
    REPO_ROOT,
    _module,
    _passing_clarification_profile_result,
    _passing_matrix_result,
    _passing_profile_result,
    _release_audit_binding,
    _write,
)


def test_release_recovery_selection_requires_an_edited_source_provenanced_case() -> None:
    module = _module()
    source_cases = module.load_case_file(
        REPO_ROOT / "tests/fixtures/greenfield-release-corpus/greenfield-release-source-provenanced.v3.json"
    )

    confirmed_case = next(case for case in source_cases if case.case_id == "release-accessibility-007-source")
    binding = _release_audit_binding(confirmed_case)
    audit_binding = {
        confirmed_case.case_id: binding
    }

    selected = module.select_recovery_case(
        source_cases,
        proof_tier="release",
        approved_audit_bindings=audit_binding,
    )

    assert selected.case_id == "release-accessibility-007-source"
    assert selected.confirmed_intent_markdown
    assert selected.provenance.corpus_tier == "source_provenanced"
    assert selected.provenance.derived_prompt_sha256

    with pytest.raises(RuntimeError, match="matching audited confirmed intent hash"):
        module.select_recovery_case(
            source_cases,
            proof_tier="release",
            approved_audit_bindings={
                confirmed_case.case_id: {
                    "audit_request_sha256": binding["audit_request_sha256"],
                    "confirmed_intent_sha256": "f" * 64,
                    "source_verification_method": binding["source_verification_method"],
                    "source_verification_uri": binding["source_verification_uri"],
                }
            },
        )

    with pytest.raises(RuntimeError, match="audited request bound to current case semantics"):
        module.select_recovery_case(
            source_cases,
            proof_tier="release",
            approved_audit_bindings={
                confirmed_case.case_id: {
                    **audit_binding[confirmed_case.case_id],
                    "audit_request_sha256": "a" * 64,
                }
            },
        )


def test_release_campaign_forwards_the_evaluated_audit_binding_to_commit_recovery(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    module = _module()
    source_cases = module.load_case_file(
        REPO_ROOT / "tests/fixtures/greenfield-release-corpus/greenfield-release-source-provenanced.v3.json"
    )
    recovery_case = next(case for case in source_cases if case.case_id == "release-accessibility-007-source")
    binding = _release_audit_binding(recovery_case)
    captured: dict[str, object] = {}
    args = module.argparse.Namespace(
        dist_dir=str(tmp_path / "dist"),
        version="0.1.15",
        include_browser_proof=True,
        install_mode="fresh",
        allow_partial_stressor_coverage=False,
        include_commit_recovery_proof=True,
        json_output=True,
        attempt_ledger_jsonl=None,
    )
    config = module.MatrixCampaignConfig(
        phase=module.campaign_phase_from_value("gate"),
        proof_tier=module.proof_tier_from_value("release"),
        telemetry_jsonl=None,
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        required_stressors=(),
    )
    corpus = type(
        "ReleaseCorpus",
        (),
        {
            "summary": {"approved_audit_bindings": {recovery_case.case_id: binding}},
            "to_dict": lambda self: {"status": "passed"},
        },
    )()
    lease = type(
        "Lease",
        (),
        {
            "temp_namespace": tmp_path,
            "to_dict": lambda self: {"temporary_namespace": str(tmp_path)},
        },
    )()
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))
    monkeypatch.setattr(module, "run_unavailable_provider_proof", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(module, "model_profile_release_proof", lambda *_args, **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "build_onboarding_quality_scorecard",
        lambda **_kwargs: {"status": "passed", "score": 10},
    )
    monkeypatch.setattr(module, "browser_proof_summary", lambda *_args, **_kwargs: {"status": "passed"})
    monkeypatch.setattr(module, "_platform_leakage_proof_summary", lambda _results: {"status": "passed"})
    monkeypatch.setattr(module, "temp_cleanup_proof", lambda _path: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "campaign_summary",
        lambda **_kwargs: {
            "outcome_statistics": {"status": "passed", "passed": True}
        },
    )

    def fake_commit_recovery(**kwargs):
        captured.update(kwargs)
        return module.GreenfieldInstalledCommitRecoveryProof(
            status="passed",
            issues=(),
            recovery_case={"binding_scope": "release-confirmed-intent-v1"},
        )

    monkeypatch.setattr(module, "run_installed_commit_recovery_proof", fake_commit_recovery)

    exit_code = module._execute_matrix_campaign(
        args=args,
        selected_cases=(recovery_case,),
        planned_cases=(recovery_case,),
        release_audits=(),
        campaign_config=config,
        corpus_provenance=corpus,
        output_path=None,
        lease=lease,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert captured["recovery_case"] is recovery_case
    assert captured["require_release_binding"] is True
    assert captured["release_audit_binding"] == binding
    assert payload["commit_recovery_proof"]["recovery_case"]["binding_scope"] == "release-confirmed-intent-v1"


def test_release_campaign_keeps_luna_control_separate_from_corpus_acceptance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _module()
    standard_id = module.model_profile_id_for_repair_tier("standard")
    luna_id = module.LOWER_CAPABILITY_CONTROL_PROFILES[0]
    main_case = replace(
        module.default_cases()[0],
        tags=(f"model-profile:{standard_id}",),
    )
    control_case = module.GreenfieldMatrixCase(
        case_id="supplemental-luna-control",
        name="supplemental Luna control",
        prompt="Ask one question about the first complete result.",
        required_terms=(),
        expectation="clarification_required",
        tags=(f"model-profile:{luna_id}",),
    )
    main_result = _passing_profile_result(module, standard_id, 20.0)
    control_result = _passing_clarification_profile_result(module, luna_id, 20.0)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    manifest = module.retained_evidence_manifest_path(evidence_dir)
    _write(manifest, "{}\n")
    args = module.argparse.Namespace(
        dist_dir=str(tmp_path / "dist"),
        version="0.1.15",
        include_browser_proof=True,
        install_mode="full",
        allow_partial_stressor_coverage=False,
        include_commit_recovery_proof=False,
        json_output=True,
        attempt_ledger_jsonl=None,
        semantic_annotations_file=str(tmp_path / "annotations.json"),
        evaluation_split_manifest=str(tmp_path / "splits.json"),
        evidence_output_dir=str(evidence_dir),
        host_candidate_arg=(
            "/trusted/codex", "exec", "--ephemeral", "--ignore-user-config",
            "--skip-git-repo-check", "--sandbox", "read-only",
            "--model", "{model}", "--config",
            "model_reasoning_effort={reasoning_effort}", "--output-schema",
            "{candidate_schema}", "-",
        ),
        lower_capability_control_file=str(tmp_path / "luna-control.json"),
    )
    config = module.MatrixCampaignConfig(
        phase=module.campaign_phase_from_value("gate"),
        proof_tier=module.proof_tier_from_value("release"),
        telemetry_jsonl=None,
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        required_stressors=(),
    )
    lease = type(
        "Lease",
        (),
        {
            "temp_namespace": tmp_path / "work",
            "to_dict": lambda self: {"temporary_namespace": str(self.temp_namespace)},
        },
    )()
    run_calls: list[dict[str, object]] = []
    profile_inputs: list[object] = []
    browser_inputs: list[object] = []
    metamorphic_inputs: list[dict[str, object]] = []
    semantic_inputs: list[dict[str, object]] = []

    def fake_run_matrix(**kwargs):
        run_calls.append(kwargs)
        return (control_result,) if kwargs["cases"] == (control_case,) else (main_result,)

    monkeypatch.setattr(module, "run_matrix", fake_run_matrix)
    monkeypatch.setattr(module, "_require_profile_argv_template", lambda argv: tuple(argv))
    monkeypatch.setattr(module, "run_unavailable_provider_proof", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "model_profile_release_proof",
        lambda results, **_kwargs: profile_inputs.append(tuple(results)) or {
            "status": "passed",
            "lower_capability_scope": {"status": "passed"},
        },
    )
    monkeypatch.setattr(
        module,
        "browser_proof_summary",
        lambda results, **_kwargs: browser_inputs.append(tuple(results)) or {"status": "passed"},
    )
    monkeypatch.setattr(module, "_platform_leakage_proof_summary", lambda _results: {"status": "passed"})
    monkeypatch.setattr(module, "temp_cleanup_proof", lambda _path: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "campaign_summary",
        lambda **_kwargs: {
            "outcome_statistics": {"status": "passed", "passed": True}
        },
    )
    monkeypatch.setattr(
        module,
        "_semantic_release_report",
        lambda **kwargs: semantic_inputs.append(kwargs) or {"status": "passed"},
    )
    monkeypatch.setattr(
        module,
        "evaluate_metamorphic_outputs",
        lambda **kwargs: metamorphic_inputs.append(kwargs) or {"passed": True},
    )
    monkeypatch.setattr(
        module,
        "build_onboarding_quality_scorecard",
        lambda **_kwargs: {"status": "passed", "score": 10},
    )
    monkeypatch.setattr(
        module,
        "retained_evidence_result",
        lambda *_args, **_kwargs: {
            "status": "passed",
            "manifest": str(evidence_dir / "retained-evidence-manifest.v1.json"),
            "manifest_sha256": "a" * 64,
            "project_navigation": [],
            "issues": [],
        },
    )

    exit_code = module._execute_matrix_campaign(
        args=args,
        selected_cases=(main_case,),
        planned_cases=(main_case,),
        release_audits=(),
        campaign_config=config,
        corpus_provenance={"status": "passed"},
        output_path=None,
        lease=lease,
        lower_capability_control_case=control_case,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["version"] == "greenfield-preconfirm-installed-matrix-v2"
    assert len(run_calls) == 2
    assert run_calls[0]["cases"] == (main_case,)
    assert run_calls[1]["cases"] == (control_case,)
    assert run_calls[1]["include_browser_proof"] is False
    assert run_calls[1]["proof_tier"] == "discovery"
    assert str(run_calls[1]["evidence_output_dir"]).endswith("-lower-capability-control")
    assert profile_inputs == [(main_result, control_result)]
    assert browser_inputs == [(main_result,)]
    assert semantic_inputs[0]["cases"] == (main_case,)
    assert semantic_inputs[0]["results"] == (main_result,)
    assert metamorphic_inputs[0]["cases"] == (main_case,)
    assert metamorphic_inputs[0]["results"] == (main_result,)
    assert len(payload["results"]) == 1
    assert payload["lower_capability_control_proof"]["status"] == "passed"
    assert payload["lower_capability_control_proof"]["case_count"] == 1
    assert payload["lower_capability_control_proof"]["profile_id"] == luna_id


def test_semantic_release_campaign_uses_sealed_case_binding_for_commit_recovery(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    module = _module()
    recovery_case = module.GreenfieldMatrixCase(
        name="semantic recovery case",
        prompt="Operator records one semantic recovery receipt.",
        required_terms=("semantic", "recovery"),
        case_id="semantic-recovery-case",
    )
    captured: dict[str, object] = {}
    args = module.argparse.Namespace(
        dist_dir=str(tmp_path / "dist"),
        version="0.1.15",
        include_browser_proof=True,
        install_mode="fresh",
        allow_partial_stressor_coverage=False,
        include_commit_recovery_proof=True,
        json_output=True,
        attempt_ledger_jsonl=None,
        semantic_annotations_file=str(tmp_path / "final-holdout.v1.json"),
        evaluation_split_manifest=str(tmp_path / "evaluation-splits.v1.json"),
    )
    config = module.MatrixCampaignConfig(
        phase=module.campaign_phase_from_value("gate"),
        proof_tier=module.proof_tier_from_value("release"),
        telemetry_jsonl=None,
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        required_stressors=(),
    )
    lease = type(
        "Lease",
        (),
        {
            "temp_namespace": tmp_path,
            "to_dict": lambda self: {"temporary_namespace": str(tmp_path)},
        },
    )()
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))
    monkeypatch.setattr(module, "run_unavailable_provider_proof", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(module, "model_profile_release_proof", lambda *_args, **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "build_onboarding_quality_scorecard",
        lambda **_kwargs: {"status": "passed", "score": 10},
    )
    monkeypatch.setattr(module, "browser_proof_summary", lambda *_args, **_kwargs: {"status": "passed"})
    monkeypatch.setattr(module, "_platform_leakage_proof_summary", lambda _results: {"status": "passed"})
    monkeypatch.setattr(module, "temp_cleanup_proof", lambda _path: {"status": "passed"})
    monkeypatch.setattr(module, "_semantic_release_report", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "campaign_summary",
        lambda **_kwargs: {
            "outcome_statistics": {"status": "passed", "passed": True}
        },
    )

    def fake_commit_recovery(**kwargs):
        captured.update(kwargs)
        return module.GreenfieldInstalledCommitRecoveryProof(
            status="passed",
            issues=(),
            recovery_case={"binding_scope": "campaign-case-v1"},
        )

    monkeypatch.setattr(module, "run_installed_commit_recovery_proof", fake_commit_recovery)

    exit_code = module._execute_matrix_campaign(
        args=args,
        selected_cases=(recovery_case,),
        planned_cases=(recovery_case,),
        release_audits=(),
        campaign_config=config,
        corpus_provenance={"status": "passed"},
        output_path=None,
        lease=lease,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert captured["recovery_case"] is recovery_case
    assert captured["require_release_binding"] is False
    assert captured["release_audit_binding"] is None
    assert payload["commit_recovery_proof"]["recovery_case"]["binding_scope"] == "campaign-case-v1"


def test_release_campaign_fails_when_onboarding_scorecard_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _module()
    release_case = module.default_cases()[0]
    args = module.argparse.Namespace(
        dist_dir=str(tmp_path / "dist"),
        version="0.1.15",
        include_browser_proof=True,
        install_mode="fresh",
        allow_partial_stressor_coverage=False,
        include_commit_recovery_proof=False,
        json_output=True,
        attempt_ledger_jsonl=None,
        semantic_annotations_file="",
        evaluation_split_manifest="",
    )
    config = module.MatrixCampaignConfig(
        phase=module.campaign_phase_from_value("gate"),
        proof_tier=module.proof_tier_from_value("release"),
        telemetry_jsonl=None,
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        required_stressors=(),
    )
    lease = type(
        "Lease",
        (),
        {
            "temp_namespace": tmp_path,
            "to_dict": lambda self: {"temporary_namespace": str(tmp_path)},
        },
    )()
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))
    monkeypatch.setattr(module, "run_unavailable_provider_proof", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(module, "model_profile_release_proof", lambda *_args, **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "build_onboarding_quality_scorecard",
        lambda **_kwargs: {"status": "failed", "score": 0},
    )
    monkeypatch.setattr(module, "browser_proof_summary", lambda *_args, **_kwargs: {"status": "passed"})
    monkeypatch.setattr(module, "_platform_leakage_proof_summary", lambda _results: {"status": "passed"})
    monkeypatch.setattr(module, "temp_cleanup_proof", lambda _path: {"status": "passed"})
    monkeypatch.setattr(module, "_semantic_release_report", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        module,
        "campaign_summary",
        lambda **_kwargs: {
            "outcome_statistics": {"status": "passed", "passed": True}
        },
    )

    exit_code = module._execute_matrix_campaign(
        args=args,
        selected_cases=(release_case,),
        planned_cases=(release_case,),
        release_audits=(),
        campaign_config=config,
        corpus_provenance={"status": "passed"},
        output_path=None,
        lease=lease,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["onboarding_quality_scorecard"] == {"status": "failed", "score": 0}


def test_final_holdout_child_rechecks_sealed_distribution_provenance_before_claim(tmp_path: Path) -> None:
    module = _module()
    sealed_root = tmp_path / "sealed-inputs"
    provenance = sealed_root / "private/build-provenance.v1.json"
    provenance.parent.mkdir(parents=True)
    provenance.write_text(
        json.dumps(
            {
                "version": "odylith-release-provenance.v1",
                "source_tree": {"head": "a" * 40, "dirty": False},
                "workflow": {"sha": "a" * 40},
            }
        ),
        encoding="utf-8",
    )
    ledger = tmp_path / "final-holdout-run.v1.json"
    args = module.argparse.Namespace(
        proof_tier="release",
        final_holdout_run_ledger=str(ledger),
        implementation_revision="b" * 40,
        output_json=str(tmp_path / "result.json"),
        semantic_annotations_file=str(sealed_root / "private/final-holdout.v1.json"),
        evaluation_split_manifest=str(sealed_root / "evaluation-splits.v1.json"),
        distribution_provenance_file=str(provenance),
    )

    with pytest.raises(RuntimeError, match="implementation revision does not match distribution build provenance"):
        module._final_holdout_run_from_args(args, sealed_input_root=str(sealed_root))
    assert not ledger.exists()

    args.implementation_revision = "a" * 40
    holdout_run = module._final_holdout_run_from_args(args, sealed_input_root=str(sealed_root))

    assert holdout_run is not None
    assert holdout_run.implementation_revision == "a" * 40
    assert not ledger.exists()
