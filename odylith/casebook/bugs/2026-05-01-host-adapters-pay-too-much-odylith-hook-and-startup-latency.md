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

- Rollback/Forward Fix: Forward-fix in v0.1.13; do not remove grounding or safety hooks without replacing them with measured fast-path equivalents.

- Verification: Local v0.1.13 timing showed low-signal direct hook modules returning empty in about 42-44 ms median for Claude prompt-context, Claude prompt-teaser, and Codex prompt-context; full CLI fallback paths dropped to about 106-116 ms median. Follow-up substrate validation proved quiet Codex and Claude prompt hooks now emit compact Context Engine, memory, Execution Engine, delivery, Tribunal, and proof evidence while still skipping the full conversation bundle; SessionStart uses the same substrate instead of manual-start fallback text; context-engine autospawn reached a live watchdog-backed daemon. Focused tests cover Claude prompt-bundle route locks plus hidden/visible prompt output parity, async Claude PostToolUse settings, Codex dirty-event deferral, Stop-time governed refresh settlement, substrate-backed prompt gating, direct launcher hook dispatch, cross-host prompt parity, host-launcher warm-daemon defaults, install launcher generation, and mixed-version prompt-bundle fallback when current-source launchers run against the shipped v0.1.12 runtime.

- Prevention: Require latency-budget and substrate-integrity tests for host hook changes, keep show/help/status passthrough paths stdout-clean and direct across Claude, Codex, and future adapters, and prevent low-signal prompt gates from constructing full conversation bundles while still proving memory, execution, delivery, Tribunal, and intervention alignment.

- Monitoring Updates: Track prompt-submit, prompt-context, prompt-teaser, stop-summary, and startup grounding latency in local benchmark or smoke outputs for each supported host adapter.

- Version/Build: Observed during v0.1.13 branch work; issue exists after v0.1.12 migration.

- Config/Flags: Default Claude and Codex project hooks and guidance bundle.

- Customer Comms: Acknowledge the report as a product bug, not a user-model-selection problem; product should make routine host turns faster by default.

- Related Incidents/Bugs: B-141; CB-147 covers repair hook spam and is adjacent but separate.

- Fixed In: v0.1.13

- Code References: - src/odylith/runtime/common/claude_cli_capabilities.py
- src/odylith/runtime/common/codex_cli_capabilities.py
- src/odylith/install/runtime.py
- src/odylith/runtime/intervention_engine/prompt_signal_runtime.py
- src/odylith/runtime/intervention_engine/host_surface_runtime.py
- src/odylith/runtime/surfaces/claude_host_prompt_bundle.py
- src/odylith/runtime/surfaces/claude_host_prompt_context.py
- src/odylith/runtime/surfaces/claude_host_session_brief.py
- src/odylith/runtime/surfaces/host_dirty_checkpoint.py
- src/odylith/runtime/surfaces/host_intervention_support.py
- src/odylith/runtime/surfaces/codex_host_prompt_context.py
- src/odylith/runtime/surfaces/codex_host_session_brief.py
- src/odylith/runtime/surfaces/codex_host_post_bash_checkpoint.py
- src/odylith/runtime/surfaces/codex_host_stop_summary.py
- .agents/bin/odylith-host-launcher.py
- tests/unit/install/test_runtime_host_hook_launcher.py
