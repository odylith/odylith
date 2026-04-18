# Tribunal

## Odylith Discipline Contract
- Tribunal owns the Judgment facet. Repeated, ambiguous, costly, or false
  allow/block pressure becomes a Tribunal candidate with rival explanations and
  discriminating next checks.
- Tribunal may promote a pattern into doctrine, tool affordance, skill
  guidance, benchmark case, or Casebook bug. It is not the hot path and must
  not run provider reasoning for ordinary Odylith Discipline decisions.
Last updated: 2026-04-17


Last updated (UTC): 2026-04-17

## Purpose
Tribunal is Odylith's diagnosis engine. It converts delivery scopes into
grounded dossiers, runs a fixed multi-actor reasoning pass over each case,
adjudicates disagreements into one explicit case form, and emits ranked cases
plus one bounded correction packet per case.

## Scope And Non-Goals
### Tribunal owns
- Candidate selection from delivery scopes.
- Dossier construction and evidence shaping.
- Multi-actor memo generation.
- Adjudication and confidence scoring.
- Optional provider enrichment with evidence validation.
- Ranked case queue and systemic brief generation.
- Compact Tribunal summaries that can feed the visible intervention value
  engine with precomputed risk, causal, and discriminating-next-check signals.
  Tribunal supplies structured diagnosis evidence; it does not decide whether
  a visible Odylith block should render.
- The shape of Tribunal-ready signals consumed downstream. Guidance Behavior
  runtime may emit a compact Tribunal-ready signal for intervention evidence,
  but that signal must remain precomputed evidence unless a real Tribunal pass
  is explicitly invoked elsewhere.

### Tribunal does not own
- Executing corrective action. That belongs to the caller and Remediator.
- Replacing deterministic grounding with unvalidated provider output.
- Surface rendering. It produces structured payloads consumed elsewhere.
- Live agent chatter. Chatter may consume precomputed Tribunal-backed payloads,
  but Tribunal must not be invoked on demand just to narrate a turn.
- Live signal selection or chat-visible proof. The Governance Intervention
  Engine may consume cached Tribunal summaries in the hot path, but provider
  Tribunal calls are forbidden inside live visibility checks.
- Guidance Behavior validation. Tribunal may be referenced by the compact
  `tribunal_signal`, but the validator and corpus remain owned by the
  governance validation runtime.
- Next-action admissibility. Execution Engine consumes diagnosis as one
  evidence input, but Tribunal does not decide whether the intended command is
  procedurally allowed.

## Developer Mental Model
- Tribunal is the reasoning layer between delivery posture and corrective
  action.
- Deterministic local reasoning is the baseline.
- External provider output is optional, advisory, and must validate against
  named evidence.
- Each case is cached by scope key and evidence fingerprint so repeated refresh
  passes can reuse stable work.
- Delivery-intelligence and shell refresh may consume deterministic Tribunal
  fallback when the persisted reasoning artifact is absent; that hot path must
  not opportunistically start provider-backed reasoning just to refresh UI.

## Runtime Contract
- Main implementation:
  `src/odylith/runtime/reasoning/tribunal_engine.py`
- Reasoning configuration:
  `odylith/runtime/odylith-reasoning.v4.json`
- Supporting design notes:
  [odylith-tribunal-and-remediation-design.md](odylith-tribunal-and-remediation-design.md)
  and [TRIBUNAL_AND_REMEDIATION.md](TRIBUNAL_AND_REMEDIATION.md)

Tribunal is usually invoked from higher-level runtime flows such as `odylith
sync`, surface generation, and evaluation or benchmark paths rather than via a
dedicated standalone CLI.

## Candidate Selection
Tribunal does not run on every scope blindly.

### Eligible scopes
`_candidate_selection(...)` starts from delivery scopes and keeps only scopes
that are:
- of supported type: `workstream`, `component`, or `diagram`
- marked `live_actionable`
- not already in the `clear_path` scenario

### Ranking
Eligible scopes are ordered by a stable banded ranking that considers:
- scope type rank
- scenario priority
- severity rank
- decision debt
- governance lag
- blast radius severity
- stable scope-id tie-breaks

### Focus set construction
The focused visible queue is built in two passes:
1. scenario coverage first
   Ensure the visible set covers distinct scenario classes.
2. priority fill second
   Fill remaining slots with the next highest-ranked cases.

The selection summary records what was shown, what overflowed, and why.

## Dossier Construction
For each focused scope, Tribunal builds a dossier containing:
- `case_id`
- subject metadata
- decision at stake
- observations derived from scope posture
- baseline scenario and severity
- evidence quality
- normalized explanation facts
- evidence items

Evidence items are the grounding substrate used for both actor memos and any
provider validation.

## Actor Model
Tribunal runs a fixed actor roster in this order:
- `observer`
  Summarizes grounded facts and visible state.
- `ownership_resolver`
  Tests ownership and authority claims.
- `causal_analyst`
  Explains why the posture likely emerged.
- `policy_judge`
  Checks policy-boundary conflicts.
- `normative_judge`
  Evaluates what the system should prefer, not just what currently exists.
- `adversary`
  Stress-tests the leading narrative.
- `counterfactual_analyst`
  Looks for discriminating alternate explanations.
- `gap_analyst`
  Identifies evidence weakness or missing proof.
- `risk_analyst`
  Evaluates downside if the current diagnosis is wrong.
- `prescriber`
  Narrows the case into a bounded next-action claim.

The actor roster is versioned by `actor_policy_version` so cache reuse can be
invalidated when reasoning policy changes.

## Adjudication Pipeline
1. Build actor memos from the same dossier and evidence set.
2. Run `_adjudicate(...)` to synthesize a case form, leading explanation,
   strongest rival, risk if wrong, and discriminating next check.
3. Optionally run provider enrichment if the case is in the provider focus set
   and passes provider-gate checks.
4. Validate provider fields against grounded evidence before accepting them.
5. Score confidence using observations, memo agreement, and provider validation
   status.
6. Re-adjudicate with final confidence and actor influence metadata.
7. Build the maintainer brief and queue row.
8. Hand the case to Remediator for packet compilation.

## Provider Enrichment Model
Provider enrichment is narrow by design.

### What the provider may refine
Tribunal only accepts provider refinement for a limited field set:
- `leading_explanation`
- `strongest_rival`
- `risk_if_wrong`
- `discriminating_next_check`
- `maintainer_brief`

### When provider use is allowed
Provider use depends on:
- provider availability
- whether the scope is in the focused provider subset
- whether evidence quality and proof routing are strong enough

The shared reasoning adapter may resolve provider availability from the active
local coding agent CLI when Odylith is already running inside Codex or Claude
Code. Explicit endpoint-backed configuration remains supported, but it is not
required for the default local product path.

When a provider times out or loses transport during one Tribunal build,
Tribunal must degrade the remainder of that run back to deterministic reasoning
instead of repeating the same provider stall case after case. This is a
runtime-health guard, not a silent success path.

### Output states
The final Tribunal payload reports:
- `deterministic-only`
  No provider used.
- `ready`
  Provider was available but did not produce validated enrichment.
- `hybrid`
  Provider enrichment was used and validated.

If provider validation fails, the degraded reason is explicit rather than
silently merged into the case.

## Cache Model
Previous cases can be reused when:
- `actor_policy_version` matches
- scope key matches
- evidence fingerprint matches
- provider-attempt requirements still align with the current gate

This allows Tribunal to avoid recomputing unchanged cases while still
invalidating stale reasoning when evidence or reasoning policy changes.

## Output Contract
`build_tribunal_payload(...)` returns a payload containing:
- `version`
- `state`
- `provider` and `model`
- `degraded_reason`
- `provider_used` and `provider_validated`
- provider counts and validation errors
- `actor_policy_version`
- `selection_summary`
- `cases`
- `case_queue`
- `findings`
- `systemic_brief`
- `cache`
- `stats`

Each case contains:
- dossier
- actor memos
- adjudication
- maintainer brief
- reasoning metadata
- one correction packet
- one queue row
- selection metadata

## Queue And Brief Generation
Tribunal emits two human-facing compressed outputs:
- `queue_row`
  The compact case summary used by surfaces and inbox views.
- `systemic_brief`
  The cross-case summary describing what patterns dominate the visible queue.

These are derived outputs from the full case set and should not become the only
debugging surface for diagnosis changes.

Precomputed `case_queue`, case refs, proof routes, and `systemic_brief`
outputs may be consumed by downstream narration contracts such as
`odylith-chatter`, but only through already-built packet or delivery payload
truth. That consumption must never trigger a fresh Tribunal pass during normal
agent execution.

Guidance Behavior summaries follow the same rule. Their `tribunal_signal`
payload is a compact, downstream-readable diagnosis cue; it must not be treated
as permission to run provider-backed Tribunal reasoning inside prompt,
checkpoint, Stop, or visibility-status hot paths.

## Guardrails
- Provider output never bypasses grounded evidence.
- Candidate selection is intentionally capped. Tribunal diagnoses the most
  relevant visible scopes, not every possible scope in one pass.
- Ownership ambiguity and evidence gaps are surfaced explicitly instead of
  flattened into a false-confidence diagnosis.
- Tribunal does not clear, fix, or mutate cases on its own. It diagnoses and
  proposes bounded next action.
- Provider runtime failure must degrade coherently: one timeout or transport
  failure disables provider enrichment for the remaining cases in that run and
  records the degraded reason explicitly.

## What To Change Together
- New actor or actor-policy change:
  update the actor roster, adjudication logic, cache versioning, and any tests
  that assume memo order or actor influence.
- New scenario or queue-shaping rule:
  update candidate selection, queue-row generation, and systemic brief logic.
- New provider contract:
  update the allowed provider fields and validation logic together.
- New case payload field:
  update cache reuse and case serialization, not just the surface renderer.

## Debugging Checklist
- Inspect the focused scope selection and `selection_summary` before debugging
  the actor logic.
- Compare `reasoning.state`, `provider_used`, and `provider_validated` to see
  whether a difference came from deterministic logic or provider enrichment.
- Inspect `confidence_factors` and `actor_influence` before changing the queue
  order heuristics.
- Use the cached-case path carefully: stale conclusions often mean the evidence
  fingerprint or actor-policy version did not change when it should have.

## Validation Playbook
### Diagnosis
- `pytest -q tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_odylith_reasoning.py`
- `odylith benchmark --repo-root . --help`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Promoted Tribunal into Odylith's own product registry and component-spec set so diagnosis no longer depends on consumer-local product documentation. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-07: Clarified and shipped the downstream contract that lets `odylith-chatter` consume precomputed Tribunal-backed case and systemic-brief truth without invoking live Tribunal during ordinary narration. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-08: Moved Tribunal fully out of `runtime/evaluation` into `src/odylith/runtime/reasoning/`, removed the legacy eval-path module, and hardened sync-owned Atlas and delivery-intelligence references plus regression guards so governed surfaces track the new package boundary without compatibility shims. (Plan: [B-061](odylith/radar/radar.html?view=plan&workstream=B-061))
- 2026-04-09: Clarified the product boundary that Tribunal diagnoses why a posture exists, while Execution Engine decides whether the next move is admissible. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
- 2026-04-17: Documented the Guidance Behavior runtime's Tribunal-ready signal as precomputed downstream evidence for the intervention engine, not a live Tribunal invocation or provider-backed hot-path dependency. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-17: Clarified that the Guidance Behavior Tribunal-ready signal now travels with the platform end-to-end contract, letting downstream evidence reference benchmark/eval and host-lane proof posture without invoking Tribunal or expanding context on the live path. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-123`)
