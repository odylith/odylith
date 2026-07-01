- Bug ID: CB-211

- Status: FixedPendingRelease

- Created: 2026-06-30

- Severity: P2

- Reproducibility: Consistent

- Type: Product

- Description: Structured rescue rejects intentional empty-list semantic patches

- Impact: A repairable final greenfield quality failure can still stop before governed writes when the correct host-adjudicated repair is to clear a list-valued semantic boundary, leaving natural rescue proof failed even though the standard path remains green.

- Components Affected: tribunal,domain-intelligence

- Environment(s): Maintainer local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-boundary-fix installed into disposable consumer repos under /Users/freedom/mock with Codex CLI provider-backed structured rescue

- Detected By: Natural structured-rescue proof leg after a fresh ten-domain standard matrix passed at hard 10/10

- Failure Signature: structured_rescue_semantic_patch requested semantic_model.domain_ontology.external_systems; Tribunal returned a decision summary to remove the unsupported external boundary but zero operations, rejection reason replacement_fact is empty, create_returncode=2, no governed records written

- Trigger Path: scripts/release/greenfield_post_confirm_matrix.py rescue proof path invoking greenfield create --repair-tier auto with provider-backed Tribunal patch planning

- Ownership: Tribunal structured patch planner replacement-fact custody and Domain Intelligence rescue patch application

- Timeline: Captured 2026-06-30 through `odylith bug capture`. Fixed in source
  the same day by distinguishing missing replacement facts from intentional
  typed list-valued semantic clears in Tribunal planning, rescue planning, and
  SemanticModelIR patch application.

- Blast Radius: Any rescue/deep greenfield or future governed operation where the correct semantic patch is an explicit empty list, empty set, or intentional clear rather than a nonempty replacement value

- SLO/SLA Impact: Standard path remains under 60s; rescue path is not release-ready because the natural host-planned proof fails before the 90s budget completes governed writes

- Data Risk: Low: fail-closed behavior prevents bad governed records, but it blocks valid project creation and erodes release proof

- Security/Compliance: No direct security exposure; compliance posture is governance-trust risk only because release evidence could falsely imply natural rescue readiness if this failed mechanism is not tracked

- Invariant Violated: Structured repair must distinguish a missing replacement fact from an intentional typed empty list or clear operation, and must apply the latter through schema custody rather than rejecting it as absent

- Root Cause: Tribunal and the greenfield rescue path used one generic
  emptiness predicate for all replacement facts. That correctly rejected blank
  strings and absent facts, but it also rejected the valid host-planned repair
  where a list-valued semantic field should become an explicit empty list.

- Solution: `tribunal_patch_planner.py` now materializes list envelopes for
  list-valued semantic fields even when `list_values` is empty, validates that
  fact as explicit when the requested operation targets a list-valued semantic
  field, and exposes the same missing-fact decision to rescue planning. The
  SemanticModelIR patch executor applies explicit empty lists to both accepted
  intent and semantic ontology, then records the host decision ledger when the
  operation carries confidence and ledger evidence. Blank, absent, prose-only,
  moved-target, artifact-plan empty, and non-list empty facts remain blockers.

- Verification: Focused proof passed 67 Tribunal/PatchSet/semantic-engine
  tests. Fresh installed dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-clear-list-fix`
  passed the maintained release matrix: 13/13 standard cases at hard 10/10,
  max standard create 30.563s, average 27.854s, zero quality/browser/platform
  leakage issues, browser proof passed for every case, temp cleanup passed,
  synthetic rescue passed in 38.917s, and natural provider-backed structured
  rescue passed in 60.926s with one accepted Tribunal operation, no rejections,
  `structured_rescue_semantic_patch` repaired, and governed writes committed.
