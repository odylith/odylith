- Bug ID: CB-258

- Status: Open

- Created: 2026-07-16

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The installed failed-subset replay of laundry-room-outage-queue clears the CB-257 scope-boundary gate but rejects the complete pre-confirm package because its domain-expert matrix lens counts three of four declared domain terms. The package renders all governed artifacts and reaches no confirmation or write.

- Impact: A usable consumer laundry utility request still cannot reach the CONFIRM, EDIT, REJECT rail.

- Components Affected: domain-intelligence

- Environment(s): Fresh installed 0.1.15 failed-subset replay built from the current 2026/freedom/v0.1.15 working tree.

- Detected By: Exact installed CB-257 replay after pre-confirm package rendering.

- Failure Signature: domain.term.coverage.too.low.expected.least.found: domain term coverage too low: expected at least 4, found 3

- Trigger Path: laundry-room-outage-queue through bin/greenfield-matrix-campaign using the generated failed-subset packet.

- Ownership: Greenfield pre-confirm domain-term selection, rendered artifact evidence, and installed quality scoring.

- Timeline: Captured 2026-07-16 through `odylith bug capture`.

- Blast Radius: Prompts with several concrete domain terms when one term is omitted from rendered evidence despite a coherent first path.

- SLO/SLA Impact: Pre-confirm compiler rejects a consumer request after the full package has been compiled, delaying deterministic confirmation.

- Data Risk: No confirmation, governed write, or transaction commit occurred.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: A concrete user-supplied domain term needed to prove the accepted first path must survive the pre-confirm artifact package or be repaired before the user sees a failure.

- Root Cause: The request's shared-laundry-room context preceded the narrow first path. Thin-prompt title recovery named the product `Tenant Utility Workspace`, and the semantic first path retained dryer queue, water leak, and test cycle but not laundry room. The term appeared only in the unscored accepted-project record. The strict matrix intentionally excludes that record and correctly rejected the three-of-four public-artifact result.

- Solution: When a command request has only role-qualified generic product language such as `tenant utility` and a concrete place context, retain that place in the canonical title. Explicit command titles with their own domain nouns continue to win over contextual replacement.

- Verification: Named prompt-source regressions prove shared-laundry context is retained and explicit titles such as `volunteer scheduling tool` remain intact. The final fresh installed failed-subset replay passed `laundry-room-outage-queue` at 10/10: all four declared domain terms appear on scored public artifacts, the commit-only transaction committed under rollback guard, and no quality issue remained. Resume discovery.

- Prevention: Treat concrete prompt context as semantic input, not disposable request framing. Test the exact required-term set against staged public artifacts and protect explicit product titles from contextual replacement.

- Agent Guardrails: Do not reduce the required term count, waive the domain-expert lens, or move term repair after CONFIRM.

- Preflight Checks: The compiled package must preserve every declared domain term across the required staged evidence surfaces before a confirmation rail is emitted.

- Regression Tests Added: `test_contextual_title_preserves_shared_laundry_room_for_generic_utility_request` proves the retained context; `test_contextual_title_keeps_explicit_command_titles` prevents title loss. The fresh installed failed-subset replay passed.

- Monitoring Updates: Track the domain-term coverage fingerprint and exact declared-versus-rendered term set in Compass.

- Version/Build: 0.1.15 local distribution rebuilt from the current working tree.

- Config/Flags: GREENFIELD_MATRIX_FAILED_SUBSET_MAX_WORKERS=1; generated failed-subset packet; quiet progress.

- Customer Comms: No customer communication; the compiler failed before confirmation and no governed records were written.

- Related Incidents/Bugs: CB-256, CB-257

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_request_context_title.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py
- scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_matrix_quality_scoring.py

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
