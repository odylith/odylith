- Bug ID: CB-209

- Status: FixedPendingRelease

- Created: 2026-06-26

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: High-variance installed greenfield prompts still stop before governed writes

- Impact: Harder real-world greenfield prompts can pass proposal generation but fail post-confirm create before Radar, Registry, Atlas, release, traceability, and quality-manifest records are committed, leaving only partial runtime/source artifacts.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 local release dists installed into fresh consumer repos under /Users/freedom/mock, including /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-17e8a6f6, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-cedafc79, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-b0713a0a, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-33bdb122, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-265cc0cf, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-3d13f434, and /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e7bc3be3

- Environment Update: 2026-06-29 fresh local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-af4117d8 installed into non-reused temporary consumer repos under /Users/freedom/mock. Later fresh custom variance used /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-72c100d1 with non-reused temporary consumer repos and persisted proof at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-72c100d1/greenfield-post-confirm-custom-variance-20260629.v1.json. The rebuilt dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-21ed5b0a passed the maintained installed matrix at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-21ed5b0a/greenfield-post-confirm-matrix.v1.json and the custom variance closure matrix at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-21ed5b0a/greenfield-post-confirm-custom-variance-20260629-21ed5b0a.v1.json.

- Environment Update: 2026-06-29 fresh variance after governance checkpoint 31cc84ef used the same rebuilt dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-21ed5b0a and persisted proof at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-21ed5b0a/greenfield-post-confirm-fresh-variance-20260629-31cc84ef.v1.json.

- Environment Update: 2026-06-29 rebuilt local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-597e5ca7 installed into non-reused temporary consumer repos under /Users/freedom/mock. The maintained matrix proof is /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-597e5ca7/greenfield-post-confirm-matrix-20260629-597e5ca7.v1.json, the fresh variance proof is /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-597e5ca7/greenfield-post-confirm-fresh-variance-20260629-597e5ca7.v1.json, and the exact failed-case replay proof is /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-597e5ca7/greenfield-post-confirm-indigenous-replay-20260629-597e5ca7.v1.json.

- Environment Update: 2026-06-29 source checkpoint after `e86b2b82` added a platform domain-leakage release gate before rebuilding the final dist. The guard derives distinctive fixture vocabulary from the maintained high-variance matrix, scans runtime/source guidance and the built wheel, excludes tests/governance/evaluation evidence, and is called by `local-release-assets`, `greenfield-post-confirm-matrix`, and the shared release proof lane. Source plus the previous `e86b2b82` dist passed the guard across 19 distinctive fixture terms; a rebuilt post-guard dist and installed matrix proof are still required before release readiness can be claimed for this checkpoint.

- Environment Update: 2026-06-29 rebuilt local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-3fbacb91 passed the platform domain-leakage build gate across 19 distinctive fixture terms. Maintained installed matrix proof persisted at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-3fbacb91/greenfield-post-confirm-matrix-20260629-3fbacb91.v1.json: 13/13 standard cases passed, every case scored 10/10, max create time 28.677s, browser proof passed, synthetic typed-probe rescue smoke passed in 35.129s, and temp cleanup was clean. Fresh non-reused variance proof persisted at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-3fbacb91/greenfield-post-confirm-fresh-variance-20260629-3fbacb91.v1.json: 10/10 new domains passed, every case scored 10/10, max create time 29.269s, browser proof passed, and temp cleanup was clean.

- Environment Update: 2026-06-30 committed checkpoint a258b913 rebuilt local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913. Maintained installed matrix proof persisted at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913/greenfield-post-confirm-matrix-20260630-a258b913.v1.json: 13/13 standard cases passed, every case scored hard 10/10, max create time 28.925s, browser surface proof passed, synthetic typed-probe rescue smoke passed in 33.537s, zero issues were reported, complete governed records were written, and temp matrix/rescue roots were clean.

- Environment Update: 2026-06-30 fresh non-reused variance proof against /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913 persisted at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913/greenfield-post-confirm-fresh-variance-20260630-a258b913.v1.json. Ten new domains passed with hard 10/10 scores, zero issues, complete governed records, browser proof, max create time 29.398s, and clean temp cleanup: maternal transport escalation, municipal tree permit appeals, fusion divertor maintenance window, school accommodation evidence circle, vaccine cold chain release, interactive museum loan condition, rail corridor vegetation outage, model risk validation waiver, robot lockout safety audit, and API deprecation migration cockpit.

- Environment Update: 2026-06-30 committed checkpoint 09e520b3 rebuilt local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-09e520b3. Maintained installed matrix proof persisted at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-09e520b3/greenfield-post-confirm-matrix.v1.json: 13/13 standard cases passed with hard 10/10 scores, zero quality/browser/leakage issues, complete governed records, browser proof, max standard create time 28.918s, average create time 25.815s, generated-term leakage proof over 213 readback terms, and synthetic typed-probe rescue wiring passed in 34.547s. Natural rescue-quality proof remains unproven and must not be claimed from that synthetic wiring proof.

- Environment Update: 2026-06-30 committed checkpoint dd718448 rebuilt local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-dd718448. Maintained installed matrix proof persisted at /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-dd718448/greenfield-post-confirm-matrix-20260630-dd718448.v1.json: 13/13 standard cases passed with hard 10/10 scores, zero quality/browser/leakage issues, complete governed records, browser proof, max standard create time 32.637s, average create time 29.091s, generated-term leakage proof over 213 readback terms, persisted temp-cleanup proof passed, synthetic typed-probe rescue wiring passed in 38.494s, and the real installed host-planned structured-rescue leg passed in 67.435s with `structured_rescue_semantic_patch`, provider-backed `last_repair_patchset_request`, a planned Tribunal patch summary, committed governed records, and no final quality issues.

- Environment Update: 2026-06-30 committed checkpoint 5c5fd0ed rebuilt local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-5c5fd0ed after actor-label custody and source-local Registry forensics regeneration. Maintained installed matrix proof persisted at /tmp/greenfield-post-confirm-matrix-5c5fd0ed.v1.json: 13/13 standard cases passed with hard 10/10 scores, zero quality/browser/leakage/prompt issues, complete governed records, per-case browser proof, max standard create time 28.685s, average standard create time 25.844s, platform-domain leakage proof passed across generated readback terms, temp-cleanup proof passed with no remaining simulation roots, synthetic typed-probe rescue passed in 34.851s, and the real installed structured-rescue leg passed in 61.940s with a provider-authored `structured_rescue_semantic_patch` under the 90s rescue budget.

- Environment Update: 2026-06-30 final committed checkpoint 925545d8 rebuilt local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-925545d8 after recording proof governance. Maintained installed matrix proof persisted at /tmp/greenfield-post-confirm-matrix-925545d8.v1.json: 13/13 standard cases passed with hard 10/10 scores, zero quality/browser/leakage/prompt issues, complete governed records, per-case browser proof, max standard create time 29.643s, average standard create time 27.049s, matrix-generated-term leakage proof passed across 213 generated readback terms, temp-cleanup proof passed with no remaining simulation roots, synthetic typed-probe rescue passed in 35.531s, and the real installed structured-rescue leg passed in 62.307s with natural rescue quality proven under the 90s rescue budget.

- Detected By: Custom high-variance installed greenfield matrix after release smoke and standard installed matrix passed

- Failure Signature: autonomous warehouse safety state and federated agent incident command returned create_returncode=2 in the earlier installed matrix; post-confirm quality manifest missing; Radar workstreams 1, Registry specs 0, Atlas sources 0, release records 0, trace nodes 0. A later installed matrix on cedafc79 fixed those two cases but exposed two additional platform failures: indigenous data sovereignty review returned create_returncode=2 before governed writes, and spacecraft anomaly triage committed records but failed rendered package quality because multiple Radar titles ended with a clipped article phrase `a`. The 33bdb122 installed matrix then reopened this bug: pediatric agency practice and security disclosure council returned create_returncode=2 before governed writes, with no quality manifest, one Radar workstream, zero Registry specs, zero Atlas sources, zero release/program records, zero trace nodes, and zero Project implementation prompts. The 3d13f434 installed matrix reopened the release gate again: 12 of 13 cases passed with hard 10/10 scores, browser proof, and complete records, but sparse disclosure confirmation scored 0/10 after governed writes because it produced only two Registry component specs, carried only three of four required domain anchors, and failed architect, engineer, and domain-expert matrix lenses.

- Trigger Path: scripts/release/greenfield_preconfirm_matrix.py custom cases using greenfield propose followed by greenfield create --confirm --release 0.0.1 --json

- Ownership: Domain Intelligence greenfield post-confirm semantic compiler and final quality gate

- Timeline: 2026-06-26: standard installed five-domain matrix passed at 17.404-18.353s with zero quality issues; custom high-variance installed matrix then failed autonomous warehouse safety state at 17.855s and federated agent incident command at 10.728s before governed writes. After semantic-custody and typed Tribunal-lens fixes, the cedafc79 standard installed matrix passed five cases at 17.074-18.574s with zero issues and all expert lenses passing. A harder cedafc79 custom installed matrix then passed autonomous warehouse safety state, federated agent incident command, deepfake provenance escrow, and fusion plasma shot readiness at 16.851-17.347s, but indigenous data sovereignty review failed before governed writes in 8.999s and spacecraft anomaly triage failed the package/domain-expert gate after writing records in 18.454s due clipped Radar article phrases. After the second semantic-custody fix, the b0713a0a dist passed release smoke, the standard installed matrix, and the harder six-case installed matrix with every create under 19s and every PM, architect, engineer, and domain-expert lens passing. On 2026-06-27 the 33bdb122 installed matrix failed two of five cases after Project dashboard prompt custody was added: flood shelter intake, semiconductor lab custody, and port berth carbon tariff passed with hard 10/10 scores in 19.878-22.416s, but pediatric agency practice failed in 14.282s and security disclosure council failed in 10.708s before governed records were committed. The 265cc0cf installed matrix then passed all five standard create cases with 10/10 brutal matrix scores in 26.626-31.091s, but release proof still failed because the packaged CLI rescue-smoke leg stayed on the standard tier, did not mark rescue activation, kept a 60s budget, and did not record `post_confirm_rescue_probe` as repaired.

- Blast Radius: Any consumer greenfield prompt with overloaded safety/state/agent/model/release language that deterministic completion cannot safely normalize before final writes

- SLO/SLA Impact: Fixed pending release by rebuilt dist a258b913. The committed maintained installed matrix completed 13/13 standard cases with hard 10/10 scores, browser proof, zero issues, complete governed records, and 22.874-28.925s create timings. The fresh non-reused ten-domain variance matrix completed 10/10 new domains with hard 10/10 scores, browser proof, zero issues, complete governed records, and 24.009-29.398s create timings. Synthetic typed-probe rescue passed in 33.537s under the 90s rescue budget; natural host-model semantic rescue remains a separate proof class.

- Data Risk: Low: governed records are not written after failed create; product intent can remain in runtime files

- Security/Compliance: No direct security exposure; governance trust and release-readiness claim risk

- Invariant Violated: Confirmed greenfield create must either write a complete governed project package within the standard/rescue budget or return exact recoverable blockers after exhausting bounded semantic repair

- Workaround: None acceptable; do not hand-edit generated project repos or weaken quality gates

- Root Cause: Retained repros showed multiple semantic-custody misses. First, system-generated outcome text such as product monitors reporting evidence was projected into user capability prose as modal drift (`can reports`). Second, passive review-state clauses such as `operator override records and release readiness must be reviewable` were misread as actor rows, promoting result nouns like `Release Readiness` into people. A separate modal normalizer misread `decide what can be released` as an actor plus verb, producing `what bes released`. The artifact-plan PatchSet executor also had a repair-custody risk: an untargeted row patch could mutate the only row instead of requiring an explicit row selector. The cedafc79 installed repros exposed two further owner defects: the semantic compiler treated every phrase beginning with `release readiness` as proof-control text, rejecting a valid first-path result event and falling back to proof-boundary prose; and first-path/actor recovery treated hyphenated noun compounds and passive object-state tails as action or actor facts, turning `research-use limits` into a fake `use limits` action and `recovery state before a corrective procedure is released` into a human actor. The rescue-path proof then exposed provider-path failed mechanisms: with `--ignore-user-config`, a blank Codex model inherited an account-incompatible CLI default, the automatic ladder still contained unsupported `gpt-5.3-codex`, and the Tribunal patch-plan schema had open-ended or untyped fields that strict structured output rejected. The architectural learning is that actor, action, object, passive state predicate, system-generated result, proof-control text, review target, provider model selection, and schema-constrained repair facts must be separated before rendering governed artifacts; row-level and provider-authored repair must be fail-closed without explicit custody.
  Additional Root Cause on 2026-06-27: Project dashboard source-launch prompts were admitted into the final package gate, but their renderer still treated clipped embedded clauses as full sentences. The shared Project `short()` helper re-added terminal periods to fragments, and source-launch then embedded those fragments before comma clauses, producing `workspace., validation points` and `workspace., input validation`. The same source-launch path joined an action with a visible outcome that semantically restated the action, creating low-quality `do X and receive do X` prompts. Separately, operator next-step previews could clip inside subordinate tails such as `when required information`, which passed existing gates but failed the premium human-readable bar.
  Follow-up Root Cause on 2026-06-27: Independent review showed the initial source fix was still incomplete. The duplicate action/outcome class survived for shorter object-repetition shapes such as `receive a disclosure and receive a disclosure` and `review compliance exceptions and receive compliance exceptions`, and the proof fallback still copied the raw first-path text after the displayed path had been semantically cleaned. Release proof also had an evidence gap: installed matrix and release smoke could prove normal governed writes, while rescue activation after a repairable typed failure was only proven source-local. The first rescue-smoke harness narrowed that gap but still under-proved release readiness because rescue was opt-in from the canonical matrix wrapper and the auto-rescue check used a monkeypatched installed-engine script instead of the packaged CLI. The engine manifest also recorded mechanical package repairs but not semantic or artifact-plan repair issue codes, so a real auto-rescue create could pass without durable evidence of which typed issue was repaired.
  Installed Harness Root Cause on 2026-06-27: The rebuilt 265cc0cf installed proof exposed a release-matrix custody bug rather than a packaged-runtime semantic failure. The matrix accidentally passed the internal rescue-probe environment to normal standard create cases, while the actual rescue-smoke `greenfield create --repair-tier auto` subprocess used the plain environment. The packaged CLI therefore had no injected typed final-gate finding in the only leg meant to prove auto-rescue, so it correctly stayed on the standard tier and recorded no repaired probe code. Standard simulations and rescue simulations must have opposite probe-env custody.
  Source-Local Brutal QA Repro on 2026-06-28: A fresh disposable source-local
  wildfire mutual-aid evacuation workspace simulation failed post-confirm before
  governed writes in 14.495s, then the temp repo was deleted. The final blockers
  were `greenfield rendered package repeats noncanonical prose across 4
  artifact(s)` for the accepted first-path outcome phrase and `quality lens
  architect missing explicit external system boundary`. Root learning: stricter
  independent package-lens readback is valuable, but it exposed two platform
  custody gaps. First, canonical accepted-intent first-path outcome text can be
  repeated by sanctioned projections and must be represented as typed canonical
  source text rather than treated like unsanctioned copy repetition. Second,
  reports, feeds, and constraint sources named in the accepted first path must
  become explicit external boundary facts or an exact ambiguity, not an empty
  `External systems` section that fails only at the final package lens.
  Installed object-list canonical-custody root cause on 2026-06-29: fresh dist
  `odylith-local-release-0.1.15-e7bc3be3` proved the previous typed projection
  custody still missed compact action-complement/object-list tails. First-path
  canonical projection facts preserve full actor/action/object facts, but the
  package can render a repeated tail without the lead action/object. Without
  typed tail custody, the repetition gate classifies legitimate sanctioned
  first-path reuse as noncanonical. The repair must stay in semantic projection
  custody, not disclosure/security vocabulary, regex towers, or weaker gates.
  Source-local quality blind spot on 2026-06-29: after the semantic projection
  custody repair, the same `security disclosure council` prompt completed
  source-local governed writes in 22.633s with 4 Radar records, 3 Registry
  specs, 6 Atlas sources, release/program records, and backlog-contract
  validation passing, but the generated Project Brief still contained a clipped
  coding-readiness gate ending `external vulnerability reports, affected.`.
  Root cause: Project Brief summary composition punctuated a `short_summary`
  comma-list fragment as if it were a complete sentence, and the existing
  package/public-copy gates did not catch this persisted readback defect.
  Registry-forensics leakage root cause on 2026-06-30: the platform leakage
  guard correctly protected source, shipped guidance, wheels, and runtime
  archives, but it still excluded Registry component forensics as generic
  governance evidence. `sync_component_spec_requirements` then mirrored raw
  Compass timeline summaries and artifact paths into component
  `FORENSICS.v1.json` sidecars, allowing high-variance simulation vocabulary
  to persist inside platform Registry custody even though the installable dist
  stayed clean. Failed mechanism: treating all governance evidence as the same
  raw repro lane. Casebook and Compass streams may retain concrete repro
  evidence, but Registry component forensics are platform component custody and
  must project generic event facts.

- Solution: Fix Odylith generally in semantic/projection ownership rather than domain-specific terms or rendered-string repair. Confirmed-intent recovery now localizes role-only actors to the project, keeps object modifiers out of actor labels, treats state-review predicates as review targets, rejects passive object-state subjects as human actors, and uses article-safe actor references. Outcome-action projection now converts system-generated results into modal-safe `review` or `see` actions before `user can` prose is composed. The role-can normalizer now preserves interrogative/modal clauses such as `what can be released`. First-path visible-result extraction now respects token boundaries inside hyphenated noun compounds, and semantic proof-control detection no longer rejects first-path `release readiness for ...` noun results while still rejecting control claims such as `release readiness requires ...`. Artifact-plan PatchSet row repair now refuses untargeted row mutations. A shared Tribunal lens contract now lets PM, architect, engineer, and domain-expert checks emit source-map target paths, semantic-node IDs, projection IDs, repairability, and repair owner at judgment time instead of reconstructing repair custody from check-name prose. The structured reasoning adapter now supplies an explicit live-proven Codex model for general structured repair when config is blank, maps the legacy Spark alias to the live CLI model, avoids the unsupported Codex ladder rung, and keeps user-config bypass reproducible. Tribunal patch planning now uses strict structured-output schemas for decision ledger, proof deltas, and replacement facts, then materializes the typed fact envelope back into caller-owned semantic or artifact-plan replacements after custody validation.
  Current Source Fix: Source-launch prompt composition now emits embedded prompt facts as fragments instead of sentences, strips dangling subordinate tails, uses generic material-term containment plus semantic overlap scoring to suppress outcomes that merely restate the action object, and routes proof fallback through the same cleaned first-path projection instead of copying raw confirmed text. Operator next-step preview trimming now detects incomplete subordinate tails near the end of clipped fragments, removing tails like `when required information` while preserving complete clauses such as `when required information is missing`. Release proof now runs installed rescue smoke by default from the canonical matrix wrapper. The smoke uses the packaged CLI in `--repair-tier auto`, injects one maintainer-only typed post-confirm finding through an exact internal release-proof token, requires the engine to auto-escalate to rescue, applies a typed semantic PatchSet marker, writes governed records, and fails unless the final manifest records `post_confirm_rescue_probe` as repaired under the 90s budget. The matrix harness now keeps normal standard cases on a clean environment and applies the internal probe environment only to the rescue-smoke create subprocess, with unit coverage for both sides of the boundary.
  Next Required Fix: extend canonical projection facts so action-complement and
  object-list tail variants carry fact identity, semantic node/source path,
  projection id, and sanctioned surface roles through package quality. Rebuilt
  installed proof must show the security disclosure council tail is accepted
  only through typed custody, while unsanctioned repeated prose remains blocked.
  Additional Required Fix: Project Brief readiness-gate summaries must clip at
  sentence-safe or comma-list-safe boundaries. If a summary is a clipped prefix
  of a longer source sentence, the brief owner must drop incomplete comma-list
  tails instead of adding a terminal period, and persisted readback tests must
  assert no readiness gate ends with an orphaned list fragment.
  Release Guard Fix on 2026-06-29: domain-leakage assurance moved from manual
  review into the maintained release custody path. `platform_domain_leakage_check.py`
  now uses the release matrix's fixture-owned distinctive terms to fail the
  build, standalone matrix, and shared release proof when project vocabulary
  appears in runtime or shipped guidance surfaces. The guard intentionally
  allows tests, Casebook/Radar/Compass/technical-plan evidence, evaluation
  corpora, and release notes so Odylith can learn from domain-heavy repros
  without letting those terms become generator or guidance defaults. Failed
  guard mechanism captured after proof: the first pass scanned persisted
  `greenfield-post-confirm-*` matrix JSON as if it were install payload and
  therefore flagged valid proof evidence as domain leakage. The guard now treats
  matrix proof JSON in the dist as evidence while still scanning the built wheel
  and text install payloads.
  Registry forensics custody fix on 2026-06-30: component forensics no longer
  store raw Compass summary prose or raw artifact paths. They preserve event
  index, timestamp, kind, component IDs, workstream scope, confidence,
  meaningfulness, and artifact counts while rendering generic event summaries
  and neutral artifact reference labels. The platform leakage guard now scans
  `odylith/registry/source/components` as protected custody, so future raw
  project-domain phrases in component specs or forensics fail release proof.
  Failed mechanism captured later on 2026-06-30: after source code already
  contained scenario-neutral forensics, a release build still failed because
  the committed sidecars had been regenerated through the pinned dogfood
  launcher, which emitted raw Compass event summaries such as prior
  high-variance project names. For unreleased source-side forensics custody
  changes, the sidecars must be regenerated and checked with the explicit
  source-local runtime before packaging; otherwise the source implementation
  and committed governed records can disagree and the build leakage gate will
  correctly fail.

- Rollback/Forward Fix: Forward fix only

- Verification: Run source-local and installed high-variance matrices including autonomous warehouse safety state, federated agent incident command, indigenous data sovereignty review, and spacecraft anomaly triage; require create_returncode 0, committed quality manifest, complete Radar/Registry/Atlas/release/trace records, zero package quality issues, all expert lenses passing, and create latency under 60s unless documented rescue path is active. Source-local proof on 2026-06-26 is green: focused Tribunal/greenfield proof passed 53 tests in 85.82s; the broad greenfield runtime pack passed 299 tests in 474.86s; six source-local CLI confirmed-create simulations passed with temp cleanup after every case. Timings were autonomous warehouse safety state 15.501s, federated agent incident command 14.685s, deepfake provenance escrow 15.143s, fusion plasma shot readiness 13.934s, indigenous data sovereignty review 15.344s, and spacecraft anomaly triage 15.333s. Every source-local run wrote four Radar workstreams, three Registry specs, six Atlas diagrams, five rendered surfaces, release/program records, 18 trace nodes, at least three required domain-term hits, zero issues, and all PM/architect/engineer/domain-expert lenses passed. Installed cedafc79 standard matrix passed five cases, but custom installed proof still failed two cases. Current source-local proof after the second fix: focused regressions passed 4 tests in 17.61s; indigenous data sovereignty review and spacecraft anomaly triage source CLI simulations both wrote governed records, produced complete Radar/Registry/Atlas/release/trace artifacts, reported zero quality issues, passed all expert lenses, and finished in 12.708s and 12.328s; the widened greenfield suite passed 162 tests in 148.37s. Final installed proof from b0713a0a is green: local release smoke exited 0; the standard installed five-domain matrix passed at 16.523-18.483s; the harder six-case installed matrix passed autonomous warehouse safety state 17.356s, federated agent incident command 17.020s, deepfake provenance escrow 16.602s, fusion plasma shot readiness 17.302s, indigenous data sovereignty review 17.649s, and spacecraft anomaly triage 17.107s. Every installed case wrote five Radar workstreams, three Registry specs, six Atlas diagrams, five rendered surfaces, release/program records, 18 trace nodes, zero package-quality issues, and passed PM, architect, engineer, and domain-expert lenses. Current rescue-provider proof: focused reasoning and Tribunal patch-planner tests passed 57 tests in 0.36s, compile proof passed, and a live Codex CLI `gpt-5.4` structured patch-plan call returned one validated `project_outcome` operation in 24.895s with no provider failure or custody rejection. Controlled source-local rescue-write proof passed in 39.768s against the 90s budget: a valid accepted-intent proposal had unique first-pass Radar semantic-coverage misses injected at prewrite, auto tier activated rescue, the real Codex CLI structured planner repaired typed semantic findings, the second pass passed, the normal write transaction committed four workstreams, three Registry specs, and six Atlas sources, final issue count was zero, and the temp repo was deleted after the run.
  Current source checkpoint on 2026-06-27 added Project dashboard prompt
  custody to the package gate and release matrix scoring. Focused blocker
  proof passed 6 tests in 35.44s; Project/source-launch/matrix proof passed
  10 tests in 0.51s; the broad greenfield suite passed 241 tests in 844.71s.
  The checkpoint is not release-closed until a fresh dist proves the installed
  standard matrix and at least one installed rescue-path simulation under the
  90s rescue budget with temp cleanup.
  Reopened installed proof on 2026-06-27: 33bdb122 built successfully but the
  installed standard matrix failed two of five cases before governed writes.
  The retained pediatric repro showed exact final blockers:
  `Project implementation prompt Create first implementation plan leaked
  malformed punctuation` and `Project implementation prompt Build smallest
  runnable slice leaked malformed punctuation`. Source replay after the fix
  produced zero rendered-package issues for the same saved confirmed intent,
  and source-mode confirmed create committed governed records in 15.428s.
  Focused source-launch, duplicate action/outcome, next-step clipping, and
  release-matrix rescue harness tests passed 15 tests in 0.41s. The current
  broad greenfield package and installed-matrix unit pack passed 245 tests in
  900.23s. Reviewer feedback then rejected the opt-in/synthetic rescue proof.
  The repaired source checkpoint passed 17 focused prompt/probe/matrix tests in
  0.43s and a real disposable source-local CLI auto-rescue probe completed in
  20.411s with requested tier `auto`, active tier `rescue`, two passes, zero
  issues, committed write transaction, and repaired issue code
  `post_confirm_rescue_probe`; the temp repo was deleted. The broadened
  source-level greenfield post-confirm pack then passed 282 tests in 933.23s.
  Rebuilt installed proof from 265cc0cf passed the five standard matrix cases
  with hard 10/10 scores in 26.626-31.091s, but failed release readiness
  because the default rescue-smoke case did not activate packaged CLI
  auto-rescue or record the typed rescue probe repair.
  After the harness custody fix, the same packaged 265cc0cf dist passed the
  full installed matrix: flood shelter intake 24.913s, pediatric agency
  practice 23.784s, semiconductor lab custody 23.365s, port berth carbon tariff
  22.452s, and security disclosure council 23.391s, each with score 10/10,
  zero issues, five Radar records, three Registry specs, six Atlas diagrams,
  and 18 trace nodes. The installed CLI auto-rescue smoke then passed in
  29.974s with zero issues and the same governed-record count floor.
  Final rebuilt proof from pushed commit f6a06af6 passed on dist
  odylith-local-release-0.1.15-f6a06af6: flood shelter intake 22.425s,
  pediatric agency practice 21.431s, semiconductor lab custody 20.657s, port
  berth carbon tariff 20.223s, security disclosure council 20.605s, and
  installed CLI auto-rescue smoke 26.842s. Every standard case scored 10/10,
  reported zero issues, wrote five Radar records, three Registry specs, six
  Atlas diagrams, and 18 trace nodes; rescue smoke reported zero issues with
  the same governed-record count floor.
  2026-06-28 evidence audit found a release-proof recurrence: this bug already
  required installed matrix proof by default, but the shared
  `run_release_proof_steps` lane still stopped after local release smoke and
  did not run `greenfield_preconfirm_matrix.py`. The matrix was therefore
  available as an explicit make target but not canonical release-gated. The
  same audit found the default matrix was still eight standard cases, rescue
  smoke could be read as full rescue-quality proof, and matrix JSON proof was
  stdout-only. The forward fix wires the installed matrix into the shared
  release proof lane, expands the default standard catalog to thirteen domains,
  persists `greenfield-post-confirm-matrix.v1.json` under the dist directory,
  records rescue as `synthetic_typed_probe_wiring_only`, and tightens domain
  expertise scoring so every case-required domain anchor must appear.
  The standalone `greenfield-post-confirm-matrix` target now also writes
  `greenfield-post-confirm-matrix.v1.json` by default, with
  `GREENFIELD_MATRIX_OUTPUT_JSON` as the explicit override, so explicit local
  matrix runs and canonical release proof both leave durable evidence instead
  of relying on terminal output.
  2026-06-28 brutal proof audit reopened the proof contract again. The first
  hardened release matrix still under-proved generated governance quality
  because its rendered-surface health check counted only Radar, Registry,
  Atlas, Compass, and shell output while the product shell also ships Casebook.
  The same audit found that browser proof was optional, ran against only one
  generated repo, and was absent from the maintained release wrapper and shared
  release-candidate lane. A live broad greenfield test also exposed Project tab
  prompt drift: operator next-step implementation prompts could pass through
  the selected workstream title and slice while omitting the accepted
  first-path contract. Those were failed proof mechanisms, not consumer-project
  defects.
  A second 2026-06-28 release-proof review found the next false-confidence
  recurrence: the renamed browser state proof still checked Atlas only by shell
  heading and could pass while generated diagram state failed to hydrate. The
  same review found the matrix JSON marked browser proof as passed for cases
  where browser proof never ran because post-confirm create failed. The forward
  fix adds Atlas generated-state assertions for rendered diagram buttons,
  generated count, active diagram ID, title, and loaded SVG/PNG assets; adds
  invalid Atlas diagram recovery; and moves browser-proof summary custody into
  a separate owner that reports unattempted proof as skipped and failed when
  browser proof was requested. This preserves the failed mechanism: heading-only
  shell checks are not release proof for generated Atlas state.
  Final rebuilt proof from dist
  `odylith-local-release-0.1.15-atlas-state-proof` passed the installed
  twelve-case standard matrix with per-case generated browser state proof:
  all standard cases scored 10/10, every browser proof was attempted and
  passed, zero browser issues were reported, create times were 20.660-23.125s
  with a 21.439s average, each case produced six rendered surfaces, twelve
  surface payloads, and twelve Atlas rendered assets, and the synthetic
  wiring-only rescue smoke passed in 27.280s. Matrix-owned temp directories
  were empty after the run, and the proof JSON was persisted as
  `greenfield-post-confirm-matrix.v1.json` in the local release dist.
  A later brutal installed audit with twelve fresh domains found no governed
  write failures, but it exposed a release-quality false positive in the
  Project implementation prompt surface. The package-manager supply-chain
  exception desk case completed in 21.671s, scored 10/10, passed all current
  prompt-quality checks, and deleted its temp repo, while independent prompt
  inspection found low-quality source-launch copy: `supplying chain exception
  desk user receives vulnerable dependency reports` and `tracking provenance
  and building evidence`. A focused reproduction on the same installed dist
  confirmed the five Project prompts were present and Odylith reported no
  `Project implementation prompt` issues. The failed mechanism is that
  source-launch proof prompts reused gerundized validation fragments rather
  than projecting base actions from the first-path semantic model, and the
  release matrix gave `implementation_prompts` 10/10 for row count plus coarse
  structural checks instead of semantic readability.
  The first source fix also produced an implementation-level failed mechanism:
  a prompt-quality guard scanned entire prompt text for gerund actor drift and
  falsely rejected valid title/context phrases such as `city permitting team
  uses...` and `Pain Entry Capture and Editing Service blocks...`. The forward
  fix scopes the guard to bounded proof-action segments (`proof gates for`,
  `evidence covering`, and `covering`) and requires lowercase gerundized
  subjects followed by actor-like markers and finite verbs. The same pass fixed
  a second source-launch projection defect where a visible-result phrase like
  `a user updates the plan...` was composed as `receive a user updates...` and
  a truncated proof clause ended as `clear..`.
  Independent review then found two more failed mechanisms before the rebuilt
  installed matrix could count as evidence. First, the semantic proof renderer
  required at least two first-path actions, so single-action paths such as a
  release readiness gate could still fall back to validation prose and render
  `evidence covering publishing release readiness...` while the prompt checker
  returned no issues. Second, the prompt checker briefly counted `-ing` words
  after `covering`, which falsely rejected valid noun-heavy domain results such
  as `screening intake, staffing review, and packaging approval`. The forward
  fix makes one-action first paths first-class semantic proof facts, phrases
  proof results as `evidence that the accepted path can...`, and removes the
  suffix-count guard instead of growing a regex tower.
  Post-fix rebuilt installed proof from dist
  `odylith-local-release-0.1.15-prompt-quality-proof` passed the maintained
  thirteen-case matrix plus the retained package supply-chain exception desk
  regression: all standard cases scored 10/10, every create finished in
  20.666-23.468s with a 21.694s average, every case attempted and passed
  headless generated browser proof, prompt findings were zero, total issues
  were zero, all PM/architect/engineer/domain-expert lenses passed, temp
  matrix roots were clean, and the synthetic wiring-only rescue smoke passed
  in 27.399s. Natural rescue quality remains unclaimed.
  Current source leakage-boundary proof on 2026-06-30: focused leakage,
  Registry spec-sync, Registry render, delivery-intelligence, and public-bundle
  tests passed 68 tests in 28.45s; py_compile passed for the touched scanner
  and Registry sync owner; `git diff --check` passed; the strengthened
  platform leakage guard passed across 285 distinctive fixture terms; an exact
  scan of `odylith/registry/source/components` returned zero findings; exact
  text search found no retained historical simulation phrases in Registry
  component custody; D-043 Atlas refreshed with 46 fresh / 0 stale diagrams.
  This proves source-local leakage custody only until a new committed-head dist
  is rebuilt and rerun through the installed matrix.

- Prevention: Keep high-variance installed simulations in release proof; require failure stderr/blocker retention for any matrix failure before cleanup; do not rely on standard-domain passes alone. Release proof must include the installed standard matrix and the installed CLI auto-rescue smoke by default; `RESCUE_SMOKE=0` is local debugging only and cannot support release-readiness claims. The shared release proof function itself must invoke the matrix, persist the matrix JSON proof artifact, and fail closed when standard cases, expert lenses, strict domain-anchor coverage, governed writes, rendered artifact checks, cleanup, or the wiring-only rescue smoke fail. Standalone matrix runs must persist the same proof payload instead of becoming stdout-only evidence. Expert-lens failures must carry typed Tribunal lens evidence at the point of judgment: source-map target, semantic node, projection, repairability, and owner. Failed mechanisms recorded here must not be repeated: broad proof-control rejection of product-result noun phrases, action extraction inside hyphenated noun compounds, passive object-state tails promoted to actors, rendered-string cleanup after Radar files are already written, blank Codex structured model inheritance under ignored user config, unsupported automatic model ladder rungs, model-facing patch-plan schema holes, raw first-path fallback after cleaned projection, source-only rescue proof substituted for built-dist rescue evidence, release-lane smoke substituted for installed matrix proof, opt-in rescue smoke silently under-proving the default matrix, synthetic installed-engine probes substituted for packaged CLI auto-rescue, semantic/plan repairs omitted from manifest repaired issue codes, or internal rescue-probe environment wired to standard matrix cases while rescue smoke runs without it.
  Updated prevention on 2026-06-28: release proof must include Casebook in the
  generated visible-surface set, must reject stale asset subpaths and malformed
  shell payload globals, and must run headless generated browser state proof
  for every generated standard matrix repo when the maintained release wrapper
  is used. That proof must cover Atlas generated diagram state, not only Atlas
  shell routing, and the persisted matrix proof must distinguish skipped browser
  proof from passed browser proof. `BROWSER_PROOF=0` is local debugging only and
  cannot support release readiness. Project tab implementation prompts must
  preserve the accepted first-path contract directly instead of relying on
  loose semantic overlap between a selected workstream title and the confirmed
  path.
  Updated prevention after the package-manager audit: Project source-launch
  prompts must render proof and validation obligations from typed first-path
  actions or other semantic facts, not from gerundized validation prose. The
  Project prompt quality gate must reject awkward semantic projection in prompt
  text and result text, and the release matrix must not award a 10/10 prompt
  score merely because five prompt rows exist.
  Guardrails from the failed source fix: do not scan whole prompt bodies for
  proof-action grammar defects when the prompt also carries product story,
  excluded-scope, readiness, and validation-command context. Quality guards
  must inspect the owned semantic clause they are judging, or they become a new
  brittle regex tower.
  Additional guardrail from independent review: do not use suffix counts such
  as repeated `-ing` words as semantic quality evidence. If the generator can
  project an accepted first-path action directly, fix the projection and make
  the prompt checker reject only typed or locally owned malformed structures.
  Additional failed mechanism on 2026-06-28: the maintained release matrix
  could still award a hard 10/10 when a generated create payload self-reported
  a passing `post_confirm_quality_manifest` and the harness observed count
  floors, even if the collected artifact package was empty or semantically
  unreviewed. The failed mechanism is self-reported custody: producer
  manifests, row counts, prompt counts, and domain-term substring hits are not
  sufficient release-quality evidence unless the matrix independently
  recomputes package quality lenses from the generated repo artifacts and
  compares that readback against the manifest. Do not repeat this by adding
  more phrase filters; strengthen the typed artifact-package readback and keep
  the score capped when independent package-lens evidence is missing or fails.
  Additional failed mechanisms on 2026-06-29 from a source-local wildfire
  mutual-aid simulation: the governed write completed in 23.170s and produced
  complete record counts, but brutal QA scored 0/10 because generated HTML
  referenced `odylith/surfaces/brand/lockup/odylith-lockup-horizontal.svg`
  without seeding the managed brand asset tree, and independent package
  readback treated the final committed program record as missing prewrite
  dry-run safety evidence. The fixes stay platform-owned: `brand_assets`
  seeds missing managed surface assets before greenfield dashboard refresh and
  the rollback transaction snapshots `odylith/surfaces/brand`; prewrite
  creates an explicit `prewrite_safety` evidence object that records program,
  release-target, release-assignment, and validation dry-run proof separately
  from final committed program state; and static surface health now rejects
  missing local HTML assets before browser proof. The retained wildfire replay
  passed source-local create in 23.205s with 22 brand assets seeded, six
  rendered surfaces, twelve payload assets, twelve Atlas assets, no browser or
  surface issues, all expert lenses passing, and hard 10/10 across all matrix
  dimensions. Manual shell-trap cleanup left three temp repos behind before
  explicit deletion, so future ad hoc simulations must include an explicit
  post-run cleanup assertion rather than relying on trap intent.
  Additional guardrail from the clinical trial role-collapse false positive:
  producer manifests, artifact counts, and package-lens booleans are not enough
  when role projections lose judgment separation. The matrix and validation
  gate must independently check Tribunal visible-role distinctness and
  role-appropriate suffixes before awarding expert-gate or release-readiness
  credit.
  Additional failed mechanism on 2026-06-29 from a source-local cross-border
  clinical trial consent simulation: post-confirm create completed in 30.980s
  and wrote the expected Radar, Registry, Atlas, release, traceability, and
  rendered-surface records, but the generated validation gate rendered
  beneficiary advocate, domain operator, risk owner, and evidence owner as the
  same visible actor label, `Cross-border Clinical Trial proof reviewer`. The
  maintained matrix scorer still awarded a hard 10/10 with zero issues. Root
  learning: expert-lens and release-quality gates must reject collapsed
  Tribunal role projections. A project can be complete and still be
  non-premium when independent judgment roles are indistinguishable. Do not fix
  this with domain terms; fix the generic role-projection and validation
  custody so distinct stable roles get role-appropriate visible labels or an
  explicit, reviewable reason when one actor legitimately owns multiple hats.
  Follow-up hardening from the same escaped class: the first role-collapse fix
  overcorrected by forcing separation even when the accepted intent explicitly
  named one human actor wearing multiple hats. The accepted fix records
  `actor_source` provenance for every Tribunal visible actor, allows shared
  labels only when they are grounded in explicit accepted actors, and requires
  generated judgment actors to carry role-specific language. The release matrix
  now checks both the create payload and persisted accepted-project preview,
  and fails on drift between the two. A fresh biobank consent simulation then
  exposed another false-positive 10/10: the evidence owner was incorrectly
  projected as `Specimen Link Ledger`, an internal evidence system. The generic
  fix stops drawing visible judgment actors from evidence objects or systems,
  requires generated judgment labels to be human/review-role shaped, and keeps
  explicit actors from the accepted intent as the first source of truth.
  Additional source-local proof after these fixes: the biobank consent replay
  completed governed writes in 21.867s with four Radar workstreams, four
  Registry specs, six Atlas Mermaid sources, twelve rendered Atlas assets,
  twenty Compass records, full release/project records, zero final issues, all
  expert lenses passing, and no temp leftovers after cleanup.
  Follow-up failed mechanism from the broader 121-test pack: the role-provenance
  hardening overcorrected by rewriting an explicit `Audit reviewer` actor into
  `audit proof reviewer`. That is not a project-domain exception; audit
  reviewer/auditor is a generic evidence-owner role concept. The fix extends
  the typed Tribunal evidence-owner vocabulary so explicit audit reviewers are
  preserved while internal evidence systems remain rejected. The targeted
  Tribunal pack passed 5 tests and the broader greenfield/matrix/local-release
  pack passed 121 tests in 86.48s.
  Additional failed mechanism on 2026-06-29 from the retained HIIT integration:
  post-confirm failed before governed writes because Atlas labels rendered
  `Saved session in history with<br/>date, workout, and total time`, leaving a
  visible line ending in `with`. The accepted-project preview also stored
  compact one-line Mermaid, so public-copy custody reported the failure from
  both rendered Atlas sources and the memory preview. This is a generic
  generated-label custody problem, not a HIIT-domain problem. The fix belongs
  in shared Mermaid wrapping/extraction: move stranded connector words to the
  following visual line and prove compact Mermaid visible-label extraction does
  not treat graph syntax or class declarations as public prose. The exact HIIT
  integration then passed post-confirm in 20.34s as part of a three-test
  focused proof, and the broader affected source-local pack passed 85 tests in
  70.23s.
  Additional installed release-gate failure on 2026-06-29 from dist
  `odylith-local-release-0.1.15-3d13f434`: the fresh maintained installed
  matrix failed sparse disclosure confirmation while all other standard cases
  passed. The failed case completed create in 21.474s with browser proof and
  governed records, but independent readback found only two Registry component
  specs, 17 trace nodes, and three of four required domain anchors. The expert
  failures were architect, engineer, and domain expert. Root learning: sparse
  accepted intents can satisfy final write custody while still underfilling the
  semantic topology and domain-anchor obligations needed for premium artifacts.
  This must not be fixed with disclosure/council/embargo keywords or another
  regex layer. The platform needs typed sparse-intent obligations in the
  semantic/artifact plan: derive enough distinct component responsibilities
  from actor, first-path, state-object, proof-boundary, and system facts, and
  carry required domain anchors as auditable projection obligations rather than
  substring afterthoughts.
  Follow-up source-local repair on 2026-06-29 fixed the sparse topology escape
  without disclosure-specific terms: terse proof boundaries are now preserved as
  grammatical definite proof clauses, explicit two-system confirmations are
  topped up by generic state/proof/release obligations, and component labels
  trim terminal punctuation before Registry projection. Focused sparse proof
  passed, including governed writes, at least three Registry component specs,
  retained `embargo` proof language, and no clipped `result is` / `before`
  tails. The same pass deliberately widened validation and found the release
  posture is still not green: the component/general quality pack failed 10
  tests and the post-confirm slop/live pack failed 3 tests. Durable failure
  classes now visible before the next release claim are: platform helper
  domain-vocabulary leakage, first-path sequence labels drifting from expected
  action fragments, clipped public copy in quantum-lab Atlas previews, repeated
  noncanonical release prose, rendered Atlas custody mismatch in a test path,
  source file size pressure in `greenfield_first_path_semantics.py`, a
  component-contract phrase normalization regression, and Project
  host-handoff prompt quality not being rejected by position. These are not
  reasons to weaken gates or add domain regex; they prove the next fix must
  stay in typed semantic projection, sequence-step ownership, prompt-quality
  collection, and governed surface custody owners before rebuilding a dist.
  Follow-up source-local repair on 2026-06-29 resolved that widened failure
  bundle without project-domain vocabulary or rendered-prose semantic repair.
  The durable failed mechanisms were: carried-subject parsing lost middle
  actor actions such as legal review, sparse result-object tails such as
  progress evidence were conjugated as verbs, quoted visible-result clauses
  such as clear "what changed" insights lost priority to broad dashboard
  lists, Radar rationale joined modal actor capability and finite product
  follow-up in one comma chain, Project handoff prompts treated sentence
  fragments as already-punctuated sentences, and Atlas sequence labels either
  swallowed named result-view tails or rendered dangling connector fragments.
  The fix moved carried-subject and visible-result disambiguation into focused
  first-path owners, made sequence projection distinguish evidence noun
  compounds from named view/readout/report result steps, rendered Radar
  follow-up as separate clauses, and normalized source-launch prompt paths as
  punctuation-neutral fragments. Proof after the repair: the full
  post-confirm slop/live pack passed 119 tests in 260.92s, the component and
  general artifact-quality pack passed 91 tests in 521.34s, and the sparse
  confirmed-intent/matrix guard pack passed 27 tests in 14.07s. Release
  readiness is still not claimed until an installed high-variance matrix and
  fresh local dist proof pass with persisted readback.
  Installed release-gate failure on 2026-06-29 from fresh dist
  `odylith-local-release-0.1.15-b81deed4`: the maintained thirteen-case
  installed matrix passed twelve standard cases with hard 10/10 scores in
  22.600-27.724s and synthetic auto-rescue smoke in 34.547s, but quantum
  communication lab failed before governed writes in 13.503s. A controlled
  retained repro deleted after evidence capture reproduced the exact blocker:
  `greenfield rendered package repeats noncanonical prose across 3 artifact(s)
  and 3 occurrence(s): A researcher ends with a completed run that reports
  whether the Bell inequality was violated, the QBER, and the established key`.
  This is a generic canonical-projection custody failure: a source-grounded
  first-path visible result can be repeated across sanctioned artifacts yet be
  classified as noncanonical because the package repetition gate still reasons
  over flattened strings rather than typed fact identity, semantic node,
  projection role, and sanctioned surface. Do not fix this with quantum terms
  or more phrase allowlists; fix the package readback to preserve canonical
  semantic fact provenance through artifact collection and repetition scoring.
  The same matrix exposed a release-proof failure mechanism: the persisted
  JSON did not retain create stdout/stderr or final blockers for the failed
  quantum case before deleting the temp repo, so failure diagnosis required a
  manual repro. Future matrix failures must persist bounded blocker evidence
  while still deleting temp repos.
  The generic repair keeps semantic projection custody typed instead of adding
  quantum wording or a repetition allowlist. `CanonicalProjectionFact` variants
  now preserve source layer, semantic node ID, source path, repair owner, and
  allowed projection IDs through compact supporting-tail variants; package
  repetition scoring admits a repeated chunk only when the rendered artifact's
  projection ID is sanctioned for that canonical fact. The release matrix now
  persists bounded failed-create stdout/stderr/blocker excerpts and asserts
  matrix-root cleanup after best-effort deletion. Source proof passed focused
  package repetition (`10 passed`), installed-matrix unit proof (`27 passed`),
  retained quantum confirmed-create integration (`1 passed in 27.92s`), and
  the four transaction tests rerun after stale refresh-stub custody was made
  explicit (`4 passed in 108.87s`). Release readiness remains unclaimed until
  rebuilt installed matrix proof passes.
  A follow-up JSON proof review found the first fix still populated
  `failure_detail` for passed cases by copying create stdout unconditionally.
  That proof-noise mechanism is now pinned so passed matrix cases keep
  failure fields empty while failed cases retain blocker excerpts. The same
  installed run exposed local HTTP server broken-pipe tracebacks from client
  disconnects; `_QuietHandler` now suppresses broken-pipe/connection-reset
  disconnect noise without swallowing CLI failures. Added proof:
  installed-matrix unit suite `28 passed` and local-release smoke suite
  `20 passed`.
  Final rebuilt installed proof for the current working tree passed against
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-typed-custody-test`.
  The maintained matrix produced `status=passed` with thirteen standard
  high-variance cases at hard 10/10, browser proof passed for all thirteen,
  no quality issues, no persisted failure excerpts on passed cases, and no
  remaining Odylith temp repos under `/Users/freedom/mock`. Create timings
  stayed under the standard budget at 22.615-28.216s; the retained quantum
  case passed in 27.015s with five Radar workstreams, four Registry specs,
  six Atlas diagrams, nineteen trace nodes, five Project implementation
  prompts, and all PM/architect/engineer/domain-expert lenses passing. The
  sparse confirmed-intent replay also passed at 10/10 with complete counts.
  Auto-rescue wiring smoke passed in 35.012s. This proof clears the specific
  CB-209 escaped blockers covered by this matrix, while broader quality work
  continues to require fresh high-variance simulations for new failure classes.
  Independent harness review on the same checkpoint found false-confidence
  risks that must be fixed before any release-readiness claim: release-matrix
  quality lenses still use producer-owned create payload previews for
  validation, component, next-step, program, prewrite-safety, and release
  judgments; domain-expert depth still relies heavily on lexical overlap;
  Project prompt scoring can still award 10/10 from count plus structural
  phrase gates; non-Atlas browser proof mostly checks shell routing and
  headings instead of generated state; matrix-root cleanup is not asserted
  after best-effort cleanup; and latency scoring times only create, not the
  wider proof/readback/cleanup loop. These are proof architecture defects, not
  generated-project defects.
  Follow-up source checkpoint on 2026-06-29 closed the most urgent false-score
  mechanism without weakening gates. Independent review found the release
  matrix could still award hard 10/10 scores when producer-owned payloads,
  stubbed lens reports, count floors, and position-based Project prompt
  checks looked complete even if governed artifact readback was shallow. The
  fix adds an independent package-evidence readback owner for project brief
  quality, Radar section/depth checks, Registry proof-contract text, Atlas
  topology labels, prewrite-safety evidence, Project implementation prompts,
  and domain-term carry-through; those findings now block the corresponding
  premium score dimensions. Generated-copy quality now consumes typed
  `ArtifactQualityUnit` leaves so metadata, shell commands, Mermaid labels,
  prompt fields, semantic facts, and free prose keep separate custody instead
  of being flattened into one text stream. Source-launch prompts now carry
  explicit `step_id` values, and prompt-quality checks prefer those IDs over
  positional inference. The failed mechanism is preserved: future release
  scoring must not accept count-only artifacts, dry-run-only prewrite safety,
  stub Atlas diagrams, producer-only lens payloads, or position-only prompt
  identity as premium evidence.
  Proof after the source fix: focused artifact/source-launch/matrix proof
  passed 49 tests in 1.97s, the affected broad greenfield quality suite passed
  228 tests in 579.08s after a small typed-unit decomposition, and
  `generated_copy_quality.py` was reduced below the 800-line soft limit by
  moving typed unit traversal into `generated_copy_quality_units.py`. A fresh
  six-domain installed adversarial run against the earlier
  `odylith-local-release-0.1.15-c259177b` dist passed in 17.365-43.304s with
  governed writes, browser proof, zero old-scorer issues, and temp cleanup,
  but that evidence predated the independent readback gates and therefore is
  not sufficient release closure. A rebuilt dist must rerun installed matrix
  proof under the hardened scorer before release readiness can be claimed.
  Installed proof against rebuilt dist `odylith-local-release-0.1.15-def2f783`
  exposed a new proof-harness defect before release closure: all thirteen
  standard scenarios completed governed writes in 22.566-27.824s, with the
  synthetic rescue smoke passing in 34.916s, but the hardened release matrix
  scored every standard scenario 0/10 because independent readback classified
  `odylith/radar/source/CLAUDE.md` as a Radar workstream and required product
  workstream sections on a cross-host guidance file. Root cause: the readback
  scorer selected generated governance records by broad folder/suffix shape
  and only excluded `AGENTS.md`, so the newer `CLAUDE.md` companion guidance
  surface crossed the custody boundary into generated artifact evidence. This
  is a failed mechanism in the proof architecture, not a generated-project
  content failure. Future readback must select governed records by record
  custody/type and exclude guidance/catalog companions consistently; do not
  repair this by weakening product-manager quality gates or accepting
  guidance-file false positives as generated project evidence.
  Verification after the custody-boundary fix is green. Fresh dist
  `odylith-local-release-0.1.15-e1dd08d6` passed the maintained installed
  matrix under the hardened scorer: all thirteen standard real consumer-lane
  creates passed with hard 10/10 scores, zero issues, per-case generated
  browser-state proof, and strict temp cleanup. Standard create timings were
  22.581-27.010s. Each non-quantum case produced four Radar workstreams, three
  Registry specs, six Atlas diagrams, twelve rendered-surface payload/assets,
  five Project implementation prompts, eighteen trace nodes, and passed PM,
  architect, engineer, and domain-expert lenses; the quantum case produced four
  Registry specs and nineteen trace nodes. Synthetic rescue wiring smoke also
  passed in 34.942s. Natural rescue quality remains separately unproven because
  this matrix's rescue proof is a typed-probe wiring smoke, not a naturally
  occurring host-model semantic repair.
  A fresh non-reused high-variance installed matrix against final local dist
  `odylith-local-release-0.1.15-a0dae6b7` reopened the post-confirm gate on
  2026-06-29. Eleven new standard cases passed with hard 10/10 scores, zero
  issues, browser proof, and create timings of 24.065-26.756s across transplant
  cold-chain exceptions, rural microgrid restoration, public defender discovery
  deadlines, fermentation contamination holds, special-education appeals,
  music clearance, hazardous rail inspection, API deprecation exceptions, coral
  permit review, auction provenance disputes, and bank fraud reimbursement.
  The twelfth ambiguous broad prompt, `model lab notebook`, failed before
  governed writes in 24.549s because the project brief preview and operator
  next steps repeated adjacent words as `teams Teams`. No Radar, Registry,
  Atlas, release/program, traceability, or Project implementation prompt records
  were written for that case. Synthetic rescue smoke still passed in 35.170s,
  and temp cleanup left no `odylith-greenfield-*` directories under
  `/Users/freedom/mock`. Failed mechanism: broad prompts whose accepted title
  or actor phrase begins with the same word as the actor/object can duplicate a
  semantic head across surface composition boundaries. Fix this at semantic
  title/actor/projection composition custody, not by adding domain-specific
  model/notebook vocabulary or weakening adjacent-repetition gates.
  Source fix checkpoint: finite action leads such as `records`, `sees`,
  `reviews`, and `launches` now remain actorless action fragments during sparse
  intent recovery instead of becoming plural actor labels; project-brief actor
  choice copy now asks who participates in the first path instead of echoing
  people/team categories; and the operator next-step overlap gate compares the
  implementation prompt against sanctioned first-path projection fields rather
  than flattened contract metadata, persistence text, and deferred-scope prose.
  Focused regressions passed 6 selected tests in 36.44s, the package-level
  `model lab notebook` regression passed, and a source-local CLI create for the
  same prompt completed in 19.708s with governed writes, 4 Radar records, 3
  Registry specs, 6 Atlas diagrams, project records, and temp cleanup. Remaining
  release obligation: rebuild the installable dist and rerun the high-variance
  installed matrix before claiming release readiness.
  Final source-local proof after code-hygiene cleanup moved the new sparse
  regressions out of the oversized slop-regression file and into
  `tests/unit/runtime/test_greenfield_sparse_recovery_regressions.py`. The
  sparse-recovery tests passed, the focused next-step/slop checks passed, the
  full live-simulation regression file passed 14 tests in 188.05s, and the
  `model lab notebook` source-local CLI create completed in 19.232s. Its final
  post-confirm manifest stayed on the standard 60s tier, completed the
  fixpoint pass in 5.149s, reported zero issues, passed the validation gate,
  wrote 4 Radar workstreams, rendered 3 Registry component specs, rendered 6
  Atlas sources, and produced project-brief and operator-next-step previews.
  The temp repo was deleted after proof. Remaining release obligation is still
  unchanged: rebuild the installable dist and rerun the high-variance installed
  matrix before claiming release readiness.
  Fresh installed release-gate failure on 2026-06-29 from dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e7bc3be3`:
  the maintained thirteen-case standard matrix passed twelve cases at hard
  10/10 and under 28s, but `security disclosure council` failed before governed
  writes in 12.96s with `greenfield rendered package repeats noncanonical prose
  across 3 artifact(s)` for the repeated object-list tail beginning `Affected
  partner review, embargo decisions, evidence custody, legal signoff, and public
  advisory release readiness...`. Synthetic rescue smoke passed in 34.393s, and
  temp matrix dirs were cleaned. This is a release-blocking semantic projection
  custody failure, not a domain-specific disclosure/content failure.
  Follow-up source-local proof for that prompt then exposed a second release
  quality blocker even after governed writes succeeded: the Project Brief
  readiness gate persisted `external vulnerability reports, affected.`. The
  root cause is source-level summary clipping in
  `greenfield_confirmed_project_brief.py`, not a consumer-project defect.
  Fresh recursive installed variance on 2026-06-29 reopened the release gate
  after the `13b796e9` proof. Ten non-reused projects produced seven passes and
  three failures with temp cleanup: `lead service line replacement equity`
  wrote records in 24.809s but missed one required domain anchor, `space
  telescope calibration anomaly` failed before governed writes in 34.656s on
  actor-led finite action inside user-can clauses across proposal summary,
  validation, release-gate, and promotion criteria text, and `carbon removal
  mrv attestation` wrote records in 23.131s but generated only two Registry
  specs. A parallel review found the matrix scorer can still overstate 10/10
  because domain readback can include internal runtime JSON, operator
  usefulness can count custody files as project brief evidence, count-only
  dimensions overlap, and the Python entrypoint can pass with skipped browser
  proof.

  Source-local checkpoint after the 2026-06-29 root-cause fixes: the telescope
  failure came from a generic carried-subject bug, where an actorless
  comma-chained first path could seed a fake subject from a later action word
  and then project malformed sibling actions. The fix stops bare
  material-action clauses from seeding carried subjects and consolidates
  actor-role nouns behind `greenfield_actor_roles.py` so recovery, fragments,
  and actor signatures share one role source. The carbon Registry
  under-provisioning came from release-scope polarity, where negative
  proof-boundary language was applied before affirmative proof/evidence
  ownership, dropping a proof ledger even though it was required as supporting
  release custody. The fix separates affirmative proof terms from negative
  scope tails and keeps proof/evidence owners as supporting components unless a
  stronger explicit exclusion applies. The scorer fix excludes runtime custody
  JSON and accepted-project source launch text from rendered domain readback,
  counts real project-brief and next-step preview artifacts instead of custody
  files, and fails the Python matrix entrypoint when browser proof is skipped
  outside an explicit debug flag. Focused proof passed 95 focused regression
  tests and the full 52-test general artifact-quality suite. Six fresh
  source-local simulations then passed under 23 seconds with hard 10/10 scores,
  zero issues, complete governed counts, and explicit temp cleanup: space
  telescope calibration, carbon removal MRV, lead service line equity, public
  comment response, apprenticeship credential readiness, and port berth carbon
  tariff. Release readiness remains blocked until a fresh built dist proves the
  same behavior in the installed consumer lane with browser proof.
  Installed proof from pushed commit `a4ede761` then passed from fresh local
  dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a4ede761`:
  all 13 maintained standard cases passed with hard 10/10 scores, zero issues,
  per-case headless generated-surface browser proof attempted and passed,
  complete Radar/Registry/Atlas/project-brief/trace evidence, and clean temp
  cleanup. Create timings were 22.726-27.078s, including the retained sparse
  disclosure and quantum communication lab cases. Synthetic typed-probe rescue
  wiring smoke passed in 33.430s with zero issues. This closes the installed
  proof obligation for this checkpoint while preserving the existing guardrail
  that natural host-model semantic rescue quality is not proven by synthetic
  wiring smoke.
  Fresh adversarial installed variance after that checkpoint reopened the gate:
  a non-reused twelve-case matrix against the same `a4ede761` dist passed eleven
  cases with hard 10/10 scores and browser proof, but `warehouse robot near miss
  investigation` failed before governed writes in 30.707s. The exact prompt was
  a generic near-miss investigation workspace where safety leads capture incident
  telemetry, preserve operator statements, map zone controls, route maintenance
  review, and publish restart readiness proof. Confirmed create rejected its own
  output with `semantic slop: gerundized actor-role action leaked` at
  `proposal.validation_strategy.0`, `proposal.validation_strategy.8`, and
  `proposal.semantic_model.first_path_contract.capability`, leaving no Radar,
  Registry, Atlas, release, traceability, or quality-manifest records. An exact
  disposable installed repro reproduced the same blockers and deleted the temp
  repo. A near-equivalent passing repro showed a separate artifact-quality smell:
  generated workstream/component names can still inflate into unreadable labels
  such as review-workspace changes-it titles. The failed mechanism is generic:
  the guard that is supposed to catch real gerundized actor/action splices still
  fires on valid noun/action facts after generated confirmation text weakens an
  action phrase into `safety leads route maintenance review`; the fix must
  improve semantic phrase custody and detector precision without domain
  vocabulary, whole-text prompt scanning, or weaker gates.
  Follow-up proof review then exposed another generic post-confirm quality
  failure inside an existing create fixture: `sequence_event_steps` preserved
  the accepted semantic first path, but its projection expander split
  connector-led object tails into standalone fragments. The Project Brief
  rendered `handles an accept, decline. Or more-info request.` at
  `project_brief.blueprint_sections.1.must_capture`, and the final public-copy
  gate correctly blocked `sentence connector splice` before governed writes.
  The failed mechanism was over-broad subject/action detection on short noun
  tails such as `required request context` and `more-info request`, not a
  request-handoff domain issue. The source fix keeps connector-led and short
  non-finite object tails attached to the prior action in the sequence-step
  owner, preserving real actor/action splits while preventing orphaned `. Or`
  or standalone object fragments in Project Brief and Atlas projections. That
  exposed the next required custody layer: the package repetition gate then
  correctly rejected the newly preserved sequence-step variants as repeated
  noncanonical prose until `greenfield_canonical_projection_facts.py` began
  carrying sequence-step projections as typed first-path facts. The request
  handoff source-local CLI replay then completed governed create in 19.609s
  with 4 Radar records, 3 Registry specs, 6 Atlas diagrams, zero issues, no
  `. Or` fragment, and temp cleanup. Related unit-fixture hardening also made
  no-refresh create tests explicitly bypass rendered-surface custody; live
  source-local create still exercises the real rendered-custody path.
  A 2026-07-07 installed 120-case volume run against
  `odylith-local-release-0.1.15-b678d1ee` reopened the same class with
  `autonomous shuttle disengagement`. The accepted first path was a single
  action with a long `using ...` evidence list, but `sequence_event_steps`
  reparsed the already-normalized semantic step and treated action-word nouns
  as new actions, rendering `... weather context. Explicit expert review,
  auditable decision ledger. And a final disengagement review recommendation`
  at `project_brief.blueprint_sections.1.must_capture`. The public-copy gate
  correctly blocked the sentence connector splice before governed writes. The
  generic fix is to trust `first_path_steps` as the canonical semantic split
  and stop running the looser sequence expander over those typed steps; fallback
  raw/legacy paths can still use the expander where no semantic split exists.
  Fresh current-head installed variance on 2026-06-29 reopened release quality
  again. The custom ten-case matrix against dist
  `odylith-local-release-0.1.15-af4117d8` passed nine non-reused domains with
  hard 10/10 scores and browser proof under 25 seconds, then failed the
  intentionally ambiguous `decision evidence room` prompt before governed
  writes in 25.708s. The no-write Product Intent Confirmation had already
  malformed the accepted first path as `Multiple teams bring reviews supporting
  facts`, `Multiple teams bring decides what is ready`, `Multiple teams bring
  preserves rationale`, and `Multiple teams bring publishes proof...`.
  Post-confirm correctly blocked those strings as modal/base-form grammar drift
  at fourteen proposal paths and wrote no Radar, Registry, Atlas, release,
  traceability, Project Brief, or implementation-prompt records. The failed
  mechanism is generic subject-boundary custody: first-path subject carry
  treated an unknown leading action as part of the actor phrase when a later
  object token also looked like a known action verb. The fix must repair actor
  subject boundary selection in the semantic parser, not weaken modal/base
  gates, add rendered-prose repair, or add domain-specific vocabulary.
  Source fix on 2026-06-29 repaired this failure class generically. The
  carried-subject owner now trims a trailing unowned action-like tail only when
  the remaining head is an actor-role subject, so `Multiple teams bring
  requests` carries `Multiple teams` rather than `Multiple teams bring`.
  Common action morphology now recognizes `bring/brings` and `group/groups`,
  preventing accepted action chains from collapsing separate events into one
  oversized semantic fact. Confirmed-intent completion also stops adding a
  synthesized proof ledger when the operator already supplied two explicit
  internal systems, because that previous padding could turn proof-boundary
  prose into malformed component names. Focused proof passed the targeted
  13-test subset in 78.18s, and the wider greenfield quality pack passed
  201 tests in 242.43s. An exact source-local replay of the `decision evidence
  room` prompt completed confirmed create in about 21s with final manifest
  passed, zero issues, 4 Radar workstreams, 3 Registry specs, 6 Atlas diagrams,
  6 SVG renders, 6 PNG renders, accepted-project truth written, and verified
  temp cleanup. Installed release readiness remains unclaimed until a fresh
  rebuilt dist reruns the maintained and adversarial installed matrices.
  Fresh installed proof from rebuilt dist
  `odylith-local-release-0.1.15-f5fef9e6` then reopened the sparse-topology
  class before release could be claimed. The maintained matrix passed twelve
  of thirteen standard cases with hard 10/10 scores in 18.441-43.304s and
  synthetic rescue smoke passed, but `sparse disclosure confirmation` scored
  0/10 after governed writes in 20.591s: independent readback found only two
  Registry specs and 17 trace nodes, so architect and engineer lenses failed.
  Root cause: the previous source fix suppressed proof/state topology padding
  for every two-system accepted intent. That protected rich explicit
  two-system narratives, but it also blocked the generic completion needed when
  accepted systems are terse labels or generated fallback rows. The same
  investigation found a public-copy defect: internal compiler labels such as
  `Relevant behavior:` and `Rationale:` could leak into rendered Registry
  component specs as clipped public fragments. The forward fix must distinguish
  sparse/generated rows from rich explicit rows and strip compiler-only labels
  before public Registry projection; it must not add disclosure terms, keyword
  stuffing, rendered-string semantic repair, or weaker expert gates.
  Source-local follow-up on 2026-06-29 now implements that generic boundary.
  Sparse confirmed-system completion tops up terse/generated two-row topology
  while preserving rich explicit two-system intents, and confirmed system-row
  expansion renders public descriptions without compiler labels. Focused
  sparse/confirmed-intent proof passed 3 tests in 13.41s, the broad affected
  greenfield pack passed 202 tests in 250.95s, and compile proof passed for
  the touched runtime modules. Installed release readiness remains blocked
  until a new dist proves this source fix in the maintained and adversarial
  installed matrices.
  Fresh installed proof from pushed commit `db69b062` then passed against
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-db69b062`.
  The maintained matrix produced status `passed`: all thirteen standard cases
  scored hard 10/10 with zero issues, generated browser proof passed for all
  thirteen cases, and no `odylith-greenfield-matrix-*` temp directories
  remained under `/Users/freedom/mock`. Standard create timings were
  21.927-26.698s, including the retained sparse disclosure confirmation
  passing with 4 Radar workstreams, 3 Registry specs, 6 Atlas diagrams,
  18 trace nodes, 5 Project implementation prompts, all expert lenses passing,
  and zero prompt findings. The retained quantum communication lab case passed
  in 26.698s with 5 Registry specs and 20 trace nodes. Synthetic typed-probe
  rescue wiring passed in 32.728s with zero issues; natural host-model semantic
  rescue quality remains a separate proof class.
  Fresh custom installed variance against
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-72c100d1`
  reopened the gate again with two failures across ten non-reused domains. Eight
  cases passed in 17.365-43.304s, but `ai eval red team finding board` failed
  before governed writes in 39.491s with forty-four typed semantic slop findings
  for gerundized actor-role action leakage, and `airport runway closure
  readiness` failed before governed writes in 20.325s because Project
  implementation prompt copy contained adjacent duplicate prose from a
  preposition-led actor label (`for For Duty Manager`). This is a platform
  actor-boundary and generated-prose-shape precision defect, not a project
  content defect.
  Rebuilt installed proof from pushed commit `21ed5b0a` then passed against
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-21ed5b0a`.
  The maintained matrix produced status `passed`: all thirteen standard cases
  scored hard 10/10 with zero issues, generated browser proof passed for all
  thirteen cases, and no `odylith-greenfield-matrix-*` temp directories
  remained under `/Users/freedom/mock`. Standard create timings were
  22.975-28.762s. The custom variance closure matrix also produced status
  `passed`: AI-eval red-team finding board, airport runway closure readiness,
  museum accession record-owner review, and battery materials release evidence
  desk all scored 10/10 with zero issues, browser proof passed, governed records
  were written, and create timings were 25.191-27.711s. This closes the
  title-compound actor false-positive and preposition-led actor duplicate-copy
  failure classes for the current installable dist. Synthetic typed-probe rescue
  wiring passed in 34.408s with zero issues; natural host-model semantic rescue
  quality remains a separate proof class.
  Fresh recursive variance after governance checkpoint `31cc84ef` reopened the
  release gate again. Ten non-reused installed projects were simulated against
  `odylith-local-release-0.1.15-21ed5b0a`; nine passed with hard 10/10 scores,
  zero issues, browser proof, complete governed counts, and 23.221-25.678s
  create timings. `Indigenous language curriculum evidence circle` failed
  before governed writes in 21.296s because confirmed Atlas flowchart `First
  Path Sequence` omitted the tail of the accepted first path. A source-local
  repro confirmed the accepted first path was three events: educators submit
  lesson plans, elders review cultural context, and coordinators record learner
  progress evidence. The semantic model retained all three events, but the
  rendered flowchart terminal node compressed `Coordinators record learner
  progress evidence` to `Progress evidence`, dropping enough distinctive tail
  terms for the Atlas tail-preservation gate to fail. This is a generic
  terminal sequence-label custody defect, not an indigenous-language or
  curriculum-specific failure.
  Independent validator review on the same checkpoint also found the hard 10/10
  score still overstates what is proven: several dimensions remain threshold or
  self-consistency driven, domain-term coverage is lexical rather than causal,
  role lenses are not equivalent to independent semantic expert approval,
  browser proof still focuses on successful generated-state paths, and natural
  rescue quality is not proven by synthetic typed-probe wiring. The failed
  mechanism is false confidence from count/threshold proof; future claims need
  negative fixtures, mutation tests, richer cross-field invariants, degraded UI
  browser states, and adversarial prompt fuzzing.
  Follow-up scorer hardening started from that review: independent domain
  readback can no longer prove premium quality only by finding accepted terms
  somewhere in the rendered package. The release scorer now requires the major
  generated surfaces to carry semantic source terms themselves, so a generic
  Registry or Atlas surface cannot hide behind domain words repeated in Radar,
  Project prompts, or runtime previews. This is a generic evidence-distribution
  gate, not a domain allowlist or generator rule.

- Agent Guardrails: Before claiming release readiness, run hard prompts with overloaded terms such as state, agent, model, case, claim, release, record, proof, system, consent, and verify governed writes plus expert lenses. Capture failures in Casebook before fixing. Release scoring must inspect persisted artifact readback, not only producer manifests or create stdout. Canonical projection fixes must preserve typed custody for compact first-path tails; do not add domain vocabulary, regex towers, or gate weakening for repeated object-list prose. Project Brief readiness gates must be audited from persisted readback for clipped comma-list fragments, not only package create status.
  2026-06-29 guardrail: do not "fix" title-compound user roles by adding
  domain allowlists or weakening the gerundized actor-role gate. The gate must
  keep rejecting direct malformed actor-action splices such as a lowercase role
  subject followed by a finite verb, while accepting product-title compounds
  where only the first token normalizes from gerund form and the suffix is a
  valid user role. Do not repair adjacent duplicate `for For` style defects by
  string-patching rendered Project prompts; actor completion must remove
  preposition-led and action-led role fragments before projection.

- Preflight Checks: Search CB-208 and this bug before changing greenfield completion, final quality gates, repair routing, or release matrix proof.

- Version/Build: Fixed pending release in
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-597e5ca7`.
  The source fix splits actor path-role cleanup into a dedicated owner,
  preserves direct gerund actor-role rejection while allowing title-compound
  user roles, trims preposition/action-led actor fragments before projection,
  strips longer title-suffix subjects from accepted-path actor descriptions,
  and moves non-goal derivation out of the confirmed-intent completion parent.
  Focused regression proof passed, the affected greenfield pack passed
  136 tests in 70.79s, exact source-local replays of the AI-eval and runway
  failures returned 0 while writing governed records, the rebuilt maintained
  installed matrix passed 13/13 standard cases with hard 10/10 scores, browser
  proof, zero issues, and 22.975-28.762s create timings, and the rebuilt custom
  variance closure matrix passed 4/4 cases with hard 10/10 scores, browser
  proof, zero issues, and 25.191-27.711s create timings. No matching temp
  project roots remained under `/Users/freedom/mock` after the installed runs.
  The subsequent fresh variance run passed nine of ten domains but failed the
  indigenous language curriculum evidence circle before governed writes on
  Atlas first-path tail preservation; current source work must fix terminal
  sequence label custody and then rebuild/rerun installed variance before any
  release-readiness claim.
  Source-local fix evidence: terminal flowchart labels now cap lossy compaction
  when the rendered terminal node drops distinctive accepted-event tail terms,
  and the fallback label is rebuilt from the first-path action clause instead
  of a vague result-object phrase. Mermaid label balancing also preserves short
  noun heads such as `Audio Capture and` instead of moving `and` to the next
  line. Focused sequence/connector tests passed, and an exact source-local
  replay of the indigenous-language prompt returned 0 in about 20s, wrote
  4 Radar workstreams, 3 Registry specs, 6 Atlas sources, and rendered the
  First Path Sequence terminal node as `Record learner progress evidence`.
  The source-local replay repo was deleted. Rebuilt installed proof on
  597e5ca7 passed the exact failed-case replay, the maintained 13-case matrix,
  and a fresh 10-domain variance matrix. All standard creates stayed under 27s,
  all cases scored hard 10/10 with zero issues, browser proof passed, synthetic
  rescue smoke passed in 32.401s, and no matching temp roots remained under
  `/Users/freedom/mock` after the runs. Natural host-model semantic rescue
  quality is still not proven by this synthetic rescue smoke and must stay a
  separate release-risk class.
  Fresh source-local scientific variance on 2026-07-01 reopened the
  post-confirm completion invariant. A gene-regulatory-network perturbation
  review workspace failed before governed writes in about 25s because the final
  gate reported `proposal.risks.2.statement leaked mixed actor-role casing`
  and the confirmed Atlas `First Path Sequence` omitted the tail of the
  accepted first path. This repeats the actor-role semantic slop and first-path
  tail failure classes, but the new architectural learning is priority
  ordering: non-critical projection quality findings must not strand a
  confirmed project with only `confirmed-intent.md`. Semantic custody should
  still be repaired at the model or typed-projection layer, but post-confirm
  completion must commit governed records with an explicit quality-debt ledger
  whenever the remaining findings are typed, non-critical projection defects.
  Do not repeat failed mechanisms by adding domain vocabulary, weakening
  semantic slop detection globally, or string-patching rendered prose after the
  fact.
  Source-local root-cause fix evidence: the failed scientific replay was not a
  domain-generation failure after all; the confirmed-intent Markdown parser
  failed to recognize ordinary inline section labels such as `Title: ...`,
  `State object: ...`, `First complete path: ...`, and `Proof boundary: ...`.
  That contaminated title, story, ambiguity, and first-path facts before
  artifact projection. Section parsing now has a dedicated owner that accepts
  both heading sections and inline label-value rows, and
  `greenfield_confirmed_intent.py` no longer owns that parser block locally.
  The exact source-local replay passed in 29.768s with a clean passed manifest,
  zero issues, committed write transaction, 4 Radar workstreams, 4 Registry
  specs, 6 Atlas diagrams, and temp repo cleanup. Regression proof:
  `tests/unit/runtime/test_greenfield_confirmed_intent.py::test_confirmed_intent_parser_preserves_inline_label_sections_for_scientific_intent`.
  Post-proof scorer hardening evidence: `greenfield_matrix_package_evidence.py`
  now checks domain semantic term distribution across Radar, Registry, Atlas,
  and Project prompt surfaces. The regression fixture proves a globally
  domain-rich package with generic Registry specs is rejected. Focused
  scorer tests passed 36/36, and the touched test file remains under the
  1500-line ceiling. A two-case installed smoke under the stricter local scorer
  passed the previously failing indigenous-language prompt at 25.898s and the
  retained quantum prompt at 28.487s with hard 10/10 scores and zero issues.
  The full installed matrix still must be rerun before claiming this stricter
  scorer is release-green.
  Focused reviewer regression on 2026-06-29 found the runtime quality-repair
  suite red after the scorer-hardening checkpoint:
  `test_workstream_titles_compact_while_keeping_clauses` rendered the workflow
  title as `Let Case Preparation Workspace User Organize Client Statements,
  Country Condition Evidence, Deadline Risk, Interpreter Needs`, losing the
  accepted `while keeping legal signoff separate from evidence collection`
  constraint before title projection. Root cause: first-path step extraction
  split the preservation constraint into a later fragment, while
  `workflow_title_action` chose only the first action/fallback fragment for the
  workstream title. The forward fix stays in action-title semantic ownership:
  it recovers useful preservation constraints from the full first path, attaches
  them to a compact action head before final title rendering, and uses shared
  semantic-word extraction plus string partitioning instead of adding a new
  regex parser. Focused proof now passes
  `tests/unit/runtime/test_greenfield_preconfirm_quality_repairs.py` and
  `tests/unit/runtime/test_greenfield_confirmed_backlog_terms.py` together:
  44 tests passed in 6.46s. Installed matrix proof against the rebuilt package
  remains required because this source fix landed after dist `2308795e`.
  In parallel, prior dist `odylith-local-release-0.1.15-2308795e` did pass the
  maintained installed matrix under the stricter current scorer:
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-2308795e/greenfield-post-confirm-matrix-20260629-2308795e.v1.json`
  reports status `passed`, 13/13 standard cases, all hard 10/10 scores, zero
  quality issues, generated browser proof for 13/13 cases, 24.156-29.311s
  standard create timings, and synthetic typed-probe rescue wiring at 33.109s.
  This is valid maintained-matrix evidence for the previous package, not final
  release evidence for the current source delta.
  Rebuilt installed proof after the source fix then passed on dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a46ef6cc`.
  The maintained matrix proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a46ef6cc/greenfield-post-confirm-matrix-20260629-a46ef6cc.v1.json`
  reports status `passed`, 13/13 standard cases, all hard 10/10 scores, zero
  quality issues, browser proof for 13/13 cases, 21.980-26.653s standard
  create timings, clean temp cleanup, and synthetic typed-probe rescue wiring
  passed in 32.990s. Fresh non-reused variance proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a46ef6cc/greenfield-post-confirm-fresh-variance-20260629-a46ef6cc.v1.json`
  passed 10/10 new domains with hard 10/10 scores, zero issues, browser proof
  for 10/10 cases, 24.258-26.624s standard create timings, and clean temp
  cleanup. The fresh domains covered transplant cold-chain exception review,
  algorithmic hiring appeal audit, nuclear canister inspection, tribal water
  compact hearings, robotics lockout/tagout, synthetic biology strain release,
  disaster cash assistance fraud review, digital repatriation consent,
  autonomous vehicle map-update safety, and agent tool-permission governance.
  Natural host-model semantic rescue quality remains unclaimed; this proof
  covers standard path and synthetic typed-probe rescue wiring.
  Follow-up leakage-proof hardening on 2026-06-29 closed a proof-custody gap
  in fresh/custom variance simulations. The maintained shell wrapper already
  ran `platform_domain_leakage_check.py`, but programmatic `run_matrix(...)`
  calls with custom `GreenfieldMatrixCase` rows reused only the default fixture
  vocabulary. A fresh variance pass could therefore prove completion and
  artifact quality without proving that its own distinctive project terms were
  absent from protected Odylith runtime, shipped guidance, and wheel custody.
  Independent review then found the first selected-case fix still too thin:
  required-term-only mining left some maintained cases with zero or weak
  distinctive coverage. The final forward fix gives maintained cases explicit
  `leakage_terms`, requires every selected case to contribute at least one
  distinctive term before simulation begins, filters platform-native words only
  when they appear as standalone terms, and still lets explicit phrases such as
  `agent tool permission tribunal` be scanned. Focused proof passed 50 install
  tests plus py_compile; the current `a46ef6cc` source/dist scan now covers 44
  explicit fixture terms, reports zero missing cases, and reports zero protected
  custody findings.
  Follow-up custody audit on 2026-06-29 found no actual project-domain leakage
  in current source or dist custody, but found the guard too narrow as a
  standalone release claim: it covered matrix terms, source runtime/guidance,
  top-level dist text, and the wheel, while omitting root `.codex` guidance,
  public `docs/`, historical consumer-domain sentinels, and Odylith payloads
  inside runtime tarballs. The forward fix keeps domain examples in release
  proof vocabulary only and broadens the guard generically: source scanning now
  includes `.codex` and `docs`, default release proof adds historical sentinels
  for prior escaped consumer domains, dist scanning recurses into runtime
  tarballs for Odylith launchers/runtime/guidance while skipping third-party
  packages and governed evidence, and line tokenization is cached once per
  line so archive proof stays bounded. Focused proof passed
  `tests/unit/install/test_platform_domain_leakage_check.py` and
  `tests/unit/install/test_greenfield_preconfirm_matrix.py` together:
  52 tests passed in 0.24s. Source plus dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-cd6cf643`
  then passed the strengthened platform domain-leakage check across 49
  distinctive fixture terms with zero protected-custody findings. The matrix
  selected-case preflight remains selected-case-only; the standalone release
  leakage guard owns the broader historical sentinel proof. Fresh local release
  dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-14f5102a`
  then rebuilt from the committed checkpoint and passed the same strengthened
  49-term platform domain-leakage build gate.
  Reopened installed proof on 2026-06-29: the fresh dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-14f5102a`
  passed the strengthened 49-term platform domain-leakage gate, but the
  maintained installed matrix proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-14f5102a/greenfield-post-confirm-matrix-20260629-14f5102a.v1.json`
  failed 4/13 standard cases. `flood shelter intake` and
  `apprenticeship credential readiness` stopped before governed writes with
  `accepted-project memory preview leaked adjacent duplicate word prose`;
  `semiconductor lab custody` and `package supply chain exception desk`
  stopped before governed writes with `project dashboard preview leaked
  adjacent duplicate word prose`. Each failed case returned create code 2,
  wrote no quality manifest, and produced zero Radar workstreams, Registry
  specs, Atlas sources, release/program records, trace nodes, trace
  workstreams, and Project implementation prompts. Nine standard cases still
  passed with hard 10/10 scores and the synthetic typed-probe rescue smoke
  passed, but the release claim is falsified because repairable final-gate
  preview-copy defects were not cleared internally before the transaction
  returned. Temp matrix roots were clean after the run.
  Forward fix and precommit proof: source now treats concrete
  `project_dashboard_preview.*` leaves as exact artifact-draft repair targets
  and fixes the artifact-draft path parser so list-index paths such as
  `created.components[0].feature_history[0].summary` and
  `host_handoff_prompts[0].prompt` reach the addressed scalar leaf. This keeps
  repair authority in source-owned typed leaf paths and the existing generic
  duplicate/tail cleanup; it does not add domain vocabulary or a new prose
  patch tower. Focused proof passed 44 artifact-plan/quality-repair tests,
  25 package/source-launch/repetition tests, 76 post-confirm engine/repair
  tests, py_compile, Casebook validation, and the 49-term platform
  domain-leakage guard. A fresh installable local dist then replayed the four
  failed standard cases with browser proof and all four passed with hard 10/10
  scores in 27.038-29.000s. The full maintained installed matrix proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-repair-routing-precommit-matrix.v1.json`
  passed 13/13 cases with hard 10/10 scores, zero issues, generated browser
  proof, complete governed records, max standard create time 29.244s, and
  synthetic typed-probe rescue wiring in 33.836s. Temp matrix and rescue roots
  were clean after the run. Post-commit release proof then rebuilt committed
  checkpoint a258b913 into
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913`;
  the maintained installed matrix proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913/greenfield-post-confirm-matrix-20260630-a258b913.v1.json`
  passed 13/13 standard cases with hard 10/10 scores, zero issues, browser
  surface proof, complete governed records, max standard create time 28.925s,
  and synthetic typed-probe rescue wiring in 33.537s. Temp matrix and rescue
  roots were clean after the committed-dist run. A fresh non-reused ten-domain
  variance run against the same committed dist passed 10/10 with hard 10/10
  scores, zero issues, browser proof, complete governed records, max standard
  create time 29.398s, and clean temp cleanup.
  Follow-up domain-custody audit on 2026-06-30 found the strengthened release
  guard still missed one source-level risk: generic runtime helpers carried
  example-domain nouns as visible-result hints. The source fix removed those
  nouns from runtime decision lists, promoted them into historical leak-guard
  sentinels so protected source custody fails if they reappear, and kept fixture
  usage confined to tests and release-proof cases. The same pass fixed a generic
  component-kind ownership bug where external storage/provider vocabulary could
  demote an accepted internal evidence-capture system to an adapter, and routed
  sequence-step capitalization through the shared greenfield text owner instead
  of a local helper. Proof passed the 52-term platform domain-leakage guard,
  py_compile for the touched modules, and 78 focused greenfield/matrix/component
  tests. A fresh 12-domain installed variance proof against the prior dist still
  passed 12/12 with hard 10/10 scores, zero issues, browser proof, max create
  time 28.819s, and clean temp cleanup; a rebuilt dist from this source
  checkpoint remains required before shipped-custody closure.
  Rebuilt-dist proof for checkpoint `9a764dc7` completed on 2026-06-30:
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-9a764dc7/greenfield-post-confirm-matrix-20260630-9a764dc7.v1.json`
  passed 13/13 maintained installed cases with hard 10/10 scores, zero issues,
  browser surface proof, complete governed records, 22.259-29.208s standard
  create timings, synthetic typed-probe rescue wiring in 33.474s, and clean
  temp cleanup.
  A follow-up source audit then found a subtler domain-custody risk that the
  sentinel scan alone cannot prove away: the generic status-view Registry
  profile injected `notification freshness marker`, `notification delivery
  markers`, and `notification delivery` even when the accepted intent did not
  own notifications. The source fix keeps status-view contracts generic by
  projecting source freshness, source event markers, and downstream action
  execution instead. Focused proof passed 39 component-spec tests, 3 explicit
  notification/intent regression tests, the 52-term platform leakage guard, and
  exact-string scan for the removed phrases. Fresh local release dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-3c616936`
  then passed the platform domain-leakage build gate across the same 52
  distinctive fixture terms.
  Proof-custody follow-up on 2026-06-30 found a release-evidence
  false-positive risk after the next fresh b013c835 dist/matrix pass: the
  installed matrix rebuilt `project_dashboard_preview` inside
  `collect_artifact_package`, so Project implementation prompt counts, prompt
  quality, and domain-term readback came from a regenerated builder payload
  rather than the persisted `odylith/tooling-payload.v1.js` that operators
  actually open. Browser proof also skipped the shell-owned Project tab, and
  the platform leakage proof stopped at pre-run declared terms rather than
  rescanning terms actually present in generated readback artifacts. The source
  fix keeps custody in persisted artifacts: matrix package collection reads
  `tooling-payload.v1.js`, persisted project-brief Markdown gets structural
  readback checks, browser proof opens `odylith/index.html?tab=project` and
  verifies accepted Project state plus five implementation prompt cards,
  static surface health checks Project payload prompt integrity, and each case
  rescans generated readback terms against protected platform source/dist
  custody. Focused proof passed 64 matrix/browser/leakage unit tests, 2 Project
  browser integration tests, py_compile, and one real installed flood-shelter
  post-confirm run with browser proof in 26.754s, hard 10/10 score, four
  generated leakage terms checked, zero leakage findings, and clean temp
  cleanup. Rebuilt full-dist maintained matrix proof remains required before
  release readiness can be claimed for this checkpoint.
  Rebuilt full-dist proof for committed checkpoint `aebe9245` completed on
  2026-06-30:
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-aebe9245/greenfield-post-confirm-matrix-20260630-aebe9245.v1.json`
  passed 13/13 maintained installed standard cases with hard 10/10 scores,
  zero quality issues, zero browser issues, complete governed records, per-case
  Project shell browser proof, persisted Project prompt payload readback,
  22.338-28.973s standard create timings with a 25.949s average, generated-term
  leakage proof across 55 generated readback terms with zero protected-custody
  findings, synthetic typed-probe auto-rescue in 33.617s, and clean temp
  cleanup. Natural non-internal host-model rescue quality remains a separate
  unclaimed proof class.
  Fresh non-reused variance against current checkpoint `25b8f9cf` then reopened
  release readiness on 2026-06-30. The ten-domain installed matrix completed
  with clean temp cleanup, but the result was failed for two distinct reasons:
  the post-run platform leakage proof treated required domain-coverage anchors
  as forbidden leakage sentinels and therefore falsely flagged platform-native
  words such as `artifact`, `protocol`, `sample`, `interpreter`, `verifier`,
  `consent`, `menu`, `court`, and `outage`; and the `satellite debris collision
  adjudication` case failed before governed writes in 33.445s because no-write
  Product Intent Confirmation recovery collapsed a noun-leading
  `product coordination for actor receiving/calculating/recording...` prompt
  into generic `Representative User reviews ...` prose, then the final gate
  correctly rejected `proposal.intent.customer` with `semantic slop:
  gerundized actor-role action leaked`. The failed mechanism is generic:
  release-proof leakage custody must be phrase-first and use declared
  distinctive sentinels rather than ordinary domain coverage anchors, while
  prompt-intent recovery must preserve product title, actor, and actor-led
  gerund action lists before generic first-path fallback. Do not fix this with
  domain allowlists, a broader single-token blacklist, rendered-prose repair,
  or a weakened semantic slop gate.
  Source fix in progress: `_case_generated_leakage_terms` now scans only the
  case's declared leakage sentinels, preserving fallback behavior only for
  legacy cases without declared sentinels; prompt recovery recognizes neutral
  `coordination` product containers and treats actor-led gerund action lists as
  usable first-path sources, preserving source punctuation while converting the
  action tail to base form. The broad regression pass exposed a separate generic
  title-selection risk where confirmed outcome states could be demoted behind
  first-input actions; workflow titles now prefer explicitly confirmed or
  approved outcomes without naming the domain object. Focused proof passed 60
  leakage/matrix unit tests, 66 recovery/post-confirm tests, the broader
  affected 266-test pack, and a disposable source-local satellite replay
  completed governed create in 24.522s with 4 Radar workstreams, 3 Registry
  specs, 6 Atlas sources, and clean debug-repo deletion. Rebuilt installed dist
  and fresh high-variance proof remain required before release readiness can be
  reclaimed.
  Rebuilt checkpoint `8495f96a` then proved the leakage-custody correction was
  incomplete rather than releasable. The fresh ten-domain installed matrix
  passed 7/10 with complete governed records, zero browser issues, and all
  standard creates under 29s, but failed the domain-expert lens for three
  cases. Two failures were corpus-authoring defects: the custom proof required
  unaccepted anchors (`trial`, `debris`) that the operator prompt never
  supplied, which would pressure the generator to hallucinate domain terms.
  The real platform defect was semantic custody for leading purpose context:
  `lead service-line abatement; intake...` preserved the action list but lost
  `abatement` from governed artifacts. A reviewer also caught that the
  phrase-only leakage correction could miss distinctive bare anchors such as
  `wafer` when a generated project uses the bare anchor and platform custody
  leaks it separately. The current source fix rejects ungrounded matrix
  `required_terms` before simulation, unions declared leakage sentinels with
  filtered distinctive required anchors, keeps generic anchors such as
  `artifact`, `protocol`, `sample`, `interpreter`, `model`, and `water` out of
  leakage custody noise, and carries semicolon-led purpose context into the
  first actionable path step without carrying unrelated sentence context. A
  follow-up read-only review found one more failed mechanism before release:
  the new grounding preflight rejected the shipped default matrix because a
  valid prompt used a plural source token while the required anchor was
  singular. The harness now accepts simple token inflection variants, the
  default case catalog itself is regression-tested against the grounding
  preflight, and the semicolon purpose-context owner was decomposed into its
  own first-path module after the broader suite caught the parser crossing the
  800-line anti-slop guard. Focused proof passed the install/leakage/recovery
  pack, the first-path file-size guard, py_compile, a 65-term platform
  source/dist leakage scan, and a disposable source-local municipal replay that
  preserved `lead`, `water`, `abatement`, and `sample` in generated governed
  records. Rebuilt installed dist and fresh corrected high-variance matrix
  proof remain required before release readiness can be reclaimed.
  Follow-up proof on 2026-06-30 found that the leakage correction needed one
  more custody split before release proof could be trusted. Required domain
  coverage anchors and forbidden platform leakage sentinels are now separate:
  selected cases scan declared leakage sentinels before simulation, generated
  readback adds only declared sentinels plus distinctive required anchors that
  are actually present and not already native to platform custody, and legacy
  custom cases without sentinels keep their fallback. A fresh custom variance
  against the previous `cdee30ee` dist then passed platform leakage proof
  across 45 generated readback terms but failed one case before governed
  writes because top-level product risk prose began with generic `Operator`.
  Source repair keeps the final gate strict and localizes actor-leading product
  risk rows through accepted actor semantics instead of weakening the gate or
  adding domain terms. The same broad source proof exposed a Registry contract
  profile custody bug: profile routing used too much surrounding context, so a
  notification/deadline component could inherit search/dashboard state from a
  sibling surface, while over-narrowing then starved true status-view contracts
  of accepted lifecycle transitions. The source fix routes profile selection
  from component-local context, stops treating `notification` alone as a
  status-view signal, and renders true status-view contracts from local
  component context plus accepted state/path/proof. Focused proof passed 68
  leakage, matrix, actor-risk, and component-boundary tests; the broader
  affected greenfield/component suite passed 325 tests in 409.12s. Rebuilt
  installed proof remains required before release readiness is reclaimed.
  Release-proof harness failed mechanism on 2026-06-30: the rebuilt
  `7cf9d2ed` local release dist passed the 65-term platform domain-leakage
  build gate, but the maintained installed matrix had to be killed after the
  first disposable case because generated-readback leakage filtering scanned
  protected source and runtime tarball custody once per required generated
  anchor while holding the runtime tarball open. That was not evidence of
  domain leakage in Odylith source; it was a proof-harness custody and latency
  defect. The forward fix computes platform-native required anchors once for
  the selected matrix vocabulary and reuses that baseline during per-case
  generated artifact readback, preserving fail-closed leakage checks without
  an unbounded per-term archive scan. Do not repeat the failed mechanism by
  adding broader term-by-term rescans, domain allowlists, or weaker leakage
  proof.
  Reviewer follow-up on 2026-06-30 found two additional leakage-proof blind
  spots before rebuilt release proof could be trusted. First,
  `scripts/release` was outside the source custody scan, so release tooling
  itself could carry project-domain vocabulary while proving other surfaces
  clean. Second, phrase detection was line-bounded and separator-dependent, so
  wrapped phrases and identifier-shaped leaks such as camelCase or compacted
  lowercase project phrases could pass. The forward fix moves intentional
  release fixture vocabulary into the excluded matrix fixture catalog, includes
  release scripts in protected custody, tokenizes documents across line
  boundaries with identifier case splitting, detects compacted multi-token
  phrases, and caches the tokenized source/dist corpus for repeated matrix
  scans. Focused leakage proof passed 71 tests, and cold/warm guard timing
  against the `7cf9d2ed` dist improved to 28.228s cold, 0.062s for a warm
  three-term query, and 0.809s for a warm 65-term query with zero findings.
  Reviewer follow-up on 2026-06-30 found that the resulting leakage proof was
  still too dependent on manually curated case sentinels and that the brutal
  matrix domain-coverage score still used substring matching. The failed
  mechanism was two-sided: partial `leakage_terms` declarations could suppress
  omitted case vocabulary, while a naive attempt to derive every source-text
  token from prompts and confirmed intents produced generic governance phrases
  such as `verification evidence`, `owner reviews`, and `question is` as false
  leakage sentinels. The forward fix keeps declared leakage terms as explicit
  proof vocabulary, supplements them with required anchors and conservative
  multi-token source-text phrases that contain distinctive project vocabulary,
  keeps generic confirmation and governance wording out of derived sentinels,
  and uses token-aware term matching for matrix domain coverage instead of raw
  substring containment. Focused proof passed 73 leakage/matrix tests, the full
  install suite passed 448 tests, and the strengthened source/dist leakage
  guard passed across 387 distinctive fixture terms against the `88df22be`
  dist. Do not repeat the failed mechanisms by relying on hand-curated
  sentinels alone, broad free-text token extraction, or substring scoring.
  Fresh variance on 2026-06-30 against committed dist
  `odylith-local-release-0.1.15-1ef33083` proved the source-text leakage
  extractor was still too broad before any temp repo was created. A ten-domain
  installed matrix was blocked at preflight because the derived case vocabulary
  treated platform/governance-native phrases such as `handoff evidence`,
  `manual override`, `operators request`, and `support team` as forbidden
  project-domain sentinels, then found those phrases in protected runtime and
  bundled guidance custody. The failed mechanism is not a consumer-project
  defect and must not be fixed by weakening the leakage gate, broad allowlists,
  or one-off regex phrase suppression. The next forward fix must make
  source-text sentinel derivation materially more selective: declared
  case-owned sentinels remain explicit proof vocabulary, but automatically
  derived prompt phrases must require richer domain-specific signal than one
  long token next to generic governance vocabulary. Rerun fresh non-reused
  installed variance after the fix, keep browser proof on, and delete every
  temp repo after evidence extraction.
  Independent score-harness review in the same pass found additional
  false-confidence risk before any new 10/10 claim can be trusted. The
  installed matrix can still compute a premium score when browser proof is not
  requested; several governed surfaces are counted for completion without
  persisted readback quality checks; `compass_records` can be inflated by
  rendered Compass shell assets instead of durable generated Compass records;
  and non-Atlas browser proof mostly verifies shell hydration rather than
  payload-to-render binding. The forward fix must make omitted browser proof a
  hard premium-score blocker, tighten Compass record counting to durable
  runtime/source records, and then incrementally promote release, program,
  Compass, Casebook, and rendered-shell payloads into first-class package
  evidence. Do not repeat the failed mechanism of counting surface existence as
  release-quality artifact proof.
  After the source-text overreach fix, the same fresh variance immediately
  exposed a real platform domain leak before repo creation: the research grant
  case's selected vocabulary found `conflict of interest` hardcoded in
  `greenfield_confirmed_system_completion.py` and
  `greenfield_confirmed_system_rows.py`, including the built wheel/runtime
  tarballs from `odylith-local-release-0.1.15-1ef33083`. This is not a false
  positive; it is historical example-domain wording in generic greenfield
  runtime defaults. The forward fix must replace that wording with generic
  policy/eligibility language in platform source, add a sentinel regression,
  rebuild the dist, and rerun fresh variance.
  Fresh non-reused variance after the domain-custody dist rebuild reopened the
  post-confirm gate on 2026-06-30. Nine of ten new installed projects passed
  with hard 10/10 scores, browser proof, complete governed records, and
  sub-60s creates, and the installed synthetic auto-rescue smoke passed in
  33.324s. `Performing arts safety rehearsal` failed before governed writes in
  36.865s with 76 `semantic slop: gerundized actor-role action leaked`
  blockers. A source-local replay showed the no-write Product Intent
  Confirmation itself was malformed: the prompt `... planner that lets a stage
  manager record ...` recovered the product container as the human actor and
  rendered `A performing arts safety rehearsal planner let a stage manager...`.
  The failed mechanism is generic relative-purpose recovery. Prompt/intent
  recovery handles `product for actor receiving...` and direct `where actor
  acts...` forms, but still misses `product that lets/enables/helps actor
  act...` forms. Do not fix this by weakening the gerundized actor-role gate,
  adding performing-arts vocabulary, or patching rendered strings. The forward
  fix must extract the embedded actor/action from helper relative clauses and
  project that semantic fact before post-confirm completion.
  Independent scoring review in the same pass confirmed that the quality
  scorer still permits false 10/10 claims for artifact families whose persisted
  readback is shallow. Release/program scoring is count-or-preview based,
  Compass quality accepts the presence of narrow runtime/source files without
  content evaluation, Casebook is not a scored artifact family, and shell
  payload proof for non-Project tabs mostly checks route/hydration structure.
  Treat those as release-blocking proof gaps: release/program, Compass,
  Casebook, and rendered shell payloads must become first-class persisted
  readback evidence before any honest premium 10/10 release claim.
  Forward fix on 2026-06-30 kept the platform gate strict and addressed the
  generic causes. Prompt-source recovery now recognizes helper-relative clauses
  such as `product that lets/enables/helps/allows <actor> <action>` and extracts
  the embedded human actor/action before no-write Product Intent Confirmation,
  so product containers do not become actor-role subjects. Project brief
  clipping now removes dangling terminal verbs such as `keep` when shortening
  long accepted sentences, preventing persisted brief/readback copy from ending
  in broken tails. The release matrix now collects persisted governed readback
  through a first-class owner: release catalogs/events, program wave records,
  Compass runtime/source records, and per-surface payload globals are parsed and
  scored before premium claims. Release/program freshness is linked to actual
  generated Radar workstream ids, program umbrellas count as coverage for their
  own workstream, preview-only source-launch output no longer satisfies
  operator evidence, and omitted browser proof fails only the browser-proof
  dimension instead of masquerading as copy/semantic slop. Source proof passed
  58 matrix tests, 84 install/leakage tests, 68 intent-recovery/Project tests,
  113 generated-prose/slop tests, py_compile, a 285-term source leakage guard,
  a disposable source-local performing-arts create in 15.770s, and a disposable
  municipal readback collector replay where all dimensions except intentionally
  omitted browser proof scored 10. Fresh rebuilt installed proof with browser
  proof remains required before release readiness can be reclaimed.
  Follow-up custody audit on 2026-06-30 found that the runtime/source leakage
  guard was green but platform-facing Registry CURRENT_SPEC history still named
  old simulation scenarios, and `atlas_box_explanations.py` carried one
  remote-signal category trigger from a specific technical domain. The forward
  fix is not to weaken evidence capture: fixture catalogs, Casebook evidence,
  and forensic snapshots may retain concrete repro vocabulary, but platform
  contracts and runtime heuristics must describe generic failure classes and
  semantic cues. The current fix rewrites Domain Intelligence, Dashboard, and
  Release CURRENT_SPEC proof notes into scenario-neutral language, removes the
  technical-domain trigger from Atlas box explanations, and reruns the
  285-term platform leakage guard plus a stricter platform-surface scan with
  zero retained-scenario matches outside intentional fixtures/evidence.
  Hygiene follow-up in the same slice found that `atlas_box_explanations.py`
  was already above the source-size pressure line and that tracked-object
  phrase fallback could select generic control verbs such as `stays` as the
  visible object. The fix moves tracked-object phrase selection into
  `atlas_box_terms.py`, keeps the Atlas explanation owner under the threshold,
  and pins the generic fallback behavior with focused tests. Do not repeat the
  failed mechanism by adding more local vocabulary to the explanation renderer
  or by letting generic control prose stand in for a domain object.
  Precommit installed-package proof on 2026-06-30 rebuilt
  `odylith-local-release-0.1.15-1ef33083-precommit` from the current working
  tree and passed the 285-term platform domain-leakage guard at build time and
  matrix time. The maintained installed matrix passed 13/13 high-variance
  standard cases with hard 10/10 release-quality scores, zero issues, every
  browser surface proof attempted and passed, generated terms absent from
  platform source/dist, complete governed records, five Project implementation
  prompts per project with zero prompt findings, max standard create time
  28.697s, and average standard create time 25.779s. Synthetic typed-probe
  rescue wiring passed in 33.237s under the 90s rescue tier. The temp project
  cleanup scan was empty after the run. This is a precommit checkpoint only:
  do not cite it as final release proof until the code is committed, pushed,
  rebuilt from the committed head, and the installed matrix passes again.
  Committed-head proof on 2026-06-30 rebuilt
  `odylith-local-release-0.1.15-78787588` after commit `78787588` and passed
  the platform leakage guard over source plus dist. The installed matrix then
  passed 13/13 high-variance standard creates from the fresh dist with zero
  quality issues, zero platform-leakage issues, zero browser-surface issues,
  minimum/average/maximum create times of 22.690s/26.156s/29.050s, and 10/10
  brutal scores for completion, governance depth, implementation prompts,
  browser proof, copy clarity, latency, operator usefulness, and all expert
  lenses. The matrix used generated artifact terms as the leakage corpus and
  confirmed those terms did not leak back into platform source or dist. The
  synthetic typed-probe rescue smoke passed in 33.888s, but its manifest still
  records `natural_rescue_quality_proven=false`; do not use that smoke as proof
  of natural host-model rescue quality.
  Follow-up proof-hardening on 2026-06-30 found two release-evidence gaps that
  could let future claims depend on chat-side evidence instead of durable
  artifacts: fresh high-variance cases required Python-level harness calls, and
  temp cleanup was enforced but not persisted in the matrix JSON. The harness now
  accepts explicit external case files, writes per-case post-confirm manifest
  summaries, derives natural-rescue proof only from non-probe provider-backed
  structured patch evidence, and records temp-cleanup proof as a matrix status
  gate. A three-case external variance run against the latest local dist passed
  with 10/10 scores, zero quality/browser/platform-leakage findings, 24.952s
  minimum, 25.405s average, 25.970s maximum standard create time, passed cleanup
  proof, and synthetic rescue smoke at 33.491s. Natural host-rescue quality
  remains unproven.
  Fresh committed-head proof after the proof-hardening checkpoint rebuilt
  `odylith-local-release-0.1.15-4750c7ec` from pushed commit `4750c7ec` and
  passed the source-plus-dist platform leakage guard. The maintained installed
  matrix then passed 13/13 high-variance standard post-confirm creates with
  persisted JSON proof, 10/10 scores, zero quality issues, zero browser-surface
  issues, zero platform-leakage issues, 22.622s minimum, 26.394s average,
  28.799s maximum create time, browser proof passed for all 13 cases,
  persisted temp-cleanup proof passed with no remaining temp paths, and the
  synthetic typed-probe rescue smoke passed in 34.340s. The manifest summaries
  were present for all 13 standard cases and recorded no standard-path rescue
  activation. Natural host-model rescue remains explicitly unproven and must
  not be inferred from the synthetic typed-probe smoke.
  Natural rescue proof-gap follow-up on 2026-06-30 found a custody defect in
  the final manifest evidence path. A provider-backed repair pass could enrich
  a typed PatchSet with a structured Tribunal plan, then rerun completion and
  produce a clean final package; the clean final manifest rebuilt evidence from
  the final report and discarded the provider-backed repair request. That meant
  release proof could not distinguish real host-planned semantic repair from
  deterministic rescue wiring. The forward fix preserves the last nonempty
  repair PatchSet request as `last_repair_patchset_request`, lets release
  scoring read provider-backed repair evidence from that field after a clean
  final pass, and adds a separate maintained natural structured-rescue proof
  leg that requires an explicit provider, a non-probe repaired issue, a planned
  Tribunal patch summary, clean governed writes, and the 90-second rescue
  budget. Focused runtime, release-proof-scope, natural-rescue matrix, wrapper,
  and structured-rescue tests passed; installed committed-head proof remains
  pending for this checkpoint.
  Installed natural-rescue proof then failed on dist
  `odylith-local-release-0.1.15-e4b31938`: all thirteen standard cases passed
  at hard 10/10 in 24.780-32.306s and synthetic rescue wiring passed in
  37.364s, but the real host-planned structured-rescue leg failed before
  governed writes in 47.228s. Direct planner instrumentation showed the
  root cause: the structured PatchSet planner inherited global high-effort
  Codex reasoning and capped its call at 25.0s, causing a provider timeout
  before replacement facts were returned. The semantic executor correctly
  refused to apply an empty external-boundary fact, so the proof blocker
  remained. The forward fix makes this narrow schema-constrained PatchSet
  planner use a rescue-calibrated default effort and a larger bounded share of
  the 90-second rescue budget while still honoring explicit operator effort
  env overrides. A retained source-local repro then passed in 55.085s with
  `structured_rescue_semantic_patch` recorded in `repaired_issue_codes`, a
  provider-backed `last_repair_patchset_request`, and committed governed
  records. Fresh committed-head dist proof was then completed from commit
  `dd718448`: the installed matrix passed 13/13 standard cases under 33s with
  hard 10/10 quality scores and the real installed natural structured-rescue
  leg passed in 67.435s under the 90s rescue tier with a provider-planned
  semantic patch, committed governed records, and zero final findings.
  Regression follow-up on 2026-06-30 against fresh current-head dist
  `odylith-local-release-0.1.15-261f00dc` passed all thirteen standard
  high-variance greenfield cases at hard 10/10 in 24.713-33.345s with
  browser proof, domain-leakage proof, complete governed records, prompt
  quality proof, and temp-cleanup proof, but the real installed natural
  structured-rescue leg failed in 49.691s before governed writes. The blocker
  was not Codex provider availability: a live direct Codex structured-planner
  probe returned a valid `semantic_external_systems` plan in 12.692s. The root
  cause was a custody edge in semantic patch execution: when the host-planned
  replacement fact matched the already-present canonical semantic value, the
  executor treated the patch as a no-op and did not write the
  `semantic_patch_ledger` entry required by `structured_rescue_semantic_patch`.
  Source now records host-authored semantic adjudication ledgers for
  idempotent typed semantic facts when the replacement fact, decision ledger,
  and confidence are present. Focused semantic executor, structured-rescue,
  patch-payload, natural-rescue proof-scope, and no-rendered-repair contract
  tests passed; rebuilt installed proof remains pending for this checkpoint.
  Rebuilt installed proof against committed dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-de17cdda`
  falsified release readiness. The natural installed structured-rescue leg now
  passes in 62.823s with `structured_rescue_semantic_patch`, committed governed
  records, complete Radar/Registry/Atlas/project brief/prompt/traceability
  evidence, and clean findings, so the previous idempotent semantic-ledger
  failure is fixed in the package. The maintained standard matrix still failed
  4/13 cases and scored 6.923/10 overall because `flood shelter intake` and
  `apprenticeship credential readiness` stopped on `accepted-project memory
  preview leaked adjacent duplicate word prose`, while `semiconductor lab
  custody` and `package supply chain exception desk` stopped on `project
  dashboard preview leaked adjacent duplicate word prose`. Each failed case
  activated rescue, emitted a repairable `generated_copy_quality` `plan_patch`
  request owned by `artifact_plan_projector`, but had zero Tribunal plan
  operations, zero repaired issue codes, failed validation, and wrote no
  governed records. The failed create times were 20.508s, 21.842s, 22.004s,
  and 22.759s; the nine passing standard cases remained 10/10 with complete
  records and max passing create time 30.270s. Platform domain leakage passed
  across 178 terms, temp cleanup passed with no remaining roots, browser proof
  passed only for the nine committed cases and was skipped for the four failed
  creates. The mechanism-level learning is that removing rendered-copy mutation
  was architecturally correct, but the replacement `ArtifactPlanIR` repair path
  is not implemented deeply enough: a typed `plan_patch` envelope without a
  real projection-fact patch or host-planned structured artifact-plan repair is
  equivalent to giving up before the governed write. Do not reintroduce
  artifact-draft string cleanup; fix the artifact-plan repair substrate or
  projection facts so generated-copy quality failures can be repaired before
  final commit.
  Source follow-up on 2026-06-30 replaced the fake repairable envelope with a
  source-owned projection repair target resolver. Preview findings such as
  `prewrite_package.accepted_project_preview.proposal.diagrams[0].mermaid_source`
  now map to the sanctioned `diagrams[0].mermaid_source` ArtifactPlanIR fact,
  while Project dashboard release-card copy findings map to card-specific
  source facts instead of a rendered dashboard body.
  The Tribunal patch planner now materializes artifact-plan text/list envelopes
  as `{path, value}` source patches and preserves multiline source text; rescue
  evidence includes the current target value. Scoped projection rerender now
  refreshes `project_dashboard` from source previews, and Mermaid source leaves
  inside preview packages are typed as `mermaid_source` so generated-copy gates
  inspect visible labels instead of graph syntax. The four prior source-local
  failure shapes now pass with committed writes: flood shelter intake in
  19.406s, semiconductor lab custody in 20.957s, package supply chain exception
  desk in 21.309s, and apprenticeship credential readiness in 22.103s. Focused
  runtime proof passed 79 tests in 6.89s and the widened post-confirm/install
  proof slice passed 100 tests in 40.83s. At that source checkpoint, release
  readiness remained capped until
  a rebuilt installed dist passes the full 13-case matrix, browser proof,
  domain-leakage proof, temp cleanup, synthetic rescue, and natural structured
  rescue.
  Additional source follow-up on 2026-06-30 found a hidden quality miss after
  green validators passed: a wearable-health prompt completed governed writes
  but produced semantically awkward artifacts, including a false `Separate
  Urgent` actor, malformed first-path clauses, and a Radar title shaped like
  `Keep ... Clear ... Clear ...`. The failed mechanism was generic: the
  provider-free fallback grammar did not recognize ordinary coordinated action
  verbs such as `separate` and `give`, so sibling action clauses could be
  promoted into actor prefixes, and the state-boundary title owner added the
  clarity adjective even when the state label already carried it. The source
  fix adds those verbs to shared domain-neutral prose grammar, keeps actor carry
  across coordinated action clauses, routes Project dashboard release-card
  findings to card-specific SemanticModelIR or ArtifactPlanIR facts, gives
  accepted-project scoped rerender a fresh source-launch context, and prevents
  repeated clarity adjectives in Radar state-boundary titles. Proof after the
  fix: focused recovery/backlog tests passed 48 tests in 89.26s; the combined
  recovery/projection pack passed 130 tests in 98.20s; the post-confirm/install
  proof slice passed 100 tests in 42.16s; source platform leakage passed across
  285 distinctive terms; and six non-reused source-local simulations completed
  in 19.455-21.543s with zero final issues, Atlas render passing, Registry
  validation passing, no escaped bad strings, and temp repos deleted after each
  run. Release readiness still requires a rebuilt installed dist matrix with
  browser proof and hardened artifact readback.
  Rebuilt installed proof against committed dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-2a389428`
  passed after cleaning the failed first run root. The maintained matrix
  persisted
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-2a389428/greenfield-post-confirm-matrix.v1.json`:
  13/13 standard installed cases passed with hard 10/10 scores, zero quality
  issues, zero browser-surface issues, zero platform-leakage findings across
  213 generated readback terms, complete governed records, 13/13 per-case
  browser proof, temp-cleanup proof passed with no remaining paths, max
  standard create time 30.468s, and average standard create time 27.801s. The
  synthetic typed-probe rescue smoke passed in 37.493s, and the real installed
  structured-rescue leg passed in 62.894s with natural rescue quality proven
  under the 90s rescue tier. Failed-mechanism note: the first full matrix
  attempt against the same dist exited with `Bus error: 10` from the Python
  harness and left `/Users/freedom/mock/odylith-greenfield-matrix-a60029b7`.
  macOS crash diagnostics reported `Object has no pager because the backing
  vnode was force unmounted`. One-case and three-case browser probes then
  passed generated artifact proof, and the final full retry passed after temp
  cleanup. Treat this as release-harness/runtime fragility to harden with
  incremental proof persistence and stronger subprocess isolation; do not
  mistake the bus error for a generated-artifact semantic failure.
  Latest committed-dist proof from 925545d8 passed the maintained installed
  release matrix from `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-925545d8`
  with persisted proof at `/tmp/greenfield-post-confirm-matrix-925545d8.v1.json`:
  13/13 standard cases passed at hard 10/10, zero quality issues, zero browser
  issues, zero prompt findings, platform-domain leakage proof passed, complete
  governed records were read back, per-case browser proof passed, temp cleanup
  reported no remaining simulation roots, max standard create time was
  29.643s, synthetic rescue passed in 35.531s, and real installed structured
  rescue passed in 62.307s with natural rescue quality proven under the 90s
  rescue tier.
  Release-provenance proof gap on 2026-07-01: independent closure review found
  that the committed-head local dist `odylith-local-release-0.1.15-3bd4d233`
  passed behavioral greenfield proof but its `build-provenance.v1.json` left
  `workflow.sha` empty. That weakens release-readiness custody because the
  local installable package was not self-describing enough to prove which
  source commit produced it. The failed mechanism is treating local release
  smoke plus matrix pass as sufficient without checking provenance commit
  binding. Forward fix: local release provenance now records the local git
  `HEAD` and source-tree posture; a fresh dist from the post-fix commit must
  be rebuilt and rerun before final install commands are handed off.
  Repeated forensics mechanism on 2026-07-01: running the pinned dogfood
  `sync-component-spec-requirements` command after the provenance governance
  update regenerated component forensics with old raw event projection and
  reintroduced protected historical scenario terms into Registry custody.
  The source-local command
  `odylith governance sync-component-spec-requirements --repo-root .`
  regenerated the same sidecars through the current neutralized forensics
  projector; the 285-term platform leakage guard then passed and the leaked
  terms disappeared from `odylith/registry/source/components`. Guardrail: in
  product-repo source-change slices, use source-local regeneration for
  forensics/leakage/governance-learning sidecars until the source fix is
  shipped, then prove the shipped pinned runtime separately through installed
  release artifacts.
  Repeated forensics mechanism on 2026-07-02: a fresh `local-release-assets`
  build from committed head failed the 285-term platform leakage gate because
  committed Registry `FORENSICS.v1.json` sidecars again retained old scenario
  vocabulary in generic platform custody. Source-local `--check-only` correctly
  reported stale sidecars, but the first source-local sync pass also exposed a
  convergence bug: updating a component `CURRENT_SPEC.md` could change the
  workspace-derived forensics snapshot, leaving affected sidecars stale until a
  second invocation. Forward fix: release packaging and installed matrix
  wrappers now require a source-local `sync-component-spec-requirements
  --check-only` preflight before leakage proof, and the sync command reruns the
  forensics projection from a refreshed Registry report after any component spec
  write so one invocation leaves check-only clean.
  Fresh installed proof against
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e4441a43`
  reopened the matrix on 2026-07-02 after the exact grn-sim source-local
  replay passed. Thirteen of fourteen installed standard cases completed at
  hard 10/10, but `sparse disclosure confirmation` failed before governed
  writes in 12.504s because `GreenfieldSemanticCompiler` selected the proof
  boundary as `semantic_model.first_path_contract.visible_result` when the
  accepted first path ended with a terse terminal event:
  `council publishes proof`. The failed mechanism was generic source-priority
  custody, not disclosure vocabulary: one-word terminal result objects such as
  `proof` were rejected, the apply-semantic bridge appended the synthetic
  `accepted result for review` fallback even when a real terminal event existed,
  and the compiler ranked a long proof-boundary candidate above valid
  first-path event candidates by a 0.01 confidence margin. The source repair
  nominalizes terse terminal event objects into action-state results such as
  `published proof`, ranks first-path event candidates ahead of proof-boundary
  candidates, lets the apply-semantic bridge trust explicit
  `first_path.events.N` results without fallback poisoning, keeps lower-case
  subject/action first-path splits such as `compliance records review evidence`
  intact, preserves subjectless generated choice tails, keeps curated Project
  Brief readiness summaries from losing middle and terminal actions, and
  derives missing actors from partial accepted actor lists while rejecting
  prefixed duplicate actor labels. Focused proof passed
  `tests/unit/runtime/test_greenfield_semantic_compiler.py`,
  `tests/unit/runtime/test_greenfield_semantic_model_quality.py`,
  `tests/unit/runtime/test_greenfield_preconfirm_engine.py`, the full
  `test_greenfield_preconfirm_slop_regressions.py` file, and syntax proof
  for the touched source. Source-local replay of the sparse confirmed intent
  then completed in 24.268s with a passed manifest, zero issues, 4 Radar
  records, 3 Registry specs, 6 Atlas diagrams, no `result result`, preserved
  `published proof`, no `accepted result for review` fallback, and temp cleanup.
  High-volume variance learning on 2026-07-02: the maintained matrix passed
  14/14 standard cases on the working forensics-preflight dist, but the first
  external 30-case no-browser sweep exposed 12 real post-confirm create
  failures across climate data assimilation, battery electrolyte degradation,
  and plasma confinement shot planning. All failures shared the same generic
  signature: accepted first-path text entered the semantic compiler with
  adjacent duplicate copy such as `review review`, which then escaped into
  governed surfaces and was correctly rejected before writes. The failed
  mechanism was semantic ingress custody, not Atlas, Registry, or scientific
  domain vocabulary. The fix moves adjacent duplicate-word cleanup into shared
  confirmed-text and first-path ingress owners so renderers do not carry the
  burden. Representative source-local replays for all three failed project
  classes then committed governed records with passed manifests, zero issues,
  and no repeated review copy.
  Follow-up quality learning on 2026-07-02: broader runtime tests found that
  actor completion and specialized component contracts still had semantic
  overreach after the ingress repair. Actor completion mined rich accepted
  actor lists for extra role nouns, hyphenated human labels were rendered as
  awkward display names, document-context proof obligations could remain
  hyphenated in component specs, and specialized status/document profiles could
  bury access proof rows or truncate important transition states. The generic
  repair keeps rich operator actor lists authoritative, derives missing actors
  only from first-path evidence when the accepted list is absent or thin,
  naturalizes display labels at render boundaries, selects proof rows by proof
  category instead of blind order, and merges semantic/profile transition
  fragments before lifecycle summarization. Runtime proof passed 179 greenfield
  quality tests, while the install/matrix/leakage/preflight slice passed 106
  tests. Release readiness still requires a fresh dist and hundreds-scale
  seeded installed sweep from the current code.
  Harness learning on 2026-07-02: deleting temp repos after every simulation
  left the platform without enough durable artifact evidence for brutal QA at
  scale. The matrix harness now records per-case retained evidence before
  cleanup: case metadata, prompt and confirmed-intent hashes, artifact
  inventory, artifact hashes and excerpts, required-term grounding from full
  readback text, browser-proof state, quality findings, and manifest summary.
  It also supports seeded install mode, installing Odylith once per batch and
  cloning mutable consumer repo state for each case while symlinking the
  immutable runtime. This preserves cleanup discipline without losing
  auditability and makes 100s of project simulations operationally realistic.
  Proof-scoring failed mechanism on 2026-07-02: the first two seeded
  high-volume discovery batches correctly skipped browser proof and recorded
  that skip at the top level, but each per-case quality block still awarded
  `browser_surface_proof: 10` and printed `all brutal release-quality
  dimensions scored 10`. That made discovery evidence look like complete
  release-quality browser proof. The source harness now marks unrequested
  browser proof as an unscored dimension with
  `score_basis=volume_discovery_without_browser_surface_proof`, preserves pass
  status for fast volume discovery, and reserves the full brutal release claim
  for runs where browser proof is actually requested and attempted.
  High-volume homonym/title learning on 2026-07-02: seeded batch three exposed
  six real quality failures after governed create completed for weather radar
  calibration and geologic atlas field mapping cases. The generator preserved
  lower-level first-path phrases such as `radar scan`, `beam blockage
  evidence`, `map sheet`, and `stratigraphy evidence`, but collapsed the
  project frame to generic outcome labels such as `Calibration Decision
  Workspace` and `Mapping Release Workspace`, leaving required domain
  qualifiers present only in accepted-project runtime state. The source fix
  preserves command-led prompt targets before sentence boundaries as the
  canonical project frame, keeps source-grounded control-plane homonyms valid
  only in matching local domain context, rejects object-list fragments such as
  `Drought Restrictions Expert` and `Windows Operator` as supplemental actors,
  and restores readable title splitting for source shorthand such as
  `adverse-event` and `follow-up`. The evidence harness now separates required
  term grounding across all retained artifacts from scored generated-surface
  grounding, and reports when a required term appears only outside scored
  governed artifacts. Focused proof passed six homonym/title/evidence tests,
  five prior recovery regressions, four install evidence/scoring tests, syntax
  proof for the touched source, and the full confirmed-intent recovery suite
  passed 48 tests in 151.01 seconds.
  High-volume homonym stress learning on 2026-07-02: seeded batch four passed
  27 of 30 platform-homonym cases, including product-domain uses of registry,
  compass, casebook, tribunal, source, proof, pipeline, and agent language, but
  the three `software release waiver board` cases failed before governed writes
  in 25.505-26.599s. The final blocker was
  `confirmed Atlas flowchart First Path Sequence omits the tail of the accepted
  first path`. Source-local replay confirmed the flowchart correctly rendered
  the terminal event as `Publish go decision`; the false failure came from the
  tail-preservation gate reducing the accepted tail to `{manager, publish}`
  after `decision` was treated as generic, while the renderer intentionally
  stripped the actor subject and exposed only `publish` in the terminal node.
  This is a generic checker/semantic-shape mismatch, not a software-release
  domain exception and not a reason to weaken Atlas tail preservation. The
  repair must compare the same subject-stripped terminal action/object shape
  that the renderer owns, while still rejecting diagrams that drop the terminal
  action or visible result entirely.
  High-variance actor-source learning on 2026-07-04: the new 60-case
  taxonomy regression stopped after 25 clean cases on `robotics warehouse
  near-miss lab v1`. The exact failed prompt named a concrete actor, `safety
  engineers`, and also contained object-list material, `baseline routes, and
  operator notes before releasing a safety result`. Confirmed-intent recovery
  promoted that object-list tail into extra human actor rows, including
  `Operator Notes`, and final post-confirm quality correctly failed before
  governed writes with
  `greenfield.public.product.content.uses.generic.actor.label.instead.project`.
  This is not a robotics or warehouse defect. The failed mechanism is
  candidate-clause recovery accepting object-list fragments after a concrete
  actor has already been recovered. The banned fixes remain explicit: do not
  weaken the generic actor-label gate, do not add project-domain exceptions,
  and do not patch rendered Radar, Registry, Atlas, or project-brief strings.
  The source fix must keep actor extraction semantic: once a clause yields a
  concrete actor, later comma/and fragments need their own human actor signal
  before they can become additional actors.
  Failed mechanism learning on 2026-07-04: reviewer audit caught that the
  first repair pass overcorrected. A broad material-action fallback could let
  action-only first paths pass completeness without a distinct visible
  outcome; bounded workflow-phrase actor recovery could promote non-human
  result/workflow nouns before `turns ... into ...`; actor-row shortening
  could drop legitimate single-action object-list detail from Problem and
  Product View; and visible-result grounding could strip meaningful completion
  state verbs from valid result phrases. These failures are generic semantic
  custody failures, not project-domain defects. The next repair must preserve
  typed source facts without weakening validation: require a visible result
  or dense actor/action/object path shape, reject non-human workflow/result
  subjects as actors, summarize actor rows by parsed path shape rather than
  raw comma splitting, and strip action-state morphology only when it is
  ungrounded/generated rather than accepted product language.
  Fresh installed release-matrix proof on 2026-07-05 against working-tree dist
  `odylith-local-release-0.1.15-guidance-smoke2-20260705T0458` reopened this
  bug before any release-ready claim. The run passed 12 of 14 standard
  installed cases at hard 10/10 with complete Radar, Registry, Atlas, trace,
  prompt, and expert-lens evidence, and both rescue smoke cases passed in
  53.674s and 66.516s. Two standard cases still failed before governed writes:
  `package supply chain exception desk` failed in 29.098s because inline actor
  casing drift reached `proposal.backlog.0.domain_intelligence.summary` and
  `proposal.backlog.0.domain_intelligence.intent.0` before a quality manifest
  existed; `sparse disclosure confirmation` failed in 26.004s because the
  domain-expert quality lens found missing high-risk accepted-assumption
  coverage. The sparse case is especially important: the manifest classified
  the finding as repairable `quality_lens_gap` owned by
  `artifact_plan_projector`, but the generated patchset request carried empty
  `replacement_fact`, `decision_ledger_entry`, and
  `proof_obligation_delta`, so rescue activation reran without an executable
  artifact-plan repair and rolled back the write transaction. The failed
  mechanisms are generic and must not be fixed with project vocabulary,
  regex allowlists, weakened gates, or rendered-prose patching. Next repair
  must move inline actor casing custody and high-risk assumption coverage into
  typed semantic/artifact-plan facts, and the rescue planner must either emit
  an executable structured patch with source-grounded replacement facts or
  fail early with a precise non-repairable blocker instead of burning passes.
  Source-local repair learning on 2026-07-05: `package supply chain exception
  desk` was fixed by moving inline actor event rendering through the existing
  backlog text-model actor-subject contract, preserving protected tokens while
  lowering ordinary role words before domain-intelligence prose is rendered.
  `sparse disclosure confirmation` exposed two separate generic failures:
  the artifact-plan rescue planner had no source-anchored fallback for
  `ArtifactPlanIR.assumptions`, and the domain-expert quality lens could mark
  a one-term accepted assumption such as `The first release records evidence
  only.` as high-risk while requiring two rendered terms, an impossible gate.
  The repair adds an executable assumptions PatchSet fact derived from accepted
  assumptions and the accepted proof boundary, keeps rescue patch execution
  fail-closed when no concrete fact exists, and corrects the lens math so
  short assumptions must cover all available meaningful terms rather than an
  impossible minimum. Source-local replay passed both failed cases after the
  fix: `package supply chain exception desk` completed in 35.554s, `sparse
  disclosure confirmation` completed in 26.947s, both wrote governed records
  with passed manifests, and the scanned bad-copy sentinels were clean.
  Follow-up source-local proof on 2026-07-05 reran the exact saved grn-sim
  gene-expression simulation confirmed intent in a disposable repo from the
  current source tree. The replay completed in 29.828s with return code 0,
  wrote governed records, produced five Radar markdown records, five Registry
  specs, six Atlas Mermaid diagrams, and one Casebook record, and the scanned
  duplicate-copy sentinels for result result, output output, proof proof, to
  flags, package Manager, and Launches launches were all clean. The same pass
  also corrected the assumptions rescue ledger so ArtifactPlanIR.assumptions
  repair explains accepted-assumption and proof-boundary custody instead of
  incorrectly describing a Registry component-contract repair.

- Related Incidents/Bugs: CB-208

- Code References: - src/odylith/runtime/domain_intelligence
- src/odylith/runtime/domain_intelligence/artifact_tribunal_actors.py
- src/odylith/runtime/reasoning/tribunal_lens.py
- src/odylith/runtime/artifact_quality/greenfield_quality_lenses.py
- src/odylith/runtime/common/mermaid_text.py
- scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_rescue_smoke.py
- src/odylith/runtime/project_intelligence/source_launch.py
- src/odylith/runtime/domain_intelligence/greenfield_experience.py
- src/odylith/runtime/domain_intelligence/greenfield_canonical_projection_facts.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_project_brief.py
- src/odylith/runtime/artifact_quality/greenfield_package_quality.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_actor_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_actor_path_role.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_non_goals.py
- src/odylith/runtime/domain_intelligence/greenfield_generated_prose_shape.py
- src/odylith/runtime/governance/sync_component_spec_requirements.py
- src/odylith/runtime/governance/component_registry_intelligence.py
- scripts/release/publish_release_assets.py
- tests/unit/runtime/test_greenfield_confirmed_surfaces.py
- tests/unit/runtime/test_greenfield_project_brief_rendering.py
- tests/integration/runtime/test_greenfield_hiit_preconfirm_quality.py
