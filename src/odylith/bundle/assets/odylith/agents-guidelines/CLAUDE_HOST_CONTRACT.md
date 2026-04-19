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
- Consumer repos may be Python, TypeScript, JavaScript, Go, Rust, Java,
  shell, SQL, or mixed-language; the language changes, the anti-slop bar does
  not.
- Routed Claude leaves inherit the same anti-slop contract. Do not use
  Task-tool subagents, `.claude/commands/`, `.claude/agents/`, or
  `.claude/skills/` as a place to hide duplicate helpers, fake wrappers,
  giant phase-mixed handlers, or near-identical mirrors.
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
  `./.odylith/bin/odylith claude session-start --repo-root .` hook command,
  which mirrors a compact Compass-derived brief into Claude's documented
  auto-memory directory under `~/.claude/projects/<project>/memory/`.
- Subagent-start grounding runs through the CLI-backed
  `./.odylith/bin/odylith claude subagent-start --repo-root .` hook command,
  which injects the active Odylith slice into Claude project subagents via
  the documented `hookSpecificOutput.additionalContext` shape.
- User-prompt context can narrow explicit `B-###`, `CB-###`, or `D-###`
  references through the CLI-backed
  `./.odylith/bin/odylith claude prompt-context --repo-root .` hook command.
- User-prompt teaser visibility runs through the paired
  `./.odylith/bin/odylith claude prompt-teaser --repo-root .` hook command,
  which prints only the earned one-line teaser as a best-effort stdout source.
  Chat visibility still depends on either host display or the assistant-render
  fallback carried by prompt context.
- Destructive Bash blocking runs through a repo-managed Claude `PreToolUse`
  Bash hook command
  (`./.odylith/bin/odylith claude bash-guard --repo-root .`) and denies a
  narrow destructive subset (`rm -rf`, `git reset --hard`,
  `git checkout --`, `git push --force`, `git clean -fdx`) via the
  documented `permissionDecision: "deny"` shape.
- Edit-like checkpointing runs through the CLI-backed
  `./.odylith/bin/odylith claude post-edit-checkpoint --repo-root .` hook
  command, matched against `Write|Edit|MultiEdit`, so the project-root
  `.claude/` layer stays declarative and the governance refresh runs through
  `odylith sync --impact-mode selective <path>`.
- Bash checkpointing runs through the CLI-backed
  `./.odylith/bin/odylith claude post-bash-checkpoint --repo-root .` hook
  command, matched against `Bash`, so shell edits, inline write scripts, and
  patch-style Bash payloads can surface the same visible Observation/Proposal
  beat as direct Claude edits and Codex checkpoints.
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
  and may emit one stop surface carrying the earned Observation plus a short
  `Odylith Assist:` line from the shared closeout bundle. If that exact
  Odylith text is not already visible in the last assistant message, the Stop
  hook may block once with a continuation reason so the assistant speaks it
  before ending. The `stop_hook_active` guard prevents loops.
- Claude `UserPromptSubmit`, `Stop`, direct-edit `PostToolUse`, and Bash
  `PostToolUse` observation lanes all route through the shared
  `src/odylith/runtime/intervention_engine/` core. `UserPromptSubmit` may emit
  one teaser sentence only; `Stop` or `PostToolUse` may upgrade that into a
  full `**Odylith Observation**`; governed write suggestions stay inside one
  confirmation-gated `Odylith Proposal`.
- Claude splits `UserPromptSubmit` into two hook commands on purpose:
  `prompt-context` returns discreet JSON `hookSpecificOutput.additionalContext`
  for anchor context and continuity, while `prompt-teaser` prints an earned
  teaser as plain stdout when the host exposes it. JSON additional context is
  discreet model context and now carries an assistant-render fallback so the
  next assistant message can speak the teaser if the host hides hook output.
- `PostToolUse` is the primary intervention source lane. When the recovered
  bundle earns an Observation or Proposal, Claude should emit that live beat
  through hook `systemMessage` and carry the full Observation/Proposal/Assist
  bundle plus assistant-render fallback through top-level `additionalContext`.
  If the host keeps hook output hidden, the next assistant message must render
  the fallback Markdown instead of silently dropping the product moment.
- Do not run the primary `PostToolUse` edit checkpoint asynchronously. Async
  hooks are useful for background diagnostics, but they deliver output on a later
  turn and can suppress completion notices in normal Claude Code sessions; the
  Observation/Proposal lane is a live UX surface, so it stays synchronous.
- Success-only governance refresh receipts must stay quiet when an earned live
  intervention exists. If refresh fails or is skipped, Claude may append that
  failure-level status after the visible Observation/Proposal beat instead of
  replacing it.
- That live path is intervention-engine-owned on purpose. Do not route Claude
  prompt, stop, or post-edit hooks through the heavier closeout chatter stack
  just to render teaser/Observation/Proposal text.
- `Stop` is the fallback closeout lane, not the primary delightful
  intervention surface. Use it to recover a missed late Observation or a
  shared `Odylith Assist:` closeout beat, not as the only place users can ever
  see the intervention.
- Claude Stop must use that same one-shot continuation path for unseen
  Ambient Highlight, Observation, and Proposal beats generated by prompt,
  direct-edit, or Bash checkpoint hooks. If a live beat was only delivered
  through hidden `systemMessage`, stdout, or assistant fallback context, replay
  it before Assist instead of leaving Assist as the only visible Odylith
  surface.
- Stop-summary Assist may render from concrete validation proof in the
  assistant summary even when the hook payload did not expose changed paths.
  That fallback is bounded to validation/pass signals and must not invent
  updated artifacts. It may still name affected governance-contract IDs from
  bounded request, packet, or target-ref truth when it says the work stayed
  inside those contracts rather than updating them.
- Stop-summary Assist may also render from explicit user feedback that Odylith
  ambient highlights, interventions, Observations, Proposals, Assist, hooks,
  or chat output are not visible. Claude should recover that prompt from the
  session ledger even if the last assistant message is too short to be a
  meaningful implementation summary. Low-signal short turns still stay silent.
- Stop blocking must dedupe against the generated labels in the current
  visible text. A prior Observation label does not prove the current Assist
  closeout was already visible.
- `./.odylith/bin/odylith claude visible-intervention --repo-root .` is the
  manual low-latency escape hatch for Claude Code sessions that keep hook
  output hidden. It prints the exact Markdown the assistant should show; do
  not rewrite the copy by hand.
- `./.odylith/bin/odylith claude intervention-status --repo-root .` is the
  cheap activation proof surface. It reports static project-hook readiness,
  the active UX lanes, recent delivery-ledger events, pending proposals, and
  the exact smoke command to force a visible fallback. Use it before telling
  an operator the Claude intervention UX is active in a particular session.
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
- The same conversation moment must keep one stable intervention identity
  across `UserPromptSubmit`, `Stop`, and `PostToolUse`. Claude should feel
  like one evolving intervention path, not a fresh branded interruption at
  every hook boundary.
- `PostToolUse` may surface the first eligible Proposal even when the matching
  Observation was already shown earlier in the session. Do not force Claude to
  repeat the same Observation block just to unlock Proposal copy.
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
