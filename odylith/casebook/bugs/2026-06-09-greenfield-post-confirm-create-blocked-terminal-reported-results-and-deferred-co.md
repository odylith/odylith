- Bug ID: CB-204

- Status: Open

- Created: 2026-06-09

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A confirmed greenfield create could fail after confirmation when the accepted first path ended in a reported, saved, viewable result and the component set included a deferred service. The platform incorrectly missed the visible-result event, clipped the First Path Sequence tail, and required a rendered Registry spec for a deferred component.

- Impact: Operators could confirm a valid Product Intent Confirmation and still receive internal repair required blockers instead of governed project records.

- Components Affected: odylith

- Environment(s): Odylith product repo and installed local release v0.1.15 greenfield create path

- Detected By: User transcript from confirmed greenfield create in a fresh consumer repo

- Failure Signature: greenfield proposal confirmed completion failed: semantic_model first_path_contract has no visible-result event; confirmed Atlas flowchart First Path Sequence omits the tail of the accepted first path; prewrite Registry package missing rendered active component spec for deferred service

- Trigger Path: odylith greenfield create --repo-root . --prompt <confirmed request> --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1

- Ownership: Odylith greenfield domain-intelligence and post-confirm completion gates

- Timeline: Captured 2026-06-09 through `odylith bug capture`.

- Blast Radius: Any greenfield confirmed intent whose terminal result uses report/save/find/compare/viewable language or contains deferred components

- SLO/SLA Impact: Post-confirm completion could fail instead of finishing the governed project package under the agreed 60 second budget

- Data Risk: No user data loss; the confirmed intent file remains saved, but governed project records are not written

- Security/Compliance: Policy and compliance posture: the failure blocks creation of reviewable governance records that carry privacy, accessibility, safety, and release-boundary obligations; no direct secret exposure was observed.

- Invariant Violated: After confirmation, Odylith must either create the full governed project package or fail only on a real user-correctable issue; deferred scope must not be treated as active Registry scope

- Root Cause: Visible-result detection and apply-semantic fallback did not recognize generic reported/saved/viewable terminal result language; Atlas terminal labels clipped proof-critical tail terms; rendered Registry scope alignment included deferred components.

- Solution: Expanded generic visible-result/action grammar, preserved semantic terminal outcome in First Path Sequence terminal/proof labels, routed result/history terminal steps generically, and aligned rendered spec checks with first-release scope semantics.

- Rollback/Forward Fix: Forward fix only; weakening gates would hide real partial-create failures.

- Verification: Exact transcript-shaped repro now completes in 13.002s with 4 backlog items, 4 rendered components, 6 diagrams, validation passed, detailed visible result preserved, and First Path Sequence tail terms present.

- Prevention: Keep subprocess and integration regressions for reported/saved/viewable terminal results and deferred Registry scope alignment.

- Agent Guardrails: Do not patch consumer repos for Odylith platform failures; reproduce against product source and fix generic parser, renderer, or gate contracts.

- Preflight Checks: Run greenfield create regression for terminal reported/saved results and deferred components before release.

- Regression Tests Added: tests/integration/runtime/test_greenfield_create_performance.py::test_greenfield_create_preserves_reported_saved_result_tail_and_deferred_scope_under_sixty_seconds; tests/unit/runtime/test_greenfield_general_artifact_quality.py::test_rendered_registry_scope_alignment_ignores_deferred_components

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_first_path_fragments.py
- src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py
- src/odylith/runtime/domain_intelligence/greenfield_preconfirm_semantic_alignment.py
