Status: Done

Created: 2026-04-06

Updated: 2026-04-07

Backlog: B-051

Goal: Make `odylith version` and `odylith doctor` tell the same truth about
trust-degraded wrapped-runtime posture so operators do not mistake a runnable
product repo for a release-eligible pinned runtime.

Assumptions:
- The underlying runtime trust and repair behavior is already governed under
  `B-048`; this slice is about posture derivation and operator-facing truth.
- Wrapped-runtime posture should remain healthy enough for diagnosis while
  still marking release eligibility fail-closed.

Constraints:
- Do not invent a new lane model or hide trust degradation behind softer
  wording.
- Keep status derivation grounded in live runtime evidence instead of stale
  install state.

Reversibility: The status-helper and messaging changes are code-level
clarifications. They can be tightened later without migrating repo state.

Boundary Conditions:
- Scope includes runtime-source classification, doctor/version messaging, and
  focused posture proof.
- Scope excludes runtime trust repair logic outside the classification and
  explanation path.

Related Bugs:
- [2026-04-06-doctor-and-version-disagree-on-wrapped-runtime-trust-degradation.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-doctor-and-version-disagree-on-wrapped-runtime-trust-degradation.md)

## Success Criteria
- [x] `odylith version` and `odylith doctor` agree on trust-degraded
      wrapped-runtime posture.
- [x] Product-repo release eligibility stays fail-closed when trust evidence is
      degraded.
- [x] Focused CLI and install-manager proof covers the regression directly.

## Non-Goals
- [x] Introducing new runtime lanes or new operator commands.
- [x] Reworking the broader repair semantics owned by `B-048`.

## Impacted Areas
- [x] [runtime_status.py](/Users/freedom/code/odylith/src/odylith/install/runtime_status.py)
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [2026-04-06-odylith-runtime-posture-reporting-explains-wrapped-runtime-degradation.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-06-odylith-runtime-posture-reporting-explains-wrapped-runtime-degradation.md)

## Traceability
### Status Derivation
- [x] Centralize the trust-degraded wrapped-runtime classification behind the
      shared status helper.

### Operator Messaging
- [x] Make `odylith version` explain trust-degraded wrapped runtime directly.
- [x] Make `odylith doctor` report the aligned healthy-but-trust-degraded
      posture instead of falling through a generic failure path.

### Proof
- [x] Add focused install-manager and CLI regressions for the wrapped-runtime
      disagreement.

## Risks & Mitigations

- [x] Risk: the new wording could imply pinned health even when trust is
  - [ ] Mitigation: TODO (add explicit mitigation).
      degraded.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: keep release eligibility explicitly fail-closed in the
        shared status contract.
- [x] Risk: `doctor` and `version` could drift again if they derive posture
  - [ ] Mitigation: TODO (add explicit mitigation).
      independently.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: route both through the same runtime-status helper.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/integration/install/test_manager.py -k 'trust_degraded_wrapped_runtime or wrapped_runtime_for_product_repo'`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/test_cli.py -k 'trust_degraded_wrapped_runtime_detail or runtime_toolchain_boundary'`
- [x] `git diff --check`

## Rollout/Communication
- [x] Land the shared posture derivation first.
- [x] Align `version` and `doctor` wording in the same slice.
- [x] Close the paired Casebook bug once focused proof is green.

## Current Outcome
- [x] `B-051` is complete and now points at a closed technical plan.
- [x] `odylith version` and `odylith doctor` tell the same wrapped-runtime
      trust story.
- [x] Product-repo release posture stays honest: runnable is no longer confused
      with release-eligible.
