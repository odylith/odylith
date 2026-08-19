"""Shared exact fixtures for semantic release evidence contracts."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import tempfile
from typing import Any

from greenfield_semantic_release_support import DETERMINISTIC_LAW_REPORT_VERSION
from greenfield_semantic_release_support import REQUIRED_DETERMINISTIC_LAW_IDS
from greenfield_semantic_release_support import canonical_sha256
from greenfield_semantic_deterministic_law_contract import DETERMINISTIC_LAW_EVIDENCE_VERSION
from greenfield_semantic_deterministic_law_contract import deterministic_law_command
from greenfield_semantic_pipeline_evidence import ACTIVE_EVIDENCE_PLAN_VERSION
from greenfield_semantic_pipeline_receipts import PIPELINE_VERSION
from greenfield_semantic_release_evaluation import CANDIDATE_BUNDLE_VERSION
from greenfield_semantic_standard_pipeline_experiment import _compile_packet
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    SEMANTIC_EXECUTION_EVIDENCE_VERSION,
)


def deterministic_law_report_fixture(revision: str) -> dict[str, Any]:
    """Build one internally consistent report with inspectable execution evidence."""

    results = []
    for law_id in REQUIRED_DETERMINISTIC_LAW_IDS:
        evidence = {
            "version": DETERMINISTIC_LAW_EVIDENCE_VERSION,
            "implementation_revision": revision,
            "law_id": law_id,
            "command": deterministic_law_command(
                law_id=law_id, python_executable="python",
            ),
            "returncode": 0,
            "duration_ms": 1,
            "stdout_sha256": "c" * 64,
            "stderr_sha256": "d" * 64,
        }
        results.append(
            {
                "law_id": law_id,
                "status": "passed",
                "evidence": evidence,
                "evidence_sha256": canonical_sha256(evidence),
            }
        )
    return {
        "version": DETERMINISTIC_LAW_REPORT_VERSION,
        "implementation_revision": revision,
        "contracts": {
            "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
            "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
            "development_evidence_plan_version": ACTIVE_EVIDENCE_PLAN_VERSION,
            "development_author_segment_version": PIPELINE_VERSION,
            "mechanism_evidence_version": SEMANTIC_EXECUTION_EVIDENCE_VERSION,
            "candidate_bundle_version": CANDIDATE_BUNDLE_VERSION,
        },
        "required_law_ids": list(REQUIRED_DETERMINISTIC_LAW_IDS),
        "results": results,
    }


def verified_transaction_receipt_fixture(
    packet: dict[str, Any], *, prompt: str
) -> dict[str, Any]:
    """Compile and cache real hash-bound transaction bytes for receipt tests."""

    packet_json = json.dumps(packet, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return deepcopy(_verified_transaction_receipt(packet_json, prompt))


@lru_cache(maxsize=16)
def _verified_transaction_receipt(packet_json: str, prompt: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="odylith-receipt-fixture-") as temporary:
        return _compile_packet(
            packet=json.loads(packet_json),
            prompt=prompt,
            repo_root=Path(temporary) / "greenfield-evidence-repository",
        )


__all__ = [
    "deterministic_law_report_fixture",
    "verified_transaction_receipt_fixture",
]
