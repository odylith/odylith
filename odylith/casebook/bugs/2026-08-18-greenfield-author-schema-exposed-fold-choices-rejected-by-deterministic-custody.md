- Bug ID: CB-347

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: The candidate-adjudication provider schema offered every locked workflow candidate against every visible-output and state target. The post-provider verifier accepted only pairs sharing exact source custody and preserving independent material relations, so a one-shot development author could select a schema-valid but deterministically impossible fold.

- Impact: Fresh two-stage development evidence stops before a segment is written, consuming a one-shot assignment and preventing attributable convergence evidence.

- Components Affected: domain-intelligence

- Environment(s): Detached source-local Greenfield development cohort at 7d37417cd5d0ccb01e26041d01f932b169e53643

- Detected By: Fresh revision-bound 24-case two-stage development cohort

- Failure Signature: ValueError: Semantic workflow fold lacks shared exact source custody after provider-accepted structured author output

- Trigger Path: greenfield_semantic_host_execution.author_development_case -> select_semantic_source_claims -> require_semantic_source_candidate_adjudication

- Ownership: Semantic source-candidate adjudication schema and deterministic fold custody

- Timeline: Observed on 2026-08-18 after two clean cohort cases; the third assignment failed once and the wave stopped immediately

- Blast Radius: Any prompt with multiple locked workflow, state, or visible-output candidates whose exact citations differ

- SLO/SLA Impact: Release-blocking development evidence failure; no customer write occurred

- Data Risk: No customer-data risk; failed evidence is preserved as failed and cannot be retried or reused

- Security/Compliance: Fail-closed custody held, but the provider contract exposed choices the safety verifier could never accept

- Invariant Violated: Every provider-exposed semantic decision must be admissible under the same deterministic custody contract that validates it

- Workaround: None; do not retry or weaken custody

- Root Cause: Provider schema constructed a Cartesian product of workflow candidates and all fold targets while deterministic validation applied pair-specific exact-source and material-relation rules later

- Solution: Use one typed fold-eligibility owner for both provider schema construction and deterministic validation; expose retain plus only admissible candidate-target pairs

- Rollback/Forward Fix: Forward-fix the pre-confirm authoring contract and invalidate stale evidence plans and packets

- Verification: Positive shared-custody fold, negative citation-mismatch fold, negative independent-material-relation fold, authority/transaction/post-confirm/host/evaluator proof, deterministic laws, then fresh assignments

- Prevention: Treat schema-verifier option-set divergence as a contract regression and structurally prove provider options are a subset of deterministic acceptance

- Agent Guardrails: Do not add prompt rules, phrase vocabulary, regex inference, retries, or weakened citation custody; remove impossible choices at the typed contract boundary

- Preflight Checks: Frozen tree; fresh protocol identities; old plan and segments retained only as failed historical evidence; replacement holdout unopened

- Regression Tests Added: Provider schema exposes only exact-custody fold pairs and removes pairs that would discard an independent material relation

- Related Incidents/Bugs: CB-334

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_semantic_source_candidate_adjudication.py
- tests/unit/runtime/test_greenfield_semantic_source_candidate_adjudication.py
