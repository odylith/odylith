from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

from odylith.runtime.surfaces import claude_host_post_edit_checkpoint


def test_should_refresh_returns_true_for_governed_paths() -> None:
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/radar/source/queued/B-999.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/technical-plans/in-progress/2026-04/plan.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/casebook/bugs/CB-123.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/registry/source/components/foo/CURRENT_SPEC.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/atlas/source/diagram.mmd") is True


def test_should_refresh_skips_non_governed_paths_and_agents_files() -> None:
    assert claude_host_post_edit_checkpoint.should_refresh("src/odylith/cli.py") is False
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/radar/source/AGENTS.md") is False
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/registry/source/CLAUDE.md") is False
    assert claude_host_post_edit_checkpoint.should_refresh("") is False


def test_edited_path_returns_relative_token(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    (project / "odylith" / "radar" / "source").mkdir(parents=True)
    target = project / "odylith" / "radar" / "source" / "queued.md"
    target.write_text("# stub\n", encoding="utf-8")

    payload = {"tool_input": {"file_path": str(target)}}
    token = claude_host_post_edit_checkpoint.edited_path(payload=payload, project_dir=project)
    assert token == "odylith/radar/source/queued.md"


def test_edited_path_ignores_files_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    other = tmp_path / "other-file.md"
    other.write_text("# stub\n", encoding="utf-8")
    payload = {"tool_input": {"file_path": str(other)}}
    assert claude_host_post_edit_checkpoint.edited_path(payload=payload, project_dir=project) == ""


def test_main_refreshes_governance_for_governed_edit(monkeypatch, tmp_path: Path, capsys) -> None:
    project = tmp_path / "repo"
    (project / "odylith" / "radar" / "source").mkdir(parents=True)
    target = project / "odylith" / "radar" / "source" / "queued.md"
    target.write_text("# stub\n", encoding="utf-8")

    captured: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=180):
        captured.append((str(project_dir), list(args), timeout))
        return subprocess.CompletedProcess(args, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(
        claude_host_post_edit_checkpoint.claude_host_shared,
        "run_odylith",
        _fake_run_odylith,
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"file_path": str(target)}})),
    )

    exit_code = claude_host_post_edit_checkpoint.main(["--repo-root", str(project)])

    assert exit_code == 0
    assert len(captured) == 1
    project_dir, args, timeout = captured[0]
    assert args[0] == "sync"
    assert "--impact-mode" in args and "selective" in args
    assert "odylith/radar/source/queued.md" in args
    assert timeout == 180
    payload = json.loads(capsys.readouterr().out)
    assert "Odylith governance refresh completed" in payload["systemMessage"]


def test_main_skips_non_governed_edits_silently(monkeypatch, tmp_path: Path, capsys) -> None:
    project = tmp_path / "repo"
    (project / "src").mkdir(parents=True)
    target = project / "src" / "main.py"
    target.write_text("# stub\n", encoding="utf-8")

    called: list[bool] = []

    monkeypatch.setattr(
        claude_host_post_edit_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: called.append(True),
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"file_path": str(target)}})),
    )

    exit_code = claude_host_post_edit_checkpoint.main(["--repo-root", str(project)])

    assert exit_code == 0
    assert called == []
    payload = json.loads(capsys.readouterr().out)
    assert "additionalContext" in payload
    assert "Odylith Assist:" in payload["additionalContext"]


def test_main_emits_observation_and_proposal_for_correlated_edit(monkeypatch, tmp_path: Path, capsys) -> None:
    project = tmp_path / "repo"
    (project / "src").mkdir(parents=True)
    target = project / "src" / "main.py"
    target.write_text("# stub\n", encoding="utf-8")

    monkeypatch.setattr(
        claude_host_post_edit_checkpoint,
        "_post_edit_bundle",
        lambda **kwargs: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "card",
                    "key": "iv-demo",
                    "suppressed_reason": "",
                    "markdown_text": "**Odylith Observation:** The truth is warm.",
                    "plain_text": "Odylith Observation: The truth is warm.",
                    "headline": "The truth is warm.",
                },
                "proposal": {
                    "key": "iv-demo",
                    "eligible": True,
                    "suppressed_reason": "",
                    "markdown_text": 'Odylith Proposal: Odylith is proposing one clean governed bundle for this moment.\n\nTo apply, say "apply this proposal".',
                    "plain_text": "Odylith Proposal",
                    "confirmation_text": "apply this proposal",
                    "action_surfaces": ["radar", "registry"],
                },
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"file_path": str(target)}, "session_id": "session-9"})),
    )

    exit_code = claude_host_post_edit_checkpoint.main(["--repo-root", str(project)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "**Odylith Observation:**" in payload["additionalContext"]
    assert "Odylith Proposal:" in payload["additionalContext"]
    assert "**Odylith Assist:** kept this grounded." in payload["additionalContext"]
    assert "**Odylith Observation:**" in payload["systemMessage"]
    assert "Odylith Proposal:" in payload["systemMessage"]
    assert "Odylith Assist:" not in payload["systemMessage"]


def test_post_edit_bundle_uses_recent_prompt_excerpt_not_intervention_summary(tmp_path: Path) -> None:
    claude_host_post_edit_checkpoint.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Odylith Proposal pending.",
        session_id="edit-1",
        host_family="claude",
        intervention_key="iv-edit-1",
        turn_phase="post_edit_checkpoint",
        prompt_excerpt="Preserve the human prompt across Claude post-edit checkpoints.",
        display_markdown="**Odylith Proposal**",
    )

    bundle = claude_host_post_edit_checkpoint._post_edit_bundle(
        project_dir=tmp_path,
        path_token="src/main.py",
        session_id="edit-1",
    )

    assert bundle["observation"]["prompt_excerpt"] == (
        "Preserve the human prompt across Claude post-edit checkpoints."
    )
