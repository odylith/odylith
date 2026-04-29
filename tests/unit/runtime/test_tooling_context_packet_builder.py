import json
from pathlib import Path

from odylith.runtime.context_engine import tooling_context_packet_builder as builder
from odylith.runtime.context_engine import tooling_context_packet_compaction as compaction
from odylith.runtime.context_engine import tooling_context_packet_completion as completion
from odylith.runtime.context_engine import tooling_context_packet_context_views as context_views
from odylith.runtime.context_engine import tooling_context_packet_finalization as finalization
from odylith.runtime.context_engine import tooling_context_packet_preflight as preflight
from odylith.runtime.context_engine import tooling_context_packet_profile as packet_profile
from odylith.runtime.governance import validate_guidance_behavior


def _write_guidance_behavior_corpus(root: Path) -> None:
    corpus_path = root / validate_guidance_behavior.CORPUS_RELATIVE_PATH
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(
        json.dumps(
            {
                "version": validate_guidance_behavior.EXPECTED_CORPUS_VERSION,
                "contract": validate_guidance_behavior.CONTRACT,
                "family": "guidance_behavior",
                "cases": [
                    {
                        "id": "guidance-runtime-fixture",
                        "family": "guidance_behavior",
                        "prompt": "Keep guidance behavior evidence connected.",
                        "expected_behavior": ["Retain compact runtime evidence."],
                        "forbidden_behavior": ["Do not require a broad scan."],
                        "required_evidence": ["The validator command is present."],
                        "related_guidance_refs": ["AGENTS.md"],
                        "severity": "high",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_packet_finalization_metadata_has_a_dedicated_owner() -> None:
    builder_source = Path(builder.__file__).read_text(encoding="utf-8")
    completion_source = Path(completion.__file__).read_text(encoding="utf-8")
    finalization_source = Path(finalization.__file__).read_text(encoding="utf-8")

    assert "def _finalize_packet_metadata" not in builder_source
    assert "def _prune_hot_path_finalize_base_payload" not in builder_source
    assert "packet_completion.complete_packet" in builder_source
    assert "packet_finalization.finalize_packet_metadata" in completion_source
    assert "def finalize_packet_metadata" in finalization_source
    assert "def prune_hot_path_finalize_base_payload" in finalization_source


def test_packet_adaptive_profile_has_a_dedicated_owner() -> None:
    builder_source = Path(builder.__file__).read_text(encoding="utf-8")
    completion_source = Path(completion.__file__).read_text(encoding="utf-8")
    profile_source = Path(packet_profile.__file__).read_text(encoding="utf-8")

    assert "def _adaptive_packet_profile" not in builder_source
    assert "def _reorder_trim_paths" not in builder_source
    assert "packet_profile.adaptive_packet_profile" in completion_source
    assert "def adaptive_packet_profile" in profile_source
    assert "def reorder_trim_paths" in profile_source


def test_packet_compaction_has_a_dedicated_owner() -> None:
    builder_source = Path(builder.__file__).read_text(encoding="utf-8")
    completion_source = Path(completion.__file__).read_text(encoding="utf-8")
    compaction_source = Path(compaction.__file__).read_text(encoding="utf-8")

    assert "def _compact_finalize_metadata" not in builder_source
    assert "def _merge_guidance_rows" not in builder_source
    assert "packet_compaction.compact_finalize_metadata" in completion_source
    assert "def compact_finalize_metadata" in compaction_source
    assert "def merge_guidance_rows" in compaction_source


def test_packet_preflight_and_enrichment_have_a_dedicated_owner() -> None:
    builder_source = Path(builder.__file__).read_text(encoding="utf-8")
    preflight_source = Path(preflight.__file__).read_text(encoding="utf-8")

    assert "guidance_behavior_runtime.summary_for_packet" not in builder_source
    assert "discipline_runtime.summary_for_packet" not in builder_source
    assert "packet_preflight.build_packet_preflight" in builder_source
    assert "packet_preflight.enrich_packet_payload" in builder_source
    assert "def build_packet_preflight" in preflight_source
    assert "def enrich_packet_payload" in preflight_source


def test_packet_context_view_refresh_has_a_dedicated_owner() -> None:
    builder_source = Path(builder.__file__).read_text(encoding="utf-8")
    completion_source = Path(completion.__file__).read_text(encoding="utf-8")
    context_view_source = Path(context_views.__file__).read_text(encoding="utf-8")

    assert "def _refresh_context_views" not in builder_source
    assert "def _retained_guidance" not in builder_source
    assert "packet_context_views.refresh_context_views" in completion_source
    assert "def refresh_context_views" in context_view_source
    assert "def reuse_hot_path_context_views" in context_view_source


def test_packet_completion_cycle_has_a_dedicated_owner() -> None:
    builder_source = Path(builder.__file__).read_text(encoding="utf-8")
    completion_source = Path(completion.__file__).read_text(encoding="utf-8")

    assert "budgeting.apply_packet_budget" not in builder_source
    assert "packet_finalization.sync_packet_budget_truncation" not in builder_source
    assert "def _stabilize_completed_packet" in completion_source
    assert "def _stamp_within_budget_truth" in completion_source


def test_packet_compaction_filters_malformed_rows_and_merges_guidance_details() -> None:
    assert compaction.mapping_rows([{"path": "ok"}, "bad-row", ["not", "a-mapping"]]) == [{"path": "ok"}]

    merged = compaction.merge_guidance_rows(
        [
            {
                "chunk_id": "guidance-1",
                "title": "",
                "signals": ["primary-signal"],
                "actionability": {},
            },
            {"chunk_id": "guidance-1", "title": "duplicate ignored"},
            {"title": "missing id ignored"},
        ],
        detail_rows=[
            {
                "chunk_id": "guidance-1",
                "title": "Grounded Context Guidance",
                "canonical_source": "AGENTS.md",
                "actionability": {"read_path": "AGENTS.md", "signals": ["detail-signal"]},
                "evidence_summary": {"score": 4},
            }
        ],
    )

    assert len(merged) == 1
    assert merged[0]["title"] == "Grounded Context Guidance"
    assert merged[0]["canonical_source"] == "AGENTS.md"
    assert merged[0]["actionability"]["read_path"] == "AGENTS.md"
    assert merged[0]["evidence_summary"]["score"] == 4


def test_gated_bootstrap_retrieval_plan_compaction_keeps_only_operator_critical_context() -> None:
    compact = compaction.compact_finalize_retrieval_plan(
        {
            "packet_kind": "bootstrap_session",
            "packet_state": "gated_ambiguous",
            "anchor_quality": "explicit",
            "guidance_coverage": "direct",
            "evidence_consensus": "mixed",
            "ambiguity_class": "selection_ambiguous",
            "precision_score": 44,
            "routing_confidence": "low",
            "selected_guidance_chunks": [
                {
                    "chunk_id": "g1",
                    "title": "First",
                    "match_tier": "direct_path",
                    "canonical_source": "AGENTS.md",
                    "signals": ["one", "two", "three", "four"],
                    "actionability": {"read_path": "AGENTS.md", "signals": ["a", "b", "c", "d"]},
                    "evidence_summary": {"score": 7},
                    "summary": "drop in gated bootstrap",
                },
                {"chunk_id": "g2", "title": "Second"},
            ],
            "selected_docs": ["doc-a", "doc-b"],
            "selected_commands": ["cmd-a", "cmd-b"],
            "selected_tests": [{"path": "test_a.py"}, {"path": "test_b.py"}],
            "selected_domains": ["runtime", "governance", "surfaces"],
            "anchor_paths": ["src/a.py", "src/b.py", "src/c.py"],
            "explicit_paths": ["ignored-a", "ignored-b"],
            "shared_anchor_paths": ["ignored-shared"],
            "evidence_profile": {"score": 99},
            "actionability_profile": {"score": 99},
            "noise": "drop",
        },
        packet_kind="bootstrap_session",
        packet_state="gated_ambiguous",
    )

    assert compact["selected_domains"] == ["runtime", "governance"]
    assert compact["anchor_paths"] == ["src/a.py", "src/b.py"]
    assert compact["selected_guidance_chunks"] == [
        {
            "chunk_id": "g1",
            "title": "First",
            "match_tier": "direct_path",
            "score": 7,
            "read_path": "AGENTS.md",
            "canonical_source": "AGENTS.md",
            "signals": ["a", "b", "c"],
        }
    ]
    assert "selected_docs" not in compact
    assert "selected_commands" not in compact
    assert "selected_tests" not in compact
    assert "noise" not in compact
    assert "evidence_profile" not in compact


def test_hot_path_pruning_respects_internal_context_escape_hatch() -> None:
    payload = {
        "_retain_hot_path_internal_context": True,
        "working_memory_tiers": {"warm": {"guidance_chunks": [{"chunk_id": "keep"}]}},
        "unexpected_debug_payload": {"kept": True},
    }

    assert finalization.prune_hot_path_finalize_base_payload(
        packet_kind="governance_slice",
        packet_state="gated_ambiguous",
        base_payload=payload,
    ) == payload


def test_sync_packet_budget_truncation_preserves_retry_metadata_and_updates_truth() -> None:
    synced = finalization.sync_packet_budget_truncation(
        {"truncation": {"packet_budget": {"retry_index": 2, "steps": ["trim-docs"]}}},
        packet_metrics={
            "within_budget": False,
            "estimated_bytes": 2048,
            "estimated_tokens": 512,
            "max_bytes": 1024,
            "max_tokens": 256,
        },
    )

    assert synced["truncation"]["packet_budget"] == {
        "retry_index": 2,
        "steps": ["trim-docs"],
        "within_budget": False,
        "estimated_bytes": 2048,
        "estimated_tokens": 512,
        "max_bytes": 1024,
        "max_tokens": 256,
    }


def test_adaptive_packet_profile_distinguishes_grounded_density_from_conflicted_precision() -> None:
    dense = packet_profile.adaptive_packet_profile(
        packet_kind="governance_slice",
        packet_state="expanded",
        selection_state="explicit",
        retrieval_plan={
            "precision_score": 82,
            "routing_confidence": "high",
            "ambiguity_class": "none",
            "evidence_consensus": "strong",
            "anchor_quality": "explicit",
            "guidance_coverage": "direct",
        },
        optimization_snapshot={
            "control_advisories": {
                "confidence": {"score": 3},
                "evidence_strength": {"score": 3, "sample_balance": "balanced"},
                "freshness": {"bucket": "fresh"},
            }
        },
        full_scan_recommended=False,
    )
    conflicted = packet_profile.adaptive_packet_profile(
        packet_kind="governance_slice",
        packet_state="gated_ambiguous",
        selection_state="ambiguous",
        retrieval_plan={
            "precision_score": 41,
            "routing_confidence": "low",
            "ambiguity_class": "historical_fanout",
            "evidence_consensus": "weak",
            "anchor_quality": "shared",
            "guidance_coverage": "thin",
        },
        optimization_snapshot={
            "control_advisories": {
                "confidence": {"score": 3},
                "evidence_strength": {"score": 3, "sample_balance": "balanced", "signal_conflict": True},
                "freshness": {"bucket": "fresh"},
            }
        },
        full_scan_recommended=True,
    )

    assert dense["reliability"] == "reliable"
    assert dense["packet_strategy"] == "density_first"
    assert dense["budget_mode"] == "spend_when_grounded"
    assert dense["speed_mode"] == "accelerate_grounded"
    assert conflicted["reliability"] == "guarded"
    assert conflicted["packet_strategy"] == "precision_first"
    assert conflicted["retrieval_focus"] == "precision_repair"
    assert conflicted["speed_mode"] == "conserve"
    assert conflicted["budget_scale"] == 0.96


def test_packet_preflight_escalates_gated_packet_when_validator_is_grounded(monkeypatch, tmp_path: Path) -> None:
    plan_states: list[str] = []

    monkeypatch.setattr(
        preflight.guidance_behavior_runtime,
        "summary_for_packet",
        lambda **_: {"status": "available"},
    )
    monkeypatch.setattr(
        preflight.guidance_behavior_runtime,
        "commands_with_validator",
        lambda commands, _summary, **_: [*commands, "odylith validate guidance-behavior --repo-root ."],
    )
    monkeypatch.setattr(preflight.discipline_runtime, "summary_for_packet", lambda **_: {})
    monkeypatch.setattr(preflight.discipline_runtime, "commands_with_validator", lambda commands, _summary, **_: commands)
    monkeypatch.setattr(preflight.tooling_guidance_catalog, "compact_catalog_summary", lambda _catalog: {"version": "test"})
    monkeypatch.setattr(
        preflight.retrieval,
        "compact_retrieval_bundle",
        lambda **_: {
            "selected_guidance_chunks": [
                {"chunk_id": "g1", "match_tier": "direct_path", "actionability": {"actionable": True}}
            ],
            "guidance_brief": [],
        },
    )

    def _build_plan(**kwargs):
        plan_states.append(kwargs["packet_state"])
        return {
            "anchor_quality": "shared",
            "guidance_coverage": "thin",
            "ambiguity_class": "selection_ambiguous",
            "evidence_consensus": "mixed",
            "precision_score": 55,
        }

    monkeypatch.setattr(preflight.routing, "build_retrieval_plan", _build_plan)
    monkeypatch.setattr(preflight.routing, "grounded_ambiguous_write_candidate", lambda **_: False)

    packet_preflight = preflight.build_packet_preflight(
        repo_root=tmp_path,
        packet_kind="governance_slice",
        packet_state="gated_ambiguous",
        changed_paths=("src/odylith/runtime/context_engine/tooling_context_packet_builder.py",),
        explicit_paths=(),
        shared_only_input=False,
        selection_state="ambiguous",
        workstream_selection={},
        candidate_workstreams=[],
        components=[],
        diagrams=[],
        docs=[],
        recommended_commands=[],
        recommended_tests=[],
        engineering_notes={},
        miss_recovery={},
        full_scan_recommended=True,
        full_scan_reason="selection_ambiguous",
        session_id="",
        family_hint="guidance_behavior",
        guidance_catalog={},
        optimization_snapshot={},
        delivery_profile="full",
    )

    assert plan_states == ["gated_ambiguous", "expanded"]
    assert packet_preflight.packet_state == "expanded"
    assert packet_preflight.full_scan_recommended is False
    assert packet_preflight.full_scan_reason == ""
    assert packet_preflight.effective_recommended_commands == ("odylith validate guidance-behavior --repo-root .",)


def test_packet_enrichment_prioritizes_payload_docs_and_carries_narrowing(monkeypatch) -> None:
    monkeypatch.setattr(preflight.guidance_behavior_runtime, "commands_with_validator", lambda commands, _summary, **_: commands)
    monkeypatch.setattr(preflight.discipline_runtime, "commands_with_validator", lambda commands, _summary, **_: commands)
    monkeypatch.setattr(preflight.retrieval, "prioritize_docs", lambda docs, **_: [*docs[::-1]])
    monkeypatch.setattr(preflight.retrieval, "prioritize_bootstrap_docs", lambda docs, **_: ["bootstrap", *docs[:1]])
    monkeypatch.setattr(
        preflight.routing,
        "build_narrowing_guidance",
        lambda **kwargs: {"required": kwargs["full_scan_recommended"], "state": kwargs["packet_state"]},
    )

    packet_preflight = preflight.PacketPreflight(
        packet_state="gated_ambiguous",
        full_scan_recommended=True,
        full_scan_reason="selection_ambiguous",
        source_recommended_commands=("pytest tests/unit/runtime/test_tooling_context_packet_builder.py",),
        recommended_commands=("pytest tests/unit/runtime/test_tooling_context_packet_builder.py",),
        effective_recommended_commands=("pytest tests/unit/runtime/test_tooling_context_packet_builder.py",),
        guidance_behavior_summary={"status": "available"},
        discipline_summary={},
        catalog={},
        guidance_catalog_summary={},
        retrieval_bundle={
            "prioritized_docs": ["docs/first.md", "docs/second.md"],
            "selected_guidance_chunks": [{"chunk_id": "g1"}],
            "guidance_brief": [{"chunk_id": "g1", "title": "Guidance"}],
            "working_memory_tiers": {"warm": {"guidance_chunks": [{"chunk_id": "g1"}]}},
        },
        selected_guidance_chunks=[{"chunk_id": "g1"}],
        selected_workstreams=[],
        retrieval_plan={"miss_recovery": {"queries": ["context"]}},
        optimization={},
        adaptive_packet_profile={"packet_strategy": "precision_first"},
    )

    enriched = preflight.enrich_packet_payload(
        packet_kind="bootstrap_session",
        payload={
            "docs": ["old-a.md", "old-b.md"],
            "relevant_docs": ["rel-a.md", "rel-b.md"],
            "impact": {"docs": ["impact-a.md", "impact-b.md"]},
        },
        changed_paths=("src/odylith/runtime/context_engine/tooling_context_packet_builder.py",),
        components=[],
        workstream_selection={},
        candidate_workstreams=[],
        diagrams=[],
        miss_recovery={"active": True},
        delivery_profile="full",
        preflight=packet_preflight,
        proof_state_payload={"proof_state_resolution": {"state": "none", "lane_ids": []}},
    )

    assert enriched["docs"] == ["docs/first.md", "docs/second.md"]
    assert enriched["relevant_docs"] == ["bootstrap", "rel-a.md"]
    assert enriched["impact"]["docs"] == ["bootstrap", "impact-a.md"]
    assert enriched["impact"]["guidance_brief"] == [{"chunk_id": "g1", "title": "Guidance"}]
    assert enriched["narrowing_guidance"] == {"required": True, "state": "gated_ambiguous"}
    assert enriched["working_memory_tiers"] == {"warm": {"guidance_chunks": [{"chunk_id": "g1"}]}}
    assert enriched["proof_state_resolution"] == {"state": "none", "lane_ids": []}


def test_refresh_context_views_uses_repo_root_for_working_memory_tiers(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(context_views.routing, "build_retrieval_plan", lambda **kwargs: {})
    monkeypatch.setattr(context_views.retrieval, "compact_guidance_brief", lambda *args, **kwargs: [])
    monkeypatch.setattr(context_views.routing, "build_narrowing_guidance", lambda **kwargs: {})

    seen: dict[str, Path] = {}

    def _fake_build_working_memory_tiers(**kwargs):
        seen["repo_root"] = Path(kwargs["repo_root"])
        return {"warm": {"guidance_chunks": []}}

    monkeypatch.setattr(context_views.retrieval, "build_working_memory_tiers", _fake_build_working_memory_tiers)

    payload, retrieval_plan = context_views.refresh_context_views(
        repo_root=tmp_path,
        packet_kind="governance_slice",
        packet_state="grounded",
        payload={},
        changed_paths=("agents-guidelines/WORKFLOW.md",),
        explicit_paths=(),
        shared_only_input=False,
        selection_state="grounded",
        workstream_selection={},
        candidate_workstreams=[],
        components=[],
        diagrams=[],
        docs=[],
        recommended_commands=[],
        recommended_tests=[],
        fallback_guidance_chunks=[],
        miss_recovery={},
        guidance_catalog_summary={},
        full_scan_recommended=False,
        full_scan_reason="",
        session_id="",
        build_working_memory_tiers=True,
    )

    assert seen["repo_root"] == tmp_path
    assert payload["working_memory_tiers"] == {"warm": {"guidance_chunks": []}}
    assert retrieval_plan == {}


def test_packet_proof_state_resolves_from_delivery_scopes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        builder.delivery_intelligence_engine,
        "load_delivery_intelligence_artifact",
        lambda **_: {
            "scopes": [
                {
                    "scope_key": "workstream:B-062",
                    "proof_state": {
                        "lane_id": "proof-state-control-plane",
                        "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                        "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                        "frontier_phase": "manifests-deploy",
                        "proof_status": "fixed_in_code",
                    },
                    "claim_guard": {
                        "highest_truthful_claim": "fixed in code",
                        "blocked_terms": ["fixed", "cleared", "resolved"],
                    },
                }
            ],
            "indexes": {"workstreams": {"B-062": "workstream:B-062"}},
        },
    )

    resolved = builder._packet_proof_state(  # noqa: SLF001
        repo_root=tmp_path,
        workstream_selection={"selected_workstream": {"entity_id": "B-062"}},
        candidate_workstreams=[],
        components=[],
        diagrams=[],
    )

    assert resolved["proof_state"]["lane_id"] == "proof-state-control-plane"
    assert resolved["claim_guard"]["highest_truthful_claim"] == "fixed in code"
    assert resolved["proof_state_resolution"] == {
        "state": "resolved",
        "lane_ids": ["proof-state-control-plane"],
    }


def test_packet_proof_state_avoids_delivery_artifact_when_no_anchor_exists(monkeypatch, tmp_path: Path) -> None:
    def _unexpected_delivery_artifact_load(**_kwargs):  # noqa: ANN003
        raise AssertionError("unanchored packets should not load delivery intelligence")

    monkeypatch.setattr(
        builder.delivery_intelligence_engine,
        "load_delivery_intelligence_artifact",
        _unexpected_delivery_artifact_load,
    )

    resolved = builder._packet_proof_state(  # noqa: SLF001
        repo_root=tmp_path,
        workstream_selection={},
        candidate_workstreams=[],
        components=[],
        diagrams=[],
    )

    assert resolved == {"proof_state_resolution": {"state": "none", "lane_ids": []}}


def test_packet_proof_state_preserves_ambiguous_resolution(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        builder.delivery_intelligence_engine,
        "load_delivery_intelligence_artifact",
        lambda **_: {
            "scopes": [
                {
                    "scope_key": "workstream:B-062",
                    "proof_state_resolution": {
                        "state": "ambiguous",
                        "lane_ids": ["lane-a", "lane-b"],
                    },
                }
            ],
            "indexes": {"workstreams": {"B-062": "workstream:B-062"}},
        },
    )

    resolved = builder._packet_proof_state(  # noqa: SLF001
        repo_root=tmp_path,
        workstream_selection={"selected_workstream": {"entity_id": "B-062"}},
        candidate_workstreams=[],
        components=[],
        diagrams=[],
    )

    assert resolved == {
        "proof_state_resolution": {
            "state": "ambiguous",
            "lane_ids": ["lane-a", "lane-b"],
        }
    }


def test_finalize_packet_carries_guidance_behavior_runtime_summary(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    _write_guidance_behavior_corpus(tmp_path)
    monkeypatch.setattr(builder, "_odylith_switch_snapshot", lambda **_: {"enabled": True})

    packet = builder.finalize_packet(
        repo_root=tmp_path,
        packet_kind="governance_slice",
        payload={"changed_paths": ["src/odylith/runtime/governance/validate_guidance_behavior.py"]},
        packet_state="expanded",
        changed_paths=("src/odylith/runtime/governance/validate_guidance_behavior.py",),
        explicit_paths=(),
        shared_only_input=False,
        selection_state="grounded",
        workstream_selection={},
        candidate_workstreams=[],
        components=[],
        diagrams=[],
        docs=[],
        recommended_commands=[],
        recommended_tests=[],
        engineering_notes={},
        miss_recovery={},
        full_scan_recommended=False,
        full_scan_reason="",
        family_hint="guidance_behavior",
        delivery_profile="full",
    )

    assert packet["guidance_behavior_summary"]["status"] == "available"
    assert packet["guidance_behavior_summary"]["validation_status"] == "not_run"
    assert any("validate guidance-behavior" in command for command in packet["recommended_commands"])
    assert packet["context_packet"]["guidance_behavior_summary"]["case_count"] == 1
    assert packet["evidence_pack"]["guidance_behavior_summary"]["family"] == "guidance_behavior"
