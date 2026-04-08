- Bug ID: CB-020

- Status: Closed

- Created: 2026-03-29

- Fixed: 2026-04-08

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Compass kept rendering a deterministic local standup brief even
  when Odylith was running inside Codex and the local provider was available.
  The original failure was shared reasoning autodetect and adapter coverage,
  and the same symptom later regressed on 2026-04-08 when the bounded
  `shell-safe` global brief path hard-disabled provider use again even though
  the local provider was available.

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

- Root Cause: Odylith's shared reasoning defaults initially assumed an
  `openai-compatible` endpoint with explicit base URL, model, and API key.
  After local-provider autodetect was added, the shared Codex path still
  forced the stale legacy model name `Codex-Spark 5.3`, so the local provider
  returned no usable structured brief and Compass still fell back to
  deterministic narration. The shared adapter stack also only knew how to call
  Codex CLI explicitly, not Claude Code. A later Compass refresh-contract
  follow-on then over-closed the bounded path: `_global_brief_provider_allowed`
  returned `False` for every `shell-safe` global window, so successful bounded
  renders still surfaced deterministic local briefs by policy instead of by
  genuine provider unavailability.

- Solution: Add implicit local-provider autodetect for Odylith reasoning when
  the shared explicit endpoint is absent, prefer the current host provider when
  it is detectable, add a Claude Code CLI structured-output adapter, stop
  forcing the stale legacy Codex model alias so local Codex can choose its
  current default automatically, suppress implicit provider calls under
  pytest/CI proof lanes, and route Compass runtime refresh through the same
  implicit local-provider path so global standup briefs can warm and reuse the
  AI brief cache. The bounded `shell-safe` follow-on also now allows
  opportunistic provider-backed global `24h`/`48h` narration while keeping
  scoped shell-safe warming deferred.

- Verification: Fixed on 2026-04-08. `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_compass_dashboard_runtime.py` passed with `23
  passed`; `PYTHONPATH=src python -m pytest -q
  tests/integration/runtime/test_surface_browser_deep.py -k
  'shell_safe_compass_refresh_artifacts_use_provider_backed_global_briefs_when_available
  or explicit_full_compass_refresh_artifacts_do_not_show_deterministic_brief'`
  passed with `2 passed, 22 deselected`; and `python -m py_compile
  src/odylith/runtime/surfaces/compass_dashboard_runtime.py
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/integration/runtime/test_surface_browser_deep.py` passed. A fresh
  local Compass `shell-safe` render on this repo now produces provider-backed
  global standup briefs when the local provider is available, and the browser
  lane now fails if that path regresses back to deterministic fallback.

- Prevention: Shared Odylith reasoning must default to the active local coding
  agent when one is available, and Compass must not hard-disable the same
  provider on its bounded global refresh path. Provider-unavailable or
  provider-deferred regressions should fail in focused reasoning and Compass
  browser coverage before they reach a rendered shell.

- Detected By: User report after the Compass shell showed `Deterministic local
  brief` instead of a provider-authored standup brief.

- Failure Signature: `standup_brief.24h.source == deterministic` with notice
  reason `provider_unavailable` or `provider_deferred`, no usable global
  provider-backed brief cache entry for the current packet, and the shell
  banner `Compass rendered a deterministic local brief...` even though the
  local provider is available.

- Trigger Path: `odylith sync --repo-root . --force --impact-mode full`,
  `python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root .`,
  or any successful Compass `shell-safe` rerender inside a local-provider
  environment where the bounded global brief path still hard-disables provider
  use.

- Ownership: Shared Odylith reasoning adapter and Compass standup narration.

- Timeline: The original regression was diagnosed on 2026-03-29 after
  confirming the generated Compass runtime payload contained only deterministic
  standup briefs. The local-provider autodetect and Claude Code adapter landed
  the same day and the generated Compass payload was rerendered afterward. The
  symptom resurfaced on 2026-04-08 when a successful `shell-safe` Compass
  render still emitted `Showing deterministic local brief`; that follow-on
  traced to an over-closed shell-safe global provider gate and was fixed the
  same day.

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
  not auto-call local providers from pytest/CI proof lanes, but also do not
  hard-disable provider use for bounded global Compass refresh once a provider
  is actually available.

- Preflight Checks: Inspect this bug,
  `src/odylith/runtime/evaluation/odylith_reasoning.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `tests/unit/runtime/test_odylith_reasoning.py`, and
  `tests/integration/runtime/test_surface_browser_deep.py` before changing
  local-provider selection or shell-safe Compass brief policy again.

- Regression Tests Added:
  `tests/unit/runtime/test_odylith_reasoning.py`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`, and
  `tests/integration/runtime/test_surface_browser_deep.py::test_shell_safe_compass_refresh_artifacts_use_provider_backed_global_briefs_when_available`

- Monitoring Updates: Compass runtime payload inspection and local rerender
  proof should continue checking whether global standup briefs are provider,
  cache, or deterministic sourced, and the shell-safe browser lane should fail
  if the global brief drops back to deterministic while the provider is
  available.

- Related Incidents/Bugs:
  [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md)

- Version/Build: workspace state on 2026-03-29 before local-provider
  autodetect and Claude Code adapter support.

- Config/Flags: shared reasoning defaults, local Codex/Claude Code CLI
  availability, Compass runtime refresh path, `--refresh-profile shell-safe`.

- Customer Comms: Tell operators that Compass now auto-uses the local coding
  agent for standup narration when available, without asking for separate
  endpoint keys or a stale host-model override, and still fails closed to
  deterministic narration when no local provider can run.

- Code References: `src/odylith/runtime/evaluation/odylith_reasoning.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `tests/unit/runtime/test_odylith_reasoning.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: `2026/freedom/v0.1.10` Compass closeout series.
