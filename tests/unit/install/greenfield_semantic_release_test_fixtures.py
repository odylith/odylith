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
from greenfield_semantic_pipeline_receipts import PIPELINE_VERSION, pipeline_receipt
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
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_author_profile,
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


def pipeline_receipt_fixture(
    packet: dict[str, Any],
    *,
    prompt: str,
    case_id: str,
    assignment: dict[str, Any] | None = None,
    host_profile: str = "codex",
    tier: str = "standard",
    predecessor: str = "",
) -> dict[str, Any]:
    """Build one exact author receipt around unchanged semantic bytes."""

    wall_ms = 50_000 if tier == "standard" else 70_000
    graph = deepcopy(packet["source_meaning_graph"])
    graph_sha256 = str(packet["source_meaning_sha256"])
    author_run = deepcopy(packet["author_run"])
    profile = standard_author_profile(host_profile, 0)
    author_run["host_profile"] = host_profile
    author_run["model"] = profile["model"]
    author_run["reasoning_effort"] = profile["reasoning_effort"]
    normalized_packet = deepcopy(packet)
    normalized_packet["author_run"] = deepcopy(author_run)
    author = {
        "stage": "source_meaning_author",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": author_run["model"],
        "reasoning_effort": author_run["reasoning_effort"],
        "status": "completed",
        "failure_kind": "",
        "failure": "",
        "usage": {"input_tokens": 100, "output_tokens": 200},
        "wall_ms": 12_000,
        "model_call_count": 1,
        "graph": graph,
        "graph_sha256": graph_sha256,
        "author_run": author_run,
    }
    outcome = (
        "clarify"
        if packet["semantic_intent"]["status"] == "clarification_required"
        else "commit"
    )
    transaction = (
        None
        if outcome == "clarify"
        else verified_transaction_receipt_fixture(normalized_packet, prompt=prompt)
    )
    return pipeline_receipt(
        case_id=case_id,
        status="completed",
        outcome=outcome,
        wall_ms=wall_ms,
        host_profile=host_profile,
        budget={
            "tier": tier,
            "prior_standard_failure_sha256": predecessor,
            "evidence_assignment": deepcopy(assignment),
        },
        author=author,
        packet=normalized_packet,
        transaction=transaction,
        failed_stage="",
        failure="",
    )


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
    "pipeline_receipt_fixture",
    "verified_transaction_receipt_fixture",
]
