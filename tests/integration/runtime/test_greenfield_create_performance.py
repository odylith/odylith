from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent

POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS = 60.0


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


def _generated_visible_surface_payload(root) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "odylith").rglob("*")
        if path.is_file() and path.suffix in {".html", ".js"}
    )


def _assert_whole_project_completed(payload: dict, root: Path, *, elapsed: float) -> None:
    assert elapsed < POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) >= 4
    assert len(payload["diagrams"]) == 6
    assert (root / ".odylith/runtime/greenfield/confirmed-intent.json").is_file()
    assert (root / "odylith/runtime/source/accepted-project.v1.json").is_file()
    assert (root / "odylith/radar/radar.html").is_file()
    assert (root / "odylith/registry/registry.html").is_file()
    assert (root / "odylith/atlas/atlas.html").is_file()
    assert (root / "odylith/compass/compass.html").is_file()
    assert (root / "odylith/index.html").is_file()
    assert len(list((root / "odylith/atlas/source").glob("*.svg"))) == len(payload["diagrams"])
    assert len(list((root / "odylith/atlas/source").glob("*.png"))) == len(payload["diagrams"])


def test_greenfield_create_cli_completes_whole_project_under_sixty_seconds(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    _write_confirmed_intent(tmp_path)

    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    started = time.perf_counter()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "odylith.cli",
            "greenfield",
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
        ],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS,
    )
    elapsed = time.perf_counter() - started

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    _assert_whole_project_completed(payload, tmp_path, elapsed=elapsed)


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

NARRATIVE_AGENCY_CONFIRMED_INTENT_TEXT = """Stand Tall — a dignity and agency app for kids

## Product story
Kids are constantly told what to do, but rarely get safe practice at the harder skills underneath: noticing how they feel, setting a boundary, making a choice and owning it, and treating others as people who matter. Stand Tall gives a child short, story-driven moments where they make real decisions — speak up or stay quiet, share or keep, forgive or hold the line — and then see the consequences play out kindly. A trusted grown-up sets it up and can look in on what their kid is exploring, but the child's own choices stay the heart of it. The goal isn't points or streaks; it's a kid who walks away feeling a little more like the author of their own actions and a little more aware that everyone around them deserves the same respect.

## State object
The unit of truth is a child's growing sense of agency: their profile, the dignity and choice scenarios they've worked through, the decisions they made inside each one, and the reflections a grown-up can gently see — all tied to one kid and held privately under that grown-up's account.

## First complete path
A parent or teacher creates an account, adds a child, and picks an age band. The child opens an illustrated scenario, makes a choice at the decision point, sees a caring consequence and a one-line reflection, and finishes the moment. The grown-up later opens a simple recap showing what the child explored and what it was teaching — one full loop from setup to a child's choice to a grown-up's view.

## Human actors
- Child learner — makes the choices and does the reflecting
- Parent — sets up the child, picks scenarios, reviews progress at home
- Teacher or counselor — runs it for a small group or a specific kid
- Content author — writes and curates the dignity and agency scenarios

## External systems
- Email or sign-in provider for the grown-up account
- Asset/media hosting for illustrations and audio
- Push or email reminders for grown-ups (optional, off by default)

## Internal product systems
- Account and child-profile management with age bands
- Scenario library and authoring/curation
- Choice-and-consequence engine that records each decision
- Reflection capture for the child
- Grown-up recap and progress view
- Privacy and consent boundary around children's data

## Critical assumptions
- A grown-up always owns the account; children don't self-register
- Single-device, turn-based use to start; no live multiplayer
- Content is pre-authored and curated, not kid-generated, in the first release
- "Progress" is qualitative reflection, not scores or rankings
- Children's data is minimized and never used for ads or external sharing

## Ambiguities
- Target age band for v1 — early (5–7), middle (8–10), or tween (11–13)?
- Primary setting — home/parent-led, or classroom/teacher-led with groups?
- Does the child read independently, or is narration/audio required?
- How much can a grown-up see — full choice history, or only gentle summaries?

## Proof boundary
Done means: a grown-up can create an account and a child profile, the child can complete one scenario end to end with a recorded choice and reflection, and the grown-up can open a recap of it — with children's data kept private to that account. Authoring depth, multiple age bands, and reminders are out of scope for this first proof.
"""

GLP1_CONFIRMED_INTENT_TEXT = """# GLP-1 Companion - Medication Tracking App

## Product story
People starting or maintaining a GLP-1 medication take it on a weekly cadence, titrate doses upward on a schedule, and live with side effects that change week to week. This product gives one person a calm, private place to log each injection, follow their titration schedule without second-guessing the dose, watch weight and side effects trend over time, and avoid missing or double-recording a dose. It is a personal adherence and self-knowledge companion, not a clinical or prescribing tool.

## State object
The durable thing the product holds is a single user's medication journey: their current medication and dose, their titration schedule, a dated history of injections taken, recorded weight readings, and logged side effects.

## First complete path
A user sets up their medication, current dose, and weekly injection day. When a dose is due, the app reminds them; they confirm the injection, optionally log their weight and any side effects, and the app records it, advances them along their titration schedule, and shows the next due date.

## Human actors
- The person on the GLP-1 medication, tracking their own treatment (the only first-class user)
- Optionally, a caregiver helping that person stay on schedule (later, not in the first path)

## External systems
- Push or local notification delivery for dose reminders
- Optional calendar export for injection days (later)
- No EHR, pharmacy, or prescriber integration in the first version

## Internal product systems
- Medication and titration-schedule model that knows dose steps and timing
- Injection log that records each taken dose and computes the next due date
- Weight and side-effect tracking with trend views over time
- Reminder/adherence engine that flags missed or upcoming doses and guards against double-dosing

## Critical assumptions
- Single-user, personal-use app; no multi-tenant accounts or provider dashboards in v1
- The user, not a clinician, enters their prescribed medication and dose
- Weekly-injection GLP-1s are the primary cadence; the schedule model should not hard-code one drug
- Data is private to the user and stored for them; sharing or sync is out of scope for the first path

## Ambiguities
- Platform: native mobile, web, or both
- Whether titration schedules are picked from built-in presets per drug or fully hand-entered by the user
- How far to go on side-effect tracking
- Whether weight tracking is core to v1 or a fast-follow

## Proof boundary
The product is proven when one user can set up a medication and dose, receive a reminder when a dose is due, confirm an injection, see the schedule advance to the correct next dose and date, and review their injection, weight, and side-effect history as a trend — with missed-dose and double-dose cases handled correctly.
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
        "Start with this implementation slice",
        "representative user can",
        "shows open",
        "should support the user action: create an account",
        "Build the smallest behavior in Account",
        "The product checks the details, explains missing information before it produces a result, and shows a short reflection",
    ):
        assert banned not in rendered_payload
        assert banned not in generated_payload


def test_narrative_greenfield_create_normalizes_action_outcome_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(NARRATIVE_AGENCY_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a child agency practice app",
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
    generated_payload = _generated_source_payload(tmp_path)

    assert rc == 0
    assert elapsed < 30.0
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) >= 5
    assert len(payload["diagrams"]) == 6
    for banned in (
        "see open",
        "users can see open",
        "Choice-and-consequence Engine That",
        "ending in `That`",
        "understand The",
        "The unit of truth is",
        "Let Child Learner Makes",
        "Let Child Learner Create an Account",
        "Let Child Learner Create An Account",
        "let one representative user creates an account",
        "representative user can",
        "visible outcome from",
        "uses the product to parent creates",
        "shows open",
        "Grown Up Recap",
        "Scenario Library and Authoring and Curation",
        "for a reviewer to.",
        "Start with this implementation slice",
    ):
        assert banned not in rendered_payload
        assert banned not in generated_payload
    component_labels = {row["label"] for row in payload["components"]}
    assert "Scenario Library, Authoring, and Curation Service" in component_labels
    assert "Grown-up Recap and Progress View Service" in component_labels


def test_glp1_greenfield_create_completes_without_actor_or_state_label_drift_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(GLP1_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a GLP-1 medication tracking app",
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
    generated_payload = _generated_source_payload(tmp_path)
    visible_surface_payload = _generated_visible_surface_payload(tmp_path)

    assert rc == 0
    assert elapsed < 30.0
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 4
    assert len(payload["diagrams"]) == 6
    for banned in (
        "Tracking Their Own Treatment",
        "Caregiver Helping",
        "Caregiver need",
        "Durable Thing the Product Holds",
        "Durable Thing The Product Holds",
        "Glp 1 Companion",
        "glp 1 companion",
        "The glp-1 companion",
        "Promote glp-1 companion",
        "External dependencies for glp-1 companion",
        "providers for glp-1 companion",
        "for glp-1 companion stay",
        "Person On The GLP-1",
        "the person on the glp-1",
        "The person on the glp-1",
        "Optionally log their weight",
        "Advances them along their titration schedule",
        "and advances them along their titration schedule",
        "They optionally logs",
        "reach the next due date",
        "and see what to fix when required information is missing",
        "and lets the person on the GLP-1 see the next due date, and see what to fix",
        "lets the caregiver reach",
        "lets the next participant reach",
        "Medication and Titration Schedule Model That Knows Dose Steps and Timing Service",
        "Weight and Side Effect Tracking with Trend Views Over Time Service",
        "Proof proof reviewer",
        "Proof build owner",
        "Proof release reviewer",
        "result result",
        "has mid-sentence capitalization drift near `Their`",
        "does not contain at least four component-local domain terms",
        "greenfield post-confirm completion failed",
    ):
        assert banned not in rendered_payload
        assert banned not in generated_payload
        assert banned not in visible_surface_payload
    actor_labels = [row["visible_actor"] for row in payload["validation_gate"]["visible_actors"]]
    assert actor_labels[0] == "Person on the GLP-1 Medication"
    assert "GLP-1 Companion risk reviewer" in actor_labels
    assert "GLP-1 Companion proof reviewer" in actor_labels
    assert "Single User's Medication Journey" in generated_payload
    assert "GLP-1 Companion - Medication Tracking App" in visible_surface_payload
    assert "They optionally log their weight" in visible_surface_payload
    assert "The app advances them along their titration schedule" in visible_surface_payload
    assert "Caregiver: supplies context" in rendered_payload
    assert "deferred from the first path" in rendered_payload
    component_labels = {row["label"] for row in payload["components"]}
    assert "Medication and Titration Schedule Model Service" in component_labels
    assert "Weight and Side Effect Tracking Service" in component_labels


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
