- Bug ID: CB-127

- Type: ProductUXRegression


- Status: Closed

- Created: 2026-04-25

- Severity: P1

- Reproducibility: Consistent


- Description: A plain Odylith help fast-path turn printed raw CLI help, then surfaced an unrelated topology Observation tied to B-096. The intervention scorer treated command catalog stdout and stale replay state as live conversation evidence, producing a confusing branded interruption instead of staying silent.

- Impact: Operators asking for CLI help can receive irrelevant Odylith Observation copy after the command output, reducing trust in live interventions and making the product feel out of context.

- Components Affected: governance-intervention-engine

- Environment(s): Odylith product repo maintainer Codex session, v0.1.11 intervention runtime

- Detected By: User pasted the out-of-context help transcript and Observation into the Codex session.

- Failure Signature: Raw odylith --help output was followed by '**Odylith Observation:** The discussion is already reasoning in topology, ownership, or boundary terms. Radar already tracks B-096...'

- Trigger Path: Plain 'Odylith, help' or equivalent first-match help passthrough prompt with pending or computed live intervention state.

- Ownership: governance-intervention-engine prompt-submit relevance and host-visible narration contract

- Timeline: 2026-04-25: User reported raw help stdout followed by irrelevant topology Observation in Codex chat.

- Blast Radius: Codex and Claude prompt-submit hooks, visible-intervention fallback, prompt teaser replay, and any host path that mixes raw CLI help stdout with intervention scoring.

- SLO/SLA Impact: High product trust impact for live intervention UX; no data-plane availability impact.

- Data Risk: None known; failure is relevance, narration, and UX trust only.

- Security/Compliance: None known; no secret exposure or compliance boundary change.

- Invariant Violated: First-match CLI help/show passthrough routes must print requested stdout only; raw command catalogs are not conversation evidence and must not earn Odylith live narration.

- Workaround: Render the requested CLI help output only and omit Odylith Observation/Proposal/Assist for passthrough help/show prompts.

- Root Cause: The fact producer and signal profile accepted raw CLI help stdout as assistant-summary evidence, and prompt-submit fallback/replay did not suppress pending live narration for first-match passthrough prompts.

- Solution: Detect help/show passthrough prompts and raw CLI help stdout, suppress live narration and replay for those routes, remove CLI help from fact/evidence scoring, and tighten generic topology copy for real architecture prompts.

- Rollback/Forward Fix: Forward fix only; reverting preserves the confusing live-narration behavior.

- Verification: Focused runtime regressions passed (`107 passed`): prompt-context, visible-intervention, stop-summary, host-support, and intervention-engine tests prove help passthrough renders no Odylith narration even with pending replay. Browser/shell mirror tests passed (`66 passed`), guidance-behavior validation passed, Casebook source validation passed, and direct visible-intervention smokes proved prompt-submit and stop-summary silence for `Odylith, help` plus raw CLI help stdout.

- Prevention: Keep first-match command-output routes fail-quiet for live narration, and require observation facts to be rooted in the current user request rather than command catalogs or Odylith self-summary strings.

- Agent Guardrails: Do not narrate Odylith topology or governance observations after plain help/show commands. If a command prints usage text, treat it as output, not semantic prompt evidence.

- Preflight Checks: Before claiming live narration relevance, verify the prompt is not a help/show passthrough and assistant summary is not raw CLI help stdout.

- Regression Tests Added: tests/unit/runtime/test_host_intervention_support.py, tests/unit/runtime/test_host_visible_intervention.py, tests/unit/runtime/test_codex_host_prompt_context.py, tests/unit/runtime/test_claude_host_prompt_context.py

- Monitoring Updates: intervention-status remains the visibility ledger; this fix adds deterministic passthrough suppression rather than a new monitor.

- Version/Build: v0.1.11 maintainer branch 2026/freedom/v0.1.11

- Config/Flags: No config flags; unconditional passthrough suppression.

- Customer Comms: No external customer communication required; maintainer-visible UX regression.

- Related Incidents/Bugs: B-096, CB-121, CB-122, CB-123

- Code References: - src/odylith/runtime/intervention_engine/fact_producer_runtime.py
- src/odylith/runtime/intervention_engine/signal_kernel.py
- src/odylith/runtime/surfaces/host_intervention_support.py
- src/odylith/runtime/surfaces/host_visible_intervention.py
