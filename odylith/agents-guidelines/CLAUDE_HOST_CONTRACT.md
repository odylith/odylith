# Claude Host Contract

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

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
- `PostToolUse` matchers on `Write|Edit|MultiEdit` and `PreToolUse` matchers
  on `Bash`, both consumed by the baked Claude host modules.

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
- Claude's governed-refresh precision comes from the exact edited path in the
  `PostToolUse` payload itself, so this lane does not depend on Bash-command
  target inference and remains the authoritative exact-path parity target for
  Codex's narrower Bash checkpoint contract.
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
  trivial or question-shaped stop messages and only logs a Compass
  `implementation` event when the message looks like a real action summary.
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
  edit-trigger that Codex's `PostToolUse` Bash-only checkpoint cannot
  replicate.
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
  `baseline_safe_live_proven`) as authoritative over older Compass, shell,
  or release-history context for Claude host capability questions.
