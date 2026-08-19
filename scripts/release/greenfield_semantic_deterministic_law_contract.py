"""Auditable execution contract for revision-bound Greenfield release laws."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from greenfield_semantic_release_support import DETERMINISTIC_LAW_REPORT_VERSION
from greenfield_semantic_release_support import REQUIRED_DETERMINISTIC_LAW_IDS
from greenfield_semantic_release_support import canonical_sha256
from greenfield_semantic_release_support import exact_keys
from greenfield_semantic_release_support import mapped_rows
from greenfield_semantic_release_support import mapping
from greenfield_semantic_release_support import positive_integer
from greenfield_semantic_release_support import require_sha256
from greenfield_semantic_release_support import text
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
)


DETERMINISTIC_LAW_EVIDENCE_VERSION = "odylith.greenfield.deterministic-law-evidence.v1"
DETERMINISTIC_LAW_TEST_TARGETS = {
    "no_post_confirm_semantic_or_model_work": (
        "tests/unit/runtime/test_greenfield_graph_authority_severance.py",
        "tests/unit/runtime/test_greenfield_transaction_provenance.py::test_create_router_imports_no_preconfirm_or_semantic_interpreter",
        "tests/unit/runtime/test_greenfield_transaction_provenance.py::test_commit_loader_has_no_semantic_authority_imports",
    ),
    "exact_sealed_byte_publication": (
        "tests/unit/runtime/test_greenfield_transaction_provenance.py::test_sealed_commit_loader_rejects_tampered_transaction_bytes",
        "tests/unit/runtime/test_greenfield_transaction_provenance.py::test_sealed_commit_loader_rejects_receipt_byte_drift",
        "tests/unit/runtime/test_greenfield_transaction_provenance.py::test_commit_reloads_receipted_bytes_instead_of_using_a_mutable_loaded_projection",
        "tests/unit/runtime/test_greenfield_generation_store.py",
    ),
    "no_unsupported_accepted_facts_at_type_boundary": (
        "tests/unit/runtime/test_greenfield_semantic_graph_v4_contract.py",
        "tests/unit/runtime/test_greenfield_semantic_materiality_contract.py",
    ),
    "idempotent_retry": (
        "tests/unit/runtime/test_greenfield_commit_journal.py::test_same_hash_retry_discards_an_empty_prewrite_journal_orphan",
        "tests/unit/runtime/test_greenfield_commit_journal.py::test_recovery_rolls_back_partial_applying_entry_before_a_retry",
        "tests/unit/runtime/test_greenfield_commit_journal.py::test_same_hash_retry_returns_the_durable_result_without_reapplying",
    ),
    "no_temporary_paths": (
        "tests/unit/runtime/test_greenfield_repository_write_set.py::test_atomic_write_removes_temp_sibling_when_interrupted_after_write",
        "tests/unit/runtime/test_greenfield_commit_journal.py::test_commit_stages_atomic_writes_outside_governed_roots",
        "tests/unit/runtime/test_greenfield_pending_transaction_store.py::test_pending_transaction_staging_failure_has_no_visible_partial_package",
    ),
    "no_destructive_clipping": (
        "tests/unit/runtime/test_greenfield_semantic_projection_plan.py",
        "tests/unit/runtime/test_greenfield_semantic_artifact_consumers.py",
    ),
    "no_partial_visible_generation_under_injected_failure": (
        "tests/unit/runtime/test_greenfield_repository_write_set.py::test_repository_write_set_rolls_back_mid_write_failures",
        "tests/unit/runtime/test_greenfield_repository_write_set.py::test_repository_write_set_readback_failure_rolls_back",
        "tests/unit/runtime/test_greenfield_managed_mutation_boundary.py::test_failed_writer_does_not_supersede_or_expose_partial_live_tree",
        "tests/unit/runtime/test_greenfield_commit_journal.py::test_sigkill_after_first_sealed_write_recovers_the_preconfirm_tree",
    ),
}

if tuple(DETERMINISTIC_LAW_TEST_TARGETS) != REQUIRED_DETERMINISTIC_LAW_IDS:
    raise RuntimeError("deterministic law test ownership does not match the release law set")


def deterministic_law_command(*, law_id: str, python_executable: str) -> list[str]:
    """Return the exact one-shot command owned by a deterministic law."""

    targets = DETERMINISTIC_LAW_TEST_TARGETS.get(law_id)
    if targets is None:
        raise RuntimeError(f"deterministic law lacks an executable test owner: {law_id}")
    executable = text(
        python_executable, f"deterministic law {law_id} Python executable", maximum=2_000,
    )
    return [executable, "-m", "pytest", "-q", *targets, "--tb=short"]


def require_deterministic_law_report(
    value: Any,
    *,
    implementation_revision: str,
    candidate_bundle_version: str,
    development_evidence_plan_version: str,
    development_author_segment_version: str,
    mechanism_evidence_version: str,
) -> dict[str, Any]:
    """Validate executable proof and custody for every deterministic law."""

    report = mapping(value, "deterministic law report")
    exact_keys(
        report,
        {"version", "implementation_revision", "contracts", "required_law_ids", "results"},
        "deterministic law report",
    )
    if report.get("version") != DETERMINISTIC_LAW_REPORT_VERSION:
        raise RuntimeError("deterministic law report uses an unsupported version")
    if report.get("implementation_revision") != implementation_revision:
        raise RuntimeError("deterministic law report is stale for the implementation revision")
    expected_contracts = {
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
        "development_evidence_plan_version": development_evidence_plan_version,
        "development_author_segment_version": development_author_segment_version,
        "mechanism_evidence_version": mechanism_evidence_version,
        "candidate_bundle_version": candidate_bundle_version,
    }
    contracts = mapping(report.get("contracts"), "deterministic law contracts")
    exact_keys(contracts, set(expected_contracts), "deterministic law contracts")
    if contracts != expected_contracts:
        raise RuntimeError("deterministic law report is stale for the release contracts")
    if report.get("required_law_ids") != list(REQUIRED_DETERMINISTIC_LAW_IDS):
        raise RuntimeError("deterministic law report changes the required law set")
    rows = mapped_rows(report.get("results"), "deterministic law results")
    if len(rows) != len(REQUIRED_DETERMINISTIC_LAW_IDS):
        raise RuntimeError("deterministic law report lacks exact law coverage")
    normalized = [
        _require_result(raw, law_id=law_id, implementation_revision=implementation_revision)
        for law_id, raw in zip(REQUIRED_DETERMINISTIC_LAW_IDS, rows, strict=True)
    ]
    return {
        "version": DETERMINISTIC_LAW_REPORT_VERSION,
        "implementation_revision": implementation_revision,
        "contracts": expected_contracts,
        "required_law_ids": list(REQUIRED_DETERMINISTIC_LAW_IDS),
        "results": normalized,
    }


def _require_result(
    value: Mapping[str, Any], *, law_id: str, implementation_revision: str,
) -> dict[str, Any]:
    row = mapping(value, f"deterministic law {law_id}")
    exact_keys(
        row,
        {"law_id", "status", "evidence", "evidence_sha256"},
        f"deterministic law {law_id}",
    )
    if row.get("law_id") != law_id or row.get("status") != "passed":
        raise RuntimeError(f"deterministic law did not pass: {law_id}")
    evidence = _require_evidence(
        row.get("evidence"), law_id=law_id, implementation_revision=implementation_revision,
    )
    evidence_sha256 = require_sha256(
        row.get("evidence_sha256"), f"deterministic law {law_id} evidence",
    )
    if evidence_sha256 != canonical_sha256(evidence):
        raise RuntimeError(f"deterministic law evidence hash mismatch: {law_id}")
    return {
        "law_id": law_id,
        "status": "passed",
        "evidence": evidence,
        "evidence_sha256": evidence_sha256,
    }


def _require_evidence(
    value: Any, *, law_id: str, implementation_revision: str,
) -> dict[str, Any]:
    evidence = mapping(value, f"deterministic law {law_id} execution evidence")
    exact_keys(
        evidence,
        {
            "version", "implementation_revision", "law_id", "command", "returncode",
            "duration_ms", "stdout_sha256", "stderr_sha256",
        },
        f"deterministic law {law_id} execution evidence",
    )
    if evidence.get("version") != DETERMINISTIC_LAW_EVIDENCE_VERSION:
        raise RuntimeError(f"deterministic law evidence uses an unsupported version: {law_id}")
    if (
        evidence.get("implementation_revision") != implementation_revision
        or evidence.get("law_id") != law_id
        or evidence.get("returncode") != 0
    ):
        raise RuntimeError(f"deterministic law evidence does not prove its claimed pass: {law_id}")
    raw_command = evidence.get("command")
    if not isinstance(raw_command, list) or not raw_command:
        raise RuntimeError(f"deterministic law command must be a non-empty string array: {law_id}")
    command = [
        text(part, f"deterministic law {law_id} command", maximum=2_000)
        for part in raw_command
    ]
    if command != deterministic_law_command(law_id=law_id, python_executable=command[0]):
        raise RuntimeError(f"deterministic law command does not match its test owner: {law_id}")
    return {
        "version": DETERMINISTIC_LAW_EVIDENCE_VERSION,
        "implementation_revision": implementation_revision,
        "law_id": law_id,
        "command": command,
        "returncode": 0,
        "duration_ms": positive_integer(
            evidence.get("duration_ms"), f"deterministic law {law_id} duration",
        ),
        "stdout_sha256": require_sha256(
            evidence.get("stdout_sha256"), f"deterministic law {law_id} stdout",
        ),
        "stderr_sha256": require_sha256(
            evidence.get("stderr_sha256"), f"deterministic law {law_id} stderr",
        ),
    }


__all__ = [
    "DETERMINISTIC_LAW_EVIDENCE_VERSION",
    "DETERMINISTIC_LAW_TEST_TARGETS",
    "deterministic_law_command",
    "require_deterministic_law_report",
]
