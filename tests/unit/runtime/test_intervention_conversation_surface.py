from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.intervention_engine import visibility_broker


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
    assert rendered.startswith("---\n\nOdylith can already")
    assert rendered.endswith("turn that into a proposal.\n\n---")


def test_render_live_text_prefers_ambient_over_teaser_after_prompt_phase() -> None:
    bundle = {
        "ambient_signals": {
            "selected_signal": "insight",
            "insight": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith Insight: this is now grounded enough to keep visible.",
                "markdown_text": "**Odylith Insight:** this is now grounded enough to keep visible.",
            },
        },
        "intervention_bundle": {
            "candidate": {
                "stage": "teaser",
                "suppressed_reason": "",
                "teaser_text": "Odylith can already see governed truth taking shape here.",
            },
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
    }

    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )
    old_order = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
        prefer_ambient_over_teaser=False,
    )

    assert rendered == surface_runtime.wrap_live_text(
        "**Odylith Insight:** this is now grounded enough to keep visible."
    )
    assert old_order == surface_runtime.wrap_live_text("Odylith can already see governed truth taking shape here.")


def test_render_live_text_can_stack_distinct_high_value_ambient_signals() -> None:
    bundle = {
        "ambient_signals": {
            "selected_signal": "risks",
            "selected_signals": ["risks", "history", "insight"],
            "risks": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith Risks: a hard invariant is active before implementation proceeds.",
                "markdown_text": "**Odylith Risks:** a hard invariant is active before implementation proceeds.",
                "semantic_signature": ["hard", "invariant", "implementation"],
            },
            "history": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith History: CB-121 already records this failure mode.",
                "markdown_text": "**Odylith History:** CB-121 already records this failure mode.",
                "semantic_signature": ["cb-121", "failure", "mode"],
            },
            "insight": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith Insight: B-096 is the governed thread that owns the next move.",
                "markdown_text": "**Odylith Insight:** B-096 is the governed thread that owns the next move.",
                "semantic_signature": ["b-096", "governed", "thread"],
            },
        },
        "intervention_bundle": {
            "candidate": {
                "stage": "teaser",
                "suppressed_reason": "",
                "teaser_text": "Odylith can already see governed truth taking shape here.",
            },
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
    }

    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )

    assert rendered == surface_runtime.wrap_live_text(
        "\n\n".join(
            [
                "**Odylith Risks:** a hard invariant is active before implementation proceeds.",
                "**Odylith History:** CB-121 already records this failure mode.",
                "**Odylith Insight:** B-096 is the governed thread that owns the next move.",
            ]
        )
    )


def test_render_live_text_can_stack_same_label_when_candidate_ids_are_distinct() -> None:
    first = {
        "candidate_id": "ambient:risks:first",
        "eligible": True,
        "render_hint": "explicit_label",
        "plain_text": "Odylith Risks: hidden hook payloads are not visibility proof.",
        "markdown_text": "**Odylith Risks:** hidden hook payloads are not visibility proof.",
        "semantic_signature": ["hidden", "hooks", "visibility"],
    }
    second = {
        "candidate_id": "ambient:risks:second",
        "eligible": True,
        "render_hint": "explicit_label",
        "plain_text": "Odylith Risks: duplicate governance writes would corrupt release truth.",
        "markdown_text": "**Odylith Risks:** duplicate governance writes would corrupt release truth.",
        "semantic_signature": ["duplicate", "governance", "release"],
    }
    bundle = {
        "ambient_signals": {
            "selected_signal": "risks",
            "selected_signals": ["risks", "risks"],
            "selected_signal_ids": ["ambient:risks:first", "ambient:risks:second"],
            "ambient_signal_payloads": {
                "ambient:risks:first": first,
                "ambient:risks:second": second,
            },
            "risks": first,
        },
        "intervention_bundle": {
            "candidate": {"stage": "silent", "suppressed_reason": ""},
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
    }

    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )

    assert rendered == surface_runtime.wrap_live_text(
        "\n\n".join([first["markdown_text"], second["markdown_text"]])
    )


def test_ambient_candidate_id_is_not_just_the_signal_label() -> None:
    first = {
        "signal_name": "risks",
        "plain_text": "Odylith Risks: hidden hook payloads are not visibility proof.",
        "duplicate_group": "risk:hidden-hooks",
    }
    second = {
        "signal_name": "risks",
        "plain_text": "Odylith Risks: duplicate governance writes would corrupt release truth.",
        "duplicate_group": "risk:duplicate-writes",
    }

    assert conversation_surface._ambient_candidate_id(first) != conversation_surface._ambient_candidate_id(second)


def test_ambient_payload_candidates_prefilter_fact_flood_before_rendering(monkeypatch) -> None:
    calls = 0

    def fake_render_ambient_signal(*, moment, facts, markdown, seed):
        nonlocal calls
        calls += 1
        detail = facts[0]["detail"]
        prefix = "**Odylith Risks:**" if markdown else "Odylith Risks:"
        return "risks", f"{prefix} {detail}"

    monkeypatch.setattr(conversation_surface.voice, "render_ambient_signal", fake_render_ambient_signal)
    observation = conversation_surface.ObservationEnvelope.from_mapping(
        surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id="ambient-prefilter",
            prompt_excerpt="Do not let candidate floods spend hot-path latency.",
        )
    )
    intervention = {
        "candidate": {
            "key": "ambient-prefilter",
            "stage": "teaser",
            "suppressed_reason": "",
            "moment": {"score": 92, "kind": "guardrail"},
        },
        "facts": [
                {
                    "kind": "invariant",
                    "headline": f"Hard invariant unique{index}",
                    "detail": f"risk detail unique{index}",
                    "priority": 96,
                    "refs": [],
                }
            for index in range(80)
        ],
    }

    payloads = conversation_surface._ambient_payload_candidates(
        observation=observation,
        intervention=intervention,
    )

    assert len(payloads) == 24
    assert calls == 24
    assert len({row["duplicate_group"] for row in payloads}) == 24


def test_render_live_text_dedupes_semantically_duplicate_ambient_signals() -> None:
    bundle = {
        "ambient_signals": {
            "selected_signal": "risks",
            "selected_signals": ["risks", "history"],
            "risks": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith Risks: preserve visible chat proof for CB-121 now.",
                "markdown_text": "**Odylith Risks:** preserve visible chat proof for CB-121 now.",
                "semantic_signature": ["preserve", "visible", "proof", "cb-121"],
            },
            "history": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith History: preserve visible chat proof for CB-121 now.",
                "markdown_text": "**Odylith History:** preserve visible chat proof for CB-121 now.",
                "semantic_signature": ["preserve", "visible", "proof", "cb-121"],
            },
        },
        "intervention_bundle": {
            "candidate": {"stage": "silent", "suppressed_reason": ""},
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
    }

    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )

    assert "**Odylith Risks:**" in rendered
    assert "**Odylith History:**" not in rendered


def test_append_intervention_events_records_same_label_distinct_ambient_signals(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    first = {
        "candidate_id": "ambient:risks:first",
        "eligible": True,
        "render_hint": "explicit_label",
        "plain_text": "Odylith Risks: hidden hook payloads are not visibility proof.",
        "markdown_text": "**Odylith Risks:** hidden hook payloads are not visibility proof.",
        "semantic_signature": ["hidden", "hooks", "visibility"],
    }
    second = {
        "candidate_id": "ambient:risks:second",
        "eligible": True,
        "render_hint": "explicit_label",
        "plain_text": "Odylith Risks: duplicate governance writes would corrupt release truth.",
        "markdown_text": "**Odylith Risks:** duplicate governance writes would corrupt release truth.",
        "semantic_signature": ["duplicate", "governance", "release"],
    }
    bundle = {
        "observation": {
            "host_family": "codex",
            "turn_phase": "post_bash_checkpoint",
            "session_id": "ambient-events-same-label",
            "changed_paths": [],
        },
        "ambient_signals": {
            "selected_signal": "risks",
            "selected_signals": ["risks", "risks"],
            "selected_signal_ids": ["ambient:risks:first", "ambient:risks:second"],
            "ambient_signal_payloads": {
                "ambient:risks:first": first,
                "ambient:risks:second": second,
            },
            "risks": first,
        },
        "intervention_bundle": {
            "candidate": {
                "key": "ambient-events-same-label",
                "stage": "silent",
                "moment": {"semantic_signature": ["ambient", "same-label"]},
                "suppressed_reason": "",
            },
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
    }

    events = conversation_surface.append_intervention_events(
        repo_root=tmp_path,
        bundle=bundle,
        include_proposal=False,
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    rows = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="ambient-events-same-label",
    )

    assert events == ["ambient_signal", "ambient_signal"]
    assert [row["display_markdown"] for row in rows] == [
        first["markdown_text"],
        second["markdown_text"],
    ]
    assert [row["semantic_signature"] for row in rows] == [
        first["semantic_signature"],
        second["semantic_signature"],
    ]
    assert [row["intervention_key"] for row in rows] == [
        "ambient:risks:first",
        "ambient:risks:second",
    ]
    confirmed = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="ambient-events-same-label",
        last_assistant_message=f"{first['markdown_text']}\n\n{second['markdown_text']}",
        render_surface="codex_status_probe",
    )

    assert {
        row["intervention_key"]
        for row in confirmed
    } == {"ambient:risks:first", "ambient:risks:second"}


def test_post_tool_teaser_emits_ambient_signal_event(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id="ambient-event-1",
            prompt_excerpt="Keep the governance record visible.",
        ),
    )

    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )
    events = conversation_surface.append_intervention_events(
        repo_root=tmp_path,
        bundle=bundle,
        include_proposal=False,
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    rows = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="ambient-event-1",
    )

    assert bundle["ambient_signals"]["selected_signal"] == "insight"
    assert rendered.startswith("---\n\n**Odylith Insight:**")
    assert "ambient_signal" in events
    assert "intervention_teaser" not in events
    ambient_rows = [row for row in rows if row["kind"] == "ambient_signal"]
    assert len(ambient_rows) == 1
    selected_id = bundle["ambient_signals"]["selected_signal_ids"][0]
    assert ambient_rows[0]["intervention_key"] == selected_id
    assert (
        ambient_rows[0]["semantic_signature"]
        == bundle["ambient_signals"]["ambient_signal_payloads"][selected_id]["semantic_signature"]
    )
    metadata = ambient_rows[0]["metadata"]
    assert metadata["value_engine_version"] == "intervention-value-engine.v1"
    assert metadata["event_candidate_id"] == selected_id
    assert metadata["visibility_proof"]["delivery_status"] == "assistant_fallback_ready"
    assert metadata["value_decision"]["selected"][0]["candidate_id"] == selected_id
    assert metadata["value_decision"]["selected"][0]["feature_vector"]["materiality"] > 0.0
    assert metadata["value_decision"]["selected"][0]["evidence_fingerprints"]


def test_high_strength_risk_and_history_stack_with_observation(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id="ambient-stack-1",
            prompt_excerpt=(
                "CB-121 is a regression and this must never hide visible chat output again. "
                "Keep B-096 governed and accurate."
            ),
            packet_summary={"workstreams": ["B-096"], "bugs": ["CB-121"]},
        ),
    )

    rendered = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=True,
    )

    assert bundle["intervention_bundle"]["candidate"]["stage"] == "card"
    assert bundle["ambient_signals"]["selected_signals"] == ["history"]
    assert bundle["ambient_signals"]["risks"]["suppressed_reason"] == "duplicate_visible_proposition"
    assert rendered.startswith("---\n\n**Odylith History:**")
    assert "**Odylith Risks:**" not in rendered
    assert "\n\n**Odylith History:**" in rendered
    assert "\n\n**Odylith Observation:**" in rendered
    assert rendered.endswith("\n\n---")


def test_append_intervention_events_records_each_distinct_ambient_signal(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = {
        "observation": {
            "host_family": "codex",
            "turn_phase": "post_bash_checkpoint",
            "session_id": "ambient-events-stack-1",
            "changed_paths": [],
        },
        "ambient_signals": {
            "selected_signal": "risks",
            "selected_signals": ["risks", "history", "insight"],
            "risks": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith Risks: a hard invariant is active before implementation proceeds.",
                "markdown_text": "**Odylith Risks:** a hard invariant is active before implementation proceeds.",
                "semantic_signature": ["hard", "invariant", "implementation"],
            },
            "history": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith History: CB-121 already records this failure mode.",
                "markdown_text": "**Odylith History:** CB-121 already records this failure mode.",
                "semantic_signature": ["cb-121", "failure", "mode"],
            },
            "insight": {
                "eligible": True,
                "render_hint": "explicit_label",
                "plain_text": "Odylith Insight: B-096 owns the next governed move.",
                "markdown_text": "**Odylith Insight:** B-096 owns the next governed move.",
                "semantic_signature": ["b-096", "governed", "move"],
            },
        },
        "intervention_bundle": {
            "candidate": {
                "key": "ambient-events-stack",
                "stage": "teaser",
                "moment": {"semantic_signature": ["ambient", "events"]},
                "suppressed_reason": "",
                "teaser_text": "Odylith can already see governed truth taking shape here.",
            },
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
    }

    events = conversation_surface.append_intervention_events(
        repo_root=tmp_path,
        bundle=bundle,
        include_proposal=False,
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    rows = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="ambient-events-stack-1",
    )

    assert events == ["ambient_signal", "ambient_signal", "ambient_signal"]
    assert [row["display_markdown"] for row in rows] == [
        "**Odylith Risks:** a hard invariant is active before implementation proceeds.",
        "**Odylith History:** CB-121 already records this failure mode.",
        "**Odylith Insight:** B-096 owns the next governed move.",
    ]


def test_hidden_duplicate_teaser_can_recover_as_ambient_signal(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    observation = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="ambient-hidden-duplicate-1",
        prompt_excerpt="Keep the governance record visible.",
    )
    first = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=observation,
    )
    candidate = first["intervention_bundle"]["candidate"]
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Hidden teaser was computed.",
        session_id="ambient-hidden-duplicate-1",
        host_family="codex",
        intervention_key=candidate["key"],
        turn_phase="post_bash_checkpoint",
        semantic_signature=candidate["moment"]["semantic_signature"],
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    second = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=observation,
    )
    rendered = conversation_surface.render_live_text(
        second,
        markdown=True,
        include_proposal=False,
    )

    assert second["intervention_bundle"]["candidate"]["suppressed_reason"] == "duplicate_teaser"
    assert second["ambient_signals"]["selected_signal"] == "insight"
    assert rendered.startswith("---\n\n**Odylith Insight:**")


def test_visible_duplicate_teaser_still_suppresses_ambient_signal(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    observation = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="ambient-visible-duplicate-1",
        prompt_excerpt="Keep the governance record visible.",
    )
    first = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=observation,
    )
    candidate = first["intervention_bundle"]["candidate"]
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Visible teaser was printed.",
        session_id="ambient-visible-duplicate-1",
        host_family="codex",
        intervention_key=candidate["key"],
        turn_phase="post_bash_checkpoint",
        semantic_signature=candidate["moment"]["semantic_signature"],
        delivery_channel="stdout_teaser",
        delivery_status="best_effort_visible",
    )

    second = conversation_surface.build_conversation_bundle(
        repo_root=tmp_path,
        observation=observation,
    )

    assert second["intervention_bundle"]["candidate"]["suppressed_reason"] == "duplicate_teaser"
    assert second["ambient_signals"]["selected_signal"] == ""


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

    assert rendered.startswith("---\n\n**Odylith Observation:** ")
    assert "\n\n-----\nOdylith Proposal: " in rendered
    assert rendered.endswith("\n---")
    events = conversation_surface.append_intervention_events(
        repo_root=tmp_path,
        bundle=bundle,
        include_proposal=True,
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface="claude_post_edit_checkpoint",
    )
    rows = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="surface-2",
    )

    assert events == ["intervention_card", "capture_proposed"]
    assert [row["kind"] for row in rows] == ["intervention_card", "capture_proposed"]
    for row in rows:
        metadata = row["metadata"]
        assert metadata["value_engine_version"] == "intervention-value-engine.v1"
        assert metadata["visibility_proof"]["delivery_status"] == "assistant_render_required"
        assert {
            selected["label"]
            for selected in metadata["value_decision"]["selected"]
        } >= {"observation", "proposal"}


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

    assert rendered.startswith("---\n\n**Odylith Observation:** The signal is real.")
    assert "Odylith Proposal:" in rendered
    assert rendered.endswith("\n---")


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
