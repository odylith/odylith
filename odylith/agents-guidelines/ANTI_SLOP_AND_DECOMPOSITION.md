# Anti-Slop And Decomposition

## Purpose
- This guide exists to stop AI-assisted authoring from degrading the current
  repo or project tree.
- Treat AI slop as a regression.
- Do not dismiss it as an aesthetic complaint.
- Use this guide when the slice shows duplicate helper churn, fake
  extractions, mirrored host drift, oversized-file pressure, or comment noise.
- This anti-slop contract is shared across consumer and maintainer lanes.
- Codex and Claude must enforce the same anti-slop contract across consumer
  and maintainer lanes.
- Treat the slop class, not the language syntax, as the thing to ban.
- Any codebase or project surface can accumulate slop: services, libraries,
  apps, CLIs, infra glue, scripts, docs, prompts, workflows, hooks,
  templates, config, and generated assets all count.
- Consumer repos may be Python, TypeScript, JavaScript, Go, Rust, Java,
  shell, SQL, or mixed-language; the language changes, the anti-slop bar does
  not.
- Structural cleanup is not permission to drift behavior, UX, or UI. Preserve
  semantics deliberately and prove the touched contract on the real toolchain
  or surface that owns it.

## Language-Agnostic Slop Inventory
- Treat fake seams, duplicate helpers, giant phase-mixed functions, mirror
  drift, and filler documentation as the same failure class even when the host
  repo is not Python.
- In Python, common slop signals include `_host()` shims, `bind(host)` or
  globals injection, duplicated `_normalize_*` helpers, and giant payload or
  router functions.
- In TypeScript or JavaScript, common slop signals include duplicated
  prop-shaping or parser helpers, near-identical platform adapters, giant
  components or handlers that mix data prep and rendering, and wrapper modules
  that still tunnel back into private parent helpers.
- In Go, Rust, Java, or similar compiled stacks, common slop signals include
  copy-pasted coercion or decoding helpers, giant control modules that own too
  many phases, and extracted packages that still depend on hidden parent
  internals instead of real contracts.
- In shell, SQL, docs, prompts, hooks, commands, templates, and generated
  config, common slop signals include near-identical mirrored assets,
  boilerplate command pipelines, duplicated validation text, and placeholder
  comments that explain nothing.
- Project assets, prompts, hooks, commands, templates, and generated config
  are code surfaces for this rule. Do not hide slop there just because the
  file is not runtime code.

## No Transitional States
- No transitional states. Do not replace one slop class with another.
- Move ownership, not just file boundaries.
- Do not treat a shared helper or kernel as a cleanup ornament. If the shared
  owner lands, adopt it in the touched slice or leave an explicit bounded
  follow-up tied to the same slop class.
- Do not hide the old owner behind compatibility wrappers, lazy proxies,
  facade accessors, or mirror-only indirection after a nominal extraction.
- Do not hide transitional slop behind compatibility wrappers, alias walls,
  partial migrations, or host-only copies once the real owner exists.
- Partial shared-kernel adoption is still incomplete. If a shared helper or
  kernel lands, the touched callers must adopt it or the pass is incomplete.
- A cleanup is not complete just because the original smell disappeared. If
  the replacement smell survives in the touched slice, the pass is incomplete.
- When one host or lane tightens the anti-slop bar, propagate the stronger rule
  across shared guidance, host contracts, install-generated guidance, skills,
  and shipped mirrors in the same change.

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
- Do not use partial shared-kernel adoption as proof of cleanup. A new shared
  owner that only a minority of the touched callers adopt is an incomplete pass.
- Do not use compatibility wrappers, lazy proxies, facade accessors, or
  mirror-only indirection to keep the old owner alive after nominal
  extraction.
- Do not soften the anti-slop rule on one host, one lane, or one generated
  asset surface while claiming the shared contract stayed intact.
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
- For shared hot paths, user-visible flows, or high-risk structural moves,
  land characterization or contract-focused tests before or alongside the
  refactor instead of relying on post hoc confidence.
- When introducing a shared helper, update the touched duplicates in the same
  slice or leave an explicit bounded follow-up plan.
- When guidance, skills, or bundled docs change, update the shipped mirrors in
  the same change.
- When the anti-slop rule itself changes, update shared guidance, both host
  contracts, install-generated guidance, shared skills, and shipped mirrors in
  the same change so the contract does not drift by lane.
- When claiming repo-wide or lane-wide cleanup, rerun the requested repo-wide
  structural scan or equivalent inventory instead of relying on touched-slice
  tests alone.
- Repo-wide or lane-wide anti-slop claims require two proof layers: fresh
  behavior proof for the touched slice and a fresh structural inventory for
  the claimed scope. One does not substitute for the other.
- Guidance-only hardening without updated tests, validators, or mirror-content
  checks is incomplete.
- In consumer repos, prove consumer-owned code with the consumer repo's own
  language toolchain, tests, linters, build checks, and formatter or type
  checks where applicable. Odylith narrows the slice; the consumer repo still
  proves its own code.
- In TypeScript or JavaScript repos, that usually means tests plus lint and
  typecheck/build proof. In Go, Rust, Java, shell, SQL, or mixed-language
  repos, use the analogous native test, lint, type, parser, build, or
  integration surface instead of silently downgrading the bar.
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
- If the pass adds a shared kernel, helper, or contract but leaves the touched
  callers on local forks without a bounded follow-up, the pass is incomplete.
- If you remove a fake seam and replace it with an alias wall, the pass is
  still incomplete. Remove the local alias wall or move that logic behind a
  real owner before closeout.
- If you remove a fake seam and replace it with a compatibility wrapper, lazy
  proxy, facade accessor, or mirror-only indirection, the pass is still
  incomplete. Move the real owner instead.
- If a touched change updates guidance or skills that ship through bundle
  mirrors or install-managed assets, refresh those mirrors in the same change
  and prove them with tests instead of assuming they stayed aligned.
- Fail the pass locally when the touched files still contain banned shim or
  duplicate-helper patterns after the refactor. In other words, fail closed
  on unresolved slop in the touched slice.

## Review Questions
- Does this change reduce a real duplication or boundary problem, or did it
  just move code into another file?
- Did this change remove the slop class, or did it merely rename it?
- Is the new helper owned by a stable contract that more than one caller
  should share?
- Did the pass leave a shared helper or kernel as an ornament instead of
  finishing the touched migration?
- Did the change remove filler comments and replace them with truthful
  documentation?
- Would the next maintainer be able to find the owner and the proof path
  without rediscovering them from scratch?
