from __future__ import annotations

import json
import time
from pathlib import Path

from odylith.runtime.intervention_engine import continuity_runtime
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import engine
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import surface_runtime


def _seed_repo(root: Path) -> None:
    (root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        json.dumps({"version": "v1", "components": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "v1", "diagrams": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "radar" / "traceability-graph.v1.json").write_text(
        json.dumps({"version": "v1", "workstreams": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "casebook" / "bugs").mkdir(parents=True, exist_ok=True)


def test_repo_truth_cache_reuses_expensive_indexes(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    _seed_repo(tmp_path)
    engine._REPO_TRUTH_CACHE.clear()  # noqa: SLF001
    counts = {"component_index": 0, "workstream_index": 0}
    build_component_index = engine.component_registry.build_component_index
    collect_workstream_index = engine.workstream_inference.collect_workstream_path_index_from_traceability

    def _count_component_index(*args, **kwargs):  # noqa: ANN002, ANN003
        counts["component_index"] += 1
        return build_component_index(*args, **kwargs)

    def _count_workstream_index(*args, **kwargs):  # noqa: ANN002, ANN003
        counts["workstream_index"] += 1
        return collect_workstream_index(*args, **kwargs)

    monkeypatch.setattr(engine.component_registry, "build_component_index", _count_component_index)
    monkeypatch.setattr(
        engine.workstream_inference,
        "collect_workstream_path_index_from_traceability",
        _count_workstream_index,
    )

    first = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="post_edit_checkpoint",
        session_id="perf-1",
        prompt_excerpt="Capture governance bug memory for this regression lane.",
        changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
    )
    second = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="post_edit_checkpoint",
        session_id="perf-2",
        prompt_excerpt="Map the topology and ownership boundary for this runtime slice.",
        changed_paths=["src/odylith/runtime/intervention_engine/voice.py"],
    )

    engine.build_intervention_bundle(repo_root=tmp_path, observation=first)
    engine.build_intervention_bundle(repo_root=tmp_path, observation=second)

    assert counts == {"component_index": 1, "workstream_index": 1}


def test_warm_intervention_preview_stays_within_local_latency_budget(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    engine._REPO_TRUTH_CACHE.clear()  # noqa: SLF001
    base = surface_runtime.observation_envelope(
        host_family="claude",
        turn_phase="post_edit_checkpoint",
        session_id="perf-latency",
        prompt_excerpt="Capture governance bug memory for this regression lane.",
        changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
    )

    engine.build_intervention_bundle(repo_root=tmp_path, observation=base)
    started = time.perf_counter()
    for index in range(60):
        engine.build_intervention_bundle(
            repo_root=tmp_path,
            observation={
                **base,
                "session_id": f"perf-latency-{index}",
                "prompt_excerpt": f"Capture governance bug memory for this regression lane {index}.",
            },
        )
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0


def test_pending_proposal_state_stays_within_local_latency_budget(tmp_path: Path) -> None:
    for index in range(120):
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="capture_proposed",
            summary="Odylith Proposal pending.",
            session_id=f"perf-pending-{index}",
            host_family="codex",
            intervention_key=f"iv-pending-{index}",
            turn_phase="post_edit_checkpoint",
            confirmation_text="apply this proposal",
            proposal_status="pending",
            prompt_excerpt=f"Preserve prompt memory for proposal {index}.",
            display_markdown='-----\nOdylith Proposal: Odylith is proposing one clean governed bundle for this moment. It is staying in preview until every action has a safe apply lane.\n\nTo apply, say "apply this proposal".\n-----',
        )

    started = time.perf_counter()
    for _ in range(80):
        pending = stream_state.pending_proposal_state(repo_root=tmp_path)
        assert pending["pending_count"] == 120
    elapsed = time.perf_counter() - started

    assert elapsed < 1.0


def test_session_memory_snapshot_stays_within_local_latency_budget(tmp_path: Path) -> None:
    for index in range(160):
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="intervention_teaser" if index % 2 == 0 else "intervention_card",
            summary=f"Signal {index}",
            session_id="perf-session-memory",
            host_family="codex",
            intervention_key=f"iv-session-{index}",
            turn_phase="post_edit_checkpoint",
            moment_kind="capture" if index % 2 == 0 else "boundary",
            semantic_signature=[f"token-{index}", "shared"],
        )

    started = time.perf_counter()
    for _ in range(120):
        snapshot = stream_state.session_memory_snapshot(
            repo_root=tmp_path,
            session_id="perf-session-memory",
        )
        assert snapshot["recent_event_count"] == 80
    elapsed = time.perf_counter() - started

    assert elapsed < 0.7


def test_moment_continuity_snapshot_stays_within_local_latency_budget(tmp_path: Path) -> None:
    for index in range(180):
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="intervention_teaser" if index % 3 == 0 else "intervention_card",
            summary=f"Signal {index}",
            session_id="perf-continuity",
            host_family="codex",
            intervention_key="iv-continuity-main" if index % 2 == 0 else f"iv-continuity-{index}",
            turn_phase="stop_summary" if index % 3 else "prompt_submit",
            moment_kind="continuation" if index % 2 == 0 else "boundary",
            semantic_signature=["governed", "proposal", "b321"] if index % 2 == 0 else [f"token-{index}"],
        )

    started = time.perf_counter()
    for _ in range(160):
        snapshot = continuity_runtime.moment_continuity_snapshot(
            repo_root=tmp_path,
            session_id="perf-continuity",
            moment_key="iv-continuity-main",
            semantic_signature=["governed", "proposal", "b321"],
        )
        assert snapshot["seen_card"] is True
        assert snapshot["stage_floor"] == "card"
    elapsed = time.perf_counter() - started

    assert elapsed < 0.8


def test_continuity_snapshot_prefers_exact_key_over_signature_fallback(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Main moment teaser.",
        session_id="perf-continuity-key",
        intervention_key="iv-main",
        moment_kind="continuation",
        semantic_signature=["shared", "signature"],
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Different moment same signature.",
        session_id="perf-continuity-key",
        intervention_key="iv-other",
        moment_kind="boundary",
        semantic_signature=["shared", "signature"],
    )

    snapshot = continuity_runtime.moment_continuity_snapshot(
        repo_root=tmp_path,
        session_id="perf-continuity-key",
        moment_key="iv-main",
        semantic_signature=["shared", "signature"],
    )

    assert snapshot["matching_event_count"] == 1
    assert snapshot["latest_kind"] == "intervention_teaser"


def test_warm_conversation_surface_bundle_stays_within_local_latency_budget(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    engine._REPO_TRUTH_CACHE.clear()  # noqa: SLF001
    base = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="perf-surface",
        prompt_excerpt="Capture governance bug memory for this regression lane.",
        changed_paths=["src/odylith/runtime/intervention_engine/conversation_surface.py"],
    )

    conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=base,
    )
    started = time.perf_counter()
    for index in range(80):
        bundle = conversation_surface.build_conversation_bundle(
            repo_root=tmp_path,
            observation={
                **base,
                "session_id": f"perf-surface-{index}",
                "prompt_excerpt": f"Capture governance bug memory for this regression lane {index}.",
            },
        )
        assert conversation_surface.render_live_text(
            bundle,
            markdown=True,
            include_proposal=True,
        )
    elapsed = time.perf_counter() - started

    assert elapsed < 2.2


def test_cold_no_signal_preview_stays_within_tight_latency_budget(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    engine._REPO_TRUTH_CACHE.clear()  # noqa: SLF001
    started = time.perf_counter()
    for index in range(120):
        bundle = engine.build_intervention_bundle(
            repo_root=tmp_path,
            observation=surface_runtime.observation_envelope(
                host_family="claude",
                turn_phase="prompt_submit",
                session_id=f"perf-cold-{index}",
                prompt_excerpt="Refactor helper names in main.py.",
            ),
        )
        assert bundle["candidate"]["stage"] == "silent"
        assert bundle["proposal"]["eligible"] is False
    elapsed = time.perf_counter() - started

    assert elapsed < 0.8
