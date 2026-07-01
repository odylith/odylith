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

- Failed Mechanisms: Replaying the consumer repo cannot fix the platform because the final gate correctly fails closed before governed writes. Adding one-off consumer edits, weakening the generated-copy gate, or patching rendered Mermaid text would repeat prior failed mechanisms from CB-208. The durable fix has to repair source facts and projection helpers before Atlas source is finalized.

- Solution: Added a generic source-owned Mermaid header/body label helper so fixed node headers remove only their duplicated body-leading term. Added generic saved-as result-object semantics so generic objects such as result, output, outcome, or artifact become the saved target label. Added optional EvaluationSemantics IR for research, model, simulation, prediction, and evaluation prompts; the no-write Product Intent prompt now demands observed quantity, source evidence, method/model boundary, variables, baseline/comparison, uncertainty/tolerance, reproducibility, and excluded claims, and post-confirm workstream intelligence projects those obligations into governed artifacts. Added suffix-once completion custody and use-to actor parsing to keep neighboring final-gate failures from blocking the same replay.

- Rollback/Forward Fix: Forward fix in Odylith domain-intelligence and Atlas rendering path; do not weaken gates.

- Verification: Source-local proof passed the focused Atlas/scientific replay tests, the 45-test post-confirm quality repair suite, the 27-test live simulation and semantic model quality suite, and the 93-test confirmed diagram/recovery/post-confirm repair suite. Disposable source-local CLI replay of the saved grn-sim confirmed intent completed governed create in 25s with 4 backlog records, 5 components, 6 diagrams, validation gate passed, and zero `result result` or `evidence evidence` occurrences. A second disposable thin scientific prompt replay completed governed create in 24s with 4 backlog records, 3 components, 6 diagrams, validation gate passed, zero `result result`, zero `evidence evidence`, and governed artifacts containing method, baseline, uncertainty, tolerance, and reproducibility evidence. Fresh committed-head local release dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-9bea5784` passed the source-plus-dist 285-term platform leakage gate. Installed-path replay of the saved failed intent completed post-confirm create in 32s with governed records and zero repeated result/evidence copy; installed thin-science propose-to-create completed in 28s with evidence-depth terms present and zero repeated result/evidence copy.

- Prevention: Add unit and package-quality regressions for visible-result and proof labels whose semantic body contains result/output/result-explanation language; include high-variance scientific simulation proof.

- Agent Guardrails: Search Casebook/governance first, avoid domain-specific vocabulary and regex towers, repair semantic or label projection facts rather than hand-polishing generated repos.

- Preflight Checks: Confirm no duplicate maintainer bug exists; inspect CB-209 and CB-213 failed mechanisms; test source-local and installed dist paths before release claims.

- Related Incidents/Bugs: Consumer CB-001 in /Users/freedom/mock/grn-sim; maintainer CB-209; maintainer CB-213.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagrams.py
- src/odylith/runtime/domain_intelligence/greenfield_sequence_labeling.py
