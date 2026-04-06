from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine as context_engine
from odylith.runtime.context_engine import odylith_context_engine_store as store


def test_build_memory_areas_snapshot_uses_judgment_memory_posture() -> None:
    payload = store._build_memory_areas_snapshot(  # noqa: SLF001
        enabled=True,
        authoritative_truth={"read_only_repo_truth": True},
        compiler_state={"ready": True},
        guidance_catalog={"chunk_count": 12, "source_doc_count": 4, "task_family_count": 3},
        runtime_state={"active_sessions": 1, "bootstrap_packets": 2},
        entity_counts={"indexed_entity_count": 88, "evidence_documents": 44},
        backend_transition={
            "status": "standardized",
            "actual_local_backend": {
                "storage": "lance_local_columnar",
                "sparse_recall": "tantivy_sparse_recall",
            },
        },
        optimization={"sample_size": 6, "coverage_rate": 0.75, "satisfaction_rate": 0.5},
        evaluation={},
        judgment_memory={
            "areas": [
                {"key": "decisions", "state": "strong", "summary": "Done plans and benchmark proof are retained."},
                {"key": "workspace_actor", "state": "strong", "summary": "Workspace and actor identity are retained."},
                {"key": "outcomes", "state": "strong", "summary": "Benchmark deltas and finished workstreams are retained."},
                {"key": "contradictions", "state": "partial", "summary": "One contradiction remains open."},
            ]
        },
    )

    assert payload["contract"] == "memory_areas.v1"
    assert payload["status"] == "active"
    assert payload["counts"] == {"strong": 7, "partial": 1}
    assert payload["gap_count"] == 1
    assert "repo truth" in payload["headline"].lower()
    areas = {row["key"]: row for row in payload["areas"]}
    assert areas["repo_truth"]["state"] == "strong"
    assert areas["retrieval"]["state"] == "strong"
    assert areas["guidance"]["state"] == "strong"
    assert areas["session_packets"]["state"] == "strong"
    assert areas["outcomes"]["state"] == "strong"
    assert areas["outcomes"]["summary"] == "Benchmark deltas and finished workstreams are retained."
    assert areas["decisions"]["state"] == "strong"
    assert areas["collaboration"]["state"] == "strong"
    assert areas["contradictions"]["state"] == "partial"


def test_build_memory_areas_snapshot_reports_disabled_posture() -> None:
    payload = store._build_memory_areas_snapshot(  # noqa: SLF001
        enabled=False,
        authoritative_truth={},
        compiler_state={},
        guidance_catalog={},
        runtime_state={},
        entity_counts={},
        backend_transition={},
        optimization={},
        evaluation={},
    )

    assert payload["status"] == "disabled"
    assert payload["headline"] == "Odylith is disabled, so memory-area posture is suppressed for this run."
    assert payload["counts"] == {"disabled": 8}
    assert payload["gap_count"] == 8
    assert all(row["state"] == "disabled" for row in payload["areas"])


def test_print_runtime_status_includes_judgment_memory_summary(capsys) -> None:  # noqa: ANN001
    context_engine._print_runtime_status(  # noqa: SLF001
        {
            "repo_root": "/tmp/repo",
            "daemon_pid": 0,
            "daemon_alive": False,
            "watcher_backend": "polling",
            "preferred_watcher_backend": "polling",
            "updated_utc": "2026-03-28T08:00:00Z",
            "projection_fingerprint": "abc123",
            "projection_scope": "full",
            "updated_projections": ["components"],
            "active_sessions": 1,
            "bootstrap_packets": 2,
            "projection_snapshot_path": "/tmp/repo/.odylith/runtime/projection.json",
            "state_path": "/tmp/repo/.odylith/runtime/state.json",
            "socket_path": "/tmp/repo/.odylith/runtime/socket",
            "odylith_switch": {"enabled": True},
            "memory_snapshot": {
                "engine": {
                    "backend": {
                        "storage": "lance_local_columnar",
                        "sparse_recall": "tantivy_sparse_recall",
                    },
                    "target_backend": {
                        "storage": "lance_local_columnar",
                        "sparse_recall": "tantivy_sparse_recall",
                    },
                    "backend_transition": {"status": "standardized"},
                },
                "backend_transition": {"evidence_source": "live_backend"},
                "runtime_state": {"bootstrap_packets": 2},
                "guidance_catalog": {"chunk_count": 12},
                "entity_counts": {"indexed_entity_count": 88},
                "memory_areas": {
                    "counts": {"strong": 6, "partial": 1},
                    "headline": "Repo truth, retrieval memory, and decision memory are strong.",
                },
                "judgment_memory": {
                    "counts": {"strong": 5, "partial": 2, "cold": 1},
                    "headline": "Decision memory and onboarding memory are durable.",
                },
                "remote_retrieval": {"enabled": False},
                "repo_scan_degraded_fallback": {},
                "governance_runtime_first": {},
            },
        }
    )

    output = capsys.readouterr().out
    assert "- memory_areas: strong=6, partial=1" in output
    assert "- memory_headline: Repo truth, retrieval memory, and decision memory are strong." in output
    assert "- judgment_memory: strong=5, partial=2, cold=1" in output
    assert "- judgment_headline: Decision memory and onboarding memory are durable." in output


def test_run_odylith_remote_sync_skips_local_warm_when_remote_is_not_active(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        context_engine.odylith_remote_retrieval,
        "remote_config",
        lambda **_: {"enabled": False, "status": "disabled", "mode": "disabled"},
    )
    monkeypatch.setattr(
        context_engine.store,
        "warm_projections",
        lambda **_: (_ for _ in ()).throw(AssertionError("disabled remote sync should not warm projections")),
    )
    monkeypatch.setattr(
        context_engine.odylith_memory_backend,
        "local_backend_ready",
        lambda **_: (_ for _ in ()).throw(AssertionError("disabled remote sync should not check local backend readiness")),
    )
    monkeypatch.setattr(
        context_engine.odylith_memory_backend,
        "all_documents",
        lambda **_: (_ for _ in ()).throw(AssertionError("disabled remote sync should not load local documents")),
    )
    monkeypatch.setattr(
        context_engine.odylith_remote_retrieval,
        "sync_remote",
        lambda **kwargs: {
            "status": "disabled",
            "dry_run": kwargs["dry_run"],
            "attempted_documents": len(kwargs["documents"]),
        },
    )

    rc = context_engine._run_odylith_remote_sync(repo_root=tmp_path, dry_run=True)  # noqa: SLF001
    output = capsys.readouterr().out

    assert rc == 0
    assert '"status": "disabled"' in output


def test_run_odylith_remote_sync_warms_full_projection_when_backend_is_stale(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    warm_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        context_engine.odylith_remote_retrieval,
        "remote_config",
        lambda **_: {"enabled": True, "configured": True, "status": "ready", "mode": "augment"},
    )
    monkeypatch.setattr(
        context_engine.store,
        "projection_input_fingerprint",
        lambda **_: "fp-full",
    )
    monkeypatch.setattr(
        context_engine.odylith_memory_backend,
        "local_backend_ready_for_projection",
        lambda **_: False,
    )
    monkeypatch.setattr(
        context_engine.store,
        "warm_projections",
        lambda **kwargs: warm_calls.append(kwargs) or {"ready": True},
    )
    monkeypatch.setattr(
        context_engine.odylith_memory_backend,
        "all_documents",
        lambda **_: [{"doc_key": "doc-1", "embedding": [0.1]}],
    )
    monkeypatch.setattr(
        context_engine.odylith_remote_retrieval,
        "sync_remote",
        lambda **kwargs: {
            "status": "ok",
            "dry_run": kwargs["dry_run"],
            "attempted_documents": len(kwargs["documents"]),
        },
    )

    rc = context_engine._run_odylith_remote_sync(repo_root=tmp_path, dry_run=True)  # noqa: SLF001
    output = capsys.readouterr().out

    assert rc == 0
    assert warm_calls == [
        {
            "repo_root": tmp_path,
            "force": False,
            "reason": "odylith_remote_sync",
            "scope": "full",
        }
    ]
    assert '"status": "ok"' in output


def test_memory_backend_sticky_snapshot_accepts_full_scope_as_reasoning_superset() -> None:
    compatible = store._memory_backend_sticky_snapshot_compatible(  # noqa: SLF001
        live_signature={
            "projection_scope": "reasoning",
            "document_count": 100,
            "edge_count": 20,
        },
        sticky_signature={
            "projection_scope": "full",
            "document_count": 120,
            "edge_count": 24,
        },
        observed_backend={
            "provider": "projection_scan",
            "storage": "compiler_projection_snapshot",
            "sparse_recall": "repo_scan_fallback",
        },
        sticky_backend={
            "provider": "odylith_memory_backend",
            "storage": "lance_local_columnar",
            "sparse_recall": "tantivy_sparse_recall",
        },
    )

    assert compatible is True


def test_load_judgment_workstream_hint_matches_overlapping_slice(tmp_path: Path) -> None:
    judgment_path = store.judgment_memory_path(repo_root=tmp_path)
    judgment_path.parent.mkdir(parents=True, exist_ok=True)
    judgment_path.write_text(
        json.dumps(
            {
                "contract": "judgment_memory.v1",
                "starter_slice": {
                    "path": "src/odylith/runtime/context_engine",
                    "workstream_id": "B-010",
                    "status": "established",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    hint = store._load_judgment_workstream_hint(  # noqa: SLF001
        repo_root=tmp_path,
        changed_paths=["src/odylith/runtime/context_engine/odylith_context_engine_store.py"],
    )

    assert hint["workstream_id"] == "B-010"
    assert hint["slice_path"] == "src/odylith/runtime/context_engine"
    assert hint["confidence"] == "high"
    assert hint["matched_paths"] == ["src/odylith/runtime/context_engine/odylith_context_engine_store.py"]


def test_workstream_selection_uses_judgment_hint_to_break_low_signal_ambiguity() -> None:
    selection = store._workstream_selection(  # noqa: SLF001
        connection=None,
        candidates=[
            {
                "entity_id": "B-010",
                "title": "Durable memory",
                "evidence": {
                    "score": 60,
                    "strong_signal_count": 1,
                    "broad_only": False,
                    "matched_paths": ["src/odylith/runtime/context_engine/odylith_context_engine_store.py"],
                    "counters": {"direct_exact": 1},
                },
            },
            {
                "entity_id": "B-008",
                "title": "Memory areas",
                "evidence": {
                    "score": 18,
                    "strong_signal_count": 0,
                    "broad_only": False,
                    "matched_paths": ["src/odylith/runtime/context_engine/odylith_context_engine_store.py"],
                    "counters": {"trace_doc_exact": 1},
                },
            },
        ],
        judgment_hint={
            "workstream_id": "B-010",
            "confidence": "medium",
            "reason": "Durable slice memory already ties `src/odylith/runtime/context_engine` to `B-010`.",
        },
    )

    assert selection["state"] == "inferred_confident"
    assert selection["ambiguity_class"] == "judgment_memory_confirmed"
    assert selection["selected_workstream"]["entity_id"] == "B-010"
    assert "Durable slice memory already ties" in selection["reason"]


def test_load_bug_projection_handles_multiline_open_bug_rows(tmp_path: Path) -> None:
    bugs_root = tmp_path / "odylith" / "casebook" / "bugs"
    bugs_root.mkdir(parents=True, exist_ok=True)
    (bugs_root / "2026-03-29-open-bug.md").write_text("# Bug\n", encoding="utf-8")
    (bugs_root / "INDEX.md").write_text(
        "# Bug Index\n\n"
        "## Open Bugs\n\n"
        "| Bug ID | Date | Title | Severity | Components | Status | Link |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| CB-201 | 2026-03-29 | Runtime payload remains inconsistent | P1 | `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,\n"
        "  memory-area headline contract. | Open | [2026-03-29-open-bug.md](2026-03-29-open-bug.md) |\n\n"
        "## Closed Bugs\n\n"
        "| Bug ID | Date | Title | Severity | Components | Status | Link |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n",
        encoding="utf-8",
    )

    rows = store._load_bug_projection(repo_root=tmp_path)  # noqa: SLF001

    assert rows == [
        {
            "Bug ID": "CB-201",
            "Date": "2026-03-29",
            "Title": "Runtime payload remains inconsistent",
            "Severity": "P1",
            "Components": "`src/odylith/runtime/context_engine/odylith_context_engine_store.py`, memory-area headline contract.",
            "Status": "Open",
            "Link": "[bug](odylith/casebook/bugs/2026-03-29-open-bug.md)",
            "IndexPath": "odylith/casebook/bugs/INDEX.md",
        }
    ]


def test_build_judgment_memory_snapshot_retains_negative_contradiction_and_onboarding_memory(tmp_path: Path) -> None:
    benchmark_path = tmp_path / ".odylith" / "runtime" / "odylith-benchmarks"
    benchmark_path.mkdir(parents=True, exist_ok=True)
    (benchmark_path / "latest.v1.json").write_text("{}", encoding="utf-8")

    snapshot = store._build_judgment_memory_snapshot(  # noqa: SLF001
        repo_root=tmp_path,
        projection_updated_utc="2026-03-29T06:22:04Z",
        backlog_projection={
            "updated_utc": "2026-03-29",
            "active": [],
            "execution": [],
            "finished": [
                {
                    "idea_id": "B-010",
                    "title": "Durable judgment memory",
                    "link": "[done](odylith/radar/source/ideas/2026-03/2026-03-28-odylith-durable-judgment-memory-and-memory-backend-productization.md)",
                }
            ],
            "parked": [],
        },
        plan_projection={"active": [], "done": [], "parked": []},
        bug_projection=[
            {
                "Date": "2026-03-29",
                "Title": "Critical runtime regression",
                "Severity": "P0",
                "Status": "Open",
                "Link": "[bug](odylith/casebook/bugs/2026-03-29-critical-runtime-regression.md)",
            }
        ],
        diagram_projection=[],
        runtime_state={},
        optimization={},
        evaluation={},
        benchmark_report={
            "generated_utc": "2026-03-29T06:22:04Z",
            "acceptance": {"status": "provisional_pass"},
            "comparison": {
                "required_path_recall_delta": 0.964,
                "validation_success_delta": 0.714,
                "median_latency_delta_ms": -14.415,
                "median_prompt_token_delta": -338.0,
                "median_total_payload_token_delta": -261.5,
            },
        },
        recent_bootstrap_packets=[],
        active_sessions=[],
        repo_dirty_paths=[],
        welcome_state={
            "show": False,
            "chosen_slice": {
                "path": "src/odylith/runtime/context_engine",
                "seam": "`src/odylith/runtime/context_engine` <-> `src/odylith/runtime/memory`",
                "component_label": "Context Engine",
            },
        },
        previous_snapshot={},
        retrieval_state="strong",
    )

    areas = {row["key"]: row for row in snapshot["areas"]}

    assert snapshot["status"] == "active"
    assert areas["negative"]["state"] == "strong"
    assert areas["negative"]["item_count"] == 1
    assert areas["contradictions"]["state"] == "strong"
    assert any(item["kind"] == "bugs_without_active_plan" for item in areas["contradictions"]["items"])
    assert any(item["kind"] == "proof_vs_open_risk" for item in areas["contradictions"]["items"])
    assert areas["onboarding"]["state"] == "partial"
    assert snapshot["headline"]
    assert snapshot["starter_slice"]["path"] == "src/odylith/runtime/context_engine"
    assert snapshot["starter_slice"]["status"] == "inferred"
