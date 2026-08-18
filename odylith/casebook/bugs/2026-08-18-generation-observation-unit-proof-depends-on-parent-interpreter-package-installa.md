- Bug ID: CB-346

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The after-image tamper characterization launches a child Python process from an isolated temporary repository without binding the Odylith source package. Under the canonical global interpreter the child cannot import odylith.runtime, so the test fails before exercising generation integrity. Delivery risk is a false canonical validation failure; production installed-runtime isolation remains correct.

- Impact: Canonical dev validation cannot prove generation after-image tamper rejection unless the parent interpreter happens to have this source checkout installed.

- Components Affected: domain-intelligence

- Environment(s): Odylith maintainer source-local validation under global Python 3.13 with child cwd set to an isolated temporary repository

- Detected By: Untouched make dev-validate shard 3, then exact global-interpreter reproduction

- Failure Signature: Child Python raises ModuleNotFoundError: No module named odylith.runtime before generation observation runs

- Trigger Path: python3 -m pytest -q tests/unit/install/test_greenfield_commit_recovery_proof.py::test_installed_generation_observation_rejects_tampered_after_image

- Ownership: Greenfield release proof test environment custody

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Generation after-image tamper characterization and canonical maintainer validation

- SLO/SLA Impact: Blocks release validation; no production generation readback impact

- Data Risk: No repository or generation data is mutated by the import failure; the intended tamper is confined to a temporary test repository.

- Security/Compliance: Security posture is unchanged because production execution still strips PYTHONPATH. Compliance, privacy, accessibility, and safety posture are unaffected because the fix is confined to a source-level unit subprocess.

- Invariant Violated: A source-level unit proof must declare its source package import path and must not inherit correctness from an incidental parent installation.

- Root Cause: The unit subprocess uses sys.executable from a temporary cwd without an explicit source import path, while canonical make dev-validate uses a global interpreter that does not install the worktree package.

- Solution: Bind the absolute worktree src directory only in this source-level unit subprocess environment; leave production installed-release isolation unchanged.

- Rollback/Forward Fix: Forward-fix the test harness environment only; do not weaken installed runtime isolation.

- Verification: Run the exact node and the full Greenfield commit recovery proof file under global python3.

- Prevention: Subprocess unit proofs must explicitly bind either installed-runtime custody or source-tree custody and test the chosen boundary.

- Agent Guardrails: Do not add PYTHONPATH to production installed release execution; scope it to this unit subprocess.

- Preflight Checks: Confirm the exact failure under global python3 and retain existing tests that production release environments strip PYTHONPATH.

- Regression Tests Added: tests/unit/install/test_greenfield_commit_recovery_proof.py::test_installed_generation_observation_rejects_tampered_after_image

- Related Incidents/Bugs: CB-305

- Code References: - tests/unit/install/test_greenfield_commit_recovery_proof.py
