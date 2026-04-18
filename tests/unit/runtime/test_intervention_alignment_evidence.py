from __future__ import annotations

from odylith.runtime.intervention_engine import alignment_evidence
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.intervention_engine.contract import ObservationEnvelope


def _observation(**overrides: object) -> ObservationEnvelope:
    payload = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="prompt_context",
        session_id="alignment-evidence-test",
        prompt_excerpt="Keep this turn bounded.",
        **overrides,
    )
    return ObservationEnvelope.from_mapping(payload)


def test_alignment_evidence_tolerates_malformed_count_fields() -> None:
    observation = _observation(
        execution_engine_summary={
            "execution_engine_present": True,
            "execution_engine_candidate_target_count": "n/a",
            "execution_engine_diagnostic_anchor_count": object(),
        },
        memory_summary={"recent_event_count": "many"},
        visibility_summary={
            "chat_visible_proof": "unproven_this_session",
            "event_count": "n/a",
            "visible_event_count": object(),
        },
        delivery_snapshot={"event_count": "unknown", "unconfirmed_event_count": object()},
    )

    assert alignment_evidence.runtime_evidence_classes(observation) == []
    assert alignment_evidence.governance_facts_from_alignment(
        observation=observation,
        evidence_classes=[],
    ) == []
    assert alignment_evidence.merged_session_memory(
        observation=observation,
        stream_memory={"visible_event_count": "2", "recent_event_count": "bad"},
    )["visible_event_count"] == 2


def test_legacy_packet_anchors_feed_refs_without_current_context_packet() -> None:
    observation = _observation(
        packet_summary={
            "packet_kind": "governance_slice",
            "anchors": {
                "workstreams": ["B-096"],
                "components": ["governance-intervention-engine"],
                "bugs": ["CB-122"],
                "diagrams": ["D-038"],
            },
        },
    )

    refs = {(row["kind"], row["id"]) for row in alignment_evidence.active_target_refs(observation)}

    assert ("workstream", "B-096") in refs
    assert ("component", "governance-intervention-engine") in refs
    assert ("bug", "CB-122") in refs
    assert ("diagram", "D-038") in refs
    assert alignment_evidence.runtime_evidence_classes(observation) == ["context_engine_packet"]


def test_tribunal_case_facts_keep_case_refs_precise() -> None:
    observation = _observation(
        tribunal_summary={
            "case_queue": [
                {"id": "CB-121", "headline": "First visibility regression"},
                {"id": "CB-122", "headline": "Second visibility regression"},
            ],
        },
    )

    facts = alignment_evidence.governance_facts_from_alignment(
        observation=observation,
        evidence_classes=["tribunal_signal"],
    )
    refs_by_headline = {
        fact.headline: {(row["kind"], row["id"]) for row in fact.refs}
        for fact in facts
    }

    assert refs_by_headline["Tribunal already has CB-121 in the decision path."] == {("bug", "CB-121")}
    assert refs_by_headline["Tribunal already has CB-122 in the decision path."] == {("bug", "CB-122")}


def test_guidance_behavior_summary_feeds_intervention_alignment_without_visible_noise_on_pass() -> None:
    observation = _observation(
        context_packet_summary={
            "guidance_behavior_summary": {
                "family": "guidance_behavior",
                "status": "available",
                "validation_status": "not_run",
                "case_count": 2,
                "selected_case_ids": ["guidance-a", "guidance-b"],
                "validator_command": "odylith validate guidance-behavior --repo-root .",
                "tribunal_signal": {
                    "scope_type": "component",
                    "scope_id": "governance-intervention-engine",
                    "scope_label": "Guidance Behavior Contract",
                    "operator_readout": {"severity": "info"},
                },
            },
        },
    )

    refs = {(row["kind"], row["id"]) for row in alignment_evidence.active_target_refs(observation)}

    assert "guidance_behavior_contract" in alignment_evidence.runtime_evidence_classes(observation)
    assert ("component", "governance-intervention-engine") in refs
    assert alignment_evidence.governance_facts_from_alignment(
        observation=observation,
        evidence_classes=["guidance_behavior_contract"],
    ) == []


def test_failed_guidance_behavior_summary_becomes_single_high_signal_fact() -> None:
    observation = _observation(
        memory_summary={
            "guidance_behavior_summary": {
                "family": "guidance_behavior",
                "status": "failed",
                "validation_status": "failed",
                "case_count": 1,
                "failed_check_ids": ["visible_intervention_proof"],
                "tribunal_signal": {
                    "scope_type": "component",
                    "scope_id": "governance-intervention-engine",
                    "scope_label": "Guidance Behavior Contract",
                },
            },
        },
    )

    facts = alignment_evidence.governance_facts_from_alignment(
        observation=observation,
        evidence_classes=alignment_evidence.runtime_evidence_classes(observation),
    )

    assert [fact.headline for fact in facts] == ["Guidance behavior validation is not passing."]
    assert "visible_intervention_proof" in facts[0].detail
    assert "guidance_behavior_contract" in facts[0].evidence_classes


def test_character_summary_feeds_alignment_without_copy_or_noise_on_pass() -> None:
    observation = _observation(
        context_packet_summary={
            "character_summary": {
                "family": "agent_operating_character",
                "status": "available",
                "validation_status": "not_run",
                "case_count": 19,
                "selected_case_ids": ["character-visible-pass-stays-silent"],
                "validator_command": "odylith validate discipline --repo-root .",
            },
        },
    )

    refs = {(row["kind"], row["id"]) for row in alignment_evidence.active_target_refs(observation)}

    assert "agent_operating_character_contract" in alignment_evidence.runtime_evidence_classes(observation)
    assert ("component", "execution-engine") in refs
    assert alignment_evidence.governance_facts_from_alignment(
        observation=observation,
        evidence_classes=["agent_operating_character_contract"],
    ) == []


def test_failed_character_summary_becomes_single_high_signal_fact() -> None:
    observation = _observation(
        memory_summary={
            "character_summary": {
                "family": "agent_operating_character",
                "status": "failed",
                "validation_status": "failed",
                "case_count": 1,
                "validator_command": "odylith validate discipline --repo-root .",
            },
        },
    )

    facts = alignment_evidence.governance_facts_from_alignment(
        observation=observation,
        evidence_classes=alignment_evidence.runtime_evidence_classes(observation),
    )

    assert [fact.headline for fact in facts] == ["Odylith Discipline validation is not passing."]
    assert "local Discipline validator" in facts[0].detail
    assert "agent_operating_character_contract" in facts[0].evidence_classes
