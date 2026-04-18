# Odylith Code Hygiene Guard

Use this skill when a slice shows duplicate helper churn, fake modularization,
oversized-file pressure, mirrored host drift, or comment slop. Treat AI slop
as a regression.

## Default Flow
- Read the nearest `AGENTS.md`, then read
  `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` before editing.
- Inventory the current owner, call sites, shared helpers, validators, and
  file sizes before changing structure.
- Consolidate generic coercion and normalization helpers into a real shared
  owner instead of adding one more local wrapper.
- If a touched hand-maintained source file is already above `1200` LOC,
  choose decomposition or carry an explicit active decomposition plan before
  adding more growth.
- Update inline documentation only for invariants, failure modes, boundary
  assumptions, or non-obvious state transitions.
- Add or update enforcement tests so the cleanup stays pinned in CI.

## Hard Bans
- `def _host()` plus a wall of rebound private host symbols is banned.
- Do not duplicate generic coercion helpers such as `_mapping`,
  `_json_dict`, `_normalize_*`, `_delta`, or `_parts` across files when one
  shared owner is appropriate.
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
