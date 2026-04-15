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
- The Bash checkpoint does two things, in order: first it runs
  `./.odylith/bin/odylith start --repo-root .` to keep the session
  grounded; then, if the edit-like Bash command (``apply_patch``, ``sed
  -i``, ``cp``, ``mv``, ``tee``, ``cat >``, etc.) actually touched any
  repo-relative path under the Odylith governed source-of-truth
  subtrees (``odylith/radar/source/``, ``odylith/technical-plans/``,
  ``odylith/casebook/bugs/``, ``odylith/registry/source/``,
  ``odylith/atlas/source/``), it runs
  `./.odylith/bin/odylith sync --impact-mode selective <paths>` so the
  derived dashboards stay aligned. The changed-path set is inferred from
  the current Bash command itself, then intersected with the current
  dirty governed path set so the hook does not widen refresh to
  unrelated repo dirtiness. If the command does not expose an exact
  governed target, the checkpoint skips selective refresh instead of
  guessing. Scoped `AGENTS.md` and `CLAUDE.md` companions inside
  governed subtrees are ignored.
- The command-scoped inference must stay exact under dirty worktrees and
  shell edge cases: rename and move operations preserve the old governed path
  when truth leaves a governed subtree, shell control operators and
  redirection tails cannot widen the target set, and explicit inline
  `python -c` / `node -e` file-write one-liners may refresh only when the
  hook can recover an exact governed path literal from the current command.
- The Bash checkpoint never blocks the command: sync failures exit the
  hook with code 0 and emit a fail-soft `systemMessage` describing the
  failure so the operator can recover manually.
- This is **Bash-checkpoint parity** with Claude's `post-edit-checkpoint`
  lane — it covers the primary Codex governed-edit workflow, whose
  edit-like Bash commands include `apply_patch`. It is *not* universal
  host-edit parity: if Codex ever grows a native non-Bash edit hook, a
  separate Codex hook module would be needed to cover that surface.
- Codex prompt-context, stop-summary, and post-bash checkpoint lanes all feed
  the same shared conversation-observation core in
  `src/odylith/runtime/intervention_engine/`. Prompt submit may emit one
  teaser sentence only; stop-summary or post-bash may upgrade that into a full
  `**Odylith Observation**`; governed writes stay inside one confirmation-gated
  `Odylith Proposal`.
- Post-bash checkpoint is the primary visible intervention lane. When the
  recovered bundle earns an Observation or Proposal, Codex should surface that
  live beat through a visible hook `systemMessage` and also duplicate the full
  Observation/Proposal/Assist bundle into
  `hookSpecificOutput.additionalContext` so the next turn inherits continuity
  without forcing the user to wait for stop.
- Success-only governance refresh receipts must stay quiet when an earned live
  intervention exists. If refresh fails or is skipped, Codex may append that
  failure-level status after the visible Observation/Proposal beat instead of
  replacing it.
- Stop-summary is the fallback closeout lane, not the primary delightful
  intervention surface. When the recovered stop bundle carries a real closeout
  delta or a missed late Observation, Codex may emit one visible stop
  `systemMessage` containing that recovered beat and one short
  `Odylith Assist:` line rather than burying both in summary state.
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
