---
status: queued
idea_id: B-056
title: Trust Bootstrap Warning Suppression and Success Clarity
date: 2026-04-06
priority: P1
commercial_value: 4
product_impact: 4
market_value: 3
impacted_parts: Sigstore verification output, benign TUF warning handling, install and repair success messaging, and release-note wording
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: Operators should not leave a successful verified install wondering whether the scary warning block was fatal. Quieting or translating benign verifier noise is a trust-polish fix for the exact moment Odylith claims supply-chain rigor.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-040
workstream_blocks:
related_diagram_ids: D-019,D-020
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
Successful trust bootstrap can still emit scary non-fatal verifier warnings
such as offline-mode or unsupported-key chatter even when verification actually
passed.

## Customer
- Primary: operators reading install and repair output.

## Opportunity
Capture verifier stderr, suppress only allowlisted benign warnings, and always
print one explicit success line when verification succeeded.

## Proposed Solution
- classify known benign verifier warnings
- suppress or translate them on successful verification
- preserve fatal stderr when verification really fails
- refresh the 0.1.8 release note to mention the quieter verified output

## Scope
- release-asset verification output handling
- install and repair CLI messaging
- release-note refresh

## Non-Goals
- weakening verification itself

## Risks
- a bad allowlist could hide a real verification failure

## Dependencies
- `B-040`

## Success Metrics
- successful verification prints a clear success line
- benign warning chatter no longer dominates the terminal
- real verification failures still show full error details

## Validation
- `pytest -q tests/unit/install/test_release_assets.py tests/unit/test_cli.py`

## Rollout
Ship after the trust semantics are stable so the quieter output reflects a
trustworthy success path.

## Why Now
The current warning story undercuts the very trust posture Odylith is trying to
strengthen.

## Product View
Security messaging should sound strict when the system failed and calm when the
system actually verified. Right now those two states blur together.

## Impacted Components
- `odylith`
- `release`

## Interface Changes
- successful verifier runs collapse benign warnings and print an explicit
  verification-success line

## Migration/Compatibility
- output-only improvement

## Test Strategy
- capture successful verifier stderr and assert fatal-versus-benign handling

## Open Questions
- whether later versions should surface a machine-readable verifier warning
  classification in the install ledger

## 2026-04-08 Follow-Up
- `v0.1.10` cleaned the hosted `install.sh` happy path, but pinned-runtime
  release-proof lanes still print `Failed to load a trusted root key:
  unsupported key type: 7` before successful `OK:` asset lines during
  dogfood activation, consumer rehearsal, and GA gate.
- Next release must carry the same success-clarity contract through those
  managed-runtime verification paths instead of treating the hosted installer
  cleanup as end-to-end completion.
- Bound residual bug: [CB-076](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-08-successful-pinned-runtime-verification-still-prints-scary-trusted-root-key-warning-noise.md)

## Outcome
- Bound to `B-056` under `B-048`.
