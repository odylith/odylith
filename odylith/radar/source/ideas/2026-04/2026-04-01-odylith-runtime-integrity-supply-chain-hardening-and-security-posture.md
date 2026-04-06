---
status: implementation
idea_id: B-040
title: Odylith Runtime Integrity, Supply-Chain Hardening, and Security Posture
date: 2026-04-01
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: managed runtime trust anchor, launcher and bootstrap launcher trust checks, release-asset override policy, GitHub workflow pinning, security documentation, process-lifetime verification, and v0.1.7 release messaging
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Odylith's runtime and release trust model is now part of the product claim, so local tamper detection, supply-chain pinning, and honest security documentation need to land as one bounded wave instead of remaining scattered follow-up fixes.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-01-odylith-runtime-integrity-supply-chain-hardening-and-security-posture.md
execution_model: standard
workstream_type: child
workstream_parent: B-033
workstream_children:
workstream_depends_on: B-027,B-029,B-030
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
Odylith had already improved install and release verification, but the local
runtime trust boundary was still too weak once assets were staged into
`.odylith/`. A malicious or merely drifted local runtime tree could still
confuse launcher fallback, repair could inherit stale mutable authority, and
consumer posture still exposed insecure maintainer-only release overrides and
workflow mutability that undercut the stronger product story.

## Customer
- Primary: consumer-repo operators who need `./.odylith/bin/odylith` to fail
  closed on bad local runtime state instead of hanging or silently trusting
  mutable runtime bytes.
- Secondary: Odylith maintainers proving pinned dogfood and release builds who
  need a stronger local trust boundary, pinned workflow supply chain, and one
  honest public security posture.

## Opportunity
If Odylith treats runtime integrity, supply-chain proof, and process lifetime
as one product contract, the product gains a more credible answer to local
tamper, insecure release rehearsal toggles, and launcher trust ambiguity
without pretending it can solve full same-user repo compromise from inside the
same repo.

## Proposed Solution
- Add repo-root managed-runtime trust anchors outside `.odylith/` and verify
  hot-path managed-runtime files before `odylith.cli` import.
- Verify the deeper runtime tree during `doctor`, repair, and same-version
  runtime reuse so dependency drift or symlink substitution shows up as trust
  failure instead of reuse.
- Preserve a narrow compatibility path for legacy `0.1.0` and `0.1.1`
  consumer installs so they can bootstrap onto a modern trusted release
  without weakening the modern trust contract.
- Reject insecure localhost release overrides and Sigstore-bypass toggles
  outside the product-repo maintainer lane.
- Pin first-party GitHub workflow actions to immutable SHAs, pin the runner
  image, and pin Hatch in CI.
- Publish the security contract in README-linked docs, bundled guidelines,
  skills, Registry, Radar, Casebook, and `v0.1.7` release messaging.
- Explicitly verify no Odylith-owned Python helper processes remain after the
  validated command or timeout path finishes.

## Scope
- `src/odylith/install/runtime.py`, `runtime_integrity.py`,
  `release_assets.py`, and related installer/manager paths
- release, release-candidate, and test workflow pinning
- security docs and skills across product and bundled consumer trees
- Registry/Radar/Casebook/plan truth for the security contract
- `v0.1.7` release note and popup-facing authored messaging

## Non-Goals
- claiming full tamper-proof local security against same-user repo compromise
- broad hosted disclosure-program policy or enterprise security-process work
- replacing Sigstore with a different release-signing stack in this wave

## Risks
- trust checks could strand legacy consumer installs unless the compatibility
  path is explicit and tightly bounded
- new verification could slow startup if the hot path is not kept smaller than
  the deep doctor path
- security docs could overclaim if they do not state residual same-user risk
  plainly

## Dependencies
- `B-033` remains the umbrella release-hardening workstream
- `B-027` already defines lane-boundary language that this security contract
  must stay consistent with
- `B-029` already established gitignore bootstrap for Odylith-managed state
- `B-030` already owns upgrade spotlight and consumer release-note UX that
  should carry the new security posture

## Success Metrics
- modern managed runtimes fail closed on local drift instead of executing
  unverified bytes
- consumer posture rejects insecure localhost and Sigstore-bypass release
  overrides
- release, release-candidate, and test workflows no longer rely on floating
  first-party action tags or floating Hatch installs
- `v0.1.7` popup-facing release copy explains the strengthened security
  posture honestly
- focused validation and live checks finish without lingering Odylith-owned
  Python processes

## Validation
- `pytest tests/unit/install/test_runtime.py tests/unit/install/test_release_assets.py -q`
- `pytest tests/integration/install/test_manager.py -q`
- `pytest tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_sync_cli_compat.py -q`
- live launcher/runtime checks plus final Odylith-owned process sweep

## Rollout
Land the runtime trust-anchor and workflow-pinning changes first, then refresh
the security docs and bundled guidance, and finally rerun the release-facing
validation and process-lifetime checks before any `v0.1.7` messaging ships.

## Why Now
Odylith is already making a stronger public trust claim around its managed
runtime. The remaining mutable-runtime and workflow gaps weaken that claim more
than another feature win would help it.

## Product View
If Odylith cannot explain why its local runtime should be trusted, then the
rest of the product story is standing on sand. Security posture has to become
part of the product, not just an internal aspiration.

## Impacted Components
- `odylith`
- `release`
- `security`
- `dashboard`

## Interface Changes
- launcher and repair flows surface stronger trust failures instead of silently
  reusing questionable runtime bytes
- consumer release overrides become narrower and more obviously maintainer-only
- security posture shows up in public docs, bundled guidance, and release
  messaging with explicit residual-risk framing

## Migration/Compatibility
- modern installs should keep the stronger fail-closed runtime behavior by
  default
- legacy `0.1.0` and `0.1.1` installs keep a narrowly bounded upgrade bridge
  so they can reach a modern trusted release
- no consumer repo migration is required beyond taking a newer Odylith update

## Test Strategy
- keep the runtime, release-asset, and manager tests as the characterization
  base for trust-anchor changes
- add or retain targeted workflow and process-lifetime checks so the security
  story is proved in both unit and live validation lanes
- refresh the release-facing docs only after the validation and process-sweep
  evidence is green

## Open Questions
- whether the compatibility bridge for legacy installs should age out on a
  fixed release schedule once enough modern installs have crossed over
- whether future release proof should add stronger artifact-origin reporting in
  the operator surfaces instead of keeping that detail maintainer-only

## Outcome
- Bound to `B-040` as a child of `B-033`.
- This workstream carries runtime-integrity hardening, supply-chain pinning,
  security posture publication, and process-lifetime verification together as
  one bounded security wave.
