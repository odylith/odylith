# Compass
Last updated: 2026-04-08


Last updated (UTC): 2026-04-08

## Purpose
Compass is Odylith's execution, decision, and runtime-posture surface. It turns
the local timeline stream plus linked governance artifacts into an operator view
of what changed, what is active, what risks or cases dominate, and what the
standup-level summary should be.

## Scope And Non-Goals
### Compass owns
- The local Codex/Odylith timeline stream.
- Runtime snapshot generation and history retention.
- Timeline grouping and transaction shaping.
- The standup brief pipeline, including deterministic fallback narration.
- The Compass HTML shell and bundle.

### Compass does not own
- The authoritative backlog, component inventory, or bug markdown. It projects
  them from Radar, Registry, and Casebook inputs.
- Shell-level routing. Dashboard owns that.

## Developer Mental Model
- Compass is both a live stream and a derived runtime snapshot surface.
- `odylith/compass/runtime/codex-stream.v1.jsonl` is append-oriented local
  event truth for the surface.
- Everything else in `odylith/compass/runtime/` is derived from that stream and
  linked governance sources.
- The standup brief is not allowed to disappear just because the AI provider is
  unavailable; deterministic local narration is the baseline.

## Runtime Contract
### Runtime inputs
- `odylith/compass/runtime/codex-stream.v1.jsonl`
- `odylith/radar/source/INDEX.md`
- `odylith/technical-plans/INDEX.md`
- `odylith/casebook/bugs/INDEX.md`
- `odylith/radar/traceability-graph.v1.json`
- `odylith/atlas/source/catalog/diagrams.v1.json`

### Generated artifacts
- `odylith/compass/compass.html`
- `odylith/compass/compass-payload.v1.js`
- `odylith/compass/compass-app.v1.js`
- `odylith/compass/runtime/current.v1.json`
- `odylith/compass/runtime/current.v1.js`
- `odylith/compass/runtime/history/index.v1.json`
- `odylith/compass/runtime/history/restore-pins.v1.json`
- `odylith/compass/runtime/history/YYYY-MM-DD.v1.json`
- `odylith/compass/runtime/history/archive/YYYY-MM-DD.v1.json.gz`
- `odylith/compass/runtime/history/embedded.v1.js`

### Owning modules
- `src/odylith/runtime/surfaces/render_compass_dashboard.py`
  Render facade, argument parsing, runtime refresh, and shell bundle output.
- `src/odylith/runtime/surfaces/compass_dashboard_base.py`
  Low-churn path, markdown, git, and parsing helpers.
- `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`
  High-churn runtime payload, digest, and history builders.
- `src/odylith/runtime/surfaces/compass_dashboard_shell.py`
  Compass shell HTML/CSS composition.
- `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`
  AI/deterministic standup brief pipeline and cache.
- `src/odylith/runtime/surfaces/update_compass.py`
  Statement capture and surface refresh helper.
- `src/odylith/runtime/surfaces/restore_compass_history.py`
  Explicit restore command for archived Compass history dates.
- `src/odylith/runtime/surfaces/watch_prompt_transactions.py`
  Prompt-transaction watcher integration.

## Command Surface
Compass is exposed through the top-level CLI:
- `odylith compass log`
  Append one timeline event.
- `odylith compass update`
  Capture update statements into timeline and standup inputs.
- `odylith compass restore-history`
  Rehydrate archived daily history snapshots back into the active Compass calendar.
- `odylith compass watch-transactions`
  Observe prompt transactions and refresh Compass as activity occurs.

The render step itself is part of `odylith sync` and surface refresh workflows.

## Runtime Pipeline
### 1. Collect evidence
Compass loads backlog, plan, bug, diagram, and stream inputs and resolves
component/workstream linkage.

### 2. Select source events
`compass_dashboard_runtime.py` ranks recent events by event kind, workstream
signal, and source-vs-generated artifact mix so implementation and decision
events dominate the visible narrative.

### 3. Build runtime payload
The runtime builder shapes:
- current workstream state
- recent activity and grouped transactions
- bug and plan summaries
- freshness posture
- product-repo self-host posture
- Tribunal or operator readout slices
- standup brief inputs

### 4. Write snapshots and history
`refresh_runtime_artifacts(...)` writes current snapshot files, keeps a 15-day
active daily history lane by default, compresses older daily snapshots into
`history/archive/`, and honors explicit restore pins for older dates that must
remain active.

### 5. Render shell
The shell renderer externalizes the payload and control script into the checked
in surface bundle.

## Standup Brief Contract
`compass_standup_brief_narrator.py` owns the standup brief policy:
- AI-authored narration is allowed when Odylith can resolve a runnable shared
  reasoning provider. By default Compass prefers the active local coding agent
  CLI when one is available and only falls back to explicit endpoint config
  when that is the configured path.
- Invalid, empty, deferred, or unavailable AI output must degrade to a
  deterministic local brief.
- The local cache lives at `.odylith/compass/standup-brief-cache.v5.json`.

The intent is that Compass always produces an understandable standup artifact,
even when the shared reasoning provider is down.

## Benchmark-Facing Slice Contract

- When benchmark or focused regression work targets
  `compass_brief_freshness`, the bounded slice is the Compass runtime builder,
  the standup brief narrator, focused Compass tests, this component spec, and
  `odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`.
- Those proof slices must not widen into install, repair, or context-engine
  guidance unless a required path or focused validator points there directly.
- Warm and cold benchmark packets should choose the same truthful Compass slice
  so cache posture changes timing, not the first-pass support surface.

## Timeline Semantics
Compass distinguishes:
- durable implementation and decision events
- operator statements
- bug and plan updates
- self-host posture transition and failed preflight statements
- local changes
- transaction boundaries and grouped activity

Generated-only narrative noise is intentionally deprioritized so dashboard
churn does not drown out meaningful implementation evidence.

## Snapshot-Age Contract
- Compass rolling windows, per-day timelines, and audit-hour detail are anchored
  to the loaded runtime snapshot timestamp, not the browser wall clock.
- If the loaded runtime snapshot is materially stale, Compass must surface that
  explicitly as a warning with the snapshot age and timestamp; it must not
  silently render recent day buckets as if they were live empty days.
- Provider-backed standup narration stays opportunistic and manual-refresh
  bounded. Local timeline, workstream, risk, and KPI readouts must remain
  understandable without spending provider credits.
- `shell-safe` may reuse exact global brief cache or request provider-backed
  global `24h`/`48h` narration opportunistically, but it keeps scoped provider
  warming disabled and must still degrade cleanly to deterministic narration if
  the provider is unavailable or invalid.
- Explicit `odylith dashboard refresh --repo-root . --surfaces compass
  --compass-refresh-profile full` is the deeper refresh contract. That path
  keeps the five-minute runtime reuse clamp, but any reused payload must
  already satisfy the requested deep-refresh truth contract. Full refresh may
  reuse exact current-packet validated AI brief cache as a bounded recovery
  path, and must fail render rather than writing deterministic or stale
  fallback brief state on a passing run.
- When the top-level shell refreshes without rerendering Compass, ordinary
  stale-snapshot disclosure belongs inside Compass itself.
- The shell should reserve runtime-status cards for failed deeper-refresh
  state or other cross-surface posture the Compass frame cannot already
  explain.
- Any shell-facing Compass freshness status must still derive from the current
  Compass runtime snapshot rather than pretending the shell wrapper refresh
  updated Compass data.
- Live history augmentation for stale rolling windows may fetch only retained
  or explicitly restored history dates. Off-retention days must stay absent
  rather than triggering browser-visible 404 requests.

## Traceability Risk Projection
- Compass consumes shared Radar `warning_items`, but default risk rows are
  reserved for operator-facing `warning` and `error` diagnostics.
- Maintainer-facing info diagnostics, including autofix conflict notes, should
  remain visible in the underlying traceability artifacts without showing up as
  primary Compass risk rows.

## Self-Host Readout Contract
- Compass runtime payload now carries `self_host` with:
  `repo_role`, `posture`, `runtime_source`, `release_eligible`,
  `pinned_version`, and `active_version`.
- When the public product repo is detached, diverged, or incomplete, Compass
  must surface that as an explicit risk row rather than leaving self-host drift
  implicit.
- A pinned but unverified local wrapper runtime must also surface as an
  explicit self-host risk; version alignment alone is not sufficient.
- Install/runtime lifecycle transitions and failed local self-host preflight
  checks are allowed to append concise timeline statements so Compass history
  shows when the product repo drifted in or out of valid dogfood posture.

## Intent Behind Compass
Compass exists so a developer or operator can answer:
- what happened recently
- which workstreams are actually moving
- what state the product thinks it is in right now
- what the standup summary should sound like

It is the runtime narrative surface, not the canonical source of backlog truth
or component definitions.

## What To Change Together
- New event kind:
  update log/update/watch flows, runtime event ranking, and shell rendering.
- New runtime snapshot field:
  update current snapshot JSON, history serialization, and shell payload
  consumption together.
- New standup section or brief contract:
  update narrator validation, deterministic fallback, and shell rendering at
  the same time.
- New freshness or activity heuristic:
  update runtime scoring, history output, and any dependent tests together.

## Failure And Recovery Posture
- Missing required governance inputs should fail Compass render rather than
  producing a misleading runtime snapshot.
- AI brief failures should degrade to deterministic narration, not to a missing
  brief.
- Exception: explicit Compass `full` refresh is fail-closed. That path must not
  report success with deterministic local brief output or stale fallback state.
- History retention should archive older daily snapshots without touching the
  live stream, and restore should remain explicit.
- Compass stream noise should never be treated as authoritative implementation
  evidence unless the event kind and artifact mix justify it.

## Validation Playbook
### Compass
- `odylith compass update --repo-root . --help`
- `odylith compass restore-history --repo-root . --help`
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root . --output odylith/compass/compass.html`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_dashboard_base.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_standup_brief_narrator.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-20 · Decision:** Successor created: B-255 reopens B-253 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/compass/CURRENT_SPEC.md +1 more
- **2026-03-04 · Implementation:** Shipped Registry dashboard rendering plus governance and traceability sync updates, and refreshed generated Radar, Atlas, and Compass shells.
  - Evidence: src/odylith/runtime/governance/sync_workstream_artifacts.py, src/odylith/runtime/surfaces/render_backlog_ui.py +2 more
- **2026-03-04 · Decision:** Standardized governance visibility around Registry as the canonical component audit surface across Radar, Atlas, and Compass.
  - Evidence: src/odylith/runtime/governance/sync_workstream_artifacts.py, src/odylith/runtime/surfaces/render_backlog_ui.py +2 more
- **2026-03-03 · Implementation:** Implemented lineage fields and relation edges across validation, reciprocal backfill, traceability graph, and Radar/Compass rendering.
  - Evidence: odylith/radar/source/INDEX.md, odylith/technical-plans/INDEX.md +2 more
- **2026-03-03 · Decision:** kickoff B-034 lineage model with successor-first reopen policy and typed relation semantics.
  - Evidence: odylith/radar/source/INDEX.md, odylith/technical-plans/INDEX.md +2 more
- **2026-03-01 · Implementation:** Added Codex decision/implementation stream ingestion into Compass timeline audits and shipped logging skill contract.
  - Evidence: odylith/skills/compass-timeline-stream/SKILL.md, src/odylith/runtime/common/log_compass_timeline_event.py
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Added Odylith-owned Compass runtime roots so the public repo can keep a first-class audit trail for product changes and validation events. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-03-27: Changed Compass history to a 15-day active window with compressed archived daily snapshots and an explicit restore-history command for older dates. (Plan: [B-003](odylith/radar/radar.html?view=plan&workstream=B-003))
- 2026-03-27: Added self-host posture payload, product-runtime risk surfacing, and posture-transition evidence for the public Odylith repo. (Plan: [B-004](odylith/radar/radar.html?view=plan&workstream=B-004))
- 2026-04-02: Anchored rolling windows and audit timelines to the loaded runtime snapshot time and added explicit stale-runtime warnings so old snapshots no longer masquerade as empty recent days. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-07: Aligned Compass traceability risk rows with Radar's shared operator-facing warning policy so maintainer autofix diagnostics stay in the artifacts instead of primary risk cards. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-05: Documented the bounded `compass_brief_freshness` benchmark slice so proof stays on Compass runtime, narrator, focused tests, and product-surface guidance instead of widening into unrelated install or repair surfaces. (Plan: [B-038](odylith/radar/radar.html?view=plan&workstream=B-038))
- 2026-04-08: Clarified that shell-host refresh truth must distinguish wrapper freshness from Compass child-runtime freshness so stale or failed deeper-refresh snapshots stay explicit on the Compass tab. (Plan: [B-060](odylith/radar/radar.html?view=plan&workstream=B-060))
- 2026-04-08: Locked explicit Compass `full` refresh to a fail-closed contract: the valid five-minute reuse clamp stays, but a passing rerender can reuse only deep-refresh-clean payloads and must never land on deterministic local brief output or stale fallback truth. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-08: Finalized stale-runtime disclosure to a single in-frame Compass warning for ordinary stale snapshots and bounded live-history backfill to retained or restored days so stale windows no longer spray 404 history fetches into the shell browser lane. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
