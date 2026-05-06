- Bug ID: CB-171

- Status: FixedPendingRelease

- Created: 2026-05-06

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Radar refresh can render over stale traceability release projection

- Impact: Operators can see fresh Radar HTML while downstream traceability, Compass, and release projections read stale release membership. This splits governed source truth from generated topology and makes release filters look corrupted after migrations or target-release edits.

- Components Affected: radar

- Environment(s): Odylith product repo branch 2026/freedom/v0.1.15 during v0.1.15 release-target correction.

- Detected By: Maintainer release-projection integrity audit after correcting release-assignment-events.v1.jsonl.

- Failure Signature: odylith/radar/source/releases/release-assignment-events.v1.jsonl restored prior release targets, but odylith/radar/traceability-graph.v1.json still reported the old 32-target release projection; odylith sync --impact-mode selective odylith/radar/source/releases/release-assignment-events.v1.jsonl skipped as not relevant.

- Trigger Path: odylith/radar/source/releases/release-assignment-events.v1.jsonl

- Ownership: Radar sync planner and traceability graph freshness guard.

- Timeline: Observed during v0.1.15 release assignment repair: source event log fixed; Radar refresh ran; traceability graph still contained stale release-0-1-15 membership; selective sync over the release event log skipped; manual traceability build corrected the projection.

- Blast Radius: Radar release filters, Compass release cards, topology graph consumers, and migrations that rely on generated traceability after release assignment changes.

- SLO/SLA Impact: Governance surface correctness: fresh rendered UI can disagree with generated release topology until a manual traceability build runs.

- Data Risk: No application data loss, but durable governance projection can preserve stale release membership and mislead operators.

- Security/Compliance: No security exposure identified; integrity failure affects governed memory and operator decision quality.

- Invariant Violated: A generated governance surface must not be considered fresh unless every generated dependency it embeds is derived from current source truth.

- Root Cause: Selective sync did not include odylith/radar/source/releases/ in the sync-relevant Radar source prefix set, and Radar rendering consumed the existing traceability graph without proving it matched the current release/program/backlog source fingerprint.

- Solution: Treat release event logs as Radar sync inputs, stamp traceability graphs with a content-backed source fingerprint, and make Radar refresh rebuild the traceability graph before render whenever source truth changes.

- Verification: PYTHONPATH=src pytest tests/unit/runtime/test_traceability_freshness.py tests/unit/runtime/test_sync_cli_compat.py::test_release_assignment_events_are_sync_relevant_and_refresh_traceability tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_validates_radar_for_backlog_only_selective_slice tests/unit/runtime/test_sync_cli_compat.py::test_dashboard_refresh_skips_component_spec_sync_for_shell_facing_refresh -q

- Prevention: Keep release event logs in the Radar sync prefix set and require traceability source fingerprints before Radar render reads traceability-graph.v1.json.

- Regression Tests Added: tests/unit/runtime/test_traceability_freshness.py::test_traceability_freshness_rebuilds_when_release_events_change; tests/unit/runtime/test_sync_cli_compat.py::test_release_assignment_events_are_sync_relevant_and_refresh_traceability

- Fixed In: 0.1.15
