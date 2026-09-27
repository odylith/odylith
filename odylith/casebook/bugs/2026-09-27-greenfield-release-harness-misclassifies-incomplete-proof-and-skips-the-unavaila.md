- Bug ID: CB-347

- Status: Open

- Created: 2026-09-27

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The consumed V31 holdout exposed three qualification-harness defects independent of the host timeout: the sealed command contained release-forbidden stop flags; unavailable-provider proof used unsupported repair tier rescue and failed in argument parsing before provider invocation; semantic scoring evaluated a partial campaign with stale relation and model-observation schemas, reporting false P0/P1 failures for completed 10/10 cases.

- Impact: Greenfield cannot obtain trustworthy release qualification even when product cases pass because the release harness can reject valid receipts, fail to exercise its stated negative control, and present evaluator incompatibility as semantic regression.

- Components Affected: release

- Environment(s): 0.1.15 release harness at commit 69ee8abd81d76eb9a1c940c9bfd266e47c163a62 evaluating the consumed V31 sealed holdout result.

- Detected By: Post-run causal review of V31 result, telemetry and current release-harness source.

- Failure Signature: Unavailable-provider proof returns argparse exit 2 for unsupported repair_tier rescue; semantic release reports relation fidelity 0 and 16 P0/32 P1 despite 16 completed cases passing 10/10; current authored_semantics source_precedence and host_candidate/candidate_review roles are rejected or ignored.

- Trigger Path: scripts/release/greenfield_preconfirm_matrix.py release proof and its semantic/model-profile evaluators.

- Ownership: Greenfield release qualification harness and evaluator contract parity.

- Timeline: 2026-09-27: V31 stopped on a real host timeout after 16 passes; post-run review proved the sealed receipt command was policy-invalid, unavailable-provider proof never reached the provider, and semantic/model-profile evaluators were stale relative to current receipts. The bounded repair then exposed a fourth proof defect: rejecting every Sol result had masked that a host-native result could relabel only its top-level profile ID without rechecking the sealed stage, host request, configured model, and reviewer observation.

- Blast Radius: Every release-tier Greenfield campaign using current participant-first receipts; incomplete campaigns are especially misleading, but stale receipt schemas can invalidate complete campaigns too.

- SLO/SLA Impact: Blocks trustworthy release adjudication and can waste another one-shot holdout if not corrected before sealing.

- Data Risk: No governed product data corruption; risk is false release evidence and incorrect operator decisions.

- Security/Compliance: Unavailable-provider fail-closed behavior is not actually proven, weakening safety evidence until fixed.

- Invariant Violated: Release evidence must execute the claimed controls, score the current canonical receipt schema, and distinguish incomplete proof from semantic failure.

- Workaround: Treat V31 semantic P0/P1 counts and relation-fidelity zero as evaluator-invalid. Preserve product case results and the consumed ledger, but make no release claim.

- Root Cause: Release harness evolution lagged the current single-host-candidate plus independent-review architecture: command packaging retained forbidden stop flags, the negative control retained an unsupported repair-tier argument, relation scoring omitted source_precedence, and model-slice scoring expected retired participant-selection/remaining-authoring roles.

- Solution: Implemented in the working checkpoint: unavailable-provider proof now authors exactly one standard host candidate and exercises installed independent review under the unavailable profile; current `source_precedence` and host-candidate/reviewer receipts are accepted by the closed evaluator schemas; incomplete campaigns return `incomplete`/`unscored` with no semantic severity assignment or release credit. Explicit Sol-high cases are now admitted only as diagnostics, are never assigned automatically, and remain excluded from release-success coverage. The aggregate proof independently rechecks the claimed profile against configured provider/model/effort, sealed stage identity, host argv receipt, and reviewer observation so a relabeled result fails closed. Release command-package validation remains a required pre-seal check. No floor is weakened and diagnostic profiles receive no release credit.

- Rollback/Forward Fix: Forward-fix the harness; never rerun the consumed V31 holdout.

- Verification: The original harness repair passes `153/153` focused and adjacent tests. The diagnostic-profile and profile-binding extension passes `341/341` focused release-harness tests, including valid explicit Sol discovery, zero Sol release credit, no automatic Sol assignment, forged top-level profile relabel rejection, and independent mutations of every configured, stage, argv, and reviewer profile binding. Governance browser proof passes `109/109` across Radar, Registry, Casebook, and Compass normal, empty/fallback, degraded, error, density, layout, sorting, and selection-race states. The complete install suite previously reached `1,715/1,716`; its sole failure is the pre-existing customer-bootstrap guidance byte budget (`17,127 < 17,000`) in untouched `test_manager.py`, unrelated to this patch. An identical-input public Astra-medium versus Sol-high comparison and full immutable release qualification remain required before sealing a new holdout.

- Prevention: Version evaluator schemas with the canonical receipt contracts and make package preflight execute the same policy validator as the release harness before a ledger can be sealed.

- Agent Guardrails: Do not interpret evaluator-invalid P0/P1 output as product semantics, do not relax semantic floors, do not patch protected cases, and do not add retries, repair, fallback authors, parser rules or regex classifiers.

- Preflight Checks: Verify release command policy, supported CLI arguments, relation schema parity, observed role parity and incomplete-campaign behavior before any new sealed input is authored.

- Regression Tests Added: Added exact current-receipt relation parity, host-candidate/reviewer observation parity, incomplete/unscored severity suppression, and one-candidate provider-unavailable/no-write controls. The consumed holdout is not a regression fixture.

- Monitoring Updates: Report product-case failures, infrastructure timeouts, missing cases, evaluator-invalid receipts and negative-control execution as separate release dimensions.

- Version/Build: 0.1.15 commit 69ee8abd81d76eb9a1c940c9bfd266e47c163a62

- Config/Flags: proof-tier=release; current participant-first host_candidate/candidate_review receipt contract; operational timeout 180s

- Customer Comms: Release remains unclaimed; operator status must distinguish product quality from evaluator validity.

- Related Incidents/Bugs: CB-346, CB-303, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_semantic_release_score.py
- scripts/release/greenfield_relation_fidelity.py
- scripts/release/greenfield_matrix_statistics.py
- scripts/release/greenfield_model_profiles.py
- scripts/release/greenfield_model_profile_proof.py

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
