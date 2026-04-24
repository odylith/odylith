from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest

from odylith.runtime.evaluation import odylith_benchmark_live_execution as live_execution


def _result(
    *,
    exit_code: int,
    validation_summary: str,
    candidate_write_path_count: int = 0,
    expectation_ok: bool = False,
) -> dict[str, Any]:
    return {
        "expectation_ok": expectation_ok,
        "candidate_write_path_count": candidate_write_path_count,
        "live_execution": {
            "exit_code": exit_code,
            "timed_out": False,
            "structured_output": {
                "validation_summary": validation_summary,
            },
        },
    }


def test_run_live_scenario_retries_negative_exit_missing_schema_without_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts: list[Mapping[str, Any]] = [
        _result(exit_code=-15, validation_summary="missing_schema_output"),
        _result(exit_code=0, validation_summary="passed", expectation_ok=True),
    ]

    def _fake_once(**_kwargs: Any) -> dict[str, Any]:
        return dict(attempts.pop(0))

    monkeypatch.setattr(live_execution, "_run_live_scenario_once", _fake_once)

    result = live_execution.run_live_scenario(
        repo_root=tmp_path,
        scenario={},
        mode="odylith_on",
        packet_source="benchmark_packet",
    )

    assert result["expectation_ok"] is True
    assert attempts == []
    assert result["live_execution"]["infra_retry_attempts"] == 1
    assert result["live_execution"]["infra_retry_replaced_exit_code"] == -15


def test_run_live_scenario_does_not_retry_real_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts: list[Mapping[str, Any]] = [
        _result(exit_code=0, validation_summary="failed"),
        _result(exit_code=0, validation_summary="passed", expectation_ok=True),
    ]

    def _fake_once(**_kwargs: Any) -> dict[str, Any]:
        return dict(attempts.pop(0))

    monkeypatch.setattr(live_execution, "_run_live_scenario_once", _fake_once)

    result = live_execution.run_live_scenario(
        repo_root=tmp_path,
        scenario={},
        mode="odylith_on",
        packet_source="benchmark_packet",
    )

    assert result["expectation_ok"] is False
    assert len(attempts) == 1
    assert "infra_retry_attempts" not in result["live_execution"]


def test_run_live_scenario_does_not_retry_after_observed_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts: list[Mapping[str, Any]] = [
        _result(exit_code=-15, validation_summary="missing_schema_output", candidate_write_path_count=1),
        _result(exit_code=0, validation_summary="passed", expectation_ok=True),
    ]

    def _fake_once(**_kwargs: Any) -> dict[str, Any]:
        return dict(attempts.pop(0))

    monkeypatch.setattr(live_execution, "_run_live_scenario_once", _fake_once)

    result = live_execution.run_live_scenario(
        repo_root=tmp_path,
        scenario={},
        mode="odylith_on",
        packet_source="benchmark_packet",
    )

    assert result["expectation_ok"] is False
    assert len(attempts) == 1
    assert "infra_retry_attempts" not in result["live_execution"]
