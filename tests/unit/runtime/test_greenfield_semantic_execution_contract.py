from __future__ import annotations

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    ACTIVE_SEMANTIC_MECHANISM_ID,
    completion_within_tier,
    require_semantic_execution_evidence,
    require_typed_standard_failure,
    semantic_execution_contract,
    semantic_execution_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_clarification_packet,
    require_semantic_intent_packet,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_clarification_packet,
)


IMPLEMENTATION_FINGERPRINT = "a" * 64


def test_active_mechanism_declares_one_four_call_typed_graph_path() -> None:
    contract = semantic_execution_contract()

    assert contract["mechanism_id"] == ACTIVE_SEMANTIC_MECHANISM_ID
    assert contract["topology"] == {
        "first_wave": ["materiality_critic", "source_path", "source_boundary"],
        "first_wave_concurrency": "parallel",
        "terminal_author": {
            "commit": "typed_graph_completion_after_settled_materiality_and_source",
            "clarify": "independent_clarification_challenge_after_materiality",
        },
        "semantic_retries": 0,
        "post_confirm_semantic_calls": 0,
    }
    assert contract["successful_model_call_counts"] == {"commit": 4, "clarify": 4}
    assert contract["automatic_deep_tier"] is False


def test_sixty_is_strict_while_ninety_and_one_twenty_are_inclusive() -> None:
    assert completion_within_tier(tier="standard", wall_ms=59_999) is True
    assert completion_within_tier(tier="standard", wall_ms=60_000) is False
    assert completion_within_tier(tier="rescue", wall_ms=90_000) is True
    assert completion_within_tier(tier="rescue", wall_ms=90_001) is False
    assert completion_within_tier(tier="explicit_deep", wall_ms=120_000) is True
    assert completion_within_tier(tier="explicit_deep", wall_ms=120_001) is False


def test_success_evidence_enforces_tier_entry_calls_and_zero_restarts() -> None:
    standard = semantic_execution_evidence(
        host_profile="codex",
        tier="standard",
        status="completed",
        outcome="commit",
        wall_ms=59_999,
        model_call_count=4,
        restart_count=0,
        implementation_fingerprint_sha256=IMPLEMENTATION_FINGERPRINT,
    )
    assert require_semantic_execution_evidence(standard) == standard

    for field, value, match in (
        ("wall_ms", 60_000, "exceeds"),
        ("model_call_count", 3, "model-call count"),
        ("restart_count", 1, "retry or restart"),
        ("automatic_deep_tier", True, "automatic deep"),
    ):
        drifted = deepcopy(standard)
        drifted[field] = value
        with pytest.raises(ValueError, match=match):
            require_semantic_execution_evidence(drifted)


def test_rescue_requires_an_exact_typed_standard_failure() -> None:
    predecessor = {
        "case_id": "case-1",
        "mechanism_execution": semantic_execution_evidence(
            host_profile="codex",
            tier="standard",
            status="rescue_required",
            outcome="typed_standard_failure",
            wall_ms=45_000,
            model_call_count=4,
            restart_count=0,
            implementation_fingerprint_sha256=IMPLEMENTATION_FINGERPRINT,
        ),
    }
    predecessor_sha = require_typed_standard_failure(predecessor, case_id="case-1")
    rescue = semantic_execution_evidence(
        host_profile="codex",
        tier="rescue",
        status="completed",
        outcome="commit",
        wall_ms=90_000,
        model_call_count=4,
        restart_count=0,
        implementation_fingerprint_sha256=IMPLEMENTATION_FINGERPRINT,
        prior_standard_failure_sha256=predecessor_sha,
    )

    assert rescue["entry_reason"] == "typed_standard_failure"
    with pytest.raises(ValueError, match="another Greenfield case"):
        require_typed_standard_failure(predecessor, case_id="case-2")


def test_explicit_deep_cannot_be_claimed_as_automatic() -> None:
    deep = semantic_execution_evidence(
        host_profile="claude",
        tier="explicit_deep",
        status="completed",
        outcome="commit",
        wall_ms=120_000,
        model_call_count=4,
        restart_count=0,
        implementation_fingerprint_sha256=IMPLEMENTATION_FINGERPRINT,
    )
    assert deep["entry_reason"] == "explicit_operator_or_ci"
    assert deep["automatic_deep_tier"] is False

    drifted = deepcopy(deep)
    drifted["entry_reason"] = "automatic_quality_retry"
    with pytest.raises(ValueError, match="tier entry reason"):
        require_semantic_execution_evidence(drifted)


def test_clarification_packet_seals_only_the_one_question() -> None:
    assessment = semantic_clarification_packet()["materiality_assessment"]
    packet = build_semantic_clarification_packet(
        assessment,
        prompt=SEMANTIC_PROMPT,
        critic_run_id="critic-run",
        author_run_id="clarification-author-run",
        critic_host_profile="codex",
    )
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)

    assert verified.semantic_intent["status"] == "clarification_required"
    assert verified.semantic_intent["facts"] == []
    assert verified.semantic_intent["relations"] == []
    assert verified.product_facts is None
    assert all(
        row["decision"] == "reject_noise"
        for row in packet["source_candidate_adjudication"]["candidate_decisions"]
    )
