---
status: implementation
idea_id: B-030
title: Odylith Consumer Upgrade, Reinstall Recovery, and Shell Refresh
date: 2026-03-30
priority: P1
commercial_value: 4
product_impact: 5
market_value: 4
impacted_lanes: service
impacted_parts: upgrade and reinstall CLI, launcher recovery, tooling dashboard refresh, default Compass refresh, Atlas diagnostics, release spotlight payload, Mermaid worker failure handling, and shell upgrade UX
sizing: L
complexity: High
ordering_score: 92
ordering_rationale: Consumer release posture is healthy once landed, but the operator path still has friction and trust gaps: reinstall semantics are surprising, missing-launcher recovery is awkward, broad sync is too heavy for shell refresh, and Mermaid worker failure can read like a hang. Tightening the release-facing recovery and refresh contract now reduces both user confusion and the risk of agents giving the wrong operational advice.
confidence: high
founder_override: yes
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-consumer-upgrade-release-spotlight-and-shell-refresh.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-016,B-028
workstream_blocks:
related_diagram_ids:
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Consumer upgrades already activate the new runtime, but the local dashboard can
stay visually stale until a later sync and the product gives the operator no
in-shell celebration or concise readout of what changed. Even after the first
spotlight pass, the close contract can still feel brittle if the popup lands on
an empty-looking fallback tab or disappears with no obvious recovery path.

## Customer
- Primary: consumer-repo operators upgrading Odylith through the supported CLI.
- Secondary: maintainers dogfooding consumer upgrades and judging whether the
  product feels alive after release.

## Opportunity
If reinstall, repair, and upgrade all stay on verified release assets, recover
from missing launchers without another checkout, refresh only the needed shell
surfaces while telling the operator exactly what was skipped, and make Mermaid
failure legible before the bulk render path starts, then Odylith turns release
upkeep into a trustworthy low-friction operator path instead of a surprising
series of special cases.

## Proposed Solution
- add a consumer-lane `odylith reinstall --latest` path that safely adopts the latest verified release and repo pin in one step
- improve missing-launcher recovery around the repo-local bootstrap launcher instead of requiring another Odylith checkout
- add an explicit `odylith dashboard refresh` command for shell-facing refreshes without full governance churn
- make default dashboard refresh include Compass while printing included versus excluded surfaces and the exact Atlas follow-up when Atlas is stale but skipped
- refresh consumer dashboard surfaces immediately after successful `odylith upgrade` or `odylith reinstall`
- persist a repo-local release spotlight payload for the current upgraded version
- gate the spotlight to real incremental upgrades only; first installs should
  show the normal launchpad without a release popup even if stale spotlight
  payload exists
- render a centered shell popup over the remembered Odylith surface instead of
  dropping back to a generic fallback background
- add a version-scoped toolbar reopen affordance so the spotlight can be
  recovered after an accidental close
- generate a crisp repo-local plain-English release note page for the upgraded
  version and link to it directly from the spotlight
- render a polished closeable shell popup with version transition, 1-3 release
  bullets, a circular `X`, outside-click dismiss, and Escape support
- make Mermaid worker timeout/fallback behavior name the blocking diagram ids and show per-diagram progress
- add Mermaid syntax preflight ahead of Atlas bulk render so parse failures stop on the first invalid `.mmd` with source path and line context

## Scope
- reinstall, upgrade, and repair-oriented CLI behavior for consumer repos
- launcher recovery guidance and bootstrap recovery affordances
- dashboard refresh command surface and narrow refresh execution path
- repo-local runtime payload file for the latest release spotlight
- dashboard render/presenter/control/CSS changes for the popup, reopen affordance,
  remembered surface state, and local release note
- Mermaid worker timeout, fallback, and final failure reporting
- bundled install/help/skill guidance that references the shipped CLI contract
- focused tests plus headless-browser proof

## Non-Goals
- changing product-repo maintainer upgrade posture beyond clearer guardrails
- redesigning the main dashboard information architecture outside the popup
- adding remote telemetry or hosted release analytics

## Risks
- automatic surface refresh could make upgrade or reinstall feel slower if it blocks on shell rendering
- the popup could feel noisy if it repeats indefinitely or fights the first-run launchpad
- release bullets could read poorly if a release ships with weak highlights
- reinstall or launcher recovery could accidentally widen trust toward host Python if the consumer boundary is not kept strict
- a “refresh dashboard” command could quietly mutate more governance truth than operators expect

## Dependencies
- `B-016` established consumer install and upgrade guidance
- `B-028` established the refreshed shell visual language and welcome-state patterns
- Open Casebook bugs on consumer runtime trust and same-version repair define the fail-closed constraints for this slice

## Success Metrics
- consumer upgrade and reinstall refresh `odylith/index.html` immediately after success
- missing-launcher recovery can be explained and executed from the repo itself without borrowing another checkout
- `odylith dashboard refresh` refreshes shell-facing surfaces without forcing Registry forensic churn, includes Compass by default, and prints the exact Atlas next step when Atlas is stale but excluded
- the refreshed shell can show a closeable release spotlight with from/to versions
- the spotlight shows at most three concise highlights and can be dismissed persistently in-browser
- first-time install and first-run launchpad flows never show the upgrade
  spotlight
- the spotlight reopens from the toolbar and returns over the operator's last
  active Odylith surface after refresh instead of dropping to a dead-looking
  fallback tab
- Mermaid worker failures name the blocking diagram ids and one-shot fallback progress instead of reading hung
- Atlas parse failures fail fast with diagram id, source path, and line context before the render batch starts

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_sync_cli_compat.py tests/integration/install/test_manager.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py`
- headless browser screenshot proof of the upgrade spotlight
- `git diff --check`

## Rollout
Ship as a consumer-lane release-hardening slice. Keep runtime activation on
verified release assets, keep transient spotlight state local under `.odylith/`,
and keep the new dashboard refresh path narrow enough that operators do not
accidentally trigger broader governance churn.

## Why Now
The product just shipped GA and the release lifecycle needs to feel both
polished and safe: one-step consumer adoption, first-class recovery, and shell
refresh that stays legible under failure.

## Product View
Upgrade should have emotional presence, and the operational path around it
should not feel brittle. If Odylith improves, the product should look like it
knows that immediately and recover cleanly when local state drifts.

## Impacted Components
- `odylith`
- `dashboard`
- `atlas`
- `release`

## Interface Changes
- consumer reinstall and upgrade now refresh shell surfaces immediately
- consumer repos gain an explicit reinstall command that adopts the verified latest release in one step
- dashboard refresh becomes an explicit narrow command instead of overloading full governance sync
- default dashboard refresh now includes Compass and tells the operator which surfaces were intentionally excluded
- Atlas auto-update now validates Mermaid syntax before the render batch and reports path-plus-line failures directly
- dashboard can show a release spotlight popup after upgrade
- first install does not show the upgrade spotlight
- the popup includes versions, release bullets, a circular close control, and a
  repo-local plain-English release note link
- the shell remembers the last active tab across refresh and can expose a
  version-scoped `Show v<version> note` reopen affordance after the spotlight
  is closed
- launcher recovery guidance can point at the repo-local bootstrap launcher

## Migration/Compatibility
- backward compatible; the spotlight payload lives under `.odylith/` and can be
  ignored safely by older shells
- the new dashboard refresh command is additive and does not remove the full
  `odylith sync` path

## Test Strategy
- unit-test reinstall and upgrade CLI behavior plus spotlight payload persistence
- unit-test shell payload derivation and render contract
- unit-test dashboard refresh command routing and narrow refresh ordering
- unit-test Mermaid worker timeout/fallback reporting
- prove the rendered popup, reopen affordance, and persisted remembered-surface
  behavior in a headless browser
- prove the incremental-upgrade path separately from first-install launchpad
  behavior so stale spotlight payload cannot leak into first use
- prove the mixed edge case where a real incremental upgrade lands in a repo
  that still needs starter onboarding, so the release note owns first paint and
  the starter guide reappears only when the operator asks for it
- prove the actual `odylith upgrade` operator path can refresh a browser-valid
  incremental-upgrade note after CLI activation, not just a seeded shell state

## Open Questions
- whether a later slice should let the popup deep-link into specific refreshed
  surfaces based on the strongest release highlight

## Outcome
- Bound to `B-030`; implementation in progress.
- Default dashboard refresh now includes Compass, prints included versus excluded surfaces, and points at the exact Atlas follow-up command when Atlas is stale but skipped.
- Atlas auto-update now fails fast on invalid Mermaid source with diagram id, source path, and parse-line context before the render batch begins.
