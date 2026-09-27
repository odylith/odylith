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

- Timeline: 2026-09-27: V31 stopped on a real host timeout after 16 passes; post-run review proved the sealed receipt command was policy-invalid, unavailable-provider proof never reached the provider, and semantic/model-profile evaluators were stale relative to current receipts. The bounded repair then exposed a fourth proof defect: a host-native result could relabel only its top-level profile ID without rechecking the sealed stage, host request, configured model, and reviewer observation. A later public Astra-medium attempt proved its host candidate succeeded but its installed proposal stage returned nonzero; because that discovery invocation omitted retained evidence, cleanup made the exact reviewer or provider cause irrecoverable. The paired Sol-high attempt retained evidence and stopped before authoring because `deep` is deliberately not a release-qualified successful execution tier.

- Blast Radius: Every release-tier Greenfield campaign using current participant-first receipts; incomplete campaigns are especially misleading, but stale receipt schemas can invalidate complete campaigns too.

- SLO/SLA Impact: Blocks trustworthy release adjudication and can waste another one-shot holdout if not corrected before sealing.

- Data Risk: No governed product data corruption; risk is false release evidence and incorrect operator decisions.

- Security/Compliance: Unavailable-provider fail-closed behavior is not actually proven, weakening safety evidence until fixed.

- Invariant Violated: Release evidence must execute the claimed controls, score the current canonical receipt schema, and distinguish incomplete proof from semantic failure.

- Workaround: Treat V31 semantic P0/P1 counts and relation-fidelity zero as evaluator-invalid. Preserve product case results and the consumed ledger, but make no release claim.

- Root Cause: Release harness evolution lagged the current single-host-candidate plus independent-review architecture: command packaging retained forbidden stop flags, the negative control retained an unsupported repair-tier argument, relation scoring omitted source_precedence, and model-slice scoring expected retired participant-selection/remaining-authoring roles.

- Solution: Implemented in the working checkpoint: unavailable-provider proof now authors exactly one standard host candidate and exercises installed independent review under the unavailable profile; current `source_precedence` and host-candidate/reviewer receipts are accepted by the closed evaluator schemas; incomplete campaigns return `incomplete`/`unscored` with no semantic severity assignment or release credit. The aggregate proof independently rechecks the claimed profile against configured provider/model/effort, sealed stage identity, the exact canonical host argv shape and argument count, the executable identity bound into the sealed stage summary, and reviewer observation. Relabeled results and valid-looking receipt substitutions fail closed. Sol-high remains an unsupported diagnostic and cannot be assigned as a successful matrix route; the incomplete explicit-diagnostic path is removed instead of adding a hidden deep-success mode. Release command-package validation and retained evidence are required before another live public control. No floor is weakened.

- Rollback/Forward Fix: Forward-fix the harness; never rerun the consumed V31 holdout.

- Verification: All `45` Greenfield install/release-harness test files pass `1,194/1,194`; the focused model-profile pack passes `377/377`. Mutation coverage rejects configured, stage, exact argv-shape, argument-count, executable-identity, model/effort, output-schema, and reviewer substitutions. Independent re-adjudication returns SHIP with no P0/P1. Fresh governance browser proof passes `105/105` across Radar, Registry, Casebook, and Compass normal, empty/fallback, degraded, error, density, layout, sorting, and selection-race states. The complete install suite previously reached `1,715/1,716`; its sole failure is the pre-existing customer-bootstrap guidance byte budget (`17,127 < 17,000`) in untouched `test_manager.py`, unrelated to this patch. Public prompt SHA-256 `f6e0f5a60a057df3573db26b0c2b847faf6177a573a8dcf242520426d660ea1d` produced no model-quality comparison: Astra reached installed propose and failed opaquely, while Sol was rejected before authoring by the supported-success guard. A fresh retained Astra public control and full immutable release qualification remain required before sealing a new holdout; the Sol comparison is not a release gate.

- Fresh Retained Public Control (2026-09-27): Immutable build `76548dc22f782f77e538d30c45b80d72bcbc3be1` passed the new disclosed `public-v32-harbor-sample-relay-001` control on its first and only Astra-medium attempt. The retained result reports one host invocation, one proposal invocation, verified reviewer custody, zero issues, a `10/10` automated contract score, 4 Radar workstreams, 4 Registry components, 5 Atlas sources, 10 Atlas renders, 14 trace nodes, 5 implementation prompts, and clean desktop/mobile normal, empty, degraded, error, and invalid-recovery browser proof. Proposal time was `128.096s`, inside the `165s` model window and `180s` operational limit but above the advisory `90s` standard target. Retained evidence manifest verification passes with no issues at `/private/tmp/odylith-v32-public.DG2npZ/astra-evidence/retained-evidence-manifest.v1.json`. The same pass exposed one repeatability defect still owned by CB-347: `greenfield_preconfirm_matrix.py` correctly requires exact host-native argv plus external evidence for release proof, but `bin/greenfield-preconfirm-matrix` and the campaign shard command do not forward that contract. Fix the maintained entrypoints before full qualification; do not bypass them with a second interpretation path, retry, fallback, or model ladder.

- V32 Independent Re-adjudication (2026-09-27): The transaction/security reviewer independently matched all `185` retained artifacts and all `114` sealed repository files and found no P0/P1 transaction defect. Semantic and UX reviewers nevertheless blocked release on product-quality and proof-oracle defects: missing actionable handoff/signature verification, empty proportional risk posture, repeated Radar copy, visible subjectless first-path fragments, false one-day-back Radar dates, ephemeral retained navigation, temporary-path traceability output, and no per-diagram mobile-readability proof. The automated `10/10` and aggregate browser pass therefore overstate release quality. CB-303 owns the semantic/projection corrections; CB-347 owns wrapper forwarding and strengthening retained/browser evidence so these classes cannot score as complete.

- Prevention: Version evaluator schemas with the canonical receipt contracts and make package preflight execute the same policy validator as the release harness before a ledger can be sealed.

- Agent Guardrails: Do not interpret evaluator-invalid P0/P1 output as product semantics, do not relax semantic floors, do not patch protected cases, and do not add retries, repair, fallback authors, parser rules or regex classifiers.

## V33 Source-Local Harness Closure (2026-09-27)

- The maintained matrix paths now preserve the one exact host-native argv and
  retained-evidence contract. Passed compiled cases require the canonical
  transaction, compiler receipt, active publication, and immutable generation
  manifest to exist and agree by identity and hash. Operator results expose a
  durable retained Project route, and Chromium proves it after workspace
  teardown.
- The final-holdout child now acquires its lease and atomically claims and binds
  exact protected hashes before opening protected corpus, annotation, or lower
  control content. Every post-claim failure terminalizes the ledger. Synthetic
  ordering and interruption proof passes `68/68`; the real protected holdout
  remains untouched.
- Browser proof now exercises responsive normal, empty/fallback, degraded,
  error, and invalid-recovery states, including real mobile Atlas touch/pointer
  movement. Generated-tree scanning rejects simulation/prewrite root leakage.
  The installed customer guidance also returns below its byte budget at
  `16,906` bytes without weakening the current candidate contract.
- Source-local release proof is green at `1,826/1,826` fast, `292/292`
  lifecycle, and `1,745/1,745` install tests. Independent transaction review
  reports no P0/P1. CB-347 stays open until the complete immutable distribution,
  public matrix, clean-install/browser/recovery proof, and final adjudication
  pass; no harness score alone qualifies Greenfield.

## V33 Public/Final Proof Boundary Recurrence (2026-09-27)

- Read-only inspection of the maintained campaign path proved that every
  `proof-tier=release` shard is still routed through final-holdout-only input
  requirements. The public campaign supplies its disclosed case files,
  matching audit, Luna clarification control, retained evidence, exact host
  argv, browser proof, and recovery proof, but
  `greenfield_preconfirm_matrix.py` unconditionally requires blinded
  annotations, an evaluation manifest, final-run ledger, implementation
  revision, and distribution provenance before provider invocation. Public
  audited qualification and protected final-holdout consumption are distinct
  proof phases; preserve their shared release floors without forcing public
  evidence through one-shot protected-input custody.
- The fresh disclosed lab control exposed a second harness violation. After
  its first host candidate failed installed proposal, the unconditional commit
  recovery lane invoked Astra again on the same source and authored a second
  candidate in `113.546s`. That second proposal failed for the same risk-graph
  class. A failed candidate is terminal and cannot become the seed for
  transaction recovery proof. Do not rerun authoring after a primary case
  failure. Recovery proof must run only from an already admitted sealed
  transaction, or report `not run` with the primary failure as its reason.
- Keep one campaign owner and one protected-holdout owner. Add an explicit
  proof-phase boundary rather than an alternate wrapper, then prove that public
  release shards reach the provider with audited repo-contained inputs while
  protected holdout shards still claim and bind their immutable inputs before
  opening them. Prove that a failed public case causes zero recovery host calls
  and zero writes. The protected final holdout remains untouched.

## V33 Public/Final Boundary And Terminal-Failure Closure (2026-09-27)

- The existing matrix owner now separates public audited qualification from
  protected final-holdout custody. Public runs receive an audited parent corpus,
  an exact-member live subset, and the repo-contained Luna clarification
  control. Protected-only annotations, manifest, ledger, revision, provenance,
  and claim-before-open requirements remain exclusively on the final-holdout
  path. Public proof therefore cannot consume protected inputs, while protected
  proof cannot bypass its immutable custody gate.
- Exact parent/subset membership has one shared deterministic owner. It rejects
  missing or duplicate IDs in either file, an absent subset member, and any
  member whose fields differ from its parent other than `source_file`. The
  duplicate membership checks formerly carried by separate preconfirm and shard
  paths were removed rather than left as competing interpretations.
- A failed primary candidate is terminal. The release result marks commit
  recovery and unavailable-provider checks `not-run` with the primary failure
  reason, makes zero secondary host/model calls, and performs no recovery write.
  Successful recovery remains limited to an already admitted sealed
  transaction. This is a terminal-failure rule, not a recovery retry or an
  alternate author path.
- Focused release-boundary/corpus/sealed-input checks pass `51/51`; focused
  public-entry, zero-secondary-call, and campaign checks pass `15/15`.
  Independent re-review found no P0/P1 after the shared-membership closure.
  No provider was called and neither public qualification nor the protected
  holdout was run. CB-347 remains open until a clean immutable distribution
  passes the full retained public matrix, clean-install/browser/recovery proof,
  and final independent adjudication.

## V36 Public Campaign Preflight Closure (2026-09-27)

- The first full retained public-campaign invocation stopped before a provider
  call because its disclosed ten-case subset contained no case satisfying the
  commit-recovery intersection: committed outcome, non-empty edited confirmed
  intent, and approved audit binding. The audited parent contained exactly one
  qualifying case, `release-accessibility-007-source`, but the live subset did
  not select it. The selector correctly failed closed; the fixture contract did
  not prove that recovery preflight was executable.
- The subset now selects that exact audited parent member and replaces one
  second committed member with `release-research-165-source`. This preserves
  ten source families, all five input styles, five committed and five
  clarification outcomes, and all eleven required stressors. The fixture test
  now executes the real recovery selector and requires case `007`, preventing a
  balanced-looking but operationally unusable release subset.
- A preceding invocation exposed a separate macOS entrypoint defect:
  `greenfield-matrix-campaign` defaulted to lexical `/tmp`, while retained
  evidence correctly rejects symlinked temp roots and macOS maps `/tmp` to
  `/private/tmp`. Both maintained Greenfield wrappers now physicalize only
  their hardcoded fallback when `TEMP_PARENT` and `TMPDIR` are absent. Explicit
  caller paths remain untouched and still fail closed on symlink crossings; no
  retained-evidence safety rule was relaxed.
- Focused wrapper, retained-evidence, public-subset, and recovery-selection
  proof passes `130/130`; the complete Greenfield install/release harness passes
  `1,257/1,257`. Fresh governance browser proof passes `144/144` across normal,
  empty/fallback, degraded/error, density, layout, sorting, and selection-race
  states. Both preflight failures occurred before model invocation and before
  protected-input access. Public qualification remains pending on a new clean
  distribution; CB-347 stays open.

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
