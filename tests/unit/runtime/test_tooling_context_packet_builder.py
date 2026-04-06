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
