from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_attempt_ledger import MatrixAttemptLedger
from greenfield_matrix_attempt_ledger import replay_case_identities
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_evidence


def test_attempt_ledger_replays_only_failed_or_interrupted_case_identities(tmp_path: Path) -> None:
    first, second = _cases()
    path = tmp_path / "attempts.v1.jsonl"
    ledger = MatrixAttemptLedger(path)

    ledger.ensure_planned((first, second))
    ledger.record_started(case=first, index=1, total=2)
    ledger.record_completed(_passed_result(first))
    ledger.record_started(case=second, index=2, total=2)

    replay = replay_case_identities(path)

    assert [identity["id"] for identity in replay] == ["case-002"]
    assert replay[0]["attempt_state"] == "started"
    serialized = path.read_text(encoding="utf-8")
    assert first.prompt not in serialized
    assert second.prompt not in serialized
    assert first.confirmed_intent_markdown not in serialized


def test_attempt_ledger_keeps_failed_completion_replayable(tmp_path: Path) -> None:
    first, _second = _cases()
    path = tmp_path / "attempts.v1.jsonl"
    ledger = MatrixAttemptLedger(path)

    ledger.ensure_planned((first,))
    ledger.record_completed(_failed_result(first))

    replay = replay_case_identities(path)

    assert replay == (
        {
            "id": first.case_id,
            "prompt_sha256": hashlib.sha256(first.prompt.encode("utf-8")).hexdigest(),
            "confirmed_intent_sha256": hashlib.sha256(
                first.confirmed_intent_markdown.encode("utf-8")
            ).hexdigest(),
            "attempt_state": "failed",
        },
    )


def test_attempt_ledger_does_not_treat_unstarted_plans_as_exact_replay_or_store_case_content(
    tmp_path: Path,
) -> None:
    first, second = _cases()
    path = tmp_path / "attempts.v1.jsonl"
    ledger = MatrixAttemptLedger(path)

    ledger.ensure_planned((first, second))
    ledger.record_started(case=first, index=1, total=2)

    replay = replay_case_identities(path)
    serialized = path.read_text(encoding="utf-8")

    assert replay == (
        {
            "id": first.case_id,
            "prompt_sha256": hashlib.sha256(first.prompt.encode("utf-8")).hexdigest(),
            "confirmed_intent_sha256": hashlib.sha256(
                first.confirmed_intent_markdown.encode("utf-8")
            ).hexdigest(),
            "attempt_state": "started",
        },
    )
    assert second.case_id not in {identity["id"] for identity in replay}
    for forbidden in (
        first.name,
        second.name,
        first.prompt,
        second.prompt,
        first.confirmed_intent_markdown,
        first.required_terms[0],
        second.required_terms[0],
    ):
        assert forbidden not in serialized


def _cases() -> tuple[GreenfieldMatrixCase, GreenfieldMatrixCase]:
    return (
        GreenfieldMatrixCase(
            case_id="case-001",
            name="first custody case",
            prompt="Create the private first custody workspace.",
            confirmed_intent_markdown="**Private edit evidence**",
            required_terms=("private", "custody"),
        ),
        GreenfieldMatrixCase(
            case_id="case-002",
            name="second custody case",
            prompt="Create the private second custody workspace.",
            required_terms=("private", "custody"),
        ),
    )


def _passed_result(case: GreenfieldMatrixCase) -> GreenfieldMatrixResult:
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        evidence={"case": case_evidence(case)},
    )


def _failed_result(case: GreenfieldMatrixCase) -> GreenfieldMatrixResult:
    return GreenfieldMatrixResult(
        name=case.name,
        status="failed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(False, ("forced",), {}, {}, 0, ()),
        evidence={"case": case_evidence(case)},
    )
