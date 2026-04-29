- Bug ID: CB-136

- Status: Closed

- Created: 2026-04-29

- Severity: P0

- Reproducibility: High

- Type: data-loss

- Description: Install overwrites Claude settings before verified runtime activation

- Impact: Consumer install can destroy existing Claude Code settings, credentials, permissions, and hooks, then leave broken Odylith hook commands after a corporate SSL or release-download failure.

- Components Affected: migration-runtime

- Environment(s): Consumer hosted install or reinstall in enterprise networks with SSL inspection, plus any repo whose .claude or .codex project settings already contain user-owned host configuration.

- Detected By: External user report after Odylith 0.1.11 GA install attempt behind corporate VPN SSL interception.

- Failure Signature: ~/.claude/settings.json or repo .claude/settings.json is replaced with Odylith-only hooks before urllib release asset download fails with certificate validation; Claude Code then runs hooks that point at missing Odylith launcher files.

- Trigger Path: curl -fsSL https://odylith.ai/install.sh | bash or odylith install/reinstall/doctor --repair before release runtime download and smoke proof complete.

- Ownership: Install lifecycle, managed project-root assets, Claude/Codex host settings activation, and migration-runtime release gating.

- Timeline: Captured 2026-04-29 through `odylith bug capture`.

- Blast Radius: Any new Odylith adopter with existing Claude or Codex project settings; enterprise users with SSL interception are most exposed because download failure happens after project settings mutation.

- SLO/SLA Impact: P0 adoption blocker: first install can break the operator's AI host environment and force manual credential/config reconstruction.

- Data Risk: High local configuration data-loss risk; AWS Bedrock and other host credentials or permissions can be removed from settings files even when install fails.

- Security/Compliance: Enterprise SSL interception and credential configuration are normal corporate controls; Odylith must not erase security-scoped host configuration.

- Invariant Violated: Install, reinstall, upgrade, and repair must not destructively mutate user-owned host settings before verified runtime activation succeeds, and host settings updates must be additive and rollback-safe.

- Root Cause: Managed project-root asset sync copied .claude/settings.json, .codex/config.toml, and .codex/hooks.json as full-file replacements, and install called that sync before release runtime download, verification, launcher creation, and smoke proof.

- Solution: Defer host settings activation until after runtime success; skip managed settings/config files during raw asset copy; merge Claude/Codex hooks and permissions into existing settings; preserve preimage backups; fail safe on invalid JSON and symlinked settings.

- Rollback/Forward Fix: Forward-fix in 0.1.12. Do not reuse 0.1.11; keep GA release immutable and roll this into the active 0.1.12 branch.

- Verification: 0.1.12 branch now has unit coverage for Claude credential/env/hook/permission preservation, invalid JSON refusal, symlink refusal, Codex hook merge, Codex config preservation, and Codex invalid JSON/symlink refusal. Install integration coverage proves install and upgrade preserve Claude/Codex host settings when runtime download fails before activation, and merge host settings only after verified runtime activation. Focused install manager, host asset, bundle, mirror, hygiene, and host contract suites passed on 2026-04-29.

- Closure Evidence: Implemented shared additive host settings helpers, skipped generated host config during raw project-root asset copy, disabled host settings activation during pre-runtime bootstrap/upgrade refresh, kept post-success activation additive, and preserved first preimage backups beside regular user-owned settings files.

- Prevention: Host settings files are user-owned extension points, not managed templates. Future project-root asset sync must keep generated config writers additive and transaction-gated.

- Agent Guardrails: Do not hand-edit or overwrite user host settings to make Odylith hooks work. Treat AI host config as customer data and preserve unknown keys, hooks, permissions, comments where possible, and preimages.

- Preflight Checks: Before changing install project-root assets, inspect bootstrap_assets.py, claude_cli_capabilities.py, codex_cli_capabilities.py, tests/unit/install/test_claude_effective_settings.py, tests/unit/install/test_codex_project_assets.py, and tests/integration/install/test_manager.py.

- Monitoring Updates: Watch install failure reports for SSL certificate errors, missing launcher hook invocations, and backup restoration complaints.

- Version/Build: 0.1.11 GA report; fix target 0.1.12.

- Config/Flags: Default hosted install, default Claude/Codex project asset sync, no special flags.

- Customer Comms: Acknowledge this as a serious install data-loss bug and state that 0.1.12 preserves existing Claude/Codex settings and activates Odylith hooks only after runtime success.

- Related Incidents/Bugs: CB-003 release atomicity/data-loss class; CB-134 generated reviewability and lock cleanup; CB-137 migration runtime gate adoption risk.

- Code References: - src/odylith/install/bootstrap_assets.py
- src/odylith/runtime/common/claude_cli_capabilities.py
- src/odylith/runtime/common/codex_cli_capabilities.py
- tests/integration/install/test_manager.py
