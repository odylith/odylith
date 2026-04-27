Status: Done

Created: 2026-03-30

Updated: 2026-03-30

Backlog: B-032

Goal: Ship the v0.1.5 operator-contract hardening wave so Odylith has one
obvious first-turn command, explicit mutation previews, step-based long-running
progress, narrow dashboard refresh semantics, stronger missing-launcher
recovery, and docs/skills/help text that all describe the same shipped
behavior.

Assumptions:
- `odylith start` is the canonical first-turn command for both consumer repos
  and the product repo's pinned dogfood posture.
- Mutation preview should use shared `--dry-run` surfaces, not one-off preview
  subcommands per operator workflow.
- Consumer repos must remain on verified release assets only; no automatic
  source-local escape hatch is acceptable in the public lane.
- Narrow dashboard refresh is more trustworthy than broadening `sync` for a
  shell-only upkeep request.

Constraints:
- Keep `odylith start` non-mutating on unhealthy paths.
- Keep preview and execution sourced from the same internal step graph so
  preview cannot drift from reality.
- Keep shell-facing refresh narrow by default; Mermaid source refresh remains
  opt-in.
- Keep source-owned and bundled docs/skills/help text aligned in the same
  change.

Reversibility: Reverting this slice removes the new command aliases, preview,
and progress scaffolding while leaving verified runtime assets, repo truth, and
operator state intact.

Boundary Conditions:
- Scope includes first-turn CLI routing, lifecycle dry-run preview, sync and
  dashboard execution plans, Mermaid worker heartbeat and failure reporting,
  narrowing fallback commands, and shipped docs/skills/help alignment.
- Scope excludes broader benchmark redesign, daemon transport changes, and a
  wider shell redesign.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Odylith still makes the operator choose between `version`, `doctor`,
      `bootstrap`, and `sync` manually for common turns.
- [x] Long-running sync and Atlas work can read hung even when the product is
      still progressing deterministically.
- [x] Mutation scope and dirty-worktree overlap are too implicit before
      lifecycle or surface-refresh writes.
- [x] Narrowing fallback guidance is still too generic when Odylith cannot
      safely ground the slice.
- [x] Docs, help text, installed skills, and repo-root guidance still lag the
      intended `start`-first operator posture.

## Success Criteria
- [x] `odylith start` always prints one final lane: `bootstrap`, `status`,
      `repair`, `install`, or `fallback`.
- [x] Missing install shape and missing launcher paths print the exact next
      self-heal/install command instead of impossible local commands.
- [x] `install`, `reinstall`, `upgrade`, `sync`, `dashboard refresh`, and
      `atlas auto-update` expose `--dry-run`.
- [x] Sync and dashboard refresh print step-based plans, dirty-worktree
      overlap, progress, heartbeat-backed long-running status, and final
      outcome summaries.
- [x] Atlas auto-update shows mutation classes, dirty overlap, named worker
      heartbeats, and final blocking diagram ids on failure.
- [x] Narrowing guidance carries one explicit next fallback command and a
      direct-read follow-up.
- [x] Source docs, bundled docs, skills, AGENTS guidance, and spec text all
      describe `odylith start`, narrow refresh, and `--dry-run` consistently.

## Non-Goals
- [x] Changing the underlying managed-runtime trust model.
- [x] Broadening consumer repos into source-local execution.
- [x] Turning `odylith start` into an automatic mutating repair command.

## Execution Waves
- [x] Wave 1: `odylith start`, start preflight, impossible-command removal,
      and narrowing fallback command contract.
- [x] Wave 2: shared dry-run/mutation-plan scaffolding, dirty-overlap preview,
      sync/dashboard progress, and heartbeat-backed long-running execution.
- [x] Wave 3: recovery wording, shell-scoped refresh polish, version/toolchain
      clarity, and doc/help/skill/spec alignment.

## Impacted Areas
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py)
- [x] [tooling_context_routing.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/tooling_context_routing.py)
- [x] [tooling_context_packet_builder.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/tooling_context_packet_builder.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [FAQ.md](/Users/freedom/code/odylith/odylith/FAQ.md)
- [x] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [x] [UPGRADE_AND_RECOVERY.md](/Users/freedom/code/odylith/odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-session-context/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-context-engine-operations/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] bundled mirrors under [src/odylith/bundle/assets/odylith](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [test_agents.py](/Users/freedom/code/odylith/tests/unit/install/test_agents.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)
- [x] [test_auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_update_mermaid_diagrams.py)

## Risks & Mitigations

- [x] Risk: `odylith start` becomes opaque.
  - [x] Mitigation: always print one explicit final lane plus the exact next
        command when Odylith cannot proceed safely.
- [x] Risk: preview drifts from execution.
  - [x] Mitigation: execute the same step graph that dry-run prints.
- [x] Risk: heartbeat output becomes noisy.
  - [x] Mitigation: limit heartbeats to 10-second intervals and only for
        subprocess-backed or worker-backed waits.
- [x] Risk: docs and bundle assets drift again.
  - [x] Mitigation: patch source-owned and bundled mirrors together and keep
        focused contract tests on the updated text.

## Validation/Test Plan
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/install/test_agents.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_tooling_context_routing.py tests/integration/install/test_manager.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_odylith_benchmark_runner.py`
- [x] `git diff --check`

## Rollout/Communication
- [x] Make `odylith start` the visible first-turn happy path in help, docs,
      AGENTS guidance, and installed skills.
- [x] Keep `dashboard refresh` visibly narrow and keep Atlas source refresh
      opt-in.
- [x] Keep `--dry-run` user-facing wording crisp about mutation classes and
      dirty-worktree overlap.

## Current Outcome
- [x] Bound to `B-032`; implementation landed and the plan was closed into
      `done`.
- [x] `odylith start` is now the canonical first-turn command. It evaluates
      install posture without mutating by default, prints one explicit lane,
      and emits the exact next repair/install/fallback command when Odylith
      cannot proceed safely.
- [x] Lifecycle, sync, dashboard refresh, and Atlas auto-update now share
      dry-run mutation previews, dirty-worktree overlap reporting, step-based
      progress, 10-second heartbeats for long-running waits, and clear final
      outcome summaries.
- [x] Narrowing guidance now preserves one exact fallback command plus a
      direct-read follow-up through the routed packet, compact packet builder,
      and hot-path store.
- [x] Source docs, bundled mirrors, skills, AGENTS guidance, and Odylith spec
      text now all describe the same `start`-first, narrow-refresh, dry-run
      contract.
- [x] Focused validation passed:
      `118 passed` for the CLI/install/sync/Atlas lane,
      `59 passed` for the packet-builder/benchmark lane,
      and `git diff --check` passed.
