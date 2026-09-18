# Greenfield Operating Envelope

Version: `odylith.greenfield-operating-envelope.v3`

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
transaction hash: `decide ... CONFIRM <hash>`, `decide ... EDIT <hash> --edit
<corrections>` (or `--edit-evidence <file>`), and `decide ... REJECT <hash>`.
Ordinary chat approval is not a terminal decision. Explicit terminal `CONFIRM`
and `REJECT` share a bounded deterministic owner and invoke neither compiler nor
model. `EDIT` verifies the retained hash, lazily uses the existing compiler with
the sealed original source and new untrusted correction, preserves tier and the
timing contract, retains the old seal, and returns a new hash and
preview. It adds no schema, stage, retry, or repair mechanism. The sealed-byte
`create` CLI remains a separate commit-only interface. Native automatic delivery
and visible completion require their own proof.

Release evaluation covers three pinned candidate success profiles; their identity
does not itself establish qualification:

- `greenfield-standard-terra-low-complete-author-review-v17`: the default and
  `auto` path, with a 90-second advisory performance target.
- `greenfield-rescue-terra-medium-complete-author-review-v17`: the explicit rescue
  path, with a 120-second advisory performance target.
- `greenfield-deep-sol-high-complete-author-review-v17`: the explicit deep path,
  with a 150-second advisory performance target.

All three profiles use one 180-second operational timeout and one 165-second
shared model window, leaving 15 seconds for deterministic completion. Meeting or
missing the selected 90/120/150-second target is recorded as performance evidence,
not used as an admission gate. Proposal elapsed time must remain strictly below
the operational timeout. Sixty seconds remains an advisory normal-case target.
The separate commit-only step must still finish strictly below 60 seconds.
Candidate v17 separates performance targets from the finite operational timeout
while retaining the standard Terra-low author posture. This timing change does
not qualify any author candidate; call count, prompts, semantic requirements,
reviewer identity, and transaction laws are unchanged.
Historical observations keep their original limits and verdicts; old sealed
v12/v13/v14/v15/v16 transactions are not relabeled or accepted as v17. Fresh
per-profile evidence is required for qualification.

The selected profile is fixed before the model request. Elapsed time or a failed
attempt never relabels or extends a standard request into rescue or deep.
Standard uses Terra low, rescue uses Terra medium, and deep uses Sol high for
one complete authoring call. An authored result then requires one read-only
Astra/medium review of the complete candidate using only
the shared model window's remaining time. There is no separate review-stage cap.
Reviewer setup, validation and finalization
are inside that deadline. No fixed author reserve, retry, repair call or tier
promotion follows. Invalid authoring and material clarification do not invoke review.
These are bounded candidate profiles, not claims about every provider model.
Host-model output is candidate evidence only. Every profile must clarify or fail
safely instead of inventing product truth. Provider unavailability is separately
proven as a fast, no-write environment outcome and is not a supported-success
profile.

The reviewer change is an unreleased candidate, not production qualification.
It passed four retained positive/negative controls and one exact independent
repeat under unchanged prompts and residual caps. Its first fresh standard package
then completed in 59.563 seconds with two calls, no independently observed P0/P1
and 32 passing desktop/mobile browser states. Four advisory presentation issues
remain. This is one development sample, not a reliability estimate, installed
proof, qualification of rescue/deep, or broader release readiness.

Standard and rescue use lower-capability authors relative to Sol deep. Release
proof requires each profile's observed committed positive case and a source-bound material
clarification with no writes, separately from unavailable-provider behavior.
No other model earns a proof claim without its own observed request evidence.

Authoring v53 returns either a reviewed source-and-design candidate or the
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
Private proof retains both actual requests, responses, profiles, caps and elapsed
times. Successful native receipts require exactly two calls and bind admission to
the complete candidate and the sealed source/intent hashes. Single-call observations
cannot qualify these profiles. Admission is not proof of universal entailment.
Independent semantic, transaction and UX adjudication remains a release gate,
including regression examples previously caught by the retired source reviewer.
This candidate has not earned a release or universal-success claim.
The previous one-call path admitted a source-exact operator invocation under the
wrong product-story role and lost an explicit source prerequisite in another
actual package. Those failures motivate this boundary. The complete reviewer passed
five frozen discrimination controls, and one actual author/reviewer candidate
passed independent semantic review in 54.975 seconds before full-package work.
That is component and model-window feasibility evidence, not complete consumer
timing, robustness or release qualification. Exact citations and a passed
structural quality manifest must not be reported as an entailment guarantee.

The subsequent native standard-tier gate failed: authoring took 50.496 seconds,
leaving 4.499 seconds for review, which returned no verdict. The command stopped
at 55.441 seconds without a complete package. This is a failed qualification,
not a sub-60-second success. The sequential candidate has not demonstrated
sufficient timing headroom; the consumer limits and semantic floor stay fixed.

Identical quote bytes at a different location do not prove the selected role.
An impossible ordinal can normalize only when the quote has one exact location;
ambiguous repeated matches fail closed without word-boundary repair.
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
Clarification receipts retain the actual single-call authoring observation.
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
