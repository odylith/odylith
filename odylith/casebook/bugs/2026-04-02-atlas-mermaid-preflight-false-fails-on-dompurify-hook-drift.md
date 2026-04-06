- Bug ID: CB-042

- Status: Closed

- Created: 2026-04-02

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: `odylith atlas auto-update` could falsely report a valid Mermaid
  diagram as a syntax failure when the Node-side preflight parser hit the
  Mermaid `DOMPurify.addHook` runtime drift path. The render path itself still
  worked in Chromium, but the preflight stopped first and blocked Atlas
  refresh, strict sync, and benchmark-governance upkeep on a false failure.

- Impact: Maintainers could lose Atlas freshness and fail governance sync even
  when the diagram source was valid, which made benchmark-maintenance work
  look flaky and undermined trust in the Atlas preflight contract.

- Components Affected: `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`, Atlas refresh
  validation contract, strict sync lane.

- Environment(s): Odylith product repo maintainer lane,
  `odylith atlas auto-update --repo-root . --from-git-working-tree --fail-on-stale`,
  `odylith atlas auto-update --repo-root . --all-stale --fail-on-stale`,
  `odylith sync --repo-root . --force --impact-mode selective`.

- Root Cause: Atlas auto-update treated every structured Mermaid preflight
  failure as a real syntax failure. For some valid diagrams, the Node parser
  raised a Mermaid runtime error (`DOMPurify.addHook is not a function`) that
  did not reproduce in the browser-backed render path. The preflight had no
  fallback lane, so the false failure aborted refresh before the trustworthy
  browser execution path could run.

- Solution: Keep fail-fast preflight for real syntax errors, but when the
  preflight hits the known DOMPurify contract-drift signature, rerun
  validation in browser-backed scratch mode with temporary SVG and PNG outputs
  outside the repo. That preserves zero contamination of tracked Atlas assets
  while keeping valid diagrams refreshable.

- Verification: `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_auto_update_mermaid_diagrams.py -k
  'validate_diagrams_batch_falls_back_to_browser_scratch_mode_on_dompurify_runtime_error
  or atlas_auto_update_fails_fast_on_mermaid_validation_error or
  mermaid_worker_request_raises_validation_error_for_structured_response'`
  passed with `3 passed`; `./.odylith/bin/odylith atlas auto-update --repo-root
  . --all-stale --fail-on-stale` passed with all `24` diagrams fresh;
  `./.odylith/bin/odylith sync --repo-root . --force --impact-mode selective`
  passed.

- Prevention: Treat runtime-only Mermaid preflight failures as toolchain drift
  until the browser-backed path confirms they are real syntax failures. Atlas
  preflight must stay fail-fast on source errors but fail-safe against known
  parser-environment mismatches.

- Detected By: Maintainer benchmark-governance follow-through on 2026-04-02
  while refreshing Atlas after the proof and diagnostic benchmark contract
  changes.

- Failure Signature: `atlas auto-update failed` with `D-024 failed:
  odylith/atlas/source/...` and detail `DOMPurify.addHook is not a function`,
  even though the same diagram rendered successfully in the browser-backed
  Mermaid CLI path.

- Trigger Path: `odylith atlas auto-update --repo-root . --from-git-working-tree
  --fail-on-stale`, `odylith atlas auto-update --repo-root . --all-stale
  --fail-on-stale`, `odylith sync --repo-root . --force --impact-mode
  selective`.

- Ownership: Atlas refresh contract, Mermaid preflight reliability, strict
  sync trust.

- Timeline: Benchmark-governance upkeep exposed a sync blocker after the Atlas
  preflight rejected a valid benchmark-proof diagram on the DOMPurify hook
  path. The fix kept the fast syntax preflight for real parse failures but
  added a browser-backed scratch fallback for the known runtime-drift path,
  which restored full Atlas refresh and strict sync.

- Blast Radius: Atlas freshness, sync reliability, maintainer release hygiene,
  and any workstream that depends on fresh diagrams during governance upkeep.

- SLO/SLA Impact: Medium maintainer friction. The bug did not corrupt source
  truth, but it blocked refresh and sync until repaired.

- Data Risk: Low direct data risk; moderate governance-staleness risk because
  valid diagrams could remain marked stale and the Atlas surface could lag the
  source truth.

- Security/Compliance: None beyond the requirement that fallback validation
  must not leak scratch outputs into tracked repo paths.

- Invariant Violated: Atlas preflight must distinguish real Mermaid syntax
  failure from parser-environment drift and must not block valid diagrams on a
  false syntax verdict.

- Workaround: Bypass the failing preflight by reproducing the same diagram in
  a manual browser-backed Mermaid CLI render, then refresh the full stale set
  once the product fix lands.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not weaken `--fail-on-stale` or disable Atlas
  preflight to dodge this class of bug. Preserve the strict gate and repair
  the false-failure path instead.

- Preflight Checks: Reproduce the failure on the diagram source, confirm the
  detail string, and verify whether the browser-backed `renderMermaid` path
  succeeds before changing Atlas refresh behavior.

- Regression Tests Added:
  `test_validate_diagrams_batch_falls_back_to_browser_scratch_mode_on_dompurify_runtime_error`

- Monitoring Updates: Atlas auto-update now prints when it degrades from the
  Node parser into browser-backed scratch validation, so maintainers can see
  that the strict gate stayed active while the false-failure path was avoided.

- Residual Risk: The fallback currently keys off the known DOMPurify hook
  signature. Future Mermaid parser-environment drifts may need to be added if
  upstream behavior changes again.

- Related Incidents/Bugs: `CB-038` improved Atlas refresh diagnostics and fast
  syntax preflight, but this bug showed that the new preflight still needed a
  trustworthy fallback for parser-runtime drift.

- Version/Build: `v0.1.7` maintainer hardening on 2026-04-02.

- Config/Flags: `--fail-on-stale`, `--all-stale`, `--from-git-working-tree`

- Customer Comms: Maintainer docs should describe Atlas preflight as strict on
  real syntax errors and resilient to known parser-runtime drift. The product
  should not imply that every preflight failure is repo-author error.

- Code References: `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `tests/unit/runtime/test_auto_update_mermaid_diagrams.py`

- Runbook References: `odylith/registry/source/components/atlas/CURRENT_SPEC.md`,
  `odylith/skills/delivery-governance-surface-ops/SKILL.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
