- Bug ID: CB-268

- Status: Open

- Created: 2026-07-17

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: Pre-confirm staging artifacts can be reentered as confirmed authority

- Impact: A staged preview or evidence file can bypass the confirmation contract and become authority for a new create compile.

- Components Affected: domain-intelligence

- Environment(s): Product-repo maintainer source-local pre-confirm compiler

- Detected By: Adversarial custody and authority review

- Failure Signature: candidate-evidence.md and candidate-intent.md load as confirmed intent; loading candidate-intent.md overwrites candidate-intent.json with a confirmed envelope

- Trigger Path: materialize_prompt_intent_hypothesis -> load_confirmed_intent_args using a .odylith/runtime/greenfield staging artifact

- Ownership: Greenfield confirmed-intent loader and staged evidence custody

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Every prompt-first or EDIT proposal that leaves candidate preview or evidence files in the runtime staging directory.

- SLO/SLA Impact: A reviewable package can be bypassed before confirmation, breaking deterministic confirmation semantics.

- Data Risk: No governed write occurred in the reproduction; untrusted staging evidence can be promoted to authority.

- Security/Compliance: Domain: accepted product intent can be misrepresented. Delivery: confirm-only semantics can be bypassed. Operational: staging data can overwrite the typed candidate. Security/compliance: no direct security or regulatory impact.

- Invariant Violated: No pre-confirm staging artifact may be loaded, promoted, or rewritten as confirmed Product Intent authority.
