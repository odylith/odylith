- Bug ID: CB-110

- Status: Closed

- Created: 2026-04-14

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Forwarded CLI help hides backend flags, `odylith bug capture`
  can corrupt multiline Casebook index rows by line-patching `INDEX.md`, and
  selective sync stays too wide for governed memory-only edits.

- Impact: Routine Casebook and plan memory upkeep could take minutes instead of
  seconds because operators had to inspect source to discover the real `bug
  capture` flags, a new bug capture could splice a fresh Casebook row into the
  middle of an existing multiline components cell, and then a narrow
  bug/plan/spec refresh still widened into a broad sync graph with Atlas,
  delivery-intelligence, and shell-facing render churn that the change did not
  need.

- Components Affected: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/bug_authoring.py`,
  `src/odylith/runtime/governance/sync_casebook_bug_index.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `tests/unit/test_cli.py`,
  `tests/unit/runtime/test_sync_cli_compat.py`, and governed-sync operator
  contract under `B-091`.

- Environment(s): Product-repo maintainer mode and downstream repos using
  forwarded CLI subcommands or explicit selective sync with governed
  memory-only changed paths.

- Root Cause: The top-level CLI registered shim parsers for forwarded commands
  like `bug capture` and `compass log`, but `--help` resolved against the shim
  instead of the backend parser. `bug capture` also maintained its own
  line-oriented `INDEX.md` inserter even though Odylith already had a canonical
  Casebook-index rebuild path from markdown source, so multiline table rows
  remained structurally unsafe. Separately, write-mode selective sync always
  built the broader governance/render plan even when the explicit changed-path
  slice only touched Casebook bug markdown, technical plans, and Registry
  living-spec docs.

- Solution: Forward `--help` for `odylith bug capture` and `odylith compass
  log` directly into the backend parsers, make `bug capture` rebuild
  `odylith/casebook/bugs/INDEX.md` from markdown source instead of line-patching
  the existing table, and add a truth-only selective sync lane that validates
  the touched plan slice, refreshes Casebook index state, mirrors the touched
  source-truth docs, and skips Atlas, delivery-intelligence, and dashboard
  renders for explicit governed memory-only edits.

- Verification: `pytest -q tests/unit/test_cli.py::test_bug_capture_help_forwards_backend_flags
  tests/unit/test_cli.py::test_compass_log_help_forwards_backend_flags
  tests/unit/test_cli.py::test_bug_capture_rebuilds_multiline_casebook_index_from_source
  tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_uses_truth_only_selective_lane_for_governance_memory_slice
  tests/unit/runtime/test_casebook_bug_index.py
  tests/unit/runtime/test_odylith_memory_areas.py::test_load_bug_projection_handles_multiline_open_bug_rows`
  and `pytest -q tests/unit/runtime/test_sync_cli_compat.py::test_sync_changed_source_truth_bundle_mirrors_updates_changed_docs
  tests/unit/runtime/test_sync_cli_compat.py::test_sync_changed_source_truth_bundle_mirrors_updates_runtime_source_corpus
  tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_appends_source_bundle_mirror_step
  tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_runs_final_registry_reconcile_after_bundle_mirror
  tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_final_registry_reconcile_triggers_delivery_stabilization`
  both passed on 2026-04-14.

- Prevention: Forwarded CLI shims must treat backend help as part of the public
  contract, and selective sync must preserve a truth-only lane for explicit
  governed memory records instead of treating every narrow record update as a
  shell-facing render wave.

- Detected By: Real maintainer bug/plan/spec memory upkeep on 2026-04-14.

- Failure Signature: `odylith bug capture --help` only exposing `--repo-root`,
  `odylith compass log --help` hiding required flags like `--kind` and
  `--summary`, a freshly captured Casebook bug row landing inside an existing
  multiline components cell in `odylith/casebook/bugs/INDEX.md`, and a
  three-path selective sync for bug/plan/spec memory edits still planning
  Atlas, delivery-intelligence, or shell-facing render work.

- Trigger Path: `odylith bug capture`, `odylith compass log`, and
  `odylith sync --impact-mode selective <bug.md> <plan.md> <CURRENT_SPEC.md>`.

- Ownership: CLI forwarding contract and governed sync operator contract.

- Timeline: Captured 2026-04-14 through `odylith bug capture`.

- Blast Radius: Casebook capture ergonomics, Compass timeline logging
  discoverability, governed memory upkeep latency, and operator trust in the
  selective sync contract.

- SLO/SLA Impact: Medium operator-latency and confidence impact on a common
  maintenance path.

- Data Risk: Low.

- Security/Compliance: No direct security impact; the narrowed sync lane
  reduces unnecessary write breadth for routine governed memory updates.

- Invariant Violated: Public forwarded subcommands must expose their real help
  surface, and explicit selective governed-memory edits must not widen into the
  full render-heavy sync graph.
