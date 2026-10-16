- Bug ID: CB-144

- Type: Product








- Status: FixedPendingRelease

- Created: 2026-04-30

- Severity: P1

- Reproducibility: Always


- Description: Intervention visibility fallback leaks internal instructions into Claude chat

- Impact: Claude Code operators see recursive, self-referential, or product-repo-specific Odylith copy instead of a plain explanation of the current state, making the intervention UX look broken.

- Components Affected: governance-intervention-engine

- Environment(s): Odylith v0.1.11 consumer install in Claude Code CLI with intervention visibility unproven for the active session.

- Detected By: Maintainer live-session complaints with copied Claude CLI transcripts showing the repeated Odylith Observation block, PostToolUse Edit output dumping Risks/History/Observation, and uninstall Stop output replaying product-repo IDs.

- Failure Signature: Claude hook output renders internal visibility copy such as `Odylith still has blocks waiting for transcript confirmation`, `Casebook already remembers CB-122`, `Odylith is ready to speak`, or `B-096` in a consumer repo that does not own those records.

- Trigger Path: Claude Code prompt, PostToolUse edit/Bash checkpoint, or stop-summary visibility-recovery path when no chat-visible Odylith beat has been confirmed.

- Ownership: governance-intervention-engine visible intervention copy contract

- Timeline: 2026-04-30: maintainer observed the repeated Claude CLI Observation after registry/atlas setup failures; repo search found the exact phrase in the shipped intervention-value adjudication corpus and related visibility fallback/runtime facts. Follow-up Claude uninstall and edit transcripts also showed product-theater copy (`brand promise`, `ready to speak`), visibility-proof jargon (`transcript confirmation`, `consistent visible lane`), and product-repo IDs (`B-096`, `CB-122`) leaking into a consumer repo that did not own those records. A later PostToolUse Edit transcript proved this was not only a Stop problem: successful governed edits printed Risks/History/Observation blocks directly after the edit receipt.

- Recurrence (2026-09-27 / 0.1.15): A Codex Stop hook emitted a blocking continuation whose reason instructed the next assistant message to reproduce an unrelated multi-item Insight/Risk/Assist block verbatim. The operator had asked for Greenfield goal status, but the continuation displaced that answer with stale B-096, B-001, `execution-engine`, and B-002 routing copy. This is the same trust failure on a Codex transport: hidden continuity became a standalone user-visible response instead of remaining subordinate to the user's request.

- Blast Radius: Claude PostToolUse and Stop hooks, Claude/Codex visible-intervention fallback copy, value-engine adjudication corpus, prompt-context/stop-summary tests, shipped guidance, and consumer trust in intervention UX.

- SLO/SLA Impact: High product-experience impact; the intervention system can be active but present internal recovery instructions as user-facing copy.

- Data Risk: Low data loss risk; high governed-memory and operator-trust risk because the visible recovery message is misleading.

- Security/Compliance: No direct security exposure, but internal host/control-plane vocabulary can leak into public-facing operator transcript.

- Invariant Violated: User-visible Odylith Observation, Assist, Risk, History, Insight, and Proposal copy must describe the user-relevant state, not internal rendering instructions, proof jargon, product-theater language, Stop-hook recovery directives, or product-repo governance IDs that do not exist in the current repo.

- Workaround: Operators can manually state the real status in chat; release builds must stop emitting the recursive copy.

- Root Cause: Visibility recovery text was authored as internal/product-repo proof language and then blessed as visible Observation/Assist/History copy in the runtime, tests, and adjudication corpus. The alignment context also injected Odylith product-repo anchors into consumer-repo visibility recovery, so consumer chat could mention `B-096` or `CB-122` even when those records did not exist locally.

- Recurrence Root Cause (2026-09-27 / 0.1.15): Removing the blocking Stop continuation was necessary but initially incomplete. Prompt-submit and Codex Stop still selected unresolved replay by host/session alone and assigned the entire stale bundle directly to `systemMessage`; the answer-first rule applied only to `additionalContext` and could not suppress already-emitted visible text. The first regression covered one Insight and inspected only hidden context, so it did not reproduce the escaped multi-item wall.

- Solution: Replace recursive/internal visibility copy with user-facing status text, clean the adjudication corpus, add regression tests that reject internal instruction phrases, product-theater phrases, and repo-specific IDs in visible intervention candidates, stop blocking Stop hooks on both Codex and Claude, keep all assistant-render fallback context explicitly subordinate to a complete direct answer, keep product-repo visibility anchors out of consumer-repo visible recovery copy, make Claude direct-edit/Bash PostToolUse hooks silent on success with compact failure/skipped-refresh output only, and add a consumer `doctor --repair` cleanup for stale 0.1.11 Compass stream events that mention product-repo-only visibility IDs absent from local Radar/Casebook truth.

- Rollback/Forward Fix: Forward-fix only; rollback would preserve the v0.1.11 transcript behavior.

- Verification: Focused visibility, value-engine, prompt/stop, and browser regression suite passed: `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_visibility_broker.py tests/unit/runtime/test_host_visible_intervention.py tests/unit/runtime/test_host_intervention_support.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_intervention_host_surface_runtime.py tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_value_engine.py tests/unit/runtime/test_intervention_delivery_status.py tests/unit/runtime/test_claude_host_stop_summary.py tests/unit/runtime/test_codex_host_stop_summary.py tests/integration/runtime/test_intervention_visibility_browser.py` (`205 passed`).

- Follow-Up Verification (2026-04-30 / 0.1.12): Claude Stop main no longer emits any Stop `systemMessage` for visible-intervention replay or Assist closeout, `stop_payload` no longer blocks Stop dispatch for visibility delivery, and consumer-repo visibility recovery does not mention Odylith product repo IDs. Focused proof: `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_claude_host_stop_summary.py` plus the broader visibility suite before release.

- Follow-Up Evidence (2026-04-30 / 0.1.12): A Claude PostToolUse Edit transcript showed the same class through a different hook: after updating a consumer Registry component spec, the Edit hook visibly printed Risks/History/Observation text and `CB-122` instead of staying silent on successful governed refresh.

- Follow-Up Evidence (2026-04-30 / 0.1.12): Read-only inspection of the affected consumer repo showed the Registry manifest was normalized, but stale 0.1.11 Compass streams and rendered Registry detail timelines still contained `B-096`, `CB-122`, `transcript confirmation`, and `Odylith is ready to speak` events. This required an upgrade-repair cleanup, not only prevention of new hook output.

- Follow-Up Evidence (2026-04-30 / 0.1.12): Maintainer clarified that ambient blocks, interventions, and Assist should remain; the broken class is fake or templated copy leaking from refresh, status, Stop, and other non-author lanes. Codex post-bash success receipts and Codex Stop-generated closeouts were confirmed as the same noise class and now stay silent unless replaying an already-earned visible beat or reporting a compact failure/skipped refresh.

- Follow-Up Verification (2026-09-27 / 0.1.15): Removed Codex Stop's blocking continuation path and its verbatim replay instruction. Prior-turn replay is no longer assigned to Codex or Claude prompt `systemMessage`, the supported Claude split/legacy `prompt-context` lane no longer prepends replay to hidden context, and Codex Stop emits no intervention replay; only current-prompt decisions remain eligible at prompt time, while Stop may report compact failure-level governance status. Prompt/checkpoint fallback context requires the assistant to answer the current user request completely first, permits at most one relevant concise line afterward, and requires stale, unrelated, conflicting, or already-visible material to be omitted. Exact cross-host and split-lane regressions seed the escaped three-Insight, one-Risk, one-Assist wall and prove none of it reaches the new status prompt. The focused host, hook, broker, parity, and browser suite passes 269 tests, and static inspection finds no replay call or verbatim replay instruction in any supported prompt/Stop surface.

- Follow-Up Verification (2026-09-30 / 0.1.15): A live `odylith codex intervention-status` on the long-running Greenfield session still offered three unconfirmed 2026-09-27 Insight notes about Compass, B-001, and `execution-engine` as its next assistant-visible replay. Prompt/Stop hooks no longer inject that wall, but explicit status and manual `visible-intervention` shared a replay read model that selected by session and confirmation state without a time boundary. The source-local read model now limits assistant-visible replay to a 30-minute moment. Old events remain unconfirmed in the diagnostic ledger; expiry does not manufacture chat visibility or native activation. The same live session now reports zero replay blocks, three unconfirmed events, and `Activation: unverified`. Focused Codex/Claude visibility, status, and browser tests, including stale-note browser rendering, pass (`138 passed`). Installed runtime and fresh native hook delivery still require separate release proof.

- Prevention: Visible intervention fixtures, Codex/Claude prompt and checkpoint contracts, generated recovery copy, consumer Compass repair logic, and guidance are scanned for control-plane terms, recursive instructions, product-theater language, repo-specific IDs, blocking Stop continuations, and any fallback instruction that can replace the user's requested answer.

- Agent Guardrails: Do not call internal delivery, hook, ledger, fallback, transcript-proof, brand-promise, or product-repo memory instructions user-facing Odylith Observations.

- Preflight Checks: Search visible intervention source/corpus text for internal instruction phrases, then run the focused regression suite.

- Regression Tests Added: tests/unit/runtime/test_intervention_value_engine.py::test_adjudication_corpus_rejects_internal_user_visible_copy; tests/unit/runtime/test_intervention_value_engine.py::test_adjudication_corpus_rejects_product_theater_and_repo_ids_in_visible_copy; tests/unit/runtime/test_intervention_visibility_broker.py::test_broker_suppresses_recursive_internal_visible_copy; tests/unit/runtime/test_intervention_visibility_broker.py::test_broker_suppresses_visible_copy_with_unresolved_local_governance_ids; tests/unit/runtime/test_intervention_host_surface_runtime.py::test_stop_payload_never_forces_a_follow_up_assistant_turn; tests/unit/runtime/test_intervention_host_surface_runtime.py::test_visible_delivery_fallback_cannot_replace_the_user_answer; updated host visibility recovery assertions; consumer-repo no-`B-096`/`CB-122` visible-copy assertions; Codex/Claude Stop assertions that visibility delivery never blocks hook dispatch; Claude/Codex PostToolUse edit/Bash tests that successful checkpoints emit no transcript payload; consumer runtime repair tests for stale 0.1.11 Compass stream cleanup; and hygiene coverage that bans successful hooks from acting like fresh visible-intervention author lanes.

- Monitoring Updates: Treat future user complaints about repeated Odylith Observation copy as a visible-copy regression, not just a delivery-ledger issue.

- Version/Build: v0.1.11 observed; target fix v0.1.12

- Config/Flags: Claude Code hooks enabled; chat_visible_proof unproven_this_session

- Customer Comms: Tell affected operators to upgrade to v0.1.12 once released.

- Related Incidents/Bugs: Related to CB-121 intervention hook payloads can be generated but never reach chat-visible UX.

- GitHub Status: fixed_pending_release

- GitHub Issue: https://github.com/odylith/odylith/issues/22

- GitHub Umbrella Scope: v0.1.12 recovery issue consolidating CB-139, CB-140, CB-141, CB-142, CB-143, CB-144, CB-145, CB-065, CB-121, and CB-122 across first-run install, Registry, Atlas-first onboarding, generated host assets, uninstall, hook visibility, stale Compass memory, and noisy CLI surfaces.

- Fixed In: 0.1.12

- Public Response: pending

- Code References: - src/odylith/runtime/intervention_engine/visibility_broker.py
- src/odylith/runtime/intervention_engine/fact_producer_runtime.py
- src/odylith/runtime/intervention_engine/value_engine_corpus.py
- odylith/runtime/source/intervention-value-adjudication-corpus.v1.json
