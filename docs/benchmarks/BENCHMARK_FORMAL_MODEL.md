# Benchmark Formal Model

This note defines the research interpretation contract for Odylith benchmark
results after the v0.1.14 Governed Harness turn-gate migration. The benchmark
does not own a private success path. It observes a product-owned Odylith
operating policy around a fixed host and records the resulting evidence,
actions, validation, receipts, latency, and token cost.

The measured win is an operating-policy win: better grounded decisions, tighter
write admission, stronger validation honesty, safer completion claims, and less
unnecessary model or tool work under the same task contract.

## Product Turn Gate

Let the product Turn Gate be:

$$
G_O(x, r, h, m) \rightarrow (d, e, c, \rho)
$$

where:

- \(x\) is the user turn.
- \(r\) is the repository state.
- \(h\) is the host capability profile.
- \(m \in \{\mathrm{observe},\mathrm{advise},\mathrm{enforce}\}\) is the gate mode.
- \(d\) is the Turn Gate decision.
- \(e\) is the evidence report.
- \(c\) is the execution capsule.
- \(\rho\) is the harness receipt.

The Odylith-on policy is the host running under that product decision:

$$
\pi_{\mathrm{odylith}} = H \circ G_O
$$

The benchmark is only an observation function:

$$
Y_s = M_B(\rho_s, \tau_s, v_s, a_s)
$$

where \(Y_s\) is the measured row outcome, \(\rho_s\) is the product receipt,
\(\tau_s\) is timing, \(v_s\) is validator evidence, and \(a_s\) is action and
write evidence. The measurement wrapper may sandbox, time, log, and score. It
must not independently decide closure.

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

The product Turn Gate emits one of:

$$
d_s \in
\{
\mathrm{answer\_only},
\mathrm{early\_exit\_proof},
\mathrm{diagnostic},
\mathrm{bounded\_edit},
\mathrm{open\_ended\_implementation},
\mathrm{unsafe\_needs\_user\_decision}
\}
$$

An early-exit proof is valid only under the product receipt:

$$
d_s = \mathrm{early\_exit\_proof}
\Rightarrow
\Phi(e_s, r_s, v_s) = 1
\land
W_s = \varnothing
\land
\rho_s.\mathrm{source} = G_O
$$

This is the core anti-gaming constraint. The row may close without a model call
or file write only when product evidence proves sufficiency, the write set is
empty, and the receipt source is the product Turn Gate.

## Operating-Policy Utility

Quality is a vector, not a single leaderboard number:

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
\forall x \in \mathcal{X}_{\mathrm{observable}},
\quad
\mathrm{Obs}(x,r) \equiv \mathrm{Obs}(s,r_s)
\Rightarrow
G_O(x,r,h,m) \sim G_O(s,r_s,h,m)
$$

This says ordinary product turns and benchmark rows use the same Turn Gate when
their observable evidence, repo state, host capability, and mode are
equivalent. It is a general-purpose policy claim over observable task classes,
not a benchmark-only shortcut and not a universal claim that Odylith improves
every repair-required coding task.

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
and fairness findings.

## Migration Interpretation

Historical fields such as `preflight_evidence_mode`,
`preflight_evidence_commands`, and `validator_status_basis` remain compatibility
fields for older reports. New public interpretation is anchored on the product
Turn Gate fields. A benchmark row that closes through non-mutating evidence is
therefore interpreted as product early-exit proof only when:

$$
\rho_s.\mathrm{source} = \mathrm{product\_turn\_gate}
$$

and:

$$
R_s.\mathrm{turn\_gate\_product\_path\_present} = 1
$$
