Status: In progress

Created: 2026-06-26

Updated: 2026-06-30

Backlog: B-142

Goal: Re-architect confirmed greenfield create around a typed, host-reasoned
semantic compiler and bounded semantic repair loop so Odylith can write
complete, premium-quality project and governance artifacts for arbitrary
domains without regex towers, rendered-string repair, domain-specific platform
vocabulary, or degraded packages.

## Architecture

- Compile the accepted Product Intent Confirmation into a lossless
  `ConfirmedIntentIR` with section IDs, source spans, content hash, and
  provenance.
- Ask host reasoning to build `SemanticModelIR` for ambiguous human meaning:
  actors, actions, objects, state, systems, first-path events, proof
  obligations, risks, assumptions, deferred scope, decision ledger entries, and
  rejected interpretations.
- Deterministically project `SemanticModelIR` into `ArtifactPlanIR` for Radar,
  Registry, Atlas, Compass, project brief, release proof, and operator next
  steps. Renderers must receive only sanctioned projection fields for their own
  surface.
- Render the `ArtifactDraftSet`, then run deterministic validators and typed
  PM, architect, engineer, and domain-expert lenses into a `ReviewReport`.
- On repairable final-gate failure, request a formal `PatchSet` against
  `SemanticModelIR` or `ArtifactPlanIR`, rerender only affected projections, and
  rerun the same gates before any governed write.
- Keep fail-closed transaction custody in Odylith: schema validation,
  projection isolation, artifact-size guards, grammar/copy guards,
  non-repetition guards, traceability guards, timing budgets, rollback, and
  final source-truth commit.

## Latency Budget

- Standard path: under 60 seconds, no host repair needed.
- Rescue path: up to 90 seconds only when a final semantic or quality gate
  fails and a targeted host-model semantic or plan patch can likely fix it.
- Premium/deep repair and CI simulation: 120 seconds only when explicitly
  selected. This is not the normal operator path.

## Non-Goals

- Do not hand-fix generated consumer project repos.
- Do not weaken final gates to make confirmed create pass.
- Do not make rendered Markdown, Radar prose, Registry prose, Atlas labels, or
  Compass strings the repair target.
- Do not add project/domain-specific platform terms except isolated test
  fixtures.
- Do not grow regex/template towers as the semantic repair strategy. Regex may
  support mechanical parsing and tokenization only behind named owners.

## Related Bugs

- [CB-207](../../../casebook/bugs/2026-06-26-greenfield-post-confirm-package-repair-repeats-risk-prose-across-surfaces.md)
  tracks the repeated parent-risk projection failure fixed by moving child risk
  projection into semantic workstream ownership.
- [CB-208](../../../casebook/bugs/2026-06-26-greenfield-post-confirm-repair-routing-remains-stringly-typed-instead-of-semanti.md)
  tracks the remaining architecture defect: rescue still needs typed findings
  and semantic or plan patches instead of English issue-substring routing and
  rendered-prose mutation.

## Latest Simulation Evidence

- 2026-06-30 source leakage-boundary checkpoint: a strict audit found the
  installable 09e520b3 package clean, but Registry component forensics still
  retained raw high-variance simulation phrases from Compass timeline
  summaries. The platform fix keeps raw repro language in Casebook and Compass
  evidence while making Registry `FORENSICS.v1.json` protected component
  custody: sidecar rows now store generic event summaries, component IDs,
  workstream scope, confidence, meaningfulness, and artifact counts instead of
  raw event prose or artifact paths. The platform leakage guard now scans
  `odylith/registry/source/components` alongside source, guidance, release
  scripts, and installable dist custody. Source-local proof passed py_compile,
  `git diff --check`, 68 focused leakage/Registry/render/delivery/bundle
  tests, the strengthened 285-term leakage guard, an exact Registry component
  scan with zero findings, and D-043 Atlas refresh with 46 fresh / 0 stale
  diagrams. This is not installed-release proof until the committed-head dist
  is rebuilt and the installed matrix is rerun.

- 2026-06-30 precommit release-dist proof:
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-1ef33083-precommit`
  rebuilt from the current working tree after governed readback scoring,
  helper-relative intent recovery, platform-facing vocabulary cleanup, and
  Atlas tracked-object extraction. The build gate passed the 285-term platform
  domain-leakage guard. The installed matrix proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-1ef33083-precommit/greenfield-post-confirm-matrix.v1.json`
  passed 13/13 maintained high-variance standard cases with hard 10/10
  release-quality scores, zero issues, every browser surface proof attempted
  and passed, generated terms absent from platform source/dist, complete
  governed records, five implementation prompts per project with zero prompt
  findings, max standard create time 28.697s, and average standard create time
  25.779s. Synthetic typed-probe rescue wiring passed in 33.237s under the
  90s rescue tier. This proves the standard installed path for the precommit
  checkpoint only; final release proof still requires commit, push, rebuild
  from the committed head, and rerun of the release matrix.

- 2026-06-30 committed release-dist proof: checkpoint e1f00464 rebuilt into
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e1f00464`
  after tightening greenfield rescue PatchSet custody. The release build and
  installed matrix both passed the 49-term platform domain-leakage guard. The
  maintained installed matrix proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e1f00464/greenfield-post-confirm-matrix-20260630-e1f00464.v1.json`
  passed 13/13 standard cases with hard 10/10 scores, zero issues, all
  product-manager, architect, engineer, and domain-expert lenses passing,
  per-case browser surface proof passing, complete governed records, five
  implementation prompts per project with zero prompt findings, max standard
  create time 29.110s, and average standard create time 26.014s. Synthetic
  typed-probe rescue wiring passed in 33.402s under the 90s rescue budget, but
  natural host-model semantic rescue quality remains unproven and must not be
  claimed from this wiring proof. Temp matrix and rescue roots were clean after
  the run.

- 2026-06-30 committed release-dist proof: checkpoint a258b913 rebuilt into
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913`
  after the repair-routing fix was committed and pushed. The maintained
  installed matrix proof at
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913/greenfield-post-confirm-matrix-20260630-a258b913.v1.json`
  passed 13/13 standard cases with hard 10/10 scores across completion,
  product-manager, architect, engineer, domain-expert, copy/semantic clarity,
  governance depth, traceability, implementation-prompts, latency, semantic
  manifest, and operator-usefulness dimensions. Every case wrote complete
  governed records, browser surface proof passed, no prompt findings or issues
  were reported, max standard create time was 28.925s, synthetic typed-probe
  rescue passed in 33.537s under the 90s rescue budget, and temp matrix/rescue
  roots were clean after the run.

- 2026-06-30 fresh non-reused variance proof:
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-a258b913/greenfield-post-confirm-fresh-variance-20260630-a258b913.v1.json`
  passed 10/10 new installed consumer simulations with hard 10/10 scores,
  zero issues, browser proof, complete governed records, max create time
  29.398s, and clean temp cleanup. The pass covered maternal transport
  escalation, municipal permit appeals, fusion maintenance planning, school
  accommodation review, vaccine cold-chain release, museum loan condition,
  rail outage planning, model risk waiver review, robot lockout safety, and
  API deprecation migration without changing platform source or hand-fixing
  generated repos.

- 2026-06-29 installed repair-routing checkpoint: fresh dist
  `odylith-local-release-0.1.15-14f5102a` passed the strengthened 49-term
  domain-leakage gate but failed 4/13 maintained cases before governed writes
  because accepted-project or Project dashboard previews retained repairable
  adjacent duplicate-word prose. The root cause was repair routing, not domain
  semantics: indexed artifact-draft paths were authorized but not traversed,
  and Project dashboard preview leaves outside the original prompt whitelist
  could be detected without gaining safe mechanical repair authority. The fix
  keeps the architecture generic: exact typed leaf paths now cover concrete
  Project dashboard preview leaves and the path parser reaches list-indexed
  scalar leaves before applying the existing duplicate/tail cleanup. Focused
  proof passed 44 artifact-plan/quality-repair tests, 25 package/source-launch
  and repetition tests, 76 post-confirm engine/repair tests, py_compile,
  Casebook validation, and the 49-term domain-leakage guard. A fresh
  installable precommit dist replayed the four failed cases with browser proof
  and all four passed at hard 10/10 in 27.038-29.000s; the full maintained
  installed matrix then passed 13/13 cases with hard 10/10 scores, zero issues,
  generated browser proof, complete governed records, max standard create time
  29.244s, synthetic typed-probe rescue wiring in 33.836s, and clean temp
  cleanup. The subsequent committed checkpoint a258b913 passed the maintained
  installed release-dist proof above.

- 2026-06-26 faithful propose-then-confirm source-local proof:
  quantum-tunneling education completed post-confirm create in 11.668 seconds
  with no simple artifact red flags; shelter-capacity coordination failed in
  9.668 seconds with Radar, Atlas, and project brief semantic-coverage
  blockers for the first-path contract plus a repeated visible-result sentence
  in the Radar index.
- The failure shows the current PatchSet seam is necessary but insufficient:
  repairable semantic-coverage findings can still be routed as artifact-plan or
  package-shape problems, then the apply side replays deterministic completion
  without a host-reasoned semantic or plan patch that changes the failed
  meaning/projection facts.
- The earlier five-scenario shortcut harness was not a faithful operator-path
  proof for all cases because two temp repos supplied too-thin confirmed-intent
  files and hit the internal-systems preflight gate before post-confirm repair.
  It remains useful only for cleanup/timing discipline and simple copy red-flag
  sampling.
- 2026-06-26 faithful high-variance checkpoint: wellness/safety, finance/risk,
  creative/media, and overloaded record/case/agent/model/release prompts all
  completed `greenfield propose` followed by confirmed `greenfield create` in
  13.1-13.5 seconds. Each run wrote four Radar records, three Registry specs,
  six Atlas Mermaid sources, six SVG renders, six PNG renders, and had zero
  semantic-slop, proposal-quality, or rendered-package quality issues in the
  post-run QA harness. Temp repos were deleted after every run.
- This checkpoint fixed three general projection defects without adding
  domain-specific platform terms: non-action first paths now route through a
  shared semantic first-path repair owner, visible result nouns are rendered as
  result objects before actor-led action stripping, and child workstream risk
  projection preserves governed risk posture even when parent risk posture is
  absent.
- 2026-06-26 fresh source-local variance pass: neonatal transfer coordination,
  offshore wind maintenance, court evidence redaction, and food relief routing
  passed under 16.2 seconds with zero matrix quality issues, while quantum
  chemistry initially failed before writes on repeated visible-result prose and
  a project-brief artifact-judgment false positive. The repair stayed generic:
  structural metadata is immutable to public-copy repair, semantic patch
  routing uses explicit IR path/node tokens, result-term comparison canonicalizes
  simple inflected result words against base action words, proof-ledger labels
  no longer duplicate proof-record suffixes, and preview artifact judgment
  reviews values rather than Python mapping syntax.
- 2026-06-26 final source-local matrix proof for this checkpoint: all five
  unrelated domains passed `greenfield propose` followed by confirmed
  `greenfield create` with governed writes, zero quality issues, and temp repo
  cleanup after every run: neonatal transfer coordination 15.062s, offshore
  wind maintenance 14.327s, court evidence redaction 14.730s, quantum chemistry
  runbook 14.545s, and food relief routing 14.650s. Each run produced four
  Radar workstreams, three Registry specs, six Atlas Mermaid sources, five
  rendered surfaces, release/program/project brief records, 18 trace nodes, and
  four trace workstreams.
- 2026-06-26 harder source-local variance found two additional generic quality
  failures before the next checkpoint. Evidence-oriented Registry specs could
  repeat the same opening sentence across components because the component-spec
  narrative owner used shared project evidence focus without component-local
  differentiation. A separate first-path case preserved title-case role wording
  after `see` and `reviewing`, causing final semantic gates to reject the
  validation strategy and project brief for mixed actor-role casing. The repair
  direction remains projection ownership and shared semantic casing, not
  rendered-string cleanup or domain-term exceptions.
- 2026-06-26 final ten-domain source-local matrix after the latest fixes:
  gene therapy consent 15.011s, asylum case preparation 14.475s, autonomous
  drone incident review 15.271s, municipal bond covenant monitoring 13.742s,
  marine microplastic custody 13.764s, museum restitution provenance 14.068s,
  wastewater signal triage 13.671s, quantum chemistry runbook 14.226s,
  mutual-aid logistics 14.432s, and language archive consent 14.301s. Every
  run completed the standard path without rescue, wrote governed records,
  reported zero post-confirm manifest issues, passed product-manager,
  architect, engineer, and domain-expert lenses, produced four workstreams,
  three Registry component previews/specs, six Atlas source diagrams, project
  brief, Compass memory preview, next steps, release assignment preview, and
  deleted its temp repo before the next run.
- 2026-06-26 fresh matrix replay found and fixed a prompt-source custody
  failure before post-confirm. When a source-local no-host `greenfield propose`
  guidance envelope was saved as the confirmed intent file, recovery could
  consume `Next step` and confirmed CLI instructions as product facts, leaving
  the recovered intent without valid internal product systems. The fix isolates
  the `Original user intent` block before prompt recovery, splits sentence-style
  prompts into product title and first-release action, and keeps broad
  noun-only prompts on the semantic fallback first-path owner. The exact
  orbital-debris replay now passes confirmed create in 14.465s wall time with a
  standard passed manifest, zero issues, governed records written, and temp
  cleanup.
- 2026-06-26 affected confirmed-intent validation exposed a proof-boundary
  projection custody miss. A release limit expressed in the accepted proof
  boundary with `without claiming ...` was dropped when post-confirm completion
  rewrote proof workstream metrics from component contracts. The fix preserves
  proof-boundary limits in both initial backlog proof metrics and the
  completion reconciler, and broadens release-proof row detection to trust plus
  evidence/release/validation semantics.
- 2026-06-26 final checkpoint proof after prompt-source, proof-boundary, and
  shared release-scope helper fixes: affected confirmed-intent and CLI paths
  passed 69 tests in 161.14s, the broader greenfield quality pack passed 160
  tests in 50.09s, and the heavy post-confirm engine/artifact suite passed 93
  tests in 283.07s. A fresh
  ten-domain source-local matrix using `greenfield propose` output as the
  confirmed intent file passed every scenario in the standard path without
  rescue: volcano school reunification 15.413s, orbital debris conjunction
  14.826s, newborn screening exception 14.241s, water-rights hearing evidence
  14.761s, key rotation incident readiness 15.258s, archaeological dig context
  custody 14.577s, cold-chain spoilage triage 13.970s, hiring audit response
  15.504s, soil carbon verification 13.996s, and courtroom translation access
  15.105s. Every run wrote governed records, reported zero manifest issues,
  passed PM/architect/engineer/domain-expert lenses, produced four Radar
  workstreams, three Registry specs, six Atlas diagrams, and deleted its temp
  repo before the next scenario.
- 2026-06-26 artifact-plan PatchSet execution checkpoint: architecture review
  found that `ArtifactPlanIR` operations were emitted but not executable.
  `greenfield_artifact_plan_patch_executor.py` now applies formal
  `target_layer: artifact_plan` replacement facts to sanctioned proposal
  projection roots, refuses prose-only replacements, preserves structural
  custody fields such as ids, slugs, schema versions, paths, and timestamps,
  and records an `artifact_plan_patch_ledger` for every applied operation. The
  focused executor test passed 2 tests in 0.14s, compile proof passed, and the
  widened post-confirm repair/artifact-quality suite passed 229 tests in
  321.33s. Full host-authored semantic compiler integration and
  affected-projection-only rerender remain open.
- 2026-06-26 recovery/completion checkpoint: a five-domain source-local
  simulation initially passed four domains but failed clinical trial
  consent/adverse-event triage before writes because valid recovered internal
  systems were collapsed during completion. The same repro then surfaced a fake
  actor candidate from the imperative step `release a first-slice monitoring
  report`. The fix preserves explicit spaced-hyphen recovered system rows
  through completion and treats actorless imperative `release ...` clauses as
  action steps inside recovered actor extraction without changing global prose
  grammar. Targeted proof passed 24 tests in 39.63s, the broad greenfield pack
  passed 283 tests in 491.56s, and a fresh five-domain source-local matrix
  passed in 13.649-14.379s with zero issues, all expert lenses passing,
  governed writes, and temp cleanup after every case.
- 2026-06-26 installed-dist variance checkpoint: the cedafc79 standard
  installed matrix passed five domains at 17.074-18.574s with zero issues and
  all PM/architect/engineer/domain-expert lenses passing, but a harder custom
  installed matrix exposed two more generic owner defects. Indigenous data
  sovereignty failed before governed writes because the semantic compiler
  rejected `release readiness for ...` as proof-control text instead of a
  first-path result event. Spacecraft anomaly triage wrote records but failed
  package quality because passive object-state text was promoted into a human
  actor and leaked `State Before a` into Radar copy. The fix stays in semantic
  custody: proof-control classification was narrowed, first-path extraction now
  respects hyphenated noun-compound boundaries, and recovered actor extraction
  rejects passive object-state subjects. Current source proof: focused
  regressions passed 4 tests in 17.61s, the two failing source CLI simulations
  passed in 12.708s and 12.328s with complete governed records and all expert
  lenses, and the widened greenfield suite passed 162 tests in 148.37s. Fresh
  installed proof from a rebuilt dist remains required before release closure.
- 2026-06-26 typed projection-contract checkpoint: architecture review found
  `ArtifactPlanIR` projection policy duplicated between PatchSet emission,
  artifact-plan execution, and safe artifact-draft repair. The cleanup adds
  `greenfield_artifact_plan.py` as the shared owner for sanctioned roots,
  projection aliases, immutable fields, affected projection calculation, and
  artifact-draft repair projection normalization. Role-surface names such as
  product-manager or architect no longer imply affected projections without a
  typed projection ID or artifact path. `greenfield_apply_semantic.py` now
  persists a typed apply-semantic input with source-path provenance and asks
  the semantic compiler for high-confidence visible-result candidates instead
  of carrying a local visibility regex. Focused proof passed 60 tests in
  26.47s, compile proof passed for the changed modules, Registry validation
  passed, and `domain-intelligence` component-spec requirement sync converged.
  This is a structural checkpoint only; fresh high-variance create simulations
  and live rescue proof remain required before release closure.
- 2026-06-26 architectural cleanup checkpoint: post-confirm repair no longer
  lets untyped English gate strings drive semantic routing. Raw completion
  report issues now become `legacy_untyped_report` blockers, raw package issue
  strings become `legacy_package_artifact_gate` blockers, and package review
  uses source-owned typed findings for semantic coverage, release drift,
  Registry preview/spec shape, and explicitly safe mechanical copy cleanup.
  Rescue/deep host reasoning is wired through
  `greenfield_post_confirm_rescue_planner.py` and the general-purpose
  `tribunal_patch_planner.py`; the host may fill only replacement facts,
  decision-ledger entries, proof-obligation deltas, rejected interpretations,
  and confidence for existing PatchSet operations after remaining-budget
  checks. `greenfield_semantic_patch_executor.py` now patches
  `SemanticModelIR` first and mirrors accepted-intent fields only for current
  compatibility. D-043 was replaced with the current architecture topology and
  Atlas refreshed to 44 fresh diagrams / zero stale diagrams. Initial focused
  proof: semantic patch executor passed 5 tests in 0.28s. The widened
  post-confirm suite passed 152 tests in 669.31s, governance validation passed,
  and installed-dist proof from commit d42f127c passed five high-variance
  consumer-lane creates in 20.107-23.147s with zero final quality issues and
  temp cleanup after every scenario.
- 2026-06-26 source-local variance proof after rescue/provider hardening:
  eight new domains passed real `greenfield propose` followed by confirmed
  `greenfield create --repair-tier auto` in the standard path without rescue:
  tribal clinic referral consent 14.434s, satellite anomaly readiness 15.514s,
  court interpreter access 15.362s, museum restitution provenance 14.948s,
  wildfire mutual aid logistics 14.549s, battery recycling audit 14.910s,
  cross-border aid disbursement 15.361s, and industrial water reuse permits
  14.749s. Every run committed governed records, reported zero final quality
  issues, passed product-manager, architect, engineer, and domain-expert
  lenses, produced four Radar workstreams, three Registry specs, six Atlas
  Mermaid sources, five rendered surfaces, 18 trace nodes, release/program/
  project brief records, and deleted its temp repo before the next case. This
  proves the normal path remains provider-free and under 60 seconds across a
  fresh, higher-variance sample after the structured rescue changes. Fresh
  installed-dist proof after this source-local checkpoint remains required
- 2026-06-27 typed PatchSet dispatch cleanup: PatchSet operations now carry
  `operation_kind`, `repair_owner`, and `projection_kind`; Tribunal structured
  patch validation preserves those caller-owned fields; post-confirm apply no
  longer routes first-path repair from `rejected_interpretation` prose; and
  quality-lens findings without structured replacement facts no longer
  rehydrate proposal fields from failed check names. Focused post-confirm,
  semantic patch, quality-lens, and Tribunal patch-planner proof passed 58
  tests in 24.85 seconds.
- 2026-06-27 actor-title projection failure and fix: a six-case
  source-local matrix initially passed legal evidence disclosure, battery
  warranty telemetry, student nutrition exception, satellite imagery claim,
  and agent memory release tribunal, but failed museum loan provenance in
  16.491s because Radar workstream titles clipped actor context to dangling
  article phrases such as `before an`. The fix trims temporal/proof context
  tails in recovered actor labels before workstream title projection and drops
  event nouns introduced by that context boundary. The widened
  post-confirm quality/slop/text suite passed 181 tests in 71.68s. A replay of
  the failing museum case plus five fresh domains then passed in
  14.005-15.737s with zero quality issues, governed writes, four Radar
  workstreams, three Registry specs, six Atlas Mermaid sources, five rendered
  surfaces, 18 trace nodes, all PM/architect/engineer/domain-expert lenses
  passing, and temp-root cleanup confirmed.
  before release closure.
- 2026-06-26 fresh installed-dist proof for commit 58a9b7c5: local release
  dist `odylith-local-release-0.1.15-58a9b7c5` passed the installed
  greenfield post-confirm matrix across flood shelter intake 20.393s,
  pediatric agency practice 18.368s, semiconductor lab custody 18.393s, port
  berth carbon tariff 18.450s, and security disclosure council 19.048s. Every
  installed consumer-lane run reported zero matrix quality issues, wrote
  governed records, produced at least five Radar records, three Registry
  records, six Atlas diagrams, 18 trace nodes, and the harness deleted
  temporary repos after the cases.
- 2026-06-29 fresh installed release-gate failure from dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e7bc3be3`:
  the maintained thirteen-case standard matrix passed twelve cases at hard
  10/10 and under 28 seconds, but `security disclosure council` failed before
  governed writes in 12.96 seconds with `greenfield rendered package repeats
  noncanonical prose across 3 artifact(s)` for the repeated object-list tail
  beginning `Affected partner review, embargo decisions, evidence custody,
  legal signoff, and public advisory release readiness...`. Synthetic rescue
  smoke passed in 34.393 seconds and temp matrix dirs were cleaned. The root
  cause is generic: canonical first-path projection facts carry full
  actor/action/object custody but not typed action-complement or object-list
  tail custody when surfaces render the tail without the leading action/object.
  Fix the semantic projection custody; do not add disclosure/security
  vocabulary, regex towers, or weaker repetition gates.
- 2026-06-29 source-local recovery after the `13b796e9` fresh-variance
  failures: root-cause review found three general platform defects rather than
  project-specific bad data. Actorless comma action chains could invent a
  carried subject because subject carry trusted a reverse action-word fallback;
  proof/evidence components could be demoted by negative proof-boundary tails
  before affirmative proof ownership was considered; and matrix scoring could
  over-credit runtime custody artifacts, accepted-project source text, and
  skipped browser proof. The repair keeps semantic custody generic: shared
  actor-role ownership, explicit-subject carried-action parsing, affirmative
  proof/evidence release-scope polarity, public-artifact-only matrix readback,
  real project-brief/next-step artifact counts, and fail-closed browser-proof
  defaults. Focused proof passed 95 tests in 89.90s; the full general
  artifact-quality suite passed 52 tests in 499.18s; and six fresh
  source-local simulations across space science, climate MRV, public
  infrastructure, civic response, workforce credentials, and port tariff
  governance all completed under 23s with hard 10/10 scores, zero issues,
  complete Radar/Registry/Atlas/release/trace counts, and temp cleanup.
  Installed dist proof remains the release blocker.
- 2026-06-29 installed checkpoint from pushed commit `a4ede761`: fresh local
  dist `odylith-local-release-0.1.15-a4ede761` passed the maintained installed
  greenfield post-confirm matrix. All 13 standard cases completed in
  22.726-27.078s with hard 10/10 scores, zero quality issues, 4 Radar
  workstreams, at least 3 Registry specs, 6 Atlas diagrams, project brief
  evidence, 18+ trace nodes, 5 Project implementation prompts, and all
  product-manager, architect, engineer, and domain-expert lenses passing.
  Per-case headless generated-surface browser proof attempted and passed for
  all 13 cases with zero browser issues, temp cleanup was clean, and synthetic
  typed-probe rescue wiring smoke passed in 33.430s. Natural host-model
  semantic rescue quality remains separate from this wiring proof.
- 2026-06-29 fresh installed proof from pushed commit `f5fef9e6` reopened the
  sparse-topology release gate before any release-ready claim. The maintained
  matrix passed twelve of thirteen standard cases with hard 10/10 scores in
  18.441-43.304s, but `sparse disclosure confirmation` scored 0/10 after
  governed writes in 20.591s because readback found only two Registry specs and
  17 trace nodes. The root cause is generic: the previous explicit two-system
  guard suppressed completion for both rich accepted narratives and terse or
  generated two-row topology. The same diagnosis found internal compiler
  labels such as `Relevant behavior:` and `Rationale:` leaking into public
  Registry copy. Source now distinguishes sparse/generated system rows from
  rich explicit rows, tops up only the sparse topology, and renders confirmed
  system descriptions without compiler labels. Focused proof passed 3 tests in
  13.41s, the broad affected greenfield pack passed 202 tests in 250.95s, and
  compile proof passed. Installed proof from a rebuilt dist remains required.
- 2026-06-29 installed proof from pushed commit `db69b062` passed the
  maintained release matrix for the sparse-topology checkpoint. Fresh local
  release dist `odylith-local-release-0.1.15-db69b062` passed all thirteen
  standard installed cases with hard 10/10 scores, zero quality issues,
  generated browser proof for all cases, strict temp cleanup, 4 Radar
  workstreams per case, at least 3 Registry specs per case, 6 Atlas diagrams,
  5 Project implementation prompts, all PM/architect/engineer/domain-expert
  lenses passing, and standard create times of 21.927-26.698s. The retained
  sparse disclosure case passed in 21.927s with 3 Registry specs and
  18 trace nodes; the retained quantum case passed in 26.698s with 5 Registry
  specs and 20 trace nodes. Synthetic typed-probe rescue wiring passed in
  32.728s; natural host-model semantic rescue quality remains separate.

## Implementation Slices

- [ ] Define `ConfirmedIntentIR`, `SemanticModelIR`, `ArtifactPlanIR`,
      `ArtifactDraftSet`, `ReviewReport`, and `PatchSet` schemas with source
      provenance and stable IDs. Current checkpoint defines typed
      `ReviewReport` findings, `PatchSet` request schemas, a source-mapped
      apply-semantic input bridge, and the first shared `ArtifactPlanIR`
      projection contract owner. A lossless `ConfirmedIntentIR`, full
      `ArtifactPlanIR` schema, `ArtifactDraftSet` schema, and stable source-span
      IDs remain open.
- [x] Convert final package validators to emit typed finding codes, source-map
      targets, semantic node IDs, projection IDs, severity, and repairability.
      `greenfield_post_confirm_findings.py` now owns typed finding collection
      for proposal, semantic, component, package, and quality-lens gates.
- [x] Replace post-confirm issue-substring routing with typed finding routing.
      Internally generated reports classify and build failure signatures from
      typed findings. Untyped completion reports are now fail-closed
      `legacy_untyped_report` blockers, and raw package issue strings are
      `legacy_package_artifact_gate` blockers with no semantic repair
      authority. `greenfield_post_confirm_patch_apply.py` consumes
      operation-level `PatchSet` entries instead of target-layer/source sets,
      preserves target path plus semantic node context, and leaves
      artifact-draft-only operations out of proposal mutation.
- [ ] Replace rendered-prose package repair with semantic or plan patch
      application and impacted-projection rerender. Current checkpoint emits a
      formal `PatchSet` request into the manifest and repair context, applies
      current deterministic semantic/quality-lens proposal repairs through an
      executable PatchSet seam, maps affected artifact projections from typed
      projection IDs or target paths, and source-types package semantic
      coverage plus shape findings before repair. The remaining mechanical
      copy cleanup is explicitly bounded to generated draft copy issues such as
      duplicate adjacent words and dangling tails; it is not allowed to route
      semantic drift. The Radar handoff regression and raw first-path risk-copy
      regression have been moved upstream into projection owners instead of
      rendered-package cleanup:
      `greenfield_traceability.py` normalizes validation sentence shape before
      Radar render, `artifact_enrichment.py` preserves complete validation
      predicates, and `greenfield_workstream_risk_projection.py` projects
      semantic visible-result evidence instead of raw comma-heavy first-path
      chains. Full host-authored semantic or plan patch application plus
      impacted-projection rerender remain open for semantic patches. The
      artifact-plan-only path now has a scoped package rerender seam:
      the artifact-draft cleanup path is now metadata-gated mechanical-only.
      Mixed action inflection, modal/base-form drift, malformed ownership
      pairs, and malformed component responsibility route to typed plan repair
      or fail closed; the draft cleaner may only collapse adjacent duplicate
      words or trim dangling tails when an `artifact_draft_mechanical_copy`
      PatchSet operation from `artifact_draft_cleaner` carries no semantic
      replacement facts.
      `greenfield_artifact_plan.py` expands affected projection dependencies
      and marks Radar/program scopes as full-prewrite, `greenfield_post_confirm_patch_apply.py`
      records a patch application ledger, `greenfield_post_confirm_engine.py`
      consumes that ledger on the next pass, and
      `greenfield_prewrite_projection_rerender.py` refreshes only the named
      prewrite package previews when staged recomputation is not required.
      A pre-commit review caught and fixed two custody escapes in this seam:
      `program` must remain a first-class projection until the full-prewrite
      guard runs, and release-scope rerender must include Compass because
      release assignment feeds Compass acceptance preview state.
- [x] Execute artifact-plan PatchSet operations for sanctioned projection
      facts. `greenfield_artifact_plan_patch_executor.py` applies only formal
      `artifact_plan` replacement facts against approved proposal roots for
      project brief, Radar backlog, Registry components, Atlas diagrams,
      release plan, program, assumptions, questions, risks, and validation
      strategy. It rejects prose-only patches, protects ids, slugs, schema
      versions, source paths, and timestamps, and records the plan-patch
      decision ledger before proposal normalization and completion rerun.
- [ ] Promote semantic-coverage failures to first-class semantic/projection
      patch obligations before rerender. The shelter-capacity failure proves
      overlap-based coverage checks can detect missing first-path projection but
      cannot repair it unless the `PatchSet` names the `FirstPathContract`,
      affected projection field, rejected interpretation, and sanctioned
      replacement fact.
      Current checkpoint routes first-path semantic-coverage findings to
      `SemanticModelIR.first_path_contract` and applies the existing
      deterministic semantic first-path repair through the PatchSet seam. Full
      host-authored semantic patches and affected-projection-only rerender
      remain open.
- [x] Isolate host-guidance envelopes before confirmed-intent recovery.
      `greenfield_confirmed_prompt_source.py` now recovers title and first-path
      sources from the `Original user intent` block rather than operational
      proposal instructions, and sentence-style prompts such as `Build a
      proposal for X. The first release should let Y...` split title from
      action before validation.
- [x] Preserve source-local recovered intent facts through completion.
      `greenfield_confirmed_system_completion.py` now keeps explicit
      spaced-hyphen recovered internal-system rows as canonical system
      name/description facts instead of collapsing them into one generic
      component-responsibility row, and
      `greenfield_confirmed_intent_recovery.py` rejects actorless imperative
      `release ...` steps as fake human actors during recovery.
- [x] Preserve negative proof-boundary release limits through backlog
      completion. `greenfield_release_scope_limits.py` owns generic
      proof-boundary limit extraction, `greenfield_confirmed_backlog.py`
      projects those limits into proof workstream deferred-scope metrics, and
      `greenfield_confirmed_completion.py` preserves them when
      component-contract reconciliation rewrites success metrics.
- [x] Add a host-reasoned semantic patch executor with bounded schema:
      `operation_id`, `semantic_node_id`, `target_path`, `affected_projections`,
      `replacement_fact`, `decision_ledger_entry`, `proof_obligation_delta`,
      `rejected_interpretation`, and confidence. Reject prose-only patches.
      Current checkpoint applies host-authored `replacement_fact` operations to
      `SemanticModelIR` nodes first, mirrors accepted-intent fields only for
      compatibility with current completion, retains proof-obligation deltas in
      the decision ledger, and routes only by explicit IR target tokens instead
      of incidental substrings. The broader host-model semantic compiler call
      remains a separate open integration.
- [ ] Add context-starved renderer contracts so Radar, Registry, Atlas,
      Compass, release proof, and next steps cannot cross-contaminate.
      Current checkpoint adds the first projection contract split:
      modal-safe actions, visible-result outcome actions, and child risk
      posture are resolved in shared projection owners before renderers compose
      surface copy. Public-copy package repair now treats structural path,
      identity, slug, schema, status, version, URL, and record-reference fields
      as immutable custody metadata. Evidence-role Registry openings now must
      render from component-local label, focus, and output facts rather than a
      repeated project-level evidence sentence. A broader explicit
      `ProjectionLexicon` remains open. The current checkpoint centralizes
      artifact-plan projection routing in `greenfield_artifact_plan.py` so
      PatchSet emission, artifact-plan execution, and safe draft repair share
      sanctioned roots, projection aliases, immutable metadata policy, and
      affected-projection calculation instead of carrying private maps.
- [x] Add high-variance simulation fixtures and artifact-quality scoring across
      PM, architect, engineer, and domain-expert lenses.
- [x] Add standard latency proof and temp-repo pruning proof for the
      recursive simulation loop.
      Rescue under 90s remains architecturally available, but this checkpoint's
      proof stayed in the standard under-60s path without host repair.

## Risks & Mitigations

- [ ] Risk: Host reasoning improves semantic quality but makes normal creates
      slower or nondeterministic.
  - [ ] Mitigation: Keep one standard semantic compiler call, use deterministic
        planning/rendering/custody, and reserve host repair for final-gate rescue.
- [ ] Risk: Typed repair becomes another wrapper around rendered text.
  - [ ] Mitigation: Tests must fail if a repair mutates rendered Markdown,
        Radar prose, Registry prose, Atlas labels, Compass entries, or release
        proof strings directly.
- [ ] Risk: Artifact lenses produce readable diagnostics but cannot drive repair.
  - [ ] Mitigation: Every lens finding must carry a finding code, semantic node
        ID, source-map target, projection ID, severity, and repairability.
        The first shared `tribunal_lens.py` contract now pins that custody
        metadata at judgment time for greenfield PM, architect, engineer, and
        domain-expert lenses instead of reconstructing it later from prose.
- [ ] Risk: The architecture record passes while generated artifacts remain
      below the premium human bar.
  - [ ] Mitigation: Completion requires fresh high-variance end-to-end
        simulations, validators, timing evidence, and PM/architect/engineer/
        domain-expert artifact-quality reports.

## Validation

- [x] Source-local root-cause proof after the fresh installed variance
      failures: first-path carried-subject parsing, shared actor-role custody,
      release-scope proof polarity, and matrix public-artifact scoring passed
      the focused 95-test bundle, the 52-test general artifact-quality suite,
      and six fresh source-local high-variance creates under 23s with hard
      10/10 scores, all expert lenses passing, governed writes, and temp
      cleanup. Fresh installed-dist proof is still pending before release
      readiness.
- [x] Installed consumer-lane proof from pushed commit `a4ede761`: fresh dist
      `odylith-local-release-0.1.15-a4ede761` passed 13 maintained standard
      cases with hard 10/10 scores, zero issues, per-case browser proof
      passing, clean temp cleanup, and synthetic rescue wiring smoke at
      33.430s.
- [ ] Unit tests for semantic IR construction, ambiguity decision ledger,
      rejected interpretations, projection isolation, and source-map targets.
- [x] Unit tests proving typed findings classify failures and feed repair
      context without validator-message substring matching.
- [ ] Unit tests proving `PatchSet` repair applies to `SemanticModelIR` or
      `ArtifactPlanIR`, rerenders only impacted projections, and never edits
      rendered artifacts directly. Current checkpoint proves the operation-level
      PatchSet seam routes existing deterministic proposal repair and refuses
      proposal mutation for artifact-draft-only operations; full host-authored
      semantic/plan patch application and impacted rerender proof remain open.
      Artifact-plan execution is now covered by
      `test_greenfield_artifact_plan_patch_executor.py`, which proves
      sanctioned projection-field updates, immutable metadata refusal, ledger
      capture, and integration through `apply_greenfield_patchset_repairs`.
      The artifact-draft executor now has focused tests proving that semantic
      grammar is not rewritten even with draft permission, non-mechanical
      artifact-draft operations are rejected, and the remaining cleanup surface
      stays limited to duplicate-word and dangling-tail mechanics.
      Installed consumer-lane proof from a temporary local release passed five
      high-variance post-confirm creates in 18.489-20.286 seconds with governed
      writes, zero quality issues, all PM/architect/engineer/domain-expert
      lenses passing, and temp cleanup verified.
- [x] End-to-end confirmed-create tests proving governed records are written
      after final package quality passes for the current prewrite transaction
      slice. The ecommerce handoff regression now passes, the widened
      greenfield slice passed with 231 tests in 137.78 seconds, and
      `test_greenfield_post_confirm_engine.py` plus
      `test_greenfield_prewrite_transaction.py` passed with 75 tests in
      315.34 seconds.
- [x] Focused seam validation passed with
      `test_greenfield_post_confirm_engine.py`,
      `test_greenfield_post_confirm_quality_repairs.py`,
      `test_greenfield_post_confirm_slop_regressions.py`,
      `test_greenfield_package_repetition_quality.py`, and
      `test_greenfield_radar_projection_quality.py`: 130 tests in 60.09
      seconds.
- [x] Timing tests proving standard under 60 seconds.
- [x] Rescue-path timing proof under 90 seconds after host-authored semantic
      repair is wired end to end.
- [x] Recursive high-variance simulation runs across unrelated domains with
      temp repos deleted after each run.
- [x] Artifact QA reports for each simulation using PM, architect, engineer,
      and domain-expert gates.
- [x] Checkpoint simulation proof: four faithful high-variance post-confirm
      creates passed under the standard 60-second path with temp cleanup and
      automated semantic/proposal/package QA at zero issues. This is a slice
      checkpoint, not final release-quality proof for arbitrary domains.
- [x] Checkpoint simulation proof: five fresh unrelated domains passed under the
      standard path with zero matrix quality issues and temp cleanup after every
      scenario.
- [x] Final checkpoint simulation proof: ten fresh high-variance domains passed
      under the standard path in 13.671-15.271 seconds with zero post-confirm
      manifest issues, all PM/architect/engineer/domain-expert quality lenses
      passing, governed records written, and temp cleanup after every scenario.
- [x] Widened regression proof after the latest fixes: post-confirm engine,
      semantic patch executor, and slop regressions passed 126 tests in
      72.62s; full greenfield artifact quality passed 49 tests in 268.59s;
      component/diagram/install-matrix unit proof passed 17 tests in 0.53s; and
      prewrite transaction proof passed 52 tests in 339.63s.
- [x] Latest regression proof: confirmed text, component spec narrative,
      component spec quality, post-confirm quality repairs, and slop
      regressions passed 160 tests in 47.14s; post-confirm engine, semantic
      patch executor, package repetition, Radar projection, and general
      artifact quality passed 93 tests in 273.24s.
- [x] Prompt-source recovery proof: confirmed-intent recovery passed 20 tests
      in 29.75s, including full propose-envelope isolation, sentence-style
      title/path recovery, and broad noun-only semantic fallback behavior.
- [x] Proof-boundary preservation proof:
      `test_confirmed_greenfield_create_completes_thin_intent_before_governed_records`
      passed in 6.12s after the completion reconciler retained the accepted
      release limit in proof workstream success metrics.
- [x] Final checkpoint proof: affected confirmed-intent/CLI paths passed 69
      tests in 161.14s; greenfield quality pack passed 160 tests in 50.09s;
      heavy post-confirm engine/artifact suite passed 93 tests in 283.07s; ten
      fresh high-variance source-local simulations passed in 13.970-15.504s
      with zero issues and temp cleanup after every scenario.
- [x] Artifact-plan PatchSet executor proof: focused tests passed 2 tests in
      0.14s, compile proof passed for the changed modules, and the widened
      post-confirm repair/artifact-quality pack passed 229 tests in 321.33s.
- [x] Typed projection-contract proof: `test_greenfield_artifact_plan_ir.py`,
      `test_greenfield_artifact_plan_patch_executor.py`,
      `test_greenfield_semantic_compiler.py`,
      `test_greenfield_post_confirm_engine.py`, and
      `test_greenfield_semantic_patch_executor.py` passed 60 tests in 26.47s;
      compile proof passed for the changed modules; `git diff --check` passed;
      Registry validation passed under `enforce-critical`; and
      `domain-intelligence` component requirement sync converged.
- [x] Recovery/completion proof: targeted recovery regressions passed 24 tests
      in 39.63s; the broad greenfield pack passed 283 tests in 491.56s; and
      five high-variance source-local simulations passed with governed writes,
      zero quality issues, all PM/architect/engineer/domain-expert lenses
      passing, and temp cleanup after every case.
- [x] Tribunal lens custody proof: `test_tribunal_lens.py`,
      `test_greenfield_quality_lens_repair.py`, and focused post-confirm
      bridge tests passed 8 tests in 0.52s. The widened focused set covering
      Tribunal lenses, quality-lens repair, post-confirm engine, artifact-plan
      PatchSet execution, live simulation regressions, and modal first-path
      semantics passed 53 tests in 85.82s.
- [x] Repair tier budget proof: `repair-tier=auto` now starts on the standard
      60-second budget and only extends to the 90-second rescue budget after a
      repairable final semantic or quality failure activates rescue. Focused
      post-confirm engine timing tests passed 4 tests in 0.23s, and the
      widened engine plus semantic/artifact-plan patch executor set passed 42
      tests in 22.83s.
- [x] Tribunal structured-patch planning unit proof: rescue/deep repair now
      uses a general-purpose Tribunal planner to ask the configured host
      reasoning provider for a formal semantic or artifact-plan patch, validate
      schema/evidence/custody fields, and merge only accepted replacement facts
      into existing PatchSet operations. Focused planner and rescue seam tests
      cover custody-field preservation, invented-target rejection,
      standard-tier no-op behavior, and rescue-tier planner integration.
- [x] Live structured-patch provider proof: the Codex CLI reasoning adapter now
      ignores unsafe user config, supplies an explicit `gpt-5.4` model for
      general structured repair when config is blank, maps the legacy Spark
      alias to the live CLI token, and removes the unsupported `gpt-5.3-codex`
      rung from automatic cheap structured fallback. Tribunal patch planning
      now exposes a strict structured-output schema for decision ledger,
      proof-obligation delta, and replacement facts, with a typed replacement
      envelope materialized back into caller-owned semantic or artifact-plan
      facts after custody validation. Focused reasoning/planner tests passed
      57 tests in 0.36s, compile proof passed, and a real Codex CLI `gpt-5.4`
      planner call returned one validated `project_outcome` patch operation in
      24.895s.
- [x] Controlled rescue-write proof: a source-local temp repo used a normal
      accepted Product Intent Confirmation and valid proposal, then injected
      unique first-pass Radar semantic-coverage misses at the prewrite package
      boundary. Auto tier activated rescue, the real Codex CLI structured
      planner repaired typed semantic findings, the second pass rendered clean,
      and the normal write transaction committed governed records in 39.768s
      against the 90s rescue budget. The manifest passed with `repair_tier:
      rescue`, `rescue_activated: true`, two passes, zero final issues, four
      workstreams, three Registry component specs, six Atlas sources, and temp
      repo cleanup after the run.
- [x] IR-first semantic patch proof: `greenfield_semantic_patch_executor.py`
      now records applied `semantic_model.*` fields and leaves
      `semantic_model` alive while mirroring accepted-intent compatibility
      fields. The focused semantic patch executor suite passed 5 tests in
      0.28s.
- [x] Typed-finding/rescue cleanup proof: focused classifier,
      package-finding, rescue-planner, semantic-patch, and Tribunal
      patch-planner tests passed 17 tests in 0.44s. The widened greenfield
      post-confirm suite covering post-confirm engine, semantic patch executor,
      artifact-plan patch executor, Tribunal patch planner, general artifact
      quality, and prewrite transactions passed 152 tests in 669.31s.
- [x] Atlas governance proof for this architecture checkpoint: D-043
      `domain-intelligence-greenfield-governance` was replaced instead of
      annotated in place, then Atlas auto-update rerendered the diagram and
      refreshed impacted catalog fingerprints. `odylith atlas auto-update
      --from-git-working-tree --fail-on-stale` completed with 44 fresh diagrams
      and zero stale diagrams.
- [x] Governance validation proof for this checkpoint: Casebook source
      validation checked 205 records; Registry validation checked 30 components
      and 629 events with 292/292 meaningful events mapped; backlog contract
      validated 143 ideas; topology integrity scored 100/100; plan
      workstream-binding, risk-mitigation, and traceability validators passed;
      Atlas render check stayed at 44 fresh / zero stale; and `git diff
      --check` passed.
- [x] Fresh installed-dist proof from commit d42f127c:
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-d42f127c`
      passed the packaged consumer-lane post-confirm matrix. Five unrelated
      scenarios completed in 20.107-23.147s with zero final quality issues,
      five Radar records, three Registry records, six Atlas diagrams, 18 trace
      nodes, governed records written, and temp repos deleted before the next
      run.
- [x] Rescue-path end-to-end timing proof under 90 seconds with a real
      configured host repair remains required before release closure.
- [x] Current broad greenfield proof: confirmed-intent recovery, confirmed
      intent, post-confirm engine, semantic patch executor, quality repairs,
      package repetition, slop regressions, general artifact quality, component
      spec quality, artifact-plan PatchSet execution, and live simulation
      regressions passed 299 tests in 474.86s.
- [x] Current high-variance source-local CLI proof: six confirmed-create
      simulations passed with temp cleanup after each case and no quality
      issues. Timings: autonomous warehouse safety state 15.501s, federated
      agent incident command 14.685s, deepfake provenance escrow 15.143s,
      fusion plasma shot readiness 13.934s, indigenous data sovereignty review
      15.344s, and spacecraft anomaly triage 15.333s. Each run wrote four
      Radar workstreams, three Registry specs, six Atlas diagrams, five
      rendered surfaces, release/program records, 18 trace nodes, at least
      three required domain-term hits, and passed PM, architect, engineer, and
      domain-expert lenses.
- [x] Final installed-dist proof from commit b0713a0a: local release smoke
      exited 0 against
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-b0713a0a`.
      The standard installed matrix passed five unrelated domains at
      16.523-18.483 seconds, with governed records written and all PM,
      architect, engineer, and domain-expert lenses passing. The harder
      six-case installed matrix passed autonomous warehouse safety state
      17.356s, federated agent incident command 17.020s, deepfake provenance
      escrow 16.602s, fusion plasma shot readiness 17.302s, indigenous data
      sovereignty review 17.649s, and spacecraft anomaly triage 17.107s. Each
      installed run wrote five Radar workstreams, three Registry specs, six
      Atlas diagrams, five rendered surfaces, release/program records, 18
      trace nodes, zero package-quality issues, and passed PM, architect,
      engineer, and domain-expert lenses.
- [x] Scoped artifact-plan rerender proof: focused ArtifactPlanIR,
      artifact-plan PatchSet, post-confirm engine, semantic patch, and
      Tribunal patch-planner tests passed 66 tests in 24.12s. The wider
      greenfield post-confirm quality pack passed 242 tests in 360.05s. A fresh
      eight-domain source-local matrix passed the standard path without rescue
      across cryogenic biobank custody 15.170s, Indigenous archive consent
      14.285s, neonatal medication handoff 15.298s, orbital debris dispute
      15.177s, soil carbon verification 15.084s, museum repatriation covenant
      14.841s, grid demand fairness 15.304s, and model incident evidence room
      15.186s. Every run reported `issue_count: 0`, `repair_tier: standard`,
      `rescue_activated: false`, one post-confirm pass, all PM/architect/
      engineer/domain-expert lenses passing, four Radar workstreams, three
      Registry specs, six Atlas Mermaid sources, 18 trace nodes, governed
      writes, and temp cleanup.
- [x] Scoped semantic repair routing checkpoint: semantic PatchSet application
      now reports applied fields, operation ids, explicit affected projections,
      and whether completion is required. Semantic target routing uses
      operation-kind allowlists and exact compatibility paths rather than loose
      token splitting. Proposal-owned projection defects from package findings
      and quality lenses now route to `ArtifactPlanIR` / `plan_patch` instead
      of unsupported semantic proposal targets, and `greenfield_artifact_plan.py`
      recognizes `proposal.*`, `prewrite_package.*`, and `ArtifactPlanIR.*`
      envelope paths for projection scope. Focused ArtifactPlanIR and semantic
      patch tests passed 17 tests in 0.26s; the post-confirm repair pack passed
      74 tests in 24.54s; the widened greenfield post-confirm quality pack
      passed 250 tests in 362.79s; a temporary installed release matrix passed
      five consumer-lane domains at 18.227-19.788s with governed writes, zero
      quality issues, all PM/architect/engineer/domain-expert lenses passing,
      and temp cleanup between cases.
- [x] Quality-lens ownership contract checkpoint: the old quality-lens proposal
      rehydration engine is gone, the live quality-lens report now emits the
      canonical semantic-model/compiler, artifact-plan/projector, or prewrite
      gate owner for every known check, unknown future checks fail closed until
      their owner is declared, and `proposal_repair` is no longer an accepted
      greenfield review/rescue/PatchSet repairability. Focused quality-lens,
      post-confirm engine, and Tribunal lens tests passed 9 tests in 0.34s;
      the widened greenfield repair pack passed 252 tests in 354.43s; and a
      fresh installed consumer-lane matrix from temporary local release
      `/tmp/odylith-local-release-0.1.15-quality-lens-custody` passed five
      domains in 18.244-19.934s with governed writes, zero quality issues, all
      expert lenses passing, and temp cleanup plus release-dir pruning.
- [x] Exact-path artifact-draft and projection-rerender custody checkpoint:
      first-path semantic PatchSet operations no longer synthesize accepted
      intent from metadata-only or rejected replacement facts; profile-triggered
      component contracts derive semantic contracts before profile fallback;
      gate-only quality-lens checks remain unrepairable; rendered-package
      quality now emits exact artifact paths through
      `greenfield_rendered_artifacts.py`; and the mechanical cleaner mutates
      only the addressed artifact leaf. Corrupted rendered Registry scope now
      uses a distinct `projection_rerender` finding and deterministic scoped
      prewrite rerender instead of semantic rescue or draft cleanup, with a
      hard `missing_projection_rerender_callback` contract blocker for direct
      engine callers that omit rerender custody. Focused projection-rerender,
      quality-lens, and exact-path repair tests passed 27 tests in 4.15s; the
      flaky rendered-Registry rerender apply repro plus semantic profile and
      first-path no-synthesis guards passed 4 tests in 18.00s; the widened
      post-confirm/semantic repair pack passed 185 tests in 79.09s; and the
      prewrite/general artifact pack passed 101 tests in 692.79s before this
      checkpoint's final test decomposition.
- [x] Installed consumer-lane proof for exact-path/projection custody: a
      temporary local release built from the current source passed the installed
      greenfield post-confirm matrix across flood shelter intake 19.745s,
      pediatric agency practice 19.003s, semiconductor lab custody 18.524s,
      port berth carbon tariff 18.522s, and security disclosure council
      18.383s. Every run exited 0, wrote governed records, reported zero
      quality issues, passed product-manager, architect, engineer, and
      domain-expert lenses, produced the expected Radar, Registry, Atlas,
      release, project-brief, rendered-surface, and traceability counts, and
      temp repos plus the temporary release directory were pruned after proof.
- [x] Code-hygiene checkpoint: the oversized post-confirm engine test owner was
      split into focused patch-payload and package-quality owners. The engine
      test file is now 1409 lines, the new patch-payload owner is 333 lines,
      the package-quality owner is 779 lines, and the moved focused tests
      passed 66 tests in 29.12 seconds. The widened post-confirm repair pack
      passed 185 tests in 77.48 seconds after the split.
- [x] Brutal-score source-local checkpoint: the release matrix scoring model
      now reports hard-min 10/10 dimensions for completion, latency, semantic
      manifest, copy/semantic clarity, governance depth, traceability, operator
      usefulness, and PM/architect/engineer/domain-expert lenses. A false
      raw-file audit that treated serialized JSON quotes as public copy was
      replaced by structured package inspection. The real failing case was
      water-rights hearing evidence: recovered actor extraction turned the
      action chain into `Legal Aides Organize Diversion` because the common
      grammar did not recognize `organize` as a base action. The generic fix
      added `organize` to the shared prose grammar owner and made confirmed
      intent recovery reject actor prefixes that already contain an embedded
      action clause. Focused score/recovery proof passed 10 tests in 13.58s.
      The failed water-rights replay then passed real source-local
      post-confirm create in 17.5s with governed records and hard score 10/10.
      A final ten-domain cleanup-proof matrix passed with min score 10/10, max
      post-confirm 16.935s, and `all_cleaned=true` across neonatal handoff,
      municipal bond covenant, water-rights hearing, quantum lab, kitchen
      robot, vaccine cold-chain, film rights, distributed-agent incident
      command, wildfire grants, and museum accessibility.
- [x] Prompt-source regression checkpoint: the widened pack found that the
      earlier `use to` infinitive safeguard overcorrected role-purpose clauses
      and left `sales reps to qualify leads and managers to see pipeline
      health` unmodalized. Prompt-source now preserves `use to` first, then
      converts human-role purpose tails before action words from `to` to `can`
      without adding regex or domain templates. Focused proof passed the two
      CRM wrapper failures, the kitchen-robot `use to choose` guard, the
      water-rights actor-chain guard, and the hard-score matrix unit tests.
- [x] Fresh installed-dist brutal-score proof: local release dist
      `odylith-local-release-0.1.15-ddecaf5e` passed the installed greenfield
      post-confirm matrix across flood shelter intake 22.842s, pediatric
      agency practice 19.780s, semiconductor lab custody 22.419s, port berth
      carbon tariff 22.001s, and security disclosure council 23.035s. Every
      installed consumer-lane run scored 10/10, wrote governed records,
      reported zero issues, passed product-manager, architect, engineer, and
      domain-expert lenses, produced five Radar records, three Registry
      records, six Atlas diagrams, 18 trace nodes, and the harness deleted the
      temporary matrix repos.
- [x] Source checkpoint for Project tab implementation prompt custody:
      accepted Project dashboard `host_handoff_prompts` are now collected as
      rendered package artifacts, required once Radar/Registry/Atlas prewrite
      evidence exists, scored in the release matrix, and validated by a
      dedicated position-based prompt-quality owner rather than label
      substring checks. Prewrite now builds the Project dashboard preview from
      the target repo root so language/runtime signals match the operator
      Project tab. The same checkpoint repaired top-level intent/project-brief
      scalar semantic slop for unbalanced quotes and narrowed Odylith-surface
      risk leakage so ordinary domain words like compass or Atlas do not fail
      without platform context. Focused blocker proof passed 6 tests in
      35.44s; Project/source-launch/matrix proof passed 10 tests in 0.51s; the
      broad greenfield pack passed 241 tests in 844.71s.
- [x] Reopened installed-matrix failure and source-level prompt-fragment fix:
      the fresh 33bdb122 local release dist built successfully but failed the
      installed standard matrix in two of five cases before governed writes.
      Pediatric agency practice failed in 14.282s and security disclosure
      council failed in 10.708s with no committed quality manifest and zero
      Registry, Atlas, release, trace, or Project prompt records. Retained
      pediatric evidence showed Project source-launch prompts composing
      sentence-shaped clipped facts before comma clauses, producing malformed
      `workspace., validation points` and `workspace., input validation`
      punctuation. The source fix keeps prompt facts fragment-shaped, uses
      semantic overlap scoring to suppress duplicate action/outcome joins, and
      trims incomplete subordinate tails in operator next-step previews. Source
      replay for the saved pediatric confirmed intent now has zero
      rendered-package issues; source-mode confirmed create committed governed
      records in 15.428s; focused source-launch/next-step proof passed 3 tests
      in 0.38s; and the focused prewrite/Project package regression set passed
      58 tests in 485.56s.
- [x] Closed the reviewer-found duplicate action/outcome and rescue-proof
      harness gaps: source-launch now treats an outcome as non-distinct when
      its material terms are already contained in the action, proof fallback
      reuses the cleaned first-path projection, and the installed matrix runs
      rescue smoke by default. The first rescue harness failed review because
      rescue was opt-in and auto-rescue was a synthetic installed-engine probe;
      the replacement smoke now runs the packaged CLI in `--repair-tier auto`
      with an exact-token typed internal finding, requires auto escalation to
      the 90s rescue tier, commits governed artifacts, and fails unless the
      manifest records the semantic repair code. Focused source-launch,
      experience, probe, and matrix harness proof passed 17 tests in 0.43s;
      compile proof passed; the current broad greenfield post-confirm pack
      passed 282 tests in 933.23s; and a disposable source-local CLI
      auto-rescue probe committed governed records in 20.411s with
      `post_confirm_rescue_probe` recorded as repaired. The matrix script is
      back under the size guard at 1148 LOC after extracting
      `scripts/release/greenfield_rescue_smoke.py`.
- [x] Fixed the installed rescue-smoke env-custody miss found by the rebuilt
      265cc0cf proof: the failed matrix passed five standard cases but the
      rescue-smoke leg stayed on the standard tier because the harness applied
      the internal probe token to standard cases and left the rescue-smoke
      subprocess on a plain environment. The matrix now keeps standard creates
      clean and sends the exact internal probe token only to
      `greenfield create --repair-tier auto` inside rescue smoke. Focused unit
      proof passed 3 tests in 0.12s, the install-matrix unit pack passed 13
      tests in 0.11s, and the same packaged 265cc0cf dist passed five standard
      installed cases in 22.452-24.913s with 10/10 scores plus installed CLI
      auto-rescue smoke in 29.974s with zero issues.
- [x] Fresh installed proof after Project prompt custody: built local release
      dist `odylith-local-release-0.1.15-f6a06af6` from the pushed
      `f6a06af6` checkpoint, ran the installed standard matrix with the
      `implementation_prompts` dimension active, kept the default installed CLI
      auto-rescue smoke enabled, and verified complete governed artifacts under
      budget. Standard cases passed with hard 10/10 scores and zero issues:
      flood shelter intake 22.425s, pediatric agency practice 21.431s,
      semiconductor lab custody 20.657s, port berth carbon tariff 20.223s, and
      security disclosure council 20.605s. Installed CLI auto-rescue smoke
      passed in 26.842s with zero issues, five Radar records, three Registry
      specs, six Atlas diagrams, and 18 trace nodes.
- [ ] Reopened release blocker from brutal installed audit: a ten-domain
      installed consumer-lane audit against dist `83f3c38f` found that the
      official matrix score can still overstate quality and that an
      open-source security embargo prompt failed before governed writes in
      12.169s. The retained repro shows a source-custody defect, not a
      project defect: a no-host greenfield proposal guidance envelope saved as
      `confirmed-intent.md` leaked platform instruction language into accepted
      intent recovery, producing contrastive drift on `normalized` and
      ungrammatical structured intent text such as `The product receive...`.
      Required fix: isolate the accepted operator-intent source before any
      title, first-path, or semantic-drift recovery; repair the source model
      generically without domain terms; add regression proof for the exact
      envelope class; rerun real installed creates; and replace synthetic-only
      rescue proof with a naturally occurring repairable failure or clearly
      classify the current probe as wiring-only.
- [x] Source checkpoint for the reopened audit: confirmed-intent envelope
      recovery now stops at generic guidance headings, `open source` no
      longer triggers adapter classification, adapter copy uses accepted-result
      language instead of normalized-result language, and short first-path
      completion renders base action phrases through modal clauses so public
      copy cannot become `The product receive...`. The escaped open-source
      security embargo prompt is now part of the default installed release
      matrix. Focused parser/recovery/grammar/matrix proof passed 10 tests in
      31.18s, semantic drift and Project prompt quality proof passed 7 tests
      in 40.81s, engine/install-harness proof passed 16 tests in 17.23s, the
      live source create performance group passed 3 tests in 53.59s, and the
      exact open-source source replay committed governed records in 17.875s.
- [x] Fixed a false expert-lens release blocker found while searching for
      natural rescue evidence: a public two-component confirmed intent kept
      two active components and two rendered specs, but the PM/architect/
      engineer/domain-expert gate still failed because architect and engineer
      checks imposed an arbitrary three-component minimum. The lens now
      requires complete coverage of accepted internal systems and active
      component specs instead of a hard-coded count. Regression proof passed,
      and the same public replay committed governed records in 15.473s with a
      passed standard manifest.
- [x] Fixed a pre-engine sparse-confirmation grammar escape: a terse but valid
      confirmed intent with one-word `State object: Report` previously failed
      before the post-confirm manifest because generated semantic copy said
      `understand Report`. One-word state labels now render as lower-cased
      object phrases in mid-sentence copy. Regression proof passed, the same
      source CLI replay committed governed records in 12.227s on the standard
      path, and the installed release matrix now includes a sparse confirmed
      intent override case so packaged proof covers this operator-input shape.
- [x] Fixed a false architect-lens blocker from the full live-create suite:
      the quantum communication case correctly generated a deferred live
      telemetry component, but the lens compared active first-release
      components against all internal systems and blocked writes. Architect
      topology now checks semantic coverage across all component rows, while
      engineer readiness still requires rendered specs for active components.
      Regression proof passed, the failed quantum replay now commits governed
      records in 18.010s on the standard path, and the installed matrix now
      includes the quantum confirmed-intent shape.
- [x] Fixed the next packaged quantum matrix escape without domain-specific
      terms. Local release dist `odylith-local-release-0.1.15-231bde74` passed
      seven standard cases and rescue wiring smoke but failed the quantum
      communication case before governed writes because Atlas first-path Mermaid
      clipped the terminal result to `QBER, and the key`. The repair preserves
      result-state modifiers inside first-path semantics, normalizes terminal
      status-result item order through a result-specific status-modifier owner,
      and makes the terminal Atlas label prefer the semantic visible result when
      the step is only a long wrapper around that result. Review caught and the
      patch fixed two generic regressions: expanded result-status words no
      longer leak into artifact-tail/component cleanup, and apostrophes in
      possessive results no longer disable comma-aware status normalization.
      Focused proof covers the exact saved-intent shape, rejects
      `and the<br/>key`, preserves the complete saved/viewable result tail, pins
      the artifact-tail leak repro, and pins possessive result ordering. A live
      source replay wrote governed records in 16.746s with four Radar records,
      four Registry specs, six Atlas diagrams, 19 trace nodes, and no clipped
      terminal label. The wider artifact-quality pack then caught and the patch
      narrowed two over-broad mechanisms: terminal Atlas labels now prefer
      semantic visible results only for long clipping-risk wrappers, and
      evidence-boundary adapter recovery requires strong audit/trail/source/
      attachment/provenance naming plus external source/repository/provider
      context so history/timeline views stay services; component-kind
      classification now lives in its own owner instead of expanding confirmed
      component assembly. The repaired artifact-quality/prewrite pack passed 61
      tests in 328.35s. Fresh local release
      `odylith-local-release-0.1.15-7e548d40` passed release smoke and the
      installed greenfield matrix: eight standard consumer-lane cases completed
      in 19.887-22.399s with governed writes, zero quality issues, hard 10/10
      scores across every brutal dimension, and all PM/architect/engineer/
      domain-expert lenses passing. The installed quantum communication case
      completed in 21.296s with no clipped terminal label. The installed
      auto-rescue smoke passed in 26.587s with rescue activated; it remains
      wiring proof, not a natural rescue-quality scenario.
- [x] Added a release-proof checkpoint that avoids commit-hash recursion:
      the final local-release dist is built after the proof checkpoint commit,
      then must pass local-release smoke and the installed greenfield matrix.
      The matrix now proves at least ten standard consumer-lane cases under
      60s with governed writes, zero quality issues, hard 10/10 scores, all
      PM/architect/engineer/domain-expert lenses passing, and every
      case-declared domain anchor present. The retained sparse-confirmation and
      quantum-communication cases must stay under 60s with no clipped terminal
      label.
      Installed CLI auto-rescue smoke must stay under the 90s rescue budget
      with rescue activated and `post_confirm_rescue_probe` repaired; this
      remains wiring proof only, not natural rescue-quality proof.
- [x] Decomposed the installed release matrix after adding the sparse and
      quantum cases pushed the runner past the source-size threshold. The
      runner now owns install, timing, artifact collection, scoring, cleanup,
      and rescue smoke; `greenfield_post_confirm_matrix_cases.py` owns only the
      high-variance case catalog. The runner is back under the hard threshold,
      and install-matrix unit proof passed.
- [x] Closed the release-gate custody miss found by independent review: the
      shared release proof lane now runs `greenfield_post_confirm_matrix.py`
      after local release smoke, persists
      `greenfield-post-confirm-matrix.v1.json` in the dist directory, and fails
      release-candidate/preflight proof if the installed matrix fails. The
      matrix payload now labels standard-path proof separately from the
      synthetic typed rescue probe so release reporting cannot imply natural
      rescue quality from wiring-only evidence.
- [x] Expanded the default installed standard matrix from eight to twelve
      domains by adding credit-union fair-lending exceptions, apprenticeship
      credential readiness, film archive rights clearance, and developer
      incident runbook readiness to the existing civic, health, lab, logistics,
      security, sparse-confirmation, and quantum cases. A c6286f0a package
      replay passed all twelve standard cases in 19.834-22.057s with zero
      issues and hard 10/10 scores; final proof still needs a rebuilt dist from
      the post-fix commit because the release-gate and strict-score metadata are
      source changes.
- [x] Closed the standalone proof-evidence gap and two broader release
      blockers exposed by the full install suite. `make
      greenfield-post-confirm-matrix` now writes
      `greenfield-post-confirm-matrix.v1.json` by default, matching canonical
      release proof. The same pass repaired guidance-budget regressions in
      always-loaded AGENTS/Claude/install guidance without dropping the
      greenfield no-source/no-hand-authored-JSON contract, and fixed
      migration-runtime scenario ordering so missing verification blocks before
      already-current no-op while verified same-version reinstall remains
      cheap. Proof passed: focused release/matrix tests (`62 passed`), full
      install suite (`383 passed`), and mirror/guidance runtime slice
      (`100 passed`). Final proof still needs a rebuilt dist from the
      post-fix commit plus local release smoke and the twelve-case installed
      matrix against that exact dist.
- [x] Hardened the generated-surface proof after brutal review found that the
      first tightened matrix still under-proved release readiness. Greenfield
      post-confirm now refreshes Casebook alongside Radar, Registry, Atlas,
      Compass, and the tooling shell; local release smoke and matrix static
      health checks require Casebook HTML, app, payload, shell tab, shell
      frame, and shell payload hrefs. Static surface health now rejects stale
      asset subpaths and malformed tooling-payload globals instead of only
      matching script basenames. The browser proof lane moved from a separate
      single generated repo to a per-case matrix option, and the maintained
      `greenfield-post-confirm-matrix` plus shared release-candidate proof
      wrappers request that browser lane by default. Project tab
      implementation prompts now include the accepted first-path contract
      directly so the operator-visible prompt cannot pass by workstream-title
      overlap alone. Focused proof passed 23 checks covering matrix scoring,
      release-wrapper wiring, stale surface detection, browser fail-closed
      behavior, and first-path prompt fidelity. Final release proof still
      requires a rebuilt dist and an environment with Playwright available so
      the per-case browser lane can run rather than fail closed as unavailable.
- [x] Closed the next browser-proof overclaim before accepting the rebuilt
      dist. Independent review found the renamed state proof still treated
      Atlas as a heading-only route check and allowed persisted matrix JSON to
      mark browser proof passed for cases where post-confirm create failed
      before browser proof ran. The release proof now checks Atlas generated
      state in browser: generated diagram buttons, stat count, active diagram
      ID, selected title, loaded generated SVG/PNG asset, and invalid diagram
      recovery. Browser-proof summary moved to a dedicated owner that marks
      requested-but-unattempted browser proof as skipped and failed. Focused
      proof passed 24 checks, the live source browser proof reported zero
      issues, and the matrix runner stayed below the 1200-line hard guard after
      extraction. Final release proof still requires a rebuilt dist and full
      installed matrix rerun against this checkpoint.
- [x] Rebuilt and proved the local release dist after the Atlas-state proof
      fix. Dist `odylith-local-release-0.1.15-atlas-state-proof` passed the
      twelve-case installed post-confirm matrix with per-case generated browser
      state proof. All standard cases scored 10/10 with zero issues, every
      browser proof was attempted and passed, create timings were
      20.660-23.125s with a 21.439s average, rendered surface counts were
      stable at six surfaces, twelve payload assets, and twelve Atlas rendered
      assets, matrix-owned temp directories were empty after cleanup, and the
      proof JSON was persisted into the dist as
      `greenfield-post-confirm-matrix.v1.json`. The installed auto-rescue smoke
      passed in 27.280s and remains explicitly synthetic wiring-only evidence.
- [ ] Remaining full-rescue release blocker: the installed auto-rescue smoke still proves
      rescue wiring through an exact internal probe, not a naturally occurring
      repairable package or semantic failure. Do not claim full release
      readiness until either a public non-internal rescue scenario passes under
      the 90s tier with host-structured patch evidence, or release reporting is
      changed to classify the current probe as wiring-only rather than rescue
      quality proof.
- [x] Project implementation prompt release-quality blocker: a fresh twelve-domain
      installed audit against dist `odylith-local-release-0.1.15-atlas-state-proof`
      wrote governed records for every case under 60s, but the package-manager
      supply-chain exception desk case exposed a false 10/10. Source-launch
      prompts included malformed semantic projection (`supplying chain exception
      desk user receives vulnerable dependency reports` and `tracking provenance
      and building evidence`) while the Project prompt checker reported no
      issues and the matrix awarded `implementation_prompts=10`. Repair must be
      generic: render prompt proof clauses from typed first-path actions or
      other semantic facts instead of gerundized validation prose, harden
      prompt-quality checks across prompt/result text, and make release score
      explanations auditable enough that a 10/10 claim is not a row-count
      assertion.
      Source checkpoint now renders proof clauses from first-path base actions,
      preserves title-cased product names without leaking mixed `package
      Manager` casing, lowers ordinary result fragments such as `release
      readiness`, rejects gerundized actor/product-subject drift inside bounded
      proof-action segments, and emits concrete score evidence for 10/10
      matrix cases. Focused proof passed 9 tests, and a disposable
      source-local package-manager replay completed post-confirm create,
      produced five Project prompts with no bad phrases, reported zero prompt
      quality issues, preserved `track provenance and build evidence`, and
      deleted the temp repo. A broader affected runtime pack then caught and
      forced a correction to an over-broad whole-prompt grammar scan plus a
      `receive a user updates...` outcome-composition defect; after narrowing
      the guard to bounded proof-action segments and dropping actor-action
      outcome phrases from receive/return composition, the full affected
      greenfield artifact/prewrite/quality pack passed 132 tests in 788.25s.
      The package-manager source replay was rerun after the correction and
      stayed clean with temp cleanup. Independent review then found that the
      first semantic proof fix still fell back to gerundized validation prose
      for single-action first paths and that the temporary `-ing` chain guard
      falsely rejected valid noun-heavy domain phrases. The source fix now
      treats one-action first paths as valid proof facts, phrases proof results
      as `evidence that the accepted path can...`, removes the suffix-count
      guard, and pins the false negative plus false positive in focused tests.
      Rebuilt installed proof is complete for the standard path: dist
      `odylith-local-release-0.1.15-prompt-quality-proof` passed the maintained
      thirteen-case installed matrix with the package supply-chain regression
      retained, every standard case scoring 10/10, zero prompt findings, zero
      total issues, all browser proofs attempted and passed, all expert lenses
      passing, create times of 20.666-23.468s, and clean matrix temp roots.
      The included rescue smoke passed in 27.399s and remains synthetic
      wiring-only rather than natural rescue-quality proof.
- [x] Closed a SemanticModelIR visible-result ownership gap exposed by a
      hostile source-local confirmed intent using `record` as both noun and
      verb. The semantic parser selected `Recorded readiness` as the visible
      result, but no first-path event was marked as the visible-result owner
      once the event list already contained three rows, so post-confirm failed
      before governed writes. The source fix attaches the selected visible
      result to the terminal event when no event owns it, keeping the repair in
      semantic-model construction instead of rendered prose, issue-message
      classification, or domain-specific wording. Focused proof passed 28
      semantic/repetition/patch-planner tests in 0.52s. The retained
      record-as-noun/verb replay now commits governed records in 15.53s with a
      standard passed manifest, zero final issues, no rescue, and temp cleanup;
      a hostile Review Status Board replay also completed standard create after
      one safe generated-copy cleanup pass. This improves the standard path
      but does not close the remaining natural rescue proof blocker.
- [x] Fixed the next hostile source-local matrix failure without weakening the
      final gate. Seven of eight cases passed, but water-rights hearing
      evidence failed before writes after auto-escalating to rescue; the
      PatchSet had empty replacement facts and the engine stopped with
      `no_progress`. Diagnosis found two generic owners, not a project defect:
      readiness/status result objects were phrased as `reach ... readiness`,
      and generated-copy tokenization treated title-label words and hyphenated
      noun compounds (`Water Use Claim`, `water-use claim`) as action verbs
      near result/status words. The fix adds token metadata for hyphen and
      title-label context in the copy gate and projects readiness/status-like
      visible results as see-style actions. Focused regressions pin the false
      positive and true positive, and the retained water-rights replay now
      commits governed records in 15.681s with a standard passed manifest, zero
      issues, all four expert lenses passing, and temp cleanup. This again
      improves standard-path quality; natural rescue remains unproven.
- [ ] Current release-quality regression: a 2026-06-28 source-local retained
      battery-materials readiness create failed before governed writes in 24s
      on clipped Project Brief preview copy ending in `or`, and the widened
      greenfield quality pack failed 14 tests while passing 284. The known
      actor-led modal/gerund escape now has focused proof, but the new shared
      prose-shape guard is too broad in evidence/review component contexts and
      list-comma regressions remain. Next fix must keep the detector
      domain-neutral while adding semantic context: corrupted actor-led
      capability/proof text should fail closed, but legitimate component
      phrases such as evidence extraction, review assignment, and publication
      record responsibilities must not be treated as actor-role corruption.
      Release scoring is capped to non-release-ready until a fresh live
      post-confirm create passes under 60s, the broad greenfield quality pack
      is green, and artifact readback confirms no clipped copy, modal drift,
      gerundized actor-role splice, or Project prompt corruption.
- [ ] Follow-up 2026-06-28 proof after shared actor-prefix, first-path list,
      and prose-shape segmentation fixes: the targeted subset passed 8 tests
      and the broader affected greenfield pack passed 284 tests in 338.06s.
      The first live source-local matrix remains red under the brutal release
      scorer. Battery materials failed before writes in 26.096s on
      `modal/base-form grammar drift leaked at proposal.risks.1.statement`.
      Public records, solar assessment, structured review, and cooking robot
      wrote governed records in 24.761-28.957s with expert manifest lenses
      passing, but release scoring failed because rendered Atlas/surface
      custody was incomplete: missing `odylith/atlas/atlas.html`, missing
      SVG/PNG diagram renders, 5/6 rendered surfaces, 10/12 surface payloads,
      and 0 Atlas rendered assets. Every temp repo and the matrix root were
      deleted. Next repair targets are risk-statement semantic/projection
      grammar and post-confirm rendered Atlas/surface custody; do not weaken
      the scorer or reintroduce rendered-prose repair.
- [x] Follow-up 2026-06-28 source-local standard-path proof after the
      Product Intent renderer, sequence-step, modal-actor, repetition, and
      exact-path artifact-draft repairs. The fix keeps repair ownership in
      typed semantic/projection owners: text `greenfield propose` now emits a
      concrete Product Intent Confirmation that can be saved as the confirmed
      intent file; sequence-step ownership keeps coordinated object lists on
      the prior action and preserves plural modal actor capability chains;
      package repetition allows complete canonical semantic event custody
      without allowing sentence-shape boilerplate; Project next-step prompts
      carry the accepted first path without echoing Radar
      `recommended_first_slice`; and artifact-draft cleanup is limited to exact
      collected public-copy projection leaves after shared structural-copy
      filtering. Expanded affected proof passed 106 tests in 414.34s; the
      focused modal/live/sequence/repetition pack passed 19 tests in 190.09s.
      Six fresh source-local operator-flow projects then passed
      propose-save-confirm-create with governed writes, zero final issues,
      hard-min 10/10 scores across completion, latency, semantic manifest,
      copy/semantic clarity, governance depth, traceability, operator
      usefulness, Project implementation prompts, product-manager, architect,
      engineer, and domain-expert lenses, and temp cleanup after every case:
      hospital sterile instrument recall 23.127s, satellite thermal anomaly
      triage 23.207s, drought water-rights transfer ledger 24.639s, battery
      recycling hazmat custody 22.815s, cryptographic key ceremony readiness
      23.949s, and workplace accommodation plan review 24.279s. This restores
      source-local standard-path quality for the tested variance, but release
      readiness still requires rebuilt installed-dist matrix proof before
      closeout.
- [x] Cross-surface governance artifact learning captured for day-to-day ops.
      The durable lesson is that generated Casebook, Registry, Atlas, Compass,
      technical-plan, release-proof, and operator-prompt artifacts must be
      evaluated as governed artifact packages with source-owned facts,
      surface-local custody, readable grammar, non-repetition, traceable proof
      obligations, exact freshness state, and actionable next decisions. The
      banned mechanisms carry across every governance surface: rendered-prose
      repair, diagnostic-sentence routing, role/surface label fallback as
      projection identity, dashboard refresh without source truth freshness,
      shallow Compass claims without validation evidence, and count-based
      scoring that ignores artifact readability. Operational rule for future
      governance generation: update owned source truth first, refresh generated
      surfaces through the first-class CLI, validate source and generated
      surface contracts, and cap release/readiness claims until punitive
      multi-lens artifact-package checks pass.
- [x] Atlas architecture coverage refreshed for the latest greenfield and
      rendered-surface owners. Created D-045 for first-path semantic/copy
      custody and D-046 for rendered-surface plus static Atlas custody; updated
      D-043 to include confirmable propose stdout, first-path sequence custody,
      collected public-copy cleanup, and rendered-surface proof; updated D-040
      to show static generated-flowchart fallback in the surface DAG. Atlas
      catalog watch paths now include the extracted sequence-step, step-role,
      prose-shape, gerund-action, structural-copy, confirmed-completion helper,
      and generated-flowchart owners. Source-local Atlas auto-update rendered
      the new SVG/PNG assets through the browserless fallback after Chromium
      launch degraded, and the rendered Atlas payload verifies D-040, D-043,
      D-045, and D-046 as fresh with SVG and PNG present. Atlas render reports
      46 diagrams, 46 fresh, 0 stale.
- [ ] Release-matrix false-positive hardening after the 2026-06-28 brutal
      audit. The current matrix can still trust producer-reported
      `post_confirm_quality_manifest` lenses plus count floors too much. The
      next implementation must recompute package quality lenses from collected
      generated artifacts, fail closed when independent readback is missing or
      disagrees with the manifest, and tighten PM/Architect/Engineer lens
      evidence around explicit SemanticModelIR and prewrite artifacts rather
      than proof-boundary fallback, empty external-system keys, or absent
      program dry-run data. This is release-proof hardening, not a generated
      project repair.
- [x] 2026-06-29 source-local brutal QA follow-up for the wildfire mutual-aid
      simulation. Initial create wrote governed records in 23.170s but scored
      0/10 under independent artifact readback because generated browser proof
      found missing managed brand lockup assets and the independent engineer
      lens could not see prewrite dry-run safety evidence after final program
      commit. The platform fix seeds missing managed brand assets before
      greenfield dashboard refresh, snapshots `odylith/surfaces/brand` in the
      rollback guard, carries explicit `prewrite_safety` evidence through the
      create payload and matrix readback, and statically rejects missing local
      HTML assets. Focused proof passed 94 tests in 12.62s. The retained
      wildfire replay then passed source-local post-confirm in 23.205s with
      complete governed counts, clean surface/browser proof, all expert lenses
      passing, and hard 10/10 across all release-matrix dimensions. This is
      one high-variance source-local proof, not installed release readiness;
      broader high-variance source-local and rebuilt installed matrix proof
      remain required.
- [x] Typed projection provenance follow-up. The retained quantum installed
      matrix failure proved that flattened string allowance could reject a
      legitimate source-grounded visible-result projection across sanctioned
      surfaces. `CanonicalProjectionFact` now preserves source layer, semantic
      node ID, source path, repair owner, and allowed projection IDs through
      compact supporting-tail variants; package repetition scoring checks the
      artifact projection against those typed facts instead of blindly allowing
      accepted-intent text. The release matrix also persists failed-create
      stdout/stderr/blocker excerpts before temp cleanup, keeps passed-case
      failure evidence empty, suppresses local-server client-disconnect noise,
      and asserts matrix root removal. Focused proof passed the
      package-repetition suite (`10 passed`), installed-matrix unit suite
      (`28 passed`), local-release smoke suite (`20 passed`), retained quantum
      confirmed-create integration (`1 passed in 27.92s`), and the four rerun
      transaction tests that exposed stale refresh-stub custody (`4 passed in
      108.87s`). Fresh installed dist matrix proof passed afterward: thirteen
      high-variance standard cases scored hard 10/10 in 22.615-28.216s with
      browser proof passing for all thirteen, zero quality issues, clean temp
      cleanup, quantum passing in 27.015s, sparse intent passing at 10/10, and
      auto-rescue wiring smoke passing in 35.012s.
- [x] Closed Tribunal visible-role scoring false positives without role-label
      regex stacking. Clinical-trial and biobank source-local simulations proved
      two distinct escapes: generated judgment roles could collapse to one proof
      reviewer label, and an internal evidence system could be projected as the
      evidence owner while the release matrix still scored 10/10. The fix adds
      actor-source provenance, allows explicit accepted many-hat actors, requires
      generated role-specific judgment labels, excludes evidence objects/systems
      from visible judgment actor selection, and validates persisted
      accepted-project actor readback against the create payload. Focused
      actor/readback proof passed 6 tests, the proposal/matrix pack passed
      85 tests in 86.30s, and a fresh biobank source-local create completed in
      21.867s with complete governed counts, all expert lenses passing, and
      zero temp leftovers. A broader 121-test follow-up caught an overcorrection
      where explicit `Audit reviewer` was rewritten to `audit proof reviewer`;
      evidence-owner vocabulary now treats audit reviewer/auditor as a generic
      valid proof role while still rejecting internal evidence systems.
- [x] Closed the external-boundary semantic input gap exposed by the broad
      quality pack. Legacy host proposal bridges can no longer leave the
      architect lens with an empty external-system boundary: apply-semantic input
      now uses explicit accepted external systems, inferred first-path external
      boundary rows, or a typed deferred manual/fixture boundary. This keeps the
      repair in semantic facts instead of diagnostic text or project-specific
      wording.
- [x] Hardened source-local simulation cleanup after background Odylith runtime
      files resurrected temp roots after apparent deletion. The release smoke
      cleanup helper now retries and verifies a settled absent temp root before
      the matrix moves to the next project, preserving the recursive
      create-assess-learn-delete discipline.
- [x] Closed the HIIT Atlas label custody blocker without weakening public-copy
      gates. The retained HIIT integration failed before governed writes because
      Mermaid labels rendered visible lines ending in `with`, and the
      accepted-project preview carried compact one-line Mermaid that public-copy
      custody still had to inspect. The source fix is generic: shared Mermaid
      label wrapping now moves stranded connector words to the following visual
      line, and compact-flowchart visible-label extraction is covered so graph
      syntax and class declarations are not treated as prose. Focused proof
      passed the two Mermaid helper tests plus the HIIT integration in 20.34s;
      the wider source-local post-confirm/Tribunal pack then passed 85 tests in
      70.23s.
- [x] Completed a fresh ten-domain source-local standard-path brutal QA matrix
      after the role-provenance, repetition, external-boundary, cleanup, and
      Mermaid label custody fixes. Domains covered regulated health, lunar
      operations, cultural archive consent, autonomous rail safety, climate
      finance, special education, esports integrity, decentralized identity,
      food recall logistics, and disaster insurance. Every run saved the
      no-write propose output as confirmed intent, completed confirmed create,
      committed governed records, scored hard 10/10 across all twelve release
      dimensions, produced the expected Radar/Registry/Atlas/Compass/project/
      release/program/rendered-surface counts, reported zero quality issues,
      and deleted its repo plus the parent temp root. Create timings were
      22.072-23.827s; whole-project timings were 15.521-16.534s.
- [ ] Fix sparse-intent topology and domain-anchor obligations before release
      readiness can be claimed. Fresh installed dist
      `odylith-local-release-0.1.15-3d13f434` failed the maintained
      thirteen-case matrix after governed writes: twelve cases passed with hard
      10/10 scores, browser proof, and complete records, but sparse disclosure
      confirmation scored 0/10 in 21.474s because independent readback saw only
      two Registry specs, 17 trace nodes, three of four required domain anchors,
      and failed architect/engineer/domain-expert lenses. The prescribed fix is
      generic: sparse confirmed intents need typed semantic/artifact-plan
      obligations that derive a minimum useful topology from accepted actors,
      first path, state object, proof boundary, and systems, then carry domain
      anchors as projection obligations. Do not repair this with
      disclosure-specific terms, keyword stuffing, or regex scoring.
- [x] Release posture for the CB-209 canonical-projection/sparse-intent
      blockers is backed by a fresh installed matrix. The current working-tree
      dist `odylith-local-release-0.1.15-typed-custody-test` passed the
      maintained high-variance matrix with persisted readback proof under the
      standard and rescue time budgets. This does not end broader greenfield
      quality work; it clears the specific failure classes represented in this
      matrix.
- [x] Hardened matrix scoring against shallow 10/10 false positives without
      lowering gates. Independent release-proof review found that producer-owned
      payloads, stubbed lens reports, count floors, and position-based Project
      prompt checks could still make a package look premium without enough
      artifact readback. The fix adds independent package-evidence checks for
      project brief, Radar, Registry, Atlas, prewrite-safety, Project prompts,
      and domain carry-through; generated-copy inspection now walks typed
      `ArtifactQualityUnit` leaves so metadata, commands, Mermaid labels,
      prompt fields, semantic facts, and free prose keep separate custody; and
      source-launch prompts carry stable `step_id` values. Focused proof passed
      49 tests in 1.97s, the broad affected pack passed 228 tests in 579.08s
      after decomposition, and the earlier six-domain installed adversarial run
      remains pre-hardening evidence rather than release closure. A rebuilt dist
      matrix under the hardened scorer is still required before release-ready
      claims.
- [x] Captured and fixed the first hardened-scorer installed proof defect
      before claiming release readiness. Fresh dist
      `odylith-local-release-0.1.15-def2f783` completed all thirteen standard
      confirmed creates in 22.566-27.824s and passed synthetic rescue smoke in
      34.916s, but every standard case scored 0/10 because release-matrix
      readback treated `odylith/radar/source/CLAUDE.md` as a generated Radar
      workstream. The failed mechanism is a custody-boundary error in the proof
      harness: broad folder/suffix collection excluded `AGENTS.md` but not the
      cross-host `CLAUDE.md` companion, so host guidance polluted generated
      artifact scoring. The fix centralizes non-artifact Markdown exclusion for
      `AGENTS.md`, `CLAUDE.md`, `INDEX.md`, and `README.md`, and the regression
      proves guidance files neither become Radar workstreams nor inflate domain
      term coverage. Focused release-matrix proof passed 31 tests; a fresh dist
      and installed matrix rerun are still required for release closure.
- [x] Fresh installed proof after the guidance-readback custody fix is green.
      Local release dist `odylith-local-release-0.1.15-e1dd08d6` passed the
      maintained installed matrix under the hardened scorer. All thirteen
      standard real consumer-lane creates scored hard 10/10 with zero issues,
      per-case generated browser-state proof, and strict temp cleanup. Standard
      create timings were 22.581-27.010s; every case produced complete
      Radar/Registry/Atlas/project/release/program/rendered-surface/trace
      evidence and passed PM, architect, engineer, and domain-expert lenses.
      Synthetic rescue wiring smoke passed in 34.942s. Natural rescue quality
      remains a separate proof obligation because the rescue lane in this
      matrix is synthetic typed-probe wiring, not an organically triggered
      host-model semantic repair.
- [x] Fixed the latest installed matrix escape in source before any release-ready
      claim.
      A fresh non-reused high-variance installed matrix against final local dist
      `odylith-local-release-0.1.15-a0dae6b7` passed eleven standard cases with
      hard 10/10 scores, zero quality issues, browser proof, complete
      governance counts, and create timings of 24.065-26.756s across regulated,
      operational, legal, scientific, cultural, environmental, financial, and
      technical domains. The twelfth ambiguous broad prompt, `model lab
      notebook`, failed before governed writes in 24.549s because the project
      brief preview and operator next steps repeated adjacent words as
      `teams Teams`; no Radar, Registry, Atlas, release/program, traceability,
      or Project implementation prompt records were written. Synthetic rescue
      smoke still passed in 35.170s, and temp cleanup left no
      `odylith-greenfield-*` directories under `/Users/freedom/mock`. Failed
      mechanism: broad prompts whose accepted title or actor phrase begins with
      the same semantic head as an actor/object can duplicate that head across
      surface composition boundaries. Fix this in semantic title, actor, and
      projection composition custody without domain-specific vocabulary,
      domain-term stuffing, weakened repetition gates, or rendered-string
      patching.
      Source fix: finite action leads such as `records`, `sees`, `reviews`, and
      `launches` now stay actorless action fragments during sparse intent
      recovery; project-brief actor-choice copy uses neutral participant wording
      instead of echoing people/team categories; and the operator next-step
      overlap gate compares against sanctioned first-path projection fields
      instead of flattened contract metadata, persistence, and deferred-scope
      prose. Focused regressions passed 6 selected tests in 36.44s, and a
      source-local CLI create for `model lab notebook` completed in 19.708s with
      governed writes, 4 Radar records, 3 Registry specs, 6 Atlas diagrams,
      project records, and temp cleanup.
      Follow-up proof moved the new sparse regressions into the dedicated
      90-line `test_greenfield_sparse_recovery_regressions.py` module instead
      of growing the pre-existing oversized slop-regression file. The sparse
      tests passed, the focused next-step/slop checks passed, the full
      live-simulation regression file passed 14 tests in 188.05s, and a fresh
      source-local CLI create for `model lab notebook` completed in 19.232s.
      The final post-confirm manifest stayed on the standard 60s tier,
      completed its fixpoint pass in 5.149s, reported zero issues, passed the
      validation gate, wrote 4 Radar workstreams, rendered 3 Registry specs,
      rendered 6 Atlas sources, and produced project-brief and
      operator-next-step previews. The temp repo was deleted after proof.
- [x] Rebuilt the installable dist and reran the high-variance installed matrix
      after the `model lab notebook` source fix; the rerun exposed a new
      release-blocking semantic projection custody failure instead of release
      readiness. Dist `odylith-local-release-0.1.15-e7bc3be3` passed twelve of
      thirteen standard installed cases at hard 10/10 and under 28s, while
      `security disclosure council` failed before governed writes in 12.96s on
      repeated object-list tail prose. Synthetic rescue smoke passed in
      34.393s and temp matrix dirs were cleaned.
- [x] Fixed action-complement and object-list canonical projection custody in
      source before the next release-readiness claim.
      `greenfield_canonical_projection_facts.py` now derives compact
      action-complement/object-list projection variants from typed
      `first_path_contract.action` and event actions, preserving fact identity,
      semantic source, projection id, repair owner, and sanctioned surface roles
      instead of weakening the package repetition gate. Focused package
      repetition proof passed, and the maintained `security disclosure council`
      live simulation now reports zero package issues.
- [x] Captured the follow-up Project Brief clipped-readiness quality miss before
      rebuilding the dist.
      A real source-local create for `security disclosure council` completed in
      22.633s with governed writes, 4 Radar records, 3 Registry specs, 6 Atlas
      sources, release/program records, and backlog-contract validation passing,
      but persisted `project-brief.v1.md` still contained a coding-readiness
      gate ending `external vulnerability reports, affected.`. The brief owner
      now treats clipped-prefix summaries as incomplete unless they end on a
      sentence-safe or comma-list-safe boundary, and drops orphaned comma-list
      tails before adding terminal punctuation. Focused Project Brief proof
      passed 12 tests including the retained security-disclosure prompt.
- [x] Rerun source-local CLI create for `security disclosure council`, assert the
      persisted Project Brief has no clipped readiness gate, delete the temp
      repo, then rebuild the installable dist and rerun the installed
      thirteen-case matrix plus synthetic rescue smoke. Do not claim release
      readiness until installed proof is green with complete governed writes,
      hard 10/10 standard scores, browser proof, zero quality issues, and temp
      cleanup.
      Completed proof on 2026-06-29: source-local `security disclosure council`
      replay completed governed writes in 22.5006s after the brief clipping fix
      and persisted no `reports, affected.` readiness tail. Fresh local release
      dist `odylith-local-release-0.1.15-13b796e9` passed local release smoke
      and the maintained thirteen-case installed matrix with browser proof for
      every generated repo. Standard creates finished in 22.477-26.930s, every
      case wrote complete Radar, Registry, Atlas, Project Brief, release,
      program, rendered-surface, traceability, and Project implementation
      prompt evidence, every hard matrix dimension scored 10/10, all PM,
      architect, engineer, and domain-expert lenses passed, and the matrix temp
      root was cleaned. Synthetic rescue wiring smoke passed in 34.261s; natural
      host-model semantic rescue quality remains a separate proof obligation
      because this proof uses a typed rescue probe rather than an organically
      triggered model repair.
- [ ] Fresh recursive installed variance pass reopened release readiness after
      the `13b796e9` proof.
      Ten non-reused installed consumer-lane simulations against
      `odylith-local-release-0.1.15-13b796e9` produced seven passes and three
      failures while cleaning the matrix temp root. `lead service line
      replacement equity` wrote governed records in 24.809s but failed domain
      readback with only three of four required anchors. `space telescope
      calibration anomaly` failed before governed writes in 34.656s because
      proposal summary, validation, release gate, and promotion criteria text
      tripped the semantic-slop gate for actor-led finite action inside
      user-can clauses. `carbon removal mrv attestation` wrote records in
      23.131s but produced only two Registry component specs, failing architect
      and engineer lenses. Independent review also found remaining proof
      false-positive risks: domain expertise can still be credited from
      runtime/accepted-project JSON, operator usefulness can be inflated by
      custody files counted as project brief records, count-only dimensions are
      partly duplicated, and the Python matrix entrypoint can pass when browser
      proof is skipped. Fix the platform and proof harness generally, then
      rerun fresh non-reused installed simulations under the hardened scorer
      before any release-ready claim.
- [x] Source-fixed the 2026-06-29 `decision evidence room` installed failure
      without domain vocabulary or rendered-prose repair.
      The failure was generic first-path subject-boundary and event-split
      custody: `Multiple teams bring requests` was misread as actor phrase
      `Multiple teams bring`, then sibling actions rendered as `Multiple teams
      bring decides...`; a separate civic first-path case showed
      `groups public comments` being absorbed into the prior `reads...`
      semantic event. The source fix keeps plural actor heads separate from
      trailing unowned action tails, adds only general action morphology for
      `bring/brings` and `group/groups`, and stops sparse system completion
      from synthesizing a proof ledger when two explicit internal systems are
      already accepted. Targeted proof passed 13 tests in 78.18s, the broader
      greenfield pack passed 201 tests in 242.43s, compile proof passed for
      the touched runtime modules, and an exact source-local propose plus
      confirmed-create replay completed in about 21 seconds with zero manifest
      issues, 4 Radar workstreams, 3 Registry specs, 6 Atlas diagrams, rendered
      SVG/PNG assets, accepted-project truth, and verified temp cleanup.
- [x] Source-fixed the follow-up sparse-topology installed proof failure from
      the `f5fef9e6` dist without weakening gates.
      The maintained matrix passed twelve standard cases but failed sparse
      disclosure confirmation at 0/10 because readback saw only two Registry
      specs and 17 trace nodes. The failed mechanism was the earlier broad
      `len(rows) < 2` guard: it protected rich explicit two-system intents, but
      it also suppressed generic state/proof topology completion for terse or
      generated two-row intents. The source fix adds sparse-row detection for
      empty, terse, and generated fallback rows, preserves rich explicit
      two-system narratives unpadded, and removes compiler-only `Relevant
      behavior` / `Rationale` labels from public Registry system descriptions.
      Focused sparse/confirmed-intent proof passed 3 tests in 13.41s, the
      broad affected greenfield pack passed 202 tests in 250.95s, and compile
      proof passed for the touched runtime modules.
- [x] Rebuild the installable dist from the current source and rerun installed
      maintained plus adversarial high-variance simulations.
      Do not claim release readiness from the source-local proof alone. The
      rebuilt installed proof must show complete governed writes, hard 10/10
      scores, browser proof, zero final quality issues, strict temp cleanup,
      and standard-path latency under 60s for normal cases.
      Completed on 2026-06-29 with dist
      `odylith-local-release-0.1.15-db69b062`: all thirteen maintained
      standard cases passed with hard 10/10 scores, zero issues, browser proof,
      complete governed readback, and standard create times of 21.927-26.698s.
      Synthetic rescue wiring passed in 32.728s. This closes the sparse
      topology checkpoint; the broader goal continues to require fresh
      high-variance simulations and natural rescue-quality proof for new
      failure classes.
- [x] Source-fixed the focused workstream-title preservation regression found
      by independent review.
      `test_workstream_titles_compact_while_keeping_clauses` was red because
      first-path fragmentation separated an accepted `while keeping ...`
      preservation constraint from the selected workflow-title action. The
      source fix recovers useful preservation constraints from the full first
      path, attaches them to a compact action head before final title
      projection, and avoids domain vocabulary, post-render repair, or a new
      regex parser. Focused proof passed
      `tests/unit/runtime/test_greenfield_post_confirm_quality_repairs.py` and
      `tests/unit/runtime/test_greenfield_confirmed_backlog_terms.py` together:
      44/44.
- [x] Rebuild the installable dist after the workstream-title source fix and
      rerun installed maintained plus fresh non-reused high-variance proof.
      Completed on 2026-06-29 with dist
      `odylith-local-release-0.1.15-a46ef6cc`. The local release build and
      matrix start both passed the platform domain-leakage guard across 19
      distinctive fixture terms. The maintained installed matrix passed 13/13
      standard cases with hard 10/10 scores, zero issues, browser proof for
      every case, complete governed readback, 21.980-26.653s standard create
      timings, clean temp cleanup, and synthetic typed-probe rescue wiring at
      32.990s. Fresh non-reused installed variance then passed 10/10 domains
      with hard 10/10 scores, zero issues, browser proof for every case,
      24.258-26.624s create timings, and clean temp cleanup. Natural
      host-model semantic rescue quality remains a separate unclaimed proof
      class.
- [x] Harden selected-case leakage custody for recursive custom simulations.
      The previous release wrapper proved the maintained matrix terms, but
      direct `run_matrix(...)` calls used by fresh variance passes did not
      propagate their selected case vocabulary into the platform leakage scan.
      Independent review then found the first pass still too weak because
      required-term-only mining left some cases with zero or thin distinctive
      coverage. `platform_domain_leakage_check.py` now accepts explicit
      per-case `leakage_terms`, falls back to required terms only for custom
      cases that still produce distinctive coverage, filters standalone generic
      product/platform-native words, and exposes a shared source/dist custody
      scan. `greenfield_post_confirm_matrix.py` requires every selected case to
      contribute at least one distinctive leakage term before serving the dist
      or creating temp repos. Focused proof passed 50 install/bootstrap tests,
      py_compile, a selected explicit platform-word phrase scan, and the
      current `a46ef6cc` source/dist scan over 44 explicit terms with zero
      missing cases and zero findings.
- [x] Broaden platform domain-leakage release custody beyond selected matrix terms.
      A follow-up custody audit found no actual project-domain leakage, but
      found the standalone guard too narrow for a release claim because it did
      not scan root `.codex`, public `docs/`, historical escaped-domain
      sentinels, or Odylith payloads inside runtime tarballs. The guard now
      keeps historical project vocabulary only as release-proof sentinels,
      scans source `.codex` and `docs`, recurses into runtime tarballs for
      Odylith launchers/runtime/guidance while skipping third-party packages
      and governed evidence, and caches per-line tokens so archive proof stays
      bounded. Focused proof passed 52 install tests, and source plus dist
      `odylith-local-release-0.1.15-cd6cf643` passed the strengthened leakage
      check across 49 distinctive fixture terms with zero protected-custody
      findings. Fresh local release dist
      `odylith-local-release-0.1.15-14f5102a` rebuilt after the committed guard
      hardening and passed the same 49-term platform leakage build gate.
- [x] Remove broad rendered-preview package repair authority.
      Safe artifact-draft cleanup now requires exact source-owned leaf paths
      from the shared ArtifactPlanIR contract. The repair executor no longer
      walks whole project brief, operator next-step, accepted-project,
      project-dashboard, or Compass preview trees; it repairs only the named
      scalar leaf, preserving structural metadata and sibling copy. Legacy
      generated-copy findings no longer emit broad safe-repair targets when
      exact package findings exist, and broad completion-level generated-copy
      findings route to plan/projection ownership rather than
      `artifact_draft_cleaner`. Focused proof passed 41 artifact-plan and
      quality-repair tests, the widened post-confirm engine/projection group
      passed 76 tests in 50.17s, compile proof passed for the changed modules,
      and independent review verified exact Compass memory repair plus
      suppression of stale broad `next_steps` safe-repair paths.
- [x] Remove generic no-op semantic PatchSet rescue operations.
      A rescue audit found that generic reviewer-lens or `SemanticModelIR`
      roots could still be marked `semantic_patch`, converted to a generic
      `semantic_fact` operation, and then no-op in the semantic executor
      because no supported IR slot was named. The source fix makes PatchSet
      emission fail closed unless a semantic finding targets an executable slot
      such as first path, proof boundary, state object, human actors, or
      system boundaries, and makes auto-rescue require a non-empty PatchSet
      before switching from the 60s standard tier to the 90s rescue tier.
      Focused proof passed the post-confirm engine, patch payload, semantic
      executor, quality repair, artifact-plan patch, and projection rerender
      suite: 97 tests in 46.13s. Natural host-model rescue quality remains an
      explicit unclaimed proof class until a non-internal provider-authored
      rescue scenario is proven end to end.
- [x] Tighten source-level domain-custody proof after the release guard missed
      hardcoded example nouns in generic runtime helpers.
      The guard now treats the historical example nouns as forbidden protected
      source-custody sentinels, while test fixtures and release matrix cases
      remain allowed proof sources. Generic visible-result and backlog helpers no
      longer depend on those nouns, component-kind classification no longer lets
      adjacent external dependency vocabulary demote an accepted internal system
      to an adapter, and sequence-step capitalization now uses the shared
      greenfield text owner. Proof passed the 52-term platform domain-leakage
      guard, py_compile for the touched modules, and 78 focused
      greenfield/matrix/component tests. A fresh 12-domain installed variance
      pass against the prior dist still passed 12/12 with hard 10/10 scores,
      browser proof, zero issues, max create time 28.819s, and clean temp
      cleanup; final shipped-custody proof still requires a rebuilt dist from
      this source checkpoint.
- [x] Prove the `9a764dc7` rebuilt dist and remove unconditional status-profile
      notification copy from generic Registry contracts.
      The installed maintained matrix at
      `odylith-local-release-0.1.15-9a764dc7/greenfield-post-confirm-matrix-20260630-9a764dc7.v1.json`
      passed 13/13 standard cases with hard 10/10 scores, zero issues, browser
      proof, complete governed records, 22.259-29.208s standard create timings,
      synthetic typed-probe rescue wiring in 33.474s, and clean temp cleanup.
      Follow-up source audit found that status-view Registry profiles still
      injected notification semantics without accepted-intent ownership. The
      profile now emits source freshness/source event/downstream action language
      instead. Focused proof passed 39 component-spec tests, 3 explicit
      notification/intent regression tests, the 52-term platform leakage guard,
      and exact-string scan for the removed phrases. Fresh local release dist
      `odylith-local-release-0.1.15-3c616936` then passed the platform
      domain-leakage build gate across the same 52 distinctive fixture terms.
- [x] Close the greenfield release-proof custody gap for Project artifacts.
      A proof audit found that the installed matrix still rebuilt the Project
      dashboard inside the proof harness, so Project implementation prompt
      counts, prompt quality, and domain-term readback could pass even if the
      generated shell payload was stale or divergent. The fix makes
      `collect_artifact_package` read `odylith/tooling-payload.v1.js`,
      strengthens persisted project-brief Markdown readback, adds real Project
      shell-pane browser proof for accepted state and five implementation
      prompt cards, and records per-case generated-domain terms that are then
      rescanned against protected source/dist custody. Focused proof passed 64
      matrix/browser/leakage unit tests, 2 Project browser integration tests,
      py_compile, and a real installed flood-shelter post-confirm run with
      browser proof in 26.754s, hard 10/10 score, four generated leakage terms
      checked, zero leakage findings, and clean temp cleanup.
- [x] Rebuild the installable dist from the Project proof-custody checkpoint
      and rerun the full maintained installed matrix with browser proof plus
      rescue smoke.
      Fresh local release dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-aebe9245`
      rebuilt from committed checkpoint `aebe9245` and passed the maintained
      installed matrix at
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-aebe9245/greenfield-post-confirm-matrix-20260630-aebe9245.v1.json`.
      The proof shows 13/13 maintained standard cases passed, every case scored
      hard 10/10, standard create times were 22.338-28.973s with a 25.949s
      average, per-case browser proof was attempted and passed, Project prompt
      readback came from the persisted tooling payload, generated-term leakage
      proof passed across 55 generated readback terms with zero findings,
      synthetic auto-rescue smoke passed in 33.617s under the 90s rescue budget,
      and temp matrix/rescue cleanup was clean.
- [ ] Close the fresh variance failure found after the Project proof-custody
      checkpoint.
      A fresh ten-domain installed variance run against current checkpoint
      `25b8f9cf` failed release readiness even though temp cleanup completed.
      The leakage proof overreached by rescanning ordinary required
      domain-coverage anchors as platform leakage sentinels, causing false
      failures on platform-native words such as `artifact`, `protocol`,
      `sample`, `interpreter`, `verifier`, and `consent`. Separately, the
      satellite/orbital case failed before governed writes because prompt-intent
      recovery dropped a direct product title and converted an actor-led gerund
      path into generic representative-user review prose. The source fix must
      keep leakage custody phrase-first and declared-sentinel based, preserve
      direct product-container titles such as `coordination`, and normalize
      actor-led gerund action lists before generic first-path fallback. Current
      source proof: 60 leakage/matrix tests passed, 66 recovery/post-confirm
      tests passed, the broader affected 266-test pack passed after generic
      confirmed/approved outcome-title selection preserved outcome workstreams
      without adding domain-object vocabulary, and a disposable source-local
      satellite replay completed governed create in 24.522s with 4 Radar
      workstreams, 3 Registry specs, 6 Atlas sources, and clean debug-repo
      deletion. Remaining proof: rebuild the installable dist from this source
      checkpoint and rerun the fresh high-variance installed matrix with
      browser proof, generated-term leakage proof, hard 10/10 scores, sub-60s
      standard creates, and clean temp cleanup.
- [ ] Close the grounded-anchor and purpose-context custody gap found after
      the `8495f96a` rebuilt proof.
      The rebuilt fresh variance matrix wrote complete governed records for
      every case and kept standard create times under 29s, but failed three
      domain-expert checks. Two failures came from ungrounded release-case
      anchors that were not present in the accepted prompt; the release harness
      now rejects such impossible `required_terms` before installing temp
      repos. The real generation failure was accepted purpose context before a
      semicolon being dropped from first-path projections, so `lead
      service-line abatement; intake...` lost `abatement` even though the
      operator supplied it. The source fix carries semicolon-led purpose
      context into the first actionable step, preserves ordinary sentence
      context dropping, and keeps leakage proof as declared sentinels plus
      filtered distinctive generated anchors rather than broad required-term
      scanning. A read-only review then found that exact-token grounding made
      the default matrix self-invalidating on singular/plural drift; the
      harness now accepts simple token inflection variants and regression-tests
      the real default catalog before simulation. The purpose-context handler
      moved into its own first-path owner module after the broader suite caught
      the parser crossing the 800-line guard. Current source proof: focused
      install/leakage/recovery tests passed, the first-path file-size guard
      passed, py_compile passed, the 65-term platform source/dist leakage scan
      passed, and a disposable source-local municipal replay preserved `lead`,
      `water`, `abatement`, and `sample` in governed records with clean temp
      cleanup. Remaining proof: rebuild the installable dist from this source
      checkpoint and rerun corrected fresh high-variance installed matrix proof
      with browser checks, generated-term leakage proof, hard 10/10 scores,
      sub-60s standard creates, and clean temp cleanup.
- [ ] Rebuild and prove the post-cdee30ee leakage/actor-risk/profile-boundary
      checkpoint.
      Source proof after the `cdee30ee` custom variance audit found no
      protected platform leakage across 45 generated readback terms, but one
      high-variance project still failed before governed writes because
      product risk prose began with generic `Operator`. The source fix keeps
      the actor gate strict and localizes top-level product risk statements and
      mitigations through accepted actor semantics. The same proof pass
      separated release-matrix leakage sentinels from required domain coverage
      anchors and fixed Registry component-profile custody so profile
      selection uses component-local context, notification/deadline services do
      not inherit status/dashboard semantics by label alone, and true
      status-view contracts still receive accepted state/path/proof transitions.
      Current source proof: 68 focused leakage/matrix/actor/component tests
      passed and the broader affected greenfield/component suite passed 325
      tests in 409.12s. Remaining proof: commit the checkpoint, rebuild the
      installable dist, rerun the maintained installed matrix and fresh
      non-reused variance matrix with browser proof, generated-term leakage
      proof, hard 10/10 scores, sub-60s standard creates, and clean temp
      cleanup.
- [x] Rebuild and prove the post-7cf9d2ed leakage-baseline harness checkpoint.
      The `7cf9d2ed` dist passed the 65-term platform domain-leakage build
      gate, but the maintained installed matrix stalled after the first
      disposable case because generated-readback required-anchor suppression
      rescanned protected source and runtime tarball custody once per term.
      Follow-up review found two more proof gaps: release scripts were outside
      protected source custody, and phrase matching could miss wrapped
      multi-line phrases plus camelCase or compacted identifier leaks. Source
      now moves intentional fixture vocabulary into the excluded matrix fixture
      catalog, includes `scripts/release` in the guarded source surface,
      tokenizes documents across line boundaries with identifier case
      splitting, detects compacted phrase tokens, computes platform-native
      required anchors once for selected matrix vocabulary, and caches the
      tokenized source/dist corpus so repeated matrix scans stay bounded.
      Focused install/leakage proof passed 71 tests, and cold/warm source+dist
      leakage timing against the `7cf9d2ed` dist was 28.228s, 0.062s, and
      0.809s. Rebuilt installable dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-2ab8793f`
      passed the 65-term platform domain-leakage build gate and persisted the
      maintained installed matrix at
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-2ab8793f/greenfield-post-confirm-matrix-20260630-2ab8793f.v1.json`.
      The matrix passed 13/13 maintained standard cases with hard 10/10 scores,
      zero quality/browser/platform-leakage issues, generated-readback
      protected-custody proof across 54 terms, create timings of
      22.856-29.056s, synthetic typed-probe rescue in 34.430s, and clean
      matrix/rescue/debug/source temp cleanup.
- [ ] Rebuild and prove the source-text leakage and token-aware coverage
      checkpoint.
      A post-proof review found that platform leakage proof still depended too
      much on manually curated case sentinels: a partial `leakage_terms`
      declaration could hide omitted prompt vocabulary. The same review found
      that release-matrix domain coverage still used raw substring containment,
      allowing false positives such as `port` inside unrelated words. The first
      source-text derivation attempt overcorrected and treated generic
      governance phrases from prompts and confirmed intents as project-domain
      sentinels, producing false positives such as `verification evidence`,
      `owner reviews`, and `question is`. Current source fix keeps explicit
      declared leakage terms, supplements them with required anchors and
      conservative multi-token source-text phrases that contain distinctive
      project vocabulary, and switches domain coverage scoring to the shared
      token-aware matcher. Source proof passed 73 focused leakage/matrix tests,
      the full install unit suite passed 448 tests, the strengthened
      source/dist leakage guard passed across 387 derived fixture terms against
      the `88df22be` dist, and the pre-fix `88df22be` maintained installed
      matrix passed 13/13 with 10/10 scores, 22.048-29.166s standard creates,
      zero issues, and rescue smoke at 34.111s. Remaining proof: commit this
      checkpoint, rebuild the installable dist from the new commit, rerun the
      maintained installed matrix and fresh non-reused variance matrix with
      browser proof, generated-term leakage proof, hard 10/10 scores,
      sub-60s standard creates, and clean temp cleanup.
- [ ] Fix the 2026-06-30 fresh-variance source-text sentinel overreach.
      The committed `1ef33083` dist passed source-plus-dist leakage proof, but
      a new ten-domain installed variance run blocked before repo creation
      because automatic prompt phrase derivation treated platform/governance
      phrases such as `handoff evidence`, `manual override`,
      `operators request`, and `support team` as project-domain leakage
      sentinels. This is a recurrence of the broad free-text extraction failed
      mechanism captured in `CB-209`, not a generated consumer-project defect.
      The fix must keep declared case-owned sentinels explicit while making
      automatically derived source-text phrases require richer domain-specific
      signal than one long token next to generic governance vocabulary. Do not
      weaken the leakage gate, add broad phrase allowlists, or build a regex
      suppression tower. Proof must include focused leakage tests, source/dist
      leakage guard, and a fresh non-reused installed variance run with browser
      proof and clean temp cleanup.
- [ ] Remove score-harness false confidence before the next 10/10 claim.
      Independent review found that installed matrix quality can still score
      10/10 without browser proof, that several governed surfaces are counted
      without persisted readback quality checks, and that Compass record counts
      can be satisfied by shell assets instead of generated Compass records.
      Immediate fix: make omitted browser proof a premium-score blocker and
      count durable Compass records from specific source/runtime record paths.
      Follow-up hardening: add first-class package-evidence readback for
      release records, program records, Compass records, Casebook records, and
      rendered shell payload fields so existence counts cannot substitute for
      artifact quality.
- [ ] Remove the fresh-variance `conflict of interest` platform leak.
      After the source-text extraction overreach fix, the same ten-domain
      variance run blocked on a real platform leak: `conflict of interest`
      appears in generic greenfield runtime defaults and in the previously
      built wheel/runtime tarballs. Replace the example-domain phrase with
      generic policy or eligibility language, add a leakage sentinel regression,
      rebuild the local release dist, and rerun the fresh variance matrix with
      browser proof.
- [x] Fix helper-relative prompt recovery for embedded actor/action facts.
      Source now extracts embedded human actor/action facts from helper-relative
      prompt forms before Product Intent Confirmation, and project brief
      clipping removes dangling terminal verbs after accepted-sentence
      shortening. Focused proof passed the new helper-relative recovery
      regression, Project clipping regression, the generated-prose and
      post-confirm slop suites, and a disposable source-local performing-arts
      create passed in 15.770s with complete governed records and clean temp
      deletion. Remaining proof is packaged installed variance after rebuild,
      not another rendered-string patch.
- [x] Promote release/program/Compass/Casebook/shell payload readback into
      first-class quality evidence.
      Independent static review found that release/program quality is still
      count-or-preview based, Compass quality accepts narrow record presence
      without content readback, Casebook has no scored record family, and
      non-Project shell payload proof mainly checks route/hydration shape.
      This means current 10/10 scores are still too optimistic even when
      browser proof is mandatory. Add persisted readback objects and
      contract-aware quality checks for these families before claiming premium
      release readiness.
      The release matrix now uses `greenfield_matrix_governed_readback.py` to
      parse persisted release catalogs/events, program wave records, Compass
      runtime/source records, and all generated surface payload globals before
      premium scoring. Counts no longer accept arbitrary nonempty files,
      release/program freshness is tied to actual generated Radar workstream
      ids, program umbrella ids satisfy their own workstream coverage, missing
      Registry/Casebook/Compass/tooling payload readback blocks the appropriate
      dimension, and preview-only source-launch data no longer satisfies
      operator proof. Omitted browser proof is now a distinct browser dimension
      blocker rather than a copy/semantic finding. Current source proof: 58
      matrix tests, 84 install/leakage tests, 68 intent-recovery/Project tests,
      113 generated-prose/slop tests, py_compile, the 285-term source leakage
      guard, and a disposable municipal collector replay with all non-browser
      dimensions at 10/10 and clean temp cleanup. Remaining proof: rebuild the
      installable dist and rerun maintained plus fresh high-variance installed
      matrices with browser proof.
- [x] Split release-matrix scoring out of the oversized runner.
      `greenfield_matrix_quality_scoring.py` now owns brutal score dimensions,
      expert-lens score assembly, write-commit checks, count minimums, browser
      proof scoring, and score explanations. `greenfield_post_confirm_matrix.py`
      is back under the hard source-size pressure and owns orchestration,
      install/create execution, artifact collection, cleanup, and persisted
      matrix output. Focused install/leakage tests passed after updating tests
      to patch the scoring owner directly.
- [x] Remove platform-facing scenario vocabulary from current Registry specs.
      A follow-up leakage audit found that source/runtime leakage proof passed,
      but Domain Intelligence, Dashboard, and Release CURRENT_SPEC proof history
      still named old simulation scenarios. Those names are valid in fixture
      catalogs, Casebook repro evidence, and forensic snapshots, but not in
      platform-facing component contracts. The current pass rewrites those
      summaries to describe failure classes, proof posture, timings, and counts
      without scenario labels; removes a technical-domain trigger from Atlas
      box explanations; reruns the 285-term leakage guard; and reruns a strict
      platform-surface scan with zero retained-scenario matches outside
      intentional fixtures/evidence.
- [x] Decompose Atlas box tracked-object phrase selection.
      The platform-facing leakage cleanup touched
      `atlas_box_explanations.py`, which was already above the source-size
      pressure line. The current checkpoint moves tracked-object phrase
      selection into `atlas_box_terms.py`, keeps Atlas rendered-copy ownership
      focused on extraction and explanation composition, and pins a generic
      fallback regression where ordinary control verbs such as `stays` could
      become the visible domain object. Focused Atlas box explanation proof
      passed after the extraction.
