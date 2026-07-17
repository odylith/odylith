- Bug ID: CB-269

- Status: Open

- Created: 2026-07-17

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: Sparse edits can retain stale title-hypothesis product facts

- Impact: An EDIT can present a stale or incomplete first path instead of recompiling a coherent pre-confirm package from the edited evidence.

- Components Affected: domain-intelligence

- Environment(s): Product-repo maintainer source-local pre-confirm compiler

- Detected By: Adversarial consumer-utility review

- Failure Signature: Visible-result edit produced Representative User can see an occupancy decision packet; title-only edit retained City Zoning Permit Review facts under a new title

- Trigger Path: materialize_prompt_intent_hypothesis -> _merge_edit_evidence for visible-result-only or title-only EDIT

- Ownership: Greenfield prompt intent materialization and edit reconstruction

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Title-derived prompt proposals receiving sparse but meaningful EDIT evidence.

- SLO/SLA Impact: Users may review misleading product facts before confirmation and need unnecessary correction turns.

- Data Risk: No governed write occurred; defect is confined to pre-confirm staging.

- Security/Compliance: Domain: product facts can describe the wrong product. Delivery: users receive an incoherent confirmation preview. Operational: the compiler retains stale derived fields. Security/compliance: no direct security or regulatory impact.

- Invariant Violated: Every EDIT must rebuild a coherent first-path package from current evidence and retain only assumptions that remain true.
