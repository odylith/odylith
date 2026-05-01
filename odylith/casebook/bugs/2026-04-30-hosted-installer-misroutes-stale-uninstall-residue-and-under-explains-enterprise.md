- Bug ID: CB-146

- Type: InstallRelease


- Status: FixedPendingRelease

- Created: 2026-04-30

- Severity: P1

- Reproducibility: Always


- Description: Hosted installer misroutes stale uninstall residue and under-explains enterprise fetch failures

- Impact: Fresh reinstall after old uninstall residue, or rerunning the hosted installer against an already-current repo with stale migration state, can fail with a scary upgrade/migration dump or Python traceback instead of completing install; release asset download failures behind VPN, proxy, firewall, or TLS inspection lack concise recovery guidance.

- Components Affected: release

- Environment(s): 0.1.12 local-release rehearsal and enterprise hosted installs; consumer repo has .odylith residue but the odylith governed tree is missing or incomplete.

- Detected By: Maintainer manual dentoai-isb local install transcript and focused stale-residue release rehearsal.

- Failure Signature: upgrade plan ... scenario: stale_migration_ledger ... blocked_reason: repo pin is missing or invalid ... customer Odylith starter tree missing; run odylith install --repo-root . or odylith doctor --repo-root . --repair. A later sharper repro crashed during compact install with `ValueError: migration ledger exists, but value-engine verification no longer passes`. A same-version rerun then showed the restored ASCII banner but still routed a complete-looking existing install through `upgrade`, dumping the full blocked migration plan before printing the same stale-ledger reason.

- Trigger Path: Run the generated install.sh after a prior uninstall or partial cleanup leaves .odylith/install.json, .odylith/runtime/current, or .odylith/state/migrations/* but removes or omits odylith/AGENTS.md, product-version truth, or the value-engine corpus written by the migration.

- Ownership: Hosted release bootstrap, managed release asset download lifecycle, and legacy safe-upgrade launcher.

- Timeline: Captured 2026-04-30 through `odylith bug capture`.

- Blast Radius: Fresh reinstall, local release rehearsal, legacy safe-upgrade recovery, and enterprise operators behind proxy, TLS inspection, VPN, firewall, or filtered GitHub/odylith.ai access.

- SLO/SLA Impact: P1 adoption and recovery regression: first-run bootstrap can fail before the dashboard or agent workflow is usable, and operators see internal upgrade diagnostics instead of install progress.

- Data Risk: Medium: governed truth can appear missing and stale runtime state can steer recovery into the wrong lane; no application data exfiltration is involved.

- Security/Compliance: Medium: public installs must remain HTTPS and signed by default; localhost HTTP must be maintainer-only opt-in, and proxy/TLS diagnostics must never print secret environment values.

- Invariant Violated: Incomplete install residue must be completed through install or repair, not upgrade; release fetch failures must stay secure, concise, and actionable across enterprise network controls.

- Root Cause: The generated install.sh treated .odylith/install.json alone as proof of a complete existing install, and the stale-residue repair path cleared old install/current pointers without clearing stale migration ledgers that claimed missing governed artifacts had already been written. After that partial fix, a complete already-current install still took the upgrade-planner path, and the value-engine migration treated a valid ledger plus missing Odylith-owned corpus as a hard stale-ledger block instead of a repairable owned-artifact drift. Separately, curl/Python release fetch failures surfaced raw transport errors without enough enterprise proxy/TLS/firewall context.

- Solution: Route only complete installs (pin, install state, and customer starter tree) to upgrade when the target is not already active; same-version hosted install uses compact install repair instead of invoking the upgrade planner. Compact-install stale residue clears stale install.json/current and stale .odylith/state/migrations ledgers when the customer tree is incomplete. The value-engine migration now repairs valid ledgers whose owned corpus is missing, while malformed ledgers still block as corruption. Keep normal release assets HTTPS-only; require ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST=1 only for local maintainer HTTP rehearsal; add concise proxy/TLS/firewall hints to generated curl fetches, managed Python downloads, and legacy safe-upgrade launcher fetches; catch compact install failures without dumping Python tracebacks.

- Rollback/Forward Fix: Forward-fix in 0.1.12; no public localhost UX change beyond the maintainer-only opt-in flag.

- Verification: Focused unit tests passed for generated install routing/fetch behavior, managed Python release downloads, launcher text, stale migration ledger residue, and compact failure reporting; integration uninstall/install lifecycle tests passed; local stale-residue hosted-asset rehearsal showed the restored ASCII banner, compact install progress, active 0.1.12 posture, restored value-engine corpus, and restored odylith/AGENTS.md without an upgrade-plan dump or traceback. On 2026-04-30, `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_release_bootstrap.py tests/unit/install/test_release_assets.py tests/unit/install/test_migration_runtime.py tests/unit/test_cli.py::test_hosted_first_install_uses_compact_progress_labels tests/unit/test_cli.py::test_compact_install_reports_failure_without_traceback tests/unit/test_cli.py::test_compact_existing_install_surface_failure_hides_sync_internals tests/integration/install/test_manager.py::test_uninstall_bundle_detaches_and_preserves_customer_odylith_tree tests/integration/install/test_manager.py::test_uninstall_bundle_retries_late_state_writes_from_active_hooks tests/integration/install/test_manager.py::test_install_and_uninstall_preserve_existing_customer_truth_tree tests/integration/install/test_manager.py::test_uninstall_bundle_preserves_symlinked_odylith_without_following_target tests/integration/install/test_manager.py::test_uninstall_bundle_unlinks_symlinked_state_root_without_following_target` passed with 131 tests. `PYTHONPATH=src python3 -m odylith.cli release migration-gate --repo-root . --target-version 0.1.12 --json` passed with no blocked manual migrations after B-140 carried the final public-docs, browser-surface, and install-managed-asset migration-observer markers.

- Prevention: Keep stale uninstall residue and enterprise release-fetch diagnostics in the local release smoke matrix and unit-test the generated install script instead of relying on manual shell inspection.

- Agent Guardrails: Do not frame localhost rehearsal as the product install path. Product install guidance stays curl over HTTPS to odylith.ai; localhost HTTP is maintainer-only proof plumbing.

- Preflight Checks: Before release, run generated installer unit tests, managed release asset tests, local release smoke including stale residue, and install/uninstall lifecycle tests.

- Regression Tests Added: tests/unit/install/test_release_bootstrap.py covers complete-vs-stale install routing, already-current compact repair routing, stale migration ledger cleanup, localhost opt-in, non-local HTTP rejection, and enterprise curl hints; tests/unit/install/test_migration_runtime.py covers valid-ledger missing-corpus repair while keeping malformed ledgers blocked; tests/unit/install/test_release_assets.py covers Python downloader enterprise hints without secret values; tests/unit/test_cli.py covers compact install failure reporting without traceback; scripts/release/local_release_smoke.py covers stale uninstall and stale migration ledger residue.

- Version/Build: v0.1.12 release candidate

- Config/Flags: Default hosted install uses HTTPS and signed release assets; ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST=1 is maintainer-only for local release testing.

- Customer Comms: Tell operators the normal install remains curl -fsSL https://odylith.ai/install.sh | bash; proxy/TLS/firewall failures now produce concise recovery hints without printing proxy secrets.

- Related Incidents/Bugs: Related to CB-012, CB-136, and CB-143.

- GitHub Issue(s): [odylith/odylith#22](https://github.com/odylith/odylith/issues/22)

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.12

- Code References: - scripts/release/publish_release_assets.py
- src/odylith/install/release_assets.py
- src/odylith/install/runtime.py
- scripts/release/local_release_smoke.py
- tests/unit/install/test_release_bootstrap.py
- tests/unit/install/test_release_assets.py
