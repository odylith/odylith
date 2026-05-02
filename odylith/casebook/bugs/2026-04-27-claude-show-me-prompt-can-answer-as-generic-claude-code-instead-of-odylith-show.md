- Bug ID: CB-129

- Type: Product








- Status: Closed

- Created: 2026-04-27

- Severity: P2

- Reproducibility: High


- Description: Claude show-me prompt can answer as generic Claude Code instead of Odylith show

- Impact: New operators asking 'odylith, show me what you can do' can see a generic Claude Code capability list instead of the scenario-aware Odylith show report, breaking the first-run mental model and brand trust.

- Components Affected: odylith-chatter

- Environment(s): Claude Code consumer or maintainer repo with Odylith project hooks installed.

- Detected By: Operator screenshot of Claude Code first-pass response.

- Failure Signature: Claude replies 'I'm Claude Code — not odylith' and lists host tools, memory, branch cleanliness, skills, and possible next moves instead of running odylith show stdout.

- Trigger Path: UserPromptSubmit: odylith, show me what you can do

- Ownership: Odylith Claude show-me prompt guard and installed Claude project assets

- Timeline: Captured 2026-04-27 from operator screenshot after prior formatter hardening.

- Blast Radius: First-run Claude Code onboarding for installed consumer repos and Odylith maintainer dogfood sessions.

- SLO/SLA Impact: High trust and adoption impact on the first product prompt; no runtime SLO impact.

- Data Risk: Low

- Security/Compliance: No direct security impact.

- Invariant Violated: The show-me prompt must route to odylith show stdout only and must never answer as generic host capability inventory.

- Root Cause: The Claude show-me guard matched the prompt but used advisory additionalContext, while generated Claude permissions did not explicitly allow odylith show; Claude could ignore the product lane and answer from host capability defaults.

- Solution: Make the show-me guard a route lock that forbids generic Claude capability answers, root/doc inspection, branch status, memory/skill listings, and follow-up prompts; add explicit Claude allowlist entries for ./.odylith/bin/odylith show and ./.odylith/bin/odylith --help in live and bundled settings; pin lower-case comma prompt coverage; and codify the route lock in the Claude host contract plus mirrored bundle copy.

- Verification: pytest tests/unit/test_claude_project_hooks.py tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_claude_cli_capabilities.py tests/unit/runtime/test_show_capabilities.py; pytest tests/unit/runtime/test_hygiene.py; live hook smoke for payload {"prompt":"odylith, show me what you can do"} returns route-lock additionalContext and no stderr.

- Prevention: Keep show-me first-match route tests covering lower-case prompts, route-lock wording, forbidden generic Claude response content, and Claude settings permission for odylith show.

- Regression Tests Added: tests/unit/test_claude_project_hooks.py covers lowercase show-me route lock; tests/unit/install/test_claude_effective_settings.py and tests/unit/runtime/test_claude_cli_capabilities.py cover show/help permission allowlist; tests/unit/runtime/test_show_capabilities.py covers shipped guard wording; tests/unit/runtime/test_hygiene.py covers the Claude host-contract and bundle route-lock wording.

- Code References: - .claude/hooks/show-me-prompt-guard.py
- src/odylith/bundle/assets/project-root/.claude/hooks/show-me-prompt-guard.py
- src/odylith/runtime/common/claude_cli_capabilities.py
- .claude/settings.json
- src/odylith/bundle/assets/project-root/.claude/settings.json
- odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md
- src/odylith/bundle/assets/odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md
