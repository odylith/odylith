# Odylith Code Hygiene Guard

Use this skill when a slice shows duplicate helper churn, fake modularization,
oversized-file pressure, mirrored host drift, or comment slop. Treat AI slop
as a regression.

## Default Flow
- Read the nearest `AGENTS.md`, then read
  `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` before editing.
- Inventory the current owner, call sites, shared helpers, validators, and
  file sizes before changing structure.
- Inventory the bounded slop signals explicitly before editing:
  remaining `def _host()` shims, duplicate `_mapping` or `_normalize_*`
  helpers, near-identical host mirrors, local alias walls that hide the real
  owner, phase-mixed giant functions, and touched files already above the repo
  size thresholds.
- Consolidate generic coercion and normalization helpers into a real shared
  owner instead of adding one more local wrapper.
- If a touched hand-maintained source file is already above `1200` LOC,
  choose decomposition or carry an explicit active decomposition plan before
  adding more growth.
- If a touched function is already above `500` LOC, extract at least one real
  phase owner or data-model seam in the same pass unless the change is purely
  a safety-critical repair.
- Remove the slop class end to end inside the touched slice. Do not stop at a
  halfway state where the shared owner exists but the touched duplicates still
  remain.
- Update inline documentation only for invariants, failure modes, boundary
  assumptions, or non-obvious state transitions.
- Add or update enforcement tests so the cleanup stays pinned in CI.

## Hard Bans
- `def _host()` plus a wall of rebound private host symbols is banned.
- A local alias wall that only renames dozens of helpers without moving the
  ownership boundary is banned.
- Do not duplicate generic coercion helpers such as `_mapping`,
  `_json_dict`, `_normalize_*`, `_delta`, or `_parts` across files when one
  shared owner is appropriate.
- Do not leave giant renderers, payload builders, or routers phase-mixed when
  the touched slice can be split into data prep, view model, and
  template/render stages, or gather, score, and decide stages.
- Do not keep host-mirror files near-identical when a shared helper, shared
  renderer, or shared formatter would remove the duplication.
- Do not add filler comments or docstrings.
- New or materially rewritten runtime Python modules must carry a truthful
  module docstring.

## Required Proof
- Every anti-slop cleanup must add or update enforcement tests.
- Run the focused regression suite for the touched slice.
- If the change updates guidance, skills, or shipped mirrors, validate the
  source and bundle copies in the same change.
- If the change touches shared runtime hot paths, run the full runtime suite.
- If the change touches browser-proved surfaces, run the full headless browser
  matrix.
- If the change touches install, upgrade, repair, launchers, or install-managed
  mirror surfaces, run the install suite and the mirror-content checks.

## Fail-Closed Exit Criteria
- No touched file may still contain `def _host()` or `host = _host()` after
  the cleanup.
- No touched file may keep a newly avoidable `_mapping`, `_normalize_*`,
  `_delta`, or `_parts` clone once the shared owner exists.
- No touched giant function may exit with the same phase-mixed ownership it had
  on entry when the pass is explicitly about structural debt.
- No touched file may replace a removed shim with a new alias wall that still
  hides the owner behind rebinding.
- Do not close the pass on assumption. Fail closed until the proof lane for
  the touched install, runtime, and browser surfaces is green.
