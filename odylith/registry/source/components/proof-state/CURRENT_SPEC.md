# Proof State

## Odylith Discipline Contract
- Proof State owns the Honesty facet. Odylith Discipline decisions must distinguish
  code-only, preview-only, validator-backed, hosted-proof, benchmark-proof,
  and release-proof claims before allowing stronger completion language.
- False proof clearance, false visible-UX claims, and public product claims
  without benchmark proof are release-blocking failures for v0.1.11.
Last updated: 2026-04-09


Last updated (UTC): 2026-04-09

## Purpose
Proof State is Odylith's live-proof control-plane contract. It keeps one
blocker lane pinned to the current blocker, failure fingerprint, first failing
phase, frontier movement, evidence tier, deployment truth, and falsification
memory across tracked governance truth, runtime memory, grounded packets,
diagnosis surfaces, and answer-time claim language.

## Scope And Non-Goals
### Proof State owns
- the additive `proof_state` payload contract
- `proof_status` and `work_category` enum policy
- resolution precedence between tracked truth and runtime live-proof memory
- the `live_proof_lanes` runtime-ledger section under
  `.odylith/runtime/odylith-proof-surfaces.v1.json`
- repeated-fingerprint falsification memory and same-lane reuse policy
- proof-drift detection and shared control-panel shaping
- claim-guard shaping for status language such as `fixed`, `cleared`, and
  `resolved`

### Proof State does not own
- authoritative bug or plan markdown
- execution of deploy or rehearsal steps
- provider-specific explanation logic
- shell or Compass visual design beyond the shared proof fields they consume

## Developer Mental Model
- Proof State is a split-authority system.
- Tracked truth in Casebook or plans owns blocker identity, first failing
  phase, and clearance condition when those fields are present.
- Runtime memory owns live attempts, last falsification, repeated-fingerprint
  count, frontier movement, and deployed-vs-local truth.
- Delivery Intelligence, Tribunal, Context Engine packets, Compass, shell,
  Registry, and chatter should all consume the same resolved lane rather than
  building separate proof summaries.
- Execution Engine consumes the resolved proof-state lane as evidence for
  admissibility and frontier posture; Proof State itself does not decide the
  next action.
- When Proof State surfaces a live blocker, unsafe closeout, or falsified
  claim frontier, that posture must dominate ordinary activity signals in
  Delivery Intelligence's shared Scope Signal Ladder.
- If more than one blocker survives resolution for the same lane, the product
  must surface ambiguity instead of inventing certainty.

## Runtime Contract
### Owning modules
- `src/odylith/runtime/governance/proof_state/contract.py`
  Enum and payload-shape helpers for proof-state consumers.
- `src/odylith/runtime/governance/proof_state/ledger.py`
  Runtime-ledger load and persist helpers for `live_proof_lanes`.
- `src/odylith/runtime/governance/proof_state/resolver.py`
  Split-authority resolution from Casebook or plan truth plus runtime proof
  memory into one lane-level contract.
- `src/odylith/runtime/governance/proof_state/readout.py`
  Shared control-panel shaping, drift warnings, and proof-link helpers.

### Primary consumers
- `src/odylith/runtime/governance/delivery_intelligence_engine.py`
- `src/odylith/runtime/governance/operator_readout.py`
- `src/odylith/runtime/reasoning/tribunal_engine.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_store.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_session_packet_runtime.py`
- `src/odylith/runtime/surfaces/dashboard_shell_links.py`
- `src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py`
- `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`
- `src/odylith/runtime/intervention_engine/conversation_runtime.py`

### Runtime memory
- `.odylith/runtime/odylith-proof-surfaces.v1.json`
  The existing proof-surfaces runtime ledger gains `live_proof_lanes`, keyed
  by `lane_id`, for last live run result, repeated-fingerprint count,
  deployment truth, and last falsification.

## Proof-State Contract
When one lane resolves cleanly, `proof_state` is additive and must include:
- `lane_id`
- `current_blocker`
- `failure_fingerprint`
- `first_failing_phase`
- `frontier_phase`
- `clearance_condition`
- `proof_status`
- `evidence_tier`
- `last_falsification`
- `allowed_next_work`
- `deprioritized_until_cleared`
- `linked_bug_id`
- `deployment_truth`

### Proof-status enum
- `diagnosed`
- `fixed_in_code`
- `unit_tested`
- `preview_tested`
- `deployed`
- `live_verified`
- `falsified_live`

### Work-category enum
- `primary_blocker`
- `adjacent_runtime`
- `observability`
- `governance`
- `test_hardening`

## Authority And Clearance Rules
- Explicit Casebook or plan fields win for blocker identity and clearance rule.
- Runtime proof memory wins for the latest live evidence and deployment truth.
- Heuristics may only fill missing fields and must mark the lane inferred.
- "Live cleared" means exactly one thing: the hosted ladder advanced beyond the
  prior failing phase.
- Reproducing the same failure fingerprint after a claimed fix marks the prior
  blocker-resolution hypothesis as falsified in runtime state.

## Drift And Claim Guard
- If the same fingerprint remains open and recent activity skews toward
  non-`primary_blocker` categories, the shared readout should emit a
  proof-drift warning.
- Claim guard must force three checks before unqualified `fixed`, `cleared`, or
  `resolved` wording:
  - is this the same fingerprint as before
  - did the hosted proof advance past the prior failing phase
  - is the claim code-only, preview-level, deployed, or actually live-verified

## Composition
- [Casebook](../casebook/CURRENT_SPEC.md) contributes blocker and proof-lane
  metadata when a bug owns the lane.
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md) carries
  proof-state into grounded packets.
- [Execution Engine](../execution-engine/CURRENT_SPEC.md) consumes the
  resolved lane when screening actions and deriving the current execution
  frontier.
- [Tribunal](../tribunal/CURRENT_SPEC.md) consumes proof-state for case reuse,
  falsification memory, and queue shaping.
- [Dashboard](../dashboard/CURRENT_SPEC.md) and [Compass](../compass/CURRENT_SPEC.md)
  render the shared control panel and proof links.
- [Odylith Chatter](../odylith-chatter/CURRENT_SPEC.md) uses claim guard so
  closeout language stays truthful about proof tier.

## Validation Playbook
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_proof_state_runtime.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_tribunal_engine.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_odylith_assist_closeout.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-09: Bound proof-state blocker posture into Delivery Intelligence's shared Scope Signal Ladder so live frontier or unsafe-closeout truth can outrank ordinary activity across Compass, Radar, Registry, Atlas, and shell consumers. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071))
- 2026-04-08: Promoted the live-proof blocker frontier, falsification memory, and claim-tier contract into a first-class Registry component so delivery, diagnosis, packets, shell, Compass, Registry, and chatter can share one authoritative proof-state lane. (Plan: [B-062](odylith/radar/radar.html?view=plan&workstream=B-062))
- 2026-04-09: Clarified that Proof State resolves blocker and claim-tier truth, while Execution Engine consumes that truth when deciding the next admissible move. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
