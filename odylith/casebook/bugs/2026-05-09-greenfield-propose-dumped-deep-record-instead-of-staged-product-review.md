- Bug ID: CB-194

- Status: FixedPendingRelease

- Created: 2026-05-09

- Severity: P1

- Reproducibility: Always

- Type: OperatorUX

- Description: Greenfield propose dumped deep record instead of staged product review

- Impact: Empty-repo greenfield users saw a long internal proposal dump before any clarification point, making it unclear when records would be written and letting tool terminology crowd out product requirements.

- Components Affected: domain-intelligence

- Environment(s): Odylith v0.1.15 consumer greenfield propose/create flow in docs-only or empty repos.

- Detected By: Maintainer reproduced from a greenfield proposal transcript where project-shaping output exposed the deep accepted record too early.

- Failure Signature: greenfield propose emitted apply-ready JSON, mode/provider metadata, project-first blueprint, workstream domain intelligence, and write/apply internals as one large default text payload.

- Trigger Path: odylith greenfield propose --repo-root . --prompt '<greenfield project prompt>'

- Ownership: domain-intelligence proposal rendering, greenfield CLI UX, show guidance, and managed greenfield skills

- Timeline: Captured 2026-05-09 through `odylith bug capture`.

- Blast Radius: All empty/thin consumer repos using greenfield propose before confirmation; especially regulated or domain-specific prompts where prompt intent must stay front-and-center.

- SLO/SLA Impact: Onboarding trust and time-to-correct-greenfield-review regressed; users could not tell preview, clarification, and write phases apart.

- Data Risk: No production data mutation, but consumer governance source could be written from misunderstood confirmation because preview text over-implied internal readiness.

- Security/Compliance: Security posture assessed: no direct secret or production-data exposure, but regulated prompts can bury compliance, approval, operator-boundary, and irreversible-action decisions under internal topology language; preview must keep those decisions explicit before writes.

- Invariant Violated: Propose must be a no-write, product-first clarification gate; confirmed create/apply is the first point where validated records are written.

- Root Cause: format_proposal_text rendered the canonical apply-ready object for host_reasoned_proposal_request, while show/guidance still primed users with Odylith surface names and _intent_title truncated meaningful trailing prompt terms. A legacy repair guard also used multi-lookahead regex over full Radar records, which turned surface refresh into CPU-bound regex work during final validation. A follow-on refresh exposed a separate lane-boundary flaw: consumer-only repair logic could run in the Odylith product repo, and standalone Registry rendering could prefer a stale runtime snapshot over source manifest truth.

- Solution: Split default propose text into four gates: interpretation, clarification, proposal preview, and next action; keep full depth in --format json/apply; make the closeout explicitly tell operators to either apply as-is, revise Gate 2 choices, or export full JSON before apply; remove surface-first show/guidance wording; preserve meaningful trailing domain terms in titles; delete stale legacy Atlas artifacts during consumer repair; replace the repair guard with linear token-family checks so refresh latency stays bounded; make legacy consumer repair return immediately for Odylith product-repo shape; make standalone Registry rendering use source manifest truth without loading stale runtime snapshots.

- Rollback/Forward Fix: Forward fix only; restore old renderer only by explicit rollback if preview gate loses required product requirements, while JSON/apply remains deep.

- Verification: 100 focused greenfield/show/bundle/registry/migration tests pass after the migration-observer update; release migration gate for 0.1.15 reports zero blocked migrations and zero ungated lifecycle paths; casebook validation passes across 193 records; plan-workstream binding and plan traceability validators pass; Atlas render reports 44 fresh diagrams and zero stale; Radar refresh completes in 3.4s after replacing the regex guard and leaves the product Registry at 30 source components with no external mock components; live propose repro emits compact product-first gates, an explicit apply/revise/export next-action choice, and no Radar/Registry/Atlas/Compass terms; headless browser matrix passes Radar, Registry, Atlas, Casebook, and Compass on desktop and mobile with zero console warnings/errors and zero horizontal overflow.

- Prevention: Tests assert compact default text, explicit next-action guidance, ASCII `--format json` export command, no provider/mode/shared-artifact chatter, no workstream-domain-intelligence dump, preserved prompt title terms, product-first show guidance, consumer legacy repair isolation from product repos, and standalone Registry source-manifest precedence.

- Agent Guardrails: When a greenfield UX complaint includes a transcript, test the exact prompt through text and JSON modes; do not judge quality only from schema or apply success.

- Preflight Checks: Before release, run greenfield text/JSON repros, greenfield profile tests, source-guard tests, release migration gate, and browser surface refresh proof.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_text_is_compact_product_preview_before_confirmed_write; tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_title_preserves_meaningful_trailing_domain_terms; tests/unit/runtime/test_render_registry_dashboard.py::test_render_registry_dashboard_standalone_uses_source_manifest_not_runtime_snapshot; updated show, bundle, and source-guard assertions.

- Monitoring Updates: Release migration observer markers added for guidance-and-skills, operator-cli-contracts, public-docs-and-release-guidance, browser-surfaces, and install-managed-assets.

- Version/Build: v0.1.15 maintainer source-local

- Related Incidents/Bugs: CB-191

- Code References: - src/odylith/runtime/domain_intelligence/proposal_rendering.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals.py
- src/odylith/runtime/analysis_engine/show_capabilities.py
