Status: In progress

Created: 2026-04-11

Updated: 2026-04-14

Backlog: B-088

Goal: Close the remaining supported Codex-vs-Claude parity gap for the
`v0.1.11` target release by baking the Codex host hook behaviors into
first-class runtime modules under `src/odylith/runtime/surfaces/`, exposing
them through a thin `odylith codex` CLI subcommand group, rewiring the checked-in
`.codex/hooks.json` contract to call the CLI directly, and normalizing the
touched human-facing release wording to distinguish the active target release
from the latest shipped GA release without renaming the governed `current` and
`next` aliases. This slice also hardens the Codex compatibility contract so
Odylith stays baseline-safe on `codex-cli 0.119.0-alpha.28`, other currently
deployed builds that expose the same capabilities, and future Codex versions
that continue honoring the repo-root `AGENTS.md` plus launcher contract even
when project-asset features vary.

Assumptions:
- `B-087` already landed the first Codex parity slice: the project-root
  `.codex/` assets, `.agents/skills/` shims, and the shared install contract
  are in place and bound to `release-0-1-11`.
- The supported Codex host event set remains `SessionStart`,
  `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`. This slice
  should not invent unsupported host-native behavior.
- The checked-in `.codex/` and `.agents/skills/` layers are enhancement
  surfaces. They must not become the only way Odylith works safely on Codex.
- Consumer install and repair may now derive an effective `.codex/config.toml`
  from the detected local Codex capability snapshot rather than treating the
  checked-in config as the only runtime truth.
- Codex does not provide repo-scoped custom slash commands, so the worthwhile
  command-equivalent surface in this slice is explicit repo-scoped
  `.agents/skills/` command-skills for the high-frequency Odylith CLI lane.
- `src/odylith/cli.py` is already in the red zone, so new CLI growth must stay
  dispatcher-only and follow the same thin-host-group pattern used by B-085.
- The underlying release selector contract is already correct: `current` and
  `next` are explicit aliases owned by source truth. The wording problem is on
  active human-facing surfaces, not in the alias mechanism itself.

Constraints:
- Do not teach the routed `spawn_agent` tool contract to emit named
  `.codex/agents/*.toml` values in this slice.
- Do not add fake Codex equivalents for Claude-only native gaps such as
  `PreCompact`, subagent lifecycle hooks, or a custom statusline API.
- Do not inline Codex host logic into `src/odylith/cli.py`; only dispatch
  scaffolding belongs there.
- Do not perform a blind global rename from `current release` to `target
  release`. Active touched surfaces should become more precise, while the
  underlying selector language and historical records remain intact.

Reversibility: This slice is structurally reversible. If the CLI-backed Codex
host pattern turns out to be the wrong fit, the new `codex_host_*.py` modules
and dispatcher can be removed and the old standalone `.codex/hooks/*.py`
scripts restored from history. Focused tests pin the expected hook outputs and
CLI contract so a rollback stays legible.

Boundary Conditions:
- Scope includes first-class Codex host runtime modules, thin `odylith codex`
  CLI dispatch, `.codex/hooks.json` command rewiring, removal of the standalone
  `.codex/hooks/*.py` logic lane, the matching bundle mirrors, focused Codex
  host tests, and touched guidance/runbook/UI wording around active target
  release semantics.
- Scope excludes router-level named custom-agent routing, full trusted-project
  live proof beyond what is possible locally this turn, broader release-wording
  churn across untouched historical artifacts, and any decomposing of `cli.py`
  beyond the dispatcher additions required for the new host group.

Related Bugs:
- [CB-111](../../../casebook/bugs/2026-04-14-consumer-lane-routine-governance-ux-can-leak-shim-plumbing-instead-of-direct-cli.md)
  tracks the consumer-lane help-surface regression where Atlas forwarded help
  still leaked backend filenames and refresh-wrapper copy after the broader
  skill-surface simplification. `B-087` remains the parent project-asset
  parity slice.

## Learnings
- [ ] Codex project-root assets are only half the parity story. Without a
      first-class runtime surface and CLI host dispatch, the shipped `.codex/`
      tree still depends on a parallel script lane that the rest of Odylith
      does not use.
- [ ] Release wording must distinguish selector semantics from operator-facing
      semantics: `current` is a governed alias, while the human-facing concept
      here is the active target release.
- [ ] Codex compatibility needs to be capability-based rather than pinned to a
      strict minimum version. Local proof should explicitly cover the
      installed `0.119.0-alpha.28` build when that build already exposes the
      needed host capabilities.
- [x] Mirroring the full specialist governance skill inventory into repo-root
      `.agents/skills/` adds ceremony to routine Codex work. The repo-root
      Codex lane should stay on `AGENTS.md`, the launcher, truthful CLI help,
      and a narrow explicit command-shim surface instead.
- [x] Common governed authoring commands in the consumer lane must forward
      backend help and present direct CLI fast paths. If `bug capture`,
      `backlog create`, `component register`, or `atlas scaffold` still land
      on shim-only `--help`, the user is back in source spelunking instead of
      a crisp first-hop lane.
- [x] Forwarded-help polish has to cover the full public surface, not just flag
      exposure. A command like `odylith atlas render --help` still regresses
      the consumer lane if it prints `cli.py` / `__main__.py` or wrapper-only
      copy instead of the top-level command name and description.
- [x] The host default has to stay shared across Codex and Claude Code.
      Codex-specific guidance should exist only for capability-gated
      optimizations that materially reduce hops compared with the shared CLI
      lane; otherwise the extra host-specific copy is just ceremony.

## Must-Ship
- [ ] Promote `B-088` into an active plan and bind it to `release-0-1-11`.
- [ ] Create `src/odylith/runtime/surfaces/codex_host_shared.py` for the
      shared Codex hook/runtime helpers.
- [ ] Create first-class runtime modules for the supported Codex host behaviors:
      session-start grounding, prompt context, destructive Bash guard,
      post-edit checkpoint, and stop-summary logging.
- [ ] Add a thin `odylith codex` dispatcher to `src/odylith/cli.py` that calls
      those modules without inlining logic.
- [ ] Rewire `.codex/hooks.json` to call `./.odylith/bin/odylith codex ...`
      directly and remove the standalone `.codex/hooks/*.py` implementation
      files from the live and bundled project-root trees.
- [ ] Add focused unit coverage for the new Codex host runtime modules and the
      updated CLI-backed hook contract.
- [ ] Clarify touched active surfaces to use `active target release` versus
      `latest shipped release` where the existing copy could mislead operators.
- [ ] Add a first-class `odylith codex compatibility` inspection command that
      proves the baseline-safe contract and reports local Codex capability
      signals without pinning a maximum version.
- [ ] Enrich the Codex host capability contract from a cheap local Codex probe
      so routing and install no longer treat all Codex builds as one frozen
      capability set.
- [ ] Derive the effective consumer `.codex/config.toml` from the detected
      local Codex capability snapshot during install or repair.
- [x] Add explicit Codex command-skills for the curated high-frequency Odylith
      CLI surface: `start`, `context`, `query`, `session-brief`, `sync`,
      `version`, `doctor`, `compass log`, and `compass refresh --wait`.

## Should-Ship
- [ ] Run the strongest local Codex CLI proof that is available in this
      environment for the new project-root hook contract.
- [ ] Log the slice to Compass so the `v0.1.11` release lane reflects the
      baked Codex runtime posture.

## Defer
- [ ] Router-level named custom-agent routing through the current `spawn_agent`
      tool contract.
- [ ] Unsupported Codex-native surfaces such as `PreCompact`, subagent
      lifecycle hooks, or a custom statusline renderer.
- [ ] Large-scale release-wording churn outside the active touched surfaces.
- [ ] `src/odylith/cli.py` decomposition toward the hard limit.

## Success Criteria
- [ ] The checked-in `.codex/hooks.json` contract is CLI-backed and no longer
      depends on standalone hook Python scripts under `.codex/hooks/`.
- [ ] The Codex host behavior is implemented and tested under
      `src/odylith/runtime/surfaces/`.
- [ ] `src/odylith/cli.py` grows only by thin dispatcher scaffolding.
- [ ] Touched human-facing release surfaces stop implying that `current`
      necessarily means the latest shipped GA release.
- [ ] Odylith documents and proves that the Codex baseline-safe lane is
      `AGENTS.md` plus `./.odylith/bin/odylith`, with `.codex/` and
      `.agents/skills/` treated as best-effort enhancements.
- [ ] Consumer installs adapt the effective `.codex/config.toml` to the local
      Codex capability snapshot instead of blindly shipping one static hooks
      assumption.
- [x] Codex exposes a curated explicit command-skill surface for the
      worthwhile Odylith CLI lane instead of pretending repo-scoped custom
      slash commands exist.
- [x] Common consumer-lane governance authoring commands expose backend help
      and the installed guidance points users straight to those CLI fast
      paths without surfacing `.agents/skills` lookup or fallback plumbing.
- [x] Forwarded consumer-lane help surfaces identify themselves as the public
      `odylith ...` command rather than leaking backend filenames or wrapper
      implementation descriptions.
- [x] Installed and shipped guidance present one shared host lane across dev,
      dogfood, and consumer postures, and limit Codex-only advice to
      capability-gated project-asset optimizations such as `odylith codex
      compatibility`.
- [ ] Focused validation is green across the new Codex runtime modules, the
      updated asset contract, and the touched release wording.

## Non-Goals
- [ ] Renaming the governed `current` / `next` aliases.
- [ ] Claiming unsupported Codex-native parity.
- [ ] Hard-pinning Odylith to one exact Codex release as the only supported
      lane.
- [ ] Reworking unrelated release, Compass, or guidance copy that this slice
      does not touch.

## Impacted Areas
- [ ] [2026-04-11-codex-host-runtime-parity-cli-dispatch-and-target-release-wording-hardening.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-11-codex-host-runtime-parity-cli-dispatch-and-target-release-wording-hardening.md)
- [ ] [2026-04-11-codex-host-runtime-parity-cli-dispatch-and-target-release-wording-hardening.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-11-codex-host-runtime-parity-cli-dispatch-and-target-release-wording-hardening.md)
- [ ] [src/odylith/runtime/surfaces/](/Users/freedom/code/odylith/src/odylith/runtime/surfaces)
- [ ] [src/odylith/runtime/common/](/Users/freedom/code/odylith/src/odylith/runtime/common)
- [ ] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [.codex/hooks.json](/Users/freedom/code/odylith/.codex/hooks.json)
- [ ] [src/odylith/bundle/assets/project-root/.codex/hooks.json](/Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/.codex/hooks.json)
- [ ] [.agents/skills/](/Users/freedom/code/odylith/.agents/skills)
- [ ] [src/odylith/bundle/assets/project-root/.agents/skills/](/Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/.agents/skills)
- [ ] [odylith/MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [ ] [odylith/registry/source/components/release/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [ ] [odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [ ] [odylith/skills/](/Users/freedom/code/odylith/odylith/skills)
- [ ] [tests/unit/install/test_codex_project_assets.py](/Users/freedom/code/odylith/tests/unit/install/test_codex_project_assets.py)
- [ ] [tests/unit/runtime/](/Users/freedom/code/odylith/tests/unit/runtime)

## Rollout
1. Land the B-088 plan and release binding before source edits.
2. Create the first-class Codex host runtime modules with focused unit tests.
3. Add the thin `odylith codex` CLI dispatcher.
4. Rewire `.codex/hooks.json` to the CLI-backed contract and remove the
   standalone hook-script lane from the live and bundled project assets.
5. Add the Codex compatibility inspection path and clarify the touched active
   release and host wording surfaces.
6. Run focused
   validation.

## Cross-Lane Impact
- **dev-maintainer (`source-local`)**: fully live once the new modules and
  dispatcher land; this is the lane that can prove the baked Codex host
  behavior before the release ships.
- **pinned dogfood**: the checked-in `.codex/hooks.json` project assets will
  point at the new `odylith codex ...` host group, so full behavior still
  depends on the `v0.1.11` runtime carrying the dispatcher and modules.
- **consumer pinned-runtime**: consumers receive the parity only when the
  `v0.1.11` release ships and they upgrade to it.

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_session_brief.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_codex_host_bash_guard.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_codex_host_stop_summary.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_compatibility.py tests/unit/test_codex_host_cli.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_subagent_reasoning_ladder.py tests/unit/test_cli.py`
- [ ] `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [ ] `git diff --check`
