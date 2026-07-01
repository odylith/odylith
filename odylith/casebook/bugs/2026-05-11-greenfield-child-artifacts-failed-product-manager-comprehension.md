- Bug ID: CB-198

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-11

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield child artifacts failed product manager comprehension

- Impact: Confirmed greenfield child workstreams, Registry component IDs, and Atlas diagram slugs could read like governance preparation instead of the business/product work a project owner asked Odylith to create.

- Components Affected: domain-intelligence

- Environment(s): Odylith greenfield create/apply against an empty consumer repo with an external-domain prompt.

- Detected By: Operator screenshot review and source audit of a consumer Radar B-002, Registry specs, Atlas slugs, and accepted-project state.

- Failure Signature: Radar B-002 used generic Decision Basis lines such as created as a new queued workstream and deeper scope decomposition waits; Registry and Atlas inherited the full prompt slug instead of a compact domain artifact identity.

- Trigger Path: odylith greenfield create --repo-root . --prompt <greenfield project intent> --release 0.0.1 --confirm, then open Radar B-002 and related Registry/Atlas artifacts.

- Ownership: Domain Intelligence greenfield projection, Radar backlog authoring, Registry component scaffolding, Atlas diagram scaffolding.

- Timeline: Captured 2026-05-11 through `odylith bug capture`.

- Blast Radius: Greenfield child workstreams, Radar INDEX rationale, component directories/specs, Atlas diagram slugs, accepted-project topology links, and Project tab source graph.

- SLO/SLA Impact: Breaks the first-read product-manager test before implementation planning starts.

- Data Risk: No production data loss; affected consumer repos may retain low-quality generated governance records until regenerated or repaired.

- Security/Compliance: In regulated domains, vague prep language and prompt-shaped IDs can obscure ownership, compliance, proof, and release-boundary responsibilities.

- Invariant Violated: A confirmed greenfield proposal must produce product-relevant artifacts shaped by project intelligence, not raw prompt repetition or generic governance preparation text.

- Root Cause: Greenfield rows carried product-specific content, but Radar authoring discarded product-specific rationale when rationale_lines crossed through the generic backlog create namespace; component and diagram slugs also inherited the raw project prompt.

- Solution: Preserve product-derived rationale through backlog authoring and use compact domain artifact slugs for generated Registry and Atlas artifacts.

- Follow-Up Evidence (2026-06-09 / Dignity-shaped confirmed create): A v0.1.15 local install transcript for a dignity-and-agency app exposed a broader comprehension failure: child workstreams could inherit parent setup actions, action-shaped outcomes rendered as object phrases such as `shows open`, component labels repeated conjunctions, `Grown-up` casing flattened, and repetitive implementation-slice template text appeared across Radar surfaces even when the post-confirm gate passed.

- Follow-Up Root Cause (2026-06-09): Confirmed-create used the same first-path action string across program and child rows without preserving actor ownership, downstream completion/enrichment layers treated action-shaped outcomes as visible objects, generated-copy gates did not reject presentational/action splices or repeated implementation templates, and component/title normalization did not distinguish setup actions, terminal outcomes, weak reflection artifacts, hyphenated role terms, or repeated conjunction chains.

- Follow-Up Solution (2026-06-09): Preserve actor-owned workflow actions for child titles and copy, prefer terminal outcome titles only for strong outcome nouns, render action-shaped outcomes as user capabilities instead of objects, gate presentational/action splices and repeated implementation-slice templates, normalize repeated component conjunction chains, preserve hyphenated terms such as `Grown-up`, and repair gerund/base-form conversion for action chains such as accepting or dismissing a suggestion.

- Follow-Up Evidence (2026-06-09 / installed post-confirm hard stop): A v0.1.15 local install transcript for a medication-tracking app showed the post-confirm package gate failing before any governed records were written because title-case workstream/component prose containing `Their` was treated as mid-sentence capitalization drift. The same replay also exposed generic actor and state-object label drift: comma-led actor descriptions could become visible actor names, acronym-number labels could be flattened, and `The durable thing the product holds is ...` could survive as the state-object label instead of the actual domain object.

- Follow-Up Root Cause (2026-06-09 / installed post-confirm hard stop): The package-quality gate treated all capitalized possessive pronouns after token zero as prose drift, even when they appeared inside title-case artifact labels. Actor extraction split comma-gerund descriptions too late, role-only fallback overused project focus, title normalization lacked a generic acronym-number restoration pass, and confirmed-text state-object extraction did not cover durable-object phrasing.

- Follow-Up Solution (2026-06-09 / installed post-confirm hard stop): Make the capitalization gate distinguish prose drift from title-case labels, keep comma-gerund actor descriptions out of visible actor names, preserve source acronym-number tokens generically during title normalization, and extract the real state object from durable-object confirmed-intent prose before writing Radar, Registry, Atlas, or Project-tab records.

- Follow-Up Evidence (2026-06-09 / generic post-confirm artifact quality): A rebuilt v0.1.15 local release installed from `/tmp/odylith-local-release-0.1.15` completed the same confirmed-create path in 13.96s with validation passed, dashboard refresh passed, 4 backlog records, 4 component records, and 6 diagram records. A generated-surface scan found zero hits for the prior hard-stop and comprehension regressions: title-case possessive-pronoun package-gate failure, broken optional-action fragments, actor/action fragments such as `Optionally log` or `Advances them`, acronym flattening, duplicated proof/result text, repeated `result result`, and component-local-domain-term gate failures.

- Follow-Up Root Cause (2026-06-09 / generic post-confirm artifact quality): The failure was not project-specific. Odylith lacked a shared, generic normalization spine across confirmed intent parsing, actor labels, first-path action semantics, sentence-label casing, Project-tab copy, component proof contracts, and the package-quality gate. Each layer had local heuristics that were individually plausible but collectively allowed drift between accepted intent, Radar, Registry, Atlas, Project Intelligence, dashboard bundles, and installed-package proof.

- Follow-Up Solution (2026-06-09 / generic post-confirm artifact quality): Add generic acronym-number restoration and sentence-label helpers, improve actor extraction for role descriptions and comma-gerund tails, carry pronoun subjects through first-path parsing, filter system-generated internal actions from user-facing capability prose, choose outcome verbs from the object type, enrich component-local contract terms from role semantics, dedupe adjacent repeated proof/output terms, and keep the package-quality gate strict on prose drift while allowing valid title-case labels.

- Follow-Up Evidence (2026-06-09 / rich GLP-1 artifact audit): A deep audit of `/Users/freedom/mock/GLP1` and a source-local replay of the same confirmed intent exposed remaining project-independent quality failures after earlier fixes: optional/later caregiver rows could still become first-release customer/problem/owner context, long internal-system purpose clauses such as `that knows dose steps and timing` and `with trend views over time` became Registry component identity, Radar enrichment repeated full workstream titles across proof/gate/owner/risk/control bullets, and the package gate could pass labels that were structurally valid but semantically explanatory.

- Follow-Up Root Cause (2026-06-09 / rich GLP-1 artifact audit): Actor completion rewrote optional/later actor rows into generic active actor descriptions and erased the deferral marker before posture, backlog, and domain-intelligence completion ran. Confirmed-create then joined every actor row as first-release scope. Internal-system parsing treated relative and descriptor clauses as identity when the noun head was a model/tracker-style capability. Radar enrichment used the full workstream title as a scoping prefix inside sections that already had title context. Package quality only rejected repeated full sentences and missed overlong explanatory component labels.

- Follow-Up Solution (2026-06-09 / rich GLP-1 artifact audit): Preserve deferred actor scope during actor completion, filter first-release actor rows generically in confirmed-intent posture and backlog generation, keep deferred actors visible only as deferred accepted context, split relative/descriptor system clauses into identity plus description, trim explanatory component-name tails, add a post-confirm package gate for overlong explanatory component labels, render Radar enrichment with section-local labels, and make repeated boilerplate component/slice-specific instead of full-title-specific.

- Follow-Up Evidence (2026-06-30 / Tribunal role fallback and component-label regression): The source-local high-variance matrix passed six fresh domains at hard 10/10, but the broader greenfield integration pack still exposed three quality regressions. Pattern-tracker and medication-tracking fixtures wrote governed records successfully, yet Tribunal visible actor projection collapsed generated judgment roles back onto the primary beneficiary when no explicit operator or risk owner was present. The medication fixture also rendered component labels as `Medication and Titration-schedule Model Service` and `Weight and Side-effect Tracking Service` even though the shared confirmed-text label contract already expected natural title-case spacing. The quantum fixture showed the opposite kind of stale proof risk: the accepted intent named live telemetry as a day-one internal product system, but the test still capped components at four.

- Follow-Up Root Cause (2026-06-30 / Tribunal role fallback and component-label regression): `artifact_tribunal_actors.py` treated absence of a distinct operator or risk owner as permission to reuse the first-path beneficiary, so generated `domain_operator` and `risk_owner` labels could pass shallow validation while losing role clarity. It also did not treat typed `graph.operators` rows as semantic operator evidence unless the label itself contained operator vocabulary. Separately, `greenfield_confirmed_components.py` kept a local `_title_phrase` title-caser that did not share the newer human-label hyphen splitter, so noun phrases with hyphenated source tokens could drift away from the shared label contract.

- Follow-Up Solution (2026-06-30 / Tribunal role fallback and component-label regression): Tribunal actor projection now preserves explicit operator rows as semantic evidence, prefers role-labeled actor candidates before action-like operator rows, and derives missing generated operator/risk roles from an appropriate product or explicit-reviewer lens instead of silently reusing the beneficiary. Component label construction now delegates to the shared `title_label` helper so noun-phrase labels such as titration schedule and side effect tracking use the same generic casing path as the rest of confirmed greenfield copy. The quantum regression expectation was corrected to require the fifth day-one telemetry component named by the accepted intent.

- Rollback/Forward Fix: Forward fix in Domain Intelligence and Radar authoring; existing generated consumer repos should be regenerated or repaired from their accepted project source.

- Verification: pytest tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_project_intelligence.py -q. Follow-up proof: `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_confirmed_backlog_terms.py tests/unit/runtime/test_greenfield_artifact_language_quality.py tests/unit/runtime/test_greenfield_prewrite_transaction.py tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py` passed (`72 passed`); `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/integration/runtime/test_greenfield_create_performance.py` passed (`7 passed`). A fresh Dignity-shaped confirmed-create replay completed in 12.296s and produced zero hits for `visible outcome from`, `uses the product to`, `understand The`, `Start with this implementation slice`, `representative user can`, `Let Child Learner Create An Account`, `shows open`, `Grown Up Recap`, and the old `Scenario Library and Authoring and Curation` label. Installed-post-confirm follow-up proof: targeted actor, confirmed-text, prewrite-transaction, and GLP-shaped performance regressions passed (`7 passed in 17.96s`); full greenfield performance integration passed (`8 passed in 125.53s`); focused actor/confirmed-text/prewrite suites passed (`55 passed in 158.04s`); exact source replay against the failing installed transcript completed successfully in 15.49s with validation passed, 4 backlog records, 4 component records, 6 diagram records, `Person on the GLP-1 Medication`, and `Single User's Medication Journey`. Final generic artifact-quality proof: full greenfield performance integration passed (`8 passed in 100.86s`), Project Intelligence tests passed (`32 passed in 0.67s`), focused parser/gate/component quality regressions passed (`14 passed in 5.58s`), touched source files compiled, `git diff --check` passed, local release assets rebuilt, installed local release replay completed in 13.96s with validation and dashboard passed, and a generated-surface scan found zero hits for the prior slop and hard-stop signatures. Rich GLP-1 artifact-audit proof: `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_shapes_radar_specs_with_domain_intelligence_substrate tests/unit/runtime/test_greenfield_confirmed_surfaces.py tests/unit/runtime/test_greenfield_general_artifact_quality.py::test_rendered_package_quality_flags_explanatory_component_labels` passed (`11 passed in 7.03s`); `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/integration/runtime/test_greenfield_create_performance.py::test_glp1_greenfield_create_completes_without_actor_or_state_label_drift_under_thirty_seconds` passed (`1 passed in 10.45s`); the full greenfield create performance suite passed (`8 passed in 100.58s`); touched domain-intelligence and artifact-quality modules compiled; source-local replay of `/Users/freedom/mock/GLP1/.odylith/runtime/greenfield/confirmed-intent.md` completed in 11.03s with validation/dashboard passed, 4 backlog records, 4 component records, 6 diagram records, no banned actor/component/proof-signature hits, compact component labels, and deferred caregiver context preserved only as deferred. Tribunal fallback follow-up proof: focused actor/component-label pack passed (`5 passed in 0.85s`), targeted pattern/GLP/quantum integration passed (`3 passed in 73.76s`), and the broader greenfield integration pair passed (`14 passed in 396.21s`). Post-fix source-local matrix proof passed 6 fresh high-variance domains at hard 10/10 with zero issues, browser proof attempted, 22.204-24.633s create times, governed readback present, and clean temp cleanup; proof JSON: `/tmp/odylith-source-local-proof-20260630-211726.json`. Fresh installed-release matrix proof is still required before release packaging.

- Prevention: Regression tests assert compact domain artifact IDs, no raw prompt slug in project payload, no generic queued-workstream rationale in greenfield Radar output, and Project tab projection from accepted-project and Tribunal state.

- Agent Guardrails: Before declaring a greenfield fix, inspect Radar child rows, Registry component IDs/specs, Atlas diagram IDs, accepted-project topology, and the Project tab story for product-owner readability.

- Preflight Checks: Run a product-manager comprehension audit on at least one greenfield fixture before local release packaging.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_feeds_project_tab_from_accepted_project_and_tribunal; tests/unit/runtime/test_project_intelligence.py::test_greenfield_workstream_body_does_not_repeat_full_project_title; tests/unit/runtime/test_greenfield_actor_labels.py::test_actor_label_keeps_comma_gerund_descriptions_out_of_visible_actor_names; tests/unit/runtime/test_greenfield_prewrite_transaction.py::test_greenfield_package_gate_allows_title_case_possessive_pronouns; tests/unit/runtime/test_greenfield_prewrite_transaction.py::test_greenfield_package_gate_still_rejects_prose_capitalization_drift; tests/integration/runtime/test_greenfield_create_performance.py::test_glp1_greenfield_create_completes_without_actor_or_state_label_drift_under_thirty_seconds; tests/unit/runtime/test_greenfield_confirmed_surfaces.py::test_long_system_descriptors_do_not_become_component_identity; tests/unit/runtime/test_greenfield_general_artifact_quality.py::test_rendered_package_quality_flags_explanatory_component_labels; tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_shapes_radar_specs_with_domain_intelligence_substrate

- Code References: - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- src/odylith/runtime/domain_intelligence/greenfield_workstream_rows.py
- src/odylith/runtime/governance/backlog_authoring.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_actor_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_backlog.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_components.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_rows.py
- src/odylith/runtime/domain_intelligence/artifact_enrichment.py
- src/odylith/runtime/domain_intelligence/greenfield_traceability.py
- src/odylith/runtime/artifact_quality/greenfield_package_quality.py
