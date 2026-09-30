- Bug ID: CB-347

## Single-authority release-gate correction (2026-09-29)

The V49 live reviewer mechanism failed on terminal-event identity and was
retired. The replacement uses one host-authored complete canonical candidate;
deterministic validation and sealing perform no semantic/provider call after
candidate receipt. A detached strong review now qualifies only frozen release
evidence, not individual consumer transactions.

Adversarial review of the first detached release gate exposed three unsafe
paths: discovery-tier proof could be accepted as terminal, preflight deleted
evidence required for review, and a synthetic ledger could pass without exact
run/input/provenance binding. Dispatch also accepted arbitrary evidence paths.
The implementation now requires a HEAD-scoped persistent proof root, release-
tier terminal statuses, exact protected-input categories and hashes, retained
run-ID and manifest binding, verified distribution provenance, and dispatch-
time recomputation. Functional tests prove missing or failed review reaches
zero workflow-dispatch calls, while a valid bound review reaches one.

The focused gate suite passes 128 tests, the combined Greenfield suite passes
2,629 tests, and independent gate re-review finds no remaining release-bypassing
P0/P1. This is still not a release or Casebook closeout.
The public replay, 40-case campaign, independent semantic/UX qualification,
and untouched protected holdout remain open.

## V49 implementation and independent correction closure (2026-09-29)

Host contract v30, host-candidate format v16, and reviewer v17 implement the
bounded V49 ownership move. The author no longer emits accepted components or
responsibility citations. The existing independent review decision owns closed
component and constraint custody; deterministic projection and retained proof
reconstruct the unchanged final candidate and transaction authority. The V48
host-owned component path is removed with no compatibility route.

Pre-checkpoint independent review exposed two P1s. A source clause could
legitimately be both a product event and an operational constraint, but the
first V49 validator rejected the overlap. It now preserves both typed custody
rows, emits one identical final component responsibility, and rejects
cross-owner reassignment. Separately, the host contract allowed same-owner
events to reuse one citation even though downstream relations could not retain
distinct event identity. The public contract and canonical host projection now
require distinct, non-overlapping event citations and fail before review on any
reuse. Independent re-review closes both findings with no remaining P0/P1 and
confirms no parser, regex, repair, retry, fallback, or extra model stage was
introduced.

Fresh proof passes the complete frozen Greenfield frontier at 3,348/3,348 and
the committed end-to-end dual-role admission control. This is not release
qualification. The next gates remain a pushed immutable build, the one exact
public falsification replay, the unchanged 40-case public/browser/recovery
campaign, independent semantic and UX qualification, and only then the still
untouched protected holdout.

## V49 bounded component-custody decision (2026-09-28)

The architecture and evidence reviews select one bounded replacement for V48:
the existing independent reviewer owns a closed typed component-custody witness;
deterministic code validates and projects that witness into the unchanged
canonical component shape. The author retains source facts, typed events,
constraints, terminal identity, and provisional design, but no longer authors
accepted `components`, `additional_responsibilities`, or event responsibility
citations.

An admitted witness must provide exactly one responsibility for each
product-owned event, using that event's exact product-action citation, plus one
additional responsibility for each non-event, non-constraint responsibility.
Deterministic validation must bind every owner to an accepted title or internal
system, require citation containment and canonical source resolution, and
reject duplicates, cross-owner reuse, additional-responsibility constraint
overlap, and source-control citations before grouping facts into canonical
components. An exact product-event/constraint dual role retains both typed
custody meanings and one final component row. Product-owned
constraints remain V48's separate second projection. A denial or clarification
has no component or constraint custody and performs no projection.

This retains one author and one reviewer and adds no regex, parser, retry,
repair, fallback, compatibility path, or model call. Remove V48's host-authored
component/responsibility schema, host event-responsibility selection, automatic
event merge, author-facing component prompt, and proof compatibility path in
the replacement change. The release proof must reconstruct both reviewer-owned
projections in the same order. The exact public replay must advance past
`candidate.accepted_source.components` while retaining the four-to-five
component and five-or-more diagram output floor. A recurrence at the component
custody admission boundary or downstream component semantics across two
independent public examples stops this line of replacement work; do not create
V50 wording or rule patches.

## V48 live falsification (2026-09-28)

Clean pushed commit `6e8b7a834` passed independent review with no P0/P1/P2,
3,336 frozen Greenfield tests, 80 maintained browser-surface checks, governance
commit readiness, and the immutable multi-platform build. The one permitted
replay of `release-accessibility-005-source` then failed closed after one host
candidate and one independent review. No transaction or governed product write
occurred; the 40-case campaign did not start and the protected holdout remains
untouched.

The retained candidate hash is
`61c8bbd8055911ab98a93aa70e9abfa5a9de8be0c4c3240d752bb9d8ebc6618f`.
Reviewer path hash
`85541195fa16830f7b7a1bce1a7ee9f2ec2c23753f774422a19b846ccc62a4f0`
maps exactly to `candidate.accepted_source.components`. The reason remains
hash-only as
`a07222617475d32572f0a914ea65a09742d3707e44adb34eb9fad83194706f5a`;
do not infer its free text. The immutable result is retained at
`/private/tmp/odylith-v48-6e8b7a834-work.6JczWo`.

V48 is falsified for release use. Reviewer-owned operational-constraint custody
removed the V47 duplicate owner but did not eliminate the broader accepted
component-semantic disagreement. Do not retry V48, start the public campaign,
or add prompt wording, regexes, parsers, repair, fallback, or a model ladder.
Compare only bounded ownership changes that remove the remaining competing
component interpretation, with explicit deletion of the losing V48 path.

## V47 live falsification (2026-09-28)

Clean pushed commit `8c82bc52638b71d8d25695c4e2a3b353c12eede9`
passed independent review with no P0/P1/P2 finding, 3,326 frozen Greenfield
unit/install tests, 67 normal/fallback/degraded browser checks, and the complete
governance commit-readiness gate. Its immutable `0.1.15` distribution then ran
the one permitted replay of `release-accessibility-005-source`.

The single Astra-medium author completed inside the 150-second advisory target,
and proposal failed closed during the one independent review. The retained
candidate hash is
`e3ecfe9c0995a358101137402fac157dcb1397681084584e3ca9240ab6f1bf3b`.
Reviewer path hash
`a5bfc254382f6f75fb72fc33f188654ff5b73b21e2b61d12131c23778755fbe5`
maps exactly to `candidate.accepted_source.components[0].responsibilities`.
The reason remains hash-only as
`499b3d8957e2f4f008dc7f7de56eef172af923719b2934574f99e8937a94e9da`;
do not infer or reconstruct its free text. No transaction or governed product
write occurred.

V47 is therefore falsified for release use. Required typed custody narrowed the
failure from the generic components boundary to one component responsibility
array, but it still left product-constraint classification jointly owned by the
host author and reviewer. Do not add more schema prose, a phrase rule, regex,
parser, retry, repair, fallback, or deterministic all-title projection. Do not
rerun this case or start the 40-case campaign on V47. Compare one bounded
replacement that gives semantic custody to one existing model decision and
deletes the losing host-custody path; the protected holdout remains untouched.

Bounded comparison selects reviewer-owned typed custody for V48. Remove custody
from the host candidate entirely. The existing independent reviewer must return
one ordered typed custody witness for every accepted operational constraint on
admission; deterministic code validates complete cardinality and fact or
precedence bindings, projects only product-owned constraints, and revalidates
the final canonical candidate before any authority hash or transaction is
sealed. Denial and clarification carry no custody and perform no projection.
This uses the existing single review call and removes the losing semantic owner
instead of adding another stage. A recurrence at the same responsibility path
falsifies V48.

V48 is implemented as host contract v29, host-candidate format v15, and
reviewer v16. The host custody field, host projection, bounded revision module,
second-review path, five-call receipt approval, and release-proof compatibility
path are deleted. Admission receipts bind the exact unprojected review input and
the exact projected final candidate; retained release proof reconstructs both
hashes for host-native and participant-first lanes. The canonical transaction,
Product Intent authority, and post-confirm execution schemas remain unchanged.

Fresh proof passes 3,336/3,336 frozen Greenfield runtime/install/integration
tests and 80/80 maintained browser-surface checks. Independent review is PASS
with no P0/P1/P2 finding after forged-final-hash, boolean-index, ownership,
retry, fixture, and cross-lane controls were resolved. V48 is therefore ready
for an immutable build and the one exact public falsification replay; it is not
yet live-qualified, and the protected holdout remains untouched.

## V46 live falsification and V47 bounded custody decision (2026-09-28)

The clean immutable V46 checkpoint `858a9325c69404f81d1f0db829e18c2ffcc645a4`
passed the complete frozen Greenfield unit/install frontier (`3324 passed`), the
real browser matrix (`67 passed`), governance validation, and independent
bounded review. Its one permitted replay of public case
`release-accessibility-005-source` nevertheless failed closed after a successful
single Astra-medium host author call. Installed proposal returned code 2, the
independent reviewer denied the candidate, and no transaction or governed write
occurred.

The retained reviewer path hash maps exactly to
`candidate.accepted_source.components`. The reason is model-authored free text
and was retained only as a hash; it cannot be recovered from repository truth,
so this record does not invent a missing clause or claim that the deterministic
projection failed. The live evidence proves only that nullable
`product_owner_fact` did not eliminate the accepted-component custody failure
class.

Retain typed constraint custody, but remove the nullable escape hatch. Replace
it with one required discriminated `constraint_custody` value: `product_owned`
with a title/internal-system owner, `participant_only` with an accepted human or
external actor, or `workflow_order` with an existing precedence binding. Only
`product_owned` projects into the existing canonical component-responsibility
relation. The other variants remain globally accepted constraints and do not
create component ownership. This is one relation refinement, not a parser,
regex rule, repair, retry, fallback, model ladder, reviewer weakening, or second
canonical interpretation.

Falsifiable release prediction: the exact public case must classify the
certification and draft-privacy constraints as product-owned by the title, the
reviewer-only disposition restriction as participant-only, and must advance
past the accepted-components denial. If the same path recurs, this mechanism is
falsified and must be removed or replaced rather than patched with more prompt
text. Do not rerun the case until the refined contract passes focused proof and
independent review on a new immutable checkpoint.

Implementation uses host contract v28 and host-candidate format v14. The old
wire field and nullable branch are removed rather than accepted through a
compatibility path. Test fixtures must now declare otherwise-unowned custody
explicitly; they no longer select the first available actor. Focused contract,
reviewer, cross-domain, parser-retirement, integration, and local-release proof
passes 198 tests. The complete frozen Greenfield runtime/install frontier passes
3,326 tests. Reviewer v15, canonical authoring v76, the transaction schema, and
post-confirm execution remain unchanged. Ownership now explicitly takes
precedence over temporal form: a product-owned obligation remains product-owned
when it also backs source precedence, while `workflow_order` is limited to pure
event ordering. Installed-release smoke pins contract v28, format v14, and the
exact non-null nested custody selectors. Independent read-only review reports no
P0/P1/P2 finding, and the frozen browser matrix passes 67 checks across normal,
fallback, and degraded states. Immutable-build replay is still pending, so the
bug remains open.

## V45/V46 typed operational-constraint ownership correction (2026-09-28)

The V44 prompt-only dual-custody correction did not qualify. An exact immutable
replay of the first failed public commit case from clean commit
`1a36b0ec544b67a6981fef90c625eb84ecb9f0cf` completed its single Astra-medium
author call, then failed closed during installed proposal with no transaction
or governed product write. The retained replay outcome names only the generic
nonzero host-native proposal result; its raw reviewer reason was not retained,
so this record does not assert a more specific V45 rejection cause.

V46 replaces prompt-only duplication with a typed host-boundary custody fact.
Every host-authored operational constraint now carries a required
`product_owner_fact`: either an exact `title` or `internal_systems` source
location, or `null` only for an accepted human/external-only restriction or a
workflow-order constraint. A non-null fact projects deterministically into the
existing canonical component-responsibility relation. Source-custody,
fixture, candidate, and authoring controls remain excluded from accepted
product facts, and an operational constraint cannot be duplicated in
`additional_responsibilities`. The canonical transaction shape and reviewer
v15 remain unchanged.

The host contract is v27 and host-candidate format is v13. Denied-review
telemetry is now observation v4: it retains only hashes for reviewer path and
reason, never untrusted raw diagnostic text. Focused implementation proof
passes 337 tests, and independent bounded review passes 375 focused tests with
no P0/P1/P2 finding. This is not release qualification: a fresh immutable
exact public replay remains pending, followed by the unchanged public campaign
only if that replay passes. Do not restore prompt-only wording, parsers,
regexes, retries, repairs, fallbacks, alternate model ladders, or a second
canonical interpretation.

## V44 product-constraint owner-custody mismatch (2026-09-27)

The first commit case in the fresh 40-case public operating-envelope campaign
failed closed after one Astra-medium host author completed successfully. The
candidate preserved the source clause requiring draft evidence to remain
private in `facts.operational_constraints`, provisional component design,
risk, acceptance, and verification. It omitted that separately worded clause
from the title-owned accepted component responsibilities, so independent
review correctly denied the candidate at `candidate.accepted_source.components`.
No transaction or governed product write occurred.

The failure exposes author/reviewer contract drift, not a parser or reviewer
defect. Reviewer v15 already requires every constraint explicitly bound to the
requested product to retain owner-bound accepted custody. Host contract v25,
the participant-first authoring prompt, and the component schema describe
additional responsibilities and capabilities without stating that a
product-governing operational or safety constraint needs both global
constraint custody and owner-bound component custody. Provisional design is
not a substitute for either accepted role.

Align those existing authoring descriptions and bump their semantic contract
versions. Keep human-only restrictions and transaction/source-custody controls
out of product component ownership, and continue deriving typed product-event
responsibilities without duplicate citations. Add positive and negative
contract controls, replay the exact failed public case on a fresh immutable
build, then rerun the unchanged 40-case campaign only if that replay passes.
Do not add a parser, regex, vocabulary rule, retry, repair, fallback author,
schema field, model ladder, or reviewer exception.

V44 source correction: host contract v26 and canonical authoring v76 now make
that dual custody explicit while candidate-review v15 and its prompt remain
byte-unchanged. The participant-first contract separately preserves one
canonical responsibility citation across component and event relations, while
the host shape continues to derive exact event responsibilities and excludes
them from `additional_responsibilities`. Positive and negative projection
controls prove product-constraint dual custody, human-only exclusion,
authoring-control exclusion, and exact event deduplication. Focused proof passes
179 tests, the complete Greenfield runtime frontier passes 2,017 tests, the
Greenfield install frontier passes 1,298 tests, and independent bounded review
reports no P0/P1/P2. Live closure still requires a fresh immutable-build replay
of the exact failed public case.

## V43 maintained matrix invocation recurrence (2026-09-27)

Final release-path inspection found that `run_matrix()` correctly rejected an
empty host-candidate command, while the direct maintained wrapper emitted the
canonical 14-argument host command only for terminal release intent. The
ordinary `release-candidate` discovery path therefore reached the same matrix
without the mandatory one-host authoring contract and could never complete
honestly.

The wrapper now obtains the command once from the existing canonical argv
owner and forwards it for both discovery and terminal release proof. There is
no second grammar, provider, retry, repair, fallback candidate, or model
ladder. A direct wrapper regression proves all 14 arguments reach the
discovery controller, and the focused release-wrapper/campaign/host suite
passes 91 tests; the complete changed-test surface passes 1,216 tests.

## V43 browser differentiation proof gap (2026-09-27)

The deterministic Greenfield browser gate exposed two release-proof defects.
Its desktop and mobile Project checks still expected the superseded `Source
excerpt:` label even though current runtime and package truth consistently
render `Accepted evidence excerpt:`. Separately, the installed browser runner
measured the number of distinct Product Story bodies but never rejected a
repeated body, so five rendered cards could satisfy the release gate while
repeating canonical meaning.

Align the browser expectation with the accepted-evidence presentation contract
and fail the per-generated-case gate unless all five Product Story bodies are
distinct. This changes only proof ownership; it does not add prose generation,
parsing, regexes, repair, retries, or another quality mechanism. The complete
focused browser matrix now passes 123 tests across desktop/mobile normal,
blank, degraded, handoff, Atlas, retained-route, no-program, and completion
opening behavior.

## V43 audit predecessor-custody self-link (2026-09-27)

Independent checkpoint review found that the regenerated source-verification
manifest named its own current path as `rebound_from` while carrying the hash
of an unretained predecessor. The final audit still loaded because lineage
metadata was not part of the repository fixture proof. This made the review
chain impossible to reproduce even though every current source response and
case binding remained valid.

Retain the original 41-file verification artifact under a distinct immutable
path, rebind the current manifest from that artifact, and require the declared
predecessor path to exist, differ from the current manifest, and hash exactly
to `rebound_from_sha256`. Regenerate the final audit bundle from the corrected
manifest so every one of its 40 review-evidence paths names the durable v16
directory. Focused audit proof passes 77 tests. Do not omit, rewrite, or infer
lineage merely because current evidence independently validates.
Independent re-adjudication verified all 40 predecessor records and all final
source/review paths and reports no remaining P0/P1/P2 in this slice.

## V43 release-proof ownership debt (2026-09-27)

Independent checkpoint review found two structural release blockers after the
behavioral P0/P1 findings were closed. The commit-recovery proof grew to 1,324
lines while mixing orchestration with retained evidence materialization, and
the clarification test module reached 1,535 lines. Both exceed the maintained
source or test limits and make the next release repair harder to attribute.

Close this debt before the checkpoint. Move one real recovery-proof phase to a
focused owner with no compatibility wrapper, alias wall, duplicated coercion,
or changed public behavior. Split clarification tests by semantic proof
ownership while preserving exact collection and assertions. Require the
focused recovery and clarification suites, source compilation, collection
equality, line-count enforcement, and a clean diff check. This is structural
convergence only; it must not add a parser, regex, model call, retry, repair,
fallback, or alternate release interpretation.

## V43 retained completion-handoff recurrence (2026-09-27)

The retained release package validates and preserves the committed Project
dashboard, but its operator result exposes only a machine-oriented navigation
row. The immutable `commands/decide.stdout` transcript truthfully retains the
temporary consumer-session URL and must not be rewritten after capture. Once
that temporary workspace is removed, the release result therefore lacks one
explicit transaction-bound handoff to the durable retained dashboard even
though the underlying bytes and route are valid.

Project a completion handoff only after the retained manifest, same-case
semantic bindings, and navigation row validate. Bind it to the sealed
transaction hash and absolute retained Project route already owned by the
manifest. Preserve the raw transcript byte-for-byte; do not parse it, add a
regex, introduce another renderer, or change the real consumer completion
handoff. Any retained-evidence failure must suppress the completion claim.

## V43 public audit-plan topology mismatch (2026-09-27)

The independently reviewed 40-case operating-envelope subset cannot currently
produce a valid audit bundle. Its request plan names the disclosed subset as
the source case file, while release provenance correctly requires the
`source-provenanced-discovery` parent corpus. Rebuilding the plan from the
parent alone selects a different deterministic sample and discards the exact
reviewed operating-envelope membership.

Keep the 200-case parent as audit source truth. Extend the existing audit-plan
writer with one optional, explicit selection file that must declare the
disclosed-subset claim, name that parent, contain exactly the requested count,
and pass the existing exact parent-membership validator. Bind the selection
path and digest into the request plan. Do not weaken the audit loader, relabel
the subset, add a second selector, or replace independent reviews.

## V37 clarification-oracle and replay-custody defect (2026-09-27)

The retained V37 campaign executed three clarification cases correctly: each
returned the canonical `first_path` question, performed zero writes or child
subprocesses, left no staged transaction, and preserved the before/after
governance record count. Release scoring nevertheless failed all three because
the disclosed live subset carried no independently frozen clarification
annotations. The evaluator correctly refuses to infer its oracle from the
observed model output; the fixture and preflight contract were incomplete.

The bounded repair adds one case-ID-bound `expected_clarification` annotation
for every disclosed clarification case while keeping the audited parent bytes
and provenance hashes unchanged. Source-case membership remains exact after
excluding only evaluation metadata, which is validated separately before any
provider invocation. Shard and failed-subset replay serialization must retain
`expectation` plus clarification-oracle custody; V37 dropped those fields and
therefore cannot serve as a faithful replay input. Reject missing, duplicate,
orphaned, incomplete, and commit-case annotations before execution. Do not
weaken the evaluator, self-score from observed output, or add a model call,
retry, repair, fallback, parser, or regex rule. V37 remains evaluator-invalid
and receives no release credit; its no-write receipts remain positive product
behavior evidence only.

V38 repair proof (2026-09-27): Case loading now rejects malformed fields and
unbounded or non-question oracle text, release membership rejects missing or
commit-case oracle data, and shard serialization rejects clarification cases
whose complete oracle custody is absent. Independent review found and closed
the initial shard fail-open path before checkpointing. Current proof includes
112 corpus/shard tests, 977 non-provider release/install tests, and 292
lifecycle tests, all green. A fresh failed-subset replay is still required;
the protected holdout remains untouched.

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

## V49 Immutable Public Replay And Diagnosability Boundary (2026-09-29)

### Separately bounded replacement decision

- An independent mechanism comparison selected one live semantic authority:
  the active host authors one complete canonical candidate, deterministic code
  validates and seals it, and explicit human confirmation controls publication.
  Strong independent semantic review moves to immutable release evaluation and
  no longer participates in consumer transaction admission.
- Same-model self-review loses because it still creates two stochastic semantic
  decisions and a serial latency tail. Ensembles lose on latency, cost, and
  arbitration. A learned classifier has no sufficiently broad independently
  labeled relation corpus and would turn visible disagreement into opaque
  overfitting.
- The change must delete reviewer custody, reviewer receipt authority, and the
  dead participant/remainder/join path rather than retain a compatibility mode.
  Runtime semantic-model calls after candidate receipt must be zero. Existing
  citation, relation, transaction, confirmation, rollback, recovery, browser,
  and detached release-review invariants remain fixed.
- The exact public case gets one fresh replay only after focused controls, the
  full frozen frontier, independent patch review, and immutable build. Failure
  retires this replacement with no follow-on prompt/schema patch; Greenfield
  then remains preview-only or leaves the production release claim.

### Terminal replay result

- Clean pushed commit `9c8bb2433ca3da7d92b4fbf6486d9e6ba2996b62`
  passed the final 3,362-test frontier and independent no-P0/P1/blocking-P2
  review, then built the complete multi-platform `0.1.15` distribution with
  platform-domain leakage proof.
- The one permitted installed replay of `release-accessibility-005-source`
  failed closed during independent review after a successful host candidate.
  The campaign stopped after one case; no transaction or governed write
  occurred. Total elapsed time was `190.726s`, including fresh installation.
- Denial path hash
  `327b80167f67d9661aebf04b3b9af6a1372050ad6f0e92bb214561263e852978`
  resolves exactly to `candidate.accepted_source.terminal.event_order`.
  The reason is retained only as
  `584acdda66a8137b4efb7a8da67b72755fef9453292acd46dce44fbdc84413ff`;
  no narrower semantic diagnosis is justified.
- This is the terminal falsifier for the one-author/one-full-candidate-reviewer
  composition. The disagreement migrated from responsibilities, components,
  and precedence to another accepted-source relation after complete relation
  consolidation. Do not add another field migration, prompt/schema patch,
  parser, regex, repair, retry, fallback, or model ladder, and do not rerun the
  public case under this mechanism.
- Evidence:
  `/private/tmp/odylith-v49-9c8bb2433-replay.5xHt1j/public-replay.v1.json` and
  `/private/tmp/odylith-v49-9c8bb2433-replay.5xHt1j/telemetry/failed-subset/failed-subset-failed-subset-001-cases.telemetry.v1.jsonl`.

- Clean pushed commit `8278cce69282cc4cde54c38bcdefe4dd95869d8c`
  passed `3,348/3,348` frozen Greenfield tests and independent no-P0/P1 review,
  then built the complete `0.1.15` distribution with platform-leakage validation.
  Its first and only exact replay of `release-accessibility-005-source` failed
  closed after a successful Astra-medium host candidate and an installed
  independent-review denial. No transaction or governed product write occurred;
  the campaign stopped immediately and neither the 40-case public campaign nor
  protected holdout was opened.
- The discovery evidence resolves the denial path exactly to
  `candidate.accepted_source.source_precedence`, but preserves the model-authored
  reason only as SHA-256. That is sufficient to reject another author prompt:
  author-owned precedence has already failed as a plain array, a typed global
  choice, and constraint-co-located typed relations. It is not sufficient to
  claim the reviewer reason was correct, so the next mechanism must carry an
  explicit passive/unowned timing falsifier rather than infer the hidden reason.
- The bounded forward fix consolidates accepted-source relations under the one
  existing reviewer: host authoring retains atomic cited facts, events, terminal
  identity, and provisional design; reviewer custody owns components,
  constraints, and source precedence; deterministic code validates and projects
  all three into the unchanged canonical candidate. Precedence projection must
  occur before `workflow_order` custody binding and final first-run validation.
  No retry, repair, parser, regex, fallback, extra model call, transaction
  mutation, or compatibility field is allowed.
- This hypothesis has one terminal gate: a passive unowned timing control must
  produce no invented edge, an explicit accepted-event ordering control must
  produce its exact cited edge, and the accessibility public replay must advance
  past precedence in one attempt. A recurrence retires this ownership line; it
  must not trigger another field migration or prompt/schema cascade.
- Evidence:
  `/private/tmp/odylith-v49-8278cce69-replay.z2jiwA/public-replay.v1.json`,
  `/private/tmp/odylith-v49-8278cce69-replay.z2jiwA/telemetry/failed-subset/failed-subset-failed-subset-001-cases.telemetry.v1.jsonl`,
  and immutable distribution
  `/private/tmp/odylith-v49-8278cce69-dist.uRQK9e`.
- The bounded consolidation is implemented as host contract v31,
  host-candidate format v17, and reviewer v18. Host candidates no longer carry
  `source_precedence`; the existing independent review returns one closed
  `source_precedence_custody` witness, and deterministic code validates and
  projects it before constraint custody and final first-run validation.
  Retained proof binds distinct review-input and projected-final hashes without
  exposing private reviewer text.
- The final frozen Greenfield frontier passes 3,362/3,362 tests in 337.71
  seconds. An earlier integrated pass found 13 stale fixture-ownership failures
  after 3,349 passes; all 13 were corrected without changing production
  semantics, and their exact rerun passed 13/13. Independent review then caught
  and closed a false passive-timing proof fixture and a model-facing
  prompt/schema contradiction; the final adjudication reports no P0, P1, or
  blocking P2 finding. The live blocker therefore moves from internal
  consistency to one immutable public replay. Failure at that replay retires
  this mechanism line instead of reopening prompt or schema churn.

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
