from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_clarification import ClarificationExecution
from greenfield_matrix_clarification import clarification_contract_issues
from greenfield_matrix_clarification import clarification_quality_verdict


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


def _clarification_execution(*, question: str, required_fields: tuple[str, ...]) -> ClarificationExecution:
    return ClarificationExecution(
        payload={
            "mode": "clarification_required",
            "clarification": {
                "question": question,
                "required_fields": list(required_fields),
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
        question="What result should the operator see, and where does the source data come from?",
        required_fields=("visible_result", "dependency_source"),
    )

    assert clarification_contract_issues(
        execution,
        expected_fields=("visible_result", "dependency_source"),
    ) == ()


def test_typed_clarification_compares_field_ids_without_changing_display_labels() -> None:
    execution = _clarification_execution(
        question="Could you specify the consent standard and minor-approval authority for this project?",
        required_fields=("consent_standard", "minor_approval_authority"),
    )

    assert clarification_contract_issues(
        execution,
        expected_fields=("consent standard", "minor-approval authority"),
    ) == ()


def test_typed_clarification_rejects_a_generic_question_for_the_wrong_field() -> None:
    execution = _clarification_execution(
        question="What is the first complete task the product should help a person finish, and what result should they see?",
        required_fields=("first_path",),
    )

    issues = clarification_contract_issues(execution, expected_fields=("proof_boundary",))

    assert "clarification payload must ask one focused question about the expected material fields" in issues
    assert any("required_fields must match the expected material fields" in issue for issue in issues)
