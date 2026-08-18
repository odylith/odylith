- Bug ID: CB-343

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The semantic graph cutover correctly removed responsibility-prose parsing from component authoring, but the replacement public summary ignored the authored responsibility entirely. Component specs retained the literal field while the Registry what_it_is surface collapsed to a generic planned-boundary sentence.

- Impact: Operators lose the component-specific ownership claim in the primary Registry row, reducing component differentiation and making the graph-native authoring path look templated despite explicit source evidence.

- Components Affected: registry

- Environment(s): Detached source-local maintainer worktree on 2026-08-18 during canonical dev-validation shard 16.

- Detected By: test_component_register_refreshes_registry_surface.

- Failure Signature: Expected Registry refresh authoring proof in what_it_is; actual summary contains only generic planned ownership boundary and standard evidence wording.

- Trigger Path: PYTHONPATH=src .venv/bin/python -m pytest -q -x tests/unit/runtime/test_owned_surface_refresh_authoring.py::test_component_register_refreshes_registry_surface

- Ownership: Registry component authoring public-summary projection.

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: All component register calls that provide explicit responsibility without a precompiled Registry row.

- SLO/SLA Impact: Blocks release validation and weakens operator utility of newly registered components.

- Data Risk: The responsibility remains in CURRENT_SPEC.md, but the Registry row loses it, creating cross-surface semantic drift rather than destructive data loss.

- Security/Compliance: No direct privacy exposure. Governance-policy risk is that security or compliance ownership stated in responsibility evidence disappears from the primary Registry summary.

- Invariant Violated: Deleting prose inference must preserve explicit typed or authored facts losslessly; presentation may format responsibility but must not drop or reinterpret it.

- Root Cause: Commit 555f72917 replaced the old regex-based responsibility focus extraction with a label-only focus and left the responsibility parameter unused.

- Solution: Keep label-only boundary focus, append the normalized authored responsibility as explicitly labeled literal presentation, and retain the generic evidence sentence. Do not parse the responsibility for nouns, roles, or ownership.

- Rollback/Forward Fix: Forward fix the lossless presentation boundary; do not restore regex, finite-verb, or domain-term inference.

- Verification: Run component authoring and owned-surface refresh tests, assert no deleted parser imports return, then replay shard 16.

- Prevention: Every mechanism-deletion wave must include positive custody tests proving explicit accepted fields survive every public governed surface.

- Agent Guardrails: Do not infer Registry identity from responsibility prose and do not replace source-specific responsibility with templates. Render the accepted field literally.

- Preflight Checks: Confirm CURRENT_SPEC already renders responsibility literally and inventory all Registry summary assertions before changing copy.

- Regression Tests Added: tests/unit/runtime/test_owned_surface_refresh_authoring.py::test_component_register_refreshes_registry_surface

- Version/Build: Greenfield semantic graph source-local release candidate based on bf982b0e.

- Related Incidents/Bugs: CB-342

- Code References: - src/odylith/runtime/governance/component_authoring.py
- tests/unit/runtime/test_owned_surface_refresh_authoring.py
