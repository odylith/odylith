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

Codex and Claude are the deterministic confirmation hosts. Both pass the sealed
transaction hash to the same commit-only confirmation callback. Other hosts may
render proposals but cannot offer governed writes until they prove the same hash
callback and visibility contract.

Release evaluation covers three pinned successful profiles:

- `greenfield-standard-gpt-5.6-terra-medium-v6`: the default and `auto` path, with
  one 60-second end-to-end consumer budget and a 55-second model window.
- `greenfield-rescue-gpt-5.6-sol-high-v5`: the explicit rescue path, with one
  90-second end-to-end consumer budget and an 80-second model window.
- `greenfield-deep-gpt-5.6-sol-high-v5`: the explicit deep path, with one
  120-second end-to-end consumer budget and a 105-second model window.

The selected profile is fixed before the model request. Elapsed time or a failed
attempt never relabels or extends a standard request into rescue or deep.
Standard uses medium reasoning on the faster Terra author; rescue and deep use
high reasoning on Sol. The tiers preserve semantic capability while fitting
their fixed elapsed-time envelopes. These are bounded provider-request
profiles, not claims about every provider model.
Host-model output is candidate evidence only. Every profile must clarify or fail
safely instead of inventing product truth. Provider unavailability is separately
proven as a fast, no-write environment outcome and is not a supported-success
profile.

The standard Terra profile is the supported lower-capability member. Release
proof requires its observed committed positive case and a source-bound material
clarification with no writes, separately from unavailable-provider behavior.
No other model earns a proof claim without its own observed request evidence.

Pre-confirm authoring permits at most two model calls: initial intent authoring,
then one source-claim review of the product story, component ownership, and human selections for
every otherwise-valid authored candidate. Clarifications need only the first call.
The review shares the original model window and is capped at 20 seconds; it cannot
extend the consumer deadline or change the chosen profile. The complete candidate
must pass custody and semantic validation again. Explicit recipients need not perform
a first-path action. Other fields, including event bindings, remain unchanged,
and a failed review never starts another call. Receipts record the actual call
count; release proof retains both candidates and the exact review response.

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
Authored semantics v13 stores one actor identity per event: the selected actor fact.
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
