# Delivery Intelligence
Last updated: 2026-04-09


Last updated (UTC): 2026-04-09

## Purpose
Delivery Intelligence is Odylith's scope-synthesis engine. It fuses governed
repo truth, runtime evidence, Tribunal outputs, and proof-state signals into
one bounded delivery snapshot that sync, shell, Registry, grounded packets,
and chatter can consume without rebuilding divergent summaries.

## Scope And Non-Goals
### Delivery Intelligence owns
- normalized delivery snapshots across workstream, component, diagram, and bug
  scopes
- severity, scenario, and operator-readout shaping for delivery consumers
- integration of Tribunal case rows and proof-state fields into the shared
  snapshot contract
- persisted delivery artifact generation for governed surfaces
- deterministic fallback behavior when richer reasoning artifacts are absent

### Delivery Intelligence does not own
- first-principles diagnosis; that belongs to [Tribunal](../tribunal/CURRENT_SPEC.md)
- live proof-lane resolution policy; that belongs to [Proof State](../proof-state/CURRENT_SPEC.md)
- next-action admissibility or hard execution gating; that belongs to
  [Execution Governance](../execution-governance/CURRENT_SPEC.md)
- final surface rendering or visual design
- mutating backlog, casebook, or component truth directly

## Developer Mental Model
- Delivery Intelligence is the product's shared posture layer.
- It should be the one place that decides what scope is actionable, what risk
  class applies, what proof or reasoning references matter, and which compact
  readouts downstream consumers receive.
- Shell, packets, Registry, and chatter should consume this artifact instead of
  rerunning their own ad-hoc scope interpretation.
- When proof-state is present, Delivery Intelligence should carry that lane
  forward faithfully rather than flattening it into generic "clearance"
  language.
- Execution Governance may consume delivery snapshots as evidence input, but
  Delivery Intelligence must not silently become the product's action-policy
  owner just because it has good posture data.

## Runtime Contract
### Owning modules
- `src/odylith/runtime/governance/delivery_intelligence_engine.py`
  Main snapshot builder and persisted delivery artifact writer.
- `src/odylith/runtime/delivery/delivery_intelligence_narrator.py`
  Compact narrative shaping and bounded summarization helpers.
- `odylith/runtime/delivery_intelligence.v4.json`
  The persisted delivery artifact consumed by product surfaces and exact
  packets.

### Primary consumers
- `src/odylith/runtime/reasoning/tribunal_engine.py`
- `src/odylith/runtime/context_engine/tooling_context_packet_builder.py`
- `src/odylith/runtime/surfaces/render_registry_dashboard.py`
- `src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py`
- `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`
- `src/odylith/runtime/intervention_engine/delivery_runtime.py`

## Snapshot Contract
Delivery snapshots may include:
- normalized scope identity and topology
- scenario, severity, and operator action posture
- `scope_signal` with rung, token, reasons, caps, `promoted_default`, and
  provider-neutral `budget_class`
- governance lag and traceability posture
- Tribunal case summaries and queue rows
- `proof_state`, `proof_state_resolution`, `claim_guard`, and related proof
  refs when one live blocker lane is in scope
- linked evidence refs for Compass, Registry, Casebook, and Atlas consumers

The snapshot is additive. Missing richer diagnosis or proof-state artifacts
must degrade to explicit absence rather than silent invention.

## Scope Signal Ladder Contract
Delivery Intelligence owns the product's one shared scope-escalation contract.
Every scope snapshot may carry:
- `scope_signal.rung`
- `scope_signal.token`
- `scope_signal.label`
- `scope_signal.reasons`
- `scope_signal.caps`
- `scope_signal.promoted_default`
- `scope_signal.budget_class`
- `scope_signal.features`

The rung contract is deterministic and auditable:
- `R0 suppressed_noise`
- `R1 background_trace`
- `R2 verified_local`
- `R3 active_scope`
- `R4 actionable_priority`
- `R5 blocking_frontier`

Default rule highlights:
- governance-only local churn caps at `R1`
- broad fanout rows cap at `R1`
- generated-only churn caps at `R0`
- verified local movement reaches `R2`
- real implementation or decision evidence reaches `R3`
- warning, stale-authority, or conflict posture promotes to `R4`
- proof-state blocker or unsafe closeout promotes to `R5`

Delivery Intelligence must compute that ladder before operator-readout shaping
or downstream ordering so Compass, Radar, Registry, Atlas, shell, and chatter
all consume one escalation truth instead of re-deriving urgency locally.

## What To Change Together
- If scope posture logic changes, update the delivery engine, downstream
  delivery consumers, and the persisted artifact together.
- If ladder rung thresholds or budget classes change, update Compass, Radar,
  Registry, Atlas, shell/chatter consumers, specs, and browser proof together.
- If proof-state fields change, keep the additive delivery snapshot contract in
  sync with Proof State and the surface consumers.
- If Tribunal queue rows gain new posture fields, Delivery Intelligence should
  preserve them so shell and chatter do not lose diagnostic fidelity.

## Composition
- [Registry](../registry/CURRENT_SPEC.md) provides component inventory and
  forensic coverage signals.
- [Radar](../radar/CURRENT_SPEC.md) and [Casebook](../casebook/CURRENT_SPEC.md)
  provide governed workstream and bug truth.
- [Tribunal](../tribunal/CURRENT_SPEC.md) supplies diagnosis and ranked case
  rows.
- [Proof State](../proof-state/CURRENT_SPEC.md) sharpens live-blocker frontier,
  falsification memory, and claim-tier posture.
- [Execution Governance](../execution-governance/CURRENT_SPEC.md) consumes the
  shared posture, scope-signal ladder, and proof-aware delivery readout when
  deciding whether the next move is admissible.
- [Odylith Chatter](../odylith-chatter/CURRENT_SPEC.md) consumes delivery
  snapshots for bounded ambient and closeout narration.

## Validation Playbook
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_delivery_intelligence_engine.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_tooling_context_packet_builder.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_tooling_dashboard.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-08: Promoted Delivery Intelligence into first-class Registry truth so Tribunal-trigger, proof-state, shell, packet, and chatter consumers stop depending on an untracked scope-synthesis seam. (Plan: [B-062](odylith/radar/radar.html?view=plan&workstream=B-062))
- 2026-04-09: Added the shared Scope Signal Ladder so Delivery Intelligence now owns one deterministic contract for scope visibility, promotion, and provider-neutral compute budgets across Compass, Radar, Registry, Atlas, and shell consumers. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071))
- 2026-04-09: Clarified the boundary that Delivery Intelligence supplies shared posture and scope signals, while Execution Governance owns next-action admissibility and execution policy. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
