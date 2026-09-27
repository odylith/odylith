- Bug ID: CB-289

- Status: Open

- Created: 2026-07-20

- Severity: P1

- Reproducibility: Always

- Type: UX

- Description: Two fresh installed release cases contained an explicit operator review path followed by Source repository and Source evidence metadata. Prompt recovery selected a later source-description fragment, causing the materiality gate to ask an unnecessary pre-confirm question.

- Impact: Users with a complete first path can receive an unnecessary Product Intent clarification before any transaction is compiled.

- Components Affected: domain-intelligence

- Environment(s): Fresh full installed 0.1.15 Greenfield release proof.

- Detected By: Installed 200-case release campaign.

- Failure Signature: greenfield proposal requires a material clarification before compiling a transaction

- Trigger Path: Run the source-provenanced Greenfield release matrix with inline Source repository and Source evidence labels after an explicit first path.

- Ownership: Greenfield prompt-intent recovery and materiality boundary.

- Timeline: Captured 2026-07-20 through `odylith bug capture`.

- Blast Radius: Any prompt that places retained source metadata after an otherwise complete operator workflow.

- SLO/SLA Impact: False-positive pre-confirm clarification blocks deterministic create readiness and invalidates release proof.

- Data Risk: No governed writes occur because the failure is pre-confirm.

- Security/Compliance: Security: no security exposure; no governed write occurs. Compliance and safety: preserve genuine material-ambiguity questions and do not promote raw source metadata into product facts.

- Invariant Violated: A prompt with an explicit actor, action chain, and visible outcome compiles a typed preview without asking a non-material clarification.

- Root Cause: Source-metadata filtering discarded only metadata-labelled sentences; later source-description sentences remained eligible for first-path recovery and eclipsed the explicit workflow.

- Solution: End prompt product-intent recovery at the first inline Source repository, Source evidence, or Repository description label while retaining the full raw prompt in the evidence ledger.

- Rollback/Forward Fix: Forward fix only; do not loosen the materiality gate.

- Verification: Focused parser and materialization regressions plus installed replay of the two failed cases, then the full release campaign.

- Prevention: Retain exact inline-source fixtures and assert both false clarification absence and source-tail exclusion.

- Agent Guardrails: Do not convert untrusted source descriptions into a first path or relax genuine material-ambiguity clarification.

- Preflight Checks: Run source-custody parser tests, pre-confirm matrix tests, and exact installed replay before the full campaign.

- Regression Tests Added: test_prompt_source_stops_at_inline_source_metadata_label; test_prompt_hypothesis_compiles_complete_path_before_inline_source_evidence.

- Monitoring Updates: Release telemetry clusters clarification-required outcomes by first issue.

- Version/Build: 0.1.15 local release candidate.

- Config/Flags: Full install, browser proof, rescue, natural rescue, commit recovery, and no early stopping.

- Customer Comms: No customer communication; caught before release.

- Related Incidents/Bugs: CB-274, CB-251

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_host_candidate.py
- src/odylith/runtime/domain_intelligence/greenfield_model_intent_authoring.py
- src/odylith/runtime/domain_intelligence/greenfield_candidate_review.py

- V41 Strict-Release Recurrence (2026-09-27): The frozen ten-case public release campaign passed nine cases at the full release floor and reproduced this failure on `release-research-165-source`. The request supplied an explicit `User intent` actor/action/result workflow before labelled `Source repository` and `Source evidence` provenance. The single host-native candidate call (`gpt-6-astra`, medium) nevertheless returned `clarification_required` for `product_boundary`; no transaction or governed write was produced. Retained evidence lives at `/Users/freedom/.codex/odylith-greenfield-public-v41-release-evidence.bu20uB/retained-evidence/release-proof-greenfield-release-public-live-subset.v1/release-research-165-source`, and the exact failed-subset replay is `/Users/freedom/.codex/odylith-greenfield-public-v41-release-evidence.bu20uB/failed-subset-replay/failed-subset-001.cases.json`.

- Revised Root Cause (2026-09-27): The earlier deterministic prompt-intent recovery fix correctly prevents source-tail prose from becoming the compiled first path, but the host-native candidate contract still presents provenance and explicit product intent without a sufficiently strong semantic ownership boundary. A cautious host can therefore treat a repository description as competing product scope and ask a false material question before deterministic recovery or independent review can run.

- Rejected Mechanisms (2026-09-27): Do not add another source-label parser, regex, vocabulary list, retry, repair turn, fallback author, participant selector, or stronger-model ladder. Do not weaken genuine `product_boundary` clarification. The bounded candidate is a domain-neutral authoring-contract correction: a complete explicit user workflow remains authoritative product intent, while labelled repository/source material remains provenance unless the user explicitly binds it into the owned product path. Prove that distinction across independent positive, paraphrased, reordered, and genuinely ambiguous negative controls before replaying the failed subset.

- Required V42 Proof: Contract-focused tests must show that unrelated labelled provenance cannot override a complete explicit workflow, while ambiguity that changes owned versus external responsibility still yields one `product_boundary` clarification. Then run focused and broad Greenfield suites, build a fresh immutable distribution, replay only the exact failed subset, and rerun the unchanged ten-case public release campaign before any protected holdout access.
