from __future__ import annotations

from odylith.runtime.memory import tooling_memory_contracts


def test_execution_profile_mapping_decodes_compact_token() -> None:
    profile = tooling_memory_contracts.execution_profile_mapping("codex_high|worker|bounded_write|delegate")

    assert profile == {
        "profile": "write_high",
        "agent_role": "worker",
        "selection_mode": "bounded_write",
        "delegate_preference": "delegate",
    }


def test_compact_execution_profile_mapping_keeps_only_shared_runtime_fields() -> None:
    profile = tooling_memory_contracts.compact_execution_profile_mapping(
        {
            "profile": "codex_medium",
            "agent_role": "worker",
            "selection_mode": "bounded_write",
            "delegate_preference": "",
            "model": "gpt-5.3-codex",
        }
    )

    assert profile == {
        "profile": "write_medium",
        "agent_role": "worker",
        "selection_mode": "bounded_write",
    }


def test_encode_execution_profile_token_trims_trailing_empty_fields() -> None:
    token = tooling_memory_contracts.encode_execution_profile_token(
        {
            "profile": "mini_high",
            "agent_role": "explorer",
            "selection_mode": "",
            "delegate_preference": "",
        }
    )

    assert token == "analysis_high|explorer"


def test_context_packet_and_evidence_pack_retain_guidance_behavior_summary() -> None:
    payload = {
        "guidance_behavior_summary": {
            "contract": "odylith_guidance_behavior_runtime_summary.v1",
            "family": "guidance_behavior",
            "status": "available",
            "validation_status": "not_run",
            "case_count": 2,
            "critical_or_high_case_count": 2,
            "selected_case_ids": ["guidance-a", "guidance-b"],
            "related_guidance_refs": ["AGENTS.md"],
            "validator_command": "odylith validate guidance-behavior --repo-root .",
            "hot_path_contract": {
                "provider_calls": False,
                "repo_wide_scan": False,
                "context_store_expansion": False,
            },
            "runtime_layer_contract": {
                "contract": "odylith_guidance_behavior_runtime_layers.v1",
                "layers": ["context_engine", "execution_engine", "memory_substrate"],
                "source_refs": [
                    "src/odylith/runtime/context_engine/tooling_context_packet_builder.py",
                    "src/odylith/runtime/memory/tooling_memory_contracts.py",
                ],
                "hot_path": {"summary_only": True, "provider_calls": False},
            },
            "platform_contract": {
                "contract": "odylith_guidance_behavior_platform_end_to_end.v1",
                "domains": ["benchmark_eval", "host_lane_bundle_mirrors", "hot_path_efficiency"],
                "source_refs": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
                "hot_path": {"summary_only": True, "repo_wide_scan": False},
            },
        },
        "packet_budget": {"max_bytes": 10000, "max_tokens": 2500},
        "packet_metrics": {"estimated_bytes": 400, "estimated_tokens": 100, "within_budget": True},
        "retrieval_plan": {},
        "packet_quality": {},
        "routing_handoff": {},
    }

    context_packet = tooling_memory_contracts.build_context_packet(
        packet_kind="governance_slice",
        packet_state="expanded",
        payload=payload,
    )
    evidence_pack = tooling_memory_contracts.build_evidence_pack(
        packet_kind="governance_slice",
        packet_state="expanded",
        payload=payload,
    )

    assert context_packet["guidance_behavior_summary"]["case_count"] == 2
    assert context_packet["guidance_behavior_summary"]["hot_path_contract"]["repo_wide_scan"] is False
    assert context_packet["guidance_behavior_summary"]["runtime_layer_contract"]["layers"] == [
        "context_engine",
        "execution_engine",
        "memory_substrate",
    ]
    assert evidence_pack["guidance_behavior_summary"]["validator_command"].endswith(
        "validate guidance-behavior --repo-root ."
    )
    assert evidence_pack["guidance_behavior_summary"]["runtime_layer_contract"]["hot_path"]["summary_only"] is True
    assert evidence_pack["guidance_behavior_summary"]["platform_contract"]["domains"] == [
        "benchmark_eval",
        "host_lane_bundle_mirrors",
        "hot_path_efficiency",
    ]


def test_context_packet_and_evidence_pack_retain_character_summary() -> None:
    payload = {
        "character_summary": {
            "contract": "odylith_agent_operating_character_runtime_summary.v1",
            "decision_contract": "odylith_agent_operating_character.v1",
            "family": "agent_operating_character",
            "status": "available",
            "validation_status": "not_run",
            "case_count": 13,
            "selected_case_ids": ["character-credit-safe-hot-path"],
            "validator_command": "odylith validate agent-operating-character --repo-root .",
            "hot_path_contract": {
                "provider_calls": False,
                "host_model_calls": False,
                "subagent_spawn": False,
                "broad_scan": False,
                "projection_expansion": False,
                "full_validation": False,
                "benchmark_execution": False,
            },
        },
        "packet_budget": {"max_bytes": 10000, "max_tokens": 2500},
        "packet_metrics": {"estimated_bytes": 400, "estimated_tokens": 100, "within_budget": True},
        "retrieval_plan": {},
        "packet_quality": {},
        "routing_handoff": {},
    }

    context_packet = tooling_memory_contracts.build_context_packet(
        packet_kind="governance_slice",
        packet_state="expanded",
        payload=payload,
    )
    evidence_pack = tooling_memory_contracts.build_evidence_pack(
        packet_kind="governance_slice",
        packet_state="expanded",
        payload=payload,
    )

    assert context_packet["character_summary"]["case_count"] == 13
    assert context_packet["character_summary"]["hot_path_contract"]["host_model_calls"] is False
    assert evidence_pack["character_summary"]["validator_command"].endswith(
        "validate agent-operating-character --repo-root ."
    )
    assert evidence_pack["character_summary"]["hot_path_contract"]["projection_expansion"] is False
