from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from greenfield_semantic_pipeline_evidence import (
    prepare_active_evidence_plan,
    require_active_evidence_plan,
    require_successful_pipeline_evidence,
)
from greenfield_semantic_pipeline_receipts import (
    PIPELINE_VERSION,
    bounded_receipt,
)
from greenfield_semantic_release_support import greenfield_runtime_source_fingerprint
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    semantic_execution_evidence,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    verified_transaction_receipt_fixture,
)


def test_active_standard_pipeline_evidence_binds_packet_host_calls_and_tier() -> None:
    packet = semantic_intent_packet()
    receipt = _standard_receipt(packet)

    normalized, metadata = require_successful_pipeline_evidence(
        receipt,
        case_id="case-1",
        prompt=SEMANTIC_PROMPT,
        semantic_artifact=packet,
    )

    assert normalized == receipt
    assert metadata["execution_tier"] == "standard"
    assert metadata["model_calls"] == 4
    assert metadata["restarts"] == 0


@pytest.mark.parametrize(
    "mutation",
    ["mechanism", "source_bytes", "host", "model", "stage", "calls", "packet"],
)
def test_active_pipeline_evidence_rejects_custody_drift(mutation: str) -> None:
    packet = semantic_intent_packet()
    receipt = _standard_receipt(packet)
    if mutation == "mechanism":
        receipt["mechanism_execution"]["mechanism_id"] = "retired-two-stage"
    elif mutation == "source_bytes":
        receipt["mechanism_execution"]["implementation_fingerprint_sha256"] = "0" * 64
    elif mutation == "host":
        receipt["graph_completion"]["host_profile"] = "claude"
    elif mutation == "model":
        receipt["graph_completion"]["model"] = "unassigned-model"
    elif mutation == "stage":
        receipt["graph_completion"]["stage"] = "materiality_critic"
    elif mutation == "calls":
        receipt["source_graph"]["model_call_count"] = 1
    else:
        receipt["packet"] = {**packet, "evidence_sha256": "0" * 64}

    with pytest.raises(ValueError):
        require_successful_pipeline_evidence(
            receipt,
            case_id="case-1",
            prompt=SEMANTIC_PROMPT,
            semantic_artifact=packet,
        )


def test_rescue_pipeline_evidence_preserves_typed_predecessor_binding() -> None:
    packet = semantic_intent_packet()
    attempt = _standard_receipt(packet, tier="rescue", predecessor="a" * 64)
    wrapper = bounded_receipt(
        case_id="case-1",
        tier="rescue",
        wall_ms=70_001,
        attempt=attempt,
    )

    _, metadata = require_successful_pipeline_evidence(
        wrapper,
        case_id="case-1",
        prompt=SEMANTIC_PROMPT,
        semantic_artifact=packet,
    )
    assert metadata["execution_tier"] == "rescue"
    assert metadata["total_wall_ms"] == 70_001

    drifted = deepcopy(wrapper)
    drifted["attempt"]["mechanism_execution"][
        "prior_standard_failure_sha256"
    ] = "b" * 64
    with pytest.raises(ValueError, match="rescue wrapper changes"):
        require_successful_pipeline_evidence(
            drifted,
            case_id="case-1",
            prompt=SEMANTIC_PROMPT,
            semantic_artifact=packet,
        )


def test_active_evidence_plan_freezes_every_prompt_and_host_before_runs(
    tmp_path: Path,
) -> None:
    corpus = {
        "cases": [
            {"case_id": "case-1", "prompt": SEMANTIC_PROMPT},
            {"case_id": "case-2", "prompt": SEMANTIC_PROMPT + " Again."},
        ],
        "annotations": [{"must_not_be_read_by_plan": True}],
    }
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
    plan = prepare_active_evidence_plan(
        corpus_path=corpus_path,
        host_profiles=["codex", "claude"],
        output_path=tmp_path / "plan.json",
    )
    verified = require_active_evidence_plan(
        plan,
        corpus=corpus,
        corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
    )

    assert [row["host_profile"] for row in verified["cases"]] == [
        "codex",
        "claude",
    ]
    assert verified["implementation_fingerprint_sha256"] == (
        greenfield_runtime_source_fingerprint()
    )
    packet = semantic_intent_packet()
    receipt = _standard_receipt(packet, assignment=verified["cases"][0])
    require_successful_pipeline_evidence(
        receipt,
        case_id="case-1",
        prompt=SEMANTIC_PROMPT,
        semantic_artifact=packet,
        assignment=verified["cases"][0],
    )

    drifted = deepcopy(plan)
    drifted["cases"][0]["host_profile"] = "claude"
    with pytest.raises(ValueError, match="frozen binding"):
        require_active_evidence_plan(
            drifted,
            corpus=corpus,
            corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        )

    drifted = deepcopy(plan)
    drifted["implementation_fingerprint_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="frozen contract"):
        require_active_evidence_plan(
            drifted,
            corpus=corpus,
            corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        )


def _standard_receipt(
    packet: dict,
    *,
    tier: str = "standard",
    predecessor: str = "",
    assignment: dict | None = None,
) -> dict:
    wall_ms = 50_000 if tier == "standard" else 70_000
    execution = semantic_execution_evidence(
        host_profile="codex",
        tier=tier,
        status="completed",
        outcome="commit",
        wall_ms=wall_ms,
        model_call_count=4,
        restart_count=0,
        implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
        prior_standard_failure_sha256=predecessor,
    )
    return {
        "version": PIPELINE_VERSION,
        "case_id": "case-1",
        "status": "completed",
        "outcome": "commit",
        "wall_ms": wall_ms,
        "budget": {"tier": tier},
        "materiality_critic": {
            "stage": "materiality_critic",
            "case_id": "case-1",
            "host_profile": "codex",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "model_call_count": 1,
            "validation_status": "passed",
            "prompt_sha256": hashlib.sha256(
                SEMANTIC_PROMPT.encode("utf-8")
            ).hexdigest(),
        },
        "source_graph": {
            "stage": "source_graph",
            "case_id": "case-1",
            "host_profile": "codex",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "low",
            "model_call_count": 2,
            "validation_status": "passed",
            "authority_used": True,
        },
        "graph_completion": {
            "stage": "graph_completion",
            "case_id": "case-1",
            "host_profile": "codex",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "low",
            "model_call_count": 1,
            "validation_status": "passed",
        },
        "materiality_assessment": deepcopy(packet["materiality_assessment"]),
        "packet": deepcopy(packet),
        "transaction": verified_transaction_receipt_fixture(
            packet, prompt=SEMANTIC_PROMPT
        ),
        "failed_stage": "",
        "failure": "",
        "model_call_count": 4,
        "restart_count": 0,
        "total_tokens": 200,
        "mechanism_execution": execution,
        "evidence_assignment": deepcopy(assignment),
    }
