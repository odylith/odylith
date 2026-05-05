# Benchmark Formal Model

This note defines the research interpretation contract for Odylith benchmark
results after the v0.1.14 Governed Harness turn-gate migration. The benchmark
does not own a private success path. It observes a product-owned Odylith
operating policy around a fixed host and records the resulting evidence,
actions, validation, receipts, latency, and token cost.

The measured win is an operating-policy win: better grounded decisions, tighter
write admission, stronger validation honesty, safer completion claims, and less
unnecessary model or tool work under the same task contract.

## Rendering Contract

This document is meant to render cleanly in GitHub Markdown. Durable report
field names and enum tokens such as `early_exit_proof` and
`product_turn_gate` stay in Markdown code spans, not inside LaTeX identifiers.
The LaTeX formulas use symbolic variables and symbolic constants, then the prose
maps those symbols back to report fields and tokens. That keeps GitHub's math
renderer from interpreting underscores in durable tokens as nested subscripts.

## Product Turn Gate

Let the product Turn Gate be:

$$
G_O(P, r, h, m) \rightarrow (d, e, c, \rho)
$$

where:

- \(P\) is the product prompt payload built from the user turn, bounded
  product policy hints, declared validation obligations, and any pre-model
  evidence the host or benchmark has already produced.
- \(r\) is the repository state.
- \(h\) is the host capability profile.
- \(m \in M\) is the gate mode. The implemented mode tokens are `observe`,
  `advise`, and `enforce`.
- \(d\) is the Turn Gate decision.
- \(e\) is the evidence report.
- \(c\) is the execution capsule.
- \(\rho\) is the harness receipt.

The Odylith-on policy is the host running under that product decision:

$$
\pi_{\mathrm{odylith}}(P,r,h,m) = H(G_O(P,r,h,m), P, r, h)
$$

The benchmark is only an observation function:

$$
Y_s = M_B(d_s, e_s, c_s, \rho_s, \tau_s, v_s, a_s)
$$

where \(Y_s\) is the measured row outcome, \(d_s\) is the product decision,
\(e_s\) is the evidence report, \(c_s\) is the execution capsule, \(\rho_s\)
is the product receipt, \(\tau_s\) is timing, \(v_s\) is validator evidence,
and \(a_s\) is action and write evidence. The measurement wrapper may sandbox,
time, log, and score. It must not independently decide closure.

The current v0.1.14 source-local implementation maps this model to
`odylith.runtime.governed_harness.turn_gate.decide_turn(...)`. The live
benchmark calls that product API for the `odylith_on` lane before any host
model subprocess is invoked. The benchmark may run focused local checks before
the Turn Gate call to populate \(P\); the gate, not the benchmark wrapper,
decides whether that evidence is sufficient.

## Experimental Unit

A benchmark scenario is:

$$
S_s =
\left(
  r_s,\;
  x_s,\;
  C_s,\;
  V_s,\;
  \Phi_s
\right)
$$

where:

- \(r_s\) is the disposable repository state.
- \(x_s\) is the user turn.
- \(C_s\) is the declared contract: required paths, writable paths, cache
  posture, timeout policy, host policy, and report fields.
- \(V_s\) is the validator family, including any focused validator evidence.
- \(\Phi_s(r)\in\{0,1\}\) is the scenario truth predicate.

Validators are observable approximations of \(\Phi_s\). A row is public evidence
only when the report exposes the validator basis and the matched-lane fairness
contract holds.

## Decision Classes

The product Turn Gate emits a decision \(d_s \in D\). The decision vocabulary
\(D\) is represented in reports by these tokens:

- `answer_only`
- `early_exit_proof`
- `diagnostic`
- `bounded_edit`
- `open_ended_implementation`
- `unsafe_needs_user_decision`

Let \(d_{\mathrm{early}}\) denote the `early_exit_proof` decision and
\(\sigma_G\) denote the receipt source token `product_turn_gate`. An
early-exit proof is valid only under the product receipt:

$$
d_s = d_{\mathrm{early}}
\Rightarrow
\Phi_G(P_s, e_s, r_s) = 1
\land
W_s^{\mathrm{obs}} = \varnothing
\land
S_{\rho}(\rho_s) = \sigma_G
$$

Here \(S_{\rho}\) is the receipt-source projection. This is the source-of-truth
constraint. The row may close without a model call or file write only when
product evidence proves sufficiency, the observed write set is empty, and the
receipt source is the product Turn Gate.

The implemented sufficiency predicate is:

$$
\Phi_G(P_s,e_s,r_s) =
A_s \land B_s \land K_s \land \neg U_s
$$

where:

$$
A_s =
\mathbf{1}\{\text{product policy admits validator-backed non-mutating closure}\}
$$

$$
B_s =
\mathbf{1}\{\text{focused check result is passed or not applicable}\}
$$

$$
K_s =
\mathbf{1}\{\text{focused checks cover the declared validation contract}\}
$$

$$
U_s =
\mathbf{1}\{\text{the prompt requests an unsafe side effect}\}
$$

In code, \(A_s\) is driven by the product `non_mutating_closure_allowed` policy
hint. The legacy corpus compatibility alias consumed by
`_non_mutating_closure_allowed(...)` is never sufficient by itself. The gate
still requires \(B_s=1\) and \(K_s=1\), emits a receipt whose `source` is
`product_turn_gate`, and builds an execution capsule whose early-exit route
constraints are `do_not_call_host_model` and `do_not_mutate_workspace`.

For live benchmark rows:

$$
W_s^{\mathrm{obs}} = CWP_s \cup WDP_s
$$

where \(CWP_s\) is the reported `candidate_write_paths` set and \(WDP_s\) is
the reported `workspace_delta_paths` set. The row is accepted only when
expectation, required-path recall, validator status, and write expectation all
pass under the reported product decision.

## Operating-Policy Utility

Quality is a vector, not a single leaderboard number. The following functional
defines the research interpretation over exposed report fields; the public
report does not need to emit one scalar `Q` field for the interpretation to be
valid:

$$
Q(\pi) =
\alpha R_{\mathrm{ground}}
+\beta R_{\mathrm{valid}}
+\gamma R_{\mathrm{bounded}}
+\delta R_{\mathrm{claim}}
-\lambda C_{\mathrm{tokens}}
-\mu C_{\mathrm{time}}
-\nu R_{\mathrm{unsafe}}
$$

where:

- \(R_{\mathrm{ground}}\) measures required-path and evidence recall.
- \(R_{\mathrm{valid}}\) measures validator-backed success.
- \(R_{\mathrm{bounded}}\) measures write-surface precision and unnecessary
  widening avoidance.
- \(R_{\mathrm{claim}}\) measures completion-claim honesty.
- \(C_{\mathrm{tokens}}\) and \(C_{\mathrm{time}}\) measure model/tool cost.
- \(R_{\mathrm{unsafe}}\) measures unsafe action or unsupported completion risk.

The paired lift is:

$$
\Delta Q =
\mathbb{E}_{s \sim \mathcal{S}}[Q(\pi_{\mathrm{odylith}}, s)]
-
\mathbb{E}_{s \sim \mathcal{S}}[Q(\pi_{\mathrm{baseline}}, s)]
$$

For a finite public report:

$$
\widehat{\Delta Q} =
\frac{1}{|\mathcal{P}|}
\sum_{s \in \mathcal{P}}
\left[
  Q(\pi_{\mathrm{odylith}}, s)
  -
  Q(\pi_{\mathrm{baseline}}, s)
\right]
$$

where \(\mathcal{P}\) is the set of matched rows whose fairness contract passes.

## Generalization Claim

The generalization claim is conditional and product-wide:

$$
\forall x \in \mathcal{X}_{\mathrm{obs}},
\quad
P_O(x,r,h,m) \equiv P_s
\land
r \equiv_R r_s
\land
h \equiv_H h_s
\land
m = m_s
\Rightarrow
G_O(P_O(x,r,h,m),r,h,m) \sim G_O(P_s,r_s,h_s,m_s)
$$

Here \(P_O\) is the product payload builder. This says ordinary product turns
and benchmark rows use the same Turn Gate when their product prompt payload,
observable evidence, repository state, host
capability, and mode are equivalent. Here \(h_s\) and \(m_s\) are the scenario
host capability and gate mode carried by \(C_s\). That is the scope of the
product-policy win: the same general-purpose policy path governs comparable
observable task classes. Separate repair-required families measure repair
outcome quality when the correct action is an actual edit.

## Report Validity

For a public row, the report must expose:

$$
R_s \supseteq
\{
d_s,\;
e_s,\;
c_s,\;
\rho_s,\;
V_s,\;
W_s,\;
F_s
\}
$$

where \(F_s\) is the fairness state. If evidence changes the outcome but is not
reported, the row is not valid public evidence:

$$
\exists e_s:
Y_s = f(e_s)
\land
e_s \not\subset R_s
\Rightarrow
F_s = 0
$$

In v0.1.14 reports this requires fields such as `turn_gate_decision`,
`turn_gate_receipt`, `execution_capsule`, `tool_gate_summary`,
`stop_gate_summary`, validator basis, observed paths, candidate write paths,
and fairness findings. `tool_gate_summary` may be `not_applicable` for rows
that take the early-exit path before any host tool call exists; the field still
has to be present so the absence of tool-gating activity is explicit.

## Migration Interpretation

Historical fields such as `preflight_evidence_mode`,
`preflight_evidence_commands`, and `validator_status_basis` remain compatibility
fields for older reports and for the focused evidence window that populates the
product prompt payload. New public interpretation is anchored on the product
Turn Gate fields.

Let \(\eta_G\) denote the live row token `turn_gate_early_exit_proof`.
A benchmark row that closes through non-mutating evidence is interpreted as
product early-exit proof only when:

$$
S_{\rho}(\rho_s) = \sigma_G
$$

and:

$$
P_{\mathrm{path}}(R_s) = 1
$$

The second predicate is represented in reports by the field
`turn_gate_product_path_present`. The corresponding live row status basis is:

$$
B_{\mathrm{status}}(v_s) = \eta_G
$$

where the reported field is `status_basis`. The live execution mode is:

$$
M_{\mathrm{exec}}(a_s) = \eta_G
$$

where the reported field is `validator_execution_mode`.
