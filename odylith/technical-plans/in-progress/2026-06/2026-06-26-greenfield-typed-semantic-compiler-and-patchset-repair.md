Status: In progress

Created: 2026-06-26

Updated: 2026-06-26

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

## Implementation Slices

- [ ] Define `ConfirmedIntentIR`, `SemanticModelIR`, `ArtifactPlanIR`,
      `ArtifactDraftSet`, `ReviewReport`, and `PatchSet` schemas with source
      provenance and stable IDs. Current checkpoint defines typed
      `ReviewReport` findings and `PatchSet` request schemas; the remaining IR
      contracts are still open.
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
      impacted-projection rerender remain open.
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
      `ProjectionLexicon` remains open.
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
- [ ] Rescue-path timing proof under 90 seconds after host-authored semantic
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
- [ ] Rescue-path end-to-end timing proof under 90 seconds with a real
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
