# Greenfield Operating Envelope

Version: `odylith.greenfield-operating-envelope.v1`

Profile: `single-product-governance-onboarding`

This contract defines where Odylith may compile and confirm a Greenfield
governance package. It is a release boundary, not a claim of universal semantic
correctness.

## Supported request shape

- One product and one first-release path.
- Text evidence supplied as an operator prompt, operator edit, Markdown product
  brief, JSON record, or typed Product Intent envelope.
- Up to 8 MiB of staged evidence, 64 human actors, and 128 systems on either
  side of the product boundary.
- A repo-local governance package only. Greenfield does not generate application
  code, deploy software, call external systems, or exercise production authority.
- Product domains where the evidence can support one actor-owned path, a visible
  result, and a bounded proof statement without inventing a safety, compliance,
  clinical, regulatory, or production claim.

## Confirmation hosts

Codex and Claude are the supported confirmation hosts. They render the same
sealed transaction contract and pass the exact transaction hash to the
commit-only command. Other hosts remain advisory or read-only until they prove
the same deterministic confirmation and visibility contract.

## Custody states

- `accepted_fact`: a direct or normalized product claim with retained source
  spans and hash receipts.
- `bounded_interpretation`: a visible pre-confirm interpretation tied to retained
  evidence spans. It is not presented as a source fact.
- `assumption`: a visible, reviewable gap that does not change the material first
  path or proof boundary.

An unresolved material field cannot be sealed. A material ambiguity produces one
focused question. Non-material gaps remain visible assumptions and do not turn
into generic Product Intent failures.

## Post-confirm boundary

`CONFIRM` accepts the exact sealed package. Product interpretation, semantic
repair, artifact generation, host-model work, and projection rebuilding are
forbidden after confirmation. Disk, permission, lock, or filesystem failures are
reported as environment failures with durable recovery state; they are not
misreported as Product Intent rejection.

The transaction contract must not claim package-level atomic visibility unless
governed bytes live in an immutable generation and every reader resolves one
atomically switched active pointer.
