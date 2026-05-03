- Bug ID: CB-139

- Type: Product








- Status: FixedPendingRelease

- Created: 2026-04-30

- Severity: P1

- Reproducibility: High


- Description: A first-time hosted install into an existing Git repo activated Odylith 0.1.11 successfully, then attempted to render first-run shell surfaces. The full sync dry-run saw 61 overlapping local worktree entries, mostly freshly seeded Odylith managed guidance/repo truth, crossed the overlap threshold, and blocked. The installer then reported missing radar, atlas, compass, registry, and casebook HTML surfaces, leaving the first-run shell incomplete even though the runtime install succeeded.

- Impact: New operators can complete the hosted install but land without the promised immediately usable local shell dashboards; the first advertised recovery command can still fail on the same overlap gate.

- Components Affected: odylith

- Environment(s): macOS Apple Silicon consumer repo first install, Odylith 0.1.11 hosted installer, existing Git repo without prior Odylith root guidance.

- Detected By: User-provided first-install terminal transcript from 2026-04-29.

- Failure Signature: workstream sync blocked: 61 local worktree entries overlap this write-mode sync plan (threshold 50), followed by missing radar.html, atlas.html, compass.html, registry.html, and casebook.html. A follow-up doctor repair reported completion, but `odylith sync --repo-root . --force --impact-mode full` still blocked on 62 overlapping entries and printed `next: odylith sync --repo-root . --proceed-with-overlap`.

- Trigger Path: curl -fsSL https://odylith.ai/install.sh | bash

- Ownership: Install lifecycle, sync overlap gate, and first-run shell bootstrap contract.

- Timeline: 2026-04-29: user removed prior mock repo, installed Claude Code, entered /Users/freedom/code/dentoai-isb, ran hosted Odylith install, verification succeeded, first-run sync blocked on 61 overlaps, and required shell HTML surfaces remained missing. The user then ran `./.odylith/bin/odylith doctor --repo-root . --repair`, which reported completion, followed by `./.odylith/bin/odylith sync --repo-root . --force --impact-mode full`, which still blocked on 62 overlaps.

- Blast Radius: All Odylith 0.1.11 hosted installs received the affected installer code. The observed break occurs on fresh consumer installs where the bootstrap tree and managed guidance create enough untracked Odylith-owned paths before first-run surface sync, which is the normal first-install shape for many Git repos.

- SLO/SLA Impact: P1 install/onboarding degradation: runtime activation completes, but first-run product activation is not complete and the documented recovery path is misleading unless it uses an explicit overlap acknowledgement.

- Data Risk: No data loss observed; the overlap gate fails closed before writing shell surfaces.

- Security/Compliance: No direct security or compliance impact observed; signed release evidence verification completed successfully before the shell bootstrap failed.

- Invariant Violated: A fresh install must not treat its own just-materialized Odylith bootstrap files as unsafe local overlap in a way that blocks required first-run dashboard generation.

- Workaround: After reviewing that the overlap is expected bootstrap output, the likely recovery is `./.odylith/bin/odylith sync --repo-root . --proceed-with-overlap`; the supplied transcript shows `doctor --repair` and `sync --force --impact-mode full` are not sufficient.

- Root Cause: Provisional: first-run install invokes the normal write-mode sync overlap gate after materializing managed/bootstrap files, so newly created Odylith-owned untracked paths are counted as local dirty overlap rather than install-owned expected writes.

- Solution: First-run install now runs the full shell bootstrap sync with a bounded `--proceed-with-overlap` acknowledgement only when this is a true first install. Rematerialize/reinstall paths keep the normal overlap gate. The installed fallback `index.html` no longer recommends the insufficient `--force --impact-mode full` command and instead points at the explicit overlap acknowledgement after inspection. `doctor --repair` now also notices missing first-run shell surfaces in a real installed tree and runs the same overlap-aware surface bootstrap, so the repair command no longer reports completion while leaving the browser empty.

- Rollback/Forward Fix: Forward fix required; do not weaken general dirty-worktree protection for normal sync, reinstall, or upgrade paths.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py -k 'install or first_run or browser_launch'` passed with 25 tests. `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_show_capabilities.py tests/integration/install/test_manager.py::test_install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle` passed with 24 tests.

- Prevention: Keep install-path regression coverage for the fresh-bootstrap dirty-overlap case and keep the normal large-overlap sync gate covered separately.

- Agent Guardrails: Do not classify this as only output noise; the failing symptom is missing first-run shell artifacts after successful runtime activation.

- Preflight Checks: Before fixing, inspect src/odylith/cli.py first-run bootstrap flow and src/odylith/runtime/governance/sync_workstream_artifacts.py overlap gating behavior.

- Regression Tests Added: `tests/unit/test_cli.py` now asserts first install adds `--proceed-with-overlap` for the full first-run surface sync, rematerialize does not auto-acknowledge overlap, browser open still runs after successful first install, failed first-run render guidance names the overlap-aware recovery path, and `doctor --repair` bootstraps missing first-run surfaces when the installed tree exists. `tests/integration/install/test_manager.py` now asserts the installed placeholder shell points at `--proceed-with-overlap` and does not mention the insufficient `--force --impact-mode full` recovery command.

- Monitoring Updates: Watch hosted install transcripts for 'Odylith runtime install succeeded, but the first-run Odylith shell is incomplete' and sync overlap blocks immediately after first materialization.

- Version/Build: Odylith 0.1.11 hosted install observed on 2026-04-29.

- Config/Flags: Default hosted install; no --source-local or manual sync flags.

- Customer Comms: Tell affected operators to upgrade to 0.1.12 and run `./.odylith/bin/odylith doctor --repo-root . --repair`. If repair still reports missing shell surfaces, then run `./.odylith/bin/odylith sync --repo-root . --proceed-with-overlap` after checking the overlap summary. Do not recommend `sync --force --impact-mode full` for this signature.

- Related Incidents/Bugs: Related but distinct from CB-060, which covered dirty-overlap output verbosity rather than a first-install sync block that leaves shell surfaces missing.

- Code References: - src/odylith/cli.py
- src/odylith/runtime/governance/sync_workstream_artifacts.py

- Runbook References: - odylith/INSTALL_AND_UPGRADE_RUNBOOK.md
