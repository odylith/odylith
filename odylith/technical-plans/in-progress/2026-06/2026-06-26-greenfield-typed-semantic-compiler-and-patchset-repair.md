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
- [ ] Replace post-confirm issue-substring routing with typed finding routing.
      Internally generated reports now classify and build failure signatures
      from typed findings first. `greenfield_post_confirm_patch_apply.py` now
      consumes operation-level `PatchSet` entries instead of target-layer/source
      sets, preserves target path plus semantic node context, and leaves
      artifact-draft-only operations out of proposal mutation. The legacy
      English-message classifier remains as a compatibility fallback for old
      report fixtures and external callers, and full host-authored
      semantic/plan patch application remains open.
- [ ] Replace rendered-prose package repair with semantic or plan patch
      application and impacted-projection rerender. Current checkpoint emits a
      formal `PatchSet` request into the manifest and repair context, applies
      current deterministic semantic/quality-lens proposal repairs through an
      executable PatchSet seam, and maps affected artifact projections from
      typed projection IDs or target paths. The Radar handoff regression and
      raw first-path risk-copy regression have been moved upstream into
      projection owners instead of rendered-package cleanup:
      `greenfield_traceability.py` normalizes validation sentence shape before
      Radar render, `artifact_enrichment.py` preserves complete validation
      predicates, and `greenfield_workstream_risk_projection.py` projects
      semantic visible-result evidence instead of raw comma-heavy first-path
      chains. Full host-authored semantic or plan patch application plus
      impacted-projection rerender remain open.
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
- [x] Add a host-reasoned semantic patch executor with bounded schema:
      `operation_id`, `semantic_node_id`, `target_path`, `affected_projections`,
      `replacement_fact`, `decision_ledger_entry`, `proof_obligation_delta`,
      `rejected_interpretation`, and confidence. Reject prose-only patches.
      Current checkpoint applies host-authored `replacement_fact` operations to
      accepted-intent semantic fields before semantic-model regeneration,
      retains proof-obligation deltas in the decision ledger, and routes only by
      explicit IR target tokens instead of incidental substrings. The actual
      host-model semantic compiler call remains a separate open integration.
- [ ] Add context-starved renderer contracts so Radar, Registry, Atlas,
      Compass, release proof, and next steps cannot cross-contaminate.
      Current checkpoint adds the first projection contract split:
      modal-safe actions, visible-result outcome actions, and child risk
      posture are resolved in shared projection owners before renderers compose
      surface copy. Public-copy package repair now treats structural path,
      identity, slug, schema, status, version, URL, and record-reference fields
      as immutable custody metadata. A broader explicit `ProjectionLexicon`
      remains open.
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
- [x] Widened regression proof after the latest fixes: post-confirm engine,
      semantic patch executor, and slop regressions passed 126 tests in
      72.62s; full greenfield artifact quality passed 49 tests in 268.59s;
      component/diagram/install-matrix unit proof passed 17 tests in 0.53s; and
      prewrite transaction proof passed 52 tests in 339.63s.
