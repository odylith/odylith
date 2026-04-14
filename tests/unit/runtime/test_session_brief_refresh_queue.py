from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import session_brief_refresh_queue


def test_queue_refresh_if_briefs_stale_dedupes_same_brief(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    runtime_path = repo_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(
        json.dumps(
            {
                "standup_brief": {
                    "24h": {
                        "generated_utc": "2026-04-13T00:00:00Z",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    launches: list[list[str]] = []

    class _FakePopen:
        def __init__(self, args, **kwargs):  # noqa: ANN001
            launches.append(list(args))

    monkeypatch.setattr(session_brief_refresh_queue.subprocess, "Popen", _FakePopen)

    first = session_brief_refresh_queue.queue_refresh_if_briefs_stale(
        repo_root=repo_root,
        threshold_seconds=60,
    )
    second = session_brief_refresh_queue.queue_refresh_if_briefs_stale(
        repo_root=repo_root,
        threshold_seconds=60,
    )

    assert first is True
    assert second is False
    assert launches == [
        [str(launcher), "compass", "refresh", "--repo-root", str(repo_root), "--wait"]
    ]
