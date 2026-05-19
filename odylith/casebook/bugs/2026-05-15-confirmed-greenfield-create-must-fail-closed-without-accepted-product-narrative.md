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

- Fresh Failure Signature: Confirmed create rejected a Product Intent Confirmation with `missing or too thin: internal_systems` even after the accepted narrative named concrete project systems. A race gearbox reliability confirmation that listed `telemetry ingestion pipeline`, `gearbox health model`, `degradation alert ledger`, `maintenance decision workspace`, and `run evidence review surface` reproduced the blocker.
- Trigger Path: The host writes the accepted confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, then runs `odylith greenfield create --repo-root . --prompt "<request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`; `greenfield_confirmed_intent` expands the prose systems but the generic-system detector marks the domain-specific `Run Evidence Review Surface` as fallback scaffold because it contains the words `evidence review`.
- Additional Root Cause: The first guardrail fixed prompt-only writes by making create fail closed, but the internal-systems quality check was over-broad. It treated one generic phrase match as enough to reject the whole accepted product narrative instead of rejecting only the exact generic fallback trio.
- Additional Invariant Violated: The confirmed-create gate must reject missing or generic fallback scaffolds, but it must not reject a domain-specific internal system merely because the system owns evidence review. Evidence review is often a legitimate domain responsibility in reliability, compliance, safety, research, and review workflows.
- Required Guardrail: Preserve the fail-closed prompt-only path while narrowing generic scaffold detection to exact fallback names such as `Workflow Service`, `State Store`, and `Evidence Review` appearing together. Add a regression test that builds the race gearbox proposal through the confirmed intent parser and greenfield Tribunal, and keep a paired rejection test for the exact generic fallback trio.
- Verification Added: `tests/unit/runtime/test_greenfield_proposals.py::test_confirmed_intent_parser_accepts_domain_specific_evidence_review_surface`, `tests/unit/runtime/test_greenfield_proposals.py::test_confirmed_intent_parser_still_rejects_exact_generic_system_scaffold`, and `tests/unit/test_cli.py::test_greenfield_propose_confirm_intent_json_is_provider_free` passed together (`3 passed`).
- Agent Guardrails: On confirm, do not ask the operator for a second product sentence when the accepted confirmation already carries story, actors, systems, assumptions, risks, and proof boundary. Diagnose the create gate first, preserve the human-visible confirmation as the source of truth, and make the product runtime accept concrete domain systems or return a precise maintainer-grade parser defect.
