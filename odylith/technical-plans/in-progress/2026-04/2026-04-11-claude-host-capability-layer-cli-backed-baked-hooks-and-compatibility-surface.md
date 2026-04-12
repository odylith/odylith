Status: In progress

Created: 2026-04-11

Updated: 2026-04-11

Backlog: B-089

Goal: Mirror the Codex capability-aware, CLI-backed parity that `B-087` and
`B-088` landed for Codex into the Claude host lane so Odylith stays as
dynamically introspected and as uniformly CLI-backed on Claude as it is on
Codex, while preserving every richer Claude-native primitive (statusline,
PreCompact, SubagentStart/Stop, Write|Edit|MultiEdit matchers, project
subagents, slash commands, CLAUDE.md memory bridge) as a first-class lane.
Specifically, build a real Claude capability layer
(`src/odylith/runtime/common/claude_cli_capabilities.py` plus an
`odylith claude compatibility` CLI surface), bake every remaining
`.claude/hooks/*.py` script into a first-class runtime module under
`src/odylith/runtime/surfaces/claude_host_*.py` routed through `odylith
claude ...`, derive an effective `.claude/settings.json` permissions and
hook-command snapshot at install time, expand the Claude slash commands and
permissions allowlist to cover the broader command surface, feed the new
Claude capability snapshot into `host_runtime.py` and `subagent_router.py`
routing decisions, author `CLAUDE_HOST_CONTRACT.md`, and add a focused
proof lane.

Assumptions:
- `B-083`, `B-084`, and `B-085` already landed the Claude delegation
  parity, the host-family execution-profile ladder, and the first baked
  Claude runtime modules (statusline + PreCompact snapshot). The `odylith
  claude` CLI subcommand group already exists.
- `B-087` and `B-088` already established the Codex capability-aware
  pattern: a frozen dataclass capability snapshot under
  `src/odylith/runtime/common/codex_cli_capabilities.py`, a thin
  `odylith codex compatibility` CLI surface, baked Codex hook modules
  routed through a thin `_cmd_codex_host_command` dispatcher, and an
  install-time effective `.codex/config.toml` derivation.
- The Claude host event set this slice cares about is `SessionStart`,
  `SubagentStart`, `UserPromptSubmit`, `PreToolUse` (Bash matcher),
  `PostToolUse` (Write|Edit|MultiEdit matcher), `PreCompact`,
  `SubagentStop`, and `Stop`. PreCompact is already CLI-backed via
  `odylith claude pre-compact-snapshot`; the remaining seven event lanes
  still execute through standalone scripts under `.claude/hooks/`.
- The shared helpers used by the standalone Claude hook scripts live in
  `.claude/hooks/odylith_claude_support.py`. They are the equivalent of
  `codex_host_shared.py` and need to migrate into
  `src/odylith/runtime/surfaces/claude_host_shared.py` (or a new
  `claude_host_hooks_shared.py`) so the baked runtime modules can import
  them through the Odylith Python package.
- `src/odylith/cli.py` is in the red zone, so new growth must stay
  dispatcher-only and follow the same thin-host-group pattern used by
  B-085 and B-088.
- Claude project assets already activate without trusted-project gating,
  unlike Codex; the capability snapshot must record that asymmetry instead
  of pretending Claude needs the same gating.

Constraints:
- Keep Codex byte-identical. No file touched in this slice may regress the
  Codex baseline contract or the Codex compatibility report.
- Do not delete the standalone `.claude/hooks/*.py` scripts in the same
  commit that bakes the runtime modules until the
  `.claude/settings.json` rewiring proves the CLI-backed contract works
  end to end. Land the baked modules and the dispatcher first, then flip
  `.claude/settings.json`, then remove the standalone scripts and the
  shared `odylith_claude_support.py` script in the same commit as the
  flip.
- Do not inline Claude host logic into `src/odylith/cli.py`; only thin
  dispatcher scaffolding belongs there.
- Do not introduce a strict minimum Claude Code version pin. The Claude
  capability snapshot must report what is locally proven, not what is
  globally assumed.
- Preserve every richer Claude-native primitive untouched: statusline,
  PreCompact, SubagentStart, SubagentStop, Write|Edit|MultiEdit matchers,
  project subagents, slash commands, CLAUDE.md memory bridge, output
  styles, rules.

Reversibility: The slice is structurally reversible. If the CLI-backed
Claude host pattern has unexpected fallout, the new `claude_host_*.py`
modules and dispatcher entries can be removed and the standalone
`.claude/hooks/*.py` scripts restored from history. Focused tests pin the
expected hook outputs, the capability-snapshot shape, and the CLI dispatch
contract so a rollback stays legible.

Boundary Conditions:
- Scope includes the new Claude capability layer module, the new
  compatibility CLI surface, the seven baked Claude host runtime modules,
  the thin `odylith claude` CLI dispatcher additions, the migration of
  shared helpers out of `.claude/hooks/odylith_claude_support.py`, the
  rewired live and bundled `.claude/settings.json`, the expanded
  permissions allowlist, the new slash commands, the new
  `CLAUDE_HOST_CONTRACT.md` doc, the install-time effective settings
  derivation, the routing capability injection, the focused unit tests,
  and the bundle mirror refresh.
- Scope excludes Codex-only behavior, MCP server surfaces, full
  benchmark-grade proof of the Claude routing changes, and any
  decomposition of `cli.py`, `subagent_router.py`, or `install/manager.py`
  beyond the dispatcher and call-site additions required for this slice.

Related Bugs:
- No new Casebook bug is opened for this slice unless a regression
  emerges during the bake-in. `CB-103` remains the silent
  model-selection flag bug closed by `B-084`; this slice extends the
  Claude host posture rather than reopening that bug.

## Learnings
- [ ] Claude project assets already activate without trusted-project
      gating, so the Claude capability snapshot must record the asymmetry
      against Codex's `trusted_project_required = True` instead of copying
      the Codex flag verbatim.
- [ ] Baking a hook into a first-class runtime module is the same kind of
      structural win for Claude as it was for Codex: it removes a parallel
      script lane, lets the hook reuse the rest of the Odylith runtime,
      and makes the hook's contract testable through the same `odylith ...`
      CLI dispatch the rest of the product uses.
- [ ] Capability-aware host posture is the right abstraction for both
      hosts. Codex uses it to gate `.codex/hooks.json` activation; Claude
      uses it to record the Claude Code build, the project-assets posture
      (always active), and the available hook event coverage.

## Must-Ship
- [ ] Promote `B-089` into an active plan and bind it to `release-0-1-11`.
- [ ] Create `src/odylith/runtime/common/claude_cli_capabilities.py`
      mirroring `codex_cli_capabilities.py`: a frozen dataclass snapshot,
      `_run_claude_command()`, `parse_claude_version()`,
      `inspect_claude_cli_capabilities()`, an `lru_cache`'d inspector,
      `clear_claude_cli_capability_cache()`, an effective settings
      renderer, and an effective settings writer.
- [ ] Create `src/odylith/runtime/surfaces/claude_host_compatibility.py`
      with `inspect_claude_compatibility`, `render_claude_compatibility`,
      and a `main()` argparse entry point that mirrors
      `codex_host_compatibility.py`'s shape and supports `--repo-root`,
      `--claude-bin`, `--json`, and `--skip-version-probe`.
- [ ] Migrate the helpers from `.claude/hooks/odylith_claude_support.py`
      into `src/odylith/runtime/surfaces/claude_host_shared.py` (or a new
      `claude_host_hooks_shared.py` if the existing module would breach
      the soft size limit).
- [ ] Bake every remaining Claude host hook into a first-class runtime
      module under `src/odylith/runtime/surfaces/`:
      `claude_host_session_start.py`, `claude_host_subagent_start.py`,
      `claude_host_prompt_context.py`, `claude_host_bash_guard.py`,
      `claude_host_post_edit_checkpoint.py`,
      `claude_host_subagent_stop.py`, `claude_host_stop_summary.py`. Each
      module exposes a pure renderer plus a `main()` argparse entry.
- [ ] Add the new Claude command names to
      `_CLAUDE_HOST_COMMAND_MODULES` in `src/odylith/cli.py` and extend
      the `claude_host_subparsers` plus the fast-path dispatch table so
      `odylith claude session-start`, `odylith claude subagent-start`,
      `odylith claude prompt-context`, `odylith claude bash-guard`,
      `odylith claude post-edit-checkpoint`,
      `odylith claude subagent-stop`, `odylith claude stop-summary`, and
      `odylith claude compatibility` all dispatch through the existing
      `_cmd_claude_host_command`-style pattern.
- [ ] Wire `host_runtime.py` so the Claude branch consumes a Claude
      capability snapshot just like the Codex branch already does, and
      report compact capability fields (`claude_cli_available`,
      `claude_cli_version`, `supports_project_hooks`,
      `compatibility_posture`, `baseline_contract`).
- [ ] Wire `subagent_router.py` so the Claude branch's runtime banner
      reflects the Claude capability snapshot the same way the Codex
      branch reflects `supports_project_hooks` today (without changing
      Codex behavior).
- [ ] Add `_write_effective_claude_project_settings(repo_root=...)` next
      to `_write_effective_codex_project_config` in
      `src/odylith/install/manager.py`, and call it from
      `_sync_managed_project_root_assets`. The renderer must merge the
      capability-derived hook commands and the broader permissions
      allowlist into a deterministic JSON shape, written via
      `atomic_write_text` (or the JSON equivalent).
- [ ] Update the live and bundled `.claude/settings.json` to call
      `./.odylith/bin/odylith claude ...` for every event lane (not just
      `PreCompact`), expand the `permissions.allow` list to cover the
      broader CLI surface (`Bash(./.odylith/bin/odylith doctor:*)`,
      `Bash(./.odylith/bin/odylith atlas:*)`,
      `Bash(./.odylith/bin/odylith backlog:*)`,
      `Bash(./.odylith/bin/odylith validate:*)`,
      `Bash(./.odylith/bin/odylith sync:*)`, etc.), and include the
      `odylith-governed-brief.md` and PreCompact snapshot anchors in the
      same managed block.
- [ ] Remove the standalone `.claude/hooks/*.py` scripts and
      `.claude/hooks/odylith_claude_support.py` from both the live tree
      and `src/odylith/bundle/assets/project-root/.claude/` once the
      settings flip is in place; the same commit must add the bundle
      mirrors of the new `.claude/settings.json` and any new slash
      commands.
- [ ] Add the missing high-frequency Claude slash commands under
      `.claude/commands/` (and bundle mirrors): `odylith-version.md`,
      `odylith-doctor.md`, `odylith-atlas-render.md`,
      `odylith-atlas-auto-update.md`, `odylith-backlog-validate.md`,
      `odylith-registry-validate.md`, `odylith-registry-sync-specs.md`,
      `odylith-compatibility.md`. Use the same `argument-hint`
      frontmatter pattern from the existing parameterized commands.
- [ ] Author `odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md`
      mirroring `CODEX_HOST_CONTRACT.md`: CLI-First Non-Negotiable, Claude
      Project-Asset Surface, Native Claude Code Support, Supported With
      Odylith Workarounds, Native-Blocked And Deferred, Router Contract
      Boundary.
- [ ] Add focused unit coverage:
      `tests/unit/runtime/test_claude_cli_capabilities.py`,
      `tests/unit/runtime/test_claude_host_compatibility.py`,
      `tests/unit/runtime/test_claude_host_session_start.py`,
      `tests/unit/runtime/test_claude_host_prompt_context.py`,
      `tests/unit/runtime/test_claude_host_bash_guard.py`,
      `tests/unit/runtime/test_claude_host_post_edit_checkpoint.py`,
      `tests/unit/runtime/test_claude_host_subagent_start.py`,
      `tests/unit/runtime/test_claude_host_subagent_stop.py`,
      `tests/unit/runtime/test_claude_host_stop_summary.py`,
      `tests/unit/install/test_effective_claude_settings.py`, and an
      extension to `tests/unit/test_codex_host_cli.py` (or a new
      `tests/unit/test_claude_host_cli.py`) covering the new dispatch.
- [ ] Refresh the bundle mirrors under
      `src/odylith/bundle/assets/project-root/.claude/` and update
      `odylith/technical-plans/INDEX.md` and the Casebook/Registry/
      Atlas/Compass governance trail entries that reference this slice.

## Should-Ship
- [ ] Run the strongest local Claude Code proof that is available in
      this environment for the new project-root hook contract.
- [ ] Log the slice to Compass so the `v0.1.11` release lane reflects
      the baked Claude runtime posture.

## Defer
- [ ] Router-level named-agent selection through Claude beyond the
      existing project-subagent contract.
- [ ] MCP server surfaces (out of scope per operator direction on the
      B-084 slice).
- [ ] Fresh Claude-host benchmark proof (out of scope; contract
      hardening only).
- [ ] `cli.py`, `subagent_router.py`, and `install/manager.py`
      decomposition beyond the dispatcher and call-site additions
      required for this slice.

## Success Criteria
- [ ] `inspect_claude_cli_capabilities()` returns a deterministic frozen
      snapshot keyed by `(repo_root, claude_bin, probe)` that captures
      the local Claude CLI version, the project-assets posture, the
      hook event coverage, and the overall posture token.
- [ ] `odylith claude compatibility` exits with status `0` when the
      Claude baseline-safe contract (`CLAUDE.md +
      ./.odylith/bin/odylith`) holds locally and reports the same shape
      as `odylith codex compatibility`.
- [ ] Every previously standalone `.claude/hooks/*.py` script is
      replaced by a CLI-backed call to `./.odylith/bin/odylith claude
      ...` in the live and bundled `.claude/settings.json`, with the
      bundle mirrors carrying the same contract.
- [ ] `host_capabilities("claude_cli")` returns the new
      capability-derived fields alongside the existing static fields,
      and `subagent_router.py`'s Claude banner reflects them.
- [ ] Consumer installs derive `.claude/settings.json` from the local
      Claude capability snapshot via
      `_write_effective_claude_project_settings`, and the resulting
      JSON is deterministic and idempotent.
- [ ] `odylith codex compatibility` and the Codex byte-identical proof
      lane stay green; nothing in this slice regresses Codex.
- [ ] The new slash commands (`/odylith-version`, `/odylith-doctor`,
      `/odylith-atlas-render`, `/odylith-atlas-auto-update`,
      `/odylith-backlog-validate`, `/odylith-registry-validate`,
      `/odylith-registry-sync-specs`, `/odylith-compatibility`) load in
      Claude Code and mirror their bundle copies.
- [ ] `CLAUDE_HOST_CONTRACT.md` is the canonical Claude host contract
      next to `CODEX_HOST_CONTRACT.md`.
- [ ] Focused validation is green across the new Claude runtime
      modules, the new compatibility CLI, the install-time effective
      settings, and the touched routing call sites.

## Non-Goals
- [ ] Replacing `CLAUDE.md` or `AGENTS.md` as canonical cross-host
      instruction surfaces.
- [ ] Hard-pinning Odylith to one exact Claude Code release.
- [ ] Adding `.claude/mcp/` surfaces.
- [ ] Decomposing `cli.py`, `subagent_router.py`, or `install/manager.py`
      beyond what this slice strictly requires.
- [ ] Producing fresh benchmark proof for the Claude host.

## Impacted Areas
- [ ] [2026-04-11-claude-host-capability-layer-cli-backed-baked-hooks-and-compatibility-surface.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-11-claude-host-capability-layer-cli-backed-baked-hooks-and-compatibility-surface.md)
- [ ] [2026-04-11-claude-host-capability-layer-cli-backed-baked-hooks-and-compatibility-surface.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-host-capability-layer-cli-backed-baked-hooks-and-compatibility-surface.md)
- [ ] [src/odylith/runtime/common/claude_cli_capabilities.py](/Users/freedom/code/odylith/src/odylith/runtime/common/claude_cli_capabilities.py)
- [ ] [src/odylith/runtime/common/host_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/common/host_runtime.py)
- [ ] [src/odylith/runtime/surfaces/](/Users/freedom/code/odylith/src/odylith/runtime/surfaces)
- [ ] [src/odylith/runtime/orchestration/subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [ ] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [.claude/settings.json](/Users/freedom/code/odylith/.claude/settings.json)
- [ ] [.claude/commands/](/Users/freedom/code/odylith/.claude/commands)
- [ ] [.claude/hooks/](/Users/freedom/code/odylith/.claude/hooks)
- [ ] [src/odylith/bundle/assets/project-root/.claude/](/Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/.claude)
- [ ] [odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md](/Users/freedom/code/odylith/odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md)
- [ ] [tests/unit/runtime/](/Users/freedom/code/odylith/tests/unit/runtime)
- [ ] [tests/unit/install/](/Users/freedom/code/odylith/tests/unit/install)
- [ ] [tests/unit/test_codex_host_cli.py](/Users/freedom/code/odylith/tests/unit/test_codex_host_cli.py)

## Rollout
1. Land the B-089 plan, the radar binding, and the technical-plans INDEX
   row before any source edit.
2. Create `claude_cli_capabilities.py`, the compatibility surface, and
   the migrated shared helpers under `claude_host_shared.py` (or a
   sibling module) with focused unit tests.
3. Bake the seven Claude host hooks into first-class runtime modules with
   focused unit tests. Each module must remain a thin renderer plus
   `main()` argparse entry that never raises into the caller.
4. Add the thin `odylith claude ...` dispatcher entries in `cli.py` and
   the matching CLI dispatch test.
5. Wire `host_runtime.py` and `subagent_router.py` to consume the Claude
   capability snapshot.
6. Add the install-time effective `.claude/settings.json` derivation in
   `install/manager.py`.
7. Update the live and bundled `.claude/settings.json`, expand the
   permissions allowlist, and remove the standalone `.claude/hooks/*.py`
   scripts in the same commit as the rewire.
8. Add the missing slash commands and their bundle mirrors.
9. Author `CLAUDE_HOST_CONTRACT.md`.
10. Run focused validation, refresh governed surfaces, and stage the
    commit.

## Cross-Lane Impact
- **dev-maintainer (`source-local`)**: fully live once the new modules
  and dispatcher land; this is the lane that can prove the baked Claude
  host behavior before the release ships.
- **pinned dogfood**: the checked-in `.claude/settings.json` will point
  at the new `odylith claude ...` host group, so full behavior depends
  on the `v0.1.11` runtime carrying the dispatcher and modules.
- **consumer pinned-runtime**: consumers receive parity only when the
  `v0.1.11` release ships and they upgrade.

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_claude_cli_capabilities.py tests/unit/runtime/test_claude_host_compatibility.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_claude_host_session_start.py tests/unit/runtime/test_claude_host_subagent_start.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_claude_host_bash_guard.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/runtime/test_claude_host_subagent_stop.py tests/unit/runtime/test_claude_host_stop_summary.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_effective_claude_settings.py tests/unit/test_codex_host_cli.py tests/unit/test_claude_project_hooks.py tests/unit/runtime/test_claude_host_statusline.py tests/unit/runtime/test_claude_host_precompact_snapshot.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_compatibility.py tests/unit/runtime/test_codex_host_session_brief.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_codex_host_bash_guard.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_codex_host_stop_summary.py`
- [ ] `./.odylith/bin/odylith claude compatibility --repo-root . || true`
- [ ] `./.odylith/bin/odylith codex compatibility --repo-root . || true`
- [ ] `./.odylith/bin/odylith start --repo-root .`
- [ ] `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [ ] `git diff --check`
