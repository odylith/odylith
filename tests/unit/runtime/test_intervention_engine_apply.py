from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.intervention_engine import apply
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
        json.dumps({"version": "v1", "workstreams": [], "warning_items": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "casebook" / "bugs").mkdir(parents=True, exist_ok=True)


def test_preview_only_bundle_cannot_apply_and_emits_no_apply_event(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_edit_checkpoint",
            session_id="apply-1",
            prompt_excerpt="Map the topology and governance boundary for this runtime slice.",
            changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
        ),
    )

    assert bundle["proposal"]["apply_supported"] is False
    with pytest.raises(ValueError, match="preview-only"):
        apply.apply_proposal_bundle(repo_root=tmp_path, payload=bundle)

    assert stream_state.load_recent_intervention_events(repo_root=tmp_path, session_id="apply-1") == []


def test_apply_rejects_stale_bundle_after_terminal_event(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="apply-2",
            prompt_excerpt="Capture governance bug memory for this regression lane.",
            changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
        ),
    )

    assert bundle["proposal"]["apply_supported"] is True
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_declined",
        summary="Odylith Proposal declined.",
        session_id="apply-2",
        intervention_key=bundle["proposal"]["key"],
        turn_phase="post_edit_checkpoint",
        proposal_status="declined",
    )

    with pytest.raises(ValueError, match="stale"):
        apply.apply_proposal_bundle(repo_root=tmp_path, payload=bundle)


def test_apply_supported_bundle_is_all_or_nothing_and_emits_capture_applied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id="apply-3",
            prompt_excerpt="Capture governance bug memory for this regression lane.",
            changed_paths=["src/odylith/runtime/intervention_engine/apply.py"],
        ),
    )

    monkeypatch.setattr(apply, "_apply_radar_create", lambda **_kwargs: {"idea_id": "B-900"})
    monkeypatch.setattr(apply, "_apply_registry_create", lambda **_kwargs: {"component_id": "regression-lane"})
    monkeypatch.setattr(apply, "_apply_casebook_create", lambda **_kwargs: {"bug_id": "CB-900"})

    result = apply.apply_proposal_bundle(repo_root=tmp_path, payload=bundle)
    events = stream_state.load_recent_intervention_events(repo_root=tmp_path, session_id="apply-3")

    assert result["status"] == "applied"
    assert [row["surface"] for row in result["applied"]] == ["radar", "registry", "casebook"]
    assert result["skipped"] == []
    assert events[-1]["kind"] == "capture_applied"
    assert events[-1]["summary"] == "Odylith Proposal applied."
    assert "Odylith Proposal:" in events[-1]["display_markdown"]
    assert events[-1]["prompt_excerpt"] == "Capture governance bug memory for this regression lane."
    assert events[-1]["host_family"] == "codex"
    assert events[-1]["moment_kind"] == bundle["candidate"]["moment"]["kind"]
    assert events[-1]["semantic_signature"] == bundle["proposal"]["semantic_signature"]


def test_decline_preserves_prompt_context_in_terminal_event(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="apply-4",
            prompt_excerpt="Capture governance bug memory before this thread goes cold.",
            changed_paths=["src/odylith/runtime/intervention_engine/apply.py"],
        ),
    )

    result = apply.apply_proposal_bundle(repo_root=tmp_path, payload=bundle, decline=True)
    events = stream_state.load_recent_intervention_events(repo_root=tmp_path, session_id="apply-4")

    assert result["status"] == "declined"
    assert events[-1]["kind"] == "capture_declined"
    assert events[-1]["prompt_excerpt"] == "Capture governance bug memory before this thread goes cold."
    assert events[-1]["host_family"] == "claude"
    assert events[-1]["moment_kind"] == bundle["candidate"]["moment"]["kind"]
    assert events[-1]["semantic_signature"] == bundle["proposal"]["semantic_signature"]


def test_apply_can_recover_latest_event_by_key_when_payload_session_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id="apply-5",
            prompt_excerpt="Capture governance bug memory for this regression lane.",
            changed_paths=["src/odylith/runtime/intervention_engine/apply.py"],
        ),
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary=bundle["proposal"]["summary"],
        session_id="apply-5",
        host_family="codex",
        intervention_key=bundle["proposal"]["key"],
        turn_phase="post_bash_checkpoint",
        display_markdown=bundle["proposal"]["markdown_text"],
        display_plain=bundle["proposal"]["plain_text"],
        prompt_excerpt=bundle["observation"]["prompt_excerpt"],
        moment_kind=bundle["candidate"]["moment"]["kind"],
        semantic_signature=bundle["proposal"]["semantic_signature"],
    )
    payload = dict(bundle)
    payload["observation"] = {**payload["observation"], "session_id": ""}

    monkeypatch.setattr(apply, "_apply_radar_create", lambda **_kwargs: {"idea_id": "B-901"})
    monkeypatch.setattr(apply, "_apply_registry_create", lambda **_kwargs: {"component_id": "regression-lane"})
    monkeypatch.setattr(apply, "_apply_casebook_create", lambda **_kwargs: {"bug_id": "CB-901"})

    result = apply.apply_proposal_bundle(repo_root=tmp_path, payload=payload)

    assert result["status"] == "applied"
