"""The revised candidate window reserves completion inside the fixed journey."""

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_host_flow as host_module
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import WholeJourneyDeadline
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow


def test_whole_deadline_reserves_completion_without_increasing_its_cap():
    now = [600.0]
    budget = WholeJourneyDeadline(0.0, lambda: now[0])
    assert budget.cap_seconds == 660.0
    assert budget.request_timeout(300.0, reserve_seconds=15.0) == 45.0
    now[0] = 645.0
    with pytest.raises(TimeoutError, match="completion reserve"):
        budget.request_timeout(300.0, reserve_seconds=15.0)
    now[0] = 660.0
    with pytest.raises(TimeoutError, match="deadline expired"):
        budget.request_timeout(300.0, reserve_seconds=15.0)


@pytest.mark.parametrize("reserve", [-1.0, float("nan"), float("inf"), True])
def test_whole_deadline_rejects_invalid_completion_reserve(reserve):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        WholeJourneyDeadline(0.0, lambda: 0.0).request_timeout(300.0, reserve_seconds=reserve)


@pytest.mark.parametrize("retention_seconds,proposal_seconds", [(0.0, 1.0), (264.0, 1.0), (0.0, 16.0)])
def test_real_driver_reserves_completion_from_shared_whole_clock(
    tmp_path, monkeypatch, retention_seconds, proposal_seconds,
):
    flow, host_run, _installed, hosts, proposals, repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    now = [0.0]
    proposal_timeouts = []
    original_installed = flow.invoke_installed
    original_propose = flow.invoke_propose
    monkeypatch.setattr(host_module.time, "monotonic", lambda: now[0])

    def timed_host(command, **kwargs):
        result = host_run(command, **kwargs)
        schema = Path(command[command.index("--output-schema") + 1]).name
        now[0] += {"authority-gate-schema.json": 1.0, "source-ledger-schema.json": 260.0,
                   "source-duty-decision-schema.json": 100.0, "candidate-schema.json": 263.0}[schema]
        return result

    def timed_installed(command, timeout):
        result = original_installed(command, timeout)
        if "source-ledger-check" in command:
            now[0] += 10.0
        return result

    def retain_checked_receipt(_value):
        now[0] += retention_seconds

    def timed_propose(candidate_path, gate_path, ledger_path, timeout):
        proposal_timeouts.append(timeout)
        result = original_propose(candidate_path, gate_path, ledger_path, timeout)
        now[0] += proposal_seconds
        return result

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 315.0, "invoke_installed": timed_installed,
        "invoke_propose": timed_propose, "retain_source_ledger_check_bytes": retain_checked_receipt,
    })
    monkeypatch.setattr(host_module, "_invoke_host", timed_host)
    if retention_seconds or proposal_seconds == 16.0:
        with pytest.raises(host_module.HostCandidateFlowError, match="failed closed|deadline expired"):
            host_module.run_host_candidate_flow(flow)
    else:
        assert host_module.run_host_candidate_flow(flow).returncode == 0

    stage = flow.observation_sink
    assert stage["model_window_seconds"] == 300.0
    assert stage["operational_timeout_seconds"] == 315.0
    assert stage["whole_journey_diagnostic_cap_seconds"] == 660.0
    assert stage["candidate_completion_reserve_seconds"] == 15.0
    assert stage["source_ledger_elapsed_seconds"] == 270.0
    assert list(repo.iterdir()) == []
    assert stage["host_workspace_cleaned"] is True
    assert stage["candidate_temp_cleaned"] is True
    if retention_seconds:
        assert len(hosts) == 3
        assert proposals == []
        assert proposal_timeouts == []
        assert stage["whole_journey_seconds"] == 645.0
        assert stage["status"] == "failed"
        assert stage["stage"] == "host"
    else:
        assert [call[2] for call in hosts] == [300.0, 300.0, 120.0, 264.0]
        assert proposal_timeouts == [16.0]
        assert stage["source_duty_verifier_elapsed_seconds"] == 110.0
        assert stage["whole_journey_seconds"] == 644.0 + proposal_seconds
        assert stage["proposal_phase_elapsed_seconds"] == 264.0 + proposal_seconds
        assert stage["status"] == ("passed" if proposal_seconds == 1.0 else "failed")
        assert stage["whole_journey_deadline_status"] == ("within" if proposal_seconds == 1.0 else "expired")
