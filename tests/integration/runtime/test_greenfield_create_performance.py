from __future__ import annotations

import json
import time

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent


SOLAR_CONFIRMED_INTENT_TEXT = """SunLedger

## Product story
SunLedger helps a homeowner forecast solar production and household demand, then choose a daily battery and load plan that lowers grid use while keeping comfort and reserve constraints visible.

## State object
The core state is an energy plan for one home: forecasted solar production, household demand, battery state, controllable loads, constraints, recommendations, explanation, execution status, and measured outcome.

## First complete path
A homeowner connects inverter, meter, battery, and weather sources. SunLedger pulls readings and weather, forecasts today's production and demand, builds a battery and load control plan, shows the homeowner why it should reduce grid draw, lets them approve it, issues the approved control actions, monitors the result, and reports whether the plan reduced grid imports without violating reserve or comfort limits.

## Human actors
- Homeowner who wants lower grid use and understandable energy decisions.
- Installer or energy advisor who configures device connections and household constraints.

## External systems
- Solar inverter telemetry.
- Smart meter or utility usage feed.
- Battery management system.
- Weather forecast provider.
- Controllable load interfaces for EV charging, HVAC, or water heating.

## Internal product systems
- Energy telemetry ingestion.
- Production and demand forecast engine.
- Optimization planner.
- Homeowner approval and explanation view.
- Control dispatch and monitoring.
- Outcome reporting.

## Critical assumptions
- The home has connected solar, metering, and battery telemetry.
- The homeowner can approve or reject an energy plan before automated control actions run.
- Weather and usage data are fresh enough to make a same-day plan useful.
- Comfort and reserve limits must override savings recommendations.

## Ambiguities
- Whether control actions should run automatically after approval or stay advisory only.
- Which device protocols and utility feeds are available in the first market.
- Whether the first release targets one home or a portfolio of homes.

## Proof boundary
The first proof is one home completing one daily loop: ingest telemetry and weather, forecast production and demand, create a defensible plan, receive homeowner approval, dispatch approved battery and load control actions, and report grid-import reduction against reserve and comfort constraints. Full closed-loop hardware automation, market bidding, and multi-site fleet optimization are outside the first proof.

## Next step
- Confirm: create the governed project records from this confirmed intent.
- Edit: revise the product story, actors, systems, first path, assumptions, ambiguities, or proof boundary before create.
- Reject: stop without creating project records.
"""


def test_greenfield_create_confirm_full_refresh_stays_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    _write_confirmed_intent(tmp_path)

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
            "--json",
        ]
    )
    elapsed = time.perf_counter() - started
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert elapsed < 30.0
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert all("(" not in line and ")" not in line for line in payload["atlas_scaffold_logs"])
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 4
    assert len(payload["diagrams"]) == 6
    assert (tmp_path / "odylith/radar/radar.html").is_file()
    assert (tmp_path / "odylith/registry/registry.html").is_file()
    assert (tmp_path / "odylith/atlas/atlas.html").is_file()
    assert (tmp_path / "odylith/compass/compass.html").is_file()
    assert (tmp_path / "odylith/index.html").is_file()
    assert len(list((tmp_path / "odylith/atlas/source").glob("*.svg"))) == len(payload["diagrams"])
    assert len(list((tmp_path / "odylith/atlas/source").glob("*.png"))) == len(payload["diagrams"])
    catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    assert all(diagram["reviewed_watch_fingerprints"] for diagram in catalog["diagrams"])
    assert all(diagram["render_source_fingerprint"] for diagram in catalog["diagrams"])
    assert all(str(diagram.get("source_png", "")).strip().endswith(".png") for diagram in catalog["diagrams"])
    assert all((tmp_path / str(diagram["source_png"])).is_file() for diagram in catalog["diagrams"])


def test_solar_greenfield_create_refreshes_semantic_model_and_stays_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(SOLAR_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "An app that optimizes the production and consumption of solar energy",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
            "--json",
        ]
    )
    elapsed = time.perf_counter() - started
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert elapsed < 30.0
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) >= 5
    assert len(payload["diagrams"]) == 6
    written_payload = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json",
            tmp_path / "odylith/runtime/source/accepted-project.v1.json",
        )
    )
    assert "visible outcome from" not in written_payload
    assert "control actions to battery" not in written_payload
