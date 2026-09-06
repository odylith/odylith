from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest


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


def _release_audit_binding(case) -> dict[str, str]:  # noqa: ANN001
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


def _clarification_result() -> dict[str, object]:
    return {
        "status": "clarification_required",
        "consistency": {
            "status": "material_ambiguity",
            "evidence_quotes": [],
        },
        "clarification": {"material_dimension": "first_path"},
    }


def _stage_observation(
    profile_id: str,
    *,
    clarification: bool = False,
    reviewed: bool = False,
) -> dict[str, object]:
    from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import GREENFIELD_INTENT_AUTHORING_VERSION
    from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import get_greenfield_model_profile

    profile = get_greenfield_model_profile(profile_id)
    initial = {
        "profile_id": profile_id, "request_role": "initial_authoring",
        "model": profile.model, "reasoning_effort": profile.reasoning_effort,
        "timeout_seconds": profile.model_timeout_seconds - profile.source_review_reserve_seconds,
        "elapsed_seconds": 5.0,
        "provider": {
            "provider": profile.provider, "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
        },
    }
    response_result = _clarification_result() if clarification else {"status": "authored"}
    has_review = not clarification or reviewed
    observation = {
        "version": "odylith.greenfield.model-proof-observation.v2",
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "semantic_model_call_count": 2 if has_review else 1,
        "response": {
            "version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "result": response_result,
        },
        "initial_authoring": initial,
    }
    if has_review:
        observation["initial_response"] = {
            "version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "result": {"status": "authored"},
        }
        observation["source_review"] = {
            "profile_id": profile_id, "request_role": "source_review",
            "model": profile.source_review_model,
            "reasoning_effort": profile.source_review_reasoning_effort,
            "timeout_seconds": profile.model_timeout_seconds - 5.0, "elapsed_seconds": 5.0,
            "provider": {
                "provider": profile.provider, "model": profile.source_review_model,
                "reasoning_effort": profile.source_review_reasoning_effort,
            },
            "response": {
                "result": response_result if clarification else {"corrections": []},
            },
        }
    return observation


def _passing_matrix_result(module, *, manifest_summary: dict[str, object] | None = None) -> object:
    profile_id = module.model_profile_id_for_repair_tier("standard")
    profile = module.get_greenfield_model_profile(profile_id)
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
            "model_profile": {
                "profile_id": profile_id,
                "stage_observation": _stage_observation(profile_id),
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


def _passing_profile_result(module, profile_id: str, proposal_seconds: float) -> object:
    profile = module.get_greenfield_model_profile(profile_id)
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
            "model_profile": {
                "profile_id": profile_id,
                "stage_observation": _stage_observation(profile_id),
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


def _passing_clarification_profile_result(
    module,
    profile_id: str,
    proposal_seconds: float,
    *,
    reviewed: bool = False,
) -> object:
    expected_field = "first_path"
    expected_question = "Who uses this product first, and what complete result do they see?"
    result = _passing_profile_result(module, profile_id, proposal_seconds)
    return replace(
        result,
        name=f"{profile_id}-clarification",
        quality=replace(
            result.quality,
            score_basis="clarification_required_no_write_contract",
        ),
        evidence={
            **dict(result.evidence or {}),
            "model_profile": {
                **result.evidence["model_profile"],
                "stage_observation": _stage_observation(
                    profile_id,
                    clarification=True,
                    reviewed=reviewed,
                ),
            },
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

    def fake_run_matrix(**kwargs):  # noqa: ANN001
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
    assert payload["temp_cleanup_proof"]["status"] == "passed"
    cases = matrix_kwargs["cases"]
    assert len(cases) == 1
    assert cases[0].name == "museum conservation queue"
    assert cases[0].leakage_terms == ("museum conservation queue",)


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

    def fake_run_matrix(**kwargs):  # noqa: ANN001
        (kwargs["temp_parent"] / "odylith-greenfield-matrix-leftover").mkdir()
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
    assert not Path(payload["proof_run"]["temporary_namespace"]).exists()


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
            str(tmp_path),
            "--include-commit-recovery-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["proof_scope"]["commit_recovery_path"] == module.COMMIT_RECOVERY_PROOF_SCOPE
    assert payload["commit_recovery_proof"]["issues"] == ["installed recovery failed"]


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

    def fake_commit_recovery(**kwargs):  # noqa: ANN001
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
            str(tmp_path),
            "--proof-tier",
            "discovery",
            "--include-commit-recovery-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
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

    def fake_commit_recovery(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return module.GreenfieldInstalledCommitRecoveryProof(
            status="passed",
            issues=(),
            recovery_case={"binding_scope": "release-confirmed-intent-v1"},
        )

    monkeypatch.setattr(module, "run_installed_commit_recovery_proof", fake_commit_recovery)

    exit_code = module._execute_matrix_campaign(  # noqa: SLF001
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

    def fake_commit_recovery(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return module.GreenfieldInstalledCommitRecoveryProof(
            status="passed",
            issues=(),
            recovery_case={"binding_scope": "campaign-case-v1"},
        )

    monkeypatch.setattr(module, "run_installed_commit_recovery_proof", fake_commit_recovery)

    exit_code = module._execute_matrix_campaign(  # noqa: SLF001
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

    exit_code = module._execute_matrix_campaign(  # noqa: SLF001
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
        module._final_holdout_run_from_args(args, sealed_input_root=str(sealed_root))  # noqa: SLF001
    assert not ledger.exists()

    args.implementation_revision = "a" * 40
    holdout_run = module._final_holdout_run_from_args(args, sealed_input_root=str(sealed_root))  # noqa: SLF001

    assert holdout_run is not None
    assert holdout_run.implementation_revision == "a" * 40
    assert not ledger.exists()


def test_temp_cleanup_proof_finds_leftover_files_and_symlinks(tmp_path: Path) -> None:
    module = _module()
    leftover_file = tmp_path / "odylith-greenfield-matrix-leftover-file"
    leftover_file.write_text("stale temp payload", encoding="utf-8")
    leftover_target = tmp_path / "target"
    leftover_target.mkdir()
    leftover_link = tmp_path / "odylith-greenfield-unavailable-leftover-link"
    leftover_link.symlink_to(leftover_target, target_is_directory=True)

    proof = module.temp_cleanup_proof(tmp_path)

    assert proof["status"] == "failed"
    assert str(leftover_file) in proof["remaining_paths"]
    assert str(leftover_link) in proof["remaining_paths"]


def test_temp_cleanup_proof_finds_installed_recovery_leftovers(tmp_path: Path) -> None:
    module = _module()
    leftover = tmp_path / "odylith-greenfield-commit-recovery-leftover"
    leftover.mkdir()

    proof = module.temp_cleanup_proof(tmp_path)

    assert proof["status"] == "failed"
    assert str(leftover) in proof["remaining_paths"]


def test_temp_cleanup_proof_finds_unavailable_provider_leftovers(tmp_path: Path) -> None:
    module = _module()
    leftover = tmp_path / "odylith-greenfield-unavailable-leftover"
    leftover.mkdir()

    proof = module.temp_cleanup_proof(tmp_path)

    assert proof["status"] == "failed"
    assert str(leftover) in proof["remaining_paths"]


def test_model_profile_release_proof_requires_all_tiers_under_strict_budgets() -> None:
    module = _module()
    results = tuple(
        _passing_profile_result(module, profile_id, elapsed)
        for profile_id, elapsed in zip(
            tuple(module.model_profile_id_for_repair_tier(tier) for tier in ("standard", "rescue", "deep")),
            (59.9, 89.9, 119.9),
            strict=True,
        )
    )

    positives_only = module.model_profile_release_proof(results, require_complete=True)
    assert positives_only["status"] == "failed"
    assert positives_only["lower_capability_scope"]["status"] == "unproven"
    assert any("clarification/no-write control" in issue for issue in positives_only["issues"])

    lower_profile_id = module.model_profile_id_for_repair_tier("standard")
    clarifications = tuple(
        _passing_clarification_profile_result(module, module.model_profile_id_for_repair_tier(tier), 20.0)
        for tier in ("standard", "rescue")
    )
    complete_results = (*results, *clarifications)
    proof = module.model_profile_release_proof(complete_results, require_complete=True)
    assert proof["status"] == "passed"
    assert proof["profiles"][lower_profile_id]["lower_capability"] is True
    assert proof["profiles"][lower_profile_id]["committed_positive_case_count"] == 1
    assert proof["profiles"][lower_profile_id]["clarification_no_write_control_count"] == 1
    assert proof["lower_capability_scope"]["status"] == "passed"
    assert len(proof["lower_capability_scope"]["observed_profiles"]) == 2
    assert proof["lower_capability_scope"]["observed_profiles"][0]["model"] == "gpt-5.6-terra"
    assert module.model_profile_release_proof(
        (*results[:-1], *clarifications),
        require_complete=True,
    )["status"] == "failed"
    breached = replace(
        results[0],
        proposal_seconds=module.get_greenfield_model_profile(
            module.model_profile_id_for_repair_tier("standard")
        ).consumer_budget_seconds,
    )
    assert module.model_profile_release_proof(
        (breached, *results[1:], *clarifications),
        require_complete=True,
    )["status"] == "failed"


def test_model_profile_release_proof_accepts_review_demoted_clarification() -> None:
    module = _module()
    profile_id = module.model_profile_id_for_repair_tier("standard")
    results = (
        _passing_profile_result(module, profile_id, 20.0),
        _passing_clarification_profile_result(
            module,
            profile_id,
            20.0,
            reviewed=True,
        ),
    )

    proof = module.model_profile_release_proof(results, require_complete=False)

    assert proof["status"] == "passed"
    assert proof["profiles"][profile_id]["committed_positive_case_count"] == 1
    assert proof["profiles"][profile_id]["clarification_no_write_control_count"] == 1


def test_model_profile_release_proof_reports_missing_lower_profile_as_unproven() -> None:
    module = _module()
    results = tuple(
        _passing_profile_result(
            module,
            module.model_profile_id_for_repair_tier(tier),
            20.0,
        )
        for tier in ("deep",)
    )

    proof = module.model_profile_release_proof(results, require_complete=False)

    assert proof["status"] == "passed"
    assert proof["coverage_status"] == "incomplete"
    assert proof["lower_capability_scope"] == {
        "status": "unproven",
        "observed_profiles": [],
        "role": "initial_authoring",
        "requirement": "installed_committed_positive_and_source_bound_clarification_no_write",
    }
    assert module.model_profile_release_proof(results, require_complete=True)["status"] == "failed"


@pytest.mark.parametrize("mutation", ["missing", "review_model", "review_timeout", "outcome"])
def test_model_profile_aggregate_rechecks_private_roles_despite_passed_label(mutation: str) -> None:
    module = _module()
    profile_id = module.model_profile_id_for_repair_tier("standard")
    result = _passing_profile_result(module, profile_id, 20.0)
    evidence = dict(result.evidence)
    profile_evidence = dict(evidence["model_profile"])
    stages = _stage_observation(profile_id)
    if mutation == "missing":
        stages = {}
    elif mutation == "review_model":
        stages["source_review"]["provider"]["model"] = "gpt-5.6-terra"
    elif mutation == "review_timeout":
        stages["source_review"]["timeout_seconds"] = 55.0
    else:
        stages = _stage_observation(profile_id, clarification=True)
    profile_evidence["stage_observation"] = stages
    evidence["model_profile"] = profile_evidence

    proof = module.model_profile_release_proof(
        (replace(result, evidence=evidence),), require_complete=False,
    )

    assert profile_evidence["status"] == "passed"
    assert proof["status"] == "failed"
    assert proof["profiles"][profile_id]["committed_positive_case_count"] == 0


def test_model_profile_release_proof_ignores_forged_lower_metadata_and_missing_provider() -> None:
    module = _module()
    deep_id = module.model_profile_id_for_repair_tier("deep")
    forged = _passing_profile_result(module, deep_id, 20.0)
    evidence = dict(forged.evidence or {})
    evidence["model_profile"] = {**evidence["model_profile"], "lower_capability": True}

    forged_proof = module.model_profile_release_proof(
        (replace(forged, evidence=evidence),),
        require_complete=False,
    )
    assert forged_proof["status"] == "passed"
    assert forged_proof["coverage_status"] == "incomplete"
    assert forged_proof["lower_capability_scope"]["observed_profiles"] == []

    unavailable = replace(
        forged,
        evidence={
            **dict(forged.evidence or {}),
            "model_profile": {
                **dict(forged.evidence["model_profile"]),
                "profile_id": module.UNAVAILABLE_PROVIDER_PROFILE,
                "observed": {
                    **dict(forged.evidence["model_profile"]["observed"]),
                    "profile_id": module.UNAVAILABLE_PROVIDER_PROFILE,
                },
            },
        },
    )
    unavailable_proof = module.model_profile_release_proof(
        (unavailable,),
        require_complete=False,
    )
    assert unavailable_proof["status"] == "failed"
    assert unavailable_proof["lower_capability_scope"]["observed_profiles"] == []


def test_model_profile_release_proof_rejects_unbound_or_writeful_lower_control() -> None:
    module = _module()
    standard_id = module.model_profile_id_for_repair_tier("standard")
    positive = _passing_profile_result(module, standard_id, 20.0)
    control = _passing_clarification_profile_result(module, standard_id, 20.0)
    evidence = dict(control.evidence or {})
    evidence["case"] = {**evidence["case"], "prompt_sha256": "not-source-bound"}
    evidence["no_write"] = {**evidence["no_write"], "write_attempts": ["open"]}

    proof = module.model_profile_release_proof(
        (positive, replace(control, evidence=evidence)),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert proof["lower_capability_scope"]["status"] == "unproven"
    assert any("source-bound no-write proof" in issue for issue in proof["issues"])


def test_model_profile_release_proof_rejects_elapsed_tier_relabeling() -> None:
    module = _module()
    rescue_id = module.model_profile_id_for_repair_tier("rescue")
    result = _passing_profile_result(module, rescue_id, 30.0)
    evidence = dict(result.evidence or {})
    profile_evidence = dict(evidence["model_profile"])
    profile_evidence["observed"] = {**profile_evidence["observed"], "authoring_tier": "standard"}
    evidence["model_profile"] = profile_evidence

    proof = module.model_profile_release_proof(
        (replace(result, evidence=evidence),),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert any("authoring tier" in issue for issue in proof["issues"])


def test_model_profile_release_proof_requires_a_passed_terminal_result() -> None:
    module = _module()
    result = _passing_profile_result(
        module,
        module.model_profile_id_for_repair_tier("standard"),
        18.0,
    )

    proof = module.model_profile_release_proof(
        (replace(result, status="failed"),),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert any("terminal matrix result" in issue for issue in proof["issues"])


def test_unavailable_provider_proof_requires_fast_no_write_failure() -> None:
    module = _module()
    values = {
        "returncode": 1,
        "proposal_seconds": 1.0,
        "detail": "Greenfield model authoring is unavailable; no records were created.",
        "write_audit_active": True,
        "write_audit_error": "",
        "write_attempts": (),
        "subprocess_attempts": ("subprocess.Popen",),
        "changed_records": (),
        "staged_transaction_present": False,
    }

    assert module.unavailable_provider_proof_issues(**values) == ()
    assert module.unavailable_provider_proof_issues(**{**values, "returncode": 0})
    assert module.unavailable_provider_proof_issues(**{**values, "write_attempts": ("open",)})


def test_commit_manifest_summary_uses_last_repair_patchset_for_clean_final_pass() -> None:
    module = _module()

    summary = module.commit_manifest_summary(
        {
            "status": "passed",
            "validation_status": "passed",
            "requested_repair_tier": "auto",
            "repair_tier": "rescue",
            "rescue_activated": True,
            "passes": 2,
            "issue_count": 0,
            "repaired_issue_codes": ["semantic_alignment"],
            "create_elapsed_seconds": 0.125,
            "write_transaction": {
                "status": "committed",
                "commit_only": True,
                "prewrite_clean_before_commit": True,
                "rollback_guard": "enabled",
                "product_create_transaction_hash": "a" * 64,
                "product_facts_sha256": "c" * 64,
                "repository_write_set_hash": "b" * 64,
            },
            "product_create_transaction": {
                "transaction_hash": "a" * 64,
                "product_facts_sha256": "c" * 64,
                "repository_write_set_hash": "b" * 64,
            },
            "patchset_request": {
                "status": "no_repairable_operations",
                "operation_count": 0,
                "operations": [],
            },
            "last_repair_patchset_request": {
                "status": "repairable",
                "operation_count": 1,
                "operations": [
                    {
                        "operation_id": "GF-PATCH-001",
                        "target_layer": "semantic_model",
                        "replacement_fact": {"external_systems": ["accepted source"]},
                    }
                ],
                "tribunal_patch_plan": {
                    "status": "planned",
                    "operation_count": 1,
                    "provider": {"provider": "codex-cli", "last_failure_code": ""},
                },
                "structured_patch_fallback": {
                    "status": "applied",
                    "source": "source_anchored_semantic_fact",
                    "operation_count": 1,
                    "provider_failure": {"provider": "codex-cli", "code": "timeout"},
                },
            },
        }
    )

    assert summary["patchset_summary_source"] == "last_repair_patchset_request"
    assert summary["patchset_status"] == "repairable"
    assert summary["patchset_operation_count"] == 1
    assert summary["tribunal_patch_plan_status"] == "planned"
    assert summary["tribunal_patch_plan_operation_count"] == 1
    assert summary["tribunal_patch_plan_provider"] == "codex-cli"
    assert summary["structured_patch_fallback_status"] == "applied"
    assert summary["structured_patch_fallback_source"] == "source_anchored_semantic_fact"
    assert summary["structured_patch_fallback_operation_count"] == 1
    assert summary["structured_patch_fallback_provider"] == "codex-cli"
    assert summary["structured_patch_fallback_provider_failure_code"] == "timeout"
    assert summary["create_elapsed_seconds"] == 0.125
    assert summary["write_transaction"] == {
        "status": "committed",
        "commit_only": True,
        "prewrite_clean_before_commit": True,
        "rollback_guard": "enabled",
        "product_create_transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }
    assert summary["product_create_transaction"] == {
        "transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }


def test_commit_manifest_summary_does_not_invent_missing_elapsed_time() -> None:
    module = _module()

    summary = module.commit_manifest_summary({"status": "passed"})

    assert summary["create_elapsed_seconds"] is None
