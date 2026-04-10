- Bug ID: CB-099

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Atlas's persistent Mermaid worker could fail genuine SVG and PNG
  render jobs after the first persistent-page optimization wave. The worker
  loaded the Mermaid CLI shell page and then assumed the `mermaid` and
  `mermaid-zenuml` browser globals already existed, which made render jobs die
  with `Cannot read properties of undefined (reading 'registerExternalDiagrams')`.

- Impact: Any Atlas refresh that genuinely needed Mermaid asset regeneration
  could fail instead of repairing the diagram set.

- Components Affected: `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`,
  `src/odylith/runtime/surfaces/mermaid_worker_session.py`,
  Atlas Mermaid render path, and `B-080`.

- Environment(s): Atlas refreshes that classify at least one diagram as
  render-needed and route through the persistent Node/Chromium Mermaid worker.

- Root Cause: The persistent page reused `dist/index.html` for `elkLayouts`,
  but it never loaded Mermaid's IIFE bundles that create the browser globals
  required by `registerExternalDiagrams(...)`.

- Solution: Bootstrap the persistent page explicitly with Mermaid and Zenuml
  script tags before the first render, then reuse the initialized page and
  render counter across jobs.

- Verification:
  - `PYTHONPATH=src python3 - <<'PY' ... _MermaidWorkerSession(...).render_one(...) ... PY`
    now writes both SVG and PNG successfully for `D-001`
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_diagram_freshness.py tests/unit/runtime/test_render_mermaid_catalog.py`
    passed (`35 passed`)

- Prevention: Persistent browser reuse must bootstrap the same browser globals
  that the one-shot Mermaid CLI path depends on before assuming the page is
  render-ready.

- Detected By: Real Atlas render profiling after the persistent-page worker
  rewrite began failing on first genuine render jobs.

- Failure Signature: Mermaid worker render returns a structured Atlas failure
  with detail `Cannot read properties of undefined (reading 'registerExternalDiagrams')`.

- Trigger Path: 1. Route Atlas render through the persistent worker. 2. Reuse a
  page that has `elkLayouts` but not Mermaid globals. 3. Attempt the first real
  render.

- Ownership: Atlas Mermaid worker bootstrap and browser-runtime reuse.

- Timeline: This surfaced during the second deeper Atlas latency cut, after the
  earlier content-fingerprint work had already made review-only refresh fast.

- Blast Radius: Any genuine Atlas Mermaid asset regeneration.

- SLO/SLA Impact: No outage, but a hard correctness failure in the Atlas repair
  path.

- Data Risk: Low source-corruption risk; medium refresh-blocking risk.

- Security/Compliance: None directly.

- Invariant Violated: Atlas must not break genuine Mermaid render jobs while
  optimizing the hot path.

- Workaround: Fall back to one-shot Mermaid CLI renders. That keeps the system
  limping but misses the intended hot path.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When reusing browser pages, bootstrap the full runtime
  contract explicitly instead of inferring global availability from a shell
  document.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs` and
  `src/odylith/runtime/surfaces/mermaid_worker_session.py`.

- Regression Tests Added: Focused Atlas Python regressions remain in
  `tests/unit/runtime/test_auto_update_mermaid_diagrams.py`; live worker proof
  uses the direct render benchmark above.

- Monitoring Updates: Watch for any Atlas render failure whose detail mentions
  missing Mermaid browser globals or `registerExternalDiagrams`.

- Residual Risk: The worker now renders correctly again, but the first real
  render still pays Chromium startup and remains slower than the Atlas
  review-only lane.

- Related Incidents/Bugs:
  [2026-04-09-atlas-auto-update-plan-can-claim-render-work-for-review-only-sync.md](2026-04-09-atlas-auto-update-plan-can-claim-render-work-for-review-only-sync.md)
  [2026-04-09-atlas-real-render-lane-still-misses-sub-second-bar-after-review-only-fast-path.md](2026-04-09-atlas-real-render-lane-still-misses-sub-second-bar-after-review-only-fast-path.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Atlas Mermaid worker path; no special flag required.

- Customer Comms: Tell operators Atlas render jobs work again on the persistent
  worker path, but the first real render still has a separate startup-latency
  issue being tracked.

- Code References: `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`,
  `src/odylith/runtime/surfaces/mermaid_worker_session.py`

- Runbook References: `odylith/registry/source/components/atlas/CURRENT_SPEC.md`,
  `odylith/technical-plans/done/2026-04/2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md`

- Fix Commit/PR: Pending.
