# Odylith Benchmark Metrics And Priorities

`proof` is the governing benchmark.

The live `proof` lane is the product comparison and the primary optimization
target. The `diagnostic` lane is the packet-and-prompt tuning surface. A
diagnostic win that harms `proof` is a regression.

The real question is not whether Odylith is faster or cheaper in isolation.
The real question is whether it produces the best valid coding outcome across
small, medium, and large or complex repo work.

## Outcome Priority Order

Odylith evaluates benchmark outcomes in this order:

1. Correctness and non-regression
2. Grounding recall and precision
3. Validation success and execution fit
4. Robustness and consistency
5. Latency to a valid outcome
6. Prompt and payload efficiency
7. Bounded behavior under tighter token budgets

## Gate Semantics

The benchmark uses three layers:

- `Hard quality gate`
  Tiers `1-4` are status blockers. If Odylith gets less correct, less
  grounded, less valid, or less consistent, the status stays `hold`.
- `Secondary guardrails`
  Packet-backed live-proof tighter-budget behavior remains status-blocking.
  Architecture-only or other non-packet sampled slices do not fail this
  guardrail just because no packet rows are present. Time to valid outcome and
  full-session token spend stay published, but they are not primary status
  gates because they are not measured on the same basis as solo-user latency
  or initial prompt size.
- `Advisory mechanism checks`
  Packet coverage, widening frequency, route posture, and similar signals stay
  visible for diagnosis, but they are explanatory signals unless they show up
  as real outcome regressions.

Current live-proof secondary guardrail:

- `within_budget_rate >= 0.80` on packet-backed sampled slices

Current diagnostic-lane efficiency guardrails:

- median prompt-bundle delta `<= +64` tokens
- median total-payload delta `<= +96` tokens

Current live-proof discipline metrics when proof-backed benchmark scenarios are present:

- `false_clearance_rate = 0.0`
- `proof_frontier_gate_accuracy_rate = 1.0`
- `proof_claim_guard_accuracy_rate = 1.0`
- `proof_same_fingerprint_reuse_rate = 1.0` whenever the sampled corpus actually includes same-fingerprint proof rows

Current Context Engine grounding metrics when Context Engine benchmark scenarios are present:

- `context_engine_packet_source_accuracy_rate = 1.0`
- `context_engine_selection_state_accuracy_rate = 1.0`
- `context_engine_workstream_accuracy_rate = 1.0`
- `context_engine_fail_closed_ambiguity_rate = 1.0`
- `context_engine_session_namespace_rate = 1.0` whenever the sampled corpus actually includes runtime-backed Context Engine rows

## What Each Tier Means

| Tier | What It Asks |
| --- | --- |
| Correctness and non-regression | Did the run land on the right answer path without hidden damage or broken invariants? |
| Grounding recall and precision | Did Odylith surface the files, components, diagrams, bugs, and runtime truth that mattered, while avoiding the wrong surfaces? |
| Validation success and execution fit | Did the run produce something that validates, and did it match the scenario's expected execution posture? |
| Robustness and consistency | Does Odylith still hold up across warm and cold cache posture, reruns, ambiguity, stale state, and recovery paths? |
| Latency to a valid outcome | How long did the live run take to reach a validated answer? |
| Prompt and payload efficiency | How much prompt or session budget did Odylith require to get there? |
| Bounded behavior under tighter token budgets | Does Odylith degrade gracefully when the token budget tightens? |

For live blocker lanes, those tiers are supplemented by proof-discipline checks:

- Does the packet expose a real proof lane when one resolves?
- Does it avoid claiming `fixed live` before the hosted frontier advances?
- Does claim-guard labeling match the actual proof tier?
- Does a repeated fingerprint stay pinned to the same blocker seam?

For Context Engine architecture work, those tiers are also supplemented by
grounding-control checks:

- Did the adaptive or explicit packet choose the right lane for the slice?
- Did the packet resolve the right workstream or say `none` explicitly?
- Did ambiguous scope stay fail-closed instead of becoming route-ready by accident?
- Did runtime-backed slices keep session scope namespaced?

## Release Rule

A lower-tier win never excuses a higher-tier regression.

That means:

- faster but less correct is a failure
- cheaper but less grounded is a failure
- smaller prompts but weaker validation is a failure
- lower latency with worse precision is a failure

The inverse is also true:

- Odylith does not need to beat raw latency or raw token cost to clear status
- it does need to keep those lower-tier metrics inside the explicit guardrails
  while winning or holding the higher tiers

## Closeout Framing

Benchmark writeups should state measured results first. If Odylith is named
directly beyond lane labels, keep it brief and secondary to the evidence.
Keep that to one final-only `Odylith Assist:` line backed by measured proof or
a measured report, and follow
[Odylith Chatter](../../odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md)
for the detailed closeout wording contract.

## Eval Quality Requirements

The benchmark is only trustworthy if the corpus measures the right work:

- small, medium, and large or complex repo work
- single-file, cross-file, and cross-surface scenarios
- correctness-sensitive and recovery-sensitive tasks
- both warm and cold cache posture where applicable
- harder, more realistic, or more reproducible cases over time, never easier

## Why This Order Exists

Coding agents do not create value by being fast in the wrong direction.

Odylith only wins when it makes the agent:

- more correct
- more grounded
- more precise
- more reliable

and only after that, faster or cheaper.
