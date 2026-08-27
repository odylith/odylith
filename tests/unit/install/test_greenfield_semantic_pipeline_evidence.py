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
from greenfield_semantic_pipeline_receipts import bounded_receipt, pipeline_receipt
from greenfield_semantic_release_support import greenfield_runtime_source_fingerprint
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_author_profile,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    verified_transaction_receipt_fixture,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


def test_active_standard_pipeline_evidence_binds_one_author_and_tier() -> None:
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
    assert metadata["model_calls"] == 1
    assert metadata["restarts"] == 0
    assert metadata["author_run_id"] == packet["author_run"]["run_id"]


def test_active_evidence_accepts_only_the_selected_unchanged_graph() -> None:
    packet = semantic_intent_packet()
    receipt = _standard_receipt(packet)

    normalized, _ = require_successful_pipeline_evidence(
        receipt,
        case_id="case-1",
        prompt=SEMANTIC_PROMPT,
        semantic_artifact=packet,
    )

    author = normalized["source_meaning_author"]
    assert author["graph"] == packet["source_meaning_graph"]
    assert author["graph_sha256"] == packet["source_meaning_sha256"]
    assert author["author_run"] == packet["author_run"]


@pytest.mark.parametrize(
    "mutation",
    [
        "mechanism",
        "source_bytes",
        "host",
        "model",
        "stage",
        "calls",
        "profile",
        "graph",
        "run",
        "packet",
    ],
)
def test_active_pipeline_evidence_rejects_custody_drift(mutation: str) -> None:
    packet = semantic_intent_packet()
    receipt = _standard_receipt(packet)
    author = receipt["source_meaning_author"]
    if mutation == "mechanism":
        receipt["mechanism_execution"]["mechanism_id"] = "retired-two-stage"
    elif mutation == "source_bytes":
        receipt["mechanism_execution"]["implementation_fingerprint_sha256"] = "0" * 64
    elif mutation == "host":
        author["author_run"]["host_profile"] = "claude"
    elif mutation == "model":
        author["author_run"]["model"] = "unassigned-model"
    elif mutation == "stage":
        author["stage"] = "parallel_graph_authors"
    elif mutation == "calls":
        author["model_call_count"] = 2
    elif mutation == "profile":
        author["reasoning_effort"] = "medium"
    elif mutation == "graph":
        author["graph_sha256"] = "0" * 64
    elif mutation == "run":
        author["author_run"]["run_id"] += ":drift"
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
        case_id="case-1", tier="rescue", wall_ms=70_001, attempt=attempt
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
    graph = deepcopy(packet["source_meaning_graph"])
    graph_sha256 = packet["source_meaning_sha256"]
    profile = standard_author_profile("codex", 0)
    author_run = {
        **deepcopy(packet["author_run"]),
        "model": profile["model"],
        "reasoning_effort": profile["reasoning_effort"],
    }
    normalized_packet = {**deepcopy(packet), "author_run": deepcopy(author_run)}
    author = {
        "stage": "source_meaning_author",
        "case_id": "case-1",
        "host_profile": "codex",
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
    return pipeline_receipt(
        case_id="case-1",
        status="completed",
        outcome="commit",
        wall_ms=wall_ms,
        host_profile="codex",
        budget={
            "tier": tier,
            "prior_standard_failure_sha256": predecessor,
            "evidence_assignment": deepcopy(assignment),
        },
        author=author,
        packet=normalized_packet,
        transaction=verified_transaction_receipt_fixture(
            normalized_packet, prompt=SEMANTIC_PROMPT
        ),
        failed_stage="",
        failure="",
    )
