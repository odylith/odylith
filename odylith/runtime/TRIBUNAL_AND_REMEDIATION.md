# Tribunal and Remediation

Tribunal is Odylith's structured diagnosis engine. It runs after Odylith has
grounded the repo and delivery intelligence has shaped the current posture, but
before the agent treats a blocked or ambiguous scope as safe to continue. Its
job is not to execute a fix. Its job is to turn an uncertain posture into an
evidence-backed case: the leading explanation, the strongest rival explanation,
the risk if that read is wrong, and the next check that would discriminate
between the two.

Tribunal is deliberately not the first-turn grounding path. The Context Engine
answers what repo facts are true and relevant. The Execution Engine answers
what move is admissible next. Tribunal answers why a live scope is blocked,
contested, stale, unsafe to close, or otherwise not a clear path.

## When Tribunal Runs

Tribunal is usually invoked from higher-level Odylith flows rather than a
standalone operator command:

- `odylith sync` after deterministic posture and delivery intelligence refresh
- governed surface refresh when the shell needs diagnosis-backed queue state
- evaluation and benchmark paths that need to prove diagnosis quality
- delivery-intelligence flows that need a case queue or systemic brief

It should not run just to narrate a chat turn, refresh a hot-path visibility
status, or replace deterministic grounding. Cached Tribunal summaries may feed
downstream surfaces, but a fresh provider-backed Tribunal pass is a deliberate
runtime event.

## Candidate Selection

Tribunal starts from delivery-intelligence scopes and keeps only scopes that
are live actionable, belong to a supported type, and are not already clear path.
The supported scope types are:

- workstream
- component
- diagram

Eligible scopes are ranked by a stable priority band:

- scope type
- scenario priority
- severity
- decision debt
- governance lag
- blast radius severity
- stable scope identity

The focused queue is built in two passes. First, Tribunal covers distinct
scenario classes so one noisy failure mode does not hide every other kind of
risk. Then it fills the remaining focus slots by priority. The selection
summary records what was shown, what overflowed, and why.

## Dossier Construction

For each focused scope, Tribunal builds a bounded case dossier. The dossier is
the evidence substrate for the whole run. It includes:

- case id and subject metadata
- the decision at stake
- observations derived from scope posture
- baseline scenario and severity
- evidence quality
- normalized explanation facts
- proof references and compact evidence items

The same dossier goes to every actor and to any optional provider enrichment.
That shared evidence set is the guardrail: disagreement is allowed, but each
claim has to remain attached to named repo facts.

## Actor Review

Tribunal runs a fixed actor roster over the same dossier:

- `observer`: summarizes grounded facts and visible state
- `ownership_resolver`: tests ownership and authority claims
- `causal_analyst`: explains why the posture likely emerged
- `policy_judge`: checks policy-boundary conflicts
- `normative_judge`: evaluates what the system should prefer
- `adversary`: stress-tests the leading narrative
- `counterfactual_analyst`: searches for alternate explanations
- `gap_analyst`: identifies missing proof or weak evidence
- `risk_analyst`: evaluates downside if the diagnosis is wrong
- `prescriber`: narrows the result into a bounded next-action claim

The actor roster is versioned. If the actor policy changes, cached reasoning
can be invalidated instead of silently reusing old judgments under a new policy.

## Adjudication

Adjudication turns the actor memos into one explicit case form. A Tribunal case
records:

- leading explanation
- strongest rival
- risk if wrong
- discriminating next check
- confidence
- actor influence metadata
- maintainer brief
- queue row
- correction-packet seed

The point is not to make the system sound more certain. The point is to make
uncertainty inspectable. A good Tribunal case says what Odylith currently
believes, what could still falsify that belief, and what bounded check or fix
should happen next.

## Provider Enrichment

Deterministic local reasoning is the baseline. External provider output is
optional, advisory, and narrowly gated.

Provider enrichment may refine only these fields:

- `leading_explanation`
- `strongest_rival`
- `risk_if_wrong`
- `discriminating_next_check`
- `maintainer_brief`

Provider text is accepted only when it cites grounded evidence items. If the
provider times out, loses transport, or returns unsupported claims, Tribunal
degrades explicitly back to deterministic reasoning. A failed provider pass is
not silently blended into the case.

Final payloads report whether the run was deterministic-only, provider-ready
without validated enrichment, or hybrid with validated enrichment.

## Cache Model

Tribunal can reuse prior cases when the actor policy version, scope key,
evidence fingerprint, and provider-attempt requirements still match. That keeps
routine refreshes fast while still discarding stale reasoning when evidence or
policy changes.

## Remediator Handoff

Tribunal diagnoses. Remediator packages the bounded correction.

After adjudication, Remediator turns the prescription into one correction
packet per case. The packet carries:

- the proposed action boundary
- validation expectations
- rollback notes
- stale guards
- approval and delegation state

The caller still owns whether and how corrective action is applied. Tribunal
and Remediator make the next move explicit and auditable; they do not bypass
operator approval or target-repo validation.

## Outputs And Surfaces

The Tribunal payload includes:

- selected cases and full dossiers
- actor memos and adjudication records
- case queue rows
- systemic brief
- provider status and validation errors
- cache stats
- correction packets

Those outputs feed `odylith/index.html`, Compass, Registry, delivery
intelligence, benchmark proof, and downstream intervention surfaces. The shell
may show compressed queue rows or systemic brief text, but those are derived
views. The full case remains the debugging surface for why a diagnosis changed.

Primary operator commands:

```bash
odylith sync --repo-root . --force
odylith context-engine --repo-root . status
odylith compass log --repo-root . --kind decision --summary "<decision>"
odylith compass update --repo-root . --statement "<current state>"
```

Consumer repositories keep local plans, bugs, specs, runbooks, and registry
truth in place. Odylith reads those inputs; it does not become their source of
truth.
