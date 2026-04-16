# Remediator
Last updated: 2026-04-09


Last updated (UTC): 2026-04-09

## Purpose
Remediator is Odylith's bounded correction-packet compiler. It converts an
adjudicated Tribunal case into one explicit execution plan with a defined mode,
scope, validation contract, rollback posture, and stale guards.

## Scope And Non-Goals
### Remediator owns
- Execution-mode selection for correction packets.
- Packet compilation for deterministic, AI-engine, hybrid, and manual modes.
- Compact packet summaries for surfaces and ledgers.
- Deterministic execution for the small allowlisted subset of packets.

### Remediator does not own
- Diagnosing cases. That belongs to Tribunal.
- Approving packets. Approval is an external policy decision.
- Performing unrestricted semantic code edits directly.
- Next-action admissibility. Execution Engine may screen a packet's
  intended move before execution, but Remediator itself only compiles bounded
  correction plans.

## Developer Mental Model
- Remediator is intentionally conservative.
- Its default posture is to narrow action, not to maximize automation.
- If a case cannot be expressed as a bounded trustworthy packet, the result
  should be `manual`, not a best-effort guess.

## Runtime Contract
- Main implementation:
  `src/odylith/runtime/reasoning/remediator.py`
- Runtime decision ledger path:
  `odylith/runtime/odylith-decisions.v1.jsonl`
- Packet schema:
  `odylith/runtime/contracts/correction_packet.v1.schema.json`
- Supporting operator notes:
  [TRIBUNAL_AND_REMEDIATION.md](TRIBUNAL_AND_REMEDIATION.md)

Supported execution modes are:
- `deterministic`
- `ai_engine`
- `hybrid`
- `manual`

## Packet Shape
Every correction packet is a structured JSON object with the same core fields:
- `id`
- `fingerprint`
- `case_id`
- `outcome_id`
- `execution_mode`
- `execution_governance`
- `approval_scope`
- `goal`
- `preconditions`
- `touched_paths`
- `commands`
- `ai_handoff`
- `validation_steps`
- `rollback_steps`
- `stale_conditions`
- `expected_evidence_after_success`
- `status`

The packet fingerprint is derived from case id, outcome id, execution mode,
touched paths, and goal.

## Selection Rules
`compile_correction_packet(...)` narrows cases using explicit rules.

### Deterministic refresh packets
Selected when the case is effectively render or refresh drift, including:
- `render_drift`
- stale or cross-surface authority cases where the touched paths remain within
  render/runtime artifact scope and do not look like evaluator changes

The deterministic packet typically runs:
- `odylith sync --repo-root . --force`

### Deterministic traceability packets
Selected for orphan traceability cases touching:
- `odylith/radar/source/ideas/`
- `odylith/radar/traceability-autofix-report.v1.json`

### AI-engine packets
Selected when the touched paths look like evaluator or reasoning-layer changes.
These packets do not run commands directly. They carry an `ai_handoff` block
with:
- subject
- goal
- allowed paths
- constraints
- validation steps
- rollback steps

### Hybrid packets
Selected for bounded ambiguity cases such as:
- `unsafe_closeout`
- `cross_surface_conflict`
- `false_priority`

Hybrid packets combine deterministic prep or validation with a bounded AI
handoff for the semantic part of the change.

### Manual packets
Everything else fails closed to `manual`.

## Deterministic Apply Semantics
`apply_deterministic_packet(...)` is intentionally narrow:
- it refuses any packet whose `execution_mode` is not `deterministic`
- it requires a non-empty `commands` list
- each command must be a non-empty list of argv tokens
- it refuses packets whose embedded execution-engine admissibility outcome
  is not `admit`
- commands execute under `repo_root`
- the result is a structured object with:
  - `ok`
  - `error`
  - `returncode`

It does not perform approval checks. The caller must enforce those.

## Packet Summary Contract
`packet_summary(...)` exposes the compact rendering shape surfaces need:
- packet id and fingerprint
- case id and outcome id
- execution mode
- goal
- approval scope
- touched paths
- status
- execution-engine outcome, mode, and authoritative lane

This lets Compass and related surfaces show posture without embedding the entire
packet body.

## Guardrails
- Deterministic execution is limited to trusted local script flows.
- Semantic code changes are described through `ai_handoff` or `hybrid`
  contracts rather than executed implicitly.
- Every packet must describe validation and rollback, even when the rollback is
  explicitly manual.
- Stale guards are part of the packet contract. If the dossier changes, the
  packet should be treated as invalid until recompiled.

## What To Change Together
- New packet family:
  update packet selection logic, the correction-packet schema if needed, packet
  summaries, and any approval/execution consumers.
- New deterministic command flow:
  keep it narrow, validate the touched-path scope, and add stale conditions.
- New AI-engine or hybrid handoff rule:
  update constraints, validation, and rollback expectations together.
- New touched-path heuristic:
  keep it aligned with Tribunal observations so packet mode does not drift from
  case semantics.

## Failure And Recovery Posture
- Unknown or weakly bounded cases should compile to `manual`.
- Failed deterministic execution should return structured failure, not partially
  claim success.
- If touched paths expand beyond the approved scope, the packet should become
  stale rather than silently proceed.
- If the configured AI engine is unavailable or untrusted at execution time,
  `ai_engine` and `hybrid` packets should not be treated as automatically
  runnable.

## Debugging Checklist
- Inspect `execution_mode` first. If the packet is `manual`, the issue is
  usually insufficient bounded scope, not missing automation.
- Inspect `touched_paths` and `stale_conditions` before widening a packet.
- Inspect `validation_steps` and `rollback_steps` before approving new packet
  families.
- For deterministic packets, run the packet through
  `apply_deterministic_packet(...)` in a test before assuming the problem is in
  Tribunal.

## Validation Playbook
### Remediation
- `pytest -q tests/unit/runtime/test_remediator.py tests/unit/runtime/test_tribunal_engine.py`
- `odylith benchmark --repo-root . --help`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Promoted Remediator into Odylith's own product registry and component-spec set so bounded corrective guidance is documented and governed inside the public repo. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-08: Moved Remediator into the dedicated `src/odylith/runtime/reasoning/` package, removed the legacy eval-path module, and aligned the governed Atlas and delivery-intelligence path truth so sync and surface consumers no longer claim the deleted package shape. (Plan: [B-061](odylith/radar/radar.html?view=plan&workstream=B-061))
- 2026-04-09: Clarified that Remediator compiles bounded correction packets, while Execution Engine owns whether the intended next move is admissible. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
