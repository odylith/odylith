- Bug ID: CB-150

- Type: Product








- Status: FixedPendingRelease

- Created: 2026-05-01

- Severity: P1

- Reproducibility: High


- Description: Casebook renders prose status and type chips

- Impact: Casebook cards can display long prose labels in Status, Fixed, or Type chips, which violates the product contract that these fields are always short compact labels and makes cards harder to scan.

- Components Affected: casebook

- Environment(s): Odylith Casebook dashboard during v0.1.13 branch work; screenshots from 2026-05-01 and 2026-05-02 showed long Status, Fixed, and Type labels.

- Detected By: Operator screenshot and explicit feedback that Casebook status, fixed, and asset type must always be short one-word labels.

- Failure Signature: Casebook detail cards show visible values like 'Mitigated locally; pending platform release...', 'Pending release/deploy', or 'OSW template upgrade repair / coroutine scheduler runtime / LocalStack proof UX' instead of compact labels such as Mitigated, Pending, or UX.

- Trigger Path: Open Casebook and inspect a bug card whose source or projection contains prose Status or Type metadata.

- Ownership: casebook renderer, Casebook source validation, bug capture, context-engine Casebook projection

- Timeline: Captured 2026-05-01 through `odylith bug capture`.

- Blast Radius: All Casebook readers and any host model that relies on Casebook chips for quick bug triage.

- SLO/SLA Impact: Triage readability and governed metadata consistency degrade; no service availability impact.

- Data Risk: Low data risk; medium governed-truth quality risk because prose metadata can leak into search/filter/display contracts.

- Security/Compliance: No direct security exposure.

- Invariant Violated: Casebook Status, Fixed, and Type must be short compact labels in source truth, projection payloads, and visible chips.

- Root Cause: Casebook validation only enforced Reproducibility compactness originally, and the first Status/Type hardening still left the optional Fixed field and some legacy Type display fallbacks able to reach the detail-card renderer as prose.

- Solution: Added shared Casebook metadata canonicalization, fail-closed Status/Type/Fixed source validation, bug capture Type rejection, projection normalization for Status, Fixed, and Type, compact visible Intel chips, checked-in source normalization, sync normalization, and the registered v0.1.13 Casebook compact-metadata migration.

- Rollback/Forward Fix: Forward fix in v0.1.13; do not restore prose Status, Fixed, or Type labels in generated Casebook surfaces.

- Verification: PYTHONPATH=src pytest -q tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/test_cli.py tests/unit/runtime/test_casebook_bug_index.py -q; focused install migration tests cover doctor and upgrade backfilling legacy Casebook records; odylith casebook validate --repo-root .; rg found no visible Intel count chip or prose Status/Type metadata. 2026-05-02 follow-up proof: `./.odylith/bin/odylith casebook validate --repo-root .` (`151 records`), `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_render_casebook_dashboard.py` (`37 passed`), `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_casebook_list_layout_browser.py` (`5 passed`), and `./.odylith/bin/odylith release migration-gate --repo-root . --target-version 0.1.13 --json` (`ok: true`). 2026-05-02 migration hardening proof: `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_casebook_metadata_migration.py tests/unit/install/test_migration_runtime.py` (`47 passed`), including 0.1.10 -> 0.1.13, 0.1.11 -> 0.1.13, and 0.1.12 -> 0.1.13 Casebook compact-label migration coverage.

- Prevention: Keep source validation and renderer tests covering compact Status, Fixed, and Type tokens plus visible chip labels.

- Regression Tests Added: tests/unit/runtime/test_casebook_source_validation.py; tests/unit/runtime/test_render_casebook_dashboard.py; tests/unit/test_cli.py; tests/unit/runtime/test_casebook_bug_index.py; tests/unit/install/test_casebook_metadata_migration.py; tests/unit/install/test_migration_runtime.py; tests/integration/runtime/test_casebook_sort_browser.py; tests/integration/runtime/test_casebook_list_layout_browser.py
- Migration Compatibility: Legacy consumer Casebook records without compact Status, Fixed, or Type labels must not break `doctor --repair`, same-version runtime repair, or 0.1.10/0.1.11/0.1.12 -> 0.1.13 upgrade. The registered v0.1.13 migration normalizes source labels, rebuilds the index, rerenders Casebook browser payloads, and writes a migration ledger before the upgrade is considered complete.

- Related Incidents/Bugs: B-141; operator screenshot 2026-05-01

- Code References: - src/odylith/runtime/common/casebook_metadata.py
- src/odylith/runtime/governance/casebook_source_validation.py
- src/odylith/runtime/governance/sync_casebook_bug_index.py
- src/odylith/runtime/surfaces/render_casebook_dashboard.py
- src/odylith/install/casebook_metadata_migration.py
- src/odylith/install/migration_runtime.py
