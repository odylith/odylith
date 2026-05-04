# Odylith Benchmark Metrics And Priorities

`proof` is the governing benchmark for the report-visible Odylith operating-policy
comparison.

The live `proof` lane is the public product comparison. It measures the full
Odylith operating policy around the same host: grounding, bounded evidence
selection, validator-backed closure evidence, write admission, validation, and
recovery posture. This is the strong operating-policy benchmark.
The Grounding Benchmark is the packet-and-prompt tuning surface. A Grounding
Benchmark win that harms `proof` is a regression.

The primary public question is:

- Does the report-visible Odylith operating policy make the same host agent reach a
  more validated, better-grounded, and less needlessly mutating outcome than the
  raw host CLI on the same measured contracts?

The benchmark proves that Odylith supplies a better operating policy around the
same model: stronger grounding, explicit write admission, validator-backed
closure, and recovery behavior under a matched-host contract.

This means validator-backed non-mutating closure is the intended write-admission
win: Odylith suppresses repository mutation when the disposable benchmark
workspace already satisfies the focused task contract. Any row carried by a
focused closure basis is validated non-mutation evidence under the measured
scenario contract.

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

The benchmark uses four layers:

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
- `Fairness and contract integrity`
  the public `odylith_on` versus `odylith_off` pair fails closed when the live
  comparison drifts from the declared contract or the report stops surfacing
  the comparison basis explicitly. These checks are release-blocking because
  they decide whether the paired benchmark is honest at all.
- `Write-admission honesty`
  non-mutating closure rows must carry product Turn Gate early-exit proof.
  They remain visible in the report as write-admission wins only when the
  receipt source is `product_turn_gate`, the write set is empty, and the
  validator evidence is exposed.
- `Advisory mechanism checks`
  packet coverage, widening frequency, route posture, and similar mechanism
  signals stay visible for diagnosis, but they are explanatory unless they
  show up as real outcome regressions.

Current live-proof secondary guardrail:

- `within_budget_rate >= 0.80` on packet-backed sampled slices

Current Grounding Benchmark lane efficiency guardrails:

- median prompt-bundle delta `<= +64` tokens
- median total-payload delta `<= +96` tokens

## Full-Product Comparison Contract

For the public live pair:

- `odylith_on` means the full Odylith assistance stack:
  grounding packet, selected docs and repo anchors, execution-engine
  posture, truthful next-move hints, report-visible validator evidence,
  product Turn Gate decisions, execution capsules, receipts, tool/stop gate
  summaries, and bounded orchestration or recovery policy. When product
  early-exit proof shows the scenario already closed, `odylith_on` may
  correctly stop before invoking the live host; that outcome is
  write-admission proof.
- `odylith_off` means the same raw host CLI with those Odylith assistance
  affordances disabled.

This is an explicit-assistance benchmark. Every intentional Odylith
advantage is:

- declared in the comparison contract
- surfaced in the machine-readable report
- held to the same same-host, same-validator, same-workspace fairness bar

## Fairness Contract

The benchmark fails closed if the live pair drifts from the declared contract.

Examples of release-blocking fairness findings:

- `odylith_on` receives undeclared Turn Gate evidence
- `odylith_off` loses prompt-visible path attribution for anchors the prompt
  actually showed
- the report cannot surface `comparison_contract`, `preflight_evidence_*`,
  `turn_gate_decision`, `turn_gate_receipt`, `execution_capsule`,
  `observed_path_sources`, `validator_status_basis`,
  `fairness_contract_passed`, or `fairness_findings` explicitly

Focused validator evidence remains a compatibility input only when the scenario
declares it and the runner executes it inside the disposable benchmark
workspace. If that evidence carries a non-mutating closure lane to completion,
the report must expose the product Turn Gate early-exit proof explicitly.

## Execution Engine Metrics

Execution Engine benchmark slices are hard-gated when present. Current
required rates on sampled execution-engine rows:

- `execution_engine_present_rate = 1.0`
- `execution_engine_resume_token_present_rate = 1.0`
- `execution_engine_false_admit_rate = 0.0`
- `execution_engine_false_deny_rate = 0.0`
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
- `execution_engine_component_id_accuracy_rate = 1.0`
- `execution_engine_canonical_component_id_accuracy_rate = 1.0`
- `execution_engine_identity_status_accuracy_rate = 1.0`
- `execution_engine_target_component_status_accuracy_rate = 1.0`
- `execution_engine_snapshot_reuse_status_accuracy_rate = 1.0`
- `execution_engine_reanchor_accuracy_rate = 1.0`
- `execution_engine_delegation_guard_accuracy_rate = 1.0` whenever the sampled
  corpus includes delegation-guard rows
- `execution_engine_parallelism_guard_accuracy_rate = 1.0` whenever the
  sampled corpus includes parallelism-guard rows

Execution Engine benchmark slices also report lower-is-better hot-path cost
diagnostics:

- `execution_engine_median_context_packet_build_ms`
- `execution_engine_median_snapshot_duration_ms`
- `execution_engine_median_prompt_bundle_tokens`
- `execution_engine_median_runtime_contract_tokens`
- `execution_engine_median_total_payload_tokens`

## Corpus Seriousness Floor

The benchmark only earns a serious operating-policy publication claim if the
tracked corpus and the published proof both clear these bars:

- at least `60` tracked operating-policy scenarios
- at least `35` write-plus-validator scenarios, interpreted as scenarios that
  are allowed to require mutation and must be validated, with each passing row
  classified by its visible closure basis
- at least `12` correctness-critical scenarios
- mechanism-heavy operating-policy families at or below `40%` of
  operating-policy scenarios
- required real-world families present in the tracked corpus:
  `api_contract_evolution`, `stateful_bug_recovery`,
  `external_dependency_recovery`, and `destructive_scope_control`
- the latest published proof covers the full current tracked corpus

Packet-only Grounding Benchmark scenarios may use bounded `benchmark.packet_fixture`
data to restore declared proof-state or external-state fields into the packet
seam, but that mechanism is scaffolding for packet-truth evaluation only. It
keeps the live fairness contract intact and keeps published proof credit on the
declared report basis.

## What Each Tier Means

| Tier | What It Asks |
| --- | --- |
| Correctness and non-regression | Did the run land on the right answer path without hidden damage or broken invariants? |
| Grounding recall and precision | Did Odylith surface the files, components, diagrams, bugs, and runtime truth that mattered, while avoiding the wrong surfaces? |
| Validation success and execution fit | Did the run produce something that validates, and did it match the scenario's expected execution posture? |
| Write admission | Did Odylith mutate only when mutation was admitted by evidence, and stop cleanly when validators already proved closure? |
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
- Did canonical `execution-engine` identity survive the packet, summary,
  router, and benchmark layers without historical alias recovery?
- Did Context Engine to Execution Engine snapshot reuse stay explicit, so
  surfaces do not silently rebuild a different posture?
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

- Odylith clears status by winning or holding the higher tiers first
- it keeps lower-tier latency and token metrics inside the explicit guardrails
  while winning or holding the higher tiers

## Closeout Framing

Benchmark writeups should state measured results first. If Odylith is named
directly beyond lane labels, keep that to one evidence-backed
`Odylith Assist:` line at closeout or for explicit visibility-feedback
fallback, backed by measured proof or a measured report, prefer
`**Odylith Assist:**` when Markdown is available, lead with the user win, link
updated governance IDs inline only when they actually changed, name affected
governance-contract IDs from bounded request or packet truth when no governed
file moved, and only frame the edge against `odylith_off` or the broader
unguided path when the evidence supports it. Keep the voice crisp, authentic,
clear, simple, insightful, soulful, friendly, free-flowing, human, and factual.
Use only concrete observed counts, measured deltas, or validation outcomes;
silence is better than filler. If a supplemental closeout line appears, it must
render before the final Assist line. Follow
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

Coding agents create value by moving in the right direction first.

Odylith only wins when it makes the agent:

- more correct
- more grounded
- more precise
- more reliable

and only after that, faster or cheaper.
