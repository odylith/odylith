- Bug ID: CB-097

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Atlas freshness and `--all-stale` selection could mark diagrams
  stale when watched files only changed mtime and not content. A checkout,
  touch, or generated-file rewrite could therefore keep diagrams in `Needs
  Update` even when the watched implementation truth and the Mermaid render
  source had not materially changed.

- Impact: Atlas could advertise false freshness debt, fail the stale gate on
  non-semantic churn, and force operators back through a review loop that did
  not correspond to real topology drift.

- Components Affected: `src/odylith/runtime/common/diagram_freshness.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  Atlas freshness contract, and `B-080`.

- Environment(s): Odylith product-repo maintainer mode, Atlas catalog refresh,
  `odylith atlas auto-update --all-stale`, and any workflow that rewrites or
  checks out watched files without changing their content.

- Root Cause: The freshness contract compared watched-path mtimes against the
  Mermaid source mtime and persisted only the review date. Atlas had no
  durable content fingerprint for watched implementation state, and it treated
  timestamp churn as equivalent to real source movement.

- Solution: Persist content fingerprints for watched paths and render-semantic
  Mermaid source, compare those fingerprints during stale selection and Atlas
  render, and ignore review-comment-only Mermaid churn when deciding whether
  SVG and PNG assets need regeneration.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_diagram_freshness.py tests/unit/runtime/test_render_mermaid_catalog.py`
    passed (`35 passed`)
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_diagram_freshness.py`
    passed (`152 passed`)

- Prevention: Atlas freshness must compare authoritative watched-path content
  and render-semantic diagram source, not raw mtimes.

- Detected By: Atlas continued to show `Needs Update` after watched-plan and
  watched-index churn that did not require a real diagram re-render.

- Failure Signature: Atlas shows a stale reason tied to a watched path whose
  bytes have not changed since the last honest review, and `--all-stale`
  selects the diagram again anyway.

- Trigger Path: 1. Rewrite or check out a watched file without a semantic
  change. 2. Leave the diagram source and rendered assets unchanged. 3. Run an
  Atlas refresh or open Atlas under the old mtime contract.

- Ownership: Atlas freshness selection and watched-path evidence contract.

- Timeline: This became obvious while driving Atlas below one second and
  finding that the stale set was dominated by timestamp churn rather than real
  topology change.

- Blast Radius: Any Atlas diagram that watches active plan, Radar, Registry, or
  code paths with mtime churn but no content drift.

- SLO/SLA Impact: No outage, but a direct operator-trust and latency failure on
  the Atlas review loop.

- Data Risk: Low source-corruption risk; medium freshness-truth risk.

- Security/Compliance: None directly.

- Invariant Violated: Atlas must not declare a diagram stale unless the watched
  implementation truth or review-age contract actually changed.

- Workaround: Re-run Atlas sync until the catalog is refreshed again. That
  clears the symptom but not the contract flaw.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not use filesystem mtimes as the freshness contract when
  content fingerprints are cheap and available.

- Preflight Checks: Inspect
  `src/odylith/runtime/common/diagram_freshness.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`, and
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`.

- Regression Tests Added: `tests/unit/runtime/test_diagram_freshness.py`,
  `tests/unit/runtime/test_auto_update_mermaid_diagrams.py`,
  `tests/unit/runtime/test_render_mermaid_catalog.py`.

- Monitoring Updates: Watch for any Atlas stale selection where the stored and
  current watched-path content fingerprints still match.

- Residual Risk: Real watched-path content changes still require review, and
  genuine Mermaid source edits still pay the render lane.

- Related Incidents/Bugs:
  [2026-04-09-atlas-auto-update-plan-can-claim-render-work-for-review-only-sync.md](2026-04-09-atlas-auto-update-plan-can-claim-render-work-for-review-only-sync.md)
  [2026-04-09-atlas-real-render-lane-still-misses-sub-second-bar-after-review-only-fast-path.md](2026-04-09-atlas-real-render-lane-still-misses-sub-second-bar-after-review-only-fast-path.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Atlas refresh and `--all-stale` paths; no special flag
  required.

- Customer Comms: Tell operators Atlas now keeps the stale signal strict
  without confusing content-stable watch churn for real architecture drift.

- Code References: `src/odylith/runtime/common/diagram_freshness.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`

- Runbook References: `odylith/registry/source/components/atlas/CURRENT_SPEC.md`,
  `odylith/technical-plans/done/2026-04/2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md`

- Fix Commit/PR: Pending.
