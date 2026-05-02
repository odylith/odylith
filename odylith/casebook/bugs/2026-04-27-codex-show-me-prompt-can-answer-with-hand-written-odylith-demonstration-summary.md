- Bug ID: CB-130

- Type: Product



- Status: Closed

- Created: 2026-04-27

- Severity: P2

- Reproducibility: High


- Description: Codex show-me prompt can answer with hand-written Odylith demonstration summary

- Impact: New operators asking 'odylith, show me what you can do' in Codex can see a hand-written diagnostic demonstration summary instead of scenario-aware odylith show stdout, breaking first-run trust and mental model.

- Components Affected: odylith-chatter

- Environment(s): Codex consumer or maintainer repo with Odylith project guidance and hooks installed.

- Detected By: Operator screenshot of Codex first-pass response.

- Failure Signature: Codex replies 'Here's what Odylith just demonstrated in this repo' and lists install posture, dirty path, impact packet, exact-path context, module counts, tmp clone noise, and spawn policy instead of printing odylith show stdout verbatim.

- Trigger Path: UserPromptSubmit: odylith, show me what you can do

- Ownership: Odylith Codex show-me route lock, Codex prompt-context hook, managed AGENTS guidance, and show-me skill assets

- Timeline: Captured 2026-04-27 through `odylith bug capture`.

- Blast Radius: First-run Codex onboarding for installed consumer repos and Odylith maintainer dogfood sessions.

- SLO/SLA Impact: High trust and adoption impact on the first product prompt; no runtime SLO impact.

- Data Risk: Low

- Security/Compliance: No direct security impact.

- Invariant Violated: The Codex show-me prompt must route to odylith show stdout only and must never be paraphrased into a host-authored demonstration, install diagnosis, context scan, or spawn-policy explanation.

- Root Cause: Codex prompt-context correctly suppressed intervention narration for passthrough show/help prompts, but it emitted no replacement route-lock context. That left Codex relying on broad repo guidance and the show-me skill, which were not explicit enough to forbid hand-authored demonstration summaries or diagnostic recaps when the first prompt matched the Odylith show lane.

- Solution: Added a shared passthrough prompt kind classifier; made `odylith codex prompt-context` emit hidden route-lock additionalContext for show/help prompts before normal prompt observation; hardened repo-root and installed AGENTS guidance, the Codex host contract, and show-me skill source/bundle copies to require stdout-only `odylith show` and forbid hand-written demonstration summaries, install posture narration, dirty-path analysis, context packet summaries, module-count scans, tmp clone warnings, spawn-policy notes, and follow-up questions.

- Verification: pytest tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_host_intervention_support.py tests/unit/runtime/test_intervention_cross_host_parity.py tests/unit/runtime/test_intervention_host_surface_runtime.py; pytest tests/unit/runtime/test_show_capabilities.py tests/unit/runtime/test_incremental_import_graph.py; pytest tests/integration/install/test_manager.py tests/integration/install/test_bundle.py; pytest tests/unit/install/test_codex_project_assets.py tests/unit/install/test_claude_effective_settings.py; pytest tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py; pytest tests/unit/test_claude_project_hooks.py tests/unit/runtime/test_claude_cli_capabilities.py; source-runtime hook smokes for Codex show/help route locks.

- Prevention: Keep Codex passthrough prompts route-locked in hook additionalContext, managed guidance, host contracts, and show-me skills; keep regression tests asserting the screenshot failure content is forbidden and that show/help route locks bypass normal prompt observation.

- Regression Tests Added: tests/unit/runtime/test_codex_host_prompt_context.py covers Codex show/help route-lock payloads and bypass of prompt observation; tests/unit/runtime/test_hygiene.py covers Codex host-contract and bundle route-lock wording; tests/unit/runtime/test_show_capabilities.py covers managed AGENTS and show-me skill stdout-only wording.

- Code References: - src/odylith/runtime/surfaces/codex_host_prompt_context.py
- src/odylith/runtime/intervention_engine/fact_producer_runtime.py
- AGENTS.md
- odylith/AGENTS.md
- src/odylith/install/agents.py
- odylith/agents-guidelines/CODEX_HOST_CONTRACT.md
- odylith/skills/odylith-show-me/SKILL.md
