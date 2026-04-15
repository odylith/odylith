from __future__ import annotations

import io
import json
from pathlib import Path

from odylith import cli
from odylith.runtime.surfaces import claude_host_post_edit_checkpoint
from odylith.runtime.surfaces import claude_host_prompt_context
from odylith.runtime.surfaces import claude_host_stop_summary
from odylith.runtime.surfaces import codex_host_post_bash_checkpoint
from odylith.runtime.surfaces import codex_host_prompt_context
from odylith.runtime.surfaces import codex_host_stop_summary


def _shared_checkpoint_bundle() -> dict[str, object]:
    return {
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "key": "iv-parity",
                "suppressed_reason": "",
                "markdown_text": (
                    "**Odylith Observation:** Radar already has a governed slice here, "
                    "so this should keep moving through the same governed thread."
                ),
                "plain_text": (
                    "Odylith Observation: Radar already has a governed slice here, "
                    "so this should keep moving through the same governed thread."
                ),
            },
            "proposal": {
                "eligible": True,
                "suppressed_reason": "",
                "markdown_text": (
                    "-----\n"
                    "Odylith Proposal: Odylith is proposing one clean governed bundle for this moment.\n\n"
                    "- Radar: extend B-096.\n"
                    "- Registry: refresh governance-intervention-engine.\n\n"
                    "To apply, say \"apply this proposal\".\n"
                    "-----"
                ),
                "plain_text": (
                    "Odylith Proposal: Odylith is proposing one clean governed bundle for this moment."
                ),
            },
        },
        "closeout_bundle": {
            "markdown_text": "**Odylith Assist:** kept this grounded.",
            "plain_text": "Odylith Assist: kept this grounded.",
        },
    }


def test_cross_host_prompt_teaser_rendering_stays_consistent() -> None:
    prompt = "Design a conversation observation engine with governed proposal flow."
    intervention = {
        "candidate": {
            "stage": "teaser",
            "teaser_text": (
                "Odylith can already see governed truth starting to crystallize here. "
                "One more corroborating signal and it can turn that into a proposal."
            ),
        }
    }

    codex_text = codex_host_prompt_context.render_codex_prompt_context(
        prompt=prompt,
        intervention_bundle_override=intervention,
    )
    claude_text = claude_host_prompt_context.render_prompt_context(
        prompt=prompt,
        intervention_bundle_override=intervention,
    )

    assert codex_text == claude_text


def test_cross_host_checkpoint_cli_dispatch_stays_consistent_for_same_bundle(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    bundle = _shared_checkpoint_bundle()

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {
                        "command": "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/main.py\n@@\n-old\n+new\n*** End Patch\nPATCH"
                    },
                    "session_id": "checkpoint-parity-1",
                }
            )
        ),
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.codex_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "_post_bash_bundle",
        lambda **kwargs: bundle,
    )

    assert cli.main(["codex", "post-bash-checkpoint", "--repo-root", str(tmp_path)]) == 0
    codex_payload = json.loads(capsys.readouterr().out)

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"file_path": str(tmp_path / "src" / "main.py")},
                    "session_id": "checkpoint-parity-1",
                }
            )
        ),
    )
    monkeypatch.setattr(
        claude_host_post_edit_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        claude_host_post_edit_checkpoint,
        "_post_edit_bundle",
        lambda **kwargs: bundle,
    )

    assert cli.main(["claude", "post-edit-checkpoint", "--repo-root", str(tmp_path)]) == 0
    claude_payload = json.loads(capsys.readouterr().out)

    assert codex_payload["hookSpecificOutput"]["additionalContext"] == claude_payload["additionalContext"]
    assert codex_payload["systemMessage"] == claude_payload["systemMessage"]


def test_cross_host_stop_rendering_stays_consistent_for_same_bundle(tmp_path: Path) -> None:
    bundle = {
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "suppressed_reason": "",
                "markdown_text": "**Odylith Observation:** The signal is real.",
                "plain_text": "Odylith Observation: The signal is real.",
            },
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
        "closeout_bundle": {
            "markdown_text": "**Odylith Assist:** kept this grounded.",
            "plain_text": "Odylith Assist: kept this grounded.",
        },
    }

    codex_text = codex_host_stop_summary.render_codex_stop_summary(
        str(tmp_path),
        message="Implemented the engine slice.",
        session_id="stop-parity-1",
        conversation_bundle_override=bundle,
    )
    claude_text = claude_host_stop_summary.render_stop_summary(
        repo_root=tmp_path,
        payload={
            "last_assistant_message": "Implemented the engine slice.",
            "session_id": "stop-parity-1",
        },
        conversation_bundle_override=bundle,
    )

    assert codex_text == claude_text
