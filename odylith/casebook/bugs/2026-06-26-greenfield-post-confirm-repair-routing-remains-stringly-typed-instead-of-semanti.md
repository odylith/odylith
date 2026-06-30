- Bug ID: CB-208

- Status: Open

- Created: 2026-06-26

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Post-confirm quality failures are still routed by human-readable issue substrings, and rendered-package repair still mutates public strings instead of applying typed semantic or artifact-plan patches. This architecture is brittle under high domain variance even when the current repeated-risk defect is fixed.

- Impact: Future confirmed creates can fail or repair the wrong layer when validator wording, domain vocabulary, or artifact shape changes, blocking governed record writes or encouraging regex/template accumulation.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo maintainer source-local architecture review on branch 2026/freedom/v0.1.15.

- Detected By: Subagent architecture review after repeated greenfield post-confirm failures and CB-207 repeated-risk repair.

- Failure Signature: Post-confirm issue classification and rescue routing used to depend on substring matching; the current internal report path now emits typed findings first, but package repair still recursively rewrites rendered public copy instead of applying semantic or artifact-plan patches.

- Trigger Path: Architecture review of src/odylith/runtime/domain_intelligence/greenfield_post_confirm_engine.py and greenfield_post_confirm_repair.py during greenfield post-confirm hardening.

- Ownership: Greenfield semantic compiler, post-confirm repair engine, package quality gates, host reasoning integration, and artifact projection boundaries.

- Timeline: Captured 2026-06-26 through `odylith bug capture`. Later on
  2026-06-26, the ecommerce handoff regression showed that a Radar validation
  line rendered as `covers happy path` and artifact enrichment clipped
  `Validate that ...` proof text into a noun fragment. That failed the final
  post-confirm package gate before any governed records were written. The fix
  moved those repairs upstream into Radar validation projection and
  artifact-enrichment sentence preservation instead of re-enabling rendered
  Markdown cleanup. A later checkpoint extracted
  `greenfield_post_confirm_patch_apply.py` so the proposal repair callback
  consumes operation-level `PatchSet` entries, preserves field target plus
  semantic-node context, carries rejected-interpretation text into semantic
  operations, and refuses proposal mutation for artifact-draft-only operations.
  The same pass moved raw first-path risk copy into
  `greenfield_workstream_risk_projection.py`, where risk posture now projects
  semantic visible-result evidence instead of repeating a comma-heavy first
  path.
  A later faithful propose-then-confirm shelter-capacity simulation completed
  proposal generation but failed post-confirm create in 9.668 seconds with
  four prewrite blockers: Radar missing semantic coverage for first path,
  Atlas missing semantic coverage for `FirstPathContract`, project brief
  preview missing semantic coverage for `FirstPathContract`, and Radar index
  repeating the same visible result inside one sentence. The paired quantum
  tunneling simulation passed create in 11.668 seconds with no simple red
  flags, while an earlier malformed shortcut harness also showed that
  incomplete confirmed-intent files can fail the internal-systems gate before
  post-confirm repair is reached. This confirms the remaining failure is not
  only copied prose: repairable semantic-coverage findings can still route as
  artifact-plan/package shape and then rerun deterministic completion without
  applying a meaning-changing semantic or plan patch.
  A later checkpoint found two additional projection-boundary failures in the
  faithful high-variance loop: visible result nouns could be reinterpreted as
  actor-led actions when embedded in `user can` copy, and child Radar
  workstream risk projection could strip or omit the explicit risk posture that
  the governed artifact Tribunal requires. The fix kept both repairs upstream:
  first-path semantic repair now rewrites the confirmed proposal's semantic
  first path before downstream completion, outcome-action rendering treats
  visible result objects as result objects before considering actor-led action
  stripping, and child workstream risk projection preserves `Risk:` semantics
  even when no parent risk posture is available.
  A later source-local high-variance matrix exposed three more general
  post-confirm quality mechanisms before writes: package copy repair could walk
  structural Registry and accepted-project path metadata as if it were prose, a
  quantum-chemistry proposal repeated a visible result by comparing
  `publish ...` action wording against `published ...` result wording without
  morphological normalization, and the artifact-judgment lens rejected a valid
  project-brief question because it treated `name` as an abstract noun instead
  of the verb in `result story name the user`. The same pass also found proof
  labels could become `Proof Ledger Proof Record`, a real readability failure
  caused by composing proof-record suffixes onto labels that already carried
  proof-ledger semantics.
  A subsequent high-variance pass exposed two more platform-level failures
  before governed writes. First, multiple evidence-oriented Registry component
  specs received the same generic opening sentence because component-spec
  narrative rendered from the shared project evidence focus rather than the
  component's local label, output, and ownership boundary. Second, a confirmed
  first path whose visible result began with a title-cased role phrase produced
  public copy such as `see Clinician review` and `reviewing Clinician review`,
  which the final semantic gate correctly rejected as mixed actor-role casing
  in the validation strategy and project brief. Both failures are projection
  ownership defects, not consumer-project defects.
  A wider component-quality suite then caught a related noun-slot hygiene
  regression: `contract_list_text` preserved `ranked status windows` where the
  component contract field should render the artifact noun `status windows`.
  Existing Casebook history already pinned plural folding for `status windows`,
  so repeating the old mistake by patching a renderer or adding a fixture
  exception is forbidden; the fix belongs in the shared contract field or
  artifact-term owner.
  Two more inherited-environment source-local simulations failed before
  governed writes: one Registry component spec used a repeated keeping summary,
  and one Radar workstream clipped a modifier phrase ending in `the safety`.
  These are again projection-owner defects. The repair must preserve component
  responsibility and workstream grammar at the semantic/projection source,
  rather than masking the final quality gate or adding prompt-specific terms.
  The subsequent ten-domain matrix passed nine domains but failed a quantum
  chemistry runbook case before writes because Radar, Atlas, and the project
  brief all missed semantic coverage for the first path. This is the same
  architectural class as the earlier shelter-capacity failure: projection
  coverage can detect the missing first-path contract, but recovery still needs
  to repair semantic/projection facts rather than rerun deterministic rendering
  with the same missing coverage.
  A later fresh matrix exposed a source-custody failure before post-confirm:
  if the no-host `greenfield propose` guidance envelope was saved as the
  confirmed intent file, recovery could consume `Next step` and confirmed CLI
  instructions as product facts. The failing orbital-debris case produced a
  thin recovered intent with no valid internal product systems. This was not a
  project-domain defect; the prompt-source owner failed to isolate the
  `Original user intent` block before title and first-path recovery.
  The affected confirmed-intent suite also exposed a proof-projection custody
  miss: a proof boundary that said the release must not claim a deferred
  outcome was present in the accepted intent, but post-confirm backlog
  completion rewrote the proof workstream metrics from component contracts and
  dropped that negative proof constraint. The fix belongs in backlog
  proof-boundary projection and completion reconciliation so repair cannot erase
  release limits.

- Blast Radius: Any greenfield project domain or complexity where semantic ambiguity, repeated claims, domain-specific proof obligations, or artifact-specific wording requires repair before governed writes.

- SLO/SLA Impact: Standard under-60s and rescue under-90s paths remain at risk until rendered-prose mutation is replaced by targeted semantic or artifact-plan patch application and impacted-projection rerender.

- Data Risk: No direct data loss; fail-closed writes protect governed records, but confirmed product intent may remain unmaterialized.

- Security/Compliance: Safety, compliance, and domain-expert review can be weakened if repair mutates wording without preserving proof obligations and provenance.

- Invariant Violated: Greenfield repair must repair semantic interpretation or artifact-plan facts, not patch rendered strings or route by mutable English diagnostics.

- Root Cause: Odylith evolved deterministic validators and rendered-package cleanup faster than it evolved a typed ConfirmedIntentIR, SemanticModelIR, ArtifactPlanIR, ReviewReport, and PatchSet boundary for host-model reasoning. The current PatchSet seam can carry typed operations, but semantic-coverage failures can still be treated as artifact-plan shape and the apply side mostly replays deterministic completion instead of accepting a host-reasoned semantic or plan patch with a decision ledger.

- Solution: Adopt a typed host-reasoned architecture: one schema-constrained semantic compiler call, deterministic artifact planning/projection, typed deterministic and reviewer-lens findings, and targeted semantic/plan PatchSet repair before final fail-closed writes.

- Verification: Typed `ReviewReport` findings, typed repair-context payloads,
  stable typed failure signatures, structured quality-lens findings, `PatchSet`
  request emission, operation-level PatchSet application, affected-projection
  mapping from target paths, rejected-interpretation preservation, and
  artifact-draft-only non-mutation are now covered by focused post-confirm
  engine tests. The Radar projection fix is covered by
  `test_greenfield_radar_projection_quality.py`, raw first-path risk-copy
  projection is covered by
  `test_workstream_risk_projects_semantic_result_instead_of_raw_first_path_chain`,
  the widened post-confirm slice passed with 130 tests in 60.09 seconds, the
  previously failing ecommerce apply path passes, the earlier widened
  greenfield slice passed with 231 tests in 137.78 seconds, and the
  post-confirm/prewrite transaction suite passed with 75 tests in 315.34
  seconds. The architecture defect remains open until rendered-string package
  repair and deterministic replay-only rescue are replaced by host-authored
  semantic or artifact-plan patch application plus impacted-projection
  rerender. New faithful simulation evidence on 2026-06-26: quantum
  tunneling propose-then-confirm passed in 11.668 seconds with no simple red
  flags; shelter capacity propose-then-confirm failed in 9.668 seconds on
  semantic-coverage and repeated-visible-result blockers before any governed
  records were written.
  Later checkpoint evidence: focused projection/post-confirm tests passed with
  33 tests in 19.81 seconds; the widened greenfield runtime slice passed with
  168 tests in 142.44 seconds; four fresh faithful propose-then-confirm
  simulations across wellness/safety, finance/risk, creative/media, and
  overloaded record/case/agent/model/release terminology all wrote governed
  records in 13.1-13.5 seconds. Each simulation produced four Radar records,
  three Registry component specs, six Atlas Mermaid sources, six SVG renders,
  six PNG renders, zero generated semantic-slop issues, zero proposal-quality
  issues, and zero rendered-package quality issues. Every temp repo was
  deleted immediately after capture.
  Later source-local evidence after structural-copy, semantic-routing,
  result-term, proof-label, and preview-judgment fixes: five fresh domains
  passed propose-then-confirm create with governed records and zero quality
  issues: neonatal transfer coordination in 15.062s, offshore wind maintenance
  in 14.327s, court evidence redaction in 14.730s, quantum chemistry runbook in
  14.545s, and food relief routing in 14.650s. Each run wrote four Radar
  workstreams, three Registry specs, six Atlas Mermaid sources, five rendered
  surfaces, release/program/project brief records, 18 trace nodes, four trace
  workstreams, and four required domain-term hits. Every scenario repo and the
  matrix parent temp directory were deleted immediately after the run.
  Latest source-local evidence after projection-owner and first-path semantic
  fixes: a ten-domain matrix passed in the standard path without rescue:
  gene therapy consent 15.011s, asylum case preparation 14.475s, autonomous
  drone incident review 15.271s, municipal bond covenant monitoring 13.742s,
  marine microplastic custody 13.764s, museum restitution provenance 14.068s,
  wastewater signal triage 13.671s, quantum chemistry runbook 14.226s,
  mutual-aid logistics 14.432s, and language archive consent 14.301s. Every
  run reported zero post-confirm manifest issues, passed the product-manager,
  architect, engineer, and domain-expert lenses, wrote governed records, and
  deleted the temp repo before the next scenario. Regression proof also passed:
  160 tests in 47.14s for confirmed text, component spec quality, post-confirm
  quality repairs, and slop regressions; 93 tests in 273.24s for post-confirm
  engine, semantic patch executor, package repetition, Radar projection, and
  general artifact quality.
  Latest recovery proof: the failed orbital-debris guidance-envelope replay now
  writes governed records in 14.465 seconds wall time, with a passed standard
  manifest, no rescue, zero issues, four Radar workstreams, three Registry
  component specs, six Atlas diagrams, and temp cleanup after the replay.
  `tests/unit/runtime/test_greenfield_confirmed_intent_recovery.py` passed 20
  tests in 29.75 seconds after adding envelope-isolation and sentence-style
  title/path recovery regressions. The proof-boundary deferred-scope regression
  in `tests/unit/runtime/test_greenfield_confirmed_intent.py::test_confirmed_greenfield_create_completes_thin_intent_before_governed_records`
  now passes in 6.12 seconds.
  Final proof after the prompt-source and proof-boundary fixes, including the
  shared release-scope helper extraction: affected confirmed-intent and CLI
  paths passed 69 tests in 161.14 seconds; the broader greenfield quality pack
  passed 160 tests in 50.09 seconds; the heavy post-confirm engine/artifact
  suite passed 93 tests in 283.07 seconds. A fresh
  ten-domain matrix using source-local `greenfield propose` output as the
  confirmed intent file passed every scenario in the standard path without
  rescue: volcano school reunification 15.413s, orbital debris conjunction
  14.826s, newborn screening exception 14.241s, water-rights hearing evidence
  14.761s, key rotation incident readiness 15.258s, archaeological dig context
  custody 14.577s, cold-chain spoilage triage 13.970s, hiring audit response
  15.504s, soil carbon verification 13.996s, and courtroom translation access
  15.105s. Every run reported zero manifest issues, all product-manager,
  architect, engineer, and domain-expert lenses passed, four Radar workstreams,
  three Registry component specs, six Atlas diagrams, and temp repo deletion
  before the next scenario.
  A later architecture review found that `ArtifactPlanIR` was still mostly a
  contract: `greenfield_post_confirm_patchset.py` could emit
  `target_layer: artifact_plan` operations, but
  `greenfield_post_confirm_patch_apply.py` executed only semantic operations.
  That left plan-level rescue unable to change project brief, Radar, Registry,
  Atlas, release, program, assumption, risk, question, or validation projection
  facts through a typed operation. The new
  `greenfield_artifact_plan_patch_executor.py` applies only formal
  `artifact_plan` replacement facts to sanctioned proposal projection roots,
  rejects prose-only replacements, preserves immutable ids, slugs, schema
  versions, source paths, and timestamps, and records an
  `artifact_plan_patch_ledger` entry with operation id, target path, semantic
  node, rejected interpretation, issue code, confidence, and applied paths.
  This is not the final host compiler or impacted-projection rerender, so
  CB-208 remains open; it does prevent repeating the failed mechanism where
  plan patches were generated but never executed.
  A subsequent five-domain source-local simulation exposed a fresh prompt
  recovery/completion failure. Tribal wildfire evacuation grants, neutrino
  observatory calibration, film archive rights clearance, and municipal bond
  covenant climate disclosure passed in 13.931-14.742 seconds with governed
  records, zero issues, and all expert lenses passing, but clinical trial
  consent/adverse-event triage failed before writes with
  `missing or too thin: internal_systems`. Reproduction showed the recovered
  guidance-envelope confirmation had three meaningful internal system rows and
  validated before completion; `complete_confirmed_intent` then collapsed those
  rows into one broad `component responsibility named by the accepted intent`
  row because internal-system completion did not reuse the canonical spaced
  hyphen row parser. The repair must preserve explicit recovered system rows
  through completion, not weaken the internal-systems gate or add a
  clinical-domain exception.
  The same clinical repro also exposed a human-readability miss after the
  internal-system collapse was fixed: the first path step `release a
  first-slice monitoring report without automating medical diagnosis` became a
  fake actor row, `Release a First-slice Monitoring`, because shared prose
  grammar did not classify `release` as a base action token and actor
  extraction had no local way to reject that imperative step. The repair belongs
  at recovered actor extraction, where imperative release steps can be treated
  as actions without changing global modal/base-form grammar.
  The final repair kept the global prose grammar unchanged to avoid breaking
  existing modal/base-form checks. Instead, confirmed-intent recovery treats
  actorless imperative `release ...` clauses as non-actor action steps only
  inside recovered actor extraction, and internal-system completion reuses the
  canonical system-row parser only for spaced-hyphen recovered rows while
  leaving existing em-dash enrichment behavior intact.
  A 2026-06-28 brutal source-local live matrix after the actor/prose-shape
  cleanup remains non-release-ready. The affected unit pack passed 284 tests
  in 338.06 seconds, but five fresh confirmed-create simulations scored 0/10
  under the release-quality scorer. Battery materials release evidence failed
  before governed writes in 26.096 seconds on `modal/base-form grammar drift
  leaked at proposal.risks.1.statement`. Public records, solar assessment,
  structured review, and cooking robot wrote records in 24.761-28.957 seconds
  with all PM/architect/engineer/domain-expert manifest lenses passing, but
  failed release scoring because rendered Atlas/surface custody was incomplete:
  `odylith/atlas/atlas.html` was missing or empty, every Atlas source diagram
  missed SVG/PNG renders, rendered surfaces were 5/6, surface payloads were
  10/12, and Atlas rendered assets were 0. Every temp repo and the matrix root
  were deleted after learning. This proves the current standard path is fast
  but not release quality: semantic write success is not enough without
  rendered-surface custody, and risk-statement modal/base-form repair still
  needs a semantic/projection-owner fix rather than rendered prose cleanup.
  Latest installed-dist proof after the brutal scoring and prompt-source
  checkpoints: local release dist `odylith-local-release-0.1.15-ddecaf5e`
  passed the installed greenfield post-confirm matrix across flood shelter
  intake 22.842s, pediatric agency practice 19.780s, semiconductor lab custody
  22.419s, port berth carbon tariff 22.001s, and security disclosure council
  23.035s. Every installed consumer-lane run scored 10/10 under the hard-min
  model, wrote governed records, reported zero issues, passed product-manager,
  architect, engineer, and domain-expert lenses, produced five Radar records,
  three Registry records, six Atlas diagrams, 18 trace nodes, and the harness
  deleted the temporary matrix repos.

- Prevention: Before adding more regex or template rules, check Casebook and repair semantic ownership, projection boundaries, or typed review contracts first.

- Agent Guardrails: Do not claim premium real-world readiness from greenfield fixes while post-confirm rescue can still mutate rendered prose or lacks fresh high-variance simulation proof. Do not repeat earlier failed mechanisms: rendered-string cleanup, issue-substring routing, domain-term exceptions, or broad template rewrites. Fix the semantic owner, projection owner, or typed repair boundary that produced the bad artifact.

- Preflight Checks: Read CB-207 and this bug before changing post-confirm repair; verify whether the change patches SemanticModelIR or ArtifactPlanIR rather than rendered strings.

- Regression Tests Added: `tests/unit/runtime/test_greenfield_post_confirm_engine.py`
  now proves typed findings override unclassifiable message text, typed
  quality-lens checks do not become generic artifact drift, repair contexts
  carry typed `ReviewReport` and `PatchSet` request payloads, manifests
  expose the patchset request, PatchSet target paths map to affected artifact
  projections, semantic operations preserve target path plus semantic node, and
  artifact-draft-only operations do not mutate proposal state.
  `tests/unit/runtime/test_greenfield_radar_projection_quality.py`
  proves Radar validation rows use the shared article normalizer and
  artifact-enrichment preserves complete `validate that` predicates.
  `tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py` proves
  risk projection uses semantic visible-result evidence instead of raw
  first-path action chains. `tests/unit/runtime/test_greenfield_projection_contracts.py`
  proves visible result objects stay modal-safe in `user can` projections and
  child workstream risk projection preserves governed risk posture through the
  same artifact Tribunal used before writes.
  `tests/unit/runtime/test_greenfield_semantic_patch_executor.py` proves
  host-authored semantic patches preserve proof-obligation deltas and do not
  route by incidental substrings such as `reactor` or `ecosystem`.
  `tests/unit/runtime/test_greenfield_post_confirm_engine.py` proves package
  repair preserves structural path metadata while still repairing public prose.
  `tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py` also
  proves proof-ledger labels do not duplicate proof-record wording and
  result-term coverage matches simple inflected result words to base action
  words. `tests/unit/runtime/test_greenfield_general_artifact_quality.py`
  proves the artifact judgment lens reviews preview values rather than Python
  mapping syntax and no longer treats `name` as an abstract noun when it is the
  verb in a normal question. `tests/unit/runtime/test_greenfield_component_spec_narrative_quality.py`
  proves evidence-role Registry openings stay component-local instead of
  repeating a generic sentence. `tests/unit/runtime/test_greenfield_confirmed_text.py`
  proves sentence-start visible results lower safely and terminal proof noun
  phrases become visible outcomes. `tests/unit/runtime/test_greenfield_post_confirm_quality_repairs.py`
  proves abstract boundary actors become review roles and workstream titles
  compact `while keeping` clauses before they reach governed anchors.
  `tests/unit/runtime/test_greenfield_confirmed_intent_recovery.py` proves
  full propose guidance envelopes are reduced to their `Original user intent`
  block before recovery, sentence-style prompts split product title from first
  release action, and operational instructions stay out of recovered project
  records. `tests/unit/runtime/test_greenfield_confirmed_intent.py` proves
  proof-boundary release limits such as `without claiming ...` remain visible
  after post-confirm backlog completion rewrites proof workstream metrics. Full
  host-authored semantic/plan patch application proof remains open.
  `tests/unit/runtime/test_greenfield_artifact_plan_patch_executor.py` proves
  artifact-plan PatchSet operations update only sanctioned projection fields,
  refuse immutable structural metadata changes, record the plan-patch ledger,
  and run through `apply_greenfield_patchset_repairs`; the focused executor
  test passed 2 tests in 0.14 seconds and the widened post-confirm repair and
  artifact-quality set passed 229 tests in 321.33 seconds.
  `tests/unit/runtime/test_greenfield_confirmed_intent_recovery.py` now proves
  source-local guidance-envelope recovery preserves explicit internal-system
  rows through completion and does not infer the fake actor `Release a
  First-slice Monitoring`. Targeted recovery and prior-regression proof passed
  24 tests in 39.63 seconds. The widened greenfield pack then passed 283 tests
  in 491.56 seconds. A five-domain source-local simulation passed after the
  fix with temp cleanup after every case: tribal wildfire evacuation grants
  13.649s, neutrino observatory calibration 14.012s, clinical trial
  consent/adverse-event triage 14.379s, film archive rights clearance 14.002s,
  and municipal bond covenant climate disclosure 14.244s. Every run wrote
  governed records, produced four Radar workstreams, three Registry specs, six
  Atlas diagrams, five rendered surfaces, 18 trace nodes, four trace
  workstreams, four required domain-term hits, zero quality issues, and passed
  product-manager, architect, engineer, and domain-expert lenses.
  A subsequent high-variance installed-matrix failure class (CB-209) exposed
  that expert-lens checks were still too local: they carried
  `name/status/evidence/issue` and then post-confirm repair reconstructed
  target paths and repair ownership from lens names. The new
  `tribunal_lens.py` contract moves multi-actor quality judgment toward the
  general Tribunal model by making each lens check emit the source-map target,
  semantic-node ID, projection ID, repairability, and repair owner at the point
  of judgment. Greenfield PM, architect, engineer, and domain-expert lenses now
  use that contract, and package findings trust those typed fields before any
  compatibility fallback. This reduces the failed mechanism where reviewer
  prose had to be interpreted later, while keeping fail-closed gates and
  provider-free custody intact.
  The same pass fixed CB-209 source-local defects without domain-specific
  exceptions: system-generated result text now projects into modal-safe review
  actions, passive state-review clauses recover role/object ownership without
  promoting result nouns into actors, interrogative modal clauses such as
  `what can be released` stay intact, and artifact-plan row patches require an
  explicit index, match, or path selector. Focused Tribunal/greenfield proof
  passed 53 tests in 85.82s; the broad greenfield runtime pack passed 299
  tests in 474.86s; six source-local CLI confirmed-create simulations passed
  in 13.934-15.501s with governed writes, zero issues, and all PM/architect/
  engineer/domain-expert lenses passing. Fresh installed-dist proof remains
  required before this architecture class can be closed.
  A later architecture audit found the typed PatchSet seam is still not enough:
  the real confirmed-create path emits repairable semantic or artifact-plan
  operations, but no live Tribunal/host planner fills `replacement_fact`,
  `decision_ledger_entry`, or `proof_obligation_delta` before the executors run.
  That leaves rescue dependent on deterministic proposal replay and remaining
  rendered-package repair owners. The same pass found a latency-contract bug:
  `repair-tier=auto` could spend the 90-second rescue budget before any
  repairable final-gate failure activated rescue. The engine now starts auto on
  the 60-second standard budget and extends to 90 seconds only after a
  repairable semantic or quality failure activates rescue. Focused engine proof
  passed 4 tests in 0.23 seconds, and the widened post-confirm engine plus
  semantic/artifact-plan patch executor set passed 42 tests in 22.83 seconds.
  The architecture remains open until a general Tribunal structured-patch
  planner can request bounded host reasoning in rescue/deep tiers, validate the
  returned formal patch against evidence and schema, and feed the existing
  semantic and artifact-plan executors without mutating rendered prose.
  The next cleanup checkpoint removed the highest-risk compatibility repair
  path instead of adding more message rules. `greenfield_post_confirm_engine.py`
  now treats raw `report.issues` strings as `legacy_untyped_report` blockers
  with no repair authority when typed findings are absent.
  `greenfield_post_confirm_findings.py` treats raw package issue strings as
  `legacy_package_artifact_gate` blockers, while
  `greenfield_post_confirm_package_findings.py` emits source-owned package
  findings for semantic coverage, release drift, Registry preview/spec shape,
  and explicitly safe mechanical copy cleanup. This prevents a human-readable
  gate sentence from becoming the semantic routing API again.
  The same checkpoint wired rescue/deep host reasoning through
  `greenfield_post_confirm_rescue_planner.py` and
  `runtime/reasoning/tribunal_patch_planner.py`. The planner can fill only
  replacement facts, decision-ledger entries, proof-obligation deltas, rejected
  interpretations, and confidence on existing PatchSet operations; Odylith
  rejects moved target layers, target paths, semantic nodes, invented operation
  IDs, and empty facts before any executor sees the plan. Standard create stays
  provider-free and under the 60-second budget; the planner is reachable only
  in rescue/deep tiers when time remains.
  Finally, `greenfield_semantic_patch_executor.py` now patches
  `SemanticModelIR` first and mirrors the accepted-intent field only for
  compatibility with the current deterministic completion path. It no longer
  deletes `semantic_model` and relies on replay as the sole authority. The
  ledger records `semantic_model.*` applied fields, preserving the intended
  repair substrate for the next impacted-projection rerender slice.
  Initial proof for this checkpoint: the focused semantic patch executor suite
  passed 5 tests in 0.28 seconds; the focused classifier, package-finding,
  rescue-planner, semantic-patch, and Tribunal patch-planner set passed 17
  tests in 0.44 seconds; and the widened greenfield post-confirm suite passed
  152 tests in 669.31 seconds. The greenfield Atlas topology was replaced and
  rerendered, and Atlas freshness passed with 44 fresh diagrams and zero stale
  diagrams after scoped auto-update. Governance proof for the checkpoint also
  passed: Casebook source validation checked 205 records, Registry validation
  checked 30 components and 629 events with all 292 meaningful events mapped,
  backlog contract validated 143 ideas, topology integrity scored 100/100,
  plan workstream binding/risk/traceability checks passed, and `git diff
  --check` passed. Fresh installed-dist proof from commit d42f127c then passed
  five high-variance consumer-lane post-confirm creates from the rebuilt local
  package in 20.107-23.147 seconds with zero final quality issues, five Radar
  records, three Registry records, six Atlas diagrams, 18 trace nodes, governed
  records written, and temp repos deleted after each scenario.
  The latest typed-IR cleanup found one more architecture debt in the same
  failure class: `ArtifactPlanIR` projection policy was duplicated across
  PatchSet emission, artifact-plan execution, and safe artifact-draft repair.
  That made future host-authored plan patches vulnerable to drift between
  target-path routing, immutable metadata policy, and impacted-projection
  selection. `greenfield_artifact_plan.py` now owns sanctioned roots,
  projection aliases, immutable fields, affected-projection calculation, and
  artifact-draft repair projection normalization. PatchSet emission,
  artifact-plan execution, and package repair consume that shared contract, and
  role-surface names such as product-manager or architect no longer imply
  affected projections without a typed projection ID or artifact path.
  The same checkpoint made `greenfield_apply_semantic.py` compile legacy
  proposal dictionaries through a persisted typed apply-semantic input with
  source-path provenance, and replaced the local first-path visibility regex
  with a semantic-compiler visible-result candidate check. Focused proof passed
  60 tests in 26.47 seconds, compile proof passed for the changed modules,
  Registry validation passed, and component-spec requirement sync converged
  for `domain-intelligence`. Subsequent rescue proof with the configured Codex
  structured provider activated the 90-second rescue path after injected typed
  semantic-coverage misses, repaired the package, reran gates, and committed
  governed records in 39.768 seconds; CB-209 carries the dedicated provider and
  rescue-custody evidence. A fresh eight-domain source-local variance run after
  the rescue/provider hardening then passed the normal standard path without
  rescue: tribal clinic referral consent 14.434s, satellite anomaly readiness
  15.514s, court interpreter access 15.362s, museum restitution provenance
  14.948s, wildfire mutual aid logistics 14.549s, battery recycling audit
  14.910s, cross-border aid disbursement 15.361s, and industrial water reuse
  permits 14.749s. Every run committed governed records, reported zero final
  quality issues, passed PM/architect/engineer/domain-expert lenses, produced
  expected Radar/Registry/Atlas/Compass/project/release records, and deleted
  its temp repo before the next case. Fresh installed-dist proof after this
  source-local checkpoint then passed from local release dist
  `odylith-local-release-0.1.15-58a9b7c5`: flood shelter intake 20.393s,
  pediatric agency practice 18.368s, semiconductor lab custody 18.393s, port
  berth carbon tariff 18.450s, and security disclosure council 19.048s. The
  installed consumer-lane matrix reported zero quality issues, governed writes,
  at least five Radar records, three Registry records, six Atlas diagrams, 18
  trace nodes, and temp cleanup by the harness.
  The next typed-dispatch cleanup removed two more failed mechanisms from the
  rescue path. First, quality-lens findings without a structured replacement
  fact no longer rehydrate proposal fields from failed check names; they remain
  typed findings until a semantic or artifact-plan patch supplies the missing
  fact. Second, PatchSet operations now carry `operation_kind`, `repair_owner`,
  and `projection_kind`, and the apply side no longer routes first-path repair
  because `rejected_interpretation` happens to mention first-path words. A
  source-local six-case matrix then found one remaining projection-owner
  failure: a museum loan prompt produced Radar titles with clipped actor
  context such as `Let Curator Signoff Before an ...`. That was not a package
  cleanup problem; recovered actor labels had carried a temporal/proof clause
  into the role head and clipped it at the title limit. The repair now trims
  actor context tails before workstream title projection and drops event nouns
  introduced by that context boundary, producing `Let Curator Coordinate
  Artifact Loan Requests` instead of a dangling article phrase. The failed
  mechanism remains banned: do not patch rendered Radar titles after the fact;
  fix the actor/title projection owner or the typed semantic fact that feeds it.
  Proof for this checkpoint: focused post-confirm repair, semantic patch,
  quality-lens, and Tribunal patch-planner tests passed 58 tests in 24.85s;
  the widened post-confirm quality/slop/text suite passed 181 tests in
  71.68s; the initial six-case source-local matrix passed five domains but
  failed museum loan provenance on two clipped article title issues while
  deleting the temp root; after the actor-title projection repair, a replay
  plus five fresh domains passed in 14.005-15.737s with zero quality issues,
  governed writes, four Radar workstreams, three Registry specs, six Atlas
  sources, five rendered surfaces, 18 trace nodes, all PM/architect/engineer/
  domain-expert lenses passing, and temp-root cleanup confirmed.
  The next scoped-rerender checkpoint addressed the remaining broad replay
  mechanism for artifact-plan-only rescue. `greenfield_artifact_plan.py` now
  owns explicit projection dependency expansion and full-prewrite triggers, so
  project-brief, Registry, Atlas, accepted-project, Compass, next-step, and
  release-preview updates can carry an auditable rerender scope while Radar and
  program changes still require staged prewrite recomputation. `greenfield_post_confirm_patch_apply.py`
  records a post-confirm patch application ledger with operation ids, affected
  projections, expanded rerender projections, completion requirements, and
  full-prewrite posture. `greenfield_post_confirm_engine.py` now consumes that
  ledger on the next pass and calls `greenfield_prewrite_projection_rerender.py`
  to refresh only the named package previews against the current package. This
  does not claim full generic SemanticModelIR scoped rerender; semantic patches
  still require semantic completion until their owned projection substrate is
  broader. A pre-commit reviewer then caught two projection-custody escapes in
  that checkpoint: `program` was normalized to `release` before the
  full-prewrite guard could see it, and `release` scoped rerender did not pull
  Compass along even though release assignment feeds the Compass acceptance
  preview. The failed mechanism is now explicit: do not let canonicalization
  erase a control-plane projection before full-prewrite policy runs, and do not
  treat a preview dependency as local when downstream package previews consume
  it. The fix keeps `program` as a first-class full-prewrite scope, adds Compass
  to the release dependency expansion, and adds regression coverage for both
  cases. Proof for this checkpoint: scoped rerender and typed PatchSet tests
  passed 66 tests in 24.12s; the wider greenfield post-confirm quality pack
  passed 242 tests in 360.05s; and eight fresh source-local confirmed-create
  simulations across biobank custody, archive consent, neonatal handoff,
  orbital debris, soil carbon, repatriation, grid fairness, and model-incident
  evidence all passed in the standard path with zero issues, all PM/architect/
  engineer/domain-expert lenses passing, four Radar workstreams, three
  Registry specs, six Atlas diagrams, 18 trace nodes, and temp cleanup after
  every case.
  The next semantic-scope cleanup removed three more failed mechanisms from the
  repair architecture. First, `greenfield_semantic_patch_executor.py` no longer
  collapses semantic application to a boolean that forces broad completion for
  every semantic change; it returns a `SemanticPatchApplication` with applied
  fields, operation ids, explicit affected projections, and whether semantic
  completion is truly required. Second, semantic target routing now uses
  operation-kind allowlists and exact compatibility paths only; the old loose
  token-splitting path is gone so a target string cannot accidentally become a
  semantic field. Third, proposal-owned plan targets such as backlog,
  Registry, Atlas, release-plan, assumptions, and validation strategy no longer
  masquerade as `semantic_patch` work. Source findings and quality lenses route
  those targets to `ArtifactPlanIR` / `plan_patch`, while the shared
  `ArtifactPlanIR` projection mapper recognizes structural envelopes such as
  `proposal.*`, `prewrite_package.*`, and `ArtifactPlanIR.*` before deriving
  scoped rerender custody. First-path semantic patches and semantic patches
  without explicit scope still require completion; scoped non-first-path
  semantic patches can now rerender only their affected projections. The banned
  mechanisms are explicit: do not recover by tokenizing semantic target names,
  do not label proposal projection defects as semantic patches, and do not
  force full completion merely because a scoped semantic fact changed. Proof:
  focused ArtifactPlanIR and semantic patch tests passed 17 tests in 0.26s;
  the post-confirm repair pack passed 74 tests in 24.54s; the widened
  greenfield post-confirm quality pack passed 250 tests in 362.79s; and a fresh
  installed consumer-lane matrix from temporary local release
  `/tmp/odylith-local-release-0.1.15-semantic-scope` passed flood shelter
  intake 19.769s, pediatric agency practice 19.788s, semiconductor lab custody
  18.903s, port berth carbon tariff 18.395s, and security disclosure council
  18.227s. Every installed run returned zero quality issues, wrote governed
  records, passed product-manager, architect, engineer, and domain-expert
  lenses, produced five Radar workstreams, three Registry specs, six Atlas
  sources, 18 trace nodes, five rendered surfaces, and the harness deleted temp
  repos between cases.
  The next quality-lens cleanup removed a dormant 768-line proposal
  rehydration engine from `greenfield_quality_lens_repair.py` and collapsed
  that owner into a metadata-only repair contract. A pre-commit review then
  caught two important escapes before commit. First, the live quality-lens
  report still emitted legacy repair owners such as Radar, release, and
  operator-experience renderers for plan-owned checks, so the new owner
  contract was not authoritative on the live path. Second, the old
  `proposal_repair` repairability alias still remained valid in review
  findings, rescue eligibility, and PatchSet target routing, meaning hidden
  proposal-level repair authority had not actually been fail-closed. The fix
  made the quality-lens report emit the same canonical owner contract consumed
  by PatchSet routing, made the package-finding collector ignore per-check
  owner/repairability drift for known checks, made unknown future lens checks
  unrepairable until their owner is declared, and removed `proposal_repair`
  from greenfield review, rescue, PatchSet, and Tribunal-lens custody. The
  banned failed mechanisms are explicit: do not leave an old repairability
  bucket accepted after moving to typed semantic/plan patches, and do not let a
  producer-provided owner override the declared quality-lens ownership
  contract. Proof: focused quality-lens, post-confirm engine, and Tribunal lens
  tests passed 9 tests in 0.34s; the widened greenfield repair pack passed 252
  tests in 354.43s; and a fresh installed consumer-lane matrix from temporary
  local release `/tmp/odylith-local-release-0.1.15-quality-lens-custody`
  passed flood shelter intake 19.934s, pediatric agency practice 18.244s,
  semiconductor lab custody 18.733s, port berth carbon tariff 18.381s, and
  security disclosure council 18.702s with governed writes, zero quality
  issues, all product-manager/architect/engineer/domain-expert lenses passing,
  and temp repos plus the temporary release directory pruned.
  The next artifact-draft cleanup checkpoint removed the remaining semantic
  authority from the package repair loop. Generated-copy categories such as
  mixed action inflection, compact action inflection, and malformed component
  responsibility now route to `plan_patch`, while non-mechanical package
  quality findings become source-owned artifact-plan findings instead of raw
  legacy blockers. `greenfield_post_confirm_repair.py` no longer calls the
  visible-result normalizer, article normalizer, modal/base-form fixer, or
  ownership-verb fixer over rendered drafts. Its repair executor now admits
  only PatchSet operations with the full mechanical contract:
  `target_layer=artifact_draft_set`, `issue_code=generated_copy_quality`,
  `operation_kind=artifact_draft_mechanical_copy`,
  `repair_owner=artifact_draft_cleaner`, the exact mechanical cleanup action,
  and no replacement fact, decision-ledger entry, or proof-obligation delta.
  A reviewer caught that `artifact_draft_set` alone was still too broad; the
  metadata gate now prevents semantic or artifact-plan operations from
  mutating rendered copy even when they name a draft projection. The banned
  failed mechanisms are explicit: do not repair semantic grammar after
  rendering, do not let a rendered package cleaner own modal/action or
  responsibility semantics, and do not accept artifact-draft mutation without
  the full typed mechanical-copy contract. Proof so far: focused mechanical
  executor tests passed 7 tests in 0.29s; the post-confirm repair/prewrite
  pack passed 113 tests in 397.10s; the widened semantic, artifact-plan,
  quality-lens, Tribunal, slop, general artifact-quality, confirmed-text, and
  ArtifactPlanIR pack passed 194 tests in 327.84s. Fresh installed-matrix
  proof from temporary local release
  `/tmp/odylith-local-release-0.1.15-mechanical-custody` then passed flood
  shelter intake 20.286s, pediatric agency practice 19.247s, semiconductor lab
  custody 18.812s, port berth carbon tariff 18.489s, and security disclosure
  council 18.981s. Every installed run wrote governed records, reported zero
  final quality issues, passed product-manager, architect, engineer, and
  domain-expert lenses, produced five Radar workstreams, three Registry specs,
  six Atlas Mermaid sources, 18 trace nodes, five rendered surfaces, and the
  temporary repos plus local release directory were pruned after proof.
  The next cleanup checkpoint tightened the remaining repair-custody seams
  instead of adding more rendered-prose fixes. First-path PatchSet operations
  no longer synthesize an accepted first path from proposal title or prompt
  metadata when the structured semantic executor rejects the replacement fact;
  unsupported or empty semantic operations now leave the proposal unchanged and
  fail closed. Profile-triggered Registry component contracts now derive the
  semantic contract first, then allow profile renderers only as fallback, so
  labels such as document, packet, status, or history cannot bypass the
  semantic basis. Gate-only expert-lens checks are now unrepairable even when a
  malformed payload claims `plan_patch`; prewrite proof gaps must be satisfied
  by rerendered package evidence, not by a model patch against rendered text.
  The package-quality path now emits typed rendered-artifact findings with
  exact repair paths through `greenfield_rendered_artifacts.py`, and the
  artifact-draft cleaner applies mechanical duplicate/tail cleanup only to the
  addressed leaf path. The old projection-wide draft cleanup mechanism is
  banned because it could mutate sibling Registry, Atlas, Radar, project brief,
  or next-step strings that did not own the finding. A pre-commit review also
  caught that corrupted rendered Registry scope is not semantic repair and not
  mechanical copy repair; it now routes through a distinct
  `projection_rerender` finding that schedules deterministic scoped prewrite
  rerender. If a direct engine caller omits the rerender callback, the engine
  fails with `missing_projection_rerender_callback` and a contract-level
  blocker instead of falling through as not rescue eligible. The banned failed
  mechanisms are explicit: do not synthesize semantic facts from metadata-only
  operations, do not let component profile keyword matches bypass semantic
  contracts, do not classify gate-only quality checks as patchable, do not
  mutate whole preview trees for one draft-copy finding, and do not send
  corrupted rendered projection scope through host semantic repair. Proof:
  moved/decomposed focused tests for projection rerender, quality-lens routing,
  exact-path draft repair, and rendered-artifact metadata passed 27 tests in
  4.15s; the original flaky rendered-Registry rerender apply path plus
  component semantic profile and first-path no-synthesis guards passed 4 tests
  in 18.00s; and the widened post-confirm/semantic repair pack passed 185
  tests in 79.09s. The earlier prewrite/general artifact pack also passed 101
  tests in 692.79s after the projection-rerender defect was fixed. Fresh
  installed proof from temporary local release
  `/tmp/odylith-local-release-0.1.15-custody-proof` then passed flood shelter
  intake 19.745s, pediatric agency practice 19.003s, semiconductor lab custody
  18.524s, port berth carbon tariff 18.522s, and security disclosure council
  18.383s. Every installed run wrote governed records, reported zero quality
  issues, passed product-manager, architect, engineer, and domain-expert
  lenses, produced five Radar workstreams, three Registry specs, six Atlas
  Mermaid sources, five rendered surfaces, 18 trace nodes, release/program/
  project-brief records, and the matrix plus temporary local release directory
  were pruned after proof. Final code-hygiene proof split the oversized
  post-confirm engine test owner into focused patch-payload and package-repair
  owners, bringing `test_greenfield_post_confirm_engine.py` down to 1409 lines
  while preserving behavior coverage; the moved projection, patch-payload,
  package-repair, and post-confirm engine tests passed 66 tests in 29.12s,
  and the widened post-confirm repair pack passed 185 tests in 77.48s after
  the split.
  A 2026-06-27 read-only audit of a generated wearable-health consumer repo
  exposed a new escaped false positive in the same custody class. The accepted
  intent clearly said the first result should show clear `"what changed"`
  insights, but the first-path semantic extractor clipped the visible-result
  fact to `clear "what`; Radar, Atlas, the project brief, accepted-project
  memory, and rendered dashboard surfaces then projected that malformed
  semantic fact while the final quality manifest still reported passed. The
  same artifact set leaked `grants consent` in base-verb capability prose and
  did not fail on unbalanced public quotes. This failure must not be repaired
  in individual renderers or by project-specific terms. The fix direction is
  to preserve complete semantic visible-result facts, repair coordinated
  action grammar in the common prose owner, and make unbalanced quoted text a
  package-quality blocker before governed writes can claim release quality.
  A later brutal-score source-local matrix exposed two further quality-proof
  lessons. First, a raw file scanner falsely reported four unbalanced-quote
  defects by reading serialized JSON syntax as public prose; release scoring
  now uses the same structured package collector as the official matrix and
  reports hard-min 10/10 dimensions instead of shallow pass/fail. Second, the
  water-rights hearing evidence case failed before governed writes because
  recovered actor extraction accepted the full action chain as a second human
  actor, `Legal Aides Organize Diversion`, after the shared grammar failed to
  recognize the domain-neutral action verb `organize`. That fake actor caused
  modal/base-form drift across intent summary, validation strategy, release
  gates, backlog product view, and success metrics. The fix stayed generic:
  `organize` is now part of the shared prose grammar action map, and confirmed
  intent recovery rejects actor prefixes that already contain an embedded
  actor-action-object clause before rendering human actor rows. Proof: the
  failed water-rights replay now writes governed records in 17.5 seconds with
  a hard score of 10/10 across completion, latency, semantic manifest,
  copy/semantic clarity, governance depth, traceability, operator usefulness,
  and PM/architect/engineer/domain-expert lenses. A final ten-domain
  source-local cleanup-proof matrix passed neonatal handoff 16.461s, municipal
  bond covenant 16.524s, water-rights hearing 16.935s, quantum lab 16.405s,
  kitchen robot 16.114s, vaccine cold-chain 16.513s, film rights 16.464s,
  distributed-agent incident command 16.270s, wildfire grants 16.316s, and
  museum accessibility 16.607s. Every scenario scored 10/10, wrote four Radar
  workstreams, three Registry specs, six Atlas Mermaid sources, 18 trace
  nodes, release/program/project-brief records, zero artifact issues, and the
  run verified `all_cleaned=true`.
  The widened regression pack then caught a prompt-source overcorrection: the
  earlier `use to choose` safeguard stopped role-purpose clauses such as
  `sales reps to qualify leads and managers to see pipeline health` from
  rendering as modal capability prose. The fix stayed in the no-regex
  prompt-source owner: after preserving `use to` infinitives, actor-purpose
  tails that look like human roles and lead into a known action now convert
  `to` to `can`, including coordinated role clauses after `and`. Focused proof
  passed the two failing CRM wrapper tests, the `use to choose` regression, the
  water-rights actor-chain regression, and the hard-score matrix unit tests.
  A later Project tab audit found another shallow-score failure class: the
  installed matrix could score a post-confirm package without inspecting the
  accepted Project dashboard implementation prompts shown to operators. The
  first fix made Project `host_handoff_prompts` rendered artifacts, but review
  then found four mechanisms that still could not support a release claim:
  missing `project_dashboard_preview` bypassed the prompt gate, prompt role
  checks were keyed to label substrings, prewrite generated Project dashboard
  prompts from the staged governance tree instead of the target repo root, and
  framework-leak detection treated ordinary domain phrases such as compass
  headings or Atlas parcel records as Odylith surface leakage. The current
  source fix keeps the gate generic: `project_dashboard_preview` is required
  once Radar, Registry, and Atlas prewrite evidence exists; Project prompt
  quality is owned by `greenfield_project_prompt_quality.py` and classified by
  prompt sequence position rather than labels; prewrite dashboard preview uses
  the target repo root for language/runtime signals; and Odylith-surface
  leakage now requires surface-specific platform context such as Registry
  component specs or Atlas diagrams. The same broad regression pass exposed a
  top-level scalar repair gap: unbalanced quoted text in intent summary,
  intent product story, and project-brief purpose was recognized as semantic
  slop but no repair path mutated those scalars. Confirmed completion now
  repairs those fields from semantic facts and strips embedded proof-boundary
  punctuation before composing public copy. Source proof for this checkpoint:
  focused blocker tests passed 6 tests in 35.44s; Project/source-launch/matrix
  tests passed 10 tests in 0.51s; the broad greenfield suite passed 241 tests
  in 844.71s after fixing late helper and repair-fixture regressions.
  The 33bdb122 installed matrix then proved that this source checkpoint was
  still insufficient. Pediatric agency practice and security disclosure
  council failed before governed writes because the new Project prompt gate
  saw malformed punctuation in source-launch prompts. Retained pediatric
  evidence showed `workspace., validation points` and `workspace., input
  validation`, caused by sentence-shaped clipped facts being embedded before
  comma clauses. The fix remains generic and upstream: source-launch prompt
  facts now render as punctuation-free fragments, action/outcome joins use
  semantic overlap to avoid `do X and receive do X` duplication, and operator
  next-step previews trim incomplete subordinate tails such as `when required
  information` before the final package gate.
  Source replay for the retained pediatric intent now reports zero rendered
  package issues, and source-mode confirmed create committed governed records
  in 15.428s. Focused source-launch and next-step clipping tests passed 3
  tests in 0.38s; the focused prewrite/Project package regression set passed
  58 tests in 485.56s. Fresh installed proof from a rebuilt dist remains
  required.
  Independent review then found that shorter object-repetition shapes still
  survived the overlap-only repair, and proof fallback still copied raw
  duplicated first-path text. Source-launch now suppresses outcomes whose
  material terms are already contained in the action, and proof fallback uses
  the cleaned first-path projection. Review also rejected the first rescue
  harness because rescue smoke was opt-in from the canonical matrix wrapper and
  the auto-rescue leg used a synthetic installed-engine probe instead of the
  packaged CLI. The matrix wrapper now includes rescue smoke by default, the
  rescue smoke runs installed `odylith greenfield create --repair-tier auto`
  with one exact-token internal typed finding, the engine must auto-escalate to
  rescue, semantic/plan repairs are recorded in manifest repaired issue codes,
  and `RESCUE_SMOKE=0` is explicitly local-debug only. Focused
  source-launch/experience/probe/matrix proof passed 17 tests in 0.43s, the
  current broad greenfield post-confirm pack passed 282 tests in 933.23s, and a
  disposable source-local CLI auto-rescue probe committed governed records in
  20.411s with `post_confirm_rescue_probe` recorded as repaired. Fresh
  installed dist proof initially failed because the matrix harness placed the
  internal probe env on standard cases while the rescue-smoke subprocess used
  the plain environment. The harness now proves the opposite custody boundary:
  standard cases stay clean, rescue smoke receives the exact internal probe
  token. Rerunning the packaged 265cc0cf dist passed five standard cases in
  22.452-24.913s with 10/10 scores and the installed CLI auto-rescue smoke in
  29.974s with zero issues. Final release-readiness still requires a rebuilt
  dist from the post-fix commit and the same installed matrix proof. That final
  rebuilt proof passed on dist odylith-local-release-0.1.15-f6a06af6: five
  standard cases completed in 20.223-22.425s with hard 10/10 scores, zero
  issues, complete governed artifacts, and the installed CLI auto-rescue smoke
  passed in 26.842s with zero issues.
  2026-06-28 brutal installed-dist audit reopened the release posture: a
  retained installed consumer repro for an open-source security embargo room
  failed before governed writes in 12.169 seconds because contrastive domain
  drift found `normalized` in generated artifacts. The saved
  `confirmed-intent.md` was the no-host Product Intent Confirmation guidance
  envelope rather than the visible operator confirmation, and the structured
  companion showed recovery defects such as `The product receive vulnerability
  reports`. This proves the earlier guidance-envelope isolation mechanism was
  incomplete: platform instruction language can still enter accepted intent
  recovery and then poison downstream artifact drift checks. The same brutal
  audit also found the latest installed rescue smoke still depends on an
  internal synthetic probe path, so it proves rescue wiring rather than real
  recovery from naturally occurring package or semantic failures. This bug
  remains release-blocking until the confirmed-intent source boundary is fixed
  generically, real installed create proof passes, and rescue proof no longer
  relies on synthetic success evidence.
  The next source checkpoint fixed the concrete source-custody and copy
  failures without adding domain terms: confirmed-intent envelope recovery now
  stops at generic guidance headings, `open source` no longer classifies a
  component as an adapter, adapter copy says accepted result instead of
  normalized result, and short first-path completion renders base action
  clauses through a modal phrase instead of producing `The product receive...`.
  The escaped open-source security embargo prompt is now a default installed
  matrix case, not an opt-in manual replay. A public two-component confirmed
  intent also exposed a separate false expert-lens blocker: the architect and
  engineer quality lenses required at least three active components even
  though the confirmed-create contract accepts two internal product systems.
  The lens now requires complete coverage of accepted internal systems and
  component specs rather than an arbitrary component-count floor. Source proof
  passed the focused parser/recovery/grammar/matrix guard tests, semantic
  drift and prompt-quality tests, engine and install-harness custody tests,
  the live create performance group, the exact open-source replay in 17.875s,
  and the two-component public replay in 15.473s. Release readiness is still
  blocked until a rebuilt installed dist passes the expanded eight-case matrix
  and the rescue lane is either proven by a non-internal natural repair or
  explicitly downgraded to wiring-only evidence.
  A subsequent sparse-confirmation replay exposed a separate pre-engine
  escape: a valid but terse confirmed-intent file with `State object: Report`
  failed before the post-confirm manifest because the completion renderer wrote
  `understand Report` into semantic public copy. This was not a domain defect
  and not a rescue-loop defect; it was a general grammatical phrase-rendering
  defect in confirmed-intent completion. One-word state labels now render as
  mid-sentence object phrases such as `the report`, the sparse confirmation
  replay writes governed records in 12.227s on the standard path, and the
  sparse confirmation shape is now part of the installed release matrix. The
  A full live-create suite then exposed one more false quality-lens blocker in
  the quantum communication case: the architect lens compared active
  first-release components against every accepted internal system and therefore
  rejected a valid topology where the live telemetry system was represented as
  a deferred component. The lens now checks semantic coverage of accepted
  internal systems across all component rows, while the engineer lens still
  requires rendered specs for active components. The quantum replay commits
  governed records in 18.010s on the standard path, and the quantum confirmed
  intent is now part of the installed release matrix. The matrix is now eight
  standard cases plus the internal rescue wiring smoke.
  Rescue remains wiring-only proof until a non-internal repairable failure is
  demonstrated or release reporting is explicitly downgraded.
  A fresh packaged installed matrix from committed dist
  `odylith-local-release-0.1.15-231bde74` proved that the previous release
  posture was still not acceptable. Seven standard cases and the installed
  rescue wiring smoke passed, but the quantum communication confirmed-intent
  case failed before governed writes because Atlas first-path Mermaid rendered a
  terminal node ending in the dangling phrase `QBER, and the key`. The accepted
  intent had the complete result-state tail: the key was established, saved,
  and viewable with prior runs. Root cause was generic, not quantum-specific:
  first-path semantics split a result-state modifier into a standalone step,
  visible-result copy left noun/status order as `key established`, and the
  terminal Atlas label preferred a long report-wrapper step over the semantic
  visible result, allowing Mermaid wrapping to clip the label into a bad noun
  tail. The banned mechanisms are explicit: do not weaken the clipped-label
  gate, do not add `key`, `QBER`, `quantum`, or any domain exception, and do not
  patch rendered Mermaid after package assembly. The fix must stay in semantic
  and projection owners: preserve result-state modifiers with the visible
  result, normalize status-modifier result items through shared phrase
  ownership, and choose the semantic visible result when a terminal step is only
  a long wrapper around that result. Pre-commit review then caught two generic
  regressions in that repair: widening the artifact-tail status vocabulary could
  turn unrelated component phrases into fake `state` artifacts, and apostrophes
  in possessive result phrases could disable comma-aware status normalization.
  The repair now keeps artifact-tail status modifiers conservative, separates
  result-status modifiers from artifact cleanup, treats apostrophes as ordinary
  possessive characters during comma splitting, and normalizes possessive result
  items such as `user's key established` into grammatical result order. Focused
  source proof covers the exact saved-intent shape, rejects the clipped Mermaid
  label, pins the artifact-tail leak repro, and pins the possessive result
  repro. A live source replay of the retained quantum intent wrote governed
  records in 16.746 seconds with four Radar records, four Registry specs, six
  Atlas diagrams, 19 trace nodes, and no clipped terminal label. Fresh rebuilt
  installed-dist proof from local release
  `odylith-local-release-0.1.15-7e548d40` then passed release smoke and the
  installed greenfield matrix. Eight standard consumer-lane cases completed in
  19.887-22.399 seconds: flood shelter intake, pediatric agency practice,
  semiconductor lab custody, port berth carbon tariff, security disclosure
  council, open-source security embargo, sparse disclosure confirmation, and
  quantum communication lab. Every standard case returned zero quality issues,
  wrote governed records, scored 10/10 across completion, latency,
  semantic-manifest, copy/semantic clarity, governance depth, traceability,
  implementation prompts, operator usefulness, and PM/architect/engineer/domain
  expert lenses. The quantum communication lab installed case completed in
  21.296 seconds with four Registry specs, six Atlas Mermaid sources, 19 trace
  nodes, and no clipped terminal label. The installed auto-rescue smoke also
  passed in 26.587 seconds with rescue activated and `post_confirm_rescue_probe`
  repaired. That rescue result remains wiring proof for the 90-second tier, not
  a naturally occurring rescue-quality scenario.
  A final release-proof checkpoint now avoids commit-hash recursion: the
  installable dist is built after the proof checkpoint commit, then must pass
  local-release smoke and the installed greenfield matrix. The matrix proves
  eight standard consumer-lane cases under 60 seconds with governed writes,
  zero quality issues, hard 10/10 scores, and all expert lenses passing. The
  retained quantum communication installed case must stay under 60 seconds with
  no clipped terminal label. Installed CLI auto-rescue smoke must stay under
  the 90-second rescue budget and is deliberately recorded as wiring-only
  proof, not natural rescue-quality proof.
  The wider artifact-quality suite then rejected two over-broad follow-up
  mechanisms before release: terminal Atlas labels were preferring bare semantic
  results for short, readable action labels such as `Publish a decision packet`
  and `Receive one follow-up reminder`, and evidence-boundary adapter recovery
  initially treated ordinary history/timeline view components as external
  adapters. The fix narrowed terminal result preference to long clipping-risk
  result wrappers only, and narrowed source-backed adapter recovery to strong
  evidence-boundary names such as audit/trail/source/attachment/provenance plus
  external source/repository/provider context, with component-kind classification
  moved into its own owner instead of bloating confirmed component assembly. The
  repaired artifact-quality and prewrite pack passed 61 tests in 328.35 seconds.
  A 2026-06-28 release-proof audit found a separate custody gap outside the
  semantic compiler itself: the standard installed matrix had grown into a
  meaningful release proof, but canonical release-candidate/preflight proof did
  not require it. The default installed matrix was expanded from eight to
  twelve standard high-variance domains, strict matrix scoring now requires all
  case-declared domain anchors, matrix JSON can be persisted as a release proof
  artifact, and the rescue leg is explicitly marked as
  `synthetic_typed_probe_wiring_only` with `natural_rescue_quality_proven:
  false`. The current c6286f0a installed package passed the expanded twelve-case
  standard matrix in 19.834-22.057 seconds with zero issues and hard 10/10
  scores before the new stricter metadata fields were added. CB-208 remains open
  because this does not prove natural rescue from a non-internal repairable
  failure and does not finish full host-authored SemanticModelIR/ArtifactPlanIR
  repair as the normal rescue substrate.
  2026-06-28 brutal source-local repro found a fresh SemanticModelIR custody
  gap before the next variance pass. A confirmed first path using overloaded
  `record` as both noun and verb (`Record owner records a record, compliance
  records review evidence, and the office records readiness`) let the
  first-path model select `Recorded readiness` as the visible result, but
  `GreenfieldSemanticModel.first_path_contract.events` marked no event as the
  visible-result owner because the event floor returned early once three
  events existed. The final semantic quality gate correctly rejected the
  inconsistent IR before governed writes. The repair belongs in SemanticModelIR
  construction, not in project terms, issue-message parsing, rendered copy
  repair, or a weakened gate: when a selected visible result exists and no
  event owns it, the terminal event now becomes the visible-result owner.
  Focused semantic/repetition/patch-planner proof passed 28 tests in 0.52s;
  the retained record-as-noun/verb replay committed records in 15.53 seconds
  with a standard passed manifest, no rescue, zero final issues, and temp
  cleanup; and a second hostile Review Status Board replay completed standard
  create after one safe generated-copy cleanup pass. This closes only the
  SemanticModelIR event-ownership gap. Natural installed rescue quality remains
  unclaimed until a non-internal repairable final-gate failure proves
  host-planned semantic or artifact-plan repair under the 90 second rescue
  budget.
  The next hostile source-local matrix passed seven of eight cases but failed
  water-rights hearing evidence before governed writes. The first pass reported
  Radar `generated_copy_quality` findings for awkward visible-result action
  prose, auto-escalated to rescue, then stopped with `no_progress` because the
  PatchSet operations carried empty replacement facts. Root-cause inspection
  found two generic owners: visible-result phrase projection rendered readiness
  objects as `reach ... readiness`, and the public-copy classifier treated
  title-label words and hyphenated noun compounds such as `Water Use Claim` and
  `water-use claim` as action verbs near result/status words. The fix stays out
  of rendered-string repair and project vocabulary: readiness/status-like
  result objects now project as see-style actions, and generated-copy token
  metadata preserves hyphen and title-label context before classifying
  `reach/use result` shapes. Focused regressions pin both the false positive
  and the true positive, and the retained water-rights replay now commits
  governed records in 15.681 seconds with a standard passed manifest, zero
  issues, all expert lenses passing, and temp cleanup. This proves another
  standard-path owner fix, not natural rescue readiness.
  A 2026-06-28 brutal source-local eval reopened release readiness for the
  current working tree. The focused actor-led prompt/gerund regression pack
  passed, and the known `intaking coordinator` / `user can intake coordinator
  records` false-negative class was moved into shared actor/prose-shape
  ownership, but a real source-local post-confirm create for the retained
  battery-materials readiness scenario still failed in 24 seconds before
  governed writes because the Project Brief preview had a clipped phrase
  ending in `or`. The widened greenfield quality pack also failed 14 tests
  while passing 284, including over-broad gerundized actor-role detections on
  legitimate evidence/review component copy, comma/list regression fallout, and
  confirmed-intent create failures. This proves two mechanism-level lessons:
  the shared shape detector must distinguish corrupted actor-role grammar from
  valid evidence/review noun phrases, and live post-confirm release scoring
  must be capped to non-release-ready whenever the standard path fails or the
  broad greenfield pack is red.
  A later 2026-06-28 source-local repair pass closed the next escaped classes
  without adding project-domain rules or returning repair authority to rendered
  prose. Durable failures captured in this pass: text `greenfield propose`
  emitted a host-instruction envelope instead of a confirmable Product Intent
  artifact; sequence-step splitting treated coordinated object-list tails such
  as `checks, and final status` as new actions; plural modal actor clauses such
  as `digestive health patients can log...` were singularized into invalid
  finite verbs; next-step handoff prompts echoed Radar
  `recommended_first_slice` prose across Radar, accepted-project, and operator
  surfaces; canonical first-path event repetition was misclassified as
  noncanonical package repetition; and artifact-draft cleanup was temporarily
  too broad for whole accepted-project preview trees. Fixes stayed generic and
  source-owned: Product Intent Confirmation now renders concrete sectioned
  product intent; first-path sequence ownership preserves coordinated object
  lists and modal actor capability chains; package repetition allows complete
  semantic-custody event facts while still rejecting noncanonical boilerplate;
  next-step prompts preserve the accepted first path without duplicating Radar
  slice prose; structural-copy filtering is shared; and mechanical artifact
  repair is limited to exact collected public-copy projections. Proof:
  expanded affected greenfield suite passed 106 tests in 414.34 seconds;
  focused modal/live/sequence regression pack passed 19 tests in 190.09
  seconds; six fresh source-local operator-flow projects completed
  propose-save-confirm-create, scored 10/10 under the brutal hard-min release
  scorer, and deleted temp repos: hospital sterile instrument recall 23.127s,
  satellite thermal anomaly triage 23.207s, drought water-rights transfer
  ledger 24.639s, battery recycling hazmat custody 22.815s, cryptographic key
  ceremony readiness 23.949s, and workplace accommodation plan review 24.279s.
  This proves the current source-local standard path for the tested variance;
  installed-dist matrix proof is still required before a release claim.
  Cross-surface governance learning from this pass applies beyond greenfield:
  Casebook, Registry, Atlas, Compass, technical plans, release proof, and
  operator prompts must be judged as governed artifact packages, not as loose
  Markdown or dashboard text. A generated record is not acceptable merely
  because it exists or validates structurally; it needs source-owned semantic
  facts, surface-local custody, readable grammar, non-repetitive copy, precise
  proof obligations, exact stale/fresh state, and an actionable next decision.
  Failed mechanisms to avoid across day-to-day ops are the same ones banned in
  post-confirm: repairing rendered prose instead of the source fact, inferring
  repair ownership from diagnostic sentences, treating role/surface labels as
  projection IDs, refreshing dashboards while Atlas/Registry truth is stale,
  logging shallow Compass claims without validation evidence, and scoring
  record counts as quality. Future governance-generation work should use the
  same pattern proven here: update the owned source record first, refresh only
  the owned generated surfaces through CLI paths, fail closed on stale
  diagrams or unmapped meaningful Registry events, and keep release/readiness
  claims capped until the artifact package passes punitive multi-lens checks.
  A 2026-06-28 Atlas coverage pass exposed a related visibility failure mode:
  newly scaffolded diagrams D-045 and D-046 existed in source and catalog truth
  but were not operator-visible until SVG/PNG assets and the Atlas payload were
  rendered. The source-local auto-update path correctly fell back to the static
  Odylith-generated flowchart renderer when Chromium launch degraded, refreshed
  D-040/D-043/D-045/D-046, and verified 46 fresh diagrams with D-045 assets
  present. The durable rule is that Atlas source truth alone is insufficient
  proof for architecture updates; any new or updated diagram must also prove
  rendered asset presence and payload visibility before completion is claimed.
  A follow-up operator check on 2026-06-28 exposed that the prior visibility
  proof was still too shallow: D-045 was active, rendered, and present in the
  payload, but it disappeared from B-142 workstream navigation because the
  Atlas renderer inferred B-142 from `related_backlog` for surface links and
  then `_attach_diagram_workstream_relationships` overwrote
  `related_workstreams` with only explicitly authored workstream rows. The fix
  preserves backlog-derived `idea_id` ownership during relationship attachment,
  and the regression proof verifies D-045 is fresh, owned by B-142, present in
  `diagram_related_workstreams`, and visible alongside D-043 and D-046 under
  the B-142 filter. Failed mechanism to avoid: treating payload existence or
  asset presence as Atlas visibility proof without checking route/filter
  indexes and tooltip lookup ownership.
  Independent architecture review on 2026-06-29 found the current
  canonical-projection repetition fix is still type-shaped rather than fully
  typed: `greenfield_canonical_projection_facts.py` builds richer fact rows and
  then flattens them to text values, while `greenfield_package_quality.py`
  consumes string allowlists and accepted-intent prose rather than fact IDs,
  source paths, semantic node IDs, and sanctioned projection roles. The
  immediate wildfire fix deliberately did not extend that pattern. Next repair
  must preserve typed projection provenance end-to-end and remove raw
  accepted-intent repetition allowances once projection aliases are attached to
  actual semantic facts.
  A 2026-06-29 source-local clinical-trial and biobank follow-up closed a
  separate release-scoring false positive without returning to rendered-prose
  repair. The clinical replay wrote complete governed records in 26.920s but
  collapsed beneficiary advocate, domain operator, risk owner, and evidence
  owner into one visible proof reviewer label while the matrix still awarded
  10/10. Independent review caught the failed mechanism: checking CLI create
  payload rows alone is not persisted artifact proof, and forced role
  separation regresses valid explicit many-hat actors. The fix adds
  `actor_source` provenance to Tribunal visible actors, permits shared labels
  only for accepted explicit actors, requires generated judgment actors to use
  role-appropriate labels, and makes the matrix compare create payload actor
  rows with persisted accepted-project preview readback. A later biobank replay
  then caught a second false positive where an internal evidence system,
  `Specimen Link Ledger`, was projected as evidence owner; actor selection now
  excludes evidence objects/systems and prefers explicit human or review-role
  actors. Focused actor/readback proof passed six targeted tests and the full
  proposal/matrix pack passed 85 tests in 86.30s.
  The same pass fixed a typed semantic omission found by the broader quality
  pack: legacy host proposals could reach the architect lens without an
  explicit external-system boundary. `greenfield_apply_semantic.py` now uses
  explicit accepted external systems when present, infers from first-path
  external-boundary rows when available, or records a generic deferred manual
  or fixture-backed boundary instead of leaving the lens empty. This is a
  SemanticModelIR input repair, not a phrase filter. The post-confirm live
  harness also now verifies temp repo deletion survives background runtime
  residue from locks and Compass caches before moving on.
  The follow-up source-local matrix on 2026-06-29 used ten fresh domains not
  reused from the maintained installed case catalog: sepsis antibiotic
  stewardship, lunar regolith mining permits, indigenous language archive
  consent, autonomous rail-yard safety, mangrove carbon-credit verification,
  special-education accommodation review, esports anti-cheat appeals,
  decentralized identity recovery, food-allergen recall trace, and wildfire
  insurance claims. Every run used no-write `greenfield propose` output as the
  confirmed intent, then executed confirmed `greenfield create`; every case
  committed governed writes, scored 10/10 across completion, latency, semantic
  manifest, copy/semantic clarity, governance depth, traceability, operator
  usefulness, Project implementation prompts, PM, architect, engineer, and
  domain-expert lenses, and produced four Radar workstreams, three Registry
  specs, six Atlas sources, twelve rendered Atlas assets, six rendered
  surfaces, twelve payloads, twenty Compass records, project/release/program
  records, eighteen trace nodes, and zero quality issues. Create timings were
  22.072-23.827s and whole-project timings were 15.521-16.534s. Every temp repo
  and the parent matrix root were deleted. This is strong source-local standard
  proof, but installed release readiness remains unclaimed until the fresh dist
  matrix and rescue proof pass.
  A later exact-leaf artifact-draft checkpoint removed the broad rendered
  preview repair authority that still survived in package cleanup. Safe
  mechanical cleanup now requires an exact artifact-draft target path owned by
  `greenfield_artifact_plan.py`; `project_brief_preview`, `next_steps_preview`,
  `compass_memory_preview`, accepted-project preview, and project-dashboard
  prompt leaves can be repaired only at the named scalar leaf. Whole preview
  roots and row-level dashboard prompts fail closed. Legacy generated-copy
  findings no longer create `safe_package_repair` operations from
  category-suffixed broad paths such as `prewrite_package.next_steps.*`; when a
  source-owned exact finding exists, the stale broad finding is suppressed, and
  remaining legacy generated-copy findings route to plan/projection ownership.
  Independent reviewer follow-up reproduced exact Compass memory repair and
  confirmed no broad `next_steps` safe-repair target remained. Focused proof
  passed 41 artifact-plan and quality-repair tests, and the widened
  post-confirm repair/engine/projection-rerender set passed 76 tests in 50.17s.
  A 2026-06-30 rescue-custody audit found a remaining failed mechanism:
  source-owned findings could still mark generic `SemanticModelIR` or
  reviewer-lens roots as `semantic_patch`, `greenfield_post_confirm_patchset.py`
  would emit a generic `semantic_fact` operation, and the semantic executor
  would correctly no-op because no concrete patchable slot was named. That made
  auto-rescue look repairable while it had no executable target. The source fix
  removes the generic semantic operation kind, suppresses semantic PatchSet
  operations unless the finding names a supported slot such as first path,
  proof boundary, state object, human actors, or system boundaries, and makes
  the post-confirm engine require a non-empty PatchSet before activating
  rescue from auto mode. Unsupported semantic roots now fail closed with exact
  blockers instead of spending rescue budget on a no-op. Focused proof passed
  the post-confirm engine, patch-payload, semantic executor, quality-repair,
  artifact-plan patch, and projection-rerender suite: 97 tests in 46.13s.
  Follow-up cleanup on 2026-06-30 removed the remaining rendered-artifact
  mutation authority instead of broadening the repair stack. The prewrite
  package path now uses read-only package inspection; the compatibility repair
  functions return the original package unchanged; final next steps fail
  closed on generated-copy defects instead of running a repair probe; generated
  copy findings route to `ArtifactPlanIR` as `plan_patch`; `safe_package_repair`
  was removed from the post-confirm and Tribunal repairability allow-lists; and
  patchsets no longer produce `artifact_draft_set` operations. Focused contract
  proof passed 42 tests in 34.85s after the cleanup, and semantic rescue proof
  passed 23 targeted tests after adding idempotent host-adjudication ledger
  support. Do not reintroduce rendered-copy mutation as a shortcut for premium
  artifact quality.
  Fresh installed matrix proof against committed dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-de17cdda`
  shows the new boundary is directionally right but incomplete. The package no
  longer mutates rendered drafts, natural structured semantic rescue now passes
  in 62.823s, and cleanup/leakage proof passes, but 4/13 standard cases fail
  because generated-copy findings route to `plan_patch` without an executable
  artifact-plan repair. The failing manifests all contain one repairable
  `generated_copy_quality` issue, `repair_owner=artifact_plan_projector`,
  `target_layer=artifact_plan`, and an addressed preview path, but no Tribunal
  plan operation and no repaired issue code. This is the precise residual debt:
  typed issue routing exists, yet the semantic/artifact-plan patch substrate
  cannot currently change the projection fact that produced the bad preview.
  Any next fix that restores `safe_package_repair`, mutates
  `ArtifactDraftSet`, or stacks phrase-specific regex cleanup repeats a failed
  mechanism. The next acceptable fix must repair sanctioned `ArtifactPlanIR`
  facts or invoke schema-constrained host reasoning to produce a typed
  artifact-plan patch, then rerender and revalidate.
  Follow-up implementation on 2026-06-30 added that missing projection-source
  repair seam without restoring rendered-copy mutation. The new resolver maps
  rendered preview quality findings back to executable SemanticModelIR or
  ArtifactPlanIR source facts before PatchSet creation. Artifact-plan planner
  envelopes now become `{path, value}` patches, the artifact-plan executor keeps
  custody over sanctioned proposal roots, and scoped rerender includes the
  Project dashboard preview as a downstream projection. The failed mechanism
  also exposed a false-positive path: `mermaid_source` leaves inside
  accepted-project previews were typed as free prose, so graph syntax could
  trigger duplicate-word gates. They are now typed as Mermaid source and checked
  through visible label units. Focused tests prove source-target mapping,
  artifact-plan patch materialization, dashboard rerender, Mermaid source label
  custody, and no rendered preview mutation. Source-local repros for all four
  `de17cdda` failed cases now pass under 23s with committed governed writes.

- Related Incidents/Bugs: CB-207

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_engine.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_repair.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_findings.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_package_findings.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_rescue_planner.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_patch_apply.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_patchset.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_rescue_probe.py
- src/odylith/runtime/domain_intelligence/greenfield_workstream_risk_projection.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_repair.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_components.py
- src/odylith/runtime/domain_intelligence/greenfield_component_kinds.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py
- src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py
- src/odylith/runtime/domain_intelligence/greenfield_sequence_terminal_labels.py
- src/odylith/runtime/domain_intelligence/greenfield_semantic_compiler.py
- src/odylith/runtime/domain_intelligence/greenfield_status_modifiers.py
- src/odylith/runtime/domain_intelligence/greenfield_text.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_text_model.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_recovery.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_text_model.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_helpers.py
- src/odylith/runtime/domain_intelligence/greenfield_release_scope_limits.py
- src/odylith/runtime/domain_intelligence/greenfield_quality_lens_repair.py
- src/odylith/runtime/domain_intelligence/greenfield_artifact_plan_patch_executor.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_recovery.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_completion.py
- src/odylith/runtime/reasoning/tribunal_lens.py
- src/odylith/runtime/artifact_quality/greenfield_quality_lenses.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_patchset.py
- src/odylith/runtime/domain_intelligence/greenfield_apply_semantic.py
- src/odylith/runtime/domain_intelligence/greenfield_external_boundary_semantics.py
- src/odylith/runtime/domain_intelligence/artifact_tribunal_actors.py
- src/odylith/runtime/domain_intelligence/greenfield_sequence_steps.py
- src/odylith/runtime/domain_intelligence/greenfield_structural_copy.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_step_roles.py
- src/odylith/runtime/domain_intelligence/greenfield_generated_prose_shape.py
- src/odylith/runtime/domain_intelligence/greenfield_gerund_actions.py
- src/odylith/runtime/common/prose_grammar.py
- src/odylith/runtime/common/mermaid_text.py
- src/odylith/runtime/artifact_quality/generated_copy_quality.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_fragments.py
- src/odylith/runtime/domain_intelligence/greenfield_artifact_plan.py
- src/odylith/runtime/domain_intelligence/greenfield_prewrite_projection_rerender.py
- src/odylith/runtime/domain_intelligence/greenfield_semantic_patch_executor.py
- src/odylith/runtime/domain_intelligence/greenfield_artifact_plan_patch_executor.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_backlog_text_model.py
- src/odylith/runtime/reasoning/tribunal_engine.py
- src/odylith/runtime/reasoning/tribunal_patch_planner.py
- src/odylith/runtime/artifact_quality/greenfield_rendered_artifacts.py
- src/odylith/runtime/artifact_quality/greenfield_project_prompt_quality.py
- src/odylith/runtime/artifact_quality/greenfield_package_quality.py
- src/odylith/runtime/surfaces/generated_flowchart_assets.py
- scripts/release/greenfield_rescue_smoke.py
- scripts/release/local_release_smoke.py
- scripts/release/greenfield_post_confirm_matrix.py
- src/odylith/runtime/domain_intelligence/greenfield_apply_prewrite.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_experience.py
- src/odylith/runtime/project_intelligence/source_launch.py
- tests/unit/runtime/test_greenfield_post_confirm_patch_payload.py
- tests/unit/runtime/test_greenfield_post_confirm_projection_rerender.py
- tests/unit/runtime/test_greenfield_confirmed_surfaces.py
- tests/integration/runtime/test_greenfield_hiit_post_confirm_quality.py
- odylith/atlas/source/domain-intelligence-greenfield-governance.mmd
- odylith/atlas/source/greenfield-first-path-semantic-copy-custody.mmd
