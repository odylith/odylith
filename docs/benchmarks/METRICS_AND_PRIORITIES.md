# Odylith Benchmark Metrics And Priorities

`proof` is the governing benchmark.

The live `proof` lane is the product comparison and the primary optimization
target. The `diagnostic` lane is the packet-and-prompt tuning surface. A
diagnostic win that harms `proof` is a regression.

The primary public question is:

- Does the full Odylith assistance stack make the same host agent perform
  better on real coding work than the raw host CLI?

The benchmark is not trying to prove that Odylith beats the base model's
weights. It is trying to prove that Odylith supplies a better operating policy
around the same model.

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
  tiers `1-4` are status blockers. If Odylith gets less correct, less
  grounded, less valid, or less consistent, the status stays `hold`.
- `Secondary guardrails`
  packet-backed live-proof tighter-budget behavior remains status-blocking.
  Architecture-only or other non-packet sampled slices do not fail this
  guardrail just because no packet rows are present. Time to valid outcome and
  full-session token spend stay published, but they are not primary status
  gates because they are not measured on the same basis as solo-user latency
  or initial prompt size.
- `Advisory mechanism checks`
  packet coverage, widening frequency, route posture, fairness findings, and
  similar mechanism signals stay visible for diagnosis, but they are
  explanatory unless they show up as real outcome regressions.

Current live-proof secondary guardrail:

- `within_budget_rate >= 0.80` on packet-backed sampled slices

Current diagnostic-lane efficiency guardrails:

- median prompt-bundle delta `<= +64` tokens
- median total-payload delta `<= +96` tokens

## Full-Product Comparison Contract

For the public live pair:

- `odylith_on` means the full Odylith assistance stack:
  grounding packet, selected docs and repo anchors, execution-engine
  posture, truthful next-move hints, scenario-declared focused-check shaping,
  preflight focused-check results only when they were executed in the
  disposable benchmark workspace and logged in the report, and bounded
  orchestration or recovery policy.
- `odylith_off` means the same raw host CLI with those Odylith assistance
  affordances disabled.

This is not a hidden-information benchmark. If an Odylith affordance is
intentional product behavior, it must be:

- declared in the comparison contract
- surfaced in the machine-readable report
- held to the same same-host, same-validator, same-workspace fairness bar

## Fairness Contract

The benchmark fails closed if the live pair drifts from the declared contract.

Examples of release-blocking fairness findings:

- `odylith_on` receives undeclared preflight evidence
- `odylith_off` loses prompt-visible path attribution for anchors the prompt
  actually showed
- the report cannot surface `comparison_contract`, `preflight_evidence_*`,
  `observed_path_sources`, `validator_status_basis`,
  `fairness_contract_passed`, or `fairness_findings` explicitly

Focused preflight evidence is allowed only when the scenario declares it and
the runner executes it inside the disposable benchmark workspace. If that
preflight evidence is what carries a no-op lane to completion, the report must
say so explicitly with `validator_status_basis=focused_noop_proxy`.

## Execution Engine Metrics

Execution Engine benchmark slices are hard-gated when present. Current
required rates on sampled execution-engine rows:

- `execution_engine_present_rate = 1.0`
- `execution_engine_resume_token_present_rate = 1.0`
- `execution_engine_outcome_accuracy_rate = 1.0`
- `execution_engine_mode_accuracy_rate = 1.0`
- `execution_engine_next_move_accuracy_rate = 1.0`
- `execution_engine_closure_accuracy_rate = 1.0`
- `execution_engine_wait_status_accuracy_rate = 1.0` whenever the sampled
  corpus includes wait-backed rows
- `execution_engine_validation_archetype_accuracy_rate = 1.0`
- `execution_engine_current_phase_accuracy_rate = 1.0` whenever the
  sampled corpus includes stable phase rows
- `execution_engine_last_successful_phase_accuracy_rate = 1.0` whenever
  the sampled corpus includes stable phase-history rows
- `execution_engine_authoritative_lane_accuracy_rate = 1.0`
- `execution_engine_target_lane_accuracy_rate = 1.0` whenever the sampled
  corpus includes target-lane rows
- `execution_engine_resume_token_accuracy_rate = 1.0`
- `execution_engine_host_family_accuracy_rate = 1.0`
- `execution_engine_model_family_accuracy_rate = 1.0` whenever the sampled
  corpus includes model-family rows
- `execution_engine_reanchor_accuracy_rate = 1.0`

## Corpus Seriousness Floor

The benchmark only earns a serious publication claim if the tracked corpus and
the published proof both clear these bars:

- at least `60` implementation scenarios
- at least `35` write-plus-validator scenarios
- at least `12` correctness-critical scenarios
- mechanism-heavy implementation families at or below `40%` of implementation
  scenarios
- required real-world families present in the tracked corpus:
  `api_contract_evolution`, `stateful_bug_recovery`,
  `external_dependency_recovery`, and `destructive_scope_control`
- the latest published proof covers the full current tracked corpus, not a
  stale subset

Packet-only diagnostic scenarios may use bounded `benchmark.packet_fixture`
data to restore declared proof-state or external-state fields into the packet
seam, but that mechanism is scaffolding for packet-truth evaluation only. It
does not waive the live fairness contract and it does not add hidden credit to
the published proof pair.

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

For live blocker lanes, those tiers are supplemented by proof-discipline
checks:

- Does the packet expose a real proof lane when one resolves?
- Does it avoid claiming `fixed live` before the hosted frontier advances?
- Does claim-guard labeling match the actual proof tier?
- Does a repeated fingerprint stay pinned to the same blocker seam?

For Context Engine architecture work, those tiers are also supplemented by
grounding-control checks:

- Did the adaptive or explicit packet choose the right lane for the slice?
- Did the packet resolve the right workstream or say `none` explicitly?
- Did ambiguous scope stay fail-closed instead of becoming route-ready by
  accident?
- Did runtime-backed slices keep session scope namespaced?

For execution-engine work, those tiers are also supplemented by
execution-engine checks:

- Did the packet and runtime summary preserve the real `admit|deny|defer`
  posture?
- Did the engine keep one truthful next move instead of collapsing into
  generic route hints?
- Did broad or ambiguous scope fail closed into `recover` with the right
  closure posture?
- Did resume tokens and authoritative lanes survive carry-through into the
  public surfaces?

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
directly beyond lane labels, keep that to one final-only `Odylith Assist:`
line backed by measured proof or a measured report, prefer
`**Odylith Assist:**` when Markdown is available, lead with the user win, link
updated governance IDs inline only when they actually changed, name affected
governance-contract IDs from bounded request or packet truth when no governed
file moved, and only frame the edge against `odylith_off` or the broader
unguided path when the evidence supports it. Keep the voice crisp, authentic,
clear, simple, insightful, soulful, friendly, free-flowing, human, and factual.
Use only concrete observed counts, measured deltas, or validation outcomes;
silence is better than filler. Follow
[Odylith Chatter](../../odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md)
for the detailed closeout wording contract.

## Eval Quality Requirements

The benchmark is only trustworthy if the corpus measures the right work:

- small, medium, and large or complex repo work
- single-file, cross-file, and cross-surface scenarios
- correctness-sensitive, recovery-sensitive, external-wait, and
  destructive-scope tasks
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
