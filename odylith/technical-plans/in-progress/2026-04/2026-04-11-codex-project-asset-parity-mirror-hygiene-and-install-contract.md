Status: In progress

Created: 2026-04-11

Updated: 2026-04-11

Backlog: B-087

Goal: Land the first Codex project-asset parity slice on Odylith's existing
project-root asset sync path by repairing the current `.claude/` bundle drift,
adding managed Codex project assets and repo-scoped skill shims, and making
the host contract explicit about what Codex CLI project assets support today
versus what the routed `spawn_agent` tool contract still does not expose.

Assumptions:
- `AGENTS.md` stays the canonical cross-host instruction surface, with
  project-scoped host assets reinforcing that contract instead of replacing it.
- The installer already treats `src/odylith/bundle/assets/project-root/` as one
  host-neutral sync tree, so Codex assets should land there instead of growing
  a second Codex-only install path.
- Codex CLI project assets are real enough to ship, but the current routed
  `spawn_agent` host integration still exposes built-in roles only.

Constraints:
- Repair the shared `.claude/` bundle mirror before adding new Codex assets on
  top of it.
- Do not change routed `spawn_agent` payload schema or `_HOST_SUPPORTED_AGENT_TYPES`
  in this slice.
- Keep native-blocked Codex gaps explicit: no fake `PreCompact`, no fake
  subagent lifecycle hooks, and no fake custom statusline API.
- Keep install and repair additive: project-root asset materialization should
  continue to flow through the existing project-root bundle sync helper.

Reversibility: This work is additive. Rollback can remove the checked-in
`.codex/` and `.agents/skills/` assets and restore the previous helper name and
contract text without changing the core `odylith/` runtime or consumer truth
layout.

Boundary Conditions:
- Scope includes live-versus-bundle `.claude/` mirror hygiene, the project-root
  sync helper rename, managed `.codex/` and `.agents/skills/` asset trees,
  Codex host-contract guidance, install and bundle docs, router/spec wording,
  and focused install plus asset-shape tests.
- Scope excludes Codex baked Python host surfaces, benchmark proof, router
  discovery of named `.codex/agents/*` as routed tool `agent_type` values, and
  any feature the Codex host does not natively expose.

Related Bugs:
- [CB-102](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-11-odylith-start-returns-no-candidates-when-dirty-path-set-is-dominated-by-bundle-asset-mirrors.md)

## Learnings
- [ ] Codex CLI project assets and the current routed `spawn_agent` tool
      contract are adjacent but distinct surfaces; Odylith should document
      both instead of conflating them.
- [ ] Mirror hygiene is a prerequisite for parity: adding new host assets on
      top of a drifted bundle just multiplies bad source truth.

## Must-Ship
- [ ] Promote `B-087` into an active plan and bind it to `release-0-1-11`.
- [ ] Repair the bundled `.claude/` mirror so it includes
      `odylith-compass-narrator` and `.claude/output-styles/odylith-grounded.md`.
- [ ] Rename `_sync_managed_project_claude_assets(...)` to
      `_sync_managed_project_root_assets(...)` without changing behavior.
- [ ] Add managed project-root Codex assets under `.codex/` and matching bundle
      mirrors under `src/odylith/bundle/assets/project-root/.codex/`.
- [ ] Add repo-scoped Codex skill shims under `.agents/skills/` and matching
      bundle mirrors under `src/odylith/bundle/assets/project-root/.agents/skills/`.
- [ ] Add `odylith/agents-guidelines/CODEX_HOST_CONTRACT.md` and mirror it into
      the bundled `odylith/agents-guidelines/` tree.
- [ ] Update install guidance, product docs, and registry/spec language so
      Codex project assets are explicit and the routed built-in-role spawn
      contract remains truthful.
- [ ] Add focused tests for bundle parity, install materialization, and Codex
      asset shape.

## Should-Ship
- [ ] Add a live Codex CLI `0.120.0+` proof step showing the project-scoped
      `.codex/` layer and repo-scoped `.agents/skills/` are discoverable in a
      trusted repo.
- [ ] Add one routing-contract regression that pins the updated Codex host-tool
      wording around custom project agents versus built-in routed roles.

## Defer
- [ ] Codex baked Python host surfaces and any `odylith codex ...` dispatcher.
- [ ] Router-level named custom-agent selection through the current host tool.
- [ ] Benchmark proof and release-note closeout.

## Success Criteria
- [ ] Fresh consumer install materializes `.codex/`, `.agents/skills/`, and the
      repaired `.claude/` assets without any extra Codex-specific install path.
- [ ] Managed docs and specs describe one truthful Codex project-asset contract,
      including trusted-project gating and native-blocked gaps.
- [ ] Focused tests parse the Codex config, agent TOML files, hook registry, and
      skill shim layout and keep the mirror inventory honest.

## Non-Goals
- [ ] Teaching the router to emit `.codex/agents/*` names as routed tool
      `agent_type` values before host proof exists.
- [ ] Claiming Codex parity for unsupported hook events or statusline surfaces.

## Impacted Areas
- [ ] [2026-04-11-codex-project-asset-parity-mirror-hygiene-and-install-contract.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-11-codex-project-asset-parity-mirror-hygiene-and-install-contract.md)
- [ ] [2026-04-11-codex-project-asset-parity-mirror-hygiene-and-install-contract.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-11-codex-project-asset-parity-mirror-hygiene-and-install-contract.md)
- [ ] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [.claude/](/Users/freedom/code/odylith/.claude/)
- [ ] [.codex/](/Users/freedom/code/odylith/.codex/)
- [ ] [.agents/skills/](/Users/freedom/code/odylith/.agents/skills/)
- [ ] [src/odylith/bundle/assets/project-root/](/Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/)
- [ ] [odylith/README.md](/Users/freedom/code/odylith/odylith/README.md)
- [ ] [docs/specs/odylith-repo-integration-contract.md](/Users/freedom/code/odylith/docs/specs/odylith-repo-integration-contract.md)
- [ ] [odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md](/Users/freedom/code/odylith/odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md)
- [ ] [odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md](/Users/freedom/code/odylith/odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md)
- [ ] [odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md](/Users/freedom/code/odylith/odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md)
- [ ] [odylith/agents-guidelines/CODEX_HOST_CONTRACT.md](/Users/freedom/code/odylith/odylith/agents-guidelines/CODEX_HOST_CONTRACT.md)
- [ ] [odylith/registry/source/components/subagent-router/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-router/CURRENT_SPEC.md)
- [ ] [src/odylith/runtime/orchestration/subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [ ] [tests/integration/install/test_bundle.py](/Users/freedom/code/odylith/tests/integration/install/test_bundle.py)
- [ ] [tests/integration/install/test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [ ] [tests/unit/install/test_release_bootstrap.py](/Users/freedom/code/odylith/tests/unit/install/test_release_bootstrap.py)

## Rollout
1. Promote the workstream, bind the plan, and attach the slice to the next
   release target.
2. Repair the shared `.claude/` bundle drift and rename the host-neutral
   project-root sync helper.
3. Add the Codex project-root assets and repo-scoped skill shims.
4. Update docs, specs, and install language.
5. Run focused validation and confirm a live Codex proof step separately.

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_bundle.py tests/integration/install/test_manager.py tests/unit/install/test_release_bootstrap.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_agent_governance_intelligence.py tests/unit/runtime/test_subagent_reasoning_ladder.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_manager.py`
- [ ] `git diff --check`

## Outcome Snapshot
- [ ] Odylith ships truthful Codex project assets without inventing a second
      install path.
- [ ] The bundled `.claude/` tree matches the live managed source-of-truth
      inventory again.
- [ ] Codex host docs now distinguish project-native Codex CLI assets from the
      still-built-in-only routed `spawn_agent` tool contract.
