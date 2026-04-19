# Anti-Slop And Decomposition

## Purpose
- This guide exists to stop AI-assisted authoring from degrading Odylith's
  source tree.
- Treat AI slop as a regression.
- Do not dismiss it as an aesthetic complaint.
- Use this guide when the slice shows duplicate helper churn, fake
  extractions, mirrored host drift, oversized-file pressure, or comment noise.

## Hard Bans
- Do not ship fake modularization. `def _host()` plus a wall of rebound
  private host symbols is banned.
- Do not replace `_host()` theater with `bind(host)`, `_HOST_BIND_NAMES`,
  generic `bind_*_runtime(globals(), host)` injection, or bind lists padded
  with scratch locals and loop temporaries.
- Do not replace fake modularization with transitional seam sludge. A giant
  function that begins by aliasing a wall of helpers into locals is still
  poor ownership, even if the `_host()` shim is gone.
- Do not duplicate generic coercion helpers such as `_mapping`,
  `_json_dict`, `_normalize_*`, `_delta`, or `_parts` across files when one
  shared owner is appropriate.
- Do not keep host-mirror files near-identical when a shared helper, shared
  renderer, or shared formatter would remove the duplication.
- Do not add filler comments or docstrings. Comments must explain invariants,
  failure modes, boundary assumptions, or non-obvious state transitions.
- Do not hide rule engines inside giant dict accretion, score piles, or
  output builders when a focused data model or phase owner would make the
  contract clearer.
- Do not leave giant renderers, payload builders, or routers phase-mixed when
  they can be split into real owners such as data prep, view model, and
  template/render stages, or gather, score, and decide stages.
- Do not grow a hand-maintained source file past `1200` LOC without an active
  decomposition plan, and do not land feature-only growth in `2000+` LOC
  files unless the change is decomposition work or a safety-critical repair.

## Decomposition Triggers
- If a touched hand-maintained source file is already above `800` LOC, inspect
  extraction pressure, reuse gaps, and helper duplication before adding new
  local glue.
- If a touched hand-maintained source file is already above `1200` LOC,
  refactor-first is the default posture.
- If a touched hand-maintained source file is already above `2000` LOC, only
  decomposition work, characterization tests, or safety-critical repairs are
  acceptable defaults.
- If a touched function is already above `300` LOC, inspect whether it mixes
  distinct phases, data-model shaping, and rendering or decision policy in one
  body.
- If a touched function is already above `500` LOC, extract at least one real
  phase owner or data-model seam in the same pass unless the change is purely
  a safety-critical repair.
- If a touched function is already above `900` LOC, treat it as red-zone
  monolith debt: do not land unrelated feature growth without a same-change
  decomposition cut or an explicit active workstream tied to the slice.
- Split by real ownership boundary, data model, or execution phase. Do not
  create suffix theater such as `_runtime2`, `_helpers_extra`, or extracted
  files that still tunnel back through private host shims.

## Documentation Bar
- New or materially rewritten runtime Python modules must carry a truthful
  module docstring.
- Function, class, or inline documentation should explain invariants, failure
  modes, boundary assumptions, or non-obvious state transitions.
- Delete comments that merely restate syntax, variable assignment, or obvious
  control flow.

## Proof Obligations
- Every anti-slop cleanup must add or update enforcement tests.
- When introducing a shared helper, update the touched duplicates in the same
  slice or leave an explicit bounded follow-up plan.
- When guidance, skills, or bundled docs change, update the shipped mirrors in
  the same change.
- For behavioral refactors, run the focused regression suite for the touched
  slice and widen proof when the change reaches shared hot paths or user-facing
  surfaces.
- If the change touches shared runtime hot paths, run the full runtime suite
  before closeout.
- If the change touches browser-proved UI or shell surfaces, run the full
  headless browser matrix before closeout.
- If the change touches install, upgrade, repair, launcher, bundled project
  assets, or bundle-mirror generation, run the install suite and mirror-content
  checks before closeout.

## Fail-Closed Cleanup Rule
- Do not stop at "better" when the touched slice still contains the same
  bounded class of slop you set out to remove.
- If you touch a shimmed extract, remove the shim or move the ownership
  boundary for real in the same slice.
- If you touch a giant render, payload, router, or decision function, leave it
  with at least one clearer phase boundary than it had on entry.
- If you introduce a shared owner for `_mapping`, `_normalize_*`, `_delta`,
  `_parts`, or similar helpers, update the touched duplicates onto that owner
  before closeout.
- If you remove a fake seam and replace it with an alias wall, the pass is
  still incomplete. Remove the local alias wall or move that logic behind a
  real owner before closeout.
- If a touched change updates guidance or skills that ship through bundle
  mirrors or install-managed assets, refresh those mirrors in the same change
  and prove them with tests instead of assuming they stayed aligned.
- Fail the pass locally when the touched files still contain banned shim or
  duplicate-helper patterns after the refactor. In other words, fail closed
  on unresolved slop in the touched slice.

## Review Questions
- Does this change reduce a real duplication or boundary problem, or did it
  just move code into another file?
- Is the new helper owned by a stable contract that more than one caller
  should share?
- Did the change remove filler comments and replace them with truthful
  documentation?
- Would the next maintainer be able to find the owner and the proof path
  without rediscovering them from scratch?
