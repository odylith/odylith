- Bug ID: CB-351

- Status: FixedPendingRelease

- Created: 2026-09-30

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The host citation resolver accepts a uniquely occurring quote while ignoring whether its supplied context occurs at that source location. A candidate can therefore present fabricated surrounding context as if it came from the operator evidence.

- Impact: Exact quote admission can carry false source context into canonical custody and weaken source-authority review.

- Components Affected: domain-intelligence

- Environment(s): Odylith product-repo maintainer branch 2026/freedom/v0.1.15, source-local runtime and installed release path.

- Detected By: Independent review of the Greenfield operating-envelope documentation against the active resolver, followed by a fabricated-context reproduction.

- Failure Signature: greenfield_model_source_citations.py returns for a unique quote before validating the supplied context; quote one source with absent fabricated context is accepted.

- Trigger Path: Supply a host citation with a unique exact quote and a context string absent from the operator source, then materialize it through the canonical source resolver.

- Ownership: Greenfield source citation resolver and canonical custody.

- Timeline: Captured 2026-09-30 through `odylith bug capture`.

- Blast Radius: Every unique-quote host citation carrying misleading context; no evidence of a published affected package yet.

- SLO/SLA Impact: Blocks P0/P1-free Greenfield semantic release qualification.

- Data Risk: Risk of semantic custody corruption in a staged package; no observed committed data loss.

- Security/Compliance: Security and policy risk: untrusted host text can appear as source context; no committed access violation observed.

- Invariant Violated: Accepted citations must bind both quoted text and its claimed source context to the same admitted evidence location.

- Workaround: Withhold release qualification and independently inspect candidate context against source until resolver validation is corrected.

- Related Incidents/Bugs: CB-324 source-custody release blocker; CB-350 public contract drift exposed this discrepancy.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_model_source_citations.py
- docs/specs/greenfield-operating-envelope.md

- Fixed: 2026-09-30

- Fixed In: 0.1.15

- Solution: The canonical resolver now verifies that the host context occurs
  uniquely in the admitted source and contains the selected quote before it
  normalizes a unique-quote citation. The same rule applies to state citations.

- Verification: Focused citation and adjacent custody controls passed 73/73,
  including fabricated, disconnected, and invented-suffix contexts. The fast
  Greenfield suite passed 1,310/1,310. Installed public semantic qualification
  remains blocked separately by CB-324.
