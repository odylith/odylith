from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

from odylith.runtime.surfaces import claude_host_prompt_context


def test_render_prompt_context_resolves_first_anchor_via_override() -> None:
    payload = {
        "target_resolution": {
            "candidate_targets": [
                {"path": "odylith/radar/source/queued/B-083.md"},
            ]
        }
    }
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="Continue work on B-083 and CB-104",
        context_output_override="Anchor resolved.\n" + json.dumps(payload),
        conversation_bundle_override={},
    )

    assert "Odylith anchor B-083" in rendered
    assert "primary target odylith/radar/source/queued/B-083.md" in rendered


def test_render_prompt_context_returns_empty_when_no_anchor_present() -> None:
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="No anchor in this prompt.",
        context_output_override="anything",
    )
    assert rendered == ""


def test_render_prompt_context_can_surface_a_teaser_without_anchor() -> None:
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="Design a conversation observation engine with governed proposal flow.",
        intervention_bundle_override={
            "candidate": {
                "stage": "teaser",
                "teaser_text": "Odylith is noticing governed truth take shape here.",
            }
        },
    )

    assert rendered == "Odylith is noticing governed truth take shape here."


def test_render_prompt_context_falls_back_to_relevant_docs_when_no_targets() -> None:
    payload = {"relevant_docs": ["odylith/CLAUDE.md"]}
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="Resolve CB-104",
        context_output_override=json.dumps(payload),
        conversation_bundle_override={},
    )
    assert "Odylith anchor CB-104" in rendered
    assert "relevant doc odylith/CLAUDE.md" in rendered


def test_main_runs_context_command_for_first_anchor(monkeypatch, tmp_path: Path, capsys) -> None:
    project = tmp_path / "repo"
    launcher = project / ".odylith" / "bin"
    launcher.mkdir(parents=True)
    (launcher / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")

    captured: list[list[str]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=20):
        captured.append(list(args))
        payload = {"target_resolution": {"candidate_targets": [{"path": "src/foo.py"}]}}
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="Context resolved.\n" + json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(
        claude_host_prompt_context.claude_host_shared,
        "run_odylith",
        _fake_run_odylith,
    )
    monkeypatch.setattr(
        claude_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {},
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Continue work on B-088"})),
    )

    exit_code = claude_host_prompt_context.main(["--repo-root", str(project)])

    assert exit_code == 0
    assert captured == [["context", "--repo-root", ".", "B-088"]]
    out = capsys.readouterr().out
    assert "Odylith anchor B-088: primary target src/foo.py." in out


def test_main_surfaces_a_teaser_when_launcher_missing_but_prompt_signal_is_real(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project = tmp_path / "repo"
    project.mkdir()

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Continue work on B-088"})),
    )

    exit_code = claude_host_prompt_context.main(["--repo-root", str(project)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert out.startswith("Odylith can already")
    assert "turn that into a proposal." in out
