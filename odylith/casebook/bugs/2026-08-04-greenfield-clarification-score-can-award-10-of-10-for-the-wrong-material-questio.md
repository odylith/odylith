- Bug ID: CB-316

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Consistent

- Type: Test

- Description: Five final holdout cases received perfect per-case clarification scores even though runtime emitted required_fields first_path while case annotations required audience, outcome, dependency, or state-transition clarification. The semantic release scorer correctly reported zero material-question recall.

- Impact: A release can appear consumer-safe while asking an irrelevant generic question that annoys the user and does not resolve the actual ambiguity.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 final private holdout from clean dist 0aac74c63

- Detected By: Adversarial comparison of per-case and semantic holdout scorecards

- Failure Signature: fh-19 fh-20 fh-21 fh-22 fh-24 scored 10/10 with required_fields first_path while semantic material_question_recall was 0/6

- Trigger Path: Greenfield release matrix expected-clarification cases with non-first_path material annotations

- Ownership: Release proof clarification contract and Domain Intelligence

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: All release claims that include typed material clarification

- SLO/SLA Impact: Delivery risk: false-green quality evidence blocks a trustworthy release decision

- Data Risk: Operational risk: no governed data loss, but misleading test evidence can ship incorrect interaction behavior

- Security/Compliance: Domain risk: safety and dependency ambiguities can be scored as resolved when they are not

- Invariant Violated: Per-case and aggregate scorers must verify the same typed material field and no-write contract

- Root Cause: Per-case clarification scoring hardcodes the canonical first_path question instead of reading each case's expected material fields

- Solution: Use one annotation-driven typed clarification contract in runtime output, per-case scoring, and aggregate semantic scoring

- Verification: The annotation-driven clarification scorer and runtime regressions passed the combined 25-test anti-clipping, clarification, EDIT, and Registry pack in 41.89 seconds. Thirteen thin-prompt authority cases also passed with one correctly scoped question and no staged artifacts. The `cf41046a9` follow-up added display-label versus field-ID equivalence and multiline evidence-preservation regressions; the broader materiality, sealed-intent, evaluator, and retired-holdout pack passed 253 tests in 294.85 seconds. Clean installed release proof remains pending.

- Prevention: Ban independent hardcoded clarification defaults in release scoring

- Agent Guardrails: A no-write clarification is not correct merely because it asked some question

- Related Incidents/Bugs: CB-251, CB-315

- Fixed In: 0.1.15

- Code References: - scripts/release/greenfield_matrix_clarification.py
- scripts/release/greenfield_semantic_release_score.py

- Fresh Blind Holdout Follow-Up (2026-08-08): The one-shot campaign exposed two additional evaluator defects. Case loading collapsed Markdown line boundaries and changed the evidence presented to the exact installed runtime, producing five false product clarifications. Per-case clarification scoring also compared user-facing source labels with snake_case field IDs literally while aggregate scoring canonicalized them. The case loader now preserves block structure and both scorers use one shared field-ID canonicalizer while retaining source labels in the visible question. The disclosed corpus is preserved as `retired-cf410-final-holdout-regressions.v1.json` and is not eligible for a new release claim.

- Disclosed Replacement Evaluator Closure (2026-08-16): Frozen-case preparation now validates the external holdout and manifest bytes before binding actual per-prompt hashes; synthetic schema metadata cannot impersonate source identity. Required-term matching is polarity-aware, accepted-fact composition is category-, field-, owner-, family-, and order-bound, and direct action atoms must preserve canonical order. Non-compiled terminal results expose one primary upstream failure and mark downstream transaction, artifact, navigation, browser, and confirmation stages not applicable; a compiled receipt followed by create failure remains an attempted transaction and never receives N/A credit. Exact adversarial probes, the `193/193` evaluator suite, `46/46` security/proof suite, and independent `211/211` closure pack pass. CB-316 remains `FixedPendingRelease`; release closeout, not a hand edit, owns final closure after exact installed and untouched-holdout proof.
