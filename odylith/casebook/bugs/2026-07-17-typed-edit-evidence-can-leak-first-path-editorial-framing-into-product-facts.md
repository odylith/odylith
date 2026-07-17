- Bug ID: CB-265

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A patterned greenfield proposal correctly classified the terminal editorial loop as supporting evidence, but copied the raw first-path edit into the typed prompt field before normalization. The prompt field is persisted with product facts, so the phrase 'smallest version of the whole product' leaked into candidate product truth despite being excluded from the accepted first path.

- Impact: Pre-confirm transactions can contain editorial evidence as typed product truth, contaminating governed artifacts before the user sees Confirm.

- Components Affected: odylith

- Environment(s): Product-repo maintainer source-local integration create

- Detected By: Full greenfield integration matrix

- Failure Signature: test_pattern_greenfield_create_blocks_placeholder_and_clause_drift_under_thirty_seconds asserted that smallest version of the whole product appeared in written product truth

- Trigger Path: greenfield propose with structured edit evidence, then hash-bound create

- Ownership: Greenfield typed intent materialization and custody ledger

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Any structured first-path edit containing terminal proof-loop framing

- SLO/SLA Impact: No post-confirm failure occurred, but pre-confirm artifact quality and custody were violated.

- Data Risk: No external data exposure; typed product truth was semantically contaminated.

- Security/Compliance: No security, compliance, policy, privacy, accessibility, or safety impact.

- Invariant Violated: Supporting evidence and editorial proof framing must never enter typed product facts or compiled governed artifacts.

- Root Cause: The edit merge assigned raw overrides[first_path] to prompt before normalize_confirmed_intent cleaned the first path; prompt_first_path_source then selected the terminal editorial sentence.

- Solution: After typed normalization, bind prompt to the accepted normalized first_path whenever an explicit first-path edit is present; expose the first-path cleaner for both parser and mapping ingestion.

- Rollback/Forward Fix: Forward fix only; the defect exists before confirmation and needs no rollback of committed product records.

- Verification: Focused envelope, transaction-authority, commit-only boundary, and patterned create checks pass after the typed-boundary fix.

- Prevention: Route all first-path fields, including prompt aliases, through one accepted-first-path normalizer before product facts are sealed.

- Agent Guardrails: Do not infer product truth from raw edit evidence after typed normalization; retain raw text only in source evidence spans.

- Preflight Checks: Run structured edit-evidence custody regression before accepting precompiled create transactions.

- Regression Tests Added: test_source_spans_exclude_smallest_version_editorial_loop_from_product_claims now covers mapping normalization and materialized candidate prompt custody.

- Monitoring Updates: No runtime monitor; the custody regression is covered by integration and unit contract tests.

- Version/Build: Unreleased 2026/freedom/v0.1.15 checkpoint

- Config/Flags: None

- Customer Comms: Not required; defect was found before release.

- Related Incidents/Bugs: CB-264

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py
