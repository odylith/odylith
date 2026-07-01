- Bug ID: CB-214

- Status: FixedPendingRelease

- Created: 2026-07-01

- Severity: P2

- Reproducibility: High

- Type: Tooling

- Description: Greenfield Atlas labels can repeat visible result copy after confirmation

- Impact: Confirmed greenfield create can fail after operator confirmation with no governed records written when generated Atlas Mermaid labels repeat adjacent visible copy.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 pinned consumer repo /Users/freedom/mock/grn-sim via Codex desktop; maintainer source-local repair target.

- Detected By: Consumer confirmed greenfield create final package quality gate.

- Failure Signature: Atlas Mermaid gene-expression-simulation-model-first-path.mmd and gene-expression-simulation-model-release-proof-review.mmd repeat adjacent word result result; no governed records written.

- Trigger Path: ./.odylith/bin/odylith greenfield create --repo-root . --prompt 'Draft a product-first greenfield proposal for building an AI-model that simulates gene expression prediction.' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1

- Ownership: Greenfield semantic model to Atlas Mermaid rendering and post-confirm package repair boundary.

- Timeline: 2026-07-01: grn-sim consumer repo confirmed intent saved; post-confirm create failed on two Atlas Mermaid repeated-result labels; consumer CB-001 captured the repro evidence. Maintainer source-local repair added generic Mermaid header/body label custody, saved-as result semantics, and evaluation-depth semantics for scientific model requests.

- Blast Radius: Greenfield confirmed-create flows whose visible result, proof, or outcome language repeats a generic diagram wrapper term such as result.

- SLO/SLA Impact: Blocks post-confirm governed project creation and violates the under-60s standard completion goal until repaired.

- Data Risk: No governed project records were written; accepted intent remains on disk and can be replayed after platform repair.

- Security/Compliance: No direct security exposure observed. Policy risk is delivery-trust erosion from a failed governed write; privacy risk is low because no user data was copied into records; accessibility/readability risk is material because repeated visible copy makes generated diagrams unclear; safety risk is low because the gate failed closed.

- Invariant Violated: Human-visible governed artifacts must be grammatical, non-repetitive, and clear before the write transaction commits.

- Workaround: No safe consumer-side workaround. Do not hand-author governed records; replay the confirmed intent only after Odylith platform repair.

- Root Cause: Atlas label composition prepended fixed headers such as Proof result and Visible result to semantic visible-result text whose body could already start with result language. A saved-result action such as "save the result as a reviewable experiment" also preserved the generic object word instead of collapsing to the target artifact. The same thin scientific request path lacked a typed evaluation-depth model, so source-local replay could either create shallow scientific artifacts or trip adjacent duplicate text such as evidence evidence when completion appended generic suffixes to an evidence-focused phrase.

- Follow-Up Root Cause (2026-07-01): The exact grn-sim saved-intent replay also exposed an adjacent Atlas first-path label grammar defect after the repeated-result fix. Subject stripping converted a finite accepted action clause into a visible Mermaid step label by using a local action replacement table, so coordinated verbs could become mixed finite/base copy such as "Uploads or select ..." instead of the imperative "Upload or select ...". The final gate did not catch this escaped shape because existing mixed-action checks were hard-coded to modal/adverbial prose shapes rather than typed Mermaid labels.

- Failed Mechanism Found During QA (2026-07-01): The first shared-grammar repair moved Atlas label conversion out of the local renderer table, but it still converted any recognized finite token after `and` or `or`. A read-only subagent review caught that this could corrupt valid object-list labels such as `Review orders and offers`, `Choose methods and controls for comparison`, and `Upload controls and records for later review` by treating plural nouns as coordinated verbs.

- Failed Mechanisms: Replaying the consumer repo cannot fix the platform because the final gate correctly fails closed before governed writes. Adding one-off consumer edits, weakening the generated-copy gate, or patching rendered Mermaid text would repeat prior failed mechanisms from CB-208. The durable fix has to repair source facts and projection helpers before Atlas source is finalized.

- Solution: Added a generic source-owned Mermaid header/body label helper so fixed node headers remove only their duplicated body-leading term. Added generic saved-as result-object semantics so generic objects such as result, output, outcome, or artifact become the saved target label. Added optional EvaluationSemantics IR for research, model, simulation, prediction, and evaluation prompts; the no-write Product Intent prompt now demands observed quantity, source evidence, method/model boundary, variables, baseline/comparison, uncertainty/tolerance, reproducibility, and excluded claims, and post-confirm workstream intelligence projects those obligations into governed artifacts. Added suffix-once completion custody and use-to actor parsing to keep neighboring final-gate failures from blocking the same replay.

- Follow-Up Solution (2026-07-01): Moved Atlas first-path label imperative conversion onto the shared prose grammar owner (`base_following_action_verbs`) and removed the local Mermaid-label action table. Added a typed Mermaid-label public-copy guard that uses shared base/finite action token classification to reject mixed coordinated action labels while allowing correct imperative labels and ordinary finite prose such as "uploads or selects".

- QA-Corrected Solution (2026-07-01): Added a shared coordinated-action discriminator that distinguishes action-clause coordination from plural object-list coordination before converting or rejecting labels. The converter still repairs action chains such as `enters a form and submits` and `logs progress and reviews weekly status`, but it preserves object lists such as `orders and offers`, `methods and controls`, and `controls and records for later review`. The typed Mermaid-label gate now reuses the same discriminator instead of running its own token-only action check.

- Additional QA Correction (2026-07-01): Local source pressure testing found that the object-list discriminator could over-preserve a leading coordinated action chain, leaving `checks and controls for drift` as `check and controls for drift`. The shared grammar owner now treats a connector whose left side is the leading action token as action coordination, while still preserving downstream plural object lists.

- Rollback/Forward Fix: Forward fix in Odylith domain-intelligence and Atlas rendering path; do not weaken gates.

- Verification: Source-local proof passed the focused Atlas/scientific replay tests, the 45-test post-confirm quality repair suite, the 27-test live simulation and semantic model quality suite, and the 93-test confirmed diagram/recovery/post-confirm repair suite. Disposable source-local CLI replay of the saved grn-sim confirmed intent completed governed create in 25s with 4 backlog records, 5 components, 6 diagrams, validation gate passed, and zero `result result` or `evidence evidence` occurrences. A second disposable thin scientific prompt replay completed governed create in 24s with 4 backlog records, 3 components, 6 diagrams, validation gate passed, zero `result result`, zero `evidence evidence`, and governed artifacts containing method, baseline, uncertainty, tolerance, and reproducibility evidence. Fresh committed-head local release dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-9bea5784` passed the source-plus-dist 285-term platform leakage gate. Installed-path replay of the saved failed intent completed post-confirm create in 32s with governed records and zero repeated result/evidence copy; installed thin-science propose-to-create completed in 28s with evidence-depth terms present and zero repeated result/evidence copy.

- Follow-Up Verification (2026-07-01): Focused tests now pass `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_hiit_quality_regression.py::test_generated_copy_quality_blocks_mixed_action_coordination_in_visible_labels tests/unit/runtime/test_greenfield_live_simulation_regressions.py::test_gene_expression_confirmed_intent_finishes_without_repeated_result_atlas_copy`. A fresh source-local disposable replay of `/Users/freedom/mock/grn-sim/.odylith/runtime/greenfield/confirmed-intent.md` completed governed create in about 25.31s with final post-confirm manifest passed, issue_count 0, 4 backlog records, 5 Registry components, and 6 Atlas diagrams. Registry validation passed with 5 components, 6 meaningful events, and 6 mapped events; Atlas render passed with 6 fresh diagrams. Direct visible-copy scan over 40 generated Radar, Registry, Atlas, runtime, and Compass files found zero `result result`, `proof proof`, `evidence evidence`, `output output`, `expression expression`, `simulation simulation`, `model model`, `Launches launches`, or `to flags`; the first-path Atlas label now renders `Upload or select a small<br/>expression dataset`.

- QA-Corrected Verification (2026-07-01): After the object-list ambiguity repair, focused proof passed `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_hiit_quality_regression.py tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py::test_first_path_clauses_compile_actions_outcomes_and_noun_lists tests/unit/runtime/test_greenfield_live_simulation_regressions.py::test_gene_expression_confirmed_intent_finishes_without_repeated_result_atlas_copy` (`9 passed`) and `tests/unit/runtime/test_greenfield_atlas_contract.py tests/unit/runtime/test_greenfield_confirmed_surfaces.py` (`27 passed`). Exact grn-sim source-local replay completed governed create in about 24.00s with manifest passed, issue_count 0, 4 backlog records, 5 Registry components, and 6 Atlas diagrams; Registry validation and Atlas render passed again. After the leading-action over-preservation correction, the focused grammar/copy proof passed again (`2 passed`) and direct sanity checks now render `checks and controls for drift` as `check and control for drift` while preserving `reviews orders and offers` and `chooses methods and controls for comparison`.

- Working-Tree Installed Matrix Verification (2026-07-01): Fresh working-tree local-release dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-label-qa2` passed the maintained installed matrix at `/tmp/greenfield-post-confirm-matrix-working-label-qa2.v1.json`: 14/14 standard cases scored hard 10/10 in 23.594-28.426 seconds, every case wrote governed records with zero issues, generated browser-surface proof passed for all 14 repos, synthetic rescue passed in 34.934 seconds, natural structured rescue passed in 66.245 seconds, platform domain-leakage proof passed across 213 generated readback terms, and temp cleanup reported no remaining roots. This is strong package-path proof, not final release closure; final closure still requires a committed-head dist rebuild and rerun after the next spaced commit/push checkpoint.

- Prevention: Add unit and package-quality regressions for visible-result and proof labels whose semantic body contains result/output/result-explanation language; include high-variance scientific simulation proof.

- Follow-Up Prevention (2026-07-01): Keep all Atlas action-label inflection on the shared prose grammar owner, and keep the fail-closed guard at typed `mermaid_label` units so mixed finite/base labels cannot bypass package quality even when the graph syntax itself is valid.

- QA-Corrected Prevention (2026-07-01): Any future label grammar repair must prove both sides of the ambiguity: real coordinated action clauses must normalize to imperative base form, including leading action chains, while noun coordination that happens to use action-shaped words must stay intact.

- Agent Guardrails: Search Casebook/governance first, avoid domain-specific vocabulary and regex towers, repair semantic or label projection facts rather than hand-polishing generated repos.

- Preflight Checks: Confirm no duplicate maintainer bug exists; inspect CB-209 and CB-213 failed mechanisms; test source-local and installed dist paths before release claims.

- Related Incidents/Bugs: Consumer CB-001 in /Users/freedom/mock/grn-sim; maintainer CB-209; maintainer CB-213.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py
- src/odylith/runtime/common/prose_grammar.py
- src/odylith/runtime/artifact_quality/generated_copy_quality.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagrams.py
- src/odylith/runtime/domain_intelligence/greenfield_sequence_labeling.py
