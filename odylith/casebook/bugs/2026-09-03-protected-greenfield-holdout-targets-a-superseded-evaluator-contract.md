- Bug ID: CB-328

- Status: Open

- Created: 2026-09-03

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The approved revision-6 protected package passes its standalone offline validator after the two independent-review P1 corrections, but it cannot enter the current one-shot release gate: it declares intent-authoring v2 and a custom protected-holdout schema, while the frozen candidate uses intent-authoring v19 and the release harness requires evaluation-splits v4 plus final-holdout v4 structural annotations. Its eight cases also cannot satisfy the frozen minimum of four observations in each of three complexity-band and model-profile slices.

- Impact: The final Greenfield release claim cannot be proved from this package; attempting the release command would claim and then interrupt the one-shot ledger before any product case executes.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Detached maintainer candidate 4ee36701 with immutable dist-v14; approved protected revision-6 package; release evaluator contract v4; authoring contract v19

- Detected By: Pure evaluate_frozen_evaluation_contract preflight after independently reviewed package corrections and before ledger claim

- Failure Signature: Preflight reports the wrong manifest and holdout versions, missing tracked corpus and v4 annotations, no declared profiles or frozen floors, no loadable matrix cases, and absent complexity/evidence-format/model-profile coverage; the final-run ledger remains absent.

- Trigger Path: Evaluate the corrected protected package manifest.json and protected-evaluation-corpus.json with scripts/release/greenfield_evaluation_contract.py against the package root.

- Ownership: Protected Greenfield evaluation authoring, structural annotation, and release-gate handoff

- Timeline: 2026-09-03: user approved protected access; two reviewed P1s were corrected without product changes; standalone offline validation passed 8/8; current release-contract preflight then proved the package is structurally stale and underpowered.

- Blast Radius: Greenfield final release adjudication only; the frozen production candidate and public 60/90/120 behavior are unchanged.

- SLO/SLA Impact: Blocks release completion and any honest completion timeline; no consumer latency regression is observed.

- Data Risk: Operational risk is release-evidence invalidation; no governed or consumer data changed because preflight stopped before the one-shot ledger or product execution.

- Security/Compliance: No direct security exposure; compliance and evaluation auditability would be invalidated by proceeding.

- Invariant Violated: The untouched final holdout must be independently authored, current-contract compatible, frozen to the published floors and slices, and accepted by pure preflight before the one-shot ledger can be claimed.

- Workaround: Do not run or claim the final ledger. Preserve the corrected package and review as rejected evaluation evidence while commissioning a replacement independently authored package.

- Root Cause: The protected authoring lane created a parallel v2 expectation schema and eight-case corpus without binding its output to the candidate's v19 authoring schema or the release harness's v4 split, annotation, floor, and minimum-sample contracts.

- Solution: Create a fresh independently authored and reviewed final-holdout v4 package directly against the frozen public contract, with at least four independent observations for every required complexity band, evidence format, and pinned model profile; pass pure leakage and contract preflight, freeze hashes, and only then execute once. Do not add an adapter stack or change production behavior.

- Rollback/Forward Fix: Forward-fix the evaluation package only. Keep candidate 62bcdd8 and its published 4ee3670 checkpoint frozen; do not weaken floors, alter the 60/90/120 profiles, or tune against protected prompts.

- Verification: Require zero evaluate_frozen_evaluation_contract issues, exact hash and byte-size binding, ledger absence, independent semantic/custody review with adjudication, complete release-slice minima, then the single installed release run.

- Prevention: Make final-holdout authoring emit or validate the exact live EVALUATION_SPLIT_VERSION, FINAL_HOLDOUT_VERSION, current authoring version, and published minimum-sample contract before independent review.

- Agent Guardrails: Never consume a one-shot ledger to discover a static package mismatch; never bridge a stale semantic schema with compatibility code; never lower frozen floors or add hidden-case production logic.

- Preflight Checks: Pure release-contract validation; current authoring-version binding; case-count and slice-minimum proof; exact/near-duplicate leakage check; independent review; hash freeze; ledger absence.

- Regression Tests Added: No product regression test: this is protected evaluation evidence. The corrected package's offline validator passes with zero errors, and the current release contract deterministically rejects it before execution.

- Monitoring Updates: Track package contract version, authoring version, independent case count, slice counts, and ledger state in the release evidence receipt.

- Version/Build: 0.1.15 candidate 62bcdd8147e47874e984483b48fb1fb0a20ca413; governance checkpoint 4ee36701fb6b7ffce95cf3c931352ed3baa82e4f; dist-v14

- Related Incidents/Bugs: CB-303, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_evaluation_contract.py
- scripts/release/greenfield_final_holdout_guard.py
- src/odylith/runtime/domain_intelligence/greenfield_model_intent_authoring.py
