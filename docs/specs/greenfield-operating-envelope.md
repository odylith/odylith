# Greenfield Operating Envelope

Version: `odylith.greenfield-operating-envelope.v6`

Profile: `single-product-governance-onboarding`

This defines Greenfield's bounded support target. A production release claim
still requires semantic, transaction, host, browser, and holdout proof within
this envelope.

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

Model-profile contract `odylith.greenfield.model-profile-contract.v24`
declares three pinned real-model profiles. Only the
standard profile is an eligible release-success route; eligibility does not
qualify a release without observed end-to-end evidence:

- `greenfield-standard-host-candidate-astra-medium-v20`: the default and
  `auto` path, the sole eligible release-success profile, with a 90-second
  advisory performance target.
- `greenfield-rescue-host-candidate-luna-medium-v20`: an explicit
  lower-capability clarification/no-write control with a 120-second advisory
  target. It is declared but is not success-qualified.
- `greenfield-deep-host-candidate-sol-high-v19`: an unsupported negative and
  diagnostic profile with a 150-second advisory target. It is declared but is
  not success-qualified.

All three profiles use one 180-second operational timeout and one 165-second
shared model window, leaving 15 seconds for deterministic completion. Meeting or
missing the selected 90/120/150-second target is recorded as performance evidence,
not used as an admission gate. Proposal elapsed time must remain strictly below
the operational timeout. Ninety seconds is the advisory normal-case target.
The separate commit-only step must still finish strictly below 60 seconds.
Profile contract v24 separates declared profiles, the release-success profile,
and the lower-capability control instead of treating evidence profiles as
interchangeable success routes. The advisory targets, finite timeout, semantic
requirements, and transaction laws are unchanged.
Historical observations keep their original limits and verdicts; old sealed
transactions and earlier model-profile receipts are not relabeled as current.
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

Canonical authoring `odylith.greenfield.intent-authoring.v77` receives one
host-owned candidate in host format v18 under candidate contract v33. The
host first returns one authority decision;
an admitted request receives one candidate pass. The deterministic compiler
validates that candidate, its citations, and relationships, then derives and
seals their canonical relation hash. It does not call a runtime semantic
model, run an online candidate reviewer, correct a candidate, or select a
fallback profile after receipt. A clarification stops without staging.

The candidate keeps source facts, actions, and relationships citation-bound.
Its separately labeled `provisional_design` currently requires 4–5 logical
components and 4–5 workstreams, plus internal exchanges and verification.
That fixed cardinality does not prove the depth is useful; release review
must reject padding on simpler projects. Design references source-event
identities without changing who performs the actions; it cannot create
accepted source facts. Five
deterministic Atlas views separate source context and first path from proposed
exchanges, delivery dependencies, and capability support. Counts alone do
not qualify their quality.

Host evidence uses `{quote, context}` selections, including one source
citation per event. The canonical resolver derives byte locations and its
internal quote/occurrence or prefix/anchor citation forms. A quote at a
different source location does not prove the selected role; ambiguous matches
fail closed. The sealed candidate and relation hashes bind the admitted
source to the canonical package. Host request arguments, model identity,
response hash, call count, cleanup, and elapsed time are observed by the
external release harness, not inferred from the sealed runtime receipt.

Admission is not proof of semantic entailment. Independent source-first
review, transaction, browser, recovery, and UX adjudication remain release
gates outside consumer admission. Exact citations and a passed structural
manifest are insufficient for a production claim.

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
Clarification records the authority or candidate stage actually reached and
does not report a nonexistent final-review call. A gate clarification requires
the focused first-path question and no witness citations; it writes nothing.
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
envelope and authority v13 reject earlier staged formats without reinterpretation.
Product-only and external-system workflows need no invented human participant.
Every event still binds to a source-cited typed actor. A provisional customer stays
an explicitly labeled assumption, never a human actor, dependency, or accepted fact;
projections do not infer a customer from the first participant.
Authored semantics v16 stores one actor identity per event: the selected actor fact,
and separately binds the required provisional design.
The raw host format v18 selects that actor through `actor_fact: {field, row}`
using the same one-based fact-row convention as terminal results. The compiler
projects this into canonical authoring v77. Actor references
may select only title, human actors, internal systems, or external systems; scalar
title uses row 1. The compiler resolves the original selected row through source
custody and derives the canonical kind, path and exact quotation. Identical names
do not choose an actor implicitly, and quote-only event references are rejected.
This structural address does not establish entailment: independent semantic
release review must verify that the selected actor performs the action.
Confirmation does not migrate old raw authoring responses or reinterpret
their actor references.
Aliases, pronouns, and omitted subjects remain in the original event text; they do
not create a second actor field or a grammatical carry state. Event-actor atomic
links in ledger v3 cite the selected fact directly, not a substring of the action.
The custody ledger v10 and current sealed-format checks reject older formats rather
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
