- Bug ID: CB-266

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The pre-confirm candidate artifact stored product facts, source spans, and supporting evidence in one JSON envelope. Although the compiler read typed facts correctly, that mixed custody surface made raw evidence appear to be staged product truth and left future re-entry points able to misuse it.

- Impact: Reviewers and downstream code cannot reliably distinguish typed candidate truth from raw supporting evidence inside the staged candidate artifact.

- Components Affected: odylith

- Environment(s): Product-repo maintainer source-local pre-confirm compiler

- Detected By: Adversarial architecture review after CB-265 reproduction

- Failure Signature: candidate-intent.json contained source_evidence and custody_ledger alongside flattened product facts

- Trigger Path: greenfield propose with prompt or edit evidence

- Ownership: Greenfield typed intent materialization and custody ledger

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Every prompt-first pre-confirm proposal and any consumer reading staged candidate JSON

- SLO/SLA Impact: No post-confirm product failure, but the candidate custody boundary was ambiguous before confirmation.

- Data Risk: No external data exposure; untrusted evidence could be mistaken for product truth.

- Security/Compliance: No security, compliance, policy, privacy, accessibility, or safety impact.

- Invariant Violated: A typed candidate artifact must contain typed product facts only; raw source spans and supporting evidence belong to an explicit evidence ledger.

- Root Cause: write_structured_confirmed_intent_file flattened the full custody envelope and product facts into candidate-intent.json.

- Solution: Write candidate-intent.json as a typed-only schema with product facts, materiality gate, and product facts hash; write source_evidence and custody_ledger to candidate-evidence.v1.json; normalize first paths again at accepted-memory and handoff boundaries.

- Rollback/Forward Fix: Forward fix only; the artifact is pre-confirm staging and no committed governed records require rollback.

- Verification: Dedicated candidate custody, transaction authority, commit-only boundary, and patterned create regressions pass after the split.

- Prevention: Treat artifact filenames as custody boundaries, keep compiler inputs typed-only, and add regression checks that candidate-intent.json has no source evidence.

- Agent Guardrails: Never place source_evidence, supporting evidence, or raw prompt text in typed candidate artifacts, transaction inputs, or generated governance surfaces.

- Preflight Checks: Validate typed candidate and evidence ledger separation before allowing the Confirm rail.

- Regression Tests Added: test_source_spans_exclude_smallest_version_editorial_loop_from_product_claims now proves candidate JSON excludes source evidence while candidate-evidence.v1.json retains it.

- Monitoring Updates: No runtime monitor; unit and integration custody contracts cover the boundary.

- Version/Build: Unreleased 2026/freedom/v0.1.15 checkpoint

- Config/Flags: None

- Customer Comms: Not required; defect was found before release.

- Related Incidents/Bugs: CB-265, CB-264

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py
- src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- src/odylith/runtime/domain_intelligence/proposal_memory.py
- src/odylith/runtime/domain_intelligence/greenfield_experience.py
