- Bug ID: CB-020

- Status: Closed

- Created: 2026-03-29

- Fixed: 2026-03-29

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Compass kept rendering a deterministic local standup brief even
  when Odylith was running inside Codex and the local provider was available.
  The same shared reasoning path also had no Claude Code-compatible local CLI
  adapter, so Compass could not produce a provider-authored standup brief out
  of the box in either supported local coding-agent environment.

- Impact: The first impression of Compass was materially weaker than intended.
  Operators saw fallback narration instead of the best AI-authored brief, the
  local standup brief cache never warmed, and Odylith looked less capable than
  the actual repo/provider environment allowed.

- Components Affected: `src/odylith/runtime/evaluation/odylith_reasoning.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`, Compass
  standup-brief cache contract, shared local-provider selection path.

- Environment(s): local Odylith product repo in Codex Desktop on macOS; same
  failure class also applied to Claude Code environments because Odylith had no
  Claude Code local-provider adapter.

- Root Cause: Odylith's shared reasoning defaults still assumed an
  `openai-compatible` endpoint with explicit base URL, model, and API key.
  After local-provider autodetect was added, the shared Codex path still
  forced the stale legacy model name `Codex-Spark 5.3`, so the local provider
  returned no usable structured brief and Compass still fell back to
  deterministic narration. The shared adapter stack also only knew how to call
  Codex CLI explicitly, not Claude Code.

- Solution: Add implicit local-provider autodetect for Odylith reasoning when
  the shared explicit endpoint is absent, prefer the current host provider when
  it is detectable, add a Claude Code CLI structured-output adapter, stop
  forcing the stale legacy Codex model alias so local Codex can choose its
  current default automatically, suppress implicit provider calls under
  pytest/CI proof lanes, and route Compass runtime refresh through the same
  implicit local-provider path so global standup briefs can warm and reuse the
  AI brief cache.

- Verification: Focused unit coverage now proves Codex autodetect, Claude
  autodetect, legacy Codex model stripping, Claude CLI structured-output
  parsing, and Compass standup brief provider behavior. A fresh local Compass
  render on this repo now produces a provider-authored global standup brief
  and writes `.odylith/compass/standup-brief-cache.v5.json`.

- Prevention: Shared Odylith reasoning must default to the active local coding
  agent when one is available. Provider-unavailable regressions should fail in
  focused reasoning and Compass coverage before they reach a rendered shell.

- Detected By: User report after the Compass shell showed `Deterministic local
  brief` instead of a provider-authored standup brief.

- Failure Signature: `standup_brief.24h.source == deterministic` with notice
  reason `provider_unavailable`, no local standup brief cache file, and the
  shell banner `Compass rendered a deterministic local brief from the current
  fact packet because live AI narration was unavailable for this view.`

- Trigger Path: `odylith sync --repo-root . --force --impact-mode full` or
  `python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root .`
  inside a local provider environment with no explicit Odylith reasoning API
  config.

- Ownership: Shared Odylith reasoning adapter and Compass standup narration.

- Timeline: The regression was diagnosed on 2026-03-29 after confirming the
  generated Compass runtime payload contained only deterministic standup
  briefs. The local-provider autodetect and Claude Code adapter landed the same
  day and the generated Compass payload was rerendered afterward.

- Blast Radius: All Odylith repos relying on default local provider behavior
  for Compass narration; Codex environments were underpowered immediately and
  Claude Code environments had no compatible local provider path at all.

- SLO/SLA Impact: No outage, but a visible product-quality regression in the
  Compass operator experience and a weaker onboarding/AHA moment.

- Data Risk: None.

- Security/Compliance: The fix keeps the local-provider path read-only and
  bounded. It does not introduce hosted secrets or broaden file-write
  authority.

- Invariant Violated: When Odylith is running inside a supported local coding
  agent, Compass should use that provider automatically for standup narration
  instead of requiring separate API-key configuration.

- Workaround: None required on the normal local Codex or Claude Code path
  after the forward fix. Explicit reasoning endpoint config remains available
  only when an operator intentionally wants to override the default local
  provider.

- Rollback/Forward Fix: Forward fix only. Reverting would reintroduce the
  weaker deterministic-only default and remove Claude Code compatibility for
  local standup narration.

- Agent Guardrails: Do not make Compass or shared Odylith reasoning depend on a
  hosted API key when Odylith is already running inside a local agent host. Do
  not auto-call local providers from pytest/CI proof lanes.

- Preflight Checks: Inspect this bug, `src/odylith/runtime/evaluation/odylith_reasoning.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`, and
  `tests/unit/runtime/test_odylith_reasoning.py` before changing local-provider
  selection again.

- Regression Tests Added: `tests/unit/runtime/test_odylith_reasoning.py`

- Monitoring Updates: Compass runtime payload inspection and local rerender
  proof should continue checking whether global standup briefs are provider,
  cache, or deterministic sourced.

- Related Incidents/Bugs: none recorded

- Version/Build: workspace state on 2026-03-29 before local-provider
  autodetect and Claude Code adapter support.

- Config/Flags: shared reasoning defaults, local Codex/Claude Code CLI
  availability, Compass runtime refresh path.

- Customer Comms: Tell operators that Compass now auto-uses the local coding
  agent for standup narration when available, without asking for separate
  endpoint keys or a stale host-model override, and still fails closed to
  deterministic narration when no local provider can run.

- Code References: `src/odylith/runtime/evaluation/odylith_reasoning.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `tests/unit/runtime/test_odylith_reasoning.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
