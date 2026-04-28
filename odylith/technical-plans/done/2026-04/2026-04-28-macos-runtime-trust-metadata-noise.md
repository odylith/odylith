Status: Done
Created: 2026-04-28
Updated: 2026-04-28
Backlog: B-049

# macOS Runtime Trust Metadata Noise

## Goal
Close `B-049` by proving that managed-runtime trust ignores only known macOS
metadata noise while continuing to fail closed on real runtime drift.

## Decisions
- Keep the policy in `runtime_tree_policy.py` as the single runtime-tree owner.
- Ignore `.DS_Store` and AppleDouble `._*` entries during trust-tree enumeration.
- Scrub the same explicit metadata entries before managed-runtime health checks
  and feature-pack installation.
- Keep arbitrary dotfiles, symlinks, and unexpected runtime files fatal.
- Do not broaden the policy into a generic hidden-file ignore.

## Related Records
- Backlog: B-049.
- Parent workstream: B-048.
- Casebook: CB-054.
- Related diagrams: D-019, D-020.
- Target release: 0.1.12.

## Must-Ship
- [x] Prove trust manifest generation excludes `.DS_Store` and AppleDouble
      entries.
- [x] Prove managed-runtime integrity remains clean when only macOS metadata
      appears after trust generation.
- [x] Prove unexpected non-allowlisted dotfiles still produce trust drift.
- [x] Reconcile B-049 and CB-054 governance state.

## Non-Goals
- Do not ignore arbitrary OS or editor artifacts.
- Do not change release asset verification or Sigstore policy.
- Do not merge this trust-tree policy with lock/cache residue cleanup.

## Impacted Areas
- [x] [runtime_tree_policy.py](/Users/freedom/code/odylith/src/odylith/install/runtime_tree_policy.py)
- [x] [runtime_integrity.py](/Users/freedom/code/odylith/src/odylith/install/runtime_integrity.py)
- [x] [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [x] [test_runtime_metadata_policy.py](/Users/freedom/code/odylith/tests/unit/install/test_runtime_metadata_policy.py)
- [x] [test_runtime.py](/Users/freedom/code/odylith/tests/unit/install/test_runtime.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_runtime_metadata_policy.py tests/unit/install/test_runtime.py -k 'macos_metadata or unexpected_runtime_dotfiles or generated_python_bytecode or cleanup_runtime_versions_residue'` passed with 7 tests.
- [x] `python3 -m py_compile tests/unit/install/test_runtime_metadata_policy.py` passed.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_runtime.py tests/unit/install/test_runtime_metadata_policy.py` passed with 43 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py -k 'feature_pack or runtime_trust or doctor_bundle or repair or reinstall'` passed with 24 tests and 58 deselected.
- [x] `./.odylith/bin/odylith validate backlog-contract --repo-root .` passed
      with 127 ideas checked.
- [x] `./.odylith/bin/odylith casebook validate --repo-root .` passed with
      134 records checked.
- [x] `./.odylith/bin/odylith validate plan-workstream-binding --repo-root .`
      passed.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py` passed with 53 browser tests.
- [x] `git diff --check` passed.

## Closure
- Closed on 2026-04-28 after runtime metadata handling was centralized,
  policy-scoped to `.DS_Store` and AppleDouble files, and proven against both
  benign macOS noise and non-allowlisted runtime drift.
