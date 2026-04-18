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

## Review Questions
- Does this change reduce a real duplication or boundary problem, or did it
  just move code into another file?
- Is the new helper owned by a stable contract that more than one caller
  should share?
- Did the change remove filler comments and replace them with truthful
  documentation?
- Would the next maintainer be able to find the owner and the proof path
  without rediscovering them from scratch?
