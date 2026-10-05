"""Synthetic gate-first observations for provider-free release tests."""

from __future__ import annotations

from pathlib import Path
import sys


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from odylith.runtime.domain_intelligence.greenfield_host_transport import (HOST_NATIVE_ARGV_ARGUMENT_COUNT)
from odylith.runtime.domain_intelligence.greenfield_host_transport import (HOST_NATIVE_ARGV_SHAPE_SHA256)
from odylith.runtime.domain_intelligence.greenfield_host_flow import HOST_NATIVE_MATRIX_OBSERVATION_VERSION
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION,
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
)


def _receipt() -> dict[str, object]:
    return {
        "version": HOST_CANDIDATE_RECEIPT_VERSION,
        "contract_version": HOST_CANDIDATE_CONTRACT_VERSION,
        "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "source_sha256": "1" * 64,
        "raw_candidate_sha256": "2" * 64,
        "canonical_candidate_sha256": "3" * 64,
        "source_duty_ledger_sha256": "0" * 64,
        "source_duty_decision_set_sha256": "f" * 64,
        "source_duty_verifier_task_sha256": "e" * 64,
        "source_duty_binding_sha256": "a" * 64,
    }


def sealed_profile_observation(
    profile_id: str,
    *,
    shared_timeout: float | None = None,
) -> dict[str, object]:
    del profile_id, shared_timeout
    return {
        "origin": "host_native",
        "host_candidate": _receipt(),
        "runtime_semantic_model_call_count": 0,
    }


def production_stage_observation(
    profile_id: str,
    *,
    response_kind: str = "authored",
    shared_timeout: float | None = None,
    evidence_text: str | None = None,
) -> dict[str, object]:
    """Return the closed release-stage shape without dispatching a provider."""

    del evidence_text
    profile = get_greenfield_model_profile(profile_id)
    receipt = _receipt()
    clarification = response_kind == "clarification_required"
    host_request = {
        "version": "odylith.greenfield.host-argv-receipt.v1",
        "executable_sha256": "4" * 64,
        "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "output_schema_present": True,
        "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
    }
    stage = {
        "version": HOST_NATIVE_MATRIX_OBSERVATION_VERSION,
        "status": "passed",
        "host_invocations": 1 if clarification else 4,
        "authority_gate_host_invocations": 1,
        "source_ledger_host_invocations": 0 if clarification else 1,
        "source_duty_verifier_host_invocations": 0 if clarification else 1,
        "candidate_host_invocations": 0 if clarification else 1,
        "contract_command_invocations": 1,
        "authority_check_command_invocations": 1,
        "source_ledger_check_command_invocations": 0 if clarification else 2,
        "proposal_command_invocations": 0 if clarification else 1,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "model_profile_id": profile_id,
        "model_window_seconds": profile.model_timeout_seconds,
        "operational_timeout_seconds": profile.operational_timeout_seconds,
        "source_ledger_diagnostic_cap_seconds": 300.0,
        "source_duty_verifier_diagnostic_cap_seconds": 120.0,
        "whole_journey_diagnostic_cap_seconds": PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS,
        "candidate_completion_reserve_seconds": 15.0,
        "whole_journey_route": "odylith-greenfield-prepare.v1",
        "whole_journey_supervision": {"version": "odylith.greenfield.journey-supervision.v1",
                                     "guardian_pid": 12345, "cancellation_grace_seconds": 2.0},
        "whole_journey_bound_status": "diagnostic_unqualified",
        "whole_journey_elapsed_scope": "through_guardian_completion_record_and_final_clock_check_before_receipt_delivery",
        "whole_journey_deadline_status": "within",
        "authority_gate_request": host_request,
        "candidate_temp_cleaned": True,
        "authority_gate_temp_cleaned": True,
        "source_ledger_temp_cleaned": True,
        "source_duty_decision_temp_cleaned": True,
        "host_workspace_cleaned": True,
        "stage": "propose",
        "contract_returncode": 0,
        "contract_sha256": "5" * 64,
        "source_sha256": receipt["source_sha256"],
        "authority_gate_schema_sha256": "a" * 64,
        "authority_gate_returncode": 0,
        "authority_gate_output_sha256": "b" * 64,
        "authority_gate_output_bytes": 500,
        "authority_gate_decision": "clarify" if clarification else "admit",
        "authority_gate_temp_outside_repo": True,
        "authority_check_returncode": 0,
        "authority_check_stdout_sha256": "c" * 64,
        "authority_check_stderr_sha256": "d" * 64,
        "response_kind": response_kind,
        "proposal_mode": (
            "clarification_required"
            if response_kind == "clarification_required"
            else "product_create_transaction"
        ),
        "elapsed_seconds": (
            min(shared_timeout, 10.0) if shared_timeout is not None else 10.0
        ),
        "proposal_phase_elapsed_seconds": (
            min(shared_timeout, 10.0) if shared_timeout is not None else 10.0
        ),
        "whole_journey_seconds": (
            min(shared_timeout, 10.0) if shared_timeout is not None else 10.0
        ) + (0.0 if clarification else 30.0),
    }
    if not clarification:
        stage.update({
            "source_ledger_request": dict(host_request),
            "source_ledger_schema_sha256": "e" * 64,
            "source_ledger_returncode": 0,
            "source_ledger_output_sha256": "f" * 64,
            "source_ledger_output_bytes": 300,
            "source_ledger_temp_outside_repo": True,
            "source_ledger_preflight_returncode": 0,
            "source_ledger_preflight_stdout_sha256": "0" * 64,
            "source_ledger_preflight_mode": "source_duty_preflight",
            "source_duty_verifier_request": dict(host_request),
            "source_duty_decision_schema_sha256": "a" * 64,
            "source_duty_verifier_returncode": 0,
            "source_duty_decision_output_sha256": "b" * 64,
            "source_duty_decision_output_bytes": 300,
            "source_completeness_verdict": "yes",
            "source_completeness_omission_count": 0,
            "source_duty_decision_temp_outside_repo": True,
            "source_ledger_check_returncode": 0,
            "source_ledger_check_stdout_sha256": "0" * 64,
            "source_ledger_check_mode": "source_duty_admitted",
            "source_ledger_elapsed_seconds": 20.0,
            "source_duty_verifier_elapsed_seconds": 10.0,
            "source_ledger_sha256": receipt["source_duty_ledger_sha256"],
            "source_duty_decision_set_sha256": receipt["source_duty_decision_set_sha256"],
            "source_duty_verifier_task_sha256": receipt["source_duty_verifier_task_sha256"],
            "host_request": dict(host_request),
            "candidate_schema_sha256": "6" * 64,
            "candidate_transport_version": HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION,
            "candidate_request_bytes": 2000,
            "candidate_request_sha256": "5" * 64,
            "host_returncode": 0,
            "host_stdout_bytes": 500,
            "host_stderr_bytes": 0,
            "raw_candidate_sha256": receipt["raw_candidate_sha256"],
            "host_output_sha256": "7" * 64,
            "host_output_bytes": 500,
            "candidate_temp_outside_repo": True,
            "proposal_returncode": 0,
            "proposal_stdout_sha256": "8" * 64,
            "proposal_stderr_sha256": "9" * 64,
        })
    return stage
