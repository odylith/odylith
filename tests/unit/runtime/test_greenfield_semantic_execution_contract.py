from __future__ import annotations

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    ACTIVE_SEMANTIC_MECHANISM_ID,
    completion_within_tier,
    require_semantic_execution_evidence,
    require_reusable_standard_handoff,
    semantic_execution_contract,
    semantic_execution_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_host_stage_profile,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    semantic_intent_packet,
)


IMPLEMENTATION_FINGERPRINT = "a" * 64


def test_active_mechanism_is_one_holistic_whole_graph_author() -> None:
    contract = semantic_execution_contract()

    assert ACTIVE_SEMANTIC_MECHANISM_ID == (
        "holistic_tagged_entity_effect_source_meaning"
    )
    assert contract["mechanism_id"] == ACTIVE_SEMANTIC_MECHANISM_ID
    topology = contract["topology"]
    assert topology["authoring_stages"] == [
        "one_holistic_source_meaning_author"
    ]
    assert topology["wave_order"] == "one_whole_graph_call"
    assert topology["candidate_selection"] == "none"
    assert topology["author_budget"] == "source_meaning_graph_at_most_54_seconds"
    assert topology["semantic_retries"] == 0
    assert topology["post_confirm_semantic_calls"] == 0
    assert contract["successful_model_call_counts"] == {
        "standard": {"commit": [1], "clarify": [1]},
        "rescue": {"commit": [1], "clarify": [1]},
        "explicit_deep": {"commit": [1], "clarify": [1]},
    }
    assert contract["automatic_deep_tier"] is False
    assert standard_host_stage_profile("codex")["authors"] == [
        {
            "role": "author",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
        },
    ]
    assert standard_host_stage_profile("claude")["authors"] == [
        {
            "role": "author",
            "model": "claude-opus-4-6",
            "reasoning_effort": "high",
        },
    ]


def test_sixty_is_strict_while_ninety_and_one_twenty_are_inclusive() -> None:
    assert completion_within_tier(tier="standard", wall_ms=59_999) is True
    assert completion_within_tier(tier="standard", wall_ms=60_000) is False
    assert completion_within_tier(tier="rescue", wall_ms=90_000) is True
    assert completion_within_tier(tier="rescue", wall_ms=90_001) is False
    assert completion_within_tier(tier="explicit_deep", wall_ms=120_000) is True
    assert completion_within_tier(tier="explicit_deep", wall_ms=120_001) is False


def test_success_evidence_enforces_one_call_and_zero_restarts() -> None:
    standard = semantic_execution_evidence(
        host_profile="codex",
        tier="standard",
        status="completed",
        outcome="commit",
        wall_ms=59_999,
        model_call_count=1,
        restart_count=0,
        implementation_fingerprint_sha256=IMPLEMENTATION_FINGERPRINT,
    )
    assert require_semantic_execution_evidence(standard) == standard

    for field, value, match in (
        ("wall_ms", 60_000, "exceeds"),
        ("model_call_count", 2, "model-call count"),
        ("restart_count", 1, "retry or restart"),
        ("automatic_deep_tier", True, "automatic deep"),
    ):
        drifted = deepcopy(standard)
        drifted[field] = value
        with pytest.raises(ValueError, match=match):
            require_semantic_execution_evidence(drifted)


def test_rescue_accepts_only_current_selected_graph_for_deterministic_finish() -> None:
    packet = semantic_intent_packet()
    graph = packet["source_meaning_graph"]
    author_run = packet["author_run"]
    predecessor = {
        "case_id": "case-1",
        "failed_stage": "deadline",
        "source_meaning_author": {
            "graph": graph,
            "graph_sha256": packet["source_meaning_sha256"],
            "author_run": author_run,
        },
        "packet": packet,
        "transaction": None,
        "mechanism_execution": semantic_execution_evidence(
            host_profile="codex",
            tier="standard",
            status="rescue_required",
            outcome="deterministic_finalize_required",
            wall_ms=55_000,
            model_call_count=1,
            restart_count=0,
            implementation_fingerprint_sha256=IMPLEMENTATION_FINGERPRINT,
        ),
    }

    assert len(require_reusable_standard_handoff(predecessor, case_id="case-1")) == 64
    drifted = deepcopy(predecessor)
    drifted["source_meaning_author"]["graph_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="reusable typed authority"):
        require_reusable_standard_handoff(drifted, case_id="case-1")


def test_explicit_deep_remains_operator_or_ci_only() -> None:
    deep = semantic_execution_evidence(
        host_profile="claude",
        tier="explicit_deep",
        status="completed",
        outcome="commit",
        wall_ms=120_000,
        model_call_count=1,
        restart_count=0,
        implementation_fingerprint_sha256=IMPLEMENTATION_FINGERPRINT,
    )
    assert deep["entry_reason"] == "explicit_operator_or_ci"
    assert deep["automatic_deep_tier"] is False


def test_old_critic_selector_and_merge_paths_are_absent() -> None:
    rendered = str(semantic_execution_contract())
    for retired in (
        "independent_source_semantic_critic",
        "source_pair_adjudicator",
        "candidate_repair_or_merge",
        "holistic_author_then_independent_critic",
    ):
        assert retired not in rendered
