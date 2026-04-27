from __future__ import annotations

from odylith.runtime.governance.delivery import scope_signal_ladder


def test_build_scope_signal_caps_generated_only_churn_to_r0() -> None:
    signal = scope_signal_ladder.build_scope_signal(
        feature_vector={
            "has_any_signal": True,
            "generated_only_churn": True,
        }
    )

    assert signal["rung"] == "R0"
    assert signal["token"] == "suppressed_noise"
    assert signal["budget_class"] == scope_signal_ladder.BUDGET_CLASS_NONE


def test_build_scope_signal_caps_governance_only_change_to_r1() -> None:
    signal = scope_signal_ladder.build_scope_signal(
        feature_vector={
            "has_any_signal": True,
            "governance_only_local_change": True,
        }
    )

    assert signal["rung"] == "R1"
    assert signal["token"] == "background_trace"
    assert signal["budget_class"] == scope_signal_ladder.BUDGET_CLASS_CACHE_ONLY


def test_build_scope_signal_promotes_verified_local_to_r2() -> None:
    signal = scope_signal_ladder.build_scope_signal(
        feature_vector={
            "has_any_signal": True,
            "narrow_verified_signal": True,
        }
    )

    assert signal["rung"] == "R2"
    assert signal["token"] == "verified_local"
    assert signal["promoted_default"] is False


def test_build_scope_signal_promotes_active_scope_to_r3() -> None:
    signal = scope_signal_ladder.build_scope_signal(
        feature_vector={
            "has_any_signal": True,
            "implementation_evidence": True,
            "meaningful_scope_activity": True,
        }
    )

    assert signal["rung"] == "R3"
    assert signal["token"] == "active_scope"
    assert signal["promoted_default"] is True
    assert signal["budget_class"] == scope_signal_ladder.BUDGET_CLASS_FAST_SIMPLE


def test_build_scope_signal_promotes_actionable_priority_to_r4() -> None:
    signal = scope_signal_ladder.build_scope_signal(
        feature_vector={
            "has_any_signal": True,
            "implementation_evidence": True,
            "open_warning": True,
        }
    )

    assert signal["rung"] == "R4"
    assert signal["token"] == "actionable_priority"
    assert signal["budget_class"] == scope_signal_ladder.BUDGET_CLASS_ESCALATED_REASONING


def test_build_scope_signal_promotes_proof_blocker_to_r5() -> None:
    signal = scope_signal_ladder.build_scope_signal(
        feature_vector={
            "has_any_signal": True,
            "proof_blocker": True,
        }
    )

    assert signal["rung"] == "R5"
    assert signal["token"] == "blocking_frontier"


def test_build_scope_signal_rolls_up_multiple_verified_children_to_r3() -> None:
    child = scope_signal_ladder.build_scope_signal(
        feature_vector={
            "has_any_signal": True,
            "narrow_verified_signal": True,
        }
    )
    parent = scope_signal_ladder.build_scope_signal(
        feature_vector={"has_any_signal": False},
        child_signals=[child, child],
    )

    assert parent["rung"] == "R3"
    assert parent["promoted_default"] is True


def test_budget_class_provider_gate_rejects_r0_to_r3() -> None:
    for rank in range(0, 4):
        rung, token, _label = scope_signal_ladder._rung_parts(rank)  # noqa: SLF001
        if rank == 0:
            budget_class = scope_signal_ladder.BUDGET_CLASS_NONE
        elif rank in {1, 2}:
            budget_class = scope_signal_ladder.BUDGET_CLASS_CACHE_ONLY
        else:
            budget_class = scope_signal_ladder.BUDGET_CLASS_FAST_SIMPLE
        assert not scope_signal_ladder.budget_class_allows_fresh_provider(budget_class)


def test_budget_class_provider_gate_allows_r4_and_r5() -> None:
    assert scope_signal_ladder.budget_class_allows_fresh_provider(scope_signal_ladder.BUDGET_CLASS_ESCALATED_REASONING)
