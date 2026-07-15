- Bug ID: CB-223

- Status: Open

- Created: 2026-07-07

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Greenfield post-confirm completion promotes evidence-list nouns into user capability copy

- Impact: Installed volume-discovery post-confirm create stopped before governed writes for soil nutrient prescription after confirmed intent because generated proposal copy leaked modal/base-form grammar drift.

- Components Affected: domain-intelligence

- Environment(s): local installed release matrix dist 0.1.15 d696aff3, volume-discovery shard 004, case hv-20260703-g-036

- Detected By: greenfield matrix volume-discovery campaign

- Failure Signature: semantic.slop.modal.base.form.grammar.drift.leaked.proposal.intent; proposal.backlog.0.product_view rendered the user can yield maps

- Follow-up Failure Signature: `sequence_event_steps` split `and a final disengagement review recommendation` out of a long `using` evidence list as a standalone action step. The earlier actor-led open-action guard did not cover the finite-action classifier used by comma-piece custody.

- Adversarial Review Finding: The first follow-up implementation accepted any short nominal result before action classification and therefore absorbed real result-led finite clauses such as `selected plan routes the case` and `final report summarizes evidence` into the prior evidence list.

- Trigger Path: GREENFIELD_MATRIX_VOLUME_CASE_FILES=/private/tmp/odylith-current-source-grounded-shards/shards/volume-discovery-004.cases.json make greenfield-matrix-campaign VERSION=0.1.15 DIST=/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-d696aff3

- Ownership: domain-intelligence first-path parser, confirmed-completion text model, and visible-result projection

- Timeline: Captured 2026-07-07 through `odylith bug capture`.

- Blast Radius: Any greenfield prompt where a transformation first path carries using/with evidence lists and a terminal final recommendation or explanation

- SLO/SLA Impact: Post-confirm no-write failure; release readiness blocked until exact failed-subset and volume replay pass

- Data Risk: No governed records were written; risk is failed project creation and contaminated generated artifacts if the gate were weakened

- Security/Compliance: No direct security exposure; regulated/scientific proposal quality can be misrepresented if evidence terms become user actions

- Invariant Violated: Post-confirm compilers must project from typed first-path facts and must not treat supporting evidence nouns or final result nouns as user actions

- Root Cause: The first-path splitter broke comma-separated using evidence into standalone steps; completion action_phrase promoted later evidence fragments into user-can product-view copy; actor-led open-action parsing misread final recommendation nouns as actor/action; visible-result focus did not consistently preserve terminal final recommendation/explanation outcomes.

- Follow-up Root Cause: `_continues_adverbial_object_list` asked the generic explicit-subject action classifier about an article-led terminal result noun. The phrase contained the homonym `review`, so the classifier treated it as a verb before the existing short nominal result owner could adjudicate it.

- Solution: Keep using/with evidence lists attached to the source action, prefer representative human action for user-can copy, reject final-result noun phrases in actor-led open-action parsing, preserve transformation actions separately from terminal visible results, and focus terminal final recommendation/explanation tails without collapsing decision-package final status.

- Follow-up Solution: Route comma-piece custody through the existing `short_nominal_result_phrase` owner only after rejecting phrases with an internal finite verb token. This keeps terminal result nouns attached to the evidence list without adding duplicate domain vocabulary and preserves real result-led follow-on actions.

- Verification: Source unit proof: 179 greenfield parser/projection tests passed. Required next proof: rebuild dist, rerun exact failed-subset case hv-20260703-g-036, rerun volume shard/volume campaign, then release-proof.

- Follow-up Verification: Adversarial review exposed and then verified the result-led finite-action counterexample. The full confirmed-diagram, first-path modal, and generated-slop suites passed 165 tests after both the terminal recommendation and real finite-action cases were added.

- Workaround: None acceptable for release. The post-confirm transaction must continue to fail closed before governed writes until parser/projection custody produces clean artifacts.

- Monitoring Updates: Track exact failed-subset replay, original shard 004 replay, volume campaign replay, and release-proof results before changing status from Open.

- Version/Build: Escaped in local installed release matrix dist 0.1.15 d696aff3; source fix is pending rebuild and installed replay proof.

- Config/Flags: `GREENFIELD_MATRIX_VOLUME_CASE_FILES` shard replay and `make greenfield-matrix-campaign VERSION=0.1.15 DIST=<local-release-dist>` with browser/rescue defaults controlled by the matrix runner.

- Prevention: Regression tests cover soil nutrient evidence-list action custody, evidence tails followed by real carried-subject actions, final recommendation/explanation noun handling, actor-led open-action noun rejection, and first-path subject extraction split under 800 LOC.

- Agent Guardrails: Do not add domain vocabulary; do not weaken semantic slop gates; do not patch rendered Radar/Registry/Atlas strings after projection; fix parser/projection custody owners.

- Preflight Checks: Run focused parser/projection tests before installed replay; do not claim release readiness from source-local proof.

- Regression Tests Added: tests/unit/runtime/test_greenfield_preconfirm_slop_regressions.py::test_using_evidence_list_does_not_become_user_can_action; tests/unit/runtime/test_greenfield_preconfirm_slop_regressions.py::test_using_evidence_tail_can_still_split_follow_on_carried_subject_actions; tests/unit/runtime/test_greenfield_preconfirm_slop_regressions.py::test_final_explanation_result_does_not_become_user_can_plan_action; tests/unit/runtime/test_greenfield_first_path_modal_semantics.py::test_actor_led_open_action_rejects_bare_final_recommendation_noun

- Related Incidents/Bugs: CB-215, CB-221, CB-222

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_first_path_action_split.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_text_model.py
- src/odylith/runtime/domain_intelligence/greenfield_visible_result_focus.py
