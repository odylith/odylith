- Bug ID: CB-145

- Status: Fixed Pending Release

- Created: 2026-04-30

- Severity: P1

- Reproducibility: Always

- Type: UX / lifecycle

- Description: Uninstall requests can be routed to raw deletion that Odylith blocks itself

- Impact: Operators asking Claude or Codex to uninstall Odylith can be trapped in a failed raw-deletion path instead of the supported uninstall command.

- Components Affected: install

- Environment(s): consumer repo, Claude Code CLI, Odylith v0.1.11 managed project assets

- Detected By: Maintainer transcript from dentoai-isb uninstall attempt

- Failure Signature: Assistant either ran `rm -rf .odylith odylith .agents .codex .claude AGENTS.md CLAUDE.md`, which Odylith PreToolUse denied, or paused an explicit `odylith uninstall` request with a destructive/no-dry-run warning, a commit/snapshot preflight, and incorrect claims that uninstall removes `.odylith/`.

- Trigger Path: User says 'just uninstall Odylith' in a Claude Code session with Odylith project hooks installed.

- Ownership: Odylith install lifecycle, host bash guard, and managed host guidance

- Timeline: 2026-04-30: Claude transcript shows uninstall intent mapped to rm -rf, the Odylith guard blocks the command, and the assistant suggests shutil.rmtree or a ! rm -rf bypass. A later transcript shows the same class without raw deletion: the user typed `odylith uninstall`, Claude inspected help, then stopped to warn that uninstall was destructive, claimed it would remove `.odylith/`, and asked whether to commit the untracked install before proceeding.

- Blast Radius: All consumer installs where host agents receive plain-English uninstall requests before v0.1.12.

- SLO/SLA Impact: P1 recovery regression: the supported exit path from a bad install can fail in front of the operator.

- Data Risk: Medium: raw deletion can remove governance truth and managed host assets outside the sanctioned uninstall audit path.

- Security/Compliance: Medium: suggesting a Python or shell bypass trains the agent to evade a safety hook rather than use the audited CLI lifecycle.

- Invariant Violated: Explicit uninstall intent must run `odylith uninstall`; safety hooks must block bypasses while pointing to the sanctioned command, and host guidance must not add commit/snapshot detours, second confirmation questions, or false removal scope.

- Root Cause: Managed host guidance and bash-guard remediation did not encode uninstall as a sanctioned Odylith CLI lifecycle path, while the guard only returned a generic destructive-deletion denial.

- Solution: Allow the Odylith uninstall CLI command through the guard, block raw shell/Python removal of Odylith-managed paths with a message naming odylith uninstall, and update guidance/tests so agents never suggest rm or shutil bypasses, commit/snapshot preflights, second confirmation detours, or `.odylith/` removal claims for explicit uninstall requests.

- Rollback/Forward Fix: Forward fix in v0.1.12; do not ask consumers to bypass hooks.

- Workaround: Before v0.1.12, type the exact repo-local lifecycle command yourself: `./.odylith/bin/odylith uninstall --repo-root .`. Do not accept an agent rewrite to raw deletion, a hook bypass, or a commit-first detour when you explicitly asked to uninstall.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_claude_host_bash_guard.py tests/unit/runtime/test_codex_host_bash_guard.py tests/unit/install/test_codex_project_assets.py tests/integration/install/test_bundle.py tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py::test_uninstall_guidance_rejects_raw_deletion_escape_hatches tests/unit/test_cli.py::test_uninstall_uses_uninstall_bundle tests/unit/test_cli.py::test_uninstall_reports_refusal_without_traceback tests/integration/install/test_manager.py::test_uninstall_bundle_detaches_and_removes_customer_odylith_tree tests/integration/install/test_manager.py::test_install_and_uninstall_remove_existing_customer_truth_tree tests/integration/install/test_manager.py::test_uninstall_bundle_unlinks_symlinked_odylith_without_following_target` passed (`51 passed`).

- Prevention: Keep uninstall routing, no-bypass language, no commit/snapshot detour language, and accurate `.odylith/` preservation scope in host-contract guidance and guard tests across Claude, Codex, and shipped project-root assets.

- Agent Guardrails: For plain-English uninstall requests, run ./.odylith/bin/odylith uninstall --repo-root . when available; never use rm -rf, shutil.rmtree, host-hook bypass instructions, commit/snapshot preflights, or a second confirmation question.

- Preflight Checks: Before uninstalling, check for the repo-local launcher and use the CLI; if missing, report the missing launcher and the hosted repair path instead of hand-deleting managed paths.

- Regression Tests Added: tests/unit/runtime/test_claude_host_bash_guard.py and tests/unit/runtime/test_codex_host_bash_guard.py cover uninstall allowlist and bypass denial; install mirror tests cover shipped hook parity; hygiene tests require host guidance to reject raw deletion, hook bypasses, commit/snapshot preflights, and `.odylith/` removal claims.

- Monitoring Updates: Watch 0.1.12 support transcripts for uninstall requests that still produce raw deletion or hook-bypass instructions.

- Version/Build: 0.1.11 observed; 0.1.12 target

- Config/Flags: Claude PreToolUse Bash hook via .agents/bin/odylith-host-launcher.py

- Customer Comms: Tell affected operators to upgrade to v0.1.12 and use odylith uninstall rather than deleting Odylith-managed directories.

- Related Incidents/Bugs: Related to CB for uninstall leaving odylith/ behind and the intervention visibility fallback leak.

- Code References: - src/odylith/runtime/surfaces/bash_guard_policy.py
- src/odylith/runtime/surfaces/claude_host_bash_guard.py
- src/odylith/runtime/surfaces/codex_host_shared.py
- src/odylith/install/manager.py
- odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md
- odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md
- odylith/agents-guidelines/CODEX_HOST_CONTRACT.md
