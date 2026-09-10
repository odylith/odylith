- Bug ID: CB-212

- Related Rendered-Date Evidence (2026-09-09): The fresh Greenfield Radar audit displays Created Date and Index Updated as 2026-09-08 while the unchanged authored date and index source are 2026-09-09. Its payload distinguishes idea_date=2026-09-09 from idea_date_display=2026-09-08. This is a separate date-only presentation path, not recurrence of the repaired source normalizer. Preserve the evidence and investigate calendar-date versus timestamp ownership before changing formatting. No date correction is claimed by the authored-preview refactor. Evidence: /private/tmp/odylith-radar-authored-proof.cEUc92/readback-3/screenshots/desktop-radar-authored-reading.png and the copied source/payload; the sealed original remains unchanged.

- Status: Open

- Created: 2026-07-01

- Severity: P2

- Reproducibility: Always

- Type: Tooling

- Description: Operational risk: governed Radar freshness metadata can regress at a local/UTC day boundary even when the UTC day has advanced. Delivery risk: release proof and checkpoint commits can carry misleading freshness evidence unless the normalizer derives UTC-labeled fields from UTC time.

- Impact: Operational and delivery risk: Radar source truth can show a stale or regressed UTC date during governed sync, reducing trust in generated governance freshness.

- Components Affected: radar

- Environment(s): Odylith maintainer lane during source-local governed sync after release proof logging.

- Detected By: Diff review after odylith sync --force changed odylith/radar/source/INDEX.md from Last updated (UTC): 2026-07-01 to 2026-06-30 while date -u reported 2026-07-01.

- Failure Signature: Last updated (UTC) header derived from local date instead of UTC date.

- Trigger Path: odylith sync --repo-root . --force --registry-policy-mode enforce-critical --enforce-deep-skills

- Ownership: Radar legacy backlog normalization and governed sync.

- Timeline: Captured 2026-07-01 through `odylith bug capture`.

- Blast Radius: Radar source index, Radar rendered surfaces, traceability freshness signals, and bundled governance surface mirrors.

- SLO/SLA Impact: Delivery-risk impact: release proof and checkpoint commits can carry false freshness regressions near day boundaries.

- Data Risk: No governed records lost; metadata freshness can be misleading until regenerated with a UTC-derived date.

- Security/Compliance: No security exposure identified; compliance posture depends on truthful audit metadata.

- Invariant Violated: A field labeled UTC must be derived from UTC time, not local calendar date.

- Root Cause: normalize_legacy_backlog_index defaulted to dt.date.today() while _update_last_updated rendered the value as Last updated (UTC).

- Solution: Default legacy backlog normalization to datetime.now(UTC).date() while preserving explicit today injection for tests and deterministic callers.

- Verification: tests/unit/runtime/test_legacy_backlog_normalization.py passes; sync --check-only passes; Radar header now remains Last updated (UTC): 2026-07-01 when date -u is 2026-07-01.

- Prevention: Keep UTC-labeled generated metadata on UTC clocks and add focused tests for local/UTC day-boundary behavior.

- Regression Tests Added: tests/unit/runtime/test_legacy_backlog_normalization.py::test_normalize_legacy_backlog_index_defaults_last_updated_to_utc_date

- Code References: - src/odylith/runtime/governance/legacy_backlog_normalization.py
- tests/unit/runtime/test_legacy_backlog_normalization.py
