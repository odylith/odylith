from __future__ import annotations

import json
import time

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent


def _generated_source_payload(root) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for source_root in (
            root / "odylith/runtime/source",
            root / "odylith/radar/source",
            root / "odylith/registry/source",
            root / "odylith/atlas/source",
        )
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix in {".json", ".jsonl", ".md", ".mmd"}
    )


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

PATTERN_CONFIRMED_INTENT_TEXT = """Pattern Relief Notebook

## Product story
A person tracking recurring discomfort wants to understand which self-care actions appear to help over time. The product turns scattered daily notes into a small personal feedback loop: record how the day felt, record what action was tried, and review the pattern before deciding what to try next.

## State object
The central thing the product tracks is a person's comfort timeline: a sequence of dated entries, each holding a rating, contributing factors, and the self-care actions tried. Around that sit saved routines and derived trends that connect actions to outcomes.

## First complete path
A new user records their first entry — rates today's status, taps the factors that applied, and logs one action they tried. The next day they log again. After a handful of entries, the app shows a simple trend: status over time, and which logged actions line up with better days. That loop — log, repeat, see the pattern — is the smallest version of the whole product working end to end.

## Human actors
- Person managing their own discomfort (primary user, self-tracking)
- Optionally, a coach or clinician the person shares a summary with (read-only, later)

## External systems
- None required for the first complete path

## Internal product systems
- Entry logging and daily check-in
- Routine library (saved activities the user can attach to an entry)
- Trend and correlation view (pattern over time, action-to-outcome signal)
- Reminder/streak nudge to sustain the daily habit

## Critical assumptions
- Single-user, self-reported data; no diagnosis is claimed.

## Ambiguities
- Platform: native mobile, web app, or both.

## Proof boundary
The first version is proven when a user can log entries over several days and the app renders an honest trend plus an action-to-outcome signal from their own data. External integrations, sharing, and reminders are outside the first proof bar.
"""

MULTI_ACTOR_CONFIRMED_INTENT_TEXT = """Choice Practice Journal

## Product story
Choice Practice Journal gives a learner short practice scenarios and gives a trusted adult a simple recap. The product is not a game score or a behavior ranking. It helps the learner make a choice, see a clear consequence, and leave a short reflection the adult can review later.

## State object
The product keeps a learner practice record with the adult-owned account, learner profile, scenario id, selected choice, consequence note, reflection, recap status, and privacy boundary.

## First complete path
A parent creates an account, adds a learner profile, and picks the age band of eight to ten for the first release. The learner opens an illustrated scenario, makes a choice at the decision point, sees a consequence and a short reflection, and finishes the session. The parent later opens a simple recap of what the learner explored.

## Human actors
- Learner, a child aged eight to ten
- Parent, the account owner at home
- Facilitator, a small-group reviewer
- Scenario author, a content writer

## External systems
- Sign-in provider for the adult account
- Media hosting for illustrations

## Internal product systems
- Account and learner profile service
- Scenario library service
- Choice consequence engine
- Reflection capture service
- Adult recap service
- Learner privacy service

## Critical assumptions
- The adult owns the account; learners do not self-register.
- The first release targets one age band and one parent-led setting.
- Scenario content is pre-authored and curated.

## Ambiguities
- Whether the learner reads independently or needs narration.
- Whether the adult sees full history or a brief recap only.

## Proof boundary
The first release succeeds when a parent can create an account and learner profile, the learner can complete one scenario with a selected choice and reflection, and the parent can open a recap. Multiple age bands, authoring workflows, reminders, and live classroom management are outside the first proof.
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


def test_pattern_greenfield_create_blocks_placeholder_and_clause_drift_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(PATTERN_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a personal pattern tracker",
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
    rendered_payload = json.dumps(payload)
    written_payload = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json",
            tmp_path / "odylith/runtime/source/accepted-project.v1.json",
            tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json",
        )
    ) + "\n" + _generated_source_payload(tmp_path)

    assert rc == 0
    assert elapsed < 30.0
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 4
    assert len(payload["diagrams"]) == 6
    for banned in (
        "Central Thing the Product",
        "Pattern Relief User",
        "Trend and Correlation View (pattern Over",
        "the optionally",
        "uses the product to central thing",
        "uses the product to person's",
        "after several entries, the app builds",
        "the pattern — is the smallest version",
        "smallest version of the whole product",
        "That loop",
        "reach the pattern",
        "Maintains sustain",
        "helps sustain the daily habit",
        "Record Their First",
        "record-their-first",
        "Reminder and Streak Nudge to Sustain",
        "reminder-and-streak-nudge-to-sustain",
    ):
        assert banned not in rendered_payload
        assert banned not in written_payload
    assert any(row.get("title") == "Let Person Managing Discomfort Record First Entry" for row in payload["backlog"])
    assert any(row.get("label") == "Reminder and Streak Nudge Service" for row in payload["components"])
    visible_actors = payload["validation_gate"]["visible_actors"]
    assert visible_actors[0]["visible_actor"] == "Person Managing Discomfort"
    assert visible_actors[1]["visible_actor"] == "Person Managing Discomfort workflow operator"
    assert "Coach" not in " ".join(row["visible_actor"] for row in visible_actors[:2])


def test_multi_actor_greenfield_create_preserves_actor_ownership_and_copy_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(MULTI_ACTOR_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a learner choice practice journal",
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

    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    proposal = accepted["proposal"]
    first_path = proposal["semantic_model"]["first_path_contract"]
    rendered_payload = json.dumps(payload)
    generated_payload = _generated_source_payload(tmp_path)

    assert first_path["actor"] == "Parent"
    assert first_path["visible_result"] == "a short reflection"
    assert [(event["actor"], event["action"]) for event in first_path["events"]] == [
        ("Parent", "creates"),
        ("Parent", "adds"),
        ("Parent", "advance"),
        ("Learner", "opens"),
        ("Learner", "advance"),
        ("Learner", "sees"),
        ("Parent", "opens"),
    ]
    for banned in (
        "Learner, A Child",
        "uses the product to parent creates",
        "add a learner profile and picks",
        "reflection and finishes",
        "understand The",
        "reach a short reflection",
        "use a short reflection",
        "visible outcome from a short reflection",
        "see a consequence and a short reflection, and see",
        "complete path where",
        "learner can create an account",
        "where learner can create",
        "Start with this implementation slice: Start with",
        "should support the user action: create an account",
        "Build the smallest behavior in Account",
        "The product checks the details, explains missing information before it produces a result, and shows a short reflection",
    ):
        assert banned not in rendered_payload
        assert banned not in generated_payload


def test_greenfield_create_rerun_replaces_previous_greenfield_workstreams_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(MULTI_ACTOR_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    first_started = time.perf_counter()
    first_rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a learner choice practice journal",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
            "--json",
        ]
    )
    first_elapsed = time.perf_counter() - first_started
    first_payload = json.loads(capsys.readouterr().out)
    old_ids = {row["idea_id"] for row in first_payload["backlog"]}

    revised_text = MULTI_ACTOR_CONFIRMED_INTENT_TEXT.replace(
        "- Learner, a child aged eight to ten",
        "- Child learner, a kid aged eight to ten",
    )
    intent_path.write_text(revised_text, encoding="utf-8")
    second_started = time.perf_counter()
    second_rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a learner choice practice journal",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
            "--json",
        ]
    )
    second_elapsed = time.perf_counter() - second_started
    second_payload = json.loads(capsys.readouterr().out)
    new_ids = {row["idea_id"] for row in second_payload["backlog"]}

    assert first_rc == 0
    assert second_rc == 0
    assert first_elapsed < 30.0
    assert second_elapsed < 30.0
    assert second_payload["validation_gate"]["status"] == "passed"
    assert old_ids != new_ids
    assert generated_semantic_slop_issues(second_payload) == []
    generated_payload = _generated_source_payload(tmp_path)
    for old_id in old_ids - new_ids:
        assert old_id not in generated_payload
    idea_files = list((tmp_path / "odylith/radar/source/ideas").rglob("*.md"))
    assert len(idea_files) == len(second_payload["backlog"])
    release_events = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(encoding="utf-8")
    for old_id in old_ids - new_ids:
        assert old_id not in release_events


def test_multi_actor_greenfield_create_rerun_is_idempotent_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(MULTI_ACTOR_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    payloads = []
    elapsed_runs = []
    for _index in range(2):
        started = time.perf_counter()
        rc = greenfield_proposals.main(
            [
                "create",
                "--repo-root",
                str(tmp_path),
                "--prompt",
                "Draft a greenfield proposal for a learner choice practice journal",
                "--intent-file",
                ".odylith/runtime/greenfield/confirmed-intent.md",
                "--release",
                "0.0.1",
                "--confirm",
                "--json",
            ]
        )
        elapsed_runs.append(time.perf_counter() - started)
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert elapsed_runs[-1] < 30.0
        payloads.append(payload)

    assert [row["idea_id"] for row in payloads[0]["backlog"]] == [row["idea_id"] for row in payloads[1]["backlog"]]
    assert payloads[0]["diagrams"] == payloads[1]["diagrams"]
    assert payloads[1]["memory"]["recorded"] is True
    assert payloads[1]["memory"]["reused_existing"] is True
    assert len(list((tmp_path / "odylith/radar/source/ideas").rglob("*.md"))) == 4
    stream = tmp_path / agent_runtime_contract.AGENT_STREAM_PATH
    events = [json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines() if line.strip()]
    acceptance_events = [
        event
        for event in events
        if str(event.get("summary", "")).startswith("Accepted greenfield proposal for Choice Practice Journal:")
    ]
    assert len(acceptance_events) == 1
