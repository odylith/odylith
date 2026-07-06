- Bug ID: CB-219

- Status: Open

- Created: 2026-07-06

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A confirmed greenfield create could fail or degrade after user confirmation when human-authored Product Intent Markdown included structural setup prose such as component equipment lists. The first-path projection treated setup details as product actions, repeated noncanonical prose into rendered artifacts, malformed external-system language, and could surface repairable post-confirm package quality failures to the user.

- Impact: Users who accepted a product intent could still see post-confirm create fail or receive malformed governed artifacts instead of a completed project package.

- Components Affected: domain-intelligence

- Environment(s): Odylith maintainer source-local greenfield create path, consumer repro /Users/freedom/mock/elec-tree, July 2026.

- Detected By: Operator-reported ArborCell post-confirm failure and source-local repro.

- Failure Signature: greenfield rendered package repeats noncanonical prose; setup equipment sentence projected as review/action copy; external system rendered as current Lab measurement tools; result copy rendered as proven it.

- Trigger Path: odylith greenfield create --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1

- Ownership: Domain Intelligence confirmed-intent custody, first-path semantic projection, project-brief next-step projection, Mermaid/public-copy quality.

- Timeline: 2026-07-06 reproduced ArborCell source-local create failure; traced repeated prose to Radar/rendered package projections; fixed setup-step custody, proof predicate normalization, terminal review outcome selection, Mermaid quality text merging, and highlighted confirmation Next step UX.

- Blast Radius: Any greenfield create whose accepted intent includes narrative structure, setup lists, review-terminal outcomes, proof predicates, or heavily edited confirmation Markdown.

- SLO/SLA Impact: Post-confirm user-facing success invariant violated; repairable package quality failures escaped instead of converging internally.

- Data Risk: Governed records could contain contaminated product facts or misleading proof boundaries, but no private data exposure was observed.

- Security/Compliance: No direct security exposure; weak custody can still affect compliance-grade evidence quality for regulated or scientific projects.

- Invariant Violated: After confirmation, generated governance artifacts must project from canonical typed product facts rather than rendered or noncanonical Markdown prose.

- Root Cause: First-path and public-copy projection owners lacked a strict setup/action distinction for accepted Markdown. Structural sentences using verbs such as uses/includes/contains could enter material action, readiness, scope, and Radar projections. Visible-result selection also let earlier publish/record/review fragments outrank terminal proof or review outcomes.

- Solution: Add shared supporting-setup step classification, skip setup rows in first-path action/capability/readiness projections, reset carried subjects per sentence, normalize proof predicates and external-system language from typed facts, prefer terminal delivery/review outcomes, merge Mermaid quality fragments, and render confirmation next steps as highlighted command bullets.

- Rollback/Forward Fix: Forward fix only; rollback would restore post-confirm failure and contaminated artifact risk.

- Verification: Exact ArborCell source-local create now succeeds and scans zero hits for the original repeated setup phrase, current Lab measurement tools, proven it, and review the oxygen-poor root zone. Focused regressions passed: ArborCell setup custody, generic setup sentence custody, ArborCell package report, confirmation UX, targeted slop tests, py_compile, git diff --check, and broader greenfield live/confirmed-text/diagram slice 58 passed.

- Prevention: Keep setup/equipment prose out of action truth at the shared first-path role owner; make public surfaces project from typed first-path facts; keep package-quality and generated-copy gates pinned with source and package-level regressions.

- Agent Guardrails: Do not patch generated projects or hand-polish rendered artifacts. Trace contamination to parser/projection owners and prove with real post-confirm create plus package report.

- Preflight Checks: Search existing B-142, CB-209, CB-215, and greenfield package-quality records before changing post-confirm projection or repair behavior.

- Regression Tests Added: tests/unit/runtime/test_greenfield_live_simulation_regressions.py covers ArborCell setup custody, generic setup-sentence custody, and ArborCell package report; tests/unit/runtime/test_greenfield_cli_paths.py pins highlighted Confirm/Edit/Reject next-step UX.

- Monitoring Updates: Future matrix campaigns should include setup-heavy confirmed-intent edits, terminal review outcomes, proof predicates, and document-derived equipment/protocol lists.

- Version/Build: source-local v0.1.15 development branch 2026/freedom/v0.1.15

- Config/Flags: Provider-free source-local create; release 0.0.1.

- Customer Comms: Internal platform stability work; no public customer notice until release proof passes.

- Related Incidents/Bugs: B-142, CB-209, CB-215

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_first_path_step_roles.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_project_brief.py
- src/odylith/runtime/common/mermaid_text.py
- tests/unit/runtime/test_greenfield_live_simulation_regressions.py
