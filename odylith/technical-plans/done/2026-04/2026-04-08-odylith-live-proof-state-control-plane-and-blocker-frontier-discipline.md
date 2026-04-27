Status: Done

Created: 2026-04-08

Updated: 2026-04-08

Backlog: B-062

Goal: Add one authoritative proof-state control plane that keeps live blocker
lanes pinned to the current blocker, failure fingerprint, frontier phase,
evidence tier, deployment truth, and falsification memory across tracked truth,
runtime memory, grounded packets, diagnosis surfaces, and answer-time claim
language.

Assumptions:
- Tracked truth in Casebook and plans is the right place to define blocker
  identity, first failing phase, and clearance condition when those fields are
  present.
- Runtime proof memory is the right place to remember live attempts, repeated
  fingerprints, deployment truth, and last falsification without mutating
  source markdown silently.
- The first landing can stay additive if new consumers treat missing
  `proof_state` as absent instead of required.

Constraints:
- Do not keep growing red-zone coordinator files in place; extract proof-state
  helpers out of `delivery_intelligence_engine.py`, `tribunal_engine.py`, and
  `odylith_context_engine_session_packet_runtime.py`.
- Keep deterministic behavior complete and authoritative even when provider
  enrichment is unavailable.
- Reuse `.odylith/runtime/odylith-proof-surfaces.v1.json` rather than inventing
  another runtime memory file for the same concept.
- Do not auto-reopen or mutate Casebook markdown on repeated fingerprints; the
  runtime may re-pin the same bug without silently rewriting source truth.

Reversibility: The proof-state family remains additive. The helper package,
payload fields, and ledger section can be removed cleanly if a later contract
revision replaces this first landing.

Boundary Conditions:
- Scope includes source-of-truth governance updates, proof-state helper
  modules, additive payload fields, runtime ledger persistence, shared readout
  rendering, and claim-guard enforcement.
- Scope excludes changing live deploy orchestration, hosted runner behavior,
  or external provider semantics.

Related Bugs:
- [CB-077](../../casebook/bugs/2026-04-08-live-proof-lanes-do-not-pin-the-primary-blocker-frontier-or-falsification-memory.md)

## Learnings
- [x] The first live-proof lane needs one authoritative `lane_id`; when more
      than one blocker candidate survives, the product now surfaces ambiguity
      instead of picking a winner by vibes.
- [x] Runtime proof memory needs both blocker identity and deployment-truth
      fields; a branch being pushed is not the same as the hosted failing path
      actually using that code.
- [x] Claim enforcement must distinguish code-only, preview, deployed, and
      live states without flattening partial progress into one generic warning.

## Must-Ship
- [x] Create a dedicated proof-state helper package and shared contract enums.
- [x] Add Casebook proof-lane metadata parsing and proof-state resolution
      precedence.
- [x] Persist live-proof lane memory in
      `.odylith/runtime/odylith-proof-surfaces.v1.json`.
- [x] Add additive `proof_state` fields to delivery scopes, operator queue
      items, Tribunal case rows, and grounded packets.
- [x] Reuse the same bug or case row on repeated live fingerprints and mark
      prior fixes as falsified in runtime state.
- [x] Add shared control-panel shaping for shell, Compass, Registry, Casebook,
      and packet consumers.
- [x] Add chatter claim enforcement so unqualified `fixed`, `cleared`, or
      `resolved` is blocked below `live_verified`.

## Should-Ship
- [x] Add proof-drift warnings when the same blocker remains open but recent
      work skews toward `observability`, `governance`, or `test_hardening`.
- [x] Carry deployment truth as `local_head`, `pushed_head`,
      `published_source_commit`, `runner_fingerprint`, and
      `last_live_failing_commit`.
- [x] Keep packet rendering compact and fixed-shape when one proof lane
      resolves cleanly, and explicit about ambiguity when it does not.

## Defer
- [x] Broad workflow automation around live deploy retries stays out of scope.
- [x] Provider-only explanation embellishments remain secondary to the
      deterministic proof-state contract.

## Success Criteria
- [x] One resolved proof lane produces the same blocker, fingerprint, frontier,
      and evidence-tier readout everywhere Odylith surfaces it.
- [x] Repeated live failure fingerprints no longer look like a new bug.
- [x] Hosted proof only counts as cleared when the run advances past the
      previous failing phase.
- [x] Claim enforcement blocks misleading live-fix language while preserving
      truthful partial-progress phrasing.
- [x] Focused tests cover normalization, repeated-fingerprint reuse, frontier
      advancement, drift detection, and rendering.

## Non-Goals
- [x] Replacing existing workstream, bug, or component source files with
      runtime-generated truth.
- [x] Turning proof-state into a provider-dependent subsystem.

## Open Questions
- [x] No B-062-scoped open question remains. Event normalization now carries
      enough structured fields for work-category drift detection in the first
      landing.

## Impacted Areas
- [x] [2026-04-08-odylith-live-proof-state-control-plane-and-blocker-frontier-discipline.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-odylith-live-proof-state-control-plane-and-blocker-frontier-discipline.md)
- [x] [2026-04-08-live-proof-lanes-do-not-pin-the-primary-blocker-frontier-or-falsification-memory.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-08-live-proof-lanes-do-not-pin-the-primary-blocker-frontier-or-falsification-memory.md)
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/proof-state/CURRENT_SPEC.md)
- [x] [FORENSICS.v1.json](/Users/freedom/code/odylith/odylith/registry/source/components/proof-state/FORENSICS.v1.json)
- [x] [odylith-live-proof-state-control-plane.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-live-proof-state-control-plane.mmd)
- [x] [diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [x] [delivery_intelligence_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/delivery_intelligence_engine.py)
- [x] [operator_readout.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/operator_readout.py)
- [x] [tribunal_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/reasoning/tribunal_engine.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [odylith_context_engine_projection_surface_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_surface_runtime.py)
- [x] [dashboard_shell_links.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/dashboard_shell_links.py)
- [x] [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)
- [x] [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [compass_runtime_payload_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py)
- [x] [render_casebook_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_casebook_dashboard.py)
- [x] [odylith_chatter_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/odylith_chatter_runtime.py)
- [x] [test_proof_state_runtime.py](/Users/freedom/code/odylith/tests/unit/runtime/test_proof_state_runtime.py)
- [x] [test_delivery_intelligence_engine.py](/Users/freedom/code/odylith/tests/unit/runtime/test_delivery_intelligence_engine.py)
- [x] [test_tribunal_engine.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tribunal_engine.py)
- [x] [test_tooling_context_packet_builder.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tooling_context_packet_builder.py)
- [x] [test_compass_dashboard_runtime.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_dashboard_runtime.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)
- [x] [test_render_registry_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_registry_dashboard.py)
- [x] [test_render_casebook_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_casebook_dashboard.py)
- [x] [test_odylith_assist_closeout.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_assist_closeout.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_proof_state_runtime.py tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_update_compass.py`
      (`109 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_update_compass.py`
      (`63 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_smoke.py`
      (`6 passed`)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
      (passed)
- [x] `git diff --check`
      (passed)

## Current Outcome
- [x] `B-062` is closed for `v0.1.11`.
- [x] Proof-state is now a first-class additive contract wired through
      delivery, Tribunal, grounded packets, Compass, Registry, Casebook,
      shell, and chatter instead of being narrated separately by each surface.
- [x] Same-fingerprint live failures now preserve blocker identity, explicit
      falsification memory, and truthful claim scope instead of collapsing into
      adjacent-progress optimism.
- [x] The remaining ambiguity behavior is intentional, explicit, and
      non-blocking: when more than one blocker survives resolution, Odylith now
      says so directly instead of pretending there is one authoritative seam.
