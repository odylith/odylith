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
