"""Synthetic gate-first observations for provider-free release tests."""

from __future__ import annotations

from pathlib import Path
import sys


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_ARGUMENT_COUNT
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_SHAPE_SHA256
from greenfield_matrix_host_candidate import HOST_NATIVE_MATRIX_OBSERVATION_VERSION
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
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
        "host_invocations": 1 if clarification else 2,
        "authority_gate_host_invocations": 1,
        "candidate_host_invocations": 0 if clarification else 1,
        "contract_command_invocations": 1,
        "authority_check_command_invocations": 1,
        "proposal_command_invocations": 0 if clarification else 1,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "model_profile_id": profile_id,
        "authority_gate_request": host_request,
        "candidate_temp_cleaned": True,
        "authority_gate_temp_cleaned": True,
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
    }
    if not clarification:
        stage.update({
            "host_request": dict(host_request),
            "candidate_schema_sha256": "6" * 64,
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
