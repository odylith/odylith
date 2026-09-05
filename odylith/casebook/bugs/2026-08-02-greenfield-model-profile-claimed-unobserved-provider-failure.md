- Bug ID: CB-306

- Status: Open

- Created: 2026-08-02

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The release harness labeled lower-capability cases as provider-failure injected from configuration alone even when the product path never invoked a provider. This could turn model-profile metadata into a false release claim.

- Impact: A release report could claim lower-capability safety without exercising provider failure and safe fallback.

- Components Affected: domain-intelligence

- Environment(s): Maintainer Greenfield semantic release proof

- Detected By: Adversarial release-proof review

- Failure Signature: model_profile.provider_failure_injected=true while no observed provider request, failure code, or fallback receipt exists

- Trigger Path: greenfield_preconfirm_matrix release profile scoring

- Ownership: Greenfield release proof and Domain Intelligence

- Timeline: Captured 2026-08-02 through `odylith bug capture`.

- Blast Radius: All Greenfield release claims across host/model profiles

- SLO/SLA Impact: Blocks trustworthy release qualification

- Data Risk: No direct data loss; false-positive safety certification risk

- Security/Compliance: No direct security breach; audit evidence integrity affected

- Invariant Violated: Release proof must report observed behavior, never inferred behavior from profile labels

- Root Cause: Profile posture metadata was conflated with runtime evidence, and aggregate semantic scoring did not require an observed provider-failure fallback proof.

- Solution: Separate configured posture from observed behavior; run bounded-provider and forced-provider-failure installed rescue cases; require manifest-proven source-anchored fallback for release success; score each profile independently.

- Rollback/Forward Fix: Forward fix in the release harness; no shipped product rollback required.

- Verification: Focused model-profile, semantic scoring, matrix, natural-rescue, campaign, and provider-failure predicate tests pass; clean installed proof must observe fallback before release.

- Prevention: Reject self-reported profile claims and require receipt- or manifest-derived evidence for every degraded-execution release claim.

- Agent Guardrails: Do not treat environment configuration, test labels, or intended posture as observed runtime proof.

- V31 Independent Reopening (2026-09-04): The immutable candidate at
  `a1e163f25cf133c3c26b4fde0dc80a6a0393441e` still reports
  `real_installed_gpt-5.6-luna-medium_authored_preconfirm` even though its only
  successful profiles are Terra medium and Sol high. Only the missing-provider
  profile is marked lower-capability; it does not execute semantic authoring.
  Independent recomputation verified all 306 retained sealed files in the first
  three public cases and their single-call, commit-only receipts, but those
  successes cannot prove lower-capability semantic safety. Derive proof claims
  from observed requests and require a real lower-profile clarification control;
  keep provider-unavailable no-write evidence separate. The existing standard
  Terra medium member is the bounded lower-capability candidate relative to Sol
  high; no extra production model or retry lane is justified.

- Preflight Checks: Confirm every claimed model profile has balanced case coverage and every degraded-provider claim has observed failure and fallback evidence.

- Regression Tests Added: Profile assignment/environment tests; aggregate-masking profile score test; release rejection without observed provider failure; manifest predicate test.

- Code References: - scripts/release/greenfield_model_profiles.py
- scripts/release/greenfield_model_profile_proof.py
- scripts/release/greenfield_preconfirm_matrix.py
