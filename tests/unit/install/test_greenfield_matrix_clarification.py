from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_clarification import ClarificationExecution
from greenfield_matrix_clarification import clarification_contract_issues
from greenfield_matrix_clarification import clarification_quality_verdict
from greenfield_model_profiles import model_profile_environment
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)


def _matrix_module():
    spec = importlib.util.spec_from_file_location(
        "greenfield_preconfirm_matrix_clarification_test",
        SCRIPTS_ROOT / "greenfield_preconfirm_matrix.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_clarification_quality_verdict_preserves_one_complete_summary_line() -> None:
    verdict = clarification_quality_verdict(())

    assert verdict.score_explanation == (
        "clarification-required pre-confirm contract verified without a transaction or governed write",
    )
    assert verdict.lenses == {
        "product_manager": False,
        "architect": False,
        "engineer": False,
        "domain_expert": False,
    }
    assert all(verdict.scores[lens] == -1 for lens in verdict.lenses)


def test_matrix_summary_renders_the_clarification_verdict_once(capsys) -> None:  # noqa: ANN001
    module = _matrix_module()
    explanation = "clarification-required pre-confirm contract verified without a transaction or governed write"
    result = module.GreenfieldMatrixResult(
        name="cell therapy clarification",
        status="passed",
        create_seconds=0.0,
        counts=module.GreenfieldArtifactCounts(),
        quality=clarification_quality_verdict(()),
    )

    module._print_human_summary((result,))  # noqa: SLF001

    output = capsys.readouterr().out
    assert output.count(f"   score: {explanation}") == 1
    assert "\n   score: c\n" not in output


def _clarification_execution(
    *,
    question: str,
    required_fields: tuple[str, ...],
    profile_id: str = STANDARD_PROFILE_ID,
) -> ClarificationExecution:
    profile = get_greenfield_model_profile(profile_id)
    return ClarificationExecution(
        payload={
            "mode": "clarification_required",
            "clarification": {
                "question": question,
                "required_fields": list(required_fields),
                "model_profile": {
                    "profile_id": profile_id,
                    "provider": "codex-cli",
                    "model": profile.model,
                    "reasoning_effort": profile.reasoning_effort,
                    "effective_timeout_seconds": profile.model_timeout_seconds,
                    "authoring_tier": profile.repair_tier,
                },
                "consistency_assessment": {
                    "status": "consistent",
                    "source_spans": [],
                },
            },
        },
        returncode=0,
        seconds=0.1,
        before_record_count=0,
        after_record_count=0,
        changed_records=(),
        staged_transaction_present=False,
        write_audit_active=True,
    )


def test_typed_clarification_accepts_the_expected_material_fields() -> None:
    execution = _clarification_execution(
        question="What result should the operator see?",
        required_fields=("visible_result",),
    )

    assert clarification_contract_issues(
        execution,
        expected_fields=("visible_result",),
        expected_question="What result should the operator see?",
        expected_model_profile_id=STANDARD_PROFILE_ID,
    ) == ()


def test_typed_clarification_keeps_model_subprocess_as_diagnostic_evidence() -> None:
    execution = _clarification_execution(
        question="What result should the operator see?",
        required_fields=("visible_result",),
    )

    assert clarification_contract_issues(
        replace(execution, subprocess_attempts=("subprocess.Popen",)),
        expected_fields=("visible_result",),
        expected_question="What result should the operator see?",
        expected_model_profile_id=STANDARD_PROFILE_ID,
    ) == ()


def test_typed_clarification_still_rejects_governed_write_attempts() -> None:
    execution = _clarification_execution(
        question="What result should the operator see?",
        required_fields=("visible_result",),
    )

    issues = clarification_contract_issues(
        replace(execution, write_attempts=("open:odylith/radar/source/workstreams.v1.json",)),
        expected_fields=("visible_result",),
    )

    assert any("attempted repository writes" in issue for issue in issues)


def test_typed_clarification_rejects_a_different_selected_profile() -> None:
    execution = _clarification_execution(
        question="What result should the operator see?",
        required_fields=("visible_result",),
    )

    issues = clarification_contract_issues(
        execution,
        expected_fields=("visible_result",),
        expected_model_profile_id=RESCUE_PROFILE_ID,
    )

    assert "clarification model_profile must match the selected pre-call profile" in issues


def test_typed_clarification_rejects_unbound_material_contradiction() -> None:
    execution = _clarification_execution(
        question="Which operating limit should govern the first release?",
        required_fields=("operational_constraints",),
    )
    payload = dict(execution.payload)
    clarification = dict(payload["clarification"])
    clarification["consistency_assessment"] = {
        "status": "material_contradiction",
        "source_spans": [],
    }
    payload["clarification"] = clarification

    issues = clarification_contract_issues(
        replace(execution, payload=payload),
        expected_fields=("operational_constraints",),
    )

    assert "material contradiction clarification requires at least two source-bound spans" in issues


def _consistency_span(text: str, *, row_index: int = 1, start: int = 9) -> dict[str, object]:
    return {
        "span_id": f"authoring:consistency:{row_index}",
        "section_key": "ambiguities",
        "row_index": row_index,
        "classification": "supporting_evidence",
        "text": text,
        "source_start_byte": start,
        "source_end_byte": start + len(text.encode("utf-8")),
        "quote_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def test_typed_clarification_accepts_source_bound_material_ambiguity() -> None:
    execution = _clarification_execution(
        question="Which system should own the stated responsibility?",
        required_fields=("product_boundary",),
    )
    payload = dict(execution.payload)
    clarification = dict(payload["clarification"])
    clarification["consistency_assessment"] = {
        "status": "material_ambiguity",
        "source_spans": [_consistency_span("two possible responsibility owners")],
    }
    payload["clarification"] = clarification

    assert clarification_contract_issues(
        replace(execution, payload=payload),
        expected_fields=("product_boundary",),
    ) == ()


def test_typed_clarification_rejects_unbound_material_ambiguity() -> None:
    execution = _clarification_execution(
        question="Which system should own the stated responsibility?",
        required_fields=("product_boundary",),
    )
    payload = dict(execution.payload)
    clarification = dict(payload["clarification"])
    invalid_span = _consistency_span("two possible responsibility owners")
    invalid_span["quote_sha256"] = "0" * 64
    clarification["consistency_assessment"] = {
        "status": "material_ambiguity",
        "source_spans": [invalid_span],
    }
    payload["clarification"] = clarification

    issues = clarification_contract_issues(
        replace(execution, payload=payload),
        expected_fields=("product_boundary",),
    )

    assert "material ambiguity clarification requires at least one valid source-bound span" in issues


def test_typed_clarification_requires_exact_field_ids() -> None:
    execution = _clarification_execution(
        question="What is the first complete path?",
        required_fields=("first_path",),
    )

    issues = clarification_contract_issues(
        execution,
        expected_fields=("first path",),
    )

    assert any("required_fields must match the expected material fields" in issue for issue in issues)


def test_typed_clarification_rejects_a_generic_question_for_the_wrong_field() -> None:
    execution = _clarification_execution(
        question="What is the first complete task the product should help a person finish, and what result should they see?",
        required_fields=("first_path",),
    )

    issues = clarification_contract_issues(execution, expected_fields=("proof_boundary",))

    assert any("required_fields must match the expected material fields" in issue for issue in issues)


def test_typed_clarification_rejects_the_wrong_product_owned_question() -> None:
    execution = _clarification_execution(
        question="What is the first complete task?",
        required_fields=("first_path",),
    )

    issues = clarification_contract_issues(
        execution,
        expected_fields=("first_path",),
        expected_question="What is the first complete task and visible result?",
    )

    assert "clarification payload question must match the frozen typed clarification" in issues


def test_typed_clarification_rejects_a_missing_frozen_field_oracle() -> None:
    execution = _clarification_execution(
        question="What is the first complete task the product should help a person finish?",
        required_fields=("first_path",),
    )

    issues = clarification_contract_issues(execution)

    assert "clarification release case lacks frozen expected material fields" in issues


def test_success_case_passes_closed_retained_stage_observation_to_profile_evidence(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    module = _matrix_module()
    repo_root = tmp_path / "repo"
    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("", encoding="utf-8")
    retained = _retained_case(module, tmp_path, "success")
    stage = _retained_stage(STANDARD_PROFILE_ID, response_kind="authored")
    _write_stage_observation(retained, stage)
    create = SimpleNamespace(
        stdout=json.dumps({"commit_manifest": {}}),
        stderr="",
        returncode=0,
    )
    execution = SimpleNamespace(
        create=create,
        proposal_seconds=1.0,
        create_seconds=0.1,
        dry_run_receipt={},
        proposal_payload={},
    )
    captured: dict[str, object] = {}

    def profile_evidence(profile, environ, *, observed, stage_observation):  # noqa: ANN001
        captured.update(
            profile=profile,
            observed=observed,
            stage_observation=stage_observation,
        )
        return {"status": "passed", "issues": []}

    monkeypatch.setattr(module, "_local_release_env", lambda **_kwargs: {})
    monkeypatch.setattr(
        module,
        "_run_compiled_greenfield_create_with_receipt",
        lambda **_kwargs: execution,
    )
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: SimpleNamespace())
    monkeypatch.setattr(module, "sealed_model_profile_observation", lambda **_kwargs: {"sealed": True})
    monkeypatch.setattr(module, "model_profile_evidence", profile_evidence)
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: module.GreenfieldArtifactCounts())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_generated_text", lambda **_kwargs: "")
    monkeypatch.setattr(module, "dry_run_commit_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "confirmation_preview_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "post_confirm_navigation_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "build_quality_verdict", lambda **_kwargs: _passing_quality(module))
    monkeypatch.setattr(module, "_case_evidence_manifest", lambda **_kwargs: {})
    monkeypatch.setattr(module, "_record_retained_execution", lambda **_kwargs: None)
    monkeypatch.setattr(module, "commit_manifest_summary", lambda _manifest: {})

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            case_id="success",
            name="success",
            prompt="Mara completes one source-grounded task.",
            required_terms=(),
        ),
        repo_root=repo_root,
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1",
        version="0.0.0",
        skip_install=True,
        include_lexical_custody_proof=False,
        retained_case=retained,
    )

    assert result.status == "passed"
    assert captured["profile"] == STANDARD_PROFILE_ID
    assert captured["stage_observation"] == stage


def test_clarification_case_passes_one_call_stage_observation_to_profile_evidence(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    module = _matrix_module()
    repo_root = tmp_path / "repo"
    retained = _retained_case(module, tmp_path, "clarification")
    stage = _retained_stage(RESCUE_PROFILE_ID, response_kind="clarification_required")
    _write_stage_observation(retained, stage)
    question = "Which visible result should Mara verify?"
    execution = _clarification_execution(
        question=question,
        required_fields=("visible_result",),
        profile_id=RESCUE_PROFILE_ID,
    )
    captured: dict[str, object] = {}

    class Audit:
        pass_fds: tuple[int, ...] = ()

        def environment(self):  # noqa: ANN201
            return {}

        def command(self, **_kwargs):  # noqa: ANN201
            return ()

        def finish(self):  # noqa: ANN201
            return SimpleNamespace(
                active=True,
                write_attempts=(),
                subprocess_attempts=(),
                error="",
            )

    def profile_evidence(profile, environ, *, observed, stage_observation):  # noqa: ANN001
        captured.update(
            profile=profile,
            observed=observed,
            stage_observation=stage_observation,
        )
        return {"status": "passed", "issues": []}

    monkeypatch.setattr(module, "begin_installed_write_audit", lambda **_kwargs: Audit())
    monkeypatch.setattr(module, "_run_greenfield_propose", lambda **_kwargs: SimpleNamespace(stdout="", stderr=""))
    monkeypatch.setattr(
        module,
        "run_expected_clarification",
        lambda **kwargs: (kwargs["invoke"](), execution)[1],
    )
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: SimpleNamespace())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: module.GreenfieldArtifactCounts())
    monkeypatch.setattr(module, "sealed_model_profile_observation", lambda **_kwargs: {"sealed": True})
    monkeypatch.setattr(module, "model_profile_evidence", profile_evidence)
    monkeypatch.setattr(module, "_case_evidence_manifest", lambda **_kwargs: {})
    monkeypatch.setattr(module, "_record_retained_execution", lambda **_kwargs: None)

    result = module._run_expected_clarification_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            case_id="clarification",
            name="clarification",
            prompt="Mara needs a material result clarified.",
            required_terms=(),
            expectation="clarification_required",
            expected_clarification_field="visible_result",
            expected_clarification_question=question,
        ),
        repo_root=repo_root,
        env=model_profile_environment(RESCUE_PROFILE_ID, {}),
        timeout=90,
        repair_tier="rescue",
        install_script=tmp_path / "install.sh",
        version="0.0.0",
        install_mode="full",
        retained_case=retained,
    )

    assert result.status == "passed"
    assert captured["profile"] == RESCUE_PROFILE_ID
    assert captured["stage_observation"] == stage


def _retained_case(module, tmp_path: Path, case_id: str):  # noqa: ANN001, ANN202
    staging = tmp_path / f"{case_id}-staging"
    staging.mkdir()
    return module.RetainedEvidenceCase(
        case_id=case_id,
        staging_root=staging,
        final_root=tmp_path / case_id,
    )


def _write_stage_observation(retained, stage: dict[str, object]) -> None:  # noqa: ANN001
    path = retained.staging_root / "semantic" / "model-authoring-observation.v1.json"
    path.parent.mkdir()
    path.write_text(json.dumps(stage), encoding="utf-8")


def _retained_stage(profile_id: str, *, response_kind: str) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    initial = {
        "profile_id": profile_id,
        "request_role": "initial_authoring",
        "timeout_seconds": profile.model_timeout_seconds - profile.source_review_reserve_seconds,
        "elapsed_seconds": 5.0,
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "provider": {
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
        },
    }
    return {
        "version": "odylith.greenfield.model-proof-observation.v2",
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "semantic_model_call_count": 1 if response_kind == "clarification_required" else 2,
        "response": {
            "version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "result": {"status": response_kind},
        },
        "initial_authoring": initial,
    }


def _passing_quality(module):  # noqa: ANN001, ANN202
    return module.GreenfieldQualityVerdict(
        passed=True,
        issues=(),
        lenses={},
        scores={},
        score=100,
        score_explanation=(),
    )
