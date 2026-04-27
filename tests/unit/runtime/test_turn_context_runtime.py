from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import tooling_context_quality
from odylith.runtime.context_engine import turn_context_runtime


def test_turn_context_splits_operator_ask_from_quoted_literals() -> None:
    turn_context = turn_context_runtime.normalize_turn_context(
        intent='Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion" "policy" "execution surfaces"',
        surfaces=["Compass"],
        visible_text=["Task Contract, Event Ledger, and Hard-Constraint Promotion"],
        active_tab="Releases",
    )

    assert turn_context_runtime.operator_ask_text(turn_context) == "Move the current release label next to the title"
    assert turn_context_runtime.anchor_literals(turn_context) == [
        "Task Contract, Event Ledger, and Hard-Constraint Promotion",
        "policy",
        "execution surfaces",
    ]


def test_packet_quality_keeps_layout_turn_out_of_governance_family() -> None:
    turn_context = turn_context_runtime.normalize_turn_context(
        intent='Move the current release label next to the title "policy" "contract" "design" "execution surfaces"'
    )

    quality = tooling_context_quality.summarize_packet_quality(
        packet_kind="session_brief",
        packet_state="compact",
        selection_state="explicit",
        full_scan_recommended=False,
        retrieval_plan={},
        packet_metrics={"within_budget": True, "estimated_tokens": 128, "estimated_bytes": 512},
        final_payload={
            "turn_context": turn_context_runtime.compact_turn_context(turn_context),
            "changed_paths": ["src/app/release_card.tsx"],
        },
    )

    assert quality["intent_profile"]["family"] == "ui_layout"
    assert quality["intent_profile"]["mode"] == "write_execution"
    assert quality["intent_profile"]["critical_path"] == "implementation_first"


def test_resolve_turn_targets_marks_consumer_odylith_paths_diagnostic_only(monkeypatch, tmp_path: Path) -> None:
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
    monkeypatch.setattr(turn_context_runtime, "_search_literal_matches", lambda **kwargs: [])

    resolution = turn_context_runtime.resolve_turn_targets(
        repo_root=tmp_path,
        turn_context=turn_context_runtime.normalize_turn_context(
            intent="Why doesn't this admin panel take full width?",
            surfaces=["compass"],
        ),
        changed_paths=["src/app/admin_panel.tsx", "odylith/compass/compass.html"],
    )

    assert resolution["lane"] == "consumer"
    assert resolution["has_writable_targets"] is True
    assert any(row["path"] == "src/app/admin_panel.tsx" and row["writable"] is True for row in resolution["candidate_targets"])
    assert any(row["path"] == "odylith/compass/compass.html" and row["writable"] is False for row in resolution["candidate_targets"])


def test_resolve_turn_targets_allows_maintainer_surface_targets(monkeypatch, tmp_path: Path) -> None:
    page = tmp_path / "src" / "odylith" / "runtime" / "surfaces" / "templates" / "compass_dashboard" / "page.html.j2"
    page.parent.mkdir(parents=True)
    page.write_text("<html></html>\n", encoding="utf-8")

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
    monkeypatch.setattr(turn_context_runtime, "_search_literal_matches", lambda **kwargs: [])

    resolution = turn_context_runtime.resolve_turn_targets(
        repo_root=tmp_path,
        turn_context=turn_context_runtime.normalize_turn_context(
            intent="Move the current release label next to 0.1.11 title",
            surfaces=["compass"],
        ),
    )

    assert resolution["lane"] == "dev_maintainer"
    assert any(
        row["path"] == "src/odylith/runtime/surfaces/templates/compass_dashboard/page.html.j2"
        and row["writable"] is True
        for row in resolution["candidate_targets"]
    )


def test_resolve_turn_targets_preserves_consumer_failover_with_diagnostic_anchors(monkeypatch, tmp_path: Path) -> None:
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

    resolution = turn_context_runtime.resolve_turn_targets(
        repo_root=tmp_path,
        turn_context=turn_context_runtime.normalize_turn_context(
            intent='Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
            surfaces=["compass"],
            visible_text=["Task Contract, Event Ledger, and Hard-Constraint Promotion"],
        ),
    )

    assert resolution["candidate_targets"] == []
    assert resolution["diagnostic_anchors"][0]["value"] == "compass"
    assert any(row["value"] == "B-073" for row in resolution["diagnostic_anchors"])
    assert resolution["has_writable_targets"] is False
    assert resolution["requires_more_consumer_context"] is True
    assert resolution["consumer_failover"] == "maintainer_ready_feedback_plus_bounded_narrowing"
