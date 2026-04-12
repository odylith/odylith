from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import delivery_intelligence_engine as engine
from odylith.runtime.governance import delivery_intelligence_refresh as refresh


def test_change_vector_treats_registry_component_dossiers_as_specs() -> None:
    vector = engine._change_vector_from_paths(  # noqa: SLF001
        [
            "odylith/registry/source/components/compass/CURRENT_SPEC.md",
            "odylith/registry/source/components/compass/FORENSICS.v1.json",
        ]
    )

    assert vector["spec"] == 2
    assert vector["doc"] == 0


def test_delivery_reasoning_config_disables_provider_for_delivery_refresh(
    monkeypatch,
    tmp_path: Path,
) -> None:
    base = engine.odylith_reasoning.ReasoningConfig(
        mode="auto",
        provider="codex-cli",
        model="gpt-5.4",
        base_url="",
        api_key="",
        scope_cap=7,
        timeout_seconds=11.0,
        codex_bin="codex",
        codex_reasoning_effort="high",
        claude_bin="claude",
        claude_reasoning_effort="high",
        api_key_env="",
        config_source="env-overrides",
        config_path="/tmp/reasoning.config.v1.json",
    )
    monkeypatch.setattr(engine.odylith_reasoning, "reasoning_config_from_env", lambda **_: base)

    config = engine._delivery_reasoning_config(repo_root=tmp_path)  # noqa: SLF001

    assert config.mode == "disabled"
    assert config.provider == "codex-cli"
    assert config.scope_cap == 7
    assert config.timeout_seconds == 11.0
    assert config.config_source == "delivery-deterministic-fallback"


def test_delivery_intelligence_main_preserves_mtime_for_semantic_noop(monkeypatch, tmp_path: Path) -> None:
    output_path = tmp_path / "odylith" / "runtime" / "delivery_intelligence.v4.json"

    monkeypatch.setattr(
        engine,
        "build_delivery_intelligence_artifact",
        lambda **_: {"version": "v4", "summary": {"state": "steady"}},
    )
    monkeypatch.setattr(engine, "validate_delivery_intelligence_artifact", lambda _payload: [])

    rc = engine.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    first_mtime_ns = output_path.stat().st_mtime_ns

    rc = engine.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    second_mtime_ns = output_path.stat().st_mtime_ns

    assert first_mtime_ns == second_mtime_ns


def test_delivery_intelligence_main_reports_current_for_semantic_noop(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        engine,
        "build_delivery_intelligence_artifact",
        lambda **_: {"version": "v4", "summary": {"state": "steady"}},
    )
    monkeypatch.setattr(engine, "validate_delivery_intelligence_artifact", lambda _payload: [])

    rc = engine.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    rc = engine.main(["--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert "delivery intelligence artifact is current" in output


def test_delivery_intelligence_main_skips_rebuild_when_inputs_are_unchanged(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        engine,
        "build_delivery_intelligence_artifact",
        lambda **_: {"version": "v4", "summary": {"state": "steady"}},
    )
    monkeypatch.setattr(engine, "validate_delivery_intelligence_artifact", lambda _payload: [])

    first_rc = engine.main(["--repo-root", str(tmp_path)])
    assert first_rc == 0

    monkeypatch.setattr(
        engine,
        "build_delivery_intelligence_artifact",
        lambda **_: (_ for _ in ()).throw(AssertionError("rebuild should have been skipped")),
    )

    second_rc = engine.main(["--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert second_rc == 0
    assert "delivery intelligence artifact is current" in output


def test_delivery_intelligence_main_guard_tracks_local_head(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _capture_guard(**kwargs):  # noqa: ANN202
        captured.update(kwargs)
        return True, "fingerprint", {}

    monkeypatch.setattr(engine.generated_refresh_guard, "should_skip_rebuild", _capture_guard)
    monkeypatch.setattr(engine, "_current_local_head", lambda _repo_root: "abc123")

    rc = engine.main(["--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["extra"] == {"max_review_age_days": 21, "local_head": "abc123"}


def test_delivery_intelligence_refresh_guard_tracks_local_head(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _capture_guard(**kwargs):  # noqa: ANN202
        captured.update(kwargs)
        return True, "fingerprint", {}

    monkeypatch.setattr(refresh.generated_refresh_guard, "should_skip_rebuild", _capture_guard)
    monkeypatch.setattr(refresh, "_current_local_head", lambda _repo_root: "abc123")

    rc = refresh.main(["--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["extra"] == {"max_review_age_days": 21, "local_head": "abc123"}


def test_slice_delivery_intelligence_for_surface_retains_proof_state_contract() -> None:
    payload = {
        "version": "v4",
        "indexes": {
            "workstreams": {"B-062": "workstream:B-062"},
        },
        "scopes": [
            {
                "scope_key": "workstream:B-062",
                "scope_id": "B-062",
                "scope_type": "workstream",
                "operator_readout": {
                    "primary_scenario": "false_priority",
                    "secondary_scenarios": [],
                    "severity": "blocker",
                    "issue": "A higher-risk blocker is still open.",
                    "why_hidden": "Preview proof did not move the live frontier.",
                    "action": "Stay pinned to the blocker seam.",
                    "action_kind": "rebind_scope",
                    "proof_refs": [],
                    "requires_approval": False,
                    "source": "deterministic",
                },
                "proof_state": {
                    "lane_id": "proof-state-control-plane",
                    "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                    "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                    "frontier_phase": "manifests-deploy",
                    "proof_status": "fixed_in_code",
                },
                "proof_state_resolution": {
                    "state": "resolved",
                    "lane_ids": ["proof-state-control-plane"],
                },
                "claim_guard": {
                    "highest_truthful_claim": "fixed in code",
                    "blocked_terms": ["fixed", "cleared", "resolved"],
                },
                "scope_signal": {
                    "rank": 5,
                    "rung": "R5",
                    "token": "blocking_frontier",
                    "label": "Blocking frontier",
                    "reasons": ["A live proof blocker is still open."],
                    "caps": [],
                    "promoted_default": True,
                    "budget_class": "escalated_reasoning",
                },
            }
        ],
        "case_queue": [],
    }

    sliced = engine.slice_delivery_intelligence_for_surface(payload=payload, surface="compass")

    assert sliced["workstreams"]["B-062"]["proof_state"]["lane_id"] == "proof-state-control-plane"
    assert sliced["workstreams"]["B-062"]["proof_state_resolution"] == {
        "state": "resolved",
        "lane_ids": ["proof-state-control-plane"],
    }
    assert sliced["workstreams"]["B-062"]["claim_guard"]["highest_truthful_claim"] == "fixed in code"
    assert sliced["workstreams"]["B-062"]["scope_signal"]["rung"] == "R5"
    assert sliced["workstreams"]["B-062"]["scope_signal"]["budget_class"] == "escalated_reasoning"
