- Bug ID: CB-347

## V42 resumed CI freshness boundary (2026-10-08)

CI `37507903773` fails five assertions after 10,036 passes and 10 skips in
71m06s. Independent review classifies all five as stale tests: one retired
`inferredWithinLane` lifecycle expectation and four empty-component browser
cases expecting the removed “Named responsibility” fallback. A bounded two-test
correction passes the lifecycle assertion once and the four Atlas assertions
once. A successor hosted CI is still required; no current CI pass or release
credit follows. Preserve V41’s 44 native browser passes as prior evidence only.
Logs: `/private/tmp/odylith-resume-ci-37507903773-20261008.log`,
`/private/tmp/odylith-ci37507903773-lifecycle-correction-20261008.log`, and
`/private/tmp/odylith-ci37507903773-atlas-correction-20261008.log`.

## V41 Public40 failure boundary (2026-10-06)

Executed four of 40 Public40 cases: two clarification cases pass, two cases
fail, and 36 remain unexecuted; no controls run. Independent review identifies three
release-harness P1s: stale Validation heading, labeled-citation false positives,
and initial confirmed intent routed to EDIT. Preserve each case outcome and do
not call a product semantic pass. B-145 remains unfinished until current proof
and its canonical gate close. Evidence:
`/private/tmp/odylith-v41-public40-campaign-handoff-20261006/actual-campaign-outcome.v1.json`
and `/private/tmp/odylith-v41-public40-case2-case4-independent-review-20261006/report.md`.

## V41 migration-gate admission boundary (2026-10-06)

The installed-v41 evidence chain is assessment-ready, including 44 native
browser passes and consumer preservation, but the canonical predecessor-bound
gate remains blocked until B-145’s migration-observer markers are admitted by
its owning workflow. The attempted scoped Radar refresh refused on managed
publication drift without writing. No Compass append, migration completion, or
release credit follows. Gate receipt:
`/private/tmp/odylith-v41-b145-final-migration-gate-20261006.json`
(SHA-256 `d2c92ae44aa96ed07e77eb9a8a68cc3e0a69769b32252facd15321421ab23334`).

## V41 installed package, adoption, and browser evidence (2026-10-06)

Clean candidate `2f9` package mechanics pass. A native v0.1.14-to-v0.1.15
upgrade passes, deterministic installed adoption covers 20 workstreams, and the
browser chain reaches 44 native passes/zero failures with consumer preservation.
Synthetic Project UI2 remains supplemental only. This evidence may support the
B-145 migration gate, but current CI, Public40, native Claude, original holdout,
and full release remain open.

## V41 Radar measurement-race correction (2026-10-06)

Independent diagnosis classifies the sole CI failure as a measurement race, not
Radar product behavior. The two affected resize cases now pass in 3.89s while
product Radar remains unchanged. Preserve the failed CI and all other gates;
this focused proof does not clear CI or release status. Evidence:
`/private/tmp/odylith-v41-radar-atomic-measurement-20261006.log` (diagnosis
SHA-256 `8a27d3ed85d78a0d31773dd7380908132cee56c4cfc2462ca5dee5727e7e9cc6`).

## V41 active-owner fixture proof and current CI boundary (2026-10-06)

The supported active-generation/source-owner fixture now passes two publication
crash tests in 90.09s with atomicity and conservation oracles retained. Root copy
checks remain 137 pass/two fixture fail as history. Current CI `37495747429` at
`5303` is still failed (`10,051` pass, one fail, 10 skip): a visible-selection
Radar resize case raises `Locator.evaluate` TypeError because `closest('#list')`
returns null during rerender. Diagnosis is pending, so do not classify product
versus test cause or mark CI clear. B-145, Public40, final holdout, native Claude,
and native Project-degraded proof remain open. Evidence:
`/private/tmp/odylith-v41-publication-fixture-active-owner-correction-20261006.log`
and `/private/tmp/odylith-v40-current-ci-failure-20261006.log`.

## V41 active-publication fixture correction boundary (2026-10-06)

The immutable-bundle hypothesis remains failed: two tests fail in 31.93s before
baseline/crash phases because dynamic tooling payload is missing. The fixture must
use the supported published asset owner: `read_active_publication(SOURCE)`;
without one it uses ordinary SOURCE, and with one it calls
`pin_active_greenfield_generation(SOURCE).repository_root` once. Invalid active
publication or pin fails closed; do not mix or fabricate payload fallback. The
selected root supplies entry, server, URL containment, copies, and source hashes,
while SOURCE/src remains the current compiler-import owner. Preserve all
publication, crash, conservation, and atomicity oracles. Evidence: failed log
`/private/tmp/odylith-v41-publication-fixture-correction-20261006.log` (SHA-256
`f4451aa2…`) and review
`/private/tmp/odylith-v41-final-patch-independent-review-20261006/review-v2.json`
(SHA-256 `d4af0bd306571fdeaaac03c30e57d5b0e7212557bb7bb204b61e4f9cf593c610`).

## V41 publication fixture asset-closure failure (2026-10-06)

Copy verification records 137 pass and two fail before baseline compilation or
crash injection. The test fixture’s `_asset_closure` reads the physical published
root index wrapper and copies its generation-relative dependencies, then expects
canonical `odylith/registry/registry.html`. Build closure and relative copies
from immutable `src/odylith/bundle/assets` instead. Preserve source subprocess
imports and all six-surface, publication, crash, source-conservation, and
atomicity oracles. This is not a product regression or lazy-proxy-order issue;
do not reset wrappers, repair consumer/source, weaken admission, or retry the
fixture. Evidence: `/private/tmp/odylith-v41-publication-browser-local-failure-diagnosis-20261006/diagnosis.json`
(SHA-256 `2e6815fb5f38746f381f32f7ab4cdf9208634b80ccbe331a5f9e0af4f6f72064`).

## V40 installed-browser Registry adapter boundary (2026-10-06)

The v40 installed matrix records 40 pass, two Registry failures, and two native
Project-degraded holds. Registry raw source Markdown correctly retains backticks
in closed Topology, while the external adapter's exact-text oracle omits them;
the source guard correctly suppresses controlled registration scaffold. Correct
the future adapter with verbatim raw-field comparison only. Do not call this a
Registry product regression, relabel v40 failures, or replay the frozen matrix.
Native Project-degraded holds receive no synthetic credit.

## V40 unpublished Compass-stream publication refusal (2026-10-06)

Selective authored publication refused before a successor because the sole
unselected managed divergence is three unpublished `ambient_signal` hook records
in `odylith/compass/runtime/agent-stream.v1.jsonl` at `2026-10-06T15:02:02Z`.
Archive the exact raw stream and diff, then preview and apply restoration only
for that stream before reviewed authored publication and one meaningful Compass
implementation append referencing the archive. The hook candidates are immutable
external history, not chat or source proof; do not replay models or disable an
engine. Evidence: compiler delta
`/private/tmp/odylith-v40-final-source-freeze-20261006/refused-unselected-delta.json`
(SHA-256 `f47e6d3b2943a9e80ad72ad2e19c9da6e93dae0fc9685f842d52ba636ac0960a`)
and failed publication log (SHA-256
`2c10705ad0ac5cf4f29babd2b74fca4d640fdea185e402899b1ced70ddf68c48`).

## V40 test-order and future-browser helper proof (2026-10-06)

The CI proxy-order test correction passes 103 paired-order and adjacent checks
without changing real admission, publication, refusal, custody, Registry mapping,
or validation. The future installed-browser helper passes 94 tests with one added
line at 1,200 LOC; its external adapter is HELD with zero execution. The failed
current CI at `73d` (10,036 pass/one fail/10 skip) and v39 matrix (26/16/2)
remain history, not superseded installed credit. Evidence:
`/private/tmp/odylith-v39-authored-sync-ci-test-fix-20261006.json` and
`/private/tmp/odylith-v40-installed-browser-future-predispatch-20261006/handoff.json`.

## V39 Project spotlight timing diagnosis (2026-10-06)

The matrix remains `26 PASS`, `16 FAIL`, and `2 HELD`. The first assertion reads
bootstrap `version_story {}` at 7.945ms, before asynchronous generation redirect
DOM at 34.773ms and payload at 50.047ms; its selected-three-highlights oracle is
valid. Failure before Close leaves the modal open and cascades 16 failures.
Actual Close works in the root’s 12 read-only review captures. The bounded remedy
is for the shared obstruction helper to wait for settled document before checking
visible Close, and for the external adapter to wait for generation payload before
version/spotlight checks and finally Close after a failed assertion. No fake time,
model, consumer repair, or oracle weakening. Evidence:
`/private/tmp/odylith-v39-project-spotlight-diagnosis-20261006/diagnosis.json`
(SHA-256 `ecd74ddf4bc716bb330f1e4d4012a955f1b7e2290e2a32dc471ac61e3965f687`).

## V39 current CI proxy-patching failure (2026-10-06)

Current CI `37480920778` at `73d1555` fails one test (`10,036` pass, `10` skip)
after 49m13s. The cause is test order: an earlier install test patches the lazy
CLI proxy `cli.sync_workstream_artifacts.main`, then teardown restores a concrete
original on that proxy. The later admission test patches the underlying module,
misses the proxy attribute, and real sync runs against a fixture missing
Traceability. The paired order reproduction is one pass/one fail. Patch only
the actual CLI proxy in the test; retain real admission, publication, model
refusal, custody, Registry mapping, and validator behavior. This is not CI-pass
credit. Evidence: `/private/tmp/odylith-v39-authored-sync-ci-paired-repro-20261006.log`;
current failed log `/private/tmp/odylith-v39-current-ci-failure-20261006.log`.

## V39 installed browser-matrix failure boundary (2026-10-06)

The actual v39 installed matrix records `26 PASS`, `16 FAIL`, and `2 HELD`
across 65 screenshots. Its first Project assertion ran before modal Close, and a
later backdrop click was intercepted; the browser owner is still diagnosing the
exact cause. Do not call Product non-regression, R3 PASS, or replay from this
result. Preserve the failed matrix at
`/private/tmp/odylith-greenfield-v14-to-v39-migration-20261006/upgrade-r3/final-installed-browser-matrix-handoff.json`
(SHA-256 `c46ad8a8…`), and retain R1–R3 history.

## V39 Casebook index-refresh regression (2026-10-06)

CI run `37464433347` at exact `11e3211` remains the historical 29-failure,
9,996-pass, 10-skip result. On final source/test bytes, all 29 original
signatures now reproduce as `29 PASS` in `6.90s`, with source pins unchanged.
The first collection-only reproduction is retained: one renamed test node meant
no tests ran and source remained unchanged.

The Casebook fix preserves the reader contract: direct sole-surface refresh
supports existing legacy-ID migration; selective, multi-surface, and upgrade
refresh update `INDEX.md` first without changing authored bug bytes or modes;
and malformed source stops later readers. Focused proof before unused-helper
removal covers 21 checks. The integrated runtime is net -95 lines with no new
modules. This is current-source regression proof only; fresh full CI, package,
installed, Public40, Luna, holdout, Claude, and release qualification remain
open. Evidence: final reproduction
`/private/tmp/odylith-v39-final-ci-regression-reproduction-r2-20261006/report.json`
(SHA-256 `579ba9a2ce21895b76b53781131af087dbb1f554959b165db53fe45e2373449a`);
retained collection-only attempt
`/private/tmp/odylith-v39-final-ci-regression-reproduction-20261006/report.json`
(SHA-256 `58ac4d99b93b8b12fdf9fe98d9ef806b84788903c36724f0c86f503984fbd3b2`);
and focused handoff
`/private/tmp/odylith-v39-casebook-refresh-focused-handoff-20261006/report.json`
(SHA-256 `2b423ec6549c026311f4dadb768fb2b383497af3798b972d4400ed658358ca63`).

## V39 temporal Casebook adapter correction (2026-10-06)

The existing Casebook helper and temporal adapter now match the actual invalid
selection and expiry contract: 16 focused checks pass across 27 bindings, with
no helper growth (the helper remains 1,199 LOC). R1, R2, and R3 failures remain
historical and this static proof is not an external browser pass or native-parity
proof. Evidence: `/private/tmp/odylith-greenfield-v14-to-v38-migration-20261006/upgrade/casebook-temporal-correction-static-proof.json`
(SHA-256 `97495204f601469ffc16296eb6ff214bc1b3c315a7f57621ccd22ef86313e7c4`).

## V38 package and migration witness boundary (2026-10-06)

Frozen candidate `11e3211` has a passing distribution result and a fresh native
v0.1.14-to-v0.1.15 upgrade witness. The upgrade renders six pages, preserves 15
source and three customer-owned files, and retains 13 owner identities. Installed
adoption also passes 20 workstreams and 88 source units. This advances bounded
package and upgrade evidence only; it does not complete B-145 or a release gate.

Two external browser-driver attempts earn zero browser credit: R1 hit a wrapper
surface/state collision and R2 lacks the required covered state. Both attempts
and the untouched 18,337-entry consumer are retained while one deterministic
binding audit runs. A supplemental installed synthetic Project UI proof has two
passes, but is not client-data credit. CI run 37464433347 remains in progress;
Public40, real Luna, native Claude, and the protected original holdout are still
unqualified or unavailable. No lifecycle completion or migration marker follows.
Evidence: distribution `/private/tmp/odylith-greenfield-v38-dist-20261006/proof/result.json`
(SHA-256 `aeb48292a56184ae8a02406cfe90bd7be9ef61da39a28dbe19b03140e56dd130`),
migration `/private/tmp/odylith-greenfield-v14-to-v38-migration-20261006/upgrade/final-migration-browser-handoff.json`
(SHA-256 `94f2e84992d36f77860f319131bf2fdf11cf98379c529bb530d86c43b882a801`),
and browser handoff `final-browser-r2-handoff.json` in that migration namespace
(SHA-256 `353268772e6eae4cbed6b6231e26396278e3fbceb4e20a697d9fe4e3020054b1`).


External R3 completes `36 PASS`, `6 FAIL`, and `2 HELD`, with the whole
18,337-entry consumer unchanged. Diagnosis attributes four notice cells to one
expired-notice assertion: the payload expires at `13:06:15Z`, and R3's
post-10-minute policy correctly hides it while the adapter asserts visibility.
The two Casebook cells wait for automatic active-row selection, although the
existing contract requires unknown query/status plus zero active rows before a
user clicks a valid record. Product UI remains unregressed, but R3 remains a
failed run. V49 owns the source Casebook-helper and external real-clock-adapter
correction; do not run a fourth attempt. This leaves external browser
qualification open without invalidating the bounded v38 package/adoption witness.
Diagnosis: `/private/tmp/odylith-greenfield-v14-to-v38-migration-20261006/upgrade/r3-six-failure-read-only-diagnosis.json`
(SHA-256 `97993fbd8448ffead5c4b433cac0977d9d4b89338c639cf7119d0f29f8b69064`).

## Successor Registry publication check (2026-10-06)

The guidance sync refused four new feature-history entries whose plan routes
were separated from their bullet lines. Keep each entry and its canonical plan
route in one paragraph so Registry validates the components. The failed sync
remains in `/private/tmp/odylith-cognitive-successor-guidance-publication-20261006.log`;
it provides no publication credit.

## V37 all-six upgrade refresh correction (2026-10-06)

The all-six upgrade refresh correction passes 240 source checks with no input
drift and independent CLEAR review. Upgrade refresh regenerates all six surfaces;
ordinary refresh remains the default three-surface path. Authenticated unfinished
upgrades preserve customer Casebook/source/INDEX modes, durable report then retire
its receipt, refuse stale or forged drift, and leave historical generations valid.
This resolves the bounded refresh ownership gap only, not installed qualification.
Preserve the earlier open-after-recovery report, published-before-report SIGKILL,
accidentally widened ordinary-three attempt, and missing immutable-pin finding.
Evidence: `/private/tmp/odylith-upgrade-all-surfaces-correction-20261006-nvascvna/independent-review-r6-final-20261006.json`
(SHA-256 `4231ab985ecfd1b0a23db736f4daf7fe542e01f9c0b5acdfb94cebfa64a8a00c`).

## V37 fixed-pair and release-gate boundary (2026-10-06)

The Research and Agriculture fixed H0/H1 pairs now pass their terminal controls.
The closure preserves the earlier failures and is limited to the declared
fixed-pair semantics, refusal/confirmation, sealed readback, and idempotence; it
does not qualify an installed semantic journey or release. Evidence:
`/private/tmp/odylith-v37-fixed-pairs-closure-20261006.json` (SHA-256
`740c03e44b44beb54f07a578047b93eceefdfdab27d8524cb942e52d41dc5724`).

Current CI at `111fc` still fails six tests (`9,956` pass, `10` skip). Four
closed-disclosure expectations, one duplicate-detail expectation, and one
incomplete fixture remain under separate fixes; preserve
`/private/tmp/odylith-ci-37448686338-diagnosis-20261006/failure-report.md`. The
six-surface upgrade correction is also pending: revision two passes 70 focused
checks, but a real ordinary post-success refresh still fails. Neither result
advances the release gate.

## Current v37 published-v14 migration witness (2026-10-06)

The subsequent selected-path census finds a separate migration ownership gap:
Casebook and Registry HTML/JS remain exact v0.1.14 after the upgrade even though
the target bundle and wheel are new. The upgrade renderer selects only
tooling-shell, Radar, and Compass. The bounded preservation/notice witness
remains valid, but this prevents class assessment completion. The first assessor
also used an invalid `--description` help assertion instead of `--what-it-is`
and lost stdout, so it earns no help credit. One retained runtime `.pyc` is
separate from the original 18,348-entry browser inventory and does not rewrite
that witness. Census and stopped assessment: `b145-selected-path-census.json`
(SHA-256 `b2a79e8616be3e021265279fc4a79e36af642bc91a9e81107a4dbf5219f853a5`) and
`b145-assessment-stopped.json` (SHA-256
`9197553152c7aa5fb4ee505d6e0691f707d590c67dbdf8289a96539e850609ce`) in the
v37 migration namespace.

A fresh native upgrade from published v0.1.14 to installed v0.1.15 returned
`RC=0` in `27.502s`. It preserved 14 of 15 raw source files and all 15 modes;
the only predeclared change is the existing Atlas
`render_source_fingerprint` leaf. Radar `INDEX.md` is byte/mode exact, 13 target
owners match across source, wheel, and installed readback, and the full consumer
inventory is exact before and after browser readback. The active wall-clock
release notice has a native Close control at desktop and mobile widths; two
positive linked-plan readbacks and 12 screenshots reported no issues.

This witness does not complete B-145. The earlier ambiguous start remains
`RC=1` with zero success credit; the v35 INDEX failure, v36 wrapper failure, and
clock-controlled follow-up remain historical limits. The five migration classes
and their markers remain open for separate class assessment, and no release,
semantic, host, holdout, or full-browser claim follows. Handoff:
`/private/tmp/odylith-greenfield-v14-to-v37-migration-start-routed-r1-20261006/handoff.json`
(SHA-256 `45d677ddbc988200a37c5e37e2c26521a1042a3afacfd0c890bd1cbd96f64af7`).
Independent review: `independent-b145-assessment-review.json` in the same
directory (SHA-256 `1a003527292ca609b5558c9e6020c0eed153b58c015debadc119ea5b5b04a085`).

## Current single-carrier transport and v36 proof boundary (2026-10-06)

The final authored-selective call mistakenly included the public release note.
Admission refuses before publishing a successor because that path is not one
of its five supported governance record kinds. Preserve
`/private/tmp/odylith-notice-transport-final-authored-admission-20261006.log`.
Select only the five changed Casebook/plan/Registry records for authored
admission; public release copy remains a separately reviewed product-doc change.
Do not expand or bypass the consumer authoring owner contract for this operation.

Selecting only those five records also refuses before publishing: the installed
release note differs from the sealed managed inventory. Preserve
`/private/tmp/odylith-notice-transport-final-authored-admission-records-20261006.log`.
Resolve the product-owned release-copy source and supported managed-asset
transition before retrying publication. The UI proof is intact; neither refusal
permits blessing a changed inventory or relaxing consumer byte preservation.

The maintainer coding standards designate that same note as the canonical
authored source and require its exact bundle mirror. The five-record consumer
admission omits this legitimate product-maintenance owner. The current decision
supersedes the initial five-record-only prescription above: add only the current
release-note route under existing product-repo and detached-source-local
authority. Bind source and mirror bytes and modes to both immutable preimages;
retain exact parity, existing note metadata, every other inventory check, and
compare-and-swap protection. Consumer and historical-note edits still refuse.
CB-305 rules out a general directory or bundle exception. Characterization and
independent review must precede publication. Publishing elsewhere does not fix
the in-place ownership gap.

The bounded owner is now implemented and independently CLEAR at source
SHA-256 `e38b6d4ff087e1d588b77c290b2872cf99aa03736188bd7cf0f635d83a80670f`.
Its existing module grows by 27 lines; 102 focused tests pass in 7.20 seconds.
The genuine two-copy publication fixture proves the current note and its exact
implicit mirror, alone and with five governance records. Consumer, pinned or
missing runtime, wrong version, historical or direct mirror selection, malformed
metadata, parity/mode/symlink drift, immutable preimage corruption, other inventory
drift, and final source/mirror and role/version races refuse. The CLI parser and
publisher test uses an explicitly synthetic post-admission sync callback and
does not prove root full sync. Preserve the 93-pass/four-fail characterization
and 101-pass/one-fail incomplete-backlog fixture. Final handoff and independent
report live in `/private/tmp/odylith-maintainer-release-note-authored-admission-20261006/`.
Canonical root publication and the next clean install remain required.

Exact pushed19bf CI run 37436166428 finishes with 13 failed, 9,906 passed and
10 skipped tests in 4,445.25 seconds. Identity and Claude asset smoke pass;
asset smoke does not prove native Claude parity. Preserve the complete failed
job log at `/private/tmp/odylith-ci-19bf-pytest-failed-20261006.log`. Ten failures
are browser adopters; three are unit adopters. The Registry digest resolves as
hidden within the new evidence disclosure, two Atlas tests read hidden content,
and the Compass VM stub lacks Element.closest. Two unit assertions still expect
the old lifecycle canvas copy and old owning-component heading. These are
diagnostic leads, not permission to remove fact, style, route or warning oracles.
Characterize each failure and verify native disclosure plus complete evidence
before changing stale presentation assumptions. Report any true product loss.
The 44-state source matrix and package smoke remain valid bounded proof, while
full checkpoint CI is failed and release qualification stays open.

The 13 exact failed signatures now pass focused current-source controls. The
Compass VM fixture models the real nearest details parent and verifies closed
to open on genuine unavailability; its complete module passes 11 tests. The two
Atlas unit adopters assert exact complete lifecycle descriptions and native
owning-component/linked-record disclosures. Ten browser adopters pass in 20.12
seconds: closed defaults are asserted, normal keyboard Enter opens the summaries,
and original evidence text, labels, styles, counts and route assertions remain.
Normal anchor clicks replace direct JavaScript clicks. Their neighboring Registry
Topology control initially exposes another hidden-default assumption; opening
that actual native summary preserves the original route proof and passes.
Root diff review finds no product edits, force clicks, observer weakening, or
removed semantic oracles. The old full CI failure remains failed; the next
immutable checkpoint still requires its own complete CI run.

At pushed checkpoint `19bf8ffb617d8d4650caf8677ee0304855fad5cf`, the bounded
44-state UX matrix, canonical publication, and eight commit-ready gates pass.
The clean v36 package builds in 164.685 seconds; all 12 checksums match and
canonical installed smoke passes in 363.160 seconds. This qualifies package
and lifecycle mechanics only; full CI is still running at that exact checkpoint.

The fresh published-v14 native upgrade passes in 27.580 seconds and preserves
all 15 required file modes and bytes, apart from the sole declared Atlas hash
leaf. The Radar INDEX is now exact. Target plan-binding/backlog validators pass.
The witness stops at its first target-browser wrapper failure: upgrade/run.py
names upgrade/browser.py, but the five-driver staging inventory placed the
unchanged helper only under predecessor/. No target renderer ran. Preserve
`/private/tmp/odylith-greenfield-v14-to-v36-migration-preflight-20261006/final-stopped-handoff.json`
(SHA-256 `a2c921b082c61f42f13fe021ddb45a9988f8c57934a5ed658768ea4170ee19ab`).
Dependency closure must check invoked support paths, not only five-driver hashes
and literal AST differences. A separately predeclared read-only continuation
may invoke the unchanged helper against the exact preserved installation; never
reinstall, re-upgrade, reseed, rewrite the STOPPED result, or count the missing-file
wrapper attempt as rendered browser proof. Full migration remains unqualified.

The separately predeclared target-browser continuation calls the actual helper
once and fails after 16.083 seconds: the visible shell upgrade spotlight backdrop
intercepts the Radar row click. There are zero target readbacks or screenshots.
All 18,348 consumer inventory entries and 13 installed owners remain exact;
the original STOPPED witness remains unchanged. Composite proof:
`/private/tmp/odylith-v36-target-browser-continuation-20261006/composite-phase-proof.json`
(SHA-256 `d6e183e12bab09496282805d75680d1e5d0bb78c37831f38a5f407e8c1adb31e`).
The normal visible dismissal path and helper timing must be diagnosed before any
product fix or new qualification run; an intercepted click alone does not prove
that the modal is undismissible. Keep the failed first renderer attempt intact.

Read-only diagnosis locates a driver arrival race: it calls the normal shell
obstruction helper on the entry redirect, whose DOM has no close control, before
the final immutable shell arrives. The helper checks count/visibility once. The
isolated diagnostic runs after spotlight expiry, so it does not prove active
native dismissal. Report:
`/private/tmp/odylith-v36-upgrade-spotlight-diagnosis-20261006/report.json`
(SHA-256 `39a3a62986b91993625e2760be4abd201154ef0b68b17ae1d8c94e283de6660e`).
Correct the external arrival order, retain the native spotlight and all click
obstruction assertions, and explicitly control the active browser-clock state
if qualifying that expired notice. Never pass by expiry, force-click or DOM removal.

The new corrected-arrival proof passes one renderer call in 3.003 seconds. It
waits for the final Radar frame, then uses the unchanged normal dismissal helper.
Supported Playwright fixed browser Date recreates the exact failed-visit instant;
the native active modal and Close are visible at both widths before dismissal,
and the backdrop is hidden before the original row click. Two original positive
plan/backlink readbacks pass with 12 screenshots. All 18,348 consumer entries,
13 managed owners, and 15 preserved files remain exact; CLEAN19bf is clean.
Proof SHA-256 `d7a567fab9f9599f3e439c82957df75a44aa2932c5e201f6fb53cd2396cbabfe`:
`/private/tmp/odylith-v36-target-browser-arrival-proof-20261006/proof-result.json`.
Composite SHA-256 `6acc7f41382d88aa5d8e3cbaabc9bdf0082d140564758d537ab0684fd66b6459`.
This is a separate controlled-time browser result; the original STOPPED witness
and first renderer FAIL remain unchanged. It does not qualify current-clock,
normal/empty/degraded matrices, semantic reliability, or the release. Root visual
inspection finds notice presentation pressure, now captured in CB-303; mechanics
success must not suppress that human readability finding.

V37 fixed semantic and migration declarations are HELD without consumer or host
execution. The migration preparation initially omitted startup when interpreting
the request to avoid an ambiguous probe. That is corrected in a separate held
revision: published v14 supports start --no-working-tree, which routes install
noise out of the packet while leaving startup active, before exact-path context.
Only the documented gated-ambiguous narrowing may continue without startup PASS
credit. All other failures stop. Preserve the first held declaration unchanged;
revision SHA-256 `68fc03c2464fe7743217c0bdd7417f31f7840097109d0508f6e790abc24ef391`:
`/private/tmp/odylith-greenfield-v14-to-v37-migration-start-routed-r1-20261006/revised-predispatch.json`.
The new checkpoint, package/checksums, canonical smoke, and exact current helper
and owner bindings remain prerequisites for either execution. Lower-capability
refusal safety is separate from the held standard-profile fixed controls.

The first new Registry history entry used a bare Plan ID, which source diagnostics
correctly rejected and omitted from the rendered component list (29 versus the
unchanged 30-entry manifest). The canonical rendered plan link is restored before
publication. Require both source validation and expected component inclusion;
an admission command's overall PASS alone does not erase its diagnostics.

The candidate previously sent its complete schema both in stdin and the
mandatory output-schema carrier. New transport v2 omits only that duplicate
stdin field, retains object-schema refusal, and refers to the supplied response
schema at the original task definition. Public contract v54, format v23,
semantic/schema/seal/profile/flow/deadline/provider owners remain unchanged.
The retained agriculture request projects from 59,003 to 29,833 bytes, saving
29,170 bytes; this projection was not a candidate replay or latency experiment.
One existing source owner adds two lines. Before-fix characterization has
16 failures/44 passes; afterward 60 focused and 289 adopter checks pass.
Independent review of the same four final hashes is CLEAR_WITH_LIMITS.

Exact installed Codex encoding preserves all 61 descriptions and two titles;
one native standard-profile canary returns a value present only in a schema
annotation in 4.838 seconds. These establish transport and small-schema attention,
not full candidate meaning or timing. Reports:
`/private/tmp/odylith-installed-codex-schema-custody-20261006-r2/report.json`,
`/private/tmp/odylith-native-codex-annotation-visibility-20261006/report.json`, and
`/private/tmp/odylith-candidate-schema-transport-implementation-20261006/handoff.json`
(SHA-256 `8cfd53da878b393f43527c32b6eabd946be92ae66a767210be93a27956896bc2`).
Retain the rejected confinement preflight and all timed public failures. A fresh
checkpoint/package plus predeclared semantic/timing evidence is required before
any claimed gain. Five migration assessment markers, native Claude authentication,
original protected holdout custody, Public40, and production release stay open.

## Current v35 migration preservation stop (2026-10-05)

Native v14-to-v35 upgrade succeeds (`rc=0`, `30.843s`): 13 target source/wheel
owners match, all 15 modes are exact, and the sole permitted catalog hash leaf is
correct. The run stops before target validators or browser proof because forbidden
Radar INDEX date bytes change from Oct 5 to Oct 6. The release migration gate then
stops (`rc=1`) on five missing current assessment markers; no ungated lifecycle
path ran. Evidence: `/private/tmp/odylith-greenfield-v14-to-v35-migration-20261005/final-failure-handoff.json`
(SHA-256 `96f81f0074888300240a766fed451aa3cbebd9f15c5a488b51f2c09887c194db`)
and `/private/tmp/odylith-v35-release-migration-gate-20261005.json` (SHA-256
`5d16f41010682e164d0a70586bbc48bdd71ce242c80d791d805326b5b78022bd`).

The owning normalizer stamped the index before deciding whether substantive
content had changed. It now stamps and atomically writes only a changed index;
idea-spec-only normalization still reports its change without rewriting the
index. The UTC-day characterization failed before the correction. All 10
normalization checks and five forced-Radar/upgrade caller checks pass afterward,
including exact byte and mode preservation across the next UTC day. Independent
review is CLEAR: `/private/tmp/odylith-radar-utc-preservation-independent-review-20261005.json`
(SHA-256 `20ef667dbb42511d57d5671bd579b89e162144010dc8c602839dd3292548da05`).
This is source/caller proof. The failed v35 consumer remains untouched; a fresh
checkpoint, package, and predecessor migration are still required. The five
assessment markers remain missing. No migration or release credit follows.

Full CI `37401400790` passes all three jobs at exact source
`5337dc9a5d408b8da7c747b366aa751ed313c8f3`; canonical v35 installed smoke also
returns zero. CI evidence is `/private/tmp/odylith-5337-full-ci-success-20261005.json`
(SHA-256 `6d0b066139dadf9a5965cf792af8b071da1b79ad02fc3a8cfecdfa347295e661`).
These results do not certify the later cognition and UTC-preservation edits or
move semantic, native-host, Public40, protected-holdout, or release gates.

## Current synthetic browser setup custody (2026-10-06)

Preserve three incomplete setup attempts: an unexplained signal10/rc138 after
47 screenshots, an external driver named watchdog.py that shadowed a runtime
package, and six Casebook timeouts from a transaction-only placeholder baseline.
The bounded setup correction renders real empty Casebook before activation and
candidate compile; the unchanged 44-cell oracle then passes. A final repetition
after the mobile counter correction passes 44/44 cells, zero issues, 111 images,
and 36 stable source/test pins in 36.356 seconds. Manifest:
`/private/tmp/odylith-cognitive-load-closure-20261006.json` (SHA-256
`a9ad31c0ded59e17debba1fb4b731e456758adcec33e0bdf118d285854848720`).
Do not use minimal transaction fixtures as full browser baselines, shadow product
imports with external driver names, or count partial screenshots as qualification.
The external process guard bounds observation; no oracle or compiler changes
were used. Synthetic current-source UI proof grants no installed, semantic,
migration, native-host, protected-holdout, or release credit.

## Current stale CI-signature closure (2026-10-05)

The retained e32 full CI failure `37391699845` remains `85` failed, `9,769`
passed, `10` skipped, and `37` errors. Fifteen signatures were already corrected
by ef0; the remaining 107 known test-only signatures now map to 268 focused
passes through 14 frozen test patches, with zero production or helper changes.
The superseded ef0 CI `37398192007` completed/cancelled after its known failures;
this is not a full-CI pass. Aggregate evidence:
`/private/tmp/odylith-ci-known-signature-closure-20261005.json` (SHA-256
`69836339fd3c5004f153d2a5222254bd97dfa046035e3a7a378b1aa26a9e5f1f`).
Independent review is CLEAR:
`/private/tmp/odylith-e32-test-only-corrections-independent-review-20261005.json`
(SHA-256 `b8d2d365a0c221c90ff9d0146ad85f2cdd0f009a55abd24ddd86686b2b1089db`).

Correcting the source narrative after its selective publication caused Compass
to refuse logging before any append. A forced full refresh also refused: authored
changes require explicit paths in a non-forced selective sync. Preserve both
refusals and admit the final source records before logging or full refresh.

The tests preserve exact authored `project_summary` and reveal source details
through native keyboard disclosures. Readable labels retain their IDs and routes.
Known historical pairs remain available for passive reading; active historical
and unknown future versions are refused, alongside changed writers and induced
drift before writes. Simulator coverage keeps Atlas selected/pending without a
ledger and preserves its bytes; positive target-owner completion has 16 passes.
No topology or runtime contract changed. Fresh full CI, installed package,
source-semantic H0/H1/terminal, migration, native Claude, and original blind
holdout remain unqualified.

## Current v34 fixed-case and availability boundary (2026-10-05)

The e32/v34 build and installed smoke pass (exit `0`, `489.773s`):
`/private/tmp/odylith-compass-verified-restoration-20261005/v34-installed-smoke-proof.json`
(SHA-256 `62bc5868f94e1a49ac1253118d2e220edf5a6d61dcf3eb8b3a45d9f7bc724e2f`).
Research H0 seals once after four calls (`148.765s` proposal; `208.601s` whole),
transaction hash `0f8964b25ae602021ec36fcb196388994065f52196013c69894203de341dd7eb`.
Independent Astra review passes all `13/13` forward duties, `47` reverse checks,
and `9/9` summaries in 303 characters with no P0/P1:
`/private/tmp/odylith-v54-v34-research-independent-source-review-20261005.json`
(SHA-256 `2067a7f9f25bd4b774f5ecb104d990c5885ae49b81c0faa545176c3def619f19`).
It reports a P2 default-Radar duplicate Decision Basis/Opportunity presentation.
The bounded owner correction is now proven: default view keeps exact authored
Decision Basis in native-closed disclosure and renders Product View once as direct
narrative. Browser proof passes `89` checks in `46.72s` across normal, empty, and
runtime-fallback `1440/430` states with 18 screenshots; handoff SHA-256
`a55bc8dade5312881c5cca4086b5f4439bc6b984e1eb9b2415fbc807460cb17f`.
Five generic provisional Radar prefixes are removed without changing authored
customer, deliverable, component responsibility, verification, Assumption marker,
or typed provisional/source custody. Six affected unit modules pass `89` in
`3.45s`; retain the first `88`-pass/one-fail run as a stale Registry boilerplate
assertion corrected by exact responsibility, planned status, and provisional
authority. Independent source review is CLEAR: warnings stay outside disclosure
and refs, authority, and custody remain unchanged. This clears only default-view
P2. Clarification preserves already-closed Project evidence/prompts and keeps
Success Metrics/Validation only in the full specification.

Research then stops at the pre-EDIT guard because the external source volume
vanishes; no H1 or terminal exists. Farm initial candidate stops at `124` after
`300.078s` shared phase and `393.667s` whole, with zero stdout, 61,247 stderr
bytes, and no proposal. Volume outage, host wall pause, and plugin-network warnings
co-occur; no sole cause is proved. Its result SHA-256 is
`ff143ee875d77cc3ef1bcfda49b0b4e53ab32f0ab8f4cd1b362dcfde2b76d1e8`; frozen
inventory is 9,693 entries (`667e6b…`). The genuine v14 migration independently
passes install/version but startup refuses before seed/upgrade, before this outage
(result SHA-256 `a2f062b37e0e4615e3e97c2014e7ab497f960d9183852a0be81b299334d4bafd`).
Native Claude authorization is absent and original protected-holdout custody is
missing. Preserve every prior attempt; no Public40, native, holdout, semantic,
migration, or release qualification follows.

## Current v31 package and caller hold (2026-10-05)

V31 build and canonical smoke pass from clean pushed `6d65bb271`; all 696
packaged Python files match that checkpoint. Before consumer execution, external
final binding stops on an overbroad assertion equating host-specific wrappers
with the shared canonical skill. Each wrapper instead binds to its own wheel
asset. Retain `v31-final-binding-held.json`; no final argv, consumer or execution
exists. Full v52 EDIT readback then exposes the separate product P1 in CB-303.
The reviewed two-line passive correction requires a fresh checkpoint/v32 build.
Keep frozen source-only baselines and caller templates; final binding must use
the corrected package and per-asset equality without repeating product attempts.
No held setup or package smoke earns semantic or migration qualification.

## Previous v30 terminal and CI boundaries (2026-10-05)

The first actual Agriculture terminal finishes once, exit 0 in 20.170 seconds.
Its result SHA-256 is `568eeae22889d461da36f0230185fed5857072373c508c954a82eb192391ed91`;
CB-303 owns semantic and publication evidence. Frozen external v3 preparation
could not bind runtime/current aliases under its strict canonical-path check.
The terminal-only v4 adapter resolves six owner paths consistently and retains
strict hashes, unknown-process refusal and CLOSED/sealed-URL opener attribution.
Native preflight and five custody controls pass without product actions;
independent static review is CLEAR. No failed consumer was replayed. Existing
preview, source, diagnostic and semantic artifacts remain unchanged; actual terminal adjudication is CLEAR. Preserve the original setup blocker and v4
review alongside the first execution receipt.

Exact-head CI `37345012135` for `3575ded39` reports 9,683 passes, one failure,
10 skips and six warnings. The sole failing private-custody test reads the
removed duplicate schema from inventory stdin; the unchanged attached schema
remains the authority. Update that test to compare retained schema bytes with
the emitted contract and assert that stdin omits the duplicate. Keep all UTF-8,
stream, hash, mode, no-write and no-leak assertions. This is stale test wiring,
not evidence that custody was lost. Full failure log SHA-256:
`228a79f1ad345536756eaf6d578d4e1e6060ed8b580f6f29670c902b5e8fa10b`.
Public40, browser, original protected/private custody, migration and final release
gates remain open. No partial or unavailable proof earns release credit.

## V29 first actual comparison and external setup boundary (2026-10-05)

The clean `0d265d402beedb46ae8abd835527fd153b9f71ee` V29 build passes in
201.014 seconds and canonical smoke passes in 366.618 seconds. The final
native parent preflight reaches two deliberate constructor holds using six
read-only Git commands and records zero installation, product, provider,
prepare, terminal, network, or consumer-write actions. Independent review is
clear (`c233f55e5011748ec625e32a2351ce2d905f2a62bee21620fe768649b4e3cc65`).

Two external binding setup defects also stopped before all product/write
operations: a clean binding setup `KeyError`, and a root outer-wrapper
`TypeError` because `final_file_manifest` values were SHA strings. Retain
`binding-setup-observation.json` and `root-launch-setup-failure.json`; the final
bindings are unchanged. These setup stops do not reclassify the immutable V28
failed entries or grant preflight/product credit.

The first actual V29 Agriculture preview exits 2 after the authority, inventory,
and verifier calls (197.094 seconds). It omits material steward-registration
action A03 and reports no supporting human actions, so no candidate is authored.
Research H0 seals after four calls; its immutable independent semantic audit
passes all 13 obligations with no P0/P1 findings (CB-303 owns the report and
manifest). Research EDIT times out during inventory
with zero stdout and process-group termination in stderr; verifier, candidate,
and proposal work are zero. The observed H0-to-EDIT input growth (11,785 to
17,928 bytes) is not a proven cause. H1 is absent and both terminal counts are
zero. The frozen consumer inventories remain Agriculture 9,686 entries
(`e1135fefa720fe64e8e39c60e78fce99c5134039deb2b837b09c78f9e67a8d0a`) and
Research 9,745 entries
(`7be393e98508b7b1e1030db78c5c2722b2e8e48ee7db72fdc195638acfc1a1ad`).

CI run `37324284688` passes for byte-identical product Python checkpoint
`9c698e77d`: 9,678 passed, 10 skipped, six warnings in 3,997.20 seconds; full
log SHA-256 `15ad52970c898940ab072bd70675bb2e17570c63447be29db30e4dcfb7d437f3`.
The later `0d` CI `37329570228` also passes: 9,678 passed, 10 skipped, six
warnings in 3,627.54 seconds; full log SHA-256
`70e8e21a579e1df8b017ce788decc9ce0eff759bc665f3a5c26f68f4587e8a9f`.
These results precede the one-line inventory input reduction. They do not replace local retained
failures or qualify semantic fidelity, terminal behavior, Public40, browser,
holdout, or release proof.

## V28 external preflight failure (2026-10-05)

The fresh v28 build and canonical installation smoke pass from clean pushed
`9c698e77d`. Both actual external preview entries then refuse in 0.169/0.168
seconds before installation, consumer creation or any model/provider/prepare call.
Exact error: `unresolved inherited terminal wrapper global before mutable phase`.
No initial or EDIT seal, product journey, terminal action or semantic result exists.
Retain both execution logs/receipts and all nine sealed external binding records
under `/private/tmp/odylith-greenfield-v52-v28-controls-release-20261005/`.

Read-only diagnosis against the real immutable methods proves that parsing the
method in isolation marks its implicit `__class__` as an unresolved global. The
live `FreshComparison.terminal` method has that name in a nonempty lexical closure.
Other checked wrappers have no missing globals. Earlier seven inert adopter
controls and static declaration review did not exercise this real closure gate;
they do not prove operational preflight. The correction must validate actual
captured cells, preserve refusal for missing globals or empty cells, and exercise
the real imported methods while stopping before product work. This is an external
harness defect; the v52 product code and failed v28 evidence remain unchanged.

The minimal external v3 correction adds four net lines to validate captured cells
before including their names in the existing scope check. Ten native controls
reproduce both v2 failures, reach a deliberate hold before mutation with v3 in
both domains, and refuse real missing globals and empty closures. Python also
refuses constructing the original methods without their required closure.
Product/model/provider/install/prepare/terminal and observed side-effect counts
are zero at that guard boundary. Adapter SHA-256:
`f21d743c70c02af3ef3da7529163db0c2f485c0dec75f5617f6f31eca393bdfc`;
result SHA-256 `061954136b94d3ad720c7630126469d72d3cf8b415e73c41352ffac11c6a1983`.
This proves the corrected scope guard, not complete preflight or product fidelity.

## V52 confirmation observer correction (2026-10-05)

The first combined gate retains 3,795 passes, 29 failures and 52 setup errors,
with all 2,313 frozen files unchanged. The release snapshot reader omitted the
complete source input when invoking the shared responsibility validator. The
one-line adopter correction forwards its already owned exact source and passes
133 release-reader checks with all custody guards intact. Remaining runtime
fixture integrations pass 324 affected and adjacent checks; independent review
clears their exact source/receipt rebinding and explicit supporting product duties.
The second broad gate retains 3,874 passes and two failures, with zero setup
errors and all 2,313 frozen files unchanged. All 2,140 installation checks pass.
Both remaining failures are the same dependency-test wrapper omitting the new
`first_run_event_orders` keyword. Its narrow forwarding correction passes 148
checks across the complete dependency module and six direct fixture adopters;
all dependency assertions and production owners remain unchanged. This composed
source proof closes those integrations; neither failed broad run is relabeled.
Fresh installed semantic and terminal proof remains required.

The existing audit owner now retains structured process facts alongside unchanged
raw process counts. The fresh CONFIRM observer distinguishes only the exact
canonical dashboard opener with matching source/code, sealed URL and independently
CLOSED journal at the event. Missing or mismatched custody, journal changes and
unknown processes refuse; model/provider/projection entries still must be zero.
The adopted terminal tail resolves every required global before any mutable phase.

The corrected audit module and two existing adopters pass 112 focused checks,
including 36 audit controls. The positive uses a real CLOSED fixture and canonical navigation
with a simulated final OS spawn; actual installed opener attribution is unproved.
Independent review found a P1 in the first external adapter: its terminal override
omitted inherited REJECT custody, including copied-old refusal and exact denial/
snapshot checks. Adapter SHA-256 `9a1a4d75a4515f5eb062892cdd3fee2cf509f0c93068dfc4958828632b139624`
is retained as failed/unexecuted. Restore the existing REJECT owner and prove the
complete adopter call graph before any consumer control. A separate P2 found that
argument repr occurred before the observer error boundary and could erase a process
attempt; unknown detail failures must still emit an unattributed counted event.
The corrected adapter delegates REJECT to its existing owner and scopes the old
zero count to preview evidence; seven inert adopter controls pass. The observer
now counts unattributed processes even when optional detail repr fails; its real
Popen negative passes. Final independent byte review clears all three harness findings. Fresh v28
terminal proof remains pending. V27 retains its failed process
assertion and unexecuted repeat; no result is reclassified.

## V27 partial terminal proof and source CI (2026-10-05)

Read-only installed diagnosis proves the durable H1 journal is closed and
all exact sealed/publication checks pass (56 writes, zero issues), with unchanged
consumer and failed-evidence inventories. Journal SHA-256:
`4fc35bad612c09249d1957ee3aab33d9495c215927a88c3350379b0e161b59bb`.
The one process launch is consistent with the required post-commit macOS browser
opener; attribution remains an inference because the trace retained no arguments.
The process assertion and unexecuted repeat retain their failed/incomplete status.
Diagnosis SHA-256: `2094a056e32cfdae64b12c8514326444503fbaeade2ab62f6208f0a3f853ff2f`.

Agriculture independently passes H0 26/26 and H1 31/31. Its reviewed six-command
terminal prefix proves original REJECT and copied rejected-old refusal, with
managed publication snapshots unchanged. The external harness then raises
`NameError: SEALED_PROGRAM` before successor CONFIRM. Failed `terminal_invocations:
0` is incomplete aggregation; it does not erase completed command records.

The first-unexecuted continuation ran H1 CONFIRM: exit 0/CLOSED, 56 sealed writes
and returned readback success with reported dashboard navigation. Installed
instrumentation observed zero model/provider/projection entries and one
subprocess.Popen. The external zero-process assertion failed; repeat CONFIRM did
not run. Missing process arguments prevent conclusive attribution. Preserve both
failed diagnostics; full terminal qualification remains incomplete.

Clean pushed `a3721bc4881d40de193aa6a976ee0eb4eecc285c` passes all Linux CI
jobs: 9,653 tests, six warnings, 3,841.43s. Run `37302863434` log SHA-256:
`1d8bbb637b8c364f02c0ba621c86a94ed2e5302b295f2ca5810397b7d178d8de`.
Prior `37288154604` remains 9,584 passes/six failures. CI proves this source
checkpoint only. Research H0 passes 13/13, but its v6/v9 EDIT admits source then
refuses candidate custody overlap; no H1 exists. Public40 and remaining release
gates stay held. Exact audit/prefix/result paths and full hashes are retained in
the v27 evidence manifest; no new semantic or terminal qualification is inferred.

## V26 source refusals and missing diagnostic custody (2026-10-05)

Clean `16a470d1b` produces the separately retained v26 distribution. All 11
manifest assets, 12 checksums, compiler/runtime identities, provenance and the
87-term leakage check pass; canonical install/upgrade smoke exits zero. These
results do not qualify semantic authoring or the full release.

The first Agriculture wrapper stops before any source call because root starts
execution while the owner is still sealing the predeclaration. The exact-input
guard correctly refuses the changed declaration. Preserve its result, eight
successful prefix commands and missing intermediate-metadata limitation. The
reviewed continuation reuses that exact installed consumer and begins only the
first unexecuted source step; no install or semantic call is replayed.

That source step returns a completeness refusal in three calls and 103.501
measured seconds. Its first untrusted omission report identifies dataset
registration. No candidate/proposal/EDIT/terminal action follows. Read-only
comparison verifies exact governed fingerprints and active generation. Research
H0 independently passes 13/13 duties, but EDIT refuses an invalid correction
reference after three calls and 135.511 measured seconds. Retain both failures.

Supported prepare supplies none of its existing raw retain callbacks. Inventory,
task and denied verifier bytes disappear during temporary-workspace cleanup;
hashes cannot recover them. The Research checker collapses wrong literal,
absent/ambiguous context and malformed references into one outward message.
No model-authored occurrence field exists, and the actual rejected subtype is
unknown. The Agriculture report alone cannot prove which current duty was
omitted. Add explicit private diagnostic retention through existing owners,
before parsing, refusal or deadline checks discard returned bytes. Retention
must consume the same deadline and cannot authorize a candidate or transaction.

The immutable failure and audit records are in
`.odylith/release-evidence/v50-implementation-20261005/`. Original failed freeze
and controls remain unchanged. Research is not replayed for missing bytes;
the 40-case public qualification remains held.

Independent review of the v51 designs identifies two P1 compatibility gaps and
one P2 path-custody gap. The transaction authority checker must retain exact
passive v50/v8 readback when the current EDIT constant becomes v9. Conversely,
both fresh candidate entrypoints must require current v6/v9; receipt-selected
passive validation cannot grant new admission. Prove this with a real compiler
v8 PCT load and legacy-receipt refusals at both fresh entrypoints. Diagnostic
creation and writes must pin directory identity against parent-path retargeting;
file-level `O_NOFOLLOW` alone is insufficient. These are pending-design findings,
not proof of an escaped v26 defect. Report:
`/private/tmp/odylith-v6-and-private-retention-independent-design-review-20261005.json`,
SHA-256 `be1f9c9656a8382f3f2db45fb4819c7ccde2dfcabc65b52e783782118194a8d2`.
Implementation and fresh independent review must close all three findings.

The first v51 retention/adopter run retains 166 passes and nine failures at
`/private/tmp/odylith-private-retention-bounded-20261005.log`. Eight existing
proposal-refusal variants supply old EDIT reference fields/v8 receipt custody,
so current v6 admission refuses before their intended proposal boundary. Update
only that supplier to explicit fresh authorization rows/current receipt; retain
all detail, seal, call-count and timing assertions. A new native retention-error
case correctly dispatches no installed command, but its shared test assertion
reads a nonexistent command log. Assert zero dispatch directly for that case.
Preserve the failed run separately; neither finding permits changing production
admission or deadlines. The owner reports 28 focused diagnostic controls passing;
combined continuation and independent review remain required.

The retention corrections pass 41 focused checks in 10.38 seconds: 28 diagnostic
controls, five native stall cases and all eight migrated refusal suppliers.
The final model-input capture delta still requires its own proof. The first
authorization run separately retains 56 passes and three failures at
`/private/tmp/odylith-v51-authorization-tests-first-20261005.log`. Two artificial
fixtures preserve outer correction whitespace that the existing authoring frame
strips; use exact retained internal Unicode/newlines and keep custody rejection.
The third expects all old v8 packages to be execution-ineligible. That expectation
is broader than the actual contract: the 24-owner identity fingerprints
post-confirm writers, unchanged by this pre-confirm revision. An already sealed,
valid v50/v8 package may remain eligible with exact writer identity; this does
not grant fresh candidate admission. Characterize that compatibility and existing
writer-identity refusal instead of adding an unnecessary commit-loader guard.
No actual publication or recovery of the failed v49 H1 is authorized.

### Private capture directory race findings (2026-10-05)

Independent implementation controls retain two failures and one pass in 0.29
seconds at `/private/tmp/odylith-private-retention-independent-controls-20261005.log`.
A same-user concurrent rename can replace the newly created directory between
`mkdir` and its first descriptor open, or move the pinned directory into the
consumer after the last pathname check. The current code therefore cannot claim
unconditional new-directory identity or outside-consumer residency during writes.
These findings affect diagnostic path custody; the candidate-input retention
failure control correctly stops the fourth model and proposal. Preserve the
failed controls and adjudicate the supported trust boundary before further proof.
POSIX `mkdir` does not return a directory descriptor; repeated pathname checks
cannot make ancestry validation and writing atomic against same-user mutation.
Do not build a retry loop or claim hostile same-user rename protection from a
finite check. Private evidence requires an operator-controlled stable parent;
detected mutations must refuse, and inode custody must not be described as an
unconditional location guarantee.

Independent report:
`/private/tmp/odylith-private-retention-independent-final-review-20261005.json`,
SHA-256 `add407a936088e9b4aac41a85c906bdaae85728d4c49248d3c1e0e4ca4027a31`.
The bounded correction binds the observed newly created leaf before descriptor
adoption and checks parent/leaf identity after writes as well as before them.
Fresh independent proof remains due; the original two failures stay retained.

The corrected writer passes 38 focused controls in 3.62 seconds. Independent
final review is clear under the stable private-parent boundary and its one
post-artifact-fsync control passes in 0.29 seconds. All 89 original assertions
remain. The original two-failure/one-pass log is hash-unchanged. Review:
`/private/tmp/odylith-private-retention-custody-correction-independent-final-review-20261005.json`,
SHA-256 `7cc5054072e711db23fcbacd1b49b85f4aa01bf9d8a12381c57035ce786e1923`.
This closes both P2 findings within the stated trust boundary; it grants no
semantic, timing, installed or release qualification.

### Actual 16a Linux CI governance failures (2026-10-05)

Run `37288154604` finishes with 9,584 passes, six failures and six warnings in
3,917.49 seconds. The exact failed log is retained at
`.odylith/release-evidence/v51-implementation-20261005/ci-16a-failed.log`,
SHA-256 `2abe24f701eb7e005fb1c6e5b2e3d849b7daf21083dbf269362a750edcdc399b`.
Five Atlas browser failures truthfully see committed stale payloads. D-004,
D-005 and D-006 miss only the changed dashboard spec history; D-018 and D-020
miss only the changed Chatter spec history. Each previous stored fingerprint
matches that spec's prior commit. Their topology/source bytes remain correct.
Review and refresh only those five catalog entries, preserving authored dates
and SVG/PNG bytes; leave unrelated stale debt untouched.

The release spec convergence failure is a separate timezone defect. Identical
frozen 16a stream and manifest reproduce the committed trace in Pacific time,
but UTC changes only the first event date from October 4 to October 5. Source
stream line 1545 records `2026-10-04T23:15:52-07:00`.
`sync_component_spec_requirements._event_date` converts that recorded timestamp
through the executing machine's local timezone. A refresh cannot converge both
hosts. Preserve the calendar date carried by the source timestamp, including
naive timestamps; retain invalid/empty fallback behavior. CB-212's prior UTC
INDEX repair and CB-018's local-window repair are distinct date contracts and
must not be blindly applied here. Prove both host timezones, signed offsets,
`Z`, naive and invalid input before selected release-spec synchronization. This
is a bounded existing-owner correction, not a new time or memory engine.

### V51 combined current-source gate (2026-10-05)

The once-only full-install plus 106-module Greenfield runtime gate finishes with
3,840 passes, one failure and 12 warnings in 347.82 seconds; all 2,312 frozen
source/test/doc files stay exact. Preserve its log, XML, declaration and receipt
under `.odylith/release-evidence/v51-implementation-20261005/`. The sole failure
is an old `.v50` literal in the actor-identity contract test; its returned
contract truthfully reports v51. Update only that explicit version expectation
and prove the complete actor-identity module, retaining all custody/reuse
assertions. The production source does not change for this correction. Do not
repeat the combined gate for a passing count or relabel its failed result.

The complete actor/spec-sync continuation passes 25 checks in 0.47 seconds,
including source-date portability, with all prior actor assertions retained.
The full Registry contract module passes 18 checks in each host timezone.
Independent review rebuilds all 13 frozen 16a release-trace lines exactly in
Pacific and UTC; the original recorded date remains October 4 and the raw
stream is untouched. The selected five-diagram review refresh preserves all
15 MMD/SVG/PNG assets and all 42 unrelated catalog entries. The five previously
failed browser cases, current D-043 and desktop/mobile normal, empty, fallback
and error metadata controls pass 20 checks in 23.73 seconds. These are source
and affected-surface continuations; original Linux CI remains failed until a
new run settles. All 2,126 installation cases in the combined XML pass. Neither
these results nor the corrected literal qualifies live semantic authoring.

## Complete 912f freeze and post-output timeout setup (2026-10-05)

The clean 912f/v25 freeze executes all 8,480 checks once: 8,479 pass,
one fails, and six warnings remain. No tracked source drifts. Preserve the
failed receipt and shard 35 at
`.odylith/release-evidence/v50-release-freeze-final-controls-20261005/`.
Every prior guidance, contract-pin, HIIT and terminal EDIT failure passes.
The sole failure is the authority-gate/124 parameter of the real terminal
lifecycle stream-custody test. Its 0.3-second flow expires before the fake
Python host emits JSON. The timeout result, failure observation, terminal
event, no-proposal boundary and cleanup assertions pass; parsing empty retained
stdout fails. Empty output is valid for a timeout before first emission.

The intended test proves custody after both streams were emitted. Synchronize
that setup explicitly before the unchanged short communication timeout,
retaining real subprocess termination, exact streams and all existing
assertions. Do not accept empty output, replenish the production deadline,
fabricate a result, retry the failed frozen run or replace the original receipt.
This setup proof does not establish a 0.3-second whole-journey guarantee.
The separately built v25 distribution passes clean 912f provenance, all 11
manifest assets, all 12 checksums and the 87-term leakage check. Its canonical
smoke completes with exit 0; its fresh installed semantic controls remain
unexecuted.

The exact test-only readiness patch now passes all 15 module checks in 6.20
seconds. All 59 original assertions remain byte-equivalent ASTs. The fake host
flushes both streams before an exclusive marker, and the existing started
observer waits finitely before the unchanged real 0.3-second communication
timeout. No product owner, clock, process mock, stream expectation or threshold
changes. Patch SHA-256:
`331bc0b5b9788418f203d8ff892ca4059a1296216a0ba3efd40d747aa2499b50`.
The original 8,479-pass/one-fail frozen run remains failed; its unchanged
passing scope and this corrected-module continuation are separate evidence.
Do not repeat the broad suite to obtain another scheduling outcome.

## Complete b694 freeze and remaining corrections (2026-10-05)

The new clean b694/v24 freeze executes every collected check once: 8,474 pass
and four fail out of 8,478, with no tracked-source drift. Preserve its failed
receipt at `.odylith/release-evidence/v50-release-freeze-fixture-continuation-20261005/`.
The six terminal EDIT failures from the previous stopped freeze now pass.
Remaining failures are the stale v49 current-contract assertion, two compacted
guidance assertions (manual `source-ledger-check` name and explicit seal wording),
and the HIIT integration's initial request with `--edit-evidence` but no prior
transaction hash. That integration stops before proposal compilation. Diagnose
its initial evidence contract against real EDIT custody before changing either
runtime or fixture; a missing prior in an actual EDIT must remain a refusal.
Restore guidance within the existing prompt budget. No skip, floor reduction,
retry of live authoring, or blanket passing freeze claim is justified.

The separate v24 canonical local release smoke completes with exit 0. All 11
manifest assets and 12 checksum entries match; clean b694 provenance and the
87-term leakage check pass. V24 is retained unchanged. Fresh v50 Agriculture,
Research and public40 controls are predeclared but remain unexecuted; their
strict clean-checkpoint bindings must be refreshed after any correction.
The b694 migration observer still requires all five current surface assessments;
no migration approval is inferred from install smoke. The prior 9ed CI is
reported failed; its failed-log download is unavailable (`log not found`).
Do not infer a failure cause or Linux pass from missing logs.

The first guidance/pin continuation retains 115 passes and one manager wording
failure in 2.59 seconds. It reveals the compacted stored-record clause omitted
the explicit digest/diagnostic distinction. Installed integration checks also
require explicitly delivered receipts. Restore that precise custody wording
within the unchanged byte limit and inspect all remaining assertions together.
Preserve the intermediate log; do not weaken the tests or receipt boundary.

Independent HIIT diagnosis finds the bounded initial route already refused
correction flags without a prior hash at pre-v50 9ed; help and source framing
defined the supplied file as EDIT evidence. The manual proposal path had
tolerated that ambiguous usage. Move the unchanged reviewed HIIT source into
its explicit initial prompt and use one consistent prompt-only citation frame.
Keep all 30 package/path/timing assertions and genuine EDIT custody refusals.
External fixture patch:
`36a019507c1efcd738e83c9136c97e53040a84898e8aa99bcef0de29655086b1`.

The corrected six-module continuation now passes all 117 checks in 10.36
seconds, including all four failures from the complete freeze. Static inspection
also finds two installed integration modules still asserting the older verbose
kernel wording. Align those independent assertions with the compact equivalent
custody, timing-exclusion and refusal statements; keep every enforcement check.
Their actual install and bundle entrypoint behavior still requires fresh proof.

Both installed/bundle integration checks now pass in 1.32 seconds. All their
assertions and line counts remain intact; equivalent kernel phrasing preserves
source custody, nonreplenishing timing, receipt-delivery exclusions and refusal
semantics. Final consumer/product kernels are 12,395/11,533 bytes under the
unchanged 12,400-byte limit, with exact scoped/bundle mirrors. Production
Greenfield runtime and compiler owners remain unchanged from b694. The complete
freeze is still the original failed 8,474-pass/four-fail run; these targeted
continuations and static equivalence do not rewrite it as passing.

## Frozen v50 terminal EDIT fixture mismatch (2026-10-05)

The clean `9d8598c02` freeze collects 8,478 checks and stops after 2,600:
2,594 pass and six fail in `test_greenfield_decision_cli.py`; 5,878 remain
unexecuted. Retain the failed receipt and shard 13 unchanged at
`.odylith/release-evidence/v50-release-freeze-20261005/`. The genuine compiled
prior is valid. Its shared receipt stub supplies initial v4/v7 custody for
EDIT without the prior lifecycle baseline, so the runtime correctly refuses
before the intended success, tamper and non-success branches. This does not
justify weakening the v5/v8 EDIT admission law. Replace only that shared
fixture through real preflight, verifier-task and receipt-validation owners,
then prove the downstream assertions and original pending-package bytes.
External test-only patch SHA-256:
`8fd880db2eac6725b31690ebf4d215be04f1e0da15976cdde15480854cc838fa`.
The exact one-file patch is now applied. All 27 decision CLI checks pass in
5.61 seconds, including the six previously blocked branches. The helper uses
real v5/v8 admission and verifies the original pending-package bytes; no
production code or runtime law changed. Continuation evidence:
`.odylith/release-evidence/v50-implementation-20261005/decision-cli-fixture-continuation.log`.
The original frozen receipt remains failed; it does not gain passing credit.

The separate clean v23 distribution binds `9d8598c02` and passes the canonical
local release smoke with exit 0, including fresh installation and published
predecessor upgrade checks. Its manifest is
`bc9cd0d21cd53d5790dfae2a85b49517e861c07467aa105dc5e8184dd33eef0b`.
This smoke does not execute positive Greenfield authoring or qualify the
unexecuted frozen checks. Preserve that distribution and provenance; a new
checkpoint requires its own clean release binding.

## New EDIT test-fixture failures (2026-10-05)

The retained linked-migration help continuation fails before its first author
call because its whole-consumer equality guard treats two legitimate v14 import
caches as source mutation. All 9,191 preexisting file bytes and modes are exact;
only `component_authoring.cpython-313.pyc` and
`scaffold_mermaid_diagram.cpython-313.pyc` are added. Offline code-body comparison
matches the unchanged published Python sources. Their respective hashes are
`60c408a7f910ccff5a1f5e42d7f2ee7c1592c41818cf8cd8c893ff701c7c32fb`
and `f53c11d4ee8a7f65504c12d92dd0a05465fb320d03f89525da14434e026f388f`.
Published isolated Python ignores the environment bytecode suppression flag.
Retain the original failed wrapper, startup/help results and current consumer.
A continuation may predeclare only these exact additions and begin at the first
unexecuted seeder, without repeating installation, startup, help or wrappers.
No blanket cache exclusion, reset or migration approval is justified.

The first eight-module v50 regression run preserves 280 passes and three
failures in 21.12 seconds. Two bounded controls stage a compiler transaction
but do not receive a guardian completion receipt, then fail on its missing
`transaction_hash`. The unmarked positive v8 compiler control reaches the
quality gate and is refused as unapproved. These new fixture paths remain
unqualified pending exact diagnosis; no receipt, quality, or runtime identity
law may be weakened to make them pass. Original evidence:
`/private/tmp/odylith-v50-edit-preservation-targeted-20261004.log`.

Owner diagnosis attributes both bounded failures to direct parent-process
staging, which cannot register through the child-only guardian channel. The
unmarked fixture bypasses the canonical authoring-manifest projection and
supplies an extra observation field. Correct those test paths using the real
owned child transport and existing manifest projector; preserve closed receipt
and quality laws. The guidance/smoke run separately records 63 passes and one
failure: added kernel wording grows the managed block to 12,946 bytes, above
the existing 12,400-byte limit. Compress shared guidance while retaining its
laws and move detailed EDIT protocol instructions into the existing skill.
Do not increase the prompt budget. Original guidance log:
`/private/tmp/odylith-v50-guidance-smoke-tests-20261005.log`.

The test-only custody/manifest correction now passes all 283 affected-owner
checks, including bounded and unmarked first v8 compilation, readback and a
second EDIT. The combined continuation retains its pre-compaction kernel
failure. Subsequent compaction passes all 64 guidance/smoke checks with consumer
and maintainer blocks at 12,398 and 11,536 bytes. The two intermediate compacted
wording failures are retained; required public-confirmation and JSON-boundary
wording is restored without changing limits or test assertions. Final guidance
log: `/private/tmp/odylith-v50-guidance-smoke-qualified-20261005.log`.

A separate nine-module flow-adopter run has 110 passes and eight failures in
53.19 seconds. All eight parameterizations of the proposal-refusal control
stop at the contract boundary: their initial-only mocked contract is reused
after adding an EDIT transaction hash, omitting required prior lifecycle context
and using a prompt unrelated to the prior seal. Preserve the original result at
`/private/tmp/odylith-v50-flow-adopter-regression-20261005.log`. Correct that fixture
through the real read-only contract/source-check owners while preserving the
targeted proposal-refusal diagnostics and old-seal byte assertions. Runtime
EDIT context requirements remain unchanged.

The one-function fixture correction now passes all eight refusal variants in
5.32 seconds. It uses the actual read-only contract and source-check owners,
verified prior prompt, v5 task and v8 receipt; every original bounded diagnostic,
zero-provider, receipt-sink, cleanup and whole-repo/old-seal byte assertion
remains intact. Continuation:
`/private/tmp/odylith-v50-proposal-refusal-fixture-continuation-20261005.log`.
Original 110-pass/eight-fail flow evidence remains unchanged. Guidance behavior
passes six cases and 11 checks. Guidance/Discipline matched-pair diagnostics
clear their hard gates for six/seven cases respectively, with provisional
status and no full-corpus/public qualification claim. Discipline validation
passes; the current move and its explanation remain local with zero host,
provider, subagent, broad-scan, projection or full-validation calls.

## Current populated-migration harness frontier (2026-10-04)

The fresh published-v14 linked fixture installs successfully, then its pre-seed
startup returns intentional scope narrowing (`gated_ambiguous`, exit 1).
The first continuation runs previously unexecuted help phases 05-12 once, then
its author wrapper fails before invoking the unchanged seeder. The full consumer
inventory differs only by two installed Python bytecode caches:
`component_authoring.cpython-313.pyc` and
`scaffold_mermaid_diagram.cpython-313.pyc`. No application, authored governance,
plan preflight, baseline or upgrade has run. The harness incorrectly assumes
help cannot create import caches. Original failed results and startup status
remain failed under `/private/tmp/odylith-v22-linked-predecessor-proof-20261004/`
and `/private/tmp/odylith-v22-linked-migration-continuation-proof-20261004/`.
Diagnose the exact cache-to-source custody and first unexecuted seeder boundary
before continuation; never exempt authored bytes or replay completed phases.

## Current installed CONFIRM audit frontier (2026-10-04)

Current semantic qualification is failed: independent v49 audit passes H0
26/26 but finds an H1 guard omission, passing 25/26 originals and 4/5 correction
units. The verifier's affirmative completeness was false. CB-303 owns the
material semantic regression. Do not publish or recover that known-bad H1.
Retain its PREPARED journal and all original failed evidence. Audit JSON:
`/private/tmp/odylith-v49-agriculture-h0-h1-semantic-audit-20261004.json`, SHA-256
`c2323e44a7cf2401b7207ffcf9d88eb9c95d0a4320ef4d67d85e4b1cc460ac6d`.

Clean `3eaa1ff5646d368e3dc4b381c82ee94a29eed25c` builds v22 and passes
canonical local release smoke. The once-only v49 Agriculture control admits
both initial and changed-hash EDIT preparations in four calls each, at 306.344
and 318.489 diagnostic seconds. Original REJECT and copied-old refusal pass
with zero observed model, projection or subprocess entries. Independent review
of these new bytes fails H1 as above; earlier v48 review cannot qualify them.

Successor CONFIRM returns 124 after its unchanged 60-second outer timeout and
process-group termination. Its absent final counter file is a secondary symptom,
not the primary failure. The original failed result remains at
`/private/tmp/odylith-greenfield-v49-installed-edit-result-20261004.json`, SHA-256
`1591287215b8b56c45b6b93dcc9fc5321f31d9f6f0fdc7c1f9877198723501c4`.
The retained write audit records 353 writes and zero subprocess attempts, ending
during immutable generation staging. The canonical audit emitter uses blocking
pipe writes, while `InstalledWriteAudit.finish` starts reading only after the
child returns. This permits pipe backpressure to stop CONFIRM before publication.
The surviving journal, pending seal, receipt, staging tree and failed evidence
must remain intact. Missing final counters cannot prove zero semantic entries.
Research's predeclared v49 control remains unexecuted while this shared audit
defect is corrected; it must not inherit the known blocking reader.

Read-only diagnosis confirms the journal is PREPARED, the original baseline
publication remains active, and all snapshot-owned bytes and modes still match
the live repository. Eleven finished staged files match the sealed after-image.
The exact audit rows occupy 65,371 bytes of a 65,536-byte pipe; a replay-free
new-pipe control rejects the next 213-byte row with EAGAIN. Production blocking
emission therefore explains the stopped generation write. Diagnosis:
`/private/tmp/odylith-v49-confirm-timeout-diagnosis-20261004.md` and adjacent JSON.

End this frozen control wave at its retained failure. Correct only the existing
audit reader, keep exact event and failure evidence, and prove a trace larger
than pipe capacity completes before `finish`, with reader/FD cleanup and
malformed-trace refusal. Do not raise the timeout, rerun authoring for luck, or
turn the original failure green. Any deterministic recovery requires a separate
receipt against the exact retained successor and its interrupted journal.

The concurrent-reader change passes 96 owner/adopter checks, but independent
review finds one medium evidence-retention defect: a read failure after a
partial trailing JSON row makes the existing parser discard earlier complete
rows. The result remains inactive, so this is not false admission; diagnostic
prefix custody is nevertheless incomplete. On reader error only, retain complete
newline-terminated rows before the trailing fragment while preserving failure
classification. Normal EOF malformed traces must remain fail closed. Add the
partial-row fault control and rerun the bounded owner/adopter proof before
checkpoint. Review:
`/private/tmp/odylith-write-audit-concurrent-reader-independent-review-20261004.md`.

The d75 Ubuntu run executes 9,529 checks: 9,494 pass and 35 fail. Its failures
are diagnosed individually; local passes are not Linux qualification. Selected
remaining populated-browser continuation passes 47 screenshots and preserves
all 11 authored files and modes. Positive linked-plan migration, the complete
browser matrix, all five migration classes and protected custody remain open.

The independently CLEAR Linux fixture proposals pass 623 local checks with
Codex absent from PATH, but one installation check still contains a second
obsolete root-guidance admission phrase. The first proposal missed that duplicate
assertion. Preserve the failed log and update all remaining assertions in the
same owned function against the installed guidance contract before a focused
continuation; do not suppress the check or reinterpret this 623/624 result as
Linux success. Log:
`/private/tmp/odylith-linux-fixture-corrections-local-validation-20261004.log`.

The selected 12 reviewed Atlas records are fresh with zero selected stale;
24 unrelated stale records remain explicit. Browser correction proof passes
30 checks, then fails D-037's old `benchmark latency` summary phrase after its
truthful summary update. The visible canonical node retains `Latency and
token-budget proof`; align that assertion to the maintained source contract
and rerun only this failed case. Incomplete observer finalization accompanies
the assertion failure and does not count as a clean browser pass. Original log:
`/private/tmp/odylith-atlas-and-registry-browser-corrections-validation-20261004.log`.

### Reviewed audit and fixture corrections (2026-10-04)

The audit reader now drains concurrently. On reader failure it preserves every
complete newline-terminated event before an incomplete trailing row and stays
inactive; ordinary malformed EOF still refuses. All 98 owner/adopter checks
pass, including a real child producing 4,096 ordered writes before `finish`,
nonzero child exit, partial-row faults and reader/FD retirement. Final independent
review is CLEAR with two additional controls. Handoff:
`/private/tmp/odylith-v49-write-audit-prefix-fix-20261004/handoff.json`, SHA-256
`38648e8476fb05587840d6871d9e7c73b369bdf694bf2687218c0bfb08fcda64`.
Final review JSON SHA-256:
`ec6ac967480c7ebaa443f51fc637f8b8d476b3b6eab1026681bc3050c8f775a1`.
The original killed CONFIRM and intermediate failed review remain failed.

Canonical selective sync passes all 19 steps. Besides the 12 rendered reviews,
it refreshes four impacted review-only records (D-022, D-023, D-034, D-038)
without changing their source or rendered assets. Atlas now reports 27 fresh
and 20 stale; this supersedes the earlier 23/24 count above.

The missed assertions in the same guidance function are corrected; the single
failed installation check passes its focused continuation. D-037's maintained
latency phrase is also corrected; its single browser continuation passes with
clean observation. Preserve both original failed logs. These continuations plus
623 installation checks and 30 browser checks establish local affected coverage,
not a fresh complete Linux or browser campaign. Logs:
`/private/tmp/odylith-linux-fixture-root-guidance-continuation-20261004.log` and
`/private/tmp/odylith-atlas-d037-browser-continuation-20261004.log`.

## Previous actor-custody and EDIT frontier (2026-10-04)

Frozen d75/v21 executes all 8,423 collected runtime/install/selected-browser
checks with zero input drift: 8,422 pass and one actor-law assertion still pins
contract v47 instead of v48. The original failed shard and unchanged
continuation remain under
`/private/tmp/odylith-greenfield-release-freeze-v21-20261004/`.
Canonical local release smoke passes; this does not qualify populated migration,
Linux, live semantic reliability, or a complete terminal journey.

Two once-only v48 installed controls fail at distinct boundaries. Agriculture
H0 is admitted in four calls and 337.870 diagnostic seconds. Independent strong
source-first review finds all 26 original duties materially faithful, with two
low, nonmaterial labeling findings. Its EDIT stops after two calls and 80.305
seconds at preflight: `first_path_actions[4]: external actor citation must be
a duty or role reference`. The rejected ledger bytes are unavailable, so the
exact actor and selected occurrence remain unknown. Research H0 is admitted;
its EDIT receives affirmative source verification with zero reported omissions,
then fails at propose after four calls and 258.004 seconds. The inner compiler
error and candidate bytes were discarded. Its actual rejection cause is unknown.
Neither control reaches REJECT, CONFIRM, or idempotence. Preserve both original
H0 seals, receipts, nonterminal consumers, and failed results; do not replay
unchanged calls for a better draw.

The reviewed v49 correction removes one redundant actor-enclosure predicate.
Exact actor citation already owns the selected source occurrence and the
compiler already inserts it first among role references. A duplicate actor
alias satisfies the old predicate without changing derived role evidence.
Nonempty typed role context, event and actor reference-only exclusion, atomic
identity, exact citation custody, verifier refusal, and receipt binding remain.
The mechanism removes 21 production lines. A separate two-line correction uses
the existing bounded diagnostic helper for both propose refusals, restoring
failure detail without admission authority or additional calls. It cannot
recover the lost research error or prove that error fixed.

Fresh affected regression passes 328 checks in 71.95 seconds:
`/private/tmp/odylith-v49-actor-and-diagnostic-targeted-validation-20261004.log`.
Independent actor review is CLEAR:
`/private/tmp/odylith-v49-actor-custody-independent-review-20261004.json`,
SHA-256 `bd1f5df32a303986e93cd5ed3951cffb027a41a2f24c6c5dfbb3da7cef5bacd9`.
This is structural proof; live changed-contract reliability remains unqualified.
The combined final review is independently CLEAR, with eight refusal controls
passing, and the complete install unit scope passes 2,079 checks. Review:
`/private/tmp/odylith-v49-actor-diagnostic-combined-final-review-20261004.json`,
SHA-256 `3162bc6d50f0e1d3cd5c268c61210dec54addd879cd9e142aec04b57724d8036`.
Install log: `/private/tmp/odylith-v49-unit-install-validation-20261004.log`.
Fresh engine validation retains all 22 engines and 22 wired handshakes;
topology validation passes 100/100 with no findings. These counts establish
structural preservation, not significant improvement of every capability.

The populated v21 installer succeeds and the installed Atlas check passes.
Original strict byte-preservation results remain failed: the existing catalog
fingerprint and separately documented UTC INDEX date differ from the predecessor.
Corrected browser observation passes four desktop authored surfaces, then stops
on an unlinked plan fixture. The predecessor idea already has an empty
`promoted_to_plan`; its plan file is not proof of a served plan route. Positive
linked-plan migration and the remaining browser matrix are unproved. No migration
class, release, or timing qualification follows. The original protected payload,
manifest directory, and run ledger remain absent; prior lifecycle is unknown.

## Historical bounded source-inventory experiment (2026-10-04)

The required original final-holdout payload and frozen manifest directory are
absent at their recorded paths during the checkpoint guard. No new protected
content was opened or run; exact-copy and prior-custody diagnosis is read-only
and blind to case content. Final qualification cannot rely on presumed custody.
Public and installed proof can proceed while that evidence boundary is settled.

The existing source-phase and preparation owners now retain the bounded checker
refusal and label the first reported omission as untrusted diagnostic evidence,
with no admission authority. Original H0 bytes, refusal and call budgets are
preserved. Full adopter tests pass 122 checks; independent review is CLEAR with
36 focused checks and five separate controls. Review:
`/private/tmp/odylith-v48-feedback-independent-review-20261004.json`, SHA-256
`f53b266316b86b398c6b005060fbbd421dda0b713e0dbb3277ab6896ecd9b27c`.
These controls prove feedback behavior, not inventory reliability.

The discarded EDIT verdict does not identify its exact missing fact. Independent
source/schema inspection finds the correction representable and identifies an
instruction asymmetry, without proving that asymmetry caused this refusal.
Host contract v48 adds one complete-source and EDIT-preservation paragraph to
the existing inventory task. The verifier, schemas, four calls and caps are
unchanged. One changed-contract agriculture regression and one frozen research
source+correction pair must preserve every original and added duty under
independent source-first mapping; negative authority controls remain required.
No reliability improvement is claimed before those observations. Diagnosis:
`/private/tmp/odylith-v20-agriculture-edit-source-stage-diagnosis-20261004.json`,
SHA-256 `220bed8e8d142974956854d8b4d01625d0e1bfa856ea5b8b8c261bd5ea8cf126`.

## V20 retained qualification and installed EDIT evidence (2026-10-05)

Clean candidate `d0021184faba41b8fac887ce107ee452d8dc2722` passes the
complete frozen runtime/install/selected-browser scope: 8,410 tests, zero input
drift. This new pass does not erase the earlier 8,387-pass/23-failure diagnostic.
Receipt: `/private/tmp/odylith-greenfield-release-freeze-v20-reconciled-20261004/receipt.json`,
SHA-256 `a30b0319b3c2589f6c178f29b513084545faf27ad2c6344bccfc02bf88619ad5`.
V20 local assets and canonical local release smoke pass; manifest SHA-256 is
`ea17a37122c64b5ff621691b59abec2f118d2a2175c8d5d201a0d8711e73aecd`.
That smoke has an empty source baseline. Actual Ubuntu CI run `37255496696`
fails at collection with `ModuleNotFoundError: greenfield_model_profiles`;
local passes do not qualify Linux. Gate receipt:
`/private/tmp/odylith-v20-test-install-gate-20261004.json`.

The civic public source-first independent review is CLEAR with stated limits,
with no material omission, invented authority or cross-artifact semantic drift.
Its exact reviewer model identifier is unavailable, so no stronger profile claim
is inferred. Review: `/private/tmp/odylith-v20-public-civic-independent-review-20261004.json`,
SHA-256 `9a9c615b2413f6d864ff6e1a4dbdb9ea380398c705feac24a6a7ae468f04672e`.
The saved exact civic snapshot passes 44 desktop/mobile browser cells with 111
screenshots, zero issues and zero drift across 116 source files. Browser receipt:
`/private/tmp/odylith-v20-civic-browser-proof-20261004/result.json`, SHA-256
`d27114313235269e3279d1b48a0cbd005cfa7768ea7ef13c39cde447c8bbcdd7`.
Both bind output SHA-256 `49168a162d38b2d9715f0301ac1e1b82062dc3c9298b79c80ef98e437b4370cf`.
This is one public control and saved-snapshot UX proof, not full release approval.

Retain three distinct agriculture observations. The original harness wrongly
rejects the already published empty bootstrap baseline before any model call.
The reconciled run obtains H0 successfully in 392.335 diagnostic seconds, then
its observation helper fails with `AttributeError` because the lightweight
pending loader has no `.proposal`. A read-only continuation uses the existing
full pre-confirm loader and canonical source frames without replaying initial
provider calls or reissuing the initial receipt. Its one actual installed EDIT
then returns source-completeness verdict `no`, one omission, three host calls
and zero candidate calls after 214.023 measured diagnostic seconds (215.447
caller wall seconds). The command returns 2 before publication. The actual
semantic refusal is separate from the two earlier harness errors; its cause
remains under independent read-only diagnosis.

Original and reconciled results remain at
`/private/tmp/odylith-greenfield-v20-installed-edit-result-20261004.json` and
`/private/tmp/odylith-greenfield-v20-installed-edit-result-reconciled-20261004.json`
(the latter SHA-256 `be276b2125cefab9b2c4a84681a38ab09e5da09f5b91c993ac743596ef8efbcb`).
Continuation: `/private/tmp/odylith-greenfield-v20-installed-edit-result-continuation-20261004.json`;
raw command evidence is retained under
`/private/tmp/odylith-greenfield-v20-installed-edit-proof-continuation-20261004/commands/06-edit-installed-prepare`.
The 660-second cap remains diagnostic and unqualified; measured scope excludes
receipt delivery and final preview serialization. Do not retry for a better
semantic draw, weaken acceptance, or attribute the omission before diagnosis.

CB-358 and B-145 separately retain the populated migration failure after
activation: 10/11 raw file byte sequences and 11/11 modes preserved, with only
the pre-existing derived catalog `render_source_fingerprint` leaf changing.
Its proposed Atlas correction passes 15 independent external-copy controls;
installed recovery remains unproved. CB-347, B-142 and B-145 remain active
implementation work. No five-class migration approval, release success or
protected evaluation follows from these observations.

## Final fixed-source diagnostic reconciliation (2026-10-04)

The corrected eight-file pack passes 220 checks in 28.08 seconds. It covers
all 23 diagnosed failures and preserves valid-hash mismatch, missing compiler
receipt, exact runtime execution inventory, model-free commit, manual source
custody, bounded receipt guidance and existing prompt-byte ceilings. Shared
guidance is shorter than the first correction. The original failed diagnostic
remains retained; fresh installed/public semantic qualification remains open.
Proof: /private/tmp/odylith-v20-final-boundary-corrections-rereview-20261004.log.

The retained 8,410-test diagnostic completes with 8,387 passing and 23
failures across five shards, with no source drift. Browser checks pass. The
failures are four obsolete create refusal strings, two malformed-hash fixtures
that no longer reach their intended boundary, two stale execution inventories,
ten test helper calls to the moved transport owner, and five guidance/smoke
expectations for the retired manual default. Preserve the original failure
receipt and unchanged continuation under
/private/tmp/odylith-greenfield-release-freeze-v20-final-20261004/.

Correct the fixtures at their actual boundary and keep the publication guards,
semantic acceptance and release floors intact. Name the compiler-owned
ProductCreateTransaction explicitly in bounded guidance, preserve the ban on
hand-authored proposal/transaction JSON and internal schema chatter, and make
the smoke validator recognize the supported prepare route. Validate all affected
files before a stable checkpoint. The diagnostic remains failed; it is not
release qualification.

## Bounded transport independent falsification (2026-10-04)

Independent final review is CLEAR for the nonce receipt boundary: all fixed
hashes match, 14 focused controls pass, and the exact previously failed
bootstrap control passes independently. Ordinary failed cleanup cannot
substitute for the receipt. Preserve the original one-failure expanded result;
complete final runtime/install/browser and installed/public gates remain open.
Review: /private/tmp/odylith-nonce-independent-final-review-20261004.md,
SHA-256 ea0244a8b310430608f136ba63357971a93c6af968390bbad9bd652336c7e652.

Before final clearance, the fixed nonce implementation awaited review. A private
guardian channel issues the completion receipt only after completion-attempt
I/O and strict raw deadline checks. Canonical digest state alone cannot grant
confirmation; copied transactions require the explicitly delivered matching
receipt. Post-certification delivery errors preserve accepted or uncertain
outcomes. Expanded regression passes 502 checks; one shell-bootstrap readiness
poll fails, and that exact test plus all boundary controls then pass 40 checks.
Preserve both logs and require the complete final freeze. Handoff:
/private/tmp/odylith-bounded-greenfield-nonce-transport-handoff-20261004.json,
SHA-256 95f024a9a80aa02d292c582345d627f6e98ff06eb62a5a65594d542c3bb6f77c.

The positive-completion correction passes 388 targeted checks, including 29
boundary controls. It rejects the original copied-create control when tentative
readiness and sealed bytes survive rollback. One final risk remains: completion
publication precedes its post-write clock sample, so late or erroneous
publication still depends on successful removal of the positive record.
Another revocable flag would repeat this failure. Establish one authoritative
acceptance boundary that ordinary cleanup errors cannot turn into permission;
retain the complete measured scope and fail closed on late acceptance.
Handoff: /private/tmp/odylith-bounded-greenfield-completion-transport-handoff-20261004.json,
SHA-256 9531049698fd05b458ef81a44e542660b961f630697e91e567b1851b4508ccd4.
Final independent clearance and release qualification remain open.

The first corrective pass passes 386 adopter tests. Independent rereview
passes 27 boundary tests and closes all four original supported findings.
It reproduces one remaining P1: if the first rollback unlink fails after
a tentative ready write, transaction bytes and that ready state can remain;
guardian exit then makes a copied transaction commit-admissible despite failed
publication. Readiness must require an actual successful protocol outcome,
not infer it from custodian death. Correct this in the existing owners and
retain the real failing copied-create control and mixed rollback failures.
Review: /private/tmp/odylith-bounded-rereview-20261004/review.json,
SHA-256 9cf1752c1493cfe198e1b789760eb12c1d0514824be8356fda3b56967ed9ce25.

The moved runtime flow passes 376 targeted checks but fails four independent
supported-operation controls. A copied sealed transaction and compiler receipt
can be committed after abort because cleanup removes the only repository-owned
deny marker. Marker release can cross the deadline and still acknowledge
completion. A numeric process-group snapshot can outlive its original identity
across the TERM/KILL grace. An ordinary same-group background grandchild can
survive successful cleanup after its leader exits. Preserve the failing
controls and correct these boundaries in the existing pending and process
owners before another freeze or installed run. Evidence lives under
/private/tmp/odylith-bounded-independent-20261004/.

Deliberately killing the independent guardian from another process also leaves
native blocked work unbounded. Adjudicate this separately against the declared
environment: the operator excludes arbitrary hostile external mutation and
hardware failure. Check for a supported internal route to the same state;
do not add a watchdog hierarchy or silently claim resilience beyond proof.

## Detached public bridge review (2026-10-04)

The corrected canonical validator and genuine record-count callers pass 71
bounded checks. Independent rereview passes 89 tests and all 22 independent
controls, including the original four coherently rebound malformed proofs.
No actionable P0/P1/P2 remains in that bounded bridge. Original red evidence
is retained; actual public semantics and consumer timing stay unqualified.
Review: /private/tmp/odylith-greenfield-public-qualification-independent-rereview-20261004.md,
SHA-256 e827e022d2131a4edf3c07a99a270e42908471fb8d7cc7a710a0c9ca0e99ab1d.

The bridge passes 316 targeted checks, including 39 new controls, but remains
unqualified. Independent review passes 292 checks and reproduces malformed
unavailable-provider evidence acceptance after coherent hash rebinding:
string values for `write_audit_active` and `staged_transaction_present`, an
object for `write_attempts`, and boolean `returncode` can pass the canonical
validator through Python truthiness. This is a P2 evidence validation defect;
it is not actual consumer semantic failure. Correct exact shapes in the
existing canonical validator, retain the original failing control and require
independent rereview before the final freeze. Invalid measured timing
decisions and missing semantic/four-lens evidence continue to refuse.

## Consumer deadline ownership gap (2026-10-04)

Independent source inspection finds a second timing gap: the installed host
instructions run separate CLI and inference passes without one product-owned
parent deadline. The release runner has a monotonic 660-second diagnostic
budget, but checks synchronous retention and observer callbacks only after
return. Local CLI receipts authenticate source meaning without timing
provenance; `propose` starts a new local clock. Neither route establishes a
complete consumer deadline. Evidence:
/private/tmp/odylith-whole-flow-custody-design-20261004.md.

Move existing four-pass orchestration, deadline and process supervision into
one supported product route and make release callers adopt that same owner.
Bound blocked callbacks and descendants with a declared cancellation grace;
preserve the existing semantic phases, model budgets and sealed transaction
laws. Manual file-based commands remain valid source-custody interfaces and
cannot acquire bounded-route credit from caller-authored timing. Keep 660
diagnostic and unqualified until fresh fixed public observations and an
authenticated decision support a finite release bound. Require real deadline,
child-cleanup, clarification-stop and EDIT-seal controls before release proof.

The parent also needs a pending-seal boundary: existing `propose` stages before
retention and observer return. A parent timeout must not leave a newly staged
seal confirmable. Quarantine only newly staged, journey-owned pending bytes
before exposure; release them only after bounded completion. Preserve old EDIT
and preexisting equal-hash seals, exact sealed transaction bytes and recovery
journals. This is deterministic pending-state custody, not another semantic
gate or a change to chat authorization.

## Frozen regression boundary correction (2026-10-04)

All eight diagnosed test-contract failures are corrected. The four affected
test files pass 81 checks and actual R1 ledger, relation and source-duty custody
families pass 114 more. The patch adds nine test lines; product acceptance,
published floors and memory source remain unchanged. The hygiene guard pins
the already approved B-133 1588-line exception exactly. Original failed
diagnostic evidence remains retained, and a fresh complete freeze is required.
Handoff: /private/tmp/odylith-freeze-test-boundary-corrections-20261004/handoff.json,
SHA-256 d429e8ae577a3b519e727bb7437fd0aacc913e6ec4133da7be8f8e44f903dc77.

## Public detached qualification bridge missing (2026-10-04)

Read-only invocation audit finds R2's public scorer reachable through its API
but not the immutable onboarding finalizer. A saved public result retains
`semantic_release=not_requested`; the finalizer requires embedded passing
semantics, so independent public audit cannot qualify it without an impermissible
base rewrite or replay. The complete model-profile owner also deliberately
refuses a finite whole-journey claim until public measurements support one.
These are release qualification gaps, not demonstrated consumer semantic
failures. Audit: /private/tmp/odylith-v20-public-qualification-invocation-20261004.md.

Adopt the exact seven-ref public audit through the existing detached finalizer,
authenticated against immutable base/output/manifest and unchanged floors.
The existing profile owner must validate separately retained, fixed-public
complete timing evidence and a bounded decision before granting timing credit.
All unrelated browser, recovery, corpus, statistics, profile, retention and
independent-lens gates remain required. Never relabel diagnostic observations,
overwrite base results, replay generation to attach review, or enter protected
scoring for public evidence. Product timing custody remains separately open.

The exact frozen runtime/install/browser diagnostic executes 8,301 tests:
8,293 pass and eight fail. One assertion expects a superseded refusal message,
one guard lacks B-133's documented bounded 12-line allowance, and six isolated
statistics/identity fixtures omit the newly canonical relation ledger boundary.
Retain all failures; repair those test contracts without weakening real custody
or floors. Receipt:
/private/tmp/odylith-greenfield-release-freeze-v20-corrected-20261004/diagnostic-receipt.json.

## Source-predicate evaluator correction independently verified (2026-10-04)

The bounded R2 correction now refuses both original P1 controls: canonical
custody prevents accepted facts being relabeled as assumptions, and compiled
evidence cannot receive clarification-only credit. Genuine advisory and
material assumptions remain accepted. Independent review also exposed a P2
malformed material-row crash; the corrected actual loader returns incomplete,
unscored evidence with zero samples and an explicit issue, without omitting it.
Final independent verification passes 11 focused controls with no actionable
P0/P1/P2. The unchanged civic reverse universe remains 219 entries, including
212 accepted facts, four assumptions and three ambiguities. Review:
/private/tmp/odylith-greenfield-r2-independent-rereview-20261004.md,
SHA-256 2ebc3a1d8218449e0c8f3b8a7c8a70cca32146abe5f5376e0a9299aeadbf8efe.
The initial failed review and all three red artifacts remain retained. Full
frozen regression, actual independent public semantic audit and release
qualification remain open.

Independent review of the fixed initial R2 handoff passes 223 existing checks
but reproduces two P1 fail-open controls. Relabeling an accepted fact as an
assumption, then recomputing its audit, hides the source-support obligation.
Separately, an exact clarification accompanied by a valid compiled snapshot
receives passing clarification credit. Neither demonstrates an actual consumer
write; both permit false release evidence. Retain the original failed review
/private/tmp/odylith-greenfield-r2-independent-review-20261004.md,
SHA-256 39dbe91d8ac4c6de0caf46a1e136096b8ab24123499e40c6b3f920d8929f163e,
and its two red controls. Require canonical custody to govern reverse labels,
preserve genuine advisory/material assumptions, and refuse compiled evidence
on the clarification outcome before re-review. Matching outer hashes do not
repair either semantic contract.

R2 preserves native/protected rules and the original 40-case/425-ID public
source predeclaration while adding an explicit disclosed-public audit mode to
the existing evaluator. Source-only expectations and independently reviewed
observed forward/reverse support remain separate. Authentic civic custody and
its 219-entry complete reverse universe pass structural checks; source census
five actors and sealed representation six remain distinct. A real case phase
owns moved scoring, reducing the parent 1231 to 1020 lines. The settled slice
passes 375 initial tests, followed by 391 correction checks and 133 final
material-shape checks. Actual fresh semantic adjudication remains open;
synthetic unit audits are not real
reviewer evidence and no semantic fidelity or release pass is claimed.

Exact handoff: /private/tmp/odylith-greenfield-r2-evaluation-owner-handoff-20261004.json,
SHA-256 eaf05aca623e55f10387b053aaa96d66174e661438ddb2736dda8aacda6cf219.
No protected input, source expectation or original failed mechanism was changed.

## Full lifecycle readback correction verified (2026-10-04)

The corrected R1 slice reuses one passive lifecycle projector and one shared
design-binding validator in admission and release readback. The unchanged civic
package passes with 13 events, 12 contexts, five responsibilities, 89 witnesses,
six state fields and one off-path transition. All six original rehashed bypasses
and coordinated binding/lifecycle owner corruption now fail. Independent
rereview reports no actionable P0/P1/P2 and independently passes 259 checks in
2.35 seconds. Four runtime/release owners remove 97 lines relative to HEAD.

Proof: `/private/tmp/odylith-greenfield-r1-independent-rereview-20261004.md`,
SHA-256 628f1eeb1dcc89e26daa232ac50c9dcb965f7bdac884e57d44529785f33ae429.
Keep the original red evidence below. This closes the bounded lifecycle
readback defect; independent semantic-predicate coverage, annotation ontology,
source-versus-representation counting and complete release qualification remain
open. No protected holdout or frozen evidence was changed.

## Rehashed lifecycle corruption escapes partial readback (2026-10-04)

Independent R1 review reproduces a P1 in release readback, while consumer
admission remains protected. The initial canonical-reader correction passes
230 focused tests and unchanged civic custody, but only validates three design
duty families. Six detached civic mutations still pass after recomputing outer
hashes: an invalid lifecycle version, replaced state meaning or source quote,
changed off-path effect, nonexistent off-path owner, and invalid boundary
citation occurrence. A matching checksum does not establish valid custody.

Retain the failed review and exact red variants:
`/private/tmp/odylith-greenfield-r1-independent-review-20261004.md` and
`/private/tmp/odylith-greenfield-r1-lifecycle-red-20261004/red-result.json`.
No frozen output, source, receipt or seal was changed. No release semantic
qualification is claimed and the protected holdout remains unopened.

Reuse the existing source-duty design-binding owner in full admission and full
lifecycle readback. Rederive passive lifecycle with its current projector,
validate exact source citations, and compare every field and version. Do not
add a parallel lifecycle interpretation, model, schema, guessed raw candidate
or permissive hash-only check. Require all six rehashed controls to fail and
the original accepted package/admission to pass before independent rereview.

## Current source-duty custody is rejected by an older scorer (2026-10-04)

Read-only checks of unchanged civic v19 pass current canonical v18 relation
validation (13 events, 12 contexts, five responsibilities), receipt v7, the
source-duty-inclusive digest and all 89 exact atomic witnesses. Moved local
support coordinates, first-run pollution and swapped actors fail. The release
scorer still rejects source_duty as an extra field, omits it from its digest,
equates normalized actions with their whole source witness, and checks every
supporting event against first_path. This is verified evaluator drift; retain
its failures without modifying actual evidence or treating it as semantic loss.

The existing canonical readers and receipt/atomic validators own the correction.
Keep source witness, normalized role and full projected-value hashes separate;
retain exact source bytes, actor identity, role-local coordinates, disjoint
first-run selection and accepted-duty binding. No new semantic phase, parser,
fallback or scoring framework. Source-only semantic predicates and producer
bookkeeping counts are different; preserve every frozen expected obligation,
reverse-check invention and report those independent qualification issues.
Pure external projection binding alone cannot make the old scorer compatible.
Evidence:
`/private/tmp/odylith-greenfield-release-custody-contract-diagnosis-20261004/REPORT.md`
and the source-first public scoring feasibility report. No score or release
qualification is claimed. The protected holdout remains unopened.

The Q1 test transport also exposed a one-megabyte automatically generated
parameter name. Native pytest argument files complete the exact frozen suite;
four readable explicit IDs then repair canonical shard invocation without
changing the parameter values or test body. The focused file passes 70 checks.

## Public campaign clarification false failure (2026-09-29)

The fixed 40-case installed public campaign stopped on its first expected
clarification case, `release-accessibility-004-topic`. The host returned the
frozen `first_path` clarification in `50.633s`, with no staged transaction or
governed write. The release evaluator nevertheless assigned 0/10 because it
required an authored candidate's sealed receipt and canonical hash on a
clarification that has no admitted canonical candidate. Eleven candidate-
receipt errors are evaluator artifacts, not evidence of semantic failure.
Retained result: `/private/tmp/odylith-public40-0ab2929d9-evidence/public40.v1.json`.

The owning correction is in the profile evidence validator: retain the exact
host argv, source hash, one-call, zero-runtime-call, output hash, and no-write
checks, but require sealed canonical-candidate custody only for authored
transaction outcomes. A clarification must have no sealed candidate receipt.
Replace the test fixture that fabricates such a receipt; add positive and
negative clarification controls, then rerun the frozen evaluator suite before
resuming the public campaign. Do not change the host prompt, candidate schema,
runtime semantic path, or one-shot public case to satisfy this false oracle.

The evaluator now treats clarification as a source-bound raw host output with
no sealed candidate receipt; authored transactions retain the sealed custody
requirement. The retained first case re-evaluates as passed without a provider
call. The focused campaign/profile/statistics tests passed 176/176, with
separate fabricated-receipt and hash-mismatch rejection controls. The public
campaign rerun remains pending; this is not a release claim.

## Discovery wrapper evidence-path miss (2026-09-29)

The public replay wrapper rejected `COMMIT_RECOVERY_PROOF=1` before case
installation because discovery mode did not forward its supplied retained-
evidence directory to the controller. No model candidate was produced in that
attempt. The same maintained controller was invoked directly with the exact
14 host argv entries and an external retained-evidence directory; the one
installed public case and all four recovery subcases then passed. This is a
wrapper usability defect, not a semantic replay failure or release-tier proof.
Keep it open for a bounded wrapper forwarding test; do not add a repair path
or reinterpret the successful direct-controller result as final qualification.

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

## Post-application bounded checks (2026-10-05)

## Current upgrade and evidence posture (2026-10-05)

The actual v14-to-v32 upgrade release candidate returned `RC=0`, but the old theme-fingerprint source-owner check failed. A four-owner production correction was independently cleared at SHA-256 `89d5025041a9c94026900630561fdfbc83a9ad4900cc2c38d9154a7b42ba0d11`. Seven full unit modules then reported `169 PASS/1 FAIL`; the single failure was a new worker test that patched a CLI proxy rather than its real owner. The corrected real-owner CLI test passes `14/14` and production code is unchanged. Fresh installed upgrade proof remains pending under B-145. Preserve the old failed consumer evidence; do not promote the source correction or RC to release qualification.

At `23881abd0e8bd15ddc64fb869b581060d50c3302`, the Research and Agriculture fixed-case H0/H1 source reviews and separate terminal adjudications are CLEAR. The terminal records prove only their declared rejection/refusal/confirmation/idempotence controls, with zero observed terminal model/provider/projection entries and one canonical opener per confirmation/repeat. They do not restore release, aggregate, browser, protected, migration, or timing credit. CB-303 holds the source semantic and presentation findings; its exact external reports are the custody references for this checkpoint.

Root applied the reviewed Atlas correction and CI test-import correction.
With `PYTHONPATH` unset, 33 actual Atlas/CI checks pass in 2.99 seconds and
90 adjacent installation/migration checks pass in 3.60 seconds. Logs:
`/private/tmp/odylith-v20-concrete-corrections-target-tests-20261004.log`, SHA-256
`88fd61e0c2bd8a6f3de4277d18d8784ad66e5910e169d996a4f34fcd33164b4f`, and
`/private/tmp/odylith-v20-atlas-migration-neighbors-20261004.log`, SHA-256
`3e19cb5b7fa67596ccafec9c85abe62aa74054885036291c9f5160176688aa17`.
These 123 application checks are separate from the earlier 15 proposed-code
controls. No new complete 8,410-test freeze, Ubuntu pass or installed recovery
has run. CB-358 remains Open and all five migration classes remain unapproved.

The bounded continuation documentation is corrected to the current terminal
offer and authoritative CLI help, including receipt-bearing CONFIRM/REJECT
and `prepare` EDIT. Readback passes without transaction or model invocation:
`/private/tmp/odylith-v20-greenfield-doc-command-readback-20261004.json`, SHA-256
`b0498cdafa2cfa6a85fa2e181616b50dd02ff01eca7acf1e1d24c4433a6c46c0`.
This later source check does not alter the d002 path assessment or certify a
new release candidate.

## V33 installation-check contract drift (2026-10-05)

The clean `761fd5d4` package build passed all 12 checksums, but canonical fresh-install smoke failed before consumer controls: the existing release checker still expected host contract v53 and candidate format v22, while the packaged owners exactly match current v54/v23 source. The three reported errors are contract version, candidate version and the schema walk’s stale format enum. Preserve `/private/tmp/odylith-compass-verified-restoration-20261005/v33-smoke.log` (SHA-256 `b2f52def59dd9442dfd1a1b68a7295afe20b00e5a0b3f98df659f111a685c1ba`) and immutable v33 assets; this is a failed installed check, with no release qualification.

Use the authoritative version constants in this existing checker and require the new project-summary schema field, including its 600-character bound. Keep all source-duty custody, read-only write-audit, subprocess, baseline and installed lifecycle checks. Add absent/optional/malformed/unbounded-summary negative cases before a fresh checkpoint and package. Do not rewrite the failed v33 distribution or run semantic consumers against it.


The existing installation checker now imports the authoritative contract and format constants and requires an authored project-summary schema of 1–600 characters. All 61 module tests pass in 2.61s, including five absent/optional/malformed/empty/unbounded-summary negative cases and the unchanged custody/write-audit controls. Source package semantics and the 22 UI owners are unchanged. Preserve the failed v33 build and smoke; a new immutable v34 distribution and full installed smoke are required. Test log: `/private/tmp/odylith-compass-verified-restoration-20261005/v34-smoke-checker-unit.log`, SHA-256 `2ad12e4c3dad108c62808a646ed450a9a095bf72bce7406cc3e56b24ff4a8e92`.

The v34 checkpoint check also refused six stale Atlas fingerprints after the narrow five-input sync had initially rendered 47 fresh diagrams. Later Registry requirement synchronization changed two spec inputs; the staged check correctly evaluated that expanded source set. The published working tree remained valid and the read-only check changed no managed files. Preserve `v34-final-commit-ready.log` (SHA-256 `d972ef6060c0fe61609fc9062383d5bf583e34a9ee67fab4572fb4ffc76f0c91`) and refresh the actual affected Atlas source closure after requirements settle; retain the freshness gate. No code or topology change is required by this failure.


### V39 final Atlas fingerprint settlement

The first V39 staged commit check retained a freshness failure: 42 diagrams were fresh and five were stale after later Registry spec and forensic records settled during full sync. The canonical Atlas preview selects five review-only fingerprint updates and zero diagram renders. This is a final metadata settlement step; topology and diagram source are unchanged. The failed gate remains recorded at `/private/tmp/odylith-v39-commit-ready-20261006/report.json` (SHA-256 `4fb978ba086d8c9a6f809818e2dba85cf43ba4e2941b7ab8cd04c18b493e63cc`). Final refresh and a fresh staged check remain required; freshness, current full CI, installed proof, and release gates are retained.


### V39 predecessor preparation preflight

Before creating a fresh predecessor, read-only preflight rediscovered the retained v38 `prepare.py` failure: the pinned driver (`39c039c717e81a017c52ba1894962583ba76759a83cda9da7f2073de0a871cda`) calls `a.inventory(...)` before its local `a=load(...)` assignment. The prior campaign retained this `UnboundLocalError` and used a separate inventory continuation. V39 stopped before a namespace, install, or consumer write; it will predeclare a single external load-order correction and retain the original script and failure. Product code, migration fixtures, preservation laws, model calls, and the frozen candidate `73d1555d5c9942f3e9647eb4706d62843428e5a1` are unchanged.

The fresh v14 preparation then passed published install, authoring, reconciliation, validation, dashboard generation, and its positive linked-plan browser preflight. One extra optional help oracle incorrectly expected target-only `update-description` in v14; the actual help command returned zero and correctly listed `register`. The failed expectation is retained in the preparation report (`c8f5377ff95c8344284f8770f553657c6c3d5ad0ba904352cb35e94f446197d5`), with the 9,412-entry post-help consumer inventory exactly unchanged and no replay. Future preparation follows only the declared version-appropriate controls.

The first external upgrade driver then stopped while importing `local_release_smoke`: it bound the frozen checkout's release scripts but omitted its `src` directory, so the helper's `odylith` import failed. Native upgrade and browser calls both remained zero, and the whole 9,412-entry v14 consumer inventory remained exact. The immutable handoff is `/private/tmp/odylith-greenfield-v14-to-v39-migration-20261006/upgrade/first-failure-handoff.json` (SHA-256 `d8699a09a11d3d7c6497d31760df4cb004aa40d9be3eac3fe3061d9b08bc651d`). Correct only the external driver's frozen-source import binding, preserve the failed attempt, and require actual helper imports plus all 27 call bindings before the first native upgrade. Product source, package, consumer and qualification rules are unchanged.

The corrected external driver passed actual helper imports and all 27 call bindings, then stopped before any native call because its declaration changed the existing expected status literal. Preserve `/private/tmp/odylith-greenfield-v14-to-v39-migration-20261006/upgrade-r2/r2-first-failure-handoff.json` (SHA-256 `da894b6fdea8b83ea1e027b5322c0e6b41915c3c74b7af7557b5493d03d3d368`). Native and browser call counts remain zero across both attempts, with the exact predecessor inventory intact. Retain the driver's existing status contract and evaluate every precondition against the actual sealed inputs before dispatch. This is external harness learning; no product upgrade result or consumer retry is implied.

The first actual native upgrade then passed once, preserving source and customer records and regenerating all six pages. Its browser process stopped before Chromium, cells or screenshots because it used the managed application interpreter, which does not include Playwright. Preserve `/private/tmp/odylith-greenfield-v14-to-v39-migration-20261006/upgrade-r3/browser-prelaunch-failure-handoff.json` (SHA-256 `e22b4b5d3d52c9ed5b242ac9eafa796eb3669c51292688387cda24544286b468`). The upgraded 18,355-entry consumer inventory stayed exact. Browser orchestration must use the verified maintainer Python with Playwright while the unchanged adapter binds and verifies the actual installed package; target renderer and semantic probes continue using managed Python with isolation. Do not repeat the native upgrade or install test dependencies into the consumer.


## V42 independent harness review and missing public annotation input (2026-10-08)

Independent review found that invalid typed source references could escape the lexical custody check when their text contained no configured source identifier. Out-of-range occurrences, boolean occurrences and forged context all reproduced the failure with neutral text. The existing checker is being corrected to reject invalid reference structure and anchors explicitly; the prior 272-test handoff is retained and does not settle this finding. Source inputs, semantic floors and the original failed public run remain unchanged.

The original public source predeclaration is now absent at `/private/tmp/odylith-greenfield-public-v47-source-annotations-20261003/public-source-predeclaration.json`, expected SHA-256 `31eefdfa1f6d49f4c49a04525c773ca63fd7dc16b3d4ce8f4a1e5957cfdd6481`. The known V41 retained roots contain references to its hash, but no exact copy. Detached source-predicate qualification and any audited transport-metadata correction must wait for restoration of those exact bytes. Do not reconstruct annotations or use derived results as their replacement. The operator has been asked to restore the file; code, CI and package validation can continue. The protected holdout was not inspected.

### V42 harness correction settled

The final correction rejects invalid projected references independently of leakage vocabulary. The owner and independent reviewer each ran the same focused suite: 324 passed, zero failed. Fifty-two neutral reference and claim mutations refuse. All 40 frozen model source frames are byte exact, and all 258 retained case 2 files remain unchanged. Retained case 2 has five Radar, five Registry and five Atlas artifacts with zero package or custody findings. This offline check does not relabel the original public campaign, which remains two passes, two failures and 36 unexecuted cases.

Final handoff: `/private/tmp/odylith-v42-release-harness-finish-20261008-r3/handoff.json`, SHA-256 `931628d0a45383eb6d2a16afa9d9ec4b05ce766ee41e201b63ef67f6135d8ee5`. Independent review: `/private/tmp/odylith-v42-release-harness-independent-review-20261008/report.json`, SHA-256 `a31058608dcb0dcb8a33db8895a69dab3b50882ee131e628c44fd9b1d675124a`. No open P0/P1 code finding remains in the six-file harness correction; a fresh primary campaign can run after the source and package checkpoint.

Release qualification is still held. The exact detached annotation file remains missing. The five two-document intake cases truthfully use one `operator_prompt` transport and provide no lifecycle EDIT credit. A distinct frozen family of receipt-bearing EDIT controls is required; retain the existing format, quality and sample floors. Current CI, installed proof, native Claude and the original protected holdout remain separate gates.

The first V42 authored refresh was safely refused before publication because the operator supplied `--force` to selective authored admission. That mode requires explicit paths without force; the later full refresh may use force. Preserve `/private/tmp/odylith-v42-source-freeze-20261008/canonical-authored-sync.log`, SHA-256 `a6299299df51b9bb0cdcfa2cbc968218cc70b7b957db88dd8b785da332ddb6f9`. Correct the invocation only; no product change or bypass is needed.

## V42 actual release run and obsolete Project browser assertion (2026-10-08)

The fresh frozen `fe4a1eff` package now passes wheel/assets construction, all
12 checksums and canonical clean-install smoke. Package result:
`/private/tmp/odylith-greenfield-v42-dist-20261008/proof/result.json`, SHA-256
`8cecc096cb06a72259e43e8fdc6cf336224b734259db0936f32f2005ad028e45`.
One populated published v0.1.14 predecessor upgrades once and passes all 44
desktop/mobile browser cells, with exact 1,020-file installed source readback.
This establishes package and installed presentation mechanics, not the semantic,
timing, host, EDIT or holdout release gates.

The unchanged full Public40 campaign is running under predeclaration SHA-256
`80fc3933a09e1385549a6c1eab48150bd38b310046b019b07768027a00241eac`.
Its first seven completed cases have three passes and four failures, all four
reporting the same Project first-path browser text assertion. Independent
read-only inspection of the retained Accessibility005 and Accessibility007
artifacts finds no loss of their exact event sentences or supporting facts.
The frozen assertion expects `Actor: <actor> <event quote>` in a visible row;
the current human-facing presenter intentionally displays the exact quote once
and retains actor, actor kind and source event in closed Supporting details.

Correct only the existing release browser owner and direct caller. Verify exact
visible event quotes in declared order, exactly one initially closed native
disclosure, exact ordered actor/kind/source evidence, and keyboard disclosure
access. Retain every other authority and fidelity assertion. Missing, changed
or reordered narrative/evidence must fail. Do not weaken floors, alter the
presenter, mutate frozen inputs or rewrite the live campaign's failures.
Original retained case-result hashes are
`ae1c835704a0bf095d1b092fe1a520026ab7f1140de5fb8a8848374235ea8fda`
and `c35b0a51c8583e933e247d01415da02273f102a774f622b879e0217cd433a2bc`.

### Exact unpublished Compass-log recovery

Startup and the new proof log initially refused because one unpublished prior
assistant event remained appended to the canonical stream. The exact raw stream,
published preimage, event and diff were archived under
`/private/tmp/odylith-v42-ambient-stream-restoration-20261008`, manifest SHA-256
`cdf234a097375864cb4b1f696a91fbfebfe7ae3e80b8ff01ad2551b14f1755a1`.
The supported stream-only restoration passed with review hash
`94776ecc10dda47544a652fe188cb37a5b0af877d4dd80ad1168c02dda59f4c2`.
A subsequent log correctly refused because the exact original canonical append
receipt still required settlement. Inspection bound that receipt to the same
unpublished event; supported `compass log --abandon-restored` then archived and
retired receipt SHA-256
`1a6052a12266acd84949d199a3f412d792e8d7d1e9a9d4961ee318c22c1af517`.
The published generation and accepted history remain unchanged. No append was
replayed, no receipt was edited, and no engine or identity check was bypassed.

## Genuine lifecycle EDIT coverage gap

Read-only independent review confirms the existing release matrix executes only
initial prepares. Literal intake edit headings are preserved source text and
grant no receipt-bound lifecycle coverage. Four prepare-only EDIT successes
would also be insufficient: each credited positive sample must commit the edited
seal and pass the existing artifact, browser and quality checks.

The separate successor-v2 control census is independently clear: four frozen
initial sources plus an additive correction contain 118 facts, 90 relations,
84 statements and 339 exact references. All prior duties must be preserved with
authorization `not_required`; no changes or removals are permitted. Independent
report SHA-256 `e13822ef49cef489c8cb965f6091a71fe17548d6af259943de425965528022d7`
at `/private/tmp/odylith-v42-genuine-edit-census-independent-review-20261008/report.json`.
No initial or EDIT case in this new family has executed, and this census does
not replace the missing original Public40 annotation.

Extend the existing case and journey owners with an explicit optional lifecycle
correction. Defaults must preserve every original Public40 source frame and
identity. The new journey retains one initial pending seal and its delivered
receipt, executes one receipt-bound EDIT, verifies exact source and prior-artifact
custody, then confirms only the edited seal through the existing terminal owner.
Keep baseline evidence separate and score the edited result through the existing
quality pipeline. Missing or foreign receipt/hash, source mismatch, prior-duty
mutation and prepare-only positives must fail. Tags cannot grant EDIT credit.
Preserve all quality and sample floors; authenticate separate source families
and untouched result rows before any later aggregate qualification.

## V42 fresh campaign terminal result and oracle correction

The frozen native campaign stopped at case 12 after 1,816.06 seconds: five
passed, six failed only the obsolete Project first-path text oracle, and
`release-civic-tech-057-source` ended in a proposal-admission exception. The
remaining 28 cases and downstream controls did not execute. The native host
returned zero with 21,909 output bytes, but proposal admission returned two;
the diagnostic contains no actual refusal reason, so its schema-hash field
does not establish a schema root cause. Exact retained admission evidence is
under investigation. Post-receipt provider calls and runtime semantic calls
are zero. Preserve the complete failed run without retries or reclassification.
Campaign result SHA-256:
`636091a540562095a0bfc7fb37fee55fb7638d9647befe3ae3ccbb4456e623d1`;
raw campaign log SHA-256:
`51f38eb3145b5c65ee97bb3ce37457d5302ac915c5e9ddebd8ce12e748f65a2d`.

The separate three-file browser correction is independently clear with 147
passing checks, including 44 damaged desktop/mobile DOM rejection cells and
two positive keyboard controls. It preserves exact narrative order, closed
actor/kind/source details, all existing authority assertions and the unchanged
product presenter. Independent report:
`/private/tmp/odylith-v42-project-browser-oracle-independent-review-20261008/report.md`,
SHA-256 `90832a00f730ea43ec00c58ac52c6491f487ec663eb2b762f3da3b4b25d5f32b`.
This validates the harness correction; it does not turn the failed campaign
into a passing run or establish semantic or release qualification.

### Exact civic-tech admission diagnosis

Independent read-only diagnosis identifies the actual refusal:
`first_path_actions duty actor differs from its source actor`. Verified duty
f7 requires the publication editor. Candidate event 7 chooses human-actor row 1
(community facilitator) instead of the available correct editor row 5. The
candidate also has 12 events for 13 admitted duties: supporting-human/system
references shift and the last event is missing. This is candidate relation drift;
source evidence and the correct editor fact are present. Admission correctly
refuses before canonicalization and sealing. Fourteen retained artifacts remain
hash exact. Final handoff:
`/private/tmp/odylith-v42-civic-tech-057-admission-diagnosis-20261008/final-handoff.json`,
SHA-256 `e937410c6547a46dfbf906a5c745e3f834d49cfb763a6132798c7ab236b1c313`.

The verified inventory already owns actor/action meaning. Prior V47 identity
and V52 action-copy corrections left separate candidate actor addresses and
event mappings. Assess complete pre-candidate ownership of the typed actor/event
catalog, including all admitted duties and missing/ambiguous identity refusal;
do not repair the rejected candidate or fix only f7 while retaining the other
mapping defects. A proposed mechanism has no implementation or reliability
credit. The current original campaign remains failed.

The terminal progress log initially refused the obsolete component alias
`odylith-domain-intelligence` before appending. Retain
`/private/tmp/odylith-v42-public40-terminal-compass-log-20261008.log` and use
the already verified `release`/`dashboard` aliases for the new factual note.

### Current proof corrections and source ownership work (2026-10-09)

The receipt-bound EDIT journey and statistics enforcement are independently
clear for source/unit scope: 593 checks passed, followed by the final guard's
positive control and two failure/custody negatives. All 40 original input
frames and frozen qualification thresholds are unchanged. The final report is
`/private/tmp/odylith-v42-receipt-edit-journey-independent-review-20261008/report.json`
(SHA-256 `c4e9fdd335808d46247b2394cc9172111b7b18097561bd139faaa8629ab832e3`).
No native EDIT execution or release credit follows. Finalized-manifest caller
propagation, the exact source-family declaration, aggregation and independent
native semantic qualification remain required.

CI run 37888598065 completed with 16 failures, 10,201 passes and 10 skips.
Six failures match the separately corrected Project browser oracle. The other
ten now pass locally after tests adopt the intended human copy and closed
diagnostic/source disclosures while retaining exact facts, codes and retry
times. The seven-file handoff is
`/private/tmp/odylith-v42-ci-ux-contract-correction-20261008/handoff.json`
(SHA-256 `943738553e43e80c58327b1f7b0ccabb6468c52cc0e1c8c35cb421f48d2eaa49`).
Preserve the original failed CI and initial local failures; CI-green is unproved.

The Civic actor audit resolves eight human duties to five canonical source
occurrences. Facilitator f1/f2/h1 share one occurrence; editor f6/f7 share another.
Normalize supporting-human duties to the human performer kind. Equal labels
at different occurrences cannot establish identity. B-142 now owns complete
compiler projection of actors, events and action bindings, with fresh system
types affirmed by the same source-only verifier and exact historical passive
contracts preserved. Implementation has begun; its mechanism remains unproved.

### Compiler and caller review settled; native comparison started (2026-10-09)

The source-owned actor/event catalog is implemented in existing owners. The
single candidate references fixed events and cannot remap their performers or
omit verified action duties. The final 525-check compiler run passed; independent
review repeated all 525 checks. Review caught and closed a supplemental-title
alias that could promote an existing human/external performer, with positive
and negative controls. Exact passive initial and EDIT receipt/host pairs are
covered; fresh use of old pairs refuses. No model stage, retry or event-cap
change was added.

Finalized EDIT evidence now reaches campaign statistics, semantic scoring,
recursive model-profile scoring and saved public qualification. Review exposed
the missing recursive forwarding before native execution. A real finalized
manifest test accepts the retained case after consumer cleanup and rejects
missing or tampered evidence in both scoring paths. Five release-helper modules
passed 197 checks; parity and recursive controls passed 36 checks independently.
The ten earlier CI copy/disclosure failures also pass on this source basis.
These results do not change the failed CI or original campaign.

Independent compiler/caller review is clear:
`/private/tmp/odylith-v43-source-catalog-independent-review-20261009/review.md`,
SHA-256 `96aecde5081ccf71664e94cfe50f875e2b957aa67928ed78534070369884d3ae`.
The four EDIT inputs separately pass exact framing and source conservation:
`/private/tmp/odylith-v43-genuine-edit-family-independent-audit-20261009/handoff.json`,
SHA-256 `36be02e906cc14ea302786c88ef13e1ce96c6568f873dbb17a41d230e2462588`.
Their native committed sample count remains zero.

One fresh source-local Civic057 comparison was attempted against the unchanged
authority source `ba29e200be8c7e20b5e05fff4c882ab162f02b057b380e386c011630075a1d84`.
Its predeclaration pins 1,090 implementation/launcher files at
`/private/tmp/odylith-v43-civic-057-native-comparison-20261009/predeclaration.json`
(SHA-256 `c32780e3e0f991d135310844e59fcec57a6265c0ee849cbe0815d45277f35e5b`).
It stopped before candidate admission because the test repository had no active
immutable generation. This was root's empty-repository setup error. The four
host stages returned, but the admission mechanism was never evaluated. The
failed run retains 41 pinned artifacts, unchanged implementation files, zero
post-receipt provider calls and no delivered completion receipt. Handoff:
`/private/tmp/odylith-v43-civic-057-native-comparison-20261009/handoff.json`,
SHA-256 `30ea52e41d85a821f84213a30f17ac84001c30739854ab9603259ce3f27a6480`.
Do not reuse its candidate or grant semantic/release credit.

A separate consumer is now installed from the hash-verified frozen fe4 bundle.
Before another native invocation, the current compiler's exact model-free
active-generation guard passed and recorded the baseline identity in
`/private/tmp/odylith-v43-civic-057-installed-comparison-20261009/baseline-precondition.json`.
The next fresh comparison keeps source, compiler, model and caps unchanged and
uses this valid installed baseline. The original Civic failure and missing
original public-source annotation remain unchanged; the holdout is untouched.

### Same-source native confirmation advances past the Civic failure (2026-10-09)

The separately installed-baseline comparison returned a sealed transaction in
218.771 seconds and confirmed it in 2.783 seconds. Terminal status is CLOSED;
the compiler reader verifies the transaction and its active generation matches
the sealed write-set hash. All pending bytes and modes are unchanged after
confirmation. The immutable source is identical to the failed fe4 case.

The new package retains all 13 actions: seven first-path human actions, one
supporting human action and five system duties. Its five human performers retain
their exact identities. Event 7 is `publication editor` → `publishes`, bound to
`/human_actors/4`; the facilitator no longer owns that action. The missing final
system action is retained as event 13. Preparation used four host invocations
and zero post-receipt provider calls; confirmation did not regenerate the package.
This is a native development comparison on the current maintainer runtime,
using the frozen fe4 installed baseline. It is not a new installed-runtime or
independent complete semantic/UX release qualification.

Handoff:
`/private/tmp/odylith-v43-civic-057-installed-comparison-20261009/handoff.json`,
SHA-256 `c210475019e8e8d4b6d7d8af6c2829e17b0bcdc0b79b3378fff76058b6b97f89`.
The 57-artifact inventory retains the original native outputs, delivered receipt
and compiler-owned pending bytes. Mechanism readback SHA-256:
`360d643a2cba18e75c319c9f68780962deb4051ca55bf663af27d29f2a986c45`.
The earlier failed Civic case and failed empty-baseline setup remain failed.
The broader Greenfield unit/CLI/release-helper regression gate is now running
before another source checkpoint. Cross-domain, real EDIT, timing, host, CI,
annotation custody and final holdout gates remain open.

### Complete Greenfield regression exposes incomplete consumer adoption (2026-10-09)

The complete 172-module Greenfield runtime/install regression finished with
3,751 passed, 48 failed and 15 fixture errors in 330.71 seconds. The retained
log is `/private/tmp/odylith-v43-greenfield-regression-20261009/pytest-r2.log`
(SHA-256 `83b5d8df235cf146b0ddb713471af80f081b5d05a567edd2b76c5bff95fdbda6`).
Packaging remains gated on resolving these failures. The earlier focused passes
and native Civic development result do not replace this integration proof.

The first traceback suggested a missed runtime consumer, but a real compiler
reproduction corrected that diagnosis: `_authored_relations_from_intent` accepts
the freshly materialized canonical binding v3, which includes the action tables.
The failing test helpers instead inject raw host binding v4 directly into the
canonical intent. Its rejection is correct; keep the production reader unchanged
and adopt the shared validator's canonical return in those test helpers. The
reproduction is retained at
`/private/tmp/odylith-v44-source-catalog-reader-integration-20261009/reader-reproduction.json`.
Other failures include transport fixtures that
overlay an invalid fake candidate contract before reaching their intended
transport assertions, event-order tests that retain candidate-owned event IDs,
and immutable historical receipt tests entering fresh-only preflight. Treat
these as separate bounded corrections; preserve all timing, failure, custody,
source-order, actor-kind and exact historical-byte assertions. Do not classify
the complete failure set as stale tests or weaken admission to make it pass.

The bounded adoption now passes 36 runtime envelope/identity/proof checks,
40 ordering/passive compatibility checks and 228 install transport checks.
No production reader or validation rule changed. The ordering review retained
a genuine nonidentity canonical walk `[1, 3, 2]`: source first-path `[1, 2]`
stays ordered while cited prerequisite 3 precedes event 2. The original failed
gate and a separate real-process readiness failure remain retained. The latter
now establishes output custody before the unchanged process timeout; it grants
no latency qualification. An independent adoption review and the complete
172-module rerun are in progress.

The committed native Civic consumer also passes all 44 required desktop/mobile
browser surface states, retaining 111 screenshots and unchanged consumer bytes.
Root visually inspected seven normal-state screenshots across Project,
Registry, Radar, Atlas and Compass. This is single-case development UX evidence.
Handoff: `/private/tmp/odylith-v43-civic-057-browser-proof-20261009/handoff.json`,
SHA-256 `298ce15a318e90c9dcf9c6c181415c546243163a8661fd9ce96a099714c36a96`.
It does not supply cross-domain, authentic EDIT, installed-release, timing or
independent complete source-semantic qualification.

### Full integration gate is green (2026-10-09)

The complete 172-module rerun passes all 3,818 tests in 341.41 seconds, with
every declared runtime, harness and test pin unchanged during execution. There
are zero failures or fixture errors. The retained log is
`/private/tmp/odylith-v44-greenfield-regression-20261009/pytest.log`, SHA-256
`d39762882c38591f3a070d0474cd1a37fde338757e89465d38a3b12411283725`.
This supersedes the failed local regression as the current integration proof;
it does not change the failed CI run or earlier failed native campaign.

Independent review clears the 14-file envelope/transport adoption and its
36 + 228 focused passes. Report:
`/private/tmp/odylith-v44-test-consumer-independent-review-20261009/report.json`,
SHA-256 `1a8d29218a13d489ec272b210efbff557e3af3160b0a55ddb2dbeb8c2bdcabc0`.
Root separately reviewed the two ordering/passive modules, requested the valid
nonidentity-walk control, and integrated their final 40-test proof.
No production validation was loosened by this adoption wave. Freeze this source
candidate and move to installed cross-domain and authentic EDIT execution.

The four real EDIT journeys remain a separate, independently predeclared family.
Their eventual coverage must authenticate that family's own retained manifest
and independent source audit; do not append them to Public40 or alter its
denominators, original annotations, timing rows or results. Actual qualifying
EDIT count is still zero. Supplemental coverage cannot replace the missing
original Public40 annotation identity.

### Original annotation custody cannot be recovered from the operator (2026-10-09)

The operator states they do not have the missing original predeclaration.
The exact required SHA-256 remains unavailable; do not reconstruct it or grant
the old campaign qualification. Required release evidence needs durable custody
rather than a sole temporary-file copy.

Root prepared an evidence-only amendment for explicit operator approval:
`/private/tmp/odylith-v44-public-evidence-replacement-proposal-20261009/proposal.json`,
SHA-256 `51e01ab156b1c4e1810bf641035da7c317ea3a68f23f8f4081892d6bc99ca88f`.
It retains the exact 40-case source file hash
`4606712fcee60cfd99e3e45ece28cadf60e899c8e71d7b8b573f6b3e13e383d2`,
original order/text, 22 committed expectations, 18 clarification expectations,
every published floor and the untouched final holdout. It proposes a new
independent source-only annotation freeze before a new native campaign, with
version-controlled public annotations and an independent verified backup.
Old failed/unqualified evidence remains unchanged; the four real EDIT cases
remain a separate supplemental family. This is pending approval, not an
effective contract change. Source checkpoint, package and CI work continue.

### Frozen package reveals an unadopted smoke consumer (2026-10-09)

Candidate ac8a680bc2df4003f1fa6be957a33951d08c6879 builds the wheel and all
release assets successfully. All 25 files and 12 declared checksums are retained;
provenance binds the clean existing-branch archive. No Git worktree was created
and the exported source stayed unchanged. The clean-install smoke then fails
at candidate-contract validation after 39.33 seconds. Keep this run failed:
`/private/tmp/odylith-greenfield-v44-dist-20261009/proof/build-result.json`;
smoke log SHA-256 `b1a7bcb8ddc68f0c3c57aeb260a098b17863a32c9924542f311552cf9703ee06`.

The actual v55/format24 host contract is source-catalog-owned and exposes only
lifecycle binding v4. The smoke helper still expects candidate-authored events
and action-remapping binding v3. Canonical sealed binding v3 remains legitimate;
it is a different boundary. The 172-module Greenfield-named gate omitted
`test_local_release_smoke.py`, so its 3,818 passes did not prove this consumer.
Adopt the real raw contract in the existing smoke helper and test it against
current positive plus explicit legacy event, first-path and action-table
reintroduction negatives. Preserve strict versions, source digests, closed
lifecycle rows, installed write/subprocess audit and baseline checks. Do not
change the compiler or relax admission to satisfy the outdated smoke assertion.
Rerun only the affected tests, then freeze a new checkpoint for distribution
proof. Authentic native EDIT and cross-domain qualification remain outstanding.

The bounded two-file smoke-consumer adoption passes all 76 focused tests in
2.44 seconds, including the actual current contract and rejection of legacy
candidate events, first-path facts and all three action-remapping tables.
Strict receipt versions, digest shape, lifecycle allocation closure, citation
context, summary and installed write/subprocess audits remain required. Product
runtime source did not change. Root reviewed the diff; the focused run retained
all 124 Greenfield runtime pins unchanged. Test log SHA-256:
`d08f65dcb04f4c20b048a325d36fe512eba0d0ea8ab7f7e83b36c15579e78af0`, under
`/private/tmp/odylith-v45-install-smoke-adoption-20261009/pytest.log`.
This is local helper proof; clean-install/package readiness awaits the next
frozen run. The prior failed build result remains immutable.

### New frozen distribution passes clean-install proof (2026-10-09)

Checkpoint 8dfb9e7fe5ceed9b5c5c8e18417d078dfdd1ba0e is pushed on the existing release branch.
The frozen archive builds the wheel, all release assets and complete clean-local
installation smoke successfully in 547.72 seconds. Smoke itself passes in
377.00 seconds. The archive remains unchanged and the Git worktree inventory
is unchanged. Result: `/private/tmp/odylith-greenfield-v45-dist-20261009/proof/build-result.json`,
SHA-256 `e0b805c4634213203b0efe76bd663445c7b49169c830a22d48b330e3ac130848`. This closes the outdated install-check refusal on the
new candidate; the original ac8 failure remains retained.

The distribution has 25 artifacts, 12 valid checksums and 11 matching manifest
assets. All 1,020 shipped source/asset owners match the exact Git archive and
wheel; there are no missing or unexpected owners. An initial private inventory
mistakenly included 184 execution-created ignored Python cache files. It remains
retained as failed; corrected inventory uses exact regular archive members,
not a live directory scan. The package itself had no mismatch.

Independent review clears the prepared four-case native EDIT recipe conditional
on this package pass and separate activation pins. Input framing/conservation
is independently clear; all four loader frames match the immutable audited
inputs. Bind the exact package, runtime, driver, native profile and audit pins;
run one initial preparation and one receipt-bound EDIT per case, followed by
edited CONFIRM and the identical deterministic CONFIRM retry. Stop on the first
failure. Execution/qualifying EDIT count remains zero until actual retained
results pass separate independent semantic, artifact and browser adjudication.
Original Public40 evidence replacement remains pending operator approval; final
holdout, timing, host qualification and current CI remain open.

### First installed genuine EDIT fails before sealing (2026-10-09)

The independently audited four-case EDIT family ran against frozen installed
checkpoint 8dfb9e7fe5ceed9b5c5c8e18417d078dfdd1ba0e after clean package proof
passed. The first accessibility case seals its initial proposal in 187.809
seconds. Its real initial source/model binding checks pass. The receipt-bound
EDIT completes the authority gate, source inventory and source-only verifier
(complete, zero omissions), then returns one authored candidate. Deterministic
proposal admission refuses it before producing an edited seal. The underlying
invariant is not yet diagnosed; do not classify this as a stale checker or
weaken admission. The outward preparation error is generic and does not explain
the technical cause.

No CONFIRM, publication or browser check occurs. The five prior pending
artifacts retain their exact bytes/modes with no custody issues. Initial and
EDIT each use the four permitted host invocations, with zero post-receipt
provider/runtime semantic calls. EDIT whole-journey time is 211.514 seconds;
this remains diagnostic timing, not public latency qualification. The campaign
stops at the first failure after 477.774 seconds; the other three cases are
unexecuted. Qualifying genuine EDIT count remains zero of four. Retained
manifest coverage is incomplete and supplies no release credit.

Exact raw source, gate, inventory, verifier, candidate, observations and failure
are retained under `/private/tmp/odylith-greenfield-v45-genuine-edit-run-20261009/evidence/genuine-lifecycle-edit-v3-01/`.
Execution result SHA-256: `d98bf9fd8d8e9f647e0914aecefab9e74490b8530328943f0cd30da759dc0f40`.
Read-only deterministic diagnosis is assigned to the existing source-catalog
owner. Recover the actual inner refusal through the existing pure reader using
unaltered retained bytes. No native retry, source/candidate rewrite, repair,
model fallback, schema relaxation or holdout access is permitted.

Completed package proof and immutable EDIT inputs/audits also have a verified
private archive outside temporary storage:
`/Users/freedom/.codex/odylith-release-evidence/2026-10-09/v45/completed-package-and-edit-inputs.tar.gz`,
SHA-256 `5840a4cdc506afbf2f0f4b7d149927fa5a3435a4836310f506f8260fd3fcad54`.
This preserves new custody; it does not recover the missing original Public40
annotations or authorize their pending replacement.

### First EDIT diagnosis classified correctly (2026-10-09)

CB-209 owns the actual product defect: unchanged pure admission reproduces the
absent title, caused by product identity being coupled to source performer
classification. The runner correctly retained a failed, incomplete campaign;
qualifying EDIT remains 0/4. No statistics, fixture repair or harness regrading
can supply the missing product outcome. A coherent source-identity ownership
correction and a fresh installed comparison are planned in B-142. The terminal
failed run is durably archived with all 91 file hashes and unchanged failure
status (archive SHA-256 c65918e8e26b5abf7234f96b13ff99367d6a4fbfaf27e1e2316e1be888ebdcaf).

### Fresh identity contract: broad gate remains red (2026-10-09)

The 173-module unchanged-source gate fails 226 tests with 69 setup errors; 3620
pass. Install diagnosis maps182 failures plus the shared69-error cascade to
explicit fixture-contract omissions: independent identity or its verdict,
authenticated prior identity, identity-preservation decisions, clarification
nullability, one old receipt literal, and a synthetic unverified legacy snapshot.
These are diagnosis classes, not permission to relax floors or regrade evidence.
CB-209 separately owns the true early canonical actor-address guard gap exposed
by the new valid actor namespace; later sealing still refuses. Repair production
invariants at their existing owners and explicitly adopt controlled fixture facts.
Frozen public/native inputs and prior failed results remain untouched; genuine
qualifying EDIT is still 0/4. Public40 replacement remains pending operator assent.

### Release EDIT callers must carry verified prior identity (2026-10-09)

After explicit fixture adoption, the strict nine-module install run passes 470
tests and fails nine positive EDIT controls in 78.08 seconds, with 217 pins
unchanged. Both real release callers omitted the new prior identity argument:
`greenfield_matrix_journey._require_preserved_duties` and
`greenfield_matrix_statistics._edit_slice_evidence`. The failing positive checks
remain intact. Each caller now threads identity from the authenticated initial
proposal's source-duty ledger receipt into the existing preservation owner.
Missing historical identity still refuses; no title fallback or evaluator
regrading is allowed. Final focused and broad proof remain pending.

The pushed 8dfb9e7 checkpoint's CI finishes with one failure, 10,428 passes and
ten skips. The failure is the release component's stale generated requirements
and forensic sidecar. Settle those through the Registry owner before the next
checkpoint; do not weaken the convergence assertion. Retained failed CI log:
`/private/tmp/odylith-v48-ci-8df-final-20261009/failed.log`, SHA-256
`d97a6c041281b81264ab181eedf1923ced9e39ed124983e5507264e1719d67a8`.
This CI run predates the current runtime correction and supplies no current
checkpoint qualification. Public40 replacement remains pending approval.

### Full adoption gate isolates five residual fixture failures (2026-10-09)

The next frozen run retains all 173 modules and adds the CI Registry convergence
module. It finishes with 3,934 passes and five failures in 342.06 seconds; all
372 pins remain unchanged. The stale release dossier check now passes. Exact
log SHA-256: `58db9a99a89f61369532bbfefbb5f4d1ed98f6a78ea17499b5b4e706ff082903`.

The parser-retirement probe is Python embedded in a string, so the earlier
serialized-caller inventory missed it. Its JSON round trip discards typed source
identity and actions; receipt construction refuses before the actual public
proposal or retired-module assertion. Retain one typed candidate beside its
serialized bytes. Keep the real proposal and complete retirement assertion.
Three relation-corruption fixtures also drop source custody when rebuilding
their authored semantics; carry the original receipt so each intended corruption
reaches its owning validator. A fourth expects the later unbound-actor message,
but the new exact catalog check correctly rejects it earlier. Preserve the exact
wrong actor and strict refusal expectation. These are test adoption changes, not
permission to weaken admission, restore the hidden cache or regrade old results.
The failed full run remains retained; packaging is held for passing proof.

Both residual modules now pass: twelve relation checks and four parser-retirement
checks. All original corruption assertions remain intact. The embedded probe
retains its original strict retirement checks and reaches the actual public
proposal. No production code or shared fixture changed in this adoption. A fresh
complete frozen gate will determine checkpoint admission. The earlier identity
repair and failed-gate evidence also has a verified 141-file local durable archive:
`/Users/freedom/.codex/odylith-release-evidence/2026-10-09/v48/completed-identity-repairs-and-failed-gates-v48-20261009.tar.gz`,
SHA-256 `d621576287a192e73af0f6c1a3075090af6f02a5259a51fa11e46b4c37335beb`.
This is a local custody copy, not an independent backup or annotation recovery.

### Full current Greenfield gate passes (2026-10-09)

The unchanged-source v49 gate passes all 3,939 tests across 174 modules in
345.02 seconds; all 372 pins remain unchanged. Log SHA-256:
`24bb1b6c2354433b1ec0de27184164e002e9d34c26a71c71dd4e5dbb0810105b`.
This includes the previously failing release dossier convergence check. Earlier
failed gates remain retained. Commit this checkpoint, build and smoke-test its
exact Git archive, then run the same four independently audited native EDIT
inputs. Qualifying EDIT remains 0/4 until those actual outcomes pass. Original
Public40 annotations are unavailable; their replacement still awaits the separate
operator amendment. The final holdout remains untouched.

The first post-proof dossier check catches a concurrent snapshot change: the
parallel read-only UX audit emits three observer timeline events after forensic
synchronization (persisted event 1597; current event 1600). The full Greenfield
runtime/test proof remains unchanged. Finish the audit, synchronize the final
stream and check convergence before staging; retain the failed check. Keep
observers active and avoid a runtime or assertion change for this ordering issue.

### Installed v49 retains an actual semantic failure and a stale command oracle (2026-10-09)

The v49 four-case diagnostic campaign exits 1 on case 01 after 493.245 seconds;
the remaining three cases do not execute. Its sole automated quality issue is
`pre-confirm terminal decision choice is not the exact repo/hash-bound command`.
Actual displayed choices carry the edited transaction hash, repository root and
delivered completion receipt. CONFIRM and REJECT use receipt-bound decide;
EDIT uses the supported receipt-bound prepare route. The release oracle still
expects receipt-free decide for all three labels. Diagnose and adopt the actual
supported command contract without weakening exact root, hash or receipt checks.
Successful CONFIRM and repeated CONFIRM do not remove this failed observation.

Independent source-first adjudication separately finds real P1 first-path,
system-inventory and preserved-boundary ownership defects, recorded in CB-209.
Even a corrected command oracle cannot qualify this old run. The frozen
expected-streams file provides hashes and transport predicates but no semantic
annotations for those obligations. Keep that limitation explicit; do not invent
post-run ground truth or rewrite the original matrix. Future qualification must
combine independent source obligations with deterministic ownership predicates,
transaction readback and actual browser review. Qualifying EDIT remains 0/4.

The failed matrix, raw evidence and source-first report are retained in the
350-file local archive with SHA-256
`ffae49f1a2fa5e95a5ab24d2014095d712f0b23392b8fe04c549aca28b11b410`.
The campaign's partial manifest remains failed due to incomplete four-case
coverage. Temporary consumer repositories were cleaned; supplemental UX review
must use the exact hash-verified retained published after-image and identify it
as diagnostic evidence. Original Public40 annotations remain unavailable; the
operator reports having no copy. Their proposed replacement still awaits the
separate amendment. The final holdout remains untouched.

### Full 6c CI exposes two remaining consumer contracts (2026-10-09)

Run `37922431429` at `6c2a157d8753badcf9d8a4c7b10578cd7535ce3b` is failed:
10,454 passed, two failed, ten skipped. Identity and Claude assets smoke passed.
D-043 browser proof still requires removed compiler-version boilerplate. The HIIT
integration test serializes a candidate and loses its explicitly declared product
identity before synthetic source-duty receipt construction. Adopt the current
authored diagram contract and preserve fixture-declared identity; never infer it
from display titles or weaken runtime source custody. Log:
`/private/tmp/odylith-v49-native-failure-learning-20261009/ci-37922431429-failed.log`.
The 3,939-pass bounded gate at this commit did not include these integration
consumers. It remains valid for its recorded scope and is not full CI qualification.

### Same-four source expectations frozen before v50 output (2026-10-09)

Independent source-only annotation now records workflow membership, supporting and
recurring duties, authority, typed carriers, proof and exact H0-to-H1 preserved
allocation predicates for the unchanged four genuine EDIT inputs. Case 01's
previous v49 exposure is explicit; it supports no blind-generalization claim.
Cases 02–04 had no executed v49 output. Original expected-stream files remain
transport evidence only. Manifest SHA-256
`9f5d6aebd439c2c89c363be28dcaef06f8c27159560d0b40dfa2cce1582d3603`:
`/private/tmp/odylith-v50-genuine-edit-source-annotations-20261009/manifest.v1.json`.
Verified local archive of all 48 input/annotation files:
`/Users/freedom/.codex/odylith-release-evidence/2026-10-09/v50/genuine-edit-source-annotations-and-inputs.tar.gz`
(SHA-256 `1e4eee9ff66e6b9ce70f5003ac0bbe3f5168cd375bc561d57d1396ce23b60172`).
This does not restore or replace Public40's unavailable original annotations.
No v50 run or qualification is claimed.

### V50 current local proof and next decisive comparison (2026-10-09)

The complete current local inventory passes 4,006 tests across 180 modules, plus
seven generated Atlas nodes. It preserves the prior full scope and adds current
source-role, HIIT, publication, label and root-CLI coverage. The first generated
batch remains failed at 116 passed / 2 failed; only its two obsolete visible-ID
readiness cases receive fresh test-only adoption and rerun. CB-303 records exact
logs and unchanged publication custody. Aggregate proof:
`/private/tmp/odylith-v50-greenfield-regression-20261009/result.json`;
request SHA-256 `164271694a09d8a16a46b6140f70d8f2782fe59c562b30c7ef856f2f997b4d3c`.

Source-role implementation, prior failures and independent reviews have verified
local durable custody at
`/Users/freedom/.codex/odylith-release-evidence/2026-10-09/v50/semantic-wave-and-independent-review.tar.gz`
(SHA-256 `a37fb76ef51da843d9fa996f633b424958e7f82a7d97974d67ce274ab9251572`).
The next frozen package runs unchanged case 01 alone, then stops for independent
source-first adjudication against the already frozen four-case annotations. Only
a source-first pass permits the unchanged remaining three cases. Exact original
row union, all failures, runtime budgets and cleanup remain conserved. This is
private discovery proof, not Public40 replacement or release-grade aggregate credit.
Public40 amendment remains pending; the final holdout is untouched.

### V50 package clears; first native case fails (2026-10-09)

Checkpoint bae34ac859eda4ea36fe5184432635dc6b9ade2d built and passed clean local
installation. Custody verifies 25 artifacts, 11 manifest assets and 1,021 wheel-owned
files with no mismatch. Independent orchestration review and final dispatch
attestation passed before case 01. These prove package/custody, not semantics.

Prelaunch review caught a private activation script that read independent review
without requiring CLEAR status. It now explicitly requires
CLEAR_PACKAGE_AND_ORCHESTRATION. BLOCKED/PENDING probes refuse; CLEAR accepts.
The preliminary failed review remains retained. No runtime framework was added.

Actual case 01 exits 1 in 267.509 seconds: H0 seals; H1 fails ledger preflight;
no H1 or publication exists; cleanup passes. Remaining cases are stopped. The
source-first report is FAIL with no observed P0, four P1 findings and a P2 narrative
finding. CB-209/CB-303 record the owners and proposed-sequence qualification.
The failed run cannot be repaired, replayed or regraded. Qualifying EDIT is 0/4.

Verified read-only local archive (not an independent backup):
/Users/freedom/.codex/odylith-release-evidence/2026-10-09/v50/native-case01-failure-and-adjudication.tar.gz
(SHA-256 7f2202bfe688e61e64d5848d793bf1840be47d4c8ab87616d19251bb32bf66c8).
Its 144 members cover the run, actual adjudication, final dispatch and migration
preparation. The live diagnosis was omitted and remains separately pinned.
The operator confirms the original Public40 annotation file is unavailable.
The separate replacement amendment is pending; unavailability does not authorize
replacement annotation or a public matrix run. Holdout remains untouched.


### 2026-10-09 — complete v51 regression exposed unadopted test readers

The frozen 181-module Greenfield selection plus seven generated-page browser nodes completed with **12 failures and 4,019 passes** in 554.87 seconds. All 956 code/test input hashes stayed unchanged during the run. The original output remains at `/private/tmp/odylith-v51-greenfield-regression-20261009/pytest.log`, SHA-256 `17d1911eee37e786deee5169356ec71c125f622beaeb433e80360094cfd57fc2`.

The failures identify five test modules whose callers did not adopt the fresh closed compact result or human projection contract: verifier-ledger and raw actor tampering address the obsolete outer fields and fail before exercising refusal; four authority CLI checks read old prompt wording or outer inventory/citations; five cross-domain cases expect the old first-path filename for the explicitly proposed execution diagram; one transaction check requires the removed `outcome:` boilerplate. Production publication and the other 4,019 checks passed in this run, but these twelve checks confer no credit until corrected and exercised. This does not prove provider/native behavior.

The bounded follow-through owns only those five test modules: target the actual fresh nested inventory, retain every tamper/refusal/citation/control invariant, verify the first-run diagram route, and compare the human summary with the authored narrative. Keep passive readback and existing failed evidence unchanged. A fresh complete run of all five affected modules and independent review of the test changes are required before composing the complete local gate; no release floor, failure history, source fixture, provider behavior, or production code is to be changed for this adoption.


### 2026-10-09 — test adoption independently reviewed and local coverage composed

The five authorized test modules pass all 164 checks in 40.80 seconds. Only their five hashes differ from the original 956-pin complete run; the other 951 remain exact. Review confirms reachable nested-result tampering, citation/refusal guards, five-domain source/ownership checks, and direct summary/proof text are preserved or strengthened: `/private/tmp/odylith-v51-complete-gate-adoption-review-20261009/report.md` (SHA-256 `ef183ffcda34b06226816128838ee1d4c12fafacff0829146a176f3073b8cc53`).

The composed result is `/private/tmp/odylith-v51-greenfield-composed-regression-20261009/result.json` (SHA-256 `a8f73b75b9536027d524d8afb1cf6442e8a9432111de48a48ab0f6b3615f749d`). It replaces all original evidence for those five modules, including earlier passes, and retains successful proof only for 176 unchanged modules and seven generated browser nodes. The original complete run remains failed, not regraded. No clean monolithic rerun, native qualification or release claim is made.


### 2026-10-09 — current repository-wide CI remains failed

Run `37939289189` for `bae34ac859eda4ea36fe5184432635dc6b9ade2d` completed with 30 failed, 10,521 passed and 10 skipped. The retained log SHA-256 is `4cfff7b7755c4894941abbcef1bf85d077015b28817238d35f692d71d6dffbd9` at `/private/tmp/odylith-v50-ci-20261009/failed-job.log`. Twenty-nine browser failures span six modules whose disclosure/layout assumptions require inspection; the remaining Tribunal test expects `/authored_semantics/first_path_relations/0` while the source-owned graph correctly publishes `/authored_semantics/source_event_relations/0`. The Tribunal decision itself passes before that obsolete expected path assertion.

The 181-module Greenfield local composite gate is a bounded proof and does not supersede these repository-wide failures. Fix only grounded test readers, preserve all semantic and browser quality assertions, rerun every affected module, and obtain current-head CI. Do not rerun the old CI as a substitute, discard the failure or claim the release is qualified.

All affected compatibility readers now have complete current-module proof: six browser modules cover 115 checks and the Tribunal module passes 28. Independent review accepts the exact disclosure, selection and source-event reference changes; production and the request observer are unchanged. The intermediate 13-failure browser run remains retained, with both test defects explained and corrected. The local release regression is explicitly composed at `/private/tmp/odylith-v51-release-local-regression-20261009/result.json` (SHA-256 `913ca316bb33825cd1bb50e364a9d52d582608ffb5604bc1f173b69490458b7a`): 4,174 selected checks, 188 complete modules, seven additional generated-page nodes and 965 current code/test hashes. This replaces evidence only for affected modules; it does not turn the failed repository-wide CI into a pass. A frozen successor must obtain its own full CI, package and native proof.
