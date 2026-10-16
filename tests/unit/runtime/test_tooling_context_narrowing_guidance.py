from __future__ import annotations

from odylith.runtime.context_engine import tooling_context_narrowing_guidance as guidance


def test_exact_path_guidance_becomes_not_required_when_closeout_is_grounded() -> None:
    result = guidance.build_narrowing_guidance(
        packet_kind="impact",
        packet_state="gated_ambiguous",
        full_scan_recommended=False,
        full_scan_reason="",
        workstream_selection={"reason": "selection_ambiguous"},
        retrieval_plan={
            "has_non_shared_anchor": True,
            "anchor_quality": "explicit",
            "ambiguity_class": "historical_fanout",
            "evidence_consensus": "strong",
            "precision_score": 45,
            "guidance_coverage": "direct",
            "anchor_paths": ["src/odylith/runtime/context_engine/tooling_context_routing.py"],
        },
        final_payload={
            "changed_paths": ["src/odylith/runtime/context_engine/tooling_context_routing.py"],
            "recommended_commands": ["pytest tests/unit/runtime/test_tooling_context_routing.py"],
        },
    )

    assert result["required"] is False
    assert result["reason"] == "Exact-path retained evidence already bounds execution and closeout without broader narrowing."
    assert result["suggested_inputs"] == []
    assert result["next_fallback_command"] == ""


def test_narrowing_guidance_prefers_anchor_prompt_before_scan_fallback() -> None:
    result = guidance.build_narrowing_guidance(
        packet_kind="bootstrap_session",
        packet_state="gated_broad_scope",
        full_scan_recommended=True,
        full_scan_reason="broad shared scope",
        workstream_selection={},
        retrieval_plan={
            "selected_components": [{"entity_id": "odylith-context-engine"}],
            "selected_guidance_chunks": [{"canonical_source": "docs/context.md"}],
        },
        final_payload={"fallback_scan": {"query": "context"}},
    )

    assert result["required"] is True
    assert result["next_best_anchors"][0]["kind"] == "component"
    assert result["next_fallback_command"] == "./.odylith/bin/odylith context --repo-root . odylith-context-engine"


def test_narrowing_guidance_accepts_turn_visible_file_targets() -> None:
    result = guidance.build_narrowing_guidance(
        packet_kind="bootstrap_session",
        packet_state="gated_ambiguous",
        full_scan_recommended=True,
        full_scan_reason="selection_ambiguous",
        workstream_selection={"reason": "selection_ambiguous"},
        retrieval_plan={
            "guidance_coverage": "direct",
            "anchor_paths": ["src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py"],
        },
        final_payload={
            "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py"],
            "target_resolution": {
                "candidate_targets": [
                    {
                        "path": "src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py",
                        "source": "path_scope",
                        "writable": True,
                    }
                ],
                "has_writable_targets": True,
                "requires_more_consumer_context": False,
            },
        },
    )

    assert result["required"] is False
    assert result["reason"] == "Turn-visible file targets already bound startup; no additional narrowing required."
    assert result["suggested_inputs"] == []
    assert result["next_fallback_command"] == ""


def test_narrowing_guidance_suppresses_noisy_degraded_receipt_commands() -> None:
    result = guidance.build_narrowing_guidance(
        packet_kind="impact",
        packet_state="gated_broad_scope",
        full_scan_recommended=True,
        full_scan_reason="working_tree_scope_degraded",
        workstream_selection={},
        retrieval_plan={"anchor_paths": ["AGENTS.md"]},
        final_payload={
            "changed_paths": ["AGENTS.md"],
            "fallback_scan": {"query": "tenant boundary"},
        },
    )

    assert result["required"] is True
    assert result["reason"] == "Current shared/control-plane context still needs one concrete code, manifest, or contract anchor."
    assert result["next_fallback_command"] == ""
    assert result["next_fallback_followup"] == ""
