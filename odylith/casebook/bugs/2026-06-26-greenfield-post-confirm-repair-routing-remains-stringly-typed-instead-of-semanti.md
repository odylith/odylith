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

- Failure Signature: Post-confirm issue classification and rescue routing used to depend on substring matching; the current internal report path now emits typed findings first, but package repair still recursively rewrites rendered public copy instead of applying semantic or artifact-plan patches.

- Trigger Path: Architecture review of src/odylith/runtime/domain_intelligence/greenfield_post_confirm_engine.py and greenfield_post_confirm_repair.py during greenfield post-confirm hardening.

- Ownership: Greenfield semantic compiler, post-confirm repair engine, package quality gates, host reasoning integration, and artifact projection boundaries.

- Timeline: Captured 2026-06-26 through `odylith bug capture`. Later on
  2026-06-26, the ecommerce handoff regression showed that a Radar validation
  line rendered as `covers happy path` and artifact enrichment clipped
  `Validate that ...` proof text into a noun fragment. That failed the final
  post-confirm package gate before any governed records were written. The fix
  moved those repairs upstream into Radar validation projection and
  artifact-enrichment sentence preservation instead of re-enabling rendered
  Markdown cleanup.

- Blast Radius: Any greenfield project domain or complexity where semantic ambiguity, repeated claims, domain-specific proof obligations, or artifact-specific wording requires repair before governed writes.

- SLO/SLA Impact: Standard under-60s and rescue under-90s paths remain at risk until rendered-prose mutation is replaced by targeted semantic or artifact-plan patch application and impacted-projection rerender.

- Data Risk: No direct data loss; fail-closed writes protect governed records, but confirmed product intent may remain unmaterialized.

- Security/Compliance: Safety, compliance, and domain-expert review can be weakened if repair mutates wording without preserving proof obligations and provenance.

- Invariant Violated: Greenfield repair must repair semantic interpretation or artifact-plan facts, not patch rendered strings or route by mutable English diagnostics.

- Root Cause: Odylith evolved deterministic validators and rendered-package cleanup faster than it evolved a typed ConfirmedIntentIR, SemanticModelIR, ArtifactPlanIR, ReviewReport, and PatchSet boundary for host-model reasoning.

- Solution: Adopt a typed host-reasoned architecture: one schema-constrained semantic compiler call, deterministic artifact planning/projection, typed deterministic and reviewer-lens findings, and targeted semantic/plan PatchSet repair before final fail-closed writes.

- Verification: Typed `ReviewReport` findings, typed repair-context payloads,
  stable typed failure signatures, structured quality-lens findings, `PatchSet`
  request emission, and callback consumption of `PatchSet` target layers are
  now covered by focused post-confirm engine tests. The Radar projection fix is
  covered by `test_greenfield_radar_projection_quality.py`, the previously
  failing ecommerce apply path now passes, the widened greenfield slice passed
  with 231 tests in 137.78 seconds, and the post-confirm/prewrite transaction
  suite passed with 75 tests in 315.34 seconds. The architecture defect remains
  open until rendered-string package repair is replaced by semantic or
  artifact-plan patch application plus impacted-projection rerender.

- Prevention: Before adding more regex or template rules, check Casebook and repair semantic ownership, projection boundaries, or typed review contracts first.

- Agent Guardrails: Do not claim premium real-world readiness from greenfield fixes while post-confirm rescue can still mutate rendered prose or lacks fresh high-variance simulation proof.

- Preflight Checks: Read CB-207 and this bug before changing post-confirm repair; verify whether the change patches SemanticModelIR or ArtifactPlanIR rather than rendered strings.

- Regression Tests Added: `tests/unit/runtime/test_greenfield_post_confirm_engine.py`
  now proves typed findings override unclassifiable message text, typed
  quality-lens checks do not become generic artifact drift, repair contexts
  carry typed `ReviewReport` and `PatchSet` request payloads, and manifests
  expose the patchset request. `tests/unit/runtime/test_greenfield_radar_projection_quality.py`
  proves Radar validation rows use the shared article normalizer and
  artifact-enrichment preserves complete `validate that` predicates. Full patch
  application proof remains open.

- Related Incidents/Bugs: CB-207

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_engine.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_repair.py
- src/odylith/runtime/domain_intelligence/greenfield_quality_lens_repair.py
