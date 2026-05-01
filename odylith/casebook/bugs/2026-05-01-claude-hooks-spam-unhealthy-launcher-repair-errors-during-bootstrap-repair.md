- Bug ID: CB-147

- Status: Open

- Created: 2026-05-01

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Claude hooks spam unhealthy launcher repair errors during bootstrap repair

- Impact: Claude Code users see repeated non-blocking UserPromptSubmit, PreToolUse, and Stop hook errors that say the Odylith launcher is untrusted or unhealthy, including while running the exact bootstrap doctor repair command the hook error recommends.

- Components Affected: governance-intervention-engine

- Environment(s): Consumer repo on v0.1.12 pinned_release during migration repair, observed in Claude Code CLI with .odylith/bin/odylith present but unhealthy and .odylith/bin/odylith-bootstrap available.

- Detected By: Operator transcript from 2026-05-01 migration feedback in a consumer repo.

- Failure Signature: Hook output repeats: Failed with non-blocking status code: Odylith launcher detected untrusted or unhealthy runtime state. From the repo root, try ./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair.

- Trigger Path: Claude Code UserPromptSubmit, PreToolUse:Bash, and Stop hooks dispatch through .agents/bin/odylith-host-launcher.py before or during bootstrap doctor --repair.

- Ownership: Claude/Codex project-root host launcher dispatch and migration repair UX boundary.

- Timeline: Captured 2026-05-01 through `odylith bug capture`.

- Blast Radius: Consumer repos with Claude project hooks installed and a stale or untrusted main Odylith launcher; migration, repair, and first prompt surfaces are affected.

- SLO/SLA Impact: Migration confidence and repair usability regression; repair remains possible but appears broken and noisy in the host transcript.

- Data Risk: Low direct data risk; no customer data exposure identified.

- Security/Compliance: Security communication risk: a recoverable stale launcher state is presented repeatedly as an untrusted runtime error in ambient hooks, weakening operator trust during supply-chain repair.

- Invariant Violated: Ambient host hooks must degrade quietly or route through the recovery-capable launcher during repair states; they must not spam the user with the same non-blocking launcher health error, especially while the recommended repair command is running.

- Root Cause: The standalone host launcher selected .odylith/bin/odylith whenever that file existed, without preferring the recovery-capable .odylith/bin/odylith-bootstrap. A stale main launcher therefore failed before the Claude hook command could run.

- Solution: Prefer the repo-local bootstrap launcher when present in both live and bundled .agents/bin/odylith-host-launcher.py; keep main-launcher fallback for older installs that do not have bootstrap.

- Rollback/Forward Fix: Forward-fix in v0.1.13; do not weaken launcher trust checks.

- Verification: pytest -q tests/unit/install/test_host_worktree_launcher.py tests/unit/install/test_codex_project_assets.py::test_live_agents_bin_matches_bundle_mirror_content

- Prevention: Keep live and bundled host-launcher assets byte-identical and preserve explicit tests for bootstrap-first hook dispatch plus main-only fallback.

- Regression Tests Added: tests/unit/install/test_host_worktree_launcher.py now covers bootstrap preference when both launchers exist and main fallback when bootstrap is absent.

- Monitoring Updates: Watch Claude transcripts for repeated UserPromptSubmit, PreToolUse, and Stop hook errors containing unhealthy runtime state during bootstrap doctor repair.

- Version/Build: Observed on v0.1.12; fix target v0.1.13.

- Config/Flags: Default Claude project hook configuration; no bypass flags.

- Customer Comms: For affected v0.1.12 sessions, the bootstrap doctor command can still repair the install, but hook noise during repair is a product bug fixed in v0.1.13.

- Related Incidents/Bugs: CB-137 trust-warning noise is adjacent but separate; this bug covers host hook launcher dispatch during repair.

- Fixed In: v0.1.13

- Code References: - .agents/bin/odylith-host-launcher.py
- src/odylith/bundle/assets/project-root/.agents/bin/odylith-host-launcher.py
- tests/unit/install/test_host_worktree_launcher.py
