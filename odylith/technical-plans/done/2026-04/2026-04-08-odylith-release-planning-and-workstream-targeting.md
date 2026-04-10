Status: Done

Created: 2026-04-08

Updated: 2026-04-08

Backlog: B-063

Goal: Add a repo-generic release-planning layer that gives workstreams one
authoritative active target release, exposes that truth through a dedicated
CLI and grounded read models, while keeping release naming explicit
operator-owned planning truth even when versioned release notes also exist.

Assumptions:
- `release_id` is immutable after creation and is the canonical source key.
- `current` and `next` are explicit aliases owned by source truth, not inferred
  from semver, publication time, or sort order.
- One active target release per workstream is the right v1 contract; true
  multi-release work should carry forward through move history or explicit
  child workstreams.
- Read UI for v1 stays in Radar and Compass; write UX stays agent plus CLI.

Constraints:
- Do not collapse release planning into execution-wave program files or generic
  workstream topology metadata.
- Do not keep growing `cli.py`, `validate_backlog_contract.py`,
  `render_backlog_ui.py`, or `compass_runtime_payload_runtime.py` in place
  when focused release modules can hold the new logic.
- Fail closed on ambiguous release selectors, duplicate aliases, and invalid
  lifecycle mutations without allowing adjacent release-note artifacts to
  rename release-planning truth automatically.
- Preserve existing release publication, upgrade spotlight, and release-note
  behavior unless the new planning contract explicitly changes the source of
  truth.

Reversibility: The release-planning layer remains additive. The Radar release
subtree, release CLI, and derived read-model fields can be removed without
rewriting existing workstream topology or publication-lane history.

Boundary Conditions:
- Scope includes new Radar source truth, loader and authoring modules, CLI
  commands, validator integration, traceability graph extensions, Radar and
  Compass read-model updates, Context Engine release resolution, release-note
  alignment, and guidance or skill updates.
- Scope excludes automatic release-note generation, automatic semver
  assignment, and simultaneous active multi-release membership.

Related Bugs:
- no related bug found

## Learnings
- [x] Release planning needs one canonical selector contract shared by CLI,
      grounded packets, and UI filters; natural-language convenience cannot
      introduce a second parsing model.
- [x] Append-only assignment history is necessary if "move to next release"
      should stay auditable instead of silently rewriting membership.
- [x] Release planning needs its own operator-owned name contract; authored
      release notes may share a version, but they must not silently rename the
      planning record.

## Must-Ship
- [x] Add source truth under `odylith/radar/source/releases/` for release
      registry plus append-only assignment history.
- [x] Add dedicated release planning modules for contract loading, selector
      resolution, authoring, and read-model shaping.
- [x] Add `odylith release create|update|list|show|add|remove|move`.
- [x] Extend backlog and sync validation to fail closed on release-planning
      contract errors.
- [x] Extend traceability outputs with release catalog, workstream active
      release, release history, and alias summaries.
- [x] Add Radar release summary cards, release chips, and release filters.
- [x] Add Compass release summary, grouped release-member view, and workstream
      release chips.
- [x] Extend Context Engine entity and query resolution for release selectors.
- [x] Update release component and neighboring governance guidance to describe
      the new planning contract.

## Should-Ship
- [x] Add a small Atlas diagram for the release-planning source flow.
- [x] Add helper text or CLI output that shows why a selector matched or failed
      when release resolution is ambiguous.
- [x] Keep release alias advancement explicit in maintainer release guidance so
      the planning lane and publication lane stay synchronized after ship.

## Defer
- [x] Stretch or candidate secondary release targets stay out of the v1
      contract.
- [x] Editable Radar or Compass release UI controls stay out of scope.
- [x] Automatic backlog splitting when a workstream carries across releases
      stays out of scope.

## Success Criteria
- [x] A workstream resolves to at most one active target release.
- [x] `current release`, `next release`, `release:<id>`, version, tag, and
      unique exact name selectors resolve consistently everywhere.
- [x] Add, remove, and move operations append history instead of silently
      rewriting release truth.
- [x] Active releases reject invalid membership changes for parked, finished,
      or superseded workstreams.
- [x] Versioned releases keep operator-owned names, and blank names fall back
      to version or tag labeling instead of inheriting release-note titles.

## Non-Goals
- [x] Replacing execution-wave programs with release planning.
- [x] Making release planning the source of truth for semver publication.
- [x] Allowing active multi-release membership in v1.

## Open Questions
- [x] No B-063-scoped open question remains. Any future stretch-release
      contract can grow as a separate additive planning layer.

## Impacted Areas
- [x] [2026-04-08-odylith-release-planning-and-workstream-targeting.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-odylith-release-planning-and-workstream-targeting.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/radar/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [releases.v1.json](/Users/freedom/code/odylith/odylith/radar/source/releases/releases.v1.json)
- [x] [release-assignment-events.v1.jsonl](/Users/freedom/code/odylith/odylith/radar/source/releases/release-assignment-events.v1.jsonl)
- [x] [v0.1.11.md](/Users/freedom/code/odylith/odylith/runtime/source/release-notes/v0.1.11.md)
- [x] [odylith-release-planning-and-workstream-targeting.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-release-planning-and-workstream-targeting.mmd)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [release_planning_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/release_planning_contract.py)
- [x] [release_planning_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/release_planning_authoring.py)
- [x] [build_traceability_graph.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/build_traceability_graph.py)
- [x] [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [x] [compass_runtime_payload_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py)
- [x] [odylith_context_engine_projection_surface_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_surface_runtime.py)
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [test_release_planning.py](/Users/freedom/code/odylith/tests/unit/runtime/test_release_planning.py)
- [x] [test_validate_backlog_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_validate_backlog_contract.py)
- [x] [test_build_traceability_graph.py](/Users/freedom/code/odylith/tests/unit/runtime/test_build_traceability_graph.py)
- [x] [test_render_backlog_ui.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_backlog_ui.py)
- [x] [test_compass_dashboard_runtime.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_dashboard_runtime.py)
- [x] [test_context_engine_release_resolution.py](/Users/freedom/code/odylith/tests/unit/runtime/test_context_engine_release_resolution.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_release_planning.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_build_traceability_graph.py`
      (passed)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_context_engine_release_resolution.py`
      (passed)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_render_tooling_dashboard.py`
      (passed)
- [x] `PYTHONPATH=src python3 -m odylith.cli release list --repo-root . --json`
      (passed)
- [x] `PYTHONPATH=src python3 -m odylith.cli release show --repo-root . --json current`
      (passed)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
      (passed)
- [x] `git diff --check`
      (passed)

## Current Outcome
- [x] `B-063` is closed for `v0.1.11`.
- [x] Release planning is now first-class repo truth with immutable
      `release_id`, explicit aliases, append-only assignment history, and one
      active target release per workstream.
- [x] Radar, Compass, Context Engine, traceability, and CLI all resolve the
      same release selectors from one contract instead of inferring release
      scope from prose or maintainer memory.
- [x] The `v0.1.11` closeout slice now has a release note, clean removal
      history for closed workstreams, a dedicated Atlas map for the release
      planning source flow, and an explicit no-auto-rename contract for
      release names.
