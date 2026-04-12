from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.surfaces import claude_host_stop_summary


def test_main_logs_meaningful_stop_summary_to_compass(monkeypatch, tmp_path: Path) -> None:
    captured: list[tuple[str, str, list[str]]] = []

    def _fake_run_compass_log(*, project_dir, summary, workstreams):
        captured.append((str(project_dir), summary, list(workstreams)))

    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        _fake_run_compass_log,
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "last_assistant_message": (
                        "Updated CLAUDE assets and validated focused runtime tests for B-083. "
                        "Validation passed on the install and runtime slices."
                    )
                }
            )
        ),
    )

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert len(captured) == 1
    project_dir, summary, workstreams = captured[0]
    assert project_dir == str(tmp_path.resolve())
    assert "Updated CLAUDE assets" in summary
    assert workstreams == ["B-083"]


def test_main_skips_question_shaped_stop_summaries(monkeypatch, tmp_path: Path) -> None:
    called: list[bool] = []
    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        lambda **kwargs: called.append(True),
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"last_assistant_message": "Would you like me to keep going?"})),
    )

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert called == []


def test_main_skips_active_stop_hook_payload(monkeypatch, tmp_path: Path) -> None:
    called: list[bool] = []
    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        lambda **kwargs: called.append(True),
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "stop_hook_active": True,
                    "last_assistant_message": (
                        "Updated CLAUDE assets and validated focused runtime tests for B-083."
                    ),
                }
            )
        ),
    )

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert called == []
