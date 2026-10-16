- Bug ID: CB-311

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P2

- Reproducibility: Always

- Type: Test

- Description: The clean v0.1.15 validation run completed all 6,235 pytest cases, then failed guidance portability because B-142 and B-143 retained maintainer-local .venv/bin/python commands in operator-visible verification notes.

- Impact: Release validation cannot complete and copied verification commands assume a repository-specific virtualenv layout.

- Components Affected: radar

- Environment(s): Odylith product repo maintainer lane at commit f3439e1cb

- Detected By: make dev-validate guidance portability gate

- Failure Signature: guidance portability FAILED: replace .venv/bin/python with a portable launcher or python -m form

- Trigger Path: ODYLITH_NO_BROWSER=1 make dev-validate

- Ownership: Radar governed source and guidance portability validation

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: B-142 and B-143 verification history; v0.1.15 release validation

- SLO/SLA Impact: Blocks release proof; runtime transaction latency and availability are unaffected.

- Data Risk: Governed source bytes remain intact; the risk is operators copying an environment-specific command that fails outside this checkout.

- Security/Compliance: The defect does not cross a security, privacy, accessibility, or safety boundary; the portability policy remains fail-closed and prevents release.

- Invariant Violated: Governed operator guidance must use portable executable forms.

- Root Cause: Historical proof notes recorded the local virtualenv executable instead of the portable active Python launcher.

- Solution: Mechanically replace the local interpreter path with python while preserving commands and recorded outcomes, refresh Radar and Casebook projections, and rerun guidance portability plus the remaining canonical validators.

- Rollback/Forward Fix: Forward fix only; do not weaken the portability gate.

- Verification: The canonical `ODYLITH_NO_BROWSER=1 make dev-validate` run completed all 6,235 pytest cases with 6,234 passes and one intentional skip before the portability gate exposed this defect. After the source correction, `odylith validate guidance-portability --repo-root .` passed across 327 maintained guidance files with zero findings; Radar refresh passed with topology quality 100/100; backlog contract validation passed for 145 workstreams; Casebook source validation passed for 307 records; and `git diff --check` passed.

- Prevention: Keep the existing portability gate release-blocking and record proof commands in portable python -m form.

- Agent Guardrails: Never paste a maintainer-local .venv interpreter path into governed human-visible records.

- Preflight Checks: Search touched governed records for .venv/bin/python before commit.

- Regression Tests Added: Existing guidance portability validator is the regression gate.

- Version/Build: 0.1.15 / f3439e1cb

- GitHub Status: fixed_pending_release

- Public Response: closed
