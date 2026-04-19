# Fail-Closed Code Hygiene

Use this maintainer-only skill when a pass is explicitly about removing AI
slop, fake modularization, duplicate helper churn, mirror drift, oversized-file
pressure, or other structural debt in shipped Odylith code.
Treat AI slop as a regression.
Apply that bar to any codebase or project surface in this lane: services,
libraries, apps, CLIs, infra glue, scripts, docs, prompts, hooks, templates,
config, and generated assets all count.
No transitional states. Do not replace one slop class with another.

## Read First
- Read the nearest `AGENTS.md`.
- Read `../../agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`.
- Read `../agents-guidelines/CODING_STANDARDS.md`.

## Required Workflow
- Inventory the bounded slop in the touched slice before editing:
  - remaining `def _host()` or `host = _host()` shims
  - duplicate `_mapping`, `_normalize_*`, `_delta`, `_parts`, or similar
    helper clones
  - transitional alias walls that still hide the owner after a fake seam was removed
  - host-mirror files that should share a helper or formatter
  - phase-mixed giant render, payload, router, or score functions
  - touched hand-maintained source files already above the repo size limits
  - install-managed mirror surfaces that will need sync
- Record the before-state in concrete terms before you edit:
  line counts for any touched `1200+` / `2000+` files, the exact helper or
  mirror clones you plan to remove, and the proof surface you will rerun.
- Record the lane and host reach as well: which shared guidance, install-
  generated guidance, Codex assets, Claude assets, shared skills, and shipped
  mirrors must stay aligned if the anti-slop rule changes.
- Record project-surface reach too: source files, hooks, prompts, templates,
  config, docs, generators, and installed assets that may be carrying the
  same slop class under different file extensions.
- Pick a real owner. Move shared coercion, normalization, or rendering logic
  into a stable owner instead of adding another wrapper layer.
- Do not treat a shared helper or kernel as a cleanup ornament. If it lands,
  adopt it in the touched slice or leave a bounded follow-up tied to the same
  slop class.
- Partial shared-kernel adoption is still incomplete. If a shared helper or
  kernel lands, the touched callers must adopt it or the pass is incomplete.
- When you touch a shimmed extract, remove the shim in the same pass.
- When you touch a giant function, extract at least one real phase owner or
  data-model seam in the same pass unless the change is purely a
  safety-critical repair.
- When you create a shared owner, update the touched duplicates onto it before
  closeout.
- Do not call the pass complete just because the first smell disappeared. If
  the replacement smell still exists in the touched slice, the pass is
  incomplete.
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
- A local alias wall that only renames a dense helper cluster without moving
  the owner is banned.
- Do not duplicate generic coercion helpers such as `_mapping`,
  `_json_dict`, `_normalize_*`, `_delta`, or `_parts` across files when one
  shared owner is appropriate.
- Do not hide the same slop class in Codex-only or Claude-only project assets,
  hooks, prompt builders, command shims, config templates, or generated
  guidance.
- Do not leave giant renderers, payload builders, or routers phase-mixed when
  the pass can split them into data prep, view model, and template/render
  stages, or gather, score, and decide stages.
- New or materially rewritten runtime Python modules must carry a truthful
  module docstring.
- Every anti-slop cleanup must add or update enforcement tests.

## Fail-Closed Exit Criteria
- No touched file may still contain `def _host()` or `host = _host()`.
- No touched file may keep an avoidable generic helper clone once the shared
  owner exists.
- No touched pass may leave a shared helper or kernel as an ornament while the
  touched callers stay on local forks without a bounded follow-up.
- No touched host-mirror pair may still keep avoidable shared control flow in
  both files once a real shared owner exists.
- No touched giant function may leave with the same phase-mixed ownership it
  had on entry when the pass is explicitly about structural debt.
- No touched file may replace a removed shim with an alias wall that still
  hides the real owner.
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
- When the anti-slop rule itself changes, prove the shared guidance, host
  contracts, install-generated guidance, shared skills, and shipped mirrors in
  the same pass.
- When the user asks for repo-wide or lane-wide anti-slop hardening, update
  guidance, skills, install-generated guidance, host contracts, mirrors, and
  enforcement tests together; prose-only hardening is incomplete.
- If the pass claims repo-wide or lane-wide cleanup, rerun the requested
  repo-wide structural scan or equivalent inventory before closeout.
- Repo-wide or lane-wide anti-slop claims require two proof layers: fresh
  behavior proof for the touched slice and a fresh structural inventory for
  the claimed scope. One does not substitute for the other.
- Run the headless browser matrix when the change touches browser-proved UI or
  shell surfaces.
