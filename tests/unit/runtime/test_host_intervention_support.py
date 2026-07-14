from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from odylith.runtime.intervention_engine import prompt_signal_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.surfaces import claude_host_prompt_teaser
from odylith.runtime.surfaces import codex_host_prompt_context
from odylith.runtime.surfaces import host_intervention_support


_VISIBILITY_OBSERVATION = (
    "---\n\n**Odylith Observation:** You should see guidance when it matters. This is the visible "
    "checkpoint; future notes will stay concise, useful, and tied to a decision or verified result."
)


_CLI_HELP_OUTPUT = """usage: odylith [-h] {start,context,query,sync,codex} ...

Odylith install, grounding, sync, runtime, and repair tooling.

positional arguments:
  {start,context,query,sync,codex}
    start               Choose the safest first Odylith turn-start path.

options:
  -h, --help            show this help message and exit
"""


def test_join_sections_dedupes_normalized_blocks() -> None:
    assert host_intervention_support.join_sections(" first ", "\nfirst\n", "second") == "first\n\nsecond"


def test_merge_replay_with_closeout_keeps_existing_assist() -> None:
    replay = "---\n\n**Odylith Observation:** already visible.\n\n**Odylith Assist:** already visible.\n\n---"
    closeout = "**Odylith Assist:** keep this grounded."

    rendered = host_intervention_support.merge_replay_with_closeout(replay=replay, closeout_text=closeout)

    assert rendered == "---\n\n**Odylith Observation:** already visible.\n\n---\n\n**Odylith Assist:** already visible."


def test_merge_replay_with_closeout_folds_live_blocks_and_keeps_assist_last() -> None:
    replay = (
        "---\n\n**Odylith Observation:** first visible beat.\n\n---\n\n"
        "---\n\nOdylith Observation: second visible beat.\n\n---"
    )
    closeout = (
        "**Odylith Assist:** keep the closeout grounded.\n"
        "**Odylith Insight:** the supplemental line should not trail Assist."
    )

    rendered = host_intervention_support.merge_replay_with_closeout(
        replay=replay,
        closeout_text=closeout,
    )

    assert rendered.count("---") == 2
    assert rendered.startswith(
        "---\n\n**Odylith Observation:** first visible beat.\n\nOdylith Observation: second visible beat.\n\n---"
    )
    assert rendered.rsplit("\n", maxsplit=1)[-1] == "**Odylith Assist:** keep the closeout grounded."
    assert rendered.index("**Odylith Insight:**") < rendered.index("**Odylith Assist:**")


def test_looks_like_teaser_live_text_distinguishes_full_live_beats() -> None:
    assert host_intervention_support.looks_like_teaser_live_text("Odylith Observation: a real signal is forming.") is True
    assert (
        host_intervention_support.looks_like_teaser_live_text(
            "---\n\n**Odylith Observation:** This is a real visible beat.\n\n---"
        )
        is False
    )


def test_render_prompt_bundle_text_joins_anchor_and_live_text(monkeypatch) -> None:
    monkeypatch.setattr(
        host_intervention_support.conversation_surface,
        "render_live_text",
        lambda *_args, **_kwargs: "Odylith Observation: a real signal is forming.",
    )

    rendered = host_intervention_support.render_prompt_bundle_text(
        bundle={"intervention_bundle": {}},
        anchor_summary="Odylith anchor B-123: primary target src/odylith/runtime/surfaces/host_intervention_support.py.",
        markdown=False,
    )

    assert rendered == (
        "Odylith anchor B-123: primary target src/odylith/runtime/surfaces/host_intervention_support.py.\n\n"
        "Odylith Observation: a real signal is forming."
    )


def test_render_prompt_system_message_appends_assist_for_visibility_feedback(tmp_path: Path) -> None:
    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I still do not see any Odylith interventions or Assist in chat.",
        session_id="visibility-feedback",
    )

    assert rendered.startswith(
        "---\n\n**Odylith Observation:** You should see guidance when it matters. This is the visible checkpoint; future notes will stay concise, useful, and tied to a decision or verified result."
    )
    assert rendered.count("---") == 2
    assert rendered.rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")
    assert "I will make the next decision, risk, or verified result visible in the conversation" in rendered
    assert "Odylith is tracking this signal" not in rendered
    assert "**Odylith Insight:**" not in rendered
    assert "**Odylith Risks:**" not in rendered
    assert "**Odylith History:**" not in rendered
    assert "B-096" not in rendered
    assert "CB-122" not in rendered
    assert "D-038" not in rendered
    assert "Casebook already remembers" not in rendered


def test_prompt_system_message_treats_intervention_experience_feedback_as_earned(tmp_path: Path) -> None:
    prompt = "I prefer Odylith Assist to be more frequent though."

    codex = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt=prompt,
        session_id="experience-codex",
    )
    claude = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="claude",
        prompt=prompt,
        session_id="experience-claude",
    )

    assert codex == claude
    assert codex == (
        "**Odylith Assist:** I will surface meaningful decisions, risks, proof points, "
        "and verified results; routine chatter stays out of the way."
    )
    assert "hook" not in codex.casefold()


def test_prompt_system_message_earns_assist_for_concrete_governed_request(tmp_path: Path) -> None:
    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="Validate B-096 intervention delivery and preserve the cross-host proof boundary.",
        session_id="prompt-signal",
    )

    assert rendered.rsplit("\n", maxsplit=1)[-1] == (
        "**Odylith Assist:** B-096 stays tied to a visible proof checkpoint; "
        "I will surface the evidence that changes its status."
    )


def test_prompt_system_message_earns_assist_for_progress_and_quality_request(tmp_path: Path) -> None:
    prompt = "How are we doing overall on quality, remaining gaps, and release risk?"

    codex = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt=prompt,
        session_id="status-codex",
    )
    claude = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="claude",
        prompt=prompt,
        session_id="status-claude",
    )

    assert codex == claude
    assert codex.rsplit("\n", maxsplit=1)[-1] == (
        "**Odylith Assist:** I will separate verified progress, open risk, and the next gate "
        "so this status guides the next move."
    )


def test_prompt_assist_summary_names_the_signal_that_earned_it() -> None:
    assert prompt_signal_runtime.prompt_assist_summary("Keep this invariant non-negotiable before release.") == (
        "I will treat the stated constraint as a release gate, not a detail to repair later."
    )
    assert prompt_signal_runtime.prompt_assist_summary("Review the audit evidence before we complete this.") == (
        "I will keep the next decision tied to a visible proof checkpoint before it becomes a completion claim."
    )
    assert prompt_signal_runtime.prompt_assist_summary("I prefer Odylith Assist to be more frequent though.") == (
        "I will surface meaningful decisions, risks, proof points, and verified results; routine chatter stays out of the way."
    )
    assert prompt_signal_runtime.prompt_assist_summary("I want to see Odylith Assist in every prompt.") == (
        "I will surface meaningful decisions, risks, proof points, and verified results; routine chatter stays out of the way."
    )
    assert prompt_signal_runtime.prompt_assist_summary("How are we doing overall on quality and gaps?") == (
        "I will separate verified progress, open risk, and the next gate so this status guides the next move."
    )


def test_session_cadence_feedback_surfaces_substantive_continuation_without_forcing_routine_chatter(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="assist_closeout",
        summary="Cadence preference recorded.",
        session_id="cadence-session",
        host_family="codex",
        intervention_key="assist",
        turn_phase="prompt_submit",
        prompt_excerpt="I prefer Odylith Assist to be more frequent though.",
    )

    assert not host_intervention_support.prompt_needs_live_bundle(
        prompt="Thanks.", repo_root=tmp_path, session_id="cadence-session"
    )
    assert host_intervention_support.prompt_needs_live_bundle(
        prompt="Please continue.", repo_root=tmp_path, session_id="cadence-session"
    )
    rendered = {
        host: host_intervention_support.render_prompt_system_message(
            repo_root=tmp_path,
            host_family=host,
            prompt="Please continue.",
            session_id="cadence-session",
        )
        for host in ("codex", "claude")
    }

    assert rendered == {
        "codex": (
            "**Odylith Assist:** I will continue from the last verified checkpoint and call out the next completed "
            "change, remaining risk, and gate."
        ),
        "claude": (
            "**Odylith Assist:** I will continue from the last verified checkpoint and call out the next completed "
            "change, remaining risk, and gate."
        ),
    }
    assert prompt_signal_runtime.has_assist_cadence_signal("Please continue.")
    assert not prompt_signal_runtime.has_assist_cadence_signal("Thanks.")


def test_prompt_assist_summary_makes_opted_in_continuation_informative() -> None:
    assert prompt_signal_runtime.prompt_assist_summary("Please continue.") == (
        "I will continue from the last verified checkpoint and call out the next completed change, remaining risk, and gate."
    )


def test_prompt_hooks_preserve_cadence_without_a_host_session_id(tmp_path: Path) -> None:
    for host in ("codex", "claude"):
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="assist_closeout",
            summary="Cadence preference recorded.",
            host_family=host,
            session_id=host_surface_runtime.normalized_session_id("", host_family=host),
            prompt_excerpt="I want Odylith Assist to be a lot more frequent and informative.",
        )

    codex = codex_host_prompt_context.render_codex_prompt_system_message(
        repo_root=str(tmp_path),
        prompt="Please continue.",
    )
    claude = claude_host_prompt_teaser.render_prompt_teaser(
        repo_root=tmp_path,
        prompt="Please continue.",
    )

    assert codex == claude == (
        "**Odylith Assist:** I will continue from the last verified checkpoint and call out the next completed "
        "change, remaining risk, and gate."
    )


def test_bare_overall_prompt_does_not_trigger_an_assist_hot_path() -> None:
    prompt = "Summarize the overall API surface for this module."

    assert not prompt_signal_runtime.has_prompt_intervention_signal(prompt)
    assert not host_intervention_support.prompt_needs_live_bundle(prompt=prompt)


def test_intervention_experience_classifier_skips_visibility_scan_for_unrelated_prompt(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        prompt_signal_runtime,
        "visibility_feedback_requested",
        lambda **kwargs: calls.append(kwargs) or False,
    )

    assert not prompt_signal_runtime.intervention_experience_feedback_requested(
        prompt="Summarize the current release candidate evidence."
    )
    assert calls == []


def test_intervention_experience_classifier_requires_direct_assist_cadence_feedback(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        prompt_signal_runtime,
        "visibility_feedback_requested",
        lambda **kwargs: calls.append(kwargs) or False,
    )

    assert prompt_signal_runtime.intervention_experience_feedback_requested(
        prompt="I prefer Odylith Assist to be more frequent though."
    )
    assert not prompt_signal_runtime.intervention_experience_feedback_requested(
        prompt="Improve the UX for Odylith interventions in Codex."
    )
    assert not prompt_signal_runtime.intervention_experience_feedback_requested(
        prompt="Make the intervention panel more visible in the dashboard."
    )
    assert not prompt_signal_runtime.intervention_experience_feedback_requested(
        prompt="Design a more insightful Odylith proposal ranking heuristic."
    )
    assert calls == []


def test_prompt_bundle_preserves_engine_alignment_proof_for_visible_assist(tmp_path: Path) -> None:
    bundle = host_intervention_support.build_prompt_conversation_bundle(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I still do not see any Odylith interventions or Assist in chat.",
        session_id="prompt-proof",
    )
    proof = dict(bundle["observation"]["alignment_proof"])
    lanes = {
        row["lane_id"]: row
        for row in proof["lanes"]
        if isinstance(row, dict)
    }

    assert proof["proof_kind"] == "visibility_recovery"
    assert proof["status"] == "ready"
    assert proof["missing_required_lanes"] == []
    assert lanes["context_engine"]["status"] == "covered"
    assert lanes["execution_engine"]["status"] == "covered"
    assert lanes["intervention_engine"]["status"] == "covered"
    assert lanes["tribunal"]["status"] == "covered"
    assert lanes["delivery_intelligence"]["status"] == "covered"
    assert lanes["memory_substrate"]["status"] == "covered"
    assert lanes["subagent_router"]["status"] == "policy_deferred"
    assert lanes["subagent_orchestrator"]["status"] == "policy_deferred"


def test_render_prompt_system_message_keeps_generic_failure_free_of_fake_assist(tmp_path: Path) -> None:
    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I do not think it is working",
        session_id="generic-failure",
    )

    assert rendered.startswith(_VISIBILITY_OBSERVATION)
    assert "**Odylith Assist:**" not in rendered


def test_render_prompt_system_message_suppresses_help_fast_path_and_replay(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending replay that should not leak into CLI help.",
        session_id="help-fast-path",
        host_family="codex",
        intervention_key="help-fast-path-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** stale replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="Odylith, help.",
        session_id="help-fast-path",
    )

    assert rendered == ""


def test_suppress_prompt_live_narration_detects_cli_help_stdout() -> None:
    assert host_intervention_support.suppress_prompt_live_narration(
        prompt="What commands does Odylith support?",
        assistant_summary=_CLI_HELP_OUTPUT,
    )


def test_low_signal_prompt_gate_does_not_import_renderer_stack() -> None:
    script = """
import sys
from odylith.runtime.surfaces import host_intervention_support

heavy = {
    'odylith.runtime.intervention_engine.alignment_context',
    'odylith.runtime.intervention_engine.conversation_surface',
    'odylith.runtime.intervention_engine.host_surface_runtime',
    'odylith.runtime.intervention_engine.visibility_replay',
}
assert not (heavy & set(sys.modules)), sorted(heavy & set(sys.modules))
assert host_intervention_support.prompt_needs_live_bundle(prompt='Odylith, you there?') is False
assert not (heavy & set(sys.modules)), sorted(heavy & set(sys.modules))
"""
    repo_root = Path(__file__).resolve().parents[3]
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{repo_root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_build_stop_conversation_bundle_suppresses_cli_help_stdout(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending stop replay that should not leak into CLI help.",
        session_id="stop-help-fast-path",
        host_family="codex",
        intervention_key="stop-help-fast-path-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** stale stop replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    bundle = host_intervention_support.build_stop_conversation_bundle(
        repo_root=tmp_path,
        host_family="codex",
        session_id="stop-help-fast-path",
        assistant_summary=_CLI_HELP_OUTPUT,
        prompt_excerpt="",
        changed_paths=[],
        workstreams=[],
        components=[],
    )

    assert bundle == {}


def test_render_stop_bundle_text_reuses_replayed_live_beat_when_live_text_is_teaser(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        host_intervention_support.conversation_surface,
        "render_live_text",
        lambda *_args, **_kwargs: "Odylith is tracking a real signal.",
    )
    monkeypatch.setattr(
        host_intervention_support.visibility_replay,
        "replayable_chat_markdown",
        lambda **_kwargs: "---\n\n**Odylith Observation:** replayed live beat.\n\n---",
    )
    monkeypatch.setattr(
        host_intervention_support.conversation_surface,
        "render_closeout_text",
        lambda *_args, **_kwargs: "**Odylith Assist:** keep the closeout grounded.",
    )

    rendered = host_intervention_support.render_stop_bundle_text(
        repo_root=tmp_path,
        host_family="codex",
        session_id="sess-1",
        bundle={"intervention_bundle": {}},
    )

    assert rendered == (
        "---\n\n**Odylith Observation:** replayed live beat.\n\n---\n\n"
        "**Odylith Assist:** keep the closeout grounded."
    )
