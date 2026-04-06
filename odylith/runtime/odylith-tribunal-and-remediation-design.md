# Odylith Tribunal and Remediation Design

## Purpose
This document is the public product-level explainer for Odylith's governance
reasoning and action loop.

## Control Flow

1. `odylith sync` refreshes deterministic local posture from repo-local truth,
   runtime ledgers, and generated surface state.
2. Delivery intelligence shapes the scope universe that is eligible for review.
3. Tribunal builds bounded dossiers, ranks eligible cases, and produces the
   maintainer-facing brief plus packet seed.
4. Remediator turns an adjudicated prescription into one bounded correction
   packet with validation, rollback, and stale guards.
5. Odylith records approval, delegation, apply, and clearance outcomes back into
   `.odylith/` runtime state and refreshes the shell surfaces.

## Product Contracts

- Runtime state:
  - `.odylith/runtime/posture.v4.json`
  - `.odylith/runtime/reasoning.v4.json`
  - `.odylith/runtime/delivery_intelligence.v4.json`
  - `.odylith/runtime/decisions.v1.jsonl`
- Schemas:
  - `odylith/runtime/contracts/tribunal_case.v1.schema.json`
  - `odylith/runtime/contracts/tribunal_outcome.v1.schema.json`
  - `odylith/runtime/contracts/correction_packet.v1.schema.json`
- Product surfaces:
  - `odylith/index.html`
  - `odylith/compass/`
  - `odylith/registry/`

## Operator Contract

Operators should use the public Odylith surface:

```bash
odylith sync --repo-root . --force
odylith context-engine --repo-root . status
odylith compass update --repo-root . --statement "<current state>"
odylith compass log --repo-root . --kind decision --summary "<decision>"
```

## Repo Boundary

Host repositories keep their own plans, bugs, specs, runbooks, component
registry, and generated repo truth. Odylith reads those inputs in place and
renders governance behavior around them; it does not absorb them into the
product repo.
