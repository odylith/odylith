- Bug ID: CB-098

- Status: Closed

- Created: 2026-04-09

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: `odylith atlas auto-update` could print a mutation plan and
  apparent timeline that included Mermaid SVG and PNG regeneration for every
  impacted diagram even when Atlas had already proven the run was review-only.
  In that state the command still only needed to rewrite freshness metadata and
  rerender Atlas, but the operator-facing plan implied more expensive work.

- Impact: Atlas review-only refreshes looked slower and heavier than they
  really were, which made the sub-second path harder to trust and obscured the
  difference between review debt and genuine Mermaid render debt.

- Components Affected: `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  Atlas CLI plan output, and `B-080`.

- Environment(s): Atlas dry runs, repeated identical syncs, and `--all-stale`
  refreshes where the selected diagrams already have current Mermaid assets.

- Root Cause: The plan printer was driven from the impacted diagram set before
  Atlas classified which diagrams actually needed a Mermaid render.

- Solution: Classify impacted diagrams first, expose render-needed versus
  review-only counts, and omit the SVG/PNG render step from the plan when all
  selected diagrams are review-only.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_auto_update_mermaid_diagrams.py`
    passed

- Prevention: Atlas timing and mutation plans must describe the classified
  work, not the worst-case work.

- Detected By: User review of Atlas refresh timing versus the actual review-only
  command path.

- Failure Signature: A dry run or repeated identical sync prints a Mermaid
  render step and output asset paths even though the same run would skip
  `_render_diagrams_batch(...)`.

- Trigger Path: 1. Select stale or changed diagrams. 2. Let Atlas discover that
  the render fingerprints already match and the outputs are current. 3. Print
  the plan before using that classification.

- Ownership: Atlas auto-update plan and operator-facing timing disclosure.

- Timeline: This showed up immediately after the content-fingerprint freshness
  work made review-only Atlas refreshes cheap enough that the remaining
  misleading plan output stood out.

- Blast Radius: Any review-only Atlas sync.

- SLO/SLA Impact: No correctness outage, but operator timing disclosure was
  misleading on the main Atlas maintenance loop.

- Data Risk: None directly.

- Security/Compliance: None directly.

- Invariant Violated: Atlas must not claim Mermaid asset regeneration when the
  run is only updating review and freshness metadata.

- Workaround: Ignore the plan and trust the later execution output. That is not
  a good product contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Distinguish review-only diagram refresh from render-needed
  refresh before presenting execution plans or elapsed-time claims.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py` around plan
  building and render classification.

- Regression Tests Added: `tests/unit/runtime/test_auto_update_mermaid_diagrams.py`.

- Monitoring Updates: Watch for any Atlas plan that advertises Mermaid render
  paths while the classified render-needed count is zero.

- Residual Risk: Real source-change renders still need their own performance
  work and remain tracked separately.

- Related Incidents/Bugs:
  [2026-04-09-atlas-watch-freshness-can-mark-diagrams-stale-on-mtime-only-churn.md](2026-04-09-atlas-watch-freshness-can-mark-diagrams-stale-on-mtime-only-churn.md)
  [2026-04-09-atlas-persistent-mermaid-worker-bootstrap-can-fail-real-render-jobs.md](2026-04-09-atlas-persistent-mermaid-worker-bootstrap-can-fail-real-render-jobs.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Atlas dry-run and sync path; no special flag required.

- Customer Comms: Tell operators Atlas now distinguishes review-only refreshes
  from render-needed work in the command plan itself.

- Code References: `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`

- Runbook References: `odylith/registry/source/components/atlas/CURRENT_SPEC.md`,
  `odylith/technical-plans/done/2026-04/2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md`

- Fix Commit/PR: Pending.
