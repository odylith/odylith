from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.surfaces import compass_self_host_runtime


def test_self_host_snapshot_reads_status_and_launcher(monkeypatch, tmp_path: Path) -> None:
    launcher = tmp_path / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(
        compass_self_host_runtime,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_role="product_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
            pinned_version="0.1.6",
            active_version="0.1.6",
            detached=False,
            diverged_from_pin=False,
        ),
    )

    snapshot = compass_self_host_runtime.self_host_snapshot(repo_root=tmp_path)

    assert snapshot["repo_role"] == "product_repo"
    assert snapshot["launcher_present"] is True
    assert snapshot["active_version"] == "0.1.6"


def test_self_host_snapshot_prefers_cached_snapshot_for_shell_safe(monkeypatch, tmp_path: Path) -> None:
    current_path = tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json"
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text(
        '{"self_host": {"repo_role": "product_repo", "active_version": "0.1.11", "launcher_present": true}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        compass_self_host_runtime,
        "version_status",
        lambda **_: (_ for _ in ()).throw(AssertionError("cached shell-safe posture should not hit version_status")),
    )

    snapshot = compass_self_host_runtime.self_host_snapshot(repo_root=tmp_path, prefer_cached=True)

    assert snapshot["repo_role"] == "product_repo"
    assert snapshot["active_version"] == "0.1.11"


def test_self_host_status_fact_uses_standup_builder_for_pinned_dogfood() -> None:
    captured: dict[str, object] = {}

    def fake_standup_fact_builder(**kwargs):  # noqa: ANN003
        captured.update(kwargs)
        return dict(kwargs)

    fact = compass_self_host_runtime.self_host_status_fact(
        {
            "repo_role": "product_repo",
            "posture": "pinned_release",
            "runtime_source": "pinned_runtime",
            "release_eligible": True,
            "pinned_version": "0.1.6",
            "active_version": "0.1.6",
            "launcher_present": True,
        },
        standup_fact_builder=fake_standup_fact_builder,
    )

    assert fact is not None
    assert captured["kind"] == "self_host_status"
    assert "pinned dogfood runtime `0.1.6`" in str(captured["text"])
