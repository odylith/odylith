from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bootstrap_runtime as hot_path_bootstrap_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_core_runtime as hot_path_core_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_finalize_runtime as hot_path_finalize_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_runtime as hot_path_runtime
from odylith.runtime.context_engine import odylith_context_engine_memory_snapshot_runtime as memory_snapshot_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_adaptive_runtime as packet_adaptive_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_architecture_runtime as packet_architecture_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_session_runtime as packet_session_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_summary_runtime as packet_summary_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_backlog_runtime as projection_backlog_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_entity_runtime as projection_entity_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_query_runtime as projection_query_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_registry_runtime as projection_registry_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as projection_search_runtime
from odylith.runtime.context_engine import odylith_context_engine_runtime_learning_runtime as runtime_learning_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import odylith_context_engine_hot_path_delivery_runtime as hot_path_delivery_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_governance_runtime as hot_path_governance_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_scope_runtime as hot_path_scope_runtime


packet_adaptive_runtime.bind(store.__dict__)
hot_path_finalize_runtime.bind(store.__dict__)


def test_projection_query_bind_calls_split_projection_binders(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        projection_search_runtime,
        "bind",
        lambda host: calls.append(("search", host)),
    )
    monkeypatch.setattr(
        projection_entity_runtime,
        "bind",
        lambda host: calls.append(("entity", host)),
    )
    monkeypatch.setattr(
        projection_backlog_runtime,
        "bind",
        lambda host: calls.append(("backlog", host)),
    )
    monkeypatch.setattr(
        projection_registry_runtime,
        "bind",
        lambda host: calls.append(("registry", host)),
    )

    projection_query_runtime.bind({})

    assert [name for name, _ in calls] == ["search", "entity", "backlog", "registry"]
    assert all(target is projection_query_runtime.__dict__ for _, target in calls)


def test_hot_path_runtime_bind_calls_split_packet_binders(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(hot_path_scope_runtime, "bind", lambda host: calls.append(("scope", host)))
    monkeypatch.setattr(hot_path_core_runtime, "bind", lambda host: calls.append(("core", host)))
    monkeypatch.setattr(hot_path_bootstrap_runtime, "bind", lambda host: calls.append(("bootstrap", host)))
    monkeypatch.setattr(hot_path_finalize_runtime, "bind", lambda host: calls.append(("finalize", host)))
    monkeypatch.setattr(hot_path_delivery_runtime, "bind", lambda host: calls.append(("delivery", host)))
    monkeypatch.setattr(hot_path_governance_runtime, "bind", lambda host: calls.append(("governance", host)))

    hot_path_runtime.bind({})

    assert [name for name, _ in calls] == [
        "scope",
        "core",
        "bootstrap",
        "finalize",
        "delivery",
        "governance",
    ]
    assert all(target is hot_path_runtime.__dict__ for _, target in calls)


def test_store_refresh_runtime_helper_bindings_calls_split_runtime_binders(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(packet_summary_runtime, "bind", lambda host: calls.append(("summary", host)))
    monkeypatch.setattr(packet_architecture_runtime, "bind", lambda host: calls.append(("architecture", host)))
    monkeypatch.setattr(packet_session_runtime, "bind", lambda host: calls.append(("session", host)))
    monkeypatch.setattr(packet_adaptive_runtime, "bind", lambda host: calls.append(("adaptive", host)))
    monkeypatch.setattr(memory_snapshot_runtime, "bind", lambda host: calls.append(("memory_snapshot", host)))
    monkeypatch.setattr(projection_query_runtime, "bind", lambda host: calls.append(("projection_query", host)))
    monkeypatch.setattr(hot_path_runtime, "bind", lambda host: calls.append(("hot_path", host)))
    monkeypatch.setattr(runtime_learning_runtime, "bind", lambda host: calls.append(("runtime_learning", host)))

    store._refresh_runtime_helper_bindings()  # noqa: SLF001

    assert [name for name, _ in calls] == [
        "summary",
        "architecture",
        "session",
        "adaptive",
        "memory_snapshot",
        "projection_query",
        "hot_path",
        "runtime_learning",
    ]
    assert all(target is store.__dict__ for _, target in calls)


def test_runtime_learning_packet_summary_helper_delegates_to_split_summary_runtime(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def _fake_packet_summary(payload: object) -> dict[str, object]:
        observed["payload"] = payload
        return {"packet_state": "compact", "route_ready": True}

    monkeypatch.setattr(
        packet_summary_runtime,
        "_packet_summary_from_bootstrap_payload",
        _fake_packet_summary,
    )

    payload = {"context_packet": {"packet_state": "compact"}}

    assert runtime_learning_runtime._packet_summary_from_bootstrap_payload(payload) == {  # noqa: SLF001
        "packet_state": "compact",
        "route_ready": True,
    }
    assert observed["payload"] == payload


def test_fast_finalize_compact_hot_path_packet_uses_finalize_trim_runtime(monkeypatch) -> None:
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        hot_path_core_runtime,
        "_trim_common_hot_path_context_packet",
        lambda *, context_packet_payload, within_budget: {
            **dict(context_packet_payload),
            "trimmed_within_budget": within_budget,
        },
    )

    def _fake_trim(*, compact: object, full_scan_recommended: bool) -> dict[str, object]:
        observed["compact"] = compact
        observed["full_scan_recommended"] = full_scan_recommended
        return {"trimmed_by_finalize": True}

    monkeypatch.setattr(
        hot_path_finalize_runtime,
        "_trim_route_ready_hot_path_prompt_payload",
        _fake_trim,
    )
    monkeypatch.setattr(
        hot_path_core_runtime,
        "_drop_redundant_hot_path_routing_handoff",
        lambda payload: {"collapsed": payload},
    )

    result = hot_path_core_runtime._fast_finalize_compact_hot_path_packet(  # noqa: SLF001
        compact={
            "context_packet": {"packet_state": "compact", "route": {}},
            "packet_metrics": {"within_budget": False},
        },
        within_budget=True,
        full_scan_recommended=False,
    )

    trimmed_compact = dict(observed["compact"])
    assert "packet_metrics" not in trimmed_compact
    assert trimmed_compact["context_packet"]["trimmed_within_budget"] is True
    assert observed["full_scan_recommended"] is False
    assert result == {"collapsed": {"trimmed_by_finalize": True}}


def test_adaptive_packet_preserves_selector_diagnostics_from_custom_mapping(monkeypatch) -> None:
    class _SelectorDiagnostics(dict):
        pass

    diagnostics = _SelectorDiagnostics(
        {
            "component_fast_selector_used": True,
            "component_selector_candidate_row_count": 2,
        }
    )

    monkeypatch.setattr(
        packet_adaptive_runtime,
        "build_impact_report",
        lambda **_kwargs: {
            "context_packet_state": "compact",
            "context_packet": {
                "packet_state": "compact",
                "route": {},
                "packet_quality": {"i": "implementation"},
            },
            "benchmark_selector_diagnostics": diagnostics,
        },
    )
    monkeypatch.setattr(packet_adaptive_runtime, "_hot_path_auto_escalation_trigger", lambda **_kwargs: "")
    monkeypatch.setattr(
        packet_adaptive_runtime,
        "_should_escalate_hot_path_to_session_brief",
        lambda **_kwargs: (False, []),
    )
    monkeypatch.setattr(packet_adaptive_runtime, "_hot_path_route_ready", lambda _payload: True)
    monkeypatch.setattr(packet_adaptive_runtime, "_hot_path_full_scan_recommended", lambda _payload: False)
    monkeypatch.setattr(packet_adaptive_runtime, "_hot_path_routing_confidence", lambda _payload: "high")
    monkeypatch.setattr(packet_adaptive_runtime, "_hot_path_payload_is_compact", lambda _payload: True)
    monkeypatch.setattr(
        packet_adaptive_runtime,
        "_update_compact_hot_path_runtime_packet",
        lambda **kwargs: dict(kwargs["payload"]),
    )

    result = packet_adaptive_runtime.build_adaptive_coding_packet(
        repo_root=Path("."),
        changed_paths=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        runtime_mode="standalone",
    )

    assert result["adaptive_escalation"]["benchmark_selector_diagnostics"] == {
        "component_fast_selector_used": True,
        "component_selector_candidate_row_count": 2,
    }


def test_compact_impact_packet_keeps_benchmark_reviewer_guide_once(monkeypatch) -> None:
    monkeypatch.setattr(
        hot_path_finalize_runtime,
        "_companion_context_paths_for_normalized_changed_paths",
        lambda _paths: [
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            "docs/benchmarks/REVIEWER_GUIDE.md",
            "docs/benchmarks/REVIEWER_GUIDE.md",
        ],
    )

    compact = hot_path_finalize_runtime._compact_hot_path_runtime_packet(  # noqa: SLF001
        packet_kind="impact",
        payload={
            "context_packet_state": "compact",
            "context_packet": {
                "packet_state": "compact",
                "route": {},
                "packet_quality": {"i": "implementation"},
            },
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        },
    )

    assert compact["docs"] == [
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
    ]
