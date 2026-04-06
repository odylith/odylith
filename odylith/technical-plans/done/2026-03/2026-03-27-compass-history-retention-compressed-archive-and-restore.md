Status: Done

Created: 2026-03-27

Updated: 2026-03-27

Goal: Change Compass history from 30-day hard-delete retention to a 15-day active window with compressed archived daily snapshots and an explicit restore command that keeps restored dates available across later syncs.

Assumptions:
- Compass daily history snapshots remain local repo-owned runtime artifacts.
- Archived history should be compressed and deterministic, not remote-hosted.
- Restoring older dates should be explicit and durable until the operator removes them from active history.

Constraints:
- Keep the default user experience simple: short active window, automatic compression, explicit restore.
- Do not delete older daily snapshots once archived successfully.
- Preserve the append-only Compass event stream contract.

Reversibility: Restored dates are rehydrated from compressed archive files, and the active-retention default is a configuration-level change backed by preserved archived snapshots.

Boundary Conditions:
- Scope includes Compass runtime history retention, archive compression, restore pins, CLI restore support, runtime metadata, and Compass docs/tests.
- Scope excludes remote storage, browser-native archive browsing, or changes to non-Compass surface history policies.

Related Bug Review:
- [x] `no related bug found` in [odylith/casebook/bugs/INDEX.md](/Users/freedom/code/odylith/odylith/casebook/bugs/INDEX.md)

## Context/Problem Statement
- [x] Compass currently defaults to 30 active days and prunes older daily history snapshots outright.
- [x] Archived Compass history is not preserved or restorable in the current product contract.
- [x] The runtime and CLI need one supported restore path that does not immediately lose older restored days on the next sync.

## Success Criteria
- [x] Default Compass retention is 15 active days.
- [x] Older daily snapshots move into a compressed archive under `odylith/compass/runtime/history/archive/`.
- [x] `odylith compass restore-history --date YYYY-MM-DD` restores archived days into active Compass history.
- [x] Restored days survive later syncs because restore pins are honored by the runtime writer.
- [x] Compass runtime metadata reports active retention plus archive/restore state clearly enough for validation and future UI use.

## Non-Goals
- [x] Building a browser UI for archive exploration.
- [x] Introducing remote storage or hosted history retrieval.
- [x] Changing the Compass event-stream append contract.

## Impacted Areas
- [x] [src/odylith/runtime/surfaces/compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [src/odylith/runtime/surfaces/render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [x] [src/odylith/runtime/surfaces/update_compass.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/update_compass.py)
- [x] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [odylith/registry/source/components/compass/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)

## Traceability
### Runbooks
- [x] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)

### Developer Docs
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)

### Runtime Contract
- [x] [odylith/compass/runtime/AGENTS.md](/Users/freedom/code/odylith/odylith/compass/runtime/AGENTS.md)
- [x] [odylith/compass/runtime/history/index.v1.json](/Users/freedom/code/odylith/odylith/compass/runtime/history/index.v1.json)

### Code References
- [x] [src/odylith/runtime/surfaces/compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [src/odylith/runtime/surfaces/render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [x] [src/odylith/runtime/surfaces/update_compass.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/update_compass.py)
- [x] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)

## Risks & Mitigations

- [x] Risk: restored dates get pruned again on the next sync and the restore UX feels broken.
  - [x] Mitigation: persist explicit restore pins and rehydrate pinned archived dates before retention pruning.
- [x] Risk: compressed archive silently diverges from active history metadata.
  - [x] Mitigation: keep compression, archive scanning, index refresh, and embedded-history rebuild inside the same writer path.
- [x] Risk: too many restored dates inflate the active embedded history payload.
  - [x] Mitigation: keep the default active window at 15 days and make older restores explicit and targeted by date.

## Validation/Test Plan
- [x] `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_update_compass.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_validate_plan_workstream_binding.py`
- [x] `PYTHONPATH=src ./.venv/bin/python -m odylith sync --repo-root .`

## Rollout/Communication
- [x] Ship the runtime and CLI contract together.
- [x] Refresh generated Compass runtime artifacts in the public product repo.
- [x] Keep archive browsing as a later follow-on rather than extending the UI in the same slice.

## Dependencies/Preconditions
- [x] Keep workstream `B-003` bound in Radar and this active plan index.

## Edge Cases
- [x] Restore is requested for a date that is missing from the archive.
- [x] A restored date is older than the active retention window but must remain active across later syncs.
- [x] Archive compression is attempted for a malformed or partial daily snapshot.

## Open Questions/Decisions
- [x] Decision: active Compass retention defaults to 15 days.
- [x] Decision: older daily snapshots move to compressed local archive rather than being deleted.
- [x] Decision: restore is explicit through CLI, not implicit browser archive loading.

## Follow-on
- [x] Future archive discovery or unpin UX remains a separate follow-on rather than blocking the completed retention/archive/restore contract.

## Current Outcome
- [x] Compass runtime history now defaults to 15 active days through the shared
  renderer/update contract.
- [x] Older daily history snapshots are compressed into
  `odylith/compass/runtime/history/archive/*.v1.json.gz` instead of being
  deleted.
- [x] `odylith compass restore-history --date YYYY-MM-DD` now restores archived
  daily snapshots, writes restore pins, and keeps restored dates active across
  later syncs.
- [x] Focused Compass runtime, update-flow, CLI, and governance validation
  coverage landed and passed.
