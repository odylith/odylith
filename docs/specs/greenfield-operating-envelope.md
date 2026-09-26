# Greenfield Operating Envelope

Version: `odylith.greenfield-operating-envelope.v5`

Profile: `single-product-governance-onboarding`

This is the bounded release claim for Greenfield, not a claim of universal
semantic correctness.

## Supported evidence

- English text supplied as one operator request plus, optionally, one edit.
- The public source formats are `operator_prompt` and
  `operator_prompt_with_edit_evidence`. Pasted Markdown is accepted as text in
  either document. JSON and typed envelopes are internal custody formats, not
  public evidence inputs. PDF, image, audio, and remote-URL ingestion are not
  direct Greenfield formats; a host may extract their text as untrusted evidence
  first.
- 1 byte through 64 KiB of combined evidence, across at most two evidence
  documents.
- One product, one state object, and one first-release path. Each authored list
  may contain at most 32 items, including human actors, external systems,
  internal systems, ambiguities, and explicit safety or operational boundaries.
  An unresolved contradiction is outside the commit envelope and must produce
  the one material clarification or a safe no-write outcome.

The sealed receipt records evidence volume, documents, actors, state objects,
paths, systems, contradictions, ambiguities, and safety boundaries. It labels
the request `bounded`, `moderate`, or `high`; domain names do not determine
complexity.

## Product boundary

Greenfield compiles a repo-local governance package. It does not generate
application code, deploy software, call external systems, or exercise production
authority. Evidence must support one actor-owned first path, a visible result,
and a bounded proof statement without invented safety, clinical, regulatory,
legal, or production claims.

## Host and model profiles

Codex and Claude host names, callbacks, and registration do not qualify a native
decision interface. Propose and compile previews publish nothing; they print only
three full shell-quoted terminal commands for their repository path and retained
transaction hash. In shorthand: `decide ... CONFIRM <hash>`, `decide ... EDIT <hash> --edit
<corrections>` (or `--edit-evidence <file>`), and `decide ... REJECT <hash>`.
Ordinary chat approval is not a terminal decision. Explicit terminal `CONFIRM`
and `REJECT` share a bounded deterministic owner and invoke neither compiler nor
model. `EDIT` verifies the retained hash, lazily uses the existing compiler with
the sealed original source and new untrusted correction, preserves tier and the
timing contract, retains the old seal, and returns a new hash and
preview. It adds no schema, stage, retry, or repair mechanism. The sealed-byte
`create` CLI remains a separate commit-only interface. Native automatic delivery
and visible completion require their own proof.

Model-profile contract v23 declares three pinned real-model profiles, but only
one is qualified to support a successful release claim:

- `greenfield-standard-participant-first-astra-medium-v19`: the default and
  `auto` path, the sole release-success profile, with a 90-second advisory
  performance target.
- `greenfield-rescue-participant-first-luna-medium-v19`: an explicit
  lower-capability clarification/no-write control with a 120-second advisory
  target. It is declared but is not success-qualified.
- `greenfield-deep-participant-first-sol-high-v18`: an unsupported negative and
  diagnostic profile with a 150-second advisory target. It is declared but is
  not success-qualified.

All three profiles use one 180-second operational timeout and one 165-second
shared model window, leaving 15 seconds for deterministic completion. Meeting or
missing the selected 90/120/150-second target is recorded as performance evidence,
not used as an admission gate. Proposal elapsed time must remain strictly below
the operational timeout. Sixty seconds remains an advisory normal-case target.
The separate commit-only step must still finish strictly below 60 seconds.
Profile contract v23 separates declared profiles, the release-success profile,
and the lower-capability control instead of treating evidence profiles as
interchangeable success routes. The advisory targets, finite timeout, semantic
requirements, and transaction laws are unchanged.
Historical observations keep their original limits and verdicts; old sealed
v12/v13/v14/v15/v16/v17 transactions and v22 model-profile receipts are not
relabeled as current. Retired standard v18 authoring receipts are not relabeled
as v19, and retired rescue Terra v18 receipts are not relabeled as Luna v19.
Fresh profile evidence is required for any qualification.

The selected profile is fixed before the model request. Elapsed time or a failed
attempt never relabels or extends a standard request into rescue or deep. The
normal `auto` and `standard` routes expose only Astra medium. Legacy explicit
`rescue` or `deep` success selection fails closed before provider execution; it
does not alias either tier to Astra. Luna remains available only for the bounded
lower-capability clarification/no-write control, while Sol remains available
only for negative diagnostic comparison. No fallback, retry, repair call, model
ladder, or tier promotion follows.
These are bounded candidate profiles, not claims about every provider model.
Host-model output is candidate evidence only. Every profile must clarify or fail
safely instead of inventing product truth. Provider unavailability is separately
proven as a fast, no-write environment outcome and is not a supported-success
profile.

Historical three-call comparisons produced complete governance packages in
76.165 and 77.288 seconds with independent acceptance and 32 passing
desktop/mobile browser states. Those receipts preserve learning only; the
three-call selector/author/join mechanism is retired and cannot qualify the
current host-owned path. They do not estimate current reliability or qualify
installed behavior, controls, unseen inputs, or release readiness. Earlier
failed attempts retain their own verdicts.

Luna retains the explicit lower-capability control obligation: source-bound
material clarification or a safe no-write outcome, separately from unavailable-
provider behavior. That control cannot contribute a committed success case.
Astra release proof requires observed committed positive cases and source-bound
material clarifications with no writes. Sol diagnostic evidence cannot qualify a
release-success profile.

Authoring v68 returns either a reviewed source-and-design candidate or the
existing material clarification result. Source facts, actions and relationships
remain citation-bound. A required, separately labeled `provisional_design`
proposes 4–5 logical components, 4–5 workstreams, internal exchanges and
verification. Design support references source-event identities without changing
who performs those actions. Source facts never come from the design section.
Five deterministic Atlas views distinguish source context and first path from
proposed exchanges, delivery dependencies and capability support. Diagram count
is not evidence of useful detail; human review and browser proof remain required.

The existing authored relation hash binds this design with source semantics;
no second candidate store, source ledger or post-confirm interpretation is added.
The old source-review/correction path remains removed. The new reviewer receives
accepted-source and proposed-decision namespaces without changing any value.
It also receives the canonical resolver's selected byte locations and bounded
surrounding text. This is a read-only view, not a second citation resolver or an
automatic occurrence repair. Review v2 binds the unchanged source and candidate;
the release checker reconstructs the same view through canonical validation.
It may admit or deny with one substantiated witness, never rewrite the candidate.
Practical proposed choices remain advisory unless materially incompatible or unsafe.
Private proof retains the one direct host-candidate request, exact resolved model
and reasoning-effort argv, response hash, source hash, call count, cleanup state,
and elapsed time. An authored candidate then receives one independent read-only
Astra review inside the selected standard window; a host clarification ends after
the one host call and writes nothing. There is no participant selector,
remaining-candidate author, deterministic join, repair, retry, or fallback lane.
Admission is not proof of universal entailment. Independent semantic,
transaction, browser, recovery, and UX adjudication remains a release gate,
including regression examples previously caught by retired mechanisms. Exact
citations and a passed structural quality manifest are not an entailment
guarantee. The sealed host-candidate and review receipts remain bound to the
complete source, candidate, and Product Intent authority.

Identical quote bytes at a different location do not prove the selected role.
Participant and state-object selectors use exact prefix/quote anchors and strict
anchor occurrences, without ordinal normalization or word-boundary repair.
The other existing quote/occurrence citations normalize an impossible ordinal
only when the quote has one exact location; ambiguous repeated matches fail closed.
Missing-information clarification uses empty model `evidence_quotes`; the compiler
binds the exact complete admitted input, including its byte range and hash. This
records examined-source custody, not proof that information is absent. Contradictions
still require two to four exact distinct model-selected source citations. Ambiguity
cannot accept nonempty model quotes or substitute for contradictory evidence.
The existing clarification dimension schema distinguishes an unstated usable
actor/task/result (`first_path`) from unclear product responsibility or scope
(`product_boundary`). Missing-information questions retain their canonical wording.
For a contradiction, the question asks which conflicting requirement should apply;
the human view presents the existing validated opposing source spans immediately
before it. JSON retains those same spans beside the question. Neither view infers,
truncates, or recomposes the conflicting claims. Full-source
clarification JSON can repeat the bounded input; no lossy excerpt or whitespace
matching mechanism is introduced.
Clarification receipts retain both actual pre-review role observations and the
shared model window; they record two calls and no final-review observation.
Participant inventory does not assign human actions or product access. Project
labels people without a typed first-path action as participants, and its operator
projection includes only typed human performers. Atlas retains all contextual
people without inferring person-to-product interaction edges; performer descriptions
and the sequence view come from the existing typed event relations.
An overrun fails without another call; a smaller caller-supplied model window
never extends the selected consumer deadline.
An initial non-structured provider failure retains its categorical code, profile,
timing and response shape through the existing private proof channel, never raw
failed output or provider diagnostic text. Public failure wording stays unchanged.
External-system admission and component ownership are defined on their existing
shared schema properties: an external dependency requires a source-stated product
exchange or operational dependency, and human-enabled work retains its enclosing
product capability as component responsibility. Output recipients, reviewers and
task data alone do not establish an external dependency. No schema shape, model
stage, profile or deadline changes with these descriptions.

## Filesystem contract

The supported publication target is one local writable repository with owned
relative paths, no symlink traversal, an exclusive advisory lock, same-filesystem
atomic file replacement, and durable `fsync` support. Greenfield materializes the
sealed after-image as an immutable generation, projects compatibility files under
rollback guard, and records active-generation identity for recovery and coherent
Greenfield handoff reads.

The public guarantee remains journaled crash recovery, not package-level atomic
visibility. Compatibility readers do not yet universally resolve one atomic
generation pointer. Injected failures must therefore preserve or recover the
journaled transaction truth without claiming that every repository reader can
observe only an all-old or all-new package.

The supported `odylith` CLI is the cooperating boundary for later managed writes.
While such a writer holds the repository lock, canonical readers remain on the old
generation. A zero-exit writer supersedes it only after the managed tree actually
changes. Failed and no-op writers do not supersede it. Unexplained drift from a
direct filesystem edit or interrupted non-cooperating writer makes the canonical
current view unavailable instead of exposing uncertain live bytes. The exact
reviewed generation remains available as an immutable receipt. This is not a
claim that arbitrary external writers are transactionally governed.

## Custody and ambiguity

Accepted facts retain source spans and entailment receipts. Conservative
completion is labeled as an assumption or bounded interpretation. One focused
question is allowed only for unresolved material ambiguity; non-material gaps do
not become Product Intent failures.

Problem, Customer, Opportunity, and Product View each use either a distinct cited fact or
one concise, useful provisional statement. Canonical assumptions carry an
`applies_to` target and `statement`; their text and role are hash-bound but never
become accepted source facts. Required decision fields render these statements
with an explicit Assumption label, not repeated gap notices. Product Intent
envelope and authority v10 reject earlier staged formats without reinterpretation.
Product-only and external-system workflows need no invented human participant.
Every event still binds to a source-cited typed actor. A provisional customer stays
an explicitly labeled assumption, never a human actor, dependency, or accepted fact;
projections do not infer a customer from the first participant.
Authored semantics v14 stores one actor identity per event: the selected actor fact,
and separately binds the required provisional design.
The v68 raw authoring contract selects that actor through `actor_fact: {field, row}`,
using the same one-based fact-row convention as terminal results. Actor references
may select only title, human actors, internal systems, or external systems; scalar
title uses row 1. The compiler resolves the original selected row through source
custody and derives the canonical kind, path and exact quotation. Identical names
do not choose an actor implicitly, and quote-only event references are rejected.
This structural address does not establish entailment: source review must still
verify that the selected actor performs the action. Confirmation does not migrate
old raw authoring responses or reinterpret their actor references.
Aliases, pronouns, and omitted subjects remain in the original event text; they do
not create a second actor field or a grammatical carry state. Event-actor atomic
links in ledger v3 cite the selected fact directly, not a substring of the action.
The custody ledger v7 and current sealed-format checks reject older formats rather
than translating their meaning during confirmation.
Failure tracking and restoration remain source-cited actions; an ungrounded
recovery classification is not part of the authored event contract.

## Post-confirm boundary

`CONFIRM` accepts exact sealed bytes. Product interpretation, semantic repair,
artifact generation, host-model work, and projection rebuilding are forbidden
inside the commit path. Lock, disk, permission, or filesystem failures are
environment or recovery outcomes, never Product Intent rejection.

`REJECT` is terminal for the retained hash and has the same no-compiler,
no-model boundary. `EDIT` is pre-confirm evidence handling, not a post-confirm
repair: it may compile the sealed original source with one new untrusted
correction and return a new preview/hash while preserving the original tier,
release limits, and old seal.
