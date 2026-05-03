- Bug ID: CB-149

- Type: Product








- Status: FixedPendingRelease

- Created: 2026-05-01

- Severity: P1

- Reproducibility: High


- Description: Host adapters pay too much Odylith hook and startup latency

- Impact: Claude Code users experience Odylith as super slow before the assistant can answer routine prompts, and the same hook/startup architecture can affect Codex or any future host adapter if low-signal turns still pay heavy context and intervention costs.

- Components Affected: governance-intervention-engine

- Environment(s): Host-adapter runtime on 2026-05-01 during v0.1.13 migration work, with large repo guidance, Odylith memory/guidance bundles, UserPromptSubmit-style hooks, Stop hooks, and startup grounding active.

- Detected By: Operator report quoting Claude's explanation that heavy system surface, startup hook fallback work, and shelling out for odylith show all contributed to slowness, with explicit instruction to fix across all host models.

- Failure Signature: Host model explains that heavy system surface, startup fallback work, and tool fanout before answering routine prompts cause visible slowness; suggested quick wins are model switches or narrower questions instead of product-side latency controls.

- Trigger Path: Routine host prompt turn with Odylith hooks and guidance loaded; plain show/help/status style prompt can still pay for startup, prompt-context, prompt-teaser, intervention-status, or shell work before the assistant answers.

- Ownership: Host adapter layer across Claude, Codex, and future hosts; intervention prompt hooks; context-engine startup grounding; project guidance bundle; show/help/status fast-path routing.

- Timeline: Captured 2026-05-01 through `odylith bug capture`.

- Blast Radius: All Odylith host adapters and their users, with immediate evidence from Claude Code and potential impact on Codex where equivalent prompt hooks and large guidance contracts are active.

- SLO/SLA Impact: Interactive latency regression on primary host adapters; increases abandonment risk and support load even when correctness is intact.

- Data Risk: Low direct data risk; product experience and operator-trust risk are high.

- Security/Compliance: No direct security exposure, but slow hook paths can encourage users to bypass Odylith guidance or disable hooks during sensitive migration work.

- Invariant Violated: Odylith host hooks must deliver high-signal grounding within an explicit host-general latency budget and must bypass heavy work on low-signal or stdout-clean prompts.

- Root Cause: Likely compounded cost across large guidance/context payloads, prompt/stop hook execution, startup fallback work, and show/help prompt paths that can shell out instead of using direct route locks.

- Solution: Implement B-141 as a host-general latency slice: measure Claude and Codex hook/startup latency, enforce budgeted fast paths for low-signal and show/help/status prompts, keep the compact alignment substrate active on quiet prompt and SessionStart lanes, collapse Claude prompt-submit work into one prompt-bundle path, defer Codex governed refresh work to Stop-time settlement, seed host-launched hooks for context-engine warm-daemon reuse, and have generated launchers dispatch baked host hook commands directly to runtime modules instead of importing the full CLI dispatcher first.

- Solution Update: v0.1.13 also slims the consumer-lane guidance surface
  without deleting Odylith capability. Installed root guidance and consumer
  `odylith/AGENTS.md` now keep a hard-law kernel plus explicit preservation
  of startup, Context Engine, Execution Engine, memory substrate, Tribunal,
  Intervention Engine, observers, governance, subagent routing, Surface DAGs,
  delivery, analysis, and migration-breakage observation. Long-form policy is
  routed to guidance and skills instead of duplicated in the hot prompt
  surface.

- Host-Native Update: Claude uses host-supported
  `disable-model-invocation: true` for lower-frequency manual workflow skills
  while leaving automatic startup, context, show, sync, bug-capture,
  preflight, and hygiene skills model-invocable. Codex keeps its separate
  `.agents/skills` policy and supported command-hook shape; no Claude-only
  fields are emitted into Codex configuration.

- Guidance Surface Update: The follow-up v0.1.13 pass removed root
  long-form duplication that already routes to playbooks: contributor identity,
  source-size discipline, and anti-slop details now stay compact in root
  `AGENTS.md`, while the detailed anti-slop bans remain in
  `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` and the
  code-hygiene skill. The checked-in Codex and Claude `odylith-start` and
  `odylith-context` skill shims remain because they preserve the serial
  startup/context contract; no local Codex duplicate registration was
  reproduced.

- Follow-up Correction: Operator feedback on 2026-05-02 showed that running
  `odylith start`, `odylith context`, and `git status` in parallel creates the
  wrong visible sequence and can make the Context Engine appear to precede the
  startup contract. The fix is cross-host guidance, not feature removal:
  startup is now a serial gate, and follow-on `context`, `query`, repo status,
  or broad search runs only after `start` completes and an exact anchor is
  known.

- Source-Local Memory Update: The 2026-05-02 activation audit found that
  detached source-local launchers could run unreleased `src/odylith/*` through
  the pinned managed Python and therefore miss the source checkout's
  LanceDB/PyArrow/Tantivy dev dependencies. Generated source-local launchers
  now prefer the source checkout `.venv` before the managed wrapper when the
  active runtime is `source-local`, while consumer pinned runtimes remain on
  the managed feature-pack path.

- Visibility Recovery Update: Explicit feedback such as "I want to see
  Odylith Assist in every prompt" now maps to the shared prompt-visible
  recovery line across Codex and Claude. The detector uses precise Assist
  visibility phrases so ordinary low-signal prompts still stay quiet and
  show/help/capability passthrough prompts remain stdout-clean. Exact
  Assist-visibility feedback renders the recovery Assist only, so stale
  Observation or Proposal blocks cannot be prepended to the recovery line.

- Consumer Start Regression Update: Operator feedback after installing
  Odylith v0.1.13 showed `./.odylith/bin/odylith start --repo-root .` taking
  about 25-30s in a consumer lane. Live repro against `dentoai-orion` measured
  `real 25.40` on the installed runtime for an expected multi-path fallback,
  with profiling attributing the cost to repeated managed-runtime tree
  integrity scans and context-engine projection/test-history fingerprinting.
  The source fix keeps full tree integrity on `doctor` and repair paths, but
  lets `start` use hot-file managed-runtime trust checks, a hot-path bootstrap
  packet, and shallow repo-root XML report fingerprinting.

- Rollback/Forward Fix: Forward-fix in v0.1.13; do not remove grounding or safety hooks without replacing them with measured fast-path equivalents.

- Verification: Local v0.1.13 timing showed low-signal direct hook modules returning empty in about 42-44 ms median for Claude prompt-context, Claude prompt-teaser, and Codex prompt-context; full CLI fallback paths dropped to about 106-116 ms median. Follow-up substrate validation proved quiet Codex and Claude prompt hooks now emit compact Context Engine, memory, Execution Engine, delivery, Tribunal, and proof evidence while still skipping the full conversation bundle; SessionStart uses the same substrate instead of manual-start fallback text; context-engine autospawn reached a live watchdog-backed daemon. Focused tests cover Claude prompt-bundle route locks plus hidden/visible prompt output parity, async Claude PostToolUse settings, Codex dirty-event deferral, Stop-time governed refresh settlement, substrate-backed prompt gating, direct launcher hook dispatch, cross-host prompt parity, host-launcher warm-daemon defaults, install launcher generation, and mixed-version prompt-bundle fallback when current-source launchers run against the shipped v0.1.12 runtime. The guidance diet measured root `AGENTS.md` at 17,381 bytes and consumer `odylith/AGENTS.md` plus its bundle mirror at 16,307 bytes after preserving the engine contract. `PYTHONPATH=src pytest -q tests/unit/install/test_agents.py tests/unit/install/test_manager.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_show_capabilities.py` passed with 119 tests covering byte budgets, engine-preservation wording, Claude model-invocable skill capping, Codex/Claude skill separation, anti-slop guidance, and show/capabilities behavior. The follow-up root-routing proof ran `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_hygiene.py::test_anti_slop_contract_stays_explicit_across_guidance_surfaces tests/unit/runtime/test_hygiene.py::test_root_agents_keeps_anti_slop_detailed_rules_routed tests/unit/runtime/test_hygiene.py::test_casebook_claude_bridge_defers_release_closeout_rule_to_agents` and `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_agents.py tests/unit/runtime/test_source_bundle_mirror.py`.

- Verification Update: The 2026-05-02 source-local activation audit proved the
  repo-local launcher reports `Context engine mode: full_local_memory`;
  `memory-snapshot` reports `lance_local_columnar` plus
  `tantivy_sparse_recall`, ready dependencies, and no backend-transition gaps;
  autospawned `context B-141` brought the daemon live with watchdog; and
  `context-engine status` reported `daemon_alive: yes`,
  `watcher_backend: watchdog`, and `memory_backend_fallback: no`. Focused
  install and intervention tests passed for the source-local launcher handoff
  and the exact Assist visibility-feedback phrase across Codex and Claude,
  including suppression of stale replay blocks for that exact recovery prompt.
  Compass forced daemon refresh now autospawns the same local daemon contract
  instead of failing when the daemon is idle; the first live run passed with
  `resolved_runtime_mode: daemon`, and the warm rerun completed in 4.1s.

- Prevention: Require latency-budget and substrate-integrity tests for host hook changes, keep show/help/status passthrough paths stdout-clean and direct across Claude, Codex, and future adapters, and prevent low-signal prompt gates from constructing full conversation bundles while still proving memory, execution, delivery, Tribunal, and intervention alignment.

- Prevention Update: Consumer-lane guidance reductions must include explicit
  engine-preservation assertions and host-separation tests. Maintainer-only
  release-gate and migration-observer guidance stays in `odylith/maintainer/`
  and must not be mirrored into consumer install assets as a latency shortcut.

- Prevention Update: Guidance, skills, Claude project commands, and bundle
  mirrors must keep the serial startup contract aligned across Codex, Claude,
  and future hosts; enforcement tests reject drift back to combined
  `start`/`context` wording or parallel kickoff guidance.

- Prevention Update: Radar topology enforcement now lives in
  `backlog_topology_contract.py` instead of growing the oversized backlog
  validator. `validate_backlog_contract.py` dropped back below its pinned
  hotfile limit, and the topology-sensitive B-141 prevention stays covered by
  the same backlog-contract tests.

- Prevention Update: The Odylith-tree consumer guidance diet keeps
  `odylith/AGENTS.md` and its bundle mirror explicit for startup, context
  ordering, engine activation, intervention visibility, consumer write
  boundaries, CLI-first, anti-slop, and host-specific capability separation
  while deferring repeated help/show/commentary/governance detail to the
  repo-root hard-law kernel that loads first. Focused install and hygiene tests
  assert that split instead of requiring every shared rule to be restated in the
  nested file.

- Prevention Update: Source-local maintainer launchers must not silently fall
  back to a pinned managed interpreter when proving unreleased engine work.
  Consumer installs keep the managed feature pack, but maintainer
  `source-local` uses the source checkout Python so full local memory,
  context-engine daemon reuse, and target recall backends stay active.

- Prevention Update: Compass daemon runtime mode is an explicit low-latency
  contract. Forced daemon refresh may autospawn the local Context Engine daemon;
  `auto` remains conservative and may fall back to standalone instead of
  leaving a daemon behind.

- Verification Update: The v0.1.13 consumer-start repro measured
  `/usr/bin/time -p ./.odylith/bin/odylith start --repo-root .` in
  `dentoai-orion` at `real 25.40`, `user 13.27`, `sys 11.62` before this
  patch. The patched source path against the same consumer repo now returns the
  expected `Need one code path` fallback in `real 2.55` after an initial
  `real 2.88` run. Focused coverage passed for fast start preflight,
  hot-path bootstrap packet construction, hot-file-only runtime integrity,
  shallow root-level test-report fingerprinting, and existing start/doctor
  behavior.

- Monitoring Updates: Track prompt-submit, prompt-context, prompt-teaser, stop-summary, and startup grounding latency in local benchmark or smoke outputs for each supported host adapter.

- Version/Build: Observed during v0.1.13 branch work; issue exists after v0.1.12 migration.

- Config/Flags: Default Claude and Codex project hooks and guidance bundle.

- Customer Comms: Acknowledge the report as a product bug, not a user-model-selection problem; product should make routine host turns faster by default.

- Related Incidents/Bugs: B-141; CB-147 covers repair hook spam and is adjacent but separate.

- Fixed In: v0.1.13

- Code References: - src/odylith/runtime/common/claude_cli_capabilities.py
- src/odylith/runtime/common/codex_cli_capabilities.py
- src/odylith/cli.py
- src/odylith/install/manager.py
- src/odylith/install/runtime.py
- src/odylith/install/runtime_integrity.py
- src/odylith/install/runtime_status.py
- src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py
- src/odylith/runtime/intervention_engine/prompt_signal_runtime.py
- src/odylith/runtime/intervention_engine/host_surface_runtime.py
- src/odylith/runtime/surfaces/host_visible_intervention.py
- src/odylith/runtime/surfaces/claude_host_prompt_bundle.py
- src/odylith/runtime/surfaces/claude_host_prompt_context.py
- src/odylith/runtime/surfaces/claude_host_session_brief.py
- src/odylith/runtime/surfaces/host_dirty_checkpoint.py
- src/odylith/runtime/surfaces/host_intervention_support.py
- src/odylith/runtime/surfaces/codex_host_prompt_context.py
- src/odylith/runtime/surfaces/codex_host_session_brief.py
- src/odylith/runtime/surfaces/codex_host_post_bash_checkpoint.py
- src/odylith/runtime/surfaces/codex_host_stop_summary.py
- src/odylith/runtime/surfaces/compass_refresh_runtime.py
- .agents/bin/odylith-host-launcher.py
- tests/unit/install/test_runtime_host_hook_launcher.py
- tests/integration/install/test_manager.py
- tests/unit/runtime/test_compass_refresh_runtime.py
- tests/unit/runtime/test_host_visible_intervention.py
