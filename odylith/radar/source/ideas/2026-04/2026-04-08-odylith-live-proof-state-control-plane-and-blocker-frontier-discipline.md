---
status: finished
idea_id: B-062
title: Live Proof-State Control Plane and Blocker Frontier Discipline
date: 2026-04-08
priority: P1
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: proof-state contract and runtime ledger, delivery intelligence snapshots and operator readouts, Tribunal case rows and cache reuse, context-engine packets, Compass timeline and standup inputs, shell proof links and queue previews, Registry proof bands, Casebook proof-lane metadata, and chatter claim lint
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Odylith can already stay broadly grounded on active workstreams, but live deploy and rehearsal lanes still drift when one blocker fingerprint remains unchanged and the product cannot keep the proof frontier, falsification memory, and claim tier pinned across surfaces.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-08-odylith-live-proof-state-control-plane-and-blocker-frontier-discipline.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on:
workstream_blocks:
related_diagram_ids: D-004,D-026
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
Odylith currently grounds operators to the right workstream, plan, and bug
neighborhood, but it does not carry one authoritative proof-state lane that
pins the active live blocker, failing phase, fingerprint, falsification
history, and truthful evidence tier all the way through delivery, Tribunal,
context packets, Compass, shell previews, Registry, and chatter.

That gap lets a session stay "grounded" while still drifting away from the
unchanged live blocker. Local fixes, preview proof, and adjacent polish can be
mistaken for progress on the primary seam even when the same hosted failure
fingerprint keeps reproducing.

## Customer
- Primary: maintainers and advanced operators proving live deploy or rehearsal
  fixes where one blocker fingerprint must stay pinned until the hosted ladder
  advances.
- Secondary: reviewers, copilots, and runtime surfaces that need to know
  whether "fixed" means diagnosed, code-only, preview-tested, deployed, or
  actually live-cleared.

## Opportunity
Introduce one canonical additive `proof_state` contract plus a split-authority
ledger that turns proof discipline into product behavior instead of maintainer
memory.

## Proposed Solution
- add a first-class `proof_state` contract that follows a single `lane_id`
  through delivery snapshots, Tribunal case rows, grounded packets, shell
  previews, Compass, Registry, and chatter
- persist runtime live-proof observations in the existing
  `.odylith/runtime/odylith-proof-surfaces.v1.json` ledger under a new
  `live_proof_lanes` section
- treat Casebook or plan metadata as authority for blocker identity and
  clearance condition, while runtime proof memory owns live attempts,
  falsifications, repeated-fingerprint memory, deployment truth, and frontier
  movement
- add proof drift detection and claim lint so surfaces can warn when activity
  is piling up in non-primary categories while the same live blocker remains
  open
- keep the first landing additive by extending existing payloads rather than
  cutting a new delivery or Tribunal artifact version

## Scope
- proof-state module family and runtime ledger helpers
- Casebook proof-lane metadata parsing and additive packet fields
- delivery-intelligence, Tribunal, context-packet, shell, Compass, Registry,
  and chatter integration
- shared claim-guard shaping for answer-time status language
- focused governance source, Atlas, and Registry updates that make the new
  contract auditable

## Non-Goals
- redesigning Tribunal actor policy
- changing live deploy semantics or external provider policy
- replacing Radar, Casebook, or plan source-of-truth with runtime-only memory
- auto-mutating Casebook markdown just because a repeated fingerprint is seen

## Risks
- a weak precedence model could let heuristics override explicit bug or plan
  truth
- repeated-fingerprint memory could misfire if lane identity or fingerprint
  normalization is unstable
- claim lint could become noisy if it rewrites truthful partial-progress
  language instead of only blocking misleading "fixed live" claims
- adding proof-state to too many hot paths without extraction would worsen the
  existing red-zone coordinator files instead of decomposing them

## Dependencies
- no hard external dependency; this slice should stay deterministic and useful
  even when provider enrichment is absent
- B-047 remains a related queued follow-on for broader Tribunal default-diagnosis
  productization

## Success Metrics
- live-proof packets show one explicit blocker, fingerprint, first failing
  phase, frontier, and clearance rule when one lane resolves cleanly
- repeated live failures on the same fingerprint mark the prior claim as
  falsified instead of looking like a fresh mystery
- shell, Compass, Registry, and grounded packets all project the same proof
  lane instead of inventing separate summaries
- claim language below `live_verified` stops emitting unqualified `fixed`,
  `cleared`, or `resolved`
- proof drift warnings appear when the blocker remains open but recent activity
  skews toward non-primary work categories

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_proof_state_runtime.py tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_tribunal_engine.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_tooling_dashboard.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_odylith_assist_closeout.py`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- focused shell and Compass browser proof if payload or rendering contracts move

## Rollout
Land the governed source and extracted proof-state helpers first, then thread
the additive contract through delivery, Tribunal, packets, and surfaces in one
bounded implementation wave so the first shipped proof-state lane is coherent.

## Why Now
Odylith is increasingly strong at workstream grounding, but the product still
lets proof discipline drift when the only thing that really matters is whether
the hosted frontier moved past the previous failing phase.

## Product View
The product should never let "fixed in code", "preview passes", or adjacent
polish masquerade as live blocker clearance when the same hosted failure
fingerprint is still the frontier.

## Impacted Components
- `proof-state`
- `odylith-context-engine`
- `tribunal`
- `dashboard`
- `compass`
- `casebook`
- `odylith-chatter`

## Interface Changes
- additive `proof_state` payloads on delivery scopes, operator queue items,
  Tribunal case rows, and grounded packets
- new proof-state enums: `proof_status` and `work_category`
- additive `claim_guard` bundle for answer-time status lint
- additive Casebook proof-lane metadata fields and runtime-ledger section
  `live_proof_lanes`

## Migration/Compatibility
- additive first landing; existing payload readers should degrade cleanly if
  they ignore `proof_state`
- no artifact version bump unless compatibility tests prove it is required
- missing deployment-truth fields degrade to `unknown`, not guessed values

## Test Strategy
- characterize explicit-source, runtime-ledger, and inferred-only lanes
- prove repeated-fingerprint falsification and same-bug reuse
- prove frontier advancement only when a live run clears the prior failing
  phase
- prove claim-guard suppression of misleading live-fix language

## Open Questions
- none required to start implementation; the main design choice is shipping a
  coherent end-to-end additive slice instead of another local-only heuristic
