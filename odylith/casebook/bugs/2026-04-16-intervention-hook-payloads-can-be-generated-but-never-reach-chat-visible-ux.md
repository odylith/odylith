- Bug ID: CB-121

- Status: Open

- Created: 2026-04-16

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Intervention hook payloads can be generated but never reach chat-visible UX

- Impact: Operators can see no Odylith Observation, Proposal, or Assist even while hooks and direct smoke commands produce structured payloads, breaking the core intervention UX.

- Components Affected: governance-intervention-engine

- Environment(s): Odylith product repo maintainer lane on branch 2026/freedom/v0.1.11, Codex Desktop thread using native exec/apply_patch tools and Claude Code hook-output reports.

- Detected By: Maintainer live-session complaint that no interventions or Odylith Assist were visible, followed by Codex binary schema inspection and direct hook smoke comparison.

- Failure Signature: Direct odylith codex/claude hook commands emit systemMessage/additionalContext, but the active chat shows no Observation, Proposal, Ambient beat, or Assist; Codex PostToolUse schema exposes Bash only while desktop tool calls use native exec/apply_patch paths.

- Trigger Path: Rely on hook systemMessage/additionalContext as the only UX delivery lane for Odylith Interventions and Assist.

- Ownership: governance-intervention-engine host visibility contract

- Timeline: After direct hook smokes passed, the maintainer still saw no chat output in Codex and Claude. Session-log and binary-schema inspection showed Codex Desktop native tool calls bypass Bash-only PostToolUse coverage and hook systemMessage was not a reliable visible transcript channel.

- Blast Radius: Codex and Claude live intervention UX, Odylith Assist closeouts, host compatibility reporting, and consumer trust in governance capture.

- SLO/SLA Impact: High product-experience impact: the flagship intervention UX can silently disappear despite green structured-output tests.

- Data Risk: Low data loss risk, high governed-memory and operator-trust risk because important observations and proposals are generated but unseen.

- Security/Compliance: None directly.

- Invariant Violated: Generated hook payload is not proof of chat-visible UX; every earned Odylith intervention must have a visible assistant-render or proven host-render path.

- Root Cause: The host contract conflated structured hook output with chat visibility and overclaimed Codex native tool hook coverage. The renderer also kept Assist primarily in hidden continuity/stop paths without a fail-visible assistant-render fallback.

- Solution: Add assistant-render fallback instructions to prompt/checkpoint additionalContext, add one-shot Stop continuation for missed closeout visibility, add shared codex/claude visible-intervention commands, reduce Codex hook matcher truth to Bash, let Stop-summary Assist recover from concrete validation/pass proof when changed paths are unavailable, and update compatibility posture/guidance to stop treating systemMessage as visible proof.

- Rollback/Forward Fix: Forward-fix only; reverting would restore silent hook-output dependence.

- Verification: Focused host/intervention suite passes: 551 tests covering fallback context, Stop one-shot visibility, visible-intervention CLI, summary-proof Assist recovery, Codex Bash-only hook truth, Claude/Codex parity, install/bundle shipping, and CLI audit coverage.

- Prevention: Regression tests must fail when a host payload carries only hidden context without assistant-render fallback, and compatibility reports must distinguish structured hook generation from chat-visible delivery.

- Agent Guardrails: When host hook visibility is unproven, agents must render the Odylith visible-intervention Markdown or fallback block directly in chat instead of saying the engine is active.

- Preflight Checks: Before claiming interventions are active, verify both structured hook generation and a chat-visible render path for the current host/session.

- Regression Tests Added: tests/unit/runtime/test_intervention_host_surface_runtime.py, tests/unit/runtime/test_host_visible_intervention.py, tests/unit/runtime/test_codex_host_compatibility.py, tests/unit/runtime/test_claude_cli_capabilities.py, tests/unit/runtime/test_claude_host_compatibility.py, tests/unit/runtime/test_codex_host_stop_summary.py, tests/unit/runtime/test_claude_host_stop_summary.py, tests/unit/test_cli_audit.py

- Monitoring Updates: Compatibility output now names assistant-render fallback as the chat-visible UX path and does not claim Codex native desktop tool hooks as automatic coverage.

- Version/Build: v0.1.11 maintainer branch

- Config/Flags: .codex/hooks.json PostToolUse matcher Bash; .claude/settings.json PostToolUse Write|Edit|MultiEdit and Bash

- Related Incidents/Bugs: Related to B-096 intervention engine rollout and the existing Odylith Assist closeout contract.

- Code References: - src/odylith/runtime/intervention_engine/host_surface_runtime.py
- src/odylith/runtime/surfaces/host_visible_intervention.py
- src/odylith/runtime/common/codex_cli_capabilities.py
- src/odylith/runtime/common/claude_cli_capabilities.py
