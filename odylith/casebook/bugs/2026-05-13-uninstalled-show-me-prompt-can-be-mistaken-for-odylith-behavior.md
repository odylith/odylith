- Bug ID: CB-201

- Status: Open

- Created: 2026-05-13

- Severity: P2

- Reproducibility: High

- Type: OperatorUX

- Description: Uninstalled show-me prompt can be mistaken for Odylith behavior

- Impact: A user can ask an Odylith-branded show-me prompt in a folder without an Odylith install and see the host build arbitrary demo files, making generic host behavior look like an Odylith product failure.

- Components Affected: odylith-chatter

- Environment(s): Codex or Claude host session opened in a folder that has no repo-local Odylith launcher or installed Odylith guidance.

- Detected By: Operator report from /Users/freedom/mock/garden-robot: show-me prompt in an uninstalled folder produced a garden robot demo app.

- Failure Signature: Host created index.html, app.js, styles.css, and README.md after 'Odylith, show me what you can do' instead of reporting that Odylith was not installed or running odylith show.

- Trigger Path: User prompt: Odylith, show me what you can do; current folder lacks ./.odylith/bin/odylith and installed Odylith guidance.

- Ownership: Host route-lock guidance, show-me skill assets, and installed AGENTS managed block.

- Timeline: Captured after operator clarified /Users/freedom/mock/garden-robot had no Odylith installation.

- Blast Radius: First-run onboarding in empty or newly created folders before Odylith has been installed.

- SLO/SLA Impact: High trust impact on first-use product experience; no runtime availability SLO impact.

- Data Risk: Low data risk, but unintended workspace writes can create files the user did not ask Odylith to create.

- Security/Compliance: Policy and workspace-write safety issue: the host must not turn an Odylith-branded advisory prompt into unapproved file creation, and missing-install posture must be explicit before any write.

- Invariant Violated: An Odylith show-me request must either run Odylith show in an installed repo or clearly report that Odylith is not installed; it must never be substituted with generic host sample-app creation.

- Root Cause: Outside an installed repo, Odylith hook assets and route locks are unavailable, so the host treated the phrase as an ordinary build request; installed route locks also did not explicitly forbid sample-app creation.

- Solution: Hardened shared show-me route locks, installed show-me skills, managed AGENTS guidance, and Codex prompt payloads to forbid sample-app creation and to report missing Odylith instead of substituting generic host work.

- Rollback/Forward Fix: Forward fix only; no product data rollback required.

- Verification: pytest tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_show_capabilities.py tests/unit/runtime/test_hygiene.py; pytest tests/unit/test_claude_project_hooks.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/install/test_codex_project_assets.py

- Prevention: Keep show-me route locks host-model agnostic, stdout-only, and explicit that missing Odylith is a blocker rather than permission to build demos.

- Agent Guardrails: Do not answer Odylith-branded show-me prompts with arbitrary repo scans or sample app creation; run odylith show or report the missing install.

- Regression Tests Added: Codex route-lock tests now assert sample-app creation is forbidden and route context is also delivered through systemMessage; show-me skill tests assert missing-install wording.

- Code References: - src/odylith/runtime/surfaces/host_prompt_route_locks.py
- src/odylith/runtime/surfaces/codex_host_prompt_context.py
- odylith/skills/odylith-show-me/SKILL.md
- src/odylith/install/agents.py
