Status: In progress

Created: 2026-06-26

Updated: 2026-07-07

Backlog: B-142

Goal: Re-architect confirmed greenfield create around a typed, host-reasoned
semantic compiler and bounded semantic repair loop so Odylith can write
complete, premium-quality project and governance artifacts for arbitrary
domains without regex towers, rendered-string repair, domain-specific platform
vocabulary, or degraded packages.

## Architecture

- Compile the accepted Product Intent Confirmation into a versioned
  `ProductIntentEnvelope` and lossless `ConfirmedIntentIR` with source
  evidence, custody ledger entries, product-facts hash, section IDs, source
  spans, and provenance.
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

## Current Architecture Risk

- Behavioral proof is strong, but a perfect brittleness claim is not yet
  honest. A 2026-07-01 source audit across
  `src/odylith/runtime/domain_intelligence`, `src/odylith/runtime/artifact_quality`,
  and `scripts/release` found 105 of 172 scanned files with regex, template,
  or direct string-repair markers and 1,568 marker lines. Some of those uses are
  acceptable mechanical parsing or tokenization, but the remaining cleanup must
  separate mechanical parsing from semantic authority more aggressively before
  the architecture can claim zero-brittle posture.
- Source-size pressure remains material in the same slice: 15 scanned files are
  above the 800-line soft limit and one release script is above 1200 lines.
  Future hardening should decompose by ownership and remove semantic decision
  authority from regex-heavy modules without disturbing the proven
  post-confirm completion path.
- The next architecture pass should preserve the completion-first invariant:
  repairable post-confirm quality failures must prefer bounded semantic or plan
  repair and retry over no-write failure, while keeping no-write failure for
  non-repairable, unsafe, external, or budget-exhausted blockers.

## Related Bugs

- [CB-207](../../../casebook/bugs/2026-06-26-greenfield-post-confirm-package-repair-repeats-risk-prose-across-surfaces.md)
  tracks the repeated parent-risk projection failure fixed by moving child risk
  projection into semantic workstream ownership.
- [CB-208](../../../casebook/bugs/2026-06-26-greenfield-post-confirm-repair-routing-remains-stringly-typed-instead-of-semanti.md)
  tracks the remaining architecture defect: rescue still needs typed findings
  and semantic or plan patches instead of English issue-substring routing and
  rendered-prose mutation.

## Latest Simulation Evidence

- 2026-07-05 confirmed projection-custody checkpoint: the source-local repair
  for structured visible-result selection was necessary but insufficient on its
  own. A targeted replay showed that accepted-project/project-intelligence and
  Atlas projections could retain stale proof-boundary result text after
  `SemanticModelIR` had been corrected. Source fix now selects one
  visible-result fact before confirmed backlog/project brief/semantic model
  construction, threads that fact into completion text, project intelligence,
  component-risk repair, and confirmed Atlas diagram projection, and rerenders
  confirmed diagrams from the current `SemanticModelIR` before final package
  scoring. Focused regression proof passed for the computer-vision failed
  subset, exact source-local `grn-sim` replay wrote governed records in
  34.820s with clean Atlas copy, exact source-local `hv-033` replay wrote
  governed records in 45.836s with stale phrases confined to raw proof fields,
  and the post-fix package-quality confirmation pack passed 61 tests in
  74.41s. This is not release readiness: the previous local-installable dist is
  stale and failed installed `hv-033`, so the next boundary is a fresh dist,
  exact installed failed-subset replay, exact installed `grn-sim` replay, then
  resumed high-variance discovery and strict release proof.

- 2026-07-05 confirmed projection-custody installed checkpoint: fresh
  local-installable dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-projection-custody-20260705T170130Z`
  built from the post-governance tree and passed build-time platform-domain
  leakage across 224 distinctive fixture terms. Exact installed failed-subset
  replay for the prior computer-vision visible-result failure passed at hard
  10/10 with zero issues and create time 44.500s. Exact installed `grn-sim`
  saved-intent replay then completed governed create in 35.022s with 4 Radar
  rows, 5 Registry specs, 6 Atlas diagrams, and zero repeated-copy probes for
  the known escaped strings. This closes the current exact installed blocker
  proof, but not release readiness: strict release proof with browser-surface,
  natural rescue, broader unseen variance, generated readback leakage, and temp
  cleanup scoring still must run against this same dist.

- 2026-07-05 confirmed projection-custody strict release checkpoint: strict
  installed release-proof tier against the same candidate dist completed with
  `status=release-ready`, `release_proof_status=passed`, and
  `release_readiness_status=proven`. The 12-case scientific/deep-tech release
  shard passed 12/12 at hard 10/10 across cryogenic ion trap calibration,
  tokamak edge plasma disruption, and microfluidic organ-chip perfusion, with
  browser proof, generated-readback platform leakage proof, temp cleanup proof,
  and a real installed natural rescue structured patch-plan case all passed.
  Standard create timings stayed under 60s with min 42.579s, average 45.175s,
  and max 46.505s; natural rescue committed governed records after one
  schema-bound semantic patch in 71.967s CLI time. This proves the strict
  release-proof tier for the candidate package. Remaining boundary before a
  final stable checkpoint is broader unseen discovery after this proof and a
  final dist rebuild after post-proof governance updates.

- 2026-07-05 confirmed projection-custody 60-case discovery checkpoint: the
  same candidate dist passed a broader installed 60-case scientific/deep-tech
  regression with zero failures, zero issue findings, zero failure clusters,
  and hard 10/10 on every case. Domains covered cryogenic ion trap calibration,
  tokamak edge plasma disruption, microfluidic organ-chip perfusion, coral reef
  bleaching nowcast, neutrino detector calibration, hyperspectral crop disease
  mapping, autonomous underwater glider routing, solid electrolyte dendrite
  imaging, carbon capture solvent degradation, metamaterial acoustic cloak
  tuning, permafrost methane flux modeling, river flood ensemble assimilation,
  exoplanet transit spectroscopy, geothermal reservoir tracer inversion,
  satellite conjunction risk scoring, and fusion materials neutron damage.
  Standard create timing stayed under 60s with min 41.797s, average 49.788s,
  and max 55.052s. This is broad discovery proof; next breadth target is the
  120/240-case discovery lane, and final package handoff still requires a
  final dist rebuild after governance settles.

- 2026-07-05 confirmed projection-custody 120-case latency checkpoint: the
  next installed discovery lane against the same candidate dist passed the
  first two 30-case shards at 60/60, then stopped early in shard 004 on a
  latency-only blocker. The failed case produced quality-complete governed
  artifacts with PM, architect, engineer, and domain-expert lenses green, but
  `greenfield create` exceeded the standard operator budget at 60.570s under
  cluster `post.confirm.create.exceeded.60s.570s`. Exact failed-subset replay
  lives at
  `/private/tmp/odylith-projection-custody-120case-20260705T180927Z/failed-subset-replay/failed-subset-001.cases.json`.
  Treat this as an open standard-path performance/replay isolation blocker:
  do not raise the 60s budget, do not classify the case as rescue, do not add
  project or scientific vocabulary to platform code, and do not resume broad
  discovery until the exact failed subset has been replayed and any root cause
  is fixed generically.
  Exact installed failed-subset replay later passed in isolation at hard 10/10
  with 47.006s create time, zero issues, complete governed records, and all
  expert lenses green. This isolates the 60.570s event as discovery-lane
  concurrency or margin pressure rather than intrinsic project complexity, but
  the broader 120/240-case lane remains blocked until controlled discovery is
  clean. The same pass corrected leakage-candidate custody after a raw
  case-derived scan treated platform-native quality obligations as project
  domain terms: `case_leakage_term_candidates` now derives fallback source
  terms from product/title/vocabulary context and confirmed-intent source
  sections while the default historical platform-leakage proof keeps its
  224-term breadth. Focused proof passed 38 leakage/preflight tests;
  source/dist platform leakage passed 224 fixture terms; exact case-aware
  source/dist leakage passed 69 terms with zero findings.
  Controlled installed shard replays then closed the stopped 120-case tranche:
  original shards 001 and 002 passed 60/60, replayed shard 003 passed 30/30,
  replayed shard 004 passed 30/30, and the aggregate 120-case proof is now
  120/120 passed with zero issues, hard 10/10 min/max quality, min create
  44.368s, average 49.031s, and max create 54.498s. Cleanup reduced obsolete
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-*` dist
  folders from 176 to one active candidate dist and removed the remaining
  Odylith scratch repo under `/Users/freedom/mock`. This is controlled
  discovery closure, not final release readiness; the final rebuilt dist still
  needs strict release proof with browser, natural rescue, leakage, and cleanup
  gates.

- 2026-07-05 accepted-project final-memory actor-selection checkpoint: the
  broader 120-case controlled-concurrency discovery tranche stopped after 40
  hard-10/10 passes on `quantum dot display aging simulation review board`
  because accepted-project final memory contained
  `lets the quantum dot display review the published readiness proof` and the
  presentational-splice gate correctly refused to write governed records. Root
  cause was generic supporting-actor selection: generated product-role actors
  were treated as present in a first path when any domain token overlapped the
  step text, so title/domain words could become follow-up recipients. Source
  fix makes first-path actor presence role-aware: a supporting actor must match
  as a direct actor phrase or through a role-compatible actor term; domain
  object overlap alone is not enough. Focused proof passed the new
  high-variance actor regression and related published-readiness slop checks
  (`7 passed`), source-local replay wrote governed records with manifest
  passed, zero issues, 4 Radar workstreams, 3 Registry components, and 6 Atlas
  diagrams, and fresh installed dist
  `/private/tmp/odylith-local-release-0.1.15-qdot-actor-20260705T002631`
  passed the exact failed-subset replay at hard 10/10 in 42.730s with zero
  issues, 18 trace nodes, 5 Project implementation prompts, zero prompt
  findings, all expert lenses green, platform leakage proof, and temp cleanup.
  This proves the escaped no-write class from a fresh installed package, not
  release readiness; browser/natural-rescue release proof and resumed broader
  120/240 discovery remain required.

- 2026-07-05 hyphenated scientific-anchor checkpoint: the resumed 60-case
  installed regression against the drone-anchor candidate dist passed 36 fresh
  cases before stopping on `radiotherapy dose adaptation intake-to-proof
  workspace`. Governed post-confirm creation completed cleanly in 39.165s, but
  the brutal domain-expert lens scored the case 0/10 because one required
  source-grounded term, `organ-at-risk`, disappeared from scored generated
  surfaces. Root cause was a generic semantic-ingress tokenization defect:
  evidence-anchor meaningfulness counted hyphenated compounds as one word and
  rejected them before typed evaluation/source requirements could project into
  Radar, Registry, Atlas, project brief, or Project prompts. The source fix
  treats hyphen, slash, and whitespace as lexical part boundaries for anchor
  meaningfulness while preserving source spelling. Focused proof passed
  `tests/unit/runtime/test_greenfield_prompt_requirement_boundary.py`
  (`5 passed in 89.71s`), source-local CLI replay wrote clean governed records
  with `organ-at-risk` visible in six scored/generated surfaces, and fresh
  candidate dist
  `/private/tmp/odylith-local-release-0.1.15-hyphen-anchor-20260704T231813`
  passed the exact installed failed-subset at hard 10/10 in 37.990s with zero
  issues and all expert lenses green. This proves the exact failure class, not
  release readiness. The resumed two-shard scientific/deep-tech tranche then
  passed 60/60 cases with all hard 10/10 scores, zero issues, all
  domain-expert lenses green, create-time min 37.896s, average 42.265s, max
  47.917s, and no case over 60s; the original radiotherapy case passed again
  in context at 39.436s. This is strong discovery evidence, but strict
  browser/natural-rescue release proof and broader 120/240 discovery are still
  required before release readiness can be claimed.

- 2026-07-05 source-anchor and architect-role recurrence checkpoint:
  the fresh 180-case extension stopped on `drone swarm search coordination
  intake-to-proof workspace` after seven hard-10/10 passes because a generated
  case prompt contained `mission evidence evidence` and the semantic compiler
  preserved that adjacent duplicate into evidence requirements and evaluation
  anchors. After that source-anchor fix, the same prompt exposed a second
  generic Product View defect: `architect` was not recognized as a human role
  noun, so capability projection recomposed `the user can robotics architect
  provides inputs`. The source fix canonicalizes adjacent duplicate words at
  the typed evidence-anchor boundary and release case-file boundary, and adds
  `architect/architects` to the generic actor-role set. Focused proof passed
  the affected 12-test pack in 92.59s. Disposable source-local CLI replay of
  the exact prompt wrote governed records with manifest passed, issue_count 0,
  4 Radar records, 3 Registry specs, and 6 Atlas diagrams; temp repos were
  deleted. Fresh local dist
  `/private/tmp/odylith-local-release-0.1.15-drone-anchor-20260704T224118`
  passed 224-term platform leakage proof, and the exact installed failed-subset
  replay passed at hard 10/10 in 38.266s with zero issues, 18 trace nodes,
  5 Project implementation prompts, zero prompt findings, and all expert
  lenses green. This proves the exact recurrence, not release readiness; the
  next step remains resumed 60/120/240 high-variance discovery followed by
  strict browser/natural-rescue release proof.

- 2026-07-04 campaign stratification hardening checkpoint: the tiered
  Greenfield matrix harness now persists source-file, tag, stressor, and
  stressor-by-tag distribution in generated case files and tier shard
  summaries. This closes the planning gap where hundreds of generated projects
  could still be opaque if the source pool did not prove ambiguity-shape
  breadth before execution. The change stays generic: no project-domain
  vocabulary enters Odylith, and the evaluator scores metadata shape rather
  than specific domains. Focused proof passed the campaign/generator/sharder
  harness suite (`63 passed in 1.53s`). This is discovery-harness proof only;
  release readiness still requires fresh installed release-proof tiers with
  browser, natural rescue, platform-leakage, temp-cleanup, and brutal artifact
  readback proof.

- 2026-07-04 failed-subset replay materialization checkpoint: the campaign
  runner now converts replayable failure-response evidence into actual
  failed-subset replay shard files when source case files and failed result JSON
  contain exact stable identity. The final campaign JSON carries
  `failure_response.failed_subset_replay` with `status=written`, file paths,
  summary path, source files, failed-result files, and `next_tier=failed-subset`;
  non-exact cases return explicit unavailable/not-required reasons and keep the
  source-shard replay guidance. This closes the remaining operator-loop gap
  where a failure packet told maintainers to build failed subsets but left that
  as manual aftercare. The wrapper exposes
  `GREENFIELD_MATRIX_FAILED_SUBSET_REPLAY_DIR` for controlled output placement.
  Focused proof passed the campaign/sharder/failure-response/generator harness
  suite (`68 passed in 1.61s`) and shell syntax checks. This is discovery-loop
  infrastructure only; it does not prove Greenfield artifact quality or release
  readiness.

- 2026-07-04 campaign harness completion and release blocker checkpoint:
  the high-volume harness now reports incrementally and replayably enough for
  stop-fix-replay execution. Live stop decisions use the failure-emitting
  shard from child telemetry, child matrix commands receive required stressor
  classes, discovery shards can report partial shard-local stressor coverage
  while the tier owns aggregate coverage, synthetic launch and cleanup failures
  write replayable payloads, and campaign status now separates
  `discovery-passed` from `release-ready` with `execution_status` retained for
  CLI exit behavior. Focused proof passed synthetic/replayability tests
  (`4 passed`), focused harness/preflight/Compass tests (`10 passed in
  15.50s`), Compass visible-copy tests (`3 passed`), the full install/matrix
  harness suite (`135 passed in 15.98s`), compile checks, shell syntax checks,
  and diff hygiene. This completes the requested runner architecture slice,
  but it does not clear the Greenfield release goal: the broad runtime quality
  pack still failed (`4 failed, 67 passed in 902.47s`) on semantic-model actor
  casing, visible-result event ownership, and extra actor derivation. The next
  implementation step is Domain Intelligence semantic repair for those defects,
  then exact failed-subset replay, then resumed 60/120/240 discovery and strict
  release proof.

- 2026-07-04 incremental telemetry and case-generation checkpoint: the
  Greenfield discovery harness now has a source-grounded case generator
  (`bin/greenfield-matrix-generate-cases`) that selects from external case
  files by stressor coverage, source balance, tag balance, and density instead
  of counting raw projects. Matrix preflight now emits structured failed case
  telemetry and incremental result JSON before expensive execution when source
  metadata is invalid, required stressors are absent, leakage terms are
  missing, or platform-domain leakage is detected. Campaign progress now tracks
  running cases and failed case identity per shard; live-stop failure-response
  packets can therefore synthesize replayable failed-subset payloads from the
  exact failed cases rather than all stopped siblings. Explicit
  `required_stressors` are enforced even outside high-variance default mode,
  and tooling payload readback now anchors on the real global assignment instead
  of scanning from the first JavaScript object. Focused proof passed
  `py_compile` for the touched harness modules, shell syntax for the wrappers,
  an external-case generator smoke, and the focused install/matrix regression
  pack (`58 passed in 8.45s`). This remains discovery-harness proof; release
  readiness still requires a fresh installable dist with browser, rescue,
  natural-rescue, platform-leakage, and temp-cleanup proof.

- 2026-07-04 tiered matrix harness checkpoint: high-volume Greenfield
  discovery is no longer a mostly opaque final-JSON runner. The release
  scripts now use a shared stressor taxonomy owner for modal expert lenses,
  path grants, noun/verb homonyms, scientific casing, multi-role review,
  long first paths, domain-depth obligations, final-memory pressure, Atlas
  label pressure, Registry contract pressure, and latency pressure. The
  maintained release cases now carry explicit stressor metadata, campaign
  summaries include a 10-point variance score, and the campaign runner emits
  merged per-case progress, incremental shard result JSON, live failure-cluster
  stop decisions, failed-result JSON pointers, stable failed case IDs and
  fingerprints, and a failure-response packet requiring Casebook capture,
  platform repair, exact failed-subset replay, then resumed 60/120/240
  discovery. D-047 now documents the shared taxonomy, failure-response, and
  stop-fix-replay loop. Focused proof passed 47 tiered harness tests, 77
  installed matrix/proof-scope tests, py_compile for touched scripts, scoped
  `git diff --check`, Atlas D-047 render with 47 fresh / 0 stale diagrams, and
  a disposable campaign smoke that intentionally failed on a fake install but
  still emitted case telemetry, merged progress, failed-result JSON, and a
  Casebook/replay failure-response packet. This is discovery-harness proof,
  not release readiness; release readiness still requires a rebuilt dist and
  strict installed release proof with browser and natural rescue.

- 2026-07-01 committed-head dist `da2643edecc66e403a9e070d7976a2033248e5bd`
  is behaviorally release-strong for local skip-verify installation: maintained
  installed proof passed 14/14 standard domains at 27.616-34.472s, synthetic
  rescue at 42.568s, and natural structured rescue at 74.053s; scientific
  variance passed 6/6 at 29.023-33.698s; exact saved `grn-sim` replay committed
  governed records in 31.15s with 4 Radar, 5 Registry, 6 Atlas, all expert
  lenses, Atlas refresh, and zero repeated visible-copy signatures. A follow-up
  adversarial installed matrix added eight fresh domains -- neural prosthetic
  calibration, wildfire smoke assimilation, quantum error correction,
  groundwater contaminant plume, pharmacovigilance signal adjudication,
  cryptographic protocol verification, crop heat stress genomics, and surgical
  robotics validation -- and passed 8/8 at hard 10/10 with zero issues,
  browser proof, complete governed records, zero prompt findings, and
  32.544-34.524s standard create times. One failed simulation mechanism was
  captured before the pass: selected leakage vocabulary must be distinctive
  domain vocabulary, not generic source-overlapping phrases such as `reviewers
  inspect`. Product priority is now explicit: for repairable failures,
  post-confirm governed projection completion outranks stopping on quality; the
  quality gate should trigger bounded repair and retry, while no-write remains
  reserved for non-repairable, unsafe, external, or budget-exhausted blockers.

- 2026-07-01 rebuilt installed release proof against committed checkpoint
  `5b94bd8f` reclaimed the CB-207 package-repetition gate. The fresh
  high-variance installed matrix at
  `/tmp/greenfield-post-confirm-fresh-variance-5b94bd8f.v1.json` passed 8/8
  standard cases at hard 10/10 with zero quality, browser, prompt, or platform
  leakage issues; complete governed records; browser proof; platform leakage
  proof across 131 generated terms; temp cleanup; max standard create time
  25.701s; synthetic rescue at 33.288s; and natural structured rescue at
  56.548s. The maintained installed release matrix at
  `/tmp/greenfield-post-confirm-matrix-5b94bd8f.v1.json` passed 13/13 standard
  cases at hard 10/10 with zero issues; browser proof; platform leakage proof
  across 213 generated terms; temp cleanup; max standard create time 28.062s;
  synthetic rescue at 33.620s; and natural structured rescue at 56.311s. CB-207
  is closed. The next CB-208 cleanup then moved package-level semantic
  repetition into source-owned structured findings: rendered package findings now
  carry `package_repetition` code, occurrence paths, projections, surfaces,
  counts, ArtifactPlanIR target roots for single-projection defects, and typed
  post-confirm review routing instead of falling back to
  `legacy_package_artifact_gate`. Source proof passed 14 focused
  package-repetition/post-confirm tests, 64 repair and ArtifactPlanIR tests, the
  full post-confirm engine suite passed 35 tests, the broader greenfield
  artifact-quality suite passed 52 tests, py_compile passed for touched modules,
  `git diff --check` passed, and the 285-term platform domain-leakage guard
  passed. Follow-up import hygiene kept `greenfield_package_quality.py` at the
  800-line soft ceiling, preserved `greenfield_package_repetition.py` at 472
  lines, and the final focused post-confirm/repair suite passed 99 tests in
  44.57s.

- 2026-07-01 fresh installed variance against the final committed
  `925545d8` dist proved CB-207 was still open. Seven of eight new domains
  passed at hard 10/10 with browser proof, complete governed records, standard
  create times under 26s, leakage proof across 114 generated readback terms,
  clean temp cleanup, synthetic rescue at 33.170s, and natural structured
  rescue at 64.368s. One document/status-style dispute workflow failed before
  governed writes in 12.336s because specialized component-profile rebuilds
  replaced three complete component-local semantic `unique_failure` facts with
  one shared profile-level generated proof/risk sentence, which then repeated
  across Registry specs and surfaced as `legacy_package_artifact_gate`. Source
  now preserves semantic `unique_failure` through specialized profiles; focused
  component/Registry/package proof passed 53 tests, and exact source-local
  replay of the failed intent committed governed records in 14.989s with zero
  final issues. Rebuilt installed proof remains required before release
  readiness is reclaimed. The separate package-repetition architecture debt has
  source proof now; release readiness still requires rebuilt installed proof from
  the committed code.

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

- 2026-06-30 release-packaging posture follow-up: the `cf815d6e` local-release
  build failed before packaging because committed Registry `FORENSICS.v1.json`
  sidecars were last regenerated by the pinned dogfood runtime and still
  contained raw Compass summaries with prior high-variance project names.
  Source implementation and tests were already scenario-neutral, so the failed
  mechanism was stale governed sidecars from the wrong runtime posture. Release
  packaging now requires source-local regeneration and source-local
  `sync-component-spec-requirements --check-only` for forensics custody changes
  before the dist leakage gate can be trusted.

- 2026-06-30 committed release-dist proof: checkpoint `5c5fd0ed` rebuilt into
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-5c5fd0ed`
  after source-local forensics regeneration and the actor/component-label
  checkpoint. The build passed the 285-term platform domain-leakage guard. The
  installed matrix proof at `/tmp/greenfield-post-confirm-matrix-5c5fd0ed.v1.json`
  passed 13/13 maintained standard cases with hard 10/10 scores, zero issues,
  all product-manager, architect, engineer, and domain-expert lenses passing,
  per-case browser proof passing, complete governed records, five
  implementation prompts per project with zero prompt findings, max standard
  create time 28.685s, synthetic typed-probe rescue passing in 34.851s, and
  real installed structured rescue passing in 61.940s under the 90-second
  rescue tier. Platform leakage proof and temp-cleanup proof both passed.

- 2026-06-30 final committed release-dist proof: checkpoint `925545d8` rebuilt
  into `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-925545d8`
  after the exact proof-governance checkpoint was committed and pushed. The
  build passed the 285-term platform domain-leakage guard. The installed matrix
  proof at `/tmp/greenfield-post-confirm-matrix-925545d8.v1.json` passed 13/13
  maintained standard cases with hard 10/10 scores, zero issues, all
  product-manager, architect, engineer, and domain-expert lenses passing,
  per-case browser proof passing, complete governed records, five
  implementation prompts per project with zero prompt findings, max standard
  create time 29.643s, average standard create time 27.049s, synthetic
  typed-probe rescue passing in 35.531s, and real installed structured rescue
  passing in 62.307s under the 90-second rescue tier. Matrix generated-term
  leakage proof and temp-cleanup proof both passed.

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

## Current Completion Audit

- 2026-07-01 audit result: the current committed release checkpoint is proven
  for the known greenfield post-confirm failure classes, but this plan remains
  active rather than globally complete. The committed `c6971540` dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-c6971540`
  passed the installed matrix after stale temp cleanup with 13/13 standard
  creates at hard 10/10, zero final quality issues, browser proof, generated
  platform-leakage readback across 213 terms, no remaining temp simulation
  roots, 22.712s minimum, 25.279s average, and 27.755s maximum standard create
  time. Synthetic typed-probe rescue passed in 34.454s, and the real
  provider-backed structured rescue passed in 58.415s under the 90s rescue
  tier. Compass records the proof under the follow-up `851f0ab0` checkpoint.
- The completion claim is intentionally finite: it proves the current
  release-candidate package and the covered high-variance scenarios, not a
  mathematical guarantee for every future domain. Remaining active work is the
  architectural hardening still named below: finish the lossless IR schema
  story for `ConfirmedIntentIR` / `ArtifactDraftSet` / stable source spans,
  complete broader context-starved projection contracts such as the
  `ProjectionLexicon`, and keep extending the hostile variance corpus whenever
  new real-world failures appear.
- 2026-07-05 installed release-matrix result: release readiness is blocked
  again. Working-tree dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-guidance-smoke2-20260705T0458`
  passed local release smoke after managed guidance fixes, then failed the
  installed release matrix with 12/14 standard cases passing at hard 10/10 and
  two prewrite failures. `package supply chain exception desk` stopped before
  manifest creation on inline actor casing drift in backlog domain-intelligence
  summary/intent fields. `sparse disclosure confirmation` reached the rescue
  path, classified the domain-expert high-risk-assumption gap as repairable,
  but emitted an artifact-plan patchset request with empty replacement facts,
  ledger, and proof-obligation delta, so no executable repair occurred and no
  governed records were written. The architecture gap is incomplete typed
  semantic/artifact-plan custody for actor casing and high-risk assumption
  coverage, plus a repair planner that can label a finding repairable without
  producing a valid patch.
- 2026-07-07 typed product-intent custody checkpoint: the current source tree
  introduces `ProductIntentEnvelope` v2 and `CustodyLedger` v1 for confirmed
  greenfield ingress. The envelope stores canonical product facts, source
  evidence, materiality status, provenance, ignored/supporting evidence, and a
  decision record with a product-facts hash. Confirmed JSON without the v2
  schema or with a stale hash is not trusted as product truth; it is
  re-normalized through the same custody pipeline. Human-edited Markdown,
  planning notes, host guidance, fenced examples, implementation prompts, and
  Next Step prose are treated as evidence and classified before they can affect
  product facts. The source slice also fixes terminal handoff visible-result
  projection and confirmation next-step UX. Proof is source-local so far:
  `255` greenfield post-confirm/parser/projection tests, `78` adjacent
  confirmed-intent recovery tests, `203` first-path/projection tests,
  py-compile, and whitespace checks passed. Clean committed-head installed
  proof remains required before release readiness.
- 2026-07-07 adversarial custody checkpoint: follow-up source review found
  that typed custody still needed source-byte verification, nested-heading
  containment, and stricter compiler fact authority. The follow-up fixes block
  nested supporting/ignored Markdown headings from product-fact re-entry,
  require sidecar JSON product facts to match adjacent Markdown
  `source_sha256`, reject unverifiable v2 envelopes instead of trusting mirrored
  top-level projection, require nested `intent` ownership for semantic compiler
  certification, remove generated `project_brief` prose as a compiler fallback
  or legacy-promotion source, remove all downstream legacy-source mutation of
  canonical `intent.*`, and broaden terminal handoff result extraction without
  accepting person-to-person routing. Exact regressions passed, the
  focused authority bundle passed `47` tests, the reviewer-targeted
  product-intent/semantic/slop suite passed `163` tests, and the adversarial
  CLI/live-selection smoke passed `18` tests.

## Implementation Slices

- [ ] Define `ProductIntentEnvelope`, `ConfirmedIntentIR`, `SemanticModelIR`, `ArtifactPlanIR`,
      `ArtifactDraftSet`, `ReviewReport`, and `PatchSet` schemas with source
      provenance and stable IDs. Current checkpoint defines the versioned
      `ProductIntentEnvelope` v2, `CustodyLedger` v1, product-facts hash
      validation, typed `ReviewReport` findings, `PatchSet` request schemas, a
      source-mapped apply-semantic input bridge, and the first shared
      `ArtifactPlanIR` projection contract owner. A lossless
      `ConfirmedIntentIR`, full `ArtifactPlanIR` schema, `ArtifactDraftSet`
      schema, and stable source-span IDs remain open.
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
      The 2026-07-01 source-address checkpoint adds an executable
      `ProjectionSourceAddress` contract in `greenfield_artifact_plan.py`:
      dict projections require a named field, row projections require a row
      index plus field, list projections may target whole-list facts or indexed
      rows only, and broad roots such as `proposal.backlog`, `components`,
      `project_brief`, non-indexed list tails, or preview-only paths cannot
      become PatchSet operations. Package and lens findings now become plan
      patches only when that source address exists;
      identifiable Registry spec copy defects map back to
      `components[n].component_contract.produced_outputs`, while unsupported
      package repetition stays fail-closed instead of advertising a fake root
      patch. This is the next typed-IR repair substrate step, but broader
      renderer context starvation and full source-span IDs remain open.
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
- [x] Source-address PatchSet custody proof: focused ArtifactPlanIR,
      artifact-plan executor, PatchSet payload, post-confirm engine,
      quality-repair, source-addressed repair, quality-lens, and package
      repetition tests passed 130 tests in 46.20s. Py-compile proof,
      `git diff --check`, and the 285-term platform domain-leakage guard
      passed for the changed source owners. The suite now proves broad
      projection roots are not executable plan patches, exact source leaves
      still route to `ArtifactPlanIR`, non-indexed list tails are rejected, and
      source-owned Registry generated-copy findings resolve to component
      contract facts before repair. Atlas freshness, Casebook source,
      component Registry, plan/workstream binding, and plan risk/mitigation
      validation also passed after the governed surface sync.
- [x] Product-intent envelope and edited-Markdown custody source proof:
      greenfield post-confirm/parser/projection tests passed `255` tests in
      `584.51s`; confirmed-intent section-boundary, recovery, and sparse
      confirmation tests passed `78` tests in `252.19s`; first-path modal,
      high-variance action, generated-prose, source-casing, confirmed-text,
      product-envelope, and metamorphic confirmed-intent tests passed `203`
      tests in `148.23s`; py-compile passed for changed source owners; and
      `git diff --check` passed.
- [x] Adversarial authority-boundary follow-up proof: nested supporting
      headings, forged JSON sidecars with recomputed product-facts hashes,
      forged in-memory envelopes, unverifiable v2 envelope downgrade attempts,
      missing-intent semantic compiler fallbacks, top-level fact bypasses,
      generated project-brief and downstream legacy promotion attempts, and
      terminal handoff variants now have focused regressions. Exact regressions
      passed; the authority bundle passed `47` tests; the reviewer-targeted
      product-intent/semantic/slop suite passed `163` tests in `136.69s`; the
      CLI/live-selection smoke passed `21` tests; py-compile and whitespace
      checks passed.
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
- [x] Fix coordinated-action actor recovery and repeated clarity titles found by
      source-local artifact QA.
      A wearable-health source-local simulation completed governed writes but
      direct artifact inspection found a false `Separate Urgent` actor,
      malformed carried-action clauses, and a `Clear ... Clear` Radar
      state-boundary title shape. The mechanism is general: the provider-free
      fallback grammar missed ordinary action verbs and the title owner added a
      clarity modifier without checking the state label. Source now recognizes
      the missing shared action verbs, carries the explicit actor across
      coordinated sibling clauses, prevents repeated clarity modifiers, routes
      Project dashboard card findings to card-specific source facts, and
      rebuilds accepted-project/dashboard previews with fresh source-launch
      context. Proof passed 48 recovery/backlog tests, 130 combined
      recovery/projection tests, 100 post-confirm/install tests, source
      leakage across 285 terms, and six source-local simulations at
      19.455-21.543s with zero final issues, Atlas render passing, Registry
      validation passing, no escaped bad strings, and temp cleanup after each
      repo. Remaining proof is rebuilt installed matrix and fresh variance with
      browser proof.
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
      Committed-head proof rebuilt
      `odylith-local-release-0.1.15-78787588`, passed the source-plus-dist
      leakage guard, then passed the maintained installed greenfield matrix:
      13/13 standard creates, 22.690s minimum, 26.156s average, 29.050s
      maximum create time, zero platform leakage findings, zero browser
      findings, zero quality issues, and 10/10 brutal scores across all
      standard matrix cases. The synthetic rescue smoke passed in 33.888s, but
      remains typed-probe wiring proof rather than natural host-rescue quality
      proof.
- [x] Make fresh-variance matrix proof durable and externally configurable.
      The installed matrix now accepts explicit external case files through the
      release script and the standalone wrapper, persists per-case post-confirm
      manifest summaries, derives natural-rescue proof only from non-probe
      provider-backed structured patch evidence, and records temp-cleanup proof
      as a matrix status gate. Focused proof passed 101 install/runtime tests,
      py_compile, shell syntax checks, and a three-case external variance run
      against the latest local dist with 10/10 scores, zero quality/browser/
      platform-leakage issues, 24.952s minimum, 25.405s average, 25.970s
      maximum create time, passed persisted cleanup proof, and synthetic rescue
      smoke at 33.491s. Natural host-rescue quality remains explicitly unproven.
      Follow-up committed-head proof rebuilt
      `odylith-local-release-0.1.15-4750c7ec` from pushed commit `4750c7ec`;
      the maintained installed matrix passed 13/13 standard creates with
      persisted JSON proof, 10/10 scores, zero quality/browser/platform-leakage
      issues, browser proof passed for all 13 cases, 22.622s minimum,
      26.394s average, 28.799s maximum create time, persisted cleanup proof
      passed with no remaining temp paths, and synthetic typed-probe rescue
      smoke passed in 34.340s. Natural host-model rescue remains explicitly
      unproven and is still the next proof gap.
- [x] Close repeated Registry-forensics stale-sidecar leakage before local dist proof.
      A 2026-07-02 fresh local release build from `0069fca4` failed before
      installable proof because committed component `FORENSICS.v1.json`
      sidecars again retained old high-variance scenario vocabulary inside
      protected Registry custody. The source projector was already generic, so
      the root cause was release workflow custody plus sync convergence:
      packaging did not first require source-local forensics freshness, and a
      sync invocation that updated a component spec could leave forensics stale
      until a second pass. The fix adds a source-local
      `sync-component-spec-requirements --check-only` preflight to local release
      build, installed matrix proof, and release proof wrappers; the sync
      command now rebuilds the Registry report and writes forensics from the
      refreshed snapshot after any spec write. Source-local check-only,
      focused sync/release-script tests, and the 285-term platform leakage guard
      are green; fresh committed-head dist and installed high-variance proof are
      still required before release readiness can be claimed.
- [x] Decompose Atlas box tracked-object phrase selection.
      The platform-facing leakage cleanup touched
      `atlas_box_explanations.py`, which was already above the source-size
      pressure line. The current checkpoint moves tracked-object phrase
      selection into `atlas_box_terms.py`, keeps Atlas rendered-copy ownership
      focused on extraction and explanation composition, and pins a generic
      fallback regression where ordinary control verbs such as `stays` could
      become the visible domain object. Focused Atlas box explanation proof
      passed after the extraction.
- [x] Preserve provider-backed rescue evidence through final clean manifests.
      The post-confirm engine now records the last nonempty repair PatchSet
      request as `last_repair_patchset_request` when a repair pass succeeds and
      the final package is clean. Confirmed greenfield create enriches the
      repair context with the structured Tribunal patch planner before the
      engine decides rescue custody, and the planner is idempotent once a plan
      summary exists. Release proof reads natural rescue evidence from that
      preserved repair request, not from chat or terminal claims, and the
      maintained matrix now has an explicit natural structured-rescue proof leg
      that requires a provider-backed non-probe repair under the 90-second
      rescue budget. Focused source proof passed the post-confirm engine,
      structured-rescue trigger, PatchSet enrichment, proof-scope, natural
      rescue matrix, wrapper/bootstrap, py_compile, shell syntax, diff hygiene,
      and platform leakage checks. Remaining proof: rebuild the installable
      dist from the committed checkpoint and rerun the maintained installed
      matrix with natural structured-rescue proof enabled.
- [x] Calibrate structured PatchSet planning for the 90-second rescue budget.
      The first committed natural-rescue proof caught a real timeout defect:
      standard installed create passed across thirteen cases, but the
      host-planned structured-rescue leg failed because the PatchSet planner
      inherited global high-effort Codex reasoning and capped the provider call
      at 25 seconds. The provider timed out, no replacement fact was available,
      and the semantic executor correctly refused an empty repair. The rescue
      planner now treats PatchSet planning as a narrow schema-constrained task:
      it defaults local CLI providers to medium effort unless an explicit
      effort env override is supplied, and it can allocate up to 45 seconds
      while preserving a 10-second rerender/write buffer inside the 90-second
      rescue budget. A retained source-local repro passed in 55.085 seconds
      with `structured_rescue_semantic_patch` repaired, a provider-backed
      `last_repair_patchset_request`, and committed governed records. Remaining
      proof: rebuild the committed-head dist and rerun the full installed
      matrix with natural structured-rescue proof.
- [x] Prove committed source-owned repair checkpoint through the installed
      release matrix.
      Fresh dist `odylith-local-release-0.1.15-2a389428` passed the maintained
      installed matrix after temp cleanup: 13/13 standard cases, hard 10/10
      scores, zero quality/browser/platform-leakage issues, 13/13 browser
      proof, generated-term leakage proof across 213 readback terms, clean
      temp cleanup, max standard create time 30.468s, average standard create
      time 27.801s, synthetic rescue smoke at 37.493s, and real installed
      structured rescue at 62.894s under the 90s rescue tier. The first full
      attempt against the same dist failed with a Python `SIGBUS` and left a
      temp root; one-case and three-case browser probes passed, then the full
      retry passed. Follow-up hardening remains to persist incremental matrix
      results and isolate browser/rescue proof legs so harness-native crashes
      cannot erase completed evidence.
- [x] Repair intentional empty-list structured rescue and prove the fresh
      installed checkpoint.
      The next natural structured-rescue proof failed before governed writes
      even though the provider chose the right semantic interpretation: the
      planner could not distinguish a missing replacement fact from an
      intentional clear of a list-valued semantic boundary, so the operation was
      rejected as `replacement_fact is empty`. The fix keeps the architecture
      typed and fail-closed: Tribunal materializes explicit `value_kind=list`
      envelopes for list-valued SemanticModelIR fields even when the list is
      empty, rescue planning treats those facts as executable, and the semantic
      executor applies the empty list to intent plus semantic ontology while
      recording the host decision ledger. Blank, absent, prose-only, moved, and
      non-list empty facts still fail closed. A separate release-harness custody
      fix keeps top-level rescue-proof JSON classified as evidence so the
      platform leakage scanner still scans source, wheel, and runtime archives
      without treating generated proof evidence as platform code. Focused proof
      passed 67 Tribunal/PatchSet/semantic-engine tests plus leakage proof
      tests and the prior project-brief boundary tests. Fresh dist
      `odylith-local-release-0.1.15-clear-list-fix` passed 13/13 maintained
      installed standard cases with hard 10/10 quality scores, zero quality,
      browser, and platform-leakage issues, 13/13 browser proof, max standard
      create 30.563s, average standard create 27.854s, synthetic rescue at
      38.917s, and real provider-backed natural structured rescue at 60.926s
      with `structured_rescue_semantic_patch`, one accepted Tribunal operation,
      no rejections, committed governed writes, and temp cleanup.
- [x] Preserve Registry forensics neutrality through source-local regeneration.
      A pre-commit leakage scan caught old simulation terms in component
      `FORENSICS.v1.json` sidecars after a pinned dogfood Registry refresh.
      The source fix from CB-209 was still correct: forensics projection emits
      generic event summaries and neutral artifact reference labels, while raw
      repro language remains in Casebook/Compass evidence. The failure was a
      lane-posture mismatch: checked-in source-owned forensics must be
      regenerated through detached source-local code before pinned/dogfood
      release proof. Source-local component-spec sync rewrote all forensics
      sidecars, source-local Registry refresh updated the surface, the
      component-spec sync check passed with zero stale forensics, the platform
      leakage guard passed across 285 distinctive fixture terms, the focused
      forensics/leakage suite passed 33 tests, and the source-local broad sync
      check passed with Registry, Atlas, Casebook, backlog, plan, and delivery
      gates clean.
- [x] Add a safe host-ledger custody boundary for natural structured rescue.
      Fresh dist `odylith-local-release-0.1.15-31ab2559` preserved the
      post-0.1.14 standard-path benchmark gains: 13/13 maintained standard
      cases passed hard 10/10 under 60 seconds, with max create time 27.835s,
      zero package/browser/platform-leakage issues, and synthetic typed-probe
      rescue in 34.084s. The real provider-backed natural rescue leg still
      failed before governed writes after 69.399s because host-authored
      `decision_ledger_entry.rationale` crossed into
      `proposal.semantic_patch_ledger` with unbalanced quoted text. The fix
      keeps replacement facts authoritative and leaves the semantic slop gate
      intact: Tribunal planner validation, semantic patch application, and
      post-confirm manifest proof now project host rationale, rejected
      interpretations, proof-delta prose, and decision summaries as safe plain
      ledger text while preserving `replacement_fact` payloads unchanged.
      Focused proof currently covers planner validation, semantic ledger
      projection, generated-copy slop detection, and manifest proof custody.
      Remaining proof: rerun the maintained installed matrix from a rebuilt
      dist with browser proof and real natural structured rescue enabled.
- [x] Prove the typed package-repetition checkpoint through a rebuilt installed
      dist.
      Fresh dist `odylith-local-release-0.1.15-c6971540` from committed head
      `c6971540` passed the release asset domain-leakage gate across 285
      distinctive fixture terms and then passed the maintained installed
      greenfield matrix after stale temp cleanup. The first matrix attempt
      proved all 13 standard cases at hard 10/10 with zero issues, browser
      proof, synthetic rescue, and natural rescue, but the aggregate run failed
      because an older pre-existing temp root remained under `/Users/freedom/mock`.
      After pruning that stale root, the clean rerun passed with status
      `passed`: 13/13 standard creates, hard 10/10 scores, zero quality issues,
      13/13 browser proof, generated-readback platform leakage proof across 213
      terms, temp cleanup proof with no remaining paths, 22.712s minimum,
      25.279s average, and 27.755s maximum standard create time. Synthetic
      typed-probe rescue passed in 34.454s, and real provider-backed structured
      rescue passed in 58.415s under the 90s rescue tier.
- [x] Repair scientific-depth intent and Atlas result-label custody for the
      CB-214 replay.
      A live consumer create failed before governed writes because two Atlas
      diagrams composed fixed result headers with a semantic body that already
      began with result language. The source fix keeps the final gate intact
      and moves custody earlier: Mermaid labels now use generic header/body
      composition, saved-as result-object semantics collapse generic
      result/output/outcome/artifact objects to the saved target, and the
      confirmed intent path carries optional EvaluationSemanticsIR for
      scientific, research, model, simulation, prediction, and evaluation
      requests. The host Product Intent prompt now asks for observed quantity,
      source evidence, method or model boundary, variables, baseline or
      comparison, uncertainty or tolerance, reproducibility, and excluded
      claims so post-confirm artifacts preserve depth without inventing facts.
      Focused source proof passed the Atlas/scientific replay tests, the
      45-test post-confirm quality repair suite, the 27-test live simulation
      and semantic model suite, and the 93-test confirmed diagram/recovery/
      post-confirm suite. Source-local CLI replay of the saved failed intent
      completed governed create in 25s with zero repeated result copy, and a
      second thin scientific prompt replay completed in 24s with evidence-depth
      terms present and no adjacent result/evidence duplicates. Remaining
      proof: the committed-head local release dist
      `odylith-local-release-0.1.15-9bea5784` passed source-plus-dist leakage
      proof after one transient feature-pack gzip I/O retry, installed replay
      of the saved failed intent completed create in 32s, and installed thin
      scientific propose-to-create completed in 28s. Full installed matrix
      proof remains required before broad release readiness is reclaimed.
- [x] Repair fresh scientific variance term-loss and evidence-depth scoring for
      CB-215 in source.
      Fresh scientific variance against installed dist `82c539b4` showed that
      Greenfield could still either fail before writes on clipped scientific
      prose or commit shallow scientific artifacts. The source repair keeps the
      fix generic: generated-confirmation recovery restores prompt-grounded
      material steps only for internally synthesized confirmations while
      explicit operator-edited confirmations stay authoritative; `load` is now
      a domain-neutral material action; one-word human actors can own carried
      sibling actions without letting a visible-result object become the next
      subject; rich scientific/evaluation paths preserve their concrete
      accepted first path while gaining EvaluationSemantics depth; and the
      installed matrix's independent domain-expert readback now derives
      evidence obligations from typed EvaluationSemantics fields instead of
      hard-coded phrases. The maintained matrix now includes a thin
      no-confirmed-intent assay-drift prediction prompt. Focused proof passed
      84 tests in 123.51s, including operator-edited confirmation authority and
      paraphrased IR-derived scientific evidence acceptance. Source-local
      implant-fatigue replay completed governed create in 23.93s with manifest
      passed, 3 Registry specs, 6 Atlas diagrams, retained fatigue evidence,
      scientific-depth terms present, and zero `bench-test tracks` or
      `result result`. Source-local seismic-inversion replay completed governed
      create in 24.57s with manifest passed, no clipped `Around`, no repeated
      result copy, and retained seismic/uncertainty evidence. Disposable replay
      repos were deleted after evidence capture. Source-local Registry
      forensics regeneration then passed check-only and the platform
      domain-leakage guard passed across 285 distinctive fixture terms after the
      known CB-209 pinned-runtime forensics posture risk was encountered and
      corrected. Remaining proof: rebuild a fresh dist, rerun
      high-variance installed scientific matrix with browser proof, rerun the
      maintained installed matrix with rescue proof, and verify temp cleanup and
      platform leakage before release readiness is reclaimed.
- [x] Repair the grn-sim Atlas coordinated-action label escape in source.
      The exact saved grn-sim replay exposed a second Atlas projection defect
      after the repeated-result fix: subject-stripped first-path labels could
      mix finite and base coordinated actions such as `Uploads or select`.
      The source repair removes the local Atlas action replacement table,
      routes label imperative conversion through the shared prose grammar owner,
      and adds a typed Mermaid-label public-copy guard backed by shared
      base/finite action-token classification. Read-only subagent QA then
      found that the first shared-grammar version still treated plural nouns
      such as `orders`, `offers`, `controls`, and `records` as coordinated
      verbs inside object lists. The corrected repair adds one shared
      clause-versus-object discriminator, preserving labels such as
      `Choose methods and controls for comparison` while still converting
      real action chains such as `enters a form and submits`. Focused proof
      passed the
      mixed-label quality regression and the gene-expression live simulation
      regression. A fresh source-local replay of the saved grn-sim confirmed
      intent completed governed create in about 24.00s with final manifest
      passed, issue_count 0, 4 backlog records, 5 Registry components, 6 Atlas
      diagrams, Registry validation passed, Atlas render passed, and zero
      repeated-copy or known clipped-copy signatures across 40 generated files.
      A later local source pressure test found one more over-preservation
      ambiguity, so leading action chains such as `checks and controls for
      drift` now stay action coordination while plural object lists remain
      intact.
      Fresh working-tree local-release proof then passed the maintained
      installed matrix from
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-label-qa2`:
      14/14 varied standard creates scored hard 10/10 in 23.594-28.426
      seconds, browser proof passed for every generated repo, synthetic rescue
      passed in 34.934 seconds, natural structured rescue passed in 66.245
      seconds, platform domain-leakage proof passed across 213 generated
      readback terms, and temp cleanup had no remaining roots. Remaining proof
      is final release-level: after checkpoint spacing permits commit/push,
      rebuild a committed-head dist and rerun the maintained installed matrix
      before claiming release posture.
- [x] Implement completion-priority quality-debt custody for non-critical
      projection defects.
      Product priority was clarified: post-confirm governed record creation is
      the first invariant, while premium artifact quality remains mandatory and
      visible as debt when it is not clean. The root cause was two-layered:
      `run_greenfield_post_confirm_engine` refused to return when only typed
      rendered-projection quality findings remained after repair/rerender
      no-progress, and `write_greenfield_proposal` could still raise inside
      `GreenfieldApplyTransaction` on component-spec, next-step, or final
      package quality after records were staged, rolling everything back. The
      source fix adds a `passed_with_quality_debt` manifest state for typed,
      non-critical, projection-owned debt only. Critical, semantic, Tribunal,
      release, untyped, and quality-lens findings still block. Final writes
      carry the same policy and record `completion_priority.final_write_quality_debt`
      instead of erasing the project for late persisted-projection polish
      failures. This is explicitly not a clean premium pass; it is governed
      completion plus an exact debt ledger. Focused proof passed the new engine
      debt regression plus semantic/no-executable hard-blocker checks, the full
      post-confirm engine suite, the projection-rerender and quality-repair
      pack, selected package hard-blocker checks, and two apply-level create
      regressions proving prewrite-detected component-contract debt and
      final-write-only next-step debt both commit governed records while
      exposing the debt in the manifest.
- [x] Fix source-grounded control-plane homonym false positives.
      A disposable source-local landslide validation create exposed CB-216:
      a legitimate domain word that is also an Odylith surface name was
      present in accepted intent, but the quality gate's trusted term cone was
      too narrow and truncated ordered source terms to twelve entries. The
      gate then misclassified the grounded homonym as Odylith control-plane
      leakage and stopped before governed writes. The fix expands the trusted
      source cone to structured accepted-intent fields and removes the
      arbitrary top-term cap, while preserving ungrounded Radar, Registry,
      Atlas, Compass, and Tribunal leak rejection. Targeted proof passed the
      homonym allowance and ungrounded control-plane rejection tests, and the
      original disposable create then completed in 27.511 seconds outer time
      with manifest passed, validation passed, issue_count 0, committed write
      transaction, 4 backlog records, 3 components, 6 diagrams, and temp
      cleanup.
- [x] Fix confirmed-intent inline label parsing before semantic projection.
      Fresh scientific variance reopened CB-206 because the Markdown
      confirmed-intent loader recognized heading-only sections but not common
      inline label-value rows such as `Title: ...`, `State object: ...`,
      `First complete path: ...`, and `Proof boundary: ...`. The accepted
      intent was therefore contaminated before the semantic compiler saw it:
      title labels leaked into title text, state/proof copy moved into adjacent
      fields, and the generated package failed on actor-role semantic slop plus
      First Path Sequence tail loss. The fix extracts confirmed-intent section
      parsing into `greenfield_confirmed_intent_sections.py`, supports both
      heading sections and inline label rows, and leaves
      `greenfield_confirmed_intent.py` below the 800-line soft limit. Targeted
      regression proof passed, and the exact source-local scientific replay
      completed in 29.768 seconds with a clean passed manifest, zero issues,
      committed write transaction, 4 Radar workstreams, 4 Registry specs,
      6 Atlas diagrams, and temp cleanup.
- [x] Make specialized Registry component contracts semantic-first.
      The broader source-local quality suite exposed a remaining CB-217
      mechanism after the proof-floor fix: specialized document/status profiles
      could still replace ready semantic component contracts, flatten protected
      source phrase surfaces, and bury explicit proof-boundary/access
      obligations after supplemental profile proof rows. The fix keeps
      `greenfield_component_contract.py` below the 800-line guard, moves source
      phrase restoration and proof-row ordering into
      `greenfield_component_semantic_contract_support.py`, and makes ready
      semantic contracts authoritative while profiles provide fallback fields or
      supplemental proof only. Targeted profile/proof regressions passed, and
      the widened greenfield quality suite passed 129 tests in 28.00 seconds.

- [x] Make shared confirmed title labels context-aware instead of globally
      splitting or preserving hyphenated tokens.
      The widened confirmed-surface suite exposed a CB-198 label-custody
      failure where `revision-round management` was flattened by an over-broad
      human-label splitter, while the first fix over-preserved object labels
      such as neck-pain timelines and titration-schedule models. The confirmed
      text owner now uses adjacent title-token context to split human-role and
      object-head compounds while preserving source-owned workflow compounds.
      Focused label regressions passed 23 tests in 15.71 seconds, and the
      widened confirmed artifact suite passed 74 tests in 631.93 seconds.
- [x] Add retained evidence and seeded install mode for hundreds-scale
      high-variance greenfield simulation.
      The first external 30-case sweep proved that one-off temp repo cleanup
      was correct for disk pressure but insufficient for brutal post-run
      assessment: once repos were deleted, only aggregate matrix JSON remained.
      The harness now persists per-case evidence before cleanup, including case
      metadata, prompt/intent hashes, artifact inventories, artifact hashes and
      excerpts, full-readback grounding for required terms, quality findings,
      browser proof state, and post-confirm manifest summaries. Seeded install
      mode installs Odylith once per batch, clones mutable repo state per case,
      symlinks the immutable runtime, and still deletes each project after
      evidence capture. The install/matrix/leakage/preflight test slice passed
      106 tests in 8.82 seconds.
- [x] Separate volume-discovery scoring from complete browser release proof.
      Independent review of the first seeded 30-case proof found a false
      confidence mechanism: the top-level JSON honestly reported browser proof
      as skipped, but per-case quality scores still awarded
      `browser_surface_proof: 10` and printed the full brutal release-quality
      explanation. The scoring owner now marks unrequested browser proof as
      unscored, excludes that optional dimension from the discovery score,
      records `score_basis=volume_discovery_without_browser_surface_proof`,
      and explains that the run is volume-discovery evidence rather than full
      browser release proof. Focused scoring regressions passed 4 tests in
      0.20 seconds.
- [x] Preserve source-grounded command targets and homonym context in
      high-volume greenfield recovery.
      Seeded batch three found six quality failures where governed records were
      written but project frames collapsed from source-grounded targets such as
      `weather radar calibration setup` and `geologic atlas field mapping
      setup` into generic outcome workspaces. The repair keeps command-led
      prompt targets before sentence boundaries as canonical project frames,
      validates control-plane homonyms through local accepted-source context
      instead of literal term membership, blocks object-list fragments from
      becoming supplemental actors, and restores readable title splitting for
      source shorthand. The matrix evidence harness now records scored
      generated-surface required-term grounding separately from runtime-only
      accepted-project grounding. Focused proof passed six homonym/title/evidence
      tests, five prior recovery regressions, four install evidence/scoring
      tests, py_compile, and the full confirmed-intent recovery suite passed
      48 tests in 151.01 seconds.
- [x] Repair high-volume duplicate-copy semantic ingress instead of Atlas or
      Registry renderer patches.
      External high-variance batch one found 12 real no-write failures in
      scientific domains, all sharing adjacent duplicate accepted-path copy
      such as `review review`. The root cause was not domain vocabulary or a
      diagram renderer; duplicate copy entered the accepted intent before
      semantic projection. Shared confirmed-text and first-path ingress now
      dedupe adjacent words before the semantic compiler or artifact renderers
      see them. Representative source-local replays for climate data
      assimilation, battery electrolyte degradation, and plasma confinement
      shot planning committed governed records with passed manifests, zero
      issues, and no repeated review copy.
- [x] Tighten actor completion and specialized component contract custody after
      broader runtime quality proof.
      The wider runtime greenfield suite exposed remaining semantic overreach:
      actor completion over-mined rich accepted actor lists, hyphenated actor
      labels rendered awkwardly, context proof labels carried hyphenated
      carrier copy, blind proof-row selection could hide access obligations,
      and status/document profile transition summaries could drop important
      states. Actor completion now treats rich operator actor lists as
      authoritative, derives missing actors from first-path evidence only when
      the accepted actor set is absent or thin, naturalizes display labels at
      render boundaries, selects proof rows by category, naturalizes proof
      carrier compounds in component narratives, and merges semantic/profile
      transition fragments before lifecycle summarization. Runtime proof passed
      179 greenfield quality tests in 302.68 seconds.
- [ ] Run the fresh committed-code local dist through hundreds-scale seeded
      high-variance installed sweeps.
      Use the four 30-case external batches as the first 120-case sweep, retain
      per-case evidence JSON, delete every temp project after evidence capture,
      and treat any create failure, quality debt, browser-proof failure,
      platform leakage, or timing breach as a new Casebook/plan learning before
      the next fix pass. Expand with additional random domains only after the
      first 120 cases are clean or the next root-cause fix is landed.
      Shard-06 source-local repair is now proven for the public-records and
      emergency-radio failures: prompt-source workflow clauses, non-goal
      visible-result tails, standalone system labels, and hyphen-label custody
      were corrected with focused regressions and exact source-local replays.
      The next proof step is a fresh working-tree dist plus shard-06 rerun
      before expanding to more unseen batches.
      The first fresh shard-06 installed rerun proved those two cases but
      exposed two more no-write modal/base-form failures in municipal
      stormwater and tribal consultation workflows. Source-local repair now
      bounds the `where <actor> <action>` shortcut to complete actor roles and
      direct transformation or single-step record workflows, with the full
      confirmed-intent recovery suite green. A second fresh dist and shard-06
      rerun remain required before expanding volume.
      That second installed rerun exposed a governance-custody failure before
      project execution: Registry Requirements Trace had copied raw Compass
      proof summaries into public component specs, so shard-domain labels leaked
      into platform contract surfaces. Requirements Trace now uses neutral
      evidence projection, retaining event kind, workstream scope, and artifact
      counts without raw scenario prose or artifact paths. Focused sync/leakage
      proof passed 37 tests, Registry sync regenerated the affected specs and
      forensics sidecars, and the selected shard-06 source leakage scan passed
      with 51 distinctive terms and zero findings. A fresh dist and installed
      shard-06 rerun are still required before moving to the next unseen batch.
      The fresh dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-high-volume-shard06-workflow-registry-fix`
      then passed shard-06 installed: 30/30 projects completed governed writes,
      zero issues, all scored quality dimensions at 10/10, product-manager,
      architect, engineer, and domain-expert lenses green, every create under
      60s with range 25.682-33.607s and average 28.031s, generated-artifact
      platform leakage passed across 43 terms, and temp cleanup left no matrix,
      rescue, source, debug, or sim roots. Browser proof was intentionally
      unrequested and remains unscored, so this is high-volume discovery proof.
      Continue with fresh shard-07 and shard-08 domains before claiming broader
      release confidence.
      The first shard-07 attempt failed before project execution on another
      leakage-sentinel false positive: a declared short platform-native phrase
      was accepted as project-domain vocabulary and collided with legitimate
      Odylith analysis code. Sentinel selection now rejects one- or two-token
      declared phrases made entirely from platform-native/common tokens while
      preserving richer project phrases and explicit longer fixtures. Platform
      leakage tests passed 32/32, and the shard-07 selected source+dist scan now
      excludes the false sentinel, retains 47 distinctive terms, and has zero
      findings. Rerun shard-07 installed before expanding to shard-08.
      The shard-07 installed rerun then passed 30/30 projects with zero issues,
      all scored dimensions at 10/10, all expert lenses green, create timing
      25.489-30.954s with average 27.809s, generated-artifact leakage passing
      across 37 terms, and temp cleanup leaving no simulation roots. The current
      fresh dist therefore has 60/60 clean high-volume discovery projects across
      shard-06 and shard-07, with browser proof intentionally unrequested and
      unscored. Run shard-08 next before any 100+ claim.
      Shard-08 then failed 3/30 installed projects on a fresh unseen batch:
      two project-brief command prompts repeated a boundary word between the
      focus label and first actor, and one final/preview package carried
      clipped source-launch readiness and risk copy into implementation prompts,
      operator next steps, accepted-project memory, and dashboard preview. The
      source repair stays generic: command prompt labels are suppressed only
      when label-tail and prompt-head collide, readable project outcomes avoid
      title/state cross-sentence duplication and restore terminal punctuation,
      source-launch prompt fragments trim terminal keep/return tails and
      incomplete risk clauses, and final next-step readiness gates are
      preview-sanitized before memory projection. Focused proof passed the full
      project-brief/source-launch slice, 26 tests in 3.61 seconds. Exact
      source-local replays
      for volcanic ash aviation advisory, solid organ transplant allocation,
      and offender reentry service plan all committed governed records under
      31 seconds with clean scans, and the final reentry replay had no
      completion-priority debt. Rebuild a fresh dist from this source before
      rerunning shard-08, then rerun shard-06 and shard-07 on that same dist
      before claiming any current-build 100+ volume proof.
      Fresh dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-high-volume-batch08-fix-20260703a`
      then passed shard-08, shard-06, and shard-07 cleanly, 90/90 projects
      with zero issues and all creates under 60 seconds. Shard-05 exposed the
      next systemic defect before the 120-project claim could be made:
      `aquifer nitrate plume` failed before governed writes because
      `Hydrogeologist Hydrogeologist` reached next steps, project implementation
      prompts, dashboard preview, Radar workstream source, Radar index, and
      prewrite Radar package. This makes the current proof 119/120 attempted,
      not a pass. Diagnose and fix semantic actor/title ownership for
      "where the <actor> turns an ambiguous <object> into..." scientific-object
      prompts without adding domain vocabulary, weakening duplicate gates, or
      patching rendered files after projection; then exact-replay the aquifer
      prompt source-locally, rebuild, rerun shard-05, and only then combine the
      four shard summaries.
      Source diagnosis found the generic owner: `workflow_title_action()` could
      fall back to an imperative action that still began with the actor when the
      actor-owned fragment splitter had no clean step boundary. The title
      composer then added `Let {actor}` again. The source fix strips an
      already-owned actor prefix from fallback title actions before composition,
      avoiding rendered-copy repair and domain vocabulary. Focused proof passed
      the new actor-prefix regression and adjacent actor-led workflow regression
      (`2 passed`), the broader project-brief/source-launch/workstream-title
      slice (`29 passed in 4.10s`), and exact source-local aquifer replay with a
      passed standard manifest, zero issues, 4 Radar rows, 3 Registry components,
      6 Atlas diagrams, and no `Hydrogeologist Hydrogeologist` hits. Rebuild the
      local dist next, rerun shard-05, then scale to sharded 100+ volume only
      from the fresh fixed package.
      A corrected four-shard installed sweep against fresh dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-high-volume-actor-prefix-20260703a`
      ran 120 projects and did not pass: 110 were clean premium passes, 10 were
      failures or quality debt, average create time was 34.959s, max create time
      was 37.521s, zero creates exceeded 60s, cleanup passed, and leakage proof
      passed. Browser proof was intentionally disabled for this volume-discovery
      sweep. The new blockers are platform classes, not project-local defects:
      mixed-case source token drift (`Cryo-EM` -> `cryo-EM`), gerundized
      actor-role customer copy, Tribunal role projection collapse across five
      domains, clipped component-contract noun slots, and two
      `passed_with_quality_debt` validation failures. Do not scale the next
      hundreds run until the failed ten cases replay cleanly from source and a
      fresh package reruns the same four shards without quality debt.
      A later disjoint 120-case sweep against
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-high-volume-20260703c`
      reached 119/120 clean premium case-quality passes with average create
      time 42.649s, max 52.471s, and zero creates over 60s, but still failed
      one scientific lower-first source-symbol case because the final write
      path restored accepted-project visible actors to source casing while the
      returned create payload reused the raw Tribunal gate. The fix keeps one
      source-cased validation-gate mapping for returned payload, durable
      accepted-project memory, and final package preview. Focused proof passed
      34 source-casing and adjacent rendering tests. The same run exposed a
      harness-only false positive: parallel wrappers must not share one
      `TEMP_PARENT`, because cleanup proof treats live sibling shard roots as
      leftovers. Rebuild the dist from this source fix, rerun the exact failed
      case, then rerun high-volume shards with isolated temp parents before any
      current-build 100+ or hundreds-scale claim.
    - 2026-07-03 high-volume latency drift blocker:
      fresh dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-high-volume-20260703d`
      passed the exact mRNA replay in 31.456s and passed the disjoint
      `/private/tmp/odylith-high-volume-20260703f/results/full-d` corpus at
      120/120 hard 10/10 with average create time 43.396s, max 50.036s, zero
      over 60s, and clean isolated cleanup. The next distinct corpus
      `/private/tmp/odylith-high-volume-20260703f/results/full-a` failed the
      release-quality latency gate: 104/120 clean passes, 16 create times over
      60s, average 46.701s, p90 61.421s, p95 64.850s, max 69.970s, and cleanup
      still passed. All failed cases wrote quality-complete artifacts with
      product-manager, architect, engineer, and domain-expert lenses green; the
      only failing dimension was standard-path latency. Failures clustered late
      in each 30-case shard, mostly positions 24-30, so the next work must
      distinguish serial single-case cost from parallel shard/runtime pressure
      and then remove standard-path work from `greenfield create`. Do not treat
      104/120 as success, do not raise the normal 60s budget, do not reclassify
      these as rescue-tier work, and do not add domain-specific exceptions.
      Serial isolation then showed the 16 failed cases are not intrinsically
      over budget: the worst single replay passed in 45.832s and the full
      16-case serial replay passed 16/16 with hard 10/10, average 47.665s, max
      54.045s, zero over 60s, and clean cleanup. Late-case artifact byte volume
      and trace breadth did not explain the four-way failures. Treat the
      four-shard result as concurrency stress, not normal operator-path proof;
      rerun the second corpus with controlled concurrency before making a
      current-build 240-project claim.
      Controlled rerun of the same second corpus is now clean: two waves with
      two shard workers at a time passed all 120 Corpus A projects with hard
      10/10 quality, zero issues, average create time 43.232s, p90 50.230s,
      maximum 52.889s, zero over 60s, and clean cleanup. Together with the
      disjoint Corpus D 120/120 result, the installed high-volume discovery
      evidence now covers 240 distinct prompts under controlled concurrency.
      This is strong operator-path discovery evidence but still not full
      release proof because browser proof and natural rescue were intentionally
      disabled.
    - 2026-07-03 Registry semantic/profile merge hardening:
      source-side review of the post-latency cleanup found a CB-217-class
      adjacent regression before release: specialized document-context profile
      obligations could survive the semantic contract builder but be trimmed
      by the merge cap or hidden by Registry narrative similarity ordering.
      The fix moved merge/floor ownership into the semantic-contract support
      owner, preserves all semantic fragments while appending bounded profile
      supplements, narrows profile-preservation guards to material
      document-context fields rather than proof-floor boilerplate, and ranks
      missing/blocked obligations ahead of low-risk metadata in the narrative
      view. Focused proof passed `57 passed in 28.82s` across source-casing,
      specialized profiles, post-confirm repair, profile ownership, and the
      confirmed-create Registry spec assertion. This fix remains generic and
      does not add domain vocabulary to Odylith.
    - 2026-07-03 Corpus G first-tranche actor/action repair:
      a new 300-case Corpus G was generated with ten unseen 30-case shards.
      The first two corrected shards against working-tree dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-high-volume-20260703e`
      exposed 20/60 failures or score blockers: fifteen modal/base-form
      no-write failures, three accepted-project final-memory punctuation
      no-write failures, one maternal-referral domain-term miss, and one
      61.106s latency breach. The failures were generic actor/action custody
      defects, not domain gaps. The source fix keeps ownership before render:
      actor labels split modal action tails through the shared modal boundary,
      confirmed actor completion strips modal subject tails and avoids duplicate
      derived labels, and prompt-source recovery now prefers bounded
      path-grant and direct transformation workflow actors before expert-lens
      sentences. Focused proof passed the actor/prompt-source slice
      (`14 passed in 32.20s`), and representative source-local replays for
      nine failed or near-failed prompts completed governed writes with passed
      post-confirm manifests, committed write transactions, and all required
      readback terms present. Do not claim current-build hundreds proof from
      this source-local pass; rebuild a fresh dist, rerun the failed subset and
      shards 01-02 through the matrix, then continue controlled-concurrency
      unseen shards.
    - 2026-07-03 tiered campaign harness hardening:
      the high-volume runner now separates discovery proof from release proof
      instead of relying on final-only shard JSON and shell convention. The
      matrix runner emits per-case JSONL telemetry, persists a `campaign`
      summary with failure clusters and stressor coverage, supports explicit
      discovery/release tiers, and rejects release-tier runs that try to use
      seeded installs, skipped browser proof, or early-stop thresholds. A new
      tiered campaign runner executes failed-subset replay, 60-case regression,
      volume discovery, and strict release proof in order with controlled
      discovery concurrency and stop-before-next-tier behavior after failures.
      It reports release proof completion, release proof status, and release
      readiness status separately from selected-tier campaign pass/fail, so a
      successful discovery-only run stays explicitly non-release-ready.
      This is an execution-quality improvement, not a generator shortcut:
      discovery evidence remains non-release proof until a full-install,
      browser, and natural-rescue release tier passes. Focused harness proof
      passed `92 passed in 0.78s`, `py_compile`, and shell syntax checks.
    - 2026-07-03 incremental campaign progress implementation:
      the tiered campaign runner now owns merged progress files in addition to
      per-shard telemetry. It tails each shard's case events, writes
      append-only `campaign-progress.v1.jsonl`, maintains a live
      `campaign-progress.v1.json` aggregate snapshot, and carries cross-tier
      failure-cluster summaries into final campaign JSON. Pending shards stop
      after a shard or cluster threshold, and in-flight sibling shards receive
      a tier stop signal so the discovery lane stops spending time after a
      root-cause class is visible. The sharder now emits variance evaluation
      by tier, including stressor coverage ratio, density, low-depth cases,
      and dominant stressors, so high-volume proof is not measured by raw case
      count alone. The campaign wrapper now runs release component-forensics
      and Chromium preflight before release-proof shards, matching the
      standalone release gate. Focused proof passed the campaign/sharder/proof
      suite (`22 passed in 0.50s`) plus Python compile checks, and a real
      external 72-case metadata sharder smoke produced observable shards. This
      is harness discipline only; it does not close the remaining greenfield
      generation defects discovered by the current variance campaign.
    - 2026-07-03 live campaign stop and direct release policy tightening:
      the merged progress stream is now an execution-control input, not just
      an observability artifact. The campaign progress owner records
      telemetry-derived tier stop decisions, emits the stop reason into progress
      snapshots, gives the origin shard a short grace window to finish writing
      its result JSON, interrupts sibling shards, and carries the live stop
      reason into final tier output. Failure clusters now prefer typed manifest
      issue signatures and concrete blocker text before score buckets, and the
      sharder can replay failures from top-level campaign cluster summaries.
      Direct matrix release-tier invocation now rejects missing browser proof,
      installed rescue smoke, or natural rescue proof, so release custody does
      not depend on using the campaign wrapper. Focused proof passed the
      campaign/sharder/natural-rescue/bootstrap suite (`27 passed in 0.51s`),
      the broader matrix unit file (`69 passed in 0.42s`), combined
      runner/matrix proof (`87 passed in 0.74s`), Python compile checks, and
      Bash syntax checks. This still does not prove post-confirm artifact
      quality for the latest failed high-variance tranche; it makes the next
      failed-subset replay and hundreds-scale campaign stop sooner and explain
      failure classes more accurately.
    - 2026-07-03 first-path requirement-control and Atlas coverage repair:
      failed-subset replay proved the harness was now surfacing the right
      generator defect. Quantum repeater v2 completed source-local create, but
      fusion plasma v2 still failed before writes because a modal requirement
      sentence became a `Workflow` event and visible result `the next path`,
      then Atlas and accepted-project memory leaked mixed finite/base labels.
      The source repair keeps the fix in typed semantic/projection custody:
      requirement-control clauses with product/control subjects are filtered
      from `FirstPathContract.events` only when material path actions remain,
      review terminal steps can own visible results, temporal `before
      reviewing...` tails split from rich material heads, subjectless Atlas
      labels normalize coordinated finite/base actions before Mermaid render,
      and Atlas coverage checks compare structured FirstPathContract projection
      facts rather than raw capability prose. Focused proof passed first-path
      semantics (`14 passed`), full slop regressions (`113 passed`),
      diagram/package suites (`98 passed`), and campaign/matrix tests
      (`96 passed`). Exact source-local replays passed for quantum repeater
      and fusion plasma in 27.086s and 35.305s with governed Radar, Registry,
      and Atlas records written and disposable repos deleted.
    - 2026-07-03 installed failed-subset proof plus campaign temp isolation:
      the fresh dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-requirement-control-20260703`
      passed the exact installed failed subset for quantum repeater v2 and
      fusion plasma v2 with governed writes, zero issues, hard 10/10 scored
      quality, all expert lenses green, and create times of 31.806s and
      39.419s. The follow-up 60-case campaign correctly stopped, but the
      actionable defect was in the harness: shard 002 had 6/6 passed cases and
      no failure clusters, yet returned failed because cleanup proof inspected
      the shared campaign `TEMP_PARENT` while shard 001 was still active. The
      campaign runner now assigns an isolated temp parent to each shard,
      precleans stale copies of that shard scope, records the temp scope in
      progress/result payloads, and removes the shard temp parent after
      completion or interruption. Focused proof passed the campaign-runner
      tests (`10 passed`) plus Python compile checks. Next proof is to rerun
      the 60-case campaign with isolated shard temp parents, then resume
      broader unseen controlled-concurrency shards.
    - 2026-07-03 tiered replay and actor-led product-view repair:
      the campaign harness now has a dedicated merged progress owner, live
      per-case telemetry flushing, stable failed-subset replay identity
      (`case.id`, slug, prompt hash, confirmed-intent hash), tier-specific
      worker policy, and an explicit 240-case discovery tier between the
      120-case discovery lane and strict release proof. Live failure clusters
      are preserved in final tier output even when interrupted shard result
      files are incomplete. The next generator failure in the 60-case tier was
      repaired at the semantic source: actor-led open actions now have a
      domain-neutral owner used by first-path semantics and confirmed
      completion text, preventing valid actor-led first-path clauses from
      falling back to later homonym object actions in product-view copy.
      Focused proof passed campaign/progress tests (`29 passed`), first-path
      plus post-confirm slop tests (`56 passed`), Python compile checks, and
      source-local exact replay with final manifest passed and zero issues.
      Remaining proof is still installed: rebuild a fresh dist, rerun the
      exact failed subset, then resume the 60-case tier before broad 120/240
      discovery or release-readiness claims.
    - 2026-07-03 installed 60-case discovery and sentinel distinctiveness:
      the working-tiered-replay dist passed the exact installed robotics
      failed-subset replay in 37.414s with governed writes, hard 10/10 scored
      quality, zero issues, and all expert lenses green. The resumed 60-case
      campaign then stopped on shard 010 before project execution because
      platform leakage preflight accepted a low-distinctiveness declared
      sentinel composed only from platform-native governance words. The fix is
      kept in harness vocabulary custody: short declared leakage sentinels made
      only from platform-native/common terms are rejected before source/dist
      scanning, while project-specific declared phrases remain authoritative.
      Focused leakage proof passed, shard 010 reran 6/6 clean, shard 009 reran
      6/6 clean, and combined aggregate-plus-rerun evidence covers 60 unique
      high-variance cases with zero failed result records and no generated
      project temp roots under `/Users/freedom/mock`. This remains discovery
      proof because browser and natural rescue were deliberately skipped.
      Fresh rebuild
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-tiered-replay2-20260703`
      passed build-time platform leakage, checksum, installer syntax, archive
      readability, and a 7-case selected installed package proof covering the
      exact actor-led replay plus the leakage-sentinel tranche. The selected
      package proof had 7/7 governed writes, hard 10/10 scored quality, zero
      issues, all expert lenses green, max create time 37.229s,
      generated-readback leakage proof passing, and temp cleanup passing.
      The full available 72-case high-variance volume-discovery tier then
      passed on the same fresh package with two-shard concurrency and stop
      thresholds active: 72/72 governed writes, zero issues, zero failure
      clusters, hard 10/10 scored quality for every case, max create 39.321s,
      average 33.575s, p95 38.143s, and no temp simulation roots. The corpus
      covered every tracked stressor class. Remaining proof: run strict
      browser/natural-rescue release proof, then expand to larger 120/240
      unseen corpora after release proof is green.
    - 2026-07-03 strict release-proof natural-rescue blocker:
      strict release proof against the same fresh package kept the release gate
      honest. Twelve release-proof standard cases, browser proof, platform
      leakage proof, temp cleanup, and synthetic rescue passed, but natural
      host-planned rescue failed before governed writes. The final manifest
      carried one `structured_rescue_semantic_patch` operation for
      `SemanticModelIR.domain_ontology.external_systems`; the Tribunal patch
      planner returned `provider_failed` because Codex CLI exceeded 45 seconds,
      so no provider-authored operation could be merged and the transaction
      correctly refused to write records. Next implementation work is to reduce
      the structured rescue prompt/planner latency and improve provider-failure
      handling without weakening the typed semantic-patch requirement, without
      treating synthetic rescue as release proof, and without raising the
      standard 60-second path budget.
    - 2026-07-04 source-anchored structured-rescue fallback:
      local-provider probes proved the latency blocker was architectural, not
      just prompt size: Codex CLI and Claude Code CLI can time out on tiny
      schema-bound structured patch requests. The rescue planner now keeps host
      reasoning first, but exact source-owned semantic PatchSet operations use
      a 12s provider window before a source-anchored fallback applies the
      current SemanticModelIR fact with a decision ledger and
      `structured_patch_fallback` manifest metadata. Campaign evidence was also
      corrected so final failure-cluster summaries do not double-count tier and
      shard aggregates, and preflight `tier_completed` snapshots retain shard
      counts and cluster counts. Focused proof passed the rescue, Tribunal,
      semantic patch, campaign runner, sharder, natural-rescue, and proof-scope
      suites (`68 passed in 0.83s`), compile checks, and `git diff --check`.
      Source-local natural-rescue proof completed in 43.439s with final
      manifest passed, governed writes committed, provider timeout recorded at
      12.0s, and `structured_rescue_semantic_patch` repaired.
    - 2026-07-04 strict installed fallback release proof:
      fresh working-tree dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-tiered-rescue-fallback-20260704`
      passed build leakage, checksum, `install.sh`, wheel, and runtime archive
      verification. Strict campaign proof
      `/tmp/odylith-tiered-rescue-fallback-release-campaign.v1.json` completed
      with `release_readiness_status=proven`, no failure clusters, and 12/12
      full-install release cases passing with browser proof and zero issue rows.
      Standard create timings were 30.674-40.448s. Synthetic rescue passed, and
      natural rescue committed governed writes with `cli_create_seconds=67.639`,
      manifest elapsed 40.888s, provider timeout recorded after 12.0s, and
      `structured_patch_fallback.status=applied`. Remaining release work is
      checkpoint/publish custody, not another source-fix blocker from this proof.
    - 2026-07-04 campaign blocker extraction checkpoint:
      the tiered campaign harness now preserves multiline final-gate blocker
      structure while deriving replay clusters, so exact failed-subset replay
      is driven by concrete post-confirm issue text instead of generic
      `issue(s)` wrappers. This is a harness-quality fix, not a generator
      shortcut: per-case incremental matrix payloads, merged campaign progress,
      failed-subset/60/120/240/release tiers, stressor coverage, live stop
      thresholds, isolated shard temp scopes, and discovery-versus-release
      separation remain in force. Focused proof passed 29 campaign/sharder
      tests, the 108-test install/matrix suite, compile checks, command-help
      checks, and diff hygiene. The next implementation step remains the
      generic actor-led product-view repair exposed by the current 120-case
      discovery stop, followed by exact replay and resumed discovery.
    - 2026-07-04 reviewer hardening checkpoint for campaign correctness:
      independent read-only review found that leakage verdicts were applied
      after live telemetry, cleanup could raise before partial-result flush,
      wrapper debug skips could still request invalid release proof, and shard
      temp cleanup errors were swallowed. The harness now applies generated
      platform-leakage verdicts per case before telemetry/stop/flush, persists
      partial result JSON before generated-repo cleanup, records cleanup failure
      as a failed proof result, downgrades any explicit browser/rescue/natural
      rescue skip to discovery proof in the standalone wrapper, and converts
      shard temp cleanup failure into a `campaign.shard-temp-cleanup-failed`
      cluster. Focused reviewer tests passed (`26 passed in 1.13s`), compile
      and shell syntax checks passed, and the widened install/matrix suite
      passed (`111 passed in 1.33s`).
    - 2026-07-04 actor-led product-view and tiered harness completion:
      current source now repairs the latest 120-case discovery blocker at the
      semantic projection owner. Product-view copy uses shared actor-led action
      parts before generic user-capability wrapping, and result-list noun
      disambiguation keeps review/evidence/proof outcome phrases as visible
      result objects rather than actor-led actions. A second harness review also
      closed exception telemetry, release-proof stressor coverage, and
      duplicate-name failed-subset replay risks. Focused proof passed the new
      harness reviewer regressions (`4 passed`), the full harness suite (`115
      passed in 1.66s`), the Greenfield semantic/source pack (`159 passed in
      84.25s`), and the combined focused suite (`273 passed in 85.49s`), plus
      compile, shell syntax, and `git diff --check`. Exact source-local replay
      of the failed actor-led product-view case completed governed create in
      41.607s with returncode 0, no actor-led `user can` slop, no `result
      result`, and the disposable repo deleted. Remaining verification is
      installable-dist replay of the failed subset and resumed 120/240
      discovery before any release-readiness claim.
    - 2026-07-04 source-case provenance checkpoint:
      the resumed controlled volume campaign passed 40/40 installed cases
      before stopping on shard 008 due to invalid evaluator metadata, not a
      post-confirm artifact failure. The source corpus declared `inspection` as
      a required term for `restaurant health reinspection`, but the case prompt
      grounded only `reinspection` and `inspector`, making the domain-term proof
      impossible. The harness now centralizes required-term grounding in the
      case-file loader, rejects ungrounded required terms before the sharder
      writes any tier files, keeps exact source terms valid, and gives
      pre-result shard exits a `campaign.shard-process-failed` cluster with
      tail-preserved stderr. Focused proof passed 95 harness/matrix tests plus
      compile checks. Live proof rejects the stale Corpus G source file before
      shard output and clusters the stale shard failure with the exact bad term.
      Remaining execution work is to rebuild corrected high-variance source
      cases from source-grounded terms, rerun the repaired shard subset, and
      resume 120/240 discovery only after the case-source preflight is clean.
    - 2026-07-04 replayable campaign failure-response checkpoint:
      a follow-up read-only reviewer found that the new stop-fix-replay loop
      could still break when a child shard died before writing a normal result
      payload, because the parent could advertise unreadable
      `failed_result_jsons` and the sharder would fail before exact replay.
      The same review found that interrupted sibling shards without failure
      evidence could pollute failed-subset inputs, release-proof preflight
      aborts were labeled as completed release proof, temp cleanup proof missed
      stale files and symlinks, and campaign summaries still lacked failure
      outcomes by stressor class. The harness now has a dedicated
      `greenfield_matrix_failure_response.py` owner, writes replayable
      synthetic shard payloads with source case IDs, stressor tags, and prompt
      fingerprints for pre-result failures, excludes evidence-free interrupted
      siblings from failed-subset replay, marks release preflight aborts as
      not completed proof, treats stale matching files/symlinks as cleanup
      failures, and reports stressor-class outcomes plus stressor-tagged
      failure clusters. Focused proof passed 53 reviewer-boundary tests, the
      134-test install/greenfield harness pack, compile, shell syntax, scoped
      diff hygiene, and a disposable fake-dist campaign smoke that intentionally
      failed installation while flushing progress, failure clusters, and a
      required failure-response packet without claiming release readiness.
    - 2026-07-04 rendered projection and replay identity checkpoint:
      reviewer-driven hardening found two platform defects outside the previous
      generator fix. The semantic compiler scanned source intent/backlog fields
      but missed rendered package roots such as project brief, accepted project,
      dashboard, and operator prompts; and failed-subset replay could miss
      cluster-only failures for no-id cases after no-ID dedupe moved to prompt
      fingerprints. Source now adds a recursive projection-surface scanner,
      applies proof-as-result rejection only to public rendered surfaces while
      preserving legitimate proof/evidence fields, treats `repo_name` as
      structural metadata rather than public prose, matches weak display names
      only when no stronger identity exists, and removes `/Users/freedom/mock`
      as a generic temp default from wrappers and source defaults. Focused
      proof passed the semantic/projection/sharder/bootstrap/wrapper pack
      (`120 passed`), the metadata false-positive focused pack (`29 passed`),
      compile checks, a clean source-local sports-concussion create in 39.48s
      with governed records written and no quality debt, and a two-case tiered
      smoke where failed-subset, 60-case regression, 240-case discovery,
      release-proof, and volume-discovery tiers all passed. This is source and
      harness proof only; release readiness still requires fresh installable
      dist proof with browser and natural rescue enabled.
    - 2026-07-04 runtime-quality semantic ownership checkpoint:
      broad runtime-quality proof after the harness work exposed four remaining
      source defects in SemanticModelIR and first-path copy custody: approval or
      review artifacts could become actors, material object-list outcomes could
      be skipped because the surrounding clause also carried release/scope
      language, actor-role phrases beginning with action-shaped words could be
      nominalized as the wrong verb, and storage/custody evidence could outrank
      the visible product outcome. The repair keeps the fix in generic semantic
      ownership rather than rendered text: actor completion treats approval
      artifacts as artifact context, visible-result selection admits material
      object-list and reviewable outcomes before proof-boundary fallback,
      action-result nominalization disambiguates actor-role nouns from leading
      verbs, and supporting storage/custody evidence is demoted below terminal
      product outcomes. Focused proof passed the actor-label and semantic
      compiler regressions plus live simulations (`43 passed in 323.42s`), the
      runtime-quality pack (`71 passed in 903.36s`), and the final focused
      semantic-quality pack (`31 passed in 51.71s`). Remaining work is to rerun
      the installed high-variance tiers and strict release proof from a fresh
      dist before any release-readiness claim.
    - 2026-07-04 reviewer follow-up on leakage and actor custody:
      read-only review found that declared leakage sentinels could be stale and
      mask source-domain vocabulary in platform leakage scans, and that actor
      completion could collapse distinct same-tail roles such as two different
      reviewers. The harness now validates external case-file `leakage_terms`
      against prompt or confirmed-intent source text before writing shards, and
      platform leakage selection falls back to source-derived terms when
      programmatic cases carry stale declared sentinels. Actor completion now
      removes tail-only dedupe while retaining exact and containment dedupe, so
      distinct same-tail roles remain separate actors. The broad rerun also
      exposed a code-hygiene failed mechanism: a duplicate legacy
      `_dedupe_actor_labels` helper later in the file overrode the new owner.
      That duplicate was removed, prefix normalization moved into the single
      actor-dedupe owner, and the same-tail/context-expanded actor cases now
      pin that custody. Focused proof passed the platform leakage, sharder
      case-file, and actor-label suites (`53 passed in 7.29s`), exact actor/live
      regression proof passed (`13 passed in 20.16s`), the widened
      harness/leakage pack passed (`88 passed in 16.53s`), and the broad
      runtime-quality pack passed (`71 passed in 894.16s`). Remaining release
      proof is unchanged: build a fresh dist, run installed high-variance
      discovery, and run strict release proof before readiness claims.
    - 2026-07-04 live progress line checkpoint:
      the tiered campaign harness now streams compact progress lines from the
      same merged telemetry owner that writes `campaign-progress.v1.jsonl` and
      the live campaign snapshot. The matrix child still flushes incremental
      result JSON after each case, and the campaign runner still owns stop
      decisions through typed failure clusters; the new renderer only projects
      canonical events to stderr for operators watching a long run. The wrapper
      streams by default and supports `GREENFIELD_MATRIX_QUIET_PROGRESS=1` for
      machine-only logs. Focused proof passed Python compile checks for the
      touched harness modules and the focused install/matrix harness suite
      (`56 passed in 0.26s`). This closes the opacity issue; it does not
      convert discovery proof into release readiness.
    - 2026-07-04 replay/concurrency/tier-size hardening:
      a read-only harness review found that the first live-progress pass still
      let four campaign contracts drift: multi-case pre-result shard crashes
      could masquerade as exact failed-subset replay, duplicate display names
      could over-select replay cases when no strong identity existed, 60/120/240
      tier names could silently shrink to small smoke pools, and the intended
      controlled-concurrency profile lived outside the harness policy. The
      follow-up fix makes exact failed-subset replay depend on stable case
      identity or single-case shard scope, emits source-shard replay packets for
      multi-case pre-result failures, treats weak names as replayable only when
      unique, fails default 60/120/240 tiers on undersized source pools unless a
      caller explicitly asks for a smaller smoke size, warns when generated case
      pools cannot satisfy 120/240 discovery, and records the default campaign
      worker profile of one failed-subset worker plus two discovery workers.
      A follow-up source read closed live name-only duplicate telemetry as well:
      duplicate display-name failures now produce source-shard replay instead
      of a fake exact subset when no strong identity exists.
      The code was decomposed at the same checkpoint: the campaign runner now
      owns orchestration, readiness posture, and CLI output, while a shard
      execution owner handles matrix command construction, process tailing,
      temp cleanup, synthetic shard payloads, and live telemetry forwarding.
      The resulting files are 428 and 792 lines, keeping both below the
      hand-maintained source soft limit instead of leaving another near-limit
      mixed-owner harness.
      Focused proof passed the campaign/sharder/generator/bootstrap harness
      suite (`61 passed in 0.18s`), Python compile checks for the touched
      harness modules, and scoped `git diff --check`. This makes the next
      hundreds-scale run faster to interpret and harder to overclaim; it still
      does not replace installed release proof.
    - 2026-07-04 replay fallback and dependency-injection cleanup:
      follow-up review found that exact failed-subset replay was still
      overclaimed when a failed shard named an unreadable or missing output
      JSON. The failure-response owner now advertises exact replay only when
      the result payload is readable and contains stable failed-case identity;
      otherwise it preserves the source shard case file for replay. The same
      pass keeps stopped sibling shards without failed-case evidence out of
      failed-case totals and removes the process-global monkeypatch seam
      between campaign orchestration and shard execution. `run_tier` now takes
      explicit command, telemetry-forwarding, and temp-cleanup dependencies,
      while the wrapper passes its current functions directly. Test ownership
      was split so direct failure-response behavior lives in its own 217-line
      module and the campaign-runner test file returns to 1,367 lines.
      Focused proof passed the full harness slice (`77 passed in 1.61s`),
      Python compile for the release harness modules, Registry forensics
      check-only (`30` components scanned, no updates required), and the broad
      runtime-quality pack (`71 passed in 928.12s`). D-047 now reflects the
      source-shard fallback and explicit dependency boundary. Remaining release
      work is unchanged: resume high-variance installed discovery, then run
      strict release proof from a fresh dist before readiness claims.
    - 2026-07-04 direct campaign case-file preflight follow-up:
      packaged exact failed-subset replay against the fresh worktree dist passed
      20/20 previously failing cases with every case at 10/10 and under 45s,
      proving the replay tier itself. The next direct campaign invocation over
      stale shard files exposed a remaining harness custody gap: invalid
      existing case-file metadata could still reach child shard execution when
      the maintainer bypassed the sharder and passed shard files directly to
      `greenfield-matrix-campaign`. The fix preflights existing selected shard
      files at the tier boundary before any worker launch, emits a typed
      `campaign.case-file-invalid` cluster, keeps completed shard count at
      zero, and preserves source-shard replay guidance for the invalid file.
      Live rerun of shard 03-10 now fails in 0.006s with no sibling launch, and
      focused proof passed the campaign-runner suite (`30 passed in 0.16s`).
    - 2026-07-04 current-taxonomy strict release proof:
      strict release proof on the fresh worktree dist completed with
      `status=release-ready`, `release_proof_completed=true`,
      `release_proof_status=passed`, `release_readiness_status=proven`, and
      zero failure clusters. The release case shard covered all 11 maintained
      stressor classes at 10/10 variance, and the 12 release cases all scored
      10/10 with standard create timing min 32.826s, max 42.597s, mean
      37.311s, and p95 41.905s. Browser proof attempted and passed 12/12 cases
      with zero issues, platform leakage passed, rescue smoke passed at
      52.260s, natural rescue passed at 68.349s within the 90s rescue budget,
      and temp cleanup proof left the release temp scope empty. This supports
      the strict release-proof posture for the current dist, while large-volume
      discovery remains blocked on regenerating valid high-taxonomy external
      shards rather than reusing stale legacy corpus G shards.
    - 2026-07-04 controlled-regression source-launch falsification:
      fresh current-source dist `/private/tmp/odylith-local-release-0.1.15-current-replay`
      first passed the exact six-case failed-subset replay from shard 006 with
      every case at hard 10/10, complete governed records, zero issues, and
      standard create timing between 34.547s and 46.534s. The follow-up
      controlled 60-case regression over shards 003-010 then stopped correctly
      on the first new failure cluster after 26 clean cases: `rail signal
      anomaly simulator v1` failed before governed writes because every Project
      implementation prompt leaked actor-led finite action inside `user can`
      prose. Source diagnosis traced this to Project source-launch rendering:
      it composed accepted path copy from `first_path_action_phrase`, which
      derived `review Engineers replay signal states`, then wrapped it as `the
      user can ...` and joined the terminal outcome as `receive accept an
      anomaly result`. The fix is source-owned and generic: accepted actor rows
      flow into source-launch first-path, capability, and proof rendering; only
      source-owned actor prefixes may split actor-led base-action material
      steps; terminal action outcomes become readable result objects before
      being joined with `receive`; and the prompt quality gate remains strict.
      Focused proof passed the new rail regression and adjacent actor-led
      source-launch prompt regression (`2 passed in 0.37s`) plus Python compile
      checks. Remaining verification: rebuild the local dist from this fix,
      rerun the exact rail failed subset, then resume the interrupted
      controlled 60-case regression before any broader discovery or release
      readiness claim.
    - 2026-07-04 existing-modal source-launch falsification:
      the rebuilt rail source-launch dist passed the exact rail replay at hard
      10/10 and resumed the interrupted controlled 60-case regression.
      Shards 007 and 008 then passed 12/12 additional high-variance installed
      cases before the live stop policy found a new source-launch cluster in
      shard 010. The failed case rejected every Project implementation prompt
      and the Project dashboard preview for adjacent duplicate visible copy.
      Source-local reproduction exposed the exact shared phrase:
      `the mission operators can can import orbit covariance...`. Root cause
      was generic modal custody: the source-owned actor path always prepended
      `can` even when the accepted first-path action already carried a modal,
      while the base capability path should strip that modal before composing
      `capture the information needed to ...`. The fix keeps ownership inside
      `src/odylith/runtime/project_intelligence/source_launch.py`: actor
      subject rendering preserves existing modal action clauses without adding
      another modal, and base-action rendering removes a leading modal before
      capability composition. Focused proof passed the existing-modal
      regression, the rail actor-source regression (`2 passed in 0.34s`), and
      the full Project source-launch quality suite (`16 passed in 1.27s`).
      Exact source-local replay completed governed create with `mode=applied`,
      manifest passed, validation passed, zero issues, and manifest elapsed
      11.923s. Fresh installable dist
      `/private/tmp/odylith-local-release-0.1.15-space-modal-fix` passed
      platform-domain leakage across 224 distinctive fixture terms, and exact
      installed failed-subset replay passed at hard 10/10 with create time
      34.148s, zero issues, complete Radar/Registry/Atlas/trace/prompt
      evidence, and all expert lenses green. Follow-up resumed shards 009-010
      from the same fresh dist with two workers and stop-on-first-cluster
      enabled; the window passed 12/12 high-variance installed cases at hard
      10/10 with zero issues and zero clusters. The exact failed case passed
      again in normal shard position at 36.361s, and both shards produced
      complete Radar/Registry/Atlas/trace/project-brief/Project-prompt
      evidence. A current-dist rerun of shards 003-008 then passed 36/36
      additional installed high-variance post-confirm cases at hard 10/10 with
      zero issues, zero failure clusters, and per-case live telemetry. The
      exact `grn-sim` confirmed intent replay now passes both source-local and
      installed paths: source-local create finished in 30.71s with governed
      records written and no repeated visible-copy hits, and installed replay
      passed at hard 10/10 with create time 30.034s, zero issues, 4 Radar
      workstreams, 5 Registry specs, 6 Atlas diagrams, 20 trace nodes, and all
      expert lenses green. Because older shards 001-002 evidence belonged to a
      stale worktree dist, those shards were rerun on the same fresh
      space-modal dist and passed 12/12 at hard 10/10 with zero issues and max
      create time 44.803s. The current fresh dist has therefore cleared the
      maintained 60-case regression tier at 60/60 with zero clusters. This is
      discovery proof, not release-readiness proof: browser, natural-rescue,
      strict release, and broader unseen-discovery proof still remain separate
      gates.
    - 2026-07-05 title-boundary semantic-ingress checkpoint:
      the resumed 120-case discovery run found a new failure after the
      quantum-dot fix: `secure multiparty risk model model-risk release gate`
      failed before governed writes because source-title boundary duplication
      fanned out into Project prompts, project brief, next steps, accepted
      memory, Compass, Radar, Registry, and Atlas. The repair keeps ownership
      in semantic ingress rather than rendered surface cleanup:
      `normalize_project_title` now collapses adjacent duplicate title terms
      and prefix-equivalent hyphen/slash compound boundaries before projection
      fan-out, and Product Intent Confirmation recovery canonicalizes recovered
      title sources before story/state/proof/system generation. Focused proof
      passed the boundary/source-launch/high-variance pack (`12 passed in
      129.16s`), source-local exact replay committed governed writes with
      manifest passed and whole-project elapsed `32.85s`, and fresh installed
      failed-subset replay against
      `/private/tmp/odylith-local-release-0.1.15-secure-title-20260705T082546`
      passed hard `10/10` in `46.865s` with zero issues, complete
      Radar/Registry/Atlas/project-brief/trace/Project-prompt evidence, all
      expert lenses green, platform leakage proof passed, and temp cleanup
      passed. This proves the escaped failed subset but remains discovery
      proof; resume broader 120/240 unseen discovery and strict release proof
      before release-readiness claims.
    - Resumed installed volume-discovery shards 007-008 against the same
      secure-title dist passed 60/60 high-variance scientific and deep-tech
      cases with zero clusters, zero rescue activations, hard `10/10` on every
      scored matrix dimension, all expert lenses green, and standard-path
      latency min `30.504s`, average `40.951s`, max `48.879s`. The tranche
      re-exercised the exact prior `secure multiparty risk model model-risk
      release gate` case at hard `10/10` in `45.971s` plus independent
      boundary-duplicate variants such as `chemical plume emergency model
      model-risk release gate` at hard `10/10` in `45.378s`. This materially
      strengthens the generic ingress fix but remains discovery evidence
      because browser-surface proof and natural-rescue proof were intentionally
      off.
    - The same secure-title installed dist then passed the remaining
      volume-discovery shards 001-006, adding 180/180 clean cases and closing
      the candidate's 240-case discovery target at 240/240 passed, zero
      clusters, zero rescue activations, all scored dimensions hard `10/10`,
      create-time min `30.504s`, average `41.828s`, max `48.879s`, and no
      standard-path create over `60s`. The tranche rechecked the earlier
      quantum-dot escaped family across intake, simulation, field-evidence, and
      model-risk variants in installed shard context. Remaining release
      boundary: run strict release proof with full install mode, browser,
      natural rescue, platform leakage, temp cleanup, and brutal artifact
      readback before release-readiness claims.
    - Strict release proof against the secure-title installed dist then passed
      the full release boundary: campaign
      `/private/tmp/odylith-secure-title-release-proof-20260705T103137/campaign.json`
      reported `status=release-ready`, `execution_status=passed`,
      `release_proof_completed=true`, `release_proof_status=passed`,
      `release_readiness_status=proven`, and zero failure clusters. The strict
      shard passed 12/12 scientific and deep-tech release cases with zero
      issues, browser proof for every generated repo, platform-domain leakage
      proof, temp cleanup proof, and hard `10/10` minimum scores for completion,
      copy semantic clarity, governance depth, traceability, implementation
      prompts, browser proof, latency, operator usefulness, semantic manifest,
      product manager, architect, engineer, and domain expert. Standard create
      timing stayed under the normal operator budget with min `39.648s`,
      average `42.987s`, and max `47.625s`. Natural rescue also passed through
      a real installed structured semantic patch case: first pass produced
      `structured_rescue_semantic_patch`, the Tribunal patch planner returned a
      schema-bound repair for
      `SemanticModelIR.domain_ontology.external_systems`, the second pass
      committed governed records, `natural_rescue_proof.cli_create_seconds` was
      `66.351s`, manifest elapsed was `39.777s`, whole-project elapsed was
      `58.397s`, and all quality lenses passed. This proves the candidate
      package's strict release boundary. Final closure still requires a fresh
      local-installable dist from the current post-governance tree, installed
      proof against that exact dist, then stable commit and push.
    - Final fresh-dist closure proof is now green for
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-final-20260705T035850`.
      The dist build passed platform-domain leakage across 224 distinctive
      fixture terms, and strict installed campaign
      `/private/tmp/odylith-final-release-proof-20260705T040258/campaign.json`
      reported `status=release-ready`, `execution_status=passed`,
      `release_proof_completed=true`, `release_proof_status=passed`,
      `release_readiness_status=proven`, and zero failure clusters. The strict
      shard passed 12/12 high-variance scientific/deep-tech cases with zero
      issues, browser proof, platform-domain leakage proof, temp cleanup proof,
      and hard `10/10` minimum scores across completion, copy semantic clarity,
      governance depth, traceability, implementation prompts, browser proof,
      latency, operator usefulness, semantic manifest, product manager,
      architect, engineer, and domain expert. Standard create timing stayed
      within the 60s target: min `38.971s`, average `42.668s`, max `47.199s`.
      Natural rescue passed on the real installed structured semantic patch
      path with `cli_create_seconds=61.178`, manifest elapsed `34.826s`,
      whole-project elapsed `53.204s`, repaired
      `structured_rescue_semantic_patch`, and committed governed writes. Final
      remaining delivery action is the stable commit and push of this release
      checkpoint.
    - Post-commit local release smoke against
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-9842e85d`
      reopened delivery closure because the fresh install `AGENTS.md` guidance
      omitted the exact `proposal JSON` confirmed-create guard. This is a
      release-package custody defect, not a Greenfield semantic-engine defect:
      `src/odylith/install/agents.py` and the root product scope block still used
      vague `source/repair JSON`, `narrate retries`, and `JSON review` wording
      while the smoke guard, asset parity tests, and bundled greenfield guidance
      required the stricter Odylith-source, hand-authored proposal-JSON,
      parser/schema, final-summary-only, and no-second-confirmation contract. The
      fix aligns the managed AGENTS generator and root scope block, adds a
      regression assertion in
      `tests/unit/install/test_agents.py`, and leaves the release smoke guard
      strict. Focused pre-rebuild proof passed
      `tests/unit/install/test_agents.py` plus
      `test_release_smoke_requires_installed_greenfield_guidance_uses_confirmed_create`
      (`10 passed`). Final delivery now requires rebuilding from the fixed tree
      and passing local release smoke against that rebuilt dist before any
      release-ready claim.
    - The first rebuilt proof dist then advanced to the next installed-guidance
      guard and failed on `AGENTS.md: Product story`, proving the managed root
      block also needed the minimum confirmation section list, not only
      proposal-JSON custody. The managed line now names Product story, State
      object, First complete path, Proof boundary, and the no-wall-of-prose
      guard, while an unrelated Assist closeout sentence was compacted to keep
      product and consumer managed blocks under the 11600-byte ceiling. Broader
      guidance parity proof passed (`12 passed`) and managed block sizes are
      `consumer_repo=11098`, `product_repo=11321`. Final delivery still requires
      a fresh rebuild and local release smoke against the post-format fixed dist.
    - 2026-07-05 post-confirm completion checkpoint: the working tree fixed the
      two standard installed failures from the guidance-smoke proof without
      domain-specific exceptions. Inline actor events now render through the
      backlog text-model actor-subject contract, so protected tokens such as
      acronyms remain intact while ordinary role words do not leak title casing
      into sentence fragments. Rescue planning now emits a deterministic,
      source-anchored `ArtifactPlanIR.assumptions` replacement fact from
      accepted assumptions plus the accepted proof boundary, while the engine
      refuses non-executable PatchSet operations before calling repair. The
      domain-expert lens also no longer requires two rendered terms from a
      one-term high-risk assumption. Focused proof passed `78` unit tests across
      quality lenses, rescue planner, patch executor, post-confirm engine, and
      actor grammar. Source-local replay passed `package supply chain exception
      desk` in `35.554s` and `sparse disclosure confirmation` in `26.947s`;
      both wrote governed records, passed final manifests, and had zero scanned
      `package Manager`, `result result`, `output output`, `proof proof`, or
      `to flags` hits. A follow-up exact saved `grn-sim` source-local replay of
      the gene-expression simulation confirmed intent completed in `29.828s`
      from the current source tree, returned `0`, wrote governed records,
      produced five Radar markdown records, five Registry specs, six Atlas
      Mermaid diagrams, and one Casebook record, and had zero scanned
      `result result`, `output output`, `proof proof`, `to flags`,
      `package Manager`, or `Launches launches` hits. The same checkpoint
      corrected assumptions rescue decision-ledger text so
      `ArtifactPlanIR.assumptions` repairs explain accepted-assumption and
      proof-boundary custody instead of component-contract custody. Remaining
      boundary: rebuild a fresh installable dist from this tree, run installed
      failed-subset proof plus exact grn-sim proof, then widen to maintained
      matrix/release proof before any release-ready claim.
    - 2026-07-05 rescue-custody correction: the reviewer found that the new
      non-executable PatchSet gate repeated an older failed mechanism by using
      a local non-empty-value predicate. That wrongly treated explicit
      list-valued SemanticModelIR clears as `no_executable_patchset`, despite
      the Tribunal planner already distinguishing missing facts from
      intentional empty semantic lists. The engine now delegates executable
      fact presence to the Tribunal missing-fact contract. The same review found
      the deterministic assumptions fallback could invent generic assumption
      rows when accepted assumptions were absent; the fallback now refuses to
      produce an `ArtifactPlanIR.assumptions` patch without accepted assumption
      source rows, and the artifact-plan executor preserves assumption metadata
      by explicit `ASM-*` id when wording changes. Focused source proof passed
      `66` PatchSet/rescue tests and the widened post-confirm/Tribunal/semantic
      patch suite passed `110` tests. A stale proof dist's strict matrix is
      diagnostic only after these source changes; final release proof must be
      rebuilt from the corrected tree.
    - 2026-07-05 current final-dist release proof: rebuilt retained dist
      `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-final-20260705T200258Z`
      and reran strict installed release proof against that exact package.
      Campaign `/private/tmp/odylith-final-release-proof-20260705T201226Z/campaign.json`
      reported `status=release-ready`, `execution_status=passed`,
      `release_proof_completed=true`, `release_proof_status=passed`,
      `release_readiness_status=proven`, and zero failure clusters. The release
      shard passed 12/12 scientific/deep-tech cases with hard `10/10` release
      scores, browser proof, platform generated-readback leakage proof, temp
      cleanup proof, and all PM/architect/engineer/domain-expert lenses green.
      Standard create timing stayed below 60s with min `45.319s`, average
      `46.688s`, and max `47.719s`; natural rescue committed governed records
      through the real installed structured semantic patch path in `74.704s`,
      under the 90s rescue budget. Exact installed replay of the saved
      `/Users/freedom/mock/grn-sim` confirmed intent then returned `0` in
      `38.349s`, wrote governed records, produced 7 Radar markdown files, 5
      Registry component specs, 6 Atlas Mermaid sources, 12 Atlas rendered
      assets, 3 Casebook markdown records, and 25 Compass files, and had zero
      scanned `result result`, `and keeps`, `to flags`, or
      `Launches launches` hits. Obsolete local release directories and
      disposable simulation repos were pruned; only the current final dist
      remains under the research-code root.
