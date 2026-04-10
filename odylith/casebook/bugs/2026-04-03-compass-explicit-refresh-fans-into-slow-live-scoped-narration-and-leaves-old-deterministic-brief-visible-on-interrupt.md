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
  Then harden the voice contract itself: bump the brief schema again to
  invalidate warmed cache entries when the narration contract tightens, rewrite
  both provider and deterministic paths toward plainer spoken narrative, reject
  repeated stock lead-ins plus canned status wrappers at validation time, and
  revalidate warmed cache entries before reuse so the live payload cannot slide
  back into canned prose. For the remaining wrapper inconsistency, align the underlying renderer default
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
  `v14`. A final closure pass should also prove the wrapper contract directly:
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
  Shell-safe prevention now has two stricter guardrails: first, keep live
  provider spend bounded to the global windows unless explicit deep refresh is
  requested; second, persist narrative-relevant window fingerprints so a hot
  refresh reuses the last validated live brief layer instead of repaying
  deterministic scoped work or another provider turn when the story has not
  materially changed.

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
  a consumer repo showed the wrapper still treated bounded
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
- Agent Guardrails: Treat stock framing in Compass as a correctness regression,
  not a polish nit. Do not ship or reuse provider, deterministic, or cached
  briefs that restate queue labels, generic attention wrappers, sloganized
  self-host status, or canned next-step scaffolding in place of real operator
  judgment.
- Agent Guardrails: Compass brief voice is plainspoken grounded maintainer
  narration. Reject stagey metaphors like `pressure point`, `center of
  gravity`, `muddy`, or `top lane`, reject dashboard-polished abstractions
  like `window coverage spans`, and reject rhythmic summary prose even when
  the facts themselves are current.

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
- Monitoring Updates: Also watch for stock-framing regressions in the live
  brief text itself; a factually current brief that slips back into house
  phrases is still a failed Compass artifact.
- Monitoring Updates: Also watch for drift back into stagey or dashboard-wise
  language. A brief that says `pressure point`, `muddy`, or `window coverage
  spans` has already failed the Compass voice contract even if the facts are
  correct.
- Monitoring Updates: Keep watching the bounded default path itself. Shell-safe
  should stay global-live and scoped-cheap, and refresh status should expose
  dead-worker truth plus phase detail instead of collapsing the whole runtime
  build into one opaque `projection/memory` stall.
- Monitoring Updates: Also watch the source facts that feed the narrator.
  Whole-window coverage and plan-fed next actions are part of the same voice
  contract; if those upstream facts slip back into checklist fragments or
  canned wrappers, provider narration will regress even when the model prompt
  stays unchanged.

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
  a more explicit background proof path. On 2026-04-09, the bounded default
  path was recut again around deterministic precomputed timeline inputs and a
  cheap-fast narration lane (`gpt-5.3-codex-spark` with low reasoning for
  simple brief work). Source-local proof dropped to `0.78s` warm wall-clock
  with `0.2s` internal runtime work and about `1.63s` on a tmpdir cold
  shell-safe render, which means the remaining gap is now cold-start/runtime
  bootstrap rather than wide provider fan-out. The same day also exposed one
  more replay hole: warmed `v20` runtime-snapshot prose could survive a
  stricter voice validator if the snapshot itself stayed in the same brief
  epoch. The forward fix bumped the brief cache epoch again to `v21` and
  locked runtime-snapshot reuse behind the current validator so older stocked
  wording cannot leak back through snapshot reuse. A second follow-on then
  cleaned the upstream fact text itself: whole-window coverage dropped the old
  `A lot moved in this window` wrapper, B-021 next-action source text stopped
  feeding raw checklist fragments into Compass, and shell-safe source-local
  proof returned both `24h` and `48h` globals provider-backed again at
  `27.29s` wall-clock. That restored live narration quality, but the default
  path is still far above the product budget because `window facts prepared`
  remains the long pole at about `10.8s`.
  Later on 2026-04-09, another regression showed that even after the budget
  cuts landed, the deterministic floor could still flatten live narration back
  into stock wrappers like `A lot happened`, `moving with it too`, and
  `Compass already proved the cost of local heuristics.` The forward fix
  bumped the brief epoch again to `v22`, recut the deterministic rewrites to
  use plain fact-anchored prose, and updated governed guidance so any test
  that blesses canned Compass fallback wording is itself treated as stale
  product contract. The same follow-on also closed the old minute-scale
  refresh lane permanently and re-stated the only acceptable Compass runtime
  lanes: hot exact-reuse under `50ms` of internal runtime work and complete
  cold shell-safe refresh under `1s` of internal runtime work. Source-local
  proof after that cut showed a hot reused runtime at `0.2s` internal work
  with about `1.19s` launcher wall-clock, and a cold bounded rebuild at
  `0.8s` internal work with about `1.20s` launcher wall-clock, which pins the
  remaining miss on startup overhead rather than narration logic.
  Another follow-on the same day then fixed the remaining default-path voice
  regression: shell-safe globals were still falling back to deterministic most
  of the time because global cache recovery only accepted exact current-packet
  cache, the v22 validator rejected older narrated caches on pre-v22 stock
  wording, and cached fact ids died whenever the packet regenerated ids. The
  forward fix taught global cache reuse to carry forward the maintained
  narrated layer, remap cached fact ids through stored evidence lookup when
  only packet-local ids changed, and rewrite old whole-window coverage
  summary bullets into the current plainer wording before validation. After a
  one-time cheap structured global seed, source-local shell-safe refresh wrote
  both global windows back as `cache exact` with no fresh provider call on the
  bounded path, and `standup briefs built` stayed under `0.1s`.

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

- Fix Commit/PR: `2026/freedom/v0.1.10` Compass closeout series.
