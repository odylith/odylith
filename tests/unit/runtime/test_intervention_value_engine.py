from __future__ import annotations

import copy

import pytest

from odylith.runtime.intervention_engine import value_engine


def _option(
    *,
    option_id: str,
    label: str,
    duplicate_group: str,
    block_kind: str = "ambient",
    support_state: str = "supported",
    freshness_state: str = "current",
    claim_text: str = "",
    materiality: float = 0.92,
    actionability: float = 0.78,
    correctness: float = 0.94,
    action_payload: dict[str, object] | None = None,
    evidence: tuple[value_engine.SignalEvidence, ...] | None = None,
    semantic_signature: tuple[str, ...] | None = None,
) -> value_engine.VisibleInterventionOption:
    if evidence is None:
        evidence = (
            value_engine.SignalEvidence(
                source_kind="test",
                source_id=option_id,
                freshness="current",
                confidence=correctness,
                excerpt="useful signal",
                evidence_class="unit",
            ),
        )
    return value_engine.VisibleInterventionOption(
        option_id=option_id,
        proposed_label=label,
        block_kind=block_kind,
        markdown_text=f"**Odylith {label.title()}:** {claim_text or 'useful signal'}.",
        plain_text=f"Odylith {label.title()}: {claim_text or 'useful signal'}.",
        proof_required=label in {"observation", "proposal"},
        action_payload=action_payload or {},
        proposition=value_engine.SignalProposition(
            proposition_id=f"prop-{option_id}",
            claim_text=claim_text or f"{label} useful signal",
            proposition_kind=label,
            support_state=support_state,
            duplicate_key=duplicate_group,
            freshness_state=freshness_state,
            semantic_signature=semantic_signature if semantic_signature is not None else (option_id, label),
            evidence=evidence,
        ),
        features=value_engine.InterventionValueFeatures(
            correctness_confidence=correctness,
            materiality=materiality,
            actionability=actionability,
            novelty=0.72,
            timing_relevance=0.88,
            user_need=0.84,
            visibility_need=0.76,
            interruption_cost=0.04,
            redundancy_cost=0.0,
            uncertainty_penalty=0.01,
            brand_risk=0.01,
        ),
    )


def test_value_engine_selects_multiple_distinct_signals_without_duplicates() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(option_id="risk", label="risks", duplicate_group="invariant:chat-proof"),
            _option(option_id="history", label="history", duplicate_group="bug:CB-122"),
            _option(option_id="insight", label="insight", duplicate_group="workstream:B-096"),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_labels() == ["risks", "history", "insight"]
    assert decision.metric_summary["selected_count"] == 3
    assert decision.metric_summary["live_block_budget"] >= 3
    assert decision.no_output_reason == ""


def test_value_engine_dedupes_ambient_against_observation_and_keeps_stronger_block() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="risk",
                label="risks",
                duplicate_group="invariant:visible",
                materiality=0.84,
                actionability=0.62,
            ),
            _option(
                option_id="observation",
                label="observation",
                block_kind="observation",
                duplicate_group="invariant:visible",
                materiality=0.95,
                actionability=0.9,
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_labels() == ["observation"]
    suppressed_by_id = {
        row["candidate_id"]: row["suppressed_reason"]
        for row in decision.suppressed_candidates
    }
    assert suppressed_by_id["risk"] == "duplicate_visible_proposition"


def test_value_engine_requires_observation_for_proposal() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="proposal",
                label="proposal",
                block_kind="proposal",
                duplicate_group="proposal:radar:B-096",
                actionability=1.0,
                action_payload={"actions": [{"surface": "radar", "target_id": "B-096", "operation": "update"}]},
            )
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_candidates == []
    assert decision.suppressed_candidates[0]["suppressed_reason"] == "proposal_requires_observation"


def test_value_engine_suppresses_unsupported_stale_hidden_and_generated_signals() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(option_id="unsupported", label="insight", duplicate_group="unsupported", support_state="unsupported"),
            _option(option_id="stale", label="history", duplicate_group="stale", freshness_state="stale"),
            _option(option_id="hidden", label="risks", duplicate_group="hidden", freshness_state="hidden_only"),
            _option(
                option_id="generated",
                label="observation",
                block_kind="observation",
                duplicate_group="generated",
                freshness_state="generated_only",
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons == {
        "unsupported": "unsupported_signal",
        "stale": "stale_signal",
        "hidden": "hidden_only_signal",
        "generated": "generated_only_signal",
    }
    assert decision.no_output_reason == "no_high_value_supported_signal"


def test_value_engine_suppresses_contradictory_and_unknown_visible_labels() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(option_id="contradictory", label="risks", duplicate_group="contradictory", support_state="contradictory"),
            _option(option_id="assist", label="assist", duplicate_group="assist"),
            _option(option_id="status", label="status", duplicate_group="status"),
            _option(option_id="unknown-kind", label="insight", duplicate_group="unknown-kind", block_kind="diagnostic_panel"),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons == {
        "contradictory": "contradictory_signal",
        "assist": "unknown_visible_label",
        "status": "unknown_visible_label",
        "unknown-kind": "unknown_block_kind",
    }
    assert decision.selected_candidates == []


def test_value_engine_rejects_label_and_block_kind_mismatches() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(option_id="insight-proposal-kind", label="insight", duplicate_group="mismatch:insight", block_kind="proposal"),
            _option(option_id="observation-ambient-kind", label="observation", duplicate_group="mismatch:observation", block_kind="ambient"),
            _option(
                option_id="proposal-ambient-kind",
                label="proposal",
                duplicate_group="mismatch:proposal",
                block_kind="ambient",
                action_payload={"actions": [{"surface": "casebook", "target_id": "CB-122", "operation": "update"}]},
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons == {
        "insight-proposal-kind": "label_block_kind_mismatch",
        "observation-ambient-kind": "label_block_kind_mismatch",
        "proposal-ambient-kind": "label_block_kind_mismatch",
    }
    assert decision.selected_candidates == []


def test_value_engine_rejects_high_score_without_grounding_evidence() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="no-evidence",
                label="insight",
                duplicate_group="adversarial:no-evidence",
                correctness=1.0,
                materiality=1.0,
                actionability=1.0,
                evidence=(),
            )
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_candidates == []
    assert decision.suppressed_candidates[0]["suppressed_reason"] == "missing_evidence_signal"
    assert decision.metric_summary["evidence_gated_count"] == 1


def test_value_engine_rejects_low_confidence_evidence_even_with_high_declared_correctness() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="weak-evidence",
                label="risks",
                duplicate_group="adversarial:weak-evidence",
                correctness=1.0,
                materiality=1.0,
                actionability=1.0,
                evidence=(
                    value_engine.SignalEvidence(
                        source_kind="test",
                        source_id="weak-evidence",
                        freshness="current",
                        confidence=0.2,
                        excerpt="weak assertion",
                        evidence_class="negative_control",
                    ),
                ),
            )
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_candidates == []
    assert decision.suppressed_candidates[0]["suppressed_reason"] == "weak_evidence_signal"


def test_value_engine_rejects_mixed_non_current_evidence_even_with_anchor_refs() -> None:
    option = value_engine.VisibleInterventionOption(
        option_id="mixed-non-current",
        proposed_label="history",
        block_kind="ambient",
        markdown_text="**Odylith History:** Non-current evidence cannot prove a current chat signal.",
        plain_text="Odylith History: Non-current evidence cannot prove a current chat signal.",
        proposition=value_engine.SignalProposition(
            proposition_id="prop-mixed-non-current",
            claim_text="Non-current evidence cannot prove a current chat signal.",
            proposition_kind="history",
            support_state="supported",
            anchor_refs=(
                {
                    "kind": "bug",
                    "id": "CB-HIDDEN",
                    "path": "odylith/casebook/bugs/cb-hidden.md",
                    "label": "CB-HIDDEN",
                },
            ),
            duplicate_key="bug:CB-HIDDEN",
            freshness_state="current",
            semantic_signature=("non-current", "evidence", "visibility"),
            evidence=(
                value_engine.SignalEvidence(
                    source_kind="casebook",
                    source_id="CB-HIDDEN",
                    freshness="hidden_only",
                    confidence=1.0,
                    excerpt="Hidden context is not visible proof.",
                    evidence_class="hidden_payload",
                ),
                value_engine.SignalEvidence(
                    source_kind="casebook",
                    source_id="CB-OLD",
                    freshness="generated_only",
                    confidence=1.0,
                    excerpt="Generated payload is not product evidence.",
                    evidence_class="generated_payload",
                ),
            ),
        ),
        features=value_engine.InterventionValueFeatures(
            correctness_confidence=1.0,
            materiality=1.0,
            actionability=1.0,
            novelty=1.0,
            timing_relevance=1.0,
            user_need=1.0,
            visibility_need=1.0,
        ),
    )

    decision = value_engine.select_visible_signals(
        [option],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_candidates == []
    assert decision.suppressed_candidates[0]["suppressed_reason"] == "non_current_evidence_signal"
    assert decision.metric_summary["evidence_gated_count"] == 1


def test_value_engine_ignores_hidden_high_confidence_when_current_evidence_is_weak() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="hidden-inflation",
                label="risks",
                duplicate_group="adversarial:hidden-inflation",
                correctness=1.0,
                materiality=1.0,
                actionability=1.0,
                evidence=(
                    value_engine.SignalEvidence(
                        source_kind="test",
                        source_id="current-weak",
                        freshness="current",
                        confidence=0.2,
                        excerpt="weak current evidence",
                        evidence_class="negative_control",
                    ),
                    value_engine.SignalEvidence(
                        source_kind="hidden_context",
                        source_id="hidden-strong",
                        freshness="hidden_only",
                        confidence=1.0,
                        excerpt="hidden evidence cannot prove visible product truth",
                        evidence_class="hidden_payload",
                    ),
                ),
            )
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_candidates == []
    assert decision.suppressed_candidates[0]["suppressed_reason"] == "weak_evidence_signal"


def test_value_engine_mapping_missing_evidence_confidence_does_not_default_to_trust() -> None:
    decision = value_engine.select_visible_signals(
        [
            {
                "candidate_id": "mapping-missing-confidence",
                "label": "insight",
                "block_kind": "ambient",
                "markdown_text": "**Odylith Insight:** Missing confidence must stay quiet.",
                "plain_text": "Odylith Insight: Missing confidence must stay quiet.",
                "duplicate_group": "adversarial:missing-confidence",
                "proposition": {
                    "proposition_id": "prop-mapping-missing-confidence",
                    "claim_text": "Missing confidence must stay quiet.",
                    "proposition_kind": "insight",
                    "support_state": "supported",
                    "duplicate_key": "adversarial:missing-confidence",
                    "freshness_state": "current",
                    "evidence": [
                        {
                            "source_kind": "test",
                            "source_id": "missing-confidence",
                            "freshness": "current",
                            "excerpt": "confidence field intentionally absent",
                            "evidence_class": "negative_control",
                        }
                    ],
                },
                "value_features": {
                    "correctness_confidence": 1.0,
                    "materiality": 1.0,
                    "actionability": 1.0,
                    "novelty": 1.0,
                    "timing_relevance": 1.0,
                    "user_need": 1.0,
                    "visibility_need": 1.0,
                    "interruption_cost": 0.0,
                    "redundancy_cost": 0.0,
                    "uncertainty_penalty": 0.0,
                    "brand_risk": 0.0,
                },
            }
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_candidates == []
    assert decision.suppressed_candidates[0]["suppressed_reason"] == "weak_evidence_signal"


def test_value_engine_allows_governed_anchor_only_support_when_evidence_rows_are_absent() -> None:
    option = value_engine.VisibleInterventionOption(
        option_id="anchor-only",
        proposed_label="history",
        block_kind="ambient",
        markdown_text="**Odylith History:** CB-122 anchors this recurrence.",
        plain_text="Odylith History: CB-122 anchors this recurrence.",
        proposition=value_engine.SignalProposition(
            proposition_id="prop-anchor-only",
            claim_text="CB-122 anchors this recurrence.",
            proposition_kind="history",
            support_state="supported",
            anchor_refs=(
                {
                    "kind": "bug",
                    "id": "CB-122",
                    "path": "odylith/casebook/bugs/2026-04-17-intervention-hooks-report-ready-while-chat-sees-zero-visible-odylith-beats.md",
                    "label": "CB-122",
                },
            ),
            duplicate_key="bug:CB-122",
            freshness_state="current",
            evidence=(),
        ),
        features=value_engine.InterventionValueFeatures(
            correctness_confidence=0.98,
            materiality=0.94,
            actionability=0.74,
            novelty=0.72,
            timing_relevance=0.9,
            user_need=0.86,
            visibility_need=0.82,
            interruption_cost=0.04,
            uncertainty_penalty=0.01,
            brand_risk=0.01,
        ),
    )

    decision = value_engine.select_visible_signals(
        [option],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_labels() == ["history"]
    assert decision.selected_candidates[0]["proposition_id"] == "prop-anchor-only"


def test_value_engine_allows_multiple_same_label_ambient_blocks_when_distinct() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="risk-a",
                label="risks",
                duplicate_group="risk:visibility-proof",
                claim_text="The chat-visible proof path is unconfirmed.",
            ),
            _option(
                option_id="risk-b",
                label="risks",
                duplicate_group="risk:unsafe-migration",
                claim_text="The migration path still has an unsafe stale artifact.",
            ),
            _option(option_id="history", label="history", duplicate_group="bug:CB-122"),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_labels() == ["risks", "risks", "history"]
    assert len({row["duplicate_group"] for row in decision.selected_candidates}) == 3
    assert decision.metric_summary["duplicate_visible_block_rate"] == 0.0


def test_value_engine_keeps_shared_domain_terms_when_claims_are_distinct() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="risk-ledger-proof",
                label="risks",
                duplicate_group="risk:ledger-proof",
                claim_text="Visibility ledger proof is missing for ambient blocks.",
                semantic_signature=(),
            ),
            _option(
                option_id="risk-ledger-latency",
                label="risks",
                duplicate_group="risk:ledger-latency",
                claim_text="Visibility ledger latency budget is exhausted for browser checks.",
                semantic_signature=(),
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert [row["candidate_id"] for row in decision.selected_candidates] == [
        "risk-ledger-latency",
        "risk-ledger-proof",
    ]
    assert decision.metric_summary["conflict_graph_edges"] == 0


def test_value_engine_collapses_same_label_duplicate_group_to_one_visible_block() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="risk-weaker",
                label="risks",
                duplicate_group="risk:chat-proof",
                materiality=0.88,
                actionability=0.70,
            ),
            _option(
                option_id="risk-stronger",
                label="risks",
                duplicate_group="risk:chat-proof",
                materiality=0.96,
                actionability=0.86,
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert [row["candidate_id"] for row in decision.selected_candidates] == ["risk-stronger"]
    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons["risk-weaker"] == "duplicate_visible_proposition"


def test_value_engine_collapses_semantic_duplicates_with_different_duplicate_keys() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="risk",
                label="risks",
                duplicate_group="risk:visibility-ledger",
                materiality=0.88,
                actionability=0.70,
                semantic_signature=("chat", "visible", "proof", "ledger"),
            ),
            _option(
                option_id="observation",
                label="observation",
                block_kind="observation",
                duplicate_group="observation:cb-122",
                materiality=0.96,
                actionability=0.90,
                semantic_signature=("chat", "visible", "proof", "ledger", "cb-122"),
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert [row["candidate_id"] for row in decision.selected_candidates] == ["observation"]
    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons["risk"] == "duplicate_visible_proposition"
    assert decision.metric_summary["conflict_graph_edges"] >= 1


def test_value_engine_collapses_duplicate_claims_when_metadata_is_sparse() -> None:
    claim = "The chat-visible proof ledger is unconfirmed for this session."
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="risk",
                label="risks",
                duplicate_group="",
                materiality=0.88,
                actionability=0.70,
                claim_text=claim,
                semantic_signature=(),
            ),
            _option(
                option_id="observation",
                label="observation",
                block_kind="observation",
                duplicate_group="",
                materiality=0.96,
                actionability=0.90,
                claim_text=claim,
                semantic_signature=(),
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert [row["candidate_id"] for row in decision.selected_candidates] == ["observation"]
    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons["risk"] == "duplicate_visible_proposition"
    assert decision.metric_summary["conflict_graph_edges"] >= 1


def test_value_engine_collapses_semantic_duplicate_flood_with_mismatched_keys() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id=f"risk-{index}",
                label="risks",
                duplicate_group=f"risk:key-{index}",
                materiality=0.98 - (index * 0.001),
                semantic_signature=("visible", "chat", "proof", "ledger", "cb-122"),
            )
            for index in range(60)
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert [row["candidate_id"] for row in decision.selected_candidates] == ["risk-0"]
    assert decision.metric_summary["eligible_unpruned_count"] == 60
    assert decision.metric_summary["candidate_pruned_count"] == 48
    assert decision.metric_summary["conflict_graph_edges"] >= 66
    assert decision.metric_summary["selected_count"] == 1
    assert decision.metric_summary["latency_ms"] <= 8.0
    assert {
        row["suppressed_reason"]
        for row in decision.suppressed_candidates
        if row["candidate_id"] != "risk-0"
    } == {"duplicate_visible_proposition"}


def test_value_engine_allows_actionable_proposal_to_coexist_with_observation_overlap() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="observation",
                label="observation",
                block_kind="observation",
                duplicate_group="observation:visible-proof",
                semantic_signature=("chat", "visible", "proof", "ledger"),
            ),
            _option(
                option_id="proposal",
                label="proposal",
                block_kind="proposal",
                duplicate_group="proposal:radar:B-096",
                actionability=1.0,
                action_payload={"actions": [{"surface": "radar", "target_id": "B-096", "operation": "update"}]},
                semantic_signature=("chat", "visible", "proof", "ledger", "radar"),
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_labels() == ["observation", "proposal"]


def test_value_engine_rejects_proposal_that_only_restates_observation_even_with_action() -> None:
    claim = "The chat-visible proof path is unconfirmed for this session."
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="observation",
                label="observation",
                block_kind="observation",
                duplicate_group="observation:visible-proof",
                claim_text=claim,
                semantic_signature=("chat", "visible", "proof", "path"),
            ),
            _option(
                option_id="proposal",
                label="proposal",
                block_kind="proposal",
                duplicate_group="proposal:visible-proof",
                claim_text=claim,
                actionability=1.0,
                action_payload={"actions": [{"surface": "casebook", "target_id": "CB-122", "operation": "update"}]},
                semantic_signature=("chat", "visible", "proof", "path", "casebook"),
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert [row["candidate_id"] for row in decision.selected_candidates] == ["observation"]
    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons["proposal"] == "duplicate_visible_proposition"
    assert decision.metric_summary["conflict_graph_edges"] >= 1


def test_value_engine_stale_evidence_cannot_be_rescued_by_anchor_refs() -> None:
    option = value_engine.VisibleInterventionOption(
        option_id="stale-with-anchor",
        proposed_label="history",
        block_kind="ambient",
        markdown_text="**Odylith History:** A stale bug anchor cannot prove current truth.",
        plain_text="Odylith History: A stale bug anchor cannot prove current truth.",
        proposition=value_engine.SignalProposition(
            proposition_id="prop-stale-with-anchor",
            claim_text="A stale bug anchor cannot prove current truth.",
            proposition_kind="history",
            support_state="supported",
            anchor_refs=(
                {
                    "kind": "bug",
                    "id": "CB-OLD",
                    "path": "odylith/casebook/bugs/cb-old.md",
                    "label": "CB-OLD",
                },
            ),
            duplicate_key="bug:CB-OLD",
            freshness_state="current",
            semantic_signature=("stale", "anchor", "current", "truth"),
            evidence=(
                value_engine.SignalEvidence(
                    source_kind="casebook",
                    source_id="CB-OLD",
                    freshness="stale",
                    confidence=1.0,
                    excerpt="Old bug evidence",
                    evidence_class="governed_anchor",
                ),
            ),
        ),
        features=value_engine.InterventionValueFeatures(
            correctness_confidence=1.0,
            materiality=1.0,
            actionability=1.0,
            novelty=1.0,
            timing_relevance=1.0,
            user_need=1.0,
            visibility_need=1.0,
        ),
    )

    decision = value_engine.select_visible_signals(
        [option],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_candidates == []
    assert decision.suppressed_candidates[0]["suppressed_reason"] == "stale_signal"


def test_value_engine_selection_is_deterministic_across_input_order() -> None:
    options = [
        _option(option_id="history", label="history", duplicate_group="bug:CB-122"),
        _option(option_id="risk-a", label="risks", duplicate_group="risk:a"),
        _option(option_id="risk-b", label="risks", duplicate_group="risk:b"),
    ]
    first = value_engine.select_visible_signals(
        options,
        context={"explicit_diagnosis_or_planning": True},
    )
    second = value_engine.select_visible_signals(
        list(reversed(options)),
        context={"explicit_diagnosis_or_planning": True},
    )

    assert [row["candidate_id"] for row in first.selected_candidates] == [
        row["candidate_id"] for row in second.selected_candidates
    ]
    assert first.selected_block_set_id == second.selected_block_set_id


def test_value_engine_requires_concrete_proposal_action_payload() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id="observation",
                label="observation",
                block_kind="observation",
                duplicate_group="observation:proposal-gate",
            ),
            _option(
                option_id="proposal",
                label="proposal",
                block_kind="proposal",
                duplicate_group="proposal:empty-action",
                actionability=1.0,
                action_payload={"actions": [{"surface": "radar"}]},
            ),
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.selected_labels() == ["observation"]
    reasons = {row["candidate_id"]: row["suppressed_reason"] for row in decision.suppressed_candidates}
    assert reasons["proposal"] == "proposal_without_concrete_action"


def test_value_engine_prunes_candidate_flood_before_subset_enumeration() -> None:
    decision = value_engine.select_visible_signals(
        [
            _option(
                option_id=f"risk-{index}",
                label="risks",
                duplicate_group=f"risk:{index}",
                materiality=0.92 - ((index % 5) * 0.01),
            )
            for index in range(60)
        ],
        context={"explicit_diagnosis_or_planning": True},
    )

    assert decision.metric_summary["eligible_unpruned_count"] == 60
    assert decision.metric_summary["candidate_pruned_count"] == 48
    assert decision.metric_summary["selected_count"] <= 4
    assert decision.metric_summary["enumerated_subset_count"] <= 793
    assert decision.metric_summary["latency_ms"] <= 8.0


def test_value_engine_scoring_clamps_features_without_inflating_evidence() -> None:
    option = _option(
        option_id="clamped",
        label="insight",
        duplicate_group="score:clamped",
        correctness=1.0,
        evidence=(
            value_engine.SignalEvidence(
                source_kind="test",
                source_id="clamped",
                freshness="current",
                confidence=0.55,
                excerpt="barely supported",
                evidence_class="unit",
            ),
        ),
    )
    option = value_engine.VisibleInterventionOption(
        **{
            **option.__dict__,
            "features": value_engine.InterventionValueFeatures(
                correctness_confidence=9.0,
                materiality=9.0,
                actionability=9.0,
                novelty=9.0,
                timing_relevance=9.0,
                user_need=9.0,
                visibility_need=9.0,
                interruption_cost=-5.0,
                redundancy_cost=-5.0,
                uncertainty_penalty=-5.0,
                brand_risk=-5.0,
            ),
        }
    )

    assert value_engine.weighted_positive_value(option.features) == 1.0
    assert value_engine.proposition_evidence_confidence(option.proposition) == 0.55
    assert value_engine.option_net_value(option) == pytest.approx(0.63)


def test_adjudication_corpus_is_bootstrap_not_publishable_calibration() -> None:
    corpus = value_engine.load_adjudication_corpus()
    report = value_engine.advisory_report(corpus)
    metrics = report["metric_summary"]
    quality = metrics["corpus_quality"]

    assert report["runtime_posture"] == "deterministic_utility_v1"
    assert quality["quality_state"] == "bootstrap"
    assert quality["publishable"] is False
    assert value_engine.runtime_calibration_publishable() is False
    assert metrics["duplicate_visible_block_rate"] == 0.0
    assert metrics["must_suppress_accuracy"] == 1.0
    assert metrics["visibility_failure_recall"] == 1.0
    assert metrics["latency_p95_ms"] <= 15.0
    assert metrics["calibration_case_count"] == 4
    assert metrics["synthetic_case_count"] >= 1


def test_adjudication_corpus_fingerprint_is_deterministic() -> None:
    corpus = value_engine.load_adjudication_corpus()
    first = value_engine.evaluate_adjudication_corpus(corpus)
    second = value_engine.evaluate_adjudication_corpus(corpus)

    assert first["corpus_fingerprint"] == second["corpus_fingerprint"]
    assert first["precision"] == second["precision"]
    assert first["recall"] == second["recall"]


def test_adjudication_corpus_rejects_contradictory_labels() -> None:
    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    first_case = corpus["cases"][0]
    first_case["must_suppress_propositions"] = list(first_case["expected_selected_propositions"])

    with pytest.raises(ValueError, match="contradicts labels"):
        value_engine.validate_adjudication_corpus(corpus)


def test_adjudication_corpus_rejects_synthetic_calibration_counting() -> None:
    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    synthetic = next(case for case in corpus["cases"] if case["origin"] == "synthetic_gate")
    synthetic["counts_for_calibration"] = True

    with pytest.raises(ValueError, match="synthetic data count"):
        value_engine.validate_adjudication_corpus(corpus)


def test_adjudication_corpus_rejects_missing_calibration_count_field() -> None:
    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    corpus["cases"][0].pop("counts_for_calibration")

    with pytest.raises(ValueError, match="missing counts_for_calibration"):
        value_engine.validate_adjudication_corpus(corpus)


def test_adjudication_corpus_rejects_empty_provenance_fields() -> None:
    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    corpus["cases"][0]["source_refs"] = []

    with pytest.raises(ValueError, match="missing source_refs provenance"):
        value_engine.validate_adjudication_corpus(corpus)

    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    corpus["cases"][0]["rationale"] = " "

    with pytest.raises(ValueError, match="missing rationale provenance"):
        value_engine.validate_adjudication_corpus(corpus)


def test_adjudication_corpus_rejects_invalid_origin_and_visibility_expectation() -> None:
    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    corpus["cases"][0]["origin"] = "spreadsheet_guess"

    with pytest.raises(ValueError, match="invalid origin"):
        value_engine.validate_adjudication_corpus(corpus)

    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    corpus["cases"][0]["visibility_expectation"] = "probably"

    with pytest.raises(ValueError, match="invalid visibility expectation"):
        value_engine.validate_adjudication_corpus(corpus)


def test_adjudication_corpus_rejects_options_without_proposition_or_value_features() -> None:
    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    corpus["cases"][0]["options"][0].pop("proposition")

    with pytest.raises(ValueError, match="without proposition provenance"):
        value_engine.validate_adjudication_corpus(corpus)

    corpus = copy.deepcopy(value_engine.load_adjudication_corpus())
    corpus["cases"][0]["options"][0].pop("value_features")

    with pytest.raises(ValueError, match="without value_features"):
        value_engine.validate_adjudication_corpus(corpus)
