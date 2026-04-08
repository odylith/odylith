- Bug ID: CB-050

- Status: Closed

- Created: 2026-04-03

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: After the explicit Compass refresh path was moved off
  `shell-safe` and onto `full`, `odylith dashboard refresh --repo-root .
  --surfaces compass` could fan into live scoped standup narration during the
  synchronous render. That made refresh materially slower, and if the operator
  interrupted the run or the live provider leg failed to finish, Compass kept
  showing the previous deterministic local brief with the old
  `provider_deferred` banner. Timeline Audit also stayed pinned to the prior
  runtime snapshot because the runtime payload is not written until the
  standup-brief stage finishes. A follow-up on 2026-04-05 exposed the inverse
  failure too: after bounding scoped refresh again, full refresh could finish
  cleanly but still leave every selected workstream on deterministic local
  narration because scoped provider refresh stayed hard-disabled. A second
  follow-up on 2026-04-05 exposed a voice-layer regression on top of the
  freshness fix: even when briefs were current, both global and scoped Compass
  briefs could still read robotic because the provider contract and the
  deterministic fallback were teaching the same stock lead-ins. A third
  follow-up on 2026-04-07 exposed the remaining wrapper inconsistency in a
  downstream repo: the default dashboard path intentionally rendered the
  bounded `shell-safe` brief, but the advertised
  `--compass-refresh-profile full` path still inherited the same 45-second
  dashboard timeout, failed twice under a realistic repo state, printed the
  wrong recovery hint (`odylith compass update --repo-root .`), and left the
  prior `shell-safe` payload active with no explicit surface-level indication
  that the requested deeper refresh never landed.

- Impact: Operators ask for refresh because they want Compass to become more
  trustworthy, not slower and more confusing. A slow refresh erodes shell UX,
  and an interrupted refresh can leave the old deterministic brief visible with
  no clear surface-level indication that the attempted live refresh never
  completed. The same interrupted render can also leave Timeline Audit pinned
  to older events such as the visible `14:00` block even though the operator
  just asked for a refresh. On 2026-04-07 that ambiguity widened into a direct
  state-integrity problem: the operator explicitly asked for `full`, the
  wrapper timed out in both runtime-backed and standalone retries, but Compass
  kept serving the prior `shell-safe` snapshot and `provider_deferred` banner
  as if that were the current truthful outcome.

- Components Affected: `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/surfaces/render_compass_dashboard.py`, Compass standup
  refresh contract, shell-facing refresh UX.

- Environment(s): Consumer shell lane, pinned dogfood maintainer proof lane,
  and detached `source-local` maintainer-dev lane when using explicit
  `odylith dashboard refresh --surfaces compass`.

- Root Cause: The explicit refresh contract oscillated between two bad
  extremes. First, `full` refresh attempted live scoped narration serially in
  the same render path as the global brief, which made the shell command slow
  enough that interrupted runs could leave the previous deterministic artifact
  in place. Then the corrective gate disabled scoped provider refresh entirely,
  so completed full refreshes still left selected workstreams on
  deterministic-local briefs by construction. Browser proof also lacked stable
  brief source/fingerprint metadata, so it could not assert whether scope and
  window changes were actually loading distinct live briefs. On top of that,
  the brief-writing layer itself had drifted into a house style: the provider
  prompt explicitly suggested phrases like `The real center of gravity is` and
  `The boring but important move was`, while the deterministic fallback
  repeated the same phrasing in code. That made a fresh brief still feel stale
  to a human reader. The remaining wrapper bug on 2026-04-07 came from three
  mismatches that were still live after the earlier fixes: the underlying
  Compass renderer still defaulted to `full` even though the public dashboard
  CLI defaulted to `shell-safe`; the dashboard wrapper reused the same
  hard-coded 45-second timeout for both bounded `shell-safe` refresh and
  provider-enabled `full` refresh; and a failed `full` attempt never patched
  the live `current.v1.json` payload to say that the deeper refresh failed, so
  the UI simply kept showing the stale prior snapshot and its normal
  `provider_deferred` notice.

- Solution: Keep `shell-safe` bounded, but let full refresh rebuild scoped
  workstream briefs too so selected workstreams stop landing on deterministic
  local narration after a completed refresh. Do that with a small worker pool
  instead of a fully serial provider walk, and publish brief
  source/window/scope/fingerprint metadata into the Compass DOM so browser
  proof can assert real brief selection instead of inferring it from prose.
  Then harden the voice contract itself: bump the brief schema to `v13`,
  invalidate the old warmed cache, rewrite both provider and deterministic
  paths toward plainer spoken narrative, and reject repeated stock lead-ins at
  validation time so the live payload cannot slide back into canned prose. For
  the remaining wrapper inconsistency, align the underlying renderer default
  with `shell-safe`, give explicit `full` refresh a materially larger dashboard
  timeout budget than bounded shell-safe refresh, replace the bogus
  `compass update` recovery hint with a real rerender command, and write an
  explicit failure marker into the live Compass payload whenever a requested
  full refresh times out or otherwise fails so the shell cannot silently keep
  serving the old `shell-safe` snapshot without admitting that deeper refresh
  failed.

- Verification: `python -m pytest -q
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/unit/runtime/test_compass_standup_brief_narrator.py
  tests/unit/runtime/test_render_compass_dashboard.py` passed with `62 passed`.
  `python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py
  tests/integration/runtime/test_surface_browser_deep.py` passed with
  `26 passed, 1 skipped`. `env PYTHONPATH=src python -m
  odylith.runtime.surfaces.render_compass_dashboard --repo-root .
  --refresh-profile full` completed in `96.20s`, and the regenerated
  `current.v1.json` now shows provider or warmed-cache scoped briefs with no
  deterministic banner notice for sampled workstreams including `B-027`,
  `B-033`, and `B-021`. The follow-up voice hardening also passed
  `python -m pytest tests/unit/runtime/test_compass_standup_brief_deterministic.py tests/unit/runtime/test_compass_standup_brief_narrator.py -q`
  with `42 passed` and
  `python -m pytest tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_compass_dashboard.py tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py -q`
  with `52 passed`, and the rerendered Compass runtime now carries brief schema
  `v13`. A final closure pass should also prove the wrapper contract directly:
  focused unit coverage for the Compass dashboard refresh timeout and retry
  hint path, plus focused runtime-payload coverage proving that a failed full
  refresh marks the live Compass payload as stale-and-failed instead of leaving
  a silent `provider_deferred` shell-safe artifact in place. That closure proof
  now passed on 2026-04-08: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_compass_dashboard_runtime.py` completed with
  `54 passed`, `python3 -m py_compile
  src/odylith/runtime/governance/dashboard_refresh_contract.py
  src/odylith/runtime/governance/sync_workstream_artifacts.py
  src/odylith/runtime/surfaces/render_compass_dashboard.py
  src/odylith/runtime/surfaces/compass_dashboard_runtime.py
  src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py
  src/odylith/runtime/surfaces/render_backlog_ui.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_sync_cli_compat.py` passed, and `git diff --check`
  stayed clean on the touched Compass refresh files.

- Prevention: Explicit refresh should mean “rebuild current truth,” not
  “silently defer to stale artifacts,” but it also must not explode into
  sequential scoped narration work inside one synchronous shell refresh.

- Detected By: User report and screenshot on 2026-04-03 showing a slow Compass
  refresh attempt followed by the old deterministic local brief banner and
  `Generated Apr 03, 2026, 14:34` still visible.

- Failure Signature: `odylith dashboard refresh --repo-root . --surfaces
  compass` takes materially longer than the old bounded refresh, and Compass
  can still show `Showing deterministic local brief` from the prior artifact if
  the attempted full refresh does not finish. Timeline Audit likewise stays on
  the prior runtime snapshot instead of advancing to newer events. In the
  2026-04-07 downstream repro, explicit `--compass-refresh-profile full` timed
  out in runtime-backed and standalone fallback mode, printed
  `next: odylith compass update --repo-root .`, and left
  `runtime_contract.refresh_profile = shell-safe` in `current.v1.json`.

- Trigger Path: Run `odylith dashboard refresh --repo-root . --surfaces
  compass` after moving the explicit refresh contract onto `--refresh-profile
  full`, then interrupt the render or inspect the shell before the live
  narrator leg completes.

- Ownership: Compass refresh contract, shell-facing refresh UX, standup brief
  narration layering.

- Timeline: On 2026-04-03, explicit refresh was moved off `shell-safe` so a
  user-requested refresh would not automatically defer into a deterministic
  brief. That surfaced a second bug immediately: the synchronous refresh path
  became slow enough to be user-visible, and a canceled run left the prior
  deterministic artifact in place. On 2026-04-05, follow-up fixes restored
  scoped provider warming and voice quality. On 2026-04-07, downstream proof in
  `/Users/freedom/code/dentoai-orion` showed the wrapper still treated bounded
  and deep refresh as if they shared the same timeout and failure posture, so
  the deeper `full` path remained operator-misleading even though the default
  bounded path stayed healthy.

- Blast Radius: Every lane that relies on the explicit Compass refresh command
  for a trustworthy shell update.

- SLO/SLA Impact: No hard outage, but a direct shell UX and operator-trust
  regression on a core Compass action.

- Data Risk: Low source-truth risk; medium operator-decision risk because a
  failed or interrupted refresh can leave the previous deterministic brief in
  place while the operator thinks a live refresh already happened.

- Security/Compliance: None directly.

- Invariant Violated: Explicit Compass refresh must stay reasonably bounded and
  must not leave the operator believing a live refresh succeeded when the old
  deterministic brief artifact is still being served.

- Workaround: Use the old bounded shell-safe path only for internal debugging,
  or wait for the live refresh to complete fully before trusting the standup
  brief. Neither is a good default shell contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not widen a shell-facing refresh command into
  per-workstream live narration unless the refresh surface exposes that extra
  cost and completion state clearly.

- Preflight Checks: Inspect `CB-047`, `CB-019`, the active B-025 plan, the
  explicit refresh command path in `sync_workstream_artifacts.py`, and the
  scoped brief gate in `compass_runtime_payload_runtime.py`.

- Regression Tests Added: Focused unit coverage locks full refresh to allow
  scoped provider warming while `shell-safe` still defers it, and headless
  browser coverage now asserts Compass brief source and fingerprint changes
  across global versus scoped selection and `24h` versus `48h` window changes.
  Additional narrator coverage now rejects overused stock openings so provider
  output cannot validate if it falls back into the old house phrases.

- Monitoring Updates: Watch Compass full-refresh latency, whether selected
  workstreams come back provider- or cache-backed after refresh, and whether
  any deterministic or `provider_deferred` notice survives on a completed
  full-refresh artifact.

- Residual Risk: Full refresh is still materially slower than shell-safe
  refresh because scoped provider warming remains the long pole. The worker
  pool keeps it under control, but this still leaves a product decision about
  whether deeper scoped warming should eventually move off the synchronous
  render path. Voice quality is now guarded against the known stock phrases,
  but future prompt or fallback changes can still regress toward flattened
  prose if they optimize for structure without preserving human rhythm. Even
  after the wrapper fix, explicit `full` refresh remains the more expensive
  path by design, so future work should still watch whether deeper scoped
  warming belongs in the synchronous dashboard refresh at all or should move to
  a more explicit background proof path.

- Related Incidents/Bugs:
  [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md)
  [2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md](2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md)

- Version/Build: Odylith product repo working tree on 2026-04-03.

- Config/Flags: Explicit Compass dashboard refresh, `--refresh-profile full`,
  global live narration, bounded scoped narration.

- Customer Comms: Tell operators that explicit Compass refresh is being split
  into “refresh truth now” versus “deep scoped narration cost” so the shell
  refresh remains trustworthy and responsive.

- Code References: `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `tests/unit/runtime/test_sync_cli_compat.py`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`,
  `tests/unit/runtime/test_render_compass_dashboard.py`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
