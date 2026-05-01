# Codex Host Contract

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Shared Host Default
- The default Odylith operating lane is shared across Codex and Claude Code:
  repo-root `AGENTS.md`, the repo-local `./.odylith/bin/odylith` launcher,
  truthful `odylith ... --help`, and the grounded governance workflow should
  mean the same thing on both hosts.
- Routine backlog, plan, bug, spec, component, and diagram upkeep should stay
  on that shared lane first.
- Host-specific guidance belongs only where a native host capability is real,
  locally supported, and materially reduces hops compared with the shared CLI
  path.
- Odylith Discipline is host-semantic, not Codex-specific.
  Codex may surface `.agents/skills/odylith-discipline`, but
  pressure observation, stance, hard-law, affordance, learning, validation, and
  benchmark decisions must come from the shared local runtime. Codex hooks,
  compatibility probes, and routed subagents must not spend host model credits
  to classify Odylith Discipline pressure.
- Odylith Discipline support is proven as a host/lane matrix, not a Codex-only happy
  path: Codex and Claude must share the same semantic contract across dev,
  pinned dogfood, and consumer lanes. Codex model aliases resolve to the Codex
  adapter family, but the Odylith Discipline decision remains local and model-agnostic.

## Shared Anti-Slop Contract
- Codex and Claude must enforce the same anti-slop contract across consumer
  and maintainer lanes.
- Treat the slop class, not the language syntax, as the thing to ban.
- Apply that bar to any codebase or project surface: services, libraries,
  apps, CLIs, infra glue, scripts, docs, prompts, hooks, templates, config,
  and generated assets all count.
- No transitional states. Do not replace one slop class with another.
- Consumer repos may be Python, TypeScript, JavaScript, Go, Rust, Java,
  shell, SQL, or mixed-language; the language changes, the anti-slop bar does
  not.
- Structural cleanup is not permission to drift behavior, UX, or UI. Preserve
  semantics deliberately and prove the touched contract on the real toolchain
  or surface that owns it.
- Routed Codex leaves inherit the same anti-slop contract. Do not use
  `spawn_agent`, `.agents/skills/`, or `.codex/` project assets as a place to
  hide duplicate helpers, fake wrappers, giant phase-mixed handlers, or
  near-identical mirrors.
- Treat hooks, prompt builders, command shims, config templates, and fallback
  renderers as code surfaces under the same anti-slop bar.
- Do not use Codex memory scaffolds, hook payload formatters, statusline or
  checkpoint helpers, or agent templates as escape hatches for softer
  anti-slop rules.
- Do not use compatibility wrappers, lazy proxies, facade accessors, or
  mirror-only indirection inside Codex-only assets to keep an old owner alive
  after nominal extraction.
- Do not soften the anti-slop rule in Codex-only assets. If a Codex-specific
  divergence is necessary, document the concrete host capability reason and
  prove parity against the shared contract.
- A cleanup is not complete just because a Codex-specific wrapper now calls a
  shared helper. If duplicated control flow or text still exists in the
  touched host assets, the pass is incomplete.
- Host-specific green proof is not repo-wide structural proof. For repo-wide
  or lane-wide anti-slop claims, rerun the requested structural inventory for
  the claimed scope and pair it with fresh behavior proof for the touched
  slice.
- Guidance-only hardening without updated tests, validators, or mirror-content
  checks is incomplete.
- Do not claim browser-rendered UI hardening from hook, snapshot, or unit proof
  alone. If the touched Codex-visible assets also drive browser-rendered
  dashboards, onboarding, shells, HTML, CSS, JS, templates, or other
  browser-proved surfaces, rerun the full headless browser matrix and cover the
  real rendered states that own the contract, including normal, empty/fallback,
  and degraded or error states when they exist.
- When one host tightens the anti-slop bar, update the other host contract,
  shared guidance, install-generated guidance, skills, and shipped mirrors in
  the same change.
- If a Codex-only asset truly must diverge from Claude, document the concrete
  host capability reason. Otherwise collapse the behavior behind one shared
  helper, formatter, template, or contract owner.

## Codex Project-Asset Surface
- Codex CLI can load repo-scoped project assets from `.codex/` plus repo-scoped
  skills from `.agents/skills/`.
- Odylith treats `AGENTS.md` as the canonical cross-host instruction surface.
  `.codex/config.toml`, `.codex/agents/*.toml`, `.codex/hooks.json`, and
  `.agents/skills/*/SKILL.md` reinforce that contract rather than replacing it.
- Core Odylith viability on Codex must not depend on those project assets.
  The baseline contract is the repo-root `AGENTS.md` plus the repo-local
  `./.odylith/bin/odylith` launcher. If a local Codex build ignores project
  assets, Odylith should still be usable through that baseline lane.
- Consumer install and repair now derive the effective `.codex/config.toml`
  from the local Codex capability snapshot instead of copying one frozen
  feature assumption forever. Hooks are enabled in the effective config only
  when the local Codex build proves `features.codex_hooks = true`.
- Codex only activates the checked-in `.codex/` layer for trusted projects.
  Install materialization is not the same thing as host activation.
- Odylith treats Codex compatibility as capability-based. Validate the local
  host with `./.odylith/bin/odylith codex compatibility --repo-root .` instead
  of pinning a maximum Codex version or assuming one exact CLI build is the
  only safe lane.

## Native Codex CLI Support
- Repo-scoped custom project agents under `.codex/agents/*.toml`.
- Repo-scoped config under `.codex/config.toml`.
- Repo-scoped lifecycle hooks under `.codex/hooks.json` when
  `[features] codex_hooks = true`.
- Repo-scoped skill shims under `.agents/skills/*/SKILL.md`.

## Codex-Only Optimizations When Supported
- The checked-in `.codex/` and `.agents/skills/` layers are best-effort
  enhancements for hosts that honor them. They are not allowed to become the
  only path by which Odylith can start safely on Codex.
- Odylith's Codex host-runtime contract now consumes a cheap local capability
  probe, so routing and host banners can distinguish the baseline-safe lane
  from locally proven project-hook support instead of treating every Codex
  build as the same frozen capability set.
- If you want to know whether those optional Codex project-asset optimizations
  are actually live, run `./.odylith/bin/odylith codex compatibility --repo-root .`.
- `baseline_safe_assistant_visible_ready` is intentionally stricter than
  "Codex can read AGENTS." It requires the local Codex feature registry to
  report `features.codex_hooks = true`, `.codex/hooks.json` to wire
  `UserPromptSubmit`, Bash `PostToolUse`, and `Stop` to the Odylith CLI hook
  commands, the live prompt-input probe to show repo-root guidance, and the
  assistant-render fallback to be available for chat-visible delivery.
  `codex debug prompt-input` proves model-visible repo guidance only; it does
  not prove the user saw any intervention in chat.
- `codex exec --json` is useful smoke coverage for the CLI command lane, but
  its event stream is not the UX transcript and must not be used as the sole
  proof that hook `systemMessage` intervention beats reached the user. Treat
  direct `odylith codex ...` hook payloads as structured-output
  proof and a rendered assistant message as the visibility proof.
- Session-start grounding runs through the CLI-backed
  `./.odylith/bin/odylith codex session-start-ground --repo-root .` hook
  command, which summarizes the active Odylith slice into hook-added developer
  context from cached runtime state. The normal hook does not run
  `odylith start`; maintainers can opt into eager start explicitly for
  diagnostics.
- User-prompt context can narrow explicit `B-###`, `CB-###`, or `D-###`
  references through the CLI-backed
  `./.odylith/bin/odylith codex prompt-context --repo-root .` hook command.
  Low-signal prompts without anchors, visibility complaints, or governance
  hints must return without building the prompt intervention bundle.
- The public command surface stays `./.odylith/bin/odylith codex ...`, but
  the repo-local launcher may dispatch baked Codex hook commands directly to
  their runtime modules after trust selection. Hot hook commands must not pay
  for the full `odylith.cli` import before prompt gating can return empty.
- Destructive Bash blocking runs through a repo-managed Codex `PreToolUse`
  Bash hook command
  (`./.odylith/bin/odylith codex bash-guard --repo-root .`) and denies a
  narrow destructive subset. Raw shell or Python removal of Odylith-managed
  paths is denied with a remediation that points back to
  `./.odylith/bin/odylith uninstall --repo-root .`.
- Edit-like Codex checkpointing runs through the CLI-backed
  `./.odylith/bin/odylith codex post-bash-checkpoint --repo-root .` hook
  command so the project-root `.codex/` layer stays declarative. The
  current Codex hook schema exposes Bash `PostToolUse`; native desktop
  developer tools such as `apply_patch`, `exec_command`, or `unified_exec`
  are parsed by the runtime for manual/test fallback but must not be claimed
  as automatically hook-dispatched until the host exposes those tool names in
  the hook input schema.
- The PostToolUse checkpoint is deliberately cheap: it infers changed paths
  from the current tool payload, intersects those paths with the dirty
  governed source-of-truth set, records a tiny dirty event under
  `.odylith/runtime/host-hooks/`, and returns silently. It must not run
  `odylith start`, `odylith sync`, or conversation rendering on the tool-call
  critical path. Stop-time settlement drains those dirty events, then runs
  `./.odylith/bin/odylith sync --impact-mode selective <paths>` only when an
  exact governed target was recorded. Scoped `AGENTS.md` and `CLAUDE.md`
  companions inside governed subtrees are ignored.
- The command-scoped inference must stay exact under dirty worktrees and
  shell edge cases: rename and move operations preserve the old governed path
  when truth leaves a governed subtree, shell control operators and
  redirection tails cannot widen the target set, and explicit inline
  `python -c` / `node -e` file-write one-liners may refresh only when the
  hook can recover an exact governed path literal from the current command.
- The checkpoint never blocks the tool call. Sync failures happen during
  Stop-time settlement, keep pending dirty events in place, exit the hook path
  with code 0, and emit a fail-soft `systemMessage` describing the failure so
  the operator can recover manually.
- This is **checkpoint parity** with Claude's direct-edit and Bash checkpoint
  lanes for hookable Bash edits. Native desktop write payloads remain
  supported by the parser and `visible-intervention` fallback command, but
  they are not automatic hook coverage until Codex exposes those tools to
  `PostToolUse`.
- Codex prompt-context and stop-summary lanes feed
  the same shared conversation-observation core in
  `src/odylith/runtime/intervention_engine/`. Prompt submit may emit one
  earned teaser plus one shared `Odylith Assist:` visibility line for
  non-passthrough prompts; stop-summary may replay an already-earned ambient
  block, Observation, or Proposal. Governed writes stay inside one
  confirmation-gated `Odylith Proposal`.
- When prompt submit earns a teaser, Codex should carry that sentence in the
  hook `systemMessage` and also place an assistant-render fallback in
  `hookSpecificOutput.additionalContext`. When no teaser is earned for a
  normal non-passthrough prompt, the shared prompt-visible Assist line is the
  fallback instead of silence. Prompt-time context should feel like one gentle
  interjection, not a visible dump of narrowing scaffolding.
- Plain `Odylith, show me what you can do` and `Odylith, help` prompts are
  first-match route locks, not requests for a Codex-authored capability
  summary. When Codex hooks are available, `codex prompt-context` must emit
  discreet `additionalContext` that locks the route before normal prompt
  observation. Baseline `AGENTS.md` and `.agents/skills/odylith-show-me` must
  enforce the same stdout-only contract when hooks are unavailable. The show
  route must forbid hand-written "here's what Odylith demonstrated" summaries,
  install-posture narration, dirty-path analysis, context-packet summaries,
  module-count scans, tmp-clone warnings, spawn-policy notes, and follow-up
  questions. Codex must run the first available repo-root show/help command,
  return stdout only, or report the shortest actionable Odylith blocker.
- Requests to list Odylith capabilities, engines, product architecture, or the
  capability map must run `odylith capabilities` and print stdout only. That
  inventory is product-owned and host-model agnostic; Codex must not infer it
  from `odylith --help`, `odylith show`, tool availability, skill lists, or
  generic Codex capability prose.
- Codex help discovery must run the single authoritative
  `odylith ... --help` command first. Do not batch that help call with
  exploratory `ls`/`rg` probes whose failure can cancel the visible help
  output. If the guessed command is invalid, fall back to `odylith --help` and
  then the nearest listed subcommand. Technical-plan work uses
  `odylith governance ...` and `odylith validate plan-* ...`;
  `odylith plan --help` is only a read-only command guide and there is no
  `odylith/technical-plans/source/` directory.
- Post-bash checkpoint is a dirty-event recorder, not a live intervention
  carrier and not a refresh receipt lane. Successful dirty-event recording
  stays silent. If deferred refresh fails or is skipped, Stop may emit only
  the compact failure-level status, optionally after an already-earned visible
  block.
- Stop-summary is a logging and replay lane, not a fresh visible-intervention
  author. It confirms what the assistant already showed, logs meaningful
  summaries to Compass, and may replay a pending Ambient Highlight,
  Observation, or Proposal that was already earned by prompt or Bash
  checkpoint hooks. It must not manufacture a new Observation, Proposal,
  Assist, Risks, History, Insight, continuation reason, transcript-proof copy,
  or governance ID from the stop summary itself.
- A replayed Stop beat may append the matching one-line Assist when that Assist
  belongs to the same pending live moment. Low-signal stops, already visible
  closeouts, validation summaries without a pending live beat, and explicit
  uninstall/status turns stay silent in hook output.
- `./.odylith/bin/odylith codex visible-intervention --repo-root .` is the
  manual low-latency escape hatch for Codex Desktop or any Codex build that
  keeps hook output hidden. It prints the exact Markdown the assistant should
  show; do not rewrite the copy by hand.
- `./.odylith/bin/odylith codex intervention-status --repo-root .` is the
  cheap activation proof surface. It reports static hook readiness, the active
  UX lanes, recent delivery-ledger events, pending proposals, and the exact
  smoke command to force a visible fallback. Use it before telling an operator
  the Codex intervention UX is active in a particular session.
- Only describe a Codex session or worktree as fully end to end after
  `intervention-status` reports `Activation: ready` and `chat-visible proof:
  proven_this_session`. `ledger_visible_unconfirmed`,
  `pending_confirmation`, `ledger_visible_with_pending_confirmation`, and
  `chat_confirmed_with_pending_confirmation` are partial proof, not
  completion; `degraded` and `unproven_this_session` are not active yet.
- That live path is intervention-engine-owned on purpose. Do not route Codex
  prompt or checkpoint hooks through the heavier closeout chatter stack just
  to render teaser/Observation/Proposal text.
- Empty or missing hook session ids must fall back to a stable host-local
  synthetic session token. Codex must never bleed recent prompt or changed-path
  memory from one session into another just because the payload omitted
  `session_id`.
- Prompt-context should still surface a truthful teaser when the signal is
  real even if anchor narrowing or launcher-backed context resolution is
  unavailable. Missing anchor context may suppress the anchor summary, not the
  earned teaser itself.
- In Codex, the first Observation line must make the interjection explicit and
  stay as short as `Odylith Assist`. Proposal should stay a short ruled block,
  not a sectioned mini card. If the surface reads like filler or the user
  cannot tell why Odylith stepped in, the host experience has failed even when
  the underlying facts are correct.
- The same conversation moment must keep one stable intervention identity
  across prompt, stop, and post-bash checkpoints. Codex should feel like one
  evolving intervention path, not a fresh branded interruption at each hook.
- Post-bash may surface the first eligible Proposal even when the matching
  Observation was already shown earlier in the session. Do not force Codex to
  repeat the same Observation block just to unlock Proposal copy.
- Codex must not invent Codex-only labels, alternate confirmation text, or a
  colder host-specific voice for those blocks. The Observation/Proposal
  markdown contract is shared with Claude and remains consistent across
  detached `source-local`, pinned dogfood, and consumer lanes.
- Guidance Behavior proof on Codex follows the same shared contract as Claude:
  run `odylith validate guidance-behavior --repo-root .` for deterministic
  pressure-case proof, keep `guidance_behavior_summary` compact on live packet
  paths, and use case-scoped validator commands when a packet names one
  pressure case.
- Codex guidance behavior must stay in the shared platform contract. The
  `.agents/skills/odylith-guidance-behavior/` shim, bundled consumer skill
  mirror, install guidance, and benchmark/eval family are validated together by
  `odylith_guidance_behavior_platform_end_to_end.v1`; do not add a Codex-only
  proof phrase, command family, or hidden-success rule.
- For the bounded delegation pressure case, routed Codex leaves still use the
  current `spawn_agent` contract. Do not claim `.codex/agents/*.toml` is
  selected by `spawn_agent`; preserve the emitted owner, goal, expected output,
  termination condition, and validation expectation in the spawned prompt.
- Codex does not have project-scoped slash commands, so Odylith uses
  `.agents/skills/` command-skills instead of trying to fake a
  `.codex/commands/` surface.
- The worthwhile explicit Codex command-skill surface is the high-frequency,
  deterministic CLI lane only:
  - `$odylith-start`
  - `$odylith-context`
  - `$odylith-query`
  - `$odylith-session-brief`
  - `$odylith-sync`
  - `$odylith-version`
  - `$odylith-doctor`
  - `$odylith-compass-log`
  - `$odylith-compass-refresh`
  - `$odylith-guidance-behavior`
- Common consumer-lane fast paths should be one direct CLI hop:
  - `./.odylith/bin/odylith bug capture --help`
  - `./.odylith/bin/odylith backlog create --help`
  - `./.odylith/bin/odylith component register --help`
  - `./.odylith/bin/odylith atlas scaffold --help`
  - `./.odylith/bin/odylith compass log --help`
- Keep `.agents/skills` lookup, missing-shim, and fallback-source-path details
  implicit unless they change the next user-visible action.
- Specialist governance, packet, registry, diagram, and orchestration
  workflows stay under `odylith/skills/` instead of being mirrored into the
  default Codex discovery path.
- The intentionally deferred lane is everything that is low-frequency,
  mutation-heavy, or better served by direct CLI invocation:
  `install`, `reinstall`, `upgrade`, `rollback`, `uninstall`, `on`, `off`,
  release/program/wave maintenance, benchmark publishing, worktree creation,
  and fake command aliases for surfaces that do not yet have a stable Odylith
  CLI family.
- A plain uninstall request is a direct CLI lifecycle request. Run
  `./.odylith/bin/odylith uninstall --repo-root .` without a commit/snapshot
  preflight or second confirmation question; do not translate it into
  `rm -rf`, Python `shutil.rmtree`, or a hook-bypass instruction. The command
  detaches root guidance, preserves repo-local `odylith/` governed source
  truth, removes the `.odylith/` runtime state, and detaches Odylith-owned
  Claude/Codex hook entries so an already-open host stops calling the removed
  launcher. Do not ask whether to remove `.claude/`, `.codex/`, or `.agents/`;
  those host directories may contain non-Odylith user config.
- Use `./.odylith/bin/odylith uninstall --repo-root . --dry-run` only when the
  operator asks what uninstall would touch, asks for a preview, or asks a
  scope question before deciding. Do not insert a dry-run as a second
  confirmation step after a direct uninstall request.
- For the known 0.1.11 component-register Registry drift, do not recommend
  hand-editing `odylith/registry/source/component_registry.v1.json`. The
  operator-facing answer after 0.1.12 ships is: upgrade, then run
  `./.odylith/bin/odylith doctor --repo-root . --repair`, then rerun the
  blocked sync or refresh command.
- In human-facing release copy, prefer `active target release` for the live
  planning lane and `latest shipped release` for the last GA version. Keep
  `current` and `next` for selector and alias semantics.
- Local evidence on 2026-04-16 shows `codex-cli 0.119.0-alpha.28` exposes
  `features.codex_hooks`, reads the repo-root AGENTS contract through
  `codex debug prompt-input`, and has the three Odylith intervention hooks
  wired in `.codex/hooks.json`; those are separate checks, and all must remain
  green before claiming live-proven Codex intervention posture.

## Native-Blocked And Deferred
- No `PreCompact` hook equivalent.
- No `SubagentStart` or `SubagentStop` hook equivalent.
- No custom statusline renderer API comparable to Claude's command-driven
  statusline.
- No routed named-agent selection through Odylith's current `spawn_agent`
  host-tool integration yet, even though Codex CLI itself supports checked-in
  custom project agents.

## Router Contract Boundary
- Keep two Codex layers distinct:
  - project-native Codex CLI assets under `.codex/` and `.agents/skills/`
  - the current Odylith routed `spawn_agent` host-tool contract
- Today, routed `spawn_agent` still emits built-in agent roles only:
  `default`, `explorer`, and `worker`.
- Until this host integration proves named-agent selection end to end, do not
  claim that `.codex/agents/*.toml` files are router-selectable
  `agent_type` values.
