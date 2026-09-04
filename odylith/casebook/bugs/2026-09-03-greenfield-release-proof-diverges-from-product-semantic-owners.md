- Bug ID: CB-329

- Status: Open

- Created: 2026-09-03

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The current-contract one-shot Greenfield holdout produced several real product failures, but independent adjudication also found that duplicate evaluator semantics turned valid product structures into release failures and removed the raw artifacts needed to adjudicate every case.

- Impact: Release scoring cannot distinguish genuine Greenfield semantic defects from proof-harness disagreement, so a terminal 0/21 result is not a trustworthy measure of consumer quality even though it correctly blocks release.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Immutable dist-v14 from candidate 62bcdd8147e47874e984483b48fb1fb0a20ca413; final-holdout v4 package 68f8a2570f74dbd4d9b721b33da75a92365d7383ca76255db7c5eb93c0d36742; one-shot run completed 2026-09-03.

- Detected By: Independent read-only adjudication of the consumed protected holdout, result 022a25352a3df11e6a8a49e92a802534f2683a26daccfcebd920315abc072178.

- Failure Signature: Fifteen Atlas cases failed an evaluator-only arrow whitelist although the product parser accepts non-arrow topology; relation fidelity collapsed to 0/312 because the scorer rejects valid state_object order 0; the write observer counted generic subprocess and relative cleanup activity as governed writes; all-1.0 Wilson gates were mathematically unattainable at finite sample size; raw generated artifacts and screenshots were cleaned before adjudication.

- Trigger Path: scripts/release/run-greenfield-final-holdout.sh through the v4 semantic release scorer and matrix evidence collectors.

- Ownership: Greenfield release evaluator semantic-contract ownership and retained-evidence boundary.

- Timeline: Package passed pure preflight, ran exactly once, terminated failed and disclosed, and was then independently adjudicated into product versus evaluator failure classes. The ledger is consumed and this holdout is retired permanently.

- Blast Radius: Protected release adjudication, final-holdout metrics, clarification no-write scoring, Atlas scoring, relation scoring, and release confidence reporting; normal consumer proposal and create paths are not directly changed by the evaluator defects.

- SLO/SLA Impact: Blocks an honest Greenfield completion claim and any reliable time-to-release estimate; public 60/90/120 latency itself remained within budget.

- Data Risk: No governed consumer data loss; evidence cleanup prevents complete retrospective adjudication and can misclassify release quality.

- Security/Compliance: No direct security exposure; proof provenance and auditability are weakened when duplicate validators disagree with product truth or raw evidence is unavailable.

- Invariant Violated: Release proof must measure the same semantic contracts the product owns, keep acceptance distinct from statistical confidence, and retain raw source, generated, and browser evidence through independent adjudication.

- Workaround: None. Do not rerun, reinterpret, or tune against this holdout. Use the disclosed cases only as regression evidence after repairing evaluator ownership.

- Root Cause: The release harness duplicated Atlas edge grammar, relation ordering, and write semantics instead of calling canonical product/shared owners; its frozen statistical floor representation conflated perfect point acceptance with finite-sample confidence; cleanup occurred before independent adjudication.

- Solution: Replace duplicate evaluator interpretations with the product Atlas parser and one shared semantic relation contract, scope write audit to governed mutations, express achievable finite-sample confidence separately from zero-tolerance product acceptance, and retain raw generated artifacts plus screenshots until adjudication completes. Delete the superseded duplicate paths.

- Rollback/Forward Fix: Forward fix only; keep the terminal failed ledger and disclosed package immutable.

- Verification: Replay the disclosed Atlas arrow and non-arrow controls, state_object order-0 relation controls, clarification cases GFH19-012 through GFH19-015, and finite-sample math tests; preserve raw artifacts; require manual and scorer agreement before commissioning a newly blinded holdout.

- Prevention: Make proof code import or call canonical semantic owners, add contract-parity tests, and fail preflight when evidence-retention or statistical-gate configuration cannot support adjudication.

- Agent Guardrails: Do not weaken product acceptance, lower semantic quality, add phrase rules or regex stacks, patch protected examples, or consume another final ledger before the public and disclosed-regression gates are clean.

- Preflight Checks: Raw evidence retention; Atlas parser parity for arrow and non-arrow edges; relation parity including state_object order 0; governed-write observer controls; achievable confidence math; exact 60/90/120 budgets; ledger absence for a newly authored holdout.

- Monitoring Updates: Report product failures, evaluator failures, evidence gaps, point acceptance, and statistical confidence as separate dimensions.

- Version/Build: 0.1.15 candidate 62bcdd8147e47874e984483b48fb1fb0a20ca413; dist-v14; governance f1b4ba3bf5edfca683b326c3295f1cd312fecd2d.

- Related Incidents/Bugs: CB-303, CB-315, CB-323, CB-328, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_matrix_package_evidence.py
- scripts/release/greenfield_relation_fidelity.py
- scripts/release/greenfield_matrix_write_audit.py
- scripts/release/greenfield_semantic_release_score.py

- Source Resolution (2026-09-03): The release evaluator now delegates Atlas
  topology to the product parser, accepts the canonical state-object order-zero
  contract, carries every canonical semantic snapshot field, and observes only
  canonical governed or pending Greenfield mutations. Exact point acceptance is
  independent from achievable confidence reporting. Every terminal v3 outcome
  requires hash-valid retained evidence in an explicit external directory, and
  a unique 256-bit claim run id prevents a stale manifest from terminalizing a
  later claim. Interrupted child processes must seal matching evidence or leave
  the ledger claimed and fail closed. Focused retained-evidence proof passed
  `78` tests, the complete install Greenfield suite passed `479`, and the
  combined runtime/install/Atlas/component/browser gate passed `1,171` tests.
  Independent review found no P0/P1. CB-329 remains open until the immutable
  public matrix and a newly blind holdout prove scorer/product agreement end to
  end; the consumed prior ledger and package remain permanently retired.

- Public v20 Adjudication Reopen (2026-09-03): The immutable public candidate
  passed retained-evidence sealing, commit recovery, crash retry, operator
  conflict preservation, temporary cleanup, and every browser proof that
  reached a created project, but failed product authorship `10/14` times. The
  retained failed-case evidence preserved command output and hashes yet omitted
  the raw structured authoring response, so it could identify the rejecting
  product owner but not independently adjudicate the exact rejected shape. The
  next candidate must retain exact request evidence and raw structured response
  bytes in the explicit external evidence directory before cleanup, including
  failed and clarification outcomes. Product behavior must remain unchanged
  when that release-proof capability is absent. The clarification case also
  exposed a write-audit false positive for an unresolved non-filesystem file
  descriptor; the observer must distinguish pipes from unresolved regular-file
  writes without weakening governed-path detection.

- V23 Evaluator Reopen And Source Resolution (2026-09-04): The public assay
  case returned the product's valid no-write `material_ambiguity` clarification,
  but the release evaluator accepted only `consistent` or
  `material_contradiction` and stopped the campaign. It also promoted
  `typed_structural_validation` into passed product-manager, architect,
  engineer, and domain-expert reviews that had never occurred. The evaluator
  now calls the product-owned consistency-span receipt validator, accepts a
  source-bound material ambiguity, and leaves absent independent lenses
  explicitly false and unscored. Automated contract success is labeled
  `automated_contract_independent_semantic_review_required`; real claimed lens
  failures still block. Relation scoring now follows the product's carried
  actor and source-bound terminal-result contracts instead of requiring both
  values inside each event. Focused evaluator, relation, confirmation, and
  authored-projection proof passes `130/130`; the final combined source gate
  passes `3,790/3,790`. CB-329 remains open until the immutable public matrix
  and independent adjudicators agree on every case.

- V29 Atlas Admission Reopen (2026-09-04): The same immutable flood package
  passed pre-confirm quality and validation, then public package evidence
  rejected its Component Boundary View for one repeated product label and no
  relationship. The boundary artifact existed only because a non-material
  ambiguity was counted as topology; it rendered the product inside an
  identically named product component. This is a product admission gap. The
  release evaluator also imposed a generic edge and two-label quota on every
  diagram even though distinct subgraph containment can be a valid relationship.
  V30 removes ambiguity as a boundary-artifact trigger and judges Atlas utility
  from typed diagram roles: a boundary view requires a distinct component,
  external dependency, or non-goal; an edge-free view is acceptable only when
  its authored boxes prove a distinct containment relation. Prediction: the
  unchanged flood package omits D-004, while real multi-component and external
  boundaries retain it and nodes-only diagrams without typed containment still
  fail. Campaign recovery and the unexecuted 60/90 tiers remain unproved because
  the losing run was deliberately stopped.

- V30 Atlas Admission Source Result (2026-09-04): The unchanged flood
  discriminator now stages D-001 through D-003 only. Ambiguity no longer
  manufactures D-004, while typed-containment controls retain a legitimate
  edge-free boundary and reject self-nesting or untyped nodes. The canonical
  package and commit gates passed, and the exact Compass no-program projection
  now says Release Targets and Plan rather than Program and Wave. This resolves
  the source-level admission defect; immutable installed browser and scorer
  parity remain required before closing the release-proof defect.
