from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bootstrap_runtime as hot_path_bootstrap_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_core_runtime as hot_path_core_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_finalize_runtime as hot_path_finalize_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_runtime as hot_path_runtime
from odylith.runtime.context_engine import odylith_context_engine_delivery_surface_payload_runtime as delivery_surface_payload_runtime
from odylith.runtime.context_engine import odylith_context_engine_memory_snapshot_runtime as memory_snapshot_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_adaptive_runtime as packet_adaptive_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_architecture_runtime as packet_architecture_runtime
from odylith.runtime.context_engine import odylith_context_engine_dossier_compaction_runtime as dossier_compaction_runtime
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


def test_context_engine_split_modules_no_longer_expose_bind_shims() -> None:
    modules = (
        packet_session_runtime,
        packet_adaptive_runtime,
        memory_snapshot_runtime,
        projection_backlog_runtime,
        projection_entity_runtime,
        projection_query_runtime,
        projection_search_runtime,
        hot_path_scope_runtime,
        hot_path_bootstrap_runtime,
        hot_path_core_runtime,
        hot_path_finalize_runtime,
        hot_path_delivery_runtime,
        hot_path_governance_runtime,
        hot_path_runtime,
        runtime_learning_runtime,
    )
    for module in modules:
        assert not hasattr(module, "bind"), f"bind shim resurfaced in {module.__name__}"


def test_projection_registry_runtime_no_longer_rebinds_parent_host() -> None:
    assert not hasattr(projection_registry_runtime, "bind")


def test_store_refresh_runtime_helper_bindings_is_noop() -> None:
    assert store._refresh_runtime_helper_bindings() is None  # noqa: SLF001


def test_store_refresh_runtime_helper_bindings_no_longer_rebinds_summary_and_architecture_modules() -> None:
    assert not hasattr(packet_summary_runtime, "bind")
    assert not hasattr(packet_architecture_runtime, "bind")


def test_context_engine_store_no_longer_exports_packet_builder_or_dossier_wrappers() -> None:
    for name in (
        "build_session_brief",
        "build_session_bootstrap",
        "build_adaptive_coding_packet",
        "build_adaptive_coding_packet_reusing_daemon",
        "compact_context_dossier_for_delivery",
        "load_delivery_surface_payload",
    ):
        assert name not in store.__dict__, f"{name} resurfaced on context_engine_store"
    assert callable(dossier_compaction_runtime.compact_context_dossier_for_delivery)


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
        store,
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
    monkeypatch.setattr(store, "_hot_path_auto_escalation_trigger", lambda **_kwargs: "")
    monkeypatch.setattr(
        store,
        "_should_escalate_hot_path_to_session_brief",
        lambda **_kwargs: (False, []),
    )
    monkeypatch.setattr(store, "_hot_path_route_ready", lambda _payload: True)
    monkeypatch.setattr(store, "_hot_path_full_scan_recommended", lambda _payload: False)
    monkeypatch.setattr(store, "_hot_path_routing_confidence", lambda _payload: "high")
    monkeypatch.setattr(store, "_hot_path_payload_is_compact", lambda _payload: True)
    monkeypatch.setattr(
        store,
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


def test_adaptive_guidance_behavior_packet_skips_runtime_warmup(monkeypatch) -> None:
    observed_skip_flags: list[bool] = []

    def _fake_build_impact_report(**kwargs):  # noqa: ANN001
        observed_skip_flags.append(bool(kwargs.get("skip_runtime_warmup")))
        return {
            "context_packet_state": "compact",
            "context_packet": {
                "packet_state": "compact",
                "route": {},
                "packet_quality": {"i": "analysis"},
                "guidance_behavior_summary": {
                    "family": "guidance_behavior",
                    "validator_command": "odylith validate guidance-behavior --repo-root .",
                },
            },
        }

    monkeypatch.setattr(store, "build_impact_report", _fake_build_impact_report)
    monkeypatch.setattr(store, "_hot_path_auto_escalation_trigger", lambda **_kwargs: "")
    monkeypatch.setattr(
        store,
        "_should_escalate_hot_path_to_session_brief",
        lambda **_kwargs: (False, []),
    )
    monkeypatch.setattr(store, "_hot_path_route_ready", lambda _payload: True)
    monkeypatch.setattr(store, "_hot_path_full_scan_recommended", lambda _payload: False)
    monkeypatch.setattr(store, "_hot_path_routing_confidence", lambda _payload: "medium")
    monkeypatch.setattr(store, "_hot_path_payload_is_compact", lambda _payload: True)
    monkeypatch.setattr(
        store,
        "_update_compact_hot_path_runtime_packet",
        lambda **kwargs: dict(kwargs["payload"]),
    )

    packet_adaptive_runtime.build_adaptive_coding_packet(
        repo_root=Path("."),
        changed_paths=["odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json"],
        runtime_mode="standalone",
        family_hint="guidance_behavior",
    )
    packet_adaptive_runtime.build_adaptive_coding_packet(
        repo_root=Path("."),
        changed_paths=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        runtime_mode="standalone",
        family_hint="execution_engine",
    )

    assert observed_skip_flags == [True, False]


def test_guidance_behavior_impact_packet_avoids_projection_connection(monkeypatch, tmp_path: Path) -> None:
    def _unexpected_projection_connection(_root):  # noqa: ANN001
        raise AssertionError("guidance behavior hot path should not open projection store")

    monkeypatch.setattr(store, "_connect", _unexpected_projection_connection)

    payload = store.build_impact_report(
        repo_root=tmp_path,
        changed_paths=["odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json"],
        runtime_mode="standalone",
        delivery_profile="agent_hot_path",
        family_hint="guidance_behavior",
        validation_command_hints=["odylith validate guidance-behavior --repo-root ."],
        skip_runtime_warmup=True,
    )

    assert payload["context_packet"]["packet_quality"]["i"] == "analysis"
    assert (
        payload["context_packet"]["execution_engine_handshake"]["route_readiness"]["full_scan_recommended"]
        is False
    )


def test_compact_impact_packet_keeps_benchmark_reviewer_guide_once(monkeypatch) -> None:
    monkeypatch.setattr(
        store,
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
