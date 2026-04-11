from __future__ import annotations

import io
import json

from odylith.runtime.surfaces import codex_host_post_bash_checkpoint


def test_post_bash_checkpoint_runs_start_for_edit_like_commands(monkeypatch) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(*, project_dir: str, args: list[str], timeout: int = 20):
        calls.append((project_dir, args, timeout))
        return None

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "apply_patch <<'PATCH'"}})),
    )
    monkeypatch.setattr(codex_host_post_bash_checkpoint.codex_host_shared, "run_odylith", _fake_run_odylith)

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert calls == [("/tmp/repo", ["start", "--repo-root", "."], 20)]


def test_post_bash_checkpoint_skips_non_edit_like_commands(monkeypatch) -> None:
    calls: list[tuple[str, list[str], int]] = []

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "pytest -q"}})),
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.codex_host_shared,
        "run_odylith",
        lambda **kwargs: calls.append((kwargs["project_dir"], kwargs["args"], kwargs["timeout"])),
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert calls == []
