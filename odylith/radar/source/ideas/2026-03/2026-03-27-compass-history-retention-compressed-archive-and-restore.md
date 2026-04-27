status: finished

idea_id: B-003

title: Compass History Retention, Compressed Archive, and Restore

date: 2026-03-27

priority: P0

commercial_value: 4

product_impact: 5

market_value: 3

impacted_parts: compass runtime history retention, compressed archive storage, restore command surface, and runtime history metadata

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Compass history should stay lightweight by default without discarding operational evidence; the product needs a simple active-window-plus-archive model before larger customer repos accumulate months of runtime history.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-27-compass-history-retention-compressed-archive-and-restore.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-001

workstream_blocks:

related_diagram_ids:

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Compass currently keeps a 30-day active history window and hard-deletes older
daily snapshots. That keeps the active surface bounded, but it throws away
runtime evidence and makes it impossible to restore older dates into Compass
without external backups.

## Customer
- Primary: Odylith maintainers and operators using Compass as the local audit
  and standup history surface.
- Secondary: installed Odylith repos that need a predictable, low-friction
  retention model without losing older operational evidence.

## Opportunity
By separating active Compass history from cold archived history, Odylith can
keep the default UI light while preserving older runtime snapshots in a
restorable compressed format.

## Proposed Solution
Keep only the most recent 15 days active in `odylith/compass/runtime/history/`,
compress older daily snapshots into an archive lane, and add an explicit
restore command that rehydrates selected dates back into active Compass history.

### Wave 1: Active window and compressed archive
- change the Compass default active retention window from 30 days to 15 days
- archive older `YYYY-MM-DD.v1.json` snapshots into compressed `.json.gz`
  artifacts under `odylith/compass/runtime/history/archive/`
- stop hard-deleting older snapshots during normal Compass refreshes

### Wave 2: Restore contract and runtime metadata
- add a supported `odylith compass restore-history --date YYYY-MM-DD` command
- persist restored-date pins so explicitly restored older dates remain
  available across later syncs instead of being immediately re-archived
- expose archive and restore metadata in Compass runtime history payloads

### Wave 3: Validation and surface contract hardening
- add focused unit coverage for archive, retention, and restore behavior
- update Compass component docs and runtime guidance to describe the new
  active-vs-archived history model
- refresh generated Compass runtime artifacts in the product repo to the new
  default contract

## Scope
- Compass runtime history retention defaults
- compressed archive storage for older daily snapshots
- restore command surface and restore-pin metadata
- Compass runtime history index/current payload metadata
- focused Compass tests and docs

## Non-Goals
- making archived dates automatically browseable in the Compass calendar
  without an explicit restore action
- redesigning Compass to stream history on demand from a remote service
- changing the append-only event stream contract

## Risks
- restored dates can bloat the active embedded history bundle if too many are
  rehydrated at once
- archive or restore metadata can drift if compression and index refresh are
  not kept in one runtime path
- CLI restore can feel unreliable if older dates are restored but then
  immediately re-pruned on the next sync

## Dependencies
- `B-001` supplies the current public Odylith Compass runtime roots and product
  command surface that this retention/restore model extends
- the existing Compass runtime writer and shell history loader are reused
  rather than replaced

## Success Metrics
- default Compass refresh keeps only the last 15 days active
- older retained daily snapshots are compressed into a deterministic archive
  path instead of being discarded
- `odylith compass restore-history --date YYYY-MM-DD` restores an archived day
  into active Compass history and keeps it available across later syncs
- Compass runtime metadata clearly reports active retention and archived/restore
  state

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_update_compass.py tests/unit/test_cli.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_validate_plan_workstream_binding.py`
- `odylith sync --repo-root .`

## Rollout
Land the new active-window and archive behavior first, then expose explicit
restore as the supported path for bringing older days back into the Compass
calendar.

## Why Now
Compass already accumulates materially sized daily runtime snapshots. The next
default should preserve older evidence without letting the active local-file
payload keep growing indefinitely.

## Product View
The smoothest UX is simple: keep a short active window fast, archive the rest
cheaply, and make restore explicit and deterministic instead of silently
deleting useful history or forcing people to manage snapshots by hand.

## Impacted Components
- `compass`
- `odylith`

## Interface Changes
- Compass runtime history defaults to 15 active days instead of 30
- older daily snapshots move into `odylith/compass/runtime/history/archive/*.v1.json.gz`
- Compass adds `odylith compass restore-history --date YYYY-MM-DD` for explicit restore
- history metadata now reports archive and restored-date state

## Migration/Compatibility
- existing active Compass history files remain valid
- older active daily snapshots are archived on the next render instead of being deleted
- archive browsing remains explicit through restore rather than changing the calendar to auto-load cold history

## Test Strategy
- add focused runtime tests for archive compression and restore-pin retention
- update Compass update-flow tests to assert the new default retention
- extend CLI tests for the new restore-history command surface
- rerun full Odylith sync so generated surfaces and runtime metadata match the new contract

## Open Questions
- should Compass later expose archived-date discovery in the UI, or keep restore purely CLI-driven
- should a future follow-on add an explicit unpin command for restored older dates
