Status: In progress

Created: 2026-06-26

Updated: 2026-06-27

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
- [ ] Typed projection provenance follow-up. Independent review found the
      current canonical projection layer still flattens facts into allowed text
      strings and permits raw accepted-intent repetition instead of validating
      repeated copy against typed semantic node IDs, source paths, projection
      IDs, and sanctioned surface roles. Do not extend that string allowance
      pattern. The next architecture slice must preserve ProjectionFactIR
      provenance into package quality and route unsanctioned projection repeats
      as typed custody findings.
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
- [ ] Release posture remains unclaimed until these source-local fixes are
      checked into governance, generated Atlas/Registry/Compass surfaces are
      refreshed, and a fresh built installed dist passes the maintained
      high-variance matrix with persisted readback proof under the standard and
      rescue time budgets.
