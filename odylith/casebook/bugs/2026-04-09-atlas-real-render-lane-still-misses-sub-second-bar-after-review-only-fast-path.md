- Bug ID: CB-100

- Status: Open

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Atlas now clears review-only freshness debt quickly, but a
  genuine Mermaid render still misses the sub-second target. The current
  repaired persistent worker renders a real diagram correctly, yet the first
  end-to-end render still takes about `2.38s` because Chromium startup and page
  bootstrap dominate the path.

- Impact: Atlas feels fast again when it only needs to review watched-path
  changes, but real diagram source edits still pay a multi-second first-render
  tax.

- Components Affected: `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`,
  `src/odylith/runtime/surfaces/mermaid_worker_session.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  Mermaid CLI integration, and `B-080`.

- Environment(s): Odylith product-repo maintainer mode, any Atlas sync that
  truly requires Mermaid SVG and PNG regeneration.

- Root Cause: The hot path now skips false renders, but genuine renders still
  start a fresh Chromium-backed Mermaid worker per CLI invocation. The browser
  startup cost dominates the first job.

- Solution: Pending. Likely candidates are a reusable cross-command Mermaid
  render daemon or another contract that can preserve a warm browser process
  without weakening validation or feature coverage. Follow-on workstream:
  `B-081`.

- Verification:
  - `PYTHONPATH=src python3 - <<'PY' ... _MermaidWorkerSession(...).render_one(...) ... PY`
    measured about `2.38s` for a real `D-001` render while writing valid SVG
    and PNG outputs

- Prevention: Atlas performance claims must distinguish review-only freshness
  refresh from genuine Mermaid asset generation until the first-render startup
  tax is gone.

- Detected By: Post-fix profiling after the content-fingerprint and review-only
  fast path work cleared the stale-review loop under one second.

- Failure Signature: Review-only Atlas refresh is sub-second, but any run with
  a real Mermaid render still spends multiple seconds before the first asset is
  written.

- Trigger Path: 1. Make a real Mermaid source change. 2. Force Atlas to render
  SVG and PNG. 3. Pay one fresh browser startup for that CLI invocation.

- Ownership: Atlas Mermaid render-latency budget.

- Timeline: This is the remaining honest latency gap after the 2026-04-09
  Atlas freshness and review-only optimization wave.

- Blast Radius: Any Atlas diagram source edit that genuinely changes render
  output.

- SLO/SLA Impact: No outage, but Atlas still misses the stated sub-second bar
  for the first real render lane.

- Data Risk: None directly.

- Security/Compliance: None directly.

- Invariant Violated: Atlas should stay under one second even when a selected
  diagram genuinely needs regeneration.

- Workaround: Avoid unnecessary renders through the new fingerprint contract.
  That helps, but it does not solve the first-render budget.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not confuse review-only sub-second refresh with true
  render-lane sub-second proof.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`,
  `src/odylith/runtime/surfaces/mermaid_worker_session.py`, and the Atlas
  render benchmarks.

- Regression Tests Added: None yet beyond the live worker benchmark; the next
  wave likely needs benchmark-style guardrails.

- Monitoring Updates: Track first-render latency separately from review-only
  Atlas refresh latency.

- Residual Risk: Operators can still feel a cold-start penalty when a real
  Mermaid source change lands.

- Related Incidents/Bugs:
  [2026-04-09-atlas-watch-freshness-can-mark-diagrams-stale-on-mtime-only-churn.md](2026-04-09-atlas-watch-freshness-can-mark-diagrams-stale-on-mtime-only-churn.md)
  [2026-04-09-atlas-persistent-mermaid-worker-bootstrap-can-fail-real-render-jobs.md](2026-04-09-atlas-persistent-mermaid-worker-bootstrap-can-fail-real-render-jobs.md)
  [2026-04-10-atlas-cold-real-render-daemon-reuse-and-sub-second-first-render-budget.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-10-atlas-cold-real-render-daemon-reuse-and-sub-second-first-render-budget.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Atlas Mermaid render path; no special flag required.

- Customer Comms: Tell operators Atlas no longer wastes time on false stale
  renders, but genuine source-change regeneration still has a tracked startup
  latency issue.

- Code References: `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`,
  `src/odylith/runtime/surfaces/mermaid_worker_session.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`

- Runbook References: `odylith/registry/source/components/atlas/CURRENT_SPEC.md`,
  `odylith/technical-plans/done/2026-04/2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md`

- Fix Commit/PR: Pending.
