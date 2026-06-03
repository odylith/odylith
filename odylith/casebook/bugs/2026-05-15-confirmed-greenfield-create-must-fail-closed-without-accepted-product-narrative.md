- Bug ID: CB-202

- Status: Open

- Created: 2026-05-15

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: Confirmed greenfield creation can currently proceed from a thin prompt after Product Intent Confirmation, causing generated Radar, Registry, Atlas, and dashboard records to collapse into generic workflow/state/evidence language instead of preserving the accepted product story, actors, state object, first path, systems, non-goals, and proof boundary.

- Impact: Consumer greenfield projects can receive shallow, generic governance artifacts even after the host wrote a rich Product Intent Confirmation, breaking product understanding before implementation starts.

- Components Affected: greenfield-governance

- Environment(s): Consumer lane pinned release and source-local maintainer validation for v0.1.15 greenfield create path.

- Detected By: Operator review of fresh greenfield generated dashboard and governance records.

- Failure Signature: Generated product story and governance records use generic first workflow/state/evidence scaffold terms instead of the accepted product narrative.

- Trigger Path: Run greenfield propose for a thin or broad new-project prompt, host writes Product Intent Confirmation in chat, then run greenfield create --confirm without passing the confirmed narrative as an input artifact.

- Ownership: Greenfield confirmed-create contract, proposal builder, installed host guidance, and release smoke.

- Timeline: Captured 2026-05-15 through `odylith bug capture`.

- Blast Radius: Any consumer greenfield project, any host model, any domain, and any complexity where the confirmed narrative is not carried into create.

- SLO/SLA Impact: Blocks trustworthy greenfield release proof; confirmed create cannot be considered safe until fail-closed narrative preservation is enforced.

- Data Risk: No application data loss, but generated governance truth can be misleading and can steer implementation from false project understanding.

- Security/Compliance: Domain-specific security, privacy, safety, compliance, and abuse posture can be erased by generic fallback governance language.

- Invariant Violated: Confirmed consumer-lane governance must start from human-readable product understanding and must not write records from a thin prompt after confirmation.

- Root Cause: The confirmed create shortcut moved schema ownership into Odylith but did not require the host-written Product Intent Confirmation as input, so the builder reconstructed records from the prompt title and deterministic generic fallback systems.

- Solution: Require a confirmed-intent artifact for confirmed create/propose-confirmed paths, fail closed when it is missing or shallow, derive components/workstreams/diagrams/project intelligence from that accepted narrative, and make release smoke exercise the same path.

- Rollback/Forward Fix: Forward fix only; prompt-only confirmed create must be rejected rather than tolerated as a compatibility path.

- Verification: Focused CLI tests must show prompt-only create fails, intent-file create preserves domain actors/systems/first path/proof boundary, installed guidance teaches the intent-file path, and release smoke rejects host-side schema repair or generic fallback.

- Prevention: Treat live product narration as a required write input, not chat-only context; add release smoke and quality gates that fail on generic workflow/state/evidence fallback when confirmed domain systems are available.

- Agent Guardrails: Do not hand-author or repair proposal JSON; do not write consumer governance records from a thin prompt; do not leak Odylith artifacts into consumer product story before product meaning is clear.

- Preflight Checks: Before greenfield create writes records, check for product story, state object, first path, human actors, internal systems, and proof boundary from the accepted confirmation.

- Version/Build: v0.1.15

- Config/Flags: consumer lane pinned release; no provider calls required

- Related Incidents/Bugs: CB-173

- GitHub Status: needs_info

- Public Response: pending

## 2026-05-19 Recurrence: Confirmation Format Was Underspecified

- Fresh Failure Signature: The no-write Product Intent Confirmation could be rendered as one large paragraph instead of scannable sections, and normal domain words could surface with decorative Markdown such as code ticks or bold markers. The accepted narrative still contained useful product reasoning, but the transcript lost the operator-facing structure needed for quick review before confirmation.
- Generic Trigger Path: A host follows `greenfield propose`, writes a Product Intent Confirmation in chat, and then asks the operator to confirm. Because the guidance and CLI reasoning payload did not explicitly require sectioned Markdown, the visible confirmation can collapse into prose even when the underlying content is domain-specific.
- Additional Invariant Violated: Before any create/apply write, the visible confirmation must be clear enough for a human operator to verify product story, state object, first path, actors, systems, assumptions, ambiguities, and proof boundary without reconstructing the structure from a paragraph.
- Required Guardrail: The CLI reasoning payload, installed guidance, bundled skills, and release smoke must require a sectioned Product Intent Confirmation: title, Product story, State object, First complete path, Human actors, External systems, Internal product systems, Critical assumptions, Ambiguities, Proof boundary, and Confirm/Edit/Reject. Story/path/proof stay short paragraphs; actors, systems, assumptions, and ambiguities stay bullets; ordinary domain nouns must not be wrapped in code ticks or decorative bold markers.

## 2026-05-19 Recurrence: Fail-Closed Internal Systems Gate Rejected Domain-Specific Evidence Review

- Fresh Failure Signature: Confirmed create rejected a Product Intent Confirmation with `missing or too thin: internal_systems` even after the accepted narrative named concrete product systems. A domain-specific confirmation that included an evidence-review surface reproduced the blocker.
- Trigger Path: The host writes the accepted confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, then runs `odylith greenfield create --repo-root . --prompt "<request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`; `greenfield_confirmed_intent` expands the prose systems but the generic-system detector can mark a domain-specific evidence-review owner as fallback scaffold merely because it contains the words `evidence review`.
- Additional Root Cause: The first guardrail fixed prompt-only writes by making create fail closed, but the internal-systems quality check was over-broad. It treated one generic phrase match as enough to reject the whole accepted product narrative instead of rejecting only the exact generic fallback trio.
- Additional Invariant Violated: The confirmed-create gate must reject missing or generic fallback scaffolds, but it must not reject a domain-specific internal system merely because the system owns evidence review. Evidence review is often a legitimate domain responsibility in reliability, compliance, safety, research, and review workflows.
- Required Guardrail: Preserve the fail-closed prompt-only path while narrowing generic scaffold detection to exact fallback names such as `Workflow Service`, `State Store`, and `Evidence Review` appearing together. Add regression tests that build a domain-specific evidence-review proposal through the confirmed intent parser and greenfield Tribunal, and keep a paired rejection test for the exact generic fallback trio.
- Verification Added: `tests/unit/runtime/test_greenfield_proposals.py::test_confirmed_intent_parser_accepts_domain_specific_evidence_review_surface`, `tests/unit/runtime/test_greenfield_proposals.py::test_confirmed_intent_parser_still_rejects_exact_generic_system_scaffold`, and `tests/unit/test_cli.py::test_greenfield_propose_confirm_intent_json_is_provider_free` passed together (`3 passed`).
- Agent Guardrails: On confirm, do not ask the operator for a second product sentence when the accepted confirmation already carries story, actors, systems, assumptions, risks, and proof boundary. Diagnose the create gate first, preserve the human-visible confirmation as the source of truth, and make the product runtime accept concrete domain systems or return a precise maintainer-grade parser defect.

## 2026-05-20 Recurrence: Confirmed Create Underfilled Governed Artifact Fields

- Fresh Failure Signature: Confirmed create could parse a rich accepted intent and still fail before durable records because generated Registry components did not carry concrete `risks`. After the risk gap was filled, the same path exposed an Atlas refresh failure where newly scaffolded diagrams watched the whole Atlas source tree and therefore marked themselves stale after their own catalog/assets were rendered.
- Generic Trigger Path: In a consumer repo, write the accepted Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, then run `odylith greenfield create --repo-root . --prompt "<request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1 --json`.
- Additional Root Cause: The confirmed-create builder relied on downstream component authoring to synthesize risk posture from component text, but the component rows themselves did not carry domain/security/policy risk fields for the governed artifact Tribunal. The diagram completion fallback also used `odylith/atlas/source` as a watch path, which self-invalidated Atlas freshness when the catalog, SVG, and PNG outputs changed.
- Additional Invariant Violated: Confirmation means Odylith owns the complete governed project artifact set. If a field required by Radar, Registry, Atlas, release planning, Compass memory, or dashboard refresh is derivable from the accepted intent, the generator must fill it and rerun gates before writing instead of returning a host-facing blocker.
- Required Guardrail: Keep a confirmed-completion pass between proposal normalization and writes. It must derive missing problem/customer/opportunity/product view, success metrics, backlog risk/security posture, component interfaces/dependencies/validation/risks, diagram watch paths, and project-level security/compliance posture from the accepted intent; run the greenfield Tribunal and governed artifact Tribunals; retry deterministic omissions for a bounded number of passes; and fail only on non-derivable contradictions. Generated Atlas watch paths must not include the generated Atlas source tree itself.
- Verification Added: `tests/unit/runtime/test_greenfield_confirmed_intent.py::test_confirmed_proposal_completion_adds_component_risks_and_fresh_diagram_watch_paths` checks component risk completion, governed component Tribunal pass/fail evidence, and non-self-invalidating diagram watch paths. `tests/unit/runtime/test_greenfield_cli_paths.py::test_greenfield_create_cli_applies_confirmed_prompt` now checks written component specs include domain/security/policy risk posture and created Atlas catalog rows do not watch `odylith/atlas/source`.
- External Repro Proof: A high-risk consumer-repo confirmed-create repro now writes the full governed project set end to end: Radar workstreams, Registry components/specs, Atlas Mermaid/SVG/PNG assets, release assignment, accepted-project memory, and refreshed Radar/Registry/Atlas/Compass/tooling-shell surfaces all pass. No external product-specific labels are copied into Odylith governance truth.
- Agent Guardrails: Upon confirmation, do not ask the operator to supply risk, internal systems, or proof text that is already present or inferable from the accepted intent. Fill the governed fields, run the Tribunals, repair deterministic gaps, and only surface a blocker when the accepted intent truly contradicts itself or omits a non-derivable product decision.

## 2026-05-20 Recurrence: Confirmed Create Stopped On Enrichable Thin Actor And System Rows

- Fresh Failure Signature: Confirmed create could reject an accepted Product Intent Confirmation with `missing or too thin: human_actors` or `missing or too thin: internal_systems` even when the surrounding product story, state object, first path, and proof boundary contained enough domain information to enrich the thin rows safely.
- Generic Trigger Path: The host writes a clear Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, but the Human actors or Internal product systems sections use concise role or capability names. `odylith greenfield create --repo-root . --prompt "<request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1` stops before records instead of expanding those rows and rerunning the gates.
- Additional Root Cause: The confirmed-intent parser treated every thin list row as a terminal operator-facing blocker. It did not have a deterministic completion layer that could derive actor responsibility, access posture, product-system responsibility, success metrics, assumptions, ambiguities, and non-goals from the accepted story/path/state/proof context before validation.
- Additional Invariant Violated: After confirmation, Odylith owns completion of derivable governance fields. The host should not be asked for another sentence when the accepted intent already contains enough product evidence to generate clear, grammatical, domain-specific rows and send the result through Tribunal validation.
- Required Guardrail: Complete confirmed intent before validation unless the narrative is missing, meta-scaffolded, or contradictory. The completion layer must stay domain-agnostic, must not store consumer project facts in Odylith governance, must not overwrite already-detailed sections, and must still fail closed for prompt-only or generic scaffold input.
- Verification Added: `tests/unit/runtime/test_greenfield_confirmed_intent.py::test_confirmed_intent_completion_expands_thin_actors_and_systems_generically` proves thin actor/system rows are expanded into reviewable product-language rows. `tests/unit/runtime/test_greenfield_confirmed_intent.py::test_confirmed_greenfield_create_completes_thin_intent_before_governed_records` proves the confirmed CLI create path writes governed records instead of stopping on enrichable thin rows.
- Agent Guardrails: On confirm, do not stop at a deterministic parser gap that can be completed from the accepted intent. Fill derivable sections, rerun validation and Tribunal gates, and surface only non-derivable contradictions or truly missing product narrative.

## 2026-06-02 Recurrence: Semantic Renderers Preserved Parser Debris After Confirmation

- Fresh Failure Signature: Confirmed create could pass the accepted narrative into downstream renderers, then still publish role/action splices, bare outcome nouns, framework proof scaffolds, adjacent-boundary boilerplate, or component-contract fragments that were grammatical enough to pass shape checks but not clear enough for humans to use.
- Generic Trigger Path: A host writes a concrete Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, then runs `odylith greenfield create --repo-root . --prompt "<request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`. The semantic model forms, but first-path clauses, component contracts, workstream text, Atlas labels, and runtime JSON can inherit parser artifacts from intermediate fields.
- Additional Root Cause: The post-confirm path had already moved toward semantic-model-first generation, but several renderers still normalized phrases locally. That let syntactically valid fragments survive as product truth because quality gates checked structure and missing fields more reliably than human-readable semantics.
- Additional Invariant Violated: After confirmation, every generated sentence must trace to accepted intent, derived semantic model facts, or generic governance invariants while staying readable on its own. A valid artifact cannot contain parser debris, activity-shaped actor names, framework proof slogans, or component boundary boilerplate that would be equally plausible in unrelated products.
- Required Guardrail: Keep first-path clause extraction, visible-result detection, component contract differentiation, Atlas label generation, and public prose checks behind semantic quality gates. Repair from the semantic model before writes; fail closed if the repaired package still contains parser artifacts, role/action splices, bare outcome nouns, truncated labels, or generic proof scaffolds.
- Verification Added: `tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py` covers actor/action splice repair, visible-result clause separation, coordinated action-verb normalization, unheaded intent parsing, runtime JSON debris rejection, component-contract verb normalization, Atlas label hygiene, and public prose slop gates. Replayable proof commands: `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_general_artifact_quality.py tests/unit/runtime/test_greenfield_component_spec_quality.py tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py tests/unit/runtime/test_greenfield_component_semantic_contract_quality.py tests/unit/runtime/test_greenfield_confirmed_repair.py tests/unit/runtime/test_greenfield_artifact_language_quality.py` (`67 passed`); `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_cli_paths.py` (`17 passed`); `.venv/bin/python -m pytest -q tests/integration/runtime/test_greenfield_create_performance.py` (`1 passed`, under-30s confirmed-create gate with semantic slop check enabled); `.venv/bin/python -m pytest -q tests/integration/runtime/test_project_tab_browser.py` (`2 passed`). Additional temp-repo measurement: `.venv/bin/python /private/tmp/odylith_greenfield_e2e_measure.py --keep` completed in 11.67 seconds with six diagrams, no missing assets, and no slop hits.
- Agent Guardrails: Do not treat shape validation as quality proof. For post-confirm greenfield work, inspect generated Radar, Registry, Atlas, project dashboard, and runtime JSON for human clarity before claiming completion, and keep examples confined to tests rather than Odylith product governance truth.

## 2026-06-03 Follow-up: Confirmed Create Prewrite Gate Needed A Dedicated Owner

- Fresh Finding: The confirmed-create completion orchestrator had grown into a hot-path owner for orchestration, semantic model completion, proposal validation, component/spec preflight checks, greenfield Tribunal execution, and governed-artifact Tribunal issue collection. The behavior was correct, but the file crossed the source-size hard threshold and made future artifact-quality fixes riskier.
- Generic Trigger Path: Maintain `greenfield create --confirm` quality or speed gates after the semantic-render pass. A small prewrite quality change would touch the large completion orchestrator even when the real ownership is Tribunal/preflight aggregation.
- Additional Root Cause: Confirmed-create quality checks were factored by execution order rather than responsibility. The parent completion loop delegated actor repair and text cleanup, but still locally owned the prewrite gate that converts completed proposals into semantic and Tribunal-ready artifacts.
- Additional Invariant Violated: Confirmed-create hot-path code must keep ownership narrow enough that quality gates can improve without reintroducing oversized orchestrators. Source-size discipline is part of the anti-slop contract for this lane.
- Required Guardrail: Keep semantic model completion and all proposal/component/spec/Tribunal preflight issue aggregation in `greenfield_confirmed_prewrite_gate.py`. The parent completion orchestrator may call the gate, but it must not re-own `_artifact_issues`, `run_greenfield_tribunal`, or collector loops for governed-artifact Tribunal results.
- Verification Added: `tests/unit/runtime/test_greenfield_confirmed_repair.py::test_confirmed_completion_prewrite_gate_stays_in_dedicated_owner` pins the owner split, parent line-count ceiling, and Tribunal aggregation location. Replayable proof: `.venv/bin/python -m py_compile src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion.py src/odylith/runtime/domain_intelligence/greenfield_confirmed_prewrite_gate.py`; `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_confirmed_repair.py` (`3 passed`); broader greenfield artifact-quality bundle passed 94 tests before Chromium was blocked by sandbox permissions; escalated rerun of `.venv/bin/python -m pytest -q tests/integration/runtime/test_greenfield_create_performance.py` passed (`1 passed in 9.81s`).
- Agent Guardrails: For future confirmed-create artifact-quality work, add behavior in the narrow owner that owns the phase. Do not grow `greenfield_confirmed_completion.py` back into semantic, Tribunal, artifact Tribunal, actor completion, or text-helper ownership.

## 2026-06-03 Follow-up: Confirmed Intent Parser Needed A Dedicated System-Row Owner

- Fresh Finding: The confirmed-intent parser still locally owned JSON/Markdown role rows, internal-system labeled spans, sentence-system splitting, concise system expansion, contextual description repair, and generic scaffold detection. The behavior had accumulated around parser convenience instead of ownership, leaving the file above the source-size hard threshold.
- Generic Trigger Path: Maintain `greenfield create --confirm` input parsing after an operator writes Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`. A small internal-system row parsing change would touch the whole confirmed-intent entrypoint even when the real ownership is system-row normalization.
- Additional Root Cause: The parser had two responsibilities: section/preamble extraction and internal-system row normalization. Actor completion and prewrite gates had dedicated owners, but confirmed-intent system rows still lived inside the entrypoint.
- Additional Invariant Violated: Confirmed-create input parsing must keep syntax parsing, actor completion, system-row normalization, and prewrite quality gates in narrow owners so future artifact-quality fixes do not recreate an oversized parser.
- Required Guardrail: Keep role/system row normalization, labeled-span parsing, sentence-system splitting, system-name prefix detection, generated system-description repair, `confirmed_system_name`, `confirmed_system_description`, and generic scaffold detection in `greenfield_confirmed_system_rows.py`.
- Verification Added: `tests/unit/runtime/test_greenfield_confirmed_intent.py::test_confirmed_intent_system_rows_stay_in_dedicated_owner` pins the owner split and parent line-count ceiling. Replayable proof: `.venv/bin/python -m py_compile src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_rows.py`; `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_confirmed_intent.py` (`27 passed`); broader greenfield artifact-quality bundle passed (`95 passed in 205.10s`).
- Agent Guardrails: For future confirmed-intent work, route system row parsing and description repair through `greenfield_confirmed_system_rows.py`; do not put row splitting, system-name detection, or generic system scaffold checks back into `greenfield_confirmed_intent.py`.

## 2026-06-03 Follow-up: Post-Confirm Completion Needed A Dedicated Semantic Drift Owner

- Fresh Finding: The post-confirm completion gate still locally owned package orchestration, prewrite-preview fidelity, contrastive domain-drift tokenization, semantic repetition clustering, generated-artifact sentence extraction, and semantic overlap scoring. The behavior was correct but left the file above the source-size hard threshold after the semantic-render hardening pass.
- Generic Trigger Path: Maintain `greenfield create --confirm` post-confirm quality gates after semantic slop checks are enabled. A small change to generated-artifact drift detection would touch the whole package completion gate even when the real ownership is semantic drift scoring.
- Additional Root Cause: The post-confirm gate had split component/spec and first-path semantics into narrower owners, but semantic drift checks still lived at the bottom of the orchestration file because they were originally added as final package checks.
- Additional Invariant Violated: Confirmed-create artifact gates must keep orchestration separate from semantic scoring so future quality fixes do not recreate oversized hot-path modules.
- Required Guardrail: Keep contrastive domain-drift checks, semantic repetition checks, generated-artifact sentence/value extraction, intent/component signature building, and semantic overlap scoring in `greenfield_post_confirm_semantic_drift.py`. The package gate may call these checks, but it must not re-own `_term_signature`, generated-artifact sentence extraction, or local semantic-overlap tokenization.
- Verification Added: `tests/unit/runtime/test_greenfield_general_artifact_quality.py::test_greenfield_post_confirm_semantic_drift_stays_in_dedicated_owner` pins the owner split and parent line-count ceiling. Replayable proof: `.venv/bin/python -m py_compile src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py src/odylith/runtime/domain_intelligence/greenfield_post_confirm_semantic_drift.py tests/unit/runtime/test_greenfield_general_artifact_quality.py`; `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_general_artifact_quality.py` (`39 passed in 154.23s`); `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_prewrite_transaction.py` (`22 passed in 108.95s`); broader greenfield artifact-quality bundle passed (`118 passed in 311.35s`); escalated Chromium-capable performance proof passed (`1 passed in 14.83s`).
- Agent Guardrails: For future post-confirm package work, route semantic drift and repetition scoring through `greenfield_post_confirm_semantic_drift.py`; do not put token signature helpers, generated-artifact sentence clustering, or overlap scoring back into `greenfield_post_confirm_completion.py`.

## 2026-06-03 Follow-up: Post-Confirm Completion Needed A Dedicated Semantic Alignment Owner

- Fresh Finding: After semantic drift moved out, the package completion gate still locally owned semantic model shape checks, component/workstream/diagram alignment, rendered Registry spec alignment, component ID fallback, first-release scope checks, and its own row coercion helper. The parent was below the hard threshold but still above the soft source-size limit.
- Generic Trigger Path: Maintain `greenfield create --confirm` post-confirm quality gates when semantic model alignment changes. A small component, workstream, diagram, or rendered-spec alignment fix would still touch the package orchestrator even though the real ownership is semantic model comparison.
- Additional Root Cause: Semantic model alignment was added as a package-gate phase and never split after the confirmed-completion path grew into separate drift, prewrite, and semantic-render owners.
- Additional Invariant Violated: Confirmed-create package orchestration must not own semantic model comparison details or duplicate row coercion helpers after a shared post-confirm row owner exists.
- Required Guardrail: Keep semantic model shape checks, component/workstream/diagram alignment, rendered Registry spec alignment, component ID fallback, and first-release scope checks in `greenfield_post_confirm_semantic_alignment.py`. Keep generated-list row coercion in `greenfield_post_confirm_rows.py`; the parent and drift modules may import that helper but must not redefine `_mapping_rows`.
- Verification Added: `tests/unit/runtime/test_greenfield_general_artifact_quality.py::test_greenfield_post_confirm_semantic_drift_stays_in_dedicated_owner` now pins semantic drift, semantic alignment, and shared row ownership while requiring `greenfield_post_confirm_completion.py` to stay under 800 lines. Replayable proof: `.venv/bin/python -m py_compile src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py src/odylith/runtime/domain_intelligence/greenfield_post_confirm_semantic_drift.py src/odylith/runtime/domain_intelligence/greenfield_post_confirm_semantic_alignment.py src/odylith/runtime/domain_intelligence/greenfield_post_confirm_rows.py tests/unit/runtime/test_greenfield_general_artifact_quality.py`; `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_general_artifact_quality.py` (`39 passed in 170.88s`); broader greenfield artifact-quality bundle passed (`118 passed in 334.66s`); escalated Chromium-capable performance proof passed (`1 passed in 11.96s`).
- Agent Guardrails: For future post-confirm package work, route semantic model alignment and rendered-spec alignment through `greenfield_post_confirm_semantic_alignment.py`; do not put semantic shape comparison, component/workstream/diagram alignment, first-release scope checks, or row coercion clones back into `greenfield_post_confirm_completion.py`.
