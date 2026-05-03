# Claude Host Contract

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Shared Discipline Contract
- Odylith Discipline is host-semantic, not Claude-specific.
  Claude may surface `.claude/skills/odylith-discipline` and
  `.claude/commands/odylith-discipline.md`, but pressure
  observation, stance, hard-law, affordance, learning, validation, and
  benchmark decisions must come from the shared local runtime. Claude hooks,
  capability probes, and Task-tool subagents must not spend host model credits
  to classify Odylith Discipline pressure.
- Odylith Discipline support is proven as a host/lane matrix, not a Claude-only happy
  path: Codex and Claude must share the same semantic contract across dev,
  pinned dogfood, and consumer lanes. Claude model aliases resolve to the
  Claude adapter family, but the Odylith Discipline decision remains local and
  model-agnostic.

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
- Routed Claude leaves inherit the same anti-slop contract. Do not use
  Task-tool subagents, `.claude/commands/`, `.claude/agents/`, or
  `.claude/skills/` as a place to hide duplicate helpers, fake wrappers,
  giant phase-mixed handlers, or near-identical mirrors.
- Treat hooks, prompt builders, slash-command shims, config templates,
  statusline scripts, and fallback renderers as code surfaces under the same
  anti-slop bar.
- Do not use Claude memory bridges, hook payload formatters, statusline
  helpers, slash-command shims, or agent templates as escape hatches for
  softer anti-slop rules.
- Do not use compatibility wrappers, lazy proxies, facade accessors, or
  mirror-only indirection inside Claude-only assets to keep an old owner alive
  after nominal extraction.
- Do not soften the anti-slop rule in Claude-only assets. If a Claude-specific
  divergence is necessary, document the concrete host capability reason and
  prove parity against the shared contract.
- A cleanup is not complete just because a Claude-specific wrapper now calls a
  shared helper. If duplicated control flow or text still exists in the
  touched host assets, the pass is incomplete.
- Host-specific green proof is not repo-wide structural proof. For repo-wide
  or lane-wide anti-slop claims, rerun the requested structural inventory for
  the claimed scope and pair it with fresh behavior proof for the touched
  slice.
- Guidance-only hardening without updated tests, validators, or mirror-content
  checks is incomplete.
- Do not claim browser-rendered UI hardening from hook, snapshot, or unit proof
  alone. If the touched Claude-visible assets also drive browser-rendered
  dashboards, onboarding, shells, HTML, CSS, JS, templates, or other
  browser-proved surfaces, rerun the full headless browser matrix and cover the
  real rendered states that own the contract, including normal, empty/fallback,
  and degraded or error states when they exist.
- When one host tightens the anti-slop bar, update the other host contract,
  shared guidance, install-generated guidance, skills, and shipped mirrors in
  the same change.
- If a Claude-only asset truly must diverge from Codex, document the concrete
  host capability reason. Otherwise collapse the behavior behind one shared
  helper, formatter, template, or contract owner.

## Claude Project-Asset Surface
- Claude Code can load repo-scoped project assets from `.claude/`, including
  `.claude/CLAUDE.md`, `.claude/settings.json`, `.claude/commands/*.md`,
  `.claude/agents/*.md`, `.claude/hooks/*` (legacy script form), and
  `.claude/skills/*/SKILL.md` shims.
- Odylith treats the repo-root `CLAUDE.md` plus `AGENTS.md` as the canonical
  cross-host instruction surface. The `.claude/` tree reinforces that contract
  rather than replacing it.
- Core Odylith viability on Claude must not depend on those project assets.
  The baseline contract is the repo-root `CLAUDE.md` plus the repo-local
  `./.odylith/bin/odylith` launcher. If a Claude session ignores project
  assets, Odylith should still be usable through that baseline lane.
- Consumer install and repair derive the effective `.claude/settings.json`
  from the local Claude capability snapshot instead of copying one frozen
  feature assumption forever. Hooks, statusline, and matcher shapes are
  enabled in the effective config only when the local Claude build proves the
  corresponding capability flag.
- Claude Code does not require a per-project trust gate for repo-scoped
  project assets the way Codex does. The asymmetry is intentional: Claude's
  `project_assets_mode` is `first_class_project_surface`, Codex's is
  `best_effort_enhancements`.
- Odylith treats Claude compatibility as capability-based. Validate the local
  host with `./.odylith/bin/odylith claude compatibility --repo-root .`
  instead of pinning a maximum Claude CLI version or assuming one exact build
  is the only safe lane.

## Native Claude CLI Support
- Repo-scoped project memory bridge under `.claude/CLAUDE.md` plus the
  user-level auto-memory directory at
  `~/.claude/projects/<project>/memory/`.
- Repo-scoped settings under `.claude/settings.json`, including the
  `permissions.allow` allowlist for Bash invocations of
  `./.odylith/bin/odylith`.
- Repo-scoped slash commands under `.claude/commands/*.md`. Each one is a
  thin shim around a deterministic `./.odylith/bin/odylith ...` invocation.
- Repo-scoped project subagents under `.claude/agents/*.md`, used as the
  Claude execution lane for routed Odylith leaves through Task-tool
  delegation.
- Repo-scoped Claude skills under `.claude/skills/*/SKILL.md` shims.
- Repo-scoped lifecycle hooks for eight Claude hook events:
  `SessionStart`, `SubagentStart`, `UserPromptSubmit`, `PreToolUse`,
  `PostToolUse`, `PreCompact`, `SubagentStop`, and `Stop`. Odylith now bakes
  every one of these into a first-class runtime module under
  `src/odylith/runtime/surfaces/claude_host_*.py`, routed through
  `./.odylith/bin/odylith claude <command> --repo-root "$CLAUDE_PROJECT_DIR"`.
- Repo-scoped statusline command under `.claude/statusline.sh` plus the
  CLI-backed `./.odylith/bin/odylith claude statusline ...` renderer.
- `PostToolUse` matchers on `Write|Edit|MultiEdit` and `Bash`, plus
  `PreToolUse` matchers on `Bash`, all consumed by the baked Claude host
  modules.

## Supported Through Odylith CLI Bakes
- The checked-in `.claude/` layer is a first-class enhancement for the Claude
  host, but it is not allowed to become the only path by which Odylith can
  start safely on Claude.
- Odylith's Claude host-runtime contract consumes a cheap local capability
  probe (`claude_cli_capabilities.inspect_claude_cli_capabilities`), so
  routing and host banners can distinguish the baseline-safe lane from
  locally proven first-class project-surface support instead of treating
  every Claude build as the same frozen capability set.
- Session-start grounding runs through the CLI-backed
  `./.odylith/bin/odylith claude session-start --repo-root . --quiet` hook
  command, which mirrors a compact Compass-derived brief into Claude's
  documented auto-memory directory under
  `~/.claude/projects/<project>/memory/`. The normal hook uses cached runtime
  state, does not run `odylith start`, and does not print duplicate stdout;
  maintainers can opt into eager start or stdout explicitly for diagnostics.
- Subagent-start grounding runs through the CLI-backed
  `./.odylith/bin/odylith claude subagent-start --repo-root .` hook command,
  which injects the active Odylith slice into Claude project subagents via
  the documented `hookSpecificOutput.additionalContext` shape.
- User-prompt grounding runs through the single CLI-backed
  `./.odylith/bin/odylith claude prompt-bundle --repo-root .` hook command.
  It preserves the old show/help/capabilities route lock, anchor context,
  hidden continuity context, and earned visible teaser behavior in one
  prompt-submit process. Generic low-signal prompts without anchors,
  visibility complaints, governance hints, or Odylith-directed wording must
  return without building the prompt intervention bundle or substrate receipt.
- The public command surface stays `./.odylith/bin/odylith claude ...`, but
  the repo-local launcher may dispatch baked Claude hook commands directly to
  their runtime modules after trust selection. Hot hook commands must not pay
  for the full `odylith.cli` import before prompt gating can return empty.
- User-prompt teaser visibility is part of `prompt-bundle`: the hook emits
  discreet `hookSpecificOutput.additionalContext` plus a `systemMessage` for
  the earned visible teaser. The legacy `prompt-context` and `prompt-teaser`
  commands remain manual compatibility surfaces, but the default installed
  hook shape no longer forks marker commands for them.
- Destructive Bash blocking runs through a repo-managed Claude `PreToolUse`
  Bash hook command
  (`./.odylith/bin/odylith claude bash-guard --repo-root .`) and denies a
  narrow destructive subset (`rm -rf`, `git reset --hard`,
  `git checkout --`, `git push --force`, `git clean -fdx`) via the
  documented `permissionDecision: "deny"` shape. Raw shell or Python removal
  of Odylith-managed paths is denied with a remediation that points back to
  `./.odylith/bin/odylith uninstall --repo-root .`.
- Edit-like checkpointing runs through the CLI-backed
  `./.odylith/bin/odylith claude post-edit-checkpoint --repo-root .` hook
  command, matched against `Write|Edit|MultiEdit`, so the project-root
  `.claude/` layer stays declarative and the governance refresh runs through
  `odylith sync --impact-mode selective <path>`. The generated Claude
  settings mark this checkpoint async so tool calls do not wait on successful
  refresh work.
- Bash checkpointing runs through the CLI-backed
  `./.odylith/bin/odylith claude post-bash-checkpoint --repo-root .` hook
  command, matched against `Bash`, so shell edits, inline write scripts, and
  patch-style Bash payloads get the same governed-refresh coverage as direct
  Claude edits without turning hook receipts into visible intervention copy.
  The generated Claude settings mark this checkpoint async as well.
- The Bash checkpoint first uses exact command-path inference. Exact
  non-governed edits return immediately; governed edits and uncertain
  edit-like commands keep the conservative startup/checkpoint path.
- Claude's governed-refresh precision comes from the exact edited path in the
  direct edit `PostToolUse` payload itself; Bash-command target inference is a
  separate parity lane and must stay command-scoped so it never widens refresh
  to unrelated dirty files.
- `PreCompact` snapshotting runs through
  `./.odylith/bin/odylith claude pre-compact-snapshot --repo-root .`, which
  writes the active Odylith slice into Claude's project auto-memory
  directory before compaction so the next post-compact turn resumes with
  fresh project memory.
- `SubagentStop` event capture runs through
  `./.odylith/bin/odylith claude subagent-stop --repo-root .`, which appends
  a structured event to `odylith/compass/runtime/agent-stream.v1.jsonl` so
  Compass can stitch routed delegation evidence into the timeline.
- `Stop` summary capture runs through
  `./.odylith/bin/odylith claude stop-summary --repo-root .`, which filters
  trivial or question-shaped stop messages, logs a Compass
  `implementation` event when the message looks like a real action summary,
  and stays silent in the Claude transcript. Stop is a memory/logging lane,
  not a visible intervention recovery lane.
- Claude `UserPromptSubmit` owns live user-facing teaser output. Direct-edit
  `PostToolUse` and Bash `PostToolUse` are governed-refresh lanes: they may
  run sync/checkpoint work, stay silent on success, and emit only a compact
  failure or skipped-refresh message when the operator needs to recover. They
  must not render Observation, Proposal, Assist, internal visibility-proof
  state, product-repo workstream ids, or Casebook ids into hook output.
- Claude bundles `UserPromptSubmit` into one hook command on purpose:
  `prompt-bundle` returns discreet JSON `hookSpecificOutput.additionalContext`
  for route locks, anchor context, and continuity, and emits an earned teaser
  through `systemMessage` for the host-visible lane. Additional context still
  carries an assistant-render fallback so the next assistant message can speak
  the teaser, or the shared prompt-visible Assist line when no teaser is
  earned, if the host hides hook output.
- Plain `Odylith, show me what you can do` and `Odylith, help` prompts are
  first-match route locks, not requests for generic Claude Code capabilities.
  The route lock is now handled inside `prompt-bundle` so the default Claude
  prompt-submit path pays one process, not three. It must forbid generic
  Claude identity answers, Claude tool, skill, and memory lists, docs or
  repository-file inspection, branch-cleanliness reports, and follow-up
  questions. Claude must run the first available repo-root command, return
  stdout only, or report the shortest actionable Odylith blocker. The generated `.claude/settings.json`
  allowlist must include `Bash(./.odylith/bin/odylith show:*)`,
  `Bash(./.odylith/bin/odylith capabilities:*)`, and
  `Bash(./.odylith/bin/odylith --help:*)` so the route is executable without a
  detour through host capability prose.
- Requests to list Odylith capabilities, engines, product architecture, or the
  capability map must run `odylith capabilities` and print stdout only. That
  inventory is product-owned and host-model agnostic; Claude must not infer it
  from `odylith --help`, `odylith show`, Claude tool lists, memory, skills, or
  generic Claude Code capability prose.
- Claude help discovery must run the single authoritative
  `odylith ... --help` command first. Do not batch that help call with
  exploratory `ls`/`rg` probes whose failure can cancel the visible help
  output. If the guessed command is invalid, fall back to `odylith --help` and
  then the nearest listed subcommand. Technical-plan work uses
  `odylith governance ...` and `odylith validate plan-* ...`;
  `odylith plan --help` is only a read-only command guide and there is no
  `odylith/technical-plans/source/` directory.
- `PostToolUse` must not be used as a live intervention source lane in Claude.
  Claude renders hook output inline; successful edit and Bash checkpoints must
  produce no transcript text. If refresh fails or is skipped, emit one compact
  status line through `systemMessage` and do not include `additionalContext`.
- Claude `PostToolUse` checkpoint hooks are async in the generated settings.
  They are not live intervention carriers: success stays silent, and skipped
  or failed refreshes emit only compact recovery status.
- Prompt-visible Odylith moments must come from prompt-time teaser/stdout or
  ordinary assistant prose, not from Stop or PostToolUse hook recovery blocks.
- Claude Stop summaries are not a visible Assist recovery path. Validation
  proof, explicit visibility feedback, and missing hook visibility may still
  inform ordinary assistant prose or the manual `visible-intervention` CLI
  fallback, but Stop hook output must not print Risks, History, Insight,
  Observation, Proposal, Assist, product-repo IDs, or transcript-proof state.
  Dedupe and continuity checks remain internal ledger concerns only.
- `./.odylith/bin/odylith claude visible-intervention --repo-root .` is the
  manual low-latency escape hatch for Claude Code sessions that keep hook
  output hidden. It prints the exact Markdown the assistant should show; do
  not rewrite the copy by hand.
- `./.odylith/bin/odylith claude intervention-status --repo-root .` is the
  cheap activation proof surface. It reports static project-hook readiness,
  the active UX lanes, recent delivery-ledger events, pending proposals, and
  the exact smoke command to force a visible fallback. Use it before telling
  an operator the Claude intervention UX is active in a particular session.
- Only describe a Claude session or worktree as fully end to end after
  `intervention-status` reports `Activation: ready` and `chat-visible proof:
  proven_this_session`. `ledger_visible_unconfirmed`,
  `pending_confirmation`, `ledger_visible_with_pending_confirmation`, and
  `chat_confirmed_with_pending_confirmation` are partial proof, not
  completion; `degraded` and `unproven_this_session` are not active yet.
- Claude worktrees created under `.claude/worktrees/<slug>/` are not ready just
  because `.claude/settings.json` and hooks exist. Provision the repo-local
  launcher in that worktree immediately with `./.odylith/bin/odylith doctor
  --repo-root .claude/worktrees/<slug> --repair` from the parent repo before
  treating hooks, slash commands, or intervention checks there as self-hosting.
- Empty or missing hook session ids must fall back to a stable host-local
  synthetic session token. Claude must never bleed recent prompt or changed-path
  memory from one session into another just because the payload omitted
  `session_id`.
- `UserPromptSubmit` should still surface a truthful teaser when the signal is
  real even if launcher-backed anchor resolution is unavailable. Missing
  launcher context may suppress the anchor summary, not the earned teaser
  itself.
- In Claude, the first Observation line must make the interjection explicit
  and stay as short as `Odylith Assist`. Proposal should stay a short ruled
  block, not a sectioned mini card. If the surface reads like filler or the
  user cannot tell why Odylith stepped in, the host experience has failed even
  when the underlying facts are correct.
- The same conversation moment must keep one stable intervention identity.
  Claude should feel like one evolving intervention path, not a fresh branded
  interruption at every hook boundary. PostToolUse and Stop do not create new
  visible intervention beats.
- Claude must not invent Claude-only labels, alternate confirmation text, or a
  different narration temperature for those blocks. The Observation/Proposal
  markdown contract is the same shared product surface Codex uses across
  detached `source-local`, pinned dogfood, and consumer lanes.
- Guidance Behavior proof on Claude follows the same shared contract as Codex:
  run `odylith validate guidance-behavior --repo-root .` for deterministic
  pressure-case proof, keep `guidance_behavior_summary` compact on live packet
  paths, and use case-scoped validator commands when a packet names one
  pressure case.
- Claude guidance behavior must stay in the shared platform contract. The
  `/odylith-guidance-behavior` command, `.claude/skills/odylith-guidance-behavior/`
  shim, bundled consumer mirrors, install guidance, and benchmark/eval family
  are validated together by `odylith_guidance_behavior_platform_end_to_end.v1`;
  do not add a Claude-only proof phrase, command family, or hidden-success rule.
- For the bounded delegation pressure case, Claude leaves still use Task-tool
  subagents plus checked-in `.claude/agents/`. Preserve the routed owner,
  goal, expected output, termination condition, and validation expectation in
  the Task prompt instead of broadening it into an open-ended review.
- Statusline rendering runs through the CLI-backed
  `./.odylith/bin/odylith claude statusline --repo-root .` command, called
  from `.claude/statusline.sh`.
- The worthwhile explicit Claude slash-command surface mirrors the Codex
  command-skill surface and adds a Claude-specific compatibility entry:
  - `/odylith-start`
  - `/odylith-context`
  - `/odylith-query`
  - `/odylith-session-brief`
  - `/odylith-sync-governance`
  - `/odylith-version`
  - `/odylith-doctor`
  - `/odylith-compass-log`
  - `/odylith-compass-refresh-wait`
  - `/odylith-atlas-render`
  - `/odylith-atlas-auto-update`
  - `/odylith-backlog-validate`
  - `/odylith-registry-validate`
  - `/odylith-registry-sync-specs`
  - `/odylith-compatibility`
  - `/odylith-guidance-behavior`
  - `/odylith-plan`
  - `/odylith-handoff`
  - `/odylith-case`
  - `/odylith-workstream-new`
  - `/odylith-worktree`
- Atlas, Radar, and Registry are worth explicit Claude slash commands
  because they already expose stable CLI subcommands with low argument
  ambiguity.
- Casebook remains explicit-skill-first for investigation, capture, and
  preflight via `.claude/skills/casebook-bug-*` shims, mirroring the Codex
  posture, until a first-class `odylith casebook ...` CLI family exists.
- The intentionally deferred lane for slash commands is everything that is
  low-frequency, mutation-heavy, or better served by direct CLI invocation:
  `install`, `reinstall`, `upgrade`, `rollback`, `uninstall`, `on`, `off`,
  release/program/wave maintenance, benchmark publishing, worktree creation,
  and fake command aliases for surfaces that do not yet have a stable
  Odylith CLI family.
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

## Native Claude Strengths Preserved
- Claude Code exposes a richer native lifecycle than Codex today, and
  Odylith intentionally preserves that asymmetry instead of reducing Claude
  to the Codex feature subset.
- `PreCompact` is a Claude-only Odylith hook lane. Codex has no equivalent,
  so the Claude bake captures the full Compass-derived auto-memory before
  the host compacts.
- `SubagentStart` and `SubagentStop` are Claude-only Odylith hook lanes.
  Codex has no equivalent today, so Claude project subagents inherit
  Odylith grounding through the documented `hookSpecificOutput` shape and
  emit structured stop events into `agent-stream.v1.jsonl`.
- The `Stop` hook lets Odylith capture meaningful end-of-turn assistant
  summaries into Compass without polling or post-hoc inference.
- `PostToolUse` matchers on `Write|Edit|MultiEdit` give Odylith a precise
  direct-edit trigger, while the paired `Bash` post-bash checkpoint gives
  Claude parity for shell edits without hiding the live beat until Stop.
- The Claude statusline command lets Odylith render a live, capability-aware
  status line; Codex has no comparable API.
- Claude project subagents under `.claude/agents/*.md` are part of the
  validated routed-delegation lane. They are not a fallback for unsupported
  Codex named-agent selection; they are the Claude execution surface for
  routed Odylith leaves.
- The `.claude/CLAUDE.md` memory bridge plus the user-level auto-memory
  directory let Odylith persist a compact Compass brief across turns and
  compact events. Codex has no comparable persistent project-memory surface.

## Native-Blocked And Deferred
- Claude Code does not expose a routed named-agent selection layer through
  Odylith's current `spawn_agent` host-tool integration. Routed Claude
  delegation runs through Task-tool subagents and the checked-in
  `.claude/agents/` layer, not through `spawn_agent` host-tool calls.
- There is no `.claude/`-native equivalent of the Codex
  `features.codex_hooks` toggle, so Odylith capability probing for Claude
  measures hook surface support by introspecting the live `.claude/`
  asset shape and the Claude CLI version, not by querying a single feature
  flag.

## Router Contract Boundary
- Keep two Claude layers distinct:
  - project-native Claude Code assets under `.claude/` (memory, settings,
    commands, agents, hooks, statusline, skills)
  - the current Odylith routed delegation contract executed through Claude
    Task-tool subagents
- Router and runtime banners now consume the live Claude capability
  snapshot. When the snapshot proves all four first-class hook lanes are
  wired (`supports_project_hooks`, `supports_subagent_hooks`,
  `supports_pre_compact_hook`, `supports_statusline_command`), the routing
  contract surfaces an explicit "first-class `.claude/` project surface
  wired locally" note. Otherwise it falls back to the baseline-safe
  `CLAUDE.md + ./.odylith/bin/odylith` activation note.
- The capability snapshot is the source of truth for Claude host posture.
  Do not hand-edit `.claude/settings.json` for capability changes that
  the renderer should be deriving from the snapshot.
- Validate the local Claude posture before commit or handoff with
  `./.odylith/bin/odylith claude compatibility --repo-root .` and treat the
  printed posture (`baseline_safe`, `baseline_safe_with_project_assets`,
  `baseline_safe_with_local_claude_cli`, or
  `baseline_safe_assistant_visible_ready`) as authoritative over older
  Compass, shell, or release-history context for Claude host capability
  questions.
