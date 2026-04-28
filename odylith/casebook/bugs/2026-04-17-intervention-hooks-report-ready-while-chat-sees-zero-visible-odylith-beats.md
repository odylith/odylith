- Bug ID: CB-122

- Status: Closed

- Closed: 2026-04-26

- Closure Evidence: v0.1.11 now separates static hook readiness from end-to-end chat-visible proof. `odylith codex intervention-status` reports `Activation: ready` with `Chat-visible proof: proven_this_session` for the active Codex session, while unproven host sessions explicitly remain unproven and instruct the assistant to render the visible fallback before claiming active UX. The shipped contract now gates full completion on `Activation: ready` plus `chat_visible_proof=proven_this_session`, not hook payload generation.

- Created: 2026-04-17

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: Recurrence of CB-121: Codex and Claude intervention-status can report static activation ready while the active session has chat_visible_proof=unproven_this_session, zero recent intervention events, and zero proven-visible events. The user observed no ambient highlights, no intervention blocks, and no Odylith Assist across the session, proving generated hook payloads and hidden additionalContext are not sufficient product proof.

- Impact: Operators receive no in-chat Odylith intervention UX even when the runtime claims hooks are armed, so the core intervention product contract silently fails.

- Components Affected: governance-intervention-engine

- Environment(s): Odylith product repo maintainer mode, Codex Desktop session, target release v0.1.11; Claude status path has the same proof-state gap.

- Detected By: User-visible session report plus odylith codex/claude intervention-status showing unproven chat-visible proof.

- Failure Signature: intervention-status activation=ready; chat_visible_proof=unproven_this_session; delivery ledger 0 recent events and 0 proven-visible events; chat transcript contains no Odylith Observation, Proposal, ambient signal, or Assist.

- Trigger Path: Substantive Codex conversation using native desktop tools and hook-backed intervention runtime without explicit assistant-rendered fallback.

- Ownership: Governance Intervention Engine and host surface adapters

- Timeline: 2026-04-16: CB-121 was marked resolved with manual fallback and delivery ledger proof. Later in the same v0.1.11 session, the user reported zero visible ambient highlights, intervention blocks, or Assist despite static activation readiness.

- Blast Radius: Codex and Claude chat-visible intervention lanes; prompt, post-tool, stop, manual fallback, Compass ledger, and intervention status surfaces.

- SLO/SLA Impact: P0 product trust failure for v0.1.11: chat-visible intervention proof can be absent while readiness appears green.

- Data Risk: No direct data loss; governance delivery state can mislead operators.

- Security/Compliance: No security exposure identified; compliance risk is false operational attestation.

- Invariant Violated: Hook systemMessage or additionalContext generation is not proof of chat-visible UX; earned intervention beats must surface inside chat or be marked unproven.

- Workaround: Run the visible-intervention fallback and render the Markdown directly, but this is not acceptable as the primary product path.

- Root Cause: Static hook readiness, hidden fallback-ready payloads, and actual chat-visible proof are still separate surfaces. The runtime lacks one shared visibility decision broker that carries Context Engine, Execution Engine, memory, Tribunal, host adapter, and ledger evidence into the assistant-visible output path.

- Solution: Introduce a shared visible-intervention decision broker, hard fail-visible when session proof is missing, and distinguish fallback-ready from chat-confirmed delivery states.

- Rollback/Forward Fix: Forward fix only; reverting would preserve a false-ready intervention posture.

- Verification: Add transcript-harness tests for Codex and Claude, focused intervention runtime tests, host compatibility tests, context/execution integration tests, and browser-visible status checks.

- Prevention: Never count generated hook JSON, systemMessage, or hidden additionalContext as visible proof unless exact Odylith Markdown is observed or confirmed through the chat transcript lane.

- v0.1.12 Follow-up Prevention: Prompt-submit no longer depends on a host-specific or manual-only fallback path for ordinary non-passthrough prompts. `src/odylith/runtime/surfaces/host_intervention_support.py` now owns the shared prompt-visible Assist bundle and Markdown composition used by Codex prompt context, Claude prompt context, Claude prompt teaser, and manual visible-intervention fallback. A normal prompt now emits the same `**Odylith Assist:** kept Odylith visible in this chat so the brand promise is something the user can see.` line across Codex and Claude, while `Odylith, help` and `Odylith, show me what you can do` remain stdout-clean route locks. Proof: focused host/intervention suite `147 passed`; install/mirror/hygiene suite `74 passed`; install integration `85 passed`; browser intervention/onboarding matrix `28 passed`; `odylith validate guidance-behavior` and `odylith validate discipline` passed.

- Agent Guardrails: When intervention-status is unproven in the active session, the assistant must render the Odylith Markdown directly before claiming the UX is active.

- Preflight Checks: Run odylith codex intervention-status and odylith claude intervention-status; assert chat-visible proof before making active-UX claims.

- Monitoring Updates: Delivery ledger must expose fallback-ready versus chat-confirmed counts and status text must keep ready-but-unproven distinct.

- Version/Build: v0.1.11

- Config/Flags: features.codex_hooks=true; Codex PostToolUse Bash-only; Claude direct edit and Bash hook coverage

- Customer Comms: No external customer comms; release blocker closed for v0.1.11 with the visibility-proof gate and assistant-render fallback contract.

- Related Incidents/Bugs: CB-121; B-096

- Code References: - src/odylith/runtime/intervention_engine/host_surface_runtime.py
- src/odylith/runtime/surfaces/host_visible_intervention.py
- src/odylith/runtime/surfaces/host_intervention_status.py
