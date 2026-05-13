from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import engine_integrity


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_engine_integrity_covers_operator_requested_engine_set() -> None:
    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)

    assert report["status"] == "pass"
    assert report["areas_checked"] == 22
    assert report["areas_present"] == 22
    assert report["command_backed_areas"] == 22
    assert report["anchor_backed_areas"] == 22
    assert report["activation_backed_areas"] == 22
    assert report["integration_backed_areas"] == 22
    assert report["handshakes_checked"] == len(engine_integrity.ENGINE_HANDSHAKES)
    assert report["handshakes_wired"] == len(engine_integrity.ENGINE_HANDSHAKES)
    assert report["counts"]["error"] == 0
    areas = {row["area"]: row for row in report["areas"]}
    assert {
        "Analysis Engine",
        "Domain Intelligence",
        "Delivery Intelligence",
        "Tribunal",
        "Reasoning Engine",
        "Execution Engine",
        "Proof State",
        "Surface DAGs",
        "Topology Integrity",
        "Governance Engine",
        "Governed Harness / Turn Gate",
        "Intervention Engine",
        "Discipline Engine",
        "Benchmark Harness",
        "Taxonomies and FSMs",
        "Context Engine",
        "Memory Substrate",
        "Subagent Router",
        "Subagent Orchestrator",
        "Install / Upgrade / Migration Runtime",
        "Security and Trust",
        "Operator Experience",
    } == set(areas)
    for row in areas.values():
        assert row["fits_as"], row["area"]
        assert row["command_backed"], row["area"]
        assert row["anchor_backed"], row["area"]
        assert row["activation_backed"], row["area"]
        assert row["integration_backed"], row["area"]
        assert row["handoff_in"] or row["handoff_out"], row["area"]
    assert "odylith greenfield apply" in areas["Domain Intelligence"]["commands"]
    assert areas["Subagent Router"]["inventory_names"] == ["Subagent Router"]
    assert areas["Subagent Orchestrator"]["inventory_names"] == ["Subagent Orchestrator"]
    assert "odylith doctor" in areas["Security and Trust"]["commands"]


def test_engine_integrity_text_report_is_operator_readable() -> None:
    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)
    text = engine_integrity._format_text(report)  # noqa: SLF001

    assert "Odylith engine integrity report" in text
    assert "- status: pass" in text
    assert "- activation_backed: 22" in text
    assert "- integration_backed: 22" in text
    assert "Engine handshakes" in text
    assert "all requested engine areas are inventory-backed" in text
    assert "Engine spine" in text
    assert "Domain Intelligence - greenfield/project-shape reasoning contracts plus validated host-authored governed writes" in text


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
        finding["area"] == "Discipline Engine"
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


def test_engine_integrity_rejects_unknown_handshake_area(monkeypatch) -> None:
    broken = engine_integrity.ENGINE_HANDSHAKES + (
        engine_integrity.EngineHandshake(
            "Imaginary Engine",
            "Analysis Engine",
            "bad handoff for regression coverage",
        ),
    )
    monkeypatch.setattr(engine_integrity, "ENGINE_HANDSHAKES", broken)

    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)

    assert report["status"] == "fail"
    assert any(
        finding["area"] == "Imaginary Engine"
        and "unknown source area" in finding["message"]
        for finding in report["findings"]
    )
