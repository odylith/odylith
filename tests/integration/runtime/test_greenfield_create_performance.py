from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from odylith.runtime.artifact_quality.generated_copy_quality import has_inline_role_casing_drift
from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent

POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS = 60.0


def _run_confirmed_create_main(tmp_path: Path, capsys, *, prompt: str) -> tuple[int, dict, float]:
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    compile_rc = greenfield_proposals.main(
        [
            "compile-transaction",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--output",
            transaction_file,
            "--release",
            "0.0.1",
            "--format",
            "json",
        ]
    )
    compile_output = capsys.readouterr().out
    assert compile_rc == 0, compile_output
    transaction_hash = str(json.loads(compile_output)["product_create_transaction"]["transaction_hash"])
    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            transaction_file,
            "--transaction-hash",
            transaction_hash,
            "--confirm",
            "--json",
        ]
    )
    elapsed = time.perf_counter() - started
    payload = json.loads(capsys.readouterr().out)
    return rc, payload, elapsed


def _run_confirmed_create_subprocess(
    *,
    tmp_path: Path,
    prompt: str,
    env: dict[str, str],
    timeout: float,
) -> tuple[subprocess.CompletedProcess[str], float]:
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    compile_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "odylith.cli",
            "greenfield",
            "compile-transaction",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--output",
            transaction_file,
            "--release",
            "0.0.1",
            "--format",
            "json",
        ],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if compile_result.returncode != 0:
        return compile_result, timeout
    transaction_hash = str(json.loads(compile_result.stdout)["product_create_transaction"]["transaction_hash"])
    started = time.perf_counter()
    create_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "odylith.cli",
            "greenfield",
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            transaction_file,
            "--transaction-hash",
            transaction_hash,
            "--confirm",
            "--json",
        ],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return create_result, time.perf_counter() - started


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
    result, elapsed = _run_confirmed_create_subprocess(
        tmp_path=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        env=env,
        timeout=POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    _assert_whole_project_completed(payload, tmp_path, elapsed=elapsed)


def test_yacht_greenfield_confirm_repairs_quality_failures_and_commits_under_sixty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(YACHT_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a yacht servicing platform",
    )
    generated_source = _generated_source_payload(tmp_path)

    assert rc == 0
    assert elapsed < POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["post_confirm_quality_manifest"]["status"] == "passed"
    assert payload["post_confirm_quality_manifest"]["issue_count"] == 0
    assert payload["post_confirm_quality_manifest"]["quality_lenses"]["status"] == "passed"
    assert set(payload["post_confirm_quality_manifest"]["quality_lenses"]["lenses"]) == {
        "product_manager",
        "architect",
        "engineer",
        "domain_expert",
    }
    assert payload["post_confirm_quality_manifest"]["write_transaction"]["status"] == "committed"
    assert payload["post_confirm_quality_manifest"]["whole_project_elapsed_seconds"] < POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) >= 5
    assert len(payload["diagrams"]) == 6
    assert "Path path" not in generated_source
    assert "hang off of" not in generated_source
    assert "rewriting Customer and Contact Directory" not in generated_source
    assert not any(
        has_inline_role_casing_drift(line)
        for line in generated_source.splitlines()
        if "Customer and Contact Directory" in line
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

YACHT_CONFIRMED_INTENT_TEXT = """# Harbormaster — Yacht Servicing Platform

## Product story
A yacht servicing platform coordinates the messy reality of keeping vessels seaworthy: an owner or captain reports a problem or schedules routine maintenance, a service company assigns the right technician, and the work happens dockside, on the hard, or in a yard slot. The platform's job is to turn an informal "the watermaker is failing and we sail in three weeks" request into a tracked job with a quote, a scheduled visit, parts on order, a technician on the dock, and a signed-off record the owner can trust. It earns its keep by making the status of every boat and every open job legible to the people who are otherwise chasing each other by phone and text.

## State object
The center of gravity is the service job: a unit of work against one vessel, moving through requested, quoted, approved, scheduled, in-progress, and completed, carrying the vessel, the customer, assigned technician(s), parts, labor time, and a final service record. Vessels and customers are long-lived records the jobs hang off of.

## First complete path
A captain submits a service request for a known yacht; a service coordinator reviews it, produces a quote, and sends it; the customer approves; the coordinator schedules a technician for a date and berth; the technician performs the work, logs parts and hours, and marks it complete; the customer receives the finished service record. That single request-to-completed-record path is the proof the product works.

## Human actors
- Yacht owner — requests work, approves quotes, reads the service history of their vessel.
- Captain or crew — reports problems, coordinates access and timing on behalf of the owner.
- Service coordinator / advisor — triages requests, builds quotes, schedules jobs, owns the customer relationship.
- Marine technician — performs the work, logs parts and labor, signs off completion.
- Service manager — sees the board of all open jobs, technician load, and overdue work.

## External systems
- Payment processor for quote approval and invoicing.
- Parts and chandlery suppliers for ordering and availability.
- Email/SMS notifications to owners, captains, and technicians.
- Marina/berth and weather data for scheduling dockside work.

## Internal product systems
- Vessel registry — the boats under service and their specs/history.
- Customer and contact directory.
- Job lifecycle and scheduling engine — state transitions, technician assignment, calendar.
- Quoting, parts, and labor capture.
- Service history and completion records per vessel.

## Critical assumptions
- Service is delivered by a company's own coordinators and technicians, not an open marketplace of independent contractors.
- One organization or a single yard operates the platform initially; multi-yard tenancy can come later.
- Scheduling is human-driven assignment, not fully automated optimization, for the first path.
- Vessels are mostly known or registered before a job opens, rather than walk-up unknown boats.

## Ambiguities
- Single service company vs. multi-vendor marketplace changes the topology and trust model.
- Whether owners self-serve in their own portal or everything routes through a coordinator.
- Whether parts/inventory is tracked in-platform or just referenced from a supplier.
- Depth of payments: full invoicing and ledger, or just quote approval to start.

## Proof boundary
The product is proven when one service request for one vessel travels end to end — request, quote, approval, schedule, technician work log, completion record — visible to both the coordinator and the customer. Inventory optimization, multi-yard tenancy, and automated scheduling are explicitly out of the first proof.
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

QUANTUM_CONFIRMED_INTENT_TEXT = """# Quantum Link Lab

## Product story

A lab application for a research team running entanglement-based quantum communication on real hardware. A researcher configures a run — entangled-photon source, the two measurement stations, basis settings, and channel conditions — launches it, and watches the link behave live: entangled pairs distributed, coincidence counts, the measured Bell/CHSH parameter, error rate (QBER), and sifted/final key bits. The headline question each run answers is whether the entanglement survived the channel well enough to certify a secure link, judged by the Bell-inequality violation. The app is the bench where an E91 experiment is set up, driven on the actual rig, observed, and compared against earlier runs.

## State object

A communication run: its E91 parameters and measurement-basis configuration, the bound source and two station endpoints, the live and final measurements (distributed pairs, coincidence counts, CHSH/S value, QBER, sifted and final key length), its status from configured through running to completed or aborted, and the timestamped record for later review and comparison.

## First complete path

A researcher opens the lab, defines a new E91 run (source, two stations, bases, channel/integration settings), launches it against the hardware, watches coincidences and the live CHSH value stream in, and ends with a completed run that reports whether the Bell inequality was violated (link certified secure or not), the QBER, and the key established — saved and viewable alongside prior runs.

## Human actors

- Researcher — configures and launches E91 runs, reads live and historical results
- Lab lead — reviews run history, compares configurations, judges link viability
- Lab technician / operator — manages source and station hardware setup, monitors active runs

## External systems

- Entangled-photon source rig and its control interface
- Two measurement stations (detectors + basis selection) and their control/readout interface
- Coincidence-counting / time-tagging electronics
- Shared clock / synchronization source across the two stations

## Internal product systems

- Run configuration and validation (E91 parameters, bases, bound endpoints)
- Hardware control and run execution (drives source + stations, sequences a run)
- Live telemetry stream (coincidences, CHSH, QBER as the run progresses)
- Security/verification logic (Bell-inequality test -> secure verdict, key sifting)
- Results store and run history (persisted runs, comparison, review)

## Critical assumptions

- v1 drives real lab hardware through a control interface; the rig is available and exposes commands/readout the app can call
- E91 is the one headline protocol; CHSH/Bell violation is the security test that defines a "good" run
- A run is owned by one researcher session at a time; concurrent control of the same hardware is out of first scope
- Live telemetry and persisted, comparable run history are both required from day one

## Ambiguities

- Hardware interface contract — is there a documented control API/SDK for the source and stations, or does the app need a driver/adapter layer built first?
- Safety/interlock requirements for driving the rig (laser/detector safety gating) — in v1 scope or assumed external?
- Single shared lab instrument set, or multiple rigs the app must select between?

## Proof boundary

The product is proven when a researcher can configure an E91 run, launch it on the real rig, watch coincidences and the CHSH value stream live, and end with a saved run that reports the Bell-inequality verdict (secure link or not), the QBER, and the established key — then find that run in history and compare it to another. Formal security certification and hardware safety-certification of the rig are beyond this first proof.
"""

SIGNAL_PROCESSING_CONFIRMED_INTENT_TEXT = """# Realtime Signal Processing Pipeline

## Product story

A system that ingests continuous streams of sensor or device signals, processes them as they arrive, and emits derived results - filtered waveforms, detected events, feature vectors - with low and predictable latency. The value is acting on signals while they still matter: catching an anomaly, triggering an alert, or feeding a downstream model the instant the data lands, instead of in a nightly batch. Operators configure what counts as a signal of interest and watch the pipeline stay healthy under continuous load.

## State object

A live processing pipeline holding ordered streams of signal samples, each moving through a chain of stages (ingest, transform, detect, emit). The durable state is the stage configuration, the per-stream processing offset, and the emitted results; the in-flight state is the bounded window of samples currently being processed.

## First complete path

A signal source connects and pushes a stream of samples; the pipeline ingests them, applies a configured transform (for example a filter or FFT window), evaluates a detection rule, and emits a result event to a sink - all within a bounded latency target, with the stream offset advanced so processing is resumable.

## Human actors

- Pipeline operator - configures stages, thresholds, and sinks; monitors health and latency.
- Integration engineer - connects signal sources and downstream consumers to the pipeline.
- Analyst or on-call responder - consumes emitted events and acts on detected conditions.

## External systems

- Signal sources (sensors, devices, upstream message brokers) producing sample streams.
- Result sinks (alerting, dashboards, data stores, downstream models) consuming emitted events.
- Time source / clock for latency measurement and windowing.

## Internal product systems

- Ingest layer - accepts streams, normalizes samples, tracks per-stream offsets.
- Processing core - staged transform and detection chain operating over bounded windows.
- Emit layer - delivers results to configured sinks with delivery guarantees.
- Control plane - stage configuration, thresholds, and pipeline lifecycle.
- Observability - latency, throughput, and backpressure health signals.

## Critical assumptions

- Streams are ordered or can be ordered per source, and bounded-window processing is acceptable rather than full-history reprocessing.
- A latency target exists and matters more than maximizing batch throughput.
- Signal types and transforms are configurable rather than hard-coded to one domain.
- Single-tenant operation to start; multi-tenant isolation is out of scope for the first path.

## Ambiguities

- Domain: audio, biomedical, RF/telemetry, industrial/IoT, or general-purpose? This shapes the default transforms.
- Latency class: sub-millisecond hard-realtime, or soft-realtime in the tens-to-hundreds of milliseconds?
- Delivery semantics: at-least-once, exactly-once, or best-effort on the emit side?
- Scale: one stream or thousands concurrent? This drives the backpressure and partitioning design.

## Proof boundary

The first path is proven when a sample stream flows end to end - ingest, transform, detect, emit - under a stated latency target with a resumable offset, demonstrated on at least one source-to-sink configuration. Multi-source scale, exactly-once delivery, and domain-specific transform libraries are beyond this first boundary.
"""

PUBLIC_RESPONSE_CONFIRMED_INTENT_TEXT = """# Public Response Workspace

## Product story

Public Response Workspace helps an operations team track a fast-moving regional incident, combine delayed field reports with capacity signals, and decide which response actions need to happen next while the situation is still changing.

## State object

The central thing the system tracks is an active incident: a geographic area with reported signals, severity trends, available response capacity, and the interventions currently in effect.

## First complete path

A regional coordinator opens the dashboard, sees an area where signal growth and capacity pressure are accelerating past a threshold, drills into the trend, allocates additional response supply and flags a public advisory, and the incident record updates to reflect the new interventions and a revised projection — one full loop from signal to decision to recorded action.

## Human actors

- Regional coordinator - monitors incidents and authorizes interventions
- Data analyst - interprets trends and validates incoming signal quality
- Capacity coordinator - reports available operational capacity
- Field reporter - submits severity data from the front line

## External systems

- Field report feeds
- Capacity availability systems
- Response supply inventory systems
- Public alerting channels

## Internal product systems

- Incident tracking and state model
- Signal and severity ingestion
- Capacity and resource allocation
- Trend and projection view
- Intervention recording and advisory issuance

## Critical assumptions

- Reports and capacity data arrive as feeds the system can ingest.
- Users are authorized response professionals, not the general public.
- The first release targets one region or jurisdiction.
- Projections are decision support, not certified forecasting.

## Ambiguities

- Geographic granularity for the first release.
- Whether live feed ingestion or imported reports are required at launch.
- Whether public advisories are issued directly or prepared for another channel.
- Whether supply allocation is tracked only or integrated with inventory systems.

## Proof boundary

The product is proven when a coordinator can, against one active incident, see accelerating signal and capacity pressure, take an allocation-and-advisory action, and have that action recorded with an updated incident picture. Multi-region coordination, certified forecasting, and live external feed integrations are outside the first proof.
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

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
    )

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

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="An app that optimizes the production and consumption of solar energy",
    )

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
    generated_payload = _generated_source_payload(tmp_path)
    assert "visible outcome from" not in written_payload
    assert "control actions to battery" not in written_payload
    for banned in (
        "sunLedger",
        "Do not expand beyond connecting inverter, meter, battery and weather sources, sunLedger",
        "Do not expand beyond connecting inverter, meter, battery and weather sources, SunLedger forecasts today's production and demand, and SunLedger builds a battery and load control plan until",
    ):
        assert banned not in written_payload
        assert banned not in generated_payload
    for required in ("approve", "approved control actions", "grid imports", "reserve", "comfort"):
        assert required in generated_payload


def test_pattern_greenfield_create_blocks_placeholder_and_clause_drift_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(PATTERN_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a personal pattern tracker",
    )
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
        "Do not expand beyond recording first entry and logging again until",
    ):
        assert banned not in rendered_payload
        assert banned not in written_payload
    assert any(row.get("title") == "Let Person Managing Discomfort Record First Entry" for row in payload["backlog"])
    assert any(row.get("label") == "Reminder and Streak Nudge Service" for row in payload["components"])
    assert "logging again" in written_payload
    assert "reviewing a simple trend: status over time" in written_payload
    visible_actors = payload["validation_gate"]["visible_actors"]
    assert visible_actors[0]["visible_actor"] == "Person Managing Discomfort"
    assert visible_actors[1]["visible_actor"] == "Person Managing Discomfort workflow operator"
    assert "Coach" not in " ".join(row["visible_actor"] for row in visible_actors[:2])


def test_multi_actor_greenfield_create_preserves_actor_ownership_and_copy_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(MULTI_ACTOR_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a learner choice practice journal",
    )

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
        ("Parent", "picks"),
        ("Learner", "opens"),
        ("Learner", "makes"),
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
        "product keeps a learner practice record",
        "accepted change to the product keeps",
        "The choice practice journal components come from product systems named in the accepted product direction: Account and Learner Profile Service, Scenario Library Service, Choice Consequence Engine, Reflection.",
        "Do not expand beyond creating an account, adding a learner profile, picking the age band of eight to ten for the first release, and opening an illustrated scenario until",
    ):
        assert banned not in rendered_payload
        assert banned not in generated_payload
    for required in ("make a choice at the decision point", "short reflection", "simple recap"):
        assert required in generated_payload


def test_narrative_greenfield_create_normalizes_action_outcome_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(NARRATIVE_AGENCY_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a child agency practice app",
    )
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

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a GLP-1 medication tracking app",
    )
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
    assert "the app records it, advances them along their titration schedule" in visible_surface_payload
    assert "Caregiver: helping that person stay on schedule (later, not in the first path)" in generated_payload
    assert "Caregiver" in visible_surface_payload
    assert "deferred from the first path" in rendered_payload
    component_labels = {row["label"] for row in payload["components"]}
    assert "Medication and Titration Schedule Model Service" in component_labels
    assert "Weight and Side Effect Tracking Service" in component_labels


def test_greenfield_create_preserves_reported_saved_result_tail_and_deferred_scope_under_sixty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(QUANTUM_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a lab app where we are building quantum communication",
    )
    rendered_payload = json.dumps(payload)
    generated_payload = _generated_source_payload(tmp_path)
    visible_surface_payload = _generated_visible_surface_payload(tmp_path)
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    first_path = accepted["proposal"]["semantic_model"]["first_path_contract"]
    sequence = next(row for row in accepted["proposal"]["diagrams"] if row["title"] == "First Path Sequence")
    sequence_source = sequence["mermaid_source"].casefold()

    assert rc == 0
    assert elapsed < POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 5
    assert len(payload["diagrams"]) == 6
    assert "the Bell inequality was violated" in first_path["visible_result"]
    assert "the QBER, and the established key" in first_path["visible_result"]
    assert "saved and viewable with prior runs" in first_path["visible_result"]
    assert any(row.get("visible_result") for row in first_path["events"])
    for term in ("qber", "key", "saved", "viewable", "prior"):
        assert term in sequence_source
    assert 'and the<br/>key"]' not in sequence_source
    assert "the key established" not in sequence_source
    assert "established key" in sequence_source
    component_labels = {row["label"] for row in payload["components"]}
    assert "Live Telemetry Stream Service" in component_labels
    for banned in (
        "semantic_model first_path_contract has no visible-result event",
        "confirmed Atlas flowchart `First Path Sequence` omits the tail",
        "prewrite Registry package missing rendered active component spec",
        "accepted result for review",
        "lets the lab lead reach",
        "lets the next participant reach",
        "visible-result event",
        "ending in `key`",
        "and the<br/>key",
    ):
        assert banned not in rendered_payload
        assert banned not in generated_payload
        assert banned not in visible_surface_payload


def test_greenfield_create_completes_signal_processing_pipeline_without_sentence_fragment_slop_under_sixty_seconds(
    tmp_path,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(SIGNAL_PROCESSING_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a real-time signal processing pipeline",
    )
    generated_payload = _generated_source_payload(tmp_path)
    visible_surface_payload = _generated_visible_surface_payload(tmp_path)
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    proposal = accepted["proposal"]
    project_payload = json.dumps(
        {
            "project_brief": proposal.get("project_brief", {}),
            "next_steps": payload.get("next_steps", {}),
        },
        sort_keys=True,
    )

    assert rc == 0
    assert elapsed < POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 5
    assert len(payload["diagrams"]) == 6
    assert proposal["backlog"][0]["product_view"] == (
        "Ingest Layer Service is complete when the user can connect and push a stream of samples, "
        "see a result event to a sink, and recover cleanly from a bad or incomplete attempt."
    )
    assert "Confirm this as the versioned state object:" in project_payload
    assert any(row["title"] == "Keep Live Processing Pipeline Clear and Reviewable" for row in proposal["backlog"])
    assert any(row["title"] == "Show Why Live Processing Pipeline Can Be Trusted" for row in proposal["backlog"])
    for bad_label in (
        "Live Processing Pipeline Holding Ordered Streams",
        "Each Moving Through a Chain of Stages",
    ):
        assert bad_label not in project_payload
        assert bad_label not in generated_payload
    for required_file in (
        "odylith/radar/radar.html",
        "odylith/registry/registry.html",
        "odylith/atlas/atlas.html",
        "odylith/compass/compass.html",
        "odylith/index.html",
    ):
        assert (tmp_path / required_file).is_file()
    assert len(list((tmp_path / "odylith/atlas/source").glob("*.svg"))) == len(payload["diagrams"])
    assert len(list((tmp_path / "odylith/atlas/source").glob("*.png"))) == len(payload["diagrams"])
    for banned in (
        "understand Pipeline",
        "connect and pushes",
        "Question Question",
        "This shapes the default transforms Impact:",
        "sentence fragment leaked after understand",
        "greenfield proposal confirmed completion failed",
    ):
        assert banned not in generated_payload
        assert banned not in visible_surface_payload


def test_greenfield_create_completes_compound_public_response_path_under_sixty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(PUBLIC_RESPONSE_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    rc, payload, elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a regional response workspace",
    )
    generated_payload = _generated_source_payload(tmp_path)
    visible_surface_payload = _generated_visible_surface_payload(tmp_path)
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    proposal = accepted["proposal"]
    first_path = proposal["semantic_model"]["first_path_contract"]
    sequence = next(row for row in proposal["diagrams"] if row["title"] == "First Path Sequence")
    sequence_source = sequence["mermaid_source"].casefold()

    assert rc == 0
    assert elapsed < POST_CONFIRM_WHOLE_PROJECT_BUDGET_SECONDS
    assert payload["validation_gate"]["status"] == "passed"
    assert generated_semantic_slop_issues(payload) == []
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 5
    assert len(payload["diagrams"]) == 6
    assert len(first_path["events"]) == 4
    assert first_path["visible_result"] == "the incident record updates to reflect the new interventions and a revised projection"
    assert [(row["action"], row["visible_result"]) for row in first_path["events"]] == [
        ("sees", False),
        ("drills", False),
        ("allocates", False),
        ("updates", True),
    ]
    assert "A regional coordinator drills into the trend" in json.dumps(first_path["events"])
    for term in ("allocates", "flags", "revised projection"):
        assert term in sequence_source
    assert "decision support" in generated_payload.casefold()
    for required_file in (
        "odylith/radar/radar.html",
        "odylith/registry/registry.html",
        "odylith/atlas/atlas.html",
        "odylith/compass/compass.html",
        "odylith/index.html",
    ):
        assert (tmp_path / required_file).is_file()
    for banned in (
        "confirmed Atlas flowchart `First Path Sequence` collapses the first path into too few events",
        "greenfield post-confirm completion failed",
        "has mid-sentence capitalization drift near `Their`",
        "flaging",
        "one full loop",
        "until the first outcome works for a representative user waits",
        "The public response workspace components come from product systems named in the accepted product direction: Incident.",
        "Do not expand beyond seeing an area where signal growth and capacity pressure are accelerating past a threshold and drilling into the trend until",
    ):
        assert banned not in generated_payload
        assert banned not in visible_surface_payload


def test_greenfield_create_rerun_replaces_previous_greenfield_workstreams_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(MULTI_ACTOR_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    first_rc, first_payload, first_elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a learner choice practice journal",
    )
    old_ids = {row["idea_id"] for row in first_payload["backlog"]}

    revised_text = MULTI_ACTOR_CONFIRMED_INTENT_TEXT.replace(
        "- Learner, a child aged eight to ten",
        "- Child learner, a kid aged eight to ten",
    )
    intent_path.write_text(revised_text, encoding="utf-8")
    second_rc, second_payload, second_elapsed = _run_confirmed_create_main(
        tmp_path,
        capsys,
        prompt="Draft a greenfield proposal for a learner choice practice journal",
    )
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
        rc, payload, elapsed = _run_confirmed_create_main(
            tmp_path,
            capsys,
            prompt="Draft a greenfield proposal for a learner choice practice journal",
        )
        elapsed_runs.append(elapsed)
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
