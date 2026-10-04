# Greenfield Operating Envelope

Receipt version: `odylith.greenfield-operating-envelope.v6`

Document revision: `11`

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

Model-profile contract `odylith.greenfield.model-profile-contract.v25`
declares three pinned real-model profiles. Only the
standard profile is an eligible release-success route; eligibility does not
qualify a release without observed end-to-end evidence:

- `greenfield-standard-host-candidate-astra-medium-v21`: the default and
  `auto` path, the sole eligible release-success profile, with a 90-second
  advisory performance target.
- `greenfield-rescue-host-candidate-luna-medium-v20`: an explicit
  lower-capability clarification/no-write control with a 120-second advisory
  target. It is declared but is not success-qualified.
- `greenfield-deep-host-candidate-sol-high-v19`: an unsupported negative and
  diagnostic profile with a 150-second advisory target. It is declared but is
  not success-qualified.

The standard profile has a 315-second proposal timeout and one shared
300-second authority-gate/candidate model window, leaving 15 seconds for
deterministic completion. The gate consumes part of that shared window; it
does not reset before candidate authoring. Lower-capability and unsupported
control profiles retain their 180/165-second limits. This constraint revision
implements the operator-approved longer bounded broad-input flow; it is not
a retry or a profile promotion. Separately bounded source-duty inventory and source-only material-duty
verification precede `propose` for the broad free-form path. The inventory's
current 300-second cap and verifier's 120-second cap are diagnostic; the finite
whole-journey release limit must be selected from fixed public complete runs.
Each local source-ledger preflight and receipt check has its own 30-second
limit after its host stage. The release harness additionally enforces one
660-second diagnostic deadline across all phases, retained-evidence callbacks,
and cleanup. This hard ceiling stays fixed at 660 seconds; phase maxima are
not additive allocations. It is explicitly `diagnostic_unqualified`, not a
public-data-backed consumer limit. Each dispatched request receives at most
the whole journey's remaining time. Candidate dispatch additionally reserves
15 seconds for completion. A callback returning after expiry makes the flow
fail before confirmation. Observation v12 samples elapsed time after the advisory observer
returns and publishes an owned final snapshot. Its explicit elapsed scope
includes model calls, local checks, raw artifact retention, cleanup, and the
observer; the final timestamp JSON serialization follows that sample.
It distinguishes `proposal_phase_elapsed_seconds`
from `whole_journey_seconds`; legacy `elapsed_seconds` retains the proposal
phase value. Product-owned timing custody across separate CLI invocations and
a measured release bound remain unproved. Citation context is a verbatim source excerpt that
contains the selected quote and occurs once in the complete evidence.
Ledger v5 owns each normalized action, target, and statement once. Exact event
and actor citations plus role context support that meaning; the compiler
derives support indexes and does not require invented verb or target
microspans. Compact v3 verification supplies every material row and citation
once with the complete authority source. Decision v4 returns one closed table
keyed by duty ID plus source-wide completeness. The compiler owns canonical
judgment order and hash custody; workflow order stays in the source inventory.
The actor, event, and role contexts must all be selected by an affirmative
judgment. Atomic action and target projections retain the complete exact event
as source support and their exact slice of the verified normalized statement.
At host intake the compiler validates every bank citation against the complete
source, including unused selections. It resolves referenced IDs and omits only
unused bank storage from the canonical ledger. Unknown or duplicate IDs,
duplicate quote/context pairs, and invalid used or unused selections reject.
Decoding without complete source cannot discard unused selections.
Candidate authoring transport v1 retains the complete source request,
candidate requirements and schema, versions, and admitted authority gate. It
presents the accepted material inventory through the same lossless compact
citation bank plus receipt custody hashes. The complete accepted receipt stays
outside the model for deterministic proposal admission. Completed authority and
inventory authoring schemas and completed verifier decisions are absent from
this phase's request. Citation resolution preserves exact quotes and contexts;
this view neither reinterprets duties nor adds a semantic stage. Observation
v12 records the exact candidate request bytes, hash, transport version, and
candidate completion reserve.
This revised path remains unqualified pending fresh complete public packages.
Neither a successful proposal receipt nor the inventory's own duration proves
the whole journey. Meeting or missing the selected 90/120/150-second target is
recorded as performance evidence, not used as an admission gate. Proposal
elapsed time must remain strictly below its operational timeout. Ninety
seconds is the advisory normal-case target.
The separate commit-only step must still finish strictly below 60 seconds.
Profile contract v25 separates declared profiles, the release-success profile,
and the lower-capability control instead of treating evidence profiles as
interchangeable success routes. The advisory targets, semantic requirements,
and transaction laws are unchanged. The standard phase limit is revised as
declared above; earlier 180/165-second v20 evidence remains unchanged and
cannot qualify v21.
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

Canonical authoring `odylith.greenfield.intent-authoring.v79` receives one
host-owned candidate in host format v21 under candidate contract v46. The
source-duty host returns one compact citation bank and typed rows that refer
to it; deterministic expansion restores the same complete cited ledger before
preflight. This path remains unqualified. Earlier v44 public evidence failed
duplicate-action custody; the fresh v45 installed civic run stopped on one
unused exact opening-outcome citation before verification or package creation.
Neither failed result becomes a positive for v46. Each host
stage returns only its schema-matching JSON; the external controller owns file
custody, CLI checks, and the separate verifier call. The host first returns one
authority decision. An admitted request receives one
exact-cited source-duty inventory (ledger v5), one source-only material-duty verdict
pass, and one candidate pass. Ledger action rows own a normalized statement,
action, and target, with exact actor, event, and role citations and a typed performer
role. Structural preflight exposes every hash-bound row across all eight material
duty sections and the complete authority source to the verifier. In the same
pass, the verifier must decide whether the inventory omits any material duty
from that full source and cite omissions when it does. An accepted receipt v7
requires one affirmative cited verdict per row, an affirmative source-wide
completeness verdict, and the complete verifier task hash; missing, negative,
uncertain, or
mismatched verdicts stop before candidate authoring. The candidate selects
actor fact addresses, design owners, and run order; it cannot independently
author action text. Binding v3 maps each
candidate event to exactly one ledger action and retains cited passive state
transitions, conditional guards, boundaries, and proof duties. The deterministic compiler
validates citations, role coverage, relationships, and hashes, then seals one
canonical relation set. The first path contains only binding-selected task
events; other cited events remain in `supporting_events`. Two actions can share
one exact source clause while retaining separate normalized typed relations.
The verifier's judgment and inventory completeness need independent source-first
semantic review; hashes only prove receipt consistency. Earlier action-only
and rows-only receipts do not qualify or admit the complete package. There is no runtime
post-receipt model call, online candidate reviewer, correction, or fallback
profile. A clarification stops without staging.

Atomic fact ledger v4 carries a narrow verified-action relation with exact
source anchors and normalized event text. This can represent an inherited verb
such as `A reviewer defines scope and audience.` across distinct action roles.
The broad free-form envelope remains unqualified until unchanged public
cross-domain packages pass blinded semantic review and the complete journey,
transaction, installed, browser, host, private, and final-holdout gates.

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
timing and response shape through the existing private proof channel. Public
failures and observations never include raw failed output or diagnostic excerpts.
The release harness may retain native host stdout/stderr outside the repository
for diagnosis, with private permissions and a 256 KiB stderr limit. Oversized
stderr fails closed with its full size/hash; it is never silently clipped.
These streams confer no semantic admission credit. Host timeouts use the shared
process-group cleanup owner and suppress later phases. Descendants escaping that
group remain explicitly unverified. Successful v12 observation fields and the
declared model and whole-journey limits remain unchanged.
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
Authored semantics v18 stores one actor identity per event: the selected actor fact,
and separately binds the required provisional design.
The raw host format v21 selects that actor through `actor_fact: {field, row}`
using the same one-based fact-row convention as terminal results. The compiler
projects this into canonical authoring v79. The verified source-duty ledger
supplies each normalized event statement, action, and target with exact event,
actor, and role citations. Actor references
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
links in atomic ledger v4 cite the selected fact directly, not a substring of the action.
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
