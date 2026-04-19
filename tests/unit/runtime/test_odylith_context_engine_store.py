import json
from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_grounding_runtime as grounding_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import odylith_context_engine_packet_session_runtime as session_packet_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_registry_runtime as surface_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as projection_search_runtime
from odylith.runtime.context_engine import projection_repo_state_runtime
from odylith.runtime.common.consumer_profile import write_consumer_profile
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import sync_session


def test_load_backlog_detail_uses_cached_runtime_projection_rows(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    idea_path = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "b-999-fast-path.md"
    plan_path = repo_root / "odylith" / "technical-plans" / "b-999-plan.md"
    idea_path.parent.mkdir(parents=True)
    plan_path.parent.mkdir(parents=True)
    idea_path.write_text(
        "\n".join(
            [
                "idea_id: B-999",
                "title: Fast path",
                "",
                "## Context",
                "Runtime-backed workstream detail.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    plan_path.write_text("# Plan\n", encoding="utf-8")

    calls = {"execute": 0, "close": 0}

    class _FakeCursor:
        def fetchall(self) -> list[dict[str, str]]:
            return [
                {
                    "idea_id": "B-999",
                    "metadata_json": json.dumps(
                        {
                            "idea_id": "B-999",
                            "title": "Fast path",
                            "promoted_to_plan": "odylith/technical-plans/b-999-plan.md",
                        }
                    ),
                    "idea_file": str(idea_path),
                }
            ]

    class _FakeConnection:
        def execute(self, query: str):  # noqa: ANN001
            assert "FROM workstreams" in query
            calls["execute"] += 1
            return _FakeCursor()

        def close(self) -> None:
            calls["close"] += 1

    def _unexpected_markdown_scan(*, repo_root: Path) -> dict[str, object]:
        raise AssertionError(f"runtime fast path should avoid scanning markdown specs under {repo_root}")

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setenv("ODYLITH_ENABLED", "1")
    monkeypatch.setattr(store, "_connect", lambda repo_root: _FakeConnection())
    monkeypatch.setattr(store, "_load_idea_specs", _unexpected_markdown_scan)
    store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{repo_root.resolve()}:default"] = "test-fingerprint"  # noqa: SLF001

    first = store.load_backlog_detail(repo_root=repo_root, workstream_id="B-999", runtime_mode="local")
    second = store.load_backlog_detail(repo_root=repo_root, workstream_id="B-999", runtime_mode="local")

    assert first == second
    assert first["idea_id"] == "B-999"
    assert first["idea_file"] == "odylith/radar/source/ideas/2026-03/b-999-fast-path.md"
    assert first["title"] == "Fast path"
    assert first["metadata"] == {
        "idea_id": "B-999",
        "title": "Fast path",
        "promoted_to_plan": "odylith/technical-plans/b-999-plan.md",
    }
    assert first["sections"] == {
        "Context": "Runtime-backed workstream detail.",
    }
    assert first["search_body"] == idea_path.read_text(encoding="utf-8")
    assert first["promoted_to_plan"] == "odylith/technical-plans/b-999-plan.md"
    assert first["problem"] == ""
    assert first["customer"] == ""
    assert first["opportunity"] == ""
    assert first["founder_pov"] == ""
    assert first["success_metrics"] == ""
    assert calls == {"execute": 1, "close": 1}


def test_load_backlog_list_reuses_cached_runtime_rows(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"execute": 0, "close": 0}

    class _FakeCursor:
        def __init__(self, rows):  # noqa: ANN001
            self._rows = rows

        def fetchone(self):  # noqa: ANN001
            return self._rows[0] if self._rows else None

        def fetchall(self):  # noqa: ANN001
            return list(self._rows)

    class _FakeConnection:
        def execute(self, query: str, params=()):  # noqa: ANN001
            calls["execute"] += 1
            if "FROM projection_state" in query:
                return _FakeCursor([{"payload_json": json.dumps({"updated_utc": "2026-04-11T00:00:00Z"})}])
            section = str(params[0]) if params else ""
            return _FakeCursor(
                [
                    {
                        "rank": "1" if section == "active" else "-",
                        "idea_id": f"B-{section[:3].upper() or '000'}",
                        "title": f"{section.title()} item",
                        "priority": "P1",
                        "ordering_score": "100",
                        "metadata_json": json.dumps({"commercial_value": "4", "status": section}),
                        "idea_file": f"odylith/radar/source/ideas/{section}.md",
                    }
                ]
            )

        def close(self) -> None:
            calls["close"] += 1

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setitem(store.load_backlog_list.__globals__, "_warm_runtime", lambda **_kwargs: True)
    monkeypatch.setitem(store.load_backlog_list.__globals__, "projection_input_fingerprint", lambda **_kwargs: "projection-fingerprint")
    monkeypatch.setitem(store.load_backlog_list.__globals__, "_connect", lambda repo_root: _FakeConnection())
    monkeypatch.setitem(
        store.load_backlog_list.__globals__,
        "_load_backlog_projection",
        lambda **_kwargs: {"rationale_map": {"B-ACT": ["cached rationale"]}},
    )

    first = store.load_backlog_list(repo_root=repo_root, runtime_mode="auto")
    second = store.load_backlog_list(repo_root=repo_root, runtime_mode="auto")

    assert first == second
    assert first["updated_utc"] == "2026-04-11T00:00:00Z"
    assert first["rationale_map"] == {"B-ACT": ["cached rationale"]}
    assert calls == {"execute": 5, "close": 1}


def test_load_component_index_reuses_cached_runtime_rows(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"execute": 0, "close": 0}

    class _FakeCursor:
        def fetchall(self):  # noqa: ANN001
            return [
                {
                    "component_id": "odylith",
                    "name": "Odylith",
                    "aliases_json": "[]",
                    "workstreams_json": "[\"B-091\"]",
                    "diagrams_json": "[\"D-036\"]",
                    "owner": "freedom-research",
                    "status": "active",
                    "spec_ref": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
                    "metadata_json": json.dumps({"component_id": "odylith", "name": "Odylith"}),
                }
            ]

    class _FakeConnection:
        def execute(self, query: str):  # noqa: ANN001
            assert "FROM components" in query
            calls["execute"] += 1
            return _FakeCursor()

        def close(self) -> None:
            calls["close"] += 1

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setitem(store.load_component_index.__globals__, "_warm_runtime", lambda **_kwargs: True)
    monkeypatch.setitem(
        store.load_component_index.__globals__,
        "projection_input_fingerprint",
        lambda **_kwargs: "projection-fingerprint",
    )
    monkeypatch.setitem(store.load_component_index.__globals__, "_connect", lambda repo_root: _FakeConnection())

    first = store.load_component_index(repo_root=repo_root, runtime_mode="auto")
    second = store.load_component_index(repo_root=repo_root, runtime_mode="auto")

    assert first.keys() == {"odylith"}
    assert first == second
    assert calls == {"execute": 1, "close": 1}


def test_load_backlog_detail_falls_back_to_markdown_specs_when_runtime_not_ready(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    idea_path = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "b-010-fallback.md"
    plan_path = repo_root / "odylith" / "technical-plans" / "b-010-plan.md"
    index_path = repo_root / "odylith" / "radar" / "source" / "INDEX.md"
    plans_index_path = repo_root / "odylith" / "technical-plans" / "INDEX.md"
    idea_path.parent.mkdir(parents=True)
    plan_path.parent.mkdir(parents=True)
    index_path.write_text("# Radar\n", encoding="utf-8")
    plans_index_path.write_text("# Plans\n", encoding="utf-8")
    plan_path.write_text("# Plan\n", encoding="utf-8")
    idea_path.write_text(
        "\n".join(
            [
                "idea_id: B-010",
                "title: Fallback detail",
                "promoted_to_plan: odylith/technical-plans/b-010-plan.md",
                "",
                "## Summary",
                "Fallback markdown parsing still works.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setenv("ODYLITH_ENABLED", "1")

    detail = store.load_backlog_detail(repo_root=repo_root, workstream_id="B-010", runtime_mode="local")

    assert detail is not None
    assert detail["idea_file"] == "odylith/radar/source/ideas/2026-03/b-010-fallback.md"
    assert detail["promoted_to_plan"] == "odylith/technical-plans/b-010-plan.md"
    assert detail["title"] == "Fallback detail"
    assert detail["metadata"]["title"] == "Fallback detail"
    assert detail["sections"] == {"Summary": "Fallback markdown parsing still works."}


def test_load_backlog_detail_grounding_light_skips_markdown_body_load(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    idea_path = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "b-011-light.md"
    idea_path.parent.mkdir(parents=True)
    idea_path.write_text(
        "\n".join(
            [
                "idea_id: B-011",
                "title: Light detail",
                "promoted_to_plan: odylith/technical-plans/b-011-plan.md",
                "",
                "## Summary",
                "This body should not be loaded for grounding_light.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setenv("ODYLITH_ENABLED", "1")
    monkeypatch.setattr(store, "_runtime_backlog_detail", lambda **kwargs: None)
    monkeypatch.setattr(
        store,
        "_raw_text",
        lambda path: (_ for _ in ()).throw(AssertionError(f"grounding_light should not read markdown body from {path}")),
    )

    detail = store.load_backlog_detail(
        repo_root=repo_root,
        workstream_id="B-011",
        runtime_mode="local",
        detail_level="grounding_light",
    )

    assert detail == {
        "idea_id": "B-011",
        "idea_file": "odylith/radar/source/ideas/2026-03/b-011-light.md",
        "metadata": {
            "idea_id": "B-011",
            "title": "Light detail",
            "promoted_to_plan": "odylith/technical-plans/b-011-plan.md",
        },
        "promoted_to_plan": "odylith/technical-plans/b-011-plan.md",
    }


def test_load_registry_detail_grounding_light_skips_component_timeline_build(monkeypatch) -> None:
    entry = component_registry.ComponentEntry(
        component_id="benchmark",
        name="Benchmark",
        kind="component",
        category="governance_surface",
        qualification="curated",
        aliases=[],
        path_prefixes=["src/odylith/runtime/evaluation/"],
        workstreams=["B-022"],
        diagrams=["D-024"],
        owner="freedom-research",
        status="active",
        what_it_is="Benchmark subsystem.",
        why_tracked="Release proof depends on it.",
        spec_ref="odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        sources=[],
    )
    snapshot = {
        "report": component_registry.ComponentRegistryReport(
            components={"benchmark": entry},
            mapped_events=[],
            unmapped_meaningful_events=[],
            candidate_queue=[],
            forensic_coverage={
                "benchmark": component_registry.ComponentForensicCoverage(
                    status="forensic_coverage_present",
                    timeline_event_count=2,
                    explicit_event_count=1,
                    recent_path_match_count=1,
                    mapped_workstream_evidence_count=1,
                    spec_history_event_count=1,
                    empty_reasons=[],
                )
            },
            diagnostics=[],
        ),
        "spec_snapshots": {
            "benchmark": component_registry.ComponentSpecSnapshot(
                title="Benchmark",
                last_updated="2026-03-31",
                feature_history=[],
                markdown="# Benchmark\n",
            )
        },
        "traceability": {
            "benchmark": {
                "runbooks": ["odylith/MAINTAINER_RELEASE_RUNBOOK.md"],
                "developer_docs": ["docs/benchmarks/README.md"],
                "code_references": ["src/odylith/runtime/evaluation/odylith_benchmark_graphs.py"],
            }
        },
    }

    monkeypatch.setattr(
        surface_runtime,
        "load_component_registry_snapshot",
        lambda **kwargs: snapshot,
    )
    monkeypatch.setattr(
        surface_runtime,
        "_connect",
        lambda repo_root: (_ for _ in ()).throw(RuntimeError("no runtime snapshot")),
    )
    monkeypatch.setattr(
        component_registry,
        "build_component_timelines",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("grounding_light should skip component timeline assembly")),
    )

    detail = surface_runtime.load_registry_detail(
        repo_root=Path("."),
        component_id="benchmark",
        runtime_mode="local",
        detail_level="grounding_light",
    )

    assert detail is not None
    assert detail["component"] == entry
    assert detail["timeline"] == []
    assert detail["traceability"]["developer_docs"] == ["docs/benchmarks/README.md"]


def test_load_registry_detail_grounding_light_uses_cached_runtime_projection_rows(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"connect": 0, "execute": 0, "close": 0}
    entry = component_registry.ComponentEntry(
        component_id="benchmark",
        name="Benchmark",
        kind="component",
        category="governance_surface",
        qualification="curated",
        aliases=[],
        path_prefixes=["src/odylith/runtime/evaluation/"],
        workstreams=["B-022"],
        diagrams=["D-024"],
        owner="freedom-research",
        status="active",
        what_it_is="Benchmark subsystem.",
        why_tracked="Release proof depends on it.",
        spec_ref="odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        sources=[],
    )

    class _FakeCursor:
        def __init__(self, *, row: dict[str, object] | None = None, rows: list[dict[str, object]] | None = None) -> None:
            self._row = row
            self._rows = list(rows or [])

        def fetchone(self) -> dict[str, object] | None:
            return self._row

        def fetchall(self) -> list[dict[str, object]]:
            return list(self._rows)

    class _FakeConnection:
        def execute(self, query: str, params: tuple[object, ...] = ()) -> _FakeCursor:
            del params
            calls["execute"] += 1
            normalized = " ".join(query.split())
            if "FROM components" in normalized:
                return _FakeCursor(row={"component_id": "benchmark"})
            if "FROM component_specs" in normalized:
                return _FakeCursor(
                    row={
                        "title": "Benchmark",
                        "last_updated": "2026-03-31",
                        "feature_history_json": "[]",
                        "markdown": "# Benchmark\n",
                        "skill_trigger_tiers_json": "{}",
                        "skill_trigger_structure": "legacy",
                        "validation_playbook_commands_json": "[]",
                    }
                )
            if "FROM component_traceability" in normalized:
                return _FakeCursor(rows=[{"bucket": "developer_docs", "path": "docs/benchmarks/README.md"}])
            raise AssertionError(f"unexpected query: {query}")

        def close(self) -> None:
            calls["close"] += 1

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setenv("ODYLITH_ENABLED", "1")
    monkeypatch.setattr(
        surface_runtime,
        "_component_entry_from_runtime_row",
        lambda row: entry if row.get("component_id") == "benchmark" else None,
    )
    monkeypatch.setattr(
        surface_runtime,
        "_connect",
        lambda repo_root: (calls.__setitem__("connect", calls["connect"] + 1) or _FakeConnection()),
    )
    surface_runtime._PROCESS_WARM_CACHE_FINGERPRINTS[f"{repo_root.resolve()}:reasoning"] = "test-fingerprint"  # noqa: SLF001

    first = surface_runtime.load_registry_detail(
        repo_root=repo_root,
        component_id="benchmark",
        runtime_mode="local",
        detail_level="grounding_light",
    )
    second = surface_runtime.load_registry_detail(
        repo_root=repo_root,
        component_id="benchmark",
        runtime_mode="local",
        detail_level="grounding_light",
    )

    assert first == second
    assert first is not None
    assert first["component"] == entry
    assert first["traceability"]["developer_docs"] == ["docs/benchmarks/README.md"]
    assert calls == {"connect": 1, "execute": 3, "close": 1}


def test_load_registry_detail_grounding_light_uses_runtime_component_fast_path(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"close": 0}

    class _FakeCursor:
        def __init__(self, payload):  # noqa: ANN001
            self._payload = payload

        def fetchone(self):  # noqa: ANN201
            return self._payload

        def fetchall(self):  # noqa: ANN201
            return list(self._payload)

    class _FakeConnection:
        def execute(self, query: str, params=()):  # noqa: ANN001
            normalized = " ".join(query.split())
            if "FROM components" in normalized:
                assert params == ("benchmark",)
                return _FakeCursor(
                    {
                        "component_id": "benchmark",
                        "name": "Benchmark",
                        "aliases_json": json.dumps(["bench"]),
                        "workstreams_json": json.dumps(["B-022"]),
                        "diagrams_json": json.dumps(["D-024"]),
                        "owner": "freedom-research",
                        "status": "active",
                        "spec_ref": "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                        "metadata_json": json.dumps(
                            {
                                "component_id": "benchmark",
                                "name": "Benchmark",
                                "kind": "component",
                                "category": "governance_surface",
                                "qualification": "curated",
                                "aliases": ["bench"],
                                "path_prefixes": ["src/odylith/runtime/evaluation/"],
                                "workstreams": ["B-022"],
                                "diagrams": ["D-024"],
                                "owner": "freedom-research",
                                "status": "active",
                                "what_it_is": "Benchmark subsystem.",
                                "why_tracked": "Release proof depends on it.",
                                "spec_ref": "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                                "sources": [],
                                "product_layer": "evidence_surface",
                            }
                        ),
                    }
                )
            if "FROM component_specs" in normalized:
                assert params == ("benchmark",)
                return _FakeCursor(
                    {
                        "title": "Benchmark",
                        "last_updated": "2026-03-31",
                        "feature_history_json": json.dumps(
                            [{"date": "2026-03-30", "summary": "Publication proof tightened."}]
                        ),
                        "markdown": "# Benchmark\n",
                        "skill_trigger_tiers_json": json.dumps({}),
                        "skill_trigger_structure": "legacy",
                        "validation_playbook_commands_json": json.dumps([]),
                    }
                )
            if "FROM component_traceability" in normalized:
                assert params == ("benchmark",)
                return _FakeCursor(
                    [
                        {"bucket": "developer_docs", "path": "docs/benchmarks/README.md"},
                        {"bucket": "developer_docs", "path": "docs/benchmarks/README.md"},
                        {"bucket": "code_references", "path": "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py"},
                    ]
                )
            raise AssertionError(f"unexpected query: {normalized}")

        def close(self) -> None:
            calls["close"] += 1

    monkeypatch.setattr(surface_runtime, "_warm_runtime", lambda **kwargs: True)
    monkeypatch.setattr(surface_runtime, "_odylith_ablation_active", lambda **kwargs: False)
    monkeypatch.setattr(surface_runtime, "_connect", lambda repo_root: _FakeConnection())
    monkeypatch.setattr(
        surface_runtime,
        "load_component_registry_snapshot",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("grounding_light fast path should avoid full snapshot assembly")),
    )

    detail = surface_runtime.load_registry_detail(
        repo_root=repo_root,
        component_id="benchmark",
        runtime_mode="local",
        detail_level="grounding_light",
    )

    assert detail is not None
    component = detail["component"]
    assert isinstance(component, component_registry.ComponentEntry)
    assert component.component_id == "benchmark"
    assert detail["traceability"] == {
        "runbooks": [],
        "developer_docs": ["docs/benchmarks/README.md"],
        "code_references": ["src/odylith/runtime/evaluation/odylith_benchmark_graphs.py"],
    }
    assert detail["timeline"] == []
    assert detail["forensic_coverage"]["status"] == "baseline_forensic_only"
    assert detail["spec_snapshot"].title == "Benchmark"
    assert calls["close"] == 1


def test_build_session_brief_forwards_retain_impact_internal_context(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_build_session_brief(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {"changed_paths": list(kwargs.get("changed_paths", []))}

    monkeypatch.setattr(session_packet_runtime, "build_session_brief", _fake_build_session_brief)

    payload = store.build_session_brief(
        repo_root=tmp_path,
        changed_paths=["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="exact_path_ambiguity",
        retain_impact_internal_context=False,
        skip_impact_runtime_warmup=True,
    )

    assert payload == {"changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"]}
    assert captured["retain_impact_internal_context"] is False
    assert captured["skip_impact_runtime_warmup"] is True


def test_build_session_bootstrap_forwards_retain_impact_internal_context(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_build_session_bootstrap(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {"changed_paths": list(kwargs.get("changed_paths", []))}

    monkeypatch.setattr(session_packet_runtime, "build_session_bootstrap", _fake_build_session_bootstrap)

    payload = store.build_session_bootstrap(
        repo_root=tmp_path,
        changed_paths=["AGENTS.md", "odylith/AGENTS.md"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="broad_shared_scope",
        retain_impact_internal_context=False,
        skip_impact_runtime_warmup=True,
    )

    assert payload == {"changed_paths": ["AGENTS.md", "odylith/AGENTS.md"]}
    assert captured["retain_impact_internal_context"] is False
    assert captured["skip_impact_runtime_warmup"] is True


def test_build_session_brief_hot_path_requests_unfinalized_impact(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_build_impact_report(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {
            "changed_paths": list(kwargs.get("changed_paths", [])),
            "explicit_paths": list(kwargs.get("changed_paths", [])),
            "candidate_workstreams": [],
            "workstream_selection": {"state": "none", "reason": "narrow first"},
            "selection_state": "none",
            "selection_reason": "narrow first",
            "selection_confidence": "low",
            "context_packet_state": "gated_ambiguous",
            "components": [],
            "diagrams": [],
            "docs": [],
            "recommended_commands": [],
            "recommended_tests": [],
            "engineering_notes": {},
            "miss_recovery": {},
            "truncation": {},
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": {},
        }

    monkeypatch.setattr(session_packet_runtime, "build_impact_report", _fake_build_impact_report)

    payload = session_packet_runtime.build_session_brief(
        repo_root=tmp_path,
        changed_paths=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="release_publication",
    )

    assert isinstance(payload.get("context_packet"), dict)
    assert captured["finalize_packet"] is False


def test_build_session_brief_hot_path_preserves_guidance_behavior_contract(monkeypatch, tmp_path: Path) -> None:
    def _fake_build_impact_report(**kwargs):  # noqa: ANN001
        return {
            "changed_paths": list(kwargs.get("changed_paths", [])),
            "explicit_paths": list(kwargs.get("changed_paths", [])),
            "candidate_workstreams": [],
            "workstream_selection": {"state": "none", "reason": "narrow first"},
            "selection_state": "none",
            "selection_reason": "narrow first",
            "selection_confidence": "low",
            "context_packet_state": "gated_ambiguous",
            "components": [],
            "diagrams": [],
            "docs": [],
            "recommended_commands": [],
            "recommended_tests": [],
            "engineering_notes": {},
            "miss_recovery": {},
            "truncation": {},
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": {},
        }

    guidance_summary = {
        "contract": "odylith_guidance_behavior_runtime_summary.v1",
        "family": "guidance_behavior",
        "status": "available",
        "validation_status": "not_run",
        "case_count": 6,
        "validator_command": "odylith validate guidance-behavior --repo-root .",
        "runtime_layer_contract": {
            "contract": "odylith_guidance_behavior_runtime_layers.v1",
            "layers": [
                "context_engine",
                "execution_engine",
                "memory_substrate",
                "intervention_engine",
                "tribunal",
            ],
            "hot_path": {"summary_only": True, "provider_calls": False},
        },
    }
    captured_summary_kwargs: dict[str, object] = {}

    monkeypatch.setattr(session_packet_runtime, "build_impact_report", _fake_build_impact_report)

    def _fake_summary_for_packet(**kwargs):  # noqa: ANN001
        captured_summary_kwargs.update(kwargs)
        return dict(guidance_summary)

    monkeypatch.setattr(
        session_packet_runtime.tooling_context_packet_builder.guidance_behavior_runtime,
        "summary_for_packet",
        _fake_summary_for_packet,
    )

    payload = session_packet_runtime.build_session_brief(
        repo_root=tmp_path,
        changed_paths=["src/odylith/runtime/governance/validate_guidance_behavior.py"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="guidance_behavior",
        validation_command_hints=[
            "odylith validate guidance-behavior --repo-root . --case-id guidance-cli-first-governed-truth"
        ],
    )

    context_packet = dict(payload.get("context_packet", {}))
    summary = dict(context_packet.get("guidance_behavior_summary", {}))
    recommended_validation = dict(
        dict(context_packet.get("execution_engine_handshake", {})).get("recommended_validation", {})
    )

    assert summary["status"] == "available"
    assert summary["runtime_layer_contract"]["layers"] == [
        "context_engine",
        "execution_engine",
        "memory_substrate",
        "intervention_engine",
        "tribunal",
    ]
    assert recommended_validation["guidance_behavior_status"] == "available"
    assert list(captured_summary_kwargs["recommended_commands"]) == [
        "odylith validate guidance-behavior --repo-root . --case-id guidance-cli-first-governed-truth"
    ]
    assert payload["recommended_commands"] == [
        "odylith validate guidance-behavior --repo-root . --case-id guidance-cli-first-governed-truth",
        guidance_summary["validator_command"],
    ]


def test_build_governance_slice_hot_path_requests_unfinalized_impact(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    detail_levels: list[str] = []

    def _fake_build_impact_report(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {
            "changed_paths": list(kwargs.get("changed_paths", [])),
            "explicit_paths": list(kwargs.get("changed_paths", [])),
            "candidate_workstreams": [],
            "workstream_selection": {"state": "explicit", "reason": "exact slice"},
            "selection_state": "explicit",
            "selection_reason": "exact slice",
            "selection_confidence": "high",
            "context_packet_state": "compact",
            "components": [],
            "diagrams": [],
            "bugs": [],
            "docs": [],
            "recommended_commands": [],
            "benchmark_selector_diagnostics": {},
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": {},
        }

    monkeypatch.setattr(grounding_runtime, "build_impact_report", _fake_build_impact_report)

    def _fake_load_backlog_detail(**kwargs):  # noqa: ANN001
        detail_levels.append(str(kwargs.get("detail_level", "full")).strip() or "full")
        return None

    monkeypatch.setattr(grounding_runtime, "load_backlog_detail", _fake_load_backlog_detail)
    monkeypatch.setattr(grounding_runtime, "load_registry_detail", lambda **kwargs: None)
    monkeypatch.setattr(grounding_runtime, "_governance_surface_refs", lambda **kwargs: {"impacted_surfaces": {}, "reasons": {}})
    monkeypatch.setattr(grounding_runtime, "_governance_closeout_docs", lambda **kwargs: [])
    monkeypatch.setattr(grounding_runtime, "_governance_diagram_catalog_companions", lambda **kwargs: [])
    monkeypatch.setattr(grounding_runtime, "_companion_context_paths", lambda **kwargs: [])
    monkeypatch.setattr(grounding_runtime, "_bounded_explicit_governance_closeout_docs", lambda **kwargs: [])

    payload = grounding_runtime.build_governance_slice(
        repo_root=tmp_path,
        changed_paths=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="release_publication",
    )

    assert isinstance(payload.get("context_packet"), dict)
    assert captured["finalize_packet"] is False
    assert detail_levels == []


def test_build_governance_slice_hot_path_uses_grounding_light_workstream_detail(monkeypatch, tmp_path: Path) -> None:
    detail_levels: list[str] = []

    def _fake_build_impact_report(**kwargs):  # noqa: ANN001
        return {
            "changed_paths": list(kwargs.get("changed_paths", [])),
            "explicit_paths": list(kwargs.get("changed_paths", [])),
            "candidate_workstreams": [{"entity_id": "B-020", "title": "Benchmark proof"}],
            "workstream_selection": {
                "state": "explicit",
                "reason": "exact slice",
                "selected_workstream": {"entity_id": "B-020", "title": "Benchmark proof"},
            },
            "selection_state": "explicit",
            "selection_reason": "exact slice",
            "selection_confidence": "high",
            "context_packet_state": "compact",
            "components": [],
            "diagrams": [],
            "bugs": [],
            "docs": [],
            "recommended_commands": [],
            "benchmark_selector_diagnostics": {},
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": {},
        }

    def _fake_load_backlog_detail(**kwargs):  # noqa: ANN001
        detail_levels.append(str(kwargs.get("detail_level", "full")).strip() or "full")
        return {
            "idea_id": "B-020",
            "idea_file": "odylith/radar/source/ideas/2026-03/b-020.md",
            "metadata": {"title": "Benchmark proof", "status": "active"},
            "promoted_to_plan": "",
        }

    monkeypatch.setattr(grounding_runtime, "build_impact_report", _fake_build_impact_report)
    monkeypatch.setattr(grounding_runtime, "load_backlog_detail", _fake_load_backlog_detail)
    monkeypatch.setattr(grounding_runtime, "load_registry_detail", lambda **kwargs: None)
    monkeypatch.setattr(grounding_runtime, "_governance_surface_refs", lambda **kwargs: {"impacted_surfaces": {}, "reasons": {}})
    monkeypatch.setattr(grounding_runtime, "_governance_closeout_docs", lambda **kwargs: [])
    monkeypatch.setattr(grounding_runtime, "_governance_diagram_catalog_companions", lambda **kwargs: [])
    monkeypatch.setattr(grounding_runtime, "_companion_context_paths", lambda **kwargs: [])
    monkeypatch.setattr(grounding_runtime, "_bounded_explicit_governance_closeout_docs", lambda **kwargs: [])

    payload = grounding_runtime.build_governance_slice(
        repo_root=tmp_path,
        changed_paths=["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"],
        workstream="B-020",
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="component_governance",
    )

    assert isinstance(payload.get("context_packet"), dict)
    assert detail_levels
    assert set(detail_levels) == {"grounding_light"}


def test_build_governance_slice_hot_path_prefers_authoritative_governance_docs_before_finalize(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_build_impact_report(**kwargs):  # noqa: ANN001
        return {
            "changed_paths": list(kwargs.get("changed_paths", [])),
            "explicit_paths": list(kwargs.get("changed_paths", [])),
            "candidate_workstreams": [{"entity_id": "B-020", "title": "Benchmark proof"}],
            "workstream_selection": {
                "state": "explicit",
                "reason": "exact slice",
                "selected_workstream": {"entity_id": "B-020", "title": "Benchmark proof"},
            },
            "selection_state": "explicit",
            "selection_reason": "exact slice",
            "selection_confidence": "high",
            "context_packet_state": "compact",
            "components": [],
            "diagrams": [],
            "bugs": [],
            "docs": ["docs/benchmarks/README.md", "README.md"],
            "recommended_commands": [],
            "benchmark_selector_diagnostics": {},
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": {},
        }

    def _fake_finalize_packet(**kwargs):  # noqa: ANN001
        captured["docs"] = list(kwargs.get("docs", []))
        return {"context_packet": {}, "route_ready": True}

    monkeypatch.setattr(grounding_runtime, "build_impact_report", _fake_build_impact_report)
    monkeypatch.setattr(grounding_runtime, "load_backlog_detail", lambda **kwargs: None)
    monkeypatch.setattr(grounding_runtime, "load_registry_detail", lambda **kwargs: None)
    monkeypatch.setattr(grounding_runtime, "_governance_surface_refs", lambda **kwargs: {"impacted_surfaces": {}, "reasons": {}})
    monkeypatch.setattr(grounding_runtime, "_governance_closeout_docs", lambda **kwargs: ["README.md", "docs/benchmarks/README.md"])
    monkeypatch.setattr(grounding_runtime, "_governance_diagram_catalog_companions", lambda **kwargs: ["odylith/atlas/source/catalog/diagrams.v1.json"])
    monkeypatch.setattr(grounding_runtime, "_companion_context_paths", lambda **kwargs: ["odylith/technical-plans/example.md"])
    monkeypatch.setattr(grounding_runtime, "_bounded_explicit_governance_closeout_docs", lambda **kwargs: list(kwargs.get("docs", [])))
    monkeypatch.setattr(
        grounding_runtime,
        "_governance_hot_path_docs",
        lambda **kwargs: ["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"],
    )
    monkeypatch.setattr(grounding_runtime, "_compact_hot_path_runtime_packet", lambda **kwargs: dict(kwargs.get("payload", {})))
    monkeypatch.setattr(store.tooling_context_packet_builder, "finalize_packet", _fake_finalize_packet)

    payload = grounding_runtime.build_governance_slice(
        repo_root=tmp_path,
        changed_paths=["README.md"],
        workstream="B-020",
        component="benchmark",
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="component_governance",
    )

    assert captured["docs"] == ["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"]
    assert payload["governance_hot_path_docs"] == ["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"]
    assert payload["governance_hot_path_docs_authoritative"] is True


def test_load_registry_detail_full_builds_component_timeline(monkeypatch) -> None:
    entry = component_registry.ComponentEntry(
        component_id="benchmark",
        name="Benchmark",
        kind="component",
        category="governance_surface",
        qualification="curated",
        aliases=[],
        path_prefixes=["src/odylith/runtime/evaluation/"],
        workstreams=["B-022"],
        diagrams=["D-024"],
        owner="freedom-research",
        status="active",
        what_it_is="Benchmark subsystem.",
        why_tracked="Release proof depends on it.",
        spec_ref="odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        sources=[],
    )
    event = component_registry.MappedEvent(
        event_index=1,
        ts_iso="2026-03-31T00:00:00Z",
        kind="decision",
        summary="Benchmark publication adjusted.",
        workstreams=["B-022"],
        artifacts=["README.md"],
        explicit_components=["benchmark"],
        mapped_components=["benchmark"],
        confidence="high",
        meaningful=True,
    )
    snapshot = {
        "report": component_registry.ComponentRegistryReport(
            components={"benchmark": entry},
            mapped_events=[event],
            unmapped_meaningful_events=[],
            candidate_queue=[],
            forensic_coverage={},
            diagnostics=[],
        ),
        "spec_snapshots": {},
        "traceability": {},
    }

    calls = {"count": 0}

    def _fake_timelines(**kwargs):  # noqa: ANN003
        calls["count"] += 1
        return {"benchmark": [event]}

    monkeypatch.setattr(
        surface_runtime,
        "load_component_registry_snapshot",
        lambda **kwargs: snapshot,
    )
    monkeypatch.setattr(component_registry, "build_component_timelines", _fake_timelines)

    detail = surface_runtime.load_registry_detail(
        repo_root=Path("."),
        component_id="benchmark",
        runtime_mode="local",
        detail_level="full",
    )

    assert detail is not None
    assert calls["count"] == 1
    assert detail["timeline"] == [event]


def test_connect_reuses_projection_connection_for_stable_snapshot(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    snapshot_path = repo_root / ".odylith" / "runtime" / "odylith-compiler" / "projection-snapshot.v1.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "ready": True,
                "tables": {
                    "projection_state": [],
                    "workstreams": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    store.clear_runtime_process_caches(repo_root=repo_root)

    first = store._connect(repo_root)  # noqa: SLF001
    second = store._connect(repo_root)  # noqa: SLF001

    assert first is second


def test_path_signal_profile_uses_custom_consumer_truth_roots(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "consumer-registry" / "source" / "components" / "compass").mkdir(parents=True)
    (repo_root / "consumer-runbooks" / "platform").mkdir(parents=True)
    write_consumer_profile(
        repo_root=repo_root,
        payload={
            "truth_roots": {
                "component_specs": "consumer-registry/source/components",
                "runbooks": "consumer-runbooks/platform",
            }
        },
    )
    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.chdir(repo_root)

    spec_profile = store._path_signal_profile("consumer-registry/source/components/compass/CURRENT_SPEC.md")  # noqa: SLF001
    runbook_profile = store._path_signal_profile("consumer-runbooks/platform/router.md")  # noqa: SLF001

    assert spec_profile == {"category": "component_spec", "weight": 10, "shared": False}
    assert runbook_profile == {"category": "runbook", "weight": 9, "shared": False}


def test_projection_input_fingerprint_reuses_cached_inputs_for_same_repo_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"count": 0}

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setattr(
        projection_repo_state_runtime,
        "projection_repo_state_token",
        lambda **_: "state-a",
    )

    def _fake_inputs(*, repo_root: Path, scope: str = "default") -> dict[str, str]:
        calls["count"] += 1
        return {"workstreams": f"fp-{calls['count']}", "scope": scope, "repo": str(repo_root)}

    monkeypatch.setattr(
        projection_search_runtime,
        "_compute_projected_input_fingerprints",
        _fake_inputs,
    )

    first = projection_search_runtime.projection_input_fingerprint(repo_root=repo_root, scope="default")
    second = projection_search_runtime.projection_input_fingerprint(repo_root=repo_root, scope="default")

    assert first == second
    assert calls["count"] == 1


def test_projection_input_fingerprint_recomputes_when_repo_state_changes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"count": 0}
    state_tokens = iter(["state-a", "state-a", "state-b", "state-b"])

    store.clear_runtime_process_caches(repo_root=repo_root)
    monkeypatch.setattr(
        projection_repo_state_runtime,
        "projection_repo_state_token",
        lambda **_: next(state_tokens),
    )

    def _fake_inputs(*, repo_root: Path, scope: str = "default") -> dict[str, str]:
        calls["count"] += 1
        return {"workstreams": f"fp-{calls['count']}", "scope": scope, "repo": str(repo_root)}

    monkeypatch.setattr(
        projection_search_runtime,
        "_compute_projected_input_fingerprints",
        _fake_inputs,
    )

    first = projection_search_runtime.projection_input_fingerprint(repo_root=repo_root, scope="default")
    second = projection_search_runtime.projection_input_fingerprint(repo_root=repo_root, scope="default")

    assert first != second
    assert calls["count"] == 2


def test_load_delivery_surface_payload_reuses_sync_session_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"artifact": 0, "slice": 0}

    monkeypatch.setattr(store, "_warm_runtime", lambda **_: False)
    monkeypatch.setattr(store, "_odylith_switch_snapshot", lambda **_: {"enabled": True})
    monkeypatch.setattr(store, "load_orchestration_adoption_snapshot", lambda **_: {"status": "ready"})

    def _fake_artifact(*, repo_root: Path) -> dict[str, object]:
        assert repo_root == repo_root.resolve()
        calls["artifact"] += 1
        return {"shell": {"summary": {"count": 1}}, "workstreams": {"B-091": {"status": "active"}}}

    def _fake_slice(*, payload, surface: str):  # noqa: ANN001
        calls["slice"] += 1
        return {
            "surface": surface,
            "summary": dict(payload.get("shell", {}).get("summary", {})),
            "workstreams": dict(payload.get("workstreams", {})),
        }

    monkeypatch.setattr(store.delivery_intelligence_engine, "load_delivery_intelligence_artifact", _fake_artifact)
    monkeypatch.setattr(store.delivery_intelligence_engine, "slice_delivery_intelligence_for_surface", _fake_slice)

    with sync_session.activate_sync_session(sync_session.GovernedSyncSession(repo_root=repo_root)):
        first = store.load_delivery_surface_payload(
            repo_root=repo_root,
            surface="shell",
            runtime_mode="standalone",
            include_shell_snapshots=False,
        )
        second = store.load_delivery_surface_payload(
            repo_root=repo_root,
            surface="shell",
            runtime_mode="standalone",
            include_shell_snapshots=False,
        )

    assert first == second
    assert first is not second
    assert calls == {"artifact": 1, "slice": 1}


def test_warm_runtime_reuses_sync_session_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    calls = {"count": 0}

    def _fake_warm_runtime_uncached(**kwargs):  # noqa: ANN003
        assert kwargs["repo_root"] == repo_root.resolve()
        calls["count"] += 1
        return True

    monkeypatch.setattr(projection_search_runtime, "_warm_runtime_uncached", _fake_warm_runtime_uncached)

    with sync_session.activate_sync_session(sync_session.GovernedSyncSession(repo_root=repo_root)):
        assert projection_search_runtime._warm_runtime(  # noqa: SLF001
            repo_root=repo_root,
            runtime_mode="auto",
            reason="test",
            scope="default",
        )
        assert projection_search_runtime._warm_runtime(  # noqa: SLF001
            repo_root=repo_root,
            runtime_mode="auto",
            reason="test",
            scope="default",
        )

    assert calls["count"] == 1
