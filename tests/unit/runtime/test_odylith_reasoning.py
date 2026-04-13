from __future__ import annotations

import json
from pathlib import Path
import subprocess
import urllib.error

import pytest

from odylith.runtime.governance import operator_readout
from odylith.runtime.reasoning import odylith_reasoning


class _StubProvider:
    def generate_finding(self, *, prompt_payload: dict[str, object]) -> dict[str, object] | None:
        evidence_items = prompt_payload.get("evidence_items", []) if isinstance(prompt_payload.get("evidence_items"), list) else []
        evidence_ids = [
            str(row.get("id", "")).strip()
            for row in evidence_items
            if isinstance(row, dict) and str(row.get("id", "")).strip()
        ]
        assert len(evidence_ids) >= 4
        return {
            "leading_explanation": {"text": "Validated provider read: the evaluator is still changing the judgment path.", "evidence_ids": evidence_ids[:2]},
            "strongest_rival": {"text": "The rival is that the latest diff is presentation-only.", "evidence_ids": [evidence_ids[2]]},
            "risk_if_wrong": {"text": "If that read is wrong, maintainers will trust unstable queue guidance.", "evidence_ids": [evidence_ids[1]]},
            "discriminating_next_check": {"text": "Classify the latest diff as presentation-only or reasoning-semantic before trusting the queue.", "evidence_ids": [evidence_ids[3]]},
            "maintainer_brief": {"text": "Validated provider read: the evaluator is still changing the judgment path. The rival is that the latest diff is presentation-only. Do now: classify the latest diff before trusting the queue.", "evidence_ids": evidence_ids[:3]},
        }


class _InvalidProvider:
    def generate_finding(self, *, prompt_payload: dict[str, object]) -> dict[str, object] | None:
        _ = prompt_payload
        return {
            "leading_explanation": {"text": "Uncited provider output", "evidence_ids": ["EX"]},
            "strongest_rival": {"text": "Uncited rival", "evidence_ids": ["EX"]},
            "risk_if_wrong": {"text": "Uncited risk", "evidence_ids": ["EX"]},
            "discriminating_next_check": {"text": "Uncited next check", "evidence_ids": ["EX"]},
            "maintainer_brief": {"text": "Uncited brief", "evidence_ids": ["EX"]},
        }


class _PathLeakingProvider:
    def generate_finding(self, *, prompt_payload: dict[str, object]) -> dict[str, object] | None:
        evidence_items = prompt_payload.get("evidence_items", []) if isinstance(prompt_payload.get("evidence_items"), list) else []
        evidence_ids = [
            str(row.get("id", "")).strip()
            for row in evidence_items
            if isinstance(row, dict) and str(row.get("id", "")).strip()
        ]
        return {
            "leading_explanation": {
                "text": "Validated provider read: src/odylith/runtime/reasoning/odylith_reasoning.py is still changing the evaluator path.",
                "evidence_ids": evidence_ids[:2],
            },
            "strongest_rival": {
                "text": "The rival is that src/odylith/runtime/reasoning/odylith_reasoning.py only changed presentation.",
                "evidence_ids": [evidence_ids[2]],
            },
            "risk_if_wrong": {
                "text": "If that read is wrong, maintainers will trust unstable queue guidance.",
                "evidence_ids": [evidence_ids[1]],
            },
            "discriminating_next_check": {
                "text": "Classify the latest diff in src/odylith/runtime/reasoning/odylith_reasoning.py before trusting the queue.",
                "evidence_ids": [evidence_ids[3]],
            },
            "maintainer_brief": {
                "text": "Validated provider read: src/odylith/runtime/reasoning/odylith_reasoning.py is still changing the evaluator path. The rival is that src/odylith/runtime/reasoning/odylith_reasoning.py only changed presentation. Do now: classify the latest diff in src/odylith/runtime/reasoning/odylith_reasoning.py before trusting the queue.",
                "evidence_ids": evidence_ids[:4],
            },
        }


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def _proof_ref(
    *,
    kind: str = "workstream",
    value: str = "B-100",
    label: str = "B-100 workstream",
    surface: str = "compass",
    anchor: str = "timeline-audit",
) -> dict[str, str]:
    return {
        "kind": kind,
        "value": value,
        "label": label,
        "surface": surface,
        "anchor": anchor,
    }


def _scope(
    *,
    scope_id: str,
    scope_label: str,
    status: str = "finished",
    code_references: list[str] | None = None,
    linked_components: list[str] | None = None,
    linked_surfaces: list[str] | None = None,
) -> dict[str, object]:
    return {
        "scope_key": f"workstream:{scope_id}",
        "scope_type": "workstream",
        "scope_id": scope_id,
        "scope_label": scope_label,
        "posture_mode": "closure_hardening",
        "trajectory": "stalled",
        "confidence": "High",
        "scores": {
            "decision_debt": 78,
            "governance_lag": 66,
            "blast_radius_severity": 59,
        },
        "operator_readout": {
            "primary_scenario": "unsafe_closeout",
            "secondary_scenarios": [],
            "severity": "blocker" if status == "finished" else "watch",
            "issue": f"{scope_label} execution moved ahead of the last explicit checkpoint.",
            "why_hidden": "The gap only appears when recent activity is compared against the last explicit checkpoint.",
            "action": f"Inspect the newest semantic diff for {scope_id}.",
            "action_kind": "refresh_authority",
            "proof_refs": [_proof_ref(value=scope_id, label=f"{scope_id} workstream")],
            "requires_approval": True,
            "source": "deterministic",
        },
        "evidence_context": {
            "basis": "explicit",
            "freshness": "current",
            "latest_event_ts_iso": "2026-03-07T10:17:57-08:00",
            "latest_explicit_ts_iso": "2026-03-01T21:38:40-08:00",
            "linked_workstreams": [scope_id],
            "linked_components": linked_components if linked_components is not None else ["odylith"],
            "linked_diagrams": ["D-010"],
            "linked_surfaces": linked_surfaces if linked_surfaces is not None else ["atlas", "radar", "dashboard"],
            "code_references": code_references if code_references is not None else ["src/odylith/runtime/surfaces/render_tooling_dashboard.py"],
            "changed_artifacts": ["odylith/index.html"],
            "blast_radius_class": "cross-surface",
        },
        "explanation_facts": [
            f"{scope_label} has newer activity than the last explicit checkpoint.",
            "Clearance is still pending in Odylith.",
        ],
        "diagnostics": {
            "status": status,
            "idea_file": f"odylith/radar/source/ideas/2026-03/{scope_id.lower()}.md",
            "plan_path": f"odylith/technical-plans/in-progress/2026-03-07-{scope_id.lower()}.md",
            "live_actionable": True,
            "live_reason": "Clearance remains pending for the latest execution state.",
            "render_drift": False,
        },
    }


def _delivery_payload(*, scope_ids: list[str] | None = None) -> dict[str, object]:
    ids = scope_ids or ["B-100"]
    return {
        "version": "v4",
        "scopes": [
            _scope(scope_id=scope_id, scope_label=f"Scope {scope_id}")
            for scope_id in ids
        ],
    }


def _posture() -> dict[str, object]:
    return {
        "status": "attention",
        "clearance": {"state": "pending"},
        "policy": {"breaches": []},
    }


def test_build_reasoning_payload_defaults_to_tribunal_v5_without_provider(tmp_path: Path) -> None:
    payload = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(),
        posture=_posture(),
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=5.0,
        ),
        provider=None,
    )

    assert payload["version"] == "v4"
    assert payload["state"] == "deterministic-only"
    assert payload["actor_policy_version"] == "tribunal-v6"
    assert payload["degraded_reason"] == "ai-provider-disabled"
    assert len(payload["cases"]) == 1
    assert len(payload["case_queue"]) == 1
    case = payload["cases"][0]
    assert case["case_id"] == "case-workstream-B-100"
    assert case["adjudication"]["form"] == "ownership_challenge"
    assert case["packet"]["execution_mode"] in {"ai_engine", "hybrid", "deterministic", "manual"}


def test_build_reasoning_payload_uses_validated_provider_output_when_evidence_checks_pass(tmp_path: Path) -> None:
    payload = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload={"version": "v4", "scopes": [_scope(scope_id="B-061", scope_label="Scope B-061", status="implementation", code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"])]},
        posture=_posture(),
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="test-model",
            base_url="http://example.invalid",
            api_key="test",
            scope_cap=5,
            timeout_seconds=5.0,
        ),
        provider=_StubProvider(),
    )

    assert payload["state"] == "hybrid"
    assert payload["degraded_reason"] == ""
    assert payload["stats"]["ai_case_count"] == 1
    assert payload["stats"]["candidate_count"] == 1
    assert "moving the evaluator" in payload["case_queue"][0]["headline"]
    assert payload["cases"][0]["reasoning"]["provider_validated"] is True
    assert "Validated provider read" in payload["cases"][0]["adjudication"]["leading_explanation"]


def test_build_reasoning_payload_falls_back_when_provider_output_fails_validation(tmp_path: Path) -> None:
    payload = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload={"version": "v4", "scopes": [_scope(scope_id="B-061", scope_label="Scope B-061", status="implementation", code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"])]},
        posture=_posture(),
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="test-model",
            base_url="http://example.invalid",
            api_key="test",
            scope_cap=5,
            timeout_seconds=5.0,
        ),
        provider=_InvalidProvider(),
    )

    assert payload["state"] == "ready"
    assert payload["degraded_reason"] == "ai-validation-failed"
    assert payload["stats"]["ai_case_count"] == 0
    assert payload["cases"][0]["reasoning"]["provider_used"] is True
    assert payload["cases"][0]["reasoning"]["provider_validated"] is False
    assert "evaluator" in payload["cases"][0]["adjudication"]["leading_explanation"]


def test_build_reasoning_payload_sanitizes_provider_raw_paths_into_artifact_labels(tmp_path: Path) -> None:
    payload = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload={"version": "v4", "scopes": [_scope(scope_id="B-061", scope_label="Scope B-061", status="implementation", code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"])]},
        posture=_posture(),
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="test-model",
            base_url="http://example.invalid",
            api_key="test",
            scope_cap=5,
            timeout_seconds=5.0,
        ),
        provider=_PathLeakingProvider(),
    )

    case = payload["cases"][0]
    assert payload["state"] == "hybrid"
    assert payload["stats"]["ai_case_count"] == 1
    assert case["reasoning"]["provider_validated"] is True
    assert "odylith_reasoning.py" in case["maintainer_brief"]
    assert operator_readout.RAW_PATH_RE.search(case["maintainer_brief"]) is None
    assert operator_readout.RAW_PATH_RE.search(case["adjudication"]["leading_explanation"]) is None
    assert operator_readout.RAW_PATH_RE.search(case["adjudication"]["discriminating_next_check"]) is None


def test_build_reasoning_payload_reuses_cached_case_when_fingerprint_is_unchanged(tmp_path: Path) -> None:
    first = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(scope_ids=["B-037"]),
        posture=_posture(),
    )

    second = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(scope_ids=["B-037"]),
        posture=_posture(),
        previous_payload=first,
    )

    assert second["stats"]["candidate_count"] == 1
    assert second["stats"]["reused_count"] == 1
    assert second["stats"]["generated_count"] == 0
    assert second["cases"][0]["case_id"] == first["cases"][0]["case_id"]


def test_build_reasoning_payload_retries_cached_failed_provider_case(tmp_path: Path) -> None:
    config = odylith_reasoning.ReasoningConfig(
        mode="auto",
        provider="openai-compatible",
        model="test-model",
        base_url="http://example.invalid",
        api_key="test",
        scope_cap=5,
        timeout_seconds=5.0,
    )
    delivery_payload = {
        "version": "v4",
        "scopes": [_scope(scope_id="B-061", scope_label="Scope B-061", status="implementation", code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"])],
    }

    first = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload=delivery_payload,
        posture=_posture(),
        config=config,
        provider=_InvalidProvider(),
    )
    second = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload=delivery_payload,
        posture=_posture(),
        previous_payload=first,
        config=config,
        provider=_StubProvider(),
    )

    assert first["cases"][0]["reasoning"]["provider_validated"] is False
    assert second["stats"]["reused_count"] == 0
    assert second["stats"]["generated_count"] == 1
    assert second["cases"][0]["reasoning"]["provider_validated"] is True


def test_build_reasoning_payload_regenerates_when_provider_contract_changes(tmp_path: Path) -> None:
    first = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload={"version": "v4", "scopes": [_scope(scope_id="B-061", scope_label="Scope B-061", status="implementation", code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"])]},
        posture=_posture(),
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=5.0,
        ),
        provider=None,
    )

    second = odylith_reasoning.build_reasoning_payload(
        repo_root=tmp_path,
        delivery_payload={"version": "v4", "scopes": [_scope(scope_id="B-061", scope_label="Scope B-061", status="implementation", code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"])]},
        posture=_posture(),
        previous_payload=first,
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="test-model",
            base_url="http://example.invalid",
            api_key="test",
            scope_cap=5,
            timeout_seconds=5.0,
        ),
        provider=_StubProvider(),
    )

    assert second["stats"]["reused_count"] == 0
    assert second["stats"]["generated_count"] == 1
    assert second["cases"][0]["reasoning"]["provider_validated"] is True


def test_reasoning_config_from_env_normalizes_invalid_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODYLITH_REASONING_MODE", "manual")
    monkeypatch.setenv("ODYLITH_REASONING_PROVIDER", "OpenAI-Compatible")
    monkeypatch.setenv("ODYLITH_REASONING_MODEL", " tribunal-editor ")
    monkeypatch.setenv("ODYLITH_REASONING_BASE_URL", " https://example.invalid/api/ ")
    monkeypatch.setenv("ODYLITH_REASONING_API_KEY", " secret ")
    monkeypatch.setenv("ODYLITH_REASONING_SCOPE_CAP", "not-a-number")
    monkeypatch.setenv("ODYLITH_REASONING_TIMEOUT_SECONDS", "not-a-number")

    config = odylith_reasoning.reasoning_config_from_env()

    assert config.mode == "auto"
    assert config.provider == "openai-compatible"
    assert config.model == "tribunal-editor"
    assert config.base_url == "https://example.invalid/api/"
    assert config.api_key == "secret"
    assert config.scope_cap == 5
    assert config.timeout_seconds == 20.0
    assert config.codex_reasoning_effort == "high"
    assert config.config_source == "env-overrides"


def test_reasoning_config_from_env_clamps_lower_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODYLITH_REASONING_SCOPE_CAP", "0")
    monkeypatch.setenv("ODYLITH_REASONING_TIMEOUT_SECONDS", "0")

    config = odylith_reasoning.reasoning_config_from_env()

    assert config.scope_cap == 1
    assert config.timeout_seconds == 1.0


def test_reasoning_config_path_uses_repo_local_odylith_state_root(tmp_path: Path) -> None:
    assert odylith_reasoning.reasoning_config_path(repo_root=tmp_path) == (
        tmp_path / ".odylith" / "reasoning.config.v1.json"
    ).resolve()


def test_reasoning_config_from_repo_local_file(tmp_path: Path) -> None:
    config_path = tmp_path / ".odylith" / "reasoning.config.v1.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "mode": "auto",
                "provider": "codex-cli",
                "model": "Codex-Spark 5.3",
                "scope_cap": 7,
                "timeout_seconds": 9.0,
                "codex_bin": "codex",
                "codex_reasoning_effort": "medium",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    config = odylith_reasoning.reasoning_config_from_env(repo_root=tmp_path, environ={})

    assert config.provider == "codex-cli"
    assert config.model == ""
    assert config.scope_cap == 7
    assert config.timeout_seconds == 9.0
    assert config.codex_reasoning_effort == "medium"
    assert config.config_source == "repo-config"
    assert config.config_path == str(config_path.resolve())


def test_reasoning_config_from_repo_local_file_resolves_codex_bin_to_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    config_path = tmp_path / ".odylith" / "reasoning.config.v1.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "mode": "auto",
                "provider": "codex-cli",
                "model": "Codex-Spark 5.3",
                "codex_bin": "codex",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    config = odylith_reasoning.reasoning_config_from_env(repo_root=tmp_path, environ={})

    assert config.codex_bin == str(codex_bin.resolve())


def test_reasoning_config_from_env_defaults_to_codex_cli_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    config = odylith_reasoning.reasoning_config_from_env(repo_root=tmp_path, environ={"CODEX_THREAD_ID": "thread-1"})

    assert config.provider == "codex-cli"
    assert config.model == ""
    assert config.codex_bin == str(codex_bin.resolve())


def test_reasoning_config_from_env_keeps_release_smoke_on_deterministic_auto_local(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    config = odylith_reasoning.reasoning_config_from_env(
        repo_root=tmp_path,
        environ={
            "CODEX_THREAD_ID": "thread-1",
            "ODYLITH_RELEASE_BASE_URL": "http://127.0.0.1:8123",
        },
    )

    assert config.provider == "auto-local"
    assert config.codex_bin == str(codex_bin.resolve())


def test_reasoning_config_from_env_defaults_to_claude_cli_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_bin = tmp_path / "bin" / "claude"
    claude_bin.parent.mkdir(parents=True, exist_ok=True)
    claude_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(claude_bin) if token in {"claude", "claude-code"} else None,
    )

    config = odylith_reasoning.reasoning_config_from_env(repo_root=tmp_path, environ={"CLAUDE_CODE_SIMPLE": "1"})

    assert config.provider == "claude-cli"
    assert config.claude_bin == str(claude_bin.resolve())


def test_reasoning_config_from_env_prefers_active_claude_host_when_both_local_bins_exist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    claude_bin = tmp_path / "bin" / "claude"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    claude_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: (
            str(codex_bin)
            if token == "codex"
            else str(claude_bin)
            if token in {"claude", "claude-code"}
            else None
        ),
    )

    config = odylith_reasoning.reasoning_config_from_env(
        repo_root=tmp_path,
        environ={
            "CLAUDE_CODE_SIMPLE": "1",
            "CODEX_THREAD_ID": "thread-1",
        },
    )

    assert config.provider == "claude-cli"
    assert config.codex_bin == str(codex_bin.resolve())
    assert config.claude_bin == str(claude_bin.resolve())


def test_cheap_structured_reasoning_profile_prefers_codex_on_auto_local(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    profile = odylith_reasoning.cheap_structured_reasoning_profile(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="auto-local",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            claude_bin="claude",
        ),
        environ={"CODEX_THREAD_ID": "thread-1"},
    )

    assert profile.provider == "codex-cli"
    assert profile.model == "gpt-5.3-codex-spark"
    assert profile.reasoning_effort == "medium"


def test_cheap_structured_reasoning_profile_prefers_claude_on_auto_local(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_bin = tmp_path / "bin" / "claude"
    claude_bin.parent.mkdir(parents=True, exist_ok=True)
    claude_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(claude_bin) if token in {"claude", "claude-code"} else None,
    )

    profile = odylith_reasoning.cheap_structured_reasoning_profile(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="auto-local",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            claude_bin="claude",
        ),
        environ={"CLAUDE_CODE_SIMPLE": "1"},
    )

    assert profile.provider == "claude-cli"
    assert profile.model == "haiku"
    assert profile.reasoning_effort == "medium"


def test_cheap_structured_reasoning_profile_advances_codex_ladder_after_budget_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    profile = odylith_reasoning.cheap_structured_reasoning_profile(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="auto-local",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            claude_bin="claude",
        ),
        environ={"CODEX_THREAD_ID": "thread-1"},
        previous_model="gpt-5.3-codex-spark",
        failure_code="credits_exhausted",
        failure_detail="You've hit your usage limit for GPT-5.3-Codex-Spark.",
    )

    assert profile.provider == "codex-cli"
    assert profile.model == "gpt-5.3-codex"
    assert profile.reasoning_effort == "medium"


def test_cheap_structured_reasoning_profile_advances_claude_ladder_after_budget_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_bin = tmp_path / "bin" / "claude"
    claude_bin.parent.mkdir(parents=True, exist_ok=True)
    claude_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(claude_bin) if token in {"claude", "claude-code"} else None,
    )

    profile = odylith_reasoning.cheap_structured_reasoning_profile(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="auto-local",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            claude_bin="claude",
        ),
        environ={"CLAUDE_CODE_SIMPLE": "1"},
        previous_model="haiku",
        failure_code="rate_limited",
        failure_detail="Claude reported rate limit for haiku.",
    )

    assert profile.provider == "claude-cli"
    assert profile.model == "sonnet"
    assert profile.reasoning_effort == "medium"


def test_cheap_structured_reasoning_profile_falls_back_to_local_host_when_openai_config_is_incomplete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    profile = odylith_reasoning.cheap_structured_reasoning_profile(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            claude_bin="claude",
        ),
        environ={"CODEX_THREAD_ID": "thread-1"},
    )

    assert profile.provider == "codex-cli"
    assert profile.model == "gpt-5.3-codex-spark"
    assert profile.reasoning_effort == "medium"


def test_reasoning_config_from_env_overrides_repo_local_file(tmp_path: Path) -> None:
    config_path = tmp_path / ".odylith" / "reasoning.config.v1.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "mode": "auto",
                "provider": "codex-cli",
                "model": "Codex-Spark 5.3",
                "scope_cap": 7,
                "timeout_seconds": 9.0,
                "codex_bin": "codex",
                "codex_reasoning_effort": "medium",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    config = odylith_reasoning.reasoning_config_from_env(
        repo_root=tmp_path,
        environ={
            "ODYLITH_REASONING_PROVIDER": "openai-compatible",
            "ODYLITH_REASONING_MODEL": "tribunal-editor",
            "ODYLITH_REASONING_BASE_URL": "https://example.invalid/api",
            "ODYLITH_REASONING_API_KEY": "secret",
        },
    )

    assert config.provider == "openai-compatible"
    assert config.model == "tribunal-editor"
    assert config.base_url == "https://example.invalid/api"
    assert config.api_key == "secret"
    assert config.scope_cap == 7
    assert config.config_source == "repo-config+env-overrides"


def test_persisted_reasoning_config_payload_omits_raw_api_key() -> None:
    payload = odylith_reasoning.persisted_reasoning_config_payload(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="tribunal-editor",
            base_url="https://example.invalid/api",
            api_key="secret",
            api_key_env="ODYLITH_REASONING_API_KEY",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        )
    )

    assert payload["version"] == "v1"
    assert payload["api_key_env"] == "ODYLITH_REASONING_API_KEY"
    assert "api_key" not in payload


def test_persisted_reasoning_config_payload_resolves_codex_cli_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "codex"
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    payload = odylith_reasoning.persisted_reasoning_config_payload(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="Codex-Spark 5.3",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        )
    )

    assert payload["codex_bin"] == str(codex_bin.resolve())
    assert payload["model"] == ""


def test_provider_from_config_requires_supported_auto_provider() -> None:
    disabled = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="disabled",
            provider="openai-compatible",
            model="m",
            base_url="https://example.invalid",
            api_key="k",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_reasoning_effort="high",
        )
    )
    unsupported = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="other",
            model="m",
            base_url="https://example.invalid",
            api_key="k",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_reasoning_effort="high",
        )
    )
    missing_fields = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="",
            base_url="https://example.invalid",
            api_key="k",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_reasoning_effort="high",
        )
    )
    valid = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="openai-compatible",
            model="tribunal-editor",
            base_url="https://example.invalid",
            api_key="k",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_reasoning_effort="high",
        )
    )

    assert disabled is None
    assert unsupported is None
    assert missing_fields is None
    assert isinstance(valid, odylith_reasoning.OpenAICompatibleReasoningProvider)


def test_provider_from_config_supports_codex_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    provider = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        ),
        repo_root=tmp_path,
    )

    assert isinstance(provider, odylith_reasoning.CodexCliReasoningProvider)


def test_provider_from_config_strips_legacy_codex_model_alias(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    provider = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="Codex-Spark 5.3",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        ),
        repo_root=tmp_path,
    )

    assert isinstance(provider, odylith_reasoning.CodexCliReasoningProvider)
    assert provider._model == ""


def test_provider_from_config_supports_claude_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    claude_bin = tmp_path / "bin" / "claude"
    claude_bin.parent.mkdir(parents=True, exist_ok=True)
    claude_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(claude_bin) if token in {"claude", "claude-code"} else None,
    )

    provider = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="claude-cli",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            claude_bin="claude",
            claude_reasoning_effort="high",
        ),
        repo_root=tmp_path,
    )

    assert isinstance(provider, odylith_reasoning.ClaudeCliReasoningProvider)


def test_provider_from_config_supports_codex_cli_via_default_app_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "Codex.app" / "Contents" / "Resources" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: None)
    monkeypatch.setattr(odylith_reasoning, "_DEFAULT_CODEX_BIN_CANDIDATES", (codex_bin,))

    provider = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="gpt-5.4",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        ),
        repo_root=tmp_path,
    )

    assert isinstance(provider, odylith_reasoning.CodexCliReasoningProvider)


def test_provider_from_config_does_not_implicit_enable_local_provider_in_release_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-1")
    monkeypatch.setenv("ODYLITH_RELEASE_BASE_URL", "http://127.0.0.1:8123")

    provider = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="auto-local",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        ),
        repo_root=tmp_path,
        allow_implicit_local_provider=True,
    )

    assert provider is None


def test_provider_from_config_can_ignore_mode_gate_for_opt_in_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_bin = tmp_path / "bin" / "codex"
    codex_bin.parent.mkdir(parents=True, exist_ok=True)
    codex_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(codex_bin) if token == "codex" else None,
    )

    provider = odylith_reasoning.provider_from_config(
        odylith_reasoning.ReasoningConfig(
            mode="disabled",
            provider="codex-cli",
            model="gpt-5.4",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        ),
        repo_root=tmp_path,
        require_auto_mode=False,
    )

    assert isinstance(provider, odylith_reasoning.CodexCliReasoningProvider)


def test_openai_provider_returns_none_when_unconfigured() -> None:
    provider = odylith_reasoning.OpenAICompatibleReasoningProvider(
        base_url="",
        api_key="",
        model="",
        timeout_seconds=2.0,
    )

    assert provider.generate_finding(prompt_payload={"case": "B-061"}) is None


def test_claude_cli_reasoning_provider_parses_json_result_wrapper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_bin = tmp_path / "bin" / "claude"
    claude_bin.parent.mkdir(parents=True, exist_ok=True)
    claude_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(claude_bin) if token in {"claude", "claude-code"} else None,
    )

    def _fake_run(*args, **kwargs):  # noqa: ANN001
        _ = (args, kwargs)
        return subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout=json.dumps(
                {
                    "type": "result",
                    "result": json.dumps({"leading_explanation": {"text": "A", "evidence_ids": ["E1"]}}),
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    provider = odylith_reasoning.ClaudeCliReasoningProvider(
        repo_root=tmp_path,
        claude_bin="claude",
        model="",
        timeout_seconds=3.0,
        reasoning_effort="high",
    )
    result = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt="Return JSON only.",
            schema_name="schema",
            output_schema={"type": "object"},
            prompt_payload={"case": "B-061"},
        )
    )

    assert result == {"leading_explanation": {"text": "A", "evidence_ids": ["E1"]}}


def test_claude_cli_reasoning_provider_passes_schema_model_and_effort(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_bin = tmp_path / "bin" / "claude"
    claude_bin.parent.mkdir(parents=True, exist_ok=True)
    claude_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    claude_bin.chmod(0o755)
    monkeypatch.setattr(
        odylith_reasoning.shutil,
        "which",
        lambda token: str(claude_bin) if token in {"claude", "claude-code"} else None,
    )

    observed: dict[str, object] = {}

    def _fake_run(command, **kwargs):  # noqa: ANN001
        observed["command"] = list(command)
        observed["stdin"] = kwargs["input"]
        observed["timeout"] = kwargs["timeout"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"type": "result", "result": json.dumps({"ok": True})}),
            stderr="",
        )

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    provider = odylith_reasoning.ClaudeCliReasoningProvider(
        repo_root=tmp_path,
        claude_bin="claude",
        model="claude-default",
        timeout_seconds=3.0,
        reasoning_effort="high",
    )
    result = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt="Return JSON only.",
            schema_name="schema",
            output_schema={
                "type": "object",
                "required": ["ok"],
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
            },
            prompt_payload={"case": "B-061"},
            model="claude-custom",
            reasoning_effort="low",
            timeout_seconds=17.0,
        )
    )

    assert result == {"ok": True}
    command = observed["command"]
    assert isinstance(command, list)
    assert command[command.index("--model") + 1] == "claude-custom"
    assert command[command.index("--effort") + 1] == "low"
    system_prompt = command[command.index("--append-system-prompt") + 1]
    assert '"ok"' in system_prompt
    assert "schema" in system_prompt.lower()
    assert observed["stdin"] == json.dumps({"case": "B-061"}, sort_keys=True, ensure_ascii=False)
    assert observed["timeout"] == 17.0


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("not-json", None),
        (json.dumps({"choices": []}), None),
        (
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"type": "text", "text": json.dumps({"leading_explanation": {"text": "A", "evidence_ids": ["E1"]}, "strongest_rival": {"text": "B", "evidence_ids": ["E2"]}, "risk_if_wrong": {"text": "C", "evidence_ids": ["E3"]}, "discriminating_next_check": {"text": "D", "evidence_ids": ["E4"]}, "maintainer_brief": {"text": "E", "evidence_ids": ["E1", "E4"]}})}
                                ]
                            }
                        }
                    ]
                }
            ),
            {
                "leading_explanation": {"text": "A", "evidence_ids": ["E1"]},
                "strongest_rival": {"text": "B", "evidence_ids": ["E2"]},
                "risk_if_wrong": {"text": "C", "evidence_ids": ["E3"]},
                "discriminating_next_check": {"text": "D", "evidence_ids": ["E4"]},
                "maintainer_brief": {"text": "E", "evidence_ids": ["E1", "E4"]},
            },
        ),
    ],
)
def test_openai_provider_generate_finding_parses_supported_response_shapes(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    expected: dict[str, str] | None,
) -> None:
    provider = odylith_reasoning.OpenAICompatibleReasoningProvider(
        base_url="https://example.invalid",
        api_key="secret",
        model="tribunal-editor",
        timeout_seconds=2.0,
    )
    monkeypatch.setattr(
        odylith_reasoning.urllib.request,
        "urlopen",
        lambda request, timeout: _FakeResponse(body),  # noqa: ARG005
    )

    result = provider.generate_finding(prompt_payload={"case_id": "case-workstream-B-061"})

    assert result == expected


def test_openai_provider_generate_finding_returns_none_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = odylith_reasoning.OpenAICompatibleReasoningProvider(
        base_url="https://example.invalid",
        api_key="secret",
        model="tribunal-editor",
        timeout_seconds=2.0,
    )

    def _boom(request, timeout):  # noqa: ANN001, ARG001
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(odylith_reasoning.urllib.request, "urlopen", _boom)

    assert provider.generate_finding(prompt_payload={"case_id": "case-workstream-B-061"}) is None
    assert provider.last_failure_code == "transport_error"


def test_codex_cli_provider_records_timeout_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    def _fake_run(command, **kwargs):  # noqa: ANN001
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs["timeout"])

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    assert provider.generate_finding(prompt_payload={"case_id": "case-workstream-B-061"}) is None
    assert provider.last_failure_code == "timeout"
    assert "2.0s" in provider.last_failure_detail


def test_codex_cli_provider_classifies_rate_limit_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    def _fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="429 Too Many Requests: rate limit reached")

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    assert provider.generate_finding(prompt_payload={"case_id": "case-workstream-B-061"}) is None
    assert provider.last_failure_code == "rate_limited"
    assert "rate limit" in provider.last_failure_detail.lower()


def test_codex_cli_provider_classifies_credit_limit_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    def _fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="Error: insufficient_quota. You have run out of credits.")

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    assert provider.generate_finding(prompt_payload={"case_id": "case-workstream-B-061"}) is None
    assert provider.last_failure_code == "credits_exhausted"
    assert "credits" in provider.last_failure_detail.lower() or "quota" in provider.last_failure_detail.lower()


def test_codex_cli_provider_failure_excerpt_keeps_tail_for_real_error_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    noisy_stdout = "OpenAI Codex banner " + ("x" * 320)
    noisy_stderr = "fatal: insufficient_quota. You have run out of credits."

    def _fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        return subprocess.CompletedProcess(command, 1, stdout=noisy_stdout, stderr=noisy_stderr)

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    assert provider.generate_finding(prompt_payload={"case_id": "case-workstream-B-061"}) is None
    assert provider.last_failure_code == "credits_exhausted"
    assert "insufficient_quota" in provider.last_failure_detail


def test_openai_provider_generate_structured_uses_custom_request_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = odylith_reasoning.OpenAICompatibleReasoningProvider(
        base_url="https://example.invalid",
        api_key="secret",
        model="tribunal-editor",
        timeout_seconds=2.0,
    )
    captured = {}

    def _fake_urlopen(request, timeout):  # noqa: ANN001
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"choices": [{"message": {"content": '{"ok":true}'}}]}))

    monkeypatch.setattr(odylith_reasoning.urllib.request, "urlopen", _fake_urlopen)

    result = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt="custom prompt",
            schema_name="compass_brief",
            output_schema={
                "type": "object",
                "required": ["ok"],
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
            },
            prompt_payload={"scope": "B-101"},
        )
    )

    assert result == {"ok": True}
    assert captured["timeout"] == 2.0
    assert captured["body"]["messages"][0]["content"] == "custom prompt"
    assert captured["body"]["response_format"]["json_schema"]["name"] == "compass_brief"
    assert captured["body"]["response_format"]["json_schema"]["schema"]["required"] == ["ok"]


def test_codex_cli_provider_generate_finding_parses_schema_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    def _fake_run(command, **kwargs):  # noqa: ANN001
        assert '-c' in command
        assert 'model_reasoning_effort="high"' in command
        output_path = Path(command[command.index("--output-last-message") + 1])
        schema_path = Path(command[command.index("--output-schema") + 1])
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert schema["required"] == [
            "leading_explanation",
            "strongest_rival",
            "risk_if_wrong",
            "discriminating_next_check",
            "maintainer_brief",
        ]
        output_path.write_text(
            json.dumps(
                {
                    "leading_explanation": {"text": "A", "evidence_ids": ["E1"]},
                    "strongest_rival": {"text": "B", "evidence_ids": ["E2"]},
                    "risk_if_wrong": {"text": "C", "evidence_ids": ["E3"]},
                    "discriminating_next_check": {"text": "D", "evidence_ids": ["E4"]},
                    "maintainer_brief": {"text": "E", "evidence_ids": ["E1", "E4"]},
                }
            ),
            encoding="utf-8",
        )
        assert kwargs["input"]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    result = provider.generate_finding(prompt_payload={"case_id": "case-workstream-B-061", "evidence_items": []})

    assert result == {
        "leading_explanation": {"text": "A", "evidence_ids": ["E1"]},
        "strongest_rival": {"text": "B", "evidence_ids": ["E2"]},
        "risk_if_wrong": {"text": "C", "evidence_ids": ["E3"]},
        "discriminating_next_check": {"text": "D", "evidence_ids": ["E4"]},
        "maintainer_brief": {"text": "E", "evidence_ids": ["E1", "E4"]},
    }


def test_codex_cli_provider_generate_structured_writes_custom_schema(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    def _fake_run(command, **kwargs):  # noqa: ANN001
        schema_path = Path(command[command.index("--output-schema") + 1])
        output_path = Path(command[command.index("--output-last-message") + 1])
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert schema["required"] == ["ok"]
        assert 'model_reasoning_effort="medium"' in command
        assert command[command.index("--model") + 1] == "gpt-5.3-codex-spark"
        assert kwargs["timeout"] == 17.0
        output_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    result = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt="custom prompt",
            schema_name="compass_brief",
            output_schema={
                "type": "object",
                "required": ["ok"],
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
            },
            prompt_payload={"scope": "B-101"},
            model="gpt-5.3-codex-spark",
            reasoning_effort="medium",
            timeout_seconds=17.0,
        )
    )

    assert result == {"ok": True}


def test_codex_cli_provider_generate_structured_falls_back_to_stdout_when_output_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    def _fake_run(command, **kwargs):  # noqa: ANN001
        output_path = Path(command[command.index("--output-last-message") + 1])
        assert not output_path.exists()
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    result = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt="custom prompt",
            schema_name="compass_brief",
            output_schema={
                "type": "object",
                "required": ["ok"],
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
            },
            prompt_payload={"scope": "B-101"},
        )
    )

    assert result == {"ok": True}


def test_codex_cli_provider_generate_structured_falls_back_to_stdout_when_output_file_is_unreadable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = odylith_reasoning.CodexCliReasoningProvider(
        repo_root=tmp_path,
        codex_bin="codex",
        model="gpt-5.4",
        timeout_seconds=2.0,
        reasoning_effort="high",
    )
    monkeypatch.setattr(odylith_reasoning.shutil, "which", lambda token: "/usr/bin/codex" if token == "codex" else None)

    def _fake_run(command, **kwargs):  # noqa: ANN001
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("{", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1, stdout=json.dumps({"ok": True}), stderr="codex wrote fallback output")

    monkeypatch.setattr(odylith_reasoning.subprocess, "run", _fake_run)

    result = provider.generate_structured(
        request=odylith_reasoning.StructuredReasoningRequest(
            system_prompt="custom prompt",
            schema_name="compass_brief",
            output_schema={
                "type": "object",
                "required": ["ok"],
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
            },
            prompt_payload={"scope": "B-101"},
        )
    )

    assert result == {"ok": True}
