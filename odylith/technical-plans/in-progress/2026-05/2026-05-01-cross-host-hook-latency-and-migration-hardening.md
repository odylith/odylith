Status: In progress

Created: 2026-05-01

Updated: 2026-05-02

Backlog: B-141

Goal: Reduce Claude and Codex host-turn latency without losing Odylith's
automatic prompt context assessment, ambient intervention blocks, visible
Assists, safety guards, or governance capture. The v0.1.13 implementation
must keep the same product behavior while moving heavy work out of the
critical path: Claude prompt-submit work becomes one bundled route, Claude
PostToolUse refreshes become async where the host supports it, Codex
PostToolUse records cheap dirty events and settles them at Stop, and
Casebook/Radar migration evidence stays captured when legacy records or
launcher repair states break.

Assumptions:
- Claude and Codex have different native hook semantics, so performance wins
  must use host-supported primitives instead of one lowest-common-denominator
  config shape.
- Prompt context, ambient highlights, Observations, Proposals, Assists, and
  governed refresh evidence are product features, not optional debug output.
- Direct-dispatch host hooks remain the reliable fallback until a long-lived
  hook daemon is separately designed, secured, and proven.
- Low-signal prompt and SessionStart fast paths must still read the compact
  alignment substrate: Context Engine packet state, memory backend, Execution
  Engine decision, delivery visibility, Tribunal state, and proof status.
- Legacy consumer Casebook records may be missing newer metadata fields and
  must migrate before stricter v0.1.13 validation runs.

Constraints:
- Do not remove safety gates. PreToolUse guards stay synchronous when they can
  block destructive or governed writes.
- Do not add unsupported host settings. Codex must not receive Claude-only
  async or `if` fields.
- Keep show/help/capability route locks stdout-clean and fast.
- Keep Status and Type in Casebook as single-word tokens in source truth,
  projection payloads, and visible chips.
- Keep generated project-root assets, Claude skills, and source bundle mirrors
  aligned with the source contracts.

Reversibility: The prompt-bundle and dirty-event settlement paths are additive
around the existing direct-dispatch runtime. If a host adapter regresses, the
settings renderers can point back to the previous command hooks while retaining
the shared route-lock and Casebook migration code.

Boundary Conditions:
- Scope includes Claude prompt-bundle rendering, Claude effective settings,
  Codex Bash guard and PostToolUse checkpoint behavior, Stop-time dirty-event
  settlement, Casebook metadata migration, host contract docs, explicit-only
  skill invocation flags, bundled project-root mirrors, and focused tests.
- Scope excludes model switching, removing Odylith grounding, MCP server
  cleanup outside the repo, and productionizing a hook daemon in v0.1.13.

Related Bugs:
- [CB-147](../../../casebook/bugs/2026-05-01-claude-hooks-spam-unhealthy-launcher-repair-errors-during-bootstrap-repair.md)
  tracks migration repair hook spam around unhealthy launcher state.
- [CB-148](../../../casebook/bugs/2026-05-01-bootstrap-doctor-repair-still-surfaces-trusted-root-warning-noise.md)
  tracks trusted-root warning noise during bootstrap doctor repair.
- [CB-149](../../../casebook/bugs/2026-05-01-host-adapters-pay-too-much-odylith-hook-and-startup-latency.md)
  tracks the host latency architecture failure.
- [CB-150](../../../casebook/bugs/2026-05-01-casebook-renders-prose-status-and-type-chips.md)
  tracks the Casebook single-word Status and Type contract.
- [CB-151](../../../casebook/bugs/2026-05-01-compass-default-governance-view-surfaces-completed-programs-and-shipped-releases.md)
  tracks the Compass default live-governance view filtering contract.
- [CB-152](../../../casebook/bugs/2026-05-02-generated-launchers-are-not-parseable-by-shipped-health-checks.md)
  tracks the mixed-version launcher-health compatibility failure found during
  fresh-host proof.

## Learnings
- [x] The original Claude-led report was a symptom, not the product boundary:
      B-141 is cross-host because Codex shares the same hot-path risk class
      around prompt context, launcher dispatch, dirty-event settlement, and
      compact intervention substrate proof.
- [x] Latency reductions that silence prompt hooks are regressions unless the
      hidden prompt context and visible intervention lanes remain equivalent.
- [x] Claude can collapse prompt work and async refreshes natively; Codex needs
      cheap command hooks plus deferred settlement because async hook fields are
      not part of its project hook contract.
- [x] Hardening Casebook metadata needs legacy migration before strict
      validation, otherwise repair and upgrade can strand older repos.
- [x] A prompt hook that only proves "the hook ran" is not Odylith-first enough;
      the cheap path must still prove the substrate handshake without building
      the full conversation/intervention bundle.
- [x] Current-source launcher templates must stay parseable by the latest
      shipped runtime health checker until the managed runtime release advances
      past that parser.
- [x] Current-source Claude prompt-bundle launchers must also run on the
      shipped v0.1.12 runtime by falling back to its existing prompt-context
      and prompt-teaser commands until the new bundled module ships.
- [x] Current-source Claude settings must keep shipped v0.1.12
      intervention-status readiness truthful by exposing legacy prompt hook
      names as no-op status markers while prompt-bundle owns the real work.
- [x] Historical consumer upgrade starts from 0.1.10, 0.1.11, and 0.1.12
      must activate the v0.1.13 target through the normal upgrade lifecycle.
      The 0.1.10 path must apply the v0.1.11 value-engine migration when
      legacy signal-ranker artifacts remain; 0.1.11 and 0.1.12 must skip that
      migration cleanly.

## Must-Ship
- [x] Add shared prompt route locks so help/show/capabilities prompts bypass
      heavy context work without changing the user-visible command contract.
- [x] Add `odylith claude prompt-bundle` so show/help route locks, prompt
      context, and teaser output run through one host path.
- [x] Render Claude settings with one prompt-submit bundle hook, host-native
      Bash guard filters, and async PostToolUse checkpoints where supported.
- [x] Keep Codex PostToolUse on a cheap dirty-event recorder and settle
      governed refresh work during Stop or the next grounding cycle.
- [x] Preserve automatic context/intervention semantics with focused parity
      tests for hidden context, visible teaser output, and route locks.
- [x] Replace bare low-signal prompt receipts and manual SessionStart fallback
      copy with compact substrate summaries covering context, memory, execution,
      delivery, Tribunal, and proof lanes.
- [x] Seed host-launched hooks with context-engine workspace-Python and
      background-autospawn defaults so warm daemon reuse is available without
      changing the public hook command contract.
- [x] Keep generated repo and bootstrap launchers compatible with v0.1.12
      fallback-health parsing while preserving direct host-hook dispatch.
- [x] Keep `claude prompt-bundle` compatible with shipped v0.1.12 runtimes by
      detecting module availability and merging legacy prompt-context plus
      prompt-teaser outputs only when the bundled module is absent.
- [x] Keep shipped `claude intervention-status` compatible with prompt-bundle
      settings by adding no-op legacy prompt-context and prompt-teaser marker
      hooks that avoid duplicate Python prompt analysis.
- [x] Add an explicit historical upgrade matrix proving 0.1.10 -> 0.1.13,
      0.1.11 -> 0.1.13, and 0.1.12 -> 0.1.13 activation, migration-plan
      state, migration-result state, pin adoption, and runtime pointer
      convergence.
- [x] Enforce Casebook single-word Status and Type metadata in validation,
      capture, projection, dashboard rendering, and migration backfills.
- [x] Mark explicit-only Claude workflow skills as slash-invocable without
      removing automatic context, bug-capture, start, show, sync, or hygiene
      skills from model invocation.
- [x] Update host contracts, source bundle mirrors, Radar, Casebook, and
      release assignments for v0.1.13.

## Should-Ship
- [ ] Convert the host hook daemon proposal into a separate design slice with
      trust, lifecycle, fallback, and local transport boundaries.
- [ ] Add a repeatable cross-host SDK benchmark harness for release evidence
      once the v0.1.13 hook architecture is stable.

## Defer
- [ ] MCP server scope cleanup remains local host configuration work, not a
      repo-shipped v0.1.13 product contract.
- [ ] Root `AGENTS.md` kernel splitting is deferred until path-scoped guidance
      behavior can be proven without weakening safety or CLI-first policy.

## Risks & Mitigations
- [x] Risk: Moving checkpoint work off the critical path could lose governance
      evidence after edits or Bash commands.
  - [x] Mitigation: Codex records durable dirty events synchronously and Stop
        settlement replays governed refresh or keeps unsettled events for the
        next prompt when refresh fails.
- [x] Risk: Claude prompt-bundle could accidentally drop visible teaser output
      or hidden prompt context.
  - [x] Mitigation: Prompt-bundle tests compare route-lock behavior and
        hidden/visible output parity against the previous prompt-context and
        prompt-teaser surfaces.
- [x] Risk: Strict Casebook Status/Type validation could break legacy
      consumer migrations.
  - [x] Mitigation: Casebook sync migration backfills missing Type and compacts
        prose Status before validation, with doctor and upgrade regression
        coverage.
- [x] Risk: Skill-surface diet could remove automatic governance capture.
  - [x] Mitigation: Explicit-only flags are limited to manual workflow skills;
        tests assert automatic context and bug-capture skills remain
        model-invokable.
- [x] Risk: Low-signal prompt optimization could bypass memory, Execution
      Engine, Tribunal, or intervention alignment.
  - [x] Mitigation: The quiet path now builds the compact local alignment
        substrate and tests assert the emitted context carries memory,
        execution, and lane-proof evidence without constructing the full
        conversation bundle.
- [x] Risk: New generated launchers could look unhealthy to the shipped
      v0.1.12 runtime during fresh install or repair.
  - [x] Mitigation: Generated launchers now include a legacy health-check
        fallback anchor and a regression test that mimics the v0.1.12 parser
        while keeping the active direct-dispatch path.
- [x] Risk: Current-source generated launchers could route Claude
      prompt-bundle to a module missing from the shipped v0.1.12 runtime.
  - [x] Mitigation: Generated launchers now detect the module in the active
        runtime or source `PYTHONPATH`; if absent, they run the shipped
        prompt-context and prompt-teaser commands and merge their outputs.
- [x] Risk: Shipped v0.1.12 `claude intervention-status` could report
      degraded when the current-source prompt-bundle hook is actually ready.
  - [x] Mitigation: Generated Claude settings include no-op legacy prompt hook
        markers for status compatibility, and current-source status treats
        prompt-bundle as the prompt-submit readiness owner.
- [x] Risk: v0.1.13 could pass latest-runtime proof while older supported
      installs fail during direct upgrade.
  - [x] Mitigation: Added a lifecycle simulator matrix for 0.1.10 -> 0.1.13,
        0.1.11 -> 0.1.13, and 0.1.12 -> 0.1.13. The 0.1.10 fixture removes
        the value corpus and seeds a legacy signal-ranker artifact so the
        value-engine migration applies, removes the old artifact, writes the
        replacement corpus, activates 0.1.13, and records the result.

## Validation
- [x] `PYTHONPATH=src pytest -q tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_host_runtime_contract.py tests/unit/runtime/test_claude_cli_capabilities.py tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_claude_host_compatibility.py tests/unit/test_claude_host_cli.py tests/unit/test_cli_audit.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py tests/integration/install/test_manager.py::test_doctor_bundle_repair_backfills_legacy_casebook_bug_ids tests/integration/install/test_manager.py::test_upgrade_same_version_backfills_legacy_casebook_bug_ids tests/integration/install/test_manager.py::test_consumer_upgrade_backfills_legacy_casebook_bug_ids_during_runtime_activation`
- [x] `PYTHONPATH=src ODYLITH_BROWSER_FAILURE_SCREENSHOTS=.odylith/browser-failures .venv/bin/python -m pytest -q tests/integration/runtime/test_*browser*.py` (`182 passed, 1 skipped`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_odylith_reasoning.py tests/unit/runtime/test_compass_standup_brief_maintenance.py tests/unit/runtime/test_compass_refresh_wait_settlement.py tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_component_registry_intelligence.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/install/test_host_worktree_launcher.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_codex_host_session_brief.py tests/unit/runtime/test_claude_host_session_brief.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_host_runtime_contract.py tests/unit/runtime/test_claude_cli_capabilities.py tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_claude_host_compatibility.py tests/unit/test_claude_host_cli.py tests/unit/test_cli_audit.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_source_bundle_mirror.py` (`588 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/install/test_manager.py::test_doctor_bundle_repair_backfills_legacy_casebook_bug_ids tests/integration/install/test_manager.py::test_upgrade_same_version_backfills_legacy_casebook_bug_ids tests/integration/install/test_manager.py::test_consumer_upgrade_backfills_legacy_casebook_bug_ids_during_runtime_activation` (`3 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_source_bundle_mirror.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_component_registry_intelligence.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_compass_standup_brief_maintenance.py tests/unit/runtime/test_compass_refresh_wait_settlement.py` (`140 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_runtime.py` (`45 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_runtime_host_hook_launcher.py` (`4 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_runtime.py tests/unit/install/test_runtime_host_hook_launcher.py` (`49 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_claude_cli_capabilities.py tests/unit/runtime/test_claude_host_compatibility.py tests/unit/runtime/test_intervention_delivery_status.py::test_claude_intervention_status_checks_prompt_teaser_and_edit_hooks tests/unit/test_claude_host_cli.py` (`34 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_intervention_delivery_status.py` (`17 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_runtime.py tests/integration/install/test_manager.py -k "launcher or fallback or start_preflight"` (`30 passed, 107 deselected`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_13` (`1 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_migration_runtime.py tests/unit/install/test_value_engine_migration.py tests/integration/install/test_lifecycle_simulator.py` (`53 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/install/test_manager.py` (`92 passed`)
- [x] Mixed-version fresh-host proof in `/private/tmp/odylith-fresh-host-final-aezgVP`: current-source install succeeded against shipped `0.1.12`; `version` and `doctor` ran healthy through the generated launcher; Codex prompt context, Claude prompt-bundle context/visible fallback, Codex and Claude `intervention-status`, and Codex/Claude visible-intervention smokes all passed; `start` reached Context/Execution Engine narrowing and returned only the expected empty-repo fallback.
- [x] Targeted browser regression rerun for default Compass completed-program
      hiding and Radar date sort (`3 passed`), followed by the full browser
      matrix (`182 passed, 1 skipped`).
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli release migration-gate --repo-root . --target-version 0.1.13`
- [x] `./.odylith/bin/odylith release migration-gate --repo-root . --target-version 0.1.13 --json` (`ok: true`; no blocked manual migrations; no ungated lifecycle paths)
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli validate guidance-behavior --repo-root .`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli validate discipline --repo-root .`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli validate self-host-posture --repo-root . --mode local-runtime`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli codex intervention-status --repo-root .`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli claude intervention-status --repo-root .`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli codex visible-intervention --repo-root . --phase prompt_submit --prompt "I do not think it is working"`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.cli claude visible-intervention --repo-root . --phase prompt_submit --prompt "I do not think it is working"`
- [x] `./.odylith/bin/odylith casebook validate --repo-root .`
- [x] `./.odylith/bin/odylith validate version-truth --repo-root .`
- [x] `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [x] `./.odylith/bin/odylith validate plan-workstream-binding --repo-root .`
- [x] `./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .`
- [x] `git diff --check`
