- Bug ID: CB-262

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Intermittent

- Type: Test

- Description: A full runtime suite run completed collection and then produced a late failure cascade after pytest reported FileNotFoundError for the repository working directory, even though the workspace was present immediately afterward. The result cannot be used as a reliable release signal until the offending test-isolation path is identified.

- Impact: The complete runtime regression suite can produce a misleading cascade and delay trustworthy release validation.

- Components Affected: tooling-quality

- Environment(s): Odylith product repo, Hatch Python 3.13 full runtime suite

- Detected By: Full runtime validation

- Failure Signature: pytest ends with FileNotFoundError for the repository working directory after late test failures; workspace exists after process exit.

- Trigger Path: Hatch full runtime suite

- Ownership: Runtime test isolation and quality gate

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: All maintainer changes that require full runtime proof.

- SLO/SLA Impact: Blocks reliable release-gate interpretation and increases validation latency.

- Data Risk: No product-data exposure; risk is false regression attribution.

- Security/Compliance: Safety and quality posture: the release gate is unreliable until test isolation is restored; no direct privacy or access-control impact.

- Invariant Violated: A full runtime validation run must preserve or restore its working directory and report attributable failures.

- Root Cause: At least one full-suite test or fixture leaves pytest unable to resolve the repository working directory; the reproduced session ends with that error while the workspace exists afterward.

- Solution: Isolate the first working-directory transition failure, add a regression, then rerun the complete suite from a clean worktree.

- Rollback/Forward Fix: Forward fix the test harness; do not accept cascade output as release proof.

- Verification: Run the complete runtime suite from a clean worktree with stable working-directory assertions and no late FileNotFoundError.

- Prevention: Require tests that change cwd to restore it under failure and run broad validation in an isolated worktree.

- Agent Guardrails: Do not label a late full-suite cascade as a product regression without reproducing its first attributable failure.

- Preflight Checks: Verify workspace exists, inspect stale pytest cache, and reproduce with a clean isolated run.

- Related Incidents/Bugs: CB-261

- GitHub Status: confirmed

- Public Response: pending

- Code References: - tests/unit/runtime
