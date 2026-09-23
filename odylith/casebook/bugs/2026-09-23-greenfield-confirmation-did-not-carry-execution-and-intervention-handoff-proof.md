- Bug ID: CB-343

- Status: Open

- Created: 2026-09-23

- Severity: P2

- Reproducibility: Consistent

- Type: OperatorUX

- Description: Before this checkpoint, Greenfield could compile and commit governed artifacts while the next-step package omitted a direct Execution Engine snapshot and post-confirm output did not guarantee one explicit chat-visible Assist fallback. Delivery Intelligence was refreshed indirectly but its staged artifact freshness was not asserted by the Greenfield proof.

- Impact: Operators could receive a successful Greenfield package without a trustworthy execution handoff or visible intervention cue, forcing downstream reinterpretation and weakening end-to-end confidence.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith product repository source-local v0.1.15 on the consolidated target branch

- Detected By: Independent Greenfield integration audit and focused staged-package tests

- Failure Signature: next_steps_preview had no execution_engine_handoff; completion output had no Odylith Assist fallback; staged surface proof did not validate delivery_intelligence.v4.json

- Trigger Path: odylith greenfield propose -> pre-confirm package -> greenfield create --confirm

- Ownership: Greenfield Domain Intelligence, Execution Engine handoff, Delivery Intelligence proof, and Intervention visibility

- Timeline: Captured 2026-09-23 through `odylith bug capture`.

- Blast Radius: All host-model Greenfield proposal and confirmation flows across Codex, Claude, and CLI surfaces

- SLO/SLA Impact: Adds a bounded pre-confirm validation step and keeps 90/120/150 timing guidance visible; no post-confirm model work

- Data Risk: No source-data loss; risk was incomplete provenance and operator visibility

- Security/Compliance: No new security exposure; fail closed on invalid staged delivery artifact

- Invariant Violated: A successful Greenfield package must carry source-grounded execution and visible handoff evidence across governed surfaces

- Root Cause: Greenfield integration stopped at governed artifact publication and relied on indirect surface refresh and terminal navigation rather than explicit execution/intervention contracts.

- Solution: Project a typed Execution Engine snapshot into next_steps_preview, validate the real staged Delivery Intelligence artifact, and render one explicit Assist fallback after confirmation.

- Verification: Focused Greenfield handoff, staged surface proof, CLI, transaction, and host confirmation tests; broader non-holdout Greenfield suite and browser matrix.

- Prevention: Keep engine seams in the sealed package and require fresh staged artifact evidence before confirmation; preserve visible fallback when native hooks are unverified.

- Agent Guardrails: Do not claim automatic chat delivery from hook context alone; do not restore prose parsing or add a second intervention channel.

- Preflight Checks: Search existing Casebook records; run focused tests before full validation; preserve final holdout untouched.

- Regression Tests Added: tests/unit/runtime/test_greenfield_authored_completion_handoff.py; tests/unit/runtime/test_greenfield_surface_refresh_proof.py; tests/unit/runtime/test_greenfield_host_confirmation.py

- Version/Build: 0.1.15 source-local checkpoint 9d01b7aa3

- Config/Flags: No new flags; 90/120/150 remain timing guidance

- Current intervention qualification (2026-09-23): The clean-source Codex
  status probe reports `Activation: degraded` even though the current session
  has `12` confirmed-in-chat Odylith events; this proves assistant-visible
  fallback delivery, not native activation. The clean-source Claude probe also
  reports `Activation: degraded` with zero recorded or confirmed events. The
  full intervention claim gate therefore remains closed until a reloaded,
  trusted host session reports `Activation: ready` plus chat visibility. No
  second intervention channel or post-confirm write was added.

- Engine integration posture (2026-09-23): `odylith validate engine-integrity`
  passes `22/22` engine areas, `22/22` handshakes, and `0` findings. This
  proves the product-level inventory and source/command anchors are wired; it
  does not substitute for native host activation, installed positive semantic
  qualification, strong review, or final holdout evidence.
