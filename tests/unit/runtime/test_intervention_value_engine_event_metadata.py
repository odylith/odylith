from __future__ import annotations

from odylith.runtime.intervention_engine import value_engine
from odylith.runtime.intervention_engine import value_engine_event_metadata


def _candidate(index: int) -> dict[str, object]:
    return {
        "candidate_id": f"candidate-{index}",
        "proposition_id": f"prop-{index}",
        "label": "risks",
        "block_kind": "ambient",
        "duplicate_group": f"risk:{index}",
        "proposition": {
            "semantic_signature": ["visible", "proof", str(index)],
            "evidence": [
                {
                    "source_id": f"CB-{index}",
                    "source_fingerprint": "shared-fingerprint",
                },
                {
                    "source_id": f"CB-{index}",
                    "source_fingerprint": "shared-fingerprint",
                },
                {
                    "source_path": f"odylith/casebook/bugs/cb-{index}.md",
                },
            ],
            "source_fingerprints": {
                "casebook": "shared-fingerprint",
                "registry": f"registry-{index}",
            },
        },
        "feature_vector": {
            "correctness_confidence": 0.94,
            "materiality": 0.9,
        },
        "net_value": 0.8,
        "suppressed_reason": "duplicate_visible_proposition" if index else "",
    }


def test_value_decision_event_metadata_is_bounded_and_dedupes_fingerprints() -> None:
    decision = value_engine.VisibleSignalSelectionDecision(
        selected_candidates=[_candidate(0)],
        suppressed_candidates=[_candidate(index) for index in range(1, 31)],
        no_output_reason="",
        selected_block_set_id="visible-set:test",
        value_engine_version="intervention-value-engine.v1",
        runtime_posture="deterministic_utility_v1",
        metric_summary={"selected_count": 1, "latency_ms": 0.2},
        decision_log={"selected_proposition_ids": ["prop-0"]},
    )

    metadata = value_engine_event_metadata.value_decision_event_metadata(
        decision=decision,
        delivery_channel="Assistant Visible Fallback",
        delivery_status="Assistant Render Required",
        render_surface="Codex Post Tool",
    )

    selected = metadata["value_decision"]["selected"][0]
    assert metadata["visibility_proof"] == {
        "delivery_channel": "assistant_visible_fallback",
        "delivery_status": "assistant_render_required",
        "render_surface": "codex_post_tool",
    }
    assert len(metadata["value_decision"]["suppressed"]) == 24
    assert selected["evidence_fingerprints"] == [
        "shared-fingerprint",
        "odylith/casebook/bugs/cb-0.md",
        "registry-0",
    ]
    assert metadata["value_decision"]["metric_summary"]["latency_ms"] == 0.2
    assert metadata["value_decision"]["decision_log"]["selected_proposition_ids"] == ["prop-0"]


def test_value_decision_event_metadata_stays_empty_for_no_candidates() -> None:
    decision = value_engine.VisibleSignalSelectionDecision(
        selected_candidates=[],
        suppressed_candidates=[],
        no_output_reason="no_high_value_supported_signal",
        selected_block_set_id="",
        value_engine_version="intervention-value-engine.v1",
        runtime_posture="deterministic_utility_v1",
        metric_summary={},
    )

    assert (
        value_engine_event_metadata.value_decision_event_metadata(
            decision=decision,
            delivery_channel="",
            delivery_status="",
            render_surface="",
        )
        == {}
    )
