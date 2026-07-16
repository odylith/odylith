- Bug ID: CB-259

- Status: Open

- Created: 2026-07-16

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The resumed installed 240-case campaign rejects cli-extension-release-notes before confirmation because greenfield propose asks for a first-path clarification instead of returning the ProductCreateTransaction receipt. No package artifacts or governed consumer writes are produced.

- Impact: A concrete extension-publisher request cannot reach the CONFIRM, EDIT, REJECT rail.

- Components Affected: domain-intelligence

- Environment(s): Fresh installed 0.1.15 240-case discovery campaign built from the current 2026/freedom/v0.1.15 branch.

- Detected By: Installed high-variance campaign fail-fast cluster.

- Failure Signature: greenfield.propose.did.not.return.productcreatetransaction.hash.transaction.file; the installed JSON response is mode clarification_required with the first-path question.

- Trigger Path: cli-extension-release-notes from tests/fixtures/greenfield-volume/developer-data-security.v1.json through bin/greenfield-matrix-campaign.

- Ownership: Greenfield pre-confirm materiality gate and ProductCreateTransaction receipt emission.

- Timeline: Captured 2026-07-16 through `odylith bug capture`.

- Blast Radius: Any concise prompt with one explicit actor-action path that the pre-confirm materiality gate reduces to one parsed step.

- SLO/SLA Impact: Pre-confirm compilation fails before the user can confirm a creation-ready package.

- Data Risk: No confirmation, transaction commit, or governed consumer write occurred.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: Every unambiguous consumer request must return a complete pre-confirm transaction receipt. A focused material question is reserved for a missing or genuinely ambiguous first path, not a clear single-step actor-action path.

- Root Cause: Three independent pre-confirm defects masked the receipt. First, materialize_prompt_intent_hypothesis checked materiality before it built the typed hypothesis. The gate accepted only two or more parsed first-path steps, so "extension publishers can assemble release notes" was treated as missing even though the shared prompt source had recovered a concrete actor, action, and outcome. Once that gate was corrected, command-led title recovery fell through to a generic word parser, which chose "Tool for Extension Publishers" and produced duplicate project-brief state prose. The pre-confirm copy-quality gate correctly rejected that malformed package. The bounded action-object extractor also initially treated the non-completing verb "use" as a title-bearing action, so a later EDIT could derive "For Release Notes Workspace" from the same vague request.

- Fix: Accept a single parsed step only when the shared prompt source has a recognizable human role, a concrete leading action, and a non-generic action. For command-led requests that wrap a bare generic product container, recover the action object before the generic title fallback. Share the non-completing-action test between the materiality and title paths, so "use" neither bypasses clarification nor becomes a derived title. Retain clarification for noun phrases, multiple operating paths, non-human actors, and generic "use a tool" requests. Retain the pre-confirm duplicate-copy quality gate.

- Verification: Added source and CLI regressions for release-note assembly, a declarative actor-action path, named-product preservation, non-human actors, generic-use rejection, and generic-use EDIT recovery. The fresh focused transaction/CLI run passes 10 tests. Run the full Greenfield suites, rebuild the distribution, replay the exact failed subset, then resume discovery.

- Prevention: Validate explicit single-step actor-action prompts through both source and installed propose paths before broad campaign execution. Do not infer an empty path solely from parsed step count.

- Agent Guardrails: Do not synthesize a receipt in the matrix harness, relax receipt validation, or move transaction compilation after CONFIRM.

- Preflight Checks: Installed greenfield propose must return a transaction hash and file before matrix create begins.

- Regression Tests Added: test_greenfield_transaction_intent_authority covers the release-notes and declarative actor-action paths plus generic-use clarification; test_greenfield_need_product_focus covers command-container title recovery and named-product preservation; test_greenfield_cli_paths covers the actual pre-confirm receipt and a generic-use EDIT that must compile without a malformed title. A fresh installed failed-subset replay remains required.

- Monitoring Updates: Track the missing-receipt fingerprint and installed module-loading failures in Compass.

- Version/Build: 0.1.15 local distribution built from the current working tree.

- Config/Flags: GREENFIELD_MATRIX_DEEP_VOLUME_MAX_WORKERS=4; stop after one failure cluster; high-variance stressors required.

- Customer Comms: No customer communication; no transaction or governed record was written.

- Related Incidents/Bugs: CB-256, CB-257, CB-258

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
