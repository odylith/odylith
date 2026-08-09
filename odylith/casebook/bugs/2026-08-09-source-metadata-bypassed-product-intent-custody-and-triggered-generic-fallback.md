- Bug ID: CB-324

- Status: FixedPendingRelease

- Created: 2026-08-09

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Source-only evidence was stripped by prompt_intent_source, then re-admitted by the raw-text grounded-human-action helper. Materialization generated an Untitled Project with Representative user and accepted product details instead of asking for the missing first complete task.

- Impact: A first-time user can receive a polished but invented project package when they supplied evidence without product intent.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith 0.1.15 source-local Greenfield pre-confirm materialization

- Detected By: Full confirmed-intent recovery regression and direct typed-intent inspection

- Failure Signature: Source evidence, Source repository, or Repository description containing an actor action produced generic product truth instead of GreenfieldClarificationRequired.

- Trigger Path: Materialize a Greenfield prompt whose only content is a source-metadata field with a plausible actor action.

- Ownership: Greenfield Product Intent evidence-custody and materiality boundary

- Timeline: Captured 2026-08-09 through `odylith bug capture`.

- Blast Radius: Any Greenfield request containing source metadata without a separate product-intent statement

- SLO/SLA Impact: Violates the pre-confirm evidence custody and consumer-utility gate; blocks release readiness.

- Data Risk: No repository write occurred in the direct repro, but an invented package could be staged for confirmation.

- Security/Compliance: Security posture: no direct exposure was observed. Compliance and policy posture: provenance and review trust are compromised when evidence metadata is promoted into accepted product facts.

- Invariant Violated: Evidence metadata may inform interpretation but cannot become product truth; materially missing first-path intent must produce one focused no-write question.

- Root Cause: The shared grounded-human-action helper scanned raw evidence instead of the product-only evidence view already owned by product_intent_source_text.

- Solution: Run grounded human-action detection only over product_intent_source_text and prove source-only prompts ask one first-task question without staging.

- Rollback/Forward Fix: Forward fix only; post-confirm repair remains forbidden.

- Verification: The source-only and prompt-plus-source focused pack passed 6 tests. The complete confirmed-intent recovery file passed 100 tests, including all three previously failing source-metadata labels, and the disclosed retired holdout passed all 124 regressions. Each source-only case raises one first-task question and leaves no Greenfield staging directory.

- Prevention: All materiality helpers must consume the same product-only evidence view before scoring title, actor, or path sufficiency.

- Agent Guardrails: Never repair missing Product Intent by generating generic product facts from source metadata.

- Preflight Checks: Require zero staging for source-only evidence and full prompt-plus-source preservation before release.

- Regression Tests Added: tests/unit/runtime/test_greenfield_confirmed_intent_recovery.py::test_source_metadata_only_requires_a_first_path_question

- Monitoring Updates: Release proof should report source-only evidence custody failures separately from ordinary material clarification.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15

- Related Incidents/Bugs: CB-303

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
