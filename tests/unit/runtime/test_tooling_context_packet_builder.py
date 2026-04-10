from pathlib import Path

from odylith.runtime.context_engine import tooling_context_packet_builder as builder


def test_refresh_context_views_uses_repo_root_for_working_memory_tiers(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(builder.routing, "build_retrieval_plan", lambda **kwargs: {})
    monkeypatch.setattr(builder.retrieval, "compact_guidance_brief", lambda *args, **kwargs: [])
    monkeypatch.setattr(builder.routing, "build_narrowing_guidance", lambda **kwargs: {})

    seen: dict[str, Path] = {}

    def _fake_build_working_memory_tiers(**kwargs):
        seen["repo_root"] = Path(kwargs["repo_root"])
        return {"warm": {"guidance_chunks": []}}

    monkeypatch.setattr(builder.retrieval, "build_working_memory_tiers", _fake_build_working_memory_tiers)

    payload, retrieval_plan = builder._refresh_context_views(
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
