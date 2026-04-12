Status: In progress

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-091

Goal: Cut governed sync from a shared-nothing step runner into one session-hoisted
derivation engine that preserves the exact backlog, Registry, delivery-intelligence,
Atlas, Compass, Casebook, and shell outcomes while removing redundant read-model
rebuilds, path canonicalization loops, and unchanged-output rewrites.

Assumptions:
- The current sync correctness contract stays intact: same tracked source truth,
  same validation gates, same rendered bytes for identical repo state.
- Warm incremental syncs matter more than forced cold full rebuilds when judging
  operator UX, but the architecture must not make `--force --impact-mode full`
  less truthful.
- The fastest honest first wave is an in-process shared session because sync already
  dispatches hot steps in one Python process on the runtime fast path.

Constraints:
- Do not weaken Radar, Registry, Atlas, or Compass fail-closed validation to hit
  the latency target.
- Do not let filesystem stat metadata become the only freshness authority for
  cached results; content truth and generator versioning still own correctness.
- Keep standalone and check-only behavior valid even if the first optimization
  wave primarily accelerates the in-process runtime fast path.

Reversibility: The shared-session and content-addressed write layers are additive.
If any cache or invalidation rule proves unsound, the fallback is to bypass the
session-derived result and recompute from canonical source truth without needing to
rewrite Radar, Registry, Atlas, or Compass contracts.

Boundary Conditions:
- Scope includes `odylith sync`, read-model hoisting for backlog specs and Registry
  report reuse, path canonicalization dedupe, repo-root inference hoisting,
  content-addressed no-op write elision, and focused surface-render plumbing.
- Scope excludes a full persistent sync daemon, filesystem-watch-backed live index,
  and a full node-level reverse-dependency graph across every governed fact; those
  stay explicit follow-on work once the first end-to-end cut proves the model.

Related Bugs:
- [CB-066](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-sync-refresh-rewrites-unchanged-artifacts-and-stales-generated-timestamps.md)

## Learnings
- [x] Full governed sync is paying mainly for repeated discovery, not inherently
      expensive validation or rendering.
- [x] The sync runner already has an in-process fast path, so a shared session can
      land meaningful wins before a persistent daemon exists.
- [x] Path normalization, consumer-profile reads, idea parsing, Registry report
      construction, and repo-root inference all need one shared ownership model or
      they multiply across validators and renderers.
- [x] Content-addressed no-op writes are part of correctness hygiene, not just
      performance, because unchanged outputs should not dirty git or trigger
      downstream invalidation.

## Must-Ship
- [x] Add one explicit sync-session runtime that owns repo root, consumer profile,
      truth-root resolution, path normalization, parsed idea specs, and component
      Registry report reuse for the duration of a sync.
- [x] Route the hottest governance helpers through that session so repeated step
      mains reuse one read model instead of reparsing and re-resolving.
- [x] Add content-addressed no-op write discipline to the first touched generated
      outputs so unchanged bytes do not rewrite tracked surfaces.
- [x] Keep the current sync plan and validation behavior externally compatible.
- [x] Add focused proof that the shared session is reused across sync steps and
      that unchanged writes stay quiet.

## Should-Ship
- [x] Hoist repo-root inference out of backlog parsing and promotion-link checks.
- [x] Replace repeated path-prefix normalization with session-interned canonical
      path tokens on the current sync hot paths.
- [x] Make the second Registry-spec sync effectively conditional on actual upstream
      mutations instead of unconditional repeated work when hashes already settled.
- [x] Skip the runtime governance-packet lane on forced/full syncs where impact is
      already all-surfaces, and make the direct sync projection warm authoritative
      for later runtime readers in the same process.
- [x] Re-harden the late Registry forensics reconciliation after shell-facing
      refresh steps so strict standalone proof does not drift red when later sync
      activity changes evidence consumed by component forensics.

## Defer
- [ ] Persistent sync daemon with warm resident session state across commands.
- [ ] Full per-node reverse-dependency DAG and fixpoint scheduler across all
      governed facts and rendered surfaces.
- [ ] Filesystem watch integration for near-zero-cost startup change detection.

## Success Criteria
- [x] Warm incremental sync proves one shared session across the hot governance
      step chain rather than repeated read-model reconstruction.
- [x] Unchanged generated outputs stop rewriting bytes on the first landed
      content-addressed paths.
- [x] Focused profiling shows lower call counts for path normalization, repo-root
      inference, idea parsing, and Registry report construction on the optimized
      sync path.
- [x] `odylith sync --check-only --runtime-mode standalone` still proves the
      governed slice fail-closed.

## Non-Goals
- [ ] Claiming sub-second cold forced full sync from scratch in Python.
- [ ] Replacing the entire sync step graph with a daemon-only control plane in
      this first implementation wave.
- [ ] Inventing a new Registry component boundary before the implementation proves
      one is needed.

## Impacted Areas
- [ ] [2026-04-12-sub-second-governed-sync-via-shared-read-models-incremental-derivation-and-content-addressed-surface-writes.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-12-sub-second-governed-sync-via-shared-read-models-incremental-derivation-and-content-addressed-surface-writes.md)
- [ ] [2026-04-12-governed-sync-shared-read-models-incremental-derivation-and-content-addressed-writes.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-12-governed-sync-shared-read-models-incremental-derivation-and-content-addressed-writes.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [ ] [diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [ ] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [ ] [workstream_inference.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/workstream_inference.py)
- [ ] [validate_backlog_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_backlog_contract.py)
- [ ] [component_registry_intelligence.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/component_registry_intelligence.py)
- [ ] [consumer_profile.py](/Users/freedom/code/odylith/src/odylith/runtime/common/consumer_profile.py)
- [ ] `src/odylith/runtime/common/*` shared sync-session helpers
- [ ] focused sync/runtime tests covering session reuse, path-cache behavior, and
      no-op write elision

## Rollout
1. Bind the workstream, plan, Registry dossier, and Atlas diagram so the
   architecture is explicit before code shifts.
2. Land the shared sync-session layer and route the current hot governance paths
   through it.
3. Add content-addressed no-op writes on the first governed render targets.
4. Re-profile, then decide whether the next justified wave is a broader DAG
   invalidation engine or a resident daemon.

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_workstream_inference.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_component_registry_intelligence.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_context_grounding_hardening.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_render_backlog_ui.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full` (`3.4s` on 2026-04-11 after runtime warm-cache priming, full-mode governance-packet bypass, and the late Registry forensics reconciliation; earlier in the same wave the pre-hardening full runs were `5.2s` then `4.5s`)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- [x] `git diff --check`

## Outcome Snapshot
- [x] Governed sync stops behaving like twenty loosely related tools that all
      rediscover the same repo state.
- [x] The first optimization wave makes one shared read model visible in code and
      in profiling data.
- [x] Unchanged generated surfaces begin to stay byte-stable across no-op syncs.
- [x] Heavy Radar, Registry, Casebook, and tooling-shell renders now fingerprint
      their watched input cone and skip payload rebuilds entirely when the emitted
      bundle set still matches.
- [x] Full-mode sync no longer spends a reasoning-scope runtime warmup on an
      impact planner it does not need, and a direct sync warm now prevents later
      surface readers from rebuilding the same default projection a second time.
- [x] Strict standalone proof stays fail-closed after the optimization wave
      because late Registry forensics reconciliation now accounts for shell-facing
      steps that can still change evidence after the first spec sync.
