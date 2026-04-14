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
- Session-start grounding runs through the CLI-backed
  `./.odylith/bin/odylith codex session-start-ground --repo-root .` hook
  command, which summarizes the active Odylith slice into hook-added developer
  context.
- User-prompt context can narrow explicit `B-###`, `CB-###`, or `D-###`
  references through the CLI-backed
  `./.odylith/bin/odylith codex prompt-context --repo-root .` hook command.
- Destructive Bash blocking runs through a repo-managed Codex `PreToolUse`
  Bash hook command
  (`./.odylith/bin/odylith codex bash-guard --repo-root .`) and denies a
  narrow destructive subset.
- Edit-like Bash checkpointing runs through the CLI-backed
  `./.odylith/bin/odylith codex post-bash-checkpoint --repo-root .` hook
  command so the project-root `.codex/` layer stays declarative.
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
- In human-facing release copy, prefer `active target release` for the live
  planning lane and `latest shipped release` for the last GA version. Keep
  `current` and `next` for selector and alias semantics.
- Local evidence on 2026-04-11 shows `codex-cli 0.119.0-alpha.28` already
  exposes `features.codex_hooks` and can render `codex debug prompt-input`
  successfully in this repo, so Odylith does not need a strict `0.120.0+`
  floor for the baseline-safe lane.

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
