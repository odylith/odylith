from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import engine_integrity


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_engine_integrity_covers_operator_requested_engine_set() -> None:
    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)

    assert report["status"] == "pass"
    assert report["areas_checked"] == 15
    assert report["areas_present"] == 15
    assert report["command_backed_areas"] == 15
    assert report["anchor_backed_areas"] == 15
    assert report["activation_backed_areas"] == 15
    assert report["counts"]["error"] == 0
    areas = {row["area"]: row for row in report["areas"]}
    assert {
        "Context Engine",
        "Execution Engine",
        "Tribunal",
        "Intervention Engine",
        "Governance",
        "Subagent Orchestration",
        "Discipline",
        "Surface DAGs",
        "Delivery",
        "Analysis",
        "Memory Substrate",
        "Topology",
        "Taxonomies and FSMs",
        "Greenfield proposals and domain intelligence",
        "Overall UX",
    } == set(areas)
    for row in areas.values():
        assert row["command_backed"], row["area"]
        assert row["anchor_backed"], row["area"]
        assert row["activation_backed"], row["area"]
    assert "odylith greenfield create" in areas["Greenfield proposals and domain intelligence"]["commands"]
    assert areas["Subagent Orchestration"]["inventory_names"] == ["Subagent Router", "Subagent Orchestrator"]


def test_engine_integrity_text_report_is_operator_readable() -> None:
    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)
    text = engine_integrity._format_text(report)  # noqa: SLF001

    assert "Odylith engine integrity report" in text
    assert "- status: pass" in text
    assert "- activation_backed: 15" in text
    assert "all requested engine areas are inventory-backed" in text


def test_engine_integrity_rejects_command_only_activation(monkeypatch) -> None:
    payload = engine_integrity.capability_inventory.inventory_payload()
    for group in payload["engine_groups"]:
        for item in group["items"]:
            if item["name"] == "Discipline Engine":
                item["anchors"] = ()

    monkeypatch.setattr(engine_integrity.capability_inventory, "inventory_payload", lambda: payload)

    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)

    assert report["status"] == "fail"
    assert any(
        finding["area"] == "Discipline"
        and "no source anchor backing" in finding["message"]
        for finding in report["findings"]
    )


def test_engine_integrity_rejects_unknown_command_roots(monkeypatch) -> None:
    payload = engine_integrity.capability_inventory.inventory_payload()
    for group in payload["engine_groups"]:
        for item in group["items"]:
            if item["name"] == "Context Engine":
                item["commands"] = ("odylith made-up-command",)

    monkeypatch.setattr(engine_integrity.capability_inventory, "inventory_payload", lambda: payload)

    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)

    assert report["status"] == "fail"
    assert any(
        finding["area"] == "Context Engine"
        and "unknown top-level command" in finding["message"]
        for finding in report["findings"]
    )
