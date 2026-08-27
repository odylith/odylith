Status: Done
Created: 2026-08-26
Updated: 2026-08-26
Backlog: B-146

# v0.1.15 Node-Owned Greenfield Extension Migration Assessment

## Goal

Determine whether the v0.1.15 node-owned Greenfield Semantic Intent protocol
requires consumer-owned source migration before release promotion.

## Decision

No consumer source-data migration is required. The graph v16, IR v23, packet
v35, Product Intent authority v40, and compiler identity v33 changes are a
single fail-closed managed-runtime boundary. Older packets are rejected before
confirmation and must be rebuilt from source evidence; existing sealed records
remain immutable historical bytes.

## Assessed Scope

- Managed Greenfield runtime activation and rollback.
- Regenerated browser and bundle surfaces.
- Semantic packet and authority version rejection.
- Consumer-owned Radar, Registry, Atlas, Casebook, and Compass source
  preservation.

## Evidence

- The one-call source-meaning cohort completed 24 of 24 disclosed cases under
  the standard 60-second ceiling; the slowest case was 32.848 seconds.
- The Greenfield runtime and install suite passed 463 tests, and seven
  revision-bound deterministic transaction laws passed.
- Fresh local v0.1.15 assets completed clean-install, upgrade, stale-residue,
  and browser normal, empty, fallback, degraded, and error proof.
- The migration observer markers in B-146 bind the exact browser and
  install-managed change set.

## Compatibility And Risk

- No consumer-owned governance record is rewritten as migration output.
- Activation and rollback remain atomic; confirmation does no semantic work.
- Derived browser assets are replaceable projections refreshed from preserved
  governance source truth.
- Obsolete protocol bytes fail closed rather than being translated.

## Validation And Stop Condition

The assessment is complete when Radar validates the finished workstream and
plan binding, the release migration gate resolves B-146's observer markers,
and managed activation preserves consumer-owned source truth.
