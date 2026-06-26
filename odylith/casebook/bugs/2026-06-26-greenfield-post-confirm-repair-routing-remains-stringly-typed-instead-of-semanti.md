- Bug ID: CB-208

- Status: Open

- Created: 2026-06-26

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Post-confirm quality failures are still routed by human-readable issue substrings, and rendered-package repair still mutates public strings instead of applying typed semantic or artifact-plan patches. This architecture is brittle under high domain variance even when the current repeated-risk defect is fixed.

- Impact: Future confirmed creates can fail or repair the wrong layer when validator wording, domain vocabulary, or artifact shape changes, blocking governed record writes or encouraging regex/template accumulation.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo maintainer source-local architecture review on branch 2026/freedom/v0.1.15.

- Detected By: Subagent architecture review after repeated greenfield post-confirm failures and CB-207 repeated-risk repair.

- Failure Signature: Post-confirm issue classification and rescue routing depend on substring matching; package repair recursively rewrites rendered public copy instead of returning typed semantic patches.

- Trigger Path: Architecture review of src/odylith/runtime/domain_intelligence/greenfield_post_confirm_engine.py and greenfield_post_confirm_repair.py during greenfield post-confirm hardening.

- Ownership: Greenfield semantic compiler, post-confirm repair engine, package quality gates, host reasoning integration, and artifact projection boundaries.

- Timeline: Captured 2026-06-26 through `odylith bug capture`.

- Blast Radius: Any greenfield project domain or complexity where semantic ambiguity, repeated claims, domain-specific proof obligations, or artifact-specific wording requires repair before governed writes.

- SLO/SLA Impact: Standard under-60s and rescue under-90s paths remain at risk because repeated string-level retries can consume repair passes without improving the semantic model.

- Data Risk: No direct data loss; fail-closed writes protect governed records, but confirmed product intent may remain unmaterialized.

- Security/Compliance: Safety, compliance, and domain-expert review can be weakened if repair mutates wording without preserving proof obligations and provenance.

- Invariant Violated: Greenfield repair must repair semantic interpretation or artifact-plan facts, not patch rendered strings or route by mutable English diagnostics.

- Root Cause: Odylith evolved deterministic validators and rendered-package cleanup faster than it evolved a typed ConfirmedIntentIR, SemanticModelIR, ArtifactPlanIR, ReviewReport, and PatchSet boundary for host-model reasoning.

- Solution: Adopt a typed host-reasoned architecture: one schema-constrained semantic compiler call, deterministic artifact planning/projection, typed deterministic and reviewer-lens findings, and targeted semantic/plan PatchSet repair before final fail-closed writes.

- Verification: Current projection fix is verified separately; the architecture defect remains open until typed findings and semantic patch repair replace stringly issue routing and rendered-string package repair.

- Prevention: Before adding more regex or template rules, check Casebook and repair semantic ownership, projection boundaries, or typed review contracts first.

- Agent Guardrails: Do not claim premium real-world readiness from greenfield fixes while post-confirm rescue is still routed by issue-string substrings or rendered-prose mutation.

- Preflight Checks: Read CB-207 and this bug before changing post-confirm repair; verify whether the change patches SemanticModelIR or ArtifactPlanIR rather than rendered strings.

- Regression Tests Added: Architecture record only; current slice tests cover child risk projection and repetition gates, not the full typed patch architecture.

- Related Incidents/Bugs: CB-207

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_engine.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_repair.py
- src/odylith/runtime/domain_intelligence/greenfield_quality_lens_repair.py
