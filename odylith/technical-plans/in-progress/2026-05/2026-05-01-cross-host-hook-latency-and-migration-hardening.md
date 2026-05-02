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
- Odylith-directed quiet prompts and SessionStart memory updates must still
  read the compact alignment substrate: Context Engine packet state, memory
  backend, Execution Engine decision, delivery visibility, Tribunal state, and
  proof status. Generic low-signal prompts may stay fully silent.
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
- [CB-155](../../../casebook/bugs/2026-05-02-radar-allowed-topology-sensitive-workstream-to-render-without-topology.md)
  tracks the Radar topology-completeness gap found when B-141 rendered without
  the Atlas diagrams that bound the cross-host/runtime slice.

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
- [x] Current-source Claude readiness treats prompt-bundle as the
      prompt-submit owner, so generated settings no longer fork no-op legacy
      prompt-context or prompt-teaser marker commands on every prompt.
- [x] Historical consumer upgrade starts from 0.1.10, 0.1.11, and 0.1.12
      must activate the v0.1.13 target through the normal upgrade lifecycle.
      The 0.1.10 path must apply the v0.1.11 value-engine migration when
      legacy signal-ranker artifacts remain; 0.1.11 and 0.1.12 must skip that
      migration cleanly.
- [x] Codex dirty-event deferral must not make the intervention engine feel
      absent. Post-bash checkpoints still defer heavy governed refresh work,
      but an already-earned Observation/Proposal payload must surface through
      Codex PostToolUse output; Assist remains excluded from that live hook
      payload.
- [x] Dev-maintainer source-local proof must separate runtime posture from
      release planning truth. `source-local` is the active maintainer runtime
      posture, `0.1.12` remains the pinned dogfood baseline, and the default
      Compass release-target view must follow the explicit current/next
      release aliases instead of rendering every older active release lane.
- [x] Governed surface refresh performance needs end-to-end protection too,
      not only hook microbenchmarks. v0.1.13 now has a temporary consumer-repo
      test that runs full sync dry-run, all-surface dashboard refresh, Compass
      status, and owned Radar/Atlas/Registry/Casebook refresh commands under
      latency budgets with a provider tripwire that fails if the local path
      tries to spend reasoning credits.
- [x] Startup grounding order is part of latency UX, not just correctness.
      `odylith start` must be the first visible grounding gate on substantive
      turns; `odylith context`, `odylith query`, `git status`, and broad repo
      search run only after startup completes and an exact anchor is known.
- [x] Claude's measured surface issue was real: root `CLAUDE.md` duplicated the
      managed `AGENTS.md` contract before importing it, `.claude/CLAUDE.md`
      restated several root rules, SessionStart printed a brief already written
      to auto-memory, and generic low-signal prompt receipts spent alignment
      work on turns that carried no Odylith signal.
- [x] Consumer-lane surface trimming must be a feature-preserving routing
      change, not a capability reduction. The v0.1.13 pass now keeps startup,
      Context Engine, Execution Engine, memory substrate, Tribunal,
      Intervention Engine, observers, governance, subagent routing, Surface
      DAGs, delivery, analysis, and migration-breakage observation named in
      the always-loaded consumer contract while moving long-form policy to
      routed guidance and skills.
- [x] Native host features should be used asymmetrically. Claude can hide
      manual workflow skills from automatic model invocation with
      `disable-model-invocation: true`; Codex should keep its separate
      `.agents/skills` layer concise and must not receive Claude-only hook or
      skill fields.
- [x] Topology is a governing spine, not optional decoration. v0.1.13 now
      links B-141 to its runtime, host, intervention, discipline, and
      migration diagrams, backfills B-140 to the migration/runtime topology,
      and rejects new topology-sensitive implementation records that omit
      `related_diagram_ids` unless they carry an explicit no-topology
      rationale.
- [x] Casebook bug closure is a release lifecycle action, not a manual field
      edit. `FixedPendingRelease` records stay pending until the `Fixed In`
      release is shipped; local closeout then updates compact `Status` and
      `Fixed` tokens through `odylith release casebook-closeout`, while the
      GitHub issue pipeline separately waits for public release availability.
- [x] The remaining root guidance surface should be trimmed by routing, not by
      deleting capability. The detailed anti-slop bans belong in
      `ANTI_SLOP_AND_DECOMPOSITION.md` and the code-hygiene skill; root
      `AGENTS.md` keeps the hard-law pointer, compact identity and file-size
      rules, and the explicit engine-preservation contract. Local
      `odylith-start` and `odylith-context` skill shims stay checked in for
      both Codex and Claude because they own the serial startup/context rule.

## Must-Ship
- [x] Add shared prompt route locks so help/show/capabilities prompts bypass
      heavy context work without changing the user-visible command contract.
- [x] Add `odylith claude prompt-bundle` so show/help route locks, prompt
      context, and teaser output run through one host path.
- [x] Render Claude settings with one prompt-submit bundle hook, host-native
      Bash guard filters, and async PostToolUse checkpoints where supported.
- [x] Keep Codex PostToolUse on a cheap dirty-event recorder and settle
      governed refresh work during Stop or the next grounding cycle.
- [x] Keep Codex PostToolUse chat-visible for earned live intervention beats:
      Observation/Proposal payloads render in the hook response while the
      durable dirty-event record owns later governance settlement.
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
      settings by treating prompt-bundle as the prompt-submit readiness owner
      in current-source capability/status checks instead of emitting no-op
      prompt-context and prompt-teaser marker hooks.
- [x] Add an explicit historical upgrade matrix proving 0.1.10 -> 0.1.13,
      0.1.11 -> 0.1.13, and 0.1.12 -> 0.1.13 activation, migration-plan
      state, migration-result state, pin adoption, and runtime pointer
      convergence.
- [x] Enforce Casebook single-word Status, Fixed, and Type metadata in
      validation, capture, projection, dashboard rendering, sync normalization,
      and the registered v0.1.13 migration from 0.1.10, 0.1.11, and 0.1.12.
- [x] Add end-to-end governed sync performance coverage for `odylith sync`,
      `odylith dashboard refresh`, `odylith compass refresh --status`, and the
      owned Radar, Atlas, Registry, and Casebook refresh commands, including a
      no-provider credit-burn tripwire and multi-surface parallelism guard.
- [x] Mark explicit-only Claude workflow skills as slash-invocable without
      removing automatic context, bug-capture, start, show, sync, or hygiene
      skills from model invocation.
- [x] Update host contracts, source bundle mirrors, Radar, Casebook, and
      release assignments for v0.1.13.
- [x] Update shared guidance, Claude commands, Codex and Claude skill shims,
      source skills, bundle mirrors, and enforcement tests so all hosts honor
      serial `start` before `context` grounding without weakening Context
      Engine or intervention kickoff.
- [x] Remove duplicate Claude guidance and hook tax without dropping features:
      root `CLAUDE.md` is a lean bridge into `AGENTS.md`, `.claude/CLAUDE.md`
      is pointer-only, generated Claude SessionStart hooks run `--quiet`,
      generic low-signal prompt receipts are suppressed on Claude and Codex,
      Odylith-directed quiet prompts still emit substrate proof, and Claude
      exact non-governed Bash edits skip startup/checkpoint work.
- [x] Slim consumer-lane guidance without muting Odylith engines: generated
      installed root guidance and consumer `odylith/AGENTS.md` now carry a
      hard-law kernel, explicit engine-preservation language, and routed
      pointers instead of duplicating the long intervention, anti-slop, and
      governance manual on every host turn.
- [x] Use Claude-native skill invocation controls to reduce the model-visible
      surface: lower-frequency workflow skills remain slash-invocable with
      `disable-model-invocation: true`, while automatic bug capture,
      preflight, code hygiene, startup, context, show, and sync stay
      model-invocable. Codex skill policy remains separate and unchanged.
- [x] Add automated Casebook release closeout: `odylith release
      casebook-closeout --apply` closes only shipped-release records with
      validation evidence, and `odylith release update --status shipped`
      invokes the same sweep automatically unless explicitly skipped.
- [x] Finish the safe root guidance surface diet: compact the maintainer-root
      contributor identity and file-size rules, route detailed anti-slop
      examples to the playbook and skill, and remove duplicate Casebook Claude
      closeout wording while preserving the sibling AGENTS import.
- [x] Finish the Odylith-tree consumer guidance de-dup: keep installed
      `odylith/AGENTS.md` explicit for startup, context ordering, engine
      activation, intervention visibility, consumer write boundaries, CLI-first,
      anti-slop, and host-specific capability separation, while routing repeated
      help/show/commentary/governance detail back to the repo-root hard-law
      kernel that loads first.
- [x] Decompose Radar topology validation out of the oversized backlog
      validator so B-141 topology enforcement does not keep growing a red-zone
      runtime file.

## Should-Ship
- [ ] Convert the host hook daemon proposal into a separate design slice with
      trust, lifecycle, fallback, and local transport boundaries.
- [ ] Add a repeatable cross-host SDK benchmark harness for release evidence
      once the v0.1.13 hook architecture is stable.

## Defer
- [ ] MCP server scope cleanup remains local host configuration work, not a
      repo-shipped v0.1.13 product contract.
- [ ] Further maintainer-lane kernel splitting is deferred until path-scoped
      guidance behavior can be proven without weakening safety, CLI-first
      policy, release-gate proof, or migration-observer obligations.

## Risks & Mitigations
- [x] Risk: Moving checkpoint work off the critical path could lose governance
      evidence after edits or Bash commands.
  - [x] Mitigation: Codex records durable dirty events synchronously and Stop
        settlement replays governed refresh or keeps unsettled events for the
        next prompt when refresh fails.
- [x] Risk: The latency fix could make Codex checkpoint hooks silent and hide
      live Intervention Engine output from the chat.
  - [x] Mitigation: Codex post-bash now emits the earned live
        Observation/Proposal payload from the existing intervention bundle
        while continuing to exclude Assist from the hook-visible path and
        defer heavy governance refresh.
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
- [x] Risk: Consumer-lane guidance slimming could accidentally drop the
      product philosophy: prompt context assessment, observations,
      interventions, ambient assists, memory, execution, or governance capture.
  - [x] Mitigation: The consumer hard-law kernel names the preserved engines,
        keeps `start` as the serial first gate, keeps context/query ordering,
        keeps intervention-status and visible-intervention proof, and routes
        long-form behavior to the existing skills and guidance rather than
        deleting it.
- [x] Risk: Low-signal prompt optimization could bypass memory, Execution
      Engine, Tribunal, or intervention alignment when the user is asking
      Odylith about its own presence or visibility.
  - [x] Mitigation: Generic low-signal prompts stay silent, while
        Odylith-directed quiet prompts still build the compact local alignment
        substrate. Tests assert the emitted context carries memory, execution,
        and lane-proof evidence without constructing the full conversation
        bundle.
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
  - [x] Mitigation: Current-source status treats prompt-bundle as the
        prompt-submit readiness owner and the v0.1.13 settings renderer no
        longer emits marker hooks that fork shells without doing product work.
- [x] Risk: v0.1.13 could pass latest-runtime proof while older supported
      installs fail during direct upgrade.
  - [x] Mitigation: Added a lifecycle simulator matrix for 0.1.10 -> 0.1.13,
        0.1.11 -> 0.1.13, and 0.1.12 -> 0.1.13. The 0.1.10 fixture removes
        the value corpus and seeds a legacy signal-ranker artifact so the
        value-engine migration applies, removes the old artifact, writes the
        replacement corpus, activates 0.1.13, and records the result.
- [x] Risk: Switching to dev-maintainer source-local could still leave the
      UI looking pinned to 0.1.12 because stale active release lanes remained
      visible beside the true 0.1.13 current/next target.
  - [x] Mitigation: Compass Release Targets now defaults to current/next
        alias groups when aliases exist, while preserving active/planned/draft
        fallback for repos that have not adopted release aliases yet.
- [x] Risk: Agents could optimize for lower wall-clock latency by launching
      `start`, `context`, `git status`, and repo search together, making the
      transcript imply the Context Engine ran before startup.
  - [x] Mitigation: Cross-host guidance and skill surfaces now make startup a
        serial gate. Tests pin root guidance, install-generated guidance,
        Claude command assets, Codex/Claude skill shims, source skills, and
        bundle mirrors to the same rule.

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
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_migration_runtime.py tests/unit/install/test_value_engine_migration.py tests/unit/install/test_migration_readiness.py tests/unit/install/test_migration_audit.py tests/integration/install/test_lifecycle_simulator.py` (`59 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/install/test_manager.py` (`92 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_codex_host_bash_guard.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_claude_host_bash_guard.py tests/unit/runtime/test_claude_host_post_bash_checkpoint.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/runtime/test_claude_host_stop_summary.py tests/unit/runtime/test_host_hook_cli_dispatch.py tests/unit/runtime/test_intervention_cross_host_parity.py tests/unit/runtime/test_host_visible_intervention.py` (`146 passed`)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_tooling_dashboard_runtime_builder.py tests/unit/runtime/test_tooling_dashboard_shell_render_integration.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_render_registry_dashboard.py` (`137 passed`)
- [x] `pytest -q tests/unit/install/test_agents.py tests/unit/install/test_claude_effective_settings.py tests/unit/install/test_codex_project_assets.py` (`46 passed`)
- [x] `pytest -q tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_post_bash_checkpoint.py tests/unit/test_claude_project_hooks.py` (`55 passed`)
- [x] `./.odylith/bin/odylith upgrade --repo-root . --source-repo . --json` switched the product repo to detached `source-local`, kept the pin at `0.1.12`, marked release eligibility false, and refreshed tooling shell, Radar, and Compass surfaces for dev-maintainer proof.
- [x] `PYTHONPATH=src pytest -q tests/unit/install/test_agents.py tests/unit/install/test_manager.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_show_capabilities.py` (`119 passed`; consumer guidance byte budgets, explicit engine preservation, Claude model-invocable skill diet, Codex/Claude skill separation, and anti-slop/show-capability contracts)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_validate_backlog_contract.py` (`30 passed`; topology-sensitive implementation workstreams opened on or after 2026-05-01 must declare `related_diagram_ids` or an explicit topology rationale)
- [x] Post-change surface measurement: root `AGENTS.md` moved from 28,982
      bytes to 17,381 bytes; consumer `odylith/AGENTS.md` and its bundle
      mirror measure 16,307 bytes; Claude model-invocable project skills are
      capped at seven while twenty-eight lower-frequency workflows remain
      explicit/slash-invocable. Codex in this session exposes one
      `odylith-start` and one `odylith-context` skill; the checked-in local
      shims remain because they preserve serial startup before context.
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_hygiene.py::test_anti_slop_contract_stays_explicit_across_guidance_surfaces tests/unit/runtime/test_hygiene.py::test_root_agents_keeps_anti_slop_detailed_rules_routed tests/unit/runtime/test_hygiene.py::test_casebook_claude_bridge_defers_release_closeout_rule_to_agents` (`3 passed`; root anti-slop detail stays routed to playbooks and Casebook Claude imports the closeout rule instead of restating it)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_agents.py tests/unit/runtime/test_source_bundle_mirror.py` (`15 passed`; generated guidance block and bundle mirror contracts still match)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_casebook_source_validation.py tests/unit/install/test_agents.py tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_validate_guidance_behavior.py tests/unit/runtime/test_validate_discipline.py` (`170 passed`; includes topology-sensitive workstream enforcement and oversized-hotfile inventory)
- [x] `./.odylith/bin/odylith release migration-gate --repo-root . --target-version 0.1.13 --json` (`ok: true`, `blocked: 0`, `ungated: 0`; root guidance routing, topology-validator decomposition, and refreshed browser/install-managed surfaces covered by B-140 migration-observer markers)
- [x] `./.odylith/bin/odylith casebook validate --repo-root . && ./.odylith/bin/odylith validate guidance-behavior --repo-root . && ./.odylith/bin/odylith validate discipline --repo-root . && ./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [x] `git diff --check`
- [x] Mixed-version fresh-host proof in `/private/tmp/odylith-fresh-host-final-aezgVP`: current-source install succeeded against shipped `0.1.12`; `version` and `doctor` ran healthy through the generated launcher; Codex prompt context, Claude prompt-bundle context/visible fallback, Codex and Claude `intervention-status`, and Codex/Claude visible-intervention smokes all passed; `start` reached Context/Execution Engine narrowing and returned only the expected empty-repo fallback.
- [x] Targeted browser regression rerun for default Compass completed-program
      hiding and Radar date sort (`3 passed`), followed by the full browser
      matrix (`182 passed, 1 skipped`).
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_render_compass_dashboard.py::test_render_compass_dashboard_emits_release_summary_and_workstream_release_ui tests/integration/runtime/test_surface_browser_smoke.py::test_compass_and_radar_target_release_cards_show_labeled_release_version` (`2 passed`; default Compass Release Targets renders only the 0.1.13 current/next group and excludes 0.1.12)
- [x] `PYTHONPATH=src ODYLITH_BROWSER_FAILURE_SCREENSHOTS=.odylith/browser-failures .venv/bin/python -m pytest -q tests/integration/runtime/test_compass_browser_regression_matrix.py::test_compass_browser_traceability_fallback_prioritizes_active_release_truth_when_source_snapshot_is_missing tests/integration/runtime/test_compass_browser_regression_matrix.py::test_compass_browser_ignores_unusable_source_truth_snapshot_and_continues_to_traceability_fallback tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_checklist_label_instead_of_fake_zero_progress tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_tracked_execution_percent_for_partial_progress` (`4 passed`; fixture release aliases now match the current-release target they assert)
- [x] `PYTHONPATH=src ODYLITH_BROWSER_FAILURE_SCREENSHOTS=.odylith/browser-failures .venv/bin/python -m pytest -q tests/integration/runtime/test_*browser*.py` (`182 passed, 1 skipped`; post-alias release-target filtering proof)
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
