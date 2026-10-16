- Bug ID: CB-345

- Status: FixedPendingRelease

- Created: 2026-09-26

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Immutable V28 public qualification passed the first 30 cases, then archive-custody-01 committed a high-quality 4 Radar / 4 Registry / 5 Atlas package whose user-visible Radar, Atlas, project brief, dashboard, and handoff copy included the source-only marker PUBLIC-V11-ARCHIVE-MARKER and paraphrased its synthetic-source control. The prompt explicitly said the marker identified only the synthetic source and must never become product copy.

- Impact: Source/evaluation custody metadata becomes user-visible product truth across governance surfaces, failing semantic fidelity despite successful transaction and browser proof.

- Components Affected: domain-intelligence

- Environment(s): Immutable V28 full-install public campaign at commit 005775a055a8becaeadd4209ce02c32f02fdf690

- Detected By: Fail-fast installed Greenfield public qualification with retained browser and semantic evidence

- Failure Signature: source evidence identifier leaked into product artifacts: PUBLIC-V11-ARCHIVE-MARKER

- Trigger Path: greenfield candidate-contract -> one host candidate -> independent review -> propose -> create -> retained product-surface leakage scan

- Ownership: Domain Intelligence semantic admission boundary

- Timeline: Captured 2026-09-26 through `odylith bug capture`.

- Blast Radius: Any Greenfield prompt containing source-custody, fixture, evidence-identity, or non-projection directives can contaminate Radar, Registry, Atlas, briefs, dashboards, and handoffs.

- SLO/SLA Impact: Blocks v0.1.15 Greenfield release qualification; timing and browser floors otherwise passed for the case.

- Data Risk: No repository corruption; semantic contamination is sealed and committed atomically.

- Security/Compliance: Trust/provenance defect: internal source metadata crosses into product-visible governance.

- Invariant Violated: Source-only evidence custody must remain sealed evidence and must not become canonical product truth or proposed product work.

- Root Cause: The shared operational-constraint semantic role is broad enough to admit source-handling/non-projection directives, and reviewer v8 does not reject the same meaning when restated in provisional workstreams or verification. Structural projection then correctly copies the contaminated canonical meaning everywhere.

- Solution: Tighten the one host-author/one reviewer semantic contract: instructions governing the supplied source, fixture or candidate as authoring-transaction inputs are authoring controls, never accepted product facts or proposed product work. Preserve them only in sealed source evidence. Requested product workflows that manage evidence, provenance or source identity as domain data remain product truth. Do not add regex, parser, repair, retry, fallback, renderer filters, or a new schema unless fresh independent recurrence disproves this bounded correction.

- Rollback/Forward Fix: Forward fix the shared semantic admission owner; preserve V28 as terminal failure evidence and rebuild a fresh immutable artifact before rerunning from case one.

- Verification: Live Astra authoring omitted the literal marker and its synthetic-source paraphrase, preserved the complete `accepts or rejects` action, and reviewer v9 admitted the clean candidate. A post-review Astra-medium discriminator admitted a genuine product audit-ledger requirement for evidence source identity, denied truncated `accepts` at `candidate.accepted_source.events[1].action_quote`, denied the literal source-control fact, and denied paraphrased source-control work; all four expected outcomes passed. Retained evidence: `/private/tmp/odylith-v29-semantic-controls-v0mroab9/results.json`, SHA-256 `4e6470674b187a5cfe7a44d5a0608ae9df81996d8e76e6280d96462cb19eac91`. Focused proof passes `437/437`; complete runtime Greenfield proof passes `1,971/1,971`; full installed proof passes `1,175/1,175`; Greenfield integration/browser proof passes `23/23`. Immutable V29 public qualification from case one remains required.

- Prevention: Treat source custody and product truth as separate semantic authorities at candidate authoring and independent review; keep downstream projection structural.

- Agent Guardrails: Do not patch renderers, word lists, fixtures, or the evaluator. Do not introduce regex stacks or repair loops. Fix the single semantic owner and remove superseded behavior.

- Preflight Checks: Confirm branch clean; prove V28 retained evidence; run source-only versus user-facing label controls before immutable rebuild.

- Regression Tests Added: Shared role, active host contract, complete disjunctive-action schema, and reviewer source-custody/coherent-branch prompt contracts are pinned in focused unit tests.

- Monitoring Updates: Retain source-identifier leakage scan as the deterministic release backstop.

- Version/Build: 0.1.15 V28 commit 005775a055a8becaeadd4209ce02c32f02fdf690

- Related Incidents/Bugs: CB-227, CB-303

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_candidate_review.py
- src/odylith/runtime/domain_intelligence/greenfield_model_intent_authoring.py
- scripts/release/greenfield_matrix_leakage.py
