- Bug ID: CB-348

- Status: InProgress

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

- Timeline: Captured 2026-09-27 through `odylith bug capture`. The V39 exact one-case replay proved the callable-selection repair reached the installed proposal command, then failed because the discovery-tier direct path omitted the required `--candidate-file` contract. V40 commit `ce11ecc03` removed that stale route, built and passed clean-install smoke, and reached the canonical host-native candidate flow. The exact replay then failed closed after 180.317 seconds because discovery runs did not allocate the private proof-capture case that release runs use; the evaluator therefore compared the sealed host receipt with empty retained observations and reported 39 derivative custody issues plus one separate scoring issue. The scoring issue treated deliberately optional discovery browser proof as a required unscored dimension even though release proof still requires the full browser matrix. This stale-evaluator recurrence is linked to CB-347.

- Blast Radius: All discovery-tier matrix runs that use the direct installed proposal path without host candidate argv

- SLO/SLA Impact: Release qualification stops on the first case before the 90/120/150 advisory timing or quality floors can be measured

- Data Risk: No product writes occurred; the case stopped before proposal commit and retained failure evidence was written externally

- Security/Compliance: No security or compliance exposure observed; failure is fail-closed

- Invariant Violated: Every selected campaign case must execute one real proposal command or fail with an explicit provider or transaction outcome, never pass a callable in place of process evidence

- Root Cause: Conditional-expression precedence in `_run_case` constructed one outer lambda whose false branch returned another lambda; the direct proposal path therefore yielded a function object. After that was repaired, the exact replay exposed that discovery tiers still selected an obsolete direct `greenfield propose` path even though all successful proposals now require one host-authored candidate from `candidate-contract`. After that stale path was removed, V40 exposed two harness ownership gaps: `run_matrix` created `RetainedEvidenceCase` only when a persistent evidence directory was requested, while every host-native discovery case requires the same private candidate and reviewer observations for immediate custody evaluation; and quality scoring correctly marked optional discovery browser proof unscored but then treated every automated unscored dimension as a blocker without excluding an explicitly not-required browser dimension.

- Solution: Remove the obsolete direct proposal route from campaign execution. Every campaign tier must pass the canonical host-candidate command, and matrix execution must fail closed before product work when that command is absent. Keep `_run_greenfield_propose` only as the candidate-file-bound commit step inside the host-candidate flow. Allocate an ephemeral proof-capture case when no external evidence directory is requested so discovery can evaluate the exact host candidate and independent reviewer receipts; preserve explicitly requested external diagnostic evidence and the immutable release-evidence path. Treat an unattempted browser dimension as non-blocking only when browser proof is explicitly not required; release proof remains fail-closed on missing browser evidence.

- Rollback/Forward Fix: Forward fix only; the immutable V38 distribution remains rejected and must be rebuilt after proof.

- Verification: Focused regression proves every campaign tier carries the canonical host-candidate command, missing custody fails before product execution, and discovery tiers capture host-authoring plus private reviewer evidence ephemerally when no evidence destination is requested. Quality scoring passes an otherwise complete discovery case with browser proof explicitly not required while still failing an otherwise identical release case with browser proof required and not attempted. The focused custody/scoring suite passes 274 tests, and the full Greenfield install/release suite passes 1,230 tests. A rebuilt immutable distribution must still complete the exact one-case replay before the seven-case replay resumes. V40 evidence is retained at `/Users/freedom/.codex/odylith-greenfield-public-v40-one-case-evidence.x1oSXH`; it is a falsification, not release proof.

- Prevention: Ban conditional expressions that return lambdas in release execution ownership, do not retain a direct proposal fallback after the candidate-file contract becomes mandatory, and keep proof capture separate from proof publication. Assert every campaign tier reaches proposal only through the canonical host-candidate flow and has the private observations required to evaluate that flow.

- Agent Guardrails: Do not retry a packaged provider campaign after a deterministic harness exception; capture evidence, fix the owner, rebuild, and replay the exact failed case.

- Preflight Checks: Run the no-host-candidate regression and compileall before any provider-backed campaign.

- Regression Tests Added: `test_run_matrix_rejects_missing_host_native_argv_before_product_execution`, `test_run_case_invokes_only_host_candidate_runner_with_process_evidence`, `test_discovery_campaign_commands_carry_canonical_host_candidate_argv`, `test_discovery_uses_ephemeral_case_proof_without_publishing_release_evidence`, optional-versus-required browser-score regressions, clarification host-custody regressions, and candidate-file enforcement.

- Version/Build: 0.1.15 V38 commit 6200e214f48b635ede7cb7153752f63a1fecbefa

- Config/Flags: failed-subset tier; one worker; direct installed proposal path; browser proof skipped by discovery contract

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_matrix_journey.py
