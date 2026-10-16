- Bug ID: CB-205

- Status: FixedPendingRelease

- Created: 2026-06-09

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Greenfield post-confirm create blocked by generated sentence fragments and question-impact repetition

- Impact: Confirmed greenfield create could leave a fresh consumer repo with no governed project records after the operator confirmed a valid product intent.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo and installed local release v0.1.15 greenfield create path

- Detected By: User transcript from fresh signal-processing consumer repo plus source-local repro

- Failure Signature: greenfield create failed with semantic slop at proposal.backlog.0.product_view; follow-up package gate exposed Question Question and repeated noncanonical question-impact text

- Trigger Path: odylith greenfield create --repo-root . --prompt <confirmed request> --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1 --json

- Ownership: Odylith greenfield domain-intelligence grammar, post-confirm completion, traceability rendering, and rendered-package quality gates

- Timeline: Captured 2026-06-09 through `odylith bug capture`.

- Blast Radius: Fresh greenfield consumer repos across arbitrary domains whose accepted first path has coordinated actions, system-emitted result events, or accepted ambiguity rows with impacts

- SLO/SLA Impact: Violates the post-confirm completion target because Confirm can fail before Radar, Registry, Atlas, Compass, and tooling shell are written

- Data Risk: No user data loss; governance writes fail closed before durable records, but accepted intent remains stranded and operator trust is degraded

- Security/Compliance: No direct security exposure; release-readiness and compliance posture are blocked because governed records are not created

- Invariant Violated: After a valid Product Intent Confirmation, post-confirm must either create the complete governed project under the time budget or expose a platform defect with no project-specific workaround

- Root Cause: Generic grammar owners did not cover coordinated finite verbs such as pushes after modal can, visible-result extraction over-trimmed emitted result events, and question-impact renderers concatenated Impact after accepted ambiguity text without punctuation while the package gate treated repeated accepted questions as noncanonical prose.

- Solution: Extend shared prose grammar and first-path fragment extraction for push, emit, transform, monitor, pipeline/system action verbs, render product_view through outcome_action_phrase instead of understand <outcome>, make completion repair detect understand <Capitalized sentence> fragments, preserve emitted result-event objects, canonicalize question-impact punctuation, and allow source-backed open-question repetition in the package gate without allowing unrelated repeated prose.

- Verification: Focused signal-processing confirmed-create regression passed in 13.61s; full greenfield create performance suite passed with 11 tests in 157.65s; post-confirm slop suite passed with 24 tests; prior GLP, quantum, and whole-project regressions passed.

- Prevention: Keep coordinated-action grammar, visible-result object extraction, question-impact rendering, and package-repetition allowlists covered by focused unit tests plus full post-confirm performance regressions.

- Agent Guardrails: Do not reword consumer project intent to dodge post-confirm failures; reproduce against Odylith source and fix the generic platform grammar or renderer.

- Preflight Checks: Run the signal-processing confirmed-create regression, prior GLP and quantum confirmed-create regressions, post-confirm slop suite, and package repetition gate test before release.

- Regression Tests Added: tests/unit/runtime/test_greenfield_preconfirm_slop_regressions.py::test_signal_pipeline_first_path_phrases_do_not_leak_modal_or_understand_fragments; tests/integration/runtime/test_greenfield_create_performance.py::test_greenfield_create_completes_signal_processing_pipeline_without_sentence_fragment_slop_under_sixty_seconds

- Version/Build: v0.1.15 local release candidate

- Config/Flags: ODYLITH_RELEASE_BASE_URL=http://127.0.0.1:8123; ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST=1; ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY=1

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/common/prose_grammar.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_fragments.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_text_model.py
- src/odylith/runtime/domain_intelligence/greenfield_traceability.py
- src/odylith/runtime/artifact_quality/greenfield_package_quality.py
