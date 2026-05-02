- Bug ID: CB-138

- Type: DashboardRenderingRegression








- Status: FixedPendingRelease

- Created: 2026-04-29

- Severity: P2

- Reproducibility: Consistent


- Description: A large consumer Casebook rendered under Odylith 0.1.11 shows the Bug Cases selector clipping long titles, summaries, and status chips at the list-panel edge while the detail pane remains readable. Casebook source validation passes for 156 records, so the failure is in the generated dashboard layout rather than malformed bug markdown.

- Impact: Operators scanning a large Casebook cannot reliably read recent bug titles, summaries, or long status labels from the selector list, making valid bug memory look broken and slowing triage.

- Components Affected: casebook

- Environment(s): Consumer pinned_release posture with Odylith pinned=active=0.1.11; generated Casebook has 156 records and source validation passes.

- Detected By: User screenshot captured on 2026-04-29 plus read-only inspection of the generated Casebook surface and shipped product renderer.

- Failure Signature: Bug Cases list rows visibly clip long selector content at the right edge; latest rows show truncated title and summary text while listMeta reports Visible: 156.

- Trigger Path: Open generated odylith/casebook/casebook.html, or the tooling-shell Casebook tab, in a consumer repo with long bug titles or long status labels; select recent high-index bug rows.

- Ownership: Odylith Casebook dashboard renderer and shipped Casebook bundle assets.

- Timeline: 2026-04-29: user supplied screenshot of the broken consumer Casebook; read-only diagnosis confirmed Odylith 0.1.11 and passing Casebook source validation.

- Blast Radius: Consumer repos on the shipped Casebook dashboard with large payloads or long bug titles/status labels; the product repo source and bundle mirror carry the same renderer contract.

- SLO/SLA Impact: No service SLO outage, but maintainer triage and bug-memory scan reliability are degraded.

- Data Risk: No source data loss observed; source validation passed for 156 records. Risk is visual omission or misread of bug evidence.

- Security/Compliance: No direct security or compliance exposure observed; delayed bug triage could defer governance follow-up.

- Invariant Violated: Generated governance surfaces must keep long records readable and responsive; valid Casebook source must not render as clipped or unrecoverable selector rows.

- Workaround: Open Source markdown from the detail pane or inspect the bug markdown directly; this bypasses the broken selector but does not restore dashboard scanning.

- Root Cause: Suspected frontend layout regression in the Casebook renderer: the narrow selector column and row/meta wrapping constraints do not preserve readability for long title, summary, and status-chip content.

- Solution: Forward-fix the product renderer so selector titles, summaries, and status chips wrap or clamp intentionally without hidden horizontal clipping, keep the detail pane under a single page-level `h1` by rendering selected bug titles as `h2`, then rematerialize consumer generated assets through the supported upgrade or refresh path.

- Rollback/Forward Fix: Forward fix in the Odylith product repo; do not patch consumer generated Casebook assets by hand.

- Verification: Fixed on the v0.1.12 branch with Casebook selector wrapping, status-chip wrapping, and detail-heading semantics. Focused proof covers desktop and compact long-row stress with `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_casebook_list_layout_browser.py`; broad proof covers the full runtime browser matrix across shell, Casebook, Radar, Registry, Atlas, Compass, intervention visibility, and onboarding tests.

- Prevention: Keep Casebook browser layout tests covering large payloads, long titles, long summaries, long status chips, and normal plus narrow/mobile viewport states.

- Agent Guardrails: For consumer Odylith UI regressions, diagnose the consumer repo read-only, capture maintainer-ready product truth, and avoid hand-editing consumer generated assets or running refresh/repair as the fix.

- Preflight Checks: Inspect src/odylith/runtime/surfaces/render_casebook_dashboard.py, src/odylith/bundle/assets/odylith/casebook/casebook.html, src/odylith/bundle/assets/odylith/casebook/casebook-app.v1.js, and existing surface browser layout tests before patching.

- Regression Tests Added: `tests/integration/runtime/test_casebook_list_layout_browser.py` mutates a real Casebook row with long title, summary, status chips, and one long unbroken token in desktop and compact contexts, then fails on hidden horizontal overflow, row-edge escaping, or non-wrapping metadata. Existing Casebook browser layout and navigation tests now anchor on `.hero-title` so selected bug titles can render as detail-level headings without creating ambiguous page-level `h1` matches.

- Monitoring Updates: None.

- Version/Build: Odylith pinned/active 0.1.11 consumer install; product repo source contains the matching Casebook renderer and bundle mirror.

- Config/Flags: No special flags; generated Casebook surface reports Visible: 156.

- Customer Comms: No external customer communication needed for this maintainer-local finding.

- Related Incidents/Bugs: No exact duplicate found by product Casebook query; related surface layout history includes CB-080 and CB-120.

- Code References: - src/odylith/runtime/surfaces/render_casebook_dashboard.py
- src/odylith/bundle/assets/odylith/casebook/casebook.html
- tests/integration/runtime/test_surface_browser_layout_audit.py
- tests/unit/runtime/test_render_casebook_dashboard.py
