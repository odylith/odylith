- Bug ID: CB-231

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The ProductCreateTransaction completeness gate accepted a compiled commit result preview without the collections required by terminal reporting. The sealed write then committed, and the CLI raised KeyError while formatting the success result.

- Impact: A consumer can see a failed create command after governed records have already committed, undermining deterministic post-confirm success and retry safety. Delivery and operational risk: release automation can classify a committed package as failed and repeat the action.

- Components Affected: domain-intelligence

- Environment(s): 0.1.15 source-local ProductCreateTransaction commit path on branch 2026/freedom/v0.1.15

- Detected By: Independent adversarial post-confirm call-graph and malformed-receipt probe

- Failure Signature: Officially receipted transaction writes sealed bytes, then greenfield_cli_output indexes a missing backlog, components, or diagrams key and raises KeyError

- Trigger Path: Compile or load a transaction whose commit_result_preview lacks a CLI reporting collection, then run greenfield create with confirm

- Ownership: Pre-confirm compiled commit-result contract and post-confirm reporting boundary

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Any malformed or incompatible transaction receipt accepted before the commit-only write

- SLO/SLA Impact: No latency breach; success reporting can fail after an otherwise successful transaction

- Data Risk: Governed writes can be durable while the caller receives an error and may retry unnecessarily

- Security/Compliance: Security: no credential exposure observed. Compliance and policy: the command outcome no longer faithfully reflects persisted governed state. Privacy, accessibility, and safety: no direct impact observed.

- Invariant Violated: Every reporting dependency must be validated before confirmation so successful sealed writes always produce a valid success receipt

- Root Cause: The preview validator checked mode, dashboard status, and quality debt but omitted the backlog, components, and diagrams collections unconditionally used by the CLI reporter

- Solution: Require list-shaped compiled reporting collections before transaction sealing and reject incomplete previews pre-confirm

- Rollback/Forward Fix: Forward fix in the current B-142 checkpoint

- Verification: Missing or non-list reporting collections fail package validation before write; valid receipts report without post-confirm parsing. The final current-source 13-case compile/create matrix also passed in 698.98 seconds; fresh installed proof remains required.

- Prevention: Treat all post-confirm reporter inputs as sealed transaction contract fields and add malformed-envelope tests

- Agent Guardrails: Do not assume a final result preview is complete because its dashboard proof is present

- Preflight Checks: Run malformed commit-result envelope tests before packaged commit-only proof

- Regression Tests Added: test_commit_result_preview_requires_every_text_report_collection; test_commit_result_preview_rejects_non_list_text_report_collection; test_compiled_package_rejects_incomplete_text_report_before_confirmation

- Monitoring Updates: Release proof must assert a complete success receipt after every committed case

- Version/Build: 0.1.15 source-local branch before final packaged proof

- Config/Flags: Default commit-only transaction path

- Customer Comms: None; caught before release

- Related Incidents/Bugs: CB-229

- Fixed In: Pending 0.1.15 release proof

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prewrite_commit_result.py
- src/odylith/runtime/domain_intelligence/greenfield_cli_output.py
- tests/unit/runtime/test_greenfield_prewrite_commit_result.py
