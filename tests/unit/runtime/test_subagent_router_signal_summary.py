from __future__ import annotations

from pathlib import Path

from odylith.runtime.orchestration import subagent_router as router
from odylith.runtime.orchestration import subagent_router_signal_summary as signal_summary


def test_request_with_consumer_write_policy_merges_profile_policy_for_write_requests(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        signal_summary,
        "load_consumer_profile",
        lambda *, repo_root: {
            "odylith_write_policy": {
                "odylith_fix_mode": "feedback_only",
                "allow_odylith_mutations": False,
                "protected_roots": ["odylith"],
            }
        },
    )
    request = router.RouteRequest(
        prompt="Repair the runtime issue.",
        needs_write=True,
        allowed_paths=["odylith/runtime/source/example.json"],
        context_signals={"routing_handoff": {"route_ready": True}},
    )

    merged = signal_summary.request_with_consumer_write_policy(request, repo_root=tmp_path)

    assert merged is not request
    assert merged.context_signals["odylith_write_policy"] == {
        "odylith_fix_mode": "feedback_only",
        "allow_odylith_mutations": False,
        "protected_roots": ["odylith"],
    }


def test_context_signal_summary_blocks_feedback_only_consumer_writes() -> None:
    request = router.RouteRequest(
        prompt="Fix the odylith runtime issue.",
        needs_write=True,
        allowed_paths=["odylith/runtime/source/example.json"],
        context_signals={
            "routing_handoff": {
                "route_ready": True,
                "routing_confidence": "high",
                "odylith_execution_profile": {
                    "host_runtime": "codex_cli",
                    "constraints": {"route_ready": True},
                },
            },
            "odylith_write_policy": {
                "odylith_fix_mode": "feedback_only",
                "allow_odylith_mutations": False,
                "protected_roots": ["odylith"],
            },
        },
    )

    summary = signal_summary._context_signal_summary(request)

    assert summary["odylith_fix_mode"] == "feedback_only"
    assert summary["allow_odylith_mutations"] is False
    assert summary["odylith_write_protected_roots"] == ["odylith"]
    assert summary["consumer_odylith_write_blocked"] is True


def test_context_signal_summary_infers_spawn_ready_for_codex_host_runtime() -> None:
    request = router.RouteRequest(
        prompt="Inspect the bounded runtime path.",
        needs_write=False,
        context_signals={"host_runtime": "codex_cli"},
    )

    summary = signal_summary._context_signal_summary(request)

    assert summary["host_runtime"] == "codex_cli"
    assert summary["native_spawn_supported"] is True
    assert summary["native_spawn_ready"] is True
    assert summary["native_spawn_ready_explicit"] is False
    assert summary["odylith_routing_signal_present"] is True


def test_context_signal_summary_preserves_explicit_spawn_not_ready() -> None:
    request = router.RouteRequest(
        prompt="Inspect the bounded runtime path.",
        needs_write=False,
        context_signals={"host_runtime": "codex_cli", "native_spawn_ready": False},
    )

    summary = signal_summary._context_signal_summary(request)

    assert summary["native_spawn_supported"] is True
    assert summary["native_spawn_ready"] is False
    assert summary["native_spawn_ready_explicit"] is True
