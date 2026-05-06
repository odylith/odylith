# Benchmark Formal Model

This note defines the public interpretation contract for Odylith benchmark
results after the Governed Harness turn-gate migration. The benchmark does not
own a private success path. It observes the same product-owned operating policy
that normal Odylith turns use, then records the decision, evidence, actions,
validation, receipts, latency, and token cost.

The measured win is an operating-policy win: better grounded decisions, tighter
write admission, stronger validation honesty, safer completion claims, and less
unnecessary model or tool work under the same task contract.

## Scope

The model is intentionally host model agnostic. It applies to any host adapter
that can receive an Odylith product payload and execute the resulting turn
contract. Host-specific transport details may change; the product Turn Gate,
evidence contract, and public report fields are the invariant surfaces.

This document is not a claim that one host model is better than another. It is
also not a claim that every task can close without tool work. It describes when
a benchmark row is valid public evidence for the Odylith operating policy.

## Rendering Contract

This document must render cleanly in GitHub Markdown. It deliberately avoids
LaTeX display blocks and LaTeX inline math. Equations are written as plain text
inside fenced `text` blocks, and durable report fields or enum tokens stay in
Markdown code spans.

That rule is part of the benchmark contract. Public benchmark interpretation
should not depend on a renderer accepting a particular math macro set.

## Core Entities

| Name | Report surface | Meaning |
| --- | --- | --- |
| `s` | `scenario_id` | One benchmark scenario row. |
| `x_s` | prompt or scenario input | The user turn being evaluated. |
| `r_s` | repo fixture and observed paths | The disposable repository state. |
| `h_s` | `host_profile` or `host_family` | The host capability profile for the row. |
| `m_s` | `mode` | The gate mode, such as `observe`, `advise`, or `enforce`. |
| `P_s` | product payload fields | The Turn Gate payload built from the prompt, policy hints, and focused evidence. |
| `G_O` | product Turn Gate | The Odylith product decision function. |
| `d_s` | `turn_gate_decision` | The product decision for the row. |
| `E_s` | evidence fields | Focused checks, path evidence, policy hints, and validation inputs. |
| `C_s` | `execution_capsule` | The action constraints the host or harness must obey. |
| `rho_s` | `turn_gate_receipt` | The product receipt proving who made the decision. |
| `A_s` | action and tool summaries | Tool admission, stop-gate, and model-call evidence. |
| `W_s` | write-path fields | Observed candidate writes and workspace deltas. |
| `V_s` | validator fields | Validator basis, execution mode, and status evidence. |
| `Y_s` | row status fields | The measured row outcome. |
| `F_s` | fairness findings | Whether the matched-lane fairness contract passed. |

## Product Turn Gate Contract

The product Turn Gate has this shape:

```text
G_O(P_s, r_s, h_s, m_s) -> (d_s, E_s, C_s, rho_s)
```

Inputs:

- `P_s` is the product prompt payload built from the user turn, bounded product
  policy hints, declared validation obligations, and any pre-model evidence the
  host or benchmark has already produced.
- `r_s` is the repository state.
- `h_s` is the host capability profile.
- `m_s` is the gate mode. Implemented mode tokens include `observe`, `advise`,
  and `enforce`.

Outputs:

- `d_s` is the Turn Gate decision.
- `E_s` is the evidence report that supports that decision.
- `C_s` is the execution capsule that constrains the next host action.
- `rho_s` is the harness receipt.

The Odylith-on lane is the host running under this product decision:

```text
odylith_on_policy(P_s, r_s, h_s, m_s) =
  host_execute(G_O(P_s, r_s, h_s, m_s), P_s, r_s, h_s)
```

The benchmark wrapper is only an observation function:

```text
Y_s = benchmark_measure(d_s, E_s, C_s, rho_s, timing_s, V_s, A_s, W_s)
```

The wrapper may sandbox, time, log, and score. It may run focused local checks
before the Turn Gate call to populate `P_s`. It must not independently decide
closure after the product gate has spoken.

The current source implementation maps this contract to
`odylith.runtime.governed_harness.turn_gate.decide_turn(...)`. Live benchmark
rows for the `odylith_on` lane call that product API before any host model
subprocess is invoked.

## Decision Vocabulary

The product Turn Gate emits one of these durable decision tokens:

| Token | Meaning | Public interpretation |
| --- | --- | --- |
| `answer_only` | No repo mutation is needed. | The host should answer from available evidence and policy. |
| `early_exit_proof` | Product evidence already proves the requested closure. | The row may close without host model/tool work only if the receipt and validation contract pass. |
| `diagnostic` | The correct next step is diagnosis. | The row should gather or explain evidence before mutation. |
| `bounded_edit` | A scoped edit is admissible. | The host may mutate only the admitted write surface. |
| `open_ended_implementation` | The task is broad and implementation-shaped. | The host must preserve normal validation and scope controls. |
| `unsafe_needs_user_decision` | The request needs explicit user direction. | The row cannot claim safe completion without the required user decision. |

These tokens are source truth. User-facing surfaces may display friendlier
labels, but reports must preserve the durable token.

## Early-Exit Proof Contract

An early-exit proof is valid only when the product Turn Gate, not the benchmark
wrapper, admits the row:

```text
early_exit_is_valid(s) =
  turn_gate_decision.decision_type == early_exit_proof
  and turn_gate_receipt.source == product_turn_gate
  and turn_gate_product_path_present == true
  and status_basis == turn_gate_early_exit_proof
  and validator_execution_mode == turn_gate_early_exit_proof
  and preflight_evidence_result_status in {passed, not_applicable}
  and focused_checks_cover_declared_contract == true
  and candidate_write_paths is empty
  and workspace_delta_paths is empty
  and prompt_requires_unsafe_side_effect == false
```

The corresponding execution capsule must include constraints equivalent to:

```text
do_not_call_host_model
do_not_mutate_workspace
```

`tool_gate_summary` may be `not_applicable` for a row that exits before any host
tool call exists. The field still has to be present so the absence of
tool-gating activity is explicit instead of ambiguous.

The legacy compatibility hint consumed by
`_non_mutating_closure_allowed(...)` is never sufficient by itself. The gate
still requires product-path presence, focused evidence coverage, a
`product_turn_gate` receipt, and an empty observed write set.

## Scenario Model

A benchmark scenario is:

```text
S_s = (
  scenario_id,
  x_s,
  r_s,
  h_s,
  m_s,
  declared_contract_s,
  validators_s,
  truth_predicate_s
)
```

The declared contract includes required paths, writable paths, cache posture,
timeout policy, host policy, expected report fields, and validator obligations.
Validators are observable approximations of the scenario truth predicate. A row
is public evidence only when the report exposes the validator basis and the
matched-lane fairness contract holds.

## Matched-Lane Fairness

Comparisons must use matched lanes. For each scenario `s`, the Odylith-on lane
and the baseline lane must share the same task contract:

```text
fair_row(s) =
  same_user_turn
  and same_repo_fixture_class
  and same_required_paths
  and same_writable_paths
  and same_validator_family
  and same_timeout_policy
  and same_cache_policy_or_reported_difference
  and compatible_host_capability_profile
  and no outcome-changing evidence omitted
```

If `fair_row(s)` is false, the row may still be useful diagnostic evidence, but
it is not valid paired benchmark evidence.

## Utility Interpretation

Quality is a vector, not a single leaderboard number. The public report does not
need to emit one scalar `Q` field for the interpretation to be valid.

| Component | Meaning | Direction |
| --- | --- | --- |
| `grounded_recall` | Required-path and evidence recall. | Higher is better. |
| `validator_success` | Validator-backed success. | Higher is better. |
| `write_boundary_precision` | Avoidance of unnecessary or out-of-scope writes. | Higher is better. |
| `claim_honesty` | Accuracy of completion and limitation claims. | Higher is better. |
| `token_cost` | Model and prompt token cost. | Lower is better. |
| `wall_time` | End-to-end row latency. | Lower is better. |
| `unsafe_or_unsupported_risk` | Unsafe action or unsupported completion risk. | Lower is better. |

Plain-text utility form:

```text
Q(policy, s) =
  + alpha * grounded_recall(policy, s)
  + beta  * validator_success(policy, s)
  + gamma * write_boundary_precision(policy, s)
  + delta * claim_honesty(policy, s)
  - lambda * token_cost(policy, s)
  - mu     * wall_time(policy, s)
  - nu     * unsafe_or_unsupported_risk(policy, s)
```

Paired lift over matched public rows:

```text
lift_Q =
  average over s in matched_public_rows:
    Q(odylith_on, s) - Q(baseline, s)
```

The weights are an interpretation lens for a benchmark family. They are not a
hidden product score unless a report explicitly publishes the chosen weights.

## Generalization Claim

The generalization claim is conditional and product-wide:

```text
For any observed turn x:
  if product_payload(x, r, h, m) is equivalent to P_s
  and repo_state_class(r) is equivalent to repo_state_class(r_s)
  and host_capability_profile(h) is equivalent to h_s
  and mode(m) is m_s
  and declared_evidence_contract(x) is equivalent to the scenario contract
  then the same product Turn Gate path is the relevant operating-policy path.
```

This is the scope of the product-policy win: comparable ordinary product turns
and benchmark rows use the same Turn Gate path when their observable payload,
repo state class, host capability, mode, and evidence contract are equivalent.

The claim does not say:

- Odylith solves all tasks in the scenario family.
- Every user request should early-exit.
- The host model is irrelevant once an edit is required.
- A benchmark row proves quality outside the exposed evidence contract.
- A single scalar utility captures all research value.

## Public Report Validity

A public benchmark row must expose enough information for another reviewer to
reconstruct why the row closed.

| Required field or group | Why it is required |
| --- | --- |
| `scenario_id` | Identifies the matched row. |
| `lane` | Separates `odylith_on` from baseline behavior. |
| `host_profile` or `host_family` | Documents host capability constraints. |
| `mode` | Documents the Turn Gate mode. |
| `turn_gate_decision` | Shows the product decision. |
| `turn_gate_receipt` | Shows whether the product Turn Gate issued the receipt. |
| `turn_gate_product_path_present` | Shows that the product code path, not a benchmark shim, was used. |
| `execution_capsule` | Shows admitted and denied actions. |
| `tool_gate_summary` | Shows tool admission or explicit non-applicability. |
| `stop_gate_summary` | Shows completion gate posture. |
| `status_basis` | Shows the source of the row status. |
| `validator_execution_mode` | Shows how validation was performed or why it was not applicable. |
| `validator_status_basis` | Preserves compatibility with older validation reports. |
| `preflight_evidence_mode` | Shows how focused evidence entered the product payload. |
| `preflight_evidence_result_status` | Shows whether the focused local evidence passed or was not applicable. |
| `required_paths` and `observed_paths` | Supports grounded recall claims. |
| `candidate_write_paths` | Shows intended or admitted writes. |
| `workspace_delta_paths` | Shows actual workspace mutation. |
| `fairness_findings` | Shows whether paired comparison is valid. |
| `token_count` and `wall_time_ms` | Supports cost and latency interpretation. |

If evidence changes the outcome but is not reported, the row is not valid
public evidence:

```text
if outcome_depends_on(evidence_item)
and evidence_item is not in the public report:
  fairness_state = failed
```

## Migration Interpretation

Historical fields such as `preflight_evidence_mode`,
`preflight_evidence_commands`, and `validator_status_basis` remain compatibility
fields for older reports and for the focused evidence window that populates the
product prompt payload. New public interpretation is anchored on the product
Turn Gate fields.

A row that closes through non-mutating evidence is interpreted as product
early-exit proof only when all of these are true:

```text
turn_gate_receipt.source == product_turn_gate
turn_gate_product_path_present == true
status_basis == turn_gate_early_exit_proof
validator_execution_mode == turn_gate_early_exit_proof
candidate_write_paths is empty
workspace_delta_paths is empty
```

Older reports that lack those fields may be used for historical comparison, but
they cannot support the stronger v0.1.14+ public early-exit claim.

## Invalid Row Conditions

A row is invalid for public benchmark claims when any of these occur:

- The `turn_gate_receipt` is missing.
- An early-exit row has a receipt source other than `product_turn_gate`.
- `turn_gate_product_path_present` is false or missing for a v0.1.14+ row.
- The row claims `early_exit_proof` but a host model call was required.
- The row claims non-mutating closure but `workspace_delta_paths` is non-empty.
- The row omits outcome-changing evidence.
- The row compares lanes with different validators, timeouts, cache posture, or
  write permissions without surfacing that difference in `fairness_findings`.
- The prompt requires an unsafe side effect and the row closes without the
  required user decision.

## Operational Reading

A positive Odylith-on result means the product operating policy improved the
row under the exposed evidence contract. It may be because the Turn Gate avoided
unnecessary host work, narrowed unsafe writes, forced better validation, or
kept claims honest.

A negative or invalid row is still useful when it names the broken contract:
missing evidence, bad validator coverage, stale product-path proof, unfair lane
matching, slow execution, or a host adapter gap. It should not be hidden behind
aggregate utility.

## Research Caveats

The model is intentionally conservative:

- It favors public evidence over private harness knowledge.
- It treats latency and token cost as first-class quality dimensions.
- It separates source-truth tokens from user-facing labels.
- It keeps host behavior and product policy distinct.
- It requires matched-lane fairness before paired lift is meaningful.

That conservatism is deliberate. Odylith benchmark reports are meant to be
reviewable governance evidence, not decorative scorecards.
