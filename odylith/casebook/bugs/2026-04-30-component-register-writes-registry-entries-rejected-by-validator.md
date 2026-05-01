- Bug ID: CB-141

- Type: Product


- Status: FixedPendingRelease

- Created: 2026-04-30

- Severity: P1

- Reproducibility: High


- Description: Component register writes Registry entries rejected by validator

- Impact: Operators can register components in a fresh consumer repo, but the next sync rejects the generated Registry source and the browser remains on stale empty delivery intelligence.

- Components Affected: registry

- Environment(s): Odylith 0.1.11 pinned consumer runtime after first install in dentoai-isb on macOS Apple Silicon.

- Detected By: User-provided Claude transcript from /Users/freedom/code/dentoai-isb after component register and sync.

- Failure Signature: component register hardcoded category detected and qualification detected, then sync failed at Registry contract validation because valid categories are data/governance_engine/governance_surface/control_gate/infrastructure and valid qualifications are candidate/curated.

- Trigger Path: Run odylith component register for dentoai-isb components, then run odylith sync --repo-root . --proceed-with-overlap --force --impact-mode full.

- Ownership: Registry component authoring CLI and Registry contract validation.

- Timeline: 2026-04-29: user registered dentoai-isb components through the CLI; registry refresh still showed zero components; full sync failed at Registry validation due invalid category and qualification values. 2026-04-30: follow-up Claude recovery guidance made the operator experience worse by recommending a hand edit of `odylith/registry/source/component_registry.v1.json`, calling it a CLI-first override, and incorrectly claiming `doctor --repair` could not help.

- Blast Radius: All Odylith 0.1.11 hosted installs received the affected component authoring writer. The break manifests when an operator uses `odylith component register`; after that, Registry validation can reject the generated source and browser Registry remains empty or stale.

- SLO/SLA Impact: P1 onboarding and governance authoring degradation; no application runtime outage.

- Data Risk: No observed data loss; generated governance source becomes invalid until repaired.

- Security/Compliance: No direct security or compliance impact observed.

- Invariant Violated: A governed CLI writer must only emit Registry source that its own validator accepts.

- Workaround: Upgrade to a fixed Odylith release and run `./.odylith/bin/odylith doctor --repo-root . --repair`; it repairs the known 0.1.11 component-register metadata drift and missing spec Feature History before the next sync. Do not advise a consumer operator to hand-edit `odylith/registry/source/component_registry.v1.json` for this known drift.

- Root Cause: Released 0.1.11 component_authoring hardcoded category and qualification to detected, while the Registry validator only accepts the canonical category and qualification enums; current regression coverage also verifies the scaffolded spec has Feature History so the emitted entry validates end to end.

- Solution: Component authoring emits category governance_engine and qualification candidate, scaffolds a Feature History entry, and the register regression now validates the emitted Registry source immediately. `doctor --repair` also includes a consumer-repo migration for already-installed 0.1.11 repos that rewrites the known `detected` taxonomy drift and backfills missing component spec Feature History.

- Rollback/Forward Fix: Forward fix in component authoring and tests; avoid relaxing Registry validator enums.

- Verification: PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_owned_surface_refresh_authoring.py::test_component_register_refreshes_registry_surface passed. PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_consumer_registry_repair.py tests/integration/install/test_manager.py::test_doctor_bundle_repair_fixes_0_1_11_component_register_drift passed.

- Prevention: Keep component register output under validator coverage so authoring CLI, spec scaffold, and Registry contract enums cannot drift. Keep recovery guidance under hygiene coverage so agents say "upgrade, then doctor repair" for this known drift instead of suggesting JSON edits.

- Agent Guardrails: If component register output fails Registry validation in a consumer repo, diagnose Odylith product drift; do not tell the operator the browser is empty because their app has no components, do not claim `doctor --repair` cannot help for this 0.1.12 repair lane, and do not recommend hand-editing the Registry manifest as a CLI-first override.

- Preflight Checks: Run component register in a temp repo and validate Registry source before releasing component authoring changes.

- Regression Tests Added: tests/unit/runtime/test_owned_surface_refresh_authoring.py::test_component_register_refreshes_registry_surface now runs validate_component_registry_contract against component register output. tests/unit/install/test_consumer_registry_repair.py and tests/integration/install/test_manager.py::test_doctor_bundle_repair_fixes_0_1_11_component_register_drift cover existing 0.1.11 consumer install repair.

- Monitoring Updates: Watch support transcripts for component register followed by Registry validation failure or registry dashboard component count remaining zero.

- Version/Build: Observed in Odylith 0.1.11 pinned consumer runtime; fixed pending release on v0.1.12 branch.

- Config/Flags: Default component register and sync; no category flag exists in 0.1.11.

- Customer Comms: Tell affected operators this is an Odylith writer/validator drift, not their repo. After upgrading to the fixed release, run `./.odylith/bin/odylith doctor --repo-root . --repair`, then rerun the sync/render command.

- Related Incidents/Bugs: Related to CB-139 and CB-140 as first-run trust failures.

- Code References: - src/odylith/runtime/governance/component_authoring.py
- src/odylith/install/consumer_registry_repair.py
- src/odylith/install/manager.py
- tests/unit/runtime/test_owned_surface_refresh_authoring.py
- tests/unit/install/test_consumer_registry_repair.py
- tests/integration/install/test_manager.py
