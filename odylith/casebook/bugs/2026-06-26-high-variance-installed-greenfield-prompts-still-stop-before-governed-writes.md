- Bug ID: CB-209

- Status: Open

- Created: 2026-06-26

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: High-variance installed greenfield prompts still stop before governed writes

- Impact: Harder real-world greenfield prompts can pass proposal generation but fail post-confirm create before Radar, Registry, Atlas, release, traceability, and quality-manifest records are committed, leaving only partial runtime/source artifacts.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 local release dists installed into fresh consumer repos under /Users/freedom/mock, including /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-17e8a6f6, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-cedafc79, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-b0713a0a, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-33bdb122, and /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-265cc0cf

- Detected By: Custom high-variance installed greenfield matrix after release smoke and standard installed matrix passed

- Failure Signature: autonomous warehouse safety state and federated agent incident command returned create_returncode=2 in the earlier installed matrix; post-confirm quality manifest missing; Radar workstreams 1, Registry specs 0, Atlas sources 0, release records 0, trace nodes 0. A later installed matrix on cedafc79 fixed those two cases but exposed two additional platform failures: indigenous data sovereignty review returned create_returncode=2 before governed writes, and spacecraft anomaly triage committed records but failed rendered package quality because multiple Radar titles ended with a clipped article phrase `a`. The 33bdb122 installed matrix then reopened this bug: pediatric agency practice and security disclosure council returned create_returncode=2 before governed writes, with no quality manifest, one Radar workstream, zero Registry specs, zero Atlas sources, zero release/program records, zero trace nodes, and zero Project implementation prompts.

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
  release proof lane, expands the default standard catalog to twelve domains,
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

- Agent Guardrails: Before claiming release readiness, run hard prompts with overloaded terms such as state, agent, model, case, claim, release, record, and verify governed writes plus expert lenses. Capture failures in Casebook before fixing.

- Preflight Checks: Search CB-208 and this bug before changing greenfield completion, final quality gates, repair routing, or release matrix proof.

- Version/Build: 0.1.15 local release dist `odylith-local-release-0.1.15-atlas-state-proof` passed the expanded twelve-case installed standard matrix and CLI auto-rescue smoke with hard 10/10 standard scores, per-case generated browser state proof, and persisted matrix evidence after release-gate wiring and Atlas-state proof were tightened. Full natural rescue quality remains unclaimed because the rescue proof is still synthetic wiring-only.

- Related Incidents/Bugs: CB-208

- Code References: - src/odylith/runtime/domain_intelligence
- src/odylith/runtime/reasoning/tribunal_lens.py
- src/odylith/runtime/artifact_quality/greenfield_quality_lenses.py
- scripts/release/greenfield_post_confirm_matrix.py
- scripts/release/greenfield_rescue_smoke.py
- src/odylith/runtime/project_intelligence/source_launch.py
- src/odylith/runtime/domain_intelligence/greenfield_experience.py
