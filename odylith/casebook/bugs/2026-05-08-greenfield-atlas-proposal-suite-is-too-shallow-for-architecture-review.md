- Bug ID: CB-182

- Status: FixedPendingRelease

- Created: 2026-05-08

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Greenfield Atlas proposal suite is too shallow for architecture review

- Impact: Greenfield operators get only a thin Atlas view from proposal/create, so the first architecture review misses ownership, state, data, deployment, safety, and observability viewpoints that should be visible before source exists.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo maintainer mode, source-local v0.1.15 greenfield path

- Detected By: Operator feedback on the robot swarm logistics greenfield run requesting deeper architectural diagrams that should be a standout greenfield win.

- Failure Signature: Canonical greenfield scaffolds emitted a two-diagram Atlas set for generic prompts and the robot-swarm profile only specialized those two diagrams instead of producing a multi-view architecture suite.

- Trigger Path: odylith greenfield propose --repo-root . --prompt 'robot swarm logistics app'; odylith greenfield create --repo-root . --prompt 'robot swarm logistics app' --release 0.0.1 --confirm

- Ownership: Domain Intelligence proposal scaffold, robot swarm logistics profile, proposal contract, and Atlas draft topology traceability.

- Timeline: Captured 2026-05-08 through `odylith bug capture`.

- Blast Radius: Fresh empty-repo greenfield proposals and create/apply journeys across Compass, Radar, Registry, and Atlas.

- SLO/SLA Impact: Degrades first-run architecture comprehension and increases follow-up prompting before the first coding lane can start.

- Data Risk: No direct data exposure, but missing data-contract and observability diagrams can hide future telemetry and audit ownership decisions.

- Security/Compliance: Safety-sensitive greenfield domains can under-explain e-stop, geofence, deployment boundary, audit, and hardware-in-the-loop constraints.

- Invariant Violated: Greenfield Atlas drafts should make architecture review materially clearer than prose by default and must carry multi-view topology, ownership, state/data, validation, and operational-risk perspectives.

- Root Cause: The deterministic apply-ready scaffold treated Atlas as a minimal proof surface and only produced system overview plus first-slice flow. The robot swarm logistics profile specialized those two rows instead of owning a domain-specific view suite, so valid proposals still under-delivered the architecture-review value promised by greenfield governance.

- Solution: Expanded the generic apply-ready scaffold to five Atlas views: system overview, first-slice sequence, component ownership map, domain state model, and validation/release topology. Expanded the robot swarm logistics specialization to ten views by adding multi-robot conflict resolution, safety envelope/e-stop, telemetry contract/data flow, cloud/edge/simulation deployment boundaries, and observability/audit loop diagrams. The proposal contract now explicitly calls for a multi-view architecture suite where topology, sequence, ownership, state/data, validation, and operational-risk views clarify the project.

- Verification: `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_greenfield_atlas_contract.py tests/unit/runtime/test_compass_dashboard_shell.py::test_workstream_and_registry_links_stay_cross_surface_and_without_footer_actions tests/integration/runtime/test_surface_browser_smoke.py::test_compass_current_workstreams_excludes_rows_already_represented_in_programs_or_release_targets tests/unit/test_cli.py::test_release_migration_gate_json_reports_registered_runtime tests/unit/test_cli.py::test_greenfield_propose_command_is_provider_free tests/unit/test_cli.py::test_greenfield_create_help_forwards_backend_flags tests/unit/test_cli.py::test_greenfield_apply_help_forwards_backend_flags` (`43 passed`); `odylith release migration-gate --target-version 0.1.15 --json` reported `blocked_manual_migrations=0`; `odylith sync --check-only --impact-mode selective`; `odylith casebook validate`; `git diff --check`; `python -m py_compile src/odylith/runtime/domain_intelligence/proposal_scaffold.py src/odylith/runtime/domain_intelligence/robot_swarm_profile.py src/odylith/runtime/domain_intelligence/proposal_contract.py`.

- Regression Tests Added: `tests/unit/runtime/test_greenfield_atlas_contract.py::test_greenfield_apply_ready_scaffold_has_multi_view_architecture_suite` asserts provider-free generic greenfield proposals produce five traceable architecture views and still pass validation plus Tribunal. `tests/unit/runtime/test_greenfield_atlas_contract.py::test_robot_swarm_greenfield_scaffold_expands_domain_specific_atlas_suite` asserts robot swarm logistics proposals produce ten domain-specific Atlas drafts, including conflict, safety, telemetry, deployment, and audit views.

- Prevention: Keep the default scaffold and domain-specific profiles tested at the canonical proposal-object layer so `greenfield propose --format json` and `greenfield create --confirm` cannot drift back to a thin Atlas set while still passing apply gates.
