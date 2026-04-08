from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import delivery_intelligence_engine as engine


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
