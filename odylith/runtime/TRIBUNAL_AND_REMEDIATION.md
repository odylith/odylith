# Tribunal and Remediation

Tribunal is Odylith's judgment layer for the moments where raw coding agents
most often get expensive: the repo is no longer a cold start, there is enough
evidence to act, but the situation is still ambiguous enough that a confident
move can be wrong.

That is the product claim. Odylith is not better because Tribunal sounds more
elaborate than a normal agent response. It is better when Tribunal changes the
failure mode from "the model guessed and continued" into "the system opened a
case, separated the leading explanation from the strongest rival, named the
risk if wrong, and produced the next discriminating check before action."

Tribunal is one of Odylith's core differentiators because it turns engineering
judgment into an inspectable artifact. It does not replace model quality, the
Context Engine, the Execution Engine, or validation. It sits between them:
grounded repo truth flows in, adversarial diagnosis happens over the same
evidence, and a bounded remediation packet flows out.

## The Failure Mode Tribunal Attacks

Ordinary coding agents do not usually fail because they cannot produce text.
They fail because they keep moving after the situation stops being simple:

- a workstream looks done, but proof has not caught up
- a component changed, but ownership or blast radius is unclear
- a fix passed one local check, but the live blocker may have the same
  fingerprint
- a generated surface says one thing while source truth says another
- a policy boundary blocks the obvious next command
- a prior failure has a lesson, but the current session does not remember it
- a broad task has several plausible causes and the agent picks the convenient
  one

Tribunal exists for that edge. It slows the agent down only when the scope is
live actionable and not a clear path. The goal is not ceremony. The goal is to
make uncertainty explicit before the agent commits to a diagnosis, closeout, or
remediation path.

## How It Fits The Odylith Stack

The surrounding Odylith systems answer different questions:

- Context Engine: what repo facts are true and relevant?
- Delivery Intelligence: which scopes are live, risky, stale, blocked, or
  execution-outrunning-governance?
- Execution Engine: what is the next admissible move under the current
  contract?
- Tribunal: what is the best explanation for this ambiguous posture, what rival
  could still be true, and what check would distinguish them?
- Remediator: what bounded correction packet can be handed to an operator or
  execution lane with validation, rollback, and stale guards?

Tribunal is therefore not the first-turn grounding path and not a chat
narration feature. It normally runs inside higher-level flows such as
`odylith sync`, governed surface refresh, delivery-intelligence refresh,
evaluation, and benchmark proof. Cached Tribunal summaries may feed surfaces
and intervention logic, but a fresh provider-backed Tribunal run is a deliberate
diagnosis event, not a hot-path flourish.

## The End-To-End Flow

1. Delivery intelligence refreshes deterministic posture from repo-local truth,
   runtime ledgers, Compass history, Registry specs, Radar workstreams, Atlas
   diagrams, Casebook bugs, and generated surface state.
2. Tribunal selects only supported live-actionable scopes: workstreams,
   components, and diagrams that are not already clear path.
3. It ranks candidates by scope type, scenario priority, severity, decision
   debt, governance lag, blast radius severity, and stable identity
   tie-breakers.
4. It builds a bounded dossier for each focused case. The dossier names the
   subject, decision at stake, observations, evidence quality, proof refs,
   explanation facts, and compact evidence items.
5. Ten actors review the same dossier. They do not get separate stories or
   hidden context. They contest one evidence set from different engineering
   angles.
6. The adjudicator synthesizes the actor memos into one case form: leading
   explanation, strongest rival, risk if wrong, discriminating next check,
   confidence, actor influence, queue row, and maintainer brief.
7. Optional provider enrichment can refine only a narrow field set, and only
   when the text cites grounded evidence. If the provider fails, times out, or
   returns unsupported claims, the case degrades explicitly back to
   deterministic reasoning.
8. Remediator turns the adjudicated prescription into one correction packet
   with action boundary, validation expectations, rollback notes, stale guards,
   and approval state.
9. The case queue, systemic brief, correction packets, and validation posture
   feed `odylith/index.html`, Compass, Registry, benchmark proof, and
   downstream intervention surfaces.

## The Actor Roster

Tribunal uses a fixed actor roster so diagnosis is repeatable and cacheable:

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

The roster is versioned. If the actor policy changes, cached reasoning can be
invalidated instead of silently reusing old judgments under a new policy.

## What Makes It Different From Asking A Bigger Model?

A bigger model can often write a better guess. Tribunal is designed to make the
guess harder to hide.

The important product differences are:

- same evidence for every actor, rather than a free-form narrative drift
- explicit rival explanation, rather than one polished answer
- discriminating next check, rather than vague "investigate further" language
- confidence tied to evidence and actor agreement
- provider output treated as advisory and evidence-gated
- cache reuse tied to evidence fingerprints, so stale reasoning expires
- remediation packaged with validation and rollback instead of implied action
- queue and systemic brief outputs that survive the current chat session

That is where the Odylith advantage can show up against an unguided agent. The
same model, looking at the same repo, gets a better operating frame: grounded
facts, structured disagreement, falsifiable diagnosis, and bounded recovery.

## What Remediator Adds

Tribunal diagnoses. Remediator packages the next move.

That separation matters. Without it, diagnosis tends to collapse directly into
action, and the agent can skip over the boring parts that make a fix safe.
Remediator turns a Tribunal prescription into a correction packet with:

- the exact action boundary
- required validation
- rollback notes
- stale guards
- approval and delegation state
- evidence links back to the case

The caller still owns whether and how corrective action is applied. Tribunal
and Remediator make the next move explicit and auditable; they do not bypass
operator approval or target-repo validation.

## Where Tribunal Wins

Tribunal is most valuable when the cost of being confidently wrong is higher
than the cost of a structured diagnosis pass:

- closeout decisions where "done" requires proof, not vibes
- live blocker recovery where the old failure fingerprint may still be present
- cross-surface drift between source truth and generated shell views
- ownership disputes across components, diagrams, and workstreams
- policy-boundary conflicts where an obvious command is not admissible
- benchmark or evaluation failures that need an explanation, not just another
  retry
- repeated failure patterns that should become Casebook memory, doctrine, or
  validation pressure

In those cases, Tribunal gives Odylith a way to improve outcomes without
claiming magical model superiority. It improves the operating policy around the
model.

## Where Tribunal Is Not The Answer

Tribunal is not supposed to run for everything.

It is the wrong tool for:

- first-turn repo grounding
- simple clear-path edits
- ordinary narration in the chat loop
- hot-path visibility checks
- replacing target-repo tests
- accepting provider claims without evidence
- executing corrective action by itself

If Tribunal ran constantly, it would become ceremony. Its value comes from
selective use at ambiguity boundaries where structured judgment changes the
next move.

## Output Contract

A Tribunal payload can include:

- selected cases and full dossiers
- actor memos and adjudication records
- leading explanation and strongest rival
- risk if wrong and discriminating next check
- confidence and actor influence metadata
- provider status and validation errors
- case queue rows
- systemic brief
- cache stats
- correction packets

The shell may show compressed queue rows or systemic brief text, but those are
derived views. The full case remains the debugging surface for why a diagnosis
changed.

## Operator Contract

Operators usually encounter Tribunal through the normal Odylith surface and
refresh commands:

```bash
odylith sync --repo-root . --force
odylith context-engine --repo-root . status
odylith compass log --repo-root . --kind decision --summary "<decision>"
odylith compass update --repo-root . --statement "<current state>"
```

Consumer repositories keep local plans, bugs, specs, runbooks, and registry
truth in place. Odylith reads those inputs; it does not become their source of
truth.
