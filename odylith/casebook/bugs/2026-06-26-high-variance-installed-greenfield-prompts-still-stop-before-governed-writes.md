- Bug ID: CB-209

- Status: Open

- Created: 2026-06-26

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: High-variance installed greenfield prompts still stop before governed writes

- Impact: Harder real-world greenfield prompts can pass proposal generation but fail post-confirm create before Radar, Registry, Atlas, release, traceability, and quality-manifest records are committed, leaving only partial runtime/source artifacts.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 local release dists installed into fresh consumer repos under /Users/freedom/mock, including /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-17e8a6f6, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-cedafc79, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-b0713a0a, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-33bdb122, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-265cc0cf, and /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-3d13f434

- Detected By: Custom high-variance installed greenfield matrix after release smoke and standard installed matrix passed

- Failure Signature: autonomous warehouse safety state and federated agent incident command returned create_returncode=2 in the earlier installed matrix; post-confirm quality manifest missing; Radar workstreams 1, Registry specs 0, Atlas sources 0, release records 0, trace nodes 0. A later installed matrix on cedafc79 fixed those two cases but exposed two additional platform failures: indigenous data sovereignty review returned create_returncode=2 before governed writes, and spacecraft anomaly triage committed records but failed rendered package quality because multiple Radar titles ended with a clipped article phrase `a`. The 33bdb122 installed matrix then reopened this bug: pediatric agency practice and security disclosure council returned create_returncode=2 before governed writes, with no quality manifest, one Radar workstream, zero Registry specs, zero Atlas sources, zero release/program records, zero trace nodes, and zero Project implementation prompts. The 3d13f434 installed matrix reopened the release gate again: 12 of 13 cases passed with hard 10/10 scores, browser proof, and complete records, but sparse disclosure confirmation scored 0/10 after governed writes because it produced only two Registry component specs, carried only three of four required domain anchors, and failed architect, engineer, and domain-expert matrix lenses.

- Trigger Path: scripts/release/greenfield_post_confirm_matrix.py custom cases using greenfield propose followed by greenfield create --confirm --release 0.0.1 --json

- Ownership: Domain Intelligence greenfield post-confirm semantic compiler and final quality gate

- Timeline: 2026-06-26: standard installed five-domain matrix passed at 17.404-18.353s with zero quality issues; custom high-variance installed matrix then failed autonomous warehouse safety state at 17.855s and federated agent incident command at 10.728s before governed writes. After semantic-custody and typed Tribunal-lens fixes, the cedafc79 standard installed matrix passed five cases at 17.074-18.574s with zero issues and all expert lenses passing. A harder cedafc79 custom installed matrix then passed autonomous warehouse safety state, federated agent incident command, deepfake provenance escrow, and fusion plasma shot readiness at 16.851-17.347s, but indigenous data sovereignty review failed before governed writes in 8.999s and spacecraft anomaly triage failed the package/domain-expert gate after writing records in 18.454s due clipped Radar article phrases. After the second semantic-custody fix, the b0713a0a dist passed release smoke, the standard installed matrix, and the harder six-case installed matrix with every create under 19s and every PM, architect, engineer, and domain-expert lens passing. On 2026-06-27 the 33bdb122 installed matrix failed two of five cases after Project dashboard prompt custody was added: flood shelter intake, semiconductor lab custody, and port berth carbon tariff passed with hard 10/10 scores in 19.878-22.416s, but pediatric agency practice failed in 14.282s and security disclosure council failed in 10.708s before governed records were committed. The 265cc0cf installed matrix then passed all five standard create cases with 10/10 brutal matrix scores in 26.626-31.091s, but release proof still failed because the packaged CLI rescue-smoke leg stayed on the standard tier, did not mark rescue activation, kept a 60s budget, and did not record `post_confirm_rescue_probe` as repaired.

- Blast Radius: Any consumer greenfield prompt with overloaded safety/state/agent/model/release language that deterministic completion cannot safely normalize before final writes

- SLO/SLA Impact: Reopened by 33bdb122. Passing cases stayed under the 60s standard budget, but failing cases did not commit governed records at any latency, so release readiness is blocked until a rebuilt dist passes the installed matrix.

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

- Solution: Fix Odylith generally in semantic/projection ownership rather than domain-specific terms or rendered-string repair. Confirmed-intent recovery now localizes role-only actors to the project, keeps object modifiers out of actor labels, treats state-review predicates as review targets, rejects passive object-state subjects as human actors, and uses article-safe actor references. Outcome-action projection now converts system-generated results into modal-safe `review` or `see` actions before `user can` prose is composed. The role-can normalizer now preserves interrogative/modal clauses such as `what can be released`. First-path visible-result extraction now respects token boundaries inside hyphenated noun compounds, and semantic proof-control detection no longer rejects first-path `release readiness for ...` noun results while still rejecting control claims such as `release readiness requires ...`. Artifact-plan PatchSet row repair now refuses untargeted row mutations. A shared Tribunal lens contract now lets PM, architect, engineer, and domain-expert checks emit source-map target paths, semantic-node IDs, projection IDs, repairability, and repair owner at judgment time instead of reconstructing repair custody from check-name prose. The structured reasoning adapter now supplies an explicit live-proven Codex model for general structured repair when config is blank, maps the legacy Spark alias to the live CLI model, avoids the unsupported Codex ladder rung, and keeps user-config bypass reproducible. Tribunal patch planning now uses strict structured-output schemas for decision ledger, proof deltas, and replacement facts, then materializes the typed fact envelope back into caller-owned semantic or artifact-plan replacements after custody validation.
  Current Source Fix: Source-launch prompt composition now emits embedded prompt facts as fragments instead of sentences, strips dangling subordinate tails, uses generic material-term containment plus semantic overlap scoring to suppress outcomes that merely restate the action object, and routes proof fallback through the same cleaned first-path projection instead of copying raw confirmed text. Operator next-step preview trimming now detects incomplete subordinate tails near the end of clipped fragments, removing tails like `when required information` while preserving complete clauses such as `when required information is missing`. Release proof now runs installed rescue smoke by default from the canonical matrix wrapper. The smoke uses the packaged CLI in `--repair-tier auto`, injects one maintainer-only typed post-confirm finding through an exact internal release-proof token, requires the engine to auto-escalate to rescue, applies a typed semantic PatchSet marker, writes governed records, and fails unless the final manifest records `post_confirm_rescue_probe` as repaired under the 90s budget. The matrix harness now keeps normal standard cases on a clean environment and applies the internal probe environment only to the rescue-smoke create subprocess, with unit coverage for both sides of the boundary.

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
  did not run `greenfield_post_confirm_matrix.py`. The matrix was therefore
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

- Agent Guardrails: Before claiming release readiness, run hard prompts with overloaded terms such as state, agent, model, case, claim, release, record, proof, system, consent, and verify governed writes plus expert lenses. Capture failures in Casebook before fixing. Release scoring must inspect persisted artifact readback, not only producer manifests or create stdout.

- Preflight Checks: Search CB-208 and this bug before changing greenfield completion, final quality gates, repair routing, or release matrix proof.

- Version/Build: 0.1.15 local release dist `odylith-local-release-0.1.15-3d13f434` failed the expanded thirteen-case installed standard matrix. Twelve standard cases passed with hard 10/10 scores in 23.410-26.861s and installed rescue smoke passed in 33.936s as synthetic wiring-only proof, but sparse disclosure confirmation failed the release gate with score 0/10 because component depth and domain-anchor coverage were insufficient. Full release readiness and natural rescue quality remain unclaimed.

- Related Incidents/Bugs: CB-208

- Code References: - src/odylith/runtime/domain_intelligence
- src/odylith/runtime/domain_intelligence/artifact_tribunal_actors.py
- src/odylith/runtime/reasoning/tribunal_lens.py
- src/odylith/runtime/artifact_quality/greenfield_quality_lenses.py
- src/odylith/runtime/common/mermaid_text.py
- scripts/release/greenfield_post_confirm_matrix.py
- scripts/release/greenfield_rescue_smoke.py
- src/odylith/runtime/project_intelligence/source_launch.py
- src/odylith/runtime/domain_intelligence/greenfield_experience.py
- tests/unit/runtime/test_greenfield_confirmed_surfaces.py
- tests/integration/runtime/test_greenfield_hiit_post_confirm_quality.py
