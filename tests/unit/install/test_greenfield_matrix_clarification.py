from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_clarification import ClarificationExecution
from greenfield_matrix_clarification import clarification_contract_issues
from greenfield_matrix_clarification import clarification_quality_verdict
from greenfield_model_profiles import model_profile_environment
from greenfield_model_profiles import model_profile_evidence
from greenfield_model_profile_proof import model_profile_release_proof
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import validate_greenfield_authoring_response
from odylith.runtime.domain_intelligence.greenfield_material_clarification import material_clarification_for_fields
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import combined_prompt_evidence_source
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_candidate_review import CANDIDATE_REVIEW_VERSION
from tests.greenfield_model_profile_test_support import (
    production_stage_observation,
    sealed_profile_observation,
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
    return ClarificationExecution(
        payload={
            "mode": "clarification_required",
            "clarification": {
                "question": question,
                "required_fields": list(required_fields),
                "model_profile": sealed_profile_observation(profile_id),
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


@pytest.mark.parametrize("mutation", ["flat", "missing_role", "extra_role", "wrong_model", "wrong_tier", "extra_field"])
def test_typed_clarification_rejects_incomplete_or_misattributed_roles(mutation: str) -> None:
    execution = _clarification_execution(
        question="What result should the operator see?",
        required_fields=("visible_result",),
    )
    observations = execution.payload["clarification"]["model_profile"]
    if mutation == "flat":
        execution.payload["clarification"]["model_profile"] = observations["remaining_candidate_authoring"]
    elif mutation == "missing_role":
        observations.pop("participant_selection")
    elif mutation == "extra_role":
        observations["candidate_review"] = observations["participant_selection"]
    elif mutation == "wrong_model":
        observations["participant_selection"]["model"] = "gpt-5.6-terra"
    elif mutation == "wrong_tier":
        observations["participant_selection"]["authoring_tier"] = ""
    else:
        observations["remaining_candidate_authoring"]["extra"] = True

    assert clarification_contract_issues(
        execution,
        expected_fields=("visible_result",),
        expected_model_profile_id=STANDARD_PROFILE_ID,
    )


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


def test_typed_clarification_accepts_complete_source_missingness_without_fake_span() -> None:
    execution = _clarification_execution(
        question="Who uses this product first, what complete task do they finish, and what result do they see?",
        required_fields=("first_path",),
    )
    payload = dict(execution.payload)
    clarification = dict(payload["clarification"])
    clarification["consistency_assessment"] = {
        "status": "material_ambiguity",
        "source_spans": [],
        "basis": "complete_source_missingness",
    }
    payload["clarification"] = clarification

    assert clarification_contract_issues(
        replace(execution, payload=payload),
        expected_fields=("first_path",),
    ) == ()


def test_complete_source_missingness_rejects_a_fabricated_span() -> None:
    execution = _clarification_execution(
        question="Who uses this product first, what complete task do they finish, and what result do they see?",
        required_fields=("first_path",),
    )
    payload = dict(execution.payload)
    clarification = dict(payload["clarification"])
    clarification["consistency_assessment"] = {
        "status": "material_ambiguity",
        "source_spans": [_consistency_span("invented support")],
        "basis": "complete_source_missingness",
    }
    payload["clarification"] = clarification

    issues = clarification_contract_issues(
        replace(execution, payload=payload),
        expected_fields=("first_path",),
    )

    assert "complete-source missingness clarification must not invent source spans" in issues


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


@pytest.mark.parametrize("output_issues", [(), ("successful output exposed a host-side repair contract",)])
@pytest.mark.parametrize("edit", ["", "EDIT: Preserve the stated source boundary."])
@pytest.mark.parametrize("terminal_failure", ["", "confirm", "same_hash_retry"])
def test_case_preserves_stage_observation_and_actual_terminal_diagnostics(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
    output_issues: tuple[str, ...],
    edit: str,
    terminal_failure: str,
) -> None:
    module = _matrix_module()
    repo_root = tmp_path / "repo"
    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("", encoding="utf-8")
    retained = _retained_case(module, tmp_path, "success")
    prompt = _retained_stage(STANDARD_PROFILE_ID, response_kind="authored")["request"]["evidence"]
    source = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=edit).evidence_source
    stage = production_stage_observation(STANDARD_PROFILE_ID, evidence_text=source)
    _write_stage_observation(retained, stage)
    candidate = stage["candidate_review"]["request"]["candidate"]
    receipt = {
        "version": CANDIDATE_REVIEW_VERSION, "status": "admitted",
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "candidate_sha256": hashlib.sha256(json.dumps(
            candidate, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest(),
    }
    transaction_hash = "a" * 64
    create = SimpleNamespace(
        stdout=json.dumps({
            "version": "odylith.greenfield.host-confirmation-callback.v1",
            "status": "CLOSED",
            "command": "CONFIRM",
            "transaction_hash": transaction_hash,
            "visible_markdown": (
                "The package is committed. Open the "
                "[Project dashboard](file:///reviewed/odylith/index.html?tab=project) "
                "or use `/reviewed/odylith/index.html`."
            ),
            "developer_context": "Return the supplied completion handoff.",
        }),
        stderr="",
        returncode=0,
    )
    execution = SimpleNamespace(
        decision=create,
        retry_decision=SimpleNamespace(stdout=create.stdout, stderr="", returncode=0),
        failure=None,
        commit_payload={"commit_manifest": {"model_authoring": {"candidate_review": receipt}}},
        proposal_seconds=1.0,
        confirmation_seconds=0.1,
        retry_seconds=0.1,
        dry_run_receipt={"transaction_hash": transaction_hash},
        proposal_payload={},
        output_contract_issues=output_issues,
        terminal_journal={},
        terminal_journal_sha256="",
        terminal_pre_retry_snapshot={},
        terminal_proof_issues=(),
    )
    if terminal_failure:
        actual = execution.decision if terminal_failure == "confirm" else execution.retry_decision
        actual.stdout, actual.stderr, actual.returncode = "actual terminal refusal", "actual terminal diagnostic", 2
        execution.output_contract_issues = (*output_issues, "terminal proof rejected")
        if terminal_failure == "confirm":
            execution.failure = SimpleNamespace(stdout="", stderr="evaluator summary", returncode=1)
            execution.retry_decision = None
        # Diagnostics must survive even without an external retained-case directory.
        retained = None
    captured: dict[str, object] = {}

    def profile_evidence(  # noqa: ANN001
        profile, environ, *, observed, stage_observation,
        reviewer_observation=None, expected_reviewer_candidate_sha256="",
        expected_source="",
    ):
        captured.update(
            profile=profile,
            observed=observed,
            stage_observation=stage_observation,
            reviewer_observation=reviewer_observation,
            expected_reviewer_candidate_sha256=expected_reviewer_candidate_sha256,
            expected_source=expected_source,
        )
        return {"status": "passed", "issues": []}

    monkeypatch.setattr(module, "_local_release_env", lambda **_kwargs: {})
    if terminal_failure:
        monkeypatch.setattr(module, "_retained_model_stage_observation", lambda _retained: stage)
    monkeypatch.setattr(
        module,
        "run_compiled_greenfield_journey",
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
    handoff_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "terminal_handoff_issues",
        lambda **kwargs: handoff_calls.append(kwargs) or (),
    )
    monkeypatch.setattr(module, "build_quality_verdict", lambda **kwargs: captured.update(
        quality_external_issues=kwargs["external_issues"],
    ) or replace(_passing_quality(module), passed=not terminal_failure))
    monkeypatch.setattr(module, "_case_evidence_manifest", lambda **_kwargs: {})
    monkeypatch.setattr(module, "_record_retained_execution", lambda **_kwargs: None)
    monkeypatch.setattr(module, "commit_manifest_summary", lambda _manifest: {})

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            case_id="success",
            name="success",
            prompt=prompt,
            confirmed_intent_markdown=edit,
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

    assert result.status == ("failed" if terminal_failure else "passed")
    assert captured["profile"] == STANDARD_PROFILE_ID
    assert captured["stage_observation"] == stage
    assert tuple(captured["quality_external_issues"]) == execution.output_contract_issues
    confirmation = result.evidence["confirmation_contract"]
    assert confirmation["scope"] == "explicit_terminal_decision"
    assert confirmation["native_chat"] == "unqualified"
    assert [call["terminal_decision"] for call in handoff_calls] == [
        decision for decision in (execution.decision, execution.retry_decision) if decision is not None
    ]
    assert all(call["transaction_hash"] == transaction_hash for call in handoff_calls)
    assert "post_confirm_navigation" not in execution.commit_payload
    if terminal_failure:
        command = next(row for row in confirmation["terminal_commands"] if row["attempt"] == terminal_failure)
        assert command == {
            "attempt": terminal_failure, "returncode": 2,
            "stdout_excerpt": "actual terminal refusal", "stderr_excerpt": "actual terminal diagnostic",
        }
    if terminal_failure == "confirm":
        assert result.failure_detail == "evaluator summary"
        assert result.create_stdout_excerpt == "actual terminal refusal"
        assert result.create_stderr_excerpt == "actual terminal diagnostic"


@pytest.mark.parametrize("mismatch", [False, True])
@pytest.mark.parametrize("edit", ["", "EDIT: Preserve the stated source boundary."])
def test_clarification_case_binds_two_call_stage_to_public_decision(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
    mismatch: bool,
    edit: str,
) -> None:
    module = _matrix_module()
    repo_root = tmp_path / "repo"
    retained = _retained_case(module, tmp_path, "clarification")
    prompt = "Mara needs a first workflow clarified."
    stage = production_stage_observation(
        STANDARD_PROFILE_ID, response_kind="clarification_required",
        evidence_text=prepare_model_authoring_evidence(prompt=prompt, edit_evidence=edit).evidence_source,
    )
    _write_stage_observation(retained, stage)
    execution = _source_bound_clarification_execution(stage)
    question = execution.payload["clarification"]["question"]
    if mismatch:
        execution.payload["clarification"]["required_fields"] = ["visible_result"]
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

    def profile_evidence(  # noqa: ANN001
        profile, environ, *, observed, stage_observation, expected_source,
        reviewer_observation=None, expected_reviewer_candidate_sha256="",
    ):
        captured.update(
            profile=profile,
            observed=observed,
            stage_observation=stage_observation,
            expected_source=expected_source,
            reviewer_observation=reviewer_observation,
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
            prompt=prompt,
            confirmed_intent_markdown=edit,
            required_terms=(),
            expectation="clarification_required",
            expected_clarification_field="visible_result" if mismatch else "first_path",
            expected_clarification_question=question,
        ),
        repo_root=repo_root,
        env=model_profile_environment(STANDARD_PROFILE_ID, {}),
        timeout=90,
        repair_tier="standard",
        install_script=tmp_path / "install.sh",
        version="0.0.0",
        install_mode="full",
        retained_case=retained,
    )

    assert result.status == ("failed" if mismatch else "passed")
    assert captured["profile"] == STANDARD_PROFILE_ID
    assert captured["stage_observation"] == stage
    assert captured["expected_source"] == stage["request"]["evidence"]


def test_runner_passes_retained_reviewer_observation_to_expected_clarification(
    tmp_path: Path, monkeypatch,  # noqa: ANN001
) -> None:
    module = _matrix_module()
    prompt = "The first complete task remains materially ambiguous."
    source = prepare_model_authoring_evidence(prompt=prompt).evidence_source
    retained = _retained_case(module, tmp_path, "reviewer-clarification")
    stage = _host_native_clarification_stage(source)
    stage["response_kind"] = "authored"
    stage["candidate_review_status"] = "clarification_required"
    semantic = retained.staging_root / "semantic"
    semantic.mkdir()
    (semantic / "host-authoring-observation.v1.json").write_text(
        json.dumps(stage), encoding="utf-8",
    )
    reviewer = _host_native_reviewer_clarification_observation(source)
    (semantic / "model-authoring-observation.v1.json").write_text(
        json.dumps(reviewer), encoding="utf-8",
    )
    execution = _host_native_clarification_execution(source)
    captured: dict[str, object] = {}

    class Audit:
        pass_fds: tuple[int, ...] = ()

        def environment(self):  # noqa: ANN201
            return {}

        def command(self, **_kwargs):  # noqa: ANN201
            return ()

        def finish(self):  # noqa: ANN201
            return SimpleNamespace(active=True, write_attempts=(), subprocess_attempts=(), error="")

    def profile_evidence(  # noqa: ANN001
        profile, environ, *, observed, stage_observation, expected_source,
        reviewer_observation=None, expected_reviewer_candidate_sha256="",
    ):
        captured.update(
            stage_observation=stage_observation,
            reviewer_observation=reviewer_observation,
            expected_source=expected_source,
        )
        return {"status": "passed", "issues": []}

    monkeypatch.setattr(module, "begin_installed_write_audit", lambda **_kwargs: Audit())
    monkeypatch.setattr(module, "_run_greenfield_propose", lambda **_kwargs: SimpleNamespace(stdout="", stderr=""))
    monkeypatch.setattr(module, "run_expected_clarification", lambda **kwargs: (kwargs["invoke"](), execution)[1])
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: SimpleNamespace())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: module.GreenfieldArtifactCounts())
    monkeypatch.setattr(module, "sealed_model_profile_observation", lambda **_kwargs: {})
    review = reviewer["candidate_review"]
    assert isinstance(review, dict)
    monkeypatch.setattr(
        module,
        "_retained_reviewer_candidate_sha256",
        lambda *_args, **_kwargs: str(review["candidate_sha256"]),
    )
    monkeypatch.setattr(module, "model_profile_evidence", profile_evidence)
    monkeypatch.setattr(module, "_case_evidence_manifest", lambda **_kwargs: {})
    monkeypatch.setattr(module, "_record_retained_execution", lambda **_kwargs: None)

    result = module._run_expected_clarification_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            case_id="reviewer-clarification", name="reviewer clarification", prompt=prompt,
            required_terms=(), expectation="clarification_required",
            expected_clarification_field="first_path",
            expected_clarification_question=execution.payload["clarification"]["question"],
        ),
        repo_root=tmp_path / "repo", env=model_profile_environment(STANDARD_PROFILE_ID, {}),
        timeout=90, repair_tier="standard", install_script=tmp_path / "install.sh",
        version="0.0.0", install_mode="full", retained_case=retained,
    )

    assert result.status == "passed", result.quality.issues
    assert captured["stage_observation"] == stage
    assert captured["reviewer_observation"] == reviewer
    assert captured["expected_source"] == source


def _source_bound_clarification_execution(stage):
    remainder = stage["remaining_candidate_authoring"]
    authored = validate_greenfield_authoring_response(
        remainder["response"], evidence_text=stage["request"]["evidence"],
        elapsed_seconds=remainder["elapsed_seconds"], provider=remainder["provider"],
        profile_id=remainder["profile_id"], effective_timeout_seconds=remainder["timeout_seconds"],
        semantic_model_call_count=2,
    )
    decision = material_clarification_for_fields(
        authored.required_fields, consistency_status=authored.consistency_status,
    )
    execution = _clarification_execution(
        question=decision.question, required_fields=decision.required_fields,
        profile_id=remainder["profile_id"],
    )
    execution.payload["clarification"]["consistency_assessment"] = {
        "status": authored.consistency_status,
        "source_spans": list(authored.consistency_source_spans),
    }
    return execution


@pytest.mark.parametrize("mutation", ["none", "field", "question", "consistency", "source", "missing_stage"])
def test_clarification_proof_binds_exact_source_and_public_decision(mutation):
    stage = production_stage_observation(STANDARD_PROFILE_ID, response_kind="clarification_required")
    execution = _source_bound_clarification_execution(stage)
    source = stage["request"]["evidence"]
    public = execution.payload["clarification"]
    if mutation == "field":
        public["required_fields"] = ["visible_result"]
    elif mutation == "question":
        public["question"] = "Could you specify the visible result?"
    elif mutation == "consistency":
        public["consistency_assessment"] = {"status": "consistent", "source_spans": []}
    elif mutation == "source":
        source += " Different source."
    elif mutation == "missing_stage":
        stage = {}
    issues = clarification_contract_issues(
        execution, expected_fields=tuple(public["required_fields"]),
        expected_question=public["question"], expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=stage, expected_source=source,
    )
    assert bool(issues) is (mutation != "none")


def _host_native_clarification_stage(
    source: str,
    *,
    profile_id: str = STANDARD_PROFILE_ID,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    return {
        "version": "odylith.greenfield.host-native-matrix-observation.v3",
        "status": "passed",
        "host_invocations": 1,
        "contract_command_invocations": 1,
        "proposal_command_invocations": 1,
        "model_profile_id": profile_id,
        "host_request": {
            "version": "odylith.greenfield.host-argv-receipt.v1",
            "executable_sha256": "7" * 64,
            "argument_count": 14,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "output_schema_present": True,
            "argv_shape_sha256": "8" * 64,
        },
        "candidate_temp_cleaned": True,
        "host_workspace_cleaned": True,
        "stage": "propose",
        "contract_returncode": 0,
        "contract_sha256": "1" * 64,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "candidate_schema_sha256": "2" * 64,
        "host_returncode": 0,
        "host_stdout_bytes": 200,
        "host_stderr_bytes": 0,
        "response_kind": "clarification_required",
        "candidate_sha256": "3" * 64,
        "candidate_raw_sha256": "4" * 64,
        "candidate_raw_bytes": 200,
        "candidate_temp_outside_repo": True,
        "proposal_returncode": 0,
        "proposal_stdout_sha256": "5" * 64,
        "proposal_stderr_sha256": "6" * 64,
        "proposal_mode": "clarification_required",
        "candidate_review_status": "unreported",
        "elapsed_seconds": 18.02,
    }


def _host_native_reviewer_clarification_observation(
    source: str,
    *,
    profile_id: str = STANDARD_PROFILE_ID,
    candidate_sha256: str = "3" * 64,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return {
        "version": "odylith.greenfield.model-proof-observation.v4",
        "authoring_version": "odylith.greenfield.intent-authoring.v69",
        "request": {
            "version": "odylith.greenfield.intent-authoring.v69",
            "evidence": source,
        },
        "semantic_model_call_count": 1,
        "origin": "host_native",
        "host_candidate": {
            "version": "odylith.greenfield.host-candidate.v1",
            "contract_version": "odylith.greenfield.intent-authoring.v69",
            "source_sha256": source_sha256,
            "candidate_sha256": candidate_sha256,
        },
        "candidate_review": {
            "version": CANDIDATE_REVIEW_VERSION,
            "status": "clarification_required",
            "source_sha256": source_sha256,
            "candidate_sha256": candidate_sha256,
            "model_profile": {
                "profile_id": profile_id,
                "provider": profile.provider,
                "model": profile.review_model,
                "reasoning_effort": profile.review_reasoning_effort,
                "effective_timeout_seconds": 120.0,
                "authoring_tier": profile.repair_tier,
            },
            "elapsed_seconds": 0.1,
            "clarification": {"material_dimension": "first_path"},
        },
    }


def _host_native_reviewer_admission_observation(
    source: str,
    *,
    profile_id: str = STANDARD_PROFILE_ID,
    host_candidate_sha256: str = "3" * 64,
    reviewer_candidate_sha256: str = "9" * 64,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return {
        "version": "odylith.greenfield.model-proof-observation.v4",
        "authoring_version": "odylith.greenfield.intent-authoring.v69",
        "request": {
            "version": "odylith.greenfield.intent-authoring.v69",
            "evidence": source,
        },
        "semantic_model_call_count": 1,
        "origin": "host_native",
        "host_candidate": {
            "version": "odylith.greenfield.host-candidate.v1",
            "contract_version": "odylith.greenfield.intent-authoring.v69",
            "source_sha256": source_sha256,
            "candidate_sha256": host_candidate_sha256,
        },
        "candidate_review": {
            "version": CANDIDATE_REVIEW_VERSION,
            "status": "admitted",
            "source_sha256": source_sha256,
            "candidate_sha256": reviewer_candidate_sha256,
            "model_profile": {
                "profile_id": profile_id,
                "provider": profile.provider,
                "model": profile.review_model,
                "reasoning_effort": profile.review_reasoning_effort,
                "effective_timeout_seconds": 120.0,
                "authoring_tier": profile.repair_tier,
            },
            "elapsed_seconds": 0.1,
            "admission_witness": {
                "participant_fact": {"field": "human_actors", "row": 1},
                "task_event_order": 1,
                "result_event_order": 1,
            },
        },
    }


def _host_native_clarification_execution(source: str) -> ClarificationExecution:
    decision = material_clarification_for_fields(
        ("first_path",), consistency_status="material_ambiguity",
    )
    execution = _clarification_execution(
        question=decision.question,
        required_fields=decision.required_fields,
    )
    clarification = execution.payload["clarification"]
    clarification.pop("model_profile")
    clarification["consistency_assessment"] = {
        "status": "material_ambiguity",
        "source_spans": [_consistency_span(source, start=0)],
    }
    return execution


def test_host_native_clarification_uses_private_one_call_custody() -> None:
    source = "The first complete task remains materially ambiguous."
    stage = _host_native_clarification_stage(source)
    execution = _host_native_clarification_execution(source)
    public = execution.payload["clarification"]

    assert "model_profile" not in public
    assert clarification_contract_issues(
        execution,
        expected_fields=("first_path",),
        expected_question=public["question"],
        expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=stage,
        expected_source=source,
    ) == ()
    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        expected_source=source,
    )
    assert evidence["status"] == "passed", evidence["issues"]
    assert evidence["sealed_request_roles"] == ["host_candidate"]
    assert evidence["maximum_semantic_model_calls"] == 1


def test_reviewer_selected_clarification_stays_host_native_without_reclassifying_host_output() -> None:
    source = "The first complete task remains materially ambiguous."
    stage = _host_native_clarification_stage(source)
    stage["response_kind"] = "authored"
    stage["candidate_review_status"] = "clarification_required"
    reviewer = _host_native_reviewer_clarification_observation(source)
    review = reviewer["candidate_review"]
    assert isinstance(review, dict)

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        reviewer_observation=reviewer,
        expected_reviewer_candidate_sha256=str(review["candidate_sha256"]),
        expected_source=source,
    )

    assert evidence["status"] == "passed", evidence["issues"]
    summary = evidence["stage_observation_summary"]
    assert summary["response_kind"] == "authored"
    assert summary["clarification_origin"] == "reviewer"
    assert evidence["sealed_request_roles"] == ["host_candidate"]
    assert summary["reviewer_receipt_verified"] is True
    assert not any(
        "participant_selection" in issue or "remaining_candidate_authoring" in issue
        for issue in evidence["issues"]
    )

    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=evidence,
    )
    proof = model_profile_release_proof((result,), require_complete=False)
    assert proof["status"] == "passed", proof["issues"]


def test_reviewer_selected_clarification_fails_closed_without_private_receipt() -> None:
    source = "The first complete task remains materially ambiguous."
    stage = _host_native_clarification_stage(source)
    stage["response_kind"] = "authored"
    stage["candidate_review_status"] = "clarification_required"

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        expected_source=source,
    )

    assert evidence["status"] == "failed"
    assert "private host-native reviewer clarification observation is missing or malformed" in evidence["issues"]
    assert evidence["stage_observation_summary"]["clarification_origin"] == "reviewer"
    assert not any(
        "participant_selection" in issue or "remaining_candidate_authoring" in issue
        for issue in evidence["issues"]
    )


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    (
        ("source", "private host-native reviewer receipt source does not match the evaluated source"),
        ("candidate_hash", "private host-native reviewer receipt candidate hash is invalid"),
        ("substituted_candidate_hash", "private host-native reviewer receipt does not match the canonical candidate"),
        ("model", "does not match pinned"),
        ("missing_profile_field", "private host-native reviewer model profile is missing or malformed"),
        ("extra_profile_field", "private host-native reviewer model profile is missing or malformed"),
        ("profile_id", "private host-native reviewer model profile identifies a different profile"),
        ("elapsed_effective_timeout", "private host-native reviewer elapsed time exceeds its effective timeout"),
        ("elapsed_shared_window", "private host-native reviewer elapsed time exceeds the shared model window"),
        ("returncode", "retained host-native successful proposal has a nonzero return code"),
    ),
)
def test_reviewer_selected_clarification_rejects_forged_private_or_stage_custody(
    mutation: str, expected_issue: str,
) -> None:
    source = "The first complete task remains materially ambiguous."
    stage = _host_native_clarification_stage(source)
    stage["response_kind"] = "authored"
    stage["candidate_review_status"] = "clarification_required"
    reviewer = _host_native_reviewer_clarification_observation(source)
    review = reviewer["candidate_review"]
    assert isinstance(review, dict)
    canonical_candidate_sha256 = str(review["candidate_sha256"])
    if mutation == "source":
        review["source_sha256"] = "0" * 64
    elif mutation == "candidate_hash":
        review["candidate_sha256"] = "forged"
    elif mutation == "substituted_candidate_hash":
        review["candidate_sha256"] = "f" * 64
    elif mutation in {"elapsed_effective_timeout", "elapsed_shared_window"}:
        model_profile = review["model_profile"]
        assert isinstance(model_profile, dict)
        if mutation == "elapsed_effective_timeout":
            review["elapsed_seconds"] = float(model_profile["effective_timeout_seconds"]) + 1.0
        else:
            model_profile["effective_timeout_seconds"] = 200.0
            review["elapsed_seconds"] = (
                get_greenfield_model_profile(STANDARD_PROFILE_ID).model_timeout_seconds + 1.0
            )
    elif mutation in {"model", "missing_profile_field", "extra_profile_field", "profile_id"}:
        model_profile = review["model_profile"]
        assert isinstance(model_profile, dict)
        if mutation == "model":
            model_profile["model"] = "forged"
        elif mutation == "missing_profile_field":
            model_profile.pop("profile_id")
        elif mutation == "extra_profile_field":
            model_profile["forged"] = True
        else:
            model_profile["profile_id"] = RESCUE_PROFILE_ID
    else:
        stage["proposal_returncode"] = 2

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        reviewer_observation=reviewer,
        expected_reviewer_candidate_sha256=canonical_candidate_sha256,
        expected_source=source,
    )

    assert evidence["status"] == "failed"
    assert any(expected_issue in issue for issue in evidence["issues"])


def _host_native_clarification_profile_evidence(
    source: str,
    *,
    profile_id: str = STANDARD_PROFILE_ID,
) -> dict[str, object]:
    return model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed={},
        stage_observation=_host_native_clarification_stage(
            source,
            profile_id=profile_id,
        ),
        expected_source=source,
    )


def _host_native_authored_profile_evidence(
    source: str,
    *,
    profile_id: str = STANDARD_PROFILE_ID,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    stage = _host_native_clarification_stage(source, profile_id=profile_id)
    stage["response_kind"] = "authored"
    observed = {
        "origin": "host_native",
        "host_candidate": {
            "version": "odylith.greenfield.host-candidate.v1",
            "contract_version": "odylith.greenfield.intent-authoring.v69",
            "source_sha256": stage["source_sha256"],
            "candidate_sha256": stage["candidate_sha256"],
        },
        "candidate_review": {
            "profile_id": profile_id,
            "provider": profile.provider,
            "model": profile.review_model,
            "reasoning_effort": profile.review_reasoning_effort,
            "effective_timeout_seconds": 120.0,
            "authoring_tier": profile.repair_tier,
        },
    }
    reviewer_candidate_sha256 = "9" * 64
    reviewer = _host_native_reviewer_admission_observation(
        source,
        profile_id=profile_id,
        host_candidate_sha256=str(stage["candidate_sha256"]),
        reviewer_candidate_sha256=reviewer_candidate_sha256,
    )
    return model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed=observed,
        stage_observation=stage,
        reviewer_observation=reviewer,
        expected_reviewer_candidate_sha256=reviewer_candidate_sha256,
        expected_source=source,
    )


def _host_native_clarification_aggregate_result(
    source: str,
    *,
    profile_evidence: dict[str, object],
) -> SimpleNamespace:
    execution = _host_native_clarification_execution(source)
    public = execution.payload["clarification"]
    return SimpleNamespace(
        name="host-native clarification",
        status="passed",
        proposal_seconds=18.02,
        quality=clarification_quality_verdict(()),
        evidence={
            "case": {
                "expectation": "clarification_required",
                "prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
                "expected_clarification": {
                    "field": "first_path",
                    "question": public["question"],
                },
            },
            "clarification": {
                "mode": "clarification_required",
                "question": public["question"],
                "required_fields": ["first_path"],
                "returncode": 0,
            },
            "no_write": {
                "before_record_count": 0,
                "after_record_count": 0,
                "changed_records": [],
                "staged_transaction_present": False,
                "write_audit_active": True,
                "write_attempts": [],
                "write_audit_error": "",
            },
            "model_profile": profile_evidence,
        },
    )


def _host_native_committed_aggregate_result(
    *,
    profile_evidence: dict[str, object],
) -> SimpleNamespace:
    return SimpleNamespace(
        name="host-native committed",
        status="passed",
        proposal_seconds=18.02,
        quality=SimpleNamespace(passed=True),
        evidence={
            "case": {
                "expectation": "transaction_committed",
                "prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
            },
            "model_profile": profile_evidence,
        },
    )


def test_host_native_clarification_passes_aggregate_profile_proof() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "passed", proof["issues"]
    assert proof["profiles"][STANDARD_PROFILE_ID]["maximum_semantic_model_calls"] == 1


def test_release_profile_proof_requires_astra_success_and_luna_no_write_control() -> None:
    source = "The first complete task remains materially ambiguous."
    clarification = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=_host_native_clarification_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )
    authored_evidence = _host_native_authored_profile_evidence(
        source,
        profile_id=STANDARD_PROFILE_ID,
    )
    assert authored_evidence["status"] == "passed", authored_evidence["issues"]
    committed = _host_native_committed_aggregate_result(
        profile_evidence=authored_evidence,
    )
    proof = model_profile_release_proof((committed, clarification), require_complete=True)

    assert proof["status"] == "passed", proof["issues"]
    assert proof["lower_capability_scope"]["status"] == "passed"
    assert proof["lower_capability_scope"]["role"] == "host_candidate"
    observed = proof["lower_capability_scope"]["observed_profiles"]
    assert len(observed) == 1
    assert observed[0]["profile_id"] == RESCUE_PROFILE_ID
    assert observed[0]["model"] == get_greenfield_model_profile(
        RESCUE_PROFILE_ID
    ).model
    assert observed[0]["committed_positive_case_count"] == 0
    assert observed[0]["clarification_no_write_control_count"] == 1


def test_complete_release_profile_proof_fails_without_astra_or_luna_control() -> None:
    source = "The first complete task remains materially ambiguous."
    astra = _host_native_committed_aggregate_result(
        profile_evidence=_host_native_authored_profile_evidence(source),
    )
    luna = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=_host_native_clarification_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )

    missing_luna = model_profile_release_proof((astra,), require_complete=True)
    missing_astra = model_profile_release_proof((luna,), require_complete=True)

    assert missing_luna["status"] == "failed"
    assert any("clarification/no-write control" in issue for issue in missing_luna["issues"])
    assert missing_astra["status"] == "failed"
    assert any("missing success profile" in issue for issue in missing_astra["issues"])


def test_release_profile_proof_rejects_duplicate_luna_controls() -> None:
    source = "The first complete task remains materially ambiguous."
    committed = _host_native_committed_aggregate_result(
        profile_evidence=_host_native_authored_profile_evidence(source),
    )
    clarification = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=_host_native_clarification_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )

    proof = model_profile_release_proof(
        (committed, clarification, clarification),
        require_complete=True,
    )

    assert proof["status"] == "failed"
    assert any("exactly one result" in issue for issue in proof["issues"])


def test_luna_or_sol_positive_result_cannot_qualify_release_success() -> None:
    source = "The first complete task remains materially ambiguous."
    luna_positive = _host_native_committed_aggregate_result(
        profile_evidence=_host_native_authored_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )
    sol_evidence = _host_native_authored_profile_evidence(source)
    sol_evidence["profile_id"] = DEEP_PROFILE_ID
    sol_positive = _host_native_committed_aggregate_result(
        profile_evidence=sol_evidence,
    )

    luna_proof = model_profile_release_proof((luna_positive,), require_complete=False)
    sol_proof = model_profile_release_proof((sol_positive,), require_complete=False)

    assert luna_proof["status"] == "failed"
    assert any("must clarify without writing" in issue for issue in luna_proof["issues"])
    assert sol_proof["status"] == "failed"
    assert any("unsupported diagnostic" in issue for issue in sol_proof["issues"])


def test_aggregate_clarification_rejects_contradictory_authored_observations() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    profile_evidence["observed"] = {
        "participant_selection": {},
        "remaining_candidate_authoring": {},
    }
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("contradictory authored observations" in issue for issue in proof["issues"])


def test_aggregate_authored_evidence_cannot_be_reclassified_by_response_kind() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_authored_profile_evidence(source)
    assert profile_evidence["status"] == "passed", profile_evidence["issues"]
    profile_evidence["stage_observation"]["response_kind"] = "clarification_required"
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("reviewed candidate does not match" in issue for issue in proof["issues"])


def test_aggregate_clarification_revalidates_retained_expected_source_hash() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    profile_evidence["stage_observation"]["source_sha256"] = "4" * 64
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("source does not match" in issue for issue in proof["issues"])


@pytest.mark.parametrize(
    "elapsed",
    (180.0, 180.001, None, True, "18.0", 0.0, -1.0, float("nan"), float("inf")),
)
def test_aggregate_clarification_rejects_expired_or_invalid_elapsed(elapsed: object) -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    profile_evidence["stage_observation"]["elapsed_seconds"] = elapsed
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("operational-timeout proof" in issue for issue in proof["issues"])


@pytest.mark.parametrize(
    "mutation",
    ("source", "response_kind", "call_count", "cleanup", "profile"),
)
def test_host_native_clarification_rejects_broken_private_custody(mutation: str) -> None:
    source = "The first complete task remains materially ambiguous."
    stage = _host_native_clarification_stage(source)
    if mutation == "source":
        stage["source_sha256"] = "4" * 64
    elif mutation == "response_kind":
        stage["response_kind"] = "authored"
    elif mutation == "call_count":
        stage["host_invocations"] = 2
    elif mutation == "cleanup":
        stage["candidate_temp_cleaned"] = False
    else:
        stage["model_profile_id"] = RESCUE_PROFILE_ID
    execution = _host_native_clarification_execution(source)

    issues = clarification_contract_issues(
        execution,
        expected_fields=("first_path",),
        expected_question=execution.payload["clarification"]["question"],
        expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=stage,
        expected_source=source,
    )

    assert issues


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
    return production_stage_observation(profile_id, response_kind=response_kind)


def _passing_quality(module):  # noqa: ANN001, ANN202
    return module.GreenfieldQualityVerdict(
        passed=True,
        issues=(),
        lenses={},
        scores={},
        score=100,
        score_explanation=(),
    )
