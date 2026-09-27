- Bug ID: CB-348

- Status: Open

- Created: 2026-09-27

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The V38 packaged failed-subset campaign aborted before semantic evaluation because the no-host-candidate proposal branch returned a lambda function instead of invoking the installed Greenfield proposal command.

- Impact: Blocks provider-backed Greenfield release qualification and prevents the seven-case public regression replay from reaching semantic or UX evaluation.

- Components Affected: release

- Environment(s): Odylith product-repo maintainer lane, immutable V38 distribution 0.1.15, failed-subset discovery tier

- Detected By: Provider-backed V38 failed-subset replay against the immutable packaged distribution

- Failure Signature: case-execution-exception: 'function' object has no attribute 'returncode'

- Trigger Path: make greenfield-matrix-campaign with GREENFIELD_MATRIX_FAILED_CASE_FILES and no host_candidate_argv

- Ownership: Greenfield release matrix journey and preconfirm campaign harness

- Timeline: Captured 2026-09-27 through `odylith bug capture`.

- Blast Radius: All discovery-tier matrix runs that use the direct installed proposal path without host candidate argv

- SLO/SLA Impact: Release qualification stops on the first case before the 90/120/150 advisory timing or quality floors can be measured

- Data Risk: No product writes occurred; the case stopped before proposal commit and retained failure evidence was written externally

- Security/Compliance: No security or compliance exposure observed; failure is fail-closed

- Invariant Violated: Every selected campaign case must execute one real proposal command or fail with an explicit provider or transaction outcome, never pass a callable in place of process evidence

- Root Cause: Conditional-expression precedence in _run_case constructed one outer lambda whose false branch returned another lambda; the direct proposal path therefore yielded a function object.

- Solution: Select the host-native or direct proposal callable explicitly before invoking run_compiled_greenfield_journey, with a regression covering the empty host_candidate_argv path.

- Rollback/Forward Fix: Forward fix only; the immutable V38 distribution remains rejected and must be rebuilt after proof.

- Verification: Focused regression must prove direct and host-native callable branches; fast release harness suites must pass; a rebuilt immutable distribution must complete the exact one-case replay before the seven-case replay resumes.

- Prevention: Ban conditional expressions that return lambdas in release execution ownership; assert the journey receives process-like proposal evidence on both branches.

- Agent Guardrails: Do not retry a packaged provider campaign after a deterministic harness exception; capture evidence, fix the owner, rebuild, and replay the exact failed case.

- Preflight Checks: Run the no-host-candidate regression and compileall before any provider-backed campaign.

- Version/Build: 0.1.15 V38 commit 6200e214f48b635ede7cb7153752f63a1fecbefa

- Config/Flags: failed-subset tier; one worker; direct installed proposal path; browser proof skipped by discovery contract

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_matrix_journey.py
