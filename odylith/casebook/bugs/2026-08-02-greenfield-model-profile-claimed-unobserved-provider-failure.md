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

- V43 Private Timing And Rescue Coverage Gaps (2026-09-05): Independent review
  finds two release-proof gaps before qualification. Rescue is now truthfully
  Terra/medium and lower-capability, so it needs its own installed committed and
  clarification/no-write evidence. The unchanged public fourteen contain only
  a standard-assigned clarification; append a separately labeled rescue control
  through the existing case-file route without changing or reassigning those
  public cases. Do not aggregate standard and rescue or mislabel rescue as higher
  capability. Also, the private initial-cap/review observation must be read from
  retained evidence and cross-checked against the sealed profile and shared
  window. The existing six-field envelope alone does not prove stage timing.
  Use the existing case and clarification readers plus model_profile_evidence;
  no canonical schema or new evaluator framework is needed. These remain open
  until the final selected review schedule is exercised and authenticated. Current
  semantic-terminal rejection already prevents any qualification attempt.

- V44 Composite Role Proof (2026-09-05): The selected candidate explicitly pins
  Terra-medium initial authors and Sol-high reviewers on standard/rescue, with
  Sol-high in both deep roles. New profile v8 identities bind the composition
  before call one. Lower capability refers to the initial-author role relative
  to all-Sol deep; do not claim every call is lower-capability or that a corrected
  candidate proves Terra alone was safe. The goal does not require a fourth
  production profile. The six-field sealed observation continues to describe
  the initial author, while retained private evidence must validate each actual
  role, model, effort, cap, elapsed time and call count. A forged passed summary
  must not bypass aggregate validation. Initial caps 40/60/85 reserve review
  15/20/20 inside unchanged model55/80/105; review may use all unused shared time.
  Each lower-author profile still needs its own real source-bound clarification
  and positive evidence, separately from unavailable-provider behavior.

- V47 Clarification Call Custody (2026-09-05): Reviewer-selected clarification can
  use two calls. Private role proof already records both, but the clarification
  dataclass lacked that count and materialization defaulted its receipt to one.
  Carry the existing actual count on both typed authoring outcomes and remove
  the receipt fallback. One- and two-call receipt tests, reviewed clarification
  metadata tests, and the shared role proof preserve this distinction without
  expanding the public six-field profile observation or adding model calls.

- Regression Tests Added: Profile assignment/environment tests; aggregate-masking profile score test; release rejection without observed provider failure; manifest predicate test.

- Code References: - scripts/release/greenfield_model_profiles.py
- scripts/release/greenfield_model_profile_proof.py
- scripts/release/greenfield_preconfirm_matrix.py
