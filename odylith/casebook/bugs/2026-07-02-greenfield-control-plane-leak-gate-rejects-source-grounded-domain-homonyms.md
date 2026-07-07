- Bug ID: CB-216

- Status: Open

- Created: 2026-07-02

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Confirmed greenfield create can fail before governed writes when a real product-domain word is also an Odylith surface name and the control-plane leak gate drops that word from its accepted-intent source-term set.

- Impact: A valid confirmed create can stop with no governed records written even though the suspicious term is grounded in the accepted product intent.

- Components Affected: domain-intelligence

- Environment(s): Maintainer source-local disposable greenfield create on branch 2026/freedom/v0.1.15.

- Detected By: Disposable high-variance source-local create using a geospatial validation request while proving completion-priority behavior.

- Failure Signature: greenfield public product content leaks Odylith control-plane term Radar at program.blueprint.child_workstreams.0, program.waves.0.workstream_titles.0, release_plan.target_workstream_titles.0, +23 more

- Trigger Path: odylith greenfield create --repo-root <temp-repo> --prompt <source-grounded homonym request> --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1 --json

- Ownership: Domain Intelligence greenfield quality gate and accepted-intent source-term custody.

- Timeline: 2026-07-01: A disposable landslide validation create failed on a source-grounded homonym. The first fix expanded accepted-intent term sources but the arbitrary top-term cap still dropped the short homonym. Removing the cap and walking structured intent text fixed the replay.

- Blast Radius: Any greenfield prompt whose legitimate domain vocabulary overlaps Odylith surface names such as Radar, Registry, Atlas, Compass, or Tribunal.

- SLO/SLA Impact: Violates the non-negotiable post-confirm completion objective by blocking governed records before write.

- Data Risk: No governed records were written in the failed disposable run; accepted intent and captured error remained available for replay.

- Security/Compliance: No direct security exposure; governance-trust and release-readiness risk are high because a false-positive platform gate blocks valid product language.

- Invariant Violated: Control-plane leak detection must reject ungrounded Odylith surface leakage without rejecting homonyms that are present in accepted product intent.

- Workaround: No consumer workaround. Do not rename the user domain or hand-edit proposal JSON; fix Odylith source-term custody and rerun confirmed create.

- Root Cause: The quality gate only trusted a small prompt/title/summary term cone and then truncated ordered accepted terms to twelve entries. Verbose accepted intent could push a short legitimate homonym out of the trusted set, so the same word was misclassified as an Odylith control-plane leak.

- Solution: Use the structured accepted-intent text cone for prompt/title/summary/product story/product view/state object/first path/proof boundary/actors/systems/assumptions/ambiguities/non-goals and remove the arbitrary top-term cap. The fix remains generic: it admits only terms grounded in accepted intent and keeps ungrounded Odylith surface names blocked.

- Rollback/Forward Fix: Forward fix only in greenfield quality-gate term custody.

- Verification: Targeted tests passed for source-grounded homonym allowance and ungrounded control-plane leakage rejection. The original disposable create then completed in 27.511s outer time with manifest passed, validation_status passed, issue_count 0, write transaction committed, 4 backlog records, 3 components, 6 diagrams, and temp cleanup.

- Follow-up Learning: The high-volume seeded batch on 2026-07-02 exposed a
  related but stronger homonym custody failure. Once source-title recovery
  preserved legitimate product frames such as `weather radar calibration setup`
  and `geologic atlas field mapping setup`, the control-plane leak gate still
  treated public product uses of `Radar` and `Atlas` as Odylith leakage because
  term-normalized source matching was too coarse (`atlas` could normalize away
  from the literal leak label, and `radar scan` could appear with adjacent
  action context rather than only the title context). The repair moved homonym
  custody from whole-term membership to local source-grounded token windows:
  product uses are allowed only when each visible occurrence overlaps accepted
  prompt, source-title, title, or first-path context, while ungrounded
  `Atlas diagram` / `Radar` control-plane copy remains blocked. Focused proof
  passed the source-grounded `Atlas` domain case, the ungrounded Atlas diagram
  rejection case, and the full confirmed-intent recovery suite.

- 2026-07-07 Follow-up Learning: The committed-head installed volume replay
  reopened the same custody class on `single cell perturbation atlas`. The
  first blocker was legitimate public product copy containing `Atlas Review`,
  where the second `Atlas` came from confirmed typed sections rather than the
  original prompt/title cone. The repair now trusts canonical confirmed product
  sections for confirmed generated proposals while keeping a hard platform
  context guard for `Odylith Atlas`, `Atlas diagram`, `Atlas surface`,
  Mermaid/catalog/dashboard contexts, governance-flow collocations, and
  control-plane copy. The same replay exposed a second-order slop path: the
  prompt note `The request uses record both as an action and as a governed
  object` could leak through evidence anchors and visible-result extraction as
  `reach an action and as a governed object`. Source repair now classifies
  word-sense/request-meta clauses as requirement-control metadata, strips them
  before first-path and visible-result projection, excludes them from evidence
  anchors, rejects leading metadata and declared visible-result/proof-boundary
  fallback contamination, and adds a semantic slop tripwire if that phrase
  family reaches generated artifacts. Focused proof passed 22 affected regressions; exact
  source-local replay of the single-cell failed prompt committed records with
  post-confirm manifest passed, issue_count 0, validation passed, 4 Radar
  records, 3 Registry components, 6 Atlas diagrams, and zero source-record hits
  for the escaped Atlas/platform and word-sense leak signatures.

- Prevention: Do not use arbitrary top-N source-term caps for semantic leak detection. Prefer structured accepted-intent evidence and keep control-plane leakage rejection tied to whether the term is grounded in user-accepted product meaning.

- Agent Guardrails: When a platform leak gate flags a word that is also ordinary domain vocabulary, first check accepted-intent grounding before adding a term exception or weakening the gate.

- Preflight Checks: Search existing control-plane leakage and domain-term Casebook records; prove both homonym allowance and ungrounded Odylith surface rejection.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_quality_gate_allows_control_plane_homonym_from_accepted_intent; tests/unit/runtime/test_greenfield_source_addressed_repair.py::test_greenfield_quality_gate_uses_confirmed_sections_for_atlas_review_homonym; tests/unit/runtime/test_greenfield_source_addressed_repair.py::test_confirmed_homonym_context_still_rejects_ungrounded_atlas_surface_copy; tests/unit/runtime/test_greenfield_source_addressed_repair.py::test_confirmed_homonym_context_rejects_source_laundered_atlas_surface_copy; tests/unit/runtime/test_greenfield_prompt_source_high_variance.py::test_visible_result_object_ignores_word_sense_metadata_tail; tests/unit/runtime/test_greenfield_prompt_source_high_variance.py::test_evidence_anchors_ignore_word_sense_metadata_requirements; tests/unit/runtime/test_greenfield_prompt_source_high_variance.py::test_semantic_slop_gate_rejects_word_sense_metadata_as_visible_result.

- Related Incidents/Bugs: CB-215, CB-209, CB-184

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_quality_gate.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_control_steps.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_fragments.py
- src/odylith/runtime/domain_intelligence/greenfield_evaluation_semantics.py
- src/odylith/runtime/domain_intelligence/greenfield_semantic_compiler.py
- src/odylith/runtime/domain_intelligence/greenfield_semantic_quality.py
- tests/unit/runtime/test_greenfield_proposals.py
