- Bug ID: CB-077

- Status: Closed

- Fixed: 2026-04-08

- Created: 2026-04-08

- Severity: P1

- Reproducibility: High

- Type: Product

- Proof Lane ID: proof-state-control-plane

- Linked Workstream: B-062

- Current Blocker: No shared proof-state lane keeps the primary blocker,
  frontier, and falsification memory pinned across delivery, Tribunal,
  grounded packets, shell previews, Compass, Registry, and chatter.

- Failure Fingerprint: same live failure fingerprint can reproduce while
  adjacent local progress still reads like blocker movement.

- First Failing Phase: status synthesis

- Clearance Condition: One coherent `proof_state` lane is carried across
  delivery scopes, Tribunal, packets, shell, Compass, Registry, and chatter,
  and claim guard blocks unqualified live-fix language below `live_verified`.

- Current Proof Status: live_verified

- Description: Odylith can stay broadly grounded on the correct workstream and
  repo slice while still failing to keep one live deploy or rehearsal blocker
  pinned across delivery snapshots, Tribunal cases, grounded packets, Compass,
  shell previews, Registry, and chatter. In that state the product knows the
  neighborhood, but it does not forcefully preserve the one thing that matters:
  the current blocker fingerprint and the proof frontier that must move before
  the claim can change.

- Impact: Operators can mistake code fixes, preview proof, observability
  improvements, or CLI polish for progress on the live blocker even when the
  same hosted failure fingerprint is still the frontier. That weakens proof
  discipline, muddles status language, and encourages sidecar work while the
  primary seam is unchanged.

- Components Affected: `src/odylith/runtime/governance/delivery_intelligence_engine.py`,
  `src/odylith/runtime/reasoning/tribunal_engine.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_session_packet_runtime.py`,
  `src/odylith/runtime/surfaces/dashboard_shell_links.py`,
  `src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/orchestration/odylith_chatter_runtime.py`, Casebook
  bug metadata parsing, shared operator readouts, and the runtime proof-surfaces
  ledger.

- Environment(s): Maintainer and consumer live deploy or rehearsal lanes where
  the same failure fingerprint can reproduce across multiple hosted attempts.

- Root Cause: Odylith has no single proof-state control plane tying tracked bug
  or plan truth to runtime live-proof memory. Blocker identity, falsification
  memory, frontier movement, deployment truth, and answer-time claim tier are
  split across heuristics or simply absent, so the product can stay grounded
  without staying proof-disciplined.

- Solution: Add one additive `proof_state` contract keyed by `lane_id`, make
  Casebook or plan metadata authoritative for blocker identity and clearance
  condition, persist live-proof memory in `.odylith/runtime/odylith-proof-surfaces.v1.json`,
  reuse the same bug or case on repeated fingerprints, and add claim lint so
  "fixed" only means live-cleared when the hosted ladder advances beyond the
  prior failing phase.

- Verification: Fixed on 2026-04-08. `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py
  tests/unit/runtime/test_odylith_context_engine_store.py
  tests/unit/runtime/test_context_grounding_hardening.py
  tests/unit/runtime/test_context_engine_release_resolution.py
  tests/unit/runtime/test_context_engine_topology_contract.py
  tests/unit/runtime/test_tooling_context_packet_builder.py
  tests/unit/runtime/test_tooling_context_routing.py
  tests/unit/runtime/test_odylith_context_cache.py
  tests/unit/runtime/test_odylith_memory_areas.py
  tests/unit/runtime/test_odylith_runtime_surface_summary.py
  tests/unit/runtime/test_grounding_component_priority.py
  tests/unit/runtime/test_casebook_bug_index.py
  tests/unit/runtime/test_proof_state_runtime.py
  tests/unit/test_cli.py` passed with `193 passed`; `PYTHONPATH=src python3 -m
  pytest -q tests/integration/runtime/test_surface_browser_smoke.py
  tests/integration/runtime/test_surface_browser_deep.py -k "context or
  governance or bootstrap or proof or release"` passed with `4 passed`;
  `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --runtime-mode
  standalone --proceed-with-overlap` passed; `PYTHONPATH=src python3 -m
  odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
  passed; `PYTHONPATH=src python3 -m odylith.cli architecture --repo-root .
  src/odylith/runtime/context_engine/odylith_context_engine_projection_surface_runtime.py`
  now reports `diagram_watch_gap_count: 0`; and `git diff --check` passed.

- Prevention: Any live-proof lane must show one explicit current blocker,
  failure fingerprint, first failing phase, clearance condition, evidence tier,
  and last falsification instead of letting each consumer infer those fields
  differently or not at all.

- Detected By: Maintainer retrospective on 2026-04-08 after a live SIM3 lane
  stayed stuck at the same hosted blocker while surrounding local progress
  narratives drifted.

- Failure Signature: The same hosted failure fingerprint reappears after a
  claimed fix, but Odylith surfaces still let adjacent improvements read as
  blocker progress because they do not carry a shared proof frontier or
  falsification memory.

- Trigger Path: 1. Diagnose a live blocker. 2. Land a code-only or preview-only
  fix. 3. Reproduce the same hosted fingerprint. 4. Open or refresh packets,
  shell previews, Compass, Registry, or chatter. 5. Observe that the product
  stays broadly grounded but does not keep the unchanged blocker seam dominant.

- Ownership: Delivery Intelligence, Tribunal, Context Engine packet shaping,
  shared surface proof routing, Casebook proof-lane metadata, and Odylith
  chatter claim policy.

- Timeline: The gap became obvious in hosted deploy proof on 2026-04-08. The
  product had enough context to stay in the right workstream and runtime lane,
  but it still lacked one durable frontier model for repeated live
  falsification.

- Blast Radius: Any operator or coding agent relying on Odylith to keep live
  deploy or rehearsal work honest after the first hosted failure reproduces.

- SLO/SLA Impact: No direct outage, but a correctness and trust risk in the
  product's most important live-proof workflows.

- Data Risk: Low source-of-truth corruption risk; high risk of misleading
  operator status language and misprioritized work.

- Security/Compliance: None directly.

- Invariant Violated: Odylith should not let "fixed in code", "preview-tested",
  or sidecar improvements masquerade as live blocker clearance when the hosted
  frontier is unchanged.

- Workaround: Maintain the blocker, fingerprint, and clearance rule manually in
  human memory and refuse to treat anything as cleared until the hosted ladder
  advances. That is precisely the discipline the product should be enforcing.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When the same live fingerprint returns, keep the same seam
  pinned and downgrade any prior blocker-resolution claim to falsified unless
  the hosted frontier actually moved.

- Preflight Checks: Inspect `B-062`, the proof-state component spec, the
  delivery-intelligence and Tribunal contracts, the Context Engine packet
  finalizers, the shell proof-link helpers, and the current proof-surfaces
  runtime ledger.

- Regression Tests Added: `test_proof_state_runtime.py`,
  `test_delivery_intelligence_engine.py`, `test_tribunal_engine.py`,
  `test_tooling_context_packet_builder.py`, `test_render_tooling_dashboard.py`,
  `test_render_registry_dashboard.py`, `test_render_compass_dashboard.py`,
  `test_render_casebook_dashboard.py`, `test_odylith_assist_closeout.py`,
  `test_context_engine_release_resolution.py`,
  `test_context_engine_topology_contract.py`, and the focused browser-backed
  surface proofs for context, governance, bootstrap, proof, and release flows.

- Monitoring Updates: Watch for repeated fingerprints that keep the same
  blocker open, queue rows that create a fresh case instead of reusing the same
  seam, and status text that says `fixed` or `cleared` without live frontier
  advancement.

- Residual Risk: Ambiguous multi-blocker lanes still surface explicit
  ambiguity instead of a forced summary. That is the intended non-blocking
  product behavior for this slice; no single-lane proof-state gap remains.

- Related Incidents/Bugs:
  no related bug found

- Version/Build: Odylith product repo working tree on 2026-04-08.

- Config/Flags: Live deploy or rehearsal lanes where hosted proof and local
  branch state can diverge.

- Customer Comms: Tell operators the product is adding a live-proof control
  panel so code-only and preview-only progress remain visible without being
  mislabeled as live blocker clearance.

- Code References: `src/odylith/runtime/governance/delivery_intelligence_engine.py`,
  `src/odylith/runtime/reasoning/tribunal_engine.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_session_packet_runtime.py`,
  `src/odylith/runtime/orchestration/odylith_chatter_runtime.py`

- Runbook References: `odylith/registry/source/components/proof-state/CURRENT_SPEC.md`,
  `odylith/registry/source/components/tribunal/CURRENT_SPEC.md`,
  `odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md`

- Fix Commit/PR: pending
