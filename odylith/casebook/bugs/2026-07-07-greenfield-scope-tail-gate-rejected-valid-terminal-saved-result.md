- Bug ID: CB-220

- Status: Open

- Created: 2026-07-07

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Greenfield scope-tail gate rejected valid terminal saved result

- Impact: A user could confirm Product Intent and still see post-confirm create fail before governed records were written even though typed first-path events and the visible result were present.

- Components Affected: domain-intelligence

- Environment(s): Maintainer source-local v0.1.15 and local-release installed matrix, July 2026.

- Detected By: Installed greenfield post-confirm release matrix high-variance case after CB-219.

- Failure Signature: greenfield post-confirm completion failed: greenfield scope boundary truncates the accepted first-path tail; hard_blocker owner typed_package_artifact_gate; write transaction not committed.

- Trigger Path: greenfield propose for a high-variance product intent, save Product Intent Confirmation, then greenfield create --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1

- Ownership: Domain Intelligence first-path projection, project-brief release-scope rendering, and typed package artifact gate.

- Timeline: 2026-07-06 local-release matrix failed a high-variance case; 2026-07-07 source-local propose/create reproduced the no-write package failure; diagnosis showed semantic events preserved five steps and visible_result saved reproducible run record while project-brief cleanup and scope-tail inflection comparison rejected valid output. A later installed 120-case discovery run against `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-fd0e5a51` reopened the family on case 2, `cryogenic ion trap calibration intake-to-proof workspace`, with the same typed-package artifact gate after the release-scope fragment dropped accepted source actions: `validate units and provenance`, `run the model`, `record uncertainty`, and `save a reviewable result`.

- Blast Radius: Any confirmed greenfield intent whose terminal action uses an inflected visible result such as saved versus save, or whose terminal action can be clipped as a noun-like record tail.

- SLO/SLA Impact: Post-confirm success invariant violated and installed matrix release proof failed; latency proof also stayed unproven for the failed package.

- Data Risk: No private data exposure observed; risk is misleading or missing governed project truth and rollback before records are written.

- Security/Compliance: No direct security exposure; regulated or scientific proposals could lose required proof-tail language before release records exist.

- Invariant Violated: After confirmation, valid typed first-path tail events and the visible result must survive release-scope projection and package quality gates without user-facing failure.

- Root Cause: The first fix closed the saved/silent-e and clipped-record class but was incomplete. Release-scope projection still reused the general readable action chain that intentionally skipped steps classified as system-generated. In scientific and modeling workflows, accepted human first-path actions such as validate, run, record, and save can be classified as system-side for ordinary UI copy, but they remain product truth for release-boundary scope. The gate correctly rejected the resulting truncated scope.

- Solution: Keep complete terminal action clauses during project-brief polishing; add past-tense silent-e variants to scope-tail coverage; move comma/then action splitting into the dedicated action-split owner; preserve actor carry through same-sentence then continuations and explicit pronoun carry; preserve actor-owned visible-result event copy without rewriting it into a different capability; clean Atlas evidence-record descriptions. The reopened fix keeps the ordinary confirmation/action compactors unchanged but lets the release-scope boundary explicitly include accepted system-classified source steps and preserve their source actions before the typed package gate evaluates tail coverage.

- Rollback/Forward Fix: Forward fix only; weakening the tail gate or deleting the release-scope check would hide real projection loss.

- Verification: Focused regressions passed; broader parser/projection/artifact-quality slice passed 213 tests in 408.27s after the action-split and actor-owned copy cleanup; exact source-local high-variance replay committed governed records with post_confirm_quality_manifest status passed, validation_status passed, issue_count 0, write_transaction committed, rollback guard enabled, 4 Radar workstreams, 3 Registry components, 6 Atlas diagrams, and zero known bad signature hits. Fresh reopening evidence: installed 120-case discovery stopped at 1/120 because fd0e5a51 case 2 failed before writes with `greenfield scope boundary truncates the accepted first-path tail`; result evidence lives under `/Volumes/FREEDOM_RESEARCH/research-code/odylith-fd0e5a51-volume-120-20260707T000000Z/`. Source-local exact replay after the reopened fix passed with post_confirm_quality_manifest status passed, validation_status passed, issue_count 0, write_transaction committed, elapsed 7.561s, 4 Radar workstreams, 3 Registry components, and 6 Atlas diagrams. Fresh local-release dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-c40223a0` passed platform-domain leakage across 224 fixture terms, and the exact installed failed-subset replay passed 1/1 at hard 10/10 with 32.441s create time, zero issues, 4 Radar workstreams, 3 Registry specs, 6 Atlas diagrams, 18 trace nodes, and all expert lenses green. Remaining proof: resume broader 120/240-case discovery and document/PRD/edited-Markdown tiers before release readiness.

- Prevention: Scope-tail gates must compare typed event and visible-result variants without domain vocabulary, and project brief cleanup must only drop genuinely clipped terminal clauses.

- Agent Guardrails: Do not fix by weakening scope-tail validation, hardcoding scientific terms, or patching generated projects. Preserve typed custody and prove with real post-confirm create.

- Preflight Checks: Search CB-219, high-variance first-path tail records, and greenfield scope-boundary tests before changing parser, project brief, or package gates.

- Regression Tests Added: tests/unit/runtime/test_greenfield_project_judgment_quality.py::test_project_judgment_accepts_past_tense_visible_result_in_scope_tail; tests/unit/runtime/test_greenfield_project_judgment_quality.py::test_scope_fragment_preserves_scientific_tail_actions_marked_system_side; tests/unit/runtime/test_greenfield_confirmed_backlog_terms.py::test_workstream_scope_boundary_preserves_scientific_tail_actions_marked_system_side; tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py::test_confirmed_project_brief_keeps_terminal_save_record_tail; tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py::test_first_path_clause_rendering_stays_in_dedicated_owner plus existing parser/title/proof-label, backlog actor-owned outcome, and protected-token casing regressions.

- Monitoring Updates: Release matrices should retain prompt-only scientific cases whose visible result is a saved or exported record, scientific first paths where accepted source actions are classified as system-side for ordinary copy, and scans for adjacent record-record style copy.

- Version/Build: v0.1.15 development branch 2026/freedom/v0.1.15

- Config/Flags: Provider-free source-local create and local-release installed matrix; release 0.0.1.

- Customer Comms: Internal platform stability work; no public response until release proof passes.

- Related Incidents/Bugs: CB-219, CB-215, B-142

- GitHub Status: installed_failed_subset_passed_pending_broad_release_proof

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_project_brief.py
- src/odylith/runtime/artifact_quality/greenfield_project_judgment.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py
- src/odylith/runtime/surfaces/atlas_box_explanations.py
