# Benchmark Interpretation Contract

This note defines how to read Odylith benchmark results after the Governed
Harness turn-gate migration. It is a benchmark validity specification: a
reviewer-facing contract for when public results support the product claim. It
is not a mathematical proof of product quality.

A benchmark row is valid only when the public report shows the product Turn
Gate decision, receipt, evidence, validation basis, actions, write set, latency,
and token cost. The harness may sandbox, time, log, and score those fields. It
must use the product Turn Gate result and visible validator evidence as the
success basis.

The measured win is an Odylith operating-policy win: better grounded decisions,
tighter write admission, stronger validation honesty, safer completion claims,
and less unnecessary model or tool work under the same task contract.

Notation is used only where it shortens a report-field rule.

## Scope

The contract is intentionally host model agnostic. It applies to any host
adapter that can receive an Odylith product payload and execute the resulting
turn contract. Host-specific transport details may change; the product Turn
Gate, evidence contract, and public report fields are the invariant surfaces.

This document is not a claim that one host model is better than another. It is
also not a claim that every task can close without tool work. It describes when
a benchmark row is valid public evidence for the Odylith operating policy.

The intended comparison is full Odylith product assistance versus a raw host CLI
baseline under a matched task contract. That is the product being measured: the
policy, evidence, validation, and completion layer around the host model.

## Public Report Readability

Charts and scorecards are secondary. A reviewer should first be able to inspect
the benchmark row in ordinary Markdown and see why the row closed.

The row should show the durable decision token, Turn Gate receipt, execution
capsule, validator basis, write-path evidence, and fairness finding. Friendly
labels are fine, but source-truth tokens need to stay visible beside them. The
important fields are `turn_gate_decision`, `turn_gate_receipt`,
`turn_gate_product_path_present`, `execution_capsule`, `tool_gate_summary`,
`stop_gate_summary`, `validation_results.status_basis`,
`validator_execution_mode`, `validator_status_basis`,
`preflight_evidence_mode`, `preflight_evidence_result_status`,
`candidate_write_paths`, `failure_artifacts.workspace_state_post_codex` when
present, and `fairness_findings`.

## Core Entities

These symbols are reviewer shorthand for concrete report surfaces. They are not
new runtime objects.

| Name | Report surface | Meaning |
| --- | --- | --- |
| `s` | `scenario_id` | One benchmark scenario row. |
| `x_s` | prompt or scenario input | The user turn being evaluated. |
| `r_s` | repo fixture and observed paths | The disposable repository state. |
| `h_s` | `host_profile` or `host_family` | The host capability profile for the row. |
| `m_s` | `mode` | The gate mode, such as `observe`, `advise`, or `enforce`. |
| `P_s` | product payload fields | The Turn Gate payload built from the prompt, policy hints, and focused evidence. |
| `T_s` | scenario contract fields | Required paths, writable paths, cache posture, timeout policy, host policy, expected report fields, and validator obligations. |
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
| `R_s` | rendered public row | The report-visible fields for `s`. |

## Product Turn Gate Contract

The product Turn Gate has this interface shape:

```math
G_O(P_s, r_s, h_s, m_s) \to (d_s, E_s, C_s, \rho_s)
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

```math
\pi_O(P_s, r_s, h_s, m_s)
= H(G_O(P_s, r_s, h_s, m_s), P_s, r_s, h_s)
```

The benchmark wrapper records the row:

```math
Y_s = M_B(d_s, E_s, C_s, \rho_s, \tau_s, V_s, A_s, W_s)
```

The wrapper may sandbox, time, log, and score. It may run focused local checks
before the Turn Gate call to populate `P_s`. It must not mark a row successful
unless the Turn Gate decision, receipt, validation fields, and write-set
evidence support that status.

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

An early-exit proof is valid only when the product Turn Gate emits
`early_exit_proof` and the public evidence shows that no host model call or
workspace mutation was required.

Compact form:

```math
\mathrm{valid}_{\mathrm{early}}(s)
\iff
d_s = d_{\mathrm{early}}
\land \Phi_G(P_s, E_s, r_s) = 1
\land W_s^{\mathrm{obs}} = \varnothing
\land S_\rho(\rho_s) = \sigma_G
```

Here `d_early` denotes the `early_exit_proof` decision and `sigma_G` denotes the
`product_turn_gate` receipt source. The predicate maps to report fields:

```math
\Phi_G(P_s, E_s, r_s) = A_s \land B_s \land K_s \land \neg U_s
```

with:

```math
A_s, B_s, K_s, U_s \in \{0,1\}
```

where `A_s` is product-policy admission for validator-backed non-mutating
closure, `B_s` is focused evidence pass or non-applicability, `K_s` is coverage
of the declared validation contract, and `U_s` is unsafe-side-effect pressure.

The report-field equivalent is:

```text
early_exit_is_valid(s) =
  turn_gate_decision.decision_type == early_exit_proof
  and turn_gate_receipt.source == product_turn_gate
  and turn_gate_product_path_present == true
  and validation_results.status_basis == turn_gate_early_exit_proof
  and validator_execution_mode == turn_gate_early_exit_proof
  and preflight_evidence_result_status in {passed, not_applicable}
  and focused_checks_cover_declared_contract == true
  and candidate_write_paths is empty after workspace-delta folding
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

For live benchmark rows:

```math
W_s^{\mathrm{obs}} = CWP_s
```

where `CWP_s` is the reported `candidate_write_paths` set after the harness has
combined structured candidate writes with detected workspace-state deltas.
Failure rows may also expose detailed workspace state under
`failure_artifacts.workspace_state_post_codex`.

## Scenario Model

A benchmark scenario is:

```math
S_s = (x_s, r_s, h_s, m_s, T_s, V_s, \Phi_s)
```

`T_s` is the declared scenario contract: required paths, writable paths, cache
posture, timeout policy, host policy, expected report fields, and validator
obligations.
Validators are observable approximations of the scenario truth predicate. A row
is public evidence only when the report exposes the validator basis and the
matched-lane fairness contract holds.

## Matched-Lane Fairness

Comparisons must use matched lanes. For each scenario `s`, the Odylith-on lane
and the baseline lane must share the same task contract:

```math
F_s = 1
\iff
\mathrm{fair\_row}(s)
```

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

## Metric Interpretation

Quality is multi-metric, not a single leaderboard number. The public report does
not need to emit one scalar `Q` field for the interpretation to be valid.

| Component | Meaning | Direction |
| --- | --- | --- |
| `grounded_recall` | Required-path and evidence recall. | Higher is better. |
| `validator_success` | Validator-backed success. | Higher is better. |
| `write_boundary_precision` | Avoidance of unnecessary or out-of-scope writes. | Higher is better. |
| `claim_honesty` | Accuracy of completion and limitation claims. | Higher is better. |
| `token_cost` | Model and prompt token cost. | Lower is better. |
| `wall_time` | End-to-end row latency. | Lower is better. |
| `unsafe_or_unsupported_risk` | Unsafe action or unsupported completion risk. | Lower is better. |

Reports may publish per-metric deltas over matched public rows. Each metric
should stay in its native unit unless the report explicitly defines a
normalization. Cost and risk terms should not be merged with quality terms
unless the report publishes the transformation, weights, and rationale.

Without those published choices, Odylith's benchmark interpretation remains the
multi-metric table above.

## Generalization Boundary

The benchmark does not claim universal product generalization. A row speaks
only to ordinary product turns with the same visible contract class.

The supported external-validity reading is:

- benchmark rows and ordinary product turns are comparable only when their
  observable payload, repo-state class, host capability, mode, and evidence
  contract match;
- the shared claim is that comparable turns use the same product Turn Gate path;
- the benchmark still cannot prove quality outside the exposed evidence
  contract.

The claim does not say:

- Odylith solves all tasks in the scenario family.
- Every user request should early-exit.
- The host model is irrelevant once an edit is required.
- A benchmark row proves quality outside the exposed evidence contract.
- One combined score captures all research value.

## Evidence Boundary

Odylith's public benchmark is an operating-policy benchmark. That is the core
product claim. The benchmark measures what the product is designed to provide
around a host model: scoped evidence, decision discipline, write admission,
validator-backed closure, and auditable completion claims.

The strongest supported public phrasing is:

```text
Under matched task contracts, Odylith's operating policy improves grounded task
closure versus the raw host CLI baseline on the published corpus.
```

The benchmark should not be described as a standalone model-intelligence contest
or as proof that the host model is irrelevant. A broader research-grade claim
would require additional evidence such as a locked held-out corpus, independent
validators, blinded review, raw logs, exact host and model versions, and
uncertainty intervals. Those additions would strengthen external validity; they
are not prerequisites for the narrower product benchmark claim above.

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
| `validation_results.status_basis` | Shows the source of the validation-backed row status. |
| `validator_execution_mode` | Shows how validation was performed or why it was not applicable. |
| `validator_status_basis` | Preserves compatibility with older validation reports. |
| `preflight_evidence_mode` | Shows how focused evidence entered the product payload. |
| `preflight_evidence_result_status` | Shows whether the focused local evidence passed or was not applicable. |
| `required_paths` and `observed_paths` | Supports grounded recall claims. |
| `candidate_write_paths` | Shows intended writes plus detected workspace-state deltas after folding. |
| `failure_artifacts.workspace_state_post_codex` | Shows detailed workspace mutation evidence when a row fails or needs diagnosis. |
| `fairness_findings` | Shows whether paired comparison is valid. |
| Published token fields | Supports cost interpretation, including `prompt_token_delta` and `total_payload_token_delta`. |
| Published latency fields | Supports latency interpretation, including `latency_delta_ms` and pair wall-clock fields. |

If evidence changes the outcome but is not reported, the row is not valid public
evidence. If outcome-changing evidence stayed private, the fairness finding
must fail or the row must be withheld from paired benchmark claims.

## Migration Interpretation

Historical fields such as `preflight_evidence_mode`,
`preflight_evidence_commands`, and `validator_status_basis` remain compatibility
fields for older reports and for the focused evidence window that populates the
product prompt payload. New public interpretation is anchored on the product
Turn Gate fields.

A row that closes through non-mutating evidence is interpreted as product
early-exit proof only when all of these are true:

```math
S_\rho(\rho_s) = \sigma_G
```

```math
P_{\mathrm{path}}(R_s) = 1
```

```math
B_{\mathrm{status}}(V_s) = \eta_G
```

```math
M_{\mathrm{exec}}(A_s) = \eta_G
```

where `eta_G` denotes the live row token `turn_gate_early_exit_proof`. The
report-field equivalent is:

```text
turn_gate_receipt.source == product_turn_gate
turn_gate_product_path_present == true
validation_results.status_basis == turn_gate_early_exit_proof
validator_execution_mode == turn_gate_early_exit_proof
candidate_write_paths is empty after workspace-delta folding
```

Older reports that lack those fields may be used for historical comparison, but
they cannot support the stronger v0.1.14+ public early-exit claim.

## Invalid Row Conditions

A row is invalid for public benchmark claims when any of these occur:

- The `turn_gate_receipt` is missing.
- An early-exit row has a receipt source other than `product_turn_gate`.
- `turn_gate_product_path_present` is false or missing for a v0.1.14+ row.
- The row claims `early_exit_proof` but a host model call was required.
- The row claims non-mutating closure but folded `candidate_write_paths` is
  non-empty.
- Detailed failure artifacts contradict the claimed non-mutating closure.
- The row omits outcome-changing evidence.
- The row compares lanes with different validators, timeouts, cache posture, or
  write permissions without surfacing that difference in `fairness_findings`.
- The prompt requires an unsafe side effect and the row closes without the
  required user decision.

## Operational Reading

A positive Odylith-on result means the product operating policy improved the
row under the exposed evidence contract. It may be because the Turn Gate avoided
unnecessary host work, narrowed unsafe writes, required better validation, or
kept claims honest.

An early-exit win should be read as a product efficiency and governance win: the
system recognized that validator-backed non-mutating evidence was already enough
to close the row. It should not be presented as harder model reasoning.

A negative or invalid row is still useful when it names the broken contract:
missing evidence, bad validator coverage, stale product-path proof, unfair lane
matching, slow execution, or a host adapter gap. It should not be hidden behind
aggregate utility.

## Research Posture

The contract is intentionally audit-friendly:

- It favors public evidence over private harness knowledge.
- It treats latency and token cost as first-class quality dimensions.
- It separates source-truth tokens from user-facing labels.
- It keeps host behavior and product policy distinct.
- It requires matched-lane fairness before paired lift is meaningful.
- It does not treat notation as proof.
- It does not publish a single combined score unless the normalization and
  weights are explicit.
- It does not generalize beyond the visible scenario contract.

That posture is deliberate. Odylith benchmark reports are meant to be
reviewable product evidence, not just scorecards.
