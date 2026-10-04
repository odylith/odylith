from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tests.greenfield_model_profile_test_support import sealed_profile_observation
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
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return _load_module(SCRIPTS_ROOT / "greenfield_preconfirm_matrix.py", "greenfield_preconfirm_matrix")


def _release_audit_binding(case) -> dict[str, str]:
    audit_evidence = importlib.import_module("greenfield_matrix_release_audit_evidence")
    source_verification_method = "github-rest-v3"
    source_verification_uri = "https://api.github.com/repositories/295992065"
    request = audit_evidence.audit_request_for_case(
        case,
        source_verification_method=source_verification_method,
        source_verification_uri=source_verification_uri,
    )
    return {
        "audit_request_sha256": audit_evidence.audit_request_sha256(request),
        "confirmed_intent_sha256": audit_evidence.case_confirmed_intent_sha256(case),
        "source_verification_method": source_verification_method,
        "source_verification_uri": source_verification_uri,
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_direct_runner_interrupt_terminalizes_before_empty_lease_release(tmp_path: Path) -> None:
    module = _module()
    holdout = tmp_path / "holdout.json"
    manifest = tmp_path / "manifest.json"
    _write(holdout, '{"cases": []}\n')
    _write(manifest, '{}\n')
    run = module._FinalHoldoutRun(
        ledger_path=tmp_path / "run-ledger.json",
        holdout_path=holdout,
        evaluation_manifest_path=manifest,
        case_paths=(holdout,),
        implementation_revision="a" * 40,
        distribution_provenance_sha256="b" * 64,
    )
    run.claim()
    temp_parent = tmp_path / "work"
    output_path = tmp_path / "partial-result.json"
    evidence_output_dir = tmp_path / "evidence"
    _write(output_path, '{"status": "running"}\n')
    lease = module.acquire_matrix_run_lease(
        temp_parent=temp_parent,
        output_path=tmp_path / "terminal-result.json",
    )

    interrupted = module._terminalize_interrupted_final_holdout(
        run=run,
        error=KeyboardInterrupt(),
        output_path=output_path,
        evidence_output_dir=evidence_output_dir,
        temp_parent=temp_parent,
    )

    terminal = json.loads(run.ledger_path.read_text(encoding="utf-8"))
    assert terminal["status"] == "interrupted"
    assert terminal["retained_evidence"]["manifest_path"] == str(
        evidence_output_dir / "retained-evidence-manifest.v1.json"
    )
    assert interrupted.parent == run.ledger_path.parent
    assert not interrupted.is_relative_to(lease.temp_namespace)
    module._release_matrix_lease_without_masking(lease=lease, active_error=None)
    assert not lease.temp_namespace.exists()


@pytest.mark.parametrize("cleanup_error_type", [RuntimeError, OSError])
def test_lease_cleanup_error_is_not_allowed_to_mask_active_interrupt(
    cleanup_error_type: type[BaseException],
) -> None:
    module = _module()

    class BrokenLease:
        def release(self) -> None:
            raise cleanup_error_type("namespace remained non-empty")

    active = KeyboardInterrupt()
    module._release_matrix_lease_without_masking(
        lease=BrokenLease(),
        active_error=active,
    )

    assert active.__notes__ == [
        "matrix lease cleanup also failed: namespace remained non-empty"
    ]


@pytest.mark.parametrize("cleanup_error_type", [RuntimeError, OSError])
def test_lease_cleanup_error_is_raised_without_an_active_error(
    cleanup_error_type: type[BaseException],
) -> None:
    module = _module()

    class BrokenLease:
        def release(self) -> None:
            raise cleanup_error_type("namespace remained non-empty")

    with pytest.raises(cleanup_error_type, match="namespace remained non-empty"):
        module._release_matrix_lease_without_masking(
            lease=BrokenLease(),
            active_error=None,
        )


def test_interruption_sealing_failure_preserves_interrupt_and_claimed_ledger(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    run = module._FinalHoldoutRun(
        ledger_path=tmp_path / "run-ledger.json",
        holdout_path=tmp_path / "holdout.json",
        evaluation_manifest_path=tmp_path / "manifest.json",
        case_paths=(tmp_path / "holdout.json",),
        implementation_revision="a" * 40,
        distribution_provenance_sha256="b" * 64,
        claimed=True,
        run_id="c" * 64,
    )
    active = KeyboardInterrupt()
    monkeypatch.setattr(
        module,
        "seal_interrupted_retained_evidence",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("forced seal failure")),
    )

    module._terminalize_interrupted_final_holdout_without_masking(
        run=run,
        error=active,
        output_path=None,
        evidence_output_dir=tmp_path / "evidence",
        temp_parent=tmp_path / "work",
    )

    assert run.claimed is True
    assert active.__notes__ == [
        "final holdout interruption evidence could not be terminalized; "
        "the ledger remains claimed: forced seal failure"
    ]


def test_main_preserves_interrupt_through_claim_terminalization_and_finally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    evidence_dir = tmp_path / "evidence"
    sealed_root = tmp_path / "sealed"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")

    args = module.argparse.Namespace(
        include_default_cases=False,
        evidence_output_dir=str(evidence_dir),
        release_audit_repo_root="",
        required_stressor=(),
        require_high_variance_stressors=False,
        campaign_phase="gate",
        proof_tier="release",
        telemetry_jsonl="",
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        sealed_release_input_root=str(sealed_root),
        install_mode="full",
        include_browser_proof=False,
        include_commit_recovery_proof=False,
        allow_skipped_browser_proof=False,
        allow_partial_stressor_coverage=False,
        semantic_annotations_file=str(sealed_root / "qualification.json"),
        evaluation_split_manifest=str(sealed_root / "splits.json"),
        final_holdout_run_ledger=str(tmp_path / "run-ledger.json"),
        implementation_revision="a" * 40,
        distribution_provenance_file=str(sealed_root / "provenance.json"),
        case_file=(str(sealed_root / "cases.json"),),
        release_audit_file="",
        temp_parent=str(tmp_path / "work"),
        dist_dir=str(dist_dir),
        output_json=str(tmp_path / "partial-result.json"),
    )

    class ClaimedRun:
        ledger_path = tmp_path / "run-ledger.json"
        run_id = "c" * 64
        claimed = False

        def claim(self) -> None:
            self.claimed = True

    run = ClaimedRun()

    class Lease:
        released = False
        temp_namespace = tmp_path / "lease"

        def release(self) -> None:
            self.released = True
            raise OSError("forced lease cleanup failure")

    lease = Lease()
    child = {"alive": False}

    def interrupted_campaign(**_kwargs):
        child["alive"] = True
        try:
            raise KeyboardInterrupt()
        finally:
            child["alive"] = False

    monkeypatch.setattr(module, "_parse_args", lambda _argv: args)
    monkeypatch.setattr(module, "_require_sealed_release_input_root", lambda **_kwargs: None)
    monkeypatch.setattr(module, "_raise_for_invalid_campaign_policy", lambda **_kwargs: None)
    monkeypatch.setattr(module, "validate_retained_evidence_output_dir", lambda **_kwargs: None)
    monkeypatch.setattr(module, "_final_holdout_run_from_args", lambda *_args, **_kwargs: run)
    monkeypatch.setattr(module, "acquire_matrix_run_lease", lambda **_kwargs: lease)
    monkeypatch.setattr(
        module,
        "_load_cli_case_files",
        lambda *_args, **_kwargs: (
            module.GreenfieldMatrixCase(
                name="interrupt",
                prompt="Create one product.",
                required_terms=(),
            ),
        ),
    )
    monkeypatch.setattr(module, "evaluate_frozen_evaluation_contract", lambda **_kwargs: {"issues": []})
    monkeypatch.setattr(module, "_execute_matrix_campaign", interrupted_campaign)
    monkeypatch.setattr(
        module,
        "seal_interrupted_retained_evidence",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("forced seal failure")),
    )

    with pytest.raises(KeyboardInterrupt) as raised:
        module.main([])

    assert run.claimed is True
    assert lease.released is True
    assert child["alive"] is False
    assert raised.value.__notes__ == [
        "final holdout interruption evidence could not be terminalized; "
        "the ledger remains claimed: forced seal failure",
        "matrix lease cleanup also failed: forced lease cleanup failure",
    ]


def _write_supplement(
    path: Path,
    *,
    case_id: str,
    tags: tuple[str, ...],
    include_leakage: bool = True,
    expectation: str = "transaction_committed",
) -> Path:
    row = {
        "case_id": case_id,
        "name": "museum conservation queue",
        "prompt": "Create a greenfield proposal for museum conservation queue review.",
        "required_terms": ["museum", "conservation", "queue"],
        "tags": list(tags),
        "expectation": expectation,
    }
    if include_leakage:
        row["leakage_terms"] = ["museum conservation queue"]
    _write(path, json.dumps({"version": "odylith.greenfield.matrix.case-file.v1", "cases": [row]}))
    return path


def _full_counts(module) -> object:
    return module.GreenfieldArtifactCounts(
        radar_workstreams=4,
        registry_component_specs=3,
        atlas_mermaid_sources=4,
        compass_records=1,
        release_records=1,
        program_records=0,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=len(module.REQUIRED_RENDERED_SURFACES),
        rendered_surface_payloads=12,
        atlas_rendered_assets=8,
        domain_term_hits=3,
        project_implementation_prompts=5,
    )


def _passing_quality(module) -> object:
    return module.GreenfieldQualityVerdict(
        passed=True,
        issues=(),
        lenses={lens: True for lens in ("product_manager", "architect", "engineer", "domain_expert")},
        scores={dimension: 10 for dimension in module.QUALITY_SCORE_DIMENSIONS},
        score=10,
        score_explanation=("all brutal release-quality dimensions scored 10",),
    )


def _stage_observation(
    profile_id: str,
    *,
    clarification: bool = False,
) -> dict[str, object]:
    from tests.greenfield_model_profile_test_support import production_stage_observation

    return production_stage_observation(
        profile_id, response_kind="clarification_required" if clarification else "authored",
    )


def _profile_evidence(profile_id: str, *, clarification: bool = False) -> dict[str, object]:
    return {
        "profile_id": profile_id,
        "semantic_authority": "active_host_single_authority",
        "sealed_request_roles": (
            ["authority_gate"] if clarification else
            ["authority_gate", "source_ledger", "source_duty_verifier", "host_candidate"]
        ),
        "host_semantic_model_calls": 1 if clarification else 4,
        "runtime_semantic_model_calls_after_candidate_receipt": 0,
        "post_receipt_provider_invocations": 0,
        "stage_observation": _stage_observation(
            profile_id,
            clarification=clarification,
        ),
        "status": "passed",
        "issues": [],
        "observed": {} if clarification else sealed_profile_observation(profile_id),
    }


def _passing_matrix_result(module, *, manifest_summary: dict[str, object] | None = None) -> object:
    profile_id = module.model_profile_id_for_repair_tier("standard")
    profile_evidence = _profile_evidence(profile_id)
    stage = dict(profile_evidence["stage_observation"])
    stage["elapsed_seconds"] = 18.0
    stage["proposal_phase_elapsed_seconds"] = 18.0
    stage["whole_journey_seconds"] = 48.0
    profile_evidence["stage_observation"] = stage
    return module.GreenfieldMatrixResult(
        name="matrix case",
        status="passed",
        proposal_seconds=18.0,
        create_seconds=18.0,
        counts=_full_counts(module),
        quality=_passing_quality(module),
        browser_surface_proof_attempted=True,
        commit_manifest_summary=manifest_summary or {},
        evidence={
            "case": {
                "id": "matrix-case",
                "expectation": "transaction_committed",
                "prompt_sha256": "a" * 64,
            },
            "model_profile": profile_evidence,
        },
    )


def _passing_profile_result(module, profile_id: str, proposal_seconds: float) -> object:
    profile_evidence = _profile_evidence(profile_id)
    stage = dict(profile_evidence["stage_observation"])
    stage["elapsed_seconds"] = proposal_seconds
    stage["proposal_phase_elapsed_seconds"] = proposal_seconds
    stage["whole_journey_seconds"] = proposal_seconds + 30.0
    profile_evidence["stage_observation"] = stage
    return replace(
        _passing_matrix_result(module),
        name=profile_id,
        proposal_seconds=proposal_seconds,
        evidence={
            "case": {
                "id": profile_id,
                "expectation": "transaction_committed",
                "prompt_sha256": "a" * 64,
            },
            "model_profile": profile_evidence,
        },
    )


def _passing_clarification_profile_result(
    module,
    profile_id: str,
    proposal_seconds: float,
) -> object:
    expected_field = "first_path"
    expected_question = "Who uses this product first, and what complete result do they see?"
    result = _passing_profile_result(module, profile_id, proposal_seconds)
    profile_evidence = _profile_evidence(profile_id, clarification=True)
    stage = dict(profile_evidence["stage_observation"])
    stage["elapsed_seconds"] = proposal_seconds
    stage["proposal_phase_elapsed_seconds"] = proposal_seconds
    stage["whole_journey_seconds"] = proposal_seconds
    profile_evidence["stage_observation"] = stage
    return replace(
        result,
        name=f"{profile_id}-clarification",
        quality=replace(
            result.quality,
            score_basis="clarification_required_no_write_contract",
        ),
        evidence={
            **dict(result.evidence or {}),
            "model_profile": profile_evidence,
            "case": {
                "id": f"{profile_id}-clarification",
                "expectation": "clarification_required",
                "prompt_sha256": "b" * 64,
                "expected_clarification": {
                    "field": expected_field,
                    "question": expected_question,
                },
            },
            "clarification": {
                "mode": "clarification_required",
                "question": expected_question,
                "required_fields": [expected_field],
                "returncode": 0,
            },
            "no_write": {
                "before_record_count": 83,
                "after_record_count": 83,
                "changed_records": [],
                "staged_transaction_present": False,
                "write_audit_active": True,
                "write_attempts": [],
                "write_audit_error": "",
            },
        },
    )


def test_case_file_loader_preserves_confirmed_intent_markdown(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    confirmed = "# Product Intent Confirmation\n\n## State object\nA review record.\n"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "language archive review",
                        "prompt": "Create a greenfield proposal for language archive review.",
                        "required_terms": ["language", "archive", "review"],
                        "leakage_terms": ["language archive review"],
                        "confirmed_intent_markdown": confirmed,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cases = module.load_case_file(case_file)

    assert len(cases) == 1
    assert cases[0].name == "language archive review"
    assert cases[0].required_terms == ("language", "archive", "review")
    assert cases[0].leakage_terms == ("language archive review",)
    assert cases[0].confirmed_intent_markdown == confirmed.strip()


def test_case_file_loader_canonicalizes_adjacent_duplicate_source_words(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    confirmed = "# Product Intent Confirmation\n\n## Proof boundary\nMission evidence evidence remains reviewable.\n"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "mission evidence review",
                        "prompt": (
                            "Create a greenfield proposal for mission evidence evidence review that preserves "
                            "coverage cell and mission evidence evidence."
                        ),
                        "required_terms": ["mission evidence evidence", "coverage cell"],
                        "leakage_terms": ["mission evidence evidence review"],
                        "confirmed_intent_markdown": confirmed,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    case = module.load_case_file(case_file)[0]

    assert "mission evidence evidence" not in case.prompt.casefold()
    assert case.required_terms == ("mission evidence", "coverage cell")
    assert case.leakage_terms == ("mission evidence review",)
    assert "Mission evidence remains reviewable." in case.confirmed_intent_markdown
    assert "evidence evidence" not in case.confirmed_intent_markdown.casefold()


def test_main_uses_external_case_files_instead_of_default_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    case_file = tmp_path / "fresh-cases.json"
    case_file.write_text(
        json.dumps(
            [
                {
                    "name": "museum conservation queue",
                    "prompt": "Create a greenfield proposal for museum conservation queue review.",
                    "required_terms": ["museum", "conservation", "queue"],
                    "leakage_terms": ["museum conservation queue"],
                }
            ]
        ),
        encoding="utf-8",
    )
    matrix_kwargs: dict[str, object] = {}

    def fake_run_matrix(**kwargs):
        matrix_kwargs.update(kwargs)
        return (_passing_matrix_result(module),)

    monkeypatch.setattr(module, "run_matrix", fake_run_matrix)

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--case-file",
            str(case_file),
            "--proof-tier",
            "discovery",
            "--include-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "discovery-passed"
    assert payload["proof_scope"]["timing_tiers"] == "advisory_profile_targets_with_separate_operational_timeout"
    assert payload["proof_scope"]["confirmation"] == "explicit_terminal_decision_and_same_hash_retry"
    assert payload["proof_scope"]["native_chat"] == "unqualified_read_only"
    assert payload["proof_scope"]["native_hook_visibility"] == "not_proven_by_this_matrix"
    assert payload["temp_cleanup_proof"]["status"] == "passed"
    cases = matrix_kwargs["cases"]
    assert len(cases) == 1
    assert cases[0].name == "museum conservation queue"
    assert cases[0].leakage_terms == ("museum conservation queue",)


def test_include_default_cases_preserves_native_assignments_before_appending_supplement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    standard = module.model_profile_id_for_repair_tier("standard")
    case_file = _write_supplement(
        tmp_path / "supplement.json",
        case_id="supplemental-museum-clarification",
        tags=(f"model-profile:{standard}",),
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(module, "_execute_matrix_campaign", lambda **kwargs: captured.update(kwargs) or 0)

    assert module.main(
        [
            "--dist-dir", str(tmp_path / "dist"), "--temp-parent", str(tmp_path),
            "--case-file", str(case_file), "--include-default-cases",
        ]
    ) == 0

    native = module.assign_model_profiles(module.default_cases())
    selected = tuple(captured["selected_cases"])
    assert selected[: len(native)] == native
    assert module.assign_model_profiles(selected) == selected
    assert tuple(captured["planned_cases"]) == selected
    assert module.case_model_profile(selected[-1]) == standard


def test_lower_capability_control_is_separate_and_profile_bound(
    tmp_path: Path,
) -> None:
    module = _module()
    case_file = _write_supplement(
        tmp_path / "luna-control.json",
        case_id="supplemental-luna-control",
        tags=(),
        expectation="clarification_required",
    )

    control = module._load_lower_capability_control_case(str(case_file))  # noqa: SLF001

    assert control is not None
    assert module.case_expectation(control) == "clarification_required"
    assert module.case_model_profile(control) == module.LOWER_CAPABILITY_CONTROL_PROFILES[0]


def test_lower_capability_control_rejects_commit_expectation(tmp_path: Path) -> None:
    module = _module()
    case_file = _write_supplement(
        tmp_path / "invalid-control.json",
        case_id="invalid-luna-control",
        tags=(),
    )

    with pytest.raises(RuntimeError, match="must require clarification"):
        module._load_lower_capability_control_case(str(case_file))  # noqa: SLF001


def test_lower_capability_control_rejects_non_luna_profile_tag(tmp_path: Path) -> None:
    module = _module()
    case_file = _write_supplement(
        tmp_path / "invalid-profile-control.json",
        case_id="invalid-profile-control",
        tags=(f"model-profile:{module.model_profile_id_for_repair_tier('standard')}",),
        expectation="clarification_required",
    )

    with pytest.raises(RuntimeError, match="only the Luna control profile"):
        module._load_lower_capability_control_case(str(case_file))  # noqa: SLF001


def test_host_argv_template_resolves_exact_profile_tokens_and_rejects_missing_tokens() -> None:
    module = _module()
    template = (
        "codex", "exec", "--model", "{model}", "--config",
        "{reasoning_effort}", "-",
    )
    with pytest.raises(RuntimeError, match="reasoning_effort"):
        module._require_profile_argv_template(template)  # noqa: SLF001
    exact_template = (
        "codex", "exec", "--ephemeral", "--ignore-user-config",
        "--skip-git-repo-check", "--sandbox", "read-only",
        "--model", "{model}", "--config",
        "model_reasoning_effort={reasoning_effort}", "--output-schema",
        "{candidate_schema}", "-",
    )
    module._require_profile_argv_template(exact_template)  # noqa: SLF001
    resolved = module._host_candidate_argv_for_profile(  # noqa: SLF001
        exact_template,
        profile_id=module.LOWER_CAPABILITY_CONTROL_PROFILES[0],
    )
    assert resolved[8] == "gpt-5.6-luna"
    assert resolved[10] == "model_reasoning_effort=medium"


def test_luna_host_control_uses_standard_product_compiler_route(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    _write(repo_root / ".odylith/bin/odylith", "")
    profile_id = module.LOWER_CAPABILITY_CONTROL_PROFILES[0]
    host_argv = (
        "codex", "exec", "--ephemeral", "--ignore-user-config",
        "--skip-git-repo-check", "--sandbox", "read-only",
        "--model", "gpt-5.6-luna", "--config",
        "model_reasoning_effort=medium", "--output-schema",
        "{candidate_schema}", "-",
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(module, "_local_release_env", lambda **_kwargs: {})
    monkeypatch.setattr(
        module,
        "_run_expected_clarification_case",
        lambda **kwargs: captured.update(kwargs) or _passing_matrix_result(module),
    )

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            case_id="supplemental-luna-control",
            name="supplemental Luna control",
            prompt="Ask one source-bound question before proceeding.",
            required_terms=(),
            expectation="clarification_required",
            tags=(f"model-profile:{profile_id}",),
        ),
        repo_root=repo_root,
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1",
        version="0.0.0",
        skip_install=True,
        host_candidate_argv=host_argv,
    )

    assert result.status == "passed"
    assert captured["repair_tier"] == "standard"
    assert captured["host_candidate_argv"] == host_argv
    assert captured["env"]["ODYLITH_GREENFIELD_MODEL_PROFILE"] == profile_id


@pytest.mark.parametrize("failure_mode", ("malformed_argv", "post_claim_validation"))
def test_release_preflight_and_protected_input_claim_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_mode: str,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/bin/sh\nexit 0\n")
    args = module.argparse.Namespace(
        include_default_cases=False,
        evidence_output_dir=str(tmp_path / "evidence"),
        release_audit_repo_root="",
        required_stressor=(),
        require_high_variance_stressors=False,
        campaign_phase="gate",
        proof_tier="release",
        telemetry_jsonl="",
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        sealed_release_input_root=str(tmp_path / "sealed"),
        install_mode="full",
        include_browser_proof=False,
        include_commit_recovery_proof=False,
        allow_skipped_browser_proof=False,
        allow_partial_stressor_coverage=False,
        semantic_annotations_file=str(tmp_path / "sealed/annotations.json"),
        evaluation_split_manifest=str(tmp_path / "sealed/splits.json"),
        final_holdout_run_ledger=str(tmp_path / "run-ledger.json"),
        implementation_revision="a" * 40,
        distribution_provenance_file=str(tmp_path / "sealed/provenance.json"),
        case_file=(str(tmp_path / "sealed/cases.json"),),
        release_audit_file="",
        temp_parent=str(tmp_path / "work"),
        dist_dir=str(dist_dir),
        output_json=str(tmp_path / "result.json"),
        host_candidate_arg=["codex", "exec"],
        lower_capability_control_file=str(tmp_path / "sealed/luna-control.json"),
    )

    factory_calls: list[bool] = []
    monkeypatch.setattr(module, "_parse_args", lambda _argv: args)
    monkeypatch.setattr(module, "_require_sealed_release_input_root", lambda **_kwargs: None)
    monkeypatch.setattr(module, "_raise_for_invalid_campaign_policy", lambda **_kwargs: None)
    monkeypatch.setattr(module, "validate_retained_evidence_output_dir", lambda **_kwargs: None)
    monkeypatch.setattr(module, "browser_runtime_preflight_issues", lambda: ())
    if failure_mode == "malformed_argv":
        class HoldoutRun:
            claimed = False

            def claim(self) -> None:
                self.claimed = True

        holdout = HoldoutRun()
        monkeypatch.setattr(
            module,
            "_final_holdout_run_from_args",
            lambda *_args, **_kwargs: factory_calls.append(True) or holdout,
        )
        monkeypatch.setattr(
            module,
            "acquire_matrix_run_lease",
            lambda **_kwargs: pytest.fail("lease acquired before release preflight finished"),
        )
        monkeypatch.setattr(
            module,
            "_require_profile_argv_template",
            lambda _argv: (_ for _ in ()).throw(RuntimeError("malformed host argv")),
        )
        with pytest.raises(RuntimeError, match="malformed host argv"):
            module.main([])

        assert holdout.claimed is False
        assert factory_calls == []
        return

    standard_profile = module.model_profile_id_for_repair_tier("standard")
    control_profile = module.LOWER_CAPABILITY_CONTROL_PROFILES[0]
    _write_supplement(
        Path(args.case_file[0]),
        case_id="release-main-case",
        tags=(f"model-profile:{standard_profile}",),
    )
    _write_supplement(
        Path(args.lower_capability_control_file),
        case_id="release-control-case",
        tags=(f"model-profile:{control_profile}",),
        expectation="clarification_required",
    )
    _write(Path(args.semantic_annotations_file), "{}\n")
    _write(Path(args.evaluation_split_manifest), "{}\n")
    holdout = module._FinalHoldoutRun(
        ledger_path=Path(args.final_holdout_run_ledger),
        holdout_path=Path(args.semantic_annotations_file),
        evaluation_manifest_path=Path(args.evaluation_split_manifest),
        case_paths=tuple(Path(value) for value in args.case_file),
        lower_capability_control_path=Path(args.lower_capability_control_file),
        implementation_revision="a" * 40,
        distribution_provenance_sha256="b" * 64,
    )
    monkeypatch.setattr(
        module,
        "_final_holdout_run_from_args",
        lambda *_args, **_kwargs: factory_calls.append(True) or holdout,
    )
    monkeypatch.setattr(
        module,
        "_require_profile_argv_template",
        lambda _argv: ("/trusted/codex", "exec"),
    )
    events: list[str] = []
    load_cases = module._load_cli_case_files
    load_control = module._load_lower_capability_control_case

    def assert_claimed(event: str) -> None:
        claim = json.loads(holdout.ledger_path.read_text(encoding="utf-8"))
        assert holdout.claimed is True
        assert claim["status"] == "claimed"
        assert claim["protected_inputs_bound"] is True
        events.append(event)

    def load_claimed_cases(*loader_args, **loader_kwargs):
        assert_claimed("cases")
        return load_cases(*loader_args, **loader_kwargs)

    def load_claimed_control(*loader_args, **loader_kwargs):
        assert_claimed("control")
        return load_control(*loader_args, **loader_kwargs)

    def reject_after_protected_loads(**_kwargs):
        assert_claimed("evaluation")
        raise RuntimeError("post-claim contract validation failed")

    monkeypatch.setattr(module, "_load_cli_case_files", load_claimed_cases)
    monkeypatch.setattr(module, "_load_lower_capability_control_case", load_claimed_control)
    monkeypatch.setattr(module, "evaluate_frozen_evaluation_contract", reject_after_protected_loads)
    monkeypatch.setattr(
        module,
        "_execute_matrix_campaign",
        lambda **_kwargs: pytest.fail("matrix executed after failed release validation"),
    )

    with pytest.raises(RuntimeError, match="post-claim contract validation failed"):
        module.main([])

    terminal = json.loads(holdout.ledger_path.read_text(encoding="utf-8"))
    assert factory_calls == [True]
    assert events == ["cases", "control", "evaluation"]
    assert terminal["status"] == "interrupted"
    assert terminal["protected_inputs_bound"] is True
    assert holdout.claimed is False


@pytest.mark.parametrize("case_args", ((), ("--case-file", "")))
def test_include_default_cases_requires_a_nonempty_case_file_before_acquiring_a_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_args: tuple[str, ...],
) -> None:
    module = _module()
    monkeypatch.setattr(module, "acquire_matrix_run_lease", lambda **_kwargs: pytest.fail("lease acquired"))

    with pytest.raises(RuntimeError, match="at least one --case-file is required"):
        module.main(["--dist-dir", str(tmp_path / "dist"), "--include-default-cases", *case_args])


@pytest.mark.parametrize(
    "profile_mode",
    ("absent", "unknown", "multiple"),
)
def test_include_default_cases_requires_one_supported_explicit_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    profile_mode: str,
) -> None:
    module = _module()
    profiles = (
        module.model_profile_id_for_repair_tier("standard"),
        module.LOWER_CAPABILITY_CONTROL_PROFILES[0],
    )
    tags = {
        "absent": (),
        "unknown": ("model-profile:unknown",),
        "multiple": tuple(f"model-profile:{profile}" for profile in profiles[:2]),
    }[profile_mode]
    case_file = _write_supplement(tmp_path / "supplement.json", case_id="supplement", tags=tags)
    monkeypatch.setattr(module, "_execute_matrix_campaign", lambda **_kwargs: pytest.fail("executed"))

    with pytest.raises(RuntimeError, match="exactly one supported explicit model profile"):
        module.main(
            [
                "--dist-dir", str(tmp_path / "dist"), "--temp-parent", str(tmp_path),
                "--case-file", str(case_file), "--include-default-cases",
            ]
        )


@pytest.mark.parametrize(
    "case_ids",
    (("FLOOD-SHELTER-INTAKE",), ("supplement-duplicate", "SUPPLEMENT-DUPLICATE")),
)
def test_include_default_cases_rejects_normalized_duplicate_ids_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_ids: tuple[str, ...],
) -> None:
    module = _module()
    profile = module.model_profile_id_for_repair_tier("standard")
    paths = tuple(
        _write_supplement(
            tmp_path / f"supplement-{index}.json",
            case_id=case_id,
            tags=(f"model-profile:{profile}",),
        )
        for index, case_id in enumerate(case_ids)
    )
    monkeypatch.setattr(module, "_execute_matrix_campaign", lambda **_kwargs: pytest.fail("executed"))
    arguments = ["--dist-dir", str(tmp_path / "dist"), "--temp-parent", str(tmp_path)]
    for path in paths:
        arguments.extend(("--case-file", str(path)))

    with pytest.raises(RuntimeError, match="duplicate case IDs"):
        module.main([*arguments, "--include-default-cases"])


def test_include_default_cases_keeps_strict_lexical_controls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    profile = module.model_profile_id_for_repair_tier("standard")
    case_file = _write_supplement(
        tmp_path / "supplement.json",
        case_id="supplement",
        tags=(f"model-profile:{profile}",),
        include_leakage=False,
    )
    monkeypatch.setattr(module, "_execute_matrix_campaign", lambda **_kwargs: pytest.fail("executed"))

    with pytest.raises(RuntimeError, match="must define leakage_terms"):
        module.main(
            [
                "--dist-dir", str(tmp_path / "dist"), "--temp-parent", str(tmp_path),
                "--case-file", str(case_file), "--include-default-cases",
            ]
        )


@pytest.mark.parametrize(
    "protected_args",
    (
        ("--proof-tier", "release"),
        ("--release-audit-file", "audit.json"),
        ("--release-audit-repo-root", "sealed"),
        ("--sealed-release-input-root", "sealed"),
        ("--semantic-annotations-file", "annotations.json"),
        ("--evaluation-split-manifest", "splits.json"),
        ("--final-holdout-run-ledger", "ledger.json"),
        ("--implementation-revision", "a" * 40),
        ("--distribution-provenance-file", "provenance.json"),
    ),
)
def test_include_default_cases_rejects_release_inputs_before_lease_or_claim(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    protected_args: tuple[str, str],
) -> None:
    module = _module()
    monkeypatch.setattr(module, "acquire_matrix_run_lease", lambda **_kwargs: pytest.fail("lease acquired"))

    with pytest.raises(RuntimeError, match="invalid --include-default-cases policy"):
        module.main(
            [
                "--dist-dir", str(tmp_path / "dist"), "--case-file", str(tmp_path / "unused.json"),
                "--include-default-cases", *protected_args,
            ]
        )


def test_case_file_rejects_missing_leakage_terms_before_simulation(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "weak case",
                        "prompt": "Create a greenfield proposal for weak case review.",
                        "required_terms": ["weak", "case"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="must define leakage_terms"):
        module.main(
            [
                "--dist-dir",
                str(dist_dir),
                "--version",
                "0.1.15",
                "--temp-parent",
                str(tmp_path),
                "--case-file",
                str(case_file),
            ]
        )

    assert not any(path.name.startswith("odylith-greenfield-matrix-") for path in tmp_path.iterdir())


def test_main_ignores_a_concurrent_sibling_run_when_checking_owned_cleanup(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    sibling = tmp_path / "odylith-greenfield-matrix-active-sibling"
    sibling.mkdir()
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))

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
            "--include-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "discovery-passed"
    assert payload["temp_cleanup_proof"]["status"] == "passed"
    assert sibling.is_dir()
    assert not Path(payload["proof_run"]["temporary_namespace"]).exists()


def test_main_marks_the_proof_failed_when_final_namespace_cleanup_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    namespace = tmp_path / "owned-proof-run"
    namespace.mkdir()

    class FailingLease:
        temp_namespace = namespace
        released = False

        def to_dict(self) -> dict[str, str]:
            return {"temporary_namespace": str(namespace)}

        def release(self) -> None:
            self.released = True
            raise RuntimeError("forced final namespace cleanup failure")

    monkeypatch.setattr(module, "acquire_matrix_run_lease", lambda **_kwargs: FailingLease())
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))

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
            "--include-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["temp_cleanup_proof"]["status"] == "failed"
    assert payload["temp_cleanup_proof"]["run_namespace_cleanup"] == "failed"
    assert "forced final namespace cleanup failure" in payload["temp_cleanup_proof"]["run_namespace_cleanup_error"]


def test_main_fails_when_owned_temp_cleanup_finds_a_leftover_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")

    def fake_run_matrix(**kwargs):
        snapshot = kwargs["temp_parent"] / "odylith-greenfield-matrix-leftover" / "snapshot"
        snapshot.parent.mkdir()
        snapshot.write_text("required recovery evidence", encoding="utf-8")
        return (_passing_matrix_result(module),)

    monkeypatch.setattr(module, "run_matrix", fake_run_matrix)

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
            "--include-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["temp_cleanup_proof"]["status"] == "failed"
    assert payload["temp_cleanup_proof"]["remaining_paths"]
    namespace = Path(payload["proof_run"]["temporary_namespace"])
    assert (namespace / "odylith-greenfield-matrix-leftover" / "snapshot").read_text(
        encoding="utf-8"
    ) == "required recovery evidence"
    assert payload["temp_cleanup_proof"]["run_namespace_cleanup"] == "failed"


def test_main_fails_when_installed_commit_recovery_proof_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))
    monkeypatch.setattr(
        module,
        "run_installed_commit_recovery_proof",
        lambda **_kwargs: module.GreenfieldInstalledCommitRecoveryProof(
            status="failed",
            issues=("installed recovery failed",),
        ),
    )

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path / "fixtures"),
            "--evidence-output-dir",
            str(tmp_path / "evidence"),
            "--include-commit-recovery-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["proof_scope"]["commit_recovery_path"] == module.COMMIT_RECOVERY_PROOF_SCOPE
    assert payload["commit_recovery_proof"]["issues"] == ["installed recovery failed"]


def test_primary_candidate_failure_makes_no_secondary_host_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _module()
    release_case = module.GreenfieldMatrixCase(
        name="audited public case",
        prompt="Create an audited public release case.",
        required_terms=("audited",),
        case_id="audited-public-case",
    )
    lower_control = module.GreenfieldMatrixCase(
        name="lower control",
        prompt="Clarify the missing tenant boundary.",
        required_terms=("tenant",),
        case_id="lower-control",
        tags=(f"model-profile:{module.LOWER_CAPABILITY_CONTROL_PROFILES[0]}",),
        expectation=module.CLARIFICATION_REQUIRED_EXPECTATION,
    )
    failed = module.GreenfieldMatrixResult(
        name=release_case.name,
        status="failed",
        proposal_seconds=1.0,
        create_seconds=0.0,
        counts=_full_counts(module),
        quality=module.GreenfieldQualityVerdict(
            passed=False,
            issues=("candidate authoring failed before proposal admission",),
            lenses={},
            scores={},
            score=0,
            score_explanation=("primary authoring failed",),
        ),
        failure_detail="candidate authoring failed before proposal admission",
        evidence={"case": {"id": release_case.case_id}},
    )
    calls: list[str] = []

    def primary_only(**_kwargs):
        calls.append("primary")
        return (failed,)

    def unexpected_secondary(**_kwargs):
        calls.append("secondary")
        raise AssertionError("a failed primary must not make another host/model call")

    monkeypatch.setattr(module, "run_matrix", primary_only)
    monkeypatch.setattr(module, "select_recovery_case", lambda *_args, **_kwargs: release_case)
    monkeypatch.setattr(module, "run_installed_commit_recovery_proof", unexpected_secondary)
    monkeypatch.setattr(module, "run_unavailable_provider_proof", unexpected_secondary)
    monkeypatch.setattr(
        module,
        "retained_evidence_result",
        lambda *_args, **_kwargs: {"status": "failed", "issues": ["primary failed"]},
    )
    args = module.argparse.Namespace(
        dist_dir=str(tmp_path / "dist"),
        version="0.1.15",
        include_browser_proof=True,
        install_mode="full",
        attempt_ledger_jsonl="",
        allow_partial_stressor_coverage=False,
        semantic_annotations_file="",
        evaluation_split_manifest="",
        evidence_output_dir=str(tmp_path / "evidence"),
        host_candidate_arg=(),
        include_commit_recovery_proof=True,
        lower_capability_control_file=str(tmp_path / "lower-control.json"),
        json_output=True,
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

    exit_code = module._execute_matrix_campaign(
        args=args,
        selected_cases=(release_case,),
        planned_cases=(release_case,),
        release_audits=(),
        campaign_config=config,
        corpus_provenance={"status": "passed"},
        output_path=None,
        lease=lease,
        lower_capability_control_case=lower_control,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert calls == ["primary"]
    assert payload["commit_recovery_proof"]["status"] == "not-run"
    assert "candidate authoring failed" in payload["commit_recovery_proof"]["issues"][0]
    assert payload["lower_capability_control_proof"]["status"] == "failed"
    assert payload["unavailable_provider_proof"]["status"] == "not-run"


def test_audited_public_release_reaches_execution_without_holdout_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    public_case = module.GreenfieldMatrixCase(
        name="public qualification",
        prompt="Create a public audited qualification case.",
        required_terms=("public",),
        case_id="public-qualification",
    )
    args = module.argparse.Namespace(
        include_default_cases=False,
        evidence_output_dir=str(tmp_path / "evidence"),
        release_audit_repo_root=str(tmp_path),
        required_stressor=(),
        require_high_variance_stressors=False,
        campaign_phase="gate",
        proof_tier="release",
        telemetry_jsonl="",
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        sealed_release_input_root="",
        install_mode="full",
        include_browser_proof=True,
        include_commit_recovery_proof=True,
        allow_skipped_browser_proof=False,
        allow_partial_stressor_coverage=False,
        semantic_annotations_file="",
        evaluation_split_manifest="",
        final_holdout_run_ledger="",
        implementation_revision="",
        distribution_provenance_file="",
        case_file=(str(tmp_path / "public-subset.json"),),
        release_parent_case_file=(),
        release_audit_file=str(tmp_path / "public-audit.json"),
        lower_capability_control_file=str(tmp_path / "lower-control.json"),
        host_candidate_arg=("trusted-host", "--profile", "{profile_id}"),
        temp_parent=str(tmp_path / "work"),
        dist_dir=str(tmp_path / "dist"),
        output_json=str(tmp_path / "result.json"),
    )
    reached: dict[str, object] = {}

    class Lease:
        released = False
        temp_namespace = tmp_path / "lease"

        def release(self) -> None:
            self.released = True

    lease = Lease()
    monkeypatch.setattr(module, "_parse_args", lambda _argv: args)
    monkeypatch.setattr(module, "_require_profile_argv_template", lambda argv: argv)
    monkeypatch.setattr(module, "validate_retained_evidence_output_dir", lambda **_kwargs: None)
    monkeypatch.setattr(
        module,
        "_load_planned_cases_and_control",
        lambda **_kwargs: ((public_case,), (public_case,), public_case),
    )
    monkeypatch.setattr(module, "load_release_audit_file", lambda *_args, **_kwargs: (object(),))
    monkeypatch.setattr(
        module,
        "evaluate_release_corpus",
        lambda *_args, **_kwargs: type(
            "Evaluation",
            (),
            {"issues": (), "summary": {"approved_audit_bindings": {}}},
        )(),
    )
    monkeypatch.setattr(module, "acquire_matrix_run_lease", lambda **_kwargs: lease)

    def execute(**kwargs):
        reached.update(kwargs)
        lease.release()
        return 0

    monkeypatch.setattr(module, "_execute_matrix_campaign", execute)

    assert module.main([]) == 0
    assert reached["planned_cases"] == (public_case,)
    assert reached["retained_evidence_run_id"] == ""
    assert not (tmp_path / "run-ledger.json").exists()


def test_main_binds_commit_recovery_to_the_selected_external_case(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    external_case = module.GreenfieldMatrixCase(
        name="external recovery case",
        prompt="Create an externally supplied recovery-bound product.",
        required_terms=("external", "recovery"),
        case_id="release-external-recovery",
        confirmed_intent_markdown="# External Intent\n\n## State\nA durable record.",
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(module, "_load_cli_case_files", lambda _paths, **_kwargs: (external_case,))
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))

    def fake_commit_recovery(**kwargs):
        captured.update(kwargs)
        return module.GreenfieldInstalledCommitRecoveryProof(
            status="passed",
            issues=(),
            recovery_case=module.case_evidence(kwargs["recovery_case"]),
        )

    monkeypatch.setattr(module, "run_installed_commit_recovery_proof", fake_commit_recovery)

    exit_code = module.main(
        [
            "--case-file",
            str(tmp_path / "external-cases.json"),
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path / "fixtures"),
            "--evidence-output-dir",
            str(tmp_path / "evidence"),
            "--proof-tier",
            "discovery",
            "--include-commit-recovery-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert captured["evidence_output_dir"] == tmp_path / "evidence-commit-recovery"
    assert captured["retained_evidence_run_id"] == ""
    assert captured["recovery_case"] is external_case
    assert payload["commit_recovery_proof"]["recovery_case"]["id"] == external_case.case_id
    assert payload["commit_recovery_proof"]["recovery_case"]["confirmed_intent_sha256"]


def test_recovery_case_selection_ignores_clarification_cases_and_rejects_unproven_release_cases() -> None:
    module = _module()
    clarification_case = module.GreenfieldMatrixCase(
        name="clarification case",
        prompt="Clarify this product first.",
        required_terms=("clarify",),
        case_id="a-clarification",
        expectation=module.CLARIFICATION_REQUIRED_EXPECTATION,
    )
    committed_case = module.GreenfieldMatrixCase(
        name="committed case",
        prompt="Create the committed product.",
        required_terms=("committed",),
        case_id="b-committed",
    )

    assert module.select_recovery_case(
        (clarification_case, committed_case),
        proof_tier="discovery",
    ) == committed_case
    with pytest.raises(RuntimeError, match="approved audit binding"):
        module.select_recovery_case((committed_case,), proof_tier="release")
    assert module.select_recovery_case(
        (clarification_case, committed_case),
        proof_tier="release",
        require_release_binding=False,
    ) == committed_case
