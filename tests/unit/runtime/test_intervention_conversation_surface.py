from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import surface_runtime


def _seed_repo(root: Path) -> None:
    (root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        json.dumps({"version": "v1", "components": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "v1", "diagrams": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "radar" / "traceability-graph.v1.json").write_text(
        json.dumps({"version": "v1", "workstreams": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "casebook" / "bugs").mkdir(parents=True, exist_ok=True)


def test_prompt_submit_live_surface_keeps_top_level_observation_and_teaser(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    observation = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="prompt_submit",
        session_id="surface-1",
        prompt_excerpt="Design a conversation observation engine with governed proposal flow.",
    )

    bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=observation,
    )

    assert bundle["observation"]["turn_phase"] == "prompt_submit"
    assert bundle["intervention_bundle"]["candidate"]["stage"] == "teaser"
    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
    )
    assert rendered.startswith("Odylith can already")
    assert rendered.endswith("turn that into a proposal.")


def test_post_edit_live_surface_renders_observation_and_proposal(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="surface-2",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow.",
            changed_paths=["src/odylith/runtime/intervention_engine/voice.py"],
        ),
    )

    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=True,
    )

    assert rendered.startswith("**Odylith Observation:** ")
    assert "\n\n-----\nOdylith Proposal: " in rendered


def test_live_surface_stays_silent_for_bare_changed_paths_without_governed_fact(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="surface-3",
            changed_paths=["src/main.py"],
        ),
    )

    assert bundle["intervention_bundle"]["candidate"]["stage"] == "silent"
    assert bundle["intervention_bundle"]["proposal"]["eligible"] is False
    assert conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=True,
    ) == ""


def test_render_live_text_accepts_raw_intervention_bundle_for_host_overrides() -> None:
    rendered = conversation_surface.render_live_text(
        {
            "candidate": {
                "stage": "card",
                "suppressed_reason": "",
                "markdown_text": "**Odylith Observation:** The signal is real.",
                "plain_text": "Odylith Observation: The signal is real.",
            },
            "proposal": {
                "eligible": True,
                "suppressed_reason": "",
                "markdown_text": '-----\nOdylith Proposal: Odylith is proposing one clean governed bundle for this moment.\n\nTo apply, say "apply this proposal".\n-----',
                "plain_text": '-----\nOdylith Proposal: Odylith is proposing one clean governed bundle for this moment.\n\nTo apply, say "apply this proposal".\n-----',
            },
        },
        markdown=True,
        include_proposal=True,
    )

    assert rendered.startswith("**Odylith Observation:** The signal is real.")
    assert "Odylith Proposal:" in rendered


def test_render_closeout_text_reads_closeout_bundle() -> None:
    rendered = conversation_surface.render_closeout_text(
        {
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            }
        },
        markdown=True,
    )

    assert rendered == "**Odylith Assist:** kept this grounded."


def test_cross_host_live_surface_rendering_stays_consistent(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    base = {
        "turn_phase": "post_bash_checkpoint",
        "session_id": "surface-4",
        "prompt_excerpt": "Design a conversation observation engine with governed proposal flow.",
        "changed_paths": ["src/odylith/runtime/intervention_engine/engine.py"],
    }
    codex_bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation={"host_family": "codex", **base},
    )
    claude_bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation={"host_family": "claude", **base},
    )

    assert conversation_surface.render_live_text(
        codex_bundle,
        markdown=True,
        include_proposal=True,
    ) == conversation_surface.render_live_text(
        claude_bundle,
        markdown=True,
        include_proposal=True,
    )


def test_cross_lane_live_surface_rendering_stays_consistent(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    base = {
        "host_family": "codex",
        "turn_phase": "post_bash_checkpoint",
        "session_id": "surface-5",
        "prompt_excerpt": "Design a conversation observation engine with governed proposal flow.",
        "changed_paths": ["src/odylith/runtime/intervention_engine/apply.py"],
    }
    consumer_bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation={**base, "delivery_snapshot": {"lane": "consumer"}},
    )
    dogfood_bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation={**base, "delivery_snapshot": {"lane": "pinned_dogfood"}},
    )
    source_local_bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation={**base, "delivery_snapshot": {"lane": "source_local"}},
    )

    consumer_text = conversation_surface.render_live_text(
        consumer_bundle,
        markdown=True,
        include_proposal=True,
    )
    assert consumer_text == conversation_surface.render_live_text(
        dogfood_bundle,
        markdown=True,
        include_proposal=True,
    )
    assert consumer_text == conversation_surface.render_live_text(
        source_local_bundle,
        markdown=True,
        include_proposal=True,
    )
