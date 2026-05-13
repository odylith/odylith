- Bug ID: CB-128

- Type: Product








- Status: Closed

- Created: 2026-04-27

- Severity: P2

- Reproducibility: High


- Description: An empty or migrated consumer repo with only Odylith-managed files under root-level odylith/ can receive a fake show report: managed compass runtime JavaScript is counted as application source, then Registry/Radar/Atlas candidates such as Core Engine, documentation, CI/CD, and a boundary map are suggested even though no app source exists.

- Impact: Operators see fake governance candidates on empty consumer repos, eroding trust in the first-run show report and making migrated consumer lanes look noisy instead of grounded.

- Components Affected: odylith

- Environment(s): Consumer repo with Odylith installed or migrated; reproduced with an empty consumer fixture containing only odylith/compass/runtime files and empty governance directories.

- Detected By: Operator feedback on odylith show output

- Failure Signature: Output says Odylith read 24 modules or reports a Core Engine Registry component from odylith/compass/runtime, plus generic docs/CI workstreams, in a repo with no application source.

- Trigger Path: odylith show --repo-root <empty-or-migrated-consumer-repo>

- Ownership: product

- Timeline: Captured 2026-04-27 through `odylith bug capture`.

- Blast Radius: First-run and migrated consumer-lane show UX; Registry, Radar, and Atlas suggestion trust.

- SLO/SLA Impact: Medium operator-confidence and triage-latency impact on a common entrypoint.

- Data Risk: Low

- Security/Compliance: No direct security impact.

- Invariant Violated: The advisory show report must only propose governance records from application source, never from Odylith managed install or governance assets.

- Root Cause: The show import scanner, incremental cache, Python root detector, fallback discovery, and candidate formatter did not share a source-inventory policy. Root-level Odylith managed assets, tests/support files, infra-only files, root tmp clone trees, and thin 1-2 file app slices could be treated as stable governance evidence, while fallback docs/CI workstreams could fire after weak or false component evidence appeared.

- Solution: Added trust-first source classification for app, test/support, infra, generated/vendor, root temp clone, docs, metadata, and Odylith-managed assets; wired import scanning, incremental cache materialization, Python root detection, fallback discovery, component discovery, TODO issue detection, and show formatting through that inventory; gated Registry/Radar/Atlas candidates unless at least three app modules and a non-wrapper boundary survive; added scenario-aware empty, metadata-only, docs-only, managed-only, tests-only, infra-only, thin-app, app-ready, and already-governed output; added a short first-run mental-model line explaining Registry/Radar/Atlas/Casebook and why weak evidence stays quiet; kept JSON backward compatible with additive scenario/source/teaching/next-prompt fields; and updated show-me skill source plus installed/bundled mirrors to print scenario-aware stdout verbatim.

- Verification: pytest tests/unit/runtime/test_show_capabilities.py tests/unit/runtime/test_incremental_import_graph.py; pytest tests/integration/install/test_manager.py tests/integration/install/test_bundle.py; pytest tests/unit/install/test_codex_project_assets.py tests/unit/install/test_claude_effective_settings.py; pytest tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py; python -m py_compile on touched runtime/install/test files; git diff --check; odylith casebook validate.

- Prevention: Keep show source discovery behind one shared source-inventory policy, fail closed on weak candidate evidence, and pin exact trust-first text for empty, metadata-only, docs-only, managed-only, tests-only, infra-only, thin-app, app-ready, monorepo, existing-governance, root-temp, generated/vendor, and real top-level odylith-package regressions.

- Regression Tests Added: tests/unit/runtime/test_show_capabilities.py covers source classification, managed root odylith skip, root tmp skip with nested tmp retained, empty/docs/metadata/tests/infra/thin-app scenarios, managed-only repos, flat src label safety, generic src/app label safety, monorepo workspace boundaries, app-plus-managed repos, existing-governance suppression, Casebook TODO source gating, additive JSON teaching and next-prompt fields, show-me mirror guidance, real root odylith packages without managed markers, and component-discovery refusal to promote tests.

- Code References: - src/odylith/runtime/analysis_engine/repo_analysis.py
- src/odylith/runtime/analysis_engine/import_graph.py
- src/odylith/runtime/analysis_engine/incremental_import_graph.py
- src/odylith/runtime/analysis_engine/component_discovery.py
- src/odylith/runtime/analysis_engine/show_capabilities.py
- tests/unit/runtime/test_show_capabilities.py
