# Fail-Closed Code Hygiene

Use this maintainer-only skill when a pass is explicitly about removing AI
slop, fake modularization, duplicate helper churn, mirror drift, oversized-file
pressure, or other structural debt in shipped Odylith code.
Treat AI slop as a regression.

## Read First
- Read the nearest `AGENTS.md`.
- Read `../../agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`.
- Read `../agents-guidelines/CODING_STANDARDS.md`.

## Required Workflow
- Inventory the bounded slop in the touched slice before editing:
  - remaining `def _host()` or `host = _host()` shims
  - duplicate `_mapping`, `_normalize_*`, `_delta`, `_parts`, or similar
    helper clones
  - host-mirror files that should share a helper or formatter
  - touched hand-maintained source files already above the repo size limits
  - install-managed mirror surfaces that will need sync
- Record the before-state in concrete terms before you edit:
  line counts for any touched `1200+` / `2000+` files, the exact helper or
  mirror clones you plan to remove, and the proof surface you will rerun.
- Pick a real owner. Move shared coercion, normalization, or rendering logic
  into a stable owner instead of adding another wrapper layer.
- When you touch a shimmed extract, remove the shim in the same pass.
- When you create a shared owner, update the touched duplicates onto it before
  closeout.
- When you touch a red-zone source file, leave it with a smaller or cleaner
  owned boundary than you found. Do not use a hygiene pass to sneak in net new
  unrelated growth.
- When guidance, hooks, skills, or bundle-managed assets change, update the
  live source and every shipped mirror in the same change.
- Add inline documentation only for invariants, failure modes, boundary
  assumptions, or non-obvious state transitions.
- Add or update enforcement tests that pin the cleaned-up class of slop.

## Hard Bans
- `def _host()` plus a wall of rebound private host symbols is banned.
- Do not duplicate generic coercion helpers such as `_mapping`,
  `_json_dict`, `_normalize_*`, `_delta`, or `_parts` across files when one
  shared owner is appropriate.
- New or materially rewritten runtime Python modules must carry a truthful
  module docstring.
- Every anti-slop cleanup must add or update enforcement tests.

## Fail-Closed Exit Criteria
- No touched file may still contain `def _host()` or `host = _host()`.
- No touched file may keep an avoidable generic helper clone once the shared
  owner exists.
- No touched host-mirror pair may still keep avoidable shared control flow in
  both files once a real shared owner exists.
- Any touched red-zone file must exit with a clearer owned seam than it had on
  entry; if not, the pass is incomplete.
- Do not stop on "improved" when the same bounded slop class is still present
  in the touched slice. Fail closed on unresolved slop in the touched slice.
- Do not claim non-regression without proof.

## Required Proof
- Run focused regression tests for the touched slice.
- Run `tests/unit/runtime` when the change touches shared runtime hot paths.
- Run `tests/unit/install` when the change touches install, upgrade, repair,
  launchers, hooks, skills, or install-managed mirrors.
- Run the headless browser matrix when the change touches browser-proved UI or
  shell surfaces.
