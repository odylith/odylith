from __future__ import annotations

import hashlib
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_clarification import ClarificationExecution
from greenfield_matrix_clarification import clarification_contract_issues
from greenfield_matrix_clarification import clarification_quality_verdict
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
