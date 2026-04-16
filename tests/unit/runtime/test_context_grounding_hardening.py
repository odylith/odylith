from __future__ import annotations

import contextlib
from pathlib import Path

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import derivation_provenance
from odylith.runtime.context_engine import odylith_context_engine_projection_compiler_runtime as projection_compiler_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_runtime as hot_path_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_scope_runtime as hot_path_scope
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as projection_search_runtime
from odylith.runtime.context_engine import tooling_context_packet_builder
from odylith.runtime.context_engine import session_bootstrap_payload_compactor
from odylith.runtime.context_engine import odylith_context_engine_store as store


class _Cursor:
    def __init__(self, *, rows: list[dict[str, object]] | None = None, row: dict[str, object] | None = None) -> None:
        self._rows = list(rows or [])
        self._row = row

    def fetchall(self) -> list[dict[str, object]]:
        return list(self._rows)

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class _EmptyConnection:
    def execute(self, _sql: str, _params: tuple[object, ...] = ()) -> _Cursor:
        return _Cursor()


def test_resolve_context_entity_exact_repo_paths_skip_runtime_search(tmp_path: Path, monkeypatch) -> None:
    connection = _EmptyConnection()
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "dashboard" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# Dashboard\n", encoding="utf-8")
    code_path = tmp_path / "src" / "odylith" / "cli.py"
    code_path.parent.mkdir(parents=True, exist_ok=True)
    code_path.write_text("print('ok')\n", encoding="utf-8")
    backlog_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.parent.mkdir(parents=True, exist_ok=True)
    backlog_index.write_text("# Backlog\n", encoding="utf-8")

    monkeypatch.setattr(
        store,
        "search_entities_payload",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("exact path resolution should not search")),
    )

    for ref, expected_kind in (
        ("odylith/radar/source/INDEX.md", "doc"),
        ("odylith/registry/source/components/dashboard/CURRENT_SPEC.md", "doc"),
        ("src/odylith/cli.py", "code"),
    ):
        entity, matches, lookup = store._resolve_context_entity(connection, repo_root=tmp_path, ref=ref, kind=None)  # noqa: SLF001

        assert matches == []
        assert lookup["resolution_mode"] == "path_exact"
        assert entity is not None
        assert entity["kind"] == expected_kind
        assert entity["path"] == ref


def test_entity_by_path_rejects_missing_or_outside_repo_files(tmp_path: Path) -> None:
    connection = _EmptyConnection()
    inside_missing = store._entity_by_path(connection, repo_root=tmp_path, path_ref="odylith/radar/source/INDEX.md")  # noqa: SLF001
    outside_root = tmp_path.parent / "outside.md"
    outside_root.write_text("outside\n", encoding="utf-8")
    outside = store._entity_by_path(connection, repo_root=tmp_path, path_ref=str(outside_root))  # noqa: SLF001

    assert inside_missing is None
    assert outside is None


def test_entity_by_path_rejects_repo_local_symlink_to_outside_file(tmp_path: Path) -> None:
    connection = _EmptyConnection()
    outside_root = tmp_path.parent / "outside-target.md"
    outside_root.write_text("outside\n", encoding="utf-8")
    linked = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    linked.parent.mkdir(parents=True, exist_ok=True)
    linked.symlink_to(outside_root)

    entity = store._entity_by_path(connection, repo_root=tmp_path, path_ref="odylith/radar/source/INDEX.md")  # noqa: SLF001

    assert entity is None


def test_session_scope_uses_dirty_repo_paths_when_no_session_seed_exists(tmp_path: Path, monkeypatch) -> None:
    store._PROCESS_PATH_SCOPE_CACHE.clear()  # noqa: SLF001
    monkeypatch.setattr(
        store.governance,
        "collect_meaningful_changed_paths",
        lambda **kwargs: [
            "odylith/radar/source/INDEX.md",
            "src/odylith/cli.py",
            "README.md",
        ],
    )
    monkeypatch.setattr(store, "_load_session_state", lambda **kwargs: None)
    monkeypatch.setattr(store, "_workspace_activity_fingerprint", lambda **kwargs: "dirty")

    payload = store._resolve_changed_path_scope_context(  # noqa: SLF001
        repo_root=tmp_path,
        explicit_paths=(),
        use_working_tree=True,
        working_tree_scope="session",
        session_id="session-1",
    )

    assert payload["working_tree_scope"] == "session"
    assert payload["working_tree_scope_degraded"] is False
    assert payload["scoped_working_tree_paths"] == ["src/odylith/cli.py", "README.md"]
    assert payload["analysis_paths"] == ["src/odylith/cli.py", "README.md"]


def test_resolve_context_entity_kind_exact_rejects_mismatched_path_entity(tmp_path: Path) -> None:
    connection = _EmptyConnection()
    code_path = tmp_path / "src" / "odylith" / "cli.py"
    code_path.parent.mkdir(parents=True, exist_ok=True)
    code_path.write_text("print('ok')\n", encoding="utf-8")

    entity, matches, lookup = store._resolve_context_entity(  # noqa: SLF001
        connection,
        repo_root=tmp_path,
        ref="src/odylith/cli.py",
        kind="component",
    )

    assert entity is None
    assert matches == []
    assert lookup["resolution_mode"] == "none"


def test_prioritize_scope_paths_prefers_high_signal_paths_over_generated_noise() -> None:
    prioritized = hot_path_scope._prioritize_scope_paths(  # noqa: SLF001
        [
            "odylith/index.html",
            "odylith/radar/backlog-payload.v1.js",
            "src/odylith/cli.py",
            "bin/validate",
            "tests/unit/test_cli.py",
            "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
            "odylith/radar/source/INDEX.md",
        ],
        max_paths=4,
    )

    assert prioritized == [
        "src/odylith/cli.py",
        "bin/validate",
        "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
        "tests/unit/test_cli.py",
    ]


def test_session_scope_caps_dirty_paths_to_high_signal_subset(tmp_path: Path, monkeypatch) -> None:
    store._PROCESS_PATH_SCOPE_CACHE.clear()  # noqa: SLF001
    monkeypatch.setattr(
        store.governance,
        "collect_meaningful_changed_paths",
        lambda **kwargs: [
            "odylith/index.html",
            "odylith/tooling-payload.v1.js",
            "odylith/radar/backlog-payload.v1.js",
            "src/odylith/cli.py",
            "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
            "bin/validate",
            "tests/unit/test_cli.py",
            "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
            "odylith/radar/source/INDEX.md",
            "CONTRIBUTING.md",
            "odylith/compass/compass.html",
            "odylith/casebook/casebook.html",
            "odylith/registry/registry.html",
            "odylith/atlas/atlas.html",
            "README.md",
            "docs/specs/odylith-repo-integration-contract.md",
            "src/odylith/runtime/context_engine/odylith_context_engine_projection_entity_runtime.py",
            "src/odylith/runtime/governance/backlog_authoring.py",
            "src/odylith/runtime/governance/sync_workstream_artifacts.py",
            "src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py",
            "src/odylith/runtime/surfaces/tooling_dashboard_runtime_builder.py",
            "src/odylith/runtime/surfaces/tooling_dashboard_release_presenter.py",
            "src/odylith/runtime/surfaces/tooling_dashboard_welcome_presenter.py",
            "src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js",
            "src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css",
            "src/odylith/runtime/evaluation/benchmark_compare.py",
            "src/odylith/runtime/common/stable_generated_utc.py",
        ],
    )
    monkeypatch.setattr(store, "_load_session_state", lambda **kwargs: None)
    monkeypatch.setattr(store, "_workspace_activity_fingerprint", lambda **kwargs: "dirty")

    payload = store._resolve_changed_path_scope_context(  # noqa: SLF001
        repo_root=tmp_path,
        explicit_paths=(),
        use_working_tree=True,
        working_tree_scope="session",
        session_id="session-1",
    )

    assert payload["working_tree_scope_degraded"] is False
    assert len(payload["repo_dirty_paths"]) == 12
    assert len(payload["analysis_paths"]) == 12
    assert payload["analysis_paths"][0] == "src/odylith/cli.py"
    assert "bin/validate" in payload["analysis_paths"]
    assert "odylith/radar/backlog-payload.v1.js" not in payload["analysis_paths"]


def test_session_scope_rescues_shared_only_dirty_paths_instead_of_degrading(tmp_path: Path, monkeypatch) -> None:
    store._PROCESS_PATH_SCOPE_CACHE.clear()  # noqa: SLF001
    monkeypatch.setattr(
        store.governance,
        "collect_meaningful_changed_paths",
        lambda **kwargs: [  # noqa: ARG005
            "AGENTS.md",
            "odylith/radar/source/INDEX.md",
        ],
    )
    monkeypatch.setattr(store, "_load_session_state", lambda **kwargs: None)
    monkeypatch.setattr(store, "_workspace_activity_fingerprint", lambda **kwargs: "dirty")

    payload = store._resolve_changed_path_scope_context(  # noqa: SLF001
        repo_root=tmp_path,
        explicit_paths=(),
        use_working_tree=True,
        working_tree_scope="session",
        session_id="session-1",
    )

    assert payload["working_tree_scope_degraded"] is False
    assert payload["scope_rescue_mode"] == "shared_only_seed"
    assert payload["scoped_working_tree_paths"] == ["AGENTS.md", "odylith/radar/source/INDEX.md"]
    assert payload["analysis_paths"] == ["AGENTS.md", "odylith/radar/source/INDEX.md"]


def test_session_scope_uses_intent_anchor_paths_before_shared_only_fallback(tmp_path: Path, monkeypatch) -> None:
    store._PROCESS_PATH_SCOPE_CACHE.clear()  # noqa: SLF001
    code_path = tmp_path / "src" / "odylith" / "cli.py"
    code_path.parent.mkdir(parents=True, exist_ok=True)
    code_path.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(
        store.governance,
        "collect_meaningful_changed_paths",
        lambda **kwargs: ["AGENTS.md"],  # noqa: ARG005
    )
    monkeypatch.setattr(store, "_load_session_state", lambda **kwargs: None)
    monkeypatch.setattr(store, "_workspace_activity_fingerprint", lambda **kwargs: "dirty")

    payload = store._resolve_changed_path_scope_context(  # noqa: SLF001
        repo_root=tmp_path,
        explicit_paths=(),
        use_working_tree=True,
        working_tree_scope="session",
        session_id="session-1",
        intent="Investigate `src/odylith/cli.py` before widening.",
    )

    assert payload["working_tree_scope_degraded"] is False
    assert payload["scope_rescue_mode"] == "intent_seed"
    assert payload["intent_anchor_paths"] == ["src/odylith/cli.py"]
    assert payload["analysis_paths"] == ["src/odylith/cli.py"]


def test_prompt_payload_suppresses_working_tree_scope_degraded_receipts_when_paths_remain() -> None:
    trimmed = store._trim_route_ready_hot_path_prompt_payload(  # noqa: SLF001
        compact={
            "changed_paths": ["AGENTS.md"],
            "full_scan_reason": "working_tree_scope_degraded",
            "fallback_scan": {"query": "tenant boundary"},
            "context_packet": {
                "full_scan_recommended": True,
                "full_scan_reason": "working_tree_scope_degraded",
                "anchors": {"changed_paths": ["AGENTS.md"]},
                "retrieval_plan": {
                    "full_scan_reason": "working_tree_scope_degraded",
                },
                "route": {
                    "narrowing_required": True,
                },
            },
        },
        full_scan_recommended=True,
    )

    assert trimmed.get("fallback_scan") is None
    assert trimmed.get("full_scan_reason") is None
    assert trimmed["context_packet"].get("full_scan_reason") is None
    assert trimmed["context_packet"]["retrieval_plan"].get("full_scan_reason") is None


def test_prompt_payload_suppresses_broad_shared_paths_receipts_when_paths_remain() -> None:
    trimmed = store._trim_route_ready_hot_path_prompt_payload(  # noqa: SLF001
        compact={
            "changed_paths": ["odylith/AGENTS.md"],
            "full_scan_reason": "broad_shared_paths",
            "fallback_scan": {"query": "tenant boundary"},
            "context_packet": {
                "full_scan_recommended": True,
                "full_scan_reason": "broad_shared_paths",
                "anchors": {"changed_paths": ["odylith/AGENTS.md"]},
                "retrieval_plan": {
                    "full_scan_reason": "broad_shared_paths",
                },
                "route": {
                    "narrowing_required": True,
                },
            },
        },
        full_scan_recommended=True,
    )

    assert trimmed.get("fallback_scan") is None
    assert trimmed.get("full_scan_reason") is None
    assert trimmed["context_packet"].get("full_scan_reason") is None
    assert trimmed["context_packet"]["retrieval_plan"].get("full_scan_reason") is None


def test_bootstrap_payload_compactor_drops_duplicate_path_receipts() -> None:
    payload = session_bootstrap_payload_compactor.compact_bootstrap_payload(
        {
            "changed_paths": ["AGENTS.md", "odylith/AGENTS.md"],
            "explicit_paths": ["AGENTS.md", "odylith/AGENTS.md"],
            "repo_dirty_paths": ["AGENTS.md", "odylith/AGENTS.md"],
            "scoped_working_tree_paths": ["AGENTS.md", "odylith/AGENTS.md"],
            "working_tree_scope": "session",
            "selection_state": "ambiguous",
            "session": {
                "session_id": "codex-1",
                "updated_utc": "2026-03-31T00:00:00Z",
                "touched_paths": ["AGENTS.md", "odylith/AGENTS.md"],
                "analysis_paths": ["AGENTS.md", "odylith/AGENTS.md"],
                "explicit_paths": ["AGENTS.md", "odylith/AGENTS.md"],
                "working_tree_scope": "session",
                "selection_state": "ambiguous",
            },
        }
    )

    assert payload["changed_paths"] == ["AGENTS.md", "odylith/AGENTS.md"]
    assert "explicit_paths" not in payload
    assert "repo_dirty_paths" not in payload
    assert "scoped_working_tree_paths" not in payload
    assert payload["session"] == {
        "session_id": "codex-1",
        "updated_utc": "2026-03-31T00:00:00Z",
    }


def test_finalized_bootstrap_payload_compactor_drops_duplicate_views() -> None:
    payload = session_bootstrap_payload_compactor.compact_finalized_bootstrap_payload(
        {
            "context_packet_state": "gated_ambiguous",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "packet_state": "gated_ambiguous",
                "packet_budget": {"max_bytes": 19200, "max_tokens": 4800},
                "packet_quality": {"routing_confidence": "low"},
                "retrieval_plan": {"ambiguity_class": "no_candidates"},
            },
            "packet_budget": {"max_bytes": 19200, "max_tokens": 4800},
            "packet_quality": {"routing_confidence": "low"},
            "retrieval_plan": {"ambiguity_class": "no_candidates"},
            "narrowing_guidance": {
                "required": True,
                "reason": "No workstream evidence matched the current changed-path set.",
                "suggested_inputs": [
                    "Provide at least one implementation, test, contract, or manifest path.",
                    "Read the highest-signal guidance source directly when the packet exposes one.",
                ],
            },
        }
    )

    assert payload.get("packet_budget") is None
    assert payload.get("packet_quality") is None
    assert payload.get("retrieval_plan") is None
    assert payload["narrowing_guidance"] == {
        "required": True,
        "reason": "Need one code path.",
    }
    assert payload.get("packet_metrics") is None
    context_packet = payload["context_packet"]
    assert context_packet["packet_kind"] == "bootstrap_session"
    assert context_packet["packet_state"] == "gated_ambiguous"
    assert context_packet["retrieval_plan"] == {"ambiguity_class": "no_candidates"}
    assert context_packet["packet_quality"] == {"rc": "low"}
    if "execution_governance" in context_packet:
        assert isinstance(context_packet["execution_governance"], dict)


def test_finalized_bootstrap_payload_compactor_preserves_turn_targets_and_anchor_followup() -> None:
    payload = session_bootstrap_payload_compactor.compact_finalized_bootstrap_payload(
        {
            "context_packet_state": "gated_ambiguous",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "packet_state": "gated_ambiguous",
                "anchors": {"has_non_shared_anchor": True},
            },
            "turn_context": {
                "intent": 'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
                "surfaces": ["compass"],
                "visible_text": ["Task Contract, Event Ledger, and Hard-Constraint Promotion"],
                "active_tab": "releases",
                "user_turn_id": "turn-2",
                "supersedes_turn_id": "turn-1",
            },
            "target_resolution": {
                "lane": "consumer",
                "candidate_targets": [
                    {
                        "path": "odylith/compass/compass.html",
                        "source": "path_scope",
                        "writable": False,
                    }
                ],
                "diagnostic_anchors": [
                    {
                        "kind": "workstream",
                        "value": "B-073",
                        "label": "Task Contract, Event Ledger, and Hard-Constraint Promotion",
                    }
                ],
                "has_writable_targets": False,
                "requires_more_consumer_context": True,
                "consumer_failover": "maintainer_ready_feedback_plus_bounded_narrowing",
            },
            "presentation_policy": {
                "commentary_mode": "task_first_minimal",
                "suppress_routing_receipts": True,
                "surface_fast_lane": True,
            },
            "narrowing_guidance": {
                "required": True,
                "reason": "No workstream evidence matched the current changed-path set.",
                "suggested_inputs": ["Open the consumer route component first."],
                "next_best_anchors": [
                    {
                        "kind": "workstream",
                        "value": "B-073",
                        "label": "Task Contract, Event Ledger, and Hard-Constraint Promotion",
                    }
                ],
            },
        }
    )

    assert payload["narrowing_guidance"] == {
        "required": True,
        "reason": "Need one code path.",
        "suggested_inputs": ["Open the consumer route component first."],
        "next_best_anchors": [
            {
                "kind": "workstream",
                "value": "B-073",
                "label": "Task Contract, Event Ledger, and Hard-Constraint Promotion",
            }
        ],
    }
    assert payload["target_resolution"] == {
        "lane": "consumer",
        "candidate_targets": [
            {
                "path": "odylith/compass/compass.html",
                "source": "path_scope",
                "writable": False,
            }
        ],
        "diagnostic_anchors": [
            {
                "kind": "workstream",
                "value": "B-073",
                "label": "Task Contract, Event Ledger, and Hard-Constraint Promotion",
            }
        ],
        "has_writable_targets": False,
        "requires_more_consumer_context": True,
        "consumer_failover": "maintainer_ready_feedback_plus_bounded_narrowing",
    }
    assert payload["presentation_policy"] == {
        "commentary_mode": "task_first_minimal",
        "suppress_routing_receipts": True,
        "surface_fast_lane": True,
    }


def test_finalized_session_brief_payload_compactor_drops_runtime_scaffolding() -> None:
    payload = session_bootstrap_payload_compactor.compact_finalized_session_brief_payload(
        {
            "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "selection_state": "ambiguous",
            "selection_reason": "Multiple candidates still overlap.",
            "selection_confidence": "low",
            "context_packet": {
                "packet_kind": "session_brief",
                "packet_state": "gated_ambiguous",
                "anchors": {
                    "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
                    "explicit_paths": [],
                    "has_non_shared_anchor": True,
                },
                "retrieval_plan": {
                    "ambiguity_class": "overlap",
                    "selected_counts": {"docs": 0, "tests": 1},
                    "precision_score": 41,
                },
                "packet_quality": {
                    "routing_confidence": "guarded",
                    "intent_family": "analysis",
                    "context_density_level": "low",
                },
                "route": {
                    "narrowing_required": True,
                    "parallelism_hint": "serial_guarded",
                },
                "execution_profile": {
                    "profile": "main_thread",
                    "agent_role": "main_thread",
                    "selection_mode": "narrow_first",
                    "delegate_preference": "hold_local",
                    "source": "odylith_runtime_packet",
                },
                "optimization": {
                    "within_budget": True,
                    "packet_strategy": "bounded",
                },
            },
            "impact": {
                "docs": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
                "recommended_commands": ["pytest -q tests/unit/runtime/test_context_grounding_hardening.py"],
                "recommended_tests": [
                    {
                        "path": "tests/unit/runtime/test_context_grounding_hardening.py",
                        "reason": "covers context delivery compaction",
                    }
                ],
            },
            "working_memory_tiers": {"hot": {"changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"]}},
            "packet_metrics": {"estimated_tokens": 999},
            "routing_handoff": {"routing_confidence": "guarded"},
        }
    )

    assert sorted(payload.keys()) == [
        "changed_paths",
        "context_packet",
        "impact",
        "selection_confidence",
        "selection_reason",
        "selection_state",
    ]
    assert payload["context_packet"]["anchors"] == {"has_non_shared_anchor": True}
    assert payload["context_packet"]["retrieval_plan"] == {
        "ambiguity_class": "overlap",
        "precision_score": 41,
        "selected_counts": "t1",
    }
    assert payload["context_packet"]["optimization"] == {"within_budget": True}
    assert payload["impact"]["recommended_tests"] == [
        {
            "path": "tests/unit/runtime/test_context_grounding_hardening.py",
            "reason": "covers context delivery compaction",
        }
    ]


def test_prune_hot_path_finalize_base_payload_for_bootstrap_session_keeps_only_delivery_fields() -> None:
    compact = tooling_context_packet_builder._prune_hot_path_finalize_base_payload(  # noqa: SLF001
        packet_kind="bootstrap_session",
        packet_state="gated_ambiguous",
        base_payload={
            "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "explicit_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "selection_state": "ambiguous",
            "selection_reason": "Multiple candidates still overlap.",
            "selection_confidence": "low",
            "context_packet_state": "gated_ambiguous",
            "full_scan_recommended": True,
            "full_scan_reason": "selection_ambiguous",
            "fallback_scan": {"performed": True, "results": [{"path": "src/odylith/runtime/context_engine/odylith_context_engine.py"}]},
            "narrowing_guidance": {"required": True, "reason": "Need one code path."},
            "adaptive_packet_profile": {"packet_strategy": "bounded"},
            "relevant_docs": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
            "recommended_commands": ["pytest -q tests/unit/runtime/test_context_grounding_hardening.py"],
            "recommended_tests": [
                {
                    "path": "tests/unit/runtime/test_context_grounding_hardening.py",
                    "reason": "covers context delivery compaction",
                }
            ],
            "retrieval_plan": {
                "selected_docs": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
                "selected_commands": ["pytest -q tests/unit/runtime/test_context_grounding_hardening.py"],
                "selected_tests": [{"path": "tests/unit/runtime/test_context_grounding_hardening.py"}],
                "selected_guidance_chunks": [{"chunk_path": "odylith/AGENTS.md"}],
                "selected_counts": {"docs": 1, "tests": 1, "commands": 1, "guidance": 1},
                "miss_recovery": {"active": True, "applied": True, "mode": "projection_exact_rescue"},
            },
            "workstream_selection": {"selected_workstream": {"entity_id": "B-020"}},
            "session": {"session_id": "codex-1", "intent": "implementation benchmark"},
            "impact_summary": {"components": [{"entity_id": "benchmark"}]},
            "runtime": {"projection_fingerprint": "fp"},
            "active_conflicts": [{"session_id": "other"}],
        },
    )

    assert compact["changed_paths"] == ["src/odylith/runtime/context_engine/odylith_context_engine.py"]
    assert compact["relevant_docs"] == ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"]
    assert compact["recommended_commands"] == ["pytest -q tests/unit/runtime/test_context_grounding_hardening.py"]
    assert compact["recommended_tests"] == [
        {
            "path": "tests/unit/runtime/test_context_grounding_hardening.py",
            "reason": "covers context delivery compaction",
        }
    ]
    assert compact["retrieval_plan"]["selected_counts"] == {"docs": 1, "tests": 1, "commands": 1, "guidance": 1}
    assert compact["retrieval_plan"]["miss_recovery"] == {
        "active": True,
        "applied": True,
        "mode": "projection_exact_rescue",
    }
    assert compact["workstream_selection"] == {"selected_workstream": {"entity_id": "B-020"}}
    assert compact.get("session") is None
    assert compact.get("impact_summary") is None
    assert compact.get("runtime") is None
    assert compact.get("active_conflicts") is None


def test_warm_runtime_reuses_matching_runtime_state_without_reloading_projection_snapshot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    snapshot_path = tmp_path / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(projection_search_runtime, "_runtime_enabled", lambda _mode: True)
    monkeypatch.setattr(projection_search_runtime, "projection_input_fingerprint", lambda **_kwargs: "fp-1")
    monkeypatch.setattr(
        projection_search_runtime,
        "read_runtime_state",
        lambda **_kwargs: {"projection_fingerprint": "fp-1", "projection_scope": "reasoning"},
    )
    monkeypatch.setattr(projection_search_runtime, "projection_snapshot_path", lambda **_kwargs: snapshot_path)
    monkeypatch.setattr(
        projection_search_runtime,
        "warm_projections",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("warm_projections should not run")),
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: False,
    )

    assert projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=tmp_path,
        runtime_mode="auto",
        reason="impact",
        scope="reasoning",
    ) is True


def test_warm_runtime_ttl_does_not_hide_projection_fingerprint_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path.resolve()
    cache_key = f"{root}:reasoning"
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE[cache_key] = 10_000.0  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS[cache_key] = "fp-stale"  # noqa: SLF001
    snapshot_path = tmp_path / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(projection_search_runtime.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(projection_search_runtime, "_runtime_enabled", lambda _mode: True)
    monkeypatch.setattr(projection_search_runtime, "projection_input_fingerprint", lambda **_kwargs: "fp-fresh")
    monkeypatch.setattr(
        projection_search_runtime,
        "read_runtime_state",
        lambda **_kwargs: {"projection_fingerprint": "fp-fresh", "projection_scope": "reasoning"},
    )
    monkeypatch.setattr(projection_search_runtime, "projection_snapshot_path", lambda **_kwargs: snapshot_path)
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: False,
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "warm_projections",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("fresh snapshot reuse should not rebuild")),
    )

    assert projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=tmp_path,
        runtime_mode="auto",
        reason="query",
        scope="reasoning",
    ) is True
    assert projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS[cache_key] == "fp-fresh"  # noqa: SLF001


def test_projection_cache_signature_ignores_stale_process_warm_fingerprint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_key = f"{tmp_path.resolve()}:reasoning"
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS[cache_key] = "fp-stale"  # noqa: SLF001
    monkeypatch.setattr(projection_search_runtime, "projection_input_fingerprint", lambda **_kwargs: "fp-fresh")

    signature = projection_search_runtime._projection_cache_signature(  # noqa: SLF001
        repo_root=tmp_path,
        scope="reasoning",
    )

    assert signature == "fp-fresh"


def test_warm_runtime_rebuilds_when_backend_projection_is_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    snapshot_path = tmp_path / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("{}", encoding="utf-8")
    warm_calls: list[dict[str, object]] = []

    monkeypatch.setattr(projection_search_runtime, "_runtime_enabled", lambda _mode: True)
    monkeypatch.setattr(projection_search_runtime, "projection_input_fingerprint", lambda **_kwargs: "fp-2")
    monkeypatch.setattr(
        projection_search_runtime,
        "read_runtime_state",
        lambda **_kwargs: {"projection_fingerprint": "fp-2", "projection_scope": "reasoning"},
    )
    monkeypatch.setattr(projection_search_runtime, "projection_snapshot_path", lambda **_kwargs: snapshot_path)
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "warm_projections",
        lambda **kwargs: warm_calls.append(kwargs) or {"ok": True},
    )

    assert projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=tmp_path,
        runtime_mode="auto",
        reason="impact",
        scope="reasoning",
    ) is True
    assert warm_calls == [
        {
            "repo_root": tmp_path.resolve(),
            "reason": "impact",
            "scope": "reasoning",
        }
    ]


def test_warm_runtime_reuses_full_snapshot_for_reasoning_queries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    snapshot_path = tmp_path / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(projection_search_runtime, "_runtime_enabled", lambda _mode: True)
    monkeypatch.setattr(
        projection_search_runtime,
        "projection_input_fingerprint",
        lambda **kwargs: "fp-full" if kwargs.get("scope") == "full" else "fp-reasoning",
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "read_runtime_state",
        lambda **_kwargs: {"projection_fingerprint": "fp-full", "projection_scope": "full"},
    )
    monkeypatch.setattr(projection_search_runtime, "projection_snapshot_path", lambda **_kwargs: snapshot_path)
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **kwargs: kwargs.get("projection_scope") == "full"
        and kwargs.get("projection_fingerprint") == "fp-full",
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "warm_projections",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("fresh full snapshot should satisfy reasoning queries")),
    )

    assert projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=tmp_path,
        runtime_mode="auto",
        reason="query",
        scope="reasoning",
    ) is True


def test_warm_runtime_reuses_reasoning_snapshot_for_default_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    snapshot_path = tmp_path / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(projection_search_runtime, "_runtime_enabled", lambda _mode: True)
    monkeypatch.setattr(
        projection_search_runtime,
        "projection_input_fingerprint",
        lambda **kwargs: "fp-reasoning" if kwargs.get("scope") == "reasoning" else "fp-default",
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "read_runtime_state",
        lambda **_kwargs: {"projection_fingerprint": "fp-reasoning", "projection_scope": "reasoning"},
    )
    monkeypatch.setattr(projection_search_runtime, "projection_snapshot_path", lambda **_kwargs: snapshot_path)
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **kwargs: kwargs.get("projection_scope") == "reasoning"
        and kwargs.get("projection_fingerprint") == "fp-reasoning",
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "warm_projections",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("fresh reasoning snapshot should satisfy default scope")),
    )

    assert projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=tmp_path,
        runtime_mode="auto",
        reason="query",
        scope="default",
    ) is True


def test_projection_compiler_runtime_refuses_fast_reuse_when_local_backend_is_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime_root = tmp_path / ".odylith" / "runtime"
    monkeypatch.setattr(store, "runtime_root", lambda **_kwargs: runtime_root)
    monkeypatch.setattr(store, "projection_input_fingerprint", lambda **_kwargs: "fp-1")
    monkeypatch.setattr(
        store,
        "read_runtime_state",
        lambda **_kwargs: {"projection_fingerprint": "fp-1", "projection_scope": "reasoning"},
    )
    monkeypatch.setattr(store, "load_runtime_timing_summary", lambda **_kwargs: [])
    monkeypatch.setattr(store, "record_runtime_timing", lambda **_kwargs: None)
    monkeypatch.setattr(
        store.odylith_projection_bundle,
        "load_bundle_manifest",
        lambda **_kwargs: {"ready": True, "projection_fingerprint": "fp-1", "projection_scope": "reasoning"},
    )
    monkeypatch.setattr(
        store.odylith_projection_snapshot,
        "load_snapshot",
        lambda **_kwargs: {
            "ready": True,
            "tables": {"components": 1},
            "projection_fingerprint": "fp-1",
            "projection_scope": "reasoning",
        },
    )
    monkeypatch.setattr(
        store.odylith_memory_backend,
        "load_manifest",
        lambda **_kwargs: {"projection_fingerprint": "fp-1", "projection_scope": "reasoning", "ready": True},
    )
    monkeypatch.setattr(
        store.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        store.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(store.odylith_context_cache, "advisory_lock", lambda **_kwargs: contextlib.nullcontext())
    monkeypatch.setattr(
        store,
        "_empty_projection_tables",
        lambda: (_ for _ in ()).throw(RuntimeError("rebuild_required")),
    )

    try:
        projection_compiler_runtime.warm_projections(
            repo_root=tmp_path,
            force=False,
            reason="query",
            scope="reasoning",
        )
    except RuntimeError as exc:
        assert str(exc) == "rebuild_required"
    else:  # pragma: no cover - defensive
        raise AssertionError("stale local backend should force a rebuild instead of fast reuse")


def test_projection_compiler_runtime_reuses_full_projection_when_reasoning_is_requested(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime_root = tmp_path / ".odylith" / "runtime"
    state_writes: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []
    compiler_provenance = derivation_provenance.build_derivation_provenance(
        repo_root=tmp_path,
        projection_scope="full",
        projection_fingerprint="fp-full",
        sync_generation=0,
        code_version=derivation_provenance.fingerprint_source_files(
            [
                Path(projection_compiler_runtime.__file__),
                Path(store.odylith_projection_snapshot.__file__),
                Path(store.odylith_projection_bundle.__file__),
            ]
        ),
        flags={"projection_names": sorted(store._projection_names_for_scope("full"))},  # noqa: SLF001
    )
    backend_provenance = derivation_provenance.build_derivation_provenance(
        repo_root=tmp_path,
        projection_scope="full",
        projection_fingerprint="fp-full",
        sync_generation=0,
        code_version=derivation_provenance.fingerprint_source_files(
            [
                Path(store.odylith_memory_backend.__file__),
                Path(store.odylith_projection_bundle.__file__),
            ]
        ),
        flags={
            "backend_dependencies_available": True,
            "storage": "lance_local_columnar",
        },
    )

    monkeypatch.setattr(store, "runtime_root", lambda **_kwargs: runtime_root)
    monkeypatch.setattr(
        store,
        "projection_input_fingerprint",
        lambda **kwargs: "fp-full" if kwargs.get("scope") == "full" else "fp-reasoning",
    )
    monkeypatch.setattr(
        store,
        "read_runtime_state",
        lambda **_kwargs: {"projection_fingerprint": "fp-old", "projection_scope": "reasoning"},
    )
    monkeypatch.setattr(store, "load_runtime_timing_summary", lambda **_kwargs: [])
    monkeypatch.setattr(store, "record_runtime_timing", lambda **kwargs: timing_rows.append(kwargs))
    monkeypatch.setattr(
        store.odylith_projection_bundle,
        "load_bundle_manifest",
        lambda **_kwargs: {
            "ready": True,
            "projection_fingerprint": "fp-full",
            "projection_scope": "full",
            "provenance": compiler_provenance,
        },
    )
    monkeypatch.setattr(
        store.odylith_projection_snapshot,
        "load_snapshot",
        lambda **_kwargs: {
            "ready": True,
            "tables": {"components": 1},
            "projection_fingerprint": "fp-full",
            "projection_scope": "full",
            "provenance": compiler_provenance,
        },
    )
    monkeypatch.setattr(
        store.odylith_memory_backend,
        "load_manifest",
        lambda **_kwargs: {
            "projection_fingerprint": "fp-full",
            "projection_scope": "full",
            "ready": True,
            "provenance": backend_provenance,
        },
    )
    monkeypatch.setattr(
        store.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        store.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **kwargs: kwargs.get("projection_scope") == "full"
        and kwargs.get("projection_fingerprint") == "fp-full",
    )
    monkeypatch.setattr(store, "preferred_watcher_backend", lambda **_kwargs: "poll")
    monkeypatch.setattr(store, "write_runtime_state", lambda **kwargs: state_writes.append(dict(kwargs["payload"])))

    summary = projection_compiler_runtime.warm_projections(
        repo_root=tmp_path,
        force=False,
        reason="query",
        scope="reasoning",
    )

    assert summary["projection_scope"] == "full"
    assert summary["projection_fingerprint"] == "fp-full"
    assert state_writes[-1]["projection_scope"] == "full"
    assert timing_rows[-1]["metadata"]["reused"] is True
    assert timing_rows[-1]["metadata"]["reused_projection_scope"] == "full"


def test_search_entities_payload_keeps_local_results_when_remote_only_is_misconfigured(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(projection_search_runtime, "_odylith_ablation_active", lambda **_: False)
    monkeypatch.setattr(projection_search_runtime, "_warm_runtime", lambda **_: True)
    monkeypatch.setattr(projection_search_runtime, "_env_truthy", lambda _name: False)
    monkeypatch.setattr(projection_search_runtime, "projection_input_fingerprint", lambda **_: "fp-1")
    monkeypatch.setattr(projection_search_runtime, "record_runtime_timing", lambda **_: None)
    monkeypatch.setattr(
        projection_search_runtime,
        "_full_scan_guidance",
        lambda **kwargs: {"performed": False, "reason": kwargs.get("reason", ""), "results": []},
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **_: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "exact_lookup",
        lambda **_: [],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "sparse_search",
        lambda **_: [
            {
                "doc_key": "component:odylith-memory-backend",
                "kind": "component",
                "entity_id": "odylith-memory-backend",
                "title": "Odylith Memory Backend",
                "path": "odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md",
                "score": 5.0,
            }
        ],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_remote_retrieval,
        "remote_config",
        lambda **_: {"enabled": False, "status": "misconfigured", "mode": "remote_only"},
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_remote_retrieval,
        "query_remote",
        lambda **_: (_ for _ in ()).throw(AssertionError("misconfigured remote must not be queried")),
    )

    payload = projection_search_runtime.search_entities_payload(
        repo_root=tmp_path,
        query="memory backend",
        limit=5,
    )

    assert payload["retrieval_mode"] == "tantivy_sparse"
    assert payload["results"][0]["source"] == "local"


def test_search_entities_payload_accepts_full_scope_backend_for_reasoning_queries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(projection_search_runtime, "_odylith_ablation_active", lambda **_: False)
    monkeypatch.setattr(projection_search_runtime, "_warm_runtime", lambda **_: True)
    monkeypatch.setattr(projection_search_runtime, "_env_truthy", lambda _name: False)
    monkeypatch.setattr(
        projection_search_runtime,
        "projection_input_fingerprint",
        lambda **kwargs: "fp-full" if kwargs.get("scope") == "full" else "fp-reasoning",
    )
    monkeypatch.setattr(projection_search_runtime, "record_runtime_timing", lambda **_: None)
    monkeypatch.setattr(
        projection_search_runtime,
        "_full_scan_guidance",
        lambda **kwargs: {"performed": False, "reason": kwargs.get("reason", ""), "results": []},
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **kwargs: kwargs.get("projection_scope") == "full"
        and kwargs.get("projection_fingerprint") == "fp-full",
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "_connect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full backend should avoid repair or fallback connect")),
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "exact_lookup",
        lambda **_: [],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "sparse_search",
        lambda **_: [
            {
                "doc_key": "component:odylith-memory-backend",
                "kind": "component",
                "entity_id": "odylith-memory-backend",
                "title": "Odylith Memory Backend",
                "path": "odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md",
                "score": 5.0,
            }
        ],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_remote_retrieval,
        "remote_config",
        lambda **_: {"enabled": False, "status": "disabled", "mode": "disabled"},
    )

    payload = projection_search_runtime.search_entities_payload(
        repo_root=tmp_path,
        query="memory backend",
        limit=5,
    )

    assert payload["retrieval_mode"] == "tantivy_sparse"
    assert payload["results"][0]["source"] == "local"


def test_search_entities_payload_keeps_local_results_when_remote_only_returns_no_hits(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(projection_search_runtime, "_odylith_ablation_active", lambda **_: False)
    monkeypatch.setattr(projection_search_runtime, "_warm_runtime", lambda **_: True)
    monkeypatch.setattr(projection_search_runtime, "_env_truthy", lambda _name: False)
    monkeypatch.setattr(projection_search_runtime, "projection_input_fingerprint", lambda **_: "fp-1")
    monkeypatch.setattr(projection_search_runtime, "record_runtime_timing", lambda **_: None)
    monkeypatch.setattr(
        projection_search_runtime,
        "_full_scan_guidance",
        lambda **kwargs: {"performed": False, "reason": kwargs.get("reason", ""), "results": []},
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **_: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "exact_lookup",
        lambda **_: [],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "sparse_search",
        lambda **_: [
            {
                "doc_key": "component:odylith-memory-backend",
                "kind": "component",
                "entity_id": "odylith-memory-backend",
                "title": "Odylith Memory Backend",
                "path": "odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md",
                "score": 5.0,
            }
        ],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_remote_retrieval,
        "remote_config",
        lambda **_: {"enabled": True, "status": "ready", "mode": "remote_only"},
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_remote_retrieval,
        "query_remote",
        lambda **_: [],
    )

    payload = projection_search_runtime.search_entities_payload(
        repo_root=tmp_path,
        query="memory backend",
        limit=5,
    )

    assert payload["retrieval_mode"] == "tantivy_sparse"
    assert payload["results"][0]["source"] == "local"


def test_clear_runtime_process_caches_clears_projection_input_fingerprints_for_repo_scoped_clear(
    tmp_path: Path,
) -> None:
    key = f"{tmp_path.resolve()}:reasoning"
    projection_search_runtime._PROCESS_PROJECTED_INPUTS_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_PROJECTED_INPUTS_CACHE[key] = ("state-1", {"components": "fp-components"})  # noqa: SLF001
    projection_search_runtime._PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE[key] = ("state-1", "fp-runtime")  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE[key] = 1.0  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS[key] = "fp-runtime"  # noqa: SLF001

    projection_search_runtime.clear_runtime_process_caches(repo_root=tmp_path)

    assert key not in projection_search_runtime._PROCESS_PROJECTED_INPUTS_CACHE  # noqa: SLF001
    assert key not in projection_search_runtime._PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE  # noqa: SLF001
    assert key not in projection_search_runtime._PROCESS_WARM_CACHE  # noqa: SLF001
    assert key not in projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS  # noqa: SLF001


def test_warm_runtime_reuses_compatible_snapshot_when_runtime_state_lags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001

    snapshot_path = tmp_path / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        projection_search_runtime,
        "read_runtime_state",
        lambda **_kwargs: {
            "projection_scope": "default",
            "projection_fingerprint": "fp-default-stale",
        },
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_projection_snapshot,
        "load_snapshot",
        lambda **_kwargs: {
            "ready": True,
            "projection_scope": "full",
            "projection_fingerprint": "fp-full-fresh",
        },
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "projection_input_fingerprint",
        lambda **kwargs: {
            "default": "fp-default-fresh",
            "reasoning": "fp-reasoning-fresh",
            "full": "fp-full-fresh",
        }[kwargs["scope"]],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "backend_dependencies_available",
        lambda: True,
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **kwargs: kwargs.get("projection_scope") == "full"
        and kwargs.get("projection_fingerprint") == "fp-full-fresh",
    )
    monkeypatch.setattr(
        projection_search_runtime,
        "warm_projections",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("compatible snapshot should avoid warm_projections")),
    )

    reused = projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=tmp_path,
        runtime_mode="auto",
        reason="test",
        scope="default",
    )

    assert reused is True
    assert projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:default"] == "fp-default-fresh"  # noqa: SLF001


def test_direct_warm_projections_primes_process_warm_cache_for_follow_on_runtime_reads(
    monkeypatch,
    tmp_path: Path,
) -> None:
    projection_search_runtime._PROCESS_WARM_CACHE.clear()  # noqa: SLF001
    projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS.clear()  # noqa: SLF001
    compiler_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        projection_search_runtime,
        "projection_input_fingerprint",
        lambda **kwargs: {
            "default": "fp-default",
            "reasoning": "fp-reasoning",
            "full": "fp-full",
        }[kwargs["scope"]],
    )
    monkeypatch.setattr(
        projection_search_runtime.odylith_context_engine_projection_compiler_runtime,
        "warm_projections",
        lambda **kwargs: compiler_calls.append(dict(kwargs)) or {"projection_scope": kwargs["scope"]},
    )

    projection_search_runtime.warm_projections(
        repo_root=tmp_path,
        force=False,
        reason="sync",
        scope="default",
    )

    monkeypatch.setattr(
        projection_search_runtime,
        "warm_projections",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("cached runtime should not rewarm projections")),
    )

    reused = projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=tmp_path,
        runtime_mode="auto",
        reason="bug_rows",
        scope="default",
    )

    assert reused is True
    assert compiler_calls == [
        {
            "repo_root": tmp_path,
            "force": False,
            "reason": "sync",
            "scope": "default",
        }
    ]
    assert projection_search_runtime._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:default"] == "fp-default"  # noqa: SLF001


def test_compact_context_dossier_for_delivery_uses_tight_defaults() -> None:
    compact = store.compact_context_dossier_for_delivery(
        {
            "resolved": True,
            "entity": {
                "entity_id": "B-031",
                "title": "Odylith First-Turn Bootstrap and Short-Form Grounding Commands",
                "status": "implementation",
                "priority": "P0",
                "related_diagram_ids": ["D-1", "D-2"],
            },
            "lookup": {"resolution_mode": "exact"},
            "related_entities": {
                "plans": [{"entity_id": "P-1"}, {"entity_id": "P-2"}, {"entity_id": "P-3"}],
            },
            agent_runtime_contract.AGENT_EVENT_KEY: [
                {"event_id": "1", "summary": "one"},
                {"event_id": "2", "summary": "two"},
                {"event_id": "3", "summary": "three"},
            ],
            "delivery_scopes": [
                {"label": "scope-a", "path": "a"},
                {"label": "scope-b", "path": "b"},
            ],
            "relations": [{"left": "a"}, {"left": "b"}, {"left": "c"}],
        }
    )

    assert compact["entity"]["diagram_id_count"] == 2
    assert compact["related_entities"]["plans"] == [{"entity_id": "P-1"}, {"entity_id": "P-2"}]
    assert len(compact[agent_runtime_contract.AGENT_EVENT_KEY]) == 2
    assert "recent_codex_events" not in compact
    assert len(compact["delivery_scope_summaries"]) == 1
    assert compact["relation_count"] == 3


def test_architecture_family_alias_keeps_shared_control_plane_slice_fail_closed() -> None:
    assert hot_path_runtime._hot_path_can_stay_fail_closed_without_full_scan(  # noqa: SLF001
        family_hint="tenant_boundary",
        changed_paths=["odylith/AGENTS.md", "odylith/radar/source/INDEX.md"],
        explicit_paths=[],
        selection_state="ambiguous",
        shared_only_input=True,
        working_tree_scope_degraded=False,
    ) is True
