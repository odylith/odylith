from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_packet_session_runtime as session_packet_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_registry_runtime as surface_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import turn_context_runtime

session_packet_runtime.bind(store.__dict__)
surface_runtime.bind(store.__dict__)


def _minimal_impact_report(**kwargs) -> dict[str, object]:  # noqa: ANN001
    changed_paths = list(kwargs.get("changed_paths", []))
    return {
        "changed_paths": changed_paths,
        "explicit_paths": changed_paths,
        "candidate_workstreams": [],
        "workstream_selection": {"state": "explicit", "reason": "exact slice"},
        "selection_state": "explicit",
        "selection_reason": "exact slice",
        "selection_confidence": "high",
        "context_packet_state": "compact",
        "components": [],
        "diagrams": [],
        "bugs": [],
        "docs": [],
        "recommended_commands": [],
        "recommended_tests": [],
        "engineering_notes": {},
        "miss_recovery": {},
        "truncation": {},
        "full_scan_recommended": False,
        "full_scan_reason": "",
        "fallback_scan": {},
    }


def test_consumer_lane_turn_intake_resolves_consumer_writable_targets_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(session_packet_runtime, "build_impact_report", _minimal_impact_report)
    monkeypatch.setattr(
        turn_context_runtime,
        "derive_lane_targeting",
        lambda repo_root: {
            "lane": "consumer",
            "repo_role": "consumer_repo",
            "write_policy": {
                "odylith_fix_mode": "feedback_only",
                "allow_odylith_mutations": False,
                "protected_roots": ["odylith", ".odylith"],
            },
        },
    )
    monkeypatch.setattr(
        turn_context_runtime,
        "_search_literal_matches",
        lambda **kwargs: [
            {
                "kind": "workstream",
                "entity_id": "B-073",
                "title": "Task Contract, Event Ledger, and Hard-Constraint Promotion",
                "path": "odylith/radar/source/ideas/2026-04/b-073.md",
            }
        ],
    )

    payload = session_packet_runtime.build_session_brief(
        repo_root=tmp_path,
        changed_paths=["src/app/release_card.tsx", "odylith/compass/compass.html"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="exact_path_ambiguity",
        generated_surfaces=["compass"],
        intent='Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
        visible_text=["Task Contract, Event Ledger, and Hard-Constraint Promotion"],
        active_tab="releases",
        user_turn_id="turn-2",
        supersedes_turn_id="turn-1",
    )

    assert payload["turn_context"] == {
        "intent": 'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
        "surfaces": ["compass", "releases"],
        "visible_text": ["Task Contract, Event Ledger, and Hard-Constraint Promotion"],
        "active_tab": "releases",
        "user_turn_id": "turn-2",
        "supersedes_turn_id": "turn-1",
    }
    assert payload["presentation_policy"] == {
        "commentary_mode": "task_first_minimal",
        "suppress_routing_receipts": True,
        "surface_fast_lane": True,
    }
    assert payload["target_resolution"]["lane"] == "consumer"
    assert any(
        row["path"] == "src/app/release_card.tsx" and row["writable"] is True
        for row in payload["target_resolution"]["candidate_targets"]
    )
    assert any(
        row["path"] == "odylith/compass/compass.html" and row["writable"] is False
        for row in payload["target_resolution"]["candidate_targets"]
    )
    assert any(row["value"] == "B-073" for row in payload["target_resolution"]["diagnostic_anchors"])


def test_dev_maintainer_lane_turn_intake_resolves_odylith_surface_targets(
    monkeypatch,
    tmp_path: Path,
) -> None:
    page = tmp_path / "src" / "odylith" / "runtime" / "surfaces" / "templates" / "compass_dashboard" / "page.html.j2"
    page.parent.mkdir(parents=True)
    page.write_text("<html></html>\n", encoding="utf-8")

    monkeypatch.setattr(session_packet_runtime, "build_impact_report", _minimal_impact_report)
    monkeypatch.setattr(
        turn_context_runtime,
        "derive_lane_targeting",
        lambda repo_root: {
            "lane": "dev_maintainer",
            "repo_role": "odylith_product_repo",
            "write_policy": {
                "odylith_fix_mode": "maintainer_authorized",
                "allow_odylith_mutations": True,
                "protected_roots": [],
            },
        },
    )
    monkeypatch.setattr(
        turn_context_runtime,
        "_search_literal_matches",
        lambda **kwargs: [
            {
                "kind": "release",
                "entity_id": "release-0-1-11",
                "title": "0.1.11",
                "path": "odylith/radar/source/releases/releases.v1.json",
            }
        ],
    )

    payload = session_packet_runtime.build_session_brief(
        repo_root=tmp_path,
        changed_paths=[],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="exact_path_ambiguity",
        generated_surfaces=["compass"],
        intent="Move the current release label next to 0.1.11 title",
        visible_text=["0.1.11"],
        active_tab="releases",
    )

    assert payload["target_resolution"]["lane"] == "dev_maintainer"
    assert any(
        row["path"] == "src/odylith/runtime/surfaces/templates/compass_dashboard/page.html.j2"
        and row["writable"] is True
        for row in payload["target_resolution"]["candidate_targets"]
    )
    assert any(row["value"] == "release-0-1-11" for row in payload["target_resolution"]["diagnostic_anchors"])
