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
