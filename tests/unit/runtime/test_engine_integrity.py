from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import engine_integrity


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_engine_integrity_covers_operator_requested_engine_set() -> None:
    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)

    assert report["status"] == "pass"
    assert report["areas_checked"] == 15
    assert report["areas_present"] == 15
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
    assert "odylith greenfield create" in areas["Greenfield proposals and domain intelligence"]["commands"]
    assert areas["Subagent Orchestration"]["inventory_names"] == ["Subagent Router", "Subagent Orchestrator"]


def test_engine_integrity_text_report_is_operator_readable() -> None:
    report = engine_integrity.evaluate_engine_integrity(REPO_ROOT)
    text = engine_integrity._format_text(report)  # noqa: SLF001

    assert "Odylith engine integrity report" in text
    assert "- status: pass" in text
    assert "all requested engine areas are inventory-backed" in text
