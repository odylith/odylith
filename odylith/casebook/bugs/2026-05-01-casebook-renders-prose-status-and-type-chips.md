- Bug ID: CB-150

- Type: Product


- Status: Open

- Created: 2026-05-01

- Severity: P1

- Reproducibility: High


- Description: Casebook renders prose status and type chips

- Impact: Casebook cards can display long prose labels in Status or Type/asset chips, which violates the product contract that these fields are always single compact words and makes cards harder to scan.

- Components Affected: casebook

- Environment(s): Odylith Casebook dashboard during v0.1.13 branch work; screenshot from 2026-05-01 showed a long Status chip and an Intel count chip.

- Detected By: Operator screenshot and explicit feedback that Casebook status and asset type must always be a single word.

- Failure Signature: Casebook card shows a visible chip like 'Mitigated locally; pending platform release, shared Kafka preview/deploy, OSW upgrade, publish, and wave retry' instead of a compact token such as Mitigated.

- Trigger Path: Open Casebook and inspect a bug card whose source or projection contains prose Status or Type metadata.

- Ownership: casebook renderer, Casebook source validation, bug capture, context-engine Casebook projection

- Timeline: Captured 2026-05-01 through `odylith bug capture`.

- Blast Radius: All Casebook readers and any host model that relies on Casebook chips for quick bug triage.

- SLO/SLA Impact: Triage readability and governed metadata consistency degrade; no service availability impact.

- Data Risk: Low data risk; medium governed-truth quality risk because prose metadata can leak into search/filter/display contracts.

- Security/Compliance: No direct security exposure.

- Invariant Violated: Casebook Status and Type must be one compact single-word token in source truth, projection payloads, and visible chips.

- Root Cause: Casebook validation only enforced Reproducibility compactness, while Status and Type values flowed through source, index, projection, and dashboard rendering without the same token contract.

- Solution: Added shared Casebook metadata canonicalization, fail-closed Status/Type source validation, bug capture Type rejection, projection normalization, compact visible Intel chips, checked-in source normalization, and legacy sync migration that backfills missing Type as Product while compacting prose Status values during repair/upgrade.

- Rollback/Forward Fix: Forward fix in v0.1.13; do not restore prose Status or Type labels in generated Casebook surfaces.

- Verification: PYTHONPATH=src pytest -q tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/test_cli.py tests/unit/runtime/test_casebook_bug_index.py -q; focused install migration tests cover doctor and upgrade backfilling legacy Casebook records; odylith casebook validate --repo-root .; rg found no visible Intel count chip or prose Status/Type metadata.

- Prevention: Keep source validation and renderer tests covering compact Status/Type tokens and visible chip labels.

- Regression Tests Added: tests/unit/runtime/test_casebook_source_validation.py; tests/unit/runtime/test_render_casebook_dashboard.py; tests/unit/test_cli.py
- Migration Compatibility: Legacy consumer Casebook records without Type must not break `doctor --repair` or same-version/runtime upgrade. The sync migration backfills Type before strict source validation so the single-word contract hardens without stranding older repos.

- Related Incidents/Bugs: B-141; operator screenshot 2026-05-01

- Code References: - src/odylith/runtime/common/casebook_metadata.py
- src/odylith/runtime/governance/casebook_source_validation.py
- src/odylith/runtime/governance/sync_casebook_bug_index.py
- src/odylith/runtime/surfaces/render_casebook_dashboard.py
