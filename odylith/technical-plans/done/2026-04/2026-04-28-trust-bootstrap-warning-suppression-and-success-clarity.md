Status: Done
Created: 2026-04-28
Updated: 2026-04-28
Backlog: B-056

# Trust Bootstrap Warning Suppression And Success Clarity

## Goal
Close the stale `B-056` release-polish workstream by reconciling the already
landed trust-warning suppression behavior with its Radar and Casebook records,
then pin the missing regression proof for calm success output and visible
runtime trust-warning posture.

## Decisions
- Treat this as a reconciliation closeout, not a new broad trust subsystem.
- Keep Sigstore/TUF warning suppression narrow: only allowlisted non-fatal
  warning streams are suppressed, and only after verification succeeds.
- Preserve unexpected verifier stderr and fatal verification failures in full.
- Keep broader upgrade transaction auditability under `CB-133`, not `B-056`.
- Surface non-fatal runtime trust warnings through `doctor` and `version` as
  classified posture information with severity and `verification_degraded`
  detail.

## Related Records
- Backlog: B-056.
- Parent workstream: B-048.
- Bugs: CB-061, CB-076.
- Related follow-up: CB-133.
- Target release: 0.1.12.

## Must-Ship
- [x] Mark `B-056` finished and explain the installed trust-warning behavior.
- [x] Update `CB-076` from pending integration to 0.1.12 closeout evidence.
- [x] Add regression coverage for the calm success notice detail.
- [x] Add regression coverage for `version` surfacing non-fatal runtime trust
      warning posture.
- [x] Refresh Radar and Casebook rendered surfaces.

## Non-Goals
- Do not broaden the trust-warning allowlist.
- Do not change artifact verification policy.
- Do not fold upgrade lifecycle audit reports into this narrow trust-warning
  closeout.

## Impacted Areas
- [x] [test_release_assets.py](/Users/freedom/code/odylith/tests/unit/install/test_release_assets.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [2026-04-06-odylith-trust-bootstrap-warning-suppression-and-success-clarity.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-06-odylith-trust-bootstrap-warning-suppression-and-success-clarity.md)
- [x] [2026-04-08-successful-pinned-runtime-verification-still-prints-scary-trusted-root-key-warning-noise.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-08-successful-pinned-runtime-verification-still-prints-scary-trusted-root-key-warning-noise.md)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_release_assets.py tests/unit/install/test_release_bootstrap.py tests/unit/test_cli.py` passed with 194 tests.
- [x] `python3 -m py_compile tests/unit/install/test_release_assets.py tests/unit/test_cli.py` passed.
- [x] `./.odylith/bin/odylith casebook validate --repo-root .` passed with
      134 records checked.
- [x] `./.odylith/bin/odylith validate backlog-contract --repo-root .` passed
      with 127 ideas checked.
- [x] `./.odylith/bin/odylith validate plan-workstream-binding --repo-root .`,
      `./.odylith/bin/odylith validate plan-traceability --repo-root .`, and
      `./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .`
      passed.
- [x] `git diff --check` passed.

## Closure
- Closed on 2026-04-28 after source truth, rendered Radar/Casebook surfaces,
  and focused regression tests agreed that scary successful-verification trust
  noise is suppressed or classified without hiding real verification failures.
