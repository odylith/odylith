from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.intervention_engine import engine
from odylith.runtime.intervention_engine import stream_state
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
    (root / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "radar" / "traceability-graph.v1.json").write_text(
        json.dumps({"version": "v1", "workstreams": [], "warning_items": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "casebook" / "bugs").mkdir(parents=True, exist_ok=True)


def _seed_registry_component(root: Path, *, component_id: str, label: str, workstream_id: str) -> None:
    spec_path = root / "odylith" / "registry" / "source" / "components" / component_id / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        "\n".join(
            [
                f"# {label}",
                "",
                "## Feature History",
                (
                    f"- 2026-04-14: Seeded intervention duplicate-lookup proof for {label}. "
                    f"(Plan: [{workstream_id}](odylith/radar/radar.html?view=plan&workstream={workstream_id}))"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path = root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["components"] = [
        {
            "component_id": component_id,
            "name": label,
            "kind": "runtime",
            "qualification": "curated",
            "owner": "product",
            "status": "active",
            "what_it_is": f"{label} owned runtime boundary.",
            "why_tracked": f"{label} is already part of the governed runtime surface.",
            "aliases": [component_id],
            "path_prefixes": ["src/odylith/runtime"],
            "workstreams": [workstream_id],
            "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        }
    ]
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")


def _seed_workstream(root: Path, *, workstream_id: str, title: str) -> None:
    graph_path = root / "odylith" / "radar" / "traceability-graph.v1.json"
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["workstreams"] = [
        {
            "idea_id": workstream_id,
            "title": title,
        }
    ]
    graph_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _seed_bug(root: Path, *, bug_id: str, title: str) -> None:
    (root / "odylith" / "casebook" / "bugs" / f"{bug_id.lower()}.md").write_text(
        f"- Bug ID: {bug_id}\n- Description: {title}\n",
        encoding="utf-8",
    )


def _seed_diagram(root: Path, *, diagram_id: str, title: str, slug: str) -> None:
    source_path = root / "odylith" / "atlas" / "source" / f"{slug}.mmd"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("flowchart TD\n  A[Start] --> B[End]\n", encoding="utf-8")
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    payload["diagrams"] = [
        {
            "diagram_id": diagram_id,
            "title": title,
            "slug": slug,
            "source_mmd": source_path.relative_to(root).as_posix(),
            "change_watch_paths": ["src/odylith/runtime"],
        }
    ]
    catalog_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_prompt_only_bundle_stays_teaser_and_holds_voice_contract(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="prompt_submit",
            session_id="session-1",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow and human voice.",
        ),
    )

    assert bundle["candidate"]["stage"] == "teaser"
    assert bundle["candidate"]["teaser_text"].startswith("Odylith can already")
    assert bundle["candidate"]["teaser_text"].endswith("turn that into a proposal.")
    assert bundle["candidate"]["markdown_text"] == ""
    assert bundle["proposal"]["eligible"] is False
    assert bundle["render_policy"]["voice_contract"]["templated_or_mechanical_forbidden"] is True
    assert bundle["render_policy"]["voice_contract"]["voice_pack_ready"] is True


def test_changed_paths_and_prompt_upgrade_to_card_and_rendered_proposal(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id="session-2",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow and human voice.",
            changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
        ),
    )

    assert bundle["candidate"]["stage"] == "card"
    assert bundle["candidate"]["markdown_text"].startswith("**Odylith Observation:** ")
    assert bundle["candidate"]["moment"]["kind"] in {"capture", "continuation", "ownership", "boundary"}
    assert "\n\n**Why now**\n" not in bundle["candidate"]["markdown_text"]
    assert bundle["proposal"]["markdown_text"].startswith("-----\nOdylith Proposal: ")
    assert "Odylith Proposal:" in bundle["proposal"]["markdown_text"]
    assert "**What Odylith is proposing**" not in bundle["proposal"]["markdown_text"]
    assert "**Apply status**" not in bundle["proposal"]["markdown_text"]
    assert bundle["proposal"]["markdown_text"].rstrip().endswith("-----")
    assert 'To apply, say "apply this proposal".' in bundle["proposal"]["plain_text"]
    assert 'To apply, say "apply this proposal".' in bundle["proposal"]["markdown_text"]
    assert "Confirm:" not in bundle["proposal"]["markdown_text"]
    assert "\n- Radar:" in bundle["proposal"]["markdown_text"]
    assert "One clean governed bundle is ready to review" not in bundle["proposal"]["markdown_text"]


def test_cross_host_core_keeps_observation_and_proposal_content_consistent(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    base = {
        "turn_phase": "post_edit_checkpoint",
        "session_id": "session-3",
        "prompt_excerpt": "Design a conversation observation engine with governed proposal flow and human voice.",
        "changed_paths": ["src/odylith/runtime/intervention_engine/apply.py"],
    }

    codex_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation={"host_family": "codex", **base},
    )
    claude_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation={"host_family": "claude", **base},
    )

    assert codex_bundle["candidate"]["markdown_text"] == claude_bundle["candidate"]["markdown_text"]
    assert codex_bundle["proposal"]["markdown_text"] == claude_bundle["proposal"]["markdown_text"]
    assert [row["kind"] for row in codex_bundle["facts"]] == [row["kind"] for row in claude_bundle["facts"]]


def test_cross_lane_core_keeps_observation_and_proposal_content_consistent(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    base = {
        "host_family": "codex",
        "turn_phase": "post_bash_checkpoint",
        "session_id": "session-3b",
        "prompt_excerpt": "Design a conversation observation engine with governed proposal flow and human voice.",
        "changed_paths": ["src/odylith/runtime/intervention_engine/voice.py"],
    }

    consumer_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation={**base, "delivery_snapshot": {"lane": "consumer"}},
    )
    dogfood_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation={**base, "delivery_snapshot": {"lane": "pinned_dogfood"}},
    )
    dev_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation={**base, "delivery_snapshot": {"lane": "source_local"}},
    )

    assert consumer_bundle["candidate"]["markdown_text"] == dogfood_bundle["candidate"]["markdown_text"]
    assert consumer_bundle["candidate"]["markdown_text"] == dev_bundle["candidate"]["markdown_text"]
    assert consumer_bundle["proposal"]["markdown_text"] == dogfood_bundle["proposal"]["markdown_text"]
    assert consumer_bundle["proposal"]["markdown_text"] == dev_bundle["proposal"]["markdown_text"]


def test_render_blocks_requires_a_full_observation_before_showing_proposal(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="prompt_submit",
            session_id="session-4",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow and human voice.",
        ),
    )

    assert surface_runtime.render_blocks(bundle, markdown=True, include_proposal=True) == ""


def test_stop_summary_can_emit_observation_before_proposal_is_ready(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="stop_summary",
            session_id="session-observation-only",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow and human voice.",
            assistant_summary="The conversation is leaning into governance, topology, and owned boundaries.",
        ),
    )

    assert bundle["candidate"]["stage"] == "card"
    assert bundle["proposal"]["eligible"] is False
    assert surface_runtime.render_blocks(bundle, markdown=True, include_proposal=True).startswith(
        "**Odylith Observation:** "
    )


def test_no_signal_bundle_stays_silent_and_has_no_proposal_actions(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="session-no-signal",
            prompt_excerpt="Refactor helper names in main.py.",
            changed_paths=["src/main.py"],
        ),
    )

    assert bundle["candidate"]["stage"] == "silent"
    assert bundle["proposal"]["eligible"] is False
    assert bundle["proposal"]["actions"] == []
    assert surface_runtime.render_blocks(bundle, markdown=True, include_proposal=True) == ""


def test_no_signal_bundle_skips_repo_truth_lookup(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(
        engine,
        "_repo_truth",
        lambda repo_root: (_ for _ in ()).throw(AssertionError("repo truth should stay cold")),
    )

    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="prompt_submit",
            session_id="session-cold",
            prompt_excerpt="Refactor helper names in main.py.",
        ),
    )

    assert bundle["candidate"]["stage"] == "silent"
    assert bundle["proposal"]["eligible"] is False


def test_render_blocks_preserve_multiline_markdown_and_heading_order(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="session-4b",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow and human voice.",
            changed_paths=["src/odylith/runtime/intervention_engine/voice.py"],
        ),
    )

    rendered = surface_runtime.render_blocks(bundle, markdown=True, include_proposal=True)

    assert rendered.startswith("**Odylith Observation:** ")
    assert "\n\n**Why now**\n" not in rendered
    assert "\n\n-----\nOdylith Proposal: " in rendered
    assert rendered.count("-----") >= 2
    assert "\n- Radar:" in rendered


def test_append_bundle_events_preserve_rich_markdown_in_stream(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id="session-4c",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow and human voice.",
            changed_paths=["src/odylith/runtime/intervention_engine/surface_runtime.py"],
        ),
    )

    surface_runtime.append_bundle_events(repo_root=tmp_path, bundle=bundle, include_proposal=True)
    events = stream_state.load_recent_intervention_events(repo_root=tmp_path, session_id="session-4c")

    card = next(row for row in events if row["kind"] == "intervention_card")
    proposal = next(row for row in events if row["kind"] == "capture_proposed")

    assert card["display_markdown"].startswith("**Odylith Observation:** ")
    assert "\n\n**Why now**\n" not in card["display_markdown"]
    assert proposal["display_markdown"].startswith("-----\nOdylith Proposal: ")
    assert proposal["display_markdown"].count("-----") >= 2
    assert "\n- Radar:" in proposal["display_markdown"]
    assert proposal["prompt_excerpt"] == (
        "Design a conversation observation engine with governed proposal flow and human voice."
    )


def test_bundle_events_drive_pending_proposal_state_until_apply(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="session-5",
            prompt_excerpt="Design a conversation observation engine with governed proposal flow and human voice.",
            changed_paths=["src/odylith/runtime/intervention_engine/contract.py"],
        ),
    )

    kinds = surface_runtime.append_bundle_events(
        repo_root=tmp_path,
        bundle=bundle,
        include_proposal=True,
    )

    assert kinds == ["intervention_card", "capture_proposed"]
    pending = stream_state.pending_proposal_state(repo_root=tmp_path)
    assert pending["pending_count"] == 1
    assert pending["pending"][0]["confirmation_text"] == "apply this proposal"
    assert pending["pending"][0]["proposal_status"] == "pending"
    assert pending["pending"][0]["prompt_excerpt"] == (
        "Design a conversation observation engine with governed proposal flow and human voice."
    )
    assert pending["pending"][0]["moment_kind"] in {"capture", "boundary", "continuation", "ownership"}
    assert pending["pending"][0]["semantic_signature"]
    assert pending["pending"][0]["display_markdown"].startswith("-----\nOdylith Proposal: ")
    assert pending["pending"][0]["display_markdown"].count("-----") >= 2
    assert "Carry this forward as one Odylith Proposal" not in pending["pending"][0]["display_markdown"]
    assert "**What Odylith is proposing**" not in pending["pending"][0]["display_markdown"]

    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_applied",
        summary="Odylith Proposal applied.",
        session_id=bundle["observation"]["session_id"],
        host_family=bundle["observation"]["host_family"],
        intervention_key=bundle["proposal"]["key"],
        turn_phase=bundle["observation"]["turn_phase"],
        proposal_status="applied",
    )

    assert stream_state.pending_proposal_state(repo_root=tmp_path)["pending_count"] == 0


def test_session_memory_snapshot_tracks_recent_signatures_and_moment_kinds(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Teaser one.",
        session_id="session-memory",
        intervention_key="iv-one",
        turn_phase="prompt_submit",
        moment_kind="capture",
        semantic_signature=["capture", "boundary"],
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation one.",
        session_id="session-memory",
        intervention_key="iv-two",
        turn_phase="stop_summary",
        moment_kind="boundary",
        semantic_signature=["boundary", "atlas"],
    )

    snapshot = stream_state.session_memory_snapshot(
        repo_root=tmp_path,
        session_id="session-memory",
    )

    assert snapshot["recent_event_count"] == 2
    assert "capture|boundary" in snapshot["recent_signatures"]
    assert "capture|boundary" in snapshot["recent_teaser_signatures"]
    assert "boundary|atlas" in snapshot["recent_card_signatures"]
    assert snapshot["recent_moment_kinds"][:2] == ["boundary", "capture"]


def test_session_memory_snapshot_cache_invalidates_after_new_event(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Teaser one.",
        session_id="session-memory-refresh",
        intervention_key="iv-one",
        moment_kind="capture",
        semantic_signature=["token-one"],
    )
    first = stream_state.session_memory_snapshot(
        repo_root=tmp_path,
        session_id="session-memory-refresh",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Card one.",
        session_id="session-memory-refresh",
        intervention_key="iv-two",
        moment_kind="boundary",
        semantic_signature=["token-two"],
    )
    second = stream_state.session_memory_snapshot(
        repo_root=tmp_path,
        session_id="session-memory-refresh",
    )

    assert first["recent_event_count"] == 1
    assert second["recent_event_count"] == 2


def test_pending_proposal_state_cache_invalidates_after_terminal_event(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Previewing a governed proposal across Radar.",
        session_id="session-pending-refresh",
        intervention_key="iv-pending-refresh",
        proposal_status="pending",
        confirmation_text="apply this proposal",
        moment_kind="continuation",
        semantic_signature=["governed", "proposal"],
    )
    first = stream_state.pending_proposal_state(repo_root=tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_applied",
        summary="Applied governed proposal across Radar.",
        session_id="session-pending-refresh",
        intervention_key="iv-pending-refresh",
        proposal_status="applied",
        moment_kind="continuation",
        semantic_signature=["governed", "proposal"],
    )
    second = stream_state.pending_proposal_state(repo_root=tmp_path)

    assert first["pending_count"] == 1
    assert second["pending_count"] == 0


def test_recent_session_prompt_excerpt_tracks_human_prompt_not_intervention_summary(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Odylith Proposal pending.",
        session_id="session-prompt",
        intervention_key="iv-memory",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Proposal**",
    )

    assert (
        surface_runtime.recent_session_prompt_excerpt(
            repo_root=tmp_path,
            session_id="session-prompt",
        )
        == ""
    )


def test_prompt_submit_duplicate_teasers_are_suppressed_using_final_stage(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    observation = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="prompt_submit",
        session_id="session-6",
        prompt_excerpt="Design a governed proposal flow for B-321.",
        packet_summary={"workstreams": ["B-321"]},
    )

    first = engine.build_intervention_bundle(repo_root=tmp_path, observation=observation)
    kinds = surface_runtime.append_bundle_events(repo_root=tmp_path, bundle=first, include_proposal=True)
    second = engine.build_intervention_bundle(repo_root=tmp_path, observation=observation)

    assert kinds == ["intervention_teaser"]
    assert second["candidate"]["stage"] == "teaser"
    assert second["candidate"]["eligible"] is False
    assert second["candidate"]["suppressed_reason"] == "duplicate_teaser"


def test_same_moment_keeps_one_key_across_teaser_observation_and_proposal(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    base_prompt = "Design a governed proposal flow for B-321 with topology and human voice."
    prompt_observation = surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="prompt_submit",
        session_id="session-progression",
        prompt_excerpt=base_prompt,
        packet_summary={"workstreams": ["B-321"]},
    )

    teaser_bundle = engine.build_intervention_bundle(repo_root=tmp_path, observation=prompt_observation)
    surface_runtime.append_bundle_events(repo_root=tmp_path, bundle=teaser_bundle, include_proposal=False)

    stop_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="stop_summary",
            session_id="session-progression",
            prompt_excerpt=base_prompt,
            assistant_summary="The conversation is now making topology and governance-boundary claims for B-321.",
            packet_summary={"workstreams": ["B-321"]},
        ),
    )

    assert stop_bundle["candidate"]["key"] == teaser_bundle["candidate"]["key"]
    assert stop_bundle["candidate"]["stage"] == "card"
    assert stop_bundle["candidate"]["suppressed_reason"] == ""
    surface_runtime.append_bundle_events(repo_root=tmp_path, bundle=stop_bundle, include_proposal=False)

    proposal_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_edit_checkpoint",
            session_id="session-progression",
            prompt_excerpt=base_prompt,
            changed_paths=["src/odylith/runtime/intervention_engine/voice.py"],
            packet_summary={"workstreams": ["B-321"]},
        ),
    )

    assert proposal_bundle["candidate"]["key"] == teaser_bundle["candidate"]["key"]
    assert proposal_bundle["candidate"]["suppressed_reason"] == "duplicate_card"
    assert proposal_bundle["proposal"]["eligible"] is True
    rendered = surface_runtime.render_blocks(proposal_bundle, markdown=True, include_proposal=True)
    assert rendered.startswith("-----\nOdylith Proposal: ")
    assert "**Odylith Observation:**" not in rendered


def test_capture_proposed_event_uses_human_summary_instead_of_pending_placeholder(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="claude",
            turn_phase="post_edit_checkpoint",
            session_id="session-human-summary",
            prompt_excerpt="Map the topology and governance boundary for this runtime slice.",
            changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
        ),
    )

    events = surface_runtime.append_bundle_events(
        repo_root=tmp_path,
        bundle=bundle,
        include_proposal=True,
    )
    rows = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="session-human-summary",
    )
    proposed = [row for row in rows if row.get("kind") == "capture_proposed"]

    assert "capture_proposed" in events
    assert proposed
    assert proposed[-1]["summary"] != "Odylith Proposal pending."
    assert proposed[-1]["summary"].startswith("Previewing a governed proposal across")


def test_preview_only_proposal_keeps_status_centralized_and_drops_inline_boilerplate(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_edit_checkpoint",
            session_id="session-6b",
            prompt_excerpt="Map the topology and governance boundary for this runtime slice.",
            changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
        ),
    )

    proposal_markdown = bundle["proposal"]["markdown_text"]

    assert bundle["proposal"]["apply_supported"] is False
    assert proposal_markdown.startswith("-----\nOdylith Proposal: ")
    assert "It is staying in preview until every action has a safe apply lane." in proposal_markdown
    assert "safely appliable today" not in proposal_markdown
    assert proposal_markdown.count("-----") >= 2
    assert "One clean governed bundle is ready to review" not in proposal_markdown


def test_different_causal_points_get_distinct_keys_even_on_same_governed_slice(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    base = {
        "host_family": "claude",
        "turn_phase": "post_edit_checkpoint",
        "session_id": "session-7",
        "packet_summary": {"workstreams": ["B-777"]},
        "changed_paths": ["src/odylith/runtime/intervention_engine/engine.py"],
    }
    topology_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation={
            **base,
            "prompt_excerpt": "Map the topology and ownership boundary for B-777.",
        },
    )
    surface_runtime.append_bundle_events(repo_root=tmp_path, bundle=topology_bundle, include_proposal=True)
    memory_bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation={
            **base,
            "prompt_excerpt": "Capture the bug memory and regression history for B-777.",
        },
    )

    assert topology_bundle["candidate"]["key"] != memory_bundle["candidate"]["key"]
    assert memory_bundle["candidate"]["stage"] == "card"
    assert memory_bundle["candidate"]["suppressed_reason"] == ""


def test_duplicate_aware_lookup_prefers_existing_records_over_new_duplicates(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    title = "Runtime Boundary Drift Memory Bug"
    _seed_workstream(tmp_path, workstream_id="B-321", title=title)
    _seed_registry_component(
        tmp_path,
        component_id="runtime-boundary-drift-memory-bug",
        label=title,
        workstream_id="B-321",
    )
    _seed_diagram(tmp_path, diagram_id="D-321", title=f"{title} Topology", slug="runtime-boundary-drift-memory-bug")
    _seed_bug(tmp_path, bug_id="CB-321", title=title)

    bundle = engine.build_intervention_bundle(
        repo_root=tmp_path,
        observation=surface_runtime.observation_envelope(
            host_family="codex",
            turn_phase="post_edit_checkpoint",
            session_id="session-8",
            prompt_excerpt="Harden the runtime boundary drift memory bug with topology and governance clarity.",
            changed_paths=["src/odylith/runtime/intervention_engine/engine.py"],
        ),
    )

    actions = {(row["surface"], row["action"]): row for row in bundle["proposal"]["actions"]}

    assert actions[("radar", "update")]["target_id"] == "B-321"
    assert actions[("registry", "update")]["target_id"] == "runtime-boundary-drift-memory-bug"
    assert actions[("atlas", "review_refresh")]["target_id"] == "D-321"
    assert actions[("casebook", "reopen")]["target_id"] == "CB-321"
    assert bundle["proposal"]["apply_supported"] is False
