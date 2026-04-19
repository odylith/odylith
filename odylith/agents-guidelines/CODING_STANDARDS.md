# Coding Standards

## Scope And Precedence
- This file is the shared Odylith coding baseline that may reach the consumer
  lane.
- For consumer-owned code, the consumer repo's own `AGENTS.md`, coding
  standards, and validation/tooling rules take precedence.
- This baseline is language-agnostic on purpose. It applies to consumer-owned
  code whether the repo is Python, TypeScript, JavaScript, Go, Rust, Java,
  shell, SQL, or mixed-language.
- Maintainer-only Odylith product coding policy lives in
  `../maintainer/agents-guidelines/CODING_STANDARDS.md`.

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Shared Documentation, Reuse, And Robustness
- Clear code documentation, reusability, and robustness are non-negotiable.
- Prefer extending shared helpers, shared contracts, and existing runtime
  primitives over copy-paste or near-duplicate logic.
- If equivalent behavior already exists, reuse it or consolidate toward one
  canonical implementation instead of growing a parallel fork.
- When behavior changes would otherwise stop being obvious to the next
  maintainer, update the governing doc, spec, or nearest high-signal code
  comment in the same change.
- Add or tighten inline code documentation only when it clarifies non-obvious
  invariants, state transitions, pressure cases, or boundary assumptions. Do
  not add filler comments to obvious code.
- New helpers should stay bounded, named for the real contract they carry, and
  covered by focused validation rather than introduced as one-off glue.

## Anti-Slop Guardrails
- Treat AI slop as a regression.
- The anti-slop contract is shared across consumer and maintainer lanes.
- Codex and Claude must enforce the same anti-slop contract across consumer
  and maintainer lanes.
- Treat the slop class, not the language syntax, as the thing to ban.
- Apply that bar to any codebase or project surface: services, libraries,
  apps, CLIs, infra glue, scripts, docs, prompts, hooks, templates, config,
  and generated assets all count.
- No transitional states. Do not replace one slop class with another.
- Move ownership, not just file boundaries.
- Do not ship fake modularization. `def _host()` plus a wall of rebound
  private host symbols is banned.
- Do not replace fake modularization with a function-local or module-local
  alias wall that still hides the real owner behind renamed helper rebinding.
- Do not duplicate generic coercion helpers such as `_mapping`,
  `_json_dict`, `_normalize_*`, `_delta`, or `_parts` across files when one
  shared owner is appropriate.
- Do not treat a shared helper or kernel as a cleanup ornament. If a new owner
  lands, adopt it in the touched slice or leave a bounded follow-up tied to
  the same slop class.
- Do not call a slop cleanup complete just because the first smell
  disappeared. If the replacement smell still exists in the touched slice, the
  pass is incomplete.
- Apply the same bar to equivalent non-Python slop such as duplicated parser
  helpers, near-identical platform adapters, giant phase-mixed controllers or
  components, mirrored hook scripts, and boilerplate command or config assets.
- Do not keep host-mirror files near-identical when a shared helper, shared
  renderer, or shared formatter would remove the duplication.
- Do not leave giant renderers, payload builders, routers, or score engines
  phase-mixed when a real owner can separate data prep, view model,
  template/render, or gather/score/decide stages.
- Project assets, prompts, hooks, commands, templates, and generated config
  are code surfaces for this rule.
- Do not add filler comments or docstrings. Comments must explain invariants,
  failure modes, boundary assumptions, or non-obvious state transitions.
- New or materially rewritten runtime Python modules must carry a truthful
  module docstring.
- Every anti-slop cleanup must add or update enforcement tests.
- When the anti-slop rule changes, propagate it across shared guidance, host
  contracts, install-generated guidance, skills, and shipped mirrors in the
  same change.
- When the user asks for repo-wide or lane-wide anti-slop hardening, update
  guidance, skills, install-generated guidance, host contracts, mirrors, and
  enforcement tests together; prose-only hardening is incomplete.
- When a cleanup exposes a structural regression, fail closed: repair the
  regression and rerun the governing proof surface before landing more slop
  cleanup on top.
- For touched `1200+` or `2000+` source files, and for touched `500+` or `900+`
  line functions, default to real decomposition work instead of another layer
  of local glue.
- Use [ANTI_SLOP_AND_DECOMPOSITION.md](./ANTI_SLOP_AND_DECOMPOSITION.md) for
  the full ban list, decomposition triggers, and proof contract.

## Shared Validation Expectations
- Every coding change should carry focused validation that proves the real
  contract touched by the change.
- In consumer repos, validate consumer-owned code with the consumer repo's own
  toolchain and rule set after Odylith narrows the slice.
- When the consumer repo is not Python, use the analogous local proof surface
  for that stack instead of downgrading the anti-slop bar because the syntax
  changed.
- Use [VALIDATION_AND_TESTING.md](./VALIDATION_AND_TESTING.md) for the full
  proof bundles and command-level validation guidance for Odylith-owned
  product surfaces.
