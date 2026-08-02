# Greenfield Operating Envelope

Version: `odylith.greenfield-operating-envelope.v2`

Profile: `single-product-governance-onboarding`

This is the bounded release claim for Greenfield, not a claim of universal
semantic correctness.

## Supported evidence

- English text supplied as one operator request plus, optionally, one edit.
- Operator text, pasted Markdown, JSON Product Intent, or a typed Product Intent
  envelope. PDF, image, audio, and remote-URL ingestion are not direct Greenfield
  formats; a host may extract their text as untrusted evidence first.
- 1 byte through 8 MiB of combined evidence, at most two evidence documents.
- One product and one first-release path, with at most 64 human actors, 16 state
  objects, 128 external systems, 128 internal systems, 16 contradictions, 32
  ambiguities, and 32 explicit safety or operational boundaries.

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

Codex and Claude are the deterministic confirmation hosts. Both pass the pending
transaction hash to the same pre-model callback. Other hosts may render proposals
but cannot offer governed writes until they prove the same callback and visibility
contract.

Release evaluation covers `provider-free-standard-v1`,
`bounded-reasoning-standard-v1`, and `lower-capability-safe-v1`. These are behavior
profiles, not claims about every provider model. Host-model output is candidate
evidence only. The lower-capability profile must clarify or fail safely instead of
inventing product truth.

## Filesystem contract

The supported publication target is one local writable repository with owned
relative paths, no symlink traversal, an exclusive advisory lock, same-filesystem
atomic file replacement, and durable `fsync` support. Current package publication
uses journaled crash recovery. It does not yet claim atomic package visibility
through an active-generation pointer.

## Custody and ambiguity

Accepted facts retain source spans and entailment receipts. Conservative
completion is labeled as an assumption or bounded interpretation. One focused
question is allowed only for unresolved material ambiguity; non-material gaps do
not become Product Intent failures.

## Post-confirm boundary

`CONFIRM` accepts exact sealed bytes. Product interpretation, semantic repair,
artifact generation, host-model work, and projection rebuilding are forbidden
inside the commit path. Lock, disk, permission, or filesystem failures are
environment or recovery outcomes, never Product Intent rejection.
